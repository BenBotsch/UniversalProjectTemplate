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

- [Issue Management](governance/issue-management.md): label taxonomy, issue forms and form field mapping.
- [Agent Workflow](governance/agent-workflow.md): agent adapter files and how to verify that tools pick them up.

## Architecture

- [ADR Process](architecture/adr/README.md): when and how to record architecture decisions.
- [ADR Template](architecture/adr/0000-adr-template.md): starting point for a new ADR.
- [ADR-0001: Use GitHub Issues as the Operational Source of Truth](architecture/adr/0001-use-github-issues.md)

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
