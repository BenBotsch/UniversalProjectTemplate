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
    assert "supported: ['1.0']" in problems[0]


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
            lambda d: d["bootstrap"]["template_only_paths"].append("../outside"),
            "bootstrap.template_only_paths.1",
        ),
        (
            "bootstrap",
            lambda d: d["bootstrap"]["template_only_paths"].append("/absolute"),
            "bootstrap.template_only_paths.1",
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
