---
id: "FEAT-032"
title: "Add Python Profile"
epic: "EPIC-08"
phase: 3
status: "active"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.1", "§10.2", "§10.3"]
dependencies: ["FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: ["#23"]
created_at: "2026-11-10"
updated_at: "2026-11-11"
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

- [x] **T1:** Manifest and files.
- [x] **T2:** Workflow job and gate mapping.
- [x] **T3:** Test application in a fixture repo.

## Acceptance Criteria

- [x] Python profile applies cleanly and its jobs pass on the skeleton.
- [x] Removing the test file makes `unit_tests` fail via the evaluator, not silently skip.

## Verification

```text
ruff check . && ruff format --check . && mypy src && pytest --cov
```

## Agent Notes

- **Allowed paths:** `profiles/python/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Use `uv` or `pip` consistently; document the choice in the profile README.

## Implementation Notes

- The profile is `profiles/python/` (T1). `profiles/python/README.md` documents the commands, the
  gate mapping and the choice of uv (pitfall). uv 0.13.5 is pinned in the shared setup action
  `.github/actions/python-setup/action.yml`. CI installs with `uv sync --locked` when `uv.lock`
  exists and warns otherwise.
- **Deviation in job names (T2):** the jobs of `python.yml` are `format`, `lint`, `type-check`,
  `test`, `build` and `audit`. `ci.yml` calls the workflow as job `python`, so GitHub reports them
  as `python / lint` and so on, and a `python-` prefix would repeat itself. `test` runs a matrix of
  Python 3.12 and 3.13. Its name is fixed, because the evaluator matches the matrix runs as
  `python / test (<version>)`.
- **Deviation in gates (R1):** the base layer has no gates `type_check`, `unit_tests` or
  `coverage`. The profile gates replace the generic base gates with `covers`:
  `python_formatting` covers `formatting`, `python_lint` covers `lint`, `python_tests` covers
  `tests`, `python_build` covers `build` and `python_security` covers `security`.
  `python_type_check` covers no base gate. Coverage is part of `python_tests`. The jobs `build`
  and `audit` go beyond the deliverables, so that no generic gate stays `not_implemented`.
- **Deviation (R2):** coverage is reported with `fail_under = 0`. The README and a comment in
  `pyproject.toml` recommend 80 %.
- **Deviation (R3):** the Dependabot ecosystem is `uv` instead of `pip`, because the profile uses
  `uv.lock`.
- Ruff, mypy and pytest exclude `scripts/ci/` and `tests/ci/`, which the base
  `repository-validation` job tests. The label `area:python` has the colour of the other `area`
  labels.
- **Tests (T3):** `tests/test_init.py` initializes a full template checkout with and without
  `--profile python` and expects no validation error. `tests/test_profiles.py` applies the profile
  to the template's base files and checks that every python gate resolves to a job of the CI run.
  While making these tests pass, two base tests that broke in derived projects were fixed in
  `FEAT-031`.
- **Verification (local, Windows, Python 3.12):** in a project initialized with the profile,
  `ruff format --check`, `ruff check`, `mypy`, `pytest --cov` (100 %), `uv build` and pip-audit
  ("No known vulnerabilities") pass, and so do actionlint, zizmor and `validate_project.py`.
  Without `tests/test_smoke.py`, pytest exits with 5, so the gate fails. R4 (green CI on GitHub)
  is not verified yet. It needs a derived repository on GitHub.
- **Open:** R4 needs a derived repository on GitHub, for example `BenBotsch/upt-smoke-public`,
  initialized with `--profile python`. The feature stays `active` until its CI is green there.
