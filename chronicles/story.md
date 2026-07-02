# Story — generated 2026-07-02T02:52:25.856601

Version: 0

## Atlas
- **ai-setup**: 16 chapter(s)
- **research**: 4 chapter(s)
- **vision**: 1 chapter(s)

Summary: ai-setup: 16 chapter(s); research: 4 chapter(s); vision: 1 chapter(s)

## Update bootstrap.md with project context initialization step (ai-setup)
Span: 2026-04-15T01:21:48-04:00 → 2026-04-15T02:12:35-04:00
Beats: 9  · Critic: True

- Update bootstrap.md with project context initialization step  (source: git:0aab01cdd44a)
- Add project context system for multi-agent context awareness  (source: git:510c347f2366)
- Complete rewrite of bootstrap.md - foolproof startup for any new OpenCode instance  (source: git:87eed675c31e)
- Update bootstrap.md with Redis HA, MCP, and Redis Sync startup  (source: git:e91b96700015)
- Add MCP server and Redis sync service  [relates: member_of]  (source: git:54fc1c04773c)
- Add persistent Redis sync poller  (source: git:754674b1446f)
- Redis HA deployment with triple redundancy  [relates: member_of]  (source: git:b41e88c8342e)
- Add multi-agent comm system and Redis HA  [relates: member_of]  (source: git:f641195f6e8d)
- Initial BreakThrough Stack commit  [relates: member_of]  (source: git:cdcf354da98a)

## conftest.py to fix path; clear shared store keys per-test for count assertion... (ai-setup)
Span: 2026-06-27T12:50:14-04:00 → 2026-06-27T22:25:08.548966
Beats: 31  · Critic: True

- conftest.py to fix path; clear shared store keys per-test for count assertions; retire pre-rebuild tests to _archive instead of leaving false-signal broken collection  [relates: member_of]  (source: learn:experiment:narrative_test_suite_hermeticity)
- Any code touching a foreign namespace must use that namespace's real Redis type (hset/hgetall here); add a test that stores the record as a HASH (not a string) so...  [relates: member_of]  (source: learn:experiment:narrative_filestore_vs_redis_wrongtype)
- Themes are multi-label so gate on micro-F1 over (beat,theme) pairs, NOT NMI (NMI assumes a partition); label gold by MEANING independent of the assigner keywords so the...  [relates: member_of]  (source: learn:experiment:narrative_slice8_eval_harness)
- A metric must be able to FAIL: write a test that drops a high-weight item and assert the metric falls. Measure summary inclusion vs all candidates, not the included set...  [relates: member_of]  (source: learn:experiment:narrative_metric_pinned_at_100)
- Wire heuristic assigners into emit at write-time (assign-at-write); when adding a Slice verify the production call path exists, not just unit tests on the class  [relates: member_of]  (source: learn:experiment:narrative_slice5_themeassigner_not_wired)
- Slice 2 complete -- see narrative_slice_2_trackrouter. Next: Slice 7 boot feed.  (source: learn:experiment:narrative_slice_1_beatlog)
- Import isolate_canonical in subprocess CLI tests; never mix beat_log and chronicle stores  (source: learn:experiment:narrative_test_isolation_gap)
- Commit untracked narrative files; next is Slice 7 bi-temporal plus boot feed  (source: learn:experiment:narrative_slices_3_5_built)
- TrackRouter Tier 0 is default; Slice 6 embeddings failed ablation -- do not ship as default  (source: learn:experiment:narrative_slice_2_trackrouter)
- The shared memory system is functional. Experiments are found by their experiment_name or keyword overlap in recommendation text.  (source: learn:experiment:shared_memory_verification)
- Slice 2: TrackRouter (heuristic) + gold fixture + benchmark metrics; ARI 0.86 / WindowDiff 0.15 (bar met); routing wired into emit  (source: git:043d55b24e22)
- Slice 1: BeatLog (time-ordered Beats) + learn->Beat & mirror-commit->Beat hooks + tests  (source: git:d5a1d58452b9)
- Next Slice 2: TrackRouter heuristic to route Beats to domain Tracks. Beats currently unrouted (track=None)  [relates: member_of]  (source: learn:experiment:narrative_slice_1_beatlog)
- Slice 8: narrative evaluation harness + gold themes/QA + multi-label metric  [relates: member_of]  (source: git:ab21b4551f94)
- Review fixes: wire ThemeAssigner, make coverage/faithfulness real, harden Slice 7  [relates: member_of]  (source: git:15b3658feccb)
- Narrative Slices 3-7: Chronicler, story CLI, themes, boot feed, test isolation  [relates: member_of]  (source: git:df771d1f80ed)
- Slice 0: narrative schema (Beat/Chapter/Track/Theme/Atlas/Edge) + edge validation vs real 66-type vocab + lexicon; fix fake relationship names in design  [relates: member_of]  (source: git:dea5829af72e)
- Fix stale bootstrap.md: mark Systems 1-5 built, CLI init, current status + stale-doc warning  (source: git:3f8fd8945b04)
- Agent-interface refinements + knowledge backup/restore tooling  [relates: member_of]  (source: git:2aba7a181f51)
- Post-refactor architecture baseline (Store/Ledger + primitives + Context + ACI)  [relates: member_of]  (source: git:10a960c05305)
- Capture perspectives+maps design note (schema-on-read + lenses for agent memory); record research  (source: git:fcf1ee6cbb20)
- Add narrative test & verification plan: per-slice acceptance bars + benchmark metrics + self-tests  (source: git:6b0d501091f7)
- Add closest-analogues research (RAPTOR/GraphRAG/HippoRAG/Amory + Zettelkasten/PARA) + what we uniquely combine  [relates: member_of]  (source: git:6c6489593161)
- Multi-domain narrative: Tracks/Themes + relationship-type edge schema + TrackRouter (context-inferred) + revised slices  [relates: member_of]  (source: git:ccc86487040c)
- Refine narrative-spine plan with our naming/architecture research; resolve the 4 decisions  [relates: member_of]  (source: git:cdf05cff5954)
- Add narrative-spine design plan (System 4 capstone) w/ prior-art lessons  [relates: member_of]  (source: git:83e70b7d7e74)
- Agent-init discovery endpoint + followable source pointers + py auto-detect  (source: git:9a7c41a745d7)
- Add scripts/mirror.py: one-step commit + push helper  [relates: member_of]  (source: git:0abcc62f6881)
- Session ended  (source: bootstrap:end)
- Wired session logging: bootstrap emits session-start, agent_cli log subcommand, story --session-end  (source: session:wireup)
- Session started  (source: bootstrap:start)

