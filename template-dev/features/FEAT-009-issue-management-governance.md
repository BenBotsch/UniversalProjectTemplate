---
id: "FEAT-009"
title: "Document Issue Management Rules and Lifecycle"
epic: "EPIC-03"
phase: 1
status: "implemented"
priority: "high"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§5.1", "§5.10", "§5.11", "§6.2", "§6.3", "§6.6", "§21.5"]
dependencies: ["FEAT-003", "FEAT-008"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-009: Document Issue Management Rules and Lifecycle

## Objective

`docs/governance/issue-management.md` defines issue types, label invariants, the status lifecycle,
severity vs. priority, hierarchy and dependencies, so humans, agents and the validator (`FEAT-018`)
apply the same rules.

## Background

§5.1 types and mandatory content, §5.10 security work, §5.11 hierarchy with native sub-issues and
"blocked by" dependencies, §6.2 invariants, §6.3 lifecycle, §6.6 severity is not priority, §21.5
proposed policy schema.

## Scope

- One governance document; it is the human-readable counterpart of `issue_policy` in
  `.project/workflow.yml` (`FEAT-013`).

### Out of Scope

- Executable validation (`FEAT-018`).

## Deliverables

| Path | Description |
|---|---|
| `docs/governance/issue-management.md` | Sections: Issue Types, Label Taxonomy (from `FEAT-008`), Metadata Invariants, Status Lifecycle (diagram from §6.3), Severity vs. Priority, Hierarchy and Dependencies, Security Work, Form Field Mapping (from `FEAT-007`), Triage Procedure |
| `docs/INDEX.md` | One line under Governance |

## Requirements

1. **R1:** Every invariant of §6.2 is listed as a numbered rule with an ID (`ISSUE-R1`...), so the validator can report rule IDs.
2. **R2:** The lifecycle lists allowed transitions explicitly as a table (from → to).
3. **R3:** States that `closed` is the native state and no `status:done` label exists.
4. **R4:** States that no second issue hierarchy is maintained in Markdown (§5.11).
5. **R5:** Security work: vulnerabilities go through `SECURITY.md`; non-confidential hardening uses `type:task` + `area:security` (§5.10).
6. **R6:** Initial label defaults follow `DEC-05` default and name it as provisional.

## Tasks

- [x] **T1:** Write the document with rule IDs and transition table.
- [x] **T2:** Integrate the sections delivered by `FEAT-007` and `FEAT-008` (or create the file first and let them add sections).

## Acceptance Criteria

- [x] Each §6.2 invariant has a rule ID used later by `FEAT-018` error messages.
- [x] Parent-child relationships and blockers can be recorded: the procedure with native sub-issues and dependencies is documented (§17.2).

## Verification

```text
grep -c "ISSUE-R" docs/governance/issue-management.md   # >= 9
```

## Agent Notes

- **Allowed paths:** `docs/governance/issue-management.md`, `docs/INDEX.md` (one line), this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** `FEAT-007`, `FEAT-008` and this feature edit the same file. Whoever starts first creates it with all section headings; the others fill only their section.
