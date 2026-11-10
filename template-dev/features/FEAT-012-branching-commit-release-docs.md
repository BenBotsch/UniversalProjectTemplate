---
id: "FEAT-012"
title: "Document Branching, Commit and Release Conventions"
epic: "EPIC-04"
phase: 1
status: "implemented"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§8.1", "§8.2", "§8.3", "§8.5", "§8.7", "§9.1", "§9.2", "§9.3", "§9.4", "§9.6", "§21.4"]
dependencies: ["FEAT-003"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-012: Document Branching, Commit and Release Conventions

## Objective

Governance documents define the simplified GitFlow, branch naming, Conventional Commits, SemVer,
release criteria and review policy in one consistent place.

## Background

§8.1 branch model (`main`, `develop`, `feature/*`, `fix/*`, `hotfix/*`, `release/*`), §8.2 process,
§8.3 naming `<purpose>/<issue-number>-<summary>`, §8.7 protection table, §9 commits, SemVer (with
`0.x` note), release structure and approval criteria. §21.4 proposes the file names. Merge policy is
open (`DEC-02`); documents describe it as "to be decided" with the proposed default.

## Scope

- `development-workflow.md`, `branching-and-releases.md`, `commit-conventions.md`, `review-policy.md`.

### Out of Scope

- Automating version calculation (`FEAT-040`), rulesets (`FEAT-027`), hotfix runbook detail (`FEAT-044`).

## Deliverables

| Path | Description |
|---|---|
| `docs/governance/development-workflow.md` | §8.2 eleven-step process end to end |
| `docs/governance/branching-and-releases.md` | §8.1 table, §8.3 naming with regex, hotfix back-sync, §9.3 SemVer incl. `0.x`, §9.4 release structure, §9.6 release criteria, protection table §8.7 with plan caveat |
| `docs/governance/commit-conventions.md` | §9.1 syntax and types, scopes, `Refs:` vs `Closes`, §9.2 breaking changes, PR-title rule |
| `docs/governance/review-policy.md` | Review expectations, elevated attention for CI/secrets/permissions/release changes (§8.5), solo-developer rules (§14.3) |
| `docs/INDEX.md` | Lines under Governance |

## Requirements

1. **R1:** Branch name regex is given and identical to what `FEAT-019` will enforce: `^(feature|fix|hotfix|release|chore|docs|refactor|ci)/[0-9]+-[a-z0-9-]+$` plus `release/X.Y.Z` exception.
   *Implementation note:* the docs quote `branching.branch_name_pattern` from `.project/workflow.yml`
   (`FEAT-013`) verbatim, which allows `feature|fix|hotfix|chore` plus `release/X.Y.Z` and strict
   kebab-case. That file is the single source `FEAT-019` reads; widen it there if more prefixes are needed.
2. **R2:** The commit types list equals `AGENTS.md` (`FEAT-004`).
3. **R3:** The merge policy section references `DEC-02` and marks the default as provisional.
4. **R4:** Release criteria list all eight items of §9.6.
5. **R5:** States that `develop` is created from `main` in the derived repository (§2.5, §13.4).

## Tasks

- [x] **T1:** Write `commit-conventions.md`.
- [x] **T2:** Write `branching-and-releases.md`.
- [x] **T3:** Write `development-workflow.md` and `review-policy.md`; update `docs/INDEX.md`.

## Acceptance Criteria

- [x] A contributor can derive the branch name, commit message and PR target from the docs for a feature, a bugfix and a hotfix.
- [x] Docs and `AGENTS.md` agree on commit types and branch rules (manual cross-check recorded in the PR).

## Verification

```text
grep -n "feat, fix, refactor, perf, docs, test, build, ci, chore" docs/governance/commit-conventions.md AGENTS.md
```

## Agent Notes

- **Allowed paths:** the four files, `docs/INDEX.md` (lines), this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** §19: `main`/`develop` adds release sync complexity; Dependabot security PRs target the default branch and must be synced to `develop` (§10.8). Mention both.
