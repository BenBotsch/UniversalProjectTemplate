---
id: "ADR-0004"
title: "Squash into develop, Merge Commits into main"
status: "accepted"
created_at: "2026-11-10"
related_issues: ["#7"]
---

# ADR-0004: Squash into develop, Merge Commits into main

## Context

The changelog and the SemVer bump are derived from Conventional Commits (`FEAT-040`). Which
commits reach a branch depends on the merge method: a squash merge produces one commit per pull
request whose message is the pull request title; a merge commit keeps every commit of the source
branch. `main` and `develop` must not diverge, because releases and hotfixes are synchronized
between them. `pull_requests.merge_strategy` in `.project/workflow.yml` already used the proposed
default of decision `DEC-02`, and `project-bootstrap configure-repo` derives the allowed merge
methods of a repository from it.

## Decision

Work branches are squash-merged into `develop`; the pull request title is the commit message and
must be a Conventional Commit. Release pull requests from `develop` into `main` and
synchronization pull requests from `main` into `develop` use merge commits. Rebase merges are
disabled.

- `pull_requests.merge_strategy` stays `into_development_branch: "squash"` and
  `release_into_default_branch: "merge"`.
- The pull request validator checks the title; commit messages on work branches should still be
  conventional, but only the title reaches `develop`.
- The merge method of hotfix pull requests into `main` is not part of this decision. Until it is
  decided, both squash and merge commits stay allowed.

## Alternatives Considered

- **Squash everywhere:** a squashed release creates a commit on `main` that `develop` does not
  contain, so every release would need extra synchronization and conflicts become likely.
- **Merge commits everywhere:** the history of `develop` would contain every intermediate commit,
  and the changelog would depend on the quality of each commit message instead of the reviewed
  pull request title.
- **Rebase merges:** rewrite commit identities and make synchronization between the two branches
  harder; GitHub also cannot enforce a conventional message for each rebased commit.

## Consequences

- The changelog of `FEAT-040` is built from the squash commits on `develop` that a release brings
  to `main`.
- Pull request titles need the same care as commit messages; the pull request validator enforces
  their format.
- A repository allows squash and merge commits; `configure-repo` disables rebase merges.
- Follow-up: decide the merge method for hotfix pull requests.
