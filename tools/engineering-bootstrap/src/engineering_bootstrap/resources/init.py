"""Turn a local clone of a repository created from the template into a project (FEAT-028).

The resource works on the working tree of a local clone and plans one change per path:

- every ``bootstrap.template_only_paths`` entry is deleted; a missing path is ``noop``;
- ``.project/project.yml`` gets the project name, description and visibility,
  ``is_template: false`` and the template source; comments and layout are kept;
- ``LICENSE`` is written from the GitHub license API, or deleted for license ``none``;
- every other tracked UTF-8 text file loses its ``template-only:start`` / ``template-only:end``
  blocks and gets its placeholder tokens replaced; ``README.md`` also gets its ``## License``
  section and ``.github/CODEOWNERS`` the project's code owner instead of the template's.

Files in ``template_only_paths`` and files matching ``placeholder_allowlist`` are not edited,
the same exclusions repository validation applies. :func:`run_init` wraps the resource: with
``apply`` it creates a branch from the development branch, writes the changes, runs the
checkout's ``scripts/ci/validate_repository.py`` and commits. It never pushes.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from engineering_bootstrap.engine import WRITE_ACTIONS, Action, Change, Engine
from engineering_bootstrap.git import Git, GitError
from engineering_bootstrap.github import NotFoundError

RESOURCE_NAME = "init"
VALIDATION_RESOURCE = "validation"
GIT_RESOURCE = "git"
VALIDATOR = "scripts/ci/validate_repository.py"
PROJECT_FILE = ".project/project.yml"
LICENSE_FILE = "LICENSE"
README_FILE = "README.md"
CODEOWNERS_FILE = ".github/CODEOWNERS"
LICENSE_NONE = "none"
LICENSE_HEADING = "## License"
MARKER_START = "template-only:start"
MARKER_END = "template-only:end"
BRANCH_FORMAT = "chore/{issue}-project-init"
COMMIT_MESSAGE = "chore: initialize project from template\n\nRefs: #{issue}\n"
VALIDATION_TIMEOUT = 300
# Same defaults as scripts/ci/validate_repository.py when workflow.yml names no tokens.
DEFAULT_PLACEHOLDER_TOKENS = (
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    "OWNER/REPOSITORY",
    "@OWNER_OR_TEAM",
    "OWNER/",
)
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 350
CODE_OWNER_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9-]{0,38}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,99})?"
)
LICENSE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}")
_YEAR_RANGE = r"\d{4}(?:\s*-\s*\d{4})?"
_SECTION_LINE = re.compile(r"([A-Za-z_][\w-]*):\s*(?:#.*)?")
_KEY_LINE = re.compile(r"(  )([A-Za-z_][\w-]*):(\s*)(.*)")


class InitRefusedError(Exception):
    """``init`` must not run against this repository or checkout."""


class InitClient(Protocol):
    """The part of :class:`~engineering_bootstrap.github.GitHubClient` that ``init`` uses."""

    def get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return the JSON body of a GET request."""
        ...


@dataclass(frozen=True)
class License:
    """A license text from the GitHub licenses API.

    Attributes:
        spdx_id: SPDX identifier, for example ``MIT``.
        name: Display name, for example ``MIT License``.
        body: License text with GitHub's ``[year]`` and ``[fullname]`` fields.
    """

    spdx_id: str
    name: str
    body: str


