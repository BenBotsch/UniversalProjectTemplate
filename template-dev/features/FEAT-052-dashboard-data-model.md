---
id: "FEAT-052"
title: "Define Dashboard Data Model and Export"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "medium"
effort: "m"
target_repo: "dashboard"
spec_refs: ["§2.4", "§15.3", "§15.4"]
dependencies: ["FEAT-013", "FEAT-051"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-052: Define Dashboard Data Model and Export

## Objective

A versioned JSON data model covers the eight categories of §15.3 per repository, and an exporter
produces it from `.project/` files, the audit report and the GitHub API.

## Background

§15.3 categories: Identity, Work Items, Delivery, CI/CD, Security, Docs, Agents, Scripts. §2.4 the
dashboard is a later goal; the template must already provide machine-readable data. §15.4 health
score.

## Scope

- JSON Schema for the model; exporter command; sample data.

### Out of Scope

- UI (`FEAT-053`), script execution (`FEAT-054`).

## Deliverables

| Path | Description |
|---|---|
| `dashboard/schemas/repository-snapshot.schema.json` | Eight categories, `snapshot_version`, `generated_at`, source references |
| `dashboard/exporter/export.py` | Builds snapshots from `audit --owner` output plus API queries |
| `dashboard/samples/*.json` | Valid sample snapshots used by UI tests |
| `dashboard/README.md` | Data sources per field, refresh strategy |

## Requirements

1. **R1:** Every field names its source (config, API, audit).
2. **R2:** No secrets or personal data beyond GitHub logins in snapshots.
3. **R3:** Scripts category lists only commands declared in `.project/` with their approval level; it never infers commands from files (§15.3).
4. **R4:** Schema changes bump `snapshot_version`.

## Tasks

- [ ] **T1:** Schema and samples.
- [ ] **T2:** Exporter with tests.

## Acceptance Criteria

- [ ] Samples validate against the schema; exporter output for a test owner validates too.

## Verification

```text
python -I -m pytest dashboard/exporter
```

## Agent Notes

- **Allowed paths:** `dashboard/**` (until a separate repo exists), this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Keep the model stable; the UI should not query GitHub directly in the MVP.
