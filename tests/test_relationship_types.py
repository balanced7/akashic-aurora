"""Invariant guard for the relationship-type vocabulary (core/foundation/relationship_types.py).

P0 test hardening (arch-triage-2026-07-07): this 66-type vocabulary is the graph-edge language the
whole knowledge/recall stack rides on, yet had ZERO tests. The load-bearing risk is SILENT edge
corruption -- a broken inverse flips edge direction, a duplicate short_name collapses two edge kinds.
These tests pin those invariants (they caught a real dangling-inverse typo, `derives_from`->`derives_to`,
on first run). Synthesized from independent claude + DeepSeek test plans (2026-07-07).
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.relationship_types import (
    RelationshipType, RelationshipTypeDefinition, RELATIONSHIP_TYPES,
    get_relationship_by_name, get_relationships_by_domain, list_all_domains,
)

_DEFS = [r.value for r in RelationshipType]


# --- the load-bearing invariants: edge-corruption guards --------------------------------------------

def test_no_duplicate_short_names():
    """Two definitions sharing a short_name collapse into one in RELATIONSHIP_TYPES -> a lost edge kind."""
    dups = [name for name, c in Counter(d.short_name for d in _DEFS).items() if c > 1]
    assert not dups, f"duplicate short_names corrupt the edge vocabulary: {dups}"


def test_no_duplicate_formal_names():
    dups = [name for name, c in Counter(d.formal_name for d in _DEFS).items() if c > 1]
    # 'Custom' / 'RDF' formal_names are shared by design; only flag OBO/BFO/RO-style formal ids as unique
    formal_dups = [n for n in dups if ":" in n]
    assert not formal_dups, f"duplicate formal ontology ids: {formal_dups}"


def test_every_inverse_resolves():
    """Every declared inverse must name a real relationship (no dangling inverse pointer)."""
    dangling = [d.short_name for d in _DEFS if get_relationship_by_name(d.inverse) is None]
    assert not dangling, f"inverses point at non-existent relationships: {dangling}"


def test_every_inverse_is_bidirectional():
    """THE critical graph invariant: A.inverse == B  ==>  B.inverse == A. A one-way inverse silently
    flips edge direction on every traversal/recall that uses it."""
    broken = []
    for d in _DEFS:
        inv = get_relationship_by_name(d.inverse)
        if inv is None or inv.inverse != d.short_name:
            broken.append((d.short_name, d.inverse, inv.inverse if inv else None))
    assert not broken, f"non-bidirectional inverse pairs (short, its_inverse, inverse's_inverse): {broken}"


def test_all_required_fields_populated():
    for d in _DEFS:
        for f in ("formal_name", "short_name", "inverse", "description", "domain"):
            assert getattr(d, f), f"{d.short_name}: empty {f}"
        assert isinstance(d.examples, list), f"{d.short_name}: examples must be a list"


def test_short_names_are_edge_safe_slugs():
    """short_names are used as edge keys -> lowercase snake, no spaces/uppercase."""
    bad = [d.short_name for d in _DEFS if d.short_name != d.short_name.lower().strip()
           or " " in d.short_name]
    assert not bad, f"short_names must be lowercase, space-free edge keys: {bad}"


# --- lookup helpers ---------------------------------------------------------------------------------

def test_lookup_by_short_formal_and_enum_name():
    d = RelationshipType.PART_OF.value
    assert get_relationship_by_name("part_of") is d
    assert get_relationship_by_name("PART_OF") is d                 # enum member name
    assert get_relationship_by_name(d.formal_name) is d            # formal name


def test_lookup_is_case_and_space_insensitive():
    assert get_relationship_by_name("Part Of") is RelationshipType.PART_OF.value
    assert get_relationship_by_name("  has_part  ".strip()) is RelationshipType.HAS_PART.value


def test_missing_name_returns_none():
    assert get_relationship_by_name("definitely_not_a_relationship") is None


def test_get_relationships_by_domain_filters_and_sorts():
    domains = list_all_domains()
    assert domains and domains == sorted(set(domains))            # unique + sorted
    dom = domains[0]
    rows = get_relationships_by_domain(dom)
    assert rows, f"domain {dom} should have members"
    assert all(rel_def.domain.lower() == dom.lower() for _, rel_def in rows)
    assert [rd.short_name for _, rd in rows] == sorted(rd.short_name for _, rd in rows)


def test_unknown_domain_is_empty():
    assert get_relationships_by_domain("no_such_domain") == []


def test_backwards_compat_dict_covers_every_member():
    assert len(RELATIONSHIP_TYPES) == len(_DEFS)                  # relies on unique short_names
    for d in _DEFS:
        assert RELATIONSHIP_TYPES[d.short_name] is d
