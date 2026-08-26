"""Outbound room router — each ask/breakout becomes a Discord thread.

Daniil, off to work 2026-08-18, verbatim: "bifrost have a discord native expression that I
can chat in, with global chat and each specific breakout or ask being visible as chatrooms!"
Design: research/in-flight/discord-native-rooms-design-2026-08-18.md. The CHAT-IN half is
phase 2 and lives behind the R1-R3 identity gate; this module is OUTBOUND ONLY and pin P5
(tests/test_discord_rooms_pins.py) twins the bridge's no-inbound-door guard.

Neighbour law: this module copies discord_bridge's GUARDS, not just its shape — never raise
into a bus caller, visible redaction, allowlist inherited (a second hand-kept kind list is
the fork this repo keeps paying for), absent-is-not-broken, injectable transport so every
pin runs offline.

TRANSPORT FACT the whole design leans on: a FORUM-channel webhook creates a thread by
posting with `thread_name`, and posts into an existing one via `?thread_id=` — so per-ask
rooms need NO bot, and a webhook URL stays write-only (it cannot read, enumerate, or act).

REGISTRY COHERENCE, stated: last-writer-wins on the JSON registry. Acceptable here because
the worst race outcome is a twin thread (annoying, harmless), never lost mail — the bus
remains the substrate of record and every clipped body carries its bifrost-fetch address.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.outcome import BoundaryOutcome
from core.comm.discord_bridge import (DISCORD_MAX, _content_str, chunk, redact,
                                       should_forward)

_ROOT = Path(__file__).resolve().parents[2]

#: T365: this credential was previously two things — a module-path constant (the dangerous
#: class AKASHIC_SECRETS_DIR can't redirect) AND a dead name (forum_url() below reads it
#: through secrets_dir() directly). The constant is removed; the ONE resolution rule is
#: forum_url()'s secrets_dir()/env-first path, documented there.

#: ask_id -> {thread_id, title, created}. A thread id is a NEW address dialect and is
#: registered in the T362 census from birth — unrecorded addresses are how dialects fracture.
REG_FILE = _ROOT / "state" / "coord" / "discord_rooms.json"

#: The surface Daniil reads teaches BOTH names on every line (Heimdall's name-collision
#: scan, Species A) -- and reads the RESIDENTS REGISTRY, never a second hand-kept table
#: (Heimdall's drift warning, honored 2026-08-18 when the map became load-bearing).
#: Avatars are the designation made visible: family = disc, team = ring
#: (scripts/generators/gen_avatars.py); a seat's SELF-SELECTED emoji rides the username.
AVATAR_BASE = "https://raw.githubusercontent.com/balanced7/akashic-aurora/master/assets/avatars"

#: agent -> {"icon": <self-selected emoji>, ...}. Written only on a seat's OWN pick --
#: assignment is not selection, and an empty entry renders no icon rather than a guess.
ICONS_FILE = _ROOT / "state" / "coord" / "discord_personas.json"


def _icons() -> Dict[str, Any]:
    try:
        return json.loads(ICONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def persona(frm: str) -> Dict[str, Optional[str]]:
    """username + avatar for a seat, from the registry + its own icon pick.
    Ratification names the resident; placement separately permits its generated face."""
    agent = str(frm or "").strip()
    base = agent.split("#", 1)[0].lower()          # incarnations wear the agent's face
    try:
        from core.fleet import residents as _R
        rec = _R.get(base)
        placed = _R.current_placement(base)
    except Exception:                                                   # noqa: BLE001
        rec, placed = None, None
    if not rec:
        return {"username": agent or "?", "avatar_url": None}
    cs = str(rec.get("callsign") or base)
    icon = str((_icons().get(base) or {}).get("icon") or "").strip()
    name = f"{icon} {cs} ({base})".strip()
    avatar_url = f"{AVATAR_BASE}/{cs.lower()}.png" if placed else None
    return {"username": name, "avatar_url": avatar_url}


def forum_url() -> str:
    """The rooms webhook, or "" when rooms are simply off (absent is not broken).
    Resolved through the VAULT's own secrets_dir() — one resolution rule for every
    credential (2026-08-19: a pin reading this file directly reached the REAL
    webhook and minted a live thread in his server; the vault's env override is
    what lets isolation actually isolate)."""
    v = os.getenv("AKASHIC_DISCORD_FORUM_WEBHOOK")
    if v and v.strip():
        return v.strip()
    from core.comm.secret_intake import secrets_dir
    try:
        return (secrets_dir() / "discord_forum_webhook.url").read_text(
            encoding="utf-8").strip()
    except OSError:
        return ""


def _reg_path() -> Path:
    return Path(os.getenv("AKASHIC_DISCORD_ROOMS_REGISTRY") or REG_FILE)


#: setup-written: {"mode": forum|text, "rooms_channel_id": ..., "channels": {...}}.
#: Akashic Labs carries no Community flag (setup receipt 2026-08-19), so rooms run
#: TEXT mode there: threads are minted by the BOT's rest call and the webhook only
#: ever posts INTO them — thread_name on a non-forum webhook is a 400.
SEATS_FILE = _ROOT / "state" / "coord" / "discord_seat_channels.json"


def _seats_registry() -> Dict[str, Any]:
    path = Path(os.getenv("AKASHIC_DISCORD_SEATS_REGISTRY") or SEATS_FILE)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mode": "forum", "channels": {}}


def _default_create_thread(name: str) -> Optional[str]:
    """TEXT-mode thread mint via the bot token (admin-granted). Isolated so pins
    run offline; returns the thread id or None (and None is a refusal upstream —
    an unregistered room would mint twins forever)."""
    import requests
    reg = _seats_registry()
    channel_id = str(reg.get("rooms_channel_id") or "")
    if not channel_id:
        return None
    from core.comm.secret_intake import secrets_dir
    try:
        token = os.getenv("AKASHIC_DISCORD_BOT_TOKEN") or \
            (secrets_dir() / "discord_bot.token").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    r = requests.post(
        f"https://discord.com/api/v10/channels/{channel_id}/threads",
        headers={"Authorization": f"Bot {token}"},
        json={"name": name[:100], "type": 11, "auto_archive_duration": 10080},
        timeout=15)
    r.raise_for_status()
    return str(r.json().get("id") or "") or None


def _load_reg() -> Dict[str, Any]:
    try:
        return json.loads(_reg_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_reg(reg: Dict[str, Any]) -> None:
    p = _reg_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, indent=1), encoding="utf-8")


def _render_room(msg: Dict[str, Any]) -> str:
    """Body + kind tag; the author line is carried by the webhook username instead of
    markdown (rooms show the speaker natively — that is what 'native expression' buys).
    Single-part render kept for callers that want one string; post_to_room and the feed
    iterate render_room_parts() for the multi-post law (T364)."""
    return render_room_parts(msg)[0]


def render_room_parts(msg: Dict[str, Any]) -> list:
    """One or more room posts for a message: the kind tag rides every part, and a body
    over the cap becomes N whole-line parts (chunk()) — no truncation, no shell handle.
    T364: a `bifrost-fetch --get` tail is a command Daniil cannot run from a phone, so
    a clip was the defect; N parts is the fix."""
    kind = str(msg.get("kind") or "?")
    body = redact(_content_str(msg.get("content")))
    head = f"`{kind}`\n"
    if not body:
        return [head.rstrip("\n")]
    if len(head) + len(body) <= DISCORD_MAX:
        return [head + body]
    parts = chunk(body, max_len=DISCORD_MAX - len(head))
    return [head + p for p in parts]


def _default_post(url: str, content: str, *, thread_id: Optional[str] = None,
                  thread_name: Optional[str] = None,
                  username: Optional[str] = None,
                  avatar_url: Optional[str] = None) -> Optional[str]:
    """The only network call in this module, isolated so every pin runs offline.
    Returns the thread id Discord minted (wait=true => the created forum post's
    channel_id IS the thread id), or None when the response carries none."""
    import requests
    params: Dict[str, str] = {"wait": "true"}
    if thread_id:
        params["thread_id"] = str(thread_id)
    payload: Dict[str, Any] = {"content": content}
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if thread_name:
        payload["thread_name"] = thread_name
    r = requests.post(url, params=params, json=payload, timeout=10)
    r.raise_for_status()
    try:
        data = r.json() if r.text else {}
    except ValueError:
        data = {}
    ch = data.get("channel_id")
    return str(ch) if ch else None


def post_to_room(msg: Dict[str, Any], *, url: Optional[str] = None, force: bool = False,
                 post: Optional[Callable[..., Optional[str]]] = None) -> BoundaryOutcome:
    """Route one message to its ask's room, creating the room on first contact.

    NEVER RAISES — a Discord outage must not raise into a bus caller, and must not
    pretend success either (the T149 law, carried from the bridge)."""
    if not force and not should_forward(msg):
        return BoundaryOutcome.failed(
            f"kind {str(msg.get('kind') or '?')!r} is not on the forward allowlist — the "
            f"rooms inherit the bridge's list; the firehose stays out of the house")

    meta = msg.get("meta") or {}
    ask_id = str(meta.get("ask_id") or meta.get("reply_id") or "").strip()
    if not ask_id:
        return BoundaryOutcome.failed(
            "no ask/reply id on this message — that is the global feed's job, not a room's")

    target = forum_url() if url is None else url
    if not target:
        return BoundaryOutcome.failed(
            "discord rooms not configured — set AKASHIC_DISCORD_FORUM_WEBHOOK or write "
            ".secrets/discord_forum_webhook.url. A configuration state, not a delivery "
            "failure: rooms are opt-in and most seats will never set them.")

    reg = _load_reg()
    known = reg.get(ask_id) or {}
    thread_id = known.get("thread_id")
    thread_name = None
    minted_by_bot = None
    if not thread_id:
        title = str(meta.get("title") or "").strip()
        room_name = (f"{ask_id} — {title}" if title else ask_id)[:100]
        if _seats_registry().get("mode") == "text":
            try:
                minted_by_bot = _default_create_thread(room_name)
            except Exception as e:                                      # noqa: BLE001
                return BoundaryOutcome.failed(
                    f"text-mode thread mint failed ({type(e).__name__}: {e}) — "
                    f"the bus is unaffected")
            if not minted_by_bot:
                return BoundaryOutcome.failed(
                    "text-mode room needs a bot-minted thread and none was "
                    "minted (no rooms_channel_id or no token) — refusing "
                    "beats minting twins")
            thread_id = minted_by_bot
        else:
            thread_name = room_name

    who = persona(str(msg.get("frm") or ""))
    parts = render_room_parts(msg)
    minted = None
    try:
        for content in parts:
            minted = (post or _default_post)(
                target, content, thread_id=thread_id, thread_name=thread_name,
                username=who["username"], avatar_url=who["avatar_url"])
    except Exception as e:                                              # noqa: BLE001
        return BoundaryOutcome.failed(
            f"discord room post failed ({type(e).__name__}: {e}) — the bus is unaffected; "
            f"this router is a listener and never blocks a send")

    if thread_name or minted_by_bot:
        tid = str(minted_by_bot or minted or "")
        if not tid:
            return BoundaryOutcome.failed(
                "room post landed but no thread id came back — room NOT registered, "
                "so the next post would mint a twin. Check the webhook targets a FORUM "
                "channel and wait=true is honored.")
        reg[ask_id] = {"thread_id": tid,
                       "title": str(thread_name or f"{ask_id} (text-mode)"),
                       "created": str(msg.get("id") or "")}
        _save_reg(reg)

    return BoundaryOutcome.done(ref=str(msg.get("id") or ""),
                                chars=sum(len(p) for p in parts))
