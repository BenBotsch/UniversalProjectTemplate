# PROJECT_NAME

PROJECT_DESCRIPTION

<!-- template-only:start -->
## Using this template

This repository is a language-agnostic project template. To turn a repository created from it
into a project:

1. Create the repository from the template on GitHub and give it a description. The script in
   `scripts/bootstrap/` does this and synchronizes the labels; see its
   [README](scripts/bootstrap/README.md).
2. Clone the new repository, install the bootstrap tool from `tools/engineering-bootstrap/` of
   the clone and open an issue for the initialization.
3. Run `project-bootstrap init --repo <owner>/<name>` in the clone to review the plan, then again
   with `--apply --issue <number>`. It deletes the template-only files and this section, replaces
   the placeholders, writes the license you choose and commits the result on a branch.
4. Push the branch, open a pull request to `develop`, select a technology profile and fill in the
   sections below.

The tool's README in `tools/engineering-bootstrap/` describes the options of `init`.
<!-- template-only:end -->

## Features

Describe the main capabilities of the project.

## Supported Platforms

List the operating systems, runtimes or devices the project supports.

## Technology Stack

List languages, frameworks and package managers. Keep this list consistent with
`technology` in [.project/project.yml](.project/project.yml).

## Requirements

List the tools and versions needed to build and run the project.

## Quick Start

Show the shortest path from a fresh clone to a running result.

## Development

Local setup, branches, commits and pull requests are described in [CONTRIBUTING.md](CONTRIBUTING.md).

## Tests and Quality

Every change runs through the quality gates defined in
[.project/quality-gates.yml](.project/quality-gates.yml). A required check that was skipped or is
not implemented counts as failed. The `quality-gate` job is the single required check; see the
[Quality Model](docs/governance/quality-model.md). The commands for local checks are listed in
[CONTRIBUTING.md](CONTRIBUTING.md#tests-and-checks).

## Project Structure

| Path | Purpose |
|---|---|
| `.github/` | Issue forms, pull request template, CODEOWNERS, workflows, Dependabot, release notes |
| `.project/` | Machine-readable project metadata used by bootstrap, validation and the dashboard |
| `docs/` | Project documentation; start at [docs/INDEX.md](docs/INDEX.md) |
| `scripts/` | Bootstrap, CI and maintenance scripts |
| `tests/`, `examples/` | Optional, depending on the technology profile |
| `AGENTS.md` | Binding rules for contributors and coding agents |
| `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CHANGELOG.md` | Community and policy files |
| `LICENSE` | License of the project; see [License](#license) |
| `.editorconfig`, `.gitattributes`, `.gitignore` | Cross-platform formatting, line endings and ignore rules |

The template prescribes no programming language and no source layout. Language-specific files
such as `pyproject.toml`, `CMakeLists.txt` or `package.json` come from technology profiles.

## Documentation

Start at [docs/INDEX.md](docs/INDEX.md). Rules for contributors and coding agents are in
[AGENTS.md](AGENTS.md).

## Roadmap

Planning happens in the GitHub Issues and milestones of
[OWNER/REPOSITORY](https://github.com/OWNER/REPOSITORY/issues).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open an issue or a pull request. For questions,
see [SUPPORT.md](SUPPORT.md).

## Security

Do not report vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md).

## License

The template is licensed under the [MIT License](LICENSE). A project created from the template
receives this `LICENSE` file as a copy. Each project decides on its own license explicitly: keep
the MIT License with the project's copyright holder, or replace the file with another license.
