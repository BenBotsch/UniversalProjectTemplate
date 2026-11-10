---
id: "EPIC-06"
title: "Universal CI and Validation"
phase: 2
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-06: Universal CI and Validation

## Goal and Value

Enforce metadata and quality automatically: repository, issue and PR validation, base CI, security baseline, quality gates without false green pipelines, Dependabot.

## Scope and Deliverables

- `validate_repository.py` with placeholder and template-only checks (§10.6, §19)
- `ci.yml`, `quality.yml`, `security.yml` (§10.2, §10.6, §11.1, §11.2)
- Issue and PR validators (§6.5, §8.5, §21.5, §21.6)
- Quality-gate evaluator and quality model (§4.3, §10.7, §10.9)
- Dependabot and severity-to-priority suggestion (§10.8, §6.6)

## Non-Goals

- Technology-specific jobs (EPIC-08)
- Release workflows (EPIC-09)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-015](../features/FEAT-015-repository-validator.md) | Implement Repository Validator with Placeholder and Template-Only Checks | 2 | critical | 014 | implemented |
| [FEAT-016](../features/FEAT-016-base-ci-workflows.md) | Add Universal Base CI and Quality Workflows | 2 | critical | 014, 015 | implemented |
| [FEAT-017](../features/FEAT-017-security-baseline-workflow.md) | Add Security Baseline Workflow and Secret Scanning | 2 | critical | 016 | implemented |
| [FEAT-018](../features/FEAT-018-issue-validation.md) | Implement Issue Validator and Issue Validation Workflow | 2 | high | 007, 008, 009, 014 | planned |
| [FEAT-019](../features/FEAT-019-pr-validation-and-commitlint.md) | Implement Pull Request Validation and Commit Convention Checks | 2 | high | 011, 012, 014 | implemented |
| [FEAT-020](../features/FEAT-020-quality-gate-evaluator.md) | Enforce Quality Gates Without False Green Pipelines | 2 | high | 013, 016 | implemented |
| [FEAT-021](../features/FEAT-021-dependabot.md) | Configure Dependabot Baseline | 2 | high | 008 | implemented |
| [FEAT-022](../features/FEAT-022-severity-priority-suggestion.md) | Suggest Priority from Bug Severity | 2 | low | 018 | planned |

## Risks and Dependencies

- False green: skipped jobs counted as passed; `FEAT-020` must fail closed
- Workflows triggered by untrusted input; least privilege and pinned actions required
- External feature dependencies: `FEAT-007`, `FEAT-008`, `FEAT-009`, `FEAT-011`, `FEAT-012`, `FEAT-013`, `FEAT-014`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- A required check that is skipped or missing makes the gate fail
- A derived repository that still contains `template-dev/` fails validation
- All §21.6 issue test cases pass
