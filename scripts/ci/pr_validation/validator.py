"""Validate pull request metadata and commit messages against .project/workflow.yml.

Two commands, one per CI job of ``.github/workflows/pr-validation.yml``:

``pull-request``
    Checks the title (Conventional Commits), the issue link, the target branch, the branch name
    and the required sections of the pull request template. Changes below
    ``elevated_review_paths`` add a notice; they do not fail the check.
``commits``
    Checks every non-merge commit of the pull request with the Conventional Commits parser.

In CI both commands read the pull request from the event file (``--event``). Pull request text
is data: it is never passed to a shell, and only repository-controlled commit IDs are passed to
``git`` as arguments. Local runs pass the values directly; see scripts/ci/README.md.

Exit codes: 0 no problem, 1 at least one rule failed, 2 invalid input.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import yaml

TEMPLATE_PATH = ".github/PULL_REQUEST_TEMPLATE.md"
# Defaults for workflow.yml schema 1.0, which has no such fields.
DEFAULT_REQUIRED_SECTIONS = (
    "Summary",
    "Related Issues",
    "Validation",
    "Tests Executed",
)
DEFAULT_AUTOMATION_AUTHORS: tuple[str, ...] = ()

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_PATTERN = re.compile(r"^[ \t]*(```|~~~)")
ISSUE_REFERENCE = (
    r"(?:(?:[\w.-]+/[\w.-]+)?#\d+|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)"
)
ISSUE_LINK_PATTERN = re.compile(
    rf"(?:\brefs:|\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?)[ \t]+{ISSUE_REFERENCE}",
    re.IGNORECASE,
)
NO_ISSUE_PATTERN = re.compile(
    r"^[ \t]*No-Issue:[ \t]*(?P<reason>.*?)[ \t]*$", re.MULTILINE
)
COMMIT_ID_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
KEBAB_SUMMARY = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def _load_sibling(name: str) -> ModuleType:
    """Load a module from this directory; ``python -I`` does not add it to sys.path."""
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"pr_validation_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


commits = _load_sibling("commits")


@dataclass(frozen=True)
class Finding:
    """A failed rule.

    Attributes:
        rule: Short rule name, for example ``title``.
        message: What is wrong.
        hint: How to fix it.
    """

    rule: str
    message: str
    hint: str


@dataclass(frozen=True)
class PullRequest:
    """The pull request fields the rules need.

    Attributes:
        title: Pull request title.
        body: Pull request description.
        head_ref: Source branch name.
        base_ref: Target branch name.
        author: Login of the author, for example ``dependabot[bot]``.
    """

    title: str
    body: str
    head_ref: str
    base_ref: str
    author: str


@dataclass(frozen=True)
class Commit:
    """A commit of the pull request.

    Attributes:
        sha: Full commit ID.
        parents: Parent commit IDs; a merge commit has more than one.
        message: Raw commit message.
    """

    sha: str
    parents: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class Rules:
    """The rules read from .project/workflow.yml and .project/project.yml.

    Attributes:
        allowed_types: Permitted Conventional Commit types.
        branch_name_pattern: Regular expression for work branch names.
        branch_types: Branch type to permitted target branches.
        default_branch: Default branch, for example ``main``.
        development_branch: Integration branch, for example ``develop``.
        issue_link_required: Whether a pull request must link an issue.
        exception_requires_reason: Whether ``No-Issue:`` needs a reason.
        required_sections: Template headings that must be filled in.
        automation_authors: Bot logins that skip branch name, issue link and section checks.
        elevated_review_paths: Path prefixes that need elevated review.
    """

    allowed_types: tuple[str, ...]
    branch_name_pattern: str
    branch_types: dict[str, tuple[str, ...]]
    default_branch: str
    development_branch: str
    issue_link_required: bool
    exception_requires_reason: bool
    required_sections: tuple[str, ...]
    automation_authors: tuple[str, ...]
    elevated_review_paths: tuple[str, ...]


def load_rules(repo: Path) -> Rules:
    """Read the rules from the ``.project`` directory of ``repo``.

    The files are expected to be valid; ``validate_project.py`` checks them in CI.

    Args:
        repo: Repository root.

    Returns:
        The rules.

    Raises:
        OSError: If a file cannot be read.
        KeyError: If a required field is missing.
        yaml.YAMLError: If a file is not valid YAML.
    """
    workflow = yaml.safe_load(
        (repo / ".project/workflow.yml").read_text(encoding="utf-8")
    )
    project = yaml.safe_load(
        (repo / ".project/project.yml").read_text(encoding="utf-8")
    )
    pull_requests = workflow["pull_requests"]
    branching = workflow["branching"]
    return Rules(
        allowed_types=tuple(pull_requests["allowed_types"]),
        branch_name_pattern=branching["branch_name_pattern"],
        branch_types={
            name: tuple(spec["targets"])
            for name, spec in branching["branch_types"].items()
        },
        default_branch=project["repository"]["default_branch"],
        development_branch=project["repository"]["development_branch"],
        issue_link_required=pull_requests["issue_link"]["required"],
        exception_requires_reason=pull_requests["issue_link"][
            "exception_requires_reason"
        ],
        required_sections=tuple(
            pull_requests.get("required_sections", DEFAULT_REQUIRED_SECTIONS)
        ),
        automation_authors=tuple(
            pull_requests.get("automation_authors", DEFAULT_AUTOMATION_AUTHORS)
        ),
        elevated_review_paths=tuple(pull_requests["elevated_review_paths"]),
    )


# Pull request rules


def check_title(title: str, rules: Rules) -> list[Finding]:
    """Check that the title is a Conventional Commits header with an allowed type."""
    _, problems = commits.parse_header(title, rules.allowed_types)
    return [
        Finding(
            "title",
            problem,
            "edit the pull request title; it becomes the squash commit",
        )
        for problem in problems
    ]


def no_issue_reason(body: str) -> str | None:
    """Return the reason of a ``No-Issue:`` line outside HTML comments, or ``None``."""
    match = NO_ISSUE_PATTERN.search(COMMENT_PATTERN.sub("", body))
    return None if match is None else match["reason"]


def has_issue_link(body: str) -> bool:
    """Return whether the body links an issue outside HTML comments."""
    return ISSUE_LINK_PATTERN.search(COMMENT_PATTERN.sub("", body)) is not None


def _has_valid_exception(body: str, rules: Rules) -> bool:
    reason = no_issue_reason(body)
    if reason is None:
        return False
    if not rules.exception_requires_reason:
        return True
    return bool(reason) and not re.fullmatch(r"<[^>]*>", reason)


def check_issue_link(pr: PullRequest, rules: Rules) -> list[Finding]:
    """Check that the pull request links an issue or states why there is none."""
    if not rules.issue_link_required or has_issue_link(pr.body):
        return []
    if no_issue_reason(pr.body) is not None:
        if _has_valid_exception(pr.body, rules):
            return []
        return [
            Finding(
                "issue-link",
                "the No-Issue line has no reason",
                "write the reason after 'No-Issue:', for example 'No-Issue: typo fix'",
            )
        ]
    return [
        Finding(
            "issue-link",
            "the description does not link an issue",
            "add 'Refs: #<number>' (or 'Closes #<number>') under Related Issues, "
            "or 'No-Issue: <reason>' for an exception",
        )
    ]


def _branch_type(branch: str) -> str | None:
    prefix, separator, _ = branch.partition("/")
    return prefix if separator else None


def check_target(pr: PullRequest, rules: Rules) -> list[Finding]:
    """Check the target branch against the branch model.

    Release pull requests from the development branch into the default branch and
    synchronization pull requests in the opposite direction are always allowed. Pull requests of
    automation authors may target either branch, because Dependabot security updates target the
    default branch.
    """
    default, development = rules.default_branch, rules.development_branch
    if (pr.head_ref, pr.base_ref) in ((development, default), (default, development)):
        return []
    if pr.author in rules.automation_authors and pr.base_ref in (default, development):
        return []
    branch_type = _branch_type(pr.head_ref)
    targets = rules.branch_types.get(branch_type or "")
    if targets is None:
        known = ", ".join(f"{name}/" for name in rules.branch_types)
        return [
            Finding(
                "target-branch",
                f"branch {pr.head_ref!r} has no known branch type",
                f"use one of: {known}; or open the pull request from {development!r}",
            )
        ]
    if pr.base_ref in targets:
        return []
    return [
        Finding(
            "target-branch",
            f"{branch_type}/ branches must target {', '.join(map(repr, targets))}, "
            f"not {pr.base_ref!r}",
            "change the base branch of the pull request",
        )
    ]


def check_branch_name(pr: PullRequest, rules: Rules) -> list[Finding]:
    """Check the source branch name.

    A work branch without an issue number is accepted when the description states a
    ``No-Issue:`` exception (see docs/governance/branching-and-releases.md).
    """
    if pr.head_ref in (rules.default_branch, rules.development_branch):
        return []
    if pr.author in rules.automation_authors:
        return []
    if re.fullmatch(rules.branch_name_pattern, pr.head_ref):
        return []
    types = "|".join(map(re.escape, rules.branch_types))
    if re.fullmatch(
        rf"(?:{types})/{KEBAB_SUMMARY}", pr.head_ref
    ) and _has_valid_exception(pr.body, rules):
        return []
    return [
        Finding(
            "branch-name",
            f"branch {pr.head_ref!r} does not match {rules.branch_name_pattern!r}",
            "rename the branch to <type>/<issue-number>-<short-summary>, "
            "for example feature/42-document-cropping",
        )
    ]


def parse_sections(markdown: str) -> dict[str, str]:
    """Split Markdown into the text directly below each heading.

    A section ends at the next heading of any level, so a subsection is not part of its parent.
    Headings inside code fences are ignored. HTML comments are removed first.

    Args:
        markdown: Markdown text.

    Returns:
        Heading text to section text; the first occurrence of a heading wins.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    fence: str | None = None
    for line in COMMENT_PATTERN.sub("", markdown).replace("\r\n", "\n").split("\n"):
        fence_match = FENCE_PATTERN.match(line)
        if fence_match is not None:
            marker = fence_match[1]
            fence = None if fence == marker else (fence or marker)
        elif fence is None:
            heading = HEADING_PATTERN.match(line)
            if heading is not None:
                title = heading[2].strip()
                current = None if title in sections else sections.setdefault(title, [])
                continue
        if current is not None:
            current.append(line)
    return {title: "\n".join(lines) for title, lines in sections.items()}


