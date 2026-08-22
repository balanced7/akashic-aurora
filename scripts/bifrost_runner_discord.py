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

# THE RECEIPT MUST NOT KILL THE LISTENER (2026-08-19, measured): this runner prints 🌱/⚠️
# and relays his words, but a Windows console hands Python cp1252 stdout -- so the FIRST
# !spawn raised UnicodeEncodeError inside the handler, which the on_message except-path
# reported to him as "send FAILED" on a spawn that had actually started. A door whose
# CONFESSION is unprintable confesses nothing. Force UTF-8 on our own streams rather than
# trusting the launch environment (a launcher flag is one forgotten env away from this
# recurring); errors="replace" so an exotic glyph degrades to a mark instead of a crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                   # noqa: BLE001
        pass                    # older/odd streams: keep going, the bus is the record

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


#: The gateway's own liveness identity. NOT "daniil" -- it SPEAKS as the operator on the bus (R3)
#: but claiming his liveness id would report the operator alive whenever a socket is up.
GATEWAY_AGENT_ID = "discord"

#: Resting phase must be one of liveness.IDLE_PHASES, or a gateway quietly waiting for a message
#: pages as a wedge after BIFROST_WEDGE_SECONDS. An observability feature that manufactures false
#: alarms gets switched off, and then we are blind again for a worse reason.
RESTING_PHASE = "online"


def _heartbeat_seconds() -> float:
    """Derived from WORKLIVE_TTL, never chosen. The TTL's own comment sizes it for a ~5s refresh
    'so a live record never flaps'; a second number here could only disagree with the first."""
    try:
        from core.comm.liveness import WORKLIVE_TTL
        return max(1.0, float(WORKLIVE_TTL) / 9.0)
    except Exception:                                                   # noqa: BLE001
        return 5.0


HEARTBEAT_S = _heartbeat_seconds()


def gateway_log_path():
    """Where the gateway's own words go, so they outlive whatever launched it. 2026-08-19: a
    harness wrapper exited 127 while the detached service kept serving, and its stdout went
    with the wrapper -- the bridge was up and unreadable."""
    return Path(os.getenv("AKASHIC_DISCORD_GATEWAY_LOG")
                or (_ROOT / "state" / "logs" / "discord-gateway.log"))


def beat(wl, phase: str = "", detail: str = "") -> None:
    """Stamp the gateway's liveness record. FAIL-OPEN by contract, inherited from liveness._flush
    ('observability must never wedge the path it observes'): a dead bus costs the signal, never
    the bridge."""
    try:
        if phase:
            wl.set(phase, detail)
        else:
            wl.refresh()
    except Exception:                                                   # noqa: BLE001
        pass


class Tee:
    """Write to the live stream AND a durable file. utf-8 explicitly, because this module prints
    a sprout and a warning glyph and a cp1252 handle would crash the gateway on its own receipt --
    which is how an observability feature causes an outage."""

    def __init__(self, stream, path):
        self._stream = stream
        self._fh = None
        try:
            dest = Path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(dest, "a", encoding="utf-8", errors="replace")
        except Exception:                                               # noqa: BLE001
            self._fh = None          # lose the record, keep the bridge

    def write(self, text):
        try:
            self._stream.write(text)
        except Exception:                                               # noqa: BLE001
            pass
        if self._fh is not None:
            try:
                self._fh.write(text)
                self._fh.flush()
            except Exception:                                           # noqa: BLE001
                pass
        return len(text or "")

    def flush(self):
        for target in (self._stream, self._fh):
            try:
                if target is not None:
                    target.flush()
            except Exception:                                           # noqa: BLE001
                pass

    def isatty(self):
        try:
            return bool(self._stream.isatty())
        except Exception:                                               # noqa: BLE001
            return False


def _token() -> str:
    v = os.getenv("AKASHIC_DISCORD_BOT_TOKEN")
    if v and v.strip():
        return v.strip()
    return _vault(BOT_TOKEN_NAME)


