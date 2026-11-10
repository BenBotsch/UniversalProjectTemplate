---
id: "ADR-0006"
title: "Apply Technology Profiles as Anchored Blocks and Own Files"
status: "proposed"
created_at: "2026-11-10"
related_issues: []
---

# ADR-0006: Apply Technology Profiles as Anchored Blocks and Own Files

## Context

The base layer of the template supports no programming language (§1.3). Its quality gates for
formatting, lint, tests, build and security are `not_implemented`. A technology profile, for
example Python, adds the tools and CI jobs of one stack to a derived project (§3.3, §10.1).
Bootstrap applies it during `init` or later (§13.2).

Several constraints apply:

- [ADR-0003](0003-aggregate-ci-in-one-quality-gate.md) requires that every CI job report into the
  single `quality-gate` job. That job lists its jobs in `needs` in `.github/workflows/ci.yml`, a
  base file.
- Projects edit the files a profile adds. A second run must not overwrite those edits.
- Projects may apply more than one profile, and each must be removable by hand.
- `project.yml` records the applied profile version for later upgrades (`FEAT-046`).

## Decision

A profile is a directory `profiles/<id>/` with a manifest `profile.yml`. The manifest is
validated against `profiles/_schema/profile.schema.json`. It also contains a directory `files/`
holding the files the profile owns. `project-bootstrap apply-profile` and
`init --profile` apply the profile in two ways.

1. **Own files.** Every file under `files/` is copied to the same path in the project. The tokens
   `PROJECT_NAME`, `PROJECT_DESCRIPTION` and `PROJECT_PACKAGE` are replaced in paths and content.
   A profile must not ship a base file such as `ci.yml`.
2. **Anchored blocks in base files.** Five base files each carry an anchor comment, and the
   profile's entries are inserted directly above it. Each inserted block is wrapped in
   `# profile:<id>:start` and `# profile:<id>:end`.

   | Anchor | File | Entries |
   |---|---|---|
   | `# bootstrap:profile-jobs` | `.github/workflows/ci.yml` | one job per `ci_jobs` entry, which calls a workflow of the profile |
   | `# bootstrap:profile-needs` | `.github/workflows/ci.yml` | the same job IDs in `quality-gate.needs` |
   | `# bootstrap:profile-gates` | `.project/quality-gates.yml` | `quality_gates` |
   | `# bootstrap:profile-updates` | `.github/dependabot.yml` | `dependabot` |
   | `# bootstrap:profile-labels` | `.project/labels.yml` | `labels` |

   `project.yml` gets the union of `technology.languages` and `technology.package_managers` and an
   entry `{id, version}` in `profiles`.

A profile gate replaces a generic base gate with `covers: <gate>` (quality-gates schema 1.2). The
covered gate becomes inapplicable once an implemented covering gate exists for every language of
the project. Every job of a profile workflow has exactly one gate, and every gate names a job of a
profile workflow, so the evaluator of ADR-0003 knows each job's applicability.

Apply is planned and reported by the engine of ADR-0002, like every other resource:

- An identical file or block is `noop`, so a second run changes nothing.
- A file or block that differs from the profile is `skipped` as a conflict. `--force` replaces it.
- A file that was deleted after the profile was recorded is `skipped` and not recreated.
  `--force` recreates it.
- A missing anchor, a missing required profile, a covered gate that does not exist, and a gate
  name that already exists each fail the run before anything is written.

The template's own checkout is never changed (`is_template: true`). `profiles/` is a template-only
path, so a derived project keeps the applied files but not the profile sources.

## Alternatives Considered

- **Profiles only add files, no base-file edits.** The `FEAT-031` notes asked for this. It fails
  for CI: `quality-gate` would not wait for the profile jobs, so a failing profile job could not
  block a merge. A separate aggregator per profile would break ADR-0003.
- **Merging parsed YAML.** Loading and dumping the base files would drop their comments, order and
  quoting. It would also mix profile entries into project entries, so neither a conflict nor a
  removal could be detected.
- **Activating jobs at CI time from `project.yml`.** All profile workflows would ship with every
  project and be skipped by conditions. The template would then pretend the stacks exist, against
  §1.3. Dependabot and labels cannot be made conditional at all.
- **Overwriting on every run.** This is simpler, but it loses the project's edits, which
  `FEAT-031` R3 forbids.

## Consequences

- A project can apply several profiles. Their blocks stack above the anchors in the order of
  application.
- Removing a profile by hand means deleting its blocks between the markers, its files and its
  `profiles` entry. There is no `remove-profile` command yet.
- Projects must keep the anchor comments. A deleted anchor makes the next apply fail with a hint to
  restore it from the template.
- Upgrading a profile (`FEAT-046`) can compare the recorded version with the template's. Changed
  blocks or files are then reported as conflicts, so the project decides with `--force`.
- Profile workflows are part of the template. The template's CI checks them with actionlint,
  zizmor and the action-pinning check, although they only run in derived projects.
