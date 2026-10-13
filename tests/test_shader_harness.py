"""Pins for the shader harness (arsenal/shaders/serve.py, render.py, headless.mjs): the lab server, the receipts, the verbs,
and the SwiftShader rule that keeps every frame off this host's GPU.

WHY THESE PINS. The harness renders hundreds of strangers' shaders on a machine with an AMD display-driver crash history,
and it serves a corpus of other people's code that must never leave this machine. So the tests guard four promises:

  * the server listens on 127.0.0.1 only, refuses port 8793 (Daniel's server), answers loopback Host names only, and
    serves nothing outside its roots however the path is spelled;
  * a renderer string that is not SwiftShader, or that names hardware, renders nothing: judge_renderer (Python) and
    judgeRenderer (headless.mjs) are twins, and both are run over the same strings here;
  * a receipt has one shape, and "ok" in it means every frame was written on a software renderer;
  * the verbs parse their arguments the way the contract names them.

And the house rules the harness keeps on the way: the probe page refuses hardware before any GL work, pictures of a
corpus shader never land outside state/, the driver loads nothing but the lab server on loopback, a burst stays under
three minutes counting launch, relaunch and shutdown, and the house lock is released only after our Chrome is dead.

No test launches Chrome or takes the house GPU lock (one test takes a lock of its own in a temp directory): the live
path is proved by running the verbs (see render.py's docstring). Every shader here is synthetic; the real corpus lives
only under state/ and no test reads it.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from arsenal.shaders import cli
from arsenal.shaders import corpus as C
from arsenal.shaders import render as R
from arsenal.shaders import serve as S

ROOT = Path(__file__).resolve().parents[1]
HEADLESS = ROOT / "arsenal" / "shaders" / "headless.mjs"
GPU_LOCK = ROOT / "arsenal" / "lanes" / "gpu_lock.mjs"
PROBE = ROOT / "arsenal" / "web" / "shaderlab" / "_harness_probe.html"
RUNTIME = ROOT / "arsenal" / "web" / "shaderlab" / "toy-runtime.js"
STATE = ROOT / "state"
NOT_STATE = ROOT / "design" / "vfx-sketches" / "never-written-by-a-test"   # tracked territory; no test may write here
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

SWIFTSHADER = "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)"
AMD = "ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)"
SECRET = "TOPSECRET-not-for-the-lab"

# (renderer string, should it render?) -- the same table drives both twins.
RENDERERS = [
    (SWIFTSHADER, True),
    ("ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0) (0x0000C0DE)), SwiftShader driver)", True),
    ("Google SwiftShader", True),
    (AMD, False),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)", False),
    ("ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)", False),
    ("SwiftShader, but on an AMD Radeon", False),          # a mixed string is hardware until proved otherwise
    ("ANGLE (Google, SwiftShader via Direct3D11)", False),
    ("WebKit WebGL", False),                               # a masked renderer proves nothing
    ("", False),
    ("   ", False),
    (None, False),
]


def _shader(sid="abcDEF", name="Harness test", code=None, passes=None):
    code = code or "void mainImage(out vec4 o, in vec2 u) { o = vec4(u / iResolution.xy, 0.5, 1.0); }"
    passes = passes or [{"name": "Image", "type": "image", "code": code, "inputs": [],
                         "outputs": [{"id": "4dfGRr", "channel": 0}]}]
    return {"ver": "0.1", "info": {"id": sid, "name": name, "username": "someone", "date": "1700000000", "likes": 1,
                                   "viewed": 2, "tags": [], "description": ""}, "renderpass": passes}


def _png(path: Path, flat: bool = False) -> Path:
    from PIL import Image
    im = Image.new("RGB", (8, 4), (20, 30, 40))
    if not flat:
        for x in range(8):
            im.putpixel((x, 0), (x * 30, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


# ------------------------------------------------------------------------------------------------- the lab server
@pytest.fixture()
def lab(tmp_path):
    """A server on an ephemeral loopback port over temp roots, with a secret file just outside them."""
    (tmp_path / "secret.txt").write_text(SECRET, encoding="utf-8")
    lab_dir = tmp_path / "lab"
    lab_dir.mkdir(parents=True)
    (lab_dir / "render.html").write_text("<!doctype html><title>r</title>", encoding="utf-8")
    lib_dir = tmp_path / "glsl"          # the house library's stand-in (the real one is arsenal/web/glsl/)
    (lib_dir / "sdf").mkdir(parents=True)
    # Served bytes only: plain comments, so the fixture shares no token run with any corpus shader (licence line).
    (lib_dir / "sdf.glsl").write_text("// house library route probe: a flat file\n", encoding="utf-8")
    (lib_dir / "sdf" / "box.glsl").write_text("// house library route probe: a nested file\n", encoding="utf-8")
    corpus = tmp_path / "corpus"
    C.save_shader(_shader("abcDEF"), corpus)
    (corpus / "media").mkdir()
    (corpus / "media" / "0123abcd.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(64)))
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    (jobs / "local-x-0123456789.json").write_text(json.dumps(_shader()), encoding="utf-8")
    server = S.start_in_thread(0, lab=lab_dir, lib=lib_dir, corpus=corpus, jobs=jobs)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _get(server, path, method="GET", headers=None):
    """A raw request: http.client sends the path exactly as written (no client-side normalisation of '..')."""
    conn = http.client.HTTPConnection(S.HOST, server.server_address[1], timeout=10)
    try:
        conn.request(method, path, headers=headers or {})
        res = conn.getresponse()
        return res.status, dict(res.getheaders()), res.read()
    finally:
        conn.close()


def test_server_binds_loopback_only(lab):
    assert lab.server_address[0] == "127.0.0.1"
    assert lab.base_url.startswith("http://127.0.0.1:")


@pytest.mark.parametrize("host,port", [("0.0.0.0", 8797), ("localhost", 8797), ("::1", 8797), ("192.168.1.10", 8797),
                                       ("", 8797)])
def test_validate_bind_refuses_any_address_but_127_0_0_1(host, port):
    with pytest.raises(S.BindRefused):
        S.validate_bind(host, port)


def test_port_8793_is_refused_everywhere():
    with pytest.raises(S.BindRefused, match="8793"):
        S.validate_bind("127.0.0.1", 8793)
    with pytest.raises(S.BindRefused):
        S.ShaderServer(8793)       # refused before any socket is opened
    with pytest.raises(S.BindRefused):
        S.probe(8793)              # not even a health probe touches Daniel's server
    with pytest.raises(ValueError):
        R.parse_port("8793")


def test_default_port_is_8797_and_allowed():
    assert S.DEFAULT_PORT == 8797
    S.validate_bind("127.0.0.1", S.DEFAULT_PORT)


def test_health_names_the_api_and_roots(lab):
    status, _, body = _get(lab, "/health")
    data = json.loads(body)
    assert status == 200 and data["api"] == S.SERVE_API
    assert "render.html" in data["lab_pages"]


@pytest.mark.parametrize("path,needle", [
    ("/lab/render.html", b"<title>r</title>"),
    ("/lib/sdf.glsl", b"a flat file"),
    ("/glsl/sdf.glsl", b"a flat file"),
    ("/lib/sdf/box.glsl", b"a nested file"),
    ("/glsl/sdf/box.glsl", b"a nested file"),
    ("/corpus/abcDEF/shader.json", b"Harness test"),
    ("/corpus/media/0123abcd.png", b"\x89PNG"),
    ("/jobs/local-x-0123456789.json", b"Harness test"),
])
def test_routes_serve_their_roots(lab, path, needle):
    status, headers, body = _get(lab, path)
    assert status == 200, (path, body[:200])
    assert needle in body
    assert headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.parametrize("path", [
    "/lab/../secret.txt",
    "/lab/%2e%2e/secret.txt",
    "/lab/..%2fsecret.txt",
    "/lab/..%5csecret.txt",
    "/lab/glsl/../../secret.txt",
    "/lab/./render.html",
    "/lab//render.html",
    "/lab/%2e%2e%2f%2e%2e%2fsecret.txt",
    "/lab/C:/Windows/win.ini",
    "/lab/render.html::$DATA",
    "/lab/render.html%00.png",
    "/lib/../../secret.txt",
    "/lib/%2e%2e/render.html",
    "/glsl/../secret.txt",
    "/glsl/%2e%2e/secret.txt",
    "/glsl/..%2fsecret.txt",
    "/glsl/sdf/../../secret.txt",
    "/glsl/C:/Windows/win.ini",
    "/glsl/sdf.glsl%00.png",
    "/glsl",
    "/glsl/",
    "/corpus/../secret.txt",
    "/corpus/abcDEF/../../secret.txt",
    "/corpus/abc/shader.json",               # not a Shadertoy id
    "/corpus/..%2f..%2fsecret.txt/shader.json",
    "/corpus/abcDEF/meta.json",              # only shader.json is served from a shader's directory
    "/corpus/abcDEF/image.glsl",
    "/corpus/media/..%2f..%2fsecret.txt",
    "/corpus/media/../../secret.txt",
    "/corpus/sets.json",
    "/corpus/harvests/x.json",
    "/jobs/../secret.txt",
    "/jobs/..%2fsecret.txt",
    "/jobs/local-x-0123456789.txt",
    "/secret.txt",
    "/etc/passwd",
])
def test_traversal_and_off_route_paths_are_refused(lab, path):
    status, _, body = _get(lab, path)
    assert status in (403, 404), (path, status)
    assert SECRET.encode() not in body


def test_a_symlink_out_of_a_root_is_refused(lab, tmp_path):
    link = Path(lab.roots["lab"]) / "escape.txt"
    try:
        os.symlink(tmp_path / "secret.txt", link)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symlinks")
    status, _, body = _get(lab, "/lab/escape.txt")
    assert status == 404 and SECRET.encode() not in body


@pytest.mark.parametrize("host,ok", [
    ("127.0.0.1", True), ("127.0.0.1:8797", True), ("localhost", True), ("LOCALHOST:8797", True), ("[::1]:8797", True),
    ("evil.example", False), ("evil.example:8797", False), ("127.0.0.1.evil.example", False),
    ("localhost.evil.example:80", False), ("192.168.1.10:8797", False),
])
def test_host_header_must_name_loopback(lab, host, ok):
    assert S.host_is_loopback(host) is ok
    status, _, _ = _get(lab, "/lab/render.html", headers={"Host": host})
    assert status == (200 if ok else 403)


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def test_server_is_read_only(lab, method):
    status, headers, _ = _get(lab, "/lab/render.html", method=method)
    assert status == 405 and "GET" in headers.get("Allow", "")


def test_head_has_no_body_and_range_is_honoured(lab):
    status, headers, body = _get(lab, "/corpus/media/0123abcd.png", method="HEAD")
    assert status == 200 and body == b"" and headers["Content-Length"] == "72"
    status, headers, body = _get(lab, "/corpus/media/0123abcd.png", headers={"Range": "bytes=8-11"})
    assert status == 206 and body == bytes(range(4)) and headers["Content-Range"] == "bytes 8-11/72"
    status, _, _ = _get(lab, "/corpus/media/0123abcd.png", headers={"Range": "bytes=500-"})
    assert status == 416


def test_safe_file_unit(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f.txt").write_text("x", encoding="utf-8")
    assert S.safe_file(tmp_path, "a/f.txt") == (tmp_path / "a" / "f.txt").resolve()
    for bad in ["", "/a/f.txt", "a/../a/f.txt", "a\\f.txt", "C:/x", "a//f.txt", "a/./f.txt", "a/f.txt\x00", "a"]:
        assert S.safe_file(tmp_path, bad) is None, bad


def test_base_for_never_reuses_a_server_over_other_roots(lab):
    """A lab server over a test's temp roots must not be mistaken for the real one: render starts a private server."""
    server, base = S.base_for(lab.server_address[1])
    try:
        assert server is not None and base != lab.base_url
        assert S.probe(server.server_address[1])["roots"]["corpus"] == str(C.CORPUS)
    finally:
        if server:
            server.shutdown()
            server.server_close()


