"""The predictive beat march's timing decision (beatsync.fire_time): audio time -> wall clock, minus the lead.
And the loopback read: 'beat' and 'record' must not hang while nothing plays (the WASAPI loopback's read never returns
in silence -- measured 2026-10-23), so they read it through beatsync.IdleFill on a reader thread."""
from __future__ import annotations

import sys
import threading
import time
import types

import numpy as np
import pytest

from arsenal.keylab import beatsync as BS
from arsenal.keylab.beatsync import fire_time

BLOCK = 512 / 44100          # one block period, ~11.6 ms


def test_a_beat_far_ahead_is_left_for_a_later_block():
    assert fire_time(t_beat=10.5, audio_t=10.0, wall_at_audio_t=100.0, wall_now=100.0, lead_s=0.015, block_s=BLOCK) is None


def test_a_beat_due_within_this_block_fires_at_beat_minus_lead():
    t = fire_time(t_beat=10.02, audio_t=10.0, wall_at_audio_t=100.0, wall_now=100.0, lead_s=0.015, block_s=BLOCK)
    assert t == pytest.approx(100.0 + 0.02 - 0.015)


def test_an_overdue_beat_fires_now_rather_than_never():
    t = fire_time(t_beat=10.0, audio_t=10.05, wall_at_audio_t=100.0, wall_now=100.001, lead_s=0.015, block_s=BLOCK)
    assert t is not None and t < 100.001


def test_a_bigger_lead_paints_earlier():
    early = fire_time(10.012, 10.0, 100.0, 100.0, 0.019, BLOCK)   # both paints fall inside this block
    late = fire_time(10.012, 10.0, 100.0, 100.0, 0.005, BLOCK)
    assert early < late and late - early == pytest.approx(0.014)


# --- a silent loopback ----------------------------------------------------------------------------------------------

class _SilentLoopback:
    """pyaudiowpatch as it behaves while nothing plays: the loopback stream's read() does not return (until the test
    releases it, so no thread is left behind)."""

    def __init__(self, rate: int, ch: int = 2):
        self.rate, self.ch = rate, ch
        self.release = threading.Event()
        self.reads = 0

    def module(self):
        dev = self

        class Stream:
            def read(self, n, exception_on_overflow=False):
                dev.reads += 1
                dev.release.wait()
                return np.zeros(n * dev.ch, dtype=np.float32).tobytes()

            def stop_stream(self):
                pass

            def close(self):
                pass

        class Inst:
            def get_default_wasapi_loopback(self):
                return {"defaultSampleRate": dev.rate, "maxInputChannels": dev.ch, "index": 0, "name": "silent loopback"}

            def open(self, **kw):
                return Stream()

            def terminate(self):
                pass

        return types.SimpleNamespace(PyAudio=Inst, paFloat32=1)


def _run(fn, timeout):
    out = {}

    def go():
        try:
            out["value"] = fn()
        except BaseException as exc:          # surfaced to the test, not lost on the thread
            out["error"] = exc

    t = threading.Thread(target=go, daemon=True)
    t0 = time.perf_counter()
    t.start()
    t.join(timeout)
    return t, out, time.perf_counter() - t0


def test_record_does_not_hang_while_nothing_plays(monkeypatch, tmp_path):
    import soundfile as sf
    dev = _SilentLoopback(rate=8000)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", dev.module())
    monkeypatch.setattr(BS, "now_playing", lambda: None)
    try:
        t, out, took = _run(lambda: BS.record(0.5, out_dir=str(tmp_path), name="silence"), 5.0)
        assert not t.is_alive(), "record() hung on a silent loopback"
        assert "error" not in out, out.get("error")
        assert dev.reads >= 1 and took < 3.0
        audio, rate = sf.read(out["value"])
        assert rate == 8000 and len(audio) >= 4000 and not np.any(audio)       # 0.5 s of silence, in real time
        timing = BS.read_timing(out["value"])
        assert timing["silence_filled_s"] >= 0.5 and timing["samples"] == len(audio)
        assert abs(timing["wall_secs"] - timing["sample_secs"]) < 0.05        # the silence kept pace with the clock
    finally:
        dev.release.set()


def test_the_beat_march_does_not_hang_while_nothing_plays_and_paints_no_beat(monkeypatch, capsys):
    dev = _SilentLoopback(rate=48000)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", dev.module())
    monkeypatch.setattr(BS, "now_playing", lambda: None)
    sent = []

    class Out:
        name = "fake KeyLab DAW out"

        def __init__(self, *a, **k):
            pass

        def send_sysex(self, data):
            sent.append(bytes(data))

        def close(self):
            pass

    saved = {}

    def save_session(blocks, rate, clock, hand_in, np_, timing=None, root=None):
        saved.update(blocks=len(blocks), rate=rate, timing=timing, silent=not any(b.any() for b in blocks))
        return "not written"

    monkeypatch.setattr(BS.W, "MidiOut", Out)
    monkeypatch.setattr(BS, "_save_session", save_session)
    try:
        t, out, took = _run(lambda: BS.run_predictive(secs=1.0, offline=True, connect=False, verbose=False, save=True),
                            6.0)
        assert not t.is_alive(), "beat hung on a silent loopback"
        assert "error" not in out, out.get("error")
        assert out["value"] == 0 and took < 4.0
    finally:
        dev.release.set()
    # the tracker heard real-time silence through the pause, the saved session's capture timing is still written,
    # and no beat was painted in the silence
    assert saved["rate"] == 48000 and saved["silent"] and saved["blocks"] >= 50
    assert saved["timing"]["sample_secs"] > 0.6 and abs(saved["timing"]["wall_secs"] - saved["timing"]["sample_secs"]) < 0.05
    assert "done -- 0 beats painted ahead" in capsys.readouterr().out


def test_idle_fill_hands_over_real_blocks_with_their_capture_stamps(monkeypatch):
    """While the device delivers, every block arrives as itself, stamped on the capture clock when the reader got it."""
    ticks = iter(range(1000))
    monkeypatch.setattr(BS, "_clock", lambda: float(next(ticks)))

    class Dev:
        rate, hop, channels, name = 48000, 512, 2, "dev"

        def __init__(self):
            self.k = 0

        def read(self):
            self.k += 1
            if self.k > 5:
                return None
            time.sleep(0.002)
            return np.full((512, 2), self.k, dtype=np.float32)

    feed = BS.IdleFill(Dev())
    got = []
    while True:
        b, stamp, filled = feed.read_stamped()
        if b is None:
            break
        got.append((int(b[0, 0]), b.shape, stamp, filled))
    feed.close()
    assert [g[0] for g in got] == [1, 2, 3, 4, 5] and all(g[1] == (512, 2) and not g[3] for g in got)
    assert [g[2] for g in got] == sorted(g[2] for g in got) and feed.filled == 0 and feed.dropped == 0
