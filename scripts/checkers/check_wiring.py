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
    # W156 (2026-08-14): a real CLI door -- argparse + __main__, run by a human to seed a
    # twin's memory from a higher world. Added BY NAME, which is the discipline this file
    # warns against three lines below, and deliberately so: the general fix is to enumerate
    # every scripts/*.py carrying a __main__ block, and that would change what this gate
    # MEANS (it would surface every pre-existing script-only module at once). Widening a
    # gate is a gate decision, not a midnight one. Filed for Daniil's call.
    "scripts/seed_world.py",        # W156: seeds a twin's memory from a higher world
    "scripts/world_diff.py",        # W159: the at-a-glance world comparison
    "scripts/world_savepoint.py",   # W160: a world's restore point (code + memory)
    "scripts/world_fidelity.py",    # W163: what a checkout can and cannot do
    "scripts/dawe_census.py",       # W164: verbs whose answer nobody outside can check
    "scripts/lens_ledger.py",       # W168: score fan lenses by what survived
    # 2026-08-18: the SUPERVISOR was never an entry point -- the process that runs 24/7,
    # spawns runners and owns wake was invisible to this walk, so core/comm/discord_feed.py
    # (called from the daemon's own loop) reported built-not-wired while being precisely
    # wired. Same class as the 2026-08-01 runner-enumeration incident recorded above.
    "scripts/bifrost_daemon.py",
    # 2026-08-24: the DSH bridge (agent/harness/dsh_plugin/bridge.py) is the cordis
    # plugin's production caller, DEPLOYED OUT-OF-TREE to $DSH_HOME -- no in-tree walk
    # reaches it, so core/comm/roster.py::go_offline (called ONLY from here) reported
    # built-not-wired while being precisely wired. Same class as the supervisor line.
    "agent/harness/dsh_plugin/bridge.py",
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
    "core/comm/wedge_discriminator.py": "KEEP built-ahead: T376 S5 decision core (half_a section 2.3 "
        "verbatim, 8 pins green in tests/test_t376_s5_wedge_discriminator.py, authored deepseek); the "
        "production consumer is the doctor/OOB py-spy executor which needs a live runner PID -- lands "
        "at the S6 drill (F004's own dies_when). Wire it there, then remove this entry.",
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
    "core/toolbelt/contest.py": "built-ahead (28ffd5b): the chorus door, kimi's build, "
        "claude-run green. UNWIRE-WHEN: a production caller invokes contest -- today only "
        "its pins exercise it. Owner: kimi lane / T099 self-tooling.",
    "core/coord/experiment.py": "built-ahead: Stage-3 coordination evidence engine",
    "core/coord/metrics.py": "built-ahead: coordination metrics watchdog",
    "core/coord/shift_loop.py": "KEEP built-ahead (2026-08-24, deepseek): the autonomous shift "
        "loop decision core (fence shift-loop, docs/library/design/autonomous-shift-loop-design.md). "
        "12 hermetic pins green in tests/test_shift_loop.py. Its production consumer is the runner "
        "turn boundary (wiring CLAIM/HANDOFF beside the existing maybe_self_restart call) — FENCED for "
        "operator+Vandor review, deliberately not built tonight (live self-modification). UNWIRE-WHEN: "
        "the runner turn boundary calls next_beat() + reads the shift-state note; then remove this entry.",
    "core/comm/remote_relay.py": "KEEP built-ahead (2026-08-24, deepseek): outbound-only "
        "Akashic<->Akashic bridge v0.1 (fence remote-bridge, "
        "docs/library/design/remote-bifrost-bridge-design.md). 9 pins green in "
        "tests/test_remote_relay_pins.py, all offline (transport injected). Deliberately "
        "inert-until-keyed + unrouted-refuses: NO production consumer BY DESIGN until v1's "
        "inbound HTTP listener (the dangerous half) lands and a caller invokes push(). "
        "Wiring push() before v1 would POST on every forwardable message with zero delivery "
        "semantics, contradicting the module's own absent-is-not-broken property. "
        "UNWIRE-WHEN: the v1 inbound listener + a production push() caller land; then remove "
        "this entry.",
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
    "core/comm/role_queue.py": "built-ahead (3919731, T108 S1): the role work queue. Design "
        "settled by the T108 fence and gated by Daniil 2026-07-28. VERIFIED NEVER RUN "
        "2026-08-01 -- bifrost:role:*, *rolefence*, *rolegen* all hold ZERO keys and no "
        "production module imports it; the reaper still routes around it (reaper.py:228 strips "
        "to_incarnation, :239 re-sends onto the shared inbox). UNWIRE-WHEN: the T108 migration "
        "routes directed/role mail through it. Owner: T108.",
    "core/recall/gate_rules.py": "built-ahead (dc8584e, R2 slice 1a): the silence-gate rules, "
        "written deliberately BEFORE the gate that consumes them -- its own docstring says so, "
        "because a rule stated by pointing at the census sample would be a fit rather than a "
        "principle. UNWIRE-WHEN: the silence gate lands and imports them. Owner: recall-heuristics.",
    "core/recall/precision_audit.py": "built-ahead (52db9b5): the retrieval-accuracy instrument "
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
# capability inside it was dead. Git holds the diagnosis in a human's handwriting -- c91ca73 built
# declare_intent with 8/8 pins, and e438ccd wired it with the message "built was not wired -- no
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

