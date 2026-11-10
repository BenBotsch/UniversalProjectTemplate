# Pester 5 tests for scripts/bootstrap/New-ProjectRepository.ps1.
# gh is replaced by a global function that records every call and simulates GitHub state;
# the tests never reach GitHub. Run: Invoke-Pester tests/bootstrap

BeforeAll {
    $script:Script = Join-Path $PSScriptRoot '..\..\scripts\bootstrap\New-ProjectRepository.ps1'
    $script:LabelsFile = Join-Path $PSScriptRoot '..\..\.project\labels.yml'
    Import-Module powershell-yaml -ErrorAction Stop
    $script:LabelCount = @((ConvertFrom-Yaml (Get-Content $script:LabelsFile -Raw))['labels']).Count

    function global:gh {
        $call = @($args | ForEach-Object { "$_" })
        $global:GhCalls.Add($call)
        $state = $global:GhState
        $joined = $call -join ' '
        $global:LASTEXITCODE = 0
        switch -Regex ($joined) {
            '^auth status' { if (-not $state.Authenticated) { $global:LASTEXITCODE = 1; 'not logged in' }; return }
            '^repo view octo/UniversalProjectTemplate ' { if ($state.TemplateIsTemplate) { 'true' } else { 'false' }; return }
            '^repo view octo/demo ' { if (-not $state.RepoExists) { $global:LASTEXITCODE = 1; 'Could not resolve' }; return }
            '^repo create ' {
                if ($state.CreateFails) { $global:LASTEXITCODE = 1; 'create failed'; return }
                $state.RepoExists = $true; $state.Branches['main'] = $true; return
            }
            '^api repos/octo/demo/branches/(\S+)' {
                if (-not $state.Branches.ContainsKey($Matches[1])) { $global:LASTEXITCODE = 1 }; return
            }
            '^api repos/octo/demo/git/ref/heads/main' { 'a' * 40; return }
            '^api --method POST repos/octo/demo/git/refs' { $state.Branches['develop'] = $true; return }
            '^label create (\S+)' {
                if ($state.FailingLabel -and $Matches[1] -eq $state.FailingLabel) { $global:LASTEXITCODE = 1; 'label failed' }
                return
            }
            default { $global:LASTEXITCODE = 99; "unexpected gh call: $joined" }
        }
    }

    function script:Invoke-Bootstrap {
        param([string[]]$Extra = @())
        $resultFile = Join-Path $TestDrive 'result.json'
        $output = & powershell.exe -NoProfile -NonInteractive -Command {
            param($ScriptPath, $Labels, $ExtraArgs, $State, $ModulePath, $StubText, $ResultFile)
            $env:PSModulePath = $ModulePath
            $global:GhState = $State
            $global:GhCalls = New-Object System.Collections.Generic.List[object]
            Set-Item -Path function:global:gh -Value ([scriptblock]::Create($StubText))
            $parameters = @{ Owner = 'octo'; Name = 'demo'; LabelsFile = $Labels; WaitSeconds = 0; Json = $true }
            foreach ($item in $ExtraArgs) { $parameters[$item] = $true }
            $summary = & $ScriptPath @parameters
            [pscustomobject]@{
                ExitCode = $LASTEXITCODE
                Summary  = ($summary | Out-String)
                Calls    = @($global:GhCalls | ForEach-Object { $_ -join ' ' })
                State    = $global:GhState
            } | ConvertTo-Json -Depth 6 | Set-Content -Path $ResultFile -Encoding UTF8
        } -args $script:Script, $script:LabelsFile, $Extra, $global:GhState, $env:PSModulePath, ${function:global:gh}.ToString(), $resultFile
        $result = Get-Content -Path $resultFile -Raw | ConvertFrom-Json
        Remove-Item -Path $resultFile
        $result | Add-Member -NotePropertyName Output -NotePropertyValue ($output | Out-String)
        $result | Add-Member -NotePropertyName Steps -NotePropertyValue (($result.Summary | ConvertFrom-Json).steps)
        return $result
    }
}

