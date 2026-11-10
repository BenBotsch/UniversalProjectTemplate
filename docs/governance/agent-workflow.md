# Agent Workflow

This document details how coding agents work in this repository. [AGENTS.md](../../AGENTS.md)
is the binding summary; this document adds procedure, not new rules. Permissions and approvals are
defined in [Agent Permissions](agent-permissions.md).

## Working Cycle

```text
Receive issue
   |
Read required context and acceptance criteria
   |
Find related code, tests, interfaces and dependencies
   |
Plan minimal scoped change
   |
Implement on feature/fix branch
   |
Run tests, lint, security checks
   |
Update affected docs and ADR (if needed)
   |
Create PR with issue reference, evidence and risk summary
   |
Human/authorized review and CI gates
   |
Merge and update issue status
```

1. **Receive the issue.** Work starts from a GitHub issue in `status:ready`. An issue labeled
   `agent:ready` meets the requirements of rule ISSUE-R8 in
   [Issue Management](issue-management.md#metadata-invariants). Do not start nontrivial work
   without an issue and acceptance criteria; ask instead.
2. **Read the required context** with the [reading strategy](#reading-strategy) below: the issue,
   its acceptance criteria, its parent and its blockers.
3. **Find related code**, tests, interfaces and dependencies. Search for existing
   implementations before writing new ones.
4. **Plan a minimal change** that satisfies the acceptance criteria. For nontrivial work, write
   the plan down, for example in the issue or the pull request description. Note risks and
   affected interfaces.
5. **Implement on a work branch** created from `develop`, named
   `<purpose>/<issue-number>-<short-summary>`; see
   [Branch Names](branching-and-releases.md#branch-names). Commit with
   [Conventional Commits](commit-conventions.md).
6. **Run the checks** defined by the project: format, lint, type check, build, tests and security
   checks. The commands are listed in [CONTRIBUTING.md](../../CONTRIBUTING.md#tests-and-checks).
   Fix failures; never skip or weaken a check.
7. **Update affected documentation** and write an ADR where the
   [documentation policy](documentation-policy.md) requires one.
8. **Open a pull request** against `develop` with the [evidence](#pull-request-evidence) below.
9. **Review and CI gates.** A human or an authorized reviewer reviews the pull request; required
   checks must pass. See the [Review Policy](review-policy.md).
10. **Merge and update the issue.** An authorized person merges. The issue status is updated
    as described in the [status lifecycle](issue-management.md#status-lifecycle). An agent
    merges only with explicit authorization; see [Agent Permissions](agent-permissions.md).

If work cannot continue, set `status:blocked`, name the blocker and stop instead of working
around it.

## Reading Strategy

Knowledge is organized in three levels. Read from the top and stop as soon as the task is clear:

1. **Root:** short central rules: [AGENTS.md](../../AGENTS.md), [README.md](../../README.md),
   [docs/INDEX.md](../INDEX.md).
2. **Area:** only the documents relevant to the task, for example `docs/architecture/` or
   `docs/governance/`.
3. **Module:** local `AGENTS.md` files in subdirectories, only for the modules you change.

Procedure: read the index, locate the relevant files, read the relevant sections, and update
the affected documents when you change something. Do not load the whole repository into context
for a small task.

## Pull Request Evidence

The pull request template defines the sections. For agents, these sections must contain:

- **Related Issues:** `Refs: #<number>`, or `No-Issue: <reason>` if there is no issue.
- **Implementation Details:** the changes made and the files affected, and decisions a reviewer
  must know about.
- **Tests Executed:** the commands actually run and their actual output or result. Checks that
  were skipped are listed with the reason. Never report an unexecuted check as passed.
- **Risks and Rollback:** remaining risks, limitations and follow-up actions.

## Reporting Format

Every pull request description and final agent message summarizes the items listed under
"Reporting" in [AGENTS.md](../../AGENTS.md#reporting):

```text
Changes:   <what changed, files affected>
Checks:    <command> -> <result>, for each executed check
Skipped:   <check> -> <reason>, or "none"
Risks:     <remaining risks, limitations, follow-ups>, or "none"
Refs:      #<issue>, #<pull request>
```

## Agent Adapter Files

[AGENTS.md](../../AGENTS.md) is the only rule set. Some tools read their own instruction file first,
so the repository contains thin adapters that only point to `AGENTS.md`:

| Tool | Adapter | Mechanism |
|---|---|---|
| Claude Code | [CLAUDE.md](../../CLAUDE.md) | Loaded at session start; imports `AGENTS.md` with `@AGENTS.md` |
| GitHub Copilot | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | Repository custom instructions; links to `AGENTS.md` |

Rules for adapters:

- An adapter has at most 15 lines.
- It contains no rule that is not in `AGENTS.md`, except tool-specific mechanics such as an import.
- It references `AGENTS.md` and `docs/INDEX.md` by relative path.
- To support another tool, add an adapter that follows the same pattern and add it to this table.

### Verifying Adapter Pickup

Not every tool reads every instruction file, or with the same priority. Verify pickup after you
add or change an adapter, and after a major tool update:

1. Start a **new** session of the tool in a fresh clone of the repository, so that no earlier
   context is reused.
2. Ask: "Which commit types are allowed in this repository?"
3. Expected answer: the list from `AGENTS.md`: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`,
   `build`, `ci`, `chore`.
4. Record the tool, its version, the date and the answer in the "Tests Executed" section of the
   pull request. If a tool is not available, for example without a Copilot seat, record the check
   as not executed.

A wrong or generic answer means the tool did not pick up the rules. Check the tool's documentation
for the file it reads, and fix the adapter instead of copying rules into it.
