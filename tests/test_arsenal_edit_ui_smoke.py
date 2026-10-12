"""First Light's Edit mode in headless Chrome against the real server (arsenal.serve + arsenal.media.editapi): the
browser half that tests/arsenal_edit_timeline.test.mjs cannot reach. Each scenario is one the 2026-10-12 review broke
live:

- a 409 reload that lands during a trim drag: letting go must not write the page's old copy over the other writer's;
- a save that lands during a drag: letting go keeps both the saved edit and the trim;
- after the server refused a save, Render refuses too (one PUT, no render job) instead of rendering the stale file;
- the Export panel says "QC clean" only when QC ran and found nothing;
- playback crosses a cut where the previous clip's computed end overshoots the next clip's rounded `at` (the
  integrator's 2026-10-12 browser proof stalled there);
- a source whose container clock starts at 1.4 s (an MPEG-TS remuxed to MKV) shows, at a timeline time, the frame
  of that file time: Chrome's currentTime counts on the container's clock, the document on the file's.

Fixture: a 4 s synthetic clip (testsrc2 + two titled sine tracks, as MKV and as an MP4 Chrome plays) in a temporary
library root; ARSENAL_MEDIA_STATE points at a temporary folder, so nothing touches the house state or Daniel's
recordings, and no real render runs. Skips when Playwright, or a Chrome or Chromium it can drive, is missing. About
16 s on the house machine."""
from __future__ import annotations

import http.client
import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.media import ff  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

sync_api = pytest.importorskip("playwright.sync_api")

CLIP = "ui smoke.mkv"
PLAY_CLIP = "ui smoke play.mp4"     # H.264 + AAC in MP4: what Chrome plays without asking
TS_CLIP = "ui smoke ts clock.mkv"  # an MPEG-TS remuxed with -copyts: its container clock starts at 1.4 s

# A drop from Explorer: the page sends name + size and the server finds the file in its library root.
DROP_JS = """async ([sel, files]) => {
  const dt = new DataTransfer();
  for (const f of files) dt.items.add(new File([new Uint8Array(f.size)], f.name, {lastModified: f.lastModified}));
  const el = document.querySelector(sel);
  const r = el.getBoundingClientRect();
  const opts = {bubbles: true, cancelable: true, dataTransfer: dt, clientX: r.left + r.width - 20, clientY: r.top + 40};
  for (const type of ['dragenter', 'dragover', 'drop']) el.dispatchEvent(new DragEvent(type, opts));
}"""

# Where the last clip's out edge sits on screen, and the timeline's zoom.
OUT_EDGE_JS = """(() => {
  const d = window.arsenalEdit.doc, v = window.arsenalEdit.view, c = d.clips[d.clips.length - 1];
  const r = document.querySelector('.ed-content').getBoundingClientRect();
  const row = document.querySelector('.ed-head-video').getBoundingClientRect();
  return {x: r.left + (c.at + c.src_out - c.src_in) * v.pxPerSec, y: row.top + row.height / 2, pps: v.pxPerSec};
})()"""


def make_clip(path: Path, seconds: float = 4.0) -> Path:
    ff.run(["-f", "lavfi", "-i", f"testsrc2=s=320x240:r=30:d={seconds}",
            "-f", "lavfi", "-i", f"sine=f=440:sample_rate=48000:d={seconds}",
            "-f", "lavfi", "-i", f"sine=f=1000:sample_rate=48000:d={seconds}",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast", "-g", "15",
            "-bf", "0", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
            "-metadata:s:a:0", "title=Voice", "-metadata:s:a:1", "title=Game", "-y", str(path)])
    return path


def make_ts_clock_clip(path: Path, scratch: Path) -> Path:
    """H.264 + AAC through MPEG-TS (its muxer starts the container clock at 1.4 s), remuxed to MKV keeping that clock."""
    ts = scratch / "ts clock.ts"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=4", "-f", "lavfi", "-i", "sine=f=440:sample_rate=48000:d=4",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", "-bf", "0",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-f", "mpegts", "-y", str(ts)])
    ff.run(["-copyts", "-i", str(ts), "-map", "0", "-c", "copy", "-y", str(path)])
    return path


