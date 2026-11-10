"""Tests for the text and JSON reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import resources

from jsonschema import Draft202012Validator

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.report import REPORT_VERSION, Report, render_json, render_text

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def schema() -> dict[str, object]:
    path = resources.files("engineering_bootstrap") / f"schemas/report-{REPORT_VERSION}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sample(mode: str = "apply") -> Report:
    return Report(
        command="sync-labels",
        mode=mode,  # type: ignore[arg-type]
        target="octo/repo",
        changes=[
            Change("labels", "bug", Action.CREATE, "missing", {"color": "d73a4a"}, applied=True),
            Change("labels", "docs", Action.NOOP, "matches"),
            Change("labels", "old", Action.SKIPPED, "delete not allowed"),
            Change("labels", "x", Action.FAILED, "create failed: HTTP 422"),
        ],
        generated_at=NOW,
    )


def test_json_report_matches_schema() -> None:
    data = json.loads(render_json(sample()))

    Draft202012Validator(schema()).validate(data)
    assert data["report_version"] == REPORT_VERSION
    assert data["generated_at"] == "2026-11-10T12:00:00+00:00"
    assert data["changes"][0] == {
        "resource": "labels",
        "key": "bug",
        "action": "create",
        "reason": "missing",
        "details": {"color": "d73a4a"},
        "applied": True,
    }


def test_summary_counts_every_action() -> None:
    assert sample().summary == {
        "create": 1,
        "update": 0,
        "delete": 0,
        "noop": 1,
        "skipped": 1,
        "failed": 1,
    }
    assert sample().failed


def test_empty_report_is_valid() -> None:
    report = Report("validate", "dry-run", ".project", [], generated_at=NOW)

    Draft202012Validator(schema()).validate(json.loads(render_json(report)))
    assert not report.failed


def test_text_report_marks_applied_changes_and_failures() -> None:
    text = render_text(sample())

    assert "create   labels/bug: missing (applied)" in text
    assert "Summary: 1 create, 0 update, 0 delete, 1 noop, 1 skipped, 1 failed" in text
    assert "Applied 1 change(s)." in text
    assert "Some changes failed" in text


def test_text_dry_run_says_nothing_was_changed() -> None:
    planned = Report(
        "sync-labels",
        "dry-run",
        "octo/repo",
        [Change("labels", "bug", Action.CREATE, "missing")],
        generated_at=NOW,
    )
    clean = Report("validate", "dry-run", ".project", [], generated_at=NOW)

    assert "Run again with --apply" in render_text(planned)
    assert render_text(clean).endswith("Dry run: nothing was changed.\n")
