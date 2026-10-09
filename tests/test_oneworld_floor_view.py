"""Floor-view pins -- the floor's surface adapter (spec d622ac s4; Daniel 2026-10-09: "keep building out the one
world ui"). surface.floor_view() is what GET /api/floor serves on the cockpit, beside the world line.

What this file pins, and one correction to how it started:
- A cockpit polls every few seconds, so the view CACHES the evaluation (at most once per max_age_s). I first
  believed per-poll evaluation would flood the journal; the first run of these pins showed the journal is
  content-idempotent, so a steady identical fire was already one fact. The real gap was the opposite: a second
  EPISODE (fire, clear, fire) with the same detail was invisible. Given the previous statuses, the engine now
  journals transitions only, each stamped with `since`, so episodes are countable.
- A floor that cannot run is not a calm floor. An engine that raises reports ok=False, "cannot say what is silent",
  never an empty all-clear (zero is not no).

The legend stays the engine's: floor_view passes it through byte for byte with its sha256. The W4 pins on what the
SURFACE may do with it are Navi's (tests/test_oneworld_w4_found_taken.py).
"""
from __future__ import annotations

import hashlib

import pytest

floor = pytest.importorskip("core.oneworld.floor")
journal = pytest.importorskip("core.oneworld.journal")
surface = pytest.importorskip("core.oneworld.surface")


@pytest.fixture
def jp(tmp_path, monkeypatch):
    p = tmp_path / "world.jsonl"
    monkeypatch.setattr(journal, "JOURNAL_PATH", p)
    return p


def _lines(p):
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def _fired(d="boom"):
    return lambda: floor.Signal(floor.FIRED, d)


def _clear(d="ok"):
    return lambda: floor.Signal(floor.CLEAR, d)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


# ------------------------------------------------------------------ the engine journals transitions only

def test_a_repeated_fire_is_not_journaled_again_when_the_engine_knows_the_previous_status(jp):
    entries = [floor.make_entry("x", _fired(), state="shadow")]
    r1 = floor.evaluate(entries, previous={})
    r2 = floor.evaluate(entries, previous=r1["statuses"])
    assert len(_lines(jp)) == 1, "the second, identical would-fire must not be journaled again"
    assert r2["shadow_would_fire"][0]["key"] == "x", "the report still says it is firing"
    assert r2["journal_suppressed"] == 1


def test_a_fire_after_a_clear_is_a_new_episode_and_is_journaled(jp):
    # Two episodes a minute apart, as the floor really evaluates. (Microseconds apart, a coarse wall clock can
    # stamp both the same, and the content-idempotent journal then rightly calls them one fact.)
    state = {"s": floor.FIRED}
    entries = [floor.make_entry("x", lambda: floor.Signal(state["s"], "d"), state="shadow")]
    r = floor.evaluate(entries, previous={}, now=lambda: "2026-10-09T10:00:00+00:00")
    state["s"] = floor.CLEAR
    r = floor.evaluate(entries, previous=r["statuses"], now=lambda: "2026-10-09T10:01:00+00:00")
    state["s"] = floor.FIRED
    floor.evaluate(entries, previous=r["statuses"], now=lambda: "2026-10-09T10:02:00+00:00")
    rows = _lines(jp)
    assert len(rows) == 2, "fire, clear, fire is two episodes"
    assert '"since": "2026-10-09T10:00:00+00:00"' in rows[0] and '"since": "2026-10-09T10:02:00+00:00"' in rows[1]


def test_without_previous_the_w3_behaviour_is_unchanged(jp):
    entries = [floor.make_entry("x", _fired(), state="shadow")]
    floor.evaluate(entries)
    floor.evaluate(entries)
    rows = _lines(jp)
    assert len(rows) == 1, "W3 semantics: the journal is content-idempotent, a steady identical fire is one fact"
    assert '"since"' not in rows[0], "W3 callers keep the W3 payload shape"


def test_statuses_account_for_every_entry_including_off():
    entries = [floor.make_entry("a", _fired(), state="shadow"), floor.make_entry("b", _clear(), state="off")]
    r = floor.evaluate(entries, previous={})
    assert r["statuses"] == {"a": floor.FIRED, "b": "off"}


# ------------------------------------------------------------------ the view caches, passes the legend through

