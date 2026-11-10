---
id: "EPIC-11"
title: "Agents and Dashboard"
phase: 5
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-11: Agents and Dashboard

## Goal and Value

Bounded, traceable agent automation and a cross-repository dashboard built on exported data.

## Scope and Deliverables

- Agent task queue (§15.1)
- Low-risk agentic workflows (§15.2, `DEC-10`)
- `audit --owner` (§13.7, §15.4)
- Dashboard data model, MVP and controlled script execution (§15.3, §2.4, §16.6, `DEC-09`, `DEC-10`)

## Non-Goals

- Agents that merge, release or change settings

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-049](../features/FEAT-049-agent-task-queue.md) | Implement Agent Task Queue with agent Labels | 5 | medium | 009, 018 | planned |
| [FEAT-050](../features/FEAT-050-agentic-workflows.md) | Add Low-Risk Agentic Workflows | 5 | low | 018, 049 | planned |
| [FEAT-051](../features/FEAT-051-cross-repo-audit.md) | Audit All Repositories of an Owner | 5 | medium | 029 | planned |
| [FEAT-052](../features/FEAT-052-dashboard-data-model.md) | Define Dashboard Data Model and Export | 5 | medium | 013, 051 | planned |
| [FEAT-053](../features/FEAT-053-dashboard-mvp.md) | Build Read-Only Dashboard MVP | 5 | low | 052 | planned |
| [FEAT-054](../features/FEAT-054-controlled-script-execution.md) | Allow Controlled Execution of Declared Scripts | 5 | low | 053 | planned |

## Risks and Dependencies

- Prompt injection via issue text
- Script execution is the highest-risk feature; strict declaration and approval
- External feature dependencies: `FEAT-009`, `FEAT-013`, `FEAT-018`, `FEAT-029`
- Blocking decisions: `DEC-09`, `DEC-10` (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- Agent actions are traceable, bounded and reviewable
- The dashboard covers several repositories consistently
