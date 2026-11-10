"""Check that GitHub Actions references are pinned to full commit SHAs.

Scans the YAML files in .github/workflows/ and .github/actions/ for ``uses:``
references. A reference passes if it is a local action (``./...``), a Docker
image pinned by digest (``docker://...@sha256:...``) or a repository reference
pinned to a 40-character commit SHA followed by a version comment, for example
``uses: actions/checkout@<sha> # v7.0.1``. Tags and branches are mutable and fail.

The check works on lines instead of parsed YAML so that it can read the version
comment and report line numbers.

Usage: python -I scripts/ci/check_action_pinning.py [repository]
       (default: the current directory)
Exit codes: 0 all references pinned, 1 unpinned references or unreadable files.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCANNED_DIRECTORIES = (".github/workflows", ".github/actions")
YAML_SUFFIXES = {".yml", ".yaml"}

USES_LINE = re.compile(
    r"""^\s*(?:-\s+)?uses:\s*(?P<quote>["']?)(?P<ref>[^\s"'#]+)(?P=quote)\s*(?:\#\s*(?P<comment>.*))?$"""
)
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DOCKER_DIGEST = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class Finding:
    """One unpinned or malformed action reference.

    Attributes:
        file: Path of the file, relative to the repository.
        line: 1-based line number.
        message: Description of the problem.
    """

    file: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.message}"


def check_reference(ref: str, comment: str | None) -> str | None:
    """Check a single ``uses:`` value.

    Args:
        ref: The referenced action or reusable workflow.
        comment: Text of the trailing comment, if any.

    Returns:
        A problem description, or ``None`` if the reference is pinned.
    """
    if ref.startswith("./"):
        return None
    if ref.startswith("docker://"):
        if DOCKER_DIGEST.match(ref):
            return None
        return f"'{ref}' is not pinned to an image digest (@sha256:...)"
    name, separator, version = ref.rpartition("@")
    if not separator or not name:
        return f"'{ref}' has no version; pin it to a full commit SHA"
    if not COMMIT_SHA.match(version):
        return f"'{ref}' is not pinned to a full commit SHA"
    if not comment or not comment.strip():
        return f"'{ref}' has no version comment, for example '# v1.2.3'"
    return None


def check_file(path: Path, display: str) -> list[Finding]:
    """Check all ``uses:`` references in one YAML file.

    Args:
        path: File to read.
        display: Path shown in findings.

    Returns:
        Findings in line order.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [Finding(display, 0, f"cannot read file: {error}")]
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        match = USES_LINE.match(line)
        if match is None:
            if re.match(r"^\s*(?:-\s+)?uses:", line):
                findings.append(
                    Finding(display, number, "cannot parse 'uses:' reference")
                )
            continue
        problem = check_reference(match["ref"], match["comment"])
        if problem:
            findings.append(Finding(display, number, problem))
    return findings


def list_files(repository: Path) -> list[Path]:
    """List the workflow and action files of a repository.

    Args:
        repository: Repository root.

    Returns:
        The files in sorted order.
    """
    return sorted(
        path
        for directory in SCANNED_DIRECTORIES
        if (repository / directory).is_dir()
        for path in (repository / directory).rglob("*")
        if path.is_file() and path.suffix in YAML_SUFFIXES
    )


def check_repository(repository: Path) -> tuple[int, list[Finding]]:
    """Check every workflow and action file of a repository.

    Args:
        repository: Repository root.

    Returns:
        Number of scanned files and all findings.
    """
    files = list_files(repository)
    findings = []
    for path in files:
        findings.extend(check_file(path, path.relative_to(repository).as_posix()))
    return len(files), findings


def main(argv: list[str]) -> int:
    """Check the action references and print the result.

    Args:
        argv: Command line; optional ``argv[1]`` is the repository root.

    Returns:
        Process exit code: 0 if all references are pinned, 1 otherwise.
    """
    repository = Path(argv[1]) if len(argv) > 1 else Path(".")
    count, findings = check_repository(repository)
    for finding in findings:
        print(f"error: {finding}", file=sys.stderr)
    if findings:
        print(f"{len(findings)} unpinned action reference(s)", file=sys.stderr)
        return 1
    print(f"{count} workflow and action file(s): all action references pinned")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
