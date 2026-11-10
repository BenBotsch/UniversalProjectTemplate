"""Shared fixtures: a minimal project configuration with its own small schemas."""

from __future__ import annotations

import json
from pathlib import Path
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
