# engineering-bootstrap

`project-bootstrap` plans and applies the GitHub setup of a repository created from the project
template: labels, branches, settings and rulesets, as configured in the repository's `.project/`
directory. It runs as a dry run by default and changes something only with `--apply`.

This package lives in the template repository until it moves to its own repository. Derived
projects do not contain it.

## Status

The core is in place: configuration loading and validation, the plan and apply engine, the
GitHub API client and the reports. Implemented commands are `init` without `--profile`,
`validate` without `--repo`, which checks the local configuration, `sync-labels`, `configure-repo`
and `apply-rulesets`. All other commands and options exit with code `2` and the message "not
implemented yet".

## Installation

Python 3.12 or later is required. Install the tool from the package directory with `pipx` or
`uv tool`:

```text
pipx install ./tools/engineering-bootstrap
uv tool install ./tools/engineering-bootstrap
```

For development, install the pinned test and lint dependencies and run the checks from the
package directory:

```text
python -I -m pip install -r requirements-dev.txt
python -I -m pytest
ruff check .
ruff format --check .
```

## Commands

```text
project-bootstrap init --repo OWNER/NAME [--path DIR] [--dry-run | --apply --issue N]
project-bootstrap validate [--repo OWNER/NAME]
project-bootstrap sync-labels --repo OWNER/NAME [--dry-run | --apply [--prune [--yes]]]
project-bootstrap configure-repo --repo OWNER/NAME [--dry-run | --apply]
project-bootstrap apply-rulesets --repo OWNER/NAME [--dry-run | --apply] [--allow-unprotected]
project-bootstrap audit --owner OWNER
```

Options of every command:

| Option | Meaning |
|---|---|
| `--config PATH` | `bootstrap.yml` or the `.project` directory; default `.project/bootstrap.yml` |
| `--dry-run` | Only report the planned changes; the default |
| `--apply` | Write the planned changes |
| `--format text\|json` | Output format of the report on standard output; default `text` |
| `--report-file PATH` | Also write the report as JSON to this file |
| `-v`, `--verbose` | Log debug messages to standard error |

Options of `sync-labels`:

| Option | Meaning |
|---|---|
| `--repo OWNER/NAME` | Repository whose labels are synchronized; required |
| `--prune` | Also delete labels that are not in `labels.yml`; requires `--apply` |
| `--yes` | Confirm `--prune` without the interactive question, for example in CI |

Options of `init`:

| Option | Meaning |
|---|---|
| `--repo OWNER/NAME` | Repository created from the template; required. The clone's `origin` must point to it |
| `--path DIR` | Root of the local clone; default the current directory |
| `--issue N` | Issue of the initialization; required with `--apply`. It names the branch `chore/N-project-init` and the commit footer `Refs: #N` |
| `--name`, `--description` | Project name and description; default the repository name and the GitHub description |
| `--code-owner USER\|ORG/TEAM` | Code owner without `@`; default `init.code_owner`, else the repository owner |
| `--license SPDX\|none` | License; default `init.license` |
| `--copyright-holder TEXT` | Holder in `LICENSE`; default `init.copyright_holder`, else the owner's profile name |
| `--template-source OWNER/NAME` | Template repository; default the repository's GitHub template |
| `--profile NAME` | Technology profile; not implemented yet |

Without `--config`, `init` reads `.project/bootstrap.yml` of the clone given by `--path`.

Exit codes: `0` success, `1` a change failed, the configuration is invalid, no token is
available, `apply-rulesets` found an unprotected repository or `init` refused the target, `2`
invalid usage, an invalid `init` value, an unconfirmed `--prune` or a command that is not
implemented yet.

## Label Synchronization

`sync-labels` makes the labels of a repository match `.project/labels.yml`:

- A configured label is found by name, case-insensitively as on GitHub. If it differs in color,
  description or the spelling of its name, it is updated; otherwise it is reported as `noop`.
- If a configured label is missing but a label with one of its `aliases` exists, that label is
  renamed. Issues and pull requests keep it, so for example GitHub's default `bug` becomes
  `type:bug`. Without a matching alias the label is created.
- A label that is not in `labels.yml` is reported as `skipped` and kept. With `--apply --prune`
  it is deleted; the run first lists each such label with the number of issues and pull requests
  that use it and asks for confirmation, or requires `--yes` when there is no terminal or the
  output format is `json`. The usage count comes from the search API and can lag behind recent
  changes.
- `bootstrap.synchronize_labels` in `bootstrap.yml` does not affect this command; it is meant for
  `init`.

## Project Initialization

`init` turns a fresh clone of a repository created from the template into a project. It works on
the local working tree; the only GitHub requests are reads of the repository, the owner's profile
and the license text. The plan has one change per path:

- every path in `bootstrap.template_only_paths` is deleted, including this tool;
- `.project/project.yml` gets the name, description, visibility, `is_template: false` and
  `template.source`; comments and layout are kept;
- `LICENSE` is written from the GitHub licenses API with the current year and the copyright
  holder, or deleted for `none`; the `## License` section of `README.md` names the license or
  states "All rights reserved";
