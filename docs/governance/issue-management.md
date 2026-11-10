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
