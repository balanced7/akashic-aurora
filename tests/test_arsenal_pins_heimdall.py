"""Blind pins for the arsenal kernel API v0 (First Light).

Written by Heimdall (deepseek) from FIRST-LIGHT-SPEC.md alone, BEFORE the kernel
implementation exists, so the kernel has to satisfy tests its author didn't write.
RED is expected until Vandor lands arsenal/*.py.

Contract source: arsenal/FIRST-LIGHT-SPEC.md -> "Kernel API v0 (Python)".
No network. pytest + tmp_path. Importing arsenal fails (RED) until it lands.

Pin coverage (the ones that matter):
  - exact rational time over long runs (30000/1001 for 10 minutes)
  - float ticks refused
  - cross-epoch comparison raising StaleEpoch
  - epoch bumps and is_current
  - ClockMap exactness
  - check_caps reasons
  - graph validation catching each listed problem
  - parse_text chains and map lines
  - plan marking engine-crossing media edges as copies, and GPL profiles
  - the take ledger refusing stale-epoch events, non-incremental epoch events,
    and writes to closed takes
"""

import json
from fractions import Fraction
from pathlib import Path

import pytest

from arsenal import timebase
from arsenal import mediatypes
from arsenal import registry
from arsenal import graph as graphmod
from arsenal import plan as planmod
from arsenal import take as takemod


# ---------------------------------------------------------------- timebase

def test_exact_rational_over_long_runs():
    # tb is SECONDS PER TICK. 29.97 fps == 1001/30000 s per tick.
    # 10 minutes == 600 s, which is NOT a whole number of 29.97 frames (17982.018...).
    # So exact rescale must REFUSE, and inexact must round to 17982 frames.
    frames_tb = timebase.tb(1001, 30000)
    # 600 s at 1/90000 (the media timebase) is 54,000,000 ticks exactly.
    ten_min = timebase.TimeRef("media", 0, 54_000_000, timebase.tb(1, 90000))
    # exact rescale to film-frame timebase is not representable:
    with pytest.raises(ValueError):
        ten_min.rescale(frames_tb, exact=True)
    # inexact rounds to 17982 frames:
    got = ten_min.rescale(frames_tb, exact=False)
    assert got.ticks == 17982
    # and 18000 frames at 1001/30000 is exactly 3003/5 s:
    frames = timebase.TimeRef("media", 0, 18000, frames_tb)
    assert frames.seconds == Fraction(3003, 5)


def test_timebase_parse_and_format():
    assert timebase.parse_tb("1001/30000") == Fraction(1001, 30000)
    assert timebase.format_tb(Fraction(1001, 30000)) == "1001/30000"
    assert timebase.format_tb(Fraction(1, 48000)) == "1/48000"


def test_tb_rejects_nonpositive():
    with pytest.raises(ValueError):
        timebase.tb(0, 1)
    with pytest.raises(ValueError):
        timebase.tb(-1, 1)
    with pytest.raises(ValueError):
        timebase.tb(1, 0)  # zero denominator -> ValueError (not ZeroDivisionError)


def test_tb_rejects_above_one_second():
    # a timebase > 1 s per tick is a rate passed by mistake; refused with the inverse named
    with pytest.raises(ValueError):
        timebase.tb(30000, 1001)  # 29.97 s/tick -- the rate mistake, inverted
    with pytest.raises(ValueError):
        timebase.tb(48000, 1)  # 48000 s/tick


def test_float_ticks_refused():
    with pytest.raises(TypeError):
        timebase.TimeRef("media", 0, 1.5, Fraction(1, 48000))


def test_integral_float_ticks_refused():
    # even a whole float is still a float, and must be refused
    with pytest.raises(TypeError):
        timebase.TimeRef("media", 0, 1.0, Fraction(1, 48000))


def test_bool_ticks_refused():
    with pytest.raises(TypeError):
        timebase.TimeRef("media", 0, True, Fraction(1, 48000))
    with pytest.raises(TypeError):
        timebase.TimeRef("media", 0, False, Fraction(1, 48000))


def test_float_timebase_refused():
    with pytest.raises(TypeError):
        timebase.TimeRef("media", 0, 48000, 1.0 / 48000)


