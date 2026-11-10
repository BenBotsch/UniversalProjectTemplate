---
id: "FEAT-003"
title: "Create Documentation Scaffold, Index and ADR Process"
epic: "EPIC-01"
phase: 1
status: "implemented"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.1", "§3.2", "§7.4", "§12.1", "§12.2", "§12.3", "§12.4", "§12.5", "§21.4"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-003: Create Documentation Scaffold, Index and ADR Process

## Objective

Derived projects inherit a lean `docs/` tree with a short index, a feature-spec template with
machine-readable frontmatter, an ADR template and ADR-0001. The tree contains no template tasks.

## Background

§12.1 defines the documentation areas, §12.2 the frontmatter, §12.3 the index, §12.4 the ADR
structure, §12.5 the single-source-of-truth rule. §21.4 warns against many empty pages: create only
files with real content. The template's own backlog lives in `template-dev/` and is removed on
bootstrap; `docs/` is what derived projects keep.

## Scope

- `docs/INDEX.md` listing only directories that contain files. `docs/governance/issue-management.md` already exists (label taxonomy from `FEAT-008`) and must be listed. Root `AGENTS.md` (`FEAT-004`) must be listed as the first entry of the agent reading order.
- Minimal, real content per area that is meaningful for every project.
- ADR template and `ADR-0001` (GitHub Issues as operational source of truth).
- Feature-spec template and a planning README for derived projects.

### Out of Scope

- Governance documents of `FEAT-006`, `FEAT-009`, `FEAT-012` (they add their own files and one line each to `docs/INDEX.md`).
- Product content (derived projects write it).

## Deliverables

| Path | Description |
|---|---|
| `docs/INDEX.md` | Compact index per §12.3; one line per existing area; reading order for agents (§7.4) |
| `docs/architecture/adr/README.md` | ADR process: when to write one, numbering, statuses (`proposed`, `accepted`, `superseded`, `deprecated`) |
| `docs/architecture/adr/0000-adr-template.md` | Template with frontmatter `id`, `title`, `status`, `created_at`, `related_issues` |
| `docs/architecture/adr/0001-use-github-issues.md` | ADR-0001 per §12.4 |
| `docs/features/README.md` | How feature specs relate to issues; document statuses `draft..archived` (§12.2) are not issue states |
| `docs/features/_template.md` | Feature spec template with §12.2 frontmatter |
| `docs/planning/README.md` | Roadmaps and milestones live here; work items live in GitHub Issues (§12.5) |

## Requirements

1. **R1:** `docs/INDEX.md` lists only directories that exist and contain at least one file.
2. **R2:** Every frontmatter in templates uses ISO 8601 dates and the exact keys of §12.2.
3. **R3:** Document statuses are defined in `docs/features/README.md` and explicitly distinguished from issue states.
4. **R4:** No file in `docs/` references `template-dev/`.
5. **R5:** No empty placeholder pages (§21.4).

## Tasks

- [x] **T1:** Write `docs/INDEX.md` with a "How to read this repository" section for agents.
- [x] **T2:** Write ADR README, ADR template and ADR-0001.
- [x] **T3:** Write `docs/features/README.md`, `docs/features/_template.md`, `docs/planning/README.md`.

## Acceptance Criteria

- [x] Project documentation can be found via a short index (§17.3).
- [x] Significant architectural changes use ADRs: the process and template exist (§17.3).
- [x] `docs/planning/` and `docs/features/` contain only README and template files, no template tasks.
- [x] All relative links in `docs/` resolve.

## Verification

```text
grep -rn "template-dev" docs/        # must be empty
# link check: markdown-link-check or lychee --offline docs/ (wired up by FEAT-016)
```

## Agent Notes

- **Allowed paths:** `docs/INDEX.md`, `docs/architecture/adr/**`, `docs/features/**`, `docs/planning/README.md`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** `docs/INDEX.md` is touched by several features. This feature owns its structure; other features add one line in the matching section. `docs/governance/` files belong to `FEAT-006`, `FEAT-009` and `FEAT-012`.
