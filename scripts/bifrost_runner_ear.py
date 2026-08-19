"""The ear's gateway shell — a thin discord.py loop around core/comm/discord_ear.py.

Runner family member (wait -> bridge -> reply), auto-enumerated as a wiring entry
point by the bifrost_runner_* rule. Everything decidable lives in the core module
where the pins are; this file owns exactly three things the pins must never touch:
the TOKEN, the SOCKET, and the event loop.

Gateway-side half of the echo-guard: webhook and bot authors are skipped before the
core logic ever sees them — the feed's own posts arrive on this socket too, and a
fleet that hears itself narrate is one bad conditional from a conversation with
itself at 100k messages a second (the tin droplets at least make light).

Run:  py scripts/bifrost_runner_ear.py            (refuses loudly if unconfigured)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from core.comm.discord_ear import EarConfigError, build_config, handle_message

_ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = _ROOT / ".secrets" / "discord_bot.token"


def _token() -> str:
    v = os.getenv("AKASHIC_DISCORD_BOT_TOKEN")
    if v and v.strip():
        return v.strip()
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def main() -> int:
    token = _token()
    if not token:
        print(f"[ear] REFUSED: no bot token ({TOKEN_FILE}). Developer portal -> Bot -> "
              f"Reset Token -> save as that file's one line.", flush=True)
        return 2
    try:
        cfg = build_config()
    except EarConfigError as e:
        print(f"[ear] REFUSED: {e}", flush=True)
        return 2

    import discord
    from core.comm.bus import Bus

    bus = Bus("daniil")          # the ear speaks AS the operator, or not at all (R3)

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[ear] listening as {client.user} -- R1 allowlist is one id; "
              f"everyone else is weather", flush=True)
        try:
            await client.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching,
                                          name="the Bifrost"))
        except Exception:                                               # noqa: BLE001
            pass                                   # presence is garnish, never load-bearing

    @client.event
    async def on_message(message):
        # gateway-side echo-guard: the feed's own webhook posts land here too.
        if message.author.bot or message.webhook_id:
            return
        reactions = []
        try:
            out = handle_message(
                cfg,
                author_id=str(message.author.id),
                author_name=str(message.author),
                channel_id=str(message.channel.id),
                content=message.content,
                bus=bus,
                react=lambda emoji: reactions.append(emoji))
        except Exception as e:                                          # noqa: BLE001
            # a dead bus send must be VISIBLE at both ends: loud here, ⚠️ there.
            # A ✅ on a dead send would be the T149 lie with an emoji on it.
            print(f"[ear] send FAILED ({type(e).__name__}: {e})", flush=True)
            try:
                await message.add_reaction("⚠️")
            except Exception:                                           # noqa: BLE001
                pass
            return
        for emoji in reactions:
            try:
                await message.add_reaction(emoji)
            except Exception:                                           # noqa: BLE001
                print("[ear] heard (bus accepted) but the receipt reaction failed "
                      "-- delivery stands, the checkmark does not", flush=True)
        if out.get("acted"):
            room = f" -> ask {out['ask_id']}" if out.get("ask_id") else " -> global"
            print(f"[ear] heard the operator{room} (bus id {out['id']})", flush=True)

    client.run(token, log_handler=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
