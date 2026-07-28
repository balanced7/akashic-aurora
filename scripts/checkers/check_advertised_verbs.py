"""check_advertised_verbs -- every command LIVE CODE tells you to run must exist.

T113 P8 generalised from one pin to the repo. That pin caught me shipping a spill
notice that said `py agent_cli.py blob --get <ref>` when there was no `blob` verb --
a retrieval handle pointing at nothing, minutes after I had written a commit message
criticising exactly that. A pin guards one string. This guards all of them.

It found one live instance immediately: doctor.py's own remediation for ghost mail
read `py agent_cli.py retire <agent>`, and no `retire` verb has ever existed. An
operator following the doctor's advice gets an argparse error and no way to act on
a finding the doctor deliberately raised.

WHY A DEAD INSTRUCTION IS WORSE THAN NO INSTRUCTION: a finding with no remedy is
honest about being incomplete. A finding with a remedy that does not resolve looks
actionable, gets followed, and burns the reader's trust in the finding itself. It is
the same failure as a pointer to a missing artifact -- content preserved, handle
unreachable -- one layer up, in the remediation plane.

SCOPE IS DELIBERATELY LIVE CODE ONLY (core/, scripts/, agent_cli.py, ai_setup_mcp.py).
docs/library/ and research/ hold DESIGN PROPOSALS and historical reports, many of
which name verbs that were proposed and never built. That is an accurate record of
what people thought at the time; ratcheting it would push someone to rewrite history
to make a checker happy. A dangling verb in an archived proposal is a fact. A
dangling verb in a runtime error message is a defect.

PLANNED lists docstring references to doors that are designed but unbuilt. They stay
declared here rather than silently allowed, so "planned" is a claim someone made on
the record instead of a hole the checker cannot see -- the same discipline as
check_door_parity's known-gaps list.
"""
from __future__ import annotations

import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAN_ROOTS = ("core", "scripts", "agent_cli.py", "ai_setup_mcp.py")
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

# verb -> why it is named before it exists. An entry here is a promise on the record.
PLANNED = {
    "session": "core/comm/session_state.py module docstring: the snapshot/resume door "
               "is designed (T086 lineage), not yet a CLI verb",
    "grant": "core/trust/__init__.py docstring: S-3 of the security schema; grants are "
             "currently edited in security/acl.json, no CLI door yet",
}

VERB_RE = re.compile(r"agent_cli\.py\s+([a-z][a-z0-9_-]*)")


def registered_verbs() -> set:
    """The subcommands argparse actually knows -- read from the AST, so the checker
    cannot drift from the parser it is checking."""
    tree = ast.parse(io.open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read())
    return {n.args[0].value for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "add_parser" and n.args
            and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)}


def _files():
    for entry in SCAN_ROOTS:
        p = os.path.join(ROOT, entry)
        if os.path.isfile(p):
            yield p
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(".py"):
                    yield os.path.join(dirpath, fn)


def scan():
    """[(relpath, lineno, verb, line)] for every advertised verb that does not resolve."""
    verbs, out = registered_verbs(), []
    for path in _files():
        # This file necessarily QUOTES dead instructions to explain what it guards
        # against, so scanning itself would report its own examples forever. A narrow,
        # named blind spot beats a checker that cannot describe its own purpose --
        # and it is one file, stated here rather than hidden in a regex.
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue
        try:
            lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            for m in VERB_RE.finditer(line):
                verb = m.group(1)
                if verb in verbs or verb in PLANNED:
                    continue
                out.append((os.path.relpath(path, ROOT), i, verb, line.strip()[:110]))
    return out


def main() -> int:
    verbs = registered_verbs()
    stale_plans = sorted(v for v in PLANNED if v in verbs)
    bad = scan()

    print(f"# advertised-verb check -- {len(verbs)} registered verb(s)")
    if PLANNED:
        print(f"PLANNED (named in docstrings, not built, {len(PLANNED)}): "
              f"{', '.join(sorted(PLANNED))}")
        print("  ^ declared promises, not silent holes; build them or drop the reference.")
    if stale_plans:
        # The list must not outlive its reason, or it becomes the thing it guards against.
        print(f"FAIL: {', '.join(stale_plans)} now EXIST -- remove from PLANNED")
        return 1
    if bad:
        for rel, line, verb, text in bad:
            print(f"FAIL: {rel}:{line} advertises `agent_cli.py {verb}` -- no such verb")
            print(f"      {text}")
        print(f"\n{len(bad)} dead instruction(s). A remedy that does not resolve is worse "
              f"than no remedy: it looks actionable, gets followed, and costs the reader "
              f"trust in the finding that raised it.")
        return 1
    print("PASS: every command live code tells you to run exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
