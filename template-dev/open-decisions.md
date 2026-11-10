# Open Decisions

Source: §19.1 of the [specification](specification.md#191-offene-architekturentscheidungen).
A decision listed in a feature's `blocked_by_decisions` blocks that feature until it is recorded.
Decisions marked **non-blocking** have a proposed default; features use the default and must not
hard-code anything that prevents changing it later.

Decisions are made by a human maintainer. Agents may prepare an options analysis but must not
record a decision themselves. Once decided, record it as an ADR under `docs/architecture/adr/`
(created by `FEAT-003`), set **Status** below to `decided`, link the ADR, and unblock the features.

| ID | Question | Blocks | Proposed default | Status |
|---|---|---|---|---|
| DEC-01 | Implementation language and distribution of the bootstrap tool (Python package, PowerShell module, both) | FEAT-024 | Python 3.12+ CLI distributed via `pipx`/`uv tool`; PowerShell only for phase A (`FEAT-023`) | decided 2026-11-10: default accepted, [ADR-0002](../docs/architecture/adr/0002-python-bootstrap-cli.md) |
| DEC-02 | Merge policy: squash vs. merge commits (drives Conventional-Commit changelog) | FEAT-040 | Squash merge into `develop`, PR title is the commit message; merge commit for release PRs `develop` → `main` | open |
| DEC-03 | Is GitHub Projects a mandatory planning standard? | FEAT-010 | Optional, provisioned when `bootstrap.yml` enables it | open |
| DEC-04 | Are native GitHub Issue Types synchronized in addition to `type:*` labels? | non-blocking (FEAT-018, FEAT-028) | Labels are authoritative; native types optional later | open |
| DEC-05 | How are `priority:*` and `status:*` set initially on issue creation? | non-blocking (FEAT-007, FEAT-018) | Forms set `status:triage`; `priority:*` is required only from `status:ready` on | open |
| DEC-06 | Which release automation produces SemVer and changelog? | FEAT-040 | Evaluate release-please vs. a tested in-house script; decision after `FEAT-039` | open |
| DEC-07 | Which security checks are available for private GitHub Free repositories? | FEAT-043 | Gitleaks + Dependabot always; CodeQL/secret scanning only where the plan allows; report gaps | open |
| DEC-08 | Extract reusable CI workflows early or after the first projects? | FEAT-038 | After two real projects use the same profile | open |
| DEC-09 | Does bootstrap and dashboard run permanently without an external server? | FEAT-053 | Yes for bootstrap (local CLI); dashboard reads exported data first | open |
| DEC-10 | How are agent actions identified, logged and approved? | FEAT-050, FEAT-054 | Dedicated bot identity or labelled PRs, `agent:*` labels, audit log artifact per run | open |

## Additional human-only choices

These are not architecture decisions but need a human before the affected task can finish:

| Choice | Affected | Note |
|---|---|---|
| License of the template repository itself | FEAT-002/T4 | Decided 2026-11-10: MIT License |
| Owner/team handle for CODEOWNERS in the template | FEAT-011 | Decided 2026-11-10: `@BenBotsch`; derived projects inherit it, `FEAT-028` changes it |
| Creating the GitHub repository and marking it as template | FEAT-048, FEAT-026 | Outward-facing action; requires explicit approval |
