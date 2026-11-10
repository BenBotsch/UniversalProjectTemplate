---
id: "FEAT-054"
title: "Allow Controlled Execution of Declared Scripts"
epic: "EPIC-11"
phase: 5
status: "planned"
priority: "low"
effort: "xl"
target_repo: "dashboard"
spec_refs: ["§7.6", "§11.1", "§11.3", "§15.3"]
dependencies: ["FEAT-053"]
blocked_by_decisions: ["DEC-10"]
agent_ready: false
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-054: Allow Controlled Execution of Declared Scripts

## Objective

The dashboard can trigger maintenance, build and test commands that a repository explicitly declares,
with approval levels, isolation, limits and a full audit log.

## Background

§15.3 requires controls for executable scripts: defined working directory, allowed arguments, runtime,
secrets, timeouts, resource limits, logging, approval levels, isolated execution; files like `.cmd`
or `.py` must not become executable just because they exist. §11.3 runner isolation. Blocked by
`DEC-10`.

## Scope

- Declaration format in `.project/workflow.yml` (`scripts:`), execution via `workflow_dispatch` on
  GitHub-hosted or isolated ephemeral runners, approval through environments.

### Out of Scope

- Local execution on a developer machine from the dashboard.

## Deliverables

| Path | Description |
|---|---|
| `.project/workflow.yml` (section) + schema | `scripts: [{id, command, args_schema, working_dir, timeout_minutes, approval: none\|environment, secrets: []}]` |
| `.github/workflows/run-declared-script.yml` | `workflow_dispatch` with `script_id` and JSON args validated against `args_schema` |
| `dashboard/app/**` (feature) | Trigger button only for declared scripts, shows run status and log link |
| `docs/governance/script-execution.md` | Controls from §15.3 and how each is enforced |

## Requirements

1. **R1:** Only declared `script_id`s run; arguments validated against the schema, passed as an array, never concatenated into a shell string.
2. **R2:** `approval: environment` scripts wait for environment approval.
3. **R3:** Timeouts and runner choice enforced in the workflow, not in the UI.
4. **R4:** Each run records who triggered it, inputs, approver, result, per `DEC-10`.
5. **R5:** Secrets are limited to those listed for the script.

## Tasks

- [ ] **T1:** Declaration schema and validation.
- [ ] **T2:** Dispatch workflow with argument validation.
- [ ] **T3:** Dashboard trigger and status.
- [ ] **T4:** Governance document.

## Acceptance Criteria

- [ ] An undeclared script id is rejected before any runner starts.
- [ ] An argument containing shell metacharacters is passed literally and cannot inject commands.
- [ ] A script with `approval: environment` does not run before approval.

## Verification

```text
python -I scripts/ci/validate_project.py
actionlint .github/workflows/run-declared-script.yml
```

## Agent Notes

- **Allowed paths:** files listed above, this feature file, backlog status.
- **Requires approval:** resolving `DEC-10`; configuring environments and secrets.
- **Pitfalls:** This is the highest-risk feature; review with the security policy and run zizmor.