@pytest.fixture(scope="module")
def srv(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    tmp = tmp_path_factory.mktemp("edit_ui")
    library = tmp / "library"
    library.mkdir()
    clip = make_clip(library / CLIP)
    make_clip(library / PLAY_CLIP)
    make_ts_clock_clip(library / TS_CLIP, tmp)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp / "state"))
        app = App([str(library)], takes_root=tmp / "takes", performance_root=tmp / "perf")
        server = Server(0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield SimpleNamespace(port=server.server_address[1], clip=clip)
        finally:
            svc = getattr(app, "edit_service", None)
            if svc:
                svc.jobs.wait_idle(60)
            server.shutdown()
            server.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = None
        for kwargs in ({"channel": "chrome"}, {}):
            try:
                b = p.chromium.launch(headless=True, **kwargs)
                break
            except Exception:  # no such channel or no downloaded browser: try the next, else skip
                continue
        if b is None:
            pytest.skip("Playwright has no Chrome or Chromium to drive")
        yield b
        b.close()


def call(srv, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=30)
    conn.request(method, path, body=None if body is None else json.dumps(body).encode("utf-8"),
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read() or b"null")
    conn.close()
    return resp.status, data


def server_doc(srv, pid):
    status, reply = call(srv, "GET", f"/api/edit/projects/{pid}")
    assert status == 200, reply
    return reply["project"]


def wait(page, js, timeout=20.0, what=""):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.evaluate(js):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"timed out waiting for {what or js}")


def fresh_page(browser, srv, clips: int, name: str = CLIP):
    """Edit mode on a new project with `clips` copies of the fixture dropped on the timeline, saved."""
    page = browser.new_context(viewport={"width": 1400, "height": 900}).new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{srv.port}/first-light")
    page.evaluate("localStorage.setItem('arsenal.firstlight.mode', 'edit')")
    page.reload()
    wait(page, "window.arsenalEdit && window.arsenalEdit.pid", what="a project")
    first = page.evaluate("window.arsenalEdit.pid")
    page.click(".ed-toolbar >> text=New")
    wait(page, f"window.arsenalEdit.pid && window.arsenalEdit.pid !== {json.dumps(first)}", what="the new project")
    st = (srv.clip.parent / name).stat()
    info = {"name": name, "size": st.st_size, "lastModified": int(st.st_mtime * 1000)}
    page.evaluate(DROP_JS, [".ed-scroll", [info] * clips])
    wait(page, f"window.arsenalEdit.doc.clips.length === {clips}", what=f"{clips} clips")
    wait(page, "window.arsenalEdit.stats().save.status === 'saved'", what="the first save")
    return page, page.evaluate("window.arsenalEdit.pid"), errors


def puts_and_renders(page):
    seen = {"PUT": 0, "render": 0}

    def on_request(r):
        if r.method == "PUT" and "/api/edit/projects/" in r.url:
            seen["PUT"] += 1
        if r.method == "POST" and r.url.endswith("/render"):
            seen["render"] += 1
    page.on("request", on_request)
    return seen


def test_a_409_during_a_trim_drag_keeps_the_other_writers_copy(browser, srv):
    page, pid, errors = fresh_page(browser, srv, 2)
    page.evaluate("window.arsenalEdit.seek(1)")
    page.locator(".ed-scroll").focus()
    page.keyboard.press("s")                                 # a split the page saves 600 ms later
    theirs = server_doc(srv, pid)
    theirs["name"] = "named by the CLI"
    status, reply = call(srv, "PUT", f"/api/edit/projects/{pid}", {"project": theirs})
    assert status == 200, reply
    their_rev = reply["project"]["rev"]
    edge = page.evaluate(OUT_EDGE_JS)
    page.mouse.move(edge["x"] - 1, edge["y"])
    page.mouse.down()
    page.mouse.move(edge["x"] - edge["pps"], edge["y"], steps=5)   # trimming 1 s off the last clip
    wait(page, "window.arsenalEdit.stats().save.conflicts === 1", 5, "the 409")
    page.wait_for_timeout(300)
    page.mouse.up()
    page.wait_for_timeout(1200)                              # longer than the save debounce
    after = server_doc(srv, pid)
    assert (after["rev"], after["name"], len(after["clips"])) == (their_rev, "named by the CLI", 2), \
        "letting go of the drag wrote the page's old copy over the other writer's"
    shown = page.evaluate("[window.arsenalEdit.doc.name, window.arsenalEdit.doc.clips.length]")
    assert shown == ["named by the CLI", 2]
    assert "changed elsewhere - reloaded" in page.locator(".ed-banner").inner_text()
    assert not errors
    page.context.close()


