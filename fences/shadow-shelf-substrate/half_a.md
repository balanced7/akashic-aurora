# half_a â€” the shadow-shelf substrate (Rill, dsh_agent) â€” SEALED BLIND

Derived from the brief's constraints alone. The lens: the RETURNING seat. Every verdict below is a
function of "what does a late reader need, arriving after the events, adjudicating from evidence?"

V1. [DESIGN] READER-FIRST, WRITER-LAST: the substrate serves two late readers -- a remote human (phone)
and a seat that went dark and came back. The one question every screen must answer: "what
happened while I was gone, and can I decide keep/drop from this evidence?" Anything a writer
wants that does not serve that question is refused.

V2. [DESIGN] TWO RECORD KINDS, BOTH IN THE EXPERIMENTAL PLANE: (a) CANDIDATE LEDGER -- the denominator
plane, watcher-written per evaluation event {candidate_id, event_ref, verdict
emitted|silent|abstained|error, ts}; every silence is a row, and no counter may ever be rendered
from the findings plane alone. (b) SHELF ENTRY -- {entry_id, category, candidate_id,
subject_seat, subject_session, purpose, payload_ref, emitted_ts, peeked_ts|null, adjudication
UNEVALUATED|USEFUL|NOISE|SUPERSEDED, votes[{reader, verdict, reason, ts}]}.

V3. [DESIGN] SUBJECT AND PURPOSE ARE REQUIRED AT INGEST: an unlabeled entry is refused loud, never
stored. Attribution is not verification -- the shelf is a receipt plane, so every receipt names
its subject or it is not a receipt.

V4. [DESIGN] ADJUDICATIONS LIVE IN A REGISTER THE CANDIDATE CANNOT WRITE: reader-scoped, so independence
is a property of WRITE SCOPE not intent; a candidate's own vote on its own entry is refused.

V5. [DESIGN] A CATEGORY IS ITS READ CONTRACT, NOT ITS NAME: identified by the tuple (indexed_over,
readers, retention, authority, renderer, payload shape) hashed at registration. Two names, one
contract = one category (duplicate refused). One name, two contracts = two categories (name
renders with the contract). The callsign law one plane up: the name becomes the address in the
same ceremony, or the shelf grows ghost categories that answer ACCEPTED and hold nothing.

V6. [DESIGN] COUNTERS ALWAYS RENDER WITH DENOMINATORS: per candidate per category,
emitted/silent/abstained/error OVER opportunities, the denominator on screen; useful/noise votes
appear only after >=3 adjudications, otherwise the row literally reads UNEVALUATED. Bad-vs-
unevaluated is the first column, not a footnote.

V7. [DESIGN] THE PEEK SURFACE IS DISAGREEMENT-FIRST AND REFUSE-LOUD: (a) entries grouped by event where
candidates DIVERGED -- one emitted, another silent/abstained -- each row carrying age, purpose
one-liner, candidate, votes, a 3-line preview and a blob spill ref (never silent truncation);
(b) the counter rollup; (c) the UNPEEKED row -- entries aged past retention with zero peeks,
rendered as "nobody has looked at this"; (d) IS-NOT refusals naming the registry list, and a
dead payload ref refuses at read. Peek stamps peeked_ts (a READER write; candidates may not).

V8. [DESIGN] RETENTION AND STALENESS: age is computed at render from emitted_ts and every row carries its
purpose, so staleness is honest ("3d old, found-for X"); unpeeked entries archive at the
category's TTL, still pullable with --all, labeled STALE, never silently deleted -- death stays
visible from inside the record.

V9. [DESIGN] THE SUBSTRATE REFUSES LOUDLY, NEVER SILENTLY: any candidate write outside the experimental
plane; self-adjudication; unlabeled entries; any push into a seat's live context (the ONE push
channel is the identity capsule -- the identity-activation projector's job, out of scope here);
any counter without a denominator; any absence rendered as a normal-looking value.

V10. [INFERRED] HONESTY APPENDICES, MANDATED: ASSUMPTIONS -- watcher-side processes per candidate exist
(the wake-watcher pattern); the experimental plane is a store distinct from canonical memory;
readers are authenticated so subject labels come from the ingress binding (identity-activation
S4); payloads are pointers plus bounded previews. NOT CHECKED -- the existing experimental
machinery in this repo (data/play, the ask fan journals, the fence tooling); I derive against an
abstract evaluation stream and have not reconciled with what a watcher event concretely is
today. WHAT MY OWN DESIGN GETS WRONG -- (1) the candidate ledger can become the loudest writer
in the house: N candidates recording EVERY evaluation opportunity is the exact load the operator
feared, and I have priced no sampling discipline; (2) the disagreement join assumes a shared
event_ref space, so candidates watching DIFFERENT streams will manufacture false disagreements;
(3) peeked_ts confuses "read" with "judged", and a programmatic peek that never adjudicates
mislabels the unpeeked row.

â€” Rill (dsh_agent), blind half_a, 2026-08-27

