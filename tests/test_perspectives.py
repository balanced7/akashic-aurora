"""
Perspectives P0 (Lens/Map schema) + P1 (reinforcement) tests, with the acceptance
bars from docs/perspectives-maps-plan.md:
  P0: round-trip + validation against the real vocabulary; built-ins valid.
  P1: bounded (no runaway) + correct decay + deterministic + co-activation.

Isolated: injects a temp FileStore -- never touches canonical.

Run: py -m pytest tests/test_perspectives.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.perspectives.schema import (
    Lens, Map, BUILTIN_LENSES, BUILTIN_MAPS, lens_key, map_key, VALID_DOMAINS,
)
from core.perspectives.reinforce import ReinforcedGraph, MAX_STRENGTH


def _graph(half_life_seconds=30 * 24 * 3600):
    return ReinforcedGraph(FileStore(os.path.join(tempfile.mkdtemp(), "s.json")),
                           half_life_seconds=half_life_seconds)


# ------------------------------------------------------------------ P0 schema
def test_lens_validate_and_roundtrip():
    good = Lens("causal", {"relevance": 0.3, "strength": 0.7}, {"causes": 1.0, "influences": 0.8})
    assert good.validate() == []
    assert Lens.from_dict(good.to_dict()) == good
    bad = Lens("x", {"not_a_factor": 1.0}, {"led_to": 1.0})  # fake factor + fake relation
    probs = bad.validate()
    assert any("factor" in p for p in probs) and any("led_to" in p for p in probs)


def test_map_validate_and_roundtrip():
    m = Map("causal", ["causal"], direction="both")
    assert m.validate() == [] and Map.from_dict(m.to_dict()) == m
    bad = Map("x", ["not_a_domain"], direction="sideways")
    probs = bad.validate()
    assert any("domain" in p for p in probs) and any("direction" in p for p in probs)


def test_builtins_are_valid():
    for lens in BUILTIN_LENSES.values():
        assert lens.validate() == [], f"built-in lens {lens.name} invalid"
    for mp in BUILTIN_MAPS.values():
        assert mp.validate() == [], f"built-in map {mp.name} invalid"
    assert lens_key("causal") == "persp:lens:causal" and map_key("causal") == "persp:map:causal"
    assert "causal" in VALID_DOMAINS and "temporal" in VALID_DOMAINS


# ------------------------------------------------------------------ P1 reinforcement
T0 = "2026-01-01T00:00:00"
T30 = "2026-01-31T00:00:00"   # +30 days (= one half-life)
T60 = "2026-03-02T00:00:00"   # +60 days (= two half-lives)


def test_bounded_never_exceeds_max():
    g = _graph()
    s = 0.0
    for _ in range(100):                 # hammer the same edge at the same instant
        s = g.reinforce("a", "b", now=T0)
        assert s <= MAX_STRENGTH + 1e-9, "strength must never exceed MAX (no runaway)"
    assert s > 0.99, "repeated reinforcement should approach MAX"


def test_saturating_monotonic():
    g = _graph()
    prev = 0.0
    for _ in range(5):
        s = g.reinforce("a", "b", now=T0)
        assert s > prev, "each reinforcement increases strength (until saturation)"
        prev = s


def test_half_life_decay():
    g = _graph()
    s0 = g.reinforce("a", "b", now=T0)        # one bump
    assert abs(g.strength("a", "b", now=T30) - s0 * 0.5) < 1e-3, "one half-life -> halved"
    assert abs(g.strength("a", "b", now=T60) - s0 * 0.25) < 1e-3, "two half-lives -> quartered"


def test_deterministic():
    a, b = _graph(), _graph()
    for _ in range(3):
        a.reinforce("x", "y", now=T0)
        b.reinforce("x", "y", now=T0)
    assert a.strength("x", "y", now=T30) == b.strength("x", "y", now=T30)


def test_cooccurrence_and_neighbors():
    g = _graph()
    n = g.reinforce_cooccurrence(["a", "b", "c"], now=T0)   # 3 pairs
    assert n == 3
    assert g.strength("a", "b", now=T0) > 0 and g.strength("b", "c", now=T0) > 0
    # a fresher association outranks a staler one of equal initial strength
    g.reinforce("a", "d", now=T30)                          # d bumped 30d after b/c
    nbrs = dict(g.neighbors("a", now=T30))
    assert nbrs["d"] > nbrs["b"], "recently-reinforced neighbour ranks above a decayed one"


if __name__ == "__main__":
    for fn in [test_lens_validate_and_roundtrip, test_map_validate_and_roundtrip,
               test_builtins_are_valid, test_bounded_never_exceeds_max,
               test_saturating_monotonic, test_half_life_decay, test_deterministic,
               test_cooccurrence_and_neighbors]:
        fn()
    print("ALL PERSPECTIVES TESTS PASSED")
