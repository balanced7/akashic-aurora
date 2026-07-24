"""
Clusterer (Slice C1) -- group atoms by MEANING and flag where the knowledge structure should
merge or split. The Codex's curation engine; flag-only (it proposes, it never mutates).

Semantic Relationship: Atoms clustered_by Meaning -> merge/split Proposals (read-only)

Embeddings are used HERE, where they earn their keep (grouping by meaning), not as a retrieval
replacement (keyword/path still win for dense technical tokens -- the hybrid stance).

Deterministic by construction (same atoms -> same clusters + ids), so re-runs don't thrash:
  1. embed atoms (via the C0 Embedder; no model -> everything is an outlier, graceful)
  2. connected components at a cosine threshold (union-find) = candidate clusters
  3. centroid + cohesion (mean cosine to centroid) + a human-readable label per cluster
  4. **preserve high-salience outliers** -- a high-importance atom that fits a cluster poorly is
     EJECTED to its own salient singleton, never force-absorbed into a generic bucket; and a
     high-importance loner bypasses the rule-of-three (size>=3) to stand as its own resource.
     (Anti-compression bias: the machine is a librarian, not an author -- it must not optimize
     away the idiosyncratic 4-hour-debugging gem. See docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_302fc9.md amendment D6.)

Proposals (the curator, C5, decides what to do with them):
  - merge: two clusters whose centroids are near-duplicate (same topic, redundant)
  - split: one cluster that is internally bimodal (two distinct sub-topics under one roof);
    the two sub-groups are computed at cluster time (we have the vectors) and carried on the
    Cluster so `propose()` stays pure.
"""
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from core.primitives.embedder import Embedder, get_embedder


