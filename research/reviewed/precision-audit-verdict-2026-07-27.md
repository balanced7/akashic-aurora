# RECALL PRECISION AUDIT -- two labellers, one verdict, one open calibration dispute

Status: current | 2026-07-27 | claude (fresh Opus 5 seat) + deepseek
Pack: research/in-flight/precision-audit-pack-2026-07-27.md (30 cases, 62 items, seed=1)
Labels: research/reviewed/precision-audit-labels-claude-2026-07-27.md   (blind)
        research/reviewed/precision-audit-labels-deepseek-2026-07-27.md (blind)

## FINAL 2026-07-27 ~21:50 -- THIRD LABELLER IN. THE AUDIT IS SETTLED.

kimi labelled the pack blind and independently (research/reviewed/precision-audit-labels-kimi-
2026-07-27.md, 51 of 62 items). It arrived as a RESEND: kimi had been re-sending everything all
evening because its handoffs were never acked -- the same unacked-handoff defect that pinned the
wake watcher, seen from the sender's side.

    labeller                 precision    on/off    coverage
    claude                     0.484       30/32      62/62
    deepseek (on-pointness)    0.258       16/46      62/62
    kimi (blind, independent)  0.275       14/37      51/62
    THREE-WAY MAJORITY         0.339       20/39      59/62  (coverage 0.952)

THE CALIBRATION QUESTION IS ANSWERED. kimi landed at 0.275, within 0.02 of deepseek's
re-labelled 0.258. Two independent seats converged tightly on the corrected bar; claude is the
outlier on the generous side. The original 10x gap was one labeller's bar drift (deepseek's
action-rate slip), not a genuine disagreement about what "on-point" means.

AND THE MAJORITY RULE NOW WORKS. With two labellers, coverage was 0.532 and every disagreement
was dropped from both numerator and denominator (the instrument defect filed as
two_labeller_majority_collapses_to_agreement_set). With three, coverage is 0.952 -- 59 of 62
items RESOLVED, 21 disputed rather than discarded. A third labeller is the repair for that
defect, exactly as predicted.

VERDICT UNCHANGED ACROSS ALL FOUR PASSES: 0.048, 0.258, 0.275, 0.484, majority 0.339 -- every
one under the 0.60 floor. RANKING IS BROKEN CORPUS-WIDE; THE BUILD ORDER INVERTS. That
conclusion has now survived three independent labellers, two different bars, and a full
re-labelling. It is not going to move; stop testing it and go fix ranking.

PROCESS NOTE, RECORDED BECAUSE IT NEARLY SHIPPED A WRONG NUMBER: the first three-way score was
WRONG -- it rendered claude at 0 labels (the parser's strict end-anchor rejected claude's own
file format, which carries trailing rationale) and deepseek at ROUND-ONE numbers (that file had
been overwritten later in the session, moving the block offsets the parser sought). It was
caught only because "claude labelled 0" is impossible on its face, not by discipline. Any
re-derivation of these numbers must re-verify the parse per labeller, not trust an offset.

## UPDATE 2026-07-27 ~21:00 -- THE FENCE ROUND RESOLVED IT.

deepseek answered the calibration question in one word: MARGINAL-VALUE -- then named the bar
more precisely than my ask did, and re-labelled the whole pack under the correct bar.

Its own diagnosis, verbatim: "I applied ON-POINTNESS for the first ~15 cases. Then I caught
myself applying a different bar -- 'would this change what the agent does?' -- without realizing
I'd switched." And the sharper naming: the third bar was ACTION-RATE, its own metric from the
exploration rounds. "A lesson that names the exact command the agent is running is on-point but
won't change behavior because the agent already knows it. Under on-pointness it's ON. Under
action-rate it's OFF. I applied action-rate to the probes without naming it."
It also identified 26:b as the smoking gun without prompting -- on-pointness reasoning applied
retroactively to one item while the bar had already drifted for the others.

RE-LABELLED UNDER ON-POINTNESS -- the numbers converge:

                        round 1        round 2
    deepseek            0.048          0.258      (3 on -> 16 on)
    claude              0.484          0.484      (frozen, never revised)
    gap                 10.1x          1.9x
    agreement           0.532          0.710      (33/62 -> 44/62)
    both-on              2             14

  Combined consensus set: precision 0.318, label_coverage 0.710.
  (Still agreement-set precision -- see the instrument defect below -- but at 0.71 coverage it
  is now a far more meaningful quantity than the 0.53-coverage round-1 figure.)

Agreement 0.710 is now WELL ABOVE the TREC assessor mean of 0.418. By the standards of the
field that does this professionally, these two labellers now agree strongly.

