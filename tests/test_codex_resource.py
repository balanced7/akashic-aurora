"""
Slice C2 -- Resource schema + shared bi-temporal lifecycle (pre-build-review design E1-E4).

Bars: id STABLE across regenerate + across membership change (merge/split -> new entities
supersede, old id intact, links forward); no atom orphaned; is_active excludes a valid_to-closed
node (the latent Ranker bug, E4); a retired Resource ranks out.

Run: py -m pytest tests/test_codex_resource.py -q
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.codex import lifecycle
from core.codex.schema import Resource, new_resource, resource_key, new_resource_id, version_hash
from core.primitives.supersession import is_active as ranker_is_active
from core.primitives.ranker import Ranker


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _load(store, rid):
    return Resource.from_dict(json.loads(store.get(resource_key(rid))))


def test_schema_roundtrip_and_stable_id():
    r = new_resource(atom_ids=["a", "b"], title="t", summary="s")
    assert r.id.startswith("res_") and r.version_hash == version_hash(["a", "b"], "s")
    assert Resource.from_dict(r.to_dict()) == r
    assert new_resource_id() != new_resource_id()                     # ids are unique
    # version_hash tracks CONTENT, not identity
    assert version_hash(["a", "b"], "s") != version_hash(["a", "b", "c"], "s")
    assert version_hash(["a", "b"], "s") != version_hash(["a", "b"], "s2")


def test_regenerate_keeps_id_and_origin_idempotent():
    store = _store()
    r = new_resource(atom_ids=["a", "b", "c"], summary="s", id="res_fixed")
    lifecycle.regenerate_in_place(store, r, resource_key, now="2026-01-01T00:00:00")
    first = _load(store, "res_fixed")
    assert first.valid_from == "2026-01-01T00:00:00" == first.recorded_at
    # identical content later -> NO rewrite (recorded_at frozen), id stable
    r2 = new_resource(atom_ids=["a", "b", "c"], summary="s", id="res_fixed")
    lifecycle.regenerate_in_place(store, r2, resource_key, now="2026-06-01T00:00:00")
    assert _load(store, "res_fixed").recorded_at == "2026-01-01T00:00:00"
    # CHANGED content -> rewrite, but the origin valid_from is preserved + id stable
    r3 = new_resource(atom_ids=["a", "b", "c", "d"], summary="s2", id="res_fixed")
    lifecycle.regenerate_in_place(store, r3, resource_key, now="2026-07-01T00:00:00")
    upd = _load(store, "res_fixed")
    assert upd.recorded_at == "2026-07-01T00:00:00" and upd.valid_from == "2026-01-01T00:00:00"
    assert upd.id == "res_fixed"


def test_supersede_forwards_links_and_keeps_old():
    store = _store()
    old = new_resource(atom_ids=["a", "b", "c"], summary="old", id="res_old")
    lifecycle.regenerate_in_place(store, old, resource_key, now="2026-01-01T00:00:00")
    new = new_resource(atom_ids=["a", "b", "c", "d"], summary="refined", id="res_new")
    lifecycle.supersede(store, old, new, resource_key, now="2026-02-01T00:00:00")
    so, sn = _load(store, "res_old"), _load(store, "res_new")
    assert so.valid_to == "2026-02-01T00:00:00" and not lifecycle.is_active(so)   # retired, NOT deleted
    assert lifecycle.is_active(sn)                                                # new active
    assert any(e.type == "replaces" and e.target == "res_new" for e in so.relates)        # forwards
    assert any(e.type == "is_version_of" and e.target == "res_old" for e in sn.relates)
    assert so.id == "res_old" and sn.id == "res_new"                             # stable, distinct ids


def test_merge_as_supersession_no_atom_orphaned():
    store = _store()
    a = new_resource(atom_ids=["a1", "a2", "a3"], summary="A", id="res_a")
    b = new_resource(atom_ids=["b1", "b2", "b3"], summary="B", id="res_b")
    for r in (a, b):
        lifecycle.regenerate_in_place(store, r, resource_key, now="2026-01-01T00:00:00")
    merged = new_resource(atom_ids=a.atom_ids + b.atom_ids, summary="A+B", id="res_ab")
    lifecycle.supersede(store, a, merged, resource_key, now="2026-02-01T00:00:00")
    lifecycle.supersede(store, b, merged, resource_key, now="2026-02-01T00:00:00")
    sa, sb, sm = _load(store, "res_a"), _load(store, "res_b"), _load(store, "res_ab")
    assert not lifecycle.is_active(sa) and not lifecycle.is_active(sb) and lifecycle.is_active(sm)
    assert set(sa.atom_ids + sb.atom_ids) <= set(sm.atom_ids), "no atom orphaned by the merge"
    assert {e.target for e in sm.relates if e.type == "is_version_of"} == {"res_a", "res_b"}


def test_split_as_supersession_no_atom_lost():
    store = _store()
    whole = new_resource(atom_ids=["x1", "x2", "x3", "y1", "y2", "y3"], summary="whole", id="res_w")
    lifecycle.regenerate_in_place(store, whole, resource_key, now="2026-01-01T00:00:00")
    left = new_resource(atom_ids=["x1", "x2", "x3"], summary="X", id="res_x")
    right = new_resource(atom_ids=["y1", "y2", "y3"], summary="Y", id="res_y")
    lifecycle.supersede(store, whole, left, resource_key, now="2026-02-01T00:00:00")
    lifecycle.supersede(store, whole, right, resource_key, now="2026-02-01T00:00:00")
    sw = _load(store, "res_w")
    assert not lifecycle.is_active(sw)
    survived = set(_load(store, "res_x").atom_ids) | set(_load(store, "res_y").atom_ids)
    assert set(whole.atom_ids) <= survived, "every atom survives the split"


def test_e4_is_active_honors_valid_to():
    assert ranker_is_active({}) is True                                  # legacy, neither field
    assert ranker_is_active({"superseded": True}) is False               # simple field
    assert ranker_is_active({"valid_to": "2026-01-01T00:00:00"}) is False  # bi-temporal closed (the fix)
    assert ranker_is_active({"valid_to": None}) is True                  # open
    assert ranker_is_active({"superseded": True, "valid_to": "x"}) is False


def test_ranker_excludes_retired_resource():
    items = [{"text": "active resource", "valid_to": None, "importance": 3},
             {"text": "retired resource", "valid_to": "2026-01-01T00:00:00", "importance": 5}]
    texts = [s.item["text"] for s in Ranker().rank(items, "")]
    assert "active resource" in texts and "retired resource" not in texts


if __name__ == "__main__":
    for fn in [test_schema_roundtrip_and_stable_id, test_regenerate_keeps_id_and_origin_idempotent,
               test_supersede_forwards_links_and_keeps_old, test_merge_as_supersession_no_atom_orphaned,
               test_split_as_supersession_no_atom_lost, test_e4_is_active_honors_valid_to,
               test_ranker_excludes_retired_resource]:
        fn()
    print("ALL C2 RESOURCE/LIFECYCLE TESTS PASSED")