def test_floor_view_evaluates_once_within_its_max_age(jp):
    calls = []

    def ev(entries, previous=None):
        calls.append(1)
        return floor.evaluate(entries, previous=previous)

    clock, cache = Clock(), {}
    entries = [floor.make_entry("x", _fired(), state="shadow")]
    surface.floor_view(entries, evaluate=ev, clock=clock, cache=cache, max_age_s=60)
    clock.t += 5
    v = surface.floor_view(entries, evaluate=ev, clock=clock, cache=cache, max_age_s=60)
    assert len(calls) == 1, "a 5 s poll inside the 60 s window must reuse the evaluation"
    assert v["age_s"] == 5.0
    clock.t += 60
    surface.floor_view(entries, evaluate=ev, clock=clock, cache=cache, max_age_s=60)
    assert len(calls) == 2


def test_polling_a_firing_floor_journals_the_fire_once(jp):
    clock, cache = Clock(), {}
    entries = [floor.make_entry("x", _fired(), state="shadow")]
    for _ in range(5):
        surface.floor_view(entries, clock=clock, cache=cache, max_age_s=60)
        clock.t += 61
    assert len(_lines(jp)) == 1, "five evaluations of the same steady fire are one fact, not five"


def test_floor_view_passes_the_engine_legend_through_byte_for_byte(jp):
    entries = [floor.make_entry("x", _fired(), state="shadow"), floor.make_entry("y", _clear(), state="shadow")]
    v = surface.floor_view(entries, clock=Clock(), cache={})
    expected = floor.evaluate(entries)["legend"]
    assert v["ok"] is True and v["legend"] == expected
    assert v["legend_sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()


def test_floor_view_names_each_entry_with_its_state_and_status(jp):
    entries = [floor.make_entry("x", _fired("why"), state="shadow"), floor.make_entry("y", _clear(), state="off")]
    v = surface.floor_view(entries, clock=Clock(), cache={})
    rows = {r["key"]: r for r in v["entries"]}
    assert rows["x"] == {"key": "x", "state": "shadow", "status": "fired", "detail": "why"}
    assert rows["y"]["status"] == "off"


def test_the_default_floor_names_its_blind_spots_beside_its_one_real_sensor(jp, monkeypatch):
    # undeliverable_mail is wired (core/oneworld/sensors.py); the other three are still honestly unwired. The
    # sensor's sources are pinned here so this never reads a live Redis.
    sensors = pytest.importorskip("core.oneworld.sensors")
    monkeypatch.setattr(sensors, "_roster_rows", lambda: [{"agent": "sol", "state": "DEAD"}])
    monkeypatch.setattr(sensors, "_mailbox_query", lambda ns, agent: {"available": True, "entries": []})
    v = surface.floor_view(clock=Clock(), cache={})
    rows = {r["key"]: r["status"] for r in v["entries"]}
    assert rows.pop("undeliverable_mail") == "clear"
    assert set(rows.values()) == {"unavailable"}, "three unwired sensors are three blind spots, never calm"
    assert "1 clear" in v["legend"] and "3 unavailable" in v["legend"]


def test_a_crashed_engine_is_blind_never_all_clear(jp):
    def ev(entries, previous=None):
        raise RuntimeError("engine down")

    v = surface.floor_view(evaluate=ev, clock=Clock(), cache={})
    assert v["ok"] is False and v["entries"] == []
    assert "cannot say what is silent" in v["legend"] and "engine down" in v["legend"]


# ------------------------------------------------------------------ the richer agent fields (Heimdall's reshape)

def test_agents_view_passes_through_the_roster_churn_fields_when_present():
    v = surface.agents_view(presence_source=lambda: [
        {"agent": "claude", "state": "LIVE", "phase": "running", "beat_age_s": 1.0,
         "n_total": 7, "n_dead": 5, "split_brain": True, "churning": False}])
    a = v["agents"][0]
    assert (a["n_total"], a["n_dead"], a["split_brain"], a["churning"]) == (7, 5, True, False)


def test_agents_view_leaves_the_churn_fields_none_when_the_source_has_none():
    v = surface.agents_view(presence_source=lambda: [
        {"agent": "kimi", "state": "LIVE", "phase": "idle", "beat_age_s": 2.0}])
    a = v["agents"][0]
    assert a["split_brain"] is None and a["n_total"] is None, "unknown is None, never a guessed False or 0"