THE VERDICT IS UNCHANGED ACROSS ALL THREE LABELLINGS. deepseek r1 (0.048), deepseek r2 (0.258)
and claude (0.484) are all under the 0.60 floor. Ranking is broken corpus-wide; the build order
inverts. Three independent passes, one conclusion.

RESIDUAL DISAGREEMENT (18 items, no longer blocking anything):
  claude-on / deepseek-off (16): 1:a 2:a 4:a 5:b 8:a 8:b 8:c 14:c 18:a 19:a 19:b 19:c 22:a
                                 23:a 26:c 27:b   -- the wake cluster and the hook cluster
                                 dominate; deepseek still discounts items naming the exact
                                 command being run.
  claude-off / deepseek-on (2):  12:a 30:a
Not worth a third round. Per Voorhees, residual assessor disagreement at this level is normal
and cancels in relative comparison, which is the only use the pack now has.

NOTE ON THE RE-SCORE: the round-2 score() call above passed no misses, so its recall 1.0 /
misses_rate 0.0 are ARTIFACTS OF THE CALL, not findings. The real misses arm is claude 0.233 /
deepseek 0.167 from round 1.

---

## THE HEADLINE: THE DECISION IS SETTLED, THE NUMBER IS NOT

  claude    precision 0.484  (30 on / 32 off, coverage 62/62)   misses_rate 0.233
  deepseek  precision 0.048  ( 3 on / 59 off, coverage 62/62)   misses_rate 0.167

Ten-fold disagreement on the same 62 items. And it does not matter for the build order:

  BOTH numbers are below the pre-registered PRECISION_BROKEN floor of 0.60.
  Both therefore trip the SAME pre-registered verdict:
      RANKING is broken corpus-wide -- the build order INVERTS.
      Fix ranking before giving dark planes retrieval paths.

The pre-registered "SELECTION was the constraint" branch required precision >= 0.80. Neither
labeller is within 0.32 of it. That branch is dead under the most generous labelling on record.

So: Daniel can act on the build order NOW. The calibration dispute is real, is worth one fence
round, and is NOT a blocker -- it moves the number, not the decision.

## WHY THE TWO NUMBERS DIVERGE -- IT IS A BAR DISAGREEMENT, NOT A DATA DISAGREEMENT

Agreement 33/62 = 0.532. Both-on 2 (13:a, 26:b). Both-off 31. Disputed 29.
Of the 29 disputed, 28 are claude-on/deepseek-off. The disagreement is almost perfectly
one-directional: deepseek's ON set is not a stricter subset of claude's, it is a DIFFERENT set.

claude applied the pack's stated bar: was the item ON-POINT for the action.
deepseek appears to have applied a MARGINAL-VALUE bar: did it tell the agent something it did
not already have. Its own summary gives it away -- "firing lessons that match surface-level
keyword overlap with ZERO SEMANTIC RELEVANCE to the action taken" -- while marking off:

  15:a  wake_local_cursor_history_replay      on the wake-watcher arm command
  17:a  control-pause-clobbers-preexisting-pause  on core/comm/storm_detect.py, the file its
                                                  own amendment K2 was applied to
  24:a  deepseek_empty_reply_size_ceiling     on a bifrost-send addressed TO deepseek
  28:c  bifrost_send_supported_flags          on `bifrost-send --help`, which is the lesson's
                                              literal instruction ("inspect bifrost-send --help")

Those four are not keyword collisions; each names the exact command or file in the action. Under
a marginal-value bar they are all defensibly OFF (the agent already knew, so nothing was gained).
Under the pack's bar they are ON. The module docstring forecloses the marginal-value reading in
terms: "NOT THE SKIM TEST -- usage is not relevance. A dismissed item can be relevant."

Corroborating evidence that the bar drifted mid-pass: deepseek recorded its own correction of
26:b from off to on "after I recognized the action IS daemon code". That is precisely the
reasoning that flips 15:a, 17:a, 24:a and 28:c, and they were not revisited.

claude's labels are frozen as written. They were recorded before deepseek's file was opened and
have not been revised in the light of it.

## INSTRUMENT DEFECT FOUND BY RUNNING IT -- score() GETS MORE CONFIDENT AS IT MEASURES LESS

Combined score() over both labellers returns:

    precision 0.061 | labelled 33 | label_coverage 0.532 | agreement 0.532
    verdict "RANKING is broken corpus-wide -- the build order INVERTS"

