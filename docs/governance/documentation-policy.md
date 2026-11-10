# Documentation Policy

Documentation is part of a change, not a follow-up. A pull request that changes behavior or an
interface updates the affected documents in the same pull request.

## Where Information Lives

Every kind of information has exactly one authoritative source, listed in
[Sources of Truth](../INDEX.md#sources-of-truth):

- **GitHub Issues** hold operational status: who works on what, with which priority, in which
  state, linked to which pull requests.
- **Markdown** in this repository holds specifications, architecture, rules and long-lived
  decisions.
- **`.project/`** holds repository and tooling configuration.
- **Releases and tags** hold the published versions.

Consequences:

- Do not track status, assignments or progress in Markdown files. Link to the issue instead.
- Do not copy configuration values into prose. Name the file and field, for example
  `branching.branch_name_pattern` in `.project/workflow.yml`. Where a value must be quoted, quote
  it exactly and name its source.
- Link to an existing document instead of copying its content.
- Where the same information must be shown in more than one place, generate it from the source
  instead of maintaining copies.

## When to Update Documentation

| Change | Update |
|---|---|
| New or changed user-visible behavior | [README.md](../../README.md) or the user documentation, and [CHANGELOG.md](../../CHANGELOG.md) under `Unreleased` |
| New or changed command, option, configuration field or environment variable | The document that describes it, and examples that use it |
| Changed public interface, file format or schema | The interface documentation; a migration note for incompatible changes |
| Changed setup, build or test commands | [CONTRIBUTING.md](../../CONTRIBUTING.md) and the technology profile documentation |
| Changed working rule for contributors or agents | [AGENTS.md](../../AGENTS.md) and the governance document that details it |
| Changed `.project/` structure | The schema, [.project/README.md](../../.project/README.md) and a migration note |
| New, moved or deleted document | [docs/INDEX.md](../INDEX.md) and every link to it |
| Feature specification changes | The feature document in [docs/features/](../features/README.md) |
| Internal change without visible effect | Comments only where the reason is not obvious from the code |

## ADR Triggers

Record an [Architecture Decision Record](../architecture/adr/README.md) when a decision:

- Selects or replaces a framework, language, platform, database or other major dependency.
- Changes the structure of the system: module boundaries, layering, communication between
  components or a public interface.
- Changes a cross-cutting policy, for example the merge strategy, versioning, security model or
  data retention.
- Is hard to reverse, or was made between alternatives that reviewers would reasonably question.

An ADR is not changed after acceptance. A new decision supersedes it with a new ADR.

## No New Control Files

Do not create new files that steer agents or tools, such as additional rule files, status lists
or task trackers, unless an issue asks for it. Rules go into `AGENTS.md` or the governance
document they belong to; configuration goes into `.project/`; status goes into GitHub Issues. A
tool-specific adapter file contains only a reference to `AGENTS.md`, as described in
[Agent Adapter Files](agent-workflow.md#agent-adapter-files).

## Document Conventions

- Documentation is written in English.
- Each document has one purpose and a descriptive title. Prefer a few well-linked documents over
  many short or empty ones.
- Links are relative so that they work in clones and forks.
- Documents with frontmatter, such as feature specifications and ADRs, keep it complete and up to
  date.
