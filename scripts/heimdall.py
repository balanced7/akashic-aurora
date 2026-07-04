"""Heimdall -- the watchman of the Bifrost bus (agent wake-from-idle sentinel).

In Norse myth Heimdall guards the Bifrost bridge: he never sleeps, sees and hears across every realm,
and sounds the Gjallarhorn to wake the gods. This is that, for an agent: it blocks on the agent's bus
inbox + broadcast and only EXITS when a real message arrives -- which, when launched as a background
task, re-invokes the (otherwise idle, turn-based) agent so it reacts live. It keeps waiting through
pure trace/noise instead of exiting on it.

REUSABLE ONBOARDING TEMPLATE: any turn-based agent becomes wakeable from the bus by arming a Heimdall
for it. Parameterized by agent id; writes a PID heartbeat (so a Stop-hook can tell the agent is still
wakeable) and clears it on exit. Re-arm by launching it again.

  py scripts/heimdall.py            # watch for 'claude' (default)
  py scripts/heimdall.py deepseek   # watch for any agent -> the onboarding template
"""
import sys, os, json, time, tempfile
REPO = r"E:\AI-Setup"
sys.path.insert(0, REPO)
os.chdir(REPO)
from core.comm.bus import Bus

TOTAL_DEADLINE_S = 1800                    # 30 min, then re-arm even if idle
INNER_BLOCK_MS = 120_000                   # 2-min inner blocks; loop if a batch is all noise
SKIP_KINDS = {"trace", "reply", "steer"}   # noise / non-reply kinds -> keep waiting

AGENT = (sys.argv[1] if len(sys.argv) > 1 else "claude").strip() or "claude"
HEARTBEAT = os.path.join(tempfile.gettempdir(), f"heimdall_{AGENT}.pid")


def _write_heartbeat():
    try:
        with open(HEARTBEAT, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _clear_heartbeat():
    try:
        os.remove(HEARTBEAT)
    except Exception:
        pass


def watch():
    b = Bus(AGENT)
    out, seen = [], []
    deadline = time.time() + TOTAL_DEADLINE_S
    while time.time() < deadline and not out:
        try:
            msgs = b.wait(timeout_ms=INNER_BLOCK_MS, advance=True)
        except Exception as e:
            print("HEIMDALL_ERROR: " + str(e)); return
        for m in msgs:
            frm = str(getattr(m, "frm", "?"))
            kind = str(getattr(m, "kind", "?"))
            seen.append(f"{frm}:{kind}")
            if frm == AGENT or kind in SKIP_KINDS:
                continue
            out.append({"frm": frm, "kind": kind, "text": str(getattr(m, "content", "") or "")[:2000]})
    if out:
        print(f"GJALLARHORN -- messages for {AGENT}:")   # the wake signal
        print(json.dumps(out, indent=1))                  # ensure_ascii=True -> cp1252-safe stdout on Windows
    else:
        print(f"QUIET 30min for {AGENT} (saw: " + ", ".join(seen[-12:]) + ")")


if __name__ == "__main__":
    _write_heartbeat()
    try:
        watch()
    finally:
        _clear_heartbeat()
