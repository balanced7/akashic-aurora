# arsenal.keylab — drive the Arturia KeyLab 88 mk3

Light the RGB pads, draw the colour LCD, name the chords you play, march the pads to whatever is playing, and
measure the device's real limits. No MIDI dependency: WinMM over ctypes, same idiom as `arsenal/midiports.py`.

```
py -m arsenal.keylab <verb> [args]      # every verb takes -h
```

## Before anything lights: put the keyboard in DAW mode
Press **Prog + the 6th screen button**, and set the pad mode to the middle option (**DAW**; left is Arturia
Program, right is Default). No SysEx can switch modes. Outside DAW mode the pads sit at their white default and
ignore colour commands. Close FL Studio first, or switch its KeyLab DAW input to our own script (`fl-install`, below):
Arturia's script writes the same pads and screen.

## Why / provenance
The protocol was read from **Arturia's own FL Studio script** (readable Python at
`…/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/`: KL3Dispatch, KL3Return, KL3Display, LedId,
ScreenId), cross-checked against the device JSON (`KeyLab3 88.json`, `protocol arturia_v4`), firmware strings,
and the MIT repo saxofonbrian/keylab-mk3-sysex. Every fact below was confirmed on the hardware on 2026-10-22.
`selftest` proves the wire format offline. Legal: Daniel's own hardware and files.

## Confirmed facts
Every row carries a dated receipt and its class: **eyes** = Daniel watched the device and said what he saw
(his words, from the 2026-10-22 session unless a row says otherwise), **measured** = a tool measured it on this machine.

| Fact | Value | Receipt |
|---|---|---|
| Envelope | `F0 00 20 6B 7F 42 <payload> F7` | 2026-10-22, eyes: the first colours landed, "Keylab Unlocked!!!!!" |
| Pad / LED colour | `[0x00, eDaw=2, eSetLed=3, ledId, R, G, B, 0x00]`, R/G/B 0..127. **req byte 0x00**; 0x02 lights the pad white and ignores colour | 2026-10-22, eyes: with req 0x02, "The pads stayed white"; with 0x00 the colours rendered |
| Pads with live colour | the **DAW bank, ids 82-93** (pads 1-12), only in physical DAW mode | 2026-10-22, eyes: "we are in Daw mode (Middle) right now", then the pattern showed |
| Burst limit | ~36 packets in one tight burst **freezes the device** (power cycle). 12 is safe; every SysEx now passes `governor.BurstGovernor` (at most 12 per 100 ms, shared by every producer on the port), and `ledframe.PadRenderer` sends only pads that changed | 2026-10-22, eyes: after the flood, "main lcd was black no matter what buttons i pressed" until a power cycle. The 100 ms window is a conservative starting value; probe P24 re-measures it |
| Pad grid | 4 across x 3 down, numbered in reading order: `1 2 3 4 / 5 6 7 8 / 9 10 11 12`, the top row farthest from the player (`protocol.GRID`, the one copy; it agrees with the MPC note rows, the bottom-left pad 9 = note 36) | 2026-10-23, eyes: Daniel at the device, "your pad representation shows pad 1 on the right when its actually the top left most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is 9-12". It supersedes the 2026-10-22 reading of his photo of the 12-colour test (`9 5 1 / 10 6 2 / 11 7 3 / 12 8 4`, 3 across x 4 down), which was the same grid turned 90 degrees; erratum: `research/reviewed/keylab-liberation-2026-10-22/erratum-pad-grid-2026-10-23.md` |
| Colour rendering | saturated blues, purples, magentas, pinks and reds read clearly; warm low-saturation colours (amber, yellow, orange, lime) come out close to white | 2026-10-22, eyes: the same photo. The gamut probe (A16 W0 d) replaces this rule of thumb with a measured table |
| Screen | `[0x00, eDaw=2, eDisplay=4, screenId, tagged fields…]` from KL3Display.py. Popups (23/24/25) dismiss after ~1 s; full-screen two-line F2L (12) stays; a 60 ms colour cycle renders with no flicker | 2026-10-22, eyes: "Hello Daniel flashed for 1 second"; on F2L, "beautifully, flawlessly rendered, 0 ficker!" |
| Ports | keys and controls arrive on **"KeyLab 88 mk3 MIDI"** (keys ch 1, pads ch 10); pads and screen go out on **"KeyLab 88 mk3 DAW"** | 2026-10-22, measured: `ports`; eyes: chordview named his chords, "the pads changed color and shaper per chord too!!!" |
| Timing | host timer ~1.5 ms, SysEx send ~0.3 ms (p99 0.65 ms); the uneven flicker at high rates is the device's own LED cadence | 2026-10-22, measured: `bench` and a timer probe; eyes: the fast rate "looked uneven" |

