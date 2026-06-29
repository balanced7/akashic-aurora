"""
Narrative schema (Slice 0) — the data shapes of the multi-domain narrative spine.

Semantic Relationship: Narrative derived_from Ledger (a multi-resolution view over time)

PURE SCHEMA. No behavior: no Chronicler, no TrackRouter, no Store I/O, no rendering —
those are later slices. This module defines only the node/edge shapes, their
(de)serialization, validation, and the `narr:` Store-key helpers.

Model (docs/narrative-spine-plan.md §2 + §2b):

    Atlas  →  Track  →  Chapter  →  Beat  ── points to ──>  atom (learning / commit / event)
    Theme  ─ orthogonal ─ gathers Beats across Tracks
    Edges  = relationship_types (core/foundation/relationship_types.py) — every edge's
             `type` is validated against the real 66-type vocabulary (no invented names).

Three axes: Time (when, the spine) × Track (which domain) × Theme (which idea).

Store namespace (later slices persist here as JSON on the Store):
    narr:beat:<id>   narr:chapter:<id>   narr:track:<id>   narr:theme:<id>   narr:atlas:current

Render target (Slice 3): chronicles/story.md (Obsidian-compatible) + chronicles/story.index.json.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from core.foundation.relationship_types import get_relationship_by_name

STORY_FORMAT_VERSION = "0"

# --- Store-key helpers (the `narr:` namespace) ---
NARR = "narr"
def beat_key(beat_id: str) -> str: return f"{NARR}:beat:{beat_id}"
def chapter_key(chapter_id: str) -> str: return f"{NARR}:chapter:{chapter_id}"
def track_key(track_id: str) -> str: return f"{NARR}:track:{track_id}"
def theme_key(theme_id: str) -> str: return f"{NARR}:theme:{theme_id}"
ATLAS_KEY = f"{NARR}:atlas:current"

# --- narrative weight (importance-at-write-time; Generative Agents) ---
MIN_WEIGHT, MAX_WEIGHT = 0, 5
# Default salience per Beat kind — the Chronicler surfaces high-weight Beats in
# summaries and keeps low-weight ones as quiet drill-down.
#   mark    : an explicit, agent-declared chapter boundary + title (weight 5 = salient).
#   session : session start/end markers that bound a default chapter (low salience).
DEFAULT_WEIGHT = {
    "milestone": 5, "mark": 5, "decision": 4, "learning": 4, "handoff": 4,
    "blocker": 3, "commit": 2, "note": 1, "session": 1,
}
BEAT_KINDS = tuple(DEFAULT_WEIGHT.keys())
# RC-05: 'handoff' (the most salient cross-agent event) was absent, so beat_log.emit silently
# rewrote it to a weight-1 'note' the Distiller preferentially drops. Registered at weight 4.

# Kinds that force a new Chapter boundary regardless of weight/time (explicit intent).
BOUNDARY_KINDS = ("mark",)


def clamp_weight(w: Any) -> int:
    try:
        w = int(w)
    except (TypeError, ValueError):
        w = 1
    return max(MIN_WEIGHT, min(MAX_WEIGHT, w))


def valid_relationship(type_name: str) -> bool:
    """True iff `type_name` is a real short-name in the 66-type vocabulary."""
    return bool(type_name) and get_relationship_by_name(type_name) is not None


def _as_edges(raw: Any) -> List["Edge"]:
    out: List[Edge] = []
    for e in raw or []:
        out.append(e if isinstance(e, Edge) else Edge(**e))
    return out


# ============================ nodes & edges ============================

@dataclass
class Edge:
    """A relationship-typed link to a target node. `type` MUST be a real short-name
    from core/foundation/relationship_types.py (validated, never invented)."""
    type: str
    target: str
    note: str = ""

    def is_valid(self) -> bool:
        return valid_relationship(self.type)


@dataclass
class Beat:
    """One salient, time-anchored narrative event that points to its raw atom."""
    id: str
    at: str                          # iso timestamp — the spine anchor
    kind: str                        # one of BEAT_KINDS
    summary: str
    source: str                      # followable pointer: learn:experiment:X | git:<sha> | ledger:<stream>:<id> | path:Ln
    weight: int = 1                  # narrative salience 0..5
    track: Optional[str] = None      # set by the TrackRouter (later slice)
    themes: List[str] = field(default_factory=list)
    relates: List[Edge] = field(default_factory=list)
    chapter: Optional[str] = None    # back-link (bidirectional provenance)
    # tag governance (G0): the append-only history of track opinions (TagEntry dicts).
    # `track` above is the cached current value; tag_history is the auditable record.
    # Empty for beats predating G0 (backward-compatible). See core/narrative/tagging.py.
    tag_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Beat":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


@dataclass
class Chapter:
    """A bounded coherent stretch of Beats within one Track (the mid view)."""
    id: str
    track: str
    title: str
    span_start: str
    span_end: Optional[str] = None
    summary: str = ""
    beats: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    relates: List[Edge] = field(default_factory=list)
    parent: str = ATLAS_KEY
    # bi-temporal (Zep): valid-in-world vs recorded-in-system; supersede, don't delete.
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    recorded_at: Optional[str] = None
    critic_ok: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Chapter":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


@dataclass
class Track:
    """A long-running per-domain/project thread (its own Chapters + arc)."""
    id: str                          # slug, e.g. "ai-setup"
    title: str
    domain: str = ""
    created_at: str = ""
    chapters: List[str] = field(default_factory=list)
    relates: List[Edge] = field(default_factory=list)
    centroid: Optional[List[float]] = None   # Tier-1 routing embedding (later slice)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Track":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


@dataclass
class Theme:
    """A cross-cutting idea-group that gathers Beats across Tracks (orthogonal)."""
    id: str                          # slug, e.g. "local-first"
    title: str
    description: str = ""
    beats: List[str] = field(default_factory=list)   # multi-label
    created_at: str = ""
    relates: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Theme":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


@dataclass
class Atlas:
    """The broad view across all Tracks over time."""
    generated_at: str = ""
    summary: str = ""
    tracks: List[str] = field(default_factory=list)
    relates: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Atlas":
        d = dict(d)
        d["relates"] = _as_edges(d.get("relates"))
        return cls(**d)


# ============================ validation ============================

def validate_edge(edge: Edge) -> List[str]:
    problems = []
    if not edge.target:
        problems.append("edge has no target")
    if not valid_relationship(edge.type):
        problems.append(f"edge type '{edge.type}' is not a real relationship short-name")
    return problems


def validate_beat(beat: Beat) -> List[str]:
    """Schema-level checks (no I/O). Empty list = valid."""
    problems = []
    if beat.kind not in BEAT_KINDS:
        problems.append(f"kind '{beat.kind}' not in {BEAT_KINDS}")
    if not beat.source:
        problems.append("beat has no source pointer (followable-pointer rule)")
    if not (MIN_WEIGHT <= beat.weight <= MAX_WEIGHT):
        problems.append(f"weight {beat.weight} out of range [{MIN_WEIGHT},{MAX_WEIGHT}]")
    for e in beat.relates:
        problems.extend(validate_edge(e))
    return problems
