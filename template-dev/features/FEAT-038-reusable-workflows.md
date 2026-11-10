---
id: "FEAT-038"
title: "Extract Versioned Reusable Workflows"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "medium"
effort: "l"
target_repo: "engineering-workflows"
spec_refs: ["§10.5", "§16.1", "§16.2", "§16.3"]
dependencies: ["FEAT-031", "FEAT-032"]
blocked_by_decisions: ["DEC-08"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-038: Extract Versioned Reusable Workflows

## Objective

Base and profile CI jobs move into reusable workflows (`workflow_call`) in a central
`engineering-workflows` repository; projects call them pinned to a release tag or SHA, so fixes
propagate without copying.

## Background

§10.5 proposes `engineering-workflows` with `reusable-<stack>.yml` files used via `workflow_call`
and fixed, tested versions; permissions and trust boundaries are evaluated per call. §16.2 defines
the repository purpose. Blocked by `DEC-08` (extract early or after the first projects; proposed
default: after two real projects use the same profile).

## Scope

- Reusable workflows for the base layer and the Python profile as first example.
- Versioning and release process for the workflows repo.

### Out of Scope

- Migrating all profiles at once; each profile migrates in its own follow-up.

## Deliverables

| Path | Description |
|---|---|
| `engineering-workflows/.github/workflows/reusable-security.yml` | `on: workflow_call`, inputs for config paths, outputs gate results |
| `engineering-workflows/.github/workflows/reusable-python.yml` | Reusable Python jobs |
| `engineering-workflows/README.md` | Inputs, outputs, permissions, versioning (SemVer tags, major tag moves only on compatible changes) |
| Template `.github/workflows/ci.yml` (change) | Calls reusable workflow pinned by SHA with version comment |

## Requirements

1. **R1:** Callers pass only needed secrets explicitly; no `secrets: inherit`.
2. **R2:** Each reusable workflow declares minimal `permissions`.
3. **R3:** Breaking input changes require a major version.
4. **R4:** Template CI result is identical before and after extraction (same gates, same failures).

## Tasks

- [ ] **T1:** Repository skeleton and release process (after `DEC-08`).
- [ ] **T2:** Extract base validation.
- [ ] **T3:** Extract Python profile jobs.
- [ ] **T4:** Switch template to calls; compare results.

## Acceptance Criteria

- [ ] A breaking-change test PR to a reusable workflow is caught by version policy.
- [ ] Template CI passes when calling the reusable workflows.

## Verification

```text
actionlint
# Compare quality-gate summaries of a test PR before and after the switch.
```

## Agent Notes

- **Allowed paths:** new workflows repo (after `DEC-08`), template `ci.yml`, this feature file, backlog status.
- **Requires approval:** resolving `DEC-08`; creating the workflows repository.
- **Pitfalls:** Reusable workflows from private repos need access settings; document them.
