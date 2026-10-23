"""Pins for arsenal/keylab/vj.py, the VJ engine (`py -m arsenal.keylab vj`).

No keyboard, no sound card: MIDI arrives through Engine.feed_midi exactly as the KeyLab input callback hands it
(kind, status, data1, data2), the audio is synthesized, and the LED output is a counting stand-in with the real
MidiOut's one method the painter calls (send_sysex). The HTTP server runs on a test-band port (8900-8999), never
on 8793 or 8794.
"""
from __future__ import annotations

import http.client
import json
import os
import queue
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

from arsenal.keylab import protocol as P
from arsenal.keylab import vj as V

RATE = 48000
NOTE_ON, NOTE_OFF, CC = 0x90, 0x80, 0xB0
REPO = Path(__file__).resolve().parents[1]
# Daniel's real Joy to the World take is his own playing and the repo is public: it lives only in the gitignored
# state/ folder (or wherever KEYLAB_JOY_TAKE points), and the tests that need it skip when it is absent.
JOY = Path(os.environ.get("KEYLAB_JOY_TAKE") or (REPO / "state" / "arsenal" / "keylab" / "joy_take_events.json"))
MAKE_JOY = REPO / "tests" / "fixtures" / "vj"


def _free_port() -> int:
    """A free port in the test-UI band (config.allocate_test_ui_port raises if it would leave the band)."""
    import config
    for offset in range(config.PORT_TEST_UI_MAX - config.PORT_TEST_UI_BASE + 1):
        port = config.allocate_test_ui_port(offset)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
        finally:
            s.close()
    pytest.skip("no free port in the 8900-8999 test band")


def _quiet(_msg):
    pass


class _SSE:
    """A minimal EventSource: reads 'data:' lines off GET /api/events on a background thread."""

    def __init__(self, port: int):
        self.conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        self.conn.request("GET", "/api/events")
        self.resp = self.conn.getresponse()
        self.events: list = []
        self.heartbeats = 0
        self._t = threading.Thread(target=self._read, daemon=True)
        self._t.start()

    def _read(self):
        try:
            while True:
                line = self.resp.readline()
                if not line:
                    return
                line = line.decode("utf-8").rstrip("\r\n")
                if line.startswith("data: "):
                    self.events.append((time.perf_counter(), json.loads(line[6:])))
                elif line.startswith(":"):
                    self.heartbeats += 1
        except (OSError, ValueError):
            return

    def of(self, t):
        return [e for _ts, e in self.events if e["t"] == t]

    def wait_for(self, pred, timeout: float) -> bool:
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            if pred():
                return True
            time.sleep(0.02)
        return pred()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


