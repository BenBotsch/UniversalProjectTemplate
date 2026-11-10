---
id: "FEAT-039"
title: "Configure Release Notes Categories and Changelog Process"
epic: "EPIC-09"
phase: 4
status: "planned"
priority: "high"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§9.3", "§9.4", "§9.5", "§17.4"]
dependencies: ["FEAT-008", "FEAT-012"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-039: Configure Release Notes Categories and Changelog Process

## Objective

GitHub-generated release notes are grouped by labels, and `CHANGELOG.md` follows Keep a Changelog
with a documented, manual-first update process.

## Background

§9.5 gives the `.github/release.yml` example and warns that it does not compute a SemVer number.
§9.4 release structure (tags `vX.Y.Z`, categories, Keep a Changelog). §9.3 SemVer including the
special meaning of `0.y.z`.

## Scope

- `.github/release.yml`; changelog maintenance rules; a check that `CHANGELOG.md` has an
  `Unreleased` section.

### Out of Scope

- Version computation and automated changelog generation (`FEAT-040`).

## Deliverables

| Path | Description |
|---|---|
| `.github/release.yml` | §9.5 categories; plus `Security` (`impact:security`) and `Performance` (`impact:performance`), both placed before "Other Changes" |
| `docs/governance/branching-and-releases.md` (section) | "Changelog": who updates `Unreleased`, when it is cut, `0.y.z` interpretation |
| `scripts/ci/check_changelog.py` | Fails if `CHANGELOG.md` lacks `## [Unreleased]` or has malformed version headings |
| `tests/ci/test_check_changelog.py` | Valid, missing section, bad heading |

## Requirements

1. **R1:** Every label used in `release.yml` exists in `labels.yml` (checked by `check_labels.py` from `FEAT-008`).
2. **R2:** `skip-changelog` excludes PRs from notes.
3. **R3:** Changelog check runs in `quality.yml` as job `changelog-check`.

## Tasks

- [ ] **T1:** `release.yml` and label consistency.
- [ ] **T2:** Changelog checker and job.
- [ ] **T3:** Documentation section.

## Acceptance Criteria

- [ ] Release notes can be categorized via labels (§17.4).
- [ ] `CHANGELOG.md` follows Keep a Changelog and is checked in CI.

## Verification

```text
python -I scripts/ci/check_changelog.py
python -I scripts/ci/check_labels.py
# GitHub: draft a release, "Generate release notes" shows the categories.
```

## Agent Notes

- **Allowed paths:** files listed above, `quality.yml` job, this feature file, backlog status.
- **Requires approval:** creating a draft release on GitHub.
- **Pitfalls:** Do not claim the notes determine the version number (§9.5).
