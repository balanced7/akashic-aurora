"""Pins for the lab server's routes (arsenal/shaders/serve.py), as the route contract of 2026-10-13 names them.

WHY A FILE OF ITS OWN. tests/test_shader_harness.py pins the server's character (loopback only, read-only, 8793 refused,
traversal refused) on the routes the render harness needs. The Shelf slice adds the routes a Workbench page needs to show
the Shelf and the atlas, and each new route is a new door into a folder, so each gets the same three questions:

  * does it serve exactly the folder the contract names (the defaults point at the real paths);
  * does it refuse every spelling of a path out of that folder, and every file the contract does not name;
  * does it keep the private things private: a study-only shader's pictures are never served, whatever sits on disk,
    and every route answers loopback names only.

    /atlas.json             arsenal/shaders/atlas.json              the atlas as data (our own words)
    /shelf/index.json       state/arsenal/shaders/shelf/            the Shelf's index (private)
    /renders/<id>/<f>.png   state/arsenal/shaders/renders/          SwiftShader stills and filmstrips (private)
    /study/<id>.md          state/arsenal/shaders/study/            the study notes (private)
    /cards/<name>/<f>.png   state/arsenal/shaders/cards/            module test cards
    /webl/<file>            arsenal/web/lib/                        params.js, params-ui.js, workbench/*

Every file here is synthetic. No test launches a browser or renders anything.
"""
from __future__ import annotations

import http.client
import json
from pathlib import Path

import pytest

from arsenal.shaders import corpus as C
from arsenal.shaders import serve as S

ROOT = Path(__file__).resolve().parents[1]
SECRET = "TOPSECRET-not-for-the-shelf"
PNG = b"\x89PNG\r\n\x1a\n" + b"shelf-route-probe"


def _shader(sid):
    return {"ver": "0.1", "info": {"id": sid, "name": "Route probe", "username": "someone", "tags": []},
            "renderpass": [{"name": "Image", "type": "image", "inputs": [], "outputs": [],
                            "code": "void mainImage(out vec4 o, in vec2 u) { o = vec4(0.5); }"}]}


def _serve(tmp_path: Path):
    """A server over temp roots for every route, with a secret file beside them."""
    (tmp_path / "secret.txt").write_text(SECRET, encoding="utf-8")
    (tmp_path / "secret.png").write_bytes(PNG + SECRET.encode())
    (tmp_path / "secret.md").write_text(SECRET, encoding="utf-8")
    lab_dir = tmp_path / "lab"
    lab_dir.mkdir()
    (lab_dir / "index.html").write_text("<!doctype html><title>lab</title>", encoding="utf-8")
    lib_dir = tmp_path / "glsl"
    lib_dir.mkdir()
    (lib_dir / "modlib.js").write_text("// house library route probe\n", encoding="utf-8")
    corpus = tmp_path / "corpus"
    C.save_shader(_shader("abcDE1"), corpus)
    jobs = tmp_path / "jobs"
    jobs.mkdir()

    atlas = tmp_path / "atlas.json"
    atlas.write_text(json.dumps({"api": "arsenal.shader-atlas/v1", "note": "atlas route probe",
                                 "loved": [{"id": "abcDE1", "short": "One", "study_only": False},
                                           {"id": "abcDE4", "short": "Ruled", "study_only": True}]}),
                     encoding="utf-8")
    shelf = tmp_path / "state" / "shelf"
    shelf.mkdir(parents=True)
    (shelf / "index.json").write_text(json.dumps({"api": "arsenal.shader-shelf/v1", "note": "shelf route probe",
                                                  "shaders": [{"id": "abcDE1", "study_only": False},
                                                              {"id": "abcDE2", "study_only": True}]}),
                                      encoding="utf-8")
    (shelf / "other.json").write_text("{}", encoding="utf-8")
    renders = tmp_path / "state" / "renders"
    for sid in ("abcDE1", "abcDE2", "abcDE4", "local-probe"):
        (renders / sid / "filmstrip").mkdir(parents=True)
        (renders / sid / "t1.00.png").write_bytes(PNG + sid.encode())
        (renders / sid / "filmstrip.png").write_bytes(PNG + b"sheet")
        (renders / sid / "receipt.json").write_text("{}", encoding="utf-8")
        (renders / sid / "filmstrip" / "t0.00.png").write_bytes(PNG)
    study = tmp_path / "state" / "study"
    study.mkdir(parents=True)
    (study / "abcDE1.md").write_text("# Study: route probe (abcDE1)\n", encoding="utf-8")
    (study / "abcDE2.md").write_text("# Study: study-only probe (abcDE2)\n", encoding="utf-8")
    (study / "abcDE1.txt").write_text("not a note", encoding="utf-8")
    cards = tmp_path / "state" / "cards"
    (cards / "hash-pcg").mkdir(parents=True)
    (cards / "hash-pcg" / "t0.00.png").write_bytes(PNG + b"card")
    (cards / "hash-pcg" / "card.json").write_text("{}", encoding="utf-8")
    webl = tmp_path / "weblib"
    (webl / "workbench").mkdir(parents=True)
    (webl / "params.js").write_text("// params route probe\n", encoding="utf-8")
    (webl / "workbench" / "panel.js").write_text("// workbench route probe\n", encoding="utf-8")

    return S.start_in_thread(0, lab=lab_dir, lib=lib_dir, corpus=corpus, jobs=jobs, atlas=atlas, shelf=shelf,
                             renders=renders, study=study, cards=cards, webl=webl)


