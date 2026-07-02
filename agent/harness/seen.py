"""Per-session anti-repeat state shared by every recall surface (Integration Tiers H0).

A lesson already surfaced THIS session must not be shown again -- not by the same hook,
and not by a different altitude (a lesson shown at plan time never re-injects at action
time, and vice versa). Hooks are fresh processes per call, so shown lesson-sources live
in one seen-file per session id, shared across every adapter and altitude.

State root honors AKASHIC_RECALL_STATE_DIR at import time (tests/conftest.py sets it
suite-wide before any import; keep in sync with core/recall/at_action.py).
"""
import os
import tempfile

_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_SEEN_DIR = os.path.join(_STATE_ROOT, "seen")


def seen_path(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:128]
    return os.path.join(_SEEN_DIR, (safe or "nosession") + ".txt")


def load_seen(session_id: str) -> set:
    if not session_id:
        return set()
    try:
        with open(seen_path(session_id), encoding="utf-8") as f:
            return {ln.strip() for ln in f if ln.strip()}
    except Exception:
        return set()


def mark_seen(session_id: str, sources) -> None:
    srcs = [s for s in (sources or []) if s]
    if not session_id or not srcs:
        return
    try:
        os.makedirs(_SEEN_DIR, exist_ok=True)
        with open(seen_path(session_id), "a", encoding="utf-8") as f:
            for s in srcs:
                f.write(s + "\n")
    except Exception:
        pass
