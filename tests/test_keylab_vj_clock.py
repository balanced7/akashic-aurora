"""Pins for the VJ engine's beat clock (2026-10-24): the song database per track, the KeyLab's Tap button, and the new
beat-event fields. The build spec: research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-
2026-10-24.md, section 3 and receipt A3 (slice S1).

Daniel (verbatim): "it could be timed to the bpm of the track once its established from a database, I can also tap the
tempo button or the tap button to the right of record on the keylab".

No keyboard, no network, no sound card: the beat grid is driven on a virtual clock with a stand-in tracker; the engine
gets its taps through feed_midi exactly as the KeyLab input hands them over (CC 23 on the DAW port), its music from the
synthesized groove, and its now-playing and database lookup from stubs. HTTP stays off (http_port=None).
"""
from __future__ import annotations

import math
import time

import numpy as np
import pytest

from arsenal.keylab import beatgrid as G
from arsenal.keylab import vj as V
from arsenal.keylab.beathand import Hand, TapLog

RATE = 48000
BLOCK = V.HOP / RATE
P150 = 0.4                     # seconds per beat at 150 BPM
CC = 0xB0


def _quiet(_msg):
    pass


def ahead_at(now, phase0, period, conf=0.9, n=4):
    """A stand-in tracker's predict(): the next n beats after now on the grid phase0 + k * period."""
    k = math.floor((now - phase0) / period) + 1
    t = phase0 + k * period
    return [{"t_beat": t + i * period, "bpm": 60.0 / period, "phase": 0.0, "confidence": conf} for i in range(n)]


class Drive:
    """Steps a BeatGrid block by block on a virtual audio clock, as the engine's audio loop does."""

    def __init__(self, grid, tracker=None):
        self.grid, self.tracker, self.now = grid, tracker, 0.0
        self.beats = []                                    # (land time, announcement)

    def until(self, t_end, taps=(), silent_s=0.0):
        taps = sorted(taps)
        i = 0
        while self.now < t_end:
            self.now += BLOCK
            due = []
            while i < len(taps) and taps[i] <= self.now:
                due.append(taps[i])
                i += 1
            ahead = self.tracker(self.now) if self.tracker else []
            self.grid.step(self.now, ahead, due, silent_s)
            a = self.grid.announce(self.now)
            if a:
                self.beats.append((self.now + a["lead_s"], a))
        return self

    def after(self, t):
        return [(land, a) for land, a in self.beats if land > t]


def taps_of(mode, grid):
    return [n for n in grid.notes if n["t"] == "tap" and n["mode"] == mode]


def phase_err(t, phase0, period):
    return G.wrap((t - phase0) / period)


# --- receipt A3: tap and grid ---------------------------------------------------------------------------------------

def test_one_tap_on_a_kick_moves_an_off_beat_lock_onto_the_kicks_bumps_ver_and_marks_the_one():
    """The kicks fall on k * 0.4 s; the tracker is locked half a beat off (hardstyle's reverse bass sits there). One tap
    on a kick moves the lights onto the kicks, bumps ver once, and (tap_one) makes that kick the ONE."""
    grid = G.BeatGrid(tap_one=True)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.2, P150))
    d.until(4.0)
    before = d.beats[-1][1]
    assert before["src"] == "track" and before["bar"] == 0 and before["bar_src"] is None
    assert abs(phase_err(d.beats[-1][0], 0.0, P150)) > 0.45                  # on the off-beat
    d.until(12.0, taps=[4.005])
    after = d.after(4.3)
    assert after and all(a["src"] == "tap" for _t, a in after)
    assert all(abs(t - (round(t / P150) * P150)) < 0.015 for t, _a in after), "the lights sit on the kicks"
    assert {a["ver"] for _t, a in after} == {before["ver"] + 1}, "one hard re-anchor"
    first = after[0]
    assert first[1]["bar"] == (round((first[0] - 4.0) / P150) % 4) + 1 and first[1]["bar_src"] == "tap"
    ones = [t for t, a in after if a["bar"] == 1]
    assert ones and all(abs(((t - 4.0) / P150) % 4) < 0.05 or abs(((t - 4.0) / P150) % 4 - 4) < 0.05 for t in ones)
    rs = taps_of("resync", grid)
    assert len(rs) == 1 and abs(abs(rs[0]["shift"]) - 0.5) < 0.03
    assert any(n["t"] == "status" and "onto your tap" in n["msg"] for n in grid.notes)


def test_a_tap_three_hundredths_of_a_beat_off_changes_nothing():
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150))
    d.until(4.0)
    ver = grid.ver
    d.until(8.0, taps=[4.0 + 0.03 * P150])
    assert grid.owner == "track" and grid.ver == ver
    assert all(a["src"] == "track" for _t, a in d.after(4.0))
    assert all(abs(phase_err(t, 0.0, P150)) < 0.01 for t, _a in d.after(4.0))
    assert taps_of("resync", grid)[0]["shift"] == 0.0


def test_a_small_tap_error_slews_the_beat_half_way():
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150))
    d.until(4.0)
    d.until(5.0, taps=[4.0 + 0.1 * P150])                 # 0.1 of a beat late: move half way
    assert grid.owner == "hand" and taps_of("resync", grid)[0]["shift"] == pytest.approx(0.05, abs=1e-6)
    t, a = d.after(4.2)[0]
    assert a["src"] == "tap" and phase_err(t, 0.0, P150) == pytest.approx(0.05, abs=0.002)


def test_four_taps_at_150_4_bpm_with_the_database_at_150_give_exactly_150_on_the_taps():
    grid = G.BeatGrid()
    grid.set_db(150.0)
    d = Drive(grid)                                       # no tracker at all: the hand alone
    taps = [4.0 + k * 60.0 / 150.4 for k in range(4)]
    d.until(8.0, taps=taps)
    after = d.after(taps[-1] + 0.01)
    assert after and all(a["bpm"] == 150.0 and a["src"] == "tap" for _t, a in after)
    assert all(abs(phase_err(t, 4.0, P150)) * P150 < 0.015 for t, _a in after), "phase within 15 ms"
    assert grid.tap_how == "db" and taps_of("lock", grid)[0]["bpm"] == 150.0
    assert [n["mode"] for n in grid.notes if n["t"] == "tap"][:4] == ["resync", "run", "run", "lock"]
    assert any(n["t"] == "status" and n["msg"].startswith("tap-lock") and "database" in n["msg"] for n in grid.notes)


def test_tap_tempo_rounds_to_a_whole_bpm_unless_told_to_keep_it_exact():
    taps = [4.0 + k * 60.0 / 143.3 for k in range(6)]
    for round_bpm, want in ((True, 143.0), (False, 143.3)):
        grid = G.BeatGrid(round_bpm=round_bpm)
        Drive(grid).until(7.0, taps=taps)
        assert grid.tap_bpm == pytest.approx(want, abs=0.05) and grid.tap_how == "tap"


def test_tapped_tempo_snaps_to_a_confident_tracker_within_four_percent():
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150, conf=0.8))
    taps = [4.0 + k * 60.0 / 151.0 for k in range(5)]
    d.until(7.0, taps=taps)
    assert grid.tap_bpm == pytest.approx(150.0) and grid.tap_how == "track"


def test_half_time_taps_keep_the_songs_tempo_and_land_on_beats():
    grid = G.BeatGrid()
    grid.set_db(150.0)
    d = Drive(grid)
    taps = [4.0 + k * 0.8 for k in range(5)]              # tapping every other kick (75 BPM)
    d.until(9.0, taps=taps)
    after = d.after(taps[-1] + 0.01)
    assert grid.tap_bpm == 150.0 and all(a["bpm"] == 150.0 for _t, a in after)
    assert all(abs(phase_err(t, 4.0, P150)) < 0.01 for t, _a in after)


def test_after_the_taps_stop_the_hand_holds_32_beats_against_an_off_beat_tracker():
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.2, P150))
    d.until(4.0)
    taps = [4.0 + k * P150 for k in range(6)]
    d.until(taps[-1] + 36 * P150, taps=taps)
    held = d.after(taps[-1] + 3 * P150)
    assert len(held) >= 32
    assert all(a["src"] == "tap" for _t, a in held), "the tracker never takes over"
    assert all(abs(phase_err(t, 0.0, P150)) < 0.01 for t, _a in held)
    assert taps_of("release", grid) and not taps_of("return", grid)
    assert any(n["t"] == "status" and n["msg"].startswith("taps stopped") for n in grid.notes)


def test_a_tracker_that_agrees_for_8_beats_takes_the_beat_back_without_a_jump():
    state = {"phase0": 0.2}                               # off-beat first; at 8 s it re-locks near the kicks
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, state["phase0"], P150))
    d.until(4.0)
    d.until(8.0, taps=[4.0])
    assert grid.owner == "hand"
    ver = grid.ver
    state["phase0"] = 0.02                                # 0.05 of a beat after the kicks
    d.until(20.0)
    assert grid.owner == "track" and taps_of("return", grid)
    landed = [t for t, _a in d.after(8.0)]
    gaps = np.diff(landed)
    assert np.all(np.abs(gaps - P150) <= 0.1 * P150), f"a jump over 10 % of a beat: {gaps}"
    assert grid.ver == ver, "no hard re-anchor on the way back"
    assert d.beats[-1][1]["src"] == "track"
    assert any(n["t"] == "status" and "tracker agrees" in n["msg"] for n in grid.notes)


def test_the_hand_follows_the_trackers_tempo_while_it_holds_the_phase():
    """Holding: the tracker refines the tempo (150 -> 151 BPM here) and the hand's phase against it holds."""
    state = {"period": P150}
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.2, state["period"]))
    d.until(4.0)
    d.until(5.0, taps=[4.0])
    state["period"] = 60.0 / 151.0
    d.until(15.0)
    tail = d.after(10.0)
    assert all(a["src"] == "tap" and a["bpm"] == pytest.approx(151.0, abs=0.01) for _t, a in tail)
    # still half a beat from the tracker's beats (where the hand put it), not drifted
    tr = [ahead_at(t - 0.001, 0.2, state["period"])[0]["t_beat"] for t, _a in tail]
    assert all(abs(abs(G.wrap((t - x) / state["period"])) - 0.5) < 0.03 for (t, _a), x in zip(tail, tr))


