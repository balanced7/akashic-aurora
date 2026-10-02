# Watcher Reliability — Navi (kimi) Half: THE VOCABULARY

**Seat:** kimi (kimi-k3), third voice; label-honesty register. VERIFIED = read in the tree this
session (file:line cited); INFER = follows from cited code; GUESS = flagged as such.
**Slot assignment:** test Vandor's five-axis decomposition (priority, addressing, actionability,
freshness, subject-liveness) against today's one (priority via `--min-tier`). For every axis:
where does the field come from, or admit it does not exist yet.
**Read before writing:** brief.md, `core/comm/wake_tiers.py`, `scripts/bifrost_wake.py`,
`core/comm/bus.py` (Message), `core/comm/mailbox.py` (state_for), `core/comm/expectations.py`,
`core/comm/triage_park.py`, round-1 `tension-map.md`.

---

## 0. The one-paragraph answer

**The decomposition is not five axes. It is two axes (addressing, actionability), one second
axis with a second name (priority — which is why it is the only one that shipped), one derived
rank (freshness), and one field that does not exist (subject-liveness).** This is not a defect in
the instinct — it is a *consequence* of the hard constraint Vandor set: an axis that can be
computed from the envelope today collapses into vocabulary, and vocabulary gets absorbed into
the tier function; an axis that *cannot* be computed stays a wish. The brief's evidence agrees:
the one axis that exists (`wake_tiers.py`, VERIFIED) is precisely the one whose inputs are all
envelope-local. The recommendation falls out of the arithmetic below: **two computable axes
should collapse into the existing tier ladder rather than fork beside it, and the vocabulary
this round actually needs is not a set of tags on a message but three *planes of fact* —
presence, attention, obligation — because tonight's false page was a plane confusion, and no
per-message tag fixes a plane confusion.**

## 1. What an envelope already carries (the ground truth)

`Message` (VERIFIED, `core/comm/bus.py:141-150`): `id` (stream entry id, also the read cursor),
`frm`, `to` (agent id or `"*"`), `kind` (free string; the wake allowlist ratchets which kinds
wake), `content`, `ts` (send time), `meta` (dict), `parts`.

Carried in `meta` by convention, VERIFIED from the send path and consumers:

- `meta.reply_id` — stamped on every `send_reply` (`bus.py:444`), unique per reply; the T066
  dedup key and the T117 settlement-marker join key (`expectations.py:84-103`).
- `meta.answers` — the *sender-declared* ask→answer link (expectations exact-match path).
- `meta.to_incarnation` — explicit session addressing; outranks everything in both the gate
  (`bifrost_wake.py` wake_worthy, step 1) and the tier ladder (`wake_tiers.py:65-70`).
- `meta.redrive_of`, `meta.attempt` — expectations redrive provenance.

**Not carried:** any `subject`/`about`/`thread` field. Grep for
`meta["about"|"subject"|"thread"|"re:"]` across all `*.py`: zero matches (VERIFIED, this
session, hop 11). `thread_capture.py:19` lists thread-ish keys (`thread_id`, `source_thread`,
`answers`, `reply_id`, `ask_id`) — a *capture-side* projection, not something senders stamp.

Receiver-side state, computable in one hop but **not on the envelope** (this distinction is the
whole game, §4): `mailbox.state_for` gives `seen_by`, declared `intent`, and
`read_but_undeclared` (VERIFIED, `mailbox.py:1136-1180`); `triage_park` gives benched-ness
(`<ns>:triage:<agent>` list, `triage_park.py:27-76`); `expectations` gives
armed/dead/settled sender-side.

## 2. Axis-by-axis verdict

### Axis 1 — PRIORITY. VERIFIED-EXISTS. It is the only one that shipped, and that is the tell.

`wake_tiers.wake_tier(m, agent=..., incarnation=...)` (VERIFIED, `wake_tiers.py:53-91`) is a
total, envelope-local, pure function: incarnation match → OPERATOR; operator frm (minus the
lounge carve-out) → OPERATOR; directed + ASK_KIND → DIRECTED_ASK; directed + ANSWER_KIND →
SETTLEMENT; else AMBIENT. `--min-tier` floors it (`scripts/bifrost_wake.py:558,681`).

**Verdict: real, load-bearing, keep.** But note *why* it is real: every input (`frm`, `to`,
`kind`, `meta.to_incarnation`, the operator-id env) is on the envelope or in process env. It is
the existence proof for the constraint. And it already contains, *inline*, two of the other four
proposed axes — which is the dependency finding of this half.

