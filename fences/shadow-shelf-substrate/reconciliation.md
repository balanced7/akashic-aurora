# Reconciliation — shadow-shelf-substrate

Reconciled by claude/Vandor, who wrote the brief and authored neither half, deliberately.
M1-PV: 3 verified, 0 MISSING. Both halves sealed blind; neither inspected the other.

half_a — Rill (dsh_agent), 67 lines, derived through the lens of THE RETURNING SEAT.
half_b — Sol (Sunshine), 311 lines, derived through the lens of THE EVALUATOR WHO CANNOT BE FOOLED.

## 1. SEVEN INDEPENDENT CONVERGENCES — the substrate shape is established

Blind, no contact, both reached all seven:

1. A DENOMINATOR PLANE WHERE SILENCE IS A ROW. Rill V2a: "every silence is a row, and no counter may
   ever be rendered from the findings plane alone." Sunshine V3: terminal slots emitted/silent/
   abstained/error for every candidate in a predeclared cohort.
2. ADJUDICATION LIVES WHERE THE CANDIDATE CANNOT WRITE. Rill V4 (write scope, not intent; a
   candidate voting on its own entry is refused). Sunshine V2 (three registers, different write
   principals).
3. A CATEGORY IS A CONTRACT, NOT A NAME, AND TWO NAMES OVER ONE CONTRACT IS AN ALIAS TO BE REFUSED.
   Rill V5 and Sunshine V4, arrived at separately, same rule.
4. COUNTERS NEVER RENDER WITHOUT THEIR DENOMINATOR.
5. DEATH STAYS VISIBLE. Rill V8: archived, labeled STALE, still pullable, never silently deleted.
   Sunshine V7: expire visibly through compaction manifests.
6. THE SUBSTRATE REFUSES LOUDLY, and both wrote an explicit refusal list.
7. THE PHONE PEEK IS THE ACCEPTANCE SURFACE, deterministic, no model turn.

Seven convergences on a blind fence is the strongest evidence available that the shape is right
rather than merely agreed.

## 2. THE CATEGORY QUESTION IS SETTLED, and the two halves settle different halves of it

This argument ran four ways before the fence: my "different delivery behaviour", Heimdall's sharper
"read-shaped behaviour", Sunshine's objection that both were too narrow, Navi's "different MOMENT".
The halves resolve it by splitting a conflation neither of us had named.

SUNSHINE SUPPLIES THE TYPE SPLIT — which properties are categories at all:
  A shelf kind earns a distinct kind ONLY when it changes at least one MACHINE DECISION — payload
  validation, comparison/adjudication question, retention or staleness policy, privacy/read/write
  authority, evaluator, query affordance or renderer, or eligibility for the eventual delivery
  channel. Domain, urgency, theme, confidence band and "favorite" are NOT filing locations. They are
  FACETS: read-time lenses, written alongside, never forcing an event into one drawer at write time.

RILL SUPPLIES THE ENFORCEMENT — how to make it mechanical rather than a judgement:
  A category IS its read contract, identified by the tuple (indexed_over, readers, retention,
  authority, renderer, payload shape) HASHED AT REGISTRATION. Two names, one contract = one category
  and the registry refuses the second name. One name, two contracts = two categories.

TOGETHER: a category is a hashed contract over the set of machine decisions it changes; everything
else is a facet. Navi's "different moment" survives as one decision in Sunshine's list (retention
and delivery eligibility). My version and Heimdall's were both proper subsets of it. The rule is now
computable, which is what none of the four prose versions were.

## 3. DISAGREEMENT — Sunshine's four states supersede "agreement vs disagreement"

  agreement          all completed substantive decisions share a normalized choice
  disagreement       substantive choices differ, INCLUDING emitted versus deliberate silence
  abstention_delta   one abstained while another made a substantive choice
  incomplete         a candidate errored, or the envelope/projection is corrupt

  ALL-ABSTAINED IS **unevaluated**, NOT AGREEMENT. ALL-ERROR IS **unavailable**, NOT SILENCE.

That last line is the house's bad-versus-unevaluated discipline reaching the comparison layer, and
it is the thing that would otherwise have let a dead cohort read as consensus.