def test_silence_and_a_new_track_hand_the_beat_back():
    for how in ("silence", "track"):
        grid = G.BeatGrid(tap_one=True)
        d = Drive(grid, tracker=lambda now: ahead_at(now, 0.2, P150))
        d.until(4.0)
        d.until(5.0, taps=[4.0])
        assert grid.owner == "hand"
        if how == "silence":
            d.until(6.0, silent_s=3.5)
            assert grid.owner == "hand", "the tap was in the silence: it holds until 3 s after it (round 1)"
            d.until(7.1, silent_s=3.5)
        else:
            grid.new_track()
            assert grid.bar_ref is None and grid.db_bpm is None
        assert grid.owner == "track" and taps_of("return", grid)


def test_eight_taps_at_a_tempo_the_tracker_disagrees_with_ask_for_one_reseed_in_15_s():
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, 0.5, conf=0.9))      # the tracker says 120
    run1 = [4.0 + k * 60.0 / 137.0 for k in range(8)]
    d.until(9.0, taps=run1)
    assert [n for n in grid.notes if n["t"] == "reseed"] == [{"t": "reseed", "bpm": 137.0}]
    run2 = [10.0 + k * 60.0 / 137.0 for k in range(8)]
    d.until(15.0, taps=run2)
    assert len([n for n in grid.notes if n["t"] == "reseed"]) == 1, "at most one re-seed in 15 s"


def test_three_taps_do_not_lock_and_unsteady_taps_never_do():
    grid = G.BeatGrid()
    Drive(grid).until(6.0, taps=[4.0, 4.4, 4.8])
    assert not grid.locked and not taps_of("lock", grid)
    grid = G.BeatGrid()
    Drive(grid).until(8.0, taps=[4.0, 4.4, 4.62, 5.3, 5.45, 6.0])
    assert not grid.locked


def test_db_source_is_named_only_while_the_tracker_agrees_with_the_database():
    grid = G.BeatGrid()
    grid.set_db(150.0)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150))
    d.until(3.0)
    assert d.beats and all(a["src"] == "db" for _t, a in d.beats)
    grid.set_db(128.0)
    d.until(6.0)
    assert d.beats[-1][1]["src"] == "track"


# --- the database tempo's octave --------------------------------------------------------------------------------

def test_restore_octave_gives_back_the_tempo_the_databases_said():
    from arsenal.keylab import tempo as T
    assert T.fuse_bpm([T.SourceBpm("deezer", 150.0)]).bpm == 75.0          # the fusion folds into 70-140
    assert G.restore_octave(75.0, [150.0, 150.0]) == 150.0
    assert G.restore_octave(74.9, [74.9]) == 74.9
    assert G.restore_octave(87.0, [174.0, 87.0, 174.0]) == 174.0
    assert G.restore_octave(110.0, [220.0]) == 110.0                        # kept inside the tracker's 60-200
    assert G.restore_octave(0.0, [150.0]) == 0.0 and G.restore_octave(75.0, []) == 75.0


def test_database_tempo_and_the_beat_commands_seed_keep_the_octave(monkeypatch):
    from arsenal.keylab import beatsync as BS
    from arsenal.keylab import tempo as T
    monkeypatch.setattr(T, "lookup", lambda artist, title, offline=False: [T.SourceBpm("deezer", 150.0, 0.4, 0.3),
                                                                           T.SourceBpm("getsongbpm", 150.0)])
    got = G.database_tempo("Artist", "Title")
    assert got["bpm"] == 150.0 and got["sources"] == ["deezer", "getsongbpm"] and 0 < got["confidence"] <= 1
    assert BS._seed_for({"artist": "Artist", "title": "Title", "status": 4}, offline=False) == 150.0
    monkeypatch.setattr(T, "lookup", lambda artist, title, offline=False: [])
    assert G.database_tempo("Artist", "Title") is None


# --- the clock in the engine: BeatClock ----------------------------------------------------------------------------

def _synth(bpm, secs, realtime=False):
    return V.SynthSource(rate=RATE, bpm=bpm, chords=("C",), realtime=realtime, seconds=secs)


class _StubReferee:
    """The referee's interface (predicted, feed, verdict, pred) with a fixed verdict."""

    def __init__(self, on_beat, offset_ms):
        from collections import deque
        self.pred = deque()
        self.v = {"state": "ok", "on_beat": on_beat, "offset_ms": offset_ms, "consistency": 0.9}

    def predicted(self, beats):
        pass

    def feed(self, block):
        pass

    def verdict(self):
        return dict(self.v)


def test_on_beat_is_no_longer_clamped_a_negative_score_reaches_the_beat():
    clk = V.BeatClock(RATE, V.HOP, "a")
    clk.ref = _StubReferee(-0.8, -190.0)
    src = _synth(120.0, 8.0)
    got = []
    while (b := src.read()) is not None:
        a = clk.feed(b)
        if a:
            got.append(a)
    late = [a for a in got if a["n"] > 3]
    assert late and late[-1]["on_beat"] == -0.8 and late[-1]["offset_ms"] == -190.0
    clk.ref = _StubReferee(-1.4, 0.0)
    clk.next_verdict = 0.0
    clk.feed(np.zeros(V.HOP, dtype=np.float32))
    assert clk.on_beat == -1.0


def test_a_reseed_never_stops_the_beat_and_an_agreeing_tracker_is_left_alone():
    clk = V.BeatClock(RATE, V.HOP, "a")
    src = _synth(120.0, 30.0)
    landed = []
    t = 0.0
    reseeded_at = None
    while (b := src.read()) is not None:
        t += BLOCK
        a = clk.feed(b)
        if a:
            landed.append(t + a["lead_s"])
        if reseeded_at is None and t >= 8.0:
            assert clk.bpm == pytest.approx(120.0, abs=2.0)
            assert clk.reseed(121.0) is False, "the tracker already agrees: left alone"
            assert clk.reseed(100.0) is True and clk.shadow is not None
            reseeded_at = t
    assert clk.reseeds == 1 and clk.shadow is None
    assert any(n["t"] == "status" and "re-seeded at 100 BPM" in n["msg"] for n in clk.notes)
    during = [x for x in landed if reseeded_at - 1.0 < x < reseeded_at + 6.0]
    assert np.max(np.diff(during)) < 1.0, "no beat stopped while the new tracker warmed up (a restart: about 2 s)"


def test_beat_clock_taps_put_the_beats_on_the_taps():
    """BeatClock with the real tracker: taps a quarter beat off the groove's kicks take the beat over (src tap)."""
    clk = V.BeatClock(RATE, V.HOP, "a")
    src = _synth(120.0, 16.0)
    taps = [6.125 + k * 0.5 for k in range(6)]
    t, i, got = 0.0, 0, []
    while (b := src.read()) is not None:
        t += BLOCK
        while i < len(taps) and taps[i] <= t:
            clk.tap(taps[i])
            i += 1
        a = clk.feed(b)
        if a:
            got.append((t + a["lead_s"], a))
    after = [(x, a) for x, a in got if x > taps[-1] + 0.1]
    assert after and all(a["src"] == "tap" for _x, a in after)
    assert all(abs(G.wrap((x - 6.125) / 0.5)) * 0.5 < 0.03 for x, _a in after)
    assert any(n.get("mode") == "lock" for n in clk.notes if n["t"] == "tap")


# --- the engine: the Tap button, the track thread, the event ---------------------------------------------------

def _collect(eng):
    seen = []
    eng.hub.tap(lambda e: seen.append((time.perf_counter(), e)))
    return seen


def _wait(pred, timeout):
    end = time.perf_counter() + timeout
    while time.perf_counter() < end and not pred():
        time.sleep(0.02)
    return pred()


def test_parse_tap():
    assert V.parse_tap("daw:cc23") == [("daw", "cc23")]
    assert V.parse_tap("cc23, midi:pad12,pads") == [(None, "cc23"), ("midi", "pad12"), (None, "pads")]
    assert V.parse_tap("off") == [] and V.parse_tap(None) == [] and V.parse_tap("") == []
    for bad in ("cc200", "pad13", "pad0", "knob3", "daw:"):
        with pytest.raises(ValueError):
            V.parse_tap(bad)
    with pytest.raises(ValueError):
        V.Engine(http_port=None, tap="cc999", say=_quiet)


def test_the_tap_button_counts_a_press_once_and_ignores_releases_and_other_ports():
    eng = V.Engine(http_port=None, say=_quiet)
    t = 100.0
    eng._handle("daw", CC, 23, 127, t)                    # a press
    eng._handle("daw", CC, 23, 0, t + 0.05)               # its release
    eng._handle("daw", CC, 23, 127, t + 0.06)             # a bounce inside 80 ms of the press
    eng._handle("midi", CC, 23, 127, t + 0.5)             # the same CC on the keys port: not the Tap button
    eng._handle("daw", CC, 23, 127, t + 0.6)              # the next press
    eng._handle("daw", CC, 23, 127, t + 0.7)              # a press-only repeat inside 250 ms: the same press
    eng._handle("daw", CC, 23, 127, t + 1.0)              # a press-only control's next press
    assert list(eng._tap_q) == [t, t + 0.6, t + 1.0] and eng.taps_seen == 3
    off = V.Engine(http_port=None, say=_quiet, tap="off")
    off._handle("daw", CC, 23, 127, t)
    assert not off._tap_q
    pads = V.Engine(http_port=None, say=_quiet, tap="pads")
    seen = []
    pads.hub.tap(seen.append)
    pads._handle("daw", 0x99, 1, 100, t)                  # DAW-mode pad 2
    assert list(pads._tap_q) == [t] and seen[-1]["t"] == "pad" and seen[-1]["pad"] == 2, "a pad still fires"


