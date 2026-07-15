"""check_door_parity -- guard the agent-facing DOOR surface against silent fragmentation.

The agent surface is spread over three doors: the CLI (agent_cli.py, 33 verbs), the MCP server
(ai_setup_mcp.py, 22 tools), and the low-level bus API (core/comm/bifrost_api.py, 18 methods). They
drift silently -- a verb added to one, forgotten on the others -- and that is the single biggest
source of agent cognitive load (you must know WHICH door holds each capability). First membrane slice:
make the surface EXPLICIT and RATCHET it.

This does NOT unify everything now. It:
  * classifies EVERY CLI/MCP verb in the MANIFEST below (shared / cli_only / mcp_only / gap),
  * FAILS on a NEW unclassified verb (stops new drift) or a `shared` verb missing from a door (regression),
  * reports `gap`s = the known CLI<->MCP debt to pay down in later slices (does NOT fail on those).

The bus API is a separate programmatic door (a different abstraction level, not a CLI/MCP verb); it is
REPORTED for visibility but not parity-enforced in v1.

Run:  py scripts/check_door_parity.py            # gate (exit 1 on unclassified/regressed verb)
      py scripts/check_door_parity.py --report   # just print the three surfaces + the manifest
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(n):
    return n.replace("-", "_")


def cli_verbs():
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    return sorted(set(_norm(m) for m in re.findall(r'add_parser\(\s*["\']([a-zA-Z0-9_-]+)["\']', src)))


def mcp_tools():
    tree = ast.parse(open(os.path.join(ROOT, "ai_setup_mcp.py"), encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any("mcp.tool" in ast.unparse(d) for d in node.decorator_list):
                out.append(_norm(node.name))
    return sorted(set(out))


def bus_methods():
    tree = ast.parse(open(os.path.join(ROOT, "core/comm/bifrost_api.py"), encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and "BifrostAPI" in node.name:
            out += [m.name for m in node.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")]
    return sorted(set(out))


# The declared intended surface. Every CLI/MCP verb MUST appear here (the ratchet).
#   shared   -> must be on BOTH cli and mcp
#   cli_only -> intentionally CLI-only (local/diagnostic/operator/needs-shell)
#   mcp_only -> intentionally MCP-only
#   gap      -> KNOWN DEBT: a core verb reachable on one door but not the other; pay down later.
MANIFEST = {
    # --- shared (16): the core verb surface, on both doors ---
    "boot": "shared", "learn": "shared", "recall": "shared", "recall_at": "shared",
    "recall_feedback": "shared", "stats": "shared", "status": "shared", "story": "shared",
    "events": "shared", "log": "shared", "promoted": "shared", "graduate": "shared",
    "injections": "shared", "handoff": "shared", "bifrost_send": "shared", "bifrost_sync": "shared",
    # slice 1b: note/notes + lock/unlock/locks + tag_anti_pattern + bifrost_nudge now have MCP twins
    "note": "shared", "notes": "shared", "lock": "shared", "unlock": "shared", "locks": "shared",
    "tag_anti_pattern": "shared", "bifrost_nudge": "shared",
    # R8 (T059): knowledge_map walks the lesson/note/doc graph -- an agent-facing read verb
    # (B5's whole point: an agent OR Daniel walks the knowledge), so it ships on both doors.
    "knowledge_map": "shared",
    # --- cli_only (8): local diagnostics / operator controls / needs shell+git ---
    "discover": "cli_only", "console_log": "cli_only", "harnesses": "cli_only",
    "recall_counters": "cli_only", "triage": "cli_only", "wrap": "cli_only",
    "bifrost_pause": "cli_only", "bifrost_resume": "cli_only",
    "list": "cli_only",   # CLI alias for `recall ""`; MCP's recall(query="") already lists all
    "fleet": "cli_only",  # local-model dispatch/roster — operator-oriented, not an agent verb
    "doctor": "cli_only",  # L2 fleet-liveness doctor (T030): operator diagnostic; agents get its
                           # one-liner in every boot; an MCP twin lands with a real MCP-agent need
    "episode": "cli_only",  # session bookends: consumed by the Bifrost UI via CLI --json (S1). An MCP
                            # twin is deferred to the S3 agent-close/auto-suggest path (design doc §7).
    "task": "cli_only",     # the coordination door over the ledger (conductor). CLI+operator-oriented
                            # (propose/approve are human-gated); MCP twin when an MCP agent needs to
                            # drive task transitions programmatically (arch-triage P1 2026-07-07).
    "bifrost_ack": "cli_only",  # P6 (T026): deliberate handled-it record. Runners auto-ack in-process
                                # (promoter.ack direct); an MCP twin lands with the P7 lookback set if
                                # MCP agents start handling salient asks themselves.
    "lookback": "cli_only",     # P7 (T027): rationale-corpus query. MCP twin deferred until an MCP
                                # agent needs WHY-lookback programmatically (same trigger as bifrost_ack).
    "recall_curate": "cli_only",  # corpus curation (bench/unbench/ghost-prune) -- operator action at
                                  # the wrap boundary (recall vNext loop 1, 2026-07-08); the wrap nudge
                                  # prints the exact command. MCP twin if an agent ever self-curates.
    "fence": "cli_only",  # R2 (T053): fence workspace door. Fence participants today drive it via
                          # CLI (claude) or the runner ToolBox (deepseek); an MCP twin lands when an
                          # MCP-hosted agent takes a fence seat (same trigger family as lookback).
    "flow": "cli_only",   # R3 (T054): flow-trace waterfall -- operator/agent diagnostic; MCP twin
                          # rides the T067 ToolBox-parity wave with delta (same trigger family).
    # --- mcp_only: Gemini web consumers + bus conveniences the CLI already covers ---
    "ask_gemini_web": "mcp_only", "ask_gemini_panel": "mcp_only", "gemini_web_login": "mcp_only",
    "bifrost_broadcast": "mcp_only",  # CLI path: bifrost-send --broadcast
    "bifrost_inbox": "mcp_only",      # CLI path: bifrost-sync --consume (same read)
    "bifrost_presence": "mcp_only",   # CLI path: bifrost-sync (refreshes + shows presence)
    # --- gap: KNOWN CLI<->MCP debt to pay down ---
    "delta": "gap",   # R1 delta door (T052): agent-facing "what moved since I was last here",
                      # shipped CLI-only; an MCP twin is the natural next step (same trigger as
                      # knowledge_map's agent-ergonomics intent). Flagged here, not silently dropped.
}


def check():
    cli, mcp = set(cli_verbs()), set(mcp_tools())
    fails, gaps = [], []
    # 1. every real verb must be classified (the ratchet: no new unclassified drift)
    for v in sorted((cli | mcp)):
        if v not in MANIFEST:
            door = "CLI" if v in cli else "MCP"
            fails.append(f"unclassified verb '{v}' (on {door}) -> add it to MANIFEST in check_door_parity.py "
                         f"(shared / cli_only / mcp_only / gap)")
    # 2. manifest expectations vs reality
    for v, cat in sorted(MANIFEST.items()):
        on_cli, on_mcp = v in cli, v in mcp
        if cat == "shared" and not (on_cli and on_mcp):
            missing = "MCP" if on_cli else "CLI"
            fails.append(f"'{v}' is declared shared but is MISSING from {missing} (regression)")
        elif cat == "cli_only" and on_mcp:
            fails.append(f"'{v}' is declared cli_only but appears on MCP -> reclassify")
        elif cat == "mcp_only" and on_cli:
            fails.append(f"'{v}' is declared mcp_only but appears on CLI -> reclassify")
        elif cat == "gap":
            gaps.append(v)
        # a verb in the manifest that no longer exists on any door -> stale manifest entry
        if cat in ("shared", "cli_only", "gap") and not on_cli and not on_mcp:
            fails.append(f"'{v}' is in the MANIFEST but exists on NO door -> remove the stale entry")
    return fails, gaps, cli, mcp


def main():
    fails, gaps, cli, mcp = check()
    bus = bus_methods()
    report = "--report" in sys.argv
    if report:
        print(f"CLI ({len(cli)}): {', '.join(sorted(cli))}\n")
        print(f"MCP ({len(mcp)}): {', '.join(sorted(mcp))}\n")
        print(f"BUS ({len(bus)}, separate programmatic door — not parity-enforced): {', '.join(bus)}\n")
        print(f"shared: {len(cli & mcp)}  |  cli-only: {len(cli - mcp)}  |  mcp-only: {len(mcp - cli)}")
    if gaps:
        print(f"\nKNOWN GAPS (CLI<->MCP debt, {len(gaps)}): {', '.join(sorted(gaps))}")
        print("  ^ backlog for later membrane slices; not a failure.")
    for f in fails:
        print("FAIL:", f)
    if fails:
        print(f"\n{len(fails)} FAIL — the door surface drifted. Classify/fix before shipping.")
        return 1
    print(f"\nPASS: door surface matches the manifest ({len(gaps)} known gap(s) tracked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
