---
id: "EPIC-08"
title: "Technology Profiles"
phase: 3
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-08: Technology Profiles

## Goal and Value

Add optional per-stack profiles on top of the universal base, and later extract them into versioned reusable workflows.

## Scope and Deliverables

- Profile mechanism (§3.3, §10.1)
- Python, C++/CMake/Conan, Node/TS, Flutter, Docker profiles (§10.3, §10.4)
- Hybrid and monorepo composition
- Reusable workflows in `engineering-workflows` (§10.5, §16.2, `DEC-08`)

## Non-Goals

- Release pipelines (EPIC-09)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-031](../features/FEAT-031-profile-mechanism.md) | Define Technology Profile Mechanism | 3 | high | 016, 020, 024 | planned |
| [FEAT-032](../features/FEAT-032-profile-python.md) | Add Python Profile | 3 | high | 031 | planned |
| [FEAT-033](../features/FEAT-033-profile-cpp-cmake-conan.md) | Add C++ Profile with CMake and Conan | 3 | medium | 031 | planned |
| [FEAT-034](../features/FEAT-034-profile-node-typescript.md) | Add Node.js and TypeScript Profile | 3 | medium | 031 | planned |
| [FEAT-035](../features/FEAT-035-profile-flutter-dart.md) | Add Flutter and Dart Profile | 3 | low | 031 | planned |
| [FEAT-036](../features/FEAT-036-profile-docker.md) | Add Docker and Container Profile | 3 | medium | 031 | planned |
| [FEAT-037](../features/FEAT-037-profile-hybrid-monorepo.md) | Support Hybrid and Monorepo Profile Composition | 3 | low | 032, 033 | planned |
| [FEAT-038](../features/FEAT-038-reusable-workflows.md) | Extract Versioned Reusable Workflows | 3 | medium | 031, 032 | planned |
| [FEAT-055](../features/FEAT-055-shared-figure-style.md) | Offer the Shared Figure Style in the Python Profile | 3 | low | 032 | planned |

## Risks and Dependencies

- Profiles that report green without running tools (§10.7)
- Extracting reusable workflows too early (`DEC-08`)
- External feature dependencies: `FEAT-016`, `FEAT-020`, `FEAT-024`
- Blocking decisions: `DEC-08` (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- Each profile has an example project with verified lint, test and build jobs
