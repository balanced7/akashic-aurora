"""Pins for core.library.atoms (A1 core -- atom family over Store + JSONL)."""

import json
import os

import pytest

from core.library import atoms as at


class FakeStore:
    """Minimal in-memory Store surface used by AtomFamily (str-in/str-out)."""

    def __init__(self):
        self.kv = {}
        self.sets = {}
        self.zsets = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value):
        self.kv[key] = value
        return True

    def sadd(self, key, *members):
        s = self.sets.setdefault(key, set())
        before = len(s)
        s.update(members)
        return len(s) - before

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def srem(self, key, *members):
        s = self.sets.setdefault(key, set())
        n = len(s & set(members))
        s -= set(members)
        return n

    def zadd(self, key, mapping):
        z = self.zsets.setdefault(key, {})
        z.update(mapping)
        return len(mapping)

    def zrange(self, key, start, end, desc=False, withscores=False):
        z = sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1], reverse=desc)
        members = [m for m, _ in z]
        stop = None if end == -1 else end + 1
        return members[start:stop]

    def cas(self, key, expected, value):
        if self.kv.get(key) == expected:
            self.kv[key] = value
            return True
        return False

    def update_atomic(self, key, fn, retries=8):
        for _ in range(retries):
            cur = self.get(key)
            new = fn(cur)
            if new is None:
                return cur
            if self.cas(key, cur, new):
                return new
        raise RuntimeError("cas conflict")


@pytest.fixture()
def fam(tmp_path):
    return at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path))


def test_mint_roundtrip_and_indexes(fam):
    a = fam.mint("design", "Substrate Atom Family", "body text", arc="library-schema",
                 seats=["claude"], categories=["substrate", "library"], now=1000.0)
    assert a["id"].startswith("art_") and a["body_sha"] == at._sha12("body text")
    got = fam.get(a["id"])
    assert got == a
    assert got["header"]["category"] == ["substrate", "library"]
    assert a["id"] in fam.store.smembers("artifact:index:type:design")
    assert a["id"] in fam.store.smembers("artifact:index:status:current")
    assert a["id"] in fam.store.smembers("artifact:index:arc:library-schema")


def test_jsonl_appended_per_type(fam):
    fam.mint("report", "Fence report", "b", now=1000.0)
    path = os.path.join(fam.jsonl_dir, "report.jsonl")
    with open(path, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) == 1 and lines[0]["header"]["type"] == "report"


def test_validation_refuses_loudly(fam):
    with pytest.raises(at.AtomError):
        fam.mint("skill", "x", "b")  # file-plane kind, not a doc atom
    with pytest.raises(at.AtomError):
        fam.mint("design", "x", "b", categories=["not-a-category"])
    with pytest.raises(at.AtomError):
        fam.mint("design", "x", "b", categories=["bus", "ui", "wiki", "voice"])
    with pytest.raises(at.AtomError):
        fam.mint("design", "x", "b", citations=[{"target": "art_x", "rel": "supersedes"}])
    with pytest.raises(at.AtomError):
        fam.mint("design", "", "b")


def test_category_folds_resolve_at_the_door(fam):
    a = fam.mint("design", "spend telemetry", "b", categories=["spend"], now=1.0)
    assert a["header"]["category"] == ["performance"]


def test_supersede_links_both_and_moves_indexes(fam):
    old = fam.mint("design", "v1 position", "old body", arc="t101", now=1000.0)
    new = fam.supersede(old["id"], body="new body", now=2000.0)
    assert new["supersedes"] == old["id"]
    flipped = fam.get(old["id"])
    assert flipped["header"]["status"] == "superseded"
    assert flipped["superseded"] == new["id"]
    assert flipped["version"] == 2
    assert old["id"] not in fam.store.smembers("artifact:index:status:current")
    assert old["id"] in fam.store.smembers("artifact:index:status:superseded")
    assert new["id"] in fam.store.smembers("artifact:index:status:current")
    # append-only: the type JSONL now has 3 lines (mint, successor mint, flip)
    path = os.path.join(fam.jsonl_dir, "design.jsonl")
    with open(path, encoding="utf-8") as f:
        assert sum(1 for l in f if l.strip()) == 3


def test_find_intersects_facets_newest_first(fam):
    a = fam.mint("design", "bus routing one", "b", categories=["bus"], now=1.0)
    b = fam.mint("design", "bus routing two", "b", categories=["bus"], now=2.0)
    fam.mint("report", "unrelated", "b", categories=["ui"], now=3.0)
    got = fam.find(type_="design", category="bus", status="current")
    assert [x["id"] for x in got] == [b["id"], a["id"]]


def test_backlinks_are_derived_with_rel_and_status(fam):
    target = fam.mint("design", "the design", "b", now=1.0)
    src = fam.mint("report", "counter", "b",
                   citations=[{"target": target["id"], "rel": "contradicts"}], now=2.0)
    bl = fam.backlinks(target["id"])
    assert bl == [{"source": src["id"], "rel": "contradicts", "status": "current"}]


def test_conversation_provenance_fields(fam):
    a = fam.mint("chronicle", "thread capture", "deepseek: ...\nclaude: ...",
                 origin="conversation", speakers=["deepseek", "claude"],
                 source_thread="1784-0..1785-0", settled="live", now=5.0)
    assert a["origin"] == "conversation" and a["settled"] == "live"
    assert a["captured_at"] == 5.0 and a["speakers"] == ["deepseek", "claude"]


def test_rebuild_from_jsonl_restores_store(fam, tmp_path):
    old = fam.mint("design", "v1", "old", now=1000.0)
    new = fam.supersede(old["id"], body="new", now=2000.0)
    fresh = at.AtomFamily(FakeStore(), jsonl_dir=str(tmp_path))
    assert fresh.rebuild() == 2
    assert fresh.get(old["id"])["header"]["status"] == "superseded"
    assert fresh.get(new["id"])["header"]["status"] == "current"
    assert new["id"] in fresh.store.smembers("artifact:index:status:current")
    assert old["id"] not in fresh.store.smembers("artifact:index:status:current")
