"""Unbound-name guardrail -- a name that cannot resolve is a dead organ, counted and ratcheted.

Semantic Relationship: Guardrails enforce NoUnboundNames

WHY THIS EXISTS, AND IT IS A MEASURED NUMBER NOT A PREFERENCE
-------------------------------------------------------------
2026-10-05. An outside contributor's basedpyright pass reported F821 (undefined name) in
`agent_cli.py`. All six sites were real, verified here by scope resolution and then at runtime:

    agent_cli.get_agent_memory   ABSENT   _continuity_drift:1910
    agent_cli.capture_event      ABSENT   _wish_curate_run:2419, _wish_write:2501
    agent_cli.io                 ABSENT   cmd_season_score:6201
    agent_cli.time               ABSENT   cmd_locks:7957
    agent_cli.REPO               ABSENT   cmd_tool_run:10250

THREE OF THE SIX FAILED SILENTLY, AND THAT IS THE WHOLE POINT. The unbound name sat inside a
`try: ... except Exception: pass`, or inside a function-wide `try` returning a falsy default.
A fail-soft handler written to absorb runtime DATA errors also absorbs NameError, which is a
STATIC defect -- so the failure that should be loudest is the one most reliably hidden, and it
renders as a measured zero indistinguishable from the honest answer.

Two measurements, both taken before this checker was written:

  `_continuity_drift()` has NEVER rendered. Its one production caller (agent_cli.py:2214)
  passes no `notes`, reaches the unbound `get_agent_memory`, and the function's outer
  `except Exception: return ""` swallows it. Its docstring says "Silent when the notes are
  newer than HEAD -- no drift, no line", so the absence reads as *no drift*. All four tests in
  tests/test_continuity_drift.py pass `notes=` explicitly and are green; not one of them
  reaches the shape the only real caller uses.

  The wish door has NEVER emitted an event. 254 wishes in docs/WISHLIST.md against 0 events
  with kind='wish', scanned over 11,242 events in 58 `events:*:raw` streams. The spine is
  healthy -- touch 3,037, learning 718, decision 393 -- it is specifically `wish` that is
  absent, because `capture_event` raises at both write sites inside `except Exception: pass`.

THE HOUSE LAW THIS SERVES
-------------------------
"A sensor with no reader and a field with no writer are two different defects and both render
as a confident 0" (`partial_wiring_is_the_shape_module_gates_cannot_see`). And the broader one
derived six-plus times here: zero is not no. An unbound name inside a fail-soft handler is the
purest mechanical generator of a false zero in the tree.

WHY A CHECKER AND NOT SIX FIXES
-------------------------------
`when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`: the moment a defect shape is
named, grep the tree for it. Six named sites in one file is an instance list, not a sweep --
and naming is not sweeping, memory is not a checker. The instances are being fixed; this
counts the class so the seventh cannot arrive quietly.

WHY A COUNTED RATCHET
---------------------
A full-tree sweep over every module at once is exactly the change that breaks a fleet quietly,
and some sites sit in other seats' lanes. So `scripts/githooks/pre_commit.py` adopts the count
at TODAY's level; from the next commit it may FALL or hold and may never RISE. A commit cannot
be blamed for debt that predates it.

WHAT COUNTS, AND WHAT DELIBERATELY DOES NOT
-------------------------------------------
A violation is a `Load` of a bare name that resolves in NO enclosing scope: not builtins, not
module level (including imports guarded by try/if), not any enclosing function or
comprehension, not a parameter, not a `global`/`nonlocal` declaration.

Deliberately NOT violations, because each would be a false positive:
  - Class bodies. A method's body cannot see its class's attributes by bare name, but a
    name used inside the class BODY can; both are handled by treating the class body as a
    scope that is skipped by nested functions.
  - Modules containing `from x import *`. The star cannot be resolved statically, so such a
    module is SKIPPED ENTIRELY and reported as a skip, never silently passed.
  - `__class__`, and the implicit names inside comprehensions.
  - Conditional definitions. A name assigned in ANY branch at a scope counts as bound there,
    because this checker answers "can this name ever resolve", not "is it always set".
  - `del x` does not unbind for our purposes; the name was bound.

THE FALSE-NEGATIVE THIS ACCEPTS
-------------------------------
A name bound only on a path that never executes still counts as bound. Catching that needs
flow analysis, and a guard that over-reports gets disabled. basedpyright is the instrument for
that class; this is the cheap always-on floor that would have caught all six.

Run::

    py scripts/checkers/check_unbound_names.py
    py scripts/checkers/check_unbound_names.py --json
"""
from __future__ import annotations

