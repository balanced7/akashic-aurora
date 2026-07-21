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


def work_backlog(agent: str, c=None, allow_fallback: bool = True, cap: int = 500) -> int:
    """The agent's TRUE pending depth on the work lane: entries beyond its LANE cursor.

    XLEN (lane_depths above) is STREAM LENGTH -- it never falls on consume, only on
    retention trim. Fed to a storm detector it is a permanently-flat supra-threshold
    line: the auto-clear fired on deepseek's first post-wiring boot (depth=289 = the
    stream's whole history) and would re-fire every window forever (live 2026-07-21).
    A storm gauge needs the CONSUMER-RELATIVE count, which falls as the runner drains
    -- exactly what K3's no-net-drain guard requires to mean anything.
    Bounded walk (cap): a storm gauge needs 'a lot vs a little', never an exact census."""
    cli = _client(c, allow_fallback)
    if cli is None:
        return 0
    try:
        from core.comm.bus import Bus
        cur = Bus(agent).read_lane_cursor().get("inbox", "0")

        def _p(s):
            h, _, t = str(s).partition("-")
            try:
                return (int(h), int(t or 0))
            except ValueError:
                return (0, 0)

        floor = _p(cur)
        entries = cli.xrevrange(f"{_ns()}:work:inbox:{agent}", count=int(cap))
        return sum(1 for sid, _ in entries if _p(sid) > floor)
    except Exception:
        return 0
