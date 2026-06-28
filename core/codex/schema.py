"""
Resource schema (Slice C2) -- the knowledge-axis node + the structural bi-temporal contract.

Semantic Relationship: Resource distilled_from AtomCluster (regenerable, supersedable)

A Resource is a derived, regenerable projection over a cluster of immutable atoms. Per the
pre-build review (deltas E1-E2):

- **E1 stable identity, not membership-derived.** `id` is assigned ONCE (`new_resource_id`) and
  never changes; `version_hash` (over atom_ids + summary) tracks the CONTENT. A merge/split is a
  supersession (new ids supersede old; old keep their ids + a `replaces` edge), so inbound links
  forward rather than break -- which a content-derived id would guarantee on every membership change.
- **E2 numeric confidence, no maturity ladder.** `confidence` is kept because it drives real
  behavior (Ranker weight + the C6 auto-apply gate); the seedling->evergreen ladder is cut (it had
  no transition logic or downstream effect).

`BiTemporal` is the structural protocol the shared lifecycle (core/codex/lifecycle.py) operates on
-- Chapter and Resource both satisfy it WITHOUT a common base class (delta E3).
"""
import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from core.narrative.schema import Edge, _as_edges      # the 66-type-validated edge (same layer)

CODEX = "codex"


def resource_key(rid: str) -> str:
    return f"{CODEX}:resource:{rid}"


def new_resource_id() -> str:
    """A STABLE, non-semantic id assigned once per Resource (never membership-derived)."""
    return f"res_{uuid.uuid4().hex[:12]}"


def version_hash(atom_ids: List[str], summary: str) -> str:
    """A content fingerprint (membership + summary) for idempotent regenerate / change-detection."""
    blob = "|".join(sorted(str(a) for a in atom_ids)) + "::" + (summary or "")
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


@runtime_checkable
class BiTemporal(Protocol):
    """The structural contract the shared lifecycle needs -- satisfied by Chapter AND Resource."""
    id: str
    valid_from: Optional[str]
    valid_to: Optional[str]
    recorded_at: Optional[str]
    relates: List[Edge]


@dataclass
class Resource:
    """A distilled, regenerable knowledge node over a cluster of atoms (stable id; bi-temporal)."""
    id: str
    title: str = ""
    summary: str = ""
    atom_ids: List[str] = field(default_factory=list)    # lossless provenance (no atom orphaned)
    centroid: List[float] = field(default_factory=list)  # embedding handle
    confidence: float = 0.5                               # drives Ranker weight + the C6 gate
    valid_from: Optional[str] = None                      # bi-temporal (world time)
    valid_to: Optional[str] = None                        # open = active; closed = superseded (canonical)
    recorded_at: Optional[str] = None                     # bi-temporal (system time)
    relates: List[Edge] = field(default_factory=list)     # replaces / is_version_of / part_of
    version_hash: str = ""
    parent: Optional[str] = None                          # tree link (a higher-level Resource)

    def compute_version(self) -> str:
        return version_hash(self.atom_ids, self.summary)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Resource":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


def new_resource(*, atom_ids: List[str], title: str = "", summary: str = "",
                 centroid: Optional[List[float]] = None, confidence: float = 0.5,
                 id: Optional[str] = None) -> Resource:
    """Mint a Resource with a fresh stable id and a computed version_hash."""
    r = Resource(id=id or new_resource_id(), title=title, summary=summary,
                 atom_ids=list(atom_ids), centroid=list(centroid or []), confidence=confidence)
    r.version_hash = r.compute_version()
    return r