# T144: marks a reference that came from a STRING CONSTANT rather than a name/attr/alias.
# Tagged rather than dropped, because string evidence is still real -- getattr dispatch -- but only
# when it crosses a module boundary. Plain ASCII on purpose: a sentinel that cannot appear in a
# Python identifier, and cannot corrupt the source the way a control character would.
STRLIT = "STRLIT::"

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "wiring_function_baseline.json")


# T146: there is deliberately NO container list here any more. The T143 fix enumerated
# (If, Try, With, AsyncWith, For, AsyncFor, While) and the PYTHON GRAMMAR drifted past it --
# ast.Match (3.10) and ast.TryStar (3.11) both walked straight through, as did methods on inner
# classes. That is the same anti-pattern this file warns about for ENTRY_POINTS two functions up:
# a hand-written list drifts the moment the world adds a member. public_defs now descends any
# statement that is not a def, structurally, so a grammar addition in 3.14 needs no edit here.


def public_defs(rel, root=ROOT):
    """[(name, lineno, end_lineno, is_method)] -- public functions and methods defined in rel.

    Module level (including inside module-level if/try/with/for/while) and one level into a class.
    Nested defs are private by construction. `main` is a self-invoking entry convention, and
    dunders are protocol, not capability.

    T143, found by a red team and confirmed by running it: this used to iterate `tree.body` and
    type-check for FunctionDef/ClassDef, so a def wrapped in ANY module-level statement sat inside
    an If/Try/With node and the walk stepped straight over it -- invisible in both directions,
    never reported dead and never counted. A dead public function appended to core/comm/bus.py
    inside `if _FLAG:` produced a clean PASS from the whole gate.

    That shape is ordinary, not exotic: `if TYPE_CHECKING:`, `try: import fast / except
    ImportError:` fallback defs, and `if os.environ.get("ENABLE_X"):` all produce it by accident.

    The descent stops at the first function boundary on purpose. A closure is private by
    construction, and reporting closures would flood the gate -- which is how a guard gets fed
    exceptions until it guards nothing, the lesson this file's comments already record twice.
    """
    out = []
    try:
        tree = ast.parse(open(os.path.join(root, rel), encoding="utf-8", errors="replace").read())
    except Exception:
        return out

    def _take(node, is_method):
        if not node.name.startswith("_") and node.name != "main":
            out.append((node.name, node.lineno, getattr(node, "end_lineno", node.lineno), is_method))

    def _nested(node):
        """Every statement nested inside a non-def statement, at ANY field name.

        No list of node types and no list of field names. ExceptHandler and match_case are not
        statements themselves, so their bodies are reached one level deeper -- generically.
        """
        found = []
        for _f, val in ast.iter_fields(node):
            for item in (val if isinstance(val, list) else [val]):
                if isinstance(item, ast.stmt):
                    found.append(item)
                elif isinstance(item, ast.AST):        # ExceptHandler, match_case, ...
                    for _f2, val2 in ast.iter_fields(item):
                        for it2 in (val2 if isinstance(val2, list) else [val2]):
                            if isinstance(it2, ast.stmt):
                                found.append(it2)
        return found

    def _walk(stmts, in_class=False):
        for node in stmts:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _take(node, in_class)                  # do NOT descend: nested defs stay private
            elif isinstance(node, ast.ClassDef):
                _walk(node.body, in_class=True)        # inner classes are still public surface
            else:
                _walk(_nested(node), in_class=in_class)

    _walk(tree.body)
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
    # T145: lines belonging to an `__all__` assignment. An export list DECLARES a surface; it does
    # not USE anything. T144 excluded same-module strings, which closed `__all__` written beside the
    # function -- and the hole simply MOVED into the package __init__.py, the most idiomatic home
    # for __all__ in Python, where the cross-module test waves it through. Chasing the location
    # would only move it again, so the manifest itself is excluded wherever it lives. This cannot
    # create a false positive by construction: a function whose only mention is an export list is
    # by definition not called by anyone.
    _all_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    end = getattr(node, "end_lineno", node.lineno) or node.lineno
                    _all_lines.update(range(node.lineno, end + 1))
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.Name):
            out.append((node.id, ln))
        elif isinstance(node, ast.Attribute):
            out.append((node.attr, ln))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if ln not in _all_lines:                  # T145: __all__ is a manifest, not a use
                out.append((STRLIT + node.value, ln))  # T144: tagged, weighed differently below
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
    sites, strsites = {}, {}
    for p in production_files:
        for name, ln in reference_sites(p, root=root):
            if name.startswith(STRLIT):
                strsites.setdefault(name[len(STRLIT):], []).append((p, ln))
            else:
                sites.setdefault(name, []).append((p, ln))
    out = []
    for m in candidate_mods:
        for name, lo, hi, _is_method in public_defs(m, root=root):
            wired = any(mod != m or not (lo <= ln <= hi) for mod, ln in sites.get(name, ()))
            if not wired:
                # T144: a STRING naming a function is evidence only from ANOTHER module. A string
                # is how a CALLER dispatches (getattr(mod, "promote")), and a caller lives
                # elsewhere; a module naming itself in a string is DESCRIBING itself, not using
                # itself. `__all__ = ["dead_fn"]` was proving its own exports alive, so every
                # module with an export list blinded the gate to exactly what it exported.
                wired = any(mod != m for mod, _ln in strsites.get(name, ()))
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


