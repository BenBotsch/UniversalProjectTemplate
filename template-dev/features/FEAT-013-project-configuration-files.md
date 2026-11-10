---
id: "FEAT-013"
title: "Create Machine-Readable Project Configuration Files"
epic: "EPIC-05"
phase: 1
status: "implemented"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§4.1", "§4.2", "§4.3", "§13.5", "§16.5", "§21.5"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-013: Create Machine-Readable Project Configuration Files

## Objective

`.project/` contains `project.yml`, `quality-gates.yml`, `workflow.yml` and `bootstrap.yml` with
versioned schemas, including the template-only mechanism that keeps `template-dev/` out of derived
repositories.

## Background

These files are a project convention, not native GitHub files (§4.1); they become effective only
through bootstrap, validators and dashboard. §4.2 assigns content per file, §4.3 shows quality gates,
§13.5 bootstrap options, §21.5 the issue policy, §16.5 template versioning.

## Scope

- Four YAML files (labels are `FEAT-008`).
- Template-only mechanism: `is_template`, `template_only_paths`.
- Template provenance fields for later upgrades (`FEAT-046`).

### Out of Scope

- JSON Schemas and validation code (`FEAT-014`).

## Deliverables

| Path | Description |
|---|---|
| `.project/project.yml` | §4.1 plus `project.is_template: true` (template) and `template: {source: "OWNER/universal-project-template", version: "0.1.0"}` |
| `.project/quality-gates.yml` | §4.3; each gate additionally names the CI job id that implements it |
| `.project/workflow.yml` | Branch model, PR rules (target branches, title convention, issue link), release approval, `issue_policy` from §21.5 |
| `.project/bootstrap.yml` | §13.5 plus `template_only_paths: ["template-dev/"]` and `dry_run_default: true`, `overwrite_user_changes: false` |
| `.project/README.md` | Purpose of each file, "not native GitHub configuration", who updates what (§21.1) |

## Requirements

1. **R1:** Every file starts with `schema_version: "1.0"`.
2. **R2:** `project.is_template` is `true` in the template and is set to `false` by bootstrap (`FEAT-028`).
3. **R3:** `template_only_paths` lists `template-dev/`; repository validation (`FEAT-015`) fails in a repo with `is_template: false` when any listed path exists.
4. **R4:** Every quality gate in `quality-gates.yml` maps to a named CI job id or is explicitly marked `not_implemented` (so `FEAT-020` can fail on it, §4.3 note).
5. **R5:** Enum values are documented in `.project/README.md` (status, visibility, versioning, commit_convention).
6. **R6:** Placeholder values use the `PROJECT_NAME`/`PROJECT_DESCRIPTION`/`OWNER` tokens.

## Tasks

- [x] **T1:** Write `project.yml` and `.project/README.md`.
- [x] **T2:** Write `quality-gates.yml` and `workflow.yml`.
- [x] **T3:** Write `bootstrap.yml` with template-only fields.

## Acceptance Criteria

- [x] Default project metadata is initialized (§17.1); schema validation follows in `FEAT-014`.
- [x] `template_only_paths` and `is_template` are defined and documented.
- [x] All files parse as YAML.

## Verification

```text
python -I -c "import sys,yaml;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .project/*.yml
```

## Agent Notes

- **Allowed paths:** `.project/project.yml`, `.project/quality-gates.yml`, `.project/workflow.yml`, `.project/bootstrap.yml`, `.project/README.md`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** §19: YAML is not effective by itself; avoid fields no tool will read. `required_when_applicable` must not become a green "skipped" (§4.3).
