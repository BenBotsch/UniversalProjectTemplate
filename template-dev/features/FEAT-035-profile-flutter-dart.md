---
id: "FEAT-035"
title: "Add Flutter and Dart Profile"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "low"
effort: "m"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.1", "§10.2", "§10.3"]
dependencies: ["FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-035: Add Flutter and Dart Profile

## Objective

The `flutter` profile adds analyzer, format and test jobs for a Flutter or plain Dart project.

## Background

§3.3 names Flutter/Dart; §10.3 tools (`dart format`, `flutter analyze`, `flutter test`).

## Scope

- `analysis_options.yaml`, workflow, profile option `flavor: flutter|dart`.

### Out of Scope

- Mobile signing, store deployment.

## Deliverables

| Path | Description |
|---|---|
| `profiles/flutter/profile.yml` | Manifest with `flavor` option |
| `profiles/flutter/files/analysis_options.yaml` | Lints baseline |
| `profiles/flutter/files/.github/workflows/flutter.yml` | Jobs `dart-format`, `flutter-analyze`, `flutter-test` |
| `profiles/flutter/README.md` | How to run `flutter create` into the repo, gate mapping |

## Requirements

1. **R1:** Jobs map to gates `format`, `lint`, `unit_tests`.
2. **R2:** Flutter SDK version pinned in one place and reused by CI.
3. **R3:** Dependabot ecosystem `pub` added via manifest.

## Tasks

- [ ] **T1:** Manifest, analyzer config, workflow.
- [ ] **T2:** README with project creation steps.

## Acceptance Criteria

- [ ] Profile applies cleanly and jobs pass on a `flutter create` skeleton.

## Verification

```text
dart format --set-exit-if-changed . && flutter analyze && flutter test
```

## Agent Notes

- **Allowed paths:** `profiles/flutter/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** The profile must not vendor generated platform folders; let `flutter create` produce them.
