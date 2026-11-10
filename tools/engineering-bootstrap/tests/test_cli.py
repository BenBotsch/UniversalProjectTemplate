"""Tests for the project-bootstrap command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from conftest import FakeGitHub, FakeRepository

from engineering_bootstrap.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main


def test_help_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for command in ("init", "validate", "sync-labels", "configure-repo", "apply-rulesets", "audit"):
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
        ["audit", "--owner", "octo"],
    ],
)
def test_unimplemented_commands_exit_with_usage_error(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(argv)

    assert code == EXIT_USAGE
    assert "not implemented yet" in capsys.readouterr().err


LABELS_YML = """schema_version: "1.0"
name: labels
labels:
  - name: "type:bug"
    color: "d73a4a"
    description: "Something is broken"
    aliases: ["bug"]
"""


@pytest.fixture
def label_project(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a project whose labels.yml configures one label, with a token in the environment."""
    (project_dir / "labels.yml").write_text(LABELS_YML, encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return project_dir


def sync(project: Path, fake: FakeGitHub, *options: str) -> int:
    argv = ["sync-labels", f"--repo={fake.repo}", "--config", str(project), *options]
    return main(argv, transport=fake.transport)


def test_sync_labels_dry_run_reports_the_plan(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_github.labels["bug"] = {"name": "bug", "color": "d73a4a", "description": ""}

    code = sync(label_project, fake_github, "--format", "json")

    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert report["command"] == "sync-labels"
    assert report["target"] == "octo/demo"
    assert report["summary"]["update"] == 1
    assert list(fake_github.labels) == ["bug"]


def test_sync_labels_apply_then_dry_run_is_noop(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert sync(label_project, fake_github, "--apply") == EXIT_OK
    capsys.readouterr()

    code = sync(label_project, fake_github, "--format", "json")

    summary = json.loads(capsys.readouterr().out)["summary"]
    assert code == EXIT_OK
    assert summary["noop"] == 1
    assert sum(summary.values()) == 1


def test_sync_labels_failure_exits_with_1(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_github.fail_post_with = 403

    assert sync(label_project, fake_github, "--apply") == EXIT_FAILED


def test_prune_requires_apply(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    code = sync(label_project, fake_github, "--prune")

    assert code == EXIT_USAGE
    assert "--prune requires --apply" in capsys.readouterr().err
    assert fake_github.requests == []


def test_prune_with_yes_deletes_unknown_labels(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_github.labels["wontfix"] = {"name": "wontfix", "color": "ffffff", "description": ""}
    fake_github.usage["wontfix"] = 2

    code = sync(label_project, fake_github, "--apply", "--prune", "--yes")

    assert code == EXIT_OK
    assert "wontfix: not in labels.yml; used by 2 issue(s)" in capsys.readouterr().err
    assert list(fake_github.labels) == ["type:bug"]


def test_prune_without_confirmation_changes_nothing(
    label_project: Path,
    fake_github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_github.labels["wontfix"] = {"name": "wontfix", "color": "ffffff", "description": ""}
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    code = sync(label_project, fake_github, "--apply", "--prune")

    assert code == EXIT_USAGE
    assert "prune not confirmed; nothing was changed" in capsys.readouterr().err
    assert list(fake_github.labels) == ["wontfix"]


@pytest.mark.parametrize(("answer", "deleted"), [("y", True), ("", False), ("no", False)])
def test_prune_asks_on_a_terminal(
    label_project: Path,
    fake_github: FakeGitHub,
    monkeypatch: pytest.MonkeyPatch,
    answer: str,
    deleted: bool,
) -> None:
    fake_github.labels["wontfix"] = {"name": "wontfix", "color": "ffffff", "description": ""}
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    sync(label_project, fake_github, "--apply", "--prune")

    assert ("wontfix" not in fake_github.labels) is deleted


@pytest.mark.parametrize("repo", ["octo", "octo/demo/labels", "../x/y", "octo/de mo", "-octo/x"])
def test_invalid_repo_is_a_usage_error(
    label_project: Path, fake_github: FakeGitHub, repo: str
) -> None:
    fake_github.repo = repo

    assert sync(label_project, fake_github) == EXIT_USAGE
    assert fake_github.requests == []


def test_missing_token_fails(
    label_project: Path,
    fake_github: FakeGitHub,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setenv("PATH", "")

    assert sync(label_project, fake_github) == EXIT_FAILED
    assert fake_github.requests == []


def test_invalid_config_fails_before_any_request(
    label_project: Path, fake_github: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    (label_project / "labels.yml").write_text("name: x\n", encoding="utf-8")

    assert sync(label_project, fake_github) == EXIT_FAILED
    assert "invalid configuration: labels.yml" in capsys.readouterr().err
    assert fake_github.requests == []


@pytest.fixture
def repo_project(template_config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return the template configuration with a token in the environment."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return template_config_dir


def configure(project: Path, fake: FakeRepository, *options: str) -> int:
    argv = ["configure-repo", f"--repo={fake.repo}", "--config", str(project), *options]
    return main(argv, transport=fake.transport)


def test_configure_repo_dry_run_changes_nothing(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    code = configure(repo_project, fake_repository, "--format", "json")

    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert report["command"] == "configure-repo"
    assert report["mode"] == "dry-run"
    assert {change["resource"] for change in report["changes"]} == {
        "branches",
        "repository-settings",
    }
    develop = next(c for c in report["changes"] if c["key"] == "develop")
    assert develop["action"] == "create"
    assert fake_repository.writes() == []


def test_configure_repo_apply_then_rerun_is_noop(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    assert configure(repo_project, fake_repository, "--apply") == EXIT_OK
    assert "develop" in fake_repository.refs
    capsys.readouterr()
    fake_repository.requests.clear()

    code = configure(repo_project, fake_repository, "--apply", "--format", "json")

    summary = json.loads(capsys.readouterr().out)["summary"]
    assert code == EXIT_OK
    assert fake_repository.writes() == []
    assert summary["create"] == summary["update"] == summary["failed"] == 0


def test_configure_repo_needs_bootstrap_schema_1_1(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    bootstrap_file = repo_project / "bootstrap.yml"
    data = yaml.safe_load(bootstrap_file.read_text(encoding="utf-8"))
    data["schema_version"] = "1.0"
    del data["repository_settings"]
    del data["protection"]
    bootstrap_file.write_text(yaml.safe_dump(data), encoding="utf-8")

    code = configure(repo_project, fake_repository)

    assert code == EXIT_FAILED
    assert "migrate it to schema_version 1.1" in capsys.readouterr().err
    assert fake_repository.requests == []


def test_configure_repo_failure_exits_with_1(
    repo_project: Path, fake_repository: FakeRepository
) -> None:
    fake_repository.empty = True

    assert configure(repo_project, fake_repository, "--apply") == EXIT_FAILED


def test_configure_repo_rejects_invalid_repo(
    repo_project: Path, fake_repository: FakeRepository
) -> None:
    argv = ["configure-repo", "--repo", "octo/demo/../x", "--config", str(repo_project)]

    assert main(argv, transport=fake_repository.transport) == EXIT_USAGE
    assert fake_repository.requests == []


def protect(project: Path, fake: FakeRepository, *options: str) -> int:
    argv = ["apply-rulesets", f"--repo={fake.repo}", "--config", str(project), *options]
    return main(argv, transport=fake.transport)


def test_apply_rulesets_dry_run_plans_the_rulesets(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    code = protect(repo_project, fake_repository, "--format", "json")

    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert report["command"] == "apply-rulesets"
    assert report["summary"]["create"] == 3
    assert fake_repository.writes() == []


def test_apply_rulesets_unprotected_repository_exits_with_1(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_repository.rulesets_available = False

    code = protect(repo_project, fake_repository)

    assert code == EXIT_FAILED
    assert "UNPROTECTED" in capsys.readouterr().out


def test_apply_rulesets_allow_unprotected_exits_with_0(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_repository.rulesets_available = False

    code = protect(repo_project, fake_repository, "--allow-unprotected", "--format", "json")

    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert report["summary"]["skipped"] == 3
    assert report["summary"]["failed"] == 0


def test_apply_rulesets_needs_bootstrap_schema_1_2(
    repo_project: Path, fake_repository: FakeRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    bootstrap_file = repo_project / "bootstrap.yml"
    data = yaml.safe_load(bootstrap_file.read_text(encoding="utf-8"))
    data["schema_version"] = "1.1"
    del data["protection"]
    bootstrap_file.write_text(yaml.safe_dump(data), encoding="utf-8")

    code = protect(repo_project, fake_repository)

    assert code == EXIT_FAILED
    assert "migrate it to schema_version 1.2" in capsys.readouterr().err
    assert fake_repository.requests == []