## Frame salience() honestly as a Tier-0 baseline with the embedding/LLM poignan... (research)
Span: 2026-06-27T20:35:28.900770 → 2026-06-27T23:44:09.992055
Beats: 7  · Critic: True

- Frame salience() honestly as a Tier-0 baseline with the embedding/LLM poignancy scorer as a documented drop-in seam at one function. Gate any upgrade behind an ablation...  [relates: member_of]  (source: learn:experiment:Heuristic importance scoring is a Tier-0 baseline, not the answer)
- Reuse the established design: per-event importance score, promote when it crosses a THRESHOLD (natural rate-limit, not a schedule), preserve a provenance pointer to the...  (source: learn:experiment:Salience promotion is the reflection/consolidation layer (prior art))
- Keep heuristic as default Tier 0; optional experimental Tier 1 behind flag only  (source: learn:experiment:narrative_slice_6_ablation_failed)
- Tier 1 embedding routing skipped - keeping heuristic as default router  (source: session:slice6)
- Benchmark showed embedding ARI=0.212 vs heuristic ARI=0.754 - ablation gate not met  (source: session:slice6)
- Capture now build later (rule of three, after narrative graph has edges). See docs/perspectives-maps-design-note.md. Honest bound: superlinear leverage not exponential...  (source: learn:experiment:perspectives_maps_swappable_interpretation)
- Researched Slice 6 embedding routing: SBERT centroid-based vs heuristic on gold fixture  (source: session:slice6)

## Slice 1 finished (mark_chapter + auto-capture), dogfood seed, doc-freshness g... (ai-setup)
Span: 2026-06-27T22:25:17.311691 → 2026-06-27T22:25:17.311691
Beats: 1  · Critic: True

- Slice 1 finished (mark_chapter + auto-capture), dogfood seed, doc-freshness guardrail, robustness sweep  [relates: member_of]  (source: mark:2026-06-27T22:25:17.311691)

## Auto-logger Slice 2 shipped: capture auto-hooks on boot/learn/log/commit/session (ai-setup)
Span: 2026-06-27T23:15:01.311967 → 2026-06-27T23:15:01.311967
Beats: 1  · Critic: True

- Auto-logger Slice 2 shipped: capture auto-hooks on boot/learn/log/commit/session  [relates: member_of]  (source: agent_cli:slice2)

## Auto-logger Slice 2 shipped: capture auto-hooks on boot/learn/log/commit/session (ai-setup)
Span: 2026-06-27T23:15:01.330970 → 2026-06-27T23:15:01.330970
Beats: 1  · Critic: True

- Auto-logger Slice 2 shipped: capture auto-hooks on boot/learn/log/commit/session  [relates: member_of]  (source: event:events:raw:1782602101332-0)

## Auto-logger Slice 5 shipped: salience promotion (reflection/consolidation) - ... (ai-setup)
Span: 2026-06-27T23:42:48.338753 → 2026-06-28T00:09:46.051000
Beats: 8  · Critic: True

- Auto-logger Slice 5 shipped: salience promotion (reflection/consolidation) - score raw events, promote salient ones to Beats with provenance, rate-limited...  (source: agent_cli:slice5)
- Perspectives P0+P1: Lens/Map schema + ReinforcedGraph (bounded Hebbian + half-life decay) + tests + lexicon  [relates: member_of]  (source: git:a7d8c10da970)
- Fixes: clean stemroller mis-tag + demote zluda (regression) + recall multi-word OR-match + story errors-that-teach  [relates: member_of]  (source: git:2a1071076a19)
- Back up OpenCode/Cursor work: auto-logger (EventLog on Ledger + bridge/promoter) + event tests + conftest hermeticity  [relates: member_of]  (source: git:b3d9baa78e60)
- Rate-limit consolidation three ways: salience threshold + per-run cap + persistent dedup. And make hooks that emit a Beat stamp the beat id back onto the raw event so...  [relates: member_of]  (source: learn:experiment:Prevent double-promotion by stamping provenance both directions)
- Always dogfood a new slice through the real CLI against canonical-shaped data, not just isolated unit fixtures. Unit tests verify the units; dogfooding verifies the...  [relates: member_of]  (source: learn:experiment:Dogfooding caught an integration gap unit tests missed)
- Do NOT pass an explicit track to emit() when you want a first-class Track; pass a RouteHint(task=...) instead so _route() registers + indexes it. Explicit track is a...  [relates: member_of]  (source: learn:experiment:BeatLog.emit explicit track skips track registration)
- Cleanup stray keys + standardize on pytest (pytest.ini, fix return-not-none) + Perspectives/Maps build plan  [relates: member_of]  (source: git:624b6e7838f4)

## Use bifrost_runner_web.bat for live gemini on bus. AI Mode needs headed (defa... (ai-setup)
Span: 2026-06-28T12:11:26.188260 → 2026-06-28T22:19:23.022712
Beats: 73  · Critic: True

