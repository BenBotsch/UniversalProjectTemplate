---
id: "FEAT-015"
title: "Implement Repository Validator with Placeholder and Template-Only Checks"
epic: "EPIC-06"
phase: 2
status: "implemented"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.1", "§10.2", "§10.6", "§10.7", "§17.1", "§19"]
dependencies: ["FEAT-014"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-015: Implement Repository Validator with Placeholder and Template-Only Checks

## Objective

`scripts/ci/validate_repository.py` checks required files, leftover template placeholders, and the
absence of template-only paths in derived repositories.

## Background

§10.2 job `repository-validation` checks structure, configuration and mandatory files. §10.6 names
`validate_repository.py`. §19 requires mandatory validation of placeholders (`OWNER`,
`PROJECT_NAME`, ...). The template-only rule keeps `template-dev/` out of derived repositories.

## Scope

- Required-file check, placeholder check, template-only check, issue-form/label consistency
  (reuses `FEAT-007` T4 check if present).

### Out of Scope

- Config schema validation (`FEAT-014`, called as a library or separate job).

## Deliverables

| Path | Description |
|---|---|
| `scripts/ci/validate_repository.py` | Checks below; output lines `RULE-ID file: message`; JSON output with `--format json` |
| `.project/workflow.yml` (section) | `repository_validation.required_files`, `placeholder_tokens` and `docs_index_severity` |
| `tests/ci/test_validate_repository.py` | Fixture repos in temp dirs |

## Requirements

1. **R1 (REPO-REQUIRED):** Fails if any `required_files` entry is missing (default: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `.project/project.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/config.yml`).
2. **R2 (REPO-PLACEHOLDER):** If `project.is_template` is `false`, fails on any `placeholder_tokens` match (`PROJECT_NAME`, `PROJECT_DESCRIPTION`, `OWNER/REPOSITORY`, `@OWNER_OR_TEAM`, `OWNER/`) in tracked text files, excluding `template-dev/` and an allowlist.
3. **R3 (REPO-TEMPLATE-ONLY):** If `project.is_template` is `false`, fails when any path in `bootstrap.template_only_paths` exists. If `true`, the check passes and prints "template repository: template-only paths allowed".
4. **R4 (REPO-DEAD-LINK-TEMPLATE):** Fails if any file outside `template_only_paths` links to a template-only path, in both modes.
5. **R5:** Only tracked files are scanned (`git ls-files`), invoked without shell interpolation.
6. **R6:** Exit code 1 on any failure; each failure names its rule ID.
7. **R7 (REPO-DOCS-INDEX):** Every Markdown file under `docs/` (except `README.md` and `_template.md` files) is linked from `docs/INDEX.md`, and every relative link in `docs/INDEX.md` resolves. Severity is `warning` or `error` per `repository_validation.docs_index_severity` (default `error`) (§21.6 stale index case).

## Tasks

- [x] **T1:** Required-file and template-only checks with tests.
- [x] **T2:** Placeholder and dead-link checks with tests.
- [x] **T3:** JSON output mode for later use by `FEAT-029` and the dashboard.
- [x] **T4:** Docs-index check with tests.

## Acceptance Criteria

- [x] Template repository (`is_template: true`) passes.
- [x] Fixture "derived repo still contains `template-dev/`" fails with `REPO-TEMPLATE-ONLY`.
- [x] Fixture "derived repo with `PROJECT_NAME` in README" fails with `REPO-PLACEHOLDER`.
- [x] Fixture "README links to `template-dev/backlog.md`" fails with `REPO-DEAD-LINK-TEMPLATE`.
- [x] Fixture "new `docs/governance/x.md` not in `docs/INDEX.md`" fails with `REPO-DOCS-INDEX`.
- [x] Template placeholders are replaced before production use: enforced by this check (§17.1).

## Verification

```text
python -I scripts/ci/validate_repository.py
python -I -m pytest tests/ci/test_validate_repository.py
```

## Agent Notes

- **Allowed paths:** `scripts/ci/validate_repository.py`, `tests/ci/**`, the `workflow.yml` section and its schema in `.project/schemas/`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** `OWNER/` also occurs in legitimate docs examples; use the allowlist rather than weakening the token list.

## Implementation Notes

- `repository_validation.placeholder_allowlist` (glob patterns) holds the allowlist from R2; it
  covers files that document or test the tokens themselves.
- The `repository_validation` section was added to the existing `workflow-1.0` schema as an
  optional property, so existing configuration files stay valid.
- CI enforcement of the check follows with `FEAT-016`.
- `CONTRIBUTING.md` and `.project/README.md` were updated per the documentation policy.
