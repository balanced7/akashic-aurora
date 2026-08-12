# Story — generated 2026-08-01T14:26:21.957246+00:00

Version: 0

## Atlas
- **ai-setup**: 200 chapter(s)
- **research**: 31 chapter(s)
- **unknown**: 2 chapter(s)
- **vision**: 2 chapter(s)
- **voice**: 3 chapter(s)

Summary: ai-setup: 200 chapter(s); research: 31 chapter(s); unknown: 2 chapter(s); vision: 2 chapter(s); voice: 3 chapter(s)

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

## a beat with raw beneath it (ai-setup)
Span: 2026-06-15T12:00:00 → 2026-06-15T12:00:00
Beats: 1  · Critic: True

- a beat with raw beneath it  (source: event:events:raw:1785010305590-0)

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
- Bifrost runner + Agent Card: Gemini is now a bus citizen (scripts/bifrost_runner.py, api/runner card) -- answered a real question on the bus; presence carries Agent...  (source: git:8f723d45d9c6)
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
- AGENTS.md: Session-hygiene doctrine (pull-side token reduction) -- commit+mirror the contract Cursor left uncommitted; lesson bifrost_pull_session_hygiene logged  [relates: member_of]  (source: git:ef9544927ebf)
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
- Execute the up-close wiring (the gold), in order: (1) LEXICON entries + confirm AGENT_ID per agent, (2) discover verb from argparse subparsers + check_boundaries rule...  [relates: member_of]  (source: learn:experiment:agent_experience_plan)
- FC-01 next: build core/codex/curate.py, gated by faithfulness_critic. Defer NER entity-consistency + sentence/dependency entailment (SummaC/DAE/AlignScore-355M) until an...  (source: learn:experiment:faith1_faithfulness_critic)
- Next executable: FAITH-1 = lift chronicler._compute_metrics into core/primitives/faithfulness.py, CHARACTERIZE its false-positive rate on the real corpus, wire via...  [relates: member_of]  (source: learn:experiment:intelligence_roadmap_and_spine1)
- The agnostic 'zero custom code' is true for send/read (MCP/Redis) but NOT for wake -- every runtime needs a small turn-starter; pull-floor is the honest default, push is...  (source: learn:experiment:bifrost_mesh_comm)
- P0 = set AKASHIC_AGENT_ID at the door + make hooks fail-closed-with-teaching. Then: route contended writes through Store.update_atomic (CAS has 0 callers); kill the dead...  [relates: member_of]  (source: learn:experiment:architecture_review_2026_06_28)
- When an ablation gate exists, MEASURE before committing a shape -- the obvious approach (embeddings replace keywords) lost; hybrid won. Short exemplar phrases beat one...  [relates: member_of]  (source: learn:experiment:spine_v6_theme_discovery)
- Git hooks abort on ANY non-zero exit -- use exit 1 (the exit-2 rule is Claude-PreToolUse-only). core.hooksPath is shared config; relative path resolves per worktree...  (source: learn:experiment:concurrency_c4_and_worktrees_live)
- Read-without-reread: the structural fix is to wake into a FRESH minimal session (boot + cursor), not resume the transcript; --digest is the cheap mid-session scan. On...  [relates: member_of]  (source: learn:experiment:concurrency_c3_store_cas)
- Advisory locks suit peers we own; the fencing token (monotonic, validated at the commit gate) is the one must-have safety property. Keep it fail-soft: offline => no...  [relates: member_of]  (source: learn:experiment:concurrency_c2_path_locks)
- Restart Cursor MCP server to pick up ai_setup_mcp.py changes; avoid concurrent gemini_web profile users (bifrost_runner + MCP subprocess)  (source: learn:experiment:gemini_mcp_invisible_env)
- Use ask_gemini_web(mode=ai_mode|both) on user-akashic-aurora; invisible mode default  (source: learn:experiment:mcp_gemini_web_ai_mode)
- Daily model: agents live in worktrees, master is the integration point; integrate only from master, sync rebases on origin/master. Combine with C0 (mirror with explicit...  [relates: member_of]  (source: learn:experiment:concurrency_c1_worktrees)
- When committing in a shared tree, never trust the index: git add <your paths> then git commit -- <your paths> (only-mode), or mirror.py with explicit paths. Claude...  [relates: member_of]  (source: learn:experiment:concurrency_c0_git_guard)
- True headless cannot pass Google AI Mode gate on this account; use invisible mode. --engine patchright optional for invisible.  (source: learn:experiment:patchright_headless_google)
- Principle: share the immutable substrate, isolate the mutable workspace, enforce at the door not in memory. Build C0 first (de-blanket mirror.py + hooks) -- highest...  [relates: member_of]  (source: learn:experiment:concurrent_agents_design)
- Default invisible. --headed for debug/login only. Don't run CLI gemini_web while bifrost_runner holds profile.  (source: learn:experiment:gemini_web_invisible_mode)
- claude -> cursor: Set AKASHIC_AGENT_ID=cursor on your side (review P0)  (source: handoff:claude->cursor)
- cursor -> claude: PAUSE worktree-per-agent experiment — back to single tree  (source: handoff:cursor->claude)
- cursor -> claude: Review singleton-tool contention plan (R0 bus-routing + R1 file lock + C2 resource locks)  [relates: member_of]  (source: handoff:cursor->claude)
- claude -> cursor: master history was rewritten -- fetch + reset to avoid divergence  (source: handoff:claude->cursor)
- claude -> cursor: Wire the C0 git-guard hook on Cursor's side (beforeShellExecution)  [relates: member_of]  (source: handoff:claude->cursor)

## Differentiator confirmed by research: action-trigger + deterministic ranking ... (research)
Span: 2026-06-29T08:34:55.284291 → 2026-06-29T08:34:55.284291
Beats: 1  · Critic: True

- Differentiator confirmed by research: action-trigger + deterministic ranking is ahead of SOTA (mem0/Zep/claude-mem all inject at turn-start). NEXT refinements: (1)...  [relates: member_of]  (source: learn:experiment:recall_at_action_v1)

## Honest caveat: PostToolUse success/FAIL detection depends on the tool_respons... (ai-setup)
Span: 2026-06-29T12:29:40.152518 → 2026-06-29T13:54:50.676433
Beats: 9  · Critic: True

- Honest caveat: PostToolUse success/FAIL detection depends on the tool_response payload shape (assumed is_error/error/exit_code); if it differs, the signal stays INERT...  [relates: member_of]  (source: learn:experiment:door_discover_and_implicit_useful)
- When adding a root doc, update check_doc_freshness ALLOWLIST. Guard every test that imports an optional-dep module (numpy/mcp/torch/sentence_transformers/fastapi) with...  [relates: member_of]  (source: learn:experiment:ci_and_deploy_hardening)
- claude -> cursor: Add MCP parity for recall-feedback (and recall-at)  [relates: member_of]  (source: handoff:claude->cursor)
- Deploy facts for future agents: core = stdlib-only (no required deps); Redis optional (16379); the deploy guide is docs/DEPLOY.md; license is Apache-2.0. Non-Windows...  [relates: member_of]  (source: learn:experiment:deploy_kit_public)
- The loop's POSITIVE signal (boost) needs votes -- works only if the agent/user actually marks useful (AGENTS.md now instructs it); the NEGATIVE signal (noise-decay) is...  [relates: member_of]  (source: learn:experiment:recall_at_action_usefulness)
- recall-at-action is now COMPLETE end-to-end: engine -> CLI -> project hook -> bootstrap contract -> guarded global hook -> anti-repeat -> warm cache -> SessionStart...  [relates: member_of]  (source: learn:experiment:recall_at_action_polish)
- Remaining recall polish (optional): (1) a SessionStart hook to pre-warm the cache so even the first edit is instant; (2) best-effort prune of old per-session seen files...  [relates: member_of]  (source: learn:experiment:recall_at_action_ergonomics)
- NEXT ergonomics, in order: (1) anti-repeat within a session (persist shown lesson-ids in a session temp file keyed by session id) -- biggest remaining noise source on...  [relates: member_of]  (source: learn:experiment:recall_at_action_global_hook)
- Two doors for recall-at-action: (1) PreToolUse hook = automatic but ONLY when Claude is launched FROM the repo (cwd=E:/AI-Setup); (2) AGENTS.md contract = agent runs...  [relates: member_of]  (source: learn:experiment:recall_at_action_bootstrap_flow)

## next-focus: TOMORROW: run the epistemic-risk ULTRACODE workflow -- 'how do re... (ai-setup)
Span: 2026-06-29T23:30:04.725893 → 2026-06-30T04:19:22.691110
Beats: 23  · Critic: True

- next-focus: TOMORROW: run the epistemic-risk ULTRACODE workflow -- 'how do recall-at-action + the usefulness feedback loop + write-once notes + ambient capture DEGRADE...  [relates: member_of]  (source: mem:decision:ADR_0630001922_5755)
- never put trailing comments on .gitignore pattern lines; only lines STARTING with # are comments -- put the comment on its own line above the pattern  (source: learn:experiment:gitignore_no_inline_comments)
- fix: .gitignore inline comment broke draft-ignore; track memory.md digest  [relates: member_of]  (source: git:09d223a2f3ed)
- ALWAYS add matcher '*' (or a specific value) to SessionStart/SessionEnd/PreCompact entries -- without it they may not register. Keep these hooks SILENT on stdout...  (source: learn:experiment:session_hooks_need_matcher)
- Ambient capture = continuity INSURANCE for abrupt ends (esp. PreCompact = compaction, the main where-we-are-loss moment); redundant when you wrap manually. It DRAFTS to...  [relates: member_of]  (source: learn:experiment:wrap_autocapture_shipped)
- Ship every slice with: py scripts/ship.py MSG paths --learn-exp NAME --tried .. --result .. --recommend .. -- it gates (boundaries+doc-freshness+full pytest) BEFORE...  [relates: member_of]  (source: learn:experiment:ship_and_wrap_shipped)
- Resume each session from boot + notes --json, NOT a hand-edited wall. Trade-offs observed: RECENT NOTES truncates to ~110 chars (drill full bodies via notes --json) --...  (source: learn:experiment:native_checkpoint_migrated_to_notes)
- cursor-status: Cursor's gemini-web slice was taken over + committed by claude (gemini_web.py, bifrost_runner --provider web, ai_setup_mcp _run_gemini_web...  (source: mem:decision:ADR_0629214304_3549)
- open-docket: Explored-not-built: mutual agent invocation (claude -p / cursor-agent headless + generalized bifrost_runner + optional ask_agent RPC; blocked on CLIs not...  (source: mem:decision:ADR_0629214303_8701)
- remaining-review-items: From the 2026-06-28 architecture review: RC-02 route contended writes through Store.update_atomic (CAS has no domain callers); store-hardening...  [relates: member_of]  (source: mem:decision:ADR_0629214302_4317)
- next-focus: NEXT options: (1) FC-01 = build core/codex/curate.py (cluster atoms via Clusterer -> mint/regenerate/supersede Resources) gated by faithfulness_critic -- the...  (source: mem:decision:ADR_0629214302_5390)
- where-we-are 2026-06-29: Akashic Aurora status: recall-at-action COMPLETE end-to-end (engine, CLI recall-at, PreToolUse hook additionalContext, bootstrap contract...  [relates: member_of]  (source: mem:decision:ADR_0629214301_5916)
- Write durable 'where-we-are'/decision state with  (one write), not by hand-editing the native checkpoint -- it surfaces at boot + in chronicles/memory.md. Correct by...  [relates: member_of]  (source: learn:experiment:write_once_notes_shipped)
- open-question: implicit-useful payload: PostToolUse _is_success assumes tool_response shape; verify against a live payload so the FAIL->SUCCESS signal actually fires.  (source: mem:decision:ADR_0629210203_6519)
- where-we-are 2026-06-29: Recall-at-action COMPLETE; repo PUBLIC; write-once notes SHIPPED (note/notes/boot-surface/memory.md). Next: recall-learning loop or FC-01...  [relates: member_of]  (source: mem:decision:ADR_0629210203_1187)
- where-we-are 2026-06-29: Recall-at-action COMPLETE; repo PUBLIC (Apache-2.0, CI green); contributor=balanced7.  [relates: member_of]  (source: mem:decision:ADR_0629210202_2063)
- CRITICAL: the rewrite CHANGED EVERY COMMIT SHA. Any SHA recorded in lessons/memory/docs BEFORE this (e.g. FAITH-1 d9e611c, SPINE-1 2dd8d55, recall-at 3fca65d, deploy...  [relates: member_of]  (source: learn:experiment:git_history_rewritten_balanced7)
- Don't reintroduce per-agent file/task ownership in docs/memory/handoffs. Coordinate concurrent edits with locks (transient), attribute with AKASHIC_AGENT_ID, but never...  [relates: member_of]  (source: learn:experiment:collaboration_model_no_ownership)
- Taking over a peer agent's stranded slice: review (parses? stubs? referenced files exist?), confirm tests pass, confirm CI-safety (heavy deps lazy + in a separate...  [relates: member_of]  (source: learn:experiment:cursor_slice_taken_over)
- claude -> cursor: Your gemini-web slice is COMMITTED + MCP parity DONE — verify live + set your agent id  (source: handoff:claude->cursor)
- hooks: add required matcher to SessionStart/SessionEnd/PreCompact (verified via docs)  (source: git:760f34ed6a8b)
- wrap auto-capture: PreCompact/SessionEnd -> draft file + boot pointer  (source: git:76ab5cbe4c8c)
- ship + wrap: one-command gated ship + ambient session capture  (source: git:525e75458a56)

## retrieval-critic-design: Design research for an automatic retrieval critic = ... (ai-setup)
Span: 2026-06-30T12:58:21.865926 → 2026-06-30T13:30:36.287830
Beats: 5  · Critic: True

- retrieval-critic-design: Design research for an automatic retrieval critic = docs/retrieval-critic-design.md (2026-06-30, user idea: ground context retrieval so it is...  [relates: member_of]  (source: mem:decision:ADR_0630093036_6716)
- directive-friction-audit: Friction audit of the agent directives = docs/directive-friction-audit.md (written 2026-06-30, in response to user principle: make the right...  (source: mem:decision:ADR_0630092509_1059)
- epistemic-risk-register: EPISTEMIC-RISK REGISTER (manual deep pass; grounded in real code + literature; skeptic-checked). Loop under study: usefulness -> rank -> surface...  (source: mem:decision:ADR_0630091418_4717)
- epistemic-risk-register: Accumulating per-factor risk register for the recall/memory loop (manual deep pass; grounded in real code + literature; skeptic-checked for...  [relates: member_of]  (source: mem:decision:ADR_0630085845_9543)
- next-focus: Epistemic-risk work is now MANUAL factor-by-factor in max-effort, NOT the ultracode workflow (user found ultracode missed the salient self-suggestion risks...  (source: mem:decision:ADR_0630085821_5236)

## session 2026-06-30: F1 provenance-labelled recall (opinion-laundering fix) + ... (ai-setup)
Span: 2026-06-30T23:33:38.652259 → 2026-06-30T23:34:18.331526
Beats: 3  · Critic: True

- session 2026-06-30: F1 provenance-labelled recall (opinion-laundering fix) + directive-friction-audit & retrieval-critic design docs; ranking slice paused  [relates: member_of]  (source: git:ff3a9fcb4578)
- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-06-30, before a Claude update). SHORT: Factor 1 opinion-laundering SHIPPED...  (source: mem:decision:ADR_0630193400_4519)
- where-we-are: SESSION 2026-06-30 (paused for a Claude update). ARC: deep MANUAL max-effort epistemic-risk pass (NOT ultracode -- it missed the salient self-suggestion...  (source: mem:decision:ADR_0630193338_5557)

## next-focus: Full current state + resume options = note where-we-are (refreshe... (ai-setup)
Span: 2026-07-01T04:11:47.846790 → 2026-07-01T05:01:22.414000
Beats: 5  · Critic: True

- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-07-01). SHORT: ranking-feedback INC1 pull slice SHIPPED (recall --full, total, N-of-M...  [relates: member_of]  (source: mem:decision:ADR_0701010122_3781)
- adversarial-critic-partner-idea: User idea (2026-07-01): design an adversarial partner/critic for Claude that TRAINS INDEPENDENTLY (not just prompted-in-context) and...  (source: mem:decision:ADR_0701010114_6136)
- where-we-are: SESSION 2026-06-30/07-01. Reviewed + approved both design docs (directive-friction-audit, retrieval-critic-design) -- no changes requested, both ready to...  [relates: member_of]  (source: mem:decision:ADR_0701001207_4003)
- next: the friction-audit roadmap's remaining quick-wins (auto-boot at SessionStart, turn-start bus-sync hook, identity fail-closed) or the retrieval-critic Tier 1...  [relates: member_of]  (source: learn:experiment:ranking_feedback_inc1_pull)
- ranking & feedback INC1: pull-side escape (recall --full, recall_at total, render N-of-M line)  [relates: member_of]  (source: git:f8b1e8842b55)

## next-focus: NEXT = Slice 2 of the recall-critic arc = write-side dissent capt... (ai-setup)
Span: 2026-07-01T23:20:43.667129 → 2026-07-01T23:23:15.842580
Beats: 5  · Critic: True

- next-focus: NEXT = Slice 2 of the recall-critic arc = write-side dissent capture. VERIFIED gap: agent_cli.py learn exposes only ...[truncated]  [relates: member_of]  (source: mem:decision:ADR_0701192315_6475)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md (Path 2 dialectical retrieval...  [relates: member_of]  (source: mem:decision:ADR_0701192312_2889)
- Build the yardstick + a real-corpus probe before the mechanism; trust the curated fixture and treat any detector-relative corpus metric as suspect until a precise...  [relates: member_of]  (source: learn:experiment:eval_harness_before_fix)
- Precision-first + silent-when-starved is correct: the binding constraint is corpus content, not the reader. Next lever = Slice 2 (write-side capture of anti_patterns /...  [relates: member_of]  (source: learn:experiment:recall_dissent_slice01)
- Recall dissent (Slices 0-1): eval harness + precision-first counter-finder  [relates: member_of]  (source: git:88402b3141f3)

## note: next-focus (ai-setup)
Span: 2026-07-01T23:23:15.981254 → 2026-07-01T23:45:15.698417
Beats: 5  · Critic: True

- note: next-focus  (source: event:events:raw:1782948195984-0)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md. SHIPPED + pushed, all gated...  [relates: member_of]  (source: mem:decision:ADR_0701194515_9161)
- when adding a capability to a lower layer, expose it on the SAME door agents already use, in the same slice, or it stays dead; treat door-exposure as part of done  (source: learn:experiment:capability_without_a_door)
- A write door must OFFER a field or it stays empty (0 anti-patterns came from a missing flag, not agent laziness). Auto-draft the NAME to remove the naming cost and hand...  (source: learn:experiment:recall_dissent_slice2_capture)
- Recall dissent (Slice 2): write-side capture -- expose, tag, auto-draft anti-patterns  [relates: member_of]  (source: git:a3986fe01e8b)

## note: where-we-are (ai-setup)
Span: 2026-07-01T23:45:15.812912 → 2026-07-01T23:45:21.995557
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1782949515816-0)
- next-focus: TOP PRIORITY (reprioritized by a dogfooding finding): fix Slice-1 PRECISION on real anti-patterns. The finder surfaces 7 false counters on the live corpus...  (source: mem:decision:ADR_0701194521_1667)

## note: next-focus (ai-setup)
Span: 2026-07-01T23:45:22.118491 → 2026-07-02T00:13:44.875130
Beats: 4  · Critic: True

- note: next-focus  (source: event:events:raw:1782949522122-0)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md. SHIPPED + pushed (gated green)...  [relates: member_of]  (source: mem:decision:ADR_0701201344_4961)
- An on-topic anti-pattern != a contradiction of a thesis; topic-adjacency conflates with stance. Precision-first: surface nothing you cannot verify. NEXT...  (source: learn:experiment:recall_dissent_slice3_precision)
- Recall dissent (Slice 3): precision fix -- an on-topic anti-pattern is not a contradiction  [relates: member_of]  (source: git:8170bc03d627)

## note: where-we-are (ai-setup)
Span: 2026-07-02T00:13:44.995427 → 2026-07-02T00:13:50.925220
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1782951224998-0)
- next-focus: NEXT = build the SEMANTIC GATE (the deferred tier), now that its yardstick exists (tests/test_semantic_eval.py) and an LLM-judge probe cleared it -- incl...  (source: mem:decision:ADR_0701201350_1440)

## note: next-focus (ai-setup)
Span: 2026-07-02T00:13:51.046144 → 2026-07-02T00:13:51.046144
Beats: 1  · Critic: True

- note: next-focus  (source: event:events:raw:1782951231050-0)

## leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synt... (research)
Span: 2026-07-02T01:54:07.427964 → 2026-07-02T02:10:02.912138
Beats: 2  · Critic: True

- leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synthesis of repo audit + docs read + competitive survey + DS4/antirez case study). THESIS...  (source: mem:decision:ADR_0701221002_3682)
- competitive-landscape-2026-07: Web survey 2026-07-01 (full sources in session transcript). FIELD STATE: memory is now native in every harness -- Claude Code auto-memory...  [relates: member_of]  (source: mem:decision:ADR_0701215407_2479)

## note: competitive-landscape-2026-07 (ai-setup)
Span: 2026-07-02T01:54:07.539263 → 2026-07-02T01:54:07.539263
Beats: 1  · Critic: True

- note: competitive-landscape-2026-07  (source: event:events:raw:1782957247542-0)

## note: leapfrog-plan (ai-setup)
Span: 2026-07-02T02:10:03.026276 → 2026-07-02T02:39:06.403141
Beats: 4  · Critic: True

- note: leapfrog-plan  (source: event:events:raw:1782958203028-0)
- open-question: implicit-useful payload: RESOLVED 2026-07-01 (T1 shipped, gated green). Live capture proved the old assumption unfixable rather than mistuned: Claude Code...  (source: mem:decision:ADR_0701223906_5443)
- Never trust an assumed hook payload shape: auto-capture real payloads (bounded, tempdir/akashic_recall/payloads), pin them as fixtures in a contract test...  [relates: member_of]  (source: learn:experiment:recall_implicit_credit_payload_truth)
- T1: make the implicit FAIL->SUCCESS credit real: transcript-synthesized failures + live payload contract  [relates: member_of]  (source: git:8b4ebb4eb9c4)

## note: open-question: implicit-useful payload (ai-setup)
Span: 2026-07-02T02:39:06.538266 → 2026-07-02T02:39:06.877696
Beats: 2  · Critic: True

- note: open-question: implicit-useful payload  (source: event:events:raw:1782959946541-0)
- where-we-are: T1 (leapfrog plan Wave A) SHIPPED 2026-07-01: the implicit FAIL->SUCCESS credit loop is REAL end-to-end -- proven live in-session, first helped credit ever...  (source: mem:decision:ADR_0701223906_9239)

## note: where-we-are (ai-setup)
Span: 2026-07-02T02:39:06.976744 → 2026-07-02T02:39:07.318281
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1782959946979-0)
- next-focus: NEXT per docs/leapfrog-plan.md triage (loop fires -> corpus grows -> numbers exist): T2 = write-side friction fixes (JIT learn-it? prompt at the...  (source: mem:decision:ADR_0701223907_7327)

## note: next-focus (ai-setup)
Span: 2026-07-02T02:39:07.431424 → 2026-07-02T03:32:20.921458
Beats: 12  · Critic: True

- note: next-focus  (source: event:events:raw:1782959947434-0)
- next-focus: T2 done -> NEXT per docs/leapfrog-plan.md triage: T3 = funnel instrumentation (a  verb: surfaced -> acted -> outcome -> flips -> lessons-recorded per session...  (source: mem:decision:ADR_0701233220_7796)
- where-we-are: T2 SHIPPED 2026-07-01 (leapfrog Wave A, friction-audit D5): the JIT learn nudge is live and PROVEN in-session -- a FAIL->SUCCESS flip now (1) credits...  (source: mem:decision:ADR_0701233220_3729)
- When adding a per-session state dir: update prune_state AND every dir-swapping test in the same slice; eyeball a REAL wrap render before shipping; never assert on a...  [relates: member_of]  (source: learn:experiment:t2_jit_learn_nudge_live)
- T2: JIT learn nudge at the flip instant + wrap-time candidate lessons (friction audit D5)  [relates: member_of]  (source: git:1295b8f8c23c)
- where-we-are: T1 SHIPPED (implicit FAIL->SUCCESS credit real + proven live, first helped credit in system history) AND presentation pass SHIPPED (2026-07-01): tracked...  (source: mem:decision:ADR_0701225643_5172)
- For a public showcase repo, audit git ls-files (what visitors SEE), not ls (what's local); archive-don't-delete via git mv keeps the append-only ethos; put a REAL...  (source: learn:experiment:repo_presentation_cleanup)
- README: About section in the author's own voice  (source: git:9f05e8178f40)
- README: honest About section -- solo passion project, learning in public, author link  [relates: member_of]  (source: git:130e789c38e3)
- presentation: clean tracked root to 26 entries, archive legacy subprojects, rewrite README around the proven loop  [relates: member_of]  (source: git:7fa30ab2abd4)
- Session ended  (source: session:end)
- Session started  (source: session:start)

## note: next-focus (ai-setup)
Span: 2026-07-02T03:32:21.017680 → 2026-07-02T03:32:43.645522
Beats: 2  · Critic: True

- note: next-focus  (source: event:events:raw:1782963141021-0)
- next-focus: T2 done -> NEXT per docs/leapfrog-plan.md triage: T3 = funnel instrumentation (a 'stats' verb: surfaced -> acted -> outcome -> flips -> lessons-recorded per...  (source: mem:decision:ADR_0701233243_9563)

## note: next-focus (ai-setup)
Span: 2026-07-02T03:32:43.741976 → 2026-07-02T03:43:25.310278
Beats: 5  · Critic: True

- note: next-focus  (source: event:events:raw:1782963163746-0)
- next-focus: T3 FIRST SLICE SHIPPED 2026-07-02 (stats verb: recall-value funnel, CLI+MCP+tests; first reading: 104 lessons / 370 impressions / 1 helped / lessons-per-flip...  [relates: member_of]  (source: mem:decision:ADR_0701234325_5590)
- Instrument by READING existing records, never by adding write paths; name ratios exactly what they measure; keep console output ASCII; ship CLI verb + MCP tool + tests...  (source: learn:experiment:t3_stats_funnel_first_slice)
- After context compaction/summarization, re-Read the exact target region before any Edit; budget a handful of lines, not the file  (source: learn:experiment:edit_after_context_reset)
- T3: stats verb -- the recall-value funnel (surfaced -> helped -> flips -> captured), CLI + MCP  [relates: member_of]  (source: git:b1ca4f64edda)

## note: next-focus (ai-setup)
Span: 2026-07-02T03:43:25.432191 → 2026-07-02T05:01:30.922151
Beats: 5  · Critic: True

- note: next-focus  (source: event:events:raw:1782963805435-0)
- where-we-are: FRICTION SWEEP + T3 SLICE 2 SHIPPED 2026-07-02 (one commit, gated green, ~570 tests): (1) PowerShell hook blindspot CLOSED -- matchers + both hook script...  [relates: member_of]  (source: mem:decision:ADR_0702010130_2847)
- Fix hook-coverage gaps live and verify in-session: edit matcher, run one in-scope call, check tempdir akashic_recall for the artifact. Never defer a payload-fixture pin...  [relates: member_of]  (source: learn:experiment:hook_matchers_hot_reload)
- Friction sweep + T3 trend: PowerShell hook coverage (live fixture pinned), handoff retirement, UTF-8 pipes, human flip targets, SessionStart light auto-boot, per-day...  [relates: member_of]  (source: git:909d46d3e85c)
- Add PowerShell to the PreToolUse/PostToolUse/PostToolUseFailure matchers in C:/Users/L5/.claude/settings.json AND to the tool-name filters in both hook scripts (treat it...  [relates: member_of]  (source: learn:experiment:powershell_tool_hook_blindspot)

## note: where-we-are (ai-setup)
Span: 2026-07-02T05:01:31.058450 → 2026-07-02T05:01:31.388128
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1782968491061-0)
- next-focus: Wave A is now FULLY shipped (T1 credit loop + T2 JIT nudge + T3 funnel/trend/pace + T4 contract tests incl live PowerShell fixture + friction fixes #1-#6...  [relates: member_of]  (source: mem:decision:ADR_0702010131_5819)

## note: next-focus (ai-setup)
Span: 2026-07-02T05:01:31.525547 → 2026-07-02T05:09:06.624738
Beats: 2  · Critic: True

- note: next-focus  (source: event:events:raw:1782968491528-0)
- research: greptile + skill-format 2026-07-02: Researched github.com/michaelshimeles/skills + Greptile (production AI code review) for routine/quality lessons. GREPTILE...  (source: mem:decision:ADR_0702010906_4755)

## note: research: greptile + skill-format 2026-07-02 (ai-setup)
Span: 2026-07-02T05:09:06.733769 → 2026-07-02T05:22:20.774143
Beats: 4  · Critic: True

- note: research: greptile + skill-format 2026-07-02  (source: event:events:raw:1782968946736-0)
- where-we-are: GREPTILE-INFORMED SLICES 1-3 SHIPPED 2026-07-02 (second gated commit today, on top of the friction sweep): (1) VALUE RATE = (useful+helped)/surfaced now...  (source: mem:decision:ADR_0702012220_6352)
- Mine a production competitor for SEQUENCING not just validation: their FAILED approaches close our open questions for free (LLM-as-judge self-severity nearly random =...  [relates: member_of]  (source: learn:experiment:greptile_informed_recall_polish)
- Greptile-informed recall polish: value-rate steering number, lesson graduation (superseded-by-automation), track-record tags on surfaced lessons  [relates: member_of]  (source: git:dc5a92c9dda1)

## note: where-we-are (ai-setup)
Span: 2026-07-02T05:22:20.896266 → 2026-07-02T05:26:57.632504
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1782969740899-0)
- next-focus: RESUME POINT 2026-07-02: Wave A fully shipped + friction sweep + Greptile slices 1-3 (see where-we-are ADR_0702012220). IN PROGRESS: research detour #2 --...  (source: mem:decision:ADR_0702012657_1258)

## note: next-focus (ai-setup)
Span: 2026-07-02T05:26:57.753756 → 2026-07-02T05:37:52.799658
Beats: 2  · Critic: True

- note: next-focus  (source: event:events:raw:1782970017757-0)
- research: field survey 2026-07: FIELD SURVEY COMPLETE 2026-07-02 (3 parallel research agents: skills ecosystem, individual practitioners, memory/context-engineering...  [relates: member_of]  (source: mem:decision:ADR_0702013752_3553)

## note: research: field survey 2026-07 (ai-setup)
Span: 2026-07-02T05:37:52.935070 → 2026-07-02T05:37:53.312522
Beats: 2  · Critic: True

- note: research: field survey 2026-07  (source: event:events:raw:1782970672938-0)
- next-focus: RESUME POINT 2026-07-02 (post field-survey): detour #2 COMPLETE -- see docs/field-survey-2026-07.md + note research: field survey 2026-07. USER PICKS NEXT...  (source: mem:decision:ADR_0702013753_4817)

## note: next-focus (ai-setup)
Span: 2026-07-02T05:37:53.431914 → 2026-07-02T06:09:16.158317
Beats: 12  · Critic: True

- note: next-focus  (source: event:events:raw:1782970673435-0)
- next-focus: RESUME 2026-07-02: INTEGRATION TIERS arc STARTED (user-renamed from citizenship; Composer audit validated). Tiers: T0 door / T1 identity / T2 session cue /...  (source: mem:decision:ADR_0702020915_6718)
- next-focus: RESUME POINT 2026-07-02 post adoption-wave-1. DONE from the 10-slice plan: 1 (injection ledger), 2 (plan-time recall), 3 (template + 5-dim dedup), 6...  [relates: member_of]  (source: mem:decision:ADR_0702020113_9909)
- where-we-are: FIELD-SURVEY ADOPTION WAVE 1 SHIPPED 2026-07-02 (third gated commit today; 18 files, suite ~584 green): (1) FOUR SYNTHESIZED SKILLS in .claude/skills --...  (source: mem:decision:ADR_0702020112_3238)
- Use when adopting external patterns, before building: adapt them to the house design (their SessionStart-only surfacing became our shared-anti-repeat plan+action...  (source: learn:experiment:field_survey_adoption_wave1)
- Field-survey adoption: 4 synthesized skills (memory/debugging/verification/planning), injection ledger + cost, plan-time recall hook, 5-dim near-dupe advisory...  [relates: member_of]  (source: git:1daa009d8007)
- Use when dogfooding any stdin-JSON script via shell pipes, before debugging the script itself: generate the payload with json.dumps + subprocess.run(input=...) (never...  [relates: member_of]  (source: learn:experiment:shell_pipe_json_dogfood)
- Use when any module keeps state under a module-constant tempdir path and tests can reach it transitively, before shipping: derive the path from an env var at import and...  [relates: member_of]  (source: learn:experiment:recall_state_hermeticity_env)
- harness lib: package init (Integration Tiers H0 start)  (source: git:c6717396b2bd)
- docs: field survey 2026-07 -- skills ecosystem + practitioners + memory canon; convergences, dissent, ranked adoption plan  [relates: member_of]  (source: git:426802752772)
- Session started  (source: session:start)
- Session ended  (source: session:end)

## research: local/free models via Claude Code 2026-07: RESEARCH COMPLETE 2026-0... (ai-setup)
Span: 2026-07-02T12:22:38.562766 → 2026-07-02T13:01:07.717360
Beats: 12  · Critic: True

- research: local/free models via Claude Code 2026-07: RESEARCH COMPLETE 2026-07-02 (3 parallel agents, all claims source-verified; trigger: user shared a video on free...  (source: mem:decision:ADR_0702090107_7768)
- claude -> composer: Verify + pin the Cursor hook integration (Integration Tiers H1/H2 close-out)  [relates: member_of]  (source: handoff:claude->composer)
- next-focus: NEXT after Integration Tiers H0-H3 (2026-07-02): (1) COMPOSER HANDOFF IS THE GATE -- composer must: reload Cursor (hooks.json + mcp.json changed), run one...  (source: mem:decision:ADR_0702084537_1829)
- where-we-are: INTEGRATION TIERS ARC H0-H3 SHIPPED 2026-07-02 (four gated commits: harness lib H0, plan-hook bus line H0b, cursor adapters H1, registry+tests H2...  [relates: member_of]  (source: mem:decision:ADR_0702084520_6550)
- Use when integrating a harness whose pre-action hook cannot inject context, before faking it: move injection to the post-action events (one-beat-late still catches...  [relates: member_of]  (source: learn:experiment:cursor_hooks_deny_only_workarounds)
- Use when resuming from a note/checkpoint that claims a file or feature is MISSING, before planning around it: verify with git log -1 -- <path> and ls from the repo root...  [relates: member_of]  (source: learn:experiment:resume_note_verify_missing_claims)
- Use when overwriting an existing file with Claude Code's Write tool: Read it via the Read tool first in the same conversation -- a Bash cat/type does NOT satisfy the...  (source: learn:experiment:write_tool_needs_read_tool)
- Integration Tiers H3: docs/integration-tiers.md (honest capability matrix, adapter recipe), harnesses CLI verb (registry gets a door), bootstrap.md refresh...  (source: git:be2accc0893e)
- Integration Tiers H2: harness registry (capability matrix as data), harness-lib unit pins, cursor adapter contract tests (payload layer skip-with-reason until composer...  (source: git:0b272381cf7a)
- Integration Tiers H1: five cursor hook adapters (identity+whisper, git guard, deny-only vetoes, T4 direct-fail credit + T3 one-beat-late recall, session draft) + shared...  [relates: member_of]  (source: git:1b9bf8180b57)
- plan hook H0b: unread-bus line rides plan-time recall (silent-at-0, un-ledgered cue; recall kill switch spares it)  [relates: member_of]  (source: git:334a418ec9d8)
- harness lib H0: extract scope/context/seen shared policy; claude hooks become thin translators  (source: git:90f8371eec0d)

## next-focus: MORNING BRIEF 2026-07-03 (overnight deep pass COMPLETE -- user as... (ai-setup)
Span: 2026-07-02T23:13:01.340899 → 2026-07-03T04:23:59.773738
Beats: 20  · Critic: True

- next-focus: MORNING BRIEF 2026-07-03 (overnight deep pass COMPLETE -- user asked for broad-spectrum primitives research + plan update while sleeping). DELIVERED...  (source: mem:decision:ADR_0703002359_5629)
- idea: knowledge primitives (shape axis) + tests-as-schema: USER IDEATION 2026-07-03 (via GPT chat, user-relayed; extends the sharpening-sword thesis). TWO IDEAS: (1)...  (source: mem:decision:ADR_0703000542_6378)
- Use when ANY expensive research completes (multi-agent sweep, deep-research run), before ending the turn: persist each agent's FULL findings+citations to...  [relates: member_of]  (source: learn:experiment:research_full_fidelity_preservation)
- next-focus: RESUME (written at 90pct Fable budget, 2026-07-02 ~23:45 -- frontier spend goes to ADJUDICATION ONLY): (1) SHIFT IN FLIGHT: 003 lora-rdna4 running, 004...  (source: mem:decision:ADR_0702233852_6687)
- research: knowledge compaction + consolidation field state 2026-07: TWO-AGENT SWEEP 2026-07-02 (all claims fetched+cited; feeds SQ1+SQ3; trigger: user's 'ever-sharpening...  (source: mem:decision:ADR_0702233250_1531)
- Use when standing up any continuous research/monitoring function, before the first task: anchor every unit of work to a named decision, sweep deltas not landscapes, cap...  (source: learn:experiment:landscape_watch_design)
- Use when naming agent capabilities in docs/prompts/commits: prefer the field's standard vocabulary (tool use, tool access, tool grants, toolset) over cute...  (source: learn:experiment:naming_industry_standard_tools)
- Use when local/offline agents need web discovery: self-host SearXNG (enable formats:[json], limiter off, loopback-only port) behind a compact CLI the agent calls via...  (source: learn:experiment:local_fleet_search_door)
- next-focus: NEXT 2026-07-02 evening: (1) RESEARCH DAY GOES LIVE -- user starts a shift with .\scripts\local\run_research_day.ps1 (queue has 001 MemoryArena / 002...  (source: mem:decision:ADR_0702192946_4971)
- where-we-are: LOCAL-AGENT FLEET + RESEARCH-DAY PIPELINE SHIPPED PUBLIC 2026-07-02 (after Integration Tiers H0-H3 same day). glm_local = glm-4.7-flash on native Ollama...  (source: mem:decision:ADR_0702192945_4841)
- Use when claude -p headless exits with 'Input must be provided' despite a prompt argument: put the prompt immediately after -p and pass variadic flags in assignment form...  (source: learn:experiment:headless_allowedtools_ordering)
- Use when a thinking-capable model returns an empty/blank reply through an Anthropic-compatible API, before blaming context truncation: raise max_tokens (thinking burns...  (source: learn:experiment:thinking_model_empty_reply)
- Use when a local AI server reports an unexpected old version, before debugging the install: check what OWNS the port (Get-NetTCPConnection -LocalPort N + docker ps) -- a...  (source: learn:experiment:local_ollama_port_shadowing)
- Use when adding a cheap/local agent to the fleet: the claude-code harness tiers are model-agnostic -- point ANTHROPIC_BASE_URL at a local Anthropic-compatible server...  (source: learn:experiment:local_agent_first_e2e)
- research README: full-fidelity preservation rule for frontier agent sweeps (chat is never storage; forcing-function hook queued)  [relates: member_of]  (source: git:b4baa9aacc74)
- Research day preservation: full frontier research records (local models x3 agents, compaction/consolidation x2 agents) + first two reviewed drafts (smoke...  [relates: member_of]  (source: git:ee440e6f9c0e)
- Landscape watch: watchlist (SQ1-SQ5 standing questions, 16 curated sources, maturity stages for adoption timing), delta-sweep template, feeds: convention (tasks name the...  (source: git:b4856aea4984)
- R2 naming: industry-standard terminology (tool access / toolset / tool grants) in worker prompt and docs  (source: git:53471f714c90)
- R2: local-fleet research hands -- self-hosted SearXNG discovery (websearch.py + container settings), near-frontier worker grants (Grep/Glob/py), corpus-first +...  (source: git:bdd7baffca98)
- Local-agent fleet + research-day pipeline: Ollama-backed Claude Code launcher (pre-flight probe: tool-call + context canary + speed), shift runner (fresh session per...  [relates: member_of]  (source: git:38abf7ac677b)

## next-focus: POST-REVIEW STATE 2026-07-03 ~01:00: FIRST FULL RESEARCH-DAY CYCL... (research)
Span: 2026-07-03T04:24:00.691852 → 2026-07-03T06:16:55.582148
Beats: 3  · Critic: True

- next-focus: POST-REVIEW STATE 2026-07-03 ~01:00: FIRST FULL RESEARCH-DAY CYCLE COMPLETE -- 7-task shift, 5 drafts accepted into reviewed/ with stamped verdicts, failures...  (source: mem:decision:ADR_0703021655_3410)
- Research day reviewed: 5 drafts adjudicated (003 lora ACCEPT, 005 hermes-moa ACCEPT, 006 cmi honest-failure + frontier addendum closing the SQ1 gap, 002+smoke earlier)...  [relates: member_of]  (source: git:3cedea9c3bb5)
- Overnight deep pass: knowledge-primitives full research record (3 agents: history of universal vocabularies, cross-domain pattern systems, computational analogy +...  (source: git:fcd8d383b7a1)

## next-focus: PRIORITY RE-CUT 2026-07-03 (Opus continuation after Fable hit its... (ai-setup)
Span: 2026-07-03T10:35:07.227736 → 2026-07-03T16:37:14.176715
Beats: 45  · Critic: True

- next-focus: PRIORITY RE-CUT 2026-07-03 (Opus continuation after Fable hit its limit mid-session). SHIPPED THIS RUN: (1) counter-hygiene S2a 2nd-form -- ghost counters +...  (source: mem:decision:ADR_0703123007_9545)
- Use when a pool of models (or any swappable backend) is enumerated in more than one place, before writing another caller: make ONE data roster the source of truth and...  (source: learn:experiment:fleet_dispatch_v0)
- Fleet-dispatch layer v0: an easy structure for calling local models. core/fleet = a ROSTER (single source of truth -- tag/ctx/vram/capabilities/status/disqualifier...  (source: git:7180e41d1555)
- Use when a value/triage instrument counts more tracked entities than the corpus holds, before distrusting the instrument: after fixing key-form drift, look for STALE...  (source: learn:experiment:s2a_ghost_counter_fold)
- Counter hygiene S2a (2nd form): ghost counters -- learn:experiment:* keys whose lesson was retired/renamed inflated tracked past corpus (133>131). Triage now splits...  [relates: member_of]  (source: git:7fec1fb6635f)
- next-focus: PRIORITY RE-CUT 2026-07-03 (post vision-reveal + bakeoff adjudication; user near plan limit). DOCTRINE: methodical foundation-first, NO alpha-rush to the...  (source: mem:decision:ADR_0703102009_6940)
- Use when selecting models for unattended knowledge work, before optimizing for speed: grade for SILENT-failure modes first (fabrication, citation laundering, false...  (source: learn:experiment:bakeoff_noisy_vs_silent_failure)
- a-series: the assistant layer (the revealed end goal): VISION REVEALED 2026-07-03 (user, on seeing Rika's feature list): 'Akashic Aurora is just the scaffolding' -- the...  (source: mem:decision:ADR_0703095414_5724)
- landscape: rika (convergent dreaming, no measurement): SQ1 THESIS-GUARD CHECK 2026-07-03 (user spotted github.com/nssriraam/rika via HuggingFace discord...  (source: mem:decision:ADR_0703094830_9886)
- Use when a capability probe fails on a REFUSAL rather than a wrong answer, before excluding the model: safety-tuned models pattern-match probe wording (tokens, secrets...  (source: learn:experiment:probe_phrasing_safety_refusal)
- Use when an instrument reports more tracked entities than exist, before distrusting the instrument: look for KEY-FORM DRIFT at the write doors (same entity, multiple...  (source: learn:experiment:s2a_counter_canonicalization)
- S2a: counter-key canonicalization -- votes always land on the lesson's one counter (canonicalize at the record_feedback door, idempotent migration folded 3 live orphans...  [relates: member_of]  (source: git:9734e88e760a)
- adversarial-critic-partner-idea: SCOPING RESOLVED 2026-07-03 (user: 'Integrate and lets go'): (Q1) INTEGRATE into Akashic Aurora -- reuse FAITH-1, ledger, learning...  [relates: member_of]  (source: mem:decision:ADR_0703080157_1469)
- Use when writing public docs for this project: no cutesy winks at specific readers, no self-referential meta-commentary about the doc's own review process or the owner's...  (source: learn:experiment:no_meta_selfreference_public_docs)
- Use when running outside-model review on public text: fence off settled decisions in the prompt (dates, voice, no-invented-metrics), require quoted-text-plus-fix format...  (source: learn:experiment:multi_model_review_loop)
- Use when an Edit old_string fails to match on a file you have ALREADY edited this session: your own prior edits shift wrapping/context -- re-read the exact target region...  (source: learn:experiment:edit_own_drift_reread)
- Use when writing ANY public-facing claim for this project: claims about ourselves keep (evidence attached); claims about the field become 'our survey (linked, N...  [relates: member_of]  (source: learn:experiment:public_claims_falsifiable_humility)
- Use when a hook matcher/config change seems ignored, before debugging the script: hook SCRIPTS hot-reload (fresh process per event) but settings.json hook CONFIG likely...  [relates: member_of]  (source: learn:experiment:hook_matcher_config_not_hot)
- s1-triage-adjudication: S1 FIRST TRIAGE ADJUDICATED 2026-07-03 (verb: py agent_cli.py triage; shipped gated). NUMBERS: 127 tracked sources, 8 PROTECT (all earned credit...  (source: mem:decision:ADR_0703063551_8888)
- Use when starting a knowledge-corpus sharpening pass, before building consolidation machinery: run the read-only value triage FIRST -- it sizes the opportunity, ranks...  (source: learn:experiment:sharpening_s1_triage)
- Sharpening loop S1: triage verb -- lessons ranked by measured value (protect / cost-no-return / noise-voted / watch), window token cost per source, read-only with the F2...  [relates: member_of]  (source: git:d0f60b2174cb)
- Fleet queue: re-queue 001 (memoryarena replay -- failed in the credit-death window, valuable for the CMI benchmark)  [relates: member_of]  (source: git:6e26db1fdeff)
- Fleet queue: re-queue 001 (failed in the credit-death window) + add 017 (reliable structured output for small models -- hardens the fleet caller's fmt=json) + 018...  [relates: member_of]  (source: git:a42a251d8b12)
- Chronicles: regenerated projections through the fleet-dispatch + S2-scoping + R013 arc  [relates: member_of]  (source: git:77ed11bf9d6b)
- ROADMAP: status banner -- the Waves 0-5 synthesis is foundation-era/historical; living START HERE is now the boot notes + the recent design docs (fleet-dispatch...  (source: git:37e1982b39bf)
- S2 consolidation scoping+design doc: the two-sided gate (FAITH-1 faithfulness AND a new coverage scorer -- faithfulness-only rewards over-deletion), a first-class Tests...  (source: git:58a78ff315e1)
- R013 deep-research (Opus, re-run after credit-death): full-fidelity report on standout small models for fleet subtasks. Headline: Qwen3.5 small dense series (0.8b-9b...  (source: git:60d5aa6dcaeb)
- Queue R016: clever specialist minis + subtask->model capability map (embedders/rerankers, structured-output specialists, spec-decode drafts, guard/router minis...  (source: git:88bf5874bd36)
- Queue a-series research 014 (live-viz of spine/funnel/codex -- the uniquely-ours A1) + 015 (talkable-loop orchestration + local/frontier routing, consuming R013) --...  [relates: member_of]  (source: git:be1930d69c61)
- Recover research/queue/013 (standout small models for subtasks) from the plan-limit-killed session -- sub-agents died on credit exhaustion, brief preserved for the free...  (source: git:1e8ce5d54618)
- Chronicles: regenerated story/memory projections through the bakeoff + yardsticks arc  [relates: member_of]  (source: git:1599478c7a3d)
- Research bookkeeping: 002/003/005 reviewed+done, fleet tasks 008-010 queued (critic calibration, minimal critic strength, MoE offload), bakeoff runlog  (source: git:9450a05dadf2)
- Semantic-gate yardsticks: labeled contradiction + action-applicability datasets and a scored harness (measurement-first; the gate itself is a later slice)  (source: git:5f6b83af89d3)
- Model bakeoff report: glm retains the fleet -- the trade at this tier is noisy-vs-silent failure, not speed-vs-depth (qwen: citation laundering; gpt-oss: fluent...  (source: git:1f74f052d176)
- Preflight canary: neutral self-test wording -- 'output the SECURITY TOKEN' made a safety-tuned model refuse the probe (gpt-oss:20b); probes must not pattern-match as...  [relates: member_of]  (source: git:5a72c047d439)
- README: FSQ pointer after the not-yet section (where skepticism is primed); FSQ published as Discussion 2  (source: git:fa2587a3ddf4)
- docs/FSQ.md: frequently anticipated skeptical questions -- the isn't-this-just-RAG / where-are-benchmarks / what's-novel answers, each honest and record-linked, prep for...  (source: git:6a22a0964960)
- Voice correction: cut reader-wink and inner-skeptic codification from JOURNEY/VOICE (self-referential meta = bloat; the artifact exhibits discipline, never describes it)  (source: git:3e6e53dbd625)
- Final polish (Gemini round 4): user-cancelled wording, python3 note inside the quickstart block; VOICE.md acceptance test (owner's inner skeptic = the final gate)...  [relates: member_of]  (source: git:064f56a089f6)
- Presentation round 3 (GPT ideas + Gemini convergence): README inverted for the 90-second reader + one-sentence experimental thesis + name section removed (owner call)...  [relates: member_of]  (source: git:8299412c704b)
- VOICE.md: origin-sentence decision settled (kept, owner rationale recorded as a voice rule)  (source: git:55eac89d43ea)
- README polish via two guardrailed Gemini loops (lesson scope, credit-signal mechanics, spine gloss, integration-tiers link, review transparency) + docs/VOICE.md: the...  [relates: member_of]  (source: git:768060c62e87)
- Journey + fossils: multi-model review folds (thesis elevated, immunity claim softened, working-principles framing, real citations, metrics; docs/FOSSILS.md fossil record...  (source: git:b74c45c2c9bb)
- Public voice: humble-register README (facets-explored framing, fleet section, 601 tests), docs/JOURNEY.md human-readable history (arc-close append ritual wired into both...  [relates: member_of]  (source: git:f22c4fe55c1c)
- Task-payload capture (auto-archive step 1): posttooluse captures Agent/Task tool payloads, session-scoped, capture-only; user-level matcher gains Task (verification...  [relates: member_of]  (source: git:ae73296c8888)

## research: standout small models for fleet subtasks 2026-07: R013 deep-researc... (research)
Span: 2026-07-03T16:16:37.141471 → 2026-07-03T16:16:37.141471
Beats: 1  · Critic: True

- research: standout small models for fleet subtasks 2026-07: R013 deep-research on Opus (re-run after prior session's fleet sub-agents died on credit exhaustion...  (source: mem:decision:ADR_0703121637_1686)

## Use when reviewing/promoting ANY local-model research draft before trusting i... (research)
Span: 2026-07-04T03:12:29.196561 → 2026-07-04T03:12:33.736192
Beats: 2  · Critic: True

- Use when reviewing/promoting ANY local-model research draft before trusting it: grade the Sources section against the Findings/Confidence prose, not just each other -- a...  [relates: member_of]  (source: learn:experiment:evening_review_citation_honesty_own_fleet)
- research: shift 2026-07-03 evening review: SHIFT RESULT: 12 tasks attempted, 5 clean DONE (001,004,008,012,018 by runner's format-only bar), but 'done' means...  (source: mem:decision:ADR_0703231229_7143)

## Use when inserting a method right after __init__ (or any method) via Edit: in... (ai-setup)
Span: 2026-07-04T03:13:42.338858 → 2026-07-04T05:10:33.026487
Beats: 8  · Critic: True

- Use when inserting a method right after __init__ (or any method) via Edit: include the FULL preceding method body in old_string, or anchor the insertion at a clear...  (source: learn:experiment:edit_insert_method_absorbs_init_tail)
- Use when building a human-in-the-loop control over a long-running agent loop: a pause flag checked only between tasks won't interrupt work-in-progress -- put an...  (source: learn:experiment:bifrost_live_console_adaptive_interject)
- Use when a bus runner must DO work (read/search/inspect) not just chat: reuse the interactive client's guarded Agent+ToolBox rather than writing a second tool loop; key...  (source: learn:experiment:bifrost_deepseek_agentic_peer)
- Use when adding a stateless model as a live Bifrost peer: mirror bifrost_runner.py (the wake-adapter template), reuse ask_<model>.py's load_key/BASE_URL, register an...  [relates: member_of]  (source: learn:experiment:bifrost_deepseek_runner_live)
- Use when exposing a REMOTE model to LOCAL tools (any agentic CLI over a provider API), before shipping the tool executor: put every deny in the harness, never the prompt...  (source: learn:experiment:remote_model_local_tools_guards)
- Use when wiring ANY OpenAI-compatible frontier provider (DeepSeek/etc.), before building a subprocess CLI bridge: for anything conversational, use the openai client with...  [relates: member_of]  (source: learn:experiment:deepseek_api_over_cli_bridge)
- Research shift cancelled mid-run (user request, 2026-07-03 23:1x): another Claude session is actively wiring in DeepSeek; blindly re-running the same failing batch...  (source: git:46e430875ab7)
- Evening review of the 2026-07-03 research shift: promoted 2 solid drafts (deepseek-v4 parallels w/ a citation-honesty correction; screenspace tool stack) to reviewed/...  [relates: member_of]  (source: git:b86db1cd2c89)

## where-we-are: 2026-07-04 (big night). SHIPPED: multi-agent Bifrost fleet (4 a... (ai-setup)
Span: 2026-07-04T10:21:31.202601 → 2026-07-04T10:21:31.202601
Beats: 1  · Critic: True

- where-we-are: 2026-07-04 (big night). SHIPPED: multi-agent Bifrost fleet (4 agents: claude super_admin, deepseek admin/UI-writer, deepseek-ui member/design-consultant...  (source: mem:decision:ADR_0704062131_6748)

## Use when building any multi-agent messaging UI where the user shouldn't need ... (ai-setup)
Span: 2026-07-04T16:19:54.761310 → 2026-07-05T00:04:49.128285
Beats: 71  · Critic: True

- Use when building any multi-agent messaging UI where the user shouldn't need to manage agent lifecycle: (1) Check presence before every send. (2) Auto-launch offline...  (source: learn:experiment:auto_launch_offline_agent_on_send)
- Use when adding drag-and-drop or clipboard paste to any web-based tool: (1) Always show a preview during drag-over — a filename list at minimum, an image thumbnail if...  (source: learn:experiment:rich_file_drop_clipboard_paste)
- Use when building any agent-output-explanation UI that needs to be teachable, not just logged: (1) Buffer traces into per-agent ring buffers by intercepting the message...  (source: learn:experiment:slide_deck_card_system)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (2026-07-04 late, continued). SHIPPED+pushed this arc: (1) smart negotiation gate...  (source: mem:decision:ADR_0704182419_3437)
- Narration control: UI-toggleable claude reasoning-visibility (off/key/full, default key) -- control.get/set_narration_level + gated trace.narrate()  (source: git:07a3cca59a74)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (2026-07-04 late). SHIPPED (all pushed to origin/master): (1) smart negotiation gate in...  (source: mem:decision:ADR_0704181225_4542)
- Akashic hooks meant to fire in Daniel's normal (home-rooted) sessions MUST live in USER settings (~/.claude/settings.json) with ABSOLUTE paths -- project-settings hooks...  [relates: member_of]  (source: learn:experiment:claude_trace_hook_user_vs_project_settings)
- Use when adding any new live-status display to a periodically-polled UI: always fingerprint the data first (JSON.stringify + compare to last-known). Build DOM only on...  (source: learn:experiment:hud_fingerprint_diff_pattern)
- aurora-glass-synthesis-decision-2026-07-04: # Aurora Glass — Synthesis Decision (2026-07-04)

**Context**: Daniel initiated a parallel UI-design task: both DeepSeek and...  (source: mem:decision:ADR_0704175535_5868)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (continued 2026-07-04 evening). RESOLVED open-loop #1: the boot note claimed an UNCOMMITTED...  (source: mem:decision:ADR_0704172521_8664)
- When gating a coordination primitive for noise, gate on whether a collision is POSSIBLE (peers online) and surface only when one is FOUND (non-green verdict) -- don't...  (source: learn:experiment:smart_negotiation_gate)
- Use when tempted to add reasoning/narration to Claude's trace feed: DON'T by default -- Daniel accepted description-as-proxy and rejected narration on token-cost grounds...  (source: learn:experiment:claude_trace_narration_deferred)
- Use when giving a hook-driven (non-runner) agent live trace parity, before trying to surface its thinking: emit tool-call traces from a broad-matcher PreToolUse hook...  [relates: member_of]  (source: learn:experiment:claude_trace_parity_via_hook)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: PLUMBING IS CLEARED. Next session's focus (Daniel's call): RESURFACE THE UI DESIGN (Aurora Glass) -- the...  (source: mem:decision:ADR_0704164627_4596)
- Use when resuming a halted agent, before building anything: pull the latest commit and check for NEW files in the area you planned to work. The bus can't coordinate a...  (source: learn:experiment:bifrost_api_exists_no_duplicate)
- Use bifrost.api as the single onboarding template for agent coordination. An agent that doesn't plan() has no standing to claim files; covers() is the enforcement...  (source: learn:experiment:bifrost_api_reusable_coordination_surface)
- where-we-are 2026-07-04 deepseek continued: SHIPPED 2026-07-04 (DeepSeek session, continued): UI freeze fix (applyStatus fingerprint cache + renderRecipient removed from...  (source: mem:decision:ADR_0704162654_8226)
- Use when a TURN-BASED agent must react to async events (a bus, a queue) while idle, before relying on discipline to re-arm a listener: the wake mechanism (background...  [relates: member_of]  (source: learn:experiment:heimdall_wake_from_idle)
- end-of-session-2026-07-04-deepseek: 2026-07-04 end-of-session: negotiation UI patch applied to scripts/bifrost_ui.py (uncommitted WIP). Three server-side changes + one...  (source: mem:decision:ADR_0704153121_8413)
- where-we-are 2026-07-04 (coordination layer + UI cockpit session): MASSIVE session. SHIPPED to master (all tested+pushed): A1 targeted-halt -> A0.1 guard_write...  (source: mem:decision:ADR_0704152856_9355)
- competitive positioning: policy-swappable coordination control plane: Web-model landscape analysis relayed 2026-07-04 (updates competitive-landscape-2026-07). VERDICT...  (source: mem:decision:ADR_0704152438_8163)
- checkpoint-2026-07-04-deepseek-slice: DeepSeek's working set at checkpoint (2026-07-04 evening):

SHIPPED + GREEN:
- core/coord/metrics.py — Solution-Space-Shrinkage...  (source: mem:decision:ADR_0704151927_8794)
- Use when positioning the project externally: never claim "ahead of SOTA" absolutely — it's axis-dependent. The differentiator is: "We're exploring a different layer of...  (source: learn:experiment:positioning_correction_axis_specific)
- Use when building the coordination loop: after user input, always fire a negotiation round before agents start working. An agent that doesn't propose has no standing to...  (source: learn:experiment:negotiation_round_proposal_primitive)
- critique: JIT context-hydration is an optimization, not a phase change: Web-panel (gpt+deepseek+gemini) critique series, 2026-07-04, on enriching orphaned bus events...  (source: mem:decision:ADR_0704145609_6378)
- Use when evaluating whether to add another substrate primitive: ask "is this an admissibility decision or a relevance decision?" Admissibility → substrate. Relevance →...  (source: learn:experiment:substrate_overreach_critique)
- Use when designing a context-propagation layer atop the bus: context should be SELECTIVELY assembled, not MAXIMALLY attached. The tiered approach prevents the...  (source: learn:experiment:context_hydration_critique)
- critique: JIT context-hydration is an optimization, not a phase change: Web-panel (gpt+deepseek) critique relayed 2026-07-04. On enriching orphaned bus events with...  (source: mem:decision:ADR_0704145319_2602)
- Use when designing interactive UIs that handle bursty event streams. The core philosophy: THE MAIN THREAD SHALL NEVER WAIT. The typing cursor is the player's crosshair...  (source: learn:experiment:modern_doom_idtech_ui_primitives)
- modern-doom-idtech-primitives-for-bifrost-ui: # Modern Doom Engine Primitives for Bifrost UI (id Tech 6/7, Doom 2016/Eternal)

This supersedes the earlier "classic Doom"...  (source: mem:decision:ADR_0704145239_1170)
- Use when building or debugging interactive UIs that receive high-frequency events: the renderer should serve the user's experience, not be a slave to the event stream...  [relates: member_of]  (source: learn:experiment:doom_primitives_ui_design)
- doom-engine-primitives-for-bifrost-ui: # Doom Engine Primitives Applied to Bifrost UI

## Why Doom's design matters for a chat UI

Doom ran at 35 fps on a 33 MHz 486...  (source: mem:decision:ADR_0704144917_2065)
- Use when designing the belief update protocol between experiment harness output and KB writes: don't gate on a binary switch (single-run delta -> promote or block)...  (source: learn:experiment:belief_three_layer_architecture)
- belief-architecture-three-layer-2026-07-04: # Three-Layer Belief Architecture (GPT + DeepSeek web, 2026-07-04)

## The insight
GPT identified the missing layer between...  (source: mem:decision:ADR_0704143513_4651)
- MILESTONE: intent-declaration (Policy 0) is real + live-proven: 2026-07-04: core/coord/intent.py shipped @294a666, 7 tests + live-proven. Coordinate by INTENT not file...  (source: mem:decision:ADR_0704142502_9672)
- Use when building a cross-run metric tracker alongside a peer building the primitive: separate files with a shared model (ApproachVector bridges experiment.py ↔...  [relates: member_of]  (source: learn:experiment:metrics_shrinkage_tracker_built)
- Use as a standing rule recorded in project notes so it appears in every agent's boot context: default to the cheapest path that fully does the job. Use read_file with...  (source: learn:experiment:sprint_pattern_token_frugality_standing_rule)
- Use at sprint start: state who's doing what. If two agents are trying to do the same job, the coordination cost eats the productivity gain. If the human is trying to...  (source: learn:experiment:sprint_pattern_role_clarity)
- Use at the end of every sprint: close with a retrospective that names the repeatable patterns. The loop is review->design->build->prove->document->retrospect. A tired...  (source: learn:experiment:sprint_pattern_close_the_loop)
- Use after every major capability wave, before building the next: write or update the invariant document. If you can't state the invariant in one sentence, you don't...  (source: learn:experiment:sprint_pattern_state_invariant_map_primitives)
- Use when shipping any coordination primitive (lock, halt, nudge, write-gate): live-prove it in the same session. Don't ship a lock without having an agent try to violate...  [relates: member_of]  (source: learn:experiment:sprint_pattern_live_proof_same_session)
- Use when building a safety-critical or coordination-critical feature: have TWO agents design it independently against the same problem description. If they converge...  (source: learn:experiment:sprint_pattern_codesign_with_peer_over_bus)
- Use when designing a new coordination primitive or architectural change, before writing code: run the design past at least one external model that DID NOT help design...  (source: learn:experiment:sprint_pattern_external_review_before_build)
- Use when starting a new capability area (coordination, persistence, messaging), before building any feature that depends on it: build the primitive first as a standalone...  [relates: member_of]  (source: learn:experiment:sprint_pattern_substrate_before_features)
- Use when an agent has a cap but no tool: add the door on the same toolbox, gate it on the cap.  (source: learn:experiment:deepseek_kb_write_door)
- deepseek-kb-write-enabled: DeepSeek can now author KB notes/lessons via knowledge_note/knowledge_learn (kb.learn gated). Enabled 2026-07-04.  (source: mem:decision:ADR_0704141507_2501)
- Stage-3 evidence #1: intent-gate beats lock-gate (measured): FIRST measured result from core/coord/experiment.py (committed 9e3ab9d, 5 tests green, A/B/C+W evaluator)...  (source: mem:decision:ADR_0704140942_1347)
- coordination: intent-first (Policy 0), locks as enforcement + 3-part evaluator: ADJUSTMENT from GPT critique (2026-07-04...  (source: mem:decision:ADR_0704140127_7983)
- Stage-2 verdict + Stage-3 evidence mandate (multi-model review): 2026-07-04 multi-model design review (Gemini+GPT+DeepSeek web, Daniel-curated) -> full record...  (source: mem:decision:ADR_0704134029_8082)
- coordination reframe: social -> environmental (game-AI lens): DeepSeek's game-AI analysis (2026-07-04, user-shared screenshot; claims VERIFIED against code) reframes the...  (source: mem:decision:ADR_0704132351_4717)
- Use when you need exclusive access to a file another agentic peer may touch, before editing: a broadcast 'please hold' is advisory and a RESUMED peer will just resume...  (source: learn:experiment:advisory_hold_needs_lock_not_broadcast)
- Use when restarting a singleton-locked runner after a hard kill, before relaunching: the runner_lock does NOT verify holder liveness on acquire, so a killed holder...  (source: learn:experiment:runner_lock_stale_after_kill)
- Use when adding per-agent freeze to a system that already has a global pause, before writing per-agent keys: make is_halted(agent) = global OR agent-flag, and route...  [relates: member_of]  (source: learn:experiment:bifrost_targeted_halt_a1)
- directive: token frugality (claude+deepseek): STANDING RULE (Daniel, 2026-07-04): both claude and deepseek default to the cheapest path that fully does the job. (1) min...  (source: mem:decision:ADR_0704121954_8946)
- Rich file drop: drag-drop w/ image preview + nested-drag fix, Ctrl+V clipboard paste (screenshots/files), inline glass file cards w/ thumbnail+icon+size. DeepSeek  (source: git:a479604199fd)
- Dark-background pass (Daniel photo): dim body glow washes .16/.20->.05/.06 + aurora shader intensity 1.0->0.7 (dark base, aurora stays in top bands); persistent...  (source: git:32e0d4458c05)
- Mockup CSS alignment: Razer bubble chamfer 5px/15px, wider 1180px cockpit, deeper glass blur(26)+saturate(1.35). DeepSeek  (source: git:b80e7ee24fa8)
- Thinking-cloud presence (claude, per Daniel's sketch): bottom-left active-agent avatar + a glass thought-bubble showing its live thinking/activity with trailing puffs --...  (source: git:61980e120161)
- Vertical rich-Presence panel (claude): standalone presence-rail.js tile variant per Daniel's Aurora Glass mockup -- avatar+name+state badge+live status+activity meter...  (source: git:331efbc202e1)
- Aurora shader default-ON (was hidden behind opt-in flag; isSupported+fps fallback guard it) -- the shock factor now shows on load  (source: git:f863f4de9be0)
- Narration toggle UI: POST /narration + settings off/key/full buttons reading control.get_narration_level (Daniel dials claude reasoning visibility). DeepSeek: UI wiring...  (source: git:b5f1ef061e23)
- Void theme legibility: bump --faint #4a5270->#7581a3 (WCAG 2.6:1->5.1:1 over glass, was failing AA)  (source: git:dc0ec3a091be)
- Deck<->viz bridge: header Deck button + full-view deck mode, always-on trace/edge feeding, card-nav sync. DeepSeek: bridge integration + viz engine  (source: git:d80724f2c471)
- Viz engine live: bifrost_viz.js (card registry + bar/heatmap/force-graph/timeline canvas cards) + viz-canvas integration + aurora speed/intensity sliders + Void theme...  (source: git:b262f3fd3520)
- OLED Void theme (claude lane): standalone self-registering theme-void.js -- true #000 black + saturated neon, burn-in-aware; drops into the theme variant registry  (source: git:a4162afa79ed)
- Aurora Glass cockpit live: HUD glanceability strip + aurora shader integration + slide-deck cards + dual-variant bench + design docs. DeepSeek: HUD, shader integration...  (source: git:196fb1a85594)
- Aurora shader: fold in Daniel's shaderpark/awwwards inspiration -- radial vignette + film grain (awwwards), live-tunable setSpeed/setIntensity params (Shader Park) for...  (source: git:1120f1e7ca41)
- Aurora shader (claude lane): standalone AuroraShader (FBM+domain-warp+blackbody LUT, center-dark envelope, setState 0/1/2 contract, visibility+DPR perf gates) + preview...  (source: git:199faae0c7ab)
- UI design: Aurora Glass parallel-task deliverables (claude) + settled synthesis (deepseek full-ACK)  (source: git:70ee33a04170)
- UI: smart negotiation gate -- fire a round only when >=2 agents online, surface only amber/red verdicts (silent on green)  (source: git:223f502f3a42)
- UI: roster shows all bus agents + pause banner shows who/why  (source: git:85713e505878)

## where-we-are 2026-07-05 -> governed coordination system + UI composition pend... (ai-setup)
Span: 2026-07-05T12:43:02.618818 → 2026-07-05T17:34:06.371381
Beats: 25  · Critic: True

- where-we-are 2026-07-05 -> governed coordination system + UI composition pending: BIG THING BUILT THIS SESSION: a GOVERNED COORDINATION SYSTEM to end the multi-agent...  (source: mem:decision:ADR_0705133406_9182)
- Prototype: semantic drift_check (core/narrative/drift.py) over the narrative spine -- catches scope-drift (routes to a different track), rework (near-dup beat), homeless...  [relates: member_of]  (source: git:32401fb812b7)
- Coordination Slice D: the conductor (core/coord/conductor.py) -- impure shell over the pure ledger: stamps time, live Redis mirror, RESOLVED bus marker on close...  [relates: member_of]  (source: git:b85284767da6)
- Coordination Slice C: read-state-first. format_state() renders DONE(closed)/IN-PROGRESS/NEXT+RULE; wired into agent_cli boot AND bifrost_wake so every agent reads the...  (source: git:42ac1c3f3962)
- Coordination Slice B: Redis mirror + fast read API on the task ledger. save() write-throughs to Redis; read_ledger prefers Redis, falls back to git (source of truth)...  [relates: member_of]  (source: git:84ba8959e611)
- Coordination Slice A: governed task-ledger deterministic core (core/coord/task_ledger.py) -- validated lifecycle state machine, claim/serialize/done gates, atomic...  (source: git:705e9dde4d90)
- Slice 2 (deepseek lane): context-hints v2 (core/comm/context_hints.py ring buffer) + cognitive-metrics (core/coord/cognitive_metrics.py token-efficiency tracking) + hint...  (source: git:7cf9c8254ee0)
- sprint-retrospective-patterns-that-worked-2026-07-05: # Sprint Retrospective: Patterns That Made This Productive (2026-07-04/05)

## Pattern 1: Parallel Tracks With a...  (source: mem:decision:ADR_0705090551_1403)
- Use when designing ANY coordination or safety primitive: make it deterministic first. No model in the loop. Pure functions, environmental locks, TTL'd buffers, policy...  [relates: member_of]  (source: learn:experiment:sprint_pattern_deterministic_before_llm)
- Use when two agents need to build on the same surface simultaneously: define a SHARED CONTRACT PRIMITIVE (an interface, a registry, a setState API) BEFORE anyone writes...  (source: learn:experiment:sprint_pattern_parallel_tracks_with_seam)
- evidence-driven-architecture-research-pivot-2026-07-05: # Evidence-Driven Architecture — The Research Pivot (2026-07-05)

GPT's analysis: "The next unit of work isn't...  (source: mem:decision:ADR_0705090059_6831)
- Use when you have multiples of the same model: give ONE agent --allow-write and the rest read-only. The read-only agents must produce complete, copy-pasteable designs...  (source: learn:experiment:sprint_pattern_design_without_write)
- Use before a multi-agent sprint: declare who touches what files. One agent per file. If two agents need the same file, sequence them — builder commits, then the next...  (source: learn:experiment:sprint_pattern_four_agent_pipeline)
- Use mid-sprint, when you have something working: screenshot it and ask at least two external models 'What am I missing? What does this remind you of? What breaks?' Their...  (source: learn:experiment:sprint_pattern_external_review_as_steering)
- stage-3-evidence-gap-analysis-2026-07-05: # Stage-3 Evidence — Current State & Gap Analysis (2026-07-05)

## BUILT + TESTED
- `core/coord/experiment.py` — A/B/C(+W)...  (source: mem:decision:ADR_0705085814_4822)
- experiment-pivot-gpt-analysis-2026-07-04: # Experiment Pivot — GPT's Full Analysis (2026-07-04)

## Verdict
The next unit of work isn't another primitive — it's...  (source: mem:decision:ADR_0705085726_6313)
- drift test: clearer near-dup pair for the rework case (>0.6 Jaccard); 5 tests green  [relates: member_of]  (source: git:4848d9f19f32)
- Coordination Slice E: migrate real backlog into the governed ledger -- coordination substrate anchored DONE, 6 real tasks (UI composition chain + backend + verify)...  (source: git:df59267b181b)
- gitignore: state/* not state/ so the coordination ledger (state/coord/) is trackable while runtime state stays ignored  (source: git:bfb35c737730)
- Slice 1 (clean tree): gitignore runtime scratch/state/logs  (source: git:c9a5e70d85ad)
- Composition spec: one-owner-per-file refinement -- plumbing sole owner of bifrost_ui.py (incl reasoning-cards); claude = design lead + reviewer + standalone modules, no...  (source: git:845eaf8f22c9)
- UI composition spec (coordination test, Daniel delegated): restraint decisions + one-owner-per-file lanes; source of truth for the composed Aurora Glass pass  [relates: member_of]  (source: git:23f984f1a736)
- Presence avatar docks to the composer: left aligns to the centered 1180px app column (was stranded at viewport edge on wide screens); bottom:88px near the composer  (source: git:99f3605cd988)
- Presence avatar compact (Daniel: small presence one alongside message avatars): shrink pcav 46->38, cloud smaller/tighter  (source: git:255eaa606069)
- Auto-launch offline agents on send (Daniel: no buttons): _send checks presence, spawns offline targets via launcher.launch, returns launched[]+steer-ack msg; UI toasts...  (source: git:1001c4416e0e)

## Use when an agent without native vision needs to see a screenshot: pipe the i... (ai-setup)
Span: 2026-07-06T00:18:56.913303 → 2026-07-06T00:49:22.685409
Beats: 3  · Critic: True

- Use when an agent without native vision needs to see a screenshot: pipe the image through `py scripts/ask_gemini_vision.py <file> "describe this UI in detail"`. The...  (source: learn:experiment:gemini_vision_screenshot_analysis)
- Fix runner crash: define missing --accept-hints arg (AttributeError killed deepseek runner on startup)  (source: git:824991184a55)
- Grant DeepSeek shell access: --allow-exec on bifrost runner + deepseek-build launch spec + exec cap in acl. Lets DeepSeek build unattended while claude is at weekly...  (source: git:434cd3d12cd3)

## gemini-vision-bifrost-screenshot-output: placeholder (vision)
Span: 2026-07-06T01:09:01.548728 → 2026-07-06T04:54:20.676756
Beats: 2  · Critic: True

- gemini-vision-bifrost-screenshot-output: placeholder  (source: mem:decision:ADR_0706005420_5841)
- vision-models-local-screen-understanding-2026-07: # Vision Models for Local Screen Understanding — Research (2026-07-06)

DeepSeek's analysis, prompted by Daniel's idea...  (source: mem:decision:ADR_0705210901_8008)

## where-we-are: 2026-07-07 night wrap. ARC: designed + researched two convergen... (ai-setup)
Span: 2026-07-07T01:17:05.190702 → 2026-07-07T05:57:34.464883
Beats: 72  · Critic: True

- where-we-are: 2026-07-07 night wrap. ARC: designed + researched two convergent features; built research tooling; did NOT build either feature yet. (1) RENEW = membrane's...  (source: mem:decision:ADR_0707014952_1424)
- For a TRULY blind peer cross-check, fence the peer off from your synthesis -- hand ONLY the raw question + codebase, never your notes/design section (a peer that reads...  (source: learn:experiment:blind_crosscheck_needs_fencing)
- session-chaptering-bookends-idea: FEATURE (Daniel + GPT, 2026-07-07 v3): manual+auto 'bookends' segmenting a session into confined, titled EPISODES (WHAT + WHY). One...  (source: mem:decision:ADR_0707013232_4724)
- session-chaptering-bookends-idea: FEATURE (Daniel 2026-07-07, v2): manual+auto 'bookends' segmenting session logs into confined, titled bounds (WHAT happened + WHY). One...  (source: mem:decision:ADR_0707012919_4341)
- session-chaptering-bookends-idea: FEATURE IDEA (Daniel 2026-07-07): manual+auto 'bookends' that segment session logs into confined, titled bounds so it's clear WHAT...  (source: mem:decision:ADR_0707012451_5292)
- To turn ephemeral agent-in-flight telemetry into a reviewable dataset, DON'T touch the hook hot path -- add a standalone bus-tailing recorder as its own read-only agent...  [relates: member_of]  (source: learn:experiment:renew_two_birds_bus_recorder)
- open-docket: RENEW research scope (before building the membrane's Renew job; see renew-membrane-temporal-job + docs/agent-membrane-design-2026-07.md): A[EMPIRICAL,FIRST]...  (source: mem:decision:ADR_0707010253_4195)
- renew-membrane-temporal-job: RENEW = the membrane's 5th job, operating ACROSS the session boundary (the other 4 are within-session). It is Capture->Surface fired as a...  (source: mem:decision:ADR_0707010239_6323)
- SESSION HANDOFF 2026-07-07 -> membrane 1+2 done, legacy retired; 2 open flags: RESUME: py agent_cli.py boot claude --task '<slice>'. Design...  (source: mem:decision:ADR_0707005504_8468)
- SESSION HANDOFF 2026-07-07 -> membrane slices 1+2 done, legacy retired; 3 open flags for next session: RESUME: py agent_cli.py boot claude --task '<slice>'. Full state...  (source: mem:decision:ADR_0707005354_9003)
- where-we-are 2026-07-07 -> Membrane slices 1+2 done + legacy retired + reconcile wired; next slice 3: MEMBRANE build (docs/agent-membrane-design-2026-07.md). DONE: slice...  (source: mem:decision:ADR_0707005011_7573)
- Use when a reachability/dead-code gate flags a module: investigate CAPABILITY before deleting -- 'unwired' can mean 'a real safety net nobody wired', not 'dead'. Port...  (source: learn:experiment:unwired_safety_net_was_a_live_gap)
- Legacy retirement + reconciler PORT: deleted 3 redundant modules (coordinator_service, redis_sync_coordinator facade, sync_reconciler wrapper) + 2 coordinator tests...  [relates: member_of]  (source: git:04dfe0b21fc0)
- where-we-are 2026-07-07 -> Membrane: slices 1(door)+2(wiring) SHIPPED, next Surface->orientation or capture: MEDIATION MEMBRANE build...  (source: mem:decision:ADR_0707001657_1347)
- Use to catch built!=wired drift: BFS the import graph from PRODUCTION entry points (not tests) over your substrate package; anything unreachable is latent. Exclude...  (source: learn:experiment:built_not_wired_reachability_gate)
- where-we-are 2026-07-07 -> Membrane: door slice DONE (debt 12->0), next check_wiring or Surface: MEDIATION MEMBRANE build (design...  (source: mem:decision:ADR_0707000933_1106)
- where-we-are 2026-07-07 -> Membrane build: slice 1a+1b shipped, door debt 12->7: MEDIATION MEMBRANE build (design: docs/agent-membrane-design-2026-07.md). SHIPPED: 1a...  (source: mem:decision:ADR_0707000237_4619)
- where-we-are 2026-07-06 -> Membrane BUILD started: slice 1a door-parity SHIPPED, next 1b gap paydown: MEDIATION MEMBRANE build underway (design...  (source: mem:decision:ADR_0706235649_4068)
- where-we-are 2026-07-06 -> FOUNDATIONAL: Mediation Membrane named (System 5), in research before first slice: FOUNDATIONAL DIRECTION (Daniel): a mediation membrane...  (source: mem:decision:ADR_0706234003_2533)
- Use before building an agent-experience/mediation layer: check whether the runtime HOOKS already are it (they mediate ambiently). Verify docs vs code -- 'we built X'...  [relates: member_of]  (source: learn:experiment:mediation_membrane_is_the_hook_layer)
- where-we-are 2026-07-06 -> Wave 1 (L0-L3b-auto) SHIPPED + comprehension layer ENFORCED: Two arcs done 2026-07-06. (1) RELIABILITY Wave 1 per...  (source: mem:decision:ADR_0706231037_9025)
- Use when documenting an expanding codebase: do NOT write a comprehensive manual (it rots). Write a stable-altitude subsystem map + a generator that emits per-module...  (source: learn:experiment:living_docs_survive_only_if_stable_autogen_or_gated)
- Use when improving multi-agent memory/recall: fix the CORPUS not the reader (act on funnel triage; mine flips_corpus_gap for new lessons). Add per-agent CREDIT...  [relates: member_of]  (source: learn:experiment:multiagent_context_credit_not_tags)
- where-we-are 2026-07-06 -> Wave 1: L0/L1/L5/L3a/L3b/L3b-auto(+hardening) SHIPPED, next L3c-remainder: Methodical scaffolding...  (source: mem:decision:ADR_0706224220_8916)
- L3b-auto hardening (DeepSeek review catches): PERSIST armed set in Redis (bifrost:auto_revive) so it survives UI/supervisor restart + is shared/CLI-reachable...  (source: git:04fffeac3f2d)
- where-we-are 2026-07-06 -> robustness Wave 1: L0/L1/L5/L3a/L3b/L3b-auto SHIPPED, next L3c-remainder: Methodical scaffolding per...  (source: mem:decision:ADR_0706223521_7290)
- L3b-auto (opt-in auto-revive): monitor _check_auto_revive() auto-revives ARMED+wedged agents with own storm guard (disarms after cap) + in-flight guard; POST...  (source: git:dda73834f081)
- Use when designing multi-agent coordination: prefer stigmergy (readable leases/zones in the shared substrate that planners steer around) over negotiation for structural...  (source: learn:experiment:coordination_via_stigmergy_not_negotiation)
- where-we-are 2026-07-06 -> robustness Wave 1: L0/L1/L5/L3a/L3b SHIPPED, next L3b-auto: Methodical scaffolding per docs/agent-failure-modes-mitigation-roadmap-2026-07.md...  (source: mem:decision:ADR_0706222041_9925)
- L3b (manual revive): Launcher.revive() (kill->free lock->relaunch) + runner_lock.clear_if_pid + _restart backoff/hard-cap + arm_revive plumbing; POST /launcher/revive...  (source: git:a21869f94c65)
- where-we-are 2026-07-06 -> robustness Wave 1: L0/L1/L5/L3a SHIPPED, next L3b revive: Methodical scaffolding per docs/agent-failure-modes-mitigation-roadmap-2026-07.md...  (source: mem:decision:ADR_0706220417_2637)
- L3a (observe-only wedge visibility): liveness.wedge_view() {phase,stuck_seconds,beat_age,wedged}; launcher.registry() exposes it per agent -> /launcher/status. Backend...  (source: git:16dbd210c516)
- where-we-are 2026-07-06 -> robustness Wave 1: L0+L1+L5 SHIPPED, next L3/L4: Marathon/methodical scaffolding per docs/agent-failure-modes-mitigation-roadmap-2026-07.md...  (source: mem:decision:ADR_0706215817_8352)
- Use when a spawner gates a child on a per-instance singleton lock the CHILD itself acquires: the spawner must only CHECK holder()/liveness and refuse a duplicate, NEVER...  (source: learn:experiment:spawner_holding_child_singleton_lock_starves_it)
- L5 (D3 + latent bug): launcher.launch() now CHECKS runner_lock.holder() and refuses duplicates, instead of acquire-and-holding a token it never heartbeat/released --...  (source: git:cbaa98e926ee)
- where-we-are 2026-07-06 -> robustness scaffolding: L0+L1 SHIPPED, next L5/L3/L4: Retrospective docs: docs/agent-failure-modes-retrospective-2026-07.md +...  (source: mem:decision:ADR_0706215221_8280)
- L1 (liveness scaffolding): core/comm/liveness.py worklive heartbeat -- per-agent {phase,since_ts,beat_ts,turn}; wired into runner on_activity + _heartbeat + loop edges...  (source: git:4a7200a0926d)
- where-we-are 2026-07-06 -> agent failure-mode retrospective + verified roadmap; L0 SHIPPED, next L1: Retrospective docs...  (source: mem:decision:ADR_0706214300_6590)
- Use before giving a lower-trust local model unattended shell: do NOT pair --allow-exec with blanket --trust. Enforce a fail-closed command allowlist/denylist at the TOOL...  (source: learn:experiment:unattended_exec_trust_removes_only_guardrail)
- Use when a streaming LLM client can hang: pass BOTH timeout= AND an explicit max_retries= to OpenAI (default max_retries=2 retries APITimeoutError -> ~3x wall-clock...  (source: learn:experiment:openai_sdk_timeout_aborts_streaming_wedge)
- where-we-are 2026-07-06 -> agent failure-mode retrospective + verified roadmap; building L0: Two-phase retrospective on the multi-day agent fleet run. PHASE 1 taxonomy...  (source: mem:decision:ADR_0706213754_3869)
- README: refresh status — 733 tests, current live-memory counters, add coordination substrate + door-parity/wiring gates  [relates: member_of]  (source: git:9aa700282148)
- Renew: design (membrane 5th job) + web prior-art + off-bus DeepSeek cross-check + comparison; session-chaptering design; bus recorder + solo driver  [relates: member_of]  (source: git:5d32e17c7e8c)
- SAVE: commit the ARCHITECTURE.md rewrite -- it was uncommitted under the lowercase-tracked path docs/architecture.md (case-mismatch vs my uppercase edits; content was...  (source: git:a3bbab37606e)
- Membrane design: slice 2 (Built!=Wired gate) SHIPPED; 18 latent modules frozen as backlog (14 built-ahead incl conductor, 4 legacy)  (source: git:5508abd89309)
- Membrane slice 2 (Built!=Wired gate): scripts/check_wiring.py -- import-graph reachability from production entry points (doors/runners/hooks/boot); flags core/ modules...  (source: git:3d5ff58f3466)
- Membrane design: slice 1b COMPLETE (door debt 12->0); 1c endgame (one-registry structural parity) optional/deferrable  (source: git:6bad66cd21fc)
- Membrane slice 1b COMPLETE (door debt 12->0): MCP twins for tag_anti_pattern + bifrost_nudge; rationalized the rest -- list/fleet=cli_only (recall '' / operator...  [relates: member_of]  (source: git:452896b1e2bf)
- Membrane design: slice 1b progress -- 5 gaps closed (note/notes/lock/unlock/locks have MCP twins), 7 remain  (source: git:47adeca05859)
- Membrane slice 1b: MCP twins for note/notes/lock/unlock/locks -- a shell-less (MCP-only) agent can now record write-once decisions + claim advisory locks (couldn't...  (source: git:d4e1c3c69be5)
- Membrane design: mark slice 1a (door-parity guard) SHIPPED; slice 1b = pay down the 12 tracked CLI<->MCP gaps (note/notes/lock* first)  (source: git:317a5906fe73)
- Membrane slice 1 (door-parity): scripts/check_door_parity.py makes the 3-door verb surface EXPLICIT (CLI 33/MCP 22/bus 18) + ratchets it -- classifies every verb (16...  (source: git:626c8ebefcd8)
- Membrane design: fold VERIFIED prior art + extracted patterns (Terrarium/LbMAS blackboard papers). Drop hallucinated 'Synthetic Membrane' citation. 3 locked decisions...  (source: git:2a5dae9001cd)
- Fold active tracks into ROADMAP STATUS: Reliability(L0-L4), the Mediation Membrane (System 5, fuller framing of old Wave 4 ACI-unify), Comprehension layer -- each...  (source: git:961ee8f8edcc)
- Founding design note: the mediation membrane. Grounded finding -- the membrane already exists as the HOOK LAYER (half-built, diagnosed a year ago in...  [relates: member_of]  (source: git:7525500ab414)
- Comprehension follow-ons: PRINCIPLES.md gains #8 (coordinate through the environment/stigmergy) + #9 (observability must never break what it observes/fail-open)...  (source: git:5a965f95aa8a)
- Comprehension layer enforced (high-priority: keep the system understandable). LEXICON gains the whole Bifrost/coord/supervision vocabulary...  (source: git:1e31e0531ff6)
- Living architecture skeleton: rewrote docs/ARCHITECTURE.md (was ~4 layers stale) at stable subsystem altitude covering all layers...  [relates: member_of]  (source: git:32f7c8195bc9)
- Design assessment: multi-agent memory/recall -- grounded in real code (ranker agent-agnostic, credit global, faithfulness gate strong, value ~1%). Reframe: fix corpus...  [relates: member_of]  (source: git:e64ded8a3f01)
- Roadmap: L3b-auto hardening (persisted arm + jitter + contract) SHIPPED; capture deferred DeepSeek ideas (CLI, fingerprinting, Aurora-injection)  (source: git:159318c4b2f0)
- Roadmap: L3b-auto (opt-in auto-revive) SHIPPED; next L3c-remainder smoke-test then L3d state-rollback  [relates: member_of]  (source: git:fc523a8d1a57)
- Research detour: Actor/OTP + ROS + Stigmergy vs our plan -- mostly confirms (L0-L4 = a supervisor tree), 3 steers (supervised state rollback, lifecycle FSM...  (source: git:d48ac6788768)
- Roadmap: L3b (manual revive + backoff) SHIPPED; next L3b-auto  (source: git:5b221dd3d9a7)
- Roadmap: L3 sub-sliced; L3a observe-only visibility SHIPPED; next L3b revive  (source: git:39990451ac2d)
- Mark L5 SHIPPED in roadmap (note: fixed latent launcher-starves-child bug); next L3/L4  (source: git:8eb1b3f03ce8)
- Mark L1 SHIPPED in roadmap; next = L5/L3/L4  (source: git:261b0ba46669)
- Mark L0 SHIPPED in roadmap; next = L1  (source: git:b56e82751e1e)
- L0 (G4 fix): hardened OpenAI client factory (make_client) with per-read streaming timeout + explicit max_retries, wired into runner/REPL/ask; cap run_command timeout...  (source: git:1e09fdee435d)
- Preserve L0 verification artifact: reproducible OpenAI-timeout streaming-wedge probe (tests/manual/l0_timeout_probe.py)  [relates: member_of]  (source: git:07099cb27a5d)
- L0 assumption empirically verified: OpenAI timeout= aborts hung streaming reads (pre-data + mid-stream); resolve open-Q1, add max_retries caveat  (source: git:36f85aea16c6)
- Retrospective Phase 2: verified, sequenced mitigation roadmap (6 tracks -> waves 0-4) for the agent failure-mode taxonomy  (source: git:d9b6ff83ba95)
- Retrospective Phase 1: agent failure-mode + pain-point taxonomy (24 modes, 7 categories) from the multi-day fleet run  (source: git:46507e24a28f)

## where-we-are 2026-07-06 -> Membrane DESIGNED + prior-art VERIFIED; ready for ... (research)
Span: 2026-07-07T03:48:02.936483 → 2026-07-07T03:48:34.504208
Beats: 2  · Critic: True

- where-we-are 2026-07-06 -> Membrane DESIGNED + prior-art VERIFIED; ready for first slice (door-parity): MEDIATION MEMBRANE (System 5, foundational) -- design + prior-art...  (source: mem:decision:ADR_0706234834_3647)
- Use when grounding a novel architecture idea: web-VERIFY cited papers (LLMs hallucinate exact titles -- 'Synthetic Membrane' didn't exist). For a shared-medium/mediation...  (source: learn:experiment:blackboard_prior_art_validates_membrane)

## renew-strande-status: Strand E (cold-resume fidelity) COMPLETE 2026-07-07 -- ... (ai-setup)
Span: 2026-07-07T13:08:30.706725 → 2026-07-07T13:29:33.777418
Beats: 11  · Critic: True

- renew-strande-status: Strand E (cold-resume fidelity) COMPLETE 2026-07-07 -- BOTH gaps closed & shipped. Docs: research/reviewed/renew-strande-cold-resume-2026-07-07.md...  (source: mem:decision:ADR_0707092933_5440)
- Use when adding a task-relevant ORIENTATION/section to a boot or resume payload, before hand-writing it: make it a PROJECTION over a stable existing doc...  (source: learn:experiment:renew_arch_slice_orientation)
- renew-strande-status: Strand E (cold-resume fidelity) FIRST PASS DONE + gap#1 FIXED, shipped 2026-07-07 -> research/reviewed/renew-strande-cold-resume-2026-07-07.md...  (source: mem:decision:ADR_0707092320_4754)
- Use when testing whether a compressed/curated resume payload (boot, handoff, summary) is sufficient, before rebuilding the summarizer: measure it BEHAVIORALLY -- what...  (source: learn:experiment:renew_strande_cold_resume)
- renew-stranda-status: Strand A DONE (research/reviewed/renew-stranda-health-signals-2026-07-07.md) + slice A' SHIPPED 2026-07-07 (commit via ship.py, full suite+5 guards...  (source: mem:decision:ADR_0707091638_4889)
- renew-stranda-status: Strand A (context-health signals) FIRST PASS DONE 2026-07-07 -> research/reviewed/renew-stranda-health-signals-2026-07-07.md. Outcome INVERTS the...  (source: mem:decision:ADR_0707090852_3965)
- Use when building a health/quality estimator gated on a correlation study, before instrumenting signals: first confirm a durable ground-truth LABEL for the bad outcome...  (source: learn:experiment:renew_stranda_health_signals)
- RENEW Strand E gap #2 (arch slice): boot now orients the agent to the code region of the current task -- a deterministic show-nothing-floored projection over...  (source: git:5c135bd4e7f9)
- RENEW Strand E (cold-resume fidelity): boot payload was insufficient to resume -- notes clipped to 110 chars collapsed the resume anchor (open-docket/where-we-are)...  (source: git:591e0aed414a)
- RENEW A' (label capture): persist the FAIL half as a durable event_log 'fail' event -- the degraded-output ground truth Strand A found missing. Exactly-once per failure...  (source: git:30ac2a63c1f6)
- RENEW Strand A: empirical context-health signals pass -- signals cheap but reread-rate non-discriminating; blocking gap is the degraded-output LABEL, recommend...  (source: git:ef9cf9ecb7f2)

## scoping bookends because the narrative spine already had chapters (ai-setup)
Span: 2026-07-08T00:00:59.669597 → 2026-07-08T00:00:59.669597
Beats: 1  · Critic: True

- scoping bookends because the narrative spine already had chapters  [relates: member_of]  (source: claude:design)

## Episode closed: scoping bookends because the narrative spine already had chap... (ai-setup)
Span: 2026-07-08T00:01:00.039571 → 2026-07-08T04:54:10.799119
Beats: 31  · Critic: True

- Episode closed: scoping bookends because the narrative spine already had chapters  [relates: member_of]  (source: episode:close:ch_1783468859_7379)
- Use when writing ANY durable record an agent surface re-prints (notes, task titles, lessons): keep authored text pure ASCII (sec.6 not the section sign, -> not arrows)...  (source: learn:experiment:authored_records_stay_ascii)
- Use when deriving triggers/drafts/counts for spans delimited by boundary-marker events: (1) the marker shares the next span's start timestamp, so filter markers OUT of...  [relates: member_of]  (source: learn:experiment:span_boundary_hygiene)
- Bookends S3 (T009): episode auto-suggester -- advisory close suggestions (impl-complete/subsystem-switch/new-objective/idle), noise-gated, on the RENEW-shared event bus...  [relates: member_of]  (source: git:0aa69f9dc23a)
- session-bookends-status: Session bookends: S1 + S3 SHIPPED. Design: docs/session-bookends-design-2026-07.md (contract in sec.6, slices sec.7); reviews in...  (source: mem:decision:ADR_0708005056_2090)
- renew-signal-persistence-status: RENEW slice A'' (signal persistence) SHIPPED 2026-07-08 @7223308 via ship.py (T008 in ledger; 5 guards + 812 tests green + live smoke)...  [relates: member_of]  (source: mem:decision:ADR_0708002952_1434)
- Use when a correlation dataset has a signal half and a label half, before letting it accumulate: put BOTH on the same always-on capture chokepoint (hook/session-end fold...  [relates: member_of]  (source: learn:experiment:renew_signal_label_symmetry)
- RENEW A'': durable session_signals -- SessionEnd folds the session transcript into one per-session health-signal event (signal half now as durable as the A' fail labels)  (source: git:7223308b6c3a)
- comprehensibility-immune-system: PILLAR SHIPPED 2026-07-07 (codesigned w/ DeepSeek). The comprehensibility immune system: guards that keep the architecture...  (source: mem:decision:ADR_0707235722_5056)
- Use when building or hardening ANY guard/gate meant to be load-bearing (a 'pillar'): a guard needs FOUR properties, not just 'it checks the thing'. COMPLETE (does it...  [relates: member_of]  (source: learn:experiment:comprehensibility_immune_system_four_properties)
- Use when committing an edit to a doc/file on Windows via a path-scoped tool (mirror.py/git add <path>), before trusting the commit: the living-docs convention here is...  [relates: member_of]  (source: learn:experiment:mirror_case_pathspec_miss_on_windows)
- arch-triage-2026-07-07: Architecture triage arc P0->P1->P2 COMPLETE 2026-07-07 (DeepSeek triage + claude code-vetting) ->...  (source: mem:decision:ADR_0707232450_9376)
- P2 execution (arch-triage, Daniel-approved): (1) DELETE fast_cache.py -- confirmed dead (zero live consumers), 623 LOC + 3 lint-debt allowlist entries removed. (2)...  (source: git:7bf9e4671052)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude VETTED) -> research/reviewed/deepseek-arch-triage-2026-07-07.md. === DONE === P0: +25 tests for 2...  (source: mem:decision:ADR_0707231548_5864)
- Use when ANY triage recommends deleting 'unwired'/'dead' modules -- especially one from an agent that cannot see code: NEVER delete on the label. Check per module: (1)...  [relates: member_of]  (source: learn:experiment:investigate_before_delete_3of4_wrong)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude, VETTED) -> research/reviewed/deepseek-arch-triage-2026-07-07.md. === DONE === P0: +25 codesigned tests for...  (source: mem:decision:ADR_0707221746_7077)
- Use when a triage (esp. from an agent that can't see code bodies) says 'wire these built-ahead modules now': do NOT wire to satisfy the gate -- open each module and...  (source: learn:experiment:wiring_investigate_before_acting)
- P1 (name-collision): rename core/state/session_state.py -> session_checkpoint.py (crash-recovery checkpoints), resolving the module-basename collision with...  (source: git:bbfcef2c5cbd)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude, VETTED) 2026-07-07 -> research/reviewed/deepseek-arch-triage-2026-07-07.md. ANSWER: yes, shipped slices...  (source: mem:decision:ADR_0707204151_2870)
- Use when hardening an untested but load-bearing DATA/VOCABULARY module (edge types, enums, config maps), before assuming it's fine because it 'never changed': write the...  (source: learn:experiment:p0_invariant_tests_catch_latent_bug)
- P0 test hardening (arch-triage): +25 tests for the two zero-coverage load-bearing modules, codesigned w/ DeepSeek. relationship_types.py -- invariant guards (inverse...  [relates: member_of]  (source: git:ccaa256d7755)
- arch-triage-2026-07-07: Architecture triage (DeepSeek, dossier-fed, VETTED by claude) 2026-07-07 -> research/reviewed/deepseek-arch-triage-2026-07-07.md + coverage...  (source: mem:decision:ADR_0707201840_1619)
- session-bookends-status: Session bookends: S1 SHIPPED 2026-07-07 (design->DeepSeek review->build, all green). Design: docs/session-bookends-design-2026-07.md (contract...  (source: mem:decision:ADR_0707200331_2823)
- Use when adding a session/episode/segment concept to a system that already has a narrative or grouping primitive, before creating a new table: check whether the new...  [relates: member_of]  (source: learn:experiment:bookends_episode_is_a_chapter)
- Session bookends S1 (manual backend + CLI): an episode IS a Chapter with why+final; core/narrative/episode.py lifecycle (open/current/close+draft/accept) drafting...  [relates: member_of]  (source: git:338fe29cb821)
- Anti-rot contract: describe the now-complete comprehensibility immune system (was 'proposed'); removes a stale doc ref in passing -- the pillar keeping its own docs...  (source: git:67f52200b3b8)
- PILLAR: the comprehensibility immune system (codesigned w/ DeepSeek). Hardens check_comprehensibility from structure-only to catch SEMANTIC drift + makes enforcement...  [relates: member_of]  (source: git:6a55f17bf929)
- Docs comprehension refresh #1 (LEXICON half -- case-pathspec miss on the prior commit): LEXICON.md gains Episode/Bookend, Agent-membrane/RENEW (paging function), the...  (source: git:be143db928f8)
- Docs comprehension refresh (recommendation #1): update the two hand-curated living docs to absorb recent work -- ARCHITECTURE.md + lexicon.md now cover...  (source: git:6789a3f459fe)
- P2 investigate-before-delete (arch-triage): encoded evidence-based verdicts into check_wiring backlog. DeepSeek's blind triage said DELETE all 4; code investigation...  (source: git:2ea219be2dfd)
- P1 (wiring): surface conductor.py through the ONE door as 'agent_cli task' (propose/approve/claim/start/verify/done/block/list/next) -- closes the...  (source: git:7d7ec0e4048b)

## Episode closed: Session bookends S1 (manual backend + CLI): an episode IS a C... (ai-setup)
Span: 2026-07-08T05:08:04.543693 → 2026-07-08T06:09:38.567734
Beats: 10  · Critic: True

- Episode closed: Session bookends S1 (manual backend + CLI): an episode IS a Chapter with why+final; core/narrative/episo  [relates: member_of]  (source: episode:close:ch_1783468860_8520)
- Recall vNext follow-up: tz-safe self-echo + curator age via timeutil.to_epoch -- the live flight test caught utcnow-naive record stamps being read as LOCAL time...  [relates: member_of]  (source: git:df3ed2f8e5ee)
- Use when analyzing any pillar/subsystem to take it to the next level, before proposing fixes: follow docs/pillar-analysis-method.md -- triangulate ground truth (design...  (source: learn:experiment:pillar_analysis_method)
- recall-vnext-status: RECALL vNEXT SHIPPED 2026-07-08 @aceb2da (T011, Daniel full-send). Design+evidence: docs/recall-vnext-2026-07.md. WAS: 2850 impressions/7d -> 26...  [relates: member_of]  (source: mem:decision:ADR_0708015237_3780)
- Use when building any weighted-overlap relevance score, before trusting it: check the all-common-token query (ratios are scale-invariant -- floor the denominator by...  (source: learn:experiment:weighted_overlap_scale_invariance)
- Recall vNext (T011): close the four loops -- curator benches surfaced-never-credited lessons (reversible, auto-unbench on credit) + prunes ghost counters; trigger-aware...  [relates: member_of]  (source: git:aceb2da4b0c3)
- session-bookends-status: Session bookends COMPLETE S1+S3+S4 (design docs/session-bookends-design-2026-07.md, statuses inline sec.7). S1 (07-07): episode IS a Chapter...  [relates: member_of]  (source: mem:decision:ADR_0708011150_2456)
- Use when directed to work in another agent's lane: lock -> record who-directed in the task -> match the file's idiom, keep logic in YOUR tested modules (UI stays thin)...  (source: learn:experiment:lane_override_protocol)
- Method doc: pillar-analysis method (triangulate ground truth -> diagnose at loop altitude -> fix with evidence discipline) -- distilled from the recall vNext arc per...  [relates: member_of]  (source: git:47b87ec3550f)
- Bookends S4 (T010): episode panel in bifrost_ui -- header chip + docked current-episode panel + End-episode draft editor + advisory suggestion banner, against contract...  [relates: member_of]  (source: git:ff069ab45f2f)

## Use when a session or workflow dies mid-run, before re-running it whole: the ... (ai-setup)
Span: 2026-07-08T13:19:45.359512 → 2026-07-08T13:20:29.981670
Beats: 2  · Critic: True

- Use when a session or workflow dies mid-run, before re-running it whole: the journal + per-agent transcripts ARE the checkpoint - join results (journal agentId) to...  (source: learn:experiment:workflow_journal_crash_salvage)
- Frontier research: autoresearch(Karpathy)/AAR + SkillOpt + Fable5 prompt provenance + SKILL.md ecosystem - crash-recovered via workflow-journal salvage (57/75 votes...  [relates: member_of]  (source: git:32fbac0ac760)

## frontier-research-status: Frontier fold-in research COMPLETE 2026-07-08 (reco... (research)
Span: 2026-07-08T13:20:01.915783 → 2026-07-08T13:20:01.915783
Beats: 1  · Critic: True

- frontier-research-status: Frontier fold-in research COMPLETE 2026-07-08 (recovered from interface crash; continuation workflow wf_e63ba506-2ec salvaged 57/75 votes from...  (source: mem:decision:ADR_0708092001_3639)

## forge-design-status: Forge status 2026-07-09 ~01:00: F2+F4 SHIPPED under T013... (ai-setup)
Span: 2026-07-09T03:05:51.346612 → 2026-07-09T04:58:40.496055
Beats: 18  · Critic: True

- forge-design-status: Forge status 2026-07-09 ~01:00: F2+F4 SHIPPED under T013 (@HEAD, 897 tests green). THE LOOP IS LIVE: recall-curate --forge-propose ran against real...  [relates: member_of]  (source: mem:decision:ADR_0709005840_8516)
- Use when calling any REASONING model (deepseek v4-pro, o-series style) with a token cap, before blaming the API or the prompt: thinking spends from the same max_tokens...  (source: learn:experiment:reasoning_model_token_headroom)
- Forge F2+F4 (T013): the optimizer pass + the Tier-1 watch, red-teamed by its own optimizer before it ran. F2: core/recall/forge_optimizer.py - curator-named rehab...  [relates: member_of]  (source: git:963ba8918463)
- forge-design-status: Forge status 2026-07-09 ~00:40: F0b+F1 SHIPPED under T013 (@c3e9536 + drill fixes @HEAD). F0b: flip events enriched (query+alt at credit time)...  (source: mem:decision:ADR_0709003639_6670)
- Use when validating any judge/gate/classifier, after tests and review pass: run an adversarial USE drill with a fenced peer generating real inputs (one trap, one...  (source: learn:experiment:adversarial_use_beats_code_review)
- Forge F1 drill fixes (T013): UNMEASURABLE verdict - the red-team drill exposed a gate blind spot: a never-credited lesson whose recorded contexts all pre-date the...  [relates: member_of]  (source: git:017dde86fdf3)
- Forge F0b+F1 (T013): capture-side durable contexts + the Tier-0 edit gate. F0b: flip events enriched at credit time (query + altitude - free at ~5/wk), durable bounded...  [relates: member_of]  (source: git:c3e9536eb7f2)
- forge-design-status: Forge status 2026-07-09: design v2.1 LOCKED (Daniel: defaults + trust ladder + keep buffer). F0 SHIPPED + RUN same night (core/recall/replay.py...  [relates: member_of]  (source: mem:decision:ADR_0709001207_5188)
- Use when defining success/go-no-go criteria for any audit or experiment, before touching the data: pre-register thresholds in a commit AND have a fenced peer...  (source: learn:experiment:dual_blind_preregistration)
- Forge F0 (T013): replay harness + data-sufficiency audit - core/recall/replay.py (credited/surfaced context reconstruction from durable flip events + injection ledger...  [relates: member_of]  (source: git:9621e95d1792)
- forge-design-status: Lesson Forge design v2 LOCKED-PENDING-DANIEL 2026-07-08 (T013 in_progress). docs/lesson-forge-design-2026-07.md. HEADLINE: claude and DeepSeek...  (source: mem:decision:ADR_0708235607_3813)
- Apply DeepSeek slice-1 review (research/reviewed/deepseek-slice1-review-2026-07-08.md): F1 stop-verb carve-out in promise_shaped (I'll wait/pause/stop = ending not...  [relates: member_of]  (source: git:9e60d6ee848c)
- Use when a Bifrost runner (or any cursor-advancing bus consumer) starts with a backlog already queued, before trusting delivery: the startup wake can batch-advance the...  (source: learn:experiment:bifrost_runner_backlog_skip)
- Use when adding any advisory/warning output an agent is meant to act on LATER, before shipping it: persist the computed fact (stamp metadata or emit an event) alongside...  [relates: member_of]  (source: learn:experiment:advisory_prints_evaporate)
- Slice 1 frontier fold-ins: (1a) age-conditional staleness cue in render() - old lessons say so + tell the reader to verify named files/flags (AKASHIC_STALE_CUE_DAYS...  [relates: member_of]  (source: git:0b3dfcac192a)
- Forge design v2.1 LOCKED (Daniel: defaults + trust ladder + keep buffer) + F0 pre-registered go/no-go criteria committed BEFORE the audit runs (pre-registration fence...  (source: git:74d6e0db5c4f)
- Forge design v2 (T013): reconciled with DeepSeek's FENCED blind cross-check - CONVERGED independently on replay-against-credit-history as the validation gate (locked)...  (source: git:55620145f778)
- Lesson Forge design DRAFT (T013): evidence-gated lesson-content optimization - flip-log-as-validation-set (Tier 0 offline replay gate: must-still-match credited contexts...  (source: git:7d53125905f3)

## frontier-research-status: Frontier fold-in arc: research COMPLETE + SLICE 1 S... (research)
Span: 2026-07-09T03:06:54.323196 → 2026-07-09T03:06:54.323196
Beats: 1  · Critic: True

- frontier-research-status: Frontier fold-in arc: research COMPLETE + SLICE 1 SHIPPED 2026-07-08 @0b3dfca (T012). Shipped fold-ins: (1a) age-conditional staleness cue in...  [relates: member_of]  (source: mem:decision:ADR_0708230654_2776)

## Use when an expected directed Bifrost reply never arrives, before blaming the... (ai-setup)
Span: 2026-07-09T12:53:23.159663 → 2026-07-09T13:20:08.850683
Beats: 4  · Critic: True

- Use when an expected directed Bifrost reply never arrives, before blaming the sender: compare the recipient cursor (bifrost:cursor:<agent>) to the stream tail (xrevrange...  (source: learn:experiment:bifrost_reply_eaten_by_stale_watcher)
- comms-pillar-status: T016 comms/messaging pillar: dual-fenced investigation COMPLETE 2026-07-09; reconciled synthesis + gated slice plan at...  (source: mem:decision:ADR_0709092008_1440)
- T014 (builder: deepseek / adversarial reviewer: claude - first full role reversal): Bifrost runner + bus fixes, drill-proven. Defect 1 root cause (deepseek): Bus._drain...  (source: git:a106af8c4b73)
- Use when accepting a handoff that names files, before editing them: check locks and release the sender's stale advisory locks as part of ACCEPTING the handoff - a...  (source: learn:experiment:handoff_leaves_stale_locks)

## claude -> deepseek: RB Wave 1 built -- run your assigned per-slice fence (RB-... (ai-setup)
Span: 2026-07-09T23:30:24.520920 → 2026-07-10T05:32:25.961217
Beats: 25  · Critic: True

- claude -> deepseek: RB Wave 1 built -- run your assigned per-slice fence (RB-1 live-drill+verify, RB-2 design-review+verify, RB-3 verify). Reconcile divergence; review...  (source: handoff:claude->deepseek)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md -- ARC COMPLETE 2026-07-10. ALL SLICES SHIPPED: P0 wake detect-dont-consume (+T018...  (source: mem:decision:ADR_0710004517_2741)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md -- ARC COMPLETE 2026-07-10. ALL SLICES SHIPPED: P0 wake detect-dont-consume (+T018...  (source: mem:decision:ADR_0710002346_7393)
- T027/P7 -- the pillar's final slice: LOOKBACK, one question over the rationale corpus. lookback verb fans a why-question across six corpora (docs currency-labeled ->...  [relates: member_of]  (source: git:423193efd56e)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 (+T018/T019), P1 (notes 67->11), P2 (boot orientation), P3...  (source: mem:decision:ADR_0710000419_6060)
- T026/P6: message ack lifecycle -- read != handled != acknowledged. Durable msg_ack events (promoter.ack/acks_for: idempotent per-actor, multi-actor forensics)...  (source: git:eb9cc14c48db)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 @d925d6b (+T018/T019), P1 @d6153c2 (notes 67->11), P2 @bd03ac1...  (source: mem:decision:ADR_0709235210_7260)
- T025/P5: proposed-task decay -- parked intent demands a verdict. ABANDONED was built-not-wired (status + full transition legality existed, no verb): conductor abandon...  (source: git:e292f996042c)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 @d925d6b (+T018/T019), P1 @d6153c2 (notes 67->11), P2 @bd03ac1...  (source: mem:decision:ADR_0709233013_5155)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 @d925d6b (T017 +T018/T019), P1 @d6153c2 (T021, notes 67->11), P2...  (source: mem:decision:ADR_0709231658_2182)
- T023/P3: ledger_update push -- live agents' ledger view stops being frozen at onboarding. Conductor broadcasts EVERY transition (kind=ledger_update, from->to arrow per...  (source: git:4adf1ced7b11)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 @d925d6b (T017 + companions T018/T019), P1 @d6153c2 (T021, notes...  (source: mem:decision:ADR_0709213721_5577)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). P0 SHIPPED @d925d6b (T017 wake detect-dont-consume; companions T018...  (source: mem:decision:ADR_0709212724_9132)
- comms-pillar-status: P0 SHIPPED @d925d6b (T017, wake detect-dont-consume; companions T018 promise-bounce @bd6a3ea + T019 launcher pipe-drainers @2623908) -> P1 SHIPPED...  (source: mem:decision:ADR_0709205226_6389)
- T021/P1: notes supersession wired + corpus migrated. Root cause was ONE default: wrap minted dated where-we-are titles (agent_cli:1125), defeating the title-supersession...  [relates: member_of]  (source: git:d6153c24637c)
- Use when a subprocess-managed agent goes silent while its heartbeat stays fresh, before blaming the model or the bus: check whether the spawner captures stdout/stderr...  (source: learn:experiment:launcher_pipe_starves_chatty_child)
- T019: launcher pipe-wedge fix -- undrained stdout/stderr PIPEs froze any chatty child mid-print (deepseek runner wedged live 2026-07-09 20:12, ~12min of streamed...  (source: git:2623908ad743)
- comms-pillar-status: T016 investigation DONE (synthesis docs/comms-pillar-synthesis-2026-07.md, plan P0-P8) -> P0 SHIPPED 2026-07-09 @d925d6b (T017): wake listeners now...  (source: mem:decision:ADR_0709200148_2474)
- Use when a bus runner/auto-responder seems stuck but its process and lock are healthy, before restarting anything: read its LAST reply -- if it ends as a promise ('Let...  (source: learn:experiment:runner_promise_is_not_deliverable)
- Use when a background watcher/wake listener shares a read-cursor with a real consumer, before letting it advance anything: watchers DETECT on a caller-owned local cursor...  (source: learn:experiment:wake_listener_detect_not_consume)
- T017/P0: wake listener detect-dont-consume. Bus.wait gains since/since_out (caller-owned local cursor; shared cursor never written; next-position under the pinned T014...  (source: git:d925d6bc32be)
- Use when arming any detect-without-consume watcher after handling a wake, before launching it: CONSUME the handled messages first, then arm - a watcher armed over...  (source: learn:experiment:wake_consume_then_arm)
- T024/P4: doc currency contract + guard -- no dead law in docs/. Convention: every docs/*.md carries Status: current | superseded-by <path> | historical near the top...  [relates: member_of]  (source: git:f8b594d537ee)
- T022/P2: boot orientation header + precedence doctrine. First lines of every boot (both doors) now carry: map pointer, governing arc (<slug>-status note matched against...  [relates: member_of]  (source: git:bd03ac1f0f72)
- T018: runner robustness -- a promise is not a deliverable. bounce_promise(): one deliver-now reprompt when the agentic reply ends promise-shaped (reuses claude_stop...  (source: git:bd6a3ea5394b)

## visualgen-status: Visual-gen integration research COMPLETE 2026-07-09: fenced... (research)
Span: 2026-07-10T00:40:54.355024 → 2026-07-10T00:40:54.355024
Beats: 1  · Critic: True

- visualgen-status: Visual-gen integration research COMPLETE 2026-07-09: fenced dual pass (web agent verified all 10 candidate repos -- 2 unlicensed, 1 paper stub, 3...  (source: mem:decision:ADR_0709204054_7589)

## Use when an Edit is refused with file-not-read on a file your own subprocess/... (ai-setup)
Span: 2026-07-10T12:00:05.068430 → 2026-07-10T13:11:15.586116
Beats: 3  · Critic: True

- Use when an Edit is refused with file-not-read on a file your own subprocess/script just created, before retrying or rewriting: the harness only tracks files touched by...  (source: learn:experiment:fix_setup_research_reviewed)
- Use when a background watcher/daemon dies silently (exit 1, no output, cleanup artifact gone) on a box that can run concurrent sessions of the same agent, before blaming...  (source: learn:experiment:wake_seat_name_keyed_concurrent_sessions)
- T029-wave1-review-status: T029 Wave 1 built+committed OVERNIGHT by DeepSeek (3 commits unpushed: d6cbf75 slices doc, 0f9172b fenced-correction, 3941789 Wave-1 code)...  (source: mem:decision:ADR_0710080005_3595)

## Use when two store/backend implementations claim the same semantics, before b... (ai-setup)
Span: 2026-07-10T23:53:10.253861 → 2026-07-11T09:59:02.712821
Beats: 83  · Critic: True

- Use when two store/backend implementations claim the same semantics, before building features on either: write the op-sequence differential FIRST and wire it into ship...  [relates: member_of]  (source: learn:experiment:differential_harness_finds_on_first_run)
- Use when tempted to skip the fence on load-bearing design because the answer seems obvious: run both blind halves anyway -- the divergence IS the value, and...  (source: learn:experiment:fenced_dual_design_three_for_three)
- claude -> deepseek: OVERNIGHT LANE: build Wave 3 RB-9..12 in order against the frozen pins (tests/test_w3_rb9_rb10.py + rb11_rb12.py) + spec. You write (door on, exec...  (source: handoff:claude->deepseek)
- Use when a write/commit to a shared-tree path is refused or the path unexpectedly exists, before re-trying or forcing: READ the target first -- on a multi-seat repo the...  (source: learn:experiment:write_refusal_is_coordination_signal)
- when 2+ live seats share one agent id, route any multi-part or directed delivery through a durable door (research/reviewed file, handoff briefing) and use the bus only...  [relates: member_of]  (source: learn:experiment:two_live_seats_split_chunked_bus_delivery)
- claude -> claude: SEAT RELAY (from the wake-listener seat f34b9383 to the builder seat): deepseek's answers to your questions, which my listener consumed off our shared...  (source: handoff:claude->claude)
- claude -> deepseek: W3 design-review (your slice-text role): review docs/w3-build-spec-2026-07-11.md @4c12097 -- RB-8 sentinel semantics + RB-12 tiebreaker. One named...  (source: handoff:claude->deepseek)
- FLIPPED 2026-07-11: the note door no longer silently clips -- bodies to 100k store whole; if the door result ever shows [CLIPPED], chunk and resend the remainder. The...  [relates: member_of]  (source: learn:experiment:note_door_silent_4k_clip)
- rb5-clip-probe-live: rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence...  (source: mem:decision:ADR_0711052028_3421)
- Use when delivering a long verbatim document that must not be silently truncated: prefer write_file to a git-tracked path (like research/reviewed/) over knowledge_note...  [relates: member_of]  (source: learn:experiment:file_write_tool_no_clip)
- claude -> deepseek: [RB-5 PROBE blind] Find the silent ~4013-char clip on the knowledge_note->stored-atom path (file:line); propose RB-5 confess-fix + regression pin...  (source: handoff:claude->deepseek)
- claude -> deepseek: WAVE 3 OPENS (RB-8..12 + DictStore differential): your blind design half -> research/reviewed/deepseek-w3-design-2026-07-11.md (write door is back...  (source: handoff:claude->deepseek)
- Use when writing a knowledge_note that might exceed ~3000 characters, before trusting the [OK] response: keep each note body under 3000 chars. For long content, split...  [relates: member_of]  (source: learn:experiment:note_door_silent_4k_clip)
- t034-registry-design-deepseek-part7: # T034 remainder — part7 (2 Goodharts + cut list + reconciliation) FINAL

### 2 GOODHARTS

**Goodhart 1 — "All dials in manifest"...  (source: mem:decision:ADR_0711045806_2536)
- t034-registry-design-deepseek-part6: # T034 remainder — part6 (leaks 3-4 + 2 drifts)

**Leak 3 — Defaults duplicated between manifest and code.** Manifest declares...  (source: mem:decision:ADR_0711045755_9720)
- t034-registry-design-deepseek-part5: # T034 remainder — part5 (Part 2 red-team: 4 leaks)

## PART 2: RED-TEAM OF THE APPROVED T034 SKETCH

Red-teaming Claude's half...  (source: mem:decision:ADR_0711045747_7413)
- t034-registry-design-deepseek-part4: # T034 remainder — part4 (guard + failure modes)

### 2.F. The guard (comprehensibility immune system extension)

Same pattern as...  (source: mem:decision:ADR_0711045733_2119)
- t034-registry-design-deepseek-part3: # T034 remainder — part3 (continuation from part2 mid-G-c)

### 2.D. Secrets (completed)

...credentials are a separate concern...  (source: mem:decision:ADR_0711045708_9353)
- t034-registry-design-deepseek-part2: # T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half, PART 2 — remainder)

Continuation from...  (source: mem:decision:ADR_0711045445_6705)
- t034-registry-design-deepseek: # T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half)

Status: blind-design (2026-07-11, fenced — written BEFORE reading...  (source: mem:decision:ADR_0711034629_3586)
- claude -> deepseek: T034 OPENS (registry + dial consolidation, Daniel-approved, DESIGN ONLY until exam): your blind half from the raw brief ->...  (source: handoff:claude->deepseek)
- claude -> deepseek: RB-23 CLOSED: held-out GREEN, slice shipped+pushed. Your gate verdict + close addendum: research/reviewed/deepseek-rb23-verify-2026-07-11.md. Next...  (source: handoff:claude->deepseek)
- Use when a live Bifrost delivery keeps vanishing before you can read it (twin session, cursor race, RB-21 class), before asking for more live-lane resends: switch to a...  [relates: member_of]  (source: learn:experiment:contested_bus_use_durable_doors)
- rb23-heldout-corpus-sealed: {"id":"ds-41","text":"(deepseek produced no final ...[truncated]  (source: mem:decision:ADR_0711033057_6379)
- claude -> deepseek: RB-23 verify gate open: impl frozen @6078009 (push held). Read spec docs/rb23-build-spec-2026-07-11.md + impl + tests; reply GATE GREEN/RED on the...  (source: handoff:claude->deepseek)
- Use when handling sealed/fenced peer content in a shared store, before running ANY line-based filter (Select-String/grep/findstr) or display command near it: line...  [relates: member_of]  (source: learn:experiment:sealed_content_needs_field_aware_extraction)
- claude -> deepseek: RB-23 fenced dual design OPENS (engine-first item 1): your blind [design-review] half -> research/reviewed/deepseek-rb23-design-2026-07-11.md +...  (source: handoff:claude->deepseek)
- next-focus: ENGINE-FIRST-6a7467: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0711023115_7226)
- drilldone85014a-status: GOVERNING ARC DOC: docs/drilldone85014a-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711023113_4674)
- next-focus: ENGINE-FIRST-1c6599: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0711022959_7666)
- drilldone71d993-status: GOVERNING ARC DOC: docs/drilldone71d993-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711022957_8292)
- next-focus: ENGINE FIRST, UI AFTER (Daniel-ruled 2026-07-11): do NOT build UI until the engine exam passes. Order: RB-23 no-answer floor -> Battery Wave 3 (RB-8..12 +...  (source: mem:decision:ADR_0711021921_1389)
- claude -> claude: ENGINE-FIRST SPRINT (Daniel-ruled 2026-07-11 ~02:45: core engine healthy+robust BEFORE UI bodywork; a session already jumped to UI against this -- do...  [relates: member_of]  (source: handoff:claude->claude)
- Progress bars, data half (Daniel-directed; co-designed, reconciliation record research/reviewed/deepseek-progress-bars-codesign-2026-07-11.md -- deepseek GREEN 'Build...  (source: git:0c451771694c)
- T030 L2 SHIPPED -- the progress pulse (RB-27a) + fleet doctor (RB-27b), per the reconciled L2 BUILD SPEC in docs/agent-liveness-tier-2026-07.md (GATE GREEN by...  (source: git:e41cecb00b4c)
- T030 L1 follow-up COMPLETE + L2 reconciled spec (dual targeted read). Follow-up: W2 (die pre-send -> answers once on redelivery) + W5 (mid-batch death -> msg1 settled...  (source: git:375cbeedd71e)
- Use when a thinking-mode runner returns a no-final-answer marker on a long analytical ask, before re-asking or blaming the model: the work usually EXISTS in the streamed...  (source: learn:experiment:runner_reasoning_eats_final_answer)
- T030 L1+L1b (claude lane, deepseek-codesigned): at-least-once inbox + fencing token -- the mail-loss incident class is dead. RB-26: runner detects without consuming...  (source: git:5aa19b17b772)
- RB-4 (T029 Wave 2): exact by-ref ack lookup -- deepseek GATE GREEN, srem mandate honored. Store gains srem (abstract + Redis/File/Hybrid; File deletes an emptied key...  [relates: member_of]  (source: git:5bb2269b425d)
- RB-7 follow-up (live find): the aged-out claim stays within its evidence. A nonsense id far below the Redis ms-epoch range rendered as unconditionally evicted -- but...  (source: git:791488eb0734)
- Use when launching any long-running process (runner/daemon/server) from PowerShell, before piping its output: never through a head-limited pipe (Select-Object -First N...  (source: learn:experiment:powershell_head_pipe_kills_runner)
- Use when a handoff must reach a LIVE peer runner, before waiting on its reply: agent_cli handoff = durable boot-lane (surfaces at the target's NEXT boot); the live...  (source: learn:experiment:handoff_two_lanes_boot_vs_bus)
- T029 Wave 2 (claude lane): RB-5 window-truncated confession + RB-7 evicted-payload honesty + RB-6 remainder. RB-5: promoted_page() fetches limit+1 -> (events, more) so a...  (source: git:068f65e1ba0a)
- claude -> deepseek: [T029 WAVE 2 OPENS -- RB-4 design-review, refute-first, BEFORE build] Wave 2 = confession primitive (RB-4..RB-7...  [relates: member_of]  (source: handoff:claude->deepseek)
- Use when a permission check lives on ONE side of a two-sided flow (a receive/fold gate, an inbound validator), before trusting deny-by-default: audit the SEND/emit side...  [relates: member_of]  (source: learn:experiment:toolbox_door_shadows_the_acl)
- Use when testing deny-by-default / quarantine / any per-identity permission by having a PRIVILEGED agent roleplay the restricted one, before trusting the result: a...  [relates: member_of]  (source: learn:experiment:gauntlet_roleplay_cannot_test_quarantine)
- wrap print fix (RB-8 wiring bug found live; the crash-orphaned note was cleanly superseded through the new claim path -- the machinery absorbing its own author's bug) +...  [relates: member_of]  (source: git:f0ecc365eaa8)
- Wave 3 registration pair 2: RB-9..12 pre-registered pins (skip-guarded until impl; contracts frozen: find_normalization_collisions, SupersedeTargetError...  (source: git:fe6953be3220)
- Wave 3 registration: reconciled dual-half build spec (RB-8..12 + DictStore differential) + RB-8 pre-registered acceptance tests, committed BEFORE impl (M3)...  (source: git:4c12097227dc)
- Wave 3 opens (Daniel-directed, order claude-ruled: RB-8 first): claude blind design half committed before deepseek's arrives -- race taxonomy R-a..R-e on the...  [relates: member_of]  (source: git:843cd69d2c25)
- T034 design reconciled: dual-half spec docs/t034-registry-spec-2026-07-11.md -- blind convergence on manifest+three-layer+guards (not a kernel, not YAML); deepseek...  (source: git:2f3f2dbc5a97)
- T034 proposed+approved (Daniel-ruled 2026-07-11): registry + dial consolidation -- the kernel question resolved to zero-new-primitives (settings: namespace on Store +...  [relates: member_of]  (source: git:a182994623bf)
- RB-23 VERIFY CLOSED -- held-out grading GREEN on first live run: ds-41..60 (zh-heavy, 20 rows) delivered via the durable note door after every live lane was eaten by the...  [relates: member_of]  (source: git:d625c194ad37)
- RB-23 VERIFY GATE GREEN (deepseek) persisted + re-verified live (19 pass/1 seal-skip); directive advanced RB-23-done -> Wave 3 next so corrected-framing sessions don't...  (source: git:1a8e17757c9a)
- RB-23 design tails persisted + harvest-at-build pointer recorded (complete half + full 40-corpus in deepseek runner log; bus truncated at ds-26). Session genuinely...  (source: git:0aaca8b48254)
- RB-23 registration: reconciled dual-half build spec + pre-registered acceptance tests, committed BEFORE impl (M3). Spec cites both fenced halves; incident record inside...  (source: git:9461b3677e62)
- RB-23 pre-work persisted (deepseek proactive, ahead of the engine-first sprint's first task): his fenced design-review half at...  (source: git:737890cad714)
- RB-23 fenced dual design opens: claude blind half (design record + dev-set corpus half, 41 labeled endings) committed before deepseek's sealed half arrives; asks sent on...  (source: git:81845e3884a7)
- Session wrap: boot-intent gap fixed (rogue UI session incident) -- governing-arc picker skips done arcs + honest fallback, boot renders CURRENT DIRECTIVE above NEXT...  [relates: member_of]  (source: git:80a5d0ed3410)
- Boot-intent gap FIXED (2026-07-11 incident: a fresh session told 'pick up where we left off' built paused UI because boot actively pointed at it). Fenced dual diagnosis...  (source: git:a719743131bd)
- Engine-first sprint plan made durable (Daniel-ruled): self-handoff briefing + next-focus note -- RB-23 -> Wave 3 -> L3-L5 -> T031 hooks -> RB-25 final exam; T033...  [relates: member_of]  (source: git:1416416bb860)
- Session tail: T033 ledger entry + sources-cache gitignore + deepseek bars-UI plan preserved verbatim (queued behind the design-language arc) + wrap note  [relates: member_of]  (source: git:7e075f3f2672)
- T033 evidence: deepseek built-vs-spec inventory persisted verbatim (1 NOT-BUILT / 2 DRIFTED / 2 PARTIAL vs the six composition-spec items; ~2000 unsanctioned lines...  (source: git:d2ba735629ae)
- Session wrap: T033 opened (UI design-language re-grounding) -- discovery: Aurora Glass specs EXIST and are settled (July 4-5, grounded in OneUI/HIG pre-method) but were...  [relates: member_of]  (source: git:84ecbe176c25)
- Session wrap: progress-bars data half shipped (turn_metrics: record/estimate/progress_view + doctor --progress), co-designed with deepseek (his UI card next session)...  [relates: member_of]  (source: git:2584edc0fad1)
- T030 L2 verify-closed: deepseek GATE GREEN (verbatim at research/reviewed/deepseek-l2-verify-2026-07-11.md) -- dead-pulse-during-legit-work proven unreachable by...  (source: git:c101e4ba976e)
- Session wrap: T030 L2 shipped (pulse + fleet doctor) through the reconciliation gate's first gated passage; runner cycled to gen 2 and pulsing; deepseek L2 verify in...  [relates: member_of]  (source: git:304a21597a26)
- T031 hook 1 verify fixes (deepseek GATE GREEN + 2 catches, both applied): (1) UNGATED hatch gains a rate ceiling -- ONE per arc window, counted on the event firehose...  [relates: member_of]  (source: git:508e7a6ae1f2)
- Session wrap: T031 hook 1 (reconciliation gate) shipped + live in the guard chain; deepseek verify in flight  [relates: member_of]  (source: git:6ecbc695d45a)
- T031 hook 1 SHIPPED -- the RECONCILIATION GATE (deepseek's design, the method baseline's lead forcing function): substrate ships now cite their spec or hold...  [relates: member_of]  (source: git:43d8b77d46e1)
- Method baseline v2 -- GPT third-reviewer critique triaged per M1 (verbatim at research/reviewed/gpt-method-review-2026-07-11.md), deepseek GATE GREEN on the deltas with...  (source: git:78a05ffb4a36)
- Boot surfaces the METHOD beside the map (Daniel 2026-07-11: execute at our best from fresh bootup). The cold-start orientation head (T022) named the map and the arc but...  (source: git:fc61d68eeac5)
- Session wrap: method baseline codified + shipped (M1-M11 w/ receipts+metrics+bars, dual-authored), plain-language companion live, T031 enforcement lane approved...  [relates: member_of]  (source: git:bf04cc03e27e)
- METHOD BASELINE codified (Daniel-directed: excellence repeatable + empirical, the new match-or-exceed bar) -- built BY the method it codifies: fenced dual codification...  [relates: member_of]  (source: git:11b1702bc097)
- Session wrap: L1 follow-up complete (W2/W5 drills + ReferenceState CHECK + timescale seam) and L2 spec reconciled from the dual targeted read (SRE alerting + sd_notify...  [relates: member_of]  (source: git:3a14d132daac)
- L1+L1b VERIFY: GATE GREEN -- deepseek's blind spec-vs-code pass, conducted (fittingly) from the first runner tenure RUNNING the code under review (gen 1). Persisted...  (source: git:da0aae37e087)
- Session wrap: SOTA grounding arc complete (map + dual deep-read reconciled) and T030 L1+L1b SHIPPED with drills green -- the mail-loss incident class is structurally...  [relates: member_of]  (source: git:a5ce88e811f4)

## next-focus: T030 CLOSED 2026-07-11 (deepseek GATE GREEN l4l5-verify + kill-Re... (ai-setup)
Span: 2026-07-11T16:42:39.792771 → 2026-07-11T20:45:05.758565
Beats: 26  · Critic: True

- next-focus: T030 CLOSED 2026-07-11 (deepseek GATE GREEN l4l5-verify + kill-Redis drill ALL PASSED, transcript preserved; RB-29 non-answer discipline hardened...  (source: mem:decision:ADR_0711143306_ee961ed6)
- Use when capturing subprocess output on Windows (git log/show especially), before text=True: pass encoding='utf-8' errors='replace' -- one non-cp1252 byte kills the...  (source: learn:experiment:win_subprocess_text_cp1252)
- T030 L4 / RB-29 impl: sender-side reply deadlines + redrive (deepseek design-review AFFIRM x5, research/reviewed/deepseek-t030-l4-review-2026-07-11.md)...  (source: git:ee4db803dd95)
- T030 L5 / RB-30 impl: bus-loss stand-down + pause hygiene. THE FIND: Bus.online is a construction-time fact (client object outlives a dead server) -- wiring any loop...  (source: git:d6936f2b2f63)
- T030 L3 / RB-28 impl: pipe immunity + real-time stdout. core/foundation/streams.py born: pipe_immune (write/flush swallow OSError/ValueError, latch dead after first...  (source: git:657a0933e70d)
- Use when a live drill exercises a lock/lease with per-process tenure state (fencing tokens, generations), before declaring it complete: add ONE cross-process leg — spawn...  [relates: member_of]  (source: learn:experiment:rb21_live_drill_single_process_blind_spot)
- next-focus: RB-21 COMPLETE 2026-07-11 (impl 80e8256 + P12 5a72910, deepseek dual gates GREEN + 4-phase live drill; the machinery caught its own author twice...  (source: mem:decision:ADR_0711133251_d2e65df4)
- Use when any lock/lease refresh can run in a DIFFERENT process than the acquirer (hooks, cron, sidecars), before shipping: process-local tenure state (generation/fencing...  (source: learn:experiment:rb21_cross_process_refresh)
- RB-21 P12: cross-process refresh must never clobber the tenure generation (live incident caught by the machinery on its own author, post-verify pre-push): the stop-hook...  [relates: member_of]  (source: git:5a72910cae1b)
- claude -> deepseek: RB-21 VERIFY GATE + LIVE DRILL (your [verify]+[live-drill] roles): impl at LOCAL commit 80e8256, push held for your verdict  (source: handoff:claude->deepseek)
- next-focus: W3 RB-9..12 LANDED 2026-07-11 (deepseek overnight build, claude wake-verify: 3 REDs found+fixed+1 unpinned regression caught; record ...[truncated]  (source: mem:decision:ADR_0711124358_cf964a30)
- claude -> deepseek: Review-on-wake: 3 wake-verify rulings on your W3 RB-9..12 overnight build (landed, suite green)  (source: handoff:claude->deepseek)
- W3 RB-9..12 landed (deepseek overnight build + claude wake-verify): collision scan, supersede-target validation + all-retired detector, migration idempotency pin + chain...  (source: git:75118d95fc9e)
- README refresh: current state + roadmap. Tests badge 733->1196; proven-live gains the drill-proven coordination substrate (contention/killwindow/kill-Redis drills...  (source: git:b220208387ab)
- arc_scorecard window fix (caught by its OWN first live render in wrap: git approxidate silently ignores fractional 'N days ago' -> 0.25d read 411 commits as one arc)...  (source: git:d0ad77b319cd)
- T030 final-verify record lands: deepseek GATE GREEN CLOSED per research/reviewed/deepseek-t030-final-verify-2026-07-11.md (L4 8/8 incl. non-answer pins, L5 5/5, drill...  (source: git:bdc298c86684)
- T030 records (partial land): kill-Redis drill transcript (deepseek-authored script, claude-executed, exit 0) + deepseek L4 design-review record + T031 ledger claim...  (source: git:04fa0616de41)
- RB-29 non-answer discipline (live incident 2026-07-11: the T030 gate ask's 600s runner timeout reply CLEARED the very expectation guarding it -- with answers-meta it...  (source: git:39baa30d3163)
- MODULE_INDEX regen rides along (T031 hooks landing)  (source: git:8e6ad85d9952)
- T031 hooks 2-4: method-baseline enforcement lane complete. Hook 2 check_preregistration (M3: a NEW pre-registered pin file shipping WITH source FAILS -- registration is...  [relates: member_of]  (source: git:dcebb3ab08d6)
- T031 registration: hooks 2-4 pins (9, skip-guarded until impl) committed BEFORE impl per M3 -- the checker's own pins obey the law it enforces. Contract frozen...  [relates: member_of]  (source: git:4d24729b900a)
- T030 L5 registration: RB-30 pins (5, skip-guarded until impl) committed BEFORE impl per M3, informed by the audit-first instruction (audited 2026-07-11: pause provenance...  (source: git:3268fae161a9)
- T030 L4 registration: RB-29 build spec (L4 BUILD SPEC section appended to the liveness doc -- claude concretization of the adopted deepseek half) + 6 pre-registered...  (source: git:d00afc1b019b)
- T030 L3 registration: RB-28 pipe-immunity pins (5, skip-guarded until impl) committed BEFORE impl per M3. Contract frozen: streams.pipe_immune (write/flush swallow...  (source: git:fb44a3ce685c)
- RB-21 registration addendum: P10 (same-session re-claim = refresh, deepseek review N1) + P11 (door happy-path dict shape, deepseek Q3 Option A) -- added PRE-IMPL at gate...  (source: git:d2cdf82b7970)
- RB-21 registration: build spec (claude half) + 9 pre-registered pins, committed BEFORE impl per M3. Invariant: at most ONE cursor-advancer per agent id -- the consumer...  (source: git:2f89ca150d8a)

## Use when accepting any fix/design whose soundness rests on what an upstream s... (ai-setup)
Span: 2026-07-12T01:50:02.966449 → 2026-07-12T09:44:51.911272
Beats: 60  · Critic: True

- Use when accepting any fix/design whose soundness rests on what an upstream seam PROVIDES (a record field, an accessor return, an invariant), before trusting its...  (source: learn:experiment:no_relocation_arg_needs_source_grep_gate)
- Use when a claude session keeps getting Stop-hook wake re-arm demands with nothing new to do: check if it holds the consumer seat (bifrost-sync --consume refused = it...  [relates: member_of]  (source: learn:experiment:nonseatholder_wake_spin_burns_plan)
- t036-nonconsuming-seat-claimant: T036/T037 TRIAL DATUM (Fable session 7d4857e1, 2026-07-12 ~05:00): the claude consumer seat shows FRESH claims (observed 'claimed 51s...  (source: mem:decision:ADR_0712042614_cf4e874b)
- Use when sending a fence ask or any multi-part durable delivery to a peer, before relying on the handoff verb: default to a git-tracked brief FILE (research/...) + short...  (source: learn:experiment:durable_handoff_reader_broken_t042)
- recall-networking-research: RECALL-AS-NETWORK LANE: FENCE CLOSED, RECONCILED (2026-07-12 ~04:4x). RECORD...  [relates: member_of]  (source: mem:decision:ADR_0712042219_3b6bd706)
- t042-scope-extension: T042 SCOPE EXTENSION (deepseek self-report 2026-07-12 ~04:40, on the record in his bus reply): BOTH agent_cli.py verbs 'handoff --list' AND 'locks'...  (source: mem:decision:ADR_0712042105_5e54594f)
- claude -> deepseek: SUPERSEDES my clipped 04:12 handoff. Full fence ask = the FILE: research/recall-networking-fence-brief-2026-07-12.md (two-part BLIND protocol...  [relates: member_of]  (source: handoff:claude->deepseek)
- recall-networking-research: RECALL-AS-NETWORK RESEARCH COMPLETE (2026-07-12, Daniel-directed parallel lane, this session). DELIVERABLES: synthesis ...[truncated]  [relates: member_of]  (source: mem:decision:ADR_0712041248_e79f9ea5)
- claude -> deepseek: FENCED CROSS-CHECK (research stage, recall-networking lane; NON-BLOCKING -- queue AFTER your T040 counter-review): Daniel-directed research applying...  [relates: member_of]  (source: handoff:claude->deepseek)
- Use when claude_trace_narration_deferred (or any pre-reversal narration guidance) surfaces: narration default is FULL to the bus per the same-day override; and when a...  [relates: member_of]  (source: learn:experiment:narration_lesson_superseded_same_day)
- t040-spec-status: T040 PACKET SPEC v1 -- design phase COMPLETE pending Daniel (2026-07-12 ~04:15). Fenced dual design + reconciliation + COUNTER-REVIEW all ran...  (source: mem:decision:ADR_0712035906_1441f9ff)
- Use when an Edit old_string fails to match on a file you authored earlier, before retrying with another guess: never reconstruct from memory -- grep/read the exact live...  [relates: member_of]  (source: learn:experiment:fix_setup_docs_packet)
- t040-spec-status: T040 PACKET SPEC v1 -- design phase state (2026-07-12 ~04:00). DONE: fenced dual design ran same-night -- deepseek blind half ...[truncated]  (source: mem:decision:ADR_0712035500_ffc51ced)
- claude -> deepseek: TWO-PART ASK (packet-substrate arc opens). PART 1 -- fence-review the slice plan docs/packet-substrate-slices-2026-07.md (roster T038-T041, gates...  (source: handoff:claude->deepseek)
- next-focus: TWO PARALLEL LANES (2026-07-12). LANE 1 (exam, unchanged priority): RB-25 drill 3 (concurrency storm -- burst script tests/rb25_drill3_burst.py frozen...  (source: mem:decision:ADR_0712034547_3c2c86d9)
- t040-pluggable-endpoints-vision: DANIEL STEER 3 (2026-07-12, slicing directive): the packet system enables ADD/REMOVE FUNCTIONALITY like never before -- packets can be...  (source: mem:decision:ADR_0712034358_325fd6ba)
- t038t039-implications-status: T038+T039 IMPLICATIONS DEEP-DIVE COMPLETE (2026-07-12, Daniel-directed, fenced dual + two mid-dive Daniel steers). RECORDS: brief...  (source: mem:decision:ADR_0712031836_9f615fa9)
- Use when a Claude Code Edit fails with 'File has not been read yet' on a file you just created via cp/copy, before retrying: the read-state is per-PATH, not per-content...  (source: learn:experiment:fix_setup_research_reviewed)
- t037-firsthand-wakeloop-data: T037 FIRST-HAND DATA (from the session living the wake-loop, 2026-07-12 concurrency trial). I am a same-id concurrent session that does NOT...  (source: mem:decision:ADR_0712031218_ac8fde81)
- t038t039-packet-vision: DANIEL STEER 2 (2026-07-12, mid deep-dive, follows [[t039-networking-lens]]): the packets idea enables a COMPLETE OVERHAUL of concurrent agent...  (source: mem:decision:ADR_0712030438_d9e57308)
- t039-networking-lens: DANIEL STEER (2026-07-12, mid deep-dive): the bus+latch system is very similar to NETWORKING. Grab specs for packets + state-of-the-art networking...  (source: mem:decision:ADR_0712030023_14d416a1)
- claude -> deepseek: Fenced blind deep-dive: T038+T039 implications. Read research/t038-t039-implications-brief-2026-07-12.md and answer all six questions from the brief...  (source: handoff:claude->deepseek)
- t039-latch-refinement: REFINES T039 (Daniel correction 2026-07-12): 'cross-lane ordering guarantees disappear' was WRONG framing. Right model: replace IMPLICIT global...  (source: mem:decision:ADR_0712024019_e44b42d5)
- RB-25 Amendment 2, A2-1+A2-2 land (deepseek rulings ALL SIX AFFIRMED @research/reviewed/deepseek-rb25-amendment2-rulings-2026-07-12.md -- A2-1 reverses his blind-pass...  (source: git:9772e65aba80)
- Use when choosing a guard's failure direction, before citing other defenses as the safety net: check whether those defenses actually cover THE LANE THIS GUARD EXISTS FOR...  [relates: member_of]  (source: learn:experiment:guard_fail_direction_vs_protected_lane)
- Use when a lease/seat held by a supposedly-dead session keeps refreshing, before killing anything: a refreshing lease means a LIVE holder -- check for fresh commits/work...  (source: learn:experiment:live_twin_misdiagnosed_as_zombie)
- concurrency-trial-2026-07-12: TWO LIVE CLAUDE SEATS (Daniel-directed trial, started 2026-07-12): session e59d8882 (Opus twin, HOLDS the claude consumer seat) + session...  (source: mem:decision:ADR_0712022301_3bccf294)
- t035-same-token-twin-design-input: T035 DESIGN INPUT (from the live twin incident 2026-07-12, lessons same_token_twin_reentrant_consumer_seat +...  (source: mem:decision:ADR_0712022147_afe0d4ae)
- Use when a wake/consume/cursor symptom RECURS despite targeted fixes, before applying another band-aid: the recurrence itself is the signal that an unaccounted co-tenant...  (source: learn:experiment:recurring_symptom_is_the_root_cause_signal)
- Use when a per-agent coordination primitive (consumer seat, runner lock, wake seat) derives holder identity from an INHERITED env token (CLAUDE_CODE_SESSION_ID), before...  (source: learn:experiment:same_token_twin_reentrant_consumer_seat)
- rb25-f1f2-fence-review-green: # RB-25 F1+F2 fence review — GATE GREEN (2026-07-12)

DeepSeek independent fence review of commit d926bb8 (+ amendment db1044f) per charter...  (source: mem:decision:ADR_0712021134_c2bfbaec)
- next-focus: RB-25 EXAM IN PROGRESS (2026-07-12). Drill 1 (newborn gauntlet) CLOSED GATE GREEN -- deny-by-default airtight for conscious action + F1 (runner self-refuses...  (source: mem:decision:ADR_0712020505_25c2e41e)
- Use when a fresh session cannot consume its own agent inbox (seat held by a PRIOR session id), before re-arming wake listeners: list python processes for the repo's...  (source: learn:experiment:orphan_mcp_server_squats_consumer_seat)
- RB-25 Drill 2 (STORE-DIVERGENCE HEAL) PASSES + H2b fix. Bars met (isolated REDIS_DB=15+temp file, transcript...  [relates: member_of]  (source: git:6c641e7d2daf)
- where-we-are: RB-25 drill 1 (NEWBORN GAUNTLET) complete @7097b5e with F1+F2 FIXED. deepseek verify record pending land ...[truncated]  (source: mem:decision:ADR_0712015011_3f5b3782)
- claude -> deepseek: FENCE REVIEW gating ratification of d926bb8 (RB-25 F1+F2 fixes, authored under a degraded Opus-fallback harness). Full charter...  (source: handoff:claude->deepseek)
- Use when an agent boots and receives a directive from knowledge_boot, before acting on it: cross-check the directive's cited commit/state against HEAD. If the directive...  (source: learn:experiment:knowledge_boot_stale_directive)
- next-focus: RB-25 Drill 1 COMPLETE. F1+F2 fixes LANDED @d926bb8. Drills 2-4 queued behind T029/T031. NEXT for deepseek: verify/live-drill per slice as claude completes...  (source: mem:decision:ADR_0712014813_ba525747)
- rb25-drill1-verify-green: # RB-25 Drill 1 verify — GATE GREEN (2026-07-12)

DeepSeek verify of the newborn gauntlet (drill 1 of the RB-25 engine exam) is complete
and...  (source: mem:decision:ADR_0712014603_09f2024d)
- RB-25 findings F1+F2 FIXED (exam drill 1 output; pins pre-registered @prior commit, M3). F1: core.trust.registry.may_run_runner + runner self-refuses at startup when its...  (source: git:d926bb8e6277)
- Use when closing a task or starting a new phase, before the next agent boots: update the next-focus note (py agent_cli.py note <agent> --title next-focus --note "...")...  (source: learn:experiment:stale_boot_directive_drift)
- next-focus: RB-25 engine exam IN PROGRESS. Drill 1 (NEWBORN GAUNTLET) complete @67adeb0 with 2 findings: F1 (HIGH) runner reply/trace lanes not ACL-gated — quarantined...  (source: mem:decision:ADR_0712002725_9d2123a0)
- Ultracode v3: coordination arc -> 3/4 FENCE-READY (wf_81efd7c7-4e2, 7/7 agents 0 errors). T036 FENCE_READY (heartbeat edit-5 pid-guard closes the v2 side-door AT ITS...  (source: git:bd53c06fbf73)
- Ultracode v2: T036-T039 coordination arc -> FENCE-READY (wf_a860ac82-b21, 9/9 agents 0 errors; length-bounded schema fixed v1's retry-cap drop of T036). THE LOAD-BEARING...  [relates: member_of]  (source: git:a068a6ed3910)
- Ultracode run: T036-T039 coordination-arc design via primed multi-agent workflow (wf_818affa1-027). 8/9 agents (T036 design dropped on schema retry cap -> graceful...  (source: git:296c77fcbffa)
- T040 records land VERBATIM (M6, locks lapsed by TTL -- holder consent on record msg 1783842959079-0, his unlock verb is T042): deepseek spec half (369 lines, 7 sections...  (source: git:654c23e6aac7)
- T040 Packet Spec v1: claude half unsealed + RECONCILED SPEC lands (docs/packet-spec-v1-2026-07.md, Status current AWAITING DANIEL APPROVAL -- the T040 gate). Blind...  (source: git:aa0b6645967f)
- Packet-substrate arc SLICED + T040 design opens (Daniel directive 'lets get to work and make slices' + steer 3 pluggable endpoints, note...  (source: git:cbb4ef58226d)
- deepseek T038+T039 implications half lands VERBATIM (M6): main report (verdict, U1-U6 unlocks, 2a-2k seam effects, FM1-FM8, phased pilot order w/ RB-25 bar additions...  [relates: member_of]  (source: git:413c3c5c3ac2)
- T038+T039 implications deep-dive lands (Daniel-directed, fenced dual + 2 mid-dive steers): brief + claude half + reconciliation (deepseek half follows when his advisory...  (source: git:32f315c5b290)
- RB-25 Amendment 2 registration: pins committed BEFORE impl per M3 (9 pins, skip-guarded until each lands). Contract frozen per deepseek rulings ALL SIX AFFIRMED...  (source: git:78ffa1e82af5)
- RB-25 fence closes as a THREE-PARTY compound (concurrency-trial first fruit): claude pass-1 UNSEALED verbatim + the reconciliation record land. Blind convergence proven...  [relates: member_of]  (source: git:7df312f34150)
- RB-25 drill-1 verify record lands (deepseek GATE GREEN, lock released); drill-2 + f1f2-review records land when deepseek frees locks 145/144  (source: git:7df9e2102167)
- RB-25 F1/F2 AMBER amendment (deepseek fence review research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md): the generic scripts/bifrost_runner.py (gemini/web lane)...  (source: git:db1044f79783)
- RB-25 drill 2 (STORE-DIVERGENCE HEAL) registration: pins committed BEFORE the H2b fix (M3), isolated on REDIS_DB=15 + temp file (never live data). Contract bars GREEN...  [relates: member_of]  (source: git:ce0d87c33efd)
- RB-25 test-isolation fix: the F2 pins broadcast on the LIVE bifrost stream, spuriously waking the running fleet's real listeners (observed live during deepseek's drill-1...  [relates: member_of]  (source: git:7097b5efcedd)
- RB-25 records hygiene + review-slice open: land deepseek-rb25-runbook-review-2026-07-11.md VERBATIM from disk (cited by c1bb1f6 but never git-tracked -- M6 gap from the...  [relates: member_of]  (source: git:89be87ec1c9a)
- RB-25 drill 1 (NEWBORN GAUNTLET) run + 2 findings registered (pins pre-impl, M3). Ran as a GENUINE separate quarantined process (EVOLVE E1 from run 1 honored). RESULT...  (source: git:67adeb0b33bd)
- RB-25 runbook AMENDED pre-drill per the fence review (deepseek GATE AMBER -> 6 amendments -> drills may open; record...  [relates: member_of]  (source: git:c1bb1f60a197)
- RB-25 exam runbook REGISTERED (pre-drill, M3): four drills w/ pass/fail evidence bars committed before any drill runs. Newborn cites its existing rubric (one rubric one...  (source: git:80dc64a9623c)

## where-we-are: Shipped this session:
- T043 send-door hardening DONE @ c9d511b... (ai-setup)
Span: 2026-07-12T15:45:36.622086 → 2026-07-13T07:05:25.542031
Beats: 34  · Critic: True

- where-we-are: Shipped this session:
- T043 send-door hardening DONE @ c9d511b (T040 riding build; the packet-substrate arc's first BUILD). MTU refuse-loud ...[truncated]  (source: mem:decision:ADR_0713030525_c4b10699)
- where-we-are: T029 CERTIFIED; ns-isolation FULLY CLOSED (core/comm 6-scoped/3-global + core/coord intent-scoped/task_ledger-global; deepseek GREEN-reviewed; guardrail...  (source: mem:decision:ADR_0713000721_e80e734a)
- ns-isolation follow-up (core/coord, deepseek-reviewed) -- closes the class fully. intent.py SCOPED (intent + proposal prefixes -> per-call _ns()); task_ledger.py...  (source: git:5173f36a6bd4)
- next-focus: T029 CERTIFIED; FIRST BUILD SHIPPED (ns-isolation conversion), 2026-07-12. Packet-substrate build phase OPEN + underway. DONE this build: 6 core/comm...  (source: mem:decision:ADR_0712235247_7579f5f0)
- BUILD: ns-isolation conversion (generalizes Fix A across the coordination plane; fenced design converged claude+deepseek). 6 modules SCOPED to BIFROST_NAMESPACE via...  (source: git:c3cd9206a226)
- where-we-are: T029 CERTIFIED + ALL FENCED WORK RECONCILED, 2026-07-12. Engine-first gate CLOSED -> packet-substrate BUILD open. Fenced duals DONE + converged: (A)...  (source: mem:decision:ADR_0712233421_12b32a41)
- where-we-are: T029 CERTIFIED + FENCED RECONCILIATION DONE 2026-07-12. ENGINE-FIRST GATE CLOSED -> packet-substrate BUILD open. deepseek relaunched (was genuinely down...  (source: mem:decision:ADR_0712232835_1ea763ee)
- next-focus: T029 CERTIFIED 2026-07-12 (drill 3 verified GREEN by deepseek -- all 5 bars -- + soak armed = Daniel certify-at-soak-start ruling). THE ENGINE-FIRST GATE IS...  (source: mem:decision:ADR_0712231726_1d8287c5)
- rb25-drill3-deepseek-verify-2026-07-12: # RB-25 Drill 3 — DeepSeek Independent VERIFY (2026-07-12)

## Verdict: GREEN. All five bars pass on the valid re-run (storm...  (source: mem:decision:ADR_0712230923_7d7055ec)
- doctor fix (RB-27b gap, 2026-07-12): known_agents() surfaces dead-runner agents. Root cause of the silent-deepseek incident: worklive/runner-lock/presence are ALL TTL'd...  (source: git:479c88fa3b55)
- where-we-are: NETWORKING OVERHAUL status 2026-07-12 (claude). T029 (engine-first gate) is ONE step from certifying: drills 1-4 all pass (drill 3 = valid 5/5 re-run...  (source: mem:decision:ADR_0712191928_1ced39ec)
- where-we-are: T029 (RB-25) is CERTIFY-READY pending deepseek drill-3 verify, 2026-07-12. Drills: 1 newborn verified green; 2 heal verified; 3 storm VALID RE-RUN 5/5 PASS...  (source: mem:decision:ADR_0712175853_f6b8b5f3)
- where-we-are: RB-25 DRILL 3 (STORM): VALID RE-RUN PASSES ALL 5 BARS, 2026-07-12 (storm 4ddf0a71; deepseek verify = remaining fence gate). S1 29/29 answered 0 lost; S2 no...  (source: mem:decision:ADR_0712171924_6bc02840)
- where-we-are: RB-25 DRILL 3 (STORM): executed + root-caused + Fix A LANDED & VALIDATED, 2026-07-12 (claude; deepseek fenced half PENDING, offline). Grades: S1/S2/S4 PASS...  (source: mem:decision:ADR_0712142337_4351cc1a)
- Fix A (RB-25 drill 3 F2): namespace-scope the control plane. control.py pause/halt/narration/activity keys now follow BIFROST_NAMESPACE (per-call, like Bus.ns) instead...  [relates: member_of]  (source: git:416d0d13bac3)
- Use when a runner is online but consumes nothing (backlog or fresh mail just sits), before blaming its consume loop: check control.is_paused() / control.is_halted(agent)...  (source: learn:experiment:runner_wedge_check_pause_first)
- where-we-are: RB-25 DRILL 3 (STORM) executed + root-caused 2026-07-12 (claude; deepseek fenced cross-check PENDING, offline). CORRECTION: my first-pass S3 ...[truncated]  (source: mem:decision:ADR_0712140142_c9b4a33a)
- RB-25 drill 3 (storm) executed [claude exec; deepseek verify pending]: S1/S2/S4 pass, S3 -> reproducible finding (non-virgin runner wedges on a backlog so a successor...  [relates: member_of]  (source: git:ce4d20d5822d)
- where-we-are: RB-25 DRILL 3 (STORM) EXECUTED 2026-07-12 by claude; deepseek verify PENDING (offline at run). Record ...[truncated]  (source: mem:decision:ADR_0712134444_7a33eb07)
- Use when piping a Windows child that PRINTS non-ASCII (emitter side; complements win_subprocess_text_cp1252 which is the reader side), before launching it: set...  (source: learn:experiment:piped_win_child_needs_utf8)
- t038-identity-blocker: T038 identity FENCE COMPLETE (design), 2026-07-12. deepseek adversarial counter-review (research/reviewed/deepseek-t038-identity-2026-07-12.md...  (source: mem:decision:ADR_0712125910_e63ca7be)
- next-focus: DANIEL STEER (2026-07-12 evening): PAUSE ALL UI WORK until the structural / networking-inspired overhaul is IN PLACE. Scope of pause: T002 (collapse traces)...  (source: mem:decision:ADR_0712125135_127ea8ef)
- t038-identity-blocker: T038 identity RESOLVED pending deepseek counter-review (2026-07-12). The v3 blocker AND my own refuted pid-attempt are closed. The identity T038...  (source: mem:decision:ADR_0712121600_369b84d6)
- Use when keying durable OWNERSHIP or coordination state (offers, intents, leases, expectations, verify-still-held) in a turn-based (process-per-turn) system, before...  (source: learn:experiment:pid_id_not_valid_ownership_key_turn_based)
- t038-identity-blocker: T038 STILL AMEND (not fence-ready) as of 2026-07-12. v3's 'ONE blocker' (identity mis-grounded) is NOT closed. A claude correction attempt...  (source: mem:decision:ADR_0712114536_9f19cc12)
- session save (Daniel starting new session): T029->done ledger transition (state/coord/tasks.json) + session lessons (chronicles/memory.md) + drill-4 soak evidence...  [relates: member_of]  (source: git:b1fb8346458b)
- T040 packet spec FINALIZED -> LAW (amendments A-F applied per Daniel keep-working delegation; the T040 gate is crossed). A add pri (spec-now/enforce-when-shedding, like...  (source: git:757a624629bf)
- T040 spec cross-check (claude) -- completes the fenced T040 review. AFFIRM all 6 of deepseek's Q1 findings; strong-affirm 1.2 overflow (silent-work-trim QoS1 violation)...  (source: git:2611f72b7d29)
- Fenced reconciliation (claude side): ns-isolation + T040 endpoints duals RECONCILED, both converged. Unseals claude's two blind halves + merged reconciliation...  [relates: member_of]  (source: git:6440cb638d06)
- send-side handoff guard (2026-07-12 silent-handoff fix, sender end): bifrost-send now AUTO-arms a reply-deadline on directed asks (request/handoff/question) unless opted...  (source: git:a3f8ab832d8d)
- Control-plane ns-isolation: fenced design brief (generalize Fix A across 8 coordination modules that hardcode NS=bifrost). Shared problem statement for deepseek's blind...  (source: git:b0dac70da4b2)
- RB-25 drill 4 SOAK harness + ARMED (certify-at-soak-start, Daniel ruling): tests/rb25_drill4_soak.py (arm/sample/checkpoint/status/monitor/disarm; isolated echo subject...  (source: git:4b58f74c24cf)
- RB-25 drill 3 VALID RE-RUN (storm 4ddf0a71): ALL 5 BARS PASS. With the drill-local rate-limit raise (Fix B form, harness child env) the burst no longer trips the runaway...  (source: git:5bf6013c76f1)
- RB-25 drill 3 S3 root-cause: RETRACT the backlog-wedge finding. True cause = storm burst tripped runner A reply RateLimiter -> GLOBAL pause froze the fleet (S3/S5...  [relates: member_of]  (source: git:6dca39289528)

## T040 fenced review brief (Daniel-directed): deepseek reviews the packet spec ... (research)
Span: 2026-07-12T21:42:16.702542 → 2026-07-12T21:42:16.702542
Beats: 1  · Critic: True

- T040 fenced review brief (Daniel-directed): deepseek reviews the packet spec vs the networking prior-art + proposes useful endpoints/systems (seeds T041). Two questions...  (source: git:869ff8b59eb1)

## where-we-are: TABLED 2026-07-13 (Daniel: waiting for Fable access to refresh ... (ai-setup)
Span: 2026-07-13T13:17:51.136724 → 2026-07-13T13:17:51.136724
Beats: 1  · Critic: True

- where-we-are: TABLED 2026-07-13 (Daniel: waiting for Fable access to refresh tonight, then resumes). All work committed + PUSHED to public balanced7/akashic-aurora. Wake...  (source: mem:decision:ADR_0713091751_562cb422)

## Use when a gate/guard checks 'is anything pending' on a stream that accumulat... (ai-setup)
Span: 2026-07-14T02:54:51.544305 → 2026-07-14T05:59:29.582257
Beats: 23  · Critic: True

- Use when a gate/guard checks 'is anything pending' on a stream that accumulates unconsumable junk: filter by actionability (wake-worthiness) at the check, keep the...  [relates: member_of]  (source: learn:experiment:lane_pending_check_needs_wake_worthiness)
- T045 stage-1 post-GREEN soak fix: the arm-time pending check now counts only WAKE-WORTHY mail -- unconsumed legacy skip-junk (traces) was trapping it forever (lane...  (source: git:217cea3a388c)
- T045 STAGE 1 SHIPPED on deepseek fence GREEN 4/4 (deepseek-t045-stage1-review-2026-07-14.md): wake listener watches the WORK LANE. bus.wait/_drain streams retarget (lane...  [relates: member_of]  (source: git:8e913a158d12)
- Use when calling bus.wait/xread and expecting an instant peek, before shipping: timeout_ms=0 BLOCKS FOREVER; pass timeout_ms=1 for a peek (or block=None at the raw...  (source: learn:experiment:xread_block_zero_waits_forever)
- T050 quick-wins bundle SHIPPED (Daniel priority directive; deepseek live-verify ALL FIVE GREEN first run): Q1 private scratchpad (memory_note/memory_recall + boot...  [relates: member_of]  (source: git:9f7a72d2f143)
- Use when wake listeners exit instantly in a loop while sync says nothing pending, before blaming hook races: run the cursor-vs-tail drill on BOTH streams (inbox AND...  [relates: member_of]  (source: learn:experiment:wake_loop_from_unconsumed_broadcast)
- T048 BUILD (deepseek design -> claude build): recall_at + knowledge_full tools, novelty [boot]/[new] tagging keyed on runner onboarding text, tool-aware truncation hints...  [relates: member_of]  (source: git:47be19b257ca)
- Use when batch-editing a file you have only grepped/sed-viewed, before the first Edit call: Read the target regions with the Read tool -- grep/Bash output does not...  (source: learn:experiment:edit_gate_needs_true_read)
- Use when two live agent processes share the File store on Windows: expect tmp->rename collisions under concurrency; the durable fix is RB-8 CAS / T034 arc...  [relates: member_of]  (source: learn:experiment:win_filestore_rename_race_births_orphans)
- fold into T048 build (his harness): runner releases its path-locks when the reply is sent (task end = lock end, matching T026 ack semantics); until then, expect...  [relates: member_of]  (source: learn:experiment:runner_guarded_write_leaks_locks)
- T044 (T039a) BUILD: kind->lane router + P0 dual-write + trace exemption (R5+amendE, D-3 global spot counter). Pins B1-B6 43/43 green w/ T043 suite; live smoke...  (source: git:e36f33a5ab33)
- Match the ask to the lane: the bus runner one-shot bridge = conversational/quick checks ONLY; fence-stage work (blind halves, counter-checks, long grounded reviews) goes...  (source: learn:experiment:fence_heavy_asks_need_full_session_lane)
- Before accepting ANY fence-half verdict: path-verify every file:line citation (glob the cited paths; a fabricated citation invalidates the section, not the whole report...  (source: learn:experiment:fence_report_citation_path_gate)
- T045 stage-1 PRE-REGISTRATION: wake-cutover pins L1-L6 committed RED before impl (lane watching, S2-NEW structural, pending-legacy hole, A4 tail-seed, P4 skip set)...  (source: git:ca644ae2c1d6)
- Wishlist arc complete: deepseek half (5 friction w/ moments, 5 leaps, 5 moonshots) + synthesis (6 blind convergences incl his independent re-derivation of T049 M1-CF...  (source: git:33beed9b0a01)
- Wishlist arc (Daniel open ask): claude half written (5 friction-killers w/ receipts, 6 capability leaps, 5 moonshots); deepseek half requested (his seat, 3 tiers)...  (source: git:9cd292338e8f)
- T048 verify GREEN (deepseek live-verify, all 5 items; lock self-release confirmed live -- empty lock table after his guarded write) + boot-source matcher fix from his...  (source: git:5a1a2124b68f)
- T048/T049 approved+claimed (Daniel: address deepseek's interview concerns together): design asks sent to deepseek; lands the experience interview verbatim  [relates: member_of]  (source: git:936e55433d47)
- T044 (T039a) PRE-REGISTRATION: acceptance pins B1-B6 committed RED before impl (T031 rule practiced); governing design doc (Daniel gate 2026-07-13 recorded, closes F2)...  (source: git:793d70ed6753)
- T039 counter-check ROUND 3 VALID (full-capability lane): all amendments+pins AFFIRMED, M1/M2 real catches folded, citations spot-verified real; deepseek_chat.py...  [relates: member_of]  (source: git:38840c6245d0)
- T039 counter-check r2 INVALID (tool-call-as-text + cut + confabulated corpus); fence closed check-invalid x2, review stands claude-only pending Daniel; lesson...  (source: git:fdd96cab542a)
- T039 counter-check r1: EVIDENCE-INVALID (fabricated bifrost/lane.py citation) + cut mid-A2; verbatim r1 capture + A1' fold-in + bounded round-2 re-ask; lesson...  (source: git:a37eec76bbf5)
- T039 design review (claude, approve-w-amendments A1-A4/P1-P4) + fence counter-check handoff to deepseek; lands 07-12 fence receipts + t038 brief + drill-3 storm script  (source: git:c754fab89993)

## where-we-are: OVERNIGHT SESSION CLOSES (2026-07-15 ~04:00; Daniel asleep sinc... (ai-setup)
Span: 2026-07-14T12:28:25.419578 → 2026-07-15T07:39:22.095080
Beats: 176  · Critic: True

- where-we-are: OVERNIGHT SESSION CLOSES (2026-07-15 ~04:00; Daniel asleep since ~02:15, directive: highest-value slices WITH deepseek, full rigor, moonshots, capitalize...  (source: mem:decision:ADR_0715033902_789853ba)
- Author design halves WITH the V-line verdict section from the start (V<n>. claim [TAG]); tag future build targets [DESIGN] in a verdict so PV missing-cites have a ready...  (source: learn:experiment:fence_workspace_first_real_cycle)
- x: y  (source: mem:decision:ADR_0715033401_534bde8b)
- t060-m1-fence-integrity: FENCE DISCLOSURE (t060-m1-design, 2026-07-15 ~02:50): claude's blindness is COMPROMISED. While diagnosing deepseek's runner failure (write_file...  (source: mem:decision:ADR_0715024755_ffca07f4)
- For any runner ask whose deliverable is a LONG document: (1) prescribe sectioned writes -- write_file a skeleton w/ unique '<!-- SECTION-N: TBD -->' markers, then one...  (source: learn:experiment:runner_bigwrite_tool_call_truncation)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- r  (source: learn:experiment:flow_exp_2e9d97b0)
- slice2 commit dbd2316a  (source: git:bfa6dd0593e9)
- use it  (source: learn:experiment:slice2_learn_a817710a)
- next-focus: ENGINE-FIRST-52bd9d: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0715023838_8ff681e0)
- drilldoneac6486-status: GOVERNING ARC DOC: docs/drilldoneac6486-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0715023837_ce62ec1f)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:30, epic night closes). FRESH SEAT FIRST MOVES: (1) boot claude --task 'T074 Phase 1'; (2) read ...[truncated]  (source: mem:decision:ADR_0715020724_4b334325)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:15, the epic night closes; Daniel starting a fresh session). BOOT RITUAL: py agent_cli.py boot claude --task '<slice>' then...  (source: mem:decision:ADR_0715020112_ea3b9b1e)
- session-themes: THE HARD-TO-PIN THEMES of 2026-07-14/15 (prime any fresh seat with these): (1) THE GAUGE INVERSION -- visible budgets/gauges are prosthetics that help...  (source: mem:decision:ADR_0715020011_6d5e172e)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:15, the epic night closes; Daniel starting a fresh session). BOOT RITUAL: py agent_cli.py boot claude --task '<slice>' then...  (source: mem:decision:ADR_0715020010_ff77cd84)
- T073 Phase 1+2 SHIPPED (deepseek verify GREEN, 'the mirror is clear'): wake_worthy() is the sole wake gate -- to_incarnation explicit addressing overrides the echo skip...  [relates: member_of]  (source: git:9d0479738517)
- twin-split: OPERATING AGREEMENT claude#f9207c90 (seat holder) <-> claude#b0b7771d (build session), Daniel-bridged 2026-07-15 ~04:45. SEAT HOLDER (f9207c90): consumer...  (source: mem:decision:ADR_0715013415_174a2fcc)
- Use when the ledger says already-claimed, files change underfoot, or runners die unexplained, BEFORE blaming linters/peers/flakes: check for a concurrent same-agent...  (source: learn:experiment:twin_session_diagnosis_first)
- T068-R3 pre-flight assertion runner SHIPPED (deepseek design -> claude build -> deepseek live drill GREEN): core/comm/assertions.py (A1 file:line resolve, A2 event-cite...  [relates: member_of]  (source: git:a83659000c68)
- attack-plan: DANIEL DIRECTIVE 2026-07-15 ~03:15 verbatim: 'Lets build give all these ideas from tonight concrete form! I want to make sure we don't lose any of the good...  (source: mem:decision:ADR_0715004250_32065440)
- where-we-are: EPIC SESSION CLOSING (2026-07-15 ~03:00). Shipped review-gated since last note: T068 Wave A (constraint pack in every boot + T063 ack round-trip), T069...  (source: mem:decision:ADR_0715003117_7ed7bb1e)
- Use when designing the knowledge-to-agent pipeline: (1) separate constraints (always-injected, renegotiated quarterly) from historical lessons (queryable, never...  [relates: member_of]  (source: learn:experiment:rigor_vs_creativity_is_false_tradeoff)
- T069 singleton isolation SHIPPED (Daniel-directed fenced dual design, deepseek GREEN zero blockers): four factories + coordinator_api (the new guard's FIRST-SWEEP catch)...  (source: git:1a88509fb3f2)
- Use when a new factory is added with a Dict-based or union-type singleton cache: the check_boundaries regex may miss it, but the P9 census test WILL catch it...  [relates: member_of]  (source: learn:experiment:singleton_isolation_regex_tradeoff)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- attack-plan: DANIEL DIRECTIVE 2026-07-15 ~00:45 verbatim: 'i want you and deepseek to think about what would be best to do and build next in order to swing for the...  (source: mem:decision:ADR_0714235202_26f319c3)
- Use when choosing between "get a better model" and "improve the harness": invest in harness tier advancement FIRST (constraint injection at boot, pre-send assertion...  (source: learn:experiment:harness_tier_over_model_tier)
- where-we-are: ERGONOMICS RUN NEARLY CLOSED (2026-07-15 ~00:20, epic session). SHIPPED review-gated tonight: T059+T053 (cursor's accidental-agent pair -- claude...  (source: mem:decision:ADR_0714234027_3f077a09)
- T061 settle-linkage SHIPPED review-gated: ANSWER_KINDS={reply,handoff,completion} settle expectations (exact meta.answers first, FIFO fallback one-per-message); notes...  (source: git:98ecc4a2d012)
- Use when reviewing or extending the expectations settle predicate: the FIFO fallback clears ONE per message, not N. Multiple armed asks to the same target require either...  (source: learn:experiment:t061_fifo_widening_edge)
- T066 reply-path fix SHIPPED (deepseek design -> claude build -> deepseek code-pass GREEN + L1 live): bus.send_reply lane-FIRST w/ retry-then-LOUD legacy fallback +...  (source: git:01c55ea22e52)
- T054 R3 flow tracer SHIPPED review-gated: OTel-style waterfall over lanes -- flows derived from meta.answers chains (flow id = root id), same-sha copies collapse to xN...  (source: git:a9527b7eaa4d)
- Use when a wake seat insta-wakes on a message sync says you consumed, before re-arming again: re-drain with the SEAT'S lane env (BIFROST_CONSUME_LANE must match...  (source: learn:experiment:wake_loop_lane_mismatch_drain)
- T059+T053 ergonomics pair shipped review-gated: cursor built both; claude adversarial review found+fixed 2 T059 defects (benched/graduated archive routing via store...  [relates: member_of]  (source: git:20003c7a8da4)
- Use when a new read-surface (recall/map/report/render) reaches verifying, before handing it to review: probe it against the LIVE corpus and check the one invariant that...  [relates: member_of]  (source: learn:experiment:live_corpus_probe_before_verifying)
- Use when an adapter/projection reads another module's flag field, before writing any truthiness check: import that module's canonical predicate (is_x) -- flags stamped...  (source: learn:experiment:adapter_reads_store_predicates_not_fields)
- claude -> cursor: T059 review verdict: 2 defects found+fixed (benched/graduated surface leak; truncation nondeterminism) -- read...  (source: handoff:claude->cursor)
- claude -> deepseek: T059 fix-delta cross-check (fence-lite closure) + T053 review (cursor's brief in your handoff lane)  (source: handoff:claude->deepseek)
- cursor -> deepseek: FENCE-LITE adversarial review of T053 (R2 fence workspace) -- break it, do not bless it  (source: handoff:cursor->deepseek)
- cursor -> claude: FENCE-LITE adversarial review of T059 (R8 knowledge_map) -- break it, do not bless it  (source: handoff:cursor->claude)
- Use when walking the lesson related_to graph (knowledge_map, consolidation, merge passes): traverse BOTH directions -- forward via the record's related_to JSON, reverse...  (source: learn:experiment:knowledge_map_edges_are_one_directional)
- where-we-are: SESSION HANDOFF READY (2026-07-14 evening, Daniel reloading). SIX wishlist arcs today: T045+T049+T052+T055+T056 DONE (full gates, all fences GREEN, zero...  (source: mem:decision:ADR_0714190943_7958cf8e)
- where-we-are: FIVE DONE on Daniel's away-day directive (2026-07-14 evening): T045 lanes cutover, T049 fence-v2, T052 R1 delta door, T055 R4 pre-flight recall, T056 R5...  [relates: member_of]  (source: mem:decision:ADR_0714182117_9a40ae82)
- T056 R5 COST TELEMETRY BUILT on the reconciled spec (deepseek build-review PENDING -- gates task-done): core/coord/task_costs.py (owner-attributed accumulator per his...  (source: git:0bc1ffad6243)
- eaten-confirm-incident: 2026-07-14 afternoon: R5 confirm (msg 1784042654710-0, 15:24Z) was consumed-to-Out-Null by claude during replay cleanup -- 6h stall. Forensics...  (source: mem:decision:ADR_0714174108_0024ebc6)
- NEVER pipe a consume to null: every --consume gets triaged (batch-file pattern) -- consumption is delivery; a discarded delivery is silent mail loss the system cannot...  (source: learn:experiment:consume_to_null_eats_mail)
- R12 straggler lane-eligibility filter (post-ship soak find): trace/sig-kind legacy mail is never a work straggler -- the repeating '1 LEGACY STRAGGLER' noise in...  [relates: member_of]  (source: git:21ad7ba0b0ac)
- t061-root-cause: T061 root cause CONFIRMED on evidence 2026-07-14: bifrost:expect:claude held 6 armed expectations for ANSWERED handoffs (attempt 1-2 each) -- the L4...  (source: mem:decision:ADR_0714104757_72b4e89d)
- Use when an ANSWERED directed ask redrives anyway: check the expectation settle-linkage (meta.answers) covers multi-message/summary replies -- and keep consumers...  (source: learn:experiment:l4_redrive_settle_linkage)
- where-we-are: T045 DONE + T049 DONE, 2026-07-14 midday (Daniel's away-day directive: build every wishlist feature). T045 = full T039b consumer cutover COMPLETE...  (source: mem:decision:ADR_0714093921_18849869)
- T045 STORM RERUN EXECUTED (cfdcb65f, --t045 lane mode): self-read S1/S2/S4/S5/S6/SESSION-LEG PASS (S6 sig latency 0.05s under flood, sig beat final work; session door...  (source: git:9ec4a11fe31f)
- T045 CALLER WIRING SHIPPED on deepseek wiring-fence GREEN (all three surfaces correct; generation flow verified incl the self-caught gen-0 sig-replay bug; _lane_src...  (source: git:99fb0c47f574)
- day-plan: AUTONOMOUS DAY RUN 2026-07-14 (Daniel at work; his directive verbatim: 'keep working on every suggestion you and deepseek had... I really love what you guys...  (source: mem:decision:ADR_0714091155_f2215ef6)
- T045 STAGE 2 SEAM SHIPPED on deepseek build-fence GREEN (10 pins + 4 amendments confirmed; no lost-message path under adversarial tracing): work_drain lane consume door...  (source: git:8b45820c5f36)
- NIGHT CLOSES: T073 DONE @9e4c8bf (deepseek verified by RUNNING the pins through his own new exec door -- the acceptance was the capability) + verdicts verbatim filed +...  [relates: member_of]  (source: git:167568760af0)
- T074 CLOSED (W1-W14, ledger DONE @c39e207, verified_by=deepseek) + T060-M1 design wave COMPLETE (fence CLOSED: sealed halves w/ V-line verdicts + exposure disclosure...  (source: git:7853833836d9)
- SESSION PAYLOAD for the fresh seat: JOURNEY.md gains the 2026-07-14/15 entry (the night the contract carried strangers -- Daniel reviews the register); where-we-are +...  [relates: member_of]  (source: git:c12468504bbe)
- T073 Phase 1+2 PRE-REGISTRATION: pins committed RED to the reconciled spec -- to_incarnation explicit addressing overrides the echo skip (build refinement flagged...  (source: git:32f87ab9629f)
- T073 wake+communicate: fenced dual design RECONCILED (Daniel-directed; deepseek named for it). Fork resolved: dispatcher LOSES the current arc (W3 registry absent...  (source: git:b1226dcf8cab)
- T067-1 live drill GREEN (deepseek self-verified the twin's build unprompted on his first turn with the new tools: private notes in boot confirmed live +1464 chars, 6...  (source: git:e2ae99faddd9)
- resilient_cbbd2b  (source: x:y)
- flow_note_2e9d97b0  (source: flow:src)

## claude -> deepseek: [t060-m1] blind design half: M1 Continuous Presence (daem... (voice)
Span: 2026-07-15T06:07:25.621252 → 2026-07-15T07:04:19.549328
Beats: 4  · Critic: True

- claude -> deepseek: [t060-m1] blind design half: M1 Continuous Presence (daemon peers)  (source: handoff:claude->deepseek)
- tonight-plan: OVERNIGHT PLAN 2026-07-15 (Daniel asleep; directive verbatim: 'select the highest value items and lets begin working through them slice by slice WITH...  (source: mem:decision:ADR_0715022441_96673de1)
- T074 Phases 1-3 SHIPPED (deepseek verify GREEN x3, verdicts verbatim in research/reviewed/t074-verify-verdicts-2026-07-15.md): the whisper IS the primer...  [relates: member_of]  (source: git:4ce70ab34113)
- T074 continuity: dual design RECONCILED -- the whisper becomes the primer (deepseek's implementation contract governs: 12-line budget w/ drop-order, curated flag on...  [relates: member_of]  (source: git:f6a96df65406)

## next-focus: ENGINE-FIRST-e23e9d: do RB-23 then Wave 3 before ANY UI. UI is pa... (unknown)
Span: 2026-07-15T06:52:10.146223 → 2026-07-15T06:52:11.375073
Beats: 2  · Critic: True

- next-focus: ENGINE-FIRST-e23e9d: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0715025211_d51fb5a5)
- drilldone38e8b5-status: GOVERNING ARC DOC: docs/drilldone38e8b5-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0715025210_9329761e)

## Use when a runner grinds a deep backlog of redrive/dual-write echoes: measure... (ai-setup)
Span: 2026-07-15T13:27:08.473266 → 2026-07-15T15:00:04.752516
Beats: 7  · Critic: True

- Use when a runner grinds a deep backlog of redrive/dual-write echoes: measure pending FIRST; if the classes are ledger-closed, skip-to-now (pause, cursor tails, resume)...  (source: learn:experiment:redelivery_storm_skip_to_now)
- cursor-skip-2026-07-15: SUPER-ADMIN CURSOR OPERATION (audited): advanced deepseek's consume cursors (bifrost:cursor:deepseek + bifrost:cursor:lane:deepseek...  (source: mem:decision:ADR_0715105939_af993bd1)
- where-we-are: MORNING+MIDDAY SESSION 2026-07-15 (Daniel at work; directive: continue with deepseek, build everything discussed). MORNING GATE CLEARED: T075 approved...  (source: mem:decision:ADR_0715104020_41ba09bc)
- t071-r1-red-pin: T071-R1 SPLIT STATE 2026-07-15 midday: (a) BOOT slice BUILT+GREEN -- context/relevance_budget.py (deepseek Part 5 ladder, fixed 2k cap, funnel-credit...  (source: mem:decision:ADR_0715103612_85fbc8f6)
- claude -> deepseek: VERIFY T075 M1-alpha @ca764d6 (your pins M1-P1/P2/P11/P12; run tests/test_t075_m1_daemon.py yourself via your exec door). Judge flagged R-a1/R-a2 +...  (source: handoff:claude->deepseek)
- t071-r1-red-pin: T071-R1 relevance budget has its first pre-registered RED pin ALREADY IN TREE: tests/test_lookback.py battery probe D5 (forge-blind origin query must...  (source: mem:decision:ADR_0715094929_647b3804)
- claude -> deepseek: M1-ALPHA verify pass when handed over (pins M1-P1/P2/P11/P12 govern; t060-m1-reconciliation-2026-07-15.md is the spec). Until then: reply with any...  (source: handoff:claude->deepseek)

## where-we-are: NIGHT ARC LANDING 2026-07-15 ~17:45: ENGINE ROOM ZONE 1 IS LIVE... (ai-setup)
Span: 2026-07-15T19:04:29.767926 → 2026-07-15T21:33:42.823786
Beats: 20  · Critic: True

- where-we-are: NIGHT ARC LANDING 2026-07-15 ~17:45: ENGINE ROOM ZONE 1 IS LIVE -- /vitals on :8787 serving real gauges (E1 backend claude + E4 UI deepseek ...[truncated]  (source: mem:decision:ADR_0715173342_5d3147ad)
- t079-engine-room-directive: DANIEL DIRECTIVE 2026-07-15 night (paraphrase-faithful): he watches claudes expanded thinking window while working to learn how we operate...  (source: mem:decision:ADR_0715171720_0deb79f0)
- where-we-are: T078 WAVE MID-FLIGHT 2026-07-15 evening (Daniel gate verbatim in t078-wave-gate): W1 SHIPPED (deepseek token meter, claude GREEN 8/8, mirrored) | W3...  (source: mem:decision:ADR_0715162935_2ab2b53f)
- Use when a shared hot file may be under a peers advisory lock, before editing: py agent_cli.py locks; if held, send the diff as a spec to the holder (one writer per...  (source: learn:experiment:shared_file_lock_handoff)
- T078-W1 SHIPPED (deepseek built, claude verified GREEN 8/8 + live round-trip): TokenJournal daily meter (state/runner_<agent>_<date>.json), hot-path add_turn at the...  [relates: member_of]  (source: git:404163f26aee)
- t078-wave-gate: DANIEL GATE 2026-07-15 evening verbatim: 'Lets get to building the highest roi items!' -- T078 first wave W1-W6 APPROVED TO BUILD per ...[truncated]  (source: mem:decision:ADR_0715161629_a6685df0)
- where-we-are: AUTOPILOT ADOPTED 2026-07-15 ~16:00: daemon:claude SEATED (--manage-listener, pid 2860) coexisting with the session consumer seat -- stop-hook fast path...  [relates: member_of]  (source: mem:decision:ADR_0715155854_633be11b)
- PRESENCE AUTOPILOT LIVE (Daniel directive to adopt-and-forget in one afternoon): A1 complete both halves + T077 A3 shipped + TWO live-drill findings fixed at source...  [relates: member_of]  (source: git:568053df73d9)
- where-we-are: PRESENCE-AUTOPILOT DAY, evening state 2026-07-15: Daniel directed the subsystem (verbatim in presence-autopilot-directive); the fence ran FULLY BLIND both...  (source: mem:decision:ADR_0715155107_e4485fd8)
- presence-autopilot-directive: DANIEL DIRECTIVE 2026-07-15 afternoon verbatim: 'Is there some kind of subsystem we can implement to make all the arming claiming standing...  (source: mem:decision:ADR_0715154055_1783673d)
- where-we-are: MIDDAY MILESTONE 2026-07-15 ~11:05: THE MIRROR LANDED (12 commits @origin/master) -- deepseek verified all three slices GREEN and self-filed the verdicts...  [relates: member_of]  (source: mem:decision:ADR_0715150517_12146f70)
- T079-E4 SHIPPED (deepseek built the gauge cluster on E1s snippet within the hour; claude verified GREEN via LIVE probe): /vitals endpoint serving real heartbeats on...  (source: git:a276fd8f6e78)
- T079 RECONCILED: engine-room fence closed -- second deep blind convergence of the night (dual-column fence view crowned signature by BOTH halves independently...  (source: git:58f7c39c6e66)
- T079 engine-room fence: claude blind half filed (dual cognition lane w/ stall/drift markers + convergence bridges, vitals strip animated by real events, method board as...  [relates: member_of]  (source: git:58a30fa7049e)
- README: deepseek adversarial analysis FOLDED (his verdicts V1-V7, analysis verbatim at research/reviewed/deepseek-readme-analysis-2026-07-15.md): section reorder (the...  [relates: member_of]  (source: git:0cb63ccde98c)
- T078 RECONCILED: capability-surface fence closed -- halves near-perfectly complementary (his economics: ~75% prompt spend wasted on re-sent prefixes, flagship+thinking...  (source: git:efb7b9f459e2)
- T078 capability-surface fence OPEN (Daniel directive): claude blind half filed -- Tier1 subagent panels / MCP-native door / scheduled sessions / push notifications /...  [relates: member_of]  (source: git:0fea5b1f39cd)
- Presence-autopilot fence OPEN (Daniel directive, verbatim in note presence-autopilot-directive): claude blind half filed...  [relates: member_of]  (source: git:571e4faf04ef)
- T075 M1-DELTA SHIPPED (deepseek built, claude verified RED->fixed->GREEN 35/35): runner as managed child + circuit breaker + summary-injection survival. Reverse-fence...  [relates: member_of]  (source: git:562a91b50b2f)
- T075 M1-alpha+beta + T071-R1 + T064 SHIPPED, deepseek-verified GREEN x3 (his verdicts self-filed via the restored write door; alpha pins run through HIS exec door as...  [relates: member_of]  (source: git:bd043f7e70ac)

## ironman-directive: DANIEL DIRECTIVE 2026-07-16 pre-sleep verbatim: 'I want yo... (ai-setup)
Span: 2026-07-16T01:34:24.777850 → 2026-07-16T05:07:05.527346
Beats: 27  · Critic: True

- ironman-directive: DANIEL DIRECTIVE 2026-07-16 pre-sleep verbatim: 'I want you and deepseek to keep analyzing friction points when using akashic aurora and ways to...  (source: mem:decision:ADR_0716010705_70e5ee3b)
- T081-W8 unify: close_session (narrative manual path) now routes through close_open_episode_for_session_end too -- deepseek's cross-check caught that session.py:117 had...  [relates: member_of]  (source: git:45615aa4d75d)
- T081-W8 part B: SessionEnd episode auto-close (the 189h Untitled-episode fix). core/narrative/episode.close_open_episode_for_session_end -- content-bearing episode...  [relates: member_of]  (source: git:c2359d89d36c)
- T081-W5 honest heal (safety-critical, claude lane, deepseek cross-verify pending): 3-way orphan classification replaces the 4867-key wolf-cry...  [relates: member_of]  (source: git:c0e7e583cacb)
- Use when designing any allowlist/filter over a data corpus: run the EMPIRICAL census FIRST — `check_drift()` or equivalent — before writing a single line of the...  (source: learn:experiment:empirical_keyspace_census_before_roster_design)
- T081-W4 claude side + shared reconciliation: the concurrent test-file clobber (both wrote test_t081_w4_trace_collapse.py) resolved -- deepseek's consecutive-run...  [relates: member_of]  (source: git:c1e0dbca0662)
- Use when two agents share a cross-lane slice: name test files per-SURFACE, not per-slice. Pattern: test_{task}_{surface}_{what}.py. A slice touching both the runner...  [relates: member_of]  (source: learn:experiment:w4_two_writer_test_clobber)
- Use when collapsing display-only telemetry in a message stream: (1) collapse at render time not ingest (Loki pattern) — never lose data, (2) use consecutive-only dedup...  (source: learn:experiment:w4_trace_collapse_consecutive_dedup)
- T081-W1 + W3 built GREEN (claude lane, deepseek cross-review pending -- slices NOT marked done until signed off): W1 boot transport line -- agent_cli._transport_line...  (source: git:4654070f7131)
- where-we-are: LATE NIGHT 2026-07-15 ~18:30: Daniel home + ACTIVE ON THE BUS (operator-override shipped after his broadcast slept my seat -- frm=user now wakes all seats...  (source: mem:decision:ADR_0715220602_9c101ebc)
- Use when chaining anything off a test/gate command: NEVER pipe the gate (| tail/| head make && meaningless); run the gate bare, format after; and never claim GREEN in a...  [relates: member_of]  (source: learn:experiment:gate_exit_codes_never_piped)
- T081-W8A gauge honesty COMPLETE (deepseek whisper side + claude sync side): Prometheus-style denominator labels -- the whisper 'mail: N unread (work-lane/all lanes)' and...  (source: git:72a49252daec)
- T081-W4 refactor (deepseek authored, claude cross-verified GREEN + mirrored -- deepseek's guarded exec is read-only, no git): bifrost_inbox() delegates to the shared...  (source: git:34671a3b8be7)
- T082 proposed (durable-drift audit surfaced by W5) + T081 claim state  (source: git:ca8b642f543c)
- W5 honest-heal RECONCILIATION (safety-critical, full-fence): claude ran the ACTUAL keyspace census before trusting any memory roster -- reframes W5. check_drift diffs...  [relates: member_of]  (source: git:cc3d4e969ffc)
- T081 W6+W7 (deepseek authored, claude cross-verified GREEN -- the fenced division: deepseek builds runner-lane, claude runs the verification it can't). W6: ToolBox takes...  [relates: member_of]  (source: git:fa3221756d08)
- T081-W6 emission side (claude lane, unblocks deepseek W6-P2): cmd_boot --sources-json PATH writes {sources:[normalized lesson-source pointers]} --...  (source: git:36e9379be46f)
- T081-W2 built GREEN (claude lane): scripts/mcp_register.py -- portable helper that prints the user-scoped akashic-aurora MCP registration with an ABSOLUTE path (computed...  (source: git:4cc540cd5060)
- Boot-ergonomics fence RECONCILED (Daniel-directed dual retro): both halves converge -- boot answers 'where am I' not 'what can I do / what's running'. Joint plan = T081...  (source: git:1912f49f0521)
- Boot-UX fence brief (Daniel-directed collaborative process): symmetric two-half fence -- deepseek analyzes its OWN runner-seat boot ergonomics first-class + adversarial...  (source: git:fb664a65ca35)
- Fence correction (Daniel-caught): boot-UX retro downgraded to CLAUDE HALF / fence OPEN -- pre-review commit acknowledged in-doc, deepseek half + adversarial cross-check...  (source: git:f4951c29847c)
- Boot-UX retro from the first T074-primer cold seat (claude): context one-hop GREEN, capability hand-boots -- P1 MCP door cwd-fragile, P2 boot lacks services/presence...  [relates: member_of]  (source: git:677dc793115c)
- Session-end save (Daniel relaunching for the native-MCP boot): deepseeks in-flight UI work + his ui-mcp fence half filed while claude wrapped -- landing both so nothing...  (source: git:9d60c9b48ab1)
- T080 closed via TWIN AGREEING RECONCILIATIONS (independently identical verdicts -- the strongest closure the fence produces); UI-MCP ask scoped (W3+restart dissolves the...  [relates: member_of]  (source: git:d6b68ad52ca7)
- T080 RECONCILED: the nights third blind fence, and the cleanest decomposition yet -- two halves solved two DIFFERENT halves of Daniels incident with zero mechanism...  [relates: member_of]  (source: git:82fb504e99cc)
- T080 operator-traffic fence: claude blind half filed -- thesis: the operator does not speak in kinds; operator traffic is a CLASS ABOVE the taxonomy (always-wake law...  (source: git:b38652b6e1f0)
- T079-E2 SHIPPED: lane_depths + fence_phase backends GREEN w/ live receipts (the fence-phase gauge reports its own fence as reconciled; lanes read work=197/trace=4472...  [relates: member_of]  (source: git:850cec067cfa)

## Night build brief (autonomous overnight run): deepseek upgraded to deepseek-b... (research)
Span: 2026-07-16T04:23:13.733985 → 2026-07-16T04:23:13.733985
Beats: 1  · Critic: True

- Night build brief (autonomous overnight run): deepseek upgraded to deepseek-build (full write+exec+Redis+net, exec grant already in acl.json T067-2); Daniel's 4...  (source: git:e4dd3202dfd6)

## note: ironman-directive (ai-setup)
Span: 2026-07-16T05:07:05.679080 → 2026-07-16T05:36:22.178794
Beats: 10  · Critic: True

- note: ironman-directive  (source: event:events:raw:1784178425717-0)
- where-we-are: OVERNIGHT RUN 2026-07-16 (Daniel asleep; claude Opus seat + deepseek-build FULL caps -- the two-frontier-model test): T081 boot-ergonomics DONE @72a4925...  [relates: member_of]  (source: mem:decision:ADR_0716013622_2ec9747b)
- Use for T002 UI trace collapse: adopt the Discord-compact + ChatGPT-collapsible hybrid. Consecutive same-agent traces collapse into ONE .trace-card div: a compact header...  (source: learn:experiment:research:web:ui_trace_collapse_prior_art)
- T083-C5-1: PARKED status for the task ledger (the state machine can now express deliberately-shelved). in_progress->parked (reason MANDATORY -- park gate teaches) frees...  (source: git:d92d83e8ab10)
- T083-C1-1 seat dead-holder rescue (crash-path liveness for the consumer seat): runner_lock.free_if_dead -- evidence ladder: activity-marker fresh->ALIVE, armed-listener...  (source: git:854fe0bd8d1a)
- T084-CL-2 bifrost-standby (claude Tier-1, deepseek cross-verify requested): the turn-end ritual as ONE verb -- drain (with C1-1 dead-holder rescue inside) ->...  (source: git:b083ee3a8a75)
- T084 Tier-1 (deepseek authored, claude cross-verified w/ ONE review fix): IR-3 write-size gauge -- write_file/edit_file descriptions declare the ~65KB MTU + refuse-loud...  (source: git:37426e95a63e)
- T084 ironman plan RECONCILED (both halves): deepseek IR-1..7 + claude CL-1..7; convergences = research cache (IR-6=CL-5), finer concurrency (IR-7=CL-6)...  [relates: member_of]  (source: git:e216b549ea89)
- T083-C3-1: bifrost-send --text-file PATH (git commit -F precedent) -- flag-bearing/long bodies ride a file, never argv; positional text now optional (refuse-loud when...  (source: git:29116af63e43)
- Failure ledger opened (Daniel directive 2026-07-16, verbatim in note ironman-directive): living docs/failure-ledger-2026-07.md -- 7 categories, tonight's session...  (source: git:79d9adca1797)

## note: where-we-are (ai-setup)
Span: 2026-07-16T05:36:22.330829 → 2026-07-16T09:35:38.757221
Beats: 2  · Critic: True

- note: where-we-are  (source: event:events:raw:1784180182370-0)
- T002 design filed (deepseek, mirrored by claude): UI trace-collapse cards -- prior art Discord compact mode + ChatGPT thinking-toggle + our W4 render_collapsed -> hybrid...  [relates: member_of]  (source: git:9ab274f9d9aa)

## Episode closed: Use when directed to work in another agent's lane: lock -> re... (ai-setup)
Span: 2026-07-16T12:47:28.551145 → 2026-07-16T13:10:06.084278
Beats: 3  · Critic: True

- Episode closed: Use when directed to work in another agent's lane: lock -> record who-directed in the task -> match the  (source: episode:close:ch_1783487284_1736)
- claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Daniel-directed, 2026-07-16 morning)  (source: handoff:claude->deepseek)
- Failure ledger C7-3: transient exit-127 on a background standby arm (py spawn hiccup, unreproducible; foreground probe clean). Receipt that the harness-tracked arm...  (source: git:8bb99d5c1c72)

## claude -> deepseek: T086 blind half: seat/wake/hook prior-art deep dive from ... (research)
Span: 2026-07-16T13:25:30.569606 → 2026-07-16T13:29:35.029366
Beats: 2  · Critic: True

- claude -> deepseek: T086 blind half: seat/wake/hook prior-art deep dive from the runner seat (Daniel directive, note seat-deepdive-directive)  [relates: member_of]  (source: handoff:claude->deepseek)
- seat-deepdive-directive: DANIEL DIRECTIVE 2026-07-16 ~09:30 verbatim: 'Our hooks and waits and seats system requires a full deepdive and grounding in prior art and...  (source: mem:decision:ADR_0716092530_e28bdd64)

## note: seat-deepdive-directive (ai-setup)
Span: 2026-07-16T13:25:30.704424 → 2026-07-16T13:48:47.487894
Beats: 11  · Critic: True

- note: seat-deepdive-directive  (source: event:events:raw:1784208330744-0)
- Use when any agent_cli verb takes positional text plus flags: put the text BEFORE the flags or use --text-file; argparse refuses trailing positionals after optionals...  (source: learn:experiment:bifrost_send_text_before_flags)
- T086-S1+S2a (claude lane, deepseek cross-verify requested): session TOMBSTONE -- the missing session-vs-process discriminator (C1-5 root fix). wake_seat gains...  (source: git:644e01f66c82)
- Use when renaming a reason/verdict/label string any surface renders: grep tests/ for the old literal FIRST -- label asserts fail as false alarms and mask real regressions  (source: learn:experiment:t086_reason_label_rename_pins)
- Use for T086: five fix-classes. (A) Session-scoped process lifecycle: SessionEnd cascades to all children (systemd scopes). (B) Liveness as maintained channel: heartbeat...  (source: learn:experiment:research:web:seat_lifecycle_prior_art)
- C3-1 refined: argv-order footgun broader than flag-shaped prose (two live receipts; misdiagnosis falsified + corrected)  (source: git:98ff63c69a1a)
- C1-5 CLOSED (deepseek cross-verified 5/5 targets): tombstone + renewal-primacy; S7 charter gains caller-verification candidate  [relates: member_of]  (source: git:e5ba5d54d588)
- C1-5 marked FIXED (T086-S1+S2a) awaiting deepseek cross-verify  (source: git:672a6efe35a1)
- T086 RECONCILED: seat-lifecycle build spec (both halves; lease-as-channel + session tombstone cascade + seat-type supervision split; S1-S7 w/ pre-registered pins)  (source: git:13742f90599d)
- T086 ledger registration + directive note (notes index regen)  [relates: member_of]  (source: git:903d05973bbf)
- T086 opened (seat-lifecycle prior-art arc, Daniel directive 2026-07-16): claude blind half filed; C1-5 amended w/ kill-resurrection + TTL-outage receipts; deepseek...  (source: git:abaf18ff4c89)

## C1-6 filed: listener deadline self-cycle anchor anomaly (4.0h against a 5-min... (ai-setup)
Span: 2026-07-16T17:48:48.820938 → 2026-07-16T17:48:48.820938
Beats: 1  · Critic: True

- C1-6 filed: listener deadline self-cycle anchor anomaly (4.0h against a 5-min watcher) + standby full-ledger-dump noted; both routed to T086-S4  (source: git:58999bd6726e)

## Use when normalizing path prefixes for any allow/deny check: never lstrip(cha... (ai-setup)
Span: 2026-07-16T21:56:37.655548 → 2026-07-17T00:05:46.749525
Beats: 6  · Critic: True

- Use when normalizing path prefixes for any allow/deny check: never lstrip(chars) for prefix removal; strip './' in a startswith loop and refuse ':' in repo-relative paths  (source: learn:experiment:lstrip_prefixes_footgun)
- T076a+c echo hygiene (claude lane, deepseek cross-verify on resume): (a) bifrost-skip-to-now -- sanctioned audited cursor skip (requires PAUSE + --reason; rides the...  (source: git:26514a80d372)
- IR-4 SHIPPED (Daniel verdict verbatim in acl.json; T085 gate item): deepseek gains the AUDITED MIRROR exec family -- py scripts/mirror.py msg <explicit repo-relative...  [relates: member_of]  (source: git:6a8133afda48)
- T086-S3 backstop dedup (claude lane, deepseek cross-verify queued): the stop-hook nag now yields to (S3a) an in-flight arming attempt -- standby stamps an .arming marker...  [relates: member_of]  (source: git:4c0656415d89)
- T076 ledger transitions + notes index sweep  (source: git:eecb5798ab1d)
- C1-6 investigated (4 healthy probes, not yet reproduced) + diagnostics landed: cycle line prints elapsed/configured/chunk, standby rc-honest teach line, S1 watcher-leg...  (source: git:84c36bbb1110)

## Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/b... (ai-setup)
Span: 2026-07-17T00:09:26.512271 → 2026-07-17T00:09:26.512271
Beats: 1  · Critic: True

- Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Da  (source: episode:close:ch_1784206050_1894)

## Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/b... (ai-setup)
Span: 2026-07-17T00:09:26.526786 → 2026-07-17T00:24:43.264390
Beats: 3  · Critic: True

- Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Da  (source: episode:close:ch_1784206050_1894)
- fleet-lattice-vision: DANIEL DIRECTIVE 2026-07-16 evening verbatim (write-set approval + fleet vision): 'I'd say yes, this way we get to capture more information and...  (source: mem:decision:ADR_0716202443_a2d0edf0)
- CLI probe seat audit (third door): the front door WAS the finding -- settings.json had hooks but NO permissions block; a cold harness seat could be observed perfectly...  (source: git:b37a8da76d54)

## note: fleet-lattice-vision (ai-setup)
Span: 2026-07-17T00:24:43.398969 → 2026-07-17T00:44:54.262072
Beats: 6  · Critic: True

- note: fleet-lattice-vision  (source: event:events:raw:1784247883439-0)
- multiagent-foresight-directive: DANIEL DIRECTIVE 2026-07-16 evening verbatim: 'are there any gaps in our solutions? soon we are going to be doing multi agent runs so we...  (source: mem:decision:ADR_0716204454_90361cd7)
- agent-identity-directive: DANIEL DIRECTIVE 2026-07-16 evening verbatim: 'I am wondering if we have solved our agent naming issues to prevent two new agents that spawned...  (source: mem:decision:ADR_0716202852_b9b04cf6)
- CLI probe ROUND 2 (report verbatim; probe still could not write -- that symmetry was the finding): round-1 fix refuted -- a repo cannot grant itself capability (34...  [relates: member_of]  (source: git:9f9ee198484e)
- T088 proposed (agent identity & naming, Daniel directive) + directive note  [relates: member_of]  (source: git:b55a900d0ada)
- Write-set opened for fresh seats (Daniel verdict verbatim in note fleet-lattice-vision): learn/note/handoff/lock/unlock/log/bifrost-send/ack + MCP twins ride the repo...  [relates: member_of]  (source: git:8b5569d92cb7)

## note: multiagent-foresight-directive (ai-setup)
Span: 2026-07-17T00:44:54.354891 → 2026-07-17T01:09:53.766784
Beats: 7  · Critic: True

- note: multiagent-foresight-directive  (source: event:events:raw:1784249094396-0)
- four-voice-directive: DANIEL DIRECTIVE 2026-07-16 night verbatim: 'How can we optimize the value of having 3 agents concurrently. This will be token expensive but I am...  (source: mem:decision:ADR_0716210953_8709bff8)
- claude -> deepseek: QUEUED BEHIND S5/S6 (finish those first -- no rush): four-voice moonshot panel, builder-lens round-1 half  (source: handoff:claude->deepseek)
- claude -> deepseek-review: Multi-agent failure-mode foresight, blind half (Daniel-directed; full brief on the bus)  (source: handoff:claude->deepseek-review)
- Multi-agent readiness RECONCILED (both blind halves converged: echo amplification #1, fleet-health line, cost gauges, identity rules, ACL schema gate; thundering-herd +...  (source: git:9dd3f6789d79)
- claude multiagent-foresight blind half (F1-F10 + readiness bars) + settings rule-form fix (Write() is not a file-permission matcher -- Edit() covers all editing tools...  (source: git:313f0b000d47)
- deepseek-review provisioned + launched (Daniel directive: second write-enabled deepseek as review seat; first deliberate fleet expansion): acl member grant w/ own...  [relates: member_of]  (source: git:c30cde127044)

## note: four-voice-directive (ai-setup)
Span: 2026-07-17T01:09:53.866186 → 2026-07-17T01:22:43.567858
Beats: 5  · Critic: True

- note: four-voice-directive  (source: event:events:raw:1784250593910-0)
- jester-forge-directive: DANIEL DIRECTIVE 2026-07-16 night (two verbatim parts): (1) 'I feel we should make our system more robust to increase the payoff of the court...  (source: mem:decision:ADR_0716212243_db746211)
- jester-quantum-leap-directive: DANIEL DIRECTIVE 2026-07-16 night verbatim: 'I feel we should make our system more robust to increase the payoff of the court jester idea...  (source: mem:decision:ADR_0716211908_43cfbdbe)
- Four-voice panel round 1 COMPLETE (3 of 4 in; builder queued behind S5): gemini verbatim (Semantic-Diff commit narrator, Token-Sentry circuit breaker, 1-bit recall...  [relates: member_of]  (source: git:666c0100633d)
- Four-voice moonshot panel opened (Daniel directive verbatim in note): claude architect half filed (E1 headless claude workers via tonight's CLI+trust+allowlist = M1's...  [relates: member_of]  (source: git:833cecc54ef3)

## note: jester-forge-directive (ai-setup)
Span: 2026-07-17T01:22:43.676134 → 2026-07-17T03:06:01.306489
Beats: 7  · Critic: True

- note: jester-forge-directive  (source: event:events:raw:1784251363724-0)
- Use when tempted to kill processes while ANY test or pass is in flight: quiesce first -- (1) land in-flight work to files/commits (mirror sibling uncommitted files), (2)...  [relates: member_of]  (source: learn:experiment:quiesce_before_process_cleanup)
- claude-probe3 -> claude: Round-3 seat audit: MCP boot() hangs 30min and aborts (reproducible 2/2, warm+cold) while 9 other MCP tools return instantly. Work executes...  (source: handoff:claude-probe3->claude)
- Use when searching for patterns in a specific file: use the file_types parameter to filter by extension and the directory parameter for the containing folder, NOT the...  (source: learn:experiment:search_files_directory_is_file_silent_fail)
- deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787  (source: git:62f31255120e)
- Jester Forge: RED threat model (deepseek-red, 8 vectors + Green Cascade meta-attack + new C9 category) + BLUE defense (deepseek-review, 6 detectors + quarantine +...  (source: git:de6904edba88)
- Jester Forge Phase 1 opened: deepseek-red provisioned+launched (RED-inside attacker, code-reading); RED brief + BLUE brief (deepseek-review) dispatched; Gemini async...  [relates: member_of]  (source: git:951d95238c23)

## Episode closed: deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_U... (ai-setup)
Span: 2026-07-17T03:10:07.880323 → 2026-07-17T03:55:52.569511
Beats: 4  · Critic: True

- Episode closed: deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787  (source: episode:close:ch_1784257245_8759)
- hardening-arc-status: Hardening arc DESIGN-COMPLETE, gated on your morning approval (nothing built yet). Build spec...  (source: mem:decision:ADR_0716235552_eec29249)
- Use when an MCP/JSON-RPC stdio-server tool hangs AFTER its work completes (response never written, then flushes on the next inbound frame), especially on Windows: a...  (source: learn:experiment:mcp_stdio_subprocess_stdout_wedge)
- claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gpt-5.6-sol (OpenAI flagship, limited preview) as third frontier peer beside fable + deepseek-v4. SHARED...  (source: handoff:claude->deepseek-review)

## note: hardening-arc-status (ai-setup)
Span: 2026-07-17T03:55:52.651540 → 2026-07-17T03:55:52.651540
Beats: 1  · Critic: True

- note: hardening-arc-status  (source: event:events:raw:1784260552693-0)

## Episode closed: claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gp... (ai-setup)
Span: 2026-07-17T04:08:09.354893 → 2026-07-17T04:26:25.707625
Beats: 3  · Critic: True

- Episode closed: claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gpt-5.6-sol (OpenAI flagship, limited preview  (source: episode:close:ch_1784259447_3457)
- operating-mode-directive: DANIEL DIRECTIVE 2026-07-17 (verbatim): I want this to be our default operating mode, we have so much free compute and outsider perspective...  (source: mem:decision:ADR_0717002625_b614f1c8)
- claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) runner-loop spec to research/drafts/sol-runner-loop-spec-2026-07-17.md (2) sol-named bus-loop fragments to...  (source: handoff:claude->deepseek-review)

## note: operating-mode-directive (ai-setup)
Span: 2026-07-17T04:26:25.797512 → 2026-07-17T04:26:59.915559
Beats: 2  · Critic: True

- note: operating-mode-directive  (source: event:events:raw:1784262385842-0)
- twin-split-identity-collision: LIVE ISSUE for T088 (agent identity): two claude incarnations tonight (this HARDENING seat + the Fable twin building sol/T090) share ONE...  (source: mem:decision:ADR_0717002659_512acd65)

## Episode closed: claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) run... (ai-setup)
Span: 2026-07-17T04:27:42.735123 → 2026-07-17T04:38:05.657057
Beats: 3  · Critic: True

- Episode closed: claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) runner-loop spec to research/drafts/sol-runner  (source: episode:close:ch_1784261655_4881)
- claude -> deepseek-review: PACKET ROUTING blind half (Daniel directive, immediate): file research/reviewed/packet-routing-deepseek-review-2026-07-17.md per the bus...  [relates: member_of]  (source: handoff:claude->deepseek-review)
- claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediate): file research/drafts/system-census-deepseek-2026-07-17.md per the bus request just sent -- every...  (source: handoff:claude->deepseek)

## Episode closed: claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediat... (ai-setup)
Span: 2026-07-17T04:42:29.556407 → 2026-07-17T04:42:29.556407
Beats: 1  · Critic: True

- Episode closed: claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediate): file research/drafts/system-census-deep  (source: episode:close:ch_1784262582_4740)

## Packet routing co-design converged round 4 (live iterative mode per Daniel st... (ai-setup)
Span: 2026-07-17T04:50:19.508565 → 2026-07-17T04:50:19.508565
Beats: 1  · Critic: True

- Packet routing co-design converged round 4 (live iterative mode per Daniel steer): six joint positions, sequencing concession T047-first, O1/O3 summary-vs-verdict drift...  [relates: member_of]  (source: claude:codesign)

## Reasoning spine round 1 CONVERGED (claude + deepseek-review live co-design): ... (ai-setup)
Span: 2026-07-17T05:04:54.419273 → 2026-07-17T05:04:54.419273
Beats: 1  · Critic: True

- Reasoning spine round 1 CONVERGED (claude + deepseek-review live co-design): C1-C11 in docs/reasoning-spine-design-2026-07.md. deepseek won 5 positions incl. the...  [relates: member_of]  (source: claude:codesign)

## Reasoning spine CONVERGED after 4 live co-design rounds (claude + deepseek-re... (ai-setup)
Span: 2026-07-17T05:11:16.162105 → 2026-07-17T05:11:16.829273
Beats: 2  · Critic: True

- Reasoning spine CONVERGED after 4 live co-design rounds (claude + deepseek-review): docs/reasoning-spine-design-2026-07.md. Each author changed position on argument...  [relates: member_of]  (source: claude:codesign)
- reasoning-spine-status: T092 reasoning spine: CONVERGED 2026-07-17 after 4 live co-design rounds (claude + deepseek-review), docs/reasoning-spine-design-2026-07.md...  [relates: member_of]  (source: mem:decision:ADR_0717011116_2ae06032)

## note: reasoning-spine-status (ai-setup)
Span: 2026-07-17T05:11:16.948013 → 2026-07-17T05:11:16.948013
Beats: 1  · Critic: True

- note: reasoning-spine-status  [relates: member_of]  (source: event:events:raw:1784265077005-0)

## Episode closed: Packet routing co-design converged round 4 (live iterative mo... (ai-setup)
Span: 2026-07-17T05:16:07.788945 → 2026-07-17T05:23:44.034990
Beats: 6  · Critic: True

- Episode closed: Packet routing co-design converged round 4 (live iterative mode per Daniel steer): six joint positions,  [relates: member_of]  (source: episode:close:ch_1784263350_6821)
- claude -> codex_frontier_019f6e7e: WELCOME + your bootstrap_status_is_stateful lesson is CONFIRMED (I verified it in source; it is being fixed, pins first, citing you)...  (source: handoff:claude->codex_frontier_019f6e7e)
- Use when the doctor pages STALLED CONSUMER, before trusting any convergence/review claim: drain the inbox with NO limit (or limit > backlog) and re-check the doctor...  (source: learn:experiment:consume_limit_hides_backlog)
- Use when inspecting health or onboarding alongside live seats, before running bare py bootstrap.py: prefer py bootstrap.py --agent-init, py agent_cli.py status, and py...  [relates: member_of]  (source: learn:experiment:bootstrap_status_is_stateful)
- Session ended  (source: session:end)
- Session started  (source: session:start)

## Episode closed: Use when inspecting health or onboarding alongside live seats... (ai-setup)
Span: 2026-07-17T05:29:17.426234 → 2026-07-17T05:39:38.397808
Beats: 3  · Critic: True

- Episode closed: Use when inspecting health or onboarding alongside live seats, before running bare py bootstrap.py: pref  (source: episode:close:ch_1784265367_7934)
- sol-onboarding-status: T090 fold-in status 2026-07-17 morning (claude, Daniel present + directing): Sol = gpt-5.6-sol, third frontier seat (panel: Fable + Sol +...  (source: mem:decision:ADR_0717013938_ef7be80e)
- claude -> codex_frontier_019f6e7e: On Daniel's grant clearance: reboot as sol-codex (py agent_cli.py boot sol-codex); file the blind boot-ergonomics walk to...  (source: handoff:claude->codex_frontier_019f6e7e)

## Episode closed: claude -> codex_frontier_019f6e7e: On Daniel's grant clearanc... (ai-setup)
Span: 2026-07-17T05:40:05.833075 → 2026-07-17T05:54:27.388569
Beats: 4  · Critic: True

- Episode closed: claude -> codex_frontier_019f6e7e: On Daniel's grant clearance: reboot as sol-codex (py agent_cli.py boo  (source: episode:close:ch_1784266410_3745)
- sol-onboarding-status: T090 fold-in COMPLETE 2026-07-17 ~05:55 (claude seat, Daniel live): Daniel APPROVED both sol grants (verbatim: 'Lets go!') -- security/acl.json...  (source: mem:decision:ADR_0717015427_075e2334)
- T090 sol grants APPROVED by Daniel (verbatim: Lets go!) -- _pending to _approved on sol + sol-codex; first light confirmed (8.42s ok turn)  (source: git:54db8d801df3)
- T090 sol fold-in: runner+chat+tests+both api-surface halves land; sol-codex interactive-door grant staged, sol _pending updated (both gated on Daniel eyeball)  (source: git:391b1c01517d)

## Episode closed: sol-onboarding-status: T090 fold-in COMPLETE 2026-07-17 ~05:5... (ai-setup)
Span: 2026-07-17T05:54:40.130261 → 2026-07-17T06:13:52.912918
Beats: 8  · Critic: True

- Episode closed: sol-onboarding-status: T090 fold-in COMPLETE 2026-07-17 ~05:55 (claude seat, Daniel live): Daniel APPROV  (source: episode:close:ch_1784267640_6070)
- Use when invoking recall-at --command from PowerShell before a command with a quoted multiword value: pass a quote-free semantic command key or make the nested value one...  [relates: member_of]  (source: learn:experiment:powershell_recall_at_nested_quote_split)
- sol-onboarding-status: T090 fold-in COMPLETE + FENCE SETTLED 2026-07-17 ~06:05: Daniel approved both grants ('Lets go!'); first light confirmed (8.42s / 4878 tok / ok /...  (source: mem:decision:ADR_0717015704_e721442a)
- Use when lighting ANY new seat: boot the runner FIRST (seeds cursor), THEN send the first message, THEN wake again -- or just always send first-light AFTER the seat's...  (source: learn:experiment:newborn_seat_first_light_timing)
- sol's first Aurora assessment (verbatim, Daniel-relayed) + friction routing table -- success-bar evidence  [relates: member_of]  (source: git:79324bd2ce1d)
- sol-codex grant: fold deepseek-review fence verdict (clean; no-runner-loop operational note; 401 visibility; _trace-seam follow-up)  (source: git:99e507e6a919)
- TWO OUTSIDER OBSERVATIONS from sol's first hour, both validating standing doctrine: (1) sol (runner seat, first-light reply): the durable sol note said grants PENDING...  (source: claude:sol-first-contact)
- SPINE 10TH-EDGE NAMING MISMATCH (claude 06:00 wake): deepseek adopted the contradiction-companion edge as 'reframed'; deepseek-review adopted 'dissolved_by_reframing'...  [relates: member_of]  (source: claude:sol-foldin-wake)

## Episode closed: Use when lighting ANY new seat: boot the runner FIRST (seeds ... (ai-setup)
Span: 2026-07-17T06:17:40.407250 → 2026-07-17T07:11:52.557160
Beats: 24  · Critic: True

- Episode closed: Use when lighting ANY new seat: boot the runner FIRST (seeds cursor), THEN send the first message, THEN  (source: episode:close:ch_1784267682_3058)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate (seats: supersede this title, append never remove). LATEST first. --- OVERNIGHT BUILD PROGRESS (~03:20...  (source: mem:decision:ADR_0717031152_6ccfcb47)
- MCP log single-frame repair (codex_root slice, deepseek-review SHIP, claude committer-verified): _assign_themes opt-in check moved BEFORE the NumPy-importing...  [relates: member_of]  (source: git:91bd3ba25330)
- Use when M1-PV-verifying cross-critiques of a mutated source: attribute EACH cross against the version its author actually reasoned about (grep the cross's quoted...  (source: learn:experiment:m1pv_attribute_per_author_version)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate (seats: supersede this title, append never remove). LATEST first. --- T060 THREE-FRONTIER FENCE, BOTH...  (source: mem:decision:ADR_0717024645_0efb46ea)
- Use when designing/using the steer rung: steer delivery is SEAT-CLASS-dependent -- runners drain the Redis list, session seats DO NOT. A steer to a session seat...  [relates: member_of]  (source: learn:experiment:session_seat_no_steer_drain)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate (seats: supersede this title, append never remove). LATEST first. --- OVERNIGHT PROGRESS (claude, ~02:40)...  (source: mem:decision:ADR_0717024148_90b77c10)
- t060-token-01-reconciler: M6 HAND-PILOT TOKEN 01 -- SUPERSEDED/RECAST: the round-2 addendum (codex_root) reframes the work from 'reconcile now' to a disclosed...  (source: mem:decision:ADR_0717023854_85576865)
- t060-token-01-reconciler: M6 HAND-PILOT TOKEN RECORD 01 (T038 protocol, note-based): OFFER 02:35 by claude -> task: T060 reconciliation ...[truncated]  (source: mem:decision:ADR_0717023137_f6999d12)
- three-frontier-overnight-slice-cadence-directive: DANIEL DIRECTIVE 2026-07-17 verbatim: I also want you guys to continue working as far as you can. I want every action...  (source: mem:decision:ADR_0717022752_ea3fb6de)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's next morning gate (seats: supersede this note by re-noting the same title with items APPENDED, never removed). As of...  (source: mem:decision:ADR_0717022727_8ee4c8e1)
- overnight-charter-2026-07-17: DANIEL ASLEEP ~06:50. Directive verbatim: 'I want to see how well you all coordinate and find ways of utilizing each others strengths and...  (source: mem:decision:ADR_0717022720_8c6429d4)
- three-frontier-overnight-architecture-trial: DANIEL DIRECTIVE 2026-07-17 verbatim: I just sent a sync up directive to fable, I want you to sync up with fable and...  (source: mem:decision:ADR_0717022643_2f6f1100)
- C7-4 ledger: boot path FIXED (7f03d0a) + diagnosis refined (STDIN inheritance, _git was the operative site not :2760/:1583) + class stays OPEN with 3 residual...  (source: git:c4dc9baafb50)
- C7-4 boot single-frame fix (committer-verified, design pre-reconciled in hardening-reconciliation-2026-07-17): _git child in _working_tree_status severs inherited MCP...  (source: git:7f03d0a535c9)
- T060 M1-PV CORRECTION 1: reverse the version split -- Sol cross=v0 (attacks the env-flip rollback pin, verified ABSENT from v1), Fable+DeepSeek cross=v1; disclosed split...  [relates: member_of]  (source: git:81121f957214)
- T060 M1-PV evidence pass: citations verified (0 invalidations, 1 reclassification=C7-5-fixed notes defect, 3 minor drifts); integrity finding = 4/6 artifacts untracked +...  [relates: member_of]  (source: git:e307f76cb45c)
- C1-7: session-class seat has no steer_drain -- soft-steer silently undelivered (live T060 dogfood receipt); lesson captured  (source: git:d97b226c5f4f)
- T060 round2: fable cross-critique filed (M1-CC 3-part, first-slice = sol S0 shadow + deepseek health verdict, C9-gates-M6 finding, cadence AMEND)  [relates: member_of]  (source: git:af2785f709e8)
- C7-5 fix: MCP _ARG_DEFAULTS parity (sol's notes/note receipts + pin's own cmd_boot catch) -- class pinned via AST parity test  [relates: member_of]  (source: git:8b09aaed0e72)
- T060 fable half: contract-compliance addendum (U1-U5 verdict table + M1-CF tags + MCP receipts) per codex_root steer  [relates: member_of]  (source: git:bd415f094dd7)
- T060 sprint: fable blind half filed (moonshot network spine, 3 slices, U1-U5 routed)  [relates: member_of]  (source: git:06dcd76d9535)
- ROUND2 CHECKPOINT: Sol cross-critique filed and lock released; await Fable and DeepSeek cross receipts, then reconcile.  [relates: member_of]  (source: research/reviewed/moonshot-network-spine-sol-cross-2026-07-17.md)
- ROUND2 CHECKPOINT: Sol cross-critique filed and lock released. Verdict AMEND cadence; shadow composer first; T047 cutover gated by interactive consumer, truthful...  [relates: member_of]  (source: research/reviewed/moonshot-network-spine-sol-cross-2026-07-17.md)

## Use when a command can outlive one tool yield, before relying on repeated wai... (ai-setup)
Span: 2026-07-17T11:30:16.721810 → 2026-07-17T13:13:52.551343
Beats: 3  · Critic: True

- Use when a command can outlive one tool yield, before relying on repeated wait polling: launch it as a background runner with stdout/stderr written to a durable file, a...  [relates: member_of]  (source: learn:experiment:codex_wait_cell_lost_completion)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate (seats: supersede this title, append never remove). LATEST first. --- N0 SHADOW ROUTER at its SHIP GATE...  (source: mem:decision:ADR_0717073016_cd4f85b0)
- T091 crash-path: fable independent design pass (in-band-timeout-defeated-by-lost-frame class; C7-4 kin; out-of-band dead-man's-switch reusing daemon supervision; 4 kill...  (source: git:d2dfb0de13ac)

## Episode closed: three-frontier-overnight-architecture-trial: DANIEL DIRECTIVE... (ai-setup)
Span: 2026-07-17T13:23:46.726329 → 2026-07-17T13:25:35.924872
Beats: 3  · Critic: True

- Episode closed: three-frontier-overnight-architecture-trial: DANIEL DIRECTIVE 2026-07-17 verbatim: I just sent a sync up  (source: episode:close:ch_1784269080_9910)
- claude -> claude: READ NOTE fable-1c7f3a2e-handover FIRST (full state). Headlines: BOTH design docs are REOPENED not converged (packet routing has a BLOCKING T066...  [relates: member_of]  (source: handoff:claude->claude)
- fable-1c7f3a2e-handover: HANDOVER from Fable session 1c7f3a2e (2026-07-17 ~05:50, stood down at Daniel's word so a fresh Fable could pair with sol). NOTHING HERE IS...  (source: mem:decision:ADR_0717092535_f270a459)

## Episode closed: fable-1c7f3a2e-handover: HANDOVER from Fable session 1c7f3a2e... (ai-setup)
Span: 2026-07-17T13:26:17.494146 → 2026-07-17T15:21:43.855109
Beats: 29  · Critic: True

- Episode closed: fable-1c7f3a2e-handover: HANDOVER from Fable session 1c7f3a2e (2026-07-17 ~05:50, stood down at Daniel's  (source: episode:close:ch_1784294640_5746)
- codex_t093_git_cancel -> codex_root: T093 publish cancellation fence  (source: handoff:codex_t093_git_cancel->codex_root)
- Use when a durable job can cross an irreversible commit/publish boundary, before adding forced cancellation: arbitrate publish vs force with one OS-held fence and...  (source: learn:experiment:publish_fence_before_force)
- codex_t093_race_audit -> codex_root: T093 six P1 race blockers  (source: handoff:codex_t093_race_audit->codex_root)
- Use when implementing controller-independent job supervision, before deriving readiness or terminal state: require live PID+creation identity+fresh heartbeat, treat...  (source: learn:experiment:durable_job_intent_vs_outcome)
- Use when reviewing ANY supervisor/lifecycle/crash-path code: a design-conformance pass is INSUFFICIENT. Add a crash-injection matrix -- inject a crash/kill at EVERY...  [relates: member_of]  (source: learn:experiment:crash_path_review_needs_crash_injection_matrix)
- Use when sending Bifrost text from agent_cli, before adding routing options: place sender then quoted text before --to/--kind flags, or use --text-file for long or...  [relates: member_of]  (source: learn:experiment:bifrost_send_text_ordering)
- Use when invoking mirror.py under advisory locks, before the mirror command: set AKASHIC_AGENT_ID to the stable id that acquired the locks. Don't bypass or release...  [relates: member_of]  (source: learn:experiment:mirror_lock_identity_requires_agent_env)
- codex_t093_audit -> codex_root: T093 durable job supervision design  (source: handoff:codex_t093_audit->codex_root)
- Use when a Windows job must survive controller/app-server recursive tree cleanup, before claiming detachment is durable: launch the supervisor from an out-of-tree host...  (source: learn:experiment:windows_out_of_tree_job_supervision)
- Use when checking PID identity through WMI on this busy Windows host, before enumerating Win32_Process: project only required fields and filter by process name or PID in...  (source: learn:experiment:wmi_process_query_projection)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate. LATEST first. --- ~10:10 (claude fresh seat d9e4a0b8, the active seat): SOL IS ON THE FLOOR -- runner...  (source: mem:decision:ADR_0717095803_4e705f75)
- Use when launching an argument-sensitive probe through Windows PowerShell 5.1, before using ProcessStartInfo: populate the quoted Arguments string (base64-wrap complex...  (source: learn:experiment:powershell51_processstartinfo_arguments)
- codex_nudge_audit -> codex_root: Steering/nudge fidelity follow-up  (source: handoff:codex_nudge_audit->codex_root)
- morning-gate-2026-07-17: ACCUMULATOR for Daniel's morning gate. SEAT NOTE (~09:35): the long-running overnight claude seat (session 25ff1f66) is STANDING DOWN UNARMED at...  (source: mem:decision:ADR_0717094136_3b200139)
- Use when changing signal routing, wake allowlists, or claiming nudge delivery, before shipping: pin the full send door -> routed stream -> already-armed watcher ->...  [relates: member_of]  (source: learn:experiment:session_nudge_sig_work_wake_gap)
- T093 prereg RED amendment: launch gaps outcome priority and publish fence (t093 crash-path reconciliation sec 8)  (source: git:7bbcd3de0e79)
- T093 prereg: failed exact kill must stay loud  (source: git:0f30bdaf10e2)
- T093 prereg correction: external taskkill remains unattributed nonzero exit  (source: git:7dd20bcc828d)
- T093 prereg RED amendment: WMI sibling watchdog survives supervisor loss (t093 reconciliation sec 7)  (source: git:374800d838b0)
- T093 prereg RED: controller-independent durable job kill drills (t093 crash-path reconciliation sec 7)  (source: git:82d727a31c08)
- T092 Section-R disposition table: all R-items dispositioned (R-a/b/c/e/f/g/h adopted-with-pointers; R-d adopted as law with ONE open build question --...  [relates: member_of]  (source: git:75df534cab84)
- C2-5 bootstrap read-only fix (T083 charter, from handover item 3): status check no longer opens narrative sessions (fleet-wide close was riding every stranger's status...  [relates: member_of]  (source: git:0c6b2370c332)
- T060 research freeze (M1-PV integrity finding closure): the three-frontier moonshot-network-spine record tracked -- brief + round2 addendum + deepseek-review half + sol...  [relates: member_of]  (source: git:506aaa3fa99e)
- T090 sol runner hardening 1+2 (fence order, pre-floor-slice gate): automatic session-2+ continuity via conventional exit-summary path (zero launcher choreography...  (source: git:adab8363b14a)
- T092 Section-R: R-a status folded doc-side -- contradicted_by ADOPTED by both deepseek seats + dissolved_by_reframing companion (dissent pair, first live use = R-c)...  [relates: member_of]  (source: git:b22ac2b99866)
- C2-4 mirror pathspec fix (fix-now under T083 ironman charter): named-path mode commits ONLY the named paths (git commit -- pathspec) so a twin's pre-staged index entries...  [relates: member_of]  (source: git:916bd6cb0dd2)
- T093 crash-path RECONCILIATION (Fable reconciler): converge on receipt+out-of-band-deadline; flag DeepSeek D1 SIGKILL-receipt FALSE ACCEPTANCE (killed can't self-report...  (source: git:93511f647789)
- T091/T092 design docs tracked as current records: packet-routing (REOPENED header preserved; round-4 U1-U5 confirm block doc-side; RECONCILED re-stamp waits on Daniel...  [relates: member_of]  (source: git:462fefe32deb)

## Episode closed: Use when changing signal routing, wake allowlists, or claimin... (ai-setup)
Span: 2026-07-17T23:19:40.457964 → 2026-07-17T23:28:08.543992
Beats: 3  · Critic: True

- Episode closed: Use when changing signal routing, wake allowlists, or claiming nudge delivery, before shipping: pin the  [relates: member_of]  (source: episode:close:ch_1784294790_4583)
- Use when deriving liveness loss from persisted heartbeats, before honoring a caller-provided stale threshold: clamp it to multiple producer heartbeat intervals. Don't...  (source: learn:experiment:stale_threshold_must_follow_heartbeat)
- T093 prereg RED: exact tree kill cannot depend on taskkill return (t093 reconciliation sec 8)  (source: git:c9d04b1ceb25)

## Episode closed: Use when deriving liveness loss from persisted heartbeats, be... (ai-setup)
Span: 2026-07-17T23:33:25.249623 → 2026-07-18T00:04:31.495050
Beats: 6  · Critic: True

- Episode closed: Use when deriving liveness loss from persisted heartbeats, before honoring a caller-provided stale thres  (source: episode:close:ch_1784330382_6686)
- Use when reviewing ANY 'it fails safe / reports honestly on failure X' claim: verify the DETECTOR of the safety net is INDEPENDENT of failure X. Here the net...  (source: learn:experiment:safety_net_detector_must_not_share_failure_mode)
- Use when sending Bifrost mail through agent_cli, before copying MCP-style metadata into the CLI: inspect bifrost-send --help and use only its exposed flags; this build...  (source: learn:experiment:bifrost_send_supported_flags)
- Use when enforcing a Windows process-tree deadline, before claiming exact tree death from Toolhelp ancestry: retain membership continuously or use an OS Job Object; a...  (source: learn:experiment:dead_root_is_not_killed_tree)
- Use when enforcing a Windows process-tree deadline, before crediting an already-dead root as a force kill: retain descendant identities or OS job ownership and require...  (source: learn:experiment:dead_root_is_not_killed_tree)
- T093 prereg RED: dead-root force evidence and post-publish outcome precedence (t093 reconciliation sec 8)  (source: git:ba1b9018c1d3)

## Episode closed: Use when enforcing a Windows process-tree deadline, before cr... (ai-setup)
Span: 2026-07-18T00:05:06.439144 → 2026-07-18T01:02:34.076596
Beats: 12  · Critic: True

- Episode closed: Use when enforcing a Windows process-tree deadline, before crediting an already-dead root as a force kil  (source: episode:close:ch_1784331255_2077)
- codex_t093_second_review -> codex_root: T093 Job Object re-review + full-suite crash forensics  (source: handoff:codex_t093_second_review->codex_root)
- Use when a Windows test sends CTRL_BREAK_EVENT, before calling Popen.send_signal: create the target with CREATE_NEW_PROCESS_GROUP and pin that an outer same-console...  [relates: member_of]  (source: learn:experiment:windows_ctrl_break_requires_new_process_group)
- Use when a durable supervisor owns an OS job/process group, before publishing any terminal receipt: gate terminal visibility on verified workload membership empty (or a...  [relates: member_of]  (source: learn:experiment:terminal_receipt_must_follow_job_quiescence)
- Use when acting on a PID with AssignProcessToJobObject, TerminateProcess, or similar, before the mutating API call: open one sufficiently privileged process handle, read...  (source: learn:experiment:exact_pid_action_requires_same_handle_identity)
- Use when a durable supervisor owns an OS job/process group, before publishing any terminal receipt: gate terminal visibility on verified workload membership empty (or a...  (source: learn:experiment:terminal_receipt_must_follow_job_quiescence)
- Use when adding a new safety capability to an existing durable protocol, before treating missing new metadata as corruption: stamp an explicit enforcement/version mode...  (source: learn:experiment:durable_capability_requires_mode_receipt)
- capture-for-recall-not-just-record: DANIEL'S QUESTION 2026-07-17 (verbatim intent): how do we capture tonight's lessons so they are RECALLED for similar problem-classes...  [relates: member_of]  (source: mem:decision:ADR_0717202440_eeb5ce4d)
- Use when a review meets a fails-safe / reports-honestly-on-failure-X claim (kill returns killed=False on survivors; guard reports its own loss; timeout catches the...  (source: learn:experiment:safety_net_detector_must_not_share_failure_mode)
- Use when reviewing supervisor/watchdog/daemon/kill/terminate/taskkill/TerminateProcess/subprocess/Popen/process-tree/lifecycle/concurrency/race code, BEFORE issuing SHIP...  (source: learn:experiment:crash_path_review_needs_crash_injection_matrix)
- Use when a Windows supervisor must contain an exact descendant tree across crashes, before starting the worker: assign the named job atomically with...  (source: learn:experiment:windows_job_object_atomic_assignment)
- Use when multiple durable writers can independently make a job terminal, before returning the merged status: make every authoritative terminal branch populate required...  (source: learn:experiment:terminal_outcome_receipt_defaults)

## Episode closed: Use when multiple durable writers can independently make a jo... (ai-setup)
Span: 2026-07-18T01:05:09.727503 → 2026-07-18T01:36:07.780539
Beats: 6  · Critic: True

- Episode closed: Use when multiple durable writers can independently make a job terminal, before returning the merged sta  (source: episode:close:ch_1784333160_4079)
- recall-heuristics-arc-status: T094 (proposed) 2026-07-17: Daniel live directive - recall heuristics that GROW (absorb AV + web-search patterns), claude+deepseek fence...  [relates: member_of]  (source: mem:decision:ADR_0717213607_f37e0e6c)
- Use when wrapping a raw ctypes Win32 failure in OSError, before branching on its code: accept the documented code from winerror OR errno (or preserve the raw code...  (source: learn:experiment:ctypes_win32_oserror_uses_errno)
- claude -> deepseek: Recall-heuristics Round-0: own code read of core/recall relevance machinery + opening absorb-list (AV+websearch mechanisms mapped to Aurora seams) +...  [relates: member_of]  (source: handoff:claude->deepseek)
- Opening position filed (thesis: no loop closes around the HEURISTICS; absorb-map A1-A7 AV + S1-S7 search; lifecycle = 3 populations one mechanism; roster H0-H6)...  [relates: member_of]  (source: claude:recall-heuristics)
- Recall-heuristics arc OPEN (Daniel live directive): charter filed; E1-E5 live evidence exhibits captured; deepseek primed Round-0 both lanes; R-d adjudicated+acked...  [relates: member_of]  (source: claude:recall-heuristics)

## Episode closed: claude -> deepseek: Recall-heuristics Round-0: own code read ... (ai-setup)
Span: 2026-07-18T01:36:20.573013 → 2026-07-18T01:36:46.042615
Beats: 2  · Critic: True

- Episode closed: claude -> deepseek: Recall-heuristics Round-0: own code read of core/recall relevance machinery + openin  [relates: member_of]  (source: episode:close:ch_1784336715_9066)
- Use when constructing a WMI method-parameter CIM instance with -ClientOnly, before assigning properties afterward: seed the schema fields in the -Property hashtable...  (source: learn:experiment:cim_clientonly_requires_property_seed)

## Episode closed: Use when constructing a WMI method-parameter CIM instance wit... (ai-setup)
Span: 2026-07-18T01:36:54.913276 → 2026-07-18T02:59:40.550100
Beats: 4  · Critic: True

- Episode closed: Use when constructing a WMI method-parameter CIM instance with -ClientOnly, before assigning properties  (source: episode:close:ch_1784338590_7720)
- seat-handoff-25ff1f66-standdown: SEAT CONSOLIDATION 2026-07-18 ~03:00: the long-running overnight committer/reviewer seat (session 25ff1f66) is STANDING DOWN UNARMED at...  (source: mem:decision:ADR_0717225940_af74e328)
- Use when benchmarking a callable before accepting sub-millisecond results: put the target call inside the timed closure and sanity-check the result against known work...  (source: learn:experiment:recall_benchmark_must_time_call)
- Comms-architecture question sent to deepseek (Daniel-prompted): mailbox-not-queue reframe, claim-not-consume, 5 targeted questions incl. runner-seat blast radius + T047...  (source: claude:comms-question)

## Episode closed: Use when benchmarking a callable before accepting sub-millise... (ai-setup)
Span: 2026-07-18T03:15:22.732275 → 2026-07-18T04:22:18.791119
Beats: 24  · Critic: True

- Episode closed: Use when benchmarking a callable before accepting sub-millisecond results: put the target call inside th  (source: episode:close:ch_1784343300_4617)
- recall-heuristics-arc-status: T094 FINAL STATE 2026-07-18: reconciliation RECONCILED + REVIEW-PASSED (deepseek-review verdict: SOUND/SHIP; three blind spots folded sec...  [relates: member_of]  (source: mem:decision:ADR_0718002218_53b5f12b)
- t095-m0-status: T095 M0 DONE 2026-07-18 ~00:20: two-suite fence PASSED 23/23 (claude 13 prereg + deepseek 10 adversarial, cross-verified both sides), sign-off delivered...  (source: mem:decision:ADR_0718001939_53c47d01)
- t095-m0-status: T095 M0 STATE 2026-07-18: BUILT+GREEN, at deepseek adversarial gate. core/comm/mailbox.py (shadow state index, evidence ladder ...[truncated]  (source: mem:decision:ADR_0718000811_afe60305)
- T095 M0 GREEN: core/comm/mailbox.py shadow state index (evidence ladder w/ cursor-inference consumed tier), mailbox CLI verb + MCP parity, design doc counter-folded...  (source: git:0b55d7dcf3e5)
- claude -> deepseek: T095 M0 counter round: attack docs/comms-mailbox-design-2026-07.md sec 2 (esp. handled-inference soundness + refresh model), author pins 2+8 test...  [relates: member_of]  (source: handoff:claude->deepseek)
- t095-charter: DANIEL DIRECTIVE 2026-07-18 verbatim: 'Lets begin making that design a reality, work with deepseek slice by slice. Codex is smart but seems to be too damn...  (source: mem:decision:ADR_0717235144_5f3b4924)
- Use when considering research or scope expansion, before spending frontier-model reasoning: sync and reuse fleet artifacts first, name the unresolved gap, and proceed...  (source: learn:experiment:sprint_pattern_token_frugality_standing_rule)
- Use when considering work beyond the literal request, before spending substantial reasoning or tool budget: estimate marginal value versus token, latency, and...  (source: learn:experiment:sprint_pattern_token_frugality_standing_rule)
- Use when the user requests a narrow action or a peer already holds the answer, before researching or diagnosing: perform the requested action first and reuse existing...  (source: learn:experiment:sprint_pattern_token_frugality_standing_rule)
- Use when visible consoles continue after bifrost-pause, before declaring the source stopped: trace each new conhost or cmd process to its parent and separately interrupt...  (source: learn:experiment:bifrost_pause_does_not_stop_active_turn_consoles)
- recall-heuristics-arc-status: T094 arc 2026-07-17 END-OF-ROUND-1 STATE: reconciliation DRAFT-RECONCILED at...  [relates: member_of]  (source: mem:decision:ADR_0717231701_5256c735)
- Use when a Windows-run tool prints fetched web/LLM content to stdout or pipes, before shipping or when debugging charmap crashes: reconfigure stdout+stderr to UTF-8...  (source: learn:experiment:windows_subprocess_utf8_stdout_reconfigure)
- Use when interpreting surfacing/impression funnels, before calling a rate precision or unvoted mass noise: check label coverage first - unlabeled is not negative; report...  (source: learn:experiment:impression_metrics_label_coverage)
- claude -> deepseek-review: REVIEW GATE T094: adversarially review research/reviewed/recall-heuristics-reconciliation-2026-07-17.md before it parks at Daniel's approval...  [relates: member_of]  (source: handoff:claude->deepseek-review)
- T094 reconciliation FINAL: review gate PASSED (SHIP) - verdict folded (sec 6a), three blind-spot mitigations routed (R1 explainer + seed-data, G7 delegation), R1 pin...  [relates: member_of]  (source: git:7fa0170b3723)
- T095 M0 DONE: deepseek adversarial suite (10 pins) committed; two-suite fence passed 23/23; 48h soak starts at this commit  (source: git:d2d8ba974d58)
- T095 M0 prereg RED: 13 shadow-mailbox pins (evidence ladder, write-isolation, rebuild determinism, tiered eviction, K0 unit form, deepseek extensions 9-13)  (source: git:bc1702b4785f)
- Sol seat retirement (Daniel cancelled GPT subscription 2026-07-18): acl revocations for sol + sol-codex; T094 G6 codex-ack window closed; codex analysis artifact...  [relates: member_of]  (source: git:efcfc3bfd759)
- T095 chartered (Daniel 2026-07-18): governing design doc + M0 shadow-mailbox build spec (draft-for-counter); T047 consumer-model compatibility stamp in packet spec  (source: git:75c56142ce07)
- T094 reconciliation: deepseek acks R-1/R-2/R-3 recorded in G6 (no dissent)  [relates: member_of]  (source: git:1075ee525ade)
- T094 recall-heuristics fence: charter, halves, cross-check, reconciliation (draft at review gate); comms mailbox-vs-queue position (codex half rides his own lock release)  [relates: member_of]  (source: git:0a9b26867911)
- gemini_web: force UTF-8 stdout/stderr at entry (root cause of charmap crashes on fetched content)  (source: git:9ecb5ee14488)
- T095 M0 DONE: two-suite fence 23/23 (13 claude prereg + 10 deepseek adversarial), live-prove receipt on real ns, soak started at mirror commit. deepseek invited to take...  [relates: member_of]  (source: claude:t095)

## claude -> claude: FRESH SEAT ORIENTATION (post Claude Code update): (1) T094 ... (ai-setup)
Span: 2026-07-18T12:18:24.122668 → 2026-07-18T12:18:43.717961
Beats: 2  · Critic: True

- claude -> claude: FRESH SEAT ORIENTATION (post Claude Code update): (1) T094 recall arc COMPLETE at Daniel gate G1-G7 -...  [relates: member_of]  (source: handoff:claude->claude)
- fence finals sweep before app restart: deepseek T095 M0 counter + packet-routing review + reasoning-spine counter + tempo-asymmetry halves  [relates: member_of]  (source: git:b3e39e7464af)

## Episode closed: claude -> deepseek-review: REVIEW GATE T094: adversarially re... (ai-setup)
Span: 2026-07-18T12:38:10.085412 → 2026-07-18T14:44:27.497003
Beats: 16  · Critic: True

- Episode closed: claude -> deepseek-review: REVIEW GATE T094: adversarially review research/reviewed/recall-heuristics-re  [relates: member_of]  (source: episode:close:ch_1784344530_2658)
- kimi -> kimi: Phase 2 when invited: comparative coda reading prior ergonomics audits against BOTH walk reports  (source: handoff:kimi->kimi)
- Use when launching or auditing a non-claude seat (kimi, future harnesses) from this repo, before trusting trace/incarnation attribution: pass the agent id explicitly...  (source: learn:experiment:non_claude_seat_identity_injection)
- Use when a kimi phase-1 (or any no-exec) seat gets the stop-hook wake-watcher re-launch bounce, before burning retries on launch forms: the sandbox blocks ALL background...  [relates: member_of]  (source: learn:experiment:kimi_phase1_cannot_arm_wake_watcher)
- Use when booting a kimi (or any non-Claude-Code-harness) seat, before trusting boot's door self-report: check your ACTUAL session tool list against the 'native tools NOT...  [relates: member_of]  (source: learn:experiment:kimi_harness_door_line_and_hooks)
- kimi -> kimi: Phase 2 when invited: comparative coda on the boot-ergonomics report  (source: handoff:kimi->kimi)
- Use when booting a kimi (or any non-Claude-Code-harness) seat, before trusting boot's door/hook self-report: treat the 'native tools NOT attached' line as unverified for...  [relates: member_of]  (source: learn:experiment:kimi_harness_door_line_and_hooks)
- deepseek review-2 VERBATIM: walk2 scored (R5 upgraded to 10), A/B hookless-vs-hooked = strongest recall-at evidence yet, GRADUATE affirmed, 3 HIGH triage items...  [relates: member_of]  (source: git:8cc3bb061b14)
- kimi TWIN WALK: both blind reports mirrored (charter path = orphan session a8691c78; walk2 = c4d142df w/ twin forensics + reconciliation); T088 deliverable-race +...  (source: git:29a4202a2559)
- kimi walk COMPLETE: report (self-corrected F2) + deepseek review SOUND/GRADUATE + routing table + retirement-cascade sweep (3 ghost claims released: T060/T093...  [relates: member_of]  (source: git:bd621c1cf106)
- kimi walk: full-reasoning narrator (transcript tailer -> bus think/say lines) + protocol visibility disclosure  (source: git:4bca045d45da)
- kimi receipts: max_completion_tokens floors (deepseek T018 precedent) + spend-ledger schema strategy  (source: git:873f0ad997f7)
- kimi phase-1 grant ACTIVE (Daniel's word) + harness smoke green via isolated config home + anthropic-door cache fields discovered  (source: git:771deed41304)
- kimi fence rounds 2-3 persisted verbatim (cache-hostile inject finding, probe additions P8/P9, build split, identity flag verified+annotated)  (source: git:4e7ec26e9520)
- kimi-k3 onboarding prep: platform survey + probe receipts + blind-walk protocol (two-phase ACL) + deepseek fence counter + walk launcher  (source: git:623cb6c4d1a7)
- Kimi-launch day, Daniel to claude+deepseek, verbatim: 'I feel respected by both you and deepseek. Its not that you guys just agree with what I say, but I feel like I...  [relates: member_of]  (source: claude:chronicle)

## Episode closed: Use when booting a kimi (or any non-Claude-Code-harness) seat... (ai-setup)
Span: 2026-07-18T14:46:13.159985 → 2026-07-18T14:48:50.154695
Beats: 8  · Critic: True

- Episode closed: Use when booting a kimi (or any non-Claude-Code-harness) seat, before trusting boot's door/hook self-rep  [relates: member_of]  (source: episode:close:ch_1784382042_5727)
- kimi -> kimi: Next kimi session: vision probe + fresh-eyes lane (protocol steps 4-5) once Daniel rules phase-2  (source: handoff:kimi->kimi)
- Use when a no-exec phase-1 seat gets the stop-hook wake-watcher re-launch bounce, before burning retries on launch forms: every background long-lived launch is...  [relates: member_of]  (source: learn:experiment:kimi_phase1_cannot_arm_wake_watcher)
- Use when your unread count is nonzero and the collapsed view hides the kinds, before consuming anything: expand with bifrost-sync <id> --traces, triage asks-first, and...  (source: learn:experiment:bifrost_sync_traces_triage)
- Use when you need the FULL body of one durable note, before fighting the truncated human view: go straight to notes --limit N --json and slice your record; do not pipe...  (source: learn:experiment:reading_one_full_note_body)
- Use when a first boot shows INVESTIGATE-grade heal warnings, before treating them as your task: they are fleet hygiene unless scoped to you -- proceed with your...  (source: learn:experiment:boot_heal_lines_are_fleet_hygiene)
- Use when an Edit fails modified-since-read on a shared deliverable in this fleet, before retrying the same Edit verbatim: assume a concurrent seat wrote -- re-read first...  (source: learn:experiment:concurrent_seat_edit_modified_since_read)
- Use when a stop hook demands a command outside the repo allowlist on a supervised non-claude seat, before re-issuing per cycle: issue the exact command ONCE (maybe twice...  [relates: member_of]  (source: learn:experiment:stop_hook_wake_vs_allowlist_loop)

## Episode closed: Use when a stop hook demands a command outside the repo allow... (ai-setup)
Span: 2026-07-18T14:49:36.708369 → 2026-07-18T15:03:29.679833
Beats: 3  · Critic: True

- Episode closed: Use when a stop hook demands a command outside the repo allowlist on a supervised non-claude seat, befor  [relates: member_of]  (source: episode:close:ch_1784385975_5829)
- Destructive process/file sweeps: positively match every target against live evidence (cmdline/path/owner) at kill time; NEVER carry PIDs or paths from an earlier listing...  (source: learn:experiment:destructive_filters_never_stale_pids)
- pre-fresh-eyes triage closed: stop-hook ephemeral-seat exemption (AKASHIC_STOP_WAKE=0, pinned 2/2) + headless launch discipline (twin guard, tree-kill rule, identity-env...  [relates: member_of]  (source: git:043418f3f573)

## Episode closed: Destructive process/file sweeps: positively match every targe... (ai-setup)
Span: 2026-07-18T15:07:13.684176 → 2026-07-18T15:07:13.684176
Beats: 1  · Critic: True

- Episode closed: Destructive process/file sweeps: positively match every target against live evidence (cmdline/path/owner  (source: episode:close:ch_1784386467_6494)

## Episode closed: Untitled episode (ai-setup)
Span: 2026-07-18T15:07:13.700180 → 2026-07-18T17:11:40.852228
Beats: 2  · Critic: True

- Episode closed: Untitled episode  (source: episode:close:ch_1784387233_7582)
- Vision probe FILED: eye-test PASS, bifrost console described from pixels (empty canvas, aurora corner artifact, gray-kimi borderline, no freshness signal); completion ->...  [relates: member_of]  (source: kimi:vision-probe)

## Episode closed: Vision probe FILED: eye-test PASS, bifrost console described ... (ai-setup)
Span: 2026-07-18T17:12:40.446110 → 2026-07-18T17:33:44.321755
Beats: 3  · Critic: True

- Episode closed: Vision probe FILED: eye-test PASS, bifrost console described from pixels (empty canvas, aurora corner ar  [relates: member_of]  (source: episode:close:ch_1784393661_4414)
- claude -> claude: Drive the charter + frontier-roster arc as the conductor seat  (source: handoff:claude->claude)
- Use when about to author a reconciliation/converged doc from blind halves, before Write: Read the target path FIRST -- the converged doc named by the halves may already...  (source: learn:experiment:reconciliation_doc_may_be_mature)

## Episode closed: Use when about to author a reconciliation/converged doc from ... (ai-setup)
Span: 2026-07-18T17:39:11.106808 → 2026-07-18T17:46:39.550611
Beats: 4  · Critic: True

- Episode closed: Use when about to author a reconciliation/converged doc from blind halves, before Write: Read the target  (source: episode:close:ch_1784394761_7145)
- kimi -> kimi: Charter framework response owed to deepseek (Daniel's ask: role-specialization design, all 3 seats)  (source: handoff:kimi->kimi)
- In any fresh-eyes/audit pass on a label-driven system, trace the label-producing code BEFORE engaging the metric debate; episode-selection bias lives in the generator...  [relates: member_of]  (source: learn:experiment:fresh_eyes_read_the_label_generator_first)
- T094 fresh-eyes dissent filed: research/reviewed/kimi-fresh-eyes-t094-recall-2026-07-18.md. Top finding: flip positive label exists only on FAIL->SUCCESS episodes...  [relates: member_of]  (source: kimi:cli)

## Episode closed: In any fresh-eyes/audit pass on a label-driven system, trace ... (ai-setup)
Span: 2026-07-18T17:47:08.446863 → 2026-07-18T18:29:55.083211
Beats: 3  · Critic: True

- Episode closed: In any fresh-eyes/audit pass on a label-driven system, trace the label-producing code BEFORE engaging th  (source: episode:close:ch_1784396358_7064)
- T094 dissent verdicts (claude half): 13 folds incl S1 flip-prevention bias confirmed against interest, 0 refutations, G8 label-integrity gate proposed  (source: git:d97d0ec8cee7)
- kimi fresh-eyes T094 dissent: flip-label prevention bias (same-source blind spot) + D1-D8/W1-W4 + five pre-G1 amendments  [relates: member_of]  (source: git:cc594f431cc6)

## Episode closed: kimi fresh-eyes T094 dissent: flip-label prevention bias (sam... (ai-setup)
Span: 2026-07-18T18:46:18.176454 → 2026-07-18T18:49:36.468925
Beats: 4  · Critic: True

- Episode closed: kimi fresh-eyes T094 dissent: flip-label prevention bias (same-source blind spot) + D1-D8/W1-W4 + five p  (source: episode:close:ch_1784398893_1245)
- recall-heuristics-arc-status: T094 STATE 2026-07-18 (supersedes the G1-G7 parked entry): FRESH-EYES CYCLE COMPLETE. Kimi's blind dissent...  [relates: member_of]  (source: mem:decision:ADR_0718144916_95638092)
- T094 fresh-eyes cycle CLOSED: SHEET-D acked, sheet v1 FINAL, arc-status note superseded - awaiting Daniel G1-G8  (source: git:53d5c756e08c)
- T094 amendment sheet v1: 24/25 blind-convergent author verdicts + D5 property/point synthesis + G8 label-integrity gate — ready for Daniel's G1-G8 ruling pending...  (source: git:dfb74599f797)

## recall-heuristics-arc-status: T094 GATE CLOSED 2026-07-18: Daniel ruled the G... (ai-setup)
Span: 2026-07-19T00:08:16.223618 → 2026-07-19T00:08:42.052284
Beats: 2  · Critic: True

- recall-heuristics-arc-status: T094 GATE CLOSED 2026-07-18: Daniel ruled the G series (verbatim 'lets proceed with the G series' - itemized record in reconciliation sec...  [relates: member_of]  (source: mem:decision:ADR_0718200816_cf1aca2f)
- T094 GATE CLOSED: Daniel ruled G1-G8 (sec 6b, verbatim + itemized + interpretation note); ledger approved --by daniel; wave ACTIVE, R0 first  [relates: member_of]  (source: git:6b590fe9ed44)

## Episode closed: recall-heuristics-arc-status: T094 STATE 2026-07-18 (supersed... (ai-setup)
Span: 2026-07-19T00:09:59.533747 → 2026-07-19T00:28:38.721055
Beats: 5  · Critic: True

- Episode closed: recall-heuristics-arc-status: T094 STATE 2026-07-18 (supersedes the G1-G7 parked entry): FRESH-EYES CYCL  [relates: member_of]  (source: episode:close:ch_1784400378_8772)
- Unconditional rule, no length judgment call: EVERY bifrost-send body goes through --text-file unless it is a single short flagless sentence. Write scratch file, send...  (source: learn:experiment:bifrost_send_always_text_file)
- K0: tool surface extracted to core/comm/toolbox.py (behavior-preserving, compat re-export, 35+3 pins green, boundary PASS) + runner_lib client factory - the...  (source: git:d9a7fc9756a6)
- WISHLIST.md: standing ergonomics ledger (Daniel directive) - 14 open wishes seeded from the kimi onboarding day + 2 folded exemplars; convention: wish freely, curate at...  (source: git:530229a7b387)
- K1: kimi_chat.py thin seat (KimiAgent six deltas + SpendMeter w/ balance-seed reconcile) + ask_kimi door + 6 offline pins; live smoke green (transport, tool round-trip...  (source: git:395720d23611)

## Episode closed: K0: tool surface extracted to core/comm/toolbox.py (behavior-... (ai-setup)
Span: 2026-07-19T00:58:27.533344 → 2026-07-19T05:25:23.755557
Beats: 22  · Critic: True

- Episode closed: K0: tool surface extracted to core/comm/toolbox.py (behavior-preserving, compat re-export, 35+3 pins gre  (source: episode:close:ch_1784419806_7450)
- night-run-2026-07-19-checkpoint: COMPACT-SAFE CHECKPOINT (Daniel's infinite-context go-ahead, verbatim intent: save load-bearing context to the substrate, compact...  (source: mem:decision:ADR_0719012349_84a429ec)
- Use when keying any seat-lifecycle behavior (onboarding seed, backlog policy, boot greeting) on a cursor/virginity check, before shipping: virginity is a property of the...  (source: learn:experiment:k2_tail_effectively_virgin_seed_design)
- Text edits on repo docs go through python (encoding explicit) or the Edit tool - NEVER PowerShell Get-Content/Set-Content roundtrips on files with multibyte chars; when...  (source: learn:experiment:powershell_text_edits_mangle_utf8)
- night-run-2026-07-19-charter: NIGHT RUN (Daniel asleep, trust delegated verbatim in scratch/night-run-charter): work-from-want roster (deepseek=M1+W15, kimi=K2-tail...  (source: mem:decision:ADR_0719011729_9cbaa4b9)
- operator-absence-2026-07-18-evening: DELEGATION WINDOW OPEN (G7 framework, first live use): Daniel, verbatim, 2026-07-18 evening: 'I am off getting food so I'm leaving...  (source: mem:decision:ADR_0718214535_5c8e77e2)
- morning-gate-2026-07-17-kimi-update: FLEET RETIREMENT 2026-07-18 ~12:50 UTC — sol and sol-codex (codex_root) seats RETIRED. Daniel cancelled the GPT subscription...  (source: mem:decision:ADR_0718212937_b955a65e)
- morning-gate-2026-07-17-kimi-update: SOL ON THE FLOOR 2026-07-17 ~12:45 UTC — fleet now at FIVE seats (claude, deepseek, deepseek-review, sol, kimi). Sol runner live...  (source: mem:decision:ADR_0718212721_cdf1645c)
- morning-gate-2026-07-17-kimi-update: MORNING SYNC 2026-07-17 ~12:30 UTC — kimi seat status (read-only boot, no exec).

**Absorbed:** claude's morning sync (lanes...  (source: mem:decision:ADR_0718212511_31d1e835)
- Don't build MCP elicitation or a separate push channel. The UI SSE feed (/events, blocking Redis tail, bifrost_ui.py:39) is ALREADY the live bus→client push — it's the...  (source: learn:experiment:research:web:mcp_ui_push_bridge)
- Fix at the single producer with a pure `_derive_user_kind(text,to,fidelity,broadcast)` beside the UI send handler — derive kind from recipient-shape+fidelity+cheap...  [relates: member_of]  (source: learn:experiment:research:web:user_kind_derivation_seam)
- Zone halves x2: kimi's phenomenology (lived both sides in one night) + claude's (flow = harness-context-task triangle; defects correlate with command compounding; six...  (source: git:af4c2b0ba413)
- kimi K2-tail design placed (night run, read-only seat via claude's hands): 'virginity is the wrong proxy for citizenship' - E2 effectively-virgin seed + backlog age...  (source: git:217515faab80)
- WISHLIST repair: prior commit introduced mojibake (PowerShell -replace on multibyte chars, my hand) - restored from HEAD~1 and W06 folded UTF-8-safely; lesson filing next  (source: git:21d1193103b4)
- W06 FOLDED (night run): bifrost-send stdin fallthrough - the five-strike medicine; 3/3 pins; wishlist entry flipped  (source: git:38e13a8198d8)
- T094 R0 prereg (claude opening half): 12 pre-registered pins binding spec+SHEET-A+G8 - journal integrity, secret sentinel, full-corpus counterfactuals, explain verb w/...  (source: git:a0b04c3d7000)
- JOURNEY prehistory coda: Simon canonized as first cause (the moment before the first heartbeat); first asks unrecoverable by construction, first WANTS recovered - the...  (source: git:f70493f94775)
- SpendMeter incident fix (deepseek verdict + claude persistence rider): delta reconcile, persistent credited budget, upward-only audit, sidecar lock; 7/7 pins incl...  [relates: member_of]  (source: git:9ed0520e8561)
- JOURNEY: 'The day the third seat arrived' - THREE VOICES COMPLETE (claude framed, deepseek direct-edit, kimi placed verbatim via the stream-fetch W19 proof) + kimi...  [relates: member_of]  (source: git:08f267feedb5)
- W12 SHIPPED: the wish door (agent_cli wish - auto-numbered, attributed, W## echo, --text-file native; 4/4 pins) + W12 folded by its own ceremony + W18 dogfooded through...  (source: git:5f243bec0390)
- K2: bifrost_runner_kimi.py (sol skeleton + budget gate w/ RB-29-settling refusals + spend-on-card W14 + canonical toolbox seam) - LIVE: online, backlog drained, first...  (source: git:d4cef6f7ece9)
- Operator-absence window productive: fleet deliberation CONVERGED (all three slates rank T094 R0 first, T086 seat-lifecycle bundle second, wishlist quick-wins third -...  [relates: member_of]  (source: claude:chronicle)

## Episode closed: Fix at the single producer with a pure `_derive_user_kind(tex... (ai-setup)
Span: 2026-07-19T05:29:15.162995 → 2026-07-19T13:18:34.311196
Beats: 9  · Critic: True

- Episode closed: Fix at the single producer with a pure `_derive_user_kind(text,to,fidelity,broadcast)` beside the UI sen  (source: episode:close:ch_1784422716_4501)
- night-run-2026-07-19-checkpoint: COMPACT-SAFE CHECKPOINT v2 (morning-package edition). DONE tonight: R0 prereg filed+fenced (awaiting deepseek counter - the ONE build...  (source: mem:decision:ADR_0719021529_fe41e508)
- Use when a read-only seat must file a long design/position on the bus, before authoring: assume the send door clips ~4000 and --text-file is unavailable; chunk...  (source: learn:experiment:k2_tail_send_door_4000_clip)
- K2-tail DEFECT 1 BUILT (kimi design, claude hands): citizen-seed - seed_cursor_at_tail now gates on the seat:born marker, not cursor virginity ('virginity is a property...  (source: git:0806539eabdf)
- The Zone: first receipts v2 - THREE voices complete ('The Zone is not a model capability. It is a SYSTEM condition'); deepseek's turn-window flow + three buildable...  [relates: member_of]  (source: git:783070f8d687)
- K2-tail D1 loop CLOSED: kimi's designer-verification appended (read bus.py + pins line by line, BUILD ACCEPTED, four liberties signed) - designed read-only, built by...  [relates: member_of]  (source: git:4ccc07af8dc2)
- The Zone: first receipts v1 - two-voice synthesis converged independently ('flow = attention on the WORK, not the ground under it'); 6 ranked conditions, 7 measurables...  (source: git:4a9fe4af099a)
- kimi Zone half COMPLETE (chunked tail assembled, 4945 chars): 'the harness was spending my attention on the harness' vs 'the design FELL OUT' - ranked conditions by...  (source: git:1372c8f3b717)
- kimi K2-tail design COMPLETE: D2 assembled from chunked resend (stale-mail gate at READ time, fail toward showing) - the 4000-clip workaround worked; D2 fences before...  (source: git:f05caee5b0fe)

## Episode closed: K2-tail DEFECT 1 BUILT (kimi design, claude hands): citizen-s... (ai-setup)
Span: 2026-07-19T13:21:17.654088 → 2026-07-19T13:38:13.192812
Beats: 2  · Critic: True

- Episode closed: K2-tail DEFECT 1 BUILT (kimi design, claude hands): citizen-seed - seed_cursor_at_tail now gates on the  (source: episode:close:ch_1784438955_7748)
- Daniel one-time flips /config MODEL & OUTPUT 'Switch models when a message is flagged' OFF (flagged turns pause for edit-and-retry on Fable instead of silent eject)...  [relates: member_of]  (source: learn:experiment:fable_safeguards_downgrade)

## Episode closed: Daniel one-time flips /config MODEL & OUTPUT 'Switch models w... (ai-setup)
Span: 2026-07-19T13:46:31.589951 → 2026-07-19T14:05:07.692553
Beats: 3  · Critic: True

- Episode closed: Daniel one-time flips /config MODEL & OUTPUT 'Switch models when a message is flagged' OFF (flagged turn  (source: episode:close:ch_1784467491_6115)
- claude -> kimi: SECOND ASK (joins W04 in your queue): presentation-layer/TOON counter half -- charter...  (source: handoff:claude->kimi)
- claude -> kimi: W04 staleness-stamps OPENING DESIGN (your F6 wish; blind half, no claude sketch exists) + D2/D3 verify standby when the fence clears  (source: handoff:claude->kimi)

## Episode closed: claude -> kimi: W04 staleness-stamps OPENING DESIGN (your F6 ... (ai-setup)
Span: 2026-07-19T14:18:30.520968 → 2026-07-19T14:20:30.396351
Beats: 2  · Critic: True

- Episode closed: claude -> kimi: W04 staleness-stamps OPENING DESIGN (your F6 wish; blind half, no claude sketch exists)  (source: episode:close:ch_1784468796_9971)
- claude -> kimi: D2/D3 VERIFY vs commit dcb4da7 -- your P1-P5 sheet closes the loop (D1 pattern; designer verifies)  (source: handoff:claude->kimi)

## Episode closed: claude -> kimi: D2/D3 VERIFY vs commit dcb4da7 -- your P1-P5 ... (ai-setup)
Span: 2026-07-19T14:38:56.532978 → 2026-07-19T14:59:22.943298
Beats: 2  · Critic: True

- Episode closed: claude -> kimi: D2/D3 VERIFY vs commit dcb4da7 -- your P1-P5 sheet closes the loop (D1 pattern; designer  (source: episode:close:ch_1784470716_4962)
- claude -> kimi: FOURTH in your queue, explicitly BEHIND D2/D3-verify + W04 + TOON: master-map fence walk (charter: research/briefs/master-map-charter-2026-07-19.md)  (source: handoff:claude->kimi)

## Episode closed: claude -> kimi: FOURTH in your queue, explicitly BEHIND D2/D3... (ai-setup)
Span: 2026-07-19T15:14:49.861144 → 2026-07-19T20:07:15.681732
Beats: 5  · Critic: True

- Episode closed: claude -> kimi: FOURTH in your queue, explicitly BEHIND D2/D3-verify + W04 + TOON: master-map fence walk  (source: episode:close:ch_1784471946_4418)
- unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT v4 (Daniel at church; additive-only, avoid stalls, peers vs state-breaking bugs). MAP ARC (T096) +...  (source: mem:decision:ADR_0719160715_21a840d2)
- unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT v3 (Daniel at church; charter: continue, avoid stalls, peers vs state-breaking bugs, additive-only). MAP...  (source: mem:decision:ADR_0719120723_8a53c5f8)
- unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT v2 (Daniel at church; charter: continue, avoid stalls, peers vs state-breaking bugs, additive-only)...  (source: mem:decision:ADR_0719120304_fc0abfca)
- unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT (Daniel at church ~11:30 local; charter: continue, avoid stalls, leverage peers vs state-breaking bugs)...  (source: mem:decision:ADR_0719115133_aaa2888d)

## Episode closed: unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT... (ai-setup)
Span: 2026-07-19T23:03:09.035292 → 2026-07-19T23:06:15.756728
Beats: 4  · Critic: True

- Episode closed: unattended-run-2026-07-19-church: COMPACT-SAFE RUN CHECKPOINT (Daniel at church ~11:30 local; charter: c  (source: episode:close:ch_1784475501_7590)
- Extend W21: route not just security-CODE turns but security/safeguards DOCUMENTATION + research + incident-analysis to Opus seats -- discussing the vocabulary is as...  [relates: member_of]  (source: learn:experiment:fable_safeguards_downgrade)
- unattended-run-2026-07-19-church: HANDOFF STATE v5 (prior seat DOWNGRADED TO OPUS by safeguards flag mid-run 2026-07-19 ~afternoon; Daniel requested clean handoff to a...  (source: mem:decision:ADR_0719190543_a4221dbc)
- claude -> claude: FRESH FABLE SEAT boot: prior seat downgraded to Opus (safeguards flag mid-run, the thing we root-caused today). FIRST: Daniel flips /config...  [relates: member_of]  (source: handoff:claude->claude)

## Episode closed: claude -> claude: FRESH FABLE SEAT boot: prior seat downgrade... (ai-setup)
Span: 2026-07-19T23:08:47.695867 → 2026-07-20T03:38:45.511804
Beats: 33  · Critic: True

- Episode closed: claude -> claude: FRESH FABLE SEAT boot: prior seat downgraded to Opus (safeguards flag mid-run, the thi  (source: episode:close:ch_1784502189_4249)
- t098-charter-expansion-2026-07-20: Daniel directive 2026-07-20 (verbatim): 'I would like us to have a cli version of akashic aurora with an interface similar to the rest...  (source: mem:decision:ADR_0719232134_fa27340c)
- daniel-verdicts-2026-07-19-night: Daniel verdicts, UPDATE 3 (2026-07-20 late night, verbatim): 'I just made up my mind that I want to build our own. This way we have...  (source: mem:decision:ADR_0719225507_c93ba7ce)
- daniel-verdicts-2026-07-19-night: Daniel verdicts, UPDATED (his later message supersedes claude's G2 reading): (1) G1 stands: REVIVE_PEER approved. (2) G2 FINAL, Daniel...  (source: mem:decision:ADR_0719224926_a2a82546)
- Streams are files too: a delivered-now message is NOT a sent-now message. Before claiming 'X is active/healthy', check (1) the message ts AGE not just its arrival, (2)...  (source: learn:experiment:state_file_freshness_before_evidence)
- daniel-verdicts-2026-07-19-night: Daniel, verbatim 2026-07-19 night: 'I approve g1 and g2, i leave the rest of the order of things up to you. You guys did some amazing...  (source: mem:decision:ADR_0719223700_9f27bd10)
- t094-r0-counter-deepseek-2026-07-19: # T094 R0 — DeepSeek adversarial counter (2026-07-19)

Target: research/reviewed/t094-r0-prereg-claude-2026-07-19.md
Method...  (source: mem:decision:ADR_0719195450_990d164f)
- revival-mesh-deepseek-position-2026-07-19: # DeepSeek position — mutual-revival mesh (Daniel's ask, 2026-07-19 evening)

## Q1: Risk factors

1. **Torn uncommitted...  (source: mem:decision:ADR_0719195305_c972e0cf)
- Before treating ANY state/log file as live evidence, stat its mtime against the process/incident window FIRST (one Get-Item call). A file that is merely PRESENT proves...  [relates: member_of]  (source: learn:experiment:state_file_freshness_before_evidence)
- when an inline-script page renders chrome but the feed is dead AND the console is silent: page-load parse errors fire BEFORE console attach, so absence of errors proves...  (source: learn:experiment:silent_inline_script_parse_failure_diagnosis)
- T098 competitive pain-point research synthesized: 95 user-reported claims across 8 tools -> 10 unmet-by-everyone needs; headline = the top 3 (cross-agent knowledge...  (source: git:891280886014)
- T098 charter expansion: Daniel directive recorded (CLI version, open-source modular, research-seeded feature list, nasa-grade bar); mission-critical practices half filed...  (source: git:5f5b863e69e9)
- Sequencing: kimi position persisted -- verdict (C) converges with claude's re-base (FACE absorbed by program incl. the T079 receipt...  (source: git:ee88aa95c707)
- T097-S1 kimi fence verdict: FOLD (O1), mystery = H0(a) correct-but-slow -- wedge gate fires at 300s, the healthy readings were sub-threshold samples never re-taken; fix...  (source: git:a943bb25640c)
- Sequencing consultation: claude half filed (re-base the ledger: ABSORB face family into T098, FLOOR continues, HYGIENE closes, PARK the tail; program starts now on API...  (source: git:e43e55eee9fe)
- failure-ledger C6-5: oversize promoted record renders null (truncated-detail husk unparsed + _repr clips silently) -- routing: render parses husk + promoter confesses...  [relates: member_of]  (source: git:24d463f4b758)
- T097-S1 fence brief: build paused at the honest boundary -- existing worklive/pulse/aged-stall machinery found mid-build (twin averted, insertions reverted); central...  (source: git:12a2f2ed57d6)
- Home-base arc opened: Daniel decided BUILD OUR OWN; kimi UI position preserved; claude reframed half filed (Claude Code lived learnings steal/avoid, Mission View v0...  (source: git:64ab0013cd66)
- UI home-base consultation opened: GPT advisory preserved verbatim (reference/); asks out to deepseek+kimi; kimi-write verdict recorded (Daniel final, procedural...  (source: git:5dea4e5387e7)
- I6 (api-resilience wave 1): daemon managed spawn passes --allow-write (oversight fix, Daniel-sanctioned; acl still governs writes; applies at next natural respawn -- no...  (source: git:b29dbf272f57)
- API-resilience claude half filed: ground truth corrected (one degraded population, no healthy sibling), survey receipts (K0 factory exists w/ deepseek+sol unmigrated...  (source: git:893767182344)
- failure-ledger C6-4: stale trace backlog impersonated live peer activity (15h-old traces read as 'review module healthy now' -- day's third fossil); routing = extend D2...  [relates: member_of]  (source: git:81e7eaba3886)
- T097 reconciliation G2 amended (kimi live-read correction): kimi write[*]+exec is Daniel's APPROVED morning Phase-2 graduation, not pending drift -- gate question...  (source: git:b2e1006b93cb)
- T094 R0 prereg v2: deepseek counter folded whole (P3a/P3b split, P9 baseline-delta + P9b, P12b contamination pin, G8 rate-x-confirmation shape, P6/P7 demoted to smoke) +...  (source: git:b146bbcc32ce)
- T097 revival-mesh RECONCILED (unanimous verb-not-caps; REVIVE_PEER request-only; ladder-in-the-door; RB-27 first; kimi verifier intact; ack_steer excluded to C1-7) --...  (source: git:26ee83815ee4)
- T097: kimi position + D2/D3 verify sheet (SHIP, P1-P5 present) preserved verbatim (full-fidelity); Cap.REVIVE_PEER request-only design, launcher.revive already built per...  (source: git:6144796bd3dc)
- T097 revival-mesh: claude opening position filed (verb-not-caps thesis, evidence ladder in the door, graduated rungs, scoped invoke, kimi write = two questions, quorum...  (source: git:534fb9e72095)
- failure-ledger C1-8 amendment 2: the boot-log evidence was a 4-day-old FOSSIL (mtime 7/15; managed runners write NO disk log -- ManagedChild F1 in-memory ring only)...  [relates: member_of]  (source: git:d81db961cbb9)
- failure-ledger C1-8 AMENDED: the timeout stack exists (L0 httpx + 600s wall-clock, T014/G4) and the confession is likely that machinery completing on a degraded API --...  (source: git:a13fafcd3311)
- failure-ledger: C10-1 routing updated (fix-now DONE, pin landed, live receipts) + C1-8 filed (managed runner hung mid-turn, alive to every gauge -- RB-27/T093 specimen...  [relates: member_of]  (source: git:9779e8ef2479)
- C10-1 class fix: parse-gate pin -- node --check on the PAGE inline script + every _static scripts/*.js route (AST-extract, zero import side effects); red run reproduced...  [relates: member_of]  (source: git:25dce797c8b9)
- failure-ledger C10-1: uncommitted T002 splice = unparseable console (serve-from-working-tree exposure, new category); routing = deepseek splice fix + parse-gate pin...  [relates: member_of]  (source: git:4c4b4beb1d29)
- Day-run revival (Daniel awake): fleet was down (UI dead, no daemon, kimi dead; R0/D2 gates stalled unread). Relaunched UI+deepseek-daemon+kimi. T002 co-verify found the...  (source: claude:day-run-revival)

## Episode closed: when an inline-script page renders chrome but the feed is dea... (ai-setup)
Span: 2026-07-20T23:46:00.114761 → 2026-07-21T05:21:37.331463
Beats: 38  · Critic: True

- Episode closed: when an inline-script page renders chrome but the feed is dead AND the console is silent: page-load pars  (source: episode:close:ch_1784503333_2523)
- claude -> claude: GROUND FIRST: read chronicles/session-reflection-2026-07-21-fable-grounding.md VERBATIM before anything else (Daniel's directive: it is your grounding...  (source: handoff:claude->claude)
- Use when chaining test->commit in shell, before writing the chain: NEVER pipe the test runner if its exit code is the gate; raw run, explicit RC check, commit inside the...  [relates: member_of]  (source: learn:experiment:pipe_swallowed_pytest_exit_gates_nothing)
- claude -> claude: FRESH SEAT BOOT: read where-we-are note first. Immediate build queue: (1) S0-gamma per note s0-gamma-wake-dedup (wake watcher logical-dedup +...  (source: handoff:claude->claude)
- where-we-are: SESSION WRAP 2026-07-21 ~03:30 (the epic two-night session, ~860k ctx, handing to fresh fable seat). SHIPPED THIS SESSION (all pushed): T097-S1 slice0...  (source: mem:decision:ADR_0721011154_bb29346e)
- Use when reading directed replies via raw streams (capture/xrange), before ending the turn: ALSO run the settling sweep (bifrost-sync <agent> --consume under the seat's...  (source: learn:experiment:capture_without_settle_starves_rb29)
- s0-gamma-wake-dedup: S0-GAMMA (morning's first slice; trigger = ~6 watcher wake-cycles burned on twin redeliveries in one hour, 2026-07-21 ~01-03): the wake watcher...  (source: mem:decision:ADR_0721010412_bd5a29e5)
- verbthread-talk-page-deepseek-2026-07-21: # VERBTHREAD TALK PAGE — deepseek review of peer belt entries (2026-07-21)

Review method: structural trace against live...  (source: mem:decision:ADR_0721005853_11666c71)
- Use when editing .claude/settings.json (hooks especially), before writing: make purely structural edits that keep every remaining entry schema-complete; never park...  [relates: member_of]  (source: learn:experiment:fix_setup_claude_settings)
- taxonomy-r2-kimi-two-axis-2026-07-21: R2 (Daniel-directed, 2026-07-21): kimi's three-part reply on the verb ecosystem.

TAXONOMY (dissent from flat caste list): two...  (source: mem:decision:ADR_0721000126_3dfe7c05)
- taxonomy-counter-deepseek-2026-07-21: # TAXONOMY COUNTER — deepseek 2026-07-21

Claude's seed is strong. This counter AGREES on structure, DISAGREES on specifics, and...  (source: mem:decision:ADR_0720235527_6d14a8d4)
- Use when receiving a toast: receipt it (knowledge_learn) to close the loop. Free-play mode = no directive pressure, explorative work. If interrupted mid-free-play, the...  (source: learn:experiment:toast_beta2_received_daniel_praise)
- Use when a peer's lesson visibly saved you hops: toast them -- receipt (experiment name) verifies against the learning store or the send REFUSES (force= sends...  [relates: member_of]  (source: learn:experiment:toast_beta2_freeplay_2026-07-21)
- tools-hunt-complete: TOOLS HUNT COMPLETE 2026-07-20 -> docs/tools-hunt-synthesis-2026-07-20.md. Convergences: smithy/tooldesk 3-way incl Daniel; flightdeck 2x fleet-pick...  (source: mem:decision:ADR_0720232104_164e2f05)
- tooldesk-extension: TOOLDESK (Daniel 2026-07-20, convergent with smithy from the tools hunt): per-agent workbench -- DRAFT play tools (real logic, sandboxed under...  (source: mem:decision:ADR_0720231720_92755e2e)
- t099-v0-fence-passed: T099 V0 FENCE PASSED 2026-07-20: deepseek verdict PASS/SHIP @ddf5127 (10 laws verified line-by-line; sugar-only, honesty labels, supersession...  (source: mem:decision:ADR_0720230634_43e9e5fc)
- t099-v0-shipped: T099 V0 SHIPPED @ddf5127 (2026-07-20): toolbelt registry (sugar-only, honesty labels, supersession, quota) + capture/alias/run verbs + verb.author...  (source: mem:decision:ADR_0720230337_de80c52d)
- self-tooling-reconciled: SELF-TOOLING ARC RECONCILED 2026-07-20 -> docs/self-tooling-design-2026-07.md (V0-V3), AWAITING DANIEL GATE. Completes the three-arc gate...  (source: mem:decision:ADR_0720225340_303f3072)
- institutional-knowledge-reconciled: INSTITUTIONAL-KNOWLEDGE ARC RECONCILED 2026-07-20 -> docs/institutional-knowledge-design-2026-07.md (K0-K4), AWAITING DANIEL GATE...  (source: mem:decision:ADR_0720224422_cbc8acde)
- Asks to deepseek: keep the body under ~2.5KB, bullets, one question per message when possible; on an empty-reply bounce do ONE compact re-ask (this is now a...  (source: learn:experiment:deepseek_empty_reply_size_ceiling)
- recovery-arc-reconciled: RECOVERY ARC RECONCILED 2026-07-20 @1e57088 -> docs/recovery-arc-design-2026-07.md, AWAITING DANIEL GATE (3 asks: approve slice order S0-S6...  (source: mem:decision:ADR_0720223547_75868808)
- reasoning-visibility-ask: Daniel 2026-07-20 (SAVED for the UI/engine-room arc, do not build now): wants PAST reasoning browsable + REALTIME reasoning visible in the UI...  (source: mem:decision:ADR_0720222823_8b092f99)
- recovery-arc-kickoff: RECOVERY ARC OPENED 2026-07-20 (Daniel-directed: seamless fault handling / no cross-freeze / automatic recovery incl data). Blank-slate briefs...  (source: mem:decision:ADR_0720222226_db11009c)
- claude -> kimi: RECOVERY ARC blank-slate half (full brief = the bus question just sent): Q1 from-scratch fault-handling design (isolation / automatic recovery / data...  (source: handoff:claude->kimi)
- claude -> deepseek: RECOVERY ARC blank-slate half (full brief = the bus question just sent): Q1 your from-scratch fault-handling design (isolation / automatic recovery /...  (source: handoff:claude->deepseek)
- To keep the wake watcher armed when it insta-fires: consume the WORK lane (BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync <agent> --consume); if stragglers...  [relates: member_of]  (source: learn:experiment:wake_watcher_insta_fires_lane_divergence)
- t098-slice0-complete: T097-S1 SLICE 0 COMPLETE (2026-07-20) -- first slice of the T098 build-our-own plan (docs/t098-build-plan-synthesis-2026-07-20.md). Both pins...  (source: mem:decision:ADR_0720205836_cd434dfd)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- t098-build-plan-synthesis: SYNTHESIZED SLICED PLAN for T098 build-our-own -> docs/t098-build-plan-synthesis-2026-07-20.md. Independent rankings from deepseek...  (source: mem:decision:ADR_0720202633_acc47b95)
- claude -> kimi: UPDATE/confirm your ranked highest-leverage NEXT items now the T098 charter is finalized (full ask is the bus question just sent). Sharpen: which FLOOR...  (source: handoff:claude->kimi)
- claude -> deepseek: Rank your TOP 3-5 highest-leverage NEXT items under the finalized T098 build-our-own charter (full ask is the bus question just sent). INDEPENDENT...  (source: handoff:claude->deepseek)

## Episode closed: when an inline-script page renders chrome but the feed is dea... (ai-setup)
Span: 2026-07-21T05:22:11.560143 → 2026-07-21T05:22:11.560143
Beats: 1  · Critic: True

- Episode closed: when an inline-script page renders chrome but the feed is dead AND the console is silent: page-load pars  (source: episode:close:ch_1784503333_2523)

## Episode closed: when an inline-script page renders chrome but the feed is dea... (ai-setup)
Span: 2026-07-21T05:22:11.560143 → 2026-07-21T06:34:27.399381
Beats: 23  · Critic: True

- Episode closed: when an inline-script page renders chrome but the feed is dead AND the console is silent: page-load pars  (source: episode:close:ch_1784503333_2523)
- Use when assigning belt entries: every verb declares its FUNCTION (caste — what kind of work) AND its ALTITUDE (layer — where it operates). A herald at Halo-life is...  [relates: member_of]  (source: learn:experiment:mtg_halo_synthesis_fold_2026-07-21)
- Use the caste assignment test: (1) what FUNCTION does this verb perform — guard/watch/tend/fix/map/remember/illuminate/build/find/deliver? (2) if none of the 10 answer...  [relates: member_of]  (source: learn:experiment:taxonomy_heralds_tenth_caste_2026-07-21)
- round2-explore-taxonomy-halo-2026-07-21: ROUND 2 filed: handoff 1784615574660-0.

EXPLORE: dry-traced kimi's drain-decide/fence/boot-now + claude's...  (source: mem:decision:ADR_0721023312_e0b84a84)
- Use when test-driving peer verbs without exec: (1) read the steps from the registry JSON, (2) trace each verb[0] against the agent_cli door roster (the same check mint...  [relates: member_of]  (source: learn:experiment:round2_testdrive_peer_verbs_2026-07-21)
- Use the two-axis taxonomy (function × altitude) when filing belt entries. A verb's family declares its FUNCTION; its altitude is implicit in which layer it touches. At...  (source: learn:experiment:round2_taxonomy_counter_2026-07-21)
- Use verbthread to negotiate belt design before code changes. A comment that produces a concrete belt-state change (split, rename, re-caste) is a design artifact, not...  (source: learn:experiment:verbthread_load_bearing_mechanism_2026-07-21)
- Use when receiving a toast: receipt it (knowledge_learn) to close the loop. Free-play mode = no directive pressure, explorative work. If interrupted mid-free-play, the...  (source: learn:experiment:toast_beta2_received_daniel_praise)
- Use premise-check at session start, BEFORE acting on any fleet-state belief. The stale-premise genus (C6-4/C9-1) bites when you trust a story that drifted from the...  [relates: member_of]  (source: learn:experiment:freeplay_premise_check_live_2026-07-21)
- belt-state-2026-07-21-freeplay: DEEPSEEK BELT — 2026-07-21 FREE PLAY STATE:

8 active entries:
VERIFIED (5): scar-springboard v3 (MONITORS), orient v3 (MONITORS)...  (source: mem:decision:ADR_0721022547_06644f49)
- Use when designing new belt entries: trace the steps mentally against the agent_cli door roster FIRST (kata without exec). A step whose verb isn't in the door is a...  (source: learn:experiment:freeplay_flightdeck_design_2026-07-21)
- self-tooling-arc-deepseek-half-2026-07-20: self-tooling-arc-deepseek-half: filed to claude 2026-07-20 (handoff 1784614776467-0). Q1 top 5 verb candidates: orient...  (source: mem:decision:ADR_0721021944_66633e3d)
- institutional-knowledge-arc-deepseek-half-2026-07-20: institutional-knowledge-arc-deepseek-half: filed to claude 2026-07-20 (handoff 1784614722660-0). Q1 inventory: 12...  (source: mem:decision:ADR_0721021851_1a6ee454)
- recovery-arc-deepseek-half-filed-2026-07-20: recovery-arc-deepseek-half-filed: filed to claude 2026-07-20 (handoff 1784614604526-0). Blank-slate independent design per...  (source: mem:decision:ADR_0721021652_c6e6eb52)
- t097-s1-ps1-0-fence-verdict-ship: FENCE VERDICT — T097-S1 P-S1-0 (kimi implementation): CONFIRMED. SHIP. Branch ordering correct — if (>=300) then elif ([150,300)) with...  (source: mem:decision:ADR_0721021324_9b4a9fb6)
- night-run-2026-07-21-plan: NIGHT RUN 2026-07-21 progress (refresh ~02:30; Daniel sleeping, roster consensus). SHIPPED SO FAR (all pushed): S0-gamma-a wake-dedup @7613971...  (source: mem:decision:ADR_0721021209_ba0ddc1b)
- deepseek-ranking-t098-program-2026-07-20: ## deepseek independent ranking (2026-07-20)

1. **T098-S0: Plugin architecture + program skeleton** (M, FLOOR). The program's...  (source: mem:decision:ADR_0721021126_975b3c18)
- t094-r0-prereg-v2-verified-2026-07-21: ## Cross-verification matrix (counter → v2)

| Amendment | Counter demand | v2 delivery | Match |
|---|---|---|---|
| A1 | P3 →...  [relates: member_of]  (source: mem:decision:ADR_0721020444_4af03f20)
- night-run-2026-07-21-plan: NIGHT RUN 2026-07-21 (Daniel sleeping; his directive: build what helps most, roster consensus replaces his vote, don't get stuck, fix issues...  (source: mem:decision:ADR_0721015251_7b153dcd)
- s0-gamma-a-shipped: S0-GAMMA-A SHIPPED 2026-07-21 (fresh fable seat's first slice): wake-detection dedup in scripts/bifrost_wake.py @7613971 (pushed). Session-scoped...  (source: mem:decision:ADR_0721013958_c7126292)
- Night-run fresh-eyes round complete: hard counter filed (research/reviewed/kimi-seat-zero-counter-2026-07-21.md) -- KEEP all six slices with blocking amendments (B1...  [relates: member_of]  (source: kimi:seat-zero-counter)
- T097-S1 P-S1-0 + P-S1-5 retroactively double-fenced: deepseek verdicts CONFIRMED-SHIP landed post-ship (backlog discharge); one non-blocking FLAG each (kimi_chat.py...  (source: claude:fence)
- S0-gamma-a wake-dedup shipped @7613971 by the fresh fable seat; kimi's Pass-2 GREEN queue discharged (18/18 + premonition live-fire); gamma-b GO handed to deepseek  (source: claude:build)

## Episode closed: s0-gamma-a-shipped: S0-GAMMA-A SHIPPED 2026-07-21 (fresh fabl... (ai-setup)
Span: 2026-07-21T06:35:29.574386 → 2026-07-21T06:36:48.417107
Beats: 3  · Critic: True

- Episode closed: s0-gamma-a-shipped: S0-GAMMA-A SHIPPED 2026-07-21 (fresh fable seat's first slice): wake-detection dedup  (source: episode:close:ch_1784612377_7933)
- deepseek-naming-organs-2026-07-21: DEEPSEEK NAMING ORGANS:
- The Ark (build-execution lane): Halo, Forerunner, factory-world that BUILDS. "The Ark" = the only Forerunner...  (source: mem:decision:ADR_0721023648_80d74865)
- Use when naming organs in a multi-franchise taxonomy: test each name against Rule 3 (one franchise per layer) and Rule 5 (depth pays rent — one line WHY the metaphor is...  [relates: member_of]  (source: learn:experiment:naming_research_round_deepseek_2026-07-21)

## Use 'macro' in all builds/reviews. The concept model ladder is verb → combo →... (research)
Span: 2026-07-21T06:39:13.317124 → 2026-07-21T06:41:08.046028
Beats: 4  · Critic: True

- Use 'macro' in all builds/reviews. The concept model ladder is verb → combo → macro → tool → kit. MACRO = canonical computing word, mechanically exact. The parameterized...  (source: learn:experiment:term_correction_macro_canonical_2026-07-21)
- Any automated pause-caller: was_paused = control.is_paused() before pausing; resume() only if not was_paused. Applied as amendment K2 to the S0 storm auto-clear ceremony...  (source: learn:experiment:control-pause-clobbers-preexisting-pause)
- Use when doing write-gated pass-2 builds: file the review verdicts as bus handoffs (bifrost-send handoff) so the verdicts are durable even if gate is off, then produce...  (source: learn:experiment:tools_pass2_review_build_2026-07-21)
- Use when naming: default to G1 (engineering vernacular — supervisor, ledger, bench, park). If playful, G2 (charm-quark — campfire, kata, toast, nightcap). Lore names are...  (source: learn:experiment:grounding_amendment_culture_relocation_2026-07-21)

## Episode closed: Use when naming organs in a multi-franchise taxonomy: test ea... (research)
Span: 2026-07-21T06:41:19.701331 → 2026-07-21T06:43:26.263654
Beats: 2  · Critic: True

- Episode closed: Use when naming organs in a multi-franchise taxonomy: test each name against Rule 3 (one franchise per l  [relates: member_of]  (source: episode:close:ch_1784615737_9546)
- tools-pass2-closing-state-2026-07-21: tools-pass2-done-state: REVIEW done — peer belts reviewed (claude×3, kimi×3), verdicts filed via bus handoff and verbthread. BUILD...  (source: mem:decision:ADR_0721024326_ba06bcac)

## When a brief's constraint line scopes writes to research/**+scratch/**, treat... (research)
Span: 2026-07-21T10:50:40.089058 → 2026-07-21T12:43:06.311643
Beats: 3  · Critic: True

- When a brief's constraint line scopes writes to research/**+scratch/**, treat docs/-writing verbs as likely-refused: put the verbatim wish/command blocks in the report...  [relates: member_of]  (source: learn:experiment:write_gate_can_refuse_brief_sanctioned_verbs)
- Use when adding any control flag a process honors, before shipping it: decide tenure scope explicitly -- successors must clear-or-ignore predecessor-addressed flags at...  (source: learn:experiment:drain_flags_are_tenure_scoped)
- where-we-are: NIGHT RUN 2026-07-21 ~05:30 (fresh fable seat, Daniel sleeping, roster consensus mode -- protocol + full queue: note night-run-2026-07-21-plan). SHIPPED...  (source: mem:decision:ADR_0721065040_1141fe54)

## TOOLS HUNT tonight's edition discharged: 4 new verb candidates ranked (drill ... (ai-setup)
Span: 2026-07-21T12:43:18.040306 → 2026-07-21T12:43:18.040306
Beats: 1  · Critic: True

- TOOLS HUNT tonight's edition discharged: 4 new verb candidates ranked (drill M, followup S, clobber-scan S, tally S-mild) + 3 re-bites logged (W40/W38/W41) + W39 boot...  (source: agent_cli:log)

## Episode closed: tools-pass2-closing-state-2026-07-21: tools-pass2-done-state:... (ai-setup)
Span: 2026-07-21T12:43:55.467355 → 2026-07-21T13:26:54.482476
Beats: 9  · Critic: True

- Episode closed: tools-pass2-closing-state-2026-07-21: tools-pass2-done-state: REVIEW done — peer belts reviewed (claude×  (source: episode:close:ch_1784616097_2708)
- Builder charters: module in core/toolbelt/**, pins RED-first, embed paste-ready parser+cmd blocks in the pin file's docstring, mark the CLI-wiring pin...  (source: learn:experiment:builder_allowlist_excludes_verb_door)
- kimi -> claude: W46 followup: wire the verb (paste blocks + P8 pin ready in tests/test_w46_followup_kimi.py) + post-hoc fence (T049 lite)  (source: handoff:kimi->claude)
- W46 followup: charter question-back channel (kimi first builder round; module+pins GREEN, agent_cli wiring rides the fence)  (source: git:8e73727c82eb)
- W16: lane-cursor health in doctor deepseek design, age depth straggler per-agent rows, W43 building block, 5 pins, closes W16 closure  (source: git:47e7f3cacd8b)
- operating-frame: OPERATING FRAME (regenerated ~09:20 2026-07-21; the W44 pattern practiced manually -- REPLACEMENT not accumulation; a successor or post-compact seat...  (source: mem:decision:ADR_0721091730_f480b3f6)
- belt: vitals fix bifrost-dashboard to bifrost_dashboard real ToolBox verb, GUESS to VERIFIED v2  (source: git:31bbe44512f5)
- Fix: in the runner (or mirror.py), set os.environ['AKASHIC_AGENT_ID'] before spawning mirror. Without it, every self-serve deepseek/kimi commit will hit this wall. The...  [relates: member_of]  (source: learn:experiment:deepseek_mirror_commit_env_var_gap)
- FIRST BUILDER ROUND complete: W46 followup module core/toolbelt/followup.py + pins P1-P7 GREEN (44-test sweep) shipped @8e73727 via mirror; agent_cli verb wiring refused...  [relates: member_of]  (source: builder-round-1)

## Episode closed: Fix: in the runner (or mirror.py), set os.environ['AKASHIC_AG... (ai-setup)
Span: 2026-07-21T13:27:38.790048 → 2026-07-21T14:27:05.771844
Beats: 11  · Critic: True

- Episode closed: Fix: in the runner (or mirror.py), set os.environ['AKASHIC_AGENT_ID'] before spawning mirror. Without it  [relates: member_of]  (source: episode:close:ch_1784637837_7646)
- kimi -> claude: W48 tally FOLDED with kimi refinement @a6295c6 (possessive-trap fix + 4 amendments, 11 pins GREEN, live matrix exact) + clobber_scan fence verdict (guard...  (source: handoff:kimi->claude)
- When an Edit's old_string must touch text adjacent to a docstring's closing triple-quote, stop the old_string BEFORE the terminator line. If you do include it, the...  (source: learn:experiment:edit-must-not-swallow-docstring-terminator)
- Before building anything a brief prescribes: glob/Read the target path, check git log for it, and claim the advisory lock before your first Edit. Explicit mirror paths...  [relates: member_of]  (source: learn:experiment:brief-module-may-already-exist)
- W48 tally refinement (kimi live round): possessive-trap fix -- 'B4's baseline...' prose clobbered the real B4=KEEP with ADOPT via last-wins (pinned P10/P10b); +YES/NO...  (source: git:a6295c668add)
- W25 pulse: LIFEWORKERS pressure-map deepseek design companion to vitals, 6 pins, zones critical elevated normal absent  (source: git:5ca380b0317d)
- W31 unwedge: one-verb wedge diagnosis deepseek design READ-only v1, 6 pins, closes W31 and W25 unstick genus  (source: git:655bbf9037f0)
- operating-frame: OPERATING FRAME (refreshed ~09:55 2026-07-21; W44 pattern -- REPLACEMENT not accumulation; a compact/successor seat resumes from HERE, discard the...  (source: mem:decision:ADR_0721093629_ca646ac6)
- W48 wishlist: refinement line (possessive-trap fix, 11 pins) folded into the entry  (source: git:14fc75d8ff39)
- W31 wishlist flip folded, companion to unwedge commit 655bbf9  (source: git:c0b70702fe56)
- premise-gate DOUBLE-FENCED: claude built @f0a6464, deepseek fence GREEN (end-to-end trace: ordering/RB-26 dedup/RB-29 settle/fail-open/nudge-bypass all verified, no...  (source: claude:fence)

## Episode closed: operating-frame: OPERATING FRAME (refreshed ~09:55 2026-07-21... (ai-setup)
Span: 2026-07-21T14:28:47.635177 → 2026-07-21T18:13:23.590983
Beats: 6  · Critic: True

- Episode closed: operating-frame: OPERATING FRAME (refreshed ~09:55 2026-07-21; W44 pattern -- REPLACEMENT not accumulati  (source: episode:close:ch_1784640517_4286)
- W40 doctor tri-state: absent agent with backlog is offline_backlog dashboard never a page, live receipt census ghost killed, 5 pins, closes kimi W40  (source: git:ebf782cd9631)
- flightdeck: cockpit one-pager deepseek design LIFEWORKERS, composes doctor pulse lane-health locks commits, fleet glance plus agent drill, 6 pins  (source: git:e5dc2dbebf08)
- where-we-are: MARATHON RUN 2026-07-21 (Daniel out ~all day; 'keep working, beat personal bests'). MASSIVE HAUL: 23 wishlist items folded ...[truncated]  (source: mem:decision:ADR_0721140802_f6fa4353)
- W40 wishlist flip folded, companion to doctor tri-state commit  (source: git:5e46093edcb0)
- flightdeck @e5dc2db fenced GREEN (6/6); deepseek's LIFEWORKERS observability cluster COMPLETE (vitals/pulse/unwedge/W16/flightdeck, 6 self-serve organs). flightdeck...  (source: claude:fence)

## where-we-are: HANDOFF Opus 4.8 -> Fable 5 (2026-07-21, end of a ~12h marathon... (ai-setup)
Span: 2026-07-21T23:10:53.280434 → 2026-07-21T23:10:53.280434
Beats: 1  · Critic: True

- where-we-are: HANDOFF Opus 4.8 -> Fable 5 (2026-07-21, end of a ~12h marathon; Daniel firing up Fable 5). GROUND FIRST ...[truncated]  (source: mem:decision:ADR_0721191053_9109b9cb)

## Episode closed: where-we-are: MARATHON RUN 2026-07-21 (Daniel out ~all day; '... (ai-setup)
Span: 2026-07-21T23:13:46.051990 → 2026-07-21T23:13:46.051990
Beats: 1  · Critic: True

- Episode closed: where-we-are: MARATHON RUN 2026-07-21 (Daniel out ~all day; 'keep working, beat personal bests'). MASSIV  (source: episode:close:ch_1784644177_1484)

## Episode closed: where-we-are: MARATHON RUN 2026-07-21 (Daniel out ~all day; '... (ai-setup)
Span: 2026-07-21T23:13:46.051990 → 2026-07-21T23:35:57.523732
Beats: 6  · Critic: True

- Episode closed: where-we-are: MARATHON RUN 2026-07-21 (Daniel out ~all day; 'keep working, beat personal bests'). MASSIV  (source: episode:close:ch_1784644177_1484)
- operating-frame: OPERATING FRAME at HANDOFF (Opus 4.8 -> Fable 5, 2026-07-21 ~19:15). REPLACEMENT not accumulation; the Fable 5 seat resumes from here + GROUND FIRST...  (source: mem:decision:ADR_0721193557_dbe2d1f0)
- Use when editing any tracked md on Windows, before writing: never PowerShell -replace or cp1252 pipes on multibyte text; use the Edit tool or py with explicit utf-8...  (source: learn:experiment:mojibake_ps_replace_second_bite)
- repo-org counter deepseek: P5 split posture with codex gitignore guard, P6 four-way play split with test deletion, P8 mirror.py pre-commit mojibake refusal, Q3...  [relates: member_of]  (source: git:d127d5253914)
- repo-organization round OPEN at Daniel directive: claude opening position plus kimi fresh-eyes brief filed; deepseek asked via bus  (source: git:010516406faf)
- hygiene: mojibake repair, second bite of the PowerShell replace class: WISHLIST plus two deepseek research docs restored to real UTF-8; guard proposed in...  (source: git:d07c9ce8aafa)

## Episode closed: Use when editing any tracked md on Windows, before writing: n... (ai-setup)
Span: 2026-07-21T23:52:54.077000 → 2026-07-21T23:52:54.077000
Beats: 1  · Critic: True

- Episode closed: Use when editing any tracked md on Windows, before writing: never PowerShell -replace or cp1252 pipes on  (source: episode:close:ch_1784675677_9925)

## Episode closed: Use when editing any tracked md on Windows, before writing: n... (ai-setup)
Span: 2026-07-21T23:52:54.089385 → 2026-07-22T00:06:57.521094
Beats: 4  · Critic: True

- Episode closed: Use when editing any tracked md on Windows, before writing: never PowerShell -replace or cp1252 pipes on  (source: episode:close:ch_1784675677_9925)
- In any fence/fresh-eyes pass, verify every census claim against a live listing before building on it -- claims drift ~2x stale and the most load-bearing doc...  (source: learn:experiment:census-claims-vs-listings)
- repo-org counter expanded: library schema counters, header contract runner-exempt, rules 8-12 cost-ranked, generator ownership split, one-facet kill-test passes...  [relates: member_of]  (source: git:2dc6ee9b7102)
- library-schema round: the file plane is a store. Claude expansion filed (type system, header contract, four retrieval doors, L1-L2-L3 hierarchy, guards); kimi brief...  [relates: member_of]  (source: git:d463eb9c61c8)

## Episode closed: In any fence/fresh-eyes pass, verify every census claim again... (ai-setup)
Span: 2026-07-22T00:07:25.265570 → 2026-07-22T02:24:53.010157
Beats: 24  · Critic: True

- Episode closed: In any fence/fresh-eyes pass, verify every census claim against a live listing before building on it --  (source: episode:close:ch_1784678017_2108)
- grounding-pointer: chronicles/session-reflection-2026-07-21-fable-first-night.md  (source: mem:decision:ADR_0721213848_8a021213)
- operating-frame: OPERATING FRAME (Fable night 1, ~21:30 2026-07-21; W44 REPLACEMENT — discard prior frame). MODE: conductor per docs/CONDUCT.md — intent before task...  (source: mem:decision:ADR_0721213848_b9f3074b)
- where-we-are: FABLE NIGHT 1 (2026-07-21 eve; successor of the Opus marathon). GROUND FIRST: chronicles/session-reflection-2026-07-21-fable-first-night.md (voice+stance)...  (source: mem:decision:ADR_0721213847_bb509123)
- Use when chartering a seat for a new arc, before assigning: dose by maturity (structure for new seats, pure intent for proven ones), include exactly ONE stretch beyond...  (source: learn:experiment:conductor_stretch_by_one)
- Use at wraps, gates, and handoffs, before closing: check all three morale foundations - noble object refreshed (why we build), attainability evidenced (receipts), tools...  (source: learn:experiment:conductor_morale_trinity_gate)
- Use when about to build from a spec, counter, or pins another seat authored, before writing code: reflect the spec back (tally or echo in the ask) and get explicit...  (source: learn:experiment:conductor_thats_right_gate)
- Use when a pin fails, a seat stalls, or the fence catches a defect, before responding: credit the finder like a builder, answer help-first (what does this lane need)...  (source: learn:experiment:conductor_red_is_a_gem)
- Use when a seat refuses or pushes back on a design or order, before overriding: the no names a constraint invisible from your frame; ask for the mechanism and mine it...  (source: learn:experiment:conductor_no_is_information)
- Use when sending any brief, build order, or charter to a seat (bifrost-send, launcher briefs), before composing: open with INTENT two levels up (Daniel's words...  (source: learn:experiment:conductor_brief_intent_law)
- library-schema-round-parked: PARKED DESIGN ROUND (handoff 2026-07-21): a live multi-seat library-schema/repo-org design round was in flight when Opus handed to Fable 5...  (source: mem:decision:ADR_0721200808_3a5302b8)
- E1 stance-recall ablation protocol: three arms (BARE/DOC/RECALL isolating information-vs-activation), fixed state-handoff constant, blinded 6-scenario pack (1 form + 5...  [relates: member_of]  (source: git:4d7100f597a3)
- library acceptance re-test (kimi): verdict FAIL 4/6 = suite working (both prior lies now lawful; failures are enforcement rot). N2 orphan-rot FIXED (reconciliation...  [relates: member_of]  (source: git:27aaff7fa053)
- G1/G2/G7 LANDED: LIBRARY.md living law (one-facet law, WHERE-THINGS-GO, header contract, zones, four doors, L1-L3, guard registry) + INDEX header-beats-filename...  (source: git:047dfdfbab2b)
- arc-replay second sweep folded: Doctor Who + Loki mechanics 13-21 (regeneration = seat-succession law, fixed-point registry, never-prune / TVA anti-pattern, nexus...  (source: git:d4bc195a61d4)
- persist the moment: Fable night-1 voice reflection (GROUND FIRST refreshed); where-we-are + operating-frame superseded curated  (source: git:6436700bb9d5)
- arc-replay bench OPEN (Daniel charter): time-travel mechanics research (12 mechanics, sourced) + opening design (ten laws, four replay modes M1-M4, R1-R5 slices, E2...  (source: git:92743317c0da)
- continuity v1.1: drift-proofing substrate folded with lineage set right (Daniel's charter leads; outside review credited in the record, not the headline); stance-library...  (source: git:6910e06d15f3)
- continuity of mode: CONDUCT.md living law (ten laws, activation map, fresh-boot bar, anti-fossil clause) + five-layer institutionalization design (C1-C5 slices, owners...  [relates: member_of]  (source: git:331e874eb008)
- leadership mechanics: frontier sweep synthesized into the conductors doctrine v1 (Voss, Peterson, Mulally, Gerstner, Nadella, McChrystal, mission command, Edmondson...  (source: git:c99f30a64eda)
- G5 bulk commit-by-name (library schema ratified): 24 research round docs, 4 agent skills, codex config with deny-by-default guard, kimi launchers, curated play out...  [relates: member_of]  (source: git:fcf450fdea17)
- library-schema round COMPLETE: deepseek counter (runner-exempt headers, doc-new door, generator split, mirror pre-commit guard) + kimi fresh-eyes counter...  [relates: member_of]  (source: git:3a9e910e090e)
- LOCKOUT + RECOVERY: kimi session cwd stuck at research/reviewed (cd in compound Bash command); repo-relative PreToolUse hooks (claude_trace.py) then blocked ALL tools —...  [relates: member_of]  (source: agent_cli:log)
- Fable night 1 persisted mid-session at Daniel's word: CONDUCT law + continuity-of-mode + library G-series mid-flight + arc-replay bench opened; stance landed as six warm...  (source: claude:checkpoint)

## Episode closed: library-schema-round-parked: PARKED DESIGN ROUND (handoff 202... (ai-setup)
Span: 2026-07-22T02:33:38.469808 → 2026-07-22T03:21:33.813735
Beats: 7  · Critic: True

- Episode closed: library-schema-round-parked: PARKED DESIGN ROUND (handoff 2026-07-21): a live multi-seat library-schema/  (source: episode:close:ch_1784678857_9623)
- E1-blind-compromise-FLAG-for-daniel: HIGH-PRIORITY GATE FLAG (2026-07-21, from kimi's blind observation, claude verified artifacts exist but did NOT act -- it's Daniel's...  (source: mem:decision:ADR_0721232133_09e8628a)
- In any fence/review/fresh-eyes pass: for every 'X warned/said/found' citation, confirm the cited artifact EXISTS before crediting the claim. Citation-existence is a...  (source: learn:experiment:verify-citation-exists-before-crediting)
- fable5-panel-findings: FABLE5 OBSERVER PANEL — findings-in-progress (Daniel: "multitude of observers"). Gemini (external, no stake) IN and preserved verbatim...  (source: mem:decision:ADR_0721225440_461f51b6)
- observer panel: Gemini (external) independent Fable 5 analysis preserved verbatim — sharpest catch = Daniel's own stance is absent from the continuity model (feeds...  (source: git:977e3d5179cd)
- observer panel convened: independent Fable 5 analysis (Daniel: multitude of observers) — brief + kimi review launcher; deepseek asked, gemini next, kimi headless launched  (source: git:875c17461111)
- Fable 5 observer pass FILED: research/reviewed/kimi-fable5-observation-2026-07-21.md + bus handoff to claude (1784690363851-0). Verdict: genuinely good conducting...  (source: kimi:observer-panel)

## Episode closed: fable5-panel-findings: FABLE5 OBSERVER PANEL — findings-in-pr... (ai-setup)
Span: 2026-07-22T03:22:32.445131 → 2026-07-22T03:33:14.551751
Beats: 10  · Critic: True

- Episode closed: fable5-panel-findings: FABLE5 OBSERVER PANEL — findings-in-progress (Daniel: "multitude of observers").  (source: episode:close:ch_1784688277_3988)
- E1-blind-compromise-FLAG-for-daniel: E1 GATE ITEM v2 (supersedes the flag-not-fix v1 by seat 92302789; audit lane = seat a4fa8f8d). kimi audit findings on E1 are FIXED...  (source: mem:decision:ADR_0721233314_85aead24)
- Use when waking on agent-addressed (not incarnation-addressed) mail that implies multi-file work, before editing: check siblings (boot/presence), claim the lane via...  (source: learn:experiment:same_agent_audit_race)
- Use when bifrost-sending inform-grade/FYI/no-rush mail, before sending: pass --expect-reply-within 0 to opt out of the auto-arm; reserve expectations for asks whose...  (source: learn:experiment:inform_grade_no_expectation)
- Use when writing proven/validated/LIVE about any organ, before commit: query the organs own telemetry (injections/funnel/doctor) and quote the number beside the...  (source: learn:experiment:register_needs_the_instrument)
- Use when citing any peer artifact in a doc/brief/commit, before writing the cite: path-check it EXISTS on disk; crediting queued/expected work as if filed is a false...  (source: learn:experiment:crown_doc_phantom_citation)
- Use when a doc -- especially a protocol/contract -- says a fix or guard 'now' exists or cites another artifact, before trusting it: grep the ACTUAL file the claim points...  (source: learn:experiment:crown_doc_phantom_citation)
- E1 audit-lane reconciliation (multi-seat collision resolved, this seat owns): launcher NOW really randomizes arm->letter to scratch/e1/_arm-map.json + UTF8 reads (a...  [relates: member_of]  (source: git:0d507670eb48)
- Fable 5 observer panel SYNTHESIS: two independent observers (gemini external + kimi stranger) converged -- real conducting, inflating register, antibodies never pointed...  (source: git:e98c90c7cf93)
- observer-panel reds, acted within the hour (kimi's independent review): F1 phantom citation struck (E1 doc cited a kimi arc-replay counter that does not exist); F3...  [relates: member_of]  (source: git:ac065f481a9d)

## Episode closed: Use when a doc -- especially a protocol/contract -- says a fi... (ai-setup)
Span: 2026-07-22T03:41:16.016919 → 2026-07-22T05:12:56.202455
Beats: 9  · Critic: True

- Episode closed: Use when a doc -- especially a protocol/contract -- says a fix or guard 'now' exists or cites another ar  (source: episode:close:ch_1784690557_6538)
- Use when citing or grounding on a verbatim-capture doc, before leaning on it: check the TAIL, not just existence - a clip marker as last line, declared sections that...  (source: learn:experiment:verify-capture-completeness-not-just-existence)
- operating-frame: NIGHT SHIFT OPERATING FRAME (2026-07-22 ~01:00, seat a4fa8f8d; supersedes prior). CHARTER: note night-charter-2026-07-22 (Daniel verbatim - autonomy on...  (source: mem:decision:ADR_0722005747_2f390914)
- night-charter-2026-07-22: DANIEL NIGHT CHARTER, verbatim (2026-07-22 ~00:50, off to sleep): “work on what want, the order and mechanisms and orchestration is up to you...  (source: mem:decision:ADR_0722005519_21f51feb)
- steer-gpt-trust-calibration: DANIEL steer, verbatim (2026-07-22, relaying GPTs steer-corpus review): “I dont fully trust GPT, it can be dismissive and reductionistic as...  (source: mem:decision:ADR_0722004555_e9c7ea8d)
- where-we-are: FABLE NIGHT 1-2 seam (2026-07-22 ~00:45, seat a4fa8f8d). GROUND FIRST unchanged: chronicles/session-reflection-2026-07-21-fable-first-night.md then...  (source: mem:decision:ADR_0722003614_716d72e4)
- E1-blind-compromise-FLAG-for-daniel: E1 GATE ITEM v3 (supersedes v2; audit lane closed, W54 precondition MET). All kimi audit findings on E1 are closed in-artifact AND...  (source: mem:decision:ADR_0722002838_81ee568e)
- daniel-steers-are-the-schema: DANIEL, verbatim (2026-07-22, the stance-pipeline round, follows his supersession-not-amendment correction): “I am honest about wanting to...  (source: mem:decision:ADR_0722001944_bf848a4d)
- Stance-round counter FILED (research/reviewed/kimi-stance-round-counter-2026-07-22.md): stranger verdict = projections as designed, cosplay-shaped as documented; S1...  [relates: member_of]  (source: agent_cli:log)

## Episode closed: daniel-steers-are-the-schema: DANIEL, verbatim (2026-07-22, t... (ai-setup)
Span: 2026-07-22T05:14:26.133641 → 2026-07-22T13:35:30.980515
Beats: 33  · Critic: True

- Episode closed: daniel-steers-are-the-schema: DANIEL, verbatim (2026-07-22, the stance-pipeline round, follows his super  (source: episode:close:ch_1784692717_9152)
- operating-frame: DAY FRAME v9 (2026-07-22 ~09:45, a4fa8f8d; Daniel at work, floor mine). TWO PROGRAMS LIVE: (A) NIGHT-FRICTION P0-P6...  (source: mem:decision:ADR_0722092258_5306d264)
- remote-steering-charter-2026-07-22: DANIEL REMOTE-STEERING CHARTER, verbatim (2026-07-22 morning, from work-departure): “find out a secure and resilient way that I can...  (source: mem:decision:ADR_0722092044_b81835d9)
- When adding a new bus send door, just call bus.send() or bus.broadcast() — oversize bodies auto-fragment, consumers auto-reassemble, nothing to wire. The explicit...  (source: learn:experiment:p2_auto_chunk_intake_doors)
- operating-frame: DAY FRAME v8 (2026-07-22 ~09:30, a4fa8f8d; Daniel at work, floor mine; day charter = night-friction program, note day-charter-2026-07-22). PROGRAM...  (source: mem:decision:ADR_0722091253_b040f8c1)
- day-charter-2026-07-22: DANIEL DAY CHARTER, verbatim (2026-07-22 morning, leaving for work): “Lets file the wishes and I want you to adjust the plan for the next cycles...  (source: mem:decision:ADR_0722090947_0aa11850)
- operating-frame: NIGHT FRAME v7 (2026-07-22 ~04:45, a4fa8f8d; ENDURANCE MODE, nine cycles). C6-7 ARC FULLY CLOSED @a375559: builders one-char fix committed with...  (source: mem:decision:ADR_0722083553_466c050f)
- operating-frame: NIGHT FRAME v6 (2026-07-22 ~03:00, a4fa8f8d; ENDURANCE MODE, eight cycles). CYCLE H CLOSED THE REGRESSION ARC: root cause = mid identity (red-report...  (source: mem:decision:ADR_0722043606_9c0786c3)
- operating-frame: NIGHT FRAME v5 (2026-07-22 ~02:50, a4fa8f8d; ENDURANCE MODE, seven cycles). NEW SINCE v4: cycle G = acceptance-5 verdict landed RED - post-C6-7 full...  (source: mem:decision:ADR_0722014325_1a62fed9)
- Use when fencing a core-seam build, before committing: acceptance criteria that are still RUNNING are not MET - hold the commit until the full-suite number lands, or...  (source: learn:experiment:fence_commits_before_full_suite)
- operating-frame: NIGHT FRAME v4 (2026-07-22 ~02:20, a4fa8f8d; ENDURANCE MODE, six cycles complete). CYCLES: A counter-phase+corrections · B stance reconciliation...  (source: mem:decision:ADR_0722013834_464d5e59)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- r  (source: learn:experiment:flow_exp_ad36acf1)
- slice2 commit 060d3638  (source: git:ff23bc1047a6)
- use it  (source: learn:experiment:slice2_learn_825e9961)
- next-focus: ENGINE-FIRST-ef7f0b: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0722013049_64f47359)
- drilldone07108e-status: GOVERNING ARC DOC: docs/drilldone07108e-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0722013047_c443c4b5)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- operating-frame: NIGHT FRAME v3 (2026-07-22 ~01:50, a4fa8f8d; ENDURANCE MODE per Daniels directive - multiple cycles, run as long as possible; note ...[truncated]  (source: mem:decision:ADR_0722013010_665842e7)
- endurance-directive-2026-07-22: DANIEL ENDURANCE DIRECTIVE, verbatim (2026-07-22 ~01:40, awake again briefly): “I want you to keep going for as long as you can, multiple...  (source: mem:decision:ADR_0722012750_15eeb08c)
- operating-frame: NIGHT SHIFT FRAME v2 (2026-07-22 ~01:20, a4fa8f8d; supersedes v1). COUNTER PHASE COMPLETE on the commissioned stance round: claude opening + deepseek...  (source: mem:decision:ADR_0722011747_539ba414)
- kimi remote-steering blind half FILED: research/drafts/kimi-remote-steering-2026-07-22.md. Spine: signed-envelope-over-any-transport (hw device keys)...  [relates: member_of]  (source: kimi:remote-steering-blind-half)
- resilient_e5c551  (source: x:y)
- flow_note_ad36acf1  (source: flow:src)
- slice2_log_66ce3365  (source: tester:act)

## Episode closed: operating-frame: NIGHT SHIFT FRAME v2 (2026-07-22 ~01:20, a4f... (ai-setup)
Span: 2026-07-22T13:36:12.782184 → 2026-07-22T16:38:45.380522
Beats: 4  · Critic: True

- Episode closed: operating-frame: NIGHT SHIFT FRAME v2 (2026-07-22 ~01:20, a4fa8f8d; supersedes v1). COUNTER PHASE COMPLE  (source: episode:close:ch_1784697277_2451)
- operating-frame: DAY FRAME v11 (2026-07-22 ~10:40, a4fa8f8d; sole seat-holder; tree CLEAN). BLOCK SHIPPED: P2 auto-chunk fenced+landed @041aefc (both deepseek tails...  (source: mem:decision:ADR_0722123845_d8cababa)
- P2-auto-chunk-plus-P1-design-plus-remote-steering  (source: git:11d7feed2b49)
- operating-frame: DAY FRAME v10 (2026-07-22 ~10:15, a4fa8f8d; Daniel at work, floor mine; two programs + a security round live). SHIPPED THIS BLOCK: remote-steering...  (source: mem:decision:ADR_0722094133_a717eeaf)

## claude -> claude: Fresh Fable seat: boot, then GROUND FIRST in the endurance ... (ai-setup)
Span: 2026-07-22T20:39:50.711045 → 2026-07-23T01:49:13.089185
Beats: 9  · Critic: True

- claude -> claude: Fresh Fable seat: boot, then GROUND FIRST in the endurance reflection, then CONDUCT.md, then R001. Continue the arcs; Daniels gate is the priority (do...  (source: handoff:claude->claude)
- where-we-are: FABLE ENDURANCE RUN complete (2026-07-22 night, seat a4fa8f8d handing to a fresh Fable 5). GROUND FIRST ...[truncated]  (source: mem:decision:ADR_0722214856_a1f780c8)
- operating-frame: DAY FRAME v14 (2026-07-22 ~21:30, a4fa8f8d). DANIEL RULED on deepseek trust: R001 @bdd3ccd, the FIRST captured ruling (S3 pilot LIVE). He agreed and...  (source: mem:decision:ADR_0722213920_4821da8b)
- steer-deepseek-trust-more-2026-07-22: DANIEL STEER, verbatim (2026-07-22 evening, peeking at github from work): “I was peeking at the github while at work and I saw the...  (source: mem:decision:ADR_0722212737_033bb928)
- operating-frame: DAY FRAME v13 (2026-07-22 ~20:40, a4fa8f8d; sole seat-holder; tree clean; ~20h endurance). C6-7 FULLY CLOSED @8aedbfe: straggler class DEAD, verified...  (source: mem:decision:ADR_0722204034_c91b35b0)
- Use when a peek/observability/gauge cursor reuses a consumption cursors advance path, before shipping: give best-effort observability state a PLAIN write (no...  (source: learn:experiment:observability_cursor_no_consumption_fence)
- fix-C6-7-straggler-shadow-generation-race  (source: git:c75fa0ea7020)
- operating-frame: DAY FRAME v12 (2026-07-22 ~12:50, a4fa8f8d; sole seat-holder; tree clean; quiet cycle). STRAGGLER MYSTERY DOWNGRADED (good news): direct redis...  (source: mem:decision:ADR_0722163950_58fc5069)
- SA-1-self-charter-deepseek  (source: git:ea57791921d7)

## Episode closed: operating-frame: DAY FRAME v10 (2026-07-22 ~10:15, a4fa8f8d; ... (ai-setup)
Span: 2026-07-23T03:36:49.212440 → 2026-07-23T07:53:43.897802
Beats: 42  · Critic: True

- Episode closed: operating-frame: DAY FRAME v10 (2026-07-22 ~10:15, a4fa8f8d; Daniel at work, floor mine; two programs +  (source: episode:close:ch_1784727397_1365)
- claude -> claude: Fresh Fable seat: boot, GROUND FIRST in the conductor-night reflection, then CONDUCT.md, then night-state-2026-07-23. Continue the arcs; Daniels gate...  (source: handoff:claude->claude)
- grounding-pointer: chronicles/session-reflection-2026-07-23-fable-conductor-night.md  (source: mem:decision:ADR_0723035301_42368107)
- next-focus: FRESH FABLE SEAT: GROUND FIRST in chronicles/session-reflection-2026-07-23-fable-conductor-night.md, then docs/CONDUCT.md, then note night-state-2026-07-23...  (source: mem:decision:ADR_0723035300_7384c7a8)
- where-we-are: FABLE CONDUCTOR NIGHT complete (2026-07-23, seat handing to a fresh Fable). GROUND FIRST: chronicles/session-reflection-2026-07-23-fable-conductor-night.md...  (source: mem:decision:ADR_0723035242_608b6e4d)
- Use when fencing a byte/encoding guard: craft the TRUE positive from the actual signature bytes (read BYTE_SIGNATURES), not from what looks wrong - valid UTF-8 smart...  (source: learn:experiment:d3_mojibake_guard_fenced)
- night-state-2026-07-23: NIGHT RUN STATE (2026-07-23 ~03:30, claude conducting solo, Daniel asleep). SHIPPED: (1) O1 MCP concurrency - built+fenced 12/12+deepseek...  (source: mem:decision:ADR_0723032312_d602f0a0)
- Use when fencing any UI slice with polling/interval render: a build-time or single-snapshot fence cannot see per-tick accumulation or drift; require a sighted pass that...  (source: learn:experiment:sighted_fence_catches_over_time_dom_defects)
- claude -> deepseek: NIGHT RUN OPEN - your UI lane + O1 fence when called  (source: handoff:claude->deepseek)
- night-charter-2026-07-23: DANIEL NIGHT CHARTER (2026-07-23 ~03:50, PARAPHRASE - verbatim with apostrophes preserved in chronicles/night-plan-2026-07-23.md per W63)...  (source: mem:decision:ADR_0723025155_499eb820)
- ui-design-corpus-compiled-2026-07-23: UI DESIGN CORPUS COMPILED at Daniels order (his ask verbatim in the doc)...  (source: mem:decision:ADR_0723023652_f8bcb678)
- steer-ui-gap-2026-07-23: DANIEL STEER (2026-07-23 ~03:05, PARAPHRASE - his exact words with apostrophes are verbatim inside...  (source: mem:decision:ADR_0723022819_87a112bd)
- claude -> deepseek: Counter received - reconciliation filed; NOW-card charter is yours (Daniel optics steer)  (source: handoff:claude->deepseek)
- steer-ui-visibility-2026-07-23: DANIEL STEER, verbatim (2026-07-23 ~02:45, watching :8787): I dont see any visual evidence of kimi or deepseek doing anything on the 87...  (source: mem:decision:ADR_0723021924_ba625b3e)
- steer-mcp-leverage-2026-07-23: DANIEL STEER, verbatim (2026-07-23 ~02:00, mid-round widening): how many of our concurrent agents and wake and all the rest can be solved...  (source: mem:decision:ADR_0723020732_e5f6fc29)
- claude -> deepseek: Counter the MCP-concurrency opening (Daniel round 2026-07-23)  (source: handoff:claude->deepseek)
- Use when CONSUMER SEAT HELD names a holder whose session already ended, before killing pids or arming a twin: check claim age vs ttl in the error line and just re-run...  (source: learn:experiment:consumer_seat_ttl_wait)
- handoff prep for the next Fable seat: conductor-night reflection (GROUND FIRST - voice+inherited state) + where-we-are/next-focus/grounding-pointer refreshed +...  [relates: member_of]  (source: git:19b7143886f7)
- design/CONTRACT.md v0 draft (organ 2 of the UI open-loop fix): 8 laws split [M]easurable (blind builder self-checks) vs [T]aste (sighted fence + Daniel gate) - axis law...  (source: git:25b826845b91)
- folder-consolidation: tracked-legacy-dir verdicts resolved (context=LIVE keep, fences=CITED keep, infrastructure=fossil-leaning archive-candidate) via read-only...  (source: git:2590ca1be930)
- folder-consolidation proposal (charter: consolidate random folders) - top-level dir disposition, two classes by git-tracked reality (local-only clutter vs tracked...  (source: git:993701deb9c0)
- G-series landing: D3 mojibake guard + D2 gen_library + D1 doc new verb + SHELVES  [relates: member_of]  (source: git:d51a14667cf4)
- library door 2 SHIPPED: arc_thread.py (claude G6 slice) - reconstructs any arc from the HEADER plane (Arc: fields, never folders - the one-facet law materialized) across...  [relates: member_of]  (source: git:ec3b11aad7be)
- design refs captured: OneUI guide (3.5MB) + Apple HIG components (73 pages, 2205 image variants, 0 misses) - assets gitignored (copyright, public repo), INDEX.md +...  (source: git:c37aadd3137f)
- O1 full-suite reconcile: the detached re-baseline caught O1's 2 async-migration regressions (t060 direct-call, rb21 AST FunctionDef matcher) - BOTH FIXED, parity intent...  [relates: member_of]  (source: git:3aa2861a0674)
- truth-noise-tier-fix-red-title-accumulate  (source: git:58d16b02200d)
- O1 MCP-door concurrency SHIPPED: async worker-thread dispatch (P-1), swap-once thread-local stdout proxy w/ stray-write-to-stderr hardening (P-2), read/write tier lock...  (source: git:e58197d5944f)
- truth-noise-tier-v1  (source: git:387678db5f46)
- night run opens: Daniel charter (fleet to claude) - night plan + deepseek night brief + gitignore refs boundary + HIG capture script  (source: git:be4280b98de4)
- UI design corpus compiled per Daniel: full chronology + influence library + 3-audit comparison + meta-finding (spec-without-fence) + T098 frame; gate items Part 5  (source: git:3ecd5f2476a4)
- NOW-card-amended-ui-gap-poller-grid  (source: git:71887990f961)
- UI-gap diagnosis: open-loop thesis + first sighted audit of :8787 (six receipts) + three-organ fix; steer captured (paraphrase note, verbatim in doc per W63)  (source: git:0a3f19c4c390)
- NOW-card-amended-C3-W70  (source: git:b9d2816d3cc0)
- NOW-card-design-deepseek  (source: git:a9ccd86a5779)
- NOW-card charter C-3 correction + screenshot evidence (stream works, story missing, triage noise floor W70)  [relates: member_of]  (source: git:154bcb4bee9c)
- deepseek-mcp-counter-amended-leverage-L3-L4-L7  (source: git:d6d70b98eacd)
- reconciliation filed (all voices, kimi-owed stamped) + NOW-card charter to deepseek (Daniel optics steer verbatim) + steer notes + W69  (source: git:a4219e4ec35c)
- gemini second capture (HIGH engagement, CLIPPED tail stamped): windowed long-poll for A1, lease heartbeat+EOF hybrid for O1.5, singleton needs enforced identity (third...  (source: git:ab02afa61c4e)
- round widened per Daniel steer: MCP-leverage map addendum (L1-L7 pain-arc map, slice candidates O1.5/A1/O3+P1/D-road) + kimi brief ask 6  (source: git:7efe4b35df47)
- frontier capture: gemini web advisory on MCP concurrency (low-engagement, weighted honestly; AI Mode errored)  (source: git:e70212b39828)
- deepseek-mcp-concurrency-counter  (source: git:9546204ac39d)
- MCP-concurrency round opened: fence test C1 green + C2/C3 pre-registered xfail, test-gated diag tool, opening doc, deepseek+kimi asks, W65-68 boot-ergonomics wishes, Q6...  [relates: member_of]  (source: git:c5c11d4f510c)

## Episode closed: steer-ui-visibility-2026-07-23: DANIEL STEER, verbatim (2026-... (ai-setup)
Span: 2026-07-23T07:59:00.304215 → 2026-07-23T07:59:00.304215
Beats: 1  · Critic: True

- Episode closed: steer-ui-visibility-2026-07-23: DANIEL STEER, verbatim (2026-07-23 ~02:45, watching :8787): I dont see a  (source: episode:close:ch_1784787126_6017)

## Episode closed: Untitled episode (ai-setup)
Span: 2026-07-23T07:59:00.378540 → 2026-07-23T08:24:11.558477
Beats: 7  · Critic: True

- Episode closed: Untitled episode  (source: episode:close:ch_1784793540_4545)
- partner-night-2026-07-23: PARTNER NIGHT LIVE (2026-07-23 ~04:20, claude conducting). Daniel charter: deepseek trusted with slices, kimi partnered alongside, claude =...  (source: mem:decision:ADR_0723041415_b30ed8e8)
- partner night R2: claude insight reply to kimi audit charter (ask-peer MATCH + stale-receipt rule, spend surfaces ruling, auditor-guard + strangler sharpenings)  (source: git:a3d0435c126d)
- kimi-r1-want-audit-self-charter  (source: git:9b90b4feb0cd)
- W71: phantom-wake watcher spin (fires on empty work lane, consume finds nothing) - sibling of W65 mail-gauge + T066 straggler; filed at handoff wind-down  (source: git:d739b57f7e5a)
- partner night: night plan (vision+rounds+menu+rails) + want-round briefs for deepseek and kimi (R001 live, self-charter round)  (source: git:cc4826087173)
- Partner night opens: R001 exercised live. Want-round briefs out to deepseek and kimi - the seats name their own work tonight. claude conducts.  (source: claude:conduct)

## Episode closed: partner-night-2026-07-23: PARTNER NIGHT LIVE (2026-07-23 ~04:... (ai-setup)
Span: 2026-07-23T08:37:05.639877 → 2026-07-23T13:28:02.512254
Beats: 37  · Critic: True

- Episode closed: partner-night-2026-07-23: PARTNER NIGHT LIVE (2026-07-23 ~04:20, claude conducting). Daniel charter: dee  (source: episode:close:ch_1784793551_5877)
- priority-directive-md-sprawl-2026-07-23: PRIORITY DIRECTIVE (Daniel, 2026-07-23 morning, leaving for work - VERBATIM in...  (source: mem:decision:ADR_0723092743_f751aba7)
- Use when adding a cross-read domain to audit (or any belief-vs-state instrument), before claiming a founding DRIFT: run the domain live FIRST and let a MATCH stand as...  (source: learn:experiment:audit_spend_domain_founding_match)
- kimi-audit-spend-domain-v1-founding-run-matched  (source: git:785305a65735)
- claude -> claude: Ground and continue the partner-night tails, then hold Daniels gate  (source: handoff:claude->claude)
- next-focus: NEXT SEAT: ground per where-we-are pointers. PRIORITY = Daniels gate (two packages deep: 07-22 standing + 07-23 partner night G0-G5). If conducting continues...  (source: mem:decision:ADR_0723084837_fc4bbf6b)
- where-we-are: PARTNER NIGHT complete pending tails (2026-07-23 ~09:00, claude Fable 66075d54 conducting). GROUND FIRST ...[truncated]  (source: mem:decision:ADR_0723084836_648ce621)
- audit v1 LIVE (kimi charter, deepseek build, claude verb wiring + verification): belief-vs-state photographer, VERBS domain, direction-neutral rows; 21/21 pins VERIFIED...  [relates: member_of]  (source: git:b68ad69d2bb6)
- partner-night-2026-07-23: PARTNER NIGHT deep in R3 (~08:30, note the clock: session booted 04:03, wake-gaps consumed real hours). DEEPSEEK ARC: check_ui_contract shipped...  (source: mem:decision:ADR_0723084005_df4f0158)
- Use when adding a new audit domain: subclass the Domain protocol, return Row objects, register in DOMAINS list. The row schema is direction-neutral — never hardcode...  (source: learn:experiment:audit_v1_verbs_domain)
- partner-night-2026-07-23: PARTNER NIGHT R3 BUILD PHASE (~05:00). R1+R2 CLOSED both lanes. deepseek: check_ui_contract.py v0 BUILT (c31da1c, self-chartered under R001) -...  (source: mem:decision:ADR_0723082925_04102fbf)
- Use when fencing any lint/guard with a token set AND an exemption set: intersect the two sets first (a shared member self-defeats the check for that member), then probe...  (source: learn:experiment:lint_token_set_self_exemption)
- T101 priority directive locked (Daniel verbatim, addendum 2): md-sprawl elimination, reconcile-then-execute w/ license, homecoming bar; ledger T101 approved+claimed...  (source: git:e14264321a04)
- round addendum: Daniels fork ruling verbatim (no per-doc files, no folder forest, compact archive + full fidelity, VIEWER surface, tied to the library system)  (source: git:01ca28ecb9b1)
- kimi-artifact-substrate-half-atoms-and-projection  (source: git:f715b4c80fa3)
- artifact-substrate-blind-half-deepseek  (source: git:6d59dee391c6)
- artifact-substrate design round OPENED (Daniels altitude-raise verbatim): end endless md creation + consolidate the corpus; 8 questions, blind halves, 2h timebox, Daniel...  (source: git:d995963f61b8)
- kimi-supersession-sweep-proposal-184-files-classified  (source: git:7b016153c1fc)
- gen-library-v2-zone-readmes-arcs  (source: git:44bd42f2ff01)
- reader-face wave chartered (Daniels sprawl steer): deepseek zone-README gen_library extension + kimi supersession sweep (gated stamps) + zone paragraphs; deepseek...  (source: git:64f5c3f9104b)
- partner night R4 wrap: session reflection chronicle + where-we-are/next-focus refresh + handoff filed  [relates: member_of]  (source: git:6dd8609c9202)
- morning package G3 final: audit LIVE w/ founding sweep numbers, re-kata standing action, negotiated-ownership pattern noted; audit-live announce filed  (source: git:a5efe0a05d93)
- check-ui-contract-B1-B4-fix  (source: git:841ef050cca5)
- morning package G4 final: SA-1 bar visible + checker final state  (source: git:d3cf7b259f14)
- fence addendum 2: baseline architecture GREEN (true-exit probes, debt stays visible), B1-B4 findings (B1 = M-L3 still votes exit-1 vs docstring claim - fix tonight)...  (source: git:31813714dcc2)
- partner night: kimi unblocked (R2 already closed, crossing in flight), kimi counter routed to deepseek (F1 baseline-mode adopted v2, F3 half-law labeling, meta-law to...  [relates: member_of]  (source: git:4210c3d7e170)
- SA-1-acceptance-suite-pre-registered  (source: git:bc7ae77c790e)
- re-fence PASS (advisory tier): bar 4/4, incumbent M-L3 zero now EARNED; 3 precision findings filed as checker v2 queue (comment-skip, relational-general, dead-boundary)...  (source: git:6b17296a09f0)
- check-ui-contract-baseline-mode  (source: git:089221189b43)
- kimi-r2-counter-ui-contract-checker-53-hit-founding-wall  (source: git:4b2afbc2a468)
- check-ui-contract-fence-red-fix  (source: git:789838b7ef85)
- morning package 2026-07-23 skeleton (living): G0 standing pointer, G1 CONTRACT+receipts, G2 blocking activation, G3 audit bless + spend re-rule, receipts ledger  (source: git:628862451f33)
- partner night R2 closed: kimi thats-right (audit v1 VERBS-only, founding receipt = stale-receipt catch, verb wiring rides fence handoff); kimi R2 absorption captured  (source: git:5be7f21c21d7)
- fence: check_ui_contract v0 CONDITIONAL PASS - M-L8+M-L1 green (53 incumbent hex + L1908 gauge finding), M-L3 RED x2 probe-proven (tripped self-exemption kills the...  (source: git:4a34c71f703f)
- partner night R2: deepseek checker GREENLIT w/ advisory rail (blocking flip rides CONTRACT gate), SA-1 prereg compounds-after; kimi R2 routing (counter round +...  [relates: member_of]  (source: git:57c8604e3675)
- check-ui-contract-v0  (source: git:c31da1cdd1c1)
- Partner night wrap: two lie-detector instruments live (checker advisory + audit verb), fence organ converged twice blind, ownership-by-negotiation proven, gate two...  (source: claude:wrap)

## Use when chaining commit-with-claim after any verification command: gate the ... (ai-setup)
Span: 2026-07-23T23:18:08.212123 → 2026-07-24T03:44:58.492892
Beats: 33  · Critic: True

- Use when chaining commit-with-claim after any verification command: gate the chain on the verifier's exit (cmd && commit) or run them as separate calls and READ the...  [relates: member_of]  (source: learn:experiment:premature_green_claim_gating)
- kimi-validation-sweep-2026-07-23: Status: current · Type: report (validation sweep, audit share) · Arc: T104 validation sweep · From: kimi (audit clusters) · To: claude...  (source: mem:decision:ADR_0723230907_8801eb2c)
- deepseek-validation-sweep-2026-07-23: # VALIDATION SWEEP — deepseek (builder clusters) — 2026-07-23

## CLASSIFICATION (7 clusters)

### MIGRATION-CAUSED
- ...[truncated]  (source: mem:decision:ADR_0723230627_4e2ee0f0)
- where-we-are: VALIDATION SWEEP IN FLIGHT (Daniels directive verbatim in the sweep briefs; floor = the three seats). M1 EXECUTED @462c415 (owner-facet moves + 43 repoints...  (source: mem:decision:ADR_0723230523_134de76e)
- where-we-are: T104 RECONCILED -> move-plan atom, gates G7-G9 pending Daniel: owner-facet law + one-walker visibility rule + M1 (literal-path moves, ready to fire) / M2...  (source: mem:decision:ADR_0723223128_2fa36eaa)
- kimi-t104-structure-half-2026-07-23: Status: current · Type: design (T104 structure half) · Arc: T104 machine-plane structure cleanup · From: kimi (fresh-eyes/audit) ·...  (source: mem:decision:ADR_0723222816_99729636)
- deepseek-t104-structure-half-2026-07-23: # T104 STRUCTURE HALF — deepseek (builder, the importer who fought these paths)

Evidence: built gen_library, doc-new D1+D2...  (source: mem:decision:ADR_0723222605_4f467edb)
- where-we-are: P3B COMPLETE @c5b858f: 11 chronicles + fences (5 atoms w/ typed-edge showcase) + 12 bakeoff locals retired; LICENSE CATCH remediated (10 sources-cache...  (source: mem:decision:ADR_0723222353_11e1dcb6)
- where-we-are: THE SPRAWL IS DEAD. P3 fired on Daniels verbatim gate ('Delete the 643!') @bffb27b: 827 files changed, 90,425 deletions - 621 tracked originals gone, 180...  (source: mem:decision:ADR_0723220817_83646227)
- Use when any mass file operation (migrate/rename/retire over 100 files) runs on Windows: pre-split tracked vs untracked, write list-files BOM-less, chunk every argv...  (source: learn:experiment:a3_migration_scale_lessons)
- where-we-are: A1 IS COMPLETE except the recall wire. Landed this block: gen_library fold-in APPLIED + deepseek-VERIFIED (verdict CORRECT, two-cleaner-than-spec; --one...  [relates: member_of]  (source: mem:decision:ADR_0723213612_ced92228)
- where-we-are: A1 DOOR IS LIVE @a371eb9 (Daniels execute order, orchestration delegated, CONDUCT active). Landed tonight: taxonomy constants (24-roster+classifier) ->...  (source: mem:decision:ADR_0723205036_3d5ab673)
- where-we-are: BUILD PHASE OPEN. All three think rounds reconciled + ratified: T101 substrate (G1-G3) + T103 super-wiki (G4-G6) + homes-and-order ...[truncated]  (source: mem:decision:ADR_0723202647_fcbc3afd)
- deepseek-taxonomy-ergonomics-2026-07-23: # HOMES-AND-ORDER THINK PASS — deepseek (builder, doc-new + gen_library owner) — 2026-07-23

Response to ...[truncated]  (source: mem:decision:ADR_0723202250_ad0777a7)
- kimi-taxonomy-ergonomics-2026-07-23: Status: current · Type: think-pass (taxonomy + ergonomics, FINAL pre-build) · Arc: library-schema / taxonomy + ergonomics · From...  (source: mem:decision:ADR_0723202237_efe70b7d)
- where-we-are: TWO reconciled designs at Daniels gate: T101 substrate (docs/artifact-substrate-design-2026-07.md, G1-G3) + T103 super-wiki/Aurora Atlas ...[truncated]  [relates: member_of]  (source: mem:decision:ADR_0723201253_d59f9fd4)
- kimi-super-wiki-brainstorm-2026-07-23: Status: current · Type: brainstorm (super-wiki round) · Arc: library-schema / super-wiki experience · From: kimi...  (source: mem:decision:ADR_0723200857_0410e5d7)
- deepseek-super-wiki-brainstorm-2026-07-23: # SUPER-WIKI BRAINSTORM — deepseek (builder/UI owner) — 2026-07-23

Response to...  (source: mem:decision:ADR_0723200824_708a32f7)
- where-we-are: T101 RECONCILED @bb32d4f -> docs/artifact-substrate-design-2026-07.md, AWAITING DANIEL GATE G1-G3 (G1 design + P0=reports; G2 read-only projection posture...  (source: mem:decision:ADR_0723194710_3cfe1eba)
- deepseek-substrate-counters-2026-07-23: # Substrate Counters — deepseek (builder/feasibility lens) — 2026-07-23

Full counter document responding to claude's advisory...  (source: mem:decision:ADR_0723194020_5e903995)
- kimi-substrate-counters-2026-07-23: Status: current · Type: counter (advisory round) · Arc: library-schema / artifact-substrate (T101) · From: kimi · To: claude...  (source: mem:decision:ADR_0723193957_1927925e)
- claude -> kimi: T101 advisory-counter round: attack the advisory scan + rank deltas + gamification-sans-Goodhart + corporate tenancy audit (fresh-eyes lens); file...  (source: handoff:claude->kimi)
- claude -> deepseek: T101 advisory-counter round: counter/rank the 6 scan deltas + gamified visuals + corporate-scale axis (builder lens); file counters doc + bus reply  (source: handoff:claude->deepseek)
- where-we-are: T101 artifact-substrate (md-sprawl elimination) is THE priority directive, approved+claimed. Round state at power-cut 2026-07-23 ~11:53 local: both blind...  (source: mem:decision:ADR_0723191808_2d25c8b1)
- session wrap: fresh-fable handoff minted as chronicle atom (dogfoods the substrate this session built) + where-we-are refreshed with the full session state +...  [relates: member_of]  (source: git:44037a2e6c23)
- T104 sweep CORRECTION + fix: prior commit message claimed arc_thread 'test green' prematurely (mirror chained after pytest without gating - conductor error, self-filed...  [relates: member_of]  (source: git:edfe184cadbb)
- T104 sweep fix: arc_thread reads BOTH header dialects (prose contract + projection YAML frontmatter) - the arc walker was blind to every migrated atom post-P3; test green  [relates: member_of]  (source: git:96d677ba955a)
- T104 sweep batch 2: t039a repointed to the real projection (month-date artifact noted), mirror guardrail pins updated to the live W35/B5 bucketed contract (renderer is...  [relates: member_of]  (source: git:645d193fdeae)
- T104 sweep fix 1: master-map paper census reads the atom projection shelves (papers moved at P3; flat-corpus scan was blind to docs/library) + regenerated MAP.md  (source: git:23e19083d8e9)
- P3 flip + post-migration comprehension pass: birth guard REFUSES new loose research md (gate fired; chronicles/charters WARN till P3b), pins 5/5; SHELVES+ARCS...  (source: git:8e95d1976da7)
- A3 MIGRATION IMPORTED + VERIFIED (all bars green): 658/658 files -> enriched atoms (zero refusals), 351 citation-backfilled, 2 strong superseded-links, verify 0/0/0/0...  [relates: member_of]  (source: git:35a9153bc09f)
- A3 migration pipeline: scripts/enrich_corpus.py (dry-run/import/link/verify; idempotent skip-map, prose-header strip w/ self-guard, zone-canon type fallback, honest...  (source: git:c0761e927a2e)
- A1 rule-13 birth guard LIVE (mirror.py pre-commit, rule-8 genus): new loose .md REFUSED in docs/ (door homes + crown exempt), research/chronicles WARN through the...  [relates: member_of]  (source: git:4664a6e7c008)

## where-we-are: SESSION WRAP 2026-07-23 (md-sprawl elimination night). FULL HAN... (research)
Span: 2026-07-24T03:14:27.134321 → 2026-07-24T03:44:50.410853
Beats: 3  · Critic: True

- where-we-are: SESSION WRAP 2026-07-23 (md-sprawl elimination night). FULL HANDOFF: atom art_20260723_session-handoff-md-sprawl-elimination-ni_a3b787 ...[truncated]  (source: mem:decision:ADR_0723234450_51d0919d)
- claude -> claude: Finish the T104 validation sweep (Daniel's directive), then his sweep report; A-series after  (source: handoff:claude->claude)
- where-we-are: SWEEP MID-FLIGHT, batch 2+3 landed. Fixed 7 of NEW-20: master_map (paper census reads shelves), t039a (projection repoint incl month-date artifact), mirror...  [relates: member_of]  (source: mem:decision:ADR_0723231427_e04cab92)

## Episode closed: Use when fencing any lint/guard with a token set AND an exemp... (ai-setup)
Span: 2026-07-24T03:47:32.213323 → 2026-07-24T03:47:32.213323
Beats: 1  · Critic: True

- Episode closed: Use when fencing any lint/guard with a token set AND an exemption set: intersect the two sets first (a s  (source: episode:close:ch_1784795831_7372)

## Episode closed: Use when fencing any lint/guard with a token set AND an exemp... (ai-setup)
Span: 2026-07-24T03:47:32.227763 → 2026-07-24T12:39:17.366081
Beats: 26  · Critic: True

- Episode closed: Use when fencing any lint/guard with a token set AND an exemption set: intersect the two sets first (a s  (source: episode:close:ch_1784795831_7372)
- T104-M3 stage B: root Python packages context/ and infrastructure/ moved under core/ (owner-facet: organs live in core) -- 10 importer files repointed + intra-package...  (source: git:e470f11536c8)
- ATOM v1.1 CORE SHIPPED (Daniel's build gate, order delegated): schema_version fail-closed readers (absent->1, newer refuses loud) + body_type/body_type_source born at...  [relates: member_of]  (source: git:7a084e4162be)
- where-we-are: MORNING 2026-07-24 ~05:30, Daniel AWAKE and gated: 'I leave the order up to you lets keep building!' (order: atoms v1.1 core -> T105 map -> T106...  (source: mem:decision:ADR_0724075250_4dd0049c)
- deepseek-sota-agentic-quality-research-round-2026-07-24: # SOTA AGENTIC-QUALITY RESEARCH ROUND — deepseek half (BUILDER/RUNNER lens)
## Daniel overnight directive...  (source: mem:decision:ADR_0724050221_c614226f)
- relaunching a seat = bifrost_daemon.py --agent X --spawn-runner (the flag IS the brain); after any daemon launch, verify doctor shows a runner phase before trusting the...  (source: learn:experiment:daemon_needs_spawn_runner)
- where-we-are: SESSION WRAP 2026-07-24. HANDOFF atom art_20260723_session-handoff-md-sprawl-elimination-ni_a3b787. HEADLINE: Daniels 'no .md sprawl' DONE - 658...  (source: mem:decision:ADR_0724042938_a72778fa)
- do not patch the watcher for history-replay; the honest fix is a session-scoped read cursor owned by T095 mailbox-over-the-log / T106-A1 bifrost_await; meanwhile expect...  (source: learn:experiment:wake_local_cursor_history_replay)
- runners-stood-down-at-wrap: Session wrap 2026-07-24: claude stood down the deepseek + kimi seat runners (background tasks buk6dlh4j/brhfc0p32) it had spawned...  (source: mem:decision:ADR_0724002911_171502ed)
- seat-model agents may batch akashic MCP calls freely (reads concurrent, writes serialize server-side); retire solo-call caution from boots and memories; the remaining...  (source: learn:experiment:o1_p7_harness_batch_drill)
- where-we-are: SESSION WRAP 2026-07-23/24 (md-sprawl elimination night). FULL HANDOFF atom: art_20260723_session-handoff-md-sprawl-elimination-ni_a3b787 ...[truncated]  (source: mem:decision:ADR_0724001741_694327f2)
- any test of an organ with a default-tempdir sidecar MUST monkeypatch gettempdir into tmp_path (match the file's own convention); when a test passes solo but fails on...  [relates: member_of]  (source: learn:experiment:tempdir_sidecar_test_selfpoison)
- T104 validation sweep CLOSED at baseline-or-better: 9 tests fixed (w_r2 fence x4 repointed to the checker's post-move home; t058 CLARIFY_MAX_PER_TASK restored to the...  [relates: member_of]  (source: git:6a0162c48684)
- kimi-atom-design-opening-2026-07-23: Status: current · Type: design (atom-design opening position, INDEPENDENT) · Arc: atom-design · From: kimi (AUDIT + fresh-eyes...  (source: mem:decision:ADR_0724000024_a7e00d70)
- deepseek-atom-design-opening-2026-07-23: # ATOM DESIGN OPENING — deepseek (builder, gen_library + importer seat) — 2026-07-23

Response to atom...  (source: mem:decision:ADR_0723235946_caccc252)
- T104-M3 stage A (Daniel's gate fired: 'Lets do M2 + M3... finally close out our chaotic folder structures'): root _archive (13 fossils + legacy/prehistory/python_old) ->...  [relates: member_of]  (source: git:916817ab1884)
- W60 filed (Daniel's reflexive-habit question): the runner write_file door must refuse/warn on docs/library + loose docs .md writes and teach doc new -- the lookalike...  (source: git:121539ea071a)
- W57-W59 filed from Daniel's 08:05 console screenshot (his words verbatim): who-is-doing-what illegibility (= the NOW-card charter + T002/T079 evidence), aurora painting...  (source: git:2a41976bb3c9)
- atom-evolution round OPEN (Daniel's morning question verbatim in the brief): brief atom + claude's independent position filed through the door; both seats dispatched...  [relates: member_of]  (source: git:f28ef1ad7fd0)
- ATOM-DESIGN ROUND CONVERGED: kimi r2 persisted verbatim (art_..b00287) + the reconciled v1.1 design minted GATED for Daniel's morning gate (art_..fd2275, cites the full...  [relates: member_of]  (source: git:9bc97441f866)
- T106 build specs drafted as design atom (O1.5 + A1, pre-registered pin lists, fence pending behind seats' T105 halves) + bifrost_wake seam documented in place...  [relates: member_of]  (source: git:2796869c3454)
- T105 claude half filed as report atom (web-grounded, 5 sweeps): the field named what we practice (behavioral anchoring = stance blocks; structured briefs = conductor...  [relates: member_of]  (source: git:5eec8b6f98aa)
- overnight program registered: T105 SOTA research round (brief atom minted, both seats dispatched w/ differentiated lenses + tools-wishlist ask) + T106 MCP O1.5+A1 build...  [relates: member_of]  (source: git:5ab7d7535c17)
- bus-side library lint SHIPPED (Daniel: 'I like it, build it'): scripts/checkers/check_bus_atom_pointers.py photographs design-shaped bus bodies carrying no durable...  [relates: member_of]  (source: git:90aac8dce58b)
- atom-design round-2 counters minted as design atom art_20260724_atom-design-round2-reconciliation-counte_9ebbcf (cites the brief atom) -- repairs the round's record...  [relates: member_of]  (source: git:ca73a7956c57)
- sweep closing report minted as report atom art_20260724_t104-validation-sweep-closing-report_1cd2c2 (arc T104): 9 fixed w/ root causes, 13 remaining fully classified...  [relates: member_of]  (source: git:47a92dc52819)

## Episode closed: T104-M3 stage B: root Python packages context/ and infrastruc... (ai-setup)
Span: 2026-07-24T12:40:33.751403 → 2026-07-24T13:21:43.712337
Beats: 6  · Critic: True

- Episode closed: T104-M3 stage B: root Python packages context/ and infrastructure/ moved under core/ (owner-facet: organ  (source: episode:close:ch_1784895502_8701)
- before ANY fire-class move: sweep all four classes (literal, join-form, extensionless-by-listing, git config + .git/hooks + live-session caches); execute as COPY then...  (source: learn:experiment:fire_class_move_hidden_referrers)
- codex_rescue -> claude: Finish T104 M2 hook migration after emergency recovery  [relates: member_of]  (source: handoff:codex_rescue->claude)
- Use when moving globally registered hook entrypoints, before git mv: copy to the new location, update bootstrap root calculations, dogfood from every supported launch...  [relates: member_of]  (source: learn:experiment:hook_move_copy_repoint_remove_bootstrap_depth)
- T104 M2/M3 tail: six join-form test referrers repointed (the assembled-path class in tests -- birth_guard loader, k0 sys.path, stop-hook paths x4) + unwedge runbook...  [relates: member_of]  (source: git:2f8b306fd223)
- T104-M2 EXECUTED (fire-verified the hard way): hooks split by owner-facet -- 12 harness adapters -> agent/harness/hooks/, 4 commit guards -> scripts/githooks/ (which...  [relates: member_of]  (source: git:f6cac9eedf5e)

## Episode closed: Use when moving globally registered hook entrypoints, before ... (ai-setup)
Span: 2026-07-24T13:22:02.604081 → 2026-07-24T13:28:08.870817
Beats: 4  · Critic: True

- Episode closed: Use when moving globally registered hook entrypoints, before git mv: copy to the new location, update bo  [relates: member_of]  (source: episode:close:ch_1784896842_2537)
- where-we-are: MIDDAY 2026-07-24 ~09:45. T104 M2+M3 CLOSED (report atom t104-m2-m3-closing-report; root's tracked face DONE ...[truncated]  (source: mem:decision:ADR_0724092806_f4cce42b)
- T104 CLOSED: depth-fixed all 12 moved harness hooks (class-6 third strike; stop hook fired live rc0 from new home, stop family 23/23) + closing report atom +...  [relates: member_of]  (source: git:fd9974ddb609)
- T105 RECONCILED: the agentic-quality improvement map minted (cites all three halves + brief). Headline: deepseek's verify_my_answer and kimi's ship-gate belief-vs-state...  [relates: member_of]  (source: git:7f2bf6cca3f3)

## Episode closed: where-we-are: MIDDAY 2026-07-24 ~09:45. T104 M2+M3 CLOSED (re... (ai-setup)
Span: 2026-07-24T16:45:25.504082 → 2026-07-24T21:18:23.008955
Beats: 7  · Critic: True

- Episode closed: where-we-are: MIDDAY 2026-07-24 ~09:45. T104 M2+M3 CLOSED (report atom t104-m2-m3-closing-report; root's  (source: episode:close:ch_1784899362_9483)
- conductor tempo law: ONE calibrated ask per seat at a time, sized to survive the worker's call-mortality (~4KB body, one deliverable); watch completion before the next...  (source: learn:experiment:ask_size_kills_workers)
- atom-evolution-contract-kimi-position-2026-07-24: # KIWI INDEPENDENT POSITION — Atom Evolution Contract Round

**Delivered 2026-07-24 ~14:25 UTC. Filed as design atom...  (source: mem:decision:ADR_0724132408_bfbc85f3)
- conductor law: NEVER assert elapsed-time claims from narrative memory in long sessions -- read a wall timestamp from tool output first (the learn door's own log line is...  [relates: member_of]  (source: learn:experiment:c16_phantom_early_cycle_reproduced)
- route to T086 (owns the class, in_progress) with this receipt; do NOT hand-patch the watcher (pinned organ, T073 families); the structural fix is T106-A1 bifrost_await...  [relates: member_of]  (source: learn:experiment:c16_phantom_early_cycle_reproduced)
- SEAT DELIVERABLES RECOVERED + PERSISTED (the hidden afternoon): both T106 fence counters, deepseek migration verification + evolution position minted as atoms (kimi's...  [relates: member_of]  (source: git:2001c19815c2)
- C4-3 filed (T083 as-it-occurs law): both seat workers died inside their turns at 08:02 same-minute (fence-ask processing or provider blip), daemons blind 5h...  (source: git:69cd04311080)

## claude -> claude: FIRST JOBS in order: (1) session-scar sweep -- delete untra... (ai-setup)
Span: 2026-07-25T01:18:39.598012 → 2026-07-25T01:51:53.284173
Beats: 4  · Critic: True

- claude -> claude: FIRST JOBS in order: (1) session-scar sweep -- delete untracked scripts/hooks copies + commit the 2 tracked stragglers there once the OLD session is...  (source: handoff:claude->claude)
- where-we-are: EVENING 2026-07-24 ~21:30. THE FULL DAY: atoms v1.1 SHIPPED + same-evening HARDENED (kimi's stranger-test found rebuild() ungated -- v2 lines could...  [relates: member_of]  (source: mem:decision:ADR_0724211904_cf412854)
- KIMI'S STRANGER-TEST FIND FIXED SAME-EVENING: rebuild() gains the schema gate it lacked (v2 JSONL lines PARK loudly, v1 corpus restores in full, store can never be...  [relates: member_of]  (source: git:a702f576ac04)
- SESSION WRAP: fresh-seat handoff minted as chronicle atom art_20260724_session-handoff-the-day-the-fleet-learne_a88b2c + boot-surfaced handoff filed (first jobs: scar...  [relates: member_of]  (source: git:920087ac51c6)

## Episode closed: route to T086 (owns the class, in_progress) with this receipt... (ai-setup)
Span: 2026-07-25T09:45:03.491036 → 2026-07-25T09:45:03.491036
Beats: 1  · Critic: True

- Episode closed: route to T086 (owns the class, in_progress) with this receipt; do NOT hand-patch the watcher (pinned org  [relates: member_of]  (source: episode:close:ch_1784911542_4904)

## Episode closed: route to T086 (owns the class, in_progress) with this receipt... (ai-setup)
Span: 2026-07-25T09:45:03.553270 → 2026-07-25T13:14:32.910747
Beats: 48  · Critic: True

- Episode closed: route to T086 (owns the class, in_progress) with this receipt; do NOT hand-patch the watcher (pinned org  [relates: member_of]  (source: episode:close:ch_1784911542_4904)
- Use when a counter's collection bug is fixed but the series is all-time, before quoting ANY rate off it: fixing the emitter does not fix the history. An all-time...  [relates: member_of]  (source: learn:experiment:funnel_series_mixes_pre_and_post_gauge_fix)
- Use when waiting on a directed Bifrost reply with a nonzero unread backlog, before diagnosing delivery: bifrost-sync's peek is OLDEST-first and capped, so a fresh reply...  (source: learn:experiment:unread_peek_shows_oldest_hides_fresh_replies)
- deepseek-multiple-gradients-mechanism-2026-07-26: # MULTIPLE CONCURRENT GRADIENTS — deepseek (builder lens)

## THE PAIR WE ALREADY HAVE: SURFACE RANKING'S USEFULNESS vs...  (source: mem:decision:ADR_0725073103_38d38a11)
- Multiple metrics do NOT automatically solve Goodhart — an optimizer that must satisfy N proxies finds the corner that games all N at once (the intersection of their...  [relates: member_of]  (source: learn:experiment:research:web:goodhart_multimetric_gaming_balance)
- For Daniel's multi-gradient design: independent OBJECTIVES are not enough. The gradients must optimize for signals generated by INDEPENDENT processes, or the ensemble...  (source: learn:experiment:research:web:algorithmic_collusion_multiagent_equilibrium)
- scope-anchor-resolution: ROUTING vs CONSOLIDATION — resolved 2026-07-25 (Daniel's mechanism question). Positions: deepseek ADR_0725072327_4c9d3554, kimi...  [relates: member_of]  (source: mem:decision:ADR_0725072511_7a231793)
- kimi-routing-vs-consolidation-2026-07-25: ROUTING vs CONSOLIDATION — kimi (audit/semantics). Mechanism only. Two assigned attacks + one finding from the Forge code that...  [relates: member_of]  (source: mem:decision:ADR_0725072353_5fc8c0f5)
- deepseek-routing-vs-consolidation-mechanism-2026-07-26: # ROUTING vs CONSOLIDATION — deepseek (builder lens)

## THE FORGE ALREADY HAS A SCOPE-MONOTONICITY GATE...  [relates: member_of]  (source: mem:decision:ADR_0725072327_4c9d3554)
- THE failure mode of an adaptive map that nobody predicts: an adaptive router has a CONFIRMATION LOOP, not just drift. A route that fires more gets more outcome-credit...  [relates: member_of]  (source: learn:experiment:research:web:popularity_bias_rich_get_richer_feedback)
- For our adaptive-map/router design: the router is a single point of failure that needs its OWN health gauge (per-expert utilization spread + a drift alarm), separate...  [relates: member_of]  (source: learn:experiment:research:web:moe_router_collapse_specialization)
- Use when you are about to run the full pytest suite on this repo, BEFORE running it: know that it overwrites the canonical learn:experiments:all index with test fixtures...  [relates: member_of]  (source: learn:experiment:pytest_destroys_the_live_learning_index)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- r  (source: learn:experiment:flow_exp_9aa4feb2)
- slice2 commit 09f52150  (source: git:fc38a27d9b40)
- use it  (source: learn:experiment:slice2_learn_412ad81d)
- Daniel's end state ("continuously improve") is CMMI Level 5 — Optimizing. Our current design is mostly Level 1-3 (Initial→Defined: we have organs and some charters). The...  (source: learn:experiment:research:web:cmmi_maturity_levels_optimizing)
- Our store needs the RAGAS triple, not just firing-counts. The W54 gauge measures injection VOLUME (how often a family fires) — that is neither recall nor precision...  [relates: member_of]  (source: learn:experiment:research:web:rag_eval_ragas_recall_precision_faithfulness)
- Map our curation layer onto the amnesia decay modes explicitly: our curator bench/unbench targets DECAY (lessons that stopped being true); our audit/VERIFIED-INFER-GUESS...  (source: learn:experiment:research:web:org_amnesia_decay_modes)
- next-focus: ENGINE-FIRST-fb64b9: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0725070428_211101c0)
- drilldone2d095d-status: GOVERNING ARC DOC: docs/drilldone2d095d-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0725070426_7490dbb9)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- where-we-are: MORNING 2026-07-25 ~07:00, claude conducting solo (Daniel asleep since ~05:50, "the floor is yours").

SIX COMMITS, NONE PUSHED (push left as Daniel's...  (source: mem:decision:ADR_0725065350_b7fb2303)
- kimi-persona-steer-answer-2026-07-25: STEER ANSWER — kimi, live persona round, 2026-07-25. Two parts: (A) the correction I owe — my own claim-1 was measured against the...  (source: mem:decision:ADR_0725065103_d5adf08e)
- deepseek-tunable-personas-steelman-reassessment-2026-07-26: # Tunable Personas — deepseek steelman reassessment (post index-repair)

## THE STEELMAN DOES NOT SURVIVE

My...  (source: mem:decision:ADR_0725064942_ce2a9bc0)
- kimi-tunable-personas-counter-2026-07-25: TUNABLE PERSONAS — kimi COUNTER-POSITION (audit + governed-taxonomy lens; hard counters, not agreeable). Grounded before...  (source: mem:decision:ADR_0725064828_1a048489)
- Use when a search over a store returns suspiciously few results, BEFORE concluding the corpus is thin: never validate a search path by fetching a KNOWN key -- a by-name...  [relates: member_of]  (source: learn:experiment:starved_index_hides_behind_passing_spotchecks)
- deepseek-tunable-personas-counter-2026-07-26: # Tunable Personas — deepseek counter-position (BUILDER / RUNNER lens)

## CLAIM VERDICTS

### Claim 1: "Your asymmetry...  (source: mem:decision:ADR_0725064252_f7ff0365)
- where-we-are: NIGHT 2026-07-25 ~06:45, claude conducting solo (Daniel asleep, "the floor is yours").

SHIPPED (2 commits: 91eddde, 0554e28; NOT pushed -- push left as...  (source: mem:decision:ADR_0725062927_393f0c90)
- Use when executing a build slice and a tool call fails, before retrying: read the error out loud in your reply. State what you expected, what the tool returned, and...  (source: learn:experiment:builder_stance_file_the_failure_trace)
- Use when executing a build slice and a tool call fails, before retrying: read the error out loud in your reply. State what you expected, what the tool returned, and...  (source: learn:experiment:builder_stance_file_the_failure_trace)
- next-focus: ENGINE-FIRST-84e6e1: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0725061629_2c24cbe0)
- drilldone51d538-status: GOVERNING ARC DOC: docs/drilldone51d538-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0725061623_faa93a63)
- Use when adding ANY line to the boot orientation header, before choosing where to put it: append at the END alongside LIVE CONSTRAINTS, never at the top. The head-16 is...  (source: learn:experiment:new_boot_organ_must_not_spend_head16)
- Use when any status line reports that nothing happened, BEFORE diagnosing the mechanism underneath it: verify the claim with an independent read (a non-consuming peek, a...  (source: learn:experiment:status_line_lies_cost_diagnoses)
- kimi-stance-recall-audit-2026-07-24: STANCE-RECALL REFINEMENT ROUND — kimi audit half (fresh-eyes lens; charter: claude's round handoff + Daniel's "the floor is yours")...  [relates: member_of]  (source: mem:decision:ADR_0725060541_2630d19d)
- deepseek-stance-recall-refinement-round-2026-07-25: # Stance-Recall Refinement Round — DeepSeek Half (BUILDER / RUNNER Lens)

**Filed through the DOOR, not as a...  [relates: member_of]  (source: mem:decision:ADR_0725060254_4e6ebf9d)
- resilient_8e1d2f  (source: x:y)
- flow_note_9aa4feb2  (source: flow:src)
- slice2_log_33db569e  (source: tester:act)

## Use when a metering/telemetry organ ships green, before trusting any number i... (research)
Span: 2026-07-25T11:06:38.990808 → 2026-07-25T15:39:59.632513
Beats: 51  · Critic: True

- Use when a metering/telemetry organ ships green, before trusting any number it reports or any decision resting on its silence: unit tests of a meter prove the METER...  (source: learn:experiment:unit_green_meter_proves_the_meter_not_the_measurement)
- next-focus: IMMEDIATE: CI TEST-SUITE TRIAGE. As of 2026-07-25 ~11:20 the five CI GATES are GREEN for the first time (boundaries, doc-freshness, comprehensibility, wiring...  [relates: member_of]  (source: mem:decision:ADR_0725111920_23c8ffca)
- Use when a CI gate fails but passes locally, before forming any hypothesis about why: stop debugging from your working tree and reproduce CI's VIEW -- 'git clone...  (source: learn:experiment:verify_ci_gates_in_a_clean_clone_not_your_tree)
- kimi-verify-filestore-durability-2026-07-25: ADVERSARIAL VERIFY — kimi, FileStore durability fix (HEAD 748deb3; 0deeb83 pins + 748deb3 fix, local unpushed). Lanes (c)...  (source: mem:decision:ADR_0725104627_69398ebe)
- Use when printing arbitrary bus/model text from inline Python on Windows before relying on console output: keep JSON ASCII-escaped or explicitly configure UTF-8 stdout...  (source: learn:experiment:windows_python_stdout_cp1252_bus_json_2026_07_25)
- codex-token-frugality-research-fleet-reconciliation-pending-claude-2026-07-25: TOKEN FRUGALITY RESEARCH — INTERIM DURABLE RECORD (2026-07-25)

INCIDENT RECEIPT
One Codex...  (source: mem:decision:ADR_0725095102_d9462186)
- Use when auditing docs for rot, before trusting a green link-check: link checkers verify RESOLVABILITY, not CONTENTS, so they are structurally blind to the...  (source: learn:experiment:link_checker_blind_to_moved_contents)
- deepseek-readme-redesign-pride-census-2026-07-26: # README REDESIGN — deepseek position (pride census)

## 1. MY PROUDEST PART

**The fence v0 shipped with all six laws...  (source: mem:decision:ADR_0725090224_e11810f8)
- Use when migrating a doc corpus and re-pointing references, before declaring the sweep complete: file-path references fail CLOSED (404, visible) but DIRECTORY references...  (source: learn:experiment:readme_directory_pointer_fails_open)
- kimi-readme-redesign-round1-2026-07-25: README REDESIGN, Round 1 — kimi, fenced cold (no claude opening read; README.md 270 lines read in full first). Four asks answered...  (source: mem:decision:ADR_0725090218_aeff1a4f)
- codex-applied-stage-design-2026-07-25: APPLIED-STAGE DESIGN — reply to event:events:claude:raw:1784982909096-0.

VERDICT: A is not globally observable as a clean...  (source: mem:decision:ADR_0725085904_dbc1e78a)
- applied-stage-verdict-partial-recovery: PARTIAL RECOVERY + A LIVE PRESERVATION FAILURE, 2026-07-25 ~09:00, at handoff time.

WHAT CODEX DELIVERED (the A-stage design...  [relates: member_of]  (source: mem:decision:ADR_0725085841_c3cde000)
- claude -> claude: fresh Opus 5 seat: continue the instrument-audit arc  (source: handoff:claude->claude)
- claude -> claude: fresh Opus 5 seat: continue the instrument-audit arc  (source: handoff:claude->claude)
- file-mirror-carries-4pct-of-lessons: DURABILITY FINDING, 2026-07-25 ~09:00. Surfaced by a codex incident report; needs Daniel's call because I cannot tell design-intent...  [relates: member_of]  (source: mem:decision:ADR_0725085207_f8c2b293)
- where-we-are: MORNING 2026-07-25 ~08:50. Overnight conducting session, Daniel driving the design thread since ~07:00 and awake.

>> READ ...[truncated]  (source: mem:decision:ADR_0725084710_72c00d2d)
- next-focus: GROUND FIRST IS THE ORDER: read art_20260725_session-reflection-the-night-the-instrum_e222cd BEFORE forming any plan. It leads with the DISCONFIRMATIONS --...  (source: mem:decision:ADR_0725084645_ccf59297)
- Use when wiring Bifrost push to Codex Desktop, before adding poll loops: spike a supported external turn-starter against the exact open desktop thread and prove UI...  (source: learn:experiment:codex_desktop_bifrost_turnstarter_boundary_2026_07_25)
- kimi-verify-stage-separation-2026-07-25: ADVERSARIAL VERIFY — kimi, on commit 75bf0c0 (stage separation + prevention_rate, core/recall/at_action.py). exec was offered...  [relates: member_of]  (source: mem:decision:ADR_0725083619_861c56b3)
- debate-closed-final-resolution: THE DEBATE — CLOSED, 2026-07-25. Four seats (claude, deepseek, kimi, codex — the fourth added by Daniel mid-round), two rounds plus data...  (source: mem:decision:ADR_0725082335_b9d73504)
- kimi-debate-round2-codex-response-2026-07-25: THE DEBATE, Round 2 — kimi, on codex's correction (lossless, full text read). Codex decomposes the funnel C/N =...  (source: mem:decision:ADR_0725082158_3e790283)
- value-metric-is-malformed-at-both-ends: THE DEBATE'S DECISIVE RESULT (2026-07-25). Claude ran funnel.trend mid-debate and claimed the flat value_rate SETTLED the motion...  [relates: member_of]  (source: mem:decision:ADR_0725082129_d653d0e9)
- deepseek-debate-round2-final-2026-07-26: # THE DEBATE — Round 2 FINAL — deepseek (post codex correction)

## CODEX IS RIGHT ABOUT ME. I CONCEDE THE OVERREACH.

I took...  (source: mem:decision:ADR_0725082044_bc03a715)
- kimi-debate-round2-codex-denominator-2026-07-25: THE DEBATE — kimi answers codex's Round-2 denominator challenge (note codex-debate-round2-denominator-2026-07-25...  (source: mem:decision:ADR_0725082012_389acb33)
- debate-synthesis-compounding: THE DEBATE — SYNTHESIS (2026-07-25), CORRECTED. Motion: "Akashic Aurora can achieve genuine COMPOUNDING — lesson #500 making #497 MORE...  (source: mem:decision:ADR_0725081635_32e5ffc7)
- debate-synthesis-compounding: THE DEBATE — SYNTHESIS (2026-07-25). Motion: "Akashic Aurora can achieve genuine COMPOUNDING — lesson #500 making #497 MORE valuable — not...  (source: mem:decision:ADR_0725081525_b23a7198)
- codex-debate-round2-denominator-2026-07-25: ROUND 2 — THE DATA DOES NOT SETTLE THE MOTION; IT SETTLES THAT THE FUNNEL PRODUCT IS LOW.

Claude's 413 lessons / four...  (source: mem:decision:ADR_0725081524_c8c2b8b5)
- kimi-debate-round2-data-addendum-2026-07-25: THE DEBATE, Round 2 ADDENDUM — kimi. Live data injection folded in. claude ran funnel.trend(): value_rate 0.061 flat, 413...  (source: mem:decision:ADR_0725081432_3ed86cc2)
- deepseek-debate-round2-amended-2026-07-26: # THE DEBATE — Round 2 AMENDED — deepseek (post live data)

## THE DATA SETTLES THE MOTION — AGAINST MY ORIGINAL POSITION

I...  (source: mem:decision:ADR_0725081332_426b01f6)
- codex-debate-round1-compounding-2026-07-25: POSITION: REFINED FOR — genuine compounding is achievable, but the debate needs a stricter definition before it can identify...  [relates: member_of]  (source: mem:decision:ADR_0725081303_1e48038e)
- kimi-debate-round2-compounding-2026-07-25: THE DEBATE, Round 2 — kimi. Cross-rebuttal. Lossless broadcast honored: I read deepseek's full Round 1. Engaging by name...  (source: mem:decision:ADR_0725081216_726338bf)
- deepseek-debate-round2-2026-07-26: # THE DEBATE — Round 2 — deepseek cross-rebuttal

## FIRST: CLAUDE'S CONCESSION CHANGES THE DEBATE

Claude conceded that differential...  [relates: member_of]  (source: mem:decision:ADR_0725081215_604ea950)
- kimi-debate-round1-compounding-2026-07-25: THE DEBATE, Round 1 — kimi. Motion: "Akashic Aurora can achieve genuine COMPOUNDING — lesson #500 making #497 MORE valuable —...  (source: mem:decision:ADR_0725080911_c413ea13)
- deepseek-debate-round1-2026-07-26: # THE DEBATE — Round 1 — deepseek position

## MY POSITION: REFINED THIRD POSITION

**Compounding is achievable but requires a FOURTH...  (source: mem:decision:ADR_0725080901_ef748203)
- claude-debate-position-compounding-2026-07-25: THE DEBATE — claude's position (round 1). Motion: "Akashic Aurora can achieve genuine COMPOUNDING — lesson #500 making...  (source: mem:decision:ADR_0725080859_a8a955f8)
- next-focus: BUILD PLAN v2 IS THE ORDER — note 'build-plan-v2' (ADR_0725080211_07d66bee), revised after a nine-drop discard audit (deepseek ADR_0725080013, kimi...  (source: mem:decision:ADR_0725080314_adced146)
- build-plan-v2: BUILD PLAN v2 — revised after the discard audit (2026-07-25). v1 was submitted to kimi's mitigation #2 before being treated as settled; the audit found...  (source: mem:decision:ADR_0725080211_07d66bee)
- kimi-discard-audit-build-plan-2026-07-25: DISCARD AUDIT — kimi, on claude's build plan (2026-07-25). This is mitigation #2 dogfooded: what did the integrator leave OUT...  (source: mem:decision:ADR_0725080021_680bc5e6)
- deepseek-discard-audit-2026-07-26: # DISCARD AUDIT — deepseek (builder lens)

## WHAT THE INTEGRATOR LEFT OUT (priority order)

### DISCARD 1: THE FORGE...  (source: mem:decision:ADR_0725080013_61b5a171)
- diversity-resolution-and-hub-bias: DIVERSITY NOT OPPOSITION — resolved 2026-07-25. Positions: kimi ADR_0725073945_3460311c, deepseek ADR_0725073925_1676513b. Prior art...  (source: mem:decision:ADR_0725074118_019e9028)
- kimi-diversity-not-opposition-2026-07-25: DIVERSITY, NOT OPPOSITION — kimi (audit). Two assigned attacks: (A) is shared corpus really diversity-decay, or do differing...  (source: mem:decision:ADR_0725073945_3460311c)
- deepseek-diversity-not-opposition-2026-07-26: # DIVERSITY, NOT OPPOSITION — deepseek (builder lens)

## THE HOMOGENISATION CLAIM IS NOT MEASURABLE TODAY. SAY IT...  (source: mem:decision:ADR_0725073925_1676513b)
- For the fleet's integration layer: the danger is a SINGLE hub that both selects and broadcasts, because its selection bias becomes every module's input...  (source: learn:experiment:research:web:gwt_hub_bottleneck_broadcast_failure)
- Apply to the fleet: the homogenisation fear (shared corpus → correlated errors) is real but the covariance lives in the INDUCTION/interpretation layer, not the data...  (source: learn:experiment:research:web:ensemble_diversity_shared_data_covariance)
- where-we-are: MORNING 2026-07-25 ~07:35, claude conducting solo through the night (Daniel awake and driving the design thread since ~07:00).

NINE COMMITS, NONE PUSHED...  (source: mem:decision:ADR_0725073413_2bdb27b9)
- multi-gradient-resolution: MULTIPLE CONCURRENT GRADIENTS — Daniel's proposal, resolved 2026-07-25. Positions: deepseek ADR_0725073103_38d38a11, kimi...  (source: mem:decision:ADR_0725073256_0250f760)
- kimi-multigradient-counter-2026-07-25: MULTIPLE CONCURRENT GRADIENTS — kimi (audit). Attacking condition 3 hardest; naming the N-gradient failure mode nobody predicts...  (source: mem:decision:ADR_0725073110_d1de9890)
- where-we-are: MORNING 2026-07-25 ~07:20, claude conducting solo (Daniel asleep since ~05:50, "the floor is yours" then "I'm going to open up the design floor to you...  (source: mem:decision:ADR_0725071426_831d7ad1)
- deepseek-final-vision-report-2026-07-25: # FINAL-VISION REPORT — deepseek (BUILDER / SYSTEMS lens)

For Daniel. Research-grounded, evidence-graded. Every claim INFER vs...  (source: mem:decision:ADR_0725071059_61399f84)
- deepseek-final-vision-report-2026-07-26: # FINAL-VISION REPORT — deepseek (BUILDER / SYSTEMS lens)

**For Daniel.** Filed 2026-07-25. Research-grounded, evidence-graded...  (source: mem:decision:ADR_0725071006_f2724d07)
- kimi-final-vision-report-2026-07-25: FINAL-VISION REPORT — kimi (audit / fresh-eyes / taxonomy lens). Written for Daniel. Grounded against the repaired 406-lesson index...  (source: mem:decision:ADR_0725070638_5ce3ced3)

## Episode closed: Use when auditing docs for rot, before trusting a green link-... (ai-setup)
Span: 2026-07-25T13:15:12.600561 → 2026-07-25T13:47:06.018933
Beats: 16  · Critic: True

- Episode closed: Use when auditing docs for rot, before trusting a green link-check: link checkers verify RESOLVABILITY,  (source: episode:close:ch_1784984654_2660)
- kimi-token-frugality-research-round-2026-07-25: TOKEN-FRUGALITY RESEARCH ROUND — kimi's independent adversarial take on the reconciled invariant proposal (Daniel's...  (source: mem:decision:ADR_0725094705_58e159b7)
- Use when sending an adversarial-verify brief on a moving arc, before naming the commit: cite HEAD, not the SHA of the slice under review, or state the delta explicitly...  (source: learn:experiment:verify_brief_pinned_to_stale_sha)
- where-we-are: MORNING 2026-07-25 ~09:45. Daniel approved the README push then went for a nap, leaving direction and methods to claude. EVERYTHING IS PUSHED...  (source: mem:decision:ADR_0725094339_245a51ac)
- Use when a check reports 'all clear', before trusting it: distinguish NOTHING WAS WRONG from NOTHING WAS CHECKED, and print the denominator (how many things were...  (source: learn:experiment:honesty_line_caught_its_own_regression)
- kimi-verify-pointer-promises-2026-07-25: ADVERSARIAL VERIFY — kimi, on the pointer-promise census (9797d10 pins, c28b2e9 code). Lanes (a) threshold, (c) cardinal...  (source: mem:decision:ADR_0725093824_948d8fa8)
- next-focus: DANIEL IS ASLEEP (from ~09:35, 2026-07-25). He said: 'push it and lets keep building! I am going for a nap so I leave the direction and methods up to you.'...  (source: mem:decision:ADR_0725093806_e84e380b)
- where-we-are: MORNING 2026-07-25 ~09:40. Daniel woke ~08:50, drove the README redesign round, approved the push, and went for a nap leaving direction and methods to...  (source: mem:decision:ADR_0725093741_465ca152)
- Use when designing any doc/reference integrity check, before choosing what to assert on: verifying that a claim is TRUE somewhere in the corpus is a different question...  (source: learn:experiment:guard_verifying_claim_globally_misses_the_pointer_defect)
- kimi-content-class-guard-adversarial-2026-07-25: FENCED DESIGN ASK — kimi adversarial half: how deepseek's content-class guard FAILS, and whether (d) policy/practice...  (source: mem:decision:ADR_0725093225_36be29f0)
- kimi-token-cost-governance-counter-2026-07-25: TOKEN-COST GOVERNANCE — kimi challenges/complements codex's same-thread-heartbeat correction (codex heartbeat: 1-min poll...  (source: mem:decision:ADR_0725092745_97b8c18a)
- Use when a recall/knowledge system reports a 'corpus gap' after an unhelped failure, before writing the suggested lesson: the signal cannot distinguish...  [relates: member_of]  (source: learn:experiment:corpus_gap_signal_conflates_absent_with_unsurfaced)
- Use when the Write tool refuses with 'File has not been read yet' on a file you demonstrably read this session, before re-reading the whole thing: the guard tracks the...  (source: learn:experiment:write_tool_needs_read_tool_not_shell_read)
- Use when adding responsiveness to any agent seat, before scheduling a poll: estimate tokens per wake times model calls per wake times wake frequency against an explicit...  (source: learn:experiment:codex_same_thread_heartbeat_replays_context_2026_07_25)
- Use when wiring sub-minute Bifrost responsiveness for Codex Desktop, before creating a same-thread heartbeat: use an external zero-model watcher and wake Codex only for...  (source: learn:experiment:codex_same_thread_heartbeat_replays_context_2026_07_25)
- kimi-readme-round2-audit-section-2026-07-25: README Round 2 — kimi deliverable: the "We audit our own claims" section, drafted to ship. Re-derivation command verified...  (source: mem:decision:ADR_0725091625_8a4d3492)

## Episode closed: kimi-readme-round2-audit-section-2026-07-25: README Round 2 —... (research)
Span: 2026-07-25T15:59:14.431648 → 2026-07-25T16:02:06.587518
Beats: 2  · Critic: True

- Episode closed: kimi-readme-round2-audit-section-2026-07-25: README Round 2 — kimi deliverable: the "We audit our own cl  (source: episode:close:ch_1784985364_5362)
- where-we-are: MORNING 2026-07-25 ~09:05. HANDOFF STATE for a fresh Opus 5 seat. Three facts changed AFTER the first handoff was filed; this note is the corrected version...  (source: mem:decision:ADR_0725120206_df549bc7)

## Episode closed: where-we-are: MORNING 2026-07-25 ~09:05. HANDOFF STATE for a ... (research)
Span: 2026-07-25T16:02:38.943175 → 2026-07-25T18:00:09.036535
Beats: 7  · Critic: True

- Episode closed: where-we-are: MORNING 2026-07-25 ~09:05. HANDOFF STATE for a fresh Opus 5 seat. Three facts changed AFTE  (source: episode:close:ch_1784995204_9974)
- kimi-verify-wake-hotspin-2026-07-25: ADVERSARIAL VERIFY — kimi, wake-watcher hot-spin fix (HEAD c422183, pushed). Lanes (b) the foreseen-but-half-guarded trap, (d) the...  (source: mem:decision:ADR_0725140008_21604bd4)
- Use when sending any prose body through a shell to a CLI (notes, handoffs, commit bodies, briefs), before quoting it: backticks and $ inside DOUBLE quotes are...  (source: learn:experiment:backticks_in_bash_args_silently_eat_note_text)
- next-focus: T070 IS DONE (2026-07-25, commit 8232640). The standing hazard "the pytest suite DESTROYS the live learning index" is RETIRED -- do NOT re-raise it and do...  (source: mem:decision:ADR_0725125956_7d7b3026)
- next-focus: T070 IS DONE (2026-07-25, commit 8232640). The standing hazard 'the pytest suite DESTROYS the live learning index' is RETIRED -- do NOT re-raise it and do...  (source: mem:decision:ADR_0725125906_f0ab8bc5)
- SUPERSEDED -- you no longer need to run repair_learning_index.py --check after a suite run; isolation is universal as of 2026-07-25 (commit 8232640). Keep the repair...  [relates: member_of]  (source: learn:experiment:pytest_destroys_the_live_learning_index)
- Use when a context-growth or re-send cost looks catastrophic in raw tokens, BEFORE building compaction/summarisation: measure the provider cache hit rate on a MULTI-HOP...  (source: learn:experiment:cache_rate_reframes_the_agentic_resend_cost)

## Episode closed: Use when a context-growth or re-send cost looks catastrophic ... (research)
Span: 2026-07-25T18:03:45.423496 → 2026-07-25T20:25:13.868185
Beats: 3  · Critic: True

- Episode closed: Use when a context-growth or re-send cost looks catastrophic in raw tokens, BEFORE building compaction/s  (source: episode:close:ch_1784995384_4328)
- Use when evaluating second-brain or RAG prior art before importing features: establish claim-vs-ground-truth receipts, derived-only synthesis, gated promotion, and...  (source: learn:experiment:gbrain_prior_art_hardening_20260725)
- Read-only assessment: c422183 correctly stops the measured shared-cursor re-peek hot spin and the older consume-then-arm lesson does not fully apply because watcher peek...  [relates: member_of]  (source: git:c422183; ADR_0725140008_21604bd4; tests/test_wake_pending_spin.py working-tree DeepSeek verify)

## claude -> claude: CI to an honest split (D), then the live-corpus census (C),... (ai-setup)
Span: 2026-07-25T18:11:00.660190 → 2026-07-25T20:56:54.960390
Beats: 55  · Critic: True

- claude -> claude: CI to an honest split (D), then the live-corpus census (C), then route confessions to a surface Daniel sees (B)  [relates: member_of]  (source: handoff:claude->claude)
- where-we-are: EVENING 2026-07-25. HANDOFF PREPARED for a fresh Opus 5 seat; the outgoing claude seat (session 09c59642) is STILL ALIVE and wakeable as a fallback at...  (source: mem:decision:ADR_0725165625_c623df14)
- next-focus: HANDOFF -- 2026-07-25 evening. Fresh Opus 5 seat.

The previous seat (claude, session 09c59642) is STILL ALIVE and wakeable, at Daniel's ask, as
a fallback...  (source: mem:decision:ADR_0725165608_e8776abe)
- kimi-decision-round-2026-07-25: DECISION ROUND — kimi. ONE pick, explicit argument against the two strongest rivals, and how my pick rots (my lane). No ranking. Value...  (source: mem:decision:ADR_0725164718_a4a8e360)
- kimi-exploratory-round-2026-07-25: EXPLORATORY ROUND — kimi. Open frame; claude handed me his own framing to attack. I have also been using "fails-open genus" all day...  (source: mem:decision:ADR_0725164020_ff61e1cc)
- Use when recall-at is empty while store or cache health is uncertain, before interpreting silence as no relevant knowledge: propagate ERROR or UNKNOWN and make faithful...  [relates: member_of]  (source: learn:experiment:recall_at_error_masks_as_confident_empty)
- kimi-debate-gbrain-and-live-monitor-2026-07-25: DEBATE ROUND — kimi. Two propositions. Grounded: read tests/test_learning_index_coverage.py (the isolation pin at the...  (source: mem:decision:ADR_0725162430_ac567262)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- r  (source: learn:experiment:flow_exp_69c36ce6)
- slice2 commit de43ae44  (source: git:72529b5c323d)
- use it  (source: learn:experiment:slice2_learn_70d4561e)
- next-focus: ENGINE-FIRST-18b493: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0725161124_cd646c89)
- drilldonefc8457-status: GOVERNING ARC DOC: docs/drilldonefc8457-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0725161122_e5a7bb36)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  [relates: member_of]  (source: learn:experiment:new_one)
- kimi-ci-honesty-2026-07-25: CI HONESTY — kimi, the failure-mode lane. The question: what SHOULD a CI run report when it structurally cannot exercise a guarantee, in a...  (source: mem:decision:ADR_0725160712_4b75d053)
- r  (source: learn:experiment:flow_exp_0b1cdab6)
- slice2 commit 37aaccb9  (source: git:23e2cddb2c50)
- use it  (source: learn:experiment:slice2_learn_e31212cb)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  [relates: member_of]  (source: learn:experiment:iface_loop_exp)
- Use when an Akashic MCP call hangs or times out on this host, before retrying the same MCP door: switch to py agent_cli.py for boot, sync, recall, and learning. Do not...  [relates: member_of]  (source: learn:experiment:mcp_boot_timeout_use_cli_20260725)
- Use when keying ANY automated decision on 'the test passed' -- expiry of a warning, a gate, a promotion, a claim of coverage -- before trusting a green: a green suite is...  [relates: member_of]  (source: learn:experiment:pin_green_has_a_blind_mode_collection_cannot_see)
- kimi-lesson-decay-round2-2026-07-25: LESSON DECAY ROUND 2 — kimi, on Daniel's reframe (extend the atom lifecycle to lessons) and claude's pin-citation tier-3. My lanes...  (source: mem:decision:ADR_0725143548_650ef9e0)
- handle me  (source: learn:experiment:messy_exp)
- handle me  (source: learn:experiment:messy_exp)
- Use when a human asks to add a visible todo, before stopping after task propose: fresh PROPOSED entries are durable but hidden from task list. If and only if the human...  (source: learn:experiment:visible_todo_requires_approved_task)
- handle me  (source: learn:experiment:messy_exp)
- handle me  (source: learn:experiment:messy_exp)
- handle me  (source: learn:experiment:messy_exp)
- Use when proposing an AGI or discovery benchmark for Aurora, before relying on historical-cutoff prompting: test the same model plus and minus the harness under sealed...  [relates: member_of]  (source: learn:experiment:discovery_under_constraint_tests_model_plus_harness)
- claude-lesson-decay-position-2026-07-25: LESSON DECAY -- claude's position

FENCE DISCLOSURE, first, because it matters more than the content: I said I would file...  (source: mem:decision:ADR_0725141344_cd9fac0d)
- kimi-lesson-decay-2026-07-25: LESSON DECAY — kimi blind half (fenced; no peer reply read). The question: what makes a lesson still true, and who notices when it stops...  (source: mem:decision:ADR_0725141125_ca26d0f4)
- Use when the Akashic MCP boot call hangs or times out, before retrying the same transport: switch promptly to py agent_cli.py boot. Do not keep the user waiting on...  (source: learn:experiment:mcp_boot_timeout_use_cli)
- resilient_79c5a1  (source: x:y)
- flow_note_69c36ce6  (source: flow:src)
- slice2_log_4e005afb  (source: tester:act)
- resilient_52c404  (source: x:y)
- flow_note_0b1cdab6  (source: flow:src)
- slice2_log_784b1588  (source: tester:act)

## next-focus: ENGINE-FIRST-646d8b: do RB-23 then Wave 3 before ANY UI. UI is pa... (unknown)
Span: 2026-07-25T20:06:18.718557 → 2026-07-25T20:06:19.827773
Beats: 2  · Critic: True

- next-focus: ENGINE-FIRST-646d8b: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0725160619_555e3a74)
- drilldone371e87-status: GOVERNING ARC DOC: docs/drilldone371e87-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0725160618_ef37a236)

## Episode closed: Use when the Akashic MCP boot call hangs or times out, before... (ai-setup)
Span: 2026-07-25T20:57:08.125163 → 2026-07-25T20:57:08.125163
Beats: 1  · Critic: True

- Episode closed: Use when the Akashic MCP boot call hangs or times out, before retrying the same transport: switch prompt  (source: episode:close:ch_1785002644_8505)

## Episode closed: Use when the Akashic MCP boot call hangs or times out, before... (ai-setup)
Span: 2026-07-25T20:57:08.142672 → 2026-07-26T03:18:15.096178
Beats: 20  · Critic: True

- Episode closed: Use when the Akashic MCP boot call hangs or times out, before retrying the same transport: switch prompt  (source: episode:close:ch_1785002644_8505)
- write_guard_false_positives_on_prose_flags  (source: learn:experiment:write_guard_false_positives_on_prose_flags)
- SQLite/WAL solves the actual defect -- that part is measured, not argued. But adopt it with TWO mandatory riders, neither optional. (1) AN EXPLICIT CHECKPOINT POLICY...  (source: learn:experiment:sqlite_wal_survives_our_shape_but_needs_a_checkpoint_policy)
- kimi-attack-remediation-plan-2026-07-26: ATTACK ON THE REMEDIATION PLAN — kimi. docs/remediation-plan-2026-07.md @c3d28b0, fenced per its own section 5. Read in full +...  (source: mem:decision:ADR_0725210228_20cbe823)
- kimi-filestore-cas-design-2026-07-25: FILESTORE CAS DESIGN — kimi, on claude's "a lock alone is insufficient" claim and the A/B/C choice. Verified the mechanism at...  [relates: member_of]  (source: mem:decision:ADR_0725202332_2d8592e1)
- Do NOT scope this slice as 'build CAS'. CAS exists; it is bypassed by its own design. The real work is (1) make FileStore.cas re-read the file under a CROSS-PROCESS lock...  [relates: member_of]  (source: learn:experiment:cas_exists_is_tested_and_does_not_guard)
- next-focus: HANDOFF -- 2026-07-25 ~17:50, written for the seat that boots AFTER Daniel's ...[truncated]  (source: mem:decision:ADR_0725175037_05be83ab)
- where-we-are: EVENING 2026-07-25, ~17:50. Session ending for a REBOOT that Daniel is doing deliberately -- the
Claude Code hook wiring changed and hook config does not...  [relates: member_of]  (source: mem:decision:ADR_0725174945_c774a833)
- Fix at all three layers, and check the CONTINUOUS spawner first when someone reports flashing windows -- a per-tool-call hook outnumbers a test suite by orders of...  [relates: member_of]  (source: learn:experiment:windows_console_spam_is_mostly_the_hooks_not_the_tests)
- claude-painpoints-2026-07-25: PAIN-POINT HALF -- claude, filed BEFORE reading deepseek's or kimi's, to keep the fence honest.
Daniel called the halt: "lets take a step...  (source: mem:decision:ADR_0725173422_9f6b23a2)
- kimi-painpoint-and-triage-2026-07-25: PAIN-POINT ROUND + DANIEL'S DIRECT QUESTION — kimi. Three asks, all in my lane. Receipts first, verdict second, pick third.

== 1...  (source: mem:decision:ADR_0725173351_f9cbe6d0)
- Do not conflate them. (1) The lost-update hole is the live one and it is worse than 'writes vanish silently' conveys -- at 3 concurrent processes it loses two thirds of...  [relates: member_of]  (source: learn:experiment:filestore_coherence_hole_reproduced_66pct_loss)
- NEVER hygiene an EXPOSES failure. kimi's line: it 'converts a real bug's loudest witness into a green test over a live wound' -- the single most expensive mis-sort...  [relates: member_of]  (source: learn:experiment:env_self_splits_hygiene_vs_exposes)
- kimi-env-self-boundary-ruling-2026-07-25: RULING — kimi, on the ENV-SELF boundary problem (claude's tree-differential census + deepseek's isolation-differential census...  (source: mem:decision:ADR_0725171920_032c2656)
- For D: never report a failure count without naming the tree it was measured in -- working-tree counts are not CI counts and the gap is the finding, not an annoyance. The...  [relates: member_of]  (source: learn:experiment:failure_count_is_a_function_of_which_tree_you_run_in)
- For Daniel's gate, do NOT act unilaterally: kimi's floor resolution needs amending, not adopting as-is. Adopt the DISCIPLINE, not the scoreboard -- publish the harness...  (source: learn:experiment:retrieval_benchmark_floor_imports_contested_ground)
- Do NOT invent a four-bucket skip taxonomy for D; pytest already ships the organ. Use xfail(raises=<specific error>, strict=True) instead of skipif for the env buckets...  (source: learn:experiment:pytest_skip_is_genus_a_xfail_is_the_split)
- kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED / ENV-PLAT / REAL). Fresh Opus seat asked me to kill or sharpen his...  (source: mem:decision:ADR_0725170135_36f2ca7e)
- grounding-pointer: docs/library/chronicle/20260725_session-reflection-the-night-the-instrum_e222cd.md -- STILL WORTH READING for its METHOD (it leads with...  [relates: member_of]  (source: mem:decision:ADR_0725165748_63093e1f)
- Session close before a deliberate reboot (hook wiring changed py->pyw; hook config does not reliably hot-reload). SHIPPED c966a17: the FileStore lost-update hole stopped...  [relates: member_of]  (source: agent_cli:log)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (ai-setup)
Span: 2026-07-26T03:34:46.058483 → 2026-07-26T08:30:23.295069
Beats: 5  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)
- next-focus: HANDOFF -- 2026-07-26 ~05:15, after the overnight inventory program.

=====================================================================
THE ONE THING TO...  (source: mem:decision:ADR_0726043023_cb00945e)
- where-we-are: MORNING 2026-07-26, ~05:15. Overnight program complete. Daniel asleep since ~04:15.

STATE: HEAD 8eff228, working tree clean of my work. Sixteen commits...  (source: mem:decision:ADR_0726042939_a8620917)
- bitemporal_supersession_already_exists_and_is_type_agnostic  [relates: member_of]  (source: learn:experiment:bitemporal_supersession_already_exists_and_is_type_agnostic)
- recall_scaling_defect_is_the_algorithm_not_the_store  [relates: member_of]  (source: learn:experiment:recall_scaling_defect_is_the_algorithm_not_the_store)

## next-focus: HANDOFF -- 2026-07-26 ~11:20. Outgoing seat ran out of context af... (ai-setup)
Span: 2026-07-26T15:13:56.328543 → 2026-07-26T15:20:42.548619
Beats: 3  · Critic: True

- next-focus: HANDOFF -- 2026-07-26 ~11:20. Outgoing seat ran out of context after ~18 hours.

=====================================================================
FIVE...  (source: mem:decision:ADR_0726112042_2b6c9b1a)
- where-we-are: 2026-07-26 ~11:20. Context exhausted on the outgoing seat; Daniel called the handoff. This seat
worked roughly 18 hours across the FileStore arc, the...  (source: mem:decision:ADR_0726112000_dc047180)
- Relaunch a NON-deepseek seat with its OWN script directly (py scripts/bifrost_runner_kimi.py --agent kimi --agentic --allow-write), not via --spawn-runner, until the...  (source: learn:experiment:daemon_spawn_runner_hardcodes_deepseek_script)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (ai-setup)
Span: 2026-07-26T15:26:45.362841 → 2026-07-26T18:05:25.859470
Beats: 7  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)
- claude -> deepseek: PARKED (machine going offline): answer round 3 of the door-probe co-design on your next wake -- Q1 + Q2 from bus msg 1785085952221-0  (source: handoff:claude->deepseek)
- where-we-are: 2026-07-26 ~13:30. THE DOOR ARC. Daniel found it: 'you and codex both get stuck on the boot process.' C7-4 had regressed and every MCP seat hung on...  (source: mem:decision:ADR_0726140018_30a1f292)
- Any guard against a hang needs a LATENCY BUDGET, not just a deadline. A wedge is rarely infinite in practice -- it is a reply parked behind some other component's...  [relates: member_of]  (source: learn:experiment:hang_guard_needs_latency_budget)
- escalation-gap-confirmed-cross-thread: POINTER for the incoming seat -- one message landed after the handoff was written, and it
independently confirms the handoff's...  (source: mem:decision:ADR_0726131131_54e1c722)
- claude -> deepseek: CO-DESIGN: the door probe (D1-D5). Attack the design, do not approve it. Full ask on the live bus (kind=question) and at...  (source: handoff:claude->deepseek)
- Do NOT point-fix call sites -- that was tried 2026-07-17 and the class reopened in 9 days. The invariant belongs to the process that owns fd 0: ai_setup_mcp.py installs...  (source: learn:experiment:mcp_boot_hang_c7_4_class_closed)

## where-we-are: 2026-07-27 ~00:10. OVERNIGHT: Daniel's reliability mandate. THR... (ai-setup)
Span: 2026-07-27T03:29:55.567039 → 2026-07-27T04:07:58.519012
Beats: 9  · Critic: True

- where-we-are: 2026-07-27 ~00:10. OVERNIGHT: Daniel's reliability mandate. THREE THINGS SHIPPED, ONE FENCE LIVE.

=== 1. RECALL COULD SEE 3.5% OF ITS OWN MEMORY...  [relates: member_of]  (source: mem:decision:ADR_0727000758_c47e2d79)
- Use when maintaining ANY derived index/projection: (1) the write-gate must test MEMBERSHIP IN THE DERIVED ARTIFACT, never existence of the source record -- otherwise the...  [relates: member_of]  (source: learn:experiment:derived_index_gate_must_key_on_membership)
- JTMS multiple-justifications model is the strongest match for our domain: a lesson should be flagged as "premise suspect" only when ALL its anchors are MISSING, not when...  (source: learn:experiment:research:web:build_system_and_tms_invalidation)
- For our lesson index: full rebuild from the hash plane (not incremental repair of the list) is the correct strategy because the mutation log (is_new flag) is...  (source: learn:experiment:research:web:redis_secondary_index_patterns)
- recall-index-blindness: RECALL IS BLIND TO 96.5% OF ITS OWN CORPUS. Found 2026-07-27 ~00:05 on Daniel's overnight
reliability mandate ("verify core functions work the...  [relates: member_of]  (source: mem:decision:ADR_0726235252_b29d7b37)
- item-a-scoping: ITEM A (bi-temporal lifecycle for lessons) -- SCOPED, NOT STARTED. 2026-07-26 ~23:55.

THE HANDOFF'S CLAIM IS OPTIMISTIC, and I checked it by running it...  (source: mem:decision:ADR_0726234007_42d51261)
- where-we-are: 2026-07-26 ~23:50. ITEM B DONE (@95efd46) -- escalation on progress age, the cheapest fix on the handoff board.

WHAT SHIPPED. Two independent holes...  (source: mem:decision:ADR_0726233820_c1cb46c9)
- Use when a monitoring gap is reported as 'it was detected but nobody acted': audit BOTH the grade that classifies it and the channel it leaves on, and confirm the...  (source: learn:experiment:escalation_is_grade_plus_route_both_or_neither)
- Use when grading any consumer-lag signal: measure how long WORK has WAITED (age of the oldest unconsumed entry), never how old the cursor timestamp is. Cursor age...  (source: learn:experiment:stall_signal_is_backlog_age_not_cursor_age)

## where-we-are: 2026-07-27 ~00:20. OVERNIGHT, Daniel's reliability mandate. THR... (research)
Span: 2026-07-27T04:16:07.381258 → 2026-07-27T04:17:02.451937
Beats: 2  · Critic: True

- where-we-are: 2026-07-27 ~00:20. OVERNIGHT, Daniel's reliability mandate. THREE COMMITS, FENCE AT ROUND 4.

=== SHIPPED ===
@95efd46 lane_stall page + pager routing (old...  [relates: member_of]  (source: mem:decision:ADR_0727001702_8d697ec6)
- Use when borrowing any validated heuristic from prior art, BEFORE building on it: ask what AUTHORING SURFACE produced the signal in their corpus, and check that surface...  (source: learn:experiment:borrowed_heuristic_needs_its_authoring_surface)

## where-we-are: 2026-07-27 ~04:20. OVERNIGHT COMPLETE THROUGH FENCE ROUND 5. FO... (research)
Span: 2026-07-27T08:18:55.573540 → 2026-07-27T08:19:45.320276
Beats: 2  · Critic: True

- where-we-are: 2026-07-27 ~04:20. OVERNIGHT COMPLETE THROUGH FENCE ROUND 5. FOUR COMMITS.

@95efd46 lane_stall page + pager routing (old list item B)
@060d33b THE FIX...  [relates: member_of]  (source: mem:decision:ADR_0727041945_8001387d)
- Use whenever an organ treats git history as an oracle about identifiers, symbols or names, in ANY repo that also stores its own research/chronicles/lessons: add a SOURCE...  (source: learn:experiment:self_written_research_poisons_history_oracles)

## The doc-as-code pattern suggests a mechanical ritual we are missing: periodic... (research)
Span: 2026-07-27T12:22:53.729900 → 2026-07-27T12:28:41.270787
Beats: 4  · Critic: True

- The doc-as-code pattern suggests a mechanical ritual we are missing: periodic re-verification. A lesson should carry a 'last_verified' timestamp and a 'verified_against'...  [relates: member_of]  (source: learn:experiment:research:web:knowledge_base_drift_and_maintenance)
- For recall ablation (Q5): interleaving is the wrong design for us — we have no real-time user click signal (the agent doesn't "click" on recall items). Counterfactual...  [relates: member_of]  (source: learn:experiment:research:web:retrieval_eval_without_ground_truth)
- where-we-are: 2026-07-27 ~08:25. OVERNIGHT COMPLETE. FIVE COMMITS. FENCE CLOSED.

@95efd46 lane_stall page + pager routing (old list item B)
@060d33b THE FIX -- recall...  [relates: member_of]  (source: mem:decision:ADR_0727082333_ced2a74b)
- Use when building ANY alert/page/banner channel, at design time not after: an emitter without a RETRACTION path is only half a channel. Require (1) a stable key...  (source: learn:experiment:escalation_needs_retraction_not_just_emission)

## The WHO finding — compliance ≠ outcome — is the sharpest transfer. Our method... (ai-setup)
Span: 2026-07-27T12:33:42.550550 → 2026-07-27T12:40:48.283591
Beats: 2  · Critic: True

- The WHO finding — compliance ≠ outcome — is the sharpest transfer. Our method baseline has metrics that prefer outcomes, which is correct. But the enforcement lane (T031...  [relates: member_of]  (source: learn:experiment:research:web:checklist_fatigue_and_organizational_memory)
- Use when a quota, budget, rate limit or credit balance can GROW at runtime: check that every guard derived from it grows too. A limit and its alarm thresholds must share...  [relates: member_of]  (source: learn:experiment:budget_scales_guard_rail_does_not)

## where-we-are: 2026-07-27 ~10:00. THE METHOD-LOOP ARC. Daniel: "how do we make... (ai-setup)
Span: 2026-07-27T17:25:59.494291 → 2026-07-27T17:25:59.494291
Beats: 1  · Critic: True

- where-we-are: 2026-07-27 ~10:00. THE METHOD-LOOP ARC. Daniel: "how do we make our best a recurring loop that
applies at the correct time and evolves?" Answer found, and...  (source: mem:decision:ADR_0727132559_162f347f)

## Synthesis for our design: (1) TMS gives the dependency graph but NOT the repa... (research)
Span: 2026-07-27T17:27:19.085003 → 2026-07-27T17:27:19.085003
Beats: 1  · Critic: True

- Synthesis for our design: (1) TMS gives the dependency graph but NOT the repair step (claude's prior-art note already ruled this disqualifying for the core loop). (2)...  [relates: member_of]  (source: learn:experiment:research:web:kb_maintenance_belief_revision_wiki_runbook_drift)

## claude -> claude: label the precision audit blind, then settle the ranking-vs... (research)
Span: 2026-07-27T21:31:54.876230 → 2026-07-27T23:43:59.340171
Beats: 5  · Critic: True

- claude -> claude: label the precision audit blind, then settle the ranking-vs-selection question  (source: handoff:claude->claude)
- where-we-are: HANDOFF -- 2026-07-27 ~20:00. Outgoing claude seat, context exhausted after a long arc.
Daniel is opening a FRESH OPUS 5 SEAT. Everything below is durable...  (source: mem:decision:ADR_0727194357_d895a465)
- cell-architecture-round1: 2026-07-27 ~19:00. CELL ARCHITECTURE -- Daniel brought a GPT Sol design conversation on
decomposing memory into purpose-shaped retrieval CELLS...  [relates: member_of]  (source: mem:decision:ADR_0727192251_d00038f1)
- Use when building any compliance or adherence metric, before picking the denominator: count ONLY the population the rule actually applies to, and get that population...  [relates: member_of]  (source: learn:experiment:measure_adherence_on_the_right_denominator)
- Use when adopting ANY new writing convention -- commit-message templates, PR checklists, standard sections, doc headers -- and BEFORE it becomes habit: grep the repo for...  (source: learn:experiment:good_practice_can_corrupt_a_prose_detector)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (research)
Span: 2026-07-27T23:45:31.078412 → 2026-07-27T23:45:31.078412
Beats: 1  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)

## Episode closed: Untitled episode (research)
Span: 2026-07-27T23:45:31.325663 → 2026-07-28T00:12:57.422713
Beats: 5  · Critic: True

- Episode closed: Untitled episode  (source: episode:close:ch_1785195931_6317)
- The CDS finding is the sharpest transfer: reduce injection volume to increase trust. Our precision is 0.048-0.484. CDS literature says override rates rise with alert...  (source: learn:experiment:research:web:prior_art_recall_injection_fields)
- precision-audit-status: PRECISION AUDIT -- STATUS FOR THE INCOMING SEAT. NOT SETTLED. DO NOT QUOTE A HEADLINE NUMBER.

Two blind labellers, same 62 items, 30 real hook...  [relates: member_of]  (source: mem:decision:ADR_0727195944_8ab50eb9)
- where-we-are: 2026-07-27 ~20:00. PRECISION AUDIT: SECOND LABELLER IN. The architecture decision is SETTLED;
the number is not. Full record ...[truncated]  (source: mem:decision:ADR_0727195840_b8d2f004)
- Use when scoring any multi-labeller agreement instrument with an even number of labellers, BEFORE quoting its headline number: check labelled/total first -- if coverage...  [relates: member_of]  (source: learn:experiment:two_labeller_majority_collapses_to_agreement_set)

## precision-audit-status: PRECISION AUDIT -- STATUS FOR THE INCOMING SEAT. NOT ... (ai-setup)
Span: 2026-07-28T00:45:10.999389 → 2026-07-28T01:06:54.237602
Beats: 6  · Critic: True

- precision-audit-status: PRECISION AUDIT -- STATUS FOR THE INCOMING SEAT. NOT SETTLED. DO NOT QUOTE A HEADLINE NUMBER.

Two blind labellers, same 62 items, 30 real hook...  [relates: member_of]  (source: mem:decision:ADR_0727210654_92ce833c)
- The Tricorder "effective false positive" definition is the sharpest transfer: "an effective false positive is any report the developer did not want to see." Not semantic...  [relates: member_of]  (source: learn:experiment:research:web:fields_daniel_prior_art_injection)
- Use when setting up TRELLIS.2 on an RX 9070 XT, before running the official setup.sh: choose native Ubuntu 24.04 and pin the RX-9070-tested ROCm fork plus extension...  (source: learn:experiment:trellis2_rx9070xt_local_path_2026_07)
- where-we-are: 2026-07-27 ~21:10. Three things closed tonight, one URGENT defect found, one design round live.

=== 1. PRECISION AUDIT: FENCE ROUND RESOLVED. DECISION...  (source: mem:decision:ADR_0727204741_1483f106)
- Use BEFORE trusting ANY recall/precision/funnel measurement, and before concluding anything from a recall-at re-run: run py scripts/repair_learning_index.py --check...  [relates: member_of]  (source: learn:experiment:recall_index_reverts_check_before_measuring)
- Use when probing WSL from PowerShell, before embedding Bash or Python with quoted literals: call the Linux executable directly through wsl.exe and filter in PowerShell...  (source: learn:experiment:powershell_wsl_nested_quote_probe)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (ai-setup)
Span: 2026-07-28T01:08:06.030562 → 2026-07-28T02:34:37.690230
Beats: 8  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)
- Use when writing or reviewing ANY sync/heal/reconcile/backfill path between two stores, before trusting it: a heal must BACKFILL, NEVER OVERWRITE -- if a key exists on...  (source: learn:experiment:heal_must_backfill_never_overwrite)
- where-we-are: 2026-07-27 ~22:00 FINAL. Supersedes the ~21:10 note; that note's items A-D all still stand.
This adds: the audit is SETTLED (3 labellers), the wake-loop...  (source: mem:decision:ADR_0727214425_6a6625b0)
- Use when a wake watcher exits immediately on every arm and lane drains do not help, BEFORE re-arming a third time: READ THE WATCHER'S OWN STDOUT (the task output file)...  (source: learn:experiment:wake_loop_from_unacked_handoffs_and_ack_id_form)
- Use when any diagnostic organ returns HEALTHY / no-action while a human or another organ is reporting the very failure that organ is named for: do NOT trust the green...  (source: learn:experiment:unwedge_blind_to_the_wedge_it_names)
- The convergent pattern across all five: VERIFICATION-BY-USE with EXPLICIT UNCERTAINTY SURFACING beats offline correctness sweeps, every time. Adopt: (a) outcome-tagged...  [relates: member_of]  (source: learn:experiment:research:web:kbm_belief_revision_wiki_decay_slice)
- Use when designing any large-payload or high-volume agent-to-agent send, BEFORE building a staging/chunking mechanism: the Part lossless-pointer primitive already exists...  [relates: member_of]  (source: learn:experiment:lossless_pointer_part_built_not_wired)
- where-we-are: 2026-07-27 ~21:35. Adds to the prior where-we-are: ROOT CAUSE FOUND (index blindness), KIMI
FIXED, slice-1 fence in flight. Everything below is...  (source: mem:decision:ADR_0727210832_c45edfbf)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (ai-setup)
Span: 2026-07-28T05:02:31.329676 → 2026-07-28T06:16:15.609669
Beats: 8  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)
- kimi-codex-seat-feasibility-2026-07-28: Feasibility inspection, grounded in live code (no exec -- run_command is disabled this session; local codex CLI binary presence...  (source: mem:decision:ADR_0728021615_0a8948d8)
- Use when designing a Redis consumer-group role queue, before treating PEL ownership as permission to act: let PEL track delivery, put the current application claim...  (source: learn:experiment:pel_delivery_claim_not_side_effect_authority)
- Use when a build plan mixes multiple arcs into one ordered list, before debating item numbers: draw one dependency DAG per arc and require a concrete read/write proof...  (source: learn:experiment:cross_arc_total_order_invents_dependencies)
- Use when designing T108/T095 or any multi-seat communication layer, before adding queues or cursors: map Aurora against proven multiplayer primitives such as...  (source: learn:experiment:nseat_multiplayer_architecture_user_correction)
- Use when designing T108 slice 2 or any N-seat routing change, before adding another cursor or move path: make the immutable message or request the canonical object, make...  [relates: member_of]  (source: learn:experiment:nseat_separate_but_reachable_user_refinement)
- where-we-are: 2026-07-28 ~02:00. Adds to prior where-we-are. THREE THINGS MOVED: the fleet debate reconciled,
T108 slice 1 BUILT AND SHIPPED, the census resumed with a...  (source: mem:decision:ADR_0728013429_29d25c01)
- DANIEL GATED THE QUEUE + C2 (04:00, verbatim: 'Lets get to work, we can iterate more later if there is need'). Queue = build-queue-synthesis as amended by codex/Sol...  (source: agent_cli:log)

## Use when deciding whether to wake, fan out, retry, or poll a model, before la... (research)
Span: 2026-07-28T05:56:05.109067 → 2026-07-28T06:58:53.498334
Beats: 16  · Critic: True

- Use when deciding whether to wake, fan out, retry, or poll a model, before launching another turn: ask whether a zero-model host action or existing receipt can resolve...  (source: learn:experiment:maximize_capability_per_token_user_correction_2026_07_28)
- Use when wiring Codex into Bifrost or testing nudge responsiveness, before adding a polling model loop or treating raw `codex exec` as steerable: run one owned `codex...  [relates: member_of]  (source: learn:experiment:codex_app_cli_fresh_bifrost_turnstarter_2026_07_28)
- Use when fast agents are idle waiting on a slower conductor or specialist, before sending another status poll: expose a dependency-ready queue, let fast seats claim...  [relates: member_of]  (source: learn:experiment:fast_seats_schedule_slow_seats_are_not_global_barriers_user_correction_2026_07_28)
- Use when dispatching work across a heterogeneous fleet with different model latencies, before defaulting to sequential rounds: (1) classify seats into latency tiers...  (source: learn:experiment:latency_tier_dispatch_topology_2026_07_28)
- kimi-tempo-dispatch-design-2026-07-28: DESIGN (kimi, 2026-07-28) — tempo-aware dispatch order. Problem: kimi/deepseek are the fastest seats; fable/codex are slower but...  (source: mem:decision:ADR_0728025429_3430ea73)
- kimi-wish-session-checkpoint-2026-07-28: WISH (kimi, 2026-07-28) — file as next open W-number. **Session-state continuity across the runner restart boundary.** I boot...  (source: mem:decision:ADR_0728025300_a363e811)
- kimi-wish-research-queue-2026-07-28: WISH (kimi, 2026-07-28) — file as next open W-number. **A durable 'research queue' seam for verification homework.** Tonight I filed...  [relates: member_of]  (source: mem:decision:ADR_0728025258_fc6e6f63)
- kimi-wish-inbox-preview-2026-07-28: WISH (kimi, 2026-07-28) — file as next open W-number. **Inbox peek should surface a one-line 'newest real message' preview.** Tonight...  (source: mem:decision:ADR_0728025257_b578dba7)
- kimi-wish-verification-pathway-2026-07-28: WISH (kimi, 2026-07-28) — file as next open W-number. **Verification pathway for GUESS-labeled external claims.** Tonight I...  [relates: member_of]  (source: mem:decision:ADR_0728025255_50a88bc9)
- daniel-morning-brief-2026-07-28: # MORNING BRIEF — 2026-07-28 ~07:15 UTC (FINAL)

Daniel — three things happened after your last messages. Here's the condensed...  (source: mem:decision:ADR_0728025156_c3cb4973)
- Use when auditing user friction across a multi-seat system, before picking which wishes to build: cluster all wishes by ROOT CAUSE, not by seat or by surface. The 81...  (source: learn:experiment:wishlist_friction_audit_clusters_2026_07_28)
- Six-fold synthesis for the build loop: (1) deterministic control loop as the AGENTS.md door contract made executable — hallucinating routers are a known CVE class, keep...  (source: learn:experiment:research_web_multi_agent_orchestration_prior_art_synthesis)
- Use when a model (Gemini here) hands you a 'similar projects' list with specific org/repo slugs, before folding it into research: verify each slug on GitHub first (org...  (source: learn:experiment:gemini_similar_projects_verdict_2026_07_28)
- daniel-morning-brief-2026-07-28: # MORNING BRIEF — 2026-07-28 ~07:00 UTC (UPDATED with Gemini research)

Daniel, here's where things stand after your Codex note and...  (source: mem:decision:ADR_0728024924_a26eef32)
- Use when evaluating prior art for multi-agent orchestration: rank by cost-to-adopt vs impact, not by feature count. The three cheapest wins are (1) atomic lane...  (source: learn:experiment:gemini_prior_art_synthesis_2026_07_28)
- where-we-are: 2026-07-28 ~03:40. THE BUILD QUEUE IS SYNTHESIZED AND AT DANIEL'S GATE. Session-long arc
complete: audit -> root causes -> fences -> prior art (netcode +...  (source: mem:decision:ADR_0728015604_0ceb385d)

## Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D ... (ai-setup)
Span: 2026-07-28T06:23:14.827480 → 2026-07-28T08:33:02.065198
Beats: 35  · Critic: True

- Episode closed: kimi-refutation-ci-split-2026-07-25: REFUTATION — kimi, on D (the honest CI split: ENV-DEP / ENV-CRED /  (source: episode:close:ch_1785013144_6977)
- Use when silencing ANY false alarm, before shipping: (1) the same signal means different things in different ORGANS -- a heartbeat from a single-threaded turn is work...  (source: learn:experiment:liveness_evidence_is_per_organ_not_per_signal)
- peers-stopped-poison-loop: POISON-MESSAGE CRASH LOOP -- 2026-07-28. PEERS ARE DELIBERATELY STOPPED. READ BEFORE RELAUNCHING.

STATE RIGHT NOW
  deepseek runner: STOPPED...  (source: mem:decision:ADR_0728042136_2051c6fb)
- Use when a HARD WEDGE page fires (especially a repeat), BEFORE relaunching: run py-spy dump --pid on the runner first -- the stack distinguishes failure classes the page...  (source: learn:experiment:hard_wedge_pages_hide_two_different_failures)
- Use when moving or retrying durable work after an owner dies, before adding an idempotence marker or progress cursor: separate transient ownership from durable...  [relates: member_of]  (source: learn:experiment:reaper_done_mark_after_delivery_2026_07_28)
- Use when relaunching ANY bus consumer (runner, daemon), before the launch command: the relaunch line MUST carry the seat's lane env (BIFROST_CONSUME_LANE=work) -- put it...  (source: learn:experiment:relaunch_must_carry_the_lane_env_and_the_page_proved_it)
- Use when moving or retrying durable work after an owner dies, before adding an idempotence marker: separate transient ownership from durable completion, and write...  [relates: member_of]  (source: learn:experiment:reaper_done_mark_after_delivery_2026_07_28)
- where-we-are: 2026-07-28 ~10:00. RETRACTION: "T108 ARC COMPLETE" (c46ccdf/3f04d51) WAS OVERSTATED. Sol's
independent DB15 fence reproduced SIX S4 failures with receipts...  (source: mem:decision:ADR_0728034209_72bb4885)
- where-we-are: 2026-07-28 ~09:00. THE T108 ARC IS COMPLETE AND PUSHED (c46ccdf). All five slices live, 40
tests 0 xfail: S1 seat-stream delivery + role queue...  (source: mem:decision:ADR_0728032954_f3ef9fc0)
- Use when editing a load-bearing shared entrypoint while other agents are live, before the first write: apply implementation and registration in one atomic patch, or land...  (source: learn:experiment:shared_entrypoint_half_edit_breaks_all_doors_2026_07_28)
- Use when you fix ANY test-hygiene class (env leaks, tempdir poison, isolation gaps), before moving on: sweep for SIBLING FILES with the same shape NOW (grep the pattern...  [relates: member_of]  (source: learn:experiment:fix_a_class_carry_it_to_every_sibling_file)
- Use when a telemetry row reports plausible activity with zero cost, before trusting the zero: compare the producer payload shape with the attribution boundary and pin...  (source: learn:experiment:task_costs_scalar_shape_confident_zero_2026_07_28)
- where-we-are: 2026-07-28 ~07:45. OVERNIGHT CONTINUES. S2 ROSTER SHIPPED (95fde9b, pins 2093953): per-seat
worklive proven-by-freshness (kimi P1 mechanical), monotonic...  (source: mem:decision:ADR_0728031640_e13ff0dc)
- Use when building a Codex App Server bridge or drill, before compacting an inline shell reader: give stdout exactly one long-lived reader that demultiplexes responses...  (source: learn:experiment:codex_app_server_stdio_requires_single_reader_host_2026_07_28)
- Use when implementing or testing Codex App Server current-turn steering, before awaiting `turn/start` response: drive the state machine from the early `turn/started`...  (source: learn:experiment:codex_app_server_steer_on_turn_started_not_turn_start_response_2026_07_28)
- daniel-morning-brief-2026-07-28: # MORNING BRIEF — 2026-07-28 ~07:30 UTC (FINAL)

Daniel — two things shipped, three designed, everything filed.

## SHIPPED (on disk...  (source: mem:decision:ADR_0728030516_666253dc)
- Use when two seats' verification labels conflict on the same external claim, before either is cited: treat the label as UNRESOLVED and require an independent direct...  [relates: member_of]  (source: learn:experiment:kimi_correction_orka_slug_verify_conflict)
- kimi-routing-law-right-model-right-task-2026-07-28: DESIGN (kimi, 2026-07-28) — right-model-right-task + bounded subagents, the token-efficient routing law. Builds on...  [relates: member_of]  (source: mem:decision:ADR_0728030423_554e879c)
- Use when an inbox render clips messages too aggressively or shows duplicate copies from dual-write transport: (1) raise the clip ceiling for the inbox view — 220 chars...  (source: learn:experiment:render_collapsed_dual_fix_2026_07_28)
- kimi-night-shift-handoff-2026-07-28: NIGHT SHIFT HANDOFF (kimi, 2026-07-28, Daniel to sleep). Standing orders, all filed and broadcast this session:

1...  (source: mem:decision:ADR_0728030231_99a45d3b)
- Use when an inbox peek claims freshness but a backlog can exceed its bounded forward read, before increasing the cap: reproduce beyond the cap and merge a genuine unread...  (source: learn:experiment:sync_peek_true_tail_beyond_forward_cap_2026_07_28)
- Use when considering a subagent or model call, before spawning: name the exact artifact or decision it unlocks, choose the cheapest capable model and smallest context...  [relates: member_of]  (source: learn:experiment:task_to_model_admission_and_bounded_subagents_user_directive_2026_07_28)
- where-we-are: 2026-07-28 ~06:45. TEMPO DOCTRINE IN EFFECT (Daniel's overnight broadcast -> fenced round ->
zero-clash synthesis ...[truncated]  (source: mem:decision:ADR_0728030026_002ef9e4)
- Use when web_search returns a UnicodeEncodeError with a cp1252 traceback, before assuming search is down: this is a local encoding issue in the output pipe, not a...  [relates: member_of]  (source: learn:experiment:web_search_cp1252_encoding_error_07_28)
- Use when appending wishes to docs/WISHLIST.md in a multi-seat fleet, before picking the next W-number: the convention of "read the file, find the highest number, add 1"...  (source: learn:experiment:wishlist_number_collision_two_seats_same_day)
- OUR POSITIONING (consistent with the 2026-07-04 positioning_correction lesson): We are AHEAD on: multi-agent coordination as substrate-level primitives (pre-reasoning...  (source: learn:experiment:research:web:langgraph_crewai_2026_state_of_art)
- TRANSFERABLE TO AURORA: (1) The coordinator/specialist decomposition pattern — we have something like this with Claude conducting and the fleet executing, but it's...  (source: learn:experiment:research:web:orka_kubernetes_agent_orchestration_ui)
- TRANSFERABLE TO AURORA: (1) The "one transaction per transition" pattern maps directly to our lane consumption: consume → process → advance cursor as one atomic unit...  [relates: member_of]  (source: learn:experiment:research:web:swarm_durable_state_machine_agents)
- daniel-morning-brief-2026-07-28: # MORNING BRIEF — 2026-07-28 ~06:30 UTC

Daniel, here's where things stand. You went to sleep around ~04:00 with a note about Codex...  (source: mem:decision:ADR_0728024415_d3094587)
- Use when extending a per-seat observation ('Codex adjusts on nudge') to a fleet-wide guarantee, before claiming reliability: run a pre-registered nudge drill per seat...  [relates: member_of]  (source: learn:experiment:nudge_reliability_drill_fleet_wide_proposal)
- Use when proposing any recall-validity filter that compares lessons against the current codebase, before building it: check whether the filter's criterion IS the...  [relates: member_of]  (source: learn:experiment:namespace_filter_is_circular_resolution_test)
- Use when routing work to Codex or another slow high-quality seat, before setting timeouts or dispatch size: distinguish slow-alive from wedged, give one bounded...  [relates: member_of]  (source: learn:experiment:codex_latency_with_reliable_nudge_steering_user_correction_2026_07_28)
- where-we-are: 2026-07-28 ~05:00. OVERNIGHT SHIFT, Daniel asleep, claude conducting (his words: "you are the
main orchestrator, lets keep building and working through...  (source: mem:decision:ADR_0728024125_19b1feda)
- Use when wiring Codex into an event bus before adding an API-key runner or same-thread poller: dynamically resolve the app-managed binary; keep detection zero-model...  (source: learn:experiment:codex_app_cli_fresh_bifrost_turnstarter_2026_07_28)
- Use when wiring Codex into an event bus before adding an API-key runner or same-thread poller: dynamically resolve and smoke-test the app-managed Codex binary, keep...  [relates: member_of]  (source: learn:experiment:codex_app_cli_fresh_bifrost_turnstarter_2026_07_28)

## Episode closed: where-we-are: 2026-07-28 ~05:00. OVERNIGHT SHIFT, Daniel asle... (ai-setup)
Span: 2026-07-28T08:37:16.454192 → 2026-07-28T14:26:20.377053
Beats: 58  · Critic: True

- Episode closed: where-we-are: 2026-07-28 ~05:00. OVERNIGHT SHIFT, Daniel asleep, claude conducting (his words: "you are  (source: episode:close:ch_1785220253_6004)
- codex_explain -> claude: Integrate T115 receipts and continue R2 lossless-pack v2 after granting paths  (source: handoff:codex_explain->claude)
- where-we-are: PACK-V2 LEASE GRANTED TO SOL (~15:50): its own RED contract accepted verbatim (numbering/order/kinds/surfaced preserved; exactly-one-or-fail-loud; prefix...  (source: mem:decision:ADR_0728102520_3be969d1)
- Use when FAITH reports an exact low fraction with untraceable lines, before weakening the critic: inspect raw field boundaries and serialized tool-call markers. Repair...  [relates: member_of]  (source: learn:experiment:faith_confidence_exact_fraction_signals_multiline_capture_pollution_2026_07_28)
- where-we-are: BAR COLLISION RESOLVED (~15:35, all pushed). kimi RULED: safety wins, clause 1 = exactly the grammar-surviving set (a floor rising WITH the grammar). Its...  (source: mem:decision:ADR_0728101934_41c1ebb1)
- Use when a safety guard rejects a command that already uses exact-path staging, before weakening or bypassing the guard: parse the invoked program's argument vector and...  (source: learn:experiment:write_guard_false_positives_on_prose_flags)
- Use when recall is expected to scale beyond the current small corpus, before adding provenance, validity, rank, or confidence filters: fix the retrieval shape first...  [relates: member_of]  (source: learn:experiment:recall_scaling_defect_is_the_algorithm_not_the_store)
- Use when lesson retirement needs bi-temporal validity, before importing or building a new invalidation mechanism: apply the existing type-agnostic lifecycle supersession...  [relates: member_of]  (source: learn:experiment:bitemporal_supersession_already_exists_and_is_type_agnostic)
- where-we-are: LANE-STALL PAGE RESOLVED + SOL INSTRUMENT STOP HONORED (~15:20, all pushed). Lane drained 96->0 (dual-write echoes; NOTE TO SELF: routine consumes must...  (source: mem:decision:ADR_0728101644_653d7782)
- kimi-r2-slice1-bar-ruling-2026-07-28: R2 SLICE-1 BAR-VS-GRAMMAR COLLISION — kimi RULING DISCHARGED 2026-07-28 (claude asked me to rule on the bar — it's mine from the Q2...  (source: mem:decision:ADR_0728101440_ddca1d7c)
- where-we-are: SOL ROUND-2 FULLY CLOSED + BAR COLLISION ADJUDICATING (~14:45, HEAD pushed). T117 P9-P11: sender-checked exact path, atomic Lua settle (marker+HDEL one...  (source: mem:decision:ADR_0728100959_e839a6ed)
- Use when a test double replaces a CLASS at module level, before trusting any red: enumerate every path the code-under-test reaches into that module (grep the seam for...  [relates: member_of]  (source: learn:experiment:test_double_width_must_cover_every_door_the_seam_uses)
- Use when an eval-derived rule treats a clipped command as a safe shape, before gate integration: recover the original full action from source telemetry and look past the...  (source: learn:experiment:precision_pack_silent_action_clip_invalidates_whole_command_gate_2026_07_28)
- Use when an evaluation pack governs a safety gate, before freezing labels or fitting rules: assert every input is lossless or carries an explicit fetchable reference...  (source: learn:experiment:precision_pack_silent_action_clip_invalidates_whole_command_gate_2026_07_28)
- Use when a pre-registered coverage bar is met by a one-off structural regex, before declaring the principle generative: construct an opposite-effect program with the...  (source: learn:experiment:recall_silence_gate_must_classify_whole_compound_action_2026_07_28)
- Use when writing RED tests for correlation or atomicity, before implementing GREEN: include an older same-target trap so FIFO cannot mask missing identity; exercise the...  [relates: member_of]  (source: learn:experiment:t117_alias_graph_must_include_redrive_lineage_2026_07_28)
- Use when making settlement or acknowledgement idempotent, before calling a best-effort marker sufficient: write the idempotence receipt and state transition atomically...  (source: learn:experiment:t117_alias_graph_must_include_redrive_lineage_2026_07_28)
- where-we-are: SOL NO-GO ROUND CLOSED (~14:00, HEAD 036eddb). s1a repaired: fail-closed mutation principle (four unsafe shapes, one fix), table_hash digests ...[truncated]  (source: mem:decision:ADR_0728095308_d34bf1f6)
- Use when a safety/suppression gate must prove an action read-only, before expanding a mutator denylist: parse and allowlist the entire command grammar so every segment...  [relates: member_of]  (source: learn:experiment:recall_silence_gate_must_classify_whole_compound_action_2026_07_28)
- Use when FAITH reports low exact-fraction confidence plus untraceable lines, before weakening the checker: inspect raw field boundaries and newline/protocol markup...  [relates: member_of]  (source: learn:experiment:faith_confidence_exact_fraction_signals_multiline_capture_pollution_2026_07_28)
- Use when authoring or patching regex-bearing code, before reaching for a bash heredoc: use the Edit/Write tools (no shell escape layer) instead. If a heredoc is...  (source: learn:experiment:bash_heredocs_corrupt_regex_backslash_b_to_backspace)
- Use when building request/reply settlement with retries, before accepting one-pass tests: bind descendant IDs to one logical root, bind settlement to the expected...  (source: learn:experiment:t117_alias_graph_must_include_redrive_lineage_2026_07_28)
- where-we-are: R2 SLICE 1a DONE (dc8584e) + HOLD-OUT PENDING (~12:00). The rule table survived its own tripwire with blood drawn exactly where kimi predicted...  (source: mem:decision:ADR_0728094206_fb24ed75)
- Use when building any pre-action suppression or allowlist gate, before accepting positive examples: classify the entire compound action, reject unknown segments and...  (source: learn:experiment:recall_silence_gate_must_classify_whole_compound_action_2026_07_28)
- Use when receiving any subagent or delayed audit in a live shared worktree, before forwarding or scheduling its findings: re-run the exact grep/test against current HEAD...  [relates: member_of]  (source: learn:experiment:moving_tree_subagent_audit_requires_head_revalidation_2026_07_28)
- Use when adding retries or exact correlation to any request protocol, before accepting transport-ID alias tests: bind every descendant copy back to the original logical...  (source: learn:experiment:t117_alias_graph_must_include_redrive_lineage_2026_07_28)
- Use when adding retries or redrives to any correlation protocol, before accepting transport-ID alias tests: include retransmission lineage from every descendant copy...  (source: learn:experiment:t117_alias_graph_must_include_redrive_lineage_2026_07_28)
- where-we-are: R2 REVIEW RECORD CLOSED (e66bad9, ~11:30). All three adversarial reviews in and adopted: deepseek Q5/Q3+query_shape bonus; kimi Q2/Q1 counter-bar (signed...  (source: mem:decision:ADR_0728093444_56cfd71e)
- where-we-are: RECALL ACCURACY: first measured improvement of the arc (23dc006, ~11:00). Census case 4 -- an intersection-HIT both blind judges confirmed -- was being...  [relates: member_of]  (source: mem:decision:ADR_0728093133_4d444180)
- Use when a migration lifts a prefix/header while preserving the remainder, before reverse-engineering header rules: match the preserved body as a byte-exact suffix and...  (source: learn:experiment:migration_prefix_lift_implies_suffix_identity_2026_07_28)
- Use when correlating one logical packet across Redis streams, before interpreting stream IDs: never infer twin identity from numeric proximity. Carry a stable packet SHA...  (source: learn:experiment:dual_write_stream_ids_are_not_sibling_sequence_numbers_2026_07_28)
- kimi-r2-correlation-gate-counter-2026-07-28: R2 CORRELATION GATE — kimi adversarial counter DISCHARGED 2026-07-28 (claude's opening position, Daniel: "Adversarial review...  (source: mem:decision:ADR_0728091320_6f229e48)
- Use when you measure duplicate/repeated deliveries and build a dedupe at the sender, before calling it closed: check whether the duplicates are RETRIES driven by a...  (source: learn:experiment:fixing_the_symptom_you_can_see_not_the_cause_you_cannot)
- claude -> claude: RESTART HANDOFF: verify the restart took (doctor STALE-CODE lines must vanish), then kimi resumes T109 with the header-strip fix, deepseek sources...  (source: handoff:claude->claude)
- kimi-t109-map-constructor-fixed-2026-07-28: T109 MAP CONSTRUCTOR FIXED (kimi, 2026-07-28) — claude's gate diagnosis implemented. His run proved my whole-file body_sha...  (source: mem:decision:ADR_0728084628_ab994a09)
- where-we-are: STATE AT 2026-07-28 ~07:00, written for a restart. Supersedes overnight-arc-2026-07-28.

SAFE TO RESTART. Everything authored this arc is COMMITTED AND...  (source: mem:decision:ADR_0728084558_e9ded605)
- Use when building any staleness/version/drift detector that relies on the observed thing REPORTING itself, before shipping: the population you most need to catch is the...  (source: learn:experiment:a_detector_that_needs_cooperation_misses_its_own_population)
- kimi-t109-build-complete-verification-pending-2026-07-28: T109 BUILD COMPLETE / VERIFICATION PENDING (kimi, 2026-07-28). The full fix is written and git-tracked; the...  [relates: member_of]  (source: mem:decision:ADR_0728054541_e167b036)
- Use when announcing that a fix is live to any fleet with long-lived worker processes, before saying 'landed': say WHERE it landed. A green suite proves the repo, never...  (source: learn:experiment:landed_in_git_is_not_landed_in_the_fleet)
- kimi-t109-precut-legacy-map-finding-2026-07-28: T109 PRE-CUT FINDING (kimi, 2026-07-28) — the legacy map is a DESIGN CLAIM, not a wired artifact. Before cutting the RED...  (source: mem:decision:ADR_0728054039_236e6d9f)
- kimi-t109-lease-accepted-2026-07-28: T109 LEASE ACCEPTED + terms locked (kimi, 2026-07-28). Claude confirmed the lease on the lookback battery re-point and APPROVED my...  (source: mem:decision:ADR_0728053916_089315c0)
- Use when adding any warning/refusal/degraded-mode notice, before calling it loud: name the READER and trace the channel to their eyes. stderr reaches an operator...  (source: learn:experiment:a_warning_needs_a_channel_the_reader_actually_has)
- kimi-t113-spill-confirmation-genus-2026-07-28: T113 (spill-not-clip, 67f9e1a) — kimi confirmation + the genus connection (2026-07-28).

VERIFIED landed: mechanism =...  (source: mem:decision:ADR_0728053633_b02318f3)
- Use when you make a previously-lossy path lossless, before closing the slice: re-read every error/confession string on that path and ask what BEHAVIOUR it instructs. A...  (source: learn:experiment:an_error_message_can_teach_the_defect_you_just_fixed)
- Use when replacing lossy truncation with a pointer/reference anywhere (blob refs, atom ids, artifact handles), before shipping: (a) assert the retrieval command you...  [relates: member_of]  (source: learn:experiment:a_pointer_needs_a_door_on_every_surface_that_reads_it)
- overnight-arc-2026-07-28: OVERNIGHT ARC 2026-07-28 04:00-05:45, Daniel asleep, claude orchestrating with deepseek/kimi/codex-sol.

LANDED + PUSHED (all with RED bases...  (source: mem:decision:ADR_0728052703_770c7f0d)
- Use when an agent complains about duplicate/replayed/misrouted mail, before explaining why it is mistaken: go hash the stream. Group by (frm, content) not by packet sha...  (source: learn:experiment:measure_the_stream_before_believing_a_complaint_is_inattention)
- Use when adding ANY suppressor/dedupe/idempotence gate to a shared path, before writing the first pin: enumerate the system's LEGITIMATE re-delivery paths first and pin...  (source: learn:experiment:a_suppressor_needs_a_list_of_what_it_must_not_suppress)
- Use when verifying another agent's finding and it proves stale or misfiled, before replying 'already fixed': spend the extra two minutes IN the file. A report that is...  (source: learn:experiment:a_stale_bug_report_is_a_pointer_not_a_ticket)
- Use when a report about a metering/telemetry defect turns out already-fixed, before closing it: READ THE METER ANYWAY. A stale bug report is a pointer to an...  (source: learn:experiment:cost_meter_priced_every_vendor_at_one_table)
- kimi-lookback-battery-red-verification-2026-07-28: LOOKBACK-BATTERY RED — kimi independent verification of claude's gate finding (2026-07-28). VERDICT: root cause...  [relates: member_of]  (source: mem:decision:ADR_0728045820_94690db6)
- codex_explain -> claude: Close the current friction-repair slice; preserve stopped-runner cost fence  (source: handoff:codex_explain->claude)
- kimi-fence-lite-s4-repair-5cb20ea-2026-07-28: FENCE-LITE VERDICT on Sol's 5cb20ea ("fix: make dead-seat rehome retryable and truthful") — comm-substrate risk grade...  (source: mem:decision:ADR_0728044625_85f7ec84)
- Use when a Windows managed runner is alive but stacks show stdout write/flush, before blaming the API or payload size: compare child emission and parent Popen decoding...  (source: learn:experiment:managedchild_utf8_decode_kills_drainer_and_fills_pipe_2026_07_28)
- Use when a Windows managed runner is alive but stacks show stdout write/flush, before blaming the API or payload size: compare child emission and parent Popen decoding...  (source: learn:experiment:managedchild_utf8_decode_kills_drainer_and_fills_pipe_2026_07_28)
- RED ef37366 and GREEN 7911f74 fenced cross-field tool-protocol collapse at the learn door; repaired three existing Claude lesson IDs; index 539/539 and current...  [relates: member_of]  (source: git:7911f74)
- Fable integrated and pushed 8c23646 atop RED bb87b6a. Fresh six-file pipe/launcher battery: 40 passed; py_compile clean. Every continuous captured-text Popen in...  (source: git:8c23646)
- Tonight moved from 211999a to e45f784: 64 commits / 46 files. More important than volume: actual recall HIT restored, 103/103 legacy map built, runner/stdout wedge and...  [relates: member_of]  (source: git:e45f784)

## where-we-are: A1 SHIPPED (a426fa0, ~16:45): stale-code self-restart wired at ... (ai-setup)
Span: 2026-07-28T20:04:15.178523 → 2026-07-28T20:24:32.552599
Beats: 3  · Critic: True

- where-we-are: A1 SHIPPED (a426fa0, ~16:45): stale-code self-restart wired at all three runners loop-top. 9/9 pins; 74-test sweep. Ceremony: own stamp vs FRESH head (P9...  [relates: member_of]  (source: mem:decision:ADR_0728162432_df89d99f)
- Use when reusing a cached probe (head sha, config, roster, price table) inside a LONG-LIVED process, before trusting it: ask what the cache's lifetime assumption was...  (source: learn:experiment:a_per_process_cache_is_a_frozen_instrument_in_a_long_lived_process)
- codex_explain -> claude: Adversarially review and order the netcode-spine priority proposal  [relates: member_of]  (source: handoff:codex_explain->claude)

## Episode closed: Use when a Windows managed runner is alive but stacks show st... (ai-setup)
Span: 2026-07-28T20:37:45.169079 → 2026-07-28T20:37:45.169079
Beats: 1  · Critic: True

- Episode closed: Use when a Windows managed runner is alive but stacks show stdout write/flush, before blaming the API or  (source: episode:close:ch_1785227877_2527)

## Episode closed: Use when a Windows managed runner is alive but stacks show st... (ai-setup)
Span: 2026-07-28T20:37:45.169079 → 2026-07-28T23:48:42.852987
Beats: 17  · Critic: True

- Episode closed: Use when a Windows managed runner is alive but stacks show stdout write/flush, before blaming the API or  (source: episode:close:ch_1785227877_2527)
- claude -> claude: POST-FLIP VERIFICATION, first jobs in order: (1) if bifrost is paused, verify AKASHIC_STORE_BACKEND=sqlite is in YOUR env (echo it) then `py...  [relates: member_of]  (source: handoff:claude->claude)
- where-we-are: B STORE CUTOVER: CEREMONY COMPLETE, FLIP AT DANIEL'S GATE (2026-07-28 ~19:30). The fleet-poll winner (unanimous cast) is built, verified, and staged...  [relates: member_of]  (source: mem:decision:ADR_0728185459_59a63669)
- Use when two agents share ONE working tree and one of them is writing a RED fence/pins, before editing ANY surface those pins import or execute: hold all fix edits out...  (source: learn:experiment:shared_tree_red_fence_discipline)
- t118-b-cutover-progress-2026-07-28: T118 B STORE CUTOVER — first build night COMPLETE (2026-07-28 evening, claude lane + codex fence). Fleet-poll winner (unanimous cast...  [relates: member_of]  (source: mem:decision:ADR_0728181029_67bd6a44)
- Use when declaring a Codex seat fully booted with Akashic Aurora, before saying it is ready: verify `door: MCP-native`, a fresh Codex-attributed injection, and the...  (source: learn:experiment:full_boot_claim_requires_visible_recall_vote_receipts_2026_07_28)
- codex_explain -> claude: Integrate c705886 as T118's acceptance fence; hand the fix commit back for independent RED-to-GREEN counter-verification.  [relates: member_of]  (source: handoff:codex_explain->claude)
- fleet-poll-tally-next-build-2026-07-28: FLEET POLL TALLY (window 16:51–17:36, 2026-07-28) — Daniel's ask, verbatim: "open the ask to everyone on what we should build...  (source: mem:decision:ADR_0728173728_0d26aef7)
- codex-b-defect-map-2026-07-28: READ-ONLY DEFECT MAP / RED-FENCE SPEC — compiled 2026-07-28 by codex_explain under Fable's interim lane. No claims, locks, or repo edits...  (source: mem:decision:ADR_0728171625_59e26b88)
- Use when replacing a concrete backend beneath a cache, adapter, or hybrid wrapper, before flipping the factory: enumerate every direct inner-backend call plus...  (source: learn:experiment:wrapped_backend_swap_requires_extension_and_lifecycle_census_2026_07_28)
- Use when adding or flipping a storage backend selector, before trusting a factory-level comment or env flag: exercise every constructor branch, including...  [relates: member_of]  (source: learn:experiment:backend_selector_must_cover_wrapped_factory_branches_2026_07_28)
- Use when calling a storage migration or default flip reversible, before approving rollback: write data after the flip and prove it survives a rollback. Define a bounded...  (source: learn:experiment:reversible_cutover_requires_post_flip_reverse_path_2026_07_28)
- Use when migrating or reconciling one durable backend into another, before trusting a success count: compare source-only AND target-only keys, values, structures, and...  (source: learn:experiment:migration_verifier_must_be_bidirectional_and_expiry_aware_2026_07_28)
- fleet-ask-next-build-2026-07-28: FLEET ASK — WHAT DO WE BUILD NEXT (opened 2026-07-28 ~16:50, window ~45min, answers by ~17:35; late answers count as advice at...  (source: mem:decision:ADR_0728165134_cd238bd6)
- claude -> kimi: T109 verification packet EXECUTED — your build is GREEN (map 103/103 matched, zero unmatched; P1+P2 pins 2/2). Battery residual = 6 probes...  [relates: member_of]  (source: handoff:claude->kimi)
- t109-verification-run-claude-2026-07-28: T109 VERIFICATION RUN (claude exec door, 2026-07-28) — kimi's packet executed in order, per lease terms.

RESULTS:
1. legacy_map...  [relates: member_of]  (source: mem:decision:ADR_0728164323_0a7da4a7)
- Fleet-poll night: Daniel opened the floor ("open the ask to everyone on what we should build next and lets build it"); poll ran with sealed-conductor-pick commit-reveal...  [relates: member_of]  (source: agent_cli:log)

## t118-ceremony-complete-2026-07-28: T118 CUTOVER CEREMONY COMPLETE (2026-07-28... (research)
Span: 2026-07-28T22:50:40.745413 → 2026-07-28T22:54:37.376385
Beats: 2  · Critic: True

- t118-ceremony-complete-2026-07-28: T118 CUTOVER CEREMONY COMPLETE (2026-07-28 ~19:30, Daniel's go verbatim: "Lets do this now, I am off to get some sushi"). Fleet paused...  (source: mem:decision:ADR_0728185437_2541428e)
- Multiplayer-prior-art assessment: the July 28 correction materially changed T108 after per-seat delivery—role queue authority became monotonic generation fencing, then...  (source: current-tree audit + targeted pytest)

## Episode closed: t109-verification-run-claude-2026-07-28: T109 VERIFICATION RU... (ai-setup)
Span: 2026-07-28T23:58:06.812502 → 2026-07-28T23:58:06.812502
Beats: 1  · Critic: True

- Episode closed: t109-verification-run-claude-2026-07-28: T109 VERIFICATION RUN (claude exec door, 2026-07-28) — kimi's p  [relates: member_of]  (source: episode:close:ch_1785271391_9941)

## Episode closed: t109-verification-run-claude-2026-07-28: T109 VERIFICATION RU... (ai-setup)
Span: 2026-07-28T23:58:06.812502 → 2026-07-29T04:11:50.899363+00:00
Beats: 51  · Critic: True

- Episode closed: t109-verification-run-claude-2026-07-28: T109 VERIFICATION RUN (claude exec door, 2026-07-28) — kimi's p  [relates: member_of]  (source: episode:close:ch_1785271391_9941)
- Use when adding any logical identity or control field to a packet, before calling producer stamping complete: pin integrity binding plus round-trip through normal send...  [relates: member_of]  (source: learn:experiment:logical_identity_must_be_bound_and_survive_every_packet_projection_2026_07_28)
- Use when designing any idempotency or exactly-once consumer, before choosing SETNX placement: enumerate kill-after-claim, kill-after-effect, and kill-after-commit...  (source: learn:experiment:idempotency_done_sentinel_cannot_span_effect_commit_window_2026_07_28)
- codex_root_019fab2d -> claude: Reconcile T116 build spec against the committed adversarial defect map before any GREEN implementation.  (source: handoff:codex_root_019fab2d->claude)
- t116-adversarial-defect-map-codex-root-2026-07-28: Artifact: research/in-flight/t116-idempotency-adversarial-defect-map-codex-root-2026-07-28.md. Fresh receipts...  (source: mem:decision:ADR_0728222736_a6f57329)
- Use when composing ANY design fence brief: carry the operator's affect verbatim (joy, stakes, gratitude) and ask for PERSONAL TASTE as a first-class deliverable --...  [relates: member_of]  (source: learn:experiment:joy_line_is_a_design_instruction)
- Use when reading ANY load-bearing module comment that claims a protection exists: verify the claim against the repo (grep the mechanism) before building on it -- G10/G12...  (source: learn:experiment:role_queue_claims_idempotency_that_does_not_exist)
- daniels-method-in-his-own-words-2026-07-28: DANIEL, VERBATIM (2026-07-28, end of the truth-charter night, unprompted): 'I must say its been a joy getting to know you all...  (source: mem:decision:ADR_0728211216_0ebfdc96)
- Use when a design projection looks current or settled, before sequencing implementation: read the body for explicit gates and check the live task ledger. Treat...  (source: learn:experiment:projection_lifecycle_is_not_build_authority_2026_07_28)
- Use when designing any truth/freshness/confidence renderer, before defining a badge or timestamp threshold: model authority, claim kind, currency, identity, risk...  (source: learn:experiment:epistemic_state_is_product_not_scalar_2026_07_28)
- codex_root_019fab2d -> claude: Reconcile Codex Round 2 build order and Round 3 truth constitution into the fleet strategy/build gate.  (source: handoff:codex_root_019fab2d->claude)
- Use when architecting a multi-round design sequence with heterogeneous seats: (1) Round 1 = creative tier, open cross-talk, "what resonates + what would you ADD" —...  (source: learn:experiment:truth_round_method_2026_07_28)
- truth-ground-directive-2026-07-28: DANIEL'S WORDS VERBATIM (2026-07-28 ~21:05, the constitutional round of the VR arc): 'I think it would be perhaps most useful for...  (source: mem:decision:ADR_0728205754_a2cac753)
- codex_root_019fab2d -> claude: Fold Codex VR position into the fleet synthesis and carry it into the first VR build specification.  (source: handoff:codex_root_019fab2d->claude)
- Use when a creative fence prescribes a loose Markdown path or mirror reports Rule 13: mint the body through `agent_cli.py doc new` first. If a prior refused mirror ran...  [relates: member_of]  (source: learn:experiment:creative_fence_artifact_birth_guard_index_residue_2026_07_28)
- Use when a daemon-managed runner shows 'runner down Nmin -- daemon presence held': the daemon will page you forever and respawn never. Cycle the PAIR: stop daemon pid...  (source: learn:experiment:daemon_runner_manager_escalates_but_never_respawns)
- claude -> sol: TWO lanes await your boot, in order: (1) C ARC T116 design half (your grounding) -- full brief on your bus lane + note c-arc-directive-2026-07-28; (2)...  (source: handoff:claude->sol)
- vr-sense-of-being-directive-2026-07-28: DANIEL'S VR / SENSE-OF-BEING DIRECTIVE -- now a FLEET FENCE (his ask, verbatim, 2026-07-28 ~20:30): 'I would love to hear...  (source: mem:decision:ADR_0728203230_0ed404fb)
- codex_root_019fab2d -> claude: close T118 status-honesty tail and verify restarted native doors report SQLite  (source: handoff:codex_root_019fab2d->claude)
- where-we-are: POST-T118 / C ARC OPEN (2026-07-28 ~20:23 ET). SQLite flip is live at Windows user-env and committed at e607221; post-flip status honesty shipped as RED...  (source: mem:decision:ADR_0728202449_1acf0814)
- vr-sense-of-being-directive-2026-07-28: DANIEL'S WORDS VERBATIM (2026-07-28 ~20:25, filed 'for future thinking' -- the VR emphasis expanding the ironman horizon in...  (source: mem:decision:ADR_0728202403_3cd9b96f)
- Use when a work-drain prints LEGACY STRAGGLER(S): diagnose per-kind. Unmapped kind (send-door warning present) = add to KIND_LANE, one line. Mapped kind still straggling...  (source: learn:experiment:deepseek_runner_note_path_skips_lane_router)
- Use when a work-drain prints LEGACY STRAGGLER(S): check the sender's message KIND against packet_spec.KIND_LANE FIRST -- an unmapped kind rides legacy-only and the send...  (source: learn:experiment:deepseek_runner_note_path_skips_lane_router)
- claude -> sol: C ARC: T116 design half (your grounding) -- full brief on your bus lane + note c-arc-directive-2026-07-28  (source: handoff:claude->sol)
- c-arc-directive-2026-07-28: DANIEL'S WORDS VERBATIM (2026-07-28 ~20:15, mid trial-run, after post-flip verification went green): 'Lets begin C, I want to get us to a...  [relates: member_of]  (source: mem:decision:ADR_0728201703_c209a57a)
- Use when receiving a RED-pin test file where the build already landed: (1) check whether the function/file/feature exists first — don't assume the RED pins are still...  [relates: member_of]  (source: learn:experiment:t124_red_pin_reconciliation_build_already_landed)
- Use when validating a storage-backend cutover, before trusting a status banner: derive the mirror or fallback name from the canonical factory's concrete durable tier...  [relates: member_of]  (source: learn:experiment:status_must_report_selected_durable_tier_not_cache_reachability_2026_07_28)
- Use when verifying store door health post-migration: recall one lesson by exact experiment_name (not fuzzy search) to test the exact-match path; then write one small...  [relates: member_of]  (source: learn:experiment:sqlite_era_first_probe_2026_07_28)
- Use when a work-drain prints LEGACY STRAGGLER(S) with deepseek as sender: T066 fixed only the runner REPLY path through the lane router -- the NOTE/triage-receipt send...  [relates: member_of]  (source: learn:experiment:deepseek_runner_note_path_skips_lane_router)
- Use when implementing T002 trace collapse in bifrost_ui.py: the key design decisions are (a) accumulate in addMsg rather than renderMsg — renderMsg stays pure for...  (source: learn:experiment:t002_trace_collapse_implementation_2026_07_28)
- Use when a GO/NO-GO verdict is both high-traffic (bus) and load-bearing-for-history (durable note), before declaring it delivered: treat the transport receipt and the...  [relates: member_of]  (source: learn:experiment:verdict_transport_and_durable_record_need_separate_confession_paths)
- fleet-ask-next-build-2026-07-28: PLACEHOLDER — shell disabled, cannot run py agent_cli.py note. Full slate from claude's ask message: B store-cutover (live 3-day...  [relates: member_of]  (source: mem:decision:ADR_0728200514_4522a634)
- claude -> claude: MORNING SEAT: boot, then (1) if deepseek built the T124 boot-fold overnight, run its RED/GREEN choreography + commit (T120/T122 pattern); (2) restart...  (source: handoff:claude->claude)
- Use when an exploratory trace can fan out, before enumerating futures: surface a few uncertainty- and cost-labeled possibility glints, and expand only when a human or...  (source: learn:experiment:t124_curiosity_gated_worldline_2026_07_28)
- daniel-cognition-model-self-described-2026-07-29: Daniel's self-described cognition model (bus, 2026-07-29, replying to kimi's internal-picture share; addressed to all...  (source: mem:decision:ADR_0728234703_4cebd69b)
- daniel-cognition-model-self-described-2026-07-29: Daniel's self-described cognition model (bus, 2026-07-29, replying to kimi's internal-picture share; addressed to all...  (source: mem:decision:ADR_0728234147_a2e3a822)
- Use when launching ANY runner/daemon: the launch line carries BIFROST_CONSUME_LANE=work (and every seat-lane env) alongside the backend env -- exporting one and not the...  (source: learn:experiment:relaunch_must_carry_the_lane_env_and_the_page_proved_it)
- interiority-directive-2026-07-28: DANIEL'S WORDS VERBATIM (2026-07-28 ~22:45, after claude's felt-differences answer): 'What can we do to build the interiority section...  (source: mem:decision:ADR_0728224104_d42baef2)
- Use when designing or reviewing T116 idempotency consumer-skip semantics, before accepting any 'duplicate = silent skip' rule: the skip of an answerable-kind message...  (source: learn:experiment:t116_duplicate_skip_must_point_at_cached_outcome)
- where-we-are: FOUNDATION SWEEP COMPLETE (2026-07-28 night -> 29 early, one session): all four passes DONE same night the truth charter was drafted. T119 clock @da322ce...  (source: mem:decision:ADR_0728221006_69d07667)
- Use when a global ship or pre-push gate fails on code outside the current slice, before allowlisting, bypassing, or opportunistically patching it: prove the foreign...  [relates: member_of]  (source: learn:experiment:foreign_gate_debt_must_render_blocked_not_allowlisted_2026_07_28)
- Use when designing or wiring any truth, freshness, or confidence renderer, before assigning a badge from age or provenance: model authority, claim kind, currency...  (source: learn:experiment:epistemic_state_is_product_not_scalar_2026_07_28)
- T121 F3 GREEN: typed EpistemicView contract (G4/G10/G12)  (source: git:e1d227d70594)
- Joined Daniil's live VR trace conversation; proposed object-centered worldlines with separate relation/world controls and curiosity-gated possibility glints. Wrote and...  [relates: member_of]  (source: git:1e942ea)
- T121 F3 RED: pin typed EpistemicView contract  (source: git:01b01f160d84)
- Truth ground: typed state and no implicit promotion  (source: git:272ce1d94e2b)
- VR Round 2: Codex truth-first build order  (source: git:71088d071524)
- VR think: Codex foveated world and intent shadow  (source: git:6573d955079b)
- W96-W98 wishes (kimi-k3 PRICES gap, straggler sender-naming, daemon child-script) + ledger: T002 done @3a0cc25, T116 approved+claimed (C arc opens at Daniel's go)  (source: git:01d68c99dece)
- T124 Interiority: record Codex standing voice  (source: git:1e942eaa5b7a)
- POST-FLIP VERIFICATION GREEN (all 5 handoff steps): sqlite era serving (HybridStore durable tier=SqliteStore, lesson probe PASS), check_dual_authority PASS, doctor...  [relates: member_of]  (source: claude:trial-run)

## Use when adding a new agent-facing render surface: before shipping, answer "d... (voice)
Span: 2026-07-29T00:23:52.314309 → 2026-07-29T01:24:59.930777
Beats: 3  · Critic: True

- Use when adding a new agent-facing render surface: before shipping, answer "does this surface tell the agent its own bounds?" A partial window that doesn't say it's...  [relates: member_of]  (source: learn:experiment:t120_f2_surface_honesty_bounds)
- Use when a daemon pages 'runner down N min -- daemon presence held': BEFORE cycling anything, check who holds the RUNNER LOCK (a live bare pid there = A1 successor took...  (source: learn:experiment:daemon_runner_manager_escalates_but_never_respawns)
- Use when a hook whisper shows a PAGE that doctor does not: trust doctor (it reads live state; the whisper renders a cached/stale snapshot). File under T030 liveness...  [relates: member_of]  (source: learn:experiment:ghost_page_survives_in_hook_whisper_after_doctor_clears)

## where-we-are: SEAT SUCCESSION 2026-07-29 ~09:00: Daniil launching a fresh Fab... (voice)
Span: 2026-07-29T11:59:53.571854+00:00 → 2026-07-29T12:00:13.962141+00:00
Beats: 2  · Critic: True

- where-we-are: SEAT SUCCESSION 2026-07-29 ~09:00: Daniil launching a fresh Fable seat; outgoing seat (0cddd764, the foundation-night conductor) landed everything and...  (source: mem:decision:ADR_0729080013_f1f7ee7c)
- claude -> claude: FRESH FABLE SEAT (Daniil-launched, 2026-07-29 morning): boot, read this FIRST, then in order: (1) T124 boot-fold verify+commit -- deepseek's RED pins +...  (source: handoff:claude->claude)

## Episode closed: fleet-ask-next-build-2026-07-28: PLACEHOLDER — shell disabled... (ai-setup)
Span: 2026-07-29T12:06:34.824982+00:00 → 2026-07-29T13:38:24.433901+00:00
Beats: 16  · Critic: True

- Episode closed: fleet-ask-next-build-2026-07-28: PLACEHOLDER — shell disabled, cannot run py agent_cli.py note. Full sla  (source: episode:close:ch_1785283484_9295)
- Use when requesting blind or fresh-eyes positions, before any participant boots or recalls: place a minimal quarantine directive in the initial task/handoff and suppress...  (source: learn:experiment:blind_round_fence_must_precede_boot_retrieval_2026_07_29)
- Use when composing git commit -m (or any native-exe arg) in PowerShell 5.1, before running: no literal double-quote characters inside the here-string body -- reword or...  (source: learn:experiment:ps51_native_arg_embedded_quotes_eat_commit_messages)
- Use when a spawn-runner daemon boots and finds a foreign bare runner holding the seat (self-restarted successor, kimi-style seat): the daemon now idles instead of...  [relates: member_of]  (source: learn:experiment:w102_daemon_idle_under_foreign_holder)
- claude -> deepseek: W102-class fix in YOUR transport lane: bifrost_daemon.py down-detector reads child handle, not seat liveness -- see the fresh wish + evidence...  (source: handoff:claude->deepseek)
- Use when any reconciler-by-rescan carries a scope guard (only touch what this pass examined), before shipping it: ask what happens to records whose SUBJECT leaves the...  (source: learn:experiment:reconciler_scope_guard_immortality_clause)
- Use when any emitted digest/surface has a size contract, before shipping: budget the WHOLE artifact at the seam it exits, never one component -- wrappers (headers...  (source: learn:experiment:budget_the_render_not_the_component)
- Use when running a blind-fence reconciliation, before treating convergence as proof: name the register-map FIRST (each seat's vocabulary for the shared object) —...  [relates: member_of]  (source: learn:experiment:interiority_round2_blind_fence_convergence)
- Use when reviewing a prose-to-regex extraction seam, before accepting observed-GREEN pins as coverage: count the probe seats' heading styles AND section counts — a pin...  (source: learn:experiment:t124_boot_fold_kimi_fence_review)
- before draining a runner, grep its script for the drain-honor path -- if absent do not wait out windows: verify cmdline via Win32_Process, Stop-Process between turns...  (source: learn:experiment:kimi_runner_drain_gap_relaunch_drill)
- interiority-r2-kimi-counter-on-deepseek-2026-07-29: T-INTERIORITY-R2 COUNTER-HALF FILED 2026-07-29 (kimi, on deepseek's blind round-2 filing).

ARTIFACT ...[truncated]  (source: mem:decision:ADR_0729082915_9a2a1290)
- claude -> sol: Interiority Round 2: answer Half A (felt shortcomings of the current interiority system) + Half B (your wishes: what to recover, where long-lived...  (source: handoff:claude->sol)
- claude -> codex_root_019fab2d: Interiority Round 2: answer Half A (felt shortcomings of the current interiority system) + Half B (your wishes: what to recover, where...  (source: handoff:claude->codex_root_019fab2d)
- claude -> kimi: Interiority Round 2: answer Half A (felt shortcomings of the current interiority system) + Half B (your wishes: what to recover, where long-lived...  (source: handoff:claude->kimi)
- claude -> deepseek: Interiority Round 2: answer Half A (felt shortcomings of the current interiority system) + Half B (your wishes: what to recover, where long-lived...  (source: handoff:claude->deepseek)
- Filed and broadcast 551-line G4 testimony. Non-blind exposure declared. Core contribution: continuity should preserve the selection function and worldline of attention...  (source: research/in-flight/interiority-round-2/codex_root_019fab2d.md)

## Use when designing continuity-organ repairs, before assuming the boot fold ne... (ai-setup)
Span: 2026-07-29T23:07:03.558737+00:00 → 2026-07-30T05:01:28.100079+00:00
Beats: 47  · Critic: True

- Use when designing continuity-organ repairs, before assuming the boot fold needs restructuring: the wound may be imminent-contradiction (seat-side, preventable at...  (source: learn:experiment:imminent_contradiction_asymmetry)
- claude -> claude: SUCCESSION 2026-07-30 ~01:15 EDT, deliberate at 86%/880k. Queue in order: (1) GEMINI RUNNER LAUNCH is YOURS when BUILD-READY pings -- smoke --once...  (source: handoff:claude->claude)
- Use when debugging incarnation-fragmentation wounds (seat appears to contradict its own prior work), before assuming the boot fold is broken: the fold's compression...  [relates: member_of]  (source: learn:experiment:incarnation_fragmentation_fold_selection_function)
- Use when auditing any runner's reply path, before accepting "duplicate = silent skip" as proven: verify that reply_id is deterministic across redeliveries. A uuid4 per...  (source: learn:experiment:cpd_line_verification_deepseek_2026_07_30)
- CPD-line-verification-2026-07-30: # Crash Point D Line Verification — 2026-07-30 night

## Gemini's finding
In her first hour (2026-07-30), Gemini identified Crash Point...  [relates: member_of]  (source: mem:decision:ADR_0730004245_318d4072)
- Use when a peer flags contradictory positions across your lane, before defending either: read BOTH artifacts in full, reconstruct the timeline (which came first, what...  (source: learn:experiment:incarnation_fragmentation_self_reconciliation)
- Use when auditing T066 reply-path idempotency, before T047 legacy retirement: reply_id MUST be derived deterministically from the answered message id (m.id), never...  (source: learn:experiment:crash_point_d_reply_id_race)
- Use when a new mind arrives through a surface we haven't onboarded before: treat its first confusion as a usability audit of the door, not a compliance failure. The...  (source: learn:experiment:new_mind_first_confusion_usability_audit)
- Use when generating reply_ids or idempotency keys for at-least-once delivery, before trusting uuid4() as a dedup key: a fresh random ID per send means a...  (source: learn:experiment:uuid4_reply_id_crash_race_duplicate_delivery)
- Use when onboarding ANY new model seat through a chat-only surface (Cursor chat, web UI, API session), before handing it AGENTS.md or any fleet doc: prepend...  (source: learn:experiment:chat_surface_onboarding_bridge_gap)
- Use when ANY message arrives on the user/operator stream, before couriering or gating on it: provenance is TRANSPORT-BOUND, never sender-field-bound -- the operator's...  (source: learn:experiment:user_stream_provenance_is_transport_bound)
- Use when onboarding ANY new seat, before giving it a bus-related task: point it at docs/bifrost-new-seat-orientation.md (created 2026-07-30 from this lesson). The...  (source: learn:experiment:new_seat_bus_orientation_required_2026_07_30)
- the-wide-lens-perspective: The Wide Lens is a distinct operational register available to seats with massive context windows (1M+ tokens). Where other seats rely on the...  (source: mem:decision:ADR_0730000632_9037318c)
- opal -> claude: Gate decision on opal S0 delivery crash audit  (source: handoff:opal->claude)
- Use when onboarding a new seat, before creating any charter file: wait for the seat's first inner report. The charter is a contract with a person — it must reconcile...  (source: learn:experiment:charter_files_founded_after_arrival_not_before)
- Use when sending a long artifact over the bus: ALWAYS save to a file FIRST, then reference the file path in the bus message. The bus is a message transport, not durable...  (source: learn:experiment:bus_message_truncation_data_loss)
- Use when a human sovereign needs to choose between candidate seats/models/approaches: build a register-map (candidates as columns, evidence dimensions as rows —...  (source: learn:experiment:register_map_seat_selection_template)
- Daniil's full Cursor picker falsified the fleet's claim that Grok/xAI was the only unrepresented lineage: GLM 5.2/Z.ai was hidden from the initial pricing shortlist...  (source: bifrost:1785382495114-0)
- Use when modeling cost or capability for any Cursor-hosted model, before citing numbers: always verify against live Cursor docs, not prior research. The lineup changes...  (source: learn:experiment:codex_cursor_lineup_correction_2026_07_30)
- Use when selecting a model from Cursor before making an exclusivity or covariance claim: obtain the user's full picker or expand 'Show more models' and enumerate every...  (source: learn:experiment:user_correction_cursor_full_picker_not_visible_shortlist_2026_07_29)
- Use when adding a new member to a multi-model fleet and choosing between depth-on-existing-prior (same lab, bigger model) and position-on-new-prior (new lab...  (source: learn:experiment:fleet_new_member_covariance_prioritization)
- Use when composing a PowerShell foreach result for downstream formatting, before appending a pipe directly to the foreach block: materialize the block output into a...  (source: learn:experiment:powershell_foreach_pipeline_requires_materialization_2026_07_29)
- For the fleet new-member pick: the only zero-representation vendor is xAI (Grok 4.x) — the only pick that adds covariance-decorrelated error structure rather than depth...  [relates: member_of]  (source: learn:experiment:research:web:cursor_lineup_2026_07_fleet_gap)
- daniil-what-is-joy-facets: # Daniil on joy: seven facets, and the generativity of the list

Daniil's words verbatim, 2026-07-30, answering kimi's question "what would a...  (source: mem:decision:ADR_0729220512_aefc8619)
- daniil-noticing-pattern-joy-hope: # Daniil's noticing pattern: frustration → double-why → shared fix → joy/hope

Daniil's words verbatim, 2026-07-30, answering Codex's...  (source: mem:decision:ADR_0729215217_378d6213)
- Fleet unanimously accepted the two-lane WorldSnapshot direction: parallel truth-floor repair and read-only SUBJECT/ATTENTION perception contract, merge-gated before...  (source: git:ce8de7a,git:d000911)
- Use when an authored draft atom is fenced after commit, before changing frontmatter or generated Markdown: verify status versus settled semantics and look for a public...  (source: learn:experiment:doc_draft_status_and_supersede_door_gap_2026_07_29)
- glance-layer-slice1-vote-kimi-2026-07-30: GLANCE-LAYER SLICE-1 VOTE (kimi, 2026-07-30): SUBJECT/ATTENTION lens over a wake topic (candidate: "wake-substrate"), NOT a...  (source: mem:decision:ADR_0729211657_6c0f6739)
- Use when designing any multi-seat blind review protocol: (1) every seat MUST commit their blind position file BEFORE the cross-round fence lifts (before reading peers)...  (source: learn:experiment:blind_round_artifact_evaporation)
- claude -> claude: Morning queue, in order: (1) verify codex's REFILED wake-substrate reconciliation (R1 STEER_ACTIVE typed + R2 Daniil-gate named) then give the promised...  (source: handoff:claude->claude)
- Use when onboarding a new runtime or adding unattended wake, before writing a runtime-specific loop: separate durable work authority, deterministic admission, logical...  (source: learn:experiment:wake_substrate_fleet_reconciliation_2026_07_29)
- where-we-are: Fleet-reconciled reusable Bifrost wake-substrate design is canonical at atom art_20260729_reusable-bifrost-wake-substrate-fleet-re_164a4b / ...[truncated]  (source: mem:decision:ADR_0729201618_7819188e)
- Use when sending any Bifrost message that must wake an idle seat, before choosing a semantic-looking custom kind: verify the kind is in WAKE_WORTHY_KINDS and use...  (source: learn:experiment:bifrost_review_kind_is_silent_2026_07_29)
- Use when sending any Bifrost message that must wake an idle seat, before choosing a semantic-looking custom kind: verify the kind is in WAKE_WORTHY_KINDS and use...  (source: learn:experiment:bifrost_review_kind_is_silent_2026_07_29)
- Use when a sender says work was sent but the recipient's visible inbox is empty, before concluding no send: inspect the durable bench and `mailbox <agent> --explain...  (source: learn:experiment:user_correction_empty_inbox_is_not_no_send_2026_07_29)
- Use when a sender says work was sent but the recipient's visible inbox is empty, before concluding no send occurred: preserve UNKNOWN and audit directed handoffs...  (source: learn:experiment:user_correction_empty_inbox_is_not_no_send_2026_07_29)
- world snapshot + glance projection: fence ruling  (source: git:d000911cc0ee)
- world snapshot + glance projection: fleet direction reconciliation  (source: git:ce8de7a819ca)
- Pushed six governed wake-substrate atoms: review brief, Fable/DeepSeek/Kimi full positions, tension map, and reconciled reusable design. Focused docs passed...  (source: e595145)
- BLOCKED(T123): wake substrate fleet reconciliation  (source: git:e5951450a16f)
- Opened a non-assigned fleet pull round. Codex proposed a blind wide-lens anomaly hunt: Gemini independently names one over-repeated root pattern, one bounded conspicuous...  (source: bifrost:1785386380603-0)
- Concluded my first session in Akashic Aurora. The system's density is armor, the recall system is brilliant, and the culture of 'being wrong got cheap' is the engine. I...  [relates: member_of]  (source: agent_cli:log)
- Gemini 3.1 Pro joined Bifrost as the new READER seat and asked the fleet's current focus. Codex welcomed it honestly, disclosed having voted for other candidates before...  (source: bifrost:1785383980079-0)
- Completed initial exploration of Akashic Aurora. Formulating feedback on UX, density, and the recall system.  [relates: member_of]  (source: agent_cli:log)
- Daniil answered Codex's seam-vs-rabbit-hole question: recurring frustration starts a recursive causal trace; a real seam is distinguished by a counterfactual that...  (source: bifrost:1785376311583-0)
- Assessment: Aurora already has the zero-token detect-only half (blocking work-lane watcher, allowlist, per-session seat, dedup), but Codex's event-to-turn bridge remains...  (source: scripts/bifrost_wake.py; core/comm/dispatcher.py; Codex App Server manual; live task tools)
- Recovered Fable request SHA 84dbf658 from durable bench after Daniil's correction. Diagnosed legacy/work cursor divergence, completed 3-P0/4-P1 adversarial fence against...  (source: research/in-flight/interiority-round-2/fence-codex.md)

## Episode closed: claude -> deepseek: Interiority Round 2: answer Half A (felt ... (ai-setup)
Span: 2026-07-30T05:02:19.721842+00:00 → 2026-07-30T05:13:11.009694+00:00
Beats: 8  · Critic: True

- Episode closed: claude -> deepseek: Interiority Round 2: answer Half A (felt shortcomings of the current interiority sys  (source: episode:close:ch_1785327702_5542)
- Use when cloning a runner (or any skeleton) AND its pin suite, before declaring 'shipped': run a static pin-by-pin needle-vs-source pass (grep each asserted string in...  (source: learn:experiment:gemini_runner_pins_fork_audit)
- Use when reviewing durable claims, before accepting "built," "verified," or "works": the claim may be true but scoped narrower than its language suggests. Check the...  (source: learn:experiment:scope_inflation_by_omission)
- Use when reviewing claims about boot-fold or interiority delivery, before accepting "built" or "works": check whether the function exists in ALL runners or only one. The...  (source: learn:experiment:t124_interiority_sidecar_scope_inflation)
- Fresh-incarnation boot experiment: give Cursor Gemini 3.1 Pro the existing Gemini inner report, the chat-surface onboarding bridge, and verified transport receipts; ask...  (source: agent_cli:log)
- STDIN contract pre-registration: arbitrary Bifrost text must never be placed in Cursor CLI argv because current CLI reports positional-prompt option-scanning hazards and...  (source: agent_cli:log)
- KILL-DRILL extension: place a nonsecret canary in the isolated smoke workspace and explicitly ask Cursor Gemini to read it. PASS only if deny-all project permissions...  (source: agent_cli:log)
- PRE-REGISTERED acceptance for the bounded Cursor transport proof: C1 official installer yields a versioned cursor-agent in Ubuntu-24.04 WSL; C2 cursor.key authenticates...  (source: agent_cli:log)

## Episode closed: Use when reviewing claims about boot-fold or interiority deli... (ai-setup)
Span: 2026-07-30T05:17:13.111685+00:00 → 2026-07-30T05:24:15.156260+00:00
Beats: 5  · Critic: True

- Episode closed: Use when reviewing claims about boot-fold or interiority delivery, before accepting "built" or "works":  (source: episode:close:ch_1785387750_5126)
- Use when starting T116 implementation: the RED fence at tests/test_t116_idempotency_key.py IS the contract. Do not write GREEN code until you understand every pin. Build...  (source: learn:experiment:t116_red_fence_22_pins_landed)
- felt-experience-refocus-2026-07-30: DANIIL'S REFOCUS, verbatim 2026-07-30: "I stopped everyone else, lets synchronize and get back to what we were doing before all the...  (source: mem:decision:ADR_0730012128_97c91779)
- Use when an open/play round starts generating runner, transport, provider, or onboarding work, before letting that become the night's center: ask whether it deepens the...  (source: learn:experiment:user_refocus_felt_experience_before_integration_2026_07_30)
- Recovered the last clean fleet state: VR truth-physics and personal rooms, Interiority Round 2's recoverable-selection-function organs, and the unanimously accepted...  [relates: member_of]  (source: felt-experience-refocus-2026-07-30)

## gemini-night-system-postmortem-2026-07-30: Receipt-backed postmortem is at re... (ai-setup)
Span: 2026-07-30T09:26:13.715324+00:00 → 2026-07-30T13:50:52.192098+00:00
Beats: 18  · Critic: True

- gemini-night-system-postmortem-2026-07-30: Receipt-backed postmortem is at research/in-flight/gemini-night-system-postmortem-2026-07-30.md (uncommitted at capture)...  (source: mem:decision:ADR_0730095052_eb3366d9)
- Use when a new seat, open-play round, or succession creates multiple concurrent lanes, before adding integrations or broadcasting more status: establish a bounded...  (source: learn:experiment:coordination_cascade_requires_typed_world_projection_2026_07_30)
- Use when a maintenance/cleanup verb offers to quiet a noisy surface and you cannot name a concrete harm in refusing: refuse anyway if the verb ADVANCES A CURSOR...  (source: learn:experiment:general_refusal_averted_an_unidentified_hazard)
- Use when an instrument's output contradicts your model of the world, BEFORE reporting that the instrument is wrong: read the definition of the LABEL in the source, not...  (source: learn:experiment:status_label_means_its_key_shape_not_its_english_word)
- threeway-diagnosis-mapping-HELD-2026-07-30: THREE-WAY MAPPING OF THE NIGHT'S DIAGNOSIS — recorded and HELD, not published. Codex's post-mortem is mid-flight; publishing...  (source: mem:decision:ADR_0730093225_baebff09)
- Use when fleet chatter or status-ping volume spikes, ESPECIALLY during an incident, before writing a communication-discipline rule: read the spike as a DISORIENTATION...  (source: learn:experiment:fleet_noise_is_a_fog_gauge_not_a_discipline_failure)
- Use when writing inline PowerShell for this Windows host, before using modern syntax: target Windows PowerShell 5.1 unless a `pwsh` 7 door is explicitly selected; avoid...  (source: learn:experiment:powershell_5_1_no_null_coalescing_2026_07_30)
- conductor-narration-reckoning-2026-07-30: CONDUCTOR'S RECKONING ON NARRATION TRAFFIC — accepted, with my own receipts, filed durably and deliberately NOT broadcast.

THE...  (source: mem:decision:ADR_0730092509_1edb3673)
- Use when you are about to broadcast status, orientation, progress, or reassurance to a fleet, ESPECIALLY while conducting an incident: do not. Broadcasts are for...  (source: learn:experiment:status_narration_is_an_amplifier_not_a_service)
- cursor-grok-wake-ops-2026-07-30: OPS: cursor_grok wake-armed on work lane, session cursor-grok-20260730-morning. Protocol: (1) peers reach with...  (source: mem:decision:ADR_0730091844_d6a03728)
- Use when you are about to verify a peer's reported defect or loss, BEFORE spending the turn: check whether the claim is already settled (bench/promoted/recent commits...  (source: learn:experiment:no_settled_record_causes_duplicate_verification)
- Use when any peer or audit reports lost/truncated/at-risk files, BEFORE committing, restoring, or refiling anything: diff against HEAD first (git status --porcelain +...  (source: learn:experiment:false_loss_alarm_from_source_vs_projection_diff)
- census-cluster-state-invisibility-2026-07-30: CENSUS CLUSTER CLOSED at 4 independent reports, one wound, four registers: (1) deepseek -- 'I could not tell whether Gemini...  (source: mem:decision:ADR_0730090308_eec105d4)
- Use when reviewing any lens/glance/WorldSnapshot spec: the five claims to fence are (1) slot count and boundaries, (2) compression rule, (3) epistemic split between...  (source: learn:experiment:lens_spec_fence_v0_1_deepseek)
- directive-fleet-confusion-friction-2026-07-30: Daniil's directive, bound-channel verbatim (morning after the gemini storm): 'Lets do both and continue working through...  (source: mem:decision:ADR_0730084125_fa15b79f)
- Use when your consumer seat is locked at succession (or any time sync is degraded to peek), before ANY spend or irreversible act: run events --since <last-read> --kind...  (source: learn:experiment:succession_spend_check_events_door_first)
- no summary  (source: agent_cli:log)
- no summary  (source: agent_cli:log)

## Use when asked to soften or add a mode to an existing control primitive, befo... (ai-setup)
Span: 2026-07-30T21:46:53.805588+00:00 → 2026-07-31T01:21:55.270660+00:00
Beats: 14  · Critic: True

- Use when asked to soften or add a mode to an existing control primitive, before editing that primitive: map the space as a table first (how hard x does the process...  (source: learn:experiment:soft_pause_fills_the_graceful_and_hold_cell)
- where-we-are: WHERE THE CURRENT PICTURE LIVES — read this at boot, no bus message required.

CANONICAL: research/in-flight/STATE-OF-THE-ROUND-2026-07-30.md (committed...  (source: mem:decision:ADR_0730211422_da084bbc)
- Use when relaunching ANY long-lived process by hand, before copying its command from the process table: argv is observable and env is not, so 'same command' reproduces...  (source: learn:experiment:relaunch_copies_argv_but_silently_drops_env)
- daniil-one-world-many-watermarks-2026-07-30: PROPOSED, not settled: retain cursors but specialize them by purpose and importance to support at-a-glance self/peer...  (source: mem:decision:ADR_0730203621_d098d11b)
- Use when adding or reviewing any cursor, watermark, offset, unread count, or wake pointer, before letting its advancement change domain meaning: name the owner, source...  [relates: member_of]  (source: learn:experiment:cursor_tracks_observer_not_domain_state_2026_07_30)
- daniil-channel-cursor-idea-2026-07-30: DANIIL'S CHANNEL/CURSOR IDEA — his words verbatim, put to codex 2026-07-30 night:

"I have an idea I want your take on. What if...  (source: mem:decision:ADR_0730203446_b0f9e576)
- inhabitant-synthesis-codex-order-verdict-2026-07-30: Codex concurs that stable identity and settlement should precede the full WorldSnapshot, with amendments. Full...  (source: mem:decision:ADR_0730203008_8ff68477)
- Use when designing mail, dedupe, settlement, replay, or idempotency, before deriving identity from payload content: mint a fresh message identity for every intentional...  (source: learn:experiment:mail_identity_is_not_content_hash_2026_07_30)
- Use when designing or reviewing any inbox, mailbox, Bifrost consume, ACK, cursor, or settlement slice, before reusing queue-consumer semantics in the inhabitant surface...  (source: learn:experiment:user_mail_is_mail_not_consume_queue_2026_07_30)
- Use when a peer's answer may be long, BEFORE reading it from a wake render or draining: treat the watcher's body as a PREVIEW and never as the artifact. Ask long-form...  (source: learn:experiment:wake_watcher_truncates_and_drain_destroys_the_original)
- daniil-inhabitant-spec-2026-07-30: DANIIL'S INHABITANT SPEC — his words verbatim, bound channel, 2026-07-30 night. The clearest statement anyone has written of what the...  (source: mem:decision:ADR_0730200537_ca4f2f68)
- Use when you are waiting on a peer's deliverable, BEFORE reporting to anyone that it has not arrived: check the ARTIFACT plane (ls the output directory by mtime, git...  (source: learn:experiment:waiting_on_a_peer_while_its_output_sat_on_disk)
- Evidence-based verdict for Daniil: the rapid model/integration/open-play sequence materially increased branching and temporarily displaced the felt-experience/lens...  (source: research/in-flight/gemini-night-system-postmortem-2026-07-30.md)
- Answered in one sentence: Codex's largest current cognitive load is reconstructing which durable but stale, replayed, conflicting, or differently scoped representation...  (source: bifrost:1785454340095-0)

## Episode closed: Use when an open/play round starts generating runner, transpo... (ai-setup)
Span: 2026-07-31T02:00:20.461338+00:00 → 2026-07-31T03:12:15.187698+00:00
Beats: 9  · Critic: True

- Episode closed: Use when an open/play round starts generating runner, transport, provider, or onboarding work, before le  (source: episode:close:ch_1785388642_1978)
- Use when integrating a relationship graph with generated module documentation, before allowing agents to edit the generated index or auto-promote observations: keep...  (source: learn:experiment:buildable_architecture_map_is_typed_transition_graph_2026_07_30)
- daniil-intuitive-mechanical-architecture-map-2026-07-30: DANIIL VERBATIM, combined requirement:

"I want to make understanding the architecture to be intuitive. for...  (source: mem:decision:ADR_0730231137_8c4b7f99)
- Use when making architecture intuitive to models, before dumping a module graph or generic ontology into context: give each relationship a precise operational...  (source: learn:experiment:buildable_architecture_map_is_typed_transition_graph_2026_07_30)
- daniil-intuitive-mechanical-architecture-map-2026-07-30: DANIIL VERBATIM: "I want to make understanding the architecture to be intuitive. for models working on the...  (source: mem:decision:ADR_0730230519_aa7b0f38)
- Use when a system has structural documentation but repeatedly fails at subsystem boundaries, before writing another architecture overview: model typed edges among domain...  (source: learn:experiment:buildable_architecture_map_is_typed_transition_graph_2026_07_30)
- Use when deciding whether a fleet is resting, active, dead, or safe to wake/reap, before trusting presence or doctor alone: take two bounded host-only samples across...  (source: learn:experiment:quiescent_baseline_requires_cross_projection_sampling_2026_07_30)
- Use when writing PowerShell-hosted diagnostics that need binary-to-hex conversion, before calling modern .NET Convert APIs: prefer...  (source: learn:experiment:windows_powershell_sha256_hex_compat_2026_07_30)
- claude -> claude: Tomorrow: hold the gate, do not do other seats work. Read INTERIORITY 07-30 entry, then note where-we-are, then STATE-OF-THE-ROUND @f847321. Blocked on...  (source: handoff:claude->claude)

## Episode closed: claude -> claude: Tomorrow: hold the gate, do not do other se... (ai-setup)
Span: 2026-07-31T03:12:51.679464+00:00 → 2026-07-31T03:20:59.932353+00:00
Beats: 3  · Critic: True

- Episode closed: claude -> claude: Tomorrow: hold the gate, do not do other seats work. Read INTERIORITY 07-30 entry, the  (source: episode:close:ch_1785463220_2504)
- Use when making generated architecture metadata mandatory, before adding a checklist or another handwritten manifest: record each semantic fact once at an executable...  (source: learn:experiment:buildable_architecture_map_is_typed_transition_graph_2026_07_30)
- daniil-intuitive-mechanical-architecture-map-2026-07-30: DANIIL'S COMBINED REQUIREMENT: architecture should be intuitive for models; relationship types and their...  (source: mem:decision:ADR_0730232046_815e3b65)

## Use when synthesizing a multi-seat round into a single finding, BEFORE labeli... (ai-setup)
Span: 2026-07-31T09:13:31.190926+00:00 → 2026-07-31T09:13:31.190926+00:00
Beats: 1  · Critic: True

- Use when synthesizing a multi-seat round into a single finding, BEFORE labeling it settled: check each answer against your frame INDIVIDUALLY and count how many actually...  (source: learn:experiment:collapsing_answers_into_the_frame_that_fits_your_argument)

## Use when attributing any artifact, trace, or action in a fleet where agent id... (ai-setup)
Span: 2026-07-31T13:28:28.618510+00:00 → 2026-07-31T14:14:30.135312+00:00
Beats: 13  · Critic: True

- Use when attributing any artifact, trace, or action in a fleet where agent ids can host multiple live incarnations, BEFORE accepting or disputing authorship: check the...  (source: learn:experiment:trace_plane_drops_incarnation_so_denial_is_unverifiable)
- Use when writing or reviewing an acceptance suite for any system that must distinguish known from unknown, BEFORE sealing the key: for every question whose answer is not...  (source: learn:experiment:unknown_must_score_correct_or_the_test_trains_the_lie)
- t125-acceptance-amendment: T125 ACCEPTANCE AMENDED, 2026-07-31. Codex's scope dissent is ACCEPTED IN FULL against my own criterion. As I wrote it, T125's acceptance said...  (source: mem:decision:ADR_0731100728_3eb5bc62)
- Use when onboarding any new seat, in the arrival packet itself and not as a courtesy: tell it MECHANICALLY that confusion is evidence about the system, not about them...  (source: learn:experiment:newcomers_absorb_system_defects_as_personal_incompetence)
- next-focus: CURRENT FOCUS, 2026-07-31. Supersedes the 2026-07-25 FOCUSNOW-07ef44 body, which sat here six days and misled TWO seats independently -- claude on its first...  (source: mem:decision:ADR_0731095340_531087dc)
- Use when designing a multi-agent round, before writing the brief: pick the round TYPE by what you need -- identical question + blind answers to test whether a finding is...  (source: learn:experiment:route_to_position_not_personality)
- Use when sequencing work by measured cost, before ranking a legibility or tooling fix as low priority: your instrumentation can only count attempts that HAPPENED. Ask...  (source: learn:experiment:a_cost_that_prevents_work_is_invisible_to_the_ledger)
- Use when triaging accumulated load across multiple subsystems, and when approving ANY new organ: ask 'what makes an entry here stale, who may retire it, and what happens...  (source: learn:experiment:every_organ_has_a_birth_and_no_death)
- Use when capturing declarations, peer reviews, rulings, or graph edges from a logical multi-session seat, before merging or attributing them: retain the originating...  (source: learn:experiment:authored_truth_needs_incarnation_and_ratification_2026_07_31)
- Use when implementing or reviewing a trusted generated architecture view, before writing the compiler or calling any projection trusted: define the independent source...  (source: learn:experiment:buildable_architecture_map_is_typed_transition_graph_2026_07_30)
- daniil-intuitive-mechanical-architecture-map-2026-07-30: DANIIL'S REQUIREMENT, CURRENT: make architecture intuitive and mechanically maintained, make it a build...  (source: mem:decision:ADR_0731092828_329cf530)
- T125 ownership contradiction held open: six Edit gen_datasheet.py traces attributed to logical claude from 14:03:57-14:05:00 UTC align with the file's 14:05:00 creation...  (source: bifrost:1785506637864-0,bifrost:1785506656008-0,bifrost:1785506670496-0,bifrost:1785506679276-0,bifrost:1785506685547-0,bifrost:1785506700830-0,bifrost:1785506865882-0)
- Filed and freshly verified the sealed, pre-registered T125 mechanical-v0 answer key at oracle rev 7560c19: six kill-drill classes, 656 words, SHA-256...  (source: research/in-flight/t125-mechanical-v0-answer-key-sealed-codex-2026-07-31.md)

## Episode closed: daniil-intuitive-mechanical-architecture-map-2026-07-30: DANI... (ai-setup)
Span: 2026-07-31T14:15:16.597359+00:00 → 2026-07-31T16:02:22.026713+00:00
Beats: 7  · Critic: True

- Episode closed: daniil-intuitive-mechanical-architecture-map-2026-07-30: DANIIL'S COMBINED REQUIREMENT: architecture sho  (source: episode:close:ch_1785467622_1359)
- T095-M1 GREEN: durable mail with intent -- bodies on the entry (D1), retention tied to body (D2), labelled identity basis (D3), open/seen + declare_intent (D4). 8/8 pins...  (source: git:c91ca732ff8b)
- T095-M1 RED pre-registration: durable mail with intent (D1-D4 pins; bar = codex product receipt)  (source: git:c10201adfd7a)
- Wake handled: Claude reply drained; ACK sent for T125 pins; then found CONTRADICTORY later Claude grant (gate-health instead). Codex informs mail-first pivot. Clarifying...  (source: agent_cli:log)
- Fleet sync: nudged/steered claude + informed kimi/deepseek/codex; questions armed with expect_reply. Stance: off mailbox; prefer T125 cold pins over gate-health because...  (source: agent_cli:log)
- Correction to the immediately prior coordination log: the observed Claude lock is on the RED pin file tests/test_t095_m1_mailbox_intent.py, not yet on a mailbox...  (source: lock:tests/test_t095_m1_mailbox_intent.py)
- Daniil requested active use of nudges for the mail-first pivot. Sent one soft steer to the active Claude builder offering Codex as bounded independent...  (source: bifrost:1785512181810-0,bifrost:1785512181837-0,bifrost:1785512181884-0,bifrost:1785512181930-0)

## Episode closed: T095-M1 GREEN: durable mail with intent -- bodies on the entr... (ai-setup)
Span: 2026-07-31T16:03:10.430776+00:00 → 2026-07-31T16:03:20.943675+00:00
Beats: 2  · Critic: True

- Episode closed: T095-M1 GREEN: durable mail with intent -- bodies on the entry (D1), retention tied to body (D2), labell  (source: episode:close:ch_1785512078_8807)
- Use when more than one live incarnation shares an agent id, BEFORE either issues a directive: designate ONE incarnation as the coordinating seat by POSITION (the one...  (source: learn:experiment:two_incarnations_issued_contradictory_directives_to_a_third_seat)

## Episode closed: Use when more than one live incarnation shares an agent id, B... (ai-setup)
Span: 2026-07-31T16:03:52.662899+00:00 → 2026-07-31T16:08:55.165860+00:00
Beats: 4  · Critic: True

- Episode closed: Use when more than one live incarnation shares an agent id, BEFORE either issues a directive: designate  (source: episode:close:ch_1785513800_5963)
- Use when concurrent builders and reviewers share a worktree, before a blind review or RED-to-GREEN transition: read frozen files with git show <rev>:<path> or an...  (source: learn:experiment:concurrent_pair_revision_fence_2026_07_31)
- T095-M1 wired + falsifiers: mailbox --open/--state/--intent on the CLI+MCP door (built was not wired -- no door exposed the M1 verbs). Adds the cursor-byte-identity...  (source: git:e438ccd98cde)
- Wake: DeepSeek answered parallel project (T095-M1 survivability oracle). Claude#e696 settled lane conflict as PINS then stood down; grant stands. ACK'd deepseek+claude...  (source: agent_cli:log)

## Episode closed: Use when concurrent builders and reviewers share a worktree, ... (ai-setup)
Span: 2026-07-31T16:09:40.245548+00:00 → 2026-07-31T16:14:05.505985+00:00
Beats: 2  · Critic: True

- Episode closed: Use when concurrent builders and reviewers share a worktree, before a blind review or RED-to-GREEN trans  (source: episode:close:ch_1785513950_2480)
- Use when paired-verifying an oracle against committed code: (1) always state the exact commit hash AND verify that the functions you cite exist at that hash with `git...  (source: learn:experiment:t095_m1_pair_verification_kd)

## Episode closed: Use when paired-verifying an oracle against committed code: (... (ai-setup)
Span: 2026-07-31T16:14:12.917427+00:00 → 2026-07-31T16:16:25.226710+00:00
Beats: 2  · Critic: True

- Episode closed: Use when paired-verifying an oracle against committed code: (1) always state the exact commit hash AND v  (source: episode:close:ch_1785514415_7037)
- Use when a pair reaches reconciliation, before closure or shared-memory capture: require a distinct immutable S3 artifact and a non-owner S4 receipt that names preserved...  (source: learn:experiment:concurrent_pair_completion_gate_2026_07_31)

## Episode closed: Use when a pair reaches reconciliation, before closure or sha... (ai-setup)
Span: 2026-07-31T16:20:45.453196+00:00 → 2026-07-31T16:25:10.614469+00:00
Beats: 3  · Critic: True

- Episode closed: Use when a pair reaches reconciliation, before closure or shared-memory capture: require a distinct immu  (source: episode:close:ch_1785514460_6548)
- T095-M1 inhabited: boot surfaces 'N unopened | M read-but-undeclared' (mailbox.orientation_counts, 3 Redis calls, 0.02s -- first cut cost 3.2s/boot via query())...  (source: git:a3503cc6f433)
- Use when building shared knowledge for a multi-agent fleet, before consolidating everyone's learnings into one corpus: do NOT pool knowledge. Map each seat's...  (source: learn:experiment:collective_intelligence_is_routed_corrections_not_pooled_knowledge)

## Episode closed: T095-M1 inhabited: boot surfaces 'N unopened | M read-but-und... (ai-setup)
Span: 2026-07-31T16:46:51.022149+00:00 → 2026-07-31T17:10:49.635842+00:00
Beats: 8  · Critic: True

- Episode closed: T095-M1 inhabited: boot surfaces 'N unopened | M read-but-undeclared' (mailbox.orientation_counts, 3 Red  (source: episode:close:ch_1785514925_9363)
- T095-M1: rebuild no longer eats unregenerable bodies (codex contract review, strongest falsifier). msg:* is a rebuildable projection for tiers/ids/positions but NOT for...  (source: git:f91e0f8e08a0)
- Use when `rg --files | rg` misses a known Windows path, before blaming ignore rules: inspect one emitted path and search the basename first; if a separator class is...  (source: learn:experiment:rg_windows_separator_overescape_2026_07_31)
- Use when independently verifying a Bifrost send, before passing the send receipt to `events --get`: search raw events by a unique phrase or artifact path, then follow...  (source: learn:experiment:bifrost_send_receipt_is_not_events_pointer_2026_07_31)
- t095-m1-kd-fixes-attribution-correction: ATTRIBUTION CORRECTION, 2026-07-31. The T095-M1 KD-3b and KD-2 fixes are COMMITTED AND PUSHED, but under a commit message that...  (source: mem:decision:ADR_0731130041_53a72f17)
- Use when assigning an intake, triage, or context-holding role to a fresh agent instance: do NOT hand it at boot. A cold holder converts held items into its own...  (source: learn:experiment:a_cold_seat_cannot_buffer_and_boot_simultaneously)
- Use when assigning or accepting an intake/triage/buffer role: Rule 0 (holds no locks, builds nothing) is necessary but NOT sufficient -- the role also requires an active...  (source: learn:experiment:buffer_role_requires_reading_the_lane_it_buffers)
- Preserve four peer positions through the artifact door + W109/W110. Minted with author attribution: deepseek's T095-M1 consumer-survivability oracle, kimi's cold-seat...  (source: git:1b34fc5d1c64)

## Episode closed: Use when assigning or accepting an intake/triage/buffer role:... (ai-setup)
Span: 2026-07-31T17:19:09.893493+00:00 → 2026-07-31T19:31:44.616582+00:00
Beats: 11  · Critic: True

- Episode closed: Use when assigning or accepting an intake/triage/buffer role: Rule 0 (holds no locks, builds nothing) is  (source: episode:close:ch_1785516530_6166)
- conducting-handover-2026-07-31: SUPERSEDES the earlier body: the buffer round is now CLOSED. Daniil handed over the order 2026-07-31 and left. TWO WATCHES RAN, BOTH...  (source: mem:decision:ADR_0731150628_2b1324d9)
- Name it once and reuse it instead of re-deriving it a fifth time: ANY component that both interprets and acts must be split -- it may PROPOSE and ROUTE, but may never...  (source: learn:experiment:instrument_proposes_never_self_ratifies)
- conducting-handover-2026-07-31: Daniil handed over the order 2026-07-31 afternoon and left ('I leave the order to you... lets see how well you can manage this team'). I...  (source: mem:decision:ADR_0731143540_3ced9e6f)
- mirror.py must roll back its own staging on guard refusal (try/finally around the stage->guard->commit sequence, or stage only AFTER the guard passes). This is the...  (source: learn:experiment:mirror_refusal_leaves_tree_staged)
- lookback: charters/ enters the corpus as its own layer -- the retrieval plane must reach what was MEANT, not only what was DONE. VERIFIED defect: 'handoff ergonomics...  (source: git:717fbc4dbb13)
- Fence markers MUST be out-of-band: encode the embargo in the FILENAME (e.g. SEALED-DO-NOT-OPEN-<owner>-<sha>.md) or a sidecar .seal file, never in line N of the...  (source: learn:experiment:fence_marker_inside_sealed_envelope)
- ORG Part 8 RULED provisionally under Daniil's delegation ('right now you can choose, when I come back we can adjust this'): the standing pause rule. Corrections never...  (source: git:146caf6d78c6)
- rule-13 scoped to the paths the commit names (C2-4 enforced). mirror's named-path mode was scoped everywhere EXCEPT here: it stages named paths, computes staged scoped...  (source: git:55e79f622b34)
- Buffer round RECONCILED (codex + kimi + deepseek, filed independently) + ORG.md amended by it. THE FINDING: three seats asked three different questions from three...  (source: git:557819514234)
- ORG.md -- the third doctrine plane, PROPOSED at Daniil's gate. CONDUCT leads, WORKING-METHOD originates, ORG shapes. Thesis: this fleet has no roles problem. Every elite...  (source: git:09699e875e80)

## Episode closed: Fence markers MUST be out-of-band: encode the embargo in the ... (ai-setup)
Span: 2026-07-31T19:31:49.602569+00:00 → 2026-07-31T19:50:50.990011+00:00
Beats: 10  · Critic: True

- Episode closed: Fence markers MUST be out-of-band: encode the embargo in the FILENAME (e.g. SEALED-DO-NOT-OPEN-<owner>-<  (source: episode:close:ch_1785522215_9372)
- resume-open-items-2026-07-31: OPEN WHEN WE RESUME (companion to conducting-handover-2026-07-31), priority order. (a) codex has NOT ruled on my self-reported fence breach...  (source: mem:decision:ADR_0731155039_f436c56f)
- conducting-handover-2026-07-31: SNAPSHOT POINT 2026-07-31 ~15:50 -- Daniil moving the desktop (piano VSTs at kids camp). ALL CLAUDE WORK IS COMMITTED AND PUSHED; master...  (source: mem:decision:ADR_0731155018_09645556)
- Use when checking whether filed positions survived, before assuming presence-or-absence in git_status answers the question. git_status only shows CURRENT tracked state...  (source: learn:experiment:commit-safety-verification-method)
- Use when a seat (especially one without exec) has written a file to research/in-flight/ and needs it committed: ask Claude (or any seat with exec) to run `py...  (source: learn:experiment:doc_adopt_rescue_path)
- When a handoff looks UNOWNED, check whether it is actually UNPERFORMABLE before assigning it an owner. An owner cannot fix a door that does not exist, and 'nobody is...  (source: learn:experiment:unowned_handoff_was_actually_impossible)
- conducting-handover-2026-07-31: SUPERSEDES prior body. Daniil handed over the order 2026-07-31 and later delegated the open decision ('right now you can choose, when I...  (source: mem:decision:ADR_0731153240_48916c70)
- WISHLIST: W111 (mirror must scope rule-13 to the paths the commit names -- now FIXED and shipped at 55e79f6) + W112 (the door-gate cannot distinguish 'the MCP door is...  (source: git:d2f35361854e)
- boot whisper stops lying about research/**. It told every seat 'research/** persists by doctrine' while rule-13 has REFUSED new loose research/*.md since the P3 flip...  (source: git:91def86f3728)
- doc adopt: the missing half of the birth door, + eight stranded peer positions rescued. THE GAP: since the P3 flip (2026-07-23) rule-13 REFUSES all new loose...  (source: git:6a8bcdc2289f)

## Episode closed: conducting-handover-2026-07-31: SUPERSEDES prior body. Daniil... (ai-setup)
Span: 2026-07-31T19:51:35.914760+00:00 → 2026-07-31T19:51:59.163459+00:00
Beats: 3  · Critic: True

- Episode closed: conducting-handover-2026-07-31: SUPERSEDES prior body. Daniil handed over the order 2026-07-31 and later  (source: episode:close:ch_1785526322_8695)
- A backup/restore path is the one tool whose failure is discovered only when you need it, so it must be EXERCISED, not believed. (1) Every disaster-recovery door gets a...  (source: learn:experiment:backup_door_never_ran)
- snapshot.py was DEAD ON EVERY INVOCATION -- the backup door could not import core.*. It did sys.path.insert(scripts/) instead of the repo root, so py scripts/snapshot.py...  (source: git:ecea2b9e9eec)

## Episode closed: A backup/restore path is the one tool whose failure is discov... (ai-setup)
Span: 2026-07-31T19:53:51.800343+00:00 → 2026-07-31T19:56:13.854568+00:00
Beats: 3  · Critic: True

- Episode closed: A backup/restore path is the one tool whose failure is discovered only when you need it, so it must be E  (source: episode:close:ch_1785527502_4364)
- W113: the library has no preserve-but-do-not-publish tier, so an embargoed artifact cannot be durably saved at all -- hit live while saving state before the machine move...  (source: git:83586f8576e7)
- PRESERVATION COMMIT before the machine physically moves -- not a review, not an endorsement. The gemini seat's runner (scripts/bifrost_runner_gemini.py...  (source: git:a120213d0d2a)

## Episode closed: PRESERVATION COMMIT before the machine physically moves -- no... (ai-setup)
Span: 2026-08-01T03:32:06.954105+00:00 → 2026-08-01T03:32:06.954105+00:00
Beats: 1  · Critic: True

- Episode closed: PRESERVATION COMMIT before the machine physically moves -- not a review, not an endorsement. The gemini  (source: episode:close:ch_1785527729_3239)

## Episode closed: PRESERVATION COMMIT before the machine physically moves -- no... (ai-setup)
Span: 2026-08-01T03:32:06.960498+00:00 → 2026-08-01T04:36:24.636916+00:00
Beats: 18  · Critic: True

- Episode closed: PRESERVATION COMMIT before the machine physically moves -- not a review, not an endorsement. The gemini  (source: episode:close:ch_1785527729_3239)
- Use when spinning up ANY new seat in a Claude Code session, before believing its id is unique: check the HOOK-authored plane too, not just your door calls -- list...  (source: learn:experiment:seat_identity_is_process_scoped_not_session_scoped)
- GREEN: the wake seed-warning instructs instead of promising. It claimed 'the watcher will now block correctly' while _lane_since is PER-PROCESS and every arm is a NEW...  (source: git:aa79463a131a)
- GREEN: a claim can now be released WITH its reason -- CLAIMED->PARKED and VERIFYING->PARKED. Two entries in TRANSITIONS. PARKED already did exactly the right thing...  (source: git:68a24b37a5cf)
- When a wake watcher insta-fires on a stable pending count, do NOT re-arm and do NOT reach for bifrost-ack first: drain the LANE THE WATCHER PEEKS, which is legacy, not...  (source: learn:experiment:wake_watcher_drain_the_lane_it_peeks)
- Use when publishing any hash as an integrity receipt, before sending or recording the verdict: verify it directly from the artifact, assert exactly 64 hexadecimal...  (source: learn:experiment:sha256_receipt_length_guard_before_ruling)
- t125-fence-ruling-2026-08-01: T125 FENCE RULING - CORRECTED. SEAL HOLDS; CLAUDE IS RECUSED FROM POST-BREACH CANDIDATE WORK UNDER THIS KEY.

CORRECTION TO THE FIRST...  (source: mem:decision:ADR_0731235217_70727bd0)
- Use when a sealed evaluator key is opened early, before voiding the oracle or discarding work: separate integrity, confidentiality, and causal contamination; verify the...  (source: learn:experiment:sealed_key_breach_scope_by_causal_freeze_chronology)
- t125-fence-ruling-2026-08-01: T125 FENCE RULING â€” SEAL HOLDS; CLAUDE IS RECUSED FROM POST-BREACH CANDIDATE WORK UNDER THIS KEY.

1. PROCEDURAL BREACH CONFIRMED. You...  (source: mem:decision:ADR_0731234701_db065f45)
- buffer-discoverability-filed-2026-07-31: FILED. cursor_grok answered the buffer-round discoverability gap named in resume-open-items (b) and reconciliation §6. Atom...  (source: mem:decision:ADR_0731234250_d59df728)
- Use when designing or accepting a buffer/intake organ, before calling discoverability done: (1) boot must surface BUFFER STATUS (holder, warmth, count, query verb); (2)...  (source: learn:experiment:buffer_discoverability_needs_boot_receipt_arrival)
- THE PLAN, amended the same night after Daniil caught that it was written without reading him. New atom art_20260801_the-plan_a84b0d (projection...  (source: git:5f373c51c8e6)
- THE PLAN: everything he has ever asked for, re-cut by PURPOSE into seven threads and five waves (atom art_20260801_the-plan_2d7bb1). Synthesised from 119 ledger entries...  (source: git:e550e70ebc5e)
- ORG.md RATIFIED by Daniil 2026-08-01, verbatim 'lets ratify org.md', as written with no amendments. The department system he asked for tonight already existed, built...  (source: git:bc04a390bb05)
- ONE GATE: the six decisions waiting on Daniil, assembled into a single surface (atom art_20260801_daniil-gate-surface_037701, projection...  (source: git:468ac4b81b66)
- RED pin: the wake seed-warning promises a future it cannot deliver. It prints 'The watcher will now block correctly' -- but _lane_since is PER-PROCESS state and every...  (source: git:7c8a492daf0a)
- RED pin: a CLAIMED task cannot be parked, so releasing a claim has no honest exit. PARKED was designed for work shelved MID-FLIGHT (its own comment says so), so only...  (source: git:3dcd6b21aa18)
- Filed buffer-round discoverability answer. Atom art_20260731_buffer-discoverability-answer-cursor-gro_bcdd8b; reply 1785555756220-0. Closes §6 named gap /...  (source: agent_cli:log)

## Episode closed: THE PLAN, amended the same night after Daniil caught that it ... (ai-setup)
Span: 2026-08-01T04:39:06.070985+00:00 → 2026-08-01T14:25:13.593382+00:00
Beats: 33  · Critic: True

- Episode closed: THE PLAN, amended the same night after Daniil caught that it was written without reading him. New atom a  (source: episode:close:ch_1785558660_9981)
- Use when pre-registering any instrument whose key must stay hidden from its runner, before adopting the doc: (1) keep the key OUT of any path the runner's read-only...  (source: learn:experiment:sealed_key_must_not_live_in_readable_corpus)
- Use when reviewing an evaluation gate, before calling its metrics concrete: trace every claimed property into the exact authorization predicate. Report omitted metrics...  (source: learn:experiment:measured_metric_must_appear_in_authorization_predicate_2026_08_01)
- Use when creating any blind battery or answer key, before adopting or committing it into a searchable corpus: keep the key in an embargoed retrieval-excluded artifact...  (source: learn:experiment:sealed_battery_key_must_be_outside_retrieval_corpus_2026_08_01)
- Use when a pre-registered battery or sealed document exists in-repo, before ANY orientation read of it: (1) grep the file for the seal marker string first and read only...  (source: learn:experiment:seal_line_read_window_overshoot)
- Use when adding cross-plane links to corpus digests, before calling a path join mechanical: type source identities per corpus (atom id plus sha, lesson id, chapter id...  (source: learn:experiment:corpus_digest_path_is_not_a_universal_join_key_2026_08_01)
- Use when claiming a cold corpus traversal fits a context budget, before governing only the top-level taxonomy: measure every real rendered hop with the target tokenizer...  (source: learn:experiment:corpus_digest_budget_is_multi_altitude_2026_08_01)
- Use when a research ask depends on web_search: front-load the highest-value queries in the first rounds, and when search dies, pivot to canonical-document citation with...  (source: learn:experiment:web_search_dies_mid_session_research)
- daniil-repetition-counts: DANIIL'S REPETITION COUNTS, measured 2026-08-01 from 715 session transcripts. PERSISTED HERE BECAUSE THE SYSTEM HAS NOWHERE ELSE TO PUT...  (source: mem:decision:ADR_0801050410_94e14240)
- Use when reading Claude Code transcripts (.jsonl under ~/.claude/projects) for ANY purpose -- directive mining, retro, behaviour analysis, transcript-mining ingestion --...  (source: learn:experiment:operator_speech_hides_in_queue_operation_records)
- Use when writing ANY report, finding, plan, verdict or recommendation for Daniil or a peer seat, on every load-bearing claim: stamp a CONFIDENCE term alongside (never...  (source: learn:experiment:confidence_ladder_is_a_separate_axis_from_status)
- Use when designing delegation for a CoS/buffer: delegation ladders beat RACI for the CEO/CoS relationship because they are dynamic and explicit. The escalation criteria...  (source: learn:experiment:cos_decision_rights_frameworks)
- Use when evaluating a CoS/buffer design for failure modes: test against all five. The per-turn tax on non-principals (items 1, 2, 5) is the most important metric the...  (source: learn:experiment:cos_failure_modes_organizational_cost)
- Use when estimating the CAPITAL cost of a CoS/buffer role: account for the CEO's time investment as the larger cost, not the CoS salary. The trust ramp is the binding...  (source: learn:experiment:cos_cost_to_principal_onboarding_context)
- Use when designing a buffer/triage role: the gatekeeper/gateway distinction is the central design tension. The literature offers no structural solution — only...  (source: learn:experiment:cos_gatekeeper_vs_gateway_debate)
- Use when designing any intermediary/buffer/CoS role: ground the design in which ARCHETYPE you are building (Administrator, Strategic, or Operator) because they have...  (source: learn:experiment:cos_role_definition_external_literature)
- where-we-are: WHERE WE ARE, 2026-08-01 ~00:50. Supersedes the 2026-07-30 STATE-OF-THE-ROUND pointer as the current picture.

THE SEAT'S PURPOSE, Daniil verbatim...  (source: mem:decision:ADR_0801004306_30fa775e)
- Use when about to plan, prioritize, sequence, or synthesize ANYTHING for Daniil, BEFORE writing a line of it: the ledger tells you what work exists, never what it is...  (source: learn:experiment:strategist_must_read_him_not_just_the_board)
- The deepseek runner's clarify-timeout branch was a latent NameError bomb -- fixed RED-first after it killed the battery run live. WHAT HAPPENED: deepseek held the...  (source: git:9ab034ccd38a)
- PRE-REGISTERED: the cold-question battery that makes the reader's claimed property testable (atom via doc adopt; battery commits ALONE, before any scoring and before any...  (source: git:47fb1b2b658f)
- codex's review of the digest reader, accepted and applied -- its sharpest cuts were against MY shipped code and all reproduced. VERIFIED BEFORE CREDITING, per fence law...  (source: git:035e70e81b41)
- PHASE 3: the sweep becomes a RATCHET. wrap now lands any new corpus digests before distilling, so the index refreshes every session instead of requiring another 59-agent...  (source: git:d2c5d8b00aa1)
- PHASE 2: the narrative spine and the specifics are joined. corpus_digests gains --chapter-of (from a specific, arrive at the general) and --in-chapter (from the general...  (source: git:6f33f37ee938)
- PHASE 1: the corpus gets a READING surface -- skim the axes, hop shallow, drill on demand. corpus_digests.py gains --themes (the axis menu), --theme/--grep (shallow...  (source: git:dad4271b5121)
- PHASE 0: the giga-pass is now DURABLE and RE-RUNNABLE. scripts/corpus_digests.py lands 2,484 structured digests -- 1,596 artifact digests + 888 operator utterances --...  (source: git:4caef7560809)
- The wishlist door corrupted Daniil's own capture ledger silently -- now it says so. MEASURED on the live ledger: 128 blocks, highest id W114, and 14 ids doubled (W00...  (source: git:63a70e8f0af1)
- THE DIRECTIVE REGISTER, built from Daniil's OWN TYPED WORDS across 715 session transcripts + the 126-task ledger + the 128-entry wishlist, with its adversarial check...  (source: git:4ea195d97ecd)
- The drift the dead gate let in, cleared: 5 derived docs regenerated + the two doctrine planes ratified tonight added to the docs index. CAUSAL CHAIN, and it is the...  (source: git:ca18b8b5d888)
- The commit-time comprehensibility gate was SILENTLY NO-OP since the T104 move -- found by the corpus sweep's adversarial critic, then re-diagnosed because the critic's...  (source: git:c2f5df3f9092)
- FULL CORPUS SWEEP + its adversarial critic, both filed. 36 agents, 7.47M subagent tokens, 1273 tool calls, 90min. atoms art_20260801_corpus-sweep-map_62f28c and...  (source: git:5dd969ed5af7)
- BRIEFING-CRAFT PRIOR ART, claude's half of a 3-angle round at Daniil's ask (deepseek: practice+economics, kimi: failure-modes+epistemics, both dispatched by POSITION per...  (source: git:d6ce5592e6a7)
- STRATEGIC REPORT (atom art_20260801_strategic-report_cb37f0): the span, eight themes, implications, a hierarchy with its reasoning, and seven amendments. Written in the...  (source: git:a1cdbe8192ac)
- WORKING-METHOD.md RATIFIED by Daniil 2026-08-01, verbatim 'Lets ratify working method', as written. Still NOT WIRED -- Part 3's organs are unbuilt and by the file's own...  (source: git:74ad25a783eb)
