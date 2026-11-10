# Project Configuration

The files in `.project/` describe the project in machine-readable form. They are a **project
convention, not native GitHub configuration**: GitHub ignores them. They take effect only through
the bootstrap tool, the CI validators and the dashboard. A field that no tool reads has no effect.

Every file starts with `schema_version`. The current version of all files is `"1.0"`. A change to
the structure of a file requires a new schema version and a migration note.

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
| `issue_policy.initial_status` | A value from `issue_policy.supported_states` |
| `issue_policy.*_label_groups`, `required_for_ready` | Group names from `labels.yml` |

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
