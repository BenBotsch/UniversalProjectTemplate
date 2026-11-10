---
id: "FEAT-036"
title: "Add Docker and Container Profile"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "medium"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.2", "§10.3", "§11.1"]
dependencies: ["FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-036: Add Docker and Container Profile

## Objective

The `docker` profile adds Dockerfile linting, image build and an image vulnerability scan; it can
be combined with any language profile.

## Background

§3.3 names Docker; §10.3 tools (Hadolint, Trivy, BuildKit); §11.1 container baseline (image
scanning, minimal images, no root where possible).

## Scope

- `Dockerfile` template, `.dockerignore`, workflow with build (no push) and scan.

### Out of Scope

- Image publishing (`FEAT-041`), Kubernetes manifests.

## Deliverables

| Path | Description |
|---|---|
| `profiles/docker/profile.yml` | Manifest, combinable (`requires_profiles: []`) |
| `profiles/docker/files/Dockerfile`, `.dockerignore` | Non-root user, pinned base image digest placeholder |
| `profiles/docker/files/.github/workflows/docker.yml` | Jobs `docker-lint` (Hadolint), `docker-build` (BuildKit via `docker buildx`), `container-scan` (Trivy, fail on critical/high) |
| `profiles/docker/README.md` | Gate mapping, how to update base image digest |

## Requirements

1. **R1:** Build job has no registry credentials and does not push.
2. **R2:** Scan severity threshold configurable; default fails on `CRITICAL,HIGH`.
3. **R3:** Dependabot ecosystem `docker` added via manifest.
4. **R4:** Jobs map to gates `lint`, `build`, `security_scan`.

## Tasks

- [ ] **T1:** Dockerfile and ignore file.
- [ ] **T2:** Workflow with lint, build, scan.

## Acceptance Criteria

- [ ] Profile applies cleanly, image builds, and scan runs with a clear pass/fail result.

## Verification

```text
hadolint Dockerfile && docker build -t local/test . && trivy image --exit-code 1 --severity CRITICAL,HIGH local/test
```

## Agent Notes

- **Allowed paths:** `profiles/docker/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Base image digests go stale; rely on Dependabot `docker` updates rather than tags.