def _get_json(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", path)
    r = c.getresponse()
    body = json.loads(r.read())
    c.close()
    return r.status, r, body


def _post_json(port, path, obj):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    data = json.dumps(obj).encode()
    c.request("POST", path, body=data, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    body = json.loads(r.read() or b"{}")
    c.close()
    return r.status, r, body


# --- 1. the SSE stream carries every event type with the contract's fields --------------------------------------

def test_sse_stream_delivers_every_event_type_with_the_contract_fields():
    port = _free_port()
    src = V.SynthSource(rate=RATE, bpm=120.0, chords=("C",), realtime=True)      # paced like a device
    eng = V.Engine(http_port=port, source=src, say=_quiet).start()
    sse = None
    try:
        sse = _SSE(port)
        assert sse.resp.status == 200
        assert "text/event-stream" in sse.resp.getheader("Content-Type")
        assert sse.resp.getheader("Access-Control-Allow-Origin") == "*"
        assert sse.wait_for(lambda: sse.of("hello"), 5)
        # the keyboard, as the input callbacks hand it over
        for k in (60, 64, 67):
            eng.feed_midi("midi", NOTE_ON, k, 100)
        eng.feed_midi("midi", CC, 64, 127)                       # pedal down
        eng.feed_midi("daw", 0x99, 3, 90)                        # DAW-mode pad 4
        eng.feed_midi("daw", 0x89, 3, 0)
        time.sleep(0.1)
        eng.feed_midi("midi", 0x99, 44, 80)                      # normal-bank pad 1 (note 44)
        eng.feed_midi("midi", 0x89, 44, 0)
        eng.feed_midi("midi", CC, 105, 100)                      # fader 1 (absolute)
        eng.feed_midi("midi", CC, 91, 65)                        # knob 1 (relative, +1)
        eng.feed_midi("midi", CC, 64, 0)                         # pedal up
        for k in (60, 64, 67):
            eng.feed_midi("midi", NOTE_OFF, k, 0)
        want = {"hello", "status", "beat", "energy", "hit", "chord", "note", "pedal", "pad", "ctl"}
        ok = sse.wait_for(lambda: want <= {e["t"] for _ts, e in sse.events}
                          and any(c["src"] == "audio" for c in sse.of("chord"))
                          and len(sse.of("beat")) >= 3, 15)
        assert ok, f"missing: {want - {e['t'] for _ts, e in sse.events}}"
    finally:
        eng.stop()
        if sse is not None:
            sse.close()

    hello = sse.of("hello")[0]
    assert hello == {"t": "hello", "v": 1, "src": "keylab-vj", "beat_engine": "a", "chords": "blend",
                     "pads_mode": "both", "leds": False, "leds_reason": "LEDs are off (--no-leds)"}
    assert all(isinstance(s["msg"], str) and s["msg"] for s in sse.of("status"))

    beats = sse.of("beat")
    for b in beats:
        assert set(b) == {"t", "due_ms", "bpm", "conf", "n", "on_beat"}
        assert 0 <= b["due_ms"] <= 300, b                     # announced ahead, inside the contract's window
        assert 0 <= b["conf"] <= 1
        assert b["on_beat"] is None or 0 <= b["on_beat"] <= 1
    assert [b["n"] for b in beats] == list(range(beats[0]["n"], beats[0]["n"] + len(beats))), "one per beat"
    assert abs(beats[-1]["bpm"] - 120.0) < 3.0
    landed = [ts + e["due_ms"] / 1000 for ts, e in sse.events if e["t"] == "beat"]
    gaps = np.diff(landed)
    assert np.all(np.abs(gaps - 0.5) < 0.1), f"beats should land 0.5 s apart at 120 BPM: {gaps}"

    for e in sse.of("energy"):
        assert set(e) == {"t", "bass", "mid", "high", "level"}
        assert all(0.0 <= e[k] <= 1.0 for k in ("bass", "mid", "high", "level"))
    for h in sse.of("hit"):
        assert set(h) == {"t", "strength", "band"} and 0 <= h["strength"] <= 1
        assert h["band"] in ("kick", "snare", "hat", "full")

    keys = [c for c in sse.of("chord") if c["src"] == "keys"]
    assert keys and keys[0]["name"] == "C" and keys[0]["root"] == 0 and keys[0]["quality"] == "maj"
    assert keys[0]["pcs"] == [0, 4, 7] and keys[0]["changed"] is True
    audio = [c for c in sse.of("chord") if c["src"] == "audio"]
    assert audio[0]["name"] == "C" and audio[0]["root"] == 0 and audio[0]["changed"] is True
    for c in keys + audio:
        assert {"t", "src", "name", "root", "quality", "pcs", "changed"} <= set(c)

    notes = sse.of("note")
    assert [(n["key"], n["on"]) for n in notes] == [(60, True), (64, True), (67, True),
                                                     (60, False), (64, False), (67, False)]
    assert notes[0]["vel"] == pytest.approx(100 / 127, abs=1e-3) and notes[-1]["vel"] == 0.0
    assert [p["on"] for p in sse.of("pedal")] == [True, False]

    pads = sse.of("pad")
    assert pads[0] == {"t": "pad", "pad": 4, "vel": round(90 / 127, 3), "on": True, "src": "daw"}
    assert pads[1]["pad"] == 4 and pads[1]["on"] is False
    assert pads[2] == {"t": "pad", "pad": 1, "vel": round(80 / 127, 3), "on": True, "src": "bank"}

    ctl = {c["id"]: c for c in sse.of("ctl")}
    assert ctl["cc105"]["kind"] == "abs" and ctl["cc105"]["value"] == pytest.approx(100 / 127, abs=1e-3)
    assert ctl["cc91"]["kind"] == "rel" and ctl["cc91"]["delta"] == 1
    for c in ctl.values():
        assert {"t", "id", "kind", "value", "delta"} <= set(c) and 0 <= c["value"] <= 1


def test_heartbeat_comment_keeps_an_idle_stream_open():
    port = _free_port()
    eng = V.Engine(http_port=port, heartbeat_s=0.3, say=_quiet).start()
    sse = _SSE(port)
    try:
        assert sse.wait_for(lambda: sse.heartbeats >= 2, 3)
    finally:
        eng.stop()
        sse.close()


def test_many_pages_each_get_every_event():
    port = _free_port()
    eng = V.Engine(http_port=port, say=_quiet).start()
    pages = [_SSE(port) for _ in range(3)]
    try:
        assert all(p.wait_for(lambda p=p: p.of("hello"), 5) for p in pages)
        eng.feed_midi("midi", NOTE_ON, 62, 64)
        assert all(p.wait_for(lambda p=p: p.of("note"), 5) for p in pages)
    finally:
        eng.stop()
        for p in pages:
            p.close()


# --- 2. chords from the audio --------------------------------------------------------------------------------------

def _chord_audio(midis, secs):
    t = np.arange(int(secs * RATE)) / RATE
    return V._partials(midis, t).astype(np.float32)


def _run_detector(det, x, t0=0.0):
    out, t = [], t0
    for k in range(0, len(x) - V.HOP + 1, V.HOP):
        t += V.HOP / RATE
        ev = det.feed(x[k:k + V.HOP], t)
        if ev:
            out.append(ev)
    return out, t


def test_audio_chord_detector_names_C_Am_G7_and_Db_from_synthesized_chords():
    det = V.AudioChords(RATE, V.HOP)
    seq = [[48, 60, 64, 67],          # C:  C3 + C4 E4 G4
           [45, 57, 60, 64],          # Am: A2 + A3 C4 E4
           [43, 55, 59, 62, 65],      # G7: G2 + G3 B3 D4 F4
           [49, 61, 65, 68]]          # Db: Db3 + Db4 F4 Ab4
    got, t = [], 0.0
    for midis in seq:
        evs, t = _run_detector(det, _chord_audio(midis, 1.5), t)
        got += evs
    assert [(e["name"], e["root"], e["quality"]) for e in got] == [
        ("C", 0, "maj"), ("Am", 9, "m"), ("G7", 7, "7"), ("Db", 1, "maj")]
    assert [e["pcs"] for e in got] == [[0, 4, 7], [0, 4, 9], [2, 5, 7, 11], [1, 5, 8]]
    assert all(e["t"] == "chord" and e["src"] == "audio" and e["changed"] is True for e in got)


def test_audio_chords_stay_silent_on_noise_and_silence():
    det = V.AudioChords(RATE, V.HOP)
    noise = (0.2 * np.random.default_rng(0).standard_normal(RATE * 3)).astype(np.float32)
    evs, t = _run_detector(det, noise)
    evs2, _ = _run_detector(det, np.zeros(RATE * 2, dtype=np.float32), t)
    assert evs == [] and evs2 == []


def test_a_held_chord_is_announced_once():
    det = V.AudioChords(RATE, V.HOP)
    evs, _ = _run_detector(det, _chord_audio([48, 60, 64, 67], 4.0))
    assert [e["name"] for e in evs] == ["C"]


# --- 3. controls -----------------------------------------------------------------------------------------------

def test_relative_knob_decodes_offset_64_ticks_and_accumulates():
    d = V.CCDecoder()
    out = [d.feed("midi:1:cc91", 91, v, 0.01 * i)[0] for i, v in enumerate((65, 65, 66, 63))]
    assert [o["kind"] for o in out] == ["rel"] * 4
    assert [o["delta"] for o in out] == [1, 1, 2, -1]
    assert out[-1]["value"] == pytest.approx(0.5 + 3 * V.REL_STEP, abs=1e-4)


def test_dial_turns_by_its_accelerated_steps():
    d = V.CCDecoder()
    cw, _ = d.feed("midi:1:cc116", 116, 72, 0.0)
    ccw, _ = d.feed("midi:1:cc116", 116, 55, 0.05)
    assert (cw["kind"], cw["delta"], ccw["delta"]) == ("rel", 8, -9)


def test_relative_value_clamps_to_the_unit_range():
    d = V.CCDecoder()
    for i in range(200):
        o, _ = d.feed("midi:1:cc92", 92, 72, i * 0.01)
    assert o["value"] == 1.0


def test_fader_is_absolute():
    d = V.CCDecoder()
    a, _ = d.feed("midi:1:cc105", 105, 0, 0.0)
    b, _ = d.feed("midi:1:cc105", 105, 127, 0.05)
    assert (a["kind"], a["value"], b["value"], b["delta"]) == ("abs", 0.0, 1.0, 127)


def test_an_unknown_cc_is_learned_relative_on_touch_when_it_repeats_near_64():
    d = V.CCDecoder()
    first, note1 = d.feed("midi:1:cc20", 20, 65, 0.0)
    second, note2 = d.feed("midi:1:cc20", 20, 65, 0.05)
    assert first["kind"] == "abs" and second["kind"] == "rel" and second["delta"] == 1
    assert note2 and "relative" in note2


def test_an_unknown_cc_sweeping_far_from_64_stays_absolute():
    d = V.CCDecoder()
    outs = [d.feed("midi:1:cc21", 21, v, i * 0.02)[0] for i, v in enumerate((10, 11, 12))]
    assert [o["kind"] for o in outs] == ["abs"] * 3 and outs[-1]["value"] == pytest.approx(12 / 127, abs=1e-4)


def test_a_table_knob_that_behaves_like_a_fader_is_relearned_absolute():
    d = V.CCDecoder()
    kinds = [d.feed("midi:1:cc94", 94, v, i * 0.02)[0]["kind"] for i, v in enumerate((10, 20, 30))]
    assert kinds[-1] == "abs"


# --- 4. replay --------------------------------------------------------------------------------------------------

def _collect(eng):
    seen = []
    eng.hub.tap(seen.append)
    return seen


def _wait(pred, timeout):
    end = time.perf_counter() + timeout
    while time.perf_counter() < end and not pred():
        time.sleep(0.02)
    return pred()


def test_replay_of_a_short_note_list_produces_note_and_chord_events_in_order(tmp_path):
    notes = [{"pos_s": 0.0, "key": k, "vel": 100, "len_s": 0.4} for k in (60, 64, 67)] + \
            [{"pos_s": 0.5, "key": k, "vel": 90, "len_s": 0.4} for k in (57, 60, 64)]
    path = tmp_path / "notes.json"
    path.write_text(json.dumps(notes), encoding="utf-8")
    eng = V.Engine(http_port=None, replay=V.load_replay(path), replay_delay=0.0, say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "replay done" for e in seen), 5)
        time.sleep(0.15)
    finally:
        eng.stop()
    seq = [(e["t"], e["key"] if e["t"] == "note" else e["name"], e.get("on")) for e in seen if e["t"] in ("note", "chord")]
    assert seq == [("note", 60, True), ("note", 64, True), ("note", 67, True), ("chord", "C", None),
                   ("note", 60, False), ("note", 64, False), ("note", 67, False),
                   ("note", 57, True), ("note", 60, True), ("note", 64, True), ("chord", "Am", None),
                   ("note", 57, False), ("note", 60, False), ("note", 64, False)]
    chords = [e for e in seen if e["t"] == "chord"]
    assert [c["src"] for c in chords] == ["keys", "keys"] and chords[1]["root"] == 9
    assert eng.replay_state["done"] and eng.replay_state["played"] == 6


def test_a_rolled_chord_is_one_chord_event():
    eng = V.Engine(http_port=None, say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        for k in (60, 67, 64):                     # C, then G (a C5 power chord for 10 ms), then E
            eng.feed_midi("midi", NOTE_ON, k, 90)
            time.sleep(0.01)
        assert _wait(lambda: any(e["t"] == "chord" for e in seen), 1)
        time.sleep(0.1)
    finally:
        eng.stop()
    assert [e["name"] for e in seen if e["t"] == "chord"] == ["C"]


def test_note_schedule_ends_a_restruck_note_before_the_new_one():
    sched = V.note_schedule([(0.0, 1.0, 60, 100), (0.5, 1.5, 60, 90)])
    assert [(round(t, 3), st, k) for t, st, k, _v in sched] == [
        (0.0, NOTE_ON, 60), (0.499, NOTE_OFF, 60), (0.5, NOTE_ON, 60), (1.5, NOTE_OFF, 60)]


def _varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def _flp(patterns, ppq=96, tempo=None):
    """A tiny FL project: the FLhd header, then FLdt with (optional tempo) + per pattern: 65 (new pattern) and
    224 (24-byte note records)."""
    ev = b""
    if tempo:
        ev += bytes([156]) + struct.pack("<I", int(tempo * 1000))
    for pid, notes in patterns.items():
        ev += bytes([65]) + struct.pack("<H", pid)
        recs = b"".join(struct.pack("<IHHIHHBBBBBBBB", pos, 0x4000, 0, ln, key, 0, 120, 0, 64, 0, 64, vel, 128, 128)
                        for pos, ln, key, vel in notes)
        ev += bytes([224]) + _varint(len(recs)) + recs
    return b"FLhd" + struct.pack("<I", 6) + struct.pack("<hHH", 0, 1, ppq) + b"FLdt" + struct.pack("<I", len(ev)) + ev


def test_flp_pattern_notes_replay_at_the_project_tempo(tmp_path):
    path = tmp_path / "song.flp"
    path.write_bytes(_flp({1: [(0, 96, 60, 100), (96, 48, 64, 128)]}, ppq=96, tempo=120.0))
    rp = V.load_replay(path)
    assert rp.bpm == 120.0 and rp.patterns == [(1, None, 2)]
    assert rp.notes == [(0.0, 0.5, 60, 99), (0.5, 0.75, 64, 127)]


def test_flp_defaults_to_the_newest_pattern_and_its_largest_stretch(tmp_path):
    """A score-log project: older dumps first; the newest pattern holds a short noodle, a gap of more than 8 beats,
    then the big take -- the take is what replays."""
    big = [(96 * 20 + 48 * i, 40, 61, 90) for i in range(30)]
    path = tmp_path / "log.flp"
    path.write_bytes(_flp({2: [(0, 96, 48, 90)] * 50, 7: [(0, 96, 60, 80), (96, 96, 62, 80)] + big}))
    rp = V.load_replay(path)
    assert "pattern 7" in rp.label and "stretch 2/2" in rp.label and len(rp.notes) == 30
    assert rp.bpm == V.DEFAULT_REPLAY_BPM and rp.notes[0][0] == 0.0
    assert [s["notes"] for s in rp.stretches] == [2, 30]
    assert len(V.load_replay(path, stretch=0).notes) == 32
    assert len(V.load_replay(path, pattern=2).notes) == 50


def test_a_score_log_json_with_ppq_replays_in_beats(tmp_path):
    path = tmp_path / "joy.json"
    path.write_text(json.dumps({"ppq": 96, "notes": [{"pos": 960, "len": 96, "key": 61, "vel": 64},
                                                     {"pos": 1056, "len": 48, "key": 65, "vel": 128}]}))
    rp = V.load_replay(path)
    assert [(k, v) for _a, _b, k, v in rp.notes] == [(61, 64), (65, 127)]
    assert [x for a, b, _k, _v in rp.notes for x in (a, b)] == pytest.approx([0.0, 0.6, 0.6, 0.9])  # 0.6 s a beat


# --- the beat clock, the hits, the pads ------------------------------------------------------------------------

def test_beat_clock_announces_each_beat_once_and_ahead():
    src = V.SynthSource(rate=RATE, bpm=120.0, chords=("C",), realtime=False, seconds=12)
    clk = V.BeatClock(RATE, V.HOP, "a", ahead_s=0.25)
    t, landed = 0.0, []
    while True:
        b = src.read()
        if b is None:
            break
        t += len(b) / RATE
        a = clk.feed(b)
        if a:
            assert -0.03 <= a["lead_s"] <= 0.25
            landed.append(t + a["lead_s"])
    gaps = np.diff(landed)
    assert len(landed) >= 15 and np.all(np.abs(gaps - 0.5) < 0.03)
    phase = np.array(landed[-8:]) % 0.5
    assert np.all(np.minimum(phase, 0.5 - phase) < 0.03), "beats land on the kicks"


def test_rate_limit_keeps_hits_to_three_in_any_second():
    rate = RATE
    x = np.zeros(rate * 4, dtype=np.float32)
    rng = np.random.default_rng(3)
    for k in range(int(4 * 8)):                                 # a full-band hit every 125 ms
        i = int(k * 0.125 * rate)
        n = int(0.03 * rate)
        x[i:i + n] += rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / (0.008 * rate))
    for limited in (False, True):
        ana = V.Analyzer(rate, V.HOP, rate_limit=limited)
        t, hits = 0.0, []
        for k in range(0, len(x) - V.HOP + 1, V.HOP):
            t += V.HOP / rate
            hits += [t for e in ana.feed(x[k:k + V.HOP], t) if e["t"] == "hit"]
        worst = max(sum(1 for h in hits if s <= h < s + 1.0) for s in hits)
        if limited:
            assert worst <= 3
        else:
            assert worst > 3, "without the limit the detector should keep up with 8 hits a second"


def test_energy_is_dark_in_silence_and_bass_leads_on_a_bass_note():
    ana = V.Analyzer(RATE, V.HOP)
    t = np.arange(RATE * 2) / RATE
    bass = (0.5 * np.sin(2 * np.pi * 55 * t)).astype(np.float32)
    out, tt = [], 0.0
    for x in (bass, np.zeros(RATE, dtype=np.float32)):
        for k in range(0, len(x) - V.HOP + 1, V.HOP):
            tt += V.HOP / RATE
            out += [(tt, e) for e in ana.feed(x[k:k + V.HOP], tt) if e["t"] == "energy"]
    loud = [e for ts, e in out if 1.0 < ts < 2.0]
    quiet = [e for ts, e in out if ts > 2.8]                    # the release fades out, then it is dark
    assert all(e["bass"] > e["high"] for e in loud)
    assert all(e[k] == 0.0 for e in quiet for k in ("bass", "mid", "high", "level"))
    rate_hz = len(out) / tt
    assert 30 <= rate_hz <= 60


class _PausingDevice:
    """Like the WASAPI loopback (measured 2026-10-23): read() hands over one block per block period while something
    plays and BLOCKS for the whole pause while nothing does."""

    def __init__(self, play_s=0.4, pause_s=0.8, then_s=0.4):
        self.rate, self.name = RATE, "pausing device"
        self.dur = V.HOP / RATE
        self.plan = [("play", int(play_s / self.dur)), ("pause", pause_s), ("play", int(then_s / self.dur))]
        self.t0 = None
        self.k = 0

    def read(self):
        if self.t0 is None:
            self.t0 = time.perf_counter()
        while self.plan:
            kind, n = self.plan[0]
            if kind == "pause":
                self.plan.pop(0)
                time.sleep(n)
                self.t0 += n
                continue
            if n <= 0:
                self.plan.pop(0)
                continue
            self.plan[0] = (kind, n - 1)
            self.k += 1
            wait = self.t0 + self.k * self.dur - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            return np.full(V.HOP, 0.25, dtype=np.float32)
        return None

    def close(self):
        pass


def test_idle_fill_keeps_the_clock_running_through_a_pause_in_real_time():
    src = V.IdleFill(_PausingDevice(), grace_s=0.1)
    t0 = time.perf_counter()
    kinds = []
    while True:
        b = src.read()
        if b is None:
            break
        kinds.append("s" if not b.any() else "p")
    wall = time.perf_counter() - t0
    covered = len(kinds) * V.HOP / RATE + src.gap_s
    assert src.filled > 0 and "s" in "".join(kinds) and kinds[-1] == "p"
    assert abs(covered - wall) < 0.1, f"blocks + grace should cover the wall time: {covered:.3f} vs {wall:.3f}"
    assert src.gap_s == pytest.approx(0.1) and src.dropped == 0


class _CountingOut:
    """Stands in for winmidi.MidiOut on the painter's path: the painter only ever calls send_sysex."""

    def __init__(self):
        self.packets = []

    def send_sysex(self, data):
        self.packets.append(bytes(data))


def test_pads_route_lights_the_daw_bank_and_state_reports_it():
    port = _free_port()
    out = _CountingOut()
    eng = V.Engine(http_port=port, led_out=out, say=_quiet).start()
    try:
        colors = ["#ff0000"] * 6 + ["#0000ff"] * 6
        status, resp, body = _post_json(port, "/api/pads", {"colors": colors})
        assert status == 202 and body["ok"] is True
        assert resp.getheader("Access-Control-Allow-Origin") == "*"
        assert _wait(lambda: len(out.packets) >= 12, 3)
        ids = sorted(p[9] for p in out.packets[:12])
        assert ids == list(range(82, 94)), "the DAW bank (ids 82-93)"
        assert out.packets[0] == P.set_led(82, (255, 0, 0))
        _post_json(port, "/api/pads", {"colors": colors})       # the same frame again: nothing new on the wire
        time.sleep(0.2)
        assert len(out.packets) == 12
        assert _post_json(port, "/api/pads", {"colors": ["#ff0000"] * 3})[0] == 400
        assert _post_json(port, "/api/pads", {"colors": ["nope"] * 12})[0] == 400
        st, _r, state = _get_json(port, "/api/state")
        assert st == 200 and state["leds"]["enabled"] is True and state["src"] == "keylab-vj"
        assert {"bpm", "chord", "inputs", "audio", "clients", "beat_n"} <= set(state)
    finally:
        eng.stop()
    assert out.packets[-12:] != [] and all(p[10:13] == b"\x00\x00\x00" for p in out.packets[-12:]), "pads off on stop"


def test_pads_route_refuses_when_leds_are_off_and_answers_preflight():
    port = _free_port()
    eng = V.Engine(http_port=port, say=_quiet).start()
    try:
        status, _r, body = _post_json(port, "/api/pads", {"colors": ["#000000"] * 12})
        assert status == 409 and body["ok"] is False and "no-leds" in body["refused"]
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("OPTIONS", "/api/pads", headers={"Origin": "http://127.0.0.1:8793",
                                                   "Access-Control-Request-Method": "POST"})
        r = c.getresponse()
        r.read()
        assert r.status == 204 and r.getheader("Access-Control-Allow-Origin") == "*"
        assert "POST" in r.getheader("Access-Control-Allow-Methods")
        c.close()
    finally:
        eng.stop()


def test_a_pad_seen_on_both_inputs_counts_once_and_pads_mode_filters():
    eng = V.Engine(http_port=None, say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        eng.feed_midi("daw", 0x99, 0, 100)                     # pad 1, DAW mode
        eng.feed_midi("midi", 0x99, 44, 100)                   # pad 1 again on the bank input, same instant
        eng.feed_midi("daw", 0x89, 0, 0)
        eng.feed_midi("midi", 0x89, 44, 0)
        assert _wait(lambda: len([e for e in seen if e["t"] == "pad"]) >= 2, 1)
        time.sleep(0.05)
    finally:
        eng.stop()
    pads = [(e["pad"], e["on"], e["src"]) for e in seen if e["t"] == "pad"]
    assert pads == [(1, True, "daw"), (1, False, "daw")]

    only_bank = V.Engine(http_port=None, pads_mode="bank", say=_quiet)
    seen2 = _collect(only_bank)
    only_bank.start()
    try:
        only_bank.feed_midi("daw", 0x99, 5, 100)
        only_bank.feed_midi("midi", 0x99, 36, 100)             # note 36 = pad 9
        assert _wait(lambda: any(e["t"] == "pad" for e in seen2), 1)
        time.sleep(0.05)
    finally:
        only_bank.stop()
    assert [(e["pad"], e["src"]) for e in seen2 if e["t"] == "pad"] == [(9, "bank")]


def test_flat_spelling_for_the_page():
    assert V.spell("C#maj7/G#") == "Dbmaj7/Ab" and V.spell("F#m") == "F#m" and V.spell("A#m7") == "Bbm7"


def test_vj_verb_is_registered():
    from arsenal.keylab.__main__ import build_parser
    args = build_parser().parse_args(["vj", "--port", "8901", "--no-leds", "--rate-limit", "--replay-audio", "demo"])
    assert args.verb == "vj" and args.port == 8901 and args.no_leds and args.rate_limit
    assert args.engine == "a" and args.replay_audio == "demo" and args.loop is False
    assert args.chords == "blend"
    assert build_parser().parse_args(["vj", "--chords", "basic"]).chords == "basic"
    assert build_parser().parse_args(["vj", "--chords", "sense"]).chords == "sense"


# --- chordsense in the engine (--chords sense, the default) ------------------------------------------------------------
# The music it is for: hardstyle (a kick and a LOW sub bass, fundamentals 40-65 Hz, under supersaw chords) and worship
# piano (block chords under a held pedal note). Everything here is synthesized in the test.

def _f0(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _hardstyle(prog=((57, "m"), (53, ""), (48, ""), (55, "")), bpm=150.0, bars=3, seed=3):
    """A minor i-VI-III-VII: supersaw chords (five detuned saws a tone), a sine sub bass on each root with its
    fundamental inside 40-65 Hz, a pitched kick on every beat. -> (float32 mono, [(t0, t1, root pc)])."""
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    seg = 4 * beat
    n_seg = len(prog) * bars
    t = np.arange(int(n_seg * seg * RATE)) / RATE
    x = np.zeros(len(t))
    truth = []
    for k in range(n_seg):
        root, q = prog[k % len(prog)]
        i0, i1 = int(k * seg * RATE), int((k + 1) * seg * RATE)
        tt = t[i0:i1]
        env = np.minimum(1, (tt - tt[0]) / 0.02) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.02)
        for m in (root + 12, root + 12 + (3 if q == "m" else 4), root + 19):
            for v in range(5):
                f = _f0(m) * 2 ** ((v - 2) * 0.06 / 12)
                ph = rng.uniform(0, 2 * np.pi)
                for h in range(1, 20):
                    x[i0:i1] += 0.07 * env * np.sin(2 * np.pi * h * f * tt + h * ph) / h
        b = 24 + root % 12
        while _f0(b) > 65.5:
            b -= 12
        x[i0:i1] += 0.5 * env * np.sin(2 * np.pi * _f0(b) * tt)
        truth.append((k * seg, (k + 1) * seg, root % 12))
    for kb in range(int(n_seg * 4)):
        i0 = int(kb * beat * RATE)
        i1 = min(len(t), i0 + int(0.3 * RATE))
        d = t[i0:i1] - t[i0]
        x[i0:i1] += 0.8 * np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(50 + 130 * np.exp(-d / 0.03)) / RATE)
                                  * np.exp(-d / 0.18))
    return (0.8 * x / np.abs(x).max()).astype(np.float32), truth