@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    """One server for the read-only tests (a shutdown waits out serve_forever's half-second poll, so one per test
    would cost half a second each)."""
    server = _serve(tmp_path_factory.mktemp("routes"))
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture()
def fresh_lab(tmp_path):
    """A server of its own, for a test that changes what is on disk."""
    server = _serve(tmp_path)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _get(server, path, method="GET", headers=None):
    conn = http.client.HTTPConnection(S.HOST, server.server_address[1], timeout=10)
    try:
        conn.request(method, path, headers=headers or {})
        res = conn.getresponse()
        return res.status, dict(res.getheaders()), res.read()
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------- the contract's paths
def test_the_new_roots_default_to_the_contract_paths():
    state = ROOT / "state" / "arsenal" / "shaders"
    assert S.ATLAS == ROOT / "arsenal" / "shaders" / "atlas.json"
    assert S.SHELF == state / "shelf"
    assert S.RENDERS == state / "renders"
    assert S.STUDY == state / "study"
    assert S.CARDS == state / "cards"
    assert S.WEBL == ROOT / "arsenal" / "web" / "lib"


def test_routes_list_names_every_route_of_the_contract():
    for route in ("/lab/<file>", "/glsl/<file>", "/lib/<file>", "/corpus/<id>/shader.json", "/corpus/media/<file>",
                  "/atlas.json", "/shelf/index.json", "/renders/<id>/<file>.png", "/study/<id>.md",
                  "/cards/<name>/<file>.png", "/webl/<file>"):
        assert route in S.ROUTES, route


def test_health_names_the_new_roots(lab):
    status, _, body = _get(lab, "/health")
    roots = json.loads(body)["roots"]
    assert status == 200
    for key in ("atlas", "shelf", "renders", "study", "cards", "webl"):
        assert key in roots, key


def test_the_real_server_serves_the_real_atlas_byte_for_byte():
    server = S.start_in_thread(0)
    try:
        status, headers, body = _get(server, "/atlas.json")
        assert status == 200 and body == S.ATLAS.read_bytes()
        assert headers["Content-Type"] == "application/json"
        for key, path in (("shelf", S.SHELF), ("renders", S.RENDERS), ("study", S.STUDY), ("cards", S.CARDS),
                          ("webl", S.WEBL), ("atlas", S.ATLAS)):
            assert server.health()["roots"][key] == str(path)
    finally:
        server.shutdown()
        server.server_close()


# ------------------------------------------------------------------------------------------------- what is served
@pytest.mark.parametrize("path,needle,ctype", [
    ("/atlas.json", b"atlas route probe", "application/json"),
    ("/shelf/index.json", b"shelf route probe", "application/json"),
    ("/renders/abcDE1/t1.00.png", PNG + b"abcDE1", "image/png"),
    ("/renders/abcDE1/filmstrip.png", PNG + b"sheet", "image/png"),
    ("/renders/local-probe/t1.00.png", PNG + b"local-probe", "image/png"),
    ("/study/abcDE1.md", b"# Study: route probe", "text/"),
    ("/study/abcDE2.md", b"study-only probe", "text/"),          # a study-only shader is shown by its note
    ("/cards/hash-pcg/t0.00.png", PNG + b"card", "image/png"),
    ("/webl/params.js", b"params route probe", "text/javascript"),
    ("/webl/workbench/panel.js", b"workbench route probe", "text/javascript"),
    ("/glsl/modlib.js", b"house library route probe", "text/javascript"),
    ("/lib/modlib.js", b"house library route probe", "text/javascript"),
])
def test_new_routes_serve_their_roots(lab, path, needle, ctype):
    status, headers, body = _get(lab, path)
    assert status == 200, (path, body[:200])
    assert body == needle if needle.startswith(PNG) else needle in body
    assert headers["Content-Type"].startswith(ctype)
    assert headers.get("X-Content-Type-Options") == "nosniff"


def test_head_answers_without_a_body(lab):
    status, headers, body = _get(lab, "/renders/abcDE1/t1.00.png", method="HEAD")
    assert status == 200 and body == b"" and int(headers["Content-Length"]) == len(PNG + b"abcDE1")


