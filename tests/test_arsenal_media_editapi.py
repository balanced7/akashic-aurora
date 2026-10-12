"""The editor's routes (/api/edit/...) over HTTP against a First Light server on a free port: a drop resolved by name
and size, Range-served video and demuxed tracks, peaks, shots, keyframes, cut plans, projects with one writer by
revision (two PUTs on one rev: one 200, one 409), and a render job that lands in <library root>/aurora-edits/.

Routes whose primitive is not built yet answer 503 and their test skips with that reason. Fixtures are synthetic
(testsrc2 + two titled sine tracks) and live in a temporary library root; state is isolated with ARSENAL_MEDIA_STATE."""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from arsenal.media import edit, ff  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402
from test_arsenal_media_edit import FAST, make_clip  # noqa: E402


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    return make_clip(tmp_path_factory.mktemp("editapi_src") / "drop me.mkv")


@pytest.fixture()
def srv(tmp_path, monkeypatch, source):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    library = tmp_path / "library"
    library.mkdir()
    clip = library / source.name
    shutil.copy2(source, clip)
    app = App([str(library)], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    server = Server(0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield SimpleNamespace(port=server.server_address[1], app=app, clip=clip, library=library, tmp=tmp_path)
    svc = getattr(app, "edit_service", None)
    if svc:
        svc.jobs.wait_idle(60)
    server.shutdown()
    server.server_close()


def call(srv, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=60)
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    conn.request(method, path, body=raw, headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    ctype = resp.getheader("Content-Type") or ""
    parsed = json.loads(data or b"null") if ctype.startswith("application/json") else data
    return resp.status, dict(resp.getheaders()), parsed


def drop(srv):
    st = srv.clip.stat()
    status, _, reply = call(srv, "POST", "/api/edit/import",
                            {"name": srv.clip.name, "size": st.st_size, "lastModified": int(st.st_mtime * 1000)})
    assert status == 200, reply
    return reply


def wait_jobs(srv, mid, kinds, timeout=45.0):
    deadline = time.monotonic() + timeout
    while True:
        status, _, reply = call(srv, "GET", f"/api/edit/media/{mid}")
        assert status == 200, reply
        jobs = reply["jobs"]
        if all(jobs[k] not in ("queued", "running") for k in kinds) or time.monotonic() > deadline:
            return jobs
        time.sleep(0.1)


def skip_if_not_built(state: str) -> None:
    if "not built yet" in state:
        pytest.skip(state)


# --------------------------------------------------------------------------------------------- media

def test_a_drop_resolves_by_name_and_size_without_copying(srv):
    reply = drop(srv)
    media = reply["media"]
    assert media["path"] == str(srv.clip.resolve()) and media["tracks"] == 2
    assert [t["label"] for t in media["audio"]] == ["Voice", "Game"]
    assert set(reply["jobs"]) == {"demux", "peaks", "shots"}
    base = f"/api/edit/media/{media['id']}"
    assert media["urls"]["audio"] == [f"{base}/audio/0", f"{base}/audio/1"]
    assert sorted(p.name for p in srv.library.iterdir()) == [srv.clip.name]          # nothing copied beside it
    status, _, listed = call(srv, "GET", "/api/edit/media")
    assert status == 200 and [m["id"] for m in listed["media"]] == [media["id"]]


def test_an_unknown_drop_is_404_with_a_hint_and_a_path_import_works(srv, source):
    status, _, reply = call(srv, "POST", "/api/edit/import", {"name": "nowhere.mp4", "size": 123, "lastModified": 0})
    assert status == 404 and "library root" in reply["hint"] and reply["roots"] == [str(srv.library.resolve())]
    status, _, reply = call(srv, "POST", "/api/edit/import", {"name": "x"})
    assert status == 400
    status, _, reply = call(srv, "POST", "/api/edit/import", {"path": str(source)})
    assert status == 200 and reply["media"]["path"] == str(source.resolve())
    status, _, reply = call(srv, "POST", "/api/edit/import", {"path": str(srv.tmp / "missing.mp4")})
    assert status == 404


def test_video_is_served_with_range(srv):
    mid = drop(srv)["media"]["id"]
    size = srv.clip.stat().st_size
    status, headers, body = call(srv, "GET", f"/api/edit/media/{mid}/video", headers={"Range": "bytes=100-299"})
    assert status == 206 and len(body) == 200 and headers["Content-Range"] == f"bytes 100-299/{size}"
    assert headers["Content-Type"] == "video/x-matroska"
    assert body == srv.clip.read_bytes()[100:300]
    status, _, _ = call(srv, "GET", "/api/edit/media/0123456789abcdef/video")
    assert status == 404


def test_demuxed_tracks_and_peaks(srv):
    mid = drop(srv)["media"]["id"]
    jobs = wait_jobs(srv, mid, ("demux", "peaks"))
    skip_if_not_built(jobs["demux"])
    assert jobs["demux"] == "done", jobs
    for n in (0, 1):
        status, headers, body = call(srv, "GET", f"/api/edit/media/{mid}/audio/{n}", headers={"Range": "bytes=0-"})
        assert status == 206 and headers["Content-Type"].startswith("audio/") and len(body) > 1000
    status, _, reply = call(srv, "GET", f"/api/edit/media/{mid}/audio/7")
    assert status == 404
    skip_if_not_built(jobs["peaks"])
    assert jobs["peaks"] == "done", jobs
    status, _, wave = call(srv, "GET", f"/api/edit/media/{mid}/peaks/1")
    assert status == 200 and wave["sample_rate"] == 48000 and wave["spp"] == 512
    assert len(wave["data"]) == 2 * wave["length"] and wave["length"] >= 4.0 * 48000 // 512
    assert all(-1.0 <= v <= 1.0 for v in wave["data"]) and max(wave["data"]) > 0.05
    status, _, media = call(srv, "GET", f"/api/edit/media/{mid}")
    assert all("start_s" in t for t in media["media"]["audio"])


def test_shots_keyframes_and_cutplan(srv):
    mid = drop(srv)["media"]["id"]
    status, _, reply = call(srv, "GET", f"/api/edit/media/{mid}/keyframes")
    assert status == 200 and reply["keyframes"][0] == pytest.approx(0.0, abs=1e-3) and len(reply["keyframes"]) >= 7
    status, _, plan = call(srv, "GET", f"/api/edit/media/{mid}/cutplan?start=1.0&end=2.0")
    if status == 503:
        pytest.skip(plan["error"])
    assert status == 200 and plan["mode_suggested"] in ("copy", "smart", "exact")
    status, _, plan = call(srv, "GET", f"/api/edit/media/{mid}/cutplan?start=x&end=2")
    assert status == 400
    jobs = wait_jobs(srv, mid, ("shots",))
    skip_if_not_built(jobs["shots"])
    status, _, shots = call(srv, "GET", f"/api/edit/media/{mid}/shots")
    assert status == 200 and isinstance(shots["cuts"], list)


# --------------------------------------------------------------------------------------------- projects

def test_projects_one_writer_by_revision(srv):
    status, _, reply = call(srv, "POST", "/api/edit/projects", {"name": "review"})
    assert status == 201
    doc = reply["project"]
    pid = doc["id"]
    status, _, listed = call(srv, "GET", "/api/edit/projects")
    assert [p["id"] for p in listed["projects"]] == [pid]
    status, _, reply = call(srv, "PUT", f"/api/edit/projects/{pid}", {"project": dict(doc, name="review 2")})
    assert status == 200 and reply["project"]["rev"] == 2
    status, _, reply = call(srv, "PUT", f"/api/edit/projects/{pid}", {"project": dict(doc, name="stale")})
    assert status == 409 and reply["project"]["rev"] == 2 and reply["project"]["name"] == "review 2"

    current = reply["project"]
    gate, codes = threading.Barrier(2), []

    def writer(name):
        gate.wait()
        codes.append(call(srv, "PUT", f"/api/edit/projects/{pid}", {"project": dict(current, name=name)})[0])

    threads = [threading.Thread(target=writer, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    assert sorted(codes) == [200, 409]
    assert call(srv, "GET", f"/api/edit/projects/{pid}")[2]["project"]["rev"] == 3


def test_put_refuses_an_invalid_timeline_and_a_foreign_origin(srv):
    mid = drop(srv)["media"]["id"]
    doc = call(srv, "POST", "/api/edit/projects", {"name": "bad"})[2]["project"]
    clip = {"id": "c1", "media_id": mid, "lane": "V1", "src_in": 1.0, "src_out": 9.0, "at": 0.0,
            "audio": [{"src_track": 0, "lane": "A1", "gain_db": 0.0, "mute": False}]}
    status, _, reply = call(srv, "PUT", f"/api/edit/projects/{doc['id']}", {"project": dict(doc, clips=[clip])})
    assert status == 400 and any("past the media's end" in p for p in reply["problems"])
    status, _, reply = call(srv, "POST", "/api/edit/projects", {"name": "x"}, headers={"Origin": "http://evil.example"})
    assert status == 403
    assert call(srv, "GET", "/api/edit/projects/20990101-000000-abcdef")[0] == 404
    assert call(srv, "GET", "/api/edit/nothing")[0] == 404


def test_malformed_bodies_and_args_are_400_not_500(srv):
    mid = drop(srv)["media"]["id"]
    doc = call(srv, "POST", "/api/edit/projects", {"name": "shapes"})[2]["project"]
    for change in ({"settings": [1, 2]}, {"markers": 5}, {"clips": {"a": 1}}, {"lanes": "V1"}):
        status, _, reply = call(srv, "PUT", f"/api/edit/projects/{doc['id']}", {"project": dict(doc, **change)})
        assert status == 400 and reply["problems"], (change, reply)
    assert call(srv, "GET", f"/api/edit/projects/{doc['id']}")[2]["project"]["rev"] == 1
    for bad in ("nan", "inf", "-inf"):
        status, _, reply = call(srv, "GET", f"/api/edit/media/{mid}/cutplan?start={bad}&end=1")
        assert status == 400 and "number of seconds" in reply["error"]


def test_the_console_keeps_editor_errors_and_drops_its_polls(capsys):
    from arsenal.serve import Handler
    for code in ("200", "206", "404", "500"):
        Handler.log_message(SimpleNamespace(path="/api/edit/media/0123456789abcdef"), '"%s" %s %s',
                            "GET /api/edit/media/0123456789abcdef HTTP/1.1", code, "-")
    logged = capsys.readouterr().err
    assert " 404 " in logged and " 500 " in logged and " 200 " not in logged and " 206 " not in logged


def test_presets_list_the_export_lane(srv):
    status, _, reply = call(srv, "GET", "/api/edit/presets")
    if status == 503:
        pytest.skip(reply["error"])
    ids = [p["id"] for p in reply["presets"]]
    assert status == 200 and ids and not any(i.startswith("alpha_") for i in ids)


def test_render_job_lands_in_aurora_edits(srv, monkeypatch):
    monkeypatch.setattr(edit, "presets", lambda: {"test_x264": dict(FAST)})     # a fast preset; the route is the test
    media = drop(srv)["media"]
    doc = call(srv, "POST", "/api/edit/projects",
               {"name": "render me", "settings": {"fps": 30, "width": 320, "height": 240}})[2]["project"]
    doc, _ = edit.add_clip(doc, edit.get_media(media["id"]), src_in=0.5, src_out=2.0)
    doc, _ = edit.add_clip(doc, edit.get_media(media["id"]), src_in=2.5, src_out=3.5)
    doc = edit.set_lane_gain(doc, "A2", mute=True)
    status, _, reply = call(srv, "PUT", f"/api/edit/projects/{doc['id']}", {"project": doc})
    assert status == 200, reply
    status, _, reply = call(srv, "POST", f"/api/edit/projects/{doc['id']}/render", {"preset": "nope"})
    assert status == 400
    status, _, reply = call(srv, "POST", f"/api/edit/projects/{doc['id']}/render", {"preset": "test_x264"})
    assert status == 202 and reply["job"]["state"] in ("queued", "running")
    jid = reply["job"]["id"]
    deadline = time.monotonic() + 45
    while True:
        status, _, job = call(srv, "GET", f"/api/edit/jobs/{jid}")
        assert status == 200
        if job["state"] in ("done", "error") or time.monotonic() > deadline:
            break
        time.sleep(0.1)
    assert job["state"] == "done", job
    out = Path(job["result"]["path"])
    assert out.parent == srv.library.resolve() / "aurora-edits" / "render me" and out.is_file()
    assert job["result"]["duration_ok"] and job["progress"] == 1.0
    assert call(srv, "GET", "/api/edit/jobs/j999-abcdef")[0] == 404


def test_a_dropped_browser_connection_prints_no_traceback(capsys):
    """The editor's monitor and lanes keep several media connections open; a browser dropping one between requests
    printed 'Exception occurred during processing of request' and a traceback (6 in a 30 s session)."""
    from arsenal.serve import Server
    for exc in (ConnectionAbortedError(10053, "aborted"), ConnectionResetError(10054, "reset"), BrokenPipeError()):
        try:
            raise exc
        except OSError:
            Server.handle_error(SimpleNamespace(), None, ("127.0.0.1", 50000))
    assert capsys.readouterr().err == ""
