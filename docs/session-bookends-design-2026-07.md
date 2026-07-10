# Session Bookends — design (for peer review before build)

Status: current  (2026-07-09, P4: Shipped design still describes what is built)

**Status:** REVIEWED by DeepSeek 2026-07-07, decisions locked — building S1 · **Author:** claude
**Feature owner:** Daniel (+ GPT), spec v3 (note `session-chaptering-bookends-idea`)
**Review:** `research/reviewed/deepseek-bookends-review-2026-07-07.md` (full).

## 0. Review outcome — locked decisions (DeepSeek 2026-07-07)

- **Q3 crux CONFIRMED:** an episode **is** a narrative `Chapter` with a mandatory `why`. **No separate
  Episode table** (it forks narrative identity → permanent 1:1 joins). Just add `why: str` to `Chapter`.
- **Q1 REVISED:** deterministic `why` is insufficient (task title = *what*, not *why*). Ship a **cheap
  LLM `writer` seam in S1**; primary `why` source = the **decision/mark beat immediately preceding**
  the boundary, task title secondary. Keep a deterministic **fallback** (no key / fail-soft), but the
  LLM is the primary path — so **S2 is dropped as a distinct slice** (folded into S1).
- **Q2 CONFIRMED:** defer branch-checkout / arch-discussion / debugging-starts.
- **Q4 CONTRACT LOCKED:** shapes below (§6), from DeepSeek. `suggestion` object matches the `draft`
  shape so the UI reuses ONE edit panel.
- **Q5 gaps ADOPTED:** (a) drop S2; (b) **session-end must force-close+draft** or chapters leak —
  S1 handles it; (c) idle trigger needs an **episode-level ~15-min threshold** in `episode_suggester`,
  separate from the 4h session gap; (d) **auto-suggest + RENEW share one event bus** to avoid
  double-nudging.

---

## 1. What we're building (from the v3 spec)

Manual + automatic **bookends** that segment a session into confined, titled **EPISODES**, each carrying
**WHAT** (title + one-line description) and **WHY** (the intent/objective of that span). One boundary
primitive; two emitters:

- **USER button** (no title-first): click → close the current chapter → **AI drafts** `{title,
  description, why}` over the just-closed span → present with **per-field** edit (Accept / Rename /
  Edit Description / Edit Why).
- **AGENT auto-suggest**: a live "current chapter" panel (duration, confidence) + a suggestion
  `"AI suggests end chapter: <title> — reason: <topic shifted>"` `[Accept][Ignore][Continue]`.
  Signals = new objective · subsystem change · long idle · branch checkout · impl-complete ·
  arch-discussion-begins · debugging-starts. **These are the same RENEW refresh triggers** —
  the feature composes with the membrane work just shipped.

## 2. What already exists (~65% — scope pass 2026-07-07)

The narrative spine (Atlas→Track→**Chapter**→Beat) already gives most of the substrate:

