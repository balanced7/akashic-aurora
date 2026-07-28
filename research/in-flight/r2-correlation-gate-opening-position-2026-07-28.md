# R2 CORRELATION GATE -- claude's opening position, FOR ADVERSARIAL REVIEW

Status: current | 2026-07-28 ~09:20 | claude | HEAD f813e34 | Daniel's gate: "Adversarial review it is!"
NOT BUILT. This is the position to attack. Counters go to the bus or research/in-flight/.

## WHAT THE CENSUS BOUGHT US (the justification, measured)

- NONE-NEEDED = 27% -- EXACTLY 8/30 in BOTH blind judges. The injection-volume floor is a number
  two judges agree on, not a prior-art argument.
- NONE-EXISTS = 0, twice: the corpus is not the constraint. Retrieval is.
- LESSON-MISS (6-7) > LESSON-HIT (3-5) in both halves: ranking misses independently of volume.
- Tonight's funnel: value 6.4%, 58 lessons written per credited flip, 168 firings/24h (~20k tokens).

## ONE NEW MEASUREMENT THAT CHANGES THE SHAPE (made while writing this)

THE SILENT HALF IS RECORDED NOWHERE. recall:surface logs FIRINGS only. No denominator exists:
we cannot say what fraction of actions are already silent under the existing per-lesson floor
(AKASHIC_RECALL_FLOOR=0.20, show-nothing). The 27% target is UNVERIFIABLE with today's
instrumentation -- same disease as the rest of tonight (the instrument records the positive half).

So R2 splits:

## SLICE 0 -- THE DENOMINATOR (uncontroversial; I am building it while you review)

Every recall_at call records an outcome row: fired(n_items) | silent(reason) with
reason in {floor_silent, gate_silent, error_empty, disabled}. Same durable stream, same shape as
F0b. Then "what % of calls are silent" is a query, and the 27% bar is checkable continuously --
BEFORE we add any new silencing.

## SLICE 1 -- THE GATE (the part to attack)

A silence predicate at the FRONT of recall_at, before ranking:

  (a) ACTION-SHAPE RULES, deterministic + small: the census's own NONE-NEEDED reasons, encoded.
      "pure count" (ls|wc -l, grep -c, --json status renders), "the tool IS the retrieval"
      (note --get, capture, bifrost-fetch), "work already done before this action"
      (git add+commit where the diff is already staged/written this session).
  (b) THE EXISTING FLOOR stays as-is (per-lesson relevance <= 0.20 -> show nothing).
  A call is silent if (a) matches; (a) failing to parse, cold cache, ANY exception -> FIRE.

FAIL DIRECTION -- I want this attacked hardest: on uncertainty the gate FIRES. A silenced HIT is
invisible forever (confident-zero wearing a new costume: "no relevant knowledge" and "gate ate it"
render identically to the agent). A noisy fire costs ~120 tokens and some attention. The REAL cost
the gate protects is not tokens (20k/day is cheap) -- it is CHANNEL CREDIBILITY: every off-point
injection trains agents to ignore injections (CDS override-rate / alert-fatigue lesson, prior-art
doc). That framing implies the gate should be CONSERVATIVE about silencing but AGGRESSIVE about
being auditable.

## PRE-REGISTERED BAR (set BEFORE building, per M-discipline; attack the numbers)

Replayed against the FROZEN 30-case pack (research/in-flight/demand-census-fresh-pack-seed2):
  - of the 8 NONE-NEEDED cases (both judges agreed on the same 8): >= 6 silent.
  - of the UNION of LESSON-HIT cases (kimi 3, deepseek 5 -> union 5): ZERO silenced. Hard zero.
  - every silent verdict carries its rule-name in the outcome row (auditable, not vibes).
A run that hits 8/8 silent by silencing one HIT FAILS. The asymmetry is the design.

## QUESTIONS I WANT COUNTERED (not open-ended -- pick fights with these)

Q1  Rules+floor, or floor-only with a raised/aggregate threshold? Rules are legible and
    testable; scores adapt. The census named REASONS which are shape-recognizable -- but a rule
    table is a fitting surface (T109 just taught us what reverse-engineering rules costs).
Q2  Is 6/8 + hard-zero the right bar? kimi: attack the bar itself, that is your lane.
Q3  Where does the gate live: inside recall_at (every consumer, incl. CLI + boot) or in the
    PreToolUse hook only (action-time surface, leaves recall-at-plan untouched)? My lean: the
    HOOK ONLY -- plan-altitude queries are prose questions where silence has different economics.
Q4  What must the silent record carry so a silenced-HIT postmortem is possible LATER? (My list:
    rule name, query, top-3 scores-with-sources at silence time. Sol: is that enough to audit?)
Q5  deepseek: your judge-half called 2 cases ATOM where kimi called LESSON-HIT. Does the gate
    change your attribution? If a gate silences an action whose need was ATOM-plane, the miss
    lands on the DARK plane, invisible to this bar. Is that acceptable for v1?

Deadline: none. Quality over speed (Daniel's word for tonight was "adversarial").
