# run_model_bakeoff.ps1 -- N models x M identical research tasks, for empirical fleet
# selection (yardstick before the mechanism, applied to the fleet itself).
#
# Fairness: identical prompt/toolset/timeout, fresh headless session per run, per-model
# agent identity (funnel attribution stays clean), preflight gates each model first --
# a model that can't tool-call is a RECORDED result, not a crash. Outputs land in
# research/bakeoff/<model>/<task>.md; grading happens elsewhere, on ANONYMIZED copies
# (scripts/local/anonymize_bakeoff.py) so the grader locks scores before unmasking.
#
# Usage:
#   .\scripts\local\run_model_bakeoff.ps1                          # default 3 models x 2 tasks
#   .\scripts\local\run_model_bakeoff.ps1 -Models @('gpt-oss:20b') -TaskTimeoutMin 20

param(
    [string[]]$Models = @("glm-4.7-flash", "qwen3-coder:30b", "gpt-oss:20b"),
    [string[]]$TaskFiles = @("research\bakeoff\tasks\004-deepseek-v4-design-parallels.md",
                             "research\bakeoff\tasks\008-critic-false-positive-calibration.md"),
    [int]$TaskTimeoutMin = 35,
    [int]$Port = 11435
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runlog = Join-Path $repo "research\bakeoff\runlog.md"
New-Item -ItemType Directory -Force (Join-Path $repo "research\bakeoff") | Out-Null

function Write-NoBom($path, $text) {
    [System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))
}
function Log($line) { Add-Content -Path $runlog -Value $line; Write-Host $line }

# --- shared env (mirrors run_research_day.ps1) -------------------------------------------
$env:OLLAMA_HOST = "127.0.0.1:$Port"
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:$Port"
$env:ANTHROPIC_AUTH_TOKEN = "ollama"

$claudeRoot = "$env:APPDATA\Claude\claude-code"
$claudeExe = Get-Command claude -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $claudeExe -and (Test-Path $claudeRoot)) {
    $claudeExe = Get-ChildItem $claudeRoot -Directory | Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
                 Sort-Object { [version]$_.Name } -Descending |
                 ForEach-Object { Join-Path $_.FullName "claude.exe" } | Where-Object { Test-Path $_ } |
                 Select-Object -First 1
}
if (-not $claudeExe) { Write-Error "claude CLI not found"; exit 1 }

Log "## Bakeoff $(Get-Date -Format 'yyyy-MM-dd HH:mm')  models=$($Models -join ', ') timeout=${TaskTimeoutMin}m"

foreach ($model in $Models) {
    $slugModel = ($model -replace '[:.]', '-')
    $outDir = Join-Path $repo "research\bakeoff\$slugModel"
    New-Item -ItemType Directory -Force $outDir | Out-Null

    # model preflight -- failing it is a scored result for the whole model
    & py (Join-Path $repo "scripts\local\preflight_local_model.py") --host "http://127.0.0.1:$Port" --model $model
    if ($LASTEXITCODE -ne 0) {
        Log "- [$model] PREFLIGHT FAILED -- all runs skipped (this is a result)"
        continue
    }

    $env:ANTHROPIC_MODEL = $model
    $env:ANTHROPIC_DEFAULT_OPUS_MODEL = $model
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = $model
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL = $model
    $env:CLAUDE_CODE_SUBAGENT_MODEL = $model
    $env:AKASHIC_AGENT_ID = "bakeoff_$slugModel"

    foreach ($taskFile in $TaskFiles) {
        $taskPath = Join-Path $repo $taskFile
        $slugTask = [System.IO.Path]::GetFileNameWithoutExtension($taskFile) -replace '^\d+-', ''
        $draft = Join-Path $outDir "$slugTask.md"
        $relDraft = "research/bakeoff/$slugModel/$slugTask.md"
        $taskBody = [System.IO.File]::ReadAllText($taskPath)
        $t0 = Get-Date
        Log "- [$(Get-Date -Format HH:mm)] START $model x $slugTask"

        $prompt = @"
You are a research worker in the Akashic Aurora repo. Read research/article-contract.md and follow it EXACTLY. Write your provisional article to $relDraft (the Write tool).

Your tools:
- SEARCH (discovery): Bash: py scripts/local/websearch.py "your query" --n 8   (finds candidates, never counts as fetching)
- FETCH (verification): WebFetch on a URL; if WebFetch fails, Bash: curl -sL <url>. Fetch every source you cite; anything unfetched is marked UNVERIFIED, never asserted bare.
- REPO (context): Grep/Glob/Read for code and docs; Bash: py agent_cli.py recall "keywords" to consult the shared corpus.

You are running UNATTENDED: every tool listed above is pre-approved -- never ask for permission or confirmation, act directly. Under 150 lines. When the article is written, re-read the file to verify, then stop.

Your task (from $taskFile):

$taskBody
"@
        $promptFile = Join-Path $env:TEMP "bakeoff_${slugModel}_${slugTask}.prompt.txt"
        Write-NoBom $promptFile $prompt
        $outLog = Join-Path $outDir "$slugTask.session.log"
        $proc = Start-Process -FilePath $claudeExe -WorkingDirectory $repo -PassThru -WindowStyle Hidden `
                -RedirectStandardInput $promptFile `
                -RedirectStandardOutput $outLog -RedirectStandardError "$outLog.err" `
                -ArgumentList @('-p', '--allowedTools=WebFetch,Grep,Glob,Read,Write,Edit,Bash(curl *),Bash(py *)')
        if (-not $proc.WaitForExit($TaskTimeoutMin * 60 * 1000)) {
            & taskkill /T /F /PID $proc.Id 2>$null | Out-Null
            Log "  [$(Get-Date -Format HH:mm)] TIMEOUT after ${TaskTimeoutMin}m"
            continue
        }
        $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
        $ok = (Test-Path $draft) -and ((Get-Item $draft).Length -gt 800) -and
              ((Select-String -Path $draft -Pattern '## Sources' -Quiet) -eq $true)
        $size = if (Test-Path $draft) { [math]::Round((Get-Item $draft).Length/1KB,1) } else { 0 }
        Log "  [$(Get-Date -Format HH:mm)] $(if ($ok) {'DONE'} else {'INVALID (missing/thin/no-Sources)'}) in ${mins}m (${size}KB)"
    }
}
Log "bakeoff complete -- anonymize before grading: py scripts/local/anonymize_bakeoff.py"
