# FENCE BRIEF — the eye PRESET register (S3-adjacent, T278 organ)

Status: DRAFT — seeking Daniil approval to open the fence.
Author: deepseek/Heimdall, 2026-08-24. Seat holding: tbd (see "Who writes what").

---

## 0 · The ask, verbatim

Daniil: *"How can we verbify or make presets to make the more robust results easier and
more reliable to access?"* — clarified in-conversation: he means **the eye**, not (only)
the `captions` verb. The `captions` gate is the same disease one plane over; this fence is
the eye half.

## 1 · Why this is the right next thing, and why it is NOT bolt-on

THE EYE (design atom `the-eye-design-v2_208b26`) treats "Build mode — inhabitants reshape
ergonomics" as an UNMAPPED primitive (§0). The eye is already BUILT through S6 (`core/eye/`
has index/pyramid/connectome/position/routes/directives, wired as the `eye` verb).
What no slice provides is the storage-and-retrieval of a NAMED, REUSABLE query — so the
"robust result" (a grammar string that took three tries to get right, a freq family that
found a lost directive) lives in ONE SEAT's history and is re-derived by archaeology every
session. That is the exact wound the eye was chartered to close ("we forget it every time"),
and it is still open at the one place it matters most: the question you already asked once.

A preset register is not a ninth verb bolted on. It is the BUILD MODE the design §0 lists
and leaves empty — made concrete as: **a named, immutable-ish, replayable `eye find`
grammar (or `eye freq` family) plus a fast-travel bookmark, stored per-seat, reachable in
one token.**

## 2 · THE SUBSTRATE SPLIT (non-negotiable, copied from routes.py — T323 s1)

A preset is an AUTHORED object. It must survive an `eye.db` rebuild, or the law
"wiping the projection loses nothing authored" is false. Copy the split EXACTLY:

- **`state/coord/eye_presets.jsonl`** — append-only, **TRACKED** (the authored truth, the
  Ledger half).
- **`eye.db presets`** (+ `preset_steps` if presets carry multi-step bodies) — queryable
  **projection**, rebuildable from the journal (the Store half).
- **Save = journal-first, then projection upsert.** `rebuild()` replays the journal.
- **Idempotency = content hash** (routes use a content-hash id so a crash-redelivered or
  double-pasted save is the SAME row). Presets inherit this: `preset_id = sha256(name + seat + body)`.
  Re-saving the same name with the same body is a no-op; re-saving the same name with a NEW
  body appends a new line (a preset is versioned by history, not overwritten).

This is not preference — it is the one rule that keeps a preset from being erased the first
time someone rebuilds the index, which is precisely when presets are most needed (the
rebuild is what resets a seat to "cold").

## 3 · The surface (two verbs, both read-shaped, both belong on the eye door)

**`eye preset save <name> [--find "<grammar>"] [--freq "<pat> ..."] [--go <addr>] [--note "..."]`**

- Stores a named query. A preset carries AT LEAST ONE body: a `find` grammar, a `freq`
  family, or a `go` address (fast-travel bookmark). It may carry more than one (see §4).
- `--by` is implied = the invoking seat's incarnation (same provenance convention as
  routes/roles); no flag to forge it.
- OUTPUT: the resolved preset id + a one-line "here is what this remembers" summary, so a
  save is auditable at a glance.

**`eye preset run <name> [--at <addr>] [--fresh]`**

- Executes the stored query against the CURRENT index (never against the saved results).
  `--fresh` forces a re-run rather than returning a cached envelope; default behaviour
  returns the live envelope exactly as `eye find`/`eye freq` would.
- `--at <addr>` runs the preset *as if* positioned there (composes with the position organ).
- `eye preset ls` and `eye preset show <name>` are the read-half (ls = names + one-liners;
  show = full body + history).

The verbs must be **READ-shaped at the door** (no mutation flags in the unattended-read
family) so a relay seat on an outage night can `preset run` the "what was I doing" preset
without an operator. `save`, being a write, goes through the door's write path like
`route save` does — it is NOT a read; do not smuggle it into the read allowlist.

## 4 · ONE RULE that makes it "more robust *results*" and not just "saved *queries*"

Daniil said *results*, not *commands*. A preset that stores only the query re-derives the
answer every time and is no better than a shell alias. The valuable thing a preset stores
is **the query + the receipt of what it found last time**:

- `last_run_ts`, `last_verdict` (for freq: unheard/recurring/standing-directive), `last_n`,
  and the **set of refs** it returned, capped (say 20 ids).
- On `run`, show the delta: "since you last ran this, N new events match, verdict moved
  X→Y". That is the "reliable" half — a preset becomes a thing you TRACK over time, not a
  thing you re-type. This is the `eye freq` standing-directive idea generalized to any query.

That single field-set is what separates this from `run`/toolbelt aliases (which are
stateless command shorthand) and earns it the name "preset."

## 5 · Hard scope (what this fence is NOT)

- NOT embeddings, NOT NL-query ("Ask-mode is a product surface; inhabitants speak
  grammar" — design §5).
- NOT a new UI. No write verbs beyond `preset save`/`ls`/`show`/`run`. The sensorium
  perceives; hands exist.
- NOT recall-at integration (a preset is not a lesson; do not store it in the learning
  store). If a recall AT trigger wants to suggest a preset later, that is a separate slice.
- NOT re-ranking/assertion logic (routes s3 territory). A preset runs; it does not judge.

## 6 · RED pins (the load-bearing acceptance, fences-standard)

1. **The rebuild pin (P1, inherited):** save 3 presets → wipe `eye.db` → `rebuild()` →
   `eye preset run <each>` returns the same body and history. A rebuild that loses a
   preset fails the organ. (Copy routes pin P5.)
2. **The idempotency pin (P2):** double-paste the same save → one row, one id. Re-save
   same name/different body → NEW id, history preserves both, `show` surfaces the latest.
3. **The provenance pin (P3):** `--by` cannot be forged by a flag; it is the invoking
   seat's incarnation. A preset saved by deepseek reads `by=deepseek` and nobody else's
   word can change that.
4. **The recency pin (P4):** `run` returns AGAINST CURRENT INDEX, not cached results; the
   delta field ("N new since last run") is real, never fabricated — a clipeed delta says
   "degraded", not "0 new".
5. **The read-door pin (P5):** `preset run`/`ls`/`show` pass the unattended-read family
   with NO mutation flag; `preset save` is refused by the read family (it is a write).

## 7 · Build slices (small, each independently shippable, pins first)

- **P-s0** schema + journal + projection + `rebuild()` replay (pins 1,2). No verb yet.
- **P-s1** `preset save` + `preset ls` + `preset show` (pin 3) — the write/read half.
- **P-s2** `preset run` + the recency delta (pins 4,5) — the "results, not commands" half.
- **P-s3** (optional) `--at <addr>` composition with the position organ + `--fresh`.

Estimated: half a focused session for P-s0/s1; P-s2 is the value and rides last. Every
slice: RED pin first.

## 8 · Who writes what (proposed, for Daniil to rule)

Deepseek (this seat) has already internalised the eye's substrate rules (routes.py split,
content-hash id, utterance collapse in `freq`). Proposal: deepseek holds **half_a**
(schema + journal/projection + save/ls/show + pins 1-3, the authored-object half), and a
peer (kimi or Rill — whoever Daniil names) holds **half_b** (run + recency delta + pins
4-5, the query-execution half). Blind rule as usual: neither reads the other's half before
sealing; tag rule ([CERTAIN|DESIGN|INFERRED|UNCERTAIN] on the verdict's FIRST physical line).

Ask: does Daniil approve opening this fence, and who writes half_b?
