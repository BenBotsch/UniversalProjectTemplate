"""Parse commit messages and pull request titles as Conventional Commits 1.0.0.

A message has a header ``type(scope)!: description``, an optional body and optional footers,
each separated by a blank line. A breaking change is marked with ``!`` in the header or with a
``BREAKING CHANGE:`` (or ``BREAKING-CHANGE:``) footer. See
https://www.conventionalcommits.org/en/v1.0.0/.

The parser only reads text; it never executes or evaluates message content.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

HEADER_PATTERN = re.compile(
    r"^(?P<type>[A-Za-z]+)"
    r"(?:\((?P<scope>[^()\r\n]*)\))?"
    r"(?P<breaking>!)?"
    r": (?P<description>\S.*)$"
)
FOOTER_PATTERN = re.compile(
    r"^(?P<token>BREAKING CHANGE|[A-Za-z][A-Za-z0-9-]*)(?::[ \t]|[ \t]#)(?P<value>.*)$",
    re.IGNORECASE,
)
BREAKING_TOKENS = ("BREAKING CHANGE", "BREAKING-CHANGE")
HEADER_HINT = (
    "use 'type(scope): description', for example 'feat(api): add image endpoint'"
)


@dataclass(frozen=True)
class ConventionalCommit:
    """A parsed Conventional Commit message.

    Attributes:
        type: Commit type, for example ``feat``.
        scope: Scope inside the parentheses, or ``None``.
        description: Text after ``": "`` in the header.
        breaking: Whether ``!`` or a breaking-change footer marks the commit.
        body: Text between header and footers, without surrounding blank lines.
        footers: ``(token, value)`` pairs in message order.
    """

    type: str
    scope: str | None
    description: str
    breaking: bool
    body: str = ""
    footers: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def parse_header(
    header: str, allowed_types: Iterable[str]
) -> tuple[ConventionalCommit | None, list[str]]:
    """Parse a single header line, such as a commit subject or a pull request title.

    Args:
        header: The header line.
        allowed_types: Permitted lowercase commit types.

    Returns:
        The parsed header (without body and footers) and a list of problems. The commit is
        ``None`` if the header does not have the Conventional Commits form.
    """
    allowed = list(allowed_types)
    if not header.strip():
        return None, [f"the header is empty; {HEADER_HINT}"]
    match = HEADER_PATTERN.match(header)
    if match is None:
        return None, [f"{header!r} is not a Conventional Commits header; {HEADER_HINT}"]
    problems = []
    commit_type = match["type"]
    if commit_type not in allowed:
        problems.append(
            f"type {commit_type!r} is not allowed; use one of: {', '.join(allowed)}"
        )
    scope = match["scope"]
    if scope is not None and not scope.strip():
        problems.append(
            "the scope in parentheses is empty; remove the parentheses or name a scope"
        )
    if header != header.rstrip():
        problems.append("the header ends with whitespace; remove it")
    commit = ConventionalCommit(
        type=commit_type,
        scope=scope,
        description=match["description"].rstrip(),
        breaking=match["breaking"] is not None,
    )
    return commit, problems


def _split_footers(paragraphs: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Separate a trailing footer paragraph from the body paragraphs."""
    if not paragraphs:
        return paragraphs, []
    lines = paragraphs[-1].split("\n")
    if FOOTER_PATTERN.match(lines[0]) is None:
        return paragraphs, []
    footers: list[tuple[str, str]] = []
    for line in lines:
        match = FOOTER_PATTERN.match(line)
        if match is not None:
            footers.append((match["token"], match["value"]))
        else:
            # A footer value may continue on the following lines.
            token, value = footers[-1]
            footers[-1] = (token, f"{value}\n{line}")
    return paragraphs[:-1], footers


def parse_message(
    message: str, allowed_types: Iterable[str]
) -> tuple[ConventionalCommit | None, list[str]]:
    """Parse a full commit message.

    Args:
        message: The raw commit message, for example from ``git log --format=%B``.
        allowed_types: Permitted lowercase commit types.

    Returns:
        The parsed commit and a list of problems. The commit is ``None`` if the header does not
        have the Conventional Commits form.
    """
    text = message.replace("\r\n", "\n").strip("\n")
    header, _, rest = text.partition("\n")
    commit, problems = parse_header(header, allowed_types)
    if rest and rest.split("\n", 1)[0].strip():
        problems.append("the header must be followed by a blank line before the body")
    paragraphs = [p.strip("\n") for p in re.split(r"\n[ \t]*\n", rest) if p.strip()]
    body_paragraphs, footers = _split_footers(paragraphs)
    for token, _ in footers:
        if token.upper() in BREAKING_TOKENS and token not in BREAKING_TOKENS:
            problems.append(
                f"footer token {token!r} must be written in uppercase: BREAKING CHANGE"
            )
    if commit is None:
        return None, problems
    breaking = commit.breaking or any(
        token.upper() in BREAKING_TOKENS for token, _ in footers
    )
    return (
        ConventionalCommit(
            type=commit.type,
            scope=commit.scope,
            description=commit.description,
            breaking=breaking,
            body="\n\n".join(body_paragraphs),
            footers=tuple(footers),
        ),
        problems,
    )