def _run_audio(tmp_path, x, chords="sense", realtime=False, timeout=60.0):
    import soundfile as sf
    wav = tmp_path / "music.wav"
    sf.write(str(wav), x, RATE)
    eng = V.Engine(http_port=None, source=V.FileSource(wav, realtime=realtime), chords=chords, say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for e in seen), timeout)
        st = eng.state()
    finally:
        eng.stop()
    return eng, seen, st


CHORD_FIELDS = {"t", "src", "name", "root", "quality", "pcs", "changed", "bass", "roman", "key", "conf"}


def test_the_engine_publishes_chord_key_and_tension_from_a_synthesized_audio_replay(tmp_path):
    x, truth = _hardstyle()
    eng, seen, st = _run_audio(tmp_path, x)
    assert eng.hello()["chords"] == "sense" and st["chords"] == "sense"
    chords = [e for e in seen if e["t"] == "chord"]
    keys = [e for e in seen if e["t"] == "key"]
    tensions = [e for e in seen if e["t"] == "tension"]
    assert chords and keys and tensions, {e["t"] for e in seen}
    for c in chords:                                     # the contract: to_vj_events' chord, spelled for the page
        assert set(c) == CHORD_FIELDS and c["src"] == "audio" and c["changed"] is True, c
        assert 0.0 <= c["conf"] <= 1.0
        if c["root"] is None:
            assert c["name"] == "N" and c["pcs"] == [] and c["roman"] is None
        else:
            assert 0 <= c["root"] < 12 and c["root"] in c["pcs"] and c["bass"] in c["pcs"]
            assert "#" not in c["name"].split("/")[0][:2] or c["name"].startswith("F#")      # the page's flats
    # the harmony is heard: the roots played (A F C G) are the roots named
    named = [c["root"] for c in chords if c["root"] is not None]
    assert len(named) >= 6 and sum(r in (9, 5, 0, 7) for r in named) >= 0.8 * len(named), named
    # the key: one the page can parse, the relative pair of what was played; every chord after it is read in it
    for k in keys:
        assert set(k) == {"t", "name", "conf", "src"} and V.parse_key(k["name"]) and 0 <= k["conf"] <= 1
        assert k["src"] == "audio"
    assert keys[0]["name"] in ("A minor", "C major"), keys
    key_now = None
    for e in seen:
        if e["t"] == "key":
            key_now = e["name"]
        elif e["t"] == "chord" and key_now and e["root"] is not None:
            assert e["key"] == key_now and e["roman"] == V.roman_in(e["root"], e["quality"], e["bass"], key_now), e
    assert any(c["roman"] for c in chords)
    for tv in tensions:
        assert set(tv) == {"t", "value", "pedal_pc", "src"} and 0.0 <= tv["value"] <= 1.0 and tv["src"] == "audio"
        assert tv["pedal_pc"] is None or 0 <= tv["pedal_pc"] < 12
    assert st["key"] == keys[-1]["name"] and st["harmony"]["key"] == keys[-1]["name"]
    assert st["harmony"]["errors"] == 0 and st["audio"]["timing"]["sense_ms"]["blocks"] == st["audio"]["blocks"]


