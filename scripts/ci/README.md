# CI Scripts and Local Checks

This directory contains the validators that the CI workflows run. `ci.yml` calls `quality.yml`,
`security.yml` and `pr-validation.yml` as reusable workflows, and its `quality-gate` job evaluates
all results; it is the only required status check. Every CI check can be run locally with the
commands below, from the repository root.

## Setup

The validators and the lint tools need Python 3.12 or later. `markdownlint-cli2` needs Node.js;
`lychee` and `gitleaks` are standalone binaries from their releases
([lychee](https://github.com/lycheeverse/lychee/releases),
[gitleaks](https://github.com/gitleaks/gitleaks/releases)).

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
| `ci.yml` | `bootstrap-tool` | `python -I -m pytest`, `ruff check .` and `ruff format --check .` in `tools/engineering-bootstrap/`; template repository only |
| `quality.yml` | `workflow-lint` | `actionlint` |
| | | `zizmor .github/workflows/` |
| `quality.yml` | `yaml-lint` | `yamllint --strict .` |
| `quality.yml` | `markdown-lint` | `npx markdownlint-cli2@0.24.0 "**/*.md"` |
| `quality.yml` | `link-check` | `lychee --offline --include-fragments --no-progress './**/*.md'` |
| `security.yml` | `secret-scan` | `gitleaks git --config .gitleaks.toml --redact .` |
| `security.yml` | `actions-pinning` | `python -I scripts/ci/check_action_pinning.py` |
| `pr-validation.yml` | `pr-validation` | See [Pull Request Checks](#pull-request-checks) |
| `pr-validation.yml` | `commitlint` | `python -I scripts/ci/pr_validation/validator.py commits --range develop..HEAD` |
| `ci.yml` | `quality-gate` | See [Quality Gate Evaluation](#quality-gate-evaluation) |
| `issue-validation.yml` | `issue-validation` | See [Issue Validation](#issue-validation); not a pull request check |

Additional checks for single files:

| Check | Command |
|---|---|
| Label configuration | `python -I scripts/ci/check_labels.py .project/labels.yml` |
| Issue forms | `python -I scripts/ci/check_issue_forms.py` |
| Findings as JSON | `python -I scripts/ci/validate_repository.py --format json` |

`validate_repository.py` also runs the label and issue-form checks. `actionlint` runs
`shellcheck` on `run:` scripts when `shellcheck` is installed; the GitHub-hosted runner has it.
Locally, `zizmor` runs only its offline audits unless `GH_TOKEN` is set.

## Pull Request Checks

[pr_validation/validator.py](pr_validation/validator.py) applies the rules of
`.project/workflow.yml` to a pull request:

| Rule | Check |
|---|---|
| `title` | The title is a Conventional Commits header with a type from `pull_requests.allowed_types` |
| `target-branch` | The target branch is one of the `targets` of the branch type; `develop` → `main` (release) and `main` → `develop` (synchronization) are always allowed |
| `branch-name` | The branch matches `branching.branch_name_pattern`; a branch without an issue number needs a `No-Issue:` reason |
| `issue-link` | The description contains `Refs: #<number>`, `Closes #<number>`, `Fixes #<number>`, `Resolves #<number>` or `No-Issue: <reason>`; HTML comments are ignored |
| `template-section` | Each heading in `pull_requests.required_sections` exists and is neither empty nor unchanged template text |
| `commit-message` | Each non-merge commit of the pull request follows Conventional Commits 1.0.0 |

Changes below `pull_requests.elevated_review_paths` add an "Elevated review required" notice to
the job; they do not fail it. Pull requests of `pull_requests.automation_authors`, such as
Dependabot, skip the branch name, issue link and section rules. Their title, target branch and
commits are still checked.

In CI the validator reads the pull request from the event file. Locally, pass the values
directly:

```text
python -I scripts/ci/pr_validation/validator.py pull-request --title "feat(api): add endpoint" --body-file body.md --head-ref feature/42-add-endpoint --base-ref develop --range develop..HEAD
python -I scripts/ci/pr_validation/validator.py commits --range develop..HEAD
```

The exit code is `0` if every rule passed, `1` if a rule failed and `2` for invalid input.

## Issue Validation

`.github/workflows/issue-validation.yml` runs [issue_validation/run.py](issue_validation/run.py)
for every `issues` event (`opened`, `edited`, `labeled`, `unlabeled`, `reopened`). It is not part
of `ci.yml` and has no quality gate. The rules are in
[issue_validation/validator.py](issue_validation/validator.py) and are described with their IDs in
[Issue Management](../../docs/governance/issue-management.md#automated-validation). They are
read from `issue_policy` in `.project/workflow.yml`, from the groups in `.project/labels.yml` and
from the required fields of the issue forms.

The runner reads the current issue, its comments and, for `agent:ready` or `status:blocked`, its
"blocked by" dependencies through the REST API. It then:

- Writes one comment, marked `<!-- issue-validation -->`, with every finding. It updates that
  comment on later events and marks it as resolved when every rule passes. Only a comment written
  by the workflow's own account counts.
- Replaces `status:triage`, or a missing status, with `status:needs-info` when a rule fails, and
  restores `status:triage` when every rule passes. The comment records that the validator set the
  label; it never removes a `status:needs-info` label that a person set.
- Gives an open issue without any status label but with no other finding `status:triage`.
- Skips pull requests, closed issues and events sent by its own account. Label changes made with
  the job token do not start new runs, so the validator cannot loop.

The job needs `issues: write`. It fails only when the GitHub API or the input fails, so a failed
read is never reported as a valid issue; rule findings are reported in the comment and the job
summary. To check an issue locally without changing it, use either command:

```text
gh api repos/OWNER/REPOSITORY/issues/NUMBER > issue.json
python -I scripts/ci/issue_validation/validator.py issue.json
python -I scripts/ci/issue_validation/run.py --event event.json --dry-run
```

`validator.py` checks every rule except the blockers. `run.py --dry-run` reads the issue through
the API with the token in `GITHUB_TOKEN` and prints the planned comment and label changes; the
event file needs `issue.number`, `repository.full_name` and `sender.login`. The exit code of
`validator.py` is `0` without findings, `1` with findings and `2` for invalid input. `run.py`
returns `0` after a run, also with findings, `1` for an API error and `2` for invalid input.

## Quality Gate Evaluation

[evaluate_quality_gates.py](evaluate_quality_gates.py) compares the job results of a CI run with
[.project/quality-gates.yml](../../.project/quality-gates.yml). The rules are described in the
[Quality Model](../../docs/governance/quality-model.md#enforcement-in-ci). In CI it reads the
changed files from the event file. Locally, download the job list of a run and pass the event
name and the revision range:

```text
gh api --paginate "repos/OWNER/REPOSITORY/actions/runs/RUN_ID/jobs?per_page=100" > jobs.json
python -I scripts/ci/evaluate_quality_gates.py --jobs jobs.json --event-name pull_request --range develop..HEAD
```

Without `--event` or `--range`, the changed files are unknown and every path-dependent gate
applies. The exit code is `0` if every applicable gate passed, `1` if a gate failed and `2` for
invalid input.

## Configuration

| File | Used by |
|---|---|
| [.project/workflow.yml](../../.project/workflow.yml) `repository_validation` | `validate_repository.py` |
| [.project/workflow.yml](../../.project/workflow.yml) `branching`, `pull_requests` | `pr_validation/validator.py` |
| [.project/workflow.yml](../../.project/workflow.yml) `issue_policy`, [.project/labels.yml](../../.project/labels.yml), [.github/ISSUE_TEMPLATE/](../../.github/ISSUE_TEMPLATE/) | `issue_validation/validator.py` |
| [.project/quality-gates.yml](../../.project/quality-gates.yml), [.project/project.yml](../../.project/project.yml) `technology.languages` | `evaluate_quality_gates.py` |
| [.yamllint.yml](../../.yamllint.yml) | `yamllint` |
| [.markdownlint.yaml](../../.markdownlint.yaml), [.markdownlint-cli2.yaml](../../.markdownlint-cli2.yaml) | `markdownlint-cli2` |
| [.gitleaks.toml](../../.gitleaks.toml) | `gitleaks` |

## Workflow Rules

The full checklist is in the
[Security Policy for Development and CI](../../docs/governance/security-policy.md#workflow-review-checklist).
In short:

- Workflows use `permissions: contents: read`; a job requests more only with a documented reason.
- Actions are pinned to a full commit SHA with the version as a comment, for example
  `uses: actions/checkout@<sha> # v7.0.1`. Look the SHA up from the action's release tag.
- No job uses `continue-on-error`. A required check must not pass because it was skipped.
- A new gate job is added to `ci.yml` or a workflow it calls, and to `quality-gates.yml`.
- `run:` scripts do not interpolate untrusted event data such as titles, bodies or branch names.
- Job ids match the `job` fields in [.project/quality-gates.yml](../../.project/quality-gates.yml).
