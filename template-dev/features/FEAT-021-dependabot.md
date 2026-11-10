---
id: "FEAT-021"
title: "Configure Dependabot Baseline"
epic: "EPIC-06"
phase: 2
status: "active"
priority: "high"
effort: "xs"
target_repo: "universal-project-template"
spec_refs: ["§10.8", "§11.1", "§13.2", "§19"]
dependencies: ["FEAT-008"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-021: Configure Dependabot Baseline

## Objective

The template ships a Dependabot configuration for GitHub Actions targeting `develop`, and documents
how profiles add ecosystems and how security PRs are synchronized.

## Background

§10.8 example; ecosystems are added only if the project files exist; security-update PRs follow the
default branch (`main`) and must be synced to `develop` (§19).

## Scope

- `.github/dependabot.yml` for `github-actions`.
- Documentation of ecosystem extension and security-PR sync.

### Out of Scope

- Ecosystem entries per profile (`FEAT-031` generates them).

## Deliverables

| Path | Description |
|---|---|
| `.github/dependabot.yml` | §10.8, weekly, `target-branch: develop`, labels `area:ci-cd`, `type:task`, commit message prefix `ci(deps)` |
| `docs/governance/branching-and-releases.md` (section) | "Dependency updates": security PRs target `main`, merge back into `develop` |

## Requirements

1. **R1:** Labels used exist in `labels.yml`.
2. **R2:** Commit prefix is compatible with `FEAT-019` title rules.
3. **R3:** No ecosystem entry for files that do not exist in the template.

## Tasks

- [x] **T1:** Add `dependabot.yml`.
- [x] **T2:** Add documentation section.

## Acceptance Criteria

- [x] Dependency updates are configured (§17.5).
- [ ] GitHub shows the Dependabot configuration as valid in a test repository.

## Verification

```text
yamllint .github/dependabot.yml
# GitHub Insights > Dependency graph > Dependabot shows no config errors.
```

## Agent Notes

- **Allowed paths:** `.github/dependabot.yml`, the doc section, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Version-update PRs honor `target-branch`; security-update PRs do not.

## Implementation Notes

- `.github/dependabot.yml` follows §10.8 with `commit-message.prefix: "ci"` and
  `include: "scope"`, which produces titles such as `ci(deps): bump actions/checkout ...`. Both
  labels exist in `.project/labels.yml`.
- Only `github-actions` is configured. The template also contains `scripts/ci/requirements*.txt`;
  a `pip` entry for them is left out because the scope names only GitHub Actions. Profiles add
  ecosystems (`FEAT-031`).
- `docs/governance/branching-and-releases.md` has a new "Dependency Updates" section;
  `docs/governance/security-policy.md` names the file in the dependency row.
- Open: GitHub must show the configuration as valid after the push.
