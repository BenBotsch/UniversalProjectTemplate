---
id: "FEAT-008"
title: "Define Complete Label Taxonomy in labels.yml"
epic: "EPIC-03"
phase: 1
status: "implemented"
priority: "critical"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§6.1", "§6.4", "§9.5"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-008: Define Complete Label Taxonomy in labels.yml

## Objective

`.project/labels.yml` declares every label of the target taxonomy with name, color, description and
group, and is the single declarative source for label synchronization.

## Background

§6.1 is the target taxonomy (type, priority, status, area, effort, impact, agent). §6.4 shows the
schema and a core subset only; the final file must contain all groups. `.github/release.yml` (§9.5)
needs `skip-changelog`.

## Scope

- All labels of §6.1 plus `skip-changelog`.
- Color logic per group, documented so new labels follow it.
- Extension rule for project-specific labels (`area:desktop`, `platform:windows`, ...).

### Out of Scope

- Synchronizing labels to GitHub (`FEAT-023`, `FEAT-025`).
- JSON Schema for the file (`FEAT-014`).

## Deliverables

| Path | Description |
|---|---|
| `.project/labels.yml` | `schema_version: "1.0"`, list of labels; groups: `type`, `priority`, `status`, `area`, `effort`, `impact`, `agent`, `meta` |
| `docs/governance/issue-management.md` (section) | "Label taxonomy" table and color logic; coordinated with `FEAT-009` |

## Requirements

1. **R1:** Contains exactly these groups and labels at minimum:
   - type: `bug`, `task`, `feature`, `epic`, `improvement`, `documentation`
   - priority: `critical`, `high`, `medium`, `low`
   - status: `triage`, `ready`, `in-progress`, `blocked`, `review`, `needs-info`
   - area: `backend`, `frontend`, `api`, `ci-cd`, `docs`, `security`
   - effort: `xs`, `s`, `m`, `l`, `xl`
   - impact: `breaking`, `performance`, `security`
   - agent: `ready`, `working`, `review-required`
   - meta: `skip-changelog`
2. **R2:** Colors and descriptions of §6.4 are kept for the labels listed there.
3. **R3:** Each group has a consistent color scheme (e.g. priority red-to-green gradient, all `area:*` one hue).
4. **R4:** Names are lowercase `group:value` with kebab-case values; `skip-changelog` is the only label without a group prefix and is documented as such.
5. **R5:** Colors are 6-digit hex without `#`; descriptions are at most 100 characters (GitHub limit).
6. **R6:** No `status:done` label; closed state is the native issue state (§6.3 note).

## Tasks

- [x] **T1:** Write `.project/labels.yml`.
- [x] **T2:** Document taxonomy and color logic.
- [x] **T3:** Add a lightweight check (until `FEAT-014`): unique names, valid hex, description length, name prefix matches `group`.

## Acceptance Criteria

- [x] All labels of §6.1 are present with group, color and description.
- [x] The check from T3 passes and fails on a duplicate name or invalid color.
- [x] `labels.yml` is usable as the source for `gh label create` loops in `FEAT-023`.

## Verification

```text
python -I scripts/ci/check_labels.py .project/labels.yml
```

## Agent Notes

- **Allowed paths:** `.project/labels.yml`, `scripts/ci/check_labels.py` (+ test), taxonomy section in `docs/governance/issue-management.md`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** §19: labels on PRs and issues can diverge; release notes use PR labels. Note this in the docs section.
