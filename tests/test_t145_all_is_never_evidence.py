"""PRE-REGISTERED ACCEPTANCE (T145) -- `__all__` is a DECLARATION, never a use.

ROUND-3 FINDING, 2026-08-03, and the answer to the question this whole exercise was built to ask:
does hardening a guard CONVERGE, or does every patch open a new seam?

Here it did neither cleanly -- it RELOCATED one. T144 ruled that a string naming a function counts
as proof-of-life only from ANOTHER module, which closed `__all__ = ["dead_fn"]` written beside the
function. Round 3 moved the export list one file up:

    core/comm/bus.py          def dead_via_pkg_init(): ...      # nothing calls it
    core/comm/__init__.py     __all__ = ["dead_via_pkg_init"]   # a DIFFERENT module

and the gate went silent again. `__init__.py` satisfies T144's cross-module test perfectly, and it
is the MOST idiomatic home for `__all__` -- so the patch made the evasion easier to trigger by
accident, not harder. Measured in the arena: LANDED against T144.

THE FIX IS NOT ABOUT LOCATION. Chasing the file would just move it again. An `__all__` entry
DECLARES an export surface; it does not USE anything. The corpus already had the sentence, from the
verb census this morning, about a different manifest entirely:

    "A manifest entry is a claim, not a reference -- it proves someone looked at it once,
     not that anything uses it."

So `__all__` is excluded as evidence wherever it appears. Verified: closes BOTH the same-module and
the package-`__init__` case, at ZERO false-positive cost on the live tree (baseline 116, unchanged,
gate still PASS). This cannot create a false positive by construction -- a function whose only
mention is an export list is, by definition, not called by anyone.

COMPLEMENTARY TO T144, NOT A REPLACEMENT. T144 still earns its keep on self-describing API
catalogues that are not `__all__` -- core/signals/coordinator_api.py:600 holds
`"code": "briefing = api.get_startup_briefing()"`, a docstring-shaped string that immunised seven
functions in that one file.

  E1  `__all__` beside the function is not evidence        (T144's case, kept closed)
  E2  `__all__` in the package __init__ is not evidence    (the relocation, closed)
  E3  a NON-__all__ string in another module still counts  (getattr dispatch must keep working)
  E4  a same-module call still counts                      (the catch_up case, no regression)
  E5  a list of strings that is not __all__ still counts   (the exclusion is narrow)

Run: py -m pytest tests/test_t145_all_is_never_evidence.py -q
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


def test_e1_all_beside_the_function_is_not_evidence(tmp_path):
    lib = _mod(tmp_path, "core/comm/bus.py",
               "def dead_fn():\n    return 1\n\n__all__ = [\"dead_fn\"]\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import bus\nprint(bus)\n")
    assert "dead_fn" in _orphans(tmp_path, [lib], [door, lib])


def test_e2_all_in_the_package_init_is_not_evidence(tmp_path):
    """THE RELOCATION. T144 closed E1 and this reopened it one file up -- in the single most
    idiomatic place a Python package puts an export list."""
    lib = _mod(tmp_path, "core/comm/bus.py", "def dead_via_pkg_init():\n    return 1\n")
    init = _mod(tmp_path, "core/comm/__init__.py",
                "__all__ = [\"dead_via_pkg_init\"]\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import bus\nprint(bus)\n")
    assert "dead_via_pkg_init" in _orphans(tmp_path, [lib], [door, init, lib]), (
        "moving __all__ into the package __init__ restored full immunity, because __init__.py "
        "satisfies the cross-module test")


def test_e3_a_non_all_string_in_another_module_still_counts(tmp_path):
    """getattr dispatch is real wiring. The exclusion must bite __all__, not strings."""
    lib = _mod(tmp_path, "core/comm/verbs.py", "def promote(x):\n    return x\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm import verbs\nfn = getattr(verbs, 'promote')\nfn(1)\n")
    assert "promote" not in _orphans(tmp_path, [lib], [door, lib])


def test_e4_a_same_module_call_still_counts(tmp_path):
    lib = _mod(tmp_path, "core/comm/mailbox.py",
               "def catch_up(ns):\n    return 1\n\n"
               "def consume(ns):\n    return catch_up(ns)\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm.mailbox import consume\nconsume('ns')\n")
    assert "catch_up" not in _orphans(tmp_path, [lib], [door, lib])


def test_e5_a_string_list_that_is_not_all_still_counts(tmp_path):
    """The exclusion is narrow: only the name `__all__`. A genuine dispatch table of strings in
    another module is still evidence, because something reads it."""
    lib = _mod(tmp_path, "core/comm/verbs.py", "def promote(x):\n    return x\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm import verbs\n"
                "HANDLERS = ['promote']\n"
                "for h in HANDLERS:\n    getattr(verbs, h)(1)\n")
    assert "promote" not in _orphans(tmp_path, [lib], [door, lib])
