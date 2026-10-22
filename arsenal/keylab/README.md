# arsenal.keylab — drive the Arturia KeyLab 88 mk3

Light the RGB pads, draw the colour LCD, name the chords you play, march the pads to whatever is playing, and
measure the device's real limits. No MIDI dependency: WinMM over ctypes, same idiom as `arsenal/midiports.py`.

```
py -m arsenal.keylab <verb> [args]      # every verb takes -h
```

## Before anything lights: put the keyboard in DAW mode
Press **Prog + the 6th screen button**, and set the pad mode to the middle option (**DAW**; left is Arturia
Program, right is Default). No SysEx can switch modes. Outside DAW mode the pads sit at their white default and
ignore colour commands. Close FL Studio first: its Arturia script writes the same pads and screen.

## Why / provenance
The protocol was read from **Arturia's own FL Studio script** (readable Python at
`…/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/`: KL3Dispatch, KL3Return, KL3Display, LedId,
ScreenId), cross-checked against the device JSON (`KeyLab3 88.json`, `protocol arturia_v4`), firmware strings,
and the MIT repo saxofonbrian/keylab-mk3-sysex. Every fact below was confirmed on the hardware on 2026-10-22.
`selftest` proves the wire format offline. Legal: Daniel's own hardware and files.

## Confirmed facts
Every row carries a dated receipt and its class: **eyes** = Daniel watched the device and said what he saw
(his words, from the 2026-10-22 session), **measured** = a tool measured it on this machine.

| Fact | Value | Receipt |
|---|---|---|
| Envelope | `F0 00 20 6B 7F 42 <payload> F7` | 2026-10-22, eyes: the first colours landed, "Keylab Unlocked!!!!!" |
| Pad / LED colour | `[0x00, eDaw=2, eSetLed=3, ledId, R, G, B, 0x00]`, R/G/B 0..127. **req byte 0x00**; 0x02 lights the pad white and ignores colour | 2026-10-22, eyes: with req 0x02, "The pads stayed white"; with 0x00 the colours rendered |
| Pads with live colour | the **DAW bank, ids 82-93** (pads 1-12), only in physical DAW mode | 2026-10-22, eyes: "we are in Daw mode (Middle) right now", then the pattern showed |
| Burst limit | ~36 packets in one tight burst **freezes the device** (power cycle). 12 is safe; every SysEx now passes `governor.BurstGovernor` (at most 12 per 100 ms, shared by every producer on the port), and `ledframe.PadRenderer` sends only pads that changed | 2026-10-22, eyes: after the flood, "main lcd was black no matter what buttons i pressed" until a power cycle. The 100 ms window is a conservative starting value; probe P24 re-measures it |
| Pad grid (printed labels) | 3 across x 4 down: `9 5 1 / 10 6 2 / 11 7 3 / 12 8 4` (`protocol.GRID`, the one copy) | 2026-10-22, eyes: Daniel's photo of the 12-colour test |
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
| `chordview [--scheme notes\|roles\|quality\|split\|frame] [--sound]` | play the keys: chord name on the LCD, chord tones lit on the pads, sustain pedal honoured; `--sound` forwards your notes to the Windows synth |
| `beat [--mode cycle\|rainbow\|march] [--engine a\|aubio] [--lead-ms 15]` | march the pads to whatever is playing (WASAPI loopback). The default engine is `beat_a`, the house tracker: it seeds the tempo from the song databases (SMTC now-playing) and paints each beat `--lead-ms` BEFORE it lands. `--engine aubio` is the old reactive path |
| `beatbench [--suite synthetic\|loops\|all] [--per-cat 30] [--seeded] [--trackers aubio,a,b]` | score beat trackers on one ruler: synthetic ground truth plus the BPM-labelled loops in your own packs (read in place); receipts in `state/arsenal/keylab/receipts/` |
| `ledbench rate [--sweep 5,10,20,40,80,120]` · `spacing` · `burst` | measure the LED limits; the rate sweep flashes N pads before level N |
| `bench` | host-to-driver send latency (mean/p50/p99) and sustained rate |
| `monitor` | print incoming MIDI (tap a pad, move a fader) |
| `probe [--only steps] [--list]` | the guided W0 hardware session: the LCD asks, you answer on the pads (1 yes, 2 no, 4 skip); receipts land in `state/arsenal/keylab/receipts/` |

Colours: a name (`red green blue cyan magenta yellow orange purple pink teal amber white off`), `#rrggbb`, or `r,g,b`.
Global: `--port SUBSTR`; `--dry-run` prints bytes and sends nothing; `--bank A|B|C|D|DAW`.

## Chord schemes (`chordview --scheme`)
`notes` (chord tones lit, root white) · `roles` (root white, major 3rd red, minor 3rd magenta, 5th blue,
7th green, 9th purple) ·
`quality` (the whole chord in its mood colour) · `split` (top row 9-5-1 is a quality bar, the rest show roles) ·
`frame` (the border glows the quality, notes light inside).

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

## Still open
- Can FL's Arturia script and this toolkit share the DAW port? Not yet tested with a receipt.
- Can our WinMM input and the piano page's Web MIDI hold "KeyLab 88 mk3 MIDI" at the same time? Untested.
- Which input port carries the faders and knobs in DAW mode, MIDI or DAW? (`monitor` on each answers it.)
- Full 7-bit colour depth versus snapping to the stored 42-colour palette.

## Files
`protocol.py` wire format + byte builders (pure, testable) · `winmidi.py` WinMM send + SysEx-capable input ·
`ledframe.py` the delta renderer · `governor.py` the burst ceiling as a guarantee (every SysEx passes it; the
`bench`/`ledbench` limit probes opt out) · `theory.py` chord naming · `chordview.py` live chord viewer, schemes
and `Voicing` (held keys + sustain) · `beatsync.py` loopback beat march + SMTC now-playing · `tempo.py` BPM seed
from the databases, pure analysis that never imports the port (Heimdall's lane) · `beat_a.py` the house beat
tracker (blind-pair winner) · `beat_b.py` the other blind contestant · `beatbench.py` the ruler both were judged
by · `probe.py` the guided hardware session · `__main__.py` the verbs.

Pins: `tests/test_keylab_w0.py` (sustain, grid, burst ceiling, colour wash zone) and
`tests/test_keylab_tempo*.py`. Licence: `beatsync` and `tempo` import aubio (GPLv3+) lazily, only when you run
them; it is never vendored or required. A house beat detector replaces it before anything is bundled.
