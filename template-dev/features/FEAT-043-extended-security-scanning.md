---
id: "FEAT-043"
title: "Add CodeQL, Dependency Review and OpenSSF Scorecard"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "medium"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§10.2", "§11.1", "§11.5", "§14.4", "§17.5"]
dependencies: ["FEAT-017"]
blocked_by_decisions: ["DEC-07"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-043: Add CodeQL, Dependency Review and OpenSSF Scorecard

## Objective

The `security-scan` job set adds SAST (CodeQL or alternative), dependency review on PRs and a
scheduled OpenSSF Scorecard run, enabled according to what the plan and visibility allow.

## Background

§11.1 code (CodeQL or alternative SAST per stack and plan), dependencies (SCA), §11.5 Scorecard
results are hints, not guarantees. §14.4 no "compliant by configuration". Blocked by `DEC-07`
(which checks for private Free repositories).

## Scope

- Workflows `codeql.yml`, `dependency-review` job, `scorecard.yml`; capability matrix document.

### Out of Scope

- Container scanning (`FEAT-036`), secret scanning (`FEAT-017`).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/codeql.yml` | Languages from active profiles; schedule weekly |
| `.github/workflows/security.yml` (job) | `dependency-review` on PRs |
| `.github/workflows/scorecard.yml` | Scheduled; results as SARIF |
| `docs/governance/security-policy.md` (section) | Capability matrix: public / private Free / paid, with fallback tools per `DEC-07` |

## Requirements

1. **R1:** If a scanner is unavailable for the repository, the job reports "not available on this plan" in the summary and the evaluator treats it as not applicable with that reason.
2. **R2:** Critical SAST findings fail the `security_scan` gate.
3. **R3:** Scorecard never blocks merges; it informs.
4. **R4:** Minimal permissions per job (`security-events: write` only where uploading SARIF).

## Tasks

- [ ] **T1:** Capability matrix per `DEC-07`.
- [ ] **T2:** CodeQL and dependency review.
- [ ] **T3:** Scorecard.

## Acceptance Criteria

- [ ] Code scanning is configured where available, with documented gaps (§17.5).
- [ ] A test PR adding a dependency with a known critical CVE fails dependency review.

## Verification

```text
actionlint .github/workflows/codeql.yml .github/workflows/scorecard.yml
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** resolving `DEC-07`; enabling code scanning in repository settings.
- **Pitfalls:** Dependency review needs the dependency graph; on private repos it may require GitHub Advanced Security.
