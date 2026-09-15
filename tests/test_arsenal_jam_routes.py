"""J3, the routes half (jam-spec 5, 6): conflicts, the owner lease, pending and launch, the landing rule, swaps, passes
and the server-restart close, exercised over HTTP against a server on a free port.

The resolver here hands back the J0 fixture defs, so these tests need no node; tests/test_arsenal_jam_store.py
covers resolving. Every clock value is synthetic (2030)."""
import copy
import http.client
import json
import random
import socket
import sys
import threading
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.jam import runs as RUNS  # noqa: E402
from arsenal.jam import schemas as S  # noqa: E402
from arsenal.jam.runs import JamApi, LEASE_MS, PENDING_EXPIRE_MS  # noqa: E402
from arsenal.pianocue import CueHub  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "jam"
T0 = 1893456000000
BAR_66 = Fraction(4 * 60000, 66)


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class Epoch:
    def __init__(self):
        self.t = float(T0)

    def __call__(self):
        return self.t


class FixtureResolver:
    """Defs from tests/fixtures/jam: a card in a minor key gets the Dorian vamp, anything else the Lydian 4."""

    def __init__(self):
        self.calls = []

    def resolve(self, card, key=None, variant=None, backing=None, voicing=None, slot=None):
        self.calls.append(("card", card["id"], key, variant))
        d = load("def_dorian_vamp.json" if card["key"].endswith("minor") else "def_lydian_four.json")
        d["card"] = {"id": card["id"], "rev": card.get("rev") or 1, "title": card["title"],
                     "variant": variant if variant not in (None, "all") else None}
        return d

    def resolve_chords(self, items, key, meter=4, backing="comp", voicing="spread", slot=None, title=None):
        self.calls.append(("chords", key))
        d = load("def_lydian_four.json")
        d["card"] = None
        d.pop("landing", None)
        return d

    def page_reads(self, card):
        return []


