---
id: "FEAT-031"
title: "Define Technology Profile Mechanism"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "high"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§1.3", "§3.3", "§4.1", "§10.1", "§10.3", "§13.2", "§16.2"]
dependencies: ["FEAT-016", "FEAT-020", "FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
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

- [ ] **T1:** Manifest schema and README.
- [ ] **T2:** Profile resource in bootstrap.
- [ ] **T3:** CI integration pattern and example "noop" profile used by tests.

## Acceptance Criteria

- [ ] The template does not assume a single programming language (§17.1).
- [ ] An example profile can be applied, re-applied and validated in tests.

## Verification

```text
python -I scripts/ci/validate_project.py
python -m pytest tools/engineering-bootstrap/tests/resources/test_profiles.py
```

## Agent Notes

- **Allowed paths:** `profiles/**`, profile resource and tests, `project.yml` field and schema, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Avoid hidden coupling: profiles must not edit base workflows, only add their own job files or reusable-workflow calls.
