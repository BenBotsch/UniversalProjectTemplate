# engineering-bootstrap

`project-bootstrap` plans and applies the GitHub setup of a repository created from the project
template: labels, branches, settings and rulesets, as configured in the repository's `.project/`
directory. It runs as a dry run by default and changes something only with `--apply`.

This package lives in the template repository until it moves to its own repository. Derived
projects do not contain it.

## Status

The core is in place: configuration loading and validation, the plan and apply engine, the
GitHub API client and the reports. Implemented commands are `validate` without `--repo`, which
checks the local configuration, and `sync-labels`. All other commands exit with code `2` and the
message "not implemented yet".

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
project-bootstrap init --repo OWNER/NAME --profile python [--dry-run | --apply]
project-bootstrap validate [--repo OWNER/NAME]
project-bootstrap sync-labels --repo OWNER/NAME [--dry-run | --apply [--prune [--yes]]]
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

Exit codes: `0` success, `1` a change failed, the configuration is invalid or no token is
available, `2` invalid usage, an unconfirmed `--prune` or a command that is not implemented yet.

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

## Behavior

- **Dry run by default.** Without `--apply`, a run reads the actual state and reports what it
  would change, but writes nothing.
- **Idempotent.** Each resource compares the actual with the desired state. An item that
  already matches is reported as `noop`, so a second `--apply` with unchanged configuration
  changes nothing.
- **No deletion by default.** Planned deletions are reported as `skipped` unless destructive
  mode is enabled; for labels that is `--apply --prune` with confirmation.
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
| `github.py` | Token resolution, HTTP client with pagination, rate limits, retries, typed errors and log redaction |
| `report.py` | Text and JSON reports |
| `resources/labels.py` | Label resource: compare, create, update, rename and delete labels |

A resource implements `read_actual()`, `desired()`, `diff(actual, desired)` and `apply(change)`.
The engine has no GitHub specifics, so every resource can be tested with fakes; GitHub access is
tested with `httpx.MockTransport` and no test needs a real repository.