Describe 'New-ProjectRepository.ps1' {
    BeforeEach {
        $global:GhState = @{
            Authenticated      = $true
            TemplateIsTemplate = $true
            RepoExists         = $false
            CreateFails        = $false
            FailingLabel       = ''
            Branches           = @{}
        }
    }

    Context 'dry run' {
        It 'plans every change and makes no changing gh call' {
            $result = Invoke-Bootstrap
            $result.ExitCode | Should -Be 0
            $changing = @($result.Calls | Where-Object { $_ -match '^(repo create|label create|api --method)' })
            $changing | Should -BeNullOrEmpty
            $result.Output | Should -Match '\[dry-run\] gh repo create octo/demo'
            @($result.Steps | Where-Object Status -eq 'planned').Step |
                Should -Be @('create repository', 'wait for default branch', 'synchronize labels', 'create develop')
        }

        It 'is the default without -DryRun and with -DryRun' {
            (Invoke-Bootstrap -Extra @('DryRun')).ExitCode | Should -Be 0
            $global:GhState.RepoExists | Should -BeFalse
        }
    }

    Context 'apply' {
        It 'creates the repository, all labels and develop' {
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 0
            $result.Calls | Should -Contain 'repo create octo/demo --private --template octo/UniversalProjectTemplate'
            @($result.Calls | Where-Object { $_ -match '^label create .* --force$' }).Count | Should -Be $script:LabelCount
            $result.Calls | Should -Contain ('api --method POST repos/octo/demo/git/refs -f ref=refs/heads/develop -f sha=' + ('a' * 40) + ' --silent')
            @($result.Steps | Where-Object Status -eq 'done').Count | Should -Be 7
        }

        It 'passes arguments as separate array elements' {
            $result = Invoke-Bootstrap -Extra @('Apply')
            $labelCall = @($result.Calls | Where-Object { $_ -like 'label create type:bug *' })[0]
            $labelCall | Should -Be 'label create type:bug --repo octo/demo --color d73a4a --description Unexpected behavior or defect --force'
        }

        It 'omits --description for a label without description' {
            $labels = Join-Path $TestDrive 'labels.yml'
            Set-Content -Path $labels -Encoding UTF8 -Value "labels:`n  - name: plain`n    color: ededed`n"
            $script:LabelsFile, $original = $labels, $script:LabelsFile
            try { $result = Invoke-Bootstrap -Extra @('Apply') } finally { $script:LabelsFile = $original }
            $result.ExitCode | Should -Be 0
            $result.Calls | Should -Contain 'label create plain --repo octo/demo --color ededed --force'
        }

        It 'skips an existing repository and develop branch on a second run' {
            $global:GhState.RepoExists = $true
            $global:GhState.Branches = @{ main = $true; develop = $true }
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 0
            $result.Calls | Should -Not -Contain 'repo create octo/demo --private --template octo/UniversalProjectTemplate'
            @($result.Calls | Where-Object { $_ -match '^api --method POST' }) | Should -BeNullOrEmpty
            ($result.Steps | Where-Object Step -eq 'create repository').Status | Should -Be 'skipped'
            ($result.Steps | Where-Object Step -eq 'create develop').Status | Should -Be 'skipped'
            ($result.Steps | Where-Object Step -eq 'synchronize labels').Status | Should -Be 'done'
        }

        It 'creates develop in an existing repository that lacks it' {
            $global:GhState.RepoExists = $true
            $global:GhState.Branches = @{ main = $true }
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 0
            ($result.Steps | Where-Object Step -eq 'create develop').Status | Should -Be 'done'
        }
    }

    Context 'failures' {
        It 'fails fast when gh is not authenticated' {
            $global:GhState.Authenticated = $false
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 1
            $result.Calls | Should -Be @('auth status')
            ($result.Steps | Where-Object Step -eq 'check gh').Detail | Should -Match 'gh auth login'
        }

        It 'fails when the template is not a template repository' {
            $global:GhState.TemplateIsTemplate = $false
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 1
            @($result.Calls | Where-Object { $_ -like 'repo create*' }) | Should -BeNullOrEmpty
        }

        It 'reports a failed repository creation and stops' {
            $global:GhState.CreateFails = $true
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 1
            ($result.Steps | Where-Object Step -eq 'create repository').Status | Should -Be 'failed'
            @($result.Calls | Where-Object { $_ -like 'label create*' }) | Should -BeNullOrEmpty
        }

        It 'fails when the default branch does not appear in time' {
            $global:GhState.RepoExists = $true
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 1
            ($result.Steps | Where-Object Step -eq 'wait for default branch').Status | Should -Be 'failed'
        }

        It 'continues after a failed label and reports it' {
            $global:GhState.FailingLabel = 'type:bug'
            $result = Invoke-Bootstrap -Extra @('Apply')
            $result.ExitCode | Should -Be 1
            @($result.Calls | Where-Object { $_ -like 'label create*' }).Count | Should -Be $script:LabelCount
            ($result.Steps | Where-Object Step -eq 'synchronize labels').Detail | Should -Be 'failed: type:bug'
        }

        It 'fails when gh is not installed' {
            $output = & powershell.exe -NoProfile -NonInteractive -Command {
                param($ScriptPath, $Labels)
                $env:PATH = ''
                & $ScriptPath -Owner octo -Name demo -LabelsFile $Labels -Json | Out-String
                "exit=$LASTEXITCODE"
            } -args $script:Script, $script:LabelsFile
            ($output -join "`n") | Should -Match 'GitHub CLI \(gh\) not found'
            ($output -join "`n") | Should -Match 'exit=1'
        }
    }

    Context 'parameter validation' {
        It 'rejects <Name>' -ForEach @(
            @{ Name = 'an owner with spaces'; Parameters = @{ Owner = 'bad owner'; Name = 'demo' } }
            @{ Name = 'a name with a semicolon'; Parameters = @{ Owner = 'octo'; Name = 'demo;rm' } }
            @{ Name = 'a description with double quotes'; Parameters = @{ Owner = 'octo'; Name = 'demo'; Description = 'say "hi"' } }
            @{ Name = 'an unknown visibility'; Parameters = @{ Owner = 'octo'; Name = 'demo'; Visibility = 'secret' } }
            @{ Name = 'a malformed template'; Parameters = @{ Owner = 'octo'; Name = 'demo'; Template = 'no-slash' } }
        ) {
            { & $script:Script @Parameters } | Should -Throw
        }
    }
}
