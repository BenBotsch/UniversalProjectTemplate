---
id: "FEAT-007"
title: "Add Issue Forms and Issue Template Configuration"
epic: "EPIC-03"
phase: 1
status: "implemented"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§5.1", "§5.2", "§5.3", "§5.4", "§5.5", "§5.6", "§5.7", "§5.8", "§5.9", "§5.10"]
dependencies: ["FEAT-008"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-007: Add Issue Forms and Issue Template Configuration

## Objective

Six YAML issue forms (Bug, Task, Feature, Epic, Improvement, Documentation) and `config.yml`
produce structured issues with the default labels from `labels.yml`.

## Background

§5.4 to §5.9 contain complete reference forms; §5.3 the `config.yml` with placeholder contact
links. Security vulnerabilities get no public form (§5.10). Forms set labels only if those labels
exist in the repository (§5.2); they are synchronized by bootstrap (`FEAT-023`, `FEAT-025`).
Forms are not a hard barrier: API and CLI can bypass them, so `FEAT-018` validates afterwards.
Initial labels follow `DEC-05` default: `type:*` + `status:triage`, no priority.

## Scope

- Six forms based on §5.4 to §5.9 and `config.yml` from §5.3.
- Stable field `id`s, because `FEAT-018` parses issue bodies by heading.

### Out of Scope

- Server-side validation (`FEAT-018`), severity mapping (`FEAT-022`), native issue types (`DEC-04`).

## Deliverables

| Path | Description |
|---|---|
| `.github/ISSUE_TEMPLATE/bug.yml` | §5.4 |
| `.github/ISSUE_TEMPLATE/task.yml` | §5.5 |
| `.github/ISSUE_TEMPLATE/feature.yml` | §5.6 |
| `.github/ISSUE_TEMPLATE/epic.yml` | §5.7, hint to use native sub-issues |
| `.github/ISSUE_TEMPLATE/improvement.yml` | §5.8 |
| `.github/ISSUE_TEMPLATE/documentation.yml` | §5.9, additionally sets `area:docs` |
| `.github/ISSUE_TEMPLATE/config.yml` | §5.3, `blank_issues_enabled: false`, placeholder links `OWNER/REPOSITORY` |
| `docs/governance/issue-management.md` (section) | Table "Form field id → issue body heading" for parsers; coordinated with `FEAT-009` |

## Requirements

1. **R1:** Every label referenced in a form exists in `.project/labels.yml`.
2. **R2:** Required fields from §5.1 are `validations.required: true` per type.
3. **R3:** Field `id`s and labels are unique per form and stable; renaming requires updating `FEAT-018` tests.
4. **R4:** The Bug form keeps Severity as a dropdown and does not imply a priority label (§5.4 note, §6.6).
5. **R5:** No form asks for secrets or vulnerability details; the Bug form shows the "do not disclose credentials" notice.
6. **R6:** `config.yml` documents in comments that the security link requires private vulnerability reporting and the support link requires Discussions.

## Tasks

- [x] **T1:** Add Bug, Task and Feature forms.
- [x] **T2:** Add Epic, Improvement and Documentation forms.
- [x] **T3:** Add `config.yml`.
- [x] **T4:** Add a test (script or CI step from `FEAT-016`) that checks every form label exists in `labels.yml` and every form parses as YAML.

## Acceptance Criteria

- [x] Bug, Task, Feature and Epic issue forms are available (§17.2).
- [x] Improvement and Documentation forms are available (§17.2).
- [x] A test fails when a form references a label missing from `labels.yml`.
- [x] In a test repository with synchronized labels, each form creates an issue with the expected labels (manual check after `FEAT-023`).

## Verification

```text
python -I scripts/ci/check_issue_forms.py     # created in T4
# Manual: GitHub "New issue" page shows exactly six forms plus two contact links, no blank issue.
```

## Agent Notes

- **Allowed paths:** `.github/ISSUE_TEMPLATE/**`, `scripts/ci/check_issue_forms.py` (+ test), the mapping section in `docs/governance/issue-management.md`, this feature file, backlog status.
- **Requires approval:** creating issues in a real repository.
- **Pitfalls:** §19: Issue Forms do not enforce required fields for API-created issues; Severity dropdown does not set a label.

## Implementation Notes

- Label check (2026-11-10) in the private test repository `BenBotsch/upt-smoke-2` with synchronized
  labels, whose forms are identical to this template (same blob SHAs): one issue per
  form (#1 to #6) was created with `gh issue create`, using the title prefix, labels and field
  headings of each form. Each issue has exactly the labels of its form. Limitation: the issues
  were created through the API, not through the web form, so the form rendering and the
  "New issue" chooser were not checked.
