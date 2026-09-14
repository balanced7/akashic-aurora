"""The arsenal band VFX Script (arsenal/fl/vfx/arsenal_band.py), run through a faithful flvfx mock.

The mock (arsenal/fl/vfx/flvfx_mock.py) carries only the names FL's factory VFX Script presets and Image-Line's
manual use. What FL leaves unpinned is flipped here rather than assumed: whether FL's own length countdown
releases a voice before or after onTick, whether the first played onTick sees ticks 0 or 1, and FL's
pattern-mode loop wrap. Nothing here touches FL, Documents or the network; live-file cases use tmp_path.
"""
import ast
import bisect
import importlib.util
import json
import math
import os
import re
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VFX_DIR = ROOT / "arsenal" / "fl" / "vfx"
BAND_PATH = VFX_DIR / "arsenal_band.py"
EXAMPLE_PATTERNS = VFX_DIR / "arsenal_patterns.py"
FL_PRESETS = Path(r"C:\Program Files\Image-Line\FL Studio 2026\Data\Patches\Plugin presets\Effects\VFX Script")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mock = _load("arsenal_fl_vfx_mock_under_test", VFX_DIR / "flvfx_mock.py")
Host = mock.Host

LANES = ("bass", "drums", "comp", "pad")
C_PATTERN, C_SWITCH, C_LANE, C_CLOCK = "Band: Pattern", "Band: Switch at", "Band: Lane", "Band: Clock"
C_SWING, C_GRID, C_HUMANIZE, C_DRUM_MAP = "Feel: Swing", "Feel: Swing grid", "Feel: Humanize", "Feel: Drum map"
C_DROPOUT, C_DROPOUT_SEED = "Feel: Dropout", "Feel: Dropout seed"
C_LIVE, C_RELOAD, C_PANIC = "Patterns: Live file", "Patterns: Reload", "Patterns: Panic"


# -- pattern fixtures ----------------------------------------------------------------------------------------------

def pset(pid, lanes, length=16, meter=(4, 4)):
    return {"version": 1, "id": pid, "title": pid, "key": "C major", "bpm_hint": 100, "meter": list(meter),
            "length_beats": length, "chords": [{"beat": 0, "name": "C", "nns": "1"}],
            "lanes": {lane: {"notes": [{"beat": b, "len": ln, "note": n, "vel": v} for (b, ln, n, v) in lanes.get(lane, [])]}
                      for lane in LANES}}


def groove_a(pid="groove-a", bass_base=36):
    lanes = {lane: [] for lane in LANES}
    for k in range(4):
        base = 4 * k
        lanes["bass"] += [(base, 1.5, bass_base + k, 100), (base + 1 + 1 / 3, 1 / 3, 31, 50), (base + 2.5, 0.5, 43, 90)]
        lanes["drums"] += [(base, 0.25, 36, 110), (base + 1, 0.25, 38, 100), (base + 2.5, 0.25, 36, 96), (base + 3, 0.25, 38, 100)]
        lanes["drums"] += [(base + s / 2, 0.1, 42, 70) for s in range(8)]
        lanes["comp"] += [(base + 3.75, 1.0, n, 72) for n in (60, 64, 67)]
        lanes["pad"] += [(base, 3.5, 48, 60), (base, 3.5, 55, 60)]
    return pset(pid, lanes)


def groove_b(pid="groove-b"):
    lanes = {"bass": [(0, 1, 24, 100), (4, 1, 26, 100)],
             "drums": [(0, 0.25, 49, 100), (2, 0.25, 39, 100), (6, 0.25, 39, 100)],
             "comp": [(1, 0.5, 72, 80), (5, 0.5, 74, 80)],
             "pad": [(0, 8, 84, 50)]}
    return pset(pid, lanes, length=8)


def patterns_module(*sets, live_path=None, drum_maps=None, version=1):
    m = types.ModuleType("arsenal_patterns")
    m.VERSION = version
    m.PATTERNS = list(sets)
    m.LIVE_PATH = live_path
    if drum_maps is not None:
        m.DRUM_MAPS = drum_maps
    return m


def notes_of(p):
    return {n["note"] for lane in LANES for n in p["lanes"][lane]["notes"]}


def expected(p, ppq, t0, t1):
    """(tick, lane index, note, length ticks) for a pattern anchored at band tick t0, up to t1. Written apart from the band."""
    loop = round(p["length_beats"] * ppq)
    out = []
    for lane_i, lane in enumerate(LANES):
        for n in p["lanes"][lane]["notes"]:
            pos = round((n["beat"] % p["length_beats"]) * ppq) % loop
            k = 0
            while t0 + k * loop + pos < t1:
                out.append((t0 + k * loop + pos, lane_i, n["note"], max(1, round(n["len"] * ppq))))
                k += 1
    return sorted(out)


def start(host, ticks=1):
    """A stopped onTick first (FL runs onTick while stopped), so controls are read, then Play."""
    host.run(ticks)
    host.play()


def assert_clean(host):
    assert host.anomalies == []
    for on, off in host.pairs():
        assert off is not None, "note %s at tick %s never released" % (on["note"], on["tick"])
        assert off["host_tick"] >= on["host_tick"]


def stamp_write(path, content, _n=[0]):
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    _n[0] += 1
    t = 1_700_000_000_000_000_000 + _n[0] * 1_000_000_000
    os.utime(path, ns=(t, t))


# -- the API surface ----------------------------------------------------------------------------------------------

def test_band_script_is_ascii_and_has_the_entry_points_fl_calls():
    raw = BAND_PATH.read_bytes()
    raw.decode("ascii")  # FL 26 fixed "invalid characters when loading a file from an external editor"; stay ASCII
    EXAMPLE_PATTERNS.read_bytes().decode("ascii")
    tree = ast.parse(raw.decode("ascii"))
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"onTick", "createDialog"} <= funcs
    assert b"__main__" not in raw  # FL may run the script under any module name


def test_band_uses_only_names_fl_presets_and_manual_use():
    """Every vfx, context, form and voice name the band touches must exist in FL: the mock mirrors that census."""
    tree = ast.parse(BAND_PATH.read_text(encoding="ascii"))
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    roots = {"vfx": "vfx", "ctx": "vfx.context", "form": "form", "v": "voice", "x": "voice"}
    allowed_voice = {"note", "velocity", "length", "output", "trigger", "release"}
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or isinstance(parents.get(node), ast.Attribute):
            continue
        chain = []
        cur = node
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name) or cur.id not in roots:
            continue
        dotted = ".".join([roots[cur.id]] + chain[::-1])
        seen.add(dotted)
        parts = dotted.split(".")
        if parts[0] == "voice":
            assert parts[1] in allowed_voice, dotted
        elif parts[0] == "form" or parts[:3] == ["vfx", "context", "form"]:
            tail = parts[1:] if parts[0] == "form" else parts[3:]
            assert not tail or tail[0] in mock.FORM_NAMES, dotted
        else:
            assert parts[1] in mock.FLVFX_NAMES, dotted
            if parts[1] == "context" and len(parts) > 2:
                assert parts[2] in mock.CONTEXT_NAMES, dotted
    assert {"vfx.Voice", "vfx.context.voices", "vfx.addOutputController", "voice.trigger", "voice.release"} <= seen
    public = {k for k in vars(mock.make_flvfx(Host())) if not k.startswith("__")}
    assert public == set(mock.FLVFX_NAMES)


@pytest.mark.skipif(not FL_PRESETS.is_dir(), reason="FL Studio 2026's factory VFX Script presets are not on this machine")
def test_mock_names_are_attested_by_fl_factory_presets():
    """Read-only census of FL's own presets: each name the mock offers the band is used by at least one of them."""
    text = ""
    for p in FL_PRESETS.rglob("*.fst"):
        text += p.read_bytes().decode("latin-1").replace("<linebreak>", "\n")
    vfx_names = set(re.findall(r"\bvfx\.(\w+)", text))
    context_names = set(re.findall(r"\bvfx\.context\.(\w+)", text))
    form_calls = set(re.findall(r"\bform\.(\w+)", text))
    assert set(mock.FLVFX_NAMES) <= vfx_names
    assert set(mock.CONTEXT_NAMES) <= context_names
    assert set(mock.FORM_NAMES) - {"addInputText"} <= form_calls  # addInputText: Tutorial 2 and the manual
    for field in ("note", "velocity", "length", "output", "trigger", "release"):
        assert re.search(r"\.%s\b" % field, text), field


def test_dialog_controls_and_defaults():
    with Host(patterns=patterns_module(groove_a())) as host:
        names = host.form.names()
        assert names == [C_PATTERN, C_SWITCH, C_LANE, C_CLOCK, C_SWING, C_GRID, C_HUMANIZE, C_DRUM_MAP, C_DROPOUT,
                         C_DROPOUT_SEED, "Mute: Bass", "Mute: Drums", "Mute: Comp", "Mute: Pad", C_LIVE, C_RELOAD, C_PANIC]
        assert host.get(C_PATTERN) == 0 and host.get(C_CLOCK) == 0 and host.get(C_SWITCH) == 0
        assert host.get(C_DROPOUT) == 0 and host.get(C_DROPOUT_SEED) == 0
        assert host.form.options(C_DROPOUT) == ["Off", "Rare", "Often"]
        assert host.form.options(C_DRUM_MAP) == ["GM", "FPC", "AD2 default"]
        for name in names:
            assert all("," not in o for o in host.form.options(name))
        assert "Bar pulse" in host.controllers


