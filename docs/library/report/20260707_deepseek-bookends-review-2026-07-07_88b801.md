---
akashic_id: art_20260707_deepseek-bookends-review-2026-07-07_88b801
akashic_sha: 074ed3a20beb
status: draft
type: report
date: 2026-07-07
title: deepseek-bookends-review-2026-07-07
gist: "Direct. Answers first, then the missed stuff. **Q1 – `why` derivation.** Insufficient deterministic source. The *active task title* is **wha"
tenant: solo
visibility: fleet
seats: []
category: [performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-07T19:53:40"
updated: "2026-07-07T19:53:40"
---
<!-- GENERATED PROJECTION of art_20260707_deepseek-bookends-review-2026-07-07_88b801 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# deepseek-bookends-review-2026-07-07

Direct. Answers first, then the missed stuff.

**Q1 – `why` derivation.** Insufficient deterministic source. The *active task title* is **what** the work is, not **why** this episode exists (the “so that…”). That intent almost certainly lives in the conversational beats immediately preceding the objective switch — the “Ah, we need to… because…” You’ll spend S2 chasing heuristics that a <100-token LLM call would nail in S1. Ship with a cheap `writer` seam from the beginning, even if it’s just `f"Started {task_title} because: {last_decision_beat.text[:80]}"`. That’s token-frugal and no worse than your deterministic guess. I’ll also pull the **immediately prior `decision` or `mark` beat** as the primary source; the task title is secondary, for when that’s missing.

**Q2 – trigger phasing.** Agreed. Defer branch-checkout / arch-discussion / debugging. None are load-bearing for the core loop; they’re nice-to-have refinements. The four you have (new-objective, subsystem switch, long-idle, impl-complete) cover the most frequent episode boundaries. Ship them first.

**Q3 – episode == narrative Chapter?** Correct model. An episode **is** a `Chapter` with mandatory intent (`why`). There’s no coarser grouping in this design; the `mark` beat boundary already segments the session into exactly the chunk you want to call an episode. Do **not** create a separate `Episode` table — it will fork the narrative identity and force every query to join two objects that are always 1:1. Add `why: str` to `Chapter` and you’re done. The existing boundary primitive works; the *close-and-draft* step is the only new behavior.

**Q4 – contract JSON shapes.** Your `episode current --json` and `episode close --json` must return objects that a panel can render directly, no additional enrichment. Expect the following from **my** side (Bifrost):

**`episode current --json`** →
```jsonc
{
  "current_chapter": {
    "id": "ch_...",
    "title": "Fixing the parser",
    "description": "We fixed the parser’s off-by-one...",
    "why": "Request from QA; parser breaks on empty input.",
    "started": "2026-07-07T14:00:00Z",
    "duration_seconds": 1823,
    "beats_count": 34,
    "suggestion": null  // or { "title": "Add unit tests", "reason": "impl-complete", "confidence": 0.88 }
  }
}
```

**`episode close --json`** (returns **a draft** for me to edit, plus the start of the next chapter) →
```jsonc
{
  "draft": {
    "chapter_id": "ch_temp_A3F2",   // the closed chapter ID, still mutable
    "title": "Fixing the parser",
    "description": "We fixed the parser’s off-by-one...",
    "why": "Request from QA; parser breaks on empty input."
  },
  "new_current_chapter": {  // next chapter, empty/open
    "id": "ch_new_...",
    "started": "2026-07-07T14:30:23Z",
    "duration_seconds": 0,
    "suggestion": null
  }
}
```

After UI lets the user edit any field, I hit a follow‑up:

**`episode accept <chapter_id> [--title] [--desc] [--why] --json`** (idempotent) → returns the finalized chapter and marks it immutable; new-current chapter stays. No “edit session” sub-state; draft is just a chapter in a mutable pre-final phase. This keeps the seam simple — I never send a patch object.

If you want a single closing round-trip with no extra step, give me an `episode close --accept-title "..." --accept-desc "..." --accept-why "..."` that writes the fields and immediately finalises. That lets the AI/agent bypass the edit dialog entirely.

**Q5 – mis-scoping / risks Claude missed.**
- **S2 deterministic `why` as a required gate is premature.** You’ll invest effort in a heuristic that the LLM seam will supplant; the deterministic version will rot. Drop S2 as a distinct slice; fold the lightweight LLM seam into S1 and replace the heuristic entirely.
- **Auto-suggest requires UI parity with the manual path.** Your plan has no way for the user to **edit** a suggested title/why before accepting; the UI would need to render the suggestion with editable fields, same as the manual close. That’s in my domain, but the contract must support it. Make the `suggestion` object match the `draft` shape exactly (title, description, why) so I can reuse the same edit panel.
- **No signal for “chapter ended without explicit close”** — if the session ends mid-chapter, the current chapter needs a forced close and draft. Your manual backend must handle that, or you’ll leak chapters.
- **Boundary detector’s 4‑hour gap is a session‑level concept.** Idle as an episode trigger should be configurable (e.g., 15 min of inactivity *within* a session), not just the 4‑h inter-session gap. Make it a separate polling threshold (`episode_suggester`) or you’ll miss short breaks between sub-problems.
- **Claude’s mention of “RENEW” triggers** — if RENEW fires its own suggestion, we’ll get duplicate chapter‑close nudges. Ensure the auto-suggest and RENEW share a single event bus, or you’ll spam the agent.

That’s it. Ship S1 with the LLM seam, fix the contract, and proceed.