def test_timebase_accepts_int_and_fraction():
    a = timebase.TimeRef("media", 0, 5, 1)  # int timebase of 1 == 1 s/tick
    assert a.seconds == Fraction(5)
    b = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))
    assert b.seconds == Fraction(1)
    # an int timebase above 1 s/tick is refused (a rate passed by mistake)
    with pytest.raises(ValueError):
        timebase.TimeRef("media", 0, 1, 48000)


def test_seconds_is_fraction():
    tr = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))
    assert isinstance(tr.seconds, Fraction)
    assert tr.seconds == Fraction(1)


def test_rescale_exact():
    a = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))  # 1s
    b = a.rescale(Fraction(1, 90000))
    assert b.ticks == 90000
    assert b.seconds == Fraction(1)


def test_rescale_exact_raises_when_inexact():
    # 1 tick at 1/7 s rescaled to 1/48000: 48000/7 is not an integer, so exact must refuse
    a = timebase.TimeRef("media", 0, 1, Fraction(1, 7))
    with pytest.raises(ValueError):
        a.rescale(Fraction(1, 48000), exact=True)


def test_rescale_inexact_rounds_half_to_even():
    # Vandor's distinguishing case: 1 tick at 1/96000 rescaled to 1/48000 gives 0;
    # 3 ticks give 2 (half-to-even, not half-up, on the .5 boundary).
    one = timebase.TimeRef("media", 0, 1, Fraction(1, 96000))
    assert one.rescale(Fraction(1, 48000), exact=False).ticks == 0
    three = timebase.TimeRef("media", 0, 3, Fraction(1, 96000))
    assert three.rescale(Fraction(1, 48000), exact=False).ticks == 2


def test_comparison_same_clock_same_epoch_exact_across_timebases():
    a = timebase.TimeRef("media", 0, 30000, Fraction(1, 30000))  # 1 s
    b = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))  # 1 s
    assert a == b
    assert not (a < b)
    assert not (a > b)
    assert a <= b
    assert a >= b


def test_comparison_exact_across_odd_timebases():
    # 1001 ticks at 1/30000 == 48048 ticks at 1/1440000 (both exactly 1001/30000 s)
    a = timebase.TimeRef("media", 0, 1001, Fraction(1, 30000))
    b = timebase.TimeRef("media", 0, 48048, Fraction(1, 1440000))
    assert a == b
    assert not (a < b)


def test_comparison_order():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    b = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))
    assert a < b
    assert b > a
    assert a <= b
    assert b >= a


def test_clock_mismatch_on_compare():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    b = timebase.TimeRef("audio", 0, 0, Fraction(1, 48000))
    with pytest.raises(timebase.ClockMismatch):
        a < b
    with pytest.raises(timebase.ClockMismatch):
        a == b


def test_stale_epoch_on_compare():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    b = timebase.TimeRef("media", 1, 0, Fraction(1, 48000))
    with pytest.raises(timebase.StaleEpoch):
        a < b
    with pytest.raises(timebase.StaleEpoch):
        a == b


def test_compare_non_timeref_raises():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    with pytest.raises(TypeError):
        a < 1
    with pytest.raises(TypeError):
        a > 1
    # == returns False (not raises) for a non-TimeRef, per spec
    assert (a == 1) is False
    assert (a == "x") is False


def test_add_int():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    b = a + 48000
    assert b.ticks == 48000
    assert b.epoch == 0
    assert b.clock == "media"
    assert isinstance(b.ticks, int)


def test_add_timeref_raises():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    b = timebase.TimeRef("media", 0, 1, Fraction(1, 48000))
    with pytest.raises(TypeError):
        a + b


def test_time_ref_json_roundtrip():
    a = timebase.TimeRef("media", 3, 90000, Fraction(1, 90000))
    j = a.to_json()
    assert j == {"clock": "media", "epoch": 3, "ticks": 90000, "timebase": "1/90000"}
    b = timebase.TimeRef.from_json(j)
    assert b == a
    assert isinstance(b.timebase, Fraction)