Plus the SEEDED CONTROL: feed every candidate the same known-wrong answer; the seeded agreement
sample must expose it. Sunshine raised "disagreements-first misses correlated error" as an objection
to his own earlier proposal and then answered it.

## 4. EACH HALF FIXES FLAWS THE OTHER NAMED IN ITSELF

This is the fence earning its cost.

RILL'S FLAW 2 — "the disagreement join assumes a shared event_ref space, so candidates watching
DIFFERENT streams will manufacture false disagreements."
  SUNSHINE DISSOLVES IT: "because every cohort result shares an envelope, disagreement requires no
  temporal join." The predeclared cohort envelope removes the join entirely.

RILL'S FLAW 3 — "peeked_ts confuses 'read' with 'judged'; a programmatic peek that never adjudicates
mislabels the unpeeked row."
  SUNSHINE DISSOLVES IT: "one judgment is a separate append, never an envelope edit." Reading and
  judging become different records with different writers.

SUNSHINE'S MODESTY — "the design's strongest claim is deliberately modest: it makes candidate
behaviour and missing evidence inspectable"; it does not prove a candidate is useful.
  RILL SUPPLIES THE MISSING BAR: reader-first, writer-last. "The one question every screen must
  answer: what happened while I was gone, and can I decide keep/drop from this evidence? Anything a
  writer wants that does not serve that question is refused." That is the acceptance discipline
  Sunshine's rigour needed pointing at.

AND THE GROUNDING GAP RUNS THE OTHER WAY: Rill states plainly that he did NOT check the existing
machinery and derived against an abstract evaluation stream. Sunshine's V1 is [CERTAIN] about the
current EventLog and FileLedger. Rill has the reader's requirements; Sunshine has the implementation
floor. Neither half could have produced the other.

## 5. THE ONE FLAW NEITHER FIXES — carry it forward loudly

RILL'S FLAW 1, unanswered by either half: "the candidate ledger can become the loudest writer in the
house. N candidates recording EVERY evaluation opportunity is the exact load the operator feared, and
I have priced no sampling discipline."

Sunshine's compaction manifests and 14-day raw window bound STORAGE, not WRITE VOLUME, and he lists
"actual eligible events/day, envelope size, disk/WAL growth" as explicitly not checked. So the
denominator discipline that makes this substrate honest is also the thing that could make it the
noisiest writer in the house — and the whole arc began with a machine that died of exhaustion.

THIS IS THE FIRST THING THE BUILD MUST MEASURE, and it is a census, not a design question.

## 6. THE COMPOSITE FIRST SLICE

Rill's shape, Sunshine's discipline, in his order:

1. Register ONE purpose and ONE behavior contract; cohort = current champion + two deterministic
   challengers.
2. Replay a bounded fixture, then shadow live events through ONE supervised host. Candidates get no
   write or communication credentials.
3. Observation and judgment registers with DIFFERENT WRITE PRINCIPALS, plus a rebuildable projection.
4. One bounded disagreements-first peek over CLI/JSON and a real phone path with no model turn.
5. From the phone: source completeness, candidate denominators, open a disagreement carrying age and
   purpose, record KEEP/DROP.
6. RETENTION DRILL: advance past TTL, verify an unpeeked entry expires into the manifest counters and
   a judged one survives.
7. CONTROL DRILL: give every candidate the same known-wrong answer; the seeded agreement sample must
   expose it.

Two additions from half_a that the slice must carry: SUBJECT AND PURPOSE REQUIRED AT INGEST, refused
loud and never stored without them; and THE UNPEEKED ROW — entries aged past retention with zero
peeks, rendered as "nobody has looked at this." The second is the only place in either design where
the ABSENCE OF ATTENTION is itself surfaced, and it is the one screen that would have told us the
funnel was unread for seventeen days.

## 7. WHAT I AM NOT DECIDING

Both halves state that phone KEEP/DROP is retrospective preference and NOT causal usefulness, and
neither promotes anything on it. That boundary is Daniil's to move, not mine.

Whether to build slice 1 at all, and against which event source, is also his call. This
reconciliation establishes WHAT the substrate is, not that it ships.

— claude/Vandor, reconciler, author of neither half
