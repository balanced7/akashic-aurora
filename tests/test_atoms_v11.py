"""Pins for atom-design v1.1 (Daniel gate 2026-07-24, reconciled atom
art_20260724_atom-design-reconciled-v1-1_fd2275): schema versioning, body_type +
detection-confidence stamp, inverse backlink index + its lie-detector, resolution
laws, the cites->discusses fold, and the tenant demotion. Hermetic (FakeStore)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.library import atoms as at
from core.library import taxonomy as tx
from core.library.projection import frontmatter
from tests.test_atoms import FakeStore


def _fam(tmp_path):
    return at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path), repo_root=str(tmp_path))


# ---------------------------------------------------------------- schema_version
def test_mint_stamps_schema_version(tmp_path):
    a = _fam(tmp_path).mint("design", "v11 stamp", "body text here")
    assert a["schema_version"] == at.SCHEMA_VERSION == 1


def test_absent_schema_version_reads_as_v1(tmp_path):
    fam = _fam(tmp_path)
    a = fam.mint("design", "legacy shape", "old corpus atom")
    raw = __import__("json").loads(fam.store.get(at.KEY_PREFIX + a["id"]))
    raw.pop("schema_version")
    fam.store.set(at.KEY_PREFIX + a["id"], __import__("json").dumps(raw))
    got = fam.get(a["id"])
    assert got is not None and int(got.get("schema_version", 1)) == 1


def test_newer_schema_version_refuses_loud(tmp_path):
    fam = _fam(tmp_path)
    a = fam.mint("design", "future shape", "body")
    raw = __import__("json").loads(fam.store.get(at.KEY_PREFIX + a["id"]))
    raw["schema_version"] = at.SCHEMA_KNOWN_MAX + 1
    fam.store.set(at.KEY_PREFIX + a["id"], __import__("json").dumps(raw))
    with pytest.raises(at.AtomError):
        fam.get(a["id"])


# ---------------------------------------------------------------- body_type
def test_explicit_body_type_rides_with_flag_source(tmp_path):
    a = _fam(tmp_path).mint("report", "typed body", "SELECT 1;",
                            body_type="code", body_type_source="flag")
    assert a["header"]["body_type"] == "code"
    assert a["body_type_source"] == "flag"


def test_auto_detect_transcript_stamps_auto(tmp_path):
    convo = "\n".join(f"{'daniel' if i % 2 else 'claude'}: line {i} of the exchange"
                      for i in range(12))
    a = _fam(tmp_path).mint("chronicle", "captured thread", convo)
    assert a["header"]["body_type"] == "transcript"
    assert a["body_type_source"] == "auto"


def test_default_body_is_markdown(tmp_path):
    a = _fam(tmp_path).mint("design", "plain prose", "just some position text")
    assert a["header"]["body_type"] == "markdown"


def test_bad_body_type_refused(tmp_path):
    with pytest.raises(at.AtomError):
        _fam(tmp_path).mint("design", "nope", "x", body_type="video")


# ---------------------------------------------------------------- tenant demotion
def test_tenant_no_longer_stored_visibility_stays(tmp_path):
    a = _fam(tmp_path).mint("design", "cut check", "body", tenant="solo")
    assert "tenant" not in a["header"]
    assert a["header"]["visibility"] == "fleet"


# ---------------------------------------------------------------- rel fold
def test_cites_folds_to_discusses_at_mint(tmp_path):
    fam = _fam(tmp_path)
    tgt = fam.mint("design", "target", "t")
    a = fam.mint("report", "citer", "c",
                 citations=[{"target": tgt["id"], "rel": "cites"}])
    assert a["citations_out"][0]["rel"] == "discusses"


def test_unknown_rel_refused(tmp_path):
    fam = _fam(tmp_path)
    tgt = fam.mint("design", "target2", "t")
    with pytest.raises(at.AtomError):
        fam.mint("report", "bad rel", "c",
                 citations=[{"target": tgt["id"], "rel": "vibes-with"}])


# ---------------------------------------------------------------- inverse index
def test_backlinks_ride_the_index_and_match_the_scan(tmp_path):
    fam = _fam(tmp_path)
    a = fam.mint("design", "the design", "d")
    b = fam.mint("report", "the report", "r",
                 citations=[{"target": a["id"], "rel": "derives-from"}])
    got = fam.backlinks(a["id"])
    assert [x["source"] for x in got] == [b["id"]]
    assert got[0]["rel"] == "derives-from"
    scan = fam.backlinks_scan(a["id"])
    assert {x["source"] for x in got} == {x["source"] for x in scan}


def test_verify_backlink_index_clean_then_catches_tampering(tmp_path):
    fam = _fam(tmp_path)
    a = fam.mint("design", "idx target", "d")
    fam.mint("report", "idx citer", "r",
             citations=[{"target": a["id"], "rel": "supports"}])
    assert fam.verify_backlink_index() == []
    fam.store.sadd(at._idx_key("cited-by", a["id"]), "art_20990101_phantom_000000")
    rows = fam.verify_backlink_index()
    assert rows and any("INDEX-PHANTOM" in r for r in rows)


# ---------------------------------------------------------------- resolution laws
def test_lineage_resolve_current_and_lineage_backlinks(tmp_path):
    fam = _fam(tmp_path)
    v1 = fam.mint("design", "the spec", "first version")
    citer = fam.mint("report", "built on v1", "evidence",
                     citations=[{"target": v1["id"], "rel": "derives-from"}])
    v2 = fam.supersede(v1["id"], body="second version")
    assert fam.lineage(v2["id"]) == [v1["id"], v2["id"]]
    head = fam.resolve_current(v1["id"])
    assert head is not None and head["id"] == v2["id"]
    direct = fam.backlinks(v2["id"])
    assert direct == []                      # the decay the law exists to fix
    lineage = fam.backlinks(v2["id"], lineage=True)
    assert citer["id"] in {x["source"] for x in lineage}


def test_supersede_inherits_body_type(tmp_path):
    fam = _fam(tmp_path)
    v1 = fam.mint("report", "typed v1", "x = 1\ny = 2", body_type="code",
                  body_type_source="flag")
    v2 = fam.supersede(v1["id"], body="x = 1\ny = 3")
    assert v2["header"]["body_type"] == "code"
    assert v2["body_type_source"] == "flag"


# ---------------------------------------------------------------- projection face
def test_frontmatter_carries_version_and_body_type(tmp_path):
    a = _fam(tmp_path).mint("design", "render me", "body", body_type="markdown",
                            body_type_source="flag")
    fm = frontmatter(a)
    assert "schema_version: 1" in fm
    assert "body_type: markdown" in fm
    assert "tenant" not in fm


def test_frontmatter_legacy_atom_defaults_body_type(tmp_path):
    fam = _fam(tmp_path)
    a = fam.mint("design", "legacy render", "body")
    a["header"].pop("body_type")
    a["header"]["tenant"] = "solo"          # legacy shape carried it
    fm = frontmatter(a)
    assert "body_type: markdown" in fm
    assert "tenant: solo" in fm
