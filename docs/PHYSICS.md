# PHYSICS -- mechanical truths of the machinery (auto-generated)

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_physics_sheet.py`.
> Derived at c753012. A bound you discover by collision is not awareness -- this sheet
> exists so every clip, cap, timeout and flag is READABLE before it is HIT.
> Dynamic envelopes (throughput, latency, limits-under-load) are NOT here: they require
> measurement, not grep -- see the master-map charter M2b (benchmark half).

## Configuration flags (141 names)

| Flag | Default (as written) | Read sites |
|---|---|---|
| `AGENT_ID` | `"unknown"` | core/comm/bus.py:1098 |
| `AI_SETUP` | `"E:\\AI-Setup"` | agent_cli.py:1111, agent_cli.py:2024, agent_cli.py:2106 +16 |
| `AKASHIC_ACK_UNHANDLED_HOURS` | `UNHANDLED_HOURS` | core/comm/promoter.py:151 |
| `AKASHIC_AGENT_ID` | `"claude"` | agent/harness/hooks/claude_posttooluse.py:197, agent/harness/hooks/claude_posttooluse.py:299, agent/harness/hooks/claude_posttooluse.py:308 +43 |
| `AKASHIC_ASK_EXPECT_S` | `"1800"` | agent_cli.py:3508 |
| `AKASHIC_AUTOBOOT` | `"1"` | agent/harness/context.py:159 |
| `AKASHIC_BIRTH_GUARD` | `""` | scripts/githooks/birth_guard.py:70 |
| `AKASHIC_BOOT_FULL` | `"0"` | agent_cli.py:1136 |
| `AKASHIC_CB_MAX` | `"3"` | scripts/bifrost_daemon.py:233 |
| `AKASHIC_CB_WINDOW_S` | `"300"` | scripts/bifrost_daemon.py:232 |
| `AKASHIC_CLEAN_DEATH` | `"1"` | core/comm/session_exit.py:51 |
| `AKASHIC_DAEMON_WAKE` | `"1"` | agent/harness/hooks/claude_stop.py:247, scripts/hooks/claude_stop.py:247 |
| `AKASHIC_DEBUG` | `` | agent/harness/hooks/claude_userpromptsubmit.py:93, scripts/hooks/claude_userpromptsubmit.py:93 |
| `AKASHIC_DRILL_ECHO` | `` | scripts/bifrost_runner.py:152, scripts/bifrost_runner.py:168, scripts/bifrost_runner_deepseek.py:960 +8 |
| `AKASHIC_EMBED_THEMES` | `""` | core/narrative/beat_log.py:79, core/narrative/theme_discovery.py:190 |
| `AKASHIC_EXPECT_TASK_SETTLE` | `"1"` | core/comm/expectations.py:44 |
| `AKASHIC_FENCE_ROOT` | `` | core/coord/fence_workspace.py:53 |
| `AKASHIC_FLOW_NO_COUNT` | `` | core/comm/flow_trace.py:199 |
| `AKASHIC_GATE_NO_CEILING` | `` | scripts/checkers/check_reconciliation_gate.py:59 |
| `AKASHIC_HEAL_VERBOSE` | `` | agent_cli.py:230 |
| `AKASHIC_INCARNATION_TTL_MIN` | `"30"` | core/comm/incarnation.py:35 |
| `AKASHIC_JOB_ENFORCEMENT` | `` | scripts/run_job.py:596 |
| `AKASHIC_JOB_OBJECT_NAME` | `` | scripts/run_job.py:595 |
| `AKASHIC_KILLPOINT` | `""` | scripts/bifrost_runner_deepseek.py:73, scripts/bifrost_runner_kimi.py:128, scripts/bifrost_runner_sol.py:128 |
| `AKASHIC_KIMI_NARRATOR` | `"1"` | scripts/kimi_walk_narrator.py:106 |
| `AKASHIC_KMAP_NO_COUNT` | `` | core/recall/knowledge_map.py:222 |
| `AKASHIC_LEARN_NUDGE` | `"1"` | agent/harness/nudge.py:25 |
| `AKASHIC_LEARN_NUDGE_CAP` | `"3"` | agent/harness/nudge.py:28 |
| `AKASHIC_LOOKBACK_NO_COUNT` | `` | core/recall/lookback.py:363 |
| `AKASHIC_MAILBOX` | `"1"` | core/comm/mailbox.py:60 |
| `AKASHIC_MCP_DIAG` | `` | ai_setup_mcp.py:724 |
| `AKASHIC_OPERATOR_IDS` | `"user,daniel"` | scripts/bifrost_wake.py:65 |
| `AKASHIC_PAYLOAD_CAPTURE` | `"1"` | agent/harness/capture.py:37 |
| `AKASHIC_PLAN_RECALL` | `"1"` | agent/harness/hooks/claude_userpromptsubmit.py:42, scripts/hooks/claude_userpromptsubmit.py:42 |
| `AKASHIC_PLAY_NETWORK` | `"0"` | core/toolbelt/play_sandbox.py:36 |
| `AKASHIC_PLAY_OUTPUT_MAX` | `"65536"` | core/toolbelt/play_sandbox.py:34 |
| `AKASHIC_PLAY_TIMEOUT_S` | `"30"` | core/toolbelt/play_sandbox.py:35 |
| `AKASHIC_PROPOSED_STALE_DAYS` | `stale_days` | core/coord/task_ledger.py:397 |
| `AKASHIC_RECALL_AT_ACTION` | `"1"` | agent/harness/hooks/claude_posttooluse.py:233, agent/harness/hooks/claude_pretooluse.py:107, agent/harness/hooks/cursor_posttooluse.py:105 +2 |
| `AKASHIC_RECALL_CACHE_TTL` | `"120"` | core/recall/at_action.py:65 |
| `AKASHIC_RECALL_FLOOR` | `"0.20"` | core/recall/at_action.py:1105 |
| `AKASHIC_RECALL_SELF_ECHO_H` | `"2"` | core/recall/at_action.py:1041 |
| `AKASHIC_RECALL_STATE_DIR` | `` | agent/harness/hooks/claude_posttooluse.py:61, agent/harness/hooks/claude_sessionend.py:35, agent/harness/hooks/cursor_beforeshell.py:23 +9 |
| `AKASHIC_RECENT_INBOX_S` | `str(12 * 3600` | core/comm/doctor.py:60 |
| `AKASHIC_RELEVANCE_BUDGET` | `"1"` | core/context/learning_loader.py:36 |
| `AKASHIC_RELEVANCE_BUDGET_CHARS` | `""` | core/context/relevance_budget.py:49 |
| `AKASHIC_SEAT_DOOR` | `""` | agent_cli.py:1221 |
| `AKASHIC_SEAT_DOOR_DETAIL` | `""` | agent_cli.py:1222 |
| `AKASHIC_SESSION_SIGNALS` | `"1"` | agent/harness/hooks/claude_sessionend.py:126, scripts/hooks/claude_sessionend.py:126 |
| `AKASHIC_SESSION_SIGNALS_MAX_BYTES` | `str(16 * 1024 * 1024` | agent/harness/hooks/claude_sessionend.py:40, scripts/hooks/claude_sessionend.py:40 |
| `AKASHIC_SPILL_DIR` | `` | agent_cli.py:83 |
| `AKASHIC_STALE_CUE_DAYS` | `"30"` | core/recall/at_action.py:70 |
| `AKASHIC_STALL_HYSTERESIS_S` | `"180"` | core/comm/doctor.py:46 |
| `AKASHIC_STOP_PROMISE` | `"1"` | agent/harness/hooks/claude_stop.py:168, scripts/hooks/claude_stop.py:168 |
| `AKASHIC_STOP_WAKE` | `"1"` | agent/harness/hooks/claude_stop.py:238, scripts/hooks/claude_stop.py:238 |
| `AKASHIC_TIMEOUT_MULTIPLIER` | `"1"` | core/comm/timescale.py:21 |
| `AKASHIC_TOMBSTONE` | `"1"` | core/comm/wake_seat.py:109, core/comm/wake_seat.py:167 |
| `AKASHIC_TOOLBELT_QUOTA` | `"20"` | core/toolbelt/registry.py:32 |
| `AKASHIC_TRACE` | `"1"` | agent/harness/hooks/claude_trace.py:27, agent/harness/trace.py:24, agent/harness/trace.py:52 +1 |
| `AKASHIC_TRANSCRIPT_TAIL_BYTES` | `str(4 * 1024 * 1024` | agent/harness/hooks/claude_posttooluse.py:105, scripts/hooks/claude_posttooluse.py:105 |
| `AKASHIC_WAKE_MARKER_FRESH_MIN` | `""` | core/comm/wake_seat.py:311 |
| `AKASHIC_WHISPER_LINES` | `""` | agent/harness/context.py:109 |
| `AKASHIC_WISHLIST_FILE` | `` | agent_cli.py:1650 |
| `BIFROST_APPROACHING_WEDGE_SECONDS` | `"150"` | core/comm/liveness.py:49 |
| `BIFROST_CONSUME_LANE` | `` | core/comm/bifrost_api.py:214 |
| `BIFROST_INCARNATION` | `` | core/comm/bus.py:275, core/comm/bus.py:356 |
| `BIFROST_LANES_DUAL_WRITE` | `True` | core/comm/packet_spec.py:300 |
| `BIFROST_MAX_HOPS` | `"6"` | core/comm/control.py:64 |
| `BIFROST_MAX_REPLIES_PER_MIN` | `"12"` | core/comm/control.py:65 |
| `BIFROST_NAMESPACE` | `"bifrost"` | agent/harness/delta.py:35, agent_cli.py:4646, core/comm/bus.py:151 +20 |
| `BIFROST_PREFLIGHT_ASSERT` | `"1"` | core/comm/assertions.py:100 |
| `BIFROST_PREMISE_GATE_MIN_AGE_MS` | `` | core/coord/task_ledger.py:333 |
| `BIFROST_REPLY_DEDUP_TTL_S` | `"1200"` | core/comm/bus.py:334 |
| `BIFROST_STALE_MS` | `DEFAULT_STALE_MS` | core/comm/packet_spec.py:337 |
| `BIFROST_UI_PORT` | `"8787"` | core/comm/doctor.py:864 |
| `BIFROST_WAKE_DEADLINE_S` | `""` | scripts/bifrost_wake.py:127 |
| `BIFROST_WAKE_LANE` | `"work"` | agent_cli.py:3432, core/comm/bifrost_api.py:134 |
| `BIFROST_WAKE_LONGLIVED` | `"1"` | scripts/bifrost_wake.py:132 |
| `BIFROST_WEDGE_SECONDS` | `"300"` | core/comm/liveness.py:44 |
| `BUS_MAX_MESSAGE_BYTES` | `DEFAULT_MAX_MESSAGE_BYTES` | core/comm/packet_spec.py:66 |
| `CLAUDE_CODE_SESSION_ID` | `` | agent_cli.py:3439, core/comm/runner_lock.py:186 |
| `CLAUDE_SESSION_ID` | `` | agent_cli.py:3439, core/comm/runner_lock.py:186 |
| `CURSOR_PROJECT_DIR` | `` | agent/harness/hooks/cursor_posttooluse.py:91, agent/harness/hooks/cursor_sessionstart.py:49 |
| `DEEPSEEK_API_KEY` | `` | scripts/ask_deepseek.py:31, scripts/deepseek_chat.py:122 |
| `DEEPSEEK_CONNECT_TIMEOUT` | `"15"` | scripts/deepseek_chat.py:61 |
| `DEEPSEEK_MAX_CMD_TIMEOUT` | `"300"` | core/comm/toolbox.py:32 |
| `DEEPSEEK_MAX_RETRIES` | `"1"` | scripts/deepseek_chat.py:63 |
| `DEEPSEEK_MODEL` | `"deepseek-v4-pro"` | scripts/ask_deepseek.py:26 |
| `DEEPSEEK_READ_TIMEOUT` | `"120"` | scripts/deepseek_chat.py:62 |
| `DEEPSEEK_RECALL_AT` | `` | core/comm/toolbox.py:1011, core/comm/toolbox.py:1041, scripts/bifrost_runner_deepseek.py:390 |
| `DEEPSEEK_RUNNER_MAX_TOKENS` | `"8000"` | scripts/bifrost_runner_deepseek.py:66 |
| `DOC_CURRENCY_STALE_DAYS` | `"45"` | scripts/checkers/check_doc_currency.py:30 |
| `EMBED_MODEL` | `DEFAULT_MODEL` | core/primitives/embedder.py:48 |
| `FRAG_REASSEMBLY_TTL` | `DEFAULT_FRAG_REASSEMBLY_TTL` | core/comm/packet_spec.py:74 |
| `GEMINI_MODEL` | `"gemini-2.5-flash"` | scripts/ask_gemini.py:22, scripts/ask_gemini_vision.py:14 |
| `GEMINI_WEB_BROWSER` | `""` | scripts/gemini_web.py:140 |
| `GEMINI_WEB_ENGINE` | `"playwright"` | scripts/gemini_web.py:102 |
| `GEMINI_WEB_HEADED` | `""` | scripts/gemini_web.py:147 |
| `GEMINI_WEB_PATCHRIGHT_CHANNEL` | `""` | scripts/gemini_web.py:245 |
| `GEMINI_WEB_STEALTH` | `"1"` | scripts/gemini_web.py:180 |
| `GEMINI_WEB_TIMEOUT_MS` | `"120000"` | scripts/gemini_web.py:50 |
| `GEMINI_WEB_TZ` | `"America/New_York"` | scripts/gemini_web.py:234 |
| `KIMI_API_KEY` | `` | scripts/kimi_chat.py:69 |
| `KIMI_BUDGET_USD` | `"105.0"` | scripts/kimi_chat.py:61 |
| `KIMI_CLAUDE_HOME` | `r"E:\AI-Setup\.kimi-claude-home"` | scripts/kimi_walk_narrator.py:36 |
| `KIMI_CONNECT_TIMEOUT` | `"15"` | scripts/kimi_chat.py:51 |
| `KIMI_EFFORT` | `"max"` | scripts/kimi_chat.py:48 |
| `KIMI_MAX_HOPS` | `"30"` | scripts/bifrost_runner_kimi.py:65, scripts/kimi_chat.py:260 |
| `KIMI_MAX_RETRIES` | `"1"` | scripts/kimi_chat.py:53 |
| `KIMI_MODEL` | `K3` | scripts/kimi_chat.py:47 |
| `KIMI_READ_TIMEOUT` | `"180"` | scripts/kimi_chat.py:52 |
| `KIMI_RUNNER_MAX_TOKENS` | `"8000"` | scripts/kimi_chat.py:50 |
| `KIMI_SPEND_FILE` | `str(REPO_ROOT / "state" / "kimi_spend.json"` | scripts/kimi_chat.py:64 |
| `KIMI_SPEND_REFUSE` | `'95'` | scripts/bifrost_runner_kimi.py:329, scripts/kimi_chat.py:63 |
| `KIMI_SPEND_WARN` | `"80.0"` | scripts/kimi_chat.py:62 |
| `LAUNCHER_AUTO_REVIVE_JITTER` | `"4"` | core/comm/launcher.py:66 |
| `LAUNCHER_RESTART_BACKOFF` | `"3"` | core/comm/launcher.py:53 |
| `LAUNCHER_RESTART_BACKOFF_MAX` | `"60"` | core/comm/launcher.py:54 |
| `LAUNCHER_RESTART_MAX` | `"5"` | core/comm/launcher.py:55 |
| `LAUNCHER_RESTART_RESET` | `"300"` | core/comm/launcher.py:56 |
| `OPENAI_API_KEY` | `` | scripts/ask_gpt.py:27 |
| `OPENAI_MODEL` | `"gpt-5"` | scripts/ask_gpt.py:23 |
| `PACKET_INTEGRITY_ENABLED` | `True` | core/comm/packet_spec.py:70 |
| `PACKET_INTEGRITY_TRACE` | `False` | core/comm/packet_spec.py:313 |
| `PACKET_TRACE_SPOT_INTERVAL` | `DEFAULT_TRACE_SPOT_INTERVAL` | core/comm/packet_spec.py:304 |
| `PYTEST_CURRENT_TEST` | `` | core/comm/bus.py:156 |
| `REDIS_DB` | `` | core/foundation/redis_connection.py:86 |
| `REDIS_HOST` | `` | core/foundation/redis_connection.py:72 |
| `REDIS_PORT` | `` | core/foundation/redis_connection.py:72 |
| `SOL_401_RETRIES` | `"3"` | scripts/sol_chat.py:56 |
| `SOL_CONNECT_TIMEOUT` | `"15"` | scripts/sol_chat.py:53 |
| `SOL_EFFORT` | `"medium"` | scripts/sol_chat.py:45 |
| `SOL_MAX_HOPS` | `"30"` | scripts/bifrost_runner_sol.py:71, scripts/sol_chat.py:185 |
| `SOL_MAX_RETRIES` | `"1"` | scripts/sol_chat.py:55 |
| `SOL_MODEL` | `SOL` | scripts/sol_chat.py:41 |
| `SOL_READ_TIMEOUT` | `"120"` | scripts/sol_chat.py:54 |
| `SOL_RUNNER_MAX_TOKENS` | `"8000"` | scripts/sol_chat.py:49 |
| `SOL_VERBOSITY` | `"medium"` | scripts/sol_chat.py:46 |
| `STORM_DEPTH_THRESHOLD` | `50` | core/comm/storm_detect.py:50 |
| `STORM_DEPTH_WINDOW` | `3` | core/comm/storm_detect.py:53 |
| `STORM_REPEAT_THRESHOLD` | `5` | core/comm/storm_detect.py:56 |

## Mechanical bounds (98 numeric constants)

| Constant | Value | Site | Note |
|---|---|---|---|
| `ACTIVITY_TTL` | 25 | core/comm/control.py:354 |  |
| `BENCH_MIN_SURFACED` | 10 | core/recall/curator.py:32 | exposure floor: it had its chances... |
| `BODY_CHARS` | 12,000 | core/recall/lookback.py:37 | rationale often sits DEEP: a synthesis doc's convergence and |
| `BOOT_CAP` | 3 | core/coord/defer_queue.py:34 |  |
| `BUDGET_CHARS_DEFAULT` | 2,000 | core/context/relevance_budget.py:36 |  |
| `BUDGET_DEFAULT` | 1,200 | agent/harness/delta.py:29 |  |
| `BULLET_MIN` | 6 | scripts/checkers/check_bus_atom_pointers.py:37 | or this many list items |
| `CANONICAL_MAXLEN` | 100,000 | core/events/event_log.py:43 | the firehose: deep but bounded |
| `CANONICAL_MAXLEN` | 100,000 | core/signals/agent_signal_ledger.py:52 | signals retained on the canonical stream |
| `CAP` | 50 | core/comm/pager.py:20 |  |
| `CATEGORY_CAP_PER_ATOM` | 3 | core/library/taxonomy.py:27 |  |
| `CHAIN_WARN_THRESHOLD` | 50 | core/learning/agent_memory.py:71 |  |
| `CLARIFY_MAX_PER_TASK` | 3 | core/comm/toolbox.py:164 |  |
| `CLARIFY_TIMEOUT_S` | 300 | core/comm/toolbox.py:165 |  |
| `CREDITED_MIN_CONTEXTS` | 2 | core/recall/replay.py:29 | criterion 3: credited contexts per credited lesson... |
| `DEFAULT_BUDGET` | 2,000 | core/comm/mailbox.py:41 |  |
| `DEFAULT_CAP` | 5,000 | core/comm/mailbox.py:40 |  |
| `DEFAULT_FRAG_REASSEMBLY_TTL` | 300 | core/comm/packet_spec.py:42 |  |
| `DEFAULT_MAXLEN` | 10,000 | core/comm/bus.py:36 |  |
| `DEFAULT_MAXLEN` | 100,000 | core/events/event_index.py:43 | match the firehose (event_log.CANONICAL_MAXLEN) |
| `DEFAULT_MAX_CHARS` | 170 | core/primitives/consolidator.py:32 |  |
| `DEFAULT_MAX_MESSAGE_BYTES` | 65,536 | core/comm/packet_spec.py:41 |  |
| `DEFAULT_MAX_PROMOTE` | 10 | core/narrative/event_promoter.py:37 | per-run cap (rate-limit; no Beat flood) |
| `DEFAULT_THRESHOLD` | 3 | core/narrative/event_promoter.py:36 | salience >= this is worth a Beat |
| `DEFAULT_TOKEN_BUDGET` | 4,000 | core/primitives/consolidator.py:31 |  |
| `DEFAULT_TRACE_SPOT_INTERVAL` | 1,000 | core/comm/packet_spec.py:212 |  |
| `DEFAULT_TTL` | 900 | core/comm/locks.py:35 | 15 min -- long enough for a slice, short enough to self-heal a crash |
| `DEFAULT_TTL` | 900 | core/coord/intent.py:37 | 15 min -- long enough for a slice, self-heals a crash (mirrors locks) |
| `DEFAULT_WINDOW_SECONDS` | 1,800 | core/narrative/event_bridge.py:22 | +/- 30 min around a point (Beat / timestamp) |
| `DIRECTIVE_STALE_DAYS` | 3 | agent_cli.py:1237 | W04: a directive older than this confesses its age at boot |
| `DRAIN_FLUSH_JOIN_SEC` | 2 | core/comm/launcher.py:218 |  |
| `DRAIN_TTL_S` | 300 | core/comm/control.py:83 |  |
| `EVENT_SCAN_LIMIT` | 5,000 | core/recall/funnel.py:35 |  |
| `FLOOR_CHARS` | 15 | scripts/bifrost_runner_deepseek.py:241 |  |
| `FORGE_WATCH_MIN_IMPRESSIONS` | 8 | core/recall/curator.py:58 | ...or this many fresh impressions, whichever first |
| `FRESH_MIN_DEFAULT` | 30 | core/comm/wake_seat.py:33 | AKASHIC_WAKE_MARKER_FRESH_MIN overrides |
| `GIT_CAP` | 10 | agent/harness/delta.py:31 | commits listed before the pull pointer takes over |
| `HEADING_MIN` | 2 | scripts/checkers/check_bus_atom_pointers.py:36 | markdown headings that make a body design-shaped |
| `HINT_MAX_PER_AGENT` | 8 | core/comm/context_hints.py:36 | ring buffer cap per receiving agent |
| `HINT_TTL_SECONDS` | 300 | core/comm/context_hints.py:37 | 5 min soft expiry (stale hints silently dropped by drain) |
| `HISTORY_CAP` | 200 | core/comm/turn_metrics.py:35 |  |
| `LINE_BUDGET` | 120 | core/coord/task_costs.py:25 |  |
| `MAX_BODY` | 240 | core/toolbelt/contest.py:45 | a second voice is shorter than the first; chorus, not solo. |
| `MAX_BODY` | 400 | core/toolbelt/toast.py:31 | gratitude is short; the leaderboard guard is distinct-users love |
| `MAX_CHARS_PER_ENTRY` | 170 | core/narrative/chronicler.py:123 |  |
| `MAX_CMD_OUT` | 16,000 | core/comm/toolbox.py:45 |  |
| `MAX_FILE_BYTES` | 120,000 | core/comm/toolbox.py:42 |  |
| `MAX_LIST` | 400 | core/comm/toolbox.py:44 |  |
| `MAX_MATCHES` | 120 | core/comm/toolbox.py:43 |  |
| `MAX_REFLECTIONS` | 50 | core/learning/agent_memory.py:150 | keep only the newest N reflections in the index |
| `MAX_TARGETS_PER_PASS` | 2 | core/recall/forge_optimizer.py:24 | locked design decision 1 |
| `MAX_TOOL_ROUNDS` | 30 | scripts/deepseek_chat.py:87 |  |
| `MIN_BEATS` | 2 | core/narrative/episode_suggester.py:55 | a thin episode has nothing worth bookending |
| `MIN_N` | 3 | core/comm/turn_metrics.py:36 |  |
| `MIN_SPAN_S` | 300 | core/narrative/episode_suggester.py:54 | a just-opened episode never suggests (anti rapid-fire after each close) |
| `MIN_WITHIN_S` | 30 | core/comm/expectations.py:69 | clamp floor: sub-30s reply deadlines on a turn-based bus are noise |
| `NUDGE_TTL` | 120 | core/comm/nudge.py:41 | a nudge auto-expires so a missed pick-up never sticks |
| `OUTCOME_MAXLEN` | 20,000 | core/recall/at_action.py:88 |  |
| `PER_AGENT_MAXLEN` | 10,000 | core/events/event_log.py:44 | per-agent: a shallower convenience index |
| `PER_AGENT_MAXLEN` | 10,000 | core/signals/agent_signal_ledger.py:51 | signals retained per agent stream |
| `PER_STREAM_LIMIT` | 400 | core/comm/flow_trace.py:30 | bounded read per stream; the window trims harder |
| `PORT_TEST_UI_MAX` | 8,999 | config.py:58 | last test-UI port. A test UI MUST live in [8900, 8999]. |
| `PRESENCE_TTL` | 90 | core/comm/bus.py:38 | seconds an agent is considered "online" after its last activity |
| `PROPOSAL_TTL` | 60 | core/coord/intent.py:138 | proposal records auto-expire after a minute |
| `REDIS_TIMEOUT` | 5 | config.py:23 |  |
| `REHAB_MIN_CONTEXTS` | 8 | core/recall/replay.py:27 | criterion 2: surfaced contexts per rehab candidate... |
| `REHAB_MIN_SURFACED` | 10 | core/recall/forge_optimizer.py:26 | rehab class definition (mirrors the audit / curator) |
| `RENDER_TTL_S` | 30 | agent/harness/delta.py:30 | X1: turn_metrics EST_CACHE_TTL pattern |
| `SCHEMA_KNOWN_MAX` | 1 | core/library/atoms.py:39 |  |
| `SEEN_CAP` | 1,000 | scripts/bifrost_wake.py:181 | newest-last trim on save; a session outliving 1000 wakes re-earns a twin wake |
| `SNIPPET_CHARS` | 72 | core/comm/flow_trace.py:31 |  |
| `STALE_DAYS` | 14 | scripts/checkers/check_comprehensibility.py:35 |  |
| `STALE_PROPOSED_DAYS` | 7 | core/coord/task_ledger.py:281 | default; render callers may override via env AKASHIC_PROPOSED_STALE_DAYS |
| `STEER_TTL` | 900 | core/comm/nudge.py:42 | a queued steer that's never picked up self-expires after 15 min |
| `SURFACE_MAXLEN` | 6,000 | core/recall/at_action.py:77 |  |
| `TF_LEN_UNIT` | 4,000 | core/recall/lookback.py:46 | chars of text per EXPECTED occurrence of a matched stem: a 12KB doc |
| `THRESHOLD` | 1,500 | scripts/checkers/check_bus_atom_pointers.py:35 | chars: below this a body is "a pointer with manners" |
| `TOKEN_BUDGET` | 4,000 | core/narrative/chronicler.py:122 |  |
| `TOOL_SEND_TEXT_MAX` | 8,000 | core/comm/packet_spec.py:331 | D3 (deepseek verdict 2026-07-19): the 4000 door |
| `WINDOW` | 240 | scripts/checkers/check_pointer_promises.py:95 |  |
| `_ANSWERED_KEY_CAP` | 20,000 | core/comm/mailbox.py:43 |  |
| `_CAP_MAX` | 200 | agent/harness/capture.py:17 |  |
| `_CAP_STR` | 400 | agent/harness/capture.py:18 |  |
| `_CTX_FLOOR` | 32,000 | core/fleet/caller.py:29 |  |
| `_DEFAULT_BUDGET_LINES` | 12 | agent/harness/context.py:42 | W6; AKASHIC_WHISPER_LINES overrides (R6) |
| `_DONE_CAP` | 8,192 | core/comm/packet_spec.py:476 |  |
| `_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION` | 9 | scripts/run_job.py:301 |  |
| `_MAX` | 4,000 | agent_cli.py:47 | clamp absurdly long fields an agent might paste |
| `_MAX_DETAIL_CHARS` | 8,000 | core/events/event_log.py:50 | raw is rich, but a single payload is still bounded |
| `_MAX_NOTE` | 100,000 | agent_cli.py:58 | durable note bodies: a ceiling against runaway pastes, not a working size |
| `_MAX_SUMMARY` | 500 | core/events/event_log.py:49 |  |
| `_NOTE_WINDOW_DAYS` | 60 | agent/harness/context.py:43 | one store pull feeds every note-derived section |
| `_RECYCLE_SLACK_MS` | 1,000 | core/comm/wake_seat.py:34 | parent may not be YOUNGER than child by more |
| `_SHA_LEN` | 24 | core/comm/blobs.py:24 | 96 bits of sha256 -- ample for a single-user blob store |
| `_STALE_DAYS` | 7 | agent/harness/context.py:39 | W5: note-derived lines gain [STALE] at this age |
| `_SWITCH_MIN_BEATS` | 2 | core/narrative/episode_suggester.py:58 | ...and needs >=2 of them, unanimous, on a non-episode track |
| `_SWITCH_WINDOW` | 3 | core/narrative/episode_suggester.py:57 | switch looks at the last N routed beats... |
| `_THEMES_MAX_DAYS` | 30 | agent/harness/context.py:40 | R2: themes older than this stay off the whisper |
