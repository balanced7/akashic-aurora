"""
Slice C1 -- the Clusterer (embedding clusters + merge/split proposals).

The clustering LOGIC is tested deterministically with a FakeEmbedder (hand-placed vectors), so
domains/merge/split/salient-preservation/worst-cases are exact and always-green. A lenient
real-model test (skips if absent) + the canonical dogfood cover "sane on real data".

Amended bars (Gemini review): a high-salience atom is never force-absorbed; a high-importance
loner is preserved as its own cluster, not dropped to noise.

Run: py -m pytest tests/test_clusterer.py -q
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.clusterer import Clusterer, Cluster, Clustering


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else list(v)


class FakeEmbedder:
    """Deterministic embedder: returns a fixed unit vector per text (None if unknown)."""
    def __init__(self, table):
        self.table = table

    @property
    def available(self):
        return True

    def embed_many(self, texts):
        return [_unit(self.table[t]) if t in self.table else None for t in texts]

    def embed(self, t):
        return self.embed_many([t])[0]


def _atoms(table, importance=None):
    importance = importance or {}
    return [{"id": k, "text": k, "importance": importance.get(k, 1)} for k in table]


# ----------------------------------------------------------------- clustering logic (always on)
def test_recovers_two_domains():
    table = {"a1": [1, 0, 0], "a2": [0.95, 0.12, 0], "a3": [0.9, 0.2, 0],
             "b1": [0, 0, 1], "b2": [0.1, 0, 0.95], "b3": [0, 0.15, 0.9]}
    cl = Clusterer(FakeEmbedder(table), sim_threshold=0.3, min_cluster=3).cluster(_atoms(table))
    groups = sorted(sorted(c.atom_ids) for c in cl.clusters)
    assert groups == [["a1", "a2", "a3"], ["b1", "b2", "b3"]]
    assert all(c.cohesion > 0.8 for c in cl.clusters)


def test_deterministic_ids_across_runs():
    table = {"a1": [1, 0, 0], "a2": [0.95, 0.12, 0], "a3": [0.9, 0.2, 0]}
    mk = lambda: Clusterer(FakeEmbedder(table), sim_threshold=0.3, min_cluster=3).cluster(_atoms(table))
    assert [c.id for c in mk().clusters] == [c.id for c in mk().clusters]


def test_high_salience_loner_preserved_not_noise():
    table = {"a1": [1, 0, 0], "a2": [0.95, 0.12, 0], "a3": [0.9, 0.2, 0],
             "gem": [0, 1, 0], "noise": [0, 0, 1]}                    # two orthogonal loners
    cl = Clusterer(FakeEmbedder(table), sim_threshold=0.3, min_cluster=3).cluster(
        _atoms(table, importance={"gem": 5, "noise": 1}))
    assert any(c.salient and c.atom_ids == ["gem"] for c in cl.clusters), "high-importance loner kept"
    assert "noise" in cl.outliers and "gem" not in cl.outliers          # low-importance loner = noise


def test_ill_fitting_salient_member_is_ejected_not_absorbed():
    # a4 links to the cluster but fits poorly; being high-importance, it is ejected, not absorbed
    table = {"a1": [1, 0, 0], "a2": [0.97, 0.1, 0], "a3": [0.95, 0.2, 0], "a4": [0.5, 0.86, 0]}
    cl = Clusterer(FakeEmbedder(table), sim_threshold=0.3, min_cluster=3, salient_keep=0.8).cluster(
        _atoms(table, importance={"a4": 5}))
    assert any(c.salient and c.atom_ids == ["a4"] for c in cl.clusters)
    core = [c for c in cl.clusters if not c.salient][0]
    assert sorted(core.atom_ids) == ["a1", "a2", "a3"], "the core cluster is not polluted by a4"


def test_merge_proposal_for_near_duplicate_centroids():
    c1 = Cluster("cl_a", ["a1", "a2", "a3"], 0.9, "x", centroid=_unit([1, 0, 0]))
    c2 = Cluster("cl_b", ["b1", "b2", "b3"], 0.9, "y", centroid=_unit([0.98, 0.2, 0]))
    c3 = Cluster("cl_c", ["c1", "c2", "c3"], 0.9, "z", centroid=_unit([0, 1, 0]))
    C = Clusterer(FakeEmbedder({}))
    merges = [p for p in C.propose(Clustering([c1, c2, c3], [])) if p.kind == "merge"]
    assert len(merges) == 1 and set(merges[0].cluster_ids) == {"cl_a", "cl_b"}   # only the near-dupes


def test_split_proposal_for_bimodal_cluster():
    # a1-a2 and b1-b2 chain into ONE cluster but are two distinct sub-topics
    table = {"a1": [1, 0], "a2": [0.9, 0.44], "b1": [0, 1], "b2": [0.44, 0.9]}
    C = Clusterer(FakeEmbedder(table), sim_threshold=0.3, min_cluster=2, split_threshold=0.7)
    cl = C.cluster(_atoms(table))
    assert len(cl.clusters) == 1, "the four chain into one cluster"
    splits = [p for p in C.propose(cl) if p.kind == "split"]
    assert splits, "the bimodal cluster is flagged for split"
    parts = cl.clusters[0].split_parts
    assert parts and {tuple(sorted(parts[0])), tuple(sorted(parts[1]))} == {("a1", "a2"), ("b1", "b2")}


def test_worst_cases():
    C = Clusterer(FakeEmbedder({}), sim_threshold=0.3, min_cluster=3)
    assert C.cluster([]).clusters == [] and C.cluster([]).outliers == []          # empty
    res = C.cluster([{"id": "x", "text": "unknown"}, {"id": "y", "text": "??"}])    # no vectors
    assert res.clusters == [] and set(res.outliers) == {"x", "y"}                  # graceful fallback
    distinct = {"p": [1, 0, 0], "q": [0, 1, 0], "r": [0, 0, 1]}
    rd = Clusterer(FakeEmbedder(distinct), sim_threshold=0.3, min_cluster=3).cluster(_atoms(distinct))
    assert rd.clusters == [] and set(rd.outliers) == {"p", "q", "r"}               # all-distinct = noise
    same = {"s1": [1, 0], "s2": [1, 0], "s3": [1, 0]}
    rs = Clusterer(FakeEmbedder(same), sim_threshold=0.3, min_cluster=3).cluster(_atoms(same))
    assert len(rs.clusters) == 1 and sorted(rs.clusters[0].atom_ids) == ["s1", "s2", "s3"]


# ----------------------------------------------------------------- real model (skip if absent)
def test_real_model_clusters_a_domain():
    from core.primitives.embedder import Embedder
    emb = Embedder()
    if not emb.available:
        pytest.skip("embedding model not available")
    audio = ["stemroller separates the vocals from a song",
             "demucs splits an audio track into its stems",
             "isolate the drum stem out of a finished mix"]
    infra = ["the redis store persists agent coordination state",
             "an append-only ledger firehose of raw events",
             "the chronicler distills beats into chapters"]
    atoms = ([{"id": f"au{i}", "text": t} for i, t in enumerate(audio)] +
             [{"id": f"in{i}", "text": t} for i, t in enumerate(infra)])
    cl = Clusterer(emb, sim_threshold=0.3, min_cluster=2).cluster(atoms)
    asg = cl.assignment()
    au = [asg.get(f"au{i}") for i in range(3)]
    # at least two audio atoms share a cluster, and that cluster holds no infra atom
    shared = [c for c in set(au) if c and au.count(c) >= 2]
    assert shared, f"audio atoms should cluster by meaning, got {asg}"
    members = [a for a, c in asg.items() if c == shared[0]]
    assert all(m.startswith("au") for m in members), "the audio cluster is not polluted by infra"


if __name__ == "__main__":
    for fn in [test_recovers_two_domains, test_deterministic_ids_across_runs,
               test_high_salience_loner_preserved_not_noise,
               test_ill_fitting_salient_member_is_ejected_not_absorbed,
               test_merge_proposal_for_near_duplicate_centroids,
               test_split_proposal_for_bimodal_cluster, test_worst_cases]:
        fn()
    print("ALL C1 CLUSTERER LOGIC TESTS PASSED")
