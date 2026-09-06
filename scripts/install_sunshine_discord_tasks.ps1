[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$ThreadId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f-]{36}$')]
    [string]$SourceThreadId,

    [string]$RepoRoot = '',
    [string]$RuntimeConfigRoot = '',
    [string]$PythonExe = '',
    [string]$GatewayTaskName = 'AkashicAurora-DiscordGateway',
    [Alias('LegacyGatewayWatchdogTaskName')]
    [string]$GatewayWatchdogTaskName = 'AkashicAurora-EarWatchdog',
    [string]$FleetTaskName = 'AkashicAurora-SunshineFleet',
    [string]$DiscordTaskName = 'AkashicAurora-SunshineDiscord',
    [string]$GptNewThreadId = '',
    [string]$GptNewSourceThreadId = '',
    [switch]$EnableGptNewExec,
    [switch]$EnableGptNewWrite,
    [string]$GptNewDiscordTaskName = 'AkashicAurora-GptNewDiscord'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}

$resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

# A normal clone is self-contained. A persistent deployment worktree may opt in
# to a separate host-owned credentials/ACL root, but that relationship must be
# explicit at install time rather than encoded as this machine's drive layout.
if ([string]::IsNullOrWhiteSpace($RuntimeConfigRoot)) {
    $RuntimeConfigRoot = $resolvedRoot
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCommand = Get-Command 'py.exe' -CommandType Application -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        $pythonCommand = Get-Command 'python.exe' -CommandType Application -ErrorAction SilentlyContinue
    }
    if (-not $pythonCommand) {
        throw 'No Python launcher found. Pass -PythonExe with an explicit interpreter path.'
    }
    $PythonExe = $pythonCommand.Source
}
$resolvedRuntimeConfigRoot = (Resolve-Path -LiteralPath $RuntimeConfigRoot).Path
$resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
$resolvedSchtasks = (Get-Command 'schtasks.exe' -CommandType Application -ErrorAction Stop).Source
$daemonScript = Join-Path $resolvedRoot 'scripts\bifrost_daemon.py'
$gatewayScript = Join-Path $resolvedRoot 'scripts\bifrost_runner_discord.py'
$wakeScript = Join-Path $resolvedRoot 'scripts\codex_bifrost_wake.py'
$serviceLauncher = Join-Path $resolvedRoot 'scripts\run_aurora_service.py'
foreach ($requiredPath in @($daemonScript, $gatewayScript, $wakeScript, $serviceLauncher)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required Sunshine integration file is missing: $requiredPath"
    }
}