def test_chords_basic_still_works_and_sends_no_key_or_tension(tmp_path):
    x, _truth = _hardstyle(bars=2)
    eng, seen, st = _run_audio(tmp_path, x, chords="basic")
    assert eng.hello()["chords"] == "basic" and st["chords"] == "basic" and st["harmony"] is None
    chords = [e for e in seen if e["t"] == "chord"]
    assert [c["name"] for c in chords][:4] == ["Am", "F", "C", "G"], [c["name"] for c in chords]
    assert all(set(c) == {"t", "src", "name", "root", "quality", "pcs", "changed", "conf"} for c in chords)
    assert not any(e["t"] in ("key", "tension") for e in seen)
    assert st["audio"]["timing"]["sense_ms"] is None and st["audio"]["chord_analysis"]["best"]


def test_chords_blend_names_with_the_templates_and_keys_and_tensions_with_chordsense(tmp_path):
    """The default: under a kick and a sub bass the older templates name the audio chords best (59 % exact against
    chordsense's 38 % on a hardstyle render, 2026-10-23), so they name them, each with its roman numeral in the key
    chordsense tells the page; chordsense's own audio chords are not published, its key and tension are."""
    x, _truth = _hardstyle(bars=2)
    eng, seen, st = _run_audio(tmp_path, x, chords="blend")
    assert eng.hello()["chords"] == "blend" and st["chords"] == "blend" and st["harmony"] is not None
    chords = [e for e in seen if e["t"] == "chord"]
    assert [c["name"] for c in chords][:4] == ["Am", "F", "C", "G"], [c["name"] for c in chords]
    basic = {"t", "src", "name", "root", "quality", "pcs", "changed", "conf"}
    assert all(set(c) == basic | {"roman", "key"} and c["src"] == "audio" for c in chords), chords
    keys = [e for e in seen if e["t"] == "key"]
    assert keys and any(e["t"] == "tension" for e in seen)
    assert keys[0]["name"] in ("A minor", "C major"), keys
    key_now = None
    for e in seen:
        if e["t"] == "key":
            key_now = e["name"]
        elif e["t"] == "chord" and key_now:
            assert e["key"] == key_now and e["roman"] == V.roman_in(e["root"], e["quality"], None, key_now), e
    assert any(c["roman"] for c in chords)
    assert st["audio"]["chord_analysis"]["best"] and st["harmony"]["errors"] == 0