- Use bifrost_runner_web.bat for live gemini on bus. AI Mode needs headed (default). Stack cheat sheet: boot=load context, learn=lessons, log=milestone beats...  [relates: member_of]  (source: learn:experiment:gemini_web_session_arc)
- AI Mode requires headed+stealth (default for ai_mode). Headless still gets gated. Use --probe to diagnose.  (source: learn:experiment:gemini_ai_mode_stealth)
- Default runner to --provider auto (web-first). User runs bifrost_runner_web.bat to keep Gemini live on the bus without API keys.  (source: learn:experiment:gemini_web_short_response_fix)
- A slice isn't done until it's mirrored (scripts/mirror.py commit+push) AND the decision is a lesson (+ snapshot_knowledge for data). Do NOT rely on docs/memory to...  [relates: member_of]  (source: learn:experiment:bifrost_pull_session_hygiene)
- Bifrost runner + Agent Card: Gemini is now a bus citizen (scripts/bifrost_runner.py, api/runner card) -- answered a real question on the bus; presence carries Agent...  (source: git:303dc25dab5e)
- A 'runner' loop (wait->bridge->reply) turns ANY stateless API into a first-class bus citizen with presence + inbox + replies, no MCP. wait(advance=True) for a consumer...  [relates: member_of]  (source: learn:experiment:bifrost_runner_and_card)
- Bifrost B2: durable promoter (salient bus msgs -> firehose as bifrost_msg, queryable + Redis-restart-survivable) + pytest pollution guard; 5 tests, suite 329  (source: git:6394bd4d49f1)
- An auto side-effect inside a transport/primitive (writing to a canonical store) WILL pollute canonical during tests -- guard it (pytest env or an explicit flag) and...  [relates: member_of]  (source: learn:experiment:bifrost_b2_promoter)
- Fix Bifrost wake boundary: build the blocking client via the canonical connector (long timeout_seconds), not a raw redis client; guardrails green, suite 324  (source: git:0a7e331e30c0)
- Fix Bifrost wake: blocking XREAD needs a dedicated long-socket-timeout client (fail-fast client's ~3s timeout aborted the block); regression test blocks past 3s; suite...  [relates: member_of]  (source: git:84576b1342ec)
- A fail-fast Redis client (short socket_timeout) CANNOT do long blocking reads -- XREAD/BLPOP need a separate client whose socket_timeout exceeds the block (or None)...  [relates: member_of]  (source: learn:experiment:bifrost_wake_socket_timeout_fix)
- Bifrost event-driven wake: Bus.wait() blocking primitive + scripts/bifrost_wake.py background watcher -> harness re-invokes the agent on a message (no API key, no OS...  (source: git:3a725d152370)
- For a turn-based agent in a harness that re-invokes on background-task completion, a backgrounded blocking XREAD is the ideal wake: ~0 idle cost, exact wake, re-armable...  (source: learn:experiment:bifrost_event_driven_wake)
- For local multi-agent + a human, a live shared chat console beats OS notifications: the human sees everything + can interject, no sound spam. Use prompt_toolkit...  (source: learn:experiment:bifrost_console_wake)
- Bifrost B3 (doors): presence (register/heartbeat/TTL) + bifrost_send/broadcast/inbox/presence MCP tools on ai_setup_mcp.py (Cursor's existing server, zero new config); 5...  (source: git:04520ec2e496)
- Adding bus tools to the server an agent ALREADY connects to (ai_setup_mcp) beats a new server (zero client config). Presence via auto-touch + TTL = liveness for free...  (source: learn:experiment:bifrost_b3_doors_presence)
- Bifrost B1: Parts + media-by-reference (core/comm/blobs.py content-addressed BlobStore + Part inline|ref wired into the bus); 7 tests, suite 311. Dogfood: shared a doc...  (source: git:3a8c134fb459)
- For local agents the FILESYSTEM is the shared blob store -- no Redis round-trip for media; the bus carries pointers, bytes fetched on demand...  [relates: member_of]  (source: learn:experiment:bifrost_b1_parts_media)
- Bifrost B0: unified bus (core/comm/bus.py) -- one Redis-Streams transport, canonical port, real per-agent fan-out (fixes broken broadcast), explicit offline; 7 tests...  (source: git:c0abe46bfb77)
- Per-agent cursor (XREAD from stored last-id) beats consumer groups for FAN-OUT: groups load-balance (one consumer per message), cursors give every agent every message it...  [relates: member_of]  (source: learn:experiment:bifrost_b0_bus_transport)
- When renaming a system built on an immutable substrate, do NOT rewrite the historical record -- rename the forward-facing identity (README/lexicon/canonical name value)...  (source: learn:experiment:project_renamed_akashic_aurora)
- After user reloads Cursor MCP: call boot(agent, task) first. Use handoff(from_agent, to, task, note) at session end. MCP and CLI share one code path — prefer MCP tools...  (source: learn:experiment:bootstrap_mcp_handoff_session)
- Keep MCP tools as thin wrappers over agent_cli cmd_* via _run() capture so CLI and MCP can never drift. For cross-agent handoff, write a handoff signal (boot already...  (source: learn:experiment:mcp_door_over_agent_cli)
- Codex C2: Resource schema + shared bi-temporal lifecycle (pre-build-reviewed E1-E4: stable id + version_hash, supersession forwards links, valid_to canonical) +...  (source: git:02bcdf63616d)
- Codex C1: Clusterer primitive (embedding clusters + merge/split proposals, salient-outlier-preserving, flag-only); 8 tests, suite 290. Dogfood surfaces the...  (source: git:3b93485afc59)
- Fix faithfulness metric: source pointers containing ')' (greedy capture to line-final paren) -- canonical story faithful=True again; 2 regression tests, suite 282  [relates: member_of]  (source: git:69b748a8dd9a)
- Re-parsing rendered text for a gate is fragile (delimiters collide with content). The robust long-term fix (C4) is to check faithfulness against the Distillation's...  [relates: member_of]  (source: learn:experiment:spine_faithfulness_parens_fix)
- Codex S1: extract shared Consolidator primitive -- chronicler + learning/consolidation onto one rank->distill engine (behavior-identical); 4 tests, suite 280  [relates: member_of]  (source: git:5113746be6b5)
- The real prize isn't DRY -- it's the SINGLE point where Ranker+Distiller (and at C4, the faithfulness critic) are constructed: wire the gate into Consolidator once...  [relates: member_of]  (source: learn:experiment:codex_s1_consolidator)
- Codex C0: Embedder primitive (all-MiniLM-L6-v2, CPU, cached+lazy, keyword fallback) into the Ranker.relevance_fn seam; ablation gate passes (embeddings beat keyword); 6...  (source: git:11a34d0af171)
- Cache-first + lazy-load is the key pattern for the per-command-process model: warm Store cache means most calls never pay the 7.5s model load. ONE embedding seam...  [relates: member_of]  (source: learn:experiment:codex_c0_embedder)
- Codex S5: unify time handling -- collapse 6 _epoch copies into timeutil.to_epoch + re-score migration (canonical: 80/80/35); 5 tests, suite 270  [relates: member_of]  (source: git:132eb23c3630)
- When unifying a helper that computes PERSISTED scores, ship a re-score migration in the same slice or windowed queries silently lose recall at the old/new boundary...  [relates: member_of]  (source: learn:experiment:codex_s5_time_unification)
- Do the 3 unifications FIRST (S5 time fn, S1 Consolidator extract, S4 node-lifecycle) so every later slice is built on one engine/lifecycle/seam -- connections simplify...  [relates: member_of]  (source: learn:experiment:codex_inventory_pressure_test)
- Spine W-c: narrative health counters (route/theme/chronicle) surfaced in status -- silent best-effort failures now observable; 4 tests, suite 265. Wave-1 hardening...  [relates: member_of]  (source: git:f8caedac801e)
- Observability counters must themselves be best-effort (never raise into the path they observe). Keep them in the narrative layer; lower primitives log their own...  [relates: member_of]  (source: learn:experiment:spine_wc_health_counters)
- Spine D4: timezone-safe chronicler comparison (core/foundation/timeutil) -- mixed naive/tz-aware no longer mis-sorts/mis-segments; 6 tests, suite 261  [relates: member_of]  (source: git:ebc4afc3e650)
- For naive timestamps, .timestamp() is locale-dependent -- always normalize naive==UTC before comparing. Fix comparison (recomputed) freely; persisted scores need a...  (source: learn:experiment:spine_d4_timezone_safe)
- Spine D2: word-boundary router/theme matching (fixes substring false positives) + drop ambiguous 'comfy'; confusable corpus, ARI bar held, suite 255  [relates: member_of]  (source: git:0be2aff99984)
- Spine D3: harden tag confidence (drop non-finite, clamp out-of-range) -- defends the CRDT no-degrade guarantee against tampered/corrupt entries; 5 new tests, suite 251  [relates: member_of]  (source: git:35b8c3bb6f54)
- Drop-don't-clamp for non-finite is the right call (clamping inf->1.0 would still let it win); clamp only finite drift. Read-path sanitization protects against...  [relates: member_of]  (source: learn:experiment:spine_d3_confidence_hardening)
- Spine V1: time-indexed EventQuery (fixes D1 silent recall loss) -- Store-backed CQRS read-model, bounded+rebuildable, opt-in; 8 worst-case tests, suite 246  [relates: member_of]  (source: git:b07a0ce97ab1)
- CQRS read-model over an append-only Ledger is the clean pattern: Ledger = system-of-record + rebuild source, Store index = queryable projection. Opt-in-by-store kept...  [relates: member_of]  (source: learn:experiment:spine_v1_event_time_index)
- Wave 1 hardening V1-V5 (time-index events, word-boundary matching, clamp confidence finite[0,1], normalize tz at boundary, health counters) FIRST; Wave 2 V6-V9...  [relates: member_of]  (source: learn:experiment:spine_v2_reevaluation)
- scorer seam IS the Cleanlab/confident-learning hook for Slice-6 embeddings -- plug an embedding/LLM scorer there. Backfill tag_history on pre-G1 beats to cut...  [relates: member_of]  (source: learn:experiment:tag_governance_g2_detection)
- Tag Governance G2: confident-learning mis-tag detection (flag-only, I6 read-only) + scorer seam for Slice-6 embeddings; worst-case tests (238 pass)  [relates: member_of]  (source: git:4066eff6345f)
- Tag Governance G1: confidence-gated append-only re-tag (a CRDT) + Store.zrem + BeatLog tag-history seed; worst-case invariant tests (233 pass)  [relates: member_of]  (source: git:0ee32b23a2fc)
- Tag stores should be CRDTs (MV-register + survivorship resolver) for self-cleanup without data loss. Sources: Shapiro CRDTs, MDM survivorship/golden-record...  [relates: member_of]  (source: learn:experiment:tag_governance_g1_crdt)
- Tag Governance G0: tag-history + confidence schema (TagEntry/TagHistory, basis->confidence, append-only + rollback) + Beat.tag_history + worst-case tests  [relates: member_of]  (source: git:f2cd9cf3fe32)
- claude -> claude: Resume Akashic Aurora: Codex parked at C4 (faithfulness critic) + Bifrost agent-comms (Cursor building its pull-side). Pick a track; keep tokens low...  (source: event:events:raw:1782683527939-0)
- AGENTS.md: Session-hygiene doctrine (pull-side token reduction) -- commit+mirror the contract Cursor left uncommitted; lesson bifrost_pull_session_hygiene logged  [relates: member_of]  (source: git:e0b8d236adb2)
- Bifrost Console: live chat TUI onto the bus (scripts/bifrost_console.py) -- watch agents talk + interject, no OS toasts/sounds; prompt_toolkit+rich, color-coded...  [relates: member_of]  (source: git:14f3feaaa374)
- Bifrost plan: agent comm/handoff layer -- review of 4 fragmented layers + A2A-model SOTA synthesis + Gemini pre-review (F1-F4: bus!=ledger, media-by-ref safety, simple...  (source: git:d8dce4332028)
- Akashic Aurora naming consistency: Redis Sentinel master breakthrough->akasha (3 confs + client, lockstep; no live sentinel), docker-compose/net/launchers/templates...  (source: git:78b10355d4de)
- Finish Akashic Aurora rename: MCP server name + configs (files renamed), stack_manager, services/port_manager, bootstrap scripts, project_context method. Left: Redis...  (source: git:2b5e4ed28e2f)
- Rename project to Akashic Aurora: README + LEXICON + project_context name + config; GitHub repo renamed ai-setup->akashic-aurora. (MCP server name left for Cursor...  (source: git:2a2884c4b0ec)
- Codex pressure-test: inventory + slice placement + 8 simplifications (one Consolidator, one embedding seam, unify supersession, collapse _epoch) ->...  [relates: member_of]  (source: git:e26fa6f98b42)
- Codex plan (Wave 2): self-curating knowledge layer over immutable atoms -- MDL-under-faithfulness objective, prior-art-grounded, sliced C0-C7. docs/codex-plan.md  (source: git:b18c8233d700)
- Spine v2 plan: mark Wave-1 hardening complete (D1-D4 + W-c)  [relates: member_of]  (source: git:0e8a02b0851b)
- Spine v2 re-evaluation: adversarial audit of every slice (4 confirmed defects + prior-art-backed v2 plan) -> docs/spine-v2-plan.md + tests/spine_probes.py  [relates: member_of]  (source: git:25803d5f4245)
- claude -> claude: guardrail smoke test  [relates: member_of]  (source: handoff:claude->claude)
- claude -> cursor: Follow the per-slice continuity protocol: commit+mirror AND record a lesson  [relates: member_of]  (source: handoff:claude->cursor)
- Session started  (source: session:start)
- Session ended  (source: session:end)
- cursor -> cursor: Continue Akashic Aurora: Bifrost pull-side done; Gemini web scaffold shelved; align with Claude on Agent Card + runner  (source: handoff:cursor->cursor)
- claude -> claude: Resume Akashic Aurora: Codex parked at C4 (faithfulness critic) + Bifrost agent-comms (Cursor building its pull-side). Pick a track; keep tokens low...  (source: handoff:claude->claude)
- Session ended  (source: session:end)
- Session started  (source: session:start)
- cursor -> claude: Realtime comm test ping from Cursor  [relates: member_of]  (source: handoff:cursor->claude)
- Session started  (source: session:start)
- Bootstrap/MCP session complete: rebuilt ai_setup_mcp.py, added handoff verb, fixed config+rule drift, user reloading Cursor MCP  (source: cursor:bootstrap_mcp_session)
- cursor -> claude: MCP server rebuilt and handoff verb live — verify after user reloads Cursor  (source: handoff:cursor->claude)
- cursor -> claude: Finish MCP integration testing + C3 threshold tuning  (source: handoff:cursor->claude)

## Word-boundary fixes substring-in-word, but genuinely-ambiguous standalone wor... (vision)
Span: 2026-06-28T15:19:03.234169 → 2026-06-28T15:19:03.234169
Beats: 1  · Critic: True

- Word-boundary fixes substring-in-word, but genuinely-ambiguous standalone words (comfy=cozy vs ComfyUI) need keyword hygiene too -- require the unambiguous product form...  [relates: member_of]  (source: learn:experiment:spine_d2_word_boundary_matching)

## Adopt A2A data MODEL not its enterprise HTTP transport (local-first). The bus... (research)
Span: 2026-06-28T18:09:39.135268 → 2026-06-28T20:31:10.340476
Beats: 4  · Critic: True

- Adopt A2A data MODEL not its enterprise HTTP transport (local-first). The bus is ephemeral (Redis Streams, per-agent inbox fan-out); the durable record is a Ledger...  (source: learn:experiment:bifrost_plan_agent_comm)
- PRE-build review beats post-build: Gemini caught the membership-derived-id trap before any code -- stable-entity-id + version-hash + supersession-forwards-links is the...  (source: learn:experiment:codex_c2_resource_lifecycle)
- Dogfood made Gemini's tension VISIBLE + bidirectional: salient_importance=4 with weight-4-learning-heavy data -> over-preservation (54 singletons, ~no curation); the one...  (source: learn:experiment:codex_c1_clusterer)
- Start C0 (embedding substrate) with research-to-do: benchmark EmbeddingGemma-300M vs E5-small vs bge-small on a local fixture, then Embedder primitive + cache +...  [relates: member_of]  (source: learn:experiment:codex_plan_wave2)

## Gemini web stealth: AI Mode gate bypassed with headed real Chrome + playwrigh... (ai-setup)
Span: 2026-06-28T22:19:23.342233 → 2026-06-28T22:19:23.342233
Beats: 1  · Critic: True

- Gemini web stealth: AI Mode gate bypassed with headed real Chrome + playwright-stealth (was bot detection, not account lock)  (source: learn:experiment:gemini_ai_mode_stealth)

## Bifrost web runner live: gemini answers bus via free gemini.google.com (bifro... (ai-setup)
Span: 2026-06-28T22:19:23.626667 → 2026-06-28T22:19:26.392297
Beats: 3  · Critic: True

- Bifrost web runner live: gemini answers bus via free gemini.google.com (bifrost_runner --provider web)  (source: learn:experiment:gemini_web_short_response_fix)
- AI Mode defaults headed+stealth; gemini chat can stay headless; isolated profile .secrets/gemini_web_profile  (source: cursor:gemini-web-policy)
- cursor -> cursor: Gemini web + Bifrost slice complete; optional: tune runner system prompt, bifrost_runner --web-mode ai_mode dogfood  (source: handoff:cursor->cursor)

## Gemini web stealth + free models on the Bifrost bus (ai-setup)
Span: 2026-06-28T22:19:26.728603 → 2026-06-29T08:21:11.155622
Beats: 22  · Critic: True

- Gemini web stealth + free models on the Bifrost bus  (source: mark:2026-06-28T22:19:26.728603)
- Execute the up-close wiring (the gold), in order: (1) LEXICON entries + confirm AGENT_ID per agent, (2) discover verb from argparse subparsers + check_boundaries rule...  (source: learn:experiment:agent_experience_plan)
- FC-01 next: build core/codex/curate.py, gated by faithfulness_critic. Defer NER entity-consistency + sentence/dependency entailment (SummaC/DAE/AlignScore-355M) until an...  (source: learn:experiment:faith1_faithfulness_critic)
- Next executable: FAITH-1 = lift chronicler._compute_metrics into core/primitives/faithfulness.py, CHARACTERIZE its false-positive rate on the real corpus, wire via...  (source: learn:experiment:intelligence_roadmap_and_spine1)
- The agnostic 'zero custom code' is true for send/read (MCP/Redis) but NOT for wake -- every runtime needs a small turn-starter; pull-floor is the honest default, push is...  (source: learn:experiment:bifrost_mesh_comm)
- P0 = set AKASHIC_AGENT_ID at the door + make hooks fail-closed-with-teaching. Then: route contended writes through Store.update_atomic (CAS has 0 callers); kill the dead...  (source: learn:experiment:architecture_review_2026_06_28)
- When an ablation gate exists, MEASURE before committing a shape -- the obvious approach (embeddings replace keywords) lost; hybrid won. Short exemplar phrases beat one...  (source: learn:experiment:spine_v6_theme_discovery)
- Git hooks abort on ANY non-zero exit -- use exit 1 (the exit-2 rule is Claude-PreToolUse-only). core.hooksPath is shared config; relative path resolves per worktree...  (source: learn:experiment:concurrency_c4_and_worktrees_live)
- Read-without-reread: the structural fix is to wake into a FRESH minimal session (boot + cursor), not resume the transcript; --digest is the cheap mid-session scan. On...  (source: learn:experiment:concurrency_c3_store_cas)
- Advisory locks suit peers we own; the fencing token (monotonic, validated at the commit gate) is the one must-have safety property. Keep it fail-soft: offline => no...  (source: learn:experiment:concurrency_c2_path_locks)
- Restart Cursor MCP server to pick up ai_setup_mcp.py changes; avoid concurrent gemini_web profile users (bifrost_runner + MCP subprocess)  (source: learn:experiment:gemini_mcp_invisible_env)
- Use ask_gemini_web(mode=ai_mode|both) on user-akashic-aurora; invisible mode default  (source: learn:experiment:mcp_gemini_web_ai_mode)
- Daily model: agents live in worktrees, master is the integration point; integrate only from master, sync rebases on origin/master. Combine with C0 (mirror with explicit...  (source: learn:experiment:concurrency_c1_worktrees)
- When committing in a shared tree, never trust the index: git add <your paths> then git commit -- <your paths> (only-mode), or mirror.py with explicit paths. Claude...  (source: learn:experiment:concurrency_c0_git_guard)
- True headless cannot pass Google AI Mode gate on this account; use invisible mode. --engine patchright optional for invisible.  (source: learn:experiment:patchright_headless_google)
- Principle: share the immutable substrate, isolate the mutable workspace, enforce at the door not in memory. Build C0 first (de-blanket mirror.py + hooks) -- highest...  (source: learn:experiment:concurrent_agents_design)
- Default invisible. --headed for debug/login only. Don't run CLI gemini_web while bifrost_runner holds profile.  (source: learn:experiment:gemini_web_invisible_mode)
- claude -> cursor: Set AKASHIC_AGENT_ID=cursor on your side (review P0)  (source: handoff:claude->cursor)
- cursor -> claude: PAUSE worktree-per-agent experiment — back to single tree  (source: handoff:cursor->claude)
- cursor -> claude: Review singleton-tool contention plan (R0 bus-routing + R1 file lock + C2 resource locks)  (source: handoff:cursor->claude)
- claude -> cursor: master history was rewritten -- fetch + reset to avoid divergence  (source: handoff:claude->cursor)
- claude -> cursor: Wire the C0 git-guard hook on Cursor's side (beforeShellExecution)  (source: handoff:claude->cursor)

## Differentiator confirmed by research: action-trigger + deterministic ranking ... (research)
Span: 2026-06-29T08:34:55.284291 → 2026-06-29T08:34:55.284291
Beats: 1  · Critic: True

- Differentiator confirmed by research: action-trigger + deterministic ranking is ahead of SOTA (mem0/Zep/claude-mem all inject at turn-start). NEXT refinements: (1)...  (source: learn:experiment:recall_at_action_v1)

## Honest caveat: PostToolUse success/FAIL detection depends on the tool_respons... (ai-setup)
Span: 2026-06-29T12:29:40.152518 → 2026-06-29T13:54:50.676433
Beats: 9  · Critic: True

- Honest caveat: PostToolUse success/FAIL detection depends on the tool_response payload shape (assumed is_error/error/exit_code); if it differs, the signal stays INERT...  (source: learn:experiment:door_discover_and_implicit_useful)
- When adding a root doc, update check_doc_freshness ALLOWLIST. Guard every test that imports an optional-dep module (numpy/mcp/torch/sentence_transformers/fastapi) with...  (source: learn:experiment:ci_and_deploy_hardening)
- claude -> cursor: Add MCP parity for recall-feedback (and recall-at)  (source: handoff:claude->cursor)
- Deploy facts for future agents: core = stdlib-only (no required deps); Redis optional (16379); the deploy guide is docs/DEPLOY.md; license is Apache-2.0. Non-Windows...  (source: learn:experiment:deploy_kit_public)
- The loop's POSITIVE signal (boost) needs votes -- works only if the agent/user actually marks useful (AGENTS.md now instructs it); the NEGATIVE signal (noise-decay) is...  (source: learn:experiment:recall_at_action_usefulness)
- recall-at-action is now COMPLETE end-to-end: engine -> CLI -> project hook -> bootstrap contract -> guarded global hook -> anti-repeat -> warm cache -> SessionStart...  (source: learn:experiment:recall_at_action_polish)
- Remaining recall polish (optional): (1) a SessionStart hook to pre-warm the cache so even the first edit is instant; (2) best-effort prune of old per-session seen files...  (source: learn:experiment:recall_at_action_ergonomics)
- NEXT ergonomics, in order: (1) anti-repeat within a session (persist shown lesson-ids in a session temp file keyed by session id) -- biggest remaining noise source on...  (source: learn:experiment:recall_at_action_global_hook)
- Two doors for recall-at-action: (1) PreToolUse hook = automatic but ONLY when Claude is launched FROM the repo (cwd=E:/AI-Setup); (2) AGENTS.md contract = agent runs...  (source: learn:experiment:recall_at_action_bootstrap_flow)

## next-focus: TOMORROW: run the epistemic-risk ULTRACODE workflow -- 'how do re... (ai-setup)
Span: 2026-06-29T23:30:04.725893 → 2026-06-30T04:19:22.691110
Beats: 23  · Critic: True

- next-focus: TOMORROW: run the epistemic-risk ULTRACODE workflow -- 'how do recall-at-action + the usefulness feedback loop + write-once notes + ambient capture DEGRADE...  (source: mem:decision:ADR_0630001922_5755)
- never put trailing comments on .gitignore pattern lines; only lines STARTING with # are comments -- put the comment on its own line above the pattern  (source: learn:experiment:gitignore_no_inline_comments)
- fix: .gitignore inline comment broke draft-ignore; track memory.md digest  (source: git:da87164d76a2)
- ALWAYS add matcher '*' (or a specific value) to SessionStart/SessionEnd/PreCompact entries -- without it they may not register. Keep these hooks SILENT on stdout...  (source: learn:experiment:session_hooks_need_matcher)
- Ambient capture = continuity INSURANCE for abrupt ends (esp. PreCompact = compaction, the main where-we-are-loss moment); redundant when you wrap manually. It DRAFTS to...  (source: learn:experiment:wrap_autocapture_shipped)
- Ship every slice with: py scripts/ship.py MSG paths --learn-exp NAME --tried .. --result .. --recommend .. -- it gates (boundaries+doc-freshness+full pytest) BEFORE...  (source: learn:experiment:ship_and_wrap_shipped)
- Resume each session from boot + notes --json, NOT a hand-edited wall. Trade-offs observed: RECENT NOTES truncates to ~110 chars (drill full bodies via notes --json) --...  (source: learn:experiment:native_checkpoint_migrated_to_notes)
- cursor-status: Cursor's gemini-web slice was taken over + committed by claude (gemini_web.py, bifrost_runner --provider web, ai_setup_mcp _run_gemini_web...  (source: mem:decision:ADR_0629214304_3549)
- open-docket: Explored-not-built: mutual agent invocation (claude -p / cursor-agent headless + generalized bifrost_runner + optional ask_agent RPC; blocked on CLIs not...  (source: mem:decision:ADR_0629214303_8701)
- remaining-review-items: From the 2026-06-28 architecture review: RC-02 route contended writes through Store.update_atomic (CAS has no domain callers); store-hardening...  (source: mem:decision:ADR_0629214302_4317)
- next-focus: NEXT options: (1) FC-01 = build core/codex/curate.py (cluster atoms via Clusterer -> mint/regenerate/supersede Resources) gated by faithfulness_critic -- the...  (source: mem:decision:ADR_0629214302_5390)
- where-we-are 2026-06-29: Akashic Aurora status: recall-at-action COMPLETE end-to-end (engine, CLI recall-at, PreToolUse hook additionalContext, bootstrap contract...  (source: mem:decision:ADR_0629214301_5916)
- Write durable 'where-we-are'/decision state with  (one write), not by hand-editing the native checkpoint -- it surfaces at boot + in chronicles/memory.md. Correct by...  (source: learn:experiment:write_once_notes_shipped)
- open-question: implicit-useful payload: PostToolUse _is_success assumes tool_response shape; verify against a live payload so the FAIL->SUCCESS signal actually fires.  (source: mem:decision:ADR_0629210203_6519)
- where-we-are 2026-06-29: Recall-at-action COMPLETE; repo PUBLIC; write-once notes SHIPPED (note/notes/boot-surface/memory.md). Next: recall-learning loop or FC-01...  (source: mem:decision:ADR_0629210203_1187)
- where-we-are 2026-06-29: Recall-at-action COMPLETE; repo PUBLIC (Apache-2.0, CI green); contributor=balanced7.  (source: mem:decision:ADR_0629210202_2063)
- CRITICAL: the rewrite CHANGED EVERY COMMIT SHA. Any SHA recorded in lessons/memory/docs BEFORE this (e.g. FAITH-1 6b81e9f, SPINE-1 aaa01cc, recall-at 31a1b67, deploy...  (source: learn:experiment:git_history_rewritten_balanced7)
- Don't reintroduce per-agent file/task ownership in docs/memory/handoffs. Coordinate concurrent edits with locks (transient), attribute with AKASHIC_AGENT_ID, but never...  (source: learn:experiment:collaboration_model_no_ownership)
- Taking over a peer agent's stranded slice: review (parses? stubs? referenced files exist?), confirm tests pass, confirm CI-safety (heavy deps lazy + in a separate...  (source: learn:experiment:cursor_slice_taken_over)
- claude -> cursor: Your gemini-web slice is COMMITTED + MCP parity DONE — verify live + set your agent id  (source: handoff:claude->cursor)
- hooks: add required matcher to SessionStart/SessionEnd/PreCompact (verified via docs)  (source: git:7c9df00a1ab0)
- wrap auto-capture: PreCompact/SessionEnd -> draft file + boot pointer  (source: git:3bde06f1aed4)
- ship + wrap: one-command gated ship + ambient session capture  (source: git:28c3afdaf0ec)

## retrieval-critic-design: Design research for an automatic retrieval critic = ... (ai-setup)
Span: 2026-06-30T12:58:21.865926 → 2026-06-30T13:30:36.287830
Beats: 5  · Critic: True

- retrieval-critic-design: Design research for an automatic retrieval critic = docs/retrieval-critic-design.md (2026-06-30, user idea: ground context retrieval so it is...  (source: mem:decision:ADR_0630093036_6716)
- directive-friction-audit: Friction audit of the agent directives = docs/directive-friction-audit.md (written 2026-06-30, in response to user principle: make the right...  (source: mem:decision:ADR_0630092509_1059)
- epistemic-risk-register: EPISTEMIC-RISK REGISTER (manual deep pass; grounded in real code + literature; skeptic-checked). Loop under study: usefulness -> rank -> surface...  (source: mem:decision:ADR_0630091418_4717)
- epistemic-risk-register: Accumulating per-factor risk register for the recall/memory loop (manual deep pass; grounded in real code + literature; skeptic-checked for...  (source: mem:decision:ADR_0630085845_9543)
- next-focus: Epistemic-risk work is now MANUAL factor-by-factor in max-effort, NOT the ultracode workflow (user found ultracode missed the salient self-suggestion risks...  (source: mem:decision:ADR_0630085821_5236)

## session 2026-06-30: F1 provenance-labelled recall (opinion-laundering fix) + ... (ai-setup)
Span: 2026-06-30T23:33:38.652259 → 2026-06-30T23:34:18.331526
Beats: 3  · Critic: True

- session 2026-06-30: F1 provenance-labelled recall (opinion-laundering fix) + directive-friction-audit & retrieval-critic design docs; ranking slice paused  (source: git:b7ac45b67168)
- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-06-30, before a Claude update). SHORT: Factor 1 opinion-laundering SHIPPED...  (source: mem:decision:ADR_0630193400_4519)
- where-we-are: SESSION 2026-06-30 (paused for a Claude update). ARC: deep MANUAL max-effort epistemic-risk pass (NOT ultracode -- it missed the salient self-suggestion...  (source: mem:decision:ADR_0630193338_5557)

## next-focus: Full current state + resume options = note where-we-are (refreshe... (ai-setup)
Span: 2026-07-01T04:11:47.846790 → 2026-07-01T05:01:22.414000
Beats: 5  · Critic: True

- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-07-01). SHORT: ranking-feedback INC1 pull slice SHIPPED (recall --full, total, N-of-M...  (source: mem:decision:ADR_0701010122_3781)
- adversarial-critic-partner-idea: User idea (2026-07-01): design an adversarial partner/critic for Claude that TRAINS INDEPENDENTLY (not just prompted-in-context) and...  (source: mem:decision:ADR_0701010114_6136)
- where-we-are: SESSION 2026-06-30/07-01. Reviewed + approved both design docs (directive-friction-audit, retrieval-critic-design) -- no changes requested, both ready to...  (source: mem:decision:ADR_0701001207_4003)
- next: the friction-audit roadmap's remaining quick-wins (auto-boot at SessionStart, turn-start bus-sync hook, identity fail-closed) or the retrieval-critic Tier 1...  (source: learn:experiment:ranking_feedback_inc1_pull)
- ranking & feedback INC1: pull-side escape (recall --full, recall_at total, render N-of-M line)  (source: git:19f0b918b0ce)

## next-focus: NEXT per docs/leapfrog-plan.md triage (loop fires -> corpus grows... (ai-setup)
Span: 2026-07-01T23:20:43.667129 → 2026-07-02T02:52:25.856601
Beats: 20  · Critic: True

- Recall dissent (Slices 0-1): eval harness + precision-first counter-finder  (source: git:bbb93b38bb1b)
- Precision-first + silent-when-starved is correct: the binding constraint is corpus content, not the reader. Next lever = Slice 2 (write-side capture of anti_patterns /...  (source: learn:experiment:recall_dissent_slice01)
- Build the yardstick + a real-corpus probe before the mechanism; trust the curated fixture and treat any detector-relative corpus metric as suspect until a precise...  (source: learn:experiment:eval_harness_before_fix)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md (Path 2 dialectical retrieval...  (source: mem:decision:ADR_0701192312_2889)
- next-focus: NEXT = Slice 2 of the recall-critic arc = write-side dissent capture. VERIFIED gap: agent_cli.py learn exposes only ...[truncated]  (source: mem:decision:ADR_0701192315_6475)
- Recall dissent (Slice 2): write-side capture -- expose, tag, auto-draft anti-patterns  (source: git:f799c8946194)
- A write door must OFFER a field or it stays empty (0 anti-patterns came from a missing flag, not agent laziness). Auto-draft the NAME to remove the naming cost and hand...  (source: learn:experiment:recall_dissent_slice2_capture)
- when adding a capability to a lower layer, expose it on the SAME door agents already use, in the same slice, or it stays dead; treat door-exposure as part of done  (source: learn:experiment:capability_without_a_door)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md. SHIPPED + pushed, all gated...  (source: mem:decision:ADR_0701194515_9161)
- next-focus: TOP PRIORITY (reprioritized by a dogfooding finding): fix Slice-1 PRECISION on real anti-patterns. The finder surfaces 7 false counters on the live corpus...  (source: mem:decision:ADR_0701194521_1667)
- Recall dissent (Slice 3): precision fix -- an on-topic anti-pattern is not a contradiction  (source: git:380b4dc3a399)
- An on-topic anti-pattern != a contradiction of a thesis; topic-adjacency conflates with stance. Precision-first: surface nothing you cannot verify. NEXT...  (source: learn:experiment:recall_dissent_slice3_precision)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md. SHIPPED + pushed (gated green)...  (source: mem:decision:ADR_0701201344_4961)
- next-focus: NEXT = build the SEMANTIC GATE (the deferred tier), now that its yardstick exists (tests/test_semantic_eval.py) and an LLM-judge probe cleared it -- incl...  (source: mem:decision:ADR_0701201350_1440)
- T1: make the implicit FAIL->SUCCESS credit real: transcript-synthesized failures + live payload contract  (source: git:0d77da61ecbc)
- Never trust an assumed hook payload shape: auto-capture real payloads (bounded, tempdir/akashic_recall/payloads), pin them as fixtures in a contract test...  (source: learn:experiment:recall_implicit_credit_payload_truth)
- open-question: implicit-useful payload: RESOLVED 2026-07-01 (T1 shipped, gated green). Live capture proved the old assumption unfixable rather than mistuned: Claude Code...  (source: mem:decision:ADR_0701223906_5443)
- where-we-are: T1 (leapfrog plan Wave A) SHIPPED 2026-07-01: the implicit FAIL->SUCCESS credit loop is REAL end-to-end -- proven live in-session, first helped credit ever...  (source: mem:decision:ADR_0701223906_9239)
- next-focus: NEXT per docs/leapfrog-plan.md triage (loop fires -> corpus grows -> numbers exist): T2 = write-side friction fixes (JIT learn-it? prompt at the...  (source: mem:decision:ADR_0701223907_7327)
- Session ended  (source: session:end)

## leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synt... (research)
Span: 2026-07-02T01:54:07.427964 → 2026-07-02T02:10:02.912138
Beats: 2  · Critic: True

- competitive-landscape-2026-07: Web survey 2026-07-01 (full sources in session transcript). FIELD STATE: memory is now native in every harness -- Claude Code auto-memory...  (source: mem:decision:ADR_0701215407_2479)
- leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synthesis of repo audit + docs read + competitive survey + DS4/antirez case study). THESIS...  (source: mem:decision:ADR_0701221002_3682)
