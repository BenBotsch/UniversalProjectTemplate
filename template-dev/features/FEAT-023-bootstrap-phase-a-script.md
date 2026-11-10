---
id: "FEAT-023"
title: "Provide Phase A Bootstrap Script with GitHub CLI"
epic: "EPIC-07"
phase: 2
status: "planned"
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
- Label sync from `.github/labels.yml` (create or update, never delete).

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

- [ ] **T1:** Script skeleton with parameter validation and auth check.
- [ ] **T2:** Repo creation and `develop` branch creation, idempotent.
- [ ] **T3:** Label sync from YAML (use `powershell-yaml` or `gh label create --force`); document the dependency.
- [ ] **T4:** Pester tests and README.

## Acceptance Criteria

- [ ] A new repository can be created from the template (§17.1).
- [ ] Bootstrap can be run repeatedly without corrupting configuration (§17.1).
- [ ] Bootstrap supports dry-run or equivalent plan output (§17.1).
- [ ] §21.6: "label already exists → no error, update if needed".

## Verification

```text
Invoke-Pester tests/bootstrap
pwsh scripts/bootstrap/New-ProjectRepository.ps1 -Owner <test-owner> -Name upt-smoke -Visibility private -DryRun
```

## Agent Notes

- **Allowed paths:** `scripts/bootstrap/**`, `tests/bootstrap/**`, this feature file, backlog status.
- **Requires approval:** any non-dry-run execution against GitHub (creates real repositories).
- **Pitfalls:** `gh repo create --template` is asynchronous; wait for the default branch before creating `develop`.
