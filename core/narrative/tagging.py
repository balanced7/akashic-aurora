"""
Tag governance (Slice G0) -- tag-history + confidence schema. Pure data + selection
logic. NO behavior change to routing, NO I/O. See docs/tag-governance-plan.md.

A tag is a re-derivable OPINION over an immutable FACT. So a Beat's `track` is not a
single value but an APPEND-ONLY history of dated, confidence-scored opinions; the
"current" tag is *derived* (the most trustworthy one), never destructively overwritten.

  TagEntry  : {value, confidence, source, at, confirmed}
  TagHistory: append-only list; current() = max by (confirmed, confidence, recency);
              rollback_to() RE-ASSERTS a prior value (appends) -- never deletes.

This makes successive cleanup runs structurally non-destructive (invariants I3 append-only,
I4 reversible): the worst a bad re-tag can do is sit in the history and lose the current()
ranking. G1 adds the confidence-gated write path on top of this.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# Router basis (and other sources) -> a confidence in [0,1]. Higher = more trustworthy.
BASIS_CONFIDENCE = {
    "human": 1.0,       # an explicit human/agent confirmation -- the strongest
    "path": 0.95,       # a commit's touched files -- unambiguous
    "strong": 0.85,     # a strong domain keyword
    "embedding": 0.75,  # Tier-1 embedding nearest-track (Slice 6)
    "category": 0.6,    # a learning/decision category
    "generic": 0.4,     # a weak topic keyword
    "persist": 0.3,     # inherited active track (no signal)
    "rollback": 0.3,    # re-asserted prior value (recency wins the tie, not confidence)
    "unknown": 0.1,     # no signal at all
}


def confidence_for(source: str) -> float:
    """Confidence for a source/basis name; unknown sources get a neutral 0.5."""
    return BASIS_CONFIDENCE.get(source, 0.5)


@dataclass
class TagEntry:
    value: str                 # the tag (a track id, or later a theme)
    confidence: float          # [0,1]
    source: str = ""           # path|strong|embedding|category|generic|persist|human|rollback|unknown
    at: str = ""               # iso timestamp (iso8601 sorts lexically = chronologically)
    confirmed: bool = False    # a human/agent pin -- auto-processes must never override

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TagEntry":
        return cls(**dict(d))


class TagHistory:
    """An append-only history of tag opinions for one node. The current tag is derived."""

    def __init__(self, entries: Optional[List[TagEntry]] = None):
        self.entries: List[TagEntry] = list(entries or [])

    # --- writes (append-only) ---
    def append(self, entry: TagEntry) -> TagEntry:
        self.entries.append(entry)
        return entry

    def add(self, value: str, *, source: str = "unknown", at: str = "",
            confidence: Optional[float] = None, confirmed: bool = False) -> TagEntry:
        conf = 1.0 if confirmed else (confidence if confidence is not None else confidence_for(source))
        return self.append(TagEntry(value=value, confidence=float(conf),
                                    source=("human" if confirmed else source), at=at, confirmed=confirmed))

    def rollback_to(self, value: str, *, at: str) -> Optional[TagEntry]:
        """Re-assert a PRIOR value so it becomes current again -- by APPENDING (the older
        entries stay; reversibility without destruction, I3+I4). A rollback is a DELIBERATE
        correction, so it's pinned (confirmed=1.0) -- it must win over the bad auto-tag it
        undoes, and not be silently re-overridden. Returns the new entry, or None if the
        value was never tagged."""
        prior = [e for e in self.entries if e.value == value]
        if not prior:
            return None
        return self.append(TagEntry(value=value, confidence=1.0,
                                    source="rollback", at=at, confirmed=True))

    # --- reads (derived) ---
    def current(self) -> Optional[TagEntry]:
        """The most trustworthy opinion: max by (confirmed, confidence, recency).
        Corrupt/valueless entries are ignored, not fatal. Empty -> None."""
        valid = [e for e in self.entries if e.value]
        if not valid:
            return None
        return max(valid, key=lambda e: (e.confirmed, e.confidence, e.at or ""))

    def current_value(self, default: str = "unknown") -> str:
        cur = self.current()
        return cur.value if cur else default

    def current_confidence(self, default: float = 0.1) -> float:
        cur = self.current()
        return cur.confidence if cur else default

    # --- serialization ---
    def to_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.entries]

    @classmethod
    def from_list(cls, raw: Any) -> "TagHistory":
        out: List[TagEntry] = []
        for d in raw or []:
            try:
                e = d if isinstance(d, TagEntry) else TagEntry(**d)
                float(e.confidence)      # corrupt confidence -> skip this entry
                out.append(e)
            except (TypeError, ValueError):
                continue                 # robustness: a corrupt entry is skipped, not fatal
        return cls(out)