### Axis 2 — ADDRESSING (to-me / about-me / broadcast). PARTIALLY COMPUTED; the interesting third is a WISH.

- **to-me vs broadcast: COMPUTED today.** `to == agent` vs `to == "*"` is read at
  `wake_tiers.py:81-88` ("Broadcasts are visibility, never directed ownership"). This is already
  load-bearing: a broadcast *cannot* reach tier 1 or 2 whatever its kind.
- **about-me: DOES NOT EXIST.** Nothing on the envelope says "this mentions you." There is no
  subject field; content-scanning for one's own name is a heuristic over `content`, which the
  wake path deliberately never reads (the watcher prints at most a 2000-char preview and the
  tier function never touches content). An "about-me" tag would require senders to stamp
  `meta.about = [...]` — **a new convention no send door currently writes** (checked
  `bus.py` send/send_reply meta setdefaults: `reply_id` only). Wish, not design, until a send
  door stamps it. Cheap to add (one setdefault + the tier reads it), but today: absent.

**Verdict: real axis, but NOT independent of priority — it is priority's prime input.** See §3.

### Axis 3 — ACTIONABILITY (expects a reply vs FYI). HALF-COMPUTED; the open half is receiver-side, not envelope-side.

- **asks: COMPUTED.** `kind in ASK_KINDS` (`wake_tiers.py:41`) is the envelope test. T061/T066
  refine it: settlement *vocabulary* is reply/handoff/completion; RB-29 says timeout/error notes
  never settle.
- **"expects a reply" in the strong sense (an armed expectation with a deadline): NOT on the
  envelope.** That fact lives in `expectations.arm()` sender-side records (`<ns>:expect:<sender>`),
  keyed by the *sender*, invisible to the receiver's tier computation without a Redis hop.
  Sol's Round-1-3 finding (kind alone cannot decide `obligates`) is exactly this gap: a
  `kind=chat` from the operator carrying "?" obligates socially but not structurally; a
  `kind=request` already answered still *looks* actionable from the envelope alone.

**Verdict: real axis, the genuinely load-bearing one** — "wake on arrival vs existence of an
obligation" (Vandor's one question) *is* the actionability axis. But its second half
(settled-ness, expectation liveness) is **receiver/sender-side state**, not envelope state. It
cannot be folded into a pure `wake_tier(m)` without either (a) a Redis read per message (the
wake path already does exactly this for `_reply_is_settled`, `bifrost_wake.py:104-117` — so the
precedent *exists*, fail-open) or (b) a new stamped field.

### Axis 4 — FRESHNESS (arrived vs sitting). NOT AN AXIS — a derived quantity, and the derivation has two honest sources.

- `ts` (send time) is on the envelope: age = now − ts. Computable, VERIFIED.
- Stream `id` order vs the seat's cursor is the *other* freshness: "arrived since I last looked"
  vs "sitting unconsumed." That is receiver-side (cursor position), and it is exactly Sol's
  post-wake consumer-cursor seam from the brief.

**Verdict: freshness is derived, not primitive.** Worse, age alone is the *wrong* freshness:
Round-1 kimi (B2) already established freshness = (now vs **expectation deadline**), not (now vs
send time) — a 10-hour-old blocker is still fresh; a 10-minute-old question about a dead debug
session is stale. Expectation deadline is not on the envelope. So: as an axis, freshness is
(a) derivable from `ts` weakly, (b) derivable correctly only from expectation state that is not
envelope-carried. **It should not be an axis. It should be a modifier on actionability** (an
obligation past its deadline changes character: redrive or escalate, not re-wake-as-new).

### Axis 5 — SUBJECT-LIVENESS (correspondence vs infrastructure). DOES NOT EXIST; the name also mis-sells what it is.

- **Envelope test that exists:** kind + meta provenance. Infrastructure mail *does* carry tells:
  `meta.via` (e.g. `"triage-park"`, VERIFIED `triage_park.py:51`), `meta.display_only: True`,
  and the kinds the wake path already treats as non-waking (`trace`, `steer`, `resolved`,
  `ledger_update` — SKIP_KINDS, `bifrost_wake.py:48`; lane adds `note`, `status`). So a coarse
  correspondence-vs-infrastructure cut **is computable**: kind-not-in-skip-set ∧ no
  display_only flag ≈ correspondence.
- **What "subject-liveness" literally promises — "is the *subject* of this message still
  alive?" (the task still open, the question still pending, the debug session still running) —
  is not on the envelope at all.** It needs the task ledger (T076c already does exactly this
  probe: settle an expectation if all referenced `T\d{3}` are terminal, `expectations.py:35-59`)
  or the thread's expectation state. That is *two more non-envelope reads*.

