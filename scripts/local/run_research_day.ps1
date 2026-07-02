# run_research_day.ps1 -- the local fleet's shift: work research/queue/ all day, one
# provisional article per task (see research/README.md for the whole loop).
#
# Each task gets a FRESH headless Claude Code session on the local model (no context rot,
# no cross-task bleed) with a hard timeout. Drafts are validated (exists + has Sources)
# before a task counts as done; anything else is marked failed for the evening review.
#
# Usage:
#   .\scripts\local\run_research_day.ps1                    # defaults: all queued tasks, 35min each
#   .\scripts\local\run_research_day.ps1 -MaxTasks 2 -TaskTimeoutMin 10   # smoke test

param(
    [int]$MaxTasks = 8,
    [int]$TaskTimeoutMin = 35,
    [string]$Model = "glm-4.7-flash",
    [string]$AgentId = "glm_local",
    [int]$Port = 11435
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$queueDir = Join-Path $repo "research\queue"
$draftDir = Join-Path $repo "research\drafts"
$runlog = Join-Path $repo ("research\runlog-" + (Get-Date -Format "yyyy-MM-dd") + ".md")
New-Item -ItemType Directory -Force $draftDir | Out-Null

function Write-NoBom($path, $text) {
    [System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))
}

function Set-TaskStatus($file, $from, $to) {
    $txt = [System.IO.File]::ReadAllText($file)
    Write-NoBom $file ($txt -replace "(?m)^status:\s*$from", "status: $to")
}

function Log($line) {
    Add-Content -Path $runlog -Value $line
    Write-Host $line
}

# --- one full pre-flight for the day (server up, model pulled, tools + context sane) ----
& powershell -NoProfile -ExecutionPolicy Bypass -Command "& '$repo\scripts\local\launch_local_agent.ps1' -Model '$Model' -Port $Port -ClaudeArgs @('--version')" | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "day pre-flight failed -- fix the local server before starting the shift"; exit 1 }

# --- env for the headless workers (children inherit; mirrors launch_local_agent.ps1) ----
$env:OLLAMA_HOST = "127.0.0.1:$Port"
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:$Port"
$env:ANTHROPIC_AUTH_TOKEN = "ollama"
$env:ANTHROPIC_MODEL = $Model
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = $Model
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = $Model
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = $Model
$env:CLAUDE_CODE_SUBAGENT_MODEL = $Model
$env:AKASHIC_AGENT_ID = $AgentId

$claudeRoot = "$env:APPDATA\Claude\claude-code"
$claudeExe = Get-Command claude -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $claudeExe -and (Test-Path $claudeRoot)) {
    $claudeExe = Get-ChildItem $claudeRoot -Directory | Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
                 Sort-Object { [version]$_.Name } -Descending |
                 ForEach-Object { Join-Path $_.FullName "claude.exe" } | Where-Object { Test-Path $_ } |
                 Select-Object -First 1
}
if (-not $claudeExe) { Write-Error "claude CLI not found"; exit 1 }

Log "## Research shift $(Get-Date -Format 'yyyy-MM-dd HH:mm')  model=$Model agent=$AgentId maxTasks=$MaxTasks timeout=${TaskTimeoutMin}m"

$done = 0
while ($done -lt $MaxTasks) {
    $task = Get-ChildItem $queueDir -Filter "*.md" | Sort-Object Name |
            Where-Object { (Get-Content $_.FullName -TotalCount 1) -match '^status:\s*queued' } |
            Select-Object -First 1
    if (-not $task) { Log "queue empty -- shift over ($done task(s) done)"; break }

    $slug = $task.BaseName -replace '^\d+-', ''
    $draft = Join-Path $draftDir "$slug.md"
    $taskBody = [System.IO.File]::ReadAllText($task.FullName)
    Set-TaskStatus $task.FullName "queued" "running"
    $t0 = Get-Date
    Log "- [$(Get-Date -Format HH:mm)] START $($task.Name) -> drafts/$slug.md"

    $prompt = @"
You are $AgentId, a research worker in the Akashic Aurora repo. Read research/article-contract.md and follow it EXACTLY. Write your provisional article to research/drafts/$slug.md (the Write tool). Fetch every source you cite -- prefer WebFetch; if WebFetch fails, use Bash: curl -sL <url>. Anything you could not fetch this session is marked UNVERIFIED, never asserted bare. Under 150 lines. When the article is written, re-read the file to verify, then stop.

Your task (from research/queue/$($task.Name)):

$taskBody
"@

    # Prompt travels via STDIN, never -ArgumentList: Start-Process joins arguments UNQUOTED,
    # which mangles any multi-line prompt into nothing (the agent then just sees the boot
    # whisper and asks what to do -- observed live 2026-07-02).
    $outLog = Join-Path $draftDir "$slug.session.log"
    $promptFile = Join-Path $env:TEMP "akashic_research_$slug.prompt.txt"
    Write-NoBom $promptFile $prompt
    $proc = Start-Process -FilePath $claudeExe -WorkingDirectory $repo -PassThru -WindowStyle Hidden `
            -RedirectStandardInput $promptFile `
            -RedirectStandardOutput $outLog -RedirectStandardError "$outLog.err" `
            -ArgumentList @('-p', '--allowedTools=WebFetch,Read,Write,Edit,Bash(curl *)')
    if (-not $proc.WaitForExit($TaskTimeoutMin * 60 * 1000)) {
        & taskkill /T /F /PID $proc.Id 2>$null | Out-Null
        Set-TaskStatus $task.FullName "running" "failed"
        Log "  [$(Get-Date -Format HH:mm)] TIMEOUT after ${TaskTimeoutMin}m -> failed"
        $done++; continue
    }

    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    $ok = (Test-Path $draft) -and ((Get-Item $draft).Length -gt 800) -and
          ((Select-String -Path $draft -Pattern '## Sources' -Quiet) -eq $true)
    if ($ok) {
        Set-TaskStatus $task.FullName "running" "done"
        Log "  [$(Get-Date -Format HH:mm)] DONE in ${mins}m ($([math]::Round((Get-Item $draft).Length/1KB,1))KB)"
    } else {
        Set-TaskStatus $task.FullName "running" "failed"
        Log "  [$(Get-Date -Format HH:mm)] FAILED in ${mins}m -- draft missing/thin/no-Sources (see $slug.session.log)"
    }
    $done++
}

Log ""
Log "shift summary: $(Get-ChildItem $queueDir -Filter '*.md' | ForEach-Object { (Get-Content $_.FullName -TotalCount 1) } | Group-Object | ForEach-Object { ""$($_.Count)x $($_.Name)"" })"
