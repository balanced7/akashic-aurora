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
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

from core.narrative.schema import Edge, _as_edges  # the 66-type-validated edge (same layer)

CODEX = "codex"


def resource_key(rid: str) -> str:
    return f"{CODEX}:resource:{rid}"


def new_resource_id() -> str:
    """A STABLE, non-semantic id assigned once per Resource (never membership-derived)."""
    return f"res_{uuid.uuid4().hex[:12]}"


def version_hash(atom_ids: list[str], summary: str) -> str:
    """A content fingerprint (membership + summary) for idempotent regenerate / change-detection."""
    blob = "|".join(sorted(str(a) for a in atom_ids)) + "::" + (summary or "")
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


@runtime_checkable
class BiTemporal(Protocol):
    """The structural contract the shared lifecycle needs -- satisfied by Chapter AND Resource."""

    id: str
    valid_from: str | None
    valid_to: str | None
    recorded_at: str | None
    relates: list[Edge]


@dataclass
class Resource:
    """A distilled, regenerable knowledge node over a cluster of atoms (stable id; bi-temporal)."""

    id: str
    title: str = ""
    summary: str = ""
    atom_ids: list[str] = field(default_factory=list)  # lossless provenance (no atom orphaned)
    centroid: list[float] = field(default_factory=list)  # embedding handle
    confidence: float = 0.5  # drives Ranker weight + the C6 gate
    valid_from: str | None = None  # bi-temporal (world time)
    valid_to: str | None = None  # open = active; closed = superseded (canonical)
    recorded_at: str | None = None  # bi-temporal (system time)
    relates: list[Edge] = field(default_factory=list)  # replaces / is_version_of / part_of
    version_hash: str = ""
    parent: str | None = None  # tree link (a higher-level Resource)

    def compute_version(self) -> str:
        return version_hash(self.atom_ids, self.summary)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Resource":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


def new_resource(
    *,
    atom_ids: list[str],
    title: str = "",
    summary: str = "",
    centroid: list[float] | None = None,
    confidence: float = 0.5,
    id: str | None = None,  # public API name
) -> Resource:
    """Mint a Resource with a fresh stable id and a computed version_hash."""
    r = Resource(
        id=id or new_resource_id(),
        title=title,
        summary=summary,
        atom_ids=list(atom_ids),
        centroid=list(centroid or []),
        confidence=confidence,
    )
    r.version_hash = r.compute_version()
    return r
