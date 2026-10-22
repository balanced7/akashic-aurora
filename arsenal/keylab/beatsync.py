"""arsenal.keylab.beatsync -- march the KeyLab pads to whatever is playing out the speakers.

Spotify deprecated its BPM/beat API for new apps (403 since 2024-11-27), so we detect the beat LOCALLY from the
system audio (WASAPI loopback). Bonus: that makes it source-agnostic -- Spotify, YouTube, or your own FL tracks
all drive the lights the same way. Now-playing title comes from Windows SMTC (no OAuth), best-effort.

Deps (prebuilt cp311 wheels): PyAudioWPatch, aubio-ledfx (imported as `aubio`), numpy.
Run:  py -m arsenal.keylab beat        (keyboard must be physically in DAW mode)

Known MVP limits (refine later): LED sends block the audio loop briefly on each beat; a dedicated output thread
would tighten timing. aubio reports half/double tempo on some tracks -- the visual follows the actual beats it
flags, so the march stays musical even when the printed BPM octave is off.
"""
from __future__ import annotations

import time
from typing import Optional

from . import protocol as P
from . import winmidi as W

HOP = 512    # samples per analysis block
WIN = 1024   # aubio tempo window


def now_playing() -> Optional[dict]:
    """Best-effort Windows SMTC read -> {title, artist, status} (None if unavailable)."""
    try:
        import asyncio
        from winrt.windows.media.control import \
            GlobalSystemMediaTransportControlsSessionManager as MM

        async def _get():
            mgr = await MM.request_async()
            session = mgr.get_current_session()
            if not session:
                return None
            props = await session.try_get_media_properties_async()
            info = session.get_playback_info()
            return {"title": props.title, "artist": props.artist, "status": int(info.playback_status)}

        return asyncio.run(_get())
    except Exception:
        return None


def _open_loopback(pa):
    """Return (device_info) for the default speakers' WASAPI loopback, with a generator fallback."""
    inst = pa.PyAudio()
    try:
        return inst, inst.get_default_wasapi_loopback()
    except Exception:
        for dev in inst.get_loopback_device_info_generator():  # type: ignore[attr-defined]
            return inst, dev
        raise RuntimeError("no WASAPI loopback device found")


def run(port: Optional[str] = None, secs: Optional[float] = None, mode: str = "cycle",
        bank: str = "DAW", gap: float = 0.005, verbose: bool = True) -> int:
    import numpy as np
    import aubio
    import pyaudiowpatch as pa

    inst, dev = _open_loopback(pa)
    rate = int(dev["defaultSampleRate"])
    ch = int(dev["maxInputChannels"]) or 2
    stream = inst.open(format=pa.paFloat32, channels=ch, rate=rate, input=True,
                       input_device_index=dev["index"], frames_per_buffer=HOP)
    tempo = aubio.tempo("default", WIN, HOP, rate)

    out = W.MidiOut(port, prefer="daw")
    out.send_sysex(P.daw_connect(True))
    from .ledframe import PadRenderer
    render = PadRenderer(out, bank=bank, gap=gap)  # only repaints pads that changed -> cheap, no flooding

    def light(colors):
        render.set_frame(colors)

    np_ = now_playing()
    if np_:
        print(f"now playing: {np_.get('artist','?')} - {np_.get('title','?')}")
    print(f"loopback: {dev['name']} @ {rate}Hz x{ch}  (mode={mode}; a few seconds to lock the beat...)")

    step = beats = 0
    last_light = 0.0  # hardware freeze guard: never repaint faster than MIN_LIGHT_GAP
    MIN_LIGHT_GAP = 0.12
    t_end = (time.perf_counter() + secs) if secs else None
    try:
        while t_end is None or time.perf_counter() < t_end:
            raw = stream.read(HOP, exception_on_overflow=False)
            frames = np.frombuffer(raw, dtype=np.float32)
            if ch > 1:
                frames = frames.reshape(-1, ch).mean(axis=1)
            samples = np.ascontiguousarray(frames, dtype=np.float32)
            if samples.shape[0] != HOP:
                continue
            if float(samples.std()) < 1e-5:   # silence -> don't lock onto noise
                continue
            if tempo(samples)[0]:
                beats += 1
                now = time.perf_counter()
                if now - last_light < MIN_LIGHT_GAP:   # guard against over-trigger flooding the device
                    continue
                last_light = now
                step += 1
                bpm = tempo.get_bpm()
                if mode == "cycle":
                    light([P.hue(step, 12)] * 12)              # all pads step hue each beat
                elif mode == "rainbow":
                    light([P.hue(i + step, 12) for i in range(12)])  # scroll a rainbow
                elif mode == "march":
                    light(["white" if i == step % 12 else "off" for i in range(12)])  # a dot walks
                else:
                    light([P.hue(step, 12)] * 12)
                if verbose:
                    print(f"  beat {beats:4d}  bpm {bpm:5.1f}")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            light(["off"] * 12)
            out.send_sysex(P.daw_connect(False))
        except Exception:
            pass
        out.close()
        try:
            stream.stop_stream(); stream.close(); inst.terminate()
        except Exception:
            pass
    print(f"done -- {beats} beats | {render.stats()}")
    return 0
