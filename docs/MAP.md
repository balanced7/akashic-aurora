# MAP -- the master census matrix (auto-generated, v0)

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_master_map.py`.
> Columns: line-1 docstring (the module's own spec) | name-matched pin file |
> name-matched design/reference doc (v0 HEURISTIC -- ranks the M3 backfill queue,
> does not certify coverage) | env flags read (physics scan). GAP = neither a
> name-matched pin nor a paper: the honest backfill queue, worst first by area.
> Companions: ARCHITECTURE.md (skeleton) - MODULE_INDEX.md (docstrings) -
> PHYSICS.md (bounds+flags) - the charter docs/library/brief/20260719_the-master-map-documentation-as-projecti_a26fd3.md.

## GAP queue (39 of 152 modules lack both pin and paper by name)

- core/foundation/durable_reconcile.py
- core/foundation/migrate_to_sqlite.py
- core/foundation/redis_connection.py
- core/foundation/timeutil.py
- core/signals/agent_signal_ledger.py
- core/signals/coordinator_api.py
- core/comm/assertions.py
- core/comm/blobs.py
- core/comm/cursor_admin.py
- core/comm/daemon_state.py
- core/comm/discord_bridge.py
- core/comm/dispatcher.py
- core/comm/fence_phase.py
- core/comm/interject.py
- core/comm/lane_depths.py
- core/comm/runner_lib.py
- core/comm/runner_lock.py
- core/comm/runtime_age.py
- core/comm/session_exit.py
- core/comm/session_state.py
- core/comm/storm_detect.py
- core/comm/timescale.py
- core/coord/capability_search.py
- core/coord/task_costs.py
- core/learning/domains.py
- core/learning/vfx_chunk_lessons.py
- core/recall/at_action.py
- core/recall/curator.py
- core/recall/funnel.py
- core/recall/pack_replay.py
- core/narrative/chapter_lifecycle.py
- core/narrative/theme_assigner.py
- core/trust/capabilities.py
- core/trust/grant_writer.py
- core/fleet/model_roster.py
- core/state/session_checkpoint.py
- core/state/session_recovery.py
- core/perspectives/reinforce.py
- agent/initializer.py

## core/foundation/  (9 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `durable_reconcile.py` | Per-family authority reconcile: make the durable source COMPLETE before migrating. | GAP | GAP | `AI_SETUP` |
| `ledger.py` | Ledger: Swappable event-record interface (append-and-replay) | tests/test_ledger.py | docs/failure-ledger-2026-07.md | `AI_SETUP` |
| `migrate_to_sqlite.py` | JSON FileStore -> SqliteStore migration: shadow-build, census law, honest verify. | GAP | GAP | `AI_SETUP` |
| `redis_connection.py` | Redis Connection: Fail-fast connectivity primitive | GAP | GAP | `AKASHIC_REDIS_HEALTH_CHECK_SEC`, `REDIS_DB`, `REDIS_HOST`, `REDIS_PORT` |
| `relationship_types.py` | Comprehensive Relationship Type Framework for Knowledge Graphs | tests/test_relationship_types.py | GAP |  |
| `sqlite_store.py` | SqliteStore -- the durable Store backend with real cross-process safety. | tests/test_sqlite_store.py | GAP | `AI_SETUP` |
| `store.py` | Store: Swappable persistence interface (full Redis-mirror) | tests/test_filestore_coherence.py | docs/filestore-coherence-design-2026-07.md | `AI_SETUP`, `AKASHIC_STORE_BACKEND` |
| `streams.py` | streams -- process plumbing for long-lived agent processes (T030 L3 / RB-28). | tests/test_t150_runner_streams_are_watchable.py | GAP |  |
| `timeutil.py` | timeutil -- one deterministic, timezone-safe way to turn an ISO timestamp into a | GAP | GAP |  |

## core/events/  (3 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `event_index.py` | EventIndex (Slice V1) -- a Store-backed time index over the raw event firehose. | tests/test_event_index.py | GAP |  |
| `event_log.py` | EventLog (Slice 1) -- capture raw cross-agent events on an append-only Ledger. | tests/test_event_log.py | GAP |  |
| `event_query.py` | EventQuery (Slice 3) -- search and time-window the raw event firehose. | tests/test_event_query.py | GAP |  |

## core/signals/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `agent_signal_ledger.py` | Agent Signal Ledger: the ordered record of every signal agents emit | GAP | GAP |  |
| `coordinator_api.py` | Coordinator API: Minimal signal-based logging for agents | GAP | GAP | `AI_SETUP` |

## core/comm/  (53 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `ask.py` | ask -- a synchronous helper call, with no seat behind it (T171). | tests/test_ask_as_resident.py | GAP | `AKASHIC_ASK_BASE_URL`, `AKASHIC_ASK_COLLAPSE_AT`, `AKASHIC_ASK_CONTEXT_CHARS`, `AKASHIC_ASK_DISTINCT_AT`, `AKASHIC_ASK_FAN_WORKERS`, `AKASHIC_ASK_MAX_TOKENS`, `AKASHIC_ASK_MODEL`, `DEEPSEEK_API_KEY` |
| `ask_bg.py` | ask_bg -- a helper call that outlives your turn without becoming a seat (T205). | tests/test_t205_ask_bg.py | GAP | `AKASHIC_AGENT_ID`, `AKASHIC_ASK_BG_ORPHAN_S` |
| `ask_state.py` | ask_state -- one durable ask's honest state (T196d). | tests/test_t196d_ask_state.py | GAP |  |
| `assertions.py` | Pre-flight assertions (T068-R3 / deepseek M10) -- verify a directed answer's FACTUAL | GAP | GAP | `BIFROST_PREFLIGHT_ASSERT` |
| `bifrost_api.py` | bifrost.api -- the one door an agent uses to join and work the Bifrost bus. | tests/test_bifrost_api.py | GAP | `BIFROST_CONSUME_LANE`, `BIFROST_WAKE_LANE` |
| `blobs.py` | BlobStore (Slice B1) -- a content-addressed blob store for Bifrost media/large payloads. | GAP | GAP | `AI_SETUP` |
| `bus.py` | Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams. | tests/test_bifrost_bus.py | GAP | `AGENT_ID`, `AKASHIC_UNATTENDED_S`, `BIFROST_INCARNATION`, `BIFROST_NAMESPACE`, `BIFROST_REASK_WINDOW_S`, `BIFROST_REPLY_DEDUP_TTL_S`, `CLAUDE_CODE_SESSION_ID`, `PYTEST_CURRENT_TEST` |
| `context_hints.py` | Context Hints -- compact, ephemeral, per-agent context forwarding between peers. | tests/test_context_hints_gate.py | GAP |  |
| `control.py` | Bifrost control plane -- human-in-the-loop PAUSE + runaway-loop guard for live agent collaboration. | tests/test_bifrost_control_halt.py | docs/library/design/20260712_control-plane-namespace-isolation-claude_fade67.md | `BIFROST_MAX_HOPS`, `BIFROST_MAX_REPLIES_PER_MIN`, `BIFROST_NAMESPACE` |
| `control_channel.py` | Out-of-band control: a loopback listener that survives a dead bus. | tests/test_control_channel.py | GAP | `AKASHIC_CONTROL_PORT_BASE` |
| `cursor_admin.py` | cursor_admin -- T076a: SANCTIONED skip-to-now for an agent's consume cursors. | GAP | GAP |  |
| `daemon_state.py` | daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope). | GAP | GAP | `BIFROST_NAMESPACE` |
| `discord_bridge.py` | Outbound Discord bridge -- the fleet becomes watchable from a phone. | GAP | GAP | `AKASHIC_DISCORD_WEBHOOK` |
| `dispatcher.py` | Dispatcher (Bifrost Mesh W2): one resident process that turns doorbell notices into wakes. | GAP | GAP |  |
| `doctor.py` | Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress, | tests/test_doctor_dead_runner_visibility.py | GAP | `AKASHIC_LANE_STALL_PAGE_S`, `AKASHIC_LANE_STALL_WARN_S`, `AKASHIC_RECENT_INBOX_S`, `AKASHIC_STALL_HYSTERESIS_S`, `BIFROST_NAMESPACE`, `BIFROST_UI_PORT` |
| `door_probe.py` | door_probe -- does the MCP door actually answer, right now, in THIS environment? | tests/test_door_probe.py | research/reviewed/deepseek-door-probe-attack-2026-07-26.md |  |
| `engine_vitals.py` | engine_vitals -- gauge_snapshot(), the engine room's pulse (T079-E1). | tests/test_t079_e1_engine_vitals.py | GAP | `BIFROST_NAMESPACE` |
| `expectations.py` | expectations -- sender-side reply deadlines + redrive (T030 L4 / RB-29). | tests/test_t030_l4_expectations.py | GAP | `AKASHIC_EXPECT_TASK_SETTLE`, `BIFROST_NAMESPACE` |
| `failure_class.py` | failure_class -- name the cause of a dead ask, and say what to do about it (T202). | tests/test_t202_failure_class.py | GAP |  |
| `fence_phase.py` | fence_phase -- the method board's state source (T079-E2). | GAP | GAP |  |
| `flow_trace.py` | flow_trace (R3 / T054) -- the OTel-style waterfall over lanes: what HAPPENED, in causal | tests/test_flow_trace.py | GAP | `AKASHIC_FLOW_NO_COUNT`, `BIFROST_NAMESPACE` |
| `friction.py` | friction -- read the collaboration tax from evidence that already exists (T196a). | tests/test_t196a_friction.py | docs/library/design/20260701_night-friction-program-every-pain-point_70f449.md |  |
| `incarnation.py` | incarnation -- who else is HERE right now, per agent id (T074 W3/R4). | tests/test_t074_incarnation_cards.py | GAP | `AKASHIC_INCARNATION_TTL_MIN`, `BIFROST_NAMESPACE` |
| `interject.py` | Adaptive interjection router -- when a human types into a live agent session, decide whether the | GAP | GAP |  |
| `lane_depths.py` | lane_depths -- the engine room's flow gauge source (T079-E2). | GAP | GAP | `BIFROST_NAMESPACE` |
| `launcher.py` | Bifrost Launcher — spawn and monitor agent processes from the Bifrost UI. | tests/test_launcher_drain.py | GAP | `AKASHIC_SHOW_CONSOLES`, `LAUNCHER_AUTO_REVIVE_JITTER`, `LAUNCHER_RESTART_BACKOFF`, `LAUNCHER_RESTART_BACKOFF_MAX`, `LAUNCHER_RESTART_MAX`, `LAUNCHER_RESTART_RESET` |
| `liveness.py` | Work-progress heartbeat (L1) -- pure observability for wedge detection. | tests/test_launcher_drainer_liveness.py | docs/library/design/20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79.md | `AKASHIC_UNATTENDED_S`, `BIFROST_APPROACHING_WEDGE_SECONDS`, `BIFROST_NAMESPACE`, `BIFROST_WEDGE_SECONDS` |
| `locks.py` | Advisory path-locks (Concurrency design C2). | tests/test_locks.py | GAP |  |
| `mailbox.py` | mailbox -- T095 M0: shadow mailbox state index over the append-only lanes. | tests/test_t095_m0_mailbox_adversarial.py | docs/library/design/20260701_comms-mailbox-over-the-log-t095-governin_06357f.md | `AKASHIC_MAILBOX`, `BIFROST_NAMESPACE` |
| `nudge.py` | Bifrost nudge -- targeted, per-agent barge-in (companion to control.py's global PAUSE). | tests/test_learn_nudge.py | GAP | `BIFROST_NAMESPACE` |
| `packet_spec.py` | Packet Spec v1 -- envelope integrity + MTU library (T040 LAW; built in T043). | GAP | docs/library/design/20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94.md | `BIFROST_LANES_DUAL_WRITE`, `BIFROST_STALE_MS`, `BUS_MAX_MESSAGE_BYTES`, `FRAG_REASSEMBLY_TTL`, `PACKET_INTEGRITY_ENABLED`, `PACKET_INTEGRITY_TRACE`, `PACKET_TRACE_SPOT_INTERVAL` |
| `pager.py` | pager -- page-grade findings reach a HUMAN (T078-W4, the 6h-invisible killer). | tests/test_page_resolution.py | GAP | `BIFROST_NAMESPACE` |
| `peer_ready.py` | peer_ready -- make the peer EXIST before asking it something (T197c). | tests/test_t197c_peer_ready.py | GAP |  |
| `presets.py` | Fan presets: a named answer contract bound to the parser that reads it back. | tests/test_t256_fan_presets.py | GAP |  |
| `promoter.py` | Bifrost B2 -- the durable projection. Promote SALIENT bus messages into the append-only Ledger. | tests/test_bifrost_promoter.py | GAP | `AKASHIC_ACK_UNHANDLED_HOURS` |
| `reaper.py` | reaper -- S4: a dead seat's unread directed mail re-homes, loudly. Never stranded. | tests/test_t108_s4_reaper_hardening.py | research/reviewed/fence-lite-s4-reaper-kimi-2026-07-28.md |  |
| `role_queue.py` | role_queue -- T108 S1: load-balanced role-addressed work with claim semantics. | tests/test_t108_role_queue.py | GAP |  |
| `room_feed.py` | Namespace-aware feed-stream discovery -- the backend half of readable side rooms. | tests/test_room_feed_namespace.py | GAP |  |
| `roster.py` | roster -- S2: the lobby. Per-seat liveness the whole fleet can read. | tests/test_s2_roster.py | docs/library/design/20260718_frontier-roster-playbook-opening-positio_fde0ed.md | `AKASHIC_RESUME_GAP_S`, `AKASHIC_ROSTER_CHURN_AT`, `AKASHIC_ROSTER_CHURN_WINDOW_S`, `AKASHIC_WORKLIVE_FRESH_S`, `AKASHIC_WORKLIVE_TTL_S` |
| `router.py` | T060 N0: pure route explanation and bounded shadow-delivery counters. | tests/test_router_confusables.py | docs/library/report/20260717_t060-n0-shadow-router-deepseek-review-pe_bf6b68.md |  |
| `runner_lib.py` | core.comm.runner_lib -- shared hardening for OpenAI-compatible seat transports (K0, 2026-07-18). | GAP | GAP |  |
| `runner_lock.py` | Bifrost runner singleton-lock -- at most ONE live runner per agent id. | GAP | GAP | `BIFROST_NAMESPACE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_SESSION_ID` |
| `runtime_age.py` | runtime_age (T116) -- how much code a RUNNING process cannot possibly contain. | GAP | GAP | `BIFROST_NAMESPACE` |
| `seat_identity.py` | seat_identity -- WHO AM I, resolved per SESSION instead of per PROCESS. | tests/test_seat_identity_resolver.py | GAP | `AKASHIC_AGENT_ID` |
| `self_restart.py` | self_restart (A1) -- a runner that knows it is stale restarts itself. | tests/test_a1_stale_self_restart.py | GAP | `AKASHIC_SELF_RESTART_MIN_BEHIND`, `AKASHIC_SELF_RESTART_MIN_UPTIME_S` |
| `session_exit.py` | session_exit -- the clean-death trio (T075 M1-beta, reconciliation ruling 3). | GAP | GAP | `AKASHIC_CLEAN_DEATH` |
| `session_state.py` | Session State — snapshot the live Bifrost session so it can be resumed later. | GAP | GAP |  |
| `storm_detect.py` | storm_detect — S0-beta storm signature detection (lane-depth spike + repeat-delivery). | GAP | GAP | `STORM_DEPTH_THRESHOLD`, `STORM_DEPTH_WINDOW`, `STORM_REPEAT_THRESHOLD` |
| `timescale.py` | Timescale (T030 L1 follow-up) -- ONE seam for BUGGIFY-style timeout shrinking. | GAP | GAP | `AKASHIC_TIMEOUT_MULTIPLIER` |
| `toolbox.py` | core.comm.toolbox -- the fleet's guarded tool surface (schemas + executor), shared seam. | tests/test_k0_toolbox_extraction.py | docs/library/report/20260715_deepseek-t067-1-design-toolbox-third-doo_ae2b37.md | `AKASHIC_AGENT_ID`, `DEEPSEEK_MAX_CMD_TIMEOUT`, `DEEPSEEK_RECALL_AT` |
| `triage_park.py` | Triage park (S0-alpha) -- the scry-to-bottom bench. | tests/test_s0_triage_park.py | GAP | `BIFROST_NAMESPACE` |
| `turn_metrics.py` | Turn metrics (progress-bars data half; co-designed claude+deepseek 2026-07-11). | tests/test_turn_metrics.py | GAP | `BIFROST_NAMESPACE` |
| `wake_seat.py` | wake_seat -- the per-session wake-seat protocol (T029 Wave 2, the R1/R16 fix). | tests/test_wake_seat.py | docs/library/design/20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf.md | `AKASHIC_TOMBSTONE`, `AKASHIC_WAKE_MARKER_FRESH_MIN`, `BIFROST_NAMESPACE` |

## core/coord/  (18 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `capability_search.py` | capability_search -- "does this system already do X?", asked at the level of MEANING. | GAP | GAP |  |
| `cognitive_metrics.py` | Cognitive Efficiency Metrics — live instrumentation for the Stage-3 evidence engine. | tests/test_cognitive_metrics.py | GAP |  |
| `compare.py` | compare -- the cross-domain set difference, with a name (T213). | tests/test_t213_compare.py | GAP |  |
| `conductor.py` | Conductor — the impure orchestration shell over the pure task ledger (Slice D). | tests/test_conductor.py | docs/library/chronicle/20260723_session-reflection-fable-s-conductor-nig_415441.md |  |
| `defer_queue.py` | defer_queue — the capability-gated standing queue (W33, seat-zero wave B3). | tests/test_w33_defer_queue.py | GAP |  |
| `experiment.py` | Coordination experiment harness -- the Stage-3 evidence engine. | tests/test_coord_experiment.py | docs/library/report/20260731_pair-sync-steer-experiment_64f62b.md |  |
| `fence_workspace.py` | Fence workspace (R2 / T053) -- the fence as a first-class object, not a naming convention. | tests/test_fence_workspace.py | GAP | `AKASHIC_FENCE_ROOT` |
| `intent.py` | Intent declaration -- Policy 0 of the coordination layer. | tests/test_boot_intent_surface.py | docs/library/report/20260711_claude-s-diagnosis-half-the-boot-intent_794515.md | `BIFROST_NAMESPACE` |
| `method_drift.py` | method_drift -- the one method number that reaches a channel people actually read. | tests/test_boot_surfaces_method_drift.py | GAP |  |
| `metrics.py` | Solution-Space-Shrinkage Tracker — the Metric C cross-run watchdog. | tests/narrative_metrics.py | GAP |  |
| `negotiation.py` | Negotiation round — brief window after user input where agents declare plans. | tests/test_negotiation.py | GAP |  |
| `preregistration.py` | preregistration -- M3's pre-registration metric, as numbers (T123 boundary fix). | GAP | docs/library/report/20260807_t207-grounding-ab-preregistration_b423f7.md |  |
| `sift.py` | sift -- the nested ask: a tiered read that returns dissent instead of consensus. | tests/test_t217_sift.py | GAP |  |
| `suite_baseline.py` | suite_baseline — the test-suite receipt the next seat diffs instead of re-deriving (W34/B4). | tests/test_w34_suite_baseline.py | GAP |  |
| `task_costs.py` | Task cost telemetry (T056 / wishlist R5) -- per-slice ROI, honestly attributed. | GAP | GAP | `BIFROST_NAMESPACE` |
| `task_ledger.py` | Governed task ledger — the deterministic coordination substrate (Phase 1: sequential-correct). | tests/test_task_ledger.py | GAP | `AKASHIC_PROPOSED_STALE_DAYS`, `BIFROST_PREMISE_GATE_MIN_AGE_MS` |
| `terms.py` | terms -- the vocabulary a codebase TALKS ABOUT, as a comparable set (T214). | tests/test_t214_terms_domain.py | GAP |  |
| `timeline.py` | timeline -- one chronological SET across domains (T211). | tests/test_t211_timeline.py | GAP | `AKASHIC_TIMELINE_FILE_LIMIT` |

## core/learning/  (5 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `agent_memory.py` | Agent Memory: a multi-type memory for agents (decisions, experiences, reflections, approaches) | tests/test_agent_memory.py | docs/library/design/20260701_multi-agent-memory-recall-design-assessm_7807ba.md |  |
| `consolidation.py` | Consolidation: distill raw episodic memory + experiment lessons into a curated chronicle. | tests/test_consolidation.py | docs/library/design/20260709_s2-the-consolidation-pass-that-sharpens_68d42c.md | `AI_SETUP` |
| `domains.py` | Recall domains — the boundary line, and why it is not a tag. | GAP | GAP |  |
| `learning_store.py` | Learning Store: Persists and retrieves experiment outcomes via the Store. | GAP | docs/library/design/20260709_agent-memory-analysis-of-learning-store_5ec82f.md | `AI_SETUP` |
| `vfx_chunk_lessons.py` | Adopt the VFX chunk rules into recall — as a PROJECTION, not a migration. | GAP | GAP | `AI_SETUP` |

## core/recall/  (13 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `anchors.py` | Lesson anchor resolver -- does a lesson's premise still hold? | tests/test_lesson_anchors.py | GAP | `AI_SETUP` |
| `at_action.py` | Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action. | GAP | GAP | `AKASHIC_AGENT_ID`, `AKASHIC_BENCH_PROBE_DAYS`, `AKASHIC_BENCH_PROBE_MAX`, `AKASHIC_RECALL_CACHE_TTL`, `AKASHIC_RECALL_FLOOR`, `AKASHIC_RECALL_SELF_ECHO_H`, `AKASHIC_RECALL_STATE_DIR`, `AKASHIC_STALE_CUE_DAYS` |
| `curator.py` | Recall curator (vNext loop 1) -- the funnel's triage made an ACTOR, not a report. | GAP | GAP |  |
| `dissent.py` | Dissent-finder (`core/recall`) — surface the strongest genuine COUNTER to a recalled lesson. | tests/test_dissent_capture.py | docs/library/report/20260718_kimi-fresh-eyes-dissent-round-t094-recal_71a6f9.md |  |
| `forge.py` | Forge F1 -- the Tier-0 edit gate (docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204 | tests/test_forge_gate.py | docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.md |  |
| `forge_optimizer.py` | Forge F2 -- the optimizer pass (docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.m | tests/test_forge_optimizer.py | GAP |  |
| `funnel.py` | Recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are | GAP | GAP |  |
| `gate_rules.py` | gate_rules (R2 slice 1a) -- three principles about an action's relationship to | tests/test_r2_s1_gate_rules.py | GAP |  |
| `knowledge_map.py` | knowledge_map (R8 / T059) -- WALK the knowledge, don't query it blind. | tests/test_knowledge_map.py | docs/library/report/20260714_claude-t059-review-r8-knowledge-map-2026_43eade.md | `AKASHIC_KMAP_NO_COUNT` |
| `lookback.py` | Lookback (P7 / T027) -- one question over the rationale corpus, layered, drillable. | tests/test_charters_in_lookback_corpus.py | docs/library/report/20260710_p7-lookback-corpus-inventory-deepseek-ve_f5fc91.md | `AKASHIC_LOOKBACK_NO_COUNT` |
| `pack_replay.py` | pack_replay (R2) -- replay the frozen census pack through TODAY's recall pipeline. | GAP | GAP |  |
| `precision_audit.py` | precision_audit -- the missing instrument: is recall ACCURATE? | tests/test_precision_audit.py | research/reviewed/precision-audit-calibration-deepseek-2026-07-27.md | `TEMP` |
| `replay.py` | Forge F0 -- replay harness + data-sufficiency audit (docs/library/design/20260701_lesson-forge-evidence-gated- | tests/test_forge_replay.py | docs/library/design/20260721_the-arc-replay-bench-opening-position-cl_551e03.md |  |

## core/primitives/  (8 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `clusterer.py` | Clusterer (Slice C1) -- group atoms by MEANING and flag where the knowledge structure should | tests/test_clusterer.py | GAP |  |
| `consolidator.py` | Consolidator (Slice S1) -- the one engine that turns a set of records into a budgeted, | tests/test_consolidator.py | GAP |  |
| `distiller.py` | Distiller: compact many items into a token budget, keeping a pointer to each source. | tests/test_distiller.py | GAP |  |
| `embedder.py` | Embedder (Slice C0) -- the embedding substrate. One local, CPU, offline model behind a tiny | tests/test_embedder.py | GAP | `EMBED_MODEL` |
| `epistemic.py` | Pure typed epistemic view for honest render surfaces. | tests/test_t121_f3_epistemic_view.py | GAP |  |
| `faithfulness.py` | Faithfulness critic (FAITH-1) -- a deterministic, NO-LLM grounding gate for distillations. | tests/test_chronicler_faithfulness.py | docs/library/design/20260709_faithfulness-critic-sota-synthesis-desig_eae48d.md |  |
| `ranker.py` | Ranker: order items by relevance x importance x recency (+ relationship type) | tests/test_ranker.py | GAP |  |
| `supersession.py` | Supersession: a newer record retires an older one (temporal correctness). | tests/test_notes_supersession.py | docs/library/brief/20260723_charter-the-supersession-sweep-megaread_76cc41.md |  |

## core/renew/  (1 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `session_signals.py` | Session signals (RENEW slice A'') -- fold one session's tool calls into deterministic context-health signal ag | tests/test_session_signals.py | GAP |  |

## core/narrative/  (17 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `beat_log.py` | BeatLog (Slice 1) -- append salient narrative Beats to the Store + read them by time. | tests/test_narrative_beat_log.py | GAP | `AKASHIC_EMBED_THEMES` |
| `chapter_lifecycle.py` | Chapter lifecycle helpers (Slice 7) — bi-temporal stamping, in-place regeneration, | GAP | GAP |  |
| `chronicler.py` | Chronicler (Slice 3) — distill narrative Beats into Chapters + Storyline + Atlas. | tests/test_chronicler.py | GAP | `AI_SETUP` |
| `drift.py` | drift_check -- lightweight SEMANTIC drift detector over the narrative spine (prototype). | tests/test_boot_surfaces_method_drift.py | docs/library/report/20260711_deepseek-l2-verify-gate-green-3-drifts-v_3395cc.md |  |
| `episode.py` | Session bookends -- the live EPISODE layer over the narrative Chapter (Slice S1). | tests/test_episode.py | docs/library/report/20260716_w8-gauge-honesty-episode-auto-close-prio_79e195.md |  |
| `episode_suggester.py` | Episode auto-suggester (bookends Slice S3) -- ADVISORY phase-boundary suggestions, never a forced close. | tests/test_episode_suggester.py | GAP | `AKASHIC_AGENT_ID` |
| `event_bridge.py` | EventBridge (Slice 4) -- join the narrative timeline to the raw event firehose. | tests/test_event_bridge.py | GAP |  |
| `event_promoter.py` | EventPromoter (Slice 5) -- promote salient raw events into narrative Beats. | tests/test_event_promoter.py | GAP |  |
| `health.py` | Narrative health counters (Slice W-c) -- give the silent best-effort paths a voice. | tests/test_narrative_health.py | GAP |  |
| `schema.py` | Narrative schema (Slice 0) — the data shapes of the multi-domain narrative spine. | tests/test_narrative_schema.py | docs/library/design/20260709_agent-security-schema-design-proposal_cdccf1.md |  |
| `session.py` | Session lifecycle (Slice 1 auto-capture) -- the spine fills itself. | tests/test_notes_supersession.py | docs/library/brief/20260723_charter-the-supersession-sweep-megaread_76cc41.md |  |
| `tag_audit.py` | TagAuditor (Slice G2) -- detect likely mis-tags. FLAG-ONLY: it returns suspects and | tests/test_tag_audit.py | GAP |  |
| `tag_governance.py` | TagGovernor (Slice G1) -- the append-only, confidence-gated re-tag write path. | tests/test_tag_governance.py | docs/library/design/20260709_tag-governance-safe-self-improving-taggi_1c9052.md |  |
| `tagging.py` | Tag governance (Slice G0) -- tag-history + confidence schema. Pure data + selection | tests/test_tagging.py | GAP |  |
| `theme_assigner.py` | ThemeAssigner (Slice 5, Tier 0 heuristic) -- infer cross-cutting Themes from | GAP | GAP |  |
| `theme_discovery.py` | ThemeDiscoverer (Spine v2, slice V6) -- embedding theme inference that augments the | tests/test_theme_discovery.py | GAP | `AKASHIC_EMBED_THEMES` |
| `track_router.py` | TrackRouter (Slice 2, Tier 0 heuristic) -- infer which domain Track a Beat belongs to, | tests/test_track_router.py | GAP |  |

## core/trust/  (3 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `capabilities.py` | Capability tokens + role templates -- the atomic vocabulary of the security schema. | GAP | GAP |  |
| `grant_writer.py` | core.trust.grant_writer -- the WRITE side of security/acl.json (T163, S-3 of the security schema). | GAP | GAP |  |
| `registry.py` | Grant registry -- the reader over security/acl.json (source of truth), mirroring core/fleet/model_roster.py (r | tests/test_audit_registry_wiring_kimi.py | docs/library/design/20260711_t034-registry-dial-consolidation-deepsee_a65322.md | `AKASHIC_ACL_PATH` |

## core/fleet/  (3 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `caller.py` | The direct caller -- one-shot invocation of a local model for a BOUNDED subtask. | tests/test_recall_error_is_not_silence.py | GAP |  |
| `model_roster.py` | The fleet roster -- the single source of truth for local models (docs/library/design/20260709_fleet-dispatch-a | GAP | GAP |  |
| `residents.py` | The resident registry -- who a seat IS, and the receipts that earned the name. | GAP | docs/library/design/20260809_residents-and-callsigns-design_b6c98c.md |  |

## core/state/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `session_checkpoint.py` | Session Checkpoint: crash-recovery checkpoint system (renamed from session_state.py 2026-07-07 to | GAP | GAP | `AI_SETUP` |
| `session_recovery.py` | Session Recovery: Recover from checkpoint and fallback infrastructure | GAP | GAP |  |

## core/codex/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `lifecycle.py` | Node lifecycle (Slice C2, delta E3) -- bi-temporal stamping + supersession as TYPE-AGNOSTIC | GAP | docs/library/design/20260718_gemini-t086-seat-wake-hook-lifecycle-pri_dc70d6.md |  |
| `schema.py` | Resource schema (Slice C2) -- the knowledge-axis node + the structural bi-temporal contract. | tests/test_narrative_schema.py | docs/library/design/20260709_agent-security-schema-design-proposal_cdccf1.md |  |

## core/perspectives/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `reinforce.py` | ReinforcedGraph (Slice P1) -- an association graph whose edges STRENGTHEN with co-use | GAP | GAP |  |
| `schema.py` | Perspectives schema (Slice P0) -- Lens + Map shapes. Pure data, no behavior. | tests/test_narrative_schema.py | docs/library/design/20260709_agent-security-schema-design-proposal_cdccf1.md |  |

## agent/harness/  (9 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `capture.py` | Payload-truth capture shared by every harness adapter (Integration Tiers H1). | tests/test_bifrost_console_capture.py | docs/library/chronicle/20260723_last-session-draft-auto-captured-2026-07_1dd6ee.md | `AKASHIC_PAYLOAD_CAPTURE` |
| `context.py` | The auto-boot whisper shared by every harness adapter (Integration Tiers H0). | tests/test_context_hints_gate.py | docs/library/design/20260620_research-context-handling-compaction-and_e5960c.md | `AKASHIC_AUTOBOOT`, `AKASHIC_WHISPER_LINES` |
| `delta.py` | The delta door (T052 / wishlist R1) -- "what changed since I was last here." | tests/test_t052_delta_door.py | docs/library/design/20260714_design-brief-r1-delta-door-t052-full-fen_a36fa9.md | `BIFROST_NAMESPACE` |
| `guards.py` | Action-veto policy shared by every harness adapter (Integration Tiers H1). | tests/test_birth_guard_scoping.py | docs/library/design/20260719_fable-opus-safeguards-downgrade-research_570a26.md |  |
| `nudge.py` | JIT learn-nudge rate limiting shared by every harness adapter (friction audit D5). | tests/test_learn_nudge.py | GAP | `AKASHIC_LEARN_NUDGE`, `AKASHIC_LEARN_NUDGE_CAP` |
| `registry.py` | Harness registry (Integration Tiers H2): which runtimes plug into the stack, and what | tests/test_audit_registry_wiring_kimi.py | docs/library/design/20260711_t034-registry-dial-consolidation-deepsee_a65322.md |  |
| `scope.py` | Repo-scoping policy shared by every harness adapter (Integration Tiers H0). | tests/test_recall_agent_scope.py | docs/library/design/20260722_security-schema-amendment-scoped-admin-g_17c9ca.md |  |
| `seen.py` | Per-session anti-repeat state shared by every recall surface (Integration Tiers H0). | GAP | docs/library/report/20260716_mcp-surface-reverse-engineering-deepseek_c79c35.md | `AKASHIC_RECALL_STATE_DIR` |
| `trace.py` | Push display-only trace lines (tool calls) onto the Bifrost bus so the console shows what | tests/test_flow_trace.py | docs/library/report/20260716_t002-ui-trace-collapse-design-pre-regist_fc22a6.md | `AKASHIC_AGENT_ID`, `AKASHIC_TRACE` |

## agent/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `bifrost_pull.py` | Bifrost pull-side helpers (System 5 read lane). | tests/test_bifrost_pull.py | GAP | `BIFROST_INCARNATION`, `BIFROST_NAMESPACE`, `CLAUDE_CODE_SESSION_ID` |
| `initializer.py` | Agent Initialization Module: Derive context from startup sources | GAP | GAP |  |