def _normalize(section: str) -> str:
    """Remove fence markers, blank lines and surrounding whitespace for comparisons."""
    lines = (line.strip() for line in section.split("\n"))
    return "\n".join(line for line in lines if line and not FENCE_PATTERN.match(line))


def check_sections(pr: PullRequest, rules: Rules, template: str) -> list[Finding]:
    """Check that each required section exists and differs from the template text."""
    if pr.author in rules.automation_authors:
        return []
    found = parse_sections(pr.body)
    expected = parse_sections(template)
    findings = []
    for name in rules.required_sections:
        if name not in found:
            findings.append(
                Finding(
                    "template-section",
                    f"section {name!r} is missing",
                    "keep the headings of the pull request template unchanged",
                )
            )
            continue
        content = _normalize(found[name])
        if not content:
            message = f"section {name!r} is empty"
        elif name in expected and content == _normalize(expected[name]):
            message = f"section {name!r} still contains only the template text"
        else:
            continue
        findings.append(
            Finding("template-section", message, f"fill in the {name!r} section")
        )
    return findings


def elevated_paths(changed_files: Iterable[str], rules: Rules) -> list[str]:
    """Return the configured elevated review paths that the changed files touch."""
    files = list(changed_files)
    return [
        prefix
        for prefix in rules.elevated_review_paths
        if any(
            f == prefix
            or f.startswith(prefix if prefix.endswith("/") else f"{prefix}/")
            for f in files
        )
    ]


