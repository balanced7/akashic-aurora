# Voice — the rules for anything public this project says

> How we write READMEs, discussions, journey entries, and anything else an outside
> reader sees. Distilled 2026-07-03 from a correction ("I don't want any claim making
> them doubt the rest of the project") and two multi-model review loops that followed.
> The audience assumption is fixed: **a highly skeptical researcher who has seen a
> hundred overclaiming AI projects this month.** Write for them.

## The claim rules

1. **Claims about ourselves: keep, with evidence attached.** Test counts, live
   captures, internal metrics — state them plainly and label their scope ("internal
   numbers, small corpus — but they exist").
2. **Claims about the field: never.** No "nobody does X", "first", "only", "novel".
   Replace with the falsifiable-invitation form: *"our survey (linked, N cited
   findings) didn't find this — corrections welcome."* One refuted boast poisons every
   honest sentence around it.
3. **Beliefs are not history.** Mark them: *Working principle: X appears to hold; here
   is what would revise it.* Leave the door open for evidence.
4. **Never fabricate a number.** A reviewer once suggested inventing plausible metrics
   to strengthen a point. The metric that doesn't exist is reported as not existing —
   that sentence is itself evidence of discipline.
5. **Strong words earn their strength.** "Immune", "proven", "guaranteed" get replaced
   by the precise claim ("avoids this particular source of drift by construction —
   projections can still drift in their own ways").

## The narrative shape

Tell it as: **which facets we chose → where the direction led → why we pivoted → what
it yielded (internal benchmarks, rough numbers welcome) → the most impactful learnings
and why.** Pivots and failures go in, prominently — they are where the reading value
lives, and they are what makes the successes believable. Abandoned decisions get
preserved in [FOSSILS.md](FOSSILS.md) with their reusable lesson.

## The tone rules

- **Understate.** "This project explores a harder question" beats "answers". Let the
  reader upgrade the claim themselves; never do it for them.
- **Underpromise in writing.** State the kill criterion before the build: "if it
  doesn't beat our baseline, it ships nothing."
- **Daniel's voice for Daniel's sections.** Plain, self-deprecating, true ("one thing
  led to another"). Do not corporate-polish it — a reviewer suggested exactly that and
  was overruled on standing calibration. Fix grammar quietly; keep the warmth.
  *Settled (2026-07-03):* two independent model reviewers flagged the "somehow I've
  ended up trying to build…" origin sentence as trust-reducing; the owner kept it,
  with a rationale that is itself a voice rule: **"it's the honest truth. If someone
  doesn't want to read the rest, it means my value add was not significant or clear
  enough."** The work carries the credibility; the origin story stays true.
- **Value to the reader over positioning.** Every section should leave a skeptical
  visitor with something usable: a number they can check, a file they can open, a
  gotcha that saves them an evening.

## The review loop (how this file's rules get enforced)

Public text goes through outside-model review before it ships: ask for the N most
valuable improvements plus a blunt "what still reads arrogant, unfalsifiable, or
hollow?" Then **adjudicate — never auto-fold**:

- Adopt what survives checking (reviewers misquote, and their knowledge cutoffs make
  them "correct" true things into false ones — both happened on day one).
- Reject with a stated reason anything that conflicts with these rules or fabricates.
- Fold the adopted points, run one confirming loop, ship, and note the revision in the
  artifact ("revised after review passes by two outside models; their misfires taught
  us to verify reviews too").

The machine-readable versions of these rules live in the knowledge store
(`public_claims_falsifiable_humility`, `naming_industry_standard_tools` — correction
category) so they surface to any agent writing public text.
