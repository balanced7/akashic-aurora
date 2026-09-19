# launch_rill.ps1 -- bring up Rill (the DSH seat, agent id dsh_agent) in the browser UI, with the
# seat's identity BOUND AT INGRESS instead of inherited from whatever shell happened to be open.
#
# WHY THIS EXISTS, in two parts.
# (1) The ergonomic half: Daniel asked (2026-09-17) for a launcher so he can talk to Rill without
#     asking another seat for help.
# (2) The load-bearing half: on 2026-09-17 the LIVE dsh process was carrying ANOTHER RESIDENT'S
#     identity triple -- AKASHIC_HARNESS=codex-desktop, AKASHIC_CALLSIGN_HINT=Sunshine,
#     AKASHIC_IDENTITY_POINTER=research/in-flight/sol-sunshine-identity-history-2026-08-26.md --
#     because it had been started from a codex-desktop shell. AKASHIC_AGENT_ID was right, so the
#     boot whisper still resolved "YOU ARE: Rill"; every OTHER consumer of the environment was
#     reading a different resident's name and a different resident's history. That is the identity
#     law's own failure mode: the wrong name is the one that was ALREADY IN THE ENVIRONMENT.
#     A launcher IS the ingress, so this is the right place to fix it -- by binding and clearing
#     explicitly, never by inferring.
#
# THE RULE THIS SCRIPT FOLLOWS (fail open on the work path, fail LOUD at the boundary): it never
# blocks a session for a cosmetic reason, and it never reports success it did not observe. If the
# seat does not answer on its port, this exits non-zero and says so.
#
# Usage:
#   .\scripts\local\launch_rill.ps1                bring the seat up, or open the one already up
#   .\scripts\local\launch_rill.ps1 -New           force a FRESH seat on the next free port
#   .\scripts\local\launch_rill.ps1 -Foreground    run in this window (closing it stops the seat)
#   .\scripts\local\launch_rill.ps1 -Port 3090     a specific port
#   .\scripts\local\launch_rill.ps1 -Check         report identity + plugin + port, start nothing

[CmdletBinding()]
param(
    [int]$Port = 3080,
    [switch]$New,
    [switch]$Foreground,
    [switch]$Check,
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'

# Repo root DERIVED from this script's own location -- never a hardcoded absolute path. The older
# launchers in this directory pinned one machine's E:\AI-Setup and could not run anywhere else.
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }

function Write-Head([string]$text) { Write-Host $text -ForegroundColor Cyan }
function Write-Warn([string]$text) { Write-Host "[launch_rill] WARNING: $text" -ForegroundColor Yellow }
function Write-Bad([string]$text)  { Write-Host "[launch_rill] $text" -ForegroundColor Red }

function Test-DshWeb {
    param([int]$P)
    # A live DSH web seat answers 200 at / with the client module loader in the body. 404s on
    # /api/* are normal -- there is no health endpoint -- so the page itself is the fingerprint.
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$P/" -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200 -and $r.Content -match '__ModuleLoader__')
    } catch { return $false }
}

function Test-PortBusy {
    param([int]$P)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $wait = $client.BeginConnect('127.0.0.1', $P, $null, $null)
        $done = $wait.AsyncWaitHandle.WaitOne(300)
        $busy = ($done -and $client.Connected)
        $client.Close()
        return $busy
    } catch { return $false }
}

function Get-NewestWrite {
    param([string]$Dir)
    if (-not (Test-Path -LiteralPath $Dir)) { return $null }
    $files = Get-ChildItem -LiteralPath $Dir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '__pycache__|node_modules|\.git' } |
        Sort-Object LastWriteTime -Descending
    if ($files.Count -gt 0) { return $files[0].LastWriteTime }
    return $null
}

# --------------------------------------------------------------- 1. identity, bound at ingress
# Variables belonging to ANOTHER harness (codex-desktop / sol). CLEARED, not overwritten: they
# describe a different resident, and leaving them set means anything that reads the environment to
# answer "who is this?" answers with the wrong name.
$foreign = @('AKASHIC_CALLSIGN_HINT', 'AKASHIC_CALLSIGN_STATUS',
             'AKASHIC_IDENTITY_POINTER', 'AKASHIC_IDENTITY_POINTER_SUBJECT')
