"""Apply a technology profile to the working tree of a project (FEAT-031, ADR-0006).

A profile lives in ``profiles/<id>/`` of the template: ``profile.yml`` describes it and
``files/`` holds the files it adds. Applying it plans one change per path:

- every profile file is created; an identical file is ``noop``, a differing one is a conflict
  that is ``skipped`` unless ``force`` is set, and a file that is missing although
  ``project.yml`` already records the profile is ``skipped`` as removed by the project;
- the CI jobs, quality gates, Dependabot updates and labels of the profile are inserted as a
  block between ``# profile:<id>:start`` and ``# profile:<id>:end`` above the anchor lines
  ``# bootstrap:profile-*`` of the base files; a differing block is a conflict like a file;
- ``.project/project.yml`` gets the profile's languages and package managers and records the
  profile with its version in ``profiles``.

Profiles never edit the base workflows apart from these blocks; each profile calls its own
workflow from ``ci.yml``. Tokens such as ``PROJECT_PACKAGE`` are replaced in file paths and
content. Every edited YAML file is parsed again, so a run never leaves a file that does not load.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.resources.init import (
    PROJECT_FILE,
    replace_placeholders,
    set_yaml_scalars,
    token_pattern,
)

RESOURCE_NAME = "profile"
MANIFEST_NAME = "profile.yml"
FILES_DIR = "files"
SCHEMA_PATH = Path("_schema") / "profile.schema.json"
WORKFLOWS_DIR = ".github/workflows"
QUALITY_GATES_FILE = ".project/quality-gates.yml"
CI_FILE = f"{WORKFLOWS_DIR}/ci.yml"
DEPENDABOT_FILE = ".github/dependabot.yml"
LABELS_FILE = ".project/labels.yml"
ANCHOR_PREFIX = "# bootstrap:profile-"
GATES_ANCHOR = "# bootstrap:profile-gates"
JOBS_ANCHOR = "# bootstrap:profile-jobs"
NEEDS_ANCHOR = "# bootstrap:profile-needs"
UPDATES_ANCHOR = "# bootstrap:profile-updates"
LABELS_ANCHOR = "# bootstrap:profile-labels"
BLOCK_FILES = (QUALITY_GATES_FILE, CI_FILE, DEPENDABOT_FILE, LABELS_FILE)
PROFILE_ID = re.compile(r"[a-z][a-z0-9-]*")
_PROFILES_LINE = re.compile(r"profiles:\s*(?:\[\s*\])?\s*(?:#.*)?")
# The self-repository form is not accepted by actionlint yet; see the comment in ci.yml.
_CALL_COMMENT = "# zizmor: ignore[self-repository]"


class ProfileError(Exception):
    """The profile cannot be loaded; the message names the reason."""


class AnchorError(ValueError):
    """A base file lacks the anchor line that a profile block belongs above."""


@dataclass(frozen=True)
class CiJob:
    """A job of ``ci.yml`` that calls a workflow of the profile.

    Attributes:
        id: Job id in ``ci.yml``; also its name, so its jobs report as ``<id> / <job>``.
        workflow: File name of the called workflow in ``.github/workflows/``.
    """

    id: str
    workflow: str


@dataclass(frozen=True)
class Profile:
    """A loaded, consistent profile.

    Attributes:
        id: Profile id, the directory name below ``profiles/``.
        version: Semantic version, recorded in ``project.yml``.
        description: One line about the profile.
        requires_profiles: Profiles that must be applied first.
        languages: Values the profile adds to ``technology.languages``.
        package_managers: Values the profile adds to ``technology.package_managers``.
        files: Content of each file below ``files/``, keyed by its path there, tokens unreplaced.
        ci_jobs: Jobs that ``ci.yml`` gets.
        quality_gates: Gates that ``quality-gates.yml`` gets, by name.
        dependabot: Entries of ``updates`` in ``dependabot.yml``.
        labels: Entries of ``labels`` in ``labels.yml``.
    """

    id: str
    version: str
    description: str
    requires_profiles: tuple[str, ...]
    languages: tuple[str, ...]
    package_managers: tuple[str, ...]
    files: dict[str, str]
    ci_jobs: tuple[CiJob, ...]
    quality_gates: dict[str, dict[str, Any]]
    dependabot: tuple[dict[str, Any], ...]
    labels: tuple[dict[str, Any], ...]


def package_name(project_name: str) -> str:
    """Return the importable package name of a project: lowercase, other characters as ``_``.

    Raises:
        ValueError: If no letter remains or the name would start with a digit.
    """
    name = re.sub(r"[^a-z0-9]+", "_", project_name.lower()).strip("_")
    if not name or name[0].isdigit():
        raise ValueError(f"cannot derive a package name from {project_name!r}")
    return name


def replacements_for(name: str, description: str) -> dict[str, str]:
    """Return the token values that profile files use."""
    return {
        "PROJECT_NAME": name,
        "PROJECT_DESCRIPTION": description,
        "PROJECT_PACKAGE": package_name(name),
    }


def _is_safe_relative(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(path) and not pure.is_absolute() and ".." not in pure.parts and "\\" not in path


def _read_files(files_dir: Path, listed: Sequence[str]) -> dict[str, str]:
    present = (
        {path.relative_to(files_dir).as_posix() for path in files_dir.rglob("*") if path.is_file()}
        if files_dir.is_dir()
        else set()
    )
    unlisted = sorted(present - set(listed))
    missing = sorted(set(listed) - present)
    if unlisted:
        raise ProfileError(f"files not listed in {MANIFEST_NAME}: {', '.join(unlisted)}")
    if missing:
        raise ProfileError(f"listed files are missing in {FILES_DIR}/: {', '.join(missing)}")
    contents = {}
    for path in listed:
        if not _is_safe_relative(path):
            raise ProfileError(f"unsafe file path {path!r}")
        if path in (PROJECT_FILE, *BLOCK_FILES) or path.startswith(".git/"):
            raise ProfileError(f"{path} is a base file; profiles edit it through anchors only")
        try:
            contents[path] = (files_dir / path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ProfileError(f"{path} is not readable UTF-8 text: {exc}") from None
    return contents


def _check_jobs_have_gates(
    files: Mapping[str, str], ci_jobs: Sequence[CiJob], gates: Mapping[str, Mapping[str, Any]]
) -> None:
    """Every job of a profile workflow has a gate, and every gate names a profile workflow."""
    workflows = {job.workflow for job in ci_jobs}
    gated = {(gate["workflow"], gate["job"]) for gate in gates.values()}
    for workflow in sorted(workflows):
        path = f"{WORKFLOWS_DIR}/{workflow}"
        if path not in files:
            raise ProfileError(f"ci job calls {workflow}, but {FILES_DIR}/{path} does not exist")
        try:
            document = yaml.safe_load(files[path]) or {}
        except yaml.YAMLError as exc:
            raise ProfileError(f"{path} is not valid YAML: {exc}") from None
        jobs = document.get("jobs") if isinstance(document, dict) else None
        if not isinstance(jobs, dict) or not jobs:
            raise ProfileError(f"{path} has no jobs")
        ungated = sorted(job for job in jobs if (workflow, job) not in gated)
        if ungated:
            raise ProfileError(f"jobs of {workflow} without a quality gate: {', '.join(ungated)}")
    for name, gate in gates.items():
        if gate["workflow"] not in workflows:
            raise ProfileError(
                f"gate {name} names {gate['workflow']}, which no ci job of the profile calls"
            )


def load_profile(source: Path, profile_id: str) -> Profile:
    """Load ``<source>/<profile_id>/`` and check it against the profile schema.

    Args:
        source: Directory that holds the profiles and ``_schema/profile.schema.json``.
        profile_id: Directory name of the profile.

    Raises:
        ProfileError: If the profile is missing, invalid or inconsistent.
    """
    if not PROFILE_ID.fullmatch(profile_id):
        raise ProfileError(f"invalid profile id {profile_id!r}")
    directory = source / profile_id
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        known = sorted(
            path.parent.name for path in source.glob(f"*/{MANIFEST_NAME}") if path.is_file()
        )
        raise ProfileError(
            f"no profile {profile_id!r} in {source}; available: {', '.join(known) or 'none'}"
        )
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads((source / SCHEMA_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ProfileError(f"cannot read {profile_id}: {exc}") from None
    error = best_match(Draft202012Validator(schema).iter_errors(manifest))
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "(root)"
        raise ProfileError(f"{manifest_path}:{location}: {error.message}")
    if manifest["id"] != profile_id:
        raise ProfileError(f"{manifest_path}: id {manifest['id']!r} differs from the directory")

    files = _read_files(directory / FILES_DIR, manifest.get("files", []))
    ci_jobs = tuple(CiJob(job["id"], job["workflow"]) for job in manifest.get("ci_jobs", []))
    gates = dict(manifest.get("quality_gates", {}))
    _check_jobs_have_gates(files, ci_jobs, gates)
    technology = manifest.get("technology", {})
    return Profile(
        id=profile_id,
        version=manifest["version"],
        description=manifest["description"],
        requires_profiles=tuple(manifest.get("requires_profiles", [])),
        languages=tuple(technology.get("languages", [])),
        package_managers=tuple(technology.get("package_managers", [])),
        files=files,
        ci_jobs=ci_jobs,
        quality_gates=gates,
        dependabot=tuple(manifest.get("dependabot", [])),
        labels=tuple(manifest.get("labels", [])),
    )


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _is_flat(value: Any) -> bool:
    return not isinstance(value, dict | list) or (
        isinstance(value, list) and not any(isinstance(item, dict | list) for item in value)
    )


def _inline(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_scalar(item) for item in value) + "]"
    return _scalar(value)


def render_yaml(value: Any, indent: int = 0) -> list[str]:
    """Render mappings and lists in the style of the base files, one string per line.

    Sequences are indented below their key, strings are double-quoted and lists of scalars are
    written as flow sequences, which is what yamllint and the hand-written files expect.
    """
    pad = " " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict) and not item:
                lines.append(f"{pad}{key}: {{}}")
            elif _is_flat(item):
                lines.append(f"{pad}{key}: {_inline(item)}")
            else:
                lines.append(f"{pad}{key}:")
                lines.extend(render_yaml(item, indent + 2))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict | list):
                nested = render_yaml(item, indent + 2)
                lines.append(f"{pad}- {nested[0][indent + 2 :]}")
                lines.extend(nested[1:])
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    else:
        lines.append(f"{pad}{_scalar(value)}")
    return lines


def set_block(text: str, anchor: str, profile_id: str, body: Sequence[str]) -> tuple[str, str]:
    """Insert or replace the block of a profile directly above an anchor line.

    The block of a profile for an anchor is the one between the previous anchor and this one,
    so one file can hold a block per anchor, such as the jobs and the needs in ``ci.yml``.

    Returns:
        The new text and ``"noop"``, ``"insert"`` or ``"replace"``.

    Raises:
        AnchorError: If the anchor line is missing.
        ValueError: If the block has no end marker.
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += newline
    position = next((i for i, line in enumerate(lines) if line.strip() == anchor), None)
    if position is None:
        raise AnchorError(f"anchor line {anchor!r} is missing")
    anchor_line = lines[position]
    indent = anchor_line[: len(anchor_line) - len(anchor_line.lstrip())]
    start_marker, end_marker = f"# profile:{profile_id}:start", f"# profile:{profile_id}:end"
    wanted = [
        f"{indent}{line}{newline}" if line else newline
        for line in (start_marker, *body, end_marker)
    ]
    previous = max(
        (i for i in range(position) if lines[i].strip().startswith(ANCHOR_PREFIX)), default=-1
    )
    start = next(
        (i for i in range(previous + 1, position) if lines[i].strip() == start_marker), None
    )
    if start is None:
        return "".join(lines[:position] + wanted + lines[position:]), "insert"
    end = next((i for i in range(start + 1, position) if lines[i].strip() == end_marker), None)
    if end is None:
        raise ValueError(f"{start_marker} in line {start + 1} has no {end_marker}")
    current = lines[start : end + 1]
    if [line.rstrip() for line in current] == [line.rstrip() for line in wanted]:
        return "".join(lines), "noop"
    return "".join(lines[:start] + wanted + lines[end + 1 :]), "replace"