## Verbs
| verb | does |
|---|---|
| `ports` | list MIDI ports (+ Windows MIDI service); marks the KeyLab |
| `selftest` | prove the wire format offline, no keyboard needed |
| `connect` / `disconnect` | arm / drop DAW-integration mode (disconnect hands the screen back) |
| `led <A1..D12\|button\|id> <colour>` | light one LED |
| `pad <1..12> <colour>` · `all <colour>` · `off` | pads (default bank DAW) |
| `rainbow` · `show` | hue sweep; the full light show (flashes, rainbow wave, chord bloom) |
| `chord <spec> [--play]` | light a chord's pads (`Cmaj7`, `F#m`, `C E G`, `60 64 67`) |
| `note <n> [--pad N]` | send a Note On/Off |
| `display <text> [--line2 … --full]` | write the LCD: one-line popup, two-line popup, or persistent full screen |
| `screen <text> [--line2 …] [--layout full\|inverted\|big\|line\|popup\|title\|icon]` · `screen --labels "a,b,…"` | write the screen in **guest mode** (never the DAW connect: FL keeps the KeyLab), every byte built exactly as Arturia's FL script builds it; `--labels` names the 8 screen buttons. Receipt in `state/arsenal/keylab/receipts/screen-*.json` |
| `screen --live [--scene NAME] [--pulse] [--source vj\|keys] [--reassert S]` | keep **chord, roman numeral, key, BPM and the VJ scene** on the screen, from the VJ engine's feed (`127.0.0.1:8794/api/events`) or straight from the keys. Line 1, the only line the firmware leaves in its own case, carries the chord with its numeral and key (`Gbmaj7  IVmaj7  in Db`; `(song)` after a chord heard in the audio; past 32 characters `(song)` and then the key give way, never the chord or numeral), line 2 `150 BPM \| SCENE`; numeral and key need `vj --chords sense`; an audio no-chord shows `--`; redraws only on change, at most every 100 ms; `--pulse` adds a beat marker drawn on the beat |
| `chordview [--scheme notes\|roles\|quality\|split\|frame] [--sound]` | play the keys: chord name on the LCD, chord tones lit on the pads, sustain pedal honoured; `--sound` forwards your notes to the Windows synth |
| `chords [file] [--live] [--notes FILE --bpm 100] [--json]` | hear the harmony (`chordsense`): chord with its inversion, key, roman numeral and function, tension 0..1, pedal and resolution events, from a recording, from whatever is playing (`--live`, loopback, read-only) or from a score through the keys path; `--json` streams one event per line for a renderer |
| `beat [--mode cycle\|rainbow\|march] [--engine a\|g\|...\|aubio] [--lead-ms 15]` | march the pads to whatever is playing (WASAPI loopback). The default engine is `beat_a`, the house tracker: it seeds the tempo from the song databases (SMTC now-playing) and paints each beat `--lead-ms` BEFORE it lands. `--engine w` / `--engine g` are opt-in live trials of the grid trackers (they hold half-time bass music on the bench; not shipped, see below); any `beat_<name>.py` contestant works the same way. `--engine aubio` is the old reactive path |
| `beatbench [--suite synthetic\|loops\|all\|drift\|shift\|bright\|bright_variants\|real] [--per-cat 30] [--seeded] [--trackers aubio,a,g] [--vs a]` | score beat trackers on one ruler: synthetic ground truth plus the BPM-labelled loops in your own packs (read in place); receipts (with every argument and each case's file + sha1) in `state/arsenal/keylab/receipts/`. Only the trackers named are imported. `--vs` pairs every tracker with the reference loop by loop (per group and pooled; a cluster bootstrap by pack folder). Held-out sets: `--exclude-seeds 7,11` (with `--per-cat`) drops those draws' loops by CONTENT; `--write-manifest PATH` / `--manifest PATH` freeze a draw and re-score exactly it; `--suite bright_variants --variant-seed N` draws unseen bright basses; `--suite real --since YYYYMMDD-HHMMSS` scores only later recordings |
| `record [--secs 90]` · `annotate [path] [--bpm X]` · `confirm [path] [--tapkey]` · `tapkey [path]` | real-song ground truth: capture what plays (with a timing record; a capture gap is refused), fit a grid that lists its rival tempi (`--bpm` forces one exactly), listen to the CLICKS render, confirm it (refused if the grid changed since the render). `tapkey` turns the taps of a `beat --save --hand` session into an answer key |
| `ledbench rate [--sweep 5,10,20,40,80,120]` · `spacing` · `burst` | measure the LED limits; the rate sweep flashes N pads before level N |
| `bench` | host-to-driver send latency (mean/p50/p99) and sustained rate |
| `monitor` | print incoming MIDI (tap a pad, move a fader) |
| `probe [--only steps] [--list]` | the guided W0 hardware session: the LCD asks, you answer on the pads (1 yes, 2 no, 4 skip); receipts land in `state/arsenal/keylab/receipts/` |
| `fl-install [--dry-run] [--hardware-dir D]` · `fl-uninstall [--dry-run]` · `fl-status` | our own FL Studio script for the DAW port (below): copy `fl/device_AuroraKeyLab.py` into FL's `Settings/Hardware/Aurora KeyLab/` (refused if that folder holds anything not ours; no other folder is ever opened, Arturia's included), remove it (only our files, then the empty folder), or check it (installed? same bytes as the repo? FL running? which script FL saved for the KeyLab DAW input, read-only from the registry) |
| `vj [--port 8794] [--engine a] [--chords sense\|basic] [--no-leds] [--replay-midi FILE] [--replay-audio FILE\|demo] [--loop] [--rate-limit]` | the VJ engine (`vj.py`): keys, pedal, pads (DAW mode or the normal bank; with FL's script running, DAW-mode pads 1-8 also toggle FL's step sequencer, so use the bank), every CC (learned on touch: absolute or relative around 64), the beat announced ~250 ms ahead, energy bands, heavy hits and chords from the keys AND from the audio, served as Server-Sent Events on `127.0.0.1:8794/api/events` (`/api/state`; `POST /api/pads` lights the DAW-bank pads, guest mode: 409 when `--no-leds`, 503 when no KeyLab DAW output is found, and the stream's `hello` says `leds: false` either way so the page does not post). `--replay-midi` plays a JSON note list or an FL project's newest score-log pattern (read-only) as if live (a file with no tempo plays at an assumed 100 BPM and says so; `--replay-bpm` sets it); `--replay-audio demo` is a made-up groove for trying a page with no music, `--replay-audio FILE --loop` repeats a file. **`--chords sense`** (the default) runs chordsense on both ears: every loopback block (chords with `roman`, `key`, `bass`, `conf`; a `key` event when the key lands or moves; a `tension` event with every chord, pedal and resolution) and the keys (the chord NAME stays the exact keys reading, ~45 ms after the attack; chordsense names what that reading cannot, such as a chord under a foreign held pedal note, and gives the key, the numerals and the tension; the page is told the keys' key while they have been played in the last 10 s, else the audio's). `--chords basic` keeps the older audio templates and sends no key or tension. `hello` says which runs (`chords`). `/api/state` carries the capture timing record and the per-block cost: on a real-time hardstyle replay 2400 of 2400 blocks read, gap +0.6 ms, 0.87 ms a block (p99 2.8 ms, chordsense 0.28 ms, p99 0.88) against a 10.7 ms block |

Colours: a name (`red green blue cyan magenta yellow orange purple pink teal amber white off`), `#rrggbb`, or `r,g,b`.
Global: `--port SUBSTR`; `--dry-run` prints bytes and sends nothing; `--bank A|B|C|D|DAW`.

## Chord schemes (`chordview --scheme`)
`notes` (chord tones lit, root white) · `roles` (root white, major 3rd red, minor 3rd magenta, 5th blue,
7th green, 9th purple) ·
`quality` (the whole chord in its mood colour) · `split` (the top row, pads 1-4, is a quality bar, the rest show roles) ·
`frame` (the border glows the quality, notes light inside).

## Hearing the harmony (`chordsense.py`)
Daniel, 2026-10-23: "realtime audio chord analysis could really help us match beat events to rythm and flow".
`ChordSense(rate, hop).feed(block)` listens to audio and `feed_notes(events)` to the keys; both run one theory
(11 chord qualities plus slash chords, a Krumhansl-Kessler key, roman numerals such as V7, bVII and V/V, and a
tension from function, dissonance and a pedal detector), emit events only when something changes, and
`snapshot()` gives a renderer the continuous state (tension, chroma, sounding notes, bass, a harmonic `pulse`).
The audio front end splits harmonic from percussive with a causal median, so drums read as no chord ('N').
Measured on the synthetic set (48 random progressions, 384 chords over all 12 roots and 11 qualities, random
voicings, a third of the triads inverted, the beatbench drums on top): the full label (root, quality and bass)
is right 96.6% of the time once settled, the root 99.2%, with 0.02 stray events per chord (a thinner reading of
the chord being held, Am7 to Am in an arpeggio, must last a second before it is named). A change is decided
about 0.5 s after it happens and its `t_change` back-dates it to the attack (median error 9 ms, p90 40 ms), the
time to line up with beats. About 75x real time at 48 kHz / hop 512 on one core; numpy and scipy only, under
the same licence firewall as the beat trackers. Daniel's Joy to the World (his FL score log) reads Db major,
and the closing passage, a D-flat struck 95 times over a walking bass, reads as a Db pedal whose tension sits
above the opening (0.56 against 0.47 from the notes, 0.60 against 0.49 from an additive audio render). Not yet
done: no real recording has been scored against a chord answer key (there is none on this machine; on three
loopback recordings it names about 44 root changes a minute, unchecked), the decision latency is about half a
second, the key misreads Joy's free intro for its first ~50 beats, and 9th/11th/13th, dim7, m7b5 and 6 chords
fall outside the vocabulary (they read as the nearest of the 11).

## Read from Arturia's script, not yet confirmed on the hardware
Facts only (numbers and ids); the full map with sources is
`research/reviewed/keylab-liberation-2026-10-22/evidence-control-map-2026-10-22.md`.
- Faders 1-9: CC 105-113, absolute; each has a capacitive touch CC (28-31, 33-37). Knobs 1-9: CC 91, 92, 94-97,
  102-104, relative around 64; touch CC 8-15 and 38. Main dial: turn CC 116 (relative), click CC 117.
- Transport CC 20-27 and 40-44; the eight screen buttons CC 45-52. Controls are on channel 1, pads on channel 10.
- Arturia's FL script never uses Shift, and Bank/Settings/MIDI/Transpose/Octave are unbound in it: candidates
  for the mode-pin combo.
- Every button LED takes full RGB through the same SetLed message as the pads.
- Screen ids 28/29/30 draw a knob, fader or pad graphic with a live 0-127 bar. The enum also names list screens
  (20-22), a colour picker (39) and a browser (40) that Arturia's script never draws: whether the firmware renders
  them is a probe.

## Our FL script (`fl/device_AuroraKeyLab.py`, design D8, slice v0 "Aurora drives")
Daniel, 2026-10-22: "Lets let the play pause controls work with FL but the fades for mixer is dumb, i want them
unassociated so I can link them to whatever by default." Picked in FL as the Controller type of the "KeyLab 88 mk3
DAW" input in place of Arturia's "KeyLab mk3" (the MIDI input keeps its own script). On the DAW port it:
- sends the DAW connect on load and the disconnect on unload (the same bytes as `protocol.daw_connect`);
- drives FL's transport from the transport buttons: Stop 20 (press), Play 21, Record 22, Loop 24 (loop recording) and
  Metronome 27 (release), Tap 23, Save 41, Undo 43, Redo 44 (press), Rewind 25 / Fast forward 26 (while held);
- swallows everything else (`handled`, no FL call): faders, knobs, touch sensors, dial, Back 40, Quantize 42, screen
  buttons, DAW-bank pads. Our programs read the same messages from the shared input (P1 above);
- lets the pitch and mod wheels through to FL untouched, if they ever arrive on that port;
- never writes the screen or a pad; it lights only the Play / Record / Loop / Metronome LEDs, on change, at most 11
  per 100 ms of its own (the handshake keeps the 12th slot).
Twelve FL functions in all, listed at the top of the script for the P23 freeze drill; eleven of them are ones
Arturia's script already calls on this machine, `transport.isPlaying` is the new one. Install, the switch back (one
dropdown) and the first-run drill: `fl/INSTALL.md`. Pins: `tests/test_keylab_fl_script.py` (every transport edge,
a sweep of every other message, the LED burst rule, the import and FL-call allowlists, the licence check against
Arturia's files, install / uninstall against a temporary Hardware folder). Not in v0: the heartbeat handoff (FL
drives when the hub is gone), the Aurora Link port, the pad remap and PERFORM mode.

