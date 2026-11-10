# Agent Implementation Guide

How coding agents pick, implement, verify and report work from this backlog. The repository-wide
rules in the root `AGENTS.md` (delivered by `FEAT-004`) take precedence once they exist; until then,
this guide and §7 of the [specification](specification.md#7-agentsmd-und-agent-first-entwicklung) apply.

## Picking work

Pick the **highest-ranked** row in [backlog.md](backlog.md) that meets all of these conditions:

1. `status` is `planned`.
2. `agent_ready` is `true`.
3. Every feature in `dependencies` has `status: implemented`.
4. No entry of `blocked_by_decisions` is still `open` in [open-decisions.md](open-decisions.md).
5. No other agent works on it (status `active`, or an open PR that references the feature ID).

If nothing qualifies, stop and report which decision or dependency blocks the next item. Do not
start a feature with `agent_ready: false`; a human must first resolve the blocker and flip the flag.

Work one task (`FEAT-NNN/Tn`) per pull request. Several tasks of the same feature may follow each
other; do not mix tasks of different features in one PR.

## Working cycle

Follows §7.5:

1. Read the feature file completely, then the referenced sections of
   [specification.md](specification.md). The specification is authoritative for intent; the feature
   file is authoritative for scope.
2. Set `status: active` and `updated_at` in the feature file and regenerate the backlog
   (see [tools/](tools/README.md)) in your first commit.
3. Inspect existing files before creating new ones; extend existing units.
4. Implement only the deliverables listed in the feature file and only inside **Allowed paths**.
5. Write or update tests for every requirement `R*` that can be tested.
6. Run the commands in **Verification** and the relevant linters. Record the actual output.
7. Update documentation affected by the change (`docs/INDEX.md` when adding a doc).
8. Open a PR with the report below. Tick completed tasks and acceptance criteria in the feature file.
9. When all acceptance criteria are met and merged, set `status: implemented`.

## Permissions

Follows §7.6. Allowed without asking: reading, editing files inside **Allowed paths**, running local
tests and linters, opening pull requests.

Requires explicit human approval each time:

- Anything listed under **Requires approval** in the feature file.
- Creating or configuring GitHub repositories, rulesets, environments, secrets, or labels on a real
  repository (dry-runs are allowed).
- Merging, tagging, releasing, deleting branches, force pushes, history rewrites.
- Recording a decision `DEC-NN`; agents may prepare an options analysis only.
- Choosing a license or a CODEOWNERS owner.

Never commit credentials, tokens, private keys or personal data, including in tests and fixtures.

## Definition of Done

A task is done when:

- Every deliverable of the task exists at the listed path.
- Tests cover the task's requirements, including the relevant failure paths, and pass.
- Verification commands ran, and their actual results are in the PR.
- Linters and formatters configured in the repository pass on changed files.
- Affected documentation is updated; no file outside `template-dev/` links to `template-dev/`.
- Feature file shows the new status, backlog and epics are regenerated, and
  `python -I template-dev/tools/verify_backlog.py` passes.

## Report format

Every PR description and every final agent message contains:

```text
Feature/Task: FEAT-NNN/Tn
Changes:      files added or changed, one line each
Verification: commands run and their actual result (pass/fail, counts)
Not verified: checks that were skipped and why
Risks:        remaining risks, open questions, follow-ups
References:   spec sections, related features, decisions
```

## Template-only rule

`template-dev/` is copied into every repository created from the template and removed by
`project-bootstrap init` (`FEAT-028`). Therefore:

- Deliverables outside `template-dev/` must never link to, import from, or mention paths inside it.
  Validation rule `REPO-DEAD-LINK-TEMPLATE` (`FEAT-015`) enforces this.
- `docs/` is the clean scaffold for derived projects. It must not contain tasks of the template.
- Tools that only serve template development (such as the backlog migration of `FEAT-048`) live in
  `template-dev/`.

## Names and paths

| Item | Value |
|---|---|
| CLI command | `project-bootstrap` (§13.7) |
| Python package | `engineering_bootstrap` |
| Package location until its own repository exists | `tools/engineering-bootstrap/`; `src/...` and `tests/...` paths in `FEAT-024` to `FEAT-030`, `FEAT-046` and `FEAT-051` are relative to it |
| Workflows until `DEC-08` is decided | `.github/workflows/` and `profiles/<stack>/` |
| CI scripts | `scripts/ci/` |
| Project configuration | `.project/` |
| Dashboard until its own repository exists | `dashboard/` |

## Parallel lanes

Features in different lanes have disjoint deliverable paths and may run concurrently once their
dependencies are implemented. `FEAT-001` is the common start of all lanes.

| Lane | Sequence | Area |
|---|---|---|
| A | `FEAT-001` → `FEAT-002` / `FEAT-003` → `FEAT-012` / `FEAT-006` | Root files, docs, governance |
| B | `FEAT-004` → `FEAT-005` | Agent instructions |
| C | `FEAT-008` → `FEAT-007` / `FEAT-009` | Labels, forms, issue rules |
| D | `FEAT-013` → `FEAT-014` | Project configuration and schemas |
| E | `FEAT-011` | PR template and CODEOWNERS |

Cross-lane dependencies: `FEAT-006` needs `FEAT-004` (lane B); `FEAT-009` and `FEAT-012` need
`FEAT-003` (lane A); `FEAT-014` needs `FEAT-008` (lane C).

From phase 2 on, follow the serial chain **`FEAT-013` → `FEAT-014` → `FEAT-015` / `FEAT-016` →
`FEAT-020`**, because the validators, base CI and quality gates share `.project/` schemas and
`scripts/ci/`. Phase 2 work that can run beside this chain: `FEAT-018` and `FEAT-019` (separate
validator packages), `FEAT-021`, `FEAT-023`, and the bootstrap CLI after `DEC-01`.

Two agents must never edit the same file in parallel. Shared files (`docs/INDEX.md`,
`.project/workflow.yml`, `labels.yml`, generated `backlog.md`) are changed in small, separate commits and
rebased before the PR is opened.
