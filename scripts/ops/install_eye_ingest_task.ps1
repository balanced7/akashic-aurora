<#
install_eye_ingest_task.ps1 -- make the OS scheduler own THE EYE's ingest (2026-10-07).

WHY. The eye is the only searchable record of 1,604 transcripts and 56,386 events, and for most of
that corpus it is the only copy that still exists -- 138 transcript files remain on the harness disk
against 1,673 sessions the index holds. Nothing scheduled its ingest. The first run on the night of
2026-10-07 took in 3,717 new events: about six days of work that had happened and was not findable.

AkashicAurora-TranscriptArchive-Daily has run every day and succeeded the whole time, so the BYTES
were preserved throughout. Only the findability rotted. Preserving a corpus you cannot search is a
backup, not a library.

This registers the ingest beside its AkashicAurora-* siblings, following the mem_watch note's own
reasoning -- "a recorder that has to be started by hand stops at the first reboot":

  - daily at 12:20, ten minutes after EphemeralArchive and twenty after TranscriptArchive, so the
    index is built over an archive that has already settled;
  - plus AtLogOn, because the useful property is "fresh when he sits down", and a reboot is exactly
    when a hand-run ingest would have been skipped;
  - pyw (py.ini pins 3.11) so no console window appears -- which is WHY the action is the wrapper
    scripts\ops\eye_ingest_task.py and not `agent_cli.py eye ingest`. Under Task Scheduler
    sys.stdout is None, print() silently discards, and the coverage report -- the only thing that
    would say the index had stopped being whole -- would go nowhere every day. The wrapper calls
    repair_background_stdio first and writes a dated receipt to state\eye\ingest-receipts\.
  - ExecutionTimeLimit 1 hour: an incremental pass measured 39-85 s, so an hour means "something is
    wrong", not "this is a long job".

NOT INSTALLED AUTOMATICALLY. Registering a recurring task is persistent machine configuration, so it
is the operator's call and not something a build step does on its own. Run it when you want it:

    powershell -ExecutionPolicy Bypass -File scripts\ops\install_eye_ingest_task.ps1

Idempotent: re-running replaces the definition. Runs as the logged-on user; no admin.
To check it afterwards:

    Get-ScheduledTaskInfo -TaskName AkashicAurora-EyeIngest-Daily
    Get-Content state\eye\ingest-receipts\*.jsonl -Tail 1

To remove it:

    Unregister-ScheduledTask -TaskName AkashicAurora-EyeIngest-Daily -Confirm:$false
#>
param([string]$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path)

$name = 'AkashicAurora-EyeIngest-Daily'
$script = Join-Path $Repo 'scripts\ops\eye_ingest_task.py'

if (-not (Test-Path $script)) { throw "missing $script" }

$action = New-ScheduledTaskAction -Execute 'pyw' -Argument "`"$script`"" -WorkingDirectory $Repo
$daily = New-ScheduledTaskTrigger -Daily -At 12:20
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# IgnoreNew: the logon trigger must never start a second pass while the daily one is mid-run. The
# ingest writes to a WAL sqlite db, so two passes are survivable but pointless.
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $daily, $logon -Settings $settings `
    -Principal $principal -Force `
    -Description 'Akashic Aurora: keep THE EYE current. Indexes every session JSONL incrementally and writes a dated coverage receipt to state\eye\ingest-receipts (scripts\ops\eye_ingest_task.py). Nothing scheduled this before 2026-10-07 and the index had gone 3,717 events stale.' | Out-Null

$t = Get-ScheduledTask -TaskName $name
"registered $name"
"  action : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
"  daily  : $($t.Triggers[0].StartBoundary)"
"  policy : MultipleInstances=$($t.Settings.MultipleInstances) ExecutionTimeLimit=$($t.Settings.ExecutionTimeLimit)"
"  receipts: state\eye\ingest-receipts\<YYYY-MM>.jsonl"
