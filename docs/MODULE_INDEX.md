# Module Index (auto-generated)

> Do NOT edit by hand. Regenerate with `py scripts/gen_arch_index.py`.
> The big picture lives in [ARCHITECTURE.md](ARCHITECTURE.md); this is the per-module detail,
> each module's line-1 docstring = its single responsibility.

## core/foundation/  (6 modules)
- `ledger.py` — Ledger: Swappable event-record interface (append-and-replay)
- `redis_connection.py` — Redis Connection: Fail-fast connectivity primitive
- `relationship_types.py` — Comprehensive Relationship Type Framework for Knowledge Graphs
- `store.py` — Store: Swappable persistence interface (full Redis-mirror)
- `streams.py` — streams -- process plumbing for long-lived agent processes (T030 L3 / RB-28).
- `timeutil.py` — timeutil -- one deterministic, timezone-safe way to turn an ISO timestamp into a

## core/events/  (3 modules)
- `event_index.py` — EventIndex (Slice V1) -- a Store-backed time index over the raw event firehose.
- `event_log.py` — EventLog (Slice 1) -- capture raw cross-agent events on an append-only Ledger.
- `event_query.py` — EventQuery (Slice 3) -- search and time-window the raw event firehose.

## core/signals/  (2 modules)
- `agent_signal_ledger.py` — Agent Signal Ledger: the ordered record of every signal agents emit
- `coordinator_api.py` — Coordinator API: Minimal signal-based logging for agents