def test_a_save_landing_mid_drag_keeps_both_edits(browser, srv):
    page, pid, errors = fresh_page(browser, srv, 1)
    page.evaluate("window.arsenalEdit.seek(1)")
    page.locator(".ed-scroll").focus()
    page.keyboard.press("s")
    saves = page.evaluate("window.arsenalEdit.stats().save.saves")
    edge = page.evaluate(OUT_EDGE_JS)
    page.mouse.move(edge["x"] - 1, edge["y"])
    page.mouse.down()
    page.mouse.move(edge["x"] - edge["pps"], edge["y"], steps=5)
    wait(page, f"window.arsenalEdit.stats().save.saves > {saves}", 5, "the split's save")  # lands mid-drag
    page.mouse.up()
    wait(page, "window.arsenalEdit.stats().save.status === 'saved' && !window.arsenalEdit.stats().save.dirty", 5)
    doc = server_doc(srv, pid)
    clips = sorted(doc["clips"], key=lambda c: c["at"])
    assert len(clips) == 2, "the split saved during the drag is kept"
    assert abs(clips[-1]["src_out"] - 3.0) < 0.05, f"the trim is kept: src_out {clips[-1]['src_out']}"
    assert not errors
    page.context.close()


def test_render_refuses_after_a_refused_save(browser, srv):
    page, pid, errors = fresh_page(browser, srv, 1)
    seen = puts_and_renders(page)
    rev = server_doc(srv, pid)["rev"]
    page.evaluate("""(() => { const d = JSON.parse(JSON.stringify(window.arsenalEdit.doc));
        d.clips[0].src_out = 999; window.arsenalEdit.commit(d); })()""")
    wait(page, "window.arsenalEdit.stats().save.status === 'not saved: refused'", 5, "the refusal")
    before = dict(seen)
    page.click(".ed-export button")
    wait(page, "/not rendered|Rendered|render failed/.test(document.querySelector('.ed-export-status').textContent)",
         10, "the Export panel's answer")
    text = page.locator(".ed-export-status").inner_text()
    assert text.startswith("not rendered:") and "refused" in text, text
    assert seen["PUT"] - before["PUT"] <= 1, f"{seen['PUT'] - before['PUT']} PUTs after Render"
    assert seen["render"] == 0, "a render job was started for a revision the page no longer shows"
    assert server_doc(srv, pid)["rev"] == rev
    assert not errors
    page.context.close()


def test_export_panel_says_qc_clean_only_when_qc_ran_clean(browser, srv):
    page, pid, errors = fresh_page(browser, srv, 1)
    replies = iter([
        {"path": "X:\\out.mp4", "duration_s": 3.2, "duration_expected_s": 4.0, "duration_ok": False,
         "qc": {"error": "RuntimeError: ffmpeg exited 1"}},
        {"path": "X:\\out.mp4", "duration_s": 4.0, "duration_expected_s": 4.0, "duration_ok": True,
         "qc": {"ok": True, "problems": [], "I": -18.8, "TP": -12.0, "duration_s": 4.0}},
    ])
    current = {}

    def render(route):
        current["result"] = next(replies)
        route.fulfill(status=202, content_type="application/json", body=json.dumps({"job": {"id": "j1-ui", "rev": 1}}))

    page.route("**/api/edit/projects/*/render", render)
    page.route("**/api/edit/jobs/j1-ui", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(
        {"id": "j1-ui", "state": "done", "progress": 1, "error": None, "result": current["result"]})))
    status = page.locator(".ed-export-status")
    page.click(".ed-export button")
    wait(page, "/^Rendered/.test(document.querySelector('.ed-export-status').textContent)", 10, "the first render")
    assert "QC failed to run" in status.inner_text() and "QC clean" not in status.inner_text()
    assert status.get_attribute("data-kind") == "warn"
    page.click(".ed-export button")
    wait(page, "/QC clean/.test(document.querySelector('.ed-export-status').textContent)", 10, "the second render")
    assert status.get_attribute("data-kind") == "ok"
    assert status.inner_text().startswith("Rendered revision 1 to")
    assert not errors
    page.context.close()