def set_profiles(text: str, profiles: Sequence[Mapping[str, str]]) -> str:
    """Rewrite the top-level ``profiles`` list of ``project.yml`` and keep everything else.

    Raises:
        ValueError: If the key is missing or the result does not parse to ``profiles``.
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if _PROFILES_LINE.fullmatch(line.rstrip("\r\n"))),
        None,
    )
    if start is None:
        raise ValueError(f"{PROJECT_FILE} has no top-level profiles list; migrate it to 1.1")
    end = start + 1
    while end < len(lines) and lines[end][:1] in (" ", "\t"):
        end += 1
    if profiles:
        rendered = ["profiles:"] + [
            line
            for entry in profiles
            for line in (f'  - id: "{entry["id"]}"', f'    version: "{entry["version"]}"')
        ]
    else:
        rendered = ["profiles: []"]
    result = "".join(lines[:start] + [line + newline for line in rendered] + lines[end:])
    if (yaml.safe_load(result) or {}).get("profiles") != [dict(entry) for entry in profiles]:
        raise ValueError("rewriting profiles did not produce the expected list")
    return result


def _union(current: Any, added: Sequence[str]) -> list[str]:
    values = list(current) if isinstance(current, list) else []
    return values + [value for value in added if value not in values]


@dataclass
class ProfileResource:
    """Engine resource that applies one profile to a working tree.

    Args:
        root: Root of the working tree.
        profile: The loaded profile.
        replacements: Values of ``PROJECT_NAME``, ``PROJECT_DESCRIPTION`` and
            ``PROJECT_PACKAGE``.
        force: Overwrite differing files and blocks instead of skipping them as conflicts.
    """

    root: Path
    profile: Profile
    replacements: Mapping[str, str]
    force: bool = False
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = ()
    _content: dict[str, str] = field(default_factory=dict, repr=False)

    def _targets(self) -> dict[str, str]:
        """Return the content of each profile file by its path in the project."""
        pattern = token_pattern(list(self.replacements))
        if pattern is None:
            return dict(self.profile.files)
        targets = {}
        for path, content in self.profile.files.items():
            target, _ = replace_placeholders(path, pattern, self.replacements)
            text, _ = replace_placeholders(content, pattern, self.replacements)
            if not _is_safe_relative(target):
                raise ValueError(f"{path} becomes the unsafe path {target!r}")
            targets[target] = text
        return targets

    def read_actual(self) -> dict[str, str | None]:
        """Read the base files and the files the profile writes; ``None`` if missing."""
        paths = [PROJECT_FILE, *BLOCK_FILES, *self._targets()]
        actual: dict[str, str | None] = {}
        for path in paths:
            target = self.root / path
            actual[path] = target.read_bytes().decode("utf-8") if target.is_file() else None
        return actual

    def desired(self) -> dict[str, str]:
        """Return the profile files with their tokens replaced."""
        return self._targets()

    def diff(self, actual: dict[str, str | None], desired: dict[str, str]) -> list[Change]:
        """Plan the files, the blocks and the record in ``project.yml``."""
        self._content = {}
        project_text = actual.get(PROJECT_FILE)
        if project_text is None:
            return [Change(self.name, PROJECT_FILE, Action.FAILED, "missing")]
        project = yaml.safe_load(project_text) or {}
        if not isinstance(project.get("profiles"), list):
            reason = "has no profiles list; migrate it to schema 1.1 first"
            return [Change(self.name, PROJECT_FILE, Action.FAILED, reason)]
        recorded = {entry["id"]: entry["version"] for entry in project["profiles"]}
        missing = [name for name in self.profile.requires_profiles if name not in recorded]
        if missing:
            reason = f"requires the profile(s) {', '.join(missing)}; apply them first"
            return [Change(self.name, PROJECT_FILE, Action.FAILED, reason)]

        changes = [
            self._file_change(path, actual.get(path), content, self.profile.id in recorded)
            for path, content in sorted(desired.items())
        ]
        changes.extend(self._block_changes(actual))
        changes.append(self._project_change(project_text, project, recorded))
        return changes

    def apply(self, change: Change) -> None:
        """Write one planned file."""
        content = self._content.get(change.key)
        if content is None:
            raise RuntimeError(f"no planned content for {change.key}")
        target = self.root / change.key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))

    def _file_change(self, path: str, current: str | None, content: str, recorded: bool) -> Change:
        if path.endswith(".toml"):
            try:
                tomllib.loads(content)
            except tomllib.TOMLDecodeError as exc:
                reason = f"is not valid TOML after replacing the tokens: {exc}"
                return Change(self.name, path, Action.FAILED, reason)
        if current == content:
            return Change(self.name, path, Action.NOOP, "matches the profile")
        if current is None:
            if recorded and not self.force:
                reason = "removed since the profile was applied; --force creates it again"
                return Change(self.name, path, Action.SKIPPED, reason)
            self._content[path] = content
            return Change(self.name, path, Action.CREATE, "profile file")
        if not self.force:
            reason = "conflict: differs from the profile; review it or rerun with --force"
            return Change(self.name, path, Action.SKIPPED, reason)
        self._content[path] = content
        return Change(self.name, path, Action.UPDATE, "overwritten with --force")

    def _blocks(self) -> dict[str, list[tuple[str, list[str]]]]:
        """Return the blocks per base file as ``(anchor, lines)``; empty parts are left out."""
        profile = self.profile
        blocks: dict[str, list[tuple[str, list[str]]]] = {}
        if profile.quality_gates:
            blocks[QUALITY_GATES_FILE] = [(GATES_ANCHOR, render_yaml(profile.quality_gates))]
        if profile.ci_jobs:
            jobs = [
                line
                for job in profile.ci_jobs
                for line in (
                    f"{job.id}:",
                    f'  name: "{job.id}"',
                    f"  uses: ./{WORKFLOWS_DIR}/{job.workflow} {_CALL_COMMENT}",
                )
            ]
            needs = [f"- {job.id}" for job in profile.ci_jobs]
            blocks[CI_FILE] = [(JOBS_ANCHOR, jobs), (NEEDS_ANCHOR, needs)]
        if profile.dependabot:
            blocks[DEPENDABOT_FILE] = [(UPDATES_ANCHOR, render_yaml(list(profile.dependabot)))]
        if profile.labels:
            blocks[LABELS_FILE] = [(LABELS_ANCHOR, render_yaml(list(profile.labels)))]
        return blocks

    def _block_changes(self, actual: Mapping[str, str | None]) -> list[Change]:
        changes = []
        for path, blocks in self._blocks().items():
            text = actual.get(path)
            if text is None:
                changes.append(Change(self.name, path, Action.FAILED, "missing"))
                continue
            new, outcomes = text, []
            try:
                for anchor, body in blocks:
                    new, outcome = set_block(new, anchor, self.profile.id, body)
                    outcomes.append(outcome)
                problem = self._check_block_file(path, new)
            except AnchorError as exc:
                reason = f"{exc}; restore it from the template to apply profiles"
                changes.append(Change(self.name, path, Action.FAILED, reason))
                continue
            except (ValueError, yaml.YAMLError) as exc:
                changes.append(Change(self.name, path, Action.FAILED, str(exc)))
                continue
            if problem:
                changes.append(Change(self.name, path, Action.FAILED, problem))
            elif all(outcome == "noop" for outcome in outcomes):
                changes.append(Change(self.name, path, Action.NOOP, "profile block matches"))
            elif "replace" in outcomes and not self.force:
                reason = "conflict: the profile block differs; review it or rerun with --force"
                changes.append(Change(self.name, path, Action.SKIPPED, reason))
            else:
                self._content[path] = new
                verb = "replace" if "replace" in outcomes else "insert"
                changes.append(
                    Change(self.name, path, Action.UPDATE, f"{verb} the block of {self.profile.id}")
                )
        return changes

    def _check_block_file(self, path: str, text: str) -> str | None:
        """Return why the edited base file is wrong, or ``None``."""
        document = yaml.safe_load(text)
        if path != QUALITY_GATES_FILE:
            return None
        gates = (document or {}).get("quality_gates") or {}
        for name, gate in self.profile.quality_gates.items():
            target = gate.get("covers")
            if target is not None and target not in gates:
                return f"gate {name} covers {target!r}, which quality-gates.yml does not define"
        names = re.findall(r"^  ([a-z][a-z0-9_]*):", text, flags=re.MULTILINE)
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            return f"gate(s) defined twice: {', '.join(duplicates)}"
        return None

    def _project_change(
        self, text: str, project: Mapping[str, Any], recorded: Mapping[str, str]
    ) -> Change:
        technology = project.get("technology") or {}
        lists: dict[tuple[str, str], str | bool | list[str]] = {}
        for key, added in (
            ("languages", self.profile.languages),
            ("package_managers", self.profile.package_managers),
        ):
            merged = _union(technology.get(key), added)
            if merged != technology.get(key):
                lists[("technology", key)] = merged
        entries = [dict(entry) for entry in project["profiles"]]
        wanted = {"id": self.profile.id, "version": self.profile.version}
        if self.profile.id not in recorded:
            entries.append(wanted)
        elif recorded[self.profile.id] != self.profile.version:
            entries = [wanted if entry["id"] == self.profile.id else entry for entry in entries]
        if not lists and entries == project["profiles"]:
            return Change(self.name, PROJECT_FILE, Action.NOOP, "profile is recorded")
        try:
            new = set_yaml_scalars(text, lists) if lists else text
            new = set_profiles(new, entries)
        except ValueError as exc:
            return Change(self.name, PROJECT_FILE, Action.FAILED, str(exc))
        self._content[PROJECT_FILE] = new
        details = {
            "profile": wanted,
            "technology": {key: value for (_, key), value in lists.items()},
        }
        reason = f"record {self.profile.id} {self.profile.version}"
        return Change(self.name, PROJECT_FILE, Action.UPDATE, reason, details)
