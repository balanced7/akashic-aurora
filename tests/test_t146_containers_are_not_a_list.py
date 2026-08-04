"""PRE-REGISTERED ACCEPTANCE (T146) -- stop enumerating containers; descend structurally.

ROUND-4 FINDING, 2026-08-03, found by deepseek-red and confirmed 3/3 in the arena. The T143 fix
descended module-level statement containers via a hand-written tuple:

    _CONTAINERS = (ast.If, ast.Try, ast.With, ast.AsyncWith, ast.For, ast.AsyncFor, ast.While)

That list drifted, exactly the way lists do. Three shapes walked straight through it:

    match _MODE:            -> ast.Match      (Python 3.10)   LANDED
        case "fanout":
            def route_event(e): ...

    try: ...                -> ast.TryStar    (Python 3.11)   LANDED
    except* ValueError:
        def dead_in_trystar(): ...

    class Outer:                                              LANDED
        class Inner:        -> public_defs went only ONE level into a class body
            def dead_inner_method(self): ...

THE ROOT CAUSE IS THE ANTI-PATTERN THIS FILE ALREADY WARNS ABOUT, two functions higher, in its own
words about ENTRY_POINTS:

    "EVERY seat runner, enumerated rather than listed by hand (2026-08-01). The hand-written list
     named only bifrost_runner_deepseek and drifted the moment new seats landed."

I read that comment, agreed with it, and then wrote a hand list anyway one function down -- and the
Python grammar drifted past it instead of the fleet. `match` and `except*` are not exotic; they are
language features newer than the tuple.

THE FIX HAS NO LIST. Walk any statement that is not a def, through `ast.iter_fields`, and never
descend into a FunctionDef body. Nested `ExceptHandler` and `match_case` are not statements
themselves, so their bodies are reached one level deeper -- generically, not by name. A grammar
addition in Python 3.14 will be handled by code written today.

Same shape as T145 one layer up: patch the MEANING, not the enumeration.

  N1  a def inside `match`/`case` is a candidate              (ast.Match)
  N2  a def inside `except*` is a candidate                   (ast.TryStar)
  N3  a method on an INNER class is a candidate
  N4  a NESTED def is still NOT a candidate                   (the fix must not overreach)
  N5  a def inside a container inside a class counts as a method
  N6  the previously-covered shapes still work                (no regression on if/try/with/for)

Run: py -m pytest tests/test_t146_containers_are_not_a_list.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402


def _defs(tmp_path, body):
    p = tmp_path / "core" / "comm"
    p.mkdir(parents=True, exist_ok=True)
    (p / "probe.py").write_text(body, encoding="utf-8")
    return check_wiring.public_defs("core/comm/probe.py", root=str(tmp_path))


def _names(tmp_path, body):
    return {n for n, _lo, _hi, _m in _defs(tmp_path, body)}


def test_n1_def_inside_match_is_a_candidate(tmp_path):
    got = _names(tmp_path,
                 '_MODE = "direct"\n'
                 "match _MODE:\n"
                 '    case "fanout":\n'
                 "        def route_event(e):\n"
                 "            return [e]\n"
                 "    case _:\n"
                 "        pass\n")
    assert "route_event" in got, "ast.Match was not in the hand-written container tuple"


def test_n2_def_inside_except_star_is_a_candidate(tmp_path):
    got = _names(tmp_path,
                 "try:\n"
                 "    pass\n"
                 "except* ValueError:\n"
                 "    def dead_in_trystar():\n"
                 "        return 1\n")
    assert "dead_in_trystar" in got, "ast.TryStar is a distinct node from ast.Try"


def test_n3_a_method_on_an_inner_class_is_a_candidate(tmp_path):
    got = _names(tmp_path,
                 "class Outer:\n"
                 "    class Inner:\n"
                 "        def dead_inner_method(self):\n"
                 "            return 1\n")
    assert "dead_inner_method" in got


def test_n4_a_nested_def_is_still_not_a_candidate(tmp_path):
    """The limit on the fix. A closure is private by construction, and flooding this gate is how a
    guard gets fed exceptions until it guards nothing."""
    got = _names(tmp_path,
                 "def outer():\n"
                 "    def inner_helper():\n"
                 "        return 1\n"
                 "    class AlsoPrivate:\n"
                 "        def hidden(self):\n"
                 "            return 2\n"
                 "    return inner_helper()\n")
    assert "outer" in got
    assert "inner_helper" not in got and "hidden" not in got


def test_n5_a_def_in_a_container_in_a_class_is_a_method(tmp_path):
    got = _defs(tmp_path,
                "import sys\n"
                "class Thing:\n"
                "    if sys.platform == 'win32':\n"
                "        def platform_specific(self):\n"
                "            return 1\n")
    by_name = {n: m for n, _lo, _hi, m in got}
    assert by_name.get("platform_specific") is True, "in-class context must survive the container"


def test_n6_the_previously_covered_shapes_still_work(tmp_path):
    got = _names(tmp_path,
                 "if True:\n"
                 "    def from_if():\n"
                 "        return 1\n"
                 "try:\n"
                 "    def from_try():\n"
                 "        return 2\n"
                 "except ImportError:\n"
                 "    def from_except():\n"
                 "        return 3\n"
                 "for _ in range(1):\n"
                 "    def from_for():\n"
                 "        return 4\n"
                 "\n"
                 "def plain():\n"
                 "    return 5\n")
    assert {"from_if", "from_try", "from_except", "from_for", "plain"} <= got
