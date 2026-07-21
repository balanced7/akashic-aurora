"""
T099 · V0.1 — kata: the tool that tells you when your tools are real (kimi's hunt B4).

Law: kata runs every step of a GUESS-tier alias against the DOOR'S OWN GRAMMAR (argparse
parse-only — nothing executes). All steps parse -> the entry levels up GUESS->VERIFIED with
tested_against=kata-<stamp> (via supersession mint, never edit-in-place). Any step failing
grammar -> kata REFUSES the upgrade and names the bad step. Honesty made climbable.

Pre-registered RED before cmd_kata/_kata_check exist.
Run: py -m pytest tests/test_t099_v01_kata.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_kata_levels_up_parseable_alias(tmp_path):
    import agent_cli
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt("t-kata", root=str(tmp_path))          # real door grammar (default known_verbs)
    tb.mint("peek", [["discover"]])
    assert tb.get("peek")["evidence"] == "GUESS"
    ok, results = agent_cli._kata_check(tb.resolve("peek"))
    assert ok and results[0][0] is True
    e = agent_cli._kata_apply(tb, "peek", results)
    assert e["evidence"] == "VERIFIED" and str(e["tested_against"]).startswith("kata-")
    assert e["version"] == 2, "level-up rides supersession, never edit-in-place"


def test_kata_refuses_bad_grammar_and_names_the_step(tmp_path):
    import agent_cli
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt("t-kata", root=str(tmp_path))
    tb.mint("broken", [["discover"], ["bifrost-skip-to-now"]])   # skip-to-now REQUIRES agent + --by + --reason
    ok, results = agent_cli._kata_check(tb.resolve("broken"))
    assert not ok, "a step failing the door's grammar must fail the kata"
    assert results[0][0] is True and results[1][0] is False, "the failing step is NAMED"
    assert tb.get("broken")["evidence"] == "GUESS", "no upgrade on a failed kata"
