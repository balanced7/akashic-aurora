"""J3, the verbs (jam-spec 7): py -m arsenal.pianocue card / deck / loop / try / jam / template.

The card and deck verbs write the files directly when no server answers; the loop verbs need a jam page (exit 3), a
server (exit 4) and a run that has not moved underneath them (exit 5). Voicing needs node. Every card, session and
page here is synthetic; the servers run on free ports and never touch 8793."""
import http.server
import json
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import pianocue  # noqa: E402
from arsenal.jam import schemas as S  # noqa: E402
from arsenal.pianocue import CueHub  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "jam"
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="the voicing bridge needs node")


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run(argv, capsys):
    code = pianocue.main([str(a) for a in argv])
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture()
def srv(tmp_path):
    app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    app.cues = CueHub(heartbeat_s=0.3, id_base=0)
    server = Server(0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield SimpleNamespace(port=server.server_address[1], app=app, tmp=tmp_path)
    app.cues.close()
    server.shutdown()
    server.server_close()


class Page:
    """A listening page: the event stream, with or without the jam caps."""

    def __init__(self, port, query="?caps=jam1,deck1&page=p-test"):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.sock.sendall(f"GET /api/piano/cues{query} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode("ascii"))
        self.buf = b""
        self._until(b"\r\n\r\n")
        self._until(b"\n\n")

    def _until(self, sep):
        while sep not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError
            self.buf += chunk
        part, self.buf = self.buf.split(sep, 1)
        return part

    def event(self):
        while True:
            text = self._until(b"\n\n").decode("utf-8")
            if not text.startswith(":"):
                fields = dict(line.split(": ", 1) for line in text.split("\n"))
                return fields["event"], json.loads(fields["data"])

    def close(self):
        self.sock.close()


LAMENT = ["card", "add", "--id", "lament-test", "--title", "Walking bass under a held chord",
          "--meaning", "Hold one chord and let the bass step down.", "--group", "moves", "--kind", "loop",
          "--key", "Db major", "--chords", "6m11:4 | 6m11/5:4 | 6m11/4:4 | 6m11/3:4",
          "--upper-same", "2", "--upper-same", "3", "--upper-same", "4",
          "--notes-for", "1=Bb2 Bb3 Ab4 C5 Db5 Eb5 F5", "--bpm", "60", "--groove", "hold",
          "--explain", "Your hands hold one chord; only the bass walks down.", "--why", "It is the old lament bass.",
          "--try", "Play a slow melody on one note.", "--check", "slot=3 role=#11 relative_to=bass want=present "
          "say=you found C over the Gb bass", "--tag", "bass"]


@needs_node
def test_card_verbs_write_the_files_directly_with_no_server(tmp_path, capsys):
    port, root = closed_port(), tmp_path / "jam"
    common = ["--port", port, "--jam-root", root]
    code, out, err = run(LAMENT + common, capsys)
    assert code == 0, err
    assert f"no server on 127.0.0.1:{port}" in err
    assert "card lament-test rev 1 (loop, Db major, 60 bpm, 4 bars)" in out and "Bbm11/Ab" in out
    assert "(upper same)" in out
    stored = json.loads((root / "deck" / "cards" / "lament-test.json").read_text(encoding="utf-8"))
    S.validate_card(stored, stored=True)
    assert stored["checks"][0]["slot"] == 2 and stored["chords"][1]["upper"] == "same"
    assert stored["chords"][0]["notes"] == [46, 58, 68, 72, 73, 75, 77] and stored["page_reads"][0]["name"] == "Bbm11"

    code, out, _ = run(["card", "list"] + common, capsys)
    assert code == 0 and "lament-test" in out and "deck rev 1: 1 card" in out
    code, out, _ = run(["card", "info", "lament", "--key", "Eb major"] + common, capsys)
    assert code == 0 and "Cm11/Bb" in out and "what   Your hands hold one chord" in out
    code, out, _ = run(["card", "edit", "lament", "--title", "The lament", "--add-tag", "sad"] + common, capsys)
    assert code == 0 and "card lament-test rev 2" in out
    code, _, err = run(["card", "edit", "lament", "--if-rev", "1", "--title", "x"] + common, capsys)
    assert code == 5 and "conflict" in err
    code, out, _ = run(["card", "keep", "lament", "--key", "D major"] + common, capsys)
    assert code == 0 and "card k-lament-test-" in out and "D major" in out
    code, out, _ = run(["card", "rm", "lament-test"] + common, capsys)
    assert code == 0 and "moved to trash/lament-test.rev2." in out
    code, out, _ = run(["card", "trash"] + common, capsys)
    assert code == 0 and "lament-test" in out
    code, out, _ = run(["card", "restore", "lament-test"] + common, capsys)
    assert code == 0 and "restored as rev 3" in out

    missing = [a for i, a in enumerate(LAMENT) if a != "--meaning" and LAMENT[i - 1] != "--meaning"]
    code, _, err = run([*missing[:2], "--id", "no-meaning", *missing[4:]] + common, capsys)
    assert code == 2 and "--meaning" in err
    code, _, err = run(["card", "add", "--id", "bad-line", "--title", "t", "--meaning", "m", "--kind", "loop",
                        "--group", "try", "--key", "Eb major", "--chords", "1maj9:4 | ", "--explain", "x", "--why",
                        "x", "--try", "x", "--names", "Ebmaj9"] + common, capsys)
    assert code == 2 and "--chords" in err and "--names" in err
    code, out, _ = run(["card", "add", "--id", "dry", "--title", "t", "--meaning", "m", "--kind", "chord", "--key",
                        "Eb major", "--names", "Abmaj7#11:8", "--explain", "x", "--why", "x", "--try", "x",
                        "--dry-run"] + common, capsys)
    assert code == 0 and json.loads(out)["card"]["chords"] == [{"n": "4maj7#11", "beats": 8}]
    assert not (root / "deck" / "cards" / "dry.json").exists()


@needs_node
def test_loop_verbs_need_a_jam_page_then_drive_the_run(srv, capsys):
    port = srv.port
    code, _, err = run(LAMENT + ["--port", port], capsys)
    assert code == 0 and "no server" not in err
    code, _, err = run(["loop", "start", "lament", "--port", port], capsys)
    assert code == 3 and f"http://127.0.0.1:{port}/piano" in err
    plain = Page(port, "")
    try:
        code, _, err = run(["loop", "start", "lament", "--port", port], capsys)
        assert code == 3 and "reload the piano page" in err
    finally:
        plain.close()
    page = Page(port)
    try:
        code, out, err = run(["loop", "start", "lament", "--bpm", "60", "--port", port], capsys)
        assert code == 0, err
        assert 'loop "Walking bass under a held chord" in Db major, 60 bpm, 4 bars, hold/' in out
        assert "until stopped" in out and "waiting for Daniel's pause on 1 jam page" in out
        rid = out.split(":")[0].split()[1]
        code, _, err = run(["loop", "tempo", "+4", "--port", port], capsys)
        assert code == 5 and "waiting for Daniel's pause" in err
        status, reply = srv.app.jam.handle("POST", f"/api/piano/jam/runs/{rid}/launch", {},
                                           {"page_id": "p-test", "epoch_ms": time.time() * 1000 + 400})
        assert status == 200, reply
        code, out, err = run(["loop", "tempo", "-4", "--port", port], capsys)
        assert code == 0 and "version 2: tempo -4 from bar" in out, err
        code, out, _ = run(["loop", "set", "--groove", "pulse", "--port", port], capsys)
        assert code == 0 and "version 3: set groove=pulse" in out
        code, out, _ = run(["jam", "status", "--port", port], capsys)
        assert code == 0 and rid in out and "sound owner p-test" in out and "with jam1" in out
        code, out, _ = run(["jam", "mark", "he", "held", "Db", "--port", port], capsys)
        assert code == 0 and f"marked run {rid}" in out
        code, out, _ = run(["loop", "stop", "--port", port], capsys)
        assert code == 0 and "version 4: stop from bar" in out
        code, out, _ = run(["jam", "runs", "--port", port], capsys)
        assert code == 0 and rid in out and "stopped: cli" in out
        code, _, err = run(["loop", "stop", "--port", port], capsys)
        assert code == 2 and "no loop or try is running" in err
    finally:
        page.close()
    events = srv.app.jam.runs.get(rid)["events"]
    assert [e["kind"] for e in events] == ["start", "launch", "change", "change", "mark", "stop"]
    assert events[2]["bpm"] == 56


@needs_node
def test_try_and_play_take_chord_lines_and_slots(srv, capsys):
    port = srv.port
    run(LAMENT + ["--port", port], capsys)
    page = Page(port)
    try:
        code, _, err = run(["try", "1maj9:4 | 4maj7#11:4", "--port", port], capsys)
        assert code == 2 and "--key" in err
        code, out, err = run(["try", "1maj9:4 | 4maj7#11:4", "--key", "F major", "--now", "--port", port], capsys)
        assert code == 0 and 'try "chords" in F major' in out and "bass backing, 2 passes" in out, err
        assert "starts in" in out
        st = srv.app.jam.handle("GET", "/api/piano/jam", {}, None)[1]
        assert st["run"]["mode"] == "try" and st["run"]["settings"][0]["try_backing"] == "bass"
        assert st["run"]["settings"][0]["passes"] == 2 and st["run"]["state"] == "running"
        assert [s["name"] for s in st["def"]["slots"]] == ["Fmaj9", "Bbmaj7#11"]
        code, out, err = run(["card", "play", "lament", "--slot", "3", "--vel", "40", "--now", "--port", port],
                             capsys)
        assert code == 0 and 'play "Walking bass under a held chord"' in out and "Bbm11/Gb" in out, err
        play = srv.app.jam.handle("GET", "/api/piano/jam", {}, None)[1]["play"]
        assert play["mode"] == "play" and play["slot"] == 2 and play["velocity"] == 40
        start = srv.app.jam.runs.get(play["run"])["events"][0]
        assert len(start["def"]["slots"]) == 1 and start["def"]["slots"][0]["vel"] == 40
    finally:
        page.close()


@needs_node
def test_card_show_and_open_reach_the_page(srv, capsys):
    port = srv.port
    run(LAMENT + ["--port", port], capsys)
    page = Page(port)  # a fresh page gets no backlog, so its first event is the show below
    try:
        code, out, err = run(["card", "show", "lament", "--slot", "2", "--port", port], capsys)
        assert code == 0 and "show Bbm11/Ab" in out, err
        kind, data = page.event()
        assert kind == "cue" and data["cue"]["type"] == "hover" and data["cue"]["label"] == "Bbm11/Ab"
        d = srv.app.jam.handle("GET", "/api/piano/deck/cards/lament-test/resolve", {"slot": ["1"]}, None)[1]["def"]
        assert data["cue"]["notes"] == d["slots"][0]["voicings"]["play"] and data["cue"]["hold_ms"] == 0
        assert data["cue"]["detail"] == "6m11/5 in Db major" and data["cue"]["source"] == "claude"
        code, out, _ = run(["card", "open", "lament", "--port", port], capsys)
        assert code == 0 and "for 1 deck page" in out
        kind, data = page.event()
        assert kind == "deck" and data["deck"]["op"] == "open" and data["deck"]["card_id"] == "lament-test"
    finally:
        page.close()


def test_no_server_and_an_old_server(capsys):
    code, _, err = run(["loop", "stop", "--port", closed_port()], capsys)
    assert code == 4 and "no arsenal server answers" in err

    class Old(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"error": f"no route for GET {self.path}"}).encode()
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    old = http.server.HTTPServer(("127.0.0.1", 0), Old)
    threading.Thread(target=old.serve_forever, daemon=True).start()
    try:
        code, _, err = run(["jam", "status", "--port", old.server_address[1]], capsys)
        assert code == 4 and "predates the jam routes" in err
    finally:
        old.shutdown()
        old.server_close()


@needs_node
def test_deck_seed_and_order_through_the_server(srv, tmp_path, capsys):
    cards = []
    for name in ("card_pair_question.json", "card_pair_answer.json"):
        c = json.loads((FIX / name).read_text(encoding="utf-8"))
        for key in ("rev", "page_reads", "created_at", "updated_at", "updated_by"):
            c.pop(key, None)
        c["source"] = {"kind": "seed", "seed_version": 1}
        cards.append(c)
    seed = tmp_path / "deck-v1.json"
    seed.write_text(json.dumps({"api": "arsenal.jam.seed/v0", "seed_version": 1, "cards": cards}), encoding="utf-8")
    srv.app.jam.seed_path = seed
    port = srv.port
    code, out, err = run(["deck", "seed", "--dry-run", "--port", port], capsys)
    assert code == 0 and "would install 2" in out, err
    code, out, _ = run(["deck", "seed", "--port", port], capsys)
    assert code == 0 and "installed 2, updated 0, kept 0" in out
    code, out, _ = run(["deck", "seed", "--port", port], capsys)
    assert code == 0 and "installed 0, updated 0, kept 2" in out
    code, out, _ = run(["deck", "order", "float-answer", "--port", port], capsys)
    assert code == 0 and "float-answer first" in out
    code, out, _ = run(["deck", "--port", port], capsys)
    lines = [line for line in out.splitlines() if "float-" in line]
    assert code == 0 and "float-answer" in lines[0] and "float-question" in lines[1]
    srv.app.jam.seed_path = tmp_path / "missing.json"
    code, _, err = run(["deck", "seed", "--port", port], capsys)
    assert code == 2 and "no seed deck" in err


@needs_node
def test_template_save_from_moment_keeps_his_voicing(tmp_path, capsys):
    from arsenal.performance import PerformanceStore
    perf = PerformanceStore(tmp_path / "perf")
    session = perf.open({})
    held = [39, 51, 63, 65, 68, 70]  # Eb2 Eb3 Eb4 F4 Ab4 Bb4, a synthetic held sus chord
    later = [44, 56, 60, 63, 67]      # Ab2 Ab3 C4 Eb4 G4
    events = [{"t_ms": 1000 + i * 5, "kind": "on", "note": n, "vel": 50} for i, n in enumerate(held)]
    events += [{"t_ms": 7000, "kind": "off", "note": n} for n in held]
    events += [{"t_ms": 8000 + i * 5, "kind": "on", "note": n, "vel": 50} for i, n in enumerate(later)]
    events += [{"t_ms": 13000, "kind": "off", "note": n} for n in later]
    perf.append(session, events)
    common = ["--port", closed_port(), "--jam-root", tmp_path / "jam", "--root", tmp_path / "perf"]
    code, out, err = run(["template", "save-from-moment", session, "0:03", "--dry-run"] + common, capsys)
    assert code == 0, err
    moment = json.loads(out)["moment"]
    assert moment["notes"] == held and moment["session"] == session and moment["at_ms"] <= 3000 < moment["until_ms"]
    code, out, err = run(["template", "save-from-moment", session, "0:03", "--title", "The held sus"] + common, capsys)
    assert code == 0 and "The held sus" in out, err
    cards = list((tmp_path / "jam" / "deck" / "cards").glob("t-*.json"))
    assert len(cards) == 1
    c = json.loads(cards[0].read_text(encoding="utf-8"))
    assert c["chords"][0]["notes"] == held and c["source"]["kind"] == "saved-from-moment"
    assert c["created_by"] == "daniel" and c["group"] == "kept" and c["moments"][0]["session"] == session
    code, out, err = run(["template", "save-last", "--dry-run"] + common, capsys)
    assert code == 0 and json.loads(out)["moment"]["notes"] == later, err
