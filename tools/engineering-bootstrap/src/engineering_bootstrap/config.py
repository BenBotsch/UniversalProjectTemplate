"""Load and validate the project configuration in ``.project/``.

Each file is validated against ``.project/schemas/<name>-<schema_version>.schema.json`` of the
configured project, so the tool always uses the schema version the project declares. Files are
parsed with ``yaml.safe_load`` only; their content is never executed.

Cross-file consistency checks stay in the repository validator (``scripts/ci/validate_project.py``)
of the template; this module checks what the tool needs before it plans changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

CONFIG_NAMES = ("project", "workflow", "labels", "bootstrap", "quality-gates")
SCHEMA_DIR_NAME = "schemas"
ROOT_PATH = "(root)"


class ConfigError(Exception):
    """The configuration cannot be loaded; ``problems`` lists every reason."""

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        super().__init__("; ".join(str(problem) for problem in problems))


@dataclass(frozen=True)
class Problem:
    """One configuration problem.

    Attributes:
        file: Name of the affected file, for example ``labels.yml``.
        path: Dotted location inside the file, or ``(root)``.
        message: Human-readable description.
    """

    file: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.path}: {self.message}"


@dataclass(frozen=True)
class ProjectConfig:
    """Schema-valid project configuration.

    Attributes:
        directory: The ``.project`` directory the files were read from.
        files: Parsed content per configuration name, for example ``"labels"``.
    """

    directory: Path
    files: dict[str, dict[str, Any]]

    @property
    def bootstrap(self) -> dict[str, Any]:
        """The ``bootstrap`` section of ``bootstrap.yml``."""
        return self.files["bootstrap"].get("bootstrap", {})


def resolve_config_dir(path: Path) -> Path:
    """Return the configuration directory for a ``--config`` value.

    Args:
        path: A configuration file such as ``.project/bootstrap.yml`` or the directory itself.

    Returns:
        The directory that holds the configuration files.
    """
    return path if path.is_dir() else path.parent


def _read_yaml(path: Path) -> tuple[Any, list[Problem]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [Problem(path.name, ROOT_PATH, "file not found")]
    except OSError as exc:
        return None, [Problem(path.name, ROOT_PATH, f"cannot read file: {exc.strerror}")]
    try:
        return yaml.safe_load(text), []
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}" if mark is not None else ROOT_PATH
        reason = getattr(exc, "problem", None) or str(exc)
        return None, [Problem(path.name, where, f"invalid YAML syntax: {reason}")]


def _validate_schema(name: str, data: Any, schema_dir: Path) -> list[Problem]:
    file = f"{name}.yml"
    if not isinstance(data, dict):
        return [Problem(file, ROOT_PATH, "top level must be a mapping")]
    version = data.get("schema_version")
    if not isinstance(version, str):
        return [Problem(file, "schema_version", "missing or not a string")]
    schema_file = schema_dir / f"{name}-{version}.schema.json"
    if not schema_file.is_file():
        available = sorted(
            p.name.removeprefix(f"{name}-").removesuffix(".schema.json")
            for p in schema_dir.glob(f"{name}-*.schema.json")
        )
        message = f"unsupported schema_version {version!r}; supported: {available}"
        return [Problem(file, "schema_version", message)]
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [Problem(file, "schema_version", f"cannot read schema {schema_file.name}: {exc}")]
    problems = []
    for error in Draft202012Validator(schema).iter_errors(data):
        # oneOf/anyOf errors are vague; report the most specific sub-error instead.
        detail = best_match(error.context) if error.context else error
        location = ".".join(str(part) for part in detail.absolute_path) or ROOT_PATH
        problems.append(Problem(file, location, detail.message))
    return sorted(problems, key=lambda problem: (problem.path, problem.message))


def validate_config(directory: Path) -> tuple[dict[str, Any], dict[str, list[Problem]]]:
    """Read and schema-validate every configuration file.

    Args:
        directory: The ``.project`` directory.

    Returns:
        The parsed data of each readable file and the problems per configuration name; a name
        with an empty list is valid.
    """
    schema_dir = directory / SCHEMA_DIR_NAME
    data: dict[str, Any] = {}
    problems: dict[str, list[Problem]] = {}
    for name in CONFIG_NAMES:
        content, read_problems = _read_yaml(directory / f"{name}.yml")
        if read_problems:
            problems[name] = read_problems
            continue
        data[name] = content
        problems[name] = _validate_schema(name, content, schema_dir)
    return data, problems


def load_config(directory: Path) -> ProjectConfig:
    """Load the configuration and fail if any file is invalid.

    Args:
        directory: The ``.project`` directory.

    Returns:
        The validated configuration.

    Raises:
        ConfigError: If a file is missing, unreadable or does not match its schema.
    """
    data, problems = validate_config(directory)
    all_problems = [problem for name in CONFIG_NAMES for problem in problems[name]]
    if all_problems:
        raise ConfigError(all_problems)
    return ProjectConfig(directory=directory, files=data)
