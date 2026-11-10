# Documentation Index

Compact entry point for humans and coding agents. Each line points to an area that contains
content. When you add a document, add one line in the matching section; when you add a new area,
add a section.

## How to Read This Repository

Do not load the whole repository into context. Read in this order and stop as soon as you have
what the task needs:

1. [AGENTS.md](../AGENTS.md): binding rules for contributors and coding agents.
2. This index: locate the documents relevant to the task.
3. The relevant sections of those documents, and any `AGENTS.md` in the directories you change.
4. When your change affects documented behavior, update the affected documents in the same pull
   request.

## Project

- [Project Overview](../README.md): purpose, requirements, quick start and structure.
- [Contributing](../CONTRIBUTING.md): setup, branches, commits, checks and pull requests.
- [Security Policy](../SECURITY.md): private vulnerability reporting.
- [Support](../SUPPORT.md): where to ask questions.
- [Changelog](../CHANGELOG.md): notable changes per release.
- [Project Configuration](../.project/README.md): machine-readable metadata in `.project/`.

## Governance

- [Issue Management](governance/issue-management.md): issue types, label taxonomy, metadata rules (`ISSUE-R*`), status lifecycle, hierarchy, issue forms and triage.
- [Development Workflow](governance/development-workflow.md): the path of a change from issue to release, including hotfixes.
- [Branching and Releases](governance/branching-and-releases.md): branch model and names, merge strategy, SemVer, release criteria and branch protection.
- [Branch Protection](governance/branch-protection.md): the rulesets `apply-rulesets` creates, review modes, required checks, plan limits and unprotected repositories.
- [Commit Conventions](governance/commit-conventions.md): Conventional Commits, types, issue references and breaking changes.
- [Review Policy](governance/review-policy.md): review checklist, elevated attention and solo development.
- [Agent Workflow](governance/agent-workflow.md): agent working cycle, reading strategy, pull request evidence, reporting and adapter files.
- [Agent Permissions](governance/agent-permissions.md): what agents may do without approval, enforcing controls and escalation.
- [Security Policy for Development and CI](governance/security-policy.md): security baseline, workflow review checklist, secret scanning and fork pull requests.
- [Quality Model](governance/quality-model.md): quality characteristics, measurable gates, the quality-gate check and flaky tests.
- [Documentation Policy](governance/documentation-policy.md): where information lives, when to update documents and when to write an ADR.

## Architecture

- [ADR Process](architecture/adr/README.md): when and how to record architecture decisions.
- [ADR Template](architecture/adr/0000-adr-template.md): starting point for a new ADR.
- [ADR-0001: Use GitHub Issues as the Operational Source of Truth](architecture/adr/0001-use-github-issues.md)
- [ADR-0002: Implement the Bootstrap Tool as a Python CLI](architecture/adr/0002-python-bootstrap-cli.md)
- [ADR-0003: Aggregate CI Results in a Single Quality Gate Job](architecture/adr/0003-aggregate-ci-in-one-quality-gate.md)
- [ADR-0004: Squash into develop, Merge Commits into main](architecture/adr/0004-merge-policy.md)

## Features

- [Feature Specifications](features/README.md): how specifications relate to issues, document
  statuses and the specification template.

## Planning

- [Planning](planning/README.md): roadmaps, milestones and release planning.

## Sources of Truth

| Information | Authoritative source |
|---|---|
| Operational status, ownership, priority, pull request links | GitHub Issues |
| Portfolio and board views, additional planning fields | GitHub Projects |
| Specifications, architecture, rules, long-lived decisions | Markdown in this repository |
| Repository and tooling configuration | `.project/` |
| Published versions | GitHub Releases and tags |

Link to the authoritative source instead of copying its content. Do not create new files that
duplicate status or configuration kept elsewhere.
