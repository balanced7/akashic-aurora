"""check_wiring -- the Built != Wired gate (membrane slice 2).

A capability that exists + passes tests but is not reachable on any PRODUCTION call path runs nowhere;
latent capability accumulates silently and is a maintainability tax (PRINCIPLES #4, applied to dead
weight). This flags every `core/` module NOT reachable, via the import graph, from a production entry
point (the doors, runners, hooks, boot). Ratchets like the other guards: freeze today's known-standalone
modules in EXCEPTIONS, FAIL on a NEW unwired module.

Limitation: static imports only (incl. lazy imports inside functions). A module reached solely via a
computed importlib name won't be seen; add it to EXCEPTIONS with a note if so.

Run:  py scripts/check_wiring.py            # gate (exit 1 on a NEW unwired core/ module)
      py scripts/check_wiring.py --report   # print reachable vs unwired
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The production call paths -- what actually RUNS in production.
ENTRY_POINTS = [
    "agent_cli.py", "ai_setup_mcp.py", "bootstrap.py", "config.py",
    "scripts/bifrost_runner_deepseek.py", "scripts/bifrost_runner.py",
    "scripts/bifrost_ui.py", "scripts/bifrost_wake.py", "scripts/deepseek_chat.py",
]
_HOOKS = os.path.join(ROOT, "scripts", "hooks")
if os.path.isdir(_HOOKS):
    ENTRY_POINTS += [f"scripts/hooks/{h}" for h in sorted(os.listdir(_HOOKS)) if h.endswith(".py")]

# core/ modules NOT on a runtime path today (frozen 2026-07-07). This is a BACKLOG, not an amnesty: each
# is either "built-ahead" (wire when its consumer lands) or "legacy" (delete). A NEW unwired module fails
# the gate; it must be wired, deleted, or added here with a reason.
EXCEPTIONS = {
    # built-ahead -- capability built before its production consumer; wire it when that lands
    "core/codex/lifecycle.py": "built-ahead: codex knowledge layer (Wave-2)",
    "core/codex/schema.py": "built-ahead: codex knowledge layer (Wave-2)",
    "core/comm/dispatcher.py": "built-ahead: bus doorbell->wake; not wired into the runners yet",
    "core/comm/interject.py": "built-ahead: human-interjection router; not wired yet",
    "core/coord/conductor.py": "built-ahead: orchestration shell (Slice D) -- wire in the membrane's coordination work",
    "core/coord/experiment.py": "built-ahead: Stage-3 coordination evidence engine",
    "core/coord/metrics.py": "built-ahead: coordination metrics watchdog",
    "core/foundation/fast_cache.py": "built-ahead: L1/L2 cache; consumer not wired",
    "core/learning/consolidation.py": "built-ahead: memory->chronicle consolidation",
    "core/narrative/drift.py": "built-ahead: narrative drift detector (prototype)",
    "core/narrative/tag_audit.py": "built-ahead: tag mis-tag detector",
    "core/narrative/tag_governance.py": "built-ahead: governed re-tag write path",
    "core/perspectives/reinforce.py": "built-ahead: perspectives ReinforcedGraph",
    "core/perspectives/schema.py": "built-ahead: perspectives Map/Lens schema",
    # legacy / deprecated -- superseded; deletion candidates (a later boy-scout slice)
    "core/signals/coordinator_service.py": "legacy: pre-Bifrost coordinator; superseded",
    "core/state/redis_sync_coordinator.py": "legacy: deprecated facade (see ARCHITECTURE.md)",
    "core/state/sync_reconciler.py": "legacy: state reconciler; superseded by Store CAS",
    "core/state/session_recovery.py": "legacy: pre-Bifrost session recovery",
}


def _dotted(rel):
    d = rel[:-3].replace("/", ".").replace("\\", ".")
    return d[:-9] if d.endswith(".__init__") else d


def module_map():
    """dotted-name -> relpath for core/ + agent/ (dotted) and scripts/ (also by bare basename, since
    scripts add themselves to sys.path and import each other bare)."""
    m = {}
    for pkg in ("core", "agent"):
        for dp, _dn, fn in os.walk(os.path.join(ROOT, pkg)):
            if "__pycache__" in dp:
                continue
            for f in fn:
                if f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                    m[_dotted(rel)] = rel
    for f in os.listdir(os.path.join(ROOT, "scripts")):
        if f.endswith(".py"):
            m[f"scripts.{f[:-3]}"] = f"scripts/{f}"
            m.setdefault(f[:-3], f"scripts/{f}")  # bare import name
    return m


def imports_of(rel, modmap):
    out = set()
    try:
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
    except Exception:
        return out
    for node in ast.walk(tree):
        cands = []
        if isinstance(node, ast.Import):
            cands = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and (node.level or 0) == 0:
            cands = [f"{node.module}.{a.name}" for a in node.names] + [node.module]
        for c in cands:
            if c in modmap:
                out.add(modmap[c])
    return out


def analyze():
    modmap = module_map()
    # __init__.py are package markers (implicitly loaded on submodule import); the static graph can't
    # see that, so exclude them -- they are not capability modules.
    core_universe = {rel for rel in modmap.values()
                     if rel.startswith("core/") and not rel.endswith("__init__.py")}
    # BFS from the entry points over the import graph
    reachable, frontier = set(), list(ENTRY_POINTS)
    seen = set(ENTRY_POINTS)
    while frontier:
        f = frontier.pop()
        for dep in imports_of(f, modmap):
            if dep not in seen:
                seen.add(dep); frontier.append(dep)
            reachable.add(dep)
    unwired = sorted(core_universe - reachable)
    return core_universe, reachable, unwired


def main():
    core_universe, reachable, unwired = analyze()
    report = "--report" in sys.argv
    if report:
        print(f"core/ modules: {len(core_universe)}  |  reachable from production: "
              f"{len(core_universe & reachable)}  |  unwired: {len(unwired)}\n")
        print("UNWIRED (built, not on a production call path):")
        for u in unwired:
            print(f"  {u}{'   [exception]' if u in EXCEPTIONS else ''}")
    new_unwired = [u for u in unwired if u not in EXCEPTIONS]
    stale = sorted(e for e in EXCEPTIONS if e not in unwired)  # exception now wired or gone
    for s in stale:
        print(f"WARN: '{s}' is in EXCEPTIONS but is now wired (or gone) -> remove the stale entry")
    for u in new_unwired:
        print(f"FAIL: '{u}' exists but is NOT reachable from any production entry point "
              f"(built != wired) -> wire it, delete it, or add to EXCEPTIONS with a reason")
    if new_unwired:
        print(f"\n{len(new_unwired)} NEW unwired core/ module(s). Latent capability must not accumulate.")
        return 1
    print(f"\nPASS: every core/ module is wired to a production path "
          f"({len(EXCEPTIONS)} known-standalone exception(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
