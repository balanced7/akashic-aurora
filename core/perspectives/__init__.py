"""
core.perspectives -- the interpretation layer over the narrative graph (System 4).

The substrate (Ledger + beats + typed edges) stays sacred and immutable. This layer is
swappable: Maps (structural projections) + Perspectives/Lenses (value-sets) + a
reinforced association graph (edges that strengthen with co-use, decay without).

See docs/library/design/20260709_perspectives-maps-build-plan-the-interpr_5a5e0a.md.  Slice P0 = schema; P1 = reinforcement.
"""
from core.perspectives.schema import (
    Lens, Map, valid_relationship, VALID_DOMAINS,
    BUILTIN_LENSES, BUILTIN_MAPS, lens_key, map_key,
)
from core.perspectives.reinforce import ReinforcedGraph, get_reinforced_graph

__all__ = [
    "Lens", "Map", "valid_relationship", "VALID_DOMAINS",
    "BUILTIN_LENSES", "BUILTIN_MAPS", "lens_key", "map_key",
    "ReinforcedGraph", "get_reinforced_graph",
]
