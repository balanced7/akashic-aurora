"""The clickable player reads a synthetic take and cannot send notes to the live piano."""
import io
import json
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

import pytest

from arsenal import pianocue, replay
from arsenal.performance import PerformanceStore
from arsenal.replay_harmony import harmony, theory_module


@pytest.fixture
def take(tmp_path):
    store = PerformanceStore(tmp_path / "sessions")
    session = store.open()
    store.append(session, [
        {"kind": "on", "t_ms": 0, "note": 48, "vel": 55},
        {"kind": "pedal", "t_ms": 100, "down": True, "value": 100},
        {"kind": "off", "t_ms": 200, "note": 48},
        {"kind": "on", "t_ms": 1500, "note": 64, "vel": 91},
        {"kind": "off", "t_ms": 1700, "note": 64},
        {"kind": "sound_end", "t_ms": 3000, "note": 48, "by": "pedal"},
        {"kind": "sound_end", "t_ms": 3000, "note": 64, "by": "pedal"},
        {"kind": "pedal", "t_ms": 3000, "down": False, "value": 0},
        {"kind": "on", "t_ms": 4000, "note": 67, "vel": 75},
        {"kind": "off", "t_ms": 5000, "note": 67},
        {"kind": "sound_end", "t_ms": 5000, "note": 67, "by": "release"},
    ])
    return store, session


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_excerpt_keeps_carried_pedal_and_velocity_and_scales_time(take):
    store, session = take
    before = snapshot(store.root)
    data = replay.excerpt(store, session, "0:01", seconds=3, speed=0.5)
    steps = data["cue"]["steps"]
    assert [(s["notes"], s["at_ms"], s["hold_ms"], s["velocity"]) for s in steps] == [
        ([48], 0, 4000, 55), ([64], 1000, 3000, 91)]
    assert snapshot(store.root) == before


def test_link_resolves_latest_and_escapes_label_without_sending(take, monkeypatch):
    store, session = take
    monkeypatch.setattr(pianocue, "send_cue", lambda *a: pytest.fail("link must not send a cue"))
    out = io.StringIO()
    assert pianocue.main(["replay-link", "latest", "0:01", "--seconds", "3", "--label", "A [bright] & B",
                         "--root", str(store.root), "--json"], out=out) == 0
    data = json.loads(out.getvalue())
    q = parse_qs(urlsplit(data["url"]).query)
    assert q["session"] == [session]
    assert q["label"] == ["A [bright] & B"]
    assert "\\[bright\\]" in data["markdown"]
    assert "latest" not in data["url"]


@pytest.mark.parametrize("seconds,speed", [(0, 1), (61, 1), (float("nan"), 1), (2, 0), (2, 3), (2, float("inf"))])
def test_rejects_unbounded_excerpt(take, seconds, speed):
    store, session = take
    with pytest.raises(ValueError):
        replay.excerpt(store, session, "0:00", seconds, speed)


def test_rejects_past_end_and_empty_window(take):
    store, session = take
    with pytest.raises(ValueError, match="beyond"):
        replay.excerpt(store, session, "0:04", 2)
    with pytest.raises(ValueError, match="nothing sounds"):
        replay.excerpt(store, session, "0:03", 0.5)


def test_read_only_http_player_and_errors(take):
    store, session = take
    before = snapshot(store.root)
    server = replay.Server(0, store.root, store.root.parent / "conversation")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for path in replay.ASSETS:
            with urllib.request.urlopen(base + path) as response:
                assert response.status == 200
                assert response.headers["Cache-Control"] == "no-store"
        url = base + f"/api/piano/replay?session={session}&at=0:01&seconds=3"
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
        assert data["cue"]["source"] == "replay"
        assert len(data["cue"]["steps"]) == 2
        assert data["chords"]
        with urllib.request.urlopen(base + "/web/piano/replay-theory.js") as response:
            module = response.read().decode("utf-8")
            assert "export default Theory" in module
            assert "import * as THREE" not in module
        for path, expected in [("/api/piano/replay?session=missing&at=0:01", 404),
                               ("/api/piano/replay?seconds=nan", 400),
                               ("/web/../pianocue.py", 404), ("/api/performance", 404)]:
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + path)
            assert error.value.code == expected
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(base + "/api/piano/cue", data=b"{}"))
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert snapshot(store.root) == before


