"""The failsafe deadman -- an out-of-band watcher that survives the bus it watches.

Daniil, 2026-08-20: "an always on failsafe watcher that isn't tied to the bifrost as a recovery
mechanism for if you forgot to set a watcher."

OUT-OF-BAND IS THE WHOLE POINT. control_channel.py records what happens otherwise:
"control.is_halted is checked inside the message-handling path, which only runs AFTER a message
arrives, which is exactly what a blocked read prevents" -- kimi was once up, heartbeating and
uncommandable for twelve hours. Anything living on Bifrost goes blind in precisely the failures
worth watching for. This module touches no redis, no bus, no lane: a JSON file, a clock, and
(in the runner) a write-only webhook.

THE EXPECTATION IS THE HARD HALF, NOT THE TIMER. Silence is usually CORRECT -- at 3am with no run
active, quiet is the right state, and a watcher that alarms on quiet gets muted, leaving us blind
for a worse reason than before. So this implements the rule earned on 2026-08-19: A HEARTBEAT
PROVES PRESENCE AND CANNOT PROVE ABSENCE; absence only becomes measurable against a DURABLE
EXPECTATION. No expectation on disk -> no alarm, ever.

The file lives OUTSIDE the process that declares it, so a crashed or 529'd session leaves its
expectation behind and the watcher still fires. That is the entire mechanism.

V1 IS NOTIFY-ONLY by decision. Auto-recovery (spawning a fresh seat) is feasible now that T366/T367
make a stillborn spawn visible, but this house has scars from thundering-herd spawns, so that half
waits on Daniil's ruling. A zero-blast-radius watcher that reliably speaks is most of the value.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

#: Default silence budget: how long a declared-active run may go unstamped before it is wrong.
DEFAULT_GRACE_S = 1800.0
#: Do not re-alarm inside this window. An un-cooled alarm fires every scheduler tick and becomes
#: wallpaper, which is how a monitor stops being read.
DEFAULT_COOLDOWN_S = 1800.0


def default_path() -> str:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.getenv("AKASHIC_RUN_EXPECTATION") or os.path.join(
        here, "state", "expect", "run-active.json")


# ---------------------------------------------------------------- the decidable half (pinned)
def verdict(expectation: Any, *, now: Optional[float] = None) -> Optional[str]:
    """The alarm line, or None for silence. Pure: hand it a dict, get a decision.

    Fails toward SILENCE on anything malformed. A watcher that alarms on its own parse errors
    teaches the reader to ignore it, and an ignored monitor is worse than an absent one."""
    now = float(now if now is not None else time.time())
    if not isinstance(expectation, dict):
        return None
    if not expectation.get("active"):
        return None                      # stood down, or never declared: quiet is correct
    stamped = expectation.get("checkpoint_at")
    if not isinstance(stamped, (int, float)) or isinstance(stamped, bool):
        return None                      # cannot tell -> say nothing, never a false alarm
    grace = expectation.get("grace_s")
    grace = float(grace) if isinstance(grace, (int, float)) and not isinstance(grace, bool) \
        else DEFAULT_GRACE_S
    silent_for = now - float(stamped)
    if silent_for <= grace:
        return None
    last = expectation.get("last_alarm_at")
    if isinstance(last, (int, float)) and not isinstance(last, bool):
        cooldown = expectation.get("cooldown_s")
        cooldown = float(cooldown) if isinstance(cooldown, (int, float)) \
            and not isinstance(cooldown, bool) else DEFAULT_COOLDOWN_S
        if now - float(last) < cooldown:
            return None                  # already said it recently; do not become wallpaper
    who = str(expectation.get("declared_by") or "an undeclared seat")
    what = str(expectation.get("what") or "an unnamed run")
    mins = int(silent_for // 60)
    return (f"FAILSAFE: {who} declared a run active ({what}) and has not checkpointed for "
            f"{mins} min, past its {int(grace // 60)} min grace. The seat may be down, "
            f"529'd, or stalled -- nothing has moved.")


# ---------------------------------------------------------------- the file half
def load(path: Any) -> Optional[Dict[str, Any]]:
    try:
        with open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _write(path: Any, doc: Dict[str, Any]) -> Dict[str, Any]:
    p = str(path)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    os.replace(tmp, p)                   # atomic on the same volume
    return doc


def declare(path: Any, *, who: str, what: str, grace_s: float = DEFAULT_GRACE_S,
            now: Optional[float] = None) -> Dict[str, Any]:
    """Open an expectation. From here until stand_down, silence is a finding."""
    now = float(now if now is not None else time.time())
    return _write(path, {"active": True, "declared_by": str(who), "what": str(what),
                         "declared_at": now, "checkpoint_at": now,
                         "grace_s": float(grace_s), "cooldown_s": DEFAULT_COOLDOWN_S})


def checkpoint(path: Any, *, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Say 'still here'. Cheap by design -- a heavy checkpoint would not get called."""
    doc = load(path)
    if not isinstance(doc, dict):
        return None
    doc["checkpoint_at"] = float(now if now is not None else time.time())
    return _write(path, doc)


def stand_down(path: Any, *, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Close the expectation. After this, silence is correct again."""
    doc = load(path)
    if not isinstance(doc, dict):
        return None
    doc["active"] = False
    doc["stood_down_at"] = float(now if now is not None else time.time())
    return _write(path, doc)


def mark_alarmed(path: Any, *, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    doc = load(path)
    if not isinstance(doc, dict):
        return None
    doc["last_alarm_at"] = float(now if now is not None else time.time())
    return _write(path, doc)
