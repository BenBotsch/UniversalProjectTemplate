"""Validate the structure and template hygiene of a repository.

Rules, each reported with its ID:

- ``REPO-REQUIRED``: every ``repository_validation.required_files`` entry exists.
- ``REPO-PLACEHOLDER``: in a derived repository (``project.is_template: false``), no tracked
  text file contains a ``placeholder_tokens`` entry, except files in ``template_only_paths``
  and files matching ``placeholder_allowlist``.
- ``REPO-TEMPLATE-ONLY``: in a derived repository, no tracked file lies below a
  ``bootstrap.template_only_paths`` entry.
- ``REPO-TEMPLATE-MARKER``: in a derived repository, no tracked text file outside the
  template-only paths and the placeholder allowlist contains a ``template-only:start`` or
  ``template-only:end`` marker; ``project-bootstrap init`` removes these blocks.
- ``REPO-DEAD-LINK-TEMPLATE``: no Markdown file outside the template-only paths links to a
  template-only path, in both template and derived repositories.
- ``REPO-DOCS-INDEX``: every Markdown file under ``docs/`` except ``README.md`` and
  ``_template.md`` is linked from ``docs/INDEX.md``, and every relative link in the index
  resolves. Severity follows ``repository_validation.docs_index_severity``.
- ``REPO-ISSUE-FORMS``: the issue forms are consistent with the labels
  (``check_issue_forms.py``), if ``.github/ISSUE_TEMPLATE/`` exists.
- ``REPO-CONFIG``: the configuration this validator reads is readable.

Only files tracked by Git are scanned (``git ls-files``, run without a shell). File content
is only read as text; it is never executed.

Usage: python -I scripts/ci/validate_repository.py [--format text|json] [repository_dir]
Output: text mode prints one line per finding as ``<RULE-ID> <file>: <message>``;
json mode prints one JSON document with all findings.
Exit codes: 0 no errors (warnings allowed), 1 at least one error.
Requires: pyyaml (see scripts/ci/requirements.txt) and git on PATH.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import posixpath
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

DEFAULT_REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    ".project/project.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/config.yml",
)
TEMPLATE_MARKER = re.compile(r"template-only:(?:start|end)")
DEFAULT_PLACEHOLDER_TOKENS = (
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    "OWNER/REPOSITORY",
    "@OWNER_OR_TEAM",
    "OWNER/",
)
DEFAULT_DOCS_INDEX_SEVERITY = "error"
SEVERITIES = ("error", "warning")
DOCS_INDEX = "docs/INDEX.md"
INDEX_EXEMPT_NAMES = ("README.md", "_template.md")
ISSUE_TEMPLATE_DIR = ".github/ISSUE_TEMPLATE"
LABELS_FILE = ".project/labels.yml"
TEMPLATE_MESSAGE = "template repository: template-only paths allowed"

# Inline links [text](target "title") and reference definitions [label]: target.
_INLINE_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^)]*)?\)")
_REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.MULTILINE)
_EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//")


@dataclass(frozen=True)
class Finding:
    """One validation result.

    Attributes:
        rule: Rule ID, for example ``REPO-REQUIRED``.
        file: Repository-relative POSIX path of the affected file.
        message: Human-readable description.
        severity: ``error`` or ``warning``.
        line: 1-based line number, or ``None`` if the finding concerns the whole file.
    """

    rule: str
    file: str
    message: str
    severity: str = "error"
    line: int | None = None

    def __str__(self) -> str:
        location = f"{self.file}:{self.line}" if self.line else self.file
        prefix = "" if self.severity == "error" else "warning: "
        return f"{self.rule} {location}: {prefix}{self.message}"


@dataclass
class Settings:
    """Configuration read from ``.project/``, with defaults for missing values."""

    is_template: bool = False
    template_only_paths: list[str] = field(default_factory=list)
    required_files: list[str] = field(
        default_factory=lambda: list(DEFAULT_REQUIRED_FILES)
    )
    placeholder_tokens: list[str] = field(
        default_factory=lambda: list(DEFAULT_PLACEHOLDER_TOKENS)
    )
    placeholder_allowlist: list[str] = field(default_factory=list)
    docs_index_severity: str = DEFAULT_DOCS_INDEX_SEVERITY


def _load_check_issue_forms() -> ModuleType:
    """Load check_issue_forms.py from this directory; ``python -I`` does not add it to sys.path."""
    path = Path(__file__).with_name("check_issue_forms.py")
    spec = importlib.util.spec_from_file_location("check_issue_forms", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_issue_forms = _load_check_issue_forms()


def tracked_files(repo: Path) -> list[str]:
    """Return the files tracked by Git in ``repo`` as POSIX paths relative to it.

    Args:
        repo: Root directory of the repository.

    Returns:
        Sorted repository-relative paths.

    Raises:
        RuntimeError: If ``git ls-files`` fails, for example outside a Git repository.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"cannot run git: {error}") from error
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git ls-files failed: {message}")
    return sorted(path for path in result.stdout.decode("utf-8").split("\0") if path)


