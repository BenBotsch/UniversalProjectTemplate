---
id: "FEAT-045"
title: "Document Self-Hosted Runner Trust Model"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "low"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§11.2", "§11.3", "§14.4"]
dependencies: ["FEAT-017"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-045: Document Self-Hosted Runner Trust Model

## Objective

The template documents when self-hosted runners are allowed, how they are isolated, and CI checks
that untrusted events never target them.

## Background

§11.3 lists five rules (no public fork PRs on persistent private runners, prefer hosted or ephemeral
runners, no personal credentials, limited secrets and network, no untrusted code into deploy
context). §14.4: do not trade security for cost.

## Scope

- Policy document and a workflow check.

### Out of Scope

- Runner provisioning automation.

## Deliverables

| Path | Description |
|---|---|
| `docs/governance/self-hosted-runners.md` | §11.3 rules, decision tree, label conventions (`self-hosted`, `ephemeral`) |
| `scripts/ci/check_runner_usage.py` | Fails if a job with `runs-on` containing `self-hosted` can be triggered by `pull_request` from forks or `pull_request_target`, unless allowlisted with justification |
| `tests/ci/test_check_runner_usage.py` | Allowed and forbidden combinations |

## Requirements

1. **R1:** Check runs in `security.yml`.
2. **R2:** Allowlist entries require a comment with reason and owner.

## Tasks

- [ ] **T1:** Policy document.
- [ ] **T2:** Check script with tests and job.

## Acceptance Criteria

- [ ] A workflow running fork PRs on a `self-hosted` runner fails the check.

## Verification

```text
python -I -m pytest tests/ci/test_check_runner_usage.py
```

## Agent Notes

- **Allowed paths:** files listed above, `security.yml` job, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** registering any real runner.
- **Pitfalls:** Static analysis of `if:` conditions is limited; prefer a conservative failure.
