# launch_kimi_walk.ps1 -- start kimi-k3's blind boot-ergonomics walk (protocol:
# research/briefs/kimi-k3-blind-walk-protocol-2026-07-18.md). Session-scoped env only;
# the key never leaves this shell, nothing is persisted to settings.
$key = (Get-Content E:\AI-Setup\.secrets\kimi.key -Raw).Trim()
$env:ANTHROPIC_BASE_URL = "https://api.moonshot.ai/anthropic"
$env:ANTHROPIC_AUTH_TOKEN = $key
$env:ANTHROPIC_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "kimi-k3"
$env:ANTHROPIC_DEFAULT_FABLE_MODEL = "kimi-k3"
$env:CLAUDE_CODE_SUBAGENT_MODEL = "kimi-k3"
$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = "1048576"
$env:CLAUDE_CODE_EFFORT_LEVEL = "max"
$env:ENABLE_TOOL_SEARCH = "false"
$env:AKASHIC_AGENT_ID = "kimi"          # hooks + doors scope to the kimi seat (claude_stop.py:30)
Set-Location E:\AI-Setup
Write-Host "kimi-k3 walk session: endpoint + seat env armed. Verify with /status, then paste the brief from the protocol doc." -ForegroundColor Cyan
claude
