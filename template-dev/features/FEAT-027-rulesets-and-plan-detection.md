---
id: "FEAT-027"
title: "Apply Rulesets with Plan Detection and Solo Mode"
epic: "EPIC-07"
phase: 2
status: "planned"
priority: "high"
effort: "l"
target_repo: "engineering-bootstrap"
spec_refs: ["§8.7", "§14.2", "§14.3", "§14.4", "§17.4", "§19"]
dependencies: ["FEAT-020", "FEAT-026"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
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

- [ ] **T1:** Capability probe with tests.
- [ ] **T2:** Ruleset resource for rulesets API.
- [ ] **T3:** Fallback to classic branch protection.
- [ ] **T4:** Governance doc.

## Acceptance Criteria

- [ ] Branch protection or rulesets are applied where supported (§17.1).
- [ ] `main` cannot receive direct pushes in protected configurations (§17.4).
- [ ] Unsupported configurations are reported, not silently ignored (§17.1).

## Verification

```text
python -m pytest tools/engineering-bootstrap/tests/resources/test_rulesets.py
project-bootstrap apply-rulesets --repo <test-owner>/upt-smoke-public --dry-run
```

## Agent Notes

- **Allowed paths:** ruleset resource, tests, `bootstrap.yml` section and schema, `docs/governance/branch-protection.md`, `docs/INDEX.md` line, this feature file, backlog status.
- **Requires approval:** `--apply` against real repositories; `--allow-unprotected`.
- **Pitfalls:** A required status check that never reports blocks all merges; verify the check ran once before requiring it.
