# Project Configuration

The files in `.project/` describe the project in machine-readable form. They are a **project
convention, not native GitHub configuration**: GitHub ignores them. They take effect only through
the bootstrap tool, the CI validators and the dashboard. A field that no tool reads has no effect.

Every file starts with `schema_version`. The current version is `"1.3"` for `bootstrap.yml`, `"1.2"`
for `workflow.yml`, `"1.1"` for `quality-gates.yml` and `labels.yml`, and `"1.0"` for `project.yml`. A
change to the structure of a file requires a new schema version and a migration note; see [Migrations](#migrations).

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
- Every action that `.github/workflows/` and `.github/actions/` use is allowed by
  `repository_settings.actions` in `bootstrap.yml`, so `configure-repo` cannot stop CI. Actions
  of verified creators count only if `patterns_allowed` lists them.

Unknown fields are rejected at every level. Project-specific data belongs under a top-level
`x_extensions` mapping, which every schema allows and template tooling ignores.

To change a structure, add a new schema file with the next version instead of editing the
existing one, update `schema_version` in the configuration file and document the migration.

## Files

| File | Content | Read by | Created by | Updated when |
|---|---|---|---|---|
| `project.yml` | Identity, template provenance, branches, versioning, technology, quality and agent flags | Bootstrap, validators, dashboard | Bootstrap | Stack, platform or policy changes |
| `labels.yml` | Label names, colors, descriptions, aliases and groups | Label synchronization, issue validation | Template owner | Taxonomy changes |
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
| `applies_when.events` | GitHub event names, for example `pull_request`, `push` |
| `applies_when.languages` | Values of `technology.languages` in `project.yml`; `"*"` means any language |
| `applies_when.changed_paths`, `ignored_paths` | Glob patterns of changed files; `*` also matches `/` |
| `workflow` | File name in `.github/workflows/`: `ci.yml` or a workflow that `ci.yml` calls |
| `job` | Job id in that workflow |
| `status` | `implemented`, `not_implemented` |
| `flaky_tests[]` | `test` (test id), `issue` (`#<number>`), `reason` |

`applies_when` is mandatory for every kind except `required`; all of its conditions must hold
for the gate to apply. A gate that applies passes only if its job finished with `success`. A
skipped, missing or `not_implemented` job fails the gate; it is never reported as green. See the
[Quality Model](../docs/governance/quality-model.md#enforcement-in-ci).

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
| `repository_settings.has_wiki`, `delete_branch_on_merge` | `true`, `false` |
| `repository_settings.topics` | Optional; up to 20 lowercase topics of letters, digits and `-`. Omit it to leave the topics unmanaged |
| `repository_settings.actions.allowed_actions` | `all`, `local_only`, `selected`; `selected` requires `github_owned_allowed`, `verified_allowed` and `patterns_allowed` (for example `owner/repo@*`), the other values forbid them |
| `repository_settings.actions.default_workflow_permissions` | `read`, `write` |
| `repository_settings.actions.can_approve_pull_request_reviews` | `true`, `false` |
| `repository_settings.security.*` | `true`, `false` for `dependabot_alerts`, `dependabot_security_updates`, `secret_scanning`, `secret_scanning_push_protection`, `private_vulnerability_reporting` |
| `protection.mode` | `solo` (no required approval), `team` (one approval, code owner review, stale approvals dismissed) |
| `protection.required_status_checks` | Check names, for example the CI job name `quality-gate`; each is required only after it has reported once on the branch |
| `protection.release_tag_pattern` | Optional; release tag pattern without `refs/tags/`, for example `v*`. Omit it to leave tags unprotected |
| `init.license` | SPDX id of a license that the GitHub licenses API offers, for example `MIT` or `Apache-2.0`, or `none` for no license ("All rights reserved") |
| `init.code_owner` | Optional; user or team (`org/team`) without `@` that replaces the template's code owner. Default: the repository owner; an organization needs a team |
| `init.copyright_holder` | Optional; copyright holder in `LICENSE`. Default: the profile name of the repository owner, else the login |

`project-bootstrap configure-repo` applies `repository_settings`. It takes the branch names and
the description from `project.yml` and the merge methods from `workflow.yml`, so these values are
not repeated here. Settings that GitHub does not offer for the repository's plan or visibility are
reported as skipped.

`project-bootstrap apply-rulesets` applies `protection` as rulesets on the default and the
development branch of `project.yml` and on the release tags; `bootstrap.configure_rulesets`
switches it off. See [Branch Protection](../docs/governance/branch-protection.md).

`project-bootstrap init` reads `init` when it turns a repository created from the template into a
project. Name, owner and description come from the GitHub repository, and command line options
override every value. The bootstrap tool README in the template describes the run.

## Template-only content

The template repository contains content that must not reach derived projects. Two fields
control this:

- `project.is_template` in `project.yml` is `true` in the template. Bootstrap sets it to `false`
  when it initializes a derived project.
- `template_only_paths` in `bootstrap.yml` lists the paths that exist only in the template.
  Bootstrap removes them during initialization. Repository validation fails if one of these paths
  exists while `is_template` is `false`.

Template-only text inside a file that a project keeps sits between two marker lines. Initialization
removes both lines and everything between them; blocks must not nest. The comment syntax follows the
file type:

```markdown
<!-- template-only:start -->
Text that only the template shows.
<!-- template-only:end -->
```

In YAML, `CODEOWNERS` and other files with `#` comments the lines are `# template-only:start` and
`# template-only:end`. Repository validation fails if a marker remains while `is_template` is
`false`.

## Placeholders

Values that bootstrap replaces during initialization use these tokens: `PROJECT_NAME`,
`PROJECT_DESCRIPTION`, `OWNER/REPOSITORY`, `OWNER/` (in clone URLs) and `@OWNER_OR_TEAM` (in
`CODEOWNERS`). `placeholder_tokens` in `workflow.yml` lists the tokens that repository validation
reports when they remain in a derived project.

Repository validation (`python -I scripts/ci/validate_repository.py`) reports each check with a
rule ID: `REPO-REQUIRED`, `REPO-PLACEHOLDER`, `REPO-TEMPLATE-ONLY`, `REPO-DEAD-LINK-TEMPLATE`,
`REPO-DOCS-INDEX`, `REPO-ISSUE-FORMS`, `REPO-CONFIG` and `REPO-TEMPLATE-MARKER`. Placeholder,
template-only and marker checks run
only when `is_template` is `false`. `--format json` prints the findings for other tools.

## Migrations

| File | From | To | Change | Migration |
|---|---|---|---|---|
| `workflow.yml` | `1.0` | `1.1` | Adds the required fields `pull_requests.required_sections` and `pull_requests.automation_authors`, read by the pull request validator | Set `schema_version: "1.1"` and add both fields; the values in this template are the defaults. Until then the validator uses the defaults and `validate_project.py` still accepts `1.0`. |
| `workflow.yml` | `1.1` | `1.2` | Adds the required field `pull_requests.merge_strategy.hotfix_into_default_branch`, decided in [ADR-0005](../docs/architecture/adr/0005-squash-hotfixes.md) | Set `schema_version: "1.2"` and add `hotfix_into_default_branch: "squash"`. `validate_project.py` still accepts `1.0` and `1.1`. |
| `quality-gates.yml` | `1.0` | `1.1` | Adds `applies_when` per gate, mandatory except for `required` gates, and the required list `flaky_tests` | Set `schema_version: "1.1"`, add `applies_when` to each conditional gate and `flaky_tests: []`. `validate_project.py` still accepts `1.0`, but the quality-gate job rejects it. |
| `labels.yml` | `1.0` | `1.1` | Adds the optional list `aliases` per label: existing label names that label synchronization renames to the configured name instead of creating a second label, so issues and pull requests keep their label | Set `schema_version: "1.1"` and add `aliases` where an existing label should be renamed. An alias must not equal another label's name or alias. `validate_project.py` still accepts `1.0` without `aliases`. |
| `bootstrap.yml` | `1.0` | `1.1` | Adds the required section `repository_settings` with wiki, auto-delete of head branches, optional topics, Actions permissions, workflow token and security features, read by `project-bootstrap configure-repo` | Set `schema_version: "1.1"` and copy the `repository_settings` section of this template; adjust `patterns_allowed` to the third-party actions the workflows use. `validate_project.py` still accepts `1.0`, but `configure-repo` rejects it. |
| `bootstrap.yml` | `1.1` | `1.2` | Adds the required section `protection` with the review mode, the required status checks and the optional release tag pattern, read by `project-bootstrap apply-rulesets` | Set `schema_version: "1.2"` and copy the `protection` section of this template; use `mode: "team"` when more than one maintainer reviews. `validate_project.py` still accepts `1.0` and `1.1`, but `apply-rulesets` rejects them. |
| `bootstrap.yml` | `1.2` | `1.3` | Adds the required section `init` with the required `license` and the optional `code_owner` and `copyright_holder`, read by `project-bootstrap init` | Set `schema_version: "1.3"` and add `init:` with `license: "MIT"` or the project's license. `validate_project.py` still accepts `1.0` to `1.2`; `init` reads the section only in the template checkout it initializes. |
