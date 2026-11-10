---
id: "ADR-0003"
title: "Aggregate CI Results in a Single Quality Gate Job"
status: "accepted"
created_at: "2026-11-10"
related_issues: []
---

# ADR-0003: Aggregate CI Results in a Single Quality Gate Job

## Context

The quality gates in `.project/quality-gates.yml` are implemented by jobs in several workflows:
`ci.yml`, `quality.yml`, `security.yml` and `pr-validation.yml`. Making each job a required
status check has two problems:

- GitHub treats a job that was skipped by an `if:` condition or a path filter as passed, so a
  required check can be green although its work never ran.
- Jobs that apply only to some changes, such as tests for code changes or pull request
  validation, cannot be required checks without blocking the changes they do not apply to.

A job can only read the results of jobs in the same workflow run through `needs:`. The results
of separately triggered workflows are not available to it without polling the API.

## Decision

`quality.yml`, `pr-validation.yml` and `security.yml` are reusable workflows
(`on: workflow_call`). `ci.yml` calls them, so every gate job runs in the same workflow run.
`security.yml` keeps its schedule and manual triggers.

The final `quality-gate` job in `ci.yml` needs all other jobs and runs with `if: always()`. It
reads the job results of the run from the Actions API and evaluates them with
`scripts/ci/evaluate_quality_gates.py` against `quality-gates.yml`. Its applicability rules
(`applies_when`) are declared in that file, not in the evaluator. `quality-gate` is the only
required status check.

## Alternatives Considered

- **Every job as a required check:** a skipped job counts as passed, and conditional jobs block
  unrelated changes. This is the problem the decision solves.
- **Separate workflows and an aggregator triggered by `workflow_run`:** the aggregator runs in the
  context of the default branch, reports its status on a different run than the pull request
  checks, and must wait for several workflows to finish.
- **One workflow file with all jobs:** has the same effect but makes a large file, and the
  scheduled security scan would need its own conditions inside the pull request workflow.

## Consequences

- Rulesets and branch protection require only `quality-gate`. Adding, renaming or removing a gate
  job changes `quality-gates.yml`, not the repository settings.
- Jobs of called workflows are shown as `<caller job> / <job>`, for example
  `quality / workflow-lint`. The evaluator resolves these names from the workflow files.
- `quality-gate` needs `actions: read` to list the jobs of its run.
- The called workflows have no own `pull_request` or `push` triggers; they run only through
  `ci.yml`, or, for `security.yml`, on its schedule.
- Because CI also runs on edited pull requests, a change to the title or description re-runs all
  jobs, not only the pull request validation.
- Technology profiles add their jobs to `ci.yml` and to `quality-gates.yml`; a failed job without
  a gate also fails the quality gate.
