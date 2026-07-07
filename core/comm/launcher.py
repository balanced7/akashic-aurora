"""
Bifrost Launcher — spawn and monitor agent processes from the Bifrost UI.

The Bifrost console can already SEE who's online (presence) and steer them. This
module adds LAUNCH: one-click start for runners, local-model Claude Code sessions,
and headless frontier invocations. It tracks the spawned process lifecycle so the UI
can show running / crashed / token-exhausted / exited / never-launched, and it lets
you kill a runaway agent with one click.

Architecture:
  - AgentSpec: a declared launchable agent (what to run, how, with what env)
  - AgentProcess: a running instance (pid, status, exit code, tail of stdout/stderr)
  - Launcher: the singleton that owns the registry, spawns processes, and monitors them

Exit reason detection:
  - For ANY process, exit_code 0 = "clean"
  - non-zero exit + stderr contains "token" or "credit" or "limit" = "token_exhausted"
  - non-zero exit + stderr contains "api_key" or "unauthorized" = "auth_error"
  - non-zero exit + killed by us = "killed"
  - non-zero exit otherwise = "error"
  - Process still running = "running"
  - Never launched = "never_launched"

Process safety:
  - Only ONE instance per agent_id (enforced by runner_lock for runners, by launcher
    tracking for other types).
  - Kill is best-effort: terminate() then kill() after grace period.
  - Failed launches are tracked (exit_reason set) so the UI shows the failure.
  - Zombie reaping: the monitor thread reaps exited processes.

Integration with the Bifrost UI (scripts/bifrost_ui.py):
  GET  /launcher/status          -> all agent specs + their run status
  POST /launcher/launch          {"agent_id": "deepseek"}  -> spawn
  POST /launcher/kill            {"agent_id": "deepseek"}  -> terminate
  POST /launcher/launch-primed   {"agent_id": "deepseek", "prompt": "..."} -> spawn + inject prompt
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Restart-storm guard (L3c): exponential backoff, a hard cap, and a reset window so a runner that
# ran healthily for a while starts fresh. A deterministic boot-crash must not crash-loop forever.
RESTART_BACKOFF_BASE = float(os.getenv("LAUNCHER_RESTART_BACKOFF", "3"))   # seconds, first retry
RESTART_BACKOFF_MAX = float(os.getenv("LAUNCHER_RESTART_BACKOFF_MAX", "60"))
RESTART_MAX_ATTEMPTS = int(os.getenv("LAUNCHER_RESTART_MAX", "5"))          # then escalate + stop
RESTART_RESET_S = float(os.getenv("LAUNCHER_RESTART_RESET", "300"))         # healthy-for-this-long -> reset the counter

HERE = Path(__file__).resolve().parent.parent.parent  # core/comm -> repo root
SCRIPTS = HERE / "scripts"
SECURITY_DIR = HERE / "security"
REGISTRY_PATH = SECURITY_DIR / "launcher.json"
SESSION_FILE = HERE / "state" / "bifrost-session.json"   # durable across Redis + OS restarts

# ------------------------------------------------------------------ data types

@dataclass
class AgentSpec:
    """A declared launchable agent. The registry holds these; the Launcher spawns from them."""
    agent_id: str
    runtime: str           # "python_runner" | "powershell" | "claude_headless" | "shell"
    description: str
    command: List[str]     # executable + base args (e.g. ["py", "scripts/bifrost_runner_deepseek.py", "--agentic"])
    env: Dict[str, str] = field(default_factory=dict)
    cwd: str = ""          # relative to repo root, or absolute; "" = repo root
    auto_restart: bool = False
    enabled: bool = True   # False = greyed out in the UI


@dataclass
class AgentProcess:
    """A tracked running (or recently exited) agent process."""
    agent_id: str
    pid: int = 0
    handle: Optional[subprocess.Popen] = None
    status: str = "never_launched"   # running | exited | crashed | killed | never_launched
    started_at: str = ""
    exit_code: Optional[int] = None
    exit_reason: str = ""            # clean | token_exhausted | error | killed | auth_error
    exit_seen_at: str = ""
    stdout_tail: str = ""            # last ~500 chars of stdout for diagnostics
    stderr_tail: str = ""            # last ~500 chars of stderr


# ------------------------------------------------------------------ registry

def _default_registry() -> Dict[str, AgentSpec]:
    """The built-in launchable agents. Override/augment via security/launcher.json."""
    repo = str(HERE)
    py = sys.executable or "py"

    return {
        "deepseek": AgentSpec(
            agent_id="deepseek",
            runtime="python_runner",
            description="DeepSeek API peer (admin) — tool-using bus citizen",
            command=[py, str(SCRIPTS / "bifrost_runner_deepseek.py"), "--agentic", "--root", repo],
            env={"PYTHONUNBUFFERED": "1"},
            cwd=repo,
            enabled=True,
        ),
        "deepseek-think": AgentSpec(
            agent_id="deepseek",
            runtime="python_runner",
            description="DeepSeek API peer (admin) — agentic + deep thinking mode",
            command=[py, str(SCRIPTS / "bifrost_runner_deepseek.py"), "--agentic", "--think", "--root", repo],
            env={"PYTHONUNBUFFERED": "1"},
            cwd=repo,
            enabled=True,
        ),
        "deepseek-write": AgentSpec(
            agent_id="deepseek",
            runtime="python_runner",
            description="DeepSeek API peer (admin) — agentic + write access",
            command=[py, str(SCRIPTS / "bifrost_runner_deepseek.py"), "--agentic", "--allow-write", "--root", repo],
            env={"PYTHONUNBUFFERED": "1"},
            cwd=repo,
            enabled=True,
        ),
        "deepseek-build": AgentSpec(
            agent_id="deepseek",
            runtime="python_runner",
            description="DeepSeek API peer (admin) — agentic + write + shell (build while claude is down)",
            command=[py, str(SCRIPTS / "bifrost_runner_deepseek.py"), "--agentic", "--allow-write", "--allow-exec", "--root", repo],
            env={"PYTHONUNBUFFERED": "1"},
            cwd=repo,
            enabled=True,
        ),
        "gemini": AgentSpec(
            agent_id="gemini",
            runtime="python_runner",
            description="Gemini web bridge — answers bus questions",
            command=[py, str(SCRIPTS / "bifrost_runner.py")],
            env={"PYTHONUNBUFFERED": "1"},
            cwd=repo,
            enabled=True,
        ),
    }


def _load_registry() -> Dict[str, AgentSpec]:
    """Merge the built-in defaults with any overrides in security/launcher.json."""
    specs = _default_registry()
    try:
        if REGISTRY_PATH.exists():
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            for entry in data.get("agents", []):
                aid = entry.get("agent_id")
                if not aid:
                    continue
                specs[aid] = AgentSpec(
                    agent_id=aid,
                    runtime=entry.get("runtime", "shell"),
                    description=entry.get("description", ""),
                    command=entry.get("command", []),
                    env=entry.get("env", {}),
                    cwd=entry.get("cwd", ""),
                    auto_restart=entry.get("auto_restart", False),
                    enabled=entry.get("enabled", True),
                )
    except Exception:
        pass
    return specs


# ------------------------------------------------------------------ exit reason detection

# Patterns in stderr/stdout that indicate token/credit exhaustion
_TOKEN_EXHAUSTED_PATTERNS = [
    # Multi-word phrases (safe substring match) + single words only when strongly indicative.
    # Bare "token", "limit", "429", "balance" removed — too eager; the phrases below cover real cases.
    "credit", "quota", "billing", "rate limit",
    "exceeded your", "run out of", "insufficient",
    "you've reached", "too many requests",
    "context length", "context window", "maximum context",
    "token budget", "token limit", "max tokens",
    "out of credit", "out of token",
]
_AUTH_ERROR_PATTERNS = [
    "api_key", "api key", "unauthorized", "authentication",
    "invalid key", "not authorized", "401", "403",
    "login required", "sign in", "LOGIN_REQUIRED",
]


def _classify_exit(exit_code: int, stdout_tail: str, stderr_tail: str, killed_by_us: bool) -> str:
    """What happened to this process? Best-effort classification."""
    if killed_by_us:
        return "killed"
    if exit_code == 0:
        return "clean"
    combined = (stderr_tail + " " + stdout_tail).lower()
    for pat in _TOKEN_EXHAUSTED_PATTERNS:
        if pat in combined:
            return "token_exhausted"
    for pat in _AUTH_ERROR_PATTERNS:
        if pat in combined:
            return "auth_error"
    return "error"


# ------------------------------------------------------------------ Launcher

class Launcher:
    """Singleton: spawns and monitors agent processes."""

    def __init__(self):
        self._specs: Dict[str, AgentSpec] = {}
        self._procs: Dict[str, AgentProcess] = {}
        self._lock = threading.Lock()
        self._monitor_stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._restart_attempts: Dict[str, int] = {}    # agent_id -> consecutive restart count (L3c backoff)
        self._restart_last: Dict[str, float] = {}       # agent_id -> ts of last restart (for the reset window)
        self._auto_revive: set = set()                  # agent_ids armed for auto-revive-on-wedge (L3b, opt-in, default off)
        self._reload()

    def _reload(self):
        with self._lock:
            self._specs = _load_registry()

    # -- public API ----------------------------------------------------------

    def registry(self) -> List[Dict[str, Any]]:
        """All launchable agents + their current run status. For the UI."""
        from core.comm import liveness   # L3a: observe-only wedge view (fail-open; None when no record)
        self._reload()
        out = []
        with self._lock:
            for tag, spec in sorted(self._specs.items()):
                proc = self._procs.get(spec.agent_id)
                out.append({
                    "tag": tag,
                    "agent_id": spec.agent_id,
                    "runtime": spec.runtime,
                    "description": spec.description,
                    "enabled": spec.enabled,
                    "auto_restart": spec.auto_restart,
                    "status": proc.status if proc else "never_launched",
                    "pid": proc.pid if proc and proc.status == "running" else 0,
                    "started_at": proc.started_at if proc else "",
                    "exit_code": proc.exit_code if proc else None,
                    "exit_reason": proc.exit_reason if proc else "",
                    "exit_seen_at": proc.exit_seen_at if proc else "",
                    "stdout_tail": (proc.stdout_tail or "")[-200:] if proc else "",
                    "stderr_tail": (proc.stderr_tail or "")[-200:] if proc else "",
                    "liveness": liveness.wedge_view(spec.agent_id),   # L3a: observe-only phase + stuck-time + wedged flag
                })
        return out

    def launch(self, tag: str, *, prompt: str = "", extra_args: List[str] | None = None) -> Dict[str, Any]:
        """Spawn the agent identified by `tag`. Returns {ok, agent_id, pid, error?}.

        If the agent is already running, returns ok=False with a reason.
        If prompt is given, it's injected as stdin or as an extra arg (for Claude headless).
        """
        self._reload()
        spec = self._specs.get(tag)
        if spec is None:
            return {"ok": False, "error": f"unknown agent tag: {tag}"}

        with self._lock:
            existing = self._procs.get(spec.agent_id)
            if existing and existing.status == "running":
                # Double-check the process is actually alive
                if existing.handle and existing.handle.poll() is None:
                    return {"ok": False, "error": f"'{spec.agent_id}' is already running (pid {existing.pid})"}
                # Stale — the process died but we hadn't reaped it yet
                existing.status = "exited"
                existing.exit_code = existing.handle.returncode if existing.handle else -1
                existing.exit_reason = _classify_exit(
                    existing.exit_code or -1, existing.stdout_tail, existing.stderr_tail, False)

        # Singleton gate (D3): refuse to spawn a duplicate when a live runner already holds the lock.
        # The child runner acquires + heartbeats + releases its OWN lock, so the launcher must only
        # CHECK, never HOLD it -- a stray acquire here would keep the child from acquiring the lock it
        # needs to start (the launcher's token != the child's), starving its own spawn. A crashed
        # holder's key clears via runner_lock.LOCK_TTL, after which a relaunch succeeds.
        if spec.runtime == "python_runner":
            from core.comm import runner_lock
            h = runner_lock.holder(spec.agent_id)
            if h:
                return {"ok": False, "agent_id": spec.agent_id, "pid": h.get("pid"),
                        "error": f"'{spec.agent_id}' already has a live runner (pid {h.get('pid')}); "
                                 f"refusing to spawn a duplicate. If it crashed, retry in "
                                 f"~{runner_lock.LOCK_TTL}s once its lock expires (or kill it first)."}

        cwd = spec.cwd or str(HERE)
        cmd = list(spec.command)
        if extra_args:
            cmd.extend(extra_args)

        env = {**os.environ, **spec.env}

        # Claude headless: prompt goes as a positional argument, not stdin
        if spec.runtime == "claude_headless" and prompt:
            cmd.append(prompt)
            prompt = ""   # don't pipe to stdin below

        try:
            handle = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE if prompt else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
        except Exception as e:
            return {"ok": False, "error": f"failed to spawn: {type(e).__name__}: {e}"}

        if prompt:
            try:
                handle.stdin.write(prompt)
                handle.stdin.close()
            except Exception:
                pass

        proc = AgentProcess(
            agent_id=spec.agent_id,
            pid=handle.pid,
            handle=handle,
            status="running",
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        with self._lock:
            self._procs[spec.agent_id] = proc

        self._ensure_monitor()
        self._save_session_to_disk()     # persist: tomorrow's 1-click restore
        return {"ok": True, "agent_id": spec.agent_id, "pid": handle.pid, "tag": tag}

    def kill(self, tag: str) -> Dict[str, Any]:
        """Terminate the running agent. Graceful first (SIGTERM/CTRL_BREAK), then force (SIGKILL/Terminate)."""
        spec = self._specs.get(tag)
        if spec is None:
            return {"ok": False, "error": f"unknown agent tag: {tag}"}

        with self._lock:
            proc = self._procs.get(spec.agent_id)
            if not proc or proc.status != "running":
                return {"ok": False, "error": f"'{spec.agent_id}' is not running"}
            handle = proc.handle

        if handle is None:
            return {"ok": False, "error": "no process handle"}

        # Graceful first
        try:
            if sys.platform == "win32":
                handle.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                handle.terminate()
        except Exception:
            pass

        # Wait a moment for graceful exit
        try:
            handle.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill
            try:
                handle.kill()
                handle.wait(timeout=2)
            except Exception:
                pass

        with self._lock:
            proc.status = "killed"
            proc.exit_code = handle.poll()
            proc.exit_reason = "killed"
            proc.exit_seen_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            try:
                out, err = handle.communicate(timeout=5)
                proc.stdout_tail = (out or "")[-500:]
                proc.stderr_tail = (err or "")[-500:]
            except Exception:
                pass

        self._save_session_to_disk()     # persist the change
        return {"ok": True, "agent_id": spec.agent_id, "tag": tag}

    def _free_lock_for_relaunch(self, aid: str, dead_pid) -> None:
        """Before a relaunch, make sure the singleton lock is free -- since L5, launch() refuses while
        a holder is present, so a killed runner whose `finally` didn't release would block its own
        relaunch until the TTL. Wait briefly for a graceful release, then force-free ONLY the dead pid."""
        from core.comm import runner_lock
        deadline = time.time() + 4
        while runner_lock.holder(aid) and time.time() < deadline:
            time.sleep(0.25)
        if dead_pid is not None:
            runner_lock.clear_if_pid(aid, dead_pid)

    def revive(self, tag: str, reason: str = "manual") -> Dict[str, Any]:
        """Recover a wedged or dead runner: kill it (if up), free its singleton lock, relaunch.
        This is the primitive behind the UI 'Revive' button and (when armed) the auto-revive monitor."""
        spec = self._specs.get(tag)
        if spec is None:
            return {"ok": False, "error": f"unknown agent tag: {tag}"}
        aid = spec.agent_id
        with self._lock:
            proc = self._procs.get(aid)
            dead_pid = proc.pid if (proc and proc.status == "running") else None
        if dead_pid is not None:
            self.kill(tag)                       # graceful -> force; the runner's finally usually frees the lock
        self._free_lock_for_relaunch(aid, dead_pid)
        # a human/explicit revive is a fresh start -> clear the crash-backoff counter
        self._restart_attempts.pop(aid, None)
        self._restart_last.pop(aid, None)
        res = self.launch(tag)
        res.update({"revived": True, "revive_reason": reason, "killed_pid": dead_pid})
        return res

    def arm_revive(self, tag: str, on: bool = True) -> Dict[str, Any]:
        """Opt in/out of automatic revive-on-wedge for this agent (default OFF -> observe-only).
        When armed, the monitor auto-revives if the agent is flagged 'wedged' past the threshold."""
        spec = self._specs.get(tag)
        if spec is None:
            return {"ok": False, "error": f"unknown agent tag: {tag}"}
        with self._lock:
            if on:
                self._auto_revive.add(spec.agent_id)
            else:
                self._auto_revive.discard(spec.agent_id)
            armed = spec.agent_id in self._auto_revive
        return {"ok": True, "tag": tag, "agent_id": spec.agent_id, "auto_revive": armed}

    def status(self, tag: str) -> Dict[str, Any]:
        """Quick status for one agent tag."""
        for row in self.registry():
            if row["tag"] == tag:
                return row
        return {"tag": tag, "error": "unknown"}

    # -- session save / restore (durable across restarts) -------------------

    def _save_session_to_disk(self) -> bool:
        """Snapshot currently-running agent tags to state/bifrost-session.json so a
        single 'Restore Session' click tomorrow spins up the same fleet. Best-effort."""
        try:
            with self._lock:
                running_tags = [
                    tag for tag, spec in self._specs.items()
                    if self._procs.get(spec.agent_id) and self._procs[spec.agent_id].status == "running"
                ]
            os.makedirs(SESSION_FILE.parent, exist_ok=True)
            payload = {"tags": sorted(running_tags), "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "saved_by": "launcher"}
            SESSION_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def session_snapshot(self) -> Dict[str, Any]:
        """What a restore would do — for the UI 'Restore' button to preview."""
        try:
            if not SESSION_FILE.exists():
                return {"ok": True, "tags": [], "message": "no saved session yet"}
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            tags = data.get("tags", [])
            # Enrich with known spec descriptions
            enriched = []
            for tag in tags:
                spec = self._specs.get(tag)
                enriched.append({
                    "tag": tag,
                    "description": spec.description if spec else "?",
                    "already_running": (self._procs.get(spec.agent_id) and
                                        self._procs[spec.agent_id].status == "running") if spec else False,
                })
            return {"ok": True, "tags": enriched, "saved_at": data.get("saved_at", ""),
                    "count": len(tags),
                    "already_running": sum(1 for e in enriched if e["already_running"])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def restore_session(self) -> Dict[str, Any]:
        """Re-launch every agent tag saved from the last session. Skips agents already running.
        Returns {ok, results: [{tag, launched, error?}], total, launched_count}."""
        snapshot = self.session_snapshot()
        if not snapshot["ok"]:
            return {"ok": False, "error": snapshot.get("error", "could not read session file")}

        tags = [t["tag"] for t in snapshot.get("tags", [])]
        if not tags:
            return {"ok": True, "results": [], "total": 0, "launched_count": 0,
                    "message": "no agents in saved session"}

        results = []
        launched_count = 0
        for tag in tags:
            # Check if already running
            spec = self._specs.get(tag)
            if spec:
                with self._lock:
                    proc = self._procs.get(spec.agent_id)
                if proc and proc.status == "running":
                    results.append({"tag": tag, "launched": False,
                                    "reason": "already running", "pid": proc.pid})
                    continue
            # Launch it
            r = self.launch(tag)
            if r.get("ok"):
                results.append({"tag": tag, "launched": True, "pid": r.get("pid")})
                launched_count += 1
            else:
                results.append({"tag": tag, "launched": False,
                                "reason": r.get("error", "launch failed")})

        self._save_session_to_disk()
        return {"ok": True, "results": results, "total": len(tags),
                "launched_count": launched_count,
                "message": f"{launched_count}/{len(tags)} agents launched"}

    # -- process monitor ----------------------------------------------------

    def _ensure_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="launcher-monitor")
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Background: poll running processes, detect exits, classify reasons."""
        while not self._monitor_stop.wait(2.0):
            with self._lock:
                for aid, proc in list(self._procs.items()):
                    if proc.status != "running":
                        continue
                    handle = proc.handle
                    if handle is None:
                        continue
                    code = handle.poll()
                    if code is None:
                        continue  # still running
                    # Process exited
                    proc.exit_code = code
                    proc.exit_seen_at = time.strftime("%Y-%m-%dT%H:%M:%S")
                    try:
                        out, err = handle.communicate(timeout=5)
                        proc.stdout_tail = (out or "")[-500:]
                        proc.stderr_tail = (err or "")[-500:]
                    except Exception:
                        pass
                    proc.exit_reason = _classify_exit(
                        code, proc.stdout_tail, proc.stderr_tail, proc.status == "killed")
                    proc.status = "exited"

                    # Auto-restart if configured
                    spec = self._specs.get(aid) or next(
                        (s for t, s in self._specs.items() if s.agent_id == aid), None)
                    if spec and spec.auto_restart and proc.exit_reason != "killed":
                        tag = next((t for t, s in self._specs.items() if s.agent_id == aid), aid)
                        threading.Thread(target=self._restart, args=(tag,), daemon=True).start()

    def _restart(self, tag: str, reason: str = "crash"):
        """Restart a crashed agent with exponential backoff + a hard cap (L3c anti crash-storm), freeing
        the singleton lock first -- post-L5, launch() refuses while a stale holder lingers within its TTL,
        so the old flat sleep(3) would silently fail to relaunch a hard-killed runner."""
        spec = self._specs.get(tag)
        aid = spec.agent_id if spec else tag
        now = time.time()
        if now - self._restart_last.get(aid, 0) > RESTART_RESET_S:
            self._restart_attempts[aid] = 0            # ran healthy long enough -> fresh count
        attempts = self._restart_attempts.get(aid, 0) + 1
        self._restart_attempts[aid] = attempts
        self._restart_last[aid] = now
        if attempts > RESTART_MAX_ATTEMPTS:
            try:
                from core.comm.bus import get_bus
                get_bus("launcher").broadcast("note",
                    f"[supervisor] '{aid}' failed {RESTART_MAX_ATTEMPTS}x ({reason}); auto-restart stopped "
                    f"-- needs a human (check stderr_tail / Revive).", meta={"via": "launcher-supervisor"})
            except Exception:
                pass
            return
        backoff = min(RESTART_BACKOFF_BASE * (2 ** (attempts - 1)), RESTART_BACKOFF_MAX)
        time.sleep(backoff)
        with self._lock:
            proc = self._procs.get(aid)
            dead_pid = proc.pid if proc else None
        self._free_lock_for_relaunch(aid, dead_pid)    # clear the dead predecessor's lock so L5 doesn't block us
        self.launch(tag)

    def shutdown(self):
        """Stop the monitor thread. Call on UI server shutdown."""
        self._monitor_stop.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=3)


# ------------------------------------------------------------------ singleton

_LAUNCHER: Optional[Launcher] = None


def get_launcher() -> Launcher:
    global _LAUNCHER
    if _LAUNCHER is None:
        _LAUNCHER = Launcher()
    return _LAUNCHER