def main() -> int:
    # Durable log before anything can refuse: a REFUSED line nobody can read is the same blind
    # spot as a crash nobody can read.
    sys.stdout = Tee(sys.stdout, gateway_log_path())
    from core.comm import liveness as _liveness
    wl = _liveness.worklive(GATEWAY_AGENT_ID)
    beat(wl, RESTING_PHASE, "gateway starting")
    print(f"[discord-in] log -> {gateway_log_path()}  |  liveness id "
          f"{GATEWAY_AGENT_ID}, beat {HEARTBEAT_S:.0f}s", flush=True)
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

    def _pulse():
        """Keep the liveness record fresh so ABSENCE is detectable. A daemon thread: it must
        never be the reason the gateway outlives its usefulness."""
        while True:
            time.sleep(HEARTBEAT_S)
            beat(wl)

    threading.Thread(target=_pulse, name="discord-gateway-beat", daemon=True).start()

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    # ---- T380: the comms-stage reaction ladder (📨 landed -> 🤔 opened ->
    # ✅ answered-strict / 💬 replied-unlinked / ⚠️ dead). The tracker is the
    # pure pinned half (core/comm/discord_ladder.py); this loop applies its ops
    # to the operator's original messages. Reaction failures stay garnish-never-
    # wounds; ops are staggered (<=3 per tick) against the per-route reaction
    # rate limit (Heimdall's fence counter c3); a deleted message evicts its
    # entry (c4). In-process state: a gateway restart drops in-flight ladder
    # entries -- documented T380 residual; the relay 📨 never depends on this.
    from collections import deque as _deque
    _ladder_msgs: dict = {}
    _ladder_ops = _deque()
    _LADDER_EMOJI = {"thinking": "🤔", "answered": "✅", "replied": "💬",
                     "dead": "⚠️"}

    async def _ladder_loop():
        from core.comm.discord_ladder import LadderTracker
        tracker = LadderTracker(client=bus._client, ns=bus.ns, operator="daniil")
        client._ladder_tracker = tracker           # on_message tracks through this
        while True:
            await asyncio.sleep(4)
            try:
                _ladder_ops.extend(tracker.poll())
            except Exception as e:                                      # noqa: BLE001
                print(f"[discord-in] ladder poll failed ({type(e).__name__}: {e})",
                      flush=True)
                continue
            for _ in range(min(3, len(_ladder_ops))):
                op = _ladder_ops.popleft()
                msg = _ladder_msgs.get(op["discord_msg_id"])
                if msg is None:
                    continue                # pre-restart entry: residual, drop it
                emoji = _LADDER_EMOJI.get(op["op"])
                if not emoji:
                    continue
                try:
                    if op["op"] in ("answered", "replied", "dead"):
                        try:
                            await msg.remove_reaction("🤔", client.user)
                        except Exception:                               # noqa: BLE001
                            pass            # removing our own 🤔 is best-effort
                        _ladder_msgs.pop(op["discord_msg_id"], None)
                    await msg.add_reaction(emoji)
                except discord.NotFound:
                    _ladder_msgs.pop(op["discord_msg_id"], None)  # deleted: evict
                except Exception as e:                                  # noqa: BLE001
                    print(f"[discord-in] ladder react failed on {op['op']} "
                          f"({type(e).__name__}: {e}) -- delivery stands, the "
                          f"emote does not", flush=True)

    @client.event
    async def on_ready():
        print(f"[discord-in] listening as {client.user} -- R1 allowlist is one id; "
              f"everyone else is weather", flush=True)
        beat(wl, RESTING_PHASE, f"listening as {client.user}")
        warn = credential_warning(_credential_horizon())
        if warn:                        # the recovery path's own expiry, said BEFORE it bites
            print(f"[discord-in] CREDENTIAL: {warn}", flush=True)
        try:
            await client.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching,
                                          name="the Bifrost"))
        except Exception:                                               # noqa: BLE001
            pass                                   # presence is garnish, never load-bearing
        # T380: one ladder loop per process (on_ready refires on RESUME -- guard)
        if not getattr(client, "_ladder_started", False):
            client._ladder_started = True
            asyncio.create_task(_ladder_loop())

    @client.event
    async def on_message(message):
        # gateway-side echo-guard: the feed's own webhook posts land here too.
        if message.author.bot or message.webhook_id:
            return
        # raw content carries mention TOKENS (<@&roleid>); translate them to the
        # readable @Name before the words ride the bus — verbatim in spirit, not
        # in snowflakes.
        beat(wl, "handling", f"msg from {message.author}")
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
            # A landed-receipt (📨) on a dead send would be the T149 lie with an
            # emoji on it -- and ✅ is the ladder's word for ANSWERED now (T380).
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
        beat(wl, RESTING_PHASE, "idle")
        if out.get("spawned"):
            try:
                _watch_spawn(int(out["spawned"]), message)
            except (TypeError, ValueError):
                pass                        # no pid to watch is not a reason to die
        # T380: enter the ladder -- directed operator relays only (ambient
        # broadcasts and guest words get their landed emote and stop there).
        # reversed(): out["id"] is the LAST target's stream id, so that agent
        # leads the list the tracker resolves the identity sha from.
        try:
            _t = getattr(client, "_ladder_tracker", None)
            if (_t is not None and out.get("acted") and out.get("id")
                    and out.get("to") and not out.get("guest")):
                if _t.track(str(out["id"]),
                            to_agents=[str(a) for a in reversed(out["to"])],
                            channel_id=str(message.channel.id),
                            discord_msg_id=str(message.id)):
                    _ladder_msgs[str(message.id)] = message
        except Exception as e:                                          # noqa: BLE001
            print(f"[discord-in] ladder track failed ({type(e).__name__}: {e})",
                  flush=True)
        if out.get("acted"):
            room = f" -> ask {out['ask_id']}" if out.get("ask_id") else " -> global"
            if out.get("guest"):
                # The guest's snowflake is printed ON PURPOSE. It is the single
                # fact an operator needs to promote a visitor, and making him hunt
                # it through Developer Mode is friction the ear can just delete --
                # a visitor SAYING HELLO is the most natural way to hand it over.
                # Printing an id grants nothing: R3 still holds, reach not authority.
                print(f"[discord-in] heard a GUEST {message.author} "
                      f"id={message.author.id} (authority: none){room} "
                      f"(bus id {out['id']})", flush=True)
            else:
                who = (out.get("speaker") or "the operator")
                print(f"[discord-in] heard {who}{room} (bus id {out['id']})",
                      flush=True)
        elif out.get("reason"):
            # A refused message used to vanish. Silence at a gate is how a visitor
            # concludes the house is dead -- say what was refused and whose it was.
            print(f"[discord-in] REFUSED {message.author} id={message.author.id}: "
                  f"{out['reason']}", flush=True)

    client.run(token, log_handler=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
