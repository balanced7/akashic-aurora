"""Shared schema for bounded, subject-explicit observations.

An observation is evidence about one named subject at one instant.  It carries
the boundary needed to keep a sample from masquerading as a total and records
its effects so a reader can distinguish looking from acting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from core.foundation.timeutil import now_iso


_TOTAL_RELATIONS = {"exact", "at_least", "unknown"}


@dataclass(frozen=True)
class Observation:
    name: str
    subject: str
    status: str
    summary: str
    source: Tuple[str, ...]
    observed_at: str = field(default_factory=now_iso)
    total: Optional[int] = None
    total_relation: str = "unknown"
    shown: Optional[int] = None
    order: str = "unspecified"
    truncated: bool = False
    effects: Tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)
    drill: str = ""

    def __post_init__(self) -> None:
        if not str(self.subject or "").strip():
            raise ValueError("observation subject is required")
        if self.total_relation not in _TOTAL_RELATIONS:
            raise ValueError(f"invalid total_relation: {self.total_relation}")
        object.__setattr__(self, "source", tuple(self.source or ()))
        object.__setattr__(self, "effects", tuple(self.effects or ()))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "subject": self.subject,
            "status": self.status,
            "summary": self.summary,
            "source": list(self.source),
            "observed_at": self.observed_at,
            "total": self.total,
            "total_relation": self.total_relation,
            "shown": self.shown,
            "order": self.order,
            "truncated": self.truncated,
            "effects": list(self.effects),
            "details": dict(self.details),
            "drill": self.drill,
        }


@dataclass(frozen=True)
class Snapshot:
    kind: str
    subject: str
    observations: Tuple[Observation, ...]
    observed_at: str = field(default_factory=now_iso)
    effects: Tuple[str, ...] = ()
    schema_version: str = "observation.snapshot.v1"

    def __post_init__(self) -> None:
        if not str(self.subject or "").strip():
            raise ValueError("snapshot subject is required")
        rows = tuple(self.observations or ())
        for row in rows:
            if row.subject != self.subject:
                raise ValueError(
                    f"observation subject {row.subject!r} does not match snapshot "
                    f"subject {self.subject!r}"
                )
        object.__setattr__(self, "observations", rows)
        if not self.effects:
            ordered = []
            for row in rows:
                for effect in row.effects:
                    if effect not in ordered:
                        ordered.append(effect)
            object.__setattr__(self, "effects", tuple(ordered))
        else:
            object.__setattr__(self, "effects", tuple(self.effects))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "subject": self.subject,
            "observed_at": self.observed_at,
            "effects": list(self.effects),
            "observations": [row.as_dict() for row in self.observations],
        }
