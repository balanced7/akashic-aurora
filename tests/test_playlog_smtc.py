"""The play tracker (playlog.py: outside this repo, in the private akashic-local repo, started at logon by the task
Aurora-PlayLog) reads Spotify's now-playing every 2 s. Until 2026-10-29 each tick asked Windows for a new SMTC session
manager and enumerated every session: NPSMSvc at 322-404 % of one core, 0 % with the tracker suspended.

These pin its one-manager read and its outputs as they were (the database rows and the heartbeat), against a fake
winrt (tests/fake_winrt_smtc.py) and a stub for the VJ engine's state (never the live engine). PLAYLOG_PY names another
copy to test (its .bak shows the before); they skip when the tracker is not on this machine.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

from core import local
from fake_winrt_smtc import PAUSED, PLAYING, FakeSmtc, until

# The tracker lives in this machine's PRIVATE repo (akashic-local/playlog), found the way core/local.py finds the
# profile -- never a path written here. PLAYLOG_PY overrides; no private repo -> these skip and say so.
_PRIVATE = local.profile_dir()
PLAYLOG_PY = Path(os.environ.get("PLAYLOG_PY") or (_PRIVATE.parent / "playlog" / "playlog.py" if _PRIVATE
                                                   else "no-akashic-local/playlog.py"))
ENGINE = {"bpm": 128.0, "conf": 0.9, "db_bpm": 127.0, "chord": "Am", "key": "A minor", "level_db": -12.0}
T0 = 1_761_750_000.0          # 2025-10-29, local time on this machine


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def PL(monkeypatch, tmp_path, clock):
    if not PLAYLOG_PY.exists():
        pytest.skip(f"no play tracker at {PLAYLOG_PY}")
    monkeypatch.syspath_prepend(str(PLAYLOG_PY.parent))          # its nowplaying.py, as `pythonw playlog.py` sees it
    sys.modules.pop("nowplaying", None)
    loader = importlib.machinery.SourceFileLoader("playlog_under_test", str(PLAYLOG_PY))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    monkeypatch.setattr(mod, "DB_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "DB", str(tmp_path / "plays.sqlite"))
    monkeypatch.setattr(mod, "HEARTBEAT", str(tmp_path / "heartbeat.json"))
    monkeypatch.setattr(mod, "LOCK", str(tmp_path / "service.lock"))
    monkeypatch.setattr(mod, "LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setattr(mod, "engine_state", lambda: dict(ENGINE))    # never the live engine on :8794
    monkeypatch.setattr(mod, "time", types.SimpleNamespace(time=clock, sleep=lambda s: None))
    yield mod
    np_mod = sys.modules.pop("nowplaying", None)
    if np_mod is not None and hasattr(np_mod, "shutdown"):
        np_mod.shutdown()


@pytest.fixture
def fake(monkeypatch):
    return FakeSmtc().install(monkeypatch)


def iso(t):
    return datetime.fromtimestamp(t).isoformat(timespec="seconds")


def test_ticks_ask_windows_for_one_session_manager_and_never_enumerate_per_tick(PL, fake, clock):
    fake.add_session("Chrome", "A video", "A channel", PLAYING, current=True)
    fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    L = PL.Logger(PL.connect())
    for _ in range(10):
        L.tick()
        clock.t += 2.0
    assert fake.managers == 1                        # was 10: a new manager every tick
    assert fake.enumerations <= 1                    # was 10: every session enumerated every tick
    assert fake.property_reads == 1


def test_the_rows_and_the_heartbeat_are_what_they_were(PL, fake, clock, tmp_path):
    fake.add_session("Chrome", "A video", "A channel", PLAYING, current=True)    # a browser video is not a song
    sp = fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    db = PL.connect()
    L = PL.Logger(db)

    def tick(expect):
        assert until(lambda: PL.now_playing() == expect), (PL.now_playing(), expect)
        L.tick()
        clock.t += 2.0

    a = {"artist": "Artist A", "title": "Song A", "app": "Spotify.exe", "playing": True}
    b = {"artist": "Artist B", "title": "Song B", "app": "Spotify.exe", "playing": True}
    for _ in range(3):
        tick(a)                                      # T0, +2, +4: play 1 opens
    fake.change(sp, status=PAUSED)
    for _ in range(2):
        tick(dict(a, playing=False))                 # +6, +8: paused samples
    fake.change(sp, title="Song B", artist="Artist B", status=PLAYING)
    for _ in range(2):
        tick(b)                                      # +10: play 1 closes, play 2 opens; +12

    ms = lambda dt: (T0 + dt) * 1000
    assert db.execute("SELECT key, artist, title, first_played, last_played, plays, seconds, db_bpm, best_bpm, "
                      "music_key FROM tracks ORDER BY id").fetchall() == [
        ("artist a — song a", "Artist A", "Song A", iso(T0), iso(T0 + 4), 1, 6.0, 127.0, 128.0, "A minor"),
        ("artist b — song b", "Artist B", "Song B", iso(T0 + 10), iso(T0 + 10), 0, 0.0, None, None, None)]
    assert db.execute("SELECT track_id, started, ended, started_ms, ended_ms, seconds, bpm_median, bpm_min, bpm_max, "
                      "conf_median, db_bpm, music_key, level_db_mean, samples, engine_samples, app "
                      "FROM plays ORDER BY id").fetchall() == [
        (1, iso(T0), iso(T0 + 4), ms(0), ms(4), 6.0, 128.0, 128.0, 128.0, 0.9, 127.0, "A minor", -12.0, 3, 3,
         "Spotify.exe"),
        (2, iso(T0 + 10), None, ms(10), None, None, None, None, None, None, 127.0, None, None, 0, 0, "Spotify.exe")]
    played = (128.0, 0.9, -12.0, "Am", "A minor")
    quiet = (None, None, None, None, None)
    assert db.execute("SELECT play_id, t_ms, playing, bpm, conf, level_db, chord, music_key FROM samples "
                      "ORDER BY rowid").fetchall() == [
        (1, ms(0), 1, *played), (1, ms(2), 1, *played), (1, ms(4), 1, *played),
        (1, ms(6), 0, *quiet), (1, ms(8), 0, *quiet),
        (2, ms(10), 1, *played), (2, ms(12), 1, *played)]
    hb = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert list(hb) == ["at", "pid", "now", "play_id"]
    assert hb["now"] == b and list(hb["now"]) == ["artist", "title", "app", "playing"] and hb["play_id"] == 2


def test_no_spotify_session_is_none_and_the_heartbeat_says_so(PL, fake, tmp_path):
    fake.add_session("Chrome", "A video", "A channel", PLAYING, current=True)
    L = PL.Logger(PL.connect())
    L.tick()
    assert PL.now_playing() is None
    assert json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))["now"] is None


def test_without_winrt_the_tracker_reads_none_and_keeps_ticking(PL, monkeypatch, tmp_path):
    FakeSmtc.remove_winrt(monkeypatch)
    L = PL.Logger(PL.connect())
    L.tick()
    L.tick()
    assert PL.now_playing() is None
    assert json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))["now"] is None


def test_without_its_nowplaying_copy_the_tracker_reads_none(PL, fake, monkeypatch):
    fake.add_session("Spotify.exe", "Song A", "Artist A", PLAYING)
    monkeypatch.setitem(sys.modules, "nowplaying", None)     # the file next to playlog.py gone
    assert PL.now_playing() is None
