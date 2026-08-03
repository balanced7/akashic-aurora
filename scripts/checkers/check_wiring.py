"""check_wiring -- the Built != Wired gate (membrane slice 2).

A capability that exists + passes tests but is not reachable on any PRODUCTION call path runs nowhere;
latent capability accumulates silently and is a maintainability tax (PRINCIPLES #4, applied to dead
weight). This flags every `core/` module NOT reachable, via the import graph, from a production entry
point (the doors, runners, hooks, boot). Ratchets like the other guards: freeze today's known-standalone
modules in EXCEPTIONS, FAIL on a NEW unwired module.

Limitation: static imports only (incl. lazy imports inside functions). A module reached solely via a
computed importlib name won't be seen; add it to EXCEPTIONS with a note if so.

Run:  py scripts/checkers/check_wiring.py            # gate (exit 1 on a NEW unwired core/ module)
      py scripts/checkers/check_wiring.py --report   # print reachable vs unwired
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth

# The production call paths -- what actually RUNS in production.
ENTRY_POINTS = [
    "agent_cli.py", "ai_setup_mcp.py", "bootstrap.py", "config.py",
    "scripts/bifrost_runner.py",
    "scripts/bifrost_ui.py", "scripts/bifrost_wake.py", "scripts/deepseek_chat.py",
]

# EVERY seat runner, enumerated rather than listed by hand (2026-08-01). The hand-written list
# named only bifrost_runner_deepseek and drifted the moment new seats landed: gemini, kimi and
# sol runners -- ~900 tracked lines each, with __main__ entries -- were invisible to this walk.
# The consequence is a FALSE built-not-wired report for anything reachable only through them,
# and core/comm/control_channel.py was exactly that: imported by the gemini AND kimi runners,
# reported unwired for a week. A false positive here is expensive twice over -- it pressures a
# live module onto the EXCEPTIONS backlog (which the comment below calls a backlog, not an
# amnesty), and it teaches readers that this gate cries wolf.
# Same enumerate-don't-list discipline the hook dirs below already use.
_rd = os.path.join(ROOT, "scripts")
if os.path.isdir(_rd):
    ENTRY_POINTS += [f"scripts/{r}" for r in sorted(os.listdir(_rd))
                     if r.startswith("bifrost_runner_") and r.endswith(".py")]
# T104-M2 (2026-07-24): hooks split by owner-facet -- harness adapters live in
# agent/harness/hooks/, commit guards in scripts/githooks/. Enumerate BOTH live
# dirs; the transitional scripts/hooks/ session-continuity copies are NOT entry
# points (deleted at next session start) and are deliberately not walked.
for _hd, _prefix in ((os.path.join(ROOT, "agent", "harness", "hooks"), "agent/harness/hooks"),
                     (os.path.join(ROOT, "scripts", "githooks"), "scripts/githooks")):
    if os.path.isdir(_hd):
        ENTRY_POINTS += [f"{_prefix}/{h}" for h in sorted(os.listdir(_hd)) if h.endswith(".py")]

# core/ modules NOT on a runtime path today (frozen 2026-07-07). This is a BACKLOG, not an amnesty: each
# is either "built-ahead" (wire when its consumer lands) or "legacy" (delete). A NEW unwired module fails
# the gate; it must be wired, deleted, or added here with a reason.
EXCEPTIONS = {
    # built-ahead -- capability built before its production consumer; wire it when that lands
    # P2 investigate-before-delete verdicts (arch-triage 2026-07-07): DeepSeek's blind triage said
    # DELETE codex/*+fast_cache+session_recovery; code investigation KEEPS codex (paused tested
    # roadmap), CONSOLIDATES session_recovery (dup-class, not dead), and confirms only fast_cache dead.
    "core/codex/lifecycle.py": "KEEP built-ahead: Codex Wave-2 (docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_302fc9.md) C2 DONE, C3+ paused; "
        "TESTED by tests/test_codex_resource.py -- NOT superseded, do not delete (verified P2 2026-07-07)",
    "core/codex/schema.py": "KEEP built-ahead: Codex Wave-2 (docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_302fc9.md) C2 DONE, C3+ paused; "
        "TESTED by tests/test_codex_resource.py -- NOT superseded, do not delete (verified P2 2026-07-07)",
    "core/comm/dispatcher.py": "built-ahead: mesh doorbell->wake. BLOCKED on the W3 wake-adapter "
        "'invoker' registry (does not exist yet; Dispatcher.run() has no production caller) AND an "
        "architecture choice vs the live bifrost_wake mechanism -- wire when W3 lands (arch-triage 2026-07-07)",
    "core/comm/interject.py": "built-ahead: human-interjection router; not wired yet",
    # Added 2026-07-25 while clearing a CI that had been RED for over a day -- the boundary
    # guard failed FIRST and skipped every gate behind it, including the whole test suite,
    # so these two never surfaced. Both are kimi-lane builds from arcs still in flight, not
    # dead code. Dated and owned so they are TRACKED debt, not normalised debt: each names
    # what would clear it. If the owning slice lands, delete the entry -- do not renew it.
    # core/comm/runner_lib.py -- ENTRY REMOVED 2026-08-03 (T134). Its own UNWIRE-WHEN was "a
    # runner imports the factory instead of constructing its own client", and that is now the
    # case: scripts/kimi_chat.py:41 `from core.comm.runner_lib import make_openai_compat_client`,
    # reached from scripts/bifrost_runner_kimi.py:52. The entry asked to be deleted rather than
    # renewed when its slice landed; this is that deletion.
    "core/toolbelt/contest.py": "built-ahead (1cc5a39): the chorus door, kimi's build, "
        "claude-run green. UNWIRE-WHEN: a production caller invokes contest -- today only "
        "its pins exercise it. Owner: kimi lane / T099 self-tooling.",
    "core/coord/experiment.py": "built-ahead: Stage-3 coordination evidence engine",
    "core/coord/metrics.py": "built-ahead: coordination metrics watchdog",
    "core/learning/consolidation.py": "built-ahead: memory->chronicle consolidation",
    "core/narrative/drift.py": "built-ahead: narrative drift detector (prototype)",
    "core/narrative/tag_audit.py": "built-ahead: tag mis-tag detector",
    "core/narrative/tag_governance.py": "built-ahead: governed re-tag write path",
    "core/perspectives/reinforce.py": "built-ahead: perspectives ReinforcedGraph",
    "core/perspectives/schema.py": "built-ahead: perspectives Map/Lens schema",
    # Added 2026-08-01 (opus-engineer) while draining this backlog at Daniil's ask, after the
    # write-edge hook made check_wiring run at COMMIT time rather than only in a CI nobody read.
    # The sweep started at 7 and only these 3 were real: core/comm/control_channel.py was a
    # FALSE POSITIVE (imported by the gemini AND kimi runners, which were missing from
    # ENTRY_POINTS), and durable_reconcile / migrate_to_sqlite / pack_replay are SELF-INVOKING
    # tools with their own __main__ -- both classes are now recognised structurally above, so
    # neither can recur. These three are library modules with no consumer yet: genuinely
    # built-ahead, each naming what clears it.
    "core/comm/role_queue.py": "built-ahead (451d2a9, T108 S1): the role work queue. Design "
        "settled by the T108 fence and gated by Daniil 2026-07-28. VERIFIED NEVER RUN "
        "2026-08-01 -- bifrost:role:*, *rolefence*, *rolegen* all hold ZERO keys and no "
        "production module imports it; the reaper still routes around it (reaper.py:228 strips "
        "to_incarnation, :239 re-sends onto the shared inbox). UNWIRE-WHEN: the T108 migration "
        "routes directed/role mail through it. Owner: T108.",
    "core/recall/gate_rules.py": "built-ahead (eae78d4, R2 slice 1a): the silence-gate rules, "
        "written deliberately BEFORE the gate that consumes them -- its own docstring says so, "
        "because a rule stated by pointing at the census sample would be a fit rather than a "
        "principle. UNWIRE-WHEN: the silence gate lands and imports them. Owner: recall-heuristics.",
    "core/recall/precision_audit.py": "built-ahead (25dbcd5): the retrieval-accuracy instrument "
        "kimi named as the hole every 2026-07-27 architecture position argued around without a "
        "single accuracy number. Exercised by 3 test files, no production caller yet. "
        "UNWIRE-WHEN: a door or scheduled audit invokes it -- an instrument nobody runs measures "
        "nothing. Owner: recall lane.",
    # unwired diagnostic -- kept, not on a runtime path (name-collision cleanup pending)
    "core/state/session_recovery.py": "unwired but KEPT (P2 2026-07-07): session-HISTORY recovery from "
        "local files, distinct from session_checkpoint's crash-resume. Class-name collision RESOLVED "
        "(checkpoint's helper renamed CheckpointRecovery). Still unwired (exported by __init__, no live "
        "consumer) -- wire when a session-history consumer lands, or retire then. "
        "RE-CONFIRMED UNWIRED 2026-08-03 (T134b): this entry read STALE for two days because "
        "self_invoking_modules absolved it on a two-line `recovery = main()` stub. Traced -- no "
        "importer, no shell caller. The gate was wrong, not the entry; see tests/"
        "test_t134_self_invoking_is_not_a_library.py.",
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


SHELL_DIRS = ("scripts/githooks", ".github/workflows")

# A real guard block, not the bare string: a module that merely MENTIONS __main__ in prose or
# in a docstring has not declared itself runnable, and this rule must not be evadable by a
# comment. (The sibling no-syspath-insert rule is evadable by aliasing the import -- a gap found
# 2026-08-01 while testing this file's neighbour; flagged, not fixed here.)
_SELF_ENTRY = re.compile(r"^if\s+__name__\s*==\s*[\"']__main__[\"']\s*:", re.M)


def _is_reexported(rel, root=ROOT) -> bool:
    """True if rel's OWN package __init__.py imports it by name -- i.e. it is an API surface.

    A package that re-exports a module is publishing it for callers to import THROUGH the
    package; if it were live, the import graph would already show it. That makes re-export the
    discriminator between a tool and a library (T134b).
    """
    init = os.path.join(root, os.path.dirname(rel), "__init__.py")
    mod = os.path.basename(rel)[:-3]
    try:
        with open(init, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError):
        return False                      # fail open: an unreadable __init__ re-exports nothing
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.rsplit(".", 1)[-1] == mod:   # from .mod import X
                return True
            if any(a.name == mod for a in node.names):                  # from . import mod
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.rsplit(".", 1)[-1] == mod for a in node.names):
                return True
    return False


def self_invoking_modules(universe, root=ROOT) -> set:
    """core/ modules that ARE entry points: run directly by a human, never imported.

    Migrations, audits and replay harnesses have no caller to find -- that is what they are.
    They declare their own runnability instead, and this reads that declaration. Without it
    the entire class is permanently reported unwired, which is worse than noise: the gate's
    only offered remedy is EXCEPTIONS, so each false positive pushes a live tool onto a list
    the file itself calls "a BACKLOG, not an amnesty".

    A LIBRARY IS NOT A TOOL (T134b, 2026-08-03). Reading the `__main__` guard alone also absolved
    any library carrying a demo stub. Measured: core/state/session_recovery.py has no importer and
    no shell caller, its whole guard body is `recovery = main()`, its docstring's usage is `from
    core.state.session_recovery import SessionRecovery`, and core/state/__init__.py re-exports it.
    Nothing about the module changed -- this rule landed and silently reclassified it as wired,
    and the resulting stale-EXCEPTIONS warning invited deleting a still-accurate entry.

    That failure runs the opposite way to the one above and is worse for it: a false positive is
    LOUD and gets argued with, while a gate that quietly stops asking just gets believed. So
    re-exported modules keep their unwired verdict; the three modules this rule was written for
    (durable_reconcile, migrate_to_sqlite, pack_replay) are re-exported by nothing and are
    unaffected.
    """
    out = set()
    for rel in universe:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                if not _SELF_ENTRY.search(fh.read()):
                    continue
        except OSError:
            continue
        if _is_reexported(rel, root=root):
            continue
        out.add(rel)
    return out


def shell_invoked_modules(dirs=None) -> set:
    """Modules invoked from tracked SHELL entry points -- hooks and CI.

    The import-graph BFS below cannot see `py -m core.comm.door_probe`, so it declared
    door_probe.py unwired while it was the FIRST BLOCKING STEP of the only mandatory door in
    the repo (scripts/githooks/pre-push:29). That false positive is expensive: the remedy the
    guard offers is "add to EXCEPTIONS", so each one pushes a load-bearing module onto a
    permanent exemption list, and a guard that cries wolf gets fed exceptions until it guards
    nothing.

    A shell hook and a CI workflow ARE production entry points -- arguably the strictest ones,
    since they gate the push. Fail-open by design: an unreadable directory yields nothing extra
    and the import-graph verdict stands, so this can only ever ADD evidence of wiring, never
    hide a genuinely dead module.
    """
    import re as _re
    roots = dirs if dirs is not None else [os.path.join(ROOT, d) for d in SHELL_DIRS]
    dash_m = _re.compile(r"-m\s+([A-Za-z_][A-Za-z0-9_.]*)")
    by_path = _re.compile(r"\b((?:scripts|core|agent)/[A-Za-z0-9_\-./]+\.py)\b")
    found = set()
    for root in roots:
        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    try:
                        text = open(os.path.join(dirpath, fn), encoding="utf-8",
                                    errors="replace").read()
                    except OSError:
                        continue
                    for mod in dash_m.findall(text):
                        found.add(mod.replace(".", "/") + ".py")
                    for rel in by_path.findall(text):
                        found.add(rel.replace("\\", "/"))
        except Exception:
            continue                      # fail open: never crash the guard on a bad read
    return found


# ---------------------------------------------------------------- function level (T134)
#
# The module gate above passed every day while core/comm/mailbox.py::declare_intent had zero
# production callers: mailbox.py IS imported by the CLI door, so the MODULE read wired while the
# capability inside it was dead. Git holds the diagnosis in a human's handwriting -- 95e0c55 built
# declare_intent with 8/8 pins, and b945813 wired it with the message "built was not wired -- no
# door exposed the M1 verbs". This is that sentence, automated.
#
# EVIDENCE IS DELIBERATELY WEAK, and that is the design. "Referenced" means MENTIONED BY NAME on a
# production path -- call, attribute, bare name, import alias, keyword argument, or an exact-match
# string constant (getattr and verb-table dispatch). The comments above record the same lesson
# twice (control_channel.py, door_probe.py): a false positive here is expensive twice over, because
# the only remedy this file offers is an EXCEPTIONS entry, and a guard that cries wolf gets fed
# exceptions until it guards nothing. So this reports only capability with ZERO mentions -- the
# class it can be certain about -- and stays quiet everywhere else.
#
# Limitations, stated rather than discovered later: an unused import counts as wiring (an unused
# import is a different defect, and calling it deadness would produce false positives); a name
# assembled at runtime ("declare_" + verb) is invisible; a private helper reached only through a
# dead public function is not reported, because the public function is what gets reported first.

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "wiring_function_baseline.json")


def public_defs(rel, root=ROOT):
    """[(name, lineno, end_lineno, is_method)] -- public functions and methods defined in rel.

    Top level and one level into a class. Nested defs are private by construction. `main` is a
    self-invoking entry convention, and dunders are protocol, not capability.
    """
    out = []
    try:
        tree = ast.parse(open(os.path.join(root, rel), encoding="utf-8", errors="replace").read())
    except Exception:
        return out

    def _take(node, is_method):
        if not node.name.startswith("_") and node.name != "main":
            out.append((node.name, node.lineno, getattr(node, "end_lineno", node.lineno), is_method))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _take(node, False)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _take(sub, True)
    return out


def reference_sites(rel, root=ROOT):
    """[(name, lineno)] -- every name MENTIONED in rel, over-broad on purpose (see above).

    String constants match EXACTLY, so `getattr(mod, "promote")` is wiring while a docstring that
    merely says `reason = should_restart(...)` is not. A guard evadable by writing the name in a
    comment guards nothing.
    """
    out = []
    try:
        tree = ast.parse(open(os.path.join(root, rel), encoding="utf-8", errors="replace").read())
    except Exception:
        return out
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.Name):
            out.append((node.id, ln))
        elif isinstance(node, ast.Attribute):
            out.append((node.attr, ln))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.value, ln))
        elif isinstance(node, ast.keyword) and node.arg:
            out.append((node.arg, ln))
        elif isinstance(node, ast.alias):
            out.append((node.name.rsplit(".", 1)[-1], ln))
            if node.asname:
                out.append((node.asname, ln))
    return out


def unwired_functions(candidate_mods, production_files, root=ROOT):
    """[(module, name, lineno)] -- public defs no production file ever names.

    A def at lines lo..hi in module M is WIRED if its name appears anywhere on a production path
    OTHER than inside its own body. That last clause is the whole subtlety, and the first draft got
    it wrong in the expensive direction: suppressing every reference made inside the DEFINING
    MODULE (rather than inside the function's own body) reported load_learnings_for_boot as never
    called, when core/context/aggregator.py:104 calls it from inside aggregator's own public
    function. That draft found 277 orphans; this rule finds 44. Recursion is still not wiring.

    The caller passes the candidate list, so a module already frozen on the MODULE backlog can be
    excluded there -- reporting every function inside a known-unwired module is noise, and noise is
    what turns a guard into a thing people silence.
    """
    sites = {}
    for p in production_files:
        for name, ln in reference_sites(p, root=root):
            sites.setdefault(name, []).append((p, ln))
    out = []
    for m in candidate_mods:
        for name, lo, hi, _is_method in public_defs(m, root=root):
            wired = any(mod != m or not (lo <= ln <= hi) for mod, ln in sites.get(name, ()))
            if not wired:
                out.append((m, name, lo))
    return sorted(out)


def stale_function_baseline(baseline, candidate_mods, production_files, root=ROOT):
    """Baseline entries that are now WIRED (or gone) -- the backlog must be able to shrink.

    The module gate is currently reporting two of its own stale entries, which is the property
    worth copying: an exemption list that can only grow stops being a backlog.
    """
    live = {f"{m}::{n}" for m, n, _lo in
            unwired_functions(candidate_mods, production_files, root=root)}
    return sorted(e for e in baseline if e not in live)


def load_baseline(path=BASELINE_PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            return set(json.load(fh).get("entries", []))
    except (OSError, ValueError):
        return set()          # fail open: a missing baseline freezes nothing, it does not crash


def function_level(reachable, core_universe):
    """-> (candidate_mods, production_files, orphans, stale) for the gate and the report."""
    cand = sorted(m for m in core_universe if m in reachable and m not in EXCEPTIONS)
    prod = sorted({p for p in (set(ENTRY_POINTS) | {r for r in reachable if r.endswith(".py")})
                   if os.path.exists(os.path.join(ROOT, p))})
    orphans = unwired_functions(cand, prod)
    stale = stale_function_baseline(sorted(load_baseline()), cand, prod)
    return cand, prod, orphans, stale


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
    # Shell hooks and CI are production entry points too -- the strictest ones, since they gate
    # the push. Union them in as wiring evidence so a module invoked via `py -m` is not reported
    # dead and pressured onto the permanent EXCEPTIONS list.
    reachable = reachable | shell_invoked_modules()
    # SELF-INVOKING TOOLS are entry points, not orphans (2026-08-01). shell_invoked_modules()
    # already encodes the intent one line above -- "a module invoked via `py -m` is not reported
    # dead" -- but detects invocation only from OUTSIDE, by finding a caller. A migration, an
    # audit or a replay harness is run by a HUMAN at need; there is no caller to find, and the
    # module declares its own runnability with `if __name__ == "__main__":`.
    #
    # Without this, that whole class lands on the built-not-wired backlog permanently. Measured
    # here: 3 of 6 reported orphans were self-invoking tools (durable_reconcile, migrate_to_sqlite,
    # pack_replay), and the backlog comment above calls itself "a BACKLOG, not an amnesty" --
    # so every false positive quietly converts a live tool into normalised debt.
    reachable = reachable | self_invoking_modules(core_universe)
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

    # T134: the same question one level down -- a wired module can still hold dead capability.
    _cand, _prod, orphans, fn_stale = function_level(reachable, core_universe)
    baseline = load_baseline()
    new_orphans = [(m, n, lo) for m, n, lo in orphans if f"{m}::{n}" not in baseline]
    if report or "--functions" in sys.argv:
        print(f"\npublic core/ functions unwired: {len(orphans)}  "
              f"|  frozen backlog: {len(baseline)}  |  new: {len(new_orphans)}\n")
        cur = None
        for m, n, lo in orphans:
            if m != cur:
                print(f"  {m}")
                cur = m
            print(f"      {n}  (:{lo}){'' if f'{m}::{n}' in baseline else '   [NEW]'}")
    for s in fn_stale:
        print(f"WARN: '{s}' is in the function backlog but is now wired (or gone) "
              f"-> remove the stale entry")
    for m, n, lo in new_orphans:
        print(f"FAIL: '{m}::{n}' (:{lo}) is public but NO production entry point ever calls it "
              f"(built != wired, one level down) -> wire it, delete it, or add it to "
              f"{os.path.relpath(BASELINE_PATH, ROOT).replace(os.sep, '/')} with a reason")

    if new_unwired or new_orphans:
        if new_unwired:
            print(f"\n{len(new_unwired)} NEW unwired core/ module(s). "
                  f"Latent capability must not accumulate.")
        if new_orphans:
            print(f"\n{len(new_orphans)} NEW unwired public function(s). A capability nothing "
                  f"calls runs nowhere, however green its tests are.")
        return 1
    print(f"\nPASS: every core/ module is wired to a production path "
          f"({len(EXCEPTIONS)} known-standalone exception(s)); no NEW unwired public function "
          f"({len(baseline)} on the frozen backlog).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
