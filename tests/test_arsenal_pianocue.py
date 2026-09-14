"""Claude's hand on the piano page: the cue channel routes, the CLI verbs, the voicing bridge and replay.

The event-stream client here speaks raw HTTP over a socket, so every byte of the protocol is checked. Nothing here
reads Daniel's practice log: replay runs on a synthetic session in a temporary store.
"""
import http.client
import http.server
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import pianocue  # noqa: E402
from arsenal.performance import PerformanceStore  # noqa: E402
from arsenal.pianocue import CueError, CueHub, build_replay_cue, parse_clock, validate_cue  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="the voicing bridge needs node")


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture()
def server(tmp_path):
    app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    clock = FakeClock()
    app.cues = CueHub(heartbeat_s=0.3, clock=clock, id_base=0)  # ids 1, 2, 3 ... (a real server counts from boot ms)
    srv = Server(0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield SimpleNamespace(port=srv.server_address[1], app=app, clock=clock)
    app.cues.close()
    srv.shutdown()
    srv.server_close()


class SSE:
    """A raw event-stream client: connects, reads the headers and the opening block ("retry: 1000" and the "id:"
    cursor; the listener is registered by then), and hands back one event block at a time."""

    def __init__(self, port, last_event_id=None, timeout=5.0, path="/api/piano/cues"):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        request = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nAccept: text/event-stream\r\n"
        if last_event_id is not None:
            request += f"Last-Event-ID: {last_event_id}\r\n"
        self.sock.sendall((request + "\r\n").encode("ascii"))
        self.buf = b""
        head = self._until(b"\r\n\r\n").decode("latin-1").split("\r\n")
        self.status = int(head[0].split()[1])
        self.headers = {k.strip().lower(): v.strip() for k, v in (line.split(":", 1) for line in head[1:] if line)}
        opening = self.block().split("\n")
        assert opening[0] == "retry: 1000" and len(opening) == 2 and opening[1].startswith("id: "), opening
        self.cursor = int(opening[1][4:])

    def _until(self, sep):
        while sep not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError("the stream closed")
            self.buf += chunk
        part, self.buf = self.buf.split(sep, 1)
        return part

    def block(self):
        return self._until(b"\n\n").decode("utf-8")

    def cue(self):
        while True:
            text = self.block()
            if text.startswith(":"):
                continue
            fields = dict(line.split(": ", 1) for line in text.split("\n"))
            data = json.loads(fields["data"])
            assert fields["event"] == "cue" and int(fields["id"]) == data["id"]
            return data

    def close(self):
        self.sock.close()


def _request(port, method, path, body=None, headers=None, conn=None):
    own = conn is None
    conn = conn or http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    raw = body if isinstance(body, bytes) else (json.dumps(body).encode("utf-8") if body is not None else None)
    conn.request(method, path, body=raw, headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    resp = conn.getresponse()
    data = resp.read()
    if own:
        conn.close()
    return resp.status, json.loads(data or b"null")


def _post_cue(port, cue, conn=None):
    return _request(port, "POST", "/api/piano/cue", {"cue": cue}, conn=conn)


def _status(port):
    return _request(port, "GET", "/api/piano/cues/status")[1]


# ------------------------------------------------------------------------------------------------ routes
def test_two_listeners_get_the_same_cue_with_defaults(server):
    a, b = SSE(server.port), SSE(server.port)
    try:
        assert a.status == 200 and a.headers["content-type"].startswith("text/event-stream")
        assert _status(server.port) == {"listeners": 2, "last_id": 0}
        before = int(time.time() * 1000)
        status, reply = _post_cue(server.port, {"type": "play", "notes": [67, 60, 64, 60], "label": "C"})
        assert (status, reply) == (200, {"id": 1, "listeners": 2})
        want = {"type": "play", "notes": [60, 64, 67], "velocity": 80, "hold_ms": 2500, "arpeggio_ms": 0,
                "sound": True, "label": "C", "detail": None, "source": "claude"}
        for listener in (a, b):
            got = listener.cue()
            assert got["id"] == 1 and got["cue"] == want
            assert before - 1000 <= got["sent_at"] <= int(time.time() * 1000) + 1000
        assert _status(server.port) == {"listeners": 2, "last_id": 1}
    finally:
        a.close()
        b.close()


def test_frame_bytes_are_exactly_the_protocol(server):
    listener = SSE(server.port)
    try:
        _post_cue(server.port, {"type": "clear"})
        text = listener.block()
        lines = text.split("\n")
        assert lines[0] == "id: 1" and lines[1] == "event: cue" and lines[2].startswith("data: {") and len(lines) == 3
        assert json.loads(lines[2][6:])["cue"] == {"type": "clear", "label": None, "detail": None, "source": "claude"}
    finally:
        listener.close()


def test_last_event_id_replays_newer_cues_once_and_fresh_pages_get_none(server):
    for n in range(3):
        assert _post_cue(server.port, {"type": "hover", "notes": [60 + n]}) == (200, {"id": n + 1, "listeners": 0})
    back = SSE(server.port, last_event_id=1)
    fresh = SSE(server.port)
    try:
        assert [back.cue()["id"], back.cue()["id"]] == [2, 3]
        _post_cue(server.port, {"type": "hover", "notes": [70]})
        assert back.cue()["id"] == 4
        assert fresh.cue()["id"] == 4  # a page opened without Last-Event-ID starts with live cues only
    finally:
        back.close()
        fresh.close()


def test_ring_keeps_the_last_fifty_and_a_restart_id_replays_all_young(server):
    for n in range(60):
        _post_cue(server.port, {"type": "hover", "notes": [21 + n]})
    for last in (0, 10 ** 9):  # 10**9: an id from before a server restart
        listener = SSE(server.port, last_event_id=last)
        try:
            assert [listener.cue()["id"] for _ in range(50)] == list(range(11, 61))
        finally:
            listener.close()


def test_the_stream_opens_with_an_id_so_a_page_that_saw_no_cue_still_resumes(server):
    first = SSE(server.port)
    assert first.cursor == 0  # nothing issued yet: the hub's base
    first.close()  # the page drops before any cue reached it
    for n in range(2):
        _post_cue(server.port, {"type": "hover", "notes": [60 + n]})
    back = SSE(server.port, last_event_id=first.cursor)  # what the browser sends back on its own retry
    try:
        assert back.cursor == 0 and [back.cue()["id"], back.cue()["id"]] == [1, 2]
    finally:
        back.close()
    fresh = SSE(server.port)
    assert fresh.cursor == 2
    fresh.close()
    # a page that had to open a fresh EventSource asks with ?lastEventId= (the header wins when both are there)
    query = SSE(server.port, path="/api/piano/cues?lastEventId=1")
    both = SSE(server.port, last_event_id=2, path="/api/piano/cues?lastEventId=0")
    try:
        assert query.cursor == 1 and query.cue()["id"] == 2
        _post_cue(server.port, {"type": "clear"})
        assert query.cue()["id"] == 3 and both.cue()["id"] == 3
    finally:
        query.close()
        both.close()


def test_ids_stay_unique_across_a_restart_so_the_new_server_replays_to_an_old_page():
    clock = FakeClock()
    old = CueHub(clock=clock, id_base=1_000)
    seen = old.publish({"type": "clear"})["id"]  # 1001: the last id the page saw
    new = CueHub(clock=clock, id_base=2_000)
    new.publish({"type": "clear"})  # posted as soon as the restarted server answered, before the page is back
    ids = lambda frames: [int(f.split(b"\n")[0][4:]) for f in frames]  # noqa: E731
    assert ids(new.subscribe(seen)[2]) == [2001]
    assert ids(new.subscribe(2001)[2]) == [] and ids(new.subscribe(2000)[2]) == [2001]
    new.publish({"type": "clear"})
    assert ids(new.subscribe(seen)[2]) == [2001, 2002]  # still below the base: from the earlier server
    assert ids(CueHub(clock=clock, id_base=500).subscribe(seen)[2]) == []  # (a clock set back: nothing young yet)
    back = CueHub(clock=clock, id_base=500)
    back.publish({"type": "clear"})
    assert ids(back.subscribe(seen)[2]) == [501]  # an id above the last issued is foreign too
    assert new.open_stream(seen)[2].startswith(b"retry: 1000\nid: 2000\n\nid: 2001\n")
    assert new.open_stream(None)[2] == b"retry: 1000\nid: 2002\n\n"
    assert abs(CueHub().id_base - time.time() * 1000) < 60_000  # the default base is the boot time in epoch ms


def test_a_real_restart_with_default_ids_replays_the_cue_posted_before_the_page_returned(tmp_path):
    def boot():
        app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
        srv = Server(0, app)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return app, srv

    app1, srv1 = boot()
    page = SSE(srv1.server_address[1])
    _post_cue(srv1.server_address[1], {"type": "hover", "notes": [60]})
    seen = page.cue()["id"]
    page.close()
    app1.cues.close()
    srv1.shutdown()
    srv1.server_close()
    time.sleep(0.05)
    app2, srv2 = boot()
    try:
        port = srv2.server_address[1]
        posted = _post_cue(port, {"type": "hover", "notes": [62], "label": "posted before the page came back"})[1]
        assert posted["id"] > seen
        back = SSE(port, last_event_id=seen)
        try:
            got = back.cue()
            assert got["id"] == posted["id"] and got["cue"]["label"] == "posted before the page came back"
        finally:
            back.close()
    finally:
        app2.cues.close()
        srv2.shutdown()
        srv2.server_close()


def test_cues_older_than_ten_seconds_are_not_replayed(server):
    _post_cue(server.port, {"type": "play", "notes": [60]})
    server.clock.t += 10.5
    _post_cue(server.port, {"type": "play", "notes": [62]})
    listener = SSE(server.port, last_event_id=0)
    try:
        assert listener.cue()["id"] == 2
        _post_cue(server.port, {"type": "play", "notes": [64]})
        assert listener.cue()["id"] == 3
    finally:
        listener.close()


def test_heartbeat_comment(server):
    listener = SSE(server.port)
    try:
        assert listener.block() == ": hb"  # the fixture's hub beats every 0.3 s
    finally:
        listener.close()


def test_a_closed_page_is_unregistered(server):
    listener = SSE(server.port)
    assert _status(server.port)["listeners"] == 1
    listener.close()
    deadline = time.monotonic() + 3
    while _status(server.port)["listeners"] and time.monotonic() < deadline:
        time.sleep(0.05)
    assert _status(server.port)["listeners"] == 0
    assert _post_cue(server.port, {"type": "clear"})[1]["listeners"] == 0


def test_open_streams_do_not_block_other_requests(server):
    listeners = [SSE(server.port) for _ in range(6)]
    try:
        t0 = time.monotonic()
        for _ in range(5):
            assert _request(server.port, "GET", "/api/health")[0] == 200
        assert time.monotonic() - t0 < 2.0
        assert _post_cue(server.port, {"type": "clear"})[1]["listeners"] == 6
    finally:
        for listener in listeners:
            listener.close()


BAD = [
    (b"not json", "not JSON"),
    ({}, '{"cue"'),
    ({"cue": {"type": "strum", "notes": [60]}}, "type must be one of"),
    ({"cue": {"type": "play"}}, "notes must be a non-empty list"),
    ({"cue": {"type": "play", "notes": [20]}}, "21..108"),
    ({"cue": {"type": "play", "notes": [109]}}, "21..108"),
    ({"cue": {"type": "play", "notes": [True]}}, "21..108"),
    ({"cue": {"type": "play", "notes": [60], "velocity": 0}}, "velocity must be an integer 1..127"),
    ({"cue": {"type": "play", "notes": [60], "hold_ms": -1}}, "hold_ms"),
    ({"cue": {"type": "play", "notes": [60], "hold": 3}}, "unknown field 'hold'"),
    ({"cue": {"type": "play", "notes": [60], "label": 5}}, "label must be a string"),
    ({"cue": {"type": "hover", "notes": [60], "sound": True}}, "a hover never sounds"),
    ({"cue": {"type": "play", "notes": [60], "source": "someone"}}, "source must be one of"),
    ({"cue": {"type": "sequence"}}, "a sequence needs steps"),
    ({"cue": {"type": "sequence", "steps": [{"at_ms": 0, "type": "play", "notes": [60], "sound": False}]}},
     "steps[0].unknown field 'sound'"),
    ({"cue": {"type": "sequence", "steps": [{"at_ms": -5, "type": "play", "notes": [60]}]}}, "steps[0].at_ms"),
    ({"cue": {"type": "sequence", "steps": [{"at_ms": 0, "type": "clear", "notes": [60]}]}}, "play or hover"),
    ({"cue": {"type": "clear", "notes": [60]}}, "a clear cue has unknown field 'notes'"),
    ({"cue": [60, 64]}, "must be a JSON object"),
]


@pytest.mark.parametrize("body,message", BAD)
def test_malformed_cues_answer_400_and_keep_the_connection(server, body, message):
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    try:
        status, reply = _request(server.port, "POST", "/api/piano/cue", body, conn=conn)
        assert status == 400 and message in reply["error"], reply
        assert _request(server.port, "GET", "/api/piano/cues/status", conn=conn) == (200, {"listeners": 0, "last_id": 0})
    finally:
        conn.close()


def test_cross_site_pages_cannot_send_cues(server):
    status, reply = _request(server.port, "POST", "/api/piano/cue", {"cue": {"type": "clear"}},
                             headers={"Origin": "https://example.com"})
    assert status == 403 and "this machine" in reply["error"]
    status, _ = _request(server.port, "POST", "/api/piano/cue", {"cue": {"type": "clear"}},
                         headers={"Origin": f"http://127.0.0.1:{server.port}"})
    assert status == 200


def test_existing_routes_still_answer(server):
    assert _request(server.port, "GET", "/api/health")[1]["ok"] is True
    assert _request(server.port, "POST", "/api/nothing", {"x": 1})[0] == 404
    assert _request(server.port, "GET", "/api/performance")[0] == 200


# ------------------------------------------------------------------------------------------ validation
def test_sequence_steps_are_sorted_and_inherit_the_cue_defaults():
    cue = validate_cue({"type": "sequence", "velocity": 60, "hold_ms": 900, "source": "replay", "steps": [
        {"at_ms": 500, "type": "hover", "notes": [64]},
        {"at_ms": 0, "type": "play", "notes": [60, 48], "velocity": 100, "label": "C/C"}]})
    assert cue["steps"] == [
        {"at_ms": 0, "type": "play", "notes": [48, 60], "velocity": 100, "hold_ms": 900, "arpeggio_ms": 0,
         "label": "C/C", "detail": None},
        {"at_ms": 500, "type": "hover", "notes": [64], "velocity": 60, "hold_ms": 900, "arpeggio_ms": 0,
         "label": None, "detail": None}]
    assert cue["source"] == "replay" and cue["sound"] is True
    assert validate_cue({"type": "hover", "notes": [60]})["sound"] is False
    assert validate_cue({"type": "play", "notes": [60], "sound": False, "hold_ms": 0})["hold_ms"] == 0
    with pytest.raises(CueError):
        validate_cue({"type": "play", "notes": [60], "steps": []})


# ---------------------------------------------------------------------------------------------- replay
def _session_events(with_sound_end=True):
    events = [
        {"t_ms": 1000, "kind": "on", "note": 60, "vel": 70},
        {"t_ms": 1002, "kind": "chord", "chord": "C4", "notes": ["C4"], "key": None, "detect_kind": "note"},
        {"t_ms": 1100, "kind": "pedal", "down": True, "value": 90},
        {"t_ms": 1200, "kind": "off", "note": 60},
        {"t_ms": 1500, "kind": "on", "note": 64, "vel": 50},
        {"t_ms": 1600, "kind": "off", "note": 64},
        {"t_ms": 4000, "kind": "pedal", "down": False, "value": 0},
        {"t_ms": 5000, "kind": "on", "note": 63, "vel": 90},
        {"t_ms": 5002, "kind": "chord", "chord": "Cm", "notes": ["C4", "Eb4", "G4"], "key": "C minor",
         "detect_kind": "chord", "nns": "1m", "nns_key": "C minor"},
        {"t_ms": 5500, "kind": "off", "note": 63},
    ]
    if with_sound_end:
        events += [{"t_ms": 4000, "kind": "sound_end", "note": 60, "by": "pedal"},
                   {"t_ms": 4000, "kind": "sound_end", "note": 64, "by": "pedal"},
                   {"t_ms": 5500, "kind": "sound_end", "note": 63, "by": "release"}]
    return events


@pytest.mark.parametrize("with_sound_end", [True, False])
def test_replay_holds_pedalled_notes_until_their_sound_ended(with_sound_end):
    cue = build_replay_cue(_session_events(with_sound_end), start_ms=1400, seconds=4)
    assert cue["type"] == "sequence" and cue["source"] == "replay" and cue["label"] == "you, at 0:01"
    assert [(s["at_ms"], s["notes"], s["hold_ms"], s["velocity"]) for s in cue["steps"]] == [
        (0, [60], 2600, 70),       # struck before the window, still ringing under the pedal
        (100, [64], 2500, 50),     # key up at 1600, the pedal held it to 4000
        (3600, [63], 400, 90),     # clipped at the window's end (5400)
    ]
    assert cue["steps"][0]["detail"] == "already sounding at 0:01"
    assert (cue["steps"][2]["label"], cue["steps"][2]["detail"]) == ("Cm", "1m in C minor")
    validate_cue(cue)

    fast = build_replay_cue(_session_events(with_sound_end), start_ms=1400, seconds=4, speed=2.0, at_text="0:01.4")
    assert [(s["at_ms"], s["hold_ms"]) for s in fast["steps"]] == [(0, 1300), (50, 1250), (1800, 200)]
    assert fast["label"] == "you, at 0:01.4"
    with pytest.raises(ValueError):
        build_replay_cue(_session_events(with_sound_end), start_ms=6000, seconds=2)


def test_parse_clock():
    assert parse_clock("5:22") == 322000
    assert parse_clock("0:01.4") == 1400
    assert parse_clock("1:02:03") == 3723000
    assert parse_clock("90") == 90000
    with pytest.raises(ValueError):
        parse_clock("five")


# ---------------------------------------------------------------------------------------------- bridge
def _voice(items, **kw):
    return pianocue.voice(items, **kw)


@needs_node
def test_the_suffix_reader_agrees_with_every_template():
    import subprocess
    out = subprocess.run([NODE, str(pianocue.BRIDGE), "--check"], capture_output=True, text=True, timeout=60)
    reply = json.loads(out.stdout)
    assert reply["templates"] >= 30 and reply["problems"] == []
    assert reply["page_spelling"] == "piano.js spellForKey", reply  # labels follow the page's own function


DANIEL = ["Abmaj9#11", "Ebmaj9#11", "Bb7sus4/Eb", "Bb11/Ab", "Dbmaj9", "Abm", "Cbmaj7", "Gbmaj7/F", "Ebm(add9)/Bb",
          "Cm11/Bb", "Fm9/Ab"]


@needs_node
@pytest.mark.parametrize("style", ["close", "open", "spread", "drop2", "shell"])
def test_daniels_chords_voice_with_the_bass_lowest_and_read_back(style):
    results = _voice(DANIEL, key="Eb major", voicing=style)
    by_name = {r["input"]: r for r in results}
    names = "C Db D Eb E F Gb G Ab A Bb B".split()
    for r in results:
        assert not r.get("error"), r
        notes = r["notes"]
        assert notes == sorted(set(notes)) and 21 <= notes[0] and notes[-1] <= 108 and len(notes) >= 3
        if "/" in r["name"]:
            assert names[notes[0] % 12] == r["name"].split("/")[1].replace("Cb", "B"), (style, r)
        assert r["roundtrip"]["match"] in ("exact", "enharmonic", "equivalent"), (style, r)
    for name in ("Bb7sus4/Eb", "Bb11/Ab", "Dbmaj9", "Gbmaj7/F", "Ebm(add9)/Bb", "Cm11/Bb", "Fm9/Ab"):
        assert by_name[name]["roundtrip"]["match"] == "exact", (style, by_name[name])
    assert by_name["Abm"]["roundtrip"]["page_name"] == "Abm"
    assert by_name["Dbmaj9"]["number"] == "b7maj9" and by_name["Bb7sus4/Eb"]["number"] == "5^7sus4/1"


@needs_node
def test_numbers_and_notes():
    r = _voice(["4maj9#11", "b7maj9", "5^7sus4/1", "2-^7", "Ab3 Eb4 G4 Bb4 C5 D5", "60 64 67"], key="Eb major")
    assert [x["name"] for x in r[:4]] == ["Abmaj9#11", "Dbmaj9", "Bb7sus4/Eb", "Fm7"]
    assert [x["number"] for x in r[:4]] == ["4maj9#11", "b7maj9", "5^7sus4/1", "2m7"]
    assert all(not x["warnings"] or "no name" in x["warnings"][0] for x in r[:4])
    assert r[4]["notes"] == [56, 63, 67, 70, 72, 74] and r[4]["names"] == ["Ab3", "Eb4", "G4", "Bb4", "C5", "D5"]
    assert r[5]["name"] == "C" and r[5]["number"] == "6"  # C major in Eb major is the 6 chord, borrowed
    assert "--key" in _voice(["4maj7"])[0]["error"]
    assert "cannot read" in _voice(["Cmaj7zz"])[0]["error"]


@needs_node
@pytest.mark.parametrize("key,items,names", [
    # b6 in Eb major is spelled Cb from the key, but the page never shows a Cb root off the key's scale: it shows B
    ("Eb major", ["1", "4", "5", "6m", "b3", "b6", "b7maj9", "#4m7b5"], ["Eb", "Ab", "Bb", "Cm", "Gb", "B", "Dbmaj9", "Am7b5"]),
    ("C minor", ["1", "1m", "b3", "4", "5", "b6", "b7"], ["C", "Cm", "Eb", "F", "G", "Ab", "Bb"]),
    ("A minor", ["1m", "b3", "4m", "5"], ["Am", "C", "Dm", "E"]),
])
def test_plain_and_flat_numbers_are_numbers_not_notes(key, items, names):
    results = _voice(items, key=key)
    assert [r.get("error") for r in results] == [None] * len(items), results
    assert [r["kind"] for r in results] == ["number"] * len(items)
    assert [r["name"] for r in results] == names
    assert all(len(r["notes"]) >= 3 for r in results)


@needs_node
def test_midi_numbers_and_number_mistakes():
    r = _voice(["44 60 63", "44", "5", "1 4 5", "13", "b3 Eb4 Gb4"], key=None)
    assert r[0]["kind"] == "notes" and r[0]["notes"] == [44, 60, 63]
    assert r[1]["kind"] == "notes" and r[1]["notes"] == [44]
    assert "--key" in r[2]["error"]
    assert "Nashville numbers" in r[3]["error"] and '"1 | 4 | 5"' in r[3]["error"]
    assert "off the keyboard" in r[4]["error"]
    assert r[5]["kind"] == "notes" and r[5]["notes"] == [59, 63, 66]  # several tokens: lowercase b3 is the note B3


LIL = {1: 52, 2: 51, 3: 48, 4: 46, 5: 45, 6: 46, 7: 34}  # the bridge's low-interval limits


def _crowding(notes):
    return sum(1 for i, a in enumerate(notes) for b in notes[i + 1:] if 1 <= b - a <= 7 and a < LIL[b - a])


def _match_cost(a, b):
    """Semitones moved: the smaller chord's notes matched one-to-one to the larger's, leftovers to their nearest."""
    s, l = (a, b) if len(a) <= len(b) else (b, a)
    best = None
    for idx in permutations(range(len(l)), len(s)):
        cost = sum(abs(x - l[j]) for x, j in zip(s, idx))
        cost += sum(min(abs(m - n) for m in s) for j, n in enumerate(l) if j not in idx)
        best = cost if best is None else min(best, cost)
    return best


CYCLE = ["Cmaj7", "Fmaj7", "Bbmaj7", "Ebmaj7", "Abmaj7", "Dbmaj7", "Gbmaj7", "Bmaj7", "Emaj7", "Amaj7", "Dmaj7",
         "Gmaj7"] * 2
LEAD_PROGRESSIONS = [
    (None, CYCLE),
    (None, ["C7", "B7", "Bb7", "A7", "Ab7", "G7", "Gb7", "F7", "E7", "Eb7", "D7", "Db7", "C7"]),
    (None, ["C", "C/E", "C/G", "C", "F/C", "C", "G/B", "C"]),
    (None, ["G7", "C", "G7", "Cmaj7", "D7/F#", "G"]),
    ("Eb major", ["1maj9", "4maj9#11", "5^7sus4/1", "1maj9", "4m", "b7maj9", "5^7sus4", "1"]),
]


@needs_node
@pytest.mark.parametrize("style", ["close", "open", "spread", "drop2", "shell"])
def test_voice_leading_never_moves_more_than_the_plain_voicing_and_keeps_its_register(style):
    for key, chords in LEAD_PROGRESSIONS:
        plain = _voice(chords, key=key, voicing=style)
        led = _voice(chords, key=key, voicing=style, voice_lead=True)
        for i, (a, b) in enumerate(zip(plain, led)):
            notes, where = b["notes"], (style, chords[i], i)
            assert notes == sorted(set(notes)), where  # no repeated note
            assert notes[0] == a["notes"][0], where  # the bass stays where the style puts it
            upper, plain_upper = notes[1:], a["notes"][1:]
            assert abs(sum(upper) / len(upper) - sum(plain_upper) / len(plain_upper)) <= 7, where
            assert _crowding(notes) <= _crowding(a["notes"]), (where, notes)
            assert b["roundtrip"]["detected"] == a["roundtrip"]["detected"], where
            if i:
                step = _match_cost(led[i - 1]["notes"], notes)
                assert b["movement"] == step, where
                assert step <= _match_cost(led[i - 1]["notes"], a["notes"]), where
    assert CYCLE  # (the 24-chord cycle of fourths ran above in this style)


@needs_node
@pytest.mark.parametrize("style", ["close", "open", "drop2", "shell"])
def test_slash_basses_sit_at_c2_or_above_with_room_above_them(style):
    chords = ["F/A", "G/B", "Fmaj7/E", "Gbmaj7/F", "Bb11/Ab", "F#aug/D", "F#dim7/D#", "F/C", "Ab/C", "E7/G#",
              "Bb7sus4/Eb", "Fm9/Ab"]
    for r in _voice(chords, key="Eb major", voicing=style):
        n = r["notes"]
        assert n[0] >= 36 and n[1] - n[0] >= 5 and _crowding(n[:2]) == 0, (style, r["name"], r["names"])


@needs_node
def test_drop2_over_a_slash_bass_keeps_the_tension_that_names_the_chord():
    rs = _voice(["Cmaj13/G", "G13/D", "Cm11/G", "Dm11/A", "Cmaj9#11/G"], voicing="drop2")
    pcs = [{n % 12 for n in r["notes"]} for r in rs]
    assert 9 in pcs[0] and 4 in pcs[1] and 5 in pcs[2] and 7 in pcs[3]  # A, E (13ths); F, G (11ths)
    for r in rs[:4]:
        assert r["notes"][0] % 12 == "C Db D Eb E F Gb G Ab A Bb B".split().index(r["name"].split("/")[1])
        assert not {"thirteenth", "eleventh"} & set(r["roundtrip"]["omits"]), r
    assert any("leaves out the ninth" in w for w in rs[4]["warnings"]), rs[4]  # maj9#11 names its 9th
    c11 = _voice(["C11/G"], voicing="drop2")[0]  # a dominant 11 keeps its 11th and 9th and leaves out the 3rd
    assert {5, 2} <= {n % 12 for n in c11["notes"]} and 4 not in {n % 12 for n in c11["notes"]}
    assert any("leaves out the major 3rd" in w for w in c11["warnings"]), c11


@needs_node
def test_voice_leading_moves_less():
    chords = ["Dm9", "G13", "Cmaj9", "Fmaj7#11", "Bm7b5", "E7b9", "Am9"]
    plain = _voice(chords, voicing="close")
    led = _voice(chords, voicing="close", voice_lead=True)
    total = lambda rs: sum(r["movement"] for r in rs[1:])  # noqa: E731
    assert total(led) < total(plain)
    for a, b in zip(plain, led):
        assert a["notes"][0] % 12 == b["notes"][0] % 12  # the bass stays the bass
        assert b["roundtrip"]["match"] == a["roundtrip"]["match"]


PCS = "C Db D Eb E F Gb G Ab A Bb B".split()


@needs_node
def test_drop2_triads_double_the_root_on_top_over_a_root_bass():
    names = ["C", "Cm", "Csus4", "Csus2", "C5", "C7", "Cmaj7", "Bdim"]
    got = {r["input"]: r["notes"] for r in _voice(names, voicing="drop2")}
    assert got["C"] == [48, 55, 60, 64, 72]        # C3 | G3 C4 E4 C5: the C7 shape with the octave for the 7th
    assert got["Cm"] == [48, 55, 60, 63, 72]
    assert got["Csus4"] == [48, 55, 60, 65, 72] and got["Csus2"] == [48, 55, 60, 62, 72]
    assert got["C5"] == [48, 55, 60, 72]           # C3 | G3 C4 C5
    assert got["C7"] == [48, 55, 60, 64, 70] and got["Cmaj7"] == [48, 55, 60, 64, 71]  # seventh chords unchanged
    assert got["Bdim"] == [47, 53, 59, 62, 71]
    for suffix, upper_count in (("", 4), ("m", 4), ("dim", 4), ("aug", 4), ("sus2", 4), ("sus4", 4), ("5", 3)):
        for r in _voice([root + suffix for root in PCS], voicing="drop2"):
            n, root = r["notes"], PCS.index(r["input"][:-len(suffix)] if suffix else r["input"])
            upper = n[1:]
            assert n[0] % 12 == root and 41 <= n[0] <= 52, r                  # a root bass between F2 and E3
            assert len(upper) == upper_count and upper[-1] % 12 == root, r      # the doubled root on top
            # not an octave too high: the top root is F4..E5, except where the bass's tritone would crowd (Fdim..Adim
            # over F2..A2 lift the upper voices an octave, as a m7b5 drop 2 there does)
            assert upper[0] - n[0] >= 5 and upper[-1] - upper[0] <= 18, r
            assert upper[-1] <= (81 if suffix == "dim" else 76), r
            assert r["roundtrip"]["match"] in ("exact", "enharmonic"), r


@needs_node
@pytest.mark.parametrize("key,items,names", [
    ("Eb major", ["b6", "b2", "b5", "#4", "b3", "b7maj9"], ["B", "E", "A", "A", "Gb", "Dbmaj9"]),
    ("Db major", ["b3", "b7", "b6m", "4"], ["E", "B", "Am", "Gb"]),
    ("Gb major", ["4", "b7", "b3"], ["Cb", "E", "A"]),       # Cb is on Gb major's scale: the page shows it
    ("Eb minor", ["b6", "b2", "b3"], ["Cb", "E", "Gb"]),     # and on Eb minor's
    ("C major", ["#1m", "b1"], ["Dbm", "B"]),
])
def test_numbers_are_named_as_the_page_names_them(key, items, names):
    rs = _voice(items, key=key)
    assert [r["name"] for r in rs] == names, rs
    assert [r["number_typed"] for r in rs] == items


@needs_node
def test_no_number_in_any_page_key_gets_a_name_the_page_would_not_show():
    import re
    keys = [f"{k} major" for k in PCS[:6] + ["F#"] + PCS[7:]] + \
           [f"{k} minor" for k in "C C# D Eb E F F# G G# A Bb B".split()]
    items = [acc + str(d) + sfx for acc in ("", "b", "#") for d in range(1, 8) for sfx in ("", "m", "^7", "/5")]
    root_of = lambda name: re.match(r"[A-G](#{1,2}|b{1,2})?", name or "").group(0) if name else None  # noqa: E731
    checked = 0
    for key in keys:
        for r in _voice(items, key=key):
            assert not r.get("error"), (key, r)
            rt, root = r["roundtrip"], root_of(r["name"])
            if rt["match"] in ("exact", "enharmonic"):
                assert r["name"] == rt["page_name"], (key, r["input"], r["name"], rt)
            if re.search(r"[A-G](bb|##)", r["name"]) or root in ("E#", "B#", "Cb", "Fb"):
                assert root_of(rt["page_name"]) == root, (key, r["input"], r["name"], rt)  # F## in G# minor: the page's own
            checked += 1
    assert checked == len(keys) * len(items)


@needs_node
def test_dash_minor_chords_and_a_lone_two_digit_midi_note():
    rs = _voice(["C-7", "Bb-7", "F-9", "Eb-", "C-(maj7)", "C-^7"], key="Eb major")
    assert [(r["kind"], r["name"]) for r in rs] == [("chord", "Cm7"), ("chord", "Bbm7"), ("chord", "Fm9"), ("chord", "Ebm"),
                                                    ("chord", "Cm(maj7)"), ("chord", "Cm7")]
    assert _voice(["Bb-7"])[0]["name"] == "Bbm7"  # no key needed
    keyed, bare = _voice(["57"], key="Eb major")[0], _voice(["57"])[0]
    assert keyed["kind"] == "notes" and keyed["notes"] == [57]
    assert any("read as the MIDI note A3" in w and "5^7" in w for w in keyed["warnings"]), keyed
    assert bare["warnings"] == []  # without a key a number cannot be meant
    assert not any("MIDI note" in w for w in _voice(["44 60 63"], key="Eb major")[0]["warnings"])


def _root_pc(name):
    import re
    m = re.match(r"([A-G])(#{1,2}|b{1,2})?", name)
    acc = 0 if not m.group(2) else (len(m.group(2)) if m.group(2)[0] == "#" else -len(m.group(2)))
    return ("C D EF G A B".index(m.group(1)) + acc) % 12


@needs_node
@pytest.mark.parametrize("key,tonic", [("C major", 0), ("Eb major", 3), ("F# minor", 6)])
def test_a_number_whose_suffix_starts_with_an_accidental_keeps_its_root_and_tones(key, tonic):
    # (round 6: "5b9" was glued into the text "Gb9" and read back as a G-flat 9th; 4122 of 5040 such numbers had the
    # wrong root across the 24 page keys)
    want = {"1b5": (0, {0, 4, 6}), "5b9": (7, {7, 11, 2, 8}), "4#11": (5, {5, 9, 0, 11}), "5#5": (7, {7, 11, 3}),
            "5^b9": (7, {7, 11, 2, 8}), "b7b5": (10, {10, 2, 4}), "5^7b9": (7, {7, 11, 2, 5, 8}),
            "1^7#9": (0, {0, 4, 7, 10, 3}), "6b13": (9, {9, 1, 4, 5}), "2m7b5": (2, {2, 5, 8, 0}), "7b5/1": (11, {11, 3, 5, 0})}
    if key.endswith("minor"):
        want = {k: v for k, v in want.items() if k != "7b5/1"}
    rs = {r["input"]: r for r in _voice(list(want), key=key)}
    for item, (root, tones) in want.items():
        r = rs[item]
        assert not r.get("error"), r
        assert _root_pc(r["name"]) == (tonic + root) % 12, (key, item, r["name"], r["names"])
        pcs, full = {n % 12 for n in r["notes"]}, {(tonic + t) % 12 for t in tones}
        assert pcs <= full and full - pcs <= {(tonic + root + 7) % 12}, (key, item, r["names"])  # (a natural 5th may be left out)
        assert not any("reads back as" in w for w in r["warnings"]), (key, item, r["warnings"])
    if key == "C major":
        assert [rs[i]["name"] for i in ("5b9", "1b5", "4#11", "5#5", "6b13", "5^7b9")] == \
            ["G(b9)", "C(b5)", "F(#11)", "Gaug", "A(b13)", "G7b9"]
        assert rs["7b5/1"]["notes"][0] % 12 == 0 and rs["7b5/1"]["name"] == "B(b5)/C", rs["7b5/1"]
        assert any("no name for b9" in w for w in rs["5b9"]["warnings"]), rs["5b9"]
    if key == "Eb major":
        assert rs["5b9"]["name"] == "Bb(b9)" and rs["1b5"]["name"] == "Eb(b5)", rs


@needs_node
def test_minor_keys_follow_the_pages_relative_numbering_when_asked():
    items = ["1m", "6m", "1", "Am", "C", "F#m"]
    tonic = {r["input"]: r for r in _voice(items, key="A minor")}
    rel = {r["input"]: r for r in _voice(items, key="A minor", minor="relative")}
    assert (tonic["1m"]["name"], tonic["Am"]["number"], tonic["C"]["number"]) == ("Am", "1m", "b3"), tonic
    assert (rel["6m"]["name"], rel["1"]["name"], rel["1m"]["name"]) == ("Am", "C", "Cm"), rel
    assert (rel["Am"]["number"], rel["C"]["number"], rel["Am"]["roundtrip"]["page_number"]) == ("6m", "1", "6m"), rel
    assert rel["6m"]["number_typed"] == "6m" and not rel["6m"]["warnings"], rel["6m"]
    with pytest.raises(pianocue.VoicingError, match="minor must be tonic or relative"):
        _voice(["Am"], key="A minor", minor="dorian")


@needs_node
def test_minor_flag_on_the_cli(capsys):
    code, out, _ = _run(["voicing", "Am", "--key", "A minor", "--minor", "relative", "--json"], capsys)
    assert code == 0 and json.loads(out)[0]["number"] == "6m", out
    code, out, _ = _run(["voicing", "Am", "--key", "A minor", "--json"], capsys)
    assert code == 0 and json.loads(out)[0]["number"] == "1m", out


@needs_node
def test_an_off_keyboard_token_that_looks_like_a_number_says_so():
    keyed, bare, plain = _voice(["17"], key="Eb major")[0], _voice(["17"])[0], _voice(["13"], key="Eb major")[0]
    assert "off the keyboard" in keyed["error"] and 'did you mean the Nashville number "1^7"?' in keyed["error"], keyed
    assert '"1^7"' in bare["error"] and "needs --key" in bare["error"], bare
    assert "off the keyboard" in plain["error"] and "did you mean" not in plain["error"], plain
    assert _voice(["1^7"], key="Eb major")[0]["name"] == "Eb7"


@needs_node
def test_drop2_slash_bass_with_an_octave_is_the_dropped_voice_not_two_octaves_under():
    cg, c, g7d = _voice(["C/G", "C", "G7/D"], voicing="drop2", octave=3)
    assert cg["names"] == ["G2", "C3", "E3", "C4"] and cg["roundtrip"]["match"] == "exact", cg  # was G1 G2 C3 E3 C4
    assert c["names"] == ["C2", "G2", "C3", "E3", "C4"], c  # (the --octave help's own example, unchanged)
    assert g7d["notes"][0] == 38 and g7d["notes"].count(38) == 1, g7d  # D2: a bass in octave N-1 keeps its place


# ---------------------------------------------------------------------------------------- cues.js player
PLAYER_SCRIPT = r"""
const { createCuePlayer } = await import(%(url)s);
let T = 1000;
const target = new EventTarget();
const make = (ev, extra = {}) => createCuePlayer({
  now: () => T, timer: "timeout", startDelayMs: 0, lifecycleTarget: target,
  noteOn: (m, v, meta) => ev.push({ k: "on", m, t: T, at: meta.at }),
  noteOff: (m, meta) => ev.push({ k: "off", m, t: T, reason: meta.reason }),
  caption: (info) => ev.push({ k: "cap", t: T - 1000, label: info && info.label, source: info && info.source,
                               under: info && info.under ? info.under.label : null }),
  ...extra });
const walk = (p, ms, step = 10) => { for (let e = 0; e < ms; e += step) { T += step; p.pump(); } };
const steps = Array.from({ length: 24 }, (_, i) => ({ at_ms: i * 250, type: "play", notes: [60 + (i %% 12)], hold_ms: 200 }));
const out = {};

// frozen timers: 1 s of playing, then the clock jumps 3 s at once (a laptop asleep, a tab frozen without pagehide)
let ev = [], p = make(ev, { lateDropMs: 250 });
p.handle({ type: "sequence", steps }, { id: 1 });
walk(p, 1000);
const before = ev.filter((e) => e.k === "on").length;
T += 3000;
p.pump();
const burst = ev.filter((e) => e.k === "on" && e.t === T).length;
walk(p, 3000);
out.freeze = { before, burst, ons: ev.filter((e) => e.k === "on").length, state: p.state(),
               late: ev.filter((e) => e.k === "on").map((e) => Math.round(e.t - e.at)) };
p.dispose();

// pagehide: the queue is cancelled and the notes released, and nothing plays after the page returns
T = 1000; ev = []; p = make(ev);
p.handle({ type: "sequence", steps }, { id: 2 });
walk(p, 1050);
target.dispatchEvent(new Event("pagehide"));
const hidden = p.state();
T += 5000;
p.pump();
walk(p, 2000);
out.pagehide = { hidden, after: p.state(), ons: ev.filter((e) => e.k === "on").length,
                 reasons: ev.filter((e) => e.k === "off").map((e) => e.reason) };
p.dispose();
const disposedStillListens = (() => { const q = make([]); q.dispose(); target.dispatchEvent(new Event("pagehide")); return q.state().pageHides; })();
out.pagehide.after_dispose = disposedStillListens;

// captions: a replay keeps its own caption on top with the step under it; Claude's labelled steps show over theirs
for (const source of ["replay", "claude"]) {
  T = 1000; ev = []; p = make(ev);
  p.handle({ type: "sequence", source, label: "you, at 0:30", detail: "8 s", steps: [
    { at_ms: 0, type: "play", notes: [48], hold_ms: 1000, label: "Cm", detail: "1m in C minor" },
    { at_ms: 500, type: "play", notes: [60], hold_ms: 300, label: "Ab", detail: "b6 in C minor" },
    { at_ms: 1200, type: "play", notes: [62], hold_ms: 200 }] }, { id: 3 });
  walk(p, 1600);
  out[source] = ev.filter((e) => e.k === "cap").map((e) => [e.t, e.label, e.under]);
  p.dispose();
}
console.log(JSON.stringify(out));
process.exit(0);
"""


@needs_node
def test_cue_player_never_bursts_after_a_freeze_or_a_pagehide_and_a_replay_keeps_its_caption():
    script = PLAYER_SCRIPT % {"url": json.dumps((ROOT / "arsenal" / "web" / "piano" / "cues.js").as_uri())}
    proc = subprocess.run([NODE, "--input-type=module", "-"], input=script, capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    freeze = out["freeze"]
    assert freeze["before"] == 5 and freeze["burst"] <= 2, freeze          # at most one step's worth, never ten at once
    assert freeze["state"]["lateDropped"] == 10 and freeze["ons"] == 24 - 10, freeze
    assert max(freeze["late"]) <= 250 and freeze["state"]["pending"] == 0, freeze

    ph = out["pagehide"]
    assert ph["hidden"]["pending"] == 0 and ph["hidden"]["sounding"] == [] and ph["hidden"]["pageHides"] == 1, ph
    assert ph["ons"] == 5 and ph["after"]["noteOns"] == 5 and ph["reasons"][-1] == "pagehide", ph
    assert ph["after_dispose"] == 0  # a disposed player stops listening

    # replay: the sequence caption stays on top from 0 to its end, and the newest step's caption sits under it
    assert out["replay"] == [[0, "you, at 0:30", "Cm"], [500, "you, at 0:30", "Ab"], [800, "you, at 0:30", "Cm"],
                             [1000, "you, at 0:30", None], [1400, None, None]], out["replay"]
    assert out["claude"] == [[0, "Cm", None], [500, "Ab", None], [800, "Cm", None], [1000, "you, at 0:30", None],
                             [1400, None, None]], out["claude"]


TIMING_SCRIPT = r"""
const { createCuePlayer } = await import(%(url)s);
let T = 1000;
const WALL = 1789000000000;
const make = (ev, extra = {}) => createCuePlayer({
  now: () => T, timer: "timeout", startDelayMs: 50, lateDropMs: 250, lifecycleTarget: new EventTarget(),
  noteOn: (m, v, meta) => ev.push({ k: "on", m, t: T - 1000, at: meta.at, cue: meta.cue_id, label: meta.label }),
  noteOff: (m, meta) => ev.push({ k: "off", m, t: T - 1000, cue: meta.cue_id, reason: meta.reason }),
  ...extra });
const walk = (p, ms, step = 5) => { for (let e = 0; e < ms; e += step) { T += step; p.pump(); } };
const cuesWithin40 = (ons) => Math.max(0, ...ons.map((o) => new Set(ons.filter((x) => x.t >= o.t && x.t - o.t < 40).map((x) => x.cue)).size));
const firstOn = (ons, cue) => { const o = ons.find((e) => e.cue === cue); return o ? o.t : null; };
const out = {};

// three separate cues sent 700 ms apart reach the page at once (a freeze, a stall, a reconnect replay)
{ T = 1000; const ev = [], p = make(ev);
  [2400, 1700, 1000].forEach((age, i) => p.handle({ type: "play", notes: [48 + i, 55 + i, 64 + i], hold_ms: 1200 },
                                                  { id: i + 1, sent_at: WALL + T - age, age_ms: age }));
  walk(p, 4000);
  const ons = ev.filter((e) => e.k === "on");
  out.backlog = { first: [1, 2, 3].map((c) => firstOn(ons, c)), within40: cuesWithin40(ons), spaced: p.state().spaced, ons: ons.length };
  p.dispose(); }

// live cues with a few ms of network jitter start on arrival: nothing is pushed later
{ T = 1000; const ev = [], p = make(ev);
  const lat = [12, 2, 20, 5, 18, 3], arrivals = [];
  lat.forEach((l, i) => {
    const sent = 1000 + i * 400;
    while (T < sent + l) { T += 1; p.pump(); }
    arrivals.push(T - 1000);
    p.handle({ type: "play", notes: [60 + i], hold_ms: 100 }, { id: 10 + i, sent_at: WALL + sent, age_ms: l });
  });
  walk(p, 600);
  out.jitter = { spaced: p.state().spaced, delay: ev.filter((e) => e.k === "on").map((e, i) => e.at - 1000 - arrivals[i] - 50) };
  p.dispose(); }

// a cue that arrived 3 s late on its own (a reconnect replaying one cue) does not push the next, fresh cue late
{ T = 1000; const ev = [], p = make(ev);
  p.handle({ type: "play", notes: [60], hold_ms: 100 }, { id: 15, sent_at: WALL + T - 3000, age_ms: 3000 });
  walk(p, 700);
  const arrived = T - 1000;
  p.handle({ type: "play", notes: [62], hold_ms: 100 }, { id: 16, sent_at: WALL + T - 5, age_ms: 5 });
  walk(p, 400);
  out.loneLate = { spaced: p.state().spaced, delay: ev.filter((e) => e.k === "on" && e.cue === 16).map((e) => e.at - 1000 - arrived - 50) };
  p.dispose(); }

// a clear among the backlog acts at once (round 6): the cue that arrived before it never sounds, the one after it does
{ T = 1000; const ev = [], p = make(ev);
  p.handle({ type: "play", notes: [48, 52, 55], hold_ms: 0, label: "A" }, { id: 21, sent_at: WALL + T - 2000, age_ms: 2000 });
  p.handle({ type: "clear" }, { id: 22, sent_at: WALL + T - 1300, age_ms: 1300 });
  p.handle({ type: "play", notes: [50, 53, 57], hold_ms: 0, label: "B" }, { id: 23, sent_at: WALL + T - 600, age_ms: 600 });
  walk(p, 3000);
  out.clear = { ons: ev.filter((e) => e.k === "on").map((e) => [e.cue, e.m, e.t]), offs: ev.filter((e) => e.k === "off").map((e) => [e.cue, e.m, e.t, e.reason]),
                sounding: p.state().sounding, clears: p.state().clears };
  p.clear();
  out.clear.after = p.state().sounding;
  p.dispose(); }

// two clears among a backlog, each acting at once; and the same with a pagehide after
for (const hideAt of [null, 800]) {
  T = 1000; const ev = [], target = new EventTarget(), p = make(ev, { lifecycleTarget: target });
  const send = (cue, id, age) => p.handle(cue, { id, sent_at: WALL + T - age, age_ms: age });
  send({ type: "play", notes: [48], hold_ms: 0 }, 60, 3000);  // starts at 50
  send({ type: "clear" }, 61, 2500);                          // 550
  send({ type: "play", notes: [50], hold_ms: 0 }, 62, 2000);  // 1050
  send({ type: "clear" }, 63, 1500);                          // 1550
  send({ type: "play", notes: [52], hold_ms: 0 }, 64, 1000);  // 2050
  const r = { clears: p.state().clears };
  if (hideAt !== null) { walk(p, hideAt); r.before = p.state().pending; target.dispatchEvent(new Event("pagehide")); r.hidden = p.state().pending; }
  walk(p, 3000);
  Object.assign(r, { ons: ev.filter((e) => e.k === "on").map((e) => [e.cue, e.t]), offs: ev.filter((e) => e.k === "off").map((e) => [e.cue, e.t, e.reason]),
                     sounding: p.state().sounding, pending: p.state().pending });
  (out.clears ||= []).push(r);
  p.dispose();
}

// a 420 ms jank starting 150 ms before chord 3 of a slow progression: chord 3 plays late, nothing is dropped
{ T = 1000; const ev = [], p = make(ev);
  const prog = [[36, 52, 58, 62, 67], [41, 51, 57, 60, 65], [43, 53, 59, 62, 67], [36, 52, 55, 60, 64]];
  p.handle({ type: "sequence", steps: prog.map((n, i) => ({ at_ms: i * 1000, type: "play", notes: n, hold_ms: 1100, label: `chord ${i + 1}` })) },
           { id: 30, sent_at: WALL + T, age_ms: 0 });
  while (T < 1000 + 50 + 2000 - 150) { T += 5; p.pump(); }
  T += 420;
  p.pump();
  walk(p, 3000);
  const late = {};
  for (const o of ev.filter((e) => e.k === "on")) (late[o.label] ||= []).push(Math.round(o.t + 1000 - o.at));
  out.jank = { late, lateDropped: p.state().lateDropped };
  p.dispose(); }

// a 2 s stall inside a fast walk, with another cue's chord falling due in it: the walk plays on from its newest step,
// and the other cue's chord (a different layer) still sounds
{ T = 1000; const ev = [], p = make(ev);
  p.handle({ type: "sequence", steps: Array.from({ length: 40 }, (_, i) => ({ at_ms: i * 125, type: "play", notes: [72 + (i %% 12)], hold_ms: 100 })) }, { id: 40 });
  walk(p, 600);
  p.handle({ type: "play", notes: [36, 43, 52], hold_ms: 0, label: "pad" }, { id: 41 });
  T += 2000;
  p.pump();
  const atResume = ev.filter((e) => e.k === "on" && e.t === T - 1000);
  walk(p, 4000);
  out.stall = { walkAtResume: atResume.filter((e) => e.cue === 40).length, padAtResume: atResume.filter((e) => e.cue === 41).length,
                lateDropped: p.state().lateDropped, walkOns: ev.filter((e) => e.k === "on" && e.cue === 40).length };
  p.dispose(); }

// the bass octave: a chord of 3+ notes whose lowest is below C3 also sounds that note an octave up, synth only
{ T = 1000; const calls = [];
  let h = 0;
  const voice = { noteOn: (m, v, when) => { calls.push(["on", m, v, !!when.synthOnly, ++h]); return h; }, release: (hd) => calls.push(["release", hd]) };
  const ev = [], p = make(ev, { voice, bassDouble: true, lookaheadMs: 0 });
  p.handle({ type: "play", notes: [36, 52, 55, 60], velocity: 100, hold_ms: 300 }, { id: 50 });
  walk(p, 400);
  const first = calls.splice(0);
  for (const notes of [[36, 48, 55], [36, 43], [50, 55, 60]]) p.handle({ type: "play", notes, hold_ms: 100 }, { id: 51 });
  walk(p, 200);
  const none = calls.splice(0).filter((c) => c[0] === "on" && c[3]).length;
  p.handle({ type: "play", notes: [38, 53, 57], hold_ms: 0 }, { id: 52 });
  walk(p, 100);
  p.clear();
  const cleared = calls.splice(0);
  p.setBassDouble(false);
  p.handle({ type: "play", notes: [36, 52, 55], hold_ms: 100 }, { id: 53 });
  walk(p, 200);
  out.double = { first, none, cleared, off: calls.filter((c) => c[0] === "on" && c[3]).length,
                 keys: ev.filter((e) => e.k === "on" && e.cue === 50).map((e) => e.m), doubled: p.state().doubled };
  p.dispose(); }

// round 6: a live stream after a stalled backlog. The backlog is spaced; the first fresh cue starts on arrival and drops
// the backlog cues still waiting; every live cue after it starts on arrival (they were chained 2.3 s late)
{ T = 1000; const ev = [], p = make(ev);
  [2400, 1700, 1000].forEach((age, i) => p.handle({ type: "play", notes: [48 + i, 55 + i, 64 + i], hold_ms: 3000 },
                                                  { id: 70 + i, sent_at: WALL + T - age, age_ms: age }));
  walk(p, 100);                                   // the first started at 50; the others (750, 1450) still wait
  const arrivals = [];
  for (let i = 0; i < 6; i++) {
    arrivals.push(T - 1000);
    p.handle({ type: "play", notes: [72 + i], hold_ms: 300 }, { id: 80 + i, sent_at: WALL + T - 1, age_ms: 1 });
    walk(p, 600);
  }
  walk(p, 3000);
  const ons = ev.filter((e) => e.k === "on");
  out.stream = { backlog: [70, 71, 72].map((c) => firstOn(ons, c)), live: arrivals.map((a, i) => firstOn(ons, 80 + i) - a),
                 dropped: p.state().backlogDropped, spaced: p.state().spaced, sounding: p.state().sounding };
  p.dispose(); }

// round 6: a clear right after a stalled backlog acts at once (it waited 2.4 s behind the backlog)
{ T = 1000; const ev = [], p = make(ev);
  [2400, 1700, 1000].forEach((age, i) => p.handle({ type: "play", notes: [50 + i, 57 + i, 65 + i], hold_ms: 3000 },
                                                  { id: 90 + i, sent_at: WALL + T - age, age_ms: age }));
  walk(p, 100);
  p.handle({ type: "clear" }, { id: 93, sent_at: WALL + T - 1, age_ms: 1 });
  const at = T - 1000;
  walk(p, 3000);
  const offs = ev.filter((e) => e.k === "off");
  out.clearNow = { at, offs: [...new Set(offs.map((e) => e.t))], reasons: [...new Set(offs.map((e) => e.reason))],
                   ons: ev.filter((e) => e.k === "on").map((e) => [e.cue, e.t]), sounding: p.state().sounding, pending: p.state().pending };
  p.dispose(); }

// round 6: the player admits each sounding cue with the voice as it arrives and passes the cue's key with every strike
{ T = 1000; const seen = [], admitted = [];
  const voice = { admitCue: (info) => { admitted.push(info.id); return `k${info.id}`; },
                  noteOn: (m, v, when) => { seen.push([m, when.cue]); return seen.length; }, release: () => {} };
  const p = make([], { voice, lookaheadMs: 0 });
  p.handle({ type: "play", notes: [60, 64], hold_ms: 100 }, { id: 101, sent_at: WALL + T, age_ms: 0 });
  p.handle({ type: "hover", notes: [62], hold_ms: 100 }, { id: 102, sent_at: WALL + T, age_ms: 0 });
  p.handle({ type: "sequence", steps: [{ at_ms: 0, type: "play", notes: [48], hold_ms: 50 }, { at_ms: 100, type: "play", notes: [50], hold_ms: 50 }] },
           { id: 103, sent_at: WALL + T, age_ms: 0 });
  walk(p, 400);
  out.admit = { admitted, seen };
  p.dispose(); }
console.log(JSON.stringify(out));
process.exit(0);
"""


@needs_node
def test_cue_player_spaces_cues_that_arrive_together_and_only_drops_steps_something_overtook():
    script = TIMING_SCRIPT % {"url": json.dumps((ROOT / "arsenal" / "web" / "piano" / "cues.js").as_uri())}
    proc = subprocess.run([NODE, "--input-type=module", "-"], input=script, capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    b = out["backlog"]  # ages 2400, 1700, 1000: they play in order, as far apart as they were sent
    assert b["first"] == [50, 750, 1450] and b["within40"] == 1 and b["spaced"] == 2 and b["ons"] == 9, b
    assert out["jitter"] == {"spaced": 0, "delay": [0, 0, 0, 0, 0, 0]}, out["jitter"]
    assert out["loneLate"] == {"spaced": 0, "delay": [0]}, out["loneLate"]  # a late cue alone delays nothing after it

    c = out["clear"]  # a clear acts at once, backlog or not: A (before it) never sounds, B (after it) does
    assert [x[0] for x in c["ons"]] == [23, 23, 23] and {x[2] for x in c["ons"]} == {50}, c
    assert c["offs"] == [] and c["sounding"] == [50, 53, 57] and c["clears"] == 1 and c["after"] == [], c
    through, hidden = out["clears"]  # two clears among a backlog, each at once; then the same with a pagehide at 800 ms
    assert through == {"clears": 2, "ons": [[64, 50]], "offs": [], "sounding": [52], "pending": 0}, through
    assert hidden == {"clears": 2, "before": 0, "hidden": 0, "ons": [[64, 50]], "offs": [[64, 800, "pagehide"]],
                      "sounding": [], "pending": 0}, hidden

    assert out["jank"] == {"late": {"chord 1": [0] * 5, "chord 2": [0] * 5, "chord 3": [270] * 5, "chord 4": [0] * 5},
                           "lateDropped": 0}, out["jank"]

    s = out["stall"]
    assert s["walkAtResume"] <= 2 and s["padAtResume"] == 3 and s["lateDropped"] >= 14, s

    d = out["double"]
    assert d["first"][:2] == [["on", 36, 100, False, 1], ["on", 48, 50, True, 2]], d  # the bass, then its octave
    assert [c[1] for c in d["first"] if c[0] == "on"] == [36, 48, 52, 55, 60] and ["release", 1] in d["first"] \
        and ["release", 2] in d["first"], d
    assert d["none"] == 0, d  # the octave already there, two notes, a bass at C3 or above: no double
    assert sum(1 for c in d["cleared"] if c[0] == "on" and c[3]) == 1 and len([c for c in d["cleared"] if c[0] == "release"]) == 4, d
    assert d["off"] == 0 and d["keys"] == [36, 52, 55, 60] and d["doubled"] == 2, d  # the octave is never a key; off stops it

    st = out["stream"]  # the first live cue drops the two backlog cues still waiting; every live cue starts on arrival
    assert st == {"backlog": [50, None, None], "live": [50] * 6, "dropped": 2, "spaced": 2, "sounding": []}, st
    cn = out["clearNow"]  # a clear right after a backlog silences at once, and nothing that waited plays
    assert cn == {"at": 100, "offs": [100], "reasons": ["clear"], "ons": [[90, 50]] * 3, "sounding": [], "pending": 0}, cn
    ad = out["admit"]  # the voice hears of each sounding cue as it arrives (not a hover), and every strike carries its key
    assert ad["admitted"] == [101, 103], ad
    assert sorted(ad["seen"]) == [[48, "k103"], [50, "k103"], [60, "k101"], [64, "k101"]], ad


TABS_SCRIPT = r"""
const { createClaudeVoice, createCueClient } = await import(%(url)s);
const tick = (ms = 40) => new Promise((r) => setTimeout(r, ms));
function fakeWindow() { const w = new EventTarget(); const d = new EventTarget(); d.visibilityState = "visible"; w.document = d; return w; }
const stubMidi = (sent) => ({ outputs: new Map([["p", { id: "p", name: "stub", send: (b) => sent.push(b) }]]) });
const channel = `test-${Date.now()}`;
const out = {};
const sentA = [], sentB = [];
const wa = fakeWindow(), wb = fakeWindow();
const a = createClaudeVoice({ midiAccess: stubMidi(sentA), lifecycleTarget: wa, unlockTarget: null, channel });
await a.setMidiOutput("p");
await tick(10);
const b = createClaudeVoice({ midiAccess: stubMidi(sentB), lifecycleTarget: wb, unlockTarget: null, channel });
await b.setMidiOutput("p");
await tick();
const sounds = () => [a.noteOn(60, 80) !== null, b.noteOn(60, 80) !== null];
out.newest = sounds();                                                   // the tab opened last
wa.dispatchEvent(new Event("pointerdown"));
await tick();
out.clicked = sounds();                                                  // the tab Daniel clicked
wa.document.visibilityState = "hidden";
wa.document.dispatchEvent(new Event("visibilitychange"));
await tick();
out.visible = sounds();                                                  // the visible tab beats a hidden one
wa.document.visibilityState = "visible";
wa.document.dispatchEvent(new Event("visibilitychange"));
await tick();
wb.dispatchEvent(new Event("pagehide"));
await tick();
out.afterPagehide = a.noteOn(62, 80) !== null;                           // a tab in the back/forward cache said bye
wb.dispatchEvent(new Event("pageshow"));
await tick();
out.afterPageshow = sounds();                                            // back from the cache it takes part again (a was touched later)
out.synthOnlySkipsMidi = (() => { const n = sentA.length; const h = a.noteOn(40, 50, { synthOnly: true }); return [h, sentA.length - n]; })();
b.dispose();
await tick();
const c = createClaudeVoice({ lifecycleTarget: fakeWindow(), unlockTarget: null, channel });  // cannot sound (no MIDI, no audio)
await tick();
out.silentPeer = a.noteOn(64, 80) !== null;                              // a newer tab that cannot sound does not take over
out.stats = { a: a.stats().tab.peers.length, yieldedA: a.stats().yielded, yieldedB: b.stats().yielded, midiA: sentA.length > 0, midiB: sentB.length > 0 };
a.dispose(); c.dispose();

// round 6, per cue: the voice stays with the tabs that had the cue when it arrived
{
  const ch2 = `${channel}-cue`;
  const w1 = fakeWindow(), w2 = fakeWindow(), w3 = fakeWindow();
  const mk = async (w) => { const v = createClaudeVoice({ midiAccess: stubMidi([]), lifecycleTarget: w, unlockTarget: null, channel: ch2 });
                            await v.setMidiOutput("p"); await tick(10); return v; };
  const v1 = await mk(w1), v2 = await mk(w2);
  await tick();
  w1.dispatchEvent(new Event("pointerdown")); await tick();                  // tab 1 leads
  const S = 1789000000000;
  const walkKey = [v1, v2].map((v) => v.admitCue({ id: 7, sent_at: S }));    // a walk reaches both tabs
  const hits = (key, vs) => vs.map((v) => v.noteOn(60, 80, { cue: key }) !== null);
  const r = { keysAgree: walkKey[0] === walkKey[1], start: hits(walkKey[0], [v1, v2]) };
  const v3 = await mk(w3); await tick();                                      // a new tab opens mid-walk
  w3.dispatchEvent(new Event("pointerdown")); await tick();                  // and Daniel clicks it
  r.newTabClicked = hits(walkKey[0], [v1, v2]);                               // the walk stays in tab 1: tab 3 never had it
  r.newTabLeadsNewCues = [v1, v2, v3].map((v) => v.stats().tab.leader);
  const nextKey = [v1, v2, v3].map((v) => v.admitCue({ id: 8, sent_at: S + 5000 }));
  r.nextCue = hits(nextKey[0], [v1, v2, v3]);                                 // the next cue sounds in tab 3
  const oldId = v1.stats().tab.id;
  w1.dispatchEvent(new Event("pagehide")); await tick();                     // tab 1 leaves mid-walk
  r.leaderLeft = hits(walkKey[0], [v2]);                                      // tab 2, which has the walk, takes over
  w1.dispatchEvent(new Event("pageshow")); await tick();                     // tab 1 comes back (its player was cleared)
  w1.dispatchEvent(new Event("pointerdown")); await tick();                  // and is clicked
  r.backWithNewId = v1.stats().tab.id !== oldId;
  r.afterReturn = hits(walkKey[0], [v2]);                                     // the walk stays in tab 2
  const localKey = v2.admitCue({ id: "local-1" });                            // a local cue, in tab 2 only
  r.local = [localKey.startsWith("local:"), hits(localKey, [v2])[0]];
  r.noKey = [v1.noteOn(61, 80) !== null, v2.noteOn(61, 80) !== null];         // no cue key: whichever tab leads now
  r.firstLoadKeepsId = (() => { const id0 = v2.stats().tab.id; w2.dispatchEvent(new Event("pageshow")); return v2.stats().tab.id === id0; })();
  out.perCue = r;
  v1.dispose(); v2.dispose(); v3.dispose();
}

// the client closes its stream on freeze and reopens on resume; a back/forward cache return reopens once, on pageshow
class FakeES {
  constructor(url) { this.url = url; this.readyState = 0; this.closed = false; FakeES.all.push(this);
                     setTimeout(() => { if (!this.closed) { this.readyState = 1; if (this.onopen) this.onopen(); } }, 1); }
  addEventListener() {}
  close() { this.closed = true; this.readyState = 2; }
}
FakeES.CLOSED = 2;
FakeES.all = [];
const w = fakeWindow();
const client = createCueClient({ EventSourceImpl: FakeES, fetchImpl: null, lifecycleTarget: w });
await tick(10);
const open = () => FakeES.all.filter((e) => !e.closed).length;
w.document.dispatchEvent(new Event("freeze"));
out.frozen = { status: client.status, open: open() };
w.document.dispatchEvent(new Event("resume"));
await tick(10);
out.resumed = { status: client.status, made: FakeES.all.length, open: open(), url: FakeES.all[FakeES.all.length - 1].url };
w.dispatchEvent(new Event("pagehide"));
w.document.dispatchEvent(new Event("freeze"));
const made = FakeES.all.length;
w.document.dispatchEvent(new Event("resume"));
out.cacheResume = FakeES.all.length - made;
const shown = new Event("pageshow");
Object.defineProperty(shown, "persisted", { value: true });
w.dispatchEvent(shown);
await tick(10);
out.cacheShown = { made: FakeES.all.length - made, open: open(), status: client.status, pauses: client.stats().pauses };
client.close();
console.log(JSON.stringify(out));
process.exit(0);
"""


@needs_node
def test_only_one_tab_sounds_claudes_voice_and_a_frozen_page_closes_its_stream():
    script = TABS_SCRIPT % {"url": json.dumps((ROOT / "arsenal" / "web" / "piano" / "cues.js").as_uri())}
    proc = subprocess.run([NODE, "--input-type=module", "-"], input=script, capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["newest"] == [False, True] and out["clicked"] == [True, False] and out["visible"] == [False, True], out
    assert out["afterPagehide"] is True and out["afterPageshow"] == [True, False], out
    assert out["synthOnlySkipsMidi"] == [None, 0], out  # no audio in node and no MIDI for a synth-only strike: silent
    assert out["silentPeer"] is True and out["stats"]["midiA"] and out["stats"]["midiB"], out
    assert out["stats"]["yieldedA"] == 2 and out["stats"]["yieldedB"] == 2, out  # each strike sounded in one tab only
    assert out["frozen"] == {"status": "paused", "open": 0}, out
    assert out["resumed"]["status"] == "listening" and out["resumed"]["made"] == 2 and out["resumed"]["open"] == 1, out
    assert "lastEventId" not in out["resumed"]["url"], out  # what was sent while frozen is not replayed
    assert out["cacheResume"] == 0 and out["cacheShown"]["made"] == 1 and out["cacheShown"]["open"] == 1, out
    assert out["cacheShown"]["status"] == "listening" and out["cacheShown"]["pauses"] == 2, out

    pc = out["perCue"]  # round 6: the voice never passes mid-cue to a tab that does not have the cue
    assert pc["keysAgree"] and pc["start"] == [True, False], pc
    assert pc["newTabClicked"] == [True, False] and pc["newTabLeadsNewCues"] == [False, False, True], pc
    assert pc["nextCue"] == [False, False, True], pc
    assert pc["leaderLeft"] == [True] and pc["backWithNewId"] and pc["afterReturn"] == [True], pc
    assert pc["local"] == [True, True] and pc["noKey"] == [True, False] and pc["firstLoadKeepsId"], pc


LABELS_SCRIPT = r"""
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { pathToFileURL } from "node:url";
const ROOT = %(root)s;
const src = readFileSync(ROOT + "web/piano.js", "utf8");
const A = src.indexOf("// ===== THEORY BEGIN"), B = src.indexOf("// ===== THEORY END");
const Theory = new Function(src.slice(A, B) + "\nreturn Theory;")();
const NV = await import(pathToFileURL(ROOT + "web/piano/nashville.js").href);
// the page's own spellForKey, run out of piano.js, with the minor-key numbering under test (the page's pref)
const s0 = src.indexOf("function spellForKey(info, key) {"), s1 = src.indexOf("\n}\n", s0) + 2;
if (s0 < 0) throw new Error("spellForKey is gone from piano.js");
const spellForKey = new Function("Theory", "spellInKey", "theoryUi", "ODD_NAMES", src.slice(s0, s1) + "\nreturn spellForKey;")(
  Theory, NV.spellInKey, { minor: %(minor)s }, new Set(["E#", "B#", "Cb", "Fb"]));
const page = (notes, keyName) => { const k = NV.parseKey(keyName); return spellForKey(Theory.detect(notes, k.bias), k).name; };
const bridge = (items, key) => JSON.parse(execFileSync(process.execPath, [ROOT + "pianocue_voicing.mjs"], {
  input: JSON.stringify({ items, key, voicing: "close", minor: %(minor)s }), encoding: "utf8", maxBuffer: 1e8,
  env: { ...process.env, PIANOCUE_OWN_SPELLING: %(own)s } })).results;
const KEYS = [...["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"].map((k) => k + " major"),
              ...["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"].map((k) => k + " minor")]
  .filter((k) => %(minor)s === "tonic" || k.endsWith(" minor"));  // relative numbering changes minor keys only
const NOTES = [];
for (let lo = 60; lo < 72; lo++) {
  NOTES.push(String(lo), `${lo} ${lo + 12}`, `${lo} ${lo + 1} ${lo + 2}`);
  for (let iv = 1; iv < 12; iv++) NOTES.push(`${lo} ${lo + iv}`);
}
const CHORDS = [];
for (const r of ["C", "C#", "Db", "D#", "Eb", "E", "F#", "Gb", "G#", "Ab", "A#", "Bb", "B", "Cb", "E#"])
  for (const s of ["", "m", "7", "maj7", "m7b5", "dim7", "sus4", "9", "5"]) CHORDS.push(r + s);
CHORDS.push("C/E", "Ab7/Gb", "Dbm7/B", "F#/A#");
const out = { keys: KEYS.length, notes: 0, chords: 0, mismatches: [] };
for (const key of KEYS) {
  for (const r of bridge(NOTES, key)) {
    out.notes++;
    const want = page(r.notes, key);
    if (r.name !== want) out.mismatches.push([key, r.input, r.name, want]);
  }
  for (const r of bridge(CHORDS, key)) {
    if (r.error || !["exact", "enharmonic"].includes(r.roundtrip.match)) continue;
    out.chords++;
    const want = page(r.notes, key);
    if (r.name !== want) out.mismatches.push([key, r.input, r.name, want]);
  }
}
console.log(JSON.stringify(out));
process.exit(0);
"""


@needs_node
# the bridge runs spellForKey out of piano.js (its copy stands in); minor: the page's arsenal.piano.minor pref
@pytest.mark.parametrize("own_spelling,minor", [(False, "tonic"), (True, "tonic"), (False, "relative"), (True, "relative")])
def test_labels_in_a_key_match_the_pages_real_spellforkey(own_spelling, minor):
    script = LABELS_SCRIPT % {"root": json.dumps(str(ROOT / "arsenal").replace("\\", "/") + "/"),
                              "own": json.dumps("1" if own_spelling else "0"), "minor": json.dumps(minor)}
    proc = subprocess.run([NODE, "--input-type=module", "-"], input=script, capture_output=True, text=True,
                          encoding="utf-8", timeout=300)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["notes"] == out["keys"] * 12 * 14 and out["chords"] > out["keys"] * 100, out
    assert out["mismatches"] == [], out["mismatches"][:20]


@needs_node
def test_typed_chords_notes_and_power_chords_are_labelled_as_the_page_shows_them():
    by = {r["input"]: r for r in _voice(["Ab7", "Db7", "Bbm", "Cbmaj7"], key="C# minor")}
    assert (by["Ab7"]["name"], by["Ab7"]["number"]) == ("G#7", "5^7"), by["Ab7"]  # beside 5^7 the page writes G#7
    assert by["Db7"]["name"] == "C#7" and by["Bbm"]["name"] == "A#m" and by["Cbmaj7"]["name"] == "Bmaj7", by
    assert _voice(["Db7"], key="E major")[0]["name"] == "C#7" and _voice(["Fb"], key="Eb major")[0]["name"] == "E"
    assert _voice(["Cbmaj7"])[0]["name"] == "Cbmaj7"  # no key: Claude's own spelling stays
    notes = _voice(["Db4 F4", "C4"], key="A major") + _voice(["C4"], key="C# minor")
    assert [r["name"] for r in notes] == ["C#-E#", "C4", "B#3"], notes  # (every interval: the spellForKey sweep test)
    for r in _voice(["C5", "G5", "F#5", "5^5"], key="C major"):
        assert not r.get("error") and r["warnings"] == [] and r["roundtrip"]["match"] == "exact", r
    shell = {r["input"]: r for r in _voice(["C7#11", "C7b9", "C9sus4", "Cmaj7"], voicing="shell")}
    assert any("reads this shell voicing as C7b5" in w and "close" in w for w in shell["C7#11"]["warnings"]), shell
    assert any("not C7b9" in w for w in shell["C7b9"]["warnings"]) and any("not C9sus4" in w for w in shell["C9sus4"]["warnings"])
    assert not any("reads this" in w for w in shell["Cmaj7"]["warnings"]), shell["Cmaj7"]
    assert "an octave lower" in pianocue.build_parser()._subparsers._group_actions[0].choices["play"].format_help()


# ------------------------------------------------------------------------------------------------- CLI
def _run(argv, capsys):
    out = io.StringIO()
    code = pianocue.main(argv, out=out)
    return code, out.getvalue(), capsys.readouterr().err


@needs_node
def test_play_hover_clear_and_status(server, capsys):
    port = str(server.port)
    listener = SSE(server.port)
    try:
        code, out, _ = _run(["play", "Dbmaj9", "--key", "Eb major", "--voicing", "spread", "--port", port,
                             "--arp", "40", "--hold", "1.5", "--vel", "90"], capsys)
        assert code == 0 and "sent cue #1 to 1 listener" in out and "b7maj9" in out
        cue = listener.cue()["cue"]
        expected = _voice(["Dbmaj9"], key="Eb major", voicing="spread")[0]["notes"]
        assert cue == {"type": "play", "notes": expected, "velocity": 90, "hold_ms": 1500, "arpeggio_ms": 40,
                       "sound": True, "label": "Dbmaj9", "detail": "b7maj9 in Eb major", "source": "claude"}

        assert _run(["play", "C4", "E4", "G4", "--silent", "--label", "C, quietly", "--port", port], capsys)[0] == 0
        cue = listener.cue()["cue"]
        assert cue["notes"] == [60, 64, 67] and cue["sound"] is False and cue["label"] == "C, quietly"

        assert _run(["hover", "4maj9#11", "--key", "Eb major", "--port", port], capsys)[0] == 0
        cue = listener.cue()["cue"]
        assert cue["type"] == "hover" and cue["sound"] is False and cue["label"] == "Abmaj9#11"

        assert _run(["clear", "--port", port], capsys)[0] == 0
        assert listener.cue()["cue"]["type"] == "clear"

        code, out, _ = _run(["status", "--port", port], capsys)
        assert code == 0 and "listeners 1, last cue id 4" in out
    finally:
        listener.close()


@needs_node
def test_details_carry_the_typed_number_and_what_explicit_notes_read_as(server, capsys):
    port = str(server.port)
    listener = SSE(server.port)
    try:
        assert _run(["play", "#4", "--key", "Eb major", "--port", port], capsys)[0] == 0
        cue = listener.cue()["cue"]
        assert (cue["label"], cue["detail"]) == ("A", "#4 in Eb major")  # the page numbers it b5; the typed number stays

        code, out, _ = _run(["hover", "57", "--key", "Eb major", "--port", port], capsys)
        assert code == 0 and "read as the MIDI note A3" in out
        assert listener.cue()["cue"]["notes"] == [57]

        notes = "Ab2 C4 Eb4 G4 Bb4 D5"
        r = _voice([notes], key="Eb major")[0]
        assert r["kind"] == "notes" and r["number"]
        assert _run(["play", *notes.split(), "--label", "Abmaj9#11", "--key", "Eb major", "--port", port], capsys)[0] == 0
        cue = listener.cue()["cue"]
        assert cue["label"] == "Abmaj9#11" and cue["detail"] == f"{r['name']} · {r['number']} in Eb major", cue
        assert _run(["play", *notes.split(), "--key", "Eb major", "--port", port], capsys)[0] == 0
        cue = listener.cue()["cue"]
        assert (cue["label"], cue["detail"]) == (r["name"], f"{r['number']} in Eb major")
        assert _run(["play", "C4", "E4", "G4", "--label", "a C", "--port", port], capsys)[0] == 0
        assert listener.cue()["cue"]["detail"] == "C"  # no key: the reading alone
        assert _run(["play", "C4", "E4", "G4", "--label", "a C", "--detail", "mine", "--port", port], capsys)[0] == 0
        assert listener.cue()["cue"]["detail"] == "mine"

        assert _run(["play", "Bb-7", "--port", port], capsys)[0] == 0
        assert listener.cue()["cue"]["label"] == "Bbm7"
    finally:
        listener.close()


def test_split_progression_splits_chords_inside_a_bar_and_keeps_notes_grouped():
    sp = pianocue.split_progression
    assert sp("Abmaj9#11 Bb7sus4/Eb | Ebmaj9") == ["Abmaj9#11", "Bb7sus4/Eb", "Ebmaj9"]
    assert sp("Abmaj9#11 | Bb7sus4/Eb | Ebmaj9") == ["Abmaj9#11", "Bb7sus4/Eb", "Ebmaj9"]
    assert sp("4maj9#11:2 5^7sus4/1:2 | 1") == ["4maj9#11:2", "5^7sus4/1:2", "1"]
    assert sp("1 4 | 5 1") == ["1", "4", "5", "1"] and sp("1 4 5 1") == ["1", "4", "5", "1"]
    assert sp("Ab2 Eb3 G3 | Bb2 F3 Ab3") == ["Ab2 Eb3 G3", "Bb2 F3 Ab3"]  # notes with octaves: one chord each
    assert sp("57 60 64 | 1") == ["57 60 64", "1"] and sp("Ab2 Eb3 G3:2 | C") == ["Ab2 Eb3 G3:2", "C"]
    # a chord name that also looks like a note with an octave (C7, G7, E7, A7, Ab7) reads as the chord it names
    assert sp("Dm7 G7 | Cmaj7") == ["Dm7", "G7", "Cmaj7"] and sp("C7 F7 | Bb7") == ["C7", "F7", "Bb7"]
    assert sp("E7 A7 | D") == ["E7", "A7", "D"] and sp("Cmaj7 | G7 C") == ["Cmaj7", "G7", "C"]
    assert sp("Ab7 Db7 | Gb") == ["Ab7", "Db7", "Gb"] and sp("Dm7 G7:2 | C6/9") == ["Dm7", "G7:2", "C6/9"]
    assert sp("Bb-7 Eb7 | Abmaj7") == ["Bb-7", "Eb7", "Abmaj7"] and sp("C/E G7/D | C") == ["C/E", "G7/D", "C"]
    assert sp("E13 A13 | D9") == ["E13", "A13", "D9"] and sp("F#m7b5 B7b9 | Em") == ["F#m7b5", "B7b9", "Em"]
    # a bar with one note that is not also a chord is notes; a voicing all in octave 5 or 6 stays notes
    assert sp("Ab2 Eb3 G3 | Bb2 F3 Ab3:2") == ["Ab2 Eb3 G3", "Bb2 F3 Ab3:2"] and sp("G7 C4 | C") == ["G7 C4", "C"]
    assert sp("C5 E5 G5 | D5 F5 A5") == ["C5 E5 G5", "D5 F5 A5"] and sp("C4 E4 G4 | C") == ["C4 E4 G4", "C"]
    assert sp("C6 E6 G6 | 84 88 91") == ["C6 E6 G6", "84 88 91"] and sp("C5 G7 | F") == ["C5", "G7", "F"]
    # the help's own examples read as the chords they name
    ap = pianocue.build_parser()
    pg = ap._subparsers._group_actions[0].choices["progression"]
    text = " ".join((ap.format_help() + pg.format_help()).split())
    examples = re.findall(r'"([^"]*\|[^"]*)"', text)
    assert {ex: len(sp(ex)) for ex in examples} == {"Abmaj9#11 | Bb7sus4/Eb | Ebmaj9": 3, "4maj9#11 | 5^7sus4/1:2 | 1": 3,
                                                     "1 4 | 5 1": 4, "Dm7 G7 | Cmaj7": 3,
                                                     "Ab2 Eb3 G3 | Bb2 F3 Ab3": 2}, examples


@needs_node
def test_progression_bars_of_chords_that_look_like_notes_voice_as_those_chords(server, capsys):
    listener = SSE(server.port)
    try:
        for text, labels in (("Dm7 G7 | Cmaj7", ["Dm7", "G7", "Cmaj7"]), ("C7 F7 | Bb7", ["C7", "F7", "Bb7"]),
                             ("E7 A7 | D", ["E7", "A7", "D"]), ("Cmaj7 | G7 C", ["Cmaj7", "G7", "C"])):
            code, out, err = _run(["progression", text, "--bpm", "120", "--beats", "2", "--port", str(server.port)], capsys)
            assert code == 0 and "cannot" not in err, (text, out, err)
            assert [s["label"] for s in listener.cue()["cue"]["steps"]] == labels, text
        code, out, err = _run(["progression", "Ab2 Eb3 G3 | Bb2 F3 Ab3", "--port", str(server.port)], capsys)
        assert code == 0 and [s["notes"] for s in listener.cue()["cue"]["steps"]] == [[44, 51, 55], [46, 53, 56]], err
    finally:
        listener.close()


@needs_node
def test_play_and_hover_several_chords_go_one_after_another(server, capsys):
    port = str(server.port)
    listener = SSE(server.port)
    try:
        for argv in (["F#m7b5 Bbmaj7#11"], ["F#m7b5", "Bbmaj7#11"]):  # one quoted argument, or two
            code, out, err = _run(["hover", *argv, "--port", port], capsys)
            assert code == 0 and "2 chords one after another, 2.5 s each" in out, (out, err)
            cue = listener.cue()["cue"]
            assert cue["type"] == "sequence" and cue["label"] == "F#m7b5 | Bbmaj7#11", cue
            assert [(s["at_ms"], s["hold_ms"], s["type"], s["label"]) for s in cue["steps"]] == [
                (0, 2500, "hover", "F#m7b5"), (2500, 2500, "hover", "Bbmaj7#11")]  # a hover holds to the next: no blink
            assert cue["steps"][0]["notes"] == _voice(["F#m7b5"], voicing="spread")[0]["notes"]

        code, out, err = _run(["play", "Dm7", "G7", "Cmaj7", "--hold", "2", "--vel", "50", "--key", "C major", "--port", port],
                              capsys)
        assert code == 0, (out, err)
        cue = listener.cue()["cue"]
        assert cue["type"] == "sequence" and cue["sound"] is True and cue["detail"] == "in C major"
        assert [(s["at_ms"], s["hold_ms"], s["type"], s["velocity"], s["detail"]) for s in cue["steps"]] == [
            (0, 1960, "play", 50, "2m7 in C major"), (2000, 1960, "play", 50, "5^7 in C major"),
            (4000, 1960, "play", 50, "1maj7 in C major")]

        code, out, err = _run(["hover", "F#m7b5", "Bbmaj7#11", "--hold", "0", "--port", port], capsys)
        assert code == 2 and "each needs a length" in err and 'progression "F#m7b5 | Bbmaj7#11" --hover' in err, err

        # notes stay one chord: a voicing, MIDI numbers, notes in octave 5
        for argv, notes in ((["Ab3", "Eb4", "G4"], [56, 63, 67]), (["60 64 67"], [60, 64, 67]), (["C5", "E5", "G5"], [72, 76, 79])):
            assert _run(["hover", *argv, "--port", port], capsys)[0] == 0
            cue = listener.cue()["cue"]
            assert cue["type"] == "hover" and cue["notes"] == notes, (argv, cue)
    finally:
        listener.close()


@needs_node
def test_progression_timing_and_hover(server, capsys):
    listener = SSE(server.port)
    try:
        code, out, _ = _run(["progression", "Ebmaj9 | Abmaj9#11:2 | 5^7sus4/1", "--key", "Eb major", "--bpm", "60",
                             "--beats", "4", "--hover", "--voice-lead", "--port", str(server.port)], capsys)
        assert code == 0, out
        cue = listener.cue()["cue"]
        assert cue["type"] == "sequence" and cue["label"] == "Ebmaj9 | Abmaj9#11 | Bb7sus4/Eb"
        assert [(s["at_ms"], s["hold_ms"], s["type"]) for s in cue["steps"]] == [
            (0, 4000, "hover"), (4000, 2000, "hover"), (6000, 4000, "hover")]  # hovers hold to the next: no blink
        assert [s["detail"] for s in cue["steps"]] == ["1maj9 in Eb major", "4maj9#11 in Eb major",
                                                        "5^7sus4/1 in Eb major"]

        code, out, _ = _run(["progression", "1 4 5 1", "--key", "Eb major", "--bpm", "90", "--port",
                             str(server.port)], capsys)
        assert code == 0, out
        cue = listener.cue()["cue"]
        assert [s["label"] for s in cue["steps"]] == ["Eb", "Ab", "Bb", "Eb"]
        assert [(s["at_ms"], s["hold_ms"], s["type"]) for s in cue["steps"]] == [
            (0, 2627, "play"), (2667, 2626, "play"), (5333, 2627, "play"), (8000, 2627, "play")]  # 2666.7 ms rounded
    finally:
        listener.close()


@needs_node
def test_a_non_ascii_label_through_a_pipe_does_not_crash_after_sending(server):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    proc = subprocess.run([sys.executable, "-m", "arsenal.pianocue", "play", "C4", "E4", "G4", "--label",
                           "D♭maj9 · the ♭7", "--detail", "4maj9♯11 — the Lydian 4", "--port", str(server.port)],
                          capture_output=True, cwd=str(ROOT), env=env, timeout=120)
    out, err = proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")
    assert proc.returncode == 3, (out, err)  # nobody listening: the check after the print still runs
    assert "sent cue #1 to 0 listeners" in out and "D♭maj9 · the ♭7" in out and "no piano page is listening" in err
    assert "Traceback" not in err


@needs_node
def test_nobody_listening_exits_non_zero_with_the_page_url(server, capsys):
    code, out, err = _run(["play", "Cmaj7", "--port", str(server.port)], capsys)
    assert code == 3 and f"no piano page is listening - open http://127.0.0.1:{server.port}/piano" in err


def test_replay_verb_on_a_synthetic_session(server, tmp_path, capsys):
    store = PerformanceStore(tmp_path / "sessions")
    session = store.open()
    store.append(session, _session_events())
    listener = SSE(server.port)
    try:
        code, out, _ = _run(["replay", "latest", "0:01.4", "--seconds", "4", "--root", str(tmp_path / "sessions"),
                             "--port", str(server.port)], capsys)
        assert code == 0, out
        cue = listener.cue()["cue"]
        assert cue["source"] == "replay" and cue["label"] == "you, at 0:01.4" and len(cue["steps"]) == 3
        assert session in cue["detail"]
    finally:
        listener.close()
    assert _run(["replay", session, "9:00", "--root", str(tmp_path / "sessions"), "--port", str(server.port)],
                capsys)[0] == 2


def test_no_server_and_an_old_server(capsys):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
    code, _, err = _run(["clear", "--port", str(free)], capsys)
    assert code == 4 and "no arsenal server answers" in err

    class Old(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = json.dumps({"error": "no route for POST /api/piano/cue"}).encode()
            self.send_response(404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    old = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Old)
    threading.Thread(target=old.serve_forever, daemon=True).start()
    try:
        code, _, err = _run(["clear", "--port", str(old.server_address[1])], capsys)
        assert code == 4 and "has no piano cue channel" in err and "restart" in err
    finally:
        old.shutdown()
        old.server_close()
