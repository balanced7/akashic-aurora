"""expectations -- sender-side reply deadlines + redrive (T030 L4 / RB-29).

The sender arms an expectation when it NEEDS an answer; the pull floor (boot /
bifrost-sync) sweeps at render -- no daemon, a turn-based sender checks exactly when it
can act (T025 doctrine). Expired -> redrive a copy (meta {redrive_of, attempt}) up to
REDRIVES times with a fresh deadline each attempt; exhausted -> durable
`expectation_dead` event + a loud render line. RB-26's consumer-side ack registry
dedupes redelivered handoffs; duplicates are tolerated for chat kinds (reconciled).

Reply detection is CONSUMPTION-IMMUNE: arm() captures the sender-inbox stream tail as
an ANCHOR and the sweep reads the stream from there -- entries outlive cursors, so a
reply the sender already read still clears its expectation. An ANSWER is any directed
message of an ANSWER_KIND (reply / handoff / completion -- T061: answers legitimately
arrive as pointer+verdict handoffs per the packet law; six of them redrove ~4 times on
2026-07-14 because only kind=reply settled). Exact match when the answer's meta carries
answers:<orig_id>; an unlinked answer from the recipient clears the OLDEST expectation
to that recipient armed BEFORE it (FIFO fallback; expectations armed after an answer are
immune to it). "note" is deliberately NOT an answer kind: RB-29 timeout/error notes must
keep the expectation armed so the redrive fires.

Records are Redis-ephemeral coordination state, not durable knowledge -- losing Redis
is the bigger RB-30 event and voids the expectations with it (design-review AFFIRMED).

Spec: docs/library/design/20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79.md L4 BUILD SPEC.
Review: docs/library/report/20260711_t030-l4-design-review-deepseek-fenced-ga_6a89fd.md (AFFIRM x5).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

# T076c: task ids an ask's text references -- the settle probe's extraction surface.
_TASK_IDS = re.compile(r"\bT\d{3}\b")


def _terminal_task_settle(content: Any) -> Optional[str]:
    """T076c root spigot: if the ask's text references task ids and ALL of them are
    TERMINAL in the ledger (done/abandoned), the ask is an echo of finished work --
    return the settle reason. No ids / any unknown id / any probe error -> None
    (conservative: redrive exactly as before). Kill switch AKASHIC_EXPECT_TASK_SETTLE=0."""
    if os.getenv("AKASHIC_EXPECT_TASK_SETTLE", "1") == "0":
        return None
    ids = sorted(set(_TASK_IDS.findall(str(content or ""))))
    if not ids:
        return None
    try:
        from core.coord.task_ledger import read_ledger
        status = {str(t.get("id")): str(t.get("status") or "")
                  for t in (read_ledger().get("tasks") or [])}
        if all(status.get(i) in ("done", "abandoned") for i in ids):
            return "referenced tasks terminal: " + ", ".join(f"{i}={status[i]}" for i in ids)
    except Exception:
        return None
    return None


def _ns() -> str:
    # ns-isolation (2026-07-12, Fix A generalized): coordination keys follow BIFROST_NAMESPACE so a
    # drill namespace can never collide with (or freeze) live. Default "bifrost" preserved; per-call.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _expect_prefix() -> str:
    return f"{_ns()}:expect:"
REDRIVES = 3
MIN_WITHIN_S = 30      # clamp floor: sub-30s reply deadlines on a turn-based bus are noise


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("expect")._client
    except Exception:
        return None


def _key(sender: str) -> str:
    return _expect_prefix() + str(sender)


def _id_tuple(sid: str) -> Tuple[int, int]:
    """Stream ids compare as (ms, seq) -- string compare lies across digit widths."""
    try:
        ms, _, seq = str(sid).partition("-")
        return int(ms), int(seq or 0)
    except Exception:
        return (0, 0)


def arm(sender: str, orig_id: str, to: str, kind: str, content: Any, within_s: int) -> bool:
    """Record a reply expectation for an already-sent message. Clamps within_s to
    >= MIN_WITHIN_S. The anchor is the sender-inbox tail AT ARM TIME (the sender's own
    send never lands in its own inbox, so the anchor cleanly precedes any reply)."""
    c = _client()
    if c is None:
        return False
    try:
        from core.comm.bus import Bus
        anchor = Bus(str(sender)).tail().get("inbox", "0")
        within = max(MIN_WITHIN_S, int(within_s))
        rec = {"to": str(to), "kind": str(kind), "content": content,
               "within_s": within, "deadline_ts": time.time() + within,
               "redrives_left": REDRIVES, "attempt": 0,
               "anchor": anchor, "created": time.time()}
        c.hset(_key(str(sender)), str(orig_id), json.dumps(rec, default=str))
        return True
    except Exception:
        return False


def _emit_dead(sender: str, orig_id: str, rec: Dict[str, Any]) -> None:
    """Durable exhaustion record; the sweep's caller prints the loud line."""
    try:
        from core.events.event_log import capture_event
        capture_event("expectation_dead",
                      f"{rec.get('to')} never answered {orig_id} after {REDRIVES} redrives",
                      agent_id=str(sender), refs=[str(orig_id)],
                      detail={"to": rec.get("to"), "kind": rec.get("kind"),
                              "attempts": rec.get("attempt")})
    except Exception:
        pass


