---
id: "ADR-0002"
title: "Implement the Bootstrap Tool as a Python CLI"
status: "accepted"
created_at: "2026-11-10"
related_issues: []
---

# ADR-0002: Implement the Bootstrap Tool as a Python CLI

## Context

Bootstrap creates and configures GitHub repositories from this template: labels, branches,
repository settings, rulesets, project initialization and audits. The first stage is a PowerShell
script that calls the GitHub CLI (`scripts/bootstrap/New-ProjectRepository.ps1`). It covers
repository creation, labels and the `develop` branch, but it is not designed for declarative
configuration, API pagination, rate limits, retries or detailed plan and apply reports.

The full tool must run on Windows, Linux and macOS, in CI and locally, be testable with API mocks,
and read the configuration in `.project/`. The repository validators in `scripts/ci/` are already
written in Python 3.12.

## Decision

The bootstrap tool is a Python 3.12+ command line application, distributed as a package that is
installed with `pipx` or `uv tool`. PowerShell is used only for the existing first-stage script;
new bootstrap features are added to the Python CLI.

- The CLI is developed and released in its own repository; this template contains only the
  configuration it reads.
- The CLI reads the configuration in `.project/` and validates it with the existing schemas.
- It accesses GitHub through the REST and GraphQL APIs with token authentication, not by wrapping
  the GitHub CLI.
- It runs as a dry run by default and changes something only when asked to apply.
- The PowerShell script stays usable until the CLI covers its steps, and is then retired.

## Alternatives Considered

- **PowerShell module:** runs on Windows PowerShell without installation and is cross-platform
  with PowerShell 7, but PowerShell 7 is not installed by default on Linux and macOS, YAML support
  needs an extra module, and the test and packaging ecosystem is smaller.
- **Both Python and PowerShell:** two implementations of the same behavior drift apart and double
  the test effort.
- **Go or another compiled language:** single binaries are easy to distribute, but the project's
  tooling and validators are in Python, and contributors would need a second toolchain.

## Consequences

- Users install Python 3.12 or later and `pipx` or `uv`; the README of the tool documents this.
- The validators and the CLI can share code for reading `.project/` and checking schemas.
- GitHub API access is tested with mocked HTTP responses; no test needs a real repository.
- Until the CLI replaces it, the PowerShell script and the CLI must produce the same labels and
  branches.
