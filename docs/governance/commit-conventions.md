# Commit Conventions

Commits and pull request titles follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Release notes and
version numbers are derived from them, so a wrong type is a wrong release note.

## Syntax

```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

- **type:** one of the allowed types below, lowercase.
- **scope:** optional; the affected component in lowercase, for example `api`, `parser`, `ci`.
  Use a scope that already appears in the history before inventing a new one.
- **description:** imperative mood, lowercase start, no trailing period, for example
  `add image analysis endpoint`.
- **body:** optional; explains why the change was made, wrapped at about 72 characters.
- **footers:** `Refs: #<number>`, `BREAKING CHANGE: <text>` and other `Token: value` lines.

## Types

Allowed types: feat, fix, refactor, perf, docs, test, build, ci, chore.

| Type | Meaning |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `refactor` | Restructuring without intended behavior change |
| `perf` | Performance improvement |
| `docs` | Documentation only |
| `test` | Tests only |
| `build` | Build system or dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance that fits no other type |

The same list is configured as `pull_requests.allowed_types` in
[`.project/workflow.yml`](../../.project/workflow.yml) and stated in
[AGENTS.md](../../AGENTS.md). Change all three together.

Examples:

```text
feat(api): add image analysis endpoint
fix(parser): handle empty input correctly
refactor(core): simplify processing pipeline
test(core): add edge case coverage
docs(readme): update installation guide
ci(actions): add Windows build matrix
```

## Issue References

```text
feat(scanner): implement automatic cropping

Refs: #42
```

- `Refs: #42` links the issue. It is a project convention and does **not** close the issue.
- `Closes #42` or `Fixes #42` in a pull request description closes the issue when the pull
  request is merged into the **default branch** (`main`). Pull requests into `develop` do not close
  issues automatically; close the issue manually after the merge or when the release reaches
  `main`.
- A pull request without an issue states the reason instead of the reference.

## Breaking Changes

Mark an incompatible change with `!` after the type or scope, and describe it in a
`BREAKING CHANGE:` footer:

```text
feat(api)!: replace legacy response format

BREAKING CHANGE: Clients must use the new response schema.
Refs: #108
```

A breaking change also gets the `impact:breaking` label on its pull request, because release notes
are generated from pull request labels.

## Pull Request Titles

Pull requests into `develop` are squash-merged, and the pull request title becomes the commit
message on `develop`. The title therefore follows the same syntax, for example
`feat(api): add image analysis endpoint`. The individual commits on a feature branch should still
be small and conventional, but the title is what reaches the history.

The merge strategy is a provisional default; see
[Branching and Releases](branching-and-releases.md#merge-strategy).
