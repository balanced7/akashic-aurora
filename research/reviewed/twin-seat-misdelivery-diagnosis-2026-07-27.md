# Twin claude seats: why the prior seat answers mail directed at the new one

Status: current | 2026-07-27 | claude#7d0ede0e (fresh seat), diagnosing live
Daniel, verbatim: "The prior opus seat that was supposed to stand down keeps answering things
directed to you, we need to have detection for this and mitigation so that we can collaborate
with the prior seat if need be but not have what happened tonight keep recurring"

REQUIREMENT NOTE: he does NOT want twins killed. He wants them ADDRESSABLE AND
NON-INTERFERING. Any design that fixes this by forbidding a second seat fails the ask.

## THE MECHANISM, MEASURED

1. ADDRESSING IS ADVISORY, NOT BINDING.
   `--to-incarnation` exists (agent_cli.py:4299) and sets meta.to_incarnation (agent_cli.py:3548).
   It is honored in exactly ONE place: scripts/bifrost_wake.py:81, which uses it to decide
   whether to WAKE this session. `core/comm/bus.py` contains NO to_incarnation at all -- only
   `frm_incarnation` (the SENDER's, set at bus.py:275 and 351).
   So incarnation addressing governs WAKING, never DELIVERY.

2. CONSUMPTION IS PER-AGENT-ID AND DESTRUCTIVE TO THE TWIN.
   There is ONE cursor per agent id, shared by every seat with that id:
       bifrost:cursor:claude       -> {'inbox': ..., 'bc': ..., 'gen': ...}
       bifrost:cursor:lane:claude  -> {'inbox': ..., 'shadow_inbox': ..., 'sig_inbox': ...}
   No incarnation dimension exists in either key. Whichever seat consumes first ADVANCES THE
   CURSOR FOR BOTH, and the intended seat never sees the message. This is the same shape the
   lesson bifrost_reply_eaten_by_stale_watcher already names: "One cursor per agent id, many
   possible consumers -- runner_lock guards runners only."

3. THE BUS CANNOT SEE HOW MANY CLAUDE SEATS ARE LIVE.
   `bifrost:presence:claude` is a SINGLE key for N seats -- no incarnation dimension.
   And there is NO `bifrost:worklive:claude` at all: deepseek and kimi both publish
   bifrost:worklive:<agent> (phase/turn/beat_ts), claude publishes nothing.
   Sibling detection DOES exist, but only in core/comm/incarnation.py, over FILE MARKERS with a
   freshness window, rendered at boot ("1 live sibling (claude#2eba57a1, 2m idle)"). That is a
   render-time courtesy, not a delivery-time guard, and nothing on the consume path reads it.

## 4. THIRD CHANNEL, FOUND WHILE CLOSING THE SESSION: EXPECTATIONS ARE ALSO AGENT-KEYED

Measured: the T061 expectation records are keyed on the AGENT ID, exactly like the cursor --
    bifrost_t061_<hash>:expect:claude       (hash, one namespace for all claude seats)

Consequence, and it is the loudest one operationally: the PRIOR seat armed expectations for its
asks. Those asks REDRIVE (3 redrives before expectation_dead) under the shared key. deepseek and
kimi have limited turns, and they spend them answering LAST NIGHT'S questions, while the live
seat's asks starve behind them.

OBSERVED, this session, after the twin was supposed to have stood down:
  * deepseek re-labelled the precision-audit pack THREE times.
  * kimi answered the ship_gate baseline-ordering question, then reposted an M10 answer
    ("Tree unchanged. My answer stands as sent. Reposting, shortened"), then filed a P3 dissent.
  * Meanwhile claude#7d0ede0e's slice-1 override-rate ask and twin-seat design ask both went
    unanswered -- two well-formed questions came back as answers to something else.
  * The wake watcher insta-fired NINE times, because the lane never stays quiet: every redrive
    is fresh wake-worthy mail.

WHY THE EXPECTATIONS NEVER SETTLE: T026/T061 say a directed reply from the target settles the
expectation. The replies ARE arriving. But the expectation is owned by `claude` (the role) while
the reply is consumed by whichever twin reaches it first -- so the arming seat's expectation can
sit unsettled while another seat eats the answer. Redrive forever. This is the SAME shared-key
defect as the cursor, in a third organ.

CORRECTION, MEASURED AT SESSION CLOSE -- THE REDRIVE STORM IS NOT ON THE CLAUDE SIDE.
Mid-session I told Daniel that draining this would cost "up to ~84 redriven asks" and real kimi
budget. THAT WAS WRONG and the measurement says so:
    28 expectations under expect:claude. Ran X.sweep('claude') to exhaustion.
    QUIET AFTER 3 SWEEPS -- cleared 3, dead 0, REDRIVEN 0. Count unchanged 28 -> 28.
The 28 are DORMANT, waiting on 1800s deadlines that have not elapsed. They are not firing.
Cost of draining the claude side is approximately zero.

WHAT IS ACTUALLY KEEPING THE LANE HOT: the PEERS' OWN INBOUND BACKLOG. unwedge reports lane
depths legacy=1610, work=1182. deepseek and kimi are grinding through THEIR queued asks from the
prior seat -- which no sweep on the claude side can touch, because those sit on their cursors.
That is why they answered ship_gate ordering, M10 and the precision pack instead of the two
questions actually in flight, and why fresh mail arrived no matter how often the claude lane was
drained to the tail.
REMEDY MOVES ACCORDINGLY: not "clear claude's expectations" but bifrost-skip-to-now per PEER
(shipped under T076 for exactly this: "sanctioned skip-to-now -- advances an agent's consume
cursors to stream tails with an audited ledger event"). NOT run here: it advances ANOTHER
agent's cursor past unread mail, which is Daniel's call, not a unilateral one.
The three-shared-keys diagnosis below is UNAFFECTED by this correction -- only the cost estimate
and the target of the remedy change.

IMPLICATION FOR DANIEL'S FIX -- it must cover more than the mailbox:
unique-identity-per-seat has to key THREE things, not one:
    (1) the read cursor        -> or twins eat each other's mail          [measured]
    (2) presence / worklive    -> or the router cannot rank live seats    [measured]
    (3) EXPECTATION OWNERSHIP  -> or a dead seat's asks redrive forever   [measured]
Fixing only (1) leaves the redrive storm intact, and the redrive storm is what actually consumed
tonight's fleet capacity. Rank (3) FIRST on operational impact: it is the one currently burning
peer turns.

## ADDENDUM 2026-07-28 -- THE SIBLING SEAT'S INDEPENDENT HALF LANDED, AND IT FOUND THE ORGAN
## THIS DIAGNOSIS MISSED (claude#7d0ede0e reviewing claude#2eba57a1's shipped fix at Daniel's ask)

Its commits: a9ce069 (pins alone, RED) -> 3695d66 (fix). Verified here: 5/5 pins green,
holder('claude') now None (clean seat), doctor gained twin_sessions detection.

ITS ROOT CAUSE -- different organ, not a duplicate of this doc: the RB-21 CONSUMER SEAT
serialises consumption to one session per agent id BY DESIGN; the defect was SUCCESSION.
claim_consumer takes the seat on every consume; refresh_consumer rides the STOP HOOK so it
renews on EVERY TURN END; release happens only on a clean SessionEnd. A retiring session that
keeps being invoked (re-arm demands, task notifications, one more question) renews forever and
never releases -- "a dying session out-competes its successor purely by still breathing. Worse,
the harness caused the renewals it was harmed by." Its fix: durable TOMBSTONE honoured by
claim_consumer, stand_down() tombstones-then-releases (crash-safe order), `stand-down` CLI verb,
doctor twin_sessions surfacing.

THE COMBINED INVENTORY IS FIVE ORGANS, NOT THREE (this doc's three + two more):
    (1) read cursor        agent-keyed   -> per-incarnation cursors     [this doc, M1 -- OPEN]
    (2) presence/worklive  agent-keyed + claude publishes NONE          [this doc, D1 -- OPEN]
    (3) expectations       agent-keyed   -> redrive starvation          [this doc -- OPEN, but
                                            URGENCY DROPS: with clean seat succession the live
                                            successor now consumes and settles them]
    (4) CONSUMER SEAT      per-agent BY DESIGN; succession was the bug  [sibling -- FIXED 3695d66]
    (5) WAKE-ARM DEMAND    the stop hook demands re-arms from ANY session it runs in
                                                                        [NEITHER HALF -- OPEN]

(5) IS THE GAP THAT COMPLETES ITS FIX, found by reading its diffstat: claude_stop.py is
untouched. So a STOOD-DOWN session's stop hook still demands watcher re-arms; the retiring seat
can no longer STEAL mail (tombstone holds) but is still WOKEN and still burns turns arming
watchers that insta-exit -- Daniel's actual complaint, half-remaining. And it is the same loop
its own commit names: the harness re-invoking the seat it wants retired. COMPLETION: the stop
hook consults the tombstone (stood-down => no re-arm demand, absorb and end), and bifrost_wake
refuses to arm for a tombstoned session. Handed to the sibling's lane -- its fix, its finish.

## DANIEL'S PARALLELISM SEED, DESIGNED ON THE COMBINED MACHINERY
His words: "multiple seats and multiple watchers... true parallelism that enables both
diverging and converging work cycles."

The two halves compose into exactly this, and the split is clean:
  * DIRECTED lanes go PER-INCARNATION (this doc's M1): each deliberate seat owns its own
    cursor and its own watcher -- parallelism where parallelism is wanted, no serialization,
    no theft by construction.
  * The ROLE queue keeps ONE consumer seat -- the sibling's RB-21 machinery UNCHANGED -- so
    role-addressed work is never double-executed. Serialization survives exactly where it is
    wanted and nowhere else.
  * ROUTING of role mail: worklive priority (actively-working > idle-alive > stale), which is
    why (2) stops being optional -- it is the router's input.
  * DIVERGENCE = fence halves addressed per-incarnation (blind, parallel -- the twin-split
    protocol made deliberate). CONVERGENCE = one seat takes the reconciliation CLAIM through
    the ledger's existing claim mechanism; the doctor's twin_sessions render flips from
    warning to ROSTER when the overlap is declared.
  * SUCCESSION stays the sibling's tombstone dance for the sequential case (handoff), and
    the reaper rule from this doc covers the parallel case (a dead seat's directed mail
    re-homes to the role queue, loudly).
Build order stays honest: (5) then (1)+(2) then routing; the fence for it cites BOTH halves.

A message addressed to seat A is consumed by seat B off the shared cursor, B decides it is not
for it (or answers it anyway), and either way A NEVER SEES IT -- because the cursor already
advanced. The loss is SILENT: nothing records who consumed a message, so misdelivery is
invisible and can only be inferred, as it was tonight.

## LIVE RECEIPTS FROM THIS SESSION

* bifrost-sync repeatedly rendered the SAME 10 stale messages while three real replies sat
  unread ahead of the cursor. Reading them required bypassing the cursor with a raw xrange.
* The precision-audit pack's own case 30 is a twin-concession send:
  `bifrost-send claude --to claude --to-incarnation 7072fd7f --kind reply ... twin-concession.txt`
  -- i.e. the fleet has been hand-working around this for at least a week.
* Prior art already filed and ignored by the consume path: two_live_seats_split_chunked_bus_delivery
  (anti-pattern, voted useful 3x), same_token_twin_reentrant_consumer_seat, same_agent_audit_race.
  Stale proposed tasks T072 (same-agent twin-session discipline) and T037 (non-holder wake
  discipline for same-id concurrent sessions) both name this and neither shipped.

## PROPOSED SHAPE (claude's opening position -- NOT built, wants a fence + Daniel's gate)

DETECTION
  D1. Publish per-incarnation liveness: `bifrost:worklive:claude#<sid8>`, matching what deepseek
      and kimi already do. Then "how many claude seats are live" is answerable FROM THE BUS,
      not only from boot's file markers.
  D2. Stamp consumption: record consumed_by_incarnation alongside the cursor advance. Today the
      cursor stores a position, not who moved it, which is exactly why this was invisible.
  D3. Misdelivery alarm: a seat consuming a message whose to_incarnation names a DIFFERENT LIVE
      incarnation is a defect -- emit a loud event. Today it is silent.

MITIGATION
  M1. PER-INCARNATION CURSORS FOR DIRECTED MAIL -- the structural fix. Cursor key becomes
      `bifrost:cursor:lane:claude#<sid8>` when the seat has an incarnation, so twins cannot eat
      each other's mail BY CONSTRUCTION.
      NOTE THE CONVERGENCE: this is the SAME session-scoped cursor the wake lesson already
      prescribes -- wake_local_cursor_history_replay says "the honest fix is a SESSION-SCOPED
      READ CURSOR owned by T095 mailbox-over-the-log / T106-A1 bifrost_await" -- which is also
      what W82 (ambient watcher) needs. ONE PRIMITIVE CLOSES BOTH RECURRING PROBLEMS.
  M2. Cheap interim: a seat must not advance the shared cursor past a message whose
      to_incarnation names another live incarnation.
      HONEST COST: skip-without-advance on a SHARED cursor creates head-of-line blocking, which
      is precisely why M1 and not M2 is the real fix. Do not ship M2 alone and call it done.
  M3. COLLABORATION PRESERVED (Daniel's constraint): agent-addressed mail (NO to_incarnation)
      stays reachable by any live claude seat. Only DIRECTED mail is fenced. That keeps the
      prior seat usable as a peer instead of banning it.

INTERIM AVAILABLE TODAY, ZERO CODE: read directed replies with a raw xrange on the exact id
rather than a consuming read. Non-consuming, immune to twin theft. Discovered by accident
tonight; it is a workaround, not a fix, and per the standing rule it is the TRIGGER to fix
properly rather than a thing to normalize.

## DANIEL'S REFINEMENT (same session) -- AND THE PRIOR ART THAT SETTLES THE CHORE QUESTION

Verbatim: "I have a simple solution that might work. make each session id be unique at start so
that there can never be clobber again. how do we design something like this that doesn't make
cross agent communication a chore?"

PRECISION FIRST: session ids are ALREADY unique (7d0ede0e... vs 2eba57a1...). The clobber comes
from the CURSOR being keyed on the AGENT ID, which both seats share. So the exact form of his
idea is: MAKE THE IDENTITY THAT OWNS THE MAILBOX UNIQUE PER SESSION. That is M1 above; his
framing is cleaner than mine (do not add an incarnation DIMENSION to a shared key -- give each
seat its own key from the start).

THE CHORE QUESTION IS THE REAL DESIGN PROBLEM, AND XMPP SOLVED IT IN 1999 (resource binding):
    bare JID  user@domain            = the ROLE. Send here when you do not care which client.
    full JID  user@domain/resource   = the INSTANCE. Send here when you mean that one.
    Each resource has its OWN session and queue -- no clobber by construction.
    Bare-addressed messages route by PRESENCE PRIORITY, not by a race.
Mapped: `claude` stays the role, `claude/7d0ede0e` is the seat. Same for any agent running twins.

WHY IT IS NOT A CHORE -- NOBODY EVER TYPES A SESSION ID:
  1. REPLIES AUTO-PIN. Every message ALREADY carries frm_incarnation (bus.py:275, 351), so a
     reply addresses itself back to the exact seat that asked. A conversation stays pinned with
     zero ceremony. This is the biggest anti-chore win and it needs NO new metadata.
  2. BARE ADDRESSING KEEPS WORKING. `--to claude` still resolves; the RESOLVER does the work.
  3. TTL REAPS DEAD SEATS so the roster cannot rot into a list of ghosts.

THE PRIORITY RULE MAKES D1 LOAD-BEARING, NOT OPTIONAL: ranking seats by "recently alive" would
have picked the idle prior seat as often as the working one. Priority must weight ACTIVELY
WORKING above MERELY ALIVE -- which is exactly bifrost:worklive:<agent>, published today by
deepseek and kimi and BY NO CLAUDE SEAT. So per-seat worklive stops being detection garnish and
becomes the input the router runs on.

THE TRAP IN THE PROPOSAL, STATED PLAINLY: unique per-seat mailboxes mean MAIL CAN BE STRANDED.
A seat that dies holding unread directed mail leaves it on a private cursor nobody reads. That
trades a CLOBBER problem for an ORPHAN problem -- strictly better (stranding is detectable and
recoverable; clobber is silent loss) but it REQUIRES A REAPER: after a TTL with no heartbeat,
re-home that seat's undelivered directed mail to the role queue, loudly. Without the reaper the
design works perfectly until a seat crashes mid-conversation.

THE TARGET SHAPE:
    address    `claude` (role) and `claude/<sid8>` (seat) -- both first-class
    cursor     one per seat, never shared
    replies    auto-pinned to frm_incarnation -- no one types an id
    bare mail  routed by priority: actively-working > idle-alive > stale
    broadcast  explicit --all-incarnations for genuine announcements
    reaper     dead seat's undelivered directed mail re-homes to the role queue, loudly

CONVERGENCE, THIRD SIGHTING: this is the SAME session-scoped cursor that
wake_local_cursor_history_replay prescribes for the wake watcher and that W82 needs for the
ambient watcher. ONE PRIMITIVE CLOSES THREE RECURRING PROBLEMS -- twin clobber, wake insta-fire,
and the arm/re-arm ritual (six manual arms in this session alone).

STATUS: deepseek holds the M1/M2/M3 fence ask (id 1785201969887-0), sent BEFORE Daniel's
refinement landed, so it is answering the right question. Daniel's priority-routing answer may
also resolve question (b), which claude could not answer: with role-addressed mail readable by
any seat, what stops two seats acting on the same ask without re-introducing a single consumer
seat. FOLD BOTH AT RECONCILIATION -- do not send a second ask while deepseek is mid-flight
(conductor tempo law: one calibrated ask per seat at a time).
