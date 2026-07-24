"""
Perspectives schema (Slice P0) -- Lens + Map shapes. Pure data, no behavior.

Semantic Relationship: View derived_from (Map x Lens) over Substrate (read-only)

- **Map** = a STRUCTURAL projection: which relationship-type *domains* (causal / temporal /
  structural / ...) form the graph you traverse. Selects a sub-graph of the substrate.
- **Lens / Perspective** = a VALUE-SET: factor weights (relevance/importance/recency/
  strength) + per-relation weights + an optional focus seed. Parameterizes the Ranker.

Swap a Map (how the territory is wired) or a Lens (what matters on it) over the immutable
substrate -> a different surfaced view. Everything validates against the REAL 66-type
vocabulary (no invented relation names). See docs/library/design/20260709_perspectives-maps-build-plan-the-interpr_5a5e0a.md.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from core.foundation.relationship_types import RelationshipType, get_relationship_by_name

# the real relationship-type domains (causal, temporal, structural, semantic, ...)
VALID_DOMAINS = {rt.value.domain for rt in RelationshipType}

# factor knobs a Lens may weight (must match the Ranker's blendable factors)
FACTORS = ("relevance", "importance", "recency", "strength")


def lens_key(name: str) -> str: return f"persp:lens:{name}"
def map_key(name: str) -> str: return f"persp:map:{name}"


def valid_relationship(short_name: str) -> bool:
    return bool(short_name) and get_relationship_by_name(short_name) is not None


@dataclass
class Lens:
    """A value-set tuning what gets surfaced. Reuses the Ranker; never mutates data."""
    name: str
    factor_weights: Dict[str, float] = field(default_factory=dict)   # relevance/importance/recency/strength
    relation_weights: Dict[str, float] = field(default_factory=dict)  # short_name -> weight
    seed: Optional[str] = None     # focus node id (personalization, for spreading activation later)
    goal: str = ""

    def validate(self) -> List[str]:
        problems = []
        for f in self.factor_weights:
            if f not in FACTORS:
                problems.append(f"factor '{f}' not in {FACTORS}")
        for f, v in self.factor_weights.items():
            if not isinstance(v, (int, float)):
                problems.append(f"factor '{f}' weight must be numeric")
        for rel in self.relation_weights:
            if not valid_relationship(rel):
                problems.append(f"relation '{rel}' is not a real relationship short-name")
        return problems

    def to_dict(self) -> Dict[str, Any]: return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Lens": return cls(**dict(d))


@dataclass
class Map:
    """A structural projection: which relationship-type domains form the traversed graph."""
    name: str
    relation_domains: List[str] = field(default_factory=list)   # subset of VALID_DOMAINS
    node_kinds: List[str] = field(default_factory=list)         # beat kinds to include ([] = all)
    direction: str = "both"                                     # forward | backward | both

    def validate(self) -> List[str]:
        problems = []
        for d in self.relation_domains:
            if d not in VALID_DOMAINS:
                problems.append(f"domain '{d}' not in {sorted(VALID_DOMAINS)}")
        if self.direction not in ("forward", "backward", "both"):
            problems.append(f"direction '{self.direction}' invalid")
        return problems

    def to_dict(self) -> Dict[str, Any]: return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Map": return cls(**dict(d))


# --- a FEW concrete built-ins (not a config sea -- rule of three) ---
BUILTIN_LENSES = {
    "causal": Lens("causal", {"relevance": 0.3, "importance": 0.3, "recency": 0.1, "strength": 0.3},
                   {"causes": 1.0, "prevents": 1.0, "influences": 0.8, "develops_into": 0.8},
                   goal="why did this happen / what unblocked what"),
    "recency": Lens("recency", {"relevance": 0.2, "importance": 0.2, "recency": 0.6, "strength": 0.0},
                    goal="what's hot right now"),
    "thematic": Lens("thematic", {"relevance": 0.3, "importance": 0.2, "recency": 0.1, "strength": 0.4},
                     {"member_of": 1.0, "instance_of": 1.0, "related_to": 0.8, "similar_to": 0.8},
                     goal="this idea across domains"),
}
BUILTIN_MAPS = {
    "narrative": Map("narrative", ["temporal", "structural"]),
    "causal": Map("causal", ["causal"]),
    "dependency": Map("dependency", ["associative"]),     # depends_on / requires / supports
}