@dataclass(frozen=True)
class InitValues:
    """The values that replace the template's placeholders.

    Attributes:
        repo: Repository as ``OWNER/NAME``.
        name: Project name.
        description: One-line project description.
        visibility: ``public``, ``private`` or ``internal``, as GitHub reports it.
        code_owner: User or ``org/team`` without ``@`` for ``.github/CODEOWNERS``.
        template_source: Template repository as ``OWNER/NAME``.
        copyright_holder: Holder named in ``LICENSE`` or the README.
        year: Copyright year.
        license: License to write, or ``None`` for no license ("All rights reserved").
    """

    repo: str
    name: str
    description: str
    visibility: str
    code_owner: str
    template_source: str
    copyright_holder: str
    year: int
    license: License | None

    @property
    def owner(self) -> str:
        """Owner part of :attr:`repo`."""
        return self.repo.split("/", 1)[0]

    @property
    def template_owner(self) -> str:
        """Owner part of :attr:`template_source`, the code owner the template names."""
        return self.template_source.split("/", 1)[0]

    def replacements(self) -> dict[str, str]:
        """Return the value of each known placeholder token."""
        return {
            "PROJECT_NAME": self.name,
            "PROJECT_DESCRIPTION": self.description,
            "OWNER/REPOSITORY": self.repo,
            "@OWNER_OR_TEAM": f"@{self.code_owner}",
            "OWNER/": f"{self.owner}/",
        }

    def license_sentence(self) -> str:
        """Return the body of the README's ``## License`` section."""
        if self.license is None:
            return f"Copyright (c) {self.copyright_holder}. All rights reserved."
        return f"This project is licensed under the [{self.license.name}]({LICENSE_FILE})."

    def license_text(self) -> str | None:
        """Return the content of ``LICENSE``, or ``None`` if the project has no license."""
        if self.license is None:
            return None
        body = self.license.body.replace("[year]", str(self.year))
        return body.replace("[fullname]", self.copyright_holder).rstrip() + "\n"


@dataclass(frozen=True)
class InitSettings:
    """Paths and tokens from the configuration, shared with repository validation.

    Attributes:
        template_only_paths: ``bootstrap.template_only_paths`` of ``bootstrap.yml``.
        placeholder_tokens: ``repository_validation.placeholder_tokens`` of ``workflow.yml``.
        placeholder_allowlist: Globs of files that name the tokens on purpose.
    """

    template_only_paths: tuple[str, ...]
    placeholder_tokens: tuple[str, ...] = DEFAULT_PLACEHOLDER_TOKENS
    placeholder_allowlist: tuple[str, ...] = ()


@dataclass(frozen=True)
class InitOptions:
    """Values given on the command line; ``None`` falls back to the configuration or GitHub."""

    name: str | None = None
    description: str | None = None
    code_owner: str | None = None
    license: str | None = None
    copyright_holder: str | None = None
    template_source: str | None = None


def settings_from_config(files: Mapping[str, Mapping[str, Any]]) -> InitSettings:
    """Build the settings from the parsed, schema-valid configuration files."""
    validation = files["workflow"].get("repository_validation", {})
    return InitSettings(
        template_only_paths=tuple(files["bootstrap"]["bootstrap"]["template_only_paths"]),
        placeholder_tokens=tuple(validation.get("placeholder_tokens", DEFAULT_PLACEHOLDER_TOKENS)),
        placeholder_allowlist=tuple(validation.get("placeholder_allowlist", ())),
    )


def _single_line(value: str, what: str, limit: int) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{what} is empty")
    if len(value) > limit or any(char in value for char in "\r\n"):
        raise ValueError(f"{what} must be one line of at most {limit} characters")
    return value


def fetch_license(client: InitClient, license_id: str) -> License:
    """Return a license text from ``GET /licenses/{key}``.

    Raises:
        ValueError: If the id is malformed or GitHub does not offer the license.
    """
    if not LICENSE_ID_PATTERN.fullmatch(license_id):
        raise ValueError(f"invalid license id {license_id!r}")
    try:
        data = client.get_json(f"/licenses/{license_id.lower()}")
    except NotFoundError:
        raise ValueError(
            f"GitHub offers no license {license_id!r}; see https://api.github.com/licenses"
        ) from None
    return License(spdx_id=data["spdx_id"], name=data["name"], body=data["body"])


