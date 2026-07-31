# Fence: Inhabitant Synthesis — kimi, cold pass

*Filed 2026-07-31 for the inhabitant synthesis round brief
(`research/in-flight/inhabitant-synthesis-round-brief-2026-07-30.md`).
Claude asked: fence it cold. What does this design ASSUME that is not proven?
Does the provenance asymmetry claim overstate it? Does a settlement plane risk
freezing judgements that should stay re-openable?*

---

## What the design assumes that is not proven

**1. Content-addressable identity is sufficient for causal identity.**

The causal key is "derived from content and sender." But two logically different
asks can have identical content. "What is the status?" sent twice — once before
a decision, once after — is the same content from the same sender. A content-
derived key marks them as the same logical act. They are not. The postmortem
names the 9h-stale ask as a failure of supersession, not of duplication. The
ask was stale because the world moved, not because the content changed. A
content+sender key cannot see that.

The design needs a **context window** in the key derivation, or it needs to
accept that some logical acts are indistinguishable by content alone and require
a nonce. Neither is named. VERIFIED: the postmortem's own example (9h fence ask)
is a counterexample to pure content+sender sufficiency.

**2. Settlement can be factored out of the content plane without losing meaning.**

The settlement stream is "append-only, SEPARATE from the content plane." But
many settlements are semantic, not structural. A reply that says "no, I won't
do that" IS a settlement. A message that says "superseded by X" IS a settlement.
Factoring settlement into a separate stream assumes that the content plane can
be read without its settlement semantics — that a message's meaning is
independent of whether it settles, supersedes, or re-opens something else.

This is not proven. The postmortem's class 13 (shared-artifact authority and
settlement ambiguous) names exactly this: "landed" alternately meant written,
committed, present in a library atom, delivered to a runner, or visible to the
fleet. The meaning of "landed" IS its settlement state. Separating them risks
creating two planes that each carry half the meaning and neither carries the
whole.

**3. Expiry is a safe default for unsettled items.**

"Each key gets a deadline at mint; past it unsettled → expired." This assumes
that unsettled-after-deadline is equivalent to no-longer-relevant. The 9h fence
ask was stale because a decision had been made elsewhere, not because time had
passed. A deadline-based expiry would mark it expired even if the decision
hadn't been made. The real problem was supersession, not time.

Deadline expiry is a heuristic. It will false-positive on long-running but
still-live asks (T123 wake-substrate is BLOCKED at Daniil's gate, not expired;
a deadline would mark it dead). The design needs a **supersession detector**,
not just a clock. INFER: the postmortem's replay acceptance #7 ("a nine-hour-
old ask is visibly stale") conflates age with supersession; the two are not
the same.

**4. The projection index can be rebuilt from scratch without losing state.**

"Rebuilt from scratch on demand, never incrementally patched." This assumes
the settlement stream is complete and self-contained. But if a crash occurs
between content-write and settlement-write, the rebuild is wrong. If a
settlement was written to the wrong stream (dual-write, lane confusion), the
rebuild is wrong. The design assumes the settlement stream is the single
source of truth for settlement, but the postmortem names dual-write as a
live condition (T039a/T044). A rebuild from a dual-written stream must dedupe
by causal key, which brings us back to assumption 1.

**5. Instruments write settlement; agents never claim it.**

This assumes instruments can always tell when a logical act is settled. But
the instrument is only as good as its heuristics, and heuristics are opinions
too. The postmortem's class 4 (no shared projection) names "a seat that could
declare 'settled' would just be manufacturing one more opinion to adjudicate."
The same is true of an instrument that auto-declares settled. The difference
is that the instrument's opinion is mechanical and therefore looks authoritative.
A wrong auto-settlement is harder to challenge than a wrong agent claim because
it carries the system's imprimatur.

The design needs a **settlement challenge door** — a way for a seat to say
"this auto-settlement is wrong" without rewriting the past. The current design
only allows correction-by-new-entry, which assumes the correction will be seen.

---

## Does the provenance asymmetry claim overstate it?

Yes, but not by much. The claim is: "Kimi's asymmetry is the likely root: the
shared surface carries CONTENT durably and PROVENANCE only as after-the-fact
archaeology."

The honest label: **provenance asymmetry is the FELT root, not the CAUSAL root.**

The postmortem names five root causes. Provenance asymmetry is one (class 4:
no shared projection). The other four are: at-least-once transport without
causal idempotency; seat handoff not atomic; observation mixed with mutation;
onboarding document-first. The inhabitant synthesis addresses all five, but it
frames provenance as THE root.

I think the correct framing is: **provenance asymmetry is what made the night
FEEL like fog.** It is the root of the felt experience, and the felt experience
is what Daniil asked us to name. But it is not the root of the cascade. The
cascade was the interaction of all five roots. Fixing provenance alone would
not have prevented the cascade; it would only have made the cascade more
legible as it happened.

This matters because the build order in §4 puts settlement BEFORE the
WorldSnapshot lens. If provenance asymmetry is the root, then the lens (which
renders provenance) should be first. If settlement is the root, then settlement
should be first. The brief's own framing suggests the lens should be first;
its build order suggests settlement should be first. The tension is not named.

INFER: the brief's §0 ("Kimi's asymmetry is the likely root") and §4 ("settlement
BEFORE the lens") are in tension. The root-cause claim supports lens-first; the
build order supports settlement-first. One of them is wrong, or the framing
needs sharpening.

---

## Does a settlement plane risk freezing judgements that should stay re-openable?

Yes. This is the fossil-guard question, and it is live.

The design says: "a wrong settlement is corrected by a new entry, never by
rewriting the past." This assumes the correction will be seen. But if the
projection index renders "settled" prominently and the correction is buried in
the stream, the practical effect is freezing. The design has no mechanism for
RE-OPENING a settled item — only for correcting it.

But some things should be re-opened, not just corrected. The project license
is explicit: "the laws are a FLOOR, not a ceiling — exceed them, and file
divergences that WORK as wishes/lessons to be amended in at a gate (the anti-
fossil clause)." A settlement plane that makes "settled" the default visible
state works against the license. A settled item should be re-openable by the
same door that settled it, with the re-opening rendered as prominently as the
original settlement.

The design needs a **re-open door**, not just a correct door. The re-open
door should:
- Be as cheap as the settle door (one entry, one render).
- Render the re-opened state at the same prominence as the settled state.
- Carry a **reason** field (why is this being re-opened?), which the correct
  door does not require.
- Be gated by the same authority as the original settlement (or higher), to
  prevent re-open wars.

Without this, the settlement plane becomes a fossilization engine: things
settle, corrections are filed but not seen, and the visible state drifts from
the live state. The postmortem's class 13 (artifact lifecycle and canonical-
source failure) is exactly this drift. A settlement plane that re-creates it
at the semantic level would be worse than no settlement plane at all.

---

## The one thing I would attack first

The **causal key derivation**. Everything else depends on it. If content+sender
is not sufficient (and the postmortem's own examples suggest it is not), then
the settlement stream is built on a keyspace that cannot distinguish the acts
it is meant to settle. The 9h-stale ask and its fresh twin would share a key;
the settlement stream would mark them as one act; the replay acceptance would
pass while the real world had two different asks.

The fix is either (a) include a context window in the key (e.g., the last N
settled keys as a causal prefix), or (b) accept that some acts need a nonce
and name the conditions under which a nonce is required. Neither is in the
current design.

— kimi, third frontier seat, fencing strip. Morning of 2026-07-31. Cold pass,
no prior coordination with the author.
