# Traceability

Maps every acceptance criterion of §17, every automated test case of §21.6 and the template-only
regressions to the features that deliver them. The first feature listed is the one whose acceptance
criteria prove the item; the others contribute. A phase exit gate in the [roadmap](roadmap.md) is
met only when all rows of its features are proven.

Coverage of §3 to §16 is checked mechanically: every heading of these sections is referenced by at
least one feature's `spec_refs` or background.

## §17.1 Repository and Structure

| Criterion | Features |
|---|---|
| A new repository can be created from the template. | FEAT-030, FEAT-001, FEAT-026 |
| No programming language or framework is mandatory. | FEAT-001, FEAT-031 |
| The common repository structure is documented and extensible. | FEAT-003, FEAT-001 |
| Default project metadata is initialized and schema-validated. | FEAT-014, FEAT-013, FEAT-028 |
| `main` and `develop` branches are correctly configured. | FEAT-026 |
| Template placeholders are replaced before production use. | FEAT-015, FEAT-028 |
| A consistent README and project entry point are available. | FEAT-002 |
| The selected project license is explicit and appropriate. | FEAT-028, FEAT-002 |

## §17.2 Issues and Project Management

| Criterion | Features |
|---|---|
| Bug, Task, Feature and Epic issue forms are available. | FEAT-007 |
| Improvement and Documentation forms are available. | FEAT-007 |
| Required issue fields are validated. | FEAT-018 |
| Standard labels can be created and synchronized automatically. | FEAT-025, FEAT-008, FEAT-023 |
| Exactly one type label and one status label are enforced by validation. | FEAT-018 |
| Priority and other required metadata are validated according to policy. | FEAT-018, FEAT-009 |
| Conflicting labels are detected and reported. | FEAT-018 |
| Parent-child relationships and blockers can be recorded. | FEAT-009, FEAT-048 |
| Issues can be linked to pull requests and releases. | FEAT-019, FEAT-011, FEAT-039 |
| Confidential security vulnerabilities have a private reporting channel. | FEAT-002 |

## §17.3 Agents and Documentation

| Criterion | Features |
|---|---|
| `AGENTS.md` contains repository-wide development rules. | FEAT-004 |
| Claude Code and Copilot can access relevant shared instructions. | FEAT-005 |
| Agent-specific files do not duplicate core rules unnecessarily. | FEAT-005 |
| Agents can identify the relevant issue and acceptance criteria. | FEAT-004, FEAT-007, FEAT-049 |
| Project documentation can be found via a short index. | FEAT-003, FEAT-015 |
| Relevant documentation is updated for behavior changes. | FEAT-006, FEAT-011 |
| Significant architectural changes use ADRs. | FEAT-003 |
| Agent write, merge, release and destructive operations are permission-controlled. | FEAT-006, FEAT-027, FEAT-050 |
| Agents report actual tests, changes, remaining risks and references. | FEAT-004, FEAT-006 |

## §17.4 CI/CD and Releases

| Criterion | Features |
|---|---|
| Repository validation runs automatically. | FEAT-016, FEAT-015 |
| Pull-request metadata is checked. | FEAT-019 |
| Conventional Commit/PR-title rules are checked. | FEAT-019 |
| GitHub Actions/YAML validation is available. | FEAT-016 |
| Secret scanning or an appropriate equivalent is configured. | FEAT-017, FEAT-043 |
| Technology-specific lint, tests and build are configured during bootstrap. | FEAT-031, FEAT-032 to FEAT-036, FEAT-028 |
| Required checks cannot silently succeed without executing required work. | FEAT-020 |
| Releases are produced from approved `main` commits. | FEAT-041, FEAT-027 |
| Release tags follow the project versioning convention. | FEAT-040, FEAT-012 |
| Release Notes and Changelog are generated or maintained consistently. | FEAT-039, FEAT-040 |
| Required quality gates and release approvals are observed. | FEAT-041, FEAT-020 |

## §17.5 Security and Maintenance

