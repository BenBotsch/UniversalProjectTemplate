# Security Policy for Development and CI

This document defines the security baseline of the repository and the rules every GitHub Actions
workflow must follow. It is the checklist for reviewing workflow changes. How to report a
vulnerability is described in [SECURITY.md](../../SECURITY.md).

## Security Baseline

| Area | Minimum measure | In this repository |
|---|---|---|
| Workflow tokens | Minimal `GITHUB_TOKEN` permissions | `permissions: contents: read` in every workflow |
| Workflow dependencies | Actions pinned to reviewed full commit SHAs, or a lock-file mechanism | `actions-pinning` job in `security.yml` |
| Secrets | No committed tokens or keys; secret scanning enabled where available | `secret-scan` job in `security.yml` (Gitleaks) |
| Dependencies | Dependabot and suitable dependency checks | `.github/dependabot.yml` for GitHub Actions; other ecosystems are added for the ecosystems in use |
| Code | CodeQL or another SAST tool, depending on the stack and plan | Added per technology profile |
| Containers | Image scanning, minimal images, no root user where possible | Added per technology profile |
| Releases | Checksums, attestations, signed tags or artifacts where suitable | Release workflow |
| Supply chain | SBOM, build provenance and dependency review | Release workflow |
| Cloud deployment | OIDC instead of long-lived credentials, where supported | Deployment workflow |
| Agents | Least privilege, human approval, isolated execution | [Agent Permissions](agent-permissions.md) |
| Disclosure | `SECURITY.md` and a private reporting channel | [SECURITY.md](../../SECURITY.md) |

## Workflow Review Checklist

Check every new or changed workflow against these rules. Changes below `.github/workflows/` need
elevated review attention; see [Review Policy](review-policy.md).

- [ ] **Read-only default:** the workflow sets `permissions: contents: read` at the top level.
- [ ] **Explicit write access:** a job that needs more sets its own `permissions:` block with only
  the scopes it needs, and the pull request explains why.
- [ ] **Pinned actions:** every third-party action and reusable workflow is pinned to a full
  40-character commit SHA, with the version as a comment, for example
  `uses: actions/checkout@<sha> # v7.0.1`. Look the SHA up from the action's release tag; never
  guess it. `python -I scripts/ci/check_action_pinning.py` enforces this.
- [ ] **Verified downloads:** tools downloaded in a `run:` step have a pinned version and are
  verified against a SHA-256 checksum stored in the workflow.
- [ ] **No untrusted input in scripts:** issue titles, pull request bodies, comments, branch names
  and other event data are not interpolated with `${{ }}` into `run:` scripts. Pass them through
  `env:` and quote the variable in the script.
- [ ] **No `pull_request_target`:** template workflows do not use it; see
  [`pull_request_target`](#pull_request_target).
- [ ] **No secrets for untrusted code:** secrets are not passed to jobs that run code from fork
  pull requests or other code that anyone can change; see
  [Pull Requests from Forks](#pull-requests-from-forks).
- [ ] **No credentials in the checkout:** `actions/checkout` uses `persist-credentials: false`
  unless a later step must push, and that step is reviewed.
- [ ] **No false green:** no job uses `continue-on-error`, and a required job never passes because
  it was skipped.
- [ ] **Separate publishing:** jobs that publish releases, packages or deployments are separate
  from build and test jobs and run in a protected environment with required reviewers.
- [ ] **Runners:** jobs for untrusted pull requests run on GitHub-hosted or isolated, short-lived
  runners, never on persistent self-hosted runners with access to sensitive data.
- [ ] **Static checks pass:** `actionlint` and `zizmor` report no findings; see
  [scripts/ci/README.md](../../scripts/ci/README.md).

## Secret Scanning

The `secret-scan` job in `.github/workflows/security.yml` runs Gitleaks with the default rules and
[.gitleaks.toml](../../.gitleaks.toml):

| Trigger | Scanned commits |
|---|---|
| Pull request into `main` or `develop` | The commits of the pull request |
| Push to `main` or `develop` | The full history |
| Weekly schedule and manual run | The full history |

Any finding fails the job. The allowlist covers only `fixtures/secrets/` directories below `tests/`,
for deliberately fake test values; it never covers real secrets.

For the full-history scan, the checkout with `fetch-depth: 0` fetches every branch, and Gitleaks
scans all fetched refs. It therefore checks every branch on GitHub, not only the branch that
triggered the run. A secret on any branch fails the push runs on `main` and `develop` and the
scheduled run until the branch is deleted. This is intended: no branch may hold a secret. Delete
branches with deliberately fake secrets right after a test.

GitHub secret scanning and push protection are repository settings. Enabling them changes
repository security settings and needs approval by a maintainer; see
[Agent Permissions](agent-permissions.md).

### When a Secret Is Found

1. **Revoke or rotate the secret first.** Once a secret is pushed, treat it as compromised, even if
   the commit is removed later.
2. Remove the secret from the code and load it from a protected secret store instead.
3. If the secret reached a shared branch, decide with a maintainer whether to rewrite the history.
   A rewrite needs explicit approval and does not replace the rotation.
4. Report the incident privately, as described in [SECURITY.md](../../SECURITY.md), if the secret
   could have been used.

A false positive is fixed in the code where possible, for example by using an obviously fake value.
Extend the allowlist only for test fixtures and explain the entry in the pull request.

## `pull_request_target`

`pull_request_target` runs in the context of the base branch, with a token that can have write
access and with access to secrets, even for pull requests from forks. Checking out and running the
pull request's code in such a job gives that code these privileges.

Template workflows do not use `pull_request_target`. A project may use it only when all of these
apply, and the reason is recorded in an ADR:

- The job does not check out or run code from the pull request, for example a job that only
  labels pull requests or posts a comment based on metadata.
- Event data is handled as untrusted input, as described in the checklist.
- The job's permissions are limited to the scopes it needs.

## Pull Requests from Forks

The CI design guarantees that code from an external pull request cannot read secrets:

- All workflows that run pull request code use the `pull_request` trigger. For pull requests from
  forks, GitHub does not pass repository or environment secrets to these runs and makes the
  `GITHUB_TOKEN` read-only.
- No workflow uses `pull_request_target` or `workflow_run` to run pull request code in a
  privileged context.
- The template workflows do not reference any secrets. The only token used is the job's
  `GITHUB_TOKEN` with `contents: read`.
- Release and deployment credentials are available only in protected environments with required
  reviewers. Jobs triggered by pull requests do not use these environments.

Test case: an external pull request that tries to read a secret, for example by printing
`${{ secrets.EXAMPLE }}` in a new step, gets an empty value. To verify it, open such a pull request
from a fork against a test repository that has a dummy secret, and check that the value is empty
in the log. Do not use a real secret for this test.

In the repository settings, keep **Actions > General > Fork pull request workflows** at the
default, so that workflows from outside collaborators need approval, and do not enable "Send
secrets to workflows from fork pull requests" for private repositories.
