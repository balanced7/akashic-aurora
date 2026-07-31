"""gen_datasheet -- T125 v0: the per-module DATASHEET, mechanically derived.

Daniil's ruling (2026-07-31), verbatim: "the thing that would confuse me is not knowing what ties
to what and why... walk the inputs and outputs of this system and query it... what module depends
on this, what logic sections would touching this change... Our current method for finding out what
links to what is too unintuitive and costly so it doesn't get done, THIS is the heart of what I am
trying to fix."

The shape is a COMPONENT DATASHEET plus a blast-radius query -- not an ontology. v0 is MECHANICAL
ONLY: every field below is derived from the code itself, so nobody authors it and it cannot lie
about the past. Authored claims (who owns truth, what must never happen) are deliberately ABSENT
in v0; they arrive later, labelled AUTHORED, never laundered through the word "compiled".

Three laws this file obeys, each from a named failure:
  1. UNIVERSE = ONE REVISION, WORKTREES EXCLUDED. The file list comes from `git ls-files`, so a
     registered worktree (.claude/worktrees/*, which still carries a pre-T104 layout) can never be
     compiled into the map. A tree-walk would have merged TWO Auroras silently -- a live grep hit
     the ghost copy before the real one on 2026-07-31.
  2. UNSCANNED != EMPTY. Every run emits a coverage manifest naming what it could not read and
     why. A module missing from the output must be distinguishable from a module with no edges.
  3. UNKNOWN IS LEGAL. A field we cannot derive renders UNKNOWN and blocks nothing. Nothing here
     renders "verified" -- v0 has no gate receipts, so it makes no verification claims at all.

Run:  py scripts/generators/gen_datasheet.py --explain core/comm/bus.py   # one datasheet
      py scripts/generators/gen_datasheet.py --impact core/comm/bus.py    # blast radius
      py scripts/generators/gen_datasheet.py --json                       # whole graph
      py scripts/generators/gen_datasheet.py --coverage                   # manifest only
"""
import ast
import collections
import itertools
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Package roots that count as INTERNAL edges. An import outside these is external (stdlib or dep)
# and is recorded separately -- "what third-party surface does this module touch" is part of the
# datasheet a reader needs before touching it.
INTERNAL_ROOTS = ("core", "scripts", "agent", "context", "security", "infrastructure")


def _git_files():
    """The universe: tracked .py files at ONE revision. Law 1.

    `git ls-files` lists the index of THIS working tree only -- a linked worktree has its own
    index and cannot appear here. That is why the universe is declared this way rather than by
    walking the filesystem and excluding paths by pattern: an exclusion list is something a
    later edit can forget, and this cannot be forgotten.
    """
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "*.py"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return [], f"git ls-files failed rc={r.returncode}: {(r.stderr or '').strip()[:200]}"
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()], ""


def _rev():
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() or "UNKNOWN"


def _annot(node):
    """Render a type annotation back to source text. Returns UNKNOWN when absent -- an unannotated
    parameter is genuinely unknown, and saying so is the point (law 3)."""
    if node is None:
        return "UNKNOWN"
    try:
        return ast.unparse(node)
    except Exception:
        return "UNKNOWN"


def _signature(fn):
    """Inputs and accepted types, straight off the def. Daniil asked for 'limits and accepted
    filetypes'; for a Python component the honest mechanical answer is the parameter list with its
    annotations, plus the return annotation."""
    a = fn.args
    parts = []
    for arg in list(a.posonlyargs) + list(a.args):
        parts.append({"name": arg.arg, "type": _annot(arg.annotation)})
    if a.vararg:
        parts.append({"name": "*" + a.vararg.arg, "type": _annot(a.vararg.annotation)})
    for arg in a.kwonlyargs:
        parts.append({"name": arg.arg, "type": _annot(arg.annotation)})
    if a.kwarg:
        parts.append({"name": "**" + a.kwarg.arg, "type": _annot(a.kwarg.annotation)})
    return {"params": parts, "returns": _annot(fn.returns)}


def _parse(rel):
    path = os.path.join(ROOT, rel)
    try:
        src = open(path, encoding="utf-8").read()
    except Exception as e:
        return None, f"unreadable: {type(e).__name__}"
    try:
        return ast.parse(src), ""
    except SyntaxError as e:
        # A file we cannot parse is UNSCANNED, not empty (law 2). Python 2 leftovers and templates
        # live in the tree; they must not silently render as "this module has no API".
        return None, f"syntax error line {e.lineno}"


def _module_name(rel):
    return rel[:-3].replace("/", ".").replace("\\", ".")


_PATH_EXT = (".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh")


