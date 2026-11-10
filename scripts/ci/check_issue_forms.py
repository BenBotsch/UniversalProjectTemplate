"""Check the GitHub issue forms in .github/ISSUE_TEMPLATE/.

Verifies that every form parses as YAML, references only labels defined in
.project/labels.yml, sets exactly one type and one status label, uses unique
and stable field ids and labels, and marks the fields that the issue type
requires as required. Exactly one form must exist per supported issue type.
config.yml must disable blank issues and list well-formed contact links.

Usage: python -I scripts/ci/check_issue_forms.py [template_dir] [labels_file]
       (defaults: .github/ISSUE_TEMPLATE and .project/labels.yml)
Exit codes: 0 valid, 1 invalid or unreadable files.
Requires: pyyaml (see scripts/ci/requirements.txt).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE = "config.yml"
INPUT_TYPES = {"textarea", "input", "dropdown", "checkboxes"}
ELEMENT_TYPES = INPUT_TYPES | {"markdown"}
FIELD_ID = re.compile(r"^[a-z][a-z0-9_]*$")

# Field ids that must be required, per type label. Issue validation parses issue
# bodies by these fields, so renaming an id is an interface change.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "type:bug": (
        "summary",
        "reproduction",
        "expected",
        "actual",
        "environment",
        "severity",
        "evidence",
        "acceptance",
    ),
    "type:task": ("objective", "context", "scope", "implementation", "acceptance"),
    "type:feature": (
        "problem",
        "user_story",
        "requirements",
        "acceptance",
        "dependencies",
    ),
    "type:epic": ("goal", "scope", "non_goals", "milestones", "risks", "success"),
    "type:improvement": ("current", "proposal", "impact", "criteria"),
    "type:documentation": ("affected", "change", "acceptance"),
}


def load_label_names(data: Any) -> set[str]:
    """Return the label names defined in a parsed labels document.

    Args:
        data: Result of ``yaml.safe_load`` on ``.project/labels.yml``.

    Returns:
        The set of label names; empty if the document has no usable labels.
    """
    if not isinstance(data, dict) or not isinstance(data.get("labels"), list):
        return set()
    return {
        label["name"]
        for label in data["labels"]
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    }


def check_form(data: Any, label_names: set[str]) -> tuple[str | None, list[str]]:
    """Check one parsed issue form.

    Args:
        data: Result of ``yaml.safe_load`` on an issue form file.
        label_names: Label names defined in ``.project/labels.yml``.

    Returns:
        The form's type label (``None`` if it has not exactly one) and all
        problems found, one message per problem.
    """
    if not isinstance(data, dict):
        return None, ["top level must be a mapping"]

    errors: list[str] = []
    for key in ("name", "description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"'{key}' must be a non-empty string")

    labels = data.get("labels", [])
    if not isinstance(labels, list) or not all(
        isinstance(item, str) for item in labels
    ):
        errors.append("'labels' must be a list of strings")
        labels = []
    for name in labels:
        if name not in label_names:
            errors.append(f"label '{name}' is not defined in labels.yml")
    if len(set(labels)) != len(labels):
        errors.append("'labels' contains duplicates")

    type_labels = [name for name in labels if name.startswith("type:")]
    status_labels = [name for name in labels if name.startswith("status:")]
    if len(type_labels) != 1:
        errors.append(f"must set exactly one type label, found {type_labels}")
    if len(status_labels) != 1:
        errors.append(f"must set exactly one status label, found {status_labels}")
    form_type = type_labels[0] if len(type_labels) == 1 else None

    body = data.get("body")
    if not isinstance(body, list) or not body:
        errors.append("'body' must be a non-empty list")
        return form_type, errors

    fields = _check_body(body, errors)
    if form_type in REQUIRED_FIELDS:
        for field_id in REQUIRED_FIELDS[form_type]:
            if field_id not in fields:
                errors.append(f"required field '{field_id}' is missing")
            elif not fields[field_id]:
                errors.append(f"field '{field_id}' must set validations.required: true")
    elif form_type is not None:
        errors.append(f"type label '{form_type}' has no required-field definition")
    return form_type, errors


def _check_body(body: list[Any], errors: list[str]) -> dict[str, bool]:
    """Check the body elements; return each input field id with its required flag."""
    fields: dict[str, bool] = {}
    seen_labels: set[str] = set()
    for index, element in enumerate(body):
        where = f"body[{index}]"
        if not isinstance(element, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        element_type = element.get("type")
        if element_type not in ELEMENT_TYPES:
            errors.append(f"{where}: unsupported type {element_type!r}")
            continue
        attributes = element.get("attributes")
        if not isinstance(attributes, dict):
            errors.append(f"{where}: 'attributes' must be a mapping")
            continue
        if element_type == "markdown":
            continue

        field_id = element.get("id")
        if not isinstance(field_id, str) or not FIELD_ID.match(field_id):
            errors.append(
                f"{where}: 'id' must be lowercase snake_case, got {field_id!r}"
            )
            continue
        if field_id in fields:
            errors.append(f"{where}: duplicate id '{field_id}'")
            continue
        label = attributes.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(
                f"{where} ({field_id}): 'attributes.label' must be a non-empty string"
            )
        elif label.lower() in seen_labels:
            errors.append(f"{where} ({field_id}): duplicate label '{label}'")
        else:
            seen_labels.add(label.lower())
        validations = element.get("validations") or {}
        fields[field_id] = (
            isinstance(validations, dict) and validations.get("required") is True
        )
    return fields


def check_config(data: Any) -> list[str]:
    """Check a parsed ``config.yml`` of the issue template chooser.

    Args:
        data: Result of ``yaml.safe_load`` on ``config.yml``.

    Returns:
        All problems found, one message per problem.
    """
    if not isinstance(data, dict):
        return ["top level must be a mapping"]
    errors: list[str] = []
    if data.get("blank_issues_enabled") is not False:
        errors.append("'blank_issues_enabled' must be false")
    links = data.get("contact_links")
    if not isinstance(links, list) or not links:
        errors.append("'contact_links' must be a non-empty list")
        return errors
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(f"contact_links[{index}]: must be a mapping")
            continue
        for key in ("name", "url", "about"):
            if not isinstance(link.get(key), str) or not link[key].strip():
                errors.append(
                    f"contact_links[{index}]: '{key}' must be a non-empty string"
                )
        url = link.get("url")
        if isinstance(url, str) and not url.startswith("https://"):
            errors.append(f"contact_links[{index}]: 'url' must start with https://")
    return errors


def check_directory(template_dir: Path, labels_file: Path) -> list[str]:
    """Check all issue forms and the chooser configuration in a directory.

    Args:
        template_dir: Directory that holds the issue forms and ``config.yml``.
        labels_file: Path to ``.project/labels.yml``.

    Returns:
        All problems found, each prefixed with the affected file.
    """
    errors: list[str] = []
    label_data, problem = _load(labels_file)
    if problem:
        return [problem]
    label_names = load_label_names(label_data)
    if not label_names:
        return [f"{labels_file}: no labels defined"]

    if not template_dir.is_dir():
        return [f"{template_dir}: directory not found"]

    forms_by_type: dict[str, list[str]] = {}
    config_seen = False
    paths = sorted(template_dir.glob("*.yml")) + sorted(template_dir.glob("*.yaml"))
    for path in paths:
        data, problem = _load(path)
        if problem:
            errors.append(problem)
            continue
        if path.name == CONFIG_FILE:
            config_seen = True
            errors.extend(f"{path}: {message}" for message in check_config(data))
            continue
        form_type, messages = check_form(data, label_names)
        errors.extend(f"{path}: {message}" for message in messages)
        if form_type:
            forms_by_type.setdefault(form_type, []).append(path.name)

    if not config_seen:
        errors.append(f"{template_dir / CONFIG_FILE}: file not found")
    for form_type in REQUIRED_FIELDS:
        found = forms_by_type.get(form_type, [])
        if len(found) != 1:
            errors.append(
                f"{template_dir}: expected one form for '{form_type}', found {found}"
            )
    return errors


def _load(path: Path) -> tuple[Any, str | None]:
    """Parse a YAML file; return the data or an error message."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"{path}: file not found"
    except yaml.YAMLError as exc:
        return None, f"{path}: invalid YAML: {exc}"


def main(argv: list[str]) -> int:
    """Check the issue forms and print the result.

    Args:
        argv: Command line; optional ``argv[1]`` is the template directory and
            ``argv[2]`` the labels file.

    Returns:
        Process exit code: 0 if all files are valid, 1 otherwise.
    """
    template_dir = Path(argv[1]) if len(argv) > 1 else Path(".github/ISSUE_TEMPLATE")
    labels_file = Path(argv[2]) if len(argv) > 2 else Path(".project/labels.yml")
    errors = check_directory(template_dir, labels_file)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s) in issue forms", file=sys.stderr)
        return 1
    print(f"{template_dir}: {len(REQUIRED_FIELDS)} issue forms and {CONFIG_FILE} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