@dataclass
class Cluster:
    id: str
    atom_ids: List[str]
    cohesion: float                       # mean cosine of members to the centroid (0..1)
    label: str                            # the most-central member's text (human handle)
    centroid: List[float] = field(default_factory=list)
    salient: bool = False                 # a preserved high-importance atom/anchor
    split_score: float = 0.0              # >0 if internally bimodal (distinctness of the two halves)
    split_parts: Optional[Tuple[List[str], List[str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "atom_ids": self.atom_ids, "cohesion": round(self.cohesion, 3),
                "label": self.label, "salient": self.salient,
                "split_score": round(self.split_score, 3)}


@dataclass
class Clustering:
    clusters: List[Cluster]
    outliers: List[str]                   # low-importance loners (noise; not a resource)

    def assignment(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for c in self.clusters:
            for a in c.atom_ids:
                out[a] = c.id
        return out


@dataclass
class Proposal:
    kind: str                             # "merge" | "split"
    cluster_ids: List[str]
    score: float                          # 0..1 (centroid sim for merge; distinctness for split)
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "cluster_ids": self.cluster_ids,
                "score": round(self.score, 3), "reason": self.reason}


def _cluster_id(atom_ids: Sequence[str]) -> str:
    h = hashlib.md5("|".join(sorted(atom_ids)).encode("utf-8")).hexdigest()[:12]
    return f"cl_{h}"


class Clusterer:
    def __init__(self, embedder: Optional[Embedder] = None, *,
                 sim_threshold: float = 0.45, min_cluster: int = 3,
                 salient_importance: float = 4.0, salient_keep: float = 0.55,
                 merge_threshold: float = 0.82, split_threshold: float = 0.40):
        self.embedder = embedder or get_embedder()
        self.sim_threshold = sim_threshold      # edge if cosine >= this
        self.min_cluster = min_cluster          # rule of three: no (non-salient) cluster below this
        self.salient_importance = salient_importance
        self.salient_keep = salient_keep        # a salient member below this cos-to-centroid is ejected
        self.merge_threshold = merge_threshold
        self.split_threshold = split_threshold  # two halves with inter-centroid cos below this = bimodal

    # ------------------------------------------------------------------ cluster
    def cluster(self, atoms: Sequence[Dict[str, Any]]) -> Clustering:
        """atoms: dicts with `id`, `text`, optional `importance`. Returns a Clustering. Never raises."""
        ids = [str(a.get("id", i)) for i, a in enumerate(atoms)]
        imp = [float(a.get("importance", 1) or 1) for a in atoms]
        vecs = self.embedder.embed_many([a.get("text", "") for a in atoms])
        have = [i for i, v in enumerate(vecs) if v is not None]
        if not have:
            return Clustering([], list(ids))     # no model -> all outliers (graceful, no crash)

        V = np.array([vecs[i] for i in have], dtype=float)        # unit-normalized rows
        sims = V @ V.T
        n = len(have)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a in range(n):                                        # union at the threshold
            for b in range(a + 1, n):
                if sims[a, b] >= self.sim_threshold:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)         # lower root -> deterministic

        comps: Dict[int, List[int]] = {}
        for a in range(n):
            comps.setdefault(find(a), []).append(a)

        clusters: List[Cluster] = []
        outliers: List[str] = [ids[i] for i in range(len(atoms)) if i not in have]

        for members in sorted(comps.values(), key=lambda ms: min(have[m] for m in ms)):
            keep, ejected = self._eject_ill_fitting_salient(members, V, imp, have)
            if len(keep) >= self.min_cluster:
                clusters.append(self._build_cluster(keep, V, atoms, ids, have))
            else:
                ejected = sorted(set(ejected) | set(keep))       # too small to be a resource
            for m in ejected:
                gi = have[m]
                if imp[gi] >= self.salient_importance:
                    clusters.append(self._build_cluster([m], V, atoms, ids, have, salient=True))
                else:
                    outliers.append(ids[gi])

        clusters.sort(key=lambda c: c.atom_ids[0])
        return Clustering(clusters, sorted(set(outliers)))

    def _eject_ill_fitting_salient(self, members: List[int], V, imp: List[float],
                                   have: List[int]) -> Tuple[List[int], List[int]]:
        """A high-importance member that fits the cluster poorly is pulled out (never absorbed)."""
        if len(members) <= 1:
            return list(members), []
        centroid = self._centroid(V[members])
        keep, ejected = [], []
        for m in members:
            cos = float(V[m] @ centroid)
            if imp[have[m]] >= self.salient_importance and cos < self.salient_keep:
                ejected.append(m)
            else:
                keep.append(m)
        return keep, ejected

    @staticmethod
    def _centroid(rows) -> np.ndarray:
        c = rows.mean(axis=0)
        nrm = np.linalg.norm(c)
        return c / nrm if nrm > 0 else c

    def _build_cluster(self, local: List[int], V, atoms, ids, have: List[int],
                       *, salient: bool = False) -> Cluster:
        rows = V[local]
        centroid = self._centroid(rows)
        coss = [float(rows[k] @ centroid) for k in range(len(local))]
        cohesion = float(sum(coss) / len(coss)) if coss else 1.0
        atom_ids = [ids[have[m]] for m in local]
        label = str(atoms[have[local[int(np.argmax(coss))]]].get("text", ""))[:80]
        split_score, split_parts = 0.0, None
        if len(local) >= 2 * self.min_cluster:
            split_score, split_parts = self._bimodality(atom_ids, rows)
        return Cluster(id=_cluster_id(atom_ids), atom_ids=atom_ids, cohesion=cohesion, label=label,
                       centroid=[float(x) for x in centroid], salient=salient,
                       split_score=split_score, split_parts=split_parts)

    def _bimodality(self, atom_ids: List[str], rows) -> Tuple[float, Optional[Tuple[List[str], List[str]]]]:
        """Split by the two least-similar 'poles'; bimodal if both halves are >=min_cluster and
        their centroids are distinct (inter-cosine < split_threshold). Deterministic."""
        n = len(atom_ids)
        sims = rows @ rows.T
        pa, pb, lo = 0, 1, 2.0
        for a in range(n):
            for b in range(a + 1, n):
                if sims[a, b] < lo:
                    lo, pa, pb = sims[a, b], a, b
        ga = [k for k in range(n) if sims[k, pa] >= sims[k, pb]]
        gb = [k for k in range(n) if k not in ga]
        if len(ga) < self.min_cluster or len(gb) < self.min_cluster:
            return 0.0, None
        inter = float(self._centroid(rows[ga]) @ self._centroid(rows[gb]))
        if inter >= self.split_threshold:
            return 0.0, None
        return 1.0 - inter, ([atom_ids[k] for k in ga], [atom_ids[k] for k in gb])

    # ------------------------------------------------------------------ propose (flag-only)
    def propose(self, clustering: Clustering) -> List[Proposal]:
        """Flag-only merge/split candidates, worst-first by score. NEVER mutates."""
        out: List[Proposal] = []
        cl = [c for c in clustering.clusters if not c.salient and c.centroid]
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                cos = float(np.array(cl[i].centroid) @ np.array(cl[j].centroid))
                if cos >= self.merge_threshold:
                    out.append(Proposal("merge", [cl[i].id, cl[j].id], cos,
                                        f"centroids near-duplicate (cos={cos:.2f})"))
        for c in cl:
            if c.split_score > 0 and c.split_parts:
                out.append(Proposal("split", [c.id], c.split_score,
                                    f"bimodal {len(c.split_parts[0])}+{len(c.split_parts[1])} "
                                    f"(distinctness={c.split_score:.2f})"))
        out.sort(key=lambda p: -p.score)
        return out


_INSTANCE: Optional[Clusterer] = None


def get_clusterer(embedder: Optional[Embedder] = None) -> Clusterer:
    global _INSTANCE
    if embedder is not None:
        return Clusterer(embedder)
    if _INSTANCE is None:
        _INSTANCE = Clusterer()
    return _INSTANCE
