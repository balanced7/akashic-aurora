"""Pins for the page index of the house GLSL library: arsenal/web/glsl/index.json (slice S1, shader school 2026-10-13).

WHY. A page cannot list a directory, so modlib.loadLibrary reads an index of the library's files. If the index lags the
files, a page silently composes yesterday's library while the CLI composes today's, and "tweak one module and have
everything update" (Daniel, 2026-10-13) is false without anyone noticing. So the index carries each file's sha256, a
test fails the moment it is stale, and `py -m arsenal shader lib index --write` regenerates it and keeps a
content-addressed archive copy of every module version under state/ (a receipt can then name bytes that still exist).

The hash is of the file's text with line endings normalised to LF: *.glsl is not pinned by .gitattributes and this
machine checks out with core.autocrlf=true, so hashing raw bytes would make a CRLF checkout look stale.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from types import SimpleNamespace

import pytest

from arsenal.shaders import modules as M


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def module_text(name: str, body: str) -> str:
    return "//! " + json.dumps({"name": name, "kind": "helper", "cat": "math"}) + "\n" + body + "\n"


def test_the_committed_index_matches_the_library_files():
    assert M.INDEX_PATH.exists(), "no index: run py -m arsenal shader lib index --write"
    on_disk = json.loads(M.INDEX_PATH.read_text(encoding="utf-8"))
    assert on_disk == M.build_index(), "index.json is stale: run py -m arsenal shader lib index --write"


def test_the_index_lists_library_files_by_posix_path_with_the_hash_of_their_lf_text(tmp_path):
    lib = tmp_path / "glsl"
    (lib / "noise").mkdir(parents=True)
    value, core = module_text("value", "float v(float x){ return x; }"), module_text("core", "float c(){ return 1.; }")
    (lib / "noise" / "value.glsl").write_bytes(value.replace("\n", "\r\n").encode("utf-8"))   # a CRLF checkout
    (lib / "core.glsl").write_bytes(core.encode("utf-8"))
    (lib / "README.md").write_text("not a module", encoding="utf-8")
    assert M.build_index(lib) == {"api": M.API, "files": [{"path": "core.glsl", "sha256": sha(core)},
                                                          {"path": "noise/value.glsl", "sha256": sha(value)}]}


def test_a_stale_index_is_caught(tmp_path):
    lib = tmp_path / "glsl"
    lib.mkdir()
    (lib / "a.glsl").write_text(module_text("a", "float a(float x){ return x; }"), encoding="utf-8")
    M.write_index(lib, archive_dir=tmp_path / "archive")
    assert M.index_is_current(lib)
    (lib / "a.glsl").write_text(module_text("a", "float a(float x){ return -x; }"), encoding="utf-8")
    assert not M.index_is_current(lib)
    M.write_index(lib, archive_dir=tmp_path / "archive")
    (lib / "b.glsl").write_text(module_text("b", "float b(float x){ return x; }"), encoding="utf-8")
    assert not M.index_is_current(lib)
    assert not M.index_is_current(tmp_path / "nowhere")


def test_write_index_keeps_a_content_addressed_archive_copy_of_every_version(tmp_path):
    lib, archive = tmp_path / "glsl", tmp_path / "archive"
    lib.mkdir()
    v1, v2 = module_text("wave", "float w(float x){ return x; }"), module_text("wave", "float w(float x){ return -x; }")
    (lib / "wave.glsl").write_text(v1, encoding="utf-8")
    M.write_index(lib, archive_dir=archive)
    (lib / "wave.glsl").write_text(v2, encoding="utf-8")
    report = M.write_index(lib, archive_dir=archive)
    for text in (v1, v2):
        kept = archive / "wave" / f"{sha(text)}.glsl"
        assert kept.exists() and hashlib.sha256(kept.read_bytes()).hexdigest() == sha(text)
    assert json.loads((lib / "index.json").read_text(encoding="utf-8")) == report["index"]


def test_a_truncated_archive_copy_is_rewritten_not_trusted(tmp_path):
    """Review defect 10: an interrupted write used to leave a truncated file at the hash's path, and the existence
    check then kept it forever. A copy whose bytes do not hash to its name is rewritten."""
    lib, archive = tmp_path / "glsl", tmp_path / "archive"
    lib.mkdir()
    text = module_text("wave", "float w(float x){ return x; }")
    (lib / "wave.glsl").write_text(text, encoding="utf-8")
    kept = archive / "wave" / f"{sha(text)}.glsl"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(text.encode("utf-8")[:10])
    report = M.write_index(lib, archive_dir=archive)
    assert kept.read_bytes() == text.encode("utf-8") and report["archived"] == [kept.as_posix()]
    assert M.write_index(lib, archive_dir=archive)["archived"] == []     # a good copy is never rewritten


def test_an_interrupted_archive_write_leaves_nothing_at_the_hash_path(tmp_path, monkeypatch):
    lib, archive = tmp_path / "glsl", tmp_path / "archive"
    lib.mkdir()
    text = module_text("wave", "float w(float x){ return x; }")
    (lib / "wave.glsl").write_text(text, encoding="utf-8")

    def interrupted(src, dst):
        raise OSError("power cut")
    monkeypatch.setattr(M.os, "replace", interrupted)
    try:
        M.write_index(lib, archive_dir=archive)
    except OSError:
        pass
    leftovers = [p for p in archive.rglob("*") if p.is_file()]
    assert leftovers == [], leftovers
    assert not (lib / "index.json").exists()


def test_index_and_archive_files_are_created_for_the_umask_not_as_owner_only(tmp_path, monkeypatch):
    """Re-review (round 2), LOW: tempfile.mkstemp creates 0600 and os.replace keeps it, so on POSIX index.json and the
    archive copies became owner-only where the earlier plain writes followed the umask. The temporary file is now
    created with 0666, which the umask narrows exactly as it narrows a plain write."""
    lib, archive = tmp_path / "glsl", tmp_path / "archive"
    lib.mkdir()
    (lib / "wave.glsl").write_text(module_text("wave", "float w(float x){ return x; }"), encoding="utf-8")
    created, real_open = [], M.os.open

    def recording_open(path, flags, mode=0o777, *args, **kwargs):
        if flags & os.O_CREAT:
            created.append((os.path.basename(path), mode))
        return real_open(path, flags, mode, *args, **kwargs)
    monkeypatch.setattr(M.os, "open", recording_open)
    M.write_index(lib, archive_dir=archive)
    assert len(created) == 2 and all(mode == 0o666 for _, mode in created), created


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_index_json_gets_the_mode_a_plain_write_would(tmp_path):
    lib = tmp_path / "glsl"
    lib.mkdir()
    (lib / "wave.glsl").write_text(module_text("wave", "float w(float x){ return x; }"), encoding="utf-8")
    old = os.umask(0o022)
    try:
        M.write_index(lib, archive_dir=tmp_path / "archive")
    finally:
        os.umask(old)
    assert stat.S_IMODE((lib / "index.json").stat().st_mode) == 0o644


def test_the_index_verb_reports_whether_the_committed_index_is_current(capsys):
    ns = SimpleNamespace(action="index", names=[], write=False, dir=None, json=True, target=None)
    assert M._cmd(ns) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["current"] is True and out["index"] == M.build_index() and out["written"] is False
