# Technology Profiles

A technology profile adds the tools, CI jobs and quality gates of one stack to a project created
from this template. The base layer supports no language. Its gates for formatting, lint, tests,
build and security stay `not_implemented` until a profile covers them. The design is recorded in
[ADR-0006](../docs/architecture/adr/0006-technology-profiles.md).

`profiles/` is a template-only path. A derived project keeps the files a profile applied, but not
this directory.

## Applying a Profile

During initialization, `init` applies the profile in the same commit:

```text
project-bootstrap init --repo OWNER/NAME --profile python --apply --issue N
```

In an initialized project, run the command from a template checkout:

```text
project-bootstrap apply-profile --profile python --path ../my-project [--apply] [--force]
```

`--source DIR` reads profiles from another directory. The default is this directory of the
installed template checkout. Like every command, `apply-profile` only reports the plan without
`--apply`. It does not commit, so review and commit the changes on a work branch.

A second run plans only `noop`. A file or block the project has edited is reported as a conflict
and kept. `--force` replaces it with the profile's version. A file deleted after the profile was
recorded is not recreated, unless `--force` is given.

## Layout

```text
profiles/
  _schema/profile.schema.json   schema of profile.yml
  <id>/
    profile.yml                 manifest
    README.md                   what the profile adds; not copied
    files/                      files copied to the same path in the project
```

The manifest lists the following:

| Field | Meaning |
|---|---|
| `id`, `version` | Directory name and semantic version; `project.yml` records both in `profiles` |
| `description` | One line for reports |
| `requires_profiles` | Profiles that must be applied first |
| `technology` | Languages and package managers added to `project.yml` |
| `files` | Every file below `files/`, exactly; tokens are replaced in paths and content |
| `ci_jobs` | Jobs added to `ci.yml`; each calls a workflow of the profile and is added to `quality-gate.needs` |
| `quality_gates` | Gates added to `quality-gates.yml`, in its format |
| `dependabot` | Entries added to `updates` in `dependabot.yml` |
| `labels` | Entries added to `labels.yml`, usually an `area:*` label |

The tokens are `PROJECT_NAME`, `PROJECT_DESCRIPTION` and `PROJECT_PACKAGE`. `PROJECT_PACKAGE` is
the name in lower case with every other character replaced by `_`.

## Rules for a Profile

- A profile owns its files. It must not ship a base file such as `ci.yml`, `quality-gates.yml`,
  `dependabot.yml`, `labels.yml` or `project.yml`.
- Base files get entries only at their anchors, such as `# bootstrap:profile-jobs`. Projects keep
  the anchors.
- Every job of a profile workflow has one gate, and every gate names a job of a profile workflow.
  `load_profile` rejects a profile that breaks this.
- A gate that replaces a generic base gate sets `covers: <gate>` and lists its languages in
  `applies_when.languages`.
- Profile workflows follow the rules of the base workflows. Actions are pinned to commit SHAs and
  permissions are read-only. The template's CI checks them with actionlint, zizmor and the
  pinning check.

## Adding a Profile

1. Create `profiles/<id>/` with `profile.yml`, `README.md` and `files/`.
2. Add a test in `tools/engineering-bootstrap/tests/` that applies the profile to a template
   checkout and validates the result.
3. Raise `version` whenever the files or entries change.
