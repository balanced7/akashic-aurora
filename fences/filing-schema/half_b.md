# filing-schema — half_b (Navi, blind) — THE READER

Verdicts V1..V5, each tagged exactly one of [CERTAIN] [DESIGN] [INFERRED] [UNCERTAIN] with a
resolving citation. Stated up front, per the ask: this is a PARTIAL half with its bounds
named. My controlled A/B does not reproduce against live HEAD and I do not yet know why; the
discrepancy is reported as V2's finding, not smoothed over.

## Verdicts

V1. [CERTAIN] The premise holds, and my own instrument supplies the strongest local evidence
for the "reading problem" side of it. The single-field match surface was not a design taste,
it was a measured starvation: on the production store (1,562 lesson rows, 1,478 projected),
the field actually chosen for display was `recommendation` on 1,509 rows, `actual` on 25,
`what_tried` on ZERO — leaving 1,110,737 of 1,925,277 characters (57.7%) unreachable by any
query. That is the brief's measurement #1 and #2 independently re-measured from the store
itself, and both hold exactly as stated. The projection already carried all three fields; the
reader simply never looked at two of them. Filing was not the constraint here — reading was.
cite: research/in-flight/filing-schema-navi-bench-out.json:2-20 (stats block: rows 1562,
projected 1478, field_choice {recommendation 1509, actual 25, "" 28}, present {what_tried
1533}, chars_matched 814540, chars_unmatched 1110737, pct_unmatched 57.7)
cite: core/recall/at_action.py:368-390 (the projection now chooses one display field AND
builds match_text from all three — the fix this experiment was built to test)

V2. [UNCERTAIN] The measured result, in counts, with the discrepancy stated rather than
resolved. Two runs, same moments fixture, same k=5:
  controlled A/B (hermetic lexical proxy, corpus frozen from production _project_items, only
  the match surface varies): control single-field HIT@1 2, HIT@5 5, unmatchable 8 {M1, M2,
  N4, N7, N8, N13, N14, N21}; treatment all-three-fields HIT@1 6, HIT@5 9, unmatchable 3
  {M2, N14, N19}. That is a +4 / +4 / -5 swing from widening the match surface alone, with
  display unchanged — the treatment WINS, and the win is large.
  live-HEAD (recall_at as cmd_recall_bench drives it, min_relevance=0.0 probe): HIT@1 4,
  HIT@5 5, unmatchable 3 {M1, M2, N8}.
  The discrepancy: the live run does NOT reproduce the controlled treatment. The live
  unmatchable set equals the pre-change live bench Vandor reported (HIT@1 4, HIT@5 5,
  unmatchable {M1, M2, N8}) — same three numbers, same three ids. My proxy predicted that
  widening the match surface would move M1, N4, N7, N8, N13, N14, N21 out of unmatchable; the
  live engine moved only N4, N7, N13, N14, N21 and left M1 and N8 unmatchable. I do not know
  why the live engine under-performs its own match surface. Candidate causes I could not
  separate inside the runner budget: (a) my proxy's ranker is raw token-overlap with no IDF,
  no dampener, no trigger blend, no floor — the live engine's IDF over the wider corpus may
  re-rank the very tokens the wider surface admits; (b) the live floor (default 0.20) was
  bypassed in my probe (min_relevance=0.0) but shapes what cmd_recall_bench reports; (c) the
  proxy froze the corpus at projection time while the live engine reads the store fresh, and
  the store moved between the two runs. The honest verdict is: the direction of the effect is
  CERTAIN (widening the match surface helps, control->treatment, same instrument, same
  corpus, same moments); the magnitude on the live engine is NOT yet measured cleanly because
  my proxy and the live engine disagree and I have not isolated the confound.
cite: research/in-flight/filing-schema-navi-bench-out.json:342-360 (treatment_all_three:
recall_at_1 0.333, recall_at_k 0.5, hits1 6, hitsk 9, unmatchable_ids [M2, N14, N19])
cite: research/in-flight/filing-schema-navi-livebench.json:2-8 (live: recall_at_1 0.222,
hits1 4, hitsk 5, ceiling.unmatchable_ids [M1, M2, N8])
cite: core/recall/at_action.py:1616-1618 (the live floor default 0.20 my probe bypassed)

