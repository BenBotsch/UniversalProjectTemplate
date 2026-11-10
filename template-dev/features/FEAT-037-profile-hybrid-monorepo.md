---
id: "FEAT-037"
title: "Support Hybrid and Monorepo Profile Composition"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "low"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.1", "§10.7"]
dependencies: ["FEAT-032", "FEAT-033"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-037: Support Hybrid and Monorepo Profile Composition

## Objective

Several profiles can be applied to subdirectories of one repository; CI runs each profile only when
its paths change, while the quality-gate evaluator still prevents false green.

## Background

§3.3 names hybrid/monorepo setups; §10.7 forbids green-by-skip. Path filtering is the main risk.

## Scope

- Profile instance field `path:` in `project.yml`; CI change detection per instance.

### Out of Scope

- Build-graph tools (Bazel, Nx).

## Deliverables

| Path | Description |
|---|---|
| `.project/project.yml` (field) | `profiles: [{id, version, path}]` + schema update |
| `scripts/ci/detect_changes.py` | Outputs which profile instances are affected by a diff |
| `profiles/README.md` (section) | Monorepo usage and example layout `services/api` (python) + `native/core` (cpp) |
| `tests/ci/test_detect_changes.py` | Change in one path, shared root file triggers all, no change |

## Requirements

1. **R1:** Change in shared files (`.project/`, root workflows) marks all instances affected.
2. **R2:** The evaluator treats non-affected instances as "not applicable" with reason, affected ones as required.
3. **R3:** Two instances of the same profile in different paths are supported.

## Tasks

- [ ] **T1:** Schema field and resource support for `path`.
- [ ] **T2:** Change detection with tests.
- [ ] **T3:** Example and docs.

## Acceptance Criteria

- [ ] A Python + C++ fixture repo runs only affected jobs and the `quality-gate` job reflects the result correctly.

## Verification

```text
python -I -m pytest tests/ci/test_detect_changes.py
```

## Agent Notes

- **Allowed paths:** files listed in Deliverables, profile resource changes, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** On push to `main`, run all instances; path filtering is for PRs only.
