"""Tests for the GitHub client, using httpx.MockTransport instead of the network."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable

import httpx
import pytest

from engineering_bootstrap.github import (
    AuthenticationError,
    GitHubClient,
    GitHubError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    RedactingFilter,
    TransientError,
    install_redaction,
    resolve_token,
)

TOKEN = "ghp_FakeTokenForTests0123456789"
Handler = Callable[[httpx.Request], httpx.Response]


class Recorder:
    """Mock transport that replays responses in order and records the requests."""

    def __init__(self, *responses: httpx.Response | Handler | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response(request) if callable(response) else response


def make_client(recorder: Recorder, **options: object) -> tuple[GitHubClient, list[float]]:
    sleeps: list[float] = []
    client = GitHubClient(
        TOKEN,
        transport=httpx.MockTransport(recorder),
        sleep=sleeps.append,
        clock=lambda: 1_000.0,
        **options,  # type: ignore[arg-type]
    )
    return client, sleeps


def test_requests_carry_auth_and_api_headers() -> None:
    recorder = Recorder(httpx.Response(200, json={"login": "octo"}))
    client, _ = make_client(recorder)

    assert client.get_json("/user") == {"login": "octo"}

    headers = recorder.requests[0].headers
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert headers["accept"] == "application/vnd.github+json"
    assert headers["x-github-api-version"] == "2022-11-28"
    assert headers["user-agent"].startswith("engineering-bootstrap/")


def test_paginate_follows_next_links() -> None:
    next_link = '<https://api.github.com/repos/o/r/labels?per_page=100&page=2>; rel="next"'
    recorder = Recorder(
        httpx.Response(200, json=[{"name": "a"}], headers={"link": next_link}),
        httpx.Response(200, json=[{"name": "b"}]),
    )
    client, _ = make_client(recorder)

    names = [item["name"] for item in client.paginate("/repos/o/r/labels")]

    assert names == ["a", "b"]
    assert recorder.requests[0].url.params["per_page"] == "100"
    assert recorder.requests[1].url.params["page"] == "2"


def test_paginate_refuses_links_to_other_hosts() -> None:
    next_link = '<https://evil.example/steal?page=2>; rel="next"'
    recorder = Recorder(httpx.Response(200, json=[1], headers={"link": next_link}))
    client, _ = make_client(recorder)

    with pytest.raises(GitHubError, match="another origin"):
        list(client.paginate("/repos/o/r/labels"))
    assert len(recorder.requests) == 1


def test_paginate_rejects_non_list_pages() -> None:
    client, _ = make_client(Recorder(httpx.Response(200, json={"message": "x"})))

    with pytest.raises(GitHubError, match="expected a JSON array"):
        list(client.paginate("/repos/o/r/labels"))


def test_server_errors_are_retried_with_backoff() -> None:
    recorder = Recorder(
        httpx.Response(502),
        httpx.Response(503),
        httpx.Response(200, json={}),
    )
    client, sleeps = make_client(recorder)

    client.get_json("/repos/o/r")

    assert len(recorder.requests) == 3
    assert sleeps == [1.0, 2.0]


def test_network_errors_are_retried() -> None:
    recorder = Recorder(httpx.ConnectError("refused"), httpx.Response(200, json={}))
    client, sleeps = make_client(recorder)

    client.get_json("/repos/o/r")

    assert sleeps == [1.0]


def test_persistent_server_error_raises_transient_error() -> None:
    recorder = Recorder(*(httpx.Response(500) for _ in range(3)))
    client, _ = make_client(recorder, max_retries=2)

    with pytest.raises(TransientError, match="HTTP 500 after 3 attempt"):
        client.get_json("/repos/o/r")


def test_post_is_not_retried_after_server_error() -> None:
    recorder = Recorder(httpx.Response(502))
    client, sleeps = make_client(recorder)

    with pytest.raises(TransientError):
        client.request("POST", "/repos/o/r/labels", json={"name": "bug"})
    assert len(recorder.requests) == 1
    assert sleeps == []


def test_primary_rate_limit_waits_until_reset() -> None:
    limited = httpx.Response(
        403,
        json={"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1030"},
    )
    recorder = Recorder(limited, httpx.Response(200, json={}))
    client, sleeps = make_client(recorder)

    client.get_json("/repos/o/r")

    assert sleeps == [31.0]


def test_retry_after_header_is_honored_also_for_post() -> None:
    recorder = Recorder(
        httpx.Response(429, headers={"retry-after": "5"}),
        httpx.Response(201, json={}),
    )
    client, sleeps = make_client(recorder)

    client.request("POST", "/repos/o/r/labels", json={"name": "bug"})

    assert sleeps == [5.0]


def test_secondary_rate_limit_without_headers_waits_a_minute() -> None:
    recorder = Recorder(
        httpx.Response(403, json={"message": "You have exceeded a secondary rate limit."}),
        httpx.Response(200, json={}),
    )
    client, sleeps = make_client(recorder)

    client.get_json("/repos/o/r")

    assert sleeps == [60.0]


def test_rate_limit_wait_over_the_limit_fails_clearly() -> None:
    limited = httpx.Response(
        403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "5000"}
    )
    client, sleeps = make_client(Recorder(limited), max_rate_limit_wait=300)

    with pytest.raises(RateLimitError, match="rate limit exceeded; reset in 4001 s"):
        client.get_json("/repos/o/r")
    assert sleeps == []


@pytest.mark.parametrize(
    ("status", "error", "text"),
    [
        (401, AuthenticationError, "authentication failed (Bad credentials)"),
        (403, PermissionDeniedError, "permission denied (Resource not accessible)"),
        (404, NotFoundError, "not found (Not Found)"),
        (422, GitHubError, "HTTP 422 (Validation Failed)"),
    ],
)
def test_error_statuses_raise_typed_errors(
    status: int, error: type[GitHubError], text: str
) -> None:
    message = {
        401: "Bad credentials",
        403: "Resource not accessible",
        404: "Not Found",
        422: "Validation Failed",
    }[status]
    client, _ = make_client(Recorder(httpx.Response(status, json={"message": message})))

    with pytest.raises(error, match=text.replace("(", r"\(").replace(")", r"\)")) as raised:
        client.get_json("/repos/o/r")
    assert raised.value.status == status
    assert TOKEN not in str(raised.value)


def test_absolute_url_to_other_origin_is_refused() -> None:
    recorder = Recorder()
    client, _ = make_client(recorder)

    with pytest.raises(GitHubError, match="another origin"):
        client.get_json("https://example.com/repos/o/r")
    assert recorder.requests == []


def test_redirects_are_not_followed() -> None:
    redirect = httpx.Response(302, headers={"location": "https://example.com/"})
    client, _ = make_client(Recorder(redirect))

    response = client.request("GET", "/repos/o/r")

    assert response.status_code == 302


def test_debug_logging_never_contains_the_token(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    recorder = Recorder(httpx.Response(502), httpx.Response(200, json={}))
    client, _ = make_client(recorder)

    client.get_json("/repos/o/r")

    assert caplog.records, "expected debug records from the client and httpx"
    assert TOKEN not in caplog.text
    assert "Bearer" not in caplog.text


def test_redaction_filter_removes_tokens_from_records(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.handler.addFilter(RedactingFilter((TOKEN,)))
    log = logging.getLogger("test.redaction")

    log.debug("token %s", TOKEN)
    log.debug("headers {'Authorization': 'Bearer abc123secret'}")
    log.debug("Authorization: token other-secret-value")
    log.debug("leaked github_pat_11ABCDEFG0123456789_abcdef")

    assert TOKEN not in caplog.text
    assert "abc123secret" not in caplog.text
    assert "other-secret-value" not in caplog.text
    assert "github_pat_" not in caplog.text
    assert caplog.text.count("***") == 4


def test_redaction_filter_covers_exception_text(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.handler.addFilter(RedactingFilter((TOKEN,)))

    try:
        raise RuntimeError(f"failed with {TOKEN}")
    except RuntimeError:
        logging.getLogger("test.redaction").exception("request failed")

    assert TOKEN not in caplog.text


def test_install_redaction_adds_filter_to_handlers() -> None:
    log = logging.getLogger("test.install")
    handler = logging.NullHandler()
    log.addHandler(handler)
    try:
        installed = install_redaction(TOKEN, log)
        assert installed in handler.filters
    finally:
        log.removeHandler(handler)


def test_empty_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        GitHubClient("")


def test_resolve_token_prefers_github_token() -> None:
    def fail(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("gh must not run")

    environ = {"GITHUB_TOKEN": " first ", "GH_TOKEN": "second"}

    assert resolve_token(environ, run=fail) == "first"
    assert resolve_token({"GH_TOKEN": "second"}, run=fail) == "second"


def test_resolve_token_falls_back_to_gh() -> None:
    calls: list[list[str]] = []

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="from-gh\n", stderr="")

    token = resolve_token({}, which=lambda _: "/usr/bin/gh", run=run)

    assert token == "from-gh"
    assert calls == [["/usr/bin/gh", "auth", "token"]]


@pytest.mark.parametrize(
    ("which_result", "returncode", "stdout"),
    [(None, 0, ""), ("/usr/bin/gh", 1, ""), ("/usr/bin/gh", 0, "  \n")],
)
def test_resolve_token_without_any_source_fails(
    which_result: str | None, returncode: int, stdout: str
) -> None:
    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")

    with pytest.raises(AuthenticationError, match="GITHUB_TOKEN or GH_TOKEN"):
        resolve_token({}, which=lambda _: which_result, run=run)
