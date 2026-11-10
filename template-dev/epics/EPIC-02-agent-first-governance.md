---
id: "EPIC-02"
title: "Agent-First Governance"
phase: 1
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-02: Agent-First Governance

## Goal and Value

Make the repository safe and predictable for coding agents: one authoritative `AGENTS.md`, thin tool adapters and written agent workflow, permission and documentation policies.

## Scope and Deliverables

- Root `AGENTS.md` with Definition of Done (§7.2)
- `CLAUDE.md` and `.github/copilot-instructions.md` as thin adapters (§7.3)
- Agent workflow, permission matrix and documentation policy (§7.4-§7.6)

## Non-Goals

- Running agents or agent automation (EPIC-11)

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-004](../features/FEAT-004-agents-md.md) | Write Root AGENTS.md | 1 | critical | 001 | implemented |
| [FEAT-005](../features/FEAT-005-agent-adapter-files.md) | Add Thin Agent Adapter Files | 1 | high | 004 | implemented |
| [FEAT-006](../features/FEAT-006-agent-governance-docs.md) | Write Agent Workflow, Permissions and Documentation Policy | 1 | high | 003, 004 | implemented |

## Risks and Dependencies

- Divergent rules between adapters and `AGENTS.md`; adapters must only point to it
- Permission rules that tooling cannot enforce; mark which rules are enforced where
- External feature dependencies: `FEAT-001`, `FEAT-003`
- Blocking decisions: none (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- An agent can find all rules from `AGENTS.md` within two links
- Adapters contain no rule that is not in `AGENTS.md`
