"""check_door_parity -- guard the agent-facing DOOR surface against silent fragmentation.

The agent surface is spread over FOUR doors: the CLI (agent_cli.py), the MCP server
(ai_setup_mcp.py), the runner ToolBox (deepseek_chat.py -- the third door, ENFORCED since
T067-1: `knowledge_map` was declared shared, the guard checked CLI+MCP, declared PASS, and
the one agent who needed it never got the tool), and the low-level bus API
(core/comm/bifrost_api.py). They drift silently -- a verb added to one, forgotten on the
others -- and that is the single biggest source of agent cognitive load (you must know
WHICH door holds each capability). Membrane rule: make the surface EXPLICIT and RATCHET it.

This does NOT unify everything now. It:
  * classifies EVERY CLI/MCP/ToolBox verb in the MANIFEST below
    (shared / cli_only / mcp_only / toolbox_only / gap),
  * FAILS on a NEW unclassified verb on ANY enforced door (stops new drift),
  * FAILS on a `shared` verb missing from CLI or MCP (regression),
  * FAILS on a `shared` verb with NO ToolBox coverage: present by name, covered by a
    declared alias (the ToolBox spells some shared verbs its own way: recall ->
    knowledge_recall), or explicitly EXEMPTED with a rationale (the ToolBox is agentic-tool
    primitives, not a CLI mirror -- design non-goal (g)). A new shared verb with none of
    the three is exactly the knowledge_map class, and it fails loud,
  * notes (never fails) cli_only/mcp_only verbs that ALSO live on the ToolBox -- the
    classification describes CLI<->MCP parity, not ToolBox access (agent self-service),
  * reports `gap`s = the known CLI<->MCP debt to pay down in later slices (does NOT fail).

The bus API is a separate programmatic door (a different abstraction level, not a verb
surface); it is REPORTED for visibility but not parity-enforced.

Run:  py scripts/checkers/check_door_parity.py            # gate (exit 1 on unclassified/regressed verb)
      py scripts/checkers/check_door_parity.py --report   # print the four surfaces + the manifest
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth


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


def toolbox_verbs():
    """The third door (T067-1): every public method on the runner ToolBox, including runner
    plumbing (execute/release_written_locks) -- the ratchet SEES everything; hiding plumbing
    behind an exclusion list would recreate the exact blind spot this slice closes."""
    # 2026-07-25 (deepseek's find): this parsed scripts/deepseek_chat.py, where ToolBox
    # USED to live. The class moved to core/comm/toolbox.py and the parser did not follow,
    # so it matched no ClassDef, returned [], and every shared verb read as having NO
    # ToolBox coverage -- 66 phantom FAIL lines, including the two T067 pins that sat in
    # the baseline being treated as evidence of real door divergence. The canary was not
    # silent because the doors agreed; it was dead. Same genus as the GROUND FIRST pointer
    # the same night: a migration moved the file and the reference did not follow.
    # A guard that cannot find its subject must SAY SO, not report a clean empty set --
    # so the missing-class case now fails loudly instead of cascading phantom failures.
    src = os.path.join(ROOT, "core/comm/toolbox.py")
    tree = ast.parse(open(src, encoding="utf-8").read())
    out = []
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ToolBox":
            found = True
            out += [m.name for m in node.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")]
    if not found:
        raise RuntimeError(
            f"door-parity guard cannot find `class ToolBox` in {src} -- it has moved again. "
            "Fix the path; an empty verb list would silently pass or phantom-fail every "
            "shared verb.")
    return sorted(set(_norm(n) for n in out))


# A few deliberate vocabulary pairs differ across CLI and MCP.  The canonical key is
# the CLI spelling after '-' -> '_' normalization; the value is the actual MCP tool.
# The guard treats the pair as one shared capability and verifies both endpoints.
CLI_MCP_ALIASES = {
    "packet_trace": "packet_route",
    "packet_stats": "packet_route_stats",
}


# The declared intended surface. Every CLI/MCP capability MUST appear here (the ratchet),
# either by its real name or through CLI_MCP_ALIASES.
#   shared   -> must be on BOTH cli and mcp
#   cli_only -> intentionally CLI-only (local/diagnostic/operator/needs-shell)
#   mcp_only -> intentionally MCP-only
#   gap      -> KNOWN DEBT: a core verb reachable on one door but not the other; pay down later.
MANIFEST = {
    # --- shared: the core verb surface, on both doors ---
    "boot": "shared", "learn": "shared", "recall": "shared", "recall_at": "shared",
    "recall_feedback": "shared", "stats": "shared", "status": "shared", "story": "shared",
    "events": "shared", "log": "shared", "promoted": "shared", "graduate": "shared",
    "injections": "shared", "handoff": "shared", "bifrost_send": "shared", "bifrost_sync": "shared",
    # slice 1b: note/notes + lock/unlock/locks + tag_anti_pattern + bifrost_nudge now have MCP twins
    "note": "shared", "notes": "shared", "lock": "shared", "unlock": "shared", "locks": "shared",
    "tag_anti_pattern": "shared", "bifrost_nudge": "shared",
    # R8 (T059): knowledge_map walks the lesson/note/doc graph -- an agent-facing read verb
    # (B5's whole point: an agent OR Daniel walks the knowledge), so it ships on both doors.
    "knowledge_map": "shared", "task": "shared",
    # T060 N0: dry-run explanation + bounded observation counters are read-only on both doors.
    "packet_trace": "shared", "packet_stats": "shared",
    # --- T067 backlog, classified by deepseek 2026-07-25 ---
    # These 23 accumulated invisibly behind a DEAD CANARY: toolbox_verbs() parsed the file
    # `class ToolBox` used to live in, so it returned an EMPTY set and phantom-failed
    # everything (66 fails, all noise). With the parser repaired (dc107d2) the real backlog
    # surfaced. deepseek classified all 23 against agent_cli.py's own add_parser calls:
    # 22 CLI-only operator/author/diagnostic surfaces, 1 MCP-only health check. No gaps.
    "alias": "cli_only",           # toolbelt authoring: mint/list/retire verb aliases
    "audit": "cli_only",           # belief-vs-state audit; operator diagnostic, writes nothing
    "bench": "cli_only",           # S0 triage bench: operator mailbox management
    "bifrost_drain": "cli_only",   # drain a PEER's lane -- operator intervention, not self-service
    "capture": "cli_only",         # full-fidelity bus read by stream id; forensic tool
    "clobber_scan": "cli_only",    # static scan for unconditional shared-key writes (W47)
    "defer": "cli_only",           # capability-gated standing queue (W33)
    "doc": "cli_only",             # seed a new doc with the header contract; authoring door
    "flightdeck": "cli_only",      # cockpit one-pager (W25); operator dashboard
    "followup": "cli_only",        # charter question-back (W46)
    "kata": "cli_only",            # grammar-prove a toolbelt alias against the door
    "kit": "cli_only",             # install a kit bundle on a seat's belt (T099)
    # deepseek classified this cli_only ("operator diagnostic, observation only") and the
    # guard refuted it TWICE, which is the guard working: first that mailbox is already on
    # the MCP door (so not cli_only), then that it is absent from the ToolBox (so not
    # shared either). 22 of its 23 calls held; the one that did not was caught by the
    # checker it was helping to fix. Recorded as a `gap` -- the honest label for a verb on
    # two doors and missing from the third. Gaps are REPORTED, never silenced, and this one
    # is tracked as a followup rather than left to live in a comment.
    "mailbox": "gap",              # T095 M0 shadow mailbox: CLI+MCP, absent from ToolBox
    "roster": "gap",               # T108 S2 seat directory: CLI only; agents need an MCP read twin
    "stand_down": "gap",           # T086 session yield: CLI only; no MCP lifecycle twin yet
    "new": "cli_only",             # subcommand of `doc`
    "pulse": "cli_only",           # LIFEWORKERS pressure map (W25)
    "run": "cli_only",             # execute a toolbelt alias
    "suite_baseline": "cli_only",  # record/compare the pytest baseline; needs shell
    "tally": "cli_only",           # local counter roll-up
    "toast": "cli_only",           # peer credit; receipt verifies against the learning store
    "tool": "cli_only",            # toolbelt introspection
    "unwedge": "cli_only",         # operator recovery for a wedged seat
    "wish": "cli_only",            # append to WISHLIST.md -- author surface, needs the repo
    "diag_echo_slow": "mcp_only",  # MCP server health check; no CLI meaning
    # --- cli_only: local diagnostics / operator controls / needs shell+git ---
    "discover": "cli_only", "console_log": "cli_only", "harnesses": "cli_only",
    "recall_counters": "cli_only", "triage": "cli_only", "wrap": "cli_only",
    "bifrost_pause": "cli_only", "bifrost_resume": "cli_only",
    "bifrost_skip_to_now": "cli_only", "bifrost_standby": "cli_only",
    "list": "cli_only",   # CLI alias for `recall ""`; MCP's recall(query="") already lists all
    "fleet": "cli_only",  # local-model dispatch/roster — operator-oriented, not an agent verb
    "doctor": "cli_only",  # L2 fleet-liveness doctor (T030): operator diagnostic; agents get its
                           # one-liner in every boot; an MCP twin lands with a real MCP-agent need
    "episode": "cli_only",  # session bookends: consumed by the Bifrost UI via CLI --json (S1). An MCP
                            # twin is deferred to the S3 agent-close/auto-suggest path (design doc §7).
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
                      # knowledge_map's agent-ergonomics intent). Flagged here, not silently
                      # dropped. T067-1: the ToolBox now covers deepseek's need; the CLI<->MCP
                      # debt itself stays open.
    # --- toolbox_only (T067-1): the third door's own verbs -- agentic-tool primitives and
    #     runner-internal machinery with no CLI/MCP twin by design. Ratcheted like the rest:
    #     a NEW public ToolBox method must be classified here or the guard fails. ---
    "read_file": "toolbox_only", "list_directory": "toolbox_only", "find_files": "toolbox_only",
    "search_files": "toolbox_only",                       # file I/O primitives
    "git_log": "toolbox_only", "git_diff": "toolbox_only", "git_show": "toolbox_only",
    "git_status": "toolbox_only",                         # git inspection primitives
    "knowledge_recall": "toolbox_only",  # ToolBox spelling of shared `recall` (alias below)
    "knowledge_learn": "toolbox_only",   # ToolBox spelling of shared `learn` (alias below)
    "knowledge_note": "toolbox_only",    # ToolBox spelling of shared `note` (alias below)
    "knowledge_boot": "toolbox_only",    # ToolBox spelling of shared `boot` (alias below)
    "knowledge_full": "toolbox_only",    # CLI reaches this as `recall --full`
    "memory_note": "toolbox_only", "memory_recall": "toolbox_only",  # private scratchpad, no twin
    "write_file": "toolbox_only", "edit_file": "toolbox_only",       # guarded write (T048/T050)
    "run_command": "toolbox_only",       # gated shell
    "web_search": "toolbox_only",        # local websearch bridge
    "ask_clarification": "toolbox_only", # R7 (T058) mid-task human question, runner-internal
    "reload_ui": "toolbox_only",         # exists-but-disabled for deepseek (UI is harness-owned)
    "bifrost_steer": "toolbox_only",     # soft steer; CLI covers the family via bifrost-nudge
    "bifrost_hint": "toolbox_only",      # compact context hint, ToolBox-only
    "bifrost_dashboard": "toolbox_only", # T081-W7 text dashboard for the runner seat
    "research_note": "toolbox_only",     # IR-6 category-specialized knowledge_learn wrapper
    "execute": "toolbox_only",           # the dispatch door itself (runner plumbing)
    "release_written_locks": "toolbox_only",  # runner lifecycle: locks released at reply (T048)
}

# T067-1: shared-verb coverage on the THIRD door. The ToolBox spells some shared verbs its
# own way; an alias declares "this ToolBox method IS that shared verb for this seat".
TOOLBOX_ALIASES = {
    "recall": "knowledge_recall",
    "learn": "knowledge_learn",
    "note": "knowledge_note",
    "boot": "knowledge_boot",
    "bifrost_sync": "bifrost_inbox",   # same read (peek unread); consume stays runner-owned
    "handoff": "bifrost_send",         # ToolBox hands off via bifrost_send(kind='handoff')
}

# Shared verbs deliberately NOT ToolBox tools (design non-goal (g): the ToolBox is
# agentic-tool primitives, not a CLI mirror). Every entry needs a rationale -- a NEW
# shared verb missing from ToolBox+aliases+here FAILS (the knowledge_map class).
TOOLBOX_EXEMPT = {
    "recall_feedback": "funnel voting is the operator/wrap loop, not an in-task tool",
    "stats": "operator telemetry; the boot one-liner covers the agent's need",
    "status": "operator/coordination view; boot + ledger folds cover it",
    "story": "chronicle door; agents reach narrative via boot/notes",
    "events": "forensic drill-down; agent-facing reads ride recall/knowledge_full",
    "log": "operator log surface",
    "promoted": "salient-tier listing; the boot DECISIONS section covers it",
    "graduate": "curation verb; operator/claude loop",
    "injections": "hook-side diagnostic; runner recall rides recall_at",
    "notes": "project notes ride the boot fold; knowledge_note is the write side",
    "lock": "advisory locks are taken by the guarded-write path itself (_prewrite)",
    "unlock": "released by the runner at reply time (release_written_locks)",
    "locks": "lock listing is operator/diagnostic",
    "tag_anti_pattern": "curation verb; operator/claude loop",
    "packet_trace": "operator/MCP route explanation; transport continues to use packet_spec directly",
    "packet_stats": "operator/MCP shadow-delivery telemetry; not an in-task mutation tool",
    "task": "governed conductor surface; runner seats receive approved work over Bifrost",
}


def check():
    cli, mcp, tb = set(cli_verbs()), set(mcp_tools()), set(toolbox_verbs())
    fails, gaps = [], []
    mcp_alias_targets = set(CLI_MCP_ALIASES.values())
    # 1. every real verb on an ENFORCED door must be classified (the ratchet: no new drift)
    for v in sorted((cli | mcp | tb)):
        if v not in MANIFEST and v not in mcp_alias_targets:
            door = "CLI" if v in cli else ("MCP" if v in mcp else "ToolBox")
            fails.append(f"unclassified verb '{v}' (on {door}) -> add it to MANIFEST in check_door_parity.py "
                         f"(shared / cli_only / mcp_only / toolbox_only / gap)")
    # 1b. the alias/exempt maps must stay honest over time
    for cli_name, mcp_name in sorted(CLI_MCP_ALIASES.items()):
        if MANIFEST.get(cli_name) != "shared":
            fails.append(f"CLI_MCP_ALIASES maps '{cli_name}' but it is not a shared verb -> prune the alias")
        if cli_name not in cli:
            fails.append(f"CLI_MCP_ALIASES points at CLI '{cli_name}' which is missing -> the alias covers nothing")
        if mcp_name not in mcp:
            fails.append(f"CLI_MCP_ALIASES points '{cli_name}' at MCP '{mcp_name}' which is missing -> the alias covers nothing")
        if mcp_name in MANIFEST:
            fails.append(f"MCP alias target '{mcp_name}' is also in MANIFEST -> classify the capability once via '{cli_name}'")
    for shared_v, tb_name in sorted(TOOLBOX_ALIASES.items()):
        if MANIFEST.get(shared_v) != "shared":
            fails.append(f"TOOLBOX_ALIASES maps '{shared_v}' but it is not a shared verb -> prune the alias")
        if tb_name not in tb:
            fails.append(f"TOOLBOX_ALIASES points '{shared_v}' at '{tb_name}' which is NOT on the ToolBox "
                         f"-> the alias covers nothing")
    for shared_v in sorted(TOOLBOX_EXEMPT):
        if MANIFEST.get(shared_v) != "shared":
            fails.append(f"TOOLBOX_EXEMPT lists '{shared_v}' but it is not a shared verb -> prune the exemption")
    # 2. manifest expectations vs reality
    for v, cat in sorted(MANIFEST.items()):
        mcp_name = CLI_MCP_ALIASES.get(v, v)
        on_cli, on_mcp, on_tb = v in cli, mcp_name in mcp, v in tb
        if cat == "shared":
            if not (on_cli and on_mcp):
                missing = "MCP" if on_cli else "CLI"
                fails.append(f"'{v}' is declared shared but is MISSING from {missing} (regression)")
            # T067-1: third-door coverage -- by name, by declared alias, or explicitly exempted.
            if not (on_tb or TOOLBOX_ALIASES.get(v) in tb or v in TOOLBOX_EXEMPT):
                fails.append(f"'{v}' is declared shared but is MISSING from ToolBox (third-door regression) "
                             f"-> wire it, alias it, or exempt it with a rationale")
        elif cat == "cli_only" and on_mcp:
            fails.append(f"'{v}' is declared cli_only but appears on MCP -> reclassify")
        elif cat == "mcp_only" and on_cli:
            fails.append(f"'{v}' is declared mcp_only but appears on CLI -> reclassify")
        elif cat == "toolbox_only" and (on_cli or on_mcp):
            fails.append(f"'{v}' is declared toolbox_only but appears on {'CLI' if on_cli else 'MCP'} "
                         f"-> reclassify")
        elif cat == "gap":
            gaps.append(v)
        # a verb in the manifest that no longer exists on any door -> stale manifest entry
        if cat in ("shared", "cli_only", "gap", "toolbox_only") and not (on_cli or on_mcp or on_tb):
            fails.append(f"'{v}' is in the MANIFEST but exists on NO door -> remove the stale entry")
    return fails, gaps, cli, mcp


def main():
    fails, gaps, cli, mcp = check()
    bus = bus_methods()
    tb = set(toolbox_verbs())
    report = "--report" in sys.argv
    if report:
        print(f"CLI ({len(cli)}): {', '.join(sorted(cli))}\n")
        print(f"MCP ({len(mcp)}): {', '.join(sorted(mcp))}\n")
        print(f"ToolBox ({len(tb)}, the runner's third door -- enforced since T067-1): "
              f"{', '.join(sorted(tb))}\n")
        print(f"BUS ({len(bus)}, separate programmatic door -- not parity-enforced): {', '.join(bus)}\n")
        tb_only = sorted(v for v, c in MANIFEST.items() if c == "toolbox_only")
        self_service = sorted(v for v, c in MANIFEST.items()
                              if c in ("cli_only", "mcp_only") and v in tb)
        covered = sorted(v for v, c in MANIFEST.items()
                         if c == "shared" and (v in tb or TOOLBOX_ALIASES.get(v) in tb))
        shared_live = sum(1 for v, c in MANIFEST.items()
                          if c == "shared" and v in cli and CLI_MCP_ALIASES.get(v, v) in mcp)
        alias_cli, alias_mcp = set(CLI_MCP_ALIASES), set(CLI_MCP_ALIASES.values())
        print(f"shared: {shared_live}  |  cli-only: {len(cli - mcp - alias_cli)}  |  "
              f"mcp-only: {len(mcp - cli - alias_mcp)}")
        print(f"toolbox: {len(tb)} verbs | toolbox_only: {len(tb_only)} | shared covered on ToolBox "
              f"(name or alias): {len(covered)} | shared exempt: {len(TOOLBOX_EXEMPT)}")
        if self_service:
            print(f"note: cli/mcp-only verbs also on the ToolBox (agent self-service, by design): "
                  f"{', '.join(self_service)}")
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
