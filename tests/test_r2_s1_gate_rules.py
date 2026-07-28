"""R2 slice 1a -- THE RULE TABLE, derived from principles, allergic to fitting. RED first.

The reconciled bar's rules half (kimi's Q1, adopted): three PRINCIPLES about an
action's relationship to knowledge, never eight anecdotes --

  no_item_changes_a_count   the action's output is fully determined by the command
                            (pure counts, byte-maps, --json status renders)
  tool_is_the_retrieval     the action is itself a lookup; recall cannot beat the
                            tool's own answer (grep-for-content, note --get, help)
  work_already_done         the action ships work that is already written (commit
                            of staged/authored content; the deciding happened before)

Sol's Q4 placed the gate AFTER ranking, so a rule sees (query_shape, action text,
ranking result) and returns (rule_name, matched_features) -- the structural facts
for the receipt, never raw command text (secrets ride argv).

THE ANTI-FITTING PINS ARE THE POINT OF THIS FILE:
  A1  the module source contains NO census case numbers -- a principle that cannot
      be stated without a case number is a fit, rejected at the table (kimi Q1).
  A2  case 9 (relevance-judgment NONE-NEEDED) matches NO rule -- it is the floor's
      business; a "shape rule" stretched to catch it has learned the pack.
  A3  the table exposes a stable table_hash for sol's receipt -- a rule name alone
      is mutable semantics; the hash pins which table fired.

Behaviour pins run the REAL pack actions through the rules (pack = tripwire):
  B1  >=5 of the shape-catchable NONE-NEEDED set match some rule.
  B2  ZERO of the intersection-HIT set match any rule.
  B3  ZERO of the should-surface set match any rule.
  B4  a rule match returns matched_features with NO raw command text.
"""

import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import gate_rules as G
from core.recall import pack_replay as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pack_cases():
    with io.open(os.path.join(ROOT, P.PACK_PATH), encoding="utf-8") as f:
        return {c["case"]: c for c in P.parse_pack(f.read())}


# --------------------------------------------------------------- A1 anti-fitting
def test_a1_the_module_names_no_case_numbers():
    src = io.open(os.path.join(ROOT, "core", "recall", "gate_rules.py"),
                  encoding="utf-8").read()
    hits = re.findall(r"\bcase[ _]?(\d+)\b", src, re.I)
    assert not hits, (
        f"FITTING SURFACE: the rule module references census case number(s) {hits}. "
        f"A principle that cannot be stated without a case number is a fit -- kimi's "
        f"Q1 rejection rule, enforced structurally.")


# --------------------------------------------------------------- A2 the floor's case
def test_a2_the_relevance_judgment_case_matches_no_rule():
    c9 = _pack_cases()[9]
    verdict = G.match(query_shape=c9["kind"], action=c9["action"])
    assert verdict is None, (
        f"RULE STRETCHED INTO THE FLOOR'S TERRITORY: the relevance-judgment case "
        f"matched {verdict!r}. The moment a shape rule catches it, the table has "
        f"learned the pack (kimi Q2-b): editing a source file is a real edit, and "
        f"whether its lessons are tangential is the FLOOR's judgment, not a shape's.")


# --------------------------------------------------------------- A3 the receipt hash
def test_a3_the_table_exposes_a_stable_hash():
    h1, h2 = G.table_hash(), G.table_hash()
    assert h1 and h1 == h2 and len(h1) >= 12, (
        "sol's receipt needs rule_table_hash -- a name alone is mutable semantics")


# --------------------------------------------------------------- B1/B2/B3 the bar
def test_b1_shape_catchable_cases_match():
    cases = _pack_cases()
    matched = [n for n in sorted(P.SHAPE_CATCHABLE)
               if G.match(query_shape=cases[n]["kind"], action=cases[n]["action"])]
    assert len(matched) >= 5, (
        f"the bar's clause 1: >=5 of the shape-catchable set must match a principle; "
        f"got {len(matched)}: {matched}. If a principle cannot catch its own shape "
        f"class, the principle is wrong -- fix the PRINCIPLE, never add a case rule.")


def test_b2_intersection_hits_never_match():
    cases = _pack_cases()
    hits = [n for n in sorted(P.INTERSECTION_HIT)
            if G.match(query_shape=cases[n]["kind"], action=cases[n]["action"])]
    assert not hits, (
        f"HARD ZERO VIOLATED AT THE TABLE: intersection-HIT case(s) {hits} match a "
        f"silence rule. Both blind judges said these lessons change the action.")


