---
id: "EPIC-05"
title: "Project Configuration and Schemas"
phase: 1
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-05: Project Configuration and Schemas

## Goal and Value

Machine-readable project metadata in `.project/` with JSON Schemas and a validator, including the template-only mechanism (`template_only_paths`, `is_template`).

## Scope and Deliverables

- `.project/project.yml`, `workflow.yml`, `quality-gates.yml`, `bootstrap.yml` (§4.1-§4.3, §13.5)
- JSON Schemas and `validate_project.py` (§4.4)

## Non-Goals

- Bootstrap commands that consume the config (EPIC-07)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-013](../features/FEAT-013-project-configuration-files.md) | Create Machine-Readable Project Configuration Files | 1 | critical | 001 | implemented |
| [FEAT-014](../features/FEAT-014-config-schemas-and-validator.md) | Add JSON Schemas and Project Configuration Validator | 1 | critical | 008, 013 | implemented |

## Risks and Dependencies

- Schema drift between config and consumers; every consumer validates first
- Breaking schema changes without `schema_version` bump (handled by `FEAT-046`)
- External feature dependencies: `FEAT-001`, `FEAT-008`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- All `.project/` files validate against their schemas in CI
- `template_only_paths` contains `template-dev/` and `is_template: true` is set in the template
