---
id: "FEAT-029"
title: "Implement Validate, Audit, Drift Detection and Health Score"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "medium"
effort: "m"
target_repo: "engineering-bootstrap"
spec_refs: ["§13.2", "§13.7", "§13.8", "§15.4", "§16.5"]
dependencies: ["FEAT-015", "FEAT-025", "FEAT-026", "FEAT-027"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-029: Implement Validate, Audit, Drift Detection and Health Score

## Objective

`project-bootstrap validate` checks local configuration; `audit` compares a live repository
against its configuration, reports drift per resource and computes a health score.

## Background

§13.7 commands `validate` and `audit`, §13.2 steps 10-11 (initial validation and result report),
§13.8 Phase C (CI drift check), §15.4 health-score checklist, §16.5 drift between template version
and repository.

## Scope

- `validate`: schema + repository validation without network.
- `audit`: all resources in read-only mode, plus health indicators.

### Out of Scope

- Multi-repo audit (`FEAT-051`).

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/commands/validate.py` | Calls `FEAT-014` and `FEAT-015` checks |
| `src/engineering_bootstrap/commands/audit.py` | Runs `diff()` of all resources; never writes |
| `src/engineering_bootstrap/health.py` | Weighted score 0-100 with documented weights; indicators from the §15.4 checklist |
| `docs/governance/health-score.md` | Indicator list, weights, thresholds |
| `tests/commands/**` | Drift fixtures, score calculation |

## Requirements

1. **R1:** `audit` performs no write calls (test asserts only GET requests).
2. **R2:** Each drift entry names resource, expected, actual, and the fixing command.
3. **R3:** Score weights are configuration, not code constants. Security-critical violations (unprotected release workflow, secrets findings, missing protection where supported) are listed separately and cap the score; many trivial passes cannot compensate them (§15.4).
4. **R4:** Template version drift: compares `template.version` with the latest template release, if reachable.

## Tasks

- [ ] **T1:** `validate` command.
- [ ] **T2:** `audit` command with drift report.
- [ ] **T3:** Health score and doc.

## Acceptance Criteria

- [ ] Bootstrap produces a final validation report (§17.1).
- [ ] A manually removed label shows as drift with the fix `sync-labels --apply`.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/commands
project-bootstrap audit --repo <test-owner>/upt-smoke --format json
```

## Agent Notes

- **Allowed paths:** command modules, `health.py`, tests, `docs/governance/health-score.md`, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** none (read-only).
- **Pitfalls:** Do not count `skipped` capability resources as drift.