def _read_yaml(repo: Path, relative: str, findings: list[Finding]) -> dict[str, Any]:
    """Parse a YAML mapping; record a ``REPO-CONFIG`` finding and return ``{}`` on failure."""
    path = repo / relative
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        findings.append(Finding("REPO-CONFIG", relative, f"cannot read: {error}"))
        return {}
    if not isinstance(data, dict):
        findings.append(Finding("REPO-CONFIG", relative, "top level is not a mapping"))
        return {}
    return data


def _string_list(value: Any, default: list[str]) -> list[str]:
    """Return ``value`` if it is a list of strings, otherwise ``default``."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return default


def load_settings(repo: Path, findings: list[Finding]) -> Settings:
    """Read the validator settings from ``.project/``.

    Missing files or fields fall back to the defaults. A missing ``project.yml`` is reported
    by ``REPO-REQUIRED``; the repository is then treated as derived, which is the stricter mode.

    Args:
        repo: Root directory of the repository.
        findings: List that receives ``REPO-CONFIG`` findings.

    Returns:
        The effective settings.
    """
    settings = Settings()
    project = _read_yaml(repo, ".project/project.yml", findings).get("project")
    if isinstance(project, dict) and project.get("is_template") is True:
        settings.is_template = True

    bootstrap = _read_yaml(repo, ".project/bootstrap.yml", findings).get("bootstrap")
    if isinstance(bootstrap, dict):
        settings.template_only_paths = _string_list(
            bootstrap.get("template_only_paths"), []
        )

    section = _read_yaml(repo, ".project/workflow.yml", findings).get(
        "repository_validation"
    )
    if isinstance(section, dict):
        settings.required_files = _string_list(
            section.get("required_files"), settings.required_files
        )
        settings.placeholder_tokens = _string_list(
            section.get("placeholder_tokens"), settings.placeholder_tokens
        )
        settings.placeholder_allowlist = _string_list(
            section.get("placeholder_allowlist"), []
        )
        severity = section.get("docs_index_severity", DEFAULT_DOCS_INDEX_SEVERITY)
        if severity in SEVERITIES:
            settings.docs_index_severity = severity
        else:
            findings.append(
                Finding(
                    "REPO-CONFIG",
                    ".project/workflow.yml",
                    f"repository_validation.docs_index_severity must be one of "
                    f"{', '.join(SEVERITIES)}, got {severity!r}",
                )
            )
    return settings


def _is_below(path: str, prefixes: list[str]) -> bool:
    """Return whether ``path`` equals or lies below one of the repository-relative prefixes."""
    for prefix in prefixes:
        stripped = prefix.strip("/")
        if stripped and (path == stripped or path.startswith(stripped + "/")):
            return True
    return False


def _read_text(repo: Path, relative: str) -> str | None:
    """Return the content of a UTF-8 text file, or ``None`` for binary or unreadable files."""
    try:
        data = (repo / relative).read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def check_required_files(repo: Path, settings: Settings) -> list[Finding]:
    """Report each required file that does not exist (``REPO-REQUIRED``)."""
    return [
        Finding("REPO-REQUIRED", relative, "required file is missing")
        for relative in settings.required_files
        if not (repo / relative).is_file()
    ]


def check_template_only(files: list[str], settings: Settings) -> list[Finding]:
    """Report template-only paths that are tracked in a derived repository (``REPO-TEMPLATE-ONLY``)."""
    if settings.is_template:
        return []
    findings = []
    for prefix in settings.template_only_paths:
        if any(_is_below(path, [prefix]) for path in files):
            findings.append(
                Finding(
                    "REPO-TEMPLATE-ONLY",
                    prefix,
                    "template-only path exists in a derived repository; remove it",
                )
            )
    return findings


def _token_pattern(tokens: list[str]) -> re.Pattern[str] | None:
    """Build one regex for all tokens; a token must not continue a longer identifier."""
    if not tokens:
        return None
    ordered = sorted(tokens, key=len, reverse=True)
    alternatives = "|".join(re.escape(token) for token in ordered)
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternatives})")


def _project_texts(
    repo: Path, files: list[str], settings: Settings
) -> list[tuple[str, str]]:
    """Return path and text of the tracked text files a derived repository must clean up.

    Files in ``template_only_paths`` and files matching ``placeholder_allowlist`` are left out.
    """
    texts = []
    for relative in files:
        if _is_below(relative, settings.template_only_paths):
            continue
        if any(
            fnmatch.fnmatchcase(relative, glob)
            for glob in settings.placeholder_allowlist
        ):
            continue
        text = _read_text(repo, relative)
        if text is not None:
            texts.append((relative, text))
    return texts


def check_placeholders(
    repo: Path, files: list[str], settings: Settings
) -> list[Finding]:
    """Report placeholder tokens left in a derived repository (``REPO-PLACEHOLDER``).

    Reports at most one finding per line, naming the longest matching token.
    """
    if settings.is_template:
        return []
    pattern = _token_pattern(settings.placeholder_tokens)
    if pattern is None:
        return []
    findings = []
    for relative, text in _project_texts(repo, files, settings):
        for number, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                findings.append(
                    Finding(
                        "REPO-PLACEHOLDER",
                        relative,
                        f"placeholder {match.group(0)!r} was not replaced",
                        line=number,
                    )
                )
    return findings


def check_template_markers(
    repo: Path, files: list[str], settings: Settings
) -> list[Finding]:
    """Report template-only markers left in a derived repository (``REPO-TEMPLATE-MARKER``)."""
    if settings.is_template:
        return []
    findings = []
    for relative, text in _project_texts(repo, files, settings):
        for number, line in enumerate(text.splitlines(), start=1):
            match = TEMPLATE_MARKER.search(line)
            if match:
                findings.append(
                    Finding(
                        "REPO-TEMPLATE-MARKER",
                        relative,
                        f"marker {match.group(0)!r} is left; remove the template-only block",
                        line=number,
                    )
                )
    return findings


def markdown_links(text: str) -> list[tuple[int, str]]:
    """Return the link targets in Markdown text with their 1-based line numbers.

    Fenced code blocks are skipped. Anchors and query strings are removed from the targets.
    """
    links: list[tuple[int, str]] = []
    in_fence = False
    fence = ""
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        targets = _INLINE_LINK.findall(line) + _REFERENCE_LINK.findall(line)
        for target in targets:
            cleaned = target.split("#", 1)[0].split("?", 1)[0]
            if cleaned:
                links.append((number, cleaned))
    return links


def resolve_link(source: str, target: str) -> str | None:
    """Resolve a link target relative to its source file.

    Args:
        source: Repository-relative POSIX path of the file that contains the link.
        target: Link target without anchor.

    Returns:
        The normalized repository-relative target, or ``None`` for external links and links
        that leave the repository.
    """
    if _EXTERNAL.match(target):
        return None
    if target.startswith("/"):
        resolved = posixpath.normpath(target.lstrip("/"))
    else:
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), target))
    if resolved == ".." or resolved.startswith("../"):
        return None
    return resolved


def check_template_links(
    repo: Path, files: list[str], settings: Settings
) -> list[Finding]:
    """Report links from regular files to template-only paths (``REPO-DEAD-LINK-TEMPLATE``)."""
    if not settings.template_only_paths:
        return []
    findings = []
    for relative in files:
        if not relative.endswith(".md") or _is_below(
            relative, settings.template_only_paths
        ):
            continue
        text = _read_text(repo, relative)
        if text is None:
            continue
        for number, target in markdown_links(text):
            resolved = resolve_link(relative, target)
            if resolved and _is_below(resolved, settings.template_only_paths):
                findings.append(
                    Finding(
                        "REPO-DEAD-LINK-TEMPLATE",
                        relative,
                        f"links to template-only path {target!r}, which derived repositories "
                        "do not contain",
                        line=number,
                    )
                )
    return findings


def check_docs_index(repo: Path, files: list[str], settings: Settings) -> list[Finding]:
    """Check that ``docs/INDEX.md`` lists every document and has no broken links (``REPO-DOCS-INDEX``)."""
    severity = settings.docs_index_severity
    documents = [
        path
        for path in files
        if path.startswith("docs/")
        and path.endswith(".md")
        and path != DOCS_INDEX
        and posixpath.basename(path) not in INDEX_EXEMPT_NAMES
    ]
    text = _read_text(repo, DOCS_INDEX) if (repo / DOCS_INDEX).is_file() else None
    if text is None:
        if not documents:
            return []
        return [Finding("REPO-DOCS-INDEX", DOCS_INDEX, "index is missing", severity)]

    findings = []
    linked: set[str] = set()
    for number, target in markdown_links(text):
        resolved = resolve_link(DOCS_INDEX, target)
        if resolved is None:
            continue
        linked.add(resolved)
        if not (repo / resolved).exists():
            findings.append(
                Finding(
                    "REPO-DOCS-INDEX",
                    DOCS_INDEX,
                    f"link target {target!r} does not exist",
                    severity,
                    number,
                )
            )
    for document in documents:
        if document not in linked:
            findings.append(
                Finding(
                    "REPO-DOCS-INDEX",
                    document,
                    f"not linked from {DOCS_INDEX}",
                    severity,
                )
            )
    return findings


def check_forms(repo: Path) -> list[Finding]:
    """Run the issue form consistency check, if issue forms exist (``REPO-ISSUE-FORMS``)."""
    template_dir = repo / ISSUE_TEMPLATE_DIR
    if not template_dir.is_dir():
        return []
    problems = check_issue_forms.check_directory(template_dir, repo / LABELS_FILE)
    findings = []
    for problem in problems:
        location, _, message = problem.partition(": ")
        try:
            relative = Path(location).resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            relative = location
        findings.append(Finding("REPO-ISSUE-FORMS", relative, message or problem))
    return findings


def validate_repository(repo: Path) -> tuple[Settings, list[Finding]]:
    """Run all repository checks.

    Args:
        repo: Root directory of the repository.

    Returns:
        The effective settings and all findings, sorted by rule, file and line.
    """
    findings: list[Finding] = []
    settings = load_settings(repo, findings)
    try:
        files = tracked_files(repo)
    except RuntimeError as error:
        findings.append(Finding("REPO-CONFIG", ".", str(error)))
        return settings, findings

    findings.extend(check_required_files(repo, settings))
    findings.extend(check_template_only(files, settings))
    findings.extend(check_placeholders(repo, files, settings))
    findings.extend(check_template_markers(repo, files, settings))
    findings.extend(check_template_links(repo, files, settings))
    findings.extend(check_docs_index(repo, files, settings))
    findings.extend(check_forms(repo))
    findings.sort(key=lambda item: (item.rule, item.file, item.line or 0, item.message))
    return settings, findings


def main(argv: list[str] | None = None) -> int:
    """Validate a repository and print the findings.

    Args:
        argv: Command line arguments without the program name; ``None`` uses ``sys.argv``.

    Returns:
        Process exit code: 0 if there is no error, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Validate repository structure and hygiene."
    )
    parser.add_argument(
        "repository", nargs="?", default=".", help="repository root (default: .)"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    repo = Path(args.repository)
    settings, findings = validate_repository(repo)
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]

    if args.format == "json":
        document = {
            "repository": str(repo),
            "template_repository": settings.is_template,
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": [asdict(item) for item in findings],
        }
        print(json.dumps(document, indent=2))
    else:
        if settings.is_template:
            print(TEMPLATE_MESSAGE)
        for item in findings:
            print(item, file=sys.stderr)
        print(f"{repo}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
