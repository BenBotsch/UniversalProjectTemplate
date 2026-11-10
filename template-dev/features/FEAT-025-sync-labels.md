---
id: "FEAT-025"
title: "Implement Idempotent Label Synchronization"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "high"
effort: "s"
target_repo: "engineering-bootstrap"
spec_refs: ["§6.4", "§13.3", "§13.6", "§13.7", "§21.6"]
dependencies: ["FEAT-008", "FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-025: Implement Idempotent Label Synchronization

## Objective

`project-bootstrap sync-labels` makes the repository labels match `.project/labels.yml`:
create missing, update color/description, report (and optionally delete) unknown labels.

## Background

§6.4 label definitions, §13.7 command `sync-labels`, §13.3 (copying labels alone is no conformance
check), §13.6 idempotency, §21.6 "label already exists → no error".
Deleting labels removes them from issues, so it must be opt-in.

## Scope

- `LabelResource` for the CLI engine; rename support via `aliases` in `labels.yml`.

### Out of Scope

- Org-level labels.

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/resources/labels.py` | Diff by name (case-insensitive), color, description; `aliases` → rename instead of create |
| `tests/resources/test_labels.py` | Create, update, noop, rename, unknown-label report, `--prune` |

## Requirements

1. **R1:** Without `--prune`, unknown labels are only reported.
2. **R2:** `--prune` requires `--apply` and lists labels plus affected issue counts before deleting.
3. **R3:** Second run reports only `noop`.
4. **R4:** Default GitHub labels (`bug`, `enhancement`, ...) are mapped via `aliases` or reported as unknown.

## Tasks

- [ ] **T1:** Resource with diff and tests.
- [ ] **T2:** Rename via aliases; prune with safety prompt in text mode.

## Acceptance Criteria

- [ ] Labels can be created from the central label definition (§17.1).
- [ ] §21.6 "label already exists" yields no error and updates color/description.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources/test_labels.py
project-bootstrap sync-labels --repo <test-owner>/upt-smoke --dry-run
```

## Agent Notes

- **Allowed paths:** label resource, its tests, this feature file, backlog status.
- **Requires approval:** `--apply --prune` against any real repository.
- **Pitfalls:** GitHub label names are case-insensitive but case-preserving; compare normalized.