def _path_refs(tree):
    """Repo paths a module NAMES but does not import -- the class that killed the pre-commit gate.

    `scripts/githooks/pre_commit.py` invokes `os.path.join(ROOT, "scripts", "check_comprehensibility.py")`.
    That file moved to scripts/checkers/ in T104-M1; the missing path makes the interpreter exit rc=2,
    and the caller blocks only on rc==1, so the drift guard has been silently dead at the commit layer
    while its own docstring claims UNBYPASSABLE. cursor_grok hit the same wall from the other side as a
    newcomer ("where is check_comprehensibility.py?" -> FileNotFoundError). An import graph cannot see
    this: the reference is a STRING, and it is assembled from join() segments rather than written whole.

    So both forms are collected: bare literals, and os.path.join(...) whose string args are constants
    (a leading ROOT-style name contributes nothing and is skipped). Reconstructed relative paths are
    checked against the universe; misses render BROKEN.

    Only ROOT-ANCHORED reconstructions are returned. `os.path.join(SOME_VAR, "models.json")` yields
    a single constant whose directory came from a variable -- we do not know where it points, so it
    is not a reference we may call BROKEN. Claiming otherwise would be the exact failure this whole
    round is about: an instrument reporting a fact about the world when it only has a fact about its
    own reach. Unanchored refs are dropped here and counted as unresolved in the manifest.
    """
    roots = INTERNAL_ROOTS + ("tests", "docs", "research")
    refs, unresolved = set(), 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
            if name == "join":
                parts = [a.value for a in node.args
                         if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if not (parts and any(p.endswith(_PATH_EXT) for p in parts)):
                    continue
                if len(parts) >= 2 and parts[0] in roots:
                    refs.add("/".join(parts))          # root-anchored: resolvable
                else:
                    unresolved += 1                    # directory came from a variable: UNKNOWN
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.strip()
            if any(c in v for c in "\\[]*+()?"):       # a regex, not a path
                continue
            if (v.endswith(_PATH_EXT) and "/" in v and " " not in v
                    and v.lstrip("./").split("/")[0] in roots):
                refs.add(v.lstrip("./"))
    return sorted(refs), unresolved


def _history():
    """The TEMPORAL lens, over the same universe and the same revision as the structural one.

    Daniil's ask: "a cheap instant snapshot ... to help you understand what is going on at any
    given moment ... I'm trying to reduce the burden of concurrency." So this answers "what moved
    under me", not "what is old" -- raw age cannot tell a settled primitive from an abandoned one.

    Three honesty constraints, each earned:
      - HORIZON. Git history here begins ~34d ago while the project is months old. A file at the
        ceiling was not "last touched 34 days ago", it was NOT TOUCHED SINCE THE HORIZON, and the
        two must not render alike. UNSCANNED != EMPTY, applied to time.
      - NO LIVENESS CLAIM. Git sees COMMITTED state only. A peer editing right now is invisible
        here; that is the advisory locks' job. This surface must never imply who is active.
      - AUTHORSHIP IS NOT AVAILABLE. 1371 commits, one author (`balanced7`) -- mirror/claude is
        sole committer, so git collapses the whole fleet into one name. Per-agent attribution has
        to come from the ledger. It is omitted here rather than faked.

    Co-change is the payload. Files that always change together but never import each other are
    coupled in practice and invisible to the import graph -- `agent_cli.py` and `ai_setup_mcp.py`
    move together 2 times in 3 with no edge between them (the same verbs behind two doors).
    Sweeps are excluded: a commit touching everything couples everything and means nothing.
    """
    raw = subprocess.run(["git", "-C", ROOT, "log", "--format=@%at", "--name-only"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    commits, cur, ts = [], None, None
    for ln in raw.splitlines():
        ln = ln.strip()
        if ln.startswith("@"):
            if cur is not None:
                commits.append((ts, cur))
            ts, cur = int(ln[1:]), []
        elif ln and cur is not None:
            cur.append(ln.replace("\\", "/"))
    if cur is not None:
        commits.append((ts, cur))

    last, touches = {}, collections.Counter()
    pair, solo = collections.Counter(), collections.Counter()
    horizon = min((t for t, _ in commits), default=None)
    for t, fs in commits:                                  # newest-first: first sighting wins
        for f in set(fs):
            touches[f] += 1
            last.setdefault(f, t)
        py = [f for f in set(fs)
              if f.endswith(".py") and not f.startswith(("tests/", "docs/_archive"))]
        if 2 <= len(py) <= 12:                             # sweep guard
            for f in py:
                solo[f] += 1
            for a, b in itertools.combinations(sorted(py), 2):
                pair[(a, b)] += 1

    cochange = collections.defaultdict(list)
    for (a, b), n in pair.items():
        denom = min(solo[a], solo[b])
        if n >= 4 and denom and n / denom >= 0.5:
            cochange[a].append({"with": b, "times": n, "confidence": round(n / denom, 2)})
            cochange[b].append({"with": a, "times": n, "confidence": round(n / denom, 2)})
    return last, touches, cochange, horizon


def build():
    files, git_err = _git_files()
    sheets, skipped = {}, []
    if git_err:
        return {"error": git_err, "sheets": {}, "coverage": {"fatal": git_err}}

    for rel in files:
        rel = rel.replace("\\", "/")
        tree, err = _parse(rel)
        if tree is None:
            skipped.append({"path": rel, "reason": err})
            continue
        doc = ast.get_docstring(tree)
        exposes, internal, external = [], set(), set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                exposes.append({"kind": "function", "name": node.name, **_signature(node)})
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                methods = [n.name for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and not n.name.startswith("_")]
                exposes.append({"kind": "class", "name": node.name, "methods": methods})
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    (internal if n.name.split(".")[0] in INTERNAL_ROOTS else external).add(n.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                bucket = internal if node.module.split(".")[0] in INTERNAL_ROOTS else external
                bucket.add(node.module)
                # `from core.comm import mailbox` binds a SUBMODULE, not an attribute, and the
                # dotted target is what the reverse-edge resolver looks up. Recording only the
                # package under-reported blast radius: core/comm/mailbox.py rendered fan-in 1 while
                # agent_cli.py:3929 and core/comm/promoter.py:111 both import it. Caught by grepping
                # the tool's own answer instead of trusting it -- the field that matters most was
                # the field that was wrong. Names that resolve to no module simply never match.
                for alias in node.names:
                    bucket.add(f"{node.module}.{alias.name}")
        sheets[rel] = {
            "path": rel,
            "module": _module_name(rel),
            "spec": " ".join(doc.strip().splitlines()[0].split())[:160] if doc else "UNKNOWN (no docstring)",
            "exposes": exposes,
            "imports_internal": sorted(internal),
            "imports_external": sorted(external),
            "depended_on_by": [],
            "tested_by": [],
            "flags": [],
            "path_refs": _path_refs(tree)[0],
            "unresolved_path_refs": _path_refs(tree)[1],
            "broken_path_refs": [],
            "fixture_path_refs": [],
        }

    # Reverse edges: who breaks if I touch this. Resolved by DOTTED NAME against the universe, not
    # by filename similarity -- MAP.md's name-match is an explicit v0 heuristic and it must not
    # leak into a field that answers "what does touching this change".
    by_module = {s["module"]: rel for rel, s in sheets.items()}
    for rel, s in sheets.items():
        for imp in s["imports_internal"]:
            target = by_module.get(imp)             # dotted submodule names now come from the
                                                    # ImportFrom aliases above, so no guessing here
            if target and target != rel:
                sheets[target]["depended_on_by"].append(rel)
    for s in sheets.values():
        s["depended_on_by"] = sorted(set(s["depended_on_by"]))

    # Tests naming the module by dotted path -- precise, not a stem heuristic.
    for rel, s in sheets.items():
        if not rel.startswith("tests/"):
            continue
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except Exception:
            continue
        for mod, target in by_module.items():
            if mod in src and target != rel:
                sheets[target]["tested_by"].append(rel)
    for s in sheets.values():
        s["tested_by"] = sorted(set(s["tested_by"]))

    # Named-but-missing paths. Checked against the UNIVERSE for .py (law 1 -- a file that exists only
    # in a linked worktree must still read as BROKEN here) and against disk for everything else.
    # A test naming `core/x.py` is a FIXTURE, not a defect -- guards are tested by feeding them
    # paths that deliberately do not exist. Counting those as breakage would bury the real hits
    # (27 raw -> 3 live), which is how a guard trains people to ignore it.
    universe = set(f.replace("\\", "/") for f in files)
    for rel, s in sheets.items():
        bucket = "fixture_path_refs" if rel.startswith("tests/") else "broken_path_refs"
        for ref in s["path_refs"]:
            ok = ref in universe if ref.endswith(".py") else os.path.exists(os.path.join(ROOT, ref))
            if not ok:
                s[bucket].append(ref)

    # Env flags read, reusing the shipped physics scanner rather than a second scanner that could
    # disagree with PHYSICS.md.
    flag_err = ""
    try:
        from gen_physics_sheet import scan as physics_scan
        flags, _bounds = physics_scan()
        for name, sites in flags.items():
            for site, _default in sites:
                p = site.split(":")[0].replace("\\", "/")
                if p in sheets:
                    sheets[p]["flags"].append(name)
        for s in sheets.values():
            s["flags"] = sorted(set(s["flags"]))
    except Exception as e:
        flag_err = f"{type(e).__name__}: {e}"

    # Temporal band. Attached to the SAME sheets so the two perspectives can never drift apart
    # into two organs that disagree -- the failure cursor_grok hit with roster-DEAD vs presence-online.
    now = int(time.time())
    last, touches, cochange, horizon = _history()
    horizon_days = round((now - horizon) / 86400.0, 1) if horizon else None
    for rel, s in sheets.items():
        t = last.get(rel)
        age = round((now - t) / 86400.0, 1) if t else None
        s["touches"] = touches.get(rel, 0)
        s["last_touch_days"] = age if age is not None else "UNKNOWN (no commit in history)"
        # At the ceiling we only know "not since the horizon" -- do not render it as a precise age.
        s["at_horizon"] = bool(age is not None and horizon_days and age >= horizon_days - 0.5)
        # Only NON-import partners: an import edge is already visible in depends_on, so surfacing it
        # again as "coupling" would inflate the signal with things the reader can already see.
        s["changes_with"] = sorted(
            [c for c in cochange.get(rel, []) if c["with"] not in
             {by_module.get(m, "") for m in s["imports_internal"]} | set(s["depended_on_by"])],
            key=lambda c: -c["confidence"])

    coverage = {
        "revision": _rev(),
        "history_horizon_days": horizon_days,
        "horizon_note": ("Git history begins here; the project predates it. at_horizon=true means "
                         "NOT TOUCHED SINCE THE HORIZON, not 'last changed that many days ago'."),
        "liveness_note": ("COMMITTED state only. A peer editing uncommitted right now is invisible "
                          "here -- that is the advisory locks' plane. Nothing here implies who is active."),
        "authorship": ("UNAVAILABLE from git: all commits carry one author (sole-committer pattern), "
                       "so per-agent attribution must come from the ledger. Omitted rather than faked."),
        "universe": "git ls-files *.py (ONE revision; linked worktrees structurally excluded)",
        "in_universe": len(files),
        "scanned": len(sheets),
        "skipped": skipped,
        "unscanned_note": "A path in `skipped` has NO datasheet. Absent != no edges.",
        "not_derived_in_v0": [
            "open ledger tasks touching a path (join not built in v0)",
            "authored claims: authoritative_for, MUST NOT, required authority (v0 is mechanical only)",
            "runtime/observed receipts (no gate-health receipts exist yet -- nothing renders VERIFIED)",
        ],
    }
    if flag_err:
        coverage["flags_unscanned"] = flag_err
    return {"sheets": sheets, "coverage": coverage}


def render_sheet(s, cov):
    L = [f"# {s['path']}", "", f"**spec**  {s['spec']}", "",
         f"rev {cov['revision']} · mechanical v0 · no field here is VERIFIED (no gate receipts exist)", ""]
    L.append("## exposes")
    if not s["exposes"]:
        L.append("- (nothing public)")
    for e in s["exposes"]:
        if e["kind"] == "class":
            L.append(f"- class `{e['name']}` — methods: {', '.join(e['methods']) or '(none public)'}")
        else:
            args = ", ".join(f"{p['name']}: {p['type']}" for p in e["params"])
            L.append(f"- `{e['name']}({args}) -> {e['returns']}`")
    L += ["", "## depends on (internal)"] + ([f"- {i}" for i in s["imports_internal"]] or ["- (none)"])
    L += ["", f"## blast radius — {len(s['depended_on_by'])} module(s) import this"]
    L += [f"- {d}" for d in s["depended_on_by"]] or ["- (none in universe)"]
    L += ["", "## verified by (tests naming it)"] + ([f"- {t}" for t in s["tested_by"]] or ["- UNKNOWN (no test names this module)"])
    L += ["", "## env flags read"] + ([f"- `{f}`" for f in s["flags"]] or ["- (none)"])
    L += ["", "## external surface"] + ([f"- {i}" for i in s["imports_external"][:20]] or ["- (none)"])
    if s["broken_path_refs"]:
        L += ["", "## !! BROKEN path references (named, but not in the universe)"]
        L += [f"- `{b}`" for b in s["broken_path_refs"]]
    age = (f">= {cov['history_horizon_days']}d (at horizon -- not touched since history begins)"
           if s.get("at_horizon") else f"{s.get('last_touch_days')}d ago")
    L += ["", "## temporal (committed state only -- says nothing about who is active NOW)",
          f"- last changed: {age}", f"- touches in history: {s.get('touches')}"]
    if s.get("changes_with"):
        L += ["", "## changes together with (no import edge -- coupling the import graph cannot see)"]
        L += [f"- `{c['with']}` — {c['confidence']:.0%} of the time ({c['times']}x)"
              for c in s["changes_with"]]
    L += ["", "## not derived in v0"] + [f"- {n}" for n in cov["not_derived_in_v0"]]
    return "\n".join(L)


def main():
    argv = sys.argv[1:]
    g = build()
    if g.get("error"):
        print("FATAL:", g["error"])
        return 2
    sheets, cov = g["sheets"], g["coverage"]

    if "--json" in argv:
        print(json.dumps(g, indent=2))
        return 0
    if "--coverage" in argv:
        print(json.dumps(cov, indent=2))
        return 0
    for flag in ("--explain", "--impact"):
        if flag in argv:
            try:
                target = argv[argv.index(flag) + 1].replace("\\", "/")
            except IndexError:
                print(f"{flag} needs a path, e.g. core/comm/bus.py")
                return 2
            s = sheets.get(target)
            if not s:
                skip = next((k for k in cov["skipped"] if k["path"] == target), None)
                if skip:
                    print(f"UNSCANNED: {target} — {skip['reason']} (no datasheet; this is not 'no edges')")
                    return 1
                print(f"NOT IN UNIVERSE: {target} — not a tracked .py file at rev {cov['revision']}")
                return 1
            if flag == "--explain":
                print(render_sheet(s, cov))
            else:
                print(f"# impact of touching {target}\n")
                print(f"{len(s['depended_on_by'])} module(s) import it directly:")
                for d in s["depended_on_by"]:
                    print(f"  {d}")
                print(f"\n{len(s['tested_by'])} test file(s) name it:")
                for t in s["tested_by"] or ["  UNKNOWN - nothing names this module"]:
                    print(f"  {t}" if t.startswith("tests") else t)
                if s.get("changes_with"):
                    print("\nALSO CHECK - historically changes with it, no import edge:")
                    for c in s["changes_with"]:
                        print(f"  {c['with']}  ({c['confidence']:.0%} of the time, {c['times']}x)")
            return 0

    if "--pulse" in argv:
        # The at-a-glance orientation snapshot. THREE bands of five -- a surface you must read
        # forty rows of is not "at a glance", it is another thing to get through.
        live = {p: s for p, s in sheets.items()
                if not p.startswith(("tests/", "docs/_archive"))
                and isinstance(s.get("last_touch_days"), (int, float))}
        print(f"PULSE @{cov['revision']} | {cov['scanned']}/{cov['in_universe']} scanned, "
              f"{len(cov['skipped'])} UNSCANNED | history horizon {cov['history_horizon_days']}d")
        print("committed state only -- says nothing about who is editing right now\n")

        print("MOVING (most recently committed):")
        for p, s in sorted(live.items(), key=lambda kv: kv[1]["last_touch_days"])[:5]:
            print(f"  {s['last_touch_days']:5.1f}d  {p:<44} fan-in {len(s['depended_on_by']):3d}")

        print("\nDIVERGING (cold, but its dependents moved):")
        rows = []
        for p, s in live.items():
            deps = [live[d]["last_touch_days"] for d in s["depended_on_by"] if d in live]
            if len(s["depended_on_by"]) >= 3 and deps:
                med = sorted(deps)[len(deps) // 2]
                if s["last_touch_days"] - med > 20:
                    rows.append((s["last_touch_days"] - med, p, s, med))
        for gap, p, s, med in sorted(rows, reverse=True)[:5]:
            print(f"  gap {gap:5.1f}d  {p:<40} self {s['last_touch_days']:5.1f}d vs deps {med:5.1f}d")
        if not rows:
            print("  (none)")

        print("\nRISK (churn x blast radius):")
        for p, s in sorted(live.items(),
                           key=lambda kv: -(kv[1]["touches"] * max(len(kv[1]["depended_on_by"]), 1)))[:5]:
            print(f"  {s['touches']:4d} touches x fan-in {len(s['depended_on_by']):3d}  {p:<40}"
                  f" tested={'yes' if s['tested_by'] else 'NO'}")
        return 0

    print(f"datasheets: {cov['scanned']} scanned of {cov['in_universe']} in universe "
          f"@{cov['revision']}; {len(cov['skipped'])} UNSCANNED")
    print("try: --explain <path> | --impact <path> | --pulse | --json | --coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
