---
id: "FEAT-004"
title: "Write Root AGENTS.md"
epic: "EPIC-02"
phase: 1
status: "implemented"
priority: "critical"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§7.1", "§7.2", "§7.4", "§7.6", "§19"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-004: Write Root AGENTS.md

## Objective

A concise root `AGENTS.md` defines the mandatory working rules for humans and AI coding agents in
every derived repository.

## Background

§7.2 provides the reference content (Purpose, Language, Before Starting Work, Branching, Commits,
Implementation, Quality, Security, Documentation, Definition of Done, Agent Boundaries, Reporting,
Project-Specific Instructions). §7.1 requires it to be the single core rule set; adapter files only
point to it (`FEAT-005`). §7.4 requires token efficiency.

## Scope

- Root `AGENTS.md` based on §7.2, tightened for brevity.
- Precedence rule for nested `<module>/AGENTS.md` files.

### Out of Scope

- Detailed workflow and permission tables (`FEAT-006` in `docs/governance/`).
- Tool-specific adapter files (`FEAT-005`).

## Deliverables

| Path | Description |
|---|---|
| `AGENTS.md` | All §7.2 sections; links to `docs/INDEX.md`, `docs/governance/agent-workflow.md`, `docs/governance/agent-permissions.md` |

## Requirements

1. **R1:** Contains every section of §7.2 with equivalent rules; wording may be shortened, not weakened.
2. **R2:** Commit types match §9.1 exactly: `feat, fix, refactor, perf, docs, test, build, ci, chore`.
3. **R3:** Agent boundaries list merge, tag/publish, security/access settings, deletion of data/production resources, unrelated refactors, self-approval of sensitive changes (§7.2, §7.6).
4. **R4:** States that local `AGENTS.md` files may add rules but never override repository-wide security policy.
5. **R5:** Under 200 lines; no duplication of content that lives in `docs/governance/`.
6. **R6:** Project-specific commands are referenced, not guessed ("use project-defined build and test commands").

## Tasks

- [x] **T1:** Write `AGENTS.md`.
- [x] **T2:** Add the `AGENTS.md` line to `docs/INDEX.md` if `FEAT-003` is merged; otherwise note it in the PR for `FEAT-003`.

## Acceptance Criteria

- [x] `AGENTS.md` contains repository-wide development rules (§17.3).
- [x] Agents can identify the relevant issue and acceptance criteria from the "Before Starting Work" section (§17.3).
- [x] Agents report actual tests, changes, remaining risks and references (Reporting section, §17.3).
- [x] Linked governance files exist or are tracked by `FEAT-006` (link check passes once both are merged).

## Verification

```text
wc -l AGENTS.md                     # < 200
grep -n "feat, fix, refactor, perf, docs, test, build, ci, chore" AGENTS.md
```

## Agent Notes

- **Allowed paths:** `AGENTS.md`, one line in `docs/INDEX.md`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** §19 "agent instructions contradict each other": keep `AGENTS.md` the only core reference. Do not copy the user's personal global rules into the template.
