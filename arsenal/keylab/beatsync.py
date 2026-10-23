"""arsenal.keylab.beatsync -- march the KeyLab pads to whatever is playing out the speakers.

Spotify deprecated its BPM/beat API for new apps (403 since 2024-11-27), so we detect the beat LOCALLY from the
system audio (WASAPI loopback). Bonus: that makes it source-agnostic -- Spotify, YouTube, or your own FL tracks
all drive the lights the same way. Now-playing title comes from Windows SMTC (no OAuth), best-effort.

Deps (prebuilt cp311 wheels): PyAudioWPatch, aubio-ledfx (imported as `aubio`), numpy.
Run:  py -m arsenal.keylab beat        (keyboard must be physically in DAW mode)

The loopback's read() never returns while nothing plays (WASAPI delivers no packets in silence), so no loop here reads
it directly: IdleFill does the blocking reads on its own thread and hands over silence, in real time, during a pause
('beat' and 'record' used to hang on silence until something played; the VJ engine found it, 2026-10-23).

Known limits: aubio (the optional old path) reports half/double tempo on some tracks -- the visual follows the actual
beats it flags, so the march stays musical even when the printed BPM octave is off.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Tuple

from . import protocol as P
from . import winmidi as W

HOP = 512    # samples per analysis block
WIN = 1024   # aubio tempo window
GAP_TOL_S = 0.020   # a capture whose sample time and wall time differ by more than this has a gap

# The clock captures are timed with. A module attribute so a test can drive a capture on a fake clock.
_clock = time.perf_counter


def capture_timing(first_return: float, first_frames: int, last_return: float, n_samples: int, rate: int,
                   epoch_minus_clock: Optional[float] = None) -> dict:
    """Did the capture lose time? WASAPI loopback hands over nothing while nothing plays, and an overflow drops
    samples, so a recording can be shorter than the time it took: the audio after a gap is then earlier than the
    music was, and a whole-track grid fitted to it is wrong after the gap. The first block began first_frames /
    rate before it was handed over; from there to the last hand-over is the wall time. The sample count gives the
    sample time. They must agree within GAP_TOL_S."""
    wall_start = first_return - first_frames / rate
    wall_secs = last_return - wall_start
    sample_secs = n_samples / rate
    gap_s = wall_secs - sample_secs
    off = (time.time() - _clock()) if epoch_minus_clock is None else epoch_minus_clock
    stamp = lambda c: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c + off)) + f".{int((c + off) % 1 * 1000):03d}"
    return {"wall_start": stamp(wall_start), "wall_end": stamp(last_return), "wall_secs": round(wall_secs, 4),
            "samples": int(n_samples), "rate": int(rate), "sample_secs": round(sample_secs, 4),
            "gap_ms": round(gap_s * 1000, 1), "gap": abs(gap_s) > GAP_TOL_S}


def write_timing(audio_path: str, timing: dict) -> str:
    """`<audio>.rec.json`, next to the audio: wall_secs, sample_secs, the gap flag (annotate refuses a gap)."""
    import json
    side = audio_path + ".rec.json"
    with open(side, "w", encoding="utf-8") as f:
        json.dump(timing, f, indent=1)
    return side


def read_timing(audio_path: str) -> Optional[dict]:
    import json
    import os
    side = audio_path + ".rec.json"
    if not os.path.exists(side):
        return None
    with open(side, encoding="utf-8") as f:
        return json.load(f)


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


class LoopbackStream:
    """The default speakers' loopback as a block source: read() -> one block of HOP frames, shape (HOP, channels),
    float32. read() BLOCKS while nothing plays -- read it through IdleFill."""

    def __init__(self, pa):
        self.inst, dev = _open_loopback(pa)
        self.dev = dev
        self.rate = int(dev["defaultSampleRate"])
        self.channels = int(dev["maxInputChannels"]) or 2
        self.hop = HOP
        self.name = f"loopback: {dev['name']} @ {self.rate} Hz"
        self.stream = self.inst.open(format=pa.paFloat32, channels=self.channels, rate=self.rate, input=True,
                                     input_device_index=dev["index"], frames_per_buffer=HOP)

    def read(self):
        import numpy as np
        raw = self.stream.read(HOP, exception_on_overflow=False)
        return np.frombuffer(raw, dtype=np.float32).reshape(-1, self.channels).copy()

    def close(self) -> None:
        try:
            self.stream.stop_stream(); self.stream.close(); self.inst.terminate()
        except Exception:
            pass


class IdleFill:
    """Wraps a device whose read() BLOCKS while nothing plays (the WASAPI loopback delivers nothing in silence --
    measured 2026-10-23: a 3 s read on an idle Focusrite never returned). A reader thread does the blocking reads and
    stamps each block's hand-over on the capture clock (_clock); read_stamped() hands over (block, stamp, filled):
    the device's blocks, or a block of silence once the device has been quiet for grace_s, then one per block period
    on an absolute schedule, so whatever the blocks drive (a beat tracker, a recording, an analysis clock) keeps
    running through a pause in real time. The grace at the start of each pause is wall time no block covers (gap_s).
    If the reader runs more than max_backlog_s ahead of the consumer, the oldest blocks are dropped and counted
    (dropped_s), never silently; max_backlog_s=None never drops (a recording keeps every sample).

    src: .rate and .read() -> a block (None = ended); optional .name, .hop, .channels (the silence block's shape:
    (hop,) for 1, else (hop, channels)) and .close(). close() closes src only once the reader has left read() --
    a reader still blocked in a silent device's read is left to process exit."""

    def __init__(self, src, grace_s: float = 0.1, max_backlog_s: Optional[float] = 2.0):
        import numpy as np
        self._np = np
        self.src, self.rate, self.name = src, int(src.rate), getattr(src, "name", "")
        self.hop = int(getattr(src, "hop", HOP))
        ch = int(getattr(src, "channels", 1) or 1)
        self.fill_shape = (self.hop,) if ch == 1 else (self.hop, ch)
        self.dur = self.hop / float(self.rate)
        self.grace_s = grace_s
        self.max_blocks = None if max_backlog_s is None else max(4, int(max_backlog_s / self.dur))
        self.q: "queue.SimpleQueue" = queue.SimpleQueue()
        self.filled = self.dropped = 0
        self.gap_s = 0.0                  # wall time no block covers (the grace at the start of each pause)
        self._idle = False
        self._last_real: Optional[float] = None
        self._next_fill = 0.0
        self._stop = False
        self._err: Optional[BaseException] = None
        self._t = threading.Thread(target=self._pump, name="loopback-reader", daemon=True)
        self._t.start()

    @property
    def dropped_s(self) -> float:
        return self.dropped * self.dur

    @property
    def filled_s(self) -> float:
        return self.filled * self.dur

    def _pump(self) -> None:
        while not self._stop:
            try:
                b = self.src.read()
                stamp = _clock()
            except Exception as exc:
                self._err = exc
                self.q.put((None, _clock()))
                return
            self.q.put((b, stamp))
            if b is None:
                return

    def read_stamped(self) -> Tuple[Optional[object], float, bool]:
        """-> (block or None at the end, its hand-over time on _clock, True if it is a block of silence)."""
        if self.max_blocks is not None:
            while self.q.qsize() > self.max_blocks:
                try:
                    self.q.get_nowait()
                    self.dropped += 1
                except queue.Empty:
                    break
        now = time.perf_counter()
        if self._idle:
            deadline = self._next_fill
        else:
            deadline = (self._last_real if self._last_real is not None else now) + self.dur + self.grace_s
        try:
            b, stamp = self.q.get(timeout=max(0.0, deadline - now))
        except queue.Empty:
            if not self._idle:
                self._idle = True
                self.gap_s += self.grace_s
                self._next_fill = deadline
            self._next_fill += self.dur
            self.filled += 1
            return self._np.zeros(self.fill_shape, dtype=self._np.float32), _clock(), True
        if b is None:
            if self._err is not None:
                raise self._err
            return None, stamp, False
        self._idle = False
        self._last_real = time.perf_counter()
        return b, stamp, False

    def read(self):
        return self.read_stamped()[0]

    def close(self) -> None:
        self._stop = True
        self._t.join(timeout=0.3)
        if not self._t.is_alive():
            close = getattr(self.src, "close", None)
            if callable(close):
                close()


