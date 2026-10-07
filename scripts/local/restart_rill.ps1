# restart_rill.ps1 -- bounce the DSH web seat (dsh_agent / Rill) onto the CORRECT world.
#
# WHY: on 2026-09-25 Rill's akashic_* MCP door + presence beat were answering from Redis
# 16381 (ALPHA) while the fleet reads 16379 (prod). Root cause (traced to source):
#   - $DSH_HOME\.env correctly stamps AKASHIC_REPO=E:\AI-Setup (prod).
#   - BUT the RUNNING `node bin.js web --port 3080` process had INHERITED a stale
#     AKASHIC_REPO=...\worktrees\reconcile-20260923 (an alpha worktree) from its now-dead
#     launcher. loadLayeredEnv does not overwrite an already-set process.env var, so the
#     stale value won. The plugin then spawned `py ai_setup_mcp.py` with cwd = that alpha
#     worktree, and its .aurora-world marker said alpha -> 16381.
#   - Fix = kill the stale host, relaunch via launch_rill.ps1 (which binds AKASHIC_REPO
#     at ingress AND warns on any layer mismatch).
#
# SAFETY: launch_rill.ps1 does the port dance, the verify-and-fail-loud loop, and writes
# its own log. This wrapper only (a) finds the RIGHT host process, (b) kills it, (c) waits
# for the port to free, (d) hands off to launch_rill.ps1, (e) tees everything to a log.
# Use -Check for a read-only dry run that reports the pid it WOULD kill and nothing else.

[CmdletBinding()]
param(
    [int]$Port = 3080,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$logDir = Join-Path $Root 'state\logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logDir "restart-rill-$stamp.log"

function Log([string]$t) { Write-Host $t; Add-Content -LiteralPath $log -Value $t }

# Find the dsh web HOST: a node.exe whose command line carries the package bin.js AND
# 'web' AND the target port. Exclude our own process id. Match on the exact bin.js path,
# NOT a bare substring (learned: a substring filter once matched and killed a claude.exe
# desktop helper).
$hosts = Get-CimInstance Win32_Process -Filter "name='node.exe'" |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'dsh[\\/]lib[\\/]bin\.js' -and $_.CommandLine -match '\bweb\b' -and $_.CommandLine -match "--port\s+$Port\b" }

if (-not $hosts) {
    if ($Check) { Log "[restart_rill -Check] no dsh web host found for port $Port (nothing would be killed)." ; exit 0 }
    Log "[restart_rill] no dsh web host found for port $Port -- nothing to kill; handing off to launch_rill."
    & (Join-Path $Root 'scripts\local\launch_rill.ps1') -Port $Port
    exit $LASTEXITCODE
}

$pidList = @($hosts | ForEach-Object { $_.ProcessId })
if ($Check) {
    foreach ($h in $hosts) {
        $c = if ($h.CommandLine.Length -gt 140) { $h.CommandLine.Substring(0,140) + '...' } else { $h.CommandLine }
        Log "[restart_rill -Check] WOULD kill node.exe pid $($h.ProcessId) :: $c"
    }
    Log "[restart_rill -Check] read-only; nothing killed."
    exit 0
}

foreach ($id in $pidList) {
    Log "[restart_rill] stopping stale dsh web host pid $id"
    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
}

# Wait for the port to actually free (the old process may hold it briefly).
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    $busy = $false
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $w = $c.BeginConnect('127.0.0.1', $Port, $null, $null)
        $done = $w.AsyncWaitHandle.WaitOne(150)
        $busy = ($done -and $c.Connected)
        $c.Close()
    } catch { $busy = $false }
    if (-not $busy) { break }
}
Log "[restart_rill] port $Port free after killing stale host"

# Hand off. launch_rill.ps1 binds identity at ingress, re-checks the env layer, and fails
# LOUD (non-zero) if the seat does not answer -- we inherit that verdict.
& (Join-Path $Root 'scripts\local\launch_rill.ps1') -Port $Port
exit $LASTEXITCODE
