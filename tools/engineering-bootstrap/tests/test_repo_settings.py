"""Tests for the repository settings resource."""

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
from engineering_bootstrap.resources.repo_settings import (
    RepoSettingsResource,
    Setting,
    settings_from_config,
)

Files = dict[str, dict[str, Any]]


@pytest.fixture
def files(template_config_dir: Path) -> Files:
    """Return the parsed configuration of the template, with a real description."""
    parsed = copy.deepcopy(load_config(template_config_dir).files)
    parsed["project"]["project"]["description"] = "Demo project"
    return parsed


@pytest.fixture
def client(fake_repository: FakeRepository) -> Iterator[GitHubClient]:
    with GitHubClient("token", transport=fake_repository.transport, sleep=lambda _: None) as c:
        yield c


def run(client: GitHubClient, files: Files, *, apply: bool) -> dict[str, Change]:
    resource = RepoSettingsResource(client, "octo/demo", settings_from_config(files))
    return {change.key: change for change in Engine([resource]).run(apply=apply)}


def actions(changes: dict[str, Change]) -> dict[str, Action]:
    return {key: change.action for key, change in changes.items()}


def by_key(files: Files) -> dict[str, Setting]:
    return {setting.key: setting for setting in settings_from_config(files)}


def test_desired_values_come_from_project_workflow_and_bootstrap(files: Files) -> None:
    settings = by_key(files)

    assert settings["default_branch"].value == "main"
    assert settings["description"].value == "Demo project"
    assert settings["has_issues"].value is True
    assert settings["has_discussions"].value is False
    assert settings["has_wiki"].value is False
    assert settings["delete_branch_on_merge"].value is True
    # workflow.yml: squash into develop, merge commits for releases.
    assert settings["merge_methods"].value == {
        "allow_squash_merge": True,
        "allow_merge_commit": True,
        "allow_rebase_merge": False,
    }
    assert settings["is_template"].report_only
    assert settings["actions_permissions"].value == {"enabled": True, "allowed_actions": "selected"}
    assert settings["actions_selected"].value["patterns_allowed"] == [
        "DavidAnson/markdownlint-cli2-action@*",
        "lycheeverse/lychee-action@*",
    ]
    assert settings["workflow_permissions"].value == {
        "default_workflow_permissions": "read",
        "can_approve_pull_request_reviews": False,
    }
    assert settings["topics"].skip_reason == "repository_settings.topics not set"


def test_merge_methods_follow_merge_strategy(files: Files) -> None:
    files["workflow"]["pull_requests"]["merge_strategy"] = {
        "into_development_branch": "rebase",
        "release_into_default_branch": "rebase",
    }

    assert by_key(files)["merge_methods"].value == {
        "allow_squash_merge": False,
        "allow_merge_commit": False,
        "allow_rebase_merge": True,
    }


def test_placeholder_description_is_not_managed(files: Files) -> None:
    files["project"]["project"]["description"] = "PROJECT_DESCRIPTION"

    setting = by_key(files)["description"]

    assert setting.skip_reason == (
        "project.description still contains the placeholder 'PROJECT_DESCRIPTION'"
    )


def test_bootstrap_schema_1_0_is_rejected(files: Files) -> None:
    del files["bootstrap"]["repository_settings"]

    with pytest.raises(ValueError, match=r"migrate it to schema_version 1\.1"):
        settings_from_config(files)


