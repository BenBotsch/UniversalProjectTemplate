---
id: "FEAT-032"
title: "Add Python Profile"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.1", "§10.2", "§10.3"]
dependencies: ["FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-032: Add Python Profile

## Objective

The `python` profile adds packaging, lint, format, type-check, test and coverage jobs for Python
projects, wired into the quality gates.

## Background

§3.3 names Python; §10.2 job catalog (build, unit tests, lint, format, type check, coverage);
§10.3 tool list (Ruff, mypy or pyright, pytest).

## Scope

- Profile manifest and files: `pyproject.toml` skeleton, `src/`, `tests/`, Ruff config, workflow job.

### Out of Scope

- Framework-specific settings (Django, FastAPI).

## Deliverables

| Path | Description |
|---|---|
| `profiles/python/profile.yml` | Manifest per `FEAT-031` |
| `profiles/python/files/pyproject.toml` | Project metadata placeholders, Ruff, mypy, pytest, coverage config |
| `profiles/python/files/.github/workflows/python.yml` | Jobs `python-lint`, `python-typecheck`, `python-test` (matrix of supported Python versions), least privilege, SHA-pinned |
| `profiles/python/files/src/PROJECT_PACKAGE/__init__.py`, `tests/test_smoke.py` | Minimal package with one passing test |
| `profiles/python/README.md` | Commands, gate mapping |

## Requirements

1. **R1:** Jobs map to gates `lint`, `format`, `type_check`, `unit_tests`, `coverage`.
2. **R2:** Coverage threshold configurable; default 80 % for new code is documented as a recommendation only.
3. **R3:** Dependabot ecosystem `pip` added via manifest.
4. **R4:** Applying the profile to an empty derived repo yields green CI.

## Tasks

- [ ] **T1:** Manifest and files.
- [ ] **T2:** Workflow job and gate mapping.
- [ ] **T3:** Test application in a fixture repo.

## Acceptance Criteria

- [ ] Python profile applies cleanly and its jobs pass on the skeleton.
- [ ] Removing the test file makes `unit_tests` fail via the evaluator, not silently skip.

## Verification

```text
ruff check . && ruff format --check . && mypy src && pytest --cov
```

## Agent Notes

- **Allowed paths:** `profiles/python/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Use `uv` or `pip` consistently; document the choice in the profile README.
