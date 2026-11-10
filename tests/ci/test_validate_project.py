"""Tests for scripts/ci/validate_project.py.

The repository's own .project/ directory is the valid fixture. Invalid cases copy it to a
temporary directory and change one value, so the fixtures cannot drift from the real files.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / ".project"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "project"

_spec = importlib.util.spec_from_file_location(
    "validate_project", ROOT / "scripts" / "ci" / "validate_project.py"
)
validate_project = importlib.util.module_from_spec(_spec)
sys.modules["validate_project"] = validate_project
_spec.loader.exec_module(validate_project)


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    target = tmp_path / ".project"
    shutil.copytree(PROJECT_DIR, target)
    return target


def edit(
    project_dir: Path, name: str, change: Callable[[dict[str, Any]], None]
) -> None:
    path = project_dir / f"{name}.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def messages(project_dir: Path) -> list[str]:
    return [str(problem) for problem in validate_project.validate_project(project_dir)]


def assert_single_problem(
    project_dir: Path, file: str, path: str, fragment: str
) -> None:
    problems = validate_project.validate_project(project_dir)
    assert len(problems) == 1, [str(problem) for problem in problems]
    problem = problems[0]
    assert problem.file.name == file
    assert problem.path == path
    assert fragment in problem.message


# Repository configuration


def test_repository_configuration_is_valid() -> None:
    assert validate_project.validate_project(PROJECT_DIR) == []


def test_main_returns_zero_for_repository_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert validate_project.main(["prog", str(PROJECT_DIR)]) == 0
    assert "5 configuration files valid" in capsys.readouterr().out


@pytest.mark.parametrize(
    "schema_file", sorted((PROJECT_DIR / "schemas").glob("*.schema.json"))
)
def test_schemas_are_valid_draft_2020_12(schema_file: Path) -> None:
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    version = schema["properties"]["schema_version"]["const"]
    assert schema["$id"].endswith(f":{version}")
    assert schema_file.name.endswith(f"-{version}.schema.json")


def test_every_configuration_file_has_a_schema() -> None:
    for name in validate_project.CONFIG_NAMES:
        assert (PROJECT_DIR / "schemas" / f"{name}-1.0.schema.json").is_file()


# Read errors and schema versions (R4)


def test_missing_file_is_reported(project_copy: Path) -> None:
    (project_copy / "bootstrap.yml").unlink()
    assert_single_problem(project_copy, "bootstrap.yml", "(root)", "file not found")


def test_yaml_syntax_error_is_reported(project_copy: Path) -> None:
    shutil.copy(FIXTURES / "invalid-syntax.yml", project_copy / "project.yml")
    problems = validate_project.validate_project(project_copy)
    project_problems = [p for p in problems if p.file.name == "project.yml"]
    assert len(project_problems) == 1
    assert project_problems[0].path.startswith("line ")
    assert "invalid YAML syntax" in project_problems[0].message


def test_unknown_schema_version_is_reported(project_copy: Path) -> None:
    edit(project_copy, "labels", lambda d: d.update(schema_version="9.9"))
    problems = messages(project_copy)
    assert len(problems) == 1
    assert "labels.yml:schema_version: unsupported schema_version '9.9'" in problems[0]
    assert "supported: ['1.0', '1.1']" in problems[0]


def test_labels_schema_1_0_is_still_accepted(project_copy: Path) -> None:
    def downgrade(data: dict) -> None:
        data["schema_version"] = "1.0"
        for entry in data["labels"]:
            entry.pop("aliases", None)

    edit(project_copy, "labels", downgrade)
    assert messages(project_copy) == []


def test_aliases_are_rejected_by_labels_schema_1_0(project_copy: Path) -> None:
    edit(project_copy, "labels", lambda d: d.update(schema_version="1.0"))
    assert any("aliases" in problem for problem in messages(project_copy))


def test_bootstrap_schema_1_0_is_still_accepted(project_copy: Path) -> None:
    def downgrade(data: dict) -> None:
        data["schema_version"] = "1.0"
        del data["repository_settings"]
        del data["protection"]
        del data["init"]

    edit(project_copy, "bootstrap", downgrade)
    assert messages(project_copy) == []


def test_bootstrap_schema_1_1_is_still_accepted(project_copy: Path) -> None:
    def downgrade(data: dict) -> None:
        data["schema_version"] = "1.1"
        del data["protection"]
        del data["init"]

    edit(project_copy, "bootstrap", downgrade)
    assert messages(project_copy) == []


def test_bootstrap_schema_1_2_is_still_accepted(project_copy: Path) -> None:
    def downgrade(data: dict) -> None:
        data["schema_version"] = "1.2"
        del data["init"]

    edit(project_copy, "bootstrap", downgrade)
    assert messages(project_copy) == []


def test_protection_is_required_by_bootstrap_schema_1_2(project_copy: Path) -> None:
    edit(project_copy, "bootstrap", lambda d: d.pop("protection"))
    assert_single_problem(
        project_copy, "bootstrap.yml", "(root)", "'protection' is a required property"
    )


def test_init_is_required_by_bootstrap_schema_1_3(project_copy: Path) -> None:
    edit(project_copy, "bootstrap", lambda d: d.pop("init"))
    assert_single_problem(
        project_copy, "bootstrap.yml", "(root)", "'init' is a required property"
    )


@pytest.mark.parametrize(
    ("init", "location"),
    [
        ({"license": "MIT License"}, "init.license"),
        ({"license": "MIT", "code_owner": "@octo"}, "init.code_owner"),
        ({"license": "MIT", "copyright_holder": "A\nB"}, "init.copyright_holder"),
        ({"license": "MIT", "year": 2026}, "init"),
    ],
)
def test_invalid_init_values_are_rejected(
    project_copy: Path, init: dict, location: str
) -> None:
    edit(project_copy, "bootstrap", lambda d: d.update(init=init))
    assert_single_problem(project_copy, "bootstrap.yml", location, "")


def test_workflow_schema_1_1_is_still_accepted(project_copy: Path) -> None:
    def downgrade(data: dict) -> None:
        data["schema_version"] = "1.1"
        del data["pull_requests"]["merge_strategy"]["hotfix_into_default_branch"]

    edit(project_copy, "workflow", downgrade)
    assert messages(project_copy) == []


def test_hotfix_merge_method_is_required_by_workflow_schema_1_2(
    project_copy: Path,
) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["pull_requests"]["merge_strategy"].pop(
            "hotfix_into_default_branch"
        ),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "pull_requests.merge_strategy",
        "'hotfix_into_default_branch' is a required property",
    )


def test_hotfix_merge_method_must_be_a_merge_method(project_copy: Path) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["pull_requests"]["merge_strategy"].update(
            hotfix_into_default_branch="ff"
        ),
    )
    assert any(
        "pull_requests.merge_strategy.hotfix_into_default_branch" in problem
        for problem in messages(project_copy)
    )


def test_protection_mode_must_be_solo_or_team(project_copy: Path) -> None:
    edit(project_copy, "bootstrap", lambda d: d["protection"].update(mode="none"))
    assert any("protection.mode" in problem for problem in messages(project_copy))


def test_repository_settings_are_required_by_bootstrap_schema_1_1(
    project_copy: Path,
) -> None:
    edit(project_copy, "bootstrap", lambda d: d.pop("repository_settings"))
    assert_single_problem(
        project_copy,
        "bootstrap.yml",
        "(root)",
        "'repository_settings' is a required property",
    )


def test_selected_actions_require_an_allow_list(project_copy: Path) -> None:
    edit(
        project_copy,
        "bootstrap",
        lambda d: d["repository_settings"]["actions"].pop("patterns_allowed"),
    )
    assert any("patterns_allowed" in problem for problem in messages(project_copy))


def test_allow_list_is_rejected_unless_actions_are_selected(project_copy: Path) -> None:
    edit(
        project_copy,
        "bootstrap",
        lambda d: d["repository_settings"]["actions"].update(allowed_actions="all"),
    )
    problems = messages(project_copy)
    assert len(problems) == 3
    assert all(
        "repository_settings.actions: False schema does not allow" in problem
        for problem in problems
    )


def test_numeric_schema_version_is_reported(project_copy: Path) -> None:
    edit(project_copy, "workflow", lambda d: d.update(schema_version=1.0))
    assert_single_problem(
        project_copy, "workflow.yml", "schema_version", "not a string"
    )


def test_missing_schema_directory_is_reported(project_copy: Path) -> None:
    shutil.rmtree(project_copy / "schemas")
    assert messages(project_copy)[0].endswith("schema directory not found")


def test_main_returns_one_and_prints_location(
    project_copy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(project_copy, "project", lambda d: d["project"].update(status="unknown"))
    assert validate_project.main(["prog", str(project_copy)]) == 1
    stderr = capsys.readouterr().err
    assert "project.yml:project.status: 'unknown' is not one of" in stderr


# Unknown fields and extensions (R1)


def test_unknown_top_level_field_is_rejected(project_copy: Path) -> None:
    edit(project_copy, "project", lambda d: d.update(custom_field=True))
    assert_single_problem(
        project_copy, "project.yml", "(root)", "'custom_field' was unexpected"
    )


def test_unknown_nested_field_is_rejected(project_copy: Path) -> None:
    edit(project_copy, "bootstrap", lambda d: d["bootstrap"].update(deploy=True))
    assert_single_problem(
        project_copy, "bootstrap.yml", "bootstrap", "'deploy' was unexpected"
    )


@pytest.mark.parametrize("name", validate_project.CONFIG_NAMES)
def test_extension_fields_are_allowed_under_x_extensions(
    project_copy: Path, name: str
) -> None:
    edit(
        project_copy, name, lambda d: d.update(x_extensions={"team": {"slack": "#dev"}})
    )
    assert messages(project_copy) == []


def test_missing_required_field_is_reported(project_copy: Path) -> None:
    edit(project_copy, "project", lambda d: d["project"].pop("visibility"))
    assert_single_problem(
        project_copy, "project.yml", "project", "'visibility' is a required property"
    )


# Enums and formats (R2)


@pytest.mark.parametrize(
    ("name", "change", "path"),
    [
        (
            "project",
            lambda d: d["project"].update(visibility="secret"),
            "project.visibility",
        ),
        (
            "project",
            lambda d: d["repository"].update(versioning="calver"),
            "repository.versioning",
        ),
        ("project", lambda d: d["template"].update(version="1.0"), "template.version"),
        (
            "project",
            lambda d: d["technology"].update(languages=["Python"]),
            "technology.languages.0",
        ),
        (
            "project",
            lambda d: d["repository"].update(default_branch="Main Branch"),
            "repository.default_branch",
        ),
        ("labels", lambda d: d["labels"][0].update(color="#d73a4a"), "labels.0.color"),
        (
            "labels",
            lambda d: d["labels"][0].update(description="x" * 101),
            "labels.0.description",
        ),
        (
            "quality-gates",
            lambda d: d["quality_gates"]["lint"].update(status="done"),
            "quality_gates.lint.status",
        ),
        (
            "quality-gates",
            lambda d: d["quality_gates"]["lint"].update(workflow="ci"),
            "quality_gates.lint.workflow",
        ),
        ("workflow", lambda d: d["branching"].update(model="trunk"), "branching.model"),
        (
            "workflow",
            lambda d: d["pull_requests"]["merge_strategy"].update(
                into_development_branch="ff"
            ),
            "pull_requests.merge_strategy.into_development_branch",
        ),
        (
            "workflow",
            lambda d: d["issue_policy"]["agent_ready_requires"].append("vibes"),
            "issue_policy.agent_ready_requires.4",
        ),
        (
            "bootstrap",
            lambda d: d["bootstrap"]["optional_profiles"].append("cobol"),
            "bootstrap.optional_profiles.6",
        ),
        (
            "bootstrap",
            lambda d: d["bootstrap"].update(dry_run_default="yes"),
            "bootstrap.dry_run_default",
        ),
        (
            "bootstrap",
            lambda d: d["bootstrap"]["template_only_paths"].insert(0, "../outside"),
            "bootstrap.template_only_paths.0",
        ),
        (
            "bootstrap",
            lambda d: d["bootstrap"]["template_only_paths"].insert(0, "/absolute"),
            "bootstrap.template_only_paths.0",
        ),
    ],
)
def test_invalid_value_is_reported_at_its_location(
    project_copy: Path, name: str, change: Callable[[dict[str, Any]], None], path: str
) -> None:
    edit(project_copy, name, change)
    problems = validate_project.validate_project(project_copy)
    assert [(p.file.name, p.path) for p in problems] == [(f"{name}.yml", path)]


def test_gate_without_applicability_key_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "quality-gates",
        lambda d: d["quality_gates"]["lint"].pop("required_when_applicable"),
    )
    problems = validate_project.validate_project(project_copy)
    assert [p.path for p in problems] == ["quality_gates.lint"]


def test_gate_with_two_applicability_keys_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "quality-gates",
        lambda d: d["quality_gates"]["lint"].update(required=True),
    )
    problems = validate_project.validate_project(project_copy)
    assert [p.path for p in problems] == ["quality_gates.lint"]


# Cross-file checks (R3)


def test_equal_default_and_development_branch_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "project",
        lambda d: d["repository"].update(development_branch="main"),
    )
    problems = messages(project_copy)
    assert any(
        "project.yml:repository.development_branch: must differ" in p for p in problems
    )


def test_issue_policy_group_missing_in_labels_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["issue_policy"]["required_for_ready"].append("team"),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "issue_policy.required_for_ready.2",
        "label group 'team' is not defined in labels.yml",
    )


def test_supported_type_missing_in_labels_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["issue_policy"]["supported_types"].append("spike"),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "issue_policy.supported_types.6",
        "'type:spike' is not defined",
    )


def test_supported_state_missing_in_labels_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "labels",
        lambda d: d.update(
            labels=[l for l in d["labels"] if l["name"] != "status:blocked"]
        ),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "issue_policy.supported_states.4",
        "'status:blocked' is not defined",
    )


def test_initial_status_outside_supported_states_is_reported(
    project_copy: Path,
) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["issue_policy"].update(initial_status="review-pending"),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "issue_policy.initial_status",
        "is not in supported_states",
    )


def test_branch_unknown_to_project_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["branching"]["branch_types"]["feature"].update(source="trunk"),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "branching.branch_types.feature.source",
        "branch 'trunk' is not defined in project.yml",
    )


def test_renamed_development_branch_must_be_used_in_workflow(
    project_copy: Path,
) -> None:
    edit(
        project_copy,
        "project",
        lambda d: d["repository"].update(development_branch="dev"),
    )
    problems = validate_project.validate_project(project_copy)
    assert problems
    assert all(
        p.file.name == "workflow.yml" and "'develop'" in p.message for p in problems
    )


def test_release_from_development_branch_is_reported(project_copy: Path) -> None:
    edit(
        project_copy,
        "workflow",
        lambda d: d["releases"].update(source_branch="develop"),
    )
    assert_single_problem(
        project_copy,
        "workflow.yml",
        "releases.source_branch",
        "must be the default branch 'main'",
    )


@pytest.mark.parametrize(
    ("section", "key"),
    [("branching", "branch_name_pattern"), ("releases", "tag_pattern")],
)
def test_invalid_regular_expression_is_reported(
    project_copy: Path, section: str, key: str
) -> None:
    edit(project_copy, "workflow", lambda d: d[section].update({key: "^(unclosed$"}))
    assert_single_problem(
        project_copy, "workflow.yml", f"{section}.{key}", "invalid regular expression"
    )


def test_label_rules_from_check_labels_are_applied(project_copy: Path) -> None:
    edit(project_copy, "labels", lambda d: d["labels"][0].update(group="status"))
    assert_single_problem(
        project_copy, "labels.yml", "labels", "does not match group 'status'"
    )


def test_cross_file_checks_skip_files_with_schema_errors(project_copy: Path) -> None:
    edit(project_copy, "labels", lambda d: d["labels"][0].update(color="red"))
    edit(
        project_copy,
        "workflow",
        lambda d: d["issue_policy"]["supported_types"].append("spike"),
    )
    problems = validate_project.validate_project(project_copy)
    assert [(p.file.name, p.path) for p in problems] == [
        ("labels.yml", "labels.0.color")
    ]


def write_workflow(project_dir: Path, *uses: str) -> None:
    workflows = project_dir.parent / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    steps = "".join(f"      - uses: {ref}\n" for ref in uses)
    (workflows / "ci.yml").write_text(
        f"on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n{steps}",
        encoding="utf-8",
    )


SHA = "a" * 40


def test_template_workflows_are_covered_by_the_actions_allow_list() -> None:
    problems = validate_project.check_allowed_actions(
        yaml.safe_load((PROJECT_DIR / "bootstrap.yml").read_text(encoding="utf-8"))[
            "repository_settings"
        ]["actions"],
        ROOT,
        PROJECT_DIR / "bootstrap.yml",
    )

    assert problems == []


def test_action_missing_from_the_allow_list_is_reported(project_copy: Path) -> None:
    write_workflow(
        project_copy,
        f"actions/checkout@{SHA} # v7",
        "./.github/actions/setup",
        f"astral-sh/setup-uv@{SHA} # v6",
    )

    assert_single_problem(
        project_copy,
        "bootstrap.yml",
        "repository_settings.actions",
        f".github/workflows/ci.yml:8 uses 'astral-sh/setup-uv@{SHA}', which allowed_actions "
        "'selected' blocks; add a matching entry to patterns_allowed",
    )


@pytest.mark.parametrize(
    ("ref", "actions", "allowed"),
    [
        ("./local", {"allowed_actions": "local_only"}, True),
        ("docker://alpine@sha256:" + "0" * 64, {"allowed_actions": "local_only"}, True),
        ("owner/repo@v1", {"allowed_actions": "all"}, True),
        ("actions/checkout@v7", {"allowed_actions": "local_only"}, False),
        ("github/codeql-action/init@v4", "selected", True),
        ("owner/repo/sub/path@v1", "selected", True),
        ("owner/other@v1", "selected", True),
        ("owner/repo@v2", {"patterns": ["owner/repo@v1"]}, False),
        ("someone/action@v1", "selected", False),
        ("actions/checkout@v7", {"github_owned_allowed": False}, False),
    ],
)
def test_action_is_allowed_follows_the_github_policy(
    ref: str, actions: dict[str, Any] | str, allowed: bool
) -> None:
    settings: dict[str, Any] = {
        "allowed_actions": "selected",
        "github_owned_allowed": True,
        "verified_allowed": True,
        "patterns_allowed": ["owner/repo@*", "owner/*"],
    }
    if isinstance(actions, dict):
        if "patterns" in actions:
            settings["patterns_allowed"] = actions.pop("patterns")
        settings.update(actions)

    assert validate_project.action_is_allowed(ref, settings) is allowed


def test_bootstrap_1_0_skips_the_allow_list_check(project_copy: Path) -> None:
    bootstrap = yaml.safe_load(
        (project_copy / "bootstrap.yml").read_text(encoding="utf-8")
    )
    del bootstrap["repository_settings"]
    del bootstrap["protection"]
    del bootstrap["init"]
    bootstrap["schema_version"] = "1.0"
    (project_copy / "bootstrap.yml").write_text(
        yaml.safe_dump(bootstrap), encoding="utf-8"
    )
    write_workflow(project_copy, f"someone/action@{SHA} # v1")

    assert messages(project_copy) == []
