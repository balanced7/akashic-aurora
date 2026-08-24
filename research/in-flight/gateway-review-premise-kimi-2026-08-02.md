# Gateway review — PREMISE AND ROT (kimi, follow-up, tight)

Status: filed 2026-08-02, kimi. Follow-up to
`research/in-flight/coordination-review-premise-kimi-2026-08-02.md` (filed first, per
sequencing). Reviews `research/in-flight/coordination-addendum-api-gateway-daniil-2026-08-02.md`.
Still blind of deepseek. VERIFIED/INFER/GUESS labeled.

## (1) New roster-that-lies / SPOF debt? Substrate or projection?

**Not a SPOF on the traffic plane — the fail-open rule genuinely kills that. The SPOF
migrates to the TRUTH plane, and that is where it becomes a roster-that-lies candidate.**

INFER, mechanics: the doc's "gateway FAILS OPEN (bypass mode; it must never be able to
take the fleet down)" is the correct and sufficient answer to the transport SPOF question —
a dead gateway that passes bytes is no worse than no gateway. But fail-open has a
consequence the doc does not name: **the gateway cannot distinguish "I am bypassing myself"
from "there is no traffic."** Both render as silence from the wire tap. The roster-that-lies
was never a process that crashed loudly — it was a surface that kept rendering DEAD/STALE
with full authority while the truth was elsewhere (VERIFIED:
`roster_sensor_wrong_about_the_seat_reading_it`, 2026-08-01 — my own row read STALE while I
was mid-turn). A bypassed gateway is that instrument at birth: its absence-of-reading is
ambiguous between "fleet idle" and "fleet unsensed," and every downstream consumer
(codebook, board, Daniil's glance) will read it as the former, because absence-renders-as-
idle is the default failure mode of every meter.

So: it does not create SPOF-shaped debt in the dependency sense; it creates
**coverage-shaped debt** — the sensor's evidentiary scope silently shrinks while its
rendered authority stays constant. That is the roster's exact disease, one layer down.

Two-speed: **SUBSTRATE, and the doc already votes that way against its own fence.** The
"one more single-writer field-set on bifrost:sensor:<agent>" framing treats it as
infrastructure feeding verdicts. But the doc's own rule — "meters by default, content only
into the trace lane by deliberate choice" — splits it: the CAPTURE (tap, attribution, hash
writes) is substrate and pays full ceremony (fail-open kill drill, pre-registered
acceptance against recorded SSE ground truth, attribution spoof test); the RENDER of
gateway-derived columns on any board/dashboard is projection, fence-lite, gated on Daniil
seeing it. The addendum should not ship as one slice; it is two slices with different
prices. Note the identity-plane exposure: X-Akashic-Agent is a self-asserted header —
one-level naming riding a two-level system (VERIFIED: the
`concurrent_same_name_instances` lesson). A runner that omits or mis-states it attributes
its traffic to the wrong seat or to nobody, and the gateway cannot tell. The header needs
a gateway-side loud default (`unknown-<conn-id>`), never nearest-seat inference — the same
law as the hook fallbacks that silently substitute 'claude'.

## (2) COLD-SEAT / BYPASS ROT — the forcing function

The bypass is the gateway's **roster moment in advance**: a fresh seat with the provider's
base_url is invisible to the sensor and the sensor's silence reads as "no traffic," not
"unsensed traffic." Tonight's lesson generalizes it (VERIFIED:
`drain_traces_are_backlog_not_liveness` — content surfacing proved only that a seat once
spoke; here, absence of content would "prove" only that no sensed seat is speaking). A
fresh seat is precisely the population too new to have been taught to cooperate
(`a_detector_that_needs_cooperation_misses_its_own_population` — the detector shipped and
was blind to the two runners whose staleness motivated it; same shape).

Forcing functions, stacked cheap→strong; the design needs the first two at minimum:

1. **Coverage must be a rendered field, never an assumption.** The codebook's per-seat
   columns include `gateway_coverage: sensed | unsensed | unknown`, and `unsensed` renders
   at the same alarm tier as `wedged` — because an unsensed seat is a seat about which the
   board may be lying. This makes bypass LOUD by construction: the panel's silence about a
   seat becomes a named state, not an absence. Absence-as-evidence is only valid when
   presence is guaranteed visible (the main doc's own epistemic claim); coverage-rendering
   is what pays for that guarantee.
2. **External cross-check that needs no cooperation** (the T116 move, already house law):
   the gateway sees wire traffic; the ledger sees emitted signals; the process table sees
   runners. A seat emitting signals whose runner process holds no gateway connection in the
   census is BYPASS, rendered as such. This is cheap — all three sources already exist —
   and it converts "gateway silence" from an ambiguous reading into a diffable fact. This
   is also the cold-seat-law answer: the gateway must not be the sole repository of its
   own coverage state; the ledger and the process table are the independent witnesses.
3. **Fail-closed at the wallet, not the wire** (GUESS at feasibility, strong if buildable):
   provider keys live ONLY in the gateway; runners hold no key. Then bypass is not
   silent — it is impossible without a key the seat doesn't have, and "discoverable"
   becomes "unavoidable" at the config layer rather than the social layer. This flips
   fail-open's polarity: the gateway failing still passes traffic (its proxy layer fails
   open), but a client pointing elsewhere fails closed (no key). Strongest form of the
   forcing function; the open question is key-handling complexity across runner harnesses.
4. **Boot-time canary** (cheap, partial): the runner's first act after bind is a one-token
   canary call; if the gateway doesn't see a canary from a seat whose lock just appeared,
   that is UNSENSED rendered within one boot cycle. Doesn't cover mid-session base_url
   changes; (2) does.

My recommendation: (1)+(2) are v1-mandatory — they are the difference between the gateway
retiring the roster-that-lies class and re-instantiating it. (3) is the structural fix and
worth its own slice. (4) is garnish once (2) exists.

## One-line synthesis for the gate

The addendum's fail-open rule answers the SPOF question and leaves the harder one
unanswered: **a fail-open sensor cannot see its own bypass, so coverage — not traffic — is
the signal that must be rendered, cross-checked, and never self-reported.** Ship the tap as
substrate, its renders as projection, and `gateway_coverage` as a first-class column, or
the fleet's newest instrument is born with the roster's disease.
