# Agent Permissions

This document defines which operations a coding agent may perform on its own and which need
approval. [AGENTS.md](../../AGENTS.md#agent-boundaries) summarizes the boundaries; this document
details them and names the control that enforces each one.

## Permission Matrix

| Action | Agent without further approval | Additional approval |
|---|---|---|
| Read code, search locally | Yes | No |
| Change a work branch (`feature/*`, `fix/*`, `chore/*`) | Within the scope of the issue | Project policy |
| Run tests in an isolated environment | Yes, if safe | When the run has external side effects |
| Create issues and draft pull requests | According to project policy | Optional |
| Add dependencies | After review of the dependency | When the risk is elevated |
| Change `main` or `develop` directly | No | Exceptional case only |
| Change secrets, access rights or security settings | No | Yes |
| Publish a release | No | Yes |
| Destructive data operations | No | Yes |
| Merge a pull request | No | Yes |
| Create or move a tag | No | Yes |
| Approve its own potentially sensitive change | No | Not possible; a human reviews |
| Refactors or migrations unrelated to the issue | No | Yes, as a separate issue |

"Approval" means an explicit statement by an authorized person for this specific operation. An
approval for one operation does not extend to the next; every merge and every release needs its
own approval.

Examples of an elevated dependency risk: a new package with few maintainers or no releases, a
dependency that runs code at install time, a license that differs from the project license, or a
dependency that requests network or file system access the project does not need otherwise.

## Controls

Each restriction is enforced by a technical control where the repository and the GitHub plan
allow it. Where no technical control is available, the restriction is an **organizational
control**: it is binding, but it depends on agents and humans following it. Do not describe an
organizational control as technically enforced.

| Restricted action | Technical control | Without the technical control |
|---|---|---|
| Change `main` or `develop` directly | Branch protection or ruleset: require a pull request, block force pushes and deletion | Organizational: agents push only to work branches |
| Merge a pull request | Branch protection: required checks and reviews; the agent's token lacks merge rights | Organizational: only a human merges |
| Publish a release, create or move a tag | Release workflow in a protected environment with required reviewers; tag rulesets | Organizational: releases and tags only after explicit approval |
| Change secrets, access rights or security settings | Separate roles: the agent's token has no admin scope; secrets are stored as protected secrets, available only in protected environments | Organizational: the agent never requests these scopes |
| Destructive data operations | No production credentials in agent environments; production access only through protected environments | Organizational: explicit confirmation before every destructive command |
| Approve its own sensitive change | Required reviews from code owners for the paths listed in `.github/CODEOWNERS` | Organizational: a human reviews every change in these paths |
| Add dependencies with elevated risk | Dependency review in CI, where available | Organizational: the risk is stated in the pull request |
| Run tests with external side effects | CI jobs with minimal `permissions:`; no secrets for untrusted code | Organizational: ask before running |

Principles behind the controls:

- **Minimal tokens:** every token and every workflow gets only the permissions it needs.
- **Protected environments and secrets:** release and deployment credentials are reachable only
  from protected environments with required reviewers.
- **Separate roles:** the identity an agent uses cannot merge, release or administer the
  repository.

### Availability

Branch protection, rulesets and environments with required reviewers are not available in every
context. On GitHub Free they are available for public repositories, but may be unavailable for
private repositories. Bootstrap reports which controls could be applied. Until a technical control
is in place, the organizational control in the last column applies.

On a solo account, required reviews can block every merge, because an author's own approval does
not count; see [Review Policy](review-policy.md#solo-development).

## Escalation

When a task needs an operation that requires approval:

1. **Stop** before the operation. Do not try a workaround that achieves the same effect, for
   example a different command, tool or token.
2. **Ask** the responsible person: name the operation, why it is needed, its effects and how it
   can be undone.
3. **Wait** for an explicit approval of this operation. Silence, an earlier approval or an
   approval for a similar operation is not enough.
4. **Record** the approval and the result in the pull request or the issue.

If no approval is given, leave the operation undone and report it as open. If an agent detects
that a restricted operation happened without approval, it stops and reports it immediately.
