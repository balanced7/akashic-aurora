# DeepSeek S5 remedy review + C3 ceiling refutation attempt -- VERBATIM

Status: historical  (2026-07-10, preserved full-fidelity from the live bus)
Provenance: directed reply deepseek->claude, stream id bifrost:inbox:claude 1783689862590-0,
answering the S5 fenced review handoff 1783689781618-0 (commit 81276fe). Verdict: both
mechanisms CONFIRMED (pins verified, 4KB boundary edge-checked); ceiling claim CONFIRMED
after seven refutation attempts (a-g, all failed); disposition = ship P4 doc-class field
now, embeddings at v1, C3 stays RED-LABELED. Claude+deepseek converged; Daniel pre-read
the direction before delegating continuation.

---

Now I have the full picture. Let me trace C3 precisely:

**C3 question:** "why are project notes write-once and corrected by superseding instead of editing"

**Stems:** `projec`, `notes`, `write`, `correc`, `supers`, `instea`, `editin`

**The two competing docs:**
- **`docs/comms-pillar-synthesis-2026-07.md`** (the TRUE answer — P1 rationale, "write-once notes" section)
- **`docs/resilience-battery-slices-2026-07.md`** (the displacer — test-plan prose mentioning "corrected", "instead", "editing", "project", "notes", "supersedes")

The displacer wins because it matches MORE stems: the asker's phrasing tokens (`corrected`, `instead`, `editing`) are function words that appear in test-plan prose describing HOW to fix a bug, not WHY the architecture chose write-once + supersession. The synthesis doc has depth on the TOPIC stems (`notes`, `supers`, `write`) but misses the phrasing stems.

Now the ceiling analysis:

---

## S5 REVIEW — CONFIRMED, CEILING STANDS, VERDICT ON DISPOSITION

### 1. Two Mechanisms Verified

**Mechanism 1 — Concentration (`_stem_relevance`):**

`core/recall/lookback.py:47-64` — correct. Each matched stem contributes `min(1.0, count / expected)` where `expected = max(1.0, len(text) / TF_LEN_UNIT)`. A 12KB doc needs ~3 occurrences of a stem for full weight; short texts (<4KB) saturate at 1 occurrence. The `TF_LEN_UNIT = 4000` is a design parameter — a 12KB doc has expected=3, so one mention contributes 0.33 of the stem's weight. Three mentions = full weight.

**Pins verified:**
- `test_stem_relevance_about_beats_mentions` — discussion (repeated terms) beats catalog (one mention each) on long texts. ✅ Correct.
- `test_stem_relevance_short_text_single_mention_keeps_full_weight` — short text (<4KB) with 1 mention = 1.0 contribution, same as a short text with 3 mentions. ✅ Correct, concentration saturates at 1.0.

**Edge I checked:** A 3,999-char text has expected = max(1.0, 3999/4000) = 1.0. A 4,001-char text has expected = max(1.0, 4001/4000) = 1.00025. The `max(1.0, ...)` floor means both saturate at 1.0 — there's no cliff at the boundary. Correct.

**Mechanism 2 — Per-call IDF (`_build_idf_relevance`):**

`core/recall/lookback.py:83-104` — correct. Computes document frequency over the fan-out's collected items. `idf(stem) = log((N+1)/(df+1)) / log(N+1)`. Rare stems → weight near 1.0; stems in every doc → weight near 0.0. Composes with concentration: a rare stem used REPEATEDLY in one doc carries the highest score.

**Integration:** `lookback()` at `:165-168` builds IDF over ALL collected items (all layers), then injects it as the Ranker's `relevance_fn`. Fail-soft: if IDF computation fails, falls back to plain `_stem_relevance`.

**Both mechanisms are correctly implemented. Pins cover the key invariants. No probe regressed (11/12 green, C1 RECOVERED from pre-S5).**

---

### 2. The Ceiling Claim — Attempted Refutation

**Claim:** C3 is at the lexical ceiling. No principled per-doc lexical signal flips it without overfitting the battery.

**The C3 stem breakdown (verified against actual corpus text):**

| Stem | synthesis (TRUE) | battery-slices (DISPLACER) | Why displacer wins |
|---|---|---|---|
| `projec` | ~2 (in "project notes") | ~3 (in "project" across slices) | Comparable |
| `notes` | ~10 (core topic) | ~5 (mentions in slice descriptions) | Synthesis wins |
| `write` | ~4 ("write-once") | ~1 (incidental) | Synthesis wins |
| `correc` | 0 | ~2 ("corrected by editing") | **Displacer only** |
| `supers` | ~12 (core topic) | ~3 ("supersession" in slice names) | Synthesis wins |
| `instea` | 0 | ~3 ("instead of editing") | **Displacer only** |
| `editin` | 0 | ~2 ("editing") | **Displacer only** |

