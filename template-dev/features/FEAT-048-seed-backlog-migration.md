---
id: "FEAT-048"
title: "Migrate Seed Backlog to GitHub Issues"
epic: "EPIC-10"
phase: 2
status: "planned"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§5.11", "§12.5", "§15.1"]
dependencies: ["FEAT-007", "FEAT-008", "FEAT-025"]
blocked_by_decisions: []
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-048: Migrate Seed Backlog to GitHub Issues

## Objective

Once the template repository exists on GitHub, every epic and feature in `template-dev/` becomes a
GitHub Issue (epics as parents, features as sub-issues) with correct labels and dependencies. From
then on, issues are the source of truth for status; feature files stay as specifications.

## Background

§5.11 and §12.5: Markdown must not duplicate issue status. The seed backlog exists only because no
repository existed at planning time. Issues of the template repository are not copied to derived
repositories, so the template-only rule is kept.

## Scope

- Migration script with dry-run; idempotent by marker `<!-- seed-id: FEAT-NNN -->` in issue bodies.
- Update `related_issues` in each feature file; mark `backlog.md` status column as "see issue".

### Out of Scope

- Projects board setup (`FEAT-010`).

## Deliverables

| Path | Description |
|---|---|
| `template-dev/tools/migrate_seed_backlog.py` | Parses frontmatter, creates or updates issues, sets sub-issue relations and "blocked by" dependencies where the API supports it |
| `template-dev/tools/README.md` (section) | Usage, required token scopes, rollback (close issues by marker) |
| Feature files (frontmatter) | `related_issues: ["#N"]` filled |
| `template-dev/tools/generate_backlog.py` | Status column of the generated backlog replaced by issue links from `related_issues` |

## Requirements

1. **R1:** Labels per issue: `type:epic` or `type:feature`, `priority:*`, `effort:*`, `status:ready` if `agent_ready` else `status:triage`/`status:blocked`, `agent:ready` if `agent_ready`.
2. **R2:** Re-run updates existing issues found by marker; never creates duplicates.
3. **R3:** Dry-run prints every planned API call.
4. **R4:** Issue body links back to the feature file on the default branch.
5. **R5:** Lives inside `template-dev/` because it is template-only tooling.

## Tasks

- [ ] **T1:** Script with dry-run and marker-based idempotency.
- [ ] **T2:** Sub-issues and dependencies.
- [ ] **T3:** Run migration (human-approved), update feature files and backlog.

## Acceptance Criteria

- [ ] All epics and features exist as issues with correct hierarchy and labels.
- [ ] A second run makes no changes.
- [ ] `template-dev/README.md` states that issues are now the source of truth for status.

## Verification

```text
python -I template-dev/tools/migrate_seed_backlog.py --repo <owner>/universal-project-template --dry-run
```

## Agent Notes

- **Allowed paths:** `template-dev/**`.
- **Requires approval:** creating the GitHub repository; running the migration without `--dry-run`.
- **Pitfalls:** Issue validation (`FEAT-018`) may comment on created issues; bodies must contain the sections the forms produce.
