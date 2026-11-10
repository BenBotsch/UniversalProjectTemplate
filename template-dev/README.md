# Template Development Workspace

> **TEMPLATE-ONLY.** This folder plans and tracks the development of the
> `universal-project-template` itself. It must never reach a derived repository.
> Bootstrap (`FEAT-028`) deletes it during `init`, and repository validation (`FEAT-015`)
> fails if it still exists in a repository whose `.project/project.yml` does not set
> `project.is_template: true`.

## Why a separate folder

GitHub copies every file of a template repository into each derived repository. The `docs/`
tree is the clean scaffold that derived projects inherit, so it must not contain the
template's own tasks. Everything that only concerns building the template lives here.

Rule for all deliverables: files outside `template-dev/` must never link to or depend on
`template-dev/`. Derived repositories would otherwise contain dead links.

## Seed backlog

The specification (sections 5.11 and 12.5) makes GitHub Issues the operational source of truth
and forbids a second, manually maintained issue hierarchy in Markdown. No GitHub repository
exists yet, so this folder holds a **seed backlog**. `FEAT-048` migrates it into Issues and
sub-issues of the template repository (Issues are not copied into derived repositories). After the
migration, the feature files remain specifications, and status lives only in GitHub Issues.

## Contents

| File | Purpose |
|---|---|
| [specification.md](specification.md) | Verbatim source specification (German). Authoritative for intent. |
| [roadmap.md](roadmap.md) | Five phases, goals, exit gates, epic mapping |
| [backlog.md](backlog.md) | Single prioritized table of all features |
| [open-decisions.md](open-decisions.md) | Open architecture decisions and the features they block |
| [traceability.md](traceability.md) | Specification acceptance criteria and test cases mapped to features |
| [agent-implementation-guide.md](agent-implementation-guide.md) | How agents pick, implement, verify and report work |
| [epics/](epics/) | One file per epic |
| [features/](features/) | One specification per feature, plus [_template.md](features/_template.md) |
| [tools/](tools/) | Generator for backlog and epics, consistency verifier |

## Identifiers

| Prefix | Meaning | Example |
|---|---|---|
| `EPIC-NN` | Epic, a multi-feature initiative | `EPIC-03` |
| `FEAT-NNN` | Feature, the unit of backlog work | `FEAT-018` |
| `FEAT-NNN/Tn` | Task inside a feature, sized for one pull request | `FEAT-018/T3` |
| `DEC-NN` | Open architecture decision | `DEC-01` |
| `§x.y` | Section of [specification.md](specification.md) | `§6.5` |

IDs are stable. Do not renumber; mark obsolete features as `deprecated` instead.

## Feature status

Status values follow §12.2 and describe the specification file, not a GitHub issue state.

| Status | Meaning |
|---|---|
| `draft` | Specification incomplete; not ready for implementation |
| `planned` | Specified; may still wait for dependencies or decisions |
| `active` | Implementation in progress |
| `implemented` | All acceptance criteria met and merged |
| `deprecated` | Superseded or dropped; keep for history |
| `archived` | Closed and no longer relevant |

`agent_ready: true` additionally requires: clear scope and acceptance criteria, all
`dependencies` implemented, no open entry in `blocked_by_decisions`, and no action that needs
permissions an agent does not have (§6.2, §21.5).

## Target repositories

The specification (§16) describes three repositories plus a later dashboard. Each feature names its
`target_repo`. Until the separate repositories exist, code for `engineering-bootstrap` lives under
`tools/engineering-bootstrap/` of this repository (CLI command `project-bootstrap`, §13.7). Reusable
workflows for `engineering-workflows` are extracted only after `DEC-08` is decided (`FEAT-038`);
until then, workflows live in `.github/workflows/` and `profiles/` of this repository.

| `target_repo` | Content |
|---|---|
| `universal-project-template` | This repository: forms, labels, governance, base CI, config |
| `engineering-bootstrap` | Bootstrap CLI: `init`, `validate`, `sync-labels`, `audit` |
| `engineering-workflows` | Versioned reusable CI/CD workflows |
| `dashboard` | Cross-repository dashboard (phase 5) |
