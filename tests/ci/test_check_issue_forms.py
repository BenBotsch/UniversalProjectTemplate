"""Tests for scripts/ci/check_issue_forms.py."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"
LABELS_FILE = ROOT / ".project" / "labels.yml"

_spec = importlib.util.spec_from_file_location(
    "check_issue_forms", ROOT / "scripts" / "ci" / "check_issue_forms.py"
)
check_issue_forms = importlib.util.module_from_spec(_spec)
sys.modules["check_issue_forms"] = check_issue_forms
_spec.loader.exec_module(check_issue_forms)

LABEL_NAMES = check_issue_forms.load_label_names(
    yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
)


def load_form(name: str) -> dict:
    return yaml.safe_load((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def field(form: dict, field_id: str) -> dict:
    return next(element for element in form["body"] if element.get("id") == field_id)


@pytest.fixture
def template_copy(tmp_path: Path) -> Path:
    target = tmp_path / "ISSUE_TEMPLATE"
    shutil.copytree(TEMPLATE_DIR, target)
    return target


# Repository files


def test_repository_forms_are_valid() -> None:
    assert check_issue_forms.check_directory(TEMPLATE_DIR, LABELS_FILE) == []


def test_main_returns_zero_for_repository_forms(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert check_issue_forms.main(["prog", str(TEMPLATE_DIR), str(LABELS_FILE)]) == 0
    assert "OK" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("form_file", "expected_labels"),
    [
        ("bug.yml", ["type:bug", "status:triage"]),
        ("task.yml", ["type:task", "status:triage"]),
        ("feature.yml", ["type:feature", "status:triage"]),
        ("epic.yml", ["type:epic", "status:triage"]),
        ("improvement.yml", ["type:improvement", "status:triage"]),
        ("documentation.yml", ["type:documentation", "status:triage", "area:docs"]),
    ],
)
def test_forms_set_initial_labels_without_priority(
    form_file: str, expected_labels: list[str]
) -> None:
    labels = load_form(form_file)["labels"]
    assert labels == expected_labels
    assert not any(name.startswith("priority:") for name in labels)


def test_bug_severity_is_a_required_dropdown() -> None:
    severity = field(load_form("bug.yml"), "severity")
    assert severity["type"] == "dropdown"
    assert severity["attributes"]["options"] == ["Critical", "High", "Medium", "Low"]
    assert severity["validations"]["required"] is True


def test_bug_form_warns_against_disclosing_credentials() -> None:
    notice = load_form("bug.yml")["body"][0]
    assert notice["type"] == "markdown"
    assert "Do not disclose credentials" in notice["attributes"]["value"]


def test_config_disables_blank_issues_and_links_private_reporting() -> None:
    config = load_form("config.yml")
    assert config["blank_issues_enabled"] is False
    urls = [link["url"] for link in config["contact_links"]]
    assert "https://github.com/OWNER/REPOSITORY/security/advisories/new" in urls


# check_form


def test_unknown_label_is_reported() -> None:
    form = load_form("task.yml")
    form["labels"].append("area:nonexistent")
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("'area:nonexistent' is not defined" in message for message in errors)


def test_missing_type_label_is_reported() -> None:
    form = load_form("task.yml")
    form["labels"] = ["status:triage"]
    form_type, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert form_type is None
    assert any("exactly one type label" in message for message in errors)


def test_two_status_labels_are_reported() -> None:
    form = load_form("task.yml")
    form["labels"] = ["type:task", "status:triage", "status:ready"]
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("exactly one status label" in message for message in errors)


def test_duplicate_labels_are_reported() -> None:
    form = load_form("task.yml")
    form["labels"] = ["type:task", "status:triage", "status:triage"]
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("duplicates" in message for message in errors)


def test_required_field_not_marked_required_is_reported() -> None:
    form = load_form("bug.yml")
    del field(form, "reproduction")["validations"]
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert errors == ["field 'reproduction' must set validations.required: true"]


def test_renamed_required_field_is_reported() -> None:
    form = load_form("feature.yml")
    field(form, "user_story")["id"] = "story"
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert "required field 'user_story' is missing" in errors


def test_duplicate_field_id_is_reported() -> None:
    form = load_form("documentation.yml")
    duplicate = copy.deepcopy(field(form, "change"))
    duplicate["attributes"]["label"] = "Another Label"
    form["body"].append(duplicate)
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("duplicate id 'change'" in message for message in errors)


def test_duplicate_field_label_is_reported() -> None:
    form = load_form("documentation.yml")
    field(form, "change")["attributes"]["label"] = "Affected Documentation"
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("duplicate label" in message for message in errors)


@pytest.mark.parametrize("bad_id", [None, "Summary", "user-story", "1st"])
def test_invalid_field_id_is_reported(bad_id: str | None) -> None:
    form = load_form("improvement.yml")
    form["body"].append(
        {"type": "input", "id": bad_id, "attributes": {"label": "Extra"}}
    )
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("lowercase snake_case" in message for message in errors)


def test_unsupported_element_type_is_reported() -> None:
    form = load_form("improvement.yml")
    form["body"].append({"type": "slider", "attributes": {}})
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert any("unsupported type 'slider'" in message for message in errors)


def test_empty_body_is_reported() -> None:
    form = load_form("improvement.yml")
    form["body"] = []
    _, errors = check_issue_forms.check_form(form, LABEL_NAMES)
    assert "'body' must be a non-empty list" in errors


def test_non_mapping_form_is_reported() -> None:
    assert check_issue_forms.check_form(["not", "a", "form"], LABEL_NAMES) == (
        None,
        ["top level must be a mapping"],
    )


# check_config


def test_blank_issues_enabled_is_reported() -> None:
    config = load_form("config.yml")
    config["blank_issues_enabled"] = True
    assert "'blank_issues_enabled' must be false" in check_issue_forms.check_config(
        config
    )


def test_contact_link_without_https_is_reported() -> None:
    config = load_form("config.yml")
    config["contact_links"][0]["url"] = "http://example.com"
    errors = check_issue_forms.check_config(config)
    assert any("must start with https://" in message for message in errors)


# check_directory and main


def test_form_with_missing_label_fails_directory_check(template_copy: Path) -> None:
    path = template_copy / "task.yml"
    form = yaml.safe_load(path.read_text(encoding="utf-8"))
    form["labels"].append("area:nonexistent")
    path.write_text(yaml.safe_dump(form), encoding="utf-8")
    assert check_issue_forms.main(["prog", str(template_copy), str(LABELS_FILE)]) == 1


def test_missing_form_is_reported(template_copy: Path) -> None:
    (template_copy / "epic.yml").unlink()
    errors = check_issue_forms.check_directory(template_copy, LABELS_FILE)
    assert any("expected one form for 'type:epic'" in message for message in errors)


def test_second_form_for_same_type_is_reported(template_copy: Path) -> None:
    shutil.copy(template_copy / "bug.yml", template_copy / "bug-copy.yml")
    errors = check_issue_forms.check_directory(template_copy, LABELS_FILE)
    assert any("expected one form for 'type:bug'" in message for message in errors)


def test_missing_config_is_reported(template_copy: Path) -> None:
    (template_copy / "config.yml").unlink()
    errors = check_issue_forms.check_directory(template_copy, LABELS_FILE)
    assert any("config.yml: file not found" in message for message in errors)


def test_invalid_yaml_is_reported(template_copy: Path) -> None:
    (template_copy / "task.yml").write_text("name: [unclosed\n", encoding="utf-8")
    errors = check_issue_forms.check_directory(template_copy, LABELS_FILE)
    assert any("invalid YAML" in message for message in errors)


def test_missing_labels_file_is_reported(tmp_path: Path) -> None:
    errors = check_issue_forms.check_directory(TEMPLATE_DIR, tmp_path / "labels.yml")
    assert errors == [f"{tmp_path / 'labels.yml'}: file not found"]


def test_missing_template_directory_is_reported(tmp_path: Path) -> None:
    errors = check_issue_forms.check_directory(tmp_path / "missing", LABELS_FILE)
    assert errors == [f"{tmp_path / 'missing'}: directory not found"]
