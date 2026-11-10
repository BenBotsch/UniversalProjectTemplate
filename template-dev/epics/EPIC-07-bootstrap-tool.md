---
id: "EPIC-07"
title: "Bootstrap Tool"
phase: 2
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-07: Bootstrap Tool

## Goal and Value

Repeatable, idempotent GitHub setup: a phase A script with `gh`, then the `project-bootstrap` CLI with plan/apply, labels, branches, settings, rulesets, init, validate and audit.

## Scope and Deliverables

- Phase A PowerShell script (§13.3, §13.4, §13.8)
- CLI core, `sync-labels`, branches and settings, rulesets with plan detection and solo mode (§8.7, §13.5-§13.7, §14)
- `init` with template-only cleanup (§13.2)
- `validate`/`audit` with health score (§13.7, §15.4)
- End-to-end test suite (§13.8, §17.6)

## Non-Goals

- Cross-owner audit (`FEAT-051`)
- Template upgrades (`FEAT-046`)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-023](../features/FEAT-023-bootstrap-phase-a-script.md) | Provide Phase A Bootstrap Script with GitHub CLI | 2 | high | 008, 013 | implemented |
| [FEAT-024](../features/FEAT-024-bootstrap-cli-core.md) | Build Bootstrap CLI Core with Plan, Apply and Reports | 2 | critical | 013, 014 | implemented |
| [FEAT-025](../features/FEAT-025-sync-labels.md) | Implement Idempotent Label Synchronization | 2 | high | 008, 024 | implemented |
| [FEAT-026](../features/FEAT-026-branches-and-repo-settings.md) | Configure Branches and Repository Settings | 2 | high | 024 | implemented |
| [FEAT-027](../features/FEAT-027-rulesets-and-plan-detection.md) | Apply Rulesets with Plan Detection and Solo Mode | 2 | high | 020, 026 | implemented |
| [FEAT-028](../features/FEAT-028-project-init.md) | Initialize Derived Project and Remove Template-Only Content | 2 | critical | 002, 007, 013, 015, 024 | implemented |
| [FEAT-029](../features/FEAT-029-validate-audit-health.md) | Implement Validate, Audit, Drift Detection and Health Score | 2 | medium | 015, 025, 026, 027 | planned |
| [FEAT-030](../features/FEAT-030-bootstrap-test-suite.md) | Build Bootstrap End-to-End Test Suite | 2 | high | 025, 026, 027, 028 | planned |

## Risks and Dependencies

- `DEC-01` is decided: Python CLI (ADR-0002)
- Plan-dependent features (rulesets on private Free repos) must degrade with a clear report, not fail silently
- Writes to real repositories need approval
- External feature dependencies: `FEAT-002`, `FEAT-007`, `FEAT-008`, `FEAT-013`, `FEAT-014`, `FEAT-015`, `FEAT-020`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- Two test repositories created independently have identical labels, branches and rules
- A second `apply` reports no changes
- `init` removes `template-dev/` and a second `init` does not fail
