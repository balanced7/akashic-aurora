<#
push-to-phone -- put the Termux:Widget link buttons on the phone, over the existing `ssh s24` path.

    powershell -File E:\AI-Setup\scripts\phone\push-to-phone.ps1
    powershell -File E:\AI-Setup\scripts\phone\push-to-phone.ps1 -WhatIf
    powershell -File E:\AI-Setup\scripts\phone\push-to-phone.ps1 -PanelPort 8789

WHY THIS IS A SCRIPT AND NOT A FEW LINES OF ADVICE. The buttons have to be re-pushed whenever they
change, from a worktree, by a seat that may not be able to reach the phone at all. So the push is
idempotent, it reports what it did, and it REFUSES cleanly when the phone is unreachable instead of
half-copying and leaving Daniel with two of the three buttons.

WHAT IT TOUCHES ON THE PHONE: exactly one directory, `~/.shortcuts/tasks/` -- Termux's own folder for
Termux:Widget buttons. No settings, no other package, no system path. That boundary is the whole reason
this is safe to run unattended.

WHY IT DOES NOT TRY TO WAKE THE PHONE: it cannot, and pretending otherwise would be the failure this
project exists to remove. When the phone is dark, the fix is Daniel tapping link-up ON the phone.
#>
param(
    [switch]$WhatIf,
    [int]$PanelPort = 8789,
    [string]$HostName = ''      # override: an address to try first
)

$ErrorActionPreference = 'Stop'
$Repo   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\phone-panel
$Source = Join-Path $PSScriptRoot ''
$Remote = 's24'
$Port   = 8022
$Tailnet = '100.116.105.68'
$Ssh = 'C:\Program Files\Git\usr\bin\ssh.exe'   # Windows' OpenSSH 9.5 fails KEX against the phone
$Scp = 'C:\Program Files\Git\usr\bin\scp.exe'
$SshConf = "$env:USERPROFILE\.ssh\config"
$RemoteDir = '.shortcuts/tasks'
$Files = @('link-up.sh', 'link-down.sh', 'link-status.sh')

function Say($text) { Write-Host $text }

function Test-Port([string]$Ip, [int]$P = $Port, [int]$TimeoutMs = 1200) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { return $c.ConnectAsync($Ip, $P).Wait($TimeoutMs) -and $c.Connected }
    catch { return $false } finally { $c.Dispose() }
}

function Get-LanHost {
    if (Test-Path $SshConf) {
        $m = [regex]::Match((Get-Content -Raw $SshConf), '(?ms)^Host s24\s.*?^\s*HostName\s+(\S+)')
        if ($m.Success) { return $m.Groups[1].Value }
    }
    return $null
}

# ---- 1. can the phone be reached at all? -------------------------------------------------------
$candidates = @()
if ($HostName) { $candidates += $HostName }
$lan = Get-LanHost
if ($lan) { $candidates += $lan }
$candidates += $Tailnet
$candidates = $candidates | Select-Object -Unique

$phone = $null
foreach ($ip in $candidates) {
    if (Test-Port $ip) { $phone = $ip; break }
}

if (-not $phone) {
    Say "REFUSED: the phone does not answer on :$Port at any of: $($candidates -join ', ')"
    Say ""
    Say "Nothing was copied and nothing was changed. This is the exact situation the buttons exist"
    Say "for: on the PHONE, open Termux:Widget and tap link-up (that starts sshd and raises"
    Say "Tailscale), then run this again. The PC cannot wake a phone whose tailnet is down."
    exit 2
}
Say "phone reachable at ${phone}:$Port"

if (-not (Test-Path $Ssh) -or -not (Test-Path $Scp)) {
    Say "REFUSED: Git's ssh/scp not found at $Ssh / $Scp"
    Say "Windows' own OpenSSH 9.5 fails the key exchange against this phone; install Git for Windows."
    exit 3
}

# ---- 2. what are we sending? -------------------------------------------------------------------
$paths = @()
foreach ($f in $Files) {
    $p = Join-Path $PSScriptRoot $f
    if (-not (Test-Path $p)) { Say "REFUSED: $f is missing from $PSScriptRoot"; exit 4 }
    $paths += $p
}

if ($WhatIf) {
    Say "WOULD copy to ${Remote}:$RemoteDir/ :"
    foreach ($p in $paths) { Say ("  {0,7:N0} bytes  {1}" -f (Get-Item $p).Length, (Split-Path -Leaf $p)) }
    Say "WOULD then: chmod +x on each, and list the folder back"
    Say "(no remote change was made: -WhatIf)"
    exit 0
}

# ---- 3. copy, mark executable, read it back ----------------------------------------------------
$mkdir = & $Ssh -o BatchMode=yes -o ConnectTimeout=8 -o "HostName=$phone" $Remote "mkdir -p ~/$RemoteDir && echo ok" 2>&1
if ($LASTEXITCODE -ne 0) {
    Say "REFUSED: ssh reached the port but not a shell: $mkdir"
    exit 5
}

foreach ($p in $paths) {
    $name = Split-Path -Leaf $p
    & $Scp -q -o BatchMode=yes -o ConnectTimeout=8 -o "HostName=$phone" $p "${Remote}:$RemoteDir/$name" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Say "FAILED to copy $name"; exit 6 }
    Say "copied $name"
}

$chmod = & $Ssh -o BatchMode=yes -o "HostName=$phone" $Remote "chmod +x ~/$RemoteDir/link-*.sh && ls -l ~/$RemoteDir/link-*.sh" 2>&1
Say ""
Say "now on the phone:"
$chmod | ForEach-Object { Say "  $_" }
Say ""
Say "Next, on the phone: long-press the home screen > Widgets > Termux:Widget > drag a Task widget"
Say "out and choose link-up / link-down / link-status."
Say "The panel itself is at 127.0.0.1:$PanelPort once the PhoneLink watcher forwards it"
Say "(add -R ${PanelPort}:127.0.0.1:${PanelPort} to phonelink.ps1 watch -- see docs/PHONE-PANEL.md)."
exit 0
