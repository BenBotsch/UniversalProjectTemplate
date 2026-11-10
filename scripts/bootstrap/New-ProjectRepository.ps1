#Requires -Version 5.1
<#
.SYNOPSIS
    Creates a GitHub repository from the template and prepares labels and the develop branch.

.DESCRIPTION
    Phase A bootstrap with the GitHub CLI (gh). The script:

    1. Checks that gh is installed and authenticated, and that the template repository exists.
    2. Creates <owner>/<name> from the template, unless the repository already exists.
    3. Waits until the default branch of the new repository exists.
    4. Creates or updates every label from .project/labels.yml. Labels are never deleted.
    5. Creates the development branch from the default branch, unless it already exists.
    6. Prints a summary of done, skipped, planned and failed steps.

    Without -Apply the script runs as a dry run: it performs read-only checks and prints every
    gh call that would change something, but changes nothing. Running it again against an
    existing repository updates the labels and skips existing branches.

.PARAMETER Owner
    User or organization that owns the new repository.

.PARAMETER Name
    Name of the new repository.

.PARAMETER Visibility
    private (default), public or internal.

.PARAMETER Description
    Repository description. Double quotes are not allowed.

.PARAMETER Template
    Template repository as <owner>/<repository>. Default: <Owner>/UniversalProjectTemplate.

.PARAMETER LabelsFile
    Label definitions. Default: .project/labels.yml of this template checkout.

.PARAMETER DefaultBranch
    Default branch of the template. Default: main.

.PARAMETER DevelopmentBranch
    Integration branch to create. Default: develop.

.PARAMETER DryRun
    Show the planned changes only. This is the default; the switch makes it explicit.

.PARAMETER Apply
    Perform the changes.

.PARAMETER WaitSeconds
    How long to wait for the default branch of a newly created repository. Default: 120.

.PARAMETER Json
    Print the summary as JSON instead of a table.

.EXAMPLE
    ./scripts/bootstrap/New-ProjectRepository.ps1 -Owner octo -Name my-project -DryRun

.EXAMPLE
    ./scripts/bootstrap/New-ProjectRepository.ps1 -Owner octo -Name my-project -Visibility private -Apply
#>
[CmdletBinding(DefaultParameterSetName = 'DryRun')]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$')]
    [string]$Owner,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9._-]{0,99}$')]
    [string]$Name,

    [ValidateSet('private', 'public', 'internal')]
    [string]$Visibility = 'private',

    [ValidatePattern('^[^"]*$')]
    [string]$Description = '',

    [ValidatePattern('^$|^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$')]
    [string]$Template = '',

    [string]$LabelsFile = (Join-Path $PSScriptRoot '..\..\.project\labels.yml'),

    [ValidatePattern('^[A-Za-z0-9._/-]+$')]
    [string]$DefaultBranch = 'main',

    [ValidatePattern('^[A-Za-z0-9._/-]+$')]
    [string]$DevelopmentBranch = 'develop',

    [Parameter(ParameterSetName = 'DryRun')]
    [switch]$DryRun,

    [Parameter(Mandatory = $true, ParameterSetName = 'Apply')]
    [switch]$Apply,

    [ValidateRange(0, 3600)]
    [int]$WaitSeconds = 120,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Repository = "$Owner/$Name"
if (-not $Template) { $Template = "$Owner/UniversalProjectTemplate" }
$IsDryRun = -not $Apply
$Steps = New-Object System.Collections.Generic.List[object]

function Add-Step {
    <# Records the result of one step for the summary. #>
    param([string]$Step, [ValidateSet('done', 'skipped', 'planned', 'failed')][string]$Status, [string]$Detail = '')
    $Steps.Add([pscustomobject]@{ Step = $Step; Status = $Status; Detail = $Detail })
}

function Format-Argument {
    <# Quotes an argument for display in dry-run output. #>
    param([string]$Value)
    if ($Value -match '[\s"]' -or $Value -eq '') { return '"' + $Value + '"' }
    return $Value
}