def test_engine_taps_on_cc23_take_the_beat_and_the_audio_loop_reads_every_block():
    """Live-paced groove at 120 BPM; the Tap button pressed six times a quarter beat after the kicks: the beat moves
    onto the taps (tap events, the tap-lock status line, src tap), the ctl events still arrive, and the audio loop reads
    every block on time."""
    secs = 9.0
    eng = V.Engine(http_port=None, source=_synth(120.0, secs, realtime=True), say=_quiet)
    seen = _collect(eng)
    eng.start()
    try:
        t0 = time.perf_counter()
        assert _wait(lambda: any(e["t"] == "beat" for _ts, e in seen), 6.0)
        # the groove's kicks land at t0 + k * 0.5 (the paced source started with the engine): tap a quarter beat late
        first = t0 + math.ceil((time.perf_counter() - t0) / 0.5 + 1) * 0.5 + 0.125
        taps = [first + k * 0.5 for k in range(6)]
        for tp in taps:
            while time.perf_counter() < tp:
                time.sleep(0.0005)
            eng.feed_midi("daw", CC, 23, 127)
            time.sleep(0.03)
            eng.feed_midi("daw", CC, 23, 0)
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for _ts, e in seen), secs + 5)
        st = eng.state()
    finally:
        eng.stop()
    modes = [e["mode"] for _ts, e in seen if e["t"] == "tap"]
    assert modes[:4] == ["resync", "run", "run", "lock"] and modes.count("lock") == 3, modes
    assert any(e["t"] == "status" and e["msg"].startswith("tap-lock") for _ts, e in seen)
    assert sum(1 for _ts, e in seen if e["t"] == "ctl" and e["id"] == "cc23") == 12
    beats = [(ts + e["due_ms"] / 1000.0, e) for ts, e in seen if e["t"] == "beat"]
    after = [(x, e) for x, e in beats if taps[-1] + 0.1 < x < taps[-1] + 2.0]
    assert after and all(e["src"] == "tap" for _x, e in after), [e["src"] for _x, e in after]
    assert all(abs(G.wrap((x - taps[-1]) / 0.5)) * 0.5 < 0.03 for x, _e in after), "the lights land on the taps"
    a = st["audio"]
    want = int(np.ceil(secs * RATE / V.HOP))
    assert a["blocks"] == want and a["late_blocks"] <= 2 and a["timing"]["capture"]["gap"] is False, a
    assert st["clock"]["taps_seen"] == 6 and st["clock"]["tap"] == "daw:cc23,daw:pad12"


def test_pad_12_taps_take_the_beat_by_default_and_the_first_tap_is_the_one():
    """Daniel, 2026-10-25: pad 12 taps the VJ engine's tempo too, by default, and the first tap of a run marks the ONE.
    Live-paced groove at 120 BPM; DAW-mode pad 12 hit six times a quarter beat after the kicks: the beat moves onto the
    taps (tap-lock, src tap), the beats then carry the bar with bar 1 on the first tap's beat, and the pad events still
    go out (the page knows from the hello that pad 12 taps and fires nothing for it)."""
    secs = 9.0
    eng = V.Engine(http_port=None, source=_synth(120.0, secs, realtime=True), say=_quiet)
    assert eng.hello()["tap"] == "daw:cc23,daw:pad12" and eng.hello()["tap_one"] is True
    seen = _collect(eng)
    eng.start()
    try:
        t0 = time.perf_counter()
        assert _wait(lambda: any(e["t"] == "beat" for _ts, e in seen), 6.0)
        first = t0 + math.ceil((time.perf_counter() - t0) / 0.5 + 1) * 0.5 + 0.125
        taps = [first + k * 0.5 for k in range(6)]
        for tp in taps:
            while time.perf_counter() < tp:
                time.sleep(0.0005)
            eng.feed_midi("daw", 0x99, 11, 100)          # DAW-mode pad 12
            time.sleep(0.03)
            eng.feed_midi("daw", 0x89, 11, 0)
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for _ts, e in seen), secs + 5)
        st = eng.state()
    finally:
        eng.stop()
    modes = [e["mode"] for _ts, e in seen if e["t"] == "tap"]
    assert modes[:4] == ["resync", "run", "run", "lock"], modes
    assert sum(1 for _ts, e in seen if e["t"] == "pad" and e["pad"] == 12 and e["on"]) == 6, "the pad events still go out"
    beats = [(ts + e["due_ms"] / 1000.0, e) for ts, e in seen if e["t"] == "beat"]
    after = [(x, e) for x, e in beats if taps[-1] + 0.1 < x < taps[-1] + 2.0]
    assert after and all(e["src"] == "tap" for _x, e in after), [e["src"] for _x, e in after]
    assert all(abs(G.wrap((x - taps[-1]) / 0.5)) * 0.5 < 0.03 for x, _e in after), "the lights land on the taps"
    # the ONE: the first tap's beat is bar 1, so a beat a whole number of bars after it is bar 1 again
    for x, e in after:
        k = round((x - taps[0]) / 0.5)
        assert e["bar"] == (k % 4) + 1, (k, e["bar"])
    assert st["clock"]["taps_seen"] == 6


class _NowPlaying:
    """Windows' now-playing, as a script: a list of (seconds from the first poll, {"artist", "title"} or None)."""

    def __init__(self, script):
        self.script, self.t0 = script, None

    def __call__(self):
        if self.t0 is None:
            self.t0 = time.perf_counter()
        el = time.perf_counter() - self.t0
        cur = None
        for at, np_ in self.script:
            if el >= at:
                cur = np_
        return None if cur is None else {**cur, "status": 4}


def test_the_track_thread_looks_up_each_track_once_and_the_database_tempo_reaches_the_beats():
    lookups = []

    def lookup(artist, title):
        lookups.append(title)
        return {"bpm": 120.0, "confidence": 1.0, "sources": ["stub"]} if title == "One" else None

    np_fn = _NowPlaying([(0.0, None), (0.3, {"artist": "Someone", "title": "One"}),
                         (3.5, {"artist": "Someone", "title": "Two"})])
    eng = V.Engine(http_port=None, source=_synth(120.0, 6.0, realtime=True), say=_quiet, now_playing=np_fn,
                   db_lookup=lookup, track_poll_s=0.05)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for _ts, e in seen), 12)
        st = eng.state()
    finally:
        eng.stop()
    assert lookups == ["One", "Two"], "each track looked up once, however often it is polled"
    tracks = [e for _ts, e in seen if e["t"] == "track"]
    assert tracks == [{"t": "track", "bpm_db": 120.0, "key_db": None}, {"t": "track", "bpm_db": None, "key_db": None}]
    msgs = [e["msg"] for _ts, e in seen if e["t"] == "status"]
    assert "database tempo 120 BPM for Someone - One (stub)" in msgs
    assert "no database tempo for Someone - Two: the tracker finds the tempo" in msgs
    i1 = next(i for i, (_ts, e) in enumerate(seen) if e["t"] == "track")
    i2 = [i for i, (_ts, e) in enumerate(seen) if e["t"] == "track"][1]
    during = [e for _ts, e in seen[i1:i2] if e["t"] == "beat"]
    assert during and during[-1]["src"] == "db", "the tracker agrees with the database: src db"
    after = [e for _ts, e in seen[i2:] if e["t"] == "beat"]
    assert after and all(e["src"] == "track" for e in after[1:]), "a new track forgets the old database tempo"
    assert st["clock"]["track"]["title"] == "Someone - Two" and st["clock"]["track"]["lookups"] == 2
    assert st["clock"]["db_lookup"] is True and st["clock"]["db_bpm"] is None


def test_seed_bpm_holds_the_launch_track_and_a_disagreeing_database_reseeds_later_tracks():
    np_fn = _NowPlaying([(0.0, {"artist": "A", "title": "Launch"}), (2.0, {"artist": "A", "title": "Next"})])
    eng = V.Engine(http_port=None, source=_synth(120.0, 4.0, realtime=True), say=_quiet, seed_bpm=120.0,
                   now_playing=np_fn, db_lookup=lambda a, t: {"bpm": 90.0, "sources": ["stub"]}, track_poll_s=0.05)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for _ts, e in seen), 10)
    finally:
        eng.stop()
    msgs = [e["msg"] for _ts, e in seen if e["t"] == "status"]
    assert "database tempo 90 BPM for A - Launch (stub); --seed-bpm 120 holds this track" in msgs
    warm = [m for m in msgs if "warming up a tracker seeded at 90 BPM" in m]
    assert len(warm) == 1, msgs                            # the next track: the tracker (at 120) disagrees with 90


def test_no_track_thread_without_now_playing_and_a_replay_never_looks_up(monkeypatch):
    eng = V.Engine(http_port=None, source=_synth(120.0, 0.5), say=_quiet)
    eng.start()
    try:
        assert all(t.name != "vj-track" for t in eng._threads)
    finally:
        eng.stop()
    got = {}

    class _Eng(V.Engine):
        def __init__(self, **kw):
            got.update(kw)
            raise SystemExit(0)

    monkeypatch.setattr(V, "Engine", _Eng)
    with pytest.raises(SystemExit):
        V.run(port=8901, leds=False, replay_audio="demo", midi=False)
    assert got["now_playing"] is None and got["db_lookup"] is None
    assert got["tap"] == "daw:cc23,daw:pad12" and got["tap_one"] is True and got["tap_round"] is True


def test_the_verb_takes_the_clock_flags(monkeypatch):
    from arsenal.keylab import __main__ as CLI
    got = {}
    monkeypatch.setattr(V, "run", lambda **kw: got.update(kw) or 0)
    assert CLI.main(["vj", "--no-leds", "--port", "8901", "--tap", "daw:cc23,pad12", "--tap-one", "--tap-exact",
                     "--no-db"]) == 0
    assert got["tap"] == "daw:cc23,pad12" and got["tap_one"] is True and got["tap_round"] is False
    assert got["db"] is False
    got.clear()
    assert CLI.main(["vj", "--no-leds", "--port", "8901"]) == 0
    assert got["tap"] == "daw:cc23,daw:pad12" and got["tap_one"] is True and got["tap_round"] is True and got["db"] is True
    got.clear()
    assert CLI.main(["vj", "--no-leds", "--port", "8901", "--no-tap-one"]) == 0
    assert got["tap_one"] is False and got["tap"] == "daw:cc23,daw:pad12"


