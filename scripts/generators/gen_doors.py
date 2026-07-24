"""gen_doors -- regenerate docs/DOORS.md: the agent-door I/O reference, derived (master-map M2, v0).

Daniel's ask 2026-07-19 (verbatim slice): "every system where and what its inputs and outputs
are." The CLI is the fleet's biggest door and its argparse tree ALREADY declares every verb and
argument -- so the reference derives from build_parser() itself, never hand-listed, never rots.
v0 covers the CLI door (agent_cli.py). The MCP door (ai_setup_mcp.py) and the runner ToolBox
door are named as KNOWN-GAP sections for the fence (deepseek's map-counter question #3: are the
ToolBox schemas introspectable as built) rather than half-derived here.

Run:  py scripts/generators/gen_doors.py            # writes docs/DOORS.md
      py scripts/generators/gen_doors.py --check    # exit 1 if stale vs code (CI/pre-ship)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth
OUT = os.path.join(ROOT, "docs", "DOORS.md")
sys.path.insert(0, ROOT)


def cli_verbs():
    """Introspect agent_cli's parser: {verb: {help, args:[(flag, required, choices, help)]}}.
    Uses argparse's public-ish action tree (stable across 3.x); alias names collapse by parser
    identity so a verb with aliases lists once."""
    import agent_cli
    p = agent_cli.build_parser()
    subaction = next((a for a in p._actions if isinstance(a, argparse._SubParsersAction)), None)
    if subaction is None:
        return {}
    # canonical name + help come from the _ChoicesPseudoAction list (one per verb, not per alias)
    helps = {ca.dest: (ca.help or "") for ca in getattr(subaction, "_choices_actions", [])}
    verbs = {}
    seen = set()
    for name, sub in subaction.choices.items():
        if id(sub) in seen or name not in helps and any(id(s) == id(sub) for n, s in subaction.choices.items() if n in helps):
            # skip aliases: keep the name that carries a help entry
            if name not in helps:
                continue
        seen.add(id(sub))
        args = []
        for a in sub._actions:
            if isinstance(a, argparse._HelpAction):
                continue
            flag = "/".join(a.option_strings) if a.option_strings else f"<{a.dest}>"
            choices = ",".join(map(str, a.choices)) if a.choices else ""
            args.append((flag, bool(a.required), choices, (a.help or "").strip()))
        verbs[name] = {"help": helps.get(name, ""), "args": args}
    return dict(sorted(verbs.items()))


def render(verbs):
    lines = [
        "# DOORS -- agent-door I/O reference (auto-generated, v0)",
        "",
        "Status: current",
        "Class: reference",
        "",
        "> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_doors.py`.",
        "> What goes IN each door and what it is FOR, derived from the door's own declaration",
        "> (argparse). Companion to MAP.md (modules), PHYSICS.md (bounds/flags). Guarded by",
        "> check_comprehensibility so it cannot silently rot.",
        "",
        f"## CLI door -- `py agent_cli.py <verb>` ({len(verbs)} verbs)",
        "",
        "The agent's shell door. `*` marks a required argument; `{a,b}` shows the accepted values.",
        "",
        "| Verb | What it does | Inputs |",
        "|---|---|---|",
    ]
    for name, v in verbs.items():
        inputs = []
        for flag, required, choices, _help in v["args"]:
            tok = flag + ("*" if required else "")
            if choices:
                tok += " {" + choices + "}"
            inputs.append(f"`{tok}`")
        lines.append(f"| `{name}` | {v['help'].replace('|', '/')} | {' '.join(inputs)} |")
    lines += [
        "",
        "## MCP door -- the native tool surface (KNOWN GAP, v0)",
        "",
        "`ai_setup_mcp.py` exposes the same verbs as MCP tools (bifrost_sync/send, handoff,",
        "note, learn, task, ...). v0 does not yet derive their schemas here; the master-map",
        "charter M2 fence (deepseek's question #3) settles whether the MCP + runner-ToolBox",
        "schemas introspect cleanly enough to project the same way this CLI table does.",
        "",
        "## Runner ToolBox door (KNOWN GAP, v0)",
        "",
        "`core/comm/toolbox.py` is the deepseek/sol/kimi runner tool surface (read_file,",
        "write_file, run_command, bifrost_send, ...). Its `_fn`-registered schemas are the",
        "third door check_door_parity does not yet see (T067-1) -- projecting it is M2's",
        "second slice.",
        "",
    ]
    return "\n".join(lines)


def main():
    try:
        verbs = cli_verbs()
    except Exception as e:
        print(f"gen_doors: could not introspect the CLI parser ({type(e).__name__}: {e})")
        return 2
    text = render(verbs)
    if "--check" in sys.argv:
        try:
            if open(OUT, encoding="utf-8").read() == text:
                print("DOORS.md current"); return 0
        except OSError:
            pass
        print("DOORS.md STALE vs code -- regenerate (py scripts/generators/gen_doors.py)"); return 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote docs/DOORS.md: {len(verbs)} CLI verbs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
