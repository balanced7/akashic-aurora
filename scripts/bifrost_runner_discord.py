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

# T150/T152 runner-family law (regressed out in the ear-v2 rewrite, caught by the
# census guards via the 2026-08-22 baseline delta): line-buffered utf-8 streams
# with replace, guarded -- a stream that cannot be reconfigured (pytest capture,
# an exotic wrapper) degrades to old behaviour, never takes the ear down. This is
# also the fix for the lazy-banner symptom (ARMED lines sitting unflushed in a
# block buffer) that bit the operator's seat twice today.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

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
                                      spawn_closing_report,
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
#: How long a spawned seat may work in silence before its silence is itself reported.
#: The proof window (25s) answers "did it live"; this answers "did it ever say anything",
#: which is the question Daniil was actually asking on 2026-08-24 and did not get back.
_SPAWN_REPORT_DEADLINE = float(os.getenv("AKASHIC_SPAWN_REPORT_DEADLINE") or 600.0)
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
#: pid -> the launch note for a SEAT launch (url + whether the lever is drilled). It is
#: delivered to the channel immediately rather than left in this log -- "wrote it to a file
#: nobody reads" is the exact defect this day was spent closing.
_launch_notes: dict = {}


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

    # T160: the ear says WHO IT IS before anything it writes can be attributed --
    # the bus below speaks AS the operator (R3), which is exactly why the SEAT
    # identity must be stamped separately or every record reads 'unknown'.
    from core.comm.runner_lib import set_seat_agent
    set_seat_agent("discord")
    bus = Bus("daniil")          # inbound speaks AS the operator, or not at all (R3)

    def _spawn(task: str, mode: str = "default"):
        """!spawn's lever: a fresh claude session, detached, logging to its own file.

        The sprout is still not the harvest -- but it is now proof of LIFE, not proof
        of start. T365: on the day he could not reach anyone, this lever answered 🌱
        over a child that had already died on an expired OAuth session, and a receipt
        that is true about the syscall and false about the world is worse than none.
        Raise on a corpse; on_message's except-path turns that into his ⚠️.

        mode (2026-08-23, spawn GRANT):
          default    -- read-only posture, no permission flags (the historical shape;
                        a spawned seat needs a live approver for any mutation/exec).
          arm        -- scoped resuscitation: --permission-mode acceptEdits +
                        --allowedTools Bash,Read,Write,Edit,Glob,Grep so the seat can
                        arm its own wake watcher, drain, and build. Guards still on.
          dangerous  -- break-glass: --dangerously-skip-permissions. Bypasses every
                        approval. The blunt hammer, for when arm is provably not enough.
        """
        import shutil
        import subprocess
        import time as _t
        # `!spawn <bare seat name>` launches THAT seat (2026-08-24). Until today the word
        # was only ever a TASK STRING, so when he typed `!spawn rill` -- locked out, with
        # the conductor dead -- the gateway spawned a claude seat to go and think about
        # the word "rill". It investigated Rill, wrote a report, and stopped. Rill itself
        # was never started and stayed down all day. Every layer worked; the lever meant
        # something other than what he meant.
        #
        # Anything that is not EXACTLY a seat name falls through to the historical path
        # below, unchanged -- a lever that sometimes swallows your sentence because it
        # began with a name would be worse than the one it replaces.
        from core.fleet import seat_launchers as _sl
        _seat, _flags = _sl.parse_spawn_target(task)
        if _seat and _seat.get("kind") == "claude_seat":
            # `!spawn vandor` has TWO preconditions that 2026-08-24 proved independent:
            # the Claude Code DESKTOP APP (dead 12:01:59 -> 14:45:52) and the `claude`
            # CLI, which kept working the whole time the app was down. So the app is
            # never ensured as a side effect -- when it is missing he gets the state and
            # the choices, because package surgery fired from a phone by one bare word is
            # not something this house does silently.
            from core.fleet import app_package as _ap
            _row = _ap.observe_app()
            try:
                from core.comm import wake_seat as _ws
                _live = len(_ws.iter_seats("claude") or [])
            except Exception:                                           # noqa: BLE001
                _live = 0
            _plan = _sl.claude_seat_plan(
                app_healthy=bool(_row.get("healthy")),
                app_repairable=bool(_row.get("repairable")),
                app_detail=str(_row.get("detail")), live_seats=_live, flags=_flags)
            print(f"[discord-in] vandor preflight: {_plan['action']}", flush=True)
            if _plan["action"] == "options":
                # The handler's except-path carries this straight into his channel. It is
                # a REFUSAL TO GUESS, not a failure, and it names every way forward.
                raise RuntimeError(_plan["message"])
            if _plan["action"] == "repair_then_spawn":
                import scripts.revive as _revive
                _step = {"organ": "app", "kind": "msix-repair", "pkg": _row.get("pkg")}
                _ok = _revive._heal_app(_step)
                _lines = NL.join(str(x) for x in (_step.get("receipt") or ()))
                if not _ok:
                    raise RuntimeError(f"app repair REFUSED — no seat spawned.{NL}{_lines}")
                print(f"[discord-in] app repaired:{NL}{_lines}", flush=True)
            # fall through to the CLI spawn, with a task worth booting on
            task = ("fresh Vandor seat, launched by the operator from Discord: boot, "
                    "read the latest handoff, drain the work lane, and take the watch")
            _seat = None
        if _seat:
            argv, env_overlay, cwd = _sl.launch_argv(_seat, root=str(_ROOT))
            lenv = os.environ.copy()
            lenv.update(env_overlay)          # the seat states its OWN id; never inherits
            logs = _ROOT / "state" / "spawn-logs"
            logs.mkdir(parents=True, exist_ok=True)
            log = logs / f"launch-{_seat['slug']}-{int(_t.time())}.log"
            flags = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                     | getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with open(log, "w", encoding="utf-8") as fh:
                p = subprocess.Popen(argv, env=lenv, cwd=cwd, stdout=fh, stderr=fh,
                                     creationflags=flags)
            note = _sl.launch_note(_seat)
            _launch_notes[p.pid] = note
            _pending_spawns[p.pid] = (p, log)
            print(f"[discord-in] 🚀 {note} (pid {p.pid} -> {log.name})", flush=True)
            return p.pid
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
        # spawn GRANT (2026-08-23): translate the mode into CLI permission flags that ride
        # the launch line. Session-scoped by the harness; a spawned seat cannot grant these
        # to itself (security-schema-proposal.md:439).
        #
        #   default    -- read-only (the historical shape; needs a live approver).
        #   arm        -- DEFAULT since 2026-08-23: acceptEdits (file writes auto-approve)
        #                 + the Bash/Read/Write/Edit/Glob/Grep tools available. File edits
        #                 carry a guard rail; Bash command AUTO-APPROVE is scoped by the
        #                 `permissions.allow` rules in .claude/settings.json (self-arm +
        #                 drain verbs are there) rather than broad open.
        #   dangerous  -- --dangerously-skip-permissions: bypass every approval. Full hammer.
        # THE RULE NOW LIVES IN CORE, WITH ITS PINS (2026-08-24). Daniil: "lets make sure
        # the cli version it spawns is exec enabled so it can respond, we have been bitten
        # by that so many times." A seat spawned read-only boots, appears on every dial,
        # and can do nothing -- it cannot arm its own watcher, drain, commit or test. A
        # rule kept inline here is a rule that can regress silently; kept in core it is
        # governed by test_a_spawned_claude_seat_can_ALWAYS_exec across every mode,
        # including the unknown ones, which degrade to ARMED rather than to read-only.
        permission_flags = _sl.claude_permission_flags(mode)
        with open(log, "w", encoding="utf-8") as fh:
            p = subprocess.Popen([exe, "-p", prompt, *permission_flags], env=env,
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

        async def _confess(text: str, warn: bool = True) -> None:
            try:
                if warn:                    # a closing report is news, not an alarm --
                    await message.add_reaction("⚠️")   # only a stillbirth wears the siren
            except Exception:                                           # noqa: BLE001
                pass                        # the reaction is garnish; the words matter
            try:                            # 1900 < Discord's 2000: a confession that
                await message.reply(text[:1900], mention_author=False)   # clips is a
            except Exception as e:                                      # noqa: BLE001
                print(f"[discord-in] stillbirth notice UNDELIVERABLE ({type(e).__name__}"
                      f": {e}) -- it stands in this log only", flush=True)

        def _watch() -> None:
            started = time.time()
            # A seat launch says what it is and whether the lever is proven, NOW -- not at
            # a deadline ten minutes away, and not only into this log. An undrilled lever
            # must announce that it is undrilled while he can still act on it.
            note = _launch_notes.pop(pid, None)
            if note:
                try:
                    asyncio.run_coroutine_threadsafe(_confess(f"🚀 {note}", warn=False),
                                                     loop)
                except Exception as e:                                  # noqa: BLE001
                    print(f"[discord-in] could not relay the launch note: {e}", flush=True)
            try:
                code = proc.wait(timeout=_SPAWN_PROOF_SECONDS)
            except subprocess.TimeoutExpired:
                code = None
            reason = spawn_stillborn_reason(code, _spawn_said(log))
            if not reason:
                print(f"[discord-in] spawn {pid} still breathing after "
                      f"{_SPAWN_PROOF_SECONDS:.0f}s -- the sprout holds", flush=True)
                # KEEP LISTENING. Until 2026-08-24 the thread ENDED on this line, so a
                # seat that outlived the 25s proof window was never heard from again --
                # and "the sprout holds" went to this log, not to the man who asked. The
                # proof window answers "did it live"; the wait below answers "did it ever
                # say anything", which is the question he was actually asking.
                if code is None:
                    try:
                        code = proc.wait(timeout=_SPAWN_REPORT_DEADLINE)
                    except subprocess.TimeoutExpired:
                        code = None
                report = spawn_closing_report(
                    code, _spawn_said(log),
                    elapsed_s=time.time() - started,
                    deadline_s=_SPAWN_REPORT_DEADLINE)
                if not report:
                    return
                print(f"[discord-in] spawn {pid} closing report ({log.name})", flush=True)
                try:
                    asyncio.run_coroutine_threadsafe(
                        _confess(f"🌱 `{log.name}` — {report}", warn=False), loop)
                except Exception as e:                                  # noqa: BLE001
                    print(f"[discord-in] could not relay the closing report: {e}",
                          flush=True)
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
        from core.comm import roster
        _inc = (os.environ.get("BIFROST_INCARNATION")
                or f"{os.getpid()}-discord")
        while True:
            time.sleep(HEARTBEAT_S)
            beat(wl)
            # T147: the roster reads a PER-INCARNATION key; the worklive beat above
            # writes the bare one. Without this line a live gateway renders DEAD to
            # the reaper's only sensor (same defect, same fix as the kimi runner).
            try:
                roster.heartbeat(os.environ.get("BIFROST_NAMESPACE", "bifrost"),
                                 "discord", _inc, phase="running")
            except Exception:
                pass                    # the beat must never kill the beater

    threading.Thread(target=_pulse, name="discord-gateway-beat", daemon=True).start()

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    def _revive(target, observe_only, message):
        """The R3-amendment lever (T382): run the reconciler and speak its
        confession back into the channel that pulled it. FIXED script, enum-
        validated target, zero content passthrough -- and it must work when
        the bus is a corpse, so the reply path is the raw socket, never a
        webhook and never the feed."""
        import threading as _th

        def _work():
            cmd = [sys.executable, str(_ROOT / "scripts" / "revive.py")]
            if target:
                cmd += ["--target", str(target)]
            if observe_only:
                cmd += ["--observe"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=240, cwd=str(_ROOT),
                                   encoding="utf-8", errors="replace")
                out = (r.stdout or "").strip()
                if (r.stderr or "").strip():
                    out += NL + "stderr: " + r.stderr.strip()[:400]
                out = out or f"(revive exited {r.returncode} with no words)"
            except Exception as e:                                      # noqa: BLE001
                out = f"revive FAILED to launch: {type(e).__name__}: {e}"

            async def _say(txt):
                try:
                    await message.channel.send(txt)
                except Exception:                                       # noqa: BLE001
                    pass                    # the socket too can die; log remains
            print(f"[discord-in] revive lever ran (target={target}, "
                  f"observe={observe_only})", flush=True)
            for i in range(0, len(out), 1800):
                try:
                    asyncio.run_coroutine_threadsafe(_say(out[i:i + 1800]),
                                                     client.loop)
                except Exception:                                       # noqa: BLE001
                    pass
        _th.Thread(target=_work, name="revive-lever", daemon=True).start()

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
                entry = _ladder_msgs.get(op["discord_msg_id"])
                if entry is None:
                    continue                # pre-restart entry: residual, drop it
                msg, current = entry
                emoji = _LADDER_EMOJI.get(op["op"])
                if not emoji:
                    continue
                try:
                    # ONE evolving badge: remove exactly the badge we last
                    # applied, then add the next stage. The remove targets our
                    # own reaction only (no manage_messages needed).
                    if current:
                        try:
                            await msg.remove_reaction(current, client.user)
                        except Exception:                               # noqa: BLE001
                            pass            # removing our own badge is best-effort
                    await msg.add_reaction(emoji)
                    if op["op"] in ("answered", "replied", "dead"):
                        _ladder_msgs.pop(op["discord_msg_id"], None)  # terminal
                    else:
                        entry[1] = emoji                    # 🤔 is now current
                except discord.NotFound:
                    _ladder_msgs.pop(op["discord_msg_id"], None)  # deleted: evict
                except Exception as e:                                  # noqa: BLE001
                    print(f"[discord-in] ladder react failed on {op['op']} "
                          f"({type(e).__name__}: {e}) -- delivery stands, the "
                          f"emote does not", flush=True)

    # ---- 2026-08-26: the guest reply path (the tier's missing direction, live
    # defect: Daniil -- "your reply never landed in the discord"). The pure pinned
    # half (core/comm/discord_guest_reply.py) decides WHAT may post; this loop reads
    # the operator inbox for seat replies that --answers a tracked GUEST message and
    # posts them to the guest's own channel, attributed, never steering (control
    # kinds are refused in the tracker itself). In-process state: a gateway restart
    # drops in-flight tracking -- the same residual the ladder confesses.
    async def _guest_reply_loop():
        from core.comm.discord_guest_reply import GuestReplyTracker
        from core.comm.bus import Bus as _Bus
        tracker = GuestReplyTracker()
        client._guest_tracker = tracker           # on_message tracks through this
        parser = _Bus("guest-reply-parse", client=bus._client,
                      namespace=bus.ns, promote=False)
        cur = "0-0"
        try:
            last = bus._client.xrevrange(f"{bus.ns}:inbox:daniil", count=1)
            if last:
                cur = last[0][0].decode() if isinstance(last[0][0], bytes) else str(last[0][0])
        except Exception:                                         # noqa: BLE001
            pass                                   # tail-init: the archive never replays
        while True:
            await asyncio.sleep(2)
            try:
                rows = bus._client.xrange(f"{bus.ns}:inbox:daniil",
                                          min="(" + str(cur), max="+", count=50)
            except Exception as e:                                # noqa: BLE001
                print(f"[discord-in] guest-reply read failed ({type(e).__name__}: {e})",
                      flush=True)
                continue
            batch = []
            for sid, fields in rows:
                sid = sid.decode() if isinstance(sid, bytes) else str(sid)
                cur = sid
                f = {(k.decode() if isinstance(k, bytes) else str(k)):
                     (v.decode() if isinstance(v, bytes) else str(v))
                     for k, v in dict(fields).items()}
                if f.get("kind") == "trace":
                    continue
                try:
                    msg = parser._to_msg(sid, f)   # the ONE seam: Bus shapes the record
                except Exception:                                 # noqa: BLE001
                    continue
                meta = getattr(msg, "meta", None) or {}
                text = getattr(msg, "content", "") or f.get("content") or ""
                batch.append({"id": sid, "frm": str(getattr(msg, "frm", "") or f.get("frm", "")),
                              "kind": str(f.get("kind") or ""), "meta": meta,
                              "text": str(text)})
            for op in tracker.poll(batch):
                try:
                    await op["channel_key"].channel.send(
                        f"[reply from {op['frm']}]\n{op['text']}")
                    print(f"[discord-in] guest reply posted ({op['frm']})", flush=True)
                except Exception as e:                            # noqa: BLE001
                    print(f"[discord-in] guest reply UNDELIVERABLE "
                          f"({type(e).__name__}: {e}) -- it stands in this log only",
                          flush=True)

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
        # 2026-08-26: one guest-reply loop per process, same guard discipline.
        if not getattr(client, "_guest_loop_started", False):
            client._guest_loop_started = True
            asyncio.create_task(_guest_reply_loop())

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
        # 2026-08-23 (Serge's shader ask): the ear learns to RECEIVE media.
        # Attachments download to the local blob plane (B1: the filesystem is
        # the shared store) and ride the bus as content-addressed parts. Data,
        # never instruction (R2); size-capped; one bad file never mutes words.
        att_paths = []
        if message.attachments:
            att_dir = _ROOT / "state" / "inbound-media"
            att_dir.mkdir(parents=True, exist_ok=True)
            for att in message.attachments[:6]:
                try:
                    if int(getattr(att, "size", 0) or 0) > 15 * 1024 * 1024:
                        print(f"[discord-in] attachment {att.filename} refused: "
                              f"{att.size} bytes > 15MB cap", flush=True)
                        continue
                    safe = "".join(c for c in str(att.filename)
                                   if c.isalnum() or c in "._-")[:80] or "file"
                    dest = att_dir / f"{message.id}-{safe}"
                    await att.save(dest)
                    att_paths.append(str(dest))
                except Exception as e:                                  # noqa: BLE001
                    print(f"[discord-in] attachment save failed "
                          f"({type(e).__name__}: {e})", flush=True)
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
                spawner=_spawn,
                message_id=str(message.id),
                reviver=lambda target, observe_only: _revive(
                    target, observe_only, message),
                attachments=att_paths or None)
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
                    # [message, current badge] -- the ladder is ONE evolving
                    # badge, not an accumulation (Daniil 2026-08-22: "have mail
                    # update to something once it reaches the agent, and the
                    # reply be the checkmark"). 📨 was just added by the react
                    # loop below; the applier swaps it forward stage by stage.
                    _ladder_msgs[str(message.id)] = [message, "📨"]
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
                # 2026-08-26: hand the guest's bus id to the reply tracker, so a
                # seat that --answers it reaches the guest's own channel.
                try:
                    if getattr(client, "_guest_tracker", None):
                        client._guest_tracker.track(str(out["id"]), message)
                except Exception:                                 # noqa: BLE001
                    pass
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