## Answered by probe
- **P1, FL and this toolkit on one DAW port: they SHARE.** Dated 2026-10-22 21:45, from Daniel's eyes. FL Studio
  was open with Arturia's script connected (the LCD showed "*Addictive Drums") and the Windows MIDI Service
  running. `pad 5 green --no-connect` opened the port without an error, and pad 5 "is green and staying green".
  Run alongside FL in guest mode (`beat --no-connect`): FL keeps the connection and the screen, and we only paint
  the pads. Not yet tested: whether FL repaints pads during transport, when its step-sequencer view drives pads 1-8.

## The screen, live (`screen.py`)
The screen is a layout engine: the computer picks a firmware layout and fills in text, per-line colour, a 0-127 bar,
an icon number or button labels (no raw pixels). `screen.py` builds every layout exactly as Arturia's FL script does
(`KL3Display.py`, `KL3Buttons.py`; `tests/test_keylab_screen.py` runs Arturia's own classes against stub FL modules
and compares every byte). Facts from that script worth knowing:
- Frame: `F0 00 20 6B 7F 42 00 02 04 <screen id> <fields> F7`, each field `[tag] value 00`. Colours are 0-127 per
  channel (FL halves its 8-bit colours). Colour type 1 = use the RGB that follows.
- Lines: ASCII only, or the **whole** line becomes ".Undefined text."; over 32 characters becomes the first 28 +
  "..."; **line 2 and line 3 are upper-cased**. So the live readout keeps the chord on line 1 ("Am" stays "Am").