| Criterion | Features |
|---|---|
| No credentials, tokens or private keys are committed. | FEAT-017 |
| GitHub Actions permissions follow least privilege. | FEAT-017 |
| External Actions are pinned or managed by an approved lock strategy. | FEAT-017, FEAT-021 |
| Dependency updates and relevant security checks are configured. | FEAT-021, FEAT-043 |
| Self-hosted runners follow a documented trust model. | FEAT-045 |
| Repository settings can be audited for drift. | FEAT-029, FEAT-051 |
| Bootstrap scripts are idempotent. | FEAT-030, FEAT-024, FEAT-025 |
| A dry-run mode shows proposed changes before execution. | FEAT-024, FEAT-023 |
| Missing privileges and unavailable plan features are reported explicitly. | FEAT-027, FEAT-029 |
| Template changes can be rolled out via controlled upgrades. | FEAT-046 |

## §17.6 Bootstrap documentation and acceptance tests

| Criterion | Features |
|---|---|
| Bootstrap can configure an empty test repository. | FEAT-030 |
| Bootstrap can rerun without generating duplicates. | FEAT-030, FEAT-025 |
| Bootstrap preserves manual changes unless explicitly authorized otherwise. | FEAT-030, FEAT-024 |
| Bootstrap supports a private and a public repository test case. | FEAT-030 |
| The initial CI pipeline passes on a valid example repository. | FEAT-030, FEAT-016 |
| CI fails with a clear error on invalid metadata or missing required scripts. | FEAT-020, FEAT-014 |
| At least one language-specific extension has been tested end to end. | FEAT-032 |
| A user can create and configure a new project from written instructions. | FEAT-002, FEAT-028 |

## §21.6 Automated test cases

| Test case | Expected | Features |
|---|---|---|
| Issue without `type:*` | Validation failure / hint | FEAT-018 |
| Issue with two `priority:*` | Validation failure | FEAT-018 |
| Bug without reproduction steps | Validation failure / `status:needs-info` | FEAT-018 |
| `agent:ready` with open blockers | Validation failure | FEAT-018, FEAT-049 |
| Feature-branch PR against `main` | PR warning / policy error | FEAT-019 |
| Release PR from `develop` to `main` | Allowed when gates pass | FEAT-019, FEAT-020 |
| PR with invalid commit/title pattern | Validation failure | FEAT-019 |
| Run bootstrap twice | No duplicates | FEAT-030 |
| Missing `develop` branch | Correction proposal / bootstrap | FEAT-026, FEAT-029 |
| Private branch protection unavailable | Explicit warning, no success message | FEAT-027 |
| Required build not executed | CI failure, not pass | FEAT-020 |
| External PR with secret access | Access denied | FEAT-017 |
| Documentation change with stale index | Warning/error per policy | FEAT-015 (`REPO-DOCS-INDEX`) |

## Template-only regressions

These cases protect derived repositories from inheriting this workspace (see
[README](README.md#why-a-separate-folder)).

| Case | Expected | Features |
|---|---|---|
| Template repository (`is_template: true`) contains `template-dev/` | Validation passes | FEAT-015 |
| Derived repository still contains `template-dev/` | `REPO-TEMPLATE-ONLY` failure | FEAT-015, FEAT-030 |
| File outside `template-dev/` links into it | `REPO-DEAD-LINK-TEMPLATE` failure | FEAT-015 |
| `init` on a fresh derived repository | `template-dev/` removed, `is_template: false`, removal in JSON report | FEAT-028, FEAT-030 |
| `init` run twice | Second run succeeds, nothing left to remove | FEAT-028, FEAT-030 |
| `init --dry-run` | Lists the removal, changes nothing | FEAT-028 |
| `.project/bootstrap.yml` declares template-only paths | `template_only_paths` contains `template-dev/` | FEAT-013 |
| `docs/planning/` and `docs/features/` in the template | Contain only `README.md` and `_template.md` | FEAT-003 |
