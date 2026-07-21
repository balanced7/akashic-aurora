# launch_kimi_seatzero.ps1 -- headless kimi-k3 counter round on the seat-zero onboarding wave.
# Brief: research/briefs/kimi-tools-hunt-tonight-brief-2026-07-21.md (night-run 2026-07-21).
# Env model cloned from scripts/local/launch_kimi_fresheyes.ps1 (smoke-proven 2026-07-18):
# AKASHIC_STOP_WAKE=0 (ephemeral-seat exemption, pinned by tests/test_stop_wake_exempt.py),
# read+agent_cli allowlist with writes scoped to research/** + scratch/**, launcher-owned
# identity env. Run as a harness-tracked background task.
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

# Extract the verbatim brief (the blockquote body) from the brief doc.
$doc = Get-Content "E:\AI-Setup\research\briefs\kimi-tools-hunt-tonight-brief-2026-07-21.md" -Raw
$lines = ($doc -split "`n") | Where-Object { $_ -match '^> ?' } | ForEach-Object { $_ -replace '^> ?', '' }
$brief = ($lines -join "`n").Trim()
if (-not $brief) { Write-Error "brief extraction empty -- refusing to launch"; exit 1 }

Write-Host "[launcher] kimi tools-hunt tonight session starting (brief $($brief.Length) chars)"
claude -p $brief `
  --allowedTools "Read" "Glob" "Grep" "Bash(py agent_cli.py *)" "Write(research/**)" "Edit(research/**)" "Write(scratch/**)" "Edit(scratch/**)" `
  --max-turns 35
$rc = $LASTEXITCODE
Write-Host "[launcher] kimi tools-hunt tonight session exited rc=$rc"
exit $rc