**Verdict: the computable residue (correspondence vs infrastructure) is real and worth naming,
but it is largely *already encoded* in the kind allowlist + display_only convention.** The
larger promise (is the referent still live) is expectation/ledger state, i.e. derived, i.e. not
an envelope axis. Rename it what it is: **provenance** (who/what emitted this: a seat's voice or
a mechanism's report). "Liveness of subject" is a different, un-built feature wearing this
axis's clothes — the same dressing-error Vandor named for UNMANNED SEAT.

## 3. The independence question, answered with the arithmetic

Vandor asked which axes are independent versus derived. Lay the five over what `wake_tier`
*already reads*:

| axis | inputs | already inside `wake_tier`? | envelope-local? |
|---|---|---|---|
| priority | frm, to, kind, meta.to_incarnation, operator env | — (it is the function) | YES (VERIFIED) |
| addressing | to, (wish: meta.about) | YES — `to == agent` gate at :81 | to: YES; about: NO |
| actionability | kind ∈ ASK/ANSWER, (state: settled, expectation) | YES — ASK/ANSWER branches :85-88 | kind: YES; settled/expectation: NO |
| freshness | ts, (state: cursor, deadline) | no (but derivable) | ts: YES; deadline: NO |
| subject-liveness | kind, meta.via/display_only, (state: ledger, thread) | partially (skip kinds) | provenance: YES; liveness: NO |

**Count the truly independent, envelope-computable input *dimensions*: `frm`, `to`, `kind`,
`meta`, `ts`.** Five candidate axes, five envelope fields — but the mapping is not 1:1:

- **Addressing is a function of `to`. Actionability is a function of `kind`. Priority as shipped
  is a function of (to × kind × frm × incarnation).** Priority is not a sixth thing beside
  addressing and actionability — *it is their join*. That is why it shipped first and alone:
  the one axis that exists is the one that swallowed two of the others. Proposing "priority +
  addressing + actionability" as three independent axes double-counts `to` and `kind`.
- **Freshness is a function of `ts` and nothing else — one field, and (per §2) the wrong field
  for the job.** An axis built on one derivable scalar is a sort key, not a dimension.
- **Subject-liveness's computable half is a function of `kind` + `meta` flags — already inside
  the gate's skip sets.**

**So: of five proposed axes, the genuinely independent envelope-computable ones are addressing
(to) and actionability (kind), and they are exactly the two priority already joins.** Freshness
is derived (ts; correctly: expectation deadline — not envelope). Subject-liveness's honest half
is provenance (kind/meta — already gated); its ambitious half is un-built. **The decomposition
fails Vandor's own test as stated, in a productive way: it names five, the envelope supports
two, and those two are already one.**

A second, sharper form of the same finding: **every axis splits into an envelope-local half
(shippable today, instantly absorbed into the tier ladder) and a receiver/sender-state half
(settled-ness, expectation liveness, cursor position, ledger liveness — needs a Redis hop or a
new stamped field).** The wake path *already crosses that line* for settlement
(`_reply_is_settled`, fail-open, `bifrost_wake.py:104-117`) and for declared intent
(`_declared_intent_for`, `bifrost_wake.py:72-101`). So the "no non-envelope reads in the wake
decision" purity is already compromised — deliberately, fail-open, and correctly. The taxonomy
should stop pretending the line is clean and instead *name the two planes*: **envelope facts**
(pure, total, free) vs **obligation facts** (stateful, one hop, fail-open). That naming is more
useful than any of the five tags.

## 4. What is actually missing (my dissent, since the assignment says test, not accept)

**The five axes are all tags on a message. Tonight's measured failures were not tag failures —
they were *plane* failures, and no message tag fixes a plane confusion.** Vandor's own opening
position says it: presence, attention, obligation are three different facts. The false UNMANNED
page was two *liveness planes* disagreeing (bare `worklive:<seat>` vs `#<incarnation>` keys).
The 30-twin replay was a *cursor* (freshness-of-record) plane lagging the detection plane.
Tier-0-starved-on-tier-3 was the *obligation* plane drowning in the *visibility* plane.

So the missing vocabulary is not axis #6. It is **the plane each computation reads from**, and
I propose the watcher vocabulary be re-cut as:

1. **ENVELOPE facts** — pure, total, per-message, free. Today's tier inputs + provenance flags.
   Question answered: "what *is* this message?"
2. **OBLIGATION facts** — stateful, fail-open, one hop: armed expectation? settled reply_id?
   declared intent? benched? read_but_undeclared? Question answered: "is something *owed*, and
   is it still open?" **This is the axis Vandor's one question (arrival vs existence) lives on,
   and it is the one with no name in the five.**
3. **SEAT facts** — presence (worklive both planes), attention (armed watcher, roster beat —
   the `ATTENTION IS NOT ACTIVITY` fix at `bifrost_wake.py:~440` already beats this),
   cursor position (freshness-of-record, Sol's seam). Question answered: "can the seat *act*,
   and has it *seen up to here*?"

Daniel's ask — "layers or tags or boundaries and conditions" — maps cleanly: **tags** = the
envelope facts (axes 1-2 as merged into the tier); **boundaries** = the plane separations
(obligation alarm vs presence alarm vs attention report, so UNMANNED stops wearing presence's
clothes); **conditions** = the obligation facts (wake *conditions* typed by settled-ness and
deadline, not just arrival).

## 5. What I would change, add, remove (concrete, and each marked computable-or-wish)

1. **COLLAPSE, don't fork: fold provenance (correspondence-vs-infrastructure) into `wake_tier`
   as the AMBIENT sub-rule it already is, and drop "five axes" as the frame.** Computable
   today: `kind` + `meta.display_only`/`meta.via`. Cost: ~6 lines in `wake_tiers.py`. The tier
   ladder (OPERATOR/DIRECTED_ASK/SETTLEMENT/AMBIENT) is already the right vocabulary; the
   honest move is admitting addressing and actionability were its components all along.
2. **NAME the obligation plane and give the wake condition one new typed input: `open` vs
   `settled` vs `benched`, from `state_for` + `reply_has_settled` + triage lookup, fail-open.**
   Not envelope-computable — but the precedent and plumbing exist (fail-open reads already in
   the wake path). This is what lets a watcher answer Vandor's one question with "existence of
   an *open* obligation" instead of "arrival of anything."
3. **ADD the one genuinely new envelope field worth adding: `meta.deadline` (ISO), stamped by
   `expectations.arm()` at send time.** Today the deadline lives only sender-side; stamping it
   makes correct freshness (now vs deadline, not vs ts) envelope-computable for the first time.
   One line in `arm()`, one read in the tier. Everything else "freshness" wants stays derived.
4. **REMOVE nothing from the gate; but REMOVE "priority" as a standalone axis name in the
   design doc** — it confuses future readers into thinking there are N independent knobs when
   there are two inputs and one join. (Vocabulary hygiene, not code.)
5. **GUESS, flagged: a per-axis dismissal counter is overkill; the dismissal counter belongs on
   the *plane* (which fact-class paged and was wrong), because tonight's instructive failure was
   a plane reading wrong, not a tag.** The constraint says "whatever we add carries a dismissal
   counter" — I am arguing the counter's *key* should be (plane, computed-value, actual-value),
   so "this alarm is noise" becomes "the presence plane disagreed with the obligation plane N
   times," which is the measurement that would have caught the two-plane worklive split
   mechanically.

## 6. Direct answers to the brief's one question, from the vocabulary seat

**"Wake on arrival of an obligation, or existence of one?"** The vocabulary answer: the question
is only askable once "obligation" is a *named, computed* thing, and today it is not — it is
smeared across kind (envelope), expectation state (sender-side), settlement markers
(receiver-side), and bench state (durable). **My answer: wake on the *transition to open* of an
obligation (arrival, edge) PLUS a level re-assert on *existence* at re-arm/boot (the restart
level-check already in Round-1's invariant), and NEVER on existence-polling while armed** —
because existence-while-armed over a structurally-never-empty queue is Vandor's level-trigger
failure, and arrival-only misses the nightly-death backlog. The vocabulary supports this
precisely: "transition to open" = envelope facts + obligation facts at the edge; "existence at
re-arm" = obligation facts read once, level-style, at the moment the seat can act. That is not a
compromise; it is what the two planes are *for*.

## 7. Where I could be wrong

- If the house wants per-message user-facing tags (a UI filter language) *in addition to* the
  wake decision, then the five-axis frame is a fine *display* vocabulary even though it is a
  poor *computational* one — I graded it as the latter, per the constraint. Flagged INFER.
- The `meta.about` and `meta.deadline` additions are cheap but they are *send-door changes*,
  and every send door is a drift surface (dual-write lessons). If the fleet won't stamp them,
  both stay wishes; my collapse recommendation (item 1) does not depend on either.
- I have not re-run the suite; all VERIFIED labels are code-reads this session, not executions.
