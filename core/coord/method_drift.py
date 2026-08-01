"""method_drift -- the one method number that reaches a channel people actually read.

WHY THIS EXISTS
---------------
M3 pre-registration compliance is measured (arc_scorecard, 30% live on 2026-07-27). But
arc_scorecard is a READER wired to the `wrap` verb, and wrap goes unrun for whole sessions --
the same shape as ship.py holding the method checkers behind a suite gate that could never
pass. A number nobody reads is not observability; it is the seventh computed red with no
channel found in a single night.

Boot has PROVEN readership: a seat reads that block and acts on it (delta, mail, funnel)
within the first minute of a session. So the drift line rides boot.

THE CONSTRAINT THAT SHAPES IT (deepseek, round 2, and it killed my first proposal)
----------------------------------------------------------------------------------
Do not simply add traffic to a read channel. Its walkthrough: tool call 1 helps, call 12 is
skimmed, call 27 -- the one that mattered -- is dismissed, because 26 prior impressions taught
the reader that this channel is low signal. Adding method reminders to a busy channel does not
solve banner-blindness; it accelerates it.

Its prescription is TRIGGER SELECTIVITY: evaluate every trigger, stay SILENT on the ones that
do not fire, speak only when something is true and actionable. So this module is silent while
we are compliant. There is deliberately NO "method: all good" line -- that line is the
furniture, and furniture is how the message that mattered gets skimmed.

Silence here means "nothing has drifted", never "nothing was checked": an unmeasurable window
also renders silent, because a fabricated healthy number is the confident-zero disease and this
whole arc exists to stop building those.
"""
from __future__ import annotations

import os
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Below this, boot speaks. 80% is deliberately not 100%: a single legitimately-bundled commit
# (a pin and its fix that genuinely cannot be split) must not trip the alarm, or the alarm
# becomes noise and we are back to banner-blindness.
DEFAULT_THRESHOLD = 80.0
WINDOW = 30


def _stats(n: int) -> Dict[str, Any]:
    """Measured M3 compliance. Injectable so the pins never shell out to git.

    T123: this used to mutate the import path to reach scripts/checkers and pull the checker
    back in -- an INVERTED dependency (core reaching out to the script layer) that the
    architecture guardrail refuses by rule `no-syspath-insert`. The metric now lives at
    core/coord/preregistration.py; this reader and the ship gate both import INWARD from it.
    """
    from core.coord.preregistration import audit_stats
    return audit_stats(n)


def boot_line(threshold: float = DEFAULT_THRESHOLD, window: int = WINDOW) -> str:
    """One line when the practice has drifted; EMPTY STRING otherwise. Never raises."""
    try:
        s = _stats(window)
    except Exception:
        return ""                     # fail open, silently: a reader must never break boot
    total = int(s.get("total") or 0)
    if total <= 0:
        return ""                     # no window is not compliance -- absence is not evidence
    pct = float(s.get("pct") or 0.0)
    if pct >= float(threshold):
        return ""                     # compliant -> silent. The absence of a line IS the signal.
    clean = int(s.get("clean") or 0)
    return (f"method drift: M3 pre-registration {clean}/{total} clean ({pct:.0f}%) -- pins are "
            f"landing WITH their implementation, so git holds no evidence the acceptance came "
            f"first. Commit the RED pin alone, then the fix. (py scripts/arc_scorecard.py)")
