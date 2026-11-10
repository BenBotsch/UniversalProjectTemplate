# Branching and Releases

The repository uses a simplified GitFlow with a release branch `main` and an integration branch
`develop`. The model is configured in [`.project/workflow.yml`](../../.project/workflow.yml); this
document explains it. If the two disagree, the configuration is authoritative and this document is
corrected.

## Branch Model

| Branch | Purpose | Created from | Merged into |
|---|---|---|---|
| `main` | Released, stable code; default branch | Initial | Receives release and hotfix pull requests |
| `develop` | Integration of new development | `main` | `main` through a release pull request |
| `feature/*` | New functionality | `develop` | `develop` |
| `fix/*` | Regular bug fixes | `develop` | `develop` |
| `chore/*` | Maintenance, CI and documentation work | `develop` | `develop` |
| `hotfix/*` | Urgent fix of released code | `main` | `main`, then synchronized into `develop` |
| `release/*` | Optional release stabilization | `develop` | `main`, then synchronized into `develop` |

### Creating `develop`

In a project created from this template, `develop` is created from that project's own `main`.
Do not rely on branches copied from the template; they do not share a meaningful history with
the new repository.

```text
git switch main
git pull --ff-only origin main
git switch -c develop
git push -u origin develop
```

`main` stays the default branch. Pull requests for regular work target `develop` explicitly.

## Branch Names

```text
<purpose>/<issue-number>-<short-kebab-case-summary>
release/<X.Y.Z>
```

| Work | Branch | Pull request target |
|---|---|---|
| Feature for issue #42 | `feature/42-document-cropping` | `develop` |
| Bug fix for issue #77 | `fix/77-empty-input` | `develop` |
| Maintenance for issue #88 | `chore/88-ci-refactor` | `develop` |
| Hotfix for issue #105 | `hotfix/105-credential-leak` | `main` |
| Release 1.4.0 | `release/1.4.0` | `main` |

Branch names must match `branching.branch_name_pattern` in `workflow.yml`:

```text
^((feature|fix|hotfix|chore)/[0-9]+-[a-z0-9]+(-[a-z0-9]+)*|release/[0-9]+\.[0-9]+\.[0-9]+)$
```

The summary is lowercase kebab-case without leading, trailing or double hyphens. Documentation,
CI and refactoring work uses `chore/` or the branch type of the issue; the commit type still says
`docs`, `ci` or `refactor`. A branch without an issue number is an exception that needs a reason
in the pull request.

## Merge Strategy

| Pull request | Strategy | Reason |
|---|---|---|
| Work branch into `develop` | Squash merge | One conventional commit per pull request; the title becomes the commit message |
| Release into `main` | Merge commit | Keeps the commits of `develop` in the history of `main` |
| Hotfix into `main` | Squash merge | One conventional commit per hotfix, like work branches into `develop` |
| Synchronization of `main` into `develop` | Merge commit | `develop` must contain every commit of `main`; a squash would make the branches diverge |

The strategy is decided in
[ADR-0004](../architecture/adr/0004-merge-policy.md) and
[ADR-0005](../architecture/adr/0005-squash-hotfixes.md); it is configured in
`pull_requests.merge_strategy` in `workflow.yml`. Rebase merges are disabled. Before a project
changes the strategy, record a new ADR in [`docs/architecture/adr/`](../architecture/adr/README.md)
and update the configuration and this section together. GitHub cannot enforce a merge method per
source branch, so the person who merges picks the method from this table.

## Synchronizing `main` into `develop`

Two branches mean extra synchronization work. After each of these events, open a pull request
from `main` into `develop` and merge it with a merge commit:

- A release pull request was merged into `main`, so that `develop` contains the release commit
  and any release fixes.
- A hotfix was merged into `main`.
- A Dependabot security update was merged into `main`. Dependabot version updates can target
  `develop`, but security update pull requests target the default branch.

Resolve conflicts in the synchronization pull request, never by force-pushing either branch.

## Dependency Updates

