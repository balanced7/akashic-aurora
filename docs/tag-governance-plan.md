# Tag Governance — safe, self-improving tagging (plan + test plan)

> Status: PLAN (plan-first, build-in-slices, each gated by acceptance bars AND safety
> invariants). Companion to `docs/narrative-spine-plan.md` + `docs/perspectives-maps-plan.md`.
> Best built after / alongside Slice 6 embeddings (the label model's strongest signal).

## The principle

**A tag is a re-derivable *opinion* over an immutable *fact*. Cleanup re-derives the
opinion; it must never touch the fact.** Hold that line and "successive runs erasing
data" becomes structurally impossible.

**The guarantee:** the worst case of any cleanup run is a **no-op**. Facts never move;
tags can only become *more confident or confirmed*, never silently downgraded. Accuracy
ratchets up; data never ratchets down.

(Origin lesson: cleaning the stemroller mis-tag, an agent *deleted the beats* instead of
*re-tagging* them — deleting a fact to fix a bad opinion is the exact data-loss trap this
plan prevents. Recorded in the spine as `retag_never_delete`.)

## The model

- **Fact (substrate)** — beats / events / edges / the Ledger. Immutable, append-only.
  A tag operation NEVER deletes or edits a fact, only its tag.
- **Tag (opinion)** — `track` (and later `themes`) is **append-only history**:
  `[{track, confidence, source, at, confirmed}, …]`. The *current* tag = the
  highest-confidence non-superseded entry. Re-tagging appends; the prior tag stays.
- **Confidence** — derived from the router basis (path 0.95 · strong 0.85 · category 0.6 ·
  generic 0.4 · persist 0.3 · unknown 0.1), a model probability, or `confirmed = 1.0`.

## Safety invariants (the worst-case spec — every slice tests the ones it touches)

| # | Invariant | Test shape |
|---|---|---|
| **I1 Immutability** | no op ever deletes/edits a fact (beat.source/summary, raw event) | after ANY op sequence, the set of substrate facts is identical |
| **I2 Monotonicity** | current-tag confidence never *decreases* except via explicit human downgrade | property/fuzz: random re-tag sequences never lower a confirmed/high tag |
| **I3 Append-only** | every tag change is recorded; nothing silently overwritten | history grows; every prior tag recoverable |
| **I4 Reversibility** | any tag state is restorable (per-tag history + snapshot) | roll back to a prior tag; snapshot-restore round-trip |
| **I5 No hard-destroy** | "delete" = quarantine (recoverable namespace), never `del` | quarantine round-trip restores |
| **I6 Read-only detect** | flagging suspects never mutates anything | store byte-identical before/after a scan |

## Mechanisms (grounded in prior art)

- **Weak supervision / label model** (Snorkel) — each router signal (path, strong-kw,
  category, embedding-nearest, neighbour-agreement) is a **labeling function** that votes
  or abstains; a label model learns each LF's reliability from agreement/disagreement and
  combines them into a track + calibrated confidence. Multi-signal consensus > any single
  rule. https://snorkel.ai/data-centric-ai/weak-supervision/
- **Confident learning** (Cleanlab) — use model probabilities to flag tags that disagree
  with the confident prediction; no hyperparameters, no guaranteed-correct labels needed.
  Flag for review, never auto-act. https://dcai.csail.mit.edu/2024/label-errors/
- **Bi-temporal / supersede-don't-delete** (Zep) — the append-only tag history.
- **Active learning (uncertainty sampling)** — confirmations of flagged cases become
  permanent gold-fixture rows; the model is re-evaluated against the growing fixture in CI
  → accuracy ratchets up, can't regress on what it's learned.

---

## Slices (each independently testable; leaves the suite green)

### G0 — Tag history + confidence schema
- **Bar:** `Beat` gains a tag-history; current-tag = highest-confidence non-superseded;
  basis→confidence mapping. No behavior change to routing yet.
- **Shape:** round-trip; current-tag selection; basis→confidence.
- **Worst-case:** empty history; tie-confidence (break by `confirmed` then recency); a
  corrupt history entry is skipped, not fatal; a beat with no tag → "unknown"/0.1.
- **Invariants:** I3 (append-only), I4 (reversible).

### G1 — Append-only, confidence-gated re-tag (the safety core)
- **Bar:** `retag(beat, track, confidence, source)` appends; current changes ONLY if
  `confidence > current` or `confirmed`. `confirm_tag()` pins (1.0, confirmed). `rollback()`.
- **Shape:** a higher-confidence re-tag wins; an equal/lower one appends but doesn't change current.
- **Worst-case (the headline):**
  - **a low-confidence run cannot overwrite a high-confidence tag** (I2).
  - **a confirmed tag is never auto-overwritten** — even by a higher-confidence *auto* re-tag (only an explicit human downgrade).
  - **fuzz: 1,000 random low-confidence re-tags leave every confirmed/high tag unchanged** (I2) and every fact unchanged (I1).
  - rollback restores a prior tag (I4); re-tag is idempotent (re-applying = no-op on current).
- **Invariants:** I1, I2, I3, I4.

### G2 — Mis-tag detection (confident learning + consistency), FLAG-ONLY
- **Bar:** `flag_suspect_tags()` returns candidates (low-confidence, model-disagreement,
  lone-tag-in-a-run, weakly-connected-in-the-reinforced-graph). Returns; never mutates.
- **Shape:** a planted ZLUDA-style mis-tag is flagged.
- **Worst-case:** high-confidence/confirmed tags are **NOT** flagged (no false alarms on
  good data); empty store → no flags, no crash; all-confirmed store → 0 flags; corrupt
  beat skipped.
- **Invariants:** I6 (the scan is byte-read-only — assert store unchanged after).

### G3 — Weak-supervision label model (multi-signal consensus)
- **Bar:** combine LFs (path/strong/category/embedding/neighbour) → track + calibrated
  confidence; **must beat the single-best-LF baseline ARI on the gold fixture** (ablation).
- **Shape:** consensus resolves a conflict by learned reliability (reliable path LF beats
  unreliable persist LF); abstentions don't vote.
- **Worst-case:** all LFs abstain → unknown + lowest confidence (no crash); all LFs
  disagree → lowest confidence (so it's flaggable, not silently wrong); one LF is a
  constant liar → its learned reliability collapses, it stops dominating.
- **Metric:** ARI vs baseline; a calibration check (higher-confidence tags are measurably
  more accurate than lower).

### G4 — Quarantine-not-delete + the safe cleanup op
- **Bar:** `quarantine(key, reason)` → `quarantine:` namespace (recoverable). The cleanup
  op = snapshot → flag → confidence-gated re-tag of low-confidence only → quarantine true
  artifacts (with reason) → never touch facts/confirmed/high-confidence.
- **Shape:** quarantined item restores (round-trip); cleanup re-tags a low-confidence
  mis-tag to the right track.
- **Worst-case (the user's nightmare, as a test):**
  - **run cleanup N times in a row → confirmed/high tags unchanged, facts unchanged, no
    compounding degradation** (I1+I2 fuzz).
  - cleanup never deletes a fact (substrate key-count preserved; artifacts go to quarantine).
  - cleanup is reversible (snapshot restore + per-tag rollback both recover).
  - cleanup on a corrupt/empty store → consistent state, no crash; a mid-run failure leaves
    a consistent state (idempotent re-run completes it).
- **Invariants:** I1, I2, I4, I5.

### G5 — Active-learning loop + standing eval
- **Bar:** confirmations append to the gold fixture; `test_tag_governance.py` runs the
  whole battery — all six invariants + the accuracy/calibration/detection metrics — and is
  CI-gated. Accuracy on past corrections can never regress (they're permanent fixture rows).
- **The loop:** flag → human/agent confirms a few → fixture grows → label model + confident-
  learning re-evaluated → ratchet.

---

## Honest bounds

- The label model needs *some* signal diversity; if every LF uses the same keyword, it
  can't out-vote a shared blind spot — embeddings (a different signal) are what break ties.
- Confidence calibration is approximate; treat "high confidence" as "don't auto-touch,"
  not "certainly correct."
- Active learning improves where it's *reviewed*; unreviewed regions stay at baseline. The
  flag queue is only useful if someone (human or agent) works it.
- This governs *tags*, not *facts* — a wrong fact (a bad raw event) is a separate concern
  (the autologger's capture quality), out of scope here.

## How it maps onto what we have

- The router already emits `basis` → that's the confidence level, ready to record.
- `snapshot_knowledge.py` gives batch reversibility (I4); the harmonization's quarantine
  pattern gives I5.
- Bi-temporal fields already on Chapters → the same shape for tag history.
- Embeddings (Slice 6) + the reinforced graph (P1, done) are two new labeling functions.

## Prior art
Snorkel / weak supervision; Cleanlab / confident learning; Zep bi-temporal; active learning
(uncertainty sampling); data-centric AI. (URLs in research learnings: `recall weak supervision`
/ `recall confident learning` / `recall tag governance`.)