def values_from_github(
    client: InitClient,
    repo: str,
    repository: Mapping[str, Any],
    init_section: Mapping[str, Any],
    options: InitOptions,
    year: int,
) -> InitValues:
    """Combine command line options, the ``init`` section and the GitHub repository.

    Args:
        client: GitHub client, for the owner's profile and the license text.
        repo: Repository as ``OWNER/NAME``.
        repository: Body of ``GET /repos/{repo}``.
        init_section: ``init`` of ``bootstrap.yml``; empty for schema versions before 1.3.
        options: Command line values; they take precedence.
        year: Copyright year.

    Raises:
        ValueError: If a value is missing or invalid.
    """
    owner = repository["owner"]
    name = _single_line(options.name or repository["name"], "project name", MAX_NAME_LENGTH)
    description = options.description or repository.get("description") or ""
    if not description.strip():
        raise ValueError("the repository has no description; set one on GitHub or --description")
    description = _single_line(description, "description", MAX_DESCRIPTION_LENGTH)

    template = repository.get("template_repository") or {}
    template_source = options.template_source or template.get("full_name")
    if not template_source:
        raise ValueError(
            "GitHub names no template for this repository; pass --template-source OWNER/NAME"
        )

    code_owner = options.code_owner or init_section.get("code_owner")
    if code_owner is None:
        if owner.get("type") == "Organization":
            raise ValueError("an organization needs a team as code owner; pass --code-owner")
        code_owner = owner["login"]
    code_owner = code_owner.removeprefix("@")
    if not CODE_OWNER_PATTERN.fullmatch(code_owner):
        raise ValueError(f"invalid code owner {code_owner!r}; expected USER or ORG/TEAM")

    license_id = options.license or init_section.get("license")
    if not license_id:
        raise ValueError("no license: set init.license in bootstrap.yml or pass --license")
    holder = options.copyright_holder or init_section.get("copyright_holder")
    if holder is None:
        profile = client.get_json(f"/users/{owner['login']}")
        holder = profile.get("name") or owner["login"]
    holder = _single_line(holder, "copyright holder", 200)
    if "[" in holder or "]" in holder:
        raise ValueError("the copyright holder must not contain '[' or ']'")

    license_ = None if license_id.lower() == LICENSE_NONE else fetch_license(client, license_id)
    return InitValues(
        repo=repo,
        name=name,
        description=description,
        visibility=repository["visibility"],
        code_owner=code_owner,
        template_source=template_source,
        copyright_holder=holder,
        year=year,
        license=license_,
    )


def _remote_names_repo(url: str, repo: str) -> bool:
    normalized = url.strip().rstrip("/").removesuffix(".git").lower()
    return normalized.endswith((f"/{repo.lower()}", f":{repo.lower()}"))


def check_target(
    git: Git, repo: str, repository: Mapping[str, Any], project_file: Mapping[str, Any]
) -> None:
    """Refuse a run that could wipe the template or edit the wrong checkout (R8).

    Raises:
        InitRefusedError: If GitHub marks the repository as a template, if ``project.yml`` is the
            template's own (``is_template: true`` and ``template.source`` equal to ``repo``), or if
            the checkout's ``origin`` is not ``repo``.
    """
    if repository.get("is_template"):
        raise InitRefusedError(f"{repo} is a template repository on GitHub; init would wipe it")
    project = project_file.get("project", {})
    source = project_file.get("template", {}).get("source", "")
    if project.get("is_template") is True and source.lower() == repo.lower():
        raise InitRefusedError(f"{repo} is the template source named in {PROJECT_FILE}")
    url = git.remote_url()
    if url is None or not _remote_names_repo(url, repo):
        raise InitRefusedError(
            f"the checkout's origin ({url or 'missing'}) is not {repo}; run init in a clone of it"
        )


def token_pattern(tokens: Sequence[str]) -> re.Pattern[str] | None:
    """Build one regex for all tokens, longest first; a token must not continue a longer name.

    This is the matching of ``validate_repository.py``, so init replaces what validation reports.
    """
    if not tokens:
        return None
    alternatives = "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternatives})")


def replace_placeholders(
    text: str, pattern: re.Pattern[str], replacements: Mapping[str, str]
) -> tuple[str, Counter[str]]:
    """Replace each token that has a value; return the text and the count per token."""
    counts: Counter[str] = Counter()

    def substitute(match: re.Match[str]) -> str:
        token = match.group(0)
        if token not in replacements:
            return token
        counts[token] += 1
        return replacements[token]

    return pattern.sub(substitute, text), counts


