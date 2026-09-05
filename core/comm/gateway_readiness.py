"""Process-owned readiness generation for the Discord gateway.

Process presence is not service readiness.  The gateway writes this short-lived
record from Discord's asyncio loop, so a dead socket, a wedged loop, a process
replacement, or a process running in the wrong Aurora world cannot inherit a
healthy verdict from an old command line.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Iterable, Optional

from core.comm.liveness import WORKLIVE_TTL, _safe_code_sha


READINESS_TTL = int(WORKLIVE_TTL)


def _namespace(value: Optional[str] = None) -> str:
    return str(value or os.environ.get("BIFROST_NAMESPACE") or "bifrost")


def key(namespace: Optional[str] = None) -> str:
    return f"{_namespace(namespace)}:discord:gateway-readiness"


def make_record(
    *,
    pid: int,
    generation: str,
    ready: bool,
    world: str,
    detail: str = "",
    now: Optional[float] = None,
    code_sha: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "pid": int(pid),
        "generation": str(generation or ""),
        "ready": bool(ready),
        "world": str(world or ""),
        "beat_ts": round(time.time() if now is None else float(now), 3),
        "code_sha": str(_safe_code_sha() if code_sha is None else code_sha),
        "detail": str(detail or "")[:160],
    }


def publish(
    client,
    namespace: Optional[str] = None,
    *,
    pid: int,
    generation: str,
    ready: bool,
    world: str,
    detail: str = "",
    ttl: int = READINESS_TTL,
) -> Optional[dict[str, Any]]:
    """Write one bounded readiness generation; observability never wounds service."""
    record = make_record(
        pid=pid,
        generation=generation,
        ready=ready,
        world=world,
        detail=detail,
    )
    try:
        client.set(key(namespace), json.dumps(record), ex=max(1, int(ttl)))
        return record
    except Exception:                                                   # noqa: BLE001
        return None


def read(client=None, namespace: Optional[str] = None) -> Optional[dict[str, Any]]:
    try:
        if client is None:
            from core.comm.bus import get_bus

            client = get_bus("gateway-readiness")._client
        raw = client.get(key(namespace))
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        value = json.loads(raw) if raw else None
        return value if isinstance(value, dict) else None
    except Exception:                                                   # noqa: BLE001
        return None


def assess(
    record: Optional[dict[str, Any]],
    *,
    live_pids: Iterable[int],
    expected_world: str,
    now: Optional[float] = None,
    ttl: float = READINESS_TTL,
) -> dict[str, Any]:
    """Return a truthful health verdict for one observed process generation."""
    if not isinstance(record, dict):
        return {"healthy": False, "detail": "no process-owned readiness record"}
    try:
        pid = int(record.get("pid"))
    except (TypeError, ValueError):
        return {"healthy": False, "detail": "readiness pid is missing or invalid"}
    live = {int(value) for value in live_pids}
    if pid not in live:
        return {
            "healthy": False,
            "detail": f"readiness pid {pid} does not own the live gateway process",
        }
    generation = str(record.get("generation") or "")
    if not generation:
        return {"healthy": False, "detail": "readiness generation is missing"}
    world = str(record.get("world") or "")
    if world != str(expected_world):
        return {
            "healthy": False,
            "detail": f"readiness world {world or '<missing>'} != {expected_world}",
        }
    try:
        age = max(0.0, (time.time() if now is None else float(now)) - float(record["beat_ts"]))
    except (KeyError, TypeError, ValueError):
        return {"healthy": False, "detail": "readiness timestamp is missing or invalid"}
    if age > float(ttl):
        return {
            "healthy": False,
            "detail": f"readiness is stale ({age:.1f}s > {float(ttl):.1f}s)",
            "age_s": round(age, 3),
        }
    if record.get("ready") is not True:
        detail = str(record.get("detail") or "Discord socket is not ready")
        return {
            "healthy": False,
            "detail": f"Discord is not ready: {detail}",
            "age_s": round(age, 3),
        }
    return {
        "healthy": True,
        "detail": (
            f"Discord ready: pid {pid}, generation {generation}, world {world}, "
            f"beat {age:.1f}s"
        ),
        "age_s": round(age, 3),
        "pid": pid,
        "generation": generation,
        "world": world,
        "code_sha": str(record.get("code_sha") or ""),
    }
