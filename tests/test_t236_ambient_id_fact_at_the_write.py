"""T236 RED: the corpus knows T227 is taken and says so 220 minutes before I type it.

MEASURED 2026-08-07, and this pin exists because the diagnosis "pay more attention" was wrong.

  identifiers_minted_before_the_registry_speaks_collide fired TWICE -- 04:15 and 14:33 -- and
  BOTH times the triggering action was `task propose --help`, the command where I am already
  doing the right thing. The colliding filename `tests/test_t227_*.py` was written at 18:14, a
  gap of 220 minutes. In the 20 minutes before that write, 7 injections carried 15 lessons and
  not one of them was this one.

The recall corpus indexes lessons by TOPIC, so they fire at the trigger site and go silent at the
application site. That is a ROUTING defect and it has a fix; the attention framing had none.

TWO DESIGN LAWS, both from the same measurement.

FACT, NOT RULE. The 14:33 injection said "MINT THE IDENTIFIER FIRST, THEN WRITE. Any label chosen
before the registry issues it is a guess." True, general, ignorable -- a rule demands compliance
and arrives context-free. What was needed at 18:14 was "T227 is DONE: LEXICON gains its MECHANISM
column." That asks nothing. It closes an information gap, and a fact cannot be a demand.

FIRE ON THE ANOMALY, NOT THE ACTION. There are already 269 injections and ~42k tokens a day
across 364 distinct lessons, and this repo's own prior art says reduce injection volume to
increase trust. So the check must be silent almost always, and its silence must itself be
informative. Precision comes from targeting MINTING rather than MENTIONING:

  * a PATH carries a minted id; prose mentions one. Commit bodies reference done tasks
    constantly and must never trigger this.
  * a path that ALREADY EXISTS is being edited, not minted. Silent.
  * an ACTIVE id in a new path is someone working their claimed task. Silent.
  * only a TERMINAL id (done/abandoned) in a NEW path is the mistake I actually made.

AMBIENT, NEVER A DEMAND. This rides `hookSpecificOutput.additionalContext` and must never reach
`_deny`. The hook is able to block -- that is what makes the restraint a design decision worth
pinning rather than an implementation detail.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _facts(path, exists=False, ledger=None):
    from agent.harness.hooks.claude_pretooluse import id_facts_for_path
    return id_facts_for_path(path, exists=exists, ledger=ledger or _LEDGER)


_LEDGER = {
    "T227": {"status": "done", "title": "LEXICON gains its MECHANISM column"},
    "T099": {"status": "abandoned", "title": "some parked intent"},
    "T240": {"status": "in_progress", "title": "a live claimed task"},
    "T241": {"status": "proposed", "title": "not yet approved"},
}


def test_a_terminal_id_in_a_new_path_states_the_fact():
    """THE PIN. Exactly the 2026-08-07 mistake, caught at the moment it is made."""
    out = _facts("tests/test_t227_diversity_prescription_is_mode_aware.py")
    assert out, "the id was taken and the hook said nothing -- this is the measured failure"
    assert "T227" in out
    assert "done" in out.lower()
    assert "LEXICON" in out, "state WHAT it is; 'taken' alone is not a fact the writer can act on"


def test_it_states_a_fact_and_does_not_issue_a_rule():
    """A rule demands compliance and gets read past. A fact closes a gap and asks nothing."""
    out = _facts("tests/test_t227_thing.py").lower()
    for imperative in ("must ", "should ", "always ", "never ", "remember", "make sure"):
        assert imperative not in out, f"{imperative!r} makes this a demand, not a fact"


def test_an_abandoned_id_also_counts_as_taken():
    """Terminal is terminal: an abandoned id is as spent as a done one."""
    assert _facts("docs/t099_revival.md")


def test_a_free_id_is_silent():
    """Silence is the default and is itself informative."""
    assert _facts("tests/test_t999_brand_new.py") == ""


def test_an_active_id_is_silent():
    """Working a claimed task is the normal case and must never be interrupted."""
    assert _facts("tests/test_t240_live_work.py") == ""
    assert _facts("tests/test_t241_proposed_work.py") == ""


def test_editing_an_existing_file_is_silent():
    """An existing path is being EDITED, not minted. This is the difference between
    minting and mentioning, and it is where the precision comes from."""
    assert _facts("tests/test_t227_already_here.py", exists=True) == ""


def test_a_path_without_an_id_is_silent_and_costs_nothing():
    """The regex gate runs before any ledger read, so the common case is free."""
    assert _facts("core/comm/ask.py") == ""
    assert _facts("") == ""


def test_the_hook_never_denies_on_this_path():
    """AMBIENT, NEVER A DEMAND -- and the hook is fully capable of denying, which is why
    this is pinned rather than assumed."""
    src = (REPO / "agent" / "harness" / "hooks" / "claude_pretooluse.py").read_text(
        encoding="utf-8", errors="replace")
    i = src.index("def id_facts_for_path")
    j = src.index("\ndef ", i + 10)
    assert "_deny" not in src[i:j], "the id fact must never block an action"


def test_it_works_against_the_REAL_ledger():
    """The pin that would have caught the actual defect, added after the pins missed it.

    Every test above injects a fake ledger, so none of them exercised the real `state_view()`
    read -- and that read was wrong: state_view() is keyed by STATUS BUCKET, not
    {"tasks": [...]}. The implementation was silent on the exact case it was built for while
    all nine pins stayed green. Mocking the seam that is wrong is how a pin certifies nothing.

    T001 is used as the fixture because it is the oldest DONE task in the ledger and is not
    going to change status; the test asserts against live state deliberately.
    """
    from agent.harness.hooks.claude_pretooluse import id_facts_for_path

    out = id_facts_for_path("tests/test_t001_would_collide.py")
    assert out, "the real ledger lookup returned nothing for a known-DONE id"
    assert "T001" in out and "done" in out.lower()

    assert id_facts_for_path("tests/test_t999_free.py") == "", \
        "a free id must stay silent against the real ledger too"


def test_it_fails_open_on_a_broken_ledger():
    """A helper that can brick a Write is not a helper."""
    from agent.harness.hooks.claude_pretooluse import id_facts_for_path
    assert id_facts_for_path("tests/test_t227_x.py", ledger="not-a-dict") == ""
    assert id_facts_for_path("tests/test_t227_x.py", ledger={"T227": "malformed"}) == ""


def test_the_id_pattern_survives_the_ledger_reaching_four_digits():
    """Found by a BLIND three-view fan (evidence lens) on 2026-08-07, and independently by me
    while writing the prediction for it.

    The first cut matched exactly three digits, so on the day the ledger issues T1000 the check
    would stop firing -- silently, with every pin still green, because every fixture used a
    three-digit id. A guard that expires on a birthday nobody marks is worse than no guard: it
    is a guard everyone believes in.
    """
    from agent.harness.hooks.claude_pretooluse import id_facts_for_path

    big = {"T1000": {"status": "done", "title": "a task from the future"}}
    assert id_facts_for_path("tests/test_t1000_future.py", exists=False, ledger=big)
    assert "T1000" in id_facts_for_path("tests/test_t1000_future.py", exists=False, ledger=big)


def test_the_hook_survives_a_non_dict_tool_input():
    """Found by the ABSENCE lens of a blind multi-view fan: `or {}` guards None but not a
    truthy non-dict, so a tool whose input is a bare string would raise AttributeError in
    main() -- outside id_facts_for_path's own try -- and crash the hook on every file call.

    Exercised through the real hook process, because the defect lived in the CALLER, which is
    exactly the seam a unit test of the function would have missed (and did).
    """
    import json as _json
    import subprocess as _sp

    payload = _json.dumps({"tool_name": "Write", "session_id": "t236-nondict",
                           "cwd": str(REPO), "tool_input": "a bare string"})
    for hook in ("scripts/hooks/claude_pretooluse.py",
                 "agent/harness/hooks/claude_pretooluse.py"):
        r = _sp.run([sys.executable, hook], input=payload, cwd=REPO,
                    capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"{hook} crashed on a non-dict tool_input: {r.stderr[:300]}"
        assert "AttributeError" not in r.stderr