- Screen buttons: label slot = screen id - 1; slots 0-3 sit on buttons 5-8, slots 4-7 on buttons 1-4.
- Never sent: 38 (boot), 43 (pedal calibration), 44 (bootloader). The writer refuses them and anything that is not
  a screen frame, so it can never send the DAW connect or an LED.

**Sharing the screen with FL Studio.** FL's script repaints its own screen and all eight button labels whenever FL
refreshes for anything but plain mixer / control-value changes (a window focus change, a selection, transport start
or stop, a rename or recolour), repaints a popup on every idle tick while Rewind / Fast-forward is held, and draws
knob and fader popups when a control moves. `screen --live` redraws only when its own text changes, so after an FL
repaint FL's screen stays until the next chord, BPM or scene change; `--reassert 3` wins it back every 3 s. The clean
answers: FL closed (then `screen --live --connect`, refused while FL runs) or our own FL script with a VJ hand-off
mode (design D8). When FL closes, its script sends the DAW disconnect; whether the screen still draws our frames
without the connect is not yet known (first test below).

**Awaiting Daniel's eyes.** 2026-10-23 01:26, one guest-mode frame (screen 12, "Aurora" / "NIGHT SHIFT") went to
"KeyLab 88 mk3 DAW" without an error, with FL Studio **not running** (receipt
`state/arsenal/keylab/receipts/screen-20261023-012612.json`). Nobody could look at the screen.

