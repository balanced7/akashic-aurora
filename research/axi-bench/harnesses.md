# AXI bench: `harnesses`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 3,716 | 2,006 | -1,710 (-46%) |
| Stdout characters (all runs) | 4,717 | 602 | -4,115 (-87%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many tiers does the cursor harness automate? | `6` | 5/5 | 5/5 |
| Which agent id does the deepseek-harness use? | `dsh_agent` | 5/5 | 5/5 |
| Which harnesses automate tier T5? List them separated by commas. | `['claude-code']` | 5/5 | 5/5 |
| In one word or hyphenated phrase, what is the cursor harness's status for tier T3? | `one-beat-late` | 5/5 | 5/5 |
| How many harnesses are listed? | `5` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora harnesses` (exit 0)

```
# INTEGRATION TIERS  (T0 door .. T6 close; the story: docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md)

## claude-code  (agent id: claude; 7/7 tiers automated)
   adapters: agent/harness/hooks/claude_*.py (`agent_cli.py hooks install`: user or project scope, scope-guarded; check with `hooks status`)
   + T0: yes -- shell (Bash/PowerShell) + ai_setup_mcp.py
   + T1: yes -- .claude/settings.json env
   + T2: yes -- SessionStart additionalContext (light whisper, tiered by cwd) (once installed: `hooks status`)
   + T3: yes, AT the action -- PreToolUse can inject on allow (once installed: `hooks status`)
   + T4: yes -- transcript-synthesized FAIL (PostToolUse never fires on failure) + PostToolUseFailure fast path; conservative _is_success
   + T5: yes -- UserPromptSubmit injects plan-time recall + unread-bus line (once installed: `hooks status`)
   + T6: yes -- SessionEnd/PreCompact -> chronicles/last-session-draft.md (once installed: `hooks status`)

## deepseek-harness  (agent id: dsh_agent; 5/7 tiers automated)
   adapters: out-of-tree dsh-posttool (cordis) plugin -> core/recall/actions.py::recall_context (importable contract)
   + T0: yes -- exec proven: the dsh seat drives the house CLI (uv run agent_cli.py) and messages peers over the Bifrost bus
   + T1: yes -- $DSH_HOME/.env user-env layer (dsh-launch-environment) stamps AKASHIC_AGENT_ID=dsh_agent + AKASHIC_REPO; verified live 2026-08-24: child processes inherit the stamp across a host restart
   - T2: pending -- session/created -> boot-whisper listener wired; first live observation rides the next fresh session (plugin mounted mid-session 2026-08-24)
   + T3: one-beat-late -- post-execute recall attaches via decision.additionalContexts (the harness contract, pinned in tests/test_dsh_contract.py); recall-at contexts observed arriving at the next step in live sessions 2026-08-24 (they ride the loop's active batch, same shape as cursor's tier)
   + T4: yes -- tools/post-execute carries a direct fail signal; outcome-credit wired. The stale-generation doubt is RETIRED: post-reboot 2026-08-24 the plugin writes c:-normalized targets (stage file evidence), so the V27 join keys surface and resolve identically; the first real flip-credit is the remaining unobserved event
   - T5: pending -- trigger observed live 2026-08-24 (user/message captured, planPending set post-mount) and the plan-recall door verified end-to-end; the assemble-time injection itself is still unobserved
   + T6: yes -- session/disposed+flush fire presence-offline + the DSH-native session-end shim (zstd log -> last-session-draft + session_signals); shim dogfooded end-to-end 2026-08-24, first live fire rides the next session close

## cursor  (agent id: composer; 6/7 tiers automated)
   adapters: agent/harness/hooks/cursor_*.py (project .cursor/hooks.json)
   + T0: yes -- Shell tool + scripts/static/mcp/ (cursor MCP config)
   + T1: yes -- sessionStart hook returns env (propagates all session hooks) + MCP config env
   + T2: yes -- sessionStart additional_context
   + T3: one-beat-late -- preToolUse is deny-only (cannot inject on allow); recall rides postToolUse/postToolUseFailure additional_context
   + T4: yes, DIRECT -- postToolUseFailure is a real fail event (no transcript synthesis needed)
   - T5: unavailable -- beforeSubmitPrompt cannot inject context
   + T6: yes -- sessionEnd -> chronicles/last-session-draft.md

## codex-desktop  (agent id: sol; 2/7 tiers automated)
   adapters: agent/harness/codex_app_server.py (owned app-server child) + the claude_* hooks via .codex/hooks.json (`agent_cli.py hooks install --harness codex`)
   + T0: yes -- shell + ai_setup_mcp.py (.codex/config.toml)
   + T1: yes -- .codex/config.toml env (AKASHIC_AGENT_ID)
   - T2: pending -- SessionStart wiring declared; no live receipt yet (docs/CODEX_INTEGRATION.md)
   - T3: pending -- PreToolUse runs the claude_* adapter; Codex payload parity unobserved
   - T4: pending -- PostToolUse runs the claude_* adapter; Codex payload parity unobserved
   - T5: pending -- UserPromptSubmit not yet observed live
   - T6: pending -- no Codex transcript parser; close/draft unbuilt

## bare-cli  (agent id: <set AKASHIC_AGENT_ID>; 1/7 tiers automated)
   adapters: none -- the AGENTS.md contract, followed manually
   + T0: yes -- uv run agent_cli.py (the one door)
   - T1: manual -- export AKASHIC_AGENT_ID before working
   - T2: manual -- uv run agent_cli.py boot <id> --task ...
   - T3: manual -- uv run agent_cli.py recall-at --path/--command before acting
   - T4: manual -- uv run agent_cli.py learn / recall-feedback
   - T5: unavailable -- no per-prompt seam exists
   - T6: manual -- uv run agent_cli.py wrap --commit
```


## After: output

`aurora harnesses` (exit 0)

```
tiers: 7
harnesses[5]{harness,agent_id,automated,T0,T1,T2,T3,T4,T5,T6}:
  claude-code,claude,7,yes,yes,yes,"yes, AT the action",yes,yes,yes
  deepseek-harness,dsh_agent,5,yes,yes,pending,one-beat-late,yes,pending,yes
  cursor,composer,6,yes,yes,yes,one-beat-late,"yes, DIRECT",unavailable,yes
  codex-desktop,sol,2,yes,yes,pending,pending,pending,pending,pending
  bare-cli,null,1,yes,manual,manual,manual,manual,unavailable,manual
story: docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md
help[2]:
  uv run agent_cli.py harnesses --json
  uv run agent_cli.py hooks status
```