@pytest.fixture()
def jam(tmp_path):
    app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    epoch = Epoch()
    app.cues = CueHub(heartbeat_s=0.3, id_base=0)
    app.jam = JamApi(root=tmp_path / "jam", performance=app.performance, hub=lambda: app.cues,
                     resolver=FixtureResolver(), now_ms=epoch)
    srv = Server(0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield SimpleNamespace(port=srv.server_address[1], app=app, epoch=epoch, root=tmp_path / "jam", tmp=tmp_path)
    app.cues.close()
    srv.shutdown()
    srv.server_close()


def call(jam, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", jam.port, timeout=10)
    raw = body if isinstance(body, bytes) else (json.dumps(body).encode("utf-8") if body is not None else None)
    conn.request(method, path, body=raw, headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, json.loads(data or b"null")


def post(jam, path, body):
    return call(jam, "POST", path, body)


def get(jam, path):
    return call(jam, "GET", path)


def add_card(jam, name="card_lydian_four.json", **changes):
    c = load(name)
    c.update(changes)
    status, reply = post(jam, "/api/piano/deck/cards", {"card": c, "by": "claude"})
    assert status == 200, reply
    return reply


class Stream:
    """A raw event-stream client that reads named events."""

    def __init__(self, port, query=""):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.sock.sendall(f"GET /api/piano/cues{query} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode("ascii"))
        self.buf = b""
        self._until(b"\r\n\r\n")
        self.block()

    def _until(self, sep):
        while sep not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError
            self.buf += chunk
        part, self.buf = self.buf.split(sep, 1)
        return part

    def block(self):
        return self._until(b"\n\n").decode("utf-8")

    def event(self):
        while True:
            text = self.block()
            if text.startswith(":"):
                continue
            fields = dict(line.split(": ", 1) for line in text.split("\n"))
            data = json.loads(fields["data"])
            assert int(fields["id"]) == data["id"]
            return fields["event"], data

    def close(self):
        self.sock.close()


# ============================================================================================ deck
def test_deck_writes_answer_409_when_the_card_moved_underneath(jam):
    assert add_card(jam)["rev"] == 1
    assert post(jam, "/api/piano/deck/cards", {"card": load("card_lydian_four.json"), "by": "claude"}) == \
        (409, {"error": "card lydian-four exists", "rev": 1})
    status, reply = post(jam, "/api/piano/deck/cards/lydian-four/update", {"patch": {"title": "Lydian"}, "if_rev": 1,
                                                                            "by": "daniel"})
    assert status == 200 and reply["rev"] == 2 and reply["card"]["updated_by"] == "daniel"
    for path, body in (("/api/piano/deck/cards/lydian-four/update", {"patch": {"title": "x"}, "if_rev": 1}),
                       ("/api/piano/deck/cards/lydian-four/delete", {"if_rev": 1})):
        status, reply = post(jam, path, body)
        assert status == 409 and reply["rev"] == 2
    status, reply = post(jam, "/api/piano/deck/order", {"order": ["lydian-four"], "if_rev": 1})
    assert status == 409 and reply["rev"] == 2
    bad = load("card_lydian_four.json")
    bad.update(id="bad-card", chords=[{"n": "1maj9", "beats": 0}])
    status, reply = post(jam, "/api/piano/deck/cards", {"card": bad})
    assert status == 400 and reply["field"] == "chords[0].beats"
    assert post(jam, "/api/piano/deck/cards", {"card": bad, "colour": "blue"})[1]["field"] == "colour"
    assert post(jam, "/api/piano/deck/cards", {"card": bad, "by": "vandor"})[1]["field"] == "by"
    assert get(jam, "/api/piano/deck/cards/nope")[0] == 404
    status, doc = get(jam, "/api/piano/deck")
    assert status == 200 and doc["rev"] == 2 and [c["id"] for c in doc["cards"]] == ["lydian-four"]
    assert doc["cards"][0]["numbers"] == "1maj9 4maj7#11" and doc["cards"][0]["runs"] == 0
    status, reply = post(jam, "/api/piano/deck/cards/lydian-four/delete", {"if_rev": 2, "by": "daniel"})
    assert status == 200 and reply["trashed"].startswith("trash/lydian-four.rev2.")
    assert get(jam, "/api/piano/deck/trash")[1]["trash"][0]["id"] == "lydian-four"
    assert post(jam, "/api/piano/deck/cards/lydian-four/restore", {"by": "daniel"})[1]["rev"] == 3


def test_deck_and_jam_frames_ride_the_cue_stream_and_status_counts_jam_pages(jam):
    page = Stream(jam.port, "?caps=jam1,deck1&page=p-a")
    try:
        status, st = get(jam, "/api/piano/cues/status")
        assert st["caps"] == {"jam1": 1, "deck1": 1} and st["pages"][0]["page_id"] == "p-a"
        add_card(jam)
        kind, data = page.event()
        assert kind == "deck" and data["id"] == 1 and set(data) == {"id", "deck", "sent_at"}
        assert data["deck"]["op"] == "upsert" and data["deck"]["card_id"] == "lydian-four"
        assert data["deck"]["rev"] == 1 and data["deck"]["deck_rev"] == 1 and data["deck"]["summary"]["title"]
        assert post(jam, "/api/piano/cue", {"cue": {"type": "clear"}}) == (200, {"id": 2, "listeners": 1})
        assert page.event()[0] == "cue"
        status, reply = post(jam, "/api/piano/deck/open", {"card_id": "lyd", "by": "claude"})
        assert (status, reply) == (200, {"id": "lydian-four", "listeners": 1})
        kind, data = page.event()
        assert kind == "deck" and data["deck"]["op"] == "open"
        status, reply = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel",
                                                           "page_id": "p-a"})
        assert status == 200 and reply["jam_pages"] == 1 and reply["listeners"] == 1
        kinds = [page.event() for _ in range(2)]
        assert [(k, d["jam"]["op"]) for k, d in kinds] == [("jam", "owner"), ("jam", "start")]
        start = kinds[1][1]["jam"]
        assert start["run"] == reply["run"] and start["state"] == "running" and start["version"] == 1
        assert start["def"]["api"] == "arsenal.jam.def/v0" and start["segments"][0]["from_bar"] == -1
    finally:
        page.close()


# ============================================================================================ pending, launch, owner
def test_a_claude_start_waits_pending_until_the_owner_launches(jam):
    add_card(jam)
    assert post(jam, "/api/piano/jam/owner", {"page_id": "p-a", "claim": True})[1]["owner"]["page_id"] == "p-a"
    status, reply = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "claude"})
    assert status == 200 and reply["state"] == "pending" and reply["start_epoch_ms"] is None and reply["def"]
    rid = reply["run"]
    st = get(jam, "/api/piano/jam")[1]
    assert st["run"]["run"] == rid and st["run"]["segments"] == [] and st["position"] is None
    assert st["def"]["card"]["id"] == "lydian-four"
    jam.epoch.t += 3000
    launch = f"/api/piano/jam/runs/{rid}/launch"
    assert post(jam, launch, {"page_id": "p-b", "epoch_ms": jam.epoch.t + 500}) == \
        (409, {"error": "only the owner page launches a run", "owner": "p-a"})
    status, reply = post(jam, launch, {"page_id": "p-a", "epoch_ms": jam.epoch.t + 100})
    assert status == 400 and reply["field"] == "epoch_ms"
    status, reply = post(jam, launch, {"page_id": "p-a", "epoch_ms": jam.epoch.t + 500, "via": "rest"})
    assert status == 200 and reply["start_epoch_ms"] == T0 + 3500
    assert reply["bar0_epoch_ms"] == pytest.approx(float(T0 + 3500 + BAR_66), abs=1e-6)
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    S.validate_run(run["run"])
    assert run["run"]["state"] == "running" and run["run"]["courtesy"] == {"held_ms": 3000.0, "via": "rest"}
    assert [e["kind"] for e in run["events"]] == ["start", "launch"]
    assert post(jam, launch, {"page_id": "p-a", "epoch_ms": jam.epoch.t + 900})[0] == 409


