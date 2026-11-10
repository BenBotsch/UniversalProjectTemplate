# Project Configuration

The files in `.project/` describe the project in machine-readable form. They are a **project
convention, not native GitHub configuration**: GitHub ignores them. They take effect only through
the bootstrap tool, the CI validators and the dashboard. A field that no tool reads has no effect.

Every file starts with `schema_version`. The current version is `"1.1"` for `workflow.yml` and
`"1.0"` for all other files. A change to the structure of a file requires a new schema version
and a migration note; see [Migrations](#migrations).

## Schemas and Validation

Each file has a JSON Schema (draft 2020-12) in [`schemas/`](schemas/), named
`<file>-<schema_version>.schema.json`, for example `project-1.0.schema.json`. The validator
selects the schema by the `schema_version` of each file:

```text
python -I -m pip install -r scripts/ci/requirements.txt
python -I scripts/ci/validate_project.py
```

It reports each problem as `<file>:<path>: <message>` and exits with 1 if any file is missing,
has invalid YAML syntax, an unsupported `schema_version` or a schema violation. After the schema
check it applies the label rules of `scripts/ci/check_labels.py` and these cross-file checks:

- Every label group and every type and status value in `workflow.yml` `issue_policy` exists in
  `labels.yml`, and `initial_status` is one of `supported_states`.
- `development_branch` differs from `default_branch`.
- Every branch named in `workflow.yml` is the default or development branch of `project.yml`, and
  releases come from the default branch.
- `branch_name_pattern` and `tag_pattern` are valid regular expressions.

Unknown fields are rejected at every level. Project-specific data belongs under a top-level
`x_extensions` mapping, which every schema allows and template tooling ignores.

To change a structure, add a new schema file with the next version instead of editing the
existing one, update `schema_version` in the configuration file and document the migration.

## Files

| File | Content | Read by | Created by | Updated when |
|---|---|---|---|---|
| `project.yml` | Identity, template provenance, branches, versioning, technology, quality and agent flags | Bootstrap, validators, dashboard | Bootstrap | Stack, platform or policy changes |
| `labels.yml` | Label names, colors, descriptions and groups | Label synchronization, issue validation | Template owner | Taxonomy changes |
| `quality-gates.yml` | Required checks and the CI jobs that implement them | Quality-gate job in CI | Template owner | A CI job is added, renamed or removed |
| `workflow.yml` | Branch model, pull request rules, release approval, issue policy | Pull request and issue validators, bootstrap | Template owner | Branch, review or issue rules change |
| `bootstrap.yml` | Features to provision, safety defaults, template-only paths, profiles | Bootstrap | Template owner | Provisioning options change |

Label naming and color rules are documented in
[docs/governance/issue-management.md](../docs/governance/issue-management.md).

## Allowed values

### `project.yml`

| Field | Allowed values |
|---|---|
| `project.status` | `planning`, `active`, `maintenance`, `archived` |
| `project.visibility` | `private`, `internal`, `public` |
| `project.is_template` | `true` only in the template repository, `false` in every derived project |
| `repository.versioning` | `semver` |
| `repository.commit_convention` | `conventional-commits` |
| `technology.*` | Lists of lowercase identifiers, for example `python`, `cmake`, `windows`, `uv`; empty means not yet decided |

`template.source` is `OWNER/REPOSITORY` of the template a project was created from, and
`template.version` is the template version used at creation. Projects are not synchronized
automatically with later template versions; upgrades run as reviewed migrations.

### `quality-gates.yml`

| Field | Allowed values |
|---|---|
| Applicability key | `required`, `required_when_applicable`, `required_for_code_changes`, `review_required_for_relevant_changes`; each set to `true` |
| `workflow` | File name in `.github/workflows/` |
| `job` | Job id in that workflow |
| `status` | `implemented`, `not_implemented` |

A required gate passes only if its job finished with `success`. A skipped, missing or
`not_implemented` job fails the gate; it is never reported as green.

### `workflow.yml`

| Field | Allowed values |
|---|---|
| `branching.model` | `gitflow-simplified` |
| `branching.branch_types.*.source`, `targets`, `back_merge_to` | Branch names from `project.yml` (`default_branch`, `development_branch`) |
| `pull_requests.title_convention` | `conventional-commits` |
| `pull_requests.allowed_types` | Conventional Commit types |
| `pull_requests.merge_strategy.*` | `squash`, `merge`, `rebase` |
| `pull_requests.required_sections` | Headings of `.github/PULL_REQUEST_TEMPLATE.md` that must be filled in |
| `pull_requests.automation_authors` | Bot logins such as `dependabot[bot]`; their pull requests skip the branch name, issue link and section checks |
| `issue_policy.initial_status` | A value from `issue_policy.supported_states` |
| `issue_policy.*_label_groups`, `required_for_ready` | Group names from `labels.yml` |
| `repository_validation.required_files`, `placeholder_allowlist` | Paths relative to the repository root; the allowlist takes glob patterns |
| `repository_validation.placeholder_tokens` | Literal tokens; a match inside a longer identifier is ignored |
| `repository_validation.docs_index_severity` | `error` (default), `warning` |

### `bootstrap.yml`

| Field | Allowed values |
|---|---|
| Feature switches (`create_develop_branch`, `synchronize_labels`, ...) | `true`, `false` |
| `dry_run_default` | `true` shows planned changes only; apply must be requested explicitly |
| `overwrite_user_changes` | `false` keeps files and settings a project has changed |
| `template_only_paths` | Paths relative to the repository root that exist only in the template |
| `optional_profiles` | `python`, `cpp`, `node`, `flutter`, `docker`, `hybrid` |

## Template-only content

The template repository contains content that must not reach derived projects. Two fields
control this:

- `project.is_template` in `project.yml` is `true` in the template. Bootstrap sets it to `false`
  when it initializes a derived project.
- `template_only_paths` in `bootstrap.yml` lists the paths that exist only in the template.
  Bootstrap removes them during initialization. Repository validation fails if one of these paths
  exists while `is_template` is `false`.

## Placeholders

Values that bootstrap replaces during initialization use these tokens: `PROJECT_NAME`,
`PROJECT_DESCRIPTION` and `OWNER`. Repository validation reports tokens that remain in a derived
project.

Repository validation (`python -I scripts/ci/validate_repository.py`) reports each check with a
rule ID: `REPO-REQUIRED`, `REPO-PLACEHOLDER`, `REPO-TEMPLATE-ONLY`, `REPO-DEAD-LINK-TEMPLATE`,
`REPO-DOCS-INDEX`, `REPO-ISSUE-FORMS` and `REPO-CONFIG`. Placeholder and template-only checks run
only when `is_template` is `false`. `--format json` prints the findings for other tools.

## Migrations

| File | From | To | Change | Migration |
|---|---|---|---|---|
| `workflow.yml` | `1.0` | `1.1` | Adds the required fields `pull_requests.required_sections` and `pull_requests.automation_authors`, read by the pull request validator | Set `schema_version: "1.1"` and add both fields; the values in this template are the defaults. Until then the validator uses the defaults and `validate_project.py` still accepts `1.0`. |