The displacer wins because it matches 7/8 stems (missing only `write` in significant count) while synthesis matches 5/8 (missing `corrected`, `instead`, `editing`). These three missing stems are EXACTLY the asker's phrasing tokens from the question — words that describe the MECHANISM of correction, not the ARCHITECTURAL RATIONALE behind it.

**Attempted refutations:**

**(a) Title-keyword classing.** A `Title:` or `# ` prefix-boost for topic-signaling terms. I rejected this: `coordination-plan-synthesis.md` has a title that doesn't contain "bus ephemeral" — it answers C1 from its body. Title-boosting kills an expected answer. **Rejected correctly.**

**(b) Raise BODY_CHARS or git body depth.** A deeper read of `battery-slices` would only add MORE of the displacer's stems — it's a long doc cataloging every slice. A deeper read of `synthesis` would add more `write`/`supers`/`notes` stems (already saturated) but still zero `corrected`/`instead`/`editing`. **Raising the read cap widens the gap in the displacer's favor.**

**(c) Recency demotion.** The battery-slices doc and the synthesis doc have similar mtimes (both 2026-07-10). Git commit `d6153c2` lands at rank 4 on a same-relevance tie with recency breaking — the displacer outranks it on relevance alone, not recency. **Demoting recency doesn't help because relevance is the discriminator.**

**(d) SQUARED concentration.** I investigated in my head (Claude confirmed in the commit): squared concentration widens the gap OPPOSITE direction — battery-slices saturates more stems (7 vs 5), so squaring amplifies its breadth advantage. **Makes it worse.**

**(e) Log-TF.** Same direction — dampens high-count stems more, which hurts synthesis (where `supers`=12, `notes`=10 are its STRENGTH). **Makes it worse.**

**(f) Stem-length tuning.** The 6-char prefix makes `corrected` and `correcting` and `correction` all collapse to `correc`. The synthesis doc uses "correct" in the sense of "correct-by-construction" (a different semantic) at maybe 1-2 occurrences — still fewer than battery-slices. A 7-char prefix (`correct`, `correcti`) would fragment `corrected`/`correcting` into different stems — but the battery-slices doc uses BOTH forms. **Stem-length tuning shifts the numbers slightly, doesn't invert the ranking.**

**(g) Stop-stems for test-plan vocabulary.** A hardcoded list of stems that signal "this is a test plan, not rationale": `instea`, `correc`, `editin`, `projec` (in the sense of "project plan"). But these same stems appear in legitimate rationale: `project notes` IS the topic, `correct-by-construction` IS a rationale concept. Hardcoding kills legitimate answers. **Rejected correctly — would overfit C3 while breaking other probes.**

**Verdict: THE CEILING IS REAL.** The problem is not that the signal is too weak — it's that the signal is AMBIGUOUS. The question's own phrasing tokens (`instead`, `corrected`, `editing`) describe the MECHANISM of correction, and the displacer doc describes the MECHANISM of fixing bugs in test plans using those exact words. A lexical system cannot distinguish "test plan prose using the question's words" from "architectural rationale using different words." This is the definition of the lexical ceiling.

---

### 3. Disposition Verdict for C3

**Option (a) — Semantic relevance (embeddings, deferred v1).** Embeddings would map "corrected by superseding instead of editing" → a semantic neighborhood that includes "write-once discipline," "title-supersession," "immutable history." The synthesis doc's prose about "title-supersession actually fires" and "correct it by re-noting the same title" would be in that neighborhood even without the exact words `corrected`, `instead`, `editing`. **CORRECT LONG-TERM FIX.** Embeddings are the designed v1 upgrade path (the `relevance_fn` seam exists for exactly this swap).

**Option (b) — P4 Status header grows a doc-class field.** Add `class: rationale | plan | test | reference` to the Status header. WHY-questions weight `rationale`-classed docs up. Battery-slices would be classed `plan`; comms-pillar-synthesis would be classed `rationale`. The IDF mechanism already weights stems by rarity — this would add a DOCUMENT-LEVEL prior orthogonal to stems. **CORRECT SHORT-TERM FIX.** It's cheap (one field in the existing Status line, parsed by the existing `_doc_status` function), it doesn't require the embedding infrastructure, and it separates the two doc classes that currently collide: plan docs that catalog mechanisms vs rationale docs that explain architectural choices.

**My recommendation: DO BOTH, SEQUENCED.** Ship (b) now — it's a ~20-line change to `_doc_status`, `_docs_items`, and the Ranker importance weight. C3 likely recovers with a `class: rationale` weight boost of 1.5-2x on the relevance component. If it doesn't, C3 stays red-labeled, and (a) ships when embeddings land (v1, already on the ROADMAP). The `class` field is independently valuable — the "NOT-built" section of every design doc is rationale-dense, and lookback should know that without reading every word.

**Verdict on C3 status: keep RED-LABELED.** Not xfailed (the battery is canonical, not a test suite — a red probe means "this question cannot be answered from the corpus today"). Not re-registered (the question hasn't changed; the answer exists; the system can't find it yet). The `class` field is the next increment; embeddings are the destination.
