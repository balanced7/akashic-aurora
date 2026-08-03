"""check_advertised_tools -- the tool-surface twin of check_advertised_verbs (T142).

check_advertised_verbs enforces the SHELL half of the door contract: every `py agent_cli.py <verb>`
named in live code must resolve. This enforces the TOOL half: every tool a doc tells an agent to
CALL must exist on one of the two tool surfaces -- the DeepSeek ToolBox (core/comm/toolbox.py) or
the MCP server (ai_setup_mcp.py). A name that resolves at either door is advertised truthfully.

WHY IT EXISTS. A read-only seat walked AGENTS.md on 2026-08-03 and could not complete step one. The
contract's first instruction is `py agent_cli.py boot <id>`; `run_command` is gated by allow_exec
plus the ACL families door, and security/acl.json quarantines unlisted agents to read-only BY
DEFAULT -- so the default new agent has no shell. The tool it needed (knowledge_boot) had existed
for months, and AGENTS.md never mentioned the tool surface at all. check_wiring hunts capability
with no door; this hunts a door with no capability behind it.

NAMESPACE-SCOPED BY DESIGN. Only a prefix carrying TWO OR MORE real tools counts as a tool
namespace. `read_`, `write_`, `list_`, `run_` each have exactly one tool and are ordinary
vocabulary in this repo -- write_tombstone, read_verdict, list_parked and list_snapshots are core
functions, not tools. Flagging those would be the false-positive flood that gets a guard fed
exceptions until it guards nothing, which is the lesson check_wiring's own comments record twice.

Run:  py scripts/checkers/check_advertised_tools.py           # gate over the contract docs
      py scripts/checkers/check_advertised_tools.py --report  # also print the tool namespaces
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLBOX = os.path.join(ROOT, "core", "comm", "toolbox.py")

# The docs that make PROMISES to a newcomer. Deliberately short: these are the contract surfaces,
# not every markdown file in the tree. A design doc musing about a tool it wishes existed is not a
# broken promise; AGENTS.md telling you to call one is.
CONTRACT_DOCS = ("AGENTS.md", "README.md", "docs/DOORS.md")

_TOOL_DEF = re.compile(r'_fn\("([a-z0-9_]+)"')
_MCP_DEF = re.compile(r"^\s*async def ([a-z][a-z0-9_]*)\(", re.M)

# A token IMMEDIATELY FOLLOWED BY "(" -- i.e. written as a CALL. Both live false-positive classes
# from the first run die here. `--kind bifrost_msg` is an argument VALUE, never a call, and a doc
# discussing a kind is not advertising a tool. Not preceded by / or . so paths and attribute
# access stay out.
_TOKEN = re.compile(r"(?<![\w/.\-])([a-z][a-z0-9]*_[a-z0-9_]+)(?=\()")


def real_tools(path=TOOLBOX, mcp=None):
    """The union of BOTH tool surfaces -- the DeepSeek ToolBox and the MCP server.

    The first live run reported AGENTS.md:113 for advertising `bifrost_sync(agent)`. That line is
    CORRECT: bifrost_sync is a real MCP tool (ai_setup_mcp.py), and the line even labels it
    "# MCP: bifrost_sync(agent)". Reading only core/comm/toolbox.py made an honest doc look like a
    liar -- the expensive direction, and the exact failure this repo's sibling gate records twice.
    There are two tool doors; a name that resolves at either one is advertised truthfully.
    """
    names = set()
    try:
        names |= set(_TOOL_DEF.findall(open(path, encoding="utf-8", errors="replace").read()))
    except OSError:
        pass
    mcp = mcp if mcp is not None else os.path.join(ROOT, "ai_setup_mcp.py")
    try:
        names |= set(_MCP_DEF.findall(open(mcp, encoding="utf-8", errors="replace").read()))
    except OSError:
        pass
    return names                          # fail open: no tool list, nothing to enforce


def namespaces(tools):
    """prefix -> count, keeping only prefixes with >= 2 tools (a real namespace)."""
    counts = {}
    for t in tools:
        if "_" in t:
            counts[t.split("_")[0]] = counts.get(t.split("_")[0], 0) + 1
    return {p for p, n in counts.items() if n >= 2}


_FILE_STEMS = None


def _file_stems():
    """Every filename stem in the tree. `bifrost_runner_deepseek` is a FILE, not a missing tool."""
    global _FILE_STEMS
    if _FILE_STEMS is None:
        _FILE_STEMS = set()
        for dp, dn, fn in os.walk(ROOT):
            dn[:] = [d for d in dn
                     if d not in ("__pycache__", ".git", "node_modules", "ComfyUI-Zluda")]
            for f in fn:
                _FILE_STEMS.add(os.path.splitext(f)[0])
    return _FILE_STEMS


def scan(docs, toolbox=TOOLBOX, mcp=None):
    """[(doc, token, lineno)] -- tokens in a tool NAMESPACE that are not real tools."""
    tools = real_tools(toolbox, mcp=mcp)
    ns = namespaces(tools)
    if not ns:
        return []
    out = []
    for d in docs:
        try:
            text = open(d, encoding="utf-8", errors="replace").read()
        except OSError:
            continue                      # fail open: an unreadable doc promises nothing
        for i, line in enumerate(text.splitlines(), 1):
            for tok in _TOKEN.findall(line):
                if tok in tools or tok.split("_")[0] not in ns:
                    continue
                if tok in _file_stems():          # it is a file, not a tool call
                    continue
                out.append((d, tok, i))
    return out


def main():
    tools = real_tools()
    ns = sorted(namespaces(tools))
    docs = [os.path.join(ROOT, d) for d in CONTRACT_DOCS]
    docs = [d for d in docs if os.path.exists(d)]
    bad = scan(docs)
    if "--report" in sys.argv:
        print(f"tools: {len(tools)}  |  namespaces (>=2 tools): {', '.join(ns)}")
        print(f"contract docs scanned: {[os.path.relpath(d, ROOT) for d in docs]}\n")
    for d, tok, ln in bad:
        rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
        print(f"FAIL: {rel}:{ln} advertises tool '{tok}', which is not in the TOOLS list "
              f"-> fix the name, or add the tool, or stop promising it")
    if bad:
        print(f"\n{len(bad)} advertised tool(s) do not exist. A door that names a capability "
              f"nobody can call strands the agent that believes it.")
        return 1
    print(f"PASS: every tool named in {len(docs)} contract doc(s) exists "
          f"({len(tools)} tools, {len(ns)} namespace(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
