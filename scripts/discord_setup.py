"""One-shot Discord server setup — runs under the admin grant Daniil flipped on his way
to work (2026-08-19, verbatim: "admin is granted! ... I just want us to be able to
iterate quickly").

IDEMPOTENT: every create checks for an existing thing by name first; re-running is a
no-op that prints what already stands. Everything it mints is recorded: roles and
channels into state/coord/discord_seat_channels.json, webhooks into the VAULT through
the secret_intake door — the first credentials this house ever delivered to itself.

Creates:
  - three mentionable roles in family colors (Vandor/Amber, Heimdall/Onyx, Navi/Jade)
  - #aurora-rooms as a FORUM channel (falls back to text if the guild lacks Community;
    the mode is recorded so the router knows which physics apply)
  - #vandor, #heimdall, #navi seat channels under an "Akashic Aurora" category —
    each a bidirectional lane: seat questions land there, his replies route back
  - a webhook per created channel, saved via the vault door

Run:  py scripts/discord_setup.py           (add --dry-run to only look)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from core.comm import secret_intake as VAULT

_ROOT = Path(__file__).resolve().parents[1]
API = "https://discord.com/api/v10"
SEATS_FILE = _ROOT / "state" / "coord" / "discord_seat_channels.json"

ROLES = [("Vandor", 0xE8A13C), ("Heimdall", 0x2B2B33), ("Navi", 0x27A17A)]
SEAT_CHANNELS = [("vandor", "claude"), ("heimdall", "deepseek"), ("navi", "kimi")]


def _token() -> str:
    v = os.getenv("AKASHIC_DISCORD_BOT_TOKEN")
    if v and v.strip():
        return v.strip()
    return (_ROOT / ".secrets" / "discord_bot.token").read_text(encoding="utf-8").strip()


class D:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bot {token}"

    def get(self, path):
        r = self.s.get(API + path, timeout=15); r.raise_for_status(); return r.json()

    def post(self, path, payload):
        r = self.s.post(API + path, json=payload, timeout=15)
        r.raise_for_status(); return r.json()


def main() -> int:
    dry = "--dry-run" in sys.argv
    d = D(_token())

    guilds = d.get("/users/@me/guilds")
    if not guilds:
        print("[setup] the bot is in no guild -- invite it first"); return 2
    g = guilds[0]
    gid = g["id"]
    print(f"[setup] guild: {g['name']} ({gid})"
          + (" [COMMUNITY]" if "COMMUNITY" in g.get("features", []) else " [no community]"))
    forum_ok = "COMMUNITY" in g.get("features", [])

    # ---- roles (idempotent by name) ---------------------------------------------
    have_roles = {r["name"]: r for r in d.get(f"/guilds/{gid}/roles")}
    for name, color in ROLES:
        if name in have_roles:
            print(f"[setup] role {name}: already stands")
            continue
        if dry:
            print(f"[setup] role {name}: WOULD create"); continue
        d.post(f"/guilds/{gid}/roles",
               {"name": name, "color": color, "mentionable": True})
        print(f"[setup] role {name}: created, mentionable, #{color:06x}")

    # ---- channels ----------------------------------------------------------------
    chans = d.get(f"/guilds/{gid}/channels")
    by_name = {c["name"]: c for c in chans}

    def ensure_channel(name: str, ctype: int, parent: str | None = None):
        if name in by_name:
            print(f"[setup] #{name}: already stands")
            return by_name[name]
        if dry:
            print(f"[setup] #{name}: WOULD create (type {ctype})")
            return None
        payload = {"name": name, "type": ctype}
        if parent:
            payload["parent_id"] = parent
        c = d.post(f"/guilds/{gid}/channels", payload)
        by_name[name] = c
        print(f"[setup] #{name}: created (type {ctype})")
        return c

    cat = ensure_channel("akashic-aurora", 4)
    cat_id = cat["id"] if cat else None

    # the rooms channel: forum where possible, text where not — the MODE is recorded
    # because the router's create-thread physics differ (forum: webhook thread_name;
    # text: bot-created threads). Honest state beats a silent wrong assumption.
    rooms_type = 15 if forum_ok else 0
    rooms = ensure_channel("aurora-rooms", rooms_type, cat_id)

    registry: dict = {"mode": ("forum" if forum_ok else "text"), "channels": {}}
    for chan_name, agent in SEAT_CHANNELS:
        c = ensure_channel(chan_name, 0, cat_id)
        if c:
            registry["channels"][c["id"]] = agent

    # ---- webhooks, delivered straight to the vault -------------------------------
    def ensure_webhook(channel: dict, vault_target: str):
        if not channel:
            return
        hooks = d.get(f"/channels/{channel['id']}/webhooks")
        ours = next((h for h in hooks if h.get("token")), None)
        if not ours:
            if dry:
                print(f"[setup] webhook on #{channel['name']}: WOULD create"); return
            ours = d.post(f"/channels/{channel['id']}/webhooks",
                          {"name": "Akashic Aurora"})
        url = f"https://discord.com/api/webhooks/{ours['id']}/{ours['token']}"
        receipt = VAULT.save_secret(vault_target, url)
        print(f"[setup] webhook on #{channel['name']}: in the vault "
              f"({receipt['bytes']}B -> .secrets/{vault_target})")

    ensure_webhook(rooms, "discord_forum_webhook.url")
    for chan_name, agent in SEAT_CHANNELS:
        c = by_name.get(chan_name)
        if c:
            ensure_webhook(c, f"discord_channel_{chan_name}.url")

    if not dry:
        SEATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEATS_FILE.write_text(json.dumps(registry, indent=1), encoding="utf-8")
        print(f"[setup] seat-channel registry written ({len(registry['channels'])} lanes, "
              f"rooms mode: {registry['mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
