---
id: "EPIC-09"
title: "Releases and Supply Chain"
phase: 4
status: "planned"
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# EPIC-09: Releases and Supply Chain

## Goal and Value

Traceable, verified, reproducible releases with changelog, SemVer, protected release workflow, SBOM and attestations, extended security scanning, hotfix and rollback.

## Scope and Deliverables

- `.github/release.yml` and Keep-a-Changelog process (§9.4, §9.5)
- SemVer automation (`DEC-02`, `DEC-06`)
- Protected `release.yml` with environment approval (§9.6, §11.2)
- SBOM, checksums, attestations (§11.1)
- CodeQL, dependency review, Scorecard (§11.1, §11.5, `DEC-07`)
- Hotfix, back-merge, rollback (§8.1, §8.2)
- Self-hosted runner trust model (§11.3)

## Non-Goals

- Publishing to package registries of specific ecosystems beyond profile examples

## Features

| ID | Title | Phase | Priority | Depends on | Status |
|---|---|---|---|---|---|
| [FEAT-039](../features/FEAT-039-release-notes-and-changelog.md) | Configure Release Notes Categories and Changelog Process | 4 | high | 008, 012 | planned |
| [FEAT-040](../features/FEAT-040-semver-automation.md) | Automate Semantic Version and Changelog Proposals | 4 | medium | 019, 039 | planned |
| [FEAT-041](../features/FEAT-041-protected-release-workflow.md) | Add Protected Release Workflow with Environment Approval | 4 | high | 017, 020, 040 | planned |
| [FEAT-042](../features/FEAT-042-sbom-attestations-checksums.md) | Generate SBOM, Checksums and Build Attestations | 4 | medium | 041 | planned |
| [FEAT-043](../features/FEAT-043-extended-security-scanning.md) | Add CodeQL, Dependency Review and OpenSSF Scorecard | 4 | medium | 017 | planned |
| [FEAT-044](../features/FEAT-044-hotfix-and-rollback.md) | Define Hotfix, Back-Merge and Rollback Process | 4 | medium | 012, 041 | planned |
| [FEAT-045](../features/FEAT-045-self-hosted-runner-policy.md) | Document Self-Hosted Runner Trust Model | 4 | low | 017 | planned |

## Risks and Dependencies

- Security features unavailable on private Free repositories (`DEC-07`)
- Release credentials exposed to untrusted runs
- External feature dependencies: `FEAT-008`, `FEAT-012`, `FEAT-017`, `FEAT-019`, `FEAT-020`
- Blocking decisions: `DEC-02`, `DEC-06`, `DEC-07` (see [open-decisions.md](../open-decisions.md))

## Success Criteria

- A test release is traceable from tag to commit, verified by attestation and reproducibly published
