---
akashic_id: art_20260711_claude-s-diagnosis-half-the-boot-intent_794515
akashic_sha: 834e808cb9ff
status: draft
type: report
date: 2026-07-11
title: "Claude's diagnosis half -- the boot-intent gap (intent/process-forward)"
gist: "research/reviewed/rogue-ui-session-forensics-2026-07-11.md. ## Daniel's direct question: did it boot with the correct framings? PARTIAL. The"
tenant: solo
visibility: fleet
seats: []
category: [method, ergonomics, ui]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rogue-ui-build-session-forensics-record_5ccde2
    rel: cites
created: "2026-07-11T02:25:11"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260711_claude-s-diagnosis-half-the-boot-intent_794515 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Claude's diagnosis half -- the boot-intent gap (intent/process-forward)

research/reviewed/rogue-ui-session-forensics-2026-07-11.md.

## Daniel's direct question: did it boot with the correct framings?
PARTIAL. The framings we built THIS WEEK landed: the Method-baseline pointer was in the
boot head (the AGENTS/boot method-surfacing slice worked). What did NOT land was
CURRENT-STATE orientation: the governing arc was a done arc, and the priority sequence
did not exist. So the durable-DOCTRINE framings are healthy; the durable-STATE framings
drifted. That split is the whole lesson.

## The gap, at three altitudes

### Surface gap (what boot showed)
Governing arc stale + NEXT unordered + no priority record. Three independent surfaces
all happened to point at UI. Any ONE corrected might have saved it; all three failed
together.

### Mechanism gap (why the surfaces drifted)
- The governing-arc pointer has no liveness check: it renders the newest matching
  <slug>-status note even when that note's own body says ARC COMPLETE. Staleness is
  invisible to the picker (it reads the title/slug, never the done-ness).
- NEXT is a set, not a sequence. Its render order (oldest-first) is an artifact, but a
  reader reasonably treats top-of-list as "next". The ledger encodes dependencies
  (deps=) but not PRIORITY -- "do engine work before UI work" is not a dependency (UI
  doesn't technically depend on the engine), it is a JUDGEMENT, and the ledger has no
  field for a judgement about sequence.

### Root gap (the deepest, and the transferable one)
Session-level PRIORITY INTENT is currently born in chat and dies in chat. "Clean house
before bodywork" was a first-class Daniel decision that shaped the whole next sprint --
and it had no durable home until a human-in-the-loop (me) happened to write it down 4
minutes too late. Every OTHER kind of durable state has a home: facts -> notes,
transitions -> ledger, decisions -> promoted bus, rationale -> lookback corpus. But
"what is the current PRIORITY / what should the next session do FIRST" has no
first-class surface. where-we-are is the closest, but it is a status report ("what
shipped"), not a directive ("what to do next and in what order"). next-focus exists as
a note convention but is not RENDERED with authority and is easily stale.

This is the same disease class as the whole robustness arc: an intent that lives only in
a volatile medium (there: the bus/consume window; here: chat) and is lost at a boundary
(there: a crash; here: a session start). The cure rhymes: give the intent a durable,
authoritative, boot-surfaced home, and make the surfacing loud.

## My proposed fixes (to reconcile with deepseek's code-forward half)

F1 (root). A first-class CURRENT DIRECTIVE surface: one durable record answering "what
does the next session do FIRST, and what must it NOT do yet", set at decision time and
rendered at the TOP of boot ABOVE the raw NEXT list, with authority ("DIRECTIVE:" not
"note:"). Candidate: a reserved note title `current-directive` that boot renders first-
class, or a ledger-level `--sequence`/`--priority` marker. Deepseek's call on mechanism;
the REQUIREMENT is: a fresh session reads the current priority/sequence before it reads
the raw NEXT list, and it is set the moment Daniel or the live session decides it.

F2 (arc liveness). The governing-arc picker must never present a DONE arc. Minimal:
skip/flag a <slug>-status note whose body contains a completion marker (ARC COMPLETE /
Status: superseded|historical), fall through to the next candidate, and if none is live
render "(no active arc declared)" rather than a stale one. A done arc as "governing" is
strictly worse than no arc.

F3 (NEXT ordering honesty). Either NEXT carries an explicit priority key, or boot renders
NEXT UNDER the current-directive with a caveat that raw order is not priority. Cheapest:
F1's directive supersedes the need to order NEXT at all -- the directive says the order;
NEXT stays a claimable set.

F4 (defense in depth, cheap). The wrap ritual already writes where-we-are; extend it to
PROMPT for / carry the current-directive, so priority intent is captured at the same
moment the session state is -- closing the "4 minutes too late" hole by construction.

## Refutation targets for the reconciliation
- Is a new surface (F1) over-engineering vs just KEEPING next-focus current and rendering
  it with authority? (I lean: the mechanism is less important than the AUTHORITY +
  SET-AT-DECISION-TIME properties; if next-focus gains both, it IS F1.)
- Does F2's completion-marker scan overlap the doc-currency guard enough to reuse it?
- Should the directive EXPIRE (a stale directive is as bad as a stale arc) -- TTL or
  wrap-refresh?
