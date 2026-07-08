# Recall vNext — closing the four loops (2026-07-08)

**Status:** Daniel-directed full build 2026-07-08 (T011); DeepSeek review invited post-hoc for the v2+
items. **Author:** claude. **Evidence base:** 7d funnel (2,850 impressions -> 26 helped = 1.05%;
triage: 1 protect / 34 cost_no_return / 141 ghosts / 0 noise votes ever), 24h injection ledger
(68 injections, ~7.6k tokens, 59 of 60 lessons injected), and a night of lived hook experience.

## Thesis

The recall machinery (provenance tags, FAITH gate, dissent, counters, graduation, ghosts, injection
ledger) is complete and honest — but **four loops are designed-open**: credit flows in through one
narrow valve (same-target flips), curation is a report nobody acts on, matching ignores the trigger
structure the lessons themselves encode, and gaps are nudged but never aggregated. Closing loops, not
adding machinery, is the transformation. Target state: **a learned reflex system** — precise triggers,
provable influence, self-curating corpus, directed acquisition.

## The four loops

### 1. Curation loop — triage becomes an actor (V1, tonight)
`core/recall/curator.py`: deterministic rules over the funnel counters.
- **Bench** (mirrors graduation's field mechanics): `surfaced >= 10 AND helped+useful == 0 AND
  age > 10d` -> `benched` stamp; benched lessons leave recall surfaces (cache/boot) but stay in
  full-corpus queries with a `[benched]` tag. NOT deletion — a Store-state flag, reversible.
- **Unbench on credit**: any new helped/useful (e.g. via `recall --full` engagement or a wrap vote)
  clears the stamp — the safety valve against benching a quiet guardian.
- **Ghosts**: zero-credit ghosts pruned (existing `prune_ghost_counters`); credited ghosts REPORTED
  for supersession adjudication, never auto-folded (no edge data = no deterministic fold).
- Verbs: `recall-curate` (report) / `recall-curate --apply`. A one-line nudge in `wrap` when the
  bench bucket is non-empty. **Gate:** injections/day and value_rate before vs after; corpus surface
  count drops by ~the cost_no_return bucket.

### 2. Precision loop — match on the trigger, not the prose (V2, tonight)
The lesson convention already encodes its firing condition: *"Use when <symptom>, before <action>:
<advice>"*. The matcher keyword-matches whole prose instead — that's why June's refactor arc fires
on "continue working". Changes:
- **Trigger-aware relevance** via the Ranker's existing `relevance_fn` seam (no fork): parse the
  `use when ... :` clause at cache-build time into a `trigger` field; relevance = 0.6 x overlap(query,
  trigger) + 0.4 x overlap(query, prose) when a trigger exists, else plain overlap. Deterministic.
- **Mined trigger terms:** durable `flip` events carry (target, credited sources) — each lesson's
  historically-credited target tokens are appended to its trigger vocabulary at cache build. Every
  flip credit sharpens future matching; the corpus self-tunes from its own outcome history.
- **Calibrated show-nothing floor:** replay credited pairs (flip events) and the 24h injection ledger
  through the new relevance fn; set the default floor to keep >=95% of historical helps while cutting
  the never-helped mass. Env `AKASHIC_RECALL_FLOOR` overrides. (Calibration result recorded below.)
- **Self-echo suppression:** a lesson does not resurface to its own author within
  `AKASHIC_RECALL_SELF_ECHO_H` (default 2h) of being recorded — its author just lived it.
**Gate:** replay keeps historical helps; injections/day falls materially; the June cluster stops
firing on generic prompts.

### 3. Credit loop — widen the aperture at the natural moments (V3, tonight)
`helped` = same-target FAIL->SUCCESS only, so plan-altitude influence and prevented mistakes are
structurally invisible (the 1.05% is an undercount — but indistinguishable from noise, which blocks
pruning confidence). Three deterministic channels, no LLM:
- **Wrap-time review:** `wrap` prints the session's surfaced lessons (from the injection ledger) with
  prefilled one-keystroke vote commands. Voting moves to the reflective moment — this is why the
  explicit channel sat at 4 useful / 0 noise forever.
- **Engaged counter:** a `recall --full <source>` pull is a strong interest signal; count `engaged`
  separately (displayed in triage; NOT in ranking until it earns it — evidence first).
- **Session-outcome join:** the A'' `session_signals` fold gains `recall_surfaced` / `recall_helped`
  per session — recall efficacy lands in the same durable dataset the Renew correlation reads.
  One dataset, two pillars.

### 4. Acquisition loop — gaps become a directed queue (V3, tonight)
Every uncredited flip is a place the corpus failed to help. `wrap` already nudges per-flip; aggregate
instead: cluster the session's uncredited flips by target class and print "corpus gaps" with prefilled
`learn` commands. Directed acquisition instead of ad-hoc capture.

## Deliberately deferred (design-review items, not tonight)
- **Trigger CONTRACTS v2** — structured predicates ({tools, path_globs, command_res}) mined per
  lesson from experiment records + credit history; a Rete-lite over the hook stream. The trigger-
  clause weighting above is the evidence-cheap v1 of this.
- **Consolidation-merge mining** — near-duplicate lesson clusters (the sprint_pattern_* family)
  merged with credit folded. Needs supersession edges on lessons first.
- **Cross-agent `confirmed` tag** — a lesson helped for an agent that didn't author it earns a
  stronger provenance tier (the anti-opinion-laundering ladder's next rung).
- **Per-session injection token budget** — the ledger measures it; cap it. Cheap, but measure the
  post-V2 volume first: precision may make it moot.

## Calibration record (V2) — run 2026-07-08
Replay of durable credited flips + the 24h injection ledger through the trigger-aware relevance fn:
- **Credited pairs scorable: 1 of 26 historical helps** (older flips predate source-carrying detail
  or point at renamed/retired lessons — counter history didn't survive corpus churn; the ghost
  adjudication debt made itself visible). That one TRUE help scored **0.667**.
- Injection population (n=108, 24h): min 0.036 / p25 0.057 / **median 0.125** / p75 0.20 / max 0.50.
- Floor sweep: 0.10 cuts 44% of the population; 0.15 cuts 65%; all candidate floors keep the
  credited pair with >=6x margin.
- **Chosen default: 0.20** (`AKASHIC_RECALL_FLOOR`) — keeps the credited pair at 3.2x margin and
  cuts **91%** of the 24h injection population. n=1 honesty: recalibrate once the wrap-review /
  engaged channels grow the credited set (the loops this slice ships produce exactly that data).
- The scoring that earned it (found by probe-driven iteration, each step tested):
  (1) IDF weights computed from the corpus (no hand-tuned relevance), (2) the ratio's denominator
  floored at one fully-rare term's mass (a single corpus-common token can otherwise score 1.0 —
  scale-invariance bug), (3) single-hit dampener for 3+-token queries and low-weight lone hits,
  (4) conversational/domain filler added to the module's existing `_STOP` class ('lets continue
  working on the system' -> empty query -> silence; a 60-doc corpus's IDF cannot see that alone).
- **Probe battery (live corpus):** three generic prompts -> SILENT; six genuine trigger queries ->
  their exact lesson ranked FIRST (four of them as the sole result). Before: 59 of 60 lessons
  injected within 24h.