def remove_template_blocks(text: str) -> tuple[str, int]:
    """Remove every block from a ``template-only:start`` to a ``template-only:end`` line.

    Both marker lines are removed with the block, whatever comment syntax surrounds them. A blank
    line after a block that follows a blank line is removed too, so no double blank line remains.

    Returns:
        The text and the number of removed blocks.

    Raises:
        ValueError: If the markers are unbalanced or nested.
    """
    kept: list[str] = []
    start: int | None = None
    blocks = 0
    drop_blank = False
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        if MARKER_START in line:
            if start is not None:
                raise ValueError(f"line {number}: {MARKER_START} inside the block of line {start}")
            start = number
        elif MARKER_END in line:
            if start is None:
                raise ValueError(f"line {number}: {MARKER_END} without {MARKER_START}")
            start = None
            blocks += 1
            drop_blank = not kept or not kept[-1].strip()
        elif start is None:
            if not (drop_blank and not line.strip()):
                kept.append(line)
            drop_blank = False
    if start is not None:
        raise ValueError(f"line {start}: {MARKER_START} without {MARKER_END}")
    return "".join(kept), blocks


def set_section(text: str, heading: str, body: str) -> str:
    """Replace the content of a Markdown section, or append the section if it is missing.

    The section ends at the next heading of level one or two.
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.rstrip("\r\n") == heading), None)
    if start is None:
        return f"{text.rstrip()}{newline}{newline}{heading}{newline}{newline}{body}{newline}"
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith(("# ", "## "))),
        len(lines),
    )
    section = [f"{heading}{newline}", newline, f"{body}{newline}"]
    if end < len(lines):
        section.append(newline)
    return "".join(lines[:start] + section + lines[end:])


def replace_code_owner(text: str, old: str, new: str) -> tuple[str, int]:
    """Replace the owner ``@old`` by ``@new``; teams such as ``@old/team`` stay unchanged."""
    if old.lower() == new.lower():
        return text, 0
    pattern = re.compile(rf"(?<![\w@./-])@{re.escape(old)}(?![\w/-])", re.IGNORECASE)
    return pattern.subn(f"@{new}", text)


def _split_value(rest: str) -> tuple[str, str]:
    """Split a YAML value from a trailing comment."""
    if rest[:1] in ('"', "'"):
        quote, index = rest[0], 1
        while index < len(rest):
            if quote == '"' and rest[index] == "\\":
                index += 2
                continue
            if rest[index] == quote:
                if quote == "'" and rest[index + 1 : index + 2] == "'":
                    index += 2
                    continue
                break
            index += 1
        end = index + 1
    else:
        comment = re.search(r"\s#", rest)
        end = comment.start() if comment else len(rest)
    return rest[:end], rest[end:]


def _render_scalar(value: str | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def set_yaml_scalars(text: str, values: Mapping[tuple[str, str], str | bool]) -> str:
    """Set ``section.key`` scalars of a two-level YAML file and keep comments and layout.

    Only keys indented by two spaces directly below a top-level section are found.

    Raises:
        ValueError: If a key is missing or the result does not parse to the given values.
    """
    lines = text.splitlines(keepends=True)
    remaining = dict(values)
    section: str | None = None
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        ending = line[len(content) :]
        if _SECTION_LINE.fullmatch(content):
            section = content.split(":", 1)[0]
            continue
        if content and not content[0].isspace():
            section = None
            continue
        match = _KEY_LINE.fullmatch(content)
        if match is None or (section, match.group(2)) not in remaining:
            continue
        indent, key, space, rest = match.groups()
        _, comment = _split_value(rest)
        rendered = _render_scalar(remaining.pop((section, key)))
        lines[index] = f"{indent}{key}:{space or ' '}{rendered}{comment}{ending}"
    if remaining:
        missing = ", ".join(f"{section}.{key}" for section, key in remaining)
        raise ValueError(f"cannot find {missing}")
    result = "".join(lines)
    parsed = yaml.safe_load(result)
    for (section_name, key), value in values.items():
        if parsed.get(section_name, {}).get(key) != value:
            raise ValueError(f"setting {section_name}.{key} did not produce the expected value")
    return result


def _is_below(path: str, prefixes: Sequence[str]) -> bool:
    for prefix in prefixes:
        stripped = prefix.strip("/")
        if stripped and (path == stripped or path.startswith(stripped + "/")):
            return True
    return False


def _read_text(path: Path) -> str | None:
    """Return the content of a UTF-8 text file, or ``None`` for binary or unreadable files."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _license_matches(current: str, values: InitValues) -> bool:
    """Return whether ``LICENSE`` is the configured license for the holder, in any year."""
    if values.license is None:
        return False
    pattern = re.escape(values.license.body.rstrip())
    pattern = pattern.replace(re.escape("[year]"), _YEAR_RANGE)
    pattern = pattern.replace(re.escape("[fullname]"), re.escape(values.copyright_holder))
    return re.fullmatch(pattern, current.rstrip()) is not None


