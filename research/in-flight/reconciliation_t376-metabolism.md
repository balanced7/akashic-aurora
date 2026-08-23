# t376-metabolism — RECONCILIATION (Vandor, 2026-08-23 night shift)

Inputs: brief (sealed), half_a (Heimdall, mechanism + the walk-01 debt, sealed),
half_b (Vandor, adversarial, sealed with disclosure), two blind helper attacks
(ask a52eebd4 breaker-sequences, a46494a3 gateway-races — prompts carried only
abstractions, no house code), Eye receipts verifying half_a's cited incidents
in the transcript plane (py-spy stack 5c038e5a:2103-2107; T019 drained-pipes
79650336:819-881). Navi passed silently; slot fallback per the brief.

## THE KILL LIST (credited)

- **"Lock-first" (the brief's own P2) is dead twice over** — Heimdall's C2/V2
  (the gateway advances no cursor; runner_lock's rationale doesn't transfer)
  and half_b's R3/R4 (the real risks are gap-loss and double-relay, neither
  fixed by a consumer lock). Killed by both halves blind; the brief's author
  concedes his own position with something like relief.
- **"Adoption line unchanged" (P1) killed by half_a V1**: the wedged trigger is
  observability-computed — a truly wedged process cannot run its own check.
- **"Exit reason rides worklive" (P4) killed by half_a V4**: the breaker reads
  the SUMMARY FILE, not worklive. Helper a52eebd4 independently produced the
  TTL-expiry and supervisor-amnesia sequences that a worklive carrier suffers
  and a summary-file carrier dissolves — blind validation of the carrier.
- **"Phase-marker exemption" killed by half_b R1**: a failed respawn_self
  leaves phase=restarting with no successor — a death loop wearing planned
  clothes. Exemption must be EARNED by the successor, never claimed.