def test_base_for_never_reuses_a_server_over_another_library(tmp_path):
    """Same lab, corpus and jobs, but a different house library: still not ours, so render starts a private server."""
    other = S.start_in_thread(0, lib=tmp_path)
    try:
        server, base = S.base_for(other.server_address[1])
        try:
            assert server is not None and base != other.base_url
            assert S.probe(server.server_address[1])["roots"]["lib"] == str(S.LIB)
        finally:
            if server:
                server.shutdown()
                server.server_close()
    finally:
        other.shutdown()
        other.server_close()


def test_the_house_library_is_arsenal_web_glsl_on_lib_and_glsl():
    """The house library moved to arsenal/web/glsl/ (build spec, ruling 1); /lib/ serves it and /glsl/ is its alias,
    the path modlib.js's own usage note fetches (/glsl/modlib.js, /glsl/index.json)."""
    assert S.LIB == ROOT / "arsenal" / "web" / "glsl"
    assert "/glsl/<file>" in S.ROUTES and "/lib/<file>" in S.ROUTES
    server = S.start_in_thread(0)
    try:
        assert Path(server.roots["lib"]) == S.LIB and server.health()["roots"]["lib"] == str(S.LIB)
        on_disk = (S.LIB / "modlib.js").read_bytes()
        for route in ("/lib/modlib.js", "/glsl/modlib.js"):
            status, headers, body = _get(server, route)
            assert status == 200 and body == on_disk, route
            assert headers["Content-Type"].startswith("text/javascript")
        status, _, _ = _get(server, "/lab/glsl/modlib.js")   # the old home is gone, and nothing serves it
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()


def test_the_serve_banner_says_who_the_server_is_for(lab):
    lines = S.banner(lab)
    assert any(S.HEADLESS_ONLY in line for line in lines)
    assert S.HEADLESS_ONLY == "for the headless driver; do not open in a browser"
    assert any("/glsl/" in line for line in lines)
    assert S.HEADLESS_ONLY in R.__doc__     # the render module's docstring says it of the serve verb too