import argparse
import ast
import builtins
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]

#: Directories whose contents are not live code. `archive` and the worktrees are other trees
#: entirely; `.venv` is not ours. Kept narrow on purpose -- an exclusion is slack.
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", ".claude", ".codex", ".cursor",
    "archive", "X", "logs", "state", ".pytest_cache", ".ruff_cache", "tooling-upgrade",
}

BUILTINS: Set[str] = set(dir(builtins)) | {
    "__name__", "__file__", "__doc__", "__package__", "__spec__", "__loader__",
    "__builtins__", "__debug__", "__class__", "__annotations__", "__dict__",
}


# --------------------------------------------------------------------------- scope collection
class _Scope:
    """One lexical scope. `transparent` marks a class body: nested functions skip it."""

    __slots__ = ("names", "kind", "globals_", "nonlocals")

    def __init__(self, kind: str) -> None:
        self.names: Set[str] = set()
        self.kind = kind                      # module | function | class | comp
        self.globals_: Set[str] = set()
        self.nonlocals: Set[str] = set()


def _bind_target(node: ast.AST, scope: _Scope) -> None:
    """Add every Name bound by an assignment/for/with/except target."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            scope.names.add(sub.id)


def _collect(node: ast.AST, scope: _Scope) -> None:
    """Bind every name this scope introduces, WITHOUT descending into nested scopes.

    Nested scopes get their own _Scope when the resolver walks them; here we only record the
    NAME the nested def/class/lambda binds in THIS scope.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Import):
            for a in child.names:
                scope.names.add((a.asname or a.name).split(".")[0])
        elif isinstance(child, ast.ImportFrom):
            for a in child.names:
                if a.name == "*":
                    continue                  # handled by the caller: module is skipped
                scope.names.add(a.asname or a.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.names.add(child.name)
            continue                          # do NOT descend: its body is another scope
        elif isinstance(child, ast.Lambda):
            continue
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            continue
        elif isinstance(child, ast.Assign):
            for t in child.targets:
                _bind_target(t, scope)
        elif isinstance(child, (ast.AnnAssign, ast.AugAssign)):
            if child.target is not None:
                _bind_target(child.target, scope)
        elif isinstance(child, ast.NamedExpr):
            _bind_target(child.target, scope)
        elif isinstance(child, (ast.For, ast.AsyncFor)):
            _bind_target(child.target, scope)
        elif isinstance(child, ast.ExceptHandler):
            if child.name:
                scope.names.add(child.name)
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            for item in child.items:
                if item.optional_vars is not None:
                    _bind_target(item.optional_vars, scope)
        elif isinstance(child, ast.Global):
            scope.globals_.update(child.names)
            scope.names.update(child.names)
        elif isinstance(child, ast.Nonlocal):
            scope.nonlocals.update(child.names)
            scope.names.update(child.names)
        elif isinstance(child, (ast.Match,)):
            # match-case capture patterns bind names
            for sub in ast.walk(child):
                if isinstance(sub, ast.MatchAs) and sub.name:
                    scope.names.add(sub.name)
                elif isinstance(sub, ast.MatchStar) and sub.name:
                    scope.names.add(sub.name)
                elif isinstance(sub, ast.MatchMapping) and sub.rest:
                    scope.names.add(sub.rest)
        # recurse through plain statement containers (if/try/while/else bodies)
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                  ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                                  ast.GeneratorExp)):
            _collect(child, scope)


def _params(fn) -> Set[str]:
    a = fn.args
    out = {p.arg for p in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)}
    if a.vararg:
        out.add(a.vararg.arg)
    if a.kwarg:
        out.add(a.kwarg.arg)
    return out