[`.github/dependabot.yml`](../../.github/dependabot.yml) configures Dependabot version updates:

- Version update pull requests target `develop`, are opened weekly and carry the labels
  `area:ci-cd` and `type:task`.
- Their commit messages and titles start with `ci(deps):`, so they follow the commit conventions.
- The template configures only the `github-actions` ecosystem. Add an ecosystem such as `pip`,
  `npm` or `docker` only when the project contains its manifest files. Use only labels that exist
  in `.project/labels.yml`.
- Security update pull requests ignore `target-branch` and always target the default branch
  (`main`). After merging one, synchronize `main` into `develop` as described in
  [Synchronizing `main` into `develop`](#synchronizing-main-into-develop).

## Semantic Versioning

Versions follow [Semantic Versioning 2.0.0](https://semver.org/):

| Change | Example | Triggered by |
|---|---|---|
| Patch | `1.0.0` → `1.0.1` | `fix`, `perf` and other changes without new functionality |
| Minor | `1.0.0` → `1.1.0` | `feat` |
| Major | `1.0.0` → `2.0.0` | Breaking change (`!` or `BREAKING CHANGE:`) |
| Release candidate | `1.1.0-rc.1` | Optional pre-release before a final release |

**Versions `0.y.z`** mark initial development; the public interface is not stable. During `0.x`:

- A breaking change increments the minor version, for example `0.3.2` → `0.4.0`.
- New functionality and fixes increment the patch version, for example `0.3.2` → `0.3.3`.
- `1.0.0` is released when the public interface is declared stable.

Tags have the form `vX.Y.Z` (`releases.tag_pattern` in `workflow.yml`). The pattern currently
allows only final releases; using release-candidate tags requires extending it first.

## Release Structure

- `main` contains released code only. A tag `vX.Y.Z` is created only on the approved release
  commit on `main`.
- Release notes are grouped by features, fixes, performance, security and breaking changes. They
  are generated from pull request labels.
- [CHANGELOG.md](../../CHANGELOG.md) follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- Release artifacts are built reproducibly in CI, not on a developer machine.
- Release candidates and staged publication are optional.
- Packages document target platforms, minimum versions, checksums, SBOM or attestation and
  license information.
- A human approves every publication.

## Release Criteria

A release is approved only if all of these are true:

1. All required checks succeeded; a skipped check does not count as passed.
2. The version number fits the changes, and the changelog is updated.
3. There are no unresolved critical security findings.
4. Breaking changes are clearly documented.
5. Compatibility with the supported platforms is documented.
6. The artifacts are unambiguously linked to the tagged commit.
7. A rollback or hotfix plan is available.
8. An authorized person, or a protected approval mechanism, approved the release.

## Branch Protection

| Rule | `main` | `develop` |
|---|---|---|
| Prevent direct pushes | Yes | Yes |
| Require a pull request before merge | Yes | Yes |
| Require the `quality-gate` check | Yes | Yes |
| Require resolved conversations | Yes | Yes |
| Prevent force pushes | Yes | Yes |
| Prevent deletion | Yes | Yes |
| Require review | Depends on team size | Depends on team size |
| Require release approval | Yes | Not applicable |

`quality-gate` is the only required status check; it fails when a gate that applies was skipped,
failed or is not implemented. Do not require individual jobs, because GitHub treats a skipped job
as passed. See the [Quality Model](quality-model.md#enforcement-in-ci).

Whether these rules can be **enforced** depends on repository visibility and the GitHub plan.
Branch protection and rulesets are available for public repositories on GitHub Free, but may be
unavailable for private repositories on the same plan. Where a rule cannot be enforced
technically, it is an organizational rule that every contributor follows; do not report it as
enforced. Check the current plan conditions before setting up protection. Review rules for small
teams are described in the [Review Policy](review-policy.md). How `project-bootstrap
apply-rulesets` enforces these rules, and what it reports where it cannot, is described in
[Branch Protection](branch-protection.md).