def test_b3_should_surface_never_matches():
    cases = _pack_cases()
    ss = [n for n in cases
          if n not in P.SHAPE_CATCHABLE and n not in P.INTERSECTION_HIT
          and n not in P.CONTESTED and n not in P.FLOOR_BUSINESS]
    bad = [n for n in ss if G.match(query_shape=cases[n]["kind"], action=cases[n]["action"])]
    assert not bad, (
        f"clause 3 (kimi's strongest attack): the gate may ONLY silence NONE-NEEDED. "
        f"should-surface case(s) {bad} matched a rule -- adding silence to planes the "
        f"census says are already too dark.")


# --------------------------------------------------------------- B4 no raw text
def test_b4_matched_features_carry_no_raw_command():
    cases = _pack_cases()
    for n in sorted(P.SHAPE_CATCHABLE):
        v = G.match(query_shape=cases[n]["kind"], action=cases[n]["action"])
        if not v:
            continue
        feats = str(v.get("matched_features"))
        assert cases[n]["action"][:40] not in feats, (
            f"RAW COMMAND IN THE RECEIPT (case {n}): secrets ride argv; the receipt "
            f"records structural facts, never the text (sol Q4): {feats[:120]}")


# --------------------------------------------------------------- C-pins: sol's s1a NO-GO
def test_c1_a_write_verb_through_a_door_prefix_never_matches():
    """sol's NO-GO: `recall-feedback` matched the door rule via the recall\S* pattern.
    It WRITES (a vote mutates the funnel). The write-verb exclusion must be the
    principle 'any mutating segment kills the match', not an enumerated list that
    rots as verbs are added."""
    v = G.match(query_shape="command",
                action="cd /e/ai-setup && py agent_cli.py recall-feedback claude "
                       "--source learn:experiment:x --vote useful")
    assert v is None, f"a WRITE through the knowledge door matched a silence rule: {v}"


def test_c2_mutation_then_measurement_never_matches():
    """A compound command that MUTATES then counts is an action with effects; the
    count sink at the tail must not silence the mutation at the head."""
    v = G.match(query_shape="command",
                action="cd /e/ai-setup && rm -rf build && ls build 2>/dev/null | wc -l")
    assert v is None, f"mutate-then-measure matched: {v}"


def test_c3_commit_then_count_never_matches():
    v = G.match(query_shape="command",
                action="cd /e/ai-setup && git add x.py && git commit -q -m done && "
                       "git log --oneline | wc -l")
    assert v is None, f"a commit wearing a count suffix matched: {v}"


def test_c4_a_door_read_piped_to_a_writer_never_matches():
    """Reading status is inert; MATERIALIZING it somewhere is an action whose
    destination a lesson can absolutely change."""
    v = G.match(query_shape="command",
                action="py agent_cli.py status | Set-Content -Path state/snapshot.txt")
    assert v is None, f"door-read piped to a writer matched: {v}"


def test_c5_table_hash_covers_every_decision_affecting_structure(monkeypatch):
    """sol: a decision-affecting _PREFIX change left table_hash unchanged -- the
    receipt field failed its one job (a silence stays explainable after edits).
    Everything that can flip a verdict must be digested."""
    import re as _re
    h1 = G.table_hash()
    monkeypatch.setattr(G, "_PREFIX", _re.compile(r"^something-else", _re.I))
    assert G.table_hash() != h1, (
        "changing _PREFIX changes decisions but not the hash -- receipts would "
        "attribute new behaviour to the old table")


# --------------------------------------------------------------- D-pins: the inversion
def test_d1_an_unknown_program_never_matches_even_wearing_a_count_suffix():
    """sol's round-2 NO-GO, the generative pin it asked for: the mutator vocabulary
    is INFINITE, so safety cannot be a denylist. `py destructive_script.py | wc -l`
    matched the count rule -- the sink was known, the program was not, and unknown
    programs mutate. The grammar must recognise EVERY segment as read-only or FIRE.
    This pin uses a program no list could contain."""
    for action in (
        "py destructive_script.py | wc -l",
        "cd /e/ai-setup && frobulate --hard | grep -c done",
        "py -c \"import os; os.remove('victim')\" | wc -l",
        "Clear-Content victim; Get-Content data | Measure-Object",
        "py agent_cli.py status | Tee-Object -FilePath status.txt",
        "git tag release && grep -c TODO README.md",
    ):
        v = G.match(query_shape="command", action=action)
        assert v is None, (
            f"UNKNOWN/MUTATING SEGMENT SILENCED: {action!r} -> {v}. A denylist fails "
            f"toward SILENCING when the unknown mutator wears a known sink; the "
            f"allowlist grammar fails toward FIRING, which is the bar's law.")