# ------------------------------------------------------------------------------- the resolver
class _Resolver(ast.NodeVisitor):
    def __init__(self, module: ast.Module, lazy_annotations: bool = False) -> None:
        mod = _Scope("module")
        _collect(module, mod)
        self.stack: List[_Scope] = [mod]
        self.fn_stack: List[str] = []
        self.violations: List[Tuple[int, str, str]] = []   # (lineno, name, where)
        #: PEP 563. With `from __future__ import annotations` every annotation is stored as a
        #: STRING and never evaluated, so an unresolvable name inside one raises nothing. The
        #: first version of this checker did not know that and reported 23 findings across
        #: core/comm/ask.py, toolbox.py and incarnation.py -- every one a `Dict`/`Any` in an
        #: annotation under a future-import, i.e. 23 false positives in the most load-bearing
        #: modules in the tree. Caught by validating against six KNOWN sites first and then
        #: reading the ones I had not predicted, which is the only reason the count is honest.
        self.lazy_annotations = lazy_annotations

    # -- scope helpers ---------------------------------------------------------------------
    def _resolves(self, name: str) -> bool:
        if name in BUILTINS:
            return True
        # a function skips enclosing CLASS bodies, per Python's own scoping rule
        for i, sc in enumerate(reversed(self.stack)):
            if sc.kind == "class" and i != 0:
                continue
            if name in sc.names:
                return True
        return False

    def _where(self) -> str:
        return self.fn_stack[-1] if self.fn_stack else "<module>"

    # -- scopes ----------------------------------------------------------------------------
    def _function(self, node) -> None:
        # decorators and defaults evaluate in the ENCLOSING scope
        for d in node.decorator_list:
            self.visit(d)
        a = node.args
        for d in list(a.defaults) + [x for x in a.kw_defaults if x is not None]:
            self.visit(d)
        if not self.lazy_annotations:
            for p in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs) + \
                     ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else []):
                if p.annotation is not None:
                    self.visit(p.annotation)
            if getattr(node, "returns", None) is not None:
                self.visit(node.returns)

        sc = _Scope("function")
        sc.names |= _params(node)
        for st in node.body:
            _collect(ast.Module(body=[st], type_ignores=[]), sc)
        self.stack.append(sc)
        self.fn_stack.append(node.name)
        for st in node.body:
            self.visit(st)
        self.fn_stack.pop()
        self.stack.pop()

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def visit_Lambda(self, node) -> None:
        a = node.args
        for d in list(a.defaults) + [x for x in a.kw_defaults if x is not None]:
            self.visit(d)
        sc = _Scope("function")
        sc.names |= _params(node)
        self.stack.append(sc)
        self.visit(node.body)
        self.stack.pop()

    def visit_ClassDef(self, node) -> None:
        for d in node.decorator_list:
            self.visit(d)
        for b in list(node.bases) + [k.value for k in node.keywords]:
            self.visit(b)
        sc = _Scope("class")
        for st in node.body:
            _collect(ast.Module(body=[st], type_ignores=[]), sc)
        self.stack.append(sc)
        self.fn_stack.append(node.name)
        for st in node.body:
            self.visit(st)
        self.fn_stack.pop()
        self.stack.pop()

    def _comp(self, node) -> None:
        # the FIRST iterable evaluates in the enclosing scope; the rest inside
        sc = _Scope("comp")
        for i, gen in enumerate(node.generators):
            if i == 0:
                self.visit(gen.iter)
            _bind_target(gen.target, sc)
        self.stack.append(sc)
        for i, gen in enumerate(node.generators):
            if i != 0:
                self.visit(gen.iter)
            for cond in gen.ifs:
                self.visit(cond)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.stack.pop()

    visit_ListComp = _comp
    visit_SetComp = _comp
    visit_DictComp = _comp
    visit_GeneratorExp = _comp

    def visit_AnnAssign(self, node) -> None:
        """`x: Dict[Any, Any] = {}` -- the annotation is not evaluated under PEP 563."""
        if not self.lazy_annotations and node.annotation is not None:
            self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
        if node.target is not None and not isinstance(node.target, ast.Name):
            self.visit(node.target)          # attribute/subscript targets still evaluate

    # -- the check ------------------------------------------------------------------------
    def visit_Name(self, node) -> None:
        if isinstance(node.ctx, ast.Load) and not self._resolves(node.id):
            self.violations.append((node.lineno, node.id, self._where()))
        self.generic_visit(node)


# ------------------------------------------------------------------------------------- driver
def _py_files() -> List[Path]:
    out: List[Path] = []
    for p in ROOT.rglob("*.py"):
        parts = set(p.relative_to(ROOT).parts)
        if parts & SKIP_DIRS:
            continue
        out.append(p)
    return sorted(out)


#: Paths that are not this house's live code: vendored third party, explicitly archived, and
#: scratch. Their findings are REPORTED SEPARATELY rather than dropped, because an exclusion
#: that cannot be seen is slack, and a guard with invisible slack is a rubber stamp. They are
#: simply not in the ratcheted count -- we do not own them and cannot fix them.
_NOT_OURS_PREFIXES = (
    "ComfyUI-Zluda/",          # vendored third party
    "docs/_archive/",          # explicitly archived
    "research/in-flight/t342/dead-modules/",
    "scratch/", "temp/",       # fragments and scratch, never imported
)