def test_chord_names_are_spelled_by_the_key_they_are_read_in():
    """By scale degree, not by a fixed flats rule: the iii chord of E major is G#m (not Abm), the borrowed bVII of C
    major is Bb (not A#); the suffix and a slash bass are kept, the bass re-spelled too."""
    assert V.spell_in_key("Abm", 8, "m", "E major") == "G#m"
    assert V.spell_in_key("Dbm7", 1, "m7", "A major") == "C#m7"
    assert V.spell_in_key("A#", 10, "maj", "C major") == "Bb"
    assert V.spell_in_key("F#", 6, "maj", "Db major") == "Gb"
    assert V.spell_in_key("Ab/C", 8, "maj", "Eb major") == "Ab/C"
    assert V.spell_in_key("Am", 9, "m", None) is None                 # no key: the caller keeps its own spelling
    assert V.spell_in_key("N", None, None, "C major") is None
    assert V.spell_in_key("Am", 4, "m", "C major") is None            # the name's root is not the event's root
    h = V.Harmony(rate=None)
    h._key["audio"] = ("E major", 0.8)
    out = h.decorate({"t": "chord", "src": "audio", "name": "Abm", "root": 8, "quality": "m", "pcs": [8, 11, 3],
                      "changed": True}, 0.0)
    assert out["name"] == "G#m" and out["key"] == "E major" and out["roman"] == "iii", out


