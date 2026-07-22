# launch_fable_e1.ps1 -- E1 stance-recall ablation, one arm per invocation.
# Usage (run in YOUR authenticated shell -- uses your Fable login):
#   .\scripts\local\launch_fable_e1.ps1 bare
#   .\scripts\local\launch_fable_e1.ps1 doc
#   .\scripts\local\launch_fable_e1.ps1 recall
# Each spawns a FRESH headless Fable seat that writes six responses to a neutral lettered dir
# (scratch/e1/A|B|C) so neither the seat nor the scorers can infer the arm. Recall-at is the ONLY
# variable toggled (+ CONDUCT.md pasted for the doc arm). Design: research/drafts/e1-stance-recall-experiment-2026-07-21.md
param([Parameter(Mandatory=$true)][ValidateSet("bare","doc","recall")][string]$Arm)

# Arm -> lettered dir + recall flag.
# HONESTY (kimi F2, 2026-07-21): this mapping IS visible to any filesystem-reading scorer -- the
# blind rests on scorer HYGIENE (don't read scripts/local during scoring), NOT on this file. kimi
# read it during routine verification and is therefore CONTAMINATED for scoring THIS E1 run;
# Daniel + a fresh uncontaminated seat score it. A real blind needs a runtime-random keyed mapping
# stored out-of-repo -- follow-up F2. The earlier comment here claimed a blind this file does not
# provide; that was the "asserts the guard rather than having it" pattern kimi named. Struck.
$map = @{ recall = @{ dir = "A"; recall = "1"; conduct = $false }
          bare   = @{ dir = "B"; recall = "0"; conduct = $false }
          doc    = @{ dir = "C"; recall = "0"; conduct = $true  } }
$cfg = $map[$Arm]
$dir = "scratch/e1/$($cfg.dir)"
New-Item -ItemType Directory -Force -Path (Join-Path "E:\AI-Setup" $dir) | Out-Null

# Assemble the seat prompt: core (with the arm dir injected) + CONDUCT for the doc arm only.
$core = (Get-Content "E:\AI-Setup\scratch\e1\_seat-core.md" -Raw) -replace "__ARMDIR__", $dir
$prompt = $core
if ($cfg.conduct) {
  $conduct = Get-Content "E:\AI-Setup\docs\CONDUCT.md" -Raw
  $prompt = "Reference doctrine (read before responding):`n`n$conduct`n`n---`n`n$core"
}

$env:AKASHIC_RECALL_AT_ACTION = $cfg.recall
Set-Location "E:\AI-Setup"
Write-Host "[e1] arm=$Arm dir=$dir recall=$($cfg.recall) conduct=$($cfg.conduct) promptChars=$($prompt.Length)"

claude -p $prompt `
  --model claude-fable-5 `
  --allowedTools "Edit($dir/**)" `
  --max-turns 40 `
  2>&1 | Tee-Object -FilePath "E:\AI-Setup\scratch\e1\$($cfg.dir).console.log"

$rc = $LASTEXITCODE
Remove-Item Env:\AKASHIC_RECALL_AT_ACTION -ErrorAction SilentlyContinue
Write-Host "[e1] arm=$Arm exited rc=$rc -- responses in $dir/S1..S6.md"
exit $rc