def _NOT_OURS(rel: str) -> bool:
    return rel.startswith(_NOT_OURS_PREFIXES)


def check(as_json: bool = False) -> int:
    offenders: List[Tuple[str, int, str, str]] = []
    not_ours: List[Tuple[str, int, str, str]] = []
    skipped_star: List[str] = []
    unparsed: List[Tuple[str, str]] = []

    for path in _py_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            # utf-8-SIG, not utf-8: three of this repo's own files carry a UTF-8 BOM
            # (scripts/arc_scorecard.py, tests/test_exec_env_identity.py,
            # tests/test_t075_m1_daemon.py). Python's import machinery strips it, but
            # read_text("utf-8") keeps it and ast.parse then fails at line 1. The first
            # version of this checker reported those three as "could not be parsed" --
            # three files silently unchecked. They were only visible because the skip is
            # REPORTED; a checker that passed them quietly would have hidden them forever.
            src = path.read_text(encoding="utf-8-sig")
        except Exception as e:                                   # noqa: BLE001
            unparsed.append((rel, f"unreadable: {e}")); continue
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError as e:
            unparsed.append((rel, f"SyntaxError line {e.lineno}")); continue
        if any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names)
               for n in ast.walk(tree)):
            skipped_star.append(rel); continue
        lazy = any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
                   and any(a.name == "annotations" for a in n.names)
                   for n in tree.body)
        r = _Resolver(tree, lazy_annotations=lazy)
        for st in tree.body:
            r.visit(st)
        bucket = not_ours if _NOT_OURS(rel) else offenders
        for lineno, name, where in r.violations:
            bucket.append((rel, lineno, name, where))

    if as_json:
        print(json.dumps({
            "violations": [{"file": f, "line": l, "name": n, "in": w}
                           for f, l, n, w in offenders],
            "count": len(offenders),
            "not_ours": [{"file": f, "line": l, "name": n, "in": w}
                         for f, l, n, w in not_ours],
            "not_ours_count": len(not_ours),
            "skipped_star_import": skipped_star,
            "unparsed": [{"file": f, "why": w} for f, w in unparsed],
        }, indent=2))
        return 1 if offenders else 0

    # Typed absence, every time: a skip is REPORTED, never silently passed. Zero is not no.
    if skipped_star:
        print("SKIPPED, not counted: %d module(s) use `from x import *`, which cannot be"
              % len(skipped_star))
        print("resolved statically. These are UNCHECKED, not clean:")
        for rel in skipped_star:
            print("  ? %s" % rel)
        print()
    if unparsed:
        print("SKIPPED, not counted: %d file(s) could not be parsed:" % len(unparsed))
        for rel, why in unparsed:
            print("  ? %s (%s)" % (rel, why))
        print()
    if not_ours:
        files = sorted({f for f, _, _, _ in not_ours})
        print("NOT OURS, not counted: %d finding(s) in %d vendored/archived/scratch file(s)."
              % (len(not_ours), len(files)))
        print("Real, and we cannot fix them; shown so the exclusion is visible:")
        for f in files:
            print("  ~ %s (%d)" % (f, sum(1 for g, _, _, _ in not_ours if g == f)))
        print()

    if offenders:
        # The heading MUST start with "VIOLATIONS" -- pre_commit._count_violations only counts
        # itemised "- [" lines inside a VIOLATIONS block and otherwise falls back to counting
        # FAIL: summaries. check_session_resolvers titled its block differently and the ratchet
        # adopted 1 instead of 16; a baseline built from a wrong count is a rubber stamp.
        print("VIOLATIONS -- names that resolve in no enclosing scope (%d):" % len(offenders))
        for rel, lineno, name, where in offenders:
            print("  - [%s:%d] `%s` in %s" % (rel, lineno, name, where))
        print("\nFAIL: %d bare name(s) cannot resolve at runtime." % len(offenders))
        print("      Each raises NameError when reached. If the site sits inside a fail-soft")
        print("      `except Exception`, it raises SILENTLY and the organ renders a false")
        print("      zero -- which is how the wish door filed 254 wishes and emitted 0 events.")
        print("      Fix the binding; do not widen the except.")
        return 1

    print("PASS: every bare name resolves in some enclosing scope.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable, for the ratchet")
    a = ap.parse_args()
    return check(as_json=a.json)


if __name__ == "__main__":
    sys.exit(main())