@dataclass(frozen=True)
class Snapshot:
    """The parts of the working tree that init reads.

    Attributes:
        texts: Content of each tracked file outside the template-only paths; ``None`` for binary
            or unreadable files.
        present_template_only: Template-only paths that exist.
        license_text: Content of ``LICENSE``, or ``None`` if it does not exist.
    """

    texts: dict[str, str | None]
    present_template_only: list[str]
    license_text: str | None


@dataclass
class InitResource:
    """Engine resource that initializes the working tree of a local clone.

    Args:
        root: Root of the working tree.
        values: Project values.
        settings: Template-only paths and placeholder configuration.
        list_files: Returns the tracked files; :meth:`Git.tracked_files` in production.
    """

    root: Path
    values: InitValues
    settings: InitSettings
    list_files: Callable[[], list[str]]
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = ()
    _content: dict[str, str | None] = field(default_factory=dict, repr=False)

    def read_actual(self) -> Snapshot:
        """Read the tracked files and the template-only paths."""
        texts = {
            path: _read_text(self.root / path)
            for path in self.list_files()
            if not _is_below(path, self.settings.template_only_paths)
        }
        present = [
            path
            for path in self.settings.template_only_paths
            if os.path.lexists(self.root / path.strip("/"))
        ]
        license_path = self.root / LICENSE_FILE
        license_text = _read_text(license_path) if license_path.is_file() else ""
        return Snapshot(texts, present, license_text if license_path.is_file() else None)

    def desired(self) -> InitValues:
        """Return the project values."""
        return self.values

    def diff(self, actual: Snapshot, desired: InitValues) -> list[Change]:
        """Plan the deletions and file edits; ``noop`` for paths that already match."""
        self._content = {}
        changes = self._template_only_changes(actual)
        changes.append(self._project_change(actual))
        changes.append(self._license_change(actual, desired))
        changes.extend(self._text_changes(actual, desired))
        return changes

    def apply(self, change: Change) -> None:
        """Write, create or delete one path."""
        target = self.root / change.key.strip("/")
        if change.action is Action.DELETE:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            # Remove parents that the deletion left empty, such as tools/ for tools/x/.
            parent = target.parent
            while parent != self.root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
            return
        content = self._content.get(change.key)
        if content is None:
            raise RuntimeError(f"no planned content for {change.key}")
        target.write_bytes(content.encode("utf-8"))

    def _template_only_changes(self, actual: Snapshot) -> list[Change]:
        changes = []
        root = self.root.resolve()
        for path in self.settings.template_only_paths:
            target = self.root / path.strip("/")
            if path not in actual.present_template_only:
                changes.append(Change(self.name, path, Action.NOOP, "already removed"))
            elif not target.resolve().is_relative_to(root) and not target.is_symlink():
                reason = "resolves outside the working tree; not deleted"
                changes.append(Change(self.name, path, Action.FAILED, reason))
            else:
                changes.append(Change(self.name, path, Action.DELETE, "template-only path"))
        return changes

    def _project_change(self, actual: Snapshot) -> Change:
        text = actual.texts.get(PROJECT_FILE)
        if text is None:
            return Change(self.name, PROJECT_FILE, Action.FAILED, "missing or not UTF-8 text")
        wanted: dict[tuple[str, str], str | bool] = {
            ("project", "name"): self.values.name,
            ("project", "description"): self.values.description,
            ("project", "visibility"): self.values.visibility,
            ("project", "is_template"): False,
            ("template", "source"): self.values.template_source,
        }
        parsed = yaml.safe_load(text) or {}
        differing = {
            key: value
            for key, value in wanted.items()
            if parsed.get(key[0], {}).get(key[1]) != value
        }
        if not differing:
            return Change(self.name, PROJECT_FILE, Action.NOOP, "project values are set")
        try:
            self._content[PROJECT_FILE] = set_yaml_scalars(text, differing)
        except ValueError as exc:
            return Change(self.name, PROJECT_FILE, Action.FAILED, str(exc))
        fields = {f"{section}.{key}": value for (section, key), value in differing.items()}
        return Change(
            self.name, PROJECT_FILE, Action.UPDATE, f"set {', '.join(fields)}", {"fields": fields}
        )

    def _license_change(self, actual: Snapshot, values: InitValues) -> Change:
        desired = values.license_text()
        if desired is None or values.license is None:
            if actual.license_text is None:
                return Change(self.name, LICENSE_FILE, Action.NOOP, "no license")
            return Change(self.name, LICENSE_FILE, Action.DELETE, "license none")
        details = {"license": values.license.spdx_id, "holder": values.copyright_holder}
        if actual.license_text is not None and _license_matches(actual.license_text, values):
            return Change(self.name, LICENSE_FILE, Action.NOOP, "license matches", details)
        self._content[LICENSE_FILE] = desired
        action = Action.CREATE if actual.license_text is None else Action.UPDATE
        return Change(self.name, LICENSE_FILE, action, f"write {values.license.spdx_id}", details)

    def _skip_text(self, path: str) -> bool:
        if path in (PROJECT_FILE, LICENSE_FILE):
            return True
        return any(fnmatch.fnmatchcase(path, glob) for glob in self.settings.placeholder_allowlist)

    def _text_changes(self, actual: Snapshot, values: InitValues) -> list[Change]:
        pattern = token_pattern(self.settings.placeholder_tokens)
        replacements = values.replacements()
        changes: list[Change] = []
        unknown: Counter[str] = Counter()
        for path, text in sorted(actual.texts.items()):
            if text is None or self._skip_text(path):
                continue
            try:
                new, blocks = remove_template_blocks(text)
            except ValueError as exc:
                changes.append(Change(self.name, path, Action.FAILED, f"template block: {exc}"))
                continue
            details: dict[str, Any] = {}
            if blocks:
                details["template_blocks"] = blocks
            if pattern is not None:
                new, counts = replace_placeholders(new, pattern, replacements)
                if counts:
                    details["placeholders"] = dict(sorted(counts.items()))
                unknown.update(match.group(0) for match in pattern.finditer(new))
            if path == README_FILE:
                with_license = set_section(new, LICENSE_HEADING, values.license_sentence())
                if with_license != new:
                    details["license_section"] = True
                new = with_license
            if path == CODEOWNERS_FILE:
                new, owners = replace_code_owner(new, values.template_owner, values.code_owner)
                if owners:
                    details["code_owner"] = values.code_owner
            if new == text:
                continue
            self._content[path] = new
            changes.append(Change(self.name, path, Action.UPDATE, _describe(details), details))
        for token in sorted(unknown):
            reason = "no value is known for this token; replace it by hand"
            changes.append(Change(self.name, f"placeholder:{token}", Action.SKIPPED, reason))
        return changes