def check_pull_request(pr: PullRequest, rules: Rules, template: str) -> list[Finding]:
    """Apply every pull request rule.

    Args:
        pr: The pull request.
        rules: The configured rules.
        template: Text of the pull request template.

    Returns:
        All findings, in rule order.
    """
    findings = check_title(pr.title, rules)
    findings += check_target(pr, rules)
    findings += check_branch_name(pr, rules)
    if pr.author not in rules.automation_authors:
        findings += check_issue_link(pr, rules)
    findings += check_sections(pr, rules, template)
    return findings


def check_commits(items: Iterable[Commit], rules: Rules) -> list[Finding]:
    """Check every non-merge commit message.

    Merge commits are skipped: their messages are generated by Git or GitHub, and with a squash
    merge only the pull request title reaches the target branch.
    """
    findings = []
    for commit in items:
        if len(commit.parents) > 1:
            continue
        _, problems = commits.parse_message(commit.message, rules.allowed_types)
        findings += [
            Finding(
                "commit-message",
                f"commit {commit.sha[:12]}: {problem}",
                "reword the commit (git rebase) or squash it; see "
                "docs/governance/commit-conventions.md",
            )
            for problem in problems
        ]
    return findings


# Git and event input


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {arguments[0]} failed: {result.stderr.strip()}")
    return result.stdout


def _checked_range(revision_range: str) -> str:
    if revision_range.startswith("-") or ".." not in revision_range:
        raise ValueError(f"invalid revision range {revision_range!r}; use BASE..HEAD")
    return revision_range


def read_commits(repo: Path, revision_range: str) -> list[Commit]:
    """Read the commits of ``BASE..HEAD``, oldest first."""
    output = _git(
        repo,
        "log",
        "--reverse",
        "--format=%H%x1f%P%x1f%B%x1e",
        _checked_range(revision_range),
    )
    result = []
    for record in output.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, parents, message = record.split("\x1f", 2)
        result.append(Commit(sha, tuple(parents.split()), message))
    return result


def read_changed_files(repo: Path, revision_range: str) -> list[str]:
    """Read the files changed between the merge base and HEAD of ``BASE..HEAD``."""
    base, _, head = _checked_range(revision_range).partition("..")
    output = _git(repo, "diff", "--name-only", "-z", f"{base}...{head.lstrip('.')}")
    return [name for name in output.split("\0") if name]


