"""Tests for loading and validating the project configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from engineering_bootstrap.config import (
    ConfigError,
    load_config,
    resolve_config_dir,
    validate_config,
)

# The template repository this package currently lives in; absent once it has its own repo.
TEMPLATE_PROJECT_DIR = Path(__file__).resolve().parents[3] / ".project"


def test_valid_configuration_loads(project_dir: Path) -> None:
    config = load_config(project_dir)

    assert config.directory == project_dir
    assert config.files["labels"] == {"schema_version": "1.0", "name": "labels"}


def test_bootstrap_section_is_exposed(project_dir: Path) -> None:
    (project_dir / "bootstrap.yml").write_text(
        'schema_version: "1.0"\nname: "b"\nbootstrap:\n  dry_run_default: true\n',
        encoding="utf-8",
    )

    assert load_config(project_dir).bootstrap == {"dry_run_default": True}


def test_resolve_config_dir_accepts_file_or_directory(project_dir: Path) -> None:
    assert resolve_config_dir(project_dir / "bootstrap.yml") == project_dir
    assert resolve_config_dir(project_dir) == project_dir


def test_missing_file_is_reported(project_dir: Path) -> None:
    (project_dir / "labels.yml").unlink()

    _, problems = validate_config(project_dir)

    assert [str(p) for p in problems["labels"]] == ["labels.yml:(root): file not found"]
    assert problems["project"] == []


def test_invalid_yaml_reports_line(project_dir: Path) -> None:
    (project_dir / "workflow.yml").write_text("a: [1\nb: 2\n", encoding="utf-8")

    _, problems = validate_config(project_dir)

    assert problems["workflow"][0].path.startswith("line ")
    assert "invalid YAML syntax" in problems["workflow"][0].message


def test_schema_violation_names_location(project_dir: Path) -> None:
    (project_dir / "project.yml").write_text('schema_version: "1.0"\nname: ""\n', encoding="utf-8")

    _, problems = validate_config(project_dir)

    assert [p.path for p in problems["project"]] == ["name"]


@pytest.mark.parametrize(
    ("content", "path", "message"),
    [
        ("- a\n", "(root)", "top level must be a mapping"),
        ("name: x\n", "schema_version", "missing or not a string"),
        ('schema_version: "9.9"\nname: x\n', "schema_version", "unsupported schema_version"),
    ],
)
def test_schema_version_problems(project_dir: Path, content: str, path: str, message: str) -> None:
    (project_dir / "labels.yml").write_text(content, encoding="utf-8")

    _, problems = validate_config(project_dir)

    assert problems["labels"][0].path == path
    assert message in problems["labels"][0].message


def test_load_config_raises_with_all_problems(project_dir: Path) -> None:
    (project_dir / "labels.yml").unlink()
    (project_dir / "project.yml").write_text("name: x\n", encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_config(project_dir)

    assert {p.file for p in error.value.problems} == {"labels.yml", "project.yml"}


@pytest.mark.skipif(not TEMPLATE_PROJECT_DIR.is_dir(), reason="runs only inside the template")
def test_template_configuration_is_valid() -> None:
    _, problems = validate_config(TEMPLATE_PROJECT_DIR)

    assert {name: [str(p) for p in found] for name, found in problems.items() if found} == {}
