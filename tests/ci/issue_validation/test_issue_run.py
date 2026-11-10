"""Tests for scripts/ci/issue_validation/run.py with a fake GitHub API."""

from __future__ import annotations

import email.message
import http.server
import importlib.util
import io
import json
import sys
import threading
import urllib.error
from pathlib import Path
from typing import Any, ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "issue_run_under_test", ROOT / "scripts" / "ci" / "issue_validation" / "run.py"
)
run_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = run_module
_spec.loader.exec_module(run_module)
validator = run_module.validator

POLICY = validator.load_policy(ROOT)
REPOSITORY = "octo/project"
BOT = run_module.DEFAULT_BOT_LOGIN
BASE = f"/repos/{REPOSITORY}/issues/7"


def filled_body(issue_type: str, *, skip: tuple[str, ...] = ()) -> str:
    return "\n".join(
        f"### {f.label}\n\nSome {f.field_id}.\n"
        for f in POLICY.forms[issue_type]
        if f.field_id not in skip
    )


class FakeGitHub:
    """In-memory issue, comments and dependencies behind the ``Client`` protocol."""

    def __init__(
        self,
        labels: list[str],
        body: str,
        *,
        state: str = "open",
        comments: list[dict[str, Any]] | None = None,
        blockers: list[dict[str, Any]] | None = None,
        fail: tuple[str, str] | None = None,
    ) -> None:
        self.issue: dict[str, Any] = {
            "number": 7,
            "state": state,
            "body": body,
            "labels": [{"name": name} for name in labels],
        }
        self.comments = comments or []
        self.blockers = blockers or []
        self.fail = fail
        self.calls: list[tuple[str, str]] = []
        self.writes: list[tuple[str, str, Any]] = []

    @property
    def labels(self) -> list[str]:
        return [label["name"] for label in self.issue["labels"]]

    def request(self, method: str, url: str, body: Any = None) -> Any:
        self.calls.append((method, url))
        path = url.split("?", 1)[0]
        if self.fail is not None and (method, path) == self.fail:
            raise run_module.ApiError(
                f"GitHub API {method} {path} failed with HTTP 403"
            )
        if method != "GET":
            self.writes.append((method, path, body))
        if (method, path) == ("GET", BASE):
            return run_module.Response(200, json.loads(json.dumps(self.issue)))
        if (method, path) == ("GET", f"{BASE}/comments"):
            return run_module.Response(200, list(self.comments))
        if (method, path) == ("GET", f"{BASE}/dependencies/blocked_by"):
            return run_module.Response(200, list(self.blockers))
        if (method, path) == ("POST", f"{BASE}/comments"):
            comment = {"id": 100 + len(self.comments), "user": {"login": BOT}, **body}
            self.comments.append(comment)
            return run_module.Response(201, comment)
        if method == "PATCH" and path.startswith(
            f"/repos/{REPOSITORY}/issues/comments/"
        ):
            comment_id = int(path.rsplit("/", 1)[1])
            comment = next(c for c in self.comments if c["id"] == comment_id)
            comment.update(body)
            return run_module.Response(200, comment)
        if (method, path) == ("POST", f"{BASE}/labels"):
            self.issue["labels"] += [
                {"name": name} for name in body["labels"] if name not in self.labels
            ]
            return run_module.Response(200, self.issue["labels"])
        if method == "DELETE" and path.startswith(f"{BASE}/labels/"):
            name = path.rsplit("/", 1)[1].replace("%3A", ":")
            self.issue["labels"] = [
                label for label in self.issue["labels"] if label["name"] != name
            ]
            return run_module.Response(200, self.issue["labels"])
        raise AssertionError(f"unexpected request {method} {url}")


def event(sender: str = "octocat", **issue: Any) -> Any:
    return run_module.Event(REPOSITORY, 7, sender, issue.get("pull_request", False))


def own_comments(api: FakeGitHub) -> list[dict[str, Any]]:
    return [c for c in api.comments if c["user"]["login"] == BOT]


def validate(api: FakeGitHub, **kwargs: Any) -> Any:
    return run_module.run(event(), POLICY, api, **kwargs)


# §21.6 and the comment lifecycle


