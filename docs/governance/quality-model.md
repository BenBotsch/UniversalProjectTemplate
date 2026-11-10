# Quality Model

This document explains how the project defines product quality and how CI enforces it. The
gates themselves are configured in [.project/quality-gates.yml](../../.project/quality-gates.yml);
this document does not repeat them.

## Reference Model

Quality requirements are derived from
[ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html), the reference model for software
product quality. It does not prescribe metrics or thresholds; each project selects the
characteristics that matter for its product and makes them measurable.

| Characteristic | Typical measurable evidence |
|---|---|
| Functional suitability | Acceptance criteria verified by tests or documented checks |
| Performance efficiency | Benchmarks or load tests with a stated budget |
| Compatibility | Tests on every documented supported platform and interface version |
| Interaction capability | Accessibility checks, usability reviews, documented user workflows |
| Reliability | Tests of failure paths, no untracked flaky tests, recovery procedures |
| Security | No unresolved critical findings from secret scanning, dependency and code analysis |
| Maintainability | Formatting, linting, type checks, tests that run on every change, reviewed architecture decisions |
| Flexibility | Documented supported platforms and configuration, reproducible builds |
| Safety | Hazard analysis and safeguards, where the product can cause harm |

A characteristic that does not apply to a project is left out deliberately and, if the choice is
not obvious, recorded in an ADR.

## Measurable Gates

A gate is a check with an unambiguous result, for example "no critical static analysis finding",
"all unit tests pass" or "supported platforms are documented". Each gate in
`quality-gates.yml` names the CI job that implements it and the conditions under which it
applies. Gates that cannot be decided by a tool, such as documentation completeness, are review
gates: CI reports that a review is required, and reviewers enforce them.

Code coverage is not proof of quality on its own. A coverage number shows which code ran, not
whether the tests check the right behavior. Use it to find untested code, combined with tests of
requirements, failure paths and edge cases, never as the only gate.

## Enforcement in CI

The `quality-gate` job in [ci.yml](../../.github/workflows/ci.yml) is the single required status
check. It runs after every other job, also when one of them failed, and compares the actual job
results of the run with `quality-gates.yml`:

| Situation | Result |
|---|---|
| The gate applies and its job finished with `success` | Passed |
| The gate applies and its job failed, was skipped, cancelled or did not run | Failed |
| The gate applies but is marked `not_implemented` | Failed: "gate X is required but not implemented" |
| The gate does not apply | Passed; the reason is shown in the job summary |
| A review gate applies | Notice "Review required"; never fails |
| A job without a gate failed | Failed |

A gate applies when all of its `applies_when` conditions hold: the event, the languages in
`project.yml` `technology.languages`, and the changed files. A gate without conditions always
applies. This is why individual jobs must not be required checks: GitHub treats a job skipped by
a condition or path filter as passed, while the quality gate treats it as failed when the gate
applies.

The job summary lists every gate with its job, result and reason, together with the commit SHA
and the run id, so that each result is bound to the commit and run that produced it. Run the
evaluation locally as described in [scripts/ci/README.md](../../scripts/ci/README.md#checks).

## Flaky Tests

A test that fails intermittently is tracked, stabilized and, if necessary, quarantined; it is
never disabled silently. A quarantined test is listed under `flaky_tests` in
`quality-gates.yml` with its tracking issue and the reason, and the job summary shows the list.
Remove the entry when the issue is resolved.
