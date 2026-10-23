"""Pins for arsenal/keylab/vj.py, the VJ engine (`py -m arsenal.keylab vj`).

No keyboard, no sound card: MIDI arrives through Engine.feed_midi exactly as the KeyLab input callback hands it
(kind, status, data1, data2), the audio is synthesized, and the LED output is a counting stand-in with the real
MidiOut's one method the painter calls (send_sysex). The HTTP server runs on a test-band port (8900-8999), never
on 8793 or 8794.
"""
from __future__ import annotations

import http.client
import json
import socket
import struct
import threading
import time

import numpy as np
import pytest

from arsenal.keylab import protocol as P
from arsenal.keylab import vj as V

RATE = 48000
NOTE_ON, NOTE_OFF, CC = 0x90, 0x80, 0xB0


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
    assert hello == {"t": "hello", "v": 1, "src": "keylab-vj", "beat_engine": "a", "pads_mode": "both"}
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
    seq = [(e["t"], e.get("key", e.get("name")), e.get("on")) for e in seen if e["t"] in ("note", "chord")]
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
    assert args.engine == "a" and args.replay_audio == "demo"
