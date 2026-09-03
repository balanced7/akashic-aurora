"""The automatic Discord feed — the subscription that makes the bridge real.

CENSUS FINDING 2026-08-18: the outbound bridge (T223, 08-07) shipped its module and manual
verbs, and NO process ever subscribed the bus to it — built-not-wired at the feed layer.
Even a configured webhook posted nothing except by hand. This module is the missing caller:
the daemon pumps it every few seconds, it tails the LEGACY plane (broadcast + per-agent
inboxes — the complete straggler net per the T039a/T045 dual-write law, so tailing it alone
yields every message exactly once, no work-lane twins), and forwards each new message to the
global channel (discord_bridge.forward) and its ask's room (discord_rooms.post_to_room),
each of which self-filters.

THE RULE THIS MODULE EXISTS TO KEEP: a first run against a stream with history must
initialize its cursor to the stream's TAIL and post NOTHING. The legacy plane holds
millions of entries; "turn on the feed" must never mean "replay the archive to a phone."

Cursor: one Redis hash, stream_key -> last_seen_id, advanced AFTER the post attempt
(RB-26 shape: a crash redelivers, so a duplicate phone line is possible and chosen —
duplicate beats lost on a notification surface).

NEVER RAISES into the daemon; unconfigured is a state, and the fast-exit costs one env
read plus at most one file stat.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from core.outcome import BoundaryOutcome
from core.comm import discord_bridge as DB
from core.comm import discord_rooms as ROOMS

CURSOR_KEY = "bifrost:discord:feed_cursor"

#: per pump() call — the daemon runs this at ~0.1 Hz, so this caps burst size, and
#: Discord's 30/min/webhook budget stays respected under sustained chatter.
MAX_PER_PUMP = 20


def configured() -> bool:
    return bool(DB.webhook_url() or ROOMS.forum_url())


def _decode(fields: Dict[Any, Any]) -> Dict[str, Any]:
    """Envelope fields arrive as flat (possibly bytes) pairs — and bus._emit
    json.dumps's content/meta/parts with ensure_ascii, so an em-dash rides as a
    literal backslash-u2014 inside a QUOTED string. The phone is not a JSON
    parser (live receipt 2026-08-18: first-light rendered on Daniil's screen
    with wrapping quotes and raw escapes). Decode every field that parses;
    leave anything that doesn't exactly as it came."""
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        ks = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
        vs = v.decode(errors="replace") if isinstance(v, (bytes, bytearray)) else v
        out[ks] = vs
    for field in ("content", "meta", "parts"):
        if isinstance(out.get(field), str):
            try:
                out[field] = json.loads(out[field])
            except ValueError:
                pass
    return out


#: the operator's inbox names — a seat's question FOR HIM rides these streams, and
#: each routes to his lane with that seat (his ask, 2026-08-19: "separate messaging
#: channels for all of you so that if anyone has a question specifically for me
#: I can respond").
_OPERATOR_INBOXES = ("daniil", "daniel", "user")


def seat_channel_url(agent: str) -> str:
    """The webhook of his lane with this seat, vaulted by ``discord_setup``.

    The stable seat address is authoritative and therefore checked first.  A ratified
    callsign is a backwards-compatible display alias for the four original lanes.  Both
    candidates must exist in the vault allowlist before any path is constructed: a bus
    sender string is not permission to read an arbitrary file.  This also lets an
    unratified seat such as ``sol`` have transport without inventing a callsign ceremony.
    """
    base = str(agent or "").split("#", 1)[0].lower()
    try:
        from core.fleet import residents as _R
        cs = str((_R.get(base) or {}).get("callsign") or "").strip().lower()
    except Exception:                                                   # noqa: BLE001
        cs = ""
    from core.comm.secret_intake import TARGETS, secrets_dir
    candidates = [f"discord_channel_{base}.url"]
    if cs:
        candidates.append(f"discord_channel_{cs}.url")
    for name in dict.fromkeys(candidates):
        if name not in TARGETS:
            continue
        try:
            value = (secrets_dir() / name).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return ""


