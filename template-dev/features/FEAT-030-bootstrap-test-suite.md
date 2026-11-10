---
id: "FEAT-030"
title: "Build Bootstrap End-to-End Test Suite"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "high"
effort: "m"
target_repo: "engineering-bootstrap"
spec_refs: ["§13.8", "§17.1", "§17.6", "§21.6"]
dependencies: ["FEAT-025", "FEAT-026", "FEAT-027", "FEAT-028"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-030: Build Bootstrap End-to-End Test Suite

## Objective

An end-to-end suite proves bootstrap against mocked APIs on every PR and against a private and a
public test repository on demand, including the template-only regression cases.

## Background

§13.8 requires unit tests, API mocks and integration checks in a test repository. §17.6 requires one private and one
public test repository. §21.6 lists bootstrap cases (rerun, existing labels, missing permissions).

## Scope

- Mock-based E2E scenarios in CI; live scenarios as `workflow_dispatch` with a dedicated test owner.

### Out of Scope

- Load testing.

## Deliverables

| Path | Description |
|---|---|
| `tests/e2e/test_bootstrap_flow.py` | Full flow `init → sync-labels → configure-repo → apply-rulesets → audit` with mocks |
| `tests/e2e/fixtures/template_tree/` | Minimal template tree incl. `template-dev/` and placeholders |
| `.github/workflows/bootstrap-e2e.yml` | Mock suite on PR; live suite on `workflow_dispatch` only |
| `tests/e2e/README.md` | How to run live tests, required permissions, cleanup |

## Requirements

1. **R1:** Case "first run": all `create`, final audit clean.
2. **R2:** Case "second run": all `noop`.
3. **R3:** Case "labels already exist": no error, updates only.
4. **R4:** Case "missing permission (403)": clear error, non-zero exit, no partial claim of success.
5. **R5 (template-only):** Case "derived repo still contains `template-dev/`": `validate_repository.py` fails with `REPO-TEMPLATE-ONLY`.
6. **R6 (template-only):** Case "init twice": second run has no error for already removed `template-dev/`.
7. **R7:** Case "private Free plan": rulesets reported as `skipped`/`UNPROTECTED`, not failed silently.
8. **R8:** Live suite uses a short-lived credential from a protected environment; never runs on fork PRs.

## Tasks

- [ ] **T1:** Fixture tree and mock E2E flow.
- [ ] **T2:** Regression cases R3 to R7.
- [ ] **T3:** Live workflow and README.

## Acceptance Criteria

- [ ] Bootstrap tested against at least one private and one public test repository (§17.6).
- [ ] All cases R1 to R7 pass in the mock suite.

## Verification

```text
python -m pytest tests/e2e
# Live: gh workflow run bootstrap-e2e.yml (requires approval)
```

## Agent Notes

- **Allowed paths:** `tests/e2e/**`, `.github/workflows/bootstrap-e2e.yml`, this feature file, backlog status.
- **Requires approval:** creating test repositories and environment secrets; triggering the live run.
- **Pitfalls:** Clean up live test repos at the end or reuse fixed names to avoid clutter.
