"""Validate the project configuration files in .project/ against their JSON Schemas.

Each file is validated against .project/schemas/<name>-<schema_version>.schema.json,
selected by the file's own ``schema_version``. After schema validation, the
label rules of check_labels.py and cross-file checks run:

- every label group and value named in workflow.yml ``issue_policy`` exists in labels.yml;
- ``development_branch`` differs from ``default_branch`` in project.yml;
- branches in workflow.yml are the default or development branch of project.yml,
  and releases come from the default branch;
- ``branch_name_pattern`` and ``tag_pattern`` are valid regular expressions.

The files are only parsed with ``yaml.safe_load``; their content is never executed.

Usage: python -I scripts/ci/validate_project.py [project_dir]   (default: .project)
Output: one line per problem as ``<file>:<path>: <message>``.
Exit codes: 0 valid, 1 invalid, missing or unreadable files.
Requires: pyyaml, jsonschema (see scripts/ci/requirements.txt).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

CONFIG_NAMES = ("project", "labels", "quality-gates", "workflow", "bootstrap")
SCHEMA_DIR_NAME = "schemas"
ROOT_PATH = "(root)"


@dataclass(frozen=True)
class Problem:
    """One validation problem.

    Attributes:
        file: Path of the affected file.
        path: Dotted location inside the file, or ``(root)``.
        message: Human-readable description.
    """

    file: Path
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.path}: {self.message}"


def _load_check_labels() -> ModuleType:
    """Load check_labels.py from this directory; ``python -I`` does not add it to sys.path."""
    path = Path(__file__).with_name("check_labels.py")
    spec = importlib.util.spec_from_file_location("check_labels", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_labels = _load_check_labels()


def load_config(path: Path) -> tuple[Any, list[Problem]]:
    """Parse one YAML configuration file.

    Args:
        path: File to read.

    Returns:
        The parsed data (``None`` on failure) and the problems found while reading.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [Problem(path, ROOT_PATH, "file not found")]
    except OSError as exc:
        return None, [Problem(path, ROOT_PATH, f"cannot read file: {exc.strerror}")]
    try:
        return yaml.safe_load(text), []
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}" if mark is not None else ROOT_PATH
        reason = getattr(exc, "problem", None) or str(exc)
        return None, [Problem(path, where, f"invalid YAML syntax: {reason}")]


def validate_schema(path: Path, data: Any, schema_dir: Path) -> list[Problem]:
    """Validate parsed data against the schema selected by its ``schema_version``.

    Args:
        path: File the data came from, used in messages; its stem names the schema.
        data: Parsed YAML content.
        schema_dir: Directory that holds ``<name>-<version>.schema.json`` files.

    Returns:
        All schema problems, sorted by location.
    """
    if not isinstance(data, dict):
        return [Problem(path, ROOT_PATH, "top level must be a mapping")]
    version = data.get("schema_version")
    if not isinstance(version, str):
        return [Problem(path, "schema_version", "missing or not a string")]
    schema_file = schema_dir / f"{path.stem}-{version}.schema.json"
    if not schema_file.is_file():
        available = sorted(
            p.name.removeprefix(f"{path.stem}-").removesuffix(".schema.json")
            for p in schema_dir.glob(f"{path.stem}-*.schema.json")
        )
        return [
            Problem(
                path,
                "schema_version",
                f"unsupported schema_version {version!r}; supported: {available}",
            )
        ]
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    problems = []
    for error in validator.iter_errors(data):
        # oneOf/anyOf errors are vague; report the most specific sub-error instead.
        detail = best_match(error.context) if error.context else error
        location = ".".join(str(part) for part in detail.absolute_path) or ROOT_PATH
        problems.append(Problem(path, location, detail.message))
    return sorted(problems, key=lambda problem: (problem.path, problem.message))


def check_cross_file(configs: dict[str, Any], paths: dict[str, Path]) -> list[Problem]:
    """Check consistency between the configuration files.

    Args:
        configs: Schema-valid parsed data, keyed by configuration name.
        paths: File path per configuration name, used in messages.

    Returns:
        All cross-file problems.
    """
    problems: list[Problem] = []
    labels = configs.get("labels")
    workflow = configs.get("workflow")
    project = configs.get("project")

    if labels is not None:
        problems.extend(
            Problem(paths["labels"], "labels", message)
            for message in check_labels.check_document(labels)
        )

    if workflow is not None:
        problems.extend(
            _check_regex(
                paths["workflow"],
                "branching.branch_name_pattern",
                workflow["branching"]["branch_name_pattern"],
            )
        )
        problems.extend(
            _check_regex(
                paths["workflow"],
                "releases.tag_pattern",
                workflow["releases"]["tag_pattern"],
            )
        )

    if labels is not None and workflow is not None:
        problems.extend(
            _check_issue_policy(labels, workflow["issue_policy"], paths["workflow"])
        )

    if project is not None:
        repository = project["repository"]
        default, development = (
            repository["default_branch"],
            repository["development_branch"],
        )
        if default == development:
            problems.append(
                Problem(
                    paths["project"],
                    "repository.development_branch",
                    f"must differ from default_branch ({default!r})",
                )
            )
        if workflow is not None:
            problems.extend(
                _check_branches(
                    workflow, {default, development}, default, paths["workflow"]
                )
            )
    return problems


