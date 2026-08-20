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

import asyncio
import json
import os
import subprocess
import sys
import threading
import time

NL = chr(10)          # newline, spelled out: an escape in this file got eaten once

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from typing import Optional

from core.comm.discord_inbound import (EarConfigError, build_config,
                                      credential_horizon_days,
                                      credential_warning, handle_message,
                                      spawn_credential_refusal,
                                      spawn_stillborn_reason)

_ROOT = Path(__file__).resolve().parents[1]
# How long a fresh seat must keep breathing before its sprout is proven honest.
# MEASURED, not guessed: an expired-OAuth death takes 15.8-16.9s (n=3, all exit 1) --
# the CLI spends that time trying to refresh before it gives up. A 5s window, which
# is what intuition first offered, would have called every one of those a live seat.
# That is far past discord.py's 10s heartbeat-blocked warning, so the long watch runs
# on a thread and speaks in a follow-up; only an INSTANT death rides the reply.
_SPAWN_PROOF_SECONDS = float(os.getenv("AKASHIC_SPAWN_PROOF_SECONDS") or 25.0)
_SPAWN_INSTANT_SECONDS = float(os.getenv("AKASHIC_SPAWN_INSTANT_SECONDS") or 2.0)
#: Vault names, not paths. Resolved through secret_intake.secrets_dir() so
#: AKASHIC_SECRETS_DIR redirects them -- a module-path constant is UNISOLATABLE, and a pin
#: one ambient file away from a real credential eventually does something real to a third
#: party (2026-08-19: a rooms pin minted a live thread in his server, using exactly this
#: shape). The lesson said the class was closed at the organ; this file was still an
#: instance, so it is closed here too.
BOT_TOKEN_NAME = "discord_bot.token"
SPAWN_TOKEN_NAME = "claude_oauth.token"


