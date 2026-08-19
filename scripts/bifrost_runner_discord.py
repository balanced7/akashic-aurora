"""Discord inbound gateway shell — a thin discord.py loop around core/comm/discord_inbound.py.

Runner family member (wait -> bridge -> reply), auto-enumerated as a wiring entry
point by the bifrost_runner_* rule. Everything decidable lives in the core module
where the pins are; this file owns exactly three things the pins must never touch:
the TOKEN, the SOCKET, and the event loop.

Gateway-side half of the echo-guard: webhook and bot authors are skipped before the
core logic ever sees them — the feed's own posts arrive on this socket too, and a
fleet that hears itself narrate is one bad conditional from a conversation with
itself at 100k messages a second (the tin droplets at least make light).

Run:  py scripts/bifrost_runner_discord.py            (refuses loudly if unconfigured)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from core.comm.discord_inbound import EarConfigError, build_config, handle_message

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
        print(f"[discord-in] REFUSED: no bot token ({TOKEN_FILE}). Developer portal -> Bot -> "
              f"Reset Token -> save as that file's one line.", flush=True)
        return 2
    try:
        cfg = build_config()
    except EarConfigError as e:
        print(f"[discord-in] REFUSED: {e}", flush=True)
        return 2

    import discord
    from core.comm.bus import Bus

    bus = Bus("daniil")          # inbound speaks AS the operator, or not at all (R3)

    def _spawn(task: str):
        """!spawn's lever: a fresh claude session, detached, logging to its own file.
        The promise is process START (🌱); the sprout is not the harvest."""
        import shutil
        import subprocess
        import time as _t
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("claude CLI not on PATH -- cannot spawn a fresh seat")
        logs = _ROOT / "state" / "spawn-logs"
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / f"spawn-{int(_t.time())}.log"
        prompt = (f"You were spawned by the operator's !spawn from Discord. First run: "
                  f"py agent_cli.py boot claude --task \"{task[:200]}\" -- then do the "
                  f"task, land every result durably (commits by name, notes, handoff), "
                  f"and end with a wrap. Task, in his words: {task}")
        with open(log, "w", encoding="utf-8") as fh:
            p = subprocess.Popen([exe, "-p", prompt],
                                 cwd=str(_ROOT), stdout=fh, stderr=fh,
                                 creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                 | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        print(f"[discord-in] 🌱 spawned pid {p.pid} -> {log.name}: {task[:80]}", flush=True)
        return p.pid

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[discord-in] listening as {client.user} -- R1 allowlist is one id; "
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
        # raw content carries mention TOKENS (<@&roleid>); translate them to the
        # readable @Name before the words ride the bus — verbatim in spirit, not
        # in snowflakes.
        readable = message.content
        for r in message.role_mentions:
            readable = readable.replace(f"<@&{r.id}>", f"@{r.name}")
        for u in message.mentions:
            readable = readable.replace(f"<@{u.id}>", f"@{u.display_name}")
        reactions = []
        try:
            out = handle_message(
                cfg,
                author_id=str(message.author.id),
                author_name=str(message.author),
                channel_id=str(message.channel.id),
                content=readable,
                bus=bus,
                react=lambda emoji: reactions.append(emoji),
                role_mentions=[r.name for r in message.role_mentions],
                spawner=_spawn)
        except Exception as e:                                          # noqa: BLE001
            # a dead bus send must be VISIBLE at both ends: loud here, ⚠️ there.
            # A ✅ on a dead send would be the T149 lie with an emoji on it.
            print(f"[discord-in] send FAILED ({type(e).__name__}: {e})", flush=True)
            try:
                await message.add_reaction("⚠️")
            except Exception:                                           # noqa: BLE001
                pass
            return
        for emoji in reactions:
            try:
                await message.add_reaction(emoji)
            except Exception:                                           # noqa: BLE001
                print("[discord-in] heard (bus accepted) but the receipt reaction failed "
                      "-- delivery stands, the checkmark does not", flush=True)
        if out.get("acted"):
            room = f" -> ask {out['ask_id']}" if out.get("ask_id") else " -> global"
            print(f"[discord-in] heard the operator{room} (bus id {out['id']})", flush=True)

    client.run(token, log_handler=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
