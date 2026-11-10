# Development Workflow

This is the path of a change from issue to release. The details of each step are in the linked
documents.

## Regular Changes

1. **Specify the issue.** Fill in the issue form, complete triage and set `status:ready`; see
   [Issue Management](issue-management.md#triage-procedure).
2. **Create the branch** from `develop` with the issue number, for example
   `feature/42-auto-crop` or `fix/77-empty-response`; see
   [Branch Names](branching-and-releases.md#branch-names). Set the issue to `status:in-progress`.
3. **Commit in small steps** with [Conventional Commits](commit-conventions.md).
4. **Open a pull request against `develop`.** Use a Conventional Commit title, reference the
   issue with `Refs: #<number>` and fill in every section of the template. Set the issue to
   `status:review`.
5. **Run the checks and get a review.** CI runs automatically; run the local checks listed in
   [CONTRIBUTING.md](../../CONTRIBUTING.md#tests-and-checks) before. Review follows the
   [Review Policy](review-policy.md).
6. **Merge into `develop`** with the configured
   [merge strategy](branching-and-releases.md#merge-strategy). Close the issue if its acceptance
   criteria are met; merges into `develop` do not close it automatically.

## Releases

<!-- The numbering continues the steps above. -->
<!-- markdownlint-disable MD029 -->
7. **Test the release candidate** from a defined state of `develop`, optionally on a
   `release/X.Y.Z` branch.
8. **Open a release pull request into `main`** and get it approved against the
   [release criteria](branching-and-releases.md#release-criteria).
9. **Tag the release** as `vX.Y.Z`, only on the approved release commit on `main`.
10. **Build, attest and publish the artifacts** in CI, and update the
    [changelog](../../CHANGELOG.md).
11. **Synchronize `main` into `develop`**, including hotfixes and release fixes; see
    [Synchronizing `main` into `develop`](branching-and-releases.md#synchronizing-main-into-develop).
<!-- markdownlint-enable MD029 -->

## Hotfixes

An urgent fix of released code starts from `main` instead of `develop`:

1. Create `hotfix/<issue-number>-<summary>` from `main`.
2. Open the pull request against `main`; the release criteria apply.
3. Tag and publish a patch release.
4. Synchronize `main` into `develop`.
