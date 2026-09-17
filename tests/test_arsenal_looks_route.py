"""GET and PUT /api/piano/looks (arsenal/pianolooks.py): the Studio drawer's saved looks, over HTTP against a server on a
free port. Round trip, rev conflicts, the Host, Origin, type and size refusals, value checks, and the atomic write."""
import http.client
import json
import re
import socket
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import pianolooks  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

LOOKS = "/api/piano/looks"


def preset(pid="look-a", name="Moonlit practice", **settings):
    return {"id": pid, "name": name,
            "settings": settings or {"scheme": "classic", "enabled": True, "intensity": 0.85, "theme": "moon"}}


@pytest.fixture()
def looks(tmp_path):
    app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    srv = Server(0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1], app, tmp_path / "looks"
    srv.shutdown()
    srv.server_close()


def call(port, method, body=None, headers=None, path=LOOKS):
    """(status, reply). The Host header is http.client's own (127.0.0.1:port) unless headers name one."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    raw = body if isinstance(body, bytes) else (json.dumps(body).encode("utf-8") if body is not None else None)
    sent = {"Content-Type": "application/json"} if raw is not None else {}
    sent.update(headers or {})
    conn.request(method, path, body=raw, headers={k: v for k, v in sent.items() if v is not None})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, (json.loads(data) if data else None)


def test_get_answers_an_empty_list_before_any_save_and_writes_nothing(looks):
    port, app, folder = looks
    assert app.looks.root == folder.resolve()
    status, reply = call(port, "GET")
    assert status == 200 and reply == {"api": pianolooks.API, "rev": 0, "presets": []}
    assert not folder.exists()  # a GET never creates the folder


def test_looks_root_follows_the_state_folders(tmp_path):
    assert App([str(tmp_path)], takes_root=tmp_path / "t").looks.root == ROOT / "state" / "arsenal" / "looks"
    assert App([str(tmp_path)], takes_root=tmp_path / "t", performance_root=tmp_path / "p").looks.root == \
        (tmp_path / "looks").resolve()
    assert App([str(tmp_path)], takes_root=tmp_path / "t", looks_root=tmp_path / "mine").looks.root == tmp_path / "mine"


def test_round_trip_keeps_every_value_and_bumps_rev(looks):
    port, _, folder = looks
    first = [preset(), dict(preset("look-b", "Film · wide 16:9", framing="16:9", quality="ultra", motion=0.4,
                                   autoWorld=False), favourite=True, created=1893456000000, updated=1893456000001)]
    status, reply = call(port, "PUT", {"rev": 0, "presets": first})
    assert status == 200 and reply == {"api": pianolooks.API, "rev": 1, "presets": first}
    assert call(port, "GET") == (200, reply)
    on_disk = json.loads((folder / "presets.json").read_text(encoding="utf-8"))
    assert on_disk == reply
    # the page's own origin, under either loopback name, and the api field echoed back are all accepted
    status, reply = call(port, "PUT", {"api": pianolooks.API, "rev": 1, "presets": first[:1]},
                         headers={"Host": f"localhost:{port}", "Origin": f"http://localhost:{port}"})
    assert status == 200 and reply["rev"] == 2 and reply["presets"] == first[:1]
    status, reply = call(port, "PUT", {"rev": 2, "presets": []},
                         headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json; charset=utf-8"})
    assert status == 200 and reply == {"api": pianolooks.API, "rev": 3, "presets": []}
    assert sorted(p.name for p in folder.iterdir()) == ["presets.json"]  # no temp file left behind


def test_a_stale_rev_is_refused_with_409_and_the_current_list(looks):
    port, _, folder = looks
    assert call(port, "PUT", {"rev": 0, "presets": [preset()]})[0] == 200
    before = (folder / "presets.json").read_bytes()
    status, reply = call(port, "PUT", {"rev": 0, "presets": [preset("look-z", "Other window")]})
    assert status == 409 and reply["rev"] == 1 and reply["presets"] == [preset()]
    assert "changed" in reply["error"]
    assert call(port, "PUT", {"rev": 7, "presets": []})[0] == 409
    assert (folder / "presets.json").read_bytes() == before


@pytest.mark.parametrize("host", ["evil.example:{port}", "127.0.0.1:1", "localhost", "192.168.1.20:{port}",
                                  "127.0.0.1.nip.io:{port}", "user@127.0.0.1:{port}", "127.0.0.1:{port}/x", ""])
def test_a_host_other_than_this_machine_on_this_port_is_refused(looks, host):
    port, _, folder = looks
    host = host.format(port=port)
    for method, body in (("GET", None), ("PUT", {"rev": 0, "presets": [preset()]})):
        status, reply = call(port, method, body, headers={"Host": host})
        assert status == 403, (method, host, reply)
    assert not folder.exists()


@pytest.mark.parametrize("origin", ["http://evil.example", "http://127.0.0.1:1", "https://127.0.0.1:{port}", "null",
                                    "http://localhost:{port}", "http://127.0.0.1.nip.io:{port}"])
def test_an_origin_other_than_the_page_is_refused(looks, origin):
    port, _, folder = looks
    origin = origin.format(port=port)  # localhost is refused here because the Host is 127.0.0.1
    for method, body in (("GET", None), ("PUT", {"rev": 0, "presets": [preset()]})):
        status, reply = call(port, method, body, headers={"Origin": origin})
        assert status == 403, (method, origin, reply)
    assert not folder.exists()


@pytest.mark.parametrize("kind", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data", None])
def test_a_put_that_is_not_application_json_is_refused(looks, kind):
    port, _, folder = looks
    status, reply = call(port, "PUT", {"rev": 0, "presets": [preset()]}, headers={"Content-Type": kind})
    assert status == 415 and "application/json" in reply["error"]
    assert not folder.exists()


def test_the_size_cap_is_256_kb(looks):
    port, _, folder = looks
    # declared over the cap: refused from the header alone, before a byte of the body is read
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.putrequest("PUT", LOOKS)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(pianolooks.MAX_BODY + 1))
    conn.endheaders()
    resp = conn.getresponse()
    assert resp.status == 413 and "256 KB" in json.loads(resp.read())["error"]
    conn.close()
    # exactly at the cap is accepted (padded with whitespace)
    body = json.dumps({"rev": 0, "presets": [preset()]}).encode("utf-8")
    body += b" " * (pianolooks.MAX_BODY - len(body))
    assert len(body) == pianolooks.MAX_BODY and call(port, "PUT", body)[0] == 200
    # no Content-Length at all
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.putrequest("PUT", LOOKS)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Transfer-Encoding", "chunked")
    conn.endheaders()
    conn.send(b"0\r\n\r\n")
    resp = conn.getresponse()
    assert resp.status == 411
    conn.close()
    assert json.loads((folder / "presets.json").read_text(encoding="utf-8"))["rev"] == 1


def test_at_most_100_presets_with_unique_ids(looks):
    port, _, _ = looks
    many = [preset(f"look-{i}", f"Look {i}") for i in range(pianolooks.MAX_PRESETS)]
    status, reply = call(port, "PUT", {"rev": 0, "presets": many + [preset("look-x", "One too many")]})
    assert status == 400 and "at most 100" in reply["error"]
    assert call(port, "PUT", {"rev": 0, "presets": [preset(), preset()]})[0] == 400
    assert call(port, "PUT", {"rev": 0, "presets": many})[0] == 200


@pytest.mark.parametrize("name", ["", "   ", "x" * 61, 5, None, "tab\there", "line\nbreak"])
def test_bad_names_are_refused(looks, name):
    port, _, folder = looks
    status, reply = call(port, "PUT", {"rev": 0, "presets": [preset(name=name)]})
    assert status == 400 and "name" in reply["error"]
    assert not folder.exists()


def test_names_of_one_to_sixty_characters_are_kept_as_given(looks):
    port, _, _ = looks
    names = ["A", "x" * 60, "Nocturne · rain on the lake", "Écran large"]
    presets = [preset(f"look-{i}", name) for i, name in enumerate(names)]
    status, reply = call(port, "PUT", {"rev": 0, "presets": presets})
    assert status == 200 and [p["name"] for p in reply["presets"]] == names


@pytest.mark.parametrize("settings", [{"theme": {"name": "moon"}}, {"theme": ["moon"]}, {"theme": None},
                                      {"theme": "x" * 201}, {"bad key": 1}, {"__proto__": 1},
                                      {f"s{i}": i for i in range(65)}])
def test_setting_values_must_be_strings_numbers_or_booleans(looks, settings):
    port, _, folder = looks
    status, reply = call(port, "PUT", {"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": settings}]})
    assert status == 400, reply
    assert not folder.exists()


@pytest.mark.parametrize("raw", [
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": {"intensity": NaN}}]}',
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": {"intensity": Infinity}}]}',
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": {}, "builtIn": true}]}',
    b'{"rev": 0, "presets": [{"id": "builtin:classic", "name": "A", "settings": {}}]}',
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": {}, "favourite": "yes"}]}',
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A", "settings": {}, "created": -1}]}',
    b'{"rev": 0, "presets": [{"id": "look-a", "name": "A"}]}',
    b'{"rev": true, "presets": []}',
    b'{"rev": "0", "presets": []}',
    b'{"presets": []}',
    b'{"rev": 0, "presets": {}}',
    b'{"rev": 0, "presets": [], "extra": 1}',
    b'{"api": "arsenal.piano.looks/v0", "rev": 0, "presets": []}',
    b'[]',
    b'not json',
    b'\xff\xfe',
    b'[' * 5000 + b']' * 5000,
])
def test_malformed_bodies_are_refused_with_400(looks, raw):
    port, _, folder = looks
    status, reply = call(port, "PUT", raw)
    assert status == 400 and reply["error"], reply
    assert not folder.exists()


def test_a_failed_write_leaves_the_previous_file_and_no_temp_file(looks, monkeypatch):
    port, _, folder = looks
    assert call(port, "PUT", {"rev": 0, "presets": [preset()]})[0] == 200
    before = (folder / "presets.json").read_bytes()

    def half_written(doc, fh, **kwargs):  # the disk fills part-way through the new file
        fh.write(json.dumps(doc)[:40])
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(pianolooks.json, "dump", half_written)
    status, reply = call(port, "PUT", {"rev": 1, "presets": [preset("look-b", "Never lands")]})
    assert status == 500 and "No space left" in reply["error"]
    monkeypatch.undo()
    assert (folder / "presets.json").read_bytes() == before
    assert sorted(p.name for p in folder.iterdir()) == ["presets.json"]

    def refuse_replace(src, dst):  # the rename itself fails (another program holds the file)
        raise PermissionError(13, "The process cannot access the file")

    monkeypatch.setattr(pianolooks.os, "replace", refuse_replace)
    assert call(port, "PUT", {"rev": 1, "presets": [preset("look-b", "Never lands")]})[0] == 500
    monkeypatch.undo()
    assert (folder / "presets.json").read_bytes() == before
    assert sorted(p.name for p in folder.iterdir()) == ["presets.json"]
    assert call(port, "GET") == (200, {"api": pianolooks.API, "rev": 1, "presets": [preset()]})


def test_an_unreadable_file_is_reported_and_never_overwritten(looks):
    port, _, folder = looks
    folder.mkdir()
    (folder / "presets.json").write_text('{"rev": 3, "presets": [', encoding="utf-8")
    status, reply = call(port, "GET")
    assert status == 500 and "left as it is" in reply["error"]
    assert call(port, "PUT", {"rev": 3, "presets": []})[0] == 500
    assert (folder / "presets.json").read_text(encoding="utf-8") == '{"rev": 3, "presets": ['


def test_concurrent_saves_on_one_rev_let_exactly_one_through(looks):
    port, _, _ = looks
    results = []
    barrier = threading.Barrier(8)

    def save(i):
        barrier.wait()
        results.append(call(port, "PUT", {"rev": 0, "presets": [preset(f"look-{i}", f"Window {i}")]})[0])

    threads = [threading.Thread(target=save, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [200] + [409] * 7
    assert call(port, "GET")[1]["rev"] == 1


def test_other_methods_and_paths_stay_unrouted(looks):
    port, _, _ = looks
    assert call(port, "PUT", {"rev": 0, "presets": []}, path="/api/presets")[0] == 404
    assert call(port, "POST", {"rev": 0, "presets": []})[0] == 404
    assert call(port, "HEAD")[0] == 200


def test_a_request_hidden_in_an_unread_body_is_never_parsed(looks):
    """A request nothing reads the body of (an unrouted 404) carries a whole PUT in its body, as a page on another site can
    send a simple POST with a text/plain body and no preflight. The server closes the connection rather than read the
    leftover bytes as a second request, which would pass the Host and Origin checks."""
    port, _, folder = looks
    crlf = "\r\n"
    inner = json.dumps({"rev": 0, "presets": [preset("pwned", "written by another site")]}).encode("utf-8")
    hidden = crlf.join([f"PUT {LOOKS} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Content-Type: application/json",
                        f"Content-Length: {len(inner)}", "", ""]).encode("ascii") + inner
    for method, path in (("POST", LOOKS), ("POST", "/api/nope"), ("PUT", "/api/nope")):
        outer = crlf.join([f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Origin: http://evil.example",
                           "Content-Type: text/plain;charset=UTF-8", "Connection: keep-alive",
                           f"Content-Length: {len(hidden)}", "", ""]).encode("ascii")
        data, kept_open = b"", False
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(outer + hidden)
            try:
                while chunk := sock.recv(65536):
                    data += chunk
            except socket.timeout:
                kept_open = True
        statuses = re.findall(rb"HTTP/1\.[01] (\d{3}) ", data)  # (a body ends without a newline: not anchored)
        assert statuses == [b"404"] and not kept_open and b"Connection: close" in data, (method, path, data)
    assert not folder.exists()
    assert call(port, "GET")[1]["presets"] == []
    # a body the route reads in full leaves the keep-alive connection usable
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("PUT", LOOKS, body=json.dumps({"rev": 0, "presets": [preset()]}),
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 200 and resp.getheader("Connection") is None
    resp.read()
    conn.request("GET", LOOKS)
    resp = conn.getresponse()
    assert resp.status == 200 and json.loads(resp.read())["rev"] == 1
    conn.close()