# Kinds that can SETTLE an expectation (T061). "note" is deliberately absent -- RB-29
# timeout/error notes must keep the expectation armed so the redrive fires.
#
# FIFO EDGE (T061 adversarial review, deepseek 2026-07-15): the unlinked-FIFO fallback
# clears EXACTLY ONE expectation per answer message. If a sender has N expectations on
# the same target and answers all N with one message, only the oldest clears; N-1 will
# redrive (the limitation pre-existed T061; the widening just makes it reachable through
# handoff/completion shapes too). Multiple armed asks to the same target need either
# meta.answers-linked answers (one per ask) or multiple answers (one per expectation).
# ALSO: an unlinked handoff/completion that is genuinely UNRELATED to the ask will still
# FIFO-clear the oldest expectation (false-positive by census alone). Rare in practice
# because most answers from a target while an expectation is armed ARE answers.
ANSWER_KINDS = {"reply", "handoff", "completion"}


def _answers_since(sender: str, anchor: str) -> List[Any]:
    """Directed ANSWER-kind messages in the sender's inbox stream AFTER `anchor` -- read
    from the stream position, not the cursor, so consumption cannot hide them. The bc
    lane is pinned at its current tail (broadcast answers are room chatter, never
    settle)."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(sender))
        bc_now = b.tail().get("bc", "0")
        msgs = b.wait(timeout_ms=1, limit=200, since={"inbox": anchor, "bc": bc_now})
        return [m for m in msgs if getattr(m, "kind", "") in ANSWER_KINDS]
    except Exception:
        return []


def _resolve_link(answers_id: Any, recs: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """The expectation `answers_id` refers to, tolerating the DUAL-WRITE ID PAIR.

    One send lands on both the lane stream and the legacy stream under two ids. The
    expectation is armed on the id send() returned; the peer answers against the id
    it actually received. Live receipt: ask 1785226575154-0, reply
    meta.answers=1785226575153-0 -- one message, two names.

    RESOLVED BY EVIDENCE, NEVER ARITHMETIC (sol's NO-GO on the first fix, which
    adjusted the SEQUENCE while the live pair differed in the MILLISECOND -- dead
    code that let FIFO settle the WRONG ask when two were armed to one target).
    The bus records `{ns}:idalias:<id> -> <sibling>` at _emit, the one place both
    ids are known. Sends that predate the alias (or a lapsed TTL) degrade to the
    FIFO fallback, which is at-least-once -- imprecise, never stranding."""
    a = str(answers_id or "")
    if not a:
        return None
    if a in recs:
        return a
    try:
        c = _client()
        # Bounded alias walk (2 hops): a reply to a REDRIVE names the redrive's
        # LANE id -> its legacy sibling (emit alias) -> the ORIGINAL ask (redrive
        # alias). One hop covers the plain dual-write pair; two covers a redrive's
        # sibling. Bounded, never a loop: each hop must strictly resolve.
        cur = a
        for _ in range(2):
            if c is None:
                break
            sib = c.get(f"{_ns()}:idalias:{cur}")
            if not sib:
                break
            cur = str(sib)
            if cur in recs:
                return cur
    except Exception:
        pass
    return None


# T117 P10 (sol's fault injection): settle+mark is ONE ATOMIC TRANSITION. The
# best-effort mark AFTER hdel meant a failed marker SET with a healthy HDEL restored
# the double-settlement on the next sweep. Lua: the marker is written (NX, TTL
# bounded by the ASK'S OWN horizon -- within_s has no API max) and the expectation
# deleted in one script; if the script cannot run, the expectation SURVIVES -- a
# loud redrive beats silent wrong-work settlement. MODULE-LEVEL by sol's review of
# the pin, not the code: nested inside sweep it was unfaultable, so P10 could only
# patch an obsolete seam and would have gone nominal the moment the code moved.
# The suite owns the receipt only if it can break the real transition.
_SETTLE_LUA = ("redis.call('SET', KEYS[1], '1', 'EX', tonumber(ARGV[2]), 'NX') "
               "redis.call('HDEL', KEYS[2], ARGV[1]) return 1")


def _settle_once(c, sender: str, key: str, oid: str, rid, rec: Dict[str, Any]) -> bool:
    try:
        horizon = max(172800, int(float(rec.get("within_s", MIN_WITHIN_S)))
                      * (int(rec.get("redrives_left", 0)) + 2) * 4)
        c.eval(_SETTLE_LUA, 2, f"{_ns()}:reply_settled:{sender}:{rid}", key,
               oid, horizon)
        return True
    except Exception:
        return False                       # expectation stays armed; never half-settle


def sweep(sender: str, now: Optional[float] = None) -> Dict[str, List[str]]:
    """One render-time pass: clear answered, redrive expired, kill exhausted.
    Returns {"redriven": [ids], "dead": [ids], "cleared": [ids]}; `now` injectable so
    pins never sleep. Never raises."""
    out: Dict[str, List[str]] = {"redriven": [], "dead": [], "cleared": [], "settled": []}
    c = _client()
    if c is None:
        return out
    try:
        key = _key(str(sender))
        raw = c.hgetall(key) or {}
        if not raw:
            return out
        now = time.time() if now is None else float(now)
        recs: Dict[str, Dict[str, Any]] = {}
        for oid, v in raw.items():
            try:
                recs[str(oid)] = json.loads(v)
            except Exception:
                c.hdel(key, oid)               # unparseable record: drop, never wedge
        if not recs:
            return out
        oldest = min((r.get("anchor", "0") for r in recs.values()), key=_id_tuple)
        # T117 P8 (sol's third NO-GO): SETTLEMENT IS IDEMPOTENT PER REPLY. sweep()
        # re-reads from the oldest anchor every pass, so a stored reply that settled
        # an ask on sweep N is read again on sweep N+1 -- its target now gone from
        # recs, its link "unrecognised", and FIFO would hand it a DIFFERENT ask.
        # One reply settled two asks; the second was wrong, and the older ask's real
        # answer then found nothing left to settle. A durable PER-REPLY marker (not
        # a stream frontier -- a frontier could skip a reply needed by a later-armed
        # expectation whose anchor predates it) makes every settlement once-only.
        def _settled(rid) -> bool:
            try:
                return bool(rid) and bool(c.exists(f"{_ns()}:reply_settled:{sender}:{rid}"))
            except Exception:
                return False               # marker unreadable -> behave as before

        def _settle_atomic(oid, rid, rec) -> bool:
            return _settle_once(c, sender, key, oid, rid, rec)

        replies = _answers_since(sender, oldest)
        linked = set()                         # T117: replies whose link RESOLVED
        for r in replies:                      # 1) exact linkage clears first
            if _settled(getattr(r, "id", None)):
                linked.add(getattr(r, "id", None))   # spent: never reaches FIFO either
                continue
            a = _resolve_link((getattr(r, "meta", None) or {}).get("answers"), recs)
            # T117 P9 (sol): the precise path checks WHO answered -- P5 guarded FIFO
            # only, so a reply from agent X naming Y's ask id settled Y's ask.
            if a and recs[a].get("to") != getattr(r, "frm", None):
                a = None
            if a and _settle_atomic(a, getattr(r, "id", None), recs[a]):
                del recs[a]
                out["cleared"].append(a)
                linked.add(getattr(r, "id", None))
        for r in replies:                      # 2) FIFO fallback: one clear per reply
            # T117: skip only replies whose link actually RESOLVED (or that already
            # settled an ask on a PRIOR sweep). A reply naming an id we do not hold
            # is UNLINKED, and the fallback exists for exactly that.
            if getattr(r, "id", None) in linked:
                continue
            cands = sorted(
                ((oid, rec) for oid, rec in recs.items()
                 if rec.get("to") == getattr(r, "frm", None)
                 and _id_tuple(rec.get("anchor", "0")) < _id_tuple(getattr(r, "id", "0"))),
                key=lambda kv: float(kv[1].get("created", 0)))
            if cands and _settle_atomic(cands[0][0], getattr(r, "id", None), cands[0][1]):
                oid = cands[0][0]
                del recs[oid]
                out["cleared"].append(oid)
        for oid, rec in list(recs.items()):    # 3) deadlines
            if now < float(rec.get("deadline_ts", 0)):
                continue
            # T117 P11 debug find: this probe reads the TASK PLANE, and in an isolated
            # env (or any task-store outage) it RAISED -- sweep's outer catch then
            # swallowed the whole deadline loop, so REDRIVES silently stopped. A
            # settle-probe failure means "cannot prove settled", never "stop redriving".
            try:
                settle = _terminal_task_settle(rec.get("content"))   # T076c: echoes of DONE
            except Exception:
                settle = None
            if settle is not None:                               # work settle, never redrive
                try:
                    from core.events.event_log import capture_event
                    capture_event("expectation_settled_done_task",
                                  f"ask {oid} to {rec.get('to')} auto-settled: {settle}",
                                  agent_id=str(sender), refs=[str(oid)],
                                  detail={"to": rec.get("to"), "settle": settle,
                                          "attempt": rec.get("attempt")})
                except Exception:
                    pass
                c.hdel(key, oid)
                out["settled"].append(oid)
                continue
            if int(rec.get("redrives_left", 0)) > 0:
                from core.comm.bus import Bus
                attempt = int(rec.get("attempt", 0)) + 1
                new_mid = Bus(str(sender)).send(rec["to"], rec.get("kind", "request"),
                                                rec.get("content"),
                                                meta={"redrive_of": oid, "attempt": attempt})
                # T117 P11 (sol): the peer answers the only id it ever SAW -- the
                # redrive's. Alias it to the ORIGINAL ask, or the reply resolves to
                # nothing and the original redrives again: the disease reborn one
                # generation down. (_resolve_link follows aliases, so the redrive's
                # lane sibling reaches the original in two hops.)
                if new_mid:
                    try:
                        c.set(f"{_ns()}:idalias:{new_mid}", oid, ex=172800)
                    except Exception:
                        pass
                rec.update(attempt=attempt,
                           redrives_left=int(rec.get("redrives_left", 0)) - 1,
                           deadline_ts=now + int(rec.get("within_s", MIN_WITHIN_S)))
                c.hset(key, oid, json.dumps(rec, default=str))
                out["redriven"].append(oid)
            else:
                _emit_dead(sender, oid, rec)
                c.hdel(key, oid)
                out["dead"].append(oid)
        return out
    except Exception:
        return out


def format_sweep_lines(res: Dict[str, List[str]]) -> List[str]:
    """Render-side: loud lines for what the sweep did (empty list = quiet)."""
    lines = []
    for oid in res.get("settled", []):
        lines.append(f"= settled {oid} (T076c: its referenced tasks are DONE in the ledger -- "
                     f"echo, not a live ask; durable event recorded)")
    for oid in res.get("redriven", []):
        lines.append(f"~ redrove {oid} (no reply by deadline -- copy sent, meta redrive_of)")
    for oid in res.get("dead", []):
        lines.append(f"!! EXPECTATION DEAD: {oid} unanswered after {REDRIVES} redrives "
                     f"-- durable event recorded; chase it or let it go")
    return lines
