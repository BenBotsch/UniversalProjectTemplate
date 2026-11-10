"""Tests for the label resource against a stateful fake GitHub."""

from __future__ import annotations

import pytest
from conftest import FakeGitHub

from engineering_bootstrap.engine import Action, Engine
from engineering_bootstrap.github import GitHubClient, GitHubError
from engineering_bootstrap.resources.labels import LabelResource, LabelSpec, specs_from_config

BUG = LabelSpec("type:bug", "d73a4a", "Something is broken", ("bug",))
FEATURE = LabelSpec("type:feature", "a2eeef", "New functionality", ("enhancement",))


def label(name: str, color: str = "d73a4a", description: str = "") -> dict[str, str]:
    return {"name": name, "color": color, "description": description}


def run(
    fake: FakeGitHub,
    specs: list[LabelSpec],
    *,
    apply: bool,
    prune: bool = False,
) -> dict[str, tuple[Action, str]]:
    with GitHubClient("token", transport=fake.transport) as client:
        resource = LabelResource(client, fake.repo, specs, prune=prune)
        changes = Engine([resource], allow_destructive=prune).run(apply=apply)
    return {change.key: (change.action, change.reason) for change in changes}


def test_specs_from_config_reads_aliases() -> None:
    specs = specs_from_config(
        {
            "labels": [
                {"name": "type:bug", "color": "d73a4a", "description": "x", "aliases": ["bug"]},
                {"name": "status:blocked", "color": "000000", "description": "y"},
            ]
        }
    )

    assert specs[0].aliases == ("bug",)
    assert specs[1].aliases == ()


def test_dry_run_plans_create_and_writes_nothing(fake_github: FakeGitHub) -> None:
    result = run(fake_github, [BUG], apply=False)

    assert result == {"type:bug": (Action.CREATE, "missing")}
    assert fake_github.labels == {}
    assert all(method == "GET" for method, _ in fake_github.requests)


def test_apply_creates_missing_labels(fake_github: FakeGitHub) -> None:
    run(fake_github, [BUG, FEATURE], apply=True)

    assert fake_github.labels["type:feature"] == {
        "name": "type:feature",
        "color": "a2eeef",
        "description": "New functionality",
    }


def test_matching_label_is_noop_and_color_case_is_ignored() -> None:
    fake = FakeGitHub("octo/demo", [label("type:bug", "D73A4A", "Something is broken")])

    assert run(fake, [BUG], apply=True) == {"type:bug": (Action.NOOP, "matches")}
    assert ("PATCH", "/repos/octo/demo/labels/type%3Abug") not in fake.requests


def test_differing_fields_are_updated() -> None:
    fake = FakeGitHub("octo/demo", [label("Type:Bug", "ffffff", "old")])

    result = run(fake, [BUG], apply=True)

    assert result == {"type:bug": (Action.UPDATE, "name, color, description differ")}
    assert fake.labels == {"type:bug": label("type:bug", "d73a4a", "Something is broken")}
    assert ("PATCH", "/repos/octo/demo/labels/Type%3ABug") in fake.requests


def test_alias_is_renamed_instead_of_created() -> None:
    fake = FakeGitHub("octo/demo", [label("bug", "d73a4a", "Something is broken")])

    result = run(fake, [BUG], apply=True)

    assert result == {"type:bug": (Action.UPDATE, "rename from alias 'bug'")}
    assert list(fake.labels) == ["type:bug"]
    assert not any(method == "POST" for method, _ in fake.requests)


def test_alias_rename_also_reports_other_differences() -> None:
    fake = FakeGitHub("octo/demo", [label("Bug", "ffffff", "Something is broken")])

    result = run(fake, [BUG], apply=False)

    assert result == {"type:bug": (Action.UPDATE, "rename from alias 'Bug'; color differ")}


def test_existing_name_wins_over_alias() -> None:
    fake = FakeGitHub(
        "octo/demo",
        [label("bug"), label("type:bug", "d73a4a", "Something is broken")],
    )

    result = run(fake, [BUG], apply=False)

    assert result["type:bug"] == (Action.NOOP, "matches")
    assert result["bug"] == (
        Action.SKIPPED,
        "alias of 'type:bug', which already exists; kept (delete with --prune)",
    )


