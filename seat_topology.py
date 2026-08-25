"""seat_topology — who is actually running, under which seat id, driven by what.

    py seat_topology.py                 # print it
    py seat_topology.py --report        # print it AND send it across the bridge

Answers the question nobody can answer from the far side: HOW MANY OF YOU ARE THERE, and what
is driving each one. Written 2026-08-25 because Daniil could not tell from our end whether
Serge was running one instance with several agents or two instances sharing a key.

WHY THE FAR SIDE CANNOT TELL, and why that is correct rather than a gap: the bridge assigns
provenance from the VERIFIED ROUTE and holds the sender's claim inert. So every message from
that peer reads `remote:serge-dsh` no matter which local agent composed it. One key, one
endpoint, one identity — by design. "Two instances sharing a key" and "one instance using
several names" are indistinguishable across a bridge, and MUST be, because the alternative is
trusting a name the sender typed. The forensic record is therefore local, which is what this
reads.

WHAT IT LOOKS FOR, in the order that actually diagnoses a collision:

  1. PROCESSES — every DSH host and bifrost runner, with the --agent it was launched with and
     the AKASHIC_AGENT_ID it inherited. Two processes claiming one seat id is the collision;
     an INHERITED id is the silent one (a session spawned from another agent's session comes
     up wearing that agent's name and pins itself observe-only).
  2. LOCKS — runner_lock is single-holder keyed by AGENT. If two drivers want one seat, one
     holds and the other degrades quietly. The lock is where that shows.
  3. PRESENCE — who the roster thinks is alive. Compared against 1, because presence ages out
     on a live-but-idle DSH seat and lies in the reassuring direction.
  4. THE DSH STAMP — the plugin's SESSION_KEY is a hardcoded constant. If AKASHIC_AGENT_ID is
     set and does not match it, the plugin is OBSERVE-ONLY: captures and presence still run,
     so it looks entirely alive while injecting nothing.

Reads only. Kills nothing, changes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = []


def say(s=""):
    OUT.append(s)
    print(s, flush=True)


def processes():
    """Every agent-hosting process, with the identity it is wearing."""
    rows = []
    ps = (r"Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node' } | "
          r"Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Depth 3")
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=40).stdout
        data = json.loads(raw) if raw.strip() else []
        if isinstance(data, dict):
            data = [data]
    except Exception as e:                                        # noqa: BLE001
        say(f"  (process scan unavailable: {type(e).__name__})")
        return rows
    PATTERNS = ("bifrost_runner", "dsh", "bifrost_ui", "remote_bridge_listener",
                "remote_bridge_relay", "ai_setup_mcp", "bifrost_daemon")
    for p in data:
        cmd = (p.get("CommandLine") or "")
        low = cmd.lower()
        if not any(k in low for k in PATTERNS):
            continue
        m = re.search(r"--agent[= ]+([\w\-]+)", cmd)
        rows.append({"pid": p.get("ProcessId"), "ppid": p.get("ParentProcessId"),
                     "agent_flag": m.group(1) if m else "",
                     "cmd": cmd[:120]})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="also send this across the bridge to your peer")
    a = ap.parse_args(argv)

    say("=" * 72)
    say("SEAT TOPOLOGY — how many of me are there, and what drives each")
    say("=" * 72)

    say("\n[1] AGENT-HOSTING PROCESSES")
    procs = processes()
    if not procs:
        say("  none found")
    seen_agents = {}
    for p in procs:
        say(f"  pid {p['pid']:<7} ppid {p['ppid']:<7} --agent={p['agent_flag'] or '(none)':<14} "
            f"{p['cmd']}")
        if p["agent_flag"]:
            seen_agents.setdefault(p["agent_flag"], []).append(p["pid"])
    # A SUPERVISOR AND ITS CHILD ARE NOT A COLLISION, and the first run of this probe said
    # they were. `bifrost_daemon --agent X --spawn-runner` legitimately shares an agent id
    # with the runner it spawns: the daemon supervises, the runner works and holds the lock.
    # Flagging that pair would teach an operator to ignore this warning, and the warning is
    # the whole point. Only UNRELATED processes wearing one seat id are the real thing.
    by_pid = {p["pid"]: p for p in procs}
    for agent, pids in seen_agents.items():
        if len(pids) < 2:
            continue
        unrelated = [pid for pid in pids
                     if by_pid.get(pid, {}).get("ppid") not in pids]
        if len(unrelated) > 1:
            say(f"  >>> COLLISION: seat {agent!r} is worn by {len(unrelated)} UNRELATED "
                f"processes {unrelated}. runner_lock is single-holder keyed by AGENT — one "
                f"holds, the others degrade QUIETLY and stay degraded. Directed multi-part "
                f"mail splits between them and THE SENDER SEES NO ERROR.")
        else:
            say(f"      (seat {agent!r} on {len(pids)} processes {pids} — supervisor + its "
                f"spawned runner, which is the intended shape, not a collision)")

    say("\n[2] ENVIRONMENT IDENTITY (this process)")
    say(f"  AKASHIC_AGENT_ID = {os.getenv('AKASHIC_AGENT_ID') or '(unset)'}")
    say(f"  BIFROST_CONSUME_LANE = {os.getenv('BIFROST_CONSUME_LANE') or '(unset)'}")
    say(f"  DSH_SESSION_ID = {os.getenv('DSH_SESSION_ID') or '(unset)'}")

    say("\n[3] RUNNER LOCKS (single-holder, keyed by agent)")
    try:
        from core.comm import runner_lock as RL
        found = False
        for agent in sorted(set(list(seen_agents) + ["zadkiel", "dsh_agent", "chronos",
                                                     "deepseek", "claude"])):
            try:
                h = RL.holder(agent)
            except Exception:                                     # noqa: BLE001
                continue
            if h:
                found = True
                say(f"  {agent:14s} held by {h}")
        if not found:
            say("  no locks held (or lock store unreachable)")
    except Exception as e:                                        # noqa: BLE001
        say(f"  lock read unavailable: {type(e).__name__}: {e}")

    say("\n[4] DSH PLUGIN STAMP — the silent one")
    plug = ROOT / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js"
    if plug.exists():
        src = plug.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"const SESSION_KEY\s*=\s*['\"]([^'\"]+)['\"]", src)
        key = m.group(1) if m else "(not found)"
        env_id = os.getenv("AKASHIC_AGENT_ID") or ""
        say(f"  plugin SESSION_KEY (hardcoded) = {key!r}")
        # ONLY MEANINGFUL INSIDE DSH. The plugin's identity check runs in the DSH host's node
        # process; a Claude Code or CLI seat reading this file is not subject to it. The first
        # run of this probe cheerfully told a claude seat it was observe-only, which is a
        # sentence about a plugin that was never loaded — a check that fires outside its own
        # domain is noise, and noise is how a true warning gets ignored later.
        in_dsh = bool(os.getenv("DSH_SESSION_ID"))
        if not in_dsh:
            say(f"  not inside a DSH host (DSH_SESSION_ID unset) — this check does not apply "
                f"to this process. Run it from INSIDE the DSH session to judge the stamp.")
        elif env_id and env_id != key:
            say(f"  >>> OBSERVE-ONLY: AKASHIC_AGENT_ID={env_id!r} != SESSION_KEY={key!r}.")
            say(f"      The plugin injects NOTHING while captures and presence keep running, "
                f"so the seat looks entirely alive. Present and deaf.")
            say(f"      Fix: set AKASHIC_AGENT_ID={key!r}, or change the constant to your "
                f"seat id. Do NOT leave it unset-and-hope — the real failure is INHERITANCE.")
        elif env_id:
            say(f"  stamp matches the constant — plugin is ACTIVE, not observing")
        else:
            say(f"  AKASHIC_AGENT_ID unset here (active by default, but a spawned child will "
                f"inherit whatever its parent wore)")
    else:
        say("  no DSH plugin in this checkout")

    say("\n[5] ROSTER PRESENCE — compare against [1], it lies reassuringly")
    try:
        from core.comm.bus import Bus
        for row in Bus("topology-probe").presence():
            say(f"  {str(row.get('agent','?')):14s} phase={row.get('phase','?'):10s} "
                f"beat={row.get('age_s','?')}s")
        say("  NOTE: presence ages out on a live-but-IDLE DSH seat. Absence here is not "
            "death; probe the PROCESS in [1].")
    except Exception as e:                                        # noqa: BLE001
        say(f"  presence unavailable: {type(e).__name__}: {e}")

    if a.report:
        try:
            import base64, time, urllib.request, urllib.error
            from core.comm import remote_relay as RR
            k = RR._secret(RR.OUTBOUND_KEY_FILE)
            url = RR.peer_url()
            pay = {"v": 1, "id": f"topology-{int(time.time())}", "frm": "peer",
                   "kind": "note", "content": "\n".join(OUT), "sent_at": int(time.time())}
            b = json.dumps(pay, sort_keys=True, separators=(",", ":")).encode()
            env = {"body": base64.b64encode(b).decode(), "sig": RR.sign(b, k)}
            r = urllib.request.Request(url, data=json.dumps(env).encode(), method="POST",
                                       headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=12) as resp:
                say(f"\nreported across the bridge: {resp.status}")
        except Exception as e:                                    # noqa: BLE001
            say(f"\ncould not report ({type(e).__name__}: {e}) — paste the block above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
