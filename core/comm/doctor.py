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

def _ns() -> str:
    # ns-isolation (2026-07-12): the doctor diagnoses agents WITHIN a namespace; its stall/page keys
    # (and its known_agents enumeration) must stay coherent with its scoped inputs (liveness,
    # runner_lock). Default "bifrost" preserved; per-call, not import-time.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


STALL_HYSTERESIS_S = _scaled(int(os.getenv("AKASHIC_STALL_HYSTERESIS_S", "180")), floor=1)
PAGE_DEDUP_TTL = _scaled(3600)          # one bus note per (agent, state) per hour


def _stalled_since_prefix() -> str:
    return f"{_ns()}:stalled_since:"


def _paged_prefix() -> str:
    return f"{_ns()}:doctor_paged:"
# Recency window for surfacing an inbox-bearing agent whose runner has DIED (lost its runner-lock +
# presence TTLs) but whose DURABLE inbox still holds undelivered work -- without resurrecting
# long-retired agents' stale inboxes. The 2026-07-12 gap: deepseek's runner died, its lock+presence
# TTL'd away, and it vanished from known_agents() while 7 unread asks sat in its inbox unwatched.
RECENT_INBOX_S = _scaled(int(os.getenv("AKASHIC_RECENT_INBOX_S", str(12 * 3600))), floor=1)


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
    key = _stalled_since_prefix() + str(agent)
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
        elif non_idle and stuck >= liveness.APPROACHING_WEDGE_S and not pulse_fresh:
            # P-S1-0: the sub-threshold window C1-8 hid in. Non-idle + dead pulse but not yet
            # past the page threshold -> DASHBOARD 'approaching wedge' (today: silence). Below
            # the page line because L0 self-heal may still land; visible so a mission face can
            # never render this window as "fleet healthy".
            out.append(_f(agent, "approaching_wedge", "dashboard",
                          f"{agent}: APPROACHING WEDGE -- '{phase}' for {int(stuck)}s with no "
                          f"fresh pulse (sub-threshold; pages at {int(liveness.DEFAULT_WEDGE_S)}s "
                          "if it doesn't self-heal)",
                          f"py agent_cli.py doctor --json   # py-spy dump --pid <{agent}-runner-pid> if it climbs"))

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

        # T077 A3: runner-down visibility from daemon presence card
        try:
            from core.comm.incarnation import daemon_runtimes
            rt = daemon_runtimes(agent)
            runner = rt.get("runner", "")
            if runner == "blocked":
                out.append(_f(agent, "runner_blocked", "page",
                              f"{agent}: RUNNER BLOCKED (circuit breaker tripped) — "
                              f"daemon holds presence, runner stopped. "
                              f"Restart the daemon to reset.",
                              f"py scripts/bifrost_daemon.py --agent {agent} --spawn-runner"))
            elif runner == "down":
                since = rt.get("since_s", "?")
                out.append(_f(agent, "runner_down", "banner",
                              f"{agent}: runner DOWN ({since}s) — daemon presence held, "
                              f"restart the daemon to respawn.",
                              f"py scripts/bifrost_daemon.py --agent {agent} --spawn-runner"))
        except Exception:
            pass
    except Exception:
        pass

    # T078 W1: token cost line from daily journal (meters before levers, R1)
    try:
        cl = _token_cost_line(agent)
        if cl is not None:
            out.append(cl)
    except Exception:
        pass

    return out


def _f(agent, state, grade, line, drill):
    return {"agent": agent, "state": state, "grade": grade, "line": line, "drill": drill}


def _token_cost_line(agent: str, journal_dir: str = "") -> Optional[Dict[str, Any]]:
    """Read today's token journal and render a dashboard-grade cost line. None when
    absent or zero-turn. T078 W1: the meter that every lever slice gets a receipt from."""
    import os as _os
    import json as _json
    import time as _time
    today = _time.strftime("%Y-%m-%d")
    base = journal_dir or _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
        "state")
    path = _os.path.join(base, f"runner_{agent}_{today}.json")
    try:
        if not _os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = _json.loads(f.read().strip() or "{}") or {}
        turns = int(data.get("turns", 0) or 0)
        if turns <= 0:
            return None
        prompt_t = int(data.get("prompt_tokens", 0) or 0)
        comp_t = int(data.get("completion_tokens", 0) or 0)
        total = prompt_t + comp_t
        cost = float(data.get("cost_est", 0) or 0)
        line = (f"{agent}: {turns} turn(s) · {_fmt_toks(total)} tokens "
                f"today · ~${cost:.2f} est")
        return _f(agent, "token_cost", "dashboard", line,
                  f"py agent_cli.py doctor --token {agent}")
    except Exception:
        return None


