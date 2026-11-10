# Branch Protection

This document describes how `project-bootstrap apply-rulesets` enforces the protection rules of
[Branching and Releases](branching-and-releases.md#branch-protection), what each GitHub plan
allows, and what to do where GitHub cannot enforce them.

## What Is Applied

`apply-rulesets` creates three repository rulesets. Branch names come from `project.yml`, the
merge methods from `pull_requests.merge_strategy` in `workflow.yml` and everything else from the
`protection` section of `bootstrap.yml`.

| Ruleset | Applies to | Rules |
|---|---|---|
| `bootstrap-default-branch` | `refs/heads/<default_branch>` | No deletion, no force push, changes only through a pull request, resolved conversations, allowed merge methods, required status checks |
| `bootstrap-development-branch` | `refs/heads/<development_branch>` | Same as the default branch |
| `bootstrap-release-tags` | `refs/tags/<release_tag_pattern>`, for example `v*` | Release tags cannot be moved or deleted |

Both branch rulesets allow every merge method that `merge_strategy` uses, because each branch
receives pull requests of both kinds: `main` gets merge commits from releases and squash merges
from hotfixes, `develop` gets squash merges from work branches and merge commits from the
synchronization of `main`.

The rulesets have **no bypass actors**: the rules also apply to repository administrators and
to agents with an administrator token. The tool owns the rulesets with these names and replaces
their content when it differs from the configuration; change them in `bootstrap.yml`, not on
GitHub. Rulesets with other names are reported and never changed.

## Review Mode

| `protection.mode` | Required approvals | Code owner review | Stale approvals dismissed |
|---|---|---|---|
| `solo` | 0 | No | No |
| `team` | 1 | Yes | Yes |

GitHub does not count an author's approval of their own pull request. On a project with one
maintainer, a required approval would block every merge, so `solo` keeps the pull request and
the status checks but requires no approval. Switch to `team` when a second maintainer joins. See
the [Review Policy](review-policy.md#solo-development).

## Required Status Checks

`quality-gate` is the only required check. GitHub blocks every merge on a required check that
never reports, so `apply-rulesets` requires a check only after it has reported once on the head
of the protected branch. Until then the report contains a `skipped` change such as
`bootstrap-default-branch:quality-gate` with the reason "never ran on 'main'; not required yet".

To complete the protection of a new repository:

1. Push to the default and the development branch, or merge a pull request into each, so that
   CI runs there.
2. Run `apply-rulesets --apply` again. The check is then required, bound to the GitHub App that
   ran it, so a commit status of the same name from elsewhere does not satisfy it.

A check that a ruleset already requires stays required, even if the newest commit has no run yet.
A misspelled check name never reports and therefore stays `skipped`; the report shows it.

## Plans and Visibility

| Repository | Rulesets | Result of `apply-rulesets` |
|---|---|---|
| Public, any plan | Available | Rulesets are applied |
| Private, GitHub Free | Not available; classic branch protection neither | `UNPROTECTED`, exit code `1` |
| Private, GitHub Pro, Team or Enterprise | Available according to GitHub's documentation | Rulesets are applied; not yet tested by this project |

The tool detects the case from GitHub's answer to the rulesets API and does not fall back to
classic branch protection: on GitHub Free it is unavailable for private repositories as well,
and on every other plan rulesets cover the same rules. Organization rulesets are out of scope;
they are listed as unmanaged rulesets when they apply to the repository.

## Unprotected Repositories

When GitHub offers no rulesets, every ruleset is reported as `failed` with a reason that starts
with `UNPROTECTED`, and the run exits with `1`. Nothing is changed. The options are:

- Make the repository public, if its content allows it, and run `apply-rulesets` again.
- Upgrade the account or organization to a plan with rulesets for private repositories.
- Accept that the rules are organizational only. Then do not claim technical enforcement, and
  run the tool with `--allow-unprotected`, which reports the rulesets as `skipped` and exits with
  `0`. Use it only after this decision has been made and recorded; agents need approval for it,
  see [Agent Permissions](agent-permissions.md).

## Emergency Changes

There is no bypass. An administrator who must push directly, for example to repair a broken
default branch, sets the enforcement of the ruleset to `Disabled` in the repository settings,
makes the change and records the reason in the related issue. The next `apply-rulesets --apply`
run reports the ruleset as `update` and enables it again.