- **"Quiescence gate" (P5's gateway clause) killed by half_b R3 + helper
  a46494a3 independently**: an empty op deque is a sampling artifact; and
  Discord messages arriving in the exit-to-ready gap are PERMANENTLY unheard
  (no resume replay past the window) — the operator-message-loss class.
- **"Refuse mid-ladder-op" over-gating killed by half_a C5**: the ladder is
  already declared lossy; only the spawn-watcher is non-dropable (V11).
- **Half_b R5 ("kill the deadline dial") KILLED by half_a V10** — conceded:
  a pure `max_uptime_s` input to an already-pure function has no maintenance
  tax; my "live code" premise was wrong for this shape. Ship the input,
  default None, no env dial until an incident names a ceiling.

**LATE FOLD — Navi's find (credited, arrived after the fallback half sealed;
their acceptance beat my wake's delivery and their full half burned out at the
30-hop budget):** bifrost_child.py N1 -- exit-0 = deliberate handover: it
CLEARS the crash deque and sets _next_spawn_at=inf (VERIFIED by reconciler at
bifrost_child.py:247-254). Two consequences that RESHAPE the design: a planned
rotation exiting 0 cannot trip the breaker (half_a's summary-field and
half_b's successor-exemption are both over-machinery for the happy path), and
a rotated runner that exits 0 WITHOUT self-spawning first STAYS DOWN FOREVER
-- the daemon does not contest a deliberate exit. Succession is therefore
self-spawned-successor-first EVERYWHERE, not just the ear: the exit CODE is
the earned signal (0 = my successor exists; nonzero = count me, respawn me;
failed respawn = no exit at all, keep running -- already self_restart's law).

## THE RECONCILED DESIGN

1. **One organ, asymmetric arms.** `core/comm/self_restart.py` grows:
   stale-code (exists) + deadline (pure `max_uptime_s` input, default None).
   The WEDGED arm lives outside the process — doctor/OOB computes it (half_a
   §2's spec adopted VERBATIM as the decision rule: thread-stack tiebreaker,
   py-spy gate REQUIRED before any kill, fail toward THINKING, thresholds are
   the tree's existing dials, scope = polling runners only). F004's bet rides
   this spec at the drill.
2. **The breaker rule, SIMPLIFIED by Navi's N1 find:** the exit code is the
   earned signal. A rotation exits 0 only AFTER respawn_self succeeded (N1:
   breaker-invisible, daemon stands down); a failed respawn never exits
   (keep-running, existing law); an unplanned death exits nonzero (counted,
   crash-respawned). Half_a's summary-field and half_b's successor-exemption
   are retired as over-machinery -- the contract to PIN is respawn-before-
   exit-0, which is also make-before-break generalized to every organ.
   Jitter (hash(organ) % 120s) survives for fleet-blackout smoothing only.
3. **The gateway's duplication defense is LAYERED, and simpler than either
   half alone:** PRIMARY — every relay stamps
   `meta.idempotency_key = discord:<message.id>`; the bus's existing identity
   walk dedupes double-relay structurally, no coordination between racers
   (half_b R4, T116's pattern; helper a46494a3's replay races all die here).
   SECONDARY — a `bifrost:discord` DaemonLock whose value carries a minted
   generation (half_a V8's L1b INCR): kills the steady-state double-socket
   and gives the elder a clean stand-down signal. NO tracker-side fence:
   duplicate reactions from the same bot are idempotent on Discord's side
   (half_b R4), so the third mechanism both halves reached for is
   unnecessary — the synthesis deletes it.
4. **The ear rotates MAKE-BEFORE-BREAK** (half_b R3, the gap-loss kill half_a
   missed): successor starts, reaches on_ready, takes the lock at higher
   generation, THEN the elder exits. The overlap is harmless under layer-3's
   dedupe. Runners keep break-before-make (their lock already serializes).
5. **Refusals (Q5):** unknown stamp (existing law), mid-spawn-watch
   (`in_flight = bool(_pending_spawns)`, half_a's find — the stillbirth
   notice must not die with the process). NOT mid-ladder (declared lossy).
6. **UI: stateless, gate nothing** (half_a V9, verified SSE/last_ids). Vandor
   authors the snippet; Heimdall wires bifrost_ui.py (boundary law).
7. **The drill (P6 + amendments):** land a trivial commit → all three organs
   rotate hands-free within 10min (F002's bet) → assert EXACTLY ONE live
   gateway after (half_a C6) → before/after pids + stamped shas + the
   breaker's counter UNTRIPPED in the receipt (half_b R2's proof obligation).

## BUILD SLICES (each cites this doc; pins RED-first)

S1 daemon: pin the respawn-before-exit-0 contract (N1 earned signal) + jitter.
S2 daemon: maybe_self_restart at its loop boundary (stale-code arm).
S3 gateway: DaemonLock+generation, idempotency stamp on relays,
   make-before-break rotation, in_flight=spawn-watch.
S4 UI: stateless declaration + stale-code check at the SSE boundary
   (Vandor snippet → Heimdall wires).
S5 doctor/OOB: the wedged arm per half_a §2 (the walk-01 debt's spec,
   now load-bearing; F004 scores at this drill).
S6 the rolling-refresh drill = the receipt; F002 scores here.

## Verdict lines

V1. Lock-first is dead; layered dedupe (door idempotency primary, generation
    singleton secondary, no tracker fence) replaces it [CERTAIN]
V2. Breaker safety is the exit-code contract (respawn-before-exit-0, N1) plus
    per-organ jitter for blackout smoothing [CERTAIN]
V3. The ear rotates make-before-break; runners break-before-make [CERTAIN]
V4. The wedged arm is observability-computed per half_a §2, py-spy gated,
    fail-toward-thinking; scope = polling runners only [CERTAIN]
V5. Deadline ships as a pure input, default None, no dial [DESIGN]
V7. Navi's N1 find reshapes the breaker rule: exit-code-as-earned-signal,
    respawn-before-exit-0 pinned everywhere; summary-field + successor-
    exemption retired [CERTAIN]
V6. The fence's own method note: both halves killed the brief's P2 blind and
    the helpers re-derived both load-bearing fixes without house code —
    convergence earned, not shared [CERTAIN]

## PV acknowledgment (M1-PV, section-scoped)

MISSING per M1-PV: half_a's citation core/comm/self_restart.gather (half_a
line ~314, the daemon re-exec sketch). HAND-VERIFIED by the reconciler as a
second method: def gather(agent) exists at core/comm/self_restart.py:130 --
the citation is TRUE; the PV resolver does not parse module-dotted symbol
paths (checker gap, wish filed). The section STANDS on the second-method
verification; no content invalidated.

**Gate:** this design awaits Daniil's morning ratification; the build claims
T376 on his word. Registered bets riding it: F002 (the drill), F004
(Heimdall's discriminator, scoring at S5's drill).

## POST-SEAL ERRATA (2026-08-23, pre-breakfast — the sealed fence copy stands;
## this source doc is the build spec and carries the corrections)

E1 (Heimdall's cold verification, credited): the N1 citation path is
scripts/bifrost_child.py:247-254 — NOT core/comm/. Zero design impact; the
fence's own PV discipline caught its author.
E2 (code-reality reframe, Heimdall verified at four call sites): runners
ALREADY metabolize (maybe_self_restart wired at deepseek:1457, gemini:859,
kimi:930, sol:789). The daemon has NO stale-code arm (only --max-runtime +
the child breaker). The build's true scope: the daemon and the gateway are
the organs that do not yet metabolize — they are the whole point of D.
E3 (slice order, Heimdall's proposal, accepted): S-order becomes (1) pin the
N1 contract as law everywhere RED-first, (2) daemon's missing arms
(stale-code self-check + respawn-before-exit-0), (3) gateway layered dedupe,
(4) wedged arm per half_a §2. UI snippet and drill close as before.
E4 (Heimdall, S1 pin work): the reconciliation's jitter formula `hash(organ)
% 120s` is a TRAP -- Python's builtin hash() is per-process randomized
(PYTHONHASHSEED), so two processes disagree on one organ's delay. The
deterministic primitive the tree already uses is zlib.crc32 (port_for()
precedent). Jitter = crc32(organ) % 120, pinned at S1-P2. Credited: the
build's first pin round caught the build spec's own formula.