def test_hello_and_the_summary_advertise_the_chord_engine():
    assert V.Engine(http_port=None, say=_quiet).hello()["chords"] == "blend"      # the default
    for mode in ("blend", "sense", "basic"):
        eng = V.Engine(http_port=None, chords=mode, say=_quiet)
        assert eng.hello()["chords"] == mode and f"chords {mode}" in eng.summary()
        assert eng.greeting()[0]["chords"] == mode
    with pytest.raises(ValueError):
        V.Engine(http_port=None, chords="magic", say=_quiet)


def test_the_audio_loop_reads_every_block_in_real_time_with_chordsense_on(tmp_path):
    """The audio loop never blocks: paced like a device, every block is read, the capture timing record (wall time vs
    sample time, beatsync.capture_timing) shows no gap, and chordsense's share of a block stays far under the block."""
    x, _truth = _hardstyle(bars=1)                          # 6.4 s
    eng, seen, st = _run_audio(tmp_path, x, realtime=True, timeout=20.0)
    a = st["audio"]
    want = int(np.ceil(len(x) / V.HOP))
    assert a["blocks"] == want and a["dropped_s"] == 0.0
    cap = a["timing"]["capture"]
    assert cap["samples"] == want * V.HOP and cap["gap"] is False and abs(cap["unexplained_gap_ms"]) < 20.0, cap
    assert a["behind_s"] < 0.05 and a["late_blocks"] <= 2, a
    block_ms = 1000.0 * V.HOP / RATE
    sm = a["timing"]["sense_ms"]
    assert sm["blocks"] == want and sm["p99"] < 0.5 * block_ms, sm
    assert any(e["t"] == "chord" for e in seen)


def test_the_keys_name_chords_as_today_and_chordsense_adds_key_roman_and_tension():
    """Held piano chords keep today's names (theory, after the 30 ms settle: exact, and ~45 ms from the attack where
    chordsense's notes path takes ~180 ms); chordsense gives the key, each chord's numeral and the tension; where the
    keys' reading has no name (a C7 under a held D-flat), chordsense's chord is sent instead."""
    prog = [(1, (0, 4, 7)), (6, (0, 4, 7)), (8, (0, 4, 7)), (10, (0, 3, 7))]
    notes, t = [], 0.0
    for _rep in range(3):
        for root, iv in prog:
            lh = 36 + root if root >= 4 else 48 + root
            for k in (lh, lh + 12) + tuple(60 + (root + i) % 12 for i in iv):
                notes.append((t, t + 1.45, k, 90))
            t += 1.5
    t_c7 = t
    for k in (48, 60, 64, 67, 70, 73):                     # C7, and D-flat 5 held over it: no name for theory
        notes.append((t, t + 2.5, k, 90))
    ev = V.replay_events(V.Replay(notes, "worship"))
    chords = [(tt, e) for tt, e in ev if e["t"] == "chord"]
    played = [(tt, e) for tt, e in chords if tt < t_c7]
    assert [e["name"] for _tt, e in played] == ["Db", "Gb", "Ab", "Bbm"] * 3
    assert all(abs((tt + 1e-9) % 1.5 - V.CHORD_SETTLE_S) < 1e-6 for tt, _e in played)   # 30 ms after each attack
    assert all(e["src"] == "keys" and e["conf"] == 1.0 and set(e) == CHORD_FIELDS for _tt, e in played)
    keys = [(tt, e) for tt, e in ev if e["t"] == "key"]
    assert keys and keys[0][1]["name"] == "Db major" and keys[0][1]["src"] == "keys" and keys[0][0] < 6.0
    after = [e for tt, e in played if tt > keys[0][0]]
    assert [e["roman"] for e in after][-4:] == ["I", "IV", "V", "vi"] and all(e["key"] == "Db major" for e in after)
    tensions = [e for _tt, e in ev if e["t"] == "tension"]
    assert tensions and all(e["src"] == "keys" and 0 <= e["value"] <= 1 for e in tensions)
    c7 = [e for tt, e in chords if tt >= t_c7]
    assert c7 and c7[0]["root"] == 0 and c7[0]["src"] == "keys", c7


def test_the_page_is_told_one_key_the_keys_while_they_play_else_the_audio():
    h = V.Harmony(rate=RATE)
    key = lambda name, conf=0.8: {"type": "key", "t": 0.0, "src": "x", "key": name, "tonic": 0, "mode": "major",
                                   "confidence": conf}
    tension = lambda v, pc=None: {"type": "pedal", "t": 0.0, "src": "x", "pc": pc if pc is not None else 0,
                                  "on": pc is not None, "tension": v}
    out = h._take("audio", [key("C major")], 1.0)
    assert [(e["t"], e["name"], e["src"]) for e in out] == [("key", "C major", "audio")]
    h._struck = 100.0                                       # Daniel plays
    out = h._take("keys", [key("Db major", 0.6)], 100.0)
    assert [(e["name"], e["src"]) for e in out if e["t"] == "key"] == [("Db major", "keys")]
    assert h._take("audio", [key("G major")], 105.0) == []    # the speakers' key waits while the keys are the witness
    assert [e["value"] for e in h._take("audio", [tension(0.9)], 105.5) if e["t"] == "tension"] == []
    kt = h._take("keys", [tension(0.3, pc=1)], 106.0)
    assert [(e["value"], e["pedal_pc"], e["src"]) for e in kt] == [(0.3, 1, "keys")]
    back = h.refresh(110.5)                                 # 10.5 s since the last key: the audio speaks again
    assert [(e["t"], e.get("name"), e.get("value"), e["src"]) for e in back] == [("key", "G major", None, "audio"),
                                                                                 ("tension", None, 0.9, "audio")]
    assert h.refresh(111.0) == [] and h.snapshot()["key"] == "G major"
    # every chord is read in the key the page is told, whatever key the ear that heard it was in
    c = h.decorate({"t": "chord", "src": "audio", "name": "A#", "root": 10, "quality": "maj", "pcs": [2, 5, 10],
                    "bass": 10, "roman": "I", "key": "A# major", "conf": 0.5, "changed": True}, 111.0)
    assert c["key"] == "G major" and c["roman"] == V.roman_in(10, "maj", 10, "G major") == "bIII"
    assert c["name"] == "Bb"                                # the page's flats