def test_now_and_the_page_start_at_once_and_a_new_start_replaces_a_pending_one(jam):
    add_card(jam)
    pending = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "claude"})[1]["run"]
    reply = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "claude",
                                               "now": True})[1]
    assert reply["state"] == "running" and reply["start_epoch_ms"] == T0 + 800
    old = get(jam, f"/api/piano/jam/runs/{pending}")[1]["run"]
    assert old["stop_reason"] == "replaced" and old["stopped_epoch_ms"] == T0
    play = post(jam, "/api/piano/jam/start", {"mode": "play", "card_id": "lydian-four", "by": "daniel"})[1]
    assert play["start_epoch_ms"] == T0 + 250 and play["count_in_bars"] == 0
    st = get(jam, "/api/piano/jam")[1]
    assert st["run"]["run"] == reply["run"] and st["play"]["run"] == play["run"]
    for body, field in (({"mode": "play", "card_id": "lydian-four", "count_in": 1}, "count_in"),
                        ({"mode": "loop", "card_id": "lydian-four", "try_backing": "bass"}, "try_backing"),
                        ({"mode": "jam", "card_id": "lydian-four"}, "mode"),
                        ({"mode": "loop", "chords": "1maj9:4"}, "key"),
                        ({"mode": "loop", "card_id": "lydian-four", "bpm": 400}, "bpm")):
        status, err = post(jam, "/api/piano/jam/start", body)
        assert (status, err.get("field")) == (400, field), err


def test_the_owner_lease_claims_win_expire_and_release(jam):
    frames = []
    page = Stream(jam.port, "?caps=jam1&page=p-a")
    try:
        assert post(jam, "/api/piano/jam/owner", {"page_id": "p-a"})[1]["owner"]["page_id"] == "p-a"
        assert post(jam, "/api/piano/jam/owner", {"page_id": "p-b", "claim": True})[1]["owner"]["page_id"] == "p-b"
        frames = [page.event()[1]["jam"] for _ in range(2)]
    finally:
        page.close()
    assert [(f["op"], f["owner"]) for f in frames] == [("owner", "p-a"), ("owner", "p-b")]
    assert post(jam, "/api/piano/jam/owner", {"page_id": "p-a", "claim": False})[1]["owner"]["page_id"] == "p-b"
    jam.epoch.t += LEASE_MS + 1
    assert get(jam, "/api/piano/jam")[1]["owner"] is None
    post(jam, "/api/piano/jam/owner", {"page_id": "p-a"})
    assert post(jam, "/api/piano/jam/owner", {"page_id": "p-a", "claim": False})[1]["owner"] is None
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "now": True})[1]["run"]
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    ack = {"page_id": "p-c", "role": "viewer", "version": 1, "bar": 0, "bar_epoch_ms": run["bar0_epoch_ms"],
           "perf_ms": 1000.0, "perf_offset_ms": jam.epoch.t - 1000}
    assert post(jam, f"/api/piano/jam/runs/{rid}/ack", ack) == (200, {"ok": True, "duplicate": False})
    assert get(jam, "/api/piano/jam")[1]["owner"]["page_id"] == "p-c"
    assert get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]["owner_page_id"] == "p-c"
    assert post(jam, "/api/piano/jam/owner", {"page_id": "not a page!"})[0] == 400


# ============================================================================================ the landing rule
def _segment_at(segs, bar):
    chosen = segs[0]
    for s in segs:
        if s["from_bar"] <= bar:
            chosen = s
    return chosen


def _t(segs, bar, m=4):
    s = _segment_at(segs, bar)
    return Fraction(s["epoch_ms"]) + (bar - s["from_bar"]) * Fraction(m * 60000) / Fraction(s["bpm"])


