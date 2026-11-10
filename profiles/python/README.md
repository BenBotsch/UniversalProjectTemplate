# Python Profile

The `python` profile turns a derived project into a Python package. It uses uv for the
environment and the lock file, Ruff for formatting and lint, mypy for types, pytest with coverage
for tests, `uv build` for the distribution and pip-audit for known vulnerabilities.

```text
project-bootstrap init --repo OWNER/NAME --profile python --apply --issue N
```

## What It Adds

| Path | Content |
|---|---|
| `pyproject.toml` | Package metadata, the `dev` dependency group and the Ruff, mypy, pytest and coverage settings |
| `src/<package>/__init__.py`, `py.typed` | The package, typed, with `__version__` |
| `tests/test_smoke.py` | One test that imports the package |
| `.github/workflows/python.yml` | The jobs below, called by `ci.yml` as job `python` |
| `.github/actions/python-setup/action.yml` | Shared setup: Python, uv and `uv sync` |
| `.pre-commit-config.yaml` | Local hooks: whitespace, YAML and TOML checks, Ruff and mypy |
| `docs/figures/README.md`, `.gitattributes`, `.editorconfig` | Guide and settings for generated figures |

The package name is the project name in lower case, with every other character replaced by `_`.
The profile also adds a Dependabot entry for the `uv` ecosystem and the label `area:python`.

## Commands

```text
uv lock                      # create uv.lock; commit it
uv sync                      # install the project and the dev group
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest --cov
uv build
```

Commit `uv.lock`. CI then installs with `uv sync --locked` and fails when the lock file is out of
date. Without `uv.lock`, CI resolves the dependencies anew and warns.

## Jobs and Quality Gates

Each job reports into `quality-gate` (ADR-0003). The profile gates replace the generic base gates
with `covers`, so these become inapplicable for a Python project.

| Job | Gate | Covers | Command |
|---|---|---|---|
| `python / format` | `python_formatting` | `formatting` | `ruff format --check .` |
| `python / lint` | `python_lint` | `lint` | `ruff check .`, and `figkit check docs/figures` when figures exist |
| `python / type-check` | `python_type_check` | none | `mypy` |
| `python / test (3.12)`, `(3.13)` | `python_tests` | `tests` | `pytest --cov` |
| `python / build` | `python_build` | `build` | `uv build` |
| `python / audit` | `python_security` | `security` | `pip-audit --strict` on the exported lock |

`python_tests` is required for code changes. A pull request that changes only Markdown or `docs/`
skips it. pytest fails when it collects no test, so deleting the tests fails the gate.

## Figures

The optional dependency group `figures` installs [FigureKit](https://github.com/BenBotsch/FigureKit),
the shared figure style, with matplotlib. `uv sync` and the built package leave it out.
`docs/figures/README.md` describes the naming, the light and dark files, embedding and alt text.

When `docs/figures/` holds an SVG, PNG or WebP file, the `lint` job installs the group and runs
`figkit check docs/figures`. A missing dark file, an opaque chart or a file above its budget
fails the gate. Without figures the job is unchanged. matplotlib writes SVG lines that end with a
space, so the pre-commit hooks, `.gitattributes` and `.editorconfig` leave `docs/figures/*.svg`
unchanged.

FigureKit is pinned to a tag. The audit job leaves the git source out of its export, because it
has no hash and no PyPI advisory, and audits its dependencies. To drop figures, delete the group
and `docs/figures/`.

## Decisions

- **uv, not pip.** One tool installs Python dependencies, locks them and builds the package. The
  version of uv is pinned in the setup action. Dependabot updates the lock through its `uv`
  ecosystem.
- **Coverage is reported, not enforced.** `fail_under` is 0, because a new project has no code to
  measure. Raise it once the project has real code. 80 % is a reasonable start.
- **The base layer stays out.** `scripts/ci/` and `tests/ci/` belong to the template base layer
  and are tested by its `repository-validation` job. Ruff, mypy and pytest exclude them.
- **Supported Python versions.** `requires-python` is `>=3.12`. The test matrix runs every
  version from 3.12 on. Change both together.
