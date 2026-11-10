---
id: "FEAT-041"
title: "Add Protected Release Workflow with Environment Approval"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "high"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§8.2", "§9.4", "§9.6", "§11.1", "§11.2", "§14.2"]
dependencies: ["FEAT-017", "FEAT-020", "FEAT-040"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-041: Add Protected Release Workflow with Environment Approval

## Objective

`release.yml` creates the tag `vX.Y.Z` on the approved release commit on `main`, builds artifacts
reproducibly and publishes only after approval through a protected `release` environment.

## Background

§8.2 steps 8-10, §9.4 (tags on `main`, reproducible artifacts, human approval), §9.6 release
criteria, §11.2 separate publish jobs with protected environments, §14.2 releases via protected
environments and tags.

## Scope

- Workflow triggered by merge of a release PR into `main` or by `workflow_dispatch` with version.
- Jobs: `verify` (all gates green, version and changelog present), `build`, `package`, `publish`
  (environment `release`).

### Out of Scope

- SBOM and attestations (`FEAT-042`), stack-specific packaging (profiles).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/release.yml` | Jobs above; `publish` uses `environment: release` |
| `scripts/release/verify_release.py` | §9.6 checks: version format, changelog entry, no `CRITICAL` open security alerts (if API available), tag does not exist |
| `docs/governance/branching-and-releases.md` (section) | Release checklist per §9.6, environment setup steps |
| `tests/release/test_verify_release.py` | Each §9.6 criterion |

## Requirements

1. **R1:** Tags only from `main`; the workflow refuses other refs.
2. **R2:** `publish` cannot run without environment approval; solo mode documents self-approval limits (§14.3).
3. **R3:** Write permissions only in `publish` (`contents: write`), other jobs read-only.
4. **R4:** Artifacts are uploaded with the commit SHA in their metadata.
5. **R5:** No long-lived cloud credentials; OIDC where deployment needs cloud access (§11.1).

## Tasks

- [ ] **T1:** `verify_release.py` with tests.
- [ ] **T2:** Workflow jobs and environment documentation.
- [ ] **T3:** Dry release in a test repository.

## Acceptance Criteria

- [ ] Releases can be traced to tags and release notes (§17.4).
- [ ] Release workflows require protected or explicit approval (§17.5).
- [ ] A release attempt from `develop` is refused.

## Verification

```text
python -I -m pytest tests/release/test_verify_release.py
actionlint .github/workflows/release.yml
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** creating the `release` environment and its reviewers; any real release.
- **Pitfalls:** Environment protection rules for private repos depend on the plan; detect and report (§14.4).
