"""lane_depths -- the engine room's flow gauge source (T079-E2).

One pipeline-cheap call: {work, legacy, trace, sig} XLEN per agent. Missing
streams read 0 (a lane that never existed is empty, not an error); a hostile
backend reads all-zero (the engine room renders through its own outages).
The 562-storm of 2026-07-15 would have been a visible spike here.
"""
from __future__ import annotations

import os
from typing import Dict


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _client(c=None, allow_fallback: bool = True):
    if c is not None:
        return c
    if not allow_fallback:
        return None
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def lane_depths(agent: str, c=None, allow_fallback: bool = True) -> Dict[str, int]:
    ns = _ns()
    keys = {"work": f"{ns}:work:inbox:{agent}", "legacy": f"{ns}:inbox:{agent}",
            "trace": f"{ns}:trace", "sig": f"{ns}:sig"}
    out = {k: 0 for k in keys}
    cli = _client(c, allow_fallback)
    if cli is None:
        return out
    for name, key in keys.items():
        try:
            out[name] = int(cli.xlen(key))
        except Exception:
            out[name] = 0
    return out
