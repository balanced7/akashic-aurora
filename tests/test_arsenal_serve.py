"""The First Light server's routes, exercised without a browser: library, Range, plan, takes."""
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.serve import App, Server, clip_id_for  # noqa: E402

PAYLOAD = bytes(range(256)) * 40  # 10240 bytes; not a real video, just bytes to stream


@pytest.fixture()
def server(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    clip = library / "tiny.mp4"
    clip.write_bytes(PAYLOAD)
    srv = Server(0, App([str(library)], takes_root=tmp_path / "takes"))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", clip
    srv.shutdown()
    srv.server_close()


def _get(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def _post(url, obj):
    request = urllib.request.Request(url, data=json.dumps(obj).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def test_library_range_resolve_and_traversal(server):
    base, clip = server
    status, _, body = _get(base + "/api/health")
    assert status == 200 and json.loads(body)["ok"] is True

    status, _, body = _get(base + "/api/library")
    clips = json.loads(body)["clips"]
    assert [c["name"] for c in clips] == ["tiny.mp4"] and clips[0]["id"] == clip_id_for(clip)

    status, headers, body = _get(f"{base}/api/media/{clips[0]['id']}", {"Range": "bytes=10-19"})
    assert status == 206 and body == PAYLOAD[10:20]
    assert headers["Content-Range"] == "bytes 10-19/10240"
    status, _, _ = _get(f"{base}/api/media/{clips[0]['id']}", {"Range": "bytes=99999-"})
    assert status == 416

    assert _get(f"{base}/api/resolve?name=tiny.mp4&size=10240")[0] == 200
    assert _get(f"{base}/api/resolve?name=tiny.mp4&size=1")[0] == 404
    assert _get(base + "/web/../serve.py")[0] == 404


def test_plan_and_take_lifecycle(server):
    base, clip = server
    graph = json.loads(_get(base + "/api/graph/first-light")[2])

    status, planned = _post(base + "/api/plan", graph)
    assert status == 200 and "PLAN first-light" in planned["text"]
    assert _post(base + "/api/plan", {"graph": graph})[1]["plan"] == planned["plan"]
    status, refused = _post(base + "/api/plan", dict(graph, edges=graph["edges"] + [["clip.media", "fx.video"]]))
    assert status == 400 and refused["problems"]

    status, opened = _post(base + "/api/take/open", {"graph": graph, "clip_id": clip_id_for(clip), "meta": {"ua": "test"}})
    assert status == 200
    take_id = opened["take_id"]

    def t(epoch, ticks):
        return {"clock": "media", "epoch": epoch, "ticks": ticks, "timebase": "1/90000"}

    status, ok = _post(f"{base}/api/take/{take_id}/events",
                       {"events": [{"kind": "play", "t": t(0, 0)},
                                   {"kind": "epoch", "epoch": 1, "reason": "seek", "t": t(1, 0)}]})
    assert status == 200 and ok["accepted"] == 2
    status, _ = _post(f"{base}/api/take/{take_id}/events", {"events": [{"kind": "midi", "t": t(0, 5), "cc": 74, "value": 9}]})
    assert status == 409
    assert _post(f"{base}/api/take/{take_id}/close", {"summary": {"p95": 11}})[0] == 200

    loaded = json.loads(_get(f"{base}/api/take/{take_id}")[2])
    assert loaded["take"]["meta"]["clip_name"] == "tiny.mp4"
    assert [e["kind"] for e in loaded["events"]] == ["play", "epoch"]


def test_recordings_are_saved_into_the_library(server):
    base, clip = server
    body = b"\x1aE\xdf\xa3" + bytes(2048)
    upload = urllib.request.Request(base + "/api/recordings?name=piano%20take%21", data=body, method="POST",
                                    headers={"Content-Type": "video/webm;codecs=vp9"})
    with urllib.request.urlopen(upload, timeout=10) as response:
        saved = json.loads(response.read())
    path = Path(saved["path"])
    assert path.parent == (clip.parent / "arsenal-renders").resolve()
    assert path.name.endswith(" piano-take.webm") and path.read_bytes() == body and saved["bytes"] == len(body)
    assert saved["clip_id"] == clip_id_for(path)
    refused = urllib.request.Request(base + "/api/recordings", data=b"x", method="POST",
                                     headers={"Content-Type": "text/plain"})
    try:
        urllib.request.urlopen(refused, timeout=10)
        raise AssertionError("a text/plain upload should be refused")
    except urllib.error.HTTPError as error:
        assert error.code == 415
