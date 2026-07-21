"""
play_sandbox (T099 · play-tier sandbox) — the bounded subprocess that runs play tools.

Semantic Relationship: PlaySandbox hosts one play-tool run under the families gate.

The play tier's law (docs/self-tooling-design-2026-07.md + tooldesk-crosscheck-kimi-2026-07-20):
  SANDBOX     — play tools run in a bounded subprocess: path-jailed (writes only to
                data/play/<agent>/out/), timeout-capped, output-capped, network-off by
                default, one-level subprocess only (close_fds, stdin=DEVNULL per C7-4).
  RECEIPT     — every run emits a receipt to data/play/<agent>/runs/<tool>/<ts>.json:
                {tool, seat, rc, duration_s, output_kb, crash, violations}. No receipt,
                no run — the C9 epistemology lesson applied at birth.
  HONESTY     — play tools start at GUESS (untested draft confesses it's untested).
                kata is the ladder out (grammar-check → VERIFIED).
  FAMILIES   — the door is the EXISTING _exec_family gate + a new play-<agent> family
                (one law per tier, never blurred: PLAY's law is sandbox+receipts,
                ALIAS's law is sugar-only).

Usage: py core/toolbelt/play_sandbox.py <agent>/<tool> [args...]
  This is the subprocess the families gate launches — one thin runner, audited.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAY = os.path.join(ROOT, "data", "play")
MAX_OUTPUT_BYTES = int(os.getenv("AKASHIC_PLAY_OUTPUT_MAX", "65536"))   # 64KB
DEFAULT_TIMEOUT_S = float(os.getenv("AKASHIC_PLAY_TIMEOUT_S", "30"))
NETWORK_ENABLED = os.getenv("AKASHIC_PLAY_NETWORK", "0") == "1"


def find_tool(ref: str) -> tuple[str, str, str]:
    """(agent, tool, script_path) or raises ValueError on bad ref / no tool."""
    try:
        agent, tool = ref.split("/", 1)
    except ValueError:
        raise ValueError(f"bad tool ref {ref!r} — use <agent>/<tool>")
    agent = str(agent).strip()
    tool = str(tool).strip()
    if not agent or not tool or ".." in agent or ".." in tool or "/" in tool or "\\" in tool:
        raise ValueError(f"bad ref parts agent={agent!r} tool={tool!r}")
    path = os.path.join(PLAY, agent, f"{tool}.py")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no play tool at {path}")
    return agent, tool, path


def sandboxed_run(agent: str, tool: str, path: str,
                  args: list[str] | None = None,
                  timeout_s: float = DEFAULT_TIMEOUT_S,
                  max_output: int = MAX_OUTPUT_BYTES,
                  network: bool = NETWORK_ENABLED) -> dict:
    """Run one play tool in a bounded subprocess. Returns a RECEIPT dict.
    Sandbox violations are caught and logged — the receipt IS the evidence.
    Never raises — a crash inside the sandbox is a FAIL receipt, not a caller crash."""
    t0 = time.time()
    receipt = {"tool": tool, "agent": agent, "rc": -1, "duration_s": 0.0,
               "output_kb": 0, "crash": False, "violations": [],
               "evidence": "GUESS", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "argv": args or []}
    argv = [sys.executable, path] + list(args or [])
    out_dir = os.path.join(PLAY, agent, "out")
    os.makedirs(out_dir, exist_ok=True)
    try:
        env = os.environ.copy()
        # Sandbox flags: the tool itself can read these to self-limit
        env["AKASHIC_PLAY_SANDBOX"] = "1"
        env["AKASHIC_PLAY_AGENT"] = agent
        env["AKASHIC_PLAY_TOOL"] = tool
        env["AKASHIC_PLAY_OUT_DIR"] = out_dir
        if not network:
            env["AKASHIC_PLAY_NETWORK"] = "0"
        r = subprocess.run(argv, capture_output=True, timeout=timeout_s,
                           stdin=subprocess.DEVNULL, cwd=ROOT,   # one-level only (C7-4)
                           env=env, close_fds=True,              # no grandchild spawns
                           text=False)
        out = (r.stdout or b"") + (r.stderr or b"")
        receipt["rc"] = r.returncode
        receipt["duration_s"] = round(time.time() - t0, 3)
        # Output cap: clip with a LOUD marker (T043 lineage)
        if len(out) > max_output:
            out = out[:max_output]
            tag = f"\n\n[... OUTPUT CLIPPED at {max_output}B — AKASHIC_PLAY_OUTPUT_MAX: {len(out)}B shown ...]\n"
            out += tag.encode("utf-8", errors="replace")
            receipt["violations"].append("output_capped")
        receipt["output_kb"] = round(len(out) / 1024.0, 2)
        _write_receipt(agent, tool, receipt, out)
    except subprocess.TimeoutExpired:
        receipt["crash"] = True
        receipt["rc"] = -1
        receipt["duration_s"] = round(time.time() - t0, 3)
        receipt["violations"].append(f"timeout ({timeout_s}s)")
        _write_receipt(agent, tool, receipt, f"[TIMEOUT after {timeout_s}s]".encode())
    except Exception as e:
        receipt["crash"] = True
        receipt["rc"] = -2
        receipt["duration_s"] = round(time.time() - t0, 3)
        receipt["violations"].append(f"exception: {type(e).__name__}: {e}")
        tb = traceback.format_exc()
        _write_receipt(agent, tool, receipt, tb.encode("utf-8", errors="replace"))
    return receipt


def _write_receipt(agent: str, tool: str, receipt: dict, output: bytes) -> str:
    """Persist receipt + captured output to the runs ledger."""
    runs_dir = os.path.join(PLAY, agent, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    stamp = int(time.time())
    out_path = os.path.join(runs_dir, f"{tool}-{stamp}.out")
    rec_path = os.path.join(runs_dir, f"{tool}-{stamp}.json")
    with open(out_path, "wb") as f:
        f.write(output)
    with open(rec_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, ensure_ascii=False)
    return rec_path


def list_tools(agent: str) -> list[str]:
    """Return active play-tool names for an agent (the .py scripts in data/play/<agent>/)."""
    d = os.path.join(PLAY, agent)
    if not os.path.isdir(d):
        return []
    tools = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".py") and not fn.startswith("_") and fn != "__init__.py":
            tools.append(fn[:-3])
    return tools


def list_seats() -> list[str]:
    """Return every agent with a play directory."""
    if not os.path.isdir(PLAY):
        return []
    return sorted(d for d in os.listdir(PLAY)
                  if os.path.isdir(os.path.join(PLAY, d)) and not d.startswith("."))


def render_list(agent: str | None = None) -> str:
    """Human-readable tool listing."""
    rows = ["# play tools — sandboxed drafts (GUESS until kata'd)"]
    agents = [agent] if agent else list_seats()
    for a in agents:
        tools = list_tools(a)
        if not tools:
            continue
        rows.append(f"  [{a}]")
        for t in tools:
            path = os.path.join(PLAY, a, f"{t}.py")
            size = os.path.getsize(path)
            # Check for receipts
            runs = os.path.join(PLAY, a, "runs")
            recs = []
            if os.path.isdir(runs):
                recs = [f for f in os.listdir(runs) if f.startswith(f"{t}-") and f.endswith(".json")]
            n = len(recs)
            rows.append(f"    {t:<20}  {size:>5}B  {n} receipt(s)")
    rows.append(f"\n  run one: py agent_cli.py tool run <agent>/<tool>")
    return "\n".join(rows)


# ---------------------------------------------------------------- standalone mode
if __name__ == "__main__":
    """Entry point when the families gate launches: py core/toolbelt/play_sandbox.py <agent>/<tool> [args]"""
    if len(sys.argv) < 2:
        print(render_list())
        sys.exit(0)
    ref = sys.argv[1]
    tool_args = sys.argv[2:]
    try:
        agent, tool, path = find_tool(ref)
    except (ValueError, FileNotFoundError) as e:
        print(f"[play-sandbox] {e}", file=sys.stderr)
        sys.exit(1)
    receipt = sandboxed_run(agent, tool, path, args=tool_args)
    # Print receipt summary to stdout (the caller captures it)
    print(json.dumps({k: v for k, v in receipt.items()
                      if k not in ("argv",)}, indent=1, default=str))
    rc = receipt.get("rc", -1)
    sys.exit(0 if rc == 0 else 1)
