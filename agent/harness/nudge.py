"""JIT learn-nudge rate limiting shared by every harness adapter (friction audit D5).

A FAIL->SUCCESS flip is the moment a lesson was just earned, so THAT is when the nudge
fires (core/recall/at_action.build_learn_nudge supplies the text) -- but a nudge that
repeats is noise, and hooks are fresh processes per call, so the three-way rate limit
(the hook-discipline lesson) lives in a per-session state file:
  once per target per session · per-session cap AKASHIC_LEARN_NUDGE_CAP (default 3) ·
  kill switch AKASHIC_LEARN_NUDGE=0.
Callers own their directory (they all pass <state root>/nudge; session keys differ per
harness, so sharing the directory is safe).
"""
import json
import os


def _safe(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


def _state_path(nudge_dir: str, session_id: str) -> str:
    return os.path.join(nudge_dir, _safe(session_id) + ".json")


def nudge_allowed(nudge_dir: str, session_id: str, target: str) -> bool:
    if os.getenv("AKASHIC_LEARN_NUDGE", "1") == "0":
        return False
    try:
        cap = int(os.getenv("AKASHIC_LEARN_NUDGE_CAP", "3"))
    except Exception:
        cap = 3
    try:
        with open(_state_path(nudge_dir, session_id), encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        st = {}
    return target not in st.get("targets", []) and len(st.get("targets", [])) < cap


def mark_nudged(nudge_dir: str, session_id: str, target: str) -> None:
    try:
        os.makedirs(nudge_dir, exist_ok=True)
        p = _state_path(nudge_dir, session_id)
        try:
            with open(p, encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            st = {}
        st.setdefault("targets", []).append(target)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass
