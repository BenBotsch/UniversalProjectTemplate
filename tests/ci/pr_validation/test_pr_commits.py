"""Tests for scripts/ci/pr_validation/commits.py (Conventional Commits 1.0.0 parser)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "pr_commits", ROOT / "scripts" / "ci" / "pr_validation" / "commits.py"
)
commits = importlib.util.module_from_spec(_spec)
sys.modules["pr_commits"] = commits
_spec.loader.exec_module(commits)

TYPES = ("feat", "fix", "refactor", "perf", "docs", "test", "build", "ci", "chore")


@pytest.mark.parametrize(
    ("header", "commit_type", "scope", "breaking"),
    [
        ("feat: add cropping", "feat", None, False),
        ("fix(api): handle empty body", "fix", "api", False),
        ("feat(api)!: drop v1 endpoints", "feat", "api", True),
        ("chore!: require Python 3.12", "chore", None, True),
        ("ci(deps): bump actions/checkout from 7.0.1 to 7.1.0", "ci", "deps", False),
    ],
)
def test_valid_headers_are_parsed(
    header: str, commit_type: str, scope: str | None, breaking: bool
) -> None:
    commit, problems = commits.parse_header(header, TYPES)
    assert problems == []
    assert (commit.type, commit.scope, commit.breaking) == (
        commit_type,
        scope,
        breaking,
    )


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("", "the header is empty"),
        ("add cropping", "is not a Conventional Commits header"),
        ("feat:add cropping", "is not a Conventional Commits header"),
        ("feat: ", "is not a Conventional Commits header"),
        ("feat (api): add", "is not a Conventional Commits header"),
        ("Feat: add cropping", "type 'Feat' is not allowed"),
        ("feature: add cropping", "type 'feature' is not allowed"),
        ("feat(): add cropping", "the scope in parentheses is empty"),
        ("feat: add cropping ", "ends with whitespace"),
    ],
)
def test_invalid_headers_are_reported(header: str, expected: str) -> None:
    _, problems = commits.parse_header(header, TYPES)
    assert len(problems) == 1
    assert expected in problems[0]


def test_allowed_types_come_from_the_caller() -> None:
    _, problems = commits.parse_header("feat: add", ("fix",))
    assert problems == ["type 'feat' is not allowed; use one of: fix"]


def test_message_with_body_and_footers_is_parsed() -> None:
    message = (
        "feat(parser): support footers\n"
        "\n"
        "First paragraph.\n"
        "\n"
        "Second paragraph.\n"
        "\n"
        "Refs: #42\n"
        "Reviewed-by: Alice\n"
        "  continued value\n"
    )
    commit, problems = commits.parse_message(message, TYPES)
    assert problems == []
    assert commit.body == "First paragraph.\n\nSecond paragraph."
    assert commit.footers == (
        ("Refs", "#42"),
        ("Reviewed-by", "Alice\n  continued value"),
    )
    assert commit.breaking is False


@pytest.mark.parametrize("token", ["BREAKING CHANGE", "BREAKING-CHANGE"])
def test_breaking_change_footer_marks_the_commit(token: str) -> None:
    commit, problems = commits.parse_message(
        f"refactor: rename config keys\n\n{token}: `a` is now `b`\n", TYPES
    )
    assert problems == []
    assert commit.breaking is True


def test_footer_with_hash_separator_is_parsed() -> None:
    commit, problems = commits.parse_message(
        "fix: correct offset\n\nFixes #12\n", TYPES
    )
    assert problems == []
    assert commit.footers == (("Fixes", "12"),)


def test_lowercase_breaking_change_footer_is_reported() -> None:
    _, problems = commits.parse_message("fix: x\n\nbreaking change: y\n", TYPES)
    assert problems == [
        "footer token 'breaking change' must be written in uppercase: BREAKING CHANGE"
    ]


def test_missing_blank_line_after_header_is_reported() -> None:
    _, problems = commits.parse_message("fix: x\nbody directly below\n", TYPES)
    assert problems == ["the header must be followed by a blank line before the body"]


def test_crlf_message_is_accepted() -> None:
    commit, problems = commits.parse_message("docs: update\r\n\r\nRefs: #1\r\n", TYPES)
    assert problems == []
    assert commit.footers == (("Refs", "#1"),)


def test_invalid_header_in_message_returns_no_commit() -> None:
    commit, problems = commits.parse_message("WIP\n\nmore\n", TYPES)
    assert commit is None
    assert "is not a Conventional Commits header" in problems[0]
