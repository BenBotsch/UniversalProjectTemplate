# Issue Management

## Label Taxonomy

[`.project/labels.yml`](../../.project/labels.yml) is the single declarative source for labels.
Labels are created and updated on GitHub from this file; do not add or edit labels manually in the
GitHub UI. Check the file after every change:

```text
python -I scripts/ci/check_labels.py .project/labels.yml
```

### Groups

| Group | Labels | Meaning | Color logic |
|---|---|---|---|
| `type` | `type:bug`, `type:task`, `type:feature`, `type:epic`, `type:improvement`, `type:documentation` | Kind of work | Distinct color per type |
| `priority` | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` | Implementation priority | Red (urgent) to green (low) |
| `status` | `status:triage`, `status:ready`, `status:in-progress`, `status:blocked`, `status:review`, `status:needs-info` | Processing state | Signal colors: gray waiting, green ready, blue active, red blocked, violet review, pale yellow needs input |
| `area` | `area:backend`, `area:frontend`, `area:api`, `area:ci-cd`, `area:docs`, `area:security` | Affected part of the project | One shared light blue (`c5def5`) |
| `effort` | `effort:xs`, `effort:s`, `effort:m`, `effort:l`, `effort:xl` | Rough size | Light to dark violet as size grows |
| `impact` | `impact:breaking`, `impact:performance`, `impact:security` | Cross-cutting consequences | Orange family, strongest for `breaking` |
| `agent` | `agent:ready`, `agent:working`, `agent:review-required` | Agent suitability and approval state | Teal family, darker as human attention is needed |
| `meta` | `skip-changelog` | Process control | Neutral gray |

The colors of `type`, `priority` and `status` are fixed by the project specification. There is no
`status:done` label: a closed issue uses the native GitHub issue state.

### Naming rules

- Names are lowercase `group:value`; the value is kebab-case, for example `status:in-progress`.
- The prefix of the name equals the `group` field of the entry.
- Labels in group `meta` have no prefix. `skip-changelog` is currently the only one; it excludes a
  pull request from generated release notes.
- Colors are 6-digit hex without `#`. Descriptions have at most 100 characters (GitHub limit).

### Adding labels

Projects may add labels for their own needs, for example `area:desktop`, `area:ml`,
`platform:windows` or `platform:linux`.

1. Reuse an existing group if the meaning fits; add a new group only for a new dimension, such as
   `platform`.
2. Follow the color logic of the group. All labels of a new group share one hue.
3. Add the entry to `.project/labels.yml`, run the check, and synchronize the labels.
4. Do not rename or delete a label that is in use without a migration of the affected issues and
   pull requests.

### Labels on pull requests

Release notes are generated from the labels of **pull requests**, not of the linked issues. The two
can diverge. The author of a pull request sets the release-relevant labels on the pull request
itself: the `type:*` label of the change, `impact:breaking` or `impact:security` where applicable,
and `skip-changelog` for changes without user-visible effect.

## Issue Forms

Issues are created through the YAML forms in
[`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/). Blank issues are disabled in the web
UI. Security vulnerabilities have no public form; they are reported privately as described in
[SECURITY.md](../../SECURITY.md). Planned, non-confidential security hardening uses the Task form
with the `area:security` label.

| Form | File | Initial labels |
|---|---|---|
| Bug Report | `bug.yml` | `type:bug`, `status:triage` |
| Task | `task.yml` | `type:task`, `status:triage` |
| Feature Request | `feature.yml` | `type:feature`, `status:triage` |
| Epic | `epic.yml` | `type:epic`, `status:triage` |
| Improvement | `improvement.yml` | `type:improvement`, `status:triage` |
| Documentation | `documentation.yml` | `type:documentation`, `status:triage`, `area:docs` |

Forms set no `priority:*` label; the priority is set during triage. The Severity dropdown of the
Bug form describes the impact, is stored as text and does not set a priority label.

Forms are not a hard barrier: issues created through the API or CLI bypass them and must be
checked separately. Labels set by a form exist only after the labels are synchronized from
`.project/labels.yml`. Check the forms after every change:

```text
python -I scripts/ci/check_issue_forms.py
```

### Form Fields and Issue Body Headings

GitHub writes each form field into the issue body as a `### <label>` heading followed by the
answer; empty optional fields contain `_No response_`. Tools that parse issue bodies rely on the
headings below. Field ids and labels are an interface: renaming one requires updating the parsers,
their tests and `scripts/ci/check_issue_forms.py`.

| Form | Field id | Issue body heading | Required |
|---|---|---|---|
| Bug | `summary` | `### Summary` | yes |
| Bug | `reproduction` | `### Steps to Reproduce` | yes |
| Bug | `expected` | `### Expected Behavior` | yes |
| Bug | `actual` | `### Actual Behavior` | yes |
| Bug | `environment` | `### Environment` | yes |
| Bug | `severity` | `### Severity` | yes |
| Bug | `evidence` | `### Logs and Evidence` | yes |
| Bug | `acceptance` | `### Acceptance Criteria` | yes |
| Task | `objective` | `### Objective` | yes |
| Task | `context` | `### Context and Motivation` | yes |
| Task | `scope` | `### Scope` | yes |
| Task | `implementation` | `### Implementation Notes` | yes |
| Task | `dependencies` | `### Dependencies and Blockers` | no |
| Task | `acceptance` | `### Acceptance Criteria` | yes |
| Feature | `problem` | `### Problem Statement` | yes |
| Feature | `user_story` | `### User Story` | yes |
| Feature | `requirements` | `### Functional Requirements` | yes |
| Feature | `acceptance` | `### Acceptance Criteria` | yes |
| Feature | `out_of_scope` | `### Out of Scope` | no |
| Feature | `dependencies` | `### Dependencies and Related Issues` | yes |
| Epic | `goal` | `### Goal and Business Value` | yes |
| Epic | `scope` | `### Scope and Deliverables` | yes |
| Epic | `non_goals` | `### Non-Goals` | yes |
| Epic | `milestones` | `### Milestones and Sub-Issues` | yes |
| Epic | `risks` | `### Risks and Dependencies` | yes |
| Epic | `success` | `### Success Criteria` | yes |
| Improvement | `current` | `### Current Situation` | yes |
| Improvement | `proposal` | `### Proposed Improvement` | yes |
| Improvement | `impact` | `### Expected Benefits and Impact` | yes |
| Improvement | `criteria` | `### Acceptance Criteria` | yes |
| Documentation | `affected` | `### Affected Documentation` | yes |
| Documentation | `change` | `### Required Change` | yes |
| Documentation | `acceptance` | `### Acceptance Criteria` | yes |
