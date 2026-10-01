"""resume_on_deaf -- S2 of the wake ladder (T420, Daniel 2026-10-01).

THE IDEAL, in his words' spirit: the seat is a durable thing the house can re-open, not a
desktop window that must stay up. Only a background task the session itself launched can
start a turn in an idle Claude Code session, so once the window is closed or the box has
rebooted nothing inside the house can wake it -- EXCEPT the vendor's own session resume:
`claude -p --resume <sid> "<prompt>"` takes a new turn on the exact session with full
continuity (proven 2026-09-02 in 26 s, lesson exact_session_resume_actuator_proven_26s).

Three organs, kept pure so they can be pinned without a daemon, a bus or a credential:

  EXPECTED-UP RECORD  minted OUT OF BAND by the launcher (bifrost-standby, the harness-tracked
                      arm) and retracted by stand-down or the janitor. Never written by the
                      armed process: the failure class is the arm not happening, and an
                      actor that never ran leaves no record (rearm_actor_is_a_trigger_consumer).
  DECISION            resume_decision(): a total function over the observable facts, every
                      hold NAMED. The same table serves the daemon and the doctor.
  ACTUATOR            trigger_resume(): credential preflight (the vaulted claude_oauth.token
                      is the whole cure -- S1, Daniel's), argv built once, detached launch
                      with its own log, a receipt per attempt, a cooldown and a breaker.

What this does NOT do: it never arms a listener for the resumed turn (a headless turn's
background tasks die with it); presence between resumes is the daemon's own listener, which
re-spawns from the .rearm trigger this module leaves. The loop is: daemon listener detects
mail -> session is deaf -> resume turn answers and lands -> daemon listener re-spawns.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[2]

RESUME_AFTER_MIN = 10.0        # the session has been silent this long with no harness listener
RESUME_STALE_MIN = 24 * 60.0   # older than this the session is gone; the janitor's, not ours
RESUME_COOLDOWN_MIN = 30.0     # one resume per session per window
RESUME_BREAKER = 3             # consecutive failed launches -> hold until a human looks
RESUME_MIN_ALIVE_S = 30.0      # a resume child that exits sooner than this DIED (dead credential ~16 s)
TOKEN_NAME = "claude_oauth.token"

#: Heimdall's R4 falsifier (fences/resume-on-deaf/half_a.md): a launch that succeeds and a turn
#: that dies 16 s later were both recorded as success, so a present-but-dead credential could
#: never trip the breaker. The actuator now keeps the child handle here and the daemon settles
#: it on later ticks: an early exit becomes a FAILED receipt that the breaker counts.
in_flight: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------- expected-up record
def expected_dir(base: Optional[str] = None) -> Path:
    return Path(base or os.environ.get("AKASHIC_WAKE_EXPECTED_DIR") or (_ROOT / "state" / "wake-expected"))


def expected_path(agent: str, session_id: str, base: Optional[str] = None) -> Path:
    return expected_dir(base) / f"{agent}_{session_id}.json"


def declare_expected(agent: str, session_id: str, *, by: str = "harness",
                     cwd: Optional[str] = None, base: Optional[str] = None,
                     now: Optional[float] = None) -> bool:
    """The launcher says: this session SHOULD be reachable. Idempotent; best-effort."""
    if not (agent and session_id):
        return False
    try:
        d = expected_dir(base)
        d.mkdir(parents=True, exist_ok=True)
        rec = {"agent": agent, "session_id": session_id, "by": by,
               "cwd": cwd or os.getcwd(), "declared_at": now if now is not None else time.time()}
        expected_path(agent, session_id, base).write_text(json.dumps(rec), encoding="utf-8")
        return True
    except Exception:
        return False


def retract_expected(agent: str, session_id: str, base: Optional[str] = None) -> bool:
    try:
        expected_path(agent, session_id, base).unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def expected_sessions(agent: str, base: Optional[str] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        for p in sorted(expected_dir(base).glob(f"{agent}_*.json")):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                if rec.get("agent") == agent and rec.get("session_id"):
                    out.append(rec)
            except Exception:
                continue
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- the decision table
def resume_decision(*, expected: bool, alive_age_min: Optional[float], harness_armed: bool,
                    tombstoned: bool = False, token_ok: bool = False,
                    last_resume_age_min: Optional[float] = None, failures: int = 0,
                    after_min: float = RESUME_AFTER_MIN, stale_min: float = RESUME_STALE_MIN,
                    cooldown_min: float = RESUME_COOLDOWN_MIN,
                    breaker: int = RESUME_BREAKER) -> Tuple[str, str]:
    """('resume' | 'hold', reason). Total: every input combination names its verdict."""
    if not expected:
        return "hold", "not expected-up (no launcher record)"
    if tombstoned:
        return "hold", "session tombstoned (ended by record)"
    if harness_armed:
        return "hold", "reachable (a harness-parented listener holds the seat)"
    if alive_age_min is None:
        return "hold", "no activity marker (never saw a hook fire)"
    if alive_age_min < after_min:
        return "hold", f"grace ({alive_age_min:.0f}m < {after_min:.0f}m; a turn may be running)"
    if alive_age_min > stale_min:
        return "hold", f"stale ({alive_age_min / 60:.0f}h silent; the janitor's, not a resume)"
    if failures >= breaker:
        return "hold", f"breaker ({failures} consecutive failed launches; a human looks first)"
    if last_resume_age_min is not None and last_resume_age_min < cooldown_min:
        return "hold", f"cooldown ({last_resume_age_min:.0f}m since the last resume)"
    if not token_ok:
        return "hold", ("no credential: vault holds no claude_oauth.token and the CLI is not "
                        "logged in (S1: `claude setup-token` -> `py agent_cli.py secret "
                        "claude_oauth.token`)")
    return "resume", f"deaf {alive_age_min:.0f}m, expected-up, credential present"


# ---------------------------------------------------------------- the actuator
def resume_prompt(agent: str, reason: str) -> str:
    return (f"You were RESUMED headlessly by the house's daemon because this session is deaf "
            f"({reason}): the desktop window is closed or no listener that can start a turn "
            f"holds your seat. Do, in order: `py agent_cli.py boot {agent}`; drain the work "
            f"lane (`BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync {agent} --consume "
            f"--limit 200`); answer every message that needs you -- operator mail is answered "
            f"with `py agent_cli.py bifrost-send {agent} --to daniil --kind chat --text-file "
            f"<file>` so the words reach his phone; land results durably (note / handoff / "
            f"commits by name). Do NOT arm a wake listener: this headless turn cannot keep one "
            f"alive, the daemon holds presence between resumes. End with a one-line wrap.")


def resume_argv(argv0: List[str], session_id: str, prompt: str, *,
                model_flag: Optional[List[str]] = None,
                permission_flags: Optional[List[str]] = None) -> List[str]:
    """One builder so the pin and the launcher cannot drift: `-p <prompt> --resume <sid>`."""
    return [*argv0, *(model_flag or []), "-p", prompt, "--resume", session_id,
            *(permission_flags or [])]


def vault_token(name: str = TOKEN_NAME) -> str:
    """The one vault reader: secret_intake.secrets_dir()/<allowlisted name>."""
    try:
        from core.comm.secret_intake import secrets_dir
        return (secrets_dir() / name).read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def cli_logged_in(exe: str, run=subprocess.run) -> Optional[bool]:
    """`claude auth status` as a tri-state; every failure mode is None (unknown), never False."""
    try:
        r = run([exe, "auth", "status"], capture_output=True, text=True, timeout=10)
        text = f"{r.stdout}\n{r.stderr}".lower()
        if "logged in" in text and "not logged in" not in text:
            return True
        if "not logged in" in text or "logged out" in text:
            return False
        return None
    except Exception:
        return None


def claude_argv0(which: Callable[[str], Optional[str]] = shutil.which) -> Optional[List[str]]:
    exe = which("claude")
    if not exe:
        return None
    native = Path(exe).with_name("node_modules") / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return [str(native)] if native.exists() else [exe]


def receipts_path(agent: str, base: Optional[str] = None) -> Path:
    return Path(base or os.environ.get("AKASHIC_WAKE_RESUMES_DIR")
                or (_ROOT / "state" / "wake-resumes")) / f"{agent}.jsonl"


def record_resume(agent: str, session_id: str, ok: bool, detail: str, *,
                  log_path: str = "", base: Optional[str] = None, now: Optional[float] = None) -> None:
    try:
        p = receipts_path(agent, base)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now if now is not None else time.time(), "session_id": session_id,
                                "ok": bool(ok), "detail": detail[:300], "log": log_path},
                               ensure_ascii=True) + "\n")
    except Exception:
        pass


def resume_history(agent: str, session_id: str, base: Optional[str] = None,
                   now: Optional[float] = None) -> Tuple[Optional[float], int]:
    """(minutes since the last attempt for this session, consecutive failures)."""
    t = now if now is not None else time.time()
    last: Optional[float] = None
    failures = 0
    try:
        for line in open(receipts_path(agent, base), encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("session_id") != session_id:
                continue
            last = float(r.get("ts") or 0)
            failures = 0 if r.get("ok") else failures + 1
    except Exception:
        pass
    return ((t - last) / 60.0 if last else None), failures


def trigger_resume(agent: str, session_id: str, *, reason: str,
                   which: Callable[[str], Optional[str]] = shutil.which,
                   popen=subprocess.Popen, env: Optional[Dict[str, str]] = None,
                   token: Optional[str] = None, logged_in: Optional[bool] = None,
                   receipts_base: Optional[str] = None, log_dir: Optional[str] = None,
                   now: Optional[float] = None) -> Tuple[bool, str]:
    """Launch one headless resume turn, detached, with its own log and a receipt.
    (ok, detail). Refuses at t=0 on a KNOWN-bad credential state (fail-open on ignorance,
    exactly as the gateway's spawn preflight does)."""
    argv0 = claude_argv0(which)
    if not argv0:
        detail = "claude CLI not on PATH"
        record_resume(agent, session_id, False, detail, base=receipts_base, now=now)
        return False, detail
    tok = vault_token() if token is None else token
    if not tok.strip() and (cli_logged_in(argv0[0]) if logged_in is None else logged_in) is False:
        detail = ("no credential: vault holds no claude_oauth.token and the CLI reports logged "
                  "out (S1)")
        record_resume(agent, session_id, False, detail, base=receipts_base, now=now)
        return False, detail
    try:
        from core.fleet import seat_launchers as _sl
        perm = _sl.claude_permission_flags("arm")
    except Exception:
        perm = ["--permission-mode", "acceptEdits",
                "--allowedTools", "Bash,PowerShell,Read,Write,Edit,Glob,Grep"]
    try:
        from core.fleet import seat_model as _smod
        model_flag = _smod.model_flag()
    except Exception:
        model_flag = []
    argv = resume_argv(argv0, session_id, resume_prompt(agent, reason),
                       model_flag=model_flag, permission_flags=perm)
    e = dict(env if env is not None else os.environ)
    if tok.strip():
        e["CLAUDE_CODE_OAUTH_TOKEN"] = tok.strip()
    e.setdefault("AKASHIC_AGENT_ID", agent)
    # R5 (Heimdall): the resumed turn drains the WORK lane; the prompt inlines the env on its
    # own drain line, and the spawn env carries it too so neither can drift alone.
    e.setdefault("BIFROST_CONSUME_LANE", "work")
    e.setdefault("BIFROST_WAKE_LANE", "work")
    logs = Path(log_dir or (_ROOT / "state" / "spawn-logs"))
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    log = logs / f"resume-{session_id[:8]}-{int(now if now is not None else time.time())}.log"
    try:
        fh = open(log, "w", encoding="utf-8")
        proc = popen(argv, env=e, cwd=str(_ROOT), stdout=fh, stderr=fh,
                     creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    except Exception as ex:
        detail = f"launch failed: {type(ex).__name__}: {ex}"
        record_resume(agent, session_id, False, detail, log_path=str(log), base=receipts_base, now=now)
        return False, detail
    detail = f"resumed {session_id[:8]} ({reason}) -> {log.name}"
    record_resume(agent, session_id, True, detail, log_path=str(log), base=receipts_base, now=now)
    in_flight[session_id] = {"agent": agent, "proc": proc,
                             "started": now if now is not None else time.time(),
                             "log": str(log), "receipts_base": receipts_base}
    return True, detail


def settle_in_flight(agent: str, now: Optional[float] = None,
                     min_alive_s: float = RESUME_MIN_ALIVE_S) -> List[Tuple[str, str]]:
    """The daemon's per-tick settle: [(session_id, 'dead' | 'alive' | 'pending')].
    A child that exited before min_alive_s DIED (a dead credential kills a resume in ~16 s):
    it gets a FAILED receipt so the breaker can count it. A child still running past
    min_alive_s is alive and leaves the registry; its later exit is a normal turn end."""
    t = now if now is not None else time.time()
    out: List[Tuple[str, str]] = []
    for sid, rec in list(in_flight.items()):
        if rec.get("agent") != agent:
            continue
        proc = rec.get("proc")
        try:
            code = proc.poll() if proc is not None else None
        except Exception:
            code = None
        age = t - float(rec.get("started") or t)
        if code is not None and age < min_alive_s:
            tail = ""
            try:
                with open(rec.get("log") or "", encoding="utf-8", errors="replace") as f:
                    tail = f.read()[-240:].replace("\n", " | ")
            except Exception:
                pass
            record_resume(agent, sid, False, f"resume DIED after {age:.0f}s rc={code}: {tail}",
                          log_path=rec.get("log") or "", base=rec.get("receipts_base"), now=t)
            in_flight.pop(sid, None)
            out.append((sid, "dead"))
        elif age >= min_alive_s:
            in_flight.pop(sid, None)
            out.append((sid, "alive"))
        else:
            out.append((sid, "pending"))
    return out


def maybe_resume(agent: str, session_id: str, *, now: Optional[float] = None,
                 tmp: Optional[str] = None, expected_base: Optional[str] = None,
                 receipts_base: Optional[str] = None, token: Optional[str] = None,
                 logged_in: Optional[bool] = None, trigger=trigger_resume) -> Tuple[str, str]:
    """The daemon's one call: read the live facts, decide, act. ('resume'|'hold', reason)."""
    from core.comm import wake_seat
    t = now if now is not None else time.time()
    expected = expected_path(agent, session_id, expected_base).exists()
    alive = wake_seat.activity_age_min(agent, session_id, now=t, tmp=tmp)
    armed = wake_seat.harness_armed(agent, session_id, tmp)
    try:
        tomb = bool(wake_seat.is_tombstoned(session_id, tmp=tmp))
    except Exception:
        tomb = False
    tok = vault_token() if token is None else token
    token_ok = bool(tok.strip()) or (logged_in is True)
    last_age, failures = resume_history(agent, session_id, receipts_base, now=t)
    verdict, reason = resume_decision(expected=expected, alive_age_min=alive, harness_armed=armed,
                                      tombstoned=tomb, token_ok=token_ok,
                                      last_resume_age_min=last_age, failures=failures)
    if verdict != "resume":
        return verdict, reason
    ok, detail = trigger(agent, session_id, reason=reason, token=tok, logged_in=logged_in,
                         receipts_base=receipts_base, now=t)
    return ("resume" if ok else "hold"), detail