def test_bug_without_reproduction_gets_needs_info_and_a_comment() -> None:
    api = FakeGitHub(
        ["type:bug", "status:triage"], filled_body("bug", skip=("reproduction",))
    )
    result = validate(api)
    assert result.comment == "created"
    assert api.labels == ["type:bug", "status:needs-info"]
    (comment,) = own_comments(api)
    assert comment["body"].startswith(run_module.MARKER)
    assert run_module.NEEDS_INFO_MARKER in comment["body"]
    assert "| ISSUE-R11 | section 'Steps to Reproduce' is missing |" in comment["body"]


def test_comment_is_written_before_the_labels() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    validate(api)
    assert [method for method, _, _ in api.writes] == ["POST", "POST", "DELETE"]
    assert api.writes[0][1] == f"{BASE}/comments"


def test_fixed_issue_resolves_the_comment_and_restores_triage() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    validate(api)
    api.issue["body"] = filled_body("bug")
    result = validate(api)
    assert result.comment == "resolved"
    assert api.labels == ["type:bug", "status:triage"]
    (comment,) = own_comments(api)
    assert "All issue rules pass." in comment["body"]
    assert run_module.NEEDS_INFO_MARKER not in comment["body"]


def test_unchanged_issue_does_not_write() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    validate(api)
    api.writes.clear()
    result = validate(api)
    assert result.comment == "unchanged"
    assert api.writes == []


def test_changed_findings_update_the_one_comment() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    validate(api)
    api.issue["body"] = filled_body("bug", skip=("severity",))
    result = validate(api)
    assert result.comment == "updated"
    (comment,) = own_comments(api)
    assert "'Severity'" in comment["body"]
    assert "'Summary'" not in comment["body"]


def test_valid_issue_without_comment_is_left_alone() -> None:
    api = FakeGitHub(["type:task", "status:triage"], filled_body("task"))
    result = validate(api)
    assert (result.findings, result.comment) == ((), "none")
    assert api.writes == []


def test_issue_created_without_labels_gets_needs_info() -> None:
    api = FakeGitHub([], "Created with gh issue create.")
    result = validate(api)
    assert api.labels == ["status:needs-info"]
    assert [f.rule for f in result.findings] == ["ISSUE-R1"]


def test_missing_status_alone_gets_the_initial_status() -> None:
    api = FakeGitHub(["type:task"], filled_body("task"))
    result = validate(api)
    assert api.labels == ["type:task", "status:triage"]
    assert (result.findings, result.comment) == ((), "none")


# status:needs-info ownership


def test_needs_info_set_by_a_human_is_not_removed() -> None:
    api = FakeGitHub(["type:bug", "status:needs-info"], filled_body("bug"))
    result = validate(api)
    assert api.labels == ["type:bug", "status:needs-info"]
    assert result.comment == "none"


def test_flag_in_a_comment_of_another_user_is_ignored() -> None:
    spoofed = {
        "id": 1,
        "user": {"login": "mallory"},
        "body": f"{run_module.MARKER}\n{run_module.NEEDS_INFO_MARKER}\n",
    }
    api = FakeGitHub(
        ["type:bug", "status:needs-info"], filled_body("bug"), comments=[spoofed]
    )
    validate(api)
    assert api.labels == ["type:bug", "status:needs-info"]
    assert api.writes == []


def test_planned_issue_keeps_its_status() -> None:
    api = FakeGitHub(["type:bug", "status:ready", "priority:high"], filled_body("bug"))
    result = validate(api)
    assert api.labels == ["type:bug", "status:ready", "priority:high"]
    assert [f.rule for f in result.findings] == ["ISSUE-R5"]
    assert result.comment == "created"
    assert run_module.NEEDS_INFO_MARKER not in own_comments(api)[0]["body"]


def test_needs_info_removed_by_a_human_is_not_set_again_while_planned() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    validate(api)
    api.issue["labels"] = [{"name": "type:bug"}, {"name": "status:ready"}]
    validate(api)
    assert api.labels == ["type:bug", "status:ready"]
    assert run_module.NEEDS_INFO_MARKER not in own_comments(api)[0]["body"]


def test_resolved_with_a_second_status_removes_only_needs_info() -> None:
    plan = run_module.plan_labels(
        ["type:bug", "status:needs-info", "status:ready"], [], "triage", True
    )
    assert (plan.add, plan.remove) == ([], ["status:needs-info"])


# Dependencies


