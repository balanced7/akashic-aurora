# PHYSICS -- mechanical truths of the machinery (auto-generated)

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_physics_sheet.py`.
> Derived at 9abc1a54. A bound you discover by collision is not awareness -- this sheet
> exists so every clip, cap, timeout and flag is READABLE before it is HIT.
> Dynamic envelopes (throughput, latency, limits-under-load) are NOT here: they require
> measurement, not grep -- see the master-map charter M2b (benchmark half).

## Configuration flags (255 names)

| Flag | Default (as written) | Read sites |
|---|---|---|
| `AGENT_ID` | `"unknown"` | core/comm/bus.py |
| `AI_SETUP` | `"E:\\AI-Setup"` | agent_cli.py, core/comm/blobs.py, core/foundation/durable_reconcile.py +13 |
| `AI_SETUP_ROOT` | `` | research/in-flight/t342/dead-modules/_archive__python_old__launch_ai_stack.py |
| `AI_STACK_CHAT_URL` | `"http://127.0.0.1:3000"` | research/in-flight/t342/dead-modules/_archive__python_old__launch_ai_stack.py |
| `AI_STACK_GUI_URL` | `"http://127.0.0.1:8090"` | research/in-flight/t342/dead-modules/_archive__python_old__launch_ai_stack.py |
| `AI_VOICE_URL` | `"http://127.0.0.1:5000"` | research/in-flight/t342/dead-modules/_archive__python_old__stack_gui.py |
| `AI_WATCHDOG_INTERVAL` | `"45"` | research/in-flight/t342/dead-modules/_archive__python_old__ai_watchdog.py |
| `AKASHIC_ACK_UNHANDLED_HOURS` | `UNHANDLED_HOURS` | core/comm/promoter.py |
| `AKASHIC_ACL_PATH` | `` | core/trust/registry.py |
| `AKASHIC_ADJUDICATORS` | `""` | core/fleet/verdicts.py |
| `AKASHIC_AGENT_ID` | `"dsh_agent"` | agent/harness/actions.py, agent/harness/dsh_plugin/bridge.py, agent/harness/hooks/_activity.py +29 |
| `AKASHIC_ALLOW_HARMONIZE` | `` | scripts/harmonize_knowledge.py |
| `AKASHIC_APP_PACKAGE` | `"Claude"` | core/fleet/app_package.py |
| `AKASHIC_ASK_BASE_URL` | `"https://api.deepseek.com"` | core/comm/ask.py |
| `AKASHIC_ASK_BG_ORPHAN_S` | `"1800"` | core/comm/ask_bg.py |
| `AKASHIC_ASK_COLLAPSE_AT` | `"0.85"` | core/comm/ask.py |
| `AKASHIC_ASK_CONTEXT_CHARS` | `"40000"` | core/comm/ask.py |
| `AKASHIC_ASK_DISTINCT_AT` | `"0.05"` | core/comm/ask.py |
| `AKASHIC_ASK_EXPECT_S` | `"1800"` | agent_cli.py |
| `AKASHIC_ASK_FAN_WORKERS` | `"6"` | core/comm/ask.py |
| `AKASHIC_ASK_MAX_TOKENS` | `"0"` | core/comm/ask.py |
| `AKASHIC_ASK_MODEL` | `"deepseek-v4-pro"` | core/comm/ask.py |
| `AKASHIC_AUTOBOOT` | `"1"` | agent/harness/context.py |
| `AKASHIC_BENCH_PROBE_DAYS` | `"14"` | core/recall/at_action.py |
| `AKASHIC_BENCH_PROBE_MAX` | `"3"` | core/recall/at_action.py |
| `AKASHIC_BIRTH_GUARD` | `""` | research/in-flight/t342/dead-modules/scripts__hooks__birth_guard.py, scripts/githooks/birth_guard.py |
| `AKASHIC_BOOT_FULL` | `"0"` | agent_cli.py |
| `AKASHIC_CALLSIGN_HINT` | `` | agent/harness/codex_bifrost_wake.py |
| `AKASHIC_CALLSIGN_STATUS` | `` | agent/harness/codex_bifrost_wake.py |
| `AKASHIC_CB_MAX` | `"3"` | scripts/bifrost_daemon.py |
| `AKASHIC_CB_WINDOW_S` | `"300"` | scripts/bifrost_daemon.py |
| `AKASHIC_CHAPTERS_FILE` | `` | scripts/corpus_digests.py |
| `AKASHIC_CLAUDE_CREDENTIALS` | `` | scripts/bifrost_runner_discord.py |
| `AKASHIC_CLEAN_DEATH` | `"1"` | core/comm/session_exit.py |
| `AKASHIC_CODEX_BINARY` | `` | agent/harness/codex_app_server.py |
| `AKASHIC_CONDUCTOR_SUCCESSORS` | `",".join(SUCCESSION_ORDER` | core/comm/conductor_gate.py |
| `AKASHIC_CONTROL_PORT_BASE` | `"47100"` | core/comm/control_channel.py |
| `AKASHIC_DAEMON_WAKE` | `"1"` | agent/harness/hooks/claude_stop.py, scripts/hooks/claude_stop.py |
| `AKASHIC_DEBUG` | `` | agent/harness/hooks/claude_userpromptsubmit.py, scripts/hooks/claude_userpromptsubmit.py |
| `AKASHIC_DIGESTS_FILE` | `` | scripts/corpus_digests.py |
| `AKASHIC_DISCORD_BOT_TOKEN` | `` | core/comm/discord_rooms.py, scripts/bifrost_runner_discord.py, scripts/discord_setup.py |
| `AKASHIC_DISCORD_FORUM_WEBHOOK` | `` | core/comm/discord_rooms.py |
| `AKASHIC_DISCORD_GATEWAY_LOG` | `` | agent_cli.py, scripts/bifrost_runner_discord.py |
| `AKASHIC_DISCORD_OPERATOR_ID_FILE` | `` | core/comm/discord_inbound.py |
| `AKASHIC_DISCORD_PEOPLE_FILE` | `` | core/comm/discord_inbound.py |
| `AKASHIC_DISCORD_ROOMS_REGISTRY` | `` | core/comm/discord_rooms.py |
| `AKASHIC_DISCORD_ROOTS_FILE` | `` | core/comm/discord_inbound.py |
| `AKASHIC_DISCORD_SEATS_REGISTRY` | `` | core/comm/discord_inbound.py, core/comm/discord_rooms.py |
| `AKASHIC_DISCORD_WEBHOOK` | `` | agent_cli.py, core/comm/discord_bridge.py |
| `AKASHIC_DRILL_ECHO` | `` | scripts/bifrost_runner.py, scripts/bifrost_runner_deepseek.py, scripts/bifrost_runner_gemini.py +2 |
| `AKASHIC_EMBED_THEMES` | `""` | core/narrative/beat_log.py, core/narrative/theme_discovery.py |
| `AKASHIC_EXPECT_TASK_SETTLE` | `"1"` | core/comm/expectations.py |
| `AKASHIC_FENCE_ROOT` | `` | core/coord/fence_workspace.py |
| `AKASHIC_FLOW_NO_COUNT` | `` | core/comm/flow_trace.py |
| `AKASHIC_GATE_NO_CEILING` | `` | scripts/checkers/check_reconciliation_gate.py |
| `AKASHIC_HEAL_VERBOSE` | `` | agent_cli.py |
| `AKASHIC_INCARNATION_TTL_MIN` | `"30"` | core/comm/incarnation.py |
| `AKASHIC_JOB_ENFORCEMENT` | `` | scripts/run_job.py |
| `AKASHIC_JOB_OBJECT_NAME` | `` | scripts/run_job.py |
| `AKASHIC_KILLPOINT` | `""` | scripts/bifrost_runner_deepseek.py, scripts/bifrost_runner_gemini.py, scripts/bifrost_runner_kimi.py +1 |
| `AKASHIC_KIMI_NARRATOR` | `"1"` | scripts/kimi_walk_narrator.py |
| `AKASHIC_KMAP_NO_COUNT` | `` | core/recall/knowledge_map.py |
| `AKASHIC_LANE_STALL_PAGE_S` | `"21600"` | core/comm/doctor.py |
| `AKASHIC_LANE_STALL_WARN_S` | `"3600"` | core/comm/doctor.py |
| `AKASHIC_LEARN_NUDGE` | `"1"` | agent/harness/nudge.py |
| `AKASHIC_LEARN_NUDGE_CAP` | `"3"` | agent/harness/nudge.py |
| `AKASHIC_LENS_LEDGER` | `""` | core/coord/lens_ledger.py |
| `AKASHIC_LOOKBACK_NO_COUNT` | `` | core/recall/lookback.py |
| `AKASHIC_MAILBOX` | `"1"` | core/comm/mailbox.py |
| `AKASHIC_MCP_DIAG` | `` | ai_setup_mcp.py |
| `AKASHIC_OPERATOR_IDS` | `OPERATOR_IDS_DEFAULT` | core/comm/conductor_gate.py, scripts/bifrost_wake.py |
| `AKASHIC_PAYLOAD_CAPTURE` | `"1"` | agent/harness/capture.py |
| `AKASHIC_PLAN_RECALL` | `"1"` | agent/harness/actions.py, scripts/hooks/claude_userpromptsubmit.py |
| `AKASHIC_PLAY_NETWORK` | `"0"` | core/toolbelt/play_sandbox.py |
| `AKASHIC_PLAY_OUTPUT_MAX` | `"65536"` | core/toolbelt/play_sandbox.py |
| `AKASHIC_PLAY_TIMEOUT_S` | `"30"` | core/toolbelt/play_sandbox.py |
| `AKASHIC_PORTS_NO_DOCKER` | `` | scripts/checkers/check_ports.py |
| `AKASHIC_PROPOSED_STALE_DAYS` | `stale_days` | core/coord/task_ledger.py |
| `AKASHIC_RECALL_AT_ACTION` | `"1"` | agent/harness/actions.py, agent/harness/hooks/claude_posttooluse.py, agent/harness/hooks/cursor_posttooluse.py +3 |
| `AKASHIC_RECALL_CACHE_TTL` | `"120"` | core/recall/at_action.py |
| `AKASHIC_RECALL_FLOOR` | `"0.20"` | core/recall/at_action.py |
| `AKASHIC_RECALL_SELF_ECHO_H` | `"2"` | core/recall/at_action.py |
| `AKASHIC_RECALL_STATE_DIR` | `` | agent/harness/actions.py, agent/harness/hooks/claude_posttooluse.py, agent/harness/hooks/claude_sessionend.py +14 |
| `AKASHIC_RECENT_INBOX_S` | `str(12 * 3600` | core/comm/doctor.py |
| `AKASHIC_REDIS_HEALTH_CHECK_SEC` | `"30"` | core/foundation/redis_connection.py |
| `AKASHIC_REDIS_HOST` | `"localhost"` | scripts/checkers/check_field_parity.py |
| `AKASHIC_REDIS_PORT` | `16379` | scripts/checkers/check_field_parity.py |
| `AKASHIC_RELEVANCE_BUDGET` | `"1"` | core/context/learning_loader.py, research/in-flight/t342/dead-modules/context__learning_loader.py |
| `AKASHIC_RELEVANCE_BUDGET_CHARS` | `""` | core/context/relevance_budget.py, research/in-flight/t342/dead-modules/context__relevance_budget.py |
| `AKASHIC_REMOTE_BRIDGE_PEER_URL` | `` | core/comm/remote_relay.py |
| `AKASHIC_REPO` | `` | agent/harness/dsh_plugin/bridge.py |
| `AKASHIC_RESTORE_PROD` | `` | scripts/ops/snapshot_knowledge.py |
| `AKASHIC_RESUME_GAP_S` | `"600"` | core/comm/roster.py |
| `AKASHIC_ROSTER_CHURN_AT` | `"3"` | core/comm/roster.py |
| `AKASHIC_ROSTER_CHURN_WINDOW_S` | `"3600"` | core/comm/roster.py |
| `AKASHIC_ROUTE_JOURNAL` | `""` | core/comm/ask.py |
| `AKASHIC_RUN_EXPECTATION` | `` | core/comm/failsafe.py |
| `AKASHIC_SEAT_DOOR` | `""` | agent_cli.py |
| `AKASHIC_SEAT_DOOR_DETAIL` | `""` | agent_cli.py |
| `AKASHIC_SEAT_HEARTBEAT` | `"1"` | agent/harness/hooks/claude_posttooluse.py, agent/harness/hooks/claude_stop.py, scripts/hooks/claude_posttooluse.py +1 |
| `AKASHIC_SECRETS_DIR` | `` | core/comm/secret_intake.py, peer_connect.py |
| `AKASHIC_SELF_RESTART_MIN_BEHIND` | `"3"` | core/comm/self_restart.py |
| `AKASHIC_SELF_RESTART_MIN_UPTIME_S` | `"900"` | core/comm/self_restart.py |
| `AKASHIC_SESSION8` | `` | agent_cli.py |
| `AKASHIC_SESSION_SIGNALS` | `"1"` | agent/harness/dsh_plugin/bridge.py, agent/harness/hooks/claude_sessionend.py, scripts/hooks/claude_sessionend.py |
| `AKASHIC_SESSION_SIGNALS_MAX_BYTES` | `str(16 * 1024 * 1024` | agent/harness/hooks/claude_sessionend.py, scripts/hooks/claude_sessionend.py |
| `AKASHIC_SHIFT_LOOP` | `"1"` | core/comm/shift_turn.py |
| `AKASHIC_SHOW_CONSOLES` | `` | core/__init__.py, core/comm/launcher.py, scripts/quiet/sitecustomize.py |
| `AKASHIC_SPAWN_INSTANT_SECONDS` | `` | scripts/bifrost_runner_discord.py |
| `AKASHIC_SPAWN_PROOF_SECONDS` | `` | scripts/bifrost_runner_discord.py |
| `AKASHIC_SPAWN_REPORT_DEADLINE` | `` | scripts/bifrost_runner_discord.py |
| `AKASHIC_SPILL_DIR` | `` | agent_cli.py |
| `AKASHIC_STALE_CUE_DAYS` | `"30"` | core/recall/at_action.py |
| `AKASHIC_STALL_HYSTERESIS_S` | `"180"` | core/comm/doctor.py |
| `AKASHIC_STOP_PROMISE` | `"1"` | agent/harness/hooks/claude_stop.py, scripts/hooks/claude_stop.py |
| `AKASHIC_STOP_WAKE` | `"1"` | agent/harness/hooks/claude_stop.py, scripts/hooks/claude_stop.py |
| `AKASHIC_STORE_BACKEND` | `""` | core/foundation/store.py, scripts/checkers/check_dual_authority.py |
| `AKASHIC_TASKS_PATH` | `` | core/coord/task_ledger.py |
| `AKASHIC_TEST_SHOW_CONSOLES` | `` | core/__init__.py, scripts/quiet/sitecustomize.py |
| `AKASHIC_TIMELINE_FILE_LIMIT` | `"4000"` | core/coord/timeline.py |
| `AKASHIC_TIMEOUT_MULTIPLIER` | `"1"` | core/comm/timescale.py |
| `AKASHIC_TOMBSTONE` | `"1"` | core/comm/wake_seat.py |
| `AKASHIC_TOOLBELT_QUOTA` | `"20"` | core/toolbelt/registry.py |
| `AKASHIC_TRACE` | `"1"` | agent/harness/hooks/claude_trace.py, agent/harness/trace.py, scripts/hooks/claude_trace.py |
| `AKASHIC_TRANSCRIPT_TAIL_BYTES` | `str(4 * 1024 * 1024` | agent/harness/hooks/claude_posttooluse.py, scripts/hooks/claude_posttooluse.py |
| `AKASHIC_UI_URL` | `"http://localhost:8787"` | scripts/ui_shot.py |
| `AKASHIC_UNATTENDED_S` | `"300"` | core/comm/bus.py, core/comm/liveness.py |
| `AKASHIC_VERB_FLOOR` | `"0.9"` | core/recall/at_action.py |
| `AKASHIC_WAKE_MARKER_FRESH_MIN` | `""` | core/comm/wake_seat.py |
| `AKASHIC_WHISPER_LINES` | `""` | agent/harness/context.py |
| `AKASHIC_WIRE` | `"1"` | scripts/deepseek_chat.py, scripts/wire_journal.py |
| `AKASHIC_WIRE_DIR` | `` | scripts/wire_journal.py |
| `AKASHIC_WIRE_MAX_BYTES` | `str(8 * 1024 * 1024` | scripts/wire_journal.py |
| `AKASHIC_WIRE_MAX_FILES` | `"14"` | scripts/wire_journal.py |
| `AKASHIC_WIRE_MAX_SHARDS` | `"64"` | scripts/wire_journal.py |
| `AKASHIC_WIRE_QUEUE` | `"4096"` | scripts/wire_journal.py |
| `AKASHIC_WIRE_WRITER` | `` | scripts/wire_journal.py |
| `AKASHIC_WISHLIST_FILE` | `` | agent_cli.py |
| `AKASHIC_WORKLIVE_FRESH_S` | `"45"` | core/comm/roster.py |
| `AKASHIC_WORKLIVE_TTL_S` | `"180"` | core/comm/roster.py |
| `BIFROST_AGENT` | `` | scripts/wire_journal.py |
| `BIFROST_AGENT_ID` | `` | core/comm/conductor_gate.py |
| `BIFROST_APPROACHING_WEDGE_SECONDS` | `"150"` | core/comm/liveness.py |
| `BIFROST_CONSUME_LANE` | `` | core/comm/bifrost_api.py, scripts/bifrost_runner_deepseek.py, scripts/bifrost_runner_kimi.py +1 |
| `BIFROST_INCARNATION` | `` | agent/bifrost_pull.py, agent/harness/hooks/claude_posttooluse.py, agent_cli.py +8 |
| `BIFROST_LANES_DUAL_WRITE` | `True` | core/comm/packet_spec.py |
| `BIFROST_MAX_HOPS` | `"6"` | core/comm/control.py |
| `BIFROST_MAX_REPLIES_PER_MIN` | `"12"` | core/comm/control.py, scripts/bifrost_runner_deepseek.py |
| `BIFROST_NAMESPACE` | `_DEFAULT_NS` | agent/bifrost_pull.py, agent/harness/delta.py, agent/harness/dsh_plugin/bridge.py +33 |
| `BIFROST_PREFLIGHT_ASSERT` | `"1"` | core/comm/assertions.py |
| `BIFROST_PREMISE_GATE_MIN_AGE_MS` | `` | core/coord/task_ledger.py |
| `BIFROST_REASK_WINDOW_S` | `` | core/comm/bus.py |
| `BIFROST_REPLY_DEDUP_TTL_S` | `"1200"` | core/comm/bus.py |
| `BIFROST_STALE_MS` | `DEFAULT_STALE_MS` | core/comm/packet_spec.py |
| `BIFROST_UI_PORT` | `"8787"` | core/comm/doctor.py |
| `BIFROST_WAKE_DEADLINE_S` | `""` | scripts/bifrost_wake.py |
| `BIFROST_WAKE_LANE` | `"work"` | agent_cli.py, core/comm/bifrost_api.py |
| `BIFROST_WAKE_LONGLIVED` | `"1"` | scripts/bifrost_wake.py |
| `BIFROST_WEDGE_SECONDS` | `"300"` | core/comm/liveness.py |
| `BUS_MAX_MESSAGE_BYTES` | `DEFAULT_MAX_MESSAGE_BYTES` | core/comm/packet_spec.py |
| `CLAUDE_CODE_SESSION_ID` | `""` | agent/bifrost_pull.py, agent/harness/hooks/claude_posttooluse.py, agent_cli.py +4 |
| `CLAUDE_SESSION_ID` | `` | agent_cli.py, core/comm/runner_lock.py |
| `CURSOR_PROJECT_DIR` | `` | agent/harness/hooks/cursor_posttooluse.py, agent/harness/hooks/cursor_sessionstart.py, research/in-flight/t342/dead-modules/scripts__hooks__cursor_posttooluse.py +1 |
| `DEEPSEEK_API_KEY` | `` | core/comm/ask.py, scripts/ask_deepseek.py, scripts/deepseek_chat.py |
| `DEEPSEEK_CONNECT_TIMEOUT` | `"15"` | scripts/deepseek_chat.py |
| `DEEPSEEK_MAX_CMD_TIMEOUT` | `"300"` | core/comm/toolbox.py |
| `DEEPSEEK_MAX_RETRIES` | `"1"` | scripts/deepseek_chat.py |
| `DEEPSEEK_MAX_TOOL_RESULT_CHARS` | `"20000"` | scripts/deepseek_chat.py |
| `DEEPSEEK_MAX_TOOL_ROUNDS` | `"0"` | scripts/deepseek_chat.py |
| `DEEPSEEK_MODEL` | `"deepseek-v4-pro"` | scripts/ask_deepseek.py |
| `DEEPSEEK_READ_TIMEOUT` | `"120"` | scripts/deepseek_chat.py |
| `DEEPSEEK_RECALL_AT` | `` | core/comm/toolbox.py, scripts/bifrost_runner_deepseek.py |
| `DEEPSEEK_RUNNER_MAX_TOKENS` | `"8000"` | scripts/bifrost_runner_deepseek.py |
| `DOC_CURRENCY_STALE_DAYS` | `"45"` | scripts/checkers/check_doc_currency.py |
| `DSH_HOME` | `` | agent/harness/dsh_plugin/bridge.py, core/fleet/seat_launchers.py, scripts/install_dsh_plugin.py |
| `DSH_SESSION_ID` | `` | seat_topology.py |
| `EMBED_MODEL` | `DEFAULT_MODEL` | core/primitives/embedder.py |
| `ENABLE_X` | `` | scripts/checkers/check_wiring.py |
| `FRAG_REASSEMBLY_TTL` | `DEFAULT_FRAG_REASSEMBLY_TTL` | core/comm/packet_spec.py |
| `GEMINI_API_KEY` | `""` | research/in-flight/t342/dead-modules/_archive__python_old__escalation.py |
| `GEMINI_BUDGET_USD` | `"105.0"` | scripts/gemini_chat.py |
| `GEMINI_CONNECT_TIMEOUT` | `"15"` | scripts/gemini_chat.py |
| `GEMINI_EFFORT` | `"max"` | scripts/gemini_chat.py |
| `GEMINI_GRANT_BASIS_USD` | `"105.0"` | scripts/gemini_chat.py |
| `GEMINI_MAX_HOPS` | `"30"` | scripts/bifrost_runner_gemini.py, scripts/gemini_chat.py |
| `GEMINI_MAX_RETRIES` | `"1"` | scripts/gemini_chat.py |
| `GEMINI_MODEL` | `"gemini-2.5-flash"` | scripts/ask_gemini.py, scripts/ask_gemini_vision.py, scripts/gemini_chat.py |
| `GEMINI_READ_TIMEOUT` | `"180"` | scripts/gemini_chat.py |
| `GEMINI_RUNNER_MAX_TOKENS` | `"8000"` | scripts/gemini_chat.py |
| `GEMINI_SPEND_FILE` | `str(REPO_ROOT / "state" / "gemini_spend.json"` | scripts/gemini_chat.py |
| `GEMINI_SPEND_REFUSE` | `'95'` | scripts/bifrost_runner_gemini.py, scripts/gemini_chat.py |
| `GEMINI_SPEND_WARN` | `"80.0"` | scripts/gemini_chat.py |
| `GEMINI_WEB_BROWSER` | `""` | scripts/gemini_web.py |
| `GEMINI_WEB_ENGINE` | `"playwright"` | scripts/gemini_web.py |
| `GEMINI_WEB_HEADED` | `""` | scripts/gemini_web.py |
| `GEMINI_WEB_PATCHRIGHT_CHANNEL` | `""` | scripts/gemini_web.py |
| `GEMINI_WEB_STEALTH` | `"1"` | scripts/gemini_web.py |
| `GEMINI_WEB_TIMEOUT_MS` | `"120000"` | scripts/gemini_web.py |
| `GEMINI_WEB_TZ` | `"America/New_York"` | scripts/gemini_web.py |
| `GEMMA_URL` | `"http://localhost:5000"` | research/in-flight/t342/dead-modules/_archive__python_old__health_check_session_pipeline.py |
| `KIMI_API_KEY` | `` | scripts/kimi_chat.py |
| `KIMI_BASE_URL` | `"https://api.moonshot.ai/v1"` | core/comm/ask.py |
| `KIMI_BUDGET_USD` | `"105.0"` | scripts/kimi_chat.py |
| `KIMI_CLAUDE_HOME` | `` | scripts/kimi_walk_narrator.py |
| `KIMI_CONNECT_TIMEOUT` | `"15"` | scripts/kimi_chat.py |
| `KIMI_EFFORT` | `"max"` | scripts/kimi_chat.py |
| `KIMI_GRANT_BASIS_USD` | `"105.0"` | scripts/kimi_chat.py |
| `KIMI_MAX_HOPS` | `"30"` | scripts/bifrost_runner_kimi.py, scripts/kimi_chat.py |
| `KIMI_MAX_RETRIES` | `"1"` | scripts/kimi_chat.py |
| `KIMI_MODEL` | `K3` | scripts/kimi_chat.py |
| `KIMI_READ_TIMEOUT` | `"180"` | core/comm/ask.py, scripts/kimi_chat.py |
| `KIMI_RUNNER_MAX_TOKENS` | `"8000"` | scripts/kimi_chat.py |
| `KIMI_SPEND_FILE` | `str(REPO_ROOT / "state" / "kimi_spend.json"` | scripts/kimi_chat.py |
| `KIMI_SPEND_REFUSE` | `'95'` | scripts/bifrost_runner_kimi.py, scripts/kimi_chat.py |
| `KIMI_SPEND_WARN` | `"80.0"` | scripts/kimi_chat.py |
| `LAUNCHER_AUTO_REVIVE_JITTER` | `"4"` | core/comm/launcher.py |
| `LAUNCHER_RESTART_BACKOFF` | `"3"` | core/comm/launcher.py |
| `LAUNCHER_RESTART_BACKOFF_MAX` | `"60"` | core/comm/launcher.py |
| `LAUNCHER_RESTART_MAX` | `"5"` | core/comm/launcher.py |
| `LAUNCHER_RESTART_RESET` | `"300"` | core/comm/launcher.py |
| `LD_LIBRARY_PATH` | `''` | research/in-flight/t342/dead-modules/test_gpu_pytorch.py, research/in-flight/t342/dead-modules/test_torch.py |
| `LOCALAPPDATA` | `` | agent/harness/codex_app_server.py, agent/harness/codex_bifrost_wake.py |
| `OLLAMA_URL` | `"http://localhost:11434"` | research/in-flight/t342/dead-modules/_archive__python_old__gemma_voice_service.py, research/in-flight/t342/dead-modules/_archive__python_old__stack_gui.py |
| `OPENAI_API_KEY` | `` | scripts/ask_gpt.py |
| `OPENAI_MODEL` | `"gpt-5"` | scripts/ask_gpt.py |
| `OPENCODE_AGENT_ROLE` | `'generator'` | research/in-flight/t342/dead-modules/agent_coordinator.py, research/in-flight/t342/dead-modules/agent_coordinator_v2.py, research/in-flight/t342/dead-modules/init_session.py |
| `OPENCODE_API_KEY` | `""` | research/in-flight/t342/dead-modules/_archive__python_old__escalation.py |
| `OPENCODE_SESSION` | `f"session_{time.strftime('%Y%m%d_%H%M%S'` | research/in-flight/t342/dead-modules/screenshot_logger.py |
| `OPENCODE_SESSION_ID` | `f"session_{datetime.now(` | research/in-flight/t342/dead-modules/agent_coordinator.py |
| `PACKET_INTEGRITY_ENABLED` | `True` | core/comm/packet_spec.py |
| `PACKET_INTEGRITY_TRACE` | `False` | core/comm/packet_spec.py |
| `PACKET_TRACE_SPOT_INTERVAL` | `DEFAULT_TRACE_SPOT_INTERVAL` | core/comm/packet_spec.py |
| `PYTEST_CURRENT_TEST` | `` | core/comm/bus.py, scripts/ops/archive_transcripts.py |
| `PYTHONPATH` | `""` | agent_cli.py, core/__init__.py, scripts/quiet/sitecustomize.py |
| `REDIS_DB` | `` | core/foundation/redis_connection.py |
| `REDIS_HOST` | `"localhost"` | core/foundation/redis_connection.py, research/in-flight/t342/dead-modules/_archive__python_old__gemma_voice_service.py, scripts/ops/archive_ephemeral.py |
| `REDIS_PASSWORD` | `""` | research/in-flight/t342/dead-modules/deployment_framework.py |
| `REDIS_PORT` | `"6379"` | core/foundation/redis_connection.py, research/in-flight/t342/dead-modules/_archive__python_old__gemma_voice_service.py, scripts/ops/archive_ephemeral.py |
| `ROCM_PATH` | `` | research/in-flight/t342/dead-modules/test_torch.py |
| `SESSION_EVENTS_STREAM_FROM` | `"$"` | research/in-flight/t342/dead-modules/_archive__legacy__session_compressor.py |
| `SESSION_STREAM_BLOCK_MS` | `"4000"` | research/in-flight/t342/dead-modules/_archive__legacy__session_compressor.py |
| `SESSION_SUMMARY_DEBOUNCE` | `"18"` | research/in-flight/t342/dead-modules/_archive__legacy__session_compressor.py |
| `SOL_401_RETRIES` | `"3"` | scripts/sol_chat.py |
| `SOL_CONNECT_TIMEOUT` | `"15"` | scripts/sol_chat.py |
| `SOL_EFFORT` | `"medium"` | scripts/sol_chat.py |
| `SOL_MAX_HOPS` | `"30"` | scripts/bifrost_runner_sol.py, scripts/sol_chat.py |
| `SOL_MAX_RETRIES` | `"1"` | scripts/sol_chat.py |
| `SOL_MODEL` | `SOL` | scripts/sol_chat.py |
| `SOL_READ_TIMEOUT` | `"120"` | scripts/sol_chat.py |
| `SOL_RUNNER_MAX_TOKENS` | `"8000"` | scripts/sol_chat.py |
| `SOL_VERBOSITY` | `"medium"` | scripts/sol_chat.py |
| `STORM_DEPTH_THRESHOLD` | `50` | core/comm/storm_detect.py |
| `STORM_DEPTH_WINDOW` | `3` | core/comm/storm_detect.py |
| `STORM_REPEAT_THRESHOLD` | `5` | core/comm/storm_detect.py |
| `TEMP` | `"/tmp"` | core/recall/precision_audit.py, scripts/ops/archive_transcripts.py |

## Mechanical bounds (154 numeric constants)

| Constant | Value | Site | Note |
|---|---|---|---|
| `ACTIVITY_TTL` | 25 | core/comm/control.py |  |
| `AGENT_TTL_SECONDS` | 300 | research/in-flight/t342/dead-modules/multi_agent.py |  |
| `AURORA_COMBO_OUTPUT_CHARS` | 24,000 | agent/harness/codex_bifrost_wake.py |  |
| `BACKUP_INTERVAL` | 300 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_manager.py | 5 minutes - routine backup |
| `BENCH_MIN_SURFACED` | 10 | core/recall/curator.py | exposure floor: it had its chances... |
| `BODY_CHARS` | 12,000 | core/recall/lookback.py | rationale often sits DEEP: a synthesis doc's convergence and |
| `BOOT_CAP` | 3 | core/coord/defer_queue.py |  |
| `BUDGET_CHARS_DEFAULT` | 2,000 | core/context/relevance_budget.py |  |
| `BUDGET_CHARS_DEFAULT` | 2,000 | research/in-flight/t342/dead-modules/context__relevance_budget.py |  |
| `BUDGET_DEFAULT` | 1,200 | agent/harness/delta.py |  |
| `BULLET_MIN` | 6 | scripts/checkers/check_bus_atom_pointers.py | or this many list items |
| `CACHE_TTL` | 3,600 | research/in-flight/t342/dead-modules/_archive__python_old__vision_engine.py | 1 hour |
| `CACHE_TTL` | 3,600 | research/in-flight/t342/dead-modules/_archive__python_old__vision_engine_comfy.py |  |
| `CACHE_TTL` | 300 | research/in-flight/t342/dead-modules/core__foundation__fast_cache.py | 5 minutes default |
| `CACHE_TTL` | 60 | research/in-flight/t342/dead-modules/error_documentation.py | seconds |
| `CANONICAL_MAXLEN` | 100,000 | core/events/event_log.py | the firehose: deep but bounded |
| `CANONICAL_MAXLEN` | 100,000 | core/signals/agent_signal_ledger.py | signals retained on the canonical stream |
| `CAP` | 50 | core/comm/pager.py |  |
| `CAP` | 90,000 | research/reviewed/success-sweep-raw-2026-08-10/extract_daniil_success_talk.py |  |
| `CATEGORY_CAP_PER_ATOM` | 3 | core/library/taxonomy.py |  |
| `CHAIN_WARN_THRESHOLD` | 50 | core/learning/agent_memory.py |  |
| `CLARIFY_MAX_PER_TASK` | 3 | core/comm/toolbox.py |  |
| `CLARIFY_TIMEOUT_S` | 300 | core/comm/toolbox.py |  |
| `COMPLEXITY_CODE_LINES_THRESHOLD` | 50 | research/in-flight/t342/dead-modules/master.py | If proposal has > 50 lines of code, mark as complex |
| `COMPLEXITY_STEPS_THRESHOLD` | 5 | research/in-flight/t342/dead-modules/master.py | If > 5 steps, mark as complex |
| `CREDITED_MIN_CONTEXTS` | 2 | core/recall/replay.py | criterion 3: credited contexts per credited lesson... |
| `DEFAULT_BUDGET` | 2,000 | core/comm/mailbox.py |  |
| `DEFAULT_CAP` | 5,000 | core/comm/mailbox.py |  |
| `DEFAULT_FRAG_REASSEMBLY_TTL` | 300 | core/comm/packet_spec.py |  |
| `DEFAULT_LIMIT` | 40 | scripts/corpus_digests.py |  |
| `DEFAULT_MAXLEN` | 10,000 | core/comm/bus.py |  |
| `DEFAULT_MAXLEN` | 100,000 | core/events/event_index.py | match the firehose (event_log.CANONICAL_MAXLEN) |
| `DEFAULT_MAX_CHARS` | 170 | core/primitives/consolidator.py |  |
| `DEFAULT_MAX_MESSAGE_BYTES` | 65,536 | core/comm/packet_spec.py |  |
| `DEFAULT_MAX_OCCURRENCES` | 120 | core/coord/sift.py |  |
| `DEFAULT_MAX_PROMOTE` | 10 | core/narrative/event_promoter.py | per-run cap (rate-limit; no Beat flood) |
| `DEFAULT_THRESHOLD` | 3 | core/narrative/event_promoter.py | salience >= this is worth a Beat |
| `DEFAULT_TIMEOUT` | 5 | research/in-flight/t342/dead-modules/gemini_bridge.py | 5 seconds max to determine bridge failure |
| `DEFAULT_TIMEOUT` | 5 | research/in-flight/t342/dead-modules/gemini_bridge_monitor.py |  |
| `DEFAULT_TIMEOUT_S` | 25 | core/comm/door_probe.py |  |
| `DEFAULT_TOKEN_BUDGET` | 4,000 | core/primitives/consolidator.py |  |
| `DEFAULT_TRACE_SPOT_INTERVAL` | 1,000 | core/comm/packet_spec.py |  |
| `DEFAULT_TTL` | 900 | core/comm/locks.py | 15 min -- long enough for a slice, short enough to self-heal a crash |
| `DEFAULT_TTL` | 900 | core/coord/intent.py | 15 min -- long enough for a slice, self-heals a crash (mirrors locks) |
| `DEFAULT_WINDOW_SECONDS` | 1,800 | core/narrative/event_bridge.py | +/- 30 min around a point (Beat / timestamp) |
| `DIRECTIVE_STALE_DAYS` | 3 | agent_cli.py | W04: a directive older than this confesses its age at boot |
| `DISCORD_MAX` | 2,000 | core/comm/discord_bridge.py |  |
| `DRAIN_FLUSH_JOIN_SEC` | 2 | core/comm/launcher.py |  |
| `DRAIN_TTL_S` | 300 | core/comm/control.py |  |
| `EVENT_SCAN_LIMIT` | 5,000 | core/recall/funnel.py |  |
| `FLOOR_CHARS` | 15 | scripts/bifrost_runner_deepseek.py |  |
| `FORGE_WATCH_MIN_IMPRESSIONS` | 8 | core/recall/curator.py | ...or this many fresh impressions, whichever first |
| `FRESH_MIN_DEFAULT` | 30 | core/comm/wake_seat.py | AKASHIC_WAKE_MARKER_FRESH_MIN overrides |
| `GEMINI` | 3 | research/in-flight/t342/dead-modules/_archive__python_old__escalation.py | Gemini strategic review |
| `GIT_CAP` | 10 | agent/harness/delta.py | commits listed before the pull pointer takes over |
| `HEADING_MIN` | 2 | scripts/checkers/check_bus_atom_pointers.py | markdown headings that make a body design-shaped |
| `HEALTH_CHECK_INTERVAL` | 30 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_manager.py | seconds |
| `HEALTH_CHECK_TIMEOUT` | 30 | research/in-flight/t342/dead-modules/deployment_framework.py |  |
| `HEARTBEAT_INTERVAL` | 30 | research/in-flight/t342/dead-modules/_archive__legacy__services__background_monitor.py | seconds |
| `HEARTBEAT_INTERVAL` | 10 | research/in-flight/t342/dead-modules/agent_comm_service.py | seconds - heartbeat frequency |
| `HEARTBEAT_INTERVAL` | 30 | research/in-flight/t342/dead-modules/multi_agent.py |  |
| `HINT_MAX_PER_AGENT` | 8 | core/comm/context_hints.py | ring buffer cap per receiving agent |
| `HINT_TTL_SECONDS` | 300 | core/comm/context_hints.py | 5 min soft expiry (stale hints silently dropped by drain) |
| `HISTORY_CAP` | 200 | core/comm/turn_metrics.py |  |
| `IMPLAUSIBLE_MIN_N` | 5 | core/coord/sift.py | below this, a high rate is small-n noise, not an alarm |
| `INNER_BLOCK_MS` | 120,000 | research/in-flight/t342/dead-modules/scripts__heimdall.py | 2-min inner blocks; loop if a batch is all noise |
| `LANE_MEMBERSHIP_WINDOW` | 500 | core/comm/bifrost_api.py |  |
| `LINE_BUDGET` | 120 | core/coord/task_costs.py |  |
| `MANIFEST_TTL` | 300 | research/in-flight/t342/dead-modules/agent_coordinator_v2.py | 5 minutes - manifest expires if not refreshed |
| `MAX_BACKOFF` | 30 | research/in-flight/t342/dead-modules/enterprise_web_fetch.py | seconds |
| `MAX_BACKUP_AGE_ALERT` | 900 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_manager.py | 15 minutes - alert threshold |
| `MAX_BACKUP_AGE_CRITICAL` | 1,800 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_manager.py | 30 minutes - critical threshold |
| `MAX_BODY` | 240 | core/toolbelt/contest.py | a second voice is shorter than the first; chorus, not solo. |
| `MAX_BODY` | 400 | core/toolbelt/toast.py | gratitude is short; the leaderboard guard is distinct-users love |
| `MAX_CHARS_PER_ENTRY` | 170 | core/narrative/chronicler.py |  |
| `MAX_CMD_OUT` | 16,000 | core/comm/toolbox.py |  |
| `MAX_FILE_BYTES` | 120,000 | core/comm/toolbox.py |  |
| `MAX_LIST` | 400 | core/comm/toolbox.py |  |
| `MAX_MATCHES` | 120 | core/comm/toolbox.py |  |
| `MAX_MODEL_LEN` | 32,768 | research/in-flight/t342/dead-modules/deploy_vllm.py | 32k context |
| `MAX_PER_PUMP` | 20 | core/comm/discord_feed.py |  |
| `MAX_POST_CHARS` | 1,900 | core/comm/discord_guest_reply.py |  |
| `MAX_REFLECTIONS` | 50 | core/learning/agent_memory.py | keep only the newest N reflections in the index |
| `MAX_REFS` | 2 | scripts/season_llm_player.py |  |
| `MAX_RETRIES` | 3 | research/in-flight/t342/dead-modules/enterprise_web_fetch.py |  |
| `MAX_STARTUP_WAIT` | 120 | research/in-flight/t342/dead-modules/deployment_framework.py |  |
| `MAX_TARGETS_PER_PASS` | 2 | core/recall/forge_optimizer.py | locked design decision 1 |
| `MESSAGE_TTL` | 3,600 | research/in-flight/t342/dead-modules/fast_agent_comm.py | 1 hour |
| `MESSAGE_TTL_DAYS` | 7 | research/in-flight/t342/dead-modules/multi_agent.py |  |
| `MINOR_FLOOR` | 25 | core/coord/world_diff.py |  |
| `MIN_BEATS` | 2 | core/narrative/episode_suggester.py | a thin episode has nothing worth bookending |
| `MIN_N` | 3 | core/comm/turn_metrics.py |  |
| `MIN_SPAN_S` | 300 | core/narrative/episode_suggester.py | a just-opened episode never suggests (anti rapid-fire after each close) |
| `MIN_VERIFIED` | 5 | core/coord/lens_ledger.py |  |
| `MIN_WITHIN_S` | 30 | core/comm/expectations.py | clamp floor: sub-30s reply deadlines on a turn-based bus are noise |
| `MONITOR_INTERVAL` | 100 | research/in-flight/t342/dead-modules/_archive__legacy__services__background_monitor.py | ms - fast polling |
| `NUDGE_TTL` | 120 | core/comm/nudge.py | a nudge auto-expires so a missed pick-up never sticks |
| `OUTCOME_MAXLEN` | 20,000 | core/recall/at_action.py |  |
| `PER_AGENT_MAXLEN` | 10,000 | core/events/event_log.py | per-agent: a shallower convenience index |
| `PER_AGENT_MAXLEN` | 10,000 | core/signals/agent_signal_ledger.py | signals retained per agent stream |
| `PER_STREAM_LIMIT` | 400 | core/comm/flow_trace.py | bounded read per stream; the window trims harder |
| `POLL_INTERVAL` | 5 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_sync.py | seconds between checks |
| `POLL_INTERVAL` | 30 | research/in-flight/t342/dead-modules/_archive__legacy__services__session_monitor.py | seconds between checks |
| `PORT_TEST_UI_MAX` | 8,999 | config.py | last test-UI port. A test UI MUST live in [8900, 8999]. |
| `PRESENCE_TTL` | 90 | core/comm/bus.py | seconds an agent is considered "online" after its last activity |
| `PROPOSAL_TTL` | 60 | core/coord/intent.py | proposal records auto-expire after a minute |
| `REDIS_CHECK_TIMEOUT` | 30 | research/in-flight/t342/dead-modules/launch.py |  |
| `REDIS_TIMEOUT` | 5 | config.py |  |
| `REHAB_MIN_CONTEXTS` | 8 | core/recall/replay.py | criterion 2: surfaced contexts per rehab candidate... |
| `REHAB_MIN_SURFACED` | 10 | core/recall/forge_optimizer.py | rehab class definition (mirrors the audit / curator) |
| `REHOME_CLAIM_TTL_S` | 30 | core/comm/reaper.py |  |
| `RENDER_TTL_S` | 30 | agent/harness/delta.py | X1: turn_metrics EST_CACHE_TTL pattern |
| `SCHEMA_KNOWN_MAX` | 1 | core/library/atoms.py |  |
| `SEATSEEN_TTL_S` | 86,400 | core/comm/roster.py | kimi F1: death must outlive the worklive TTL to be RENDERABLE |
| `SEEN_CAP` | 1,000 | scripts/bifrost_wake.py | newest-last trim on save; a session outliving 1000 wakes re-earns a twin wake |
| `SENTINEL_DOWN_AFTER_MS` | 5,000 | research/in-flight/t342/dead-modules/_archive__legacy__services__redis_ha_manager.py |  |
| `SIGNIFICANCE_THRESHOLD` | 3 | research/in-flight/t342/dead-modules/_archive__python_old__smart_log.py |  |
| `SILENCE_THRESHOLD_MINUTES` | 5 | research/in-flight/t342/dead-modules/_archive__legacy__services__session_monitor.py | Consider silent if no log entries in this time |
| `SKEW_WINDOW_S` | 300 | core/comm/remote_relay.py |  |
| `SNIPPET_CHARS` | 72 | core/comm/flow_trace.py |  |
| `STALE_DAYS` | 14 | scripts/checkers/check_comprehensibility.py |  |
| `STALE_PROPOSED_DAYS` | 7 | core/coord/task_ledger.py | default; render callers may override via env AKASHIC_PROPOSED_STALE_DAYS |
| `STEER_TTL` | 900 | core/comm/nudge.py | a queued steer that's never picked up self-expires after 15 min |
| `SURFACE_MAXLEN` | 6,000 | core/recall/at_action.py |  |
| `TF_LEN_UNIT` | 4,000 | core/recall/lookback.py | chars of text per EXPECTED occurrence of a matched stem: a 12KB doc |
| `THRESHOLD` | 1,500 | scripts/checkers/check_bus_atom_pointers.py | chars: below this a body is "a pointer with manners" |
| `TIMEOUT` | 15 | research/in-flight/t342/dead-modules/enterprise_web_fetch.py | seconds |
| `TOKEN_BUDGET` | 4,000 | core/narrative/chronicler.py |  |
| `TOOL_SEND_TEXT_MAX` | 8,000 | core/comm/packet_spec.py | D3 (deepseek verdict 2026-07-19): the 4000 door |
| `WINDOW` | 30 | core/coord/method_drift.py |  |
| `WINDOW` | 240 | scripts/checkers/check_pointer_promises.py |  |
| `_ANSWERED_KEY_CAP` | 20,000 | core/comm/mailbox.py |  |
| `_CAP_MAX` | 200 | agent/harness/capture.py |  |
| `_CAP_STR` | 400 | agent/harness/capture.py |  |
| `_CTX_FLOOR` | 32,000 | core/fleet/caller.py |  |
| `_DEFAULT_BUDGET_LINES` | 12 | agent/harness/context.py | W6; AKASHIC_WHISPER_LINES overrides (R6) |
| `_DONE_CAP` | 8,192 | core/comm/packet_spec.py |  |
| `_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION` | 9 | scripts/run_job.py |  |
| `_MAX` | 4,000 | agent_cli.py | clamp absurdly long fields an agent might paste |
| `_MAX_BLOB` | 3,000,000 | scripts/checkers/check_secrets.py |  |
| `_MAX_DETAIL_CHARS` | 8,000 | core/events/event_log.py | raw is rich, but a single payload is still bounded |
| `_MAX_NOTE` | 100,000 | agent_cli.py | durable note bodies: a ceiling against runaway pastes, not a working size |
| `_MAX_SUMMARY` | 500 | core/events/event_log.py |  |
| `_MIN_MARKER` | 6 | core/trust/private_plane.py |  |
| `_MIN_SUFFIX_CHARS` | 200 | core/library/legacy_map.py |  |
| `_NOTE_WINDOW_DAYS` | 60 | agent/harness/context.py | one store pull feeds every note-derived section |
| `_OUTCOME_MAX_BYTES` | 4,000,000 | core/recall/at_action.py | ~4MB ring; oldest half dropped on overflow |
| `_REASK_WINDOW_S` | 1,800 | core/comm/bus.py | 30 min; BIFROST_REASK_WINDOW_S overrides |
| `_RECYCLE_SLACK_MS` | 1,000 | core/comm/wake_seat.py | parent may not be YOUNGER than child by more |
| `_SHA_LEN` | 24 | core/comm/blobs.py | 96 bits of sha256 -- ample for a single-user blob store |
| `_STALE_DAYS` | 7 | agent/harness/context.py | W5: note-derived lines gain [STALE] at this age |
| `_SWITCH_MIN_BEATS` | 2 | core/narrative/episode_suggester.py | ...and needs >=2 of them, unanimous, on a non-episode track |
| `_SWITCH_WINDOW` | 3 | core/narrative/episode_suggester.py | switch looks at the last N routed beats... |
| `_THEMES_MAX_DAYS` | 30 | agent/harness/context.py | R2: themes older than this stay off the whisper |
