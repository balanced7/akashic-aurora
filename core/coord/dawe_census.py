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