def _check_regex(path: Path, location: str, pattern: str) -> list[Problem]:
    """Report a pattern that is not a valid regular expression; it is compiled, never matched."""
    try:
        re.compile(pattern)
    except re.error as exc:
        return [Problem(path, location, f"invalid regular expression: {exc}")]
    return []


def _check_issue_policy(
    labels: dict[str, Any], policy: dict[str, Any], path: Path
) -> list[Problem]:
    """Check that every group and value in ``issue_policy`` exists in labels.yml."""
    names = {label["name"] for label in labels["labels"]}
    groups = {label["group"] for label in labels["labels"]}
    problems = []
    for key in (
        "required_single_label_groups",
        "required_for_ready",
        "optional_single_label_groups",
    ):
        for index, group in enumerate(policy[key]):
            if group not in groups:
                problems.append(
                    Problem(
                        path,
                        f"issue_policy.{key}.{index}",
                        f"label group {group!r} is not defined in labels.yml",
                    )
                )
    for key, prefix in (("supported_types", "type"), ("supported_states", "status")):
        for index, value in enumerate(policy[key]):
            if f"{prefix}:{value}" not in names:
                problems.append(
                    Problem(
                        path,
                        f"issue_policy.{key}.{index}",
                        f"label '{prefix}:{value}' is not defined in labels.yml",
                    )
                )
    if policy["initial_status"] not in policy["supported_states"]:
        problems.append(
            Problem(
                path,
                "issue_policy.initial_status",
                f"{policy['initial_status']!r} is not in supported_states",
            )
        )
    return problems


def _check_branches(
    workflow: dict[str, Any], allowed: set[str], default: str, path: Path
) -> list[Problem]:
    """Check that workflow.yml only uses the branches defined in project.yml."""
    problems = []
    for name, branch_type in workflow["branching"]["branch_types"].items():
        base = f"branching.branch_types.{name}"
        references = [("source", branch_type["source"])]
        references += [
            (f"targets.{i}", target) for i, target in enumerate(branch_type["targets"])
        ]
        if "back_merge_to" in branch_type:
            references.append(("back_merge_to", branch_type["back_merge_to"]))
        for key, branch in references:
            if branch not in allowed:
                problems.append(
                    Problem(
                        path,
                        f"{base}.{key}",
                        f"branch {branch!r} is not defined in project.yml repository",
                    )
                )
    source = workflow["releases"]["source_branch"]
    if source != default:
        problems.append(
            Problem(
                path,
                "releases.source_branch",
                f"must be the default branch {default!r}, got {source!r}",
            )
        )
    return problems


def validate_project(project_dir: Path) -> list[Problem]:
    """Validate all configuration files in a ``.project`` directory.

    Cross-file checks only use files that passed schema validation.

    Args:
        project_dir: Directory that holds the configuration files and ``schemas/``.

    Returns:
        All problems found; empty if the configuration is valid.
    """
    schema_dir = project_dir / SCHEMA_DIR_NAME
    if not schema_dir.is_dir():
        return [Problem(schema_dir, ROOT_PATH, "schema directory not found")]

    problems: list[Problem] = []
    valid: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for name in CONFIG_NAMES:
        path = project_dir / f"{name}.yml"
        paths[name] = path
        data, read_problems = load_config(path)
        if read_problems:
            problems.extend(read_problems)
            continue
        schema_problems = validate_schema(path, data, schema_dir)
        problems.extend(schema_problems)
        if not schema_problems:
            valid[name] = data
    problems.extend(check_cross_file(valid, paths))
    return problems


def main(argv: list[str]) -> int:
    """Validate the configuration directory named in ``argv[1]`` and print the result.

    Args:
        argv: Command line; ``argv[1]`` is the optional path to the ``.project`` directory.

    Returns:
        Process exit code: 0 if the configuration is valid, 1 otherwise.
    """
    project_dir = Path(argv[1]) if len(argv) > 1 else Path(".project")
    problems = validate_project(project_dir)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} error(s) in {project_dir}", file=sys.stderr)
        return 1
    print(f"{project_dir}: {len(CONFIG_NAMES)} configuration files valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
