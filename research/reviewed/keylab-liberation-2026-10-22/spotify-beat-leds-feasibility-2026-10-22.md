# Spotify now-playing + realtime beat for the pads (SMTC, WASAPI loopback, aubio-ledfx; Spotify BPM API dead)

> Provenance: Claude Code workflow `wu22yrs27`, run 2026-10-22 by claude (Vandor) for Daniel, reviewed by claude before filing.
> Raw per-lane results: `spotify-beat-leds-feasibility-2026-10-22.raw.json` in this folder. Status: research record, not a ruling.

Build plan synthesized below from the verified findings (all confirmed current as of 2026-10-22) and grounded against our existing `arsenal/keylab` toolkit.

---

# Beat-marching pads → chord DB: build plan for Daniel + Vandor

**The one-sentence reality:** Spotify gives you *what's playing and where in the track*, but as of 2024-11-27 it gives a new app **zero** tempo/beat/key data (audio-features & audio-analysis return 403, no replacement 18 months on). So the LED march **cannot** come from Spotify — the beat must be computed locally from captured audio. Good news: every piece needed installs cleanly on Python 3.11 Windows from prebuilt wheels, and our `arsenal/keylab` SysEx toolkit already lights the pads.

---

## 1. NOW-PLAYING + POSITION — recommended path: Windows SMTC (no OAuth)

Read the Spotify **desktop** app's metadata and playback position straight from Windows' System Media Transport Controls. No Spotify account tier, no OAuth, no token refresh.