# -- playhead lock, note-offs -------------------------------------------------------------------------------------

@pytest.mark.parametrize("ppq", [96, 960])
@pytest.mark.parametrize("bpm", [72, 120])
def test_32_bars_every_note_lands_on_its_tick_and_has_one_note_off(bpm, ppq):
    a = groove_a()
    total = 32 * 4 * ppq
    with Host(ppq=ppq, bpm=bpm, patterns=patterns_module(a)) as host:
        start(host)
        t_play = host.seconds
        host.run(total)
        stop_host_tick = host.host_tick
        host.stop()
        host.run(2)
    want = expected(a, ppq, 0, total)
    assert sorted((e["tick"], e["output"], e["note"]) for e in host.ons()) == [(t, lane, note) for t, lane, note, _ in want]
    lengths = {(t, lane, note): ln for t, lane, note, ln in want}
    assert_clean(host)
    assert host.active == []
    tick_s = 60.0 / (bpm * ppq)
    for on, off in host.pairs():
        assert on["seconds"] == pytest.approx(t_play + on["tick"] * tick_s, rel=1e-9, abs=1e-9)
        assert on["length"] == lengths[(on["tick"], on["output"], on["note"])]
        natural_end = on["host_tick"] + on["length"]
        if natural_end <= stop_host_tick:
            assert off["host_tick"] == natural_end
        else:
            assert off["host_tick"] == stop_host_tick  # cut by Stop, on the stop tick
    assert len(host.ons()) == len(want) == 32 * 20  # groove_a: 3 bass + 12 drums + 3 comp + 2 pad per bar


@pytest.mark.parametrize("order", ["before", "after"])
def test_one_note_off_per_note_whichever_side_of_ontick_fl_counts_length(order):
    with Host(auto_release=order, patterns=patterns_module(groove_a())) as host:
        start(host)
        host.run(8 * 384 + 100)
        host.stop()
        host.run(1)
    assert_clean(host)
    offs = [e for e in host.events if e["kind"] == "off"]
    assert len(offs) == len(host.ons())
    natural = [e for e in offs if e["tick"] != 0]
    if order == "before":
        assert all(e["auto"] for e in natural)  # FL got there first; the band saw it gone and did not release twice
    else:
        assert not any(e["auto"] for e in natural)


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_first_played_tick_reporting_one_still_plays_the_downbeat(clock):
    a = groove_a()
    with Host(first_tick=1, patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, clock)
        start(host)
        host.run(2 * 384)
    beat0 = {n["note"] for lane in LANES for n in a["lanes"][lane]["notes"] if n["beat"] == 0}
    assert {e["note"] for e in host.ons() if e["tick"] == 1} == beat0
    bar2 = {e["tick"] for e in host.ons() if e["note"] == 37}
    assert bar2 == {384}  # both clocks stay on FL's bar grid, not one tick behind it
    assert host.anomalies == []


# -- switching ----------------------------------------------------------------------------------------------------

def test_pattern_switches_land_on_bar_lines_only_and_cut_the_old_pattern_there():
    a, b = groove_a(), groove_b()
    changes = [(1000, 1), (2500, 0), (3071, 1), (3845, 0), (6001, 1)]
    with Host(patterns=patterns_module(a, b)) as host:
        start(host)
        for at, idx in changes:
            host.run(at - host.position)
            host.set(C_PATTERN, idx)
        host.run(4 * 384)
        host.stop()
        host.run(1)
        band = host.band
        switches = [s for s in band.switches if s[0] is not None]
        poll = band.poll_every
    assert [s[1] for s in switches] == [1, 0, 1, 0, 1]
    for (t, _idx, anchor_before, bar_before), (at, _) in zip(switches, changes):
        assert (t - anchor_before) % bar_before == 0, "switch at %d is mid-bar" % t
        assert at <= t <= at + bar_before + poll
    bounds = [0] + [s[0] for s in switches] + [10 ** 9]
    owners = [0] + [s[1] for s in switches]
    sets = [notes_of(a), notes_of(b)]
    for (lo, hi), idx in zip(zip(bounds, bounds[1:]), owners):
        segment = [e for e in host.ons() if lo <= e["tick"] < hi]
        assert segment and {e["note"] for e in segment} <= sets[idx]
        if lo:
            first_pattern = [a, b][idx]
            beat0 = {n["note"] for lane in LANES for n in first_pattern["lanes"][lane]["notes"] if n["beat"] == 0}
            assert {e["note"] for e in segment if e["tick"] == lo} == beat0  # the new pattern starts from its top
    for on, off in host.pairs():
        nxt = min((t for t in bounds[1:] if t > on["tick"]), default=None)
        if nxt is not None and off["tick"] != 0:
            assert off["tick"] <= nxt  # nothing from the old pattern rings past its switch
    assert_clean(host)


def test_next_loop_waits_for_the_top_of_the_running_loop():
    with Host(patterns=patterns_module(groove_a(), groove_b())) as host:
        host.set(C_SWITCH, "Next loop")
        start(host)
        host.run(500)
        host.set(C_PATTERN, 1)
        host.run(3000)
        assert [s[0] for s in host.band.switches if s[0] is not None] == [1536]
        host.stop()
        host.run(1)
    assert_clean(host)


def test_knob_returning_before_the_bar_line_cancels_the_switch():
    with Host(patterns=patterns_module(groove_a(), groove_b())) as host:
        start(host)
        host.run(100)
        host.set(C_PATTERN, 1)
        host.run(40)
        host.set(C_PATTERN, 0)
        host.run(1000)
        assert [s for s in host.band.switches if s[0] is not None] == []
        assert host.band.current == 0


def test_editing_the_running_pattern_keeps_its_place_in_the_loop():
    a = groove_a()
    mod = patterns_module(a)
    with Host(patterns=mod) as host:
        start(host)
        host.run(384 + 50)  # into bar 2 of the 4-bar loop
        mod.PATTERNS[0] = groove_a(bass_base=40)  # same id, same length: an edit, not a new pattern
        host.set(C_RELOAD, 1)
        host.run(384 * 2)
        assert host.get(C_RELOAD) == 0  # momentary
        switch = [s for s in host.band.switches if s[0] is not None]
        assert [s[0] for s in switch] == [768] and host.band.anchor == 0
        host.stop()
        host.run(1)
    bass_roots = [(e["tick"], e["note"]) for e in host.ons() if e["output"] == 0 and e["tick"] % 384 == 0]
    assert bass_roots == [(0, 36), (384, 37), (768, 42), (1152, 43)]  # bar 3 of the edit, not bar 1
    assert_clean(host)


# -- transport ----------------------------------------------------------------------------------------------------

def test_stop_releases_everything_and_play_starts_again_at_bar_one():
    a = groove_a()
    with Host(patterns=patterns_module(a)) as host:
        start(host)
        host.run(2 * 384 + 200)
        assert host.active  # the pad is sounding
        host.stop()
        host.run(1)
        assert host.active == []
        before = len(host.events)
        host.run(500)
        assert len(host.events) == before  # silence while stopped
        host.play()
        host.run(10)
    restarted = [e for e in host.events[before:] if e["kind"] == "on"]
    beat0 = {n["note"] for lane in LANES for n in a["lanes"][lane]["notes"] if n["beat"] == 0}
    assert {e["note"] for e in restarted if e["tick"] == 0} == beat0
    assert host.anomalies == []


def test_pause_and_resume_continue_the_loop_where_it_was():
    a = groove_a()
    with Host(patterns=patterns_module(a)) as host:
        start(host)
        host.run(576)
        host.pause()
        host.run(300)
        assert host.active == []
        host.play()
        host.run(4 * 384 - 576)
        host.pause()
        host.run(1)
    got = sorted((e["tick"], e["output"], e["note"]) for e in host.ons())
    assert got == [(t, lane, note) for t, lane, note, _ in expected(a, 96, 0, 4 * 384)]
    assert_clean(host)


