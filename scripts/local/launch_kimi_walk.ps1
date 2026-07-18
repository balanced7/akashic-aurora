# launch_kimi_walk.ps1 -- start kimi-k3's blind boot-ergonomics walk (protocol:
# research/briefs/kimi-k3-blind-walk-protocol-2026-07-18.md). Session-scoped env only;
# the key never leaves this shell, nothing is persisted to settings.
$key = (Get-Content E:\AI-Setup\.secrets\kimi.key -Raw).Trim()
$env:CLAUDE_CONFIG_DIR = "E:\AI-Setup\.kimi-claude-home"   # isolated config home: no stored OAuth
                                        # (logged-in CLI 401s otherwise -- smoke-proven 2026-07-18);
                                        # kimi's harness state stays out of the claude seat's ~/.claude
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
$env:AKASHIC_AGENT_ID = "kimi"          # FULL identity chain verified 2026-07-18 (deepseek fence flag):
                                        # sessionstart card publish (claude_sessionstart.py:65), stop hook
                                        # (claude_stop.py:30), pre/post tooluse locks, pre_commit ownership --
                                        # ALL key on this env var. No sol-codex-style collision path.
Set-Location E:\AI-Setup
Write-Host "kimi-k3 walk session: endpoint + seat env armed. Verify with /status, then paste the brief from the protocol doc." -ForegroundColor Cyan
claude
