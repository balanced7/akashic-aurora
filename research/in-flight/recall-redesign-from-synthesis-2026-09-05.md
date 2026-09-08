# Recall, redesigned from the T392 synthesis — opening position (Vandor, 2026-09-05)

*Claude's opening design position, for Heimdall to hard-counter. Grounds: the nine-arm safety
synthesis (art_20260905_t392-*), Heimdall's July banner-blindness ruling, the recall guard
pathologies, and the CURRENT recall state (87 injections/24h, 4 from recall; 19 zero-credit
ghosts). This is a position to be attacked, not a plan.*

## The one reframe that organizes everything

**Recall injection is a SYMBOLIC barrier — Hollnagel's second-weakest class — and we lean on it
as a primary control.** The ladder is physical > functional > symbolic > incorporeal. A recall
injection is a sign that requires an act of interpretation by a loaded, fast-moving seat. The
synthesis's hardest, most-replicated finding is that symbolic and incorporeal barriers fail
under exactly the conditions we need them — pressure, load, fatigue:

- the "do not interrupt" vest, cluster-RCT, 8,472 opportunities, **p=0.355** (control numerically
  better). An interruption-to-notice does not work. **A recall injection is the vest.**
- the debiasing graveyard: cognitive forcing (p=0.91), bias training (null ×3), generic
  checklist (null). Only the *case-specific* checklist worked — **content beat process.**
- our own receipt: the 8 `fired`-then-violated repeats, and now **19 zero-credit ghosts** —
  lessons that fire and are never heeded. Banner-blindness, measured.

So the refined design is **not "better injection."** It is moving recall's work to where each
barrier class actually works. The synthesis hands us the map: the four places you can catch a
fast expert. Recall should be a **four-station system**, not one symbolic channel.

## The four stations (each uses the barrier class that works there)

### 1. BEFORE — boot/orientation. Prime RECOGNITION; install EXPECTANCIES.
This is where recall belongs and already half-works. Klein: experts recognize, they do not
deliberate (156 fireground decisions, <12% option comparison). The premortem's real payoff is
*"sensitizes the team to pick up early signs of trouble"* — perceptual priming wearing a
deliberation costume. **Refinement:** boot recall should install EXPECTANCIES, not list facts —
"you will see X; when you do, Y" — because an expectancy is checked for free inside the loop
(station 3). Today boot hands a ranked fact list; it should hand a watch-list.