def on_calls(notes, step, limit):
    """Expected (tick, lane, note) as FL reports them when onTick runs every step ticks: a note is triggered on the
    first call at or after its tick. Only calls before limit."""
    out = sorted((-(-t // step) * step, lane, note) for t, lane, note, _ in notes)
    return [x for x in out if x[0] < limit]


def played(host, limit):
    return sorted((e["tick"], e["output"], e["note"]) for e in host.ons() if e["tick"] < limit)


def without_pushes_into(notes, line, ppq=96):
    """notes minus the pushes (any lane but bass, starting in the last half beat before line and ringing over it) into
    a bar line where a pattern switch or Reload waits: the switch would cut them at once, so the band skips them."""
    return [(t, lane, note, ln) for t, lane, note, ln in notes
            if lane == 0 or not (line - ppq // 2 <= t < line and t + ln > line)]


@pytest.mark.parametrize("step", [1, 2, 5])
@pytest.mark.parametrize("action", ["none", "knob", "reload"])
@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_pause_mid_bar_then_switch_or_reload_resumes_on_fl_bars(clock, action, step):
    """Paused mid-bar (the KeyLab Play button pauses), a switch or Reload waits for FL's next bar line after Play."""
    a, b = groove_a(), groove_b()
    limit = 8 * 384
    with Host(tick_step=step, patterns=patterns_module(a, b)) as host:
        host.set(C_CLOCK, clock)
        start(host)
        host.run_to(576)  # bar 2, beat 3
        host.pause()
        host.run(20)
        if action == "knob":
            host.set(C_PATTERN, 1)
        elif action == "reload":
            host.set(C_RELOAD, 1)
        host.run(20)
        band = host.band
        if action != "none":
            assert band.pending is not None and band.current == 0  # held for the bar line, not applied while paused
        assert host.active == []
        host.play()
        host.run_to(limit)
        switches = [s[:2] for s in band.switches if s[0] is not None]
        host.stop()
        host.run(1)
    if action == "knob":
        assert switches == [(768, 1)]
        want = without_pushes_into(expected(a, 96, 0, 768), 768) + expected(b, 96, 768, limit)
    else:
        assert switches == ([(768, 0)] if action == "reload" else [])
        want = expected(a, 96, 0, limit)
        if action == "reload":
            want = without_pushes_into(want, 768)
    assert played(host, limit) == on_calls(want, step, limit)
    assert_clean(host)


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_play_from_a_playhead_parked_mid_bar_stays_on_fl_bars(clock):
    a = groove_a()
    limit = 4 * 384
    with Host(patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, clock)
        host.seek(576)  # stopped, playhead at bar 2 beat 3
        start(host)
        host.run_to(limit)
        host.stop()
        host.run(1)
    # Keep counting joins bar 1 of the pattern at beat 3 (its bar 1 sits on FL's bar 2); Follow song position plays
    # the pattern's own bar 2. Either way every bar line is one of FL's.
    anchor = 384 if clock == "Keep counting" else 0
    want = [x for x in expected(a, 96, anchor, limit) if x[0] >= 576]
    assert played(host, limit) == on_calls(want, 1, limit)
    bass_roots = [e["note"] for e in sorted(host.ons(), key=lambda e: e["tick"]) if e["output"] == 0 and e["tick"] % 384 == 0]
    assert bass_roots == ([37, 38] if clock == "Keep counting" else [38, 39])  # FL bars 3 and 4
    assert_clean(host)


def test_stop_while_paused_with_a_switch_waiting_starts_fresh_on_it():
    a, b = groove_a(), groove_b()
    with Host(patterns=patterns_module(a, b)) as host:
        start(host)
        host.run_to(576)
        host.pause()
        host.run(10)
        host.set(C_PATTERN, 1)
        host.run(10)
        assert host.band.pending == 1 and host.band.current == 0
        host.stop()  # the playhead goes back to the start: nothing to continue
        host.run(10)
        assert host.band.pending is None and host.band.current == 1
        before = len(host.events)
        host.play()
        host.run_to(2 * 384)
        host.stop()
        host.run(1)
    got = sorted((e["tick"], e["output"], e["note"]) for e in host.events[before:] if e["kind"] == "on")
    assert got == [(t, lane, note) for t, lane, note, _ in expected(b, 96, 0, 2 * 384)]
    assert_clean(host)


def test_follow_song_position_releases_everything_on_an_fl_loop_wrap():
    a = groove_a()
    loop = 576  # FL's pattern loop wraps mid-bar, mid-note
    with Host(loop_ticks=loop, patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, "Follow song position")
        start(host)
        host.run(3 * loop)
        host.stop()
        host.run(1)
    one_pass = [(t, lane, note) for t, lane, note, _ in expected(a, 96, 0, loop)]
    got = sorted((e["tick"], e["output"], e["note"]) for e in host.ons())
    assert got == sorted(one_pass * 3)
    play_host_tick = 1
    for k in (1, 2):
        wrap_host_tick = play_host_tick + k * loop
        across = [(on, off) for on, off in host.pairs() if on["host_tick"] < wrap_host_tick < on["host_tick"] + on["length"]]
        assert across, "the fixture should have notes ringing across the wrap"
        assert all(off["host_tick"] == wrap_host_tick for _on, off in across)
    assert_clean(host)


@pytest.mark.parametrize("step", [1, 2, 5])
def test_keep_counting_rides_through_a_one_bar_fl_loop(step):
    a = groove_a()
    limit = 8 * 384
    with Host(loop_ticks=384, tick_step=step, patterns=patterns_module(a)) as host:
        start(host)
        host.run(-(-limit // step))
        host.stop()
        host.run(1)
    got = sorted((e["host_tick"] - step, e["output"], e["note"]) for e in host.ons())  # host time since Play
    assert got == on_calls(expected(a, 96, 0, limit), step, limit)
    assert_clean(host)


# -- irregular onTick gaps ------------------------------------------------------------------------------------------
# FL may call onTick less often than every tick, and not evenly: once per audio buffer, say, which at PPQ 96 is 1 or 2
# ticks at 72 BPM and 2 or 3 at 120 with a 512-sample buffer. A gap can jump straight over FL's loop-wrap tick.

IRREGULAR = [1, 4, 2, 7, 3, 5, 2, 6, 1, 9]
SPARSE = [11, 3, 17, 5, 23, 2, 13]


def gap_host(gaps, bpm, **kw):
    if gaps == "buffer":
        return Host(bpm=bpm, buffer_samples=512, **kw)
    if isinstance(gaps, str):
        gaps = {"irregular": IRREGULAR, "sparse": SPARSE}[gaps]
    return Host(bpm=bpm, gaps=gaps, **kw)


def fired_at(marks, notes, limit):
    """(mark, lane, note) for notes (tick, lane, note, len) when onTick runs at these band ticks (increasing): a note
    is triggered by the first call at or after its tick. Only calls before limit."""
    out = []
    for t, lane, note, _ in notes:
        i = bisect.bisect_left(marks, t)
        if i < len(marks) and marks[i] < limit:
            out.append((marks[i], lane, note))
    return sorted(out)


def song_fired(calls, p, ppq, loop_end, loop_top=0):
    """(host tick, lane, note) Follow song position should trigger, given FL's played calls (host tick, ticks) and a
    pattern anchored at song tick 0. Between calls FL passed (last, ticks]; across a wrap it passed (last, loop end)
    and then [loop top, ticks]. The first played call also plays the tick before."""
    at = {}
    for t, lane, note, _ in expected(p, ppq, 0, 64 * round(p["length_beats"] * ppq)):
        at.setdefault(t, []).append((lane, note))
    out = []
    prev = None
    for h, q in calls:
        if prev is None:
            window = range(max(0, q - 1), q + 1)
        elif 0 < q - prev <= ppq:
            window = range(prev + 1, q + 1)
        elif q < prev:
            window = list(range(prev + 1, loop_end)) + list(range(loop_top, q + 1))
        else:
            window = range(0)
        out += [(h, lane, note) for t in window for lane, note in at.get(t, ())]
        prev = q
    return sorted(out)


@pytest.mark.parametrize("gaps", ["irregular", "sparse", "buffer", [7], [5, 2]])
@pytest.mark.parametrize("bpm", [72, 120])
def test_follow_song_position_plays_the_loop_top_downbeat_when_a_gap_skips_the_wrap_tick(bpm, gaps):
    a = groove_a()
    loop = 768
    with gap_host(gaps, bpm, loop_ticks=loop, patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, "Follow song position")
        start(host)
        host.run_ticks(8 * loop)
        host.stop()
        host.run(1)
    calls = host.played_calls()
    wraps = sum(1 for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 < t0)
    assert wraps >= 7 and any(t != 0 for (_h0, t0), (_h1, t) in zip(calls, calls[1:]) if t < t0)  # gaps skip tick 0
    got = sorted((e["host_tick"], e["output"], e["note"]) for e in host.ons())
    assert got == song_fired(calls, a, 96, loop)
    kicks = [e for e in host.ons() if e["output"] == 1 and e["note"] == 36 and e["tick"] < 96]
    assert len(kicks) == wraps + 1  # the loop-top kick, once per pass
    assert_clean(host)


def tail_groove(pid="tail"):
    """A 1-bar groove with notes in the last ticks of the bar (at PPQ 96: 364, 370, 380), where a sparse onTick can
    leave them between its last call and FL's loop wrap."""
    lanes = {"bass": [(0, 1, 36, 100), (364 / 96, 0.2, 38, 80)],
             "drums": [(s / 4, 0.05, 42, 60) for s in range(16)] + [(0, 0.25, 36, 110), (380 / 96, 0.1, 38, 90)],
             "comp": [(370 / 96, 0.5, 64, 70)],
             "pad": [(0, 3.5, 55, 60)]}
    return pset(pid, lanes, length=4)


@pytest.mark.parametrize("gaps", ["sparse", [7], [5, 2], "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_follow_song_position_plays_the_end_of_the_loop_before_a_wrap(bpm, gaps):
    p = tail_groove()
    loop = 384
    with gap_host(gaps, bpm, loop_ticks=loop, patterns=patterns_module(p)) as host:
        host.set(C_CLOCK, "Follow song position")
        start(host)
        host.run_ticks(24 * loop)
        host.stop()
        host.run(1)
    calls = host.played_calls()
    got = sorted((e["host_tick"], e["output"], e["note"]) for e in host.ons())
    assert got == song_fired(calls, p, 96, loop)
    tails = [(t0, t1) for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 < t0 and t0 < 364]
    if gaps == "sparse":
        assert tails  # sparse gaps leave the loop's last notes after the last call before a wrap
    assert_clean(host)


@pytest.mark.parametrize("gaps", [[3], "irregular"])
def test_follow_song_position_keeps_the_downbeat_after_a_seek_back_mid_play(gaps):
    a = groove_a()
    with gap_host(gaps, 120, patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, "Follow song position")
        start(host)
        host.run_to(1000)
        host.seek(770)  # two ticks past bar 3's line
        host.run(1)
        host.run_to(1300)
    at_seek = sorted((e["output"], e["note"]) for e in host.ons() if e["tick"] == 770)
    bar3 = sorted((lane, note) for t, lane, note, _ in expected(a, 96, 0, 1536) if 768 <= t <= 770)
    assert at_seek == bar3 and any(note == 38 for _lane, note in bar3)  # bass root and pad of bar 3, not lost
    assert host.anomalies == []


@pytest.mark.parametrize("loop", [384, 768])
@pytest.mark.parametrize("gaps", ["irregular", "sparse", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_keep_counting_advances_by_the_real_gap_across_fl_loop_wraps(bpm, gaps, loop):
    a = groove_a()
    limit = 24 * 384
    with gap_host(gaps, bpm, loop_ticks=loop, patterns=patterns_module(a)) as host:
        start(host)
        host.run_ticks(limit)
        host.stop()
        host.run(1)
    marks = [h - host.play_host_tick for h, _t in host.played_calls()]
    calls = host.played_calls()
    assert sum(1 for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 < t0) >= limit // loop - 1
    got = sorted((e["host_tick"] - host.play_host_tick, e["output"], e["note"]) for e in host.ons())
    assert [x for x in got if x[0] < limit] == fired_at(marks, expected(a, 96, 0, limit), limit)
    assert_clean(host)


def watch(host):
    """After every onTick FL makes while playing: (FL ticks, band tick, anchor, bar ticks)."""
    seen = []
    regular = host.tick

    def tick():
        playing, ticks = host.playing, host.position
        regular()
        b = host.band
        if playing and b.compiled is not None:
            seen.append((ticks, b.band_t, b.anchor, b.compiled.bar))

    host.tick = tick
    return seen


def assert_on_fl_bars(seen, clock):
    """Keep counting: after every played onTick the band's place in its bar is FL's place in its own bar (ticks modulo
    the bar). Follow song position: the band has played up to FL's tick."""
    assert seen
    for ticks, band_t, anchor, bar in seen:
        if clock == "Keep counting":
            assert (band_t - anchor) % bar == ticks % bar, (ticks, band_t, anchor)
        else:
            assert band_t == ticks, (ticks, band_t)


@pytest.mark.parametrize("loop", [576, 360])
@pytest.mark.parametrize("gaps", ["irregular", "sparse", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_keep_counting_re_anchors_to_fl_bars_when_the_fl_loop_is_not_whole_bars(bpm, gaps, loop):
    """A loop of 1.5 bars (or an off-grid 360 ticks) sends FL back to its bar 1 mid-bar. That is no wrap the band
    counts through: it releases what rings and follows FL's bars, so every kick lands with FL's bar lines and beat 2.5."""
    a = groove_a()
    limit = 24 * 384
    with gap_host(gaps, bpm, loop_ticks=loop, patterns=patterns_module(a)) as host:
        seen = watch(host)
        start(host)
        host.run_ticks(limit)
        host.stop()
        host.run(1)
        assert host.band.loop_span is None  # never guessed from a beat or 16th grid
    assert_on_fl_bars(seen, "Keep counting")
    calls = host.played_calls()
    assert sum(1 for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 < t0) >= 12
    want, prev = [], None
    for h, t in calls:  # FL's ticks each onTick sounds: since the last call, or from the loop top after a wrap
        heard = range(max(0, t - 1), t + 1) if prev is None else range(prev + 1 if t > prev else 0, t + 1)
        if any(x % 384 in (0, 240) for x in heard):
            want.append(h)
        prev = t
    assert sorted({e["host_tick"] for e in host.ons() if e["output"] == 1 and e["note"] == 36}) == want
    assert_clean(host)


SPIKES = [(96, 384, 15), (96, 384, 25), (96, 384, 26), (96, 384, 27), (96, 768, 40), (96, 384, 49), (96, 768, 50),
          (960, 3840, 250), (960, 3840, 260)]


def spike_host(ppq, loop, spike, gaps, bpm, patterns):
    """onTick at steady gaps of PPQ / 48 (or once per 512-sample buffer at bpm) and, after FL has wrapped its loop three
    times (so exact wraps have shown the span), one onTick far later than any before, right across the next wrap.
    host.spiked holds the host tick of that late onTick."""
    kw = {"gaps": [max(2, ppq // 48)]} if gaps == "steady" else {"buffer_samples": 512}
    host = Host(ppq=ppq, bpm=bpm, loop_ticks=loop, patterns=patterns, **kw)
    regular = host._next_gap
    host.spiked = []

    def gap():
        g = regular()
        if not host.spiked and host.playing and host.host_tick > 3 * loop and host.position + g >= loop:
            host.spiked.append(host.host_tick + spike)
            return spike
        return g

    host._next_gap = gap
    return host


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
@pytest.mark.parametrize("gaps,bpm", [("steady", 120), ("buffer", 72), ("buffer", 120)])
@pytest.mark.parametrize("ppq,loop,spike", SPIKES)
def test_a_long_ontick_gap_across_a_known_wrap_keeps_fl_bars_and_the_loop_top_downbeat(ppq, loop, spike, gaps, bpm,
                                                                                      clock):
    """One late onTick right across a wrap of a loop whose span exact wraps have shown: Keep counting stays on FL's
    bars for good, Follow song position keeps the loop-top downbeat, and both play every note of the take."""
    a = groove_a()
    limit = 16 * 4 * ppq
    with spike_host(ppq, loop, spike, gaps, bpm, patterns_module(a)) as host:
        host.set(C_CLOCK, clock)
        seen = watch(host)
        start(host)
        host.run_ticks(limit)
        host.stop()
        host.run(1)
        assert host.band.loop_span == loop
        assert spike > host.band.gap_bounds()[1]  # longer than FL has been leaving: not an exact wrap
    assert host.spiked
    assert_on_fl_bars(seen, clock)
    top = [e for e in host.ons() if e["host_tick"] == host.spiked[0] and e["output"] == 1 and e["note"] == 36]
    assert len(top) == 1  # the loop top's kick, in the late onTick itself
    calls = host.played_calls()
    # compared as sets: a late onTick covering two hats sounds them as one voice (two hits of one pitch in one onTick)
    if clock == "Keep counting":
        marks = [h - host.play_host_tick for h, _t in calls]
        got = {(e["host_tick"] - host.play_host_tick, e["output"], e["note"]) for e in host.ons()}
        assert sorted(x for x in got if x[0] < limit) == sorted(set(fired_at(marks, expected(a, ppq, 0, limit), limit)))
    else:
        got = {(e["host_tick"], e["output"], e["note"]) for e in host.ons()}
        assert sorted(got) == sorted(set(song_fired(calls, a, ppq, loop)))
    assert_clean(host)


@pytest.mark.parametrize("gaps", [[1], [3], "buffer"])
@pytest.mark.parametrize("fl_bars", [1, 8])
@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_a_seek_back_to_the_loop_top_from_its_last_beat_is_not_played_as_a_burst(clock, fl_bars, gaps):
    """FL seeks back to the loop top from inside the loop's last beat while playing, after the loop span is known. To
    the band that looks just like a wrap with one late onTick, so it counts the loop's end without sounding it: the
    landing onTick plays no more notes than any other, and the loop top's downbeat sounds."""
    a = groove_a()
    loop = fl_bars * 384
    for back in (10, 30, 60, 90):
        with gap_host(gaps, 120, loop_ticks=loop, patterns=patterns_module(a)) as host:
            host.set(C_CLOCK, clock)
            seen = watch(host)
            start(host)
            host.run_ticks((3 if fl_bars == 1 else 1) * loop + 48)
            assert host.band.loop_span == loop
            while host.position < loop - back:
                host.tick()
            host.seek(0)
            landing = host.host_tick
            host.run_ticks(2 * 384)
            host.stop()
            host.run(1)
        per_call = Counter(e["host_tick"] for e in host.ons())
        assert per_call[landing] <= max(n for h, n in per_call.items() if h != landing), back
        assert 36 in [e["note"] for e in host.ons() if e["host_tick"] == landing and e["output"] == 1], back
        assert_on_fl_bars(seen, clock)
        assert_clean(host)


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
@pytest.mark.parametrize("gaps", ["irregular", "sparse", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_seeks_wraps_and_pauses_with_irregular_gaps_keep_fl_bars_without_bursts(bpm, gaps, clock):
    a = groove_a()
    loop = 2 * 384
    with gap_host(gaps, bpm, loop_ticks=loop, patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, clock)
        seen = watch(host)

        def until(cond):
            while not cond():
                host.tick()

        start(host)
        host.run_ticks(3 * loop)                              # exact wraps show the span
        until(lambda: host.position >= 600)
        host.seek(130)                                        # a seek back mid-loop while playing
        host.run_ticks(300)
        prev = [host.position]

        def wrapped():
            now, was = host.position, prev[0]
            prev[0] = now
            return now < was

        until(wrapped)                                        # FL wrapped after the last onTick: pause past the top
        host.pause()
        host.run(5)
        host.play()
        host.run_ticks(200)
        host.seek((host.position + 200) % loop)               # a seek ahead while playing
        host.run_ticks(100)
        host.pause()
        host.run(5)
        host.seek((host.position + 40) % loop)                # nudged ahead while paused
        host.play()
        host.run_ticks(300)
        host.stop()
        host.run(5)
        host.seek(576)                                        # Play from a playhead parked mid-bar
        host.play()
        host.run_ticks(500)
        until(lambda: loop - 60 <= host.position < loop - 30)
        host.seek(0)                                          # back to the loop top from inside its last beat
        host.run_ticks(2 * loop)
        host.stop()
        host.run(1)
    assert_on_fl_bars(seen, clock)
    assert_clean(host)
    assert host.active == []
    log = host.call_log
    biggest = {"irregular": max(IRREGULAR), "sparse": max(SPARSE), "buffer": 3}[gaps]
    ordinary = {h1 for (h0, t0, p0), (h1, t1, p1) in zip(log, log[1:]) if p0 and p1 and 0 < t1 - t0 <= biggest}
    per_call = Counter(e["host_tick"] for e in host.ons())
    assert max(per_call.values()) <= max(per_call[h] for h in ordinary)  # no onTick after a move plays a burst


def musical_ons(host, gap):
    """(played onTick index, output, note) for a take with a constant gap: the index counts only calls made while
    FL was playing, so a pause does not shift it."""
    index = {h: k for k, (h, _t) in enumerate(host.played_calls())}
    return sorted((index[e["host_tick"]], e["output"], e["note"]) for e in host.ons())


@pytest.mark.parametrize("gap", [5, 7])
@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_a_pause_just_after_an_fl_loop_wrap_resumes_in_step(clock, gap):
    a = groove_a()

    def take(pause):
        with Host(loop_ticks=384, gaps=[gap], patterns=patterns_module(a)) as host:
            host.set(C_CLOCK, clock)
            start(host)
            wraps, prev = 0, host.position
            while wraps < 3 or not 0 < host.position < gap:
                host.tick()
                wraps += host.position < prev
                prev = host.position
            if pause:  # FL wrapped after the last onTick and paused a few ticks past its loop top
                host.pause()
                host.run(6)
                host.play()
            host.run_ticks(6 * 384)
            return musical_ons(host, gap), host.anomalies

    plain, paused = take(False), take(True)
    n = min(k for k, _o, _n in plain[0][-1:]) - 1
    assert [x for x in paused[0] if x[0] <= n] == [x for x in plain[0] if x[0] <= n]
    assert paused[1] == [] and plain[1] == []


def test_stop_in_the_last_beat_of_an_fl_loop_still_restarts_at_bar_one():
    with Host(loop_ticks=384, first_tick=1, patterns=patterns_module(groove_a())) as host:
        start(host)
        host.run(384 + 350)  # the band's bar 2, FL's last beat of its 1-bar loop: a wrap has shown the span
        assert host.band.loop_span == 384
        host.stop()  # the playhead goes to 0 and Play reports tick 1, within a beat of a wrap: still a Stop
        host.run(5)
        before = len(host.ons())
        host.play()
        host.run(20)
    assert [e["note"] for e in host.ons()[before:] if e["output"] == 0][:1] == [36]  # bar 1's root, not bar 3's


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
def test_a_playhead_nudged_ahead_while_paused_is_skipped_not_played_at_once(clock):
    a = groove_a()
    limit = 4 * 384
    with Host(patterns=patterns_module(a)) as host:
        host.set(C_CLOCK, clock)
        start(host)
        host.run_to(500)
        host.pause()
        host.run(10)
        host.seek(560)  # 60 ticks on, under a beat: Play continues from here, in step with FL's bars
        before = len(host.ons())
        host.play()
        host.run_to(limit)
        host.stop()
        host.run(1)
        loose = host.band.gap_bounds()[1]
    after = sorted((e["tick"], e["output"], e["note"]) for e in host.ons()[before:] if e["tick"] < limit)
    want = sorted((max(t, 560), lane, note) for t, lane, note, _ in expected(a, 96, 0, limit) if 560 - loose < t)
    assert after == want
    assert [t for t, _l, _n, _ln in expected(a, 96, 0, limit) if 500 < t <= 560 - loose]  # there was a burst to avoid
    assert host.anomalies == []


@pytest.mark.parametrize("views", [False, True])
@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
@pytest.mark.parametrize("gaps", ["sparse", [23], "buffer"])
def test_a_voice_is_never_released_in_the_ontick_that_triggered_it(gaps, clock, views):
    loop = 384 if clock == "Follow song position" else None
    with gap_host(gaps, 120, loop_ticks=loop, voice_views=views, patterns=patterns_module(tail_groove(), break_groove())) as host:
        host.set(C_CLOCK, clock)
        host.set(C_DROPOUT, "Often")
        start(host)
        host.run_ticks(8 * 384)
        host.set(C_PATTERN, 1)  # a switch, and rest bar lines, cut what was triggered earlier in the same onTick
        host.run_ticks(24 * 384)
        host.stop()
        host.run(1)
    pairs = host.pairs()
    assert len(pairs) > 100
    assert all(off is not None and off["host_tick"] > on["host_tick"] for on, off in pairs)
    assert_clean(host)


def test_two_hits_of_one_pitch_in_one_ontick_sound_as_the_louder_one():
    # onTick every 23 ticks from 0: the calls at 115 and 207 each cover a pair of snares 10 ticks apart
    p = pset("double", {"drums": [(100 / 96, 0.05, 38, 40), (110 / 96, 0.05, 38, 110),    # a ghost, then the backbeat
                                  (2, 0.05, 38, 110), (202 / 96, 0.3, 38, 40)]}, length=4)  # the backbeat, then a ghost
    with Host(gaps=[23], patterns=patterns_module(p)) as host:
        start(host)
        host.run_ticks(384)
        host.stop()
        host.run(1)
    assert [(e["tick"], round(e["velocity"] * 127)) for e in host.ons()] == [(115, 40), (115, 110), (207, 110)]
    assert [(e["kind"], round(e["velocity"] * 127)) for e in host.events if e["tick"] == 115] == [
        ("on", 40), ("off", 40), ("on", 110)]  # the louder hit replaces the ghost
    assert_clean(host)


@pytest.mark.parametrize("gaps", [[1], "irregular", "sparse"])
def test_a_held_chord_is_struck_again_on_the_bar_after_a_rest_bar(gaps):
    p = pset("held", {"bass": [(4 * k, 1, 36 + k, 100) for k in range(4)],
                      "pad": [(0, 12, 60, 60), (0, 12, 64, 60)],        # rings bars 1-3, through rest bar 2
                      "comp": [(7.75, 1.5, 67, 70), (4.5, 6, 72, 70)]})  # a push out of bar 2; a stab started in it
    limit = 4 * 384
    with gap_host(gaps, 120, patterns=patterns_module(p)) as host:
        chance = host.module.DROPOUT_CHANCE[2]
        seed = next(s for s in range(100) if [n for n in range(4) if host.module.dropout_bar(s, n, chance)] == [1])
        host.set(C_DROPOUT, "Often")
        host.set(C_DROPOUT_SEED, seed)
        start(host)
        host.run_to(limit)
        host.stop()
        host.run(1)
    marks = [t for _h, t in host.played_calls()]
    assert played(host, limit) == fired_at(marks, without_rests(expected(p, 96, 0, limit), {1}), limit)
    restruck = sorted((e["output"], e["note"], e["length"]) for e in host.ons() if 768 <= e["tick"] < 768 + 24)
    assert (3, 60, 384) in restruck and (3, 64, 384) in restruck and (2, 72, 240) in restruck
    assert [(e["tick"] <= 744 + 23, e["length"]) for e in host.ons() if e["note"] == 67] == [(True, 144)]  # the push played
    assert_clean(host)


@pytest.mark.parametrize("clock", ["Keep counting", "Follow song position"])
@pytest.mark.parametrize("gaps", ["irregular", "sparse", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_pause_resume_and_a_switch_while_paused_with_irregular_gaps(bpm, gaps, clock):
    a, b = groove_a(), groove_b()
    limit = 8 * 384
    with gap_host(gaps, bpm, patterns=patterns_module(a, b)) as host:
        host.set(C_CLOCK, clock)
        start(host)
        host.run_to(300)
        host.pause()
        host.run(15)
        host.play()
        host.run_to(576)
        host.pause()
        host.run(15)
        host.set(C_PATTERN, 1)
        host.run(15)
        assert host.active == [] and host.band.pending == 1
        host.play()
        host.run_to(limit)
        switches = [s[:2] for s in host.band.switches if s[0] is not None]
        host.stop()
        host.run(1)
    assert switches == [(768, 1)]
    marks = [t for _h, t in host.played_calls()]
    want = without_pushes_into(expected(a, 96, 0, 768), 768) + expected(b, 96, 768, limit)
    assert played(host, limit) == fired_at(marks, want, limit)
    assert_clean(host)


# -- the Pattern knob and voice bookkeeping -------------------------------------------------------------------------

@pytest.mark.parametrize("store", mock.KNOB_STORES)
@pytest.mark.parametrize("read", mock.KNOB_READS)
def test_pattern_knob_value_round_trips_all_64_indexes(store, read):
    with Host(knob_store=store, knob_read=read, patterns=patterns_module(groove_a())) as host:
        value = host.module.pattern_knob_value
        for i in range(64):
            host.form.setNormalizedValue(C_PATTERN, value(i))
            assert host.get(C_PATTERN) == i
        assert value(-3) == value(0) and value(99) == 1.0
    old = [i for i in range(64) if math.floor(mock.stored_normalized(i / 63.0, "16bit") * 63) != i]
    assert len(old) > 32  # what idx / 63 did under a 16-bit step read back by truncation

@pytest.mark.parametrize("store,read", [("16bit", "floor"), ("float32", "floor"), ("float", "round")])
def test_live_file_moves_the_pattern_knob_without_pulling_the_band_one_low(tmp_path, store, read):
    live = tmp_path / "arsenal_live.json"
    sets = [pset("p%d" % i, {"bass": [(0, 1, 24 + i, 100)]}, length=4) for i in range(64)]
    with Host(knob_store=store, knob_read=read, patterns=patterns_module(groove_a(), live_path=str(live))) as host:
        stamp_write(live, {"version": 1, "rev": 0, "current": 0, "patterns": sets})
        host.set(C_LIVE, 1)
        host.run(8)
        for i in list(range(64)) + [0, 63, 1, 62]:
            stamp_write(live, {"version": 1, "rev": i + 1, "current": i, "patterns": sets})
            host.run(4 * 96 + 8)  # stopped: the file is read every 4 beats' worth of calls, the knob polled after
            assert (host.band.current, host.get(C_PATTERN)) == (i, i)
        host.play()
        host.run(2 * 384)
    assert {e["note"] for e in host.ons()} == {24 + 62}
    assert host.anomalies == []


@pytest.mark.parametrize("order", ["before", "after"])
def test_wrapped_voices_are_cut_by_mute_switch_and_retrigger_and_released_once(order):
    a, b = groove_a(), groove_b()
    overlap = pset("overlap", {"pad": [(0, 5, 48, 60)], "bass": [(0, 0.5, 36, 90)]}, length=4)
    with Host(voice_views=True, auto_release=order, patterns=patterns_module(a, b, overlap)) as host:
        start(host)
        host.run_to(100)  # bass root and pad ringing
        host.set("Mute: Pad", 1)
        host.run(8)
        assert not [v for v in host.active if v.output == 3]  # cut at once, not left to FL's countdown
        host.set("Mute: Pad", 0)
        host.run_to(364)
        host.set(C_PATTERN, 1)  # lands on 384; bar 1's comp push (tick 360, a beat long) started before the knob moved
        host.run_to(700)
        push = [(on, off) for on, off in host.pairs() if on["output"] == 2 and on["tick"] == 360]
        assert len(push) == 3 and all(off is not None and off["tick"] == 384 and not off["auto"] for _on, off in push)
        host.set(C_PATTERN, 2)  # lands on 768; its 5-beat pad retriggers over itself at 1152, 1536, 1920
        host.run_to(2000)
        host.set(C_PANIC, 1)
        host.run(8)
        assert host.active == []
        host.run(384)
        host.stop()
        host.run(1)
    for t in (1152, 1536, 1920):
        at = [(e["kind"], e["note"], e["auto"]) for e in host.events if e["output"] == 3 and e["tick"] == t]
        assert at == [("off", 48, False), ("on", 48, False)]  # the band released it before sounding it again
    assert_clean(host)
    assert host.active == []


# -- dropout ------------------------------------------------------------------------------------------------------

def break_groove(pid="break"):
    """A 4-bar groove built to test rests: pads that ring over the next bar line, comp pushes into the next bar."""
    lanes = {"bass": [(4 * k, 1, 36 + k, 100) for k in range(4)],
             "drums": [(b, 0.25, 42 if b % 2 else 36, 90) for b in range(16)],
             "comp": [(4 * k + 3.75, 1, 67 + k, 70) for k in range(4)],
             "pad": [(0, 6, 60, 60), (8, 6, 64, 60)]}
    return pset(pid, lanes)


def rest_bars(host, seed, level, bars, first=0):
    band = host.module
    return {first + n for n in range(bars) if band.dropout_bar(seed, n, band.DROPOUT_CHANCE[level])}


def without_rests(notes, rests, ppq=96, first_bar=0):
    """notes minus what rests: every lane but bass (0) on a rest bar, and a push over a bar line into a rest bar; plus
    the comp and pad notes (lanes 2, 3) struck again on the bar after a rest bar for what is left of them (a push over
    that bar line is not: it played)."""
    bar = 4 * ppq
    out = []
    for t, lane, note, ln in notes:
        if lane != 0:
            n = t // bar
            ahead = (n + 1) * bar - t
            if (n + 1 if ahead <= ppq // 2 and ln > ahead else n) in rests:
                continue
        out.append((t, lane, note, ln))
    for r in rests:
        line = (r + 1) * bar
        out += [(line, lane, note, ln - (line - t)) for t, lane, note, ln in notes
                if lane in (2, 3) and ppq // 2 < line - t < ln]
    return out


def largest_gap(host):
    calls = host.played_calls()
    return max([t1 - t0 for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 > t0] or [1])


def assert_rests_are_silent(host, rests):
    """On a rest bar nothing but bass starts (a push into the next bar aside), and whatever else was ringing over its
    bar line ends there: on the first onTick at or after it, at most one gap later in host time."""
    gap = largest_gap(host)
    for on, off in host.pairs():
        if on["output"] == 0:
            continue
        for r in rests:
            s = r * 384
            assert not s <= on["tick"] < s + 384 - 48, "lane %d note at %d on rest bar %d" % (on["output"], on["tick"], r)
            if on["tick"] < s < on["tick"] + on["length"]:
                assert off["host_tick"] <= on["host_tick"] + (s - on["tick"]) + gap, (on, off, r)


def test_dropout_rule_is_deterministic_rare_or_often_and_never_two_in_a_row():
    band = mock.load_band_parsers()
    rare = [n for n in range(2000) if band.dropout_bar(5, n, band.DROPOUT_CHANCE[1])]
    often = [n for n in range(2000) if band.dropout_bar(5, n, band.DROPOUT_CHANCE[2])]
    assert [n for n in range(2000) if band.dropout_bar(5, n, 0.0)] == []
    assert 0 not in often and all(b - a > 1 for a, b in zip(often, often[1:]))
    assert all(b - a > 1 for a, b in zip(rare, rare[1:]))
    assert 120 < len(rare) < 250 and 320 < len(often) < 520  # about 1 bar in 11, and 1 in 5
    assert often == [n for n in range(2000) if band.dropout_bar(5, n, band.DROPOUT_CHANCE[2])]
    assert often != [n for n in range(2000) if band.dropout_bar(6, n, band.DROPOUT_CHANCE[2])]


def test_dropout_leans_on_the_last_bar_of_a_phrase():
    band = mock.load_band_parsers()
    for level in (1, 2):
        by_place = [0, 0, 0, 0]
        for seed in range(100):
            for n in range(64):
                by_place[n % 4] += band.dropout_bar(seed, n, band.DROPOUT_CHANCE[level])
        assert by_place[3] > 2 * max(by_place[:3])  # bar 4 of 4, the bar before a phrase top: a breath, not a glitch
        assert by_place[1] > by_place[0] and by_place[1] > by_place[2]  # then the middle of the phrase


@pytest.mark.parametrize("gaps", [[1], "irregular", "sparse", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_dropout_bars_rest_all_but_bass_and_cut_what_rings(bpm, gaps):
    p = break_groove()
    bars = 40
    limit = bars * 384
    with gap_host(gaps, bpm, patterns=patterns_module(p)) as host:
        host.set(C_DROPOUT, "Often")
        host.set(C_DROPOUT_SEED, 7)
        start(host)
        host.run_to(limit)
        host.stop()
        host.run(1)
        rests = rest_bars(host, 7, 2, bars)
    assert len(rests) >= 5
    marks = [t for _h, t in host.played_calls()]
    assert played(host, limit) == fired_at(marks, without_rests(expected(p, 96, 0, limit), rests), limit)
    assert_rests_are_silent(host, rests)
    cut = [(on, off) for on, off in host.pairs() if on["output"] == 3 and off["tick"] // 384 in rests
           and off["tick"] < on["tick"] + on["length"]]
    assert cut and not any(off["auto"] for _on, off in cut)  # pads ringing into a rest bar were cut by the band
    assert_clean(host)


def test_dropout_seed_replays_and_bass_never_rests():
    p = break_groove()

    def take(level, seed):
        with Host(patterns=patterns_module(p)) as host:
            host.set(C_DROPOUT, level)
            host.set(C_DROPOUT_SEED, seed)
            start(host)
            host.run(32 * 384)
        return sorted((e["tick"], e["output"], e["note"]) for e in host.ons())

    off, one, again, other = take("Off", 3), take("Often", 3), take("Often", 3), take("Often", 4)
    assert one == again and one != other and one != off
    assert [x for x in one if x[1] == 0] == [x for x in off if x[1] == 0]


@pytest.mark.parametrize("lane", ["Drums", "Bass"])
def test_band_instances_on_the_same_seed_rest_together(lane):
    p = break_groove()
    with Host(patterns=patterns_module(p)) as host:
        host.set(C_LANE, lane)
        host.set(C_DROPOUT, "Often")
        host.set(C_DROPOUT_SEED, 11)
        start(host)
        host.run(32 * 384)
        rests = rest_bars(host, 11, 2, 32)
    heard = {e["tick"] // 384 for e in host.ons()}
    assert heard == (set(range(32)) - rests if lane == "Drums" else set(range(32)))


@pytest.mark.parametrize("action", ["knob", "reload"])
def test_a_pattern_switch_bar_is_never_a_dropout_bar(action):
    a, b = break_groove(), break_groove("break-b")
    with Host(patterns=patterns_module(a, b)) as host:
        host.set(C_DROPOUT, "Often")
        host.set(C_DROPOUT_SEED, 2)
        rests = sorted(rest_bars(host, 2, 2, 64))
        r = next(n for n in rests if n >= 2)
        start(host)
        host.run_to(r * 384 - 100)
        host.set(C_PATTERN, 1) if action == "knob" else host.set(C_RELOAD, 1)
        host.run_to((r + 12) * 384)
        switches = [s[:2] for s in host.band.switches if s[0] is not None]
        host.stop()
        host.run(1)
    assert switches == [(r * 384, 1 if action == "knob" else 0)]
    drums_r = [e for e in host.ons() if e["output"] == 1 and r * 384 <= e["tick"] < (r + 1) * 384]
    assert len(drums_r) == 4  # bar r would have rested: as the switch bar it plays in full
    # the old pattern's comp push into the switch bar would be cut on its bar line at once, so it is skipped
    assert [e for e in host.ons() if e["output"] == 2 and r * 384 - 48 <= e["tick"] < r * 384] == []
    if action == "knob":  # a new pattern counts its bars from the switch
        rests_after = {r + n for n in rest_bars(host, 2, 2, 12)}
    else:  # an edit of the same pattern keeps its bar count, only the switch bar itself is spared
        rests_after = {n for n in rests if r < n < r + 12}
    heard = {n for n in range(r + 1, r + 12) if not [e for e in host.ons() if e["output"] == 1 and e["tick"] // 384 == n]}
    assert heard == rests_after
    assert_rests_are_silent(host, rests_after)
    assert_clean(host)


@pytest.mark.parametrize("gaps", ["irregular", "buffer"])
@pytest.mark.parametrize("bpm", [72, 120])
def test_dropout_survives_pause_resume_and_song_loop_wraps(bpm, gaps):
    p = break_groove()
    with gap_host(gaps, bpm, loop_ticks=4 * 384, patterns=patterns_module(p)) as host:
        host.set(C_CLOCK, "Follow song position")
        host.set(C_DROPOUT, "Often")
        seed = next(s for s in range(100) if rest_bars(host, s, 2, 4) == {1, 3})
        host.set(C_DROPOUT_SEED, seed)
        start(host)
        host.run_to(384 + 200)  # into rest bar 1
        host.pause()
        host.run(20)
        assert host.active == []
        host.play()
        host.run_ticks(4 * 4 * 384)
        host.stop()
        host.run(1)
    calls = host.played_calls()
    assert sum(1 for (_h0, t0), (_h1, t1) in zip(calls, calls[1:]) if t1 < t0) >= 3
    drum_bars = [e["tick"] // 384 for e in host.ons() if e["output"] == 1]
    assert set(drum_bars) == {0, 2} and drum_bars.count(0) >= 4 * 4  # the same song bars rest on every pass
    assert_rests_are_silent(host, {1, 3})
    assert_clean(host)


def test_tempo_changes_do_not_move_bar_lines():
    a = groove_a()
    with Host(bpm=120, patterns=patterns_module(a)) as host:
        start(host)
        host.run(500)
        host.bpm = 72
        host.run(4 * 384 - 500)
    got = sorted((e["tick"], e["output"], e["note"]) for e in host.ons())
    assert got == [(t, lane, note) for t, lane, note, _ in expected(a, 96, 0, 4 * 384)]


# -- lanes, drums, feel -------------------------------------------------------------------------------------------

DRUM_NOTES = [35, 36, 37, 38, 41, 42, 44, 45, 46, 48, 49, 50, 51, 57, 59, 60]


@pytest.mark.parametrize("map_name,want", [
    ("GM", DRUM_NOTES),
    ("FPC", [36, 36, 37, 38, 41, 42, 42, 45, 46, 48, 49, 50, 51, 49, 51, 60]),
    ("AD2 default", [36, 36, 42, 38, 65, 49, 48, 67, 55, 69, 77, 71, 60, 79, 84]),  # 60 has no GM piece: dropped
])
def test_drum_maps_turn_gm_notes_into_the_plugin_keys(map_name, want):
    p = pset("drum-map", {"drums": [(i * 0.25, 0.1, n, 100) for i, n in enumerate(DRUM_NOTES)]}, length=4)
    with Host(patterns=patterns_module(p)) as host:
        host.set(C_DRUM_MAP, map_name)
        start(host)
        host.run(384)
    got = [e["note"] for e in sorted(host.ons(), key=lambda e: e["tick"]) if e["output"] == 1]
    assert got == want
    assert host.anomalies == []


def test_extra_drum_maps_from_the_module_join_the_combo():
    p = pset("drum-map", {"drums": [(0, 0.1, 36, 100), (1, 0.1, 38, 100)]}, length=4)
    with Host(patterns=patterns_module(p, drum_maps={"My kit": {"36": 24}})) as host:
        assert host.form.options(C_DRUM_MAP)[-1] == "My kit"
        host.set(C_DRUM_MAP, "My kit")
        start(host)
        host.run(384)
    assert [e["note"] for e in host.ons()] == [24]


@pytest.mark.parametrize("lane", ["Bass", "Drums", "Comp", "Pad"])
def test_one_lane_per_instance_plays_on_output_one(lane):
    a = groove_a()
    with Host(patterns=patterns_module(a)) as host:
        host.set(C_LANE, lane)
        start(host)
        host.run(4 * 384)
    lane_i = LANES.index(lane.lower())
    want = sorted((t, note) for t, li, note, _ in expected(a, 96, 0, 4 * 384) if li == lane_i)
    assert sorted((e["tick"], e["note"]) for e in host.ons()) == want
    assert {e["output"] for e in host.ons()} == {0}


def test_mute_silences_a_lane_at_once_and_unmute_brings_it_back():
    a = groove_a()
    with Host(patterns=patterns_module(a)) as host:
        start(host)
        host.run(100)  # bass root (len 1.5 beats) and pad are sounding
        host.set("Mute: Pad", 1)
        host.run(8)
        assert not [v for v in host.active if v.output == 3]
        host.run(2 * 384)
        host.set("Mute: Pad", 0)
        host.run(2 * 384)
        host.stop()
        host.run(1)
    pad_ons = sorted(e["tick"] for e in host.ons() if e["output"] == 3)
    assert pad_ons == [0, 0, 1152, 1152, 1536, 1536]  # muted over bars 2 and 3 (ticks 384, 768)
    assert_clean(host)


def test_humanize_stays_in_range_varies_by_loop_and_replays_identically():
    p = pset("vel", {"bass": [(i * 0.5, 0.25, 40, 100) for i in range(8)]}, length=4)

    def take(amount):
        with Host(patterns=patterns_module(p)) as host:
            host.set(C_HUMANIZE, amount)
            start(host)
            host.run(2 * 384)
        return [round(e["velocity"] * 127) for e in host.ons()]

    assert take(0) == [100] * 16
    one, again = take(1), take(1)
    assert one == again
    assert all(80 <= v <= 120 for v in one)
    assert len(set(one)) > 3 and one[:8] != one[8:]


def test_swing_moves_only_the_off_beats_of_its_grid():
    p = pset("swing", {"drums": [(0, 0.1, 36, 100), (0.25, 0.1, 42, 100), (0.5, 0.1, 38, 100),
                                 (0.75, 0.1, 46, 100), (1 + 1 / 3, 0.1, 51, 100)]}, length=4)

    def ticks(swing, grid):
        with Host(patterns=patterns_module(p)) as host:
            host.set(C_SWING, swing)
            host.set(C_GRID, grid)
            start(host)
            host.run(384)
        return {e["note"]: e["tick"] for e in host.ons()}

    assert ticks(0, "8th") == {36: 0, 42: 24, 38: 48, 46: 72, 51: 128}
    assert ticks(1, "8th") == {36: 0, 42: 24, 38: 64, 46: 72, 51: 128}  # the off-8th lands on the triplet
    assert ticks(0.5, "16th") == {36: 0, 42: 28, 38: 48, 46: 76, 51: 128}


def test_turning_swing_mid_loop_never_plays_a_note_twice():
    p = pset("swing", {"drums": [(0.5, 0.1, 38, 100), (1.5, 0.1, 40, 100)]}, length=4)
    with Host(patterns=patterns_module(p)) as host:
        start(host)
        host.run(52)  # the off-8th at tick 48 has played
        host.set(C_SWING, 1)
        host.set(C_GRID, "8th")
        host.run(384 * 2)
    assert sorted((e["tick"], e["note"]) for e in host.ons()) == [(48, 38), (160, 40), (448, 38), (544, 40)]


def test_a_pitch_still_ringing_is_released_before_it_sounds_again():
    p = pset("overlap", {"pad": [(0, 5, 48, 60)]}, length=4)  # longer than its loop
    with Host(patterns=patterns_module(p)) as host:
        start(host)
        host.run(3 * 384)
        host.stop()
        host.run(1)
    at_384 = [(e["kind"], e["note"]) for e in host.events if e["tick"] == 384]
    assert at_384 == [("off", 48), ("on", 48)]
    assert_clean(host)
    assert len([v for v in host.active]) == 0


def test_panic_is_momentary_and_releases_everything():
    with Host(patterns=patterns_module(groove_a())) as host:
        start(host)
        host.run(100)
        ringing = list(host.active)
        assert ringing
        host.set(C_PANIC, 1)
        host.run(8)
        assert host.get(C_PANIC) == 0
        assert not any(any(v is r for r in ringing) for v in host.active)
        host.run(384)
        assert host.active  # the band plays on after a panic
    assert host.anomalies == []


def test_bar_pulse_output_rises_on_every_bar_line():
    with Host(patterns=patterns_module(groove_a())) as host:
        start(host)
        host.run(4 * 384 + 20)  # past bar 5's line and its 32nd-note pulse (12 ticks at PPQ 96)
    values = host.controllers["Bar pulse"]
    assert values.count(1) == 5  # bars 1 to 5
    assert values[-1] == 0


def test_controls_are_polled_not_read_every_tick():
    with Host(ppq=960, patterns=patterns_module(groove_a())) as host:
        start(host)
        host.run(4 * 960)
        per_tick = host.form.reads / host.host_tick
    assert per_tick < 1.0  # 17 controls every PPQ/24 ticks


# -- pattern delivery ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("breakage", [
    lambda d: "not a dict",
    lambda d: {**d, "version": 2},
    lambda d: {**d, "id": ""},
    lambda d: {**d, "meter": [4, 3]},
    lambda d: {**d, "length_beats": 6},
    lambda d: {**d, "length_beats": 0},
    lambda d: {**d, "lanes": {"bas": {"notes": []}}},
    lambda d: {**d, "lanes": {"bass": [1, 2]}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": 0, "len": 1, "note": 128, "vel": 100}]}}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": 0, "len": 1, "note": True, "vel": 100}]}}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": 0, "len": 1, "note": 40, "vel": 0}]}}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": 0, "len": 0, "note": 40, "vel": 100}]}}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": float("nan"), "len": 1, "note": 40, "vel": 100}]}}},
    lambda d: {**d, "lanes": {"bass": {"notes": [{"beat": "1", "len": 1, "note": 40, "vel": 100}]}}},
])
def test_broken_pattern_sets_are_refused_whole(breakage):
    band = mock.load_band_parsers()
    with pytest.raises(band.PatternError):
        band.parse_pattern_set(breakage(groove_b()))


def test_contract_shapes_that_are_accepted():
    band = mock.load_band_parsers()
    twelve_eight = pset("sunday", {"bass": [(-0.25, 0.5, 30, 90), (11.75, 1, 31, 90)]}, length=12, meter=(12, 8))
    parsed = band.parse_pattern_set(twelve_eight)
    assert parsed["bar_beats"] == 6.0 and parsed["length_beats"] == 12.0
    playlist = band.parse_playlist([groove_a(), groove_b()])
    assert playlist["current"] == 0 and len(playlist["patterns"]) == 2
    assert band.parse_playlist({"version": 1, "current": 9, "patterns": [groove_b()]})["current"] == 0
    assert band.parse_playlist(groove_b())["patterns"][0]["id"] == "groove-b"
    with pytest.raises(band.PatternError):
        band.parse_playlist({"version": 1, "patterns": [groove_a(), {**groove_b(), "version": 7}]})
    with pytest.raises(band.PatternError):
        band.parse_playlist({"version": 1, "current": -1, "patterns": [groove_b()]})


def test_a_refused_baked_pattern_becomes_silence_so_indexes_stay_put():
    broken = {**groove_a(), "id": "broken", "length_beats": 5}
    with Host(patterns=patterns_module(groove_a(), broken, groove_b())) as host:
        host.set(C_PATTERN, 2)
        start(host)
        host.run(384)
        assert host.band.pattern["id"] == "groove-b"
        assert "INVALID" in host.form.description and "(1 refused)" in host.form.description
    assert {e["note"] for e in host.ons()} <= notes_of(groove_b())


def test_no_patterns_module_plays_the_fallback_groove():
    with Host() as host:
        start(host)
        host.run(384)
        assert "fallback" in host.band.module_status
    assert len(host.ons()) > 5
    assert host.anomalies == []


def test_example_patterns_module_is_valid_and_plays_clean(monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    with Host(patterns_dir=VFX_DIR, bpm=84) as host:
        assert host.band.module_status == "2 patterns from arsenal_patterns"
        host.set(C_DRUM_MAP, "AD2 default")
        host.set(C_PATTERN, 1)
        start(host)
        host.run(8 * 384)
        host.stop()
        host.run(1)
    assert "arsenal_patterns" not in sys.modules or getattr(sys.modules["arsenal_patterns"], "__file__", "") != str(EXAMPLE_PATTERNS)
    assert_clean(host)
    comp = sorted({e["tick"] for e in host.ons() if e["output"] == 2})
    assert 1512 in comp  # bar 1's chord pushed to beat -0.25 wraps to the last 16th of the loop
    assert mock.check(EXAMPLE_PATTERNS, out=lambda line: None) == 0


def test_reload_reimports_a_regenerated_module_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    src = tmp_path / "arsenal_patterns.py"
    stamp_write(src, "VERSION = 1\nLIVE_PATH = None\nPATTERNS = [%r]\n" % (groove_a(),))
    with Host(patterns_dir=tmp_path) as host:
        start(host)
        host.run(384 + 20)
        stamp_write(src, "VERSION = 1\nLIVE_PATH = None\nPATTERNS = [%r, %r]\n" % (groove_b(), groove_a()))
        host.set(C_RELOAD, 1)
        host.run(400)
        assert host.band.pattern["id"] == "groove-b"
        assert [s[0] for s in host.band.switches if s[0] is not None] == [768]
    assert host.anomalies == []


def test_live_file_switches_on_a_bar_line_and_keeps_the_last_good_patterns(tmp_path):
    live = tmp_path / "arsenal_live.json"
    stamp_write(live, {"version": 1, "rev": 1, "current": 0, "patterns": [groove_b()]})
    with Host(patterns=patterns_module(groove_a(), live_path=str(live))) as host:
        host.set(C_LIVE, 1)
        host.run(1)  # stopped: read at once
        assert host.band.pattern["id"] == "groove-b"
        host.play()
        host.run(2 * 384 + 10)
        stamp_write(live, {"version": 1, "rev": 2, "current": 1, "patterns": [groove_b(), groove_a("live-a")]})
        host.run(384)  # read one beat before the bar line at 1152
        assert [s[:2] for s in host.band.switches if s[0] is not None] == [(1152, 1)]
        assert host.get(C_PATTERN) == 1  # the knob shows what the file chose
        stamp_write(live, '{"version": 1, "patterns": [')  # a half-written file
        host.run(2 * 384)
        assert host.band.pattern["id"] == "live-a" and "refused" in host.band.live_error
        live.unlink()
        host.run(2 * 384)
        assert host.band.pattern["id"] == "live-a" and "cannot read" in host.band.live_error
        stamp_write(live, {"version": 1, "rev": 3, "current": 0, "patterns": [groove_b(), groove_a("live-a")]})
        host.run(2 * 384)
        assert host.band.pattern["id"] == "groove-b"
        switches = [s for s in host.band.switches if s[0] is not None]
        assert all((t - anchor) % bar == 0 for t, _i, anchor, bar in switches)
        reads = host.band.live_reads
        bars_played = host.position // 384
        host.set(C_LIVE, 0)
        host.run(2 * 384)
        assert host.band.pattern["id"] == "groove-a"  # back to the baked module on the next bar
    assert reads <= bars_played + 2  # one read per bar, not per tick
    assert host.anomalies == []


def test_live_file_missing_from_the_start_plays_the_baked_patterns(tmp_path):
    with Host(patterns=patterns_module(groove_a(), live_path=str(tmp_path / "nope.json"))) as host:
        host.set(C_LIVE, 1)
        start(host)
        host.run(2 * 384)
        assert host.band.pattern["id"] == "groove-a" and "cannot read" in host.band.live_error
        assert host.band.log.count(host.band.live_error) == 1  # said once, not every bar
    assert host.ons()


def test_cli_check_and_simulate(tmp_path, capsys):
    assert mock.main(["check", str(EXAMPLE_PATTERNS)]) == 0
    assert "ok: 2 pattern sets" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": 1, "patterns": [{**groove_b(), "length_beats": 7}]}), encoding="utf-8")
    assert mock.main(["check", str(bad)]) == 1
    assert "refused" in capsys.readouterr().out
    assert mock.main(["simulate", str(EXAMPLE_PATTERNS), "--bars", "1", "--pattern", "1"]) == 0
    out = capsys.readouterr().out
    assert "  1.1.000  on " in out and "ANOMALY" not in out
    assert mock.main(["simulate", str(EXAMPLE_PATTERNS), "--bars", "8", "--pattern", "1", "--gaps", "1,4,2,7",
                      "--dropout", "Often", "--dropout-seed", "3", "--clock", "Follow song position",
                      "--loop-ticks", "768"]) == 0
    out = capsys.readouterr().out
    assert "  on  " in out and "ANOMALY" not in out
    assert mock.main(["simulate", str(EXAMPLE_PATTERNS), "--bars", "2", "--gaps", "buffer:512"]) == 0
    assert "ANOMALY" not in capsys.readouterr().out
    with pytest.raises(SystemExit):
        mock.main(["simulate", str(EXAMPLE_PATTERNS), "--gaps", "1,x"])
