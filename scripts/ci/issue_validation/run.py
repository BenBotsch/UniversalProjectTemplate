"""Validate the issue of an ``issues`` event and report the result on the issue.

``.github/workflows/issue-validation.yml`` runs this script for every issue event. It:

1. Reads the repository, the issue number and the sender from the event file.
2. Skips pull requests, closed issues and events sent by the validator's own account, so its
   label changes cannot start a loop.
3. Reads the current issue, its comments and, when a rule needs them, its "blocked by"
   dependencies through the REST API; the event may already be outdated.
4. Applies the rules of ``validator.py``.
5. Creates, updates or resolves exactly one comment, marked ``<!-- issue-validation -->``.
6. Sets ``status:needs-info`` for an issue in the initial status that breaks a rule, and
   restores the initial status once every rule passes. A ``status:needs-info`` label that the
   validator did not set is never removed; the comment records who set it.

The issue text is data: it is read from the API as JSON, never passed to a shell, and never
quoted in the comment. The token is read from ``GITHUB_TOKEN`` and is never printed.

Exit codes: 0 validated or skipped, also with findings; 1 GitHub API error, so that a failed
read is never reported as a valid issue; 2 invalid input or configuration.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

import yaml


def _load_validator() -> ModuleType:
    """Load validator.py; ``python -I`` does not add the script directory to sys.path."""
    path = Path(__file__).with_name("validator.py")
    spec = importlib.util.spec_from_file_location("issue_validator", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()

MARKER = "<!-- issue-validation -->"
# Recorded in the comment while status:needs-info was set by the validator.
NEEDS_INFO_MARKER = "<!-- issue-validation: needs-info set by the validator -->"
NEEDS_INFO = "status:needs-info"
DEFAULT_BOT_LOGIN = "github-actions[bot]"
DEFAULT_API_URL = "https://api.github.com"
# GitHub owners contain no dots; "." and ".." are not repository names.
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/(?!\.\.?$)[\w.-]+$")
NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
PAGE_SIZE = 100
TIMEOUT_SECONDS = 30


class ApiError(RuntimeError):
    """A GitHub API request failed."""


@dataclass(frozen=True)
class Response:
    """A GitHub API response.

    Attributes:
        status: HTTP status code.
        data: Decoded JSON body, or ``None`` for an empty body.
        next_url: URL of the next page from the ``Link`` header, if any.
    """

    status: int
    data: Any
    next_url: str | None = None


class Client(Protocol):
    """Sends one GitHub API request; tests replace it with a fake."""

    def request(
        self, method: str, url: str, body: Mapping[str, Any] | None = None
    ) -> Response:
        """Send a request to an API path or a full URL from a ``Link`` header."""


class UrllibClient:
    """GitHub REST client based on the standard library.

    Args:
        token: Token for the ``Authorization`` header.
        api_url: API base URL, ``GITHUB_API_URL`` in Actions.
    """

    def __init__(self, token: str, api_url: str = DEFAULT_API_URL) -> None:
        self._token = token
        self._api_url = api_url.rstrip("/")

    def request(
        self, method: str, url: str, body: Mapping[str, Any] | None = None
    ) -> Response:
        """Send a request; raise :class:`ApiError` for an HTTP or network error."""
        full_url = url if url.startswith(f"{self._api_url}/") else self._api_url + url
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            full_url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "issue-validation",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                link = NEXT_LINK.search(response.headers.get("Link") or "")
                return Response(
                    response.status,
                    json.loads(raw) if raw else None,
                    link[1] if link else None,
                )
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == "DELETE":
                return Response(404, None)
            raise ApiError(_http_error_message(method, url, error)) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ApiError(f"GitHub API {method} {url} failed: {error}") from error


def _http_error_message(method: str, url: str, error: urllib.error.HTTPError) -> str:
    try:
        detail = json.loads(error.read() or b"{}").get("message", "")
    except (ValueError, AttributeError):
        detail = ""
    message = f"GitHub API {method} {url} failed with HTTP {error.code}"
    if detail:
        message += f": {detail}"
    if error.code in (403, 429) and error.headers.get("x-ratelimit-remaining") == "0":
        message += " (rate limit exceeded; rerun the job later)"
    elif error.code in (401, 403):
        message += " (check the job permissions: issues: write)"
    return message


def get_all(client: Client, path: str) -> list[Any]:
    """Read every page of a list endpoint."""
    separator = "&" if "?" in path else "?"
    url: str | None = f"{path}{separator}per_page={PAGE_SIZE}"
    items: list[Any] = []
    while url is not None:
        response = client.request("GET", url)
        if not isinstance(response.data, list):
            raise ApiError(f"GitHub API GET {url} did not return a list")
        items += response.data
        url = response.next_url
    return items


@dataclass(frozen=True)
class Event:
    """The fields of an ``issues`` event the runner needs.

    Attributes:
        repository: ``owner/name``.
        number: Issue number.
        sender: Login of the account that caused the event.
        is_pull_request: Whether the event belongs to a pull request.
    """

    repository: str
    number: int
    sender: str
    is_pull_request: bool


def read_event(path: Path) -> Event:
    """Read an ``issues`` event file.

    Raises:
        ValueError: If the file is not an issue event.
    """
    event = json.loads(path.read_text(encoding="utf-8"))
    issue = event.get("issue") if isinstance(event, dict) else None
    if not isinstance(issue, dict):
        raise ValueError("the event file contains no issue")  # noqa: TRY004 - input error
    repository = (event.get("repository") or {}).get("full_name")
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.match(repository):
        raise ValueError(f"invalid repository in the event file: {repository!r}")
    number = issue.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError(f"invalid issue number in the event file: {number!r}")
    return Event(
        repository=repository,
        number=number,
        sender=(event.get("sender") or {}).get("login", ""),
        is_pull_request="pull_request" in issue,
    )


@dataclass
class LabelPlan:
    """The label changes for one run.

    Attributes:
        add: Labels to add.
        remove: Labels to remove.
        needs_info_by_validator: Whether ``status:needs-info`` is set by the validator afterwards.
    """

    add: list[str] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)
    needs_info_by_validator: bool = False

    def apply(self, labels: Sequence[str]) -> tuple[str, ...]:
        """Return ``labels`` after the plan."""
        kept = [label for label in labels if label not in self.remove]
        return tuple(kept + [label for label in self.add if label not in kept])


def plan_labels(
    labels: Sequence[str],
    findings: Sequence[Any],
    initial_status: str,
    needs_info_by_validator: bool,
) -> LabelPlan:
    """Decide the status label changes.

    Args:
        labels: Current labels.
        findings: Findings for the current labels.
        initial_status: Status value of a new issue, for example ``triage``.
        needs_info_by_validator: Whether the validator set ``status:needs-info`` earlier.

    Returns:
        The plan. With findings, an issue without status or in the initial status moves to
        ``status:needs-info``; issues in a planned status keep it, so the validator never
        undoes a maintainer's decision. Without findings, a ``status:needs-info`` set by the
        validator is replaced by the initial status. A missing status alone is not missing
        information: such an issue gets the initial status.
    """
    initial = f"status:{initial_status}"
    states = validator.group_labels(labels, "status")
    by_validator = needs_info_by_validator and NEEDS_INFO in labels
    problems = [
        finding
        for finding in findings
        if not (finding.rule == "ISSUE-R2" and not states)
    ]
    if problems:
        if not by_validator and set(states) <= {initial}:
            return LabelPlan([NEEDS_INFO], [initial] if states else [], True)
        return LabelPlan(needs_info_by_validator=by_validator)
    if by_validator:
        add = [initial] if states == [NEEDS_INFO] else []
        return LabelPlan(add, [NEEDS_INFO], False)
    return LabelPlan([initial] if not states else [])


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def comment_body(findings: Sequence[Any], needs_info_by_validator: bool) -> str:
    """Render the validator comment."""
    lines = [MARKER]
    if needs_info_by_validator:
        lines.append(NEEDS_INFO_MARKER)
    lines.append("## Issue Validation")
    lines.append("")
    if not findings:
        lines.append("All issue rules pass.")
        return "\n".join(lines) + "\n"
    lines += [
        (
            "This issue does not meet the issue rules of this repository "
            "(`.project/workflow.yml` and the issue forms):"
        ),
        "",
        "| Rule | Problem | Fix |",
        "|---|---|---|",
    ]
    lines += [
        f"| {finding.rule} | {_cell(finding.message)} | {_cell(finding.hint)} |"
        for finding in findings
    ]
    lines.append("")
    if needs_info_by_validator:
        lines.append(
            f"The validator set `{NEEDS_INFO}`. It restores the previous status once every "
            "rule passes."
        )
        lines.append("")
    lines.append(
        "The rules are described in `docs/governance/issue-management.md`. This comment is "
        "updated on every change of the issue."
    )
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class Result:
    """What a run found and did.

    Attributes:
        findings: Findings after the label changes.
        plan: The label changes.
        comment: ``created``, ``updated``, ``unchanged``, ``resolved`` or ``none``.
        skipped: Reason why the issue was not validated, or ``None``.
    """

    findings: tuple[Any, ...] = ()
    plan: LabelPlan = field(default_factory=LabelPlan)
    comment: str = "none"
    skipped: str | None = None


def _blockers(
    client: Client, base: str, repository: str
) -> tuple[tuple[str, ...], bool]:
    blockers = get_all(client, f"{base}/dependencies/blocked_by")
    open_refs = []
    for blocker in blockers:
        if not isinstance(blocker, dict) or blocker.get("state") != "open":
            continue
        match = re.search(
            r"repos/([\w.-]+/[\w.-]+)$", blocker.get("repository_url", "")
        )
        prefix = "" if match is None or match[1] == repository else match[1]
        open_refs.append(f"{prefix}#{blocker.get('number')}")
    return tuple(open_refs), bool(blockers)


def run(
    event: Event,
    policy: Any,
    client: Client,
    bot_login: str = DEFAULT_BOT_LOGIN,
    dry_run: bool = False,
) -> Result:
    """Validate the issue of ``event`` and apply the result.

    Args:
        event: The event.
        policy: The policy from ``validator.load_policy``.
        client: GitHub API client.
        bot_login: Login of the account the workflow token acts as.
        dry_run: Read only; report the planned comment and label changes.

    Returns:
        What was found and done.

    Raises:
        ApiError: If a request fails.
    """
    if event.is_pull_request:
        return Result(skipped="the event belongs to a pull request")
    if event.sender == bot_login:
        return Result(skipped=f"the event was sent by {bot_login}")
    base = f"/repos/{event.repository}/issues/{event.number}"
    data = client.request("GET", base).data
    if not isinstance(data, dict):
        raise ApiError(f"GitHub API GET {base} did not return an issue")
    if "pull_request" in data:
        return Result(skipped="the issue is a pull request")
    issue = validator.issue_from_api(data)
    if not issue.is_open:
        return Result(skipped="the issue is closed")

    comments = get_all(client, f"{base}/comments")
    own = next(
        (
            comment
            for comment in comments
            if (comment.get("user") or {}).get("login") == bot_login
            and MARKER in (comment.get("body") or "")
        ),
        None,
    )
    others = tuple(
        comment.get("body") or "" for comment in comments if comment is not own
    )
    open_blockers: tuple[str, ...] | None = None
    has_dependency = False
    if (
        validator.AGENT_READY in issue.labels
        or validator.STATUS_BLOCKED in issue.labels
    ):
        open_blockers, has_dependency = _blockers(client, base, event.repository)
    issue = replace(
        issue,
        open_blockers=open_blockers,
        has_blocker_dependency=has_dependency,
        comments=others,
    )

    findings = validator.check_issue(issue, policy)
    previous_flag = own is not None and NEEDS_INFO_MARKER in (own.get("body") or "")
    plan = plan_labels(issue.labels, findings, policy.initial_status, previous_flag)
    labels_after = plan.apply(issue.labels)
    if labels_after != issue.labels:
        issue = replace(issue, labels=labels_after)
        findings = validator.check_issue(issue, policy)

    # The comment is written before the labels: it records whether the validator set
    # status:needs-info, so an interrupted run cannot leave that label behind as human-set.
    body = comment_body(findings, plan.needs_info_by_validator)
    if own is None:
        action = "created" if findings else "none"
    elif own.get("body") == body:
        action = "unchanged"
    else:
        action = "updated" if findings else "resolved"
    if not dry_run:
        if action == "created":
            client.request("POST", f"{base}/comments", {"body": body})
        elif action in ("updated", "resolved"):
            client.request(
                "PATCH",
                f"/repos/{event.repository}/issues/comments/{own['id']}",
                {"body": body},
            )
        if plan.add:
            client.request("POST", f"{base}/labels", {"labels": plan.add})
        for label in plan.remove:
            client.request(
                "DELETE", f"{base}/labels/{urllib.parse.quote(label, safe='')}"
            )
    return Result(tuple(findings), plan, action)


def report(result: Result, number: int, dry_run: bool) -> None:
    """Print the result and append it to the GitHub job summary.

    Messages contain only label names, form headings and issue numbers, never issue text.
    """
    if result.skipped is not None:
        lines = [f"Issue #{number} skipped: {result.skipped}"]
    else:
        prefix = "planned " if dry_run else ""
        lines = [
            f"error: [{finding.rule}] {finding.message}\n  fix: {finding.hint}"
            for finding in result.findings
        ]
        lines.append(
            f"Issue #{number}: {len(result.findings)} problem(s); "
            f"{prefix}comment {result.comment}; "
            f"{prefix}labels +{result.plan.add} -{result.plan.remove}"
        )
    print("\n".join(lines))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Issue Validation\n\n" + "\n\n".join(lines) + "\n")


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--event",
        type=Path,
        default=os.environ.get("GITHUB_EVENT_PATH"),
        help="issues event JSON file (default: GITHUB_EVENT_PATH)",
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root")
    parser.add_argument(
        "--bot-login",
        default=DEFAULT_BOT_LOGIN,
        help=f"login of the workflow token's account (default: {DEFAULT_BOT_LOGIN})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="read only; print the planned changes"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, client: Client | None = None) -> int:
    """Run the command line interface; ``client`` replaces the HTTP client in tests."""
    args = _parse_arguments(argv)
    try:
        if args.event is None:
            raise ValueError("pass --event or set GITHUB_EVENT_PATH")
        event = read_event(args.event)
        policy = validator.load_policy(args.repo)
        if client is None:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise ValueError("GITHUB_TOKEN is not set")
            client = UrllibClient(
                token, os.environ.get("GITHUB_API_URL") or DEFAULT_API_URL
            )
    except (OSError, KeyError, ValueError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    try:
        result = run(event, policy, client, args.bot_login, args.dry_run)
    except ApiError as error:
        print(
            f"error: {error}\nIssue #{event.number} was not validated.", file=sys.stderr
        )
        return 1
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    report(result, event.number, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