- every other tracked UTF-8 text file loses its template-only marker blocks and gets its
  placeholder tokens replaced, and `.github/CODEOWNERS` names the project's code owner instead of
  the template's. Files in `placeholder_allowlist` are not edited. A configured token without a
  known value is reported as `skipped` and must be replaced by hand.

Markers and tokens are described in [Project Configuration](../../.project/README.md#template-only-content).

`init` refuses, with exit code `1` and before it changes anything, a repository that is a template
on GitHub, the template's own checkout (`is_template: true` and `template.source` equal to
`--repo`) and a clone whose `origin` does not point to `--repo`.

With `--apply --issue N` it requires a clean working tree, creates `chore/N-project-init` from the
development branch of `project.yml` (local, else `origin/`), writes the changes, stages them and
runs the clone's `scripts/ci/validate_repository.py`. Only if validation reports no error does it
commit `chore: initialize project from template`. It never pushes; the report and standard error
list the `git push` and `gh pr create` commands for the pull request into the development branch.
If writing or validation fails, nothing is committed and the branch is left for inspection.

Install the tool from the template checkout without `--editable` before the first `--apply`,
because initialization deletes `tools/`. A second run on the initialized clone plans no change.

## Branches and Repository Settings

`configure-repo --repo OWNER/NAME` needs `bootstrap.yml` with `schema_version: "1.1"` and a
`repository_settings` section; with schema `1.0` it exits with `1` before any request. The token
needs administration access to the repository, otherwise the settings fail without a change.

Branches (resource `branches`), from `repository` in `project.yml`:

- The default branch must exist. In a repository without commits it is reported as `failed`,
  because the API cannot create a branch without a commit.
- A missing development branch is created at the head of the default branch, unless
  `bootstrap.create_develop_branch` is `false`. An existing development branch is never moved or
  reset, even if it is behind.

Settings (resource `repository-settings`), one change per setting:

| Key | Source | GitHub setting |
|---|---|---|
| `default_branch` | `project.yml` `repository.default_branch` | Default branch |
| `description` | `project.yml` `project.description`; `skipped` while it contains a placeholder token | Description |
| `has_issues`, `has_discussions` | `bootstrap.enable_issues`, `bootstrap.enable_discussions` | Issues, Discussions |
| `has_wiki`, `delete_branch_on_merge` | `repository_settings` | Wiki, automatic deletion of head branches |
| `merge_methods` | `workflow.yml` `pull_requests.merge_strategy`: each method used there is allowed, all others are disallowed | Squash, merge commit and rebase merging, written in one request |
| `is_template` | `project.yml` `project.is_template` | Template repository; only reported, never changed |
| `topics` | `repository_settings.topics`; `skipped` when not set | Topics, replaced as a whole |
| `actions_permissions`, `actions_selected` | `repository_settings.actions` | Allowed actions and, for `selected`, the allow-list |
| `workflow_permissions` | `repository_settings.actions` | Default `GITHUB_TOKEN` permissions and whether Actions may approve pull requests |
| `dependabot_alerts`, `dependabot_security_updates` | `repository_settings.security`, if `bootstrap.configure_dependabot` | Dependabot alerts and security updates |
| `secret_scanning`, `secret_scanning_push_protection`, `private_vulnerability_reporting` | `repository_settings.security`, if `bootstrap.configure_security` | Secret scanning, push protection, private vulnerability reporting |

A setting is `skipped` with the reason when the configuration leaves it unmanaged or GitHub does
not offer it for the repository: secret scanning and push protection in a private repository
without GitHub Secret Protection or Advanced Security, and private vulnerability reporting in a
private repository. A `false` value switches a feature off. With `allowed_actions: "selected"`,
a workflow that uses an action outside the allow-list fails until the action is added to
`patterns_allowed` and `configure-repo` runs again. Organization policies can make GitHub refuse
an Actions setting; the change is then `failed` with GitHub's message.

## Rulesets

`apply-rulesets --repo OWNER/NAME` needs `bootstrap.yml` with `schema_version: "1.2"` and a
`protection` section; with an older schema it exits with `1` before any request. The token needs
administration access to the repository. Resource `rulesets`, one change per ruleset:

| Key | Applies to | Source |
|---|---|---|
| `bootstrap-default-branch` | Default branch | Branch from `project.yml`, merge methods from `workflow.yml`, review mode and required checks from `protection` |
| `bootstrap-development-branch` | Development branch | As above |
| `bootstrap-release-tags` | `refs/tags/<protection.release_tag_pattern>`; `skipped` when not set | `protection.release_tag_pattern` |
| `<ruleset>:<check>` | A required check that never reported on the branch | `skipped`: the check is not required yet, because it would block every merge |
| `other:<name>` | A ruleset with another name | `skipped`: reported, never changed |

- A missing ruleset is created, a ruleset whose content differs is replaced as a whole, and a
  matching one is `noop`. Parameters that GitHub adds with default values are ignored in the
  comparison.