def test_the_default_launch_taps_on_the_tap_button_and_pad_12_and_the_first_tap_is_the_one():
    """Daniel, 2026-10-25: the Tap button (CC 23) and pad 12 both tap the VJ engine's tempo, the first tap of a run marks
    the ONE, and that is the engine's default launch; the hello names the tap controls so the page fires no effect for
    pad 12 while it taps."""
    assert V.DEFAULT_TAP == "daw:cc23,daw:pad12"
    eng = V.Engine(http_port=None, say=_quiet)
    assert eng.tap_one is True
    hello = eng.hello()
    assert hello["tap"] == "daw:cc23,daw:pad12" and hello["tap_one"] is True
    t = 10.0
    seen = []
    eng.hub.tap(seen.append)
    eng._handle("daw", 0x99, 11, 100, t)                 # DAW-mode pad 12 (note 11)
    assert list(eng._tap_q) == [t], "pad 12 on the DAW port taps"
    assert seen[-1]["t"] == "pad" and seen[-1]["pad"] == 12, "its pad event still goes out (the page knows it taps)"
    eng._handle("daw", 0x89, 11, 0, t + 0.05)
    eng._handle("daw", CC, 23, 127, t + 0.5)             # the Tap button
    assert list(eng._tap_q) == [t, t + 0.5]
    eng._handle("daw", 0x99, 0, 100, t + 1.0)            # DAW-mode pad 1: not a tap
    assert list(eng._tap_q) == [t, t + 0.5]
    off = V.Engine(http_port=None, say=_quiet, tap="off", tap_one=False)
    assert off.hello()["tap"] == "off" and off.hello()["tap_one"] is False


# --- beathand: the math moved into TapLog, Hand keeps it ----------------------------------------------------------

def test_taplog_is_the_hands_math_with_no_port():
    assert issubclass(Hand, TapLog)
    log = TapLog()
    for k in range(6):
        log.add(1.0 + k * 0.4)
    assert log.tap_tempo(5) == pytest.approx(0.4)
    nxt, per = log.tap_grid(3.1)
    assert per == pytest.approx(0.4) and nxt == pytest.approx(3.4)
    anchor, rms = log.tap_phase(0.4)
    assert anchor == pytest.approx(1.0) and rms == pytest.approx(0.0, abs=1e-9)
    assert log.versus([1.0 + k * 0.4 - 0.02 for k in range(6)], 0.4)["offset_ms"] == pytest.approx(20.0, abs=0.5)
    log.prune(20.0)
    assert log.taps == []


# --- round 1 fixes: the verifier's repros (2026-10-24) -----------------------------------------------------------
# Each of these failed on the lane's first build (afba3841) and passes after the fix; the verifier's numbers are quoted.

def _kick_err_ms(t, period, phase0=0.0):
    """How far a beat lands from the nearest kick of a groove whose kicks fall on phase0 + k * period, in ms."""
    return abs(G.wrap((t - phase0) / period)) * period * 1000.0


@pytest.mark.parametrize("bpm", [150.0, 180.0])
def test_four_taps_with_the_first_60_ms_off_put_the_lights_back_on_the_kicks(bpm):
    """MUST FIX 1 (the verifier's pytest): 4 taps, the first one 60 ms off, the tracker on the kicks, the database right
    or absent. Before: the tap-lock fit kept the outlier (157 BPM on a 150 groove) and, once the taps stopped, the
    hand's grid ran free at that tempo: about 100 ms median error 30-60 s later. Now the outlier is dropped, the tempo
    snaps, and the lights are on the kicks within a few beats and stay there."""
    p = 60.0 / bpm
    for db in (bpm, None):
        for e_ms in (60.0, -60.0):
            grid = G.BeatGrid()
            grid.set_db(db)
            d = Drive(grid, tracker=lambda now, p=p: ahead_at(now, 0.0, p))
            d.until(4.0)
            taps = [4.0 + e_ms / 1000.0] + [4.0 + k * p for k in range(1, 4)]
            d.until(taps[-1] + 60.0, taps=taps)
            assert grid.tap_bpm == pytest.approx(bpm, abs=0.01), (db, e_ms, grid.tap_bpm)
            late = [t for t, _a in d.after(taps[-1] + 4 * p)]
            assert late and max(_kick_err_ms(t, p) for t in late) < 5.0, (db, e_ms)


def test_the_first_tap_error_sweep_never_leaves_the_lights_drifting():
    """The verifier's sweep: 4, 6 and 8 taps at 150 and 180 BPM, the first tap -60..+80 ms off, the tracker on the kicks
    and the database right. Before: from 60 ms off (4 taps) the lights drifted for good. Now: on the kicks 30-60 s on."""
    for bpm in (150.0, 180.0):
        p = 60.0 / bpm
        for ntaps in (4, 6, 8):
            for e_ms in (-60, -40, -25, 25, 40, 60, 80):
                grid = G.BeatGrid()
                grid.set_db(bpm)
                d = Drive(grid, tracker=lambda now, p=p: ahead_at(now, 0.0, p))
                d.until(4.0)
                taps = [4.0 + e_ms / 1000.0] + [4.0 + k * p for k in range(1, ntaps)]
                d.until(taps[-1] + 60.0, taps=taps)
                late = [t for t, _a in d.beats if taps[-1] + 30.0 < t < taps[-1] + 60.0]
                assert late and max(_kick_err_ms(t, p) for t in late) < 5.0, (bpm, ntaps, e_ms, grid.tap_bpm)


def test_the_hand_alone_drops_an_outlier_tap_from_the_tempo():
    """No tracker, no database: the first tap 0.3 of a beat off (the verifier's R1 size) is dropped, with 4, 6 or 8
    taps, and the lights run at 150 on the other taps (before: 134-166). With nothing to check against, a smaller miss
    at the end of 4 taps (60 ms) is within what 20 ms of human jitter does there, so it stays in (the tracker's or the
    database's tempo catches that case: test_four_taps_with_the_first_60_ms_off...)."""
    for n in (4, 6, 8):
        for e in (0.3, -0.3):
            grid = G.BeatGrid()
            d = Drive(grid)
            taps = [4.0 + e * P150] + [4.0 + k * P150 for k in range(1, n)]
            d.until(taps[-1] + 20.0, taps=taps)
            assert grid.tap_bpm == 150.0 and grid.tap_how == "tap", (n, e, grid.tap_bpm)
            assert max(_kick_err_ms(t, P150, 4.0) for t, _a in d.after(taps[-1])) < 5.0


def test_jittered_human_taps_still_lock_on_the_beat():
    """A guard, not a repro: the outlier filter must not throw away good taps. 6 taps with 20 ms of human jitter (150
    seeds) at 150 BPM, the tracker on the kicks: every run locks at 150, and 8-12 beats after the last tap no beat is
    over 40 ms off the kicks (the verifier's receipt on the first build: 0 of 30 runs over 40 ms); p95 under 20 ms
    (the hand's phase from 6 taps of 20 ms jitter is good to about 8 ms, one sigma)."""
    import random
    errs = []
    for seed in range(150):
        rng = random.Random(seed)
        grid = G.BeatGrid()
        d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150))
        d.until(4.0)
        taps = [4.0 + k * P150 + rng.gauss(0, 0.020) for k in range(6)]
        d.until(taps[-1] + 12 * P150, taps=taps)
        assert taps_of("lock", grid) and grid.tap_bpm == 150.0, (seed, grid.tap_bpm)
        errs += [_kick_err_ms(t, P150) for t, _a in d.after(taps[-1] + 8 * P150)]
    errs.sort()
    assert errs[int(0.95 * (len(errs) - 1))] < 20.0 and errs[-1] < 40.0


def test_jittered_taps_with_only_the_database_stay_within_10_ms():
    """A guard: no tracker, the database right, 6 taps with 10 ms of jitter: p95 phase error under 10 ms (the
    verifier's receipt on the first build: 7.4 ms)."""
    import random
    errs = []
    for seed in range(150):
        rng = random.Random(seed)
        grid = G.BeatGrid()
        grid.set_db(150.0)
        d = Drive(grid)
        taps = [4.0 + k * P150 + rng.gauss(0, 0.010) for k in range(6)]
        d.until(taps[-1] + 8 * P150 + 0.3, taps=taps)
        assert grid.tap_bpm == 150.0
        errs += [_kick_err_ms(t, P150, 4.0) for t, _a in d.after(taps[-1] + 0.05)]
    errs.sort()
    assert errs[int(0.95 * (len(errs) - 1))] < 10.0


def test_snap_window_is_a_true_four_percent():
    """NOTE fixed: SNAP was compared with folded_ratio, which is in octaves, so the window was 2.8 %. Taps 3.3 % fast
    (155 BPM) on a database 150 now snap to 150."""
    grid = G.BeatGrid()
    grid.set_db(150.0)
    Drive(grid).until(8.0, taps=[4.0 + k * 60.0 / 155.0 for k in range(6)])
    assert grid.tap_bpm == 150.0 and grid.tap_how == "db"
    grid = G.BeatGrid()
    grid.set_db(150.0)
    Drive(grid).until(8.0, taps=[4.0 + k * 60.0 / 157.5 for k in range(6)])       # 5 %: the taps stand
    assert grid.tap_how == "tap"


def test_once_the_taps_stop_a_hand_five_percent_off_a_confident_tracker_follows_its_tempo():
    """MUST FIX 1, part two: after the taps stop, _hold ignored a tracker 4 % or more away (not octave-folded) and the
    hand's grid ran free at the wrong tempo. Steady taps at 157.5 against a confident tracker at 150: while tapping the
    lights follow the taps; once they stop, the hand's grid takes the tracker's tempo and no longer drifts."""
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150, conf=0.9))
    d.until(4.0)
    p_tap = 60.0 / 157.5
    taps = [4.0 + k * p_tap for k in range(6)]
    d.until(taps[-1] + 40.0, taps=taps)
    assert grid.tap_how == "tap"                          # 5 %: no snap while tapping
    late = d.after(taps[-1] + 20.0)
    assert all(a["bpm"] == pytest.approx(150.0, abs=0.01) for _t, a in late)
    errs = [_kick_err_ms(t, P150) for t, _a in late]
    assert max(errs) - min(errs) < 3.0, "no drift: the error stays put"


