---
id: "FEAT-051"
title: "Audit All Repositories of an Owner"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "medium"
effort: "m"
target_repo: "engineering-bootstrap"
spec_refs: ["§13.7", "§13.8", "§15.4"]
dependencies: ["FEAT-029"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-051: Audit All Repositories of an Owner

## Objective

`project-bootstrap audit --owner OWNER` runs the single-repo audit across all repositories derived
from the template and writes one aggregated report.

## Background

§13.7 proposes `audit --owner OWNER`. §13.8 Phase D: central management of all repositories and
dashboard connection. §15.4 health score per repository.

## Scope

- Discovery of derived repos (by `.project/project.yml` `template.source` or topic), aggregation,
  JSON output for the dashboard.

### Out of Scope

- Fixing drift automatically across repos.

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/commands/audit_owner.py` | Discovery, parallel audit with rate-limit budget, aggregation |
| `schemas/audit-report.schema.json` | Versioned report schema consumed by `FEAT-052` |
| `tests/commands/test_audit_owner.py` | Mixed repos, archived repos skipped, permission errors per repo |

## Requirements

1. **R1:** Read-only; no write calls.
2. **R2:** Per-repo failures are recorded and do not abort the run.
3. **R3:** Archived and non-derived repos are excluded unless `--include-all`.
4. **R4:** Security-critical findings are listed separately (§15.4).

## Tasks

- [ ] **T1:** Discovery and aggregation.
- [ ] **T2:** Report schema and tests.

## Acceptance Criteria

- [ ] An owner with three test repos yields one report with three entries and correct scores.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/commands/test_audit_owner.py
project-bootstrap audit --owner <test-owner> --format json
```

## Agent Notes

- **Allowed paths:** command module, schema, tests, this feature file, backlog status.
- **Requires approval:** none (read-only).
- **Pitfalls:** Watch secondary rate limits when auditing many repos in parallel.
