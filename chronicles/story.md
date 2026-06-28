# Story — generated 2026-06-28T15:30:00

Version: 0

## Atlas
- **ai-setup**: 7 chapter(s)
- **research**: 2 chapter(s)
- **vision**: 1 chapter(s)

Summary: ai-setup: 7 chapter(s); research: 2 chapter(s); vision: 1 chapter(s)

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

## Codex S1: extract shared Consolidator primitive -- chronicler + learning/cons... (ai-setup)
Span: 2026-06-28T12:11:26.188260 → 2026-06-28T18:44:44.508518
Beats: 26  · Critic: True

- Tag Governance G0: tag-history + confidence schema (TagEntry/TagHistory, basis->confidence, append-only + rollback) + Beat.tag_history + worst-case tests  [relates: member_of]  (source: git:f2cd9cf3fe32)
- Tag stores should be CRDTs (MV-register + survivorship resolver) for self-cleanup without data loss. Sources: Shapiro CRDTs, MDM survivorship/golden-record...  [relates: member_of]  (source: learn:experiment:tag_governance_g1_crdt)
- Tag Governance G1: confidence-gated append-only re-tag (a CRDT) + Store.zrem + BeatLog tag-history seed; worst-case invariant tests (233 pass)  [relates: member_of]  (source: git:0ee32b23a2fc)
- Tag Governance G2: confident-learning mis-tag detection (flag-only, I6 read-only) + scorer seam for Slice-6 embeddings; worst-case tests (238 pass)  [relates: member_of]  (source: git:4066eff6345f)
- scorer seam IS the Cleanlab/confident-learning hook for Slice-6 embeddings -- plug an embedding/LLM scorer there. Backfill tag_history on pre-G1 beats to cut...  [relates: member_of]  (source: learn:experiment:tag_governance_g2_detection)
- Wave 1 hardening V1-V5 (time-index events, word-boundary matching, clamp confidence finite[0,1], normalize tz at boundary, health counters) FIRST; Wave 2 V6-V9...  [relates: member_of]  (source: learn:experiment:spine_v2_reevaluation)
- CQRS read-model over an append-only Ledger is the clean pattern: Ledger = system-of-record + rebuild source, Store index = queryable projection. Opt-in-by-store kept...  [relates: member_of]  (source: learn:experiment:spine_v1_event_time_index)
- Spine V1: time-indexed EventQuery (fixes D1 silent recall loss) -- Store-backed CQRS read-model, bounded+rebuildable, opt-in; 8 worst-case tests, suite 246  [relates: member_of]  (source: git:b07a0ce97ab1)
- Drop-don't-clamp for non-finite is the right call (clamping inf->1.0 would still let it win); clamp only finite drift. Read-path sanitization protects against...  [relates: member_of]  (source: learn:experiment:spine_d3_confidence_hardening)
- Spine D3: harden tag confidence (drop non-finite, clamp out-of-range) -- defends the CRDT no-degrade guarantee against tampered/corrupt entries; 5 new tests, suite 251  [relates: member_of]  (source: git:35b8c3bb6f54)
- Spine D2: word-boundary router/theme matching (fixes substring false positives) + drop ambiguous 'comfy'; confusable corpus, ARI bar held, suite 255  [relates: member_of]  (source: git:0be2aff99984)
- For naive timestamps, .timestamp() is locale-dependent -- always normalize naive==UTC before comparing. Fix comparison (recomputed) freely; persisted scores need a...  (source: learn:experiment:spine_d4_timezone_safe)
- Spine D4: timezone-safe chronicler comparison (core/foundation/timeutil) -- mixed naive/tz-aware no longer mis-sorts/mis-segments; 6 tests, suite 261  [relates: member_of]  (source: git:ebc4afc3e650)
- Observability counters must themselves be best-effort (never raise into the path they observe). Keep them in the narrative layer; lower primitives log their own...  [relates: member_of]  (source: learn:experiment:spine_wc_health_counters)
- Spine W-c: narrative health counters (route/theme/chronicle) surfaced in status -- silent best-effort failures now observable; 4 tests, suite 265. Wave-1 hardening...  [relates: member_of]  (source: git:f8caedac801e)
- Do the 3 unifications FIRST (S5 time fn, S1 Consolidator extract, S4 node-lifecycle) so every later slice is built on one engine/lifecycle/seam -- connections simplify...  [relates: member_of]  (source: learn:experiment:codex_inventory_pressure_test)
- When unifying a helper that computes PERSISTED scores, ship a re-score migration in the same slice or windowed queries silently lose recall at the old/new boundary...  [relates: member_of]  (source: learn:experiment:codex_s5_time_unification)
- Codex S5: unify time handling -- collapse 6 _epoch copies into timeutil.to_epoch + re-score migration (canonical: 80/80/35); 5 tests, suite 270  [relates: member_of]  (source: git:132eb23c3630)
- Cache-first + lazy-load is the key pattern for the per-command-process model: warm Store cache means most calls never pay the 7.5s model load. ONE embedding seam...  [relates: member_of]  (source: learn:experiment:codex_c0_embedder)
- Codex C0: Embedder primitive (all-MiniLM-L6-v2, CPU, cached+lazy, keyword fallback) into the Ranker.relevance_fn seam; ablation gate passes (embeddings beat keyword); 6...  (source: git:11a34d0af171)
- The real prize isn't DRY -- it's the SINGLE point where Ranker+Distiller (and at C4, the faithfulness critic) are constructed: wire the gate into Consolidator once...  [relates: member_of]  (source: learn:experiment:codex_s1_consolidator)
- Codex S1: extract shared Consolidator primitive -- chronicler + learning/consolidation onto one rank->distill engine (behavior-identical); 4 tests, suite 280  [relates: member_of]  (source: git:5113746be6b5)
- Spine v2 re-evaluation: adversarial audit of every slice (4 confirmed defects + prior-art-backed v2 plan) -> docs/spine-v2-plan.md + tests/spine_probes.py  [relates: member_of]  (source: git:25803d5f4245)
- Spine v2 plan: mark Wave-1 hardening complete (D1-D4 + W-c)  [relates: member_of]  (source: git:0e8a02b0851b)
- Codex plan (Wave 2): self-curating knowledge layer over immutable atoms -- MDL-under-faithfulness objective, prior-art-grounded, sliced C0-C7. docs/codex-plan.md  (source: git:b18c8233d700)
- Codex pressure-test: inventory + slice placement + 8 simplifications (one Consolidator, one embedding seam, unify supersession, collapse _epoch) ->...  [relates: member_of]  (source: git:e26fa6f98b42)

## Word-boundary fixes substring-in-word, but genuinely-ambiguous standalone wor... (vision)
Span: 2026-06-28T15:19:03.234169 → 2026-06-28T15:19:03.234169
Beats: 1  · Critic: True

- Word-boundary fixes substring-in-word, but genuinely-ambiguous standalone words (comfy=cozy vs ComfyUI) need keyword hygiene too -- require the unambiguous product form...  [relates: member_of]  (source: learn:experiment:spine_d2_word_boundary_matching)

## Start C0 (embedding substrate) with research-to-do: benchmark EmbeddingGemma-... (research)
Span: 2026-06-28T18:09:39.135268 → 2026-06-28T18:09:39.135268
Beats: 1  · Critic: True

- Start C0 (embedding substrate) with research-to-do: benchmark EmbeddingGemma-300M vs E5-small vs bge-small on a local fixture, then Embedder primitive + cache +...  [relates: member_of]  (source: learn:experiment:codex_plan_wave2)
