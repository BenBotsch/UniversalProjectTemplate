# Roadmap

Source: §18 and §21.7 of the [specification](specification.md#18-priorisierte-roadmap).
A phase is complete when its exit gate is demonstrated, not when all files exist.

## Phase 1: Universal Foundation (MVP)

**Goal:** A language-agnostic base that is usable immediately.

| Epic | Features |
|---|---|
| [EPIC-01 Repository Foundation](epics/EPIC-01-repository-foundation.md) | FEAT-001, FEAT-002, FEAT-003 |
| [EPIC-02 Agent-First Governance](epics/EPIC-02-agent-first-governance.md) | FEAT-004, FEAT-005, FEAT-006 |
| [EPIC-03 Issue Management](epics/EPIC-03-issue-management.md) | FEAT-007, FEAT-008, FEAT-009 |
| [EPIC-04 Branching and Pull Requests](epics/EPIC-04-branching-and-pull-requests.md) | FEAT-011, FEAT-012 |
| [EPIC-05 Project Configuration and Schemas](epics/EPIC-05-project-configuration.md) | FEAT-013, FEAT-014 |

**Exit gate:** A new repository can be created from the template, and structured issues and pull
requests are usable.

## Phase 2: GitHub Automation and Quality

**Goal:** Repeatable setup and enforced metadata quality.

| Epic | Features |
|---|---|
| [EPIC-06 Universal CI and Validation](epics/EPIC-06-universal-ci-and-validation.md) | FEAT-015 to FEAT-022 |
| [EPIC-07 Bootstrap Tool](epics/EPIC-07-bootstrap-tool.md) | FEAT-023 to FEAT-030 |
| [EPIC-03 Issue Management](epics/EPIC-03-issue-management.md) | FEAT-010 (Projects board, needs the CLI core) |
| [EPIC-10 Template Lifecycle](epics/EPIC-10-template-lifecycle.md) | FEAT-048 (backlog migration) |

**Exit gate:** Two independently created test repositories have consistent rules and a working CI
base; bootstrap is idempotent.

## Phase 3: Technology Profiles

| Epic | Features |
|---|---|
| [EPIC-08 Technology Profiles](epics/EPIC-08-technology-profiles.md) | FEAT-031 to FEAT-038, FEAT-055 |

**Exit gate:** Each profile has at least one example project with verified lint, test and build jobs.

## Phase 4: Releases and Security

| Epic | Features |
|---|---|
| [EPIC-09 Releases and Supply Chain](epics/EPIC-09-releases-and-supply-chain.md) | FEAT-039 to FEAT-045 |
| [EPIC-10 Template Lifecycle](epics/EPIC-10-template-lifecycle.md) | FEAT-046, FEAT-047 |

**Exit gate:** A test release is traceable, verified and reproducibly published.

## Phase 5: Agents and Dashboard

| Epic | Features |
|---|---|
| [EPIC-11 Agents and Dashboard](epics/EPIC-11-agents-and-dashboard.md) | FEAT-049 to FEAT-054 |

**Exit gate:** Agent actions are traceable, bounded, reviewable, and support several repositories
consistently.

## Ordering inside phases

§21.7 sets the first-implementation order across phases:

1. **First:** `AGENTS.md`, issues, labels, PR template, project configuration, minimal CI, README,
   security policy, label and branch bootstrap.
2. **Then:** issue and PR validators, test profiles for the first languages, rulesets, Dependabot,
   release process.
3. **Later:** reusable workflows, SBOM and attestations, multi-repository audit, dashboard and agent
   automation.

[backlog.md](backlog.md) ranks all features accordingly. Minimal CI (`FEAT-016`) and the phase A
bootstrap script (`FEAT-023`) are therefore ranked directly after the phase 1 features they need.
