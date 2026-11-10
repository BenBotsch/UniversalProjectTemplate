---
id: "FEAT-017"
title: "Add Security Baseline Workflow and Secret Scanning"
epic: "EPIC-06"
phase: 2
status: "implemented"
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

- [x] **T1:** `security.yml` with Gitleaks and config.
- [x] **T2:** Pinning checker with tests.
- [x] **T3:** `security-policy.md` and `docs/INDEX.md` line.

## Acceptance Criteria

- [x] Secret scanning or an appropriate equivalent is configured (§17.4).
- [x] No credentials, tokens or private keys are committed: a fixture commit with a fake AWS key fails `secret-scan` (§17.5).
- [x] External Actions are pinned or managed by an approved lock strategy (§17.5).
- [x] Test case "external PR with secret access → access denied" (§21.6) is documented with the workflow design that guarantees it.

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

## Implementation Notes

- Open: the fake-AWS-key acceptance criterion needs a GitHub run. Gitleaks was not run locally,
  because it is not installed and binary downloads are blocked in this environment.
- Gitleaks 8.30.1 is installed from the release archive and verified against a SHA-256 checksum in
  the workflow, instead of `gitleaks-action`, which needs a license key for organization accounts.
- `actions-pinning` uses the runner's `python3` and no third-party packages. It also requires a
  version comment after the SHA (`FEAT-016` R2).
- `.project/quality-gates.yml`: `secret_scan` is set to `implemented`. `scripts/ci/README.md`
  lists the local commands for both jobs.
- Enabling GitHub secret scanning and push protection is a repository setting and stays open.
- First run on GitHub on 2026-11-10: `secret-scan` (full history) and `actions-pinning` passed.
  The negative test with a fake key commit is still open.
- Negative test on 2026-11-10 (issue #1): draft pull request #3 committed a fake AWS access key;
  `secret-scan` failed with one redacted finding. The pull request was closed without merging.
  The test branch must be deleted, because the scheduled full-history scan would report it.