def test_pedalled_arpeggio_is_one_chord_then_releases_before_next():
    events = [{"kind": "pedal", "t_ms": 0, "down": True}]
    for at, note in [(0, 48), (400, 64), (800, 67)]:
        events += [{"kind": "on", "t_ms": at, "note": note, "vel": 80},
                   {"kind": "off", "t_ms": at + 180, "note": note}]
    events.append({"kind": "pedal", "t_ms": 2600, "down": False})
    for note in (50, 65, 69):
        events += [{"kind": "on", "t_ms": 3000, "note": note, "vel": 70},
                   {"kind": "off", "t_ms": 5000, "note": note}]
    cue = pianocue.validate_cue(pianocue.build_replay_cue(events, 0, 5))
    windows = harmony(cue)
    assert len(windows) == 2
    assert windows[0]["notes"] == [48, 64, 67]
    assert windows[0]["start_ms"] == 0
    assert windows[0]["end_ms"] == 2600
    assert windows[1]["notes"] == [50, 65, 69]
    assert windows[1]["start_ms"] == 3000


def test_carried_chord_and_speed_keep_original_timeline():
    events = [{"kind": "pedal", "t_ms": 0, "down": True}]
    for at, note in [(0, 48), (400, 64), (800, 67)]:
        events += [{"kind": "on", "t_ms": at, "note": note, "vel": 75},
                   {"kind": "off", "t_ms": at + 100, "note": note}]
    events.append({"kind": "pedal", "t_ms": 5000, "down": False})
    regular = pianocue.build_replay_cue(events, 1000, 3, 1)
    slow = pianocue.build_replay_cue(events, 1000, 3, .5)
    assert harmony(regular) == harmony(slow, .5)
    assert harmony(regular)[0]["notes"] == [48, 64, 67]
    assert harmony(regular)[0]["end_ms"] == 3000


def test_separated_notes_do_not_become_a_pedalled_chord():
    events = []
    for at, note in [(0, 48), (2000, 64), (4000, 67)]:
        events += [{"kind": "on", "t_ms": at, "note": note, "vel": 80},
                   {"kind": "off", "t_ms": at + 800, "note": note}]
    windows = harmony(pianocue.build_replay_cue(events, 0, 5))
    assert [w["notes"] for w in windows] == [[48], [64], [67]]


def test_theory_module_rejects_missing_marker(tmp_path):
    source = tmp_path / "piano.js"
    source.write_text("const Theory = {};", encoding="utf-8")
    with pytest.raises(ValueError, match="markers"):
        theory_module(source)


def test_saved_answer_chords_use_frozen_cue_without_rereading_take(take, monkeypatch):
    store, session = take
    server = replay.Server(0, store.root, store.root.parent / "conversation")
    server.conversation.publish({"cards": [{"id": "listen", "title": "Listen", "group": "Test",
        "observation": "A synthetic take", "question": "What rings?", "prompt": "Play a chord",
        "clips": [{"session": session, "at": "0:00", "seconds": 3, "label": "Listen"}]}]})
    saved = server.conversation.save_response({"id": "a" * 32, "card_id": "listen", "session": session,
                                               "start_ms": 0, "end_ms": 2500})
    before = snapshot(store.root)
    monkeypatch.setattr(server.performance, "events", lambda *_: pytest.fail("saved replay must stay frozen"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/conversation/replay/{saved['id']}") as r:
            data = json.load(r)
        assert data["cue"] == saved["replay"]["cue"]
        assert data["chords"]
        assert all(w["end_ms"] <= 2500 for w in data["chords"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert snapshot(store.root) == before
