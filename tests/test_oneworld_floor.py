"""W3 pins -- the floor: a shadow-first, toggleable manifest of loud absence (spec d622ac s4).

The floor is DATA, not code: a list of entries, each a row with a state (off/shadow/live) and a
budget. Shadow-first by construction -- an entry evaluates and RECORDS what it would have done
(a would-fire, journaled as a world-fact), but stays silent until promoted to live. You watch the
diary, then promote. Modes are named presets that set every entry's state at once.

The honesty rules that keep it from becoming wallpaper, made testable here:
- a sensor is THREE-state (fired / clear / unavailable) -- "quiet because I checked" and "quiet
  because I am blind" are different, and the floor must never let the second read as the first;
- found-vs-taken closes: every entry lands in exactly one bucket and the legend names the tally,
  written by the engine, so the floor cannot adjudicate its own silence;
- every entry ships a falsifier that MUST fire -- proof the entry CAN fire before it is trusted.
"""
from __future__ import annotations

import pytest

floor = pytest.importorskip("core.oneworld.floor")
journal = pytest.importorskip("core.oneworld.journal")


@pytest.fixture
def jp(tmp_path, monkeypatch):
    # The shadow diary journals would-fires; isolate it to a tmp file.
    p = tmp_path / "world.jsonl"
    monkeypatch.setattr(journal, "JOURNAL_PATH", p)
    return p


# A sensor is a callable () -> Signal (it re-reads state each evaluate), so these return callables.
def _fired(d="boom"):
    return lambda: floor.Signal(floor.FIRED, d)


def _clear(d="ok"):
    return lambda: floor.Signal(floor.CLEAR, d)


def _unavail(d="blind"):
    return lambda: floor.Signal(floor.UNAVAILABLE, d)


class _Spy:
    """A sensor that returns a fixed Signal and counts how many times it was called."""
    def __init__(self, sig):
        self.sig = sig
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.sig


def test_default_manifest_is_the_four_all_shadow():
    m = floor.default_manifest()
    assert {e.key for e in m} == {
        "undeliverable_mail", "noop_guard_success", "secret_egress", "floor_own_silence"}
    assert all(e.state == "shadow" for e in m), "shadow-first: nothing speaks until promoted"


def test_states_and_modes_exist():
    assert floor.STATES == ("off", "shadow", "live")
    assert {"quiet", "focus", "night", "firehose"} <= set(floor.MODES)


def test_make_entry_refuses_unknown_state():
    with pytest.raises(ValueError):
        floor.make_entry("t", sensor=_clear, state="SCREAMING")


def test_shadow_fire_is_journaled_not_surfaced(jp):
    e = floor.make_entry("t", sensor=_fired("mem over budget"), state="shadow")
    rep = floor.evaluate([e])
    assert not rep["live_firing"], "a shadow entry must never surface as a live alarm"
    assert any(x["key"] == "t" for x in rep["shadow_would_fire"])
    facts = journal.replay()["facts"]
    assert any(f["kind"] == "floor_would_fire" and f["payload"].get("entry") == "t"
               for f in facts), "the would-fire is the learning diary -- it must be journaled"


def test_live_fire_is_surfaced(jp):
    e = floor.make_entry("t", sensor=_fired(), state="live")
    rep = floor.evaluate([e])
    assert any(x["key"] == "t" for x in rep["live_firing"])


def test_unavailable_is_not_counted_as_clear(jp):
    e = floor.make_entry("t", sensor=_unavail("cannot read sensor"), state="shadow")
    rep = floor.evaluate([e])
    assert any(x["key"] == "t" for x in rep["unavailable"])
    assert not rep["clear"], "blind must never read as clear (zero is not no)"


def test_off_entry_is_not_evaluated(jp):
    spy = _Spy(floor.Signal(floor.CLEAR, "ok"))
    e = floor.make_entry("t", sensor=spy, state="off")
    rep = floor.evaluate([e])
    assert spy.calls == 0, "an off entry's sensor is never called"
    assert any(x["key"] == "t" for x in rep["off"])


def test_found_vs_taken_closes_and_legend_is_written(jp):
    es = [
        floor.make_entry("a", sensor=_fired(), state="live"),
        floor.make_entry("b", sensor=_clear(), state="shadow"),
        floor.make_entry("c", sensor=_unavail(), state="shadow"),
        floor.make_entry("d", sensor=_clear(), state="off"),
    ]
    rep = floor.evaluate(es)
    bucketed = (len(rep["live_firing"]) + len(rep["shadow_would_fire"]) + len(rep["clear"])
                + len(rep["unavailable"]) + len(rep["off"]))
    assert bucketed == rep["total"] == 4, "every entry lands in exactly one bucket"
    assert rep["checked"] == 3, "off is not checked"
    assert rep["legend"].strip()


def test_modes_set_states(jp):
    m = floor.default_manifest()
    assert all(e.state == "live" for e in floor.apply_mode(m, "firehose"))
    assert all(e.state != "live" for e in floor.apply_mode(m, "night")), "night never speaks"
    assert any(e.state == "off" for e in floor.apply_mode(m, "quiet"))


def test_apply_mode_refuses_unknown_mode(jp):
    with pytest.raises(ValueError):
        floor.apply_mode(floor.default_manifest(), "pandemonium")


def test_every_entry_ships_a_falsifier_that_fires():
    m = floor.default_manifest()
    result = floor.self_check(m)
    assert set(result) == {e.key for e in m}
    assert all(result.values()), "each entry's falsifier must actually fire -- proof it CAN"


def test_default_sensors_are_honest_about_being_blind(jp, monkeypatch):
    """A floor that cannot see does not report all-clear -- the anti-'false all-clear', demonstrated on the
    real default manifest. Amended 2026-10-09 when undeliverable_mail was wired (core/oneworld/sensors.py):
    with its roster unreadable it is blind too, so all four are unavailable and nothing is clear."""
    sensors = pytest.importorskip("core.oneworld.sensors")

    def blind():
        raise ConnectionError("roster down")

    monkeypatch.setattr(sensors, "_roster_rows", blind)
    rep = floor.evaluate(floor.default_manifest())
    assert not rep["clear"], "a floor that cannot see may not report anything clear"
    assert len(rep["unavailable"]) == 4


def test_the_one_wired_sensor_reports_what_it_read_and_the_rest_stay_blind(jp, monkeypatch):
    sensors = pytest.importorskip("core.oneworld.sensors")
    monkeypatch.setattr(sensors, "_roster_rows", lambda: [{"agent": "sol", "state": "DEAD"}])
    monkeypatch.setattr(sensors, "_mailbox_query", lambda ns, agent: {"available": True, "entries": []})
    rep = floor.evaluate(floor.default_manifest())
    assert [r["key"] for r in rep["clear"]] == ["undeliverable_mail"]
    assert len(rep["unavailable"]) == 3, "the three unwired sensors still say they cannot see"
