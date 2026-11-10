---
id: "FEAT-011"
title: "Add Pull Request Template and CODEOWNERS Convention"
epic: "EPIC-04"
phase: 1
status: "implemented"
priority: "critical"
effort: "xs"
target_repo: "universal-project-template"
spec_refs: ["§8.4", "§8.6", "§14.3"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-011: Add Pull Request Template and CODEOWNERS Convention

## Objective

Every pull request starts from a template that captures summary, issue reference, change type,
validation evidence, risks and review notes; `CODEOWNERS` defines ownership with a placeholder.

## Background

§8.4 contains the complete PR template (the inner `~~~text` block is valid Markdown). §8.6 the
CODEOWNERS example with `@OWNER_OR_TEAM`; it does not enforce reviews by itself and must not
block solo accounts (§14.3).

## Scope

- `.github/PULL_REQUEST_TEMPLATE.md` per §8.4.
- `.github/CODEOWNERS` with placeholder and explanatory comments.

### Out of Scope

- PR validation logic (`FEAT-019`), required-review rules (`FEAT-027`).

## Deliverables

| Path | Description |
|---|---|
| `.github/PULL_REQUEST_TEMPLATE.md` | §8.4 sections; headings stable for `FEAT-019` parsing |
| `.github/CODEOWNERS` | §8.6 with comments: placeholder replaced by bootstrap; review enforcement needs rulesets; solo-account caveat |

## Requirements

1. **R1:** Section headings exactly: Summary, Related Issues, Change Type, Implementation Details, Validation, Tests Executed, Risks and Rollback, Review Notes.
2. **R2:** "Related Issues" shows both `Refs: #` and `Closes #` usage and explains the difference (§9.1).
3. **R3:** CODEOWNERS uses only `@OWNER_OR_TEAM` so `FEAT-015` detects it as placeholder.

## Tasks

- [x] **T1:** Add PR template.
- [x] **T2:** Add CODEOWNERS.

## Acceptance Criteria

- [x] A new PR in a test repository is pre-filled with the template.
- [x] CODEOWNERS is syntactically valid (GitHub shows no CODEOWNERS errors on the file page) after placeholder replacement.

## Verification

```text
grep -c "^## " .github/PULL_REQUEST_TEMPLATE.md     # 7 level-2 sections
# Manual: GitHub CODEOWNERS file view shows no errors in a bootstrapped test repo.
```

## Agent Notes

- **Allowed paths:** the two files, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** An unreplaced `@OWNER_OR_TEAM` produces CODEOWNERS errors in derived repos; `FEAT-028` replaces it, `FEAT-015` detects it.

## Implementation Notes

- Owner decided by the maintainer on 2026-11-10: `.github/CODEOWNERS` names `@BenBotsch` instead
  of `@OWNER_OR_TEAM`. This deviates from R3: derived projects inherit the owner, and repository
  validation no longer reports an unset owner. `@OWNER_OR_TEAM` stays a placeholder token in
  `workflow.yml`, so a project that reintroduces it is still reported. `README.md` asks derived
  projects to check the owner. `FEAT-028` must replace the owner instead of a placeholder.
- Verified on 2026-11-10 in the test repository `BenBotsch/upt-smoke-2`, created from the template
  after the merge of PR #4 and bootstrapped with `New-ProjectRepository.ps1 -Apply`:
  `GET /repos/BenBotsch/upt-smoke-2/codeowners/errors?ref=main` returns no errors, and the
  community profile lists `.github/PULL_REQUEST_TEMPLATE.md` as `pull_request_template`. GitHub
  uses that file to pre-fill new pull requests; the pre-filled web form itself was not opened.