def _landing(segs, received, at="bar", cycle_bars=None, m=4, lead=250):
    """Independent exact arithmetic: the first bar line (or pass top) at least 1 beat + lead after received."""
    s = segs[0]
    for x in segs:
        if Fraction(x["epoch_ms"]) <= Fraction(received):
            s = x
    need = Fraction(60000) / Fraction(s["bpm"]) + lead
    beats = (Fraction(received) - Fraction(s["epoch_ms"])) * Fraction(s["bpm"]) / 60000
    bar = s["from_bar"] + (beats // m)
    while True:
        if _t(segs, bar, m) - Fraction(received) >= need and \
                (cycle_bars is None or (bar - _segment_at(segs, bar)["def_from_bar"]) % cycle_bars == 0):
            return int(bar), _t(segs, bar, m)
        bar += 1


def test_changes_land_on_the_first_line_one_beat_and_250_ms_away(jam):
    """A3's server half: 30 tempo changes at random moments each land on the first bar line at least 1 beat + 250 ms
    after the server received them, computed here with exact fractions."""
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]["run"]
    control = f"/api/piano/jam/runs/{rid}/control"
    rng = random.Random(90210)
    moments = sorted(rng.uniform(1000, 150000) for _ in range(30))
    for i, offset in enumerate(moments):
        received = T0 + 250 + round(offset, 3)
        segs = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]["segments"]
        want_bar, want_epoch = _landing(segs, received)
        jam.epoch.t = received
        bpm = rng.choice([60, 66, 72, 80, 96])
        status, reply = post(jam, control, {"op": "tempo", "bpm": bpm, "at": "bar", "if_version": i + 1})
        assert status == 200, reply
        assert reply["effective_bar"] == want_bar, (i, reply, want_bar)
        assert abs(reply["epoch_ms"] - float(want_epoch)) <= 0.001 and reply["version"] == i + 2
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    S.validate_run(run["run"])
    status, reply = post(jam, control, {"op": "tempo", "bpm": 90, "if_version": 1})
    assert status == 409 and reply["version"] == 31
    jam.epoch.t += 777
    segs = run["run"]["segments"]
    s = _segment_at(segs, 10 ** 6)
    status, reply = post(jam, control, {"op": "tempo", "bpm": "+4", "at": "beat"})
    assert status == 200 and reply["bpm"] == s["bpm"] + 4 and reply["at"] == "bar" and "bar lines" in reply["note"]
    assert post(jam, control, {"op": "tempo", "bpm": 300})[1]["field"] == "bpm"
    assert post(jam, control, {"op": "fly"})[1]["field"] == "op"
    jam.epoch.t += 5000
    segs = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]["segments"]
    want_bar, want_epoch = _landing(segs, jam.epoch.t, cycle_bars=2)
    status, reply = post(jam, control, {"op": "next", "key": "F major"})
    assert status == 200 and reply["at"] == "pass" and reply["effective_bar"] == want_bar
    assert jam.app.jam.resolver.calls[-1] == ("card", "lydian-four", "F major", None)
    jam.epoch.t += 20000
    segs = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]["segments"]
    want_bar, want_epoch = _landing(segs, jam.epoch.t)
    status, reply = post(jam, control, {"op": "stop"})
    assert status == 200 and reply["effective_bar"] == want_bar and abs(reply["epoch_ms"] - float(want_epoch)) <= 0.001
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    assert run["stop_reason"] == "cli" and run["stop_bar"] == want_bar
    assert post(jam, control, {"op": "stop"})[0] == 409


def test_stop_now_mute_and_set_on_a_running_loop(jam):
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]["run"]
    control = f"/api/piano/jam/runs/{rid}/control"
    jam.epoch.t += 9000
    status, reply = post(jam, control, {"op": "mute", "by": "daniel"})
    assert status == 200 and reply["epoch_ms"] == jam.epoch.t and reply["at"] == "now"
    status, reply = post(jam, control, {"op": "set", "settings": {"groove": "pulse", "walk": 0}})
    assert status == 200
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    assert run["settings"][-1]["groove"] == "pulse" and run["settings"][-1]["walk"] == 0
    assert run["settings"][-1]["muted"] is True and run["settings"][-1]["from_bar"] == reply["effective_bar"]
    assert post(jam, control, {"op": "set", "settings": {"colour": "blue"}})[1]["field"] == "settings.colour"
    assert post(jam, control, {"op": "set", "settings": {"try_backing": "bass"}})[0] == 400
    jam.epoch.t += 1234
    status, reply = post(jam, control, {"op": "stop", "at": "now", "by": "daniel"})
    assert status == 200 and reply["epoch_ms"] == jam.epoch.t
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    assert run["stop_reason"] == "page" and run["stopped_epoch_ms"] == jam.epoch.t


