---
id: "FEAT-022"
title: "Suggest Priority from Bug Severity"
epic: "EPIC-06"
phase: 2
status: "planned"
priority: "low"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§5.4", "§6.6", "§19"]
dependencies: ["FEAT-018"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-022: Suggest Priority from Bug Severity

## Objective

For bugs, the issue validator suggests a `priority:*` label derived from the Severity dropdown,
as a comment only; the final priority stays a triage decision.

## Background

Severity (impact) and priority (urgency) differ (§6.6). Dropdown values are plain text in the body
and never become labels natively (§5.4, §19). A mapper may propose but not decide.

## Scope

- Configurable mapping in `.project/workflow.yml` (default Critical→critical, High→high,
  Medium→medium, Low→low).
- Suggestion line inside the existing validation comment of `FEAT-018`.

### Out of Scope

- Automatically applying the priority label.

## Deliverables

| Path | Description |
|---|---|
| `scripts/ci/issue_validation/severity.py` | Parses the Severity section, returns suggestion |
| `.project/workflow.yml` (section) | `severity_priority_suggestion` map + schema update |
| `tests/ci/issue_validation/test_severity.py` | Each severity, missing severity, unknown value |

## Requirements

1. **R1:** Never adds or removes a `priority:*` label.
2. **R2:** Suggests only when no `priority:*` label is set.
3. **R3:** Unknown severity text produces no suggestion and no error.

## Tasks

- [ ] **T1:** Parser and mapping with tests.
- [ ] **T2:** Integrate into the comment renderer of `FEAT-018`.

## Acceptance Criteria

- [ ] A Bug with Severity "High" and no priority gets the suggestion `priority:high` in the bot comment, and no label change.

## Verification

```text
python -I -m pytest tests/ci/issue_validation/test_severity.py
```

## Agent Notes

- **Allowed paths:** files above, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Do not conflate severity and priority in wording; the comment says "suggested".
