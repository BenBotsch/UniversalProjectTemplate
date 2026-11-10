# Template Development Tools

Template-only scripts that maintain this workspace. Like the rest of `template-dev/`, they are
removed from derived repositories by `project-bootstrap init`. They use only the Python standard
library (3.10+) and are run with `-I` (isolated mode) from the repository root.

| Script | Purpose |
|---|---|
| `generate_backlog.py` | Regenerates [backlog.md](../backlog.md) and all files in [epics/](../epics/) from feature frontmatter |
| `verify_backlog.py` | Checks consistency of the whole workspace; exit code 1 on any error |

## Usage

```text
python -I template-dev/tools/generate_backlog.py
python -I template-dev/tools/verify_backlog.py
```

Both accept an optional path to the `template-dev/` directory; the default is the parent of this
folder.

## When to run

- After changing a feature's frontmatter (`status`, `priority`, `dependencies`, `title`, ...):
  run the generator, then the verifier, and commit both the feature file and the regenerated files.
- Before opening any pull request that touches `template-dev/`: run the verifier.

## What the generator owns

The generator **overwrites** `backlog.md` and every `epics/EPIC-*.md`. Do not edit these files by
hand; change the source instead:

| Content | Source |
|---|---|
| Feature rows (title, phase, priority, effort, dependencies, decisions, status) | Frontmatter of `features/FEAT-*.md` |
| Rank and tier (`first`, `then`, `later`) | `RANK` list in `generate_backlog.py` |
| Epic goal, scope, non-goals, risks, success criteria | `EPICS` dictionary in `generate_backlog.py` |

A new feature must be added to `RANK`; the generator fails otherwise.

## What the verifier checks

- Frontmatter of every feature: required keys, allowed values, ID matches file name and H1, unique IDs.
- Required sections in every feature file.
- `agent_ready: true` only without blocking decisions.
- Dependencies and decisions exist, no cycles, no dependency on a later phase.
- Every feature appears exactly once in the backlog, after its dependencies, with matching file and
  status; exactly once in the epic named in its frontmatter; and in the roadmap.
- All relative links and anchors in `template-dev/**/*.md` resolve.
- Template-only requirements are present in `FEAT-003`, `FEAT-013`, `FEAT-015`, `FEAT-028`, `FEAT-030`.
