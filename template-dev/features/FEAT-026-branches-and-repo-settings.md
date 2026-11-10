---
id: "FEAT-026"
title: "Configure Branches and Repository Settings"
epic: "EPIC-07"
phase: 2
status: "implemented"
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

- [x] **T1:** Branch resource with tests.
- [x] **T2:** Settings resource with tests and schema section.

## Acceptance Criteria

- [x] `main` and `develop` are created and configured (§17.1).
- [x] Re-run produces only `noop`.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources
project-bootstrap configure-repo --repo <test-owner>/upt-smoke --dry-run
```

## Agent Notes

- **Allowed paths:** the two resources, their tests, `bootstrap.yml` section and schema, this feature file, backlog status.
- **Requires approval:** `--apply` against real repositories.
- **Pitfalls:** Secret scanning on private repos needs GitHub Advanced Security; report, do not fail.

## Implementation Notes

- **Files outside the allowed paths, approved through the design questions:** the section is
  `repository_settings` in `bootstrap-1.1.schema.json` (not `repository.settings`), and
  `.project/bootstrap.yml` moves to `1.1`; `configure-repo` wiring in `cli.py`; the fake repository
  in `tests/conftest.py`; CLI tests in `tests/test_cli.py`; schema tests in
  `tests/ci/test_validate_project.py`; field and migration rows in `.project/README.md`; a section
  in the package README.
- **Test location:** the package keeps a flat `tests/` directory, so the tests are in
  `tests/test_branches.py`, `tests/test_repo_settings.py` and `tests/test_cli.py`.
- **Design:** branch names, description and `is_template` come from `project.yml`, the merge
  methods from `workflow.yml` `merge_strategy`, everything else from `repository_settings`, so no
  value has two sources. `develop` is created from the head of `main` only when it is missing; an
  existing branch is never moved, and a `422` from a parallel run keeps the existing branch. The
  merge methods are written in one request, so the repository never has none. Actions use an
  allow-list (`selected`, GitHub-owned actions plus `patterns_allowed`) and a read-only workflow
  token. A placeholder description is skipped. `is_template` is only reported, because marking a
  repository as template is a human decision. Secret scanning on a private repository without
  Secret Protection or Advanced Security, and private vulnerability reporting on a non-public
  repository, are `skipped` with a reason (R3). A token without admin access fails before any
  write. R4 is met by the required `merge_strategy` value while `DEC-02` is open.
- **Limits:** code scanning is out of scope (`FEAT-043`); the squash commit title and message
  settings are not managed; organization policies that reject a setting are reported as `failed`.
  The allow-list must list every third-party action a workflow uses, or CI stops; no check covers
  that yet.
- **Verification (2026-11-10):** package tests 130 passed, `ruff check` and `ruff format --check`
  clean; `tests/ci` 310 passed; `validate_project.py`, `validate_repository.py`,
  `check_labels.py`, the backlog verifier, yamllint, actionlint, zizmor, markdownlint, gitleaks
  and a relative link check clean. On GitHub, CI run 42854236693 for 102f727 on `develop` passed,
  including `bootstrap-tool` and `quality-gate`.
- **Live run against the private `BenBotsch/upt-smoke-2` (approved: `--apply`):** the dry run
  planned 6 `update`, 7 `noop` and 6 `skipped`, 0 `failed`; the apply applied the 6 updates
  (auto-delete of head branches, rebase merges off, Actions allow-list, Dependabot alerts and
  security updates); a second dry run reported 13 `noop` and 6 `skipped`. `gh api` confirmed the
  values. Skipped were the placeholder description, `is_template`, the unset topics, secret
  scanning and push protection (no Secret Protection) and private vulnerability reporting
  (private repository). `develop` already existed, so branch creation was verified only against
  the fake repository.