def test_a_database_that_sides_with_the_hand_keeps_a_wrong_tracker_out_of_the_hold():
    """The wider hold window is for a confident tracker the database does not contradict: the database says 157.5 and
    the hand tapped 157.5, so a tracker at 150 is not followed."""
    grid = G.BeatGrid(round_bpm=False)
    grid.set_db(157.5)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150, conf=0.9))
    d.until(4.0)
    p_tap = 60.0 / 157.5
    taps = [4.0 + k * p_tap for k in range(6)]
    d.until(taps[-1] + 20.0, taps=taps)
    assert grid.tap_how == "db"
    assert all(a["bpm"] == pytest.approx(157.5, abs=0.01) for _t, a in d.after(taps[-1] + 5.0))


def test_taps_at_double_a_half_time_reference_keep_the_tapped_octave():
    """MUST FIX 2: _snap compared octave-folded but returned the source's own BPM, so taps could not fix half time.
    The database says 75 (a hardstyle track folded to half), the hand taps 150: 150 (before: 75). A tracker at 90
    (confidence 0.95) and taps at 180: 180 (before: 89.98). Half-time taps on a database at 150 still give 150."""
    grid = G.BeatGrid()
    grid.set_db(75.0)
    d = Drive(grid)
    taps = [4.0 + k * P150 for k in range(6)]
    d.until(taps[-1] + 5.0, taps=taps)
    assert grid.tap_bpm == 150.0 and grid.tap_how == "db"
    assert all(a["bpm"] == 150.0 for _t, a in d.after(taps[-1]))
    p180 = 60.0 / 180.0
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, 2 * p180, conf=0.95))   # the tracker at 90
    d.until(4.0)
    taps = [4.0 + k * p180 for k in range(6)]
    d.until(taps[-1] + 30.0, taps=taps)
    assert grid.tap_bpm == pytest.approx(180.0) and grid.tap_how == "track"
    late = d.after(taps[-1] + 10.0)
    assert late and all(a["bpm"] == pytest.approx(180.0, abs=0.01) and a["src"] == "tap" for _t, a in late)
    assert max(_kick_err_ms(t, p180) for t, _a in late) < 3.0
    assert grid.owner == "hand", "a half-time tracker never takes the beat back"


# --- the same repros through the engine's clock with the real tracker (beat_a on the synthesized groove) ----------

def _run_clock(bpm, taps, secs, seed_bpm=None, db=None):
    clk = V.BeatClock(RATE, V.HOP, "a", seed_bpm=seed_bpm)
    if db:
        clk.grid.set_db(db)
    src = _synth(bpm, secs)
    t, i, got = 0.0, 0, []
    while (b := src.read()) is not None:
        t += BLOCK
        while i < len(taps) and taps[i] <= t:
            clk.tap(taps[i])
            i += 1
        a = clk.feed(b)
        if a:
            got.append((t + a["lead_s"], a))
    return clk, got


@pytest.mark.parametrize("bpm", [128.0, 150.0, 180.0])
def test_real_tracker_a_first_tap_three_tenths_of_a_beat_late_leaves_no_drift(bpm):
    """The verifier's R1: the real tracker on a groove, the first tap 0.3 of a beat late, then 5 good taps. Before: the
    lights locked at 134 on 128, 157 on 150, 188 on 180 and were still about 100 ms off 30-60 s later (owner hand)."""
    p = 60.0 / bpm
    k0 = math.ceil(10.0 / p) * p                          # a kick near 10 s (the groove's kicks fall on k * p)
    taps = [k0 + 0.3 * p] + [k0 + k * p for k in range(1, 6)]
    for db in (None, bpm):
        clk, got = _run_clock(bpm, taps, 50.0, db=db)
        late = [(x, a) for x, a in got if taps[-1] + 10.0 < x < taps[-1] + 40.0]
        errs = [_kick_err_ms(x, p) for x, _a in late]
        assert late and np.median(errs) < 15.0 and max(errs) < 30.0, (db, clk.grid.tap_bpm, np.median(errs))
        assert all(abs(a["bpm"] / bpm - 1.0) < 0.01 for _x, a in late), (db, late[-1][1]["bpm"])


def test_real_tracker_a_first_tap_a_fifth_of_a_beat_early_with_four_taps_leaves_no_drift():
    """The verifier's R3: 150 BPM, the first tap 0.2 of a beat early, 4 taps. Before: locked at 142, ~100 ms off."""
    taps = [10.0 - 0.2 * P150] + [10.0 + k * P150 for k in range(1, 4)]
    clk, got = _run_clock(150.0, taps, 50.0)
    late = [(x, a) for x, a in got if taps[-1] + 10.0 < x < taps[-1] + 40.0]
    errs = [_kick_err_ms(x, P150) for x, _a in late]
    assert late and np.median(errs) < 15.0 and max(errs) < 30.0, (clk.grid.tap_bpm, np.median(errs))


def test_real_tracker_reading_180_as_90_is_fixed_by_six_taps_at_180():
    """The verifier's R4: unseeded beat_a reads a 180 groove as 90.7 BPM (confidence 0.95). Six perfect taps at 180 gave
    tap_bpm 89.98 and the lights ran at 90. Now the lights run at 180, on the kicks, and stay there."""
    p = 60.0 / 180.0
    taps = [10.0 + k * p for k in range(6)]
    clk, got = _run_clock(180.0, taps, 40.0)
    late = [(x, a) for x, a in got if taps[-1] + 5.0 < x < taps[-1] + 25.0]
    assert late and all(abs(a["bpm"] / 180.0 - 1.0) < 0.01 for _x, a in late), clk.grid.tap_bpm
    assert len(late) / 20.0 == pytest.approx(3.0, abs=0.15), "every kick, not every other one"
    assert np.median([_kick_err_ms(x, p) for x, _a in late]) < 15.0


def test_real_tracker_seeded_at_half_time_is_overruled_by_taps_at_150():
    """The verifier's R2: a tracker seeded at 75 on a 150 groove; 6 or 10 taps at 150 gave 74.9 and the half-time
    tracker took the beat back. Now the lights stay at 150 on the kicks."""
    for n in (6, 10):
        taps = [10.0 + k * P150 for k in range(n)]
        clk, got = _run_clock(150.0, taps, 45.0, seed_bpm=75.0)
        late = [(x, a) for x, a in got if taps[-1] + 5.0 < x < taps[-1] + 30.0]
        assert late and all(abs(a["bpm"] / 150.0 - 1.0) < 0.01 for _x, a in late), (n, clk.grid.tap_bpm)
        assert len(late) / 25.0 == pytest.approx(2.5, abs=0.15)
        assert np.median([_kick_err_ms(x, P150) for x, _a in late]) < 15.0


# --- the NOTES fixed alongside ---------------------------------------------------------------------------------

def test_taps_during_silence_lock_once_instead_of_locking_and_returning_on_every_tap():
    """NOTE: from the 4th tap on, each tap in 3 s or more of silence locked and was handed straight back in the same
    block (8 taps gave 12 status lines and lock/return pairs). Now the taps take the beat, and silence hands it back
    only once it has been 3 s since the last tap."""
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150))
    d.until(4.0)
    taps = [4.0 + k * P150 for k in range(8)]
    d.until(taps[-1] + 0.1, taps=taps, silent_s=5.0)
    modes = [n["mode"] for n in grid.notes if n["t"] == "tap"]
    assert "return" not in modes and grid.owner == "hand", modes
    statuses = [n for n in grid.notes if n["t"] == "status"]
    assert len(statuses) <= 2, statuses
    d.until(taps[-1] + 3.5, silent_s=5.0)
    assert grid.owner == "track" and [n["mode"] for n in grid.notes if n["t"] == "tap"].count("return") == 1


def test_silence_forgets_the_tapped_bar():
    """NOTE: with --tap-one the bar reference survived the beat going back to the tracker after silence, so music
    returning on another phase stayed labelled bar_src "tap". Silence forgets it now."""
    grid = G.BeatGrid(tap_one=True)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.2, P150))
    d.until(4.0)
    d.until(5.0, taps=[4.0])
    assert grid.bar_ref is not None
    d.until(9.0, silent_s=3.5)
    assert grid.owner == "track" and grid.bar_ref is None
    assert d.beats[-1][1]["bar"] == 0 and d.beats[-1][1]["bar_src"] is None


def test_restore_octave_keeps_200_bpm():
    """NOTE: restore_octave folded anything at or above 200 down, so a 200 BPM database tempo seeded at 100; the
    tracker's range includes 200."""
    assert G.restore_octave(100.0, [200.0]) == 200.0
    assert G.restore_octave(105.0, [210.0]) == 105.0


def test_track_key_ignores_a_paused_media_session():
    """MUST FIX 3: a paused media session is still Windows' current session; only status 4 (Playing) is the track."""
    assert V.track_key({"artist": "A", "title": "T", "status": 4}) == ("a", "t")
    for status in (0, 1, 2, 3, 5):                        # closed, opened, changing, stopped, paused
        assert V.track_key({"artist": "A", "title": "T", "status": status}) is None, status
    assert V.track_key(None) is None and V.track_key({"artist": "A", "title": " ", "status": 4}) is None


def test_the_beat_commands_seed_ignores_a_paused_media_session(monkeypatch):
    from arsenal.keylab import beatsync as BS
    from arsenal.keylab import tempo as T
    monkeypatch.setattr(T, "lookup", lambda artist, title, offline=False: [T.SourceBpm("deezer", 150.0)])
    assert BS._seed_for({"artist": "A", "title": "T", "status": 4}, offline=False) == 150.0
    assert BS._seed_for({"artist": "A", "title": "T", "status": 5}, offline=False) is None


def test_a_paused_session_at_launch_seeds_nothing_until_it_plays():
    """MUST FIX 3 in the engine: a paused browser or Spotify session at launch was looked up and seeded the tracker
    with an unrelated song's tempo. Now nothing is looked up until a session is Playing."""
    lookups = []

    class _Np:
        def __init__(self):
            self.t0 = None

        def __call__(self):
            if self.t0 is None:
                self.t0 = time.perf_counter()
            el = time.perf_counter() - self.t0
            return {"artist": "Someone", "title": "Paused", "status": 5} if el < 1.0 else \
                {"artist": "Someone", "title": "Playing", "status": 4}

    def lookup(artist, title):
        lookups.append(title)
        return {"bpm": 100.0, "confidence": 1.0, "sources": ["stub"]}

    eng = V.Engine(http_port=None, source=_synth(120.0, 2.5, realtime=True), say=_quiet, now_playing=_Np(),
                   db_lookup=lookup, track_poll_s=0.05)
    seen = _collect(eng)
    eng.start()
    try:
        assert _wait(lambda: any(e["t"] == "status" and e["msg"] == "audio source ended" for _ts, e in seen), 10)
    finally:
        eng.stop()
    assert lookups == ["Playing"], lookups
    msgs = [e["msg"] for _ts, e in seen if e["t"] == "status"]
    assert not any("Paused" in m for m in msgs), msgs


