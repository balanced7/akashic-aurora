"""
Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress,
not presence.

Semantic Relationship: FleetDoctor diagnoses AgentLiveness (read-model; page-graded)

The 2026-07-10 mail-loss forensics' core finding: every liveness surface truthfully
said "alive and idle" while an ask was dead -- presence proves the process, never the
work. L1 (worklive) records the phase; RB-27a's pulse records progress INSIDE it; this
module is the L2 reader that turns both into graded findings, under the three-reviewer
paging table (SRE ch.6, reconciled 2026-07-11):

  PAGE-GRADE (the ONLY two; every page urgent + actionable):
    hard_wedge        -- non-idle phase aged past threshold AND the pulse is dead: the
                         worker died inside a turn; not self-healing; act (revive).
    stalled_consumer  -- idle/online with unread backlog aged past HYSTERESIS: the
                         consumer stopped consuming. Hysteresis (first-seen must age)
                         because single-sample falses on every Redis blip.
  BANNER: frozen      -- a deliberate pause, with provenance + age. Config, not crisis.
  DASHBOARD: working  -- aged phase WITH a fresh pulse (F2 solved: long legit work);
             self_reported_error -- a trigger:<reason> confession (self-reported beats
                         inferred; the reason rides in the line);
             unhandled -- the P6 hours-scale count (mail loss itself is dashboard-only:
                         RB-26 auto-heals it; paging would duplicate the automation).

Healthy fleet renders ONE line. Every finding carries its drill-down command. Fixed,
named thresholds (no auto-threshold magic). Observe-only: acting (revive/redrive) stays
with the launcher and L4. Fail-open everywhere -- the doctor must never wedge a boot.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

from core.comm import liveness
from core.comm.timescale import scaled as _scaled

NS = "bifrost"
STALL_HYSTERESIS_S = _scaled(int(os.getenv("AKASHIC_STALL_HYSTERESIS_S", "180")), floor=1)
PAGE_DEDUP_TTL = _scaled(3600)          # one bus note per (agent, state) per hour
STALLED_SINCE_PREFIX = f"{NS}:stalled_since:"
PAGED_PREFIX = f"{NS}:doctor_paged:"


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("doctor")._client
    except Exception:
        return None


# ------------------------------------------------------------------ default probes
def _probe_backlog(agent: str) -> int:
    """Unread messages beyond the agent's shared cursor (inbox only -- direct asks)."""
    try:
        from core.comm.bus import Bus
        b = Bus(agent)
        if not b.online:
            return 0
        cur = b.cursor()["inbox"]
        entries = b._client.xrevrange(b._inbox_key(agent), count=50)
        def newer(sid):
            def parse(s):
                h, _, t = str(s).partition("-")
                try:
                    return (int(h), int(t or 0))
                except ValueError:
                    return (0, 0)
            return parse(sid) > parse(cur)
        return sum(1 for sid, _ in entries if newer(sid))
    except Exception:
        return 0


def _probe_stalled_since(agent: str, present: bool) -> Optional[float]:
    """Cross-invocation hysteresis: first-seen timestamp of the CURRENT stall, kept in
    a small key; cleared the moment the stall clears. Returns the first-seen epoch
    while stalled, else None."""
    c = _client()
    if c is None:
        return time.time() if present else None
    key = STALLED_SINCE_PREFIX + str(agent)
    try:
        if not present:
            c.delete(key)
            return None
        c.set(key, str(time.time()), nx=True, ex=int(STALL_HYSTERESIS_S * 20))
        raw = c.get(key)
        return float(raw) if raw else time.time()
    except Exception:
        return time.time()


def _probe_halted(agent: str) -> Optional[Dict[str, Any]]:
    try:
        from core.comm import control
        if control.is_halted(agent):
            return {"reason": getattr(control, "halt_reason", lambda a: "")(agent) or
                              "paused (provenance pending L5)", "age_s": None}
    except Exception:
        pass
    return None


def _default_probes() -> Dict[str, Any]:
    return {
        "worklive": liveness.read,
        "progress": liveness.progress_read,
        "backlog": _probe_backlog,
        "stalled_since": _probe_stalled_since,
        "halted": _probe_halted,
        "now": time.time(),
    }


