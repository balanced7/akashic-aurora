"""PRE-REGISTERED ACCEPTANCE (T134) -- the Built != Wired gate, one level down.

MEASURED 2026-08-03. check_wiring.py PASSES today, and passed every day while
`core/comm/mailbox.py::declare_intent` had zero production callers. The gate walks the import
graph over MODULES; mailbox.py is imported by the CLI door, so the module read WIRED while the
capability inside it was dead. Latent capability accumulated behind a green gate.

THE HISTORICAL CASE IS EXACT, and is this file's reason for existing:

    95e0c55  "T095-M1 GREEN: ... open/seen + declare_intent (D4). 8/8 pins ..."   <- built + TESTED
    b945813  "T095-M1 wired + falsifiers: mailbox --open/--state/--intent on the
              CLI+MCP door (BUILT WAS NOT WIRED -- no door exposed the M1 verbs)"  <- wired

A human diagnosed "built was not wired" by hand and wrote it in a commit message. Between those
two commits the capability existed, passed its pins, and ran nowhere. This extension makes that
diagnosis automatic: a public function in a WIRED core/ module that no production entry point
ever names is dead capability, and tests are not production.

WHY THE SHAPE IS FAIL-OPEN, deliberately. The sibling gate's own comments record the lesson twice
(control_channel.py, door_probe.py): a false positive is expensive TWICE -- the only remedy the
guard offers is an EXCEPTIONS entry, so each one pushes live code onto a permanent exemption list,
and a guard that cries wolf gets fed exceptions until it guards nothing. So "referenced" here means
MENTIONED BY NAME anywhere on a production path -- call, attribute, bare name, import alias, kwarg,
or an exact-match string constant (getattr and verb-table dispatch). Weak evidence still counts as
evidence. The gate finds capability with ZERO mentions, which is the class it can be certain about.

THE FIRST DRAFT OF THIS ANALYSIS WAS WRONG, and P3 exists because of it. Excluding "the function's
own module" to suppress recursion reported `load_learnings_for_boot` as never called -- it is
called at core/context/aggregator.py:104, from inside aggregator's own public function. Measured
before the fix: 277 orphans. After: 44. P2/P3/P4 pin that boundary so it cannot regress.

  P1  a public function referenced ONLY by tests is UNWIRED          (the declare_intent case)
  P2  a call from another production module is WIRED
  P3  a call from elsewhere in its OWN module is WIRED               (the false-positive class)
  P4  recursion is not wiring -- a self-reference alone is UNWIRED
  P5  an exact-match string constant is WIRED                        (getattr / verb dispatch)
  P6  _private and dunder names are not candidates
  P7  a module already on the MODULE backlog does not flood this gate
  P8  an entry that becomes wired is reported STALE, not silently kept
  P9  a prose mention in a docstring is NOT wiring

Run: py -m pytest tests/test_t134_wiring_function_level.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402


def _mod(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return name.replace(os.sep, "/")


def _orphans(tmp_path, cand, prod):
    """-> {name} reported unwired, analysed against tmp_path as the repo root."""
    got = check_wiring.unwired_functions(cand, prod, root=str(tmp_path))
    return {name for _mod_, name, _line in got}


def test_p1_tested_but_never_called_is_unwired(tmp_path):
    """The declare_intent case: built, pinned, and reachable from nothing that runs."""
    lib = _mod(tmp_path, "core/comm/mailbox.py",
               "def declare_intent(ns, agent, sha):\n    return {'ok': True}\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import mailbox\nprint('door')\n")
    # a pin exercises it, and a pin is not a production call path
    _mod(tmp_path, "tests/test_mailbox.py",
         "from core.comm.mailbox import declare_intent\ndeclare_intent('ns', 'a', 'sha')\n")
    assert "declare_intent" in _orphans(tmp_path, [lib], [door, lib]), (
        "a capability with pins and no caller is exactly what shipped for months behind a "
        "green gate -- tests are not a production call path")


def test_p2_called_from_another_production_module_is_wired(tmp_path):
    lib = _mod(tmp_path, "core/comm/mailbox.py", "def declare_intent(ns):\n    return 1\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm.mailbox import declare_intent\ndeclare_intent('ns')\n")
    assert "declare_intent" not in _orphans(tmp_path, [lib], [door, lib])


def test_p3_called_from_elsewhere_in_its_own_module_is_wired(tmp_path):
    """THE REGRESSION THIS FILE EXISTS TO PREVENT.

    `catch_up` is called at mailbox.py:450 from inside `consume`, which lives in the same file.
    The first draft suppressed every reference made inside any public def of the defining module
    and so called it dead. Same shape as load_learnings_for_boot <- aggregator.py:104.
    """
    lib = _mod(tmp_path, "core/comm/mailbox.py",
               "def catch_up(ns):\n"
               "    return 1\n"
               "\n"
               "def consume(ns):\n"
               "    cu = catch_up(ns)\n"
               "    return cu\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm.mailbox import consume\nconsume('ns')\n")
    assert "catch_up" not in _orphans(tmp_path, [lib], [door, lib]), (
        "a helper called by its own module's public API is wired; calling it dead is the "
        "expensive direction -- the only remedy this gate offers is a permanent exemption")


def test_p4_recursion_alone_is_not_wiring(tmp_path):
    lib = _mod(tmp_path, "core/util/walk.py",
               "def descend(n):\n"
               "    if n <= 0:\n"
               "        return 0\n"
               "    return descend(n - 1)\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.util import walk\nprint(walk)\n")
    assert "descend" in _orphans(tmp_path, [lib], [door, lib]), (
        "a function that only ever calls itself runs nowhere")


def test_p5_string_constant_dispatch_is_wiring(tmp_path):
    """getattr / verb tables are how the doors dispatch; missing them would flood the gate."""
    lib = _mod(tmp_path, "core/comm/verbs.py", "def promote(x):\n    return x\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm import verbs\nfn = getattr(verbs, 'promote')\nfn(1)\n")
    assert "promote" not in _orphans(tmp_path, [lib], [door, lib])


def test_p6_private_and_dunder_are_not_candidates(tmp_path):
    lib = _mod(tmp_path, "core/comm/thing.py",
               "class Thing:\n"
               "    def __init__(self):\n"
               "        self.x = 1\n"
               "\n"
               "def _helper():\n"
               "    return 2\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import thing\nprint(thing)\n")
    got = _orphans(tmp_path, [lib], [door, lib])
    assert "__init__" not in got and "_helper" not in got


def test_p7_module_backlog_is_not_double_reported(tmp_path):
    """A module already frozen as built-ahead must not also spend the function gate's budget.
    Reporting every function inside a known-unwired module is noise, and noise is what turns a
    guard into a thing people silence."""
    lib = _mod(tmp_path, "core/recall/gate_rules.py", "def evaluate(x):\n    return x\n")
    door = _mod(tmp_path, "agent_cli.py", "print('door')\n")
    assert _orphans(tmp_path, [], [door]) == set()
    assert "evaluate" in _orphans(tmp_path, [lib], [door, lib]), (
        "sanity: the exclusion must come from the CALLER passing a filtered candidate list, "
        "not from this function silently knowing about EXCEPTIONS")


def test_p8_a_baseline_entry_that_became_wired_is_reported_stale(tmp_path):
    """The module gate is currently flagging two of its OWN stale entries (runner_lib.py,
    session_recovery.py). That self-correction is the property worth copying: a backlog that
    can only grow is how an exemption list stops being a backlog."""
    lib = _mod(tmp_path, "core/comm/mailbox.py", "def declare_intent(ns):\n    return 1\n")
    door = _mod(tmp_path, "agent_cli.py",
                "from core.comm.mailbox import declare_intent\ndeclare_intent('ns')\n")
    stale = check_wiring.stale_function_baseline(
        ["core/comm/mailbox.py::declare_intent"], [lib], [door, lib], root=str(tmp_path))
    assert "core/comm/mailbox.py::declare_intent" in stale


def test_p9_a_docstring_mention_is_not_wiring(tmp_path):
    """self_restart.py:11 mentions `should_restart(...)` in prose. Prose is not a call path, and
    a guard evadable by writing the name in a comment guards nothing."""
    lib = _mod(tmp_path, "core/comm/self_restart.py",
               '"""Usage:\n\n    reason = should_restart(stamped_sha=..., head_sha=...)\n"""\n'
               "def should_restart(stamped_sha):\n    return False\n")
    door = _mod(tmp_path, "agent_cli.py", "from core.comm import self_restart\nprint(self_restart)\n")
    assert "should_restart" in _orphans(tmp_path, [lib], [door, lib])