| Piece | Exists as | Verdict |
|---|---|---|
| Chapter primitive | `core/narrative/schema.py` `Chapter{id,track,title,summary,beats,span_start,span_end,valid_from/to}` | title+summary ✅, **`why` MISSING** |
| Boundary detection | `chronicler.py` `BoundaryDetector` — `mark` beats, >4h gap, salience spikes | ✅ (mark-beat = manual boundary) |
| Beat→chapter distillation | `Chronicler._build_chapter` via `Consolidator`+`Distiller`+`Ranker` | ✅ reusable for drafting |
| Session lifecycle | `core/narrative/session.py` `start/end_session`, `narr:session:open` | ✅ (whole-session only) |
| Subsystem-change signal | `track_router.py` `RouteResult.switched` | ✅ |
| New-objective / impl-complete | `coord/task_ledger.py` transitions (PROPOSED→…→DONE) | ✅ |
| Long-idle | `BoundaryDetector(min_gap_hours=4)` | ✅ |
| Per-beat themes | `theme_discovery.py` `assign()` | ✅ but per-beat, no **span-level shift** |
| Branch-checkout / arch-discussion / debugging-starts | — | ❌ MISSING |
| UI panel + button | `bifrost_ui.py` has SSE/panel infra, no chapter panel | ❌ (DeepSeek's domain) |

## 3. Design decisions (proposed — please challenge)

**D1. Chapter gains a `why` field.** Add `why: str = ""` to the `Chapter` dataclass (bi-temporal
schema unchanged). It is the episode's intent, distinct from `summary` (what happened).

**D2. Reuse the existing boundary primitive; add explicit close-and-draft.** A manual bookend is a
`mark` boundary beat (already forces a chapter) PLUS a new **close+draft** step. No new boundary type.

**D3. Drafting is deterministic-first, LLM-optional (project discipline: no-LLM default, token-frugal).**
Over the just-closed span's beats:
- **title** ← the `mark` beat's text if the user typed one, else the highest-salience beat (existing logic).
- **description** ← the distilled skeleton (existing `Consolidator`/`Distiller`).
- **why** ← derived from the span's **objective signals**: the active `task_ledger` task title(s) +
  any `decision`/`mark` beats in the span. If a Distiller LLM `writer` seam is wired, it may refine;
  default stays deterministic. *(Open question Q1 below.)*

**D4. Auto-suggest is ADVISORY, never forced** (mirrors the Bifrost fidelity ladder: interactive Claude
gets a recommendation, not a HALT). A new `core/narrative/episode_suggester.py` watches the existing
signals and, on a trigger, emits a suggestion record (confidence + reason) for the UI to render. It
**never closes a chapter itself** — the human/agent accepts.

**D5. Trigger coverage, phased.** Ship with the signals that already exist (new-objective, subsystem-
change via `track_router.switched`, long-idle, impl-complete). Defer branch-checkout (needs a git
signal), arch-discussion / debugging-starts (need a keyword/theme signal) to a later slice — they're
additive, not blocking. *(Q2.)*

**D6. UI/backend boundary.** Per our standing integration boundary, **DeepSeek owns `bifrost_ui.py`**;
I author the backend + CLI + a stable **contract** DeepSeek renders against. I hand off: the `episode`
verb's JSON shape (current-chapter state + draft object) and a panel sketch. No UI code from me.

## 4. Proposed slice plan (each gated by a test/benchmark)

- **S1 — manual backend + CLI (my ownable slice).** `why` field · `close_chapter(store, now, title?,
  why?)` lifecycle fn · `agent_cli.py episode` verb (`episode close [--title][--why]`, `episode current
  --json`) · deterministic `{title,description,why}` draft over the closed span · unit tests + a live
  boot/story render. Complete, testable loop with zero UI.
- **S2 — draft quality.** Sharpen the `why` derivation; optional Distiller LLM seam; acceptance test on
  a fixture span (right objective → right why).
- **S3 — auto-suggest backend.** `episode_suggester.py` over existing triggers → advisory suggestion
  records (confidence+reason). Gated: does it fire on a real subsystem switch and NOT on noise?
- **S4 — UI (DeepSeek).** Current-chapter panel + close button + per-field accept/edit, rendered against
  the S1 contract. New triggers (branch-checkout etc.) as they land.

## 5. Questions for DeepSeek (please answer in your review)

- **Q1 — `why` derivation.** Is "active task title + decision/mark beats in the span" a sufficient
  deterministic source for WHY, or does WHY genuinely need the LLM writer seam from slice 1? What would
  you pull for WHY?
- **Q2 — trigger phasing.** Agree to ship S1/S3 on the 4 existing signals and defer branch-checkout /
  arch-discussion / debugging-starts? Or is one of those load-bearing enough to include now?
- **Q3 — boundary model.** Reuse the `mark`-beat boundary (D2), or does an explicit `episode` need to be
  a *distinct* record from a narrative `Chapter` (i.e. is an episode == a chapter, or a coarser grouping
  of chapters)? This is the crux — get it wrong and we duplicate the spine.
- **Q4 — the contract.** What JSON shape do you want from `episode current` / `episode close` to render
  the panel cleanly (so we don't thrash the seam like the old `bifrost_ui.py` lock)?
- **Q5 — anything mis-scoped.** Where is this over- or under-built vs the v3 spec?

---
*Scope basis: narrative spine files above; this feature is a control-loop over Chapter + Distiller +
triggers, not a new subsystem — same shape as RENEW.*

## 6. Locked contract (DeepSeek's UI seam) — build S1 to THIS

`episode current --json`:
```json
{"current_chapter": {"id": "ch_...", "title": "...", "description": "...", "why": "...",
  "started": "ISO", "duration_seconds": 1823, "beats_count": 34,
  "suggestion": null }}
```
`suggestion` (when present) matches the draft shape + reason/confidence:
`{"title": "...", "description": "...", "why": "...", "reason": "impl-complete", "confidence": 0.88}`

`episode close --json` (returns a mutable draft + opens the next chapter):
```json
{"draft": {"chapter_id": "ch_...", "title": "...", "description": "...", "why": "..."},
 "new_current_chapter": {"id": "ch_...", "started": "ISO", "duration_seconds": 0, "suggestion": null}}
```
`episode accept <chapter_id> [--title][--desc][--why] --json` — idempotent; writes fields, marks the
chapter immutable (finalized); the open next-chapter stays. No patch object, no edit sub-state.

One-shot (agent/AI bypasses the edit dialog): `episode close --accept-title "..." --accept-desc "..."
--accept-why "..."` — writes + finalizes in a single round-trip.

## 7. Revised slice plan
- **S1 (my ownable slice, building now):** `why` field on `Chapter`; `close_chapter()` lifecycle;
  `agent_cli.py episode` verb (`current`/`close`/`accept`, `--json`, one-shot accept flags); draft
  `{title,description,why}` over the closed span (LLM `writer` seam + deterministic fallback, `why`
  from the prior decision/mark beat); **session-end force-close+draft** (no leaked chapters); tests +
  live render. Emits nothing to `bifrost_ui.py` — DeepSeek renders against §6.
- **S3 — ✅ SHIPPED 2026-07-08 (T009):** `core/narrative/episode_suggester.py` over the 4 existing
  triggers + the episode-level ~15-min idle; advisory suggestions (confidence+reason) on the **shared
  event bus** (`episode_suggestion` raw events — RENEW-dedup per Q5d). Composed at the door:
  `episode current --json` now fills the contract's `suggestion` field. Two findings hardened it:
  subsystem-switch reads the last ≥2 ROUTED beats (the live router key drifts on every emit), and the
  close-boundary `mark` beat is filtered from the next span's content (`episode.content_beats`) — it
  was becoming the next episode's drafted `why` and a phantom trigger input.
- **S4 — ✅ SHIPPED 2026-07-08 (T010):** current-chapter panel (header chip + docked panel) + End-episode
  button + per-field draft editor + advisory suggestion banner ([Accept][Ignore][Continue], localStorage
  suppression), against §6 via `/episode/current|close|accept` — thin adapters over the tested core.
  *Lane note:* built by claude on Daniel's direction (fleet paused) under the advisory lock, per the
  any-agent/any-task model; DeepSeek notified on the bus and owns follow-up styling in its lane.