def _vault(name: str) -> str:
    """One credential, by allowlisted NAME, through the one vault function."""
    from core.comm.secret_intake import secrets_dir
    try:
        return (secrets_dir() / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _cli_logged_in(exe: str) -> Optional[bool]:
    """`claude auth status` as a tri-state: True, False, or None for 'could not tell'.

    Budget MEASURED at 0.29-0.31s over five runs -- 10s is generous, and instant beside the
    16s death it exists to prevent. Every failure mode collapses to None on purpose: an
    unanswerable probe must not masquerade as a 'no'."""
    try:
        r = subprocess.run([exe, "auth", "status"], capture_output=True, text=True,
                           timeout=10)
        return bool(json.loads(r.stdout).get("loggedIn"))
    except Exception:                                                   # noqa: BLE001
        return None


def _credential_horizon() -> Optional[float]:
    """Days left on the refresh token behind !spawn. Env-overridable so a pin can pin it."""
    path = Path(os.getenv("AKASHIC_CLAUDE_CREDENTIALS")
                or (Path.home() / ".claude" / ".credentials.json"))
    try:
        creds = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return credential_horizon_days(creds, int(time.time() * 1000))


# pid -> (Popen, log path), handed from the spawner to the watcher. Bounded by how
# many times he can type !spawn; entries are popped by the watcher that claims them.
_pending_spawns: dict = {}


def _spawn_said(log) -> str:
    """Whatever the child managed to say before it stopped. The child still holds this
    handle open, so read it, never move it -- and an unreadable log is silence, not an
    excuse to crash the gateway on top of a spawn that already failed."""
    try:
        return log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _token() -> str:
    v = os.getenv("AKASHIC_DISCORD_BOT_TOKEN")
    if v and v.strip():
        return v.strip()
    return _vault(BOT_TOKEN_NAME)


def main() -> int:
    token = _token()
    if not token:
        from core.comm.secret_intake import secrets_dir
        print(f"[discord-in] REFUSED: no bot token ({secrets_dir() / BOT_TOKEN_NAME}). "
              f"Developer portal -> Bot -> "
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

        The sprout is still not the harvest -- but it is now proof of LIFE, not proof
        of start. T365: on the day he could not reach anyone, this lever answered 🌱
        over a child that had already died on an expired OAuth session, and a receipt
        that is true about the syscall and false about the world is worse than none.
        Raise on a corpse; on_message's except-path turns that into his ⚠️."""
        import shutil
        import subprocess
        import time as _t
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("claude CLI not on PATH -- cannot spawn a fresh seat")
        # Preflight: a failure knowable at t=0 should not cost 16 seconds of his evening.
        vault_token = _vault(SPAWN_TOKEN_NAME)
        refusal = spawn_credential_refusal(vault_token, _cli_logged_in(exe))
        if refusal:
            print(f"[discord-in] SPAWN REFUSED (preflight): {refusal}", flush=True)
            raise RuntimeError(refusal)
        logs = _ROOT / "state" / "spawn-logs"
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / f"spawn-{int(_t.time())}.log"
        prompt = (f"You were spawned by the operator's !spawn from Discord. First run: "
                  f"py agent_cli.py boot claude --task \"{task[:200]}\" -- then do the "
                  f"task, land every result durably (commits by name, notes, handoff), "
                  f"and end with a wrap. Task, in his words: {task}")
        # A vaulted long-lived token, when present, is what the child authenticates with --
        # that is the whole cure: the seat we build stops inheriting the expiry date of the
        # session that built it. Absent one, the child falls back to the CLI's own login.
        env = os.environ.copy()
        if vault_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = vault_token
        with open(log, "w", encoding="utf-8") as fh:
            p = subprocess.Popen([exe, "-p", prompt], env=env,
                                 cwd=str(_ROOT), stdout=fh, stderr=fh,
                                 creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                 | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # An INSTANT death (missing exe, immediate refusal) is cheap to convict here,
        # and raising lets on_message's ⚠️ path carry it. The SLOW death cannot ride
        # this reply -- 16s of blocked event loop would starve the heartbeat -- so it
        # goes to the watcher below. The decidable half lives in core with the pins.
        try:
            code = p.wait(timeout=_SPAWN_INSTANT_SECONDS)
        except subprocess.TimeoutExpired:
            code = None                     # still breathing -- keep watching it
        if code is not None:
            reason = spawn_stillborn_reason(code, _spawn_said(log))
            if reason:
                print(f"[discord-in] SPAWN STILLBORN ({log.name}): {reason}", flush=True)
                raise RuntimeError(f"spawn died before it lived -- {reason}")
        _pending_spawns[p.pid] = (p, log)
        print(f"[discord-in] 🌱 spawned pid {p.pid} -> {log.name}: {task[:80]}", flush=True)
        return p.pid

    def _watch_spawn(pid: int, message) -> None:
        """The sprout receipt is a promise; this is the part that keeps it.

        Proof of life arrives ~16s late (measured), so it cannot ride the reply he
        already got. A daemon thread watches the child and, if it turns out to be a
        corpse, speaks into the same channel he typed in -- naming the cause, because
        "spawn failed" is the original silence with punctuation on it. A seat that
        keeps breathing says nothing: he does not need a second receipt for good news,
        and an unprompted all-clear is how a channel becomes noise."""
        rec = _pending_spawns.pop(pid, None)
        if rec is None:
            return
        proc, log = rec
        loop = asyncio.get_running_loop()

        async def _confess(text: str) -> None:
            try:
                await message.add_reaction("⚠️")
            except Exception:                                           # noqa: BLE001
                pass                        # the reaction is garnish; the words matter
            try:                            # 1900 < Discord's 2000: a confession that
                await message.reply(text[:1900], mention_author=False)   # clips is a
            except Exception as e:                                      # noqa: BLE001
                print(f"[discord-in] stillbirth notice UNDELIVERABLE ({type(e).__name__}"
                      f": {e}) -- it stands in this log only", flush=True)

        def _watch() -> None:
            try:
                code = proc.wait(timeout=_SPAWN_PROOF_SECONDS)
            except subprocess.TimeoutExpired:
                code = None
            reason = spawn_stillborn_reason(code, _spawn_said(log))
            if not reason:
                print(f"[discord-in] spawn {pid} still breathing after "
                      f"{_SPAWN_PROOF_SECONDS:.0f}s -- the sprout holds", flush=True)
                return
            print(f"[discord-in] SPAWN STILLBORN ({log.name}): {reason}", flush=True)
            horizon = credential_warning(_credential_horizon())
            try:
                asyncio.run_coroutine_threadsafe(
                    _confess(NL.join(filter(None, [
                        f"⚠️ that spawn never lived — {reason} (log: {log.name})",
                        horizon,          # the next expiry, while he is already looking
                    ]))),
                    loop)
            except Exception as e:                                      # noqa: BLE001
                print(f"[discord-in] could not reach the loop to confess: {e}", flush=True)

        threading.Thread(target=_watch, name=f"spawn-watch-{pid}", daemon=True).start()

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[discord-in] listening as {client.user} -- R1 allowlist is one id; "
              f"everyone else is weather", flush=True)
        warn = credential_warning(_credential_horizon())
        if warn:                        # the recovery path's own expiry, said BEFORE it bites
            print(f"[discord-in] CREDENTIAL: {warn}", flush=True)
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
        if out.get("spawned"):
            try:
                _watch_spawn(int(out["spawned"]), message)
            except (TypeError, ValueError):
                pass                        # no pid to watch is not a reason to die
        if out.get("acted"):
            room = f" -> ask {out['ask_id']}" if out.get("ask_id") else " -> global"
            print(f"[discord-in] heard the operator{room} (bus id {out['id']})", flush=True)

    client.run(token, log_handler=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