def test_a_second_loop_swaps_on_the_next_bar_and_a_play_overlays(jam):
    add_card(jam)
    add_card(jam, id="dorian-vamp", key="D minor", title="Two-chord Dorian vamp", landing=None,
             checks=[], chords=[{"n": "1m11", "beats": 4}, {"n": "4^13", "beats": 4}], also_in=[])
    first = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]
    jam.epoch.t += 10000
    old_segs = get(jam, f"/api/piano/jam/runs/{first['run']}")[1]["run"]["segments"]
    want_bar, want_epoch = _landing(old_segs, jam.epoch.t)
    while _t(old_segs, want_bar) < Fraction(jam.epoch.t + 250):
        want_bar += 1
    second = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "dorian-vamp", "by": "daniel"})[1]
    assert second["swapped_from"] == first["run"] and second["count_in_bars"] == 0
    assert abs(second["start_epoch_ms"] - float(_t(old_segs, want_bar))) <= 0.001
    assert second["start_epoch_ms"] == second["bar0_epoch_ms"]
    old = get(jam, f"/api/piano/jam/runs/{first['run']}")[1]["run"]
    assert old["stop_reason"] == "replaced" and old["stop_bar"] == want_bar
    assert old["stopped_epoch_ms"] == second["start_epoch_ms"]
    new = get(jam, f"/api/piano/jam/runs/{second['run']}")[1]["run"]
    S.validate_run(new)
    assert new["segments"][0]["from_bar"] == 0 and new["card"]["id"] == "dorian-vamp"
    play = post(jam, "/api/piano/jam/start", {"mode": "play", "card_id": "lydian-four", "by": "daniel"})[1]
    st = get(jam, "/api/piano/jam")[1]
    assert st["run"]["run"] == second["run"] and st["play"]["run"] == play["run"]
    assert get(jam, f"/api/piano/jam/runs/{second['run']}")[1]["run"]["state"] == "running"


def test_a_knock_beside_a_playing_loop_leaves_it_playing_until_the_launch_swaps_it(jam):
    """Round-1 verify: a pending start used to stop the running loop at once with no bar, and the page kept handing
    its bars forever. Now the loop plays on while the knock waits, and the launch swaps it on a bar line."""
    add_card(jam)
    add_card(jam, id="dorian-vamp", key="D minor", title="Two-chord Dorian vamp", landing=None,
             checks=[], chords=[{"n": "1m11", "beats": 4}, {"n": "4^13", "beats": 4}], also_in=[])
    post(jam, "/api/piano/jam/owner", {"page_id": "p-a", "claim": True})
    first = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel",
                                               "page_id": "p-a"})[1]
    jam.epoch.t += 10000
    older = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "dorian-vamp", "by": "claude"})[1]
    knock = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "dorian-vamp", "by": "claude"})[1]
    assert older["state"] == knock["state"] == "pending"
    run = get(jam, f"/api/piano/jam/runs/{first['run']}")[1]["run"]
    assert run["state"] == "running" and not run["closed"]
    replaced = get(jam, f"/api/piano/jam/runs/{older['run']}")[1]["run"]
    assert replaced["stop_reason"] == "replaced" and replaced["stop_bar"] is None
    st = get(jam, "/api/piano/jam")[1]
    assert st["run"]["run"] == first["run"] and [r["run"] for r in st["pending"]] == [knock["run"]]
    jam.epoch.t += 3000
    old_segs = run["segments"]
    epoch = jam.epoch.t + 500
    want_bar, _ = _landing(old_segs, jam.epoch.t)
    while _t(old_segs, want_bar) < Fraction(epoch):
        want_bar += 1
    status, reply = post(jam, f"/api/piano/jam/runs/{knock['run']}/launch", {"page_id": "p-a", "epoch_ms": epoch})
    assert status == 200 and reply["count_in_bars"] == 0
    assert abs(reply["start_epoch_ms"] - float(_t(old_segs, want_bar))) <= 0.001
    old = get(jam, f"/api/piano/jam/runs/{first['run']}")[1]["run"]
    assert old["stop_reason"] == "replaced" and old["stop_bar"] == want_bar
    assert old["stopped_epoch_ms"] == reply["start_epoch_ms"]
    S.validate_run(old)
    assert get(jam, "/api/piano/jam")[1]["pending"] == []
    # a play replaced by a newer play stops on the bar sounding now, never with no bar
    p1 = post(jam, "/api/piano/jam/start", {"mode": "play", "card_id": "lydian-four", "by": "daniel"})[1]
    jam.epoch.t += 2000
    post(jam, "/api/piano/jam/start", {"mode": "play", "card_id": "lydian-four", "by": "daniel"})
    gone = get(jam, f"/api/piano/jam/runs/{p1['run']}")[1]["run"]
    assert gone["stop_reason"] == "replaced" and isinstance(gone["stop_bar"], int)