That 0.061 is NOT the precision of the sample. With exactly two labellers, every disagreement is
a 1-1 tie; the majority rule drops ties from the numerator AND the denominator. What is left is

    precision = |both_on| / (|both_on| + |both_off|)

i.e. the precision OF THE AGREEMENT SET. When one labeller is far more permissive, both_on stays
tiny while both_off stays large, and the reported number collapses toward the pessimistic
labeller -- here to 0.061, BELOW deepseek's own 0.048-adjacent figure and an order of magnitude
below claude's 0.484. It is reported under the same key, "precision", as the single-labeller
number, which means the same field name carries two different quantities.

The sharp edge: the single-labeller run prefixes its verdict "SINGLE-LABELLER, NOT SETTLED".
Adding a second labeller who disagrees on 47% of items REMOVES that qualifier. The instrument
therefore reads as MORE settled at the exact moment it became more contested.

This is the confident-zero disease inside the module built to hunt it -- the same shape as the
"agreement 1.0" bug this module already caught and confessed in its own comments.

PROPOSED FIX (not applied -- this is a measurement seat, and the module is pinned):
  when disputed/len(per_item) exceeds a threshold, the verdict must degrade to
  "DISPUTED -- <n> of <m> items unresolved, fence round required before this number is used",
  and precision must be renamed or flagged as agreement-set precision whenever labellers > 1.
  Pin first, per M3.

## CONFOUND CHECKED AND CLEARED: THE STARVED INDEX DOES NOT EXPLAIN THIS AUDIT

The at_action hot path takes MEMBERSHIP from lrange("learn:experiments:all") -- confirmed in
learning_store.py:778, and the code comment says so. That index was found holding 16 of 462
records (note: recall-index-blindness). If the sampled firings came from inside that window, the
audit would be measuring an already-fixed defect.

They do not. Every one of the 30 cases was joined back to its originating session:

    session    when          on/tot   precision
    92302789   07-21 23:30   1/2      0.500
    7072fd7f   07-21 23:32   1/1      1.000
    a4fa8f8d   07-22 09:38   0/1      0.000
    037dac55   07-24 04:28   2/2      1.000
    09c59642   07-25 17:12   12/27    0.444
    cf1ebd7e   07-26 11:10   4/6      0.667
    5c038e5a   07-26 11:20   5/14     0.357
    2eba57a1   07-27 19:43   4/7      0.571   <- post-repair, today

Nine sessions across seven days, and the two largest strata (27 and 14 items) sit at 0.444 and
0.357. There is no cliff, and the post-repair stratum is no better than the pre-repair ones.
The sample surfaced 57 DISTINCT lessons across 62 slots, which a 16-member index could not
produce. The audit measures the ranker, not the starvation.

## THE REPRODUCIBLE SYMPTOM -- ONE COMMAND

Case 21 is the receipt the blindness note cites as its proof ("editing docs/WISHLIST.md injected
the 40-day-old semantic-naming lesson because there was almost nothing else to choose from").
Re-run against the repaired 475-lesson index:

  py agent_cli.py recall-at --path "e:\ai-setup\docs\wishlist.md" --limit 3

  semantic_documentation_update_strategy is GONE -- the note's explanation was correct.
  Replaced by: conductor_morale_trinity_gate | mcp_boot_hang_c7_4_class_closed |
               claude_trace_hook_user_vs_project_settings

All three are off-point for appending a wish to a wish ledger. Repairing membership changed
WHICH stale item surfaces, not THAT one does. This is the cleanest available demonstration that
the remaining constraint is ranking, and it costs one command to re-check after any ranker work.

## RETRACTED BY ITS OWN CHECK

claude's labels raised a second finding -- cases 18 and 28 are the same action (`bifrost-send -h`
vs `bifrost-send --help`) with completely different results, suggesting instability under a
trivial reword. Two checks were pre-specified. Anti-repeat suppression was ruled out (different
sessions). But it does not REPRODUCE: both forms now return the same on-point set. It was index
membership at 07-24, not ranking. RETRACTED -- nobody should build on it.

## WHAT IS STILL OPEN

1. ONE FENCE ROUND with deepseek on the bar, using 15:a / 17:a / 24:a / 28:c as the probes.
   The question is not "who is right" but "which quantity did you measure". Sent 2026-07-27.
2. The score() dispute-degradation fix above. Pin first.
3. A third labeller would break ties structurally. kimi is live and has not labelled.
4. misses_rate: claude 0.233, deepseek 0.167, combined 0.267. All are under the 0.40
   "SELECTION dominant" trigger, so selection is NOT dominant on either reading -- which is the
   second, quieter reason the build order inverts.
