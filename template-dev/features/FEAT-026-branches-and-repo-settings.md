---
id: "FEAT-026"
title: "Configure Branches and Repository Settings"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "high"
effort: "m"
target_repo: "engineering-bootstrap"
spec_refs: ["§8.1", "§13.2", "§13.4", "§14.1", "§14.4"]
dependencies: ["FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-026: Configure Branches and Repository Settings

## Objective

`project-bootstrap configure-repo` creates `develop`, sets the default branch, merge methods,
auto-delete of head branches and security features from `.project/bootstrap.yml`.

## Background

§8.1 branch model, §13.2 steps 4-5, §13.4 `develop` from `main`, §14.1 repository settings table
(description, topics, default branch, issues/discussions/wiki, auto-delete branches, merge methods,
restrictive Actions permissions, read-only workflow token, Dependabot, secret/code scanning,
private vulnerability reporting), §14.4 plan-dependent features.

## Scope

- `BranchResource` and `RepoSettingsResource`.

### Out of Scope

- Rulesets (`FEAT-027`).

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/resources/branches.py` | Ensure `develop` exists from `main`; never force-update an existing branch |
| `src/engineering_bootstrap/resources/repo_settings.py` | Settings from §14.1, read and diff against `bootstrap.yml` |
| `.project/bootstrap.yml` (section) | `repository.settings` with defaults from §14.1, schema update |
| `tests/resources/test_branches.py`, `test_repo_settings.py` | Mocked API cases |

## Requirements

1. **R1:** Existing `develop` is left unchanged (no reset to `main`).
2. **R2:** Default branch stays `main` unless configured.
3. **R3:** Features unavailable for the plan/visibility are reported as `skipped` with reason, not failed.
4. **R4:** Merge methods follow `DEC-02` default once decided; until then config value is required.

## Tasks

- [ ] **T1:** Branch resource with tests.
- [ ] **T2:** Settings resource with tests and schema section.

## Acceptance Criteria

- [ ] `main` and `develop` are created and configured (§17.1).
- [ ] Re-run produces only `noop`.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources
project-bootstrap configure-repo --repo <test-owner>/upt-smoke --dry-run
```

## Agent Notes

- **Allowed paths:** the two resources, their tests, `bootstrap.yml` section and schema, this feature file, backlog status.
- **Requires approval:** `--apply` against real repositories.
- **Pitfalls:** Secret scanning on private repos needs GitHub Advanced Security; report, do not fail.
