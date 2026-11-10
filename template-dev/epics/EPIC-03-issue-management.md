---
id: "EPIC-03"
title: "Issue Management"
phase: 1
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-03: Issue Management

## Goal and Value

Structured, machine-readable issues: six forms, a complete label taxonomy, written lifecycle rules and an optional Projects board.

## Scope and Deliverables

- Issue forms and `config.yml` (§5)
- `labels.yml` with all categories of §6.1 and §6.4
- Issue management rules: invariants, lifecycle, severity vs. priority, hierarchy (§5.11, §6.2, §6.3, §6.6)
- Optional GitHub Projects setup (§15.1, `DEC-03`)

## Non-Goals

- Automated validation of issues (`FEAT-018` in EPIC-06)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-007](../features/FEAT-007-issue-forms.md) | Add Issue Forms and Issue Template Configuration | 1 | critical | 008 | implemented |
| [FEAT-008](../features/FEAT-008-label-taxonomy.md) | Define Complete Label Taxonomy in labels.yml | 1 | critical | 001 | implemented |
| [FEAT-009](../features/FEAT-009-issue-management-governance.md) | Document Issue Management Rules and Lifecycle | 1 | high | 003, 008 | implemented |
| [FEAT-010](../features/FEAT-010-github-projects.md) | Provide Optional GitHub Projects Board Setup | 2 | medium | 008, 024 | planned |

## Risks and Dependencies

- Label explosion; every label needs a documented purpose
- `DEC-03` open: Projects stays optional
- External feature dependencies: `FEAT-001`, `FEAT-003`, `FEAT-024`
- Blocking decisions: `DEC-03` (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- Every form produces an issue with `status:triage` and a `type:*` label
- `labels.yml` validates against its schema and is the only source of label definitions