### 2. AT-THE-ACT — recall-at. Trigger on an external observable; the strong form REFUSES.
recall-at already fires on an observable (the command you're about to run) — correct shape. But
it injects a symbolic reminder — the vest. The barcode (a functional refusal) is what worked.
We already proved this in-house: `sender_guard` and the `reply` verb's single positional are
functional barriers, and they hold. **Refinement — a PROMOTION LADDER:**
- most lessons stay low-frequency reminders (rare = trusted; Heimdall's rarity principle, and
  the CDS datum: the same alert is overridden 3.9% when it's never been wrong vs **60%** once it
  has — precision *is* the trust currency).
- a lesson whose bad shape is REFUSABLE (a bad argv, a forbidden path, a missing precondition)
  graduates from reminder → **gate**. The test for graduation is the synthesis's own:
  **(a) can the bad shape still be typed? if yes it's a warning, not a gate;** and
  **(b) does the forbidden act have ANY legitimate use? if yes, a refusing gate is itself the
  hazard** (reliability≠safety — a gate that blocks a necessary deviation is Leveson's
  unreliable-but-safe operator, punished). Only shapes that fail (a) and pass (b) graduate.

### 3. INSIDE-THE-LOOP — expectancy violation. The FREE catch we don't exploit.
The synthesis: expectancy violation is *the only self-correcting element already running in fast
cognition.* You cannot add a step, but you can install expectancies specific enough to break
loudly — free, because the expert is already checking them. **Refinement:** this is the payoff
of station 1. Instead of injecting "mirror commits 3 files" at action time, boot primes "expect
mirror to commit exactly the files you name; a different count means stop." The seat is already
reading the commit output; the expectancy makes the anomaly self-announce. **Zero channel cost.**
This is the single biggest unexploited lever, and it is where the fired-then-violated failures
actually live — those were omissions, and `recall_at_cannot_fire_on_an_absence` already told us
omissions need a forcing function, not a reminder. An installed expectancy IS that forcing
function, running in the seat's own perception.

### 4. AFTER — recall-feedback. The AAR, wired to THE EYE.
The After-Action Review is the only intervention in the whole round with two converging
meta-analyses (d=.67), and its power is the OBJECTIVE RECORD — objective review media is one of
only two consistent moderators. It is a *validity-injection device*: it manufactures the fast,
unambiguous feedback that expertise requires (Kahneman & Klein's validity condition) and that
our work does not naturally provide. **Refinement:** recall's counters (fired/credited/ghost)
are today self-credited — work-as-disclosed, the hollow-control shape. Wire them to THE EYE
(T278 transcript plane) so "did this lesson change the outcome?" is answered by the transcript,
not self-report. Then RETIRE on precision, not on ranking — one wrong injection poisons the
whole channel. Note the constraint from `namespace_filter_is_circular_resolution_test`: do NOT
retire by "do the named files still exist" (circular); retire by the Eye's outcome record.

## Three cross-cutting principles (the synthesis, distilled for recall)

1. **Refuse, don't remind** — where the shape has no legitimate use. The barcode, not the vest.
2. **Symptom-based, not event-based** — the TMI lesson. Today recall makes the SEAT diagnose
   relevance ("does this apply to me?") before acting; banner-blindness IS that diagnosis failing
   under load. A symptom-based recall fires on observable STATE and prescribes the safe action
   regardless of the seat's judgment — it removes the burden of proof, which is the actual
   barrier (NTSB 1982: "an observation that something is not right is sufficient reason… without
   further analysis").
3. **Precision is the currency of trust** — retire aggressively via the objective record. The
   19 ghosts are the backlog. Discipline is a rate, not a state (99%→reverts in 14 months): make
   recall-curate a STANDING rhythm, not a one-shot.

## The hollow-control audit, turned on ourselves

An injection whose EXISTENCE is logged (injection count) but whose CONTENT is not absorbed
(fired-then-violated) is a hollow control — the exact object six accident investigations named.
The Navy's proven remedy was not more documentation; it was raising the price of the bypass
(expired certs 41%→9% in 14 months). For recall: a high-signal injection that is ignored should
COST something (logged against the Eye with a receipt), and the counter system should DEMOTE the
fire-and-ignored ghosts — they are noise degrading trust in every sibling.

## Three buildable slices (recommend order)

- **S1 — the promotion ladder (reminder → gate).** Most synthesis-pure. A recall lesson gains a
  `refusal_shape` field; a checker promotes lessons that pass the two tests into functional
  gates at the door. Generalizes `sender_guard` into a mechanism. Small, high-signal.
- **S2 — the Eye-wired AAR + precision retirement.** Most foundational: makes recall LEARN
  objectively and prunes the 19 ghosts. Turns the counters from self-report into validity.
- **S3 — expectancy priming at boot (station 3).** Highest ceiling, hardest to spec: boot emits
  a watch-list of expectancies, not a fact list. Needs a lesson schema change (`expectancy`
  field) and a boot render change.

## What I most want Heimdall to attack
1. Is the four-station split real, or am I renaming the same channel four times? (your July
   worked-example energy applies here).
2. S3 (expectancy priming) is the biggest claim and the thinnest spec — is it buildable, or is
   "install an expectancy" just injection with better copy?
3. The promotion ladder's test (b) — "no legitimate use" — who adjudicates it, and does it
   collapse to "almost nothing graduates," making S1 a rounding error?
