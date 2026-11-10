---
id: "FEAT-024"
title: "Build Bootstrap CLI Core with Plan, Apply and Reports"
epic: "EPIC-07"
phase: 2
status: "planned"
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
| `pyproject.toml` | Package `engineering_bootstrap`, entry point `project-bootstrap`, Python >= 3.11 |
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

- [ ] **T1:** Package skeleton, CLI parsing, config loading.
- [ ] **T2:** Engine with `Resource` protocol and a fake resource for tests.
- [ ] **T3:** GitHub client with auth from `gh auth token` or `GITHUB_TOKEN`, pagination, rate limits, retries.
- [ ] **T4:** Report writers and JSON schema doc.

## Acceptance Criteria

- [ ] Bootstrap supports dry-run (§17.1).
- [ ] Bootstrap can run repeatedly without corrupting configuration: verified with a fake resource (§17.1).
- [ ] No secret appears in logs at debug level (test asserts redaction).

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
