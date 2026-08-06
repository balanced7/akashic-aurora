"""friction -- read the collaboration tax from evidence that already exists (T196a).

Sol's recommendation ("measure collaboration friction"), fenced through deepseek (T196
spec, branches C + C2): the verb redesign is not allowed to call itself an improvement
without a baseline, and the baseline must claim nothing the anchors cannot show. This
module is a READER: fold() is pure (no I/O at all), gather() composes reads and writes
NOTHING -- observation split from action (T025), the same split expectations.sweep()
honors from the other side.

An EPISODE is one durable ask's lifetime. Terminal episodes come from the firehose
(the durable terminal events expectations.py emits -- T196b closed the ANSWERED gap);
open episodes come from the armed expectation records (expectations.snapshot). Every
number here follows the house honesty laws: a duration without evidence is None (never
0.0, never a now-based guess -- the fabricated-total lie one layer down), a rate over
zero closed episodes is None, and the report carries a structurally NON-EMPTY `blind`
list because a report that names no blindness is claiming omniscience.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.foundation.timeutil import to_epoch

# Terminal firehose kinds -> episode outcome. ECHO is deliberately distinct from
# ANSWERED (the T196 fence's one resolved disagreement): a T076c settle has NO message
# anywhere -- the answer arrived as ledger state, and the caller's move differs (read
# the ledger, not the mailbox).
TERMINAL_KINDS = {
    "expectation_settled_answered": "answered",
    "expectation_dead": "dead",
    "expectation_settled_done_task": "echo",
}

# Named blindness (no-silent-caps made structural). Static by design: these are facts
# about the ANCHORS, not about any one report.
BLIND = [
    "answered/dead durations exist only where the terminal event carries `created` "
    "(T196b, 2026-08-05) -- older episodes report duration None",
    "answered episodes are visible only from T196b onward: before it, an answered ask "
    "left no durable terminal event at all",
    "commands are not counted: CLI door captures are selective (boot/handoff/decision/"
    "learning), so operator keystrokes and shell work are invisible (fence C)",
    "silent stalls are invisible: an ask that never redrives and never settles renders "
    "as open, not as troubled (fence C2)",
    "usefulness is not measured: time-to-settle says an answer ARRIVED, not that it "
    "helped -- v2 candidates: re-ask window, self-reclamation rate (fence C2)",
    "reads the per-agent event stream (an index): an event whose index write degraded "
    "(T179 PARTIALLY) is on the canonical firehose but absent here",
    "the peer partition rests on TWO POINT SAMPLES (attendance at ask, attendance at "
    "death) and observes nothing in between: a peer that died and recovered inside the "
    "window reads as `ignored`, and one that flapped repeatedly reads as whichever "
    "state the two samples happened to catch (T197)",
    "episodes closed before T197 (2026-08-06) carry no peer observation at all and "
    "count as dead_peer_unknown -- they are NOT back-filled, because the reader is not "
    "entitled to a verdict it never took",
    "presence_effect is a CORRELATION and licenses no causal claim: the same conductor "
    "who launches a peer also asks better-formed questions to peers worth launching, so "
    "a higher attended answer-rate is not proof that launching caused it (T199)",
    "Sol's collaboration-friction list is only PARTLY built: commands per task, "
    "operator interventions, and recovery time are all still unmeasured -- none of the "
    "three has a durable anchor yet, and time-to-first-useful-output is approximated by "
    "time-to-settle, which says an answer ARRIVED, not that it helped",
]


# T197: the pair -> the bug. Until 2026-08-06 every dead ask was the same row, and the
# 81.2% dead-rate could not say WHICH failure it was measuring. With attendance observed
# at ask time AND at death, four different bugs separate -- each with a different action:
#
#   at ask       at death        verdict        what to actually do
#   UNATTENDED   UNATTENDED      absent         launch the peer; nobody was ever home
#   ATTENDED     UNATTENDED      vanished       chase the crash; it died mid-flight
#   ATTENDED     ATTENDED        ignored        chase the consumer (wrong lane? wedge?)
#   UNATTENDED   ATTENDED        arrived_late   it came up and STILL did not answer
#
# Anything else is `unknown`, including every episode closed before this instrument
# existed. UNKNOWN is not a rounding error here: it is the guard against the reader
# back-filling 26 historical deaths with the answer it expects.
_DEAD_VERDICT = {
    ("UNATTENDED", "UNATTENDED"): "absent",
    ("ATTENDED", "UNATTENDED"): "vanished",
    ("ATTENDED", "ATTENDED"): "ignored",
    ("UNATTENDED", "ATTENDED"): "arrived_late",
}
DEAD_VERDICTS = ("absent", "vanished", "ignored", "arrived_late", "unknown")


def dead_verdict(at_ask: Any, at_death: Any) -> str:
    """Which of the four deaths this was -- or `unknown`, said plainly.

    BOTH ends are required. One end is not the pair: `peer_at_ask == ATTENDED` alone
    cannot tell `vanished` from `ignored`, and choosing either would be the fabricated
    attribution deepseek's fence (2026-08-06) identified as worse than no column at all.
    attendance's own UNKNOWN verdict also lands here -- a probe that could not read is
    evidence about the PROBE, never about the peer.
    """
    return _DEAD_VERDICT.get((str(at_ask or ""), str(at_death or "")), "unknown")


def _redrives(detail: Dict[str, Any]) -> int:
    """Both spellings live: settled events carry `attempt`, dead events `attempts`."""
    for k in ("attempt", "attempts"):
        v = detail.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
    return 0


def _span(later: Optional[float], earlier: Any) -> Optional[float]:
    """Seconds between two moments, or None when either side lacks evidence."""
    if later is None or earlier is None:
        return None
    try:
        return max(0.0, float(later) - float(earlier))
    except (TypeError, ValueError):
        return None


def fold(terminal_events: Optional[List[Dict[str, Any]]],
         open_records: Optional[Dict[str, Dict[str, Any]]], *,
         now: float) -> Dict[str, Any]:
    """PURE fold of evidence into the friction report. No I/O; `now` injected so
    pins never sleep (the expectations-suite idiom)."""
    episodes: List[Dict[str, Any]] = []
    durations: List[float] = []
    counts = {"answered": 0, "dead": 0, "echo": 0}
    dead_by_verdict = {v: 0 for v in DEAD_VERDICTS}
    # T199 v2 accumulators. by_peer answers "which peer is broken" (one fleet rate hides
    # it); presence_effect answers "does a present peer actually answer", the question
    # T197 shipped autolaunch on and could not test.
    peers: Dict[str, Dict[str, Any]] = {}
    presence = {"ATTENDED": {"n": 0, "n_answered": 0},
                "UNATTENDED": {"n": 0, "n_answered": 0}, "n_unobserved": 0}

    def _peer_row(name: Any) -> Optional[Dict[str, Any]]:
        """The bucket for one peer, or None when the event names no peer -- a malformed
        record must not mint a peer called None and then get reported as one."""
        if name is None or str(name) == "":
            return None
        return peers.setdefault(str(name), {
            "n_open": 0, "n_answered": 0, "n_dead": 0, "n_echo": 0,
            "_durations": []})

    for ev in terminal_events or []:
        outcome = TERMINAL_KINDS.get(str(ev.get("kind") or ""))
        if not outcome:
            continue                                  # not an episode event
        detail = ev.get("detail") or {}
        refs = ev.get("refs") or []
        if not refs:
            continue                                  # malformed: no ask to attribute to
        try:
            closed_at = to_epoch(ev.get("at"))
        except Exception:
            closed_at = None
        duration = _span(closed_at, detail.get("created"))
        at_ask, at_death = detail.get("peer_at_ask"), detail.get("peer_at_death")
        row = {
            "ask_id": str(refs[0]), "peer": detail.get("to"), "outcome": outcome,
            "duration_s": duration, "redrives": _redrives(detail),
            "closed_at": ev.get("at"),
            "answer_id": detail.get("answer_id"),
            "peer_at_ask": at_ask, "peer_at_death": at_death,
        }
        if outcome == "dead":
            verdict = dead_verdict(at_ask, at_death)
            row["peer_verdict"] = verdict
            dead_by_verdict[verdict] += 1
        episodes.append(row)
        counts[outcome] += 1
        if duration is not None:
            durations.append(duration)

        prow = _peer_row(detail.get("to"))
        if prow is not None:
            prow[f"n_{outcome}"] += 1
            if duration is not None:
                prow["_durations"].append(duration)

        # ECHO is excluded on purpose: a T076c settle has no message anywhere -- the
        # answer arrived as ledger state -- so it says nothing about whether a present
        # peer answers MAIL, and counting it would move a rate it cannot inform.
        if outcome in ("answered", "dead"):
            bucket = presence.get(str(at_ask or ""))
            if bucket is None:
                # Unobserved (pre-T197) or attendance's own UNKNOWN. EXCLUDED from the
                # rates and COUNTED here: folding these into UNATTENDED would fabricate
                # exactly the correlation this instrument exists to test.
                presence["n_unobserved"] += 1
            else:
                bucket["n"] += 1
                if outcome == "answered":
                    bucket["n_answered"] += 1

    for oid, rec in (open_records or {}).items():
        try:
            attempt = int(rec.get("attempt", 0) or 0)
        except (TypeError, ValueError):
            attempt = 0
        deadline = rec.get("deadline_ts")
        try:
            deadline_in = (float(deadline) - float(now)) if deadline is not None else None
        except (TypeError, ValueError):
            deadline_in = None
        episodes.append({
            "ask_id": str(oid), "peer": rec.get("to"), "outcome": "open",
            "state": "redriving" if attempt > 0 else "dispatched",
            "age_s": _span(now, rec.get("created")), "redrives": attempt,
            "deadline_in_s": deadline_in,
            "peer_at_ask": rec.get("peer_at_ask"),
        })
        prow = _peer_row(rec.get("to"))
        if prow is not None:
            prow["n_open"] += 1

    n_closed = sum(counts.values())
    durations.sort()

    def _pct(p: float) -> Optional[float]:
        if not durations:
            return None                # a percentile of nothing is not a number
        i = int(round(p * (len(durations) - 1)))
        return durations[min(len(durations) - 1, max(0, i))]

    def _median(vals):
        s = sorted(vals)
        return s[len(s) // 2] if s else None      # None, never 0.0, over an empty set

    by_peer: Dict[str, Dict[str, Any]] = {}
    for name, row in peers.items():
        closed = row["n_answered"] + row["n_dead"] + row["n_echo"]
        by_peer[name] = {
            "n_open": row["n_open"], "n_answered": row["n_answered"],
            "n_dead": row["n_dead"], "n_echo": row["n_echo"], "n_closed": closed,
            "dead_rate": (row["n_dead"] / closed) if closed else None,
            "settle_median_s": _median(row["_durations"]),
        }
    # Ordered by PAIN, not alphabet: the reader's job is to surface the broken peer, and
    # an alphabetical listing buries it. Name breaks ties so the order is stable.
    by_peer = dict(sorted(by_peer.items(),
                          key=lambda kv: (-kv[1]["n_dead"], kv[0])))

    presence_effect = {"n_unobserved": presence["n_unobserved"]}
    for state in ("ATTENDED", "UNATTENDED"):
        b = presence[state]
        presence_effect[state] = {
            "n": b["n"], "n_answered": b["n_answered"],
            # None over an empty cell. Early on every denominator is 0 or 1, and 0.0
            # rendered against n=0 would read as "attended peers never answer".
            "answer_rate": (b["n_answered"] / b["n"]) if b["n"] else None,
        }

    agg = {
        "n_open": len(open_records or {}),
        "by_peer": by_peer, "presence_effect": presence_effect,
        "n_answered": counts["answered"], "n_dead": counts["dead"],
        "n_echo": counts["echo"], "n_closed": n_closed,
        # 0/0 rendered as 0.0 would read as "nothing ever dies" -- None is the truth.
        "dead_rate": (counts["dead"] / n_closed) if n_closed else None,
        "settle_p50_s": _pct(0.5), "settle_p90_s": _pct(0.9),
        "n_duration_unknown": n_closed - len(durations),
        # T197: the partition, keyed `dead_<verdict>` and summing EXACTLY to n_dead.
        # A partition that does not sum is a set of overlapping guesses, and the rows
        # it drops would be invisible instead of named.
        **{f"dead_{v}": dead_by_verdict[v] for v in DEAD_VERDICTS if v != "unknown"},
        "dead_peer_unknown": dead_by_verdict["unknown"],
    }
    return {"episodes": episodes, "agg": agg, "blind": list(BLIND)}


def gather(agent: str, *, window_h: float = 168, log=None,
           now: Optional[float] = None) -> Dict[str, Any]:
    """Compose the reads: per-agent firehose scan + armed-record snapshot -> fold.
    ZERO writes to any stream, record, or cursor (pinned). `log`/`now` injectable."""
    now = time.time() if now is None else float(now)
    if log is None:
        from core.events.event_log import EventLog
        log = EventLog()
    try:
        raw = log.scan(agent=str(agent))
    except Exception:
        raw = []
    horizon = now - float(window_h) * 3600.0
    events = []
    for ev in raw:
        if str(ev.get("kind") or "") not in TERMINAL_KINDS:
            continue
        try:
            at = to_epoch(ev.get("at"))
        except Exception:
            at = None                  # unparseable timestamp: keep (never silently drop)
        if at is not None and at < horizon:
            continue
        events.append(ev)
    from core.comm.expectations import snapshot
    return fold(events, snapshot(str(agent)), now=now)