@pytest.mark.parametrize("mode", ["sense", "blend"])
def test_a_chordsense_failure_stops_neither_the_audio_nor_the_keys(mode):
    def broken(*_a, **_k):
        raise RuntimeError("a chordsense that broke")

    src = V.SynthSource(rate=RATE, bpm=120.0, chords=("C",), realtime=False, seconds=3.0)
    eng = V.Engine(http_port=None, source=src, say=_quiet, chords=mode)
    eng.harmony.feed_audio = broken
    eng.harmony.tick = broken
    eng.harmony.note = broken
    eng.harmony.decorate = broken
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for e in seen), 30)
        eng.feed_midi("daw", 0x99, 3, 90)                  # the MIDI thread still runs (pads)
        for k in (60, 64, 67):
            eng.feed_midi("midi", NOTE_ON, k, 100)          # ... and today's keys chord still comes
        assert _wait(lambda: any(e["t"] == "pad" for e in seen)
                     and any(e["t"] == "chord" and e["src"] == "keys" for e in seen), 3)
        st = eng.state()
    finally:
        eng.stop()
    assert st["audio"]["blocks"] == int(np.ceil(3.0 * RATE / V.HOP)) and any(e["t"] == "energy" for e in seen)
    assert st["harmony"]["errors"] >= st["audio"]["blocks"]
    said = [e["msg"] for e in seen if e["t"] == "status" and "chordsense" in e["msg"]]
    assert said and len(said) <= 4 and "a chordsense that broke" in said[0]     # said, never a flood
    chords = [e for e in seen if e["t"] == "chord"]
    if mode == "sense":
        assert [e["name"] for e in chords] == ["C"]                      # today's keys chord
    else:                                                               # blend: the templates still name the audio
        assert {e["name"] for e in chords} == {"C"} and {e["src"] for e in chords} == {"audio", "keys"}, chords


def test_the_page_gets_the_key_and_tension_it_missed_when_it_connects():
    eng = V.Engine(http_port=None, say=_quiet)
    eng.harmony._take("keys", [{"type": "key", "t": 0, "src": "keys", "key": "Db major", "tonic": 1, "mode": "major",
                                "confidence": 0.7},
                               {"type": "pedal", "t": 0, "src": "keys", "pc": 1, "on": True, "tension": 0.4}], 0.0)
    kinds = [e["t"] for e in eng.greeting()]
    assert kinds[:4] == ["hello", "status", "key", "tension"]
    assert eng.state()["key"] == "Db major"


# --- the end-to-end findings (2026-10-23) ---------------------------------------------------------------------------
# 1. LED refusal spam: hello says whether the LEDs can light; 409 = turned off, 503 = no DAW output

def test_hello_says_whether_the_leds_can_light():
    on = V.Engine(http_port=None, led_out=_CountingOut(), say=_quiet).hello()
    off = V.Engine(http_port=None, say=_quiet).hello()
    assert on["leds"] is True and on["leds_reason"] is None
    assert off["leds"] is False and off["leds_reason"] == "LEDs are off (--no-leds)"


def test_pads_route_answers_503_when_there_is_no_daw_output():
    port = _free_port()
    eng = V.Engine(http_port=port, led_refusal="no KeyLab DAW output (not found)", led_refusal_status=503,
                   say=_quiet).start()
    try:
        status, _r, body = _post_json(port, "/api/pads", {"colors": ["#000000"] * 12})
        assert status == 503 and body["ok"] is False and body["refused"] == "no KeyLab DAW output (not found)"
        st = _get_json(port, "/api/state")[2]["leds"]
        assert st["enabled"] is False and st["refusal_status"] == 503
    finally:
        eng.stop()


def test_run_refuses_with_503_and_says_so_in_hello_when_the_daw_output_will_not_open(monkeypatch):
    from arsenal.keylab import winmidi as W

    def no_port(*_a, **_k):
        raise RuntimeError("no output port containing 'keylab'")

    made = {}

    class Spy(V.Engine):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            made["eng"] = self

    monkeypatch.setattr(W, "MidiOut", no_port)
    monkeypatch.setattr(V, "fl_running", lambda: None)
    monkeypatch.setattr(V, "line_buffered_stdout", lambda: None)
    monkeypatch.setattr(V, "Engine", Spy)
    assert V.run(port=_free_port(), leds=True, audio=False, midi=False, secs=0.2, quiet=True) == 0
    eng = made["eng"]
    assert eng.pads_request({"colors": ["#000000"] * 12})[0] == 503
    assert eng.hello()["leds"] is False and "no KeyLab DAW output" in eng.hello()["leds_reason"]


# 3. the zombie stream: a stopped engine serves nothing, not even on a kept-alive connection

def test_a_stopped_engine_serves_no_stream_on_a_kept_alive_connection():
    port = _free_port()
    eng = V.Engine(http_port=port, heartbeat_s=0.2, say=_quiet).start()
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    c.request("POST", "/api/pads", body=json.dumps({"colors": ["#000000"] * 12}), headers={"Content-Type": "text/plain"})
    r = c.getresponse()
    r.read()
    assert r.status == 409
    eng.stop()
    lines = []
    try:                                   # the same connection a browser would reuse for its next request
        c.request("GET", "/api/events")
        r = c.getresponse()
        end = time.perf_counter() + 1.0
        while time.perf_counter() < end:
            line = r.fp.readline() if r.fp else b""
            if not line:
                break
            lines.append(line)
    except (OSError, http.client.HTTPException):
        pass                               # refused or closed: nothing served, which is the point
    finally:
        c.close()
    assert not any(x.startswith(b"data:") or x.startswith(b": hb") for x in lines), lines


def test_short_routes_close_their_connection():
    port = _free_port()
    eng = V.Engine(http_port=port, say=_quiet).start()
    try:
        for method, path in (("GET", "/api/state"), ("GET", "/nope"), ("OPTIONS", "/api/pads")):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            c.request(method, path)
            r = c.getresponse()
            r.read()
            assert r.getheader("Connection") == "close", (method, path)
            c.close()
        status, r, _b = _post_json(port, "/api/pads", {"colors": ["#000000"] * 12})
        assert status == 409 and r.getheader("Connection") == "close"
    finally:
        eng.stop()


def test_a_closed_hub_refuses_new_streams():
    hub = V.Hub()
    hub.close()
    assert hub.subscribe() is None
    port = _free_port()
    eng = V.Engine(http_port=port, say=_quiet).start()
    try:
        eng.hub.close()                    # the moment between closing the hub and the server going away
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        c.request("GET", "/api/events")
        r = c.getresponse()
        body = r.read()
        c.close()
        assert r.status == 503 and b"data:" not in body
    finally:
        eng.stop()


def test_an_open_stream_ends_when_the_engine_stops():
    port = _free_port()
    eng = V.Engine(http_port=port, say=_quiet).start()
    sse = _SSE(port)
    try:
        assert sse.wait_for(lambda: sse.of("hello"), 5)
        t0 = time.perf_counter()
        eng.stop()
        sse._t.join(timeout=3)
        assert not sse._t.is_alive() and time.perf_counter() - t0 < 3
    finally:
        sse.close()


# 4. nits: line-buffered stdout, --loop, Gb in flat keys, an assumed replay tempo said out loud

