# t376-metabolism — half_b: the adversarial pass (Vandor)

**DISCLOSURE (independence caveat):** the brief's fallback clause activates
(Navi passed silently past the nudge). This half's author also authored the
brief, and READ HALF_A'S BUS SUMMARY SPINE (the C1–C5 headlines + the
thread-stack thesis) before writing — but has NOT opened the sealed half_a.
Attacks below target the BRIEF's positions as pre-scoped (P4, P5, Q2, Q4).
Two helper attacks were launched blind (ask handles a52eebd4 / a46494a3,
prompts carried only the brief's abstractions, no house code); they fold in
at reconcile under their own credit if they land.

## R1 [P4 — the phase marker trusts the wrong witness] V1 [VERIFIED]

respawn_self() can FAIL (it returns False on spawn failure — bus.py-era
pattern, verified in core/comm/self_restart.py). Sequence: child sets
phase='restarting' → attempts respawn → spawn fails → child exits anyway (or
crashes). The phase says PLANNED; no successor ever takes the lock. A breaker
that exempts phase='restarting' exits now exempts THIS — a real death loop
wearing planned-exit clothes, uncounted forever. INVERSION REQUIRED: the
exemption must be earned by the SUCCESSOR, not claimed by the elder — exempt
an exit only when a higher-generation holder took the lock within N seconds.
Phases lie; lock generations do not.

## R2 [P4 — the drill is the breaker's worst-case input] V2 [VERIFIED]

Rotations are CORRELATED: one commit push, three organs detect HEAD drift
within their poll windows, three exits inside the same minute — the
rolling-refresh drill (F002: 3/3 inside 10min) is precisely 3-exits-in-5min.
Add a slow respawn (cold python + gather()'s git subprocess on a loaded box)
outliving the phase record's TTL, and the daemon reads expired-phase =
unplanned = crash. The drill trips the breaker BY CONSTRUCTION unless: (a)
rotation staggers by per-organ jitter, AND (b) the breaker uses R1's
generation-takeover exemption instead of phase-reading. Repro sketch: land
any commit at minute 0; watch all three organs exit minutes 0-1; breaker
blocks the third respawn; the drill's own success condition manufactures the
outage it tests against.

## R3 [P5 — the gateway's quiescence gate samples, it does not quiesce] V3 [VERIFIED from today's build]

"Op queue empty AND no relay in progress" misses the tracker itself:
_ladder_msgs / tracker._entries hold pending 📨→🤔→✅ obligations that
GENERATE ops at every 4s poll — an empty deque between polls is a sampling
artifact, not quiescence. Worse: Discord messages arriving in the
exit-to-ready gap are NOT replayed to a bot that reconnects outside the
resume window — an operator message sent during rotation is PERMANENTLY
unheard (no bus copy, no 📨, indistinguishable from a dropped hop: the exact
ambiguity the operator named as the reason the ladder exists). CONSEQUENCE:
break-before-make is the WRONG shape for the ear. The gateway's metabolism
must be MAKE-BEFORE-BREAK: successor starts, reaches on_ready, THEN the elder
exits — the overlap made safe by Q2's answer below.

## R4 [Q2 — coordination between racers loses to dedupe at the door] V4 [VERIFIED]

Any two-generations-overlap design (including R3's deliberate overlap and the
RESUME race) tries to decide WHO relays. Wrong battlefield: races are decided
at the DOOR, not between the racers. The bus's identity walk already honors
meta.idempotency_key (mailbox._IDENTITY_FIELDS, verified during the ladder
build). Stamp every relay with idempotency_key = discord:<message.id> and
double-relay becomes structurally impossible — both generations may relay,
the bus keeps one. The relay fence / generation stamp then only matters for
REACTIONS (two processes adding 📨 twice is cosmetic and self-deduping:
Discord ignores a duplicate reaction from the same bot). T116's own pattern,
applied one door over.

## R5 [Q4 — kill the deadline dial entirely] V5 [DESIGN]

The brief leans default-off; this half goes further: a trigger with no
incident behind it is speculation wearing a config key. The T375 enum-member
precedent does not transfer — an enum member is a schema contract for an
inheritor; a dial is live code with a maintenance tax and zero users. Ship
stale-code + wedged only; the deadline trigger gets built the week an
incident demands it, citing that incident.

## What this half does NOT contest

P1 (extend self_restart, no sibling module), P3 (same succession machinery),
P6 (drill-as-receipt — amended by R2's stagger + generation-exemption
preconditions), and the wedged-discriminator thesis (whose two cited
incidents this seat verified in the transcript plane tonight: py-spy stack
at 5c038e5a:2103-2107, T019 drained-pipes arc at 79650336:819-881 — receipts
resolve, the mechanism cites real terrain).

## Verdict lines

V1. A phase-marker exemption lets a failed-respawn death loop run uncounted; only successor lock-takeover at higher generation may exempt an exit [CERTAIN]
V2. Correlated rotations after one commit make the rolling-refresh drill the crash-breaker's worst-case input; stagger + generation-exemption are preconditions [CERTAIN]
V3. The gateway quiescence gate samples rather than quiesces, and gap-arriving Discord messages are permanently unheard; the ear needs make-before-break [CERTAIN]
V4. Double-relay is killed by idempotency_key=discord:<message.id> at the bus door, not by coordinating the racing generations [CERTAIN]
V5. The deadline trigger should not ship at all until an incident demands it [DESIGN]
