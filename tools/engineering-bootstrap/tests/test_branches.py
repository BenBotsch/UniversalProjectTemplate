"""Tests for the branch resource."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from conftest import FakeRepository

from engineering_bootstrap.engine import Action, Engine
from engineering_bootstrap.github import GitHubClient
from engineering_bootstrap.resources.branches import BranchResource, BranchSpec, spec_from_config

SPEC = BranchSpec(default_branch="main", development_branch="develop")


@pytest.fixture
def client(fake_repository: FakeRepository) -> Iterator[GitHubClient]:
    with GitHubClient("token", transport=fake_repository.transport, sleep=lambda _: None) as c:
        yield c


def run(client: GitHubClient, *, apply: bool, create: bool = True) -> dict[str, tuple[Action, str]]:
    resource = BranchResource(client, "octo/demo", SPEC, create_development_branch=create)
    changes = Engine([resource]).run(apply=apply)
    return {change.key: (change.action, change.reason) for change in changes}


def test_spec_comes_from_project_yml() -> None:
    project = {"repository": {"default_branch": "trunk", "development_branch": "next"}}

    assert spec_from_config(project) == BranchSpec("trunk", "next")


def test_missing_develop_is_created_from_main(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    planned = run(client, apply=False)

    assert planned["main"] == (Action.NOOP, "exists")
    assert planned["develop"][0] is Action.CREATE
    assert "from 'main' at aaaaaaaaaaaa" in planned["develop"][1]
    assert fake_repository.writes() == []

    run(client, apply=True)

    assert fake_repository.refs["develop"] == fake_repository.refs["main"]
    assert fake_repository.writes() == [("POST", "/repos/octo/demo/git/refs")]


def test_second_run_is_noop(client: GitHubClient, fake_repository: FakeRepository) -> None:
    run(client, apply=True)
    fake_repository.requests.clear()

    result = run(client, apply=True)

    assert {action for action, _ in result.values()} == {Action.NOOP}
    assert fake_repository.writes() == []


def test_existing_develop_is_never_moved(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    fake_repository.refs["develop"] = "b" * 40

    result = run(client, apply=True)

    assert result["develop"] == (Action.NOOP, "exists; left unchanged")
    assert fake_repository.refs["develop"] == "b" * 40
    assert fake_repository.writes() == []


def test_develop_created_meanwhile_is_kept(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    resource = BranchResource(client, "octo/demo", SPEC)
    planned = resource.diff(resource.read_actual(), resource.desired())
    fake_repository.refs["develop"] = "c" * 40

    resource.apply(next(c for c in planned if c.action is Action.CREATE))

    assert fake_repository.refs["develop"] == "c" * 40


def test_disabled_switch_skips_develop(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    result = run(client, apply=True, create=False)

    assert result["develop"] == (Action.SKIPPED, "disabled by bootstrap.create_develop_branch")
    assert ("GET", "/repos/octo/demo/git/ref/heads/develop") not in fake_repository.requests
    assert "develop" not in fake_repository.refs


def test_empty_repository_fails_with_hint(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    fake_repository.empty = True

    result = run(client, apply=True)

    assert result["main"][0] is Action.FAILED
    assert "repository has no commits" in result["main"][1]
    assert result["develop"] == (Action.FAILED, "missing, but cannot be created without 'main'")
    assert fake_repository.writes() == []


def test_missing_default_branch_fails(
    client: GitHubClient, fake_repository: FakeRepository
) -> None:
    fake_repository.refs = {"trunk": "d" * 40}

    result = run(client, apply=False)

    assert result["main"] == (
        Action.FAILED,
        "default branch does not exist; create it or fix repository.default_branch",
    )
    assert result["develop"][0] is Action.FAILED