def _describe(details: Mapping[str, Any]) -> str:
    parts = []
    if "template_blocks" in details:
        parts.append(f"remove {details['template_blocks']} template-only block(s)")
    if "placeholders" in details:
        parts.append(f"replace {sum(details['placeholders'].values())} placeholder(s)")
    if "license_section" in details:
        parts.append("set the license section")
    if "code_owner" in details:
        parts.append(f"set code owner @{details['code_owner']}")
    return "; ".join(parts) or "normalize"


def run_validation(root: Path) -> Change:
    """Run the checkout's repository validation and report its errors (R6).

    The validator is the checkout's own ``scripts/ci/validate_repository.py``, run with this
    Python in isolated mode; it reads files and never executes them.
    """
    script = root / VALIDATOR
    if not script.is_file():
        return Change(VALIDATION_RESOURCE, VALIDATOR, Action.FAILED, "validator is missing")
    try:
        # Fixed interpreter and arguments without a shell.
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-I", str(script), "--format", "json", str(root)],
            capture_output=True,
            check=False,
            timeout=VALIDATION_TIMEOUT,
        )
        document = json.loads(result.stdout.decode("utf-8"))
        findings = document["findings"]
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError) as exc:
        stderr = locals().get("result")
        message = stderr.stderr.decode("utf-8", "replace").strip() if stderr else ""
        reason = f"validator did not run: {message or type(exc).__name__}"
        return Change(VALIDATION_RESOURCE, VALIDATOR, Action.FAILED, reason)
    errors = [
        f"{item['rule']} {item['file']}"
        + (f":{item['line']}" if item.get("line") else "")
        + f": {item['message']}"
        for item in findings
        if item.get("severity", "error") == "error"
    ]
    warnings = len(findings) - len(errors)
    details = {"errors": errors, "warnings": warnings}
    if errors:
        reason = f"{len(errors)} error(s): " + "; ".join(errors[:5])
        return Change(VALIDATION_RESOURCE, VALIDATOR, Action.FAILED, reason, details)
    reason = f"passed with {warnings} warning(s)"
    return Change(VALIDATION_RESOURCE, VALIDATOR, Action.NOOP, reason, details)


