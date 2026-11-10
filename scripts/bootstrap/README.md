# Bootstrap Scripts

[New-ProjectRepository.ps1](New-ProjectRepository.ps1) creates a new GitHub repository from this
template with the GitHub CLI. It is the first stage of the bootstrap. It prepares the repository,
but does not yet configure rules or project files; see [Limits](#limits).

## What the Script Does

1. Checks that `gh` is installed and authenticated, and that the template repository is marked as
   a template.
2. Creates `OWNER/NAME` from the template, unless the repository already exists.
3. Waits until the default branch of the new repository exists. GitHub copies the template
   asynchronously.
4. Creates or updates every label from [.project/labels.yml](../../.project/labels.yml) with
   `gh label create --force`. Existing labels that are not in the file are left unchanged; no
   label is deleted.
5. Creates the development branch (`develop`) from the default branch (`main`) through the GitHub
   API, unless it already exists.
6. Prints a summary of every step with the status `done`, `skipped`, `planned` or `failed`.

The script is idempotent: running it again against an existing repository skips the creation and
the existing `develop` branch and updates the labels.

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows PowerShell 5.1 or PowerShell 7 | The script uses no features beyond 5.1. |
| [GitHub CLI](https://cli.github.com/) (`gh`) | Authenticate with `gh auth login`. |
| PowerShell module `powershell-yaml` | Reads `labels.yml`: `Install-Module powershell-yaml -Scope CurrentUser` |
| Template repository | Must be marked as a template repository on GitHub. |

### Permissions

The account used by `gh` needs:

- Permission to create repositories for the owner. For an organization this can be restricted by
  the organization settings.
- Read access to the template repository.
- Write access to the new repository, for its labels and branches (`gh` scope `repo`).

The script uses the existing `gh` login. It does not read, print or store a token, and gh output is
not written to the log.

## Usage

Without `-Apply` the script runs as a dry run. It performs read-only checks and prints every `gh`
call that would change something, but changes nothing:

```text
./scripts/bootstrap/New-ProjectRepository.ps1 -Owner octo -Name my-project -DryRun
```

Check the planned calls, then run the same command with `-Apply`:

```text
./scripts/bootstrap/New-ProjectRepository.ps1 -Owner octo -Name my-project -Visibility private -Description "Example project" -Apply
```

`-Apply` creates a real repository. An AI agent runs it only with explicit approval; see
[Agent Permissions](../../docs/governance/agent-permissions.md).

| Parameter | Default | Description |
|---|---|---|
| `-Owner` | required | User or organization of the new repository |
| `-Name` | required | Name of the new repository |
| `-Visibility` | `private` | `private`, `public` or `internal` |
| `-Description` | empty | Repository description; double quotes are not allowed |
| `-Template` | `<Owner>/UniversalProjectTemplate` | Template repository as `OWNER/REPOSITORY` |
| `-LabelsFile` | `.project/labels.yml` | Label definitions |
| `-DefaultBranch` | `main` | Default branch of the template |
| `-DevelopmentBranch` | `develop` | Integration branch to create |
| `-DryRun` | on | Show the planned changes only |
| `-Apply` | off | Perform the changes |
| `-WaitSeconds` | `120` | Maximum wait for the default branch of a new repository |
| `-Json` | off | Print the summary as JSON |

The exit code is `0` if no step failed, otherwise `1`. A failed label does not stop the other
labels, but the step is reported as failed.

## Limits

This first stage does not:

- Configure branch protection or rulesets.
- Replace placeholders or initialize project files in the new repository.
- Audit the repository settings.
- Delete labels that are not in `labels.yml`.

These steps follow in the next stage of the bootstrap. Until then, follow the manual steps in
[Using this template](../../README.md#using-this-template) after creating a repository.

## Tests

The Pester tests replace `gh` with a function that simulates GitHub; they never contact GitHub.
They need Pester 5 and `powershell-yaml`:

```text
Install-Module Pester -MinimumVersion 5.0 -Scope CurrentUser
Invoke-Pester tests/bootstrap
```
