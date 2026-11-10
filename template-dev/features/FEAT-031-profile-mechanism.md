---
id: "FEAT-031"
title: "Define Technology Profile Mechanism"
epic: "EPIC-08"
phase: 3
status: "implemented"
priority: "high"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§1.3", "§3.3", "§4.1", "§10.1", "§10.3", "§13.2", "§16.2"]
dependencies: ["FEAT-016", "FEAT-020", "FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: ["#22"]
created_at: "2026-11-10"
updated_at: "2026-11-11"
---

# FEAT-031: Define Technology Profile Mechanism

## Objective

A profile is a versioned bundle of files, CI jobs, quality-gate applicability rules and Dependabot
ecosystems. Projects select profiles in `project.yml`; bootstrap applies them; CI activates only
the jobs of selected profiles.

## Background

§1.3: the template must not pretend a stack exists. §3.3 lists profiles as optional extensions.
§10.1 separates the universal base layer from the stack layer, §10.3 lists the tools per stack.
§13.2 step 7 installs CI profiles during bootstrap. §16.2 later moves profile workflows into
`engineering-workflows` (`FEAT-038`).

## Scope

- Profile manifest format and schema; `profiles/` directory; `project-bootstrap apply-profile`.
- CI wiring pattern: a profile adds jobs that report into the `quality-gate` aggregator.

### Out of Scope

- Concrete profiles (`FEAT-032` to `FEAT-037`).

## Deliverables

| Path | Description |
|---|---|
| `profiles/README.md` | What a profile is, lifecycle, how to add one |
| `profiles/_schema/profile.schema.json` | Manifest: `id`, `version`, `files[]`, `ci_jobs[]`, `quality_gates{}`, `dependabot[]`, `labels[]` (extra `area:*`), `requires_profiles[]` |
| `.project/project.yml` (field) | `profiles: [{id, version}]` + schema update |
| `src/engineering_bootstrap/resources/profiles.py` | Copies files, merges gates and Dependabot entries, never overwrites user-modified files without `--force` |
| `tests/resources/test_profiles.py` | Apply, re-apply (noop), conflict, removal reported |

## Requirements

1. **R1:** A repository without profiles stays valid and CI green on the base layer.
2. **R2:** Applying a profile is idempotent; re-apply yields `noop`.
3. **R3:** Files changed by the user since apply are reported as conflict, not overwritten.
4. **R4:** Every profile CI job maps to a gate in `quality-gates.yml`; the evaluator (`FEAT-020`) knows its applicability rule.
5. **R5:** Profile version is recorded in `project.yml` for later upgrades (`FEAT-046`).

## Tasks

- [x] **T1:** Manifest schema and README.
- [x] **T2:** Profile resource in bootstrap.
- [x] **T3:** CI integration pattern and example "noop" profile used by tests.

## Acceptance Criteria

- [x] The template does not assume a single programming language (§17.1).
- [x] An example profile can be applied, re-applied and validated in tests.

## Verification

```text
python -I scripts/ci/validate_project.py
python -m pytest tools/engineering-bootstrap/tests/resources/test_profiles.py
```

## Agent Notes

- **Allowed paths:** `profiles/**`, profile resource and tests, `project.yml` field and schema, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Avoid hidden coupling: profiles must not edit base workflows, only add their own job files or reusable-workflow calls.

## Implementation Notes

- The design is recorded in ADR-0006 (`proposed`). The manifest schema is
  `profiles/_schema/profile.schema.json`, and `profiles/README.md` describes the layout, the rules
  and how to add a profile (T1). `profiles/` is a template-only path.
- `project-bootstrap apply-profile --profile ID [--path DIR] [--source DIR] [--force]` and
  `init --profile ID` apply a profile through `ProfileResource` in
  `tools/engineering-bootstrap/src/engineering_bootstrap/resources/profiles.py` (T2). `init` loads
  the profile before `profiles/` is deleted and writes its files into the initialization commit.
- **Deviation from the pitfall "profiles must not edit base workflows":** `quality-gate` must wait
  for the profile jobs (ADR-0003), so a profile inserts its job call and its `needs` entry above
  the anchors `# bootstrap:profile-jobs` and `# bootstrap:profile-needs` in `ci.yml`. The jobs
  themselves live in the profile's own workflow file. The same anchored blocks are used for
  `quality-gates.yml`, `dependabot.yml` and `labels.yml`. Each block is delimited by
  `# profile:<id>:start` and `# profile:<id>:end`, so it can be compared and removed by hand.
- R1: the base files carry only the anchor comments; without profiles CI is unchanged. R2: a
  second run plans only `noop`. R3: a changed file or block is `skipped` as a conflict, and a file
  deleted after the profile was recorded is not recreated; `--force` overrides both. R4:
  `load_profile` rejects a job of a profile workflow without a gate and a gate without a profile
  workflow. A profile gate can replace a generic base gate with `covers` (quality-gates schema
  1.2; `evaluate_quality_gates.py` and `validate_project.py` support it). R5: `project.yml` schema
  1.1 adds `profiles: [{id, version}]`.
- The noop profile used by the tests lives in `tools/engineering-bootstrap/tests/fixtures/profiles/noop/`
  rather than `profiles/`, so the template does not ship a profile without tooling (T3).
- **Deviation:** the tests are `tools/engineering-bootstrap/tests/test_profiles.py`, following
  the flat test layout of the package, instead of `tests/resources/test_profiles.py`.
- **Paths outside the allowed paths:** the anchors in `.github/workflows/ci.yml`,
  `.github/dependabot.yml`, `.project/labels.yml` and `.project/quality-gates.yml`; the
  quality-gates schema 1.2 with `scripts/ci/evaluate_quality_gates.py`,
  `scripts/ci/validate_project.py` and their tests; `.project/bootstrap.yml` and
  `.project/README.md`; `.yamllint.yml` (`comments-indentation` is disabled, because an anchor at
  the end of a list cannot match the indentation of the following content); the steps
  "Lint profile workflows" in `quality.yml` and "Check that profile actions are pinned" in
  `security.yml`; ADR-0006 and `docs/INDEX.md`; `init.py` (extra resources and list values) and
  the README of the bootstrap package.
- **Verification (local, Windows, Python 3.12):** 228 package tests, `ruff check` and
  `ruff format --check` in the package pass. `tests/ci` (445 tests), `validate_project.py`,
  `validate_repository.py`, `check_action_pinning.py`, actionlint, zizmor (offline),
  `yamllint --strict .` and markdownlint-cli2 on the changed Markdown files pass.