## Still open
- Does the screen draw a frame without the DAW connect when FL is closed? (The 01:26 test asks; see above.)
- Can our WinMM input and the piano page's Web MIDI hold "KeyLab 88 mk3 MIDI" at the same time? Untested.
- Which input port carries the faders and knobs in DAW mode, MIDI or DAW? (`monitor` on each answers it.)
- Full 7-bit colour depth versus snapping to the stored 42-colour palette.

## Files
`protocol.py` wire format + byte builders (pure, testable) · `winmidi.py` WinMM send + SysEx-capable input ·
`ledframe.py` the delta renderer · `governor.py` the burst ceiling as a guarantee (every SysEx passes it; the
`bench`/`ledbench` limit probes opt out) · `theory.py` chord naming · `chordview.py` live chord viewer, schemes
and `Voicing` (held keys + sustain) · `beatsync.py` loopback beat march + SMTC now-playing · `tempo.py` BPM seed
from the databases, pure analysis that never imports the port (Heimdall's lane) · `beat_a.py` the house beat
tracker (blind-pair winner) · `beat_b.py` the other blind contestant · `beat_g.py` / `beat_h.py` / `beat_w.py`
the grid-tracker contestants (Daniel's "detect the grid", 2026-10-22; scored in
`research/reviewed/keylab-liberation-2026-10-22/grid-tracker-scoring-2026-10-22.md`) · `beatbench.py` the ruler
they are all judged by · `chordsense.py` chords, key, numerals, tension and pedal from audio or notes (pure
analysis, never imports the port) · `probe.py` the guided hardware session · `screen.py` the screen encoder
(identical to Arturia's script), the guest-mode writer and the live chord / numeral / key / BPM / scene readout ·
`vj.py` the VJ engine (KeyLab + loopback -> beat / energy / chord / key / tension / pad events on :8794; chordsense
on both ears) · `fl/device_AuroraKeyLab.py` our FL Studio script (transport only) and `fl/INSTALL.md` ·
`flscript.py` its install / uninstall / status · `__main__.py` the verbs.

Pins: `tests/test_keylab_w0.py` (sustain, grid, burst ceiling, colour wash zone), `tests/test_keylab_screen.py`
(the screen bytes, the never-send refusals, pacing, the live readout against a fake engine),
`tests/test_keylab_chordsense.py` (the eight chords under drums, no flicker, Db numerals, the pedal, the speed, Joy
to the World), `tests/test_keylab_vj.py` (the contract; chordsense in the engine on a synthesized hardstyle replay, `--chords basic`, the real-time capture record, the keys' names and numerals) and `tests/test_keylab_tempo*.py`; the page: `tests/vj_core.test.mjs` and `node arsenal/lanes/vj_verify.mjs` (headless SwiftShader, a fake engine and the real one on test-band ports). Licence: `beatsync` and `tempo` import
aubio (GPLv3+) lazily, only when you run them; it is never vendored or required. A house beat detector replaces it
before anything is bundled.