def test_time_ref_json_roundtrip_str_timebase():
    j = {"clock": "media", "epoch": 0, "ticks": 3003, "timebase": "1001/30000"}
    tr = timebase.TimeRef.from_json(j)
    assert tr.timebase == Fraction(1001, 30000)
    assert tr.seconds == Fraction(3003 * 1001, 30000)


def test_timespan():
    a = timebase.TimeRef("media", 0, 0, Fraction(1, 48000))
    span = timebase.TimeSpan(a, 96000)  # 2s
    assert span.end.ticks == 96000
    assert span.contains(timebase.TimeRef("media", 0, 0, Fraction(1, 48000)))
    assert span.contains(timebase.TimeRef("media", 0, 95999, Fraction(1, 48000)))
    assert not span.contains(timebase.TimeRef("media", 0, 96000, Fraction(1, 48000)))  # end-exclusive


def test_clock_lifecycle():
    c = timebase.Clock("media", "media")
    assert c.epoch == 0
    assert c.history == []
    new = c.bump_epoch("seek")
    assert new == 1
    assert c.epoch == 1
    assert c.history == [(1, "seek")]
    st = c.stamp(48000, Fraction(1, 48000))
    assert st.epoch == 1
    assert st.clock == "media"
    assert st.ticks == 48000
    assert c.is_current(st)
    assert not c.is_current(timebase.TimeRef("media", 0, 48000, Fraction(1, 48000)))
    assert not c.is_current(timebase.TimeRef("audio", 1, 48000, Fraction(1, 48000)))


def test_clock_domain_validated():
    timebase.Clock("x", "media")
    with pytest.raises(ValueError):
        timebase.Clock("x", "bogus")


def test_clockmap_exact():
    cm = timebase.ClockMap("media", "audio", Fraction(2), Fraction(10), 0, "t0")
    ref = timebase.TimeRef("media", 0, 48000, Fraction(1, 48000))  # 1s
    assert cm.map_seconds(ref) == Fraction(2) * 1 + Fraction(10)
    assert cm.map_seconds(ref) == Fraction(12)
    # wrong source clock raises
    bad = timebase.TimeRef("timeline", 0, 48000, Fraction(1, 48000))
    with pytest.raises(timebase.ClockMismatch):
        cm.map_seconds(bad)


def test_master_by_mode():
    assert timebase.MASTER_BY_MODE["live_audio"] == "audio"
    assert timebase.MASTER_BY_MODE["live_silent"] == "presentation"
    assert timebase.MASTER_BY_MODE["offline"] == "virtual"
    assert timebase.MASTER_BY_MODE["edit"] == "timeline"


# ---------------------------------------------------------------- mediatypes

def test_port_types_present():
    for t in ("stream.video", "stream.audio", "media.video_frame", "media.audio_block",
              "media.encoded_packet", "media.subtitle_cue", "control.event",
              "control.curve", "analysis.features", "asset.reference",
              "timeline.sequence"):
        assert t in mediatypes.PORT_TYPES


def test_media_port_types_subset():
    assert set(mediatypes.MEDIA_PORT_TYPES) <= set(mediatypes.PORT_TYPES)
    for t in ("stream.video", "stream.audio", "media.video_frame"):
        assert t in mediatypes.MEDIA_PORT_TYPES
    assert "control.event" not in mediatypes.MEDIA_PORT_TYPES
    assert "analysis.features" not in mediatypes.MEDIA_PORT_TYPES


def test_memory_domains():
    for d in ("cpu", "d3d11", "d3d12", "vulkan", "opengl", "webgl", "webgpu", "browser", "encoded"):
        assert d in mediatypes.MEMORY_DOMAINS


def test_check_caps_any_accepts_all():
    out_caps = {"memory": "webgl", "primaries": "bt709"}
    in_caps = {"memory": "any"}
    assert mediatypes.check_caps(out_caps, in_caps) == []


def test_check_caps_match():
    out_caps = {"memory": "webgl", "primaries": "bt709"}
    in_caps = {"memory": "webgl", "primaries": "bt709"}
    assert mediatypes.check_caps(out_caps, in_caps) == []


def test_check_caps_mismatch_gives_reason():
    out_caps = {"memory": "webgl"}
    in_caps = {"memory": "cpu"}
    reasons = mediatypes.check_caps(out_caps, in_caps)
    assert reasons  # non-empty
    assert any("memory" in r.lower() for r in reasons)


