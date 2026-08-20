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
    """The webhook of his lane with this seat — callsign-derived (registry-fed,
    never a second roster), vaulted by discord_setup. Empty when unconfigured."""
    base = str(agent or "").split("#", 1)[0].lower()
    try:
        from core.fleet import residents as _R
        cs = str((_R.get(base) or {}).get("callsign") or "").strip().lower()
    except Exception:                                                   # noqa: BLE001
        cs = ""
    if not cs:
        return ""
    from core.comm.secret_intake import secrets_dir
    try:
        return (secrets_dir() / f"discord_channel_{cs}.url").read_text(
            encoding="utf-8").strip()
    except OSError:
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


def _forward_global(msg: Dict[str, Any]) -> None:
    """The default global path: the seat speaks AS ITSELF (rung 2 of person-hood,
    Daniil 2026-08-18: 'show up as your own person in the chat'). Reuses the rooms
    transport, which already carries a username; the manual `discord test/send`
    verbs keep the bridge's who-in-body render untouched. Same laws as everywhere:
    allowlist inherited, redaction + clip via the rooms render, never raises."""
    if not DB.should_forward(msg):
        return
    url = DB.webhook_url()
    if not url:
        return
    try:
        who = ROOMS.persona(str(msg.get("frm") or ""))
        for part in ROOMS.render_room_parts(msg):
            ROOMS._default_post(url, part,
                                username=who["username"], avatar_url=who["avatar_url"])
    except Exception:                                                   # noqa: BLE001
        pass          # a listener never wounds the beat; the room half still tries


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
                msg = _decode(fields)
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
                        try:
                            who = ROOMS.persona(str(msg.get("frm") or ""))
                            for part in ROOMS.render_room_parts(msg):
                                ROOMS._default_post(lane, part,
                                                    username=who["username"],
                                                    avatar_url=who["avatar_url"])
                        except Exception:                               # noqa: BLE001
                            pass
                        client.hset(CURSOR_KEY, key, mid_s)
                        forwarded += 1
                        continue
                (post or _forward_global)(msg)
                (room_post or ROOMS.post_to_room)(msg)
                client.hset(CURSOR_KEY, key, mid_s)      # advance AFTER the attempt
                forwarded += 1
        except Exception:                                               # noqa: BLE001
            continue          # one bad stream must not starve the rest of the beat
    return BoundaryOutcome.done(ref=f"forwarded={forwarded}",
                                forwarded=forwarded, initialized=initialized)