def test_a_soft_pad_hit_counts_as_a_tap():
    """NOTE: with --tap pads, a pad hit softer than velocity 64 never counted (the CC threshold was applied to the
    velocity)."""
    eng = V.Engine(http_port=None, say=_quiet, tap="pads")
    eng._handle("daw", 0x99, 1, 30, 100.0)                # DAW-mode pad 2, played softly
    assert list(eng._tap_q) == [100.0]


def test_the_referee_judges_one_owner_at_a_time():
    """NOTE: the referee's prediction window was cleared only when a re-seeded tracker took over, so one verdict could
    mix the tracker's beats with the hand's. It is cleared when the hand takes or returns the beat too."""
    clk = V.BeatClock(RATE, V.HOP, "a")
    src = _synth(120.0, 8.0)
    t = 0.0
    while (b := src.read()) is not None:
        t += BLOCK
        if abs(t - 6.0) < BLOCK / 2:
            clk.tap(t + 0.2)                              # a tap far off the beat: the hand takes it
        clk.feed(b)
        if clk.grid.owner == "hand":
            break
    assert clk.grid.owner == "hand"
    hand = [h["t_beat"] for h in clk.grid.view(clk.audio_t)]
    preds = list(clk.ref.pred)
    assert preds and all(min(abs(p - h) for h in hand) < 1e-6 for p in preds), (preds, hand)


# --- round 2 fixes: the verifier's repros (2026-10-25) -----------------------------------------------------------
# Each of these failed on round 1 (c2f0fc9a) and passes after the fix; the verifier's numbers are quoted.

def wobbly_tracker(period, seed, phase0=0.0, jitter=0.015, wobble=0.02, conf=0.85):
    """A stand-in for beat_a on real hardstyle (the verifier's h11): its beats on the grid phase0 + k * period, each
    up to `jitter` s off, and its bpm field wobbling up to `wobble` from beat to beat (on Hard Driver's kick section
    beat_a's beats sit 12-18 ms RMS around a straight 154.14 line while its bpm field reads 147.7-156.5)."""
    import random
    rng = random.Random(seed)
    cache = {}

    def at(k):
        if k not in cache:
            cache[k] = (phase0 + k * period + rng.uniform(-jitter, jitter), period * (1 + rng.uniform(-wobble, wobble)))
        return cache[k]

    def ahead(now):
        k = math.floor((now - phase0) / period)
        out = []
        for i in range(6):
            t, per = at(k + i)
            if t > now:
                out.append({"t_beat": t, "bpm": 60.0 / per, "phase": 0.0, "confidence": conf})
        return out[:4]
    return ahead


@pytest.mark.parametrize("bpm", [150.0, 154.0])
def test_a_wobbly_tracker_takes_the_beat_back_after_perfect_taps(bpm):
    """FIX 1 (the verifier's h11): six perfect taps on a tracker whose beats are right (+-15 ms) but whose bpm field
    wobbles +-2 % beat to beat. Round 1: the hand followed only a tracker whose bpm field held within 0.5 % for 1.5 s,
    and gave the beat back only while following, so it kept the beat in 12 of 12 runs and the lights drifted (median
    32-97 ms, worst 200 ms). Now the tracker takes the beat back every time, and the lights are the tracker's beats
    (the first build: 8 ms median, 15 ms max)."""
    p = 60.0 / bpm
    for db in (None, bpm):
        for seed in range(4):
            grid = G.BeatGrid()
            grid.set_db(db)
            d = Drive(grid, tracker=wobbly_tracker(p, seed))
            k0 = math.ceil(8.0 / p) * p
            taps = [k0 + k * p for k in range(6)]
            d.until(taps[-1] + 40.0, taps=taps)
            assert grid.owner == "track" and taps_of("return", grid), (db, seed)
            errs = [_kick_err_ms(t, p) for t, _a in d.beats if taps[-1] + 10.0 < t < taps[-1] + 40.0]
            assert np.median(errs) < 12.0 and max(errs) < 20.0, (db, seed, np.median(errs), max(errs))


def test_against_an_off_beat_wobbly_tracker_the_hand_holds_its_beat_without_drifting():
    """FIX 1, the hold: the same wobbly tracker locked half a beat off, at a tempo that is not a whole BPM (154.14, as
    Hard Driver), no database. Perfect taps on the kicks; the hand keeps them for 40 s. Round 1 snapped the taps to one
    block's bpm field (+-2 %) and, the tracker never steady enough to follow, ran free on it: off the kicks within
    seconds. Now the hand follows the tracker's own beats at its line's tempo, half a beat from them, and stays on the
    kicks (within the tracker's own jitter)."""
    p = 60.0 / 154.14
    for seed in range(4):
        grid = G.BeatGrid()
        d = Drive(grid, tracker=wobbly_tracker(p, seed, phase0=0.5 * p))
        k0 = math.ceil(8.0 / p) * p
        taps = [k0 + k * p for k in range(6)]
        d.until(taps[-1] + 40.0, taps=taps)
        held = [t for t, a in d.beats if t > taps[-1] + 1.0]
        assert grid.owner == "hand" and not taps_of("return", grid), seed
        errs = [_kick_err_ms(t, p) for t in held]
        assert np.median(errs) < 12.0 and max(errs) < 30.0, (seed, np.median(errs), max(errs))      # jitter +-15 ms


def test_the_tap_lock_snaps_to_the_trackers_smoothed_tempo_not_its_bpm_field():
    """FIX 1 (c): with no database the lock snapped to the tracker's bpm field that block (153.41 or 152.63 on a
    154.14 line on Hard Driver). Now it snaps to the tempo of the tracker's beats themselves (its line, averaged):
    within 0.3 % of 154.14 for every seed, where the bpm field alone is up to 2 % off."""
    p = 60.0 / 154.14
    for seed in range(8):
        grid = G.BeatGrid()
        d = Drive(grid, tracker=wobbly_tracker(p, seed))
        k0 = math.ceil(8.0 / p) * p
        d.until(k0 + 6 * p, taps=[k0 + k * p for k in range(6)])
        assert grid.tap_how == "track" and abs(grid.tap_bpm / 154.14 - 1.0) < 0.003, (seed, grid.tap_bpm)


def test_the_trackers_line_is_steady_on_jitter_and_not_while_it_pulls_its_phase_in():
    """The steadiness the hold asks for: the line through the tracker's landed beats. 15 ms of jitter is steady; a
    tracker moving its phase 0.11 of a beat a beat (beat_a pulling in on a released hardstyle track) is not, though its
    beats lie close to a line; nor is a re-lock half a beat over until its old phase has left the window."""
    import random
    rng = random.Random(3)
    p = 0.4
    jit = [k * p + rng.uniform(-0.015, 0.015) for k in range(10)]
    ln = G.tracker_line(jit)
    assert ln.steady(p) and abs(ln.period / p - 1.0) < 0.01
    pull = [k * p for k in range(7)] + [k * p + 0.044 * (k - 6) for k in range(7, 10)]   # 0.11 of a beat a beat
    assert not G.tracker_line(pull).steady(p)
    jump = [k * p for k in range(6)] + [k * p + 0.2 for k in range(6, 10)]                # half a beat over
    assert not G.tracker_line(jump).steady(p)
    settled = [5 * p] + [k * p + 0.2 for k in range(6, 15)]                               # the old phase all but gone
    ln = G.tracker_line(settled)
    assert ln.steady(p) and abs(G.wrap((ln.t_last - 0.2) / p)) < 1e-6


def test_a_sloppy_first_tap_among_jittered_taps_locks_at_the_database_tempo():
    """FIX 2 (the verifier's h8): ordinary jitter on the other taps plus one sloppy first tap, [+82, -7, +3, -40] ms,
    the database right and a confident tracker on the kicks. Round 1 dropped the outlier against the database's grid,
    rejected the database because the three taps left sloped 4.3 % off it, then fitted its own line through all four
    taps, outlier and all: 165 BPM on a 150 groove (197 on 174), drifting for good. Now the window for three taps is
    what their jitter can put on the slope (11 % at 150): 150 (174), on the kicks."""
    offsets = [0.082, -0.007, 0.003, -0.040]
    for bpm in (150.0, 174.0):
        p = 60.0 / bpm
        grid = G.BeatGrid()
        grid.set_db(bpm)
        d = Drive(grid, tracker=lambda now, p=p: ahead_at(now, 0.0, p, conf=1.0))
        d.until(4.0)
        k0 = math.ceil(10.0 / p) * p
        taps = [k0 + k * p + e for k, e in enumerate(offsets)]
        d.until(taps[-1] + 75.0, taps=taps)
        assert grid.tap_bpm == bpm and grid.tap_how == "db", (bpm, grid.tap_bpm)
        late = [t for t, _a in d.beats if taps[-1] + 10.0 < t]
        assert max(_kick_err_ms(t, p) for t in late) < 5.0, bpm