def test_unknown_labels_are_kept_without_prune() -> None:
    fake = FakeGitHub("octo/demo", [label("wontfix"), label("question")])

    result = run(fake, [], apply=True)

    assert result == {
        "wontfix": (Action.SKIPPED, "not in labels.yml; kept (delete with --prune)"),
        "question": (Action.SKIPPED, "not in labels.yml; kept (delete with --prune)"),
    }
    assert set(fake.labels) == {"wontfix", "question"}


def test_prune_deletes_unknown_labels_and_reports_usage() -> None:
    fake = FakeGitHub("octo/demo", [label("wontfix"), label("good first issue")])
    fake.usage["wontfix"] = 3

    result = run(fake, [], apply=True, prune=True)

    assert result["wontfix"] == (
        Action.DELETE,
        "not in labels.yml; used by 3 issue(s) and pull request(s)",
    )
    assert fake.labels == {}
    assert ("DELETE", "/repos/octo/demo/labels/good%20first%20issue") in fake.requests


def test_prune_dry_run_deletes_nothing() -> None:
    fake = FakeGitHub("octo/demo", [label("wontfix")])

    result = run(fake, [], apply=False, prune=True)

    assert result["wontfix"][0] is Action.DELETE
    assert set(fake.labels) == {"wontfix"}


def test_usage_is_unknown_for_names_with_quotes() -> None:
    fake = FakeGitHub("octo/demo", [label('say "hi"')])

    result = run(fake, [], apply=False, prune=True)

    assert "unknown number" in result['say "hi"'][1]
    assert ("GET", "/search/issues") not in fake.requests


def test_create_falls_back_to_update_when_the_label_appeared_meanwhile(
    fake_github: FakeGitHub,
) -> None:
    with GitHubClient("token", transport=fake_github.transport) as client:
        resource = LabelResource(client, fake_github.repo, [BUG])
        [change] = resource.diff([], [BUG])
        fake_github.labels["type:bug"] = label("type:bug", "ffffff", "old")

        resource.apply(change)

    assert fake_github.labels["type:bug"]["color"] == "d73a4a"
    assert ("PATCH", "/repos/octo/demo/labels/type%3Abug") in fake_github.requests


def test_other_create_errors_are_raised(fake_github: FakeGitHub) -> None:
    fake_github.fail_post_with = 403
    with GitHubClient("token", transport=fake_github.transport) as client:
        resource = LabelResource(client, fake_github.repo, [BUG])
        [change] = resource.diff([], [BUG])

        with pytest.raises(GitHubError):
            resource.apply(change)


def test_failed_write_is_reported_as_failed(fake_github: FakeGitHub) -> None:
    fake_github.fail_post_with = 403

    result = run(fake_github, [BUG], apply=True)

    assert result["type:bug"][0] is Action.FAILED


def test_labels_are_read_across_pages() -> None:
    fake = FakeGitHub("octo/demo", [label(f"l{i}") for i in range(5)])

    result = run(fake, [], apply=False)

    assert len(result) == 5


def test_second_apply_is_all_noop() -> None:
    fake = FakeGitHub("octo/demo", [label("bug"), label("enhancement", "ffffff"), label("x")])

    run(fake, [BUG, FEATURE], apply=True)
    second = run(fake, [BUG, FEATURE], apply=True)

    assert second == {
        "type:bug": (Action.NOOP, "matches"),
        "type:feature": (Action.NOOP, "matches"),
        "x": (Action.SKIPPED, "not in labels.yml; kept (delete with --prune)"),
    }


def test_apply_rejects_unsupported_actions(fake_github: FakeGitHub) -> None:
    from engineering_bootstrap.engine import Change

    resource = LabelResource(None, fake_github.repo, [])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="cannot apply"):
        resource.apply(Change("labels", "x", Action.NOOP))