# ----------------------------------------------------------------------------------------------- what is refused
@pytest.mark.parametrize("path", [
    "/renders/abcDE2/t1.00.png",            # study only by the Shelf's index
    "/renders/abcDE2/filmstrip.png",
    "/renders/abcDE4/t1.00.png",            # study only by the atlas's ruling, Shelf or no Shelf
    "/renders/abcde2/t1.00.png",            # Windows folds case; the refusal must too
])
def test_a_study_only_shaders_pictures_are_never_served(lab, path):
    status, _, body = _get(lab, path)
    assert status == 403, (path, status)
    assert PNG not in body


@pytest.mark.parametrize("path", [
    "/atlas.json/../secret.txt",
    "/atlas.json%00",
    "/atlas.jsonx",
    "/shelf/../secret.txt",
    "/shelf/%2e%2e/secret.txt",
    "/shelf/other.json",                    # only the index is served
    "/shelf/index.json/x",
    "/shelf/",
    "/renders/../secret.txt",
    "/renders/abcDE1/../../secret.png",
    "/renders/%2e%2e/secret.png",
    "/renders/..%2fsecret.png",
    "/renders/abcDE1/..%2f..%2fsecret.png",
    "/renders/abcDE1/receipt.json",         # pictures only
    "/renders/abcDE1/filmstrip/t0.00.png",  # one level: <id>/<file>.png
    "/renders/abcDE1/t1.00.png%00.txt",
    "/renders/abcDE1/C:/x.png",
    "/renders/abcDE1",
    "/renders/",
    "/study/../secret.md",
    "/study/..%2fsecret.md",
    "/study/%2e%2e/secret.md",
    "/study/abcDE1.txt",
    "/study/abc.md",                        # not a Shadertoy id
    "/study/abcDE1/x.md",
    "/study/abcDE1.md%00",
    "/cards/../secret.png",
    "/cards/hash-pcg/../../secret.png",
    "/cards/%2e%2e/secret.png",
    "/cards/hash-pcg/card.json",            # pictures only
    "/cards/hash-pcg/sub/t0.00.png",
    "/cards/.hidden/t0.00.png",
    "/webl/../secret.txt",
    "/webl/%2e%2e/secret.txt",
    "/webl/..%2fsecret.txt",
    "/webl/workbench/../../secret.txt",
    "/webl/C:/Windows/win.ini",
    "/webl/params.js%00.png",
    "/webl/./params.js",
    "/webl//params.js",
    "/webl/",
    "/state/arsenal/shaders/shelf/index.json",
    "/secret.txt",
])
def test_traversal_and_unnamed_files_are_refused(lab, path):
    status, _, body = _get(lab, path)
    assert status in (403, 404), (path, status)
    assert SECRET.encode() not in body


@pytest.mark.parametrize("path", ["/study/abcDE1.md", "/shelf/index.json", "/renders/abcDE1/t1.00.png",
                                  "/atlas.json", "/webl/params.js", "/cards/hash-pcg/t0.00.png"])
def test_private_routes_answer_loopback_names_only(lab, path):
    assert _get(lab, path, headers={"Host": "127.0.0.1"})[0] == 200
    status, _, body = _get(lab, path, headers={"Host": "evil.example"})
    assert status == 403 and b"route probe" not in body and PNG not in body


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_new_routes_are_read_only(lab, method):
    status, headers, _ = _get(lab, "/shelf/index.json", method=method)
    assert status == 405 and "GET" in headers.get("Allow", "")


def test_no_shelf_index_is_a_404_not_a_crash(fresh_lab):
    assert _get(fresh_lab, "/renders/abcDE2/t1.00.png")[0] == 403
    (Path(fresh_lab.roots["shelf"]) / "index.json").unlink()
    assert _get(fresh_lab, "/shelf/index.json")[0] == 404
    assert _get(fresh_lab, "/renders/abcDE1/t1.00.png")[0] == 200     # the atlas still names what is study only
    assert _get(fresh_lab, "/renders/abcDE4/t1.00.png")[0] == 403
    assert _get(fresh_lab, "/renders/abcDE2/t1.00.png")[0] == 200     # the cache follows the index off the disk


def test_a_newly_built_shelf_takes_effect_without_a_restart(fresh_lab):
    index = Path(fresh_lab.roots["shelf"]) / "index.json"
    assert _get(fresh_lab, "/renders/abcDE1/t1.00.png")[0] == 200
    index.write_text(json.dumps({"api": "arsenal.shader-shelf/v1", "shaders": [{"id": "abcDE1", "study_only": True}]}),
                     encoding="utf-8")
    assert _get(fresh_lab, "/renders/abcDE1/t1.00.png")[0] == 403


def test_a_symlink_out_of_a_new_root_is_refused(fresh_lab, tmp_path):
    import os
    link = Path(fresh_lab.roots["webl"]) / "escape.js"
    try:
        os.symlink(tmp_path / "secret.txt", link)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symlinks")
    status, _, body = _get(fresh_lab, "/webl/escape.js")
    assert status == 404 and SECRET.encode() not in body


def test_port_8793_is_still_refused():
    with pytest.raises(S.BindRefused, match="8793"):
        S.ShaderServer(8793)
