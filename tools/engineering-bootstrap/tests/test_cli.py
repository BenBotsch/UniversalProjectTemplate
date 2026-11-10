"""Tests for the project-bootstrap command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engineering_bootstrap.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main


def test_help_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for command in ("init", "validate", "sync-labels", "audit"):
        assert command in out


def test_validate_valid_config_as_json(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["validate", "--config", str(project_dir / "bootstrap.yml"), "--format", "json"])

    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert report["mode"] == "dry-run"
    assert report["summary"]["noop"] == 5
    assert {change["key"] for change in report["changes"]} >= {"labels.yml", "bootstrap.yml"}


def test_validate_invalid_config_fails(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project_dir / "labels.yml").write_text("name: x\n", encoding="utf-8")

    code = main(["validate", "--config", str(project_dir)])

    out = capsys.readouterr().out
    assert code == EXIT_FAILED
    assert "failed   config/labels.yml: schema_version: missing or not a string" in out


def test_report_file_is_written_as_json(project_dir: Path, tmp_path: Path) -> None:
    report_file = tmp_path / "report.json"

    code = main(["validate", "--config", str(project_dir), "--report-file", str(report_file)])

    assert code == EXIT_OK
    assert json.loads(report_file.read_text(encoding="utf-8"))["command"] == "validate"


def test_apply_and_dry_run_are_mutually_exclusive(project_dir: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["validate", "--config", str(project_dir), "--dry-run", "--apply"])

    assert exit_info.value.code == EXIT_USAGE


def test_apply_mode_is_reported(project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate", "--config", str(project_dir), "--apply", "--format", "json"])

    assert json.loads(capsys.readouterr().out)["mode"] == "apply"


@pytest.mark.parametrize(
    "argv",
    [
        ["init", "--repo", "octo/new", "--profile", "python"],
        ["validate", "--repo", "octo/new"],
        ["sync-labels", "--repo", "octo/new"],
        ["audit", "--owner", "octo"],
    ],
)
def test_unimplemented_commands_exit_with_usage_error(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(argv)

    assert code == EXIT_USAGE
    assert "not implemented yet" in capsys.readouterr().err
