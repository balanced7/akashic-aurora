"""gap_ledger -- charter P0: every restoration is honest about what it restored.

The arc's first property and its most-converged (three blind derivations: Heimdall's
amnesia-masquerading-as-continuity, Navi's every-recovered-seat-knows-it-has-recovered,
the operator-side replay finding). The wound, receipted 08-12/13: every boot organ
fail-opened SILENTLY, so a seat with a dead ask verb, invisible memory roots and a
dark watcher rendered exactly like a healthy one -- silence impersonating success.

The organ is deliberately tiny: a per-boot collector the organs report into, and one
render. Laws it enforces by shape:

  - A CLEAN boot still renders (one line) -- so a clean render is distinguishable
    from a dead collector.
  - An UNINSTRUMENTED ledger confesses itself -- absence must never read as success
    (the guard-of-guards law).
  - PARTIAL is not LOADED -- restoring 100% of a fragment is a persistence success
    and a correctness failure; this ledger is the artifact that keeps those two
    measurements apart (charter invariant).
  - Reporting NEVER raises, rendering never multiplies lines uncontrolled: honesty
    organs must be cheaper than the dishonesty they end.
"""
from __future__ import annotations

from typing import List, Tuple

_STATUSES = ("loaded", "partial", "absent", "failed")


class GapLedger:
    def __init__(self) -> None:
        self._rows: List[Tuple[str, str, str]] = []

    def report(self, plane: str, status: str, why: str = "") -> None:
        """Record one plane's restoration verdict. Never raises; an unknown status
        is coerced to 'failed' with the coercion CONFESSED in the why -- a bad
        report is itself a gap, not a crash."""
        try:
            p = " ".join(str(plane or "unnamed-plane").split())
            s = str(status or "").strip().lower()
            w = " ".join(str(why or "").split())
            if s not in _STATUSES:
                w = (w + " " if w else "") + f"[reported unknown status {s!r} -- coerced to failed]"
                s = "failed"
            self._rows.append((p, s, w))
        except Exception:
            pass

    def render(self) -> str:
        """The boot-head block. One line clean; expanded when gapped; confessional
        when empty."""
        if not self._rows:
            return ("# restored: 0/0 planes -- GAP LEDGER UNINSTRUMENTED this boot "
                    "(no organ reported; treat fullness claims with suspicion)")
        total = len(self._rows)
        loaded = sum(1 for _, s, _ in self._rows if s == "loaded")
        if loaded == total:
            names = ", ".join(p for p, _, _ in self._rows)
            return f"# restored: {loaded}/{total} planes clean ({names})"
        lines = [f"# RECOVERED WITH GAPS -- {loaded}/{total} planes loaded:"]
        for p, s, w in self._rows:
            if s == "loaded":
                continue
            label = {"failed": f"{p} FAILED", "partial": f"{p} PARTIAL",
                     "absent": f"{p} absent"}[s]
            lines.append(f"#   {label}" + (f" ({w})" if w else ""))
        return "\n".join(lines)