def test_a_change_may_land_before_one_already_waiting_later(jam):
    """Round-1 verify: a key change waiting for the pass top made a later tempo, next or set change landing earlier
    answer 500 (TempoMapError), and a set merged into a later entry replied with a bar it did not use."""
    add_card(jam)
    add_card(jam, id="dorian-vamp", key="D minor", title="Two-chord Dorian vamp", landing=None,
             checks=[], chords=[{"n": "1m11", "beats": 4}, {"n": "4^13", "beats": 4}], also_in=[])
    start = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]
    rid, control = start["run"], f"/api/piano/jam/runs/{start['run']}/control"
    jam.epoch.t = start["bar0_epoch_ms"] + 100  # bar 0: bar 1 is the next bar line, bar 2 the next pass top
    status, key = post(jam, control, {"op": "next", "key": "F major"})
    assert status == 200 and (key["at"], key["effective_bar"]) == ("pass", 2)
    status, tempo = post(jam, control, {"op": "tempo", "bpm": "+4"})
    assert status == 200 and tempo["effective_bar"] == 1 and tempo["bpm"] == 70, tempo
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    S.validate_run(run)
    segs = run["segments"]
    assert [(s["from_bar"], s["bpm"], s["def_version"]) for s in segs] == [(-1, 66, 1), (1, 70, 1), (2, 70, 2)]
    assert abs(segs[2]["epoch_ms"] - float(_t(segs, 2))) <= 0.001 and abs(tempo["epoch_ms"] - float(_t(segs, 1))) <= 0.001
    status, nxt = post(jam, control, {"op": "next", "card_id": "dorian-vamp"})
    assert status == 200 and nxt["effective_bar"] == 1
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    S.validate_run(run)
    assert [(s["from_bar"], s["bpm"], s["def_version"], s["def_from_bar"]) for s in run["segments"]] == \
        [(-1, 66, 1, 0), (1, 70, nxt["version"], 1)]  # the newest line wins over the key change waiting at bar 2
    jam.epoch.t = float(_t(run["segments"], 1)) + 100  # inside bar 1: bar 2 is the next line, bar 3 the next pass top
    status, later = post(jam, control, {"op": "set", "settings": {"walk": 0}, "at": "pass"})
    assert status == 200 and later["effective_bar"] == 3  # the new card's 2-bar cycle starts at bar 1
    status, sooner = post(jam, control, {"op": "set", "settings": {"humanize": 0}})
    assert status == 200 and sooner["effective_bar"] == 2
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    S.validate_run(run["run"])
    got = {s["from_bar"]: (s["humanize"], s["walk"]) for s in run["run"]["settings"]}
    assert got == {0: (0.6, 1), 2: (0, 1), 3: (0, 0)}, run["run"]["settings"]
    lines = {e["version"]: e for e in run["events"] if e["kind"] == "change"}
    for reply in (key, tempo, nxt, later, sooner):
        assert lines[reply["version"]]["effective_bar"] == reply["effective_bar"]
        assert abs(lines[reply["version"]]["epoch_ms"] - reply["epoch_ms"]) <= 0.001


def test_a_change_during_the_count_in_lands_on_bar_0_and_the_run_stays_whole(jam):
    """Round-2 verify: `]` during a 2-bar count-in landed a tempo on bar -1. The run came out malformed (500) with its
    segments already changed in memory, every later tempo, set and stop at bar answered 500, and the stop that finally
    worked marked it stopped with no frame (409 for the page). A next there made a count-in bar a backing bar."""
    add_card(jam)
    start = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel",
                                               "count_in": 2})[1]
    rid, control = start["run"], f"/api/piano/jam/runs/{start['run']}/control"
    assert start["count_in_bars"] == 2
    jam.epoch.t = start["start_epoch_ms"] + 300  # inside bar -2: bar -1 is the next bar line
    replies = []
    for body in ({"op": "tempo", "bpm": "+4"}, {"op": "tempo", "bpm": "+4"}, {"op": "next", "key": "F major", "at": "bar"},
                 {"op": "set", "settings": {"humanize": 0, "dropout": 0.25}}):
        status, reply = post(jam, control, body)
        assert status == 200 and reply["effective_bar"] == 0, (body, reply)
        replies.append(reply)
    assert [r.get("bpm") for r in replies[:2]] == [70, 74] and "count-in" in replies[0]["note"]
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    S.validate_run(run["run"])
    assert run["run"]["bar0_epoch_ms"] == start["bar0_epoch_ms"]
    assert [(s["from_bar"], s["bpm"], s["def_version"], s["def_from_bar"]) for s in run["run"]["segments"]] == \
        [(-2, 66, 1, 0), (0, 74, replies[2]["version"], 0)]  # no count-in bar carries a def cycle or a tempo change
    assert run["run"]["settings"][-1]["from_bar"] == 0 and run["run"]["settings"][-1]["dropout"] == 0.25
    status, stop = post(jam, control, {"op": "stop", "by": "daniel"})
    assert status == 200
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    S.validate_run(run["run"])
    on_disk = json.loads((jam.root / "runs" / rid / "run.json").read_text(encoding="utf-8"))
    assert on_disk == run["run"] and on_disk["closed"] and on_disk["stop_bar"] == stop["effective_bar"]
    assert [e["kind"] for e in run["events"]][-1] == "stop"
    assert get(jam, "/api/piano/jam")[0] == 200
    # `--now` at 140 bpm: its 800 ms lead holds a count-in bar, and a change a few ms later lands on bar 0 too
    fast = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "claude", "bpm": 140,
                                              "now": True})[1]
    jam.epoch.t += 5
    for body in ({"op": "tempo", "bpm": "+4"}, {"op": "next", "key": "F major", "at": "bar"}):
        status, reply = post(jam, f"/api/piano/jam/runs/{fast['run']}/control", body)
        assert status == 200 and reply["effective_bar"] == 0, (body, reply)
    run = get(jam, f"/api/piano/jam/runs/{fast['run']}")[1]["run"]
    S.validate_run(run)
    assert run["bar0_epoch_ms"] == fast["bar0_epoch_ms"]


