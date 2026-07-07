# RENEW Strand E — Cold-resume fidelity (empirical)

**Status:** first pass complete + gap #1 fixed, 2026-07-07 · **Author:** claude
**Scope:** open-docket item E (`[EMPIRICAL]`) — "Is the existing curated save (boot payload) *sufficient*
to resume as well as full context? If yes, Renew is mostly wiring; if no, the distiller needs work
before any of this matters."
**Design context:** `docs/agent-membrane-design-2026-07.md` §Renew (deferred step #3 = arch slice).

---

## Verdict

**No — the boot payload was NOT sufficient to resume, but the cause is cheap surface clipping, not a
lossy distiller.** Two named gaps; #1 fixed this pass, #2 scoped as the next slice. This is the *good*
branch of the docket's fork: Renew is mostly wiring, not "rebuild the distiller."

## Evidence (this session was the experiment)

At boot, `py agent_cli.py boot claude` surfaced the durable notes each clipped to **110 chars**
(`agent_cli.py cmd_boot`, `_clip(d.decision, 110)`). The resume-critical notes are long:

| note | full chars | shown at 110-char clip |
|---|---:|---|
| where-we-are 2026-07-07 | 5,895 | first line of a "Shipped:" changelog |
| open-docket | 1,480 | first ~1 of 5 research strands |
| SESSION HANDOFF | 1,466 | "membrane 1+2 done, 2 open flags…" then cut |
| renew-membrane-temporal-job | 814 | ~2 sentences |

**Direct behavioral proof:** immediately after boot I had to run `py agent_cli.py notes --json` to
recover the full `open-docket` and `where-we-are` before I could choose the next task. A second
full-context fetch to resume = the boot payload was, by definition, insufficient. The dense multi-item
notes (`open-docket`) are exactly the ones a one-line clip destroys.

## The two gaps

1. **Notes clipped to one line (FIXED this pass).** The notes *are* the resume anchor, but a flat
   110-char clip collapsed multi-item state to a stub. **Budget was not the constraint** — boot ran at
   ~3,755 / 9,000 tokens (~5,245 headroom); the full top-6 notes are only ~2,820 tokens. Fix:
   **tiered-by-recency fidelity** in `cmd_boot` — freshest note ~900 chars, next two ~500, older three
   ~220 (worst case ~640 tokens), plus a "(clipped; full bodies: `notes --json`)" pointer so the one-hop
   escape is explicit. The resume anchor now rides in the payload itself.

2. **No arch slice (OPEN — next slice).** This is the design doc's known *deferred step #3*
   ("Surface→orientation"): boot carries task ledger + lessons + notes + funnel + bifrost, but **nothing
   orienting the agent to the code region of the current task** (which modules, the LEXICON terms, the
   ARCHITECTURE altitude for this slice). A cold agent still discovers the code layout by re-reading.
   Scope it against `docs/ARCHITECTURE.md` + `docs/lexicon.md` + the task's file set; gate on a
   benchmark (does adding it reduce first-N exploratory reads?). Deliberately **not** bundled here —
   measure-before-build, and it's a real feature, not a clip tweak.

## Why this matters for Renew

The docket framed E as a fork: sufficient → Renew is wiring; insufficient → fix the distiller first.
The real answer is a **third branch**: insufficient, but because of a *surface* clip and a *missing
section*, not distiller quality. The distiller/ranker output (the LESSONS skeleton) was fine. So Renew
stays "mostly wiring" — the paging function reloads a curated set that is now materially more complete.

## What's still unmeasured (honest bounds)

- n=1 (this session). The 110-char insufficiency is structural, not a fluke, but the *tiered budgets*
  (900/500/220) are a first cut — tune once more sessions show whether the anchor survives in practice.
- "Sufficient to resume" has no deterministic score yet (an LLM judge is disallowed). A cheap proxy for
  the gate D-style test: **count full-context re-fetches per session** (`notes --json`, wide re-reads
  right after boot) before vs after this fix — a behavioral, no-LLM signal, and it composes with the
  Strand A′ `fail`-label instrumentation.

---
*Fix landed in:* `agent_cli.py` `cmd_boot` (tiered notes fidelity + clipped-pointer).