def test_new_public_repository_is_configured_and_second_run_is_noop(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    planned = run(client, files, apply=False)

    assert fake_repository.writes() == []
    assert actions(planned) == {
        "default_branch": Action.NOOP,
        "description": Action.UPDATE,
        "has_issues": Action.NOOP,
        "has_discussions": Action.NOOP,
        "has_wiki": Action.UPDATE,
        "delete_branch_on_merge": Action.UPDATE,
        "merge_methods": Action.UPDATE,
        "is_template": Action.SKIPPED,
        "topics": Action.SKIPPED,
        "actions_permissions": Action.UPDATE,
        "actions_selected": Action.UPDATE,
        "workflow_permissions": Action.UPDATE,
        "dependabot_alerts": Action.UPDATE,
        "dependabot_security_updates": Action.UPDATE,
        "secret_scanning": Action.UPDATE,
        "secret_scanning_push_protection": Action.UPDATE,
        "private_vulnerability_reporting": Action.UPDATE,
    }

    applied = run(client, files, apply=True)

    assert all(c.applied for c in applied.values() if c.action is Action.UPDATE)
    assert fake_repository.settings["description"] == "Demo project"
    assert fake_repository.settings["allow_rebase_merge"] is False
    assert fake_repository.actions["allowed_actions"] == "selected"
    assert fake_repository.selected_actions["github_owned_allowed"] is True
    assert fake_repository.workflow["default_workflow_permissions"] == "read"
    assert fake_repository.vulnerability_alerts
    assert fake_repository.security_fixes
    assert fake_repository.vulnerability_reporting
    analysis = fake_repository.settings["security_and_analysis"]
    assert analysis["secret_scanning_push_protection"] == {"status": "enabled"}

    fake_repository.requests.clear()
    second = run(client, files, apply=True)

    assert fake_repository.writes() == []
    assert {c.action for c in second.values()} == {Action.NOOP, Action.SKIPPED}


def test_template_flag_is_reported_but_never_changed(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    result = run(client, files, apply=True)

    change = result["is_template"]
    assert change.action is Action.SKIPPED
    assert "is False, configured True; not changed automatically" in change.reason
    assert fake_repository.settings["is_template"] is False


def test_private_repository_reports_unavailable_features_as_skipped(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.make_private()

    result = run(client, files, apply=True)

    for key in ("secret_scanning", "secret_scanning_push_protection"):
        assert result[key].action is Action.SKIPPED
        assert "Secret Protection or Advanced Security" in result[key].reason
    assert result["private_vulnerability_reporting"].action is Action.SKIPPED
    assert "only public repositories" in result["private_vulnerability_reporting"].reason
    assert not any(c.action is Action.FAILED for c in result.values())
    assert ("GET", "/repos/octo/demo/private-vulnerability-reporting") not in (
        fake_repository.requests
    )
    # Dependabot alerts are available for private repositories as well.
    assert fake_repository.vulnerability_alerts


def test_private_repository_with_secret_protection_manages_secret_scanning(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.make_private()
    fake_repository.settings["security_and_analysis"]["secret_protection"] = {"status": "enabled"}

    planned = run(client, files, apply=False)

    assert planned["secret_scanning"].action is Action.UPDATE
    assert planned["secret_scanning_push_protection"].action is Action.UPDATE


def test_missing_security_report_is_skipped(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    del fake_repository.settings["security_and_analysis"]

    planned = run(client, files, apply=False)

    assert planned["secret_scanning"].action is Action.SKIPPED
    assert "does not report security_and_analysis" in planned["secret_scanning"].reason


def test_token_without_admin_access_fails(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.settings["permissions"] = {"admin": False, "push": True, "pull": True}

    result = run(client, files, apply=True)

    assert list(result) == [RESOURCE_KEY]
    assert result[RESOURCE_KEY].action is Action.FAILED
    assert "needs administration access to octo/demo" in result[RESOURCE_KEY].reason
    assert fake_repository.writes() == []


@pytest.mark.parametrize(
    ("switch", "keys", "unread"),
    [
        (
            "configure_security",
            (
                "secret_scanning",
                "secret_scanning_push_protection",
                "private_vulnerability_reporting",
            ),
            "/repos/octo/demo/private-vulnerability-reporting",
        ),
        (
            "configure_dependabot",
            ("dependabot_alerts", "dependabot_security_updates"),
            "/repos/octo/demo/vulnerability-alerts",
        ),
    ],
)
def test_disabled_switch_leaves_security_settings_unmanaged(
    client: GitHubClient,
    files: Files,
    fake_repository: FakeRepository,
    switch: str,
    keys: tuple[str, ...],
    unread: str,
) -> None:
    files["bootstrap"]["bootstrap"][switch] = False

    result = run(client, files, apply=True)

    for key in keys:
        assert result[key].action is Action.SKIPPED
        assert result[key].reason == f"disabled by bootstrap.{switch}"
    assert ("GET", unread) not in fake_repository.requests


def test_configured_topics_replace_the_topics_order_insensitively(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    files["bootstrap"]["repository_settings"]["topics"] = ["python", "cli"]

    assert run(client, files, apply=True)["topics"].action is Action.UPDATE
    assert ("PUT", "/repos/octo/demo/topics") in fake_repository.requests
    fake_repository.settings["topics"] = ["python", "cli"]

    assert run(client, files, apply=False)["topics"].action is Action.NOOP


def test_merge_methods_are_written_in_one_request(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    # Only rebase is allowed; switching it off first would leave no merge method.
    fake_repository.settings.update(
        allow_squash_merge=False, allow_merge_commit=False, allow_rebase_merge=True
    )

    result = run(client, files, apply=True)

    assert result["merge_methods"].applied
    assert fake_repository.settings["allow_squash_merge"] is True
    assert fake_repository.settings["allow_rebase_merge"] is False


def test_disabled_security_feature_is_switched_off(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    fake_repository.vulnerability_alerts = True
    security = files["bootstrap"]["repository_settings"]["security"]
    security.update(dependabot_alerts=False, dependabot_security_updates=False)

    result = run(client, files, apply=True)

    assert result["dependabot_alerts"].applied
    assert result["dependabot_security_updates"].action is Action.NOOP
    assert not fake_repository.vulnerability_alerts
    assert ("DELETE", "/repos/octo/demo/vulnerability-alerts") in fake_repository.requests


def test_without_allow_list_selected_actions_are_not_managed(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    actions_config = files["bootstrap"]["repository_settings"]["actions"]
    actions_config["allowed_actions"] = "all"
    for key in ("github_owned_allowed", "verified_allowed", "patterns_allowed"):
        del actions_config[key]

    result = run(client, files, apply=True)

    assert "actions_selected" not in result
    assert result["actions_permissions"].action is Action.NOOP
    assert ("GET", "/repos/octo/demo/actions/permissions/selected-actions") not in (
        fake_repository.requests
    )


def test_failed_write_is_reported_and_others_continue(
    client: GitHubClient, files: Files, fake_repository: FakeRepository
) -> None:
    files["project"]["repository"]["default_branch"] = "trunk"

    result = run(client, files, apply=True)

    assert result["default_branch"].action is Action.FAILED
    assert "HTTP 422" in result["default_branch"].reason
    assert result["has_wiki"].applied


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            Change("repository-settings", "has_wiki", Action.CREATE, details={"value": False}),
            "cannot apply create",
        ),
        (
            Change("repository-settings", "unknown", Action.UPDATE, details={"value": False}),
            "unknown repository setting",
        ),
    ],
)
def test_apply_rejects_unexpected_changes(
    client: GitHubClient, change: Change, message: str
) -> None:
    resource = RepoSettingsResource(client, "octo/demo", [])

    with pytest.raises(ValueError, match=message):
        resource.apply(change)
