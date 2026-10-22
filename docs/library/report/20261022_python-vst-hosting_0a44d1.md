---
akashic_id: art_20261022_python-vst-hosting_0a44d1
akashic_sha: 0eaa07aed561
schema_version: 1
status: current
type: report
arc: A16
date: 2026-10-22
title: python-vst-hosting
gist: "# Hosting VST3 from Python on Windows: Pedalboard for effects, Carla for live instruments > Provenance: Claude Code workflow `wu4q2dkoo`, ru"
visibility: fleet
body_type: markdown
seats: [claude]
category: [library, bus, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T09:30:02"
updated: "2026-10-22T14:21:32"
---
<!-- GENERATED PROJECTION of art_20261022_python-vst-hosting_0a44d1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# python-vst-hosting

# Hosting VST3 from Python on Windows: Pedalboard for effects, Carla for live instruments

> Provenance: Claude Code workflow `wu4q2dkoo`, run 2026-10-22 by claude (Vandor) for Daniel, reviewed by claude before filing.
> Raw per-lane results: `python-vst-hosting-2026-10-22.raw.json` in this folder. Status: research record, not a ruling.

# Hosting VST3s from Python on Windows — honest build plan

**Bottom line up front:** The vision splits cleanly into an **easy half that ships now in pure Python** (effects/EQ/reverb chains + popping plugin GUIs) and a **hard half that cannot be pure Python** (playing Kontakt live from the KeyLab at low latency). The hard half is absolutely buildable — but the realtime audio core must be native C++ (Carla's engine), with Python as the control/UI layer. Any claim of a pure-Python realtime VSTi host is a red flag: the GIL plus garbage-collection pauses cause dropouts at the small buffers live playing needs. The good news: `arsenal/keylab` is already 80% of the control layer.

---

## 1. THE EASY SLICE — effects chains (EQ / reverb) — SHIPPABLE NOW

**Library: `spotify/pedalboard`.** This is the right tool and it's trivial on Win + Py 3.11.

```
pip install pedalboard
```

Offline (process a rendered or recorded buffer):
```python
from pedalboard import Pedalboard, Reverb, HighpassFilter, LowShelfFilter, load_plugin
from pedalboard.io import AudioFile

board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=80),
    LowShelfFilter(cutoff_frequency_hz=200, gain_db=3, q=0.7),   # built-in EQ shaping
    load_plugin(r"C:\Program Files\Common Files\VST3\FabFilter Pro-Q 3.vst3"),  # or any VST3 EQ
    Reverb(room_size=0.5, wet_level=0.3),
])
with AudioFile("in.wav") as f:
    audio = f.read(f.frames); sr = f.samplerate
out = board(audio, sr)
```

Live (mic/interface → effects → speakers, realtime-safe because the DSP runs on JUCE's C++ thread, not a Python callback):
```python
from pedalboard.io import AudioStream
with AudioStream(input_device_name="...", output_device_name="...",
                 buffer_size=256) as stream:
    stream.plugins = board          # hot-swappable while streaming
    input("Streaming — Enter to stop...")
```

Supported, actively maintained (latest **v0.9.26**, tested Py 3.10–3.15, amd64 Windows wheels). Sources: pedalboard README https://github.com/spotify/pedalboard and io reference https://spotify.github.io/pedalboard/reference/pedalboard.io.html (as of 2026-10-22).

---

## 2. THE INSTRUMENT SLICE — live Kontakt with its GUI

**pedalboard CAN host Kontakt, but only OFFLINE.** Its instrument API hands the plugin a complete timestamped MIDI list and returns a fixed-duration buffer — a render-a-clip model, not a play-live model. Its realtime `AudioStream` is audio-in/audio-out **only and rejects instrument plugins** (open issue #307 is literally a user trying to host Kontakt and getting "only Plugin type is supported": https://github.com/spotify/pedalboard/issues/307). It also can't select ASIO on Windows (issue #384). So pedalboard is the wrong engine for live playing.

**The honest live engine: Carla (falkTX / KXStudio).** A true realtime host — VST2/VST3/AU/LV2 — that opens Kontakt's native GUI, runs ASIO on Windows for low latency, and ships a documented Python control API (`carla_backend.py`: `carla_standalone_host_init`, `carla_engine_init`, `carla_add_plugin`, `carla_set_parameter_value`, …). Python loads the plugin, builds the chain, and tweaks parameters; Carla's C++ engine runs the audio thread. That is exactly the "arsenal hosts a VST" shape.

The realtime pattern (non-negotiable law):
- **Audio callback = native C++** (Carla's engine). Never a Python function.
- **MIDI input = fine in Python.** `python-rtmidi`/`mido` (or your existing `winmidi.MidiIn`) read the keybed easily — MIDI is low-rate, sparse, and never touches the sample-accurate audio path.
- **GUI** pops via Carla; pedalboard's own `show_editor()` blocks the calling thread and can't be repositioned on Windows (issue #386), another reason not to lean on it for live.

Caveats to budget for: Carla ASIO on Windows needs ASIO4All (or a native ASIO interface) and has a known rough edge — intermittent startup distortion until you nudge the buffer size (issue #2081 https://github.com/falkTX/Carla/issues/2081). Use Carla's **own shipped `carla_backend`**, NOT the pip `pycarla` wrapper (JACK/Linux-first, Windows is an unfinished TODO: https://github.com/00sapo/pycarla). Carla Host API docs: https://kx.studio/ns/dev-docs/CarlaBackend/group__CarlaHostAPI.html (as of 2026-10-22).

**Skip DawDreamer** for this — it's offline-render-only (pre-loaded MIDI, `engine.render()`, blocking `open_editor()`); great for batch/ML bounces, useless for performance. **Skip RenderMan** (unmaintained VST2 ancestor).

---

## 3. LATENCY VERDICT

**Can it feel like a real instrument? Yes — through Carla+ASIO, not through Python.**

- Dedicated ASIO interface at 128–256 samples / 48 kHz ≈ **~3–12 ms** round-trip. Under ~10 ms feels immediate.
- ASIO4All over onboard audio ≈ **~15–24 ms** — playable, a careful player notices it.
- A DIY pure-Python loop (`python-rtmidi` → `instrument.process(reset=False)` per block → `sounddevice` out) is *technically* possible but **unsupported and glitch-prone**: pedalboard's own FAQ warns Python GC causes "random pops, clicks, or audio drop-outs" in live audio (https://spotify.github.io/pedalboard/faq.html). You'd oversize buffers to survive GC, pushing real latency well above the theoretical block size. Not product-grade.

For serious live use, **a native host (Carla, or a thin JUCE host) is the honest answer.** Python orchestrates; it must not sit in the callback. Never use WASAPI-shared or DirectSound for live.

---

## 4. THE INTEGRATION ANGLE — why this is the whole keyboard, not just-another-host

`arsenal/keylab` already IS the control layer; the VST host is one new audio sink behind it:

- **`winmidi.MidiIn`** already captures live notes + SysEx in a WinMM callback.
- **`chordview.py`** already reads the keys, names the chord on the LCD, lights the pads by role/quality, and has a `--sound` flag that **forwards notes to the Windows GM synth so you hear them**. Swapping that GM-synth sink for a **Carla-engine sink** is the entire product leap: you play, you hear Kontakt, and *simultaneously* the pads show chord tones and the LCD shows the chord name.
- **`beatsync.py`** already drives the pads from WASAPI loopback — so the same light bed can react to the sound Kontakt is producing.
- The pad/LED bus has a hard limit baked in (`PAD_GAP`, ~12-packet ceiling, documented freeze wall) — that lives on the control path and is unaffected by the audio engine.

So the differentiator isn't "a Python VST host" (Carla already exists). It's **the KeyLab becoming a self-teaching instrument**: Kontakt's real sound + live chord naming + theory-lit pads + beat-reactive lights, one surface, Python-glued. That's the product no plain host ships.

Architecture: `winmidi.MidiIn` (keys) → Python chord/theory + pad/LCD paint → fan the same MIDI to `carla_backend` → Carla engine (Kontakt + EQ/reverb chain, ASIO out). pedalboard stays for offline bounce/preset-audition and effect-chain design.

---

## 5. FIRST PROBE — the single cheapest test

**Don't write code first. Install Carla standalone, load Kontakt, set the driver to ASIO (ASIO4All if no interface), and play the KeyLab live — judge latency by feel and note the buffer size Carla reports.** One download, zero code, and it answers the make-or-break question directly: *does Kontakt-from-the-keybed feel immediate on this machine?*

- If **yes** → the live path is viable; next step is `carla_backend` from Python to load the plugin and fan `winmidi` MIDI into the engine, wiring it behind `chordview`.
- If **no / too laggy** → the honest call is to treat live playing as "use a real host/DAW" and keep the Python product scoped to the effects rack + offline render + the chord/pad/light intelligence.

A secondary 5-minute Python confirmation (`pip install pedalboard`, `load_plugin` the Kontakt .vst3, call `show_editor()`) proves the plugin loads and its GUI pops on this box — useful, but it does **not** test the live-latency question, so do the Carla probe first.

---

*Note for the record:* this is reusable fleet knowledge (pedalboard = offline+effects; Carla = the live engine; never Python in the audio callback). Worth a `learn:` entry if you want it persisted — I didn't write to shared memory from this workflow run to avoid a duplicate; say the word and it goes in.

Grounding files: `E:\AI-Setup\arsenal\keylab\chordview.py`, `E:\AI-Setup\arsenal\keylab\winmidi.py`, `E:\AI-Setup\arsenal\keylab\beatsync.py`, `E:\AI-Setup\arsenal\keylab\__main__.py`.
