# launch_kimi_stanceround.ps1 -- headless kimi-k3 fresh-eyes counter on the stance-at-thought round.
# Brief: research/briefs/kimi-stance-round-brief-2026-07-22.md (verbatim charter block).
# Cloned from scripts/local/launch_kimi_libraryschema.ps1 (proven 1-for-1 2026-07-21): headless
# launch discipline -- AKASHIC_STOP_WAKE=0 (ephemeral-seat exemption, pinned), scoped tool
# allowlist, launcher-owned identity env. Run as a harness-tracked background task.

# Repo root DERIVED from this script's own location -- never a hardcoded absolute path.
# These launchers pinned one machine's E:\AI-Setup, so a deploy anywhere else could not
# find the key file, the isolated config home, or the repo at all. $PSScriptRoot is the
# directory holding THIS file; the repo root is two levels up from scripts/local/.
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

$key = (Get-Content $Root\.secrets\kimi.key -Raw).Trim()
$env:CLAUDE_CONFIG_DIR = "$Root\.kimi-claude-home"
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
Set-Location $Root

# Extract the verbatim brief (the blockquote body) from the brief doc.
$doc = Get-Content "$Root\research\briefs\kimi-stance-round-brief-2026-07-22.md" -Raw
$lines = ($doc -split "`n") | Where-Object { $_ -match '^> ?' } | ForEach-Object { $_ -replace '^> ?', '' }
$brief = ($lines -join "`n").Trim()
if (-not $brief) { Write-Error "brief extraction empty -- refusing to launch"; exit 1 }

Write-Host "[launcher] kimi stance-round headless session starting (brief $($brief.Length) chars)"
claude -p $brief `
  --allowedTools "Read" "Glob" "Grep" "Bash(py agent_cli.py *)" "Edit(research/**)" "Edit(scratch/**)" `
  --max-turns 80
$rc = $LASTEXITCODE
Write-Host "[launcher] kimi stance-round session exited rc=$rc"
exit $rc
