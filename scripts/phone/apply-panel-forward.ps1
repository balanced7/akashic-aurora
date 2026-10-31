<#
apply-panel-forward -- add ONE `-R` to the PhoneLink watcher, so the phone can reach the control panel.

    powershell -File E:\AI-Setup\scripts\phone\apply-panel-forward.ps1
    powershell -File E:\AI-Setup\scripts\phone\apply-panel-forward.ps1 -WhatIf
    powershell -File E:\AI-Setup\scripts\phone\apply-panel-forward.ps1 -Path <a copy>   # prove it

WHY THIS IS A SCRIPT AND NOT AN ALREADY-MADE EDIT. `phonelink.ps1` lives in the private akashic-local repo, OUTSIDE
this repo, so a commit cannot carry the change and a seat whose file access is confined to the repo
cannot make it. The honest options were (a) report that the forward is missing, or (b) ship the exact
transformation as something that can be RUN and PROVEN. This is (b).

WHAT IT ADDS, exactly two lines and one array element:

  $PanelPort = 8789                             (beside $Bifrost / $GamePort)
  '-R', "${PanelPort}:127.0.0.1:${PanelPort}",   (before $Remote, beside the two existing forwards)

IT CANNOT WRITE A BROKEN WATCHER. Before anything is written, the RESULT is parsed with PowerShell's own
parser; a single syntax error and it refuses, leaving the file untouched. That gate earned its keep on
this script's first run: an earlier draft mangled a quote and a comment, and the parse check is what
caught it (the drill in docs/PHONE-PANEL.md runs the applier against a COPY first for the same reason).

IT DOES NOT RESTART THE WATCHER, on purpose. The watcher IS the tunnel the phone arrives through:
restarting it from here would cut the phone off, and the running process is a scheduled task, not this
script's to bounce. The change takes effect the next time the watcher starts.

If the watcher's file is not the shape this was written for, it REFUSES and says what it looked for. It
never "fixes" a file it did not recognise.
#>
param(
    [string]$Path = '',
    [int]$PanelPort = 8789,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
function Say($text) { Write-Host $text }

$Q = [char]39                      # a single quote, built explicitly: no escaping to get wrong

# No -Path: the watcher lives in this machine's PRIVATE repo (akashic-local/phonelink). Ask the one loader where
# that is (core/local.py: AKASHIC_LOCAL, else the marker walk) instead of writing this disk's layout here.
if (-not $Path) {
    Push-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
    $private = & py -c "from core import local; p = local.profile_dir(); print(p.parent if p else '')" 2>$null
    Pop-Location
    if (-not $private) {
        Say "REFUSED: no private akashic-local repo on this machine, so no watcher to edit."
        Say "Pass -Path <phonelink.ps1>. Nothing was changed."
        exit 2
    }
    $Path = Join-Path $private 'phonelink\phonelink.ps1'
}

if (-not (Test-Path -LiteralPath $Path)) {
    Say "REFUSED: no watcher at $Path"
    Say "Pass -Path if PhoneLink lives elsewhere. Nothing was changed."
    exit 2
}
$full = [IO.Path]::GetFullPath($Path)
$text = [IO.File]::ReadAllText($full)

# ---- already done? -----------------------------------------------------------------------------
if ($text -match '\$PanelPort\s*=') {
    Say "ALREADY APPLIED: $Path already declares `$PanelPort."
    ($text -split "`r?`n") | Select-String -Pattern '\$PanelPort' |
        ForEach-Object { Say ("  " + $_.Line.Trim()) }
    Say "Nothing was changed."
    exit 0
}

# ---- lines, not substrings ---------------------------------------------------------------------
# A substring anchor is how the first draft of this script appended a comment to the WRONG line: the
# prefix `$GamePort = 8798` is a prefix of a line that continues with its own comment. Line-wise, the
# whole line is the unit and the insertion point is unambiguous.
$newline = "`n"
if ($text.Contains("`r`n")) { $newline = "`r`n" }
$lines = New-Object 'System.Collections.Generic.List[string]'
foreach ($line in ($text -split "\r?\n")) { [void]$lines.Add($line) }

$portIdx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\$GamePort\s*=\s*\d+') { $portIdx = $i; break }
}
if ($portIdx -lt 0) {
    Say "REFUSED: no `$GamePort = <n> line in $Path. This is not the watcher this applier knows."
    Say "Nothing was changed."
    exit 3
}

