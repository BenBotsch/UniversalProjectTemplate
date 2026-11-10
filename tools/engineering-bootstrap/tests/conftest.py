"""Shared fixtures: a minimal project configuration with its own small schemas."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx
import pytest

from engineering_bootstrap.config import CONFIG_NAMES

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "name"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "name": {"type": "string", "minLength": 1},
    },
}


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Return a ``.project`` directory in which every file is valid."""
    directory = tmp_path / ".project"
    schemas = directory / "schemas"
    schemas.mkdir(parents=True)
    for name in CONFIG_NAMES:
        (schemas / f"{name}-1.0.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        (directory / f"{name}.yml").write_text(
            f'schema_version: "1.0"\nname: "{name}"\n', encoding="utf-8"
        )
    return directory


class FakeGitHub:
    """Stateful stand-in for the GitHub label and search endpoints of one repository.

    Attributes:
        labels: Current labels by name, in creation order.
        usage: Number of issues and pull requests per label name, for the search endpoint.
        requests: ``(method, path)`` of every request, for assertions.
        fail_post_with: If set, POST requests answer with this status code once.
    """

    def __init__(self, repo: str, labels: list[dict[str, str]] | None = None) -> None:
        self.repo = repo
        self.labels: dict[str, dict[str, str]] = {
            label["name"]: dict(label) for label in labels or []
        }
        self.usage: dict[str, int] = {}
        self.requests: list[tuple[str, str]] = []
        self.fail_post_with: int | None = None
        self.page_size = 2

    @property
    def transport(self) -> httpx.MockTransport:
        """Return an httpx transport that serves this fake."""
        return httpx.MockTransport(self)

    def _find(self, name: str) -> str | None:
        return next((key for key in self.labels if key.lower() == name.lower()), None)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode().split("?")[0]
        self.requests.append((request.method, path))
        base = f"/repos/{self.repo}/labels"
        if path == "/search/issues":
            query = request.url.params["q"]
            name = query.split('label:"', 1)[1].rstrip('"')
            return httpx.Response(200, json={"total_count": self.usage.get(name, 0), "items": []})
        if path == base and request.method == "GET":
            return self._list(request)
        if path == base and request.method == "POST":
            if self.fail_post_with is not None:
                status, self.fail_post_with = self.fail_post_with, None
                return httpx.Response(status, json={"message": "Validation Failed"})
            body = json.loads(request.content)
            if self._find(body["name"]) is not None:
                return httpx.Response(422, json={"message": "Validation Failed"})
            self.labels[body["name"]] = body
            return httpx.Response(201, json=body)
        if path.startswith(base + "/"):
            name = unquote(path[len(base) + 1 :])
            key = self._find(name)
            if key is None:
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "DELETE":
                del self.labels[key]
                return httpx.Response(204)
            if request.method == "PATCH":
                body = json.loads(request.content)
                label = self.labels.pop(key)
                label["name"] = body.get("new_name", label["name"])
                label.update({k: body[k] for k in ("color", "description") if k in body})
                self.labels[label["name"]] = label
                return httpx.Response(200, json=label)
        return httpx.Response(404, json={"message": "Not Found"})

    def _list(self, request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        items = list(self.labels.values())
        chunk = items[(page - 1) * self.page_size : page * self.page_size]
        headers = {}
        if page * self.page_size < len(items):
            next_url = request.url.copy_merge_params({"page": str(page + 1)})
            headers["link"] = f'<{next_url}>; rel="next"'
        return httpx.Response(200, json=chunk, headers=headers)


@pytest.fixture
def fake_github() -> FakeGitHub:
    """Return a fake GitHub with an empty repository ``octo/demo``."""
    return FakeGitHub("octo/demo")


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MERGE_FIELDS = ("allow_squash_merge", "allow_merge_commit", "allow_rebase_merge")


@pytest.fixture
def template_config_dir(tmp_path: Path) -> Path:
    """Return a copy of the template's own ``.project`` directory."""
    target = tmp_path / ".project"
    shutil.copytree(REPOSITORY_ROOT / ".project", target)
    return target


class FakeRepository:
    """Stateful stand-in for the branch, settings, Actions and security endpoints of one repo.

    The initial state is a public repository created from the template: only ``main`` exists,
    and the settings have GitHub's defaults.

    Attributes:
        settings: Body of ``GET /repos/{repo}``.
        refs: Head commit per branch name.
        empty: The repository has no commits; git endpoints answer 409.
        actions, selected_actions, workflow: Bodies of the Actions permission endpoints.
        vulnerability_alerts, security_fixes, vulnerability_reporting: Security switches.
        rulesets_available: False answers the rulesets endpoints like GitHub Free does for a
            private repository.
        rulesets: Rulesets by ID, as ``GET /rulesets/{id}`` returns them.
        check_runs: GitHub App ID of the latest run per ``(branch, check name)``.
        requests: ``(method, path)`` of every request, for assertions.
    """

    def __init__(self, repo: str) -> None:
        self.repo = repo
        self.settings: dict[str, Any] = {
            "full_name": repo,
            "visibility": "public",
            "private": False,
            "permissions": {"admin": True, "push": True, "pull": True},
            "default_branch": "main",
            "description": None,
            "topics": [],
            "has_issues": True,
            "has_discussions": False,
            "has_wiki": True,
            "is_template": False,
            "delete_branch_on_merge": False,
            "allow_squash_merge": True,
            "allow_merge_commit": True,
            "allow_rebase_merge": True,
            "security_and_analysis": {
                "secret_scanning": {"status": "disabled"},
                "secret_scanning_push_protection": {"status": "disabled"},
            },
        }
        self.refs: dict[str, str] = {"main": "a" * 40}
        self.empty = False
        self.actions: dict[str, Any] = {"enabled": True, "allowed_actions": "all"}
        self.selected_actions: dict[str, Any] = {
            "github_owned_allowed": False,
            "verified_allowed": False,
            "patterns_allowed": [],
        }
        self.workflow: dict[str, Any] = {
            "default_workflow_permissions": "write",
            "can_approve_pull_request_reviews": True,
        }
        self.vulnerability_alerts = False
        self.security_fixes = False
        self.vulnerability_reporting = False
        self.rulesets_available = True
        self.rulesets: dict[int, dict[str, Any]] = {}
        self.check_runs: dict[tuple[str, str], int] = {}
        self.requests: list[tuple[str, str]] = []

    def make_private(self) -> None:
        """Turn the repository into a private one without Advanced Security."""
        self.settings.update(visibility="private", private=True)

    @property
    def transport(self) -> httpx.MockTransport:
        """Return an httpx transport that serves this fake."""
        return httpx.MockTransport(self)

    def writes(self) -> list[tuple[str, str]]:
        """Return the requests that are not GET."""
        return [request for request in self.requests if request[0] != "GET"]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = unquote(request.url.raw_path.decode().split("?")[0])
        method = request.method
        self.requests.append((method, path))
        base = f"/repos/{self.repo}"
        body = json.loads(request.content) if request.content else {}
        if not path.startswith(base):
            return _not_found()
        sub = path[len(base) :]
        if sub == "" and method == "GET":
            return httpx.Response(200, json=self.settings)
        if sub == "" and method == "PATCH":
            return self._patch(body)
        if sub.startswith("/git/"):
            return self._git(method, sub, body)
        if sub == "/topics" and method == "PUT":
            self.settings["topics"] = body["names"]
            return httpx.Response(200, json=body)
        if sub == "/actions/permissions":
            return _json_endpoint(method, self.actions, body)
        if sub == "/actions/permissions/selected-actions":
            if self.actions["allowed_actions"] != "selected":
                return httpx.Response(409, json={"message": "allowed_actions is not selected"})
            return _json_endpoint(method, self.selected_actions, body)
        if sub == "/actions/permissions/workflow":
            return _json_endpoint(method, self.workflow, body)
        if sub == "/vulnerability-alerts":
            if method == "GET":
                return httpx.Response(204) if self.vulnerability_alerts else _not_found()
            self.vulnerability_alerts = method == "PUT"
            return httpx.Response(204)
        if sub == "/automated-security-fixes":
            if method == "GET":
                return httpx.Response(200, json={"enabled": self.security_fixes, "paused": False})
            if method == "PUT" and not self.vulnerability_alerts:
                return httpx.Response(422, json={"message": "Vulnerability alerts are disabled"})
            self.security_fixes = method == "PUT"
            return httpx.Response(204)
        if sub == "/private-vulnerability-reporting":
            if self.settings["visibility"] != "public":
                return httpx.Response(422, json={"message": "only for public repositories"})
            if method == "GET":
                return httpx.Response(200, json={"enabled": self.vulnerability_reporting})
            self.vulnerability_reporting = method == "PUT"
            return httpx.Response(204)
        if sub == "/rulesets" or sub.startswith("/rulesets/"):
            return self._rulesets(method, sub, body)
        if sub.startswith("/commits/") and sub.endswith("/check-runs"):
            branch = sub[len("/commits/") : -len("/check-runs")]
            if branch not in self.refs:
                return httpx.Response(422, json={"message": f"No commit found for SHA: {branch}"})
            app_id = self.check_runs.get((branch, request.url.params["check_name"]))
            runs = [] if app_id is None else [{"name": "x", "app": {"id": app_id}}]
            return httpx.Response(200, json={"total_count": len(runs), "check_runs": runs})
        return _not_found()

    def add_ruleset(self, ruleset: dict[str, Any]) -> int:
        """Store a ruleset as GitHub would and return its ID.

        GitHub adds parameters with default values, which a comparison must ignore.
        """
        stored = copy.deepcopy(ruleset)
        for rule in stored.get("rules", []):
            if rule["type"] == "pull_request":
                rule["parameters"].setdefault("automatic_copilot_code_review_enabled", False)
        ruleset_id = stored.get("id") or max(self.rulesets, default=0) + 1
        stored.update(id=ruleset_id, source_type="Repository", source=self.repo)
        self.rulesets[ruleset_id] = stored
        return ruleset_id

    def _rulesets(self, method: str, sub: str, body: dict[str, Any]) -> httpx.Response:
        if not self.rulesets_available:
            message = "Upgrade to GitHub Pro or make this repository public to enable this feature."
            return httpx.Response(403, json={"message": message})
        if sub == "/rulesets" and method == "GET":
            summaries = [
                {key: r[key] for key in ("id", "name", "target", "source_type", "enforcement")}
                for r in self.rulesets.values()
            ]
            return httpx.Response(200, json=summaries)
        if sub == "/rulesets" and method == "POST":
            if any(r["name"] == body["name"] for r in self.rulesets.values()):
                return httpx.Response(422, json={"message": "Name must be unique"})
            return httpx.Response(201, json=self.rulesets[self.add_ruleset(body)])
        ruleset_id = int(sub[len("/rulesets/") :])
        if ruleset_id not in self.rulesets:
            return _not_found()
        if method == "GET":
            return httpx.Response(200, json=self.rulesets[ruleset_id])
        if method == "PUT":
            self.add_ruleset({**body, "id": ruleset_id})
            return httpx.Response(200, json=self.rulesets[ruleset_id])
        return _not_found()

    def _patch(self, body: dict[str, Any]) -> httpx.Response:
        analysis = body.pop("security_and_analysis", None)
        if analysis is not None and self.settings["visibility"] != "public":
            return httpx.Response(422, json={"message": "Advanced Security is not purchased"})
        if "default_branch" in body and body["default_branch"] not in self.refs:
            return httpx.Response(422, json={"message": "Validation Failed"})
        merged = {**self.settings, **body}
        if not any(merged[name] for name in MERGE_FIELDS):
            return httpx.Response(422, json={"message": "at least one merge method is required"})
        if analysis is not None:
            merged["security_and_analysis"] = {**merged["security_and_analysis"], **analysis}
        self.settings = merged
        return httpx.Response(200, json=self.settings)

    def _git(self, method: str, sub: str, body: dict[str, Any]) -> httpx.Response:
        if self.empty:
            return httpx.Response(409, json={"message": "Git Repository is empty."})
        prefix = "/git/ref/heads/"
        if method == "GET" and sub.startswith(prefix):
            sha = self.refs.get(sub[len(prefix) :])
            if sha is None:
                return _not_found()
            return httpx.Response(
                200, json={"ref": sub[len("/git/ref/") :], "object": {"sha": sha}}
            )
        if method == "POST" and sub == "/git/refs":
            branch = body["ref"].removeprefix("refs/heads/")
            if branch in self.refs:
                return httpx.Response(422, json={"message": "Reference already exists"})
            self.refs[branch] = body["sha"]
            return httpx.Response(201, json=body)
        return _not_found()


def _json_endpoint(method: str, state: dict[str, Any], body: dict[str, Any]) -> httpx.Response:
    if method == "GET":
        return httpx.Response(200, json=state)
    if method == "PUT":
        state.update(body)
        return httpx.Response(204)
    return _not_found()


def _not_found() -> httpx.Response:
    return httpx.Response(404, json={"message": "Not Found"})


@pytest.fixture
def fake_repository() -> FakeRepository:
    """Return a fake public repository ``octo/demo`` that contains only ``main``."""
    return FakeRepository("octo/demo")
