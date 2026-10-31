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
    [string]$HostName = '',     # override: an address to try first
    [string]$Tailnet = ''       # override: the phone's tailnet address (see Get-PhoneTailnet)
)

$ErrorActionPreference = 'Stop'
$Repo   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\phone-panel
$Source = Join-Path $PSScriptRoot ''
$Remote = 's24'
$Port   = 8022
$Ssh = 'C:\Program Files\Git\usr\bin\ssh.exe'   # Windows' OpenSSH 9.5 fails KEX against the phone
$Scp = 'C:\Program Files\Git\usr\bin\scp.exe'
$SshConf = "$env:USERPROFILE\.ssh\config"
$RemoteDir = '.shortcuts/tasks'
$Files = @('link-up.sh', 'link-down.sh', 'link-status.sh')

function Say($text) { Write-Host $text }

# ---- the phone's tailnet address: THIS MACHINE's value, never the repo's -----------------------
# A tailnet address is a routable address for one machine, so it belongs to the private profile
# (akashic-local/profile/reachability.json) and NOT in a public repo -- this script used to carry it
# as a literal, which is exactly the leak the pre-push scan exists to catch. Same three sources as
# core/local.py: the flag, $AKASHIC_PHONE_TAILNET, then the profile found via $AKASHIC_LOCAL or a
# marker walk. Absent is NOT fatal here: the phone may still answer on the LAN (the `s24` entry in
# ~/.ssh/config), and a REFUSAL at the end will say which addresses were tried.
function Get-LocalProfileDir {
    if ($env:AKASHIC_LOCAL) {
        if (Test-Path (Join-Path $env:AKASHIC_LOCAL 'profile') -PathType Container) {
            return (Join-Path $env:AKASHIC_LOCAL 'profile')
        }
        if (Test-Path (Join-Path $env:AKASHIC_LOCAL '.akashic-local')) {
            return (Join-Path $env:AKASHIC_LOCAL 'profile')
        }
        return $null   # a set-but-unusable variable is a misconfiguration, not an absent machine
    }
    $probe = $Repo
    while ($probe) {
        $cands = @()
        $sib = Join-Path $probe 'akashic-local'
        if (Test-Path $sib -PathType Container) { $cands += $sib }
        foreach ($kid in (Get-ChildItem -Path $probe -Directory -ErrorAction SilentlyContinue)) {
            $deep = Join-Path $kid.FullName 'akashic-local'
            if (Test-Path $deep -PathType Container) { $cands += $deep }
        }
        foreach ($c in $cands) {
            if (Test-Path (Join-Path $c '.akashic-local')) { return (Join-Path $c 'profile') }
        }
        $parent = Split-Path -Parent $probe
        if (-not $parent -or $parent -eq $probe) { break }
        $probe = $parent
    }
    return $null
}

function Get-PhoneTailnet {
    if ($env:AKASHIC_PHONE_TAILNET) { return $env:AKASHIC_PHONE_TAILNET }
    $dir = Get-LocalProfileDir
    if (-not $dir) {
        Say "note: no private profile found (no `$AKASHIC_LOCAL, no '.akashic-local' marker in an"
        Say "      akashic-local directory at or one level under a parent of $Repo), so the tailnet"
        Say "      address is UNKNOWN and only the LAN candidates below will be tried."
        return ''
    }
    $f = Join-Path $dir 'reachability.json'
    if (-not (Test-Path $f)) { return '' }
    try { $doc = Get-Content -Raw -Path $f | ConvertFrom-Json } catch {
        Say "note: the profile's ${f} is not readable JSON; the tailnet address is UNKNOWN"
        return ''
    }
    if ($null -eq $doc.version) {
        Say "note: the profile's ${f} carries no 'version', so it was NOT used (same refusal as"
        Say "      core/local.py: an unversioned overlay is a shape we have not agreed to read)."
        return ''
    }
    $host_ = $doc.phone.tailnet_host
    if ($host_) { return [string]$host_ }
    return ''
}

if (-not $Tailnet) { $Tailnet = Get-PhoneTailnet }

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
if ($Tailnet) { $candidates += $Tailnet }
$candidates = $candidates | Select-Object -Unique

if (-not $candidates) {
    Say "REFUSED: there is no address to try. The LAN entry for 's24' was not found in"
    Say "         $SshConf, and no tailnet address was supplied (flag -Tailnet,"
    Say "         `$AKASHIC_PHONE_TAILNET, or phone.tailnet_host in the private profile)."
    Say "         Nothing was copied; this is UNKNOWN, not 'the phone is down'."
    exit 2
}

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
