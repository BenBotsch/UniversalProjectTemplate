# Contributing to PROJECT_NAME

These rules apply to humans and coding agents alike. Agents additionally follow
[AGENTS.md](AGENTS.md).

## Prerequisites and Local Setup

- Git and a GitHub account with access to [OWNER/REPOSITORY](https://github.com/OWNER/REPOSITORY).
- Python 3.10 or later for the repository checks in `scripts/ci/`.
- The tools required by the technology profile, listed in [README.md](README.md#requirements).

```text
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
git switch develop
python -m pip install -r scripts/ci/requirements.txt
```

## Issues First

Every change starts from a GitHub issue with clear acceptance criteria. Use the issue forms; they
set the required labels. Label rules are described in
[docs/governance/issue-management.md](docs/governance/issue-management.md).

## Branches

- `main` holds released code; `develop` is the integration branch.
- Create branches from `develop` as `<purpose>/<issue-number>-<short-summary>`, for example
  `feature/42-document-cropping` or `fix/77-empty-input`.
- Urgent production fixes use `hotfix/<issue-number>-<summary>` from `main` and are merged back
  into `develop` afterwards.
- Never push directly to `main` or `develop`.

The branch model is configured in [.project/workflow.yml](.project/workflow.yml).

## Commits

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<scope>): <description>

[optional body]

Refs: #<issue-number>
```

Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`. Mark
incompatible changes with `!` after the type or with a `BREAKING CHANGE:` footer.

## Tests and Checks

Run all applicable checks before you open a pull request, and report the actual results.

The commands for every CI check, and how to install the tools, are listed in
[scripts/ci/README.md](scripts/ci/README.md). Format, lint, type check, build and test commands
for the code itself are defined by the technology profile; add them to this section when a profile is
set up.

Never disable, skip or weaken a check to make a pull request pass.

## Pull Requests

- Target `develop`; only release and hotfix pull requests target `main`.
- Use a Conventional Commit title and fill in every section of the pull request template.
- Link the issue with `Refs: #<number>`, or write `No-Issue: <reason>` if there is none.
- Keep pull requests small and focused on one issue.
- Changes to `.github/workflows/`, `.project/` or `SECURITY.md` need particularly careful review.
- Where the team size allows, a reviewer other than the author approves before merge. Resolve all
  review conversations.

## Documentation and Decisions

- Update documentation that is affected by your change in the same pull request.
- Record significant architecture decisions as ADRs in `docs/architecture/adr/`.
- Link to existing documents instead of copying their content.

## Security Issues

Never report a vulnerability in a public issue, pull request or discussion. Follow
[SECURITY.md](SECURITY.md).

## Definition of Done

A change is done when:

- The acceptance criteria of the issue are met.
- Applicable tests and quality checks were run and pass.
- Affected documentation is updated.
- No unresolved critical security issue is introduced.
- The change was reviewed and merged through a pull request.
