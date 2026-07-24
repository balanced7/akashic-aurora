"""Pins for core.library.projection (A1 -- one atom, one read-only render)."""

import os

from core.library import atoms as at
from core.library import projection as pj
from tests.test_atoms import FakeStore


def _mint(tmp_path, **kw):
    fam = at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path / "jsonl"))
    defaults = dict(arc="t101", seats=["claude"], categories=["substrate"], now=1000.0)
    defaults.update(kw)
    return fam, fam.mint(kw.pop("type_", "design") if "type_" in kw else "design",
                         kw.pop("title", "My Design") if "title" in kw else "My Design",
                         kw.pop("body", "the body") if "body" in kw else "the body",
                         **{k: v for k, v in defaults.items() if k not in ("type_", "title", "body")})


def test_relpath_is_type_and_id_only():
    fam, a = _mint(__import__("pathlib").Path(os.getenv("TEMP", "/tmp")))
    rel = pj.projection_relpath(a)
    assert rel.startswith(os.path.join("docs", "library", "design"))
    assert "substrate" not in rel and "t101" not in rel  # one-facet law: no facet in path


def test_render_writes_frontmatter_sha_and_guard(tmp_path):
    fam, a = _mint(tmp_path)
    path = pj.render_atom(a, repo_root=str(tmp_path))
    text = open(path, encoding="utf-8").read()
    assert text.startswith("---\n")
    assert f"akashic_id: {a['id']}" in text
    assert f"akashic_sha: {a['body_sha']}" in text
    assert "DO NOT EDIT" in text
    assert "category: [substrate]" in text
    assert "# My Design" in text and "the body" in text


def test_superseded_render_carries_banner(tmp_path):
    fam = at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path / "j"))
    old = fam.mint("design", "v1", "old", now=1.0)
    new = fam.supersede(old["id"], body="new", now=2.0)
    flipped = fam.get(old["id"])
    text = open(pj.render_atom(flipped, repo_root=str(tmp_path)), encoding="utf-8").read()
    assert "SUPERSEDED" in text and new["id"] in text


def test_draft_and_live_conversation_banners(tmp_path):
    fam = at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path / "j"))
    d = fam.mint("report", "wip", "b", status="draft", now=1.0)
    assert "DRAFT" in open(pj.render_atom(d, repo_root=str(tmp_path)), encoding="utf-8").read()
    c = fam.mint("chronicle", "thread", "b", origin="conversation", settled="live", now=2.0)
    text = open(pj.render_atom(c, repo_root=str(tmp_path)), encoding="utf-8").read()
    assert "LIVE DISCUSSION" in text and "no ruling yet" in text