- **Package:** `winrt-Windows.Media.Control` v3.2.1 (2025-06-06), the modern pywinrt namespaced package — prebuilt cp311 win_amd64 wheels, no compiler. (https://pypi.org/pypi/winrt-Windows.Media.Control/json)
- **Reject:** the old monolithic `winsdk` (frozen 2023, legacy) and the bare `winrt` package (abandoned 2021, Py3.7–3.9 only).
- **API:** `MediaManager.request_async()` → enumerate `get_sessions()`, filter `session.source_app_user_model_id == 'Spotify.exe'` → `try_get_media_properties_async()` for title/artist/album, `get_playback_info().playback_status` for play/pause, `get_timeline_properties()` for `.position` / `.end_time`.
- **Critical behavior:** `position` is a **snapshot** valid only as of `.last_updated_time` (UTC). It does **not** tick on its own. For a smooth progress animation, poll ~1–5 s and extrapolate every frame: `live_pos = position + (now_utc − last_updated_time)` while status == PLAYING; re-sync on `add_timeline_properties_changed`/`add_playback_info_changed` for seeks and pauses. Import namespace is `winrt` (`from winrt.windows.media.control import ...`).

**When to fall back to the Spotify Web API instead:** only if you need the Spotify *web* player (which routes through the browser's SMTC session, not `Spotify.exe`) or metadata when the desktop app isn't the SMTC source. That path needs OAuth Authorization-Code-with-PKCE, a **Premium** app owner, and self-allowlisting (dev mode caps at 5 users in 2026); `GET /me/player/currently-playing` + `progress_ms`/`timestamp`/`duration_ms` still work (https://developer.spotify.com/documentation/web-api/references/changes/february-2026). `spotipy` 2.26.0 (2026-03-03, pure-Python, clean 3.11 install) wraps it. **Default to SMTC** — it's strictly simpler for the solo-desktop case.

---

## 2. BPM / BEAT — recommended path: WASAPI loopback + realtime beat tracker

Since Spotify's beat grid is gone, capture the PC's audio output and run a causal beat tracker on it.

- **Capture:** `PyAudioWPatch` 0.2.12.9 (2026-10-06) — low-latency WASAPI loopback, prebuilt cp311 wheels, `get_default_wasapi_loopback()`. (https://pypi.org/project/PyAudioWPatch/) Alternative block-pull API: `soundcard` 0.4.6 (2026-04-12, pure-Python + cffi). **Not** vanilla `sounddevice`/`pyaudio` — neither does loopback on Windows without a virtual cable.
- **Beat tracker:** `aubio-ledfx` 0.4.12 (2026-10-03) — the LedFx team's maintained aubio fork, prebuilt cp311–3.15 Windows wheels, still imported as `aubio` with the `aubio.tempo` API. (https://pypi.org/project/aubio-ledfx/)
  - **Reject** classic `pip install aubio` — abandoned at 0.4.9 (2019), source-only, no wheels, build-painful on 3.11.
  - **Reject for realtime** madmom (last release 2017, needs old-numpy + Cython + MSVC) and BeatNet (pulls madmom). librosa/`beat_this` are offline/whole-file — use them in the chord phase, not the live loop.

**One-line install:** `py -m pip install PyAudioWPatch aubio-ledfx`

**Realtime loop (standard causal usage):**
```python
tempo = aubio.tempo('default', buf_size, hop_size, samplerate)  # samplerate = 48000!
# each captured block (downmixed to mono):
if tempo(samples):
    fire_pad(); bpm = tempo.get_bpm()
```

---

## 3. PIP INSTALL LIST (we already have librosa/numpy/scipy/requests)

```
py -m pip install "winrt-Windows.Media.Control[all]" PyAudioWPatch aubio-ledfx
```
Optional / later:
- `soundcard` — alternative to PyAudioWPatch if loopback misbehaves.
- `vamphost` — the chord-phase host (section 5); has cp311 win_amd64 wheels.
- `spotipy` — only if you take the Web-API fallback in section 1.

**No MIDI dependency needed** for the LEDs: our `arsenal/keylab` already does SysEx over WinMM via ctypes (no python-rtmidi/mido).

---

## 4. HONEST GOTCHAS

- **Beat-synced LEDs cannot come from Spotify, full stop.** audio-features/audio-analysis died 2024-11-27, return 403 for new apps, no replacement, no waitlist (https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api). "March to the beat" is the *harder* half; SMTC is the easy half.
- **Loopback captures ALL system audio** — Discord pings, notification dings, a second tab all land in the beat tracker. Expect the lock to wobble when other apps make noise.
- **Samplerate trap:** WASAPI loopback is typically 48000 Hz / 2-ch / float32 shared-mix. You MUST downmix to mono and pass **48000** (not 44100) to `aubio.tempo`, or the BPM is wrong.
- **Realtime lock latency:** ~30–80 ms per beat flag, **a few seconds to lock a stable BPM**, and aubio routinely reports **half/double BPM** — add octave-correction/smoothing if the pads must stay on the right subdivision. (The latency numbers are a reasoned estimate, not a hard benchmark — measure on the rig.)
- **Silence handling:** loopback yields silent/no-data frames when nothing plays — guard the loop so it doesn't stall or lock onto noise.
- **SMTC position is a snapshot** (section 1) — extrapolate or the progress bar jumps.
- **Install audit noise (benign):** winrt-runtime/Media.Control show a "files added late" PyPI notice (3.14 wheels uploaded 2025-09-20) — maintainer adding 3.14 support, not a compromise.
- **aubio-ledfx caveat:** clean install + standard `aubio.tempo` are confirmed; its PyPI page does **not** document the "reduced-latency/multi-octave" improvements some sources attribute to it — treat those as unverified.

---

## 5. CHORD PHASE — realistic path to a time-synced chord DB

**Architecture: analyze once, replay in sync.** Do NOT run a chord model on short live buffers (inaccurate, high latency). Instead:

1. **Offline per track:** capture or load the audio, run **Chordino (NNLS-Chroma)** to get `(start, end, chord)` labels. Host: `vamphost` (cp311 win_amd64 wheels, latest 1.4.0 2026-10-07 — https://pypi.org/pypi/vamphost/json). **Caveat:** pip gives you the *engine only* — you must separately drop the Chordino/NNLS-Chroma plugin DLL into `C:\Program Files\Vamp Plugins` (or set `VAMP_PATH`); the model is a free download from vamp-plugins.org / isophonics.net.
2. **Store** `(track_id, time, chord)` rows in our own DB (fits the Akasha append-only substrate).
3. **Replay:** sync stored `(time, chord)` to the live position from SMTC (section 1) — the LEDs change color on chord changes in time with the music.

**Accuracy expectations:** Chordino is older-gen (~mid-70s% maj/min, weaker on 7ths/inversions) — fine for "march the pads to the chord," weak for a precise sheet. Higher accuracy = modern PyTorch chord models (BTC transformer / ChordMini family; torch has clean cp311 wheels, you supply weights) — **but** ChordMini's pipeline drags in madmom's Windows build pain; budget WSL/Linux or a torch-only model that avoids madmom.

**Seeding / why Ultimate Guitar won't directly feed it:**
- **Ultimate Guitar:** no sanctioned API; only brittle ToS-violating scrapers, and its sheets are chord-over-lyric **text with no timestamps** — unusable as `(track,time,chord)` directly. Useful at most as a chord-vocabulary/validation hint.
- **Chordify:** has time-synced chords but closed, ToS forbids automated access.
- **AcousticBrainz:** dead (submissions ended 2022).
- **Academic sets (Isophonics/Beatles, McGill Billboard, RWC-Pop):** time-aligned annotations but no audio and tiny fixed song lists — use to **validate** our extractor, not to populate it.

Bottom line: there is **no legal time-synced chord feed to pull at scale** — we generate the DB ourselves with Chordino/torch over audio we have, and use the external sources only for validation and chord-name hints.

---

## 6. MVP SLICE — smallest thing that makes the pads march

We already own the output layer — **`arsenal/keylab`** (SysEx over WinMM, no deps):
- `py -m arsenal.keylab connect` arms DAW mode (gates the LEDs).
- `pad <1..12> <colour>`, `led`, `all`, `rainbow`, `chord <spec>` light the RGB pads; `bench --hz` already measured the colour-update ceiling.
- Wire format in `arsenal/keylab/protocol.py` (byte-builders, testable, read from Arturia's own FL integration script); I/O in `winmidi.py`.

**MVP (one evening):**
1. `py -m pip install PyAudioWPatch aubio-ledfx`
2. `py -m arsenal.keylab connect` (close FL first so it isn't fighting for the DAW port).
3. Small script: PyAudioWPatch loopback → downmix mono @48000 → `aubio.tempo` → **on each beat flag, advance a color/pad cursor** by calling into `arsenal.keylab.protocol` builders (reuse the `pad`/`led` SysEx path directly rather than shelling out per beat, to stay inside the LedStrip queue's rate ceiling). Colors can cycle a palette per beat, or map BPM→hue.
4. Confirm against `bench` findings that per-beat sends stay under the visible-stall rate.

That alone gives "pads march to the beat, changing color as it clicks through." **Layer 2** adds SMTC (section 1) for a position-driven progress animation. **Layer 3** adds the offline Chordino DB (section 5) so pad colors follow chord changes.

**Pre-flight checks before building:** confirm the KeyLab enumerates as `KeyLab 88 mk3 DAW` (`py -m arsenal.keylab ports`); if you take the Spotify Web-API fallback, confirm Daniel's account is Premium (dead app otherwise).

---

**Key files referenced (all absolute):** `E:\AI-Setup\arsenal\keylab\README.md`, `E:\AI-Setup\arsenal\keylab\protocol.py`, `E:\AI-Setup\arsenal\keylab\winmidi.py`, `E:\AI-Setup\arsenal\keylab\__main__.py`, `E:\AI-Setup\arsenal\midiports.py`.