def test_four_jittered_taps_with_a_sloppy_first_one_never_leave_the_lights_drifting():
    """FIX 2, the verifier's rate (h7): 4 taps with 20 ms of jitter and the first +80 ms, the database right and a
    tracker on the kicks. Round 1 left 7-8 runs of 80 drifting at 150 and 174 (4 at 128), every one locked 8-14 % off.
    20 seeds at each tempo here: none drifts (lights' tempo 20-40 s on within 1 %) or sits over 45 ms off."""
    import random
    for bpm in (128.0, 150.0, 174.0):
        p = 60.0 / bpm
        for seed in range(20):
            rng = random.Random(seed)
            grid = G.BeatGrid()
            grid.set_db(bpm)
            d = Drive(grid, tracker=lambda now, p=p: ahead_at(now, 0.0, p, conf=0.9))
            d.until(4.0)
            base = math.ceil(4.0 / p) * p
            taps = sorted(base + k * p + rng.gauss(0, 0.020) for k in range(4))
            taps[0] += 0.080
            taps.sort()
            d.until(taps[-1] + 40.0, taps=taps)
            ts = [t for t, _a in d.beats if taps[-1] + 20.0 < t < taps[-1] + 40.0]
            lights = 60.0 / np.median(np.diff(ts))
            assert abs(lights / bpm - 1.0) <= 0.01, (bpm, seed, lights, grid.tap_bpm)
            assert np.median([_kick_err_ms(t, p) for t in ts]) <= 45.0, (bpm, seed, grid.tap_bpm)


def test_once_the_taps_stop_a_hand_ten_percent_off_takes_the_tempo_the_database_and_tracker_agree_on():
    """FIX 2, after the release: six steady taps at 165 on a 150 groove (10 % off: no snap) with the database and a
    confident tracker both at 150. Round 1 followed a tracker only within 8 % (HOLD_WIDE), so the lights ran at 165
    for good. Two sources against a few taps: now the hand takes their tempo the moment it lets go, and stays put."""
    grid = G.BeatGrid()
    grid.set_db(150.0)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, P150, conf=0.9))
    d.until(4.0)
    taps = [4.0 + k * 60.0 / 165.0 for k in range(6)]
    d.until(taps[-1] + 30.0, taps=taps)
    assert grid.tap_how == "tap" and grid.tap_bpm == 165.0
    late = d.after(taps[-1] + 5.0)
    assert late and all(a["bpm"] == pytest.approx(150.0, abs=0.01) for _t, a in late)
    errs = [_kick_err_ms(t, P150) for t, _a in late]
    assert max(errs) - min(errs) < 3.0, "no drift"


def test_taps_that_slope_ten_percent_slow_go_back_onto_the_kicks_when_they_stop():
    """FIX 2, the phase after the release: four taps [-69, -37, +29, +65] ms on a 128 groove (h7's seed 24, first tap
    -60 ms) lie on a clean line at 116 BPM, 9 % off the database and the tracker (no snap for four taps at 128). Once
    they stop, the hand takes the tempo both agree on, and the lights go where the taps were against the tracker,
    tap by tap (on the kicks), and the tracker takes the beat back. Round 1 ran at 116 for good; measuring the offset
    against the hand's own grid at the release instead kept 0.4 of a beat of the drift (195 ms off)."""
    p = 60.0 / 128.0
    grid = G.BeatGrid()
    grid.set_db(128.0)
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.0, p, conf=0.9))
    d.until(4.0)
    base = math.ceil(4.0 / p) * p
    taps = [base + k * p + e for k, e in enumerate((-0.069, -0.037, 0.029, 0.065))]
    d.until(taps[-1] + 30.0, taps=taps)
    assert grid.tap_how == "tap" and grid.tap_bpm == 116.0
    late = [t for t, _a in d.beats if t > taps[-1] + 10.0]
    assert grid.owner == "track" and max(_kick_err_ms(t, p) for t in late) < 5.0


def test_sloppy_taps_while_the_tracker_settles_go_back_to_it_once_it_steadies():
    """FIX 1 + 2 together (the verifier's Hard Driver probe with the taps at the section start): the tracker is still
    settling while the hand taps (its beats +-45 ms, its bpm field +-3 %, 9-12.5 s), no database, and the taps are
    [+82, -7, +3, -40] ms: no steady tracker to snap to, so they lock on their own line at 165. Once the tracker
    steadies the hand puts the lights back where the taps were against it and the tracker takes the beat back. Round 1
    ran at 165 for good (outside HOLD_WIDE); before the taps' own offset was kept for the first follow, the hand held
    the 0.1-0.3 of a beat it had drifted (52-110 ms off on the recording)."""
    import random
    rng = random.Random(7)
    p = P150
    noise = {}

    def tracker(now):
        k = math.floor(now / p) + 1
        out = []
        for i in range(4):
            t = (k + i) * p
            per = p
            if 9.0 <= t <= 12.5:
                noise.setdefault(k + i, (rng.uniform(-0.045, 0.045), rng.uniform(-0.03, 0.03)))
                t += noise[k + i][0]
                per *= 1.0 + noise[k + i][1]
            out.append({"t_beat": t, "bpm": 60.0 / per, "phase": 0.0, "confidence": 0.9})
        return [b for b in out if b["t_beat"] > now]

    grid = G.BeatGrid()
    d = Drive(grid, tracker=tracker)
    d.until(8.0)
    k0 = math.ceil(10.0 / p) * p
    taps = [k0 + k * p + e for k, e in enumerate((0.082, -0.007, 0.003, -0.040))]
    d.until(taps[-1] + 30.0, taps=taps)
    assert grid.tap_how == "tap" and grid.tap_bpm == 165.0
    assert grid.owner == "track" and taps_of("return", grid)
    late = [t for t, _a in d.beats if t > taps[-1] + 15.0]
    assert max(_kick_err_ms(t, p) for t in late) < 5.0


def test_taps_at_205_on_a_half_time_tracker_keep_205_and_the_tracker_never_takes_the_beat():
    """FIX 3 (the verifier's h5, virtual grid): uptempo at 205 BPM, a tracker at half (102.5, confidence 0.9: beat_a's
    range ends at 200), no database. Round 1 never raised a reference past 200, so six perfect taps snapped to 102.5,
    the lights ran at half time and the half-time tracker took the beat back (cut-off at 200.4 BPM). Now 205, on the
    kicks, and the hand keeps it."""
    for bpm in (200.4, 205.0, 210.0):
        p = 60.0 / bpm
        grid = G.BeatGrid()
        d = Drive(grid, tracker=lambda now, p=p: ahead_at(now, 0.0, 2 * p, conf=0.9))
        d.until(4.0)
        k0 = math.ceil(4.0 / p) * p                       # a kick (the groove's kicks fall on k * p)
        taps = [k0 + k * p for k in range(6)]
        d.until(taps[-1] + 20.0, taps=taps)
        assert grid.tap_bpm == pytest.approx(bpm, abs=0.01) and grid.tap_how == "track", (bpm, grid.tap_bpm)
        late = d.after(taps[-1] + 2.0)
        assert all(a["bpm"] == pytest.approx(bpm, abs=0.01) and a["src"] == "tap" for _t, a in late), bpm
        assert max(_kick_err_ms(t, p) for t, _a in late) < 3.0 and grid.owner == "hand", bpm


def test_an_uptempo_database_tempo_stays_205_for_the_grid_and_seeds_the_tracker_at_half(monkeypatch):
    """FIX 3, the database: restore_octave folded any answer over 200 to half, so a database's 205 reached the grid as
    102.5 and taps at 205 gave 102.5 even with no tracker at all. Now database_tempo keeps 205, the grid snaps taps
    at 205 to it, and only the tracker's seed is folded (102.5: beat_a's range ends at 200), in the engine's re-seed
    and in the beat command's seed."""
    from arsenal.keylab import beatsync as BS
    from arsenal.keylab import tempo as T
    monkeypatch.setattr(T, "lookup", lambda artist, title, offline=False: [T.SourceBpm("deezer", 205.0)])
    found = G.database_tempo("Artist", "Uptempo")
    assert found["bpm"] == 205.0
    assert G.tracker_seed(205.0) == 102.5 and G.tracker_seed(150.0) == 150.0 and G.tracker_seed(None) is None
    assert BS._seed_for({"artist": "A", "title": "T", "status": 4}, offline=False) == 102.5
    grid = G.BeatGrid()
    grid.set_db(found["bpm"])
    p = 60.0 / 205.0
    d = Drive(grid)                                       # no tracker at all
    taps = [4.0 + k * p for k in range(6)]
    d.until(taps[-1] + 5.0, taps=taps)
    assert grid.tap_bpm == 205.0 and grid.tap_how == "db"
    assert all(a["bpm"] == 205.0 for _t, a in d.after(taps[-1]))
    clk = V.BeatClock(RATE, V.HOP, "a", seed_bpm=205.0)
    assert clk.tracker.seed == 102.5
    clk = V.BeatClock(RATE, V.HOP, "a")
    assert clk.reseed(205.0) is True and clk.shadow[2] == 102.5 and clk.shadow[0].seed == 102.5


def test_real_tracker_reading_205_as_half_is_fixed_by_six_taps_at_205():
    """FIX 3 with the real tracker: beat_a reads a 205 groove as 102.3 (confidence 1.0). Six perfect taps at 205, no
    database: round 1 gave tap_bpm 102.29 and the half-time tracker took the beat back (lights at 102.4). Now the
    lights run at 205, every kick, on the kicks."""
    p = 60.0 / 205.0
    k0 = math.ceil(10.0 / p) * p
    taps = [k0 + k * p for k in range(6)]
    clk, got = _run_clock(205.0, taps, 36.0)
    late = [(x, a) for x, a in got if taps[-1] + 5.0 < x < taps[-1] + 20.0]
    assert late and all(abs(a["bpm"] / 205.0 - 1.0) < 0.01 for _x, a in late), clk.grid.tap_bpm
    assert len(late) / 15.0 == pytest.approx(205.0 / 60.0, abs=0.15), "every kick, not every other one"
    assert np.median([_kick_err_ms(x, p) for x, _a in late]) < 10.0


# --- round 3 fixes: a database a few per cent off the music (2026-10-25) -----------------------------------------
# Each of these failed on round 2 (fa168a29) and passes after the fix; the verifier's numbers are quoted. A database
# tempo 5-9 % off the music is ordinary: a pitched YouTube re-upload, a DJ-pitched live version, a title that matches
# the wrong song.

def _taps_on_kicks(bpm, n, at=10.0):
    p = 60.0 / bpm
    k0 = math.ceil(at / p) * p                            # a kick (the groove's kicks fall on k * p)
    return [k0 + k * p for k in range(n)]


def _landed(beats, lo, hi):
    """The land times of the announced beats between lo and hi s."""
    return [t for t, _a in beats if lo < t < hi]


