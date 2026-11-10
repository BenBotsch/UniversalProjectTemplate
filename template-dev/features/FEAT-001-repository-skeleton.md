---
id: "FEAT-001"
title: "Create Repository Skeleton and Hygiene Files"
epic: "EPIC-01"
phase: 1
status: "planned"
priority: "critical"
effort: "s"
target_repo: "universal-project-template"
spec_refs: ["§1.2", "§1.3", "§1.4", "§3.1", "§3.2", "§3.3"]
dependencies: []
blocked_by_decisions: []
agent_ready: true
related_issues: []
created_at: "2026-11-10"
updated_at: "2026-11-10"
---

# FEAT-001: Create Repository Skeleton and Hygiene Files

## Objective

The repository has the technology-agnostic top-level layout from §3.1 and the cross-platform
hygiene files `.editorconfig`, `.gitattributes` and `.gitignore`.

## Background

The template must not force any language or `src/` layout (§1.2, §1.3). Git does not store empty
directories, and illustrative placeholders such as `[local composite/reusable actions as needed]`
must not be created as files (§3.1 note). Directories are therefore created by the features that
put real content into them; this feature only lays down the hygiene files and documents the layout.

## Scope

- `.editorconfig`, `.gitattributes`, `.gitignore` for a polyglot repository.
- A short structure description that later goes into `README.md` (`FEAT-002`) and
  `docs/development/` (`FEAT-003`).

### Out of Scope

- Language-specific folders (`src/`, `lib/`, `CMakeLists.txt`); these belong to profiles (`EPIC-08`).
- Content files of other features.

## Deliverables

| Path | Description |
|---|---|
| `.editorconfig` | UTF-8, LF, final newline, trim trailing whitespace; 2 spaces for YAML/JSON/Markdown; 4 spaces for Python; tabs for Makefiles; CRLF for `*.cmd`/`*.bat`/`*.ps1` only if required |
| `.gitattributes` | `* text=auto eol=lf`; explicit `eol=crlf` for `*.cmd`, `*.bat`; `binary` for common binary types; `linguist-documentation` for `docs/**` |
| `.gitignore` | OS/editor noise (`.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/*` with shared settings allowed), common build/cache dirs (`__pycache__/`, `node_modules/`, `build/`, `dist/`, `.venv/`, `coverage/`), local env files (`.env`, `.env.*` except `.env.example`) |
| `template-dev/features/FEAT-001-repository-skeleton.md` | Status update only |

## Requirements

1. **R1:** No file or directory forces a programming language or framework.
2. **R2:** Line-ending rules produce identical checkouts on Windows, Linux and macOS.
3. **R3:** `.gitignore` never ignores files that the template itself ships (`.project/`, `.github/`, `docs/`, `scripts/`).
4. **R4:** Secrets-prone files (`.env`, `*.pem`, `*.key`) are ignored by default; `.env.example` is not.
5. **R5:** No empty directories and no literal placeholder files are committed.

## Tasks

- [ ] **T1:** Write `.editorconfig` and `.gitattributes`.
- [ ] **T2:** Write `.gitignore` with grouped, commented sections.
- [ ] **T3:** Draft a "Repository Structure" section (text block in the PR description) for reuse by `FEAT-002` and `FEAT-003`.

## Acceptance Criteria

- [ ] No programming language or framework is mandatory (§17.1).
- [ ] `git check-ignore` confirms `.env` and `node_modules/` are ignored and `.env.example`, `.project/project.yml` are not.
- [ ] `git ls-files --eol` shows LF for text files after a fresh clone on Windows.

## Verification

```text
git check-ignore -v .env node_modules/x build/x
git check-ignore -v .env.example .project/project.yml   # must print nothing
git ls-files --eol
```

## Agent Notes

- **Allowed paths:** `.editorconfig`, `.gitattributes`, `.gitignore`, this feature file, `template-dev/backlog.md` (status column).
- **Requires approval:** none.
- **Pitfalls:** Do not ignore `.vscode/` completely if shared settings are wanted later; do not add `template-dev/` to `.gitignore` (it must stay in the template repository).