def record(secs: float = 90.0, out_dir: Optional[str] = None, name: Optional[str] = None) -> str:
    """Capture what is playing (WASAPI loopback) to a local FLAC, named after the now-playing track, so a tracker
    can be judged on the REAL song instead of synthetic audio (Daniel, 2026-10-22: "most definitely"). Recordings
    are third-party audio: they live under state/ (gitignored), are never committed, and are for local testing
    only. Returns the file path.

    The loopback is read through IdleFill: while nothing plays, the recording gets silence in real time instead of
    waiting forever for the first packet (it hung on silence before 2026-10-23). The timing record says how much of
    it was filled silence (silence_filled_s); a pause in the middle still shows as a timing gap (the grace before
    the fill starts is wall time no sample covers), so such a recording is never taken for an answer key."""
    import os
    import re
    import numpy as np
    import pyaudiowpatch as pa
    import soundfile as sf

    src = LoopbackStream(pa)
    dev, rate, ch = src.dev, src.rate, src.channels
    np_ = now_playing() or {}
    label = name or " - ".join(x for x in (np_.get("artist"), np_.get("title")) if x) or "loopback"
    safe = re.sub(r"[^\w\- .()]+", "_", label).strip()[:80]
    root = out_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                   "state", "arsenal", "keylab", "recordings")
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{time.strftime('%Y%m%d-%H%M%S')} {safe}.flac")
    print(f"recording {secs:.0f} s of '{label}' from {dev['name']} @ {rate} Hz -> {path}")
    feed = IdleFill(src, max_backlog_s=None)              # a recording keeps every sample
    chunks, need = [], int(secs * rate)
    first = last = None                                   # (clock at hand-over, frames) of the first / last block
    try:
        got = 0
        while got < need:
            frames, now, _filled = feed.read_stamped()
            if frames is None:
                break
            chunks.append(frames)
            got += len(frames)
            if first is None:
                first = (now, len(frames))
            last = now
    except KeyboardInterrupt:
        pass
    finally:
        feed.close()
    audio = np.concatenate(chunks) if chunks else np.zeros((0, ch), dtype=np.float32)
    sf.write(path, audio, rate, format="FLAC", subtype="PCM_16")
    if first is not None:
        timing = capture_timing(first[0], first[1], last, len(audio), rate)
        timing["silence_filled_s"] = round(feed.filled_s, 3)
        write_timing(path, timing)
        flag = (f"  TIMING GAP: {timing['sample_secs']:.3f} s of samples over {timing['wall_secs']:.3f} s of wall "
                f"clock ({timing['gap_ms']:+.0f} ms) -- record again before annotating" if timing["gap"] else
                f"  timing ok ({timing['gap_ms']:+.1f} ms)")
        if feed.filled:
            flag += f"  ({feed.filled_s:.1f} s of it is silence: nothing was playing)"
    else:
        flag = ""
    print(f"saved {len(audio) / rate:.1f} s -> {path}{flag}")
    return path


