"""Check .project/labels.yml for structural consistency.

Lightweight check until the JSON Schema validator exists. It verifies that
label names are unique (case-insensitive, as on GitHub), colors are 6-digit
hex without '#', descriptions fit the GitHub limit of 100 characters, and the
name prefix matches the declared group. Labels in group "meta" carry no prefix.
``aliases`` (schema 1.1) are non-empty strings of at most 50 characters; an alias must not
equal a label name or another alias, compared case-insensitively.

Usage: python -I scripts/ci/check_labels.py [path]   (default: .project/labels.yml)
Exit codes: 0 valid, 1 invalid or unreadable file.
Requires: pyyaml (see scripts/ci/requirements.txt).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}
META_GROUP = "meta"
MAX_DESCRIPTION_LENGTH = 100
# GitHub limit for label names; aliases are existing label names.
MAX_ALIAS_LENGTH = 50
REQUIRED_KEYS = ("name", "color", "description", "group")
# Closed issues use the native GitHub state; a status label for it is redundant.
FORBIDDEN_NAMES = {"status:done"}

KEBAB = r"[a-z0-9]+(?:-[a-z0-9]+)*"
GROUPED_NAME = re.compile(rf"^(?P<group>{KEBAB}):(?P<value>{KEBAB})$")
META_NAME = re.compile(rf"^{KEBAB}$")
COLOR = re.compile(r"^[0-9a-fA-F]{6}$")


def check_document(data: Any) -> list[str]:
    """Check a parsed labels document.

    Args:
        data: Result of ``yaml.safe_load`` on a labels file.

    Returns:
        All problems found, one message per problem; empty if the document is valid.
    """
    if not isinstance(data, dict):
        return ["top level must be a mapping with 'schema_version' and 'labels'"]

    errors: list[str] = []
    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            f"unsupported schema_version {version!r}; expected one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        errors.append("'labels' must be a non-empty list")
        return errors

    seen: dict[str, int] = {}
    for index, label in enumerate(labels):
        errors.extend(_check_label(index, label, seen))
    errors.extend(_check_aliases(labels, seen))
    return errors


def _check_aliases(labels: list[Any], names: dict[str, int]) -> list[str]:
    """Check the optional ``aliases`` of every label against all names and other aliases."""
    errors: list[str] = []
    owners: dict[str, int] = {}
    for index, label in enumerate(labels):
        if not isinstance(label, dict) or "aliases" not in label:
            continue
        where = f"labels[{index}] ({label.get('name')})"
        aliases = label["aliases"]
        if not isinstance(aliases, list):
            errors.append(f"{where}: 'aliases' must be a list")
            continue
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                errors.append(f"{where}: aliases must be non-empty strings")
                continue
            if len(alias) > MAX_ALIAS_LENGTH:
                errors.append(f"{where}: alias {alias!r} is longer than {MAX_ALIAS_LENGTH} characters")
            key = alias.lower()
            if key in names:
                errors.append(f"{where}: alias {alias!r} equals the name of labels[{names[key]}]")
            elif key in owners:
                errors.append(f"{where}: alias {alias!r} is already an alias of labels[{owners[key]}]")
            else:
                owners[key] = index
    return errors


def _check_label(index: int, label: Any, seen: dict[str, int]) -> list[str]:
    """Check one label entry; records its lowercase name in ``seen``."""
    where = f"labels[{index}]"
    if not isinstance(label, dict):
        return [f"{where}: must be a mapping"]

    errors: list[str] = []
    for key in REQUIRED_KEYS:
        value = label.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{where}: '{key}' must be a non-empty string")
    if errors:
        return errors

    name, color, description, group = (label[key] for key in REQUIRED_KEYS)
    where = f"{where} ({name})"

    key = name.lower()
    if key in seen:
        errors.append(f"{where}: duplicate name, first defined at labels[{seen[key]}]")
    else:
        seen[key] = index

    if name in FORBIDDEN_NAMES:
        errors.append(f"{where}: not allowed; closed is the native issue state")

    if group == META_GROUP:
        if not META_NAME.match(name):
            errors.append(
                f"{where}: meta label names must be lowercase kebab-case without a prefix"
            )
    else:
        match = GROUPED_NAME.match(name)
        if not match:
            errors.append(
                f"{where}: name must be lowercase 'group:value' in kebab-case"
            )
        elif match.group("group") != group:
            errors.append(
                f"{where}: name prefix '{match.group('group')}' does not match group '{group}'"
            )

    if not COLOR.match(color):
        errors.append(f"{where}: color must be 6-digit hex without '#', got {color!r}")

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"{where}: description has {len(description)} characters; maximum is {MAX_DESCRIPTION_LENGTH}"
        )

    return errors


def main(argv: list[str]) -> int:
    """Check the labels file named in ``argv[1]`` and print the result.

    Args:
        argv: Command line; ``argv[1]`` is the optional path to the labels file.

    Returns:
        Process exit code: 0 if the file is valid, 1 otherwise.
    """
    path = Path(argv[1]) if len(argv) > 1 else Path(".project/labels.yml")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: {path}: file not found", file=sys.stderr)
        return 1
    except yaml.YAMLError as exc:
        print(f"error: {path}: invalid YAML: {exc}", file=sys.stderr)
        return 1

    errors = check_document(data)
    for message in errors:
        print(f"error: {path}: {message}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s) in {path}", file=sys.stderr)
        return 1

    print(f"{path}: {len(data['labels'])} labels OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
