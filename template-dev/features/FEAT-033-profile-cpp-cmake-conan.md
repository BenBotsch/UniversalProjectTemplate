---
id: "FEAT-033"
title: "Add C++ Profile with CMake and Conan"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "medium"
effort: "l"
target_repo: "universal-project-template"
spec_refs: ["§3.3", "§10.1", "§10.2", "§10.3"]
dependencies: ["FEAT-031"]
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-033: Add C++ Profile with CMake and Conan

## Objective

The `cpp-cmake` profile adds a CMake project with presets, optional Conan dependency management,
clang-format and clang-tidy checks and CTest jobs on Linux and Windows.

## Background

§3.3 names C++/CMake/Conan; §10.3 tools (CMake, CTest, clang-format, clang-tidy,
AddressSanitizer/UBSan).

## Scope

- CMake skeleton with `CMakePresets.json`, one library, one test; Conan 2 `conanfile.py` as option.

### Out of Scope

- Packaging and installers; embedded toolchains.

## Deliverables

| Path | Description |
|---|---|
| `profiles/cpp-cmake/profile.yml` | Manifest |
| `profiles/cpp-cmake/files/CMakeLists.txt`, `CMakePresets.json` | Presets `debug`, `release`, `ci`, `asan` |
| `profiles/cpp-cmake/files/conanfile.py` | Optional, enabled by profile option `conan: true` |
| `profiles/cpp-cmake/files/.clang-format`, `.clang-tidy` | Baseline configs |
| `profiles/cpp-cmake/files/.github/workflows/cpp.yml` | Jobs `cpp-format`, `cpp-build`, `cpp-test` (matrix ubuntu/windows), `cpp-sanitizers` (ASan/UBSan on Linux, preset `asan`), `cpp-tidy` |
| `profiles/cpp-cmake/README.md` | Commands, gate mapping |

## Requirements

1. **R1:** Jobs map to gates `format`, `build`, `unit_tests`, `static_analysis`; sanitizer runs count towards `unit_tests`.
2. **R2:** Build uses presets only, no ad-hoc flags in the workflow.
3. **R3:** Conan cache keyed on lockfile; no secrets needed.

## Tasks

- [ ] **T1:** CMake skeleton and presets.
- [ ] **T2:** Conan option.
- [ ] **T3:** Workflow and gate mapping.

## Acceptance Criteria

- [ ] Profile applies cleanly; build and test pass on Linux and Windows runners.

## Verification

```text
cmake --preset ci && cmake --build --preset ci && ctest --preset ci
```

## Agent Notes

- **Allowed paths:** `profiles/cpp-cmake/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** clang-tidy is slow; run on changed files in PRs, full on schedule.
