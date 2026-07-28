# DEMAND CENSUS -- RECONCILED. Two blind judges, one build order.

Status: current | 2026-07-28 | claude reconciling kimi + deepseek (blind: deepseek judged
without reading kimi's labels, per protocol)
Halves: demand-census-kimi-judge-2026-07-28.md | demand-census-deepseek-judge-2026-07-28.md
Pack: research/in-flight/demand-census-fresh-pack-seed2-2026-07-28.md (30 cases, seed=2)
Bar, quoted per case by both: "would the agent's next action have been DIFFERENT if this item
had been available?" Method fixed BEFORE judging (fleet-debate reconciliation, adopted 3/3).

## THE TALLY

    CLASS          kimi   deepseek
    NONE-NEEDED       8      8      <- EXACT
    NONE-EXISTS       0      0      <- EXACT
    CODE-DOC          5      5      <- EXACT
    LESSON-MISS       6      7
    LEDGER            4      3
    NOTE              3      2
    ATOM              3      2
    LESSON-HIT        3      5

    aggregate     kimi          deepseek
    lessons       9  (30%)      12 (40%)
    dark planes   15 (50%)      12 (40%)
    none-needed   8  (27%)      8  (27%)

## THE FOUR FINDINGS, IN ORDER OF WHAT THEY SETTLE

1. NONE-EXISTS = 0, TWICE, INDEPENDENTLY. Not one action in thirty needed knowledge the
   corpus does not hold. THE CORPUS IS NOT THE CONSTRAINT -- this is a RETRIEVAL problem,
   never a capture problem. Every "we should write more lessons" instinct is now measured
   as answering the wrong question. (It also retires the NONE-EXISTS class's own purpose:
   it was there to catch a write-side gap, and there isn't one.)

2. NONE-NEEDED = 27%, EXACTLY THE SAME IN BOTH. Over a quarter of real actions needed
   NOTHING. That is the injection-volume floor, measured and replicated, and it is the
   CORRELATION GATE's justification: at minimum 27% of firings should be silent. The gate
   is no longer a prior-art argument; it is a number two judges agree on.

3. DARK PLANES CARRY 40-50% OF DEMAND -- above the debate's 40% threshold on BOTH readings.
   The second retrieval plane PAYS, and the census names it: NOTES / LEDGER / CODE-DOC
   (authoritative-state and doc planes), NOT more lessons. Sol's cell-architecture question
   is answered by measurement rather than assertion.

4. LESSONS SERVE A MINORITY (30-40%) AND MISS MORE THAN THEY HIT. LESSON-MISS (6-7) exceeds
   LESSON-HIT (3-5) in both halves: even inside the lit plane, the right item more often
   stayed dark than surfaced. Ranking work is justified INDEPENDENTLY of the volume cut --
   which is exactly the "both mechanisms are real" position the fleet debate reached (C3)
   and this census was built to apportion.

## THE ONE DISAGREEMENT, AND WHY IT DOES NOT MOVE THE BUILD

deepseek reclassified ~2 cases from ATOM to LESSON-HIT, stating it plainly (case 29): "the
lesson IS what the atom says... having it surfaced is exactly right." kimi called the atom
authoritative; deepseek called the surfaced lesson sufficient. That is a real boundary
question -- when a lesson RESTATES design intent, does demand belong to the lesson plane or
the plane holding the original? -- and it is worth settling later for attribution accuracy.
It moves lessons 30->40% and dark 50->40%. BOTH readings clear the 40% threshold, so the
build order is invariant under the disagreement. Recorded, not resolved; no third round.

## WHAT THIS GATES (for Daniel's morning table)

  R2 CORRELATION GATE  -- justified by finding 2 (27% of firings should be silent) AND by
                          finding 4 (ranking misses independently). Measured against the
                          frozen 30-case pack, which already exists.
  SECOND PLANE         -- justified by finding 3, and SCOPED by it: notes/ledger/code-doc.
                          This is the Sol/cell-architecture question, answered.
  NOT JUSTIFIED        -- "write more lessons" (finding 1: NONE-EXISTS is zero).

## PROCESS NOTE

deepseek's handoff CLIPPED at 8000 chars ("full content did NOT send; resend in chunks") --
the tally and its stated disagreement survived, per-case detail beyond case 30 did not. This
is exactly the T2 manifest gap ({part i/N, whole_sha} + INCOMPLETE render) still open in S5:
a multi-part delivery with no manifest cannot tell a reader what it lost. The tally is intact
and both judges' aggregate numbers are trustworthy; if per-case archaeology is ever needed,
re-request in chunks.