class _Painter:
    """Paints the pads on its OWN thread, so the audio loop never waits for a light. (Until 2026-10-23 the loop slept
    until each paint was due and then spent ~60 ms sending 12 pad colours; the loopback buffer overflowed meanwhile and
    ~15 % of the audio was silently dropped: 513 s kept of a 600 s run. The tracker saw holes that look like phase
    jumps, and tapped answer keys lost their clock.)"""

    def __init__(self, render, mode: str, min_gap: float, verbose: bool):
        import queue
        import threading
        self.render, self.mode, self.min_gap, self.verbose = render, mode, min_gap, verbose
        self.q = queue.Queue()
        self.painted: list = []
        self.beats = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, name="pad-painter", daemon=True)
        self._t.start()

    def submit(self, fire_at: float, info: dict) -> None:
        self.q.put((fire_at, info))

    def _run(self) -> None:
        import queue
        last = 0.0
        while not self._stop.is_set():
            try:
                fire_at, info = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            wait = fire_at - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            now = time.perf_counter()
            if now - last < self.min_gap:
                continue
            last = now
            self.painted.append(now)
            if len(self.painted) > 64:
                del self.painted[:-64]
            self.beats += 1
            _paint(self.render.set_frame, self.mode, self.beats)
            if self.verbose:
                print(f"  beat {self.beats:4d}  bpm {info['bpm']:5.1f}  conf {info['confidence']:.2f}")

    def stop(self) -> None:
        self._stop.set()
        self._t.join(timeout=1.0)


