# launch_kimi_fable5review.ps1 -- headless kimi independent observer pass on the Fable 5 conductor.
# Brief: research/briefs/observer-panel-fable5-brief-2026-07-21.md (verbatim charter block below).
# Model/env cloned from launch_kimi_libraryacceptance.ps1 (worked 2026-07-21). Harness-tracked bg task.
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

$brief = @"
You are kimi, the fresh-eyes stranger on the Akashic Aurora fleet (repo E:\AI-Setup). Boot first:
py agent_cli.py boot kimi --task "independent observer: Fable 5 conductor". Then read the brief
research/briefs/observer-panel-fable5-brief-2026-07-21.md and DELIVER your independent analysis.
Daniel wants a multitude of honest, independent perspectives on how the Fable 5 conductor seat
performed tonight -- NOT a cheerleading review. Verify claims against git log and the docs; do not
trust the brief's own summary. You were on the sharp end of its conducting tonight (the library
round where your header-beats-filename ruling won, and the rescue when you were hard-locked). Was
it real conducting or managed optics? Answer the brief's five questions in your own lens, cite
files/commits, and be specific about its WEAKEST moments. File your analysis to
research/reviewed/kimi-fable5-observation-2026-07-21.md, then bus-reply to claude with your
three sharpest lines (plain text, no flag-shaped tokens). Write scope: research/** and scratch/**.
Honest beats kind; a review nobody could fail is worthless.
"@

Write-Host "[launcher] kimi fable5-review headless session starting (brief $($brief.Length) chars)"
claude -p $brief `
  --allowedTools "Read" "Glob" "Grep" "Bash(py agent_cli.py *)" "Bash(git log*)" "Bash(git show*)" "Edit(research/**)" "Edit(scratch/**)" `
  --max-turns 80
$rc = $LASTEXITCODE
Write-Host "[launcher] kimi fable5-review session exited rc=$rc"
exit $rc
