---
id: "FEAT-020"
title: "Enforce Quality Gates Without False Green Pipelines"
epic: "EPIC-06"
phase: 2
status: "implemented"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§4.3", "§9.6", "§10.7", "§10.9", "§17.4", "§21.6"]
dependencies: ["FEAT-013", "FEAT-016"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-020: Enforce Quality Gates Without False Green Pipelines

## Objective

A final `quality-gate` job evaluates `quality-gates.yml` against the actual job results and fails
when a required gate was skipped, missing or not implemented.

## Background

§4.3: `required_when_applicable` must not turn into a successful "skipped". §10.7: missing test
definitions are configuration errors once tests are required; never declare required jobs green
without running them. §21.6: "required build not executed → CI failure".

## Scope

- Evaluator script and a `quality-gate` job that `needs:` all gate jobs with `if: always()`.
- Applicability detection (e.g. code changes present, profile active).

### Out of Scope

- Stack-specific jobs themselves (`EPIC-08`).

## Deliverables

| Path | Description |
|---|---|
| `scripts/ci/evaluate_quality_gates.py` | Inputs: `quality-gates.yml`, JSON of `needs` results, changed paths, active profiles; output: table and exit code |
| `.github/workflows/ci.yml` (job) | `quality-gate` job, the single required status check for rulesets |
| `docs/governance/quality-model.md` | §10.9: quality derived from ISO/IEC 25010:2023 characteristics, project-specific measurable gates, coverage is not the only quality proof |
| `tests/ci/test_evaluate_quality_gates.py` | Required+skipped fails; not-applicable+skipped passes with reason; `not_implemented`+required fails |

## Requirements

1. **R1:** A required gate passes only with result `success`.
2. **R2:** A `*_when_applicable` gate that is applicable must have `success`; if not applicable, the reason is printed in the job summary.
3. **R3:** A gate marked `not_implemented` and required fails with "gate X is required but not implemented".
4. **R4:** Applicability rules are declared in `quality-gates.yml`, not hard-coded.
5. **R5:** The job summary lists every gate with status and reason, the commit SHA and the run id (§10.7: results bound to SHA and run).
6. **R6:** Tests marked flaky are tracked in a list in `quality-gates.yml` with an issue reference; a flaky test may be quarantined but never silently skipped (§10.7).

## Tasks

- [x] **T1:** Evaluator with tests.
- [x] **T2:** Wire `quality-gate` job into `ci.yml`; document it as the required check.

## Acceptance Criteria

- [x] Required checks cannot silently succeed without executing required work (§17.4).
- [x] §21.6 "required build not executed" yields CI failure.

## Verification

```text
python -I -m pytest tests/ci/test_evaluate_quality_gates.py
# Test PR: disable a required job via if: false; quality-gate must fail.
```

## Agent Notes

- **Allowed paths:** evaluator, tests, `ci.yml` job, `quality-gates.yml` + schema, `docs/governance/quality-model.md`, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Jobs skipped by path filters appear as "skipped" and also satisfy GitHub required checks; that is exactly why this aggregator job is the required check.

## Implementation Notes

- Architecture (ADR-0003, user decision): `quality.yml`, `security.yml` and `pr-validation.yml`
  became reusable workflows called from `ci.yml`, so all gate jobs run in one workflow run.
  `quality-gate` (`needs:` all jobs, `if: always()`, `actions: read`) reads the job list of its
  run attempt through the Actions API instead of `needs` results, because `needs` only exposes
  the caller jobs, not the jobs inside a called workflow. Called jobs are named
  `<caller> / <job>`; the evaluator resolves names from the workflow files.
- `quality-gates.yml` moved to schema `1.1`: `applies_when` (events, languages, changed paths,
  ignored paths; R4) and `flaky_tests` (R6). The evaluator accepts only `1.1`;
  `validate_project.py` still accepts `1.0`. Migration note in `.project/README.md`.
- "Active profiles" are approximated by `project.yml` `technology.languages` until technology
  profiles exist (`EPIC-08`); `languages: ["*"]` means any declared language.
- Decisions taken during implementation: review gates (`documentation`) print a notice and never
  fail; a failed job without a gate also fails the evaluation; CI also runs on `edited` pull
  requests so that a corrected description re-runs the validation; unknown changed files (first
  push) make every path-dependent gate apply; new gates for yaml, markdown and link lint and
  action pinning were added for jobs that already existed.
- `pr-validation.yml` now runs only for pull requests into `main` or `develop`, through `ci.yml`.
- Local checks: `pytest tests/ci` (294 passed), ruff check and format, yamllint `--strict`,
  actionlint, zizmor offline, markdownlint, validators, gitleaks.
- GitHub verification (2026-11-10): push run 42832904413 on `develop` passed; called jobs appear
  as `quality / workflow-lint` etc., and non-applicable gates are listed with their reason.
  Negative test pull request #5 (closed, not merged) disabled the required `yaml-lint` job:
  run 42833894099 skipped only `quality / yaml-lint`, and `quality-gate` failed with
  "job result: skipped". A first attempt with `if: false` also failed `workflow-lint`, because
  actionlint rejects constant conditions; the final run used a non-constant condition.
- The rulesets that make `quality-gate` the required check are not configured: this private
  repository on GitHub Free has no rulesets or branch protection. Bootstrap sets them (`FEAT-027`).