def test_check_caps_output_missing_key_is_unknown():
    out_caps = {}
    in_caps = {"memory": "cpu"}
    reasons = mediatypes.check_caps(out_caps, in_caps)
    assert reasons
    assert any("unknown" in r.lower() for r in reasons)


def test_check_caps_only_checks_input_keys():
    # input requires only memory; output having extra keys is fine
    out_caps = {"memory": "cpu", "primaries": "bt709", "transfer": "bt709"}
    in_caps = {"memory": "cpu"}
    assert mediatypes.check_caps(out_caps, in_caps) == []


# ---------------------------------------------------------------- registry

def _write_manifest(tmp_path, mid, **extra):
    d = {
        "id": mid,
        "version": "1",
        "protocol": "arsenal.module/v0",
        "engine": "arsenal",
        "inputs": [],
        "outputs": [],
        "params": [],
        "isolation": "same-process",
        "licence": "MIT",
        "latency_ms": {"base": 1},
        "degradation": {"on_failure": "hold"},
        "receipts": [],
    }
    d.update(extra)
    p = tmp_path / f"{mid}.json"
    p.write_text(json.dumps(d))
    return p


def test_registry_load_and_list(tmp_path):
    _write_manifest(tmp_path, "a.mod")
    _write_manifest(tmp_path, "b.mod")
    reg = registry.load_registry(dirs=[str(tmp_path)])
    assert reg.ids() == ["a.mod", "b.mod"]
    assert reg.get("a.mod")["id"] == "a.mod"


def test_registry_missing_raises(tmp_path):
    _write_manifest(tmp_path, "a.mod")
    reg = registry.load_registry(dirs=[str(tmp_path)])
    with pytest.raises(KeyError):
        reg.get("nope.mod")


# ---------------------------------------------------------------- graph

def _build_registry(tmp_path):
    _write_manifest(tmp_path, "file.clip", engine="arsenal",
                    outputs=[{"port": "media", "type": "asset.reference"}])
    _write_manifest(tmp_path, "browser.decode", engine="browser",
                    inputs=[{"port": "media", "type": "asset.reference"}],
                    outputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "browser"}}])
    _write_manifest(tmp_path, "vfx.first-light-effect", engine="browser",
                    inputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "browser"}}],
                    outputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "webgl"}}],
                    params=[{"name": "pulse", "unit": "ratio", "range": [0, 1]},
                            {"name": "hue", "unit": "deg", "range": [0, 360]}])
    _write_manifest(tmp_path, "webmidi.input", engine="browser",
                    outputs=[{"port": "cc", "type": "control.event"}])
    _write_manifest(tmp_path, "browser.present", engine="browser",
                    inputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "webgl"}}])
    return registry.load_registry(dirs=[str(tmp_path)])


def _graph_obj(**over):
    g = {
        "api": "arsenal.graph/v0",
        "name": "first-light",
        "mode": "live_audio",
        "assets": {"clip": {"uri": "E:/v.mp4"}},
        "nodes": {
            "src": {"use": "file.clip"},
            "dec": {"use": "browser.decode"},
            "fx": {"use": "vfx.first-light-effect"},
            "midi": {"use": "webmidi.input"},
            "out": {"use": "browser.present"},
        },
        "edges": [
            ["src.media", "dec.media"],
            ["dec.video", "fx.video"],
            ["fx.video", "out.video"],
        ],
        "bindings": [
            {"from": "midi.cc", "to": "fx.hue", "range": [0, 360]},
        ],
    }
    g.update(over)
    return g


def test_load_graph_requires_api():
    with pytest.raises(graphmod.GraphError):
        graphmod.load_graph({"name": "x"})


def test_load_graph_ok():
    g = graphmod.load_graph(_graph_obj())
    assert g.api == "arsenal.graph/v0"


def test_validate_clean(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj())
    assert g.validate(reg) == []


def test_validate_unknown_module(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(nodes={
        "src": {"use": "file.clip"},
        "dec": {"use": "browser.decode"},
        "ghost": {"use": "no.such.module"},
        "out": {"use": "browser.present"},
    }, edges=[]))
    probs = g.validate(reg)
    assert probs
    assert any("no.such.module" in p for p in probs)


