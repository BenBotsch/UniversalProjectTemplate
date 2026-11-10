---
id: "FEAT-050"
title: "Add Low-Risk Agentic Workflows"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "low"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§7.6", "§11.1", "§15.2"]
dependencies: ["FEAT-018", "FEAT-049"]
blocked_by_decisions: ["DEC-10"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-050: Add Low-Risk Agentic Workflows

## Objective

Opt-in workflows let an AI agent suggest labels, point out missing acceptance criteria, analyze CI
failures, flag outdated docs and draft release notes, always as comments or reviewable PRs.

## Background

§15.2 lists low-risk agent jobs and requires suggestions and reviewable PRs first, no uncontrolled
productive changes, and a check of costs and data-processing terms. §11.1 agents: least privilege,
human approval, isolated execution. Blocked by `DEC-10` (identity, logging, approval of agent
actions).

## Scope

- One workflow per job type, each disabled by default via `.project/workflow.yml`.

### Out of Scope

- Agents that merge, release or change settings.

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/agent-triage-suggest.yml` | On issue opened: comment with suggested labels and missing sections |
| `.github/workflows/agent-ci-analysis.yml` | On failed `ci` run: comment on the PR with a probable cause |
| `.github/workflows/agent-docs-audit.yml` | Scheduled: opens PR or issue for stale docs |
| `.github/workflows/agent-release-draft.yml` | On release PR: comment with draft notes |
| `.project/workflow.yml` (section) | `agents.enabled_jobs: []`, provider, model, data policy note |
| `docs/governance/agent-permissions.md` (section) | Per-job permissions, identity per `DEC-10`, logging, cost note |

## Requirements

1. **R1:** All jobs off by default; enabling requires a config change in a reviewed PR.
2. **R2:** Permissions per job are the minimum: `issues: write` or `pull-requests: write`, never `contents: write` except the docs job that only opens PRs from a branch.
3. **R3:** Untrusted text is passed to the model as data and never executed; outputs are posted as text only.
4. **R4:** Each run uploads an audit-log artifact (inputs hash, prompt template version, output) per `DEC-10`.
5. **R5:** No secrets are passed to runs triggered by fork PRs.

## Tasks

- [ ] **T1:** Config section and permission doc after `DEC-10`.
- [ ] **T2:** Triage suggestion workflow.
- [ ] **T3:** CI analysis workflow.
- [ ] **T4:** Docs audit and release draft workflows.

## Acceptance Criteria

- [ ] With all jobs disabled, no agent workflow runs.
- [ ] Enabled triage job only comments and never changes labels.
- [ ] Agents work with least privilege and human approval (§17.3).

## Verification

```text
actionlint .github/workflows/agent-*.yml
zizmor .github/workflows/
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** resolving `DEC-10`; adding model provider secrets; enabling any job.
- **Pitfalls:** Prompt injection through issue text is expected; treat model output as untrusted too.
