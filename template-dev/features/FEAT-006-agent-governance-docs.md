---
id: "FEAT-006"
title: "Write Agent Workflow, Permissions and Documentation Policy"
epic: "EPIC-02"
phase: 1
status: "implemented"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§7.3", "§7.4", "§7.5", "§7.6", "§12.5", "§21.4"]
dependencies: ["FEAT-003", "FEAT-004"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-006: Write Agent Workflow, Permissions and Documentation Policy

## Objective

`docs/governance/` explains the detailed agent working cycle, the permission and approval model,
and when documentation must be updated.

## Background

§7.3 names `agent-workflow.md`, `agent-permissions.md` and `documentation-policy.md`. §7.5 defines
the working cycle, §7.6 the permission matrix, §7.4 the three-level knowledge structure, §12.5 the
single source of truth.

## Scope

- Three governance documents.
- How approval rules map to technical controls (branch rules, minimal tokens, environments,
  protected secrets, separate roles; §7.6 last paragraph).

### Out of Scope

- Automating `agent:*` labels (`FEAT-049`) and agentic workflows (`FEAT-050`).
- The "Agent Adapter Files" section with "Verifying Adapter Pickup" in `agent-workflow.md`,
  already written by `FEAT-005`; keep it and add the remaining content around it.

## Deliverables

| Path | Description |
|---|---|
| `docs/governance/agent-workflow.md` | §7.5 cycle as numbered steps; reading strategy from §7.4; branch naming; PR evidence requirements; reporting format |
| `docs/governance/agent-permissions.md` | §7.6 matrix as a table; mapping of each restricted action to the enforcing control; escalation procedure |
| `docs/governance/documentation-policy.md` | Which changes require which doc updates; ADR triggers; single source of truth table (§12.5); rule against new redundant control files |
| `docs/INDEX.md` | One line per new file under Governance |

## Requirements

1. **R1:** The permission matrix contains every row of §7.6 with both columns.
2. **R2:** Every "No" or "Yes (additional approval)" row names at least one enforcing control or states that enforcement is organizational only.
3. **R3:** The documentation policy states that GitHub Issues hold operational status and Markdown holds specifications (§12.5).
4. **R4:** No rule contradicts `AGENTS.md`; where detail is added, `AGENTS.md` remains the summary.

## Tasks

- [x] **T1:** Write `agent-workflow.md`.
- [x] **T2:** Write `agent-permissions.md`.
- [x] **T3:** Write `documentation-policy.md` and update `docs/INDEX.md`.

## Acceptance Criteria

- [x] Agent write, merge, release and destructive operations are permission-controlled, and the controls are documented (§17.3).
- [x] Relevant documentation is updated for behavior changes: the policy defines when (§17.3).
- [x] `AGENTS.md` links resolve to these files.

## Verification

```text
grep -c "^|" docs/governance/agent-permissions.md    # matrix rows present
# link check over docs/ and AGENTS.md
```

## Agent Notes

- **Allowed paths:** the three files, `docs/INDEX.md` (Governance lines), this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Do not promise technical enforcement that GitHub Free private repos cannot deliver (§14.3, §14.4); say "organizational control" where applicable.
