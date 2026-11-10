---
id: "FEAT-016"
title: "Add Universal Base CI and Quality Workflows"
epic: "EPIC-06"
phase: 2
status: "planned"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§10.1", "§10.2", "§10.3", "§10.4", "§10.6", "§10.7", "§11.2"]
dependencies: ["FEAT-014", "FEAT-015"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-016: Add Universal Base CI and Quality Workflows

## Objective

`ci.yml` and `quality.yml` run the universal base layer on every PR and push to `main`/`develop`:
project and repository validation, workflow lint, YAML and Markdown checks, link check.

## Background

§10.1 universal base layer, §10.2 job catalog, §10.4 flow, §10.6 minimal skeleton with
`permissions: contents: read` and concurrency, §10.3 tools (actionlint, zizmor, YAML/Markdown
validation). An empty project must not start a build that does not exist (§1.3).

## Scope

- `ci.yml`: `repository-validation` (FEAT-014 + FEAT-015 scripts).
- `quality.yml`: `workflow-lint` (actionlint, zizmor), `yaml-lint`, `markdown-lint`, `link-check`.
- Lint configuration files.

### Out of Scope

- Secret scanning (`FEAT-017`), stack-specific jobs (`EPIC-08`), quality-gate evaluator (`FEAT-020`).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/ci.yml` | Triggers per §10.6; jobs `repository-validation` |
| `.github/workflows/quality.yml` | Jobs `workflow-lint`, `yaml-lint`, `markdown-lint`, `link-check` |
| `.yamllint.yml` | Rules compatible with GitHub workflow syntax (`truthy` relaxed for `on:`) |
| `.markdownlint-cli2.yaml` | Front-matter title does not count as H1; table style consistent; `template-dev/specification.md` excluded |
| `scripts/ci/README.md` | How to run every CI check locally |

## Requirements

1. **R1:** Workflow-level `permissions: contents: read`; no job requests more.
2. **R2:** All actions pinned to full commit SHAs with a version comment (§10.6, §11.2).
3. **R3:** Job ids match the names in `quality-gates.yml` (`FEAT-013` R4).
4. **R4:** No `continue-on-error` on any job (§10.7).
5. **R5:** No untrusted input (`github.event.*.title`, `body`, `head_ref`) interpolated into `run:` scripts.
6. **R6:** Every check can be run locally with the commands in `scripts/ci/README.md`.
7. **R7:** zizmor runs with no findings at default severity or each finding is justified inline.

## Tasks

- [ ] **T1:** `ci.yml` with `repository-validation`.
- [ ] **T2:** `quality.yml` with actionlint and zizmor.
- [ ] **T3:** YAML/Markdown lint and link check with configs.
- [ ] **T4:** `scripts/ci/README.md`.

## Acceptance Criteria

- [ ] Repository validation runs automatically (§17.4).
- [ ] GitHub Actions/YAML validation is available (§17.4).
- [ ] GitHub Actions permissions follow least privilege (§17.5).
- [ ] External Actions are pinned (§17.5).
- [ ] The initial CI pipeline passes on the template and fails on a PR that introduces invalid metadata (§17.6).

## Verification

```text
actionlint
zizmor .github/workflows/
yamllint .
markdownlint-cli2
# GitHub: open a test PR with a broken .project/project.yml; ci.yml must fail.
```

## Agent Notes

- **Allowed paths:** `.github/workflows/ci.yml`, `.github/workflows/quality.yml`, lint config files, `scripts/ci/README.md`, this feature file, backlog status.
- **Requires approval:** pushing workflows to a GitHub repository (outward-facing).
- **Pitfalls:** §19 "green by skipped jobs". Pin by SHA; look SHAs up from the action's release, never invent them.
