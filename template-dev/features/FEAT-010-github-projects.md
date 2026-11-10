---
id: "FEAT-010"
title: "Provide Optional GitHub Projects Board Setup"
epic: "EPIC-03"
phase: 2
status: "planned"
priority: "medium"
effort: "m"
target_repo: "engineering-bootstrap"
spec_refs: ["§12.5", "§15.1", "§19.1"]
dependencies: ["FEAT-008", "FEAT-024"]
blocked_by_decisions: ["DEC-03"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-010: Provide Optional GitHub Projects Board Setup

## Objective

Bootstrap can create a GitHub Projects board for a repository with status view and roadmap view,
driven by `bootstrap.yml`, without making Projects the source of truth for issue metadata.

## Background

§15.1 rates GitHub Projects as high-value for status overview and roadmap; §12.5 defines Projects
as portfolio/board view only. Whether it is mandatory is open (`DEC-03`). Projects v2 is only
reachable via GraphQL and is owned by a user or organization, not a repository.

## Scope

- `bootstrap.yml` option `github_project: {enabled, owner, title, views}`.
- Board with fields mirroring labels (Status, Priority) and a Roadmap view by milestone.
- Documentation of the mapping between labels and project fields.

### Out of Scope

- Two-way synchronization of project fields to labels (only labels → fields, if at all).

## Deliverables

| Path | Description |
|---|---|
| `bootstrap/commands/project_board.py` (target repo) | Idempotent create/update of a Projects v2 board via GraphQL |
| `.project/bootstrap.yml` | New optional `github_project` section (schema update in `FEAT-014`) |
| `docs/governance/issue-management.md` (section) | "GitHub Projects" with field mapping |

## Requirements

1. **R1:** Disabled by default unless `DEC-03` decides otherwise.
2. **R2:** Idempotent: rerun finds the existing board by title and owner and does not duplicate it.
3. **R3:** Labels remain authoritative; the doc states that board fields are derived.
4. **R4:** Missing token scope (`project`) is reported as an explicit error, not success.

## Tasks

- [ ] **T1:** Record `DEC-03` (human).
- [ ] **T2:** Add config option and schema change.
- [ ] **T3:** Implement board creation with GraphQL mocks in tests.
- [ ] **T4:** Document mapping.

## Acceptance Criteria

- [ ] With the option enabled, a dry-run lists the board to be created; apply creates it once; a second apply reports "no change".
- [ ] Without `project` scope the command exits non-zero with a clear message.

## Verification

```text
pytest tests/commands/test_project_board.py
project-bootstrap init --repo OWNER/test-repo --dry-run   # shows board action
```

## Agent Notes

- **Allowed paths:** project board command and tests in the bootstrap code, `bootstrap.yml`, the doc section, this feature file, backlog status.
- **Requires approval:** running apply against a real account.
- **Pitfalls:** Projects v2 API differs for user vs. organization owners; test both paths with mocks.