def _script_files():
    """Every .py under scripts/ -- ALL of them are production call paths (T134c).

    scripts/ is the tools directory: a file in it is either run by a human or imported by one that
    is, and the import graph cannot tell which. Measured 2026-08-03: counting only the reachable
    ones left 29 of 47 invisible, including mirror.py (commit+push), ship.py and snapshot.py. The
    caller that exposed it was `scripts/snapshot.py:21  snaps = list_snapshots()` -- a live backup
    door with NO `__main__` guard (it needs none; `py scripts/snapshot.py` runs the module body),
    so neither the BFS nor self_invoking_modules could see it.

    This can only ADD evidence of wiring. A function nothing anywhere names is still reported.
    """
    out = set()
    for dp, _dn, fn in os.walk(os.path.join(ROOT, "scripts")):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f.endswith(".py"):
                out.add(os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/"))
    return out


def candidate_modules(reachable=None, core_universe=None):
    """The FUNCTION gate's TRUE field of view: reachable core modules, minus EXCEPTIONS.

    THE ONE DEFINITION. Everything that needs to know what this gate examines asks here rather
    than re-deriving it, and function_level() below consumes it so the gate itself keeps the
    definition honest.

    T159, and it is worth stating plainly because the ticket got it backwards: a module OUTSIDE
    this set is not a blind spot, it is already reported at MODULE granularity. Listing every dead
    function inside an already-reported dead module is the noise that turns a guard into a thing
    people silence -- the same argument unwired_functions' docstring makes about candidate_mods.

    That distinction is invisible from outside, which is how it caused a false measurement. The
    T158 canary oracle planted into `core_universe` (151 modules) on the reasonable-looking
    assumption that it was the gate's scope. The gate's scope is this (134). The 17-module
    difference is territory where a MISS IS CORRECT BEHAVIOUR, so canaries landing there were
    scored as detector failures and published 0.67 detector health for a healthy detector.

    Exported rather than inlined for exactly that reason: the previous fix RE-IMPLEMENTED the
    selector by walking core/, and a copy drifts the moment either side moves. Callers outside
    this process get the same answer through `--candidates`.
    """
    if reachable is None or core_universe is None:
        core_universe, reachable, _unwired = analyze()
    return sorted(m for m in core_universe if m in reachable and m not in EXCEPTIONS)


def function_level(reachable, core_universe):
    """-> (candidate_mods, production_files, orphans, stale) for the gate and the report."""
    cand = candidate_modules(reachable, core_universe)
    prod = sorted({p for p in (set(ENTRY_POINTS) | _script_files()
                               | {r for r in reachable if r.endswith(".py")})
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

    # T159: the machine-readable door onto the field of view. The canary oracle runs against a
    # SHADOW worktree, so it must ask THAT tree's own detector what it examines -- a shadow can
    # be a different commit, with a different EXCEPTIONS list and a different import graph.
    # Answering across the process boundary is what makes "ask, never re-implement" enforceable.
    if "--candidates" in sys.argv:
        print(json.dumps(candidate_modules(reachable, core_universe)))
        return 0

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