$gpValue = '${GamePort}:127.0.0.1:${GamePort}'
$ppValue = '${PanelPort}:127.0.0.1:${PanelPort}'
$DQ = [char]34
# The value sits inside DOUBLE quotes in the watcher's ArgumentList. Both spellings are accepted here
# because the file is not ours to have memorised, and a quote style is not a shape change.
$gpElement = $DQ + $gpValue + $DQ
$gpElementAlt = $Q + $gpValue + $Q

$tunnelIdx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Contains($gpElement) -or $lines[$i].Contains($gpElementAlt)) { $tunnelIdx = $i; break }
}
if ($tunnelIdx -lt 0) {
    Say "REFUSED: could not find the GamePort -R element in the watcher's ssh ArgumentList."
    Say "Looked for a line containing:  $gpElement"
    Say "The tunnel block has changed shape; read it before editing. Nothing was changed."
    exit 4
}
if ($lines[$tunnelIdx] -notmatch '\$Remote\)') {
    Say "REFUSED: the GamePort line does not end the ArgumentList with `$Remote)."
    Say "Line $($tunnelIdx + 1): $($lines[$tunnelIdx])"
    Say "Nothing was changed."
    exit 5
}

# ---- new lines ---------------------------------------------------------------------------------
$indent = ([regex]::Match($lines[$tunnelIdx], '^\s*')).Value
$newPortLine = '$PanelPort = ' + $PanelPort + '    # the phone control panel (arsenal/panel), loopback only'
$newGameLine = $indent + $Q + '-R' + $Q + ', "' + $gpValue + '",'
$newPanelLine = $indent + $Q + '-R' + $Q + ', "' + $ppValue + '", $Remote)'

[void]$lines.Insert($portIdx + 1, $newPortLine)
$tunnelIdx = $tunnelIdx + 1                            # the port line shifted everything below it
$lines[$tunnelIdx] = $newGameLine
[void]$lines.Insert($tunnelIdx + 1, $newPanelLine)

$new = [string]::Join($newline, $lines)
if ($new -eq $text) {
    Say "REFUSED: the transformation produced no change. Nothing was written."
    exit 6
}

# ---- the parse gate: the RESULT must be valid PowerShell before it may exist --------------------
$parseErrors = $null
$tokens = $null
$null = [System.Management.Automation.Language.Parser]::ParseInput($new, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors -and $parseErrors.Count -gt 0) {
    Say "REFUSED: the edited file would NOT PARSE ($($parseErrors.Count) error(s)). Nothing was written."
    $parseErrors | Select-Object -First 5 | ForEach-Object { Say ("  line {0}: {1}" -f $_.Extent.StartLineNumber, $_.Message) }
    exit 7
}

if ($WhatIf) {
    Say "WOULD change $Path (the result parses: 0 syntax errors):"
    ($new -split "\r?\n") | Select-String -Pattern '\$PanelPort|127\.0\.0\.1:\$\{PanelPort\}' |
        ForEach-Object { Say ("  + " + $_.Line.TrimEnd()) }
    Say "(no file was written: -WhatIf)"
    exit 0
}

# ---- back up, write, read back -----------------------------------------------------------------
$backup = "$Path.bak-panel-forward-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
Copy-Item -LiteralPath $full -Destination $backup -Force
[IO.File]::WriteAllText($full, $new, (New-Object Text.UTF8Encoding($false)))

Say "changed: $Path  (the result parses: 0 syntax errors)"
Say "backup : $backup"
Say ""
Say "the lines now in the watcher:"
([IO.File]::ReadAllText($full) -split "\r?\n") |
    Select-String -Pattern '\$PanelPort|127\.0\.0\.1:\$\{PanelPort\}' |
    ForEach-Object { Say ("  " + $_.Line.TrimEnd()) }
Say ""
Say "NOT restarted. The watcher is the tunnel the phone arrives through, so restart it from the PC"
Say "keyboard (never from the phone), and only when Daniel is ready to lose the link for a few seconds:"
Say "  schtasks /End /TN PhoneLink-Watcher ; schtasks /Run /TN PhoneLink-Watcher"
exit 0
