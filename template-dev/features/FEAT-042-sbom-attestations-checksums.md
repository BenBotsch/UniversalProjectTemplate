---
id: "FEAT-042"
title: "Generate SBOM, Checksums and Build Attestations"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "medium"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§9.4", "§11.1", "§17.5"]
dependencies: ["FEAT-041"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-042: Generate SBOM, Checksums and Build Attestations

## Objective

Every release publishes SHA-256 checksums, an SBOM and a build-provenance attestation bound to the
tagged commit.

## Background

§11.1 releases (checksums, attestations, signed tags/artifacts where suitable) and supply chain
(SBOM, build provenance). §9.4 for packages: checksums, SBOM/attestation, license notes.

## Scope

- Jobs in `release.yml`: `sbom` (e.g. Syft, SPDX or CycloneDX), `checksums`, `attest`
  (`actions/attest-build-provenance`).

### Out of Scope

- Signed git tags (documented as optional).

## Deliverables

| Path | Description |
|---|---|
| `.github/workflows/release.yml` (jobs) | `sbom`, `checksums`, `attest`; minimal `id-token: write`, `attestations: write` only there |
| `docs/governance/security-policy.md` (section) | How users verify checksums and attestations (`gh attestation verify`) |

## Requirements

1. **R1:** SBOM format documented and stable across releases.
2. **R2:** `SHA256SUMS` covers every published artifact.
3. **R3:** Attestation subject digests match the published artifacts.
4. **R4:** Plan limits (attestations for private repos) are detected and reported, not silently skipped.

## Tasks

- [ ] **T1:** SBOM and checksum jobs.
- [ ] **T2:** Attestation job and verification docs.

## Acceptance Criteria

- [ ] A test release contains SBOM, `SHA256SUMS` and an attestation that `gh attestation verify` accepts.

## Verification

```text
sha256sum -c SHA256SUMS
gh attestation verify <artifact> --repo <owner>/<repo>
```

## Agent Notes

- **Allowed paths:** `release.yml` jobs, doc section, this feature file, backlog status.
- **Requires approval:** running a test release.
- **Pitfalls:** Generate the SBOM from the built artifact or lockfiles, not from the whole runner filesystem.