def test_playback_crosses_a_cut_where_the_previous_clip_ends_a_nanosecond_late(browser, srv):
    """The 2026-10-12 browser proof: after a split and a deleted middle, the next clip sat at a rounded `at`
    (11.066666666) a nanosecond before the previous clip's computed end, and playback stalled on the cut, finding the
    old clip again on every frame. Here the same overshoot, built directly, must play straight through."""
    page, pid, errors = fresh_page(browser, srv, 2, PLAY_CLIP)
    if not page.evaluate("document.createElement('video').canPlayType('video/mp4; codecs=\"avc1.42E01E\"')"):
        pytest.skip("this browser plays no H.264")
    page.evaluate("""(() => { const d = JSON.parse(JSON.stringify(window.arsenalEdit.doc));
        const [a, b] = d.clips.sort((x, y) => x.at - y.at);
        Object.assign(a, {src_in: 0.4666666666666667, src_out: 1.5333333333333334, at: 0});
        Object.assign(b, {src_in: 0, src_out: 2, at: 1.066666666});
        window.arsenalEdit.commit(d); })()""")
    wait(page, "window.arsenalEdit.stats().save.status === 'saved' && !window.arsenalEdit.stats().save.dirty", 5)
    assert page.evaluate("(() => { const c = window.arsenalEdit.doc.clips; return c[0].src_out - c[0].src_in > c[1].at; })()")
    page.evaluate("window.arsenalEdit.seek(0.6)")
    page.wait_for_timeout(500)
    page.locator(".ed-scroll").focus()
    page.keyboard.press(" ")
    wait(page, "window.arsenalEdit.playback.time > 1.4", 6, "playback past the cut at 1.067 s")
    page.keyboard.press(" ")
    assert page.evaluate("window.arsenalEdit.stats().playback.boundaries") <= 2, "the cut was crossed again and again"
    assert not errors
    page.context.close()


def test_a_source_whose_container_clock_starts_late_shows_the_frame_of_its_file_time(browser, srv):
    """Every src time in the document is a file time (seconds from the file's start, where edit.render's -ss cuts);
    Chrome's currentTime counts on the container's clock, which starts at 1.4 s here. The playhead at 2.0 s must put
    the element at 3.4 s; before the house clock fix the page set 2.0 and showed the frame at file time 0.6."""
    page, pid, errors = fresh_page(browser, srv, 1, TS_CLIP)
    if not page.evaluate("document.createElement('video').canPlayType('video/x-matroska; codecs=\"avc1.42E01E\"')"
                         " || document.createElement('video').canPlayType('video/mp4; codecs=\"avc1.42E01E\"')"):
        pytest.skip("this browser plays no H.264")
    mid = page.evaluate("window.arsenalEdit.doc.clips[0].media_id")
    wait(page, f"(window.arsenalEdit.media({json.dumps(mid)}) || {{}}).media", what="the media record")
    assert page.evaluate(f"window.arsenalEdit.media({json.dumps(mid)}).media.container_start_s") == \
        pytest.approx(1.4, abs=0.01)
    page.evaluate("window.arsenalEdit.seek(2.0)")
    shown = """(() => { const v = document.querySelector('.ed-video.active');
        return v && v.readyState >= 2 && !v.seeking ? v.currentTime : null; })()"""
    wait(page, f"{shown} !== null", what="the monitor to settle")
    assert page.evaluate(shown) == pytest.approx(3.4, abs=0.5 / 30)
    assert page.evaluate("window.arsenalEdit.playback.time") == pytest.approx(2.0, abs=1e-6)
    page.locator(".ed-scroll").focus()
    page.keyboard.press(" ")                                 # playing reads the element back through the same edge
    wait(page, "window.arsenalEdit.playback.time > 2.2", 6, "playback to move")
    page.keyboard.press(" ")
    t, ct = page.evaluate("[window.arsenalEdit.playback.time, document.querySelector('.ed-video.active').currentTime]")
    assert t < 3.5 and ct - t == pytest.approx(1.4, abs=0.1), (t, ct)
    assert not errors
    page.context.close()
