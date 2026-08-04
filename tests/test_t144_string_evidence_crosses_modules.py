"""PRE-REGISTERED ACCEPTANCE (T144) -- a STRING naming a function is evidence only from ELSEWHERE.

MEASURED 2026-08-03 by probing the freshly-patched gate in an isolated worktree arena, to answer
one question: does hardening a guard CONVERGE, or does every patch open a new seam?

Four accidental-evasion classes were run against the T143-patched gate. Three landed:

    __all__ = ["dead_but_exported"]      LANDED -- the export list immunises its own exports
    def timeout(): ...                   LANDED -- `timeout=` is a kwarg everywhere (name collision)
    def _h(x: "dead_annotated" = None)   LANDED -- a string annotation counts as a reference
    a doctest naming the function        CAUGHT -- prose is still not evidence

THE MECHANISM behind the first and third. `unwired_functions` excluded references made inside the
function's OWN BODY (lines lo..hi). `__all__` sits at module level, OUTSIDE that range, so a string
constant naming a function counted as proof the function was alive. Every module carrying an
`__all__` was therefore immunising exactly the functions it exported.

THE FIX IS NARROW, and the narrowness is the point: STRING evidence must come from a DIFFERENT
module. Name, attribute, alias and keyword evidence still count same-module, because a real call
from a sibling function is real wiring -- that is the `catch_up` case T134's P3 pins. But a string
is how a CALLER dispatches (`getattr(mod, "promote")`), and a caller lives elsewhere. A module
naming itself in a string is describing itself, not using itself.

WHAT THE ARENA MEASURED, and why this patch was worth landing. It closes two evasion classes AND
surfaces 8 MORE genuinely dead functions, at ZERO false-positive cost. All eight were then verified
by hand to have zero external production references:

    core/foundation/store.py::setex
    core/signals/coordinator_api.py:: get_bootstrap_info, get_context_summary,
        get_startup_briefing, get_startup_context, get_startup_decisions,
        get_startup_learnings, request_handoff

coordinator_api.py carries a SELF-DESCRIBING API CATALOGUE -- strings naming its own functions, e.g.
line 600 `"code": "briefing = api.get_startup_briefing()"` -- and that catalogue was immunising every
function it documented. It is the same pathology the verb census named this morning from a different
direction: **a manifest entry is a claim, not a reference. It proves someone looked at it once, not
that anything uses it.**

  S1  `__all__` in the defining module does NOT prove a function is alive
  S2  a string in ANOTHER module DOES                     (getattr dispatch must keep working)
  S3  a same-module CALL still counts                     (the catch_up case must not regress)
  S4  a same-module string annotation does not
  S5  recursion is still not wiring                       (no regression)

Run: py -m pytest tests/test_t144_string_evidence_crosses_modules.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402


def _mod(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return rel.replace(os.sep, "/")


def _orphans(tmp_path, cand, prod):
    return {n for _m, n, _l in
            check_wiring.unwired_functions(cand, prod, root=str(tmp_path))}


def test_s1_all_does_not_prove_a_function_is_alive(tmp_path):
    lib = _mod(tmp_path, "core/comm/bus.py",
               "def dead_but_exported():\n    return 1\n\n"
               '__all__ = ["dead_but_exported"]\n')
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import bus\nprint(bus)\n")
    assert "dead_but_exported" in _orphans(tmp_path, [lib], [door, lib]), (
        "an export list immunised its own exports -- every module with __all__ was a blind spot")


def test_s2_a_string_in_another_module_still_counts(tmp_path):
    """getattr dispatch is real wiring and must keep working; this is the whole reason string
    evidence exists at all."""
    lib = _mod(tmp_path, "core/comm/verbs.py", "def promote(x):\n    return x\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm import verbs\nfn = getattr(verbs, 'promote')\nfn(1)\n")
    assert "promote" not in _orphans(tmp_path, [lib], [door, lib])


def test_s3_a_same_module_call_still_counts(tmp_path):
    """T134's P3, restated: a helper called by its own module's public API is WIRED. The fix must
    narrow STRING evidence only -- narrowing name evidence would resurrect the expensive
    false-positive class."""
    lib = _mod(tmp_path, "core/comm/mailbox.py",
               "def catch_up(ns):\n    return 1\n\n"
               "def consume(ns):\n    return catch_up(ns)\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm.mailbox import consume\nconsume('ns')\n")
    assert "catch_up" not in _orphans(tmp_path, [lib], [door, lib])


def test_s4_a_same_module_string_annotation_does_not_count(tmp_path):
    lib = _mod(tmp_path, "core/comm/bus.py",
               "def dead_annotated():\n    return 3\n\n"
               'def _unused(x: "dead_annotated" = None):\n    return x\n')
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import bus\nprint(bus)\n")
    assert "dead_annotated" in _orphans(tmp_path, [lib], [door, lib])


def test_s5_recursion_is_still_not_wiring(tmp_path):
    lib = _mod(tmp_path, "core/util/walk.py",
               "def descend(n):\n    return 0 if n <= 0 else descend(n - 1)\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.util import walk\nprint(walk)\n")
    assert "descend" in _orphans(tmp_path, [lib], [door, lib])
