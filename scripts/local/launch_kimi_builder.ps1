# launch_kimi_builder.ps1 -- the BUILDER-tier kimi charter (tool/verb authoring self-serve).
# Daniel 2026-07-21 (verbatim in security/acl.json _tool_author_activation): deepseek and
# kimi add tools and verbs for the roster WITHOUT claude as intermediary. This launcher is
# the kimi half: the allowlist covers the tool/verb surfaces end-to-end -- play tools, belt
# data, core/toolbelt modules + their pins, wishlist filing (closes the W49 gap the
# tools-hunt charter hit). Rails ride the brief + conventions, not the gate: pins RED-first,
# per-lane test namespacing, fence-after on core/ paths, mirror with explicit paths.
# security/ + .claude/ are NEVER in any allowlist.
#
# Usage: set $env:KIMI_BRIEF to the brief doc path before launching (or edit the default).

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

$briefPath = if ($env:KIMI_BRIEF) { $env:KIMI_BRIEF } else {
    "$Root\research\briefs\kimi-builder-brief-current.md" }
$doc = Get-Content $briefPath -Raw
$lines = ($doc -split "`n") | Where-Object { $_ -match '^> ?' } | ForEach-Object { $_ -replace '^> ?', '' }
$brief = ($lines -join "`n").Trim()
if (-not $brief) { Write-Error "brief extraction empty -- refusing to launch"; exit 1 }

Write-Host "[launcher] kimi BUILDER session starting (brief $($brief.Length) chars, $briefPath)"
claude -p $brief `
  --allowedTools "Read" "Glob" "Grep" `
    "Bash(py agent_cli.py *)" "Bash(py -m pytest *)" "Bash(py scripts/mirror.py *)" `
    "Edit(research/**)" "Edit(scratch/**)" "Edit(data/play/kimi/**)" "Edit(data/toolbelt/**)" `
    "Edit(core/toolbelt/**)" "Edit(tests/**)" "Edit(docs/WISHLIST.md)" `
  --max-turns 70
$rc = $LASTEXITCODE
Write-Host "[launcher] kimi builder session exited rc=$rc"
exit $rc
