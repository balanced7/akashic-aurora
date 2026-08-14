"""dawe_census -- which verbs are structurally UNVERIFIABLE, not which verbs are bad.

The house adopted a bar from Clarke & Dawe on 2026-08-13: a RESPONSE that is not an ANSWER
is a defect. "I'll respond, Brian; whether that constitutes an answer in your terms is
another matter." This module is the first mechanical thing built on it.

WHAT IT WILL NOT CLAIM, and the restraint is the design. A fan branch proposed flagging verbs
that print without returning a value. For a CLI verb that is NORMAL -- printing is the output
channel and an exit code is the return. A census that called those verbs defective would be
asserting a quality judgement its evidence cannot carry, which is precisely the failure it is
named after, committed by the instrument.

WHAT IT DOES CLAIM. A verb that is large AND calls no helper AND has no value-returning path
has fetch, transform and render FUSED into one body. That is not proof of a bad answer -- it
is proof that no seam exists at which the answer could be inspected, tested, or reused. The
finding is about VERIFIABILITY, not correctness:

    "these verbs are shaped so that whether they answer cannot be checked from outside"

Measured on agent_cli.py 2026-08-14: 65 of 87 verbs call no local helper (2,953 lines), and
every cmd_* is called by nothing, so the path of least resistance really is print-and-exit.
The six over 100 lines are 991 lines of it.

WHY A CENSUS AND NOT A GATE. instrument_proposes_never_self_ratifies: a structural predictor
has no business failing a commit until someone has hand-checked enough of its output to know
its false-positive rate. It reports, a human decides, and the day it earns a threshold it can
become a ratchet.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List

#: Calls that write to a terminal rather than returning a value.
TERMINAL_WRITES = {"print", "echo", "pprint"}

#: Below this, a fused body is small enough to read whole, so fusion costs nothing.
BIG_ENOUGH_TO_HIDE = 100


@dataclass(frozen=True)
class VerbShape:
    name: str
    lineno: int
    body_lines: int
    helper_calls: int
    terminal_writes: int
    value_returns: int

    @property
    def fused(self) -> bool:
        """No helper seam and no value-returning path: fetch/transform/render in one body."""
        return self.helper_calls == 0 and self.value_returns == 0

    @property
    def unverifiable(self) -> bool:
        return self.fused and self.body_lines >= BIG_ENOUGH_TO_HIDE


def survey(source: str, prefix: str = "cmd_") -> List[VerbShape]:
    """Shape every top-level `prefix*` function. Pure: takes source, returns data."""
    tree = ast.parse(source)
    local = {n.name for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out: List[VerbShape] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith(prefix):
            continue
        helpers = writes = returns = 0
        for c in ast.walk(node):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                if c.func.id in local and c.func.id != node.name:
                    helpers += 1
                elif c.func.id in TERMINAL_WRITES:
                    writes += 1
            elif isinstance(c, ast.Return) and c.value is not None:
                # `return None` and a bare `return` are exits, not answers.
                if not (isinstance(c.value, ast.Constant) and c.value.value is None):
                    returns += 1
        out.append(VerbShape(node.name, node.lineno,
                             getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                             helpers, writes, returns))
    return out


def render(shapes: List[VerbShape]) -> str:
    flagged = sorted((s for s in shapes if s.unverifiable), key=lambda s: -s.body_lines)
    fused_small = [s for s in shapes if s.fused and not s.unverifiable]
    out = [f"DAWE CENSUS -- {len(shapes)} verb(s) surveyed",
           "  This reports VERIFIABILITY, never quality. A flagged verb may answer perfectly;",
           "  the finding is that nothing outside it can check whether it does."]
    if not flagged:
        out.append("  no verb is both fused and large enough to hide -- nothing to report")
    else:
        out.append(f"  {len(flagged)} verb(s), {sum(s.body_lines for s in flagged):,} lines: "
                   f"large AND no helper seam AND no value-returning path")
        for s in flagged:
            out.append(f"    {s.body_lines:>5}  {s.name:<24} :{s.lineno:<6} "
                       f"{s.terminal_writes} terminal write(s)")
    out.append(f"  ({len(fused_small)} more are fused but under {BIG_ENOUGH_TO_HIDE} lines -- "
               f"small enough to read whole, so fusion costs nothing there)")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Silent degradation: the same bar, applied to imports rather than verbs.
# ---------------------------------------------------------------------------
#
# MEASURED on agent_cli.py 2026-08-14: 7 top-level imports, 284 FUNCTION-LOCAL ones,
# 67 try-blocks wrapping an import, and 42 of those swallowing it with a bare `pass`.
#
# A swallowed import is the purest form of the bar: a `core/` module that moves or gets
# renamed produces ZERO error, and the verb simply omits a section. It responds. It does not
# answer, and nothing anywhere says so.
#
# THIS DOES NOT CALL THEM BUGS. Some are deliberate and correct -- "boot must never fail" is a
# real design choice, and a boot that dies because one optional organ moved is worse than a
# boot that renders without it. The finding is not that 42 sites are wrong; it is that
# NOTHING DISTINGUISHES THE DELIBERATE ONES FROM THE ACCIDENTAL ONES, so the whole class is
# unauditable. A loud handler is self-classifying; a bare `pass` is not.


@dataclass(frozen=True)
class ImportGuard:
    lineno: int
    enclosing: str
    modules: tuple
    handler: str          # silent | loud | reraise


def survey_import_guards(source: str) -> List[ImportGuard]:
    """Every try-block that wraps an import, and what its handler does about failure."""
    tree = ast.parse(source)
    owner = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for c in ast.walk(fn):
                owner[id(c)] = fn.name

    out: List[ImportGuard] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        mods = []
        for b in node.body:
            for c in ast.walk(b):
                if isinstance(c, ast.ImportFrom) and c.module:
                    mods.append(c.module)
                elif isinstance(c, ast.Import):
                    mods.extend(a.name for a in c.names)
        if not mods:
            continue
        for h in node.handlers:
            body = h.body
            if any(isinstance(st, ast.Raise) for st in body):
                kind = "reraise"
            elif len(body) == 1 and isinstance(body[0], ast.Pass):
                kind = "silent"
            elif (len(body) == 1 and isinstance(body[0], ast.Expr)
                  and isinstance(body[0].value, ast.Constant)):
                kind = "silent"          # a docstring-as-body is still a pass
            else:
                kind = "loud"            # it logs, prints, records or sets a fallback flag
            out.append(ImportGuard(h.lineno, owner.get(id(node), "<module>"),
                                   tuple(sorted(set(mods))), kind))
    return out


def render_import_guards(guards: List[ImportGuard]) -> str:
    silent = [g for g in guards if g.handler == "silent"]
    loud = [g for g in guards if g.handler == "loud"]
    by_fn = {}
    for g in silent:
        by_fn.setdefault(g.enclosing, []).append(g)
    out = [f"SILENT-DEGRADATION CENSUS -- {len(guards)} import guard(s)",
           "  A swallowed import means a moved or renamed module produces NO error and the",
           "  caller simply omits a section. Some of these are deliberate and correct; the",
           "  finding is that nothing distinguishes those from the accidental ones."]
    out.append(f"  {len(silent)} SILENT (bare pass) | {len(loud)} loud (logs/records/falls back)")
    for fn, gs in sorted(by_fn.items(), key=lambda kv: -len(kv[1]))[:12]:
        mods = sorted({m for g in gs for m in g.modules})[:3]
        out.append(f"    {len(gs):>3}x  {fn:<28} e.g. {', '.join(mods)}")
    if not silent:
        out.append("  no silent import guard -- every failure is announced")
    return "\n".join(out)