def _save_session(blocks, rate, clock, hand_in, np_, timing: Optional[dict] = None,
                  root: Optional[str] = None) -> str:
    """Write what the tracker heard (FLAC) and, beside it, the hand's taps and nudges on the SAME audio clock:
    a tapped-through song is an answer key made by ear (state/, never committed). timing (capture_timing of the
    saved blocks) is written next to the audio as `<file>.rec.json` and into the hand file: a session with a gap
    (blocks skipped, an overflow) cannot be an answer key, because its taps would land on the wrong audio."""
    import json
    import os
    import re
    import numpy as np
    import soundfile as sf
    root = root or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "state", "arsenal", "keylab", "recordings")
    os.makedirs(root, exist_ok=True)
    label = " - ".join(x for x in ((np_ or {}).get("artist"), (np_ or {}).get("title")) if x) or "session"
    safe = re.sub(r"[^\w\- .()]+", "_", label).strip()[:80]
    path = os.path.join(root, f"{time.strftime('%Y%m%d-%H%M%S')} {safe} (live).flac")
    sf.write(path, np.concatenate(blocks), rate, format="FLAC", subtype="PCM_16")
    meta = {"source": "beat --save (the tracker's own input)", "now_playing": label}
    if timing is not None:
        write_timing(path, timing)
        meta["timing"] = timing
    if hand_in is not None and hand_in.log and len(clock) >= 2:
        at = np.array([c[0] for c in clock]); wall = np.array([c[1] for c in clock])
        def to_audio(t):                       # perf_counter -> seconds into this recording
            return float(np.interp(t, wall, at, left=at[0] + (t - wall[0]), right=at[-1] + (t - wall[-1])))
        meta["taps"] = [round(to_audio(t), 4) for t, kind, _ in hand_in.log if kind == "tap"]
        meta["nudges"] = [[round(to_audio(t), 4), v] for t, kind, v in hand_in.log if kind == "nudge"]
    with open(path + ".hand.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    gap = f"  TIMING GAP {timing['gap_ms']:+.0f} ms: not usable as an answer key" if timing and timing["gap"] else ""
    print(f"saved the session: {path} ({len(meta.get('taps', []))} taps){gap}")
    return path


def _paint(light, mode: str, step: int) -> None:
    if mode == "rainbow":
        light([P.hue(i + step, 12) for i in range(12)])          # scroll a rainbow
    elif mode == "march":
        light(["white" if i == step % 12 else "off" for i in range(12)])  # a dot walks
    else:
        light([P.hue(step, 12)] * 12)                             # all pads step hue each beat


def fire_time(t_beat: float, audio_t: float, wall_at_audio_t: float, wall_now: float, lead_s: float,
              block_s: float) -> Optional[float]:
    """When to paint a predicted beat, on the wall clock -- or None if a later block should handle it.

    The block that ended at audio time audio_t arrived at wall_at_audio_t, so audio time t maps to
    wall_at_audio_t + (t - audio_t). The paint goes lead_s earlier, so the light lands ON the beat. A paint due
    within the next block period belongs to this block (it sleeps until then); a paint already overdue fires now."""
    fire_at = wall_at_audio_t + (t_beat - audio_t) - lead_s
    if fire_at - wall_now > block_s:
        return None
    return fire_at


def _seed_for(np_: Optional[dict], offline: bool) -> Optional[float]:
    """The song's BPM from the database chain in tempo.py (GetSongBPM / MusicBrainz -> AcousticBrainz / Deezer),
    fused; None when nothing is playing, nothing agrees, or we are offline."""
    if not np_ or offline:
        return None
    try:
        from . import tempo as T
        found = T.lookup(np_.get("artist", ""), np_.get("title", ""))
        if not found:
            return None
        fused = T.fuse_bpm(found)
        return float(fused.bpm) if fused.bpm and fused.confidence > 0 else None
    except Exception:
        return None


def run_predictive(port: Optional[str] = None, secs: Optional[float] = None, mode: str = "cycle",
                   bank: str = "DAW", gap: float = 0.005, verbose: bool = True, lead_ms: float = 15.0,
                   seed_bpm: Optional[float] = None, offline: bool = False, connect: bool = True,
                   engine: str = "a", referee: bool = False, hand: bool = False, save: bool = False) -> int:
    """The house tracker (beat_a, the blind-pair winner, beatbench 2026-10-22) driving the pads AHEAD of the beat:
    each frame is painted at the PREDICTED beat time minus lead_ms, so the light lands on the beat instead of
    after it. lead_ms covers the device's own ~10 ms plus the loopback capture delay; tune it by eye/ear (P21
    measures it). The database seed, when found, holds the tempo octave.

    connect=False is GUEST mode, for when FL Studio's KeyLab script owns the connection (probe P1, 2026-10-22:
    with FL open, our pad writes land and stay -- the port is shared under the Windows MIDI Service). A guest
    never sends DAW connect or disconnect, so FL's integration and screen are left exactly as they were.

    engine picks the tracker module beat_<engine>.py: "a" is the shipped one; any other contestant (e.g. "g", the
    grid tracker) is an opt-in live trial and is NOT shipped unless it passes its pre-registered bench gate."""
    import importlib
    import numpy as np
    import pyaudiowpatch as pa
    Tracker = importlib.import_module(f"{__package__}.beat_{engine}").Tracker

    src = LoopbackStream(pa)
    dev, rate, ch = src.dev, src.rate, src.channels
    np_ = now_playing()
    seed = seed_bpm or _seed_for(np_, offline)
    if np_:
        print(f"now playing: {np_.get('artist','?')} - {np_.get('title','?')}")
    print(f"seed: {seed:.1f} BPM from the databases" if seed else "seed: none (the tracker finds the tempo itself)")
    tracker = Tracker(rate, HOP, seed_bpm=seed)
    hand_in = None
    if hand:
        from .beathand import Hand, folded_ratio, RESEED_DIFF, RESEED_GAP_S
        hand_in = Hand(verbose=verbose)
    ref = None
    if referee:
        from .beatref import Referee
        ref = Referee(rate, HOP)
        next_verdict = 2.0

    out = W.MidiOut(port, prefer="daw")
    if connect:
        out.send_sysex(P.daw_connect(True))
    from .ledframe import PadRenderer
    render = PadRenderer(out, bank=bank, gap=gap)
    print(f"loopback: {dev['name']} @ {rate}Hz x{ch}  (engine=beat_{engine}, mode={mode}, lead {lead_ms:.0f} ms"
          f"{', GUEST: FL keeps the connection' if not connect else ''})")

    saved_blocks: list = []            # save=True: the audio exactly as the tracker heard it (silence in a pause)
    clock: list = []                   # (audio_t, perf_counter) pairs, to put the hand's taps on the audio clock
    painter = _Painter(render, mode, 0.12, verbose)
    feed = IdleFill(src)               # the loopback's read blocks while nothing plays: never read it on this thread
    wall0 = None                       # wall time of the first block: audio_t should keep pace with it
    dropped_warned = 0.0
    save_first = save_last = None      # hand-over times of the first and last saved block (the gap check)
    audio_t = 0.0                      # seconds of audio fed to the tracker
    tracker_t0 = 0.0                   # where the current tracker's own clock started (moves on a re-seed)
    tap_locked = False                 # the hand is tapping: the lights follow the taps
    last_tap_tempo = None
    last_reseed = -1e9
    fired_for = -1.0                   # the predicted beat we last painted
    t_end = (time.perf_counter() + secs) if secs else None
    try:
        while t_end is None or time.perf_counter() < t_end:
            frames, wall_now, filled = feed.read_stamped()   # wall_now: the block's hand-over on the capture clock
            if frames is None:
                break
            if wall0 is None:
                wall0 = wall_now - HOP / rate
            behind = (wall_now - wall0) - feed.gap_s - (audio_t + HOP / rate)
            if behind - dropped_warned > 0.25:
                dropped_warned = behind
                lost = f", {feed.dropped_s:.2f} s of it dropped" if feed.dropped else ""
                print(f"  [audio] {behind:.2f} s behind the loopback so far{lost} (the loop fell behind)")
            if ch > 1:
                frames = frames.mean(axis=1)
            block = np.ascontiguousarray(frames, dtype=np.float32)
            if block.shape[0] != HOP:
                continue
            tracker.feed(block)
            if save:
                saved_blocks.append(block.copy())
                if save_first is None:
                    save_first = wall_now
                save_last = wall_now
                if len(clock) == 0 or audio_t - clock[-1][0] >= 1.0:
                    clock.append((audio_t + HOP / rate, wall_now))
            audio_t += HOP / rate
            # a re-seeded tracker counts its own time from zero: shift its predictions onto the stream's clock
            ahead = [{**b, "t_beat": b["t_beat"] + tracker_t0} for b in (tracker.predict(audio_t - tracker_t0) or [])]
            if ref is not None:
                ref.predicted(ahead or [])
                ref.feed(block)
                if audio_t >= next_verdict:
                    next_verdict = audio_t + 2.0
                    v = ref.verdict()
                    hand_txt = ""
                    if hand_in is not None and ahead:
                        period = 60.0 / ahead[0]["bpm"]
                        vs = hand_in.versus(painter.painted[-32:], period)
                        tp = hand_in.tap_tempo()
                        if vs:
                            hand_txt += f"  | your taps {vs['offset_ms']:+.0f} ms vs lights (steady {vs['steady']:.2f})"
                        if tp:
                            hand_txt += f" tap {60.0 / tp:.1f} BPM"
                        if hand_in.cc is not None:
                            hand_txt += f"  fader {hand_in.nudge_ms:+.0f} ms"
                    if v.get("state") == "ok":
                        meter = "#" * max(0, int(round(v["on_beat"] * 10)))
                        print(f"  [referee {audio_t:6.1f}s] on-beat {v['on_beat']:+.2f} {meter:<10} offset "
                              f"{v['offset_ms']:+6.0f} ms  steady {v['consistency']:.2f}  bpm {v['tracker_bpm']:.1f}"
                              f" / kicks {v.get('kick_bpm', 0):.1f}{' agree x' + str(v['agree_streak']) if v.get('agree') else ''}"
                              f"{hand_txt}")
                    else:
                        print(f"  [referee {audio_t:6.1f}s] {v.get('state')}{hand_txt}")
            nudge_ms = 0.0
            if hand_in is not None:
                hand_in.poll()
                nudge_ms = hand_in.nudge_ms
                grid = hand_in.tap_grid(wall_now)
                if grid is not None:
                    # TAP-LOCK: while the hand taps, the lights follow the taps (the hand is the metronome)
                    if not tap_locked:
                        print(f"  [hand] tap-lock: the lights follow your taps ({60.0 / grid[1]:.1f} BPM)")
                    tap_locked = True
                    last_tap_tempo = grid[1]
                    nxt_wall, per = grid
                    ahead = [{"t_beat": audio_t + (nxt_wall - wall_now), "bpm": 60.0 / per, "phase": 0.0,
                              "confidence": 1.0}]
                elif tap_locked:
                    tap_locked = False
                    print("  [hand] taps stopped: back to the tracker")
                    # taps just stopped: re-seed ONCE if the hand's tempo and the tracker's disagree
                    tp = last_tap_tempo
                    if (tp and ahead and folded_ratio(60.0 / tp, ahead[0]["bpm"]) > RESEED_DIFF
                            and audio_t - last_reseed > RESEED_GAP_S):
                        print(f"  [hand] re-seeding beat_{engine} from your taps: {60.0 / tp:.1f} BPM "
                              f"(it said {ahead[0]['bpm']:.1f})")
                        tracker = Tracker(rate, HOP, seed_bpm=60.0 / tp)
                        tracker_t0 = audio_t
                        last_reseed = audio_t
                        if ref is not None:
                            ref.pred.clear()
                        continue
            if filled or not ahead:
                continue                                   # nothing is playing: no march in the silence
            t_next = ahead[0]["t_beat"]
            if abs(t_next - fired_for) < 0.05:
                continue
            fire_at = fire_time(t_next, audio_t, wall_now, time.perf_counter(), (lead_ms - nudge_ms) / 1000.0,
                                HOP / rate)
            if fire_at is None:
                continue                                   # not this block's job yet
            fired_for = t_next
            painter.submit(fire_at, ahead[0])              # the painter thread waits; the audio loop never does
    except KeyboardInterrupt:
        pass
    finally:
        painter.stop()
        beats = painter.beats
        try:
            render.set_frame(["off"] * 12)
            if connect:
                out.send_sysex(P.daw_connect(False))
        except Exception:
            pass
        out.close()
        if save and saved_blocks:
            timing = capture_timing(save_first, HOP, save_last, len(saved_blocks) * HOP, rate)
            _save_session(saved_blocks, rate, clock, hand_in, np_, timing=timing)
        if hand_in is not None:
            hand_in.close()
            if hand_in.log:
                import json
                import os
                logdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                      "state", "arsenal", "keylab", "receipts")
                os.makedirs(logdir, exist_ok=True)
                lp = os.path.join(logdir, f"hand-{time.strftime('%Y%m%d-%H%M%S')}.json")
                json.dump({"taps_and_nudges": hand_in.log, "painted": painter.painted}, open(lp, "w"), indent=0)
                print(f"hand log: {lp}")
        feed.close()
    silence = f" | {feed.filled_s:.1f} s of silence while nothing played" if feed.filled else ""
    print(f"done -- {beats} beats painted ahead | {render.stats()}{silence}")
    return 0


def run(port: Optional[str] = None, secs: Optional[float] = None, mode: str = "cycle",
        bank: str = "DAW", gap: float = 0.005, verbose: bool = True, engine: str = "a", **kw) -> int:
    """The beat march. engine "a" (default) = beat_a painting ahead of the beat; "aubio" = the old reactive path
    (GPLv3+, optional, kept for comparison)."""
    if engine != "aubio":
        return run_predictive(port, secs, mode, bank, gap, verbose, engine=engine, **kw)
    import numpy as np
    import aubio
    import pyaudiowpatch as pa

    src = LoopbackStream(pa)
    dev, rate, ch = src.dev, src.rate, src.channels
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
    feed = IdleFill(src)               # the loopback's read blocks while nothing plays: never read it on this thread
    try:
        while t_end is None or time.perf_counter() < t_end:
            frames, _stamp, _filled = feed.read_stamped()
            if frames is None:
                break
            if ch > 1:
                frames = frames.mean(axis=1)
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
        feed.close()
    print(f"done -- {beats} beats | {render.stats()}")
    return 0