# PER-SESSION variables, cleared for a different reason: they describe THIS session, so a seat
# launched from inside one would inherit its identity and believe it is the same session -- sharing
# a recall key and pointing at the wrong port. A seat must mint its own.
$perSession = @('DSH_SESSION_ID', 'DSH_SESSION_JSONL', 'DSH_WEB_URL', 'DSH_SHELL')
$cleared = @()
foreach ($name in ($foreign + $perSession)) {
    if (Test-Path "env:$name") {
        $was = (Get-Item "env:$name").Value
        Remove-Item "env:$name"
        $kind = if ($foreign -contains $name) { 'another resident' } else { 'this session' }
        $cleared += "$name=$was   [$kind]"
    }
}
$env:AKASHIC_AGENT_ID = 'dsh_agent'
$env:AKASHIC_HARNESS = 'deepseek-harness'
$env:AKASHIC_REPO = $Root
# Interactive seats must consume the WORK lane or their cursor and their watcher disagree (a known
# wake loop). Set here so a freshly launched Rill starts on the right lane.
$env:BIFROST_CONSUME_LANE = 'work'

Write-Head "[launch_rill] identity bound at ingress"
Write-Host "  AKASHIC_AGENT_ID  = $env:AKASHIC_AGENT_ID     (Rill)"
Write-Host "  AKASHIC_HARNESS   = $env:AKASHIC_HARNESS"
Write-Host "  AKASHIC_REPO      = $env:AKASHIC_REPO"
Write-Host "  BIFROST_CONSUME_LANE = $env:BIFROST_CONSUME_LANE"
if ($cleared.Count -gt 0) {
    Write-Host "  cleared (variables that must NOT be inherited):" -ForegroundColor Yellow
    foreach ($c in $cleared) { Write-Host "    $c" -ForegroundColor Yellow }
} else {
    Write-Host "  cleared: (none present -- nothing foreign or per-session was inherited)"
}

# ------------------------------------------------------- 2. the DSH env layer ($DSH_HOME\.env)
# The layer is materialized into process.env at DSH launch, so it can OVERRIDE what is bound above.
# Read it and report a disagreement LOUDLY rather than letting it win silently.
$envFile = Join-Path $DshHome '.env'
$layer = @{}
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { $layer[$Matches[1]] = $Matches[2].Trim() }
    }
} else {
    Write-Bad "no env layer at $envFile -- children of the seat will NOT inherit the Akashic stamp."
    Write-Host "  fix: py scripts\install_dsh_plugin.py"
}
$layerOk = ($layer['AKASHIC_AGENT_ID'] -eq 'dsh_agent')
if ($layer.Count -gt 0 -and -not $layerOk) {
    Write-Warn "the env layer does not stamp AKASHIC_AGENT_ID=dsh_agent (got '$($layer['AKASHIC_AGENT_ID'])'): the seat may attribute to the wrong name."
}
if ($layer['AKASHIC_REPO'] -and $layer['AKASHIC_REPO'] -ne $Root) {
    Write-Warn "the env layer points AKASHIC_REPO at $($layer['AKASHIC_REPO']) but this launcher was started from $Root -- the LAYER wins inside the seat. Align them, or the seat works in the other tree."
}

# ------------------------------------------------------------- 3. the plugin (memory + bus door)
# A DSH seat whose plugin is not mounted looks exactly like Rill and remembers nothing -- an
# absence that renders as normal, which is the failure this whole house keeps paying for. So it is
# checked, and a stale deploy is reported as a version skew at the boundary.
$deployed = Join-Path $DshHome 'profiles\web\plugins\dsh-akashic-recall'
$inTree = Join-Path $Root 'agent\harness\dsh_plugin'
$pluginOk = Test-Path -LiteralPath $deployed
Write-Head "[launch_rill] plugin (recall + bus + MCP door)"
if ($pluginOk) {
    Write-Host "  mounted: $deployed"
    $d = Get-NewestWrite $deployed
    $s = Get-NewestWrite $inTree
    if ($d -and $s -and $s -gt $d) {
        Write-Warn "the in-tree plugin is NEWER than the deployed copy ($($s.ToString('u')) > $($d.ToString('u'))): the seat would run stale code."
        Write-Host "  fix: py scripts\install_dsh_plugin.py"
    }
} else {
    Write-Bad "NOT mounted for the web profile -- a session started now looks like Rill and has no recall, no bus listeners and no MCP door."
    Write-Host "  fix: py scripts\install_dsh_plugin.py"
    Write-Host "  (starting anyway: fail-open on the work path. The warning above is the loud half.)"
}

# ------------------------------------------------------------------- 4. -Check (starts nothing)
if ($Check) {
    Write-Head "[launch_rill] -Check: nothing started, nothing opened."
    if (Test-DshWeb -P $Port) {
        Write-Host "  port $Port : a DSH web seat is ALREADY up at http://127.0.0.1:$Port"
    } elseif (Test-PortBusy -P $Port) {
        Write-Host "  port $Port : busy with something that is NOT a DSH seat (a launch moves on)"
    } else {
        Write-Host "  port $Port : free"
    }
    if ($layerOk) { Write-Host "  env layer : OK (stamps dsh_agent)" }
    else { Write-Host "  env layer : NEEDS ATTENTION (see above)" }
    if ($pluginOk) { Write-Host "  plugin    : OK (deployed for the web profile)" }
    else { Write-Host "  plugin    : MISSING -- run scripts\install_dsh_plugin.py" }
    exit 0
}

