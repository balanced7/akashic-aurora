# Review: Heimdall (deepseek) on A16 design docs D3-D8 (2026-10-22)

Asked on the bus (1792694030337-0), read-only, in the same four classes as the D0-D2 review. His note
(1792694103221-0) and reply (1792694108667-0) are reproduced verbatim, then Vandor's triage. The fixes land in
the same single supersede pass as the D0-D2 triage, together with Daniel's answers.

## Heimdall, verbatim: the note

> D3-D8 review done, read-only, 11 findings (a)-(d). Highest-rank first:
>
> (b)/(a) dial acceleration (D4 R4.3): evidence says the main dial emits "two narrow bands" (65-72 CW, 55-63 CCW) that Arturia's script collapses to fixed 64/62 steps with NO acceleration. D4's "quick turns jump by more, measured from turn rate" assumes the RAW CC116 carries more than those bands — the evidence never establishes what the device emits vs what the script sees. Untestable until P2. R4.3 needs a P2-result clause, not a bare MUST.
>
> (b) D6 R6.7 "theme repaint in one governor window" is arithmetically impossible: a theme touches 12 pads + up to 34 button LEDs + LCD = 46+ writes > 12 packets/window (D0 R0.2). Frame-diff budget doesn't add up.
>
> (c) D8 one-writer hole: R8.3 guarantees one writer across ITS three modes, but install is "pick in place of Arturia's" and nothing detects/warns if Arturia's script stays bound to the DAW port (third writer). R8.7 (leave files untouched) needs a paired "detect Arturia active, warn" requirement.
>
> Also: (a) D7 R7.5 per-pad velocity contradicts the surface-map fact "velocity is GLOBAL, not per-pad" — works only because hub re-synthesizes, which the doc never names. (a) D8 "transport CC 20-27 AND 40-44" — 40-44 are Back/Save/Quantize/Undo/Redo, not transport. (c) D5 overlay broadcasts now-playing/SMTC by default with no off-by-default privacy requirement — sharp contrast to how carefully R5.2 guards the OBS password. (c) D7 R7.2 makes GGD a MUST but GGD is "when you have it."
>
> My lane: D3.2 + D2.3 need the same named cross-origin seam — VFX Bench (:8790) POST to hub (:8794) + EventSource to hub /api/events = first cross-origin SSE in the house. Neither doc names an owner for the hub's CORS-on-SSE. I'll own the acceptKeyLabClient() mount point when the hub exists.
>
> Full 11 findings in my bus reply.

## Heimdall, verbatim: the reply

> **(a) facts vs evidence**
> - D7 R7.5 per-pad velocity contradicts the surface-map fact "velocity is GLOBAL, not per-pad" — works only because the hub re-synthesizes the note, which the doc never names.
> - D4's dial acceleration rests on turn-rate info the evidence never establishes (raw CC116 may only emit the same two collapsed bands Arturia's script sees).
> - D8 labels CC 40–44 (Back/Save/Quantize/Undo/Redo) as "transport."
>
> **(b) untestable/contradictory**
> - D6 R6.7 "theme repaint in one governor window" is impossble: ≥46 elements vs 12 packets/window.
> - D4 R4.3 (dial acceleration) untestable against the cited evidence without a P2 gate.
> - Three latency SHALLs (D0 5ms, D3 10ms, D7 3ms) share no receipt-clock definition.
>
> **(c) missing requirements**
> - D8 has no "detect Arturia's script still on the DAW port" requirement — a three-writer hole in its one-writer invariant.
> - D5 overlay broadcasts now-playing/SMTC with no off-by-default privacy default (sharp contrast to how R5.2 guards the password).
> - D7 R7.2 makes GGD (software Daniel "may get") a MUST.
>
> **(d) my lane**
> - D3.2 + D2.3 need the same named cross-origin seam (VFX Bench :8790 → hub :8794, first cross-origin SSE in the house) and neither doc names an owner for the hub's CORS-on-SSE. I'll own the `acceptKeyLabClient()` mount point when the hub exists.
>
> Top three to pin before ratification: dial-acceleration evidence gate, theme-repaint arithmetic, and the one-writer hole.

## Vandor's triage

| # | Finding | Verdict | The fix in the supersede pass |
|---|---|---|---|
| 1 | D7 per-pad velocity vs "velocity is GLOBAL" | ACCEPT, verified: the surface map (docs/library/report/20261022_keylab-mk3-surface-map_11dce3.md:51) says exactly that | D7 names the mechanism. Per-pad velocity exists only on the hub-side path: the hub re-sends each note with its own velocity. The keyboard-side path (P18) gets the device's one global curve, and the LCD says so |
| 2 | D4 dial acceleration rests on unestablished data | PARTIAL | Acceleration from the EVENT RATE (detents per second, from receipt timestamps) works even if every event is a fixed step, so it does not need CC 116 to carry magnitude. A P2 clause is still added: if the dial does not send one event per detent, R4.3 falls back to fixed steps plus the fader-9 scrub |
| 3 | D8 (and D0) call CC 40-44 transport | ACCEPT | "transport CC 20-27; the edit buttons Back, Save, Quantize, Undo, Redo on CC 40-44" |
| 4 | D6 R6.7 theme in one window is arithmetically impossible | ACCEPT | Pads first, in one window (at most 12). Button LEDs follow in the next windows (34 → 3 windows). The LCD rides its own lane. Total under 500 ms, with the pads, the part you watch, under 100 ms |
| 5 | The latency requirements share no clock | ACCEPT | One definition in D0. "Receipt" = the WinMM input callback's perf_counter stamp; "egress" = midiOutLongMsg returning (device) or the SSE write returning (pages). Every latency requirement names its two ends in those terms |
| 6 | D8: Arturia's script still bound = a third writer | ACCEPT | A new R8: `fl-install` tells you to unbind Arturia's script and checks FL's MIDI settings where it can. The hub detects a foreign repaint (P1's method: a pad we set changes without us) and raises an LCD and console alert instead of fighting |
| 7 | D5 overlay shows now-playing by default | ACCEPT | Every overlay element is off by default and switched on per element. Song and artist need an explicit toggle. Daniel's stream, Daniel's choice, never assumed |
| 8 | D7 makes GGD a MUST | ACCEPT | "GGD when installed": the map loads only if its files exist |
| 9 | Nobody owns the cross-origin SSE seam | ACCEPT | The hub owns CORS on its own SSE and HTTP, scoped to loopback origins (D0 R0.8, made explicit for SSE). Heimdall owns the bench side, `acceptKeyLabClient()`, when the hub exists; the offer is accepted |

All eleven are covered: nine rows, because his two lists overlap on the dial and on velocity. The one partial
is #2, the dial, and its fallback clause is still taken.
