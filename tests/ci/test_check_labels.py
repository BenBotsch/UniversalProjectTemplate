"""Tests for scripts/ci/check_labels.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LABELS_FILE = ROOT / ".project" / "labels.yml"

_spec = importlib.util.spec_from_file_location(
    "check_labels", ROOT / "scripts" / "ci" / "check_labels.py"
)
check_labels = importlib.util.module_from_spec(_spec)
sys.modules["check_labels"] = check_labels
_spec.loader.exec_module(check_labels)

REQUIRED_LABELS = {
    "type": ["bug", "task", "feature", "epic", "improvement", "documentation"],
    "priority": ["critical", "high", "medium", "low"],
    "status": ["triage", "ready", "in-progress", "blocked", "review", "needs-info"],
    "area": ["backend", "frontend", "api", "ci-cd", "docs", "security"],
    "effort": ["xs", "s", "m", "l", "xl"],
    "impact": ["breaking", "performance", "security"],
    "agent": ["ready", "working", "review-required"],
}


def label(
    name: str, group: str, color: str = "ededed", description: str = "Some label"
) -> dict:
    return {"name": name, "color": color, "description": description, "group": group}


def doc(*labels: dict) -> dict:
    return {"schema_version": "1.0", "labels": list(labels)}


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "labels.yml"
    path.write_text(text, encoding="utf-8")
    return path


# --- shipped taxonomy -----------------------------------------------------


def test_shipped_labels_file_passes(capsys):
    assert check_labels.main(["check_labels.py", str(LABELS_FILE)]) == 0
    assert "labels OK" in capsys.readouterr().out


def test_shipped_labels_contain_full_taxonomy():
    data = check_labels.yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    names = {entry["name"] for entry in data["labels"]}
    expected = {
        f"{group}:{value}"
        for group, values in REQUIRED_LABELS.items()
        for value in values
    }
    assert expected <= names
    assert "skip-changelog" in names
    assert "status:done" not in names


def test_shipped_area_labels_share_one_color():
    data = check_labels.yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    colors = {entry["color"] for entry in data["labels"] if entry["group"] == "area"}
    assert len(colors) == 1


# --- valid input ----------------------------------------------------------


def test_valid_document_has_no_errors():
    assert (
        check_labels.check_document(
            doc(label("type:bug", "type"), label("skip-changelog", "meta"))
        )
        == []
    )


def test_extension_groups_are_allowed():
    assert check_labels.check_document(doc(label("platform:windows", "platform"))) == []


def test_description_at_limit_is_allowed():
    assert (
        check_labels.check_document(
            doc(label("type:bug", "type", description="x" * 100))
        )
        == []
    )


# --- invalid input --------------------------------------------------------


@pytest.mark.parametrize("second", ["type:bug", "Type:Bug"])
def test_duplicate_name_fails(second):
    errors = check_labels.check_document(
        doc(label("type:bug", "type"), label(second, "type"))
    )
    assert any("duplicate name" in error for error in errors)


@pytest.mark.parametrize("color", ["#d73a4a", "d73a4", "d73a4ag", "red", ""])
def test_invalid_color_fails(color):
    errors = check_labels.check_document(doc(label("type:bug", "type", color=color)))
    assert errors


def test_too_long_description_fails():
    errors = check_labels.check_document(
        doc(label("type:bug", "type", description="x" * 101))
    )
    assert any("maximum is 100" in error for error in errors)


def test_prefix_must_match_group():
    errors = check_labels.check_document(doc(label("type:bug", "priority")))
    assert any("does not match group" in error for error in errors)


@pytest.mark.parametrize(
    "name", ["bug", "type:Bug", "type:in_progress", "type:", "type:bug:x"]
)
def test_grouped_name_format_fails(name):
    errors = check_labels.check_document(doc(label(name, "type")))
    assert any("group:value" in error for error in errors)


def test_meta_label_must_not_have_prefix():
    errors = check_labels.check_document(doc(label("meta:skip-changelog", "meta")))
    assert any("without a prefix" in error for error in errors)


def test_status_done_is_forbidden():
    errors = check_labels.check_document(doc(label("status:done", "status")))
    assert any("native issue state" in error for error in errors)


def test_missing_key_fails():
    entry = label("type:bug", "type")
    del entry["color"]
    errors = check_labels.check_document(doc(entry))
    assert errors == ["labels[0]: 'color' must be a non-empty string"]


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {"schema_version": "2.0", "labels": [label("type:bug", "type")]},
        {"schema_version": "1.0"},
    ],
)
def test_invalid_document_structure_fails(data):
    assert check_labels.check_document(data)


# --- aliases (schema 1.1) -------------------------------------------------


def aliased(name: str, group: str, *aliases: object) -> dict:
    return {**label(name, group), "aliases": list(aliases)}


def test_aliases_are_accepted():
    data = {
        "schema_version": "1.1",
        "labels": [aliased("type:bug", "type", "bug"), aliased("type:feature", "type", "Enhancement")],
    }
    assert check_labels.check_document(data) == []


def test_shipped_aliases_map_github_default_labels():
    data = check_labels.yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    aliases = {alias: entry["name"] for entry in data["labels"] for alias in entry.get("aliases", [])}
    assert aliases == {
        "bug": "type:bug",
        "enhancement": "type:feature",
        "documentation": "type:documentation",
    }


@pytest.mark.parametrize(
    ("labels", "message"),
    [
        ([aliased("type:bug", "type", "TYPE:TASK"), label("type:task", "type")], "equals the name of labels[1]"),
        ([aliased("type:bug", "type", "bug"), aliased("type:task", "type", "Bug")], "already an alias of labels[0]"),
        ([aliased("type:bug", "type", "")], "aliases must be non-empty strings"),
        ([aliased("type:bug", "type", 3)], "aliases must be non-empty strings"),
        ([aliased("type:bug", "type", "x" * 51)], "longer than 50 characters"),
        ([{**label("type:bug", "type"), "aliases": "bug"}], "'aliases' must be a list"),
    ],
)
def test_invalid_aliases_fail(labels, message):
    errors = check_labels.check_document({"schema_version": "1.1", "labels": labels})
    assert any(message in error for error in errors), errors


# --- command line ---------------------------------------------------------


def test_cli_reports_errors_and_exits_1(tmp_path, capsys):
    path = write(
        tmp_path,
        'schema_version: "1.0"\nlabels:\n  - {name: "type:bug", color: "zzz", description: "x", group: "type"}\n',
    )
    assert check_labels.main(["check_labels.py", str(path)]) == 1
    assert "color must be 6-digit hex" in capsys.readouterr().err


def test_cli_missing_file_exits_1(tmp_path, capsys):
    assert check_labels.main(["check_labels.py", str(tmp_path / "missing.yml")]) == 1
    assert "file not found" in capsys.readouterr().err


def test_cli_invalid_yaml_exits_1(tmp_path, capsys):
    path = write(tmp_path, "labels: [unclosed\n")
    assert check_labels.main(["check_labels.py", str(path)]) == 1
    assert "invalid YAML" in capsys.readouterr().err
