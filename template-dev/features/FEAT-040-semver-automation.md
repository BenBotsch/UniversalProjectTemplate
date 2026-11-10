---
id: "FEAT-040"
title: "Automate Semantic Version and Changelog Proposals"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "medium"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§9.1", "§9.2", "§9.3", "§9.5", "§19.1"]
dependencies: ["FEAT-019", "FEAT-039"]
blocked_by_decisions: ["DEC-02", "DEC-06"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-040: Automate Semantic Version and Changelog Proposals

## Objective

A tool computes the next SemVer version from Conventional Commits merged since the last tag and
proposes the changelog entry as a reviewable PR; a human approves the release.

## Background

§9.5: label-based notes do not compute versions; use a separate tool or tested own logic. §9.1/§9.2
commit types and breaking changes drive the bump. Blocked by `DEC-02` (squash vs merge decides which
messages are authoritative) and `DEC-06` (which tool).

## Scope

- Integration of the chosen tool (e.g. release-please) or an in-house script, per `DEC-06`.
- Release PR from `develop` to `main` containing version bump and changelog.

### Out of Scope

- Publishing artifacts (`FEAT-041`).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/release-prepare.yml` | `workflow_dispatch` (and optional schedule); opens/updates release PR `develop` → `main` |
| Tool configuration | e.g. `release-please-config.json` + manifest, or `scripts/release/next_version.py` |
| `tests/release/**` | Bump cases: `fix` → patch, `feat` → minor, `!`/`BREAKING CHANGE` → major, `0.y.z` rule, RC suffix |
| `docs/governance/branching-and-releases.md` (section) | How to prepare a release |

## Requirements

1. **R1:** Version computation is deterministic and tested on fixtures for every bump rule.
2. **R2:** `0.y.z` handling follows the documented release policy (breaking change bumps minor while `0.x`).
3. **R3:** The workflow never tags or publishes; it only opens a PR.
4. **R4:** `permissions` limited to `contents: write` and `pull-requests: write` in that job only.
5. **R5:** Release candidates (`X.Y.Z-rc.N`) supported via input.

## Tasks

- [ ] **T1:** Options analysis for `DEC-06` (prepared by agent, decided by human).
- [ ] **T2:** Implement chosen tool with tests.
- [ ] **T3:** Workflow and documentation.

## Acceptance Criteria

- [ ] Version numbers follow Semantic Versioning (§17.4).
- [ ] Changelog proposal appears in a release PR and requires human merge.

## Verification

```text
python -I -m pytest tests/release
actionlint .github/workflows/release-prepare.yml
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** resolving `DEC-02` and `DEC-06`.
- **Pitfalls:** With squash merges, only PR titles reach `develop`; commitlint on individual commits then has no effect on versioning.
