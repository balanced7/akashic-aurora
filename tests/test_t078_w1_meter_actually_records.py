"""Pins: a runner that OPENS a token journal must actually RECORD to it.

WHY THIS EXISTS
---------------
T078-W1 shipped the TokenJournal as "the wave's first receipt-maker", verified 8/8 with a
live round-trip, and every runner that adopted it printed a reassuring boot line:

    [deepseek-runner] token journal: 0 turns, 0 tokens today

On 2026-07-25 -- asking what the token-efficiency work had actually produced -- there was no
`state/runner_<agent>_<date>.json` anywhere on disk, for any agent, ever. Two distinct bugs,
one outcome:

  deepseek: main() did `_token_journal = TokenJournal(...)` WITHOUT `global`, binding a
            function-local. The module-level `_token_journal` stayed None for the process
            lifetime, so the hot-path guard `if _token_journal is not None and delta:` never
            fired once.
  sol:      created a local `journal` and used it ONLY to print the boot line. add_turn is
            never called anywhere in the file. The meter was decorative.

Both printed a number every boot while measuring nothing -- the status-line-lies genus
(lesson: status_line_lies_cost_diagnoses), living inside the frugality organ itself.

These pins are STATIC so they cannot themselves go quiet: a runtime test needs a live API
turn, and a test you cannot run in CI is a test that stops running.
"""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
RUNNERS = sorted(
    p for p in (ROOT / "scripts").glob("bifrost_runner*.py")
    if p.suffix == ".py"
)


def _tree(p: Path) -> ast.AST:
    return ast.parse(p.read_text(encoding="utf-8"))


def _opens_journal(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Name) and n.id == "TokenJournal" for n in ast.walk(tree)
    ) or any(
        isinstance(n, ast.ImportFrom) and "runner_token_journal" in (n.module or "")
        for n in ast.walk(tree)
    )


def _records(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_turn"
        for n in ast.walk(tree)
    )


def _local_bind_without_global(tree: ast.AST) -> list:
    """Functions that bind a TokenJournal to a name but never declare it global.

    Only a problem when the name is ALSO read at module scope (the hot path). We approximate
    that with the underscore convention the runners use for module state.
    """
    bad = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        declared = {name for g in ast.walk(fn) if isinstance(g, ast.Global) for name in g.names}
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign):
                continue
            if "TokenJournal" not in ast.dump(node.value):
                continue
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.startswith("_") and t.id not in declared:
                    bad.append(f"{fn.name}() binds local '{t.id}' at line {node.lineno}")
    return bad


def test_every_runner_that_opens_a_journal_also_records_to_it():
    """A meter that is opened, printed, and never written is worse than no meter."""
    offenders = {}
    for p in RUNNERS:
        tree = _tree(p)
        if _opens_journal(tree) and not _records(tree):
            offenders[p.name] = "opens TokenJournal but never calls add_turn"
    assert not offenders, (
        "runner(s) print a token-journal reading while recording nothing: " + repr(offenders)
    )


def test_module_level_journal_is_not_shadowed_by_a_local_bind():
    """`_x = TokenJournal(...)` inside a function without `global _x` leaves the hot path dead."""
    offenders = {}
    for p in RUNNERS:
        bad = _local_bind_without_global(_tree(p))
        if bad:
            offenders[p.name] = bad
    assert not offenders, (
        "TokenJournal bound to a function-local while the hot path reads the module global "
        "(the deepseek 2026-07-25 defect): " + repr(offenders)
    )


def test_the_pins_are_actually_looking_at_runners():
    """Guard the guard: an empty RUNNERS list would pass both tests vacuously."""
    assert len(RUNNERS) >= 3, f"expected several runners, found {[p.name for p in RUNNERS]}"
    assert any(_opens_journal(_tree(p)) for p in RUNNERS), \
        "no runner references TokenJournal -- the pins above would be vacuous"
