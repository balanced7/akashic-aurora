<#
install_mem_watch_task.ps1 -- make the OS scheduler own the memory black box (2026-09-24).

mem_watch was launched by hand. Its last sample landed at 2026-09-07 17:37, the minute of
a reboot, and nothing started it again for 17 days: through the 09-11 kernel-pool outage,
the 09-16 hard reset and the 09-24 freeze. A recorder that has to be started by hand
stops at the first reboot. This registers it beside its AkashicAurora-* siblings:

  - trigger at logon, plus a 15-minute self-heal trigger. MultipleInstances=IgnoreNew
    makes the self-heal a no-op while the recorder lives and a restart within 15 minutes
    if it dies;
  - pyw (py.ini pins 3.11), so no console window;
  - no execution time limit, because the recorder is a long-running loop by design.

Idempotent: re-running replaces the definition. Runs as the logged-on user; no admin.
    powershell -ExecutionPolicy Bypass -File scripts\ops\install_mem_watch_task.ps1
#>
param([string]$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path)

$name = 'AkashicAurora-MemWatch'
$script = Join-Path $Repo 'scripts\ops\mem_watch.py'
$argLine = "`"$script`" --interval 300 --pressure-interval 30"

$action = New-ScheduledTaskAction -Execute 'pyw' -Argument $argLine -WorkingDirectory $Repo
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$heal = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 15)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $logon, $heal -Settings $settings `
    -Principal $principal -Force `
    -Description 'Akashic Aurora memory black box: commit, kernel pools, per-process private bytes and handles to state\mem-watch (scripts\ops\mem_watch.py).' | Out-Null

$t = Get-ScheduledTask -TaskName $name
"registered $name"
"  action : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
"  heal   : every $($t.Triggers[1].Repetition.Interval), duration '$($t.Triggers[1].Repetition.Duration)' (empty = indefinitely)"
"  policy : MultipleInstances=$($t.Settings.MultipleInstances) ExecutionTimeLimit=$($t.Settings.ExecutionTimeLimit)"