- The rulesets have no bypass actors. A required check is bound to the GitHub App of its latest
  run.
- If GitHub offers no rulesets for the repository, as for private repositories on GitHub Free,
  every ruleset is `failed` with a reason starting with `UNPROTECTED` and the exit code is `1`.
  `--allow-unprotected` reports them as `skipped` instead and exits with `0`. There is no fallback
  to classic branch protection, which is unavailable in the same case.
- `bootstrap.configure_rulesets: false` reports every ruleset as `skipped` without a request.

Rules per branch, plan limits and manual steps:
[Branch Protection](../../docs/governance/branch-protection.md).

## Behavior

- **Dry run by default.** Without `--apply`, a run reads the actual state and reports what it
  would change, but writes nothing.
- **Idempotent.** Each resource compares the actual with the desired state. An item that
  already matches is reported as `noop`, so a second `--apply` with unchanged configuration
  changes nothing.
- **No deletion by default.** Planned deletions are reported as `skipped` unless destructive
  mode is enabled; for labels that is `--apply --prune` with confirmation. `init` is the exception:
  it deletes template-only paths in the local working tree, and the result is reviewed in the
  pull request before it reaches GitHub.
- **Partial failures.** If a resource fails, its changes are reported as `failed` and resources
  that depend on it as `skipped`; independent resources still run, and the exit code is `1`.
  Changes that were written have `"applied": true` in the report, so a partial run can be
  reviewed and rolled back by hand.
- **Retries.** Network errors and HTTP 500, 502, 503 and 504 are retried with exponential
  backoff, three times by default. `POST` requests are not retried after such errors, because
  the first attempt may have succeeded; the next run detects the state and plans again.
- **Rate limits.** On a rate limit response the client waits for `retry-after` or the
  `x-ratelimit-reset` time, and 60 seconds for a secondary rate limit without either header. A
  wait longer than five minutes fails with a message that states the reset time.

## Authentication

The client uses the first available token of:

1. the environment variable `GITHUB_TOKEN`,
2. the environment variable `GH_TOKEN`,
3. the output of `gh auth token`.

The token is sent only in the `Authorization` header and only to the API origin, by default
`https://api.github.com`. Redirects are not followed, and pagination links to another host are
refused. The tool never logs request headers, and a log filter replaces the token and
credential-like values with `***`, also at debug level.

## Report Format

`--format json` and `--report-file` write a report that follows
[report-1.0.schema.json](src/engineering_bootstrap/schemas/report-1.0.schema.json):

```json
{
  "report_version": "1.0",
  "tool": {"name": "engineering-bootstrap", "version": "0.1.0"},
  "command": "sync-labels",
  "mode": "apply",
  "target": "OWNER/NAME",
  "generated_at": "2026-11-10T12:00:00+00:00",
  "summary": {"create": 1, "update": 0, "delete": 0, "noop": 12, "skipped": 0, "failed": 0},
  "changes": [
    {
      "resource": "labels",
      "key": "type:bug",
      "action": "create",
      "reason": "missing",
      "details": {"color": "d73a4a"},
      "applied": true
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `report_version` | Version of the report layout. A new major version removes, renames or redefines a field; a new minor version only adds fields |
| `mode` | `dry-run` or `apply` |
| `target` | Repository, owner or configuration directory the run worked on |
| `summary` | Number of changes per action; every action is listed |
| `changes[].resource` | Resource that produced the change, for example `labels` |
| `changes[].key` | Item inside the resource; `*` for the resource as a whole |
| `changes[].action` | `create`, `update`, `delete`, `noop`, `skipped` or `failed` |
| `changes[].reason` | Why the change is planned, skipped or failed |
| `changes[].details` | Values the change writes; never secrets |
| `changes[].applied` | `true` once the change was written |

## Architecture

| Module | Responsibility |
|---|---|
| `cli.py` | Argument parsing, logging setup, report output and exit codes |
| `config.py` | Reads `.project/*.yml` and validates each file against `.project/schemas/` |
| `engine.py` | `Resource` protocol, dependency order, dry run and apply |
| `git.py` | Local Git commands of `init`: tracked files, status, branch, stage and commit |
| `github.py` | Token resolution, HTTP client with pagination, rate limits, retries, typed errors and log redaction |
| `report.py` | Text and JSON reports |
| `resources/labels.py` | Label resource: compare, create, update, rename and delete labels |
| `resources/branches.py` | Branch resource: check the default branch, create the development branch |
| `resources/repo_settings.py` | Settings resource: repository, Actions and security settings |
| `resources/init.py` | Init resource and run: values, target checks, text edits, validation and commit |
| `resources/rulesets.py` | Ruleset resource: plan detection, branch and tag rulesets, required checks |

A resource implements `read_actual()`, `desired()`, `diff(actual, desired)` and `apply(change)`.
The engine has no GitHub specifics, so every resource can be tested with fakes; GitHub access is
tested with `httpx.MockTransport` and no test needs a real repository.
