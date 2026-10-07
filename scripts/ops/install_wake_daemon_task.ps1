<#
install_wake_daemon_task.ps1 -- make the OS scheduler own the wake-listener supervisor (2026-10-07).

DANIEL, going to work: "I want us to have multiple watchers for designated things so you dont need
to play the mental game of rearming it, every discord message from me should wake you from idle
without you having to remember to set it."

WHAT THIS DOES AND, JUST AS IMPORTANTLY, WHAT IT CANNOT DO.

It cannot wake a Claude Code session. Nothing can, from outside: the wake IS the harness's own
background-task-completion notification, so only a listener the harness itself parented can start a
turn. core/comm/wake_seat.py says it in the type system -- ORIGIN_DAEMON is "presence + consume,
never a wake", and WAKEABLE_ORIGINS is {harness, direct}. That is why the sol and gpt-new Discord
watchers can live entirely under the scheduler (codex_bifrost_wake.py calls resume_thread() and
run_turn() against the Codex app-server, so it starts the turn itself) and why copying that shape
for this seat would produce a watcher that sees everything and wakes nobody.

What it DOES own is the rung underneath: `bifrost_daemon.py --agent claude --manage-listener`,
Autopilot A1, which answers .rearm triggers by spawning listeners as managed children and sweeps
stale markers. That is the supervisor that keeps the seat PRESENT and REACHABLE between turns, which
is what stops the Discord ear reporting a cold seat, and it is what resume-on-deaf's `claude -p
--resume <sid>` leans on to re-open a session that has gone quiet.

WHY IT NEEDED A TASK. It was the only general supervisor in the fleet without one. Its sole
automatic resurrection was revive.py's daemon rung on a 5-minute cadence, so a death cost up to five
minutes of deafness and only if revive's command-line string match noticed. The instance running
when this was written (pid 55080, started 09:08:33) had been started out of band: its parent was
already gone and no revive receipt existed for it that day. It was alive by luck.

THE IDIOM IS install_mem_watch_task.ps1's, deliberately and not by coincidence -- that installer is
the only one in this repo written as documentation, and its note is the reason this file exists:
"a recorder that has to be started by hand stops at the first reboot." One task, logon trigger plus
a repeat trigger, and MultipleInstances=IgnoreNew makes the repeat a no-op while the instance lives
and a restart within the interval when it dies. No second nudge task: the EarWatchdog pattern works
(six days of gateway uptime, ~8,600 no-op nudges) but it costs a second task per watcher AND it
clobbers the target's LastTaskResult, which is why DiscordGateway permanently reports 0x800710E0 and
its real exit reason is unreadable.

  - pyw, so no console window. bifrost_daemon.py calls repair_background_stdio FIRST as of
    2026-10-07; without it this task would run forever and report nothing, which is the exact
    failure it exists to prevent, one level up. Pinned by
    tests/test_windowed_tasks_can_still_speak.py.
  - --external-supervisor: the daemon's own self-rotation is suppressed because the scheduler is
    the supervisor now. A crash then stays observable instead of being papered over in-process.
  - ExecutionTimeLimit PT0S: it is a long-running loop by design, like its five service siblings.

NOT A REPLACEMENT FOR THE STOP HOOK. scripts/hooks/claude_stop.py already blocks a turn from ending
with no listener armed -- that gate is what makes "always wakeable" structural rather than
remembered, and it is the only thing that can arm a WAKEABLE listener. This task covers the gap the
hook cannot: the hours when no session is running at all.

Idempotent: re-running replaces the definition. Runs as the logged-on user; no admin.

    powershell -ExecutionPolicy Bypass -File scripts\ops\install_wake_daemon_task.ps1

Check it afterwards:

    Get-ScheduledTaskInfo -TaskName AkashicAurora-WakeDaemon
    Get-Content "$env:LOCALAPPDATA\AkashicAurora\logs\bifrost-daemon.log" -Tail 20

Remove it:

    Unregister-ScheduledTask -TaskName AkashicAurora-WakeDaemon -Confirm:$false
#>
param(
    [string]$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$Agent = 'claude',
    [int]$HealMinutes = 5
)

$name = 'AkashicAurora-WakeDaemon'
$script = Join-Path $Repo 'scripts\bifrost_daemon.py'

if (-not (Test-Path $script)) { throw "missing $script" }

$argLine = "`"$script`" --agent $Agent --manage-listener --external-supervisor"

$action = New-ScheduledTaskAction -Execute 'pyw' -Argument $argLine -WorkingDirectory $Repo
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# The self-heal rung. IgnoreNew below makes this a no-op while the daemon lives, and a restart
# within $HealMinutes when it does not -- the whole supervision, with no probe and no second task.
$heal = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $HealMinutes)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $logon, $heal -Settings $settings `
    -Principal $principal -Force `
    -Description "Akashic Aurora: the wake-listener supervisor (bifrost_daemon --manage-listener, Autopilot A1). Answers .rearm triggers by spawning listeners as managed children and sweeps stale markers, so the seat stays present and reachable between turns. It CANNOT start a turn -- only a harness-parented listener can -- and it does not replace the stop-hook gate. Registered 2026-10-07; before that it was the only general supervisor in the fleet with no task." | Out-Null

$t = Get-ScheduledTask -TaskName $name
"registered $name"
"  action : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
"  heal   : every $($t.Triggers[1].Repetition.Interval) (empty duration = indefinitely)"
"  policy : MultipleInstances=$($t.Settings.MultipleInstances) ExecutionTimeLimit=$($t.Settings.ExecutionTimeLimit)"
"  log    : %LOCALAPPDATA%\AkashicAurora\logs\bifrost-daemon.log"