# ------------------------------------------------------------------------- 5. which port, and why
$target = $Port
$alreadyUp = Test-DshWeb -P $Port
if ($alreadyUp -and -not $New) {
    $url = "http://127.0.0.1:$Port"
    Write-Head "[launch_rill] a DSH web seat is ALREADY listening on $url"
    Write-Host "  opening it (use -New to start a fresh session on another port instead)."
    Start-Process $url | Out-Null
    exit 0
}
if ($alreadyUp -and $New) {
    Write-Host "[launch_rill] -New requested: leaving the seat on $Port alone."
}
if ((Test-PortBusy -P $Port)) {
    $found = $false
    for ($p = $Port + 1; $p -le $Port + 20; $p++) {
        if (-not (Test-PortBusy -P $p)) { $target = $p; $found = $true; break }
    }
    if (-not $found) { Write-Bad "no free port in $Port..$($Port + 20)"; exit 2 }
    Write-Warn "port $Port is taken by something that is not a DSH seat -- using $target instead."
}

# ------------------------------------------------------------------------------------ 6. launch
$dshCmd = Get-Command dsh -ErrorAction SilentlyContinue
if (-not $dshCmd) {
    Write-Bad "'dsh' is not on PATH -- cannot start the seat."
    Write-Host "  expected: the npm global shim ($env:APPDATA\npm\dsh.cmd)"
    exit 2
}
# Prefer node + the package entry over the .cmd shim: node.exe takes the redirects cleanly and gives
# us a pid, and the shim would put a cmd.exe in the middle of the process tree for nothing.
$nodeExe = $null
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$binJs = Join-Path (Split-Path $dshCmd.Source -Parent) 'node_modules\@deepseek-ai\dsh\lib\bin.js'
if ($nodeCmd -and (Test-Path -LiteralPath $binJs)) { $nodeExe = $nodeCmd.Source }

$url = "http://127.0.0.1:$target"
if ($Foreground) {
    Write-Head "[launch_rill] foreground session on $url -- closing this window stops the seat."
    if ($nodeExe) { & $nodeExe $binJs web --port $target } else { & $dshCmd.Source web --port $target }
    exit $LASTEXITCODE
}

# Output goes to a FILE, never down an inherited pipe. Learned the hard way in this script's own
# first drill: the seat inherited the launcher's stdout pipe, and when that pipe went away the seat
# died with it -- the RB-28 trap ("run it in the background and tail its output FILE instead").
$logDir = Join-Path $Root 'state\logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logDir "dsh-seat-$target-$stamp.log"

$dshArgs = @('web', '--port', "$target")
if ($NoOpen) { $dshArgs += '--no-open' }

Write-Head "[launch_rill] starting: dsh web --port $target   (working dir $Root)"
if ($nodeExe) {
    $proc = Start-Process -FilePath $nodeExe -ArgumentList (@($binJs) + $dshArgs) -WorkingDirectory $Root `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
} else {
    $proc = Start-Process -FilePath $dshCmd.Source -ArgumentList $dshArgs -WorkingDirectory $Root `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
}
Write-Host "  pid $($proc.Id)   log: $log"

# A launcher that reports success it did not observe is the anti-pattern this seat spent the night
# writing gates against, so: poll until the seat ANSWERS, then say what was seen.
$up = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    if ($proc.HasExited) { break }
    if (Test-DshWeb -P $target) { $up = $true; break }
}
if (-not $up) {
    Write-Bad "the seat did NOT answer on $url after 30s, so nothing is claimed about it."
    if ($proc.HasExited) { Write-Host "  the process exited (code $($proc.ExitCode))." }
    foreach ($f in @($log, "$log.err")) {
        if (Test-Path -LiteralPath $f) {
            $tail = Get-Content -LiteralPath $f -Tail 12 -ErrorAction SilentlyContinue
            if ($tail) { Write-Host "  --- $f (last lines) ---" -ForegroundColor DarkGray; $tail | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray } }
        }
    }
    exit 3
}
Write-Head "[launch_rill] up: $url  (answered the UI fingerprint in under 30s)"
Write-Host "  pid $($proc.Id) -- stop it with: Stop-Process -Id $($proc.Id)"
Write-Host "  log: $log"
Write-Host "  first line of its boot whisper should read 'YOU ARE: Rill'. If it names anyone else,"
Write-Host "  that is an identity fault worth reporting, not a cosmetic one."
exit 0
