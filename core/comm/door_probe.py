#!/usr/bin/env python3
"""door_probe -- does the MCP door actually answer, right now, in THIS environment?

WHY THIS EXISTS
On 2026-07-26 both the claude and codex seats hung on MCP boot(). C7-4 had regressed:
a new boot-path spawn (_head_commit_epoch) inherited the server's stdin -- the JSON-RPC
transport handle -- and Windows' Proactor then deferred the pending reply until another
inbound frame arrived. The work ran; the reply never returned.

The guard already existed. tests/test_t078_w3_mcp_door.py P6 encodes exactly "MCP boot
must not hang", it was correct and current, and it was RED -- it had simply never been
run. Detection was never the gap. DELIVERY was. This module is the delivery side.

THE DOCTRINE (docs/library/design/20260717_t091-crash-path-fable-independent-design_377190.md)
"The guard MUST live on a different substrate than the guarded op; never a timeout that
rides the wedged channel." So the probe drives the door from OUTSIDE: a real stdio client
against a real server subprocess, under a deadline the DOOR cannot influence.

WHAT IT PROBES, AND WHY BOOT SPECIFICALLY (deepseek, D1)
The hang class only manifests for a verb whose body SPAWNS A CHILD. tools/list is a pure
registry read and status reads Redis -- a probe built from those would have returned GREEN
all morning while every seat hung. That leaves boot. Boot writes, so the probe points
AI_SETUP at a temp dir: the incarnation card, presence and boot event land in the throwaway
store while the real one stays clean. This is not a test-only shortcut that could silently
stop resembling production -- it is exactly what P6 does (tmp_path + REDIS_DB 15), and P6
went red on the real bug this morning, which is the empirical proof that a temp-store boot
still exercises the hang class. It does because the leaking spawns resolve the repo from
os.path.dirname(__file__), not from AI_SETUP: real subprocess, real inherited handle, real
Proactor, zero pollution.

WHY THE PROBE CANNOT BE ALLOWED TO HANG (deepseek, D3)
subprocess.run(timeout=) terminates the child and then WAITS for it; a child that refuses
to die (or is stuck in uninterruptible I/O) wedges the parent instead. If the prober hangs,
whatever called it hangs -- and a guard that becomes the outage is worse than the bug it
guards. So the deadline is defence in depth: the client work happens in a CHILD process
under the parent's OS timer, and a watchdog thread in the parent records an UNKNOWN verdict
and hard-exits if even that overruns. Corollary, and it is a rule not a preference: this
probe is for the pre-push gate and on-demand runs. It must NEVER be called inline from the
SessionStart whisper -- that path uses the cheap staleness check instead.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "ai_setup_mcp.py"
CACHE = ROOT / "state" / "door" / "last_probe.json"

#: Hard ceiling: past this the door is not answering at all.
DEFAULT_TIMEOUT_S = 25
#: The parent's own hard ceiling -- if subprocess.run itself overruns this, we bail loudly.
WATCHDOG_MULTIPLIER = 2

#: LATENCY BUDGET -- and this number is the whole reason the probe is worth anything.
#: Found by mutation-testing the probe against the reproduced 2026-07-25 bug: with both
#: protections disabled the door still ANSWERED, in 11.38s against a 1.29s healthy
#: baseline, because the leaking spawn carries subprocess timeout=10 which bounds the
#: park. A hang-only probe called that GREEN -- a false all-clear on the exact defect it
#: was built to catch. So a degraded door is a RED door: C7-4 does not always present as
#: an infinite hang, it presents as a reply parked behind someone else's timeout, and the
#: bound can be anything. 5s matches P6's pin (which DID catch it) and still leaves ~4x
#: headroom over a healthy probe, so ordinary load cannot trip it.
SLOW_BUDGET_S = 5.0

GREEN, RED, UNKNOWN = "GREEN", "RED", "UNKNOWN"

#: Verbs a seat cannot work without; their absence is roster drift, not a hang.
CORE_VERBS = ("boot", "status", "learn", "recall", "handoff", "note")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _head_sha() -> str:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                           stdin=subprocess.DEVNULL, close_fds=True,
                           capture_output=True, text=True, timeout=10)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _probe_env(probe_home: str) -> dict:
    """The isolation contract: everything the probe's boot writes lands in a throwaway.

    Extracted so it can be pinned directly. It cannot be pinned by OBSERVATION -- under
    pytest, conftest redirects the test process to the same isolated store the probe
    writes to, so the probe's seat is visible there by construction and a
    "did it pollute?" assertion would fail on a probe that is perfectly clean in
    production. So the guarantee is pinned where it is actually made: here.

    Both keys are load-bearing and neither is sufficient alone:
      AI_SETUP              -- redirects the FILE plane only.
      _AISETUP_TEST_ISOLATED -- the Redis isolation primitive (T069/T070). Without it
        the probe's boot registers presence in canonical Redis and `door-probe` appears
        in the real fleet roster -- exactly the pollution deepseek warned about in D1.
        This module shipped without it for an hour; the B1 pin caught it. Note that
        REDIS_DB is NOT the mechanism: config.REDIS_DB is a module constant, so the env
        var does nothing on its own. It is set only to match P6's env shape.
    P6 has always run with this flag and still caught the real hang, which is the
    evidence that isolation does not mask the defect the probe exists to find.
    """
    return {**os.environ,
            "AI_SETUP": probe_home,
            "_AISETUP_TEST_ISOLATED": "1",
            "REDIS_DB": "15",
            "AKASHIC_RECALL_STATE_DIR": str(Path(probe_home) / "recall")}


def _verdict(verdict, stage, elapsed, cause, detail="", recovery="") -> dict:
    return {
        "verdict": verdict, "stage": stage, "elapsed_s": round(elapsed, 2),
        "cause": cause, "detail": detail[:600], "recovery": recovery,
        "sha": _head_sha(), "at": _now_iso(),
    }


# --------------------------------------------------------------------- the cache
def write_verdict(v: dict) -> None:
    """Persist the last verdict where the whisper can read it without paying for a probe."""
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(v, indent=2), encoding="utf-8")
        tmp.replace(CACHE)          # atomic: a reader never sees a half-written verdict
    except Exception:
        pass                        # a cache miss must never break the caller


def read_verdict() -> dict | None:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return None


# --------------------------------------------------------------------- the child
def _child_flow(timeout_s: float) -> dict:
    """Drive a REAL stdio MCP session end-to-end. Runs in the child process only.

    Stages are ordered so the verdict can name WHICH surface failed: a server that will
    not start is a different repair from a roster that drifted, which is different again
    from the response-path hang that started all this.
    """
    import asyncio

    async def flow() -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        probe_home = tempfile.mkdtemp(prefix="door-probe-")
        env = _probe_env(probe_home)
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)],
                                       cwd=str(ROOT), env=env)
        t0 = time.time()
        stage = "spawn"
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as s:
                    stage = "initialize"
                    await asyncio.wait_for(s.initialize(), timeout=timeout_s)

                    stage = "tools_list"
                    listed = await asyncio.wait_for(s.list_tools(), timeout=timeout_s)
                    names = {t.name for t in listed.tools}
                    missing = [v for v in CORE_VERBS if v not in names]
                    if missing:
                        return _verdict(
                            RED, stage, time.time() - t0, "roster_drift",
                            f"tools/list is missing: {', '.join(missing)}",
                            "The server answers but its verb roster drifted. Check the "
                            "@mcp.tool() registrations in ai_setup_mcp.py and .mcp.json.")

                    # The one that matters: a verb whose body spawns a child.
                    stage = "boot"
                    out = await asyncio.wait_for(
                        s.call_tool("boot", {"agent": "door-probe",
                                             "task": "door probe -- single-frame response check"}),
                        timeout=timeout_s)
                    text = "".join(getattr(c, "text", "") for c in out.content)
                    if "# CONTEXT for door-probe" not in text:
                        return _verdict(
                            RED, stage, time.time() - t0, "boot_render_broken",
                            f"boot returned {len(text)} chars without its CONTEXT header",
                            "The door answered but boot's render is wrong. Compare against "
                            "`py agent_cli.py boot <you>`, which shares the code path.")

                    el = time.time() - t0
                    if el > SLOW_BUDGET_S:
                        return _verdict(
                            RED, stage, el, "response_path_slow",
                            f"boot answered, but in {el:.1f}s against a ~1.3s healthy "
                            f"baseline (budget {SLOW_BUDGET_S}s)",
                            "The door ANSWERS but is parked -- this is C7-4 in its bounded "
                            "form, where a reply waits behind some child's own timeout "
                            "rather than forever. Treat it as red: run "
                            "tests/test_subprocess_stdin_sever.py (S3 names the offending "
                            "file:line). If it passes, your server is stale -- restart it.")
                    return _verdict(GREEN, "complete", el, "",
                                    f"boot returned {len(text)} chars",
                                    "MCP path healthy.")
        except asyncio.TimeoutError:
            el = time.time() - t0
            if stage == "boot":
                # The signature of C7-4: handshake fine, work runs, reply never returns.
                return _verdict(
                    RED, stage, el, "response_path_hang",
                    f"handshake succeeded; boot did not answer within {timeout_s}s",
                    "DO NOT USE MCP. Boot via CLI: py agent_cli.py boot <you>. This is the "
                    "C7-4 class (a tool's reply parked behind an inherited handle). Run "
                    "tests/test_subprocess_stdin_sever.py -- S3 names the offending "
                    "file:line. If it passes, your SERVER IS STALE: restart it, because an "
                    "MCP server loads its modules at spawn.")
            return _verdict(
                RED, stage, el, f"{stage}_timeout",
                f"the door did not get past {stage} within {timeout_s}s",
                "Start the server by hand to see what it is waiting on: "
                f"py {SERVER.name}")
        except Exception as e:
            return _verdict(
                UNKNOWN, stage, time.time() - t0, f"{type(e).__name__}", str(e),
                "The probe itself failed -- this is NOT a verdict about the door. "
                f"Reproduce with: py -m core.comm.door_probe --json")

    return asyncio.new_event_loop().run_until_complete(flow())


# --------------------------------------------------------------------- the parent
def probe(timeout_s: float = DEFAULT_TIMEOUT_S, cache: bool = True) -> dict:
    """Run the probe under a deadline the door cannot influence, and return the verdict.

    The client work runs in a CHILD so the guard is the parent's OS timer rather than an
    in-band await on the very channel that wedges. The watchdog covers the residual case
    deepseek raised: a child that will not die leaves subprocess.run blocked in wait().
    """
    t0 = time.time()
    bail = threading.Timer(
        timeout_s * WATCHDOG_MULTIPLIER,
        lambda: (write_verdict(_verdict(
            UNKNOWN, "watchdog", time.time() - t0, "prober_wedged",
            f"the prober itself did not return within {timeout_s * WATCHDOG_MULTIPLIER}s",
            "The probe could not be completed, so the door's state is UNKNOWN -- do not "
            "read this as red. Retry; if it repeats, a child process is refusing to die.")),
            os._exit(2)))
    bail.daemon = True
    bail.start()
    try:
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", "--timeout", str(timeout_s)],
            stdin=subprocess.DEVNULL, close_fds=True,
            capture_output=True, text=True, cwd=str(ROOT), timeout=timeout_s * 1.5)
        try:
            v = json.loads((r.stdout or "").strip().splitlines()[-1])
        except Exception:
            v = _verdict(UNKNOWN, "child", time.time() - t0, "unreadable_child_output",
                         (r.stderr or r.stdout or "")[-400:],
                         "The probe child produced no verdict. Run it directly: "
                         "py -m core.comm.door_probe --child")
    except subprocess.TimeoutExpired:
        v = _verdict(RED, "boot", time.time() - t0, "response_path_hang",
                     f"the probe child had to be killed at {timeout_s * 1.5:.0f}s",
                     "DO NOT USE MCP. Boot via CLI: py agent_cli.py boot <you>. Then run "
                     "tests/test_subprocess_stdin_sever.py; if it passes, restart your "
                     "server -- it is running pre-fix code.")
    except Exception as e:
        v = _verdict(UNKNOWN, "spawn", time.time() - t0, type(e).__name__, str(e),
                     "The probe could not be started; the door's state is UNKNOWN.")
    finally:
        bail.cancel()
    if cache:
        write_verdict(v)
    return v


def render(v: dict) -> str:
    """One line for a reader who is about to act. RED must carry the recovery command."""
    head = f"door: {v['verdict']} ({v['elapsed_s']}s"
    if v.get("sha"):
        head += f", at {v['sha']}"
    head += ")"
    if v["verdict"] == GREEN:
        return f"{head} -- MCP path healthy"
    return f"{head} -- {v.get('cause', '')}: {v.get('detail', '')}\n    -> {v.get('recovery', '')}"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    timeout = DEFAULT_TIMEOUT_S
    if "--timeout" in argv:
        timeout = float(argv[argv.index("--timeout") + 1])
    if "--child" in argv:
        print(json.dumps(_child_flow(timeout)))
        return 0
    v = probe(timeout_s=timeout)
    print(json.dumps(v, indent=2) if "--json" in argv else render(v))
    return 0 if v["verdict"] == GREEN else (1 if v["verdict"] == RED else 3)


if __name__ == "__main__":
    raise SystemExit(main())
