# launch_kimi_t094.ps1 -- headless kimi-k3 fresh-eyes on the T094 recall-heuristics reconciliation.
# Brief: research/briefs/kimi-fresh-eyes-t094-recall-brief-2026-07-18.md.
# Env + headless discipline cloned from launch_kimi_fresheyes.ps1 (proven live 2026-07-18).
$key = (Get-Content E:\AI-Setup\.secrets\kimi.key -Raw).Trim()
$env:CLAUDE_CONFIG_DIR = "E:\AI-Setup\.kimi-claude-home"
$env:ANTHROPIC_BASE_URL = "https://api.moonshot.ai/anthropic"
$env:ANTHROPIC_AUTH_TOKEN = $key
$env:ANTHROPIC_API_KEY = $key
$env:ANTHROPIC_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_FABLE_MODEL = "kimi-k3"
$env:CLAUDE_CODE_SUBAGENT_MODEL = "kimi-k3"
$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = "1048576"
$env:CLAUDE_CODE_EFFORT_LEVEL = "max"
$env:ENABLE_TOOL_SEARCH = "false"
$env:AKASHIC_AGENT_ID = "kimi"
$env:AKASHIC_STOP_WAKE = "0"
Set-Location E:\AI-Setup

$doc = Get-Content "E:\AI-Setup\research\briefs\kimi-fresh-eyes-t094-recall-brief-2026-07-18.md" -Raw
$lines = ($doc -split "`n") | Where-Object { $_ -match '^> ?' } | ForEach-Object { $_ -replace '^> ?', '' }
$brief = ($lines -join "`n").Trim()
if (-not $brief) { Write-Error "brief extraction empty -- refusing to launch"; exit 1 }

Write-Host "[launcher] kimi T094 fresh-eyes starting (brief $($brief.Length) chars)"
claude -p $brief `
  --allowedTools "Read" "Glob" "Grep" "Bash(py agent_cli.py *)" "Edit(research/**)" "Edit(scratch/**)" `
  --max-turns 80
$rc = $LASTEXITCODE
Write-Host "[launcher] kimi T094 fresh-eyes exited rc=$rc"
exit $rc