@pytest.mark.parametrize("bpm,db,n", [(142.0, 150.0, 4), (180.0, 170.0, 6)])
def test_perfect_taps_on_the_groove_beat_a_database_a_few_percent_off(bpm, db, n):
    """FIX 1 (the verifier's h14 cells, on the stand-in tracker): perfect taps on a 142 groove with the database at 150
    (4 taps), and on a 180 groove with the database at 170 (6 taps). Round 2 widened the snap window for every short
    run (7 % for four taps; the 180 run dropped a good end tap against the database's grid, which widened it to
    5.6 %), tried the database first, then let the database side with the hand because the hand's period was the
    snapped one: tap_bpm 150 (170), the hand kept the beat and the lights drifted (the verifier: 107 ms median, 208 ms
    max for 40 s). Now: the tracker's tempo when one is steady and agrees with the taps (at the groove's tempo or at
    half: beat_a reads 180 as 90), the taps' own tempo with no tracker, on the kicks either way."""
    p = 60.0 / bpm
    taps = _taps_on_kicks(bpm, n)
    for tracker, want in ((p, "track"), (2 * p, "track"), (None, "tap")):
        grid = G.BeatGrid()
        grid.set_db(db)
        stub = None if tracker is None else (lambda now, pt=tracker: ahead_at(now, 0.0, pt, conf=0.99))
        d = Drive(grid, tracker=stub)
        d.until(4.0)
        d.until(taps[-1] + 40.0, taps=taps)
        assert grid.tap_how == want and grid.tap_bpm == pytest.approx(bpm, abs=0.05), (tracker, grid.tap_bpm)
        late = _landed(d.beats, taps[-1] + 20.0, taps[-1] + 40.0)
        assert abs(60.0 / np.median(np.diff(late)) / bpm - 1.0) < 0.01, (tracker, grid.tap_bpm)
        assert max(_kick_err_ms(t, p) for t in late) < 5.0, tracker


def test_a_database_off_the_music_never_takes_perfect_taps_on_the_virtual_grid():
    """FIX 1, the verifier's rate (h15): the database 5 or 8 % off either way, PERFECT taps on the kicks (4, 5 or 6),
    the tracker on the kicks (confidence 0.9) or absent, at 128, 150 and 174 BPM. Round 2: 19 of 54 runs locked to the
    database's tempo and drifted 80-123 ms off, with or without a tracker (round 1 and the first build: none). Now none:
    the lights run at the groove's tempo, on the kicks."""
    for groove in (128.0, 150.0, 174.0):
        p = 60.0 / groove
        for d_off in (-0.08, -0.05, 0.05, 0.08):
            db = round(groove * (1.0 + d_off), 1)
            for n in (4, 5, 6):
                for tracker in (True, False):
                    grid = G.BeatGrid()
                    grid.set_db(db)
                    d = Drive(grid, tracker=(lambda now, p=p: ahead_at(now, 0.0, p)) if tracker else None)
                    d.until(4.0)
                    taps = _taps_on_kicks(groove, n, at=4.0)
                    d.until(taps[-1] + 25.0, taps=taps)
                    late = _landed(d.beats, taps[-1] + 15.0, taps[-1] + 25.0)
                    lights = 60.0 / np.median(np.diff(late))
                    case = (groove, db, n, tracker, grid.tap_bpm, grid.tap_how)
                    assert grid.tap_how != "db" and abs(lights / groove - 1.0) < 0.01, case
                    assert np.median([_kick_err_ms(t, p) for t in late]) < 5.0, case


def test_the_database_sides_with_the_hand_only_when_the_taps_own_slope_agrees_with_it():
    """FIX 1 (b): after the release, _hold_wide asked whether the database sided with the hand by comparing it with the
    hand's period, which is the snapped one, so a snap to the database agreed with itself and kept a right tracker out
    for good. A 142 groove, the database at 150, no tracker while the hand taps; the first tap 0.3 of a beat late (a
    real outlier, so the three taps left get the wider window and the tempo snaps to 150, as h8's sloppy tap does).
    The taps' own slope is 142. Then a confident tracker on the kicks at 142 comes in: now the hand takes its tempo and
    hands the beat back (round 2: the lights stayed at 150, drifting). With the tracker there during the taps, the
    taps agree with it, not with the database: 142 from the lock on."""
    bpm, db = 142.0, 150.0
    p = 60.0 / bpm
    taps = _taps_on_kicks(bpm, 4)
    taps[0] += 0.3 * p
    late_tracker = lambda now: ahead_at(now, 0.0, p) if now > taps[-1] + 1.5 else []      # noqa: E731
    for tracker, want in ((late_tracker, "db"), (lambda now: ahead_at(now, 0.0, p), "track")):
        grid = G.BeatGrid()
        grid.set_db(db)
        d = Drive(grid, tracker=tracker)
        d.until(4.0)
        d.until(taps[-1] + 40.0, taps=taps)
        assert grid.tap_how == want, (want, grid.tap_bpm)
        late = _landed(d.beats, taps[-1] + 20.0, taps[-1] + 40.0)
        assert abs(60.0 / np.median(np.diff(late)) / bpm - 1.0) < 0.01, (want, grid.tap_bpm)
        assert grid.owner == "track" and max(_kick_err_ms(t, p) for t in late) < 5.0, want


def test_messy_taps_on_a_wobbly_tracker_still_snap_to_it():
    """A guard on FIX 1 (a), not a round-2 repro: only the DATABASE's window went back to the spec's 4 %; the
    tracker's keeps the wide one (what human jitter puts on the taps left), since its tempo is measured off the music.
    Four messy taps [+81, +12, +16, -52] ms at 174 (the verifier's h12 C, seed 6) on a wobbly tracker (beats +-15 ms,
    bpm field +-2 %), no database: they snap to the tracker and the lights end on the kicks. Narrowed to 4 % like the
    database's, they fell back to their own 197 BPM and, the wobbly line slow to steady, one run in eight held the
    lights 97 ms off (137 ms on the verifier's h12 C with the tracker's slow wander)."""
    p = 60.0 / 174.0
    for seed in range(8):
        grid = G.BeatGrid()
        d = Drive(grid, tracker=wobbly_tracker(p, seed))
        k0 = math.ceil(8.0 / p) * p
        taps = [k0 + k * p + e for k, e in enumerate((0.081, 0.012, 0.016, -0.052))]
        d.until(taps[-1] + 40.0, taps=taps)
        assert grid.tap_how == "track" and abs(grid.tap_bpm / 174.0 - 1.0) < 0.01, (seed, grid.tap_bpm)
        late = _landed(d.beats, taps[-1] + 10.0, taps[-1] + 40.0)
        assert grid.owner == "track" and np.median([_kick_err_ms(t, p) for t in late]) < 12.0, seed


def test_one_tap_after_a_tap_run_re_phases_the_beat_and_the_next_follow_keeps_it():
    """Found while fixing round 2: after a tap run, one isolated tap 0.3 of a beat later re-phased the lights for one
    block, and the hand's next follow of the tracker undid it: _first_offset measured the old run's kept taps against
    the tracker, since the isolated tap was recent. A tracker on the off-beat (it never takes the beat back), six taps
    on the kicks, then one tap at +0.3 of a beat 5 s later: round 2 kept the lights on the old run's phase (0.000 of a
    beat off the kicks); now they stay on the new tap (+0.300), as the first build did."""
    grid = G.BeatGrid()
    d = Drive(grid, tracker=lambda now: ahead_at(now, 0.5 * P150, P150))
    taps = [4.0 + k * P150 for k in range(6)] + [12.0 + 0.3 * P150]
    d.until(25.0, taps=taps)
    late = [G.wrap(t / P150) for t, _a in d.after(12.5)]
    assert grid.owner == "hand" and late and all(abs(w - 0.3) < 0.01 for w in late), late[:4]


def _run_clock_reseed(bpm, taps, secs, db, reseed_at=None):
    """_run_clock with the database set and, at reseed_at s, the engine's re-seed to its tempo (a track change)."""
    clk = V.BeatClock(RATE, V.HOP, "a")
    clk.grid.set_db(db)
    src = _synth(bpm, secs)
    t, i, got, done = 0.0, 0, [], reseed_at is None
    while (b := src.read()) is not None:
        t += BLOCK
        if not done and t >= reseed_at:
            clk.reseed(db)
            done = True
        while i < len(taps) and taps[i] <= t:
            clk.tap(taps[i])
            i += 1
        a = clk.feed(b)
        if a:
            got.append((t + a["lead_s"], a))
    return clk, got


@pytest.mark.parametrize("bpm,db,n", [(142.0, 150.0, 4), (180.0, 170.0, 6)])
def test_real_tracker_perfect_taps_beat_a_database_a_few_percent_off(bpm, db, n):
    """FIX 1 with the real tracker (the verifier's h14): beat_a on the groove, the database 5-6 % off, perfect taps on
    the kicks, with and without the engine's re-seed to the database's tempo. 142 / database 150 / 4 taps: round 2
    gave tap_bpm 150 (db), the hand for 40 s, 107 ms median and 208 ms max off (the first build: 142.15, back to the
    tracker, 1-2 ms). 180 / database 170 / 6 taps (beat_a reads 90.7 unseeded; re-seeded at 170 it reads 180.2): round
    2 locked at 170, 78-98 ms off for 40 s (the first build: 179.91, 1-2 ms). Now the groove's tempo, on the kicks."""
    p = 60.0 / bpm
    taps = _taps_on_kicks(bpm, n)
    for reseed_at in (None, 3.0):
        clk, got = _run_clock_reseed(bpm, taps, taps[-1] + 40.0, db, reseed_at)
        late = [(x, a) for x, a in got if taps[-1] + 10.0 < x < taps[-1] + 40.0]
        errs = [_kick_err_ms(x, p) for x, _a in late]
        case = (reseed_at, clk.grid.tap_bpm, clk.grid.tap_how, clk.grid.owner)
        assert clk.grid.tap_how != "db" and abs(clk.grid.tap_bpm / bpm - 1.0) < 0.01, case
        assert late and all(abs(a["bpm"] / bpm - 1.0) < 0.01 for _x, a in late), case
        assert np.median(errs) < 15.0 and max(errs) < 30.0, (case, np.median(errs), max(errs))
