---
akashic_id: art_20260709_narrative-spine-v2-re-evaluation-upgrade_c98a1b
akashic_sha: 6bd352c6b840
status: fossil
type: design
date: 2026-07-09
title: "Narrative Spine — v2 Re-evaluation & Upgrade Plan"
gist: "**Date:** 2026-06-28 **Method:** Full re-read of every slice (schema → BeatLog → TrackRouter → Chronicler → chapter-lifecycle → session → Th"
tenant: solo
visibility: fleet
seats: []
category: [memory, method, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_narrative-spine-v2-re-evaluation-upgrade_c98a1b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Narrative Spine — v2 Re-evaluation & Upgrade Plan

**Date:** 2026-06-28
**Method:** Full re-read of every slice (schema → BeatLog → TrackRouter → Chronicler →
chapter-lifecycle → session → ThemeAssigner → EventLog/Query → EventBridge → EventPromoter →
tag-governance G0–G2), **adversarial probes run against the real code** (isolated
FileStore/FileLedger, `tests/spine_probes.py`), and **fresh prior-art research** per piece.
This is the honest assessment the spine deserves before it becomes load-bearing.

**Headline:** the architecture is sound and several hard parts are genuinely well built. The
probes surfaced **4 confirmed defects** (1 high, 2 medium, 1 latent) and **3 design weaknesses**.
None are structural — all are fixable in a focused hardening wave without re-architecting.
This plan is two waves: **W1 = correctness/robustness hardening** (the "nervous" fixes),
**W2 = research-backed capability upgrades**.

---

## 1. What I verified is SOLID (credit where due)

These were probed and held up — don't touch them except where noted:

| Piece | Evidence |
|---|---|
| **Tag-governance CRDT (G1)** | 1000-record monotonicity fuzz + order-independence pass. The lattice-join resolver is correct. (One hole — non-finite confidence — see D3.) |
| **Salience promotion rate-limiting (EventPromoter)** | Probe G: per-run cap (10) respected under a 50-event error flood; persistent dedup set holds on re-run (10 skipped). No Beat flood. |
| **Chapter-list hygiene (chapter_lifecycle)** | Probe D: inserting a salient mid-sequence beat → re-chronicle produced 7 chapters, **0 orphaned keys**; merge+active-filter works. |
| **Faithfulness gate** | Probe F: an injected *hallucinating* writer (`source: git:HALLUCINATED`) was caught — `faithful=False`. The gate bites when exercised. |
| **Event detail JSON-safety** | `_safe_detail` round-trips through `default=str` so a non-serializable payload can't crash the backend write. Good defensive instinct. |
| **Bi-temporal lifecycle, lossless pointers, layering** | `valid_from`/`recorded_at`, `event:<stream>:<id>` pointers, and the System-1-3-vs-System-4 import discipline are textbook and consistent. |

---

## 2. Confirmed defects (ranked) — with probe evidence

### D1 — EventQuery silent recall loss beyond the scan horizon  ⚠️ HIGH
**Probe C:** captured 8 events, queried a window covering all 8 with `scan=3` →
**`events_in_window` returned 3**, silently dropping the 5 oldest. The docstring claims
*"Returns ALL matches (recall = 100%)"* — **false** beyond the newest `scan` events
(default 20 000). Every drill-down (`EventBridge.events_around`, `raw_for_beat`) inherits this.

Two problems compound:
- **Correctness:** any chapter/beat older than the most recent `scan` events drills into an
  *incomplete or empty* raw record, with no error — the worst kind of failure (looks like "nothing
  happened" rather than "I didn't look far enough").
- **Scale:** each query does a full O(n) stream replay (`_read_all`) — there is **no time index**.
  At the firehose's 100 000-event `maxlen` that's a 100k-record replay per drill-down, which
  breaks the predictable-latency goal in the roadmap.

**Root cause:** the events layer never built the "time-window / indexed queries" the EventLog
docstring itself promises ("Slice 3 adds…"). EventQuery just linear-scans the newest slice.

### D2 — TrackRouter substring matching → false-positive routes  ⚠️ MEDIUM-HIGH
**Probe A:** matching is `kw in text` (raw substring), so keywords fire *inside* unrelated words:
- `"comfy sweater knitting notes"` → **vision** (`comfy` matched `comfyui`'s `comfy`)
- `"restore from snapshot backup"` → **ai-setup** (`store` inside `restore`)

This is the same failure family as the ZLUDA mis-tag you caught — short/ambiguous needles
(`comfy`, `store`, `agent`, `realtime`) matched without word boundaries. It silently lowers
routing precision and is the upstream cause of mis-tags the G2 auditor then has to clean up.

### D3 — Non-finite confidence hijacks the tag resolver  ⚠️ MEDIUM
**Probe E:** `TagHistory.from_list` validates confidence with `float(e.confidence)`, which
**accepts `inf` and `nan`**. Result:
- `confidence = +inf` → **beats a real 0.95 tag** and becomes `current()`. This breaks the I2
  monotonicity invariant — the formal "successive cleanup can't degrade data" guarantee — with a
  single malformed/hostile entry.
- `confidence = nan` is *safely* ignored (NaN loses every `max` comparison), so only `inf`/huge
  values are the live hole, but both should be rejected at the boundary.

### D4 — Mixed-timezone timestamps silently mis-sort / mis-segment  ⚠️ LATENT MEDIUM
**Probe B:** feeding interleaved naive (`...T02:00:00`) and tz-aware (`...T02:00:00+00:00`) beats
did **not crash** (best-effort swallowed it) — but that's the danger. `chronicle_all` sorts beats
by **string** (`b.at`), while `_hour_gap`/`_epoch` parse to `datetime`. A `-05:00` offset sorts as
if it were UTC wall-clock, and `_hour_gap` of a naive minus a tz-aware raises `TypeError` →
caught → returns `0.0` → **a real session gap silently fails to cut a chapter**. The probe's gaps
were small so the damage was invisible — exactly how this bites in production without a test.

---

## 3. Design weaknesses (not bugs, but limit how good the spine gets)

### W-a — ThemeAssigner is overfit to building-the-spine
The 6 theme keyword-tuples (`routing`, `logging`, `evaluation`, `design`, `memory`, `narrative`)
were "derived from 7 existing beats" — all of which are about *constructing the spine itself*.
A beat about **voice/whisper** or **vision/florence** matches **no theme**. The cross-cutting
"which idea" axis can't gather the user's actual domains. Hand-keyword themes also don't scale to
new ideas without code edits.

### W-b — Faithfulness gate is correct but dormant
Probe F proved the gate works — but the **default heuristic writer only copies** beat summaries,
so it structurally *cannot* produce an unfaithful pointer. Today the metric is always-true; it only
becomes a real gate when an LLM writer is injected, and there is **no permanent adversarial test**
pinning that it bites. (Coverage, by contrast, is a real live metric.)

### W-c — Pervasive `except: pass` hides silent degradation
`_route`, `_assign_themes`, `chronicle`, `promote_salient`, `capture` all swallow everything.
That's correct for "logging must never break the host command" — but there is **no counter, no
health signal**. A routing rule that silently no-ops (→ everything `unknown`) looks identical to
"working." You can't see the spine getting sick.

---

## 4. Prior art per piece (what the best approaches do)

- **Boundary/segment detection** (TrackRouter switch + Chronicler `BoundaryDetector`): the field has
  moved from fixed heuristics to **surprise-driven boundaries** — EM-LLM / *Human-inspired Episodic
  Memory* uses Bayesian surprise to place boundaries then refines them graph-theoretically; **LLMs as
  segmenters** now beat classical methods; **ES-Mem** and **HingeMem** are boundary-guided long-term
  memory (already cited in code). Evaluation has also matured: *granularity-aware* metrics beat raw F1.
  → our `min_gap_hours` + `weight>=5` heuristic is a fine Tier-0; the upgrade is a *surprise/semantic*
  boundary signal, gated by ARI/WindowDiff on the gold fixture.
- **Routing as weak supervision** (the G3 tie-in): **Snorkel**'s label model learns per-labeling-function
  reliability from agreement/disagreement, no ground truth; the **Hyper Label Model** combines LFs without
  dataset-specific training; **LLMs-in-the-loop** turn prompts into LFs. → our `path>strong>category>generic`
  priority list is a hand-weighted LF ensemble; the principled version learns the weights.
- **Theme discovery** (ThemeAssigner): **topic modeling** (LDA → embedding-cluster / BERTopic-style) discovers
  latent themes unsupervised; **expert-informed topic models** seed known themes and discover the rest. →
  replace hand keywords with seed-plus-discover embedding clustering over beat summaries.
- **Salience → Beat promotion** (EventPromoter): already well-grounded — Generative Agents (importance-gated
  reflection), Nemori / "What Deserves Memory" (designer-intuition heuristics as honest baseline). Keep; the
  embedding poignancy scorer remains a documented, ablation-gated seam.

Sources: [Human-inspired Episodic Memory for Infinite Context LLMs](https://arxiv.org/pdf/2407.09450) ·
[ES-Mem](https://arxiv.org/pdf/2601.07582) · [HingeMem](https://arxiv.org/pdf/2604.06845) ·
[Topic Segmentation Using Generative LMs](https://arxiv.org/html/2601.03276v1) ·
[When F1 Fails: Granularity-Aware Segmentation Eval](https://arxiv.org/pdf/2512.17083) ·
[Snorkel](https://arxiv.org/abs/1711.10160) · [Learning Hyper Label Model](https://arxiv.org/pdf/2207.13545) ·
[Language Models in the Loop](https://arxiv.org/pdf/2205.02318) ·
[SemaTopic (semantic topic modeling)](https://www.mdpi.com/2073-431X/14/9/400)

---

## 5. The v2 plan — sliced, each gated by a bar + worst-case tests

Same discipline as the tag-governance slices: build small, each gated by an executable acceptance
bar and the worst-case tests that prove robustness. **Wave 1 is the hardening you're nervous about;
do it first.** Wave 2 is research-backed capability and can wait.

### Wave 1 — Correctness & robustness hardening  ✅ **COMPLETE 2026-06-28**

All five shipped, each its own tested slice (full suite 265, guardrails clean, mirrored):
**D1** time-indexed EventQuery (`event_index.py`, 8 tests) · **D3** confidence hardening
(drop non-finite / clamp range, 5 tests) · **D2** word-boundary router+theme matching
(confusable corpus, ARI bar held, 4 tests) · **D4** timezone-safe comparison
(`foundation/timeutil.py`, 6 tests) · **W-c** narrative health counters (`narrative/health.py`,
surfaced in `status`, 4 tests). Original specs below.


**V1 — Time-indexed EventQuery (fixes D1).**  ✅ **SHIPPED 2026-06-28** — `core/events/event_index.py`
(Store-backed CQRS read-model: `events:raw:tindex` zset + per-id payload keys, bounded + rebuildable;
Ledger stays system-of-record). Index is opt-in via a Store (ledger-only callers degrade to the bounded
scan); canonical singleton wires it. `events_in_window` is now a range-scan with total in-retention recall.
8 worst-case tests green (`tests/test_event_index.py`), full suite 246. Below = the original spec.
Add a per-stream time index (`events:raw:tindex` zset `{event_id: epoch}`, written on capture) so
`events_in_window` is a **range scan**, not a full replay; resolve ids → events by direct lookup.
Delete the false "recall=100%" claim or make it true within a declared horizon.
*Bar:* window recall = 100% for events arbitrarily far back (probe C passes at N≫scan); query latency
bounded and flat as the firehose grows to 100k. *Worst-case tests:* empty stream; window fully before
/ after all events; lo>hi swap; an event exactly on each boundary; 100k-event latency assertion;
backfill path for already-captured events with no index.

**V2 — Word-boundary router & theme matching (fixes D2).**
Replace `kw in text` with token/word-boundary matching (regex `\b` or a tokenized set-intersection)
in TrackRouter `_infer` and ThemeAssigner. Build a **confusable corpus** (`comfy sweater`, `restore`,
`storage`, `management agent`, `realtime analytics`) as a permanent regression fixture.
*Bar:* every confusable routes to `unknown`/correct, not the false track; **Slice-2 gold-fixture ARI
does not regress**. *Worst-case tests:* the confusable corpus; multi-word phrase keywords still match
(`stem separation`); unicode text; empty text.

**V3 — Confidence hardening in TagHistory (fixes D3).**
Reject/clamp non-finite and out-of-range confidence at the boundary (`add` + `from_list`): require
`math.isfinite` and clamp to `[0,1]`; drop the entry otherwise.
*Bar:* `inf`, `-inf`, `nan`, `1e9`, `-5` can none of them become `current()` over a real tag.
*Worst-case tests:* fold into the existing CRDT monotonicity fuzz — add hostile non-finite records to
the 1000-record storm and assert the confirmed tag still wins.

**V4 — Timestamp normalization at the boundary (fixes D4).**
Normalize every `at` to tz-aware UTC ISO at the single choke points (`BeatLog.emit`, `EventLog.capture`):
parse, assume-UTC-if-naive, store canonical. All downstream sort/gap math then agrees.
*Bar:* a mixed naive/tz-aware input batch produces the **identical** segmentation as the same instants
normalized. *Worst-case tests:* `+00:00`, `-05:00`, naive, and `Z` forms of the same instant collapse
equal; DST-ambiguous input doesn't crash; ordering is by true instant.

**V5 — Health counters on the best-effort paths (fixes W-c).**
Increment lightweight Store counters on each silent path (`narr:health:routed|persist|unknown`,
`chronicle:fail`, `promote:skipped`) and surface them in `agent_cli.py status`.
*Bar:* a forced routing exception increments a visible counter — silent no-op becomes observable.
*Worst-case tests:* counters never raise into the host path; absent counters read as 0.

### Wave 2 — Research-backed capability upgrades (each must BEAT its Tier-0 baseline or it doesn't ship)

**V6 — Theme discovery v2 (fixes W-a). ✅ DONE 2026-06-28** (`core/narrative/theme_discovery.py`, 16 tests).
*Shape (measured, not assumed):* pure-embedding routing wins recall but TANKS precision (sprays false
themes → loses F1), so the shipped design is **HYBRID — keyword themes ∪ confident embedding themes**
(per-theme short EXEMPLAR phrases, max-pooled cosine, τ=0.44 frozen on a wide 0.38–0.46 plateau). **V6a**
seed router + ablation gate; **V6b** `discover()` clusters the residual (C1 Clusterer) into net-new themes
labeled by c-TF-IDF (no LLM), cold-start-guarded; **V6c** wired into BeatLog via `select_theme_assigner()`
— DETERMINISTIC opt-in (`AKASHIC_EMBED_THEMES=1`), default keyword (no model load on the CLI write path).
*Ablation gate PASSES on the gold fixture:* recall 0.625→0.750, F1 0.741→0.800, precision 0.857, 4
keyword-miss beats recovered. *Follow-on:* a batch consolidation re-theme pass to upgrade an existing
corpus off the hot path (the clean way to re-theme regardless of the per-write flag).

**V7 — Embedding TrackRouter / Tier-1 (the planned Slice 6).** Embedding nearest-track via the Ranker
`relevance_fn` seam. *Bar:* beats Tier-0 heuristic ARI on the gold fixture (ablation gate) or it stays off.

**V8 — Weak-supervision label model (the G3 tie-in).** Treat router signals as labeling functions; learn
their reliability (Snorkel / Hyper-Label-Model) instead of the hand-set priority list. *Bar:* beats the
single-best-signal ARI baseline on the gold fixture; confidence feeds the tag-governance `basis→confidence`.

**V9 — Faithfulness gate, exercised (fixes W-b).** Promote probe F to a permanent adversarial-writer test;
wire an LLM writer/critic behind the existing seam with the gate enforced on real output. *Bar:* the gate
fails a known-bad summary in CI; passes a faithful one.

---

## 6. Recommended sequencing

1. **Wave 1 first, in order V1 → V5.** These are the "is the spine trustworthy" fixes. V1 (recall loss) is
   the highest-value single fix — it makes the drill-down feature actually correct at scale. V2–V4 are small,
   surgical, high-confidence. V5 makes future regressions visible.
2. **Then Wave 2 as appetite allows** — V6/V7/V8 are the "make it smart" upgrades and each is independently
   shippable behind its ablation gate. V9 rides along with whenever an LLM writer lands.

Each slice: branch-by-test, acceptance bar green + full suite green + guardrails clean + mirror, exactly as
G0–G2. The probe harness (`tests/spine_probes.py`) graduates into `tests/test_spine_adversarial.py` so
every defect above stays fixed.
