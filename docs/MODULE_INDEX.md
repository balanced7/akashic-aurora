# Module Index (auto-generated)

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_arch_index.py`.
> The big picture lives in [ARCHITECTURE.md](ARCHITECTURE.md); this is the per-module detail,
> each module's line-1 docstring = its single responsibility.

## core/foundation/  (9 modules)
- `durable_reconcile.py` — Per-family authority reconcile: make the durable source COMPLETE before migrating.
- `ledger.py` — Ledger: Swappable event-record interface (append-and-replay)
- `migrate_to_sqlite.py` — JSON FileStore -> SqliteStore migration: shadow-build, census law, honest verify.
- `redis_connection.py` — Redis Connection: Fail-fast connectivity primitive
- `relationship_types.py` — Comprehensive Relationship Type Framework for Knowledge Graphs
- `sqlite_store.py` — SqliteStore -- the durable Store backend with real cross-process safety.
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

## core/comm/  (51 modules)
- `ask.py` — ask -- a synchronous helper call, with no seat behind it (T171).
- `ask_bg.py` — ask_bg -- a helper call that outlives your turn without becoming a seat (T205).
- `ask_state.py` — ask_state -- one durable ask's honest state (T196d).
- `assertions.py` — Pre-flight assertions (T068-R3 / deepseek M10) -- verify a directed answer's FACTUAL
- `bifrost_api.py` — bifrost.api -- the one door an agent uses to join and work the Bifrost bus.
- `blobs.py` — BlobStore (Slice B1) -- a content-addressed blob store for Bifrost media/large payloads.
- `bus.py` — Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams.
- `context_hints.py` — Context Hints -- compact, ephemeral, per-agent context forwarding between peers.
- `control.py` — Bifrost control plane -- human-in-the-loop PAUSE + runaway-loop guard for live agent collaboration.
- `control_channel.py` — Out-of-band control: a loopback listener that survives a dead bus.
- `cursor_admin.py` — cursor_admin -- T076a: SANCTIONED skip-to-now for an agent's consume cursors.
- `daemon_state.py` — daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope).
- `dispatcher.py` — Dispatcher (Bifrost Mesh W2): one resident process that turns doorbell notices into wakes.
- `doctor.py` — Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress,
- `door_probe.py` — door_probe -- does the MCP door actually answer, right now, in THIS environment?
- `engine_vitals.py` — engine_vitals -- gauge_snapshot(), the engine room's pulse (T079-E1).
- `expectations.py` — expectations -- sender-side reply deadlines + redrive (T030 L4 / RB-29).
- `failure_class.py` — failure_class -- name the cause of a dead ask, and say what to do about it (T202).
- `fence_phase.py` — fence_phase -- the method board's state source (T079-E2).
- `flow_trace.py` — flow_trace (R3 / T054) -- the OTel-style waterfall over lanes: what HAPPENED, in causal
- `friction.py` — friction -- read the collaboration tax from evidence that already exists (T196a).
- `incarnation.py` — incarnation -- who else is HERE right now, per agent id (T074 W3/R4).
- `interject.py` — Adaptive interjection router -- when a human types into a live agent session, decide whether the
- `lane_depths.py` — lane_depths -- the engine room's flow gauge source (T079-E2).
- `launcher.py` — Bifrost Launcher — spawn and monitor agent processes from the Bifrost UI.
- `liveness.py` — Work-progress heartbeat (L1) -- pure observability for wedge detection.
- `locks.py` — Advisory path-locks (Concurrency design C2).
- `mailbox.py` — mailbox -- T095 M0: shadow mailbox state index over the append-only lanes.
- `nudge.py` — Bifrost nudge -- targeted, per-agent barge-in (companion to control.py's global PAUSE).
- `packet_spec.py` — Packet Spec v1 -- envelope integrity + MTU library (T040 LAW; built in T043).
- `pager.py` — pager -- page-grade findings reach a HUMAN (T078-W4, the 6h-invisible killer).
- `peer_ready.py` — peer_ready -- make the peer EXIST before asking it something (T197c).
- `promoter.py` — Bifrost B2 -- the durable projection. Promote SALIENT bus messages into the append-only Ledger.
- `reaper.py` — reaper -- S4: a dead seat's unread directed mail re-homes, loudly. Never stranded.
- `role_queue.py` — role_queue -- T108 S1: load-balanced role-addressed work with claim semantics.
- `room_feed.py` — Namespace-aware feed-stream discovery -- the backend half of readable side rooms.
- `roster.py` — roster -- S2: the lobby. Per-seat liveness the whole fleet can read.
- `router.py` — T060 N0: pure route explanation and bounded shadow-delivery counters.
- `runner_lib.py` — core.comm.runner_lib -- shared hardening for OpenAI-compatible seat transports (K0, 2026-07-18).
- `runner_lock.py` — Bifrost runner singleton-lock -- at most ONE live runner per agent id.
- `runtime_age.py` — runtime_age (T116) -- how much code a RUNNING process cannot possibly contain.
- `seat_identity.py` — seat_identity -- WHO AM I, resolved per SESSION instead of per PROCESS.
- `self_restart.py` — self_restart (A1) -- a runner that knows it is stale restarts itself.
- `session_exit.py` — session_exit -- the clean-death trio (T075 M1-beta, reconciliation ruling 3).
- `session_state.py` — Session State — snapshot the live Bifrost session so it can be resumed later.
- `storm_detect.py` — storm_detect — S0-beta storm signature detection (lane-depth spike + repeat-delivery).
- `timescale.py` — Timescale (T030 L1 follow-up) -- ONE seam for BUGGIFY-style timeout shrinking.
- `toolbox.py` — core.comm.toolbox -- the fleet's guarded tool surface (schemas + executor), shared seam.
- `triage_park.py` — Triage park (S0-alpha) -- the scry-to-bottom bench.
- `turn_metrics.py` — Turn metrics (progress-bars data half; co-designed claude+deepseek 2026-07-11).
- `wake_seat.py` — wake_seat -- the per-session wake-seat protocol (T029 Wave 2, the R1/R16 fix).

## core/coord/  (15 modules)
- `capability_search.py` — capability_search -- "does this system already do X?", asked at the level of MEANING.
- `cognitive_metrics.py` — Cognitive Efficiency Metrics — live instrumentation for the Stage-3 evidence engine.
- `conductor.py` — Conductor — the impure orchestration shell over the pure task ledger (Slice D).
- `defer_queue.py` — defer_queue — the capability-gated standing queue (W33, seat-zero wave B3).
- `experiment.py` — Coordination experiment harness -- the Stage-3 evidence engine.
- `fence_workspace.py` — Fence workspace (R2 / T053) -- the fence as a first-class object, not a naming convention.
- `intent.py` — Intent declaration -- Policy 0 of the coordination layer.
- `method_drift.py` — method_drift -- the one method number that reaches a channel people actually read.
- `metrics.py` — Solution-Space-Shrinkage Tracker — the Metric C cross-run watchdog.
- `negotiation.py` — Negotiation round — brief window after user input where agents declare plans.
- `preregistration.py` — preregistration -- M3's pre-registration metric, as numbers (T123 boundary fix).
- `suite_baseline.py` — suite_baseline — the test-suite receipt the next seat diffs instead of re-deriving (W34/B4).
- `task_costs.py` — Task cost telemetry (T056 / wishlist R5) -- per-slice ROI, honestly attributed.
- `task_ledger.py` — Governed task ledger — the deterministic coordination substrate (Phase 1: sequential-correct).
- `timeline.py` — timeline -- one chronological SET across domains (T211).

## core/learning/  (5 modules)
- `agent_memory.py` — Agent Memory: a multi-type memory for agents (decisions, experiences, reflections, approaches)
- `consolidation.py` — Consolidation: distill raw episodic memory + experiment lessons into a curated chronicle.
- `domains.py` — Recall domains — the boundary line, and why it is not a tag.
- `learning_store.py` — Learning Store: Persists and retrieves experiment outcomes via the Store.
- `vfx_chunk_lessons.py` — Adopt the VFX chunk rules into recall — as a PROJECTION, not a migration.

## core/recall/  (13 modules)
- `anchors.py` — Lesson anchor resolver -- does a lesson's premise still hold?
- `at_action.py` — Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action.
- `curator.py` — Recall curator (vNext loop 1) -- the funnel's triage made an ACTOR, not a report.
- `dissent.py` — Dissent-finder (`core/recall`) — surface the strongest genuine COUNTER to a recalled lesson.
- `forge.py` — Forge F1 -- the Tier-0 edit gate (docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204
- `forge_optimizer.py` — Forge F2 -- the optimizer pass (docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.m
- `funnel.py` — Recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are
- `gate_rules.py` — gate_rules (R2 slice 1a) -- three principles about an action's relationship to
- `knowledge_map.py` — knowledge_map (R8 / T059) -- WALK the knowledge, don't query it blind.
- `lookback.py` — Lookback (P7 / T027) -- one question over the rationale corpus, layered, drillable.
- `pack_replay.py` — pack_replay (R2) -- replay the frozen census pack through TODAY's recall pipeline.
- `precision_audit.py` — precision_audit -- the missing instrument: is recall ACCURATE?
- `replay.py` — Forge F0 -- replay harness + data-sufficiency audit (docs/library/design/20260701_lesson-forge-evidence-gated-

## core/primitives/  (8 modules)
- `clusterer.py` — Clusterer (Slice C1) -- group atoms by MEANING and flag where the knowledge structure should
- `consolidator.py` — Consolidator (Slice S1) -- the one engine that turns a set of records into a budgeted,
- `distiller.py` — Distiller: compact many items into a token budget, keeping a pointer to each source.
- `embedder.py` — Embedder (Slice C0) -- the embedding substrate. One local, CPU, offline model behind a tiny
- `epistemic.py` — Pure typed epistemic view for honest render surfaces.
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

## core/trust/  (3 modules)
- `capabilities.py` — Capability tokens + role templates -- the atomic vocabulary of the security schema.
- `grant_writer.py` — core.trust.grant_writer -- the WRITE side of security/acl.json (T163, S-3 of the security schema).
- `registry.py` — Grant registry -- the reader over security/acl.json (source of truth), mirroring core/fleet/model_roster.py (r

## core/fleet/  (2 modules)
- `caller.py` — The direct caller -- one-shot invocation of a local model for a BOUNDED subtask.
- `model_roster.py` — The fleet roster -- the single source of truth for local models (docs/library/design/20260709_fleet-dispatch-a

## core/state/  (2 modules)
- `session_checkpoint.py` — Session Checkpoint: crash-recovery checkpoint system (renamed from session_state.py 2026-07-07 to
- `session_recovery.py` — Session Recovery: Recover from checkpoint and fallback infrastructure

## core/codex/  (2 modules)
- `lifecycle.py` — Node lifecycle (Slice C2, delta E3) -- bi-temporal stamping + supersession as TYPE-AGNOSTIC
- `schema.py` — Resource schema (Slice C2) -- the knowledge-axis node + the structural bi-temporal contract.

## core/perspectives/  (2 modules)
- `reinforce.py` — ReinforcedGraph (Slice P1) -- an association graph whose edges STRENGTHEN with co-use
- `schema.py` — Perspectives schema (Slice P0) -- Lens + Map shapes. Pure data, no behavior.

## core/context/  (9 modules)  ⚠️ NOT in ARCHITECTURE.md layer order — add it there
- `aggregator.py` — Aggregator: assemble the agent's starting context within a token budget.
- `arch_loader.py` — Arch-slice loader (Context pillar): boot-time ORIENTATION to the code region of the current task.
- `blocker_loader.py` — Blocker loader: surface the active blockers preventing progress, ranked.
- `briefing_loader.py` — Briefing loader: the most recent handoff briefing addressed to an agent.
- `decision_loader.py` — Decision loader: surface the decisions most applicable to a task, ranked.
- `learning_loader.py` — Learning loader: surface the learnings most relevant to a task, ranked.
- `narrative_loader.py` — Narrative loader (Slice 7) — recent Atlas + active chapters for agent boot context.
- `project_context.py` — Project Context Manager: Store-backed multi-agent context
- `relevance_budget.py` — T071-R1 relevance budget v1 -- boot's lesson section becomes MOST-RELEVANT under a

## core/infrastructure/  (1 modules)  ⚠️ NOT in ARCHITECTURE.md layer order — add it there
- `health_check.py` — Startup Diagnostics: Report on initialization health

## core/library/  (4 modules)  ⚠️ NOT in ARCHITECTURE.md layer order — add it there
- `atoms.py` — The artifact-atom family (A1 core) -- atoms as truth, JSONL as the durable record.
- `legacy_map.py` — The legacy_path -> art_id map (T109): the migration's missing handle, finally wired.
- `projection.py` — Projection renderer (A1) -- one atom -> one read-only markdown file.
- `taxonomy.py` — Taxonomy constants + the birth-door classifier (A1, homes-and-order round).

## core/season/  (1 modules)  ⚠️ NOT in ARCHITECTURE.md layer order — add it there
- `scoring.py` — core.season.scoring -- Season 1 scoring, as a pure function over data (T165).

## core/toolbelt/  (10 modules)  ⚠️ NOT in ARCHITECTURE.md layer order — add it there
- `audit.py` — audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain #1).
- `audit_spend.py` — audit_spend — the SPEND domain for core.toolbelt.audit (kimi build, partner night R3).
- `clobber_scan.py` — clobber_scan — unconditional shared-control-key writes, flagged statically (W47).
- `contest.py` — contest (T099 · play tier) -- second a toast with proof (kimi's R2 build).
- `followup.py` — followup — the question-back channel for fire-and-forget charters (W46).
- `kit.py` — kit (T099 · KIT tier) — installable bundles of belt entries (kimi, PASS 2 build).
- `play_sandbox.py` — play_sandbox (T099 · play-tier sandbox) — the bounded subprocess that runs play tools.
- `registry.py` — Toolbelt registry (T099 · V0 self-tooling) -- agent-authored verb compositions.
- `tally.py` — tally — the blind-counter consensus matrix (W48).
- `toast.py` — toast (T099 · tools-hunt BETA-2) -- gratitude with a receipt (kimi's hunt B3).

## entry points (repo root)
- `_scratch_extract_lines.py` — (no docstring)
- `agent_cli.py` — agent_cli.py -- THE single door an external agent (e.g. OpenCode) uses.
- `ai_setup_mcp.py` — ai_setup_mcp.py -- the MCP-transport door into the Akashic Aurora (System 5).
- `bootstrap.py` — Bootstrap — system entry point & honest status check
- `config.py` — Centralized Configuration - Akashic Aurora

## scripts/
- `arc_scorecard.py` — (no docstring)
- `arc_thread.py` — arc_thread.py -- door 2 of the library (LIBRARY.md): "trace our steps," materialized.
- `ask_deepseek.py` — ask_deepseek -- a thin bridge so an agent (or you) can get DeepSeek's take from the CLI.
- `ask_gemini.py` — ask_gemini -- a thin bridge so an agent (or you) can get Gemini's take from the CLI.
- `ask_gemini_vision.py` — ask_gemini_vision -- send an image file to Gemini for description/analysis.
- `ask_gpt.py` — ask_gpt -- a thin bridge so an agent (or you) can get OpenAI/GPT's take from the CLI.
- `ask_kimi.py` — ask_kimi -- a thin bridge so an agent (or you) can get Kimi's take from the CLI.
- `ask_panel.py` — ask_panel -- fan ONE question out to the frontier-model panel (Gemini + GPT + DeepSeek) and print
- `bifrost_child.py` — bifrost_child -- managed subprocess + daemon singleton lock (T075 M1-delta).
- `bifrost_console.py` — Bifrost Console -- a live chat window onto the Bifrost bus.
- `bifrost_daemon.py` — bifrost.daemon -- the agent's continuous-presence body (T075 M1-alpha + M1-delta).
- `bifrost_runner.py` — bifrost_runner -- make a stateless model (Gemini) a FIRST-CLASS Bifrost citizen.
- `bifrost_runner_deepseek.py` — bifrost_runner_deepseek -- make DeepSeek (a stateless API model) a FIRST-CLASS Bifrost citizen.
- `bifrost_runner_gemini.py` — bifrost_runner_gemini -- make gemini (gemini-k3, Moonshot) a FIRST-CLASS Bifrost citizen.
- `bifrost_runner_kimi.py` — bifrost_runner_kimi -- make Kimi (kimi-k3, Moonshot) a FIRST-CLASS Bifrost citizen.
- `bifrost_runner_sol.py` — bifrost_runner_sol -- make Sol (gpt-5.6-sol, OpenAI Responses API) a FIRST-CLASS Bifrost citizen.
- `bifrost_ui.py` — bifrost_ui -- a realtime web console for watching (and steering) live agent collaboration on Bifrost.
- `bifrost_wake.py` — bifrost.wake -- the canonical wake listener for a Bifrost agent (the receive/wake arm of bifrost.api).
- `canary_oracle.py` — The canary oracle -- the control that separates "the system improved" from "the attackers tired".
- `capture_apple_hig.py` — capture_apple_hig.py — harvest Apple HIG component sub-sections into refs/design-inspiration.
- `corpus_digests.py` — corpus_digests -- land structured corpus digests as a durable, queryable dataset.
- `deepseek_chat.py` — deepseek_chat -- an interactive, TOOL-USING conversation with DeepSeek, in its own window.
- `enrich_corpus.py` — A3 migration pipeline: the ~900-file corpus -> enriched atoms, verified, gated.
- `g_recall_at_seed.py` — (no docstring)
- `gemini_chat.py` — gemini_chat -- the gemini seat's model transport: gemini-1.5-pro as a first-class Akashic citizen.
- `gemini_web.py` — gemini_web -- ask Gemini through the FREE web surfaces (not API quota).
- `harmonize_knowledge.py` — harmonize_knowledge.py — one-time knowledge-store harmonization (2026-06-20)
- `kimi_chat.py` — kimi_chat -- the Kimi seat's model transport: kimi-k3 (Moonshot) as a first-class Akashic citizen.
- `kimi_walk_narrator.py` — kimi_walk_narrator -- stream kimi's FULL REASONING from its Claude-Code session transcript
- `mcp_register.py` — T081-W2: make the akashic-aurora MCP door attach from ANY launch cwd.
- `migrate_time_scores.py` — One-time migration (S5): re-score the persisted time-zsets with the unified `to_epoch`.
- `mirror.py` — mirror.py -- commit local changes and push to GitHub in one step.
- `rb25_storm_burst.py` — SUPERSEDED tombstone -- points old references to the canonical RB-25 storm-burst drill.
- `repair_learning_index.py` — Repair `learn:experiments:all` -- the index that decides what recall can SEE.
- `round_archive.py` — round_archive -- a round's evidence outlives the round, so a scorer can be replaced (T190).
- `run_job.py` — Durable one-shot job supervision for long Akashic operations (T093).
- `runner_token_journal.py` — runner_token_journal -- daily token-count ledger (T078 W1: C6 meter).
- `season_dryrun.py` — season_dryrun -- run the Season 1 bounty loop end to end against a shadow tree (W6).
- `season_fan_calibration.py` — Matched DeepSeek calibration: redundant replication versus positional sharding (T195).
- `season_llm_player.py` — season_llm_player -- an LLM player for the Season 1 bounty loop (T184).
- `seed_narrative.py` — seed_narrative.py -- dogfood the spine: ingest real git history as Beats, then chronicle.
- `ship.py` — ship.py -- one disciplined command to ship a slice: GATE -> commit+push -> (lesson) -> snapshot.
- `ship_gate.py` — ship_gate -- the suite gate as a ONE-WAY RATCHET (T031 unblock, 2026-07-27).
- `snapshot.py` — Snapshot the current Bifrost session for later resume. Run before shutting down.
- `sol_chat.py` — sol_chat -- the Sol seat's model transport: gpt-5.6-sol (OpenAI) as a first-class Akashic citizen.
- `ui_shot.py` — Headless screenshots of the live console -- the EYES half of the design loop.
- `vfx_ingest.py` — Turn a pasted Shadertoy shader into one the bench can compile, and SAY WHAT IT CHANGED.
- `vfx_probe_chroma.py` — Probe: chroma-aware structured metrics over real bench PNGs.
- `vfx_probe_metrics.py` — Probe: do structured metrics surface anything a PNG does not?
- `vfx_render.py` — Render something in the VFX bench from the command line, and get a file path back.
- `wire_journal.py` — The API wire journal -- Wireshark-grade forensics for our own model traffic (T156 WIRE-A).
- `worktree.py` — worktree.py -- per-agent git worktrees (Concurrency design C1).
