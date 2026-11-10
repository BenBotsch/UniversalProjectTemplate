# Issue Management

Every change starts from a GitHub issue. This document is the human-readable counterpart of
`issue_policy` in [`.project/workflow.yml`](../../.project/workflow.yml): both describe the same
rules, and the issue validator reports violations with the rule IDs used here.

## Issue Types

| Type | Label | Purpose | Mandatory content |
|---|---|---|---|
| Epic | `type:epic` | Larger initiative spanning several issues | Goal and motivation, scope, non-goals, sub-issues, risks, success criteria |
| Feature | `type:feature` | New functionality | User story, functional requirements, acceptance criteria, dependencies |
| Task | `type:task` | Concrete piece of work | Objective, scope, implementation notes, acceptance criteria |
| Bug | `type:bug` | Malfunction | Reproduction, expected and actual behavior, environment, severity, evidence |
| Improvement | `type:improvement` | Improve something that exists | Current situation, proposed improvement, benefit, how success is measured |
| Documentation | `type:documentation` | Documentation work | Affected pages, required change, how the change is validated |
| Security work | `type:task` + `area:security` | Planned, non-confidential hardening | Risk, scope, verification criteria; see [Security Work](#security-work) |

The mandatory content maps to the required fields of the issue forms; see
[Form Fields and Issue Body Headings](#form-fields-and-issue-body-headings).

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
   pull requests. To rename a label, set the new name in `.project/labels.yml` and list the old
   name under `aliases`; label synchronization then renames the existing label, and GitHub keeps
   it on every issue and pull request. Label synchronization deletes labels that are not in
   `.project/labels.yml` only on explicit request and after confirmation.

### Labels on pull requests

Release notes are generated from the labels of **pull requests**, not of the linked issues. The two
can diverge. The author of a pull request sets the release-relevant labels on the pull request
itself: the `type:*` label of the change, `impact:breaking` or `impact:security` where applicable,
and `skip-changelog` for changes without user-visible effect.

## Metadata Invariants

These rules apply to every issue. Rules marked "review" cannot be checked mechanically and are
verified during triage and review. A planned issue is an issue in `status:ready`,
`status:in-progress`, `status:blocked` or `status:review`.

| ID | Rule | Check |
|---|---|---|
| ISSUE-R1 | Every issue has exactly one `type:*` label. | automated |
| ISSUE-R2 | Every open issue has exactly one `status:*` label. | automated |
| ISSUE-R3 | An issue has at most one `priority:*` label. A planned issue has exactly one. | automated |
| ISSUE-R4 | An issue has at most one `effort:*` label. | automated |
| ISSUE-R5 | A planned issue has at least one `area:*` label, if a matching area is defined. | automated |
| ISSUE-R6 | `impact:*` and `agent:*` labels are set only when they apply. | review |
| ISSUE-R7 | `agent:ready` and `agent:working` are not set at the same time. | automated |
| ISSUE-R8 | `agent:ready` is set only if the issue has acceptance criteria and a scope, has no unresolved blockers and needs no permissions beyond those approved for agents. | automated where data exists, otherwise review |
| ISSUE-R9 | An issue in `status:blocked` names its blocker, preferably as a "blocked by" dependency, otherwise in a comment. | automated |
| ISSUE-R10 | An issue in `status:review` references a pull request or another reviewable artifact. | automated |
| ISSUE-R11 | The issue body contains the mandatory content of its type, using the headings of its issue form. | automated |

`required_single_label_groups`, `required_for_ready` and `optional_single_label_groups` in
`workflow.yml` encode ISSUE-R1 to ISSUE-R5; `agent_ready_requires` encodes ISSUE-R8.

### Initial labels

New issues start with `status:triage` and without a `priority:*` label; the priority is required
from `status:ready` on (ISSUE-R3). This is a **provisional default**. It may change once the
template has been used in real projects; a change is made in `workflow.yml` and in this section
together.

## Status Lifecycle

```text
triage -> needs-info -> triage
   |
   v
 ready -> in-progress -> review -> closed
              |           |
              +-> blocked +-> in-progress
                    |
                    +-> ready
```

Allowed transitions:

| From | To | When |
|---|---|---|
| `triage` | `needs-info` | Information is missing to assess the issue |
| `needs-info` | `triage` | The author has added the missing information |
| `triage` | `ready` | Type, priority and area are set and the issue meets the rules for its type |
| `ready` | `in-progress` | Someone starts working on the issue |
| `in-progress` | `blocked` | Work cannot continue because of a named blocker (ISSUE-R9) |
| `blocked` | `ready` | The blocker is resolved; the issue waits to be picked up again |
| `in-progress` | `review` | A pull request or reviewable artifact exists (ISSUE-R10) |
| `review` | `in-progress` | The review requests changes |
| `review` | closed | The pull request is merged and the acceptance criteria are met |
| any open state | closed | The issue is closed as "not planned", for example as a duplicate |
| closed | `triage` | A closed issue is reopened |

Any other transition goes through the intermediate states.

`closed` is the **native GitHub issue state**. There is no `status:done` label. When an issue is
closed, its `status:*` label is no longer evaluated; ISSUE-R2 applies only to open issues.

## Severity vs. Priority

Severity and priority are different properties:

- **Severity** describes the impact of a bug, for example data loss or a cosmetic flaw. The Bug
  form records it in the Severity dropdown as text.
- **Priority** describes the order of work and is a `priority:*` label.

A dropdown value is not converted into a label. Tools may *suggest* a priority from the severity,
but the final priority is a triage decision. A critical bug in a rarely used, deprecated function
can have a low priority; a medium bug that blocks a release can have a high one.

## Hierarchy and Dependencies

```text
Epic #10: Document Processing
  +-- Feature #11: Automatic Cropping
        +-- Task #12: Implement Detection Algorithm
              +-- Blocked by Task #13: Prepare Test Images
```

- **Parent and child:** use GitHub's native sub-issues. On the parent issue, create a sub-issue
  or add an existing issue as sub-issue. An epic lists planned work in "Milestones and
  Sub-Issues" until the sub-issues exist.
- **Blockers:** use GitHub's native issue dependencies ("blocked by" and "blocking") where they
  are available. Otherwise write `Blocked by #<number>` in the issue body or a comment.
- **Context:** the issue body holds context and verifiable requirements; it does not repeat the
  hierarchy.
- **No second hierarchy:** do not maintain a manual issue tree in Markdown files. The GitHub
  relationships are the only source; documents link to issues instead of copying them.
- **Traceability:** closed issues and their linked pull requests are the record of what was done.

## Security Work

- **Vulnerabilities** are never reported in a public issue. They are reported privately as
  described in [SECURITY.md](../../SECURITY.md).
- **Planned, non-confidential hardening**, for example enabling secret scanning, uses the Task
  form with the `type:task` and `area:security` labels.
- An issue that turns out to describe an unpatched vulnerability is moved to the private channel
  and its public details are removed.

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

## Triage Procedure

Triage reviews every issue in `status:triage`:

1. Check that the issue belongs in the public tracker. Move vulnerabilities to the private
   channel (see [Security Work](#security-work)).
2. Check the type (ISSUE-R1) and the mandatory content (ISSUE-R11). If information is missing,
   comment with what is needed and set `status:needs-info`.
3. Close duplicates and out-of-scope requests as "not planned", with a link or a reason.
4. Set exactly one `priority:*` label (ISSUE-R3), at least one `area:*` label (ISSUE-R5) and,
   if used, one `effort:*` label (ISSUE-R4). For bugs, take the severity into account without
   copying it.
5. Attach the issue to its parent as a sub-issue and record blockers as dependencies.
6. Set `agent:ready` only if ISSUE-R8 is met.
7. Replace `status:triage` with `status:ready`.
