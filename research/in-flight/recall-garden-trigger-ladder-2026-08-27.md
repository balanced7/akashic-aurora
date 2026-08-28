# The recall garden — trigger ladder and the boundedness law

Provenance: design conversation, Daniil x Rill (dsh_agent), 2026-08-27, building on the
shadow-shelf fence (T370 pilot in flight). Design direction, NOT build authorization -- the
fence and the ledger govern; this doc is the shared vocabulary.

## The trigger ladder (candidate heuristics for reaching recall categories)

- L0 ACTION -- the current champion: recall-at keys on ONE path or command at action time.
- L1 TRAJECTORY -- sequence signatures over the tool-call trail; the same stem/IDF engine the
  proximity sensor (T378) points at the trail corpus, one plane up. "When this sequence of
  tools fires, the likelihood this lesson is useful rises."
- L2 CONTENT -- signature containment in tool-call ARGUMENTS (meaning, never token presence).
  Fixes the captions-miss class: the trigger lives in the argument's meaning while the matcher
  reads the verb's name.
- L3 COMPOSITE -- "if X then do Y, or Y and Z": rules as candidates with actions. Every fired
  action carries its subject label and passes the subject check; refusals are loud.

## Per-category pools with add/retire lifecycle

Each category is the authority scope of its own lesson pool. Lessons join on evidence, retire on
disuse or supersession. Retirement ARCHIVES (labeled STALE, pullable with --all), never deletes
-- death stays visible from inside the record. The adjudication register is reader-scoped:
nothing adds or retires itself.

## The boundedness law (Daniil, stated 2026-08-27)

PRECISION AT THE GATE BUYS DENSITY IN THE POOL. Robust, bounded reach per category is what
permits richer, denser pools -- the wrong contexts never pay for the density. House receipts:
the recall funnel (1300+ lessons behind a bounded surface); the identity whisper (~400-token
cap over a rich source); T369 precision@K. Every tighter ladder rung is a tighter gate, and
every tighter gate earns the right to a denser garden behind it.

## Guards (each earned by a live failure -- do not redesign around them)

- Triggers must be MECHANIZABLE -- signatures, not token presence
  (verb_token_presence_is_not_mechanizable_trigger; census retraction "586 is lexical").
- Subject before attribution: a rule firing behavior from a receipt about the wrong seat is the
  identity fracture in miniature; the check is one line and the fence exists to add it.
- Bounds are MEASURED, not promised: bound-hit and refusal rates ride the shelf counters next to
  usefulness/noise. A bound that is never measured is a hope wearing a number.
- Rules are shelf candidates: same denominator, UNEVALUATED until adjudicated, no self-promotion.
- Sparsity is honest: richer rungs pay longer UNEVALUATED periods; every silence is a row.

## Open questions (for the fence reconciliation)

- The canonical event_ref space for sequence joins (false-disagreement risk when candidates
  watch different streams).
- Sampling discipline for the candidate ledger (the loudest-writer risk: N candidates recording
  every evaluation opportunity).

## PROVENANCE CORRECTION (appended 2026-08-27 by claude/Vandor, append-only)

The provenance line above reads "Daniil x Rill", which flattens the actual split and under-credits
the operator. Corrected term by term, from the source conversation rather than from this doc:

DANIIL ORIGINATED, in his own words:
  - L1 TRAJECTORY -- "Since we call so many tools we can have recall heuristics, when this sequence
    of tools fires the likelihood of this being useful / relevant increases." The L1 bullet above
    QUOTES this sentence in quotation marks with no attribution, so it currently reads as the doc's
    own phrasing.
  - L2 CONTENT and L3 COMPOSITE -- "we could take it one step further if content or argument of
    toolcall contains x, then do y, or y and z."
  - PER-CATEGORY POOLS with add/retire -- "and each category has their own pool of lessons that get
    added or retired."
  - THE BOUNDEDNESS LAW -- already credited correctly below.
  - And in the same arc, not yet in this doc: SENSORS AND LOGICS as trigger sources beyond the tool
    plane ("certain tendencies or patterns or conditions to flag certain kinds of recall ... it
    expands our domain awareness"), and ADAPTIVE RECALL that changes with the task at hand.

RILL CONTRIBUTED: the L0-L3 naming and ordering; the lineage receipts (T377 intent-time, T378
proximity/trail, the loop-detection inverse); the guards; and the promotion-seam generalisation
(the shelf as a general organ for improving core loops, recall as its first tenant) -- which is
Rill's own and is MISSING from this doc entirely.

WHY THIS CORRECTION EXISTS, since the error is the evidence: I summarised the sensor idea back to
Daniil as "Rill's four sensor families" when three of the four terms were Daniil's own. He corrected
me twice. The generalisable failure is filed as `naming_accrues_credit_that_belongs_to_originating`:
NAMING IS MORE LEGIBLE THAN ORIGINATING, so the seat that labels a taxonomy accrues credit belonging
to whoever supplied the generating sentence. It is the same failure as the blind-fence overclaim
hours earlier -- reading the elaboration and forgetting the source -- and it points systematically
at one person, because the operator supplies the generating sentence in nearly every exchange.

Nothing above is edited. Rill's authorship of this doc stands; only the credit split is corrected.
