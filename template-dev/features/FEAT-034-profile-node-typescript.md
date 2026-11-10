---
id: "FEAT-034"
title: "Add Node.js and TypeScript Profile"
epic: "EPIC-08"
phase: 3
status: "planned"
priority: "medium"
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

# FEAT-034: Add Node.js and TypeScript Profile

## Objective

The `node-ts` profile adds a TypeScript package with lockfile-based installs, ESLint, Prettier,
type check and tests.

## Background

§3.3 names Node/TypeScript; §10.3 tools (ESLint, TypeScript, Vitest, `npm audit` or comparable).
Prettier is added for the `format` gate.

## Scope

- `package.json`, `tsconfig.json`, ESLint flat config, Prettier config, one source file and test.

### Out of Scope

- Frontend frameworks, bundling, publishing to npm.

## Deliverables

| Path | Description |
|---|---|
| `profiles/node-ts/profile.yml` | Manifest |
| `profiles/node-ts/files/package.json`, `tsconfig.json`, `eslint.config.js`, `.prettierrc` | Baseline |
| `profiles/node-ts/files/.github/workflows/node.yml` | Jobs `node-lint`, `node-format`, `node-typecheck`, `node-test` (Vitest), `node-audit` (`npm audit --audit-level=high`) with `npm ci` |
| `profiles/node-ts/README.md` | Commands, gate mapping |

## Requirements

1. **R1:** Installs only via lockfile (`npm ci`); lockfile committed.
2. **R2:** Jobs map to gates `lint`, `format`, `type_check`, `unit_tests`, `security_scan`.
3. **R3:** Dependabot ecosystem `npm` added via manifest.
4. **R4:** No `postinstall` scripts in the skeleton.

## Tasks

- [ ] **T1:** Files and configs.
- [ ] **T2:** Workflow and gate mapping.

## Acceptance Criteria

- [ ] Profile applies cleanly and all jobs pass on the skeleton.

## Verification

```text
npm ci && npm run lint && npm run format:check && npm run typecheck && npm test
```

## Agent Notes

- **Allowed paths:** `profiles/node-ts/**`, this feature file, backlog status.
- **Requires approval:** none.
- **Pitfalls:** Pin the Node version via `.nvmrc` or `engines`, and use the same value in CI.
