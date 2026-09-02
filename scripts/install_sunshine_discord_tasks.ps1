[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$ThreadId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$SourceThreadId,

    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonExe = 'C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe',
    [string]$FleetTaskName = 'AkashicAurora-SunshineFleet',
    [string]$DiscordTaskName = 'AkashicAurora-SunshineDiscord'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
$daemonScript = Join-Path $resolvedRoot 'scripts\bifrost_daemon.py'
$wakeScript = Join-Path $resolvedRoot 'scripts\codex_bifrost_wake.py'
foreach ($requiredPath in @($daemonScript, $wakeScript)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required Sunshine integration file is missing: $requiredPath"
    }
}

$runtimeRoot = Join-Path $env:LOCALAPPDATA 'AkashicAurora\codex-wake'
$statePath = Join-Path $runtimeRoot 'sol-discord-continuity.state.json'
$eventPath = Join-Path $runtimeRoot 'sol-discord-continuity.events.jsonl'
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

function ConvertTo-TaskArguments {
    param([Parameter(Mandatory = $true)][string[]]$Values)
    return (($Values | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join ' ')
}

$fleetArguments = ConvertTo-TaskArguments @(
    $daemonScript,
    '--agent', 'sol',
    '--spawn-runner',
    '--runner-script', 'bifrost_runner_sol.py',
    '--runner-consume-lane', 'work',
    '--refusal-exit-code', '75',
    '--runner-arg=--ignore-source',
    '--runner-arg=discord'
)
$discordArguments = ConvertTo-TaskArguments @(
    $wakeScript,
    '--agent', 'sol',
    '--allow-from', 'daniil',
    '--allow-kind', 'chat',
    '--require-source', 'discord',
    '--state-path', $statePath,
    '--log-path', $eventPath,
    '--thread-id', $ThreadId,
    '--source-thread-id', $SourceThreadId,
    '--binding-kind', 'completed-history-fork',
    '--allow-exec',
    '--effort', 'medium',
    '--block-ms', '5000'
)

$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$tasks = @(
    @{
        Name = $FleetTaskName
        Description = 'Sunshine managed fleet runner plus Discord outbound feed; Discord ingress is owned by the continuity watcher.'
        Arguments = $fleetArguments
    },
    @{
        Name = $DiscordTaskName
        Description = 'Sunshine Discord ingress bound fail-closed to one persistent Codex continuity thread.'
        Arguments = $discordArguments
    }
)

foreach ($task in $tasks) {
    if ($PSCmdlet.ShouldProcess($task.Name, 'Register restartable at-logon scheduled task')) {
        $action = New-ScheduledTaskAction `
            -Execute $resolvedPython `
            -Argument $task.Arguments `
            -WorkingDirectory $resolvedRoot
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description $task.Description `
            -Force | Out-Null
    }
}

[pscustomobject]@{
    FleetTask = $FleetTaskName
    DiscordTask = $DiscordTaskName
    ContinuityThreadId = $ThreadId
    SourceThreadId = $SourceThreadId
    StatePath = $statePath
    EventPath = $eventPath
}