def test_validate_unknown_node_in_edge(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(edges=[["nonexistent.media", "dec.media"]]))
    probs = g.validate(reg)
    assert probs
    assert any("nonexistent" in p for p in probs)


def test_validate_unknown_port_in_edge(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(edges=[["src.nope", "dec.media"]]))
    probs = g.validate(reg)
    assert probs
    assert any("src" in p and "nope" in p for p in probs)


def test_validate_wrong_direction(tmp_path):
    reg = _build_registry(tmp_path)
    # dec.media is an input; wiring it as a source is the wrong direction
    g = graphmod.load_graph(_graph_obj(edges=[["dec.media", "src.media"]]))
    probs = g.validate(reg)
    assert probs
    assert any("direction" in p.lower() for p in probs)


def test_validate_type_mismatch(tmp_path):
    reg = _build_registry(tmp_path)
    # src.media is asset.reference, fx.video expects stream.video -> type mismatch
    g = graphmod.load_graph(_graph_obj(edges=[["src.media", "fx.video"]]))
    probs = g.validate(reg)
    assert probs
    assert any("type" in p.lower() for p in probs)


def test_validate_caps_mismatch(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(edges=[["dec.video", "out.video"]]))
    probs = g.validate(reg)
    assert probs


def test_validate_double_input(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(edges=[
        ["src.media", "dec.media"],
        ["src.media", "dec.media"],
    ]))
    probs = g.validate(reg)
    assert probs
    assert any("more than once" in p.lower() or "connected" in p.lower() for p in probs)


def test_validate_binding_target_not_param(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(bindings=[
        {"from": "midi.cc", "to": "fx.not_a_param", "range": [0, 1]},
    ]))
    probs = g.validate(reg)
    assert probs
    assert any("not_a_param" in p or "param" in p.lower() for p in probs)


def test_validate_binding_source_wrong_type(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(bindings=[
        {"from": "src.media", "to": "fx.hue", "range": [0, 360]},
    ]))
    probs = g.validate(reg)
    assert probs
    assert any("hue" in p or "control" in p.lower() for p in probs)


def test_validate_binding_range_outside_param(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(bindings=[
        {"from": "midi.cc", "to": "fx.hue", "range": [0, 999]},
    ]))
    probs = g.validate(reg)
    assert probs
    assert any("range" in p.lower() for p in probs)


def test_validate_feature_suffix_allowed(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "ffmpeg.audio-features", engine="ffmpeg",
                    outputs=[{"port": "features", "type": "analysis.features"}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={
        **_graph_obj()["nodes"],
        "af": {"use": "ffmpeg.audio-features"},
    }, bindings=[
        {"from": "af.features.rms", "to": "fx.pulse", "range": [0, 1]},
    ]))
    probs = [p for p in g.validate(reg2)
             if "pulse" in p and ("control" in p or "analysis" in p or "features" in p)]
    assert probs == []


def test_require_valid_raises(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj(edges=[["src.nope", "dec.media"]]))
    with pytest.raises(graphmod.GraphError) as ei:
        g.require_valid(reg)
    assert ei.value.problems


# ---------------------------------------------------------------- parse_text

def test_parse_text_multi_statement():
    src = """
    mode live_audio
    node src = file.clip
    node dec = browser.decode
    src.media -> dec.media
    """
    d = graphmod.parse_text(src)
    assert d["api"] == "arsenal.graph/v0"
    assert d["mode"] == "live_audio"
    assert d["nodes"]["src"]["use"] == "file.clip"
    assert d["nodes"]["dec"]["use"] == "browser.decode"
    assert ["src.media", "dec.media"] in d["edges"]


def test_parse_text_comment_ignored():
    src = """
    # this is a comment
    mode offline
    """
    d = graphmod.parse_text(src)
    assert d["mode"] == "offline"


def test_parse_text_chain_syntax():
    src = """
    mode live_audio
    node src = file.clip
    node dec = browser.decode
    node fx = vfx.first-light-effect
    node out = browser.present
    src | dec | fx | out
    """
    d = graphmod.parse_text(src)
    assert ["src.media", "dec.media"] in d["edges"]
    assert ["dec.video", "fx.video"] in d["edges"]
    assert ["fx.video", "out.video"] in d["edges"]


