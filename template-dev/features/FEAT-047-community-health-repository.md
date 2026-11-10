---
id: "FEAT-047"
title: "Provide Optional .github Community Health Repository"
epic: "EPIC-10"
phase: 4
status: "planned"
priority: "low"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§16.4", "§21.1"]
dependencies: ["FEAT-002"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-047: Provide Optional .github Community Health Repository

## Objective

A documented blueprint for a public `.github` repository on user or organization level supplies
default community health files, without replacing per-repository files or bootstrap settings.

## Background

§16.4: a `.github` repository supplies community health files only when a repository has none of its
own; it does not replace bootstrap automation or repository settings.

## Scope

- Blueprint directory with default `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `SECURITY.md`, issue
  config fallback, and a README that explains precedence.

### Out of Scope

- Creating the `.github` repository on GitHub (human action).

## Deliverables

| Path | Description |
|---|---|
| `blueprints/dot-github/README.md` | Precedence rules, which files GitHub falls back to, what it cannot do |
| `blueprints/dot-github/*.md` | Default files with placeholders |
| `.project/bootstrap.yml` (field) | `template_only_paths` gains `blueprints/` |

## Requirements

1. **R1:** Files contain no project-specific content.
2. **R2:** README states that per-repo files take precedence and that settings are not inherited.
3. **R3:** `blueprints/` is template-only and removed by `init`.

## Tasks

- [ ] **T1:** Blueprint files and README.
- [ ] **T2:** Add `blueprints/` to `template_only_paths`.

## Acceptance Criteria

- [ ] The blueprint can be copied into a new `.github` repository unchanged except for placeholders.

## Verification

```text
python -I scripts/ci/validate_repository.py
markdownlint-cli2 "blueprints/**/*.md"
```

## Agent Notes

- **Allowed paths:** `blueprints/dot-github/**`, `bootstrap.yml` field, this feature file, backlog status.
- **Requires approval:** creating the `.github` repository.
- **Pitfalls:** `.github` must be public to provide defaults to public repositories.
