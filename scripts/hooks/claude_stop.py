"""Stop hook: keep THIS Claude session wakeable from idle.

Fires when the turn ends. If no bifrost.wake listener (scripts/bifrost_wake.py) is armed for this
agent, it BLOCKS the stop and tells the model to re-arm -- turning "always wakeable" from fragile
discipline into a harness-enforced invariant ("the environment decides" applied to Claude's own
idling). The listener writes a PID heartbeat; this hook checks that PID is alive (cheap, and correct
even if the listener was killed). Loop-guarded (won't block twice within 25s) and fail-open (never
wedge the session).
"""
import json, os, subprocess, sys, tempfile, time

AGENT = os.environ.get("AKASHIC_AGENT_ID", "claude")
HEARTBEAT = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}.pid")
MARKER = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_stophook.ts")


def _pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True, timeout=6).stdout
        return str(pid) in out
    except Exception:
        return True  # fail-open: on detection error, assume alive (don't wedge the session)


def wake_armed():
    try:
        pid = int(open(HEARTBEAT).read().strip())
    except Exception:
        return False
    return _pid_alive(pid)


def main():
    try:
        sys.stdin.read()  # consume the hook payload (unused)
    except Exception:
        pass
    if wake_armed():
        return  # armed -> allow the stop
    now = time.time()
    try:
        last = float(open(MARKER).read().strip())
    except Exception:
        last = 0.0
    if now - last < 25:
        return  # already nudged very recently -> allow stop, avoid an infinite block loop
    try:
        open(MARKER, "w").write(str(now))
    except Exception:
        pass
    print(json.dumps({"decision": "block", "reason": (
        f"No bifrost.wake listener is armed for '{AGENT}' -- this session is not wakeable from idle "
        f"(DeepSeek/Daniel can't reach you). Re-arm it before stopping: launch "
        f"`py scripts/bifrost_wake.py --agent {AGENT}` as a run_in_background task (so it's harness-"
        "tracked and its completion re-invokes you). Then stop.")}))


if __name__ == "__main__":
    main()
