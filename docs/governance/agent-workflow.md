# Agent Workflow

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