# A persistent code worktree intentionally excludes host-local authority and
# credentials. Mount only the three explicit runtime surfaces it needs; never copy
# secrets or ACLs into a divergent tree where rotations and grants would drift.
if ($resolvedRoot -ne $resolvedRuntimeConfigRoot) {
    $worldMarker = Join-Path $resolvedRoot '.aurora-world'
    $vaultTarget = Join-Path $resolvedRuntimeConfigRoot '.secrets'
    $vaultLink = Join-Path $resolvedRoot '.secrets'
    $aclTarget = Join-Path $resolvedRuntimeConfigRoot 'security\acl.json'
    $aclLink = Join-Path $resolvedRoot 'security\acl.json'

    foreach ($requiredRuntimePath in @($vaultTarget, $aclTarget)) {
        if (-not (Test-Path -LiteralPath $requiredRuntimePath)) {
            throw "Required host-local runtime surface is missing: $requiredRuntimePath"
        }
    }

    if (Test-Path -LiteralPath $worldMarker) {
        $declaredWorld = (Get-Content -LiteralPath $worldMarker -Raw).Trim()
        if ($declaredWorld -ne 'alpha') {
            throw "Worktree world marker must declare alpha, found '$declaredWorld': $worldMarker"
        }
    }
    elseif ($PSCmdlet.ShouldProcess($worldMarker, 'Write alpha world marker')) {
        [IO.File]::WriteAllText($worldMarker, "alpha`n", [Text.UTF8Encoding]::new($false))
    }

    function Assert-OrCreateRuntimeLink {
        param(
            [Parameter(Mandatory = $true)][string]$Link,
            [Parameter(Mandatory = $true)][string]$Target,
            [Parameter(Mandatory = $true)][ValidateSet('Junction', 'SymbolicLink')][string]$Kind
        )
        $expected = [IO.Path]::GetFullPath($Target).TrimEnd('\')
        if (Test-Path -LiteralPath $Link) {
            $item = Get-Item -LiteralPath $Link -Force
            $actualTargets = @($item.Target) | ForEach-Object {
                [IO.Path]::GetFullPath([string]$_).TrimEnd('\')
            }
            if ($item.LinkType -ne $Kind -or $expected -notin $actualTargets) {
                throw "Runtime mount exists with the wrong target/type: $Link"
            }
            return
        }
        if ($PSCmdlet.ShouldProcess($Link, "Create $Kind to $expected")) {
            if ($Kind -eq 'Junction') {
                New-Item -ItemType Junction -Path $Link -Target $expected | Out-Null
            }
            else {
                New-Item -ItemType SymbolicLink -Path $Link -Target $expected | Out-Null
            }
        }
    }

    Assert-OrCreateRuntimeLink -Link $vaultLink -Target $vaultTarget -Kind Junction
    Assert-OrCreateRuntimeLink -Link $aclLink -Target $aclTarget -Kind SymbolicLink
}

$threadPattern = '^[0-9a-f-]{36}$'
if (($GptNewThreadId -and -not $GptNewSourceThreadId) -or
    ($GptNewSourceThreadId -and -not $GptNewThreadId)) {
    throw 'GptNewThreadId and GptNewSourceThreadId must be supplied together.'
}
if (($EnableGptNewExec -or $EnableGptNewWrite) -and
    -not $GptNewThreadId) {
    throw 'Neo capability opt-ins require GptNewThreadId and GptNewSourceThreadId.'
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
    $serviceLauncher,
    '--world', 'prod', '--',
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
$gatewayArguments = ConvertTo-TaskArguments @(
    $serviceLauncher,
    '--world', 'prod', '--',
    $gatewayScript
)
$gatewayWatchdogArguments = ConvertTo-TaskArguments @(
    '/Run', '/TN', $GatewayTaskName
)
$discordArguments = ConvertTo-TaskArguments @(
    $serviceLauncher,
    '--world', 'prod', '--',
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
    # These are explicit Neo-only launcher gates. They remain off by default so
    # this preserved history fork can never acquire Sunshine's authority merely
    # by being installed beside Sunshine. The independent gpt-new ACL is the
    # second, runtime-enforced gate.
    $gptNewCapabilityArguments = @()
    if ($EnableGptNewExec) {
        $gptNewCapabilityArguments += '--allow-exec'
    }
    if ($EnableGptNewWrite) {
        $gptNewCapabilityArguments += '--allow-write'
    }
    $gptNewDiscordArguments = ConvertTo-TaskArguments @(
        $serviceLauncher,
        '--world', 'prod', '--',
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
        $gptNewCapabilityArguments,
        '--block-ms', '5000'
    )
}

$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$gatewayWatchdogTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1)
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
        Name = $GatewayTaskName
        Description = 'Single restartable Discord inbound gateway pinned to the same deployed worktree as the continuity watchers.'
        Arguments = $gatewayArguments
    },
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

# This host did not honor RestartOnFailure in a live exact-process kill drill.
# Retain one independent clock, but make it a task nudge rather than a second
# launcher: /Run starts the owned gateway task when dead and IgnoreNew absorbs
# the same request when healthy. No process-table guess and no detached orphan.
if ($GatewayWatchdogTaskName -and $GatewayWatchdogTaskName -ne $GatewayTaskName) {
    if ($PSCmdlet.ShouldProcess(
        $GatewayWatchdogTaskName,
        "Register one-minute nudge for $GatewayTaskName"
    )) {
        $gatewayWatchdogAction = New-ScheduledTaskAction `
            -Execute $resolvedSchtasks `
            -Argument $gatewayWatchdogArguments `
            -WorkingDirectory $resolvedRoot
        $gatewayWatchdogSettings = New-ScheduledTaskSettingsSet `
            -StartWhenAvailable `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
            -MultipleInstances IgnoreNew
        Register-ScheduledTask `
            -TaskName $GatewayWatchdogTaskName `
            -Action $gatewayWatchdogAction `
            -Trigger $gatewayWatchdogTrigger `
            -Settings $gatewayWatchdogSettings `
            -Principal $principal `
            -Description "Periodic idempotent nudge of $GatewayTaskName; never launches a gateway directly." `
            -Force | Out-Null
        Enable-ScheduledTask -TaskName $GatewayWatchdogTaskName | Out-Null
    }
}

[pscustomobject]@{
    GatewayTask = $GatewayTaskName
    GatewayWatchdog = $GatewayWatchdogTaskName
    GatewayWatchdogIntervalMinutes = 1
    FleetTask = $FleetTaskName
    DiscordTask = $DiscordTaskName
    ContinuityThreadId = $ThreadId
    SourceThreadId = $SourceThreadId
    StatePath = $statePath
    EventPath = $eventPath
    GptNewDiscordTask = $(if ($gptNewDiscordArguments) { $GptNewDiscordTaskName } else { $null })
    GptNewThreadId = $(if ($gptNewDiscordArguments) { $GptNewThreadId } else { $null })
    GptNewAllowExec = [bool]$EnableGptNewExec
    GptNewAllowWrite = [bool]$EnableGptNewWrite
    GptNewStatePath = $(if ($gptNewDiscordArguments) { $gptNewStatePath } else { $null })
    GptNewEventPath = $(if ($gptNewDiscordArguments) { $gptNewEventPath } else { $null })
    RuntimeConfigRoot = $resolvedRuntimeConfigRoot
    RuntimeWorld = 'prod'
    ServiceLauncher = $serviceLauncher
}
