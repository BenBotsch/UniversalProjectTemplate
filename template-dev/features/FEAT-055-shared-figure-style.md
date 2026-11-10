---
id: "FEAT-055"
title: "Offer the Shared Figure Style in the Python Profile"
epic: "EPIC-08"
phase: 3
status: "active"
priority: "low"
effort: "s"
target_repo: "universal-project-template"
spec_refs: []
dependencies: ["FEAT-032"]
blocked_by_decisions: []
agent_ready: false
related_issues: ["#24"]
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-055: Offer the Shared Figure Style in the Python Profile

## Objective

A derived Python project can render its README and documentation figures in the shared figure
style with [FigureKit](https://github.com/BenBotsch/FigureKit), and CI checks the committed
figures. Projects of other profiles get the naming and transparency rules as a short guide.

## Background

FigureKit (package `figkit`) is the shared figure style of the owner's projects. It provides
light and dark themes, transparent SVG, PNG and WebP export, a social card and the check
`figkit check <dir>`, which fails on a missing light/dark pair, an opaque chart or a file over
budget. `PredictiveMaintenanceMLOps` and `SurfaceDefectInspection` already use it, with figures
in `docs/figures/` named `<name>.<ext>` and `<name>-dark.<ext>`.

The specification has no section on figures. The feature is optional and does not affect the
quality gates of projects without figures.

## Scope

- An optional dependency group `figures` in the Python profile's `pyproject.toml`, pinned to a
  FigureKit tag.
- A guide `docs/figures/README.md` with the naming, the `<picture>` snippet for light and dark
  pages, alt text and attribution rules.
- A CI step `figkit check docs/figures` that runs only when the folder exists.
- Hook exclusions for generated SVGs (`end-of-file-fixer`, `trailing-whitespace`) and
  `docs/figures/*.svg -whitespace` in `.gitattributes`.

### Out of Scope

- Plotting code or example figures in the template.
- Figure tooling for other profiles; they receive the guide only.
- Publishing FigureKit to a package index.

## Deliverables

| Path | Description |
|---|---|
| `profiles/python/files/pyproject.toml` | Optional group `figures = ["figkit @ git+https://github.com/BenBotsch/FigureKit@vX.Y.Z"]` |
| `profiles/python/files/docs/figures/README.md` | Naming, embedding, alt text, attribution, `figkit check` |
| `profiles/python/files/.github/workflows/python.yml` | Conditional job step `figkit check docs/figures` |
| `profiles/python/files/.pre-commit-config.yaml`, `.gitattributes` | Exclusions for generated SVGs |
| `profiles/python/README.md` | Section on figures |

## Requirements

1. **R1:** Without `docs/figures/`, the profile's CI is unchanged and green.
2. **R2:** With `docs/figures/` present, CI fails when `figkit check` reports a finding.
3. **R3:** The FigureKit dependency is pinned to a tag, never to a branch.
4. **R4:** The serving or runtime installation of a derived project does not need the `figures`
   group.

## Tasks

- [x] **T1:** Dependency group, guide and hook exclusions in the Python profile.
- [x] **T2:** Conditional CI step and fixture test with and without `docs/figures/`.

## Acceptance Criteria

- [x] A fixture project without `docs/figures/` passes CI unchanged.
- [x] A fixture project with a light figure but no dark counterpart fails the figure check.
- [x] A fixture project with valid figure pairs passes the figure check.

## Verification

```text
uv sync --group figures
uv run figkit check docs/figures
```

## Agent Notes

- **Allowed paths:** `profiles/python/**`, this feature file, backlog status.
- **Requires approval:** changing the pinned FigureKit tag in released profiles.
- **Pitfalls:** matplotlib SVGs end lines with spaces; whitespace hooks must exclude them, or they
  rewrite generated files and break byte-identical output.

## Implementation Notes

- The python profile is raised to 0.2.0. `pyproject.toml` gets the dependency group `figures`
  with `figkit @ git+https://github.com/BenBotsch/FigureKit@v0.2.1`, the tag that
  `PredictiveMaintenanceMLOps` uses (R3). A dependency group is not part of the built package, and
  `uv sync` installs only `dev` by default (R4).
- The guide is `docs/figures/README.md` of the profile. It covers the naming, `<picture>`
  embedding, alt text and sources (T1).
- **Condition (R1):** the profile ships the guide, so `docs/figures/` always exists. The step
  "Check figures" in the `lint` job therefore runs `figkit check docs/figures` only when the
  folder holds an SVG, PNG or WebP file. It uses `--locked` when `uv.lock` exists. A finding
  fails the `lint` job and its gate `python_lint` (R2). No new job or gate is needed.
- **Deviation:** the template already has a base `.gitattributes`, which a profile must not ship.
  The rule `*.svg -whitespace` is in `docs/figures/.gitattributes` instead, and
  `docs/figures/.editorconfig` keeps editors from trimming the SVGs. `.pre-commit-config.yaml` is
  new and excludes the SVGs from `end-of-file-fixer` and `trailing-whitespace` (pitfall).
- **Change to the audit job:** pip-audit rejects the git requirement of FigureKit, because it has
  no hash. `uv export` leaves it out with `--no-emit-package figkit`, so matplotlib, numpy and
  Pillow are still audited. The option is ignored when the group is deleted.
- **Tests (T2):** `test_python_figure_check_runs_only_with_figures` runs the script of the step
  with a stub `uv`: guide only, figures with and without `uv.lock`, and a finding.
- **Verification (local, Windows, FigureKit v0.2.1):** in a project initialized with the profile,
  `uv lock` and `uv sync --locked` install neither FigureKit nor matplotlib. With a rendered pair
  `demo.svg`/`demo-dark.svg`, the step reports `ok`. Without `demo-dark.svg` it fails with
  "missing its pair". With only the guide it skips. `pre-commit run trailing-whitespace` and
  `end-of-file-fixer` leave the SVG byte-identical, and `git diff --check` reports nothing for it.
  pip-audit on the export reports no known vulnerabilities. `uv build`, Ruff, mypy, pytest,
  actionlint and `pre-commit validate-config` pass. The run on GitHub is not verified yet.
