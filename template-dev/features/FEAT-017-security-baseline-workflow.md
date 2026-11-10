---
id: "FEAT-017"
title: "Add Security Baseline Workflow and Secret Scanning"
epic: "EPIC-06"
phase: 2
status: "planned"
priority: "critical"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§10.2", "§10.3", "§11.1", "§11.2", "§17.4", "§17.5"]
dependencies: ["FEAT-016"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-017: Add Security Baseline Workflow and Secret Scanning

## Objective

`security.yml` runs secret scanning on PRs, pushes and on a schedule, and the repository documents
the GitHub Actions security baseline every workflow must follow.

## Background

§11.1 baseline table, §11.2 secure Actions operation (least privilege, SHA pinning, untrusted
input, `pull_request_target`, fork secrets, separate publish jobs), §10.3 Gitleaks.

## Scope

- `security.yml` with `secret-scan` (Gitleaks) and `actions-pinning` check.
- `docs/governance/security-policy.md` with the Actions rules from §11.2.

### Out of Scope

- CodeQL, Trivy, Scorecard (`FEAT-043`), SBOM (`FEAT-042`), runners (`FEAT-045`).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/security.yml` | Jobs `secret-scan` (full history on schedule, diff on PR), `actions-pinning` |
| `.gitleaks.toml` | Default rules plus allowlist for test fixtures only |
| `scripts/ci/check_action_pinning.py` | Fails on any `uses:` not pinned to a 40-char SHA (local `./` actions excepted) |
| `docs/governance/security-policy.md` | §11.1 table and §11.2 rules as a checklist for workflow reviews |
| `tests/ci/test_check_action_pinning.py` | Tag-pinned and branch-pinned fixtures fail |

## Requirements

1. **R1:** `secret-scan` fails the run on any finding; no `continue-on-error`.
2. **R2:** No use of `pull_request_target` in template workflows; the policy explains when it would be acceptable.
3. **R3:** Secrets are never passed to jobs triggered by fork PRs.
4. **R4:** Schedule runs at least weekly.
5. **R5:** `actions-pinning` covers all files in `.github/workflows/` and `.github/actions/`.

## Tasks

- [ ] **T1:** `security.yml` with Gitleaks and config.
- [ ] **T2:** Pinning checker with tests.
- [ ] **T3:** `security-policy.md` and `docs/INDEX.md` line.

## Acceptance Criteria

- [ ] Secret scanning or an appropriate equivalent is configured (§17.4).
- [ ] No credentials, tokens or private keys are committed: a fixture commit with a fake AWS key fails `secret-scan` (§17.5).
- [ ] External Actions are pinned or managed by an approved lock strategy (§17.5).
- [ ] Test case "external PR with secret access → access denied" (§21.6) is documented with the workflow design that guarantees it.

## Verification

```text
gitleaks detect --source . --config .gitleaks.toml
python -I scripts/ci/check_action_pinning.py
python -I -m pytest tests/ci/test_check_action_pinning.py
```

## Agent Notes

- **Allowed paths:** files listed in Deliverables, `docs/INDEX.md` (line), this feature file, backlog status.
- **Requires approval:** enabling GitHub secret scanning or push protection in repository settings.
- **Pitfalls:** Never commit a real secret as a test; use well-known fake patterns and allowlist only the fixture path.
