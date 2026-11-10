---
id: "EPIC-04"
title: "Branching and Pull Requests"
phase: 1
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-04: Branching and Pull Requests

## Goal and Value

Predictable collaboration: a PR template, CODEOWNERS convention, and documented branching, commit and release conventions.

## Scope and Deliverables

- PR template and CODEOWNERS (§8.4, §8.6)
- Branching, commit and release governance (§8, §9)

## Non-Goals

- Enforcement through rulesets (`FEAT-027`) and PR validation (`FEAT-019`)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-011](../features/FEAT-011-pr-template-and-codeowners.md) | Add Pull Request Template and CODEOWNERS Convention | 1 | critical | 001 | implemented |
| [FEAT-012](../features/FEAT-012-branching-commit-release-docs.md) | Document Branching, Commit and Release Conventions | 1 | high | 003 | implemented |

## Risks and Dependencies

- Conventions that differ from what rulesets later enforce; `FEAT-027` must read the same config
- External feature dependencies: `FEAT-001`, `FEAT-003`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- A PR opened in a derived repository shows the template with linked-issue and verification sections
- Branch model `main`/`develop`/`feature/*`/`release/*`/`hotfix/*` is documented once
