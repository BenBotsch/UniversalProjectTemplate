---
id: "FEAT-046"
title: "Version the Template and Provide Upgrade Migrations"
epic: "EPIC-10"
phase: 4
status: "planned"
priority: "medium"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§4.4", "§13.8", "§16.5", "§16.6"]
dependencies: ["FEAT-013", "FEAT-029", "FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-046: Version the Template and Provide Upgrade Migrations

## Objective

The template is released with SemVer tags. Derived projects record the template version they came
from. `project-bootstrap upgrade` proposes migrations to a newer template version as a reviewable PR.

## Background

§16.5: version the template, schemas and bootstrap separately; derived projects are not synchronized
automatically; offer upgrades through planned migrations, reviewable PRs and audit reports. §13.8
Phase C: versioned setup module and CI drift check. §4.4 schema versions.

## Scope

- Template release process (tag `vX.Y.Z` of the template repo, `TEMPLATE_CHANGELOG` section).
- Migration format and `upgrade` command.

### Out of Scope

- Automatic merging of upgrade PRs.

## Deliverables

| Path | Description |
|---|---|
| `migrations/README.md` | Format: one directory per target version with `migration.yml` (steps: add file, replace block, rename key, bump `schema_version`) |
| `migrations/0.2.0/migration.yml` | First real migration once a breaking template change exists (placeholder example in tests until then) |
| `src/engineering_bootstrap/commands/upgrade.py` | Reads `template.version`, applies the chain of migrations in dry-run, writes a branch and PR on `--apply` |
| `tests/commands/test_upgrade.py` | Chain of two migrations, conflict on user-modified file, already up to date |
| `docs/governance/template-versioning.md` | Template, schema, bootstrap and workflow versions; compatibility rules |

## Requirements

1. **R1:** Every schema change bumps `schema_version` and ships a migration.
2. **R2:** Upgrades never overwrite user-modified files; conflicts are listed in the PR body.
3. **R3:** `upgrade` updates `template.version` only after all steps succeed.
4. **R4:** `audit` (`FEAT-029`) reports "template version behind" with the upgrade command.
5. **R5:** Migrations are idempotent.

## Tasks

- [ ] **T1:** Versioning doc and template release steps.
- [ ] **T2:** Migration format and engine.
- [ ] **T3:** `upgrade` command with PR creation.

## Acceptance Criteria

- [ ] A fixture project at template `0.1.0` upgrades to a test version `0.2.0` via PR with all steps listed.
- [ ] A second `upgrade` run reports "up to date".

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/commands/test_upgrade.py
project-bootstrap upgrade --repo <test-owner>/upt-smoke --dry-run
```

## Agent Notes

- **Allowed paths:** `migrations/**`, upgrade command and tests, `docs/governance/template-versioning.md`, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** tagging a template release; `--apply` against real repositories.
- **Pitfalls:** The `migrations/` folder belongs to the template's tooling; decide whether it is template-only (add to `template_only_paths`) and record the decision in the doc.
