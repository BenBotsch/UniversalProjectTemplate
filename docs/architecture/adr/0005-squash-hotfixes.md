---
id: "ADR-0005"
title: "Squash Hotfixes into main"
status: "accepted"
created_at: "2026-11-10"
related_issues: ["#12"]
---

# ADR-0005: Squash Hotfixes into main

## Context

[ADR-0004](0004-merge-policy.md) squash-merges work branches into `develop`, uses merge commits
for releases into `main` and for the synchronization of `main` into `develop`, and leaves the
merge method of hotfix pull requests into `main` open. A hotfix branch starts from `main`, targets
`main` and is synchronized into `develop` afterwards (`branching.branch_types.hotfix` in
`.project/workflow.yml`). The changelog of `FEAT-040` is derived from Conventional Commits on
`main`.

## Decision

Hotfix pull requests are squash-merged into `main`; the pull request title is the commit message
and must be a Conventional Commit, usually `fix:`. The synchronization pull request from `main`
into `develop` that follows stays a merge commit, as decided in ADR-0004.

- `pull_requests.merge_strategy.hotfix_into_default_branch` in `.project/workflow.yml` is
  `"squash"`; the field is new in schema version `1.2`.
- The allowed merge methods of a repository do not change: `main` and `develop` both allow squash
  and merge commits, because each receives one kind of pull request with each method.

## Alternatives Considered

- **Merge commit:** brings every commit of the hotfix branch to `main`, so the changelog would
  depend on each intermediate commit message instead of the reviewed pull request title, unlike
  work branches into `develop`.
- **Leave it open:** both methods stay allowed, and the changelog of a patch release depends on
  which method the person who merges picks.

## Consequences

- Each hotfix is exactly one commit on `main`, and a patch release lists one entry per hotfix.
- The squash commit exists only on `main` until the synchronization pull request brings it to
  `develop`; that pull request must not be squashed, or the branches diverge.
- GitHub cannot enforce a merge method per target branch or source branch. The method is a rule
  for the person who merges, documented in
  [Branching and Releases](../../governance/branching-and-releases.md#merge-strategy).
