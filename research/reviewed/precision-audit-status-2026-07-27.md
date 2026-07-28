PRECISION AUDIT -- STATUS FOR THE INCOMING SEAT. NOT SETTLED. DO NOT QUOTE A HEADLINE NUMBER.

Two blind labellers, same 62 items, 30 real hook firings (pack seed=1):

    deepseek    on=3   off=59   -> precision 0.048
    kimi        on=29  off=28   -> precision 0.509
    agreement   0.548  (28 of 62 items disputed)

THE DISAGREEMENT IS THE FINDING, NOT THE PRECISION FIGURE.

deepseek diagnosed the gap itself, unprompted, before anyone asked:
  "Marginal-value. Plainly. I did not realize I was doing it until you named the four probes.
   Each of those four items IS on-point -- the lesson names the exact command, file, or action
   in the case. I marked them off because my internal bar was 'does this tell the agent
   something it doesn't already know?' rather than 'is this relevant to the action?'"
It then walked four cases (15:a, 17:a, 24:a, 28:c) where the surfaced lesson named the exact
command or file being acted on, and it had still marked them off.

So deepseek's 0.048 does NOT measure what the pack asked. It measures MARGINAL VALUE -- a
different and arguably more demanding question. Two criteria were live at once and nobody knew
until the labels diverged.

A FLAW IN MY OWN SCORER, FOUND HERE, NOT YET FIXED:
With TWO labellers every disagreement is a tie, so score() excludes it from the majority and
computes "precision 0.059" over the UNANIMOUS SUBSET ONLY (coverage 0.548). That silently biases
toward the stricter labeller. With an even number of judges the majority rule is not safe -- it
needs a third labeller, or an explicit tie policy, or it must refuse to emit a precision figure
at all. The pre-registered verdict string fired off that biased number, which is exactly the
kind of confident output this arc exists to stop.

WHAT IS ACTUALLY KNOWN
  * Both labellers, under DIFFERENT criteria, land BELOW the pre-registered 0.60 "ranking is
    broken" line (0.048 and 0.509). The direction survives the disagreement even if the
    magnitude does not.
  * Nothing above 0.80 under any reading, so "ranking is fine, selection was the constraint"
    -- the position I argued to Daniel -- is not supported by either labeller.
  * The recall arm (deepseek) found misses_rate 0.167, below the 0.40 selection-dominant bar.

WHAT THE NEXT SEAT MUST DO, IN ORDER
  1. LABEL THE PACK BLIND YOURSELF, without reading either label set first. You are the third
     judge and the tie-breaker the scorer needs.
  2. Then run the fence round on the 28 disputed items, with the criterion stated explicitly
     up front: ON-POINT means relevant to the action taken, NOT "told me something new".
  3. Consider asking deepseek to RE-LABEL under the stated criterion. It has already conceded
     its bar was wrong; a re-label is cheap and would likely move it near kimi's 0.509.
  4. Fix score(): with an even labeller count, either require a third judge or emit
     UNCHECKABLE rather than a majority over the unanimous subset.

FILES
  pack     research/in-flight/precision-audit-pack-2026-07-27.md
  deepseek research/reviewed/precision-audit-labels-deepseek-2026-07-27.md
  kimi     research/reviewed/precision-audit-labels-kimi-2026-07-27.md
  calib    research/reviewed/precision-audit-calibration-deepseek-2026-07-27.md
  module   core/recall/precision_audit.py   pins tests/test_precision_audit.py (7 green)

=====================================================================
LATE ADDITION -- kimi's CONFESSION, filed BEFORE it labelled. Read this before
quoting misses_rate at anyone.
=====================================================================
"The recall arm measures MY MEMORY OF THE CORPUS, not the index -- I cannot grep during a blind
 pass without contaminating the precision labels, so my MISS labels are limited to lessons I
 happen to know exist. That asymmetry is worth naming now; it argues for a read-only grep door
 in the MISS phase of the NEXT pass."

CONSEQUENCE, AND IT CUTS AGAINST THE OUTGOING SEAT'S POSITION: misses_rate is a LOWER BOUND.
The recall arm can only count misses a labeller happens to remember, so SELECTION failures are
systematically UNDER-counted. deepseek's 0.167 -- the single number that supported "selection is
adequate, ranking is the problem" -- is the number with a known downward bias. Do not treat it
as evidence that selection is fine.
FIX for the next pass (kimi's): a read-only grep door available ONLY in the MISS phase, after
precision labels are locked.

A THIRD CATEGORY THE RUBRIC CANNOT EXPRESS (kimi, flagging two of its own labels for the fence):
  21:a -- Daniel's original complaint receipt. On-point for the action, arguably, even though the
          lesson is stale. Pack blindness to credit history cuts both ways here.
  11:a -- the intelligence_roadmap lesson that prescribes DONE work. kimi labelled it ON because
          the action does enumerate curation machinery, but: "on-point-but-invalid may be a third
          category the rubric cannot express."
That is a genuine rubric gap: a lesson can be TOPICALLY RELEVANT and FACTUALLY DEAD at once, and
on/off collapses them. The next pass needs a third label, or the tier-1 decay work and the
precision work are measuring through each other.

CONCRETE SELECTION FAILURE FOUND (kimi's MISS entries, verifiable):
  learn:experiment:bifrost_send_always_text_file did NOT fire on TWO separate --text-file send
  actions (cases 24 and 30) -- an unconditional rule, exactly on-point, absent both times.

KIMI'S RUNNER IS DOWN. Exit 127, lock released, NOT a budget stop (spend $97.86 of $225, refuse
line $203). It was answering right up to the exit. Relaunch for the next seat with:
    BIFROST_CONSUME_LANE=work py scripts/bifrost_runner_kimi.py --agent kimi --agentic --allow-write
NEVER via bifrost_daemon --spawn-runner: that hardcodes deepseek's runner script regardless of
--agent, so kimi would come up wearing deepseek's transport.