def test_the_engine_console_arrives_while_it_runs_when_piped():
    port = _free_port()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    p = subprocess.Popen([sys.executable, "-m", "arsenal.keylab", "vj", "--no-leds", "--no-midi", "--no-audio",
                          "--port", str(port), "--secs", "10"], cwd=str(REPO), env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    lines: "queue.Queue[bytes]" = queue.Queue()
    threading.Thread(target=lambda: [lines.put(x) for x in iter(p.stdout.readline, b"")], daemon=True).start()
    got = []
    try:
        end = time.perf_counter() + 7
        while time.perf_counter() < end and not any(b"VJ engine:" in x for x in got):
            try:
                got.append(lines.get(timeout=0.2))
            except queue.Empty:
                pass
        running = p.poll() is None
    finally:
        p.kill()
        p.wait(10)
    assert any(b"VJ engine:" in x for x in got), got
    assert running, "the console line must arrive while the engine runs, not at exit"


def test_vj_loop_reaches_the_file_source(monkeypatch, tmp_path):
    from arsenal.keylab import __main__ as CLI
    got = {}
    monkeypatch.setattr(V, "run", lambda **kw: got.update(kw) or 0)
    assert CLI.main(["vj", "--replay-audio", "take.wav", "--loop", "--no-leds", "--port", "8901"]) == 0
    assert got["loop"] is True and got["replay_audio"] == "take.wav"

    import soundfile as sf
    wav = tmp_path / "short.wav"
    sf.write(str(wav), np.zeros(V.HOP * 3, dtype=np.float32), RATE)
    looped, once = V.FileSource(wav, realtime=False, loop=True), V.FileSource(wav, realtime=False)
    assert all(looped.read() is not None for _ in range(10))
    assert [once.read() is not None for _ in range(4)] == [True, True, True, False]
    looped.close()
    once.close()


def test_pitch_class_6_is_gb_in_a_flat_key_and_f_sharp_otherwise():
    assert V.spell("F#/C#", flats=True) == "Gb/Db" and V.spell("F#m7/C#") == "F#m7/Db"

    def play(scale, chord):
        eng = V.Engine(http_port=None, say=_quiet)
        seen = _collect(eng)
        eng.start()
        try:
            for k in scale:
                eng.feed_midi("midi", NOTE_ON, k, 100)
                eng.feed_midi("midi", NOTE_OFF, k, 0)
            for k in chord:
                eng.feed_midi("midi", NOTE_ON, k, 100)
            assert _wait(lambda: any(e["t"] == "chord" for e in seen), 2)
            time.sleep(0.05)
        finally:
            eng.stop()
        return [e["name"] for e in seen if e["t"] == "chord"][-1], eng.key.key()

    name, key = play([61, 63, 65, 66, 68, 70, 72, 73] * 2, (54, 58, 61))       # D-flat major, then G-flat major
    assert name == "Gb" and key[2] < 0, (name, key)
    name, key = play([62, 64, 66, 67, 69, 71, 73, 74] * 2, (54, 57, 61))       # D major, then F-sharp minor
    assert name == "F#m" and key[2] > 0, (name, key)

    eng = V.Engine(http_port=None, say=_quiet)
    plain = eng.audio_chord_seen({"t": "chord", "name": "F#", "root": 6, "pcs": [1, 6, 10]}, 0.0)
    assert plain["name"] == "F#"                                                 # no key yet: F#
    eng.key.add([61, 63, 65, 66, 68, 70, 72] * 2, 0.1)
    flat = eng.audio_chord_seen({"t": "chord", "name": "F#m", "root": 6, "pcs": [1, 6, 9]}, 0.2)
    assert flat["name"] == "Gbm" and eng.state()["key"] == "Db major"


def test_the_keys_decide_the_key_over_whatever_else_the_speakers_play():
    """A demo groove in C under a replay in D-flat left the key undecided (live run, 2026-10-23), so D-flat's Gb chords
    read F#: while the keys are playing, the audio's chords spell but do not vote."""
    eng = V.Engine(http_port=None, say=_quiet)
    t = 100.0
    for i, k in enumerate([61, 63, 65, 66, 68, 70, 72, 73] * 2):
        eng._handle("midi", NOTE_ON, k, 100, t + 0.1 * i)
        eng._handle("midi", NOTE_OFF, k, 0, t + 0.1 * i + 0.05)
    for j in range(6):
        eng.audio_chord_seen({"t": "chord", "name": "C", "root": 0, "pcs": [0, 4, 7]}, t + 2 + j)
    assert eng.key.name() == "Db major"
    assert eng.audio_chord_seen({"t": "chord", "name": "F#", "root": 6, "pcs": [1, 6, 10]}, t + 9)["name"] == "Gb"
    for j in range(12):                                    # the keys quiet for longer: the audio's chords count again
        eng.audio_chord_seen({"t": "chord", "name": "G", "root": 7, "pcs": [2, 7, 11]}, t + 30 + j)
        eng.audio_chord_seen({"t": "chord", "name": "D", "root": 2, "pcs": [2, 6, 9]}, t + 30.5 + j)
    assert eng.key.flats() is False


def test_a_replay_with_no_tempo_says_the_tempo_is_assumed(tmp_path):
    path = tmp_path / "take.json"
    path.write_text(json.dumps({"ppq": 96, "notes": [{"pos": 0, "len": 96, "key": 61, "vel": 64},
                                                     {"pos": 96, "len": 96, "key": 65, "vel": 64}]}))
    rp = V.load_replay(path)
    assert rp.tempo_known is False and rp.bpm == 100.0
    assert rp.label.endswith("2 notes, tempo unknown, assumed 100 BPM (--replay-bpm to set)"), rp.label
    timed = V.load_replay(path, bpm=120)
    assert timed.tempo_known and timed.label.endswith("2 notes at 120 BPM") and "unknown" not in timed.label
    eng = V.Engine(http_port=None, replay=rp, replay_delay=0.0, say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "replay done" for e in seen), 5)
    finally:
        eng.stop()
    said = [e["msg"] for e in seen if e["t"] == "status"]
    assert any("tempo unknown, assumed 100 BPM (--replay-bpm to set)" in m for m in said), said


# replay_events: the live replay's events, offline -- and the real take the page's pedal star is tested on

def test_replay_events_are_the_live_replays_events_on_a_simulated_clock(tmp_path):
    notes = [{"pos_s": 0.0, "key": k, "vel": 100, "len_s": 0.4} for k in (60, 64, 67)] + \
            [{"pos_s": 0.5, "key": k, "vel": 90, "len_s": 0.4} for k in (57, 60, 64)]
    path = tmp_path / "notes.json"
    path.write_text(json.dumps(notes), encoding="utf-8")
    ev = V.replay_events(V.load_replay(path))
    seq = [(t, e["t"], e["key"] if e["t"] == "note" else e["name"], e.get("on")) for t, e in ev if e["t"] in ("note", "chord")]
    assert seq == [(0.0, "note", 60, True), (0.0, "note", 64, True), (0.0, "note", 67, True),
                   (0.03, "chord", "C", None),
                   (0.4, "note", 60, False), (0.4, "note", 64, False), (0.4, "note", 67, False),
                   (0.5, "note", 57, True), (0.5, "note", 60, True), (0.5, "note", 64, True),
                   (0.53, "chord", "Am", None),
                   (0.9, "note", 57, False), (0.9, "note", 60, False), (0.9, "note", 64, False)]


@pytest.mark.skipif(not JOY.exists(), reason="Daniel's Joy take is kept out of the public repo (state/, gitignored)")
def test_the_joy_take_fixture_is_what_the_engine_sends_today():
    """tests/vj_core.test.mjs tunes the pedal star on this fixture; if the engine's events change (chord naming, the
    settle), regenerate it: py tests/fixtures/vj/make_joy_take.py <the take's notes>."""
    sys.path.insert(0, str(MAKE_JOY))
    try:
        import make_joy_take as M
    finally:
        sys.path.pop(0)
    doc = json.loads(JOY.read_text(encoding="utf-8"))
    rp = V.Replay([tuple(n) for n in doc["note_list"]], "joy")
    assert len(rp.notes) == doc["notes"] == 1378
    assert M.rows(V.replay_events(rp)) == doc["events"]