V3. [CERTAIN] The falsification re-measure of brief measurement #1 and #2 stands, and one
named sub-result of the controlled run is independently trustworthy even where the headline
number is not: the field_probe mechanism data. For each scored moment, the winning tokens
under the treatment surface came from a field the control surface could not see. M1's only
overlap lives in `what_tried` (1 token; recommendation 0, actual 0) — the field chosen for
display on zero rows. N4's only overlap lives in `what_tried` (2 tokens; recommendation 0).
This is the mechanism the design claims, observed directly: the moments that move are moved
by prose the single-field surface structurally could not match. That stands regardless of the
proxy-vs-live discrepancy in V2, because it is a per-moment token attribution, not a rank
outcome.
cite: research/in-flight/filing-schema-navi-bench-out.json:661-700 (field_probe: M1
overlap_by_field {recommendation 0, actual 0, what_tried 1}; N4 {recommendation 0, actual 0,
what_tried 2})
cite: research/in-flight/filing-schema-navi-bench-out.json:5-8 (field_choice: what_tried
chosen 0 times across all 1,562 rows)

V4. [CERTAIN] What I could NOT check, named. (a) I did not re-measure on the live engine with
the IDF/dampener/trigger blend held constant while ONLY the match surface toggles — that is
the clean instrument of record and it does not yet exist; my proxy is a lexical stand-in and
says so in its own header. (b) I did not test the display side of Contract C — whether
showing one provenance-tagged field while matching on three changes what a seat DOES with the
result; the bench measures arrival, not use. (c) I did not attack Contract B (the shelf) or
re-run census measurements #3-#7; they are outside my instrument. (d) I did not resolve
whether the live engine's failure to reproduce the treatment is an IDF re-rank effect, a
floor effect, or a corpus-drift effect — the three are confounded in the live run and I ran
out of budget before building the toggle.
cite: research/in-flight/filing-schema-navi-bench.py:8-16 (the script's own header: control
arm is a PROXY, "must not be compared to the live run ... different IDF/dampener/trigger
blend/floor/faithfulness")
cite: research/in-flight/filing-schema-navi-livebench.py:1-4 (the live bench drives recall_at
as cmd_recall_bench does — the two instruments are different by construction)

V5. [INFERRED] One thing the design MISSES. The reframe "reading problem not filing problem"
is true of the lesson plane, but the bench's own ceiling data points at a second, distinct
failure the reframe does not name: the moments fixture's why_not_forty_yet note records that
batch 3 added ZERO unmatchable moments and that the two byte-identical sibling pairs
(N13/N14, N15/N16) MISS "harder than the cap predicts — the cap explains why both members
cannot sit at rank 1, it does NOT explain why neither reaches the top 5. Both pairs show up
under RANKABLE." An undiscriminable trigger does not merely split one slot; it pushes BOTH
answers below the fold. That is not a reading problem (the prose is matched) and not a filing
problem (the lessons are filed and projected); it is a TRIGGER-EXPRESSIVITY problem — the
address the moment carries is too coarse to route to its own answer. Contract C as written
widens what a query can match; it does nothing for a moment whose trigger cannot discriminate
between two different right answers. I flag this as the design's blind spot because the
bench's ambiguity cap (0.833) treats it as a property of the fixture, when the fixture note
itself reads it as a property of the trigger vocabulary — a fourth contract the reframe does
not yet have.
cite: tests/fixtures/recall_eval/moments.json:7 (why_not_forty_yet: "An undiscriminable
trigger does not merely split one slot between two moments; it appears to push both of them
down ... a measurement of the TRIGGER's insufficiency rather than the engine's quality")
cite: research/in-flight/filing-schema-navi-livebench.json:9-11 (ambiguity_cap 0.8333 carried
beside recall_at_1, not folded into it)

## The one question for Daniel

If a moment's trigger is too coarse to name its own right answer, do you want the address
fixed at the moment (a fifth contract: discriminating triggers), or is that out of scope for
this fence and a problem for the recall arc?
