[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$ThreadId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$SourceThreadId,

    [string]$RepoRoot = '',
    [string]$PythonExe = 'C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe',
    [string]$FleetTaskName = 'AkashicAurora-SunshineFleet',
    [string]$DiscordTaskName = 'AkashicAurora-SunshineDiscord',
    [string]$GptNewThreadId = '',
    [string]$GptNewSourceThreadId = '',
    [string]$GptNewDiscordTaskName = 'AkashicAurora-GptNewDiscord'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}

$resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
$daemonScript = Join-Path $resolvedRoot 'scripts\bifrost_daemon.py'
$wakeScript = Join-Path $resolvedRoot 'scripts\codex_bifrost_wake.py'
foreach ($requiredPath in @($daemonScript, $wakeScript)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required Sunshine integration file is missing: $requiredPath"
    }
}

$threadPattern = '^[0-9a-f-]{36}$'
if (($GptNewThreadId -and -not $GptNewSourceThreadId) -or
    ($GptNewSourceThreadId -and -not $GptNewThreadId)) {
    throw 'GptNewThreadId and GptNewSourceThreadId must be supplied together.'
}
foreach ($candidate in @($GptNewThreadId, $GptNewSourceThreadId)) {
    if ($candidate -and $candidate -notmatch $threadPattern) {
        throw "Invalid gpt-new Codex thread id: $candidate"
    }
}

$runtimeRoot = Join-Path $env:LOCALAPPDATA 'AkashicAurora\codex-wake'
$statePath = Join-Path $runtimeRoot 'sunshine-discord-continuity.state.json'
$eventPath = Join-Path $runtimeRoot 'sunshine-discord-continuity.events.jsonl'
$gptNewStatePath = Join-Path $runtimeRoot 'gpt-new-discord-continuity.state.json'
$gptNewEventPath = Join-Path $runtimeRoot 'gpt-new-discord-continuity.events.jsonl'
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
    '--external-supervisor',
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
    '--allow-write',
    '--block-ms', '5000'
)

$gptNewDiscordArguments = $null
if ($GptNewThreadId) {
    $gptNewDiscordArguments = ConvertTo-TaskArguments @(
        $wakeScript,
        '--agent', 'gpt-new',
        '--allow-from', 'daniil',
        '--allow-kind', 'chat',
        '--require-source', 'discord',
        '--state-path', $gptNewStatePath,
        '--log-path', $gptNewEventPath,
        '--thread-id', $GptNewThreadId,
        '--source-thread-id', $GptNewSourceThreadId,
        '--binding-kind', 'completed-history-fork',
        '--allow-exec',
        '--block-ms', '5000'
    )
}

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
if ($gptNewDiscordArguments) {
    $tasks += @{
        Name = $GptNewDiscordTaskName
        Description = 'gpt-new Discord ingress bound fail-closed to the preserved former Discord Codex fork.'
        Arguments = $gptNewDiscordArguments
    }
}

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
    GptNewDiscordTask = $(if ($gptNewDiscordArguments) { $GptNewDiscordTaskName } else { $null })
    GptNewThreadId = $(if ($gptNewDiscordArguments) { $GptNewThreadId } else { $null })
    GptNewStatePath = $(if ($gptNewDiscordArguments) { $gptNewStatePath } else { $null })
    GptNewEventPath = $(if ($gptNewDiscordArguments) { $gptNewEventPath } else { $null })
}