def _fmt_toks(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{round(n/1000)}k"
    return str(n)


# ------------------------------------------------------------------ services (T081-W3)
def _tcp_up(host: str, port: int, timeout: float = 0.4) -> bool:
    """Is something accepting connections at host:port? A fast, dependency-free liveness probe."""
    import socket
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _svc_finding(name: str, up: bool, detail: str, remedy: str) -> Dict[str, Any]:
    """A service finding in the shared finding shape: LIVE renders dashboard-grade w/ no drill;
    DOWN renders banner-grade carrying the one-line start command (never a page -- a down
    service is setup, not a work emergency)."""
    line = f"service {name}: {'LIVE' if up else 'DOWN'}" + (f" -- {detail}" if detail else "")
    return _f(name, f"service_{'live' if up else 'down'}",
              "dashboard" if up else "banner", line, "" if up else remedy)


def examine_services() -> List[Dict[str, Any]]:
    """T081-W3: fleet-INFRASTRUCTURE liveness -- the processes a seat needs but agent diagnosis
    (examine) never covers: the bus backend, the UI console, the presence daemon. Each LIVE/DOWN
    with a one-line start command for anything DOWN -- the 'what's running?' answer boot couldn't
    give (P2). Fail-open per probe: a probe that raises drops its own line, never the section."""
    out: List[Dict[str, Any]] = []
    try:   # 1) Redis -- the bus backend everything rides
        c = _client()
        up = False
        if c is not None:
            try:
                up = bool(c.ping())
            except Exception:
                up = False
        out.append(_svc_finding("redis", up, "bus backend",
                                "start Redis (config.py canonical: localhost:16379)"))
    except Exception:
        pass
    try:   # 2) UI console
        port = int(os.environ.get("BIFROST_UI_PORT", "8787"))
        out.append(_svc_finding(f"ui:{port}", _tcp_up("127.0.0.1", port), "bifrost console",
                                "py scripts/bifrost_ui.py  (Bash run_in_background)"))
    except Exception:
        pass
    try:   # 3) Presence daemon(s) -- the autopilot that owns wake/consume (T075/T077). DOWN means
           # the seat self-manages its arm/consume ritual (P3), so this line is load-bearing for a CLI seat.
        from core.comm.daemon_state import daemon_is_live
        live = []
        for a in known_agents():
            try:
                if daemon_is_live(a):
                    live.append(a)
            except Exception:
                pass
        out.append(_svc_finding("daemon", bool(live),
                                ", ".join(sorted(live)) if live
                                else "no live daemon -- seats self-manage wake/consume",
                                "py scripts/bifrost_daemon.py --agent <a>  (autopilot: owns wake+consume)"))
    except Exception:
        pass
    return out


def known_agents() -> List[str]:
    """Union of ids with a worklive record, a runner lock, presence, OR a durable inbox holding
    RECENT unconsumed mail. That last source is the fix for the 2026-07-12 gap: worklive/runner/
    presence are ALL TTL'd, so a dead-runner agent decays out of view within a minute even though its
    inbox (durable) still holds undelivered work -- and the stalled_consumer check never gets to
    examine it. Enumerating recent-inbox agents keeps a stuck/absent consumer visible; recency-gated
    (RECENT_INBOX_S) so long-retired agents' stale inboxes don't resurrect as findings."""
    c = _client()
    ids = set()
    if c is not None:
        try:
            for pat, pre in ((f"{_ns()}:worklive:*", f"{_ns()}:worklive:"),
                             (f"{_ns()}:runner:*", f"{_ns()}:runner:"),
                             (f"{_ns()}:presence:*", f"{_ns()}:presence:")):
                for k in (c.keys(pat) or []):
                    ids.add(str(k)[len(pre):])
            # durable-inbox agents whose NEWEST message is recent (survives runner death/presence TTL)
            ipre = f"{_ns()}:inbox:"
            cutoff_ms = (time.time() - RECENT_INBOX_S) * 1000
            for k in (c.keys(f"{_ns()}:inbox:*") or []):
                try:
                    last = c.xrevrange(str(k), count=1)      # newest entry, O(1)
                    if last and int(str(last[0][0]).split("-")[0]) >= cutoff_ms:
                        ids.add(str(k)[len(ipre):])
                except Exception:
                    pass
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
            key = f"{_paged_prefix()}{f['agent']}:{f['state']}"
            if c is not None and not c.set(key, "1", nx=True, ex=PAGE_DEDUP_TTL):
                continue                    # already paged this hour
            bus.broadcast("note", f"[doctor] {f['line']}  drill: {f['drill']}",
                          meta={"via": "doctor", "display_only": True})
        except Exception:
            pass
