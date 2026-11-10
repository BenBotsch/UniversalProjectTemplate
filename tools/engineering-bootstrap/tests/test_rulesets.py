"""Tests for the ruleset resource."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeRepository

from engineering_bootstrap.config import load_config
from engineering_bootstrap.engine import RESOURCE_KEY, Action, Change, Engine
from engineering_bootstrap.github import GitHubClient
from engineering_bootstrap.resources.rulesets import (
    RulesetResource,
    RulesetSpec,
    rulesets_from_config,
)

Files = dict[str, dict[str, Any]]
MAIN = "bootstrap-default-branch"
DEVELOP = "bootstrap-development-branch"
TAGS = "bootstrap-release-tags"
GITHUB_ACTIONS_APP = 15368


@pytest.fixture
def files(template_config_dir: Path) -> Files:
    """Return the parsed configuration of the template."""
    return copy.deepcopy(load_config(template_config_dir).files)


@pytest.fixture
def client(fake_repository: FakeRepository) -> Iterator[GitHubClient]:
    fake_repository.refs["develop"] = "b" * 40
    with GitHubClient("token", transport=fake_repository.transport, sleep=lambda _: None) as c:
        yield c


def run(
    client: GitHubClient, files: Files, *, apply: bool, allow_unprotected: bool = False
) -> dict[str, Change]:
    resource = RulesetResource(
        client, "octo/demo", rulesets_from_config(files), allow_unprotected=allow_unprotected
    )
    return {change.key: change for change in Engine([resource]).run(apply=apply)}


def actions(changes: dict[str, Change]) -> dict[str, Action]:
    return {key: change.action for key, change in changes.items()}


def by_name(files: Files) -> dict[str, RulesetSpec]:
    return {spec.name: spec for spec in rulesets_from_config(files)}


def stored(fake: FakeRepository, name: str) -> dict[str, Any]:
    return next(r for r in fake.rulesets.values() if r["name"] == name)


def rule(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any] | None:
    return next((r for r in ruleset["rules"] if r["type"] == rule_type), None)


def test_desired_rulesets_come_from_project_workflow_and_bootstrap(files: Files) -> None:
    specs = by_name(files)

    assert list(specs) == [MAIN, DEVELOP, TAGS]
    assert specs[MAIN].include == ("refs/heads/main",)
    assert specs[DEVELOP].include == ("refs/heads/develop",)
    assert specs[MAIN].required_checks == ("quality-gate",)
    assert specs[MAIN].branch == "main"
    assert [r["type"] for r in specs[MAIN].rules] == [
        "deletion",
        "non_fast_forward",
        "pull_request",
    ]
    review = specs[DEVELOP].rules[2]["parameters"]
    # Solo mode: no approval, but pull requests and resolved conversations stay required.
    assert review["required_approving_review_count"] == 0
    assert review["require_code_owner_review"] is False
    assert review["required_review_thread_resolution"] is True
    # workflow.yml: squash into develop, merge commits for releases; both on both branches.
    assert review["allowed_merge_methods"] == ["merge", "squash"]
    assert specs[TAGS].target == "tag"
    assert specs[TAGS].include == ("refs/tags/v*",)
    assert [r["type"] for r in specs[TAGS].rules] == ["deletion", "update"]


def test_team_mode_requires_an_approval_and_code_owner_review(files: Files) -> None:
    files["bootstrap"]["protection"]["mode"] = "team"

    review = by_name(files)[MAIN].rules[2]["parameters"]

    assert review["required_approving_review_count"] == 1
    assert review["require_code_owner_review"] is True
    assert review["dismiss_stale_reviews_on_push"] is True


def test_bootstrap_schema_before_1_2_is_rejected(files: Files) -> None:
    del files["bootstrap"]["protection"]

    with pytest.raises(ValueError, match=r"migrate it to schema_version 1\.2"):
        rulesets_from_config(files)


def test_without_tag_pattern_tags_are_not_managed(files: Files) -> None:
    del files["bootstrap"]["protection"]["release_tag_pattern"]

    assert by_name(files)[TAGS].skip_reason == "protection.release_tag_pattern not set"


def test_new_repository_is_protected_and_second_run_is_noop(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    pending = {f"{MAIN}:quality-gate", f"{DEVELOP}:quality-gate"}

    planned = run(client, files, apply=False)

    assert fake_repository.writes() == []
    assert actions(planned) == {
        MAIN: Action.CREATE,
        DEVELOP: Action.CREATE,
        TAGS: Action.CREATE,
        **dict.fromkeys(pending, Action.SKIPPED),
    }
    assert "never ran on 'main'; not required yet" in planned[f"{MAIN}:quality-gate"].reason

    applied = run(client, files, apply=True)

    assert all(applied[name].applied for name in (MAIN, DEVELOP, TAGS))
    main = stored(fake_repository, MAIN)
    assert main["enforcement"] == "active"
    assert main["bypass_actors"] == []
    assert main["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    # A check that never reported would block every merge, so it is not required yet.
    assert rule(main, "required_status_checks") is None

    fake_repository.requests.clear()
    second = run(client, files, apply=True)

    assert fake_repository.writes() == []
    assert actions(second) == {
        MAIN: Action.NOOP,
        DEVELOP: Action.NOOP,
        TAGS: Action.NOOP,
        **dict.fromkeys(pending, Action.SKIPPED),
    }


def test_check_is_required_with_its_app_once_it_reported(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    run(client, files, apply=True)
    fake_repository.check_runs[("main", "quality-gate")] = GITHUB_ACTIONS_APP

    result = run(client, files, apply=True)

    assert result[MAIN].action is Action.UPDATE
    assert result[MAIN].reason == "differs in rules"
    assert result[MAIN].applied
    assert f"{MAIN}:quality-gate" not in result
    assert result[f"{DEVELOP}:quality-gate"].action is Action.SKIPPED
    checks = rule(stored(fake_repository, MAIN), "required_status_checks")
    assert checks is not None
    assert checks["parameters"]["required_status_checks"] == [
        {"context": "quality-gate", "integration_id": GITHUB_ACTIONS_APP}
    ]
    assert run(client, files, apply=False)[MAIN].action is Action.NOOP


def test_required_check_is_kept_when_the_head_has_no_run(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.check_runs[("main", "quality-gate")] = GITHUB_ACTIONS_APP
    run(client, files, apply=True)
    # A new commit on main whose CI run has not reported yet.
    del fake_repository.check_runs[("main", "quality-gate")]

    result = run(client, files, apply=False)

    assert result[MAIN].action is Action.NOOP
    assert f"{MAIN}:quality-gate" not in result


def test_missing_development_branch_counts_as_never_ran(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    del fake_repository.refs["develop"]

    result = run(client, files, apply=False)

    assert result[DEVELOP].action is Action.CREATE
    assert result[f"{DEVELOP}:quality-gate"].action is Action.SKIPPED


@pytest.mark.parametrize(
    "tamper",
    [
        lambda r: r.update(enforcement="disabled"),
        lambda r: r.update(bypass_actors=[{"actor_id": 5, "actor_type": "RepositoryRole"}]),
        lambda r: r["rules"].remove({"type": "deletion"}),
        lambda r: rule(r, "pull_request")["parameters"].update(
            required_review_thread_resolution=False
        ),
        lambda r: r["conditions"]["ref_name"].update(include=["refs/heads/other"]),
    ],
    ids=["disabled", "bypass", "rule-removed", "parameter", "condition"],
)
def test_changed_managed_ruleset_is_restored(
    client: GitHubClient, files: Files, fake_repository: FakeRepository, tamper: Any
) -> None:
    run(client, files, apply=True)
    expected = copy.deepcopy(stored(fake_repository, MAIN))
    tamper(stored(fake_repository, MAIN))

    result = run(client, files, apply=True)

    assert result[MAIN].action is Action.UPDATE
    assert result[MAIN].applied
    assert ("PUT", f"/repos/octo/demo/rulesets/{expected['id']}") in fake_repository.requests
    assert stored(fake_repository, MAIN) == expected


def test_other_rulesets_are_reported_and_left_unchanged(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    other = {"name": "manual", "target": "branch", "enforcement": "evaluate", "rules": []}
    other_id = fake_repository.add_ruleset(other)
    before = copy.deepcopy(fake_repository.rulesets[other_id])

    result = run(client, files, apply=True)

    assert result["other:manual"].action is Action.SKIPPED
    assert result["other:manual"].reason == "not managed by bootstrap; left unchanged"
    assert fake_repository.rulesets[other_id] == before
    assert ("GET", f"/repos/octo/demo/rulesets/{other_id}") not in fake_repository.requests


def test_repository_without_rulesets_is_reported_unprotected(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.make_private()
    fake_repository.rulesets_available = False

    result = run(client, files, apply=True)

    assert actions(result) == dict.fromkeys((MAIN, DEVELOP, TAGS), Action.FAILED)
    reason = result[MAIN].reason
    assert reason.startswith("UNPROTECTED: GitHub offers no rulesets for octo/demo")
    assert "(HTTP 403: Upgrade to GitHub Pro or make this repository public" in reason
    assert "token needs the permission" not in reason
    assert "docs/governance/branch-protection.md" in reason
    assert fake_repository.writes() == []


def test_allow_unprotected_reports_skipped(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.rulesets_available = False

    result = run(client, files, apply=True, allow_unprotected=True)

    assert actions(result) == dict.fromkeys((MAIN, DEVELOP, TAGS), Action.SKIPPED)
    assert result[MAIN].reason.startswith("UNPROTECTED:")
    assert result[MAIN].reason.endswith("; accepted")


def test_other_permission_error_fails_the_resource(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    def deny(request: Any) -> Any:
        import httpx

        if request.url.path.endswith("/rulesets"):
            return httpx.Response(403, json={"message": "Resource not accessible by integration"})
        return fake_repository(request)

    with GitHubClient("token", transport=__import__("httpx").MockTransport(deny)) as denying:
        result = run(denying, files, apply=False)

    assert list(result) == [RESOURCE_KEY]
    assert result[RESOURCE_KEY].action is Action.FAILED
    assert "Resource not accessible by integration" in result[RESOURCE_KEY].reason


def test_token_without_admin_access_fails(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.settings["permissions"] = {"admin": False, "push": True, "pull": True}

    result = run(client, files, apply=True)

    assert result[RESOURCE_KEY].action is Action.FAILED
    assert "needs administration access to octo/demo" in result[RESOURCE_KEY].reason
    assert ("GET", "/repos/octo/demo/rulesets") not in fake_repository.requests


def test_disabled_switch_leaves_rulesets_unmanaged(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    files["bootstrap"]["bootstrap"]["configure_rulesets"] = False
    fake_repository.rulesets_available = False

    result = run(client, files, apply=True)

    assert actions(result) == dict.fromkeys((MAIN, DEVELOP, TAGS), Action.SKIPPED)
    assert result[MAIN].reason == "disabled by bootstrap.configure_rulesets"
    assert ("GET", "/repos/octo/demo/rulesets") not in fake_repository.requests


def test_apply_rejects_other_actions(client: GitHubClient) -> None:
    resource = RulesetResource(client, "octo/demo", [])
    change = Change("rulesets", MAIN, Action.DELETE, details={"ruleset": {}})

    with pytest.raises(ValueError, match="cannot apply delete"):
        resource.apply(change)