def read_event(path: Path) -> tuple[PullRequest, str]:
    """Read a ``pull_request`` event file.

    Args:
        path: Path of the event JSON, ``GITHUB_EVENT_PATH`` in Actions.

    Returns:
        The pull request and its ``BASE..HEAD`` commit range.

    Raises:
        ValueError: If the event has no pull request or invalid commit IDs.
    """
    event = json.loads(path.read_text(encoding="utf-8"))
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise ValueError("the event file contains no pull_request")  # noqa: TRY004 - input error
    base_sha, head_sha = pr["base"]["sha"], pr["head"]["sha"]
    for sha in (base_sha, head_sha):
        if not isinstance(sha, str) or not COMMIT_ID_PATTERN.match(sha):
            raise ValueError(f"invalid commit ID in the event file: {sha!r}")
    pull_request = PullRequest(
        title=pr.get("title") or "",
        body=pr.get("body") or "",
        head_ref=pr["head"]["ref"],
        base_ref=pr["base"]["ref"],
        author=(pr.get("user") or {}).get("login", ""),
    )
    return pull_request, f"{base_sha}..{head_sha}"


# Output


def report(findings: Sequence[Finding], notices: Sequence[str], heading: str) -> int:
    """Print the findings and notices and append them to the GitHub job summary.

    Untrusted values in messages are quoted with ``repr``, so they cannot start a line or inject
    workflow commands.

    Returns:
        The exit code: 1 if there is a finding, otherwise 0.
    """
    for notice in notices:
        print(f"::notice title=Elevated review required::{notice}")
    for finding in findings:
        print(f"error: [{finding.rule}] {finding.message}\n  fix: {finding.hint}")
    print(f"{heading}: {len(findings)} problem(s)")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [f"## {heading}", ""]
        lines += [f"> **Elevated review required:** {notice}" for notice in notices]
        if findings:
            lines += ["| Rule | Problem | Fix |", "|---|---|---|"]
            lines += [
                "| {} | {} | {} |".format(
                    *(text.replace("|", "\\|") for text in (f.rule, f.message, f.hint))
                )
                for f in findings
            ]
        else:
            lines.append("All rules passed.")
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    return 1 if findings else 0


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)

    pull_request = commands.add_parser(
        "pull-request", help="check pull request metadata"
    )
    pull_request.add_argument("--event", type=Path, help="pull_request event JSON file")
    pull_request.add_argument("--title")
    pull_request.add_argument(
        "--body-file", type=Path, help="file with the description"
    )
    pull_request.add_argument("--head-ref", help="source branch")
    pull_request.add_argument("--base-ref", help="target branch")
    pull_request.add_argument("--author", default="", help="author login")
    pull_request.add_argument("--range", help="BASE..HEAD, to find changed files")

    commit_check = commands.add_parser(
        "commits", help="check the commits of a pull request"
    )
    commit_check.add_argument("--event", type=Path, help="pull_request event JSON file")
    commit_check.add_argument("--range", help="BASE..HEAD, for example develop..HEAD")
    return parser.parse_args(argv)


def _pull_request_from_arguments(
    args: argparse.Namespace,
) -> tuple[PullRequest, str | None]:
    if args.event is not None:
        return read_event(args.event)
    missing = [
        name
        for name in ("title", "body_file", "head_ref", "base_ref")
        if getattr(args, name) is None
    ]
    if missing:
        options = ", ".join("--" + name.replace("_", "-") for name in missing)
        raise ValueError(f"use --event, or pass {options}")
    body = args.body_file.read_text(encoding="utf-8")
    return PullRequest(
        args.title, body, args.head_ref, args.base_ref, args.author
    ), args.range


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    args = _parse_arguments(argv)
    repo = args.repo
    try:
        rules = load_rules(repo)
        if args.command == "pull-request":
            pr, revision_range = _pull_request_from_arguments(args)
            template_file = repo / TEMPLATE_PATH
            template = (
                template_file.read_text(encoding="utf-8")
                if template_file.is_file()
                else ""
            )
            findings = check_pull_request(pr, rules, template)
            changed = read_changed_files(repo, revision_range) if revision_range else []
            notices = [
                f"this pull request changes {path}"
                for path in elevated_paths(changed, rules)
            ]
            return report(findings, notices, "Pull request validation")
        if args.event is not None:
            _, revision_range = read_event(args.event)
        elif args.range is not None:
            revision_range = args.range
        else:
            raise ValueError("use --event or --range")
        return report(
            check_commits(read_commits(repo, revision_range), rules), [], "Commit check"
        )
    except (OSError, KeyError, ValueError, RuntimeError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
