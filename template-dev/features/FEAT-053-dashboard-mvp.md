---
id: "FEAT-053"
title: "Build Read-Only Dashboard MVP"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "low"
effort: "l"
target_repo: "dashboard"
spec_refs: ["§2.4", "§15.3", "§15.4", "§16.6"]
dependencies: ["FEAT-052"]
blocked_by_decisions: ["DEC-09"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-053: Build Read-Only Dashboard MVP

## Objective

A read-only dashboard shows all repositories with health score, work items, delivery, CI, security,
docs and agent status from exported snapshots.

## Background

§2.4 and §16.6 end state: the dashboard links template, bootstrap, workflows and agents. §15.3 data
model, §15.4 security-critical findings shown separately. Blocked by `DEC-09` (does it run without an
external server).

## Scope

- Static or local web app reading snapshot files (default per `DEC-09`).
- Overview table, repository detail page, security findings view.

### Out of Scope

- Writes to GitHub; script execution (`FEAT-054`).

## Deliverables

| Path | Description |
|---|---|
| `dashboard/app/**` | UI; stack chosen in the options analysis for `DEC-09` |
| `dashboard/app/tests/**` | Rendering from sample snapshots |
| `dashboard/README.md` (section) | How to run locally and refresh data |

## Requirements

1. **R1:** Works offline from snapshot files.
2. **R2:** Security-critical findings are visually separated and never averaged into the score display.
3. **R3:** No credentials stored in the app.
4. **R4:** Accessible: keyboard navigation, sufficient contrast.

## Tasks

- [ ] **T1:** Options analysis for `DEC-09` (agent prepares, human decides).
- [ ] **T2:** Overview and detail views.
- [ ] **T3:** Tests with sample data.

## Acceptance Criteria

- [ ] With sample snapshots, the overview lists all repositories with score and critical-findings count.

## Verification

```text
# Per chosen stack, e.g. npm test in dashboard/app
```

## Agent Notes

- **Allowed paths:** `dashboard/**`, this feature file, backlog status.
- **Requires approval:** resolving `DEC-09`; any hosting.
- **Pitfalls:** Do not build live API access into the MVP; it pulls in auth and rate limits.
