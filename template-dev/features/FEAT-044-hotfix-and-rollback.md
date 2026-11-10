---
id: "FEAT-044"
title: "Define Hotfix, Back-Merge and Rollback Process"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "medium"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§8.1", "§8.2", "§9.6", "§10.8"]
dependencies: ["FEAT-012", "FEAT-041"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-044: Define Hotfix, Back-Merge and Rollback Process

## Objective

Hotfixes branch from `main`, release as a patch, and are merged back into `develop` automatically
proposed by a workflow; a rollback procedure exists for failed releases.

## Background

§8.1: `hotfix/*` from `main` to `main`, then synchronization to `develop`; `release/*` optionally
back to `develop`. §8.2 step 11. §9.6 requires a rollback/hotfix plan. §10.8 security PRs on `main`
also need back-merge.

## Scope

- Back-merge workflow that opens a PR `main` → `develop` after each push to `main`.
- Runbook for hotfix and rollback.

### Out of Scope

- Selectable branching strategies (§8.1 mentions them as a later option); recorded as a follow-up idea.

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/back-merge.yml` | On push to `main`: if `main` is ahead of `develop`, open or update PR `main` → `develop` titled `chore: back-merge main into develop` |
| `docs/governance/hotfix-and-rollback.md` | Hotfix steps, versioning (patch), rollback options (revert PR, re-release previous tag, yank artifact), communication |
| `tests/release/test_back_merge_logic.py` | If logic is in a script: ahead/not ahead, existing PR |

## Requirements

1. **R1:** The back-merge PR is never auto-merged; conflicts are left for a human.
2. **R2:** `permissions: contents: read, pull-requests: write`.
3. **R3:** Rollback never deletes or moves published tags without explicit approval.

## Tasks

- [ ] **T1:** Back-merge workflow.
- [ ] **T2:** Runbook and `docs/INDEX.md` line.

## Acceptance Criteria

- [ ] After a hotfix merge to `main`, a back-merge PR to `develop` appears in the test repository.
- [ ] Rollback/hotfix plan is available as required by §9.6.

## Verification

```text
actionlint .github/workflows/back-merge.yml
```

## Agent Notes

- **Allowed paths:** files listed above, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** testing on a real repository.
- **Pitfalls:** PRs created with `GITHUB_TOKEN` do not trigger CI; use a GitHub App token or document re-running checks.
