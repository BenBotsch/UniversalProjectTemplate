---
id: "FEAT-025"
title: "Implement Idempotent Label Synchronization"
epic: "EPIC-07"
phase: 2
status: "implemented"
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

- [x] **T1:** Resource with diff and tests.
- [x] **T2:** Rename via aliases; prune with safety prompt in text mode.

## Acceptance Criteria

- [x] Labels can be created from the central label definition (§17.1).
- [x] §21.6 "label already exists" yields no error and updates color/description.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources/test_labels.py
project-bootstrap sync-labels --repo <test-owner>/upt-smoke --dry-run
```

## Agent Notes

- **Allowed paths:** label resource, its tests, this feature file, backlog status.
- **Requires approval:** `--apply --prune` against any real repository.
- **Pitfalls:** GitHub label names are case-insensitive but case-preserving; compare normalized.

## Implementation Notes

- **Files outside the allowed paths, approved before the work:** `labels-1.1.schema.json` with
  optional per-label `aliases`; `.project/labels.yml` moves to `1.1` and maps `bug` →
  `type:bug`, `enhancement` → `type:feature`, `documentation` → `type:documentation`;
  `scripts/ci/check_labels.py` accepts `1.0` and `1.1` and checks that aliases are unique and do
  not collide with label names; tests in `tests/ci/`; migration row in `.project/README.md`; rename
  note in `docs/governance/issue-management.md`. The CLI wiring in `cli.py` and the package README
  are part of the command.
- **Test location:** the package keeps a flat `tests/` directory, so the tests are in
  `tests/test_labels.py` and `tests/test_cli.py`; the fake GitHub (labels, pagination, search) is a
  fixture in `tests/conftest.py`.
- **Design:** names are matched case-insensitively; a missing label is renamed from the first
  unmatched alias (`PATCH` with `new_name`), otherwise created. A `POST` that answers 422 falls back
  to `PATCH`, which covers §21.6 and parallel runs. Unknown labels are `skipped` without `--prune`;
  an alias whose target already exists is reported as such. `--prune` requires `--apply`, lists
  every deletion with its usage on standard error and needs `--yes` or a `y` on a terminal;
  otherwise the run exits with `2` and changes nothing. `--repo` is checked against an
  `OWNER/NAME` pattern before any request.
- **Limits:** usage counts come from `/search/issues` `total_count`, include pull requests and can
  lag; names with `"` get an unknown count. `bootstrap.synchronize_labels` does not gate the
  explicit command. The PowerShell bootstrap script ignores `aliases`.
- **Verification (2026-11-10):** package tests 98 passed, `ruff check` and `ruff format --check`
  clean; `tests/ci` 305 passed; `validate_project.py`, `validate_repository.py`,
  `check_labels.py`, yamllint, actionlint, markdownlint, gitleaks and the link check clean. On
  GitHub, CI run 42845006858 for ba7ca1f on `develop` passed: `bootstrap-tool` ran the 98 tests
  and both ruff checks, and `quality-gate` reported `bootstrap_tool` as passed.
- **Live run against `BenBotsch/upt-smoke-2` (approved: `--apply` without `--prune`):** dry run,
  apply and second dry run each reported 34 `noop` and 10 `skipped` (GitHub default labels; `bug`,
  `enhancement` and `documentation` as aliases of existing labels), 0 `failed`, 0 changes
  applied. The repository already had all configured labels, so create, update and rename were
  verified only against the fake GitHub. `--prune` was not run against a real repository.
