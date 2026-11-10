"""Shared fixtures: a minimal project configuration with its own small schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engineering_bootstrap.config import CONFIG_NAMES

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "name"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "name": {"type": "string", "minLength": 1},
    },
}


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Return a ``.project`` directory in which every file is valid."""
    directory = tmp_path / ".project"
    schemas = directory / "schemas"
    schemas.mkdir(parents=True)
    for name in CONFIG_NAMES:
        (schemas / f"{name}-1.0.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        (directory / f"{name}.yml").write_text(
            f'schema_version: "1.0"\nname: "{name}"\n', encoding="utf-8"
        )
    return directory
