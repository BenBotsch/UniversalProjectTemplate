---
id: "FEAT-019"
title: "Implement Pull Request Validation and Commit Convention Checks"
epic: "EPIC-06"
phase: 2
status: "planned"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§8.3", "§8.4", "§8.5", "§9.1", "§9.2", "§10.2", "§21.6"]
dependencies: ["FEAT-011", "FEAT-012", "FEAT-014"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-019: Implement Pull Request Validation and Commit Convention Checks

## Objective

Pull requests are checked for Conventional-Commit title, issue link, correct target branch, branch
name and non-empty required template sections; commits in the PR follow Conventional Commits.

## Background

§8.5 lists the PR checks, §8.3 branch naming, §9.1/§9.2 commit syntax and breaking changes, §10.2
jobs `pr-validation` and `commitlint`, §21.6 cases (feature PR against `main` → policy error; release
PR `develop` → `main` allowed; invalid title → failure).

## Scope

- Validator library and workflow `pr-validation.yml` with jobs `pr-validation` and `commitlint`.
- Rules configurable from `.project/workflow.yml`.

### Out of Scope

- Required reviews (`FEAT-027`). Squash-vs-merge semantics (`DEC-02`): commitlint checks all PR commits; if squash is chosen, the PR title is the decisive check.

## Deliverables

| Path | Description |
|---|---|
| `scripts/ci/pr_validation/validator.py` | Title regex, issue-link detection (`Refs:`, `Closes`, `Fixes`, or `No-Issue: <reason>`), target-branch matrix, branch-name regex, empty-section detection |
| `scripts/ci/pr_validation/commits.py` | Conventional Commits 1.0.0 parser incl. `!` and `BREAKING CHANGE:` footer |
| `.github/workflows/pr-validation.yml` | `on: pull_request [opened, edited, synchronize, reopened]`; `permissions: contents: read, pull-requests: read` |
| `tests/ci/pr_validation/**` | §21.6 PR cases and parser edge cases |

## Requirements

1. **R1:** Allowed types from `workflow.yml` (default `feat, fix, refactor, perf, docs, test, build, ci, chore`).
2. **R2:** Target matrix: `feature/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`, `ci/*` → `develop`; `hotfix/*` → `main`; `release/*` and `develop` → `main`. Others fail.
3. **R3:** Template sections Summary, Related Issues, Validation, Tests Executed must not be empty or unchanged placeholder text.
4. **R4:** PR text is read from the event file, never interpolated into shell.
5. **R5:** Error output lists each failed rule with a fix hint.
6. **R6:** Changes under `.github/workflows/`, `.project/`, `SECURITY.md` add a job-summary notice "elevated review required" (§8.5).

## Tasks

- [ ] **T1:** Commit message parser with tests.
- [ ] **T2:** PR validator rules with tests.
- [ ] **T3:** Workflow file and local run instructions.

## Acceptance Criteria

- [ ] Pull-request metadata is checked (§17.4).
- [ ] Conventional Commit/PR-title rules are checked (§17.4).
- [ ] §21.6: `feature/*` → `main` fails; `develop` → `main` passes; invalid title fails.

## Verification

```text
python -I -m pytest tests/ci/pr_validation
actionlint .github/workflows/pr-validation.yml
```

## Agent Notes

- **Allowed paths:** `scripts/ci/pr_validation/**`, `tests/ci/pr_validation/**`, `.github/workflows/pr-validation.yml`, `workflow.yml` rule section + schema, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Dependabot PRs have their own title format; allow `build(deps):`/`ci(deps):` via configuration rather than special-casing in code.
