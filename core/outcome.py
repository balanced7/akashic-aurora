"""BoundaryOutcome -- the one answer every fleet boundary gives to "what happened?" (T170).

WHY THIS EXISTS. On 2026-08-04 six defects were fixed (T147 T149 T150 T151 T167 T169) and they
were the SAME defect in six costumes: a boundary that failed and said nothing.

    rearm -> daemon     TypeError every tick        said: ok = False
    send  -> recipient  collapsed, not sent         said: "sent", with the original's id
    runner -> roster    never published its key     said: DEAD
    grant -> resolve    silently quarantined        said: nothing
    runner -> operator  block-buffered              said: 0 bytes
    agent -> conductor  budget spent                said: ""

Each subsystem had invented its own answer to "what happened": an int that swallows exceptions, a
mid plus a `last_reask` SIDE CHANNEL contradicted by stdout, a dict annotated `-> bool`, a
str-or-empty, a silent downgrade to quarantined. Five dialects, so every consumer had to speak
five, and none of them could express PARTIAL at all -- which is exactly why partial work vanished.
T169's fix was inventing "partial" by hand, locally, for one function.

THE ENFORCEMENT IS THE TYPE, NOT A GREP. The obvious guard -- scan for `except: return <falsy>` --
measures 1559 silent handlers, or 523 if narrowed to ones manufacturing a falsy verdict. Freezing
either is theater, and narrowing further needs a hand-written list of "action verbs" that would
drift the way _CONTAINERS drifted past `match` in T146. So the rule lives in the constructor:
**a failed BoundaryOutcome without a reason cannot be built.** A boundary that returns BoundaryOutcome cannot go
silent, because silence is unrepresentable.

NAMED BoundaryOutcome, NOT Outcome, and the reason is on the nose: check_boundaries REFUSED the
first version because core/coord/experiment.py already defines a class Outcome (a coordination-
policy simulation result -- admitted/blocked action lists, an unrelated concept). Proposing ONE
vocabulary to reduce ambiguity and immediately minting a colliding name is the exact failure this
type exists to prevent, one level up. The guard caught it in the same commit it was introduced.

WHAT IT ENABLES, which is the point of simplifying. One shape composes: the delivery ledger, the
Season 1 scoreboard, retry policy, doctor rows and the canary oracle each need a bespoke adapter
per subsystem today. Given one vocabulary they read everything, and a twentieth seat or a new
scoring axis costs nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BoundaryOutcome:
    """What happened at a boundary. Never silent, always answerable.

    ok      -- did the thing actually happen
    why     -- REQUIRED when not ok, or when partial: one line, in the reader's terms
    ref     -- the handle to act on (message id, pid, sha, path) when there is one
    partial -- the thing happened INCOMPLETELY; `why` says what is missing
    detail  -- optional structured extras; never load-bearing for the verdict
    """
    ok: bool
    why: str = ""
    ref: Optional[str] = None
    partial: bool = False
    detail: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # THE WHOLE POINT. A failure or a partial that cannot say why is the defect this type
        # exists to make unrepresentable -- six of them shipped before anyone noticed.
        if (not self.ok or self.partial) and not str(self.why).strip():
            raise ValueError(
                "BoundaryOutcome(ok=False) and BoundaryOutcome(partial=True) require a `why`. A boundary that "
                "fails silently is the T170 defect: the caller cannot tell 'did not happen' from "
                "'happened and had nothing to say'.")

    def __bool__(self) -> bool:
        """Truthy iff it fully happened. `if send(...)` stays readable, and a PARTIAL is falsy --
        a caller that ignores partiality is treated as not-done rather than quietly succeeding."""
        return bool(self.ok and not self.partial)

    @classmethod
    def done(cls, ref: Optional[str] = None, **detail) -> "BoundaryOutcome":
        return cls(ok=True, ref=ref, detail=detail)

    @classmethod
    def failed(cls, why: str, ref: Optional[str] = None, **detail) -> "BoundaryOutcome":
        return cls(ok=False, why=why, ref=ref, detail=detail)

    @classmethod
    def partially(cls, why: str, ref: Optional[str] = None, **detail) -> "BoundaryOutcome":
        """Happened, incompletely. The state five dialects could not express, and the reason
        109KB of correct analysis died in a log on 2026-08-04."""
        return cls(ok=True, why=why, ref=ref, partial=True, detail=detail)

    @classmethod
    def caught(cls, exc: BaseException, where: str = "", ref: Optional[str] = None) -> "BoundaryOutcome":
        """Fail-open WITHOUT going silent -- the exact shape consume_rearms needed.

        Fail-open is correct: a bad spawn must not kill the daemon loop. Silent fail-open is what
        turned a one-line arity typo into a permanent invisible no-op for weeks (T167).
        """
        return cls(ok=False, ref=ref,
                   why=f"{where + ': ' if where else ''}{type(exc).__name__}: {exc}",
                   detail={"exception": type(exc).__name__})

    def line(self) -> str:
        """One render, so every surface reports a boundary the same way."""
        state = "OK" if self else ("PARTIAL" if self.partial else "FAILED")
        bits = [state]
        if self.ref:
            bits.append(f"ref={self.ref}")
        if self.why:
            bits.append(self.why)
        return " | ".join(bits)