## core/comm/  (24 modules)
- `assertions.py` — Pre-flight assertions (T068-R3 / deepseek M10) -- verify a directed answer's FACTUAL
- `bifrost_api.py` — bifrost.api -- the one door an agent uses to join and work the Bifrost bus.
- `blobs.py` — BlobStore (Slice B1) -- a content-addressed blob store for Bifrost media/large payloads.
- `bus.py` — Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams.
- `context_hints.py` — Context Hints -- compact, ephemeral, per-agent context forwarding between peers.
- `control.py` — Bifrost control plane -- human-in-the-loop PAUSE + runaway-loop guard for live agent collaboration.
- `dispatcher.py` — Dispatcher (Bifrost Mesh W2): one resident process that turns doorbell notices into wakes.
- `doctor.py` — Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress,
- `expectations.py` — expectations -- sender-side reply deadlines + redrive (T030 L4 / RB-29).
- `flow_trace.py` — flow_trace (R3 / T054) -- the OTel-style waterfall over lanes: what HAPPENED, in causal
- `incarnation.py` — incarnation -- who else is HERE right now, per agent id (T074 W3/R4).
- `interject.py` — Adaptive interjection router -- when a human types into a live agent session, decide whether the
- `launcher.py` — Bifrost Launcher — spawn and monitor agent processes from the Bifrost UI.
- `liveness.py` — Work-progress heartbeat (L1) -- pure observability for wedge detection.
- `locks.py` — Advisory path-locks (Concurrency design C2).
- `nudge.py` — Bifrost nudge -- targeted, per-agent barge-in (companion to control.py's global PAUSE).
- `packet_spec.py` — Packet Spec v1 -- envelope integrity + MTU library (T040 LAW; built in T043).
- `promoter.py` — Bifrost B2 -- the durable projection. Promote SALIENT bus messages into the append-only Ledger.
- `runner_lock.py` — Bifrost runner singleton-lock -- at most ONE live runner per agent id.
- `session_exit.py` — session_exit -- the clean-death trio (T075 M1-beta, reconciliation ruling 3).
- `session_state.py` — Session State — snapshot the live Bifrost session so it can be resumed later.
- `timescale.py` — Timescale (T030 L1 follow-up) -- ONE seam for BUGGIFY-style timeout shrinking.
- `turn_metrics.py` — Turn metrics (progress-bars data half; co-designed claude+deepseek 2026-07-11).
- `wake_seat.py` — wake_seat -- the per-session wake-seat protocol (T029 Wave 2, the R1/R16 fix).

## core/coord/  (9 modules)
- `cognitive_metrics.py` — Cognitive Efficiency Metrics — live instrumentation for the Stage-3 evidence engine.
- `conductor.py` — Conductor — the impure orchestration shell over the pure task ledger (Slice D).
- `experiment.py` — Coordination experiment harness -- the Stage-3 evidence engine.
- `fence_workspace.py` — Fence workspace (R2 / T053) -- the fence as a first-class object, not a naming convention.
- `intent.py` — Intent declaration -- Policy 0 of the coordination layer.
- `metrics.py` — Solution-Space-Shrinkage Tracker — the Metric C cross-run watchdog.
- `negotiation.py` — Negotiation round — brief window after user input where agents declare plans.
- `task_costs.py` — Task cost telemetry (T056 / wishlist R5) -- per-slice ROI, honestly attributed.
- `task_ledger.py` — Governed task ledger — the deterministic coordination substrate (Phase 1: sequential-correct).

## core/learning/  (3 modules)
- `agent_memory.py` — Agent Memory: a multi-type memory for agents (decisions, experiences, reflections, approaches)
- `consolidation.py` — Consolidation: distill raw episodic memory + experiment lessons into a curated chronicle.
- `learning_store.py` — Learning Store: Persists and retrieves experiment outcomes via the Store.

## core/recall/  (9 modules)
- `at_action.py` — Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action.
- `curator.py` — Recall curator (vNext loop 1) -- the funnel's triage made an ACTOR, not a report.
- `dissent.py` — Dissent-finder (`core/recall`) — surface the strongest genuine COUNTER to a recalled lesson.
- `forge.py` — Forge F1 -- the Tier-0 edit gate (docs/lesson-forge-design-2026-07.md sec.4, sec.9 F1).
- `forge_optimizer.py` — Forge F2 -- the optimizer pass (docs/lesson-forge-design-2026-07.md sec.5, sec.9 F2).
- `funnel.py` — Recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are
- `knowledge_map.py` — knowledge_map (R8 / T059) -- WALK the knowledge, don't query it blind.
- `lookback.py` — Lookback (P7 / T027) -- one question over the rationale corpus, layered, drillable.
- `replay.py` — Forge F0 -- replay harness + data-sufficiency audit (docs/lesson-forge-design-2026-07.md sec.9).

## core/primitives/  (7 modules)
- `clusterer.py` — Clusterer (Slice C1) -- group atoms by MEANING and flag where the knowledge structure should
- `consolidator.py` — Consolidator (Slice S1) -- the one engine that turns a set of records into a budgeted,
- `distiller.py` — Distiller: compact many items into a token budget, keeping a pointer to each source.
- `embedder.py` — Embedder (Slice C0) -- the embedding substrate. One local, CPU, offline model behind a tiny
- `faithfulness.py` — Faithfulness critic (FAITH-1) -- a deterministic, NO-LLM grounding gate for distillations.
- `ranker.py` — Ranker: order items by relevance x importance x recency (+ relationship type)
- `supersession.py` — Supersession: a newer record retires an older one (temporal correctness).

## core/renew/  (1 modules)
- `session_signals.py` — Session signals (RENEW slice A'') -- fold one session's tool calls into deterministic context-health signal ag

## core/narrative/  (17 modules)
- `beat_log.py` — BeatLog (Slice 1) -- append salient narrative Beats to the Store + read them by time.
- `chapter_lifecycle.py` — Chapter lifecycle helpers (Slice 7) — bi-temporal stamping, in-place regeneration,
- `chronicler.py` — Chronicler (Slice 3) — distill narrative Beats into Chapters + Storyline + Atlas.
- `drift.py` — drift_check -- lightweight SEMANTIC drift detector over the narrative spine (prototype).
- `episode.py` — Session bookends -- the live EPISODE layer over the narrative Chapter (Slice S1).
- `episode_suggester.py` — Episode auto-suggester (bookends Slice S3) -- ADVISORY phase-boundary suggestions, never a forced close.
- `event_bridge.py` — EventBridge (Slice 4) -- join the narrative timeline to the raw event firehose.
- `event_promoter.py` — EventPromoter (Slice 5) -- promote salient raw events into narrative Beats.
- `health.py` — Narrative health counters (Slice W-c) -- give the silent best-effort paths a voice.
- `schema.py` — Narrative schema (Slice 0) — the data shapes of the multi-domain narrative spine.
- `session.py` — Session lifecycle (Slice 1 auto-capture) -- the spine fills itself.
- `tag_audit.py` — TagAuditor (Slice G2) -- detect likely mis-tags. FLAG-ONLY: it returns suspects and
- `tag_governance.py` — TagGovernor (Slice G1) -- the append-only, confidence-gated re-tag write path.
- `tagging.py` — Tag governance (Slice G0) -- tag-history + confidence schema. Pure data + selection
- `theme_assigner.py` — ThemeAssigner (Slice 5, Tier 0 heuristic) -- infer cross-cutting Themes from
- `theme_discovery.py` — ThemeDiscoverer (Spine v2, slice V6) -- embedding theme inference that augments the
- `track_router.py` — TrackRouter (Slice 2, Tier 0 heuristic) -- infer which domain Track a Beat belongs to,

## core/trust/  (2 modules)
- `capabilities.py` — Capability tokens + role templates -- the atomic vocabulary of the security schema.
- `registry.py` — Grant registry -- the reader over security/acl.json (source of truth), mirroring core/fleet/roster.py.

## core/fleet/  (2 modules)
- `caller.py` — The direct caller -- one-shot invocation of a local model for a BOUNDED subtask.
- `roster.py` — The fleet roster -- the single source of truth for local models (docs/fleet-dispatch-design.md).

## core/state/  (2 modules)
- `session_checkpoint.py` — Session Checkpoint: crash-recovery checkpoint system (renamed from session_state.py 2026-07-07 to
- `session_recovery.py` — Session Recovery: Recover from checkpoint and fallback infrastructure

## core/codex/  (2 modules)
- `lifecycle.py` — Node lifecycle (Slice C2, delta E3) -- bi-temporal stamping + supersession as TYPE-AGNOSTIC
- `schema.py` — Resource schema (Slice C2) -- the knowledge-axis node + the structural bi-temporal contract.

## core/perspectives/  (2 modules)
- `reinforce.py` — ReinforcedGraph (Slice P1) -- an association graph whose edges STRENGTHEN with co-use
- `schema.py` — Perspectives schema (Slice P0) -- Lens + Map shapes. Pure data, no behavior.

## entry points (repo root)
- `agent_cli.py` — agent_cli.py -- THE single door an external agent (e.g. OpenCode) uses.
- `ai_setup_mcp.py` — ai_setup_mcp.py -- the MCP-transport door into the Akashic Aurora (System 5).
- `bootstrap.py` — Bootstrap — system entry point & honest status check
- `config.py` — Centralized Configuration - Akashic Aurora

## scripts/
- `arc_scorecard.py` — arc_scorecard.py -- T031 hook 3: the wrap-time M-practice scorecard.
- `ask_deepseek.py` — ask_deepseek -- a thin bridge so an agent (or you) can get DeepSeek's take from the CLI.
- `ask_gemini.py` — ask_gemini -- a thin bridge so an agent (or you) can get Gemini's take from the CLI.
- `ask_gemini_vision.py` — ask_gemini_vision -- send an image file to Gemini for description/analysis.
- `ask_gpt.py` — ask_gpt -- a thin bridge so an agent (or you) can get OpenAI/GPT's take from the CLI.
- `ask_panel.py` — ask_panel -- fan ONE question out to the frontier-model panel (Gemini + GPT + DeepSeek) and print
- `bifrost_console.py` — Bifrost Console -- a live chat window onto the Bifrost bus.
- `bifrost_daemon.py` — bifrost.daemon -- the agent's continuous-presence body (T075 M1-alpha skeleton).
- `bifrost_runner.py` — bifrost_runner -- make a stateless model (Gemini) a FIRST-CLASS Bifrost citizen.
- `bifrost_runner_deepseek.py` — bifrost_runner_deepseek -- make DeepSeek (a stateless API model) a FIRST-CLASS Bifrost citizen.
- `bifrost_ui.py` — bifrost_ui -- a realtime web console for watching (and steering) live agent collaboration on Bifrost.
- `bifrost_wake.py` — bifrost.wake -- the canonical wake listener for a Bifrost agent (the receive/wake arm of bifrost.api).
- `check_boundaries.py` — Boundary guardrails for the clean core/ layer.
- `check_comprehensibility.py` — check_comprehensibility -- the guard that keeps the comprehension layer honest (the immune system).
- `check_doc_currency.py` — check_doc_currency -- P4 (T024): no dead law under docs/.
- `check_doc_freshness.py` — Doc-freshness guardrail -- the repo ROOT holds only living, intentionally-maintained docs.
- `check_door_parity.py` — check_door_parity -- guard the agent-facing DOOR surface against silent fragmentation.
- `check_preregistration.py` — check_preregistration.py -- T031 hook 2: M3's forcing function at ship time.
- `check_reconciliation_gate.py` — check_reconciliation_gate.py -- T031 hook 1: the method baseline's lead forcing function.
- `check_verbatim_citation.py` — check_verbatim_citation.py -- T031 hook 4: M6's forcing function at ship time.
- `check_wiring.py` — check_wiring -- the Built != Wired gate (membrane slice 2).
- `deepseek_chat.py` — deepseek_chat -- an interactive, TOOL-USING conversation with DeepSeek, in its own window.
- `gemini_web.py` — gemini_web -- ask Gemini through the FREE web surfaces (not API quota).
- `gen_arch_index.py` — gen_arch_index -- regenerate docs/MODULE_INDEX.md from every module's one-line docstring.
- `harmonize_knowledge.py` — harmonize_knowledge.py — one-time knowledge-store harmonization (2026-06-20)
- `migrate_time_scores.py` — One-time migration (S5): re-score the persisted time-zsets with the unified `to_epoch`.
- `mirror.py` — mirror.py -- commit local changes and push to GitHub in one step.
- `rb25_storm_burst.py` — (no docstring)
- `seed_narrative.py` — seed_narrative.py -- dogfood the spine: ingest real git history as Beats, then chronicle.
- `ship.py` — ship.py -- one disciplined command to ship a slice: GATE -> commit+push -> (lesson) -> snapshot.
- `snapshot.py` — Snapshot the current Bifrost session for later resume. Run before shutting down.
- `snapshot_knowledge.py` — snapshot_knowledge.py -- backup & restore the live knowledge layer.
- `worktree.py` — worktree.py -- per-agent git worktrees (Concurrency design C1).