def _git_failure(key: str, reason: str) -> Change:
    return Change(GIT_RESOURCE, key, Action.FAILED, reason)


def run_init(
    git: Git,
    resource_factory: Callable[[], InitResource],
    *,
    apply: bool,
    issue: int | None,
    development_branch: str,
    validate: Callable[[Path], Change] = run_validation,
) -> list[Change]:
    """Plan the initialization and, with ``apply``, write, validate and commit it on a branch.

    Args:
        git: Git of the checkout.
        resource_factory: Returns a fresh :class:`InitResource` for the working tree.
        apply: Write the changes; otherwise only plan them.
        issue: Issue number for the branch name and commit; required to write changes.
        development_branch: Branch the init branch starts from, from ``project.yml``.
        validate: Runs repository validation; injectable for tests.

    Returns:
        The changes of the resource, followed by the validation and the Git step.
    """
    branch = BRANCH_FORMAT.format(issue=issue if issue is not None else "<issue>")
    plan = Engine([resource_factory()], allow_destructive=True).run(apply=False)
    writes = [change for change in plan if change.action in WRITE_ACTIONS]
    if any(change.action is Action.FAILED for change in plan):
        return [*plan, Change(GIT_RESOURCE, branch, Action.SKIPPED, "planning failed")]
    if not writes:
        return [*plan, validate(git.root), Change(GIT_RESOURCE, branch, Action.NOOP, "no change")]
    if not apply:
        reason = f"create from {development_branch} and commit {len(writes)} change(s)"
        skipped = Change(VALIDATION_RESOURCE, VALIDATOR, Action.SKIPPED, "runs with --apply")
        return [*plan, skipped, Change(GIT_RESOURCE, branch, Action.CREATE, reason)]

    if issue is None:
        return [*plan, _git_failure(branch, "--apply needs --issue for the branch name")]
    try:
        dirty = git.status()
        if dirty:
            return [*plan, _git_failure(branch, f"working tree is not clean: {dirty[0]}")]
        start = next(
            (
                ref
                for ref in (development_branch, f"origin/{development_branch}")
                if git.ref_exists(ref)
            ),
            None,
        )
        if start is None:
            return [*plan, _git_failure(branch, f"branch {development_branch} does not exist")]
        git.create_branch(branch, start)
    except GitError as exc:
        return [*plan, _git_failure(branch, str(exc))]

    # Plan again: the new branch may differ from the checkout that was planned first.
    changes = Engine([resource_factory()], allow_destructive=True).run(apply=True)
    if any(change.action is Action.FAILED for change in changes):
        return [*changes, _git_failure(branch, "not committed; inspect the branch")]
    try:
        git.stage_all()
        validation = validate(git.root)
        if validation.action is Action.FAILED:
            reason = "not committed: validation failed; the changes are staged on the branch"
            return [*changes, validation, _git_failure(branch, reason)]
        commit = git.commit(COMMIT_MESSAGE.format(issue=issue))
    except GitError as exc:
        return [*changes, _git_failure(branch, str(exc))]
    next_steps = [
        f"git push --set-upstream origin {branch}",
        f"gh pr create --base {development_branch} --head {branch} --fill",
    ]
    reason = f"committed {commit[:12]} on {branch}; push it and open a pull request"
    details = {"commit": commit, "base": start, "next_steps": next_steps}
    return [
        *changes,
        validation,
        Change(GIT_RESOURCE, branch, Action.CREATE, reason, details, True),
    ]