# ------------------------------------------------------------------ examination
def examine(agent: str, *, probes: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """All findings for one agent, graded page|banner|dashboard. Never raises."""
    p = {**_default_probes(), **(probes or {})}
    now = p["now"]
    out: List[Dict[str, Any]] = []
    try:
        wl = p["worklive"](agent) or {}
        prog = p["progress"](agent)
        phase = str(wl.get("phase", ""))
        stuck = max(0.0, now - float(wl.get("since_ts", now))) if wl else 0.0
        pulse_fresh = bool(prog) and prog.get("age_s", 1e9) <= liveness.PROGRESS_TTL * 2 \
            and not str(prog.get("detail", "")).startswith("trigger:")

        if prog and str(prog.get("detail", "")).startswith("trigger:"):
            reason = str(prog["detail"])[len("trigger:"):]
            out.append(_f(agent, "self_reported_error", "dashboard",
                          f"{agent}: SELF-REPORTED failure -- {reason} "
                          f"(gen {prog.get('generation', '?')})",
                          f"py agent_cli.py events --search \"{agent} error\""))
        if phase.startswith("error:"):
            out.append(_f(agent, "self_reported_error", "dashboard",
                          f"{agent}: worklive error phase -- {phase[len('error:'):]}",
                          "py agent_cli.py doctor --json"))

        non_idle = bool(wl) and phase not in liveness.IDLE_PHASES \
            and not phase.startswith("error:")
        if non_idle and stuck >= liveness.DEFAULT_WEDGE_S:
            if pulse_fresh:
                out.append(_f(agent, "working", "dashboard",
                              f"{agent}: long work in '{phase}' ({int(stuck)}s) but the "
                              f"pulse is FRESH ({prog['age_s']}s: {prog.get('detail','')})"
                              " -- genuinely working, not wedged",
                              "py agent_cli.py doctor --json"))
            else:
                out.append(_f(agent, "hard_wedge", "page",
                              f"{agent}: HARD WEDGE -- '{phase}' for {int(stuck)}s with a "
                              "DEAD pulse (worker died inside the turn; not self-healing)",
                              f"py-spy dump --pid <runner-pid>  |  relaunch the runner"))

        backlog = int(p["backlog"](agent) or 0)
        idleish = (not wl) or phase in liveness.IDLE_PHASES
        if idleish and backlog > 0:
            first = p["stalled_since"](agent, True)
            age = max(0.0, now - first) if first else 0.0
            if age >= STALL_HYSTERESIS_S:
                out.append(_f(agent, "stalled_consumer", "page",
                              f"{agent}: STALLED CONSUMER -- {backlog} unread for "
                              f"{int(age)}s while idle (past hysteresis "
                              f"{int(STALL_HYSTERESIS_S)}s)",
                              f"py agent_cli.py bifrost-sync {agent}"))
            else:
                out.append(_f(agent, "stalled_consumer", "dashboard",
                              f"{agent}: backlog {backlog} while idle -- observing "
                              f"({int(age)}s / {int(STALL_HYSTERESIS_S)}s hysteresis)",
                              f"py agent_cli.py bifrost-sync {agent}"))
        else:
            p["stalled_since"](agent, False)     # clear the hysteresis clock

        frozen = p["halted"](agent)
        if frozen:
            age = frozen.get("age_s")
            out.append(_f(agent, "frozen", "banner",
                          f"{agent}: FROZEN -- {frozen.get('reason', 'paused')}"
                          + (f" ({int(age)}s)" if age else ""),
                          "py agent_cli.py bifrost-resume"))
    except Exception:
        pass
    return out


def _f(agent, state, grade, line, drill):
    return {"agent": agent, "state": state, "grade": grade, "line": line, "drill": drill}


def known_agents() -> List[str]:
    """Union of ids with a worklive record, a runner lock, or presence."""
    c = _client()
    ids = set()
    if c is not None:
        try:
            for pat, pre in ((f"{NS}:worklive:*", f"{NS}:worklive:"),
                             (f"{NS}:runner:*", f"{NS}:runner:"),
                             (f"{NS}:presence:*", f"{NS}:presence:")):
                for k in (c.keys(pat) or []):
                    ids.add(str(k)[len(pre):])
        except Exception:
            pass
    ids.discard("")
    return sorted(i for i in ids if not i.startswith(("t-", "drill-")))


def examine_fleet(agents: Optional[List[str]] = None, *,
                  probes: Optional[Dict[str, Any]] = None,
                  page_notes: bool = False) -> Dict[str, Any]:
    """The doctor's round: findings across the fleet + the one-line summary. With
    page_notes=True, page-grade findings emit ONE bus note per (agent, state) per
    PAGE_DEDUP_TTL -- the only two states that ever interrupt anyone."""
    agents = agents if agents is not None else known_agents()
    findings: List[Dict[str, Any]] = []
    for a in agents:
        findings.extend(examine(a, probes=probes))
    pages = [f for f in findings if f["grade"] == "page"]
    if not findings:
        summary = f"doctor: fleet healthy ({len(agents)} agent(s), 0 findings)"
    else:
        summary = (f"doctor: {len(pages)} page-grade, "
                   f"{sum(1 for f in findings if f['grade'] == 'banner')} banner, "
                   f"{sum(1 for f in findings if f['grade'] == 'dashboard')} dashboard "
                   f"across {len(agents)} agent(s)")
    try:
        from core.comm.control import format_pause_line, pause_status
        pause_line = format_pause_line(pause_status())
        if pause_line:
            summary = f"{pause_line}\n{summary}"   # RB-30: a frozen fleet outranks health counts
    except Exception:
        pass
    if page_notes and pages:
        _emit_pages(pages)
    return {"agents": agents, "findings": findings, "pages": pages, "summary": summary}


def _emit_pages(pages: List[Dict[str, Any]]) -> None:
    c = _client()
    try:
        from core.comm.bus import Bus
        bus = Bus("doctor")
    except Exception:
        return
    for f in pages:
        try:
            key = f"{PAGED_PREFIX}{f['agent']}:{f['state']}"
            if c is not None and not c.set(key, "1", nx=True, ex=PAGE_DEDUP_TTL):
                continue                    # already paged this hour
            bus.broadcast("note", f"[doctor] {f['line']}  drill: {f['drill']}",
                          meta={"via": "doctor", "display_only": True})
        except Exception:
            pass
