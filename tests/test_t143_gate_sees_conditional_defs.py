"""PRE-REGISTERED ACCEPTANCE (T143) -- a public def hidden in a module-level `if` is still a def.

RED-TEAM FINDING, confirmed by running it. In a five-seat DeepSeek round on 2026-08-03, the
adversarial seat (deepseek-red, read-only by grant) was given the function-level gate's rules and
asked to defeat them. Its first attack landed on the first try.

    _AKASHIC_GUARD_DEAD = False
    if _AKASHIC_GUARD_DEAD:
        def dead_handler_v1():
            return 99

Appended verbatim to core/comm/bus.py -- a wired module -- and `check_wiring.py` printed:

    PASS: every core/ module is wired to a production path (17 known-standalone exception(s));
          no NEW unwired public function (108 on the frozen backlog)

A genuinely dead public function, in a wired module, and the gate said clean.

THE MECHANISM, which the attacker named correctly before I ran it: `public_defs` iterates
`tree.body` and type-checks each node with `isinstance(node, (FunctionDef, AsyncFunctionDef))` or
`ClassDef`. A def wrapped in ANY module-level statement -- `if`, `try`, `with`, `for`, `while` --
sits inside an `If`/`Try`/`With` node, which is neither, so the walk steps straight over it. The
function is invisible in BOTH directions: never reported dead, never counted as anything.

WHY THIS IS NOT AN EXOTIC TRICK. The attacker's own framing was "the best attack is one an honest
tired engineer would produce on a Friday", and this is that. `if TYPE_CHECKING:`, `try: import fast
except ImportError:` with a pure-python fallback def, and `if os.environ.get("ENABLE_X"):` are all
ordinary Python that this repo already contains. Nobody has to be malicious for the hole to open --
the gate simply stops seeing a whole shape of code.

THE FIX MUST NOT REACH TOO FAR. Nested defs (a closure inside a function) are excluded BY DESIGN --
they are private by construction and reporting them would flood the gate. So the walk descends
through module-level STATEMENT CONTAINERS only, and stops at the first function boundary. P4 pins
exactly that line.

  P1  a def inside a module-level `if` is a candidate       (the confirmed attack)
  P2  `try`/`except` and `with` wrappers too                (same shape, same blindness)
  P3  a def inside a class inside an `if` is a candidate
  P4  a NESTED def is still NOT a candidate                 (the fix must not overreach)
  P5  the gate still finds the plain top-level case         (no regression)

Run: py -m pytest tests/test_t143_gate_sees_conditional_defs.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402


def _names(tmp_path, body):
    p = tmp_path / "core" / "comm"
    p.mkdir(parents=True, exist_ok=True)
    (p / "probe.py").write_text(body, encoding="utf-8")
    return {n for n, _lo, _hi, _m in
            check_wiring.public_defs("core/comm/probe.py", root=str(tmp_path))}


def test_p1_def_inside_a_module_level_if_is_a_candidate(tmp_path):
    got = _names(tmp_path,
                 "_FLAG = False\n"
                 "if _FLAG:\n"
                 "    def dead_handler_v1():\n"
                 "        return 99\n")
    assert "dead_handler_v1" in got, (
        "the red team's A1: a dead public function hid inside a module-level `if` and the gate "
        "reported the whole tree clean")


def test_p2_try_and_with_wrappers_too(tmp_path):
    got = _names(tmp_path,
                 "try:\n"
                 "    def from_try():\n"
                 "        return 1\n"
                 "except ImportError:\n"
                 "    def from_except():\n"
                 "        return 2\n"
                 "\n"
                 "import contextlib\n"
                 "with contextlib.suppress(Exception):\n"
                 "    def from_with():\n"
                 "        return 3\n")
    assert {"from_try", "from_except", "from_with"} <= got


def test_p3_class_inside_a_conditional(tmp_path):
    got = _names(tmp_path,
                 "if True:\n"
                 "    class Thing:\n"
                 "        def method_in_hidden_class(self):\n"
                 "            return 1\n")
    assert "method_in_hidden_class" in got


def test_p4_a_nested_def_is_still_not_a_candidate(tmp_path):
    """The fix must not overreach. A closure is private by construction; reporting closures would
    flood the gate, and a flooded gate gets silenced -- the failure this file's sibling records
    twice."""
    got = _names(tmp_path,
                 "def outer():\n"
                 "    def inner_helper():\n"
                 "        return 1\n"
                 "    return inner_helper()\n")
    assert "outer" in got
    assert "inner_helper" not in got


def test_p5_the_plain_case_still_works(tmp_path):
    got = _names(tmp_path,
                 "def plain():\n"
                 "    return 1\n"
                 "\n"
                 "def _private():\n"
                 "    return 2\n"
                 "\n"
                 "class C:\n"
                 "    def meth(self):\n"
                 "        return 3\n")
    assert "plain" in got and "meth" in got
    assert "_private" not in got