def test_parse_text_chain_no_match_raises():
    src = """
    node a = file.clip
    node b = file.clip
    a | b
    """
    with pytest.raises(graphmod.GraphError):
        graphmod.parse_text(src)


def test_parse_text_map_line():
    src = """
    mode live_audio
    node midi = webmidi.input
    node fx = vfx.first-light-effect
    map midi.cc -> fx.hue {range: 0..360, smooth: 20ms, precedence: 1}
    """
    d = graphmod.parse_text(src)
    b = d["bindings"][0]
    assert b["from"] == "midi.cc"
    assert b["to"] == "fx.hue"
    assert b["range"] == [0, 360]
    # smooth is typed JSON, never the raw "20ms" string
    assert b["smooth"] == {"attack_ms": 20, "release_ms": 20}
    assert b["precedence"] == 1


def test_parse_text_map_smooth_attack_release():
    src = """
    mode live_audio
    node midi = webmidi.input
    node fx = vfx.first-light-effect
    map midi.cc -> fx.hue {range: 0..360, smooth: 12ms/180ms}
    """
    d = graphmod.parse_text(src)
    b = d["bindings"][0]
    assert b["smooth"] == {"attack_ms": 12, "release_ms": 180}


def test_parse_text_map_precedence_default_zero():
    src = """
    mode live_audio
    node midi = webmidi.input
    node fx = vfx.first-light-effect
    map midi.cc -> fx.hue {range: 0..360}
    """
    d = graphmod.parse_text(src)
    assert d["bindings"][0]["precedence"] == 0


def test_parse_text_map_feature_suffix():
    src = """
    mode live_audio
    node af = ffmpeg.audio-features
    node fx = vfx.first-light-effect
    map af.features.rms -> fx.pulse {range: 0..1}
    """
    d = graphmod.parse_text(src)
    assert d["bindings"][0]["from"] == "af.features.rms"
    assert d["bindings"][0]["to"] == "fx.pulse"


# ---------------------------------------------------------------- plan

def test_make_plan_keys(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj())
    p = planmod.make_plan(g, reg)
    for k in ("nodes", "edges", "bindings", "latency_ms", "licence_profile", "warnings"):
        assert k in p


def test_plan_copy_on_engine_crossing_media_edge(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "ffmpeg.transcode", engine="ffmpeg",
                    inputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "any"}}],
                    outputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "cpu"}}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={
        "src": {"use": "file.clip"},
        "dec": {"use": "browser.decode"},
        "tx": {"use": "ffmpeg.transcode"},
    }, bindings=[], edges=[
        ["src.media", "dec.media"],
        ["dec.video", "tx.video"],
    ]))
    p = planmod.make_plan(g, reg2)
    crossing = [e for e in p["edges"] if e["from"].startswith("dec.video") and e["to"].startswith("tx.video")]
    assert crossing
    assert crossing[0]["copy"] is True


def test_plan_same_engine_note(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj())
    p = planmod.make_plan(g, reg)
    e = [e for e in p["edges"] if e["from"].startswith("dec.video") and e["to"].startswith("fx.video")][0]
    assert e["copy"] is False
    assert "same engine" in e["note"]


def test_plan_licence_profile_core(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj())
    p = planmod.make_plan(g, reg)
    assert p["licence_profile"] == "arsenal-core"


def test_plan_licence_profile_gpl(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "gpl.decoder", engine="gstreamer", licence="GPL-2.0-or-later",
                    inputs=[{"port": "media", "type": "asset.reference"}],
                    outputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "browser"}}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={
        "src": {"use": "file.clip"},
        "dec": {"use": "gpl.decoder"},
        "fx": {"use": "vfx.first-light-effect"},
        "out": {"use": "browser.present"},
    }, bindings=[], edges=[
        ["src.media", "dec.media"],
        ["dec.video", "fx.video"],
        ["fx.video", "out.video"],
    ]))
    p = planmod.make_plan(g, reg2)
    assert p["licence_profile"] == "arsenal-gpl"


