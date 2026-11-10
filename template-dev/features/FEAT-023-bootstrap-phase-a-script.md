---
id: "FEAT-023"
title: "Provide Phase A Bootstrap Script with GitHub CLI"
epic: "EPIC-07"
phase: 2
status: "implemented"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§13.1", "§13.3", "§13.4", "§13.6", "§13.8", "§21.6"]
dependencies: ["FEAT-008", "FEAT-013"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-023: Provide Phase A Bootstrap Script with GitHub CLI

## Objective

A PowerShell script creates a repository from the template with `gh`, syncs labels from
`labels.yml`, creates `develop` from `main` and prints a summary, so projects can start before the
Python CLI (`FEAT-024`) exists.

## Background

§13.8 Phase A: a PowerShell script with `gh` for own use. §13.3 shows repository creation and
label cloning, §13.4 the correct creation of `develop`. The idempotency rules of §13.6 apply from the
start. §21.6: "label already exists → no error".

## Scope

- `scripts/bootstrap/New-ProjectRepository.ps1` with `-Owner`, `-Name`, `-Visibility`,
  `-Description`, `-DryRun`.
- Label sync from `.project/labels.yml` (create or update, never delete).

### Out of Scope

- Rulesets, project init/placeholder replacement, audit (Phase B, `FEAT-026` to `FEAT-029`).

## Deliverables

| Path | Description |
|---|---|
| `scripts/bootstrap/New-ProjectRepository.ps1` | Steps: verify `gh auth status`; `gh repo create --template`; label sync; create `develop` from `main` if missing; summary |
| `scripts/bootstrap/README.md` | Prerequisites, permissions needed, examples, limits of Phase A |
| `tests/bootstrap/New-ProjectRepository.Tests.ps1` | Pester tests with `gh` mocked |

## Requirements

1. **R1:** `-DryRun` prints every planned `gh` call and changes nothing.
2. **R2:** Re-running against an existing repository updates labels and skips existing `develop` without error.
3. **R3:** Arguments passed to `gh` as arrays, never via string concatenation into a shell.
4. **R4:** Fails fast with a clear message if `gh` is missing or not authenticated.
5. **R5:** No token is printed or written to disk.
6. **R6:** Exit code non-zero on any failed step; summary lists done/skipped/failed steps.

## Tasks

- [x] **T1:** Script skeleton with parameter validation and auth check.
- [x] **T2:** Repo creation and `develop` branch creation, idempotent.
- [x] **T3:** Label sync from YAML (use `powershell-yaml` or `gh label create --force`); document the dependency.
- [x] **T4:** Pester tests and README.

## Acceptance Criteria

- [x] A new repository can be created from the template (§17.1).
- [x] Bootstrap can be run repeatedly without corrupting configuration (§17.1).
- [x] Bootstrap supports dry-run or equivalent plan output (§17.1).
- [x] §21.6: "label already exists → no error, update if needed".

## Verification

```text
Invoke-Pester tests/bootstrap
pwsh scripts/bootstrap/New-ProjectRepository.ps1 -Owner <test-owner> -Name upt-smoke -Visibility private -DryRun
```

## Agent Notes

- **Allowed paths:** `scripts/bootstrap/**`, `tests/bootstrap/**`, this feature file, backlog status.
- **Requires approval:** any non-dry-run execution against GitHub (creates real repositories).
- **Pitfalls:** `gh repo create --template` is asynchronous; wait for the default branch before creating `develop`.

## Implementation Notes

- The script defaults to a dry run; changes need `-Apply` (`-DryRun` is accepted and explicit).
  This follows `dry_run_default: true` in `bootstrap.yml` and §13.6, and goes beyond the `-DryRun`
  switch named in the scope.
- `develop` is created through the GitHub API (`POST repos/{repo}/git/refs` with the head SHA of
  `main`) instead of a local clone and push.
- The script waits for the default branch after `gh repo create --template` (`-WaitSeconds`,
  default 120).
- Labels use `powershell-yaml` for reading and `gh label create --force` for create-or-update.
  Empty descriptions are omitted because Windows PowerShell 5.1 drops empty native arguments.
- Placeholder replacement is out of scope (Phase B). `README.md` "Using this template" was
  corrected: it claimed that the bootstrap tooling replaces the placeholders.
- Verified locally: 18 Pester 5.7.1 tests with a simulated `gh` under Windows PowerShell 5.1.
  Not verified: PowerShell 7 and PSScriptAnalyzer.
- Smoke test on 2026-11-10 with approval, against the private test repository
  `BenBotsch/upt-smoke` from the private template `BenBotsch/universal-project-template`: dry run,
  then `-Apply` (all steps `done`, exit 0), then a second `-Apply` (creation and `develop` skipped,
  labels updated, exit 0). GitHub shows all 34 labels, plus the 10 GitHub default labels, which are
  left unchanged, and `develop` at the same commit as `main`. A label changed by hand to another
  color and description was restored by a third run.