def test_agent_ready_with_open_blocker_is_reported() -> None:
    blockers = [
        {
            "number": 3,
            "state": "open",
            "repository_url": f"https://x/repos/{REPOSITORY}",
        },
        {
            "number": 4,
            "state": "closed",
            "repository_url": f"https://x/repos/{REPOSITORY}",
        },
        {"number": 5, "state": "open", "repository_url": "https://x/repos/octo/other"},
    ]
    api = FakeGitHub(
        ["type:task", "status:triage", "agent:ready"],
        filled_body("task"),
        blockers=blockers,
    )
    result = validate(api)
    assert [f.rule for f in result.findings] == ["ISSUE-R8"]
    assert "#3, octo/other#5" in result.findings[0].message
    assert api.labels == ["type:task", "agent:ready", "status:needs-info"]


def test_dependencies_are_read_only_when_a_rule_needs_them() -> None:
    api = FakeGitHub(["type:task", "status:triage"], filled_body("task"))
    validate(api)
    assert all("dependencies" not in url for _, url in api.calls)


def test_blocked_issue_with_closed_dependency_names_its_blocker() -> None:
    api = FakeGitHub(
        ["type:task", "status:blocked", "priority:low", "area:api"],
        filled_body("task"),
        blockers=[{"number": 2, "state": "closed", "repository_url": ""}],
    )
    assert validate(api).findings == ()


def test_blocker_named_in_a_comment_counts() -> None:
    comment = {"id": 1, "user": {"login": "octocat"}, "body": "Waiting for #2."}
    api = FakeGitHub(
        ["type:task", "status:blocked", "priority:low", "area:api"],
        filled_body("task"),
        comments=[comment],
    )
    assert validate(api).findings == ()


# Skips, loop protection and errors


def test_event_of_the_bot_is_skipped() -> None:
    api = FakeGitHub([], "")
    result = run_module.run(event(sender=BOT), POLICY, api)
    assert result.skipped == f"the event was sent by {BOT}"
    assert api.calls == []


def test_pull_request_is_skipped() -> None:
    api = FakeGitHub([], "")
    result = run_module.run(event(pull_request=True), POLICY, api)
    assert result.skipped == "the event belongs to a pull request"
    assert api.calls == []


def test_closed_issue_is_skipped() -> None:
    api = FakeGitHub([], "", state="closed")
    assert validate(api).skipped == "the issue is closed"
    assert api.writes == []


def test_dry_run_does_not_write() -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "")
    result = validate(api, dry_run=True)
    assert result.comment == "created"
    assert result.plan.add == ["status:needs-info"]
    assert api.writes == []


