"""Tests for scripts/ci/issue_validation/validator.py.

The policy and the forms are the repository's own files, so the tests fail if the configuration,
the issue forms and the validator drift apart.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "issue_validator_under_test",
    ROOT / "scripts" / "ci" / "issue_validation" / "validator.py",
)
validator = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validator
_spec.loader.exec_module(validator)

POLICY = validator.load_policy(ROOT)


def filled_body(issue_type: str, *, skip: tuple[str, ...] = ()) -> str:
    """Render an issue body as an issue form would, with every field filled in."""
    parts = []
    for form_field in POLICY.forms[issue_type]:
        if form_field.field_id in skip:
            continue
        parts.append(f"### {form_field.label}\n\nSome {form_field.field_id}.\n")
    return "\n".join(parts)


def make_issue(issue_type: str = "bug", *labels: str, **changes: object):
    """A valid triaged issue of ``issue_type``, with ``labels`` added."""
    issue = validator.Issue(
        number=7,
        body=filled_body(issue_type),
        labels=(f"type:{issue_type}", "status:triage", *labels),
    )
    return replace(issue, **changes)


def rules(findings) -> list[str]:
    return [finding.rule for finding in findings]


# Configuration


def test_forms_are_read_for_every_supported_type() -> None:
    assert set(POLICY.forms) == {
        "bug",
        "task",
        "feature",
        "epic",
        "improvement",
        "documentation",
    }
    labels = {f.field_id: f.label for f in POLICY.forms["bug"]}
    assert labels["reproduction"] == "Steps to Reproduce"


def test_policy_reads_the_label_groups() -> None:
    assert POLICY.required_single == ("type", "status")
    assert POLICY.required_for_ready == ("priority", "area")
    assert POLICY.optional_single == ("priority", "effort")
    assert {"type", "status", "priority", "area", "effort", "agent"} <= set(
        POLICY.defined_groups
    )


@pytest.mark.parametrize("issue_type", sorted(POLICY.forms))
def test_complete_triaged_issue_of_every_type_passes(issue_type: str) -> None:
    assert validator.check_issue(make_issue(issue_type), POLICY) == []


# §21.6 issue cases


def test_issue_without_type_label_fails() -> None:
    issue = replace(make_issue(), labels=("status:triage",))
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R1"]
    assert "no `type:*` label" in findings[0].message


def test_two_priority_labels_fail() -> None:
    issue = make_issue("bug", "priority:high", "priority:low")
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R3"]
    assert "at most one" in findings[0].message


def test_bug_without_reproduction_steps_fails() -> None:
    issue = make_issue(body=filled_body("bug", skip=("reproduction",)))
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R11"]
    assert findings[0].message == "section 'Steps to Reproduce' is missing"


def test_agent_ready_with_open_blocker_fails() -> None:
    issue = make_issue("task", "agent:ready", open_blockers=("#12", "octo/other#3"))
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R8"]
    assert "#12, octo/other#3" in findings[0].message


# Label rules


def test_two_type_labels_fail() -> None:
    issue = make_issue("bug", "type:task")
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R1"]
    assert "2 `type:*` labels" in findings[0].message


@pytest.mark.parametrize(
    "labels",
    [("type:bug",), ("type:bug", "status:triage", "status:ready")],
    ids=["none", "two"],
)
def test_open_issue_needs_exactly_one_status(labels: tuple[str, ...]) -> None:
    issue = replace(make_issue(), labels=labels)
    assert rules(validator.check_issue(issue, POLICY)) == ["ISSUE-R2"]


def test_closed_issue_needs_no_status() -> None:
    issue = replace(make_issue(), labels=("type:bug",), is_open=False)
    assert validator.check_issue(issue, POLICY) == []


def test_two_effort_labels_fail() -> None:
    issue = make_issue("task", "effort:s", "effort:m")
    assert rules(validator.check_issue(issue, POLICY)) == ["ISSUE-R4"]


@pytest.mark.parametrize("state", ["ready", "in-progress", "review"])
def test_planned_issue_needs_priority_and_area(state: str) -> None:
    issue = replace(make_issue(), labels=("type:bug", f"status:{state}"))
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R3", "ISSUE-R5"]
    assert findings[0].message == f"`status:{state}` needs a `priority:*` label"


def test_planned_issue_with_priority_and_area_passes() -> None:
    issue = replace(
        make_issue(),
        labels=("type:bug", "status:ready", "priority:high", "area:api", "area:docs"),
    )
    assert validator.check_issue(issue, POLICY) == []


def test_triaged_issue_needs_no_priority() -> None:
    assert validator.check_issue(make_issue(), POLICY) == []


def test_required_group_without_defined_labels_is_not_required() -> None:
    policy = replace(POLICY, defined_groups=POLICY.defined_groups - {"area"})
    issue = replace(make_issue(), labels=("type:bug", "status:ready", "priority:high"))
    assert validator.check_issue(issue, policy) == []


def test_agent_ready_and_working_together_fail() -> None:
    issue = make_issue("task", "agent:ready", "agent:working", open_blockers=())
    assert rules(validator.check_issue(issue, POLICY)) == ["ISSUE-R7"]


def test_labels_without_group_are_ignored() -> None:
    assert validator.check_issue(make_issue("bug", "skip-changelog"), POLICY) == []


# Sections


def test_section_with_no_response_is_empty() -> None:
    body = filled_body("task").replace("Some scope.", "_No response_")
    findings = validator.check_issue(make_issue("task", body=body), POLICY)
    assert [f.message for f in findings] == ["section 'Scope' is empty"]


def test_optional_section_may_be_empty() -> None:
    body = filled_body("task", skip=("dependencies",))
    assert validator.check_issue(make_issue("task", body=body), POLICY) == []


def test_heading_inside_code_fence_does_not_count() -> None:
    body = filled_body("documentation", skip=("change",))
    body += "\n```text\n### Required Change\n\ntext\n```\n"
    findings = validator.check_issue(make_issue("documentation", body=body), POLICY)
    assert rules(findings) == ["ISSUE-R11"]


def test_heading_inside_html_comment_does_not_count() -> None:
    body = filled_body("improvement", skip=("criteria",))
    body += "\n<!--\n### Acceptance Criteria\n\ntext\n-->\n"
    findings = validator.check_issue(make_issue("improvement", body=body), POLICY)
    assert rules(findings) == ["ISSUE-R11"]


def test_issue_without_type_is_not_checked_for_sections() -> None:
    issue = validator.Issue(number=1, body="", labels=("status:triage",))
    assert rules(validator.check_issue(issue, POLICY)) == ["ISSUE-R1"]


def test_empty_body_reports_every_required_section() -> None:
    findings = validator.check_issue(make_issue("epic", body=""), POLICY)
    assert rules(findings) == ["ISSUE-R11"] * 6


# agent:ready


def test_agent_ready_without_blockers_passes() -> None:
    issue = make_issue("feature", "agent:ready", open_blockers=())
    assert validator.check_issue(issue, POLICY) == []


def test_agent_ready_on_blocked_issue_fails() -> None:
    issue = replace(
        make_issue("task", open_blockers=(), has_blocker_dependency=True),
        labels=(
            "type:task",
            "status:blocked",
            "priority:high",
            "area:api",
            "agent:ready",
        ),
    )
    findings = validator.check_issue(issue, POLICY)
    assert rules(findings) == ["ISSUE-R8"]
    assert "`status:blocked`" in findings[0].message


def test_agent_ready_reports_an_optional_scope_section() -> None:
    form = tuple(
        replace(f, required=False) if f.field_id == "scope" else f
        for f in POLICY.forms["task"]
    )
    policy = replace(POLICY, forms={**POLICY.forms, "task": form})
    issue = make_issue(
        "task",
        "agent:ready",
        body=filled_body("task", skip=("scope",)),
        open_blockers=(),
    )
    findings = validator.check_issue(issue, policy)
    assert rules(findings) == ["ISSUE-R8"]
    assert findings[0].message == "`agent:ready` needs a scope (section 'Scope')"


def test_agent_ready_does_not_repeat_a_required_section() -> None:
    issue = make_issue(
        "bug",
        "agent:ready",
        body=filled_body("bug", skip=("acceptance",)),
        open_blockers=(),
    )
    assert rules(validator.check_issue(issue, POLICY)) == ["ISSUE-R11"]


def test_agent_ready_requirements_follow_the_policy() -> None:
    policy = replace(POLICY, agent_ready_requires=("approved_permissions",))
    issue = make_issue("task", "agent:ready", open_blockers=("#3",))
    assert validator.check_issue(issue, policy) == []


# status:blocked


def blocked_issue(**changes: object):
    issue = replace(
        make_issue("task"),
        labels=("type:task", "status:blocked", "priority:high", "area:api"),
    )
    return replace(issue, **changes)


def test_blocked_issue_without_blocker_fails() -> None:
    assert rules(validator.check_issue(blocked_issue(), POLICY)) == ["ISSUE-R9"]


@pytest.mark.parametrize(
    "changes",
    [
        {"has_blocker_dependency": True},
        {"comments": ("Waiting for #12.",)},
        {"comments": ("Blocked by octo/api#4",)},
        {"comments": ("See https://github.com/octo/api/issues/4",)},
    ],
    ids=["dependency", "comment", "cross-repository", "url"],
)
def test_blocked_issue_with_blocker_passes(changes: dict[str, object]) -> None:
    assert validator.check_issue(blocked_issue(**changes), POLICY) == []


def test_blocker_reference_in_the_body_counts() -> None:
    issue = blocked_issue()
    issue = replace(issue, body=issue.body + "\nBlocked by #9.\n")
    assert validator.check_issue(issue, POLICY) == []


# API objects and command line


def test_issue_from_api_reads_labels_and_state() -> None:
    issue = validator.issue_from_api(
        {
            "number": 4,
            "body": None,
            "state": "closed",
            "labels": [{"name": "type:bug"}, "status:triage"],
        }
    )
    assert issue == validator.Issue(
        number=4, body="", labels=("type:bug", "status:triage"), is_open=False
    )


@pytest.mark.parametrize(
    "data",
    [{"labels": []}, {"number": True}, {"number": 1, "labels": [{"name": 3}]}],
)
def test_issue_from_api_rejects_invalid_objects(data: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="the issue has"):
        validator.issue_from_api(data)


def test_main_reports_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "issue.json"
    path.write_text(json.dumps({"number": 1, "labels": []}), encoding="utf-8")
    assert validator.main([str(path), "--repo", str(ROOT)]) == 1
    output = capsys.readouterr().out
    assert "[ISSUE-R1]" in output
    assert "[ISSUE-R2]" in output


def test_main_passes_a_valid_issue(tmp_path: Path) -> None:
    path = tmp_path / "issue.json"
    issue = {
        "number": 1,
        "body": filled_body("bug"),
        "labels": [{"name": "type:bug"}, {"name": "status:triage"}],
    }
    path.write_text(json.dumps(issue), encoding="utf-8")
    assert validator.main([str(path), "--repo", str(ROOT)]) == 0


def test_main_rejects_invalid_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "issue.json"
    path.write_text("[]", encoding="utf-8")
    assert validator.main([str(path), "--repo", str(ROOT)]) == 2
    assert "error:" in capsys.readouterr().err
