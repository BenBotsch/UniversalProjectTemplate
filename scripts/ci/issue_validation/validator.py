"""Validate issue metadata against .project/workflow.yml and the issue forms.

The rules are the metadata invariants ``ISSUE-R*`` of docs/governance/issue-management.md:

``ISSUE-R1``/``ISSUE-R2``
    Exactly one label of each group in ``issue_policy.required_single_label_groups``; ``status``
    only for open issues.
``ISSUE-R3``/``ISSUE-R4``
    At most one label of each group in ``issue_policy.optional_single_label_groups``.
``ISSUE-R3``/``ISSUE-R5``
    A planned issue has a label of each group in ``issue_policy.required_for_ready`` that
    ``labels.yml`` defines.
``ISSUE-R7``
    ``agent:ready`` and ``agent:working`` are not set together.
``ISSUE-R8``
    ``agent:ready`` needs the items of ``issue_policy.agent_ready_requires`` that data can show.
``ISSUE-R9``
    ``status:blocked`` names its blocker.
``ISSUE-R11``
    The required fields of the issue form of the type are filled in.

This module only evaluates data. ``run.py`` reads the event, calls the GitHub API and applies
the result. The issue text is data: it is parsed, never executed or passed to a shell, and no
finding quotes it.

Local check of an issue: ``gh api repos/OWNER/REPOSITORY/issues/NUMBER > issue.json``, then
``python -I scripts/ci/issue_validation/validator.py issue.json``. Blockers are not checked
locally. Exit codes: 0 no finding, 1 at least one finding, 2 invalid input.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

WORKFLOW_PATH = ".project/workflow.yml"
LABELS_PATH = ".project/labels.yml"
FORMS_DIR = ".github/ISSUE_TEMPLATE"
FORM_CONFIG = "config.yml"

# A planned issue is in one of these states (docs/governance/issue-management.md).
PLANNED_STATES = frozenset({"ready", "in-progress", "blocked", "review"})
AGENT_READY = "agent:ready"
AGENT_WORKING = "agent:working"
STATUS_BLOCKED = "status:blocked"

# Rule ID per label group; groups without an own rule share ISSUE-R1 (required) or ISSUE-R4.
GROUP_RULES = {
    "type": "ISSUE-R1",
    "status": "ISSUE-R2",
    "priority": "ISSUE-R3",
    "effort": "ISSUE-R4",
    "area": "ISSUE-R5",
}

# Form field ids that hold the acceptance criteria and the scope of an issue, in order of
# preference; the first id the form of the type has is used. ISSUE-R8.
AGENT_READY_FIELDS = {
    "acceptance_criteria": ("acceptance", "criteria", "success"),
    "scope": ("scope", "requirements", "change", "proposal", "expected"),
}
AGENT_READY_NAMES = {"acceptance_criteria": "acceptance criteria", "scope": "a scope"}

# GitHub writes this into a form field that was left empty.
NO_RESPONSE = "_No response_"
REFERENCE_PATTERN = re.compile(
    r"(?:(?:[\w.-]+/[\w.-]+)?#\d+\b|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)"
)


def _load_pr_validator() -> ModuleType:
    """Load the pull request validator; ``python -I`` does not add its directory to sys.path."""
    path = Path(__file__).resolve().parents[1] / "pr_validation" / "validator.py"
    spec = importlib.util.spec_from_file_location("issue_validation_pr_validator", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# The Markdown section parser is shared with the pull request validator.
_pr_validator = _load_pr_validator()
parse_sections = _pr_validator.parse_sections


@dataclass(frozen=True)
class Finding:
    """A failed rule.

    Attributes:
        rule: Rule ID, for example ``ISSUE-R1``.
        message: What is wrong.
        hint: How to fix it.
    """

    rule: str
    message: str
    hint: str


@dataclass(frozen=True)
class FormField:
    """An input field of an issue form.

    Attributes:
        field_id: Stable field id, for example ``reproduction``.
        label: Heading GitHub writes into the issue body, for example ``Steps to Reproduce``.
        required: Whether the form marks the field as required.
    """

    field_id: str
    label: str
    required: bool


@dataclass(frozen=True)
class Policy:
    """The issue rules read from the repository.

    Attributes:
        initial_status: Status value of a new issue, for example ``triage``.
        required_single: Groups that need exactly one label.
        required_for_ready: Groups that a planned issue needs at least one label of.
        optional_single: Groups that allow at most one label.
        agent_ready_requires: Requirements of ``agent:ready``.
        defined_groups: Label groups that ``labels.yml`` defines.
        forms: Type value, for example ``bug``, to the input fields of its form.
    """

    initial_status: str
    required_single: tuple[str, ...]
    required_for_ready: tuple[str, ...]
    optional_single: tuple[str, ...]
    agent_ready_requires: tuple[str, ...]
    defined_groups: frozenset[str]
    forms: Mapping[str, tuple[FormField, ...]]


@dataclass(frozen=True)
class Issue:
    """The issue data the rules need.

    Attributes:
        number: Issue number.
        body: Issue description.
        labels: Label names.
        is_open: Whether the issue is open.
        open_blockers: References of open "blocked by" dependencies; ``None`` if not read.
        has_blocker_dependency: Whether a "blocked by" dependency exists, open or closed.
        comments: Bodies of the comments, without the comment of the validator.
    """

    number: int
    body: str
    labels: tuple[str, ...]
    is_open: bool = True
    open_blockers: tuple[str, ...] | None = None
    has_blocker_dependency: bool = False
    comments: tuple[str, ...] = ()


def read_forms(forms_dir: Path) -> dict[str, tuple[FormField, ...]]:
    """Read the input fields of every issue form, keyed by the type value of the form.

    ``check_issue_forms.py`` ensures in CI that each type has exactly one valid form.

    Args:
        forms_dir: Directory of the issue forms.

    Returns:
        Type value to the input fields of its form, in form order.

    Raises:
        OSError: If a form cannot be read.
        yaml.YAMLError: If a form is not valid YAML.
    """
    forms: dict[str, tuple[FormField, ...]] = {}
    for path in sorted(forms_dir.glob("*.yml")):
        if path.name == FORM_CONFIG:
            continue
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(form, dict):
            continue
        types = [
            label.removeprefix("type:")
            for label in form.get("labels") or []
            if isinstance(label, str) and label.startswith("type:")
        ]
        if len(types) != 1:
            continue
        forms[types[0]] = tuple(
            FormField(
                element["id"],
                element["attributes"]["label"],
                (element.get("validations") or {}).get("required") is True,
            )
            for element in form.get("body") or []
            if isinstance(element, dict)
            and element.get("type") != "markdown"
            and isinstance(element.get("id"), str)
        )
    return forms


def load_policy(repo: Path) -> Policy:
    """Read the issue rules of ``repo``.

    The files are expected to be valid; ``validate_project.py`` checks them in CI.

    Args:
        repo: Repository root.

    Returns:
        The policy.

    Raises:
        OSError: If a file cannot be read.
        KeyError: If a required field is missing.
        yaml.YAMLError: If a file is not valid YAML.
    """
    workflow = yaml.safe_load((repo / WORKFLOW_PATH).read_text(encoding="utf-8"))
    labels = yaml.safe_load((repo / LABELS_PATH).read_text(encoding="utf-8"))
    policy = workflow["issue_policy"]
    return Policy(
        initial_status=policy["initial_status"],
        required_single=tuple(policy["required_single_label_groups"]),
        required_for_ready=tuple(policy["required_for_ready"]),
        optional_single=tuple(policy["optional_single_label_groups"]),
        agent_ready_requires=tuple(policy["agent_ready_requires"]),
        defined_groups=frozenset(
            label["name"].partition(":")[0]
            for label in labels["labels"]
            if ":" in label["name"]
        ),
        forms=read_forms(repo / FORMS_DIR),
    )


def group_labels(labels: Iterable[str], group: str) -> list[str]:
    """Return the labels of ``group``, for example ``priority:high`` for ``priority``."""
    return [label for label in labels if label.startswith(f"{group}:")]


def _values(labels: Iterable[str], group: str) -> list[str]:
    return [label.partition(":")[2] for label in group_labels(labels, group)]


def _names(labels: Sequence[str]) -> str:
    return ", ".join(f"`{label}`" for label in labels)


def check_labels(issue: Issue, policy: Policy) -> list[Finding]:
    """Check the label groups (ISSUE-R1 to ISSUE-R5) and the agent labels (ISSUE-R7)."""
    findings = []
    for group in policy.required_single:
        if group == "status" and not issue.is_open:
            continue
        found = group_labels(issue.labels, group)
        if len(found) == 1:
            continue
        message = (
            f"no `{group}:*` label is set"
            if not found
            else f"{len(found)} `{group}:*` labels are set ({_names(found)})"
        )
        findings.append(
            Finding(
                GROUP_RULES.get(group, "ISSUE-R1"),
                f"{message}; exactly one is required",
                f"keep exactly one `{group}:*` label",
            )
        )
    for group in policy.optional_single:
        found = group_labels(issue.labels, group)
        if len(found) > 1:
            findings.append(
                Finding(
                    GROUP_RULES.get(group, "ISSUE-R4"),
                    f"{len(found)} `{group}:*` labels are set ({_names(found)}); "
                    "at most one is allowed",
                    f"remove all but one `{group}:*` label",
                )
            )
    states = _values(issue.labels, "status")
    if issue.is_open and len(states) == 1 and states[0] in PLANNED_STATES:
        for group in policy.required_for_ready:
            if group in policy.defined_groups and not group_labels(issue.labels, group):
                findings.append(
                    Finding(
                        GROUP_RULES.get(group, "ISSUE-R5"),
                        f"`status:{states[0]}` needs a `{group}:*` label",
                        f"add a `{group}:*` label, or move the issue back to "
                        f"`status:{policy.initial_status}`",
                    )
                )
    if AGENT_READY in issue.labels and AGENT_WORKING in issue.labels:
        findings.append(
            Finding(
                "ISSUE-R7",
                f"`{AGENT_READY}` and `{AGENT_WORKING}` are set together",
                f"remove `{AGENT_READY}` once an agent works on the issue",
            )
        )
    return findings


def _is_filled(section: str | None) -> bool:
    if section is None:
        return False
    text = section.strip()
    return bool(text) and text != NO_RESPONSE


def _issue_form(issue: Issue, policy: Policy) -> tuple[FormField, ...] | None:
    types = _values(issue.labels, "type")
    return policy.forms.get(types[0]) if len(types) == 1 else None


def check_sections(issue: Issue, policy: Policy) -> list[Finding]:
    """Check that the required fields of the issue form of the type are filled in (ISSUE-R11)."""
    form = _issue_form(issue, policy)
    if form is None:
        return []
    sections = parse_sections(issue.body)
    return [
        Finding(
            "ISSUE-R11",
            f"section {field.label!r} is "
            f"{'missing' if field.label not in sections else 'empty'}",
            f"add the heading '### {field.label}' with its content to the description",
        )
        for field in form
        if field.required and not _is_filled(sections.get(field.label))
    ]


def check_agent_ready(issue: Issue, policy: Policy) -> list[Finding]:
    """Check the requirements of ``agent:ready`` that data can show (ISSUE-R8).

    ``approved_permissions`` needs a human decision and is checked in review. An empty section
    of a required form field is left to ISSUE-R11, so it is not reported twice.
    """
    if AGENT_READY not in issue.labels or not issue.is_open:
        return []
    findings = []
    form = _issue_form(issue, policy) or ()
    sections = parse_sections(issue.body)
    for requirement, field_ids in AGENT_READY_FIELDS.items():
        if requirement not in policy.agent_ready_requires:
            continue
        field = next(
            (
                field
                for field_id in field_ids
                for field in form
                if field.field_id == field_id
            ),
            None,
        )
        if field is None or field.required or _is_filled(sections.get(field.label)):
            continue
        findings.append(
            Finding(
                "ISSUE-R8",
                f"`{AGENT_READY}` needs {AGENT_READY_NAMES[requirement]} "
                f"(section {field.label!r})",
                f"fill in {field.label!r}, or remove `{AGENT_READY}`",
            )
        )
    if "no_unresolved_blockers" in policy.agent_ready_requires:
        if STATUS_BLOCKED in issue.labels:
            findings.append(
                Finding(
                    "ISSUE-R8",
                    f"`{AGENT_READY}` is set on an issue in `{STATUS_BLOCKED}`",
                    f"remove `{AGENT_READY}` until the blocker is resolved",
                )
            )
        if issue.open_blockers:
            findings.append(
                Finding(
                    "ISSUE-R8",
                    f"`{AGENT_READY}` is set, but the issue is blocked by open issue(s) "
                    f"{', '.join(issue.open_blockers)}",
                    f"remove `{AGENT_READY}` until the blocking issues are closed",
                )
            )
    return findings


def check_blocked(issue: Issue) -> list[Finding]:
    """Check that an issue in ``status:blocked`` names its blocker (ISSUE-R9).

    A "blocked by" dependency, or an issue reference in the description or a comment, counts.
    """
    if STATUS_BLOCKED not in issue.labels or not issue.is_open:
        return []
    if issue.has_blocker_dependency or issue.open_blockers:
        return []
    texts = (issue.body, *issue.comments)
    if any(REFERENCE_PATTERN.search(text) for text in texts):
        return []
    return [
        Finding(
            "ISSUE-R9",
            f"`{STATUS_BLOCKED}` does not name a blocker",
            "add a 'blocked by' dependency, or reference the blocker (#123) in a comment",
        )
    ]


def check_issue(issue: Issue, policy: Policy) -> list[Finding]:
    """Apply every rule.

    Args:
        issue: The issue.
        policy: The configured rules.

    Returns:
        All findings, in rule order.
    """
    findings = check_labels(issue, policy)
    findings += check_sections(issue, policy)
    findings += check_agent_ready(issue, policy)
    findings += check_blocked(issue)
    return sorted(findings, key=lambda finding: int(finding.rule.rpartition("R")[2]))


def issue_from_api(data: Mapping[str, Any]) -> Issue:
    """Build an :class:`Issue` from a REST API issue object, without blockers and comments.

    Raises:
        ValueError: If the object is not an issue.
    """
    if not isinstance(data, Mapping):
        raise ValueError("the issue is not a JSON object")  # noqa: TRY004 - input error
    number = data.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        raise ValueError("the issue has no number")  # noqa: TRY004 - input error
    labels = tuple(
        label["name"] if isinstance(label, dict) else label
        for label in data.get("labels") or []
    )
    if not all(isinstance(label, str) for label in labels):
        raise ValueError("the issue has invalid labels")
    return Issue(
        number=number,
        body=data.get("body") or "",
        labels=labels,
        is_open=data.get("state", "open") == "open",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Check a REST API issue JSON file; see the module docstring."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("issue", type=Path, help="issue JSON from the REST API")
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.repo)
        issue = issue_from_api(json.loads(args.issue.read_text(encoding="utf-8")))
    except (OSError, KeyError, ValueError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    findings = check_issue(issue, policy)
    for finding in findings:
        print(f"error: [{finding.rule}] {finding.message}\n  fix: {finding.hint}")
    print(f"Issue validation: {len(findings)} problem(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
