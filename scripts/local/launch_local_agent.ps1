# launch_local_agent.ps1 -- one command: Claude Code on a LOCAL model, as a first-class
# Akashic agent (L1 -- LOCAL-ONLY, git-excluded via .git/info/exclude; user decision
# 2026-07-02: this stays off GitHub).
#
# What it does:
#   1. ensures the NATIVE Ollama server (>=0.30.9) is up on ITS OWN port (11435 -- the
#      Docker/WSL ollama on 11434 belongs to Open WebUI and is old + CPU-only; never touch it)
#   2. ensures the model is pulled, then runs the pre-flight probe (tool calls + context
#      canary + throughput) -- a failed probe aborts the launch
#   3. launches Claude Code with every model tier pinned to the local tag and an
#      AKASHIC identity, so the whole memory loop (T0-T6 hooks, recall, credit,
#      funnel attribution) runs unchanged -- hooks are user-global and model-independent
#
# Notes: Anthropic documents the gateway mechanism but does NOT support non-Claude models
# behind it (community pattern). ANTHROPIC_API_KEY is REMOVED for the child process
# (a stale real key mis-routes); ANTHROPIC_AUTH_TOKEN=ollama replaces login for this
# session only -- your claude.ai login in other terminals is untouched.
#
# Usage:
#   .\scripts\local\launch_local_agent.ps1                       # defaults: glm-4.7-flash, id glm_local
#   .\scripts\local\launch_local_agent.ps1 -Model qwen3-coder:30b -AgentId qwen_local
#   .\scripts\local\launch_local_agent.ps1 -FullPreflight        # 40K-token canary (slow, thorough)
#   .\scripts\local\launch_local_agent.ps1 -SkipPreflight -- -p "summarize chronicles/story.md"

param(
    [string]$Model = "glm-4.7-flash",
    [string]$AgentId = "glm_local",
    [int]$Port = 11435,
    [switch]$SkipPreflight,
    [switch]$FullPreflight,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ClaudeArgs
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$hostUrl = "http://127.0.0.1:$Port"
if (-not (Test-Path $ollama)) { Write-Error "ollama.exe not found at $ollama -- winget install Ollama.Ollama"; exit 1 }

function Resolve-Claude {
    # PATH first; else the desktop app's bundled CLI (%APPDATA%\Claude\claude-code\<version>\claude.exe,
    # newest version dir wins -- the dir name changes on every app update)
    $c = Get-Command claude -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $root = "$env:APPDATA\Claude\claude-code"
    if (Test-Path $root) {
        $dirs = Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
                Sort-Object { [version]$_.Name } -Descending
        foreach ($d in $dirs) {
            $exe = Join-Path $d.FullName "claude.exe"
            if (Test-Path $exe) { return $exe }
        }
    }
    return $null
}

# --- ollama server env (inherited by the serve process we may start) ------------------
$env:OLLAMA_HOST = "127.0.0.1:$Port"
$env:OLLAMA_CONTEXT_LENGTH = "64000"     # the #1 trap: default is 4K under 24GB VRAM -> silent truncation
$env:OLLAMA_FLASH_ATTENTION = "1"
$env:OLLAMA_KV_CACHE_TYPE = "q8_0"       # halves KV cache -- what makes 64K ctx fit next to a 19GB model on 16GB VRAM

function Test-Server {
    try { (Invoke-RestMethod "$hostUrl/api/version" -TimeoutSec 3).version } catch { $null }
}

$v = Test-Server
if (-not $v) {
    Write-Host "[local-agent] starting ollama serve on $hostUrl ..."
    Start-Process -WindowStyle Hidden $ollama -ArgumentList "serve"
    $tries = 0
    while (-not ($v = Test-Server) -and $tries -lt 15) { Start-Sleep -Seconds 2; $tries++ }
    if (-not $v) { Write-Error "ollama serve did not come up on $hostUrl"; exit 1 }
}
Write-Host "[local-agent] ollama $v on $hostUrl"

# --- model present? ---------------------------------------------------------------------
$tags = (Invoke-RestMethod "$hostUrl/api/tags").models | ForEach-Object { $_.name }
if (-not ($tags | Where-Object { $_ -eq $Model -or $_ -like "$Model`:*" })) {
    Write-Host "[local-agent] pulling $Model (large download, one-time) ..."
    & $ollama pull $Model
    if ($LASTEXITCODE -ne 0) { Write-Error "pull failed"; exit 1 }
}

# --- pre-flight: a failed probe is a session saved --------------------------------------
if (-not $SkipPreflight) {
    $pfArgs = @("$repo\scripts\local\preflight_local_model.py", "--host", $hostUrl, "--model", $Model)
    if ($FullPreflight) { $pfArgs += "--full" }
    & py @pfArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "pre-flight failed -- not launching (use -SkipPreflight to override)"; exit 1 }
}

# --- Claude Code env: every tier pinned local, akashic identity -------------------------
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue   # stale real key mis-routes
$env:ANTHROPIC_BASE_URL = $hostUrl
$env:ANTHROPIC_AUTH_TOKEN = "ollama"
$env:ANTHROPIC_MODEL = $Model
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = $Model
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = $Model
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = $Model   # also serves background/token-count calls -- unset = 404 spam
$env:CLAUDE_CODE_SUBAGENT_MODEL = $Model
$env:AKASHIC_AGENT_ID = $AgentId

Write-Host ""
Write-Host "[local-agent] launching Claude Code  model=$Model  agent=$AgentId  base=$hostUrl"
Write-Host "[local-agent] akashic hooks are user-global: recall/credit/draft all attribute to '$AgentId'"
Write-Host "[local-agent] keep tasks BOUNDED (summarize/classify/consolidate); this tier loops on open-ended shell work"
Write-Host ""

$claudeExe = Resolve-Claude
if (-not $claudeExe) { Write-Error "claude CLI not found (PATH or %APPDATA%\Claude\claude-code\<ver>\claude.exe)"; exit 1 }
Write-Host "[local-agent] claude: $claudeExe"
Set-Location $repo
if ($ClaudeArgs) { & $claudeExe @ClaudeArgs } else { & $claudeExe }
