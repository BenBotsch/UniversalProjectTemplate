---
id: "FEAT-018"
title: "Implement Issue Validator and Issue Validation Workflow"
epic: "EPIC-06"
phase: 2
status: "active"
priority: "high"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§5.2", "§6.2", "§6.3", "§6.5", "§21.5", "§21.6"]
dependencies: ["FEAT-007", "FEAT-008", "FEAT-009", "FEAT-014"]
blocked_by_decisions: []
agent_ready: true
related_issues: ["#20"]
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-018: Implement Issue Validator and Issue Validation Workflow

## Objective

Every issue event is validated against the label invariants and type-specific required sections;
violations set `status:needs-info` and update one bot comment instead of spamming.

## Background

§6.5 defines triggers and the eight-step algorithm plus security rules (issue text is untrusted,
minimal `issues: write`). §6.2 invariants, §6.3 lifecycle, §21.5 policy schema, §21.6 test cases.
Forms do not protect API-created issues (§5.2). Native issue types (`DEC-04`) are out of scope;
initial labels follow `DEC-05` default.

## Scope

- Pure validation library (input: issue JSON + policy; output: findings) with unit tests.
- Thin workflow adapter that reads the event payload from file and applies labels/comments via API.

### Out of Scope

- Severity-to-priority suggestion (`FEAT-022`), periodic audit across repos (`FEAT-051`).

## Deliverables

| Path | Description |
|---|---|
| `scripts/ci/issue_validation/validator.py` | Rules mapped to `ISSUE-R*` IDs from `FEAT-009` |
| `scripts/ci/issue_validation/run.py` | Reads `$GITHUB_EVENT_PATH`, calls validator, upserts comment marked `<!-- issue-validation -->`, sets/removes `status:needs-info` |
| `.github/workflows/issue-validation.yml` | `on: issues [opened, edited, labeled, unlabeled, reopened]`; `permissions: issues: write`; concurrency per issue number |
| `tests/ci/issue_validation/**` | One test per §21.6 issue case and per rule |

## Requirements

1. **R1:** Implements: exactly one `type:*`; exactly one `status:*` on open issues; at most one `priority:*`, exactly one from `status:ready` on; at most one `effort:*`; at least one `area:*` from `status:ready` on; `agent:ready` and `agent:working` not together.
2. **R2:** Type-specific sections: parses headings produced by the forms (`FEAT-007` mapping) and reports empty required sections, e.g. Bug without "Steps to Reproduce".
3. **R3:** `agent:ready` requires acceptance criteria and scope sections, no open "blocked by" dependency (via API), and no `status:blocked`.
4. **R4:** `status:blocked` requires a blocker reference (`#123` or dependency link).
5. **R5:** Exactly one bot comment per issue, updated in place; removed or marked resolved when all rules pass, and `status:needs-info` is removed only if the bot added it.
6. **R6:** Issue title/body are read from the event JSON file, never interpolated into shell commands.
7. **R7:** API errors (rate limit, 403) fail the job with a clear message; they are never reported as "valid".
8. **R8:** Bot-triggered events (own label changes) do not cause infinite loops.

## Tasks

- [x] **T1:** Validator library for label invariants with tests.
- [x] **T2:** Section parsing per type with tests.
- [x] **T3:** Dependency and `agent:ready` checks with API mocks.
- [x] **T4:** Runner with comment upsert and label handling; loop protection.
- [ ] **T5:** Workflow file; manual test in a test repository.

## Acceptance Criteria

- [x] Required issue fields are validated (§17.2).
- [x] Exactly one type label and one status label are enforced by validation (§17.2).
- [x] Priority and other required metadata are validated according to policy (§17.2).
- [x] Conflicting labels are detected and reported (§17.2).
- [x] §21.6 cases pass: issue without `type:*` fails; two `priority:*` fail; Bug without reproduction steps fails and gets `status:needs-info`; `agent:ready` with open blockers fails.

## Verification

```text
python -I -m pytest tests/ci/issue_validation
actionlint .github/workflows/issue-validation.yml
# Manual in test repo: create an issue via `gh issue create` without labels; bot comment appears; add labels; comment resolves.
```

## Agent Notes

- **Allowed paths:** `scripts/ci/issue_validation/**`, `tests/ci/issue_validation/**`, `.github/workflows/issue-validation.yml`, this feature file, backlog status.
- **Requires approval:** creating issues in a real repository for the manual test.
- **Pitfalls:** §19: forms do not cover API paths; labels added by `GITHUB_TOKEN` do not trigger new workflow runs, which helps against loops but means re-validation needs the `edited`/`labeled` event from a user.

## Implementation Notes

- **Decisions (issue #20):** the rules come from `issue_policy` in `.project/workflow.yml`, the
  label groups in `.project/labels.yml` and the required fields of the issue forms, so a derived
  project changes the policy without code changes. Every finding carries its `ISSUE-R*` ID.
  Section parsing reuses `parse_sections` from `pr_validation/validator.py`; `_No response_`, HTML
  comments and headings inside code fences count as empty or absent. `agent:ready` (R3) looks for
  an acceptance and a scope heading by keyword, so it also works for issues not created from a
  form. `status:blocked` (R4) accepts a "blocked by" dependency or a `#123`, `owner/repo#123` or
  issue URL reference in the body or a comment.
- **Comment and labels (R5):** the runner finds its comment by the marker *and* the workflow's own
  login, so a copied marker is ignored. A second marker in the comment records that the validator
  set `status:needs-info`; only then does it remove the label and restore `status:triage`. An
  open issue without any status label gets `status:triage`.
- **Exit codes (R7):** findings do not fail the job; they are in the comment and the job summary.
  The job fails with exit `1` for an API error, with a rate-limit or `issues: write` hint, and
  with exit `2` for an invalid event file.
- **Deviations:** `ISSUE-R10` (closed issues) is left to review, because the validator skips
  closed issues. `priority` and `effort` were added to `optional_single_label_groups` in
  `.project/workflow.yml` (outside the allowed paths) so that "at most one" is policy, not code.
  `docs/governance/issue-management.md` and `scripts/ci/README.md` describe the validator.
- **Verification so far:** unit tests for every rule and §21.6 case, the runner against a fake
  API client and `UrllibClient` against a local HTTP server; `actionlint`, `zizmor` and
  `yamllint` on the workflow.
- **Open:** T5's manual test in `BenBotsch/upt-smoke-public` needs approval for creating issues
  there and a merge of the workflow into that repository's default branch, because `issues`
  events run the workflow file of the default branch. The feature stays `active` until then.