# --------------------------------------------------------------------------------------- the SwiftShader rule
@pytest.mark.parametrize("renderer,ok", RENDERERS)
def test_judge_renderer_python(renderer, ok):
    got, reason = R.judge_renderer(renderer)
    assert got is ok
    assert (reason is None) is ok
    if not ok:
        with pytest.raises(R.NotSoftwareRenderer):
            R.assert_software_renderer(renderer)
    else:
        assert R.assert_software_renderer(renderer) == renderer


def _node(code: str):
    """Run an ES module in node; its last stdout line is JSON, returned parsed."""
    out = subprocess.run([NODE, "--input-type=module", "-e", code], capture_output=True, text=True, timeout=60,
                         cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _node_module(expr: str):
    """Evaluate an expression against headless.mjs's exports in node (importing it runs no CLI and no Chrome)."""
    url = HEADLESS.resolve().as_uri()
    return _node(f"import * as H from {json.dumps(url)}; console.log(JSON.stringify({expr}));")


@needs_node
def test_judge_renderer_twins_agree():
    strings = [r for r, _ in RENDERERS]
    got = _node_module(f"{json.dumps(strings)}.map((s) => H.judgeRenderer(s))")
    for (renderer, ok), js in zip(RENDERERS, got):
        assert js["ok"] is ok, renderer
        assert js["ok"] is R.judge_renderer(renderer)[0], renderer
    assert _node_module("H.HARDWARE_HINT.source") == R.HARDWARE_HINT.pattern


@needs_node
def test_driver_cli_check_renderer():
    out = subprocess.run([NODE, str(HEADLESS), "--check-renderer", AMD], capture_output=True, text=True, timeout=60)
    assert json.loads(out.stdout)["ok"] is False
    out = subprocess.run([NODE, str(HEADLESS), "--check-renderer", SWIFTSHADER], capture_output=True, text=True,
                         timeout=60)
    assert json.loads(out.stdout) == {"ok": True, "reason": None}


@needs_node
def test_driver_flags_force_swiftshader_and_its_own_profile():
    flags = _node_module("H.chromeFlags('PROFILE')")
    for required in ("--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--disable-d3d11",
                     "--remote-debugging-port=0", "--user-data-dir=PROFILE"):
        assert required in flags
    assert not any(f.startswith(("--use-gl=", "--enable-gpu", "--ignore-gpu-blocklist")) for f in flags)
    assert "--version" not in flags   # chrome.exe --version opens a visible window on Windows


@needs_node
def test_driver_and_python_share_their_constants():
    c = _node_module("{plan: H.PLAN_API, result: H.RESULT_API, exit: H.EXIT, burst: H.BURST_MS, "
                     "hold: H.LOCK_HOLD_MS, chrome: H.CHROME_EXE}")
    assert c["plan"] == R.PLAN_API and c["result"] == R.RESULT_API
    assert c["exit"]["refused"] == R.EXIT_REFUSED and c["exit"]["lock"] == R.EXIT_LOCK
    assert R.BURST_CAP_S * 1000 <= c["burst"] < 180_000          # GPU-LOCK.md: bursts under three minutes
    assert c["hold"] > c["burst"]
    assert c["chrome"] == r"C:\Program Files\Google\Chrome\Application\chrome.exe"


@needs_node
def test_driver_refuses_a_bad_plan_without_launching_anything(tmp_path):
    out = subprocess.run([NODE, str(HEADLESS)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 2
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"api": "something-else", "jobs": []}), encoding="utf-8")
    out = subprocess.run([NODE, str(HEADLESS), "--plan", str(plan), "--result", str(tmp_path / "r.json")],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 2 and not (tmp_path / "r.json").exists()


# ------------------------------------------------------------------------------- the probe page's own renderer gate
# The probe page's script, run in node against a fake WebGL2 context that reports a given renderer string and records
# every GL call. Nothing here reaches a GPU: there is no browser, only the page's own logic.
_PROBE_RUNNER = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";
const html = readFileSync(__PROBE__, "utf8");
const script = /<script>([\s\S]*?)<\/script>/.exec(html)[1];
const out = [];
for (const renderer of __RENDERERS__) {
  const calls = [];
  const consts = { VERTEX_SHADER: 0x8B31, FRAGMENT_SHADER: 0x8B30, COMPILE_STATUS: 0x8B81, LINK_STATUS: 0x8B82,
                   TRIANGLES: 4, NO_ERROR: 0, RENDERER: 0x1F01 };
  const gl = new Proxy({}, { get(_, name) {
    if (name in consts) return consts[name];
    return (...args) => {
      calls.push(String(name));
      if (name === "getExtension") return args[0] === "WEBGL_debug_renderer_info" ? { UNMASKED_RENDERER_WEBGL: 0x9246 } : null;
      if (name === "getParameter") return args[0] === 0x9246 || args[0] === 0x1F01 ? renderer : null;
      if (name === "getError") return 0;
      if (name === "getShaderParameter" || name === "getProgramParameter") return true;
      if (name === "getShaderInfoLog" || name === "getProgramInfoLog") return "";
      return {};
    };
  } });
  const canvas = { width: 0, height: 0, style: {}, getContext: () => gl, toDataURL: () => "data:image/png;base64,AA==" };
  const sandbox = { window: {}, location: { search: "?t=0,1&w=8&h=4" }, document: { getElementById: () => canvas },
                    URLSearchParams, performance, console, setTimeout: () => 0, fetch: () => new Promise(() => {}) };
  vm.runInNewContext(script, sandbox);
  const r = sandbox.window.__render;
  out.push({ renderer, done: r.done, ok: r.ok, refused: r.refused === true, errors: r.errors, frames: r.frames.length,
             gl_work: calls.filter((c) => /^(createShader|shaderSource|compileShader|createProgram|linkProgram|useProgram|drawArrays|clear)$/.test(c)) });
}
console.log(JSON.stringify(out));
"""


@needs_node
def test_probe_page_refuses_hardware_before_any_gl_work():
    """The probe page is served under /lab/, so a person could open it in an ordinary browser on this host's AMD GPU.
    It must refuse there before it compiles or draws anything, by the same rule as the two twins."""
    code = (_PROBE_RUNNER.replace("__PROBE__", json.dumps(str(PROBE)))
            .replace("__RENDERERS__", json.dumps([r for r, _ in RENDERERS])))
    for (renderer, ok), got in zip(RENDERERS, _node(code)):
        if ok:
            assert got["ok"] and not got["refused"] and got["frames"] == 2 and "drawArrays" in got["gl_work"], got
        else:
            assert got["done"] and not got["ok"] and got["refused"], got
            assert got["gl_work"] == [] and got["frames"] == 0, got
            assert any("refused" in e for e in got["errors"]), got


def test_probe_page_gate_is_the_twins_rule_and_comes_first():
    text = PROBE.read_text(encoding="utf-8")
    m = re.search(r"const HARDWARE_HINT = /(.+)/i;", text)
    assert m and m.group(1) == R.HARDWARE_HINT.pattern
    gate = text.index("judgeRenderer(result.renderer)")
    for gl_work in ("gl.compileShader(", "gl.linkProgram(", "gl.drawArrays("):
        assert gate < text.index(gl_work), gl_work
    assert S.HEADLESS_ONLY in text


# ------------------------------------------------------------------------------- what the driver agrees to load
def _url(port=51234, src="/corpus/abcDEF/shader.json", host="127.0.0.1", page="/lab/render.html", scheme="http"):
    base = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
    return f"{base}{page}?src={base}{src}&t=0&w=8&h=4&fps=60&media={base}/corpus/media/&budget=25000"


IN_STATE = str(STATE / "arsenal" / "shaders" / "renders" / "abcDEF")
DRIVER_JOBS = [  # (job, should the driver load it?)
    ({"url": _url(), "out_dir": IN_STATE, "prefix": ""}, True),
    ({"url": _url(), "out_dir": str(STATE / "arsenal" / "shaders" / "check" / "x"), "prefix": "abcDEF_"}, True),
    ({"url": _url(port=8793), "out_dir": IN_STATE}, False),                          # Daniel's server
    ({"url": _url(host="localhost"), "out_dir": IN_STATE}, False),                   # 127.0.0.1, spelled exactly
    ({"url": _url(host="evil.example"), "out_dir": IN_STATE}, False),
    ({"url": _url(host="192.168.1.10"), "out_dir": IN_STATE}, False),
    ({"url": _url(scheme="https"), "out_dir": IN_STATE}, False),
    ({"url": _url(port=None), "out_dir": IN_STATE}, False),                          # an explicit port, always
    ({"url": _url(page="/corpus/abcDEF/shader.json"), "out_dir": IN_STATE}, False),  # a lab page, nothing else
    ({"url": "http://user:pw@127.0.0.1:51234/lab/render.html", "out_dir": IN_STATE}, False),
    ({"url": "file:///C:/Windows/win.ini", "out_dir": IN_STATE}, False),
    ({"url": "not a url", "out_dir": IN_STATE}, False),
    ({"url": _url().replace("src=http://127.0.0.1:51234", "src=http://evil.example"), "out_dir": IN_STATE}, False),
    ({"url": _url().replace("media=http://127.0.0.1:51234", "media=http://evil.example"), "out_dir": IN_STATE}, False),
    ({"url": _url(), "out_dir": str(NOT_STATE)}, False),                             # a corpus picture in a tracked folder
    ({"url": _url(), "out_dir": str(NOT_STATE), "allow_tracked": True}, False),      # ... and no flag lets it
    ({"url": _url(), "out_dir": str(STATE / ".." / "design")}, False),
    ({"url": _url(), "out_dir": "state/arsenal/shaders/renders/x"}, False),          # absolute paths only
    ({"url": _url(), "out_dir": None}, False),
    ({"url": _url(), "out_dir": IN_STATE, "prefix": "../../design/x_"}, False),       # a prefix is a name, not a path
    ({"url": _url(src="/jobs/local-x-0123456789.json"), "out_dir": str(NOT_STATE), "allow_tracked": True}, True),
    ({"url": _url(src="/jobs/local-x-0123456789.json"), "out_dir": str(NOT_STATE)}, False),
    ({"url": _url(src="/jobs/local-x-0123456789.json"), "out_dir": str(NOT_STATE), "allow_tracked": "yes"}, False),
]


@needs_node
def test_driver_loads_only_the_lab_on_loopback_and_writes_only_under_state():
    got = _node_module(f"{json.dumps([j for j, _ in DRIVER_JOBS])}.map((j) => H.jobRefusal(j))")
    for (job, ok), why in zip(DRIVER_JOBS, got):
        assert (why is None) is ok, (job, why)
    assert {int(k) for k in _node_module("H.FORBIDDEN_PORTS")} == set(S.FORBIDDEN_PORTS)
    assert _node_module("H.STATE_ROOT").rstrip("\\/").lower() == str(STATE).lower()


@needs_node
def test_driver_refuses_a_plan_with_a_bad_job_before_the_lock_or_chrome(tmp_path):
    """A refused plan is answered before the GPU lock is taken or Chrome launched. The plan names a Chrome that does not
    exist, so even a driver that skipped the check could only fail on that, never render."""
    plan = tmp_path / "plan.json"
    jobs = [{"key": "aaaaaa", "url": _url(), "out_dir": IN_STATE, "prefix": "", "timeout_ms": 30000, "w": 8, "h": 4},
            {"key": "abcDEF", "url": _url(), "out_dir": str(NOT_STATE), "prefix": "", "timeout_ms": 30000, "w": 8,
             "h": 4}]
    plan.write_text(json.dumps({"api": R.PLAN_API, "label": "pytest", "lock_wait_ms": 0, "jobs": jobs,
                                "chrome": str(tmp_path / "no-chrome.exe")}), encoding="utf-8")
    result = tmp_path / "r.json"
    out = subprocess.run([NODE, str(HEADLESS), "--plan", str(plan), "--result", str(result)], capture_output=True,
                         text=True, timeout=60)
    assert out.returncode == R.EXIT_REFUSED, out.stdout + out.stderr
    r = json.loads(result.read_text(encoding="utf-8"))
    assert r["api"] == R.RESULT_API and "abcDEF" in r["refused"] and r["lock"] is None
    assert [j["status"] for j in r["jobs"]] == ["refused", "refused"]
    assert not NOT_STATE.exists()


# ----------------------------------------------------------------------------------- the burst and the lock
@needs_node
def test_lock_options_take_signals_away_and_honour_a_zero_wait():
    got = _node_module("[{}, {lock_wait_ms: 0}, {lock_wait_ms: 90000}, {lock_wait_ms: null}, {lock_wait_ms: -5}, "
                       "{lock_wait_ms: 'abc'}, {label: 'x'}].map((p) => H.lockOptions(p))")
    assert [g["maxWaitMs"] for g in got] == [600000, 0, 90000, 600000, 600000, 600000, 600000]
    assert all(g["signals"] is False for g in got)
    hold = _node_module("H.LOCK_HOLD_MS")
    assert all(g["maxHoldMs"] == hold for g in got) and got[6]["label"] == "x"


_GUARD_RUNNER = r"""
import * as H from __HEADLESS__;
import { acquireGpuLock } from __GPU_LOCK__;
import { existsSync, writeFileSync } from "node:fs";
const [mode, dir, log] = __ARGS__;
const seen = [];
const report = (code) => writeFileSync(log, JSON.stringify({ code, seen }));
const kill = () => seen.push(["kill", existsSync(dir)]);
if (mode === "old") {  // the wiring before the fix: the lock's own signal handlers, ours registered after acquire
  const gpu = await acquireGpuLock({ dir, label: "pytest guard", yieldToJam: false, maxWaitMs: 5000, log: () => {} });
  process.once("SIGINT", () => { kill(); gpu.release(); report(130); process.exit(130); });
  process.emit("SIGINT");
} else {
  const gpu = await acquireGpuLock({ ...H.lockOptions({ label: "pytest guard", lock_wait_ms: 5000 }), dir,
                                     yieldToJam: false, log: () => {} });
  H.guardHolder({ kill, release: () => { gpu.release(); seen.push(["release", existsSync(dir)]); },
                  exit: (code) => { report(code); process.exit(code); } });
  if (mode === "signal") process.emit("SIGINT");
  else { process.on("exit", (code) => report(code)); process.exit(1); }  // a crash exit: no finally runs
}
"""


@needs_node
@pytest.mark.parametrize("mode,lock_at_kill", [("old", False), ("signal", True), ("exit", True)])
def test_our_chrome_dies_before_the_lock_is_released(tmp_path, mode, lock_at_kill):
    """On a signal or a crash exit, kill first and release second, so no waiter (a load-sensitive jam lane) takes the
    lock while our SwiftShader Chrome still burns CPU. "old" replays the wiring before the fix and shows the defect:
    the lock's own prepended handler released first. The lock here is a private one in a temp directory."""
    lock_dir, log = tmp_path / "gpu-render.lock", tmp_path / "seen.json"
    code = (_GUARD_RUNNER.replace("__HEADLESS__", json.dumps(HEADLESS.resolve().as_uri()))
            .replace("__GPU_LOCK__", json.dumps(GPU_LOCK.resolve().as_uri()))
            .replace("__ARGS__", json.dumps([mode, str(lock_dir), str(log)])))
    env = {k: v for k, v in os.environ.items() if k != "ARSENAL_GPU_LOCK_TOKEN"}   # never inherit a live lock
    subprocess.run([NODE, "--input-type=module", "-e", code], capture_output=True, text=True, timeout=60, cwd=str(ROOT),
                   env=env)
    seen = json.loads(log.read_text(encoding="utf-8"))
    assert seen["seen"][0] == ["kill", lock_at_kill], seen
    assert not lock_dir.exists()
    if mode != "old":
        assert seen["seen"][:2] == [["kill", True], ["release", False]] and seen["code"] in (130, 1)


@needs_node
def test_burst_budget_counts_launch_relaunch_and_shutdown():
    c = _node_module("""({
      burst: H.BURST_MS, margin: H.SHUTDOWN_MARGIN_MS, reserve: H.LAUNCH_RESERVE_MS, devtools: H.DEVTOOLS_WAIT_MS,
      w: [[0, 300, 30000], [0, 50000, 165000], [0, 50000, 30000], [3, 100000, 30000], [3, 130000, 30000],
          [0, 169000, 30000], [0, 160000, 30000]].map(([index, elapsedMs, timeoutMs]) =>
            ({ index, elapsedMs, timeoutMs, ...H.jobWindow({ index, elapsedMs, timeoutMs }) })),
      relaunch: [0, 60000, 100000, 106000, 150000].map((e) => H.mayRelaunch(e)),
      clip: [H.clipBudget("http://127.0.0.1:1/lab/render.html?src=x&budget=145000&t=0", 100000),
             H.clipBudget("http://127.0.0.1:1/lab/render.html?src=x&budget=25000&t=0", 100000)],
    })""")
    burst, margin = c["burst"], c["margin"]
    assert burst < 180_000 and margin >= 13_000          # GPU-LOCK.md: under 3 minutes; shutdown measured up to ~13 s
    assert c["reserve"] >= c["devtools"] + 30_000        # a launch: DevTools port, then two 15 s software checks
    for w in c["w"]:
        if w["start"]:
            assert w["elapsedMs"] + w["deadlineMs"] + margin <= burst, w   # no job's deadline eats the shutdown
            assert w["deadlineMs"] <= w["timeoutMs"]
    first, first_late, first_short, later_fits, later_late, first_none, first_tight = c["w"]
    assert first["start"] and first["deadlineMs"] == 30000
    assert first_late["start"] and first_late["deadlineMs"] == burst - margin - 50000   # cut to what the burst has left
    assert first_short["start"] and first_short["deadlineMs"] == 30000
    assert later_fits["start"] and later_fits["deadlineMs"] == 30000
    assert not later_late["start"]                       # a later job starts only if its whole deadline fits
    assert not first_none["start"]
    assert first_tight["start"] == (burst - margin - 160000 >= 1000)
    assert c["relaunch"] == [e + c["reserve"] + margin <= burst for e in (0, 60000, 100000, 106000, 150000)]
    assert c["clip"][0].endswith("budget=95000&t=0") and c["clip"][1].endswith("budget=25000&t=0")
    assert R.BURST_CAP_S * 1000 <= burst - margin        # render.py never asks a job for more than a burst can give


def test_the_kill_timer_never_fires_inside_a_burst_that_keeps_its_rules():
    """render.py's last-resort kill of the driver: the lock wait asked for, plus one jam-lane poll (60 s) and one jam scan
    (up to 30 s) the waiter may still be in when its wait runs out, plus a whole burst and the slowest shutdown."""
    for lock_wait_ms in (0, 60_000, 600_000):
        assert R.driver_limit_s(lock_wait_ms) * 1000 >= lock_wait_ms + 60_000 + 30_000 + 170_000 + 30_000


@needs_node
def test_default_fps_is_shadertoys_60_as_in_the_runtime():
    """Stills step at Shadertoy's ~60 fps: at t=4 iFrame is 240, not 120 (Hex Glitch and Dry ice count frames)."""
    assert R.DEFAULT_FPS == 60
    url = RUNTIME.resolve().as_uri()
    assert _node(f"import * as T from {json.dumps(url)}; console.log(JSON.stringify(T.DEFAULT_FPS));") == R.DEFAULT_FPS


# ----------------------------------------------------------------------------------------------------- receipts
def _source(tmp_path):
    meta = C.meta_for(_shader())
    return R.Source(key="abcDEF", kind="corpus", path=tmp_path / "shader.json", src="/corpus/abcDEF/shader.json",
                    meta=meta)


def _row(tmp_path, renderer=SWIFTSHADER, times=(0.0, 1.5), status="done", page_ok=True):
    frames = [{"t": t, "ms": 4.5, "file": str(_png(tmp_path / f"t{t:.2f}.png")), "bytes": 100, "frame": i * 45,
               "frames": 1 + i * 45, "reset": i == 0} for i, t in enumerate(times)]
    return {"key": "abcDEF", "status": status, "frames": frames, "console": [], "error": None, "wall_ms": 321,
            "render": {"done": True, "ok": page_ok, "renderer": renderer, "frames": [{"t": t} for t in times],
                       "compile": {"ok": page_ok, "passes": [{"name": "Image", "ok": page_ok,
                                                             "firstError": None if page_ok else "ERROR: 0:3: 'x' : undeclared identifier"}]},
                       "substituted": [{"src": "/media/a/x.png", "reason": "missing media: procedural stand-in"}],
                       "unsupported": [], "errors": []}}


def _merged(renderer=SWIFTSHADER):
    return {"run_dir": "runs/x", "software": {"ok": True, "webgl": {"renderer": renderer}, "feature_status": {}},
            "chrome": "Chrome/155.0.0.0", "refused": None, "error": None,
            "bursts": [{"n": 1, "lock": {"wait_ms": 800}, "chrome_launches": [{"start_ms": 300}]}]}


def test_receipt_schema_for_a_good_render(tmp_path):
    request = {"t": [0.0, 1.5], "w": 480, "h": 270, "fps": 30, "page": "render.html", "timeout_ms": 120000}
    rec = R.build_receipt(_source(tmp_path), request, _row(tmp_path), _merged(), "2026-10-13T00:00:00")
    assert R.validate_receipt(rec) == []
    assert rec["ok"] is True and rec["status"] == "done" and rec["software_renderer"] is True
    assert [f["t"] for f in rec["frames"]] == [0.0, 1.5]
    assert rec["frames"][1]["frames_walked"] == 46 and rec["frames"][0]["reset"] is True
    assert rec["frames"][0]["flat"] is False and rec["first_error"] is None
    assert rec["license"] and rec["author"] == "someone"
    assert rec["substituted"] and rec["timings"]["lock_wait_ms"] == [800]
    json.dumps(rec)  # a receipt is JSON


def test_receipt_refuses_frames_from_a_hardware_renderer(tmp_path):
    request = {"t": [0.0, 1.5], "w": 480, "h": 270, "fps": 30, "page": "render.html", "timeout_ms": 120000}
    rec = R.build_receipt(_source(tmp_path), request, _row(tmp_path, renderer=AMD), _merged(AMD), "2026-10-13T00:00:00")
    assert R.validate_receipt(rec) == []
    assert rec["ok"] is False and rec["status"] == "refused" and rec["frames"] == []
    assert rec["software_renderer"] is False and any("not counted" in e for e in rec["errors"])


def test_receipt_is_not_ok_when_a_frame_is_missing_or_compile_failed(tmp_path):
    request = {"t": [0.0, 1.5, 4.0], "w": 480, "h": 270, "fps": 30, "page": "render.html", "timeout_ms": 120000}
    rec = R.build_receipt(_source(tmp_path), request, _row(tmp_path), _merged(), "2026-10-13T00:00:00")
    assert rec["ok"] is False and R.validate_receipt(rec) == []
    request["t"] = [0.0]
    rec = R.build_receipt(_source(tmp_path), request, _row(tmp_path, times=(0.0,), page_ok=False), _merged(),
                          "2026-10-13T00:00:00")
    assert rec["ok"] is False and "undeclared identifier" in rec["first_error"]


def test_validate_receipt_catches_bad_shapes(tmp_path):
    assert "missing api" in R.validate_receipt({})
    request = {"t": [0.0], "w": 480, "h": 270, "fps": 30, "page": "render.html", "timeout_ms": 120000}
    rec = R.build_receipt(_source(tmp_path), request, _row(tmp_path, times=(0.0,)), _merged(), "2026-10-13T00:00:00")
    forged = dict(rec, renderer=AMD, software_renderer=False)
    assert "ok without a software renderer" in R.validate_receipt(forged)
    assert any("status" in p for p in R.validate_receipt(dict(rec, status="finished")))
    assert any("frames[0]" in p for p in R.validate_receipt(dict(rec, frames=[{"t": "zero"}])))


def test_frame_facts_reads_flat_frames(tmp_path):
    assert R.frame_facts(str(_png(tmp_path / "flat.png", flat=True)))["flat"] is True
    assert R.frame_facts(str(_png(tmp_path / "busy.png")))["flat"] is False
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not a png")
    assert "decode_error" in R.frame_facts(str(bad))
    assert R.frame_facts(None) == {"mean_luma": None, "flat": None}


def test_census_row_and_first_error(tmp_path):
    meta = C.meta_for(_shader())
    row = R.census_row(meta, _row(tmp_path, times=(0.0,)), _merged())
    assert row["ok"] is True and row["ms_per_frame"] == 4.5 and row["substituted"]
    bad = R.census_row(meta, _row(tmp_path, times=(0.0,), page_ok=False), _merged())
    assert bad["ok"] is False and bad["pass_errors"][0]["pass"] == "Image"
    hw = R.census_row(meta, _row(tmp_path, times=(0.0,), renderer=AMD), _merged(AMD))
    assert hw["ok"] is False and hw["status"] == "refused" and hw["png"] is None
    timeout = R.census_row(meta, {"status": "timeout", "error": "the page did not finish"}, _merged())
    assert timeout["ok"] is False and timeout["first_error"] == "the page did not finish"


def test_census_cost_is_per_drawn_frame_not_per_still(tmp_path):
    """A still at t=1 and 30 fps is 31 drawn frames; its ms is the whole walk, so one frame costs ms / 31."""
    row = _row(tmp_path, times=(1.0,))
    row["frames"][0].update(ms=310, frames=31)
    got = R.census_row(C.meta_for(_shader()), row, _merged())
    assert got["ms_per_frame"] == 10.0 and got["ms_per_still"] == 310 and got["frames_walked"] == 31
    del row["frames"][0]["frames"]  # the probe page reports no walk: each still is one frame
    assert R.census_row(C.meta_for(_shader()), row, _merged())["ms_per_frame"] == 310


def test_jumped_stills_and_the_warm_frame_reach_receipt_and_census(tmp_path):
    """A shader without history jumps to each t (one drawn frame); render.js times one warm frame after the stills.
    Both facts ride from the page's report into the receipt and the census row."""
    row = _row(tmp_path, times=(1.0, 4.0))
    for f in row["frames"]:
        f.update(frames=1, reset=False, jumped=True)
    row["render"].update(warmMs=12.5, history=False)
    request = {"t": [1.0, 4.0], "w": 480, "h": 270, "fps": 30, "page": "render.html", "timeout_ms": 120000}
    rec = R.build_receipt(_source(tmp_path), request, row, _merged(), "2026-10-13T00:00:00")
    assert R.validate_receipt(rec) == []
    assert all(f["jumped"] is True and f["frames_walked"] == 1 for f in rec["frames"])
    assert rec["timings"]["warm_ms"] == 12.5 and rec["history"] is False
    got = R.census_row(C.meta_for(_shader()), row, _merged())
    assert got["warm_ms"] == 12.5 and got["history"] is False and got["frames_walked"] == 2
    row["render"]["warmMs"] = None  # no budget left for the warm frame: absent, not zero
    assert R.census_row(C.meta_for(_shader()), row, _merged())["warm_ms"] is None


def test_page_url_names_parity_only_when_it_is_off():
    on = R.page_url("http://127.0.0.1:8797", "render.html", "/corpus/abc/shader.json", [1.0], (480, 270), 30, 9000)
    off = R.page_url("http://127.0.0.1:8797", "render.html", "/corpus/abc/shader.json", [1.0], (480, 270), 30, 9000,
                     parity=False)
    assert "parity" not in on and "parity=0" in off


def test_contact_sheet(tmp_path):
    frames = [{"t": 0.0, "png": str(_png(tmp_path / "a.png"))}, {"t": 1.0, "png": str(_png(tmp_path / "b.png"))},
              {"t": 2.0, "png": None}]
    out = R.contact_sheet(frames, "synthetic | test", tmp_path / "sheet.png", cols=2, cell=(32, 18))
    from PIL import Image
    with Image.open(out) as im:
        assert im.size == (6 + 2 * (32 + 6), 26 + 6 + 2 * (18 + 6))


# -------------------------------------------------------------------------------------------- bursts and plans
def _job(key):
    return R.Job(key, f"http://127.0.0.1:1/lab/render.html?src=/corpus/{key}/shader.json", Path("out"), "", 30000,
                 (320, 180))


def test_plan_matches_the_driver_contract():
    plan = R.build_plan("label", [_job("aaaaaa")], 60000)
    assert plan["api"] == R.PLAN_API and plan["lock_wait_ms"] == 60000
    assert set(plan["jobs"][0]) == {"key", "url", "out_dir", "prefix", "timeout_ms", "w", "h", "screenshot",
                                    "allow_tracked"}
    assert plan["jobs"][0]["allow_tracked"] is False


def test_run_jobs_splits_work_into_bursts(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(R, "BURST_GAP_S", 0)
    calls = []

    def fake_burst(plan, run_dir, n, lock_wait_ms, quiet):
        keys = [j["key"] for j in plan["jobs"]]
        calls.append(keys)
        rows = [{"key": keys[0], "status": "done"}] + [{"key": k, "status": "deferred"} for k in keys[1:]]
        return 0, {"jobs": rows, "software": {"ok": True}, "chrome": {"version": "Chrome/155"}, "lock": {"wait_ms": 1}}

    monkeypatch.setattr(R, "_run_burst", fake_burst)
    merged = R.run_jobs([_job("aaaaaa"), _job("bbbbbb"), _job("cccccc")], "t", quiet=True)
    assert calls == [["aaaaaa", "bbbbbb", "cccccc"], ["bbbbbb", "cccccc"], ["cccccc"]]
    assert all(r["status"] == "done" for r in merged["rows"].values()) and len(merged["bursts"]) == 3


def test_run_jobs_stops_on_refusal_and_on_no_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(R, "BURST_GAP_S", 0)
    monkeypatch.setattr(R, "_run_burst", lambda plan, *a: (R.EXIT_REFUSED, {
        "refused": "the renderer is not SwiftShader", "jobs": [{"key": j["key"], "status": "refused"} for j in plan["jobs"]]}))
    merged = R.run_jobs([_job("aaaaaa"), _job("bbbbbb")], "t", quiet=True)
    assert merged["refused"] and len(merged["bursts"]) == 1

    monkeypatch.setattr(R, "_run_burst", lambda plan, *a: (0, {
        "jobs": [{"key": j["key"], "status": "deferred"} for j in plan["jobs"]]}))
    merged = R.run_jobs([_job("aaaaaa")], "t", quiet=True)
    assert len(merged["bursts"]) == 1 and "no job" in merged["error"]


def test_page_url_carries_the_contract_query():
    url = R.page_url("http://127.0.0.1:8797", "render.html", "/corpus/abcDEF/shader.json", [0, 1.5, 4], (480, 270),
                     30, 115000)
    assert url.startswith("http://127.0.0.1:8797/lab/render.html?")
    for part in ("src=http://127.0.0.1:8797/corpus/abcDEF/shader.json", "t=0,1.5,4", "w=480", "h=270", "fps=30",
                 "media=http://127.0.0.1:8797/corpus/media/", "budget=115000"):
        assert part in url


# --------------------------------------------------------------------------------------------- verbs and sources
@pytest.fixture()
def parser():
    ap = argparse.ArgumentParser(prog="shader")
    sub = ap.add_subparsers(dest="verb", required=True)
    for register in (R.register_render, R.register_check, R.register_filmstrip, R.register_serve):
        register(sub)
    return ap


def test_verbs_register_into_the_cli():
    for name in ("render", "check", "filmstrip", "serve"):
        assert name in cli.VERBS


def test_render_verb_parsing(parser):
    ns = parser.parse_args(["render", "abcDEF", "--t", "0,1.5,4", "--size", "640x360", "--out", "x"])
    assert ns.t == [0.0, 1.5, 4.0] and ns.size == (640, 360) and ns.out == "x" and ns.fps == R.DEFAULT_FPS
    ns = parser.parse_args(["render", "sketch.frag"])
    assert ns.t == R.DEFAULT_T and ns.size == R.DEFAULT_SIZE and ns.page == "render.html" and ns.port == 8797
    for bad in (["render", "x", "--t", "-1"], ["render", "x", "--t", "nan"], ["render", "x", "--size", "480"],
                ["render", "x", "--size", "0x10"], ["render", "x", "--fps", "0"], ["render", "x", "--port", "8793"],
                ["render", "x", "--page", "../secret.html"]):
        with pytest.raises(SystemExit):
            parser.parse_args(bad)


def test_check_filmstrip_serve_parsing(parser):
    ns = parser.parse_args(["check", "aaaaaa", "bbbbbb", "--set", "loved"])
    assert ns.ids == ["aaaaaa", "bbbbbb"] and ns.set == "loved" and ns.t == [0.0] and ns.size == R.CHECK_SIZE
    assert parser.parse_args(["check", "--all"]).all is True
    ns = parser.parse_args(["filmstrip", "abcDEF"])
    assert ns.frames == 8 and ns.to == 8.0
    ns = parser.parse_args(["filmstrip", "abcDEF", "--frames", "4", "--to", "2"])
    assert R.filmstrip_times(ns.frames, ns.to) == [0.0, 0.6667, 1.3333, 2.0]
    assert parser.parse_args(["serve"]).port == 8797
    assert parser.parse_args(["serve", "--port", "8800"]).port == 8800
    with pytest.raises(SystemExit):
        parser.parse_args(["serve", "--port", "8793"])


def test_parse_helpers():
    assert R.parse_times(" 0 , 2,4 ") == [0.0, 2.0, 4.0]
    for bad in ("", ",", "a", "-0.5", "inf", ",".join(["1"] * (R.MAX_TIMES + 1))):
        with pytest.raises(ValueError):
            R.parse_times(bad)
    assert R.parse_size("1920X1080") == (1920, 1080)
    with pytest.raises(ValueError):
        R.parse_size(f"{R.MAX_SIDE + 1}x10")
    assert R.filmstrip_times(1, 3) == [3.0]
    with pytest.raises(ValueError):
        R.filmstrip_times(0, 3)


def test_resolve_source_frag_json_and_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "JOBS", tmp_path / "jobs")
    frag = tmp_path / "My Sketch.frag"
    frag.write_text("void mainImage(out vec4 o, in vec2 u) { o = vec4(1.0); }\n", encoding="utf-8")
    src = R.resolve_source(str(frag))
    assert src.kind == "frag" and src.key == "local-my-sketch" and src.src.startswith("/jobs/local-my-sketch-")
    staged = tmp_path / "jobs" / src.src[len("/jobs/"):]
    assert S.JOB_NAME.fullmatch(staged.name)
    assert json.loads(staged.read_text(encoding="utf-8"))["renderpass"][0]["type"] == "image"
    assert src.meta["license"]["license"] == "not stated (local file)"

    house = tmp_path / "house.frag"
    house.write_text("uniform vec2 u_res; void main() {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mainImage"):
        R.resolve_source(str(house))

    wrapped = tmp_path / "api.json"
    wrapped.write_text(json.dumps({"Shader": _shader()}), encoding="utf-8")
    assert R.resolve_source(str(wrapped)).kind == "json"

    corpus = tmp_path / "corpus"
    C.save_shader(_shader("abcDEF", name="Unique Name"), corpus)
    C.save_shader(_shader("ghiJKL", name="Other"), corpus)
    got = R.resolve_source("abcDEF", corpus)
    assert got.kind == "corpus" and got.src == "/corpus/abcDEF/shader.json"
    assert R.resolve_source("unique", corpus).key == "abcDEF"
    with pytest.raises(LookupError):
        R.resolve_source("nothing-matches", corpus)


def test_check_ids_reads_sets_in_order(tmp_path):
    corpus = tmp_path / "corpus"
    for sid in ("aaaaaa", "bbbbbb", "cccccc"):
        C.save_shader(_shader(sid), corpus)
    (corpus / "sets.json").write_text(json.dumps({"loved": ["cccccc", "zzzzzz", "aaaaaa"]}), encoding="utf-8")
    ns = argparse.Namespace(ids=[], set="loved", all=False, limit=0)
    assert R.check_ids(ns, corpus) == (["cccccc", "aaaaaa"], ["zzzzzz"])
    ns = argparse.Namespace(ids=["bbbbbb"], set=None, all=False, limit=0)
    assert R.check_ids(ns, corpus) == (["bbbbbb"], [])
    ns = argparse.Namespace(ids=[], set=None, all=True, limit=2)
    assert R.check_ids(ns, corpus)[0] == ["aaaaaa", "bbbbbb"]
    with pytest.raises(LookupError):
        R.check_ids(argparse.Namespace(ids=[], set="nope", all=False, limit=0), corpus)
    with pytest.raises(LookupError):
        R.check_ids(argparse.Namespace(ids=[], set=None, all=False, limit=0), corpus)


# ------------------------------------------------------------------------------------- where pictures may land
def _corpus_here(tmp_path, monkeypatch) -> Path:
    corpus = tmp_path / "corpus"
    C.save_shader(_shader("abcDEF", name="Someone's shader"), corpus)
    monkeypatch.setattr(C, "CORPUS", corpus)
    monkeypatch.setattr(S, "JOBS", tmp_path / "jobs")
    return corpus


def _own_frag(tmp_path) -> Path:
    frag = tmp_path / "mine.frag"
    frag.write_text("void mainImage(out vec4 o, in vec2 u) { o = vec4(u.x, 0.0, 0.0, 1.0); }\n", encoding="utf-8")
    return frag


def test_out_dir_policy_keeps_corpus_pictures_under_state(tmp_path, monkeypatch):
    corpus = _corpus_here(tmp_path, monkeypatch)
    theirs = R.resolve_source("abcDEF", corpus)
    assert theirs.corpus_subject
    inside = STATE / "arsenal" / "shaders" / "renders" / "abcDEF"
    assert R.out_dir_refusal(inside, theirs) is None
    for bad in (NOT_STATE, STATE / ".." / "design", tmp_path / "anywhere"):
        for allow in (False, True):
            why = R.out_dir_refusal(bad, theirs, allow_tracked=allow)
            assert why and "state" in why, (bad, allow)
    # A file that IS someone's shader is a corpus subject too: by where it lies, or by its Shadertoy-shaped id.
    assert R.resolve_source(str(corpus / "shaders" / "abcDEF" / "shader.json"), corpus).corpus_subject
    copy = tmp_path / "copy.json"
    copy.write_text(json.dumps(_shader("ghiJKL")), encoding="utf-8")
    assert R.resolve_source(str(copy), corpus).corpus_subject
    own = R.resolve_source(str(_own_frag(tmp_path)), corpus)
    assert not own.corpus_subject
    assert R.out_dir_refusal(inside, own) is None
    assert "--allow-tracked" in R.out_dir_refusal(NOT_STATE, own)
    assert R.out_dir_refusal(NOT_STATE, own, allow_tracked=True) is None


@pytest.mark.parametrize("verb", ["render", "filmstrip"])
def test_render_verbs_refuse_an_out_dir_outside_state_before_any_work(tmp_path, monkeypatch, parser, capsys, verb):
    _corpus_here(tmp_path, monkeypatch)
    monkeypatch.setattr(S, "base_for", lambda port: pytest.fail("a lab server was started"))
    monkeypatch.setattr(R, "run_jobs", lambda *a, **k: pytest.fail("the driver ran"))
    for extra in ([], ["--allow-tracked"]):
        ns = parser.parse_args([verb, "abcDEF", "--out", str(NOT_STATE)] + extra)
        ns.json = True
        assert ns.fn(ns) == 2
        assert "state" in capsys.readouterr().err
    ns = parser.parse_args([verb, str(_own_frag(tmp_path)), "--out", str(NOT_STATE)])
    ns.json = True
    assert ns.fn(ns) == 2 and "--allow-tracked" in capsys.readouterr().err
    assert not NOT_STATE.exists()


@pytest.mark.parametrize("verb", ["render", "filmstrip"])
def test_allow_tracked_lets_your_own_shader_out_and_tells_the_driver(tmp_path, monkeypatch, parser, verb):
    _corpus_here(tmp_path, monkeypatch)
    jobs_seen = []
    monkeypatch.setattr(S, "base_for", lambda port: (None, "http://127.0.0.1:1"))

    def fake_run(jobs, label, lock_wait_min=10, quiet=False):
        jobs_seen.extend(jobs)
        return {"run_dir": None, "software": None, "chrome": None, "bursts": [], "refused": None, "error": None,
                "rows": {j.key: {"key": j.key, "status": "error", "error": "not rendered in a test"} for j in jobs}}

    monkeypatch.setattr(R, "run_jobs", fake_run)
    out = tmp_path / "elsewhere"
    ns = parser.parse_args([verb, str(_own_frag(tmp_path)), "--out", str(out), "--allow-tracked"])
    ns.json = True
    ns.fn(ns)
    (job,) = jobs_seen
    assert job.allow_tracked is True and job.plan_row()["allow_tracked"] is True
    assert Path(job.out_dir).is_absolute() and Path(job.out_dir).is_relative_to(out.resolve())
    # inside state/ the flag is moot: the driver is told nothing it would have to trust (a temp state/ stands in, so
    # this test writes nothing under the real one)
    monkeypatch.setattr(R, "STATE_ROOT", tmp_path / "state")
    monkeypatch.setattr(R, "RENDERS", tmp_path / "state" / "arsenal" / "shaders" / "renders")
    jobs_seen.clear()
    ns = parser.parse_args([verb, str(_own_frag(tmp_path)), "--allow-tracked"])
    ns.json = True
    ns.fn(ns)
    assert jobs_seen[0].allow_tracked is False
