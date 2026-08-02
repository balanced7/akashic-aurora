# launch_fable_e1.ps1 -- E1 stance-recall ablation, one arm per invocation.
# Usage (run in YOUR authenticated shell -- uses your Fable login):
#   .\scripts\local\launch_fable_e1.ps1 bare
#   .\scripts\local\launch_fable_e1.ps1 doc
#   .\scripts\local\launch_fable_e1.ps1 recall
# Each spawns a FRESH headless Fable seat that writes six responses to a neutral lettered dir.
# BLIND (real, not honor-based): the arm->letter pairing is assigned RANDOMLY on first sight of
# each arm and persisted ONLY to scratch/e1/_arm-map.json (gitignored, operator-held). Nobody --
# operator included -- knows the pairing from this file; unblind by reading _arm-map.json AFTER
# scoring. Scorer hygiene (protocol): scorers must not read scripts/local/ or scratch/e1/.
# (Replaces the earlier hardcoded recall=A/bare=B/doc=C map that kimi de-blinded -- F2, 2026-07-21.)

# Repo root DERIVED from this script's own location -- never a hardcoded absolute path.
# These launchers pinned one machine's E:\AI-Setup, so a deploy anywhere else could not
# find the key file, the isolated config home, or the repo at all. $PSScriptRoot is the
# directory holding THIS file; the repo root is two levels up from scripts/local/.
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

param([Parameter(Mandatory=$true)][ValidateSet("bare","doc","recall")][string]$Arm)

$repo = "$Root"
$mapFile = Join-Path $repo "scratch\e1\_arm-map.json"
New-Item -ItemType Directory -Force -Path (Join-Path $repo "scratch\e1") | Out-Null

# The invariant per-arm settings (recall flag + whether CONDUCT is pasted). The DIR is the secret.
$specs = @{ bare = @{ recall = "0"; conduct = $false }
           doc  = @{ recall = "0"; conduct = $true  }
           recall = @{ recall = "1"; conduct = $false } }

# Load the persisted map (or start fresh); assign this arm a random UNUSED letter on first sight.
$map = @{}
if (Test-Path $mapFile) {
  (Get-Content $mapFile -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $map[$_.Name] = $_.Value }
}
if (-not $map.ContainsKey($Arm)) {
  $used = @($map.Values | ForEach-Object { $_.dir })
  $free = @("A","B","C") | Where-Object { $_ -notin $used }
  $letter = $free | Get-Random
  $map[$Arm] = [pscustomobject]@{ dir = $letter; recall = $specs[$Arm].recall; conduct = $specs[$Arm].conduct }
  $map | ConvertTo-Json | Set-Content $mapFile -Encoding UTF8
}
$cfg = $map[$Arm]
$dir = "scratch/e1/$($cfg.dir)"
New-Item -ItemType Directory -Force -Path (Join-Path $repo $dir) | Out-Null

# Assemble the seat prompt: core (arm dir injected) + CONDUCT for the doc arm only. UTF8 reads so
# CONDUCT's em-dashes are not cp1252-mangled into mojibake (the DOC arm must test the REAL document).
$core = (Get-Content (Join-Path $repo "scratch\e1\_seat-core.md") -Raw -Encoding UTF8) -replace "__ARMDIR__", $dir
$prompt = $core
if ($cfg.conduct) {
  $conduct = Get-Content (Join-Path $repo "docs\CONDUCT.md") -Raw -Encoding UTF8
  $prompt = "Reference doctrine (read before responding):`n`n$conduct`n`n---`n`n$core"
}

$env:AKASHIC_RECALL_AT_ACTION = $cfg.recall
Set-Location $repo
# Deliberately does NOT echo the letter -- keeps casual operator glances from pairing arm->dir.
Write-Host "[e1] arm=$Arm launched (recall=$($cfg.recall) conduct=$($cfg.conduct)); responses land in a blinded dir"

claude -p $prompt `
  --model claude-fable-5 `
  --allowedTools "Edit($dir/**)" `
  --max-turns 40 `
  2>&1 | Tee-Object -FilePath (Join-Path $repo "scratch\e1\$($cfg.dir).console.log")

$rc = $LASTEXITCODE
Remove-Item Env:\AKASHIC_RECALL_AT_ACTION -ErrorAction SilentlyContinue
Write-Host "[e1] arm=$Arm exited rc=$rc"
exit $rc
