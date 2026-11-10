---
id: "EPIC-01"
title: "Repository Foundation"
phase: 1
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-01: Repository Foundation

## Goal and Value

Provide the language-agnostic skeleton every derived project starts from: hygiene files, root community and policy files, and a documentation scaffold with an ADR process. Value: any new repository is immediately understandable and consistent.

## Scope and Deliverables

- Directory skeleton, `.editorconfig`, `.gitattributes`, `.gitignore` (§3)
- README, CONTRIBUTING, SECURITY, SUPPORT, CHANGELOG (§21.2, §21.3, §11.4)
- `docs/` scaffold for derived projects, governance set, ADR template and ADR-0001 (§12, §21.4)

## Non-Goals

- Choosing a license for derived projects (done per project by `FEAT-028`)
- Technology-specific files (EPIC-08)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-001](../features/FEAT-001-repository-skeleton.md) | Create Repository Skeleton and Hygiene Files | 1 | critical | - | implemented |
| [FEAT-002](../features/FEAT-002-root-community-files.md) | Write Root Community and Policy Files | 1 | critical | 001 | implemented |
| [FEAT-003](../features/FEAT-003-docs-scaffold-and-adr.md) | Create Documentation Scaffold, Index and ADR Process | 1 | high | 001 | implemented |

## Risks and Dependencies

- Over-filled scaffold that derived projects must delete; keep files minimal
- Accidental links from `docs/` to `template-dev/` (dead links in derived repos)
- External feature dependencies: none
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- A repository created from the template contains every root file of §21.2
- `docs/INDEX.md` links resolve and contain no template-dev references
- Repository validation (`FEAT-015`) reports no missing required file
