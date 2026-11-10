---
id: "FEAT-014"
title: "Add JSON Schemas and Project Configuration Validator"
epic: "EPIC-05"
phase: 1
status: "implemented"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§4.4", "§10.6", "§19"]
dependencies: ["FEAT-008", "FEAT-013"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-014: Add JSON Schemas and Project Configuration Validator

## Objective

Every `.project/*.yml` file has a versioned JSON Schema, and `scripts/ci/validate_project.py`
validates them locally and in CI with clear error messages.

## Background

§4.4 recommends JSON Schema for YAML, a local `validate` CLI, PR validation, versioned schemas and
migrations. §10.6 names `scripts/ci/validate_project.py` as a planned implementation.

## Scope

- Schemas for `project.yml`, `labels.yml`, `quality-gates.yml`, `workflow.yml`, `bootstrap.yml`.
- Validator script with tests.

### Out of Scope

- Repository file checks and placeholder detection (`FEAT-015`).

## Deliverables

| Path | Description |
|---|---|
| `.project/schemas/*.schema.json` | JSON Schema draft 2020-12, one per file, `$id` includes schema version |
| `scripts/ci/validate_project.py` | Loads each file, selects schema by `schema_version`, reports `file:path: message`; exit code 0/1 |
| `scripts/ci/requirements.txt` | Exists since `FEAT-008` with pinned `pytest` and `pyyaml`; add pinned `jsonschema` (hashes when the security baseline in `FEAT-017` requires them) |
| `tests/ci/test_validate_project.py` | Valid fixtures pass; invalid fixtures fail with expected messages |
| `tests/ci/fixtures/**` | Valid and invalid config samples |

## Requirements

1. **R1:** Unknown top-level fields are rejected; extension fields are allowed only under an explicit `x_extensions` key (§4.4).
2. **R2:** Enums are enforced (status, visibility, label groups, branch names format).
3. **R3:** Cross-file checks: every label used in `workflow.yml` `issue_policy` groups exists in `labels.yml`; `development_branch` != `default_branch`.
4. **R4:** Missing file, YAML syntax error, unknown `schema_version` each produce a distinct error message and exit code 1.
5. **R5:** Python standard library plus `pyyaml` and `jsonschema` only; runs with `python -I`.
6. **R6:** Untrusted file content is never executed or passed to a shell.

## Tasks

- [x] **T1:** Write schemas for all five files.
- [x] **T2:** Implement `validate_project.py` with cross-file checks.
- [x] **T3:** Add tests and fixtures (valid, unknown field, bad enum, missing file, bad version).

## Acceptance Criteria

- [x] Default project metadata is schema-validated (§17.1).
- [x] CI fails with a clear error on invalid metadata (§17.6).
- [x] All tests pass.

## Verification

```text
python -I -m pip install -r scripts/ci/requirements.txt
python -I scripts/ci/validate_project.py
python -I -m pytest tests/ci/test_validate_project.py
```

## Agent Notes

- **Allowed paths:** `.project/schemas/**`, `scripts/ci/validate_project.py`, `scripts/ci/requirements.txt`, `tests/ci/**`, this feature file, backlog status.
- **Requires approval:** adding dependencies beyond `pyyaml`, `jsonschema`, `pytest`.
- **Pitfalls:** Schema changes need a version bump and a migration note (§4.4, `FEAT-046`).

## Implementation Notes

- Negative test on 2026-11-10 (issue #1, draft pull request #2, CI run 42813310865): the pull
  request set `project.status` to `unknown-status`. `repository-validation` failed; the log shows
  `error: .project/project.yml:project.status: 'unknown-status' is not one of ['planning',
  'active', 'maintenance', 'archived']`. The pull request was closed without merging.
