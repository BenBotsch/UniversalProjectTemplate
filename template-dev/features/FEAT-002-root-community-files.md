---
id: "FEAT-002"
title: "Write Root Community and Policy Files"
epic: "EPIC-01"
phase: 1
status: "active"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.1", "§3.2", "§5.10", "§9.4", "§11.4", "§17.1", "§21.1", "§21.2", "§21.3"]
dependencies: ["FEAT-001"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-002: Write Root Community and Policy Files

## Objective

The template ships `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md` and `CHANGELOG.md`
with the minimum content required by the specification, plus a documented license-selection rule.

## Background

§21.2 defines the README minimum structure, §21.3 the CONTRIBUTING minimum content, §11.4 the
SECURITY minimum content, §9.4 the Keep-a-Changelog orientation. A license must be selected
explicitly per project (§3.1, §19); the template must not silently impose one.

## Scope

- Template versions of the five files, written in English, using placeholders `PROJECT_NAME`,
  `PROJECT_DESCRIPTION`, `OWNER`, `REPOSITORY` that bootstrap replaces (`FEAT-028`).
- License rule: how a derived project chooses its license.

### Out of Scope

- The `LICENSE` file content for derived projects (selected during bootstrap).
- Badges that do not work before bootstrap (§21.2).

## Deliverables

| Path | Description |
|---|---|
| `README.md` | §21.2 structure: Features, Supported Platforms, Technology Stack, Requirements, Quick Start, Development, Tests and Quality, Project Structure, Documentation, Roadmap, Contributing, Security, License. Includes a "Using this template" section that points to the bootstrap instructions |
| `CONTRIBUTING.md` | §21.3: prerequisites, branch conventions and issue reference, Conventional Commits, test/lint commands (placeholder per profile), PR expectations and review, ADR/doc rules, security reporting, Definition of Done |
| `SECURITY.md` | §11.4: supported versions table, private reporting channel (GitHub private vulnerability reporting with `OWNER/REPOSITORY` placeholder), expected report information, confidential handling, coordinated disclosure, explicit "do not open public issues" |
| `SUPPORT.md` | Where to ask questions (Discussions if enabled), what not to post (secrets, vulnerabilities) |
| `CHANGELOG.md` | Keep a Changelog 1.1.0 header, `## [Unreleased]` section, SemVer note |
| `LICENSE` | Only for the template repository itself, after the human choice in T4 |

## Requirements

1. **R1:** All files are English and contain no German text (§1.4).
2. **R2:** Placeholders use exactly the tokens `PROJECT_NAME`, `PROJECT_DESCRIPTION`, `OWNER`, `REPOSITORY`, `OWNER_OR_TEAM` so `FEAT-015` can detect leftovers.
3. **R3:** `SECURITY.md` never asks reporters to put vulnerability details into public issues.
4. **R4:** README states that a derived project must choose a license and that the template's own license does not automatically apply to derived code.
5. **R5:** No file links into `template-dev/`.
6. **R6:** Links to `docs/` targets only where `FEAT-003` creates them; otherwise mark as "added by FEAT-003" in the PR and fix in that feature.

## Tasks

- [x] **T1:** Write `README.md` and `CHANGELOG.md`.
- [x] **T2:** Write `CONTRIBUTING.md` and `SUPPORT.md`.
- [x] **T3:** Write `SECURITY.md`.
- [x] **T4:** Human decision: license of the template repository; add `LICENSE` afterwards (see [open-decisions.md](../open-decisions.md#additional-human-only-choices)).

## Acceptance Criteria

- [x] A consistent README and project entry point are available (§17.1).
- [x] The selected project license is explicit and appropriate (§17.1), documented as a bootstrap choice for derived projects.
- [ ] Confidential security vulnerabilities have a private reporting channel (§17.2).
- [x] `CHANGELOG.md` validates against the Keep a Changelog structure (headings `## [Unreleased]`).

## Verification

```text
grep -rn "PROJECT_NAME\|OWNER\|REPOSITORY" README.md SECURITY.md CONTRIBUTING.md   # placeholders present by design
grep -rn "template-dev" README.md CONTRIBUTING.md SECURITY.md SUPPORT.md CHANGELOG.md   # must be empty
markdownlint-cli2 "*.md"   # once FEAT-016 provides the config
```

## Agent Notes

- **Allowed paths:** the five root files, `LICENSE` (after T4 only), this feature file, backlog status.
- **Requires approval:** choosing a license (T4).
- **Pitfalls:** §19: placeholder links remain in derived repos if not validated; keep tokens consistent. Private vulnerability reporting must be enabled per repository; say so in `SECURITY.md`.

## Implementation Notes

- T4 decided by the maintainer on 2026-11-10: MIT License for the template repository, copyright
  holder from the maintainer's Git identity. Derived projects receive the file as a copy; the
  `README.md` License section asks each project to keep or replace it explicitly. `LICENSE` is not
  in `template_only_paths`, because removing it would leave derived projects without any license
  file to decide on.
