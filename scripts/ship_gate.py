"""ship_gate -- the suite gate as a ONE-WAY RATCHET (T031 unblock, 2026-07-27).

WHY THIS EXISTS
---------------
scripts/ship.py gates on the FULL pytest suite, fail-fast. The tree carries pre-existing
failures, so ship.py ABORTED ALWAYS -- the disciplined door was IMPASSABLE, not merely longer.
Measured consequence: six commits in one night through raw `git commit`, and therefore ZERO runs
of the three T031 method checkers that ride ship.py lines 38-42. The method loop
("awareness at boot -> recall at action -> gates at ship -> scorecard at wrap",
agent_cli.py:1449) is complete and correctly wired, and its enforcement stage was bypassed
because it could not be passed. Nobody forgot the method; the compliant path was blocked.

core/coord/suite_baseline.py already computed the needed delta ({new, fixed, inherited}) and
was never wired to the gate. This module is that wiring, and nothing more.

THE RISK, NAMED AND BOUNDED
---------------------------
Making a red suite shippable is exactly how "blocking" becomes "inherited" and an inherited list
rots into a growing amnesty -- the same shape as the four failures found the same night (a red
pin nobody ran; a stall filed at dashboard tier; a --check wired to nothing; 96% of lessons
unreachable). A computed red routed to a channel nobody acts on.

So this is a RATCHET, not an amnesty, and the ratchet is the whole design:
  * a NEW failure always blocks -- no flag, no override
  * a FIXED failure leaves the baseline AUTOMATICALLY and can never quietly return; if it
    regresses it is NEW, and it blocks. This is the self-limiting property: the list can only
    shrink through ordinary work, and growing it takes deliberate action.
  * inherited failures are ANNOUNCED on every ship. Silence is how a red becomes furniture.
  * a stale baseline announces its own age.
  * NO baseline FAILS CLOSED. Absence of evidence is not amnesty -- that is the confident-zero
    disease in gate form, and suite_baseline.delta() already gets this right by putting
    everything in `new`.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import suite_baseline as sb   # noqa: E402

DEFAULT_STALE_S = 48 * 3600          # announce: the list is getting old

# THE TTL IS WHAT MAKES THIS A DEFERRAL INSTEAD OF AN AMNESTY (deepseek's counter, 2026-07-27,
# and its stated condition for not opposing this change). A passive "stale" line would BE the
# disease -- a computed red routed to a channel nobody acts on, which is the exact shape of the
# four failures found the same night. So expiry is a HARD gate: past the TTL the exemption is
# REVOKED and inherited failures block again, forcing a fresh run and eyes on the list.
# Its line: "a failure that has been inherited for a week isn't inherited -- it's owned."
# delta() is the COMPLIANCE half (did we add new failures?); the TTL is the OUTCOME half (are
# we retiring the old ones?). Compliance without outcome is the WHO-checklist failure.
DEFAULT_TTL_S = 168 * 3600           # one week


def _baseline_nodes() -> List[str]:
    rec = sb.read()
    return [f["node"] for f in (rec or {}).get("failures", [])]


def _age_s(rec: Optional[Dict[str, Any]], now: Optional[float]) -> Optional[float]:
    if not rec or not rec.get("at"):
        return None
    try:
        t = time.mktime(time.strptime(str(rec["at"]), "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None
    return max(0.0, (now if now is not None else time.time()) - t)


def evaluate(current_nodes: List[str], *, now: Optional[float] = None,
             stale_after_s: float = DEFAULT_STALE_S, ttl_s: float = DEFAULT_TTL_S,
             tighten: bool = True, seat: str = "ship_gate", sha: str = "") -> Dict[str, Any]:
    """Judge a suite run against the baseline. Returns the verdict; never raises.

    tighten=True performs the RATCHET: fixed failures are removed from the baseline as a side
    effect, so today's win cannot be re-borrowed tomorrow.
    """
    rec = sb.read()
    d = sb.delta(list(current_nodes or []))
    new, fixed, inherited = d["new"], d["fixed"], d["inherited"]
    blocked = bool(new)

    if tighten and rec and fixed:
        remaining = sorted(set(_baseline_nodes()) - set(fixed))
        try:
            sb.record(remaining, seat=seat, sha=sha)
        except Exception:
            pass                      # a failed tighten must never block a ship

    age = _age_s(rec, now)
    expired = bool(inherited) and age is not None and age > float(ttl_s)
    if expired:
        blocked = True               # the deferral lapsed: inherited failures are owned now

    lines: List[str] = []
    if expired:
        lines.append(f"BLOCKED: baseline EXPIRED ({int(age / 3600)}h old, TTL "
                     f"{int(ttl_s / 3600)}h). {len(inherited)} failure(s) have been "
                     f"'inherited' past the deferral window -- they are owned, not inherited. "
                     f"Fix them, or re-record the baseline deliberately and say why.")
    if blocked and new:
        lines.append(f"BLOCKED: {len(new)} NEW failure(s) not in the baseline")
        lines.extend(f"    NEW  {n}" for n in new[:12])
    if inherited:
        lines.append(f"shipping over {len(inherited)} INHERITED failure(s) "
                     f"-- known red, not silence:")
        lines.extend(f"    inherited  {n}" for n in inherited[:12])
    if fixed:
        lines.append(f"RATCHET: {len(fixed)} failure(s) FIXED and removed from the baseline "
                     f"-- they block if they return")
    if rec is None:
        lines.append("NO BASELINE -- failing closed; every failure blocks. "
                     "Record one: py agent_cli.py suite-baseline --record")
    elif age is not None and age > float(stale_after_s):
        lines.append(f"baseline is STALE ({int(age / 3600)}h old, seat={rec.get('seat', '?')}) "
                     f"-- an inherited list nobody refreshes is how a red becomes furniture")
    if not lines:
        lines.append("suite clean against baseline")

    return {"blocked": blocked, "new": new, "fixed": fixed, "inherited": inherited,
            "age_s": age, "report": "\n".join(lines)}


def evaluate_pytest_output(text: str, **kw) -> Dict[str, Any]:
    """Convenience for the ship path: parse a pytest run, then judge it."""
    return evaluate(sb.ingest_pytest(text or ""), **kw)


def main() -> int:
    """CLI so ship.py can keep its PURE (label, argv) plan -- the property that powers its
    --dry-run and its own tests. Runs the suite, judges it against the baseline, exits
    non-zero ONLY on a new failure."""
    import argparse
    import subprocess
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="run pytest, then judge the result")
    ap.add_argument("--no-tighten", action="store_true",
                    help="do not remove fixed failures from the baseline (diagnostic only)")
    a = ap.parse_args()
    if not a.run:
        ap.print_help()
        return 0

    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    v = evaluate_pytest_output(out, tighten=not a.no_tighten, seat="ship_gate")
    print(v["report"])
    if v["blocked"]:
        print("\n[ship-gate] A NEW failure is not in the baseline. Fix it, or -- if it is a "
              "deliberate known-red -- record a new baseline EXPLICITLY and say why.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
