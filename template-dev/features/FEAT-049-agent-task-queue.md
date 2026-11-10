---
id: "FEAT-049"
title: "Implement Agent Task Queue with agent Labels"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "medium"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§6.1", "§6.2", "§7.5", "§15.1"]
dependencies: ["FEAT-009", "FEAT-018"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-049: Implement Agent Task Queue with agent Labels

## Objective

Agents can query a prioritized queue of `agent:ready` issues and claim one safely; labels move
through `agent:ready` → `agent:working` → `agent:review-required` with validation at each step.

## Background

§15.1 lists an agent task queue (medium priority). §6.2 invariants for `agent:*`, §7.5 agent working
cycle.

## Scope

- Query script returning ranked issues as JSON; claim and release commands; stale-claim detection.

### Out of Scope

- Running agents (`FEAT-050`).

## Deliverables

| Path | Description |
|---|---|
| `scripts/agents/queue.py` | `list` (rank by priority, then age, dependencies resolved), `claim <n>` (sets `agent:working`, assigns, comments), `release <n>`, `submit <n> --pr <m>` (sets `agent:review-required`) |
| `.github/workflows/agent-queue-hygiene.yml` | Daily: `agent:working` without activity for N days gets a comment and `status:needs-info` |
| `docs/governance/agent-workflow.md` (section) | Queue usage |
| `tests/agents/**` | Ranking, claim conflict, blocked issues excluded |

## Requirements

1. **R1:** `claim` fails if the issue is already `agent:working` or has open blockers.
2. **R2:** Ranking is deterministic and documented.
3. **R3:** Commands use issue numbers only; no free text into shell.
4. **R4:** Every state change leaves a comment for traceability.

## Tasks

- [ ] **T1:** `list` with ranking.
- [ ] **T2:** `claim`/`release`/`submit` with tests.
- [ ] **T3:** Hygiene workflow.

## Acceptance Criteria

- [ ] Two concurrent claims on the same issue: one succeeds, one fails with a clear message.
- [ ] Issues with open blockers never appear in `list`.

## Verification

```text
python -I -m pytest tests/agents
python -I scripts/agents/queue.py list --repo <owner>/<repo> --format json
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** none for code; live use on real repos follows `DEC-10` once decided.
- **Pitfalls:** Label-based locking is not atomic; re-read after claim and back off on conflict.
