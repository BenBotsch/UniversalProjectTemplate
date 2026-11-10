---
id: "FEAT-019"
title: "Implement Pull Request Validation and Commit Convention Checks"
epic: "EPIC-06"
phase: 2
status: "implemented"
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

- [x] **T1:** Commit message parser with tests.
- [x] **T2:** PR validator rules with tests.
- [x] **T3:** Workflow file and local run instructions.

## Acceptance Criteria

- [x] Pull-request metadata is checked (§17.4).
- [x] Conventional Commit/PR-title rules are checked (§17.4).
- [x] §21.6: `feature/*` → `main` fails; `develop` → `main` passes; invalid title fails.

## Verification

```text
python -I -m pytest tests/ci/pr_validation
actionlint .github/workflows/pr-validation.yml
```

## Agent Notes

- **Allowed paths:** `scripts/ci/pr_validation/**`, `tests/ci/pr_validation/**`, `.github/workflows/pr-validation.yml`, `workflow.yml` rule section + schema, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Dependabot PRs have their own title format; allow `build(deps):`/`ci(deps):` via configuration rather than special-casing in code.

## Implementation Notes

- `scripts/ci/pr_validation/validator.py` has two commands, `pull-request` and `commits`, one per
  job of `.github/workflows/pr-validation.yml`. Both read the event file; local runs pass the
  values directly (`scripts/ci/README.md`). Only commit IDs validated as hexadecimal are passed to
  `git`; output quotes untrusted values with `repr`.
- R2 deviation: the target matrix comes from `workflow.yml` `branch_types` (`feature`, `fix`,
  `chore`, `hotfix`, `release`). The listed `docs/*`, `refactor/*` and `ci/*` branch types are not
  configured; `branching-and-releases.md` already routes that work to `chore/`. A project adds
  them in `workflow.yml`. `develop` → `main` and `main` → `develop` are always allowed.
- `workflow.yml` moved to schema `1.1` with the required fields `pull_requests.required_sections`
  and `pull_requests.automation_authors` (`dependabot[bot]`). The migration note is in
  `.project/README.md`; schema `1.0` stays valid and the validator falls back to defaults.
- Branch names without an issue number pass when the description has `No-Issue: <reason>`, as
  `branching-and-releases.md` describes. The pull request template, `CONTRIBUTING.md` and
  `agent-workflow.md` now name `No-Issue: <reason>` as the exception format.
- A required section fails when it is missing, empty or equal to the template text after removing
  HTML comments, blank lines and code fence markers. An unchanged, unticked Validation checklist
  therefore fails.
- Merge commits are skipped by `commitlint`; their messages are generated by Git or GitHub.
- `quality-gates.yml`: `pull_request_validation` and `conventional_commits` are `implemented`;
  `documentation` stays `not_implemented`.
- Verified on GitHub: on PR #4 (develop → main) `pr-validation` and `commitlint` passed in run
  42825449146 after the description was updated to the template; the earlier description
  without `No-Issue:` and the template sections fails the same rules locally.
