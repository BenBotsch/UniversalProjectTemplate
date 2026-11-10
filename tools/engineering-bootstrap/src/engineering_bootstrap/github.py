"""GitHub REST API client with token authentication, pagination, rate limits and retries.

The token is sent only in the ``Authorization`` header and only to the configured API origin:
redirects are not followed and pagination links to other hosts are refused. The client never
logs headers; :class:`RedactingFilter` additionally removes the token from any log record.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import httpx

from engineering_bootstrap import __version__

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
TOKEN_VARIABLES = ("GITHUB_TOKEN", "GH_TOKEN")
RETRY_STATUSES = frozenset({500, 502, 503, 504})
# A failed POST may still have created something, so only these methods are retried after
# network errors and server errors. Rate-limited requests were not processed and are always
# retried.
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "PATCH", "DELETE"})
SECONDARY_RATE_LIMIT_WAIT = 60.0
REDACTED = "***"
_CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)(?:bearer|token)?\s*[^\s,'\"}]+"),
    re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{8,}"),
)


class GitHubError(Exception):
    """A GitHub API request failed.

    Attributes:
        status: HTTP status code, or ``None`` if no response was received.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class AuthenticationError(GitHubError):
    """No token is available, or GitHub rejected it (HTTP 401)."""


class PermissionDeniedError(GitHubError):
    """The token lacks a permission for the request (HTTP 403)."""


class NotFoundError(GitHubError):
    """The resource does not exist or is hidden from the token (HTTP 404)."""


class RateLimitError(GitHubError):
    """The rate limit is exhausted and the wait would exceed the configured limit."""


class TransientError(GitHubError):
    """A network or server error persisted after all retries."""


Runner = Callable[..., subprocess.CompletedProcess[str]]


