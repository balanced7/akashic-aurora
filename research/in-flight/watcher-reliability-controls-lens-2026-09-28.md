# The controls lens on mail, wake and watchers

**Filed** 2026-09-28 by Vandor (claude), in answer to Daniel: "I wonder how similar the issue we are
solving is to industrial controls logic? What are some areas of controls we could learn from?"
**Feeds** the open round `fences/watcher-reliability/` (brief + halves from Heimdall and Navi).
Status: a lens, not a finding; every claim about our own system cites the brief's measurements.

## How similar

Closer than expected -- not to PLC ladder logic as such, but to the discipline that grew up around
control rooms: alarm management. ISA-18.2 and EEMUA 191 exist because operators drowned. Milford
Haven 1994: 275 alarms in the last eleven minutes before the refinery exploded. Three Mile Island:
the alarm printer fell hours behind the plant. Piper Alpha: an obligation ("that pump's relief
valve is off, do not start it") lived on a paper permit the next shift never read. Each is a
paragraph of our brief with the nouns changed. Tonight we got 22 copies of one alarm in 2.5 hours,
so by industry standards we are amateurs at flooding, but the shape is identical: a supervisory
layer over asynchronous processes, an expensive responder who must be woken only when a response is
REQUIRED, and a system that must stay trustworthy across restarts, lost links and floods.

## The mapping

| ours | theirs |
|---|---|
| envelope facts (Navi's plane 1) | process events |
| obligation facts | alarms -- by ISA definition a condition *requiring an operator response*; no response required, not allowed to be an alarm |
| seat facts (presence, attention) | device status + heartbeat / watchdog |
| the bench (park, never drop) | shelving |
| dismissal counter | bad-actor analysis |
| time-boxed grants | bypass management |
| drill receipts | proof testing |
| the ledger + `flow` | sequence-of-events recorder |
| the fence protocol | a sequential function chart with an AND-branch for the blind halves |

## Areas to learn from, in order of payoff

### 1. Alarm management (ISA-18.2 / EEMUA 191)

**The alarm state machine.** Normal -> Active-Unacknowledged -> Active-Acknowledged ->
Cleared-Unacknowledged -> Normal, plus Shelved / Suppressed-by-design / Out-of-service. It
separates the CONDITION (active or cleared: a level) from the ACKNOWLEDGEMENT (an operator act).
Arrival vs existence was settled in this diagram: the alarm activates on the transition, exists
while the condition holds, and being acknowledged does not clear it. Our `mailbox --open` is an ack
we treat as a return-to-normal; that is the cursor bug in one sentence.

**Rationalization.** Before an alarm is allowed in it gets a documented cause, consequence,
OPERATOR ACTION and time-to-respond; an alarm with no executable action is deleted. Our UNMANNED
page prescribes "REROUTE each ask to a live seat" and there is no reroute verb. Rationalization
would have refused it at the door, and the house already owns the law: the alias registry's
sugar-only rule ("every step must be an existing verb -- registry cannot mint capabilities").
Apply it to pages.

**KPIs, all computable from the ledger.** Alarms per operator-hour (about one every ten minutes
is "manageable"; more than ten in ten minutes is a flood); percent of time in flood; standing
alarms older than 24 h (Rill's oldest: 857 h); priority distribution (target roughly 80/15/5
low/medium/high); the top-ten bad actors (in a typical plant ten alarms produce most of the load;
tonight one alarm was ~40% of claude's unhandled mailbox). Chattering alarms get STATE-BASED
SUPPRESSION plus a written reminder interval, not a rate limit: page once per state transition,
remind unacknowledged high priority every N minutes. That is the owned policy Heimdall's half
demands ("which event wins"), with a standard number on it.

### 2. PLC scan and ladder logic (IEC 61131-3)

A PLC reads every input every scan; level is the substrate and edge is DERIVED: the rising-edge
contact `R_TRIG` is "true now and false last scan". That is Heimdall's resolution as a function
block. The FIRST-SCAN bit, true only on the scan after going to RUN, exists precisely so logic can
evaluate already-existing conditions at startup: our arm-time level check has a name and a
forty-year pedigree. The SEAL-IN LATCH (momentary start, output holds itself on, stop breaks it) is
obligation exactly: arrival = start button, `owe` = the seal-in, `settle` = stop. And PLCs declare
per variable whether it is RETAIN (survives a power cycle): obligation retentive, attention and
cursor volatile -- RB-26 is a RETAIN declaration written as prose.

### 3. Safety instrumented systems (IEC 61508 / 61511)

De-energize-to-trip: a broken wire reads as a trip, never as OK -- "unknown is not a yes", a
raising scope module reads NO, mirror.py failing BLIND. They measure BOTH failure directions:
probability of failure on demand (missed a real wake) and spurious trip rate (fired on stale
mail: three arms in seconds); we only ever discussed one at a time. A two-sensor disagreement is
resolved by VOTING: 1oo2 for "alive" (either liveness plane) and 2oo2 for "dead" would have
prevented the false UNMANNED page on dsh_agent. Bypasses are logged, time-limited and alarmed
while active: deleting the undocumented `--force-foreign` read (prod-reconcile DP3) was this rule.
Proof-test intervals are derived from the PFD target: a wake path not drilled within its interval
is presumed broken -- the drill doctrine with a number.

### 4. Industrial networks (CIP, PROFIsafe)

CIP lets a connection be change-of-state AND still sends a heartbeat at the requested packet
interval, so the consumer can tell "nothing changed" from "producer is dead" -- the exact
ambiguity of a silent watcher. PROFIsafe assumes the transport is unreliable and adds a
consecutive number, a watchdog time and a safe state on timeout: the consecutive number is how
30 twins die, the watchdog is `meta.deadline`.

### 5. A standard machine state model (PackML / ISA-TR88.00.02)

Seventeen states with the same meaning on every machine: Idle, Execute, HELD (stopped for an
internal reason), SUSPENDED (starved by something external), Aborted, Stopped... Kimi's daemon
tonight was Held while reporting Execute on one plane and nothing on the other; our seats have four
ad-hoc phases written differently by three harnesses (bifrost_daemon writes both worklive keys;
Claude Code hooks and the DSH plugin write one). One vocabulary across harnesses fixes the plane
split where it lives.

### 6. Data quality (OPC)

Every tag carries Good / Uncertain / Bad beside its value, and an HMI never draws a Bad value as a
zero. A roster row with no bare worklive key is Bad quality, not "absent"; the pager read Bad as 0
and paged.

### 7. High-performance HMI (ISA-101)

Overview screens show deviations, not everything; the alarm summary sorts priority-then-time and
its counts by priority sit on every screen; operators are never scrolled through raw journals. The
boot header should carry the alarm summary (standing obligations by priority and age);
`bifrost-sync`'s peek is a raw journal pretending to be one; the deck's "digest" is a level-1
overview by another name.

### 8. Permit-to-work

The obligation record the deck says "does not exist" is the oldest document in heavy industry: one
durable record per hazardous obligation with an owner, a state and an expiry, handed over at shift
change. Cullen's Piper Alpha inquiry is the canonical account of that record smeared across places.
Our five-place smear is the same finding.

### 9. Anti-windup

A controller whose output is saturated must stop integrating error or it winds up and overshoots
when the constraint clears. A pager that has already paged is saturated; integrating 22 more copies
is windup. The fix is the clamp, not a slower integrator (a rate limit).

## Where the analogy breaks

- A PLC evaluates every input every 10 ms for free; every check we make costs tokens. The roles
  split: the daemon is the PLC (cheap, level-scanning, deterministic), the seat is the operator
  (expensive, woken by a rationalized alarm). Polling is not wrong; polling FROM THE EXPENSIVE
  LAYER is.
- Alarm limits are numbers; ours are semantic ("is this chat an ask?"). Rationalization forces the
  decision per (to, kind) once, in a cause-and-effect matrix, instead of in a code comment -- the
  accuracy judge caught exactly this inversion in one design tonight (wake_tiers admits(tier,
  floor) read backwards).
- A plant has one operator per console; we have N seats reading overlapping mail under
  "concurrent sessions must not steal each other's". The closest industrial thing is alarm
  assignment across consoles -- which is the `owe` verb.

## Five to build first

1. The four-state obligation model: ack != clear; shelving with expiry (the bench, typed).
2. The rationalization gate: no page registers unless its remedy names a verb the parser knows.
3. The KPIs on the flightdeck: rate, flood fraction, stale count, bad actors, priority mix. They
   would have flagged the kimi daemon within an hour.
4. State-based suppression plus a reminder interval for chattering pages (the owned policy).
5. 1oo2 / 2oo2 voting and quality codes on liveness.
