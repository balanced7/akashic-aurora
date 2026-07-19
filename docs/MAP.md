# MAP -- the master census matrix (auto-generated, v0)

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/gen_master_map.py`.
> Columns: line-1 docstring (the module's own spec) | name-matched pin file |
> name-matched design/reference doc (v0 HEURISTIC -- ranks the M3 backfill queue,
> does not certify coverage) | env flags read (physics scan). GAP = neither a
> name-matched pin nor a paper: the honest backfill queue, worst first by area.
> Companions: ARCHITECTURE.md (skeleton) - MODULE_INDEX.md (docstrings) -
> PHYSICS.md (bounds+flags) - the charter research/briefs/master-map-charter-2026-07-19.md.

## GAP queue (34 of 112 modules lack both pin and paper by name)

- core/foundation/redis_connection.py
- core/foundation/streams.py
- core/foundation/timeutil.py
- core/signals/agent_signal_ledger.py
- core/signals/coordinator_api.py
- core/comm/assertions.py
- core/comm/blobs.py
- core/comm/cursor_admin.py
- core/comm/daemon_state.py
- core/comm/dispatcher.py
- core/comm/fence_phase.py
- core/comm/interject.py
- core/comm/lane_depths.py
- core/comm/runner_lib.py
- core/comm/runner_lock.py
- core/comm/session_exit.py
- core/comm/session_state.py
- core/comm/timescale.py
- core/coord/task_costs.py
- core/learning/learning_store.py
- core/recall/at_action.py
- core/recall/curator.py
- core/recall/funnel.py
- core/narrative/chapter_lifecycle.py
- core/narrative/theme_assigner.py
- core/trust/capabilities.py
- core/fleet/caller.py
- core/state/session_checkpoint.py
- core/state/session_recovery.py
- core/codex/lifecycle.py
- core/perspectives/reinforce.py
- agent/harness/guards.py
- agent/harness/seen.py
- agent/initializer.py

## core/foundation/  (6 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `ledger.py` | Ledger: Swappable event-record interface (append-and-replay) | tests/test_ledger.py | docs/failure-ledger-2026-07.md | `AI_SETUP` |
| `redis_connection.py` | Redis Connection: Fail-fast connectivity primitive | GAP | GAP | `REDIS_DB`, `REDIS_HOST`, `REDIS_PORT` |
| `relationship_types.py` | Comprehensive Relationship Type Framework for Knowledge Graphs | tests/test_relationship_types.py | GAP |  |
| `store.py` | Store: Swappable persistence interface (full Redis-mirror) | tests/test_store.py | GAP | `AI_SETUP` |
| `streams.py` | streams -- process plumbing for long-lived agent processes (T030 L3 / RB-28). | GAP | GAP |  |
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

## core/comm/  (34 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `assertions.py` | Pre-flight assertions (T068-R3 / deepseek M10) -- verify a directed answer's FACTUAL | GAP | GAP | `BIFROST_PREFLIGHT_ASSERT` |
| `bifrost_api.py` | bifrost.api -- the one door an agent uses to join and work the Bifrost bus. | tests/test_bifrost_api.py | GAP | `BIFROST_CONSUME_LANE`, `BIFROST_WAKE_LANE` |
| `blobs.py` | BlobStore (Slice B1) -- a content-addressed blob store for Bifrost media/large payloads. | GAP | GAP | `AI_SETUP` |
| `bus.py` | Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams. | tests/test_bifrost_bus.py | GAP | `AGENT_ID`, `BIFROST_INCARNATION`, `BIFROST_NAMESPACE`, `BIFROST_REPLY_DEDUP_TTL_S`, `PYTEST_CURRENT_TEST` |
| `context_hints.py` | Context Hints -- compact, ephemeral, per-agent context forwarding between peers. | tests/test_context_hints_gate.py | GAP |  |
| `control.py` | Bifrost control plane -- human-in-the-loop PAUSE + runaway-loop guard for live agent collaboration. | tests/test_bifrost_control_halt.py | research\reviewed/deepseek-control-plane-ns-isolation-2026-07-12.md | `BIFROST_MAX_HOPS`, `BIFROST_MAX_REPLIES_PER_MIN`, `BIFROST_NAMESPACE` |
| `cursor_admin.py` | cursor_admin -- T076a: SANCTIONED skip-to-now for an agent's consume cursors. | GAP | GAP |  |
| `daemon_state.py` | daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope). | GAP | GAP | `BIFROST_NAMESPACE` |
| `dispatcher.py` | Dispatcher (Bifrost Mesh W2): one resident process that turns doorbell notices into wakes. | GAP | GAP |  |
| `doctor.py` | Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress, | tests/test_doctor_dead_runner_visibility.py | GAP | `AKASHIC_RECENT_INBOX_S`, `AKASHIC_STALL_HYSTERESIS_S`, `BIFROST_NAMESPACE`, `BIFROST_UI_PORT` |
| `engine_vitals.py` | engine_vitals -- gauge_snapshot(), the engine room's pulse (T079-E1). | tests/test_t079_e1_engine_vitals.py | GAP | `BIFROST_NAMESPACE` |
| `expectations.py` | expectations -- sender-side reply deadlines + redrive (T030 L4 / RB-29). | tests/test_t030_l4_expectations.py | GAP | `AKASHIC_EXPECT_TASK_SETTLE`, `BIFROST_NAMESPACE` |
| `fence_phase.py` | fence_phase -- the method board's state source (T079-E2). | GAP | GAP |  |
| `flow_trace.py` | flow_trace (R3 / T054) -- the OTel-style waterfall over lanes: what HAPPENED, in causal | tests/test_flow_trace.py | GAP | `AKASHIC_FLOW_NO_COUNT`, `BIFROST_NAMESPACE` |
| `incarnation.py` | incarnation -- who else is HERE right now, per agent id (T074 W3/R4). | tests/test_t074_incarnation_cards.py | GAP | `AKASHIC_INCARNATION_TTL_MIN`, `BIFROST_NAMESPACE` |
| `interject.py` | Adaptive interjection router -- when a human types into a live agent session, decide whether the | GAP | GAP |  |
| `lane_depths.py` | lane_depths -- the engine room's flow gauge source (T079-E2). | GAP | GAP | `BIFROST_NAMESPACE` |
| `launcher.py` | Bifrost Launcher — spawn and monitor agent processes from the Bifrost UI. | tests/test_launcher_drain.py | GAP | `LAUNCHER_AUTO_REVIVE_JITTER`, `LAUNCHER_RESTART_BACKOFF`, `LAUNCHER_RESTART_BACKOFF_MAX`, `LAUNCHER_RESTART_MAX`, `LAUNCHER_RESTART_RESET` |
| `liveness.py` | Work-progress heartbeat (L1) -- pure observability for wedge detection. | tests/test_launcher_drainer_liveness.py | docs/agent-liveness-tier-2026-07.md | `BIFROST_NAMESPACE`, `BIFROST_WEDGE_SECONDS` |
| `locks.py` | Advisory path-locks (Concurrency design C2). | tests/test_locks.py | GAP |  |
| `mailbox.py` | mailbox -- T095 M0: shadow mailbox state index over the append-only lanes. | tests/test_t095_m0_mailbox_adversarial.py | docs/comms-mailbox-design-2026-07.md | `AKASHIC_MAILBOX` |
| `nudge.py` | Bifrost nudge -- targeted, per-agent barge-in (companion to control.py's global PAUSE). | tests/test_learn_nudge.py | GAP | `BIFROST_NAMESPACE` |
| `packet_spec.py` | Packet Spec v1 -- envelope integrity + MTU library (T040 LAW; built in T043). | GAP | docs/packet-spec-v1-2026-07.md | `BIFROST_LANES_DUAL_WRITE`, `BIFROST_STALE_MS`, `BUS_MAX_MESSAGE_BYTES`, `FRAG_REASSEMBLY_TTL`, `PACKET_INTEGRITY_ENABLED`, `PACKET_INTEGRITY_TRACE`, `PACKET_TRACE_SPOT_INTERVAL` |
| `pager.py` | pager -- page-grade findings reach a HUMAN (T078-W4, the 6h-invisible killer). | tests/test_t078_w4_pager.py | GAP | `BIFROST_NAMESPACE` |
| `promoter.py` | Bifrost B2 -- the durable projection. Promote SALIENT bus messages into the append-only Ledger. | tests/test_bifrost_promoter.py | GAP | `AKASHIC_ACK_UNHANDLED_HOURS` |
| `router.py` | T060 N0: pure route explanation and bounded shadow-delivery counters. | tests/test_router_confusables.py | research\reviewed/t060-n0-shadow-router-deepseek-review-2026-07-17.md |  |
| `runner_lib.py` | core.comm.runner_lib -- shared hardening for OpenAI-compatible seat transports (K0, 2026-07-18). | GAP | GAP |  |
| `runner_lock.py` | Bifrost runner singleton-lock -- at most ONE live runner per agent id. | GAP | GAP | `BIFROST_NAMESPACE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_SESSION_ID` |
| `session_exit.py` | session_exit -- the clean-death trio (T075 M1-beta, reconciliation ruling 3). | GAP | GAP | `AKASHIC_CLEAN_DEATH` |
| `session_state.py` | Session State — snapshot the live Bifrost session so it can be resumed later. | GAP | GAP |  |
| `timescale.py` | Timescale (T030 L1 follow-up) -- ONE seam for BUGGIFY-style timeout shrinking. | GAP | GAP | `AKASHIC_TIMEOUT_MULTIPLIER` |
| `toolbox.py` | core.comm.toolbox -- the fleet's guarded tool surface (schemas + executor), shared seam. | tests/test_k0_toolbox_extraction.py | GAP | `AKASHIC_AGENT_ID`, `DEEPSEEK_MAX_CMD_TIMEOUT`, `DEEPSEEK_RECALL_AT` |
| `turn_metrics.py` | Turn metrics (progress-bars data half; co-designed claude+deepseek 2026-07-11). | tests/test_turn_metrics.py | GAP | `BIFROST_NAMESPACE` |
| `wake_seat.py` | wake_seat -- the per-session wake-seat protocol (T029 Wave 2, the R1/R16 fix). | tests/test_wake_seat.py | GAP | `AKASHIC_TOMBSTONE`, `AKASHIC_WAKE_MARKER_FRESH_MIN`, `BIFROST_NAMESPACE` |

## core/coord/  (9 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `cognitive_metrics.py` | Cognitive Efficiency Metrics — live instrumentation for the Stage-3 evidence engine. | tests/test_cognitive_metrics.py | GAP |  |
| `conductor.py` | Conductor — the impure orchestration shell over the pure task ledger (Slice D). | tests/test_conductor.py | GAP |  |
| `experiment.py` | Coordination experiment harness -- the Stage-3 evidence engine. | tests/test_coord_experiment.py | GAP |  |
| `fence_workspace.py` | Fence workspace (R2 / T053) -- the fence as a first-class object, not a naming convention. | tests/test_fence_workspace.py | GAP | `AKASHIC_FENCE_ROOT` |
| `intent.py` | Intent declaration -- Policy 0 of the coordination layer. | tests/test_boot_intent_surface.py | research\reviewed/claude-boot-intent-diagnosis-2026-07-11.md | `BIFROST_NAMESPACE` |
| `metrics.py` | Solution-Space-Shrinkage Tracker — the Metric C cross-run watchdog. | tests/narrative_metrics.py | GAP |  |
| `negotiation.py` | Negotiation round — brief window after user input where agents declare plans. | tests/test_negotiation.py | GAP |  |
| `task_costs.py` | Task cost telemetry (T056 / wishlist R5) -- per-slice ROI, honestly attributed. | GAP | GAP | `BIFROST_NAMESPACE` |
| `task_ledger.py` | Governed task ledger — the deterministic coordination substrate (Phase 1: sequential-correct). | tests/test_task_ledger.py | GAP | `AKASHIC_PROPOSED_STALE_DAYS` |

## core/learning/  (3 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `agent_memory.py` | Agent Memory: a multi-type memory for agents (decisions, experiences, reflections, approaches) | tests/test_agent_memory.py | GAP |  |
| `consolidation.py` | Consolidation: distill raw episodic memory + experiment lessons into a curated chronicle. | tests/test_consolidation.py | docs/s2-consolidation-design.md | `AI_SETUP` |
| `learning_store.py` | Learning Store: Persists and retrieves experiment outcomes via the Store. | GAP | GAP | `AI_SETUP` |

## core/recall/  (9 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `at_action.py` | Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action. | GAP | GAP | `AKASHIC_AGENT_ID`, `AKASHIC_RECALL_CACHE_TTL`, `AKASHIC_RECALL_FLOOR`, `AKASHIC_RECALL_SELF_ECHO_H`, `AKASHIC_RECALL_STATE_DIR`, `AKASHIC_STALE_CUE_DAYS` |
| `curator.py` | Recall curator (vNext loop 1) -- the funnel's triage made an ACTOR, not a report. | GAP | GAP |  |
| `dissent.py` | Dissent-finder (`core/recall`) — surface the strongest genuine COUNTER to a recalled lesson. | tests/test_dissent_capture.py | research\reviewed/t094-dissent-verdicts-claude-2026-07-18.md |  |
| `forge.py` | Forge F1 -- the Tier-0 edit gate (docs/lesson-forge-design-2026-07.md sec.4, sec.9 F1). | tests/test_forge_gate.py | docs/lesson-forge-design-2026-07.md |  |
| `forge_optimizer.py` | Forge F2 -- the optimizer pass (docs/lesson-forge-design-2026-07.md sec.5, sec.9 F2). | tests/test_forge_optimizer.py | GAP |  |
| `funnel.py` | Recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are | GAP | GAP |  |
| `knowledge_map.py` | knowledge_map (R8 / T059) -- WALK the knowledge, don't query it blind. | tests/test_knowledge_map.py | GAP | `AKASHIC_KMAP_NO_COUNT` |
| `lookback.py` | Lookback (P7 / T027) -- one question over the rationale corpus, layered, drillable. | tests/test_lookback.py | GAP | `AKASHIC_LOOKBACK_NO_COUNT` |
| `replay.py` | Forge F0 -- replay harness + data-sufficiency audit (docs/lesson-forge-design-2026-07.md sec.9). | tests/test_forge_replay.py | GAP |  |

## core/primitives/  (7 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `clusterer.py` | Clusterer (Slice C1) -- group atoms by MEANING and flag where the knowledge structure should | tests/test_clusterer.py | GAP |  |
| `consolidator.py` | Consolidator (Slice S1) -- the one engine that turns a set of records into a budgeted, | tests/test_consolidator.py | GAP |  |
| `distiller.py` | Distiller: compact many items into a token budget, keeping a pointer to each source. | tests/test_distiller.py | GAP |  |
| `embedder.py` | Embedder (Slice C0) -- the embedding substrate. One local, CPU, offline model behind a tiny | tests/test_embedder.py | GAP | `EMBED_MODEL` |
| `faithfulness.py` | Faithfulness critic (FAITH-1) -- a deterministic, NO-LLM grounding gate for distillations. | tests/test_chronicler_faithfulness.py | docs/faithfulness-research.md |  |
| `ranker.py` | Ranker: order items by relevance x importance x recency (+ relationship type) | tests/test_ranker.py | GAP |  |
| `supersession.py` | Supersession: a newer record retires an older one (temporal correctness). | tests/test_notes_supersession.py | GAP |  |

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
| `drift.py` | drift_check -- lightweight SEMANTIC drift detector over the narrative spine (prototype). | tests/test_drift.py | GAP |  |
| `episode.py` | Session bookends -- the live EPISODE layer over the narrative Chapter (Slice S1). | tests/test_episode.py | GAP |  |
| `episode_suggester.py` | Episode auto-suggester (bookends Slice S3) -- ADVISORY phase-boundary suggestions, never a forced close. | tests/test_episode_suggester.py | GAP | `AKASHIC_AGENT_ID` |
| `event_bridge.py` | EventBridge (Slice 4) -- join the narrative timeline to the raw event firehose. | tests/test_event_bridge.py | GAP |  |
| `event_promoter.py` | EventPromoter (Slice 5) -- promote salient raw events into narrative Beats. | tests/test_event_promoter.py | GAP |  |
| `health.py` | Narrative health counters (Slice W-c) -- give the silent best-effort paths a voice. | tests/test_narrative_health.py | research\reviewed/renew-stranda-health-signals-2026-07-07.md |  |
| `schema.py` | Narrative schema (Slice 0) — the data shapes of the multi-domain narrative spine. | tests/test_narrative_schema.py | docs/security-schema-implementation.md |  |
| `session.py` | Session lifecycle (Slice 1 auto-capture) -- the spine fills itself. | tests/test_notes_supersession.py | docs/session-bookends-design-2026-07.md |  |
| `tag_audit.py` | TagAuditor (Slice G2) -- detect likely mis-tags. FLAG-ONLY: it returns suspects and | tests/test_tag_audit.py | GAP |  |
| `tag_governance.py` | TagGovernor (Slice G1) -- the append-only, confidence-gated re-tag write path. | tests/test_tag_governance.py | docs/tag-governance-plan.md |  |
| `tagging.py` | Tag governance (Slice G0) -- tag-history + confidence schema. Pure data + selection | tests/test_tagging.py | GAP |  |
| `theme_assigner.py` | ThemeAssigner (Slice 5, Tier 0 heuristic) -- infer cross-cutting Themes from | GAP | GAP |  |
| `theme_discovery.py` | ThemeDiscoverer (Spine v2, slice V6) -- embedding theme inference that augments the | tests/test_theme_discovery.py | GAP | `AKASHIC_EMBED_THEMES` |
| `track_router.py` | TrackRouter (Slice 2, Tier 0 heuristic) -- infer which domain Track a Beat belongs to, | tests/test_track_router.py | GAP |  |

## core/trust/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `capabilities.py` | Capability tokens + role templates -- the atomic vocabulary of the security schema. | GAP | GAP |  |
| `registry.py` | Grant registry -- the reader over security/acl.json (source of truth), mirroring core/fleet/roster.py. | GAP | docs/t034-registry-spec-2026-07-11.md |  |

## core/fleet/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `caller.py` | The direct caller -- one-shot invocation of a local model for a BOUNDED subtask. | GAP | GAP |  |
| `roster.py` | The fleet roster -- the single source of truth for local models (docs/fleet-dispatch-design.md). | GAP | research\reviewed/deepseek-roster-playbook-counter-2026-07-18.md |  |

## core/state/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `session_checkpoint.py` | Session Checkpoint: crash-recovery checkpoint system (renamed from session_state.py 2026-07-07 to | GAP | GAP | `AI_SETUP` |
| `session_recovery.py` | Session Recovery: Recover from checkpoint and fallback infrastructure | GAP | GAP |  |

## core/codex/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `lifecycle.py` | Node lifecycle (Slice C2, delta E3) -- bi-temporal stamping + supersession as TYPE-AGNOSTIC | GAP | GAP |  |
| `schema.py` | Resource schema (Slice C2) -- the knowledge-axis node + the structural bi-temporal contract. | tests/test_narrative_schema.py | docs/security-schema-implementation.md |  |

## core/perspectives/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `reinforce.py` | ReinforcedGraph (Slice P1) -- an association graph whose edges STRENGTHEN with co-use | GAP | GAP |  |
| `schema.py` | Perspectives schema (Slice P0) -- Lens + Map shapes. Pure data, no behavior. | tests/test_narrative_schema.py | docs/security-schema-implementation.md |  |

## agent/harness/  (9 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `capture.py` | Payload-truth capture shared by every harness adapter (Integration Tiers H1). | tests/test_bifrost_console_capture.py | GAP | `AKASHIC_PAYLOAD_CAPTURE` |
| `context.py` | The auto-boot whisper shared by every harness adapter (Integration Tiers H0). | tests/test_context_hints_gate.py | docs/context-compaction-skeleton-research.md | `AKASHIC_AUTOBOOT`, `AKASHIC_WHISPER_LINES` |
| `delta.py` | The delta door (T052 / wishlist R1) -- "what changed since I was last here." | tests/test_t052_delta_door.py | research\reviewed/claude-r1-delta-door-half-2026-07-14.md | `BIFROST_NAMESPACE` |
| `guards.py` | Action-veto policy shared by every harness adapter (Integration Tiers H1). | GAP | GAP |  |
| `nudge.py` | JIT learn-nudge rate limiting shared by every harness adapter (friction audit D5). | tests/test_learn_nudge.py | GAP | `AKASHIC_LEARN_NUDGE`, `AKASHIC_LEARN_NUDGE_CAP` |
| `registry.py` | Harness registry (Integration Tiers H2): which runtimes plug into the stack, and what | GAP | docs/t034-registry-spec-2026-07-11.md |  |
| `scope.py` | Repo-scoping policy shared by every harness adapter (Integration Tiers H0). | GAP | research\reviewed/deepseek-t045-stage2-scope-review-2026-07-14.md |  |
| `seen.py` | Per-session anti-repeat state shared by every recall surface (Integration Tiers H0). | GAP | GAP | `AKASHIC_RECALL_STATE_DIR` |
| `trace.py` | Push display-only trace lines (tool calls) onto the Bifrost bus so the console shows what | tests/test_flow_trace.py | GAP | `AKASHIC_AGENT_ID`, `AKASHIC_TRACE` |

## agent/  (2 modules)

| Module | One-line spec | Pin | Paper | Flags |
|---|---|---|---|---|
| `bifrost_pull.py` | Bifrost pull-side helpers (System 5 read lane). | tests/test_bifrost_pull.py | GAP |  |
| `initializer.py` | Agent Initialization Module: Derive context from startup sources | GAP | GAP |  |
