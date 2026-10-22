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
| Fact | Value |
|---|---|
| Envelope | `F0 00 20 6B 7F 42 <payload> F7` |
| Pad / LED colour | `[0x00, eDaw=2, eSetLed=3, ledId, R, G, B, 0x00]`, R/G/B 0..127. **req byte 0x00**; 0x02 lights the pad white and ignores colour |
| Pads with live colour | the **DAW bank, ids 82-93** (pads 1-12), only in physical DAW mode |
| Burst limit | ~36 packets in one tight burst **freezes the device** (power cycle). 12 is safe; every multi-pad verb paces itself (`PAD_GAP`), and `ledframe.PadRenderer` sends only pads that changed |
| Pad grid (printed labels) | 3 across x 4 down: `9 5 1 / 10 6 2 / 11 7 3 / 12 8 4` (`chordview.GRID`) |
| Colour rendering | saturated blues, purples, magentas, pinks and reds read clearly; warm low-saturation colours (amber, yellow, orange, lime) come out close to white |
| Screen | `[0x00, eDaw=2, eDisplay=4, screenId, tagged fields…]` from KL3Display.py. Popups (23/24/25) dismiss after ~1 s; full-screen two-line F2L (12) stays; a 60 ms colour cycle renders with no flicker |
| Ports | keys and controls arrive on **"KeyLab 88 mk3 MIDI"** (keys ch 1, pads ch 10); pads and screen go out on **"KeyLab 88 mk3 DAW"** |
| Timing | host timer ~1.5 ms, SysEx send ~0.3 ms (p99 0.65 ms); the uneven flicker at high rates is the device's own LED cadence |

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
| `beat [--mode cycle\|rainbow\|march]` | march the pads to whatever is playing (WASAPI loopback + aubio); prints the Spotify/SMTC now-playing title |
| `ledbench rate [--sweep 5,10,20,40,80,120]` · `spacing` · `burst` | measure the LED limits; the rate sweep flashes N pads before level N |
| `bench` | host-to-driver send latency (mean/p50/p99) and sustained rate |
| `monitor` | print incoming MIDI (tap a pad, move a fader) |

Colours: a name (`red green blue cyan magenta yellow orange purple pink teal amber white off`), `#rrggbb`, or `r,g,b`.
Global: `--port SUBSTR`; `--dry-run` prints bytes and sends nothing; `--bank A|B|C|D|DAW`.

## Chord schemes (`chordview --scheme`)
`notes` (chord tones lit, root white) · `roles` (root white, 3rd gold, 5th blue, 7th green, 9th purple) ·
`quality` (the whole chord in its mood colour) · `split` (top row 9-5-1 is a quality bar, the rest show roles) ·
`frame` (the border glows the quality, notes light inside).

## Still open
- Can FL's Arturia script and this toolkit share the DAW port? Not yet tested with a receipt.
- Full 7-bit colour depth versus snapping to the stored 42-colour palette.
- The DAW-mode control map (fader/encoder CC numbers, relative vs absolute encoders).
- The rest of the screen vocabulary (knob, fader, pad, icon layouts in KL3Display.py).

## Files
`protocol.py` wire format + byte builders (pure, testable) · `winmidi.py` WinMM send + SysEx-capable input ·
`ledframe.py` the delta renderer · `theory.py` chord naming · `chordview.py` live chord viewer + schemes ·
`beatsync.py` loopback beat engine + SMTC now-playing · `__main__.py` the verbs.