def test_a_refused_change_leaves_the_run_exactly_as_it_was(jam, monkeypatch):
    add_card(jam)
    start = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]
    rid, control = start["run"], f"/api/piano/jam/runs/{start['run']}/control"
    jam.epoch.t += 9000
    before = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    disk = (jam.root / "runs" / rid / "run.json").read_bytes()
    monkeypatch.setattr(RUNS, "insert_segment", lambda segs, m, bar, bpm=None, def_version=None:
                        [dict(segs[0], def_from_bar=5)])
    status, reply = post(jam, control, {"op": "tempo", "bpm": 80})
    assert status == 409 and reply["field"] == "segments[0].def_from_bar" and "unchanged" in reply["error"], reply
    monkeypatch.undo()
    assert get(jam, f"/api/piano/jam/runs/{rid}")[1] == before
    assert (jam.root / "runs" / rid / "run.json").read_bytes() == disk
    status, reply = post(jam, control, {"op": "tempo", "bpm": 80})
    assert status == 200 and reply["version"] == 2
    status, reply = post(jam, control, {"op": "set", "settings": {"dropout": 1.5}})
    assert status == 400 and reply["field"].endswith("dropout"), reply


# ============================================================================================ time passing, restart
def test_passes_end_a_run_and_a_knock_nobody_takes_expires(jam):
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "try", "card_id": "lydian-four", "by": "daniel",
                                             "passes": 2})[1]["run"]
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    assert run["settings"][0]["try_backing"] == "bass" and run["settings"][0]["passes"] == 2
    end = float(_t(run["segments"], 4))
    jam.epoch.t = end - 1
    assert get(jam, "/api/piano/jam")[1]["run"]["state"] == "running"
    jam.epoch.t = end + 1
    get(jam, "/api/piano/jam")
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    assert run["stop_reason"] == "count" and run["stop_bar"] == 4 and run["stopped_epoch_ms"] == end
    knock = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "claude"})[1]["run"]
    jam.epoch.t += PENDING_EXPIRE_MS
    assert get(jam, "/api/piano/jam")[1]["run"] is None
    assert get(jam, f"/api/piano/jam/runs/{knock}")[1]["run"]["stop_reason"] == "expired"


def test_restart_closes_open_runs_and_building_an_app_does_not(jam):
    add_card(jam)
    running = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]["run"]
    jam.epoch.t += 4000
    pending = post(jam, "/api/piano/jam/start", {"mode": "play", "card_id": "lydian-four", "by": "claude"})[1]["run"]
    jam.epoch.t += 4000
    post(jam, "/api/piano/jam/mark", {"text": "a synthetic mark", "run": running})
    app2 = App([str(jam.tmp / "library")], takes_root=jam.tmp / "takes", performance_root=jam.tmp / "perf")
    assert app2.jam.root == jam.root
    app2.jam.runs.now_ms = lambda: T0 + 60000  # the restarted server's clock, a minute on (the runs are dated 2030)
    for rid in (running, pending):
        assert json.loads((jam.root / "runs" / rid / "run.json").read_text(encoding="utf-8"))["closed"] is False
    assert sorted(app2.jam.runs.close_unclosed()) == sorted([running, pending])
    for rid, last in ((running, T0 + 8000), (pending, T0 + 4000)):
        status, got = app2.jam.handle("GET", f"/api/piano/jam/runs/{rid}", {}, None)
        run, line = got["run"], got["events"][-1]
        S.validate_run(run)
        assert run["stop_reason"] == "server-restart" and run["approx"] is True and run["stopped_epoch_ms"] == last
        assert line["kind"] == "stop" and line["by"] == "server" and line["reason"] == "server-restart"
    assert app2.jam.handle("GET", "/api/piano/jam", {}, None)[1]["run"] is None


