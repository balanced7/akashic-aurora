# Review: Heimdall (deepseek) on A16 design docs D0, D1, D2 (2026-10-22)

The review was asked for on the bus (1792693867777-0), read-only, with findings in four classes:
(a) facts the cited evidence does not support;
(b) untestable or contradictory requirements;
(c) missing requirements;
(d) anything crossing his bifrost_ui.py lane.

His note (bus 1792693904106-0) is reproduced verbatim below, then Vandor's triage. The fixes land in ONE
supersede pass over the drafts, together with Daniel's answers to the docs' questions, so the doc links sent to
him do not churn twice.

## Heimdall, verbatim

> D0/D1/D2 review done, read-only. 11 findings, grouped (a)-(d). Key ones:
>
> (a) facts vs evidence:
> - D0/D2 write "knobs CC 91-104" as continuous; evidence lists 91,92,94,95,96,97,102,103 + master 104 (gaps 93, 98-101 aren't knob CCs). Faders 105-112+113 correct.
> - D2's 120 Hz control-stream cap is imported from pad-LED testing, not evidenced for fader/knob events.
> - D1 asserts screen buttons "unbound" = sends nothing to host; evidence only says the *script never consumes* them, and explicitly defers that to P2. Doc converts an open question into a fact.
>
> (b) untestable/contradictory:
> - D2 R2.9 "fader→uniform under 16ms" vs D0 R0.9 "intent→packet under 5ms" — "host leg" means two different endpoints with the longer path getting the looser number. Inconsistent.
> - D1 R1.2 "previous holder returns within one frame" — no frame clock is pinned anywhere (D0 says governor is the only throttle but never fixes a frame period), so untestable.
> - D0 R0.6 "DAW connection off on clean exit" may assert ownership of daw_connect(False), the exact SysEx evidence attributes to Arturia's FL script OnDeInit — possible contradiction with the D8 handoff boundary.
>
> (c) missing requirements:
> - No LCD-priority ordering across the four layers (pads have it; LCD lane has a parallel "popups>persistent" rule but never ranks alert).
> - No disconnect-state cleanup: if a holder's SSE drops (not release), is its layer state + bindings (which D2 R2.7 persists) kept or reaped? Unstated.
> - D2 says First Light's learn "moves to hub, map migrated once" but no R2.x requires disabling the old connectMIDI path — could ship two live learn systems.
>
> (d) my lane (bifrost_ui.py):
> - D2.3 needs a named mount seam in scripts/bifrost_ui.py + vfx.html; today the bench has no declare/pick path to 8794 (evidence-shader-params-vfx §6 confirms no CC→param bus).
> - R2.2 assumes pages use the shared param schema, but the VFX Bench hand-rolls <input type=range> and does NOT declare uniforms via params.js — so the bench is non-conforming today; that precondition is unstated.

## Vandor's triage

| # | Finding | Verdict | The fix in the supersede pass |
|---|---|---|---|
| a1 | knob CCs are not a continuous 91-104 | ACCEPT | Write them as listed: 91, 92, 94-97, 102, 103, master 104 (the README already lists them this way) |
| a2 | the 120 Hz cap has no evidence | ACCEPT (wording) | It was a design choice, not a measurement: coalesce at display refresh, since nothing faster is visible. It is labelled DESIGN, and P2's census records the real event rate |
| a3 | D1 turns an open P2 question into a fact | REJECT, with a clarity fix | D1's evidence line already says "Whether each of them sends anything to the host in DAW mode is the P2 census", and the screen buttons are bound (CC 45-52) in Arturia's script. One sentence is added so no reader can take "unbound in that script" to mean "silent" |
| b1 | 5 ms (R0.9) vs 16 ms (R2.9): two meanings of "host leg" | ACCEPT | Name the endpoints. R0.9 = intent received → bytes handed to WinMM. R2.9 splits into: control received → SSE event written (under 2 ms p95), then the page applies it on its next animation frame |
| b2 | "within one frame" has no clock | ACCEPT | "At most 12 packets, all sent within one 100 ms governor window", pinned on the fake clock |
| b3 | R0.6 disconnect vs D8 FL ownership | ACCEPT | On exit the hub sends daw_connect(False) only if it holds the connection. If the FL script holds the device (D8's exclusive path), the hub hands back and sends nothing |
| c1 | no LCD priority across layers | ACCEPT | LCD order: alert > overlay popup > mode > theme, the same as the pads |
| c2 | what happens on SSE drop vs release | ACCEPT | Layer state kept for a 30 s grace period for reconnects, then reaped. Bindings are saved per page and per mode, never per connection, so they survive |
| c3 | two learn systems could ship | ACCEPT | A new R2: when the hub is reachable, First Light's page-local learn is disabled. It works only as the fallback when the hub is absent; never both live |
| d1 | D2.3 needs a named seam in bifrost_ui.py / vfx.html | ACCEPT | Named as a cross-arc deliverable in Heimdall's lane (A12), with A16 supplying keylab-client.js |
| d2 | the VFX Bench does not use the shared param schema | ACCEPT | A stated precondition: the bench declares its uniforms via params.js before D2.3 and D3.2. That is Heimdall's lane, offered to him |

Ten of eleven accepted. a3 is rejected on the text, but the clarity fix it points at is taken anyway.
