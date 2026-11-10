---
id: "ADR-0001"
title: "Use GitHub Issues as the Operational Source of Truth"
status: "accepted"
created_at: "2026-11-10"
related_issues: []
---

# ADR-0001: Use GitHub Issues as the Operational Source of Truth

## Context

Humans and coding agents need consistent tracking of work across one or more repositories. If the
status of a work item is kept in several places, such as Markdown files, boards and issues, the
copies drift apart and nobody knows which one is correct.

## Decision

GitHub Issues are authoritative for work items and their operational status, ownership, priority
and pull request links. GitHub Projects only present and group issues. Markdown documents hold
specifications, architecture, rules and long-lived decisions, and reference issues by number.

## Alternatives Considered

- **Status in Markdown files:** versioned and readable offline, but it duplicates the issue
  lifecycle and is not updated automatically by pull requests.
- **External issue tracker:** possible, but it separates work items from code, pull requests and
  repository automation.

## Consequences

- Documentation references issues instead of duplicating their lifecycle.
- Document statuses such as `planned` or `implemented` describe the document, not the work item.
- Automation that needs the status of work reads it from GitHub, not from Markdown.