function Invoke-Gh {
    <#
    Runs gh with an argument array, never through a shell string, and returns exit code and
    output. Output is returned to the caller and not printed, so that nothing gh prints about
    the authentication ends up in the log.
    #>
    param([string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $global:LASTEXITCODE = 0
        $output = & gh @Arguments 2>&1
        $code = $global:LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    [pscustomobject]@{ ExitCode = $code; Output = (@($output) | ForEach-Object { "$_" }) -join "`n" }
}

function Invoke-Change {
    <# Runs a changing gh call, or prints it in a dry run. Returns $true on success. #>
    param([string[]]$Arguments)
    if ($IsDryRun) {
        Write-Host ('[dry-run] gh ' + (($Arguments | ForEach-Object { Format-Argument $_ }) -join ' '))
        return $true
    }
    $result = Invoke-Gh $Arguments
    if ($result.ExitCode -ne 0) {
        Write-Warning ("gh $($Arguments[0]) $($Arguments[1]) failed: " + $result.Output)
        return $false
    }
    return $true
}

function Test-Branch {
    <# Returns $true if the branch exists in the repository. #>
    param([string]$Branch)
    (Invoke-Gh @('api', "repos/$Repository/branches/$Branch", '--silent')).ExitCode -eq 0
}

function Read-Label {
    <# Reads and checks the label definitions from the labels file. #>
    if (-not (Test-Path -LiteralPath $LabelsFile -PathType Leaf)) {
        throw "labels file not found: $LabelsFile"
    }
    if (-not (Get-Module -ListAvailable -Name 'powershell-yaml')) {
        throw "PowerShell module 'powershell-yaml' is missing; install it with: Install-Module powershell-yaml -Scope CurrentUser"
    }
    Import-Module powershell-yaml -ErrorAction Stop
    $data = ConvertFrom-Yaml (Get-Content -LiteralPath $LabelsFile -Raw -Encoding UTF8)
    if ($null -eq $data -or -not $data.ContainsKey('labels') -or $data['labels'].Count -eq 0) {
        throw "labels file has no 'labels' list: $LabelsFile"
    }
    foreach ($label in $data['labels']) {
        if (-not ($label['name'] -is [string]) -or $label['name'] -eq '' -or $label['color'] -notmatch '^[0-9a-fA-F]{6}$') {
            throw "invalid label entry in ${LabelsFile}: $($label | ConvertTo-Json -Compress)"
        }
        if ("$($label['name'])$($label['description'])" -match '"') {
            throw "label name or description contains a double quote: $($label['name'])"
        }
    }
    return $data['labels']
}

function Write-Summary {
    if ($Json) {
        [pscustomobject]@{
            repository = $Repository
            template   = $Template
            dry_run    = $IsDryRun
            steps      = @($Steps | ForEach-Object { [ordered]@{ step = $_.Step; status = $_.Status; detail = $_.Detail } })
        } | ConvertTo-Json -Depth 4 | Write-Output
        return
    }
    $mode = if ($IsDryRun) { 'dry run, nothing changed' } else { 'applied' }
    Write-Host ''
    Write-Host "Summary for $Repository ($mode):"
    $Steps | Format-Table -AutoSize -Wrap | Out-String | Write-Host
    if ($IsDryRun) { Write-Host 'Run again with -Apply to perform the planned steps.' }
}

function Invoke-Bootstrap {
    # 1. Preconditions: fail fast before anything changes.
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Add-Step 'check gh' 'failed' 'GitHub CLI (gh) not found; install it from https://cli.github.com/'
        return
    }
    if ((Invoke-Gh @('auth', 'status')).ExitCode -ne 0) {
        Add-Step 'check gh' 'failed' "gh is not authenticated; run 'gh auth login'"
        return
    }
    Add-Step 'check gh' 'done' 'installed and authenticated'

    try {
        $labels = @(Read-Label)
    } catch {
        Add-Step 'read labels' 'failed' $_.Exception.Message
        return
    }
    Add-Step 'read labels' 'done' "$($labels.Count) labels"

    $templateInfo = Invoke-Gh @('repo', 'view', $Template, '--json', 'isTemplate', '--jq', '.isTemplate')
    if ($templateInfo.ExitCode -ne 0) {
        Add-Step 'check template' 'failed' "template repository $Template not found or not accessible"
        return
    }
    if ($templateInfo.Output.Trim() -ne 'true') {
        Add-Step 'check template' 'failed' "$Template is not marked as a template repository"
        return
    }
    Add-Step 'check template' 'done' $Template

    # 2. Repository: create it unless it exists.
    $exists = (Invoke-Gh @('repo', 'view', $Repository, '--json', 'name')).ExitCode -eq 0
    if ($exists) {
        Add-Step 'create repository' 'skipped' 'repository already exists'
    } else {
        $create = @('repo', 'create', $Repository, "--$Visibility", '--template', $Template)
        if ($Description) { $create += @('--description', $Description) }
        if (-not (Invoke-Change $create)) {
            Add-Step 'create repository' 'failed' 'gh repo create failed'
            return
        }
        Add-Step 'create repository' $(if ($IsDryRun) { 'planned' } else { 'done' }) "$Visibility, from $Template"
    }

    # 3. Template copies are created asynchronously; wait for the default branch.
    if ($IsDryRun -and -not $exists) {
        Add-Step 'wait for default branch' 'planned' "wait up to $WaitSeconds s for $DefaultBranch"
    } else {
        $deadline = (Get-Date).AddSeconds($WaitSeconds)
        while (-not (Test-Branch $DefaultBranch)) {
            if ((Get-Date) -ge $deadline) {
                Add-Step 'wait for default branch' 'failed' "$DefaultBranch did not appear within $WaitSeconds s"
                return
            }
            Start-Sleep -Seconds 3
        }
        Add-Step 'wait for default branch' 'done' $DefaultBranch
    }

    # 4. Labels: create or update, never delete.
    $failedLabels = @()
    foreach ($label in $labels) {
        $arguments = @('label', 'create', [string]$label['name'], '--repo', $Repository, '--color', [string]$label['color'])
        # Windows PowerShell 5.1 drops empty arguments to native commands, so an empty
        # description is omitted instead of being passed as "".
        if ([string]$label['description']) { $arguments += @('--description', [string]$label['description']) }
        $arguments += '--force'
        if (-not (Invoke-Change $arguments)) { $failedLabels += [string]$label['name'] }
    }
    if ($failedLabels.Count -gt 0) {
        Add-Step 'synchronize labels' 'failed' ('failed: ' + ($failedLabels -join ', '))
    } else {
        Add-Step 'synchronize labels' $(if ($IsDryRun) { 'planned' } else { 'done' }) "$($labels.Count) labels created or updated"
    }

    # 5. Development branch from the default branch, unless it exists.
    if ($exists -and (Test-Branch $DevelopmentBranch)) {
        Add-Step "create $DevelopmentBranch" 'skipped' 'branch already exists'
        return
    }
    $sha = '<sha of ' + $DefaultBranch + '>'
    if (-not ($IsDryRun -and -not $exists)) {
        $ref = Invoke-Gh @('api', "repos/$Repository/git/ref/heads/$DefaultBranch", '--jq', '.object.sha')
        if ($ref.ExitCode -ne 0 -or $ref.Output.Trim() -notmatch '^[0-9a-f]{40}$') {
            Add-Step "create $DevelopmentBranch" 'failed' "cannot read the head of $DefaultBranch"
            return
        }
        $sha = $ref.Output.Trim()
    }
    $branch = @('api', '--method', 'POST', "repos/$Repository/git/refs",
        '-f', "ref=refs/heads/$DevelopmentBranch", '-f', "sha=$sha", '--silent')
    if (-not (Invoke-Change $branch)) {
        Add-Step "create $DevelopmentBranch" 'failed' 'creating the branch failed'
        return
    }
    Add-Step "create $DevelopmentBranch" $(if ($IsDryRun) { 'planned' } else { 'done' }) "from $DefaultBranch"
}

Invoke-Bootstrap
Write-Summary
if (@($Steps | Where-Object { $_.Status -eq 'failed' }).Count -gt 0) { exit 1 }
exit 0