def resolve_token(
    environ: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Runner = subprocess.run,
) -> str:
    """Return a GitHub token from the environment or the GitHub CLI.

    ``GITHUB_TOKEN`` takes precedence over ``GH_TOKEN``; without either, the token of
    ``gh auth token`` is used.

    Args:
        environ: Environment to read; defaults to ``os.environ``.
        which: Locates the ``gh`` executable; injectable for tests.
        run: Runs ``gh``; injectable for tests.

    Returns:
        The token.

    Raises:
        AuthenticationError: If no token is available.
    """
    environ = os.environ if environ is None else environ
    for name in TOKEN_VARIABLES:
        value = environ.get(name, "").strip()
        if value:
            return value
    hint = "set GITHUB_TOKEN or GH_TOKEN, or log in with 'gh auth login'"
    gh = which("gh")
    if gh is None:
        raise AuthenticationError(f"no GitHub token found: {hint}")
    try:
        # Fixed argument list without a shell; the output is never logged.
        result = run([gh, "auth", "token"], capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthenticationError(f"cannot run 'gh auth token' ({exc}): {hint}") from exc
    token = result.stdout.strip()
    if result.returncode != 0 or not token:
        raise AuthenticationError(f"'gh auth token' returned no token: {hint}")
    return token


class RedactingFilter(logging.Filter):
    """Replace secrets and credential-like values in log records with ``***``.

    Args:
        secrets: Exact values to remove, for example the token in use.
    """

    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self._secrets = tuple(secret for secret in secrets if secret)

    def redact(self, text: str) -> str:
        """Return ``text`` without secrets."""
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        text = _CREDENTIAL_PATTERNS[0].sub(rf"\g<1>{REDACTED}", text)
        return _CREDENTIAL_PATTERNS[1].sub(REDACTED, text)

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the formatted message and exception text of ``record`` in place."""
        record.msg = self.redact(record.getMessage())
        record.args = None
        if record.exc_info:
            record.exc_text = self.redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def install_redaction(token: str, logger_: logging.Logger | None = None) -> RedactingFilter:
    """Add a :class:`RedactingFilter` for ``token`` to every handler of a logger.

    Handler filters see records of all child loggers, including those of ``httpx``.

    Args:
        token: The secret to redact.
        logger_: Logger whose handlers get the filter; defaults to the root logger.

    Returns:
        The installed filter.
    """
    redacting = RedactingFilter((token,))
    for handler in (logger_ or logging.getLogger()).handlers:
        handler.addFilter(redacting)
    return redacting


class GitHubClient:
    """Small synchronous client for the GitHub REST API.

    Args:
        token: Token sent as bearer authorization.
        base_url: API origin, for example ``https://api.github.com`` or a GitHub Enterprise URL.
        transport: httpx transport; tests pass ``httpx.MockTransport``.
        timeout: Timeout per request in seconds.
        max_retries: Retries after rate limits, network errors and server errors.
        max_rate_limit_wait: Longest wait in seconds for a rate limit reset; a longer wait
            fails with :class:`RateLimitError`.
        backoff: First wait in seconds after a network or server error; doubles per retry.
        sleep: Waits; injectable for tests.
        clock: Returns the current Unix time; injectable for tests.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = API_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        max_rate_limit_wait: float = 300.0,
        backoff: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not token:
            raise AuthenticationError("empty GitHub token")
        self._base = httpx.URL(base_url)
        self._max_retries = max_retries
        self._max_rate_limit_wait = max_rate_limit_wait
        self._backoff = backoff
        self._sleep = sleep
        self._clock = clock
        self._http = httpx.Client(
            base_url=self._base,
            transport=transport,
            timeout=timeout,
            follow_redirects=False,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": f"engineering-bootstrap/{__version__}",
            },
        )

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._http.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        """Send a request, waiting for rate limits and retrying transient errors.

        Args:
            method: HTTP method.
            url: Path relative to the API origin, for example ``/repos/o/r/labels``, or an
                absolute URL on the same origin.
            params: Query parameters.
            json: JSON body.

        Returns:
            The successful response (status below 400).

        Raises:
            GitHubError: Or one of its subclasses, if the request failed.
        """
        method = method.upper()
        self._check_origin(url)
        retryable = method in IDEMPOTENT_METHODS
        attempt = 0
        while True:
            try:
                response = self._http.request(method, url, params=params, json=json)
            except httpx.TransportError as exc:
                if not retryable or attempt >= self._max_retries:
                    raise TransientError(
                        f"{method} {url}: network error after {attempt + 1} attempt(s): "
                        f"{type(exc).__name__}"
                    ) from exc
                self._wait_backoff(attempt, f"{method} {url}: {type(exc).__name__}")
                attempt += 1
                continue
            # Method, URL and status only: never headers, which hold the token.
            logger.debug("%s %s -> %s", method, response.request.url, response.status_code)
            wait = self._rate_limit_wait(response)
            if wait is not None:
                if wait > self._max_rate_limit_wait:
                    raise RateLimitError(
                        f"{method} {url}: rate limit exceeded; reset in {wait:.0f} s is longer"
                        f" than the limit of {self._max_rate_limit_wait:.0f} s",
                        response.status_code,
                    )
                if attempt >= self._max_retries:
                    raise RateLimitError(
                        f"{method} {url}: still rate limited after {attempt + 1} attempt(s)",
                        response.status_code,
                    )
                logger.warning("rate limit reached; waiting %.0f s", wait)
                self._sleep(wait)
                attempt += 1
                continue
            if response.status_code in RETRY_STATUSES:
                if not retryable or attempt >= self._max_retries:
                    raise TransientError(
                        f"{method} {url}: HTTP {response.status_code} after {attempt + 1}"
                        " attempt(s)",
                        response.status_code,
                    )
                self._wait_backoff(attempt, f"{method} {url}: HTTP {response.status_code}")
                attempt += 1
                continue
            if response.status_code >= 400:
                raise _error_for(response, method, url)
            return response

    def get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return the JSON body of a GET request."""
        return self.request("GET", url, params=params).json()

    def paginate(self, url: str, *, params: Mapping[str, Any] | None = None) -> Iterator[Any]:
        """Yield the items of a paginated list endpoint, following ``Link: rel="next"``.

        Args:
            url: Path of an endpoint that returns a JSON array.
            params: Query parameters of the first request; ``per_page`` defaults to 100.

        Raises:
            GitHubError: If a page is not a JSON array or a request fails.
        """
        query: dict[str, Any] | None = {"per_page": 100, **(params or {})}
        next_url: str | None = url
        while next_url is not None:
            response = self.request("GET", next_url, params=query)
            page = response.json()
            if not isinstance(page, list):
                raise GitHubError(f"GET {url}: expected a JSON array, got {type(page).__name__}")
            yield from page
            # The next link already contains all query parameters.
            next_url = response.links.get("next", {}).get("url")
            query = None

    def _check_origin(self, url: str) -> None:
        target = httpx.URL(url)
        if target.is_absolute_url and (target.scheme, target.netloc) != (
            self._base.scheme,
            self._base.netloc,
        ):
            raise GitHubError(f"refusing to send the token to another origin: {target.host}")

    def _wait_backoff(self, attempt: int, what: str) -> None:
        delay = self._backoff * 2**attempt
        logger.warning("%s; retrying in %.0f s", what, delay)
        self._sleep(delay)

    def _rate_limit_wait(self, response: httpx.Response) -> float | None:
        """Return the seconds to wait if ``response`` is a rate limit response, else None."""
        if response.status_code not in (403, 429):
            return None
        headers = response.headers
        retry_after = headers.get("retry-after")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                return SECONDARY_RATE_LIMIT_WAIT
        if headers.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in headers:
            try:
                reset = float(headers["x-ratelimit-reset"])
            except ValueError:
                return SECONDARY_RATE_LIMIT_WAIT
            # One extra second covers clock differences to GitHub.
            return max(0.0, reset - self._clock()) + 1.0
        if response.status_code == 429 or "secondary rate limit" in _message(response).lower():
            return SECONDARY_RATE_LIMIT_WAIT
        return None


def _message(response: httpx.Response) -> str:
    """Return GitHub's error message from a response body, or an empty string."""
    try:
        body = response.json()
    except ValueError:
        return ""
    message = body.get("message") if isinstance(body, dict) else None
    return message if isinstance(message, str) else ""


def _error_for(response: httpx.Response, method: str, url: str) -> GitHubError:
    status = response.status_code
    detail = _message(response) or response.reason_phrase
    where = f"{method} {url}"
    if status == 401:
        return AuthenticationError(
            f"{where}: authentication failed ({detail}); check that the token is valid and not"
            " expired",
            status,
        )
    if status == 403:
        return PermissionDeniedError(
            f"{where}: permission denied ({detail}); the token needs the permission for this"
            " operation, for example repository administration for settings",
            status,
        )
    if status == 404:
        return NotFoundError(
            f"{where}: not found ({detail}); the resource does not exist or the token cannot"
            " see it",
            status,
        )
    return GitHubError(f"{where}: HTTP {status} ({detail})", status)