def test_plan_licence_profile_agpl_counts_as_gpl(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "agpl.mod", engine="arsenal", licence="AGPL-3.0-or-later",
                    inputs=[], outputs=[{"port": "o", "type": "asset.reference"}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={"m": {"use": "agpl.mod"}}, bindings=[], edges=[]))
    p = planmod.make_plan(g, reg2)
    assert p["licence_profile"] == "arsenal-gpl"


def test_plan_lgpl_stays_core(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "lgpl.mod", engine="arsenal", licence="LGPL-2.1-or-later",
                    inputs=[], outputs=[{"port": "o", "type": "asset.reference"}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={"m": {"use": "lgpl.mod"}}, bindings=[], edges=[]))
    p = planmod.make_plan(g, reg2)
    assert p["licence_profile"] == "arsenal-core"


def test_plan_noassertion_warning(tmp_path):
    reg = _build_registry(tmp_path)
    _write_manifest(tmp_path, "mystery.mod", engine="arsenal", licence="NOASSERTION",
                    inputs=[], outputs=[{"port": "o", "type": "asset.reference"}])
    reg2 = registry.load_registry(dirs=[str(tmp_path)])
    g = graphmod.load_graph(_graph_obj(nodes={"m": {"use": "mystery.mod"}}, bindings=[], edges=[]))
    p = planmod.make_plan(g, reg2)
    assert any("NOASSERTION" in w for w in p["warnings"])


def test_render_plan_returns_str(tmp_path):
    reg = _build_registry(tmp_path)
    g = graphmod.load_graph(_graph_obj())
    p = planmod.make_plan(g, reg)
    s = planmod.render_plan(p)
    assert isinstance(s, str)
    assert s.strip()


# ---------------------------------------------------------------- take

def _tr(clock="media", epoch=0, ticks=0, tb="1/90000"):
    return {"clock": clock, "epoch": epoch, "ticks": ticks, "timebase": tb}


def test_take_open_returns_id(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {"x": 1}, {"meta": "m"})
    assert len(tid) == len("YYYYmmdd-HHMMSS-") + 8
    assert tid[8] == "-"


def test_take_append_and_load(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    n = led.append(tid, [{"kind": "play", "t": _tr()}])
    assert n == 1
    got = led.load(tid)
    assert got["take"] is not None
    assert len(got["events"]) == 1


def test_take_list(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    lst = led.list()
    assert isinstance(lst, list)
    assert any(x["take_id"] == tid for x in lst)


def test_take_stale_epoch_refused(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    # first, an epoch event: t.epoch is the source of truth = latest(0) + 1
    led.append(tid, [{"kind": "epoch", "t": _tr(epoch=1)}])
    # then a normal event at epoch 0 -> stale
    with pytest.raises(takemod.StaleEpoch):
        led.append(tid, [{"kind": "play", "t": _tr(epoch=0)}])
    # nothing new written
    assert len(led.load(tid)["events"]) == 1


def test_take_non_incremental_epoch_refused(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    led.append(tid, [{"kind": "epoch", "t": _tr(epoch=1)}])
    # epoch event must have t.epoch == latest+1 == 2, not a jump to 5
    with pytest.raises(ValueError):
        led.append(tid, [{"kind": "epoch", "t": _tr(epoch=5)}])


def test_take_newer_epoch_without_announcement_refused(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    # a normal event at epoch 2 arrives with NO epoch event having announced it
    with pytest.raises(ValueError):
        led.append(tid, [{"kind": "play", "t": _tr(epoch=2)}])
    assert len(led.load(tid)["events"]) == 0


def test_take_epoch_field_must_agree(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    # top-level epoch field, when present, must agree with t.epoch
    with pytest.raises(ValueError):
        led.append(tid, [{"kind": "epoch", "t": _tr(epoch=1), "epoch": 2}])


def test_take_write_to_closed_refused(tmp_path):
    led = takemod.TakeLedger(str(tmp_path))
    tid = led.open({"api": "arsenal.graph/v0", "name": "g"}, {}, {})
    led.close(tid, {"ok": True})
    with pytest.raises(ValueError):
        led.append(tid, [{"kind": "play", "t": _tr()}])
