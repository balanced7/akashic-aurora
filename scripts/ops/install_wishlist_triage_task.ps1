<#
install_wishlist_triage_task.ps1 -- make the OS scheduler own the wishlist cadence (2026-10-07).

WHY. Daniel, 2026-10-07, verbatim: "I need to be better about checking those and getting them built
more frequently with a more regular cadance." The answer he accepted was that the cadence should
ARRIVE rather than be remembered -- for the same reason the mem_watch note gives about itself,
"a recorder that has to be started by hand stops at the first reboot."

The asymmetry this closes is real and measured: FILING a wish is one command and works (187 open as
of tonight, five filed in the hour this was written). CURATING one was a doc edit nobody owned, so
it starved. That is `zero_is_not_no_silence_is_not_a_verdict` -- an unowned manual step standing
next to a frictionless one always loses.

WHAT IT RUNS. scripts\ops\wishlist_triage_task.py, which PROPOSES and never closes anything. It
holds no write door to the wishlist at all, by construction. Three house rules demand that (the
charter's "never delete -- declined wishes teach too", PROPOSE-NEVER-AUTO-RETIRE, and nursery-first),
and so does plain honesty: whether a wish is already satisfied cannot be decided by a parser, only
by someone reading the wish against the code. Its two landing buckets are labelled as QUESTIONS in
the output for that reason.

  - Weekly, Monday 09:30. The report is pushed to Discord, so the hour matters less than the
    arrival; Monday is simply the conventional start-of-week review slot. Change `-At` to taste.
  - NO logon trigger, unlike its daily siblings. A weekly report that also fires on every logon is
    not a cadence, it is noise, and noise is how a surface earns being ignored.
  - -StartWhenAvailable: if the machine is off on Monday morning the pass runs when it next can.
    A missed week would silently become the new normal, which is the rot this task exists against.
  - pyw (py.ini pins 3.11) so no console window appears -- and that is WHY the action is this
    wrapper rather than a bare CLI verb. Under Task Scheduler sys.stdout is None, print() succeeds
    and discards, so the entire report would go nowhere every week while the task reported success.
    The wrapper calls repair_background_stdio FIRST and writes a dated receipt.
  - ExecutionTimeLimit 30 min: a live pass measured ~3 s with 16 git checks, so half an hour means
    "something is wrong", not "this is a long job".

NOT INSTALLED AUTOMATICALLY, same as its siblings -- a recurring task is persistent machine
configuration and belongs to the operator:

    powershell -ExecutionPolicy Bypass -File scripts\ops\install_wishlist_triage_task.ps1

Idempotent: re-running replaces the definition. Runs as the logged-on user; no admin.

Check it:
    Get-ScheduledTaskInfo -TaskName AkashicAurora-WishlistTriage-Weekly
    Get-Content state\wishlist\triage-receipts\*.jsonl -Tail 1
    Get-Content state\wishlist\latest-triage.md

Run it by hand (prints, writes nothing, posts nothing):
    py scripts\ops\wishlist_triage_task.py --dry-run

REMOVE IT -- one line, no side effects left behind:
    Unregister-ScheduledTask -TaskName AkashicAurora-WishlistTriage-Weekly -Confirm:$false
#>
param([string]$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path)

$name = 'AkashicAurora-WishlistTriage-Weekly'
$script = Join-Path $Repo 'scripts\ops\wishlist_triage_task.py'

if (-not (Test-Path $script)) { throw "missing $script" }

$action = New-ScheduledTaskAction -Execute 'pyw' -Argument "`"$script`"" -WorkingDirectory $Repo
$weekly = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:30
# IgnoreNew: a second pass would post Daniel a duplicate report, which is worse than a missed one.
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $weekly -Settings $settings `
    -Principal $principal -Force `
    -Description 'Akashic Aurora: the wishlist cadence. Weekly, ranks open wishes into fresh / landing-missing / possibly-already-built / starving, posts the short form to Daniel and writes a dated receipt to state\wishlist\triage-receipts. PROPOSES ONLY -- it holds no write door to WISHLIST.md and closes nothing. Built 2026-10-07 for his ask: "a more regular cadance".' | Out-Null

$t = Get-ScheduledTask -TaskName $name
"registered $name"
"  action  : $($t.Actions[0].Execute) $($t.Actions[0].Arguments)"
"  weekly  : $($t.Triggers[0].StartBoundary)  (Monday)"
"  policy  : MultipleInstances=$($t.Settings.MultipleInstances) ExecutionTimeLimit=$($t.Settings.ExecutionTimeLimit)"
"  receipts: state\wishlist\triage-receipts\<YYYY-MM>.jsonl"
"  report  : state\wishlist\latest-triage.md"
"  remove  : Unregister-ScheduledTask -TaskName $name -Confirm:`$false"
