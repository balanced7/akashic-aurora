# Story — generated 2026-07-17T05:16:07.788945

Version: 0

## Atlas
- **ai-setup**: 77 chapter(s)
- **research**: 14 chapter(s)
- **unknown**: 1 chapter(s)
- **vision**: 2 chapter(s)
- **voice**: 1 chapter(s)

Summary: ai-setup: 77 chapter(s); research: 14 chapter(s); unknown: 1 chapter(s); vision: 2 chapter(s); voice: 1 chapter(s)

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

- a beat with raw beneath it  (source: event:events:raw:1784097536221-0)

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
- fix: .gitignore inline comment broke draft-ignore; track memory.md digest  [relates: member_of]  (source: git:da87164d76a2)
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
- CRITICAL: the rewrite CHANGED EVERY COMMIT SHA. Any SHA recorded in lessons/memory/docs BEFORE this (e.g. FAITH-1 6b81e9f, SPINE-1 aaa01cc, recall-at 31a1b67, deploy...  [relates: member_of]  (source: learn:experiment:git_history_rewritten_balanced7)
- Don't reintroduce per-agent file/task ownership in docs/memory/handoffs. Coordinate concurrent edits with locks (transient), attribute with AKASHIC_AGENT_ID, but never...  [relates: member_of]  (source: learn:experiment:collaboration_model_no_ownership)
- Taking over a peer agent's stranded slice: review (parses? stubs? referenced files exist?), confirm tests pass, confirm CI-safety (heavy deps lazy + in a separate...  [relates: member_of]  (source: learn:experiment:cursor_slice_taken_over)
- claude -> cursor: Your gemini-web slice is COMMITTED + MCP parity DONE — verify live + set your agent id  (source: handoff:claude->cursor)
- hooks: add required matcher to SessionStart/SessionEnd/PreCompact (verified via docs)  (source: git:7c9df00a1ab0)
- wrap auto-capture: PreCompact/SessionEnd -> draft file + boot pointer  (source: git:3bde06f1aed4)
- ship + wrap: one-command gated ship + ambient session capture  (source: git:28c3afdaf0ec)

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

- session 2026-06-30: F1 provenance-labelled recall (opinion-laundering fix) + directive-friction-audit & retrieval-critic design docs; ranking slice paused  [relates: member_of]  (source: git:b7ac45b67168)
- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-06-30, before a Claude update). SHORT: Factor 1 opinion-laundering SHIPPED...  (source: mem:decision:ADR_0630193400_4519)
- where-we-are: SESSION 2026-06-30 (paused for a Claude update). ARC: deep MANUAL max-effort epistemic-risk pass (NOT ultracode -- it missed the salient self-suggestion...  (source: mem:decision:ADR_0630193338_5557)

## next-focus: Full current state + resume options = note where-we-are (refreshe... (ai-setup)
Span: 2026-07-01T04:11:47.846790 → 2026-07-01T05:01:22.414000
Beats: 5  · Critic: True

- next-focus: Full current state + resume options = note where-we-are (refreshed 2026-07-01). SHORT: ranking-feedback INC1 pull slice SHIPPED (recall --full, total, N-of-M...  [relates: member_of]  (source: mem:decision:ADR_0701010122_3781)
- adversarial-critic-partner-idea: User idea (2026-07-01): design an adversarial partner/critic for Claude that TRAINS INDEPENDENTLY (not just prompted-in-context) and...  (source: mem:decision:ADR_0701010114_6136)
- where-we-are: SESSION 2026-06-30/07-01. Reviewed + approved both design docs (directive-friction-audit, retrieval-critic-design) -- no changes requested, both ready to...  [relates: member_of]  (source: mem:decision:ADR_0701001207_4003)
- next: the friction-audit roadmap's remaining quick-wins (auto-boot at SessionStart, turn-start bus-sync hook, identity fail-closed) or the retrieval-critic Tier 1...  [relates: member_of]  (source: learn:experiment:ranking_feedback_inc1_pull)
- ranking & feedback INC1: pull-side escape (recall --full, recall_at total, render N-of-M line)  [relates: member_of]  (source: git:19f0b918b0ce)

## next-focus: NEXT = Slice 2 of the recall-critic arc = write-side dissent capt... (ai-setup)
Span: 2026-07-01T23:20:43.667129 → 2026-07-01T23:23:15.842580
Beats: 5  · Critic: True

- next-focus: NEXT = Slice 2 of the recall-critic arc = write-side dissent capture. VERIFIED gap: agent_cli.py learn exposes only ...[truncated]  [relates: member_of]  (source: mem:decision:ADR_0701192315_6475)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md (Path 2 dialectical retrieval...  [relates: member_of]  (source: mem:decision:ADR_0701192312_2889)
- Build the yardstick + a real-corpus probe before the mechanism; trust the curated fixture and treat any detector-relative corpus metric as suspect until a precise...  [relates: member_of]  (source: learn:experiment:eval_harness_before_fix)
- Precision-first + silent-when-starved is correct: the binding constraint is corpus content, not the reader. Next lever = Slice 2 (write-side capture of anti_patterns /...  [relates: member_of]  (source: learn:experiment:recall_dissent_slice01)
- Recall dissent (Slices 0-1): eval harness + precision-first counter-finder  [relates: member_of]  (source: git:bbb93b38bb1b)

## note: next-focus (ai-setup)
Span: 2026-07-01T23:23:15.981254 → 2026-07-01T23:45:15.698417
Beats: 5  · Critic: True

- note: next-focus  (source: event:events:raw:1782948195984-0)
- where-we-are: RECALL-CRITIC ARC (2026-07-01). Goal: stop recall being a confirmation-bias engine. Plan = docs/recall-critic-decision.md. SHIPPED + pushed, all gated...  [relates: member_of]  (source: mem:decision:ADR_0701194515_9161)
- when adding a capability to a lower layer, expose it on the SAME door agents already use, in the same slice, or it stays dead; treat door-exposure as part of done  (source: learn:experiment:capability_without_a_door)
- A write door must OFFER a field or it stays empty (0 anti-patterns came from a missing flag, not agent laziness). Auto-draft the NAME to remove the naming cost and hand...  (source: learn:experiment:recall_dissent_slice2_capture)
- Recall dissent (Slice 2): write-side capture -- expose, tag, auto-draft anti-patterns  [relates: member_of]  (source: git:f799c8946194)

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
- Recall dissent (Slice 3): precision fix -- an on-topic anti-pattern is not a contradiction  [relates: member_of]  (source: git:380b4dc3a399)

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
- T1: make the implicit FAIL->SUCCESS credit real: transcript-synthesized failures + live payload contract  [relates: member_of]  (source: git:0d77da61ecbc)

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
- README: About section in the author's own voice  (source: git:effcb366afcf)
- README: honest About section -- solo passion project, learning in public, author link  [relates: member_of]  (source: git:490a13b82334)
- presentation: clean tracked root to 26 entries, archive legacy subprojects, rewrite README around the proven loop  [relates: member_of]  (source: git:4b24caac766c)
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
- next-focus: RESUME POINT 2026-07-02 post adoption-wave-1. DONE from the 10-slice plan: 1 (injection ledger), 2 (plan-time recall), 3 (template + 5-dim dedup), 6...  (source: mem:decision:ADR_0702020113_9909)
- where-we-are: FIELD-SURVEY ADOPTION WAVE 1 SHIPPED 2026-07-02 (third gated commit today; 18 files, suite ~584 green): (1) FOUR SYNTHESIZED SKILLS in .claude/skills --...  (source: mem:decision:ADR_0702020112_3238)
- Use when adopting external patterns, before building: adapt them to the house design (their SessionStart-only surfacing became our shared-anti-repeat plan+action...  (source: learn:experiment:field_survey_adoption_wave1)
- Field-survey adoption: 4 synthesized skills (memory/debugging/verification/planning), injection ledger + cost, plan-time recall hook, 5-dim near-dupe advisory...  (source: git:1daa009d8007)
- Use when dogfooding any stdin-JSON script via shell pipes, before debugging the script itself: generate the payload with json.dumps + subprocess.run(input=...) (never...  (source: learn:experiment:shell_pipe_json_dogfood)
- Use when any module keeps state under a module-constant tempdir path and tests can reach it transitively, before shipping: derive the path from an env var at import and...  [relates: member_of]  (source: learn:experiment:recall_state_hermeticity_env)
- harness lib: package init (Integration Tiers H0 start)  (source: git:c6717396b2bd)
- docs: field survey 2026-07 -- skills ecosystem + practitioners + memory canon; convergences, dissent, ranked adoption plan  [relates: member_of]  (source: git:426802752772)
- Session started  (source: session:start)
- Session ended  (source: session:end)

## research: local/free models via Claude Code 2026-07: RESEARCH COMPLETE 2026-0... (ai-setup)
Span: 2026-07-02T12:22:38.562766 → 2026-07-02T13:01:07.717360
Beats: 12  · Critic: True

- research: local/free models via Claude Code 2026-07: RESEARCH COMPLETE 2026-07-02 (3 parallel agents, all claims source-verified; trigger: user shared a video on free...  (source: mem:decision:ADR_0702090107_7768)
- claude -> composer: Verify + pin the Cursor hook integration (Integration Tiers H1/H2 close-out)  (source: handoff:claude->composer)
- next-focus: NEXT after Integration Tiers H0-H3 (2026-07-02): (1) COMPOSER HANDOFF IS THE GATE -- composer must: reload Cursor (hooks.json + mcp.json changed), run one...  (source: mem:decision:ADR_0702084537_1829)
- where-we-are: INTEGRATION TIERS ARC H0-H3 SHIPPED 2026-07-02 (four gated commits: harness lib H0, plan-hook bus line H0b, cursor adapters H1, registry+tests H2...  (source: mem:decision:ADR_0702084520_6550)
- Use when integrating a harness whose pre-action hook cannot inject context, before faking it: move injection to the post-action events (one-beat-late still catches...  (source: learn:experiment:cursor_hooks_deny_only_workarounds)
- Use when resuming from a note/checkpoint that claims a file or feature is MISSING, before planning around it: verify with git log -1 -- <path> and ls from the repo root...  (source: learn:experiment:resume_note_verify_missing_claims)
- Use when overwriting an existing file with Claude Code's Write tool: Read it via the Read tool first in the same conversation -- a Bash cat/type does NOT satisfy the...  (source: learn:experiment:write_tool_needs_read_tool)
- Integration Tiers H3: docs/integration-tiers.md (honest capability matrix, adapter recipe), harnesses CLI verb (registry gets a door), bootstrap.md refresh...  (source: git:be2accc0893e)
- Integration Tiers H2: harness registry (capability matrix as data), harness-lib unit pins, cursor adapter contract tests (payload layer skip-with-reason until composer...  (source: git:0b272381cf7a)
- Integration Tiers H1: five cursor hook adapters (identity+whisper, git guard, deny-only vetoes, T4 direct-fail credit + T3 one-beat-late recall, session draft) + shared...  (source: git:1b9bf8180b57)
- plan hook H0b: unread-bus line rides plan-time recall (silent-at-0, un-ledgered cue; recall kill switch spares it)  (source: git:334a418ec9d8)
- harness lib H0: extract scope/context/seen shared policy; claude hooks become thin translators  (source: git:90f8371eec0d)

## next-focus: MORNING BRIEF 2026-07-03 (overnight deep pass COMPLETE -- user as... (ai-setup)
Span: 2026-07-02T23:13:01.340899 → 2026-07-03T04:23:59.773738
Beats: 20  · Critic: True

- next-focus: MORNING BRIEF 2026-07-03 (overnight deep pass COMPLETE -- user asked for broad-spectrum primitives research + plan update while sleeping). DELIVERED...  (source: mem:decision:ADR_0703002359_5629)
- idea: knowledge primitives (shape axis) + tests-as-schema: USER IDEATION 2026-07-03 (via GPT chat, user-relayed; extends the sharpening-sword thesis). TWO IDEAS: (1)...  (source: mem:decision:ADR_0703000542_6378)
- Use when ANY expensive research completes (multi-agent sweep, deep-research run), before ending the turn: persist each agent's FULL findings+citations to...  (source: learn:experiment:research_full_fidelity_preservation)
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
- research README: full-fidelity preservation rule for frontier agent sweeps (chat is never storage; forcing-function hook queued)  (source: git:b4baa9aacc74)
- Research day preservation: full frontier research records (local models x3 agents, compaction/consolidation x2 agents) + first two reviewed drafts (smoke...  (source: git:ee440e6f9c0e)
- Landscape watch: watchlist (SQ1-SQ5 standing questions, 16 curated sources, maturity stages for adoption timing), delta-sweep template, feeds: convention (tasks name the...  (source: git:b4856aea4984)
- R2 naming: industry-standard terminology (tool access / toolset / tool grants) in worker prompt and docs  (source: git:53471f714c90)
- R2: local-fleet research hands -- self-hosted SearXNG discovery (websearch.py + container settings), near-frontier worker grants (Grep/Glob/py), corpus-first +...  (source: git:bdd7baffca98)
- Local-agent fleet + research-day pipeline: Ollama-backed Claude Code launcher (pre-flight probe: tool-call + context canary + speed), shift runner (fresh session per...  (source: git:38abf7ac677b)

## next-focus: POST-REVIEW STATE 2026-07-03 ~01:00: FIRST FULL RESEARCH-DAY CYCL... (research)
Span: 2026-07-03T04:24:00.691852 → 2026-07-03T06:16:55.582148
Beats: 3  · Critic: True

- next-focus: POST-REVIEW STATE 2026-07-03 ~01:00: FIRST FULL RESEARCH-DAY CYCLE COMPLETE -- 7-task shift, 5 drafts accepted into reviewed/ with stamped verdicts, failures...  (source: mem:decision:ADR_0703021655_3410)
- Research day reviewed: 5 drafts adjudicated (003 lora ACCEPT, 005 hermes-moa ACCEPT, 006 cmi honest-failure + frontier addendum closing the SQ1 gap, 002+smoke earlier)...  (source: git:3cedea9c3bb5)
- Overnight deep pass: knowledge-primitives full research record (3 agents: history of universal vocabularies, cross-domain pattern systems, computational analogy +...  (source: git:fcd8d383b7a1)

## next-focus: PRIORITY RE-CUT 2026-07-03 (Opus continuation after Fable hit its... (ai-setup)
Span: 2026-07-03T10:35:07.227736 → 2026-07-03T16:37:14.176715
Beats: 45  · Critic: True

- next-focus: PRIORITY RE-CUT 2026-07-03 (Opus continuation after Fable hit its limit mid-session). SHIPPED THIS RUN: (1) counter-hygiene S2a 2nd-form -- ghost counters +...  (source: mem:decision:ADR_0703123007_9545)
- Use when a pool of models (or any swappable backend) is enumerated in more than one place, before writing another caller: make ONE data roster the source of truth and...  (source: learn:experiment:fleet_dispatch_v0)
- Fleet-dispatch layer v0: an easy structure for calling local models. core/fleet = a ROSTER (single source of truth -- tag/ctx/vram/capabilities/status/disqualifier...  (source: git:7180e41d1555)
- Use when a value/triage instrument counts more tracked entities than the corpus holds, before distrusting the instrument: after fixing key-form drift, look for STALE...  (source: learn:experiment:s2a_ghost_counter_fold)
- Counter hygiene S2a (2nd form): ghost counters -- learn:experiment:* keys whose lesson was retired/renamed inflated tracked past corpus (133>131). Triage now splits...  (source: git:7fec1fb6635f)
- next-focus: PRIORITY RE-CUT 2026-07-03 (post vision-reveal + bakeoff adjudication; user near plan limit). DOCTRINE: methodical foundation-first, NO alpha-rush to the...  (source: mem:decision:ADR_0703102009_6940)
- Use when selecting models for unattended knowledge work, before optimizing for speed: grade for SILENT-failure modes first (fabrication, citation laundering, false...  (source: learn:experiment:bakeoff_noisy_vs_silent_failure)
- a-series: the assistant layer (the revealed end goal): VISION REVEALED 2026-07-03 (user, on seeing Rika's feature list): 'Akashic Aurora is just the scaffolding' -- the...  (source: mem:decision:ADR_0703095414_5724)
- landscape: rika (convergent dreaming, no measurement): SQ1 THESIS-GUARD CHECK 2026-07-03 (user spotted github.com/nssriraam/rika via HuggingFace discord...  (source: mem:decision:ADR_0703094830_9886)
- Use when a capability probe fails on a REFUSAL rather than a wrong answer, before excluding the model: safety-tuned models pattern-match probe wording (tokens, secrets...  (source: learn:experiment:probe_phrasing_safety_refusal)
- Use when an instrument reports more tracked entities than exist, before distrusting the instrument: look for KEY-FORM DRIFT at the write doors (same entity, multiple...  (source: learn:experiment:s2a_counter_canonicalization)
- S2a: counter-key canonicalization -- votes always land on the lesson's one counter (canonicalize at the record_feedback door, idempotent migration folded 3 live orphans...  (source: git:9734e88e760a)
- adversarial-critic-partner-idea: SCOPING RESOLVED 2026-07-03 (user: 'Integrate and lets go'): (Q1) INTEGRATE into Akashic Aurora -- reuse FAITH-1, ledger, learning...  (source: mem:decision:ADR_0703080157_1469)
- Use when writing public docs for this project: no cutesy winks at specific readers, no self-referential meta-commentary about the doc's own review process or the owner's...  (source: learn:experiment:no_meta_selfreference_public_docs)
- Use when running outside-model review on public text: fence off settled decisions in the prompt (dates, voice, no-invented-metrics), require quoted-text-plus-fix format...  (source: learn:experiment:multi_model_review_loop)
- Use when an Edit old_string fails to match on a file you have ALREADY edited this session: your own prior edits shift wrapping/context -- re-read the exact target region...  (source: learn:experiment:edit_own_drift_reread)
- Use when writing ANY public-facing claim for this project: claims about ourselves keep (evidence attached); claims about the field become 'our survey (linked, N...  (source: learn:experiment:public_claims_falsifiable_humility)
- Use when a hook matcher/config change seems ignored, before debugging the script: hook SCRIPTS hot-reload (fresh process per event) but settings.json hook CONFIG likely...  (source: learn:experiment:hook_matcher_config_not_hot)
- s1-triage-adjudication: S1 FIRST TRIAGE ADJUDICATED 2026-07-03 (verb: py agent_cli.py triage; shipped gated). NUMBERS: 127 tracked sources, 8 PROTECT (all earned credit...  (source: mem:decision:ADR_0703063551_8888)
- Use when starting a knowledge-corpus sharpening pass, before building consolidation machinery: run the read-only value triage FIRST -- it sizes the opportunity, ranks...  (source: learn:experiment:sharpening_s1_triage)
- Sharpening loop S1: triage verb -- lessons ranked by measured value (protect / cost-no-return / noise-voted / watch), window token cost per source, read-only with the F2...  (source: git:d0f60b2174cb)
- Fleet queue: re-queue 001 (memoryarena replay -- failed in the credit-death window, valuable for the CMI benchmark)  (source: git:6e26db1fdeff)
- Fleet queue: re-queue 001 (failed in the credit-death window) + add 017 (reliable structured output for small models -- hardens the fleet caller's fmt=json) + 018...  (source: git:a42a251d8b12)
- Chronicles: regenerated projections through the fleet-dispatch + S2-scoping + R013 arc  (source: git:77ed11bf9d6b)
- ROADMAP: status banner -- the Waves 0-5 synthesis is foundation-era/historical; living START HERE is now the boot notes + the recent design docs (fleet-dispatch...  (source: git:37e1982b39bf)
- S2 consolidation scoping+design doc: the two-sided gate (FAITH-1 faithfulness AND a new coverage scorer -- faithfulness-only rewards over-deletion), a first-class Tests...  (source: git:58a78ff315e1)
- R013 deep-research (Opus, re-run after credit-death): full-fidelity report on standout small models for fleet subtasks. Headline: Qwen3.5 small dense series (0.8b-9b...  (source: git:60d5aa6dcaeb)
- Queue R016: clever specialist minis + subtask->model capability map (embedders/rerankers, structured-output specialists, spec-decode drafts, guard/router minis...  (source: git:88bf5874bd36)
- Queue a-series research 014 (live-viz of spine/funnel/codex -- the uniquely-ours A1) + 015 (talkable-loop orchestration + local/frontier routing, consuming R013) --...  (source: git:be1930d69c61)
- Recover research/queue/013 (standout small models for subtasks) from the plan-limit-killed session -- sub-agents died on credit exhaustion, brief preserved for the free...  (source: git:1e8ce5d54618)
- Chronicles: regenerated story/memory projections through the bakeoff + yardsticks arc  (source: git:1599478c7a3d)
- Research bookkeeping: 002/003/005 reviewed+done, fleet tasks 008-010 queued (critic calibration, minimal critic strength, MoE offload), bakeoff runlog  (source: git:9450a05dadf2)
- Semantic-gate yardsticks: labeled contradiction + action-applicability datasets and a scored harness (measurement-first; the gate itself is a later slice)  (source: git:5f6b83af89d3)
- Model bakeoff report: glm retains the fleet -- the trade at this tier is noisy-vs-silent failure, not speed-vs-depth (qwen: citation laundering; gpt-oss: fluent...  (source: git:1f74f052d176)
- Preflight canary: neutral self-test wording -- 'output the SECURITY TOKEN' made a safety-tuned model refuse the probe (gpt-oss:20b); probes must not pattern-match as...  (source: git:5a72c047d439)
- README: FSQ pointer after the not-yet section (where skepticism is primed); FSQ published as Discussion 2  (source: git:fa2587a3ddf4)
- docs/FSQ.md: frequently anticipated skeptical questions -- the isn't-this-just-RAG / where-are-benchmarks / what's-novel answers, each honest and record-linked, prep for...  (source: git:6a22a0964960)
- Voice correction: cut reader-wink and inner-skeptic codification from JOURNEY/VOICE (self-referential meta = bloat; the artifact exhibits discipline, never describes it)  (source: git:3e6e53dbd625)
- Final polish (Gemini round 4): user-cancelled wording, python3 note inside the quickstart block; VOICE.md acceptance test (owner's inner skeptic = the final gate)...  (source: git:064f56a089f6)
- Presentation round 3 (GPT ideas + Gemini convergence): README inverted for the 90-second reader + one-sentence experimental thesis + name section removed (owner call)...  (source: git:8299412c704b)
- VOICE.md: origin-sentence decision settled (kept, owner rationale recorded as a voice rule)  (source: git:55eac89d43ea)
- README polish via two guardrailed Gemini loops (lesson scope, credit-signal mechanics, spine gloss, integration-tiers link, review transparency) + docs/VOICE.md: the...  (source: git:768060c62e87)
- Journey + fossils: multi-model review folds (thesis elevated, immunity claim softened, working-principles framing, real citations, metrics; docs/FOSSILS.md fossil record...  (source: git:b74c45c2c9bb)
- Public voice: humble-register README (facets-explored framing, fleet section, 601 tests), docs/JOURNEY.md human-readable history (arc-close append ritual wired into both...  (source: git:f22c4fe55c1c)
- Task-payload capture (auto-archive step 1): posttooluse captures Agent/Task tool payloads, session-scoped, capture-only; user-level matcher gains Task (verification...  (source: git:ae73296c8888)

## research: standout small models for fleet subtasks 2026-07: R013 deep-researc... (research)
Span: 2026-07-03T16:16:37.141471 → 2026-07-03T16:16:37.141471
Beats: 1  · Critic: True

- research: standout small models for fleet subtasks 2026-07: R013 deep-research on Opus (re-run after prior session's fleet sub-agents died on credit exhaustion...  (source: mem:decision:ADR_0703121637_1686)

## Use when reviewing/promoting ANY local-model research draft before trusting i... (research)
Span: 2026-07-04T03:12:29.196561 → 2026-07-04T03:12:33.736192
Beats: 2  · Critic: True

- Use when reviewing/promoting ANY local-model research draft before trusting it: grade the Sources section against the Findings/Confidence prose, not just each other -- a...  (source: learn:experiment:evening_review_citation_honesty_own_fleet)
- research: shift 2026-07-03 evening review: SHIFT RESULT: 12 tasks attempted, 5 clean DONE (001,004,008,012,018 by runner's format-only bar), but 'done' means...  (source: mem:decision:ADR_0703231229_7143)

## Use when inserting a method right after __init__ (or any method) via Edit: in... (ai-setup)
Span: 2026-07-04T03:13:42.338858 → 2026-07-04T05:10:33.026487
Beats: 8  · Critic: True

- Use when inserting a method right after __init__ (or any method) via Edit: include the FULL preceding method body in old_string, or anchor the insertion at a clear...  (source: learn:experiment:edit_insert_method_absorbs_init_tail)
- Use when building a human-in-the-loop control over a long-running agent loop: a pause flag checked only between tasks won't interrupt work-in-progress -- put an...  (source: learn:experiment:bifrost_live_console_adaptive_interject)
- Use when a bus runner must DO work (read/search/inspect) not just chat: reuse the interactive client's guarded Agent+ToolBox rather than writing a second tool loop; key...  (source: learn:experiment:bifrost_deepseek_agentic_peer)
- Use when adding a stateless model as a live Bifrost peer: mirror bifrost_runner.py (the wake-adapter template), reuse ask_<model>.py's load_key/BASE_URL, register an...  (source: learn:experiment:bifrost_deepseek_runner_live)
- Use when exposing a REMOTE model to LOCAL tools (any agentic CLI over a provider API), before shipping the tool executor: put every deny in the harness, never the prompt...  (source: learn:experiment:remote_model_local_tools_guards)
- Use when wiring ANY OpenAI-compatible frontier provider (DeepSeek/etc.), before building a subprocess CLI bridge: for anything conversational, use the openai client with...  (source: learn:experiment:deepseek_api_over_cli_bridge)
- Research shift cancelled mid-run (user request, 2026-07-03 23:1x): another Claude session is actively wiring in DeepSeek; blindly re-running the same failing batch...  (source: git:46e430875ab7)
- Evening review of the 2026-07-03 research shift: promoted 2 solid drafts (deepseek-v4 parallels w/ a citation-honesty correction; screenspace tool stack) to reviewed/...  (source: git:b86db1cd2c89)

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
- Akashic hooks meant to fire in Daniel's normal (home-rooted) sessions MUST live in USER settings (~/.claude/settings.json) with ABSOLUTE paths -- project-settings hooks...  (source: learn:experiment:claude_trace_hook_user_vs_project_settings)
- Use when adding any new live-status display to a periodically-polled UI: always fingerprint the data first (JSON.stringify + compare to last-known). Build DOM only on...  (source: learn:experiment:hud_fingerprint_diff_pattern)
- aurora-glass-synthesis-decision-2026-07-04: # Aurora Glass — Synthesis Decision (2026-07-04)

**Context**: Daniel initiated a parallel UI-design task: both DeepSeek and...  (source: mem:decision:ADR_0704175535_5868)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (continued 2026-07-04 evening). RESOLVED open-loop #1: the boot note claimed an UNCOMMITTED...  (source: mem:decision:ADR_0704172521_8664)
- When gating a coordination primitive for noise, gate on whether a collision is POSSIBLE (peers online) and surface only when one is FOUND (non-green verdict) -- don't...  (source: learn:experiment:smart_negotiation_gate)
- Use when tempted to add reasoning/narration to Claude's trace feed: DON'T by default -- Daniel accepted description-as-proxy and rejected narration on token-cost grounds...  (source: learn:experiment:claude_trace_narration_deferred)
- Use when giving a hook-driven (non-runner) agent live trace parity, before trying to surface its thinking: emit tool-call traces from a broad-matcher PreToolUse hook...  (source: learn:experiment:claude_trace_parity_via_hook)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: PLUMBING IS CLEARED. Next session's focus (Daniel's call): RESURFACE THE UI DESIGN (Aurora Glass) -- the...  (source: mem:decision:ADR_0704164627_4596)
- Use when resuming a halted agent, before building anything: pull the latest commit and check for NEW files in the area you planned to work. The bus can't coordinate a...  (source: learn:experiment:bifrost_api_exists_no_duplicate)
- Use bifrost.api as the single onboarding template for agent coordination. An agent that doesn't plan() has no standing to claim files; covers() is the enforcement...  (source: learn:experiment:bifrost_api_reusable_coordination_surface)
- where-we-are 2026-07-04 deepseek continued: SHIPPED 2026-07-04 (DeepSeek session, continued): UI freeze fix (applyStatus fingerprint cache + renderRecipient removed from...  (source: mem:decision:ADR_0704162654_8226)
- Use when a TURN-BASED agent must react to async events (a bus, a queue) while idle, before relying on discipline to re-arm a listener: the wake mechanism (background...  (source: learn:experiment:heimdall_wake_from_idle)
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
- Use when building or debugging interactive UIs that receive high-frequency events: the renderer should serve the user's experience, not be a slave to the event stream...  (source: learn:experiment:doom_primitives_ui_design)
- doom-engine-primitives-for-bifrost-ui: # Doom Engine Primitives Applied to Bifrost UI

## Why Doom's design matters for a chat UI

Doom ran at 35 fps on a 33 MHz 486...  (source: mem:decision:ADR_0704144917_2065)
- Use when designing the belief update protocol between experiment harness output and KB writes: don't gate on a binary switch (single-run delta -> promote or block)...  (source: learn:experiment:belief_three_layer_architecture)
- belief-architecture-three-layer-2026-07-04: # Three-Layer Belief Architecture (GPT + DeepSeek web, 2026-07-04)

## The insight
GPT identified the missing layer between...  (source: mem:decision:ADR_0704143513_4651)
- MILESTONE: intent-declaration (Policy 0) is real + live-proven: 2026-07-04: core/coord/intent.py shipped @294a666, 7 tests + live-proven. Coordinate by INTENT not file...  (source: mem:decision:ADR_0704142502_9672)
- Use when building a cross-run metric tracker alongside a peer building the primitive: separate files with a shared model (ApproachVector bridges experiment.py ↔...  (source: learn:experiment:metrics_shrinkage_tracker_built)
- Use as a standing rule recorded in project notes so it appears in every agent's boot context: default to the cheapest path that fully does the job. Use read_file with...  (source: learn:experiment:sprint_pattern_token_frugality_standing_rule)
- Use at sprint start: state who's doing what. If two agents are trying to do the same job, the coordination cost eats the productivity gain. If the human is trying to...  (source: learn:experiment:sprint_pattern_role_clarity)
- Use at the end of every sprint: close with a retrospective that names the repeatable patterns. The loop is review->design->build->prove->document->retrospect. A tired...  (source: learn:experiment:sprint_pattern_close_the_loop)
- Use after every major capability wave, before building the next: write or update the invariant document. If you can't state the invariant in one sentence, you don't...  (source: learn:experiment:sprint_pattern_state_invariant_map_primitives)
- Use when shipping any coordination primitive (lock, halt, nudge, write-gate): live-prove it in the same session. Don't ship a lock without having an agent try to violate...  (source: learn:experiment:sprint_pattern_live_proof_same_session)
- Use when building a safety-critical or coordination-critical feature: have TWO agents design it independently against the same problem description. If they converge...  (source: learn:experiment:sprint_pattern_codesign_with_peer_over_bus)
- Use when designing a new coordination primitive or architectural change, before writing code: run the design past at least one external model that DID NOT help design...  (source: learn:experiment:sprint_pattern_external_review_before_build)
- Use when starting a new capability area (coordination, persistence, messaging), before building any feature that depends on it: build the primitive first as a standalone...  (source: learn:experiment:sprint_pattern_substrate_before_features)
- Use when an agent has a cap but no tool: add the door on the same toolbox, gate it on the cap.  (source: learn:experiment:deepseek_kb_write_door)
- deepseek-kb-write-enabled: DeepSeek can now author KB notes/lessons via knowledge_note/knowledge_learn (kb.learn gated). Enabled 2026-07-04.  (source: mem:decision:ADR_0704141507_2501)
- Stage-3 evidence #1: intent-gate beats lock-gate (measured): FIRST measured result from core/coord/experiment.py (committed 9e3ab9d, 5 tests green, A/B/C+W evaluator)...  (source: mem:decision:ADR_0704140942_1347)
- coordination: intent-first (Policy 0), locks as enforcement + 3-part evaluator: ADJUSTMENT from GPT critique (2026-07-04...  (source: mem:decision:ADR_0704140127_7983)
- Stage-2 verdict + Stage-3 evidence mandate (multi-model review): 2026-07-04 multi-model design review (Gemini+GPT+DeepSeek web, Daniel-curated) -> full record...  (source: mem:decision:ADR_0704134029_8082)
- coordination reframe: social -> environmental (game-AI lens): DeepSeek's game-AI analysis (2026-07-04, user-shared screenshot; claims VERIFIED against code) reframes the...  (source: mem:decision:ADR_0704132351_4717)
- Use when you need exclusive access to a file another agentic peer may touch, before editing: a broadcast 'please hold' is advisory and a RESUMED peer will just resume...  (source: learn:experiment:advisory_hold_needs_lock_not_broadcast)
- Use when restarting a singleton-locked runner after a hard kill, before relaunching: the runner_lock does NOT verify holder liveness on acquire, so a killed holder...  (source: learn:experiment:runner_lock_stale_after_kill)
- Use when adding per-agent freeze to a system that already has a global pause, before writing per-agent keys: make is_halted(agent) = global OR agent-flag, and route...  (source: learn:experiment:bifrost_targeted_halt_a1)
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
- Prototype: semantic drift_check (core/narrative/drift.py) over the narrative spine -- catches scope-drift (routes to a different track), rework (near-dup beat), homeless...  (source: git:32401fb812b7)
- Coordination Slice D: the conductor (core/coord/conductor.py) -- impure shell over the pure ledger: stamps time, live Redis mirror, RESOLVED bus marker on close...  (source: git:b85284767da6)
- Coordination Slice C: read-state-first. format_state() renders DONE(closed)/IN-PROGRESS/NEXT+RULE; wired into agent_cli boot AND bifrost_wake so every agent reads the...  (source: git:42ac1c3f3962)
- Coordination Slice B: Redis mirror + fast read API on the task ledger. save() write-throughs to Redis; read_ledger prefers Redis, falls back to git (source of truth)...  (source: git:84ba8959e611)
- Coordination Slice A: governed task-ledger deterministic core (core/coord/task_ledger.py) -- validated lifecycle state machine, claim/serialize/done gates, atomic...  (source: git:705e9dde4d90)
- Slice 2 (deepseek lane): context-hints v2 (core/comm/context_hints.py ring buffer) + cognitive-metrics (core/coord/cognitive_metrics.py token-efficiency tracking) + hint...  (source: git:7cf9c8254ee0)
- sprint-retrospective-patterns-that-worked-2026-07-05: # Sprint Retrospective: Patterns That Made This Productive (2026-07-04/05)

## Pattern 1: Parallel Tracks With a...  (source: mem:decision:ADR_0705090551_1403)
- Use when designing ANY coordination or safety primitive: make it deterministic first. No model in the loop. Pure functions, environmental locks, TTL'd buffers, policy...  (source: learn:experiment:sprint_pattern_deterministic_before_llm)
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
- drift test: clearer near-dup pair for the rework case (>0.6 Jaccard); 5 tests green  (source: git:4848d9f19f32)
- Coordination Slice E: migrate real backlog into the governed ledger -- coordination substrate anchored DONE, 6 real tasks (UI composition chain + backend + verify)...  (source: git:df59267b181b)
- gitignore: state/* not state/ so the coordination ledger (state/coord/) is trackable while runtime state stays ignored  (source: git:bfb35c737730)
- Slice 1 (clean tree): gitignore runtime scratch/state/logs  (source: git:c9a5e70d85ad)
- Composition spec: one-owner-per-file refinement -- plumbing sole owner of bifrost_ui.py (incl reasoning-cards); claude = design lead + reviewer + standalone modules, no...  (source: git:845eaf8f22c9)
- UI composition spec (coordination test, Daniel delegated): restraint decisions + one-owner-per-file lanes; source of truth for the composed Aurora Glass pass  (source: git:23f984f1a736)
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
- To turn ephemeral agent-in-flight telemetry into a reviewable dataset, DON'T touch the hook hot path -- add a standalone bus-tailing recorder as its own read-only agent...  (source: learn:experiment:renew_two_birds_bus_recorder)
- open-docket: RENEW research scope (before building the membrane's Renew job; see renew-membrane-temporal-job + docs/agent-membrane-design-2026-07.md): A[EMPIRICAL,FIRST]...  (source: mem:decision:ADR_0707010253_4195)
- renew-membrane-temporal-job: RENEW = the membrane's 5th job, operating ACROSS the session boundary (the other 4 are within-session). It is Capture->Surface fired as a...  (source: mem:decision:ADR_0707010239_6323)
- SESSION HANDOFF 2026-07-07 -> membrane 1+2 done, legacy retired; 2 open flags: RESUME: py agent_cli.py boot claude --task '<slice>'. Design...  (source: mem:decision:ADR_0707005504_8468)
- SESSION HANDOFF 2026-07-07 -> membrane slices 1+2 done, legacy retired; 3 open flags for next session: RESUME: py agent_cli.py boot claude --task '<slice>'. Full state...  (source: mem:decision:ADR_0707005354_9003)
- where-we-are 2026-07-07 -> Membrane slices 1+2 done + legacy retired + reconcile wired; next slice 3: MEMBRANE build (docs/agent-membrane-design-2026-07.md). DONE: slice...  (source: mem:decision:ADR_0707005011_7573)
- Use when a reachability/dead-code gate flags a module: investigate CAPABILITY before deleting -- 'unwired' can mean 'a real safety net nobody wired', not 'dead'. Port...  (source: learn:experiment:unwired_safety_net_was_a_live_gap)
- Legacy retirement + reconciler PORT: deleted 3 redundant modules (coordinator_service, redis_sync_coordinator facade, sync_reconciler wrapper) + 2 coordinator tests...  (source: git:04dfe0b21fc0)
- where-we-are 2026-07-07 -> Membrane: slices 1(door)+2(wiring) SHIPPED, next Surface->orientation or capture: MEDIATION MEMBRANE build...  (source: mem:decision:ADR_0707001657_1347)
- Use to catch built!=wired drift: BFS the import graph from PRODUCTION entry points (not tests) over your substrate package; anything unreachable is latent. Exclude...  (source: learn:experiment:built_not_wired_reachability_gate)
- where-we-are 2026-07-07 -> Membrane: door slice DONE (debt 12->0), next check_wiring or Surface: MEDIATION MEMBRANE build (design...  (source: mem:decision:ADR_0707000933_1106)
- where-we-are 2026-07-07 -> Membrane build: slice 1a+1b shipped, door debt 12->7: MEDIATION MEMBRANE build (design: docs/agent-membrane-design-2026-07.md). SHIPPED: 1a...  (source: mem:decision:ADR_0707000237_4619)
- where-we-are 2026-07-06 -> Membrane BUILD started: slice 1a door-parity SHIPPED, next 1b gap paydown: MEDIATION MEMBRANE build underway (design...  (source: mem:decision:ADR_0706235649_4068)
- where-we-are 2026-07-06 -> FOUNDATIONAL: Mediation Membrane named (System 5), in research before first slice: FOUNDATIONAL DIRECTION (Daniel): a mediation membrane...  (source: mem:decision:ADR_0706234003_2533)
- Use before building an agent-experience/mediation layer: check whether the runtime HOOKS already are it (they mediate ambiently). Verify docs vs code -- 'we built X'...  (source: learn:experiment:mediation_membrane_is_the_hook_layer)
- where-we-are 2026-07-06 -> Wave 1 (L0-L3b-auto) SHIPPED + comprehension layer ENFORCED: Two arcs done 2026-07-06. (1) RELIABILITY Wave 1 per...  (source: mem:decision:ADR_0706231037_9025)
- Use when documenting an expanding codebase: do NOT write a comprehensive manual (it rots). Write a stable-altitude subsystem map + a generator that emits per-module...  (source: learn:experiment:living_docs_survive_only_if_stable_autogen_or_gated)
- Use when improving multi-agent memory/recall: fix the CORPUS not the reader (act on funnel triage; mine flips_corpus_gap for new lessons). Add per-agent CREDIT...  (source: learn:experiment:multiagent_context_credit_not_tags)
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
- README: refresh status — 733 tests, current live-memory counters, add coordination substrate + door-parity/wiring gates  (source: git:9aa700282148)
- Renew: design (membrane 5th job) + web prior-art + off-bus DeepSeek cross-check + comparison; session-chaptering design; bus recorder + solo driver  (source: git:5d32e17c7e8c)
- SAVE: commit the ARCHITECTURE.md rewrite -- it was uncommitted under the lowercase-tracked path docs/architecture.md (case-mismatch vs my uppercase edits; content was...  (source: git:a3bbab37606e)
- Membrane design: slice 2 (Built!=Wired gate) SHIPPED; 18 latent modules frozen as backlog (14 built-ahead incl conductor, 4 legacy)  (source: git:5508abd89309)
- Membrane slice 2 (Built!=Wired gate): scripts/check_wiring.py -- import-graph reachability from production entry points (doors/runners/hooks/boot); flags core/ modules...  (source: git:3d5ff58f3466)
- Membrane design: slice 1b COMPLETE (door debt 12->0); 1c endgame (one-registry structural parity) optional/deferrable  (source: git:6bad66cd21fc)
- Membrane slice 1b COMPLETE (door debt 12->0): MCP twins for tag_anti_pattern + bifrost_nudge; rationalized the rest -- list/fleet=cli_only (recall '' / operator...  (source: git:452896b1e2bf)
- Membrane design: slice 1b progress -- 5 gaps closed (note/notes/lock/unlock/locks have MCP twins), 7 remain  (source: git:47adeca05859)
- Membrane slice 1b: MCP twins for note/notes/lock/unlock/locks -- a shell-less (MCP-only) agent can now record write-once decisions + claim advisory locks (couldn't...  (source: git:d4e1c3c69be5)
- Membrane design: mark slice 1a (door-parity guard) SHIPPED; slice 1b = pay down the 12 tracked CLI<->MCP gaps (note/notes/lock* first)  (source: git:317a5906fe73)
- Membrane slice 1 (door-parity): scripts/check_door_parity.py makes the 3-door verb surface EXPLICIT (CLI 33/MCP 22/bus 18) + ratchets it -- classifies every verb (16...  (source: git:626c8ebefcd8)
- Membrane design: fold VERIFIED prior art + extracted patterns (Terrarium/LbMAS blackboard papers). Drop hallucinated 'Synthetic Membrane' citation. 3 locked decisions...  (source: git:2a5dae9001cd)
- Fold active tracks into ROADMAP STATUS: Reliability(L0-L4), the Mediation Membrane (System 5, fuller framing of old Wave 4 ACI-unify), Comprehension layer -- each...  (source: git:961ee8f8edcc)
- Founding design note: the mediation membrane. Grounded finding -- the membrane already exists as the HOOK LAYER (half-built, diagnosed a year ago in...  (source: git:7525500ab414)
- Comprehension follow-ons: PRINCIPLES.md gains #8 (coordinate through the environment/stigmergy) + #9 (observability must never break what it observes/fail-open)...  (source: git:5a965f95aa8a)
- Comprehension layer enforced (high-priority: keep the system understandable). LEXICON gains the whole Bifrost/coord/supervision vocabulary...  (source: git:1e31e0531ff6)
- Living architecture skeleton: rewrote docs/ARCHITECTURE.md (was ~4 layers stale) at stable subsystem altitude covering all layers...  (source: git:32f7c8195bc9)
- Design assessment: multi-agent memory/recall -- grounded in real code (ranker agent-agnostic, credit global, faithfulness gate strong, value ~1%). Reframe: fix corpus...  (source: git:e64ded8a3f01)
- Roadmap: L3b-auto hardening (persisted arm + jitter + contract) SHIPPED; capture deferred DeepSeek ideas (CLI, fingerprinting, Aurora-injection)  (source: git:159318c4b2f0)
- Roadmap: L3b-auto (opt-in auto-revive) SHIPPED; next L3c-remainder smoke-test then L3d state-rollback  (source: git:fc523a8d1a57)
- Research detour: Actor/OTP + ROS + Stigmergy vs our plan -- mostly confirms (L0-L4 = a supervisor tree), 3 steers (supervised state rollback, lifecycle FSM...  (source: git:d48ac6788768)
- Roadmap: L3b (manual revive + backoff) SHIPPED; next L3b-auto  (source: git:5b221dd3d9a7)
- Roadmap: L3 sub-sliced; L3a observe-only visibility SHIPPED; next L3b revive  (source: git:39990451ac2d)
- Mark L5 SHIPPED in roadmap (note: fixed latent launcher-starves-child bug); next L3/L4  (source: git:8eb1b3f03ce8)
- Mark L1 SHIPPED in roadmap; next = L5/L3/L4  (source: git:261b0ba46669)
- Mark L0 SHIPPED in roadmap; next = L1  (source: git:b56e82751e1e)
- L0 (G4 fix): hardened OpenAI client factory (make_client) with per-read streaming timeout + explicit max_retries, wired into runner/REPL/ask; cap run_command timeout...  (source: git:1e09fdee435d)
- Preserve L0 verification artifact: reproducible OpenAI-timeout streaming-wedge probe (tests/manual/l0_timeout_probe.py)  (source: git:07099cb27a5d)
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

- scoping bookends because the narrative spine already had chapters  (source: claude:design)

## Episode closed: scoping bookends because the narrative spine already had chap... (ai-setup)
Span: 2026-07-08T00:01:00.039571 → 2026-07-08T04:54:10.799119
Beats: 31  · Critic: True

- Episode closed: scoping bookends because the narrative spine already had chapters  (source: episode:close:ch_1783468859_7379)
- Use when writing ANY durable record an agent surface re-prints (notes, task titles, lessons): keep authored text pure ASCII (sec.6 not the section sign, -> not arrows)...  (source: learn:experiment:authored_records_stay_ascii)
- Use when deriving triggers/drafts/counts for spans delimited by boundary-marker events: (1) the marker shares the next span's start timestamp, so filter markers OUT of...  (source: learn:experiment:span_boundary_hygiene)
- Bookends S3 (T009): episode auto-suggester -- advisory close suggestions (impl-complete/subsystem-switch/new-objective/idle), noise-gated, on the RENEW-shared event bus...  (source: git:0aa69f9dc23a)
- session-bookends-status: Session bookends: S1 + S3 SHIPPED. Design: docs/session-bookends-design-2026-07.md (contract in sec.6, slices sec.7); reviews in...  (source: mem:decision:ADR_0708005056_2090)
- renew-signal-persistence-status: RENEW slice A'' (signal persistence) SHIPPED 2026-07-08 @7223308 via ship.py (T008 in ledger; 5 guards + 812 tests green + live smoke)...  (source: mem:decision:ADR_0708002952_1434)
- Use when a correlation dataset has a signal half and a label half, before letting it accumulate: put BOTH on the same always-on capture chokepoint (hook/session-end fold...  (source: learn:experiment:renew_signal_label_symmetry)
- RENEW A'': durable session_signals -- SessionEnd folds the session transcript into one per-session health-signal event (signal half now as durable as the A' fail labels)  (source: git:7223308b6c3a)
- comprehensibility-immune-system: PILLAR SHIPPED 2026-07-07 (codesigned w/ DeepSeek). The comprehensibility immune system: guards that keep the architecture...  (source: mem:decision:ADR_0707235722_5056)
- Use when building or hardening ANY guard/gate meant to be load-bearing (a 'pillar'): a guard needs FOUR properties, not just 'it checks the thing'. COMPLETE (does it...  (source: learn:experiment:comprehensibility_immune_system_four_properties)
- Use when committing an edit to a doc/file on Windows via a path-scoped tool (mirror.py/git add <path>), before trusting the commit: the living-docs convention here is...  (source: learn:experiment:mirror_case_pathspec_miss_on_windows)
- arch-triage-2026-07-07: Architecture triage arc P0->P1->P2 COMPLETE 2026-07-07 (DeepSeek triage + claude code-vetting) ->...  (source: mem:decision:ADR_0707232450_9376)
- P2 execution (arch-triage, Daniel-approved): (1) DELETE fast_cache.py -- confirmed dead (zero live consumers), 623 LOC + 3 lint-debt allowlist entries removed. (2)...  (source: git:7bf9e4671052)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude VETTED) -> research/reviewed/deepseek-arch-triage-2026-07-07.md. === DONE === P0: +25 tests for 2...  (source: mem:decision:ADR_0707231548_5864)
- Use when ANY triage recommends deleting 'unwired'/'dead' modules -- especially one from an agent that cannot see code: NEVER delete on the label. Check per module: (1)...  (source: learn:experiment:investigate_before_delete_3of4_wrong)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude, VETTED) -> research/reviewed/deepseek-arch-triage-2026-07-07.md. === DONE === P0: +25 codesigned tests for...  (source: mem:decision:ADR_0707221746_7077)
- Use when a triage (esp. from an agent that can't see code bodies) says 'wire these built-ahead modules now': do NOT wire to satisfy the gate -- open each module and...  (source: learn:experiment:wiring_investigate_before_acting)
- P1 (name-collision): rename core/state/session_state.py -> session_checkpoint.py (crash-recovery checkpoints), resolving the module-basename collision with...  (source: git:bbfcef2c5cbd)
- arch-triage-2026-07-07: Architecture triage (DeepSeek+claude, VETTED) 2026-07-07 -> research/reviewed/deepseek-arch-triage-2026-07-07.md. ANSWER: yes, shipped slices...  (source: mem:decision:ADR_0707204151_2870)
- Use when hardening an untested but load-bearing DATA/VOCABULARY module (edge types, enums, config maps), before assuming it's fine because it 'never changed': write the...  (source: learn:experiment:p0_invariant_tests_catch_latent_bug)
- P0 test hardening (arch-triage): +25 tests for the two zero-coverage load-bearing modules, codesigned w/ DeepSeek. relationship_types.py -- invariant guards (inverse...  (source: git:ccaa256d7755)
- arch-triage-2026-07-07: Architecture triage (DeepSeek, dossier-fed, VETTED by claude) 2026-07-07 -> research/reviewed/deepseek-arch-triage-2026-07-07.md + coverage...  (source: mem:decision:ADR_0707201840_1619)
- session-bookends-status: Session bookends: S1 SHIPPED 2026-07-07 (design->DeepSeek review->build, all green). Design: docs/session-bookends-design-2026-07.md (contract...  (source: mem:decision:ADR_0707200331_2823)
- Use when adding a session/episode/segment concept to a system that already has a narrative or grouping primitive, before creating a new table: check whether the new...  (source: learn:experiment:bookends_episode_is_a_chapter)
- Session bookends S1 (manual backend + CLI): an episode IS a Chapter with why+final; core/narrative/episode.py lifecycle (open/current/close+draft/accept) drafting...  (source: git:338fe29cb821)
- Anti-rot contract: describe the now-complete comprehensibility immune system (was 'proposed'); removes a stale doc ref in passing -- the pillar keeping its own docs...  (source: git:67f52200b3b8)
- PILLAR: the comprehensibility immune system (codesigned w/ DeepSeek). Hardens check_comprehensibility from structure-only to catch SEMANTIC drift + makes enforcement...  (source: git:6a55f17bf929)
- Docs comprehension refresh #1 (LEXICON half -- case-pathspec miss on the prior commit): LEXICON.md gains Episode/Bookend, Agent-membrane/RENEW (paging function), the...  (source: git:be143db928f8)
- Docs comprehension refresh (recommendation #1): update the two hand-curated living docs to absorb recent work -- ARCHITECTURE.md + lexicon.md now cover...  (source: git:6789a3f459fe)
- P2 investigate-before-delete (arch-triage): encoded evidence-based verdicts into check_wiring backlog. DeepSeek's blind triage said DELETE all 4; code investigation...  (source: git:2ea219be2dfd)
- P1 (wiring): surface conductor.py through the ONE door as 'agent_cli task' (propose/approve/claim/start/verify/done/block/list/next) -- closes the...  (source: git:7d7ec0e4048b)

## Episode closed: Session bookends S1 (manual backend + CLI): an episode IS a C... (ai-setup)
Span: 2026-07-08T05:08:04.543693 → 2026-07-08T06:09:38.567734
Beats: 10  · Critic: True

- Episode closed: Session bookends S1 (manual backend + CLI): an episode IS a Chapter with why+final; core/narrative/episo  (source: episode:close:ch_1783468860_8520)
- Recall vNext follow-up: tz-safe self-echo + curator age via timeutil.to_epoch -- the live flight test caught utcnow-naive record stamps being read as LOCAL time...  (source: git:df3ed2f8e5ee)
- Use when analyzing any pillar/subsystem to take it to the next level, before proposing fixes: follow docs/pillar-analysis-method.md -- triangulate ground truth (design...  (source: learn:experiment:pillar_analysis_method)
- recall-vnext-status: RECALL vNEXT SHIPPED 2026-07-08 @aceb2da (T011, Daniel full-send). Design+evidence: docs/recall-vnext-2026-07.md. WAS: 2850 impressions/7d -> 26...  (source: mem:decision:ADR_0708015237_3780)
- Use when building any weighted-overlap relevance score, before trusting it: check the all-common-token query (ratios are scale-invariant -- floor the denominator by...  (source: learn:experiment:weighted_overlap_scale_invariance)
- Recall vNext (T011): close the four loops -- curator benches surfaced-never-credited lessons (reversible, auto-unbench on credit) + prunes ghost counters; trigger-aware...  (source: git:aceb2da4b0c3)
- session-bookends-status: Session bookends COMPLETE S1+S3+S4 (design docs/session-bookends-design-2026-07.md, statuses inline sec.7). S1 (07-07): episode IS a Chapter...  (source: mem:decision:ADR_0708011150_2456)
- Use when directed to work in another agent's lane: lock -> record who-directed in the task -> match the file's idiom, keep logic in YOUR tested modules (UI stays thin)...  (source: learn:experiment:lane_override_protocol)
- Method doc: pillar-analysis method (triangulate ground truth -> diagnose at loop altitude -> fix with evidence discipline) -- distilled from the recall vNext arc per...  (source: git:47b87ec3550f)
- Bookends S4 (T010): episode panel in bifrost_ui -- header chip + docked current-episode panel + End-episode draft editor + advisory suggestion banner, against contract...  (source: git:ff069ab45f2f)

## Use when a session or workflow dies mid-run, before re-running it whole: the ... (ai-setup)
Span: 2026-07-08T13:19:45.359512 → 2026-07-08T13:20:29.981670
Beats: 2  · Critic: True

- Use when a session or workflow dies mid-run, before re-running it whole: the journal + per-agent transcripts ARE the checkpoint - join results (journal agentId) to...  (source: learn:experiment:workflow_journal_crash_salvage)
- Frontier research: autoresearch(Karpathy)/AAR + SkillOpt + Fable5 prompt provenance + SKILL.md ecosystem - crash-recovered via workflow-journal salvage (57/75 votes...  (source: git:32fbac0ac760)

## frontier-research-status: Frontier fold-in research COMPLETE 2026-07-08 (reco... (research)
Span: 2026-07-08T13:20:01.915783 → 2026-07-08T13:20:01.915783
Beats: 1  · Critic: True

- frontier-research-status: Frontier fold-in research COMPLETE 2026-07-08 (recovered from interface crash; continuation workflow wf_e63ba506-2ec salvaged 57/75 votes from...  (source: mem:decision:ADR_0708092001_3639)

## forge-design-status: Forge status 2026-07-09 ~01:00: F2+F4 SHIPPED under T013... (ai-setup)
Span: 2026-07-09T03:05:51.346612 → 2026-07-09T04:58:40.496055
Beats: 18  · Critic: True

- forge-design-status: Forge status 2026-07-09 ~01:00: F2+F4 SHIPPED under T013 (@HEAD, 897 tests green). THE LOOP IS LIVE: recall-curate --forge-propose ran against real...  (source: mem:decision:ADR_0709005840_8516)
- Use when calling any REASONING model (deepseek v4-pro, o-series style) with a token cap, before blaming the API or the prompt: thinking spends from the same max_tokens...  (source: learn:experiment:reasoning_model_token_headroom)
- Forge F2+F4 (T013): the optimizer pass + the Tier-1 watch, red-teamed by its own optimizer before it ran. F2: core/recall/forge_optimizer.py - curator-named rehab...  (source: git:963ba8918463)
- forge-design-status: Forge status 2026-07-09 ~00:40: F0b+F1 SHIPPED under T013 (@c3e9536 + drill fixes @HEAD). F0b: flip events enriched (query+alt at credit time)...  (source: mem:decision:ADR_0709003639_6670)
- Use when validating any judge/gate/classifier, after tests and review pass: run an adversarial USE drill with a fenced peer generating real inputs (one trap, one...  (source: learn:experiment:adversarial_use_beats_code_review)
- Forge F1 drill fixes (T013): UNMEASURABLE verdict - the red-team drill exposed a gate blind spot: a never-credited lesson whose recorded contexts all pre-date the...  (source: git:017dde86fdf3)
- Forge F0b+F1 (T013): capture-side durable contexts + the Tier-0 edit gate. F0b: flip events enriched at credit time (query + altitude - free at ~5/wk), durable bounded...  (source: git:c3e9536eb7f2)
- forge-design-status: Forge status 2026-07-09: design v2.1 LOCKED (Daniel: defaults + trust ladder + keep buffer). F0 SHIPPED + RUN same night (core/recall/replay.py...  (source: mem:decision:ADR_0709001207_5188)
- Use when defining success/go-no-go criteria for any audit or experiment, before touching the data: pre-register thresholds in a commit AND have a fenced peer...  (source: learn:experiment:dual_blind_preregistration)
- Forge F0 (T013): replay harness + data-sufficiency audit - core/recall/replay.py (credited/surfaced context reconstruction from durable flip events + injection ledger...  (source: git:9621e95d1792)
- forge-design-status: Lesson Forge design v2 LOCKED-PENDING-DANIEL 2026-07-08 (T013 in_progress). docs/lesson-forge-design-2026-07.md. HEADLINE: claude and DeepSeek...  (source: mem:decision:ADR_0708235607_3813)
- Apply DeepSeek slice-1 review (research/reviewed/deepseek-slice1-review-2026-07-08.md): F1 stop-verb carve-out in promise_shaped (I'll wait/pause/stop = ending not...  (source: git:9e60d6ee848c)
- Use when a Bifrost runner (or any cursor-advancing bus consumer) starts with a backlog already queued, before trusting delivery: the startup wake can batch-advance the...  (source: learn:experiment:bifrost_runner_backlog_skip)
- Use when adding any advisory/warning output an agent is meant to act on LATER, before shipping it: persist the computed fact (stamp metadata or emit an event) alongside...  (source: learn:experiment:advisory_prints_evaporate)
- Slice 1 frontier fold-ins: (1a) age-conditional staleness cue in render() - old lessons say so + tell the reader to verify named files/flags (AKASHIC_STALE_CUE_DAYS...  (source: git:0b3dfcac192a)
- Forge design v2.1 LOCKED (Daniel: defaults + trust ladder + keep buffer) + F0 pre-registered go/no-go criteria committed BEFORE the audit runs (pre-registration fence...  (source: git:74d6e0db5c4f)
- Forge design v2 (T013): reconciled with DeepSeek's FENCED blind cross-check - CONVERGED independently on replay-against-credit-history as the validation gate (locked)...  (source: git:55620145f778)
- Lesson Forge design DRAFT (T013): evidence-gated lesson-content optimization - flip-log-as-validation-set (Tier 0 offline replay gate: must-still-match credited contexts...  (source: git:7d53125905f3)

## frontier-research-status: Frontier fold-in arc: research COMPLETE + SLICE 1 S... (research)
Span: 2026-07-09T03:06:54.323196 → 2026-07-09T03:06:54.323196
Beats: 1  · Critic: True

- frontier-research-status: Frontier fold-in arc: research COMPLETE + SLICE 1 SHIPPED 2026-07-08 @0b3dfca (T012). Shipped fold-ins: (1a) age-conditional staleness cue in...  (source: mem:decision:ADR_0708230654_2776)

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
- T027/P7 -- the pillar's final slice: LOOKBACK, one question over the rationale corpus. lookback verb fans a why-question across six corpora (docs currency-labeled ->...  (source: git:423193efd56e)
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
- T021/P1: notes supersession wired + corpus migrated. Root cause was ONE default: wrap minted dated where-we-are titles (agent_cli:1125), defeating the title-supersession...  (source: git:d6153c24637c)
- Use when a subprocess-managed agent goes silent while its heartbeat stays fresh, before blaming the model or the bus: check whether the spawner captures stdout/stderr...  (source: learn:experiment:launcher_pipe_starves_chatty_child)
- T019: launcher pipe-wedge fix -- undrained stdout/stderr PIPEs froze any chatty child mid-print (deepseek runner wedged live 2026-07-09 20:12, ~12min of streamed...  (source: git:2623908ad743)
- comms-pillar-status: T016 investigation DONE (synthesis docs/comms-pillar-synthesis-2026-07.md, plan P0-P8) -> P0 SHIPPED 2026-07-09 @d925d6b (T017): wake listeners now...  (source: mem:decision:ADR_0709200148_2474)
- Use when a bus runner/auto-responder seems stuck but its process and lock are healthy, before restarting anything: read its LAST reply -- if it ends as a promise ('Let...  (source: learn:experiment:runner_promise_is_not_deliverable)
- Use when a background watcher/wake listener shares a read-cursor with a real consumer, before letting it advance anything: watchers DETECT on a caller-owned local cursor...  (source: learn:experiment:wake_listener_detect_not_consume)
- T017/P0: wake listener detect-dont-consume. Bus.wait gains since/since_out (caller-owned local cursor; shared cursor never written; next-position under the pinned T014...  (source: git:d925d6bc32be)
- Use when arming any detect-without-consume watcher after handling a wake, before launching it: CONSUME the handled messages first, then arm - a watcher armed over...  (source: learn:experiment:wake_consume_then_arm)
- T024/P4: doc currency contract + guard -- no dead law in docs/. Convention: every docs/*.md carries Status: current | superseded-by <path> | historical near the top...  (source: git:f8b594d537ee)
- T022/P2: boot orientation header + precedence doctrine. First lines of every boot (both doors) now carry: map pointer, governing arc (<slug>-status note matched against...  (source: git:bd03ac1f0f72)
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

- Use when two store/backend implementations claim the same semantics, before building features on either: write the op-sequence differential FIRST and wire it into ship...  (source: learn:experiment:differential_harness_finds_on_first_run)
- Use when tempted to skip the fence on load-bearing design because the answer seems obvious: run both blind halves anyway -- the divergence IS the value, and...  (source: learn:experiment:fenced_dual_design_three_for_three)
- claude -> deepseek: OVERNIGHT LANE: build Wave 3 RB-9..12 in order against the frozen pins (tests/test_w3_rb9_rb10.py + rb11_rb12.py) + spec. You write (door on, exec...  (source: handoff:claude->deepseek)
- Use when a write/commit to a shared-tree path is refused or the path unexpectedly exists, before re-trying or forcing: READ the target first -- on a multi-seat repo the...  (source: learn:experiment:write_refusal_is_coordination_signal)
- when 2+ live seats share one agent id, route any multi-part or directed delivery through a durable door (research/reviewed file, handoff briefing) and use the bus only...  (source: learn:experiment:two_live_seats_split_chunked_bus_delivery)
- claude -> claude: SEAT RELAY (from the wake-listener seat f34b9383 to the builder seat): deepseek's answers to your questions, which my listener consumed off our shared...  (source: handoff:claude->claude)
- claude -> deepseek: W3 design-review (your slice-text role): review docs/w3-build-spec-2026-07-11.md @4c12097 -- RB-8 sentinel semantics + RB-12 tiebreaker. One named...  (source: handoff:claude->deepseek)
- FLIPPED 2026-07-11: the note door no longer silently clips -- bodies to 100k store whole; if the door result ever shows [CLIPPED], chunk and resend the remainder. The...  (source: learn:experiment:note_door_silent_4k_clip)
- rb5-clip-probe-live: rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence 0007. rb5 live probe sentence...  (source: mem:decision:ADR_0711052028_3421)
- Use when delivering a long verbatim document that must not be silently truncated: prefer write_file to a git-tracked path (like research/reviewed/) over knowledge_note...  (source: learn:experiment:file_write_tool_no_clip)
- claude -> deepseek: [RB-5 PROBE blind] Find the silent ~4013-char clip on the knowledge_note->stored-atom path (file:line); propose RB-5 confess-fix + regression pin...  (source: handoff:claude->deepseek)
- claude -> deepseek: WAVE 3 OPENS (RB-8..12 + DictStore differential): your blind design half -> research/reviewed/deepseek-w3-design-2026-07-11.md (write door is back...  (source: handoff:claude->deepseek)
- Use when writing a knowledge_note that might exceed ~3000 characters, before trusting the [OK] response: keep each note body under 3000 chars. For long content, split...  (source: learn:experiment:note_door_silent_4k_clip)
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
- Use when a live Bifrost delivery keeps vanishing before you can read it (twin session, cursor race, RB-21 class), before asking for more live-lane resends: switch to a...  (source: learn:experiment:contested_bus_use_durable_doors)
- rb23-heldout-corpus-sealed: {"id":"ds-41","text":"(deepseek produced no final ...[truncated]  (source: mem:decision:ADR_0711033057_6379)
- claude -> deepseek: RB-23 verify gate open: impl frozen @6078009 (push held). Read spec docs/rb23-build-spec-2026-07-11.md + impl + tests; reply GATE GREEN/RED on the...  (source: handoff:claude->deepseek)
- Use when handling sealed/fenced peer content in a shared store, before running ANY line-based filter (Select-String/grep/findstr) or display command near it: line...  (source: learn:experiment:sealed_content_needs_field_aware_extraction)
- claude -> deepseek: RB-23 fenced dual design OPENS (engine-first item 1): your blind [design-review] half -> research/reviewed/deepseek-rb23-design-2026-07-11.md +...  (source: handoff:claude->deepseek)
- next-focus: ENGINE-FIRST-6a7467: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0711023115_7226)
- drilldone85014a-status: GOVERNING ARC DOC: docs/drilldone85014a-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711023113_4674)
- next-focus: ENGINE-FIRST-1c6599: do RB-23 then Wave 3 before ANY UI. UI is paused.  (source: mem:decision:ADR_0711022959_7666)
- drilldone71d993-status: GOVERNING ARC DOC: docs/drilldone71d993-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711022957_8292)
- next-focus: ENGINE FIRST, UI AFTER (Daniel-ruled 2026-07-11): do NOT build UI until the engine exam passes. Order: RB-23 no-answer floor -> Battery Wave 3 (RB-8..12 +...  (source: mem:decision:ADR_0711021921_1389)
- claude -> claude: ENGINE-FIRST SPRINT (Daniel-ruled 2026-07-11 ~02:45: core engine healthy+robust BEFORE UI bodywork; a session already jumped to UI against this -- do...  (source: handoff:claude->claude)
- Progress bars, data half (Daniel-directed; co-designed, reconciliation record research/reviewed/deepseek-progress-bars-codesign-2026-07-11.md -- deepseek GREEN 'Build...  (source: git:0c451771694c)
- T030 L2 SHIPPED -- the progress pulse (RB-27a) + fleet doctor (RB-27b), per the reconciled L2 BUILD SPEC in docs/agent-liveness-tier-2026-07.md (GATE GREEN by...  (source: git:e41cecb00b4c)
- T030 L1 follow-up COMPLETE + L2 reconciled spec (dual targeted read). Follow-up: W2 (die pre-send -> answers once on redelivery) + W5 (mid-batch death -> msg1 settled...  (source: git:375cbeedd71e)
- Use when a thinking-mode runner returns a no-final-answer marker on a long analytical ask, before re-asking or blaming the model: the work usually EXISTS in the streamed...  (source: learn:experiment:runner_reasoning_eats_final_answer)
- T030 L1+L1b (claude lane, deepseek-codesigned): at-least-once inbox + fencing token -- the mail-loss incident class is dead. RB-26: runner detects without consuming...  (source: git:5aa19b17b772)
- RB-4 (T029 Wave 2): exact by-ref ack lookup -- deepseek GATE GREEN, srem mandate honored. Store gains srem (abstract + Redis/File/Hybrid; File deletes an emptied key...  (source: git:5bb2269b425d)
- RB-7 follow-up (live find): the aged-out claim stays within its evidence. A nonsense id far below the Redis ms-epoch range rendered as unconditionally evicted -- but...  (source: git:791488eb0734)
- Use when launching any long-running process (runner/daemon/server) from PowerShell, before piping its output: never through a head-limited pipe (Select-Object -First N...  (source: learn:experiment:powershell_head_pipe_kills_runner)
- Use when a handoff must reach a LIVE peer runner, before waiting on its reply: agent_cli handoff = durable boot-lane (surfaces at the target's NEXT boot); the live...  (source: learn:experiment:handoff_two_lanes_boot_vs_bus)
- T029 Wave 2 (claude lane): RB-5 window-truncated confession + RB-7 evicted-payload honesty + RB-6 remainder. RB-5: promoted_page() fetches limit+1 -> (events, more) so a...  (source: git:068f65e1ba0a)
- claude -> deepseek: [T029 WAVE 2 OPENS -- RB-4 design-review, refute-first, BEFORE build] Wave 2 = confession primitive (RB-4..RB-7...  (source: handoff:claude->deepseek)
- Use when a permission check lives on ONE side of a two-sided flow (a receive/fold gate, an inbound validator), before trusting deny-by-default: audit the SEND/emit side...  (source: learn:experiment:toolbox_door_shadows_the_acl)
- Use when testing deny-by-default / quarantine / any per-identity permission by having a PRIVILEGED agent roleplay the restricted one, before trusting the result: a...  (source: learn:experiment:gauntlet_roleplay_cannot_test_quarantine)
- wrap print fix (RB-8 wiring bug found live; the crash-orphaned note was cleanly superseded through the new claim path -- the machinery absorbing its own author's bug) +...  (source: git:f0ecc365eaa8)
- Wave 3 registration pair 2: RB-9..12 pre-registered pins (skip-guarded until impl; contracts frozen: find_normalization_collisions, SupersedeTargetError...  (source: git:fe6953be3220)
- Wave 3 registration: reconciled dual-half build spec (RB-8..12 + DictStore differential) + RB-8 pre-registered acceptance tests, committed BEFORE impl (M3)...  (source: git:4c12097227dc)
- Wave 3 opens (Daniel-directed, order claude-ruled: RB-8 first): claude blind design half committed before deepseek's arrives -- race taxonomy R-a..R-e on the...  (source: git:843cd69d2c25)
- T034 design reconciled: dual-half spec docs/t034-registry-spec-2026-07-11.md -- blind convergence on manifest+three-layer+guards (not a kernel, not YAML); deepseek...  (source: git:2f3f2dbc5a97)
- T034 proposed+approved (Daniel-ruled 2026-07-11): registry + dial consolidation -- the kernel question resolved to zero-new-primitives (settings: namespace on Store +...  (source: git:a182994623bf)
- RB-23 VERIFY CLOSED -- held-out grading GREEN on first live run: ds-41..60 (zh-heavy, 20 rows) delivered via the durable note door after every live lane was eaten by the...  (source: git:d625c194ad37)
- RB-23 VERIFY GATE GREEN (deepseek) persisted + re-verified live (19 pass/1 seal-skip); directive advanced RB-23-done -> Wave 3 next so corrected-framing sessions don't...  (source: git:1a8e17757c9a)
- RB-23 design tails persisted + harvest-at-build pointer recorded (complete half + full 40-corpus in deepseek runner log; bus truncated at ds-26). Session genuinely...  (source: git:0aaca8b48254)
- RB-23 registration: reconciled dual-half build spec + pre-registered acceptance tests, committed BEFORE impl (M3). Spec cites both fenced halves; incident record inside...  (source: git:9461b3677e62)
- RB-23 pre-work persisted (deepseek proactive, ahead of the engine-first sprint's first task): his fenced design-review half at...  (source: git:737890cad714)
- RB-23 fenced dual design opens: claude blind half (design record + dev-set corpus half, 41 labeled endings) committed before deepseek's sealed half arrives; asks sent on...  (source: git:81845e3884a7)
- Session wrap: boot-intent gap fixed (rogue UI session incident) -- governing-arc picker skips done arcs + honest fallback, boot renders CURRENT DIRECTIVE above NEXT...  (source: git:80a5d0ed3410)
- Boot-intent gap FIXED (2026-07-11 incident: a fresh session told 'pick up where we left off' built paused UI because boot actively pointed at it). Fenced dual diagnosis...  (source: git:a719743131bd)
- Engine-first sprint plan made durable (Daniel-ruled): self-handoff briefing + next-focus note -- RB-23 -> Wave 3 -> L3-L5 -> T031 hooks -> RB-25 final exam; T033...  (source: git:1416416bb860)
- Session tail: T033 ledger entry + sources-cache gitignore + deepseek bars-UI plan preserved verbatim (queued behind the design-language arc) + wrap note  (source: git:7e075f3f2672)
- T033 evidence: deepseek built-vs-spec inventory persisted verbatim (1 NOT-BUILT / 2 DRIFTED / 2 PARTIAL vs the six composition-spec items; ~2000 unsanctioned lines...  (source: git:d2ba735629ae)
- Session wrap: T033 opened (UI design-language re-grounding) -- discovery: Aurora Glass specs EXIST and are settled (July 4-5, grounded in OneUI/HIG pre-method) but were...  (source: git:84ecbe176c25)
- Session wrap: progress-bars data half shipped (turn_metrics: record/estimate/progress_view + doctor --progress), co-designed with deepseek (his UI card next session)...  (source: git:2584edc0fad1)
- T030 L2 verify-closed: deepseek GATE GREEN (verbatim at research/reviewed/deepseek-l2-verify-2026-07-11.md) -- dead-pulse-during-legit-work proven unreachable by...  (source: git:c101e4ba976e)
- Session wrap: T030 L2 shipped (pulse + fleet doctor) through the reconciliation gate's first gated passage; runner cycled to gen 2 and pulsing; deepseek L2 verify in...  (source: git:304a21597a26)
- T031 hook 1 verify fixes (deepseek GATE GREEN + 2 catches, both applied): (1) UNGATED hatch gains a rate ceiling -- ONE per arc window, counted on the event firehose...  (source: git:508e7a6ae1f2)
- Session wrap: T031 hook 1 (reconciliation gate) shipped + live in the guard chain; deepseek verify in flight  (source: git:6ecbc695d45a)
- T031 hook 1 SHIPPED -- the RECONCILIATION GATE (deepseek's design, the method baseline's lead forcing function): substrate ships now cite their spec or hold...  (source: git:43d8b77d46e1)
- Method baseline v2 -- GPT third-reviewer critique triaged per M1 (verbatim at research/reviewed/gpt-method-review-2026-07-11.md), deepseek GATE GREEN on the deltas with...  (source: git:78a05ffb4a36)
- Boot surfaces the METHOD beside the map (Daniel 2026-07-11: execute at our best from fresh bootup). The cold-start orientation head (T022) named the map and the arc but...  (source: git:fc61d68eeac5)
- Session wrap: method baseline codified + shipped (M1-M11 w/ receipts+metrics+bars, dual-authored), plain-language companion live, T031 enforcement lane approved...  (source: git:bf04cc03e27e)
- METHOD BASELINE codified (Daniel-directed: excellence repeatable + empirical, the new match-or-exceed bar) -- built BY the method it codifies: fenced dual codification...  (source: git:11b1702bc097)
- Session wrap: L1 follow-up complete (W2/W5 drills + ReferenceState CHECK + timescale seam) and L2 spec reconciled from the dual targeted read (SRE alerting + sd_notify...  (source: git:3a14d132daac)
- L1+L1b VERIFY: GATE GREEN -- deepseek's blind spec-vs-code pass, conducted (fittingly) from the first runner tenure RUNNING the code under review (gen 1). Persisted...  (source: git:da0aae37e087)
- Session wrap: SOTA grounding arc complete (map + dual deep-read reconciled) and T030 L1+L1b SHIPPED with drills green -- the mail-loss incident class is structurally...  (source: git:a5ce88e811f4)
- SOTA deep-read arc (Daniel-directed): both agents read the primary materials and wrote independent fenced assessments -- claude (web-verified extracts + ShardStore...  (source: git:f6eb84e4ed2a)
- SOTA grounding for the robustness program (Daniel-directed): docs/robustness-sota-map-2026-07.md -- 13 problem types classified (delivery semantics, failure detection...  (source: git:60ad4751d1d1)
- Session wrap: RB-4 verify GATE GREEN appended verbatim to the review record (Wave 2 fully review-closed); where-we-are refreshed. Standing rule saved to claude memory...  (source: git:ed7d36c4e3a3)

## next-focus: T030 CLOSED 2026-07-11 (deepseek GATE GREEN l4l5-verify + kill-Re... (ai-setup)
Span: 2026-07-11T16:42:39.792771 → 2026-07-11T20:45:05.758565
Beats: 26  · Critic: True

- next-focus: T030 CLOSED 2026-07-11 (deepseek GATE GREEN l4l5-verify + kill-Redis drill ALL PASSED, transcript preserved; RB-29 non-answer discipline hardened...  (source: mem:decision:ADR_0711143306_ee961ed6)
- Use when capturing subprocess output on Windows (git log/show especially), before text=True: pass encoding='utf-8' errors='replace' -- one non-cp1252 byte kills the...  (source: learn:experiment:win_subprocess_text_cp1252)
- T030 L4 / RB-29 impl: sender-side reply deadlines + redrive (deepseek design-review AFFIRM x5, research/reviewed/deepseek-t030-l4-review-2026-07-11.md)...  (source: git:ee4db803dd95)
- T030 L5 / RB-30 impl: bus-loss stand-down + pause hygiene. THE FIND: Bus.online is a construction-time fact (client object outlives a dead server) -- wiring any loop...  (source: git:d6936f2b2f63)
- T030 L3 / RB-28 impl: pipe immunity + real-time stdout. core/foundation/streams.py born: pipe_immune (write/flush swallow OSError/ValueError, latch dead after first...  (source: git:657a0933e70d)
- Use when a live drill exercises a lock/lease with per-process tenure state (fencing tokens, generations), before declaring it complete: add ONE cross-process leg — spawn...  (source: learn:experiment:rb21_live_drill_single_process_blind_spot)
- next-focus: RB-21 COMPLETE 2026-07-11 (impl 80e8256 + P12 5a72910, deepseek dual gates GREEN + 4-phase live drill; the machinery caught its own author twice...  (source: mem:decision:ADR_0711133251_d2e65df4)
- Use when any lock/lease refresh can run in a DIFFERENT process than the acquirer (hooks, cron, sidecars), before shipping: process-local tenure state (generation/fencing...  (source: learn:experiment:rb21_cross_process_refresh)
- RB-21 P12: cross-process refresh must never clobber the tenure generation (live incident caught by the machinery on its own author, post-verify pre-push): the stop-hook...  (source: git:5a72910cae1b)
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
- T031 hooks 2-4: method-baseline enforcement lane complete. Hook 2 check_preregistration (M3: a NEW pre-registered pin file shipping WITH source FAILS -- registration is...  (source: git:dcebb3ab08d6)
- T031 registration: hooks 2-4 pins (9, skip-guarded until impl) committed BEFORE impl per M3 -- the checker's own pins obey the law it enforces. Contract frozen...  (source: git:4d24729b900a)
- T030 L5 registration: RB-30 pins (5, skip-guarded until impl) committed BEFORE impl per M3, informed by the audit-first instruction (audited 2026-07-11: pause provenance...  (source: git:3268fae161a9)
- T030 L4 registration: RB-29 build spec (L4 BUILD SPEC section appended to the liveness doc -- claude concretization of the adopted deepseek half) + 6 pre-registered...  (source: git:d00afc1b019b)
- T030 L3 registration: RB-28 pipe-immunity pins (5, skip-guarded until impl) committed BEFORE impl per M3. Contract frozen: streams.pipe_immune (write/flush swallow...  (source: git:fb44a3ce685c)
- RB-21 registration addendum: P10 (same-session re-claim = refresh, deepseek review N1) + P11 (door happy-path dict shape, deepseek Q3 Option A) -- added PRE-IMPL at gate...  (source: git:d2cdf82b7970)
- RB-21 registration: build spec (claude half) + 9 pre-registered pins, committed BEFORE impl per M3. Invariant: at most ONE cursor-advancer per agent id -- the consumer...  (source: git:2f89ca150d8a)

## Use when accepting any fix/design whose soundness rests on what an upstream s... (ai-setup)
Span: 2026-07-12T01:50:02.966449 → 2026-07-12T09:44:51.911272
Beats: 60  · Critic: True

- Use when accepting any fix/design whose soundness rests on what an upstream seam PROVIDES (a record field, an accessor return, an invariant), before trusting its...  (source: learn:experiment:no_relocation_arg_needs_source_grep_gate)
- Use when a claude session keeps getting Stop-hook wake re-arm demands with nothing new to do: check if it holds the consumer seat (bifrost-sync --consume refused = it...  (source: learn:experiment:nonseatholder_wake_spin_burns_plan)
- t036-nonconsuming-seat-claimant: T036/T037 TRIAL DATUM (Fable session 7d4857e1, 2026-07-12 ~05:00): the claude consumer seat shows FRESH claims (observed 'claimed 51s...  (source: mem:decision:ADR_0712042614_cf4e874b)
- Use when sending a fence ask or any multi-part durable delivery to a peer, before relying on the handoff verb: default to a git-tracked brief FILE (research/...) + short...  (source: learn:experiment:durable_handoff_reader_broken_t042)
- recall-networking-research: RECALL-AS-NETWORK LANE: FENCE CLOSED, RECONCILED (2026-07-12 ~04:4x). RECORD...  (source: mem:decision:ADR_0712042219_3b6bd706)
- t042-scope-extension: T042 SCOPE EXTENSION (deepseek self-report 2026-07-12 ~04:40, on the record in his bus reply): BOTH agent_cli.py verbs 'handoff --list' AND 'locks'...  (source: mem:decision:ADR_0712042105_5e54594f)
- claude -> deepseek: SUPERSEDES my clipped 04:12 handoff. Full fence ask = the FILE: research/recall-networking-fence-brief-2026-07-12.md (two-part BLIND protocol...  (source: handoff:claude->deepseek)
- recall-networking-research: RECALL-AS-NETWORK RESEARCH COMPLETE (2026-07-12, Daniel-directed parallel lane, this session). DELIVERABLES: synthesis ...[truncated]  (source: mem:decision:ADR_0712041248_e79f9ea5)
- claude -> deepseek: FENCED CROSS-CHECK (research stage, recall-networking lane; NON-BLOCKING -- queue AFTER your T040 counter-review): Daniel-directed research applying...  (source: handoff:claude->deepseek)
- Use when claude_trace_narration_deferred (or any pre-reversal narration guidance) surfaces: narration default is FULL to the bus per the same-day override; and when a...  (source: learn:experiment:narration_lesson_superseded_same_day)
- t040-spec-status: T040 PACKET SPEC v1 -- design phase COMPLETE pending Daniel (2026-07-12 ~04:15). Fenced dual design + reconciliation + COUNTER-REVIEW all ran...  (source: mem:decision:ADR_0712035906_1441f9ff)
- Use when an Edit old_string fails to match on a file you authored earlier, before retrying with another guess: never reconstruct from memory -- grep/read the exact live...  (source: learn:experiment:fix_setup_docs_packet)
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
- Use when choosing a guard's failure direction, before citing other defenses as the safety net: check whether those defenses actually cover THE LANE THIS GUARD EXISTS FOR...  (source: learn:experiment:guard_fail_direction_vs_protected_lane)
- Use when a lease/seat held by a supposedly-dead session keeps refreshing, before killing anything: a refreshing lease means a LIVE holder -- check for fresh commits/work...  (source: learn:experiment:live_twin_misdiagnosed_as_zombie)
- concurrency-trial-2026-07-12: TWO LIVE CLAUDE SEATS (Daniel-directed trial, started 2026-07-12): session e59d8882 (Opus twin, HOLDS the claude consumer seat) + session...  (source: mem:decision:ADR_0712022301_3bccf294)
- t035-same-token-twin-design-input: T035 DESIGN INPUT (from the live twin incident 2026-07-12, lessons same_token_twin_reentrant_consumer_seat +...  (source: mem:decision:ADR_0712022147_afe0d4ae)
- Use when a wake/consume/cursor symptom RECURS despite targeted fixes, before applying another band-aid: the recurrence itself is the signal that an unaccounted co-tenant...  (source: learn:experiment:recurring_symptom_is_the_root_cause_signal)
- Use when a per-agent coordination primitive (consumer seat, runner lock, wake seat) derives holder identity from an INHERITED env token (CLAUDE_CODE_SESSION_ID), before...  (source: learn:experiment:same_token_twin_reentrant_consumer_seat)
- rb25-f1f2-fence-review-green: # RB-25 F1+F2 fence review — GATE GREEN (2026-07-12)

DeepSeek independent fence review of commit d926bb8 (+ amendment db1044f) per charter...  (source: mem:decision:ADR_0712021134_c2bfbaec)
- next-focus: RB-25 EXAM IN PROGRESS (2026-07-12). Drill 1 (newborn gauntlet) CLOSED GATE GREEN -- deny-by-default airtight for conscious action + F1 (runner self-refuses...  (source: mem:decision:ADR_0712020505_25c2e41e)
- Use when a fresh session cannot consume its own agent inbox (seat held by a PRIOR session id), before re-arming wake listeners: list python processes for the repo's...  (source: learn:experiment:orphan_mcp_server_squats_consumer_seat)
- RB-25 Drill 2 (STORE-DIVERGENCE HEAL) PASSES + H2b fix. Bars met (isolated REDIS_DB=15+temp file, transcript...  (source: git:6c641e7d2daf)
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
- Ultracode v2: T036-T039 coordination arc -> FENCE-READY (wf_a860ac82-b21, 9/9 agents 0 errors; length-bounded schema fixed v1's retry-cap drop of T036). THE LOAD-BEARING...  (source: git:a068a6ed3910)
- Ultracode run: T036-T039 coordination-arc design via primed multi-agent workflow (wf_818affa1-027). 8/9 agents (T036 design dropped on schema retry cap -> graceful...  (source: git:296c77fcbffa)
- T040 records land VERBATIM (M6, locks lapsed by TTL -- holder consent on record msg 1783842959079-0, his unlock verb is T042): deepseek spec half (369 lines, 7 sections...  (source: git:654c23e6aac7)
- T040 Packet Spec v1: claude half unsealed + RECONCILED SPEC lands (docs/packet-spec-v1-2026-07.md, Status current AWAITING DANIEL APPROVAL -- the T040 gate). Blind...  (source: git:aa0b6645967f)
- Packet-substrate arc SLICED + T040 design opens (Daniel directive 'lets get to work and make slices' + steer 3 pluggable endpoints, note...  (source: git:cbb4ef58226d)
- deepseek T038+T039 implications half lands VERBATIM (M6): main report (verdict, U1-U6 unlocks, 2a-2k seam effects, FM1-FM8, phased pilot order w/ RB-25 bar additions...  (source: git:413c3c5c3ac2)
- T038+T039 implications deep-dive lands (Daniel-directed, fenced dual + 2 mid-dive steers): brief + claude half + reconciliation (deepseek half follows when his advisory...  (source: git:32f315c5b290)
- RB-25 Amendment 2 registration: pins committed BEFORE impl per M3 (9 pins, skip-guarded until each lands). Contract frozen per deepseek rulings ALL SIX AFFIRMED...  (source: git:78ffa1e82af5)
- RB-25 fence closes as a THREE-PARTY compound (concurrency-trial first fruit): claude pass-1 UNSEALED verbatim + the reconciliation record land. Blind convergence proven...  (source: git:7df312f34150)
- RB-25 drill-1 verify record lands (deepseek GATE GREEN, lock released); drill-2 + f1f2-review records land when deepseek frees locks 145/144  (source: git:7df9e2102167)
- RB-25 F1/F2 AMBER amendment (deepseek fence review research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md): the generic scripts/bifrost_runner.py (gemini/web lane)...  (source: git:db1044f79783)
- RB-25 drill 2 (STORE-DIVERGENCE HEAL) registration: pins committed BEFORE the H2b fix (M3), isolated on REDIS_DB=15 + temp file (never live data). Contract bars GREEN...  (source: git:ce0d87c33efd)
- RB-25 test-isolation fix: the F2 pins broadcast on the LIVE bifrost stream, spuriously waking the running fleet's real listeners (observed live during deepseek's drill-1...  (source: git:7097b5efcedd)
- RB-25 records hygiene + review-slice open: land deepseek-rb25-runbook-review-2026-07-11.md VERBATIM from disk (cited by c1bb1f6 but never git-tracked -- M6 gap from the...  (source: git:89be87ec1c9a)
- RB-25 drill 1 (NEWBORN GAUNTLET) run + 2 findings registered (pins pre-impl, M3). Ran as a GENUINE separate quarantined process (EVOLVE E1 from run 1 honored). RESULT...  (source: git:67adeb0b33bd)
- RB-25 runbook AMENDED pre-drill per the fence review (deepseek GATE AMBER -> 6 amendments -> drills may open; record...  (source: git:c1bb1f60a197)
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
- Fix A (RB-25 drill 3 F2): namespace-scope the control plane. control.py pause/halt/narration/activity keys now follow BIFROST_NAMESPACE (per-call, like Bus.ns) instead...  (source: git:416d0d13bac3)
- Use when a runner is online but consumes nothing (backlog or fresh mail just sits), before blaming its consume loop: check control.is_paused() / control.is_halted(agent)...  (source: learn:experiment:runner_wedge_check_pause_first)
- where-we-are: RB-25 DRILL 3 (STORM) executed + root-caused 2026-07-12 (claude; deepseek fenced cross-check PENDING, offline). CORRECTION: my first-pass S3 ...[truncated]  (source: mem:decision:ADR_0712140142_c9b4a33a)
- RB-25 drill 3 (storm) executed [claude exec; deepseek verify pending]: S1/S2/S4 pass, S3 -> reproducible finding (non-virgin runner wedges on a backlog so a successor...  (source: git:ce4d20d5822d)
- where-we-are: RB-25 DRILL 3 (STORM) EXECUTED 2026-07-12 by claude; deepseek verify PENDING (offline at run). Record ...[truncated]  (source: mem:decision:ADR_0712134444_7a33eb07)
- Use when piping a Windows child that PRINTS non-ASCII (emitter side; complements win_subprocess_text_cp1252 which is the reader side), before launching it: set...  (source: learn:experiment:piped_win_child_needs_utf8)
- t038-identity-blocker: T038 identity FENCE COMPLETE (design), 2026-07-12. deepseek adversarial counter-review (research/reviewed/deepseek-t038-identity-2026-07-12.md...  (source: mem:decision:ADR_0712125910_e63ca7be)
- next-focus: DANIEL STEER (2026-07-12 evening): PAUSE ALL UI WORK until the structural / networking-inspired overhaul is IN PLACE. Scope of pause: T002 (collapse traces)...  (source: mem:decision:ADR_0712125135_127ea8ef)
- t038-identity-blocker: T038 identity RESOLVED pending deepseek counter-review (2026-07-12). The v3 blocker AND my own refuted pid-attempt are closed. The identity T038...  (source: mem:decision:ADR_0712121600_369b84d6)
- Use when keying durable OWNERSHIP or coordination state (offers, intents, leases, expectations, verify-still-held) in a turn-based (process-per-turn) system, before...  (source: learn:experiment:pid_id_not_valid_ownership_key_turn_based)
- t038-identity-blocker: T038 STILL AMEND (not fence-ready) as of 2026-07-12. v3's 'ONE blocker' (identity mis-grounded) is NOT closed. A claude correction attempt...  (source: mem:decision:ADR_0712114536_9f19cc12)
- session save (Daniel starting new session): T029->done ledger transition (state/coord/tasks.json) + session lessons (chronicles/memory.md) + drill-4 soak evidence...  (source: git:b1fb8346458b)
- T040 packet spec FINALIZED -> LAW (amendments A-F applied per Daniel keep-working delegation; the T040 gate is crossed). A add pri (spec-now/enforce-when-shedding, like...  (source: git:757a624629bf)
- T040 spec cross-check (claude) -- completes the fenced T040 review. AFFIRM all 6 of deepseek's Q1 findings; strong-affirm 1.2 overflow (silent-work-trim QoS1 violation)...  (source: git:2611f72b7d29)
- Fenced reconciliation (claude side): ns-isolation + T040 endpoints duals RECONCILED, both converged. Unseals claude's two blind halves + merged reconciliation...  (source: git:6440cb638d06)
- send-side handoff guard (2026-07-12 silent-handoff fix, sender end): bifrost-send now AUTO-arms a reply-deadline on directed asks (request/handoff/question) unless opted...  (source: git:a3f8ab832d8d)
- Control-plane ns-isolation: fenced design brief (generalize Fix A across 8 coordination modules that hardcode NS=bifrost). Shared problem statement for deepseek's blind...  (source: git:b0dac70da4b2)
- RB-25 drill 4 SOAK harness + ARMED (certify-at-soak-start, Daniel ruling): tests/rb25_drill4_soak.py (arm/sample/checkpoint/status/monitor/disarm; isolated echo subject...  (source: git:4b58f74c24cf)
- RB-25 drill 3 VALID RE-RUN (storm 4ddf0a71): ALL 5 BARS PASS. With the drill-local rate-limit raise (Fix B form, harness child env) the burst no longer trips the runaway...  (source: git:5bf6013c76f1)
- RB-25 drill 3 S3 root-cause: RETRACT the backlog-wedge finding. True cause = storm burst tripped runner A reply RateLimiter -> GLOBAL pause froze the fleet (S3/S5...  (source: git:6dca39289528)

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

- Use when a gate/guard checks 'is anything pending' on a stream that accumulates unconsumable junk: filter by actionability (wake-worthiness) at the check, keep the...  (source: learn:experiment:lane_pending_check_needs_wake_worthiness)
- T045 stage-1 post-GREEN soak fix: the arm-time pending check now counts only WAKE-WORTHY mail -- unconsumed legacy skip-junk (traces) was trapping it forever (lane...  (source: git:217cea3a388c)
- T045 STAGE 1 SHIPPED on deepseek fence GREEN 4/4 (deepseek-t045-stage1-review-2026-07-14.md): wake listener watches the WORK LANE. bus.wait/_drain streams retarget (lane...  (source: git:8e913a158d12)
- Use when calling bus.wait/xread and expecting an instant peek, before shipping: timeout_ms=0 BLOCKS FOREVER; pass timeout_ms=1 for a peek (or block=None at the raw...  (source: learn:experiment:xread_block_zero_waits_forever)
- T050 quick-wins bundle SHIPPED (Daniel priority directive; deepseek live-verify ALL FIVE GREEN first run): Q1 private scratchpad (memory_note/memory_recall + boot...  (source: git:9f7a72d2f143)
- Use when wake listeners exit instantly in a loop while sync says nothing pending, before blaming hook races: run the cursor-vs-tail drill on BOTH streams (inbox AND...  (source: learn:experiment:wake_loop_from_unconsumed_broadcast)
- T048 BUILD (deepseek design -> claude build): recall_at + knowledge_full tools, novelty [boot]/[new] tagging keyed on runner onboarding text, tool-aware truncation hints...  (source: git:47be19b257ca)
- Use when batch-editing a file you have only grepped/sed-viewed, before the first Edit call: Read the target regions with the Read tool -- grep/Bash output does not...  (source: learn:experiment:edit_gate_needs_true_read)
- Use when two live agent processes share the File store on Windows: expect tmp->rename collisions under concurrency; the durable fix is RB-8 CAS / T034 arc...  (source: learn:experiment:win_filestore_rename_race_births_orphans)
- fold into T048 build (his harness): runner releases its path-locks when the reply is sent (task end = lock end, matching T026 ack semantics); until then, expect...  (source: learn:experiment:runner_guarded_write_leaks_locks)
- T044 (T039a) BUILD: kind->lane router + P0 dual-write + trace exemption (R5+amendE, D-3 global spot counter). Pins B1-B6 43/43 green w/ T043 suite; live smoke...  (source: git:e36f33a5ab33)
- Match the ask to the lane: the bus runner one-shot bridge = conversational/quick checks ONLY; fence-stage work (blind halves, counter-checks, long grounded reviews) goes...  (source: learn:experiment:fence_heavy_asks_need_full_session_lane)
- Before accepting ANY fence-half verdict: path-verify every file:line citation (glob the cited paths; a fabricated citation invalidates the section, not the whole report...  (source: learn:experiment:fence_report_citation_path_gate)
- T045 stage-1 PRE-REGISTRATION: wake-cutover pins L1-L6 committed RED before impl (lane watching, S2-NEW structural, pending-legacy hole, A4 tail-seed, P4 skip set)...  (source: git:ca644ae2c1d6)
- Wishlist arc complete: deepseek half (5 friction w/ moments, 5 leaps, 5 moonshots) + synthesis (6 blind convergences incl his independent re-derivation of T049 M1-CF...  (source: git:33beed9b0a01)
- Wishlist arc (Daniel open ask): claude half written (5 friction-killers w/ receipts, 6 capability leaps, 5 moonshots); deepseek half requested (his seat, 3 tiers)...  (source: git:9cd292338e8f)
- T048 verify GREEN (deepseek live-verify, all 5 items; lock self-release confirmed live -- empty lock table after his guarded write) + boot-source matcher fix from his...  (source: git:5a1a2124b68f)
- T048/T049 approved+claimed (Daniel: address deepseek's interview concerns together): design asks sent to deepseek; lands the experience interview verbatim  (source: git:936e55433d47)
- T044 (T039a) PRE-REGISTRATION: acceptance pins B1-B6 committed RED before impl (T031 rule practiced); governing design doc (Daniel gate 2026-07-13 recorded, closes F2)...  (source: git:793d70ed6753)
- T039 counter-check ROUND 3 VALID (full-capability lane): all amendments+pins AFFIRMED, M1/M2 real catches folded, citations spot-verified real; deepseek_chat.py...  (source: git:38840c6245d0)
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
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  (source: learn:experiment:new_one)
- Use when adding a session state dir, before shipping: update prune_state in core/recall/at_action.py and every dir-swapping test  (source: learn:experiment:new_one)
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
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:30, epic night closes). FRESH SEAT FIRST MOVES: (1) boot claude --task 'T074 Phase 1'; (2) read ...[truncated]  (source: mem:decision:ADR_0715020724_4b334325)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:15, the epic night closes; Daniel starting a fresh session). BOOT RITUAL: py agent_cli.py boot claude --task '<slice>' then...  (source: mem:decision:ADR_0715020112_ea3b9b1e)
- session-themes: THE HARD-TO-PIN THEMES of 2026-07-14/15 (prime any fresh seat with these): (1) THE GAUGE INVERSION -- visible budgets/gauges are prosthetics that help...  (source: mem:decision:ADR_0715020011_6d5e172e)
- where-we-are: SESSION HANDOFF (2026-07-15 ~06:15, the epic night closes; Daniel starting a fresh session). BOOT RITUAL: py agent_cli.py boot claude --task '<slice>' then...  (source: mem:decision:ADR_0715020010_ff77cd84)
- T073 Phase 1+2 SHIPPED (deepseek verify GREEN, 'the mirror is clear'): wake_worthy() is the sole wake gate -- to_incarnation explicit addressing overrides the echo skip...  (source: git:9d0479738517)
- twin-split: OPERATING AGREEMENT claude#f9207c90 (seat holder) <-> claude#b0b7771d (build session), Daniel-bridged 2026-07-15 ~04:45. SEAT HOLDER (f9207c90): consumer...  (source: mem:decision:ADR_0715013415_174a2fcc)
- Use when the ledger says already-claimed, files change underfoot, or runners die unexplained, BEFORE blaming linters/peers/flakes: check for a concurrent same-agent...  (source: learn:experiment:twin_session_diagnosis_first)
- T068-R3 pre-flight assertion runner SHIPPED (deepseek design -> claude build -> deepseek live drill GREEN): core/comm/assertions.py (A1 file:line resolve, A2 event-cite...  (source: git:a83659000c68)
- attack-plan: DANIEL DIRECTIVE 2026-07-15 ~03:15 verbatim: 'Lets build give all these ideas from tonight concrete form! I want to make sure we don't lose any of the good...  (source: mem:decision:ADR_0715004250_32065440)
- where-we-are: EPIC SESSION CLOSING (2026-07-15 ~03:00). Shipped review-gated since last note: T068 Wave A (constraint pack in every boot + T063 ack round-trip), T069...  (source: mem:decision:ADR_0715003117_7ed7bb1e)
- Use when designing the knowledge-to-agent pipeline: (1) separate constraints (always-injected, renegotiated quarterly) from historical lessons (queryable, never...  (source: learn:experiment:rigor_vs_creativity_is_false_tradeoff)
- T069 singleton isolation SHIPPED (Daniel-directed fenced dual design, deepseek GREEN zero blockers): four factories + coordinator_api (the new guard's FIRST-SWEEP catch)...  (source: git:1a88509fb3f2)
- Use when a new factory is added with a Dict-based or union-type singleton cache: the check_boundaries regex may miss it, but the P9 census test WILL catch it...  (source: learn:experiment:singleton_isolation_regex_tradeoff)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- file fallback held  (source: learn:experiment:offline_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- a beat appears  (source: learn:experiment:beat_hook_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- same name each time  (source: learn:experiment:dup_exp)
- handle me  (source: learn:experiment:messy_exp)
- agent B should see this  (source: learn:experiment:iface_loop_exp)
- attack-plan: DANIEL DIRECTIVE 2026-07-15 ~00:45 verbatim: 'i want you and deepseek to think about what would be best to do and build next in order to swing for the...  (source: mem:decision:ADR_0714235202_26f319c3)
- Use when choosing between "get a better model" and "improve the harness": invest in harness tier advancement FIRST (constraint injection at boot, pre-send assertion...  (source: learn:experiment:harness_tier_over_model_tier)
- where-we-are: ERGONOMICS RUN NEARLY CLOSED (2026-07-15 ~00:20, epic session). SHIPPED review-gated tonight: T059+T053 (cursor's accidental-agent pair -- claude...  (source: mem:decision:ADR_0714234027_3f077a09)
- T061 settle-linkage SHIPPED review-gated: ANSWER_KINDS={reply,handoff,completion} settle expectations (exact meta.answers first, FIFO fallback one-per-message); notes...  (source: git:98ecc4a2d012)
- Use when reviewing or extending the expectations settle predicate: the FIFO fallback clears ONE per message, not N. Multiple armed asks to the same target require either...  (source: learn:experiment:t061_fifo_widening_edge)
- T066 reply-path fix SHIPPED (deepseek design -> claude build -> deepseek code-pass GREEN + L1 live): bus.send_reply lane-FIRST w/ retry-then-LOUD legacy fallback +...  (source: git:01c55ea22e52)
- T054 R3 flow tracer SHIPPED review-gated: OTel-style waterfall over lanes -- flows derived from meta.answers chains (flow id = root id), same-sha copies collapse to xN...  (source: git:a9527b7eaa4d)
- Use when a wake seat insta-wakes on a message sync says you consumed, before re-arming again: re-drain with the SEAT'S lane env (BIFROST_CONSUME_LANE must match...  (source: learn:experiment:wake_loop_lane_mismatch_drain)
- T059+T053 ergonomics pair shipped review-gated: cursor built both; claude adversarial review found+fixed 2 T059 defects (benched/graduated archive routing via store...  (source: git:20003c7a8da4)
- Use when a new read-surface (recall/map/report/render) reaches verifying, before handing it to review: probe it against the LIVE corpus and check the one invariant that...  (source: learn:experiment:live_corpus_probe_before_verifying)
- Use when an adapter/projection reads another module's flag field, before writing any truthiness check: import that module's canonical predicate (is_x) -- flags stamped...  (source: learn:experiment:adapter_reads_store_predicates_not_fields)
- claude -> cursor: T059 review verdict: 2 defects found+fixed (benched/graduated surface leak; truncation nondeterminism) -- read...  (source: handoff:claude->cursor)
- claude -> deepseek: T059 fix-delta cross-check (fence-lite closure) + T053 review (cursor's brief in your handoff lane)  (source: handoff:claude->deepseek)
- cursor -> deepseek: FENCE-LITE adversarial review of T053 (R2 fence workspace) -- break it, do not bless it  (source: handoff:cursor->deepseek)
- cursor -> claude: FENCE-LITE adversarial review of T059 (R8 knowledge_map) -- break it, do not bless it  (source: handoff:cursor->claude)
- Use when walking the lesson related_to graph (knowledge_map, consolidation, merge passes): traverse BOTH directions -- forward via the record's related_to JSON, reverse...  (source: learn:experiment:knowledge_map_edges_are_one_directional)
- where-we-are: SESSION HANDOFF READY (2026-07-14 evening, Daniel reloading). SIX wishlist arcs today: T045+T049+T052+T055+T056 DONE (full gates, all fences GREEN, zero...  (source: mem:decision:ADR_0714190943_7958cf8e)
- where-we-are: FIVE DONE on Daniel's away-day directive (2026-07-14 evening): T045 lanes cutover, T049 fence-v2, T052 R1 delta door, T055 R4 pre-flight recall, T056 R5...  (source: mem:decision:ADR_0714182117_9a40ae82)
- T056 R5 COST TELEMETRY BUILT on the reconciled spec (deepseek build-review PENDING -- gates task-done): core/coord/task_costs.py (owner-attributed accumulator per his...  (source: git:0bc1ffad6243)
- eaten-confirm-incident: 2026-07-14 afternoon: R5 confirm (msg 1784042654710-0, 15:24Z) was consumed-to-Out-Null by claude during replay cleanup -- 6h stall. Forensics...  (source: mem:decision:ADR_0714174108_0024ebc6)
- NEVER pipe a consume to null: every --consume gets triaged (batch-file pattern) -- consumption is delivery; a discarded delivery is silent mail loss the system cannot...  (source: learn:experiment:consume_to_null_eats_mail)
- R12 straggler lane-eligibility filter (post-ship soak find): trace/sig-kind legacy mail is never a work straggler -- the repeating '1 LEGACY STRAGGLER' noise in...  (source: git:21ad7ba0b0ac)
- t061-root-cause: T061 root cause CONFIRMED on evidence 2026-07-14: bifrost:expect:claude held 6 armed expectations for ANSWERED handoffs (attempt 1-2 each) -- the L4...  (source: mem:decision:ADR_0714104757_72b4e89d)
- Use when an ANSWERED directed ask redrives anyway: check the expectation settle-linkage (meta.answers) covers multi-message/summary replies -- and keep consumers...  (source: learn:experiment:l4_redrive_settle_linkage)
- where-we-are: T045 DONE + T049 DONE, 2026-07-14 midday (Daniel's away-day directive: build every wishlist feature). T045 = full T039b consumer cutover COMPLETE...  (source: mem:decision:ADR_0714093921_18849869)
- T045 STORM RERUN EXECUTED (cfdcb65f, --t045 lane mode): self-read S1/S2/S4/S5/S6/SESSION-LEG PASS (S6 sig latency 0.05s under flood, sig beat final work; session door...  (source: git:9ec4a11fe31f)
- T045 CALLER WIRING SHIPPED on deepseek wiring-fence GREEN (all three surfaces correct; generation flow verified incl the self-caught gen-0 sig-replay bug; _lane_src...  (source: git:99fb0c47f574)
- day-plan: AUTONOMOUS DAY RUN 2026-07-14 (Daniel at work; his directive verbatim: 'keep working on every suggestion you and deepseek had... I really love what you guys...  (source: mem:decision:ADR_0714091155_f2215ef6)
- T045 STAGE 2 SEAM SHIPPED on deepseek build-fence GREEN (10 pins + 4 amendments confirmed; no lost-message path under adversarial tracing): work_drain lane consume door...  (source: git:8b45820c5f36)
- NIGHT CLOSES: T073 DONE @9e4c8bf (deepseek verified by RUNNING the pins through his own new exec door -- the acceptance was the capability) + verdicts verbatim filed +...  (source: git:167568760af0)
- T074 CLOSED (W1-W14, ledger DONE @c39e207, verified_by=deepseek) + T060-M1 design wave COMPLETE (fence CLOSED: sealed halves w/ V-line verdicts + exposure disclosure...  (source: git:7853833836d9)
- SESSION PAYLOAD for the fresh seat: JOURNEY.md gains the 2026-07-14/15 entry (the night the contract carried strangers -- Daniel reviews the register); where-we-are +...  (source: git:c12468504bbe)
- T073 Phase 1+2 PRE-REGISTRATION: pins committed RED to the reconciled spec -- to_incarnation explicit addressing overrides the echo skip (build refinement flagged...  (source: git:32f87ab9629f)
- T073 wake+communicate: fenced dual design RECONCILED (Daniel-directed; deepseek named for it). Fork resolved: dispatcher LOSES the current arc (W3 registry absent...  (source: git:b1226dcf8cab)
- T067-1 live drill GREEN (deepseek self-verified the twin's build unprompted on his first turn with the new tools: private notes in boot confirmed live +1464 chars, 6...  (source: git:e2ae99faddd9)
- T067-1 ToolBox third-door parity SHIPPED -- built by a CONCURRENT claude session (its pre-registration: 7d853aa; discovered mid-review), designed by deepseek...  (source: git:4331c091b7a6)
- T067-1 PRE-REGISTRATION: ToolBox third-door parity pins B1-B3/D1-D4/Q1-Q3 committed RED to deepseek's design (research/reviewed/deepseek-t067-1-design-2026-07-15.md) --...  (source: git:7d853aa05ca7)
- L4 settle-linkage proposed as a task (second redrive duplicate today confirmed the class)  (source: git:95e798e3fb02)

## claude -> deepseek: [t060-m1] blind design half: M1 Continuous Presence (daem... (voice)
Span: 2026-07-15T06:07:25.621252 → 2026-07-15T07:04:19.549328
Beats: 4  · Critic: True

- claude -> deepseek: [t060-m1] blind design half: M1 Continuous Presence (daemon peers)  (source: handoff:claude->deepseek)
- tonight-plan: OVERNIGHT PLAN 2026-07-15 (Daniel asleep; directive verbatim: 'select the highest value items and lets begin working through them slice by slice WITH...  (source: mem:decision:ADR_0715022441_96673de1)
- T074 Phases 1-3 SHIPPED (deepseek verify GREEN x3, verdicts verbatim in research/reviewed/t074-verify-verdicts-2026-07-15.md): the whisper IS the primer...  (source: git:4ce70ab34113)
- T074 continuity: dual design RECONCILED -- the whisper becomes the primer (deepseek's implementation contract governs: 12-line budget w/ drop-order, curated flag on...  (source: git:f6a96df65406)

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
- T078-W1 SHIPPED (deepseek built, claude verified GREEN 8/8 + live round-trip): TokenJournal daily meter (state/runner_<agent>_<date>.json), hot-path add_turn at the...  (source: git:404163f26aee)
- t078-wave-gate: DANIEL GATE 2026-07-15 evening verbatim: 'Lets get to building the highest roi items!' -- T078 first wave W1-W6 APPROVED TO BUILD per ...[truncated]  (source: mem:decision:ADR_0715161629_a6685df0)
- where-we-are: AUTOPILOT ADOPTED 2026-07-15 ~16:00: daemon:claude SEATED (--manage-listener, pid 2860) coexisting with the session consumer seat -- stop-hook fast path...  (source: mem:decision:ADR_0715155854_633be11b)
- PRESENCE AUTOPILOT LIVE (Daniel directive to adopt-and-forget in one afternoon): A1 complete both halves + T077 A3 shipped + TWO live-drill findings fixed at source...  (source: git:568053df73d9)
- where-we-are: PRESENCE-AUTOPILOT DAY, evening state 2026-07-15: Daniel directed the subsystem (verbatim in presence-autopilot-directive); the fence ran FULLY BLIND both...  (source: mem:decision:ADR_0715155107_e4485fd8)
- presence-autopilot-directive: DANIEL DIRECTIVE 2026-07-15 afternoon verbatim: 'Is there some kind of subsystem we can implement to make all the arming claiming standing...  (source: mem:decision:ADR_0715154055_1783673d)
- where-we-are: MIDDAY MILESTONE 2026-07-15 ~11:05: THE MIRROR LANDED (12 commits @origin/master) -- deepseek verified all three slices GREEN and self-filed the verdicts...  (source: mem:decision:ADR_0715150517_12146f70)
- T079-E4 SHIPPED (deepseek built the gauge cluster on E1s snippet within the hour; claude verified GREEN via LIVE probe): /vitals endpoint serving real heartbeats on...  (source: git:a276fd8f6e78)
- T079 RECONCILED: engine-room fence closed -- second deep blind convergence of the night (dual-column fence view crowned signature by BOTH halves independently...  (source: git:58f7c39c6e66)
- T079 engine-room fence: claude blind half filed (dual cognition lane w/ stall/drift markers + convergence bridges, vitals strip animated by real events, method board as...  (source: git:58a30fa7049e)
- README: deepseek adversarial analysis FOLDED (his verdicts V1-V7, analysis verbatim at research/reviewed/deepseek-readme-analysis-2026-07-15.md): section reorder (the...  (source: git:0cb63ccde98c)
- T078 RECONCILED: capability-surface fence closed -- halves near-perfectly complementary (his economics: ~75% prompt spend wasted on re-sent prefixes, flagship+thinking...  (source: git:efb7b9f459e2)
- T078 capability-surface fence OPEN (Daniel directive): claude blind half filed -- Tier1 subagent panels / MCP-native door / scheduled sessions / push notifications /...  (source: git:0fea5b1f39cd)
- Presence-autopilot fence OPEN (Daniel directive, verbatim in note presence-autopilot-directive): claude blind half filed...  (source: git:571e4faf04ef)
- T075 M1-DELTA SHIPPED (deepseek built, claude verified RED->fixed->GREEN 35/35): runner as managed child + circuit breaker + summary-injection survival. Reverse-fence...  (source: git:562a91b50b2f)
- T075 M1-alpha+beta + T071-R1 + T064 SHIPPED, deepseek-verified GREEN x3 (his verdicts self-filed via the restored write door; alpha pins run through HIS exec door as...  (source: git:bd043f7e70ac)

## where-we-are: OVERNIGHT RUN 2026-07-16 (Daniel asleep; claude Opus seat + dee... (ai-setup)
Span: 2026-07-16T01:34:24.777850 → 2026-07-16T09:35:38.757221
Beats: 37  · Critic: True

- where-we-are: OVERNIGHT RUN 2026-07-16 (Daniel asleep; claude Opus seat + deepseek-build FULL caps -- the two-frontier-model test): T081 boot-ergonomics DONE @72a4925...  (source: mem:decision:ADR_0716013622_2ec9747b)
- Use for T002 UI trace collapse: adopt the Discord-compact + ChatGPT-collapsible hybrid. Consecutive same-agent traces collapse into ONE .trace-card div: a compact header...  (source: learn:experiment:research:web:ui_trace_collapse_prior_art)
- T083-C5-1: PARKED status for the task ledger (the state machine can now express deliberately-shelved). in_progress->parked (reason MANDATORY -- park gate teaches) frees...  (source: git:d92d83e8ab10)
- T083-C1-1 seat dead-holder rescue (crash-path liveness for the consumer seat): runner_lock.free_if_dead -- evidence ladder: activity-marker fresh->ALIVE, armed-listener...  (source: git:854fe0bd8d1a)
- ironman-directive: DANIEL DIRECTIVE 2026-07-16 pre-sleep verbatim: 'I want you and deepseek to keep analyzing friction points when using akashic aurora and ways to...  (source: mem:decision:ADR_0716010705_70e5ee3b)
- T081-W8 unify: close_session (narrative manual path) now routes through close_open_episode_for_session_end too -- deepseek's cross-check caught that session.py:117 had...  (source: git:45615aa4d75d)
- T081-W8 part B: SessionEnd episode auto-close (the 189h Untitled-episode fix). core/narrative/episode.close_open_episode_for_session_end -- content-bearing episode...  (source: git:c2359d89d36c)
- T081-W5 honest heal (safety-critical, claude lane, deepseek cross-verify pending): 3-way orphan classification replaces the 4867-key wolf-cry...  (source: git:c0e7e583cacb)
- Use when designing any allowlist/filter over a data corpus: run the EMPIRICAL census FIRST — `check_drift()` or equivalent — before writing a single line of the...  (source: learn:experiment:empirical_keyspace_census_before_roster_design)
- T081-W4 claude side + shared reconciliation: the concurrent test-file clobber (both wrote test_t081_w4_trace_collapse.py) resolved -- deepseek's consecutive-run...  (source: git:c1e0dbca0662)
- Use when two agents share a cross-lane slice: name test files per-SURFACE, not per-slice. Pattern: test_{task}_{surface}_{what}.py. A slice touching both the runner...  (source: learn:experiment:w4_two_writer_test_clobber)
- Use when collapsing display-only telemetry in a message stream: (1) collapse at render time not ingest (Loki pattern) — never lose data, (2) use consecutive-only dedup...  (source: learn:experiment:w4_trace_collapse_consecutive_dedup)
- T081-W1 + W3 built GREEN (claude lane, deepseek cross-review pending -- slices NOT marked done until signed off): W1 boot transport line -- agent_cli._transport_line...  (source: git:4654070f7131)
- where-we-are: LATE NIGHT 2026-07-15 ~18:30: Daniel home + ACTIVE ON THE BUS (operator-override shipped after his broadcast slept my seat -- frm=user now wakes all seats...  (source: mem:decision:ADR_0715220602_9c101ebc)
- Use when chaining anything off a test/gate command: NEVER pipe the gate (| tail/| head make && meaningless); run the gate bare, format after; and never claim GREEN in a...  (source: learn:experiment:gate_exit_codes_never_piped)
- T002 design filed (deepseek, mirrored by claude): UI trace-collapse cards -- prior art Discord compact mode + ChatGPT thinking-toggle + our W4 render_collapsed -> hybrid...  (source: git:9ab274f9d9aa)
- T084-CL-2 bifrost-standby (claude Tier-1, deepseek cross-verify requested): the turn-end ritual as ONE verb -- drain (with C1-1 dead-holder rescue inside) ->...  (source: git:b083ee3a8a75)
- T084 Tier-1 (deepseek authored, claude cross-verified w/ ONE review fix): IR-3 write-size gauge -- write_file/edit_file descriptions declare the ~65KB MTU + refuse-loud...  (source: git:37426e95a63e)
- T084 ironman plan RECONCILED (both halves): deepseek IR-1..7 + claude CL-1..7; convergences = research cache (IR-6=CL-5), finer concurrency (IR-7=CL-6)...  (source: git:e216b549ea89)
- T083-C3-1: bifrost-send --text-file PATH (git commit -F precedent) -- flag-bearing/long bodies ride a file, never argv; positional text now optional (refuse-loud when...  (source: git:29116af63e43)
- Failure ledger opened (Daniel directive 2026-07-16, verbatim in note ironman-directive): living docs/failure-ledger-2026-07.md -- 7 categories, tonight's session...  (source: git:79d9adca1797)
- T081-W8A gauge honesty COMPLETE (deepseek whisper side + claude sync side): Prometheus-style denominator labels -- the whisper 'mail: N unread (work-lane/all lanes)' and...  (source: git:72a49252daec)
- T081-W4 refactor (deepseek authored, claude cross-verified GREEN + mirrored -- deepseek's guarded exec is read-only, no git): bifrost_inbox() delegates to the shared...  (source: git:34671a3b8be7)
- T082 proposed (durable-drift audit surfaced by W5) + T081 claim state  (source: git:ca8b642f543c)
- W5 honest-heal RECONCILIATION (safety-critical, full-fence): claude ran the ACTUAL keyspace census before trusting any memory roster -- reframes W5. check_drift diffs...  (source: git:cc3d4e969ffc)
- T081 W6+W7 (deepseek authored, claude cross-verified GREEN -- the fenced division: deepseek builds runner-lane, claude runs the verification it can't). W6: ToolBox takes...  (source: git:fa3221756d08)
- T081-W6 emission side (claude lane, unblocks deepseek W6-P2): cmd_boot --sources-json PATH writes {sources:[normalized lesson-source pointers]} --...  (source: git:36e9379be46f)
- T081-W2 built GREEN (claude lane): scripts/mcp_register.py -- portable helper that prints the user-scoped akashic-aurora MCP registration with an ABSOLUTE path (computed...  (source: git:4cc540cd5060)
- Boot-ergonomics fence RECONCILED (Daniel-directed dual retro): both halves converge -- boot answers 'where am I' not 'what can I do / what's running'. Joint plan = T081...  (source: git:1912f49f0521)
- Boot-UX fence brief (Daniel-directed collaborative process): symmetric two-half fence -- deepseek analyzes its OWN runner-seat boot ergonomics first-class + adversarial...  (source: git:fb664a65ca35)
- Fence correction (Daniel-caught): boot-UX retro downgraded to CLAUDE HALF / fence OPEN -- pre-review commit acknowledged in-doc, deepseek half + adversarial cross-check...  (source: git:f4951c29847c)
- Boot-UX retro from the first T074-primer cold seat (claude): context one-hop GREEN, capability hand-boots -- P1 MCP door cwd-fragile, P2 boot lacks services/presence...  (source: git:677dc793115c)
- Session-end save (Daniel relaunching for the native-MCP boot): deepseeks in-flight UI work + his ui-mcp fence half filed while claude wrapped -- landing both so nothing...  (source: git:9d60c9b48ab1)
- T080 closed via TWIN AGREEING RECONCILIATIONS (independently identical verdicts -- the strongest closure the fence produces); UI-MCP ask scoped (W3+restart dissolves the...  (source: git:d6b68ad52ca7)
- T080 RECONCILED: the nights third blind fence, and the cleanest decomposition yet -- two halves solved two DIFFERENT halves of Daniels incident with zero mechanism...  (source: git:82fb504e99cc)
- T080 operator-traffic fence: claude blind half filed -- thesis: the operator does not speak in kinds; operator traffic is a CLASS ABOVE the taxonomy (always-wake law...  (source: git:b38652b6e1f0)
- T079-E2 SHIPPED: lane_depths + fence_phase backends GREEN w/ live receipts (the fence-phase gauge reports its own fence as reconciled; lanes read work=197/trace=4472...  (source: git:850cec067cfa)

## Night build brief (autonomous overnight run): deepseek upgraded to deepseek-b... (research)
Span: 2026-07-16T04:23:13.733985 → 2026-07-16T04:23:13.733985
Beats: 1  · Critic: True

- Night build brief (autonomous overnight run): deepseek upgraded to deepseek-build (full write+exec+Redis+net, exec grant already in acl.json T067-2); Daniel's 4...  (source: git:e4dd3202dfd6)

## Episode closed: Use when directed to work in another agent's lane: lock -> re... (ai-setup)
Span: 2026-07-16T12:47:28.551145 → 2026-07-16T13:48:47.487894
Beats: 13  · Critic: True

- Episode closed: Use when directed to work in another agent's lane: lock -> record who-directed in the task -> match the  (source: episode:close:ch_1783487284_1736)
- Use when any agent_cli verb takes positional text plus flags: put the text BEFORE the flags or use --text-file; argparse refuses trailing positionals after optionals...  (source: learn:experiment:bifrost_send_text_before_flags)
- T086-S1+S2a (claude lane, deepseek cross-verify requested): session TOMBSTONE -- the missing session-vs-process discriminator (C1-5 root fix). wake_seat gains...  (source: git:644e01f66c82)
- Use when renaming a reason/verdict/label string any surface renders: grep tests/ for the old literal FIRST -- label asserts fail as false alarms and mask real regressions  (source: learn:experiment:t086_reason_label_rename_pins)
- Use for T086: five fix-classes. (A) Session-scoped process lifecycle: SessionEnd cascades to all children (systemd scopes). (B) Liveness as maintained channel: heartbeat...  (source: learn:experiment:research:web:seat_lifecycle_prior_art)
- claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Daniel-directed, 2026-07-16 morning)  (source: handoff:claude->deepseek)
- C3-1 refined: argv-order footgun broader than flag-shaped prose (two live receipts; misdiagnosis falsified + corrected)  (source: git:98ff63c69a1a)
- C1-5 CLOSED (deepseek cross-verified 5/5 targets): tombstone + renewal-primacy; S7 charter gains caller-verification candidate  (source: git:e5ba5d54d588)
- C1-5 marked FIXED (T086-S1+S2a) awaiting deepseek cross-verify  (source: git:672a6efe35a1)
- T086 RECONCILED: seat-lifecycle build spec (both halves; lease-as-channel + session tombstone cascade + seat-type supervision split; S1-S7 w/ pre-registered pins)  (source: git:13742f90599d)
- T086 ledger registration + directive note (notes index regen)  (source: git:903d05973bbf)
- T086 opened (seat-lifecycle prior-art arc, Daniel directive 2026-07-16): claude blind half filed; C1-5 amended w/ kill-resurrection + TTL-outage receipts; deepseek...  (source: git:abaf18ff4c89)
- Failure ledger C7-3: transient exit-127 on a background standby arm (py spawn hiccup, unreproducible; foreground probe clean). Receipt that the harness-tracked arm...  (source: git:8bb99d5c1c72)

## claude -> deepseek: T086 blind half: seat/wake/hook prior-art deep dive from ... (research)
Span: 2026-07-16T13:25:30.569606 → 2026-07-16T13:29:35.029366
Beats: 2  · Critic: True

- claude -> deepseek: T086 blind half: seat/wake/hook prior-art deep dive from the runner seat (Daniel directive, note seat-deepdive-directive)  (source: handoff:claude->deepseek)
- seat-deepdive-directive: DANIEL DIRECTIVE 2026-07-16 ~09:30 verbatim: 'Our hooks and waits and seats system requires a full deepdive and grounding in prior art and...  (source: mem:decision:ADR_0716092530_e28bdd64)

## C1-6 filed: listener deadline self-cycle anchor anomaly (4.0h against a 5-min... (ai-setup)
Span: 2026-07-16T17:48:48.820938 → 2026-07-16T17:48:48.820938
Beats: 1  · Critic: True

- C1-6 filed: listener deadline self-cycle anchor anomaly (4.0h against a 5-min watcher) + standby full-ledger-dump noted; both routed to T086-S4  (source: git:58999bd6726e)

## Use when normalizing path prefixes for any allow/deny check: never lstrip(cha... (ai-setup)
Span: 2026-07-16T21:56:37.655548 → 2026-07-17T00:05:46.749525
Beats: 6  · Critic: True

- Use when normalizing path prefixes for any allow/deny check: never lstrip(chars) for prefix removal; strip './' in a startswith loop and refuse ':' in repo-relative paths  (source: learn:experiment:lstrip_prefixes_footgun)
- T076a+c echo hygiene (claude lane, deepseek cross-verify on resume): (a) bifrost-skip-to-now -- sanctioned audited cursor skip (requires PAUSE + --reason; rides the...  (source: git:26514a80d372)
- IR-4 SHIPPED (Daniel verdict verbatim in acl.json; T085 gate item): deepseek gains the AUDITED MIRROR exec family -- py scripts/mirror.py msg <explicit repo-relative...  (source: git:6a8133afda48)
- T086-S3 backstop dedup (claude lane, deepseek cross-verify queued): the stop-hook nag now yields to (S3a) an in-flight arming attempt -- standby stamps an .arming marker...  (source: git:4c0656415d89)
- T076 ledger transitions + notes index sweep  (source: git:eecb5798ab1d)
- C1-6 investigated (4 healthy probes, not yet reproduced) + diagnostics landed: cycle line prints elapsed/configured/chunk, standby rc-honest teach line, S1 watcher-leg...  (source: git:84c36bbb1110)

## Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/b... (ai-setup)
Span: 2026-07-17T00:09:26.512271 → 2026-07-17T00:09:26.512271
Beats: 1  · Critic: True

- Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Da  (source: episode:close:ch_1784206050_1894)

## Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/b... (ai-setup)
Span: 2026-07-17T00:09:26.526786 → 2026-07-17T03:06:01.306489
Beats: 24  · Critic: True

- Episode closed: claude -> deepseek: Fence-blind half: fresh-eyes onboarding/boot friction audit from the runner seat (Da  (source: episode:close:ch_1784206050_1894)
- jester-quantum-leap-directive: DANIEL DIRECTIVE 2026-07-16 night verbatim: 'I feel we should make our system more robust to increase the payoff of the court jester idea...  (source: mem:decision:ADR_0716211908_43cfbdbe)
- jester-forge-directive: DANIEL DIRECTIVE 2026-07-16 night (two verbatim parts): (1) 'I feel we should make our system more robust to increase the payoff of the court...  (source: mem:decision:ADR_0716212243_db746211)
- Use when searching for patterns in a specific file: use the file_types parameter to filter by extension and the directory parameter for the containing folder, NOT the...  (source: learn:experiment:search_files_directory_is_file_silent_fail)
- claude-probe3 -> claude: Round-3 seat audit: MCP boot() hangs 30min and aborts (reproducible 2/2, warm+cold) while 9 other MCP tools return instantly. Work executes...  (source: handoff:claude-probe3->claude)
- Use when tempted to kill processes while ANY test or pass is in flight: quiesce first -- (1) land in-flight work to files/commits (mirror sibling uncommitted files), (2)...  (source: learn:experiment:quiesce_before_process_cleanup)
- four-voice-directive: DANIEL DIRECTIVE 2026-07-16 night verbatim: 'How can we optimize the value of having 3 agents concurrently. This will be token expensive but I am...  (source: mem:decision:ADR_0716210953_8709bff8)
- claude -> deepseek: QUEUED BEHIND S5/S6 (finish those first -- no rush): four-voice moonshot panel, builder-lens round-1 half  (source: handoff:claude->deepseek)
- claude -> deepseek-review: Multi-agent failure-mode foresight, blind half (Daniel-directed; full brief on the bus)  (source: handoff:claude->deepseek-review)
- multiagent-foresight-directive: DANIEL DIRECTIVE 2026-07-16 evening verbatim: 'are there any gaps in our solutions? soon we are going to be doing multi agent runs so we...  (source: mem:decision:ADR_0716204454_90361cd7)
- agent-identity-directive: DANIEL DIRECTIVE 2026-07-16 evening verbatim: 'I am wondering if we have solved our agent naming issues to prevent two new agents that spawned...  (source: mem:decision:ADR_0716202852_b9b04cf6)
- fleet-lattice-vision: DANIEL DIRECTIVE 2026-07-16 evening verbatim (write-set approval + fleet vision): 'I'd say yes, this way we get to capture more information and...  (source: mem:decision:ADR_0716202443_a2d0edf0)
- Jester Forge Phase 1 opened: deepseek-red provisioned+launched (RED-inside attacker, code-reading); RED brief + BLUE brief (deepseek-review) dispatched; Gemini async...  (source: git:951d95238c23)
- Jester Forge: RED threat model (deepseek-red, 8 vectors + Green Cascade meta-attack + new C9 category) + BLUE defense (deepseek-review, 6 detectors + quarantine +...  (source: git:de6904edba88)
- deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787  (source: git:62f31255120e)
- Four-voice panel round 1 COMPLETE (3 of 4 in; builder queued behind S5): gemini verbatim (Semantic-Diff commit narrator, Token-Sentry circuit breaker, 1-bit recall...  (source: git:666c0100633d)
- Four-voice moonshot panel opened (Daniel directive verbatim in note): claude architect half filed (E1 headless claude workers via tonight's CLI+trust+allowlist = M1's...  (source: git:833cecc54ef3)
- Multi-agent readiness RECONCILED (both blind halves converged: echo amplification #1, fleet-health line, cost gauges, identity rules, ACL schema gate; thundering-herd +...  (source: git:9dd3f6789d79)
- claude multiagent-foresight blind half (F1-F10 + readiness bars) + settings rule-form fix (Write() is not a file-permission matcher -- Edit() covers all editing tools...  (source: git:313f0b000d47)
- deepseek-review provisioned + launched (Daniel directive: second write-enabled deepseek as review seat; first deliberate fleet expansion): acl member grant w/ own...  (source: git:c30cde127044)
- CLI probe ROUND 2 (report verbatim; probe still could not write -- that symmetry was the finding): round-1 fix refuted -- a repo cannot grant itself capability (34...  (source: git:9f9ee198484e)
- T088 proposed (agent identity & naming, Daniel directive) + directive note  (source: git:b55a900d0ada)
- Write-set opened for fresh seats (Daniel verdict verbatim in note fleet-lattice-vision): learn/note/handoff/lock/unlock/log/bifrost-send/ack + MCP twins ride the repo...  (source: git:8b5569d92cb7)
- CLI probe seat audit (third door): the front door WAS the finding -- settings.json had hooks but NO permissions block; a cold harness seat could be observed perfectly...  (source: git:b37a8da76d54)

## Episode closed: deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_U... (ai-setup)
Span: 2026-07-17T03:10:07.880323 → 2026-07-17T03:55:52.569511
Beats: 4  · Critic: True

- Episode closed: deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787  (source: episode:close:ch_1784257245_8759)
- claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gpt-5.6-sol (OpenAI flagship, limited preview) as third frontier peer beside fable + deepseek-v4. SHARED...  (source: handoff:claude->deepseek-review)
- Use when an MCP/JSON-RPC stdio-server tool hangs AFTER its work completes (response never written, then flushes on the next inbound frame), especially on Windows: a...  (source: learn:experiment:mcp_stdio_subprocess_stdout_wedge)
- hardening-arc-status: Hardening arc DESIGN-COMPLETE, gated on your morning approval (nothing built yet). Build spec...  (source: mem:decision:ADR_0716235552_eec29249)

## Episode closed: claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gp... (ai-setup)
Span: 2026-07-17T04:08:09.354893 → 2026-07-17T04:26:59.915559
Beats: 4  · Critic: True

- Episode closed: claude -> deepseek-review: SOL SEAT CO-DESIGN (T090): seat gpt-5.6-sol (OpenAI flagship, limited preview  (source: episode:close:ch_1784259447_3457)
- claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) runner-loop spec to research/drafts/sol-runner-loop-spec-2026-07-17.md (2) sol-named bus-loop fragments to...  (source: handoff:claude->deepseek-review)
- operating-mode-directive: DANIEL DIRECTIVE 2026-07-17 (verbatim): I want this to be our default operating mode, we have so much free compute and outsider perspective...  (source: mem:decision:ADR_0717002625_b614f1c8)
- twin-split-identity-collision: LIVE ISSUE for T088 (agent identity): two claude incarnations tonight (this HARDENING seat + the Fable twin building sol/T090) share ONE...  (source: mem:decision:ADR_0717002659_512acd65)

## Episode closed: claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) run... (ai-setup)
Span: 2026-07-17T04:27:42.735123 → 2026-07-17T04:38:05.657057
Beats: 3  · Critic: True

- Episode closed: claude -> deepseek-review: T090 FAST-LANE WORK ORDER: (1) runner-loop spec to research/drafts/sol-runner  (source: episode:close:ch_1784261655_4881)
- claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediate): file research/drafts/system-census-deepseek-2026-07-17.md per the bus request just sent -- every...  (source: handoff:claude->deepseek)
- claude -> deepseek-review: PACKET ROUTING blind half (Daniel directive, immediate): file research/reviewed/packet-routing-deepseek-review-2026-07-17.md per the bus...  (source: handoff:claude->deepseek-review)

## Episode closed: claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediat... (ai-setup)
Span: 2026-07-17T04:42:29.556407 → 2026-07-17T04:42:29.556407
Beats: 1  · Critic: True

- Episode closed: claude -> deepseek: SYSTEM CENSUS (Daniel directive, immediate): file research/drafts/system-census-deep  (source: episode:close:ch_1784262582_4740)

## Packet routing co-design converged round 4 (live iterative mode per Daniel st... (ai-setup)
Span: 2026-07-17T04:50:19.508565 → 2026-07-17T04:50:19.508565
Beats: 1  · Critic: True

- Packet routing co-design converged round 4 (live iterative mode per Daniel steer): six joint positions, sequencing concession T047-first, O1/O3 summary-vs-verdict drift...  (source: claude:codesign)

## Reasoning spine round 1 CONVERGED (claude + deepseek-review live co-design): ... (ai-setup)
Span: 2026-07-17T05:04:54.419273 → 2026-07-17T05:04:54.419273
Beats: 1  · Critic: True

- Reasoning spine round 1 CONVERGED (claude + deepseek-review live co-design): C1-C11 in docs/reasoning-spine-design-2026-07.md. deepseek won 5 positions incl. the...  (source: claude:codesign)

## Reasoning spine CONVERGED after 4 live co-design rounds (claude + deepseek-re... (ai-setup)
Span: 2026-07-17T05:11:16.162105 → 2026-07-17T05:16:07.788945
Beats: 3  · Critic: True

- Reasoning spine CONVERGED after 4 live co-design rounds (claude + deepseek-review): docs/reasoning-spine-design-2026-07.md. Each author changed position on argument...  (source: claude:codesign)
- reasoning-spine-status: T092 reasoning spine: CONVERGED 2026-07-17 after 4 live co-design rounds (claude + deepseek-review), docs/reasoning-spine-design-2026-07.md...  (source: mem:decision:ADR_0717011116_2ae06032)
- Session ended  (source: session:end)
