# Review Policy

Every change reaches `develop` or `main` through a pull request. Review makes sure that the change
does what its issue asks for, nothing else, and that the evidence in the pull request is real.

## What Reviewers Check

- The change satisfies the acceptance criteria of the linked issue and contains no unrelated
  changes.
- The pull request title follows the [commit conventions](commit-conventions.md) and the target
  branch matches the [branch model](branching-and-releases.md#branch-names).
- Every section of the pull request template is filled in. "Tests Executed" contains commands
  that were actually run and their actual results.
- Tests cover the changed behavior, including relevant failure paths. No test was removed,
  skipped or weakened to make the pull request pass.
- Affected documentation is updated, and significant decisions are recorded as ADRs.
- The release-relevant labels on the pull request are correct: the `type:*` label,
  `impact:breaking` or `impact:security` where they apply, and `skip-changelog` for changes without
  user-visible effect.

The author resolves or answers every review conversation before merge.

## Elevated Attention

Some changes can weaken the safeguards of the repository itself. Review them line by line, and do
not approve them without understanding every effect:

- CI and automation: `.github/workflows/` and other files in `.github/`.
- Project configuration: `.project/`, including labels, quality gates and branch rules.
- Secrets, tokens, permissions and access rights, including `permissions:` blocks in workflows.
- Release mechanics: versioning, tagging, publishing and changelog generation.
- Security policy: `SECURITY.md`.
- Architecture decisions: `docs/architecture/`.

These paths are listed in `pull_requests.elevated_review_paths` in
[`.project/workflow.yml`](../../.project/workflow.yml) and in
[`.github/CODEOWNERS`](../../.github/CODEOWNERS).

## Changes by Agents

Pull requests prepared by coding agents follow the same review rules as any other. An agent never
approves or merges its own potentially sensitive changes; a human reviews them. The boundaries are
defined in [AGENTS.md](../../AGENTS.md#agent-boundaries).

## Solo Development

A project with a single maintainer still uses pull requests, but adapts review:

- GitHub does not count an author's own approval as a review. Do not require approving reviews or
  code owner approval on a solo account, or every merge blocks.
- CI checks and the pull request template remain mandatory; they are the review evidence.
- Before merging, the maintainer reviews the complete diff of the pull request, with the
  checklist above.
- Manual approval rules must not assume that a second person exists.
- In private repositories on GitHub Free, branch protection may not be enforceable. Treat the
  rules as organizational rules and do not claim technical enforcement.

When a second maintainer joins, require one approving review from someone other than the author.
