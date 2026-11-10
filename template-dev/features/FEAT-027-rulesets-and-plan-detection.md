---
id: "FEAT-027"
title: "Apply Rulesets with Plan Detection and Solo Mode"
epic: "EPIC-07"
phase: 2
status: "implemented"
priority: "high"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§8.7", "§14.2", "§14.3", "§14.4", "§17.4", "§19"]
dependencies: ["FEAT-020", "FEAT-026"]
blocked_by_decisions: []
agent_ready: true
related_issues: ["#8"]
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-027: Apply Rulesets with Plan Detection and Solo Mode

## Objective

`project-bootstrap apply-rulesets` protects `main` and `develop` with rulesets (or classic
branch protection as fallback), detects what the plan and visibility support, and degrades with a
clear report instead of failing silently.

## Background

§8.7 protection rules for `main`/`develop`, §14.2 ruleset content, §14.3 solo development (required
reviews can block a single maintainer), §14.4 plan differences (no "compliant by configuration"
claim when GitHub does not enforce a setting), §19 pitfalls (admin bypass, required checks that
never report).

## Scope

- Ruleset definitions as data in `.project/bootstrap.yml`; resource with capability detection.

### Out of Scope

- Org-level rulesets.

## Deliverables

| Path | Description |
|---|---|
| `src/engineering_bootstrap/resources/rulesets.py` | Capability probe, ruleset diff/apply, fallback to branch protection, `skipped` with reason |
| `.project/bootstrap.yml` (section) | `protection.main`, `protection.develop`, `protection.mode: team\|solo`, required check `quality-gate` |
| `docs/governance/branch-protection.md` | What is enforced per plan; manual steps if unsupported |
| `tests/resources/test_rulesets.py` | Free-private (none), Free-public, Pro, Team; solo vs team |

## Requirements

1. **R1:** `main`: no direct push, no force push, no deletion, PR required, conversations resolved before merge, required check `quality-gate`, merge method per `DEC-02`; release tags `v*` protected (§14.2).
2. **R2:** `develop`: no direct push, no force push, no deletion, PR required, conversations resolved before merge, required check `quality-gate`.
3. **R3:** Solo mode sets required approvals to 0 but keeps PR and checks.
4. **R4:** If neither rulesets nor branch protection are available, the report states "UNPROTECTED" and the exit code is non-zero unless `--allow-unprotected`.
5. **R5:** Required check names match real job names; a check that never ran is reported as risk.

## Tasks

- [x] **T1:** Capability probe with tests.
- [x] **T2:** Ruleset resource for rulesets API.
- [ ] **T3:** Fallback to classic branch protection. Dropped by decision; see Implementation Notes.
- [x] **T4:** Governance doc.

## Acceptance Criteria

- [x] Branch protection or rulesets are applied where supported (§17.1).
- [x] `main` cannot receive direct pushes in protected configurations (§17.4).
- [x] Unsupported configurations are reported, not silently ignored (§17.1).

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources/test_rulesets.py
project-bootstrap apply-rulesets --repo <test-owner>/upt-smoke-public --dry-run
```

## Agent Notes

- **Allowed paths:** ruleset resource, tests, `bootstrap.yml` section and schema, `docs/governance/branch-protection.md`, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** `--apply` against real repositories; `--allow-unprotected`.
- **Pitfalls:** A required status check that never reports blocks all merges; verify the check ran once before requiring it.

## Implementation Notes

- **Decisions (issue #8):** no fallback to classic branch protection (T3 dropped), because on
  GitHub Free it is unavailable for private repositories exactly where rulesets are, and on the
  other plans rulesets cover the same rules. A required check that never reported is left out
  and reported as `skipped`. The template default is `mode: "solo"`.
- **Files outside the allowed paths:** `apply-rulesets` wiring in `cli.py`; the fake ruleset and
  check-run endpoints in `tests/conftest.py`; CLI tests in `tests/test_cli.py`; schema tests in
  `tests/ci/test_validate_project.py`; field and migration rows in `.project/README.md`; a section
  in the package README; a link from `docs/governance/branching-and-releases.md`.
- **Test location:** the package keeps a flat `tests/` directory, so the tests are in
  `tests/test_rulesets.py`.
- **Design:** the section is `protection` in `bootstrap-1.2.schema.json` with `mode`,
  `required_status_checks` and `release_tag_pattern`; branch names come from `project.yml` and the
  merge methods from `workflow.yml`, so no value has two sources. Three rulesets with stable
  names (`bootstrap-default-branch`, `bootstrap-development-branch`, `bootstrap-release-tags`)
  are owned by the tool and replaced as a whole; other rulesets are reported only. No bypass
  actors (§19). The plan probe is the rulesets list endpoint: a `403` with GitHub's upgrade
  message means `UNPROTECTED` (R4); any other `403` fails the run. A check is required only after
  it has reported on the branch head, bound to the App ID of that run (R5); an already required
  check is kept.
- **Live runs (2026-11-10):** `BenBotsch/upt-smoke-2` (private, GitHub Free): dry run reports
  the three rulesets as `failed` with `UNPROTECTED` and exits with `1`. `BenBotsch/upt-smoke-public`
  (public, created from the template): dry run plans 3 `create` and 2 `skipped` checks; `--apply`
  creates the rulesets; a second run reports 3 `noop`. `gh api` shows the rules as configured
  with no bypass actors, and a direct push to `main` is rejected with "Changes must be made
  through a pull request". Required-check path: after the template's `develop` state reached
  `main` of `upt-smoke-public` through a pull request and `develop` was created, `quality-gate`
  reported `success` on both branches; the next dry run planned 2 `update`, `--apply` added
  `quality-gate` with App ID `15368` to both branch rulesets, and a second run reported 3 `noop`.
  A pull request into `develop` with a failing `quality-gate` is then refused with "the base
  branch policy prohibits the merge".
- **Template repository (2026-11-10):** `BenBotsch/UniversalProjectTemplate` was made public;
  `--apply` created the three rulesets with `quality-gate` required on `develop` and skipped on
  `main`, where the check has not reported yet.
- **Limits:** R5 is checked against GitHub, not against `ci.yml`: a misspelled name never reports
  and stays `skipped`. Private repositories on paid plans are not tested yet. Org rulesets are out
  of scope.
