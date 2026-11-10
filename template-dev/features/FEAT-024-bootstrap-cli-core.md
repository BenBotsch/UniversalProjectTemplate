---
id: "FEAT-024"
title: "Build Bootstrap CLI Core with Plan, Apply and Reports"
epic: "EPIC-07"
phase: 2
status: "implemented"
priority: "critical"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§13.1", "§13.3", "§13.5", "§13.6", "§13.7", "§13.8"]
dependencies: ["FEAT-013", "FEAT-014"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-024: Build Bootstrap CLI Core with Plan, Apply and Reports

## Objective

A Python CLI `project-bootstrap` provides the shared core for all Phase B commands: config
loading and validation, desired-vs-actual diff, `--dry-run`/`--apply`, GitHub API client, and
human-readable plus JSON reports.

## Background

§13.8 Phase B: a small Python CLI with declarative configuration and tests, plus API mocks and a
retry/rollback strategy. §13.5 configuration (`.project/bootstrap.yml`, own schema), §13.6
idempotency (detect, compare, no destructive changes, dry-run default, machine-readable summary,
clear permission errors), §13.7 proposed commands. §16.3 places the tool in its own repository.
`DEC-01` is decided: Python 3.12+ CLI, distributed via `pipx`/`uv tool`
([ADR-0002](../../docs/architecture/adr/0002-python-bootstrap-cli.md)).

## Scope

- Package layout, CLI entry point, `plan` and `apply` engine with pluggable "resources".
- GitHub client wrapper with token auth, pagination, rate-limit handling, retries.
- Report writers (text, JSON).

### Out of Scope

- Concrete resources: labels (`FEAT-025`), branches/settings (`FEAT-026`), rulesets (`FEAT-027`),
  init (`FEAT-028`), audit (`FEAT-029`).

## Deliverables

| Path | Description |
|---|---|
| `pyproject.toml` | Package `engineering_bootstrap`, entry point `project-bootstrap`, Python >= 3.12 |
| `src/engineering_bootstrap/cli.py` | Subcommands from §13.7; global `--config`, `--dry-run` (default), `--apply`, `--format text\|json`, `--report-file` |
| `src/engineering_bootstrap/engine.py` | `Resource` protocol: `read_actual()`, `desired()`, `diff()`, `apply(change)`; ordered execution |
| `src/engineering_bootstrap/github.py` | Client with auth, pagination, rate-limit backoff, typed errors |
| `src/engineering_bootstrap/config.py` | Loads `.project/*.yml`, validates against schemas from `FEAT-014` |
| `src/engineering_bootstrap/report.py` | Change list `create/update/delete/noop/skipped/failed` with reasons |
| `tests/**` | Engine and client tests with HTTP mocks (`respx` or `responses`) |

## Requirements

1. **R1:** Dry-run is the default; `--apply` is required for writes.
2. **R2:** A second `apply` with unchanged config produces only `noop` entries.
3. **R3:** Tokens are never logged; HTTP debug logging redacts `Authorization`.
4. **R4:** On rate limit, waits until reset or fails with a clear message if wait exceeds a limit.
5. **R5:** Each resource failure is reported; the run continues for independent resources and exits non-zero. Transient errors are retried; the report lists completed changes so a partial apply can be rolled back manually (§13.8).
6. **R6:** JSON report schema is versioned (`report_version`) and documented.
7. **R7:** Until the separate `engineering-bootstrap` repository (§16.3) exists, the package lives in this repo under `tools/engineering-bootstrap/`; module paths in `FEAT-025` to `FEAT-031` are relative to that package root.

## Tasks

- [x] **T1:** Package skeleton, CLI parsing, config loading.
- [x] **T2:** Engine with `Resource` protocol and a fake resource for tests.
- [x] **T3:** GitHub client with auth from `gh auth token` or `GITHUB_TOKEN`, pagination, rate limits, retries.
- [x] **T4:** Report writers and JSON schema doc.

## Acceptance Criteria

- [x] Bootstrap supports dry-run (§17.1).
- [x] Bootstrap can run repeatedly without corrupting configuration: verified with a fake resource (§17.1).
- [x] No secret appears in logs at debug level (test asserts redaction).

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests
project-bootstrap --help
project-bootstrap validate --config .project/bootstrap.yml --dry-run --format json
```

## Agent Notes

- **Allowed paths:** `tools/engineering-bootstrap/**`, this feature file, backlog status.
- **Requires approval:** any `--apply` against real GitHub.
- **Pitfalls:** Keep the engine free of GitHub specifics so resources stay testable with fakes.

## Implementation Notes

- Implemented in `tools/engineering-bootstrap/` (R7); the package README documents commands,
  options, exit codes, authentication, behavior and the report format (R6). The report schema is
  `src/engineering_bootstrap/schemas/report-1.0.schema.json`.
- **Deviation:** `requires-python = ">=3.12"` instead of 3.11, following ADR-0002 (DEC-01).
- **Deviation:** HTTP mocks use `httpx.MockTransport` instead of `respx` or `responses`; the client
  is built on `httpx`, so no extra test dependency is needed (decision of the maintainer).
- Of the §13.7 commands, only `validate` without `--repo` (local configuration) is implemented.
  `init`, `sync-labels`, `audit` and `validate --repo` exit with code 2 and "not implemented yet";
  their resources follow in FEAT-025 to FEAT-029.
- `config.py` validates each `.project/*.yml` against the project's own
  `.project/schemas/<name>-<version>.schema.json`. The cross-file checks remain in
  `scripts/ci/validate_project.py`; the separate repository (§16.3) cannot import them.
- The engine skips planned deletions unless `allow_destructive` is set; the CLI has no option for
  it yet. After network or server errors only idempotent methods are retried, not `POST`;
  rate-limited requests are retried for every method (R4, R5).
- Redaction (R3): the client logs only method, URL and status; `RedactingFilter` on the log
  handlers removes the token, `Authorization` values and GitHub token patterns. Tests assert that
  debug logs of the client and `httpx` contain neither the token nor `Bearer`.
- **Paths outside the allowed paths, approved by the maintainer:** `.project/bootstrap.yml` (the
  package is a template-only path), `.github/workflows/ci.yml` (job `bootstrap-tool`, also needed
  by `quality-gate`), `.project/quality-gates.yml` (gate `bootstrap_tool`, applies to changes below
  `tools/engineering-bootstrap/`), `scripts/ci/README.md` (checks table) and
  `tests/ci/test_validate_project.py` (two cases assumed exactly one template-only path).
- **Verification (local, Windows, Python 3.12 virtual environment):** 65 package tests pass;
  `ruff check` and `ruff format --check` pass; after `pip install ./tools/engineering-bootstrap`,
  `project-bootstrap --help` lists the four commands and
  `project-bootstrap validate --config .project/bootstrap.yml --dry-run --format json` reports
  five `noop` entries with exit code 0. `tests/ci` (294 tests), both repository validators,
  actionlint, zizmor, yamllint, markdownlint and gitleaks pass. On GitHub, CI run 42842134012
  for f930904 on `develop` passed: `bootstrap-tool` ran the 65 tests and both ruff checks, and
  `quality-gate` reported `bootstrap_tool` as passed.
- No `--apply` against real GitHub was executed.