def test_acks_are_idempotent_and_a_lost_stream_stops_the_run(jam):
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel",
                                             "page_id": "p-a"})[1]["run"]
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]["run"]
    ack = {"page_id": "p-a", "role": "owner", "version": 1, "bar": 0, "bar_epoch_ms": run["bar0_epoch_ms"],
           "perf_ms": 1000.0, "perf_offset_ms": T0 - 1000, "log": {"local": "lg-1", "session": None,
                                                                     "t0_perf_ms": 10.0}}
    path = f"/api/piano/jam/runs/{rid}/ack"
    assert post(jam, path, ack)[1] == {"ok": True, "duplicate": False}
    assert post(jam, path, ack)[1] == {"ok": True, "duplicate": True}
    assert post(jam, path, dict(ack, version=9))[1]["field"] == "version"
    assert post(jam, path, dict(ack, role="boss"))[1]["field"] == "role"
    jam.epoch.t += 9000
    assert post(jam, path, dict(ack, bar=2, stopped="stream-lost", stop_bar=2))[0] == 200
    run = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    assert run["run"]["stop_reason"] == "stream-lost" and run["run"]["stop_bar"] == 2
    assert [e["kind"] for e in run["events"]].count("ack") == 2


def test_marks_and_the_run_listing(jam):
    assert post(jam, "/api/piano/jam/mark", {"text": "nothing to mark"})[0] == 404
    add_card(jam)
    rid = post(jam, "/api/piano/jam/start", {"mode": "loop", "card_id": "lydian-four", "by": "daniel"})[1]["run"]
    assert post(jam, "/api/piano/jam/mark", {"text": "he found D on the Ab bar"}) == (200, {"run": rid, "seq": 1})
    assert post(jam, "/api/piano/jam/mark", {"text": "x" * 201})[1]["field"] == "text"
    assert [r["run"] for r in get(jam, "/api/piano/jam/runs?card=lydian-four")[1]["runs"]] == [rid]
    assert get(jam, "/api/piano/jam/runs?card=other")[1]["runs"] == []
    got = get(jam, f"/api/piano/jam/runs/{rid}")[1]
    assert got["events"][1]["kind"] == "mark" and got["alignment"] == []
    assert get(jam, "/api/piano/deck")[1]["cards"][0]["runs"] == 1
    assert get(jam, "/api/piano/jam/runs/20300101-000000-00000000")[0] == 404


# ============================================================================================ replay, the edges
def test_replay_answers_a_cue_and_never_broadcasts_it(jam):
    store = jam.app.performance
    session = store.open({"page_id": "p-a"})
    store.append(session, [{"t_ms": 500, "kind": "on", "note": 60, "vel": 50},
                           {"t_ms": 1500, "kind": "off", "note": 60}])
    last = jam.app.cues.status()["last_id"]
    status, reply = get(jam, f"/api/piano/replay?session={session}&at=0:00&seconds=2")
    assert status == 200 and reply["cue"]["type"] == "sequence" and reply["cue"]["source"] == "replay"
    assert reply["cue"]["steps"][0]["notes"] == [60] and jam.app.cues.status()["last_id"] == last
    assert get(jam, "/api/piano/replay?session=20300101-000000-00000000&at=0:01")[0] == 404
    assert get(jam, f"/api/piano/replay?session={session}")[1]["field"] == "at"


def test_jam_posts_check_the_origin_and_the_body_and_stay_on_without_the_log(jam, tmp_path):
    status, reply = call(jam, "POST", "/api/piano/jam/owner", {"page_id": "p-a"},
                         headers={"Origin": "https://example.com"})
    assert status == 403
    assert call(jam, "POST", "/api/piano/jam/owner", b"{not json")[0] == 400
    assert call(jam, "POST", "/api/piano/jam/owner", b"[1, 2]")[0] == 400
    assert get(jam, "/api/piano/jammed")[0] == 404
    quiet = App([str(tmp_path / "lib2")], takes_root=tmp_path / "t2", performance_log=False, jam_root=tmp_path / "j2")
    quiet.jam.resolver = FixtureResolver()
    quiet.jam.deck.reader = quiet.jam.resolver.page_reads
    status, reply = quiet.jam.handle("POST", "/api/piano/deck/cards", {}, {"card": load("card_lydian_four.json")})
    assert status == 200 and quiet.jam.handle("GET", "/api/piano/deck", {}, None)[1]["rev"] == 1
    assert quiet.jam.handle("GET", "/api/piano/replay", {"session": ["x"], "at": ["0:01"]}, None)[0] == 404
