"""Vandor's development tests for the arsenal kernel. Heimdall's blind pins are kept separately."""
import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.graph import GraphError, load_graph, parse_text  # noqa: E402
from arsenal.mediatypes import check_caps  # noqa: E402
from arsenal.plan import make_plan, render_plan  # noqa: E402
from arsenal.registry import DEFAULT_DIR, load_registry  # noqa: E402
from arsenal.take import TakeLedger  # noqa: E402
from arsenal.timebase import (Clock, ClockMap, ClockMismatch, StaleEpoch, TimeRef, TimeSpan,  # noqa: E402
                              format_tb, parse_tb, tb)

FIRST_LIGHT = ROOT / "arsenal" / "graphs" / "first-light.json"


def first_light() -> dict:
    return json.loads(FIRST_LIGHT.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------ time
def test_18000_frames_at_29_97_is_exact():
    ref = TimeRef("media", 0, 0, tb(1001, 30000)) + 18000
    assert ref.seconds == Fraction(3003, 5)


def test_ten_minutes_is_not_a_whole_number_of_29_97_frames():
    ten_minutes = TimeRef("media", 0, 600 * 90000, tb(1, 90000))
    with pytest.raises(ValueError):
        ten_minutes.rescale(tb(1001, 30000))
    assert ten_minutes.rescale(tb(1001, 30000), exact=False).ticks == 17982


def test_a_rate_passed_as_a_timebase_is_refused():
    with pytest.raises(ValueError, match=r"tb\(1, 48000\)"):
        TimeRef("media", 0, 48000, 48000)
    with pytest.raises(ValueError, match=r"tb\(1001, 30000\)"):
        tb(30000, 1001)
    with pytest.raises(ValueError):
        tb(1, 0)
    assert TimeRef("media", 0, 5, 1).seconds == 5


def test_bare_numbers_are_refused():
    with pytest.raises(TypeError):
        TimeRef("media", 0, 1.0, tb(1, 48000))
    with pytest.raises(TypeError):
        TimeRef("media", 0, True, tb(1, 48000))
    with pytest.raises(TypeError):
        TimeRef("media", 0, 1, 0.5)
    with pytest.raises(TypeError):
        TimeRef("media", 0, 1, tb(1, 48000)) < 1


def test_epochs_and_clocks_do_not_mix():
    clock = Clock("media", "media")
    before = clock.stamp(100, tb(1, 1000))
    clock.bump_epoch("seek")
    after = clock.stamp(50, tb(1, 1000))
    assert not clock.is_current(before) and clock.is_current(after)
    assert clock.history == [(1, "seek")]
    with pytest.raises(StaleEpoch):
        before < after
    with pytest.raises(ClockMismatch):
        TimeRef("audio", 1, 5, tb(1, 48000)) < after


def test_rescale_and_cross_timebase_equality():
    assert TimeRef("media", 0, 48000, tb(1, 48000)).rescale(tb(1, 1000)).ticks == 1000
    odd = TimeRef("media", 0, 1, tb(1, 48000))
    with pytest.raises(ValueError):
        odd.rescale(tb(1, 1000))
    assert odd.rescale(tb(1, 1000), exact=False).ticks == 0
    # exact halves tell half-to-even apart from half-up
    assert TimeRef("media", 0, 1, tb(1, 96000)).rescale(tb(1, 48000), exact=False).ticks == 0
    assert TimeRef("media", 0, 3, tb(1, 96000)).rescale(tb(1, 48000), exact=False).ticks == 2
    assert TimeRef("media", 0, 1001, tb(1, 30000)) == TimeRef("media", 0, 48048, tb(1, 1440000))


def test_clock_map_span_and_json():
    m = ClockMap("media", "audio", Fraction(1), Fraction(1, 10), 250_000, "2026-09-13T15:00:00Z")
    assert m.map_seconds(TimeRef("media", 0, 30, tb(1, 30))) == Fraction(11, 10)
    with pytest.raises(ClockMismatch):
        m.map_seconds(TimeRef("audio", 0, 1, tb(1, 48000)))
    span = TimeSpan(TimeRef("media", 0, 10, tb(1, 10)), 10)
    assert span.contains(TimeRef("media", 0, 10, tb(1, 10))) and not span.contains(span.end)
    assert format_tb(parse_tb("1001/30000")) == "1001/30000"
    ref = TimeRef("media", 2, 12345, tb(1001, 30000))
    assert TimeRef.from_json(ref.to_json()) == ref
    with pytest.raises(TypeError):
        TimeRef.from_json({"clock": "media", "epoch": 0, "ticks": 1.5, "timebase": "1/1000"})


# ------------------------------------------------------------ caps, registry
def test_check_caps_reasons():
    assert check_caps({"memory": "browser"}, {"memory": "browser"}) == []
    assert check_caps({"memory": "cpu"}, {"memory": "any"}) == []
    assert any("memory" in r for r in check_caps({"memory": "cpu"}, {"memory": "d3d12"}))
    assert any("unknown" in r for r in check_caps({}, {"primaries": "bt709"}))


def test_registry_loads_the_builtins():
    registry = load_registry()
    assert "vfx.first-light-effect" in registry.ids()
    with pytest.raises(KeyError):
        registry.get("no.such.module")


# ----------------------------------------------------------------------- graph
def test_first_light_graph_is_valid():
    assert load_graph(first_light()).validate(load_registry()) == []


@pytest.mark.parametrize("mutate, needle", [
    (lambda g: g["nodes"].__setitem__("x", {"use": "no.such"}), "unknown module"),
    (lambda g: g["edges"].append(["decode.nope", "fx.video"]), "no port"),
    (lambda g: g["edges"].append(["screen.video", "fx.video"]), "wrong direction"),
    (lambda g: g["edges"].append(["clip.media", "fx.video"]), "type mismatch"),
    (lambda g: g["edges"].append(["decode.video", "screen.video"]), "caps memory"),
    (lambda g: g["edges"].append(["decode.video", "fx.video"]), "more than once"),
    (lambda g: g["edges"].append(["fx.video", "fx.video"]), "cycle"),
    (lambda g: g["bindings"].append({"from": "midi.cc", "to": "fx.nope"}), "not a declared param"),
    (lambda g: g["bindings"].append({"from": "decode.video", "to": "fx.hue"}), "not a control or analysis producer"),
    (lambda g: g["bindings"].append({"from": "midi.cc", "to": "fx.hue", "range": [0, 720]}), "outside"),
    (lambda g: g["bindings"].append({"from": "midi.cc", "to": "fx.hue", "smooth": "20ms"}), "whole milliseconds"),
    (lambda g: g["bindings"].append({"from": "midi.cc", "to": "fx.hue", "precedence": True}), "precedence must"),
    (lambda g: g["bindings"].append({"from": "midi.cc", "to": "fx.hue", "learn": "yes"}), "learn must"),
])
def test_graph_problems_are_named(mutate, needle):
    graph = first_light()
    mutate(graph)
    problems = load_graph(graph).validate(load_registry())
    assert any(needle in p for p in problems), problems


def test_text_form_chains_and_maps():
    source = """
    mode live_audio
    node clip = file.clip
    node dec = browser.decode
    node fx = vfx.first-light-effect
    node scr = browser.present
    node knobs = webmidi.input
    clip | dec | fx | scr     # a chain
    map knobs.cc -> fx.hue {range: 0..360, smooth: 20ms, precedence: 1}
    """
    graph = parse_text(source)
    assert graph["edges"] == [["clip.media", "dec.media"], ["dec.video", "fx.video"], ["fx.video", "scr.video"]]
    assert graph["bindings"] == [{"from": "knobs.cc", "to": "fx.hue", "range": [0, 360],
                                  "smooth": {"attack_ms": 20, "release_ms": 20}, "precedence": 1}]
    assert load_graph(graph).validate(load_registry()) == []


def test_text_form_errors_are_graph_errors():
    with pytest.raises(GraphError):
        parse_text("node a = file.clip\na | b")
    with pytest.raises(GraphError):
        parse_text("this is not a statement")


def test_map_options_are_typed():
    head = "node knobs = webmidi.input\nnode fx = vfx.first-light-effect\n"
    binding = parse_text(head + "map knobs.cc -> fx.hue {smooth: 12ms/180ms, learn: true}")["bindings"][0]
    assert binding["smooth"] == {"attack_ms": 12, "release_ms": 180} and binding["learn"] is True
    for bad in ("smooth: fast", "smooth: 12.5ms", "precedence: high", "learn: yes"):
        with pytest.raises(GraphError):
            parse_text(head + f"map knobs.cc -> fx.hue {{{bad}}}")


# ------------------------------------------------------------------------ plan
def _manifest(module_id, engine, licence, inputs=(), outputs=()):
    return {"id": module_id, "version": "0.1.0", "protocol": "arsenal.module/v0", "engine": engine,
            "inputs": list(inputs), "outputs": list(outputs), "params": [], "isolation": "process",
            "licence": licence, "latency_ms": {"base": 5}, "degradation": {"on_failure": "hold"},
            "receipts": []}


def _registry_with(tmp_path, *manifests):
    for m in manifests:
        (tmp_path / f"{m['id']}.json").write_text(json.dumps(m), encoding="utf-8")
    return load_registry([DEFAULT_DIR, tmp_path])


NATIVE_DECODE = dict(inputs=[{"port": "media", "type": "asset.reference"}],
                     outputs=[{"port": "video", "type": "stream.video", "caps": {"memory": "browser"}}])


def test_first_light_plan_is_honest():
    plan = make_plan(load_graph(first_light()), load_registry())
    assert not any(e["copy"] for e in plan["edges"])
    assert plan["latency_ms"] == 19
    assert plan["licence_profile"] == "arsenal-core"
    assert plan["master_clock"] == "audio"
    assert any("not asserted" in w for w in plan["warnings"])
    assert any("unverified" in w for w in plan["warnings"])
    assert "reference handoff" in render_plan(plan)


def test_crossing_media_edge_is_a_loud_copy_and_gpl_is_flagged(tmp_path):
    registry = _registry_with(
        tmp_path,
        _manifest("test.native-decode", "gstreamer", "LGPL-2.1-or-later", **NATIVE_DECODE),
        _manifest("test.gpl-player", "mpv", "GPL-2.0-or-later", inputs=[{"port": "media", "type": "asset.reference"}]),
    )
    graph = first_light()
    graph["nodes"]["decode"] = {"use": "test.native-decode"}
    graph["nodes"]["player"] = {"use": "test.gpl-player"}
    graph["edges"].append(["clip.media", "player.media"])
    plan = make_plan(load_graph(graph), registry)
    assert [(e["from"], e["to"]) for e in plan["edges"] if e["copy"]] == [("decode.video", "fx.video")]
    assert any("copy on decode.video -> fx.video" in w for w in plan["warnings"])
    assert plan["licence_profile"] == "arsenal-gpl"


def test_lgpl_alone_stays_core(tmp_path):
    registry = _registry_with(tmp_path, _manifest("test.native-decode", "gstreamer", "LGPL-2.1-or-later",
                                                  **NATIVE_DECODE))
    graph = first_light()
    graph["nodes"]["decode"] = {"use": "test.native-decode"}
    assert make_plan(load_graph(graph), registry)["licence_profile"] == "arsenal-core"


# ----------------------------------------------------------------------- takes
def _t(epoch, ticks):
    return {"clock": "media", "epoch": epoch, "ticks": ticks, "timebase": "1/90000"}


def test_take_round_trip_and_epoch_rules(tmp_path):
    ledger = TakeLedger(tmp_path)
    take_id = ledger.open(first_light(), {"api": "arsenal.plan/v0"}, {"clip_id": "abc", "clip_name": "x.mp4"})
    assert ledger.append(take_id, [{"kind": "play", "t": _t(0, 0)},
                                   {"kind": "midi", "t": _t(0, 900), "cc": 74, "value": 64}]) == 2
    assert ledger.append(take_id, [{"kind": "epoch", "epoch": 1, "reason": "seek", "t": _t(1, 0)}]) == 1
    with pytest.raises(StaleEpoch):  # the whole batch is refused, including its valid first event
        ledger.append(take_id, [{"kind": "midi", "t": _t(1, 10), "cc": 74, "value": 1},
                                {"kind": "midi", "t": _t(0, 20), "cc": 74, "value": 2}])
    with pytest.raises(StaleEpoch):
        ledger.append(take_id, [{"kind": "epoch", "epoch": 3, "reason": "skip", "t": _t(3, 0)}])
    with pytest.raises(ValueError):
        ledger.append(take_id, [{"kind": "midi", "t": _t(2, 0), "cc": 74, "value": 3}])
    assert [e["kind"] for e in ledger.load(take_id)["events"]] == ["play", "midi", "epoch"]
    ledger.close(take_id, {"latency_ms_p95": 12})
    with pytest.raises(ValueError):
        ledger.append(take_id, [{"kind": "pause", "t": _t(1, 5)}])
    listed = ledger.list()
    assert listed[0]["take_id"] == take_id and listed[0]["closed"] is True
