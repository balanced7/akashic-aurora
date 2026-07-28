"""
Fleet doctor (L2 / RB-27b) -- the missing READER of the liveness signals: progress,
not presence.

Semantic Relationship: FleetDoctor diagnoses AgentLiveness (read-model; page-graded)

The 2026-07-10 mail-loss forensics' core finding: every liveness surface truthfully
said "alive and idle" while an ask was dead -- presence proves the process, never the
work. L1 (worklive) records the phase; RB-27a's pulse records progress INSIDE it; this
module is the L2 reader that turns both into graded findings, under the three-reviewer
paging table (SRE ch.6, reconciled 2026-07-11):

  PAGE-GRADE (every page urgent + actionable):
    hard_wedge        -- non-idle phase aged past threshold AND the pulse is dead: the
                         worker died inside a turn; not self-healing; act (revive).
    stalled_consumer  -- idle/online with unread backlog aged past HYSTERESIS: the
                         consumer stopped consuming. Hysteresis (first-seen must age)
                         because single-sample falses on every Redis blip.
    lane_stall        -- work on the lane has WAITED past LANE_STALL_PAGE_S. The third
                         page state, added 2026-07-26 on a receipt: kimi's lane sat 45h
                         at depth 55 while every other signal read healthy, because the
                         seat was alive and looping -- so the two states above (both of
                         which need an idle phase or a dead pulse) could not see it.
                         This one is deliberately BLIND to the pulse: presence proves
                         the process, and this module exists to say it never proves
                         the work. Graded on BACKLOG age, never cursor age -- a quiet
                         agent's cursor is ancient because no mail arrived.
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
PAGE_DEDUP_TTL = _scaled(3600)          # one emission per (channel, agent, state) per hour

# Progress-age thresholds (2026-07-26). deepseek's line on the kimi post-mortem was
# "if lane_cursor_age > 6h: escalate" -- 6h kept, measured against the age of the OLDEST
# UNCONSUMED entry rather than the cursor (the cursor reading pages every returning seat).
# The warn band exists so the window is never silent on its way to a page.
# Literal seconds, not 6*3600: the physics sheet scrapes these defaults verbatim and
# renders an arithmetic expression as a truncated fragment.
LANE_STALL_PAGE_S = _scaled(int(os.getenv("AKASHIC_LANE_STALL_PAGE_S", "21600")), floor=1)   # 6h
LANE_STALL_WARN_S = _scaled(int(os.getenv("AKASHIC_LANE_STALL_WARN_S", "3600")), floor=1)    # 1h


def _stalled_since_prefix() -> str:
    return f"{_ns()}:stalled_since:"


def _paged_prefix() -> str:
    return f"{_ns()}:doctor_paged:"


def _escalated_prefix() -> str:
    # A SEPARATE dedup namespace from _paged_prefix: the pager and the bus note are two
    # channels, and one must never consume the other's slot for the hour.
    return f"{_ns()}:doctor_escalated:"


def _sid(s) -> tuple:
    """Parse a stream id into a comparable (ms, seq)."""
    h, _, t = str(s).partition("-")
    try:
        return (int(h), int(t or 0))
    except ValueError:
        return (0, 0)


def _fmt_age(s: float) -> str:
    n = int(max(0.0, float(s)))
    if n >= 3600:
        return f"{n // 3600}h{(n % 3600) // 60:02d}m"
    return f"{n // 60}m" if n >= 60 else f"{n}s"
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
    """Unread messages beyond the agent's EFFECTIVE cursor (inbox only -- direct asks).
    W43: effective = max(shared, lane shadow) -- a lane-mode consumer's drained mail no
    longer pages as a stalled backlog (kimi's live receipt: doctor paged a drained seat)."""
    try:
        from core.comm.bus import Bus
        b = Bus(agent)
        if not b.online:
            return 0
        cur = b.effective_cursor()["inbox"]
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


def _probe_lane_health(agent: str) -> Optional[Dict[str, Any]]:
    """W16 (deepseek, 2026-07-21): per-agent lane cursor health -- age, depth, straggler
    count. Uses W43 effective_cursor() as the building block. Returns None when the agent
    has no lane cursor (legacy-only consumer) or Redis is down. The three gauges answer
    'how far behind is this consumer's work cursor?' -- the question doctor couldn't ask
    before (claude's work cursor was a full day behind; mailbox --explain surfaced it but
    doctor didn't page it)."""
    try:
        from core.comm.bus import Bus
        from core.comm.lane_depths import work_backlog
        b = Bus(agent)
        if not b.online:
            return None
        lane = b.read_lane_cursor()
        inbox_pos = lane.get("inbox", "0")
        shadow_pos = lane.get("shadow_inbox", "0")

        def _ts(sid) -> float:
            h, _, _ = str(sid).partition("-")
            try:
                return int(h) / 1000.0
            except (ValueError, OverflowError):
                return 0.0

        inbox_ts = _ts(inbox_pos)
        age_s = max(0.0, time.time() - inbox_ts) if inbox_ts > 0 else None

        depth = work_backlog(agent, c=b._client)

        # PROGRESS AGE: how long the OLDEST UNCONSUMED entry has waited. age_s above is
        # the cursor's own timestamp, which is ancient for any agent that simply had no
        # mail -- grading on it pages every returning seat. This is the stall signal.
        # O(1): XRANGE from the cursor, count=2 (the cursor's own entry may or may not
        # still exist, so skip anything at or below it).
        backlog_age_s = None
        if depth > 0:
            try:
                floor = _sid(inbox_pos)
                for sid, _fields in b._client.xrange(f"{b.ns}:work:inbox:{agent}",
                                                     min=str(inbox_pos), count=2):
                    if _sid(sid) > floor:
                        backlog_age_s = max(0.0, time.time() - _ts(sid))
                        break
            except Exception:
                backlog_age_s = None

        # Straggler: legacy-stream messages between the shadow and the effective cursor
        straggler = 0
        try:
            eff = b.effective_cursor()["inbox"]
            shadow, _, _ = str(shadow_pos).partition("-")
            eff_ms, _, _ = str(eff).partition("-")
            if int(shadow or 0) < int(eff_ms or 0):
                entries = b._client.xrevrange(b._inbox_key(agent), count=200)
                def _p(s):
                    h, _, t = str(s).partition("-")
                    try:
                        return (int(h), int(t or 0))
                    except ValueError:
                        return (0, 0)
                sf, ef = _p(shadow_pos), _p(eff)
                straggler = sum(1 for sid, _ in entries if sf < _p(sid) <= ef)
        except Exception:
            pass

        is_lane = any(v != "0" for v in lane.values())
        if not is_lane:
            return None
        return {"age_s": age_s, "depth": depth, "straggler": straggler,
                "backlog_age_s": backlog_age_s}
    except Exception:
        return None


def _present_no_worklive(agent: str) -> bool:
    """W40 fence-fix: is the agent present by a signal OTHER than worklive? A runner lock
    OR a wake-seat file (the interactive seat's liveness -- claude has no runner but an
    armed watcher). Fail-SAFE toward present: a stale seat file (bounded by the W42 janitor)
    only under-reports a GONE agent, never falsely declares a LIVE seat gone. Never raises."""
    try:
        from core.comm import runner_lock
        if runner_lock.holder(str(agent)):
            return True
    except Exception:
        pass
    try:
        from core.comm import wake_seat
        for _path, _sid in wake_seat.iter_seats(str(agent)):
            return True                       # any seat file present -> a live/recent seat
    except Exception:
        pass
    return False


def _probe_halted(agent: str) -> Optional[Dict[str, Any]]:
    try:
        from core.comm import control
        if control.is_halted(agent):
            return {"reason": getattr(control, "halt_reason", lambda a: "")(agent) or
                              "paused (provenance pending L5)", "age_s": None}
    except Exception:
        pass
    return None


def _probe_bench_count(agent: str) -> int:
    try:
        from core.comm import triage_park
        return int(triage_park.count(agent) or 0)
    except Exception:
        return 0


def _default_probes() -> Dict[str, Any]:
    # EVERY ambient reader goes through this seam. token_cost and bench_count used to
    # reach past it straight to the filesystem, which made "healthy fleet = zero
    # findings" fail on any day a runner had logged turns -- a pin that is red for
    # reasons the test cannot control teaches the fleet to skip doctor reds, and this
    # module now carries page-grade pins that nobody can afford to skip (W69).
    return {
        "worklive": liveness.read,
        "progress": liveness.progress_read,
        "backlog": _probe_backlog,
        "stalled_since": _probe_stalled_since,
        "halted": _probe_halted,
        "lane_health": _probe_lane_health,
        "token_cost": _token_cost_line,
        "bench_count": _probe_bench_count,
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

        # S2 fix (self-demonstrated 2026-07-28: this doctor paged the live seat that was
        # building and committing at that moment). `stuck` measures PHASE AGE -- since_ts is
        # deliberately never refreshed by a beat, so a healthy seat holding one phase looks
        # arbitrarily stuck. And the RB-27a progress pulse is a RUNNER organ: a live SEAT
        # never writes one, so pulse_fresh is False for seats BY CONSTRUCTION. Non-idle +
        # old phase + no runner pulse therefore paged every healthy seat, forever.
        # A FRESH WORKLIVE BEAT IS LIVENESS EVIDENCE IN ITS OWN RIGHT (S2 roster: LIVE is
        # proven by beat freshness). Demanding a runner-only organ from a non-runner is the
        # category error, and a false page trains the fleet to ignore the real one.
        # Window: the roster's own freshness law (cadence-derived, WORKLIVE_FRESH_S floor)
        # rather than PROGRESS_TTL, which is a runner-tick constant far below seat cadence.
        # Pins: tests/test_doctor_wedge_vs_beat.py
        # SOL'S NO-GO ON THE FIRST VERSION, and it is the load-bearing distinction:
        # a RUNNER's heartbeat runs on its OWN THREAD -- py-spy caught this live, deepseek's
        # MainThread blocked in streams.py flush while 'Thread-3 (_heartbeat)' kept beating.
        # For a runner the beat proves PROCESS liveness, never WORK progress, so counting it
        # would mask the real wedge forever (v1 of this fix did exactly that).
        # Only a SEAT may retract a page with its beat: a seat is per-incarnation
        # (agent#sid8), single-threaded per turn, and writes its worklive from the turn
        # itself (roster.heartbeat on sync/boot) -- so its beat IS work evidence. For a bare
        # agent id the PROGRESS PULSE governs, unchanged.
        is_seat = "#" in str(agent)
        beat_ts = float(wl.get("beat_ts") or 0) if wl else 0.0
        try:
            from core.comm.roster import FRESH_S as _SEAT_FRESH_S
        except Exception:
            _SEAT_FRESH_S = 45.0
        beat_fresh = is_seat and bool(beat_ts) and \
            (now - beat_ts) <= max(_SEAT_FRESH_S, liveness.PROGRESS_TTL * 2)
        alive_signal = pulse_fresh or beat_fresh

        non_idle = bool(wl) and phase not in liveness.IDLE_PHASES \
            and not phase.startswith("error:")
        if non_idle and stuck >= liveness.DEFAULT_WEDGE_S:
            if alive_signal:
                evidence = (f"pulse is FRESH ({prog['age_s']}s: {prog.get('detail','')})"
                            if pulse_fresh else
                            f"worklive BEAT is fresh ({int(now - beat_ts)}s ago)")
                out.append(_f(agent, "working", "dashboard",
                              f"{agent}: long work in '{phase}' ({int(stuck)}s) but the "
                              f"{evidence} -- genuinely working, not wedged",
                              "py agent_cli.py doctor --json"))
            else:
                out.append(_f(agent, "hard_wedge", "page",
                              f"{agent}: HARD WEDGE -- '{phase}' for {int(stuck)}s with a "
                              "DEAD pulse (worker died inside the turn; not self-healing)",
                              f"py-spy dump --pid <runner-pid>  |  relaunch the runner"))
        elif non_idle and stuck >= liveness.APPROACHING_WEDGE_S and not alive_signal:
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
            if not wl:
                # W40 (deepseek 2026-07-21) + claude fence-fix: 'no worklive' is a RUNNER
                # signal only. Before declaring an agent GONE, check the OTHER presence
                # signals -- a runner lock or a live wake seat. An interactive seat
                # (claude) has NO worklive/runner yet IS alive via its armed watcher; the
                # unfixed code marked it 'GONE' (false negative on the live operator seat).
                if _present_no_worklive(agent):
                    # present but not runner-active: an interactive/wake-armed seat with a
                    # little mail -- benign, it consumes on its next turn/wake. Dashboard,
                    # never a page, never 'GONE'.
                    out.append(_f(agent, "idle_backlog", "dashboard",
                                  f"{agent}: {backlog} unread -- live seat (wake-armed / "
                                  f"lock-held), no runner phase; consumes on next turn/wake",
                                  f"py agent_cli.py bifrost-sync {agent}"))
                else:
                    # ABSENT: no worklive, no runner, no wake seat. Ghost mail from a
                    # retired/dead seat -- dashboard-visible (graveyard-is-a-resource) but
                    # NEVER a page. Live receipt: census (a retired one-off task-agent).
                    out.append(_f(agent, "offline_backlog", "dashboard",
                                  f"{agent}: OFFLINE — {backlog} unread but the agent is "
                                  f"GONE (no worklive, no runner, no wake seat). The backlog "
                                  f"is ghost mail from a retired seat — retire the inbox or "
                                  f"ignore.",
                                  # T115: this used to advertise a `retire` verb that
                                  # has never existed -- an operator following
                                  # the doctor's own advice got an argparse error and no way
                                  # to act on a finding the doctor deliberately raised.
                                  # skip-to-now IS "retire the inbox": it advances the
                                  # cursors past ghost mail, with an audited reason.
                                  f"py agent_cli.py bifrost-skip-to-now {agent} --by <you> "
                                  f"--reason 'ghost mail from a retired seat'  | or ignore: "
                                  f"the mail TTLs with the stream"))
                p["stalled_since"](agent, False)
            else:
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
        cl = p["token_cost"](agent)
        if cl is not None:
            out.append(cl)
    except Exception:
        pass

    # W16 (deepseek, 2026-07-21): lane-cursor health -- age, depth, straggler
    try:
        lh = p["lane_health"](agent)
        if lh is not None:
            # PROGRESS AGE (2026-07-26, the kimi receipt). W16 computed these numbers and
            # filed them dashboard-grade whatever they said; 45h at depth 55 rendered
            # beside routine token spend. Undrained work that has WAITED past the
            # threshold pages -- and it pages with no reference to the pulse or the
            # phase, because kimi's pulse was FRESH the whole time. The 'working' row
            # above and this one are both true: alive, and not moving the work.
            waited = lh.get("backlog_age_s")
            depth = int(lh.get("depth") or 0)
            if depth > 0 and waited is not None and waited >= LANE_STALL_WARN_S:
                paging = waited >= LANE_STALL_PAGE_S
                head = "LANE STALL -- " if paging else "lane slowing -- "
                tail = "" if paging else f" (pages at {_fmt_age(LANE_STALL_PAGE_S)})"
                out.append(_f(agent, "lane_stall", "page" if paging else "dashboard",
                              f"{agent}: {head}{depth} message(s) undrained on the work "
                              f"lane, oldest waiting {_fmt_age(waited)}{tail}",
                              f"py agent_cli.py unwedge {agent}"))
            parts = [f"{agent}: lane cursor"]
            if lh["age_s"] is not None:
                parts.append(f"age {int(lh['age_s'])}s")
            if lh["depth"]:
                parts.append(f"depth {lh['depth']}")
            if lh["straggler"]:
                parts.append(f"stragglers {lh['straggler']}")
            lh_line = " -- ".join(parts)
            out.append(_f(agent, "lane_health", "dashboard",
                          lh_line if len(parts) > 1 else lh_line + " healthy",
                          f"py agent_cli.py mailbox --explain {agent}"))
    except Exception:
        pass

    # TWIN SESSIONS ON ONE AGENT ID (2026-07-28 incident). Two live sessions share a cursor:
    # exactly one may consume, and the seat goes to whoever refreshed most recently. A retiring
    # session still takes turns -- re-arm demands, task notifications, one more question -- and
    # every turn renews its claim, so it out-competes its successor purely by still breathing.
    # The successor is refused and SILENTLY degraded to peek, which is why this went unnoticed
    # until the operator saw mail vanishing. Dashboard, not a page: twins are legitimate (the
    # twin-split protocol), and it is the UNANNOUNCED overlap that costs.
    try:
        from core.comm import wake_seat
        seats = [sid for _p, sid in wake_seat.iter_seats(agent)]
        if len(seats) > 1:
            held = ""
            try:
                from core.comm import runner_lock as _rl
                h = (_rl.holder(agent) or {}).get("token", "")
                held = h[len("session:"):] if h.startswith("session:") else h
            except Exception:
                pass
            who = ", ".join(s[:8] for s in seats)
            out.append(_f(agent, "twin_sessions", "dashboard",
                          f"{agent}: {len(seats)} LIVE SESSIONS share this agent id ({who}) -- "
                          f"one cursor, one consumer seat"
                          + (f"; held by {held[:8]}" if held else "; seat unheld")
                          + ". The other is being degraded to peek and may be losing mail.",
                          f"retiring seat: py agent_cli.py stand-down {agent}"))
    except Exception:
        pass

    # S0-alpha: the triage bench (scry-to-bottom) -- parked asks are VISIBLE, never limbo.
    try:
        n = int(p["bench_count"](agent) or 0)
        if n > 0:
            out.append(_f(agent, "triage_bench", "dashboard",
                          f"{agent}: {n} ask(s) on the triage bench (bottomed, not dropped)",
                          f"py agent_cli.py bench {agent}"))
    except Exception:
        pass

    return out


def _f(agent, state, grade, line, drill):
    return {"agent": agent, "state": state, "grade": grade, "line": line, "drill": drill}


def unwedge(agent: str) -> Dict[str, Any]:
    """W31 (deepseek, why-am-i-wedged, 2026-07-21): one-verb diagnostic — synthesize all
    doctor findings + lane health + lane depths + runner presence into ONE verdict and
    recommendation. READ-ONLY (v1 — acting is v2 behind a flag). The answer to 'why is
    this agent stuck?' that replaces 3+ manual tool calls. Returns {'agent', 'status',
    'verdict', 'recommendation', 'evidence'}."""
    evidence: Dict[str, Any] = {"findings": [], "lane_health": None, "lane_depths": {},
                                "runner_status": "unknown", "locks": []}
    # 1) Doctor findings (the full examine)
    try:
        evidence["findings"] = examine(agent)
    except Exception:
        pass
    # 2) Lane health (W16 — age, depth, straggler)
    try:
        evidence["lane_health"] = _probe_lane_health(agent)
    except Exception:
        pass
    # 3) Lane depths (work, legacy, trace, sig XLEN + work backlog)
    try:
        from core.comm.lane_depths import lane_depths, work_backlog
        evidence["lane_depths"] = {
            **lane_depths(agent),
            "work_backlog": work_backlog(agent),
        }
    except Exception:
        pass
    # 4) Runner status
    try:
        from core.comm.runner_lock import holder
        from core.comm.incarnation import daemon_runtimes
        h = holder(agent) or {}
        rt = daemon_runtimes(agent)
        runner = rt.get("runner", "")
        if runner == "blocked":
            evidence["runner_status"] = "blocked"
        elif runner == "down":
            evidence["runner_status"] = "down"
        elif h.get("token"):
            evidence["runner_status"] = "live"
        else:
            evidence["runner_status"] = "absent"
    except Exception:
        pass
    # 5) Locks held
    try:
        from core.comm import locks
        lm = locks.LockManager(agent)
        held = lm.list_held() if hasattr(lm, "list_held") else []
        evidence["locks"] = held[:20]
    except Exception:
        pass

    # --- SYNTHESIZE ---
    pages = [f for f in evidence["findings"] if f.get("grade") == "page"]
    banners = [f for f in evidence["findings"] if f.get("grade") == "banner"]
    lh = evidence["lane_health"] or {}
    depths = evidence["lane_depths"]
    runner = evidence["runner_status"]
    frozen = any(f["state"] == "frozen" for f in evidence["findings"])
    hard_wedge = any(f["state"] == "hard_wedge" for f in pages)
    stalled = any(f["state"] == "stalled_consumer" for f in pages)
    lane_stall = any(f["state"] == "lane_stall" for f in pages)

    if frozen:
        status, verdict, rec = "frozen", (
            f"{agent}: FROZEN — deliberately paused/halted. No action required unless "
            "this is stale."), "resume: py agent_cli.py bifrost-resume"
    elif hard_wedge:
        status, verdict, rec = "wedged", (
            f"{agent}: HARD WEDGE — died inside a turn, not self-healing. Revive."), (
            "relaunch the runner; check py-spy dump on the old pid for root cause")
    elif stalled and lh.get("depth", 0) > 0:
        age = int(lh.get("age_s", 0) or 0)
        status, verdict, rec = "stalled", (
            f"{agent}: STALLED — {lh['depth']} unprocessed on the work lane "
            f"(lane cursor {age}s behind)" + (f", {len(evidence['locks'])} lock(s) held"
            if evidence["locks"] else "")), (
            f"triaged drain: py scripts/mirror.py skip-to-now {agent} "
            f"| or drill down: py agent_cli.py mailbox --explain {agent}")
    elif stalled:
        status, verdict, rec = "stalled", (
            f"{agent}: STALLED CONSUMER — backlog present but lane cursor current; "
            "legacy mail may have accumulated"), (
            f"sync: py agent_cli.py bifrost-sync {agent}")
    elif lane_stall:
        # Ranked ABOVE the runner and BUSY branches deliberately. This branch did not
        # exist and the ladder fell through to BUSY ("working, not wedged") on a live
        # runner with a fresh pulse -- printing that verdict directly above the
        # page-grade lane_stall in its own evidence. A drill-down that argues against
        # the page it was sent to explain is worse than no drill-down: it is the
        # kimi mistake (presence read as progress) inside the tool built to catch it.
        waited = int((lh.get("backlog_age_s") or 0))
        status, verdict, rec = "stalled", (
            f"{agent}: LANE STALL — {lh.get('depth', '?')} message(s) undrained, oldest "
            f"waiting {_fmt_age(waited)}. The runner may be alive and looping; the WORK "
            "is not moving."), (
            # Measured 2026-07-26 on claude's own stalled lane (22 -> 2 -> 0): the D2
            # stale-ask gate parks in BATCHES, so one pass rarely finishes. Saying so
            # keeps a half-drained lane from reading as a failed recommendation.
            f"drain (repeat until depth 0): BIFROST_CONSUME_LANE=work py agent_cli.py "
            f"bifrost-sync {agent} --consume  | if it will not drain: py scripts/mirror.py "
            f"skip-to-now {agent}  | inspect: py agent_cli.py mailbox --explain {agent}")
    elif runner == "down":
        status, verdict, rec = "down", (
            f"{agent}: runner DOWN — daemon holds presence but no live runner"), (
            f"restart daemon: py scripts/bifrost_daemon.py --agent {agent} --spawn-runner")
    elif runner == "blocked":
        status, verdict, rec = "down", (
            f"{agent}: RUNNER BLOCKED — circuit breaker tripped"), (
            f"restart daemon to reset: py scripts/bifrost_daemon.py --agent {agent} --spawn-runner")
    elif runner == "absent":
        status, verdict, rec = "down", (
            f"{agent}: no runner process found (no live lock, no presence)"), (
            f"start: py scripts/bifrost_runner_deepseek.py --agent {agent} --agentic")
    elif lh.get("depth", 0) > 10:
        status, verdict, rec = "backlogged", (
            f"{agent}: BUSY — {lh['depth']} on the work lane but pulse is fresh. "
            "Working, not wedged."), "monitor: py agent_cli.py doctor"
    elif lh.get("straggler", 0) > 0:
        status, verdict, rec = "healthy", (
            f"{agent}: HEALTHY — {lh.get('straggler', 0)} straggler(s) on legacy stream "
            "(dual-write soak, self-clears)"), "monitor: py agent_cli.py doctor"
    elif runner == "live":
        status, verdict, rec = "healthy", (
            f"{agent}: HEALTHY — runner live, lane current, no page-grade findings"), (
            "no action needed: py agent_cli.py doctor")
    else:
        status, verdict, rec = "healthy", (
            f"{agent}: HEALTHY — no runner, no backlog, no findings"), (
            "no action needed")

    return {"agent": agent, "status": status, "verdict": verdict,
            "recommendation": rec, "evidence": evidence}


def format_unwedge(r: Dict[str, Any], json_mode: bool = False) -> str:
    """Render unwedge result as a compact text report with evidence drill-downs."""
    if json_mode:
        import json as _json
        return _json.dumps({k: r[k] for k in ("agent", "status", "verdict",
                              "recommendation", "evidence")}, indent=2, default=str)
    lines = [f"{r['verdict']}", f"  recommendation: {r['recommendation']}"]
    ev = r.get("evidence") or {}
    pages = [f for f in ev.get("findings", []) if f.get("grade") == "page"]
    if pages:
        lines.append("  page-grade findings:")
        for p in pages:
            lines.append(f"    [{p['state']}] {p['line']}")
            if p.get("drill"):
                lines.append(f"      drill: {p['drill']}")
    lh = ev.get("lane_health") or {}
    if lh:
        parts = []
        if lh.get("age_s") is not None:
            parts.append(f"age {int(lh['age_s'])}s")
        if lh.get("depth"):
            parts.append(f"depth {lh['depth']}")
        if lh.get("straggler"):
            parts.append(f"stragglers {lh['straggler']}")
        if parts:
            lines.append(f"  lane cursor: {', '.join(parts)}")
    depths = ev.get("lane_depths") or {}
    if depths:
        dp = [f"{k}={v}" for k, v in sorted(depths.items()) if v]
        if dp:
            lines.append(f"  lane depths: {', '.join(dp)}")
    if ev.get("locks"):
        lines.append(f"  held locks ({len(ev['locks'])}): "
                     f"{', '.join(str(l) for l in ev['locks'][:5])}")
    lines.append(f"  runner: {ev.get('runner_status', 'unknown')}")
    return "\n".join(lines)


def pulse(agents: Optional[List[str]] = None) -> Dict[str, Any]:
    """W25 pulse (deepseek, LIFEWORKERS, 2026-07-21): the pressure-map companion to
    vitals. Reads work_backlog for every known agent (or the named list), classifies
    each into a pressure zone, and returns a fleet-level summary. READ-only v1.
    Zones: critical (>=50, storm territory) / elevated (>=10, building) / normal
    (healthy flow) / absent (no lane cursor, legacy-only agent)."""
    if agents is None:
        try:
            agents = known_agents()
        except Exception:
            agents = []
    zones: Dict[str, List[str]] = {"critical": [], "elevated": [], "normal": [],
                                     "absent": []}
    readings: Dict[str, Dict[str, Any]] = {}
    try:
        from core.comm.lane_depths import work_backlog
        from core.comm.bus import Bus
        for a in agents:
            try:
                lane = Bus(a).read_lane_cursor()
                has_lane = any(v != "0" for v in lane.values())
                if not has_lane:
                    zones["absent"].append(a)
                    readings[a] = {"backlog": 0, "zone": "absent", "has_lane": False}
                    continue
                depth = work_backlog(a)
                readings[a] = {"backlog": depth, "has_lane": True}
                if depth >= 50:
                    zones["critical"].append(a)
                    readings[a]["zone"] = "critical"
                elif depth >= 10:
                    zones["elevated"].append(a)
                    readings[a]["zone"] = "elevated"
                else:
                    zones["normal"].append(a)
                    readings[a]["zone"] = "normal"
            except Exception:
                zones["absent"].append(a)
                readings[a] = {"backlog": 0, "zone": "absent", "has_lane": False}
    except Exception:
        pass
    critical_n = len(zones["critical"])
    elevated_n = len(zones["elevated"])
    normal_n = len(zones["normal"])
    absent_n = len(zones["absent"])
    if critical_n:
        summary = (f"pulse: {critical_n} CRITICAL ({', '.join(zones['critical'])})"
                   + (f", {elevated_n} elevated" if elevated_n else "")
                   + f" — storm territory; pressure is building")
    elif elevated_n:
        summary = (f"pulse: {elevated_n} elevated ({', '.join(zones['elevated'])}), "
                   f"{normal_n} normal — watch the elevated lanes")
    elif absent_n == len(agents):
        summary = f"pulse: no lane-mode agents ({len(agents)} agent(s), all legacy)"
    else:
        summary = f"pulse: fleet pressure normal ({normal_n} agent(s) healthy"
        if absent_n:
            summary += f", {absent_n} legacy"
        summary += ")"
    return {"agents": agents, "zones": zones, "readings": readings, "summary": summary}


def format_pulse(p: Dict[str, Any], json_mode: bool = False) -> str:
    """Render pulse result as a compact pressure map."""
    if json_mode:
        import json as _json
        return _json.dumps({k: p[k] for k in ("agents", "zones", "readings", "summary")},
                           indent=2, default=str)
    lines = [p["summary"]]
    for zone, ids in p["zones"].items():
        if ids:
            agent_lines = []
            for a in ids:
                r = p["readings"].get(a, {})
                bl = r.get("backlog", "?")
                agent_lines.append(f"{a} (backlog={bl})")
            lines.append(f"  {zone}: {', '.join(agent_lines)}")
    return "\n".join(lines)


def flightdeck(agent: Optional[str] = None, *, commit_hours: float = 6.0) -> Dict[str, Any]:
    """W25 flightdeck (deepseek, LIFEWORKERS, 2026-07-21): the cockpit one-pager —
    compose doctor + pulse + unwedge + lane-health + locks + recent commits into one
    fleet-at-a-glance view. READ-only v1. No --agent: fleet-wide compact lines. With
    --agent: full detail for one seat.

    The composition law: flightdeck REUSES existing data sources (examine_fleet, pulse,
    unwedge, _probe_lane_health) — it derives nothing new; it ARRANGES what already
    exists into one glance."""
    out: Dict[str, Any] = {"fleet": True, "agents": [], "sections": {}}
    # 1) Doctor — the whole fleet
    try:
        dr = examine_fleet()
        out["sections"]["doctor"] = {
            "summary": dr["summary"], "pages": len(dr.get("pages", [])),
            "banners": sum(1 for f in dr.get("findings", []) if f["grade"] == "banner"),
            "dashboard": sum(1 for f in dr.get("findings", []) if f["grade"] == "dashboard"),
        }
        # per-agent compact rows
        for a in dr.get("agents", []):
            af = [f for f in dr.get("findings", []) if f["agent"] == a]
            page = next((f for f in af if f["grade"] == "page"), None)
            out["agents"].append({"id": a, "doctor_page": page,
                                  "doctor_findings": len(af)})
    except Exception:
        out["sections"]["doctor"] = {"error": "doctor unavailable"}

    # 2) Pulse — pressure zones
    try:
        pu = pulse()
        out["sections"]["pulse"] = {"summary": pu["summary"], "zones": pu["zones"]}
    except Exception:
        out["sections"]["pulse"] = {"error": "pulse unavailable"}

    # 3) Lane-health rows (W16) — per-agent
    lh_rows: Dict[str, Any] = {}
    try:
        for a_row in out["agents"]:
            aid = a_row["id"]
            lh = _probe_lane_health(aid)
            lh_rows[aid] = lh
    except Exception:
        pass
    out["sections"]["lane_health"] = lh_rows

    # 4) Locks — per-agent
    lk_rows: Dict[str, list] = {}
    try:
        from core.comm import locks
        for a_row in out["agents"]:
            aid = a_row["id"]
            try:
                lm = locks.LockManager(aid)
                lk_rows[aid] = lm.list_held() if hasattr(lm, "list_held") else []
            except Exception:
                lk_rows[aid] = []
    except Exception:
        pass
    out["sections"]["locks"] = lk_rows

    # 5) Recent commits
    commits: list = []
    try:
        import subprocess
        import time as _time
        since = _time.strftime("%Y-%m-%dT%H:%M:%S",
                               _time.localtime(_time.time() - commit_hours * 3600))
        r = subprocess.run(
            ["git", "log", f"--since={since}", "--format=%h %s", "--no-merges"],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        commits = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()][:15]
    except Exception:
        pass
    out["sections"]["commits"] = commits

    # If single-agent focus, fold in unwedge
    if agent:
        out["fleet"] = False
        out["agent"] = agent
        try:
            out["sections"]["unwedge"] = unwedge(agent)
        except Exception:
            out["sections"]["unwedge"] = {"error": "unwedge unavailable"}

    return out


def format_flightdeck(fd: Dict[str, Any], json_mode: bool = False) -> str:
    """Render flightdeck as a compact cockpit view."""
    if json_mode:
        import json as _json
        return _json.dumps(fd, indent=2, default=str)

    sec = fd.get("sections", {})
    lines = ["══ FLEET FLIGHTDECK ══", ""]

    # Pause banner
    dr = sec.get("doctor", {})
    if dr.get("summary"):
        lines.append(dr["summary"])

    # Pulse
    pu = sec.get("pulse", {})
    if pu.get("summary"):
        lines.append(pu["summary"])

    # Per-agent compact lines
    lines.append("")
    lines.append(f"{'AGENT':<14} {'PULSE':<10} {'STATUS':<22} {'LANE':<22} {'LOCKS'}")
    lines.append("-" * 90)
    for a in fd.get("agents", []):
        aid = a["id"]
        # pulse zone
        zone = ""
        for z, ids in pu.get("zones", {}).items():
            if aid in ids:
                zone = z
                break
        # unwedge-style status from doctor_page
        dp = a.get("doctor_page")
        if dp:
            status = dp["state"][:20]
        else:
            status = "ok"
        # lane health
        lh = sec.get("lane_health", {}).get(aid) or {}
        lh_str = ""
        if lh:
            bits = []
            if lh.get("age_s") is not None:
                bits.append(f"age {int(lh['age_s'])}s")
            if lh.get("depth"):
                bits.append(f"d={lh['depth']}")
            if lh.get("straggler"):
                bits.append(f"s={lh['straggler']}")
            lh_str = " ".join(bits) if bits else "healthy"
        else:
            lh_str = "legacy"
        # locks
        lks = sec.get("locks", {}).get(aid, [])
        lk_str = str(len(lks)) if lks else "0"
        lines.append(f"{aid:<14} {zone:<10} {status:<22} {lh_str:<22} {lk_str}")

    # Commits
    commits = sec.get("commits", [])
    if commits:
        lines.append("")
        lines.append(f"── recent commits ({len(commits)}) ──")
        for c in commits[:8]:
            lines.append(f"  {c}")

    # Single-agent detail
    if not fd.get("fleet"):
        agent = fd.get("agent", "?")
        lines.append("")
        lines.append(f"── {agent} detail ──")
        uw = sec.get("unwedge", {})
        if uw.get("verdict"):
            lines.append(f"  status: {uw['status']}")
            lines.append(f"  verdict: {uw['verdict']}")
            lines.append(f"  recommendation: {uw.get('recommendation','')}")
            ev = uw.get("evidence", {})
            for f in ev.get("findings", [])[:6]:
                lines.append(f"    [{f['grade']}] {f['line']}")

    return "\n".join(lines)


def _token_cost_line(agent: str, journal_dir: str = "") -> Optional[Dict[str, Any]]:
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
        # T110: PRICE AT READ TIME, never trust the stored cost_est. That key was
        # computed by whatever wrote the file -- and every journal written before
        # T110 carries a DeepSeek-priced figure regardless of vendor (kimi's real
        # file said $9.076 for kimi-k3 tokens). Deriving here gives pricing one
        # source of truth (the PRICES table) and self-heals every journal ever
        # written, so no backfill script exists to go stale in turn. The stored
        # value is the fallback only if the derivation itself fails.
        cost = float(data.get("cost_est", 0) or 0)
        unpriced, missing = int(data.get("unpriced_tokens", 0) or 0), data.get("unpriced_models") or []
        try:
            from scripts.runner_token_journal import TokenJournal as _TJ
            j = _TJ(agent, journal_dir=base)      # read-only: _load() only, no add_turn
            if j.turns:
                cost, unpriced, missing = j.total_cost_est(), j.unpriced_tokens(), j.unpriced_models()
        except Exception:
            pass
        line = (f"{agent}: {turns} turn(s) · {_fmt_toks(total)} tokens "
                f"today · ~${cost:.2f} est")
        # A journal may legitimately hold tokens we refuse to price (no sourced
        # rate for that model). Rendering only the priced half turns a designed,
        # visible gap back into a confident zero -- "~$0.00 est" on 16.1M real
        # kimi tokens reads as FREE USAGE. Say the word and NAME the model: the
        # operator reading this line is the one who can supply the rate.
        if unpriced:
            names = ", ".join(str(m) for m in missing) if missing else "unknown model"
            line += f" · {_fmt_toks(unpriced)} UNPRICED ({names} — no rate in PRICES)"
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
    """The doctor's round: findings across the fleet + the one-line summary.

    Page-grade findings ALWAYS escalate to the pager (the human-facing channel),
    deduped per (agent, state) per PAGE_DEDUP_TTL. That is not opt-in and must not
    become opt-in: escalation behind a flag is how a computed red goes unread for
    45 hours. page_notes=True additionally broadcasts a fleet bus note -- louder,
    fleet-wide, and still the caller's choice."""
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
    if pages:
        _emit_pages(pages, notes=bool(page_notes))
    _reconcile_pages(pages, agents)      # retract what resolved, even when nothing pages now
    return {"agents": agents, "findings": findings, "pages": pages, "summary": summary}


def _page_key(f: Dict[str, Any]) -> str:
    """What a page is ABOUT: (agent, state). Stable across re-observations, so the same
    condition escalates once and retracts once."""
    return f"{f.get('agent')}:{f.get('state')}"


def _reconcile_pages(pages: List[Dict[str, Any]], agents: List[str]) -> None:
    """Retract escalations whose condition is GONE.

    An escalation channel that cannot retract stops being read. Live receipt (2026-07-27):
    the lane_stall pages for claude and deepseek fired correctly, both lanes drained inside the
    hour, and the pages kept rendering into every UserPromptSubmit for NINE HOURS -- because
    ack_pages() is fleet-wide and acking the resolved one would have discarded the live one.
    That is how a page becomes wallpaper, which is the same 45-hour silence this module exists
    to prevent, arriving by a different road.

    Scoped to the agents actually examined: a single-agent round must never retract a page for
    a seat it did not look at. Clears the dedup key too, so a condition that resolves and
    RECURS inside the window pages again -- a flapping consumer is a signal, not noise.
    """
    c = _client()
    if c is None:
        return
    try:
        from core.comm import pager
        live = {_page_key(f) for f in pages}
        scope = {str(a) for a in (agents or [])}
        for rec in pager.unread_pages(c=c):
            key = str(rec.get("key") or "")
            if not key or key in live:
                continue
            if str(rec.get("agent") or "") not in scope:
                continue                      # not ours to retract this round
            pager.clear_key(key, c=c)
            try:
                agent, _, state = key.partition(":")
                c.delete(f"{_escalated_prefix()}{agent}:{state}")
            except Exception:
                pass
    except Exception:
        pass


def _first_this_window(c, prefix: str, f: Dict[str, Any]) -> bool:
    """True when this (channel, agent, state) has not fired inside PAGE_DEDUP_TTL.
    Fail-OPEN toward emitting: no dedup store is a reason to page twice, never a
    reason to stay silent."""
    if c is None:
        return True
    try:
        return bool(c.set(f"{prefix}{f['agent']}:{f['state']}", "1",
                          nx=True, ex=PAGE_DEDUP_TTL))
    except Exception:
        return True


def _emit_pages(pages: List[Dict[str, Any]], *, notes: bool = True) -> None:
    """Route page-grade findings OUT of the doctor, to two channels.

    ORDER IS LOAD-BEARING (2026-07-26). The pager goes FIRST and stands alone: it is
    the only channel that reaches a human (the UserPromptSubmit hook injects [PAGE]
    lines into any live seat), and the bus-note broadcast below constructs a Bus --
    a construction that can fail. Behind it, every page died silently, which is
    exactly the outage in which a stall is most likely and least visible.
    """
    c = _client()
    for f in pages:                                  # channel 1: the human
        try:
            if _first_this_window(c, _escalated_prefix(), f):
                from core.comm import pager
                # The pager renders '[PAGE] {agent}: {text}' and every doctor line
                # already opens with '{agent}: ' -- strip ours or it stutters.
                body = str(f["line"])
                prefix = f"{f['agent']}: "
                if body.startswith(prefix):
                    body = body[len(prefix):]
                pager.page(f["agent"], f"{body}  drill: {f['drill']}", c=c,
                           key=_page_key(f))
        except Exception:
            pass
    if not notes:
        return
    try:                                             # channel 2: the fleet bus note
        from core.comm.bus import Bus
        bus = Bus("doctor")
    except Exception:
        return
    for f in pages:
        try:
            if not _first_this_window(c, _paged_prefix(), f):
                continue                    # already noted this hour
            bus.broadcast("note", f"[doctor] {f['line']}  drill: {f['drill']}",
                          meta={"via": "doctor", "display_only": True})
        except Exception:
            pass
