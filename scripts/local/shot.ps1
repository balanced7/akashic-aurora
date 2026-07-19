# scripts/local/shot.ps1 -- one-verb headless screenshot (W22, folds failure-ledger C7-6).
# The default Chrome profile hangs headless shots on GCM phone-home (PHONE_REGISTRATION_ERROR
# loop); this bakes the PROVEN isolation flag set so no seat rediscovers it. Receipt: C7-6
# (1.56 MB PNG in <40s after two hung attempts on the default profile).
# Usage: powershell -File scripts/local/shot.ps1 -Url http://127.0.0.1:8787 [-Out ui.png] [-Width 1600]
param(
    [Parameter(Mandatory = $true)][string]$Url,
    [string]$Out = "shot.png",
    [int]$Width = 1600,
    [int]$Height = 1000
)
$scratch = Join-Path $env:TEMP ("shot-profile-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$chrome = "chrome"
if (-not (Get-Command chrome -ErrorAction SilentlyContinue)) {
    foreach ($c in @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
                     "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe")) {
        if (Test-Path $c) { $chrome = $c; break }
    }
}
& $chrome --headless=new "--screenshot=$Out" "--window-size=$Width,$Height" `
    "--user-data-dir=$scratch" --no-first-run --no-default-browser-check --disable-sync `
    --disable-background-networking "--disable-features=Translate,OptimizationHints" $Url
if (Test-Path $Out) {
    Write-Output ("shot OK: {0} ({1:N0} bytes)" -f $Out, (Get-Item $Out).Length)
} else {
    Write-Output "shot FAILED: no file produced -- see failure-ledger C7-6 for the flag rationale"
    exit 1
}
Remove-Item -Recurse -Force $scratch -ErrorAction SilentlyContinue
