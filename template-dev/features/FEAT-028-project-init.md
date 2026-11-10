---
id: "FEAT-028"
title: "Initialize Derived Project and Remove Template-Only Content"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "critical"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§2.2", "§11.4", "§13.2", "§13.4", "§17.1", "§19"]
dependencies: ["FEAT-002", "FEAT-007", "FEAT-013", "FEAT-015", "FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-028: Initialize Derived Project and Remove Template-Only Content

## Objective

`project-bootstrap init` turns a freshly created repository into a project: replaces
placeholders, sets license, CODEOWNERS and contact links, deletes all `template_only_paths`
(including `template-dev/`), sets `project.is_template: false`, and commits the result through a PR.

## Background

§13.2 lists what bootstrap must personalize. §19: unreplaced placeholders are a known pitfall.
Template-only rule: GitHub copies every file, so the template backlog in `template-dev/` would end up
in every derived project unless bootstrap removes it.

## Scope

- `InitResource` working on a local clone or via the contents API.
- Changes delivered as one branch `chore/<issue>-project-init` and PR to `develop`, or as direct
  commit on first init when `develop` has no protection yet (configurable).

### Out of Scope

- Stack profiles (`FEAT-031`).

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/resources/init.py` | Steps below, each a separate change entry in the report |
| `.project/bootstrap.yml` (section) | `init.values` (project name, description, owner, team, license id, contact URLs), `template_only_paths` |
| `tests/resources/test_init.py` | Fixture template tree in a temp dir |

## Requirements

1. **R1:** Replaces `placeholder_tokens` (from `FEAT-015`) in all tracked text files outside `template_only_paths`.
2. **R2:** Writes `LICENSE` from the configured SPDX id; no license if `license: none` and README states "All rights reserved".
3. **R3:** Sets `.github/CODEOWNERS` owner and issue `config.yml` contact links.
4. **R4 (template-only cleanup):** Deletes every path in `bootstrap.template_only_paths`. Dry-run lists each path. Missing paths are `noop`, not errors.
5. **R5:** Sets `project.is_template: false` and `template.source`/`template.version` in `project.yml`.
6. **R6:** After changes, runs `validate_repository.py` (`FEAT-015`) and fails if any `REPO-PLACEHOLDER` or `REPO-TEMPLATE-ONLY` finding remains.
7. **R7:** JSON report lists replaced files, removed paths, and validation result.
8. **R8:** Never runs against a repository whose `project.yml` has `is_template: true` and the same name as `template.source`, to prevent wiping the template itself.

## Tasks

- [ ] **T1:** Placeholder replacement with tests.
- [ ] **T2:** License, CODEOWNERS, contact links.
- [ ] **T3:** Template-only cleanup, `is_template` flip, self-protection (R8).
- [ ] **T4:** Post-init validation and PR creation.

## Acceptance Criteria

- [ ] Template placeholders are replaced before production use (§17.1).
- [ ] After `init`, `template-dev/` does not exist and `validate_repository.py` passes.
- [ ] `init` twice: second run is all `noop`, no error for already removed paths.
- [ ] `init` against the template repository itself is refused.

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources/test_init.py
project-bootstrap init --repo <test-owner>/upt-smoke --dry-run --format json
```

## Agent Notes

- **Allowed paths:** init resource, tests, `bootstrap.yml` section and schema, this feature file, backlog status.
- **Requires approval:** `--apply` (deletes files in a real repository); choosing a license.
- **Pitfalls:** Replacing `OWNER` naively hits words like "OWNERSHIP"; match whole tokens.
