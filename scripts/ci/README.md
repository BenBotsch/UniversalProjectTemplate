# CI Scripts and Local Checks

This directory contains the validators that the CI workflows run. Every CI check can be run
locally with the commands below, from the repository root.

## Setup

The validators and the lint tools need Python 3.12 or later. `markdownlint-cli2` needs Node.js;
`lychee` is a standalone binary from its [releases](https://github.com/lycheeverse/lychee/releases).

```text
python -I -m pip install -r scripts/ci/requirements.txt
python -I -m pip install -r scripts/ci/requirements-lint.txt
```

Both requirement files pin exact versions. Use a virtual environment to keep them separate from
other projects.

## Checks

| Workflow | Job | Local command |
|---|---|---|
| `ci.yml` | `repository-validation` | `python -I -m pytest tests/ci` |
| | | `python -I scripts/ci/validate_project.py` |
| | | `python -I scripts/ci/validate_repository.py` |
| `quality.yml` | `workflow-lint` | `actionlint` |
| | | `zizmor .github/workflows/` |
| `quality.yml` | `yaml-lint` | `yamllint --strict .` |
| `quality.yml` | `markdown-lint` | `npx markdownlint-cli2@0.24.0 "**/*.md"` |
| `quality.yml` | `link-check` | `lychee --offline --include-fragments --no-progress './**/*.md'` |

Additional checks for single files:

| Check | Command |
|---|---|
| Label configuration | `python -I scripts/ci/check_labels.py .project/labels.yml` |
| Issue forms | `python -I scripts/ci/check_issue_forms.py` |
| Findings as JSON | `python -I scripts/ci/validate_repository.py --format json` |

`validate_repository.py` also runs the label and issue-form checks. `actionlint` runs
`shellcheck` on `run:` scripts when `shellcheck` is installed; the GitHub-hosted runner has it.
Locally, `zizmor` runs only its offline audits unless `GH_TOKEN` is set.

## Configuration

| File | Used by |
|---|---|
| [.project/workflow.yml](../../.project/workflow.yml) `repository_validation` | `validate_repository.py` |
| [.yamllint.yml](../../.yamllint.yml) | `yamllint` |
| [.markdownlint.yaml](../../.markdownlint.yaml), [.markdownlint-cli2.yaml](../../.markdownlint-cli2.yaml) | `markdownlint-cli2` |

## Workflow Rules

- Workflows use `permissions: contents: read`; a job requests more only with a documented reason.
- Actions are pinned to a full commit SHA with the version as a comment, for example
  `uses: actions/checkout@<sha> # v7.0.1`. Look the SHA up from the action's release tag.
- No job uses `continue-on-error`. A required check must not pass because it was skipped.
- `run:` scripts do not interpolate untrusted event data such as titles, bodies or branch names.
- Job ids match the `job` fields in [.project/quality-gates.yml](../../.project/quality-gates.yml).
