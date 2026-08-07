"""
T213 -- compare: the set difference, generalized. RED first.

Daniil, 2026-08-07: "at work I find a lot of value by seeing what one system has and the
other doesn't, cross matching account numbers, ip's, design documents, logs, timestamps."

HE IDENTIFIED THE SHAPE THAT IS ALREADY OUR BEST GUARD FAMILY. Four of the instruments we
trust most are the same operation, each hand-built as a one-off:

    check_door_parity      CLI verbs   MINUS  MCP verbs  MINUS  ToolBox verbs
    check_wiring           tracked files MINUS reachable files
    suite_baseline.delta   baseline failures MINUS current failures
    T122                   declared kinds MINUS kinds actually sent

A lens only SHOWS you something. A set difference FINDS it. This is that operation with a
name, so the fifth one costs a line instead of a module.

A SET MUST DECLARE WHAT ITS ELEMENTS ARE. Comparing verb names against file paths produces
a large, confident, meaningless difference. So every KeySet carries a key_type and compare
REFUSES a mismatch rather than coercing -- "names must not lie" (Principle 5) applied to
sets rather than to identifiers.

COVERAGE IS THE WHOLE BALLGAME, and this is the one that has already bitten us. A MINUS B
is only as true as the coverage of BOTH sides: where B was partially collected, every
uncollected element of B appears as a finding in A. I shipped exactly that bug in T208 --
a three-file test run reported ten baseline failures as "fixed" because they had merely
not been run, and "fixed" invites a re-record that would have deleted them. So a
difference computed against an incomplete side is UNRELIABLE, and says so.

Run: py -m pytest tests/test_t213_compare.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import compare as CMP  # noqa: E402


def _ks(name, keys, key_type="verb", complete=True, failed=None):
    return CMP.KeySet(name=name, key_type=key_type, keys=set(keys),
                      complete=complete, failed=failed or {})


# --------------------------------------------------------------------------------------
# The operation itself.
# --------------------------------------------------------------------------------------

def test_both_directions_are_reported_separately():
    """A-minus-B and B-minus-A are DIFFERENT findings. 'in the CLI but not MCP' is debt;
    'in MCP but not the CLI' is a rogue door. Collapsing them loses the diagnosis."""
    r = CMP.diff(_ks("cli", ["a", "b", "c"]), _ks("mcp", ["b", "c", "d"]))
    assert r["only_a"] == ["a"]
    assert r["only_b"] == ["d"]
    assert r["both"] == ["b", "c"]


def test_a_type_mismatch_is_refused_not_coerced():
    """THE PRINCIPLE-5 PIN, for sets. Comparing verb names to file paths yields a large,
    confident, meaningless difference -- which is worse than an error, because it looks
    like a finding."""
    r = CMP.diff(_ks("verbs", ["ask"], key_type="verb"),
                 _ks("files", ["core/x.py"], key_type="path"))
    assert r["ok"] is False
    assert "verb" in r["why"] and "path" in r["why"]
    assert r["only_a"] == [] and r["only_b"] == []


def test_an_incomplete_side_makes_the_difference_unreliable():
    """THE T208 BUG, generalized. A three-file test run made ten baseline failures look
    'fixed' because they had merely not been run. Every uncollected element of B shows
    up as a finding in A."""
    r = CMP.diff(_ks("baseline", ["t1", "t2", "t3"], key_type="node"),
                 _ks("current", ["t1"], key_type="node", complete=False))
    assert r["reliable"] is False
    assert "current" in r["why"]
    # It still reports -- refusing to compute would be its own kind of blindness.
    assert r["only_a"] == ["t2", "t3"]


def test_a_complete_pair_is_reliable():
    r = CMP.diff(_ks("a", ["x"]), _ks("b", ["x", "y"]))
    assert r["reliable"] is True and r["ok"] is True


def test_a_failed_source_taints_the_side_it_belongs_to():
    """A KeySet built from a source that errored is not complete, whatever it collected."""
    ks = _ks("mcp", ["a"], failed={"parse": "SyntaxError"})
    assert ks.complete is False
    r = CMP.diff(_ks("cli", ["a", "b"]), ks)
    assert r["reliable"] is False


def test_identical_sets_are_not_a_finding():
    r = CMP.diff(_ks("a", ["x", "y"]), _ks("b", ["y", "x"]))
    assert r["only_a"] == [] and r["only_b"] == [] and r["identical"] is True


def test_two_empty_sets_are_not_a_finding_either():
    """0 minus 0 = 0 is arithmetically true and diagnostically empty. Reporting it as
    'no debt' when both collectors returned nothing is the confident-zero lie."""
    r = CMP.diff(_ks("a", []), _ks("b", []))
    assert r["identical"] is True
    assert r["reliable"] is False, "two empty sides prove nothing about the world"


def test_the_same_entity_spelled_differently_is_not_a_finding():
    """CAUGHT ON THE FIRST LIVE RUN. The CLI hyphenates (`bifrost-send`), the MCP door
    underscores (`bifrost_send`). One verb, two spellings, and a raw difference reported
    each as missing from the other side -- twice.

    This is the classic cross-matching problem Daniil named from his own work: the same
    entity formatted differently per system. Without a per-type normalizer, a difference
    between two systems measures their FORMATTING as much as their contents."""
    r = CMP.diff(_ks("cli", ["bifrost-send", "knowledge-map"]),
                 _ks("mcp", ["bifrost_send", "knowledge_map"]))
    assert r["only_a"] == [] and r["only_b"] == []
    assert r["identical"] is True


def test_a_finding_is_reported_in_its_own_system_s_spelling():
    """Normalizing for the COMPARISON must not rewrite the answer: a verb missing from
    MCP has to be named the way the CLI spells it, or you cannot go look for it."""
    r = CMP.diff(_ks("cli", ["bifrost-drain"]), _ks("mcp", []))
    assert r["only_a"] == ["bifrost-drain"]


def test_a_type_with_no_normalizer_compares_literally():
    """An unnormalized type is a DECISION the type makes, not an omission -- and it must
    behave predictably rather than half-matching."""
    r = CMP.diff(_ks("a", ["Thing-One"], key_type="lesson"),
                 _ks("b", ["thing_one"], key_type="lesson"))
    assert r["only_a"] == ["Thing-One"] and r["only_b"] == ["thing_one"]


def test_results_carry_both_sides_provenance():
    r = CMP.diff(_ks("cli", ["a"]), _ks("mcp", ["b"]))
    assert r["a"]["name"] == "cli" and r["b"]["name"] == "mcp"
    assert r["a"]["n"] == 1 and r["b"]["n"] == 1
    assert r["key_type"] == "verb"


# --------------------------------------------------------------------------------------
# The registry: the four hand-rolled guards, now expressible.
# --------------------------------------------------------------------------------------

def test_the_known_domains_declare_their_key_types():
    """A domain whose key type is undeclared cannot be safely compared with anything."""
    for name, (fn, kt) in CMP.DOMAINS.items():
        assert kt, f"{name} has no declared key_type"
        assert callable(fn)


def test_verb_domains_share_a_key_type_so_parity_is_expressible():
    assert CMP.DOMAINS["verbs:cli"][1] == CMP.DOMAINS["verbs:mcp"][1]


def test_file_domains_share_a_key_type():
    assert CMP.DOMAINS["files:tracked"][1] == CMP.DOMAINS["files:touched"][1]


def test_select_returns_a_keyset_and_never_raises(monkeypatch):
    def boom(**kw):
        raise RuntimeError("source down")
    monkeypatch.setitem(CMP.DOMAINS, "broken", (boom, "verb"))
    ks = CMP.select("broken")
    assert ks.complete is False and ks.keys == set() and ks.failed


def test_an_unknown_domain_is_named_not_silently_empty():
    ks = CMP.select("no-such-domain")
    assert ks.complete is False and ks.failed