@pytest.mark.parametrize(
    "fail",
    [("GET", BASE), ("GET", f"{BASE}/comments"), ("POST", f"{BASE}/comments")],
)
def test_api_error_fails_the_run(
    fail: tuple[str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    api = FakeGitHub(["type:bug", "status:triage"], "", fail=fail)
    path = write_event(tmp_path)
    assert run_module.main(["--event", str(path), "--repo", str(ROOT)], api) == 1
    error = capsys.readouterr().err
    assert "HTTP 403" in error
    assert "Issue #7 was not validated." in error


def test_pages_are_followed() -> None:
    class Paged:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def request(self, method: str, url: str, body: Any = None) -> Any:
            self.urls.append(url)
            if url.endswith("page=2"):
                return run_module.Response(200, [{"id": 2}])
            return run_module.Response(200, [{"id": 1}], f"{url}&page=2")

    client = Paged()
    assert run_module.get_all(client, "/items") == [{"id": 1}, {"id": 2}]
    assert client.urls == ["/items?per_page=100", "/items?per_page=100&page=2"]


def http_error(code: int, headers: dict[str, str], message: str) -> Any:
    header = email.message.Message()
    for key, value in headers.items():
        header[key] = value
    body = io.BytesIO(json.dumps({"message": message}).encode())
    return urllib.error.HTTPError("https://api.github.com/x", code, "", header, body)


def test_rate_limit_error_names_the_rate_limit() -> None:
    error = http_error(403, {"x-ratelimit-remaining": "0"}, "API rate limit exceeded")
    message = run_module._http_error_message("GET", "/x", error)
    assert message == (
        "GitHub API GET /x failed with HTTP 403: API rate limit exceeded "
        "(rate limit exceeded; rerun the job later)"
    )


def test_permission_error_names_the_permission() -> None:
    error = http_error(403, {}, "Resource not accessible by integration")
    assert "issues: write" in run_module._http_error_message("POST", "/x", error)


# Event file and command line


def write_event(tmp_path: Path, **overrides: Any) -> Path:
    data: dict[str, Any] = {
        "action": "opened",
        "issue": {"number": 7, "title": "$(rm -rf /)", "body": "`whoami`"},
        "repository": {"full_name": REPOSITORY},
        "sender": {"login": "octocat"},
    }
    data.update(overrides)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_read_event(tmp_path: Path) -> None:
    assert run_module.read_event(write_event(tmp_path)) == run_module.Event(
        REPOSITORY, 7, "octocat", False
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"issue": None}, "contains no issue"),
        ({"repository": {"full_name": "../x"}}, "invalid repository"),
        ({"repository": {"full_name": "octo/.."}}, "invalid repository"),
        ({"issue": {"number": "7"}}, "invalid issue number"),
    ],
)
def test_invalid_event_is_rejected(
    tmp_path: Path, overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        run_module.read_event(write_event(tmp_path, **overrides))


def test_main_reports_to_the_job_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    api = FakeGitHub(["type:bug", "status:triage"], "")
    path = write_event(tmp_path)
    assert run_module.main(["--event", str(path), "--repo", str(ROOT)], api) == 0
    output = capsys.readouterr().out
    assert "Issue #7: 8 problem(s); comment created" in output
    assert "[ISSUE-R11]" in summary.read_text(encoding="utf-8")


def test_main_without_token_is_an_input_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    path = write_event(tmp_path)
    assert run_module.main(["--event", str(path), "--repo", str(ROOT)]) == 2
    assert "GITHUB_TOKEN is not set" in capsys.readouterr().err


def test_main_without_event_is_an_input_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    assert run_module.main(["--repo", str(ROOT)], FakeGitHub([], "")) == 2
    assert "pass --event" in capsys.readouterr().err


# UrllibClient against a local HTTP server


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves two comment pages, accepts writes and rejects one path with 403."""

    requests: ClassVar[list[tuple[str, str, str, Any]]] = []

    def _send(
        self, status: int, data: Any, headers: dict[str, str] | None = None
    ) -> None:
        raw = b"" if data is None else json.dumps(data).encode()
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        type(self).requests.append(
            (method, self.path, self.headers.get("Authorization", ""), body)
        )
        if self.path == "/api/forbidden":
            self._send(403, {"message": "Resource not accessible by integration"})
        elif self.path == "/api/items?per_page=100":
            port = self.server.server_address[1]
            link = (
                f'<http://127.0.0.1:{port}/api/items?per_page=100&page=2>; rel="next"'
            )
            self._send(200, [1], {"Link": link})
        elif self.path == "/api/items?per_page=100&page=2":
            self._send(200, [2])
        elif method == "DELETE":
            self._send(404, {"message": "Label does not exist"})
        else:
            self._send(201, {"ok": True})

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def log_message(self, *args: Any) -> None:
        """Keep the test output clean."""


@pytest.fixture
def api_url() -> Any:
    _Handler.requests = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/api"
    server.shutdown()
    server.server_close()


def test_urllib_client_follows_pages_and_sends_the_token(api_url: str) -> None:
    client = run_module.UrllibClient("test-token", api_url)
    assert run_module.get_all(client, "/items") == [1, 2]
    assert [path for _, path, _, _ in _Handler.requests] == [
        "/api/items?per_page=100",
        "/api/items?per_page=100&page=2",
    ]
    assert {auth for _, _, auth, _ in _Handler.requests} == {"Bearer test-token"}


def test_urllib_client_sends_json_and_accepts_a_missing_label(api_url: str) -> None:
    client = run_module.UrllibClient("test-token", api_url)
    assert client.request("POST", "/labels", {"labels": ["a"]}).data == {"ok": True}
    assert client.request("DELETE", "/labels/a").status == 404
    assert _Handler.requests[0][3] == {"labels": ["a"]}


def test_urllib_client_raises_for_http_errors(api_url: str) -> None:
    client = run_module.UrllibClient("test-token", api_url)
    with pytest.raises(run_module.ApiError, match="HTTP 403: Resource not accessible"):
        client.request("GET", "/forbidden")


def test_urllib_client_raises_for_network_errors() -> None:
    client = run_module.UrllibClient("test-token", "http://127.0.0.1:9")
    with pytest.raises(run_module.ApiError, match="failed"):
        client.request("GET", "/x")
