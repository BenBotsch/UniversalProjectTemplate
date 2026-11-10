---
id: "EPIC-10"
title: "Template Lifecycle"
phase: 4
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-10: Template Lifecycle

## Goal and Value

Keep the template and its derived projects maintainable over time: versioning and migrations, an optional `.github` community repository, and migration of this seed backlog into GitHub Issues.

## Scope and Deliverables

- Template versioning and `upgrade` migrations (§16.5)
- Optional `.github` repository blueprint (§16.4)
- Seed backlog migration to Issues (§5.11, §12.5), phase 2

## Non-Goals

- Automatic synchronization of derived projects (§16.5 forbids it)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-046](../features/FEAT-046-template-versioning-and-migrations.md) | Version the Template and Provide Upgrade Migrations | 4 | medium | 013, 029, 031 | planned |
| [FEAT-047](../features/FEAT-047-community-health-repository.md) | Provide Optional .github Community Health Repository | 4 | low | 002 | planned |
| [FEAT-048](../features/FEAT-048-seed-backlog-migration.md) | Migrate Seed Backlog to GitHub Issues | 2 | high | 007, 008, 025 | planned |

## Risks and Dependencies

- Upgrades overwriting user changes
- Duplicate status between Markdown and Issues after migration
- External feature dependencies: `FEAT-002`, `FEAT-007`, `FEAT-008`, `FEAT-013`, `FEAT-025`, `FEAT-029`, `FEAT-031`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- A derived project upgrades via reviewable PR
- After `FEAT-048`, status lives only in GitHub Issues