def _streams(bus: Any) -> List[str]:
    keys = [f"{bus.ns}:broadcast"]
    try:
        agents = sorted(bus.known_agents())
    except Exception:                                                   # noqa: BLE001
        agents = []
    keys.extend(bus._inbox_key(a) for a in agents)
    keys.extend(bus._inbox_key(op) for op in _OPERATOR_INBOXES
                if bus._inbox_key(op) not in keys)
    return keys


def _post_failure_loud(path: str, msg: Dict[str, Any], mid: str, exc: Exception) -> None:
    """A failed Discord post is a FINDING, never a shrug: stderr line + durable
    event, so the doctor and the next post-mortem can see exactly which reply
    died on which path. Never raises (the pump's beat survives the confession)."""
    try:
        import sys as _sys
        print(f"[discord-feed] POST FAILED ({path}) mid={mid} "
              f"frm={msg.get('frm')} to={msg.get('to')} "
              f"({type(exc).__name__}: {str(exc)[:120]})", file=_sys.stderr)
    except Exception:                                                   # noqa: BLE001
        pass
    try:
        from core.events.event_log import capture_event
        capture_event("discord_feed_post_failed",
                      f"{path} post failed for {msg.get('frm')}->{msg.get('to')}",
                      agent_id="discord", refs=[str(mid)],
                      detail={"path": path, "frm": str(msg.get("frm")),
                              "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    except Exception:                                                   # noqa: BLE001
        pass


def _forward_global(msg: Dict[str, Any]) -> bool:
    """The default global path: the seat speaks AS ITSELF (rung 2 of person-hood,
    Daniil 2026-08-18: 'show up as your own person in the chat'). Reuses the rooms
    transport, which already carries a username; the manual `discord test/send`
    verbs keep the bridge's who-in-body render untouched. Same laws as everywhere:
    allowlist inherited, redaction + clip via the rooms render, never raises.

    Returns False iff a post ATTEMPT failed (S2, 2026-09-02): the caller's own
    receipt must agree with the confession -- _post_failure_loud was already loud
    here, but pump() counted the corpse as forwarded because this swallowed the
    verdict along with the exception. Skipped-by-design still returns True."""
    if not DB.should_forward(msg):
        return True
    urls = DB.webhook_urls()
    if not urls:
        return True
    try:
        who = ROOMS.persona(str(msg.get("frm") or ""))
        for part in ROOMS.render_room_parts(msg):
            DB.post_via_pool(
                urls, part,
                lambda u, c, w=who: ROOMS._default_post(
                    u, c, username=w["username"], avatar_url=w["avatar_url"]))
    except Exception as exc:                                            # noqa: BLE001
        # same incident class as the seat-lane swallow: the beat survives, but
        # the failure is loud and journaled instead of impersonating success
        _post_failure_loud("global", msg, str(msg.get("id") or "?"), exc)
        return False
    return True


def pump(bus: Any, *, post: Optional[Callable[..., Any]] = None,
         room_post: Optional[Callable[..., Any]] = None) -> BoundaryOutcome:
    """One feed beat: forward everything new on the legacy plane, then advance."""
    if not configured():
        return BoundaryOutcome.failed(
            "discord feed not configured — no webhook on either channel; a state, "
            "not a failure (the pump costs one check and exits)")
    client = bus._client
    try:
        cursors = {k.decode() if isinstance(k, bytes) else str(k):
                   (v.decode() if isinstance(v, bytes) else str(v))
                   for k, v in (client.hgetall(CURSOR_KEY) or {}).items()}
    except Exception as e:                                              # noqa: BLE001
        return BoundaryOutcome.failed(f"feed cursor read failed ({type(e).__name__}: {e})")

    forwarded = 0
    initialized = 0
    failed = 0
    for key in _streams(bus):
        try:
            if key not in cursors:
                # FIRST CONTACT: tail-init, forward nothing. The archive stays home.
                last = client.xrevrange(key, count=1)
                tail_id = (last[0][0] if last else "0-0")
                tail_id = tail_id.decode() if isinstance(tail_id, bytes) else str(tail_id)
                client.hset(CURSOR_KEY, key, tail_id)
                cursors[key] = tail_id
                initialized += 1
                continue
            entries = client.xrange(key, min="(" + cursors[key], count=MAX_PER_PUMP)
            for mid, fields in entries:
                mid_s = mid.decode() if isinstance(mid, bytes) else str(mid)
                try:
                    msg = _decode(fields)
                except Exception as exc:                                # noqa: BLE001
                    # Defense-in-depth for the S1 class (2026-09-02). NOTE: the
                    # audit's proposed vehicle (list-typed content) does NOT raise
                    # in current _decode -- its isinstance guard passes non-strings
                    # through by law. But any future decode explosion must be loud
                    # EXACTLY once -- confessed, counted, skipped -- never the
                    # silent retry-forever the outer except used to produce. (This
                    # is the display plane; the durable mailbox keeps the record.)
                    failed += 1
                    _post_failure_loud(
                        "decode", {"frm": fields.get("frm"), "to": key}, mid_s, exc)
                    client.hset(CURSOR_KEY, key, mid_s)
                    continue
                msg.setdefault("id", mid_s)
                # ECHO-GUARD, and it must outrank the operator-always-forwards rule:
                # a message that CAME FROM Discord (the ear's stamp) must not be
                # pumped back TO Discord, or every phone line returns to its sender
                # wearing the fleet's face. Cursor still advances — skipped is
                # handled, not pending.
                if isinstance(msg.get("meta"), dict) and \
                        msg["meta"].get("source") == "discord":
                    client.hset(CURSOR_KEY, key, mid_s)
                    continue
                # SEAT LANE: a message addressed TO the operator posts in his
                # channel with that seat — and ONLY there (a question for him is
                # not ambient; double-posting it to global would train him to
                # read neither surface carefully).
                if str(msg.get("to") or "") in _OPERATOR_INBOXES:
                    lane = seat_channel_url(str(msg.get("frm") or ""))
                    if lane and DB.should_forward(msg):
                        ok = True
                        try:
                            who = ROOMS.persona(str(msg.get("frm") or ""))
                            for part in ROOMS.render_room_parts(msg):
                                ROOMS._default_post(lane, part,
                                                    username=who["username"],
                                                    avatar_url=who["avatar_url"])
                        except Exception as exc:                        # noqa: BLE001
                            # 2026-08-23 incident (root-caused by the vandor
                            # sprout, spawn-1787516635): this except used to
                            # `pass` AND count the post as forwarded -- a dead
                            # webhook ate every reply to the operator while the
                            # feed reported success, and even the sprout's own
                            # answer died here. A failed post is now LOUD,
                            # counted, and journaled; the cursor still advances
                            # (skip, never retry-block) but nothing lies.
                            ok = False
                            failed += 1
                            _post_failure_loud("seat-lane", msg, mid_s, exc)
                        client.hset(CURSOR_KEY, key, mid_s)
                        if ok:
                            forwarded += 1
                        continue
                gok = (post or _forward_global)(msg)
                (room_post or ROOMS.post_to_room)(msg)
                client.hset(CURSOR_KEY, key, mid_s)      # advance AFTER the attempt
                if gok is False:
                    # S2: the global post died and said so; the receipt agrees
                    # with the confession instead of claiming a delivery.
                    failed += 1
                else:
                    forwarded += 1
        except Exception as exc:                                        # noqa: BLE001
            # one bad stream must not starve the rest of the beat -- but a caught
            # exception is a FINDING, never a shrug (S1, 2026-09-02): confess to
            # stderr so 'zero errors anywhere' can only mean zero errors.
            try:
                import sys as _sys
                print(f"[discord-feed] STREAM BEAT FAILED (confessed, contained) "
                      f"{key}: {type(exc).__name__}: {str(exc)[:160]}",
                      file=_sys.stderr, flush=True)
            except Exception:                                           # noqa: BLE001
                pass
            continue
    return BoundaryOutcome.done(ref=f"forwarded={forwarded} failed={failed}",
                                forwarded=forwarded, initialized=initialized,
                                failed=failed)


#: shared across every seat's daemon -- ONE key, not one per agent, because the resource
#: being guarded (the cursor hash + the global webhook pool) is shared too.
_PUMP_LOCK_KEY = "discord-pump"
#: shorter than every known daemon's beat interval (bifrost_daemon.py ticks this at 10s) so
#: a crash mid-pump releases the election before the next beat, live or not, rather than
#: blocking a healthy daemon behind a dead one's TTL.
_PUMP_LOCK_TTL = 8


def pump_if_owner(bus: Any, *, post: Optional[Callable[..., Any]] = None,
                  room_post: Optional[Callable[..., Any]] = None) -> BoundaryOutcome:
    """`pump()`, but only for whichever daemon wins a short-lived election this beat.

    THE COORDINATION GAP THIS CLOSES (2026-09-03 reachability incident). Every seat's
    daemon calls this on its own 10s tick, independently, against the SAME shared cursor
    hash and the SAME shared webhook -- with no mutual exclusion, four daemons racing that
    cursor can each observe the same new message as "unseen" and post it, four times, which
    is what actually exhausted Discord's per-webhook rate bucket (bounded retry, shipped
    70aa9314, absorbs the resulting 429s -- it does not stop them from happening). Reusing
    the exact runner-singleton primitive (`core.comm.runner_lock`, TTL SET-NX) that already
    keeps two runners off one agent's cursor makes the four daemons behave as ONE logical
    pump: whoever wins the beat does the real work; every loser's `pump()` call is simply
    never made, and its next tick finds the cursor already caught up and does nothing. The
    daemons call this exactly as they called `pump()` before -- the election is invisible
    to them, and to every agent, which never touched Discord at all.
    """
    from core.comm import runner_lock
    token = runner_lock.instance_token(_PUMP_LOCK_KEY)
    if not runner_lock.acquire(_PUMP_LOCK_KEY, token, ttl=_PUMP_LOCK_TTL):
        return BoundaryOutcome.done(ref="not-owner-this-beat",
                                    forwarded=0, initialized=0, failed=0)
    try:
        return pump(bus, post=post, room_post=room_post)
    finally:
        runner_lock.release(_PUMP_LOCK_KEY, token)


def send_target(agent: str, *, seat_url: Optional[str] = None,
                global_url: Optional[str] = None) -> tuple:
    """Where a MANUAL `discord send` from `agent` should post: (url, source, note).

    THE DEFECT THIS RETIRES (2026-08-25). The manual verb resolved its target as the
    GLOBAL webhook while per-seat lanes existed and worked, and the automatic feed already
    used them. Daniil: "Your reply didn't go to the vandor chat". The command printed
    "[discord] posted" -- true about the call, wrong about the arrival, which is the whole
    family of defect this delivery layer has been shedding for two days.

    THREE PROPERTIES, and the second is the one that matters:
      - his lane with THIS seat is the DEFAULT, chosen by construction rather than by the
        sender remembering it at one in the morning;
      - a fallback to the global channel is ANNOUNCED. A silent fallback is precisely how
        a reply lands in the wrong room while the sender reads success;
      - `source` names the room, so a receipt can say WHERE it went. "Posted" is not a
        receipt if it cannot tell you that.

    Both urls are injectable so a pin runs without a vault or a network.
    """
    seat = str(agent or "").split("#", 1)[0].lower()
    lane = seat_url if seat_url is not None else seat_channel_url(seat)
    glob = global_url if global_url is not None else DB.webhook_url()

    if lane:
        return lane, f"{seat}'s own seat lane", ""
    if glob:
        return glob, "the GLOBAL channel", (
            f"no seat lane resolved for {seat!r} -- falling back to the GLOBAL channel. "
            f"If this was meant for his lane with this seat, that lane is missing "
            f"(discord_channel_<callsign>.url); saying so rather than posting quietly "
            f"into the wrong room.")
    return "", "", (
        "discord is not configured -- no seat lane and no global webhook. Nothing was "
        "sent, and this is a configuration state rather than a delivery failure.")
