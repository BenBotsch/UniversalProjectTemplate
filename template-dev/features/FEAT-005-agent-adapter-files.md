---
id: "FEAT-005"
title: "Add Thin Agent Adapter Files"
epic: "EPIC-02"
phase: 1
status: "implemented"
priority: "high"
effort: "xs"
target_repo: "universal-project-template"
spec_refs: ["§7.1", "§7.3"]
dependencies: ["FEAT-004"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-005: Add Thin Agent Adapter Files

## Objective

Claude Code and GitHub Copilot find the shared rules through thin adapter files that point to
`AGENTS.md` without duplicating it.

## Background

Not every agent reads every instruction file with the same priority (§7.1). §7.3 gives minimal
examples for `CLAUDE.md` and `.github/copilot-instructions.md`.

## Scope

- `CLAUDE.md` and `.github/copilot-instructions.md`.
- A documented test procedure that each tool actually picks up the rules.

### Out of Scope

- Adapters for other tools (can be added later following the same pattern).

## Deliverables

| Path | Description |
|---|---|
| `CLAUDE.md` | Per §7.3: read `AGENTS.md`, use `docs/INDEX.md`, do not override security policy |
| `.github/copilot-instructions.md` | Per §7.3: follow `AGENTS.md`, read `docs/INDEX.md`, do not invent test results |
| `docs/governance/agent-workflow.md` (section) | "Verifying adapter pickup" subsection, coordinated with `FEAT-006` |

## Requirements

1. **R1:** Each adapter is at most 15 lines and contains no rule that is not in `AGENTS.md`, except tool-specific mechanics.
2. **R2:** Both files reference `AGENTS.md` and `docs/INDEX.md` by relative path.
3. **R3:** A manual pickup test is documented: ask each tool "Which commit types are allowed in this repository?" and expect the `AGENTS.md` list.

## Tasks

- [x] **T1:** Write both adapter files.
- [x] **T2:** Document and run the pickup test for Claude Code; record the result in the PR.

## Acceptance Criteria

- [x] Claude Code and Copilot can access relevant shared instructions (§17.3).
- [x] Agent-specific files do not duplicate core rules unnecessarily (§17.3).

## Verification

```text
wc -l CLAUDE.md .github/copilot-instructions.md     # each <= 15
# Manual: run the pickup question in Claude Code; paste answer into PR "Tests Executed".
```

## Agent Notes

- **Allowed paths:** `CLAUDE.md`, `.github/copilot-instructions.md`, the subsection in `docs/governance/agent-workflow.md`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Copilot pickup cannot be tested without a Copilot seat; report it as "not executed" if unavailable.

## Implementation Notes

- Claude Code pickup test (2026-11-10): the maintainer ran a new Claude Code session in the test
  repository `BenBotsch/upt-smoke-2` and confirmed that it followed `AGENTS.md`. The answer was not
  recorded verbatim.
- Copilot pickup: not executed (no Copilot session was used). `.github/copilot-instructions.md` uses
  the documented repository instruction file and only links `AGENTS.md` and `docs/INDEX.md`.
- Duplication (R1, R2): `CLAUDE.md` (12 lines) imports `AGENTS.md`, and
  `.github/copilot-instructions.md` (9 lines) links it; neither adds a rule of its own.
