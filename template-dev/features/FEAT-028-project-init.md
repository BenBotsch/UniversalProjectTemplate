---
id: "FEAT-028"
title: "Initialize Derived Project and Remove Template-Only Content"
epic: "EPIC-07"
phase: 2
status: "implemented"
priority: "critical"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§2.2", "§11.4", "§13.2", "§13.4", "§17.1", "§19"]
dependencies: ["FEAT-002", "FEAT-007", "FEAT-013", "FEAT-015", "FEAT-024"]
blocked_by_decisions: []
agent_ready: true
related_issues: ["#14"]
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

- [x] **T1:** Placeholder replacement with tests.
- [x] **T2:** License, CODEOWNERS, contact links.
- [x] **T3:** Template-only cleanup, `is_template` flip, self-protection (R8).
- [x] **T4:** Post-init validation and PR creation.

## Acceptance Criteria

- [x] Template placeholders are replaced before production use (§17.1).
- [x] After `init`, `template-dev/` does not exist and `validate_repository.py` passes.
- [x] `init` twice: second run is all `noop`, no error for already removed paths.
- [x] `init` against the template repository itself is refused.

## Verification

```text
python -I -m pytest tools/engineering-bootstrap/tests/test_init.py
project-bootstrap init --repo <test-owner>/upt-smoke --dry-run --format json
```

## Agent Notes

- **Allowed paths:** init resource, tests, `bootstrap.yml` section and schema, this feature file, backlog status.
- **Requires approval:** `--apply` (deletes files in a real repository); choosing a license.
- **Pitfalls:** Replacing `OWNER` naively hits words like "OWNERSHIP"; match whole tokens.

## Implementation Notes

- **Decisions (issue #14):** `init` works only on a local clone; the contents API variant and the
  direct commit to `develop` are dropped. With `--apply --issue N` it creates
  `chore/N-project-init` from the development branch, writes, validates and commits, but never
  pushes; it prints the `git push` and `gh pr create` commands. Values come from the command line,
  then the new `init` section of `bootstrap.yml` (schema `1.3`: `license`, optional `code_owner`
  and `copyright_holder`), then the GitHub repository and the owner's profile. The license text
  comes from the GitHub licenses API. Template-only text inside kept files sits between
  `template-only:start` and `template-only:end` lines; the new rule `REPO-TEMPLATE-MARKER` reports
  markers left in a derived project.
- **Deviations:** `init.values` became `init` with only the values that GitHub does not provide;
  contact links (R3) are the `OWNER/REPOSITORY` placeholders of the issue `config.yml`. R5 does
  not write `template.version`, because no template release exists yet. R6 is stricter: any
  validation error, not only `REPO-PLACEHOLDER` and `REPO-TEMPLATE-ONLY`, stops the commit. R8
  also refuses a repository that is a template on GitHub and a clone whose `origin` does not
  match `--repo`.
- **Files outside the allowed paths:** `src/engineering_bootstrap/git.py` and the `init` wiring in
  `cli.py`; `REPO-TEMPLATE-MARKER` in `scripts/ci/validate_repository.py`; marker blocks and
  placeholders in `README.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS`,
  `.github/ISSUE_TEMPLATE/config.yml` and `scripts/bootstrap/`; tests in `tests/ci/` that assumed
  the template state; `.project/README.md` and the package README.
- **Test location:** the package keeps a flat `tests/` directory, so the tests are in
  `tests/test_init.py`. One test initializes a copy of the template working tree and runs the
  real `validate_repository.py`.
- **Local end-to-end run (2026-11-10):** a copy of the working tree with `origin` set to a fake
  `octo/demo` and a faked GitHub API: `--apply --issue 1` deleted `template-dev/` and
  `tools/engineering-bootstrap/`, updated 9 files and committed; validation reported no error or
  warning, `tests/ci` passed in the initialized project, and a second run planned no change.
  `init --repo BenBotsch/UniversalProjectTemplate` on the template checkout is refused with exit
  code `1`.
- **Limits and follow-ups:** a live run against `BenBotsch/upt-smoke-public` needs separate
  approval. `scripts/bootstrap/` stays in derived projects; it could become template-only. Stack
  profiles (`--profile`) are `FEAT-031`.
