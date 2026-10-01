#!/usr/bin/env python3
"""Goal certification for the 2026-10 Python tooling upgrade (plan sections 12-14). Stdlib only.

    certify.py G<n> [--phase G<n>.P<k>] [--drills]   run checks + T1-T7 (+ drills) and print
                                                      the certificate block
    certify.py G<n> --tamper-only                     T1-T7 only (the D15 gate)
    certify.py assert-branch                          HEAD is the migration branch, in a linked worktree
    certify.py assert-checks-files                    checks/G0..G7.toml tracked, parseable, append-only
    certify.py suppressions [--write]                 regenerate / verify SUPPRESSIONS.md (T4)
    certify.py fresh-clone [--gate]                   clone --no-hardlinks, uv sync --locked (, poe gate)
    certify.py drills [--expect-missed]               D01-D15 alone

The evaluator of a goal cannot run anything, so this script runs every pre-registered check
itself and prints one block. It refuses to print CERTIFIED when the worktree is dirty, HEAD is
off the branch, a checks entry was removed or changed after registration, or no oracle record
is current for HEAD (the "suite record postdates the newest *.py/pyproject/uv.lock commit"
rule, implemented as digest equality: oracle.relevant_digest).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle  # noqa: E402  (sibling module, stdlib-only)

HERE = oracle.HERE
ROOT = oracle.ROOT
CHECKS = HERE / "checks"
BRANCH = oracle.BRANCH
GOALS = tuple("G%d" % i for i in range(8))

# T-rules start to bind when the goal that creates their subject begins (pytest.ini is deleted
# in G1, Ruff arrives in G2/G3, basedpyright in G4). Before that a rule is measured and reported,
# never silently treated as passing.
T_ACTIVE_FROM = {"T1": 1, "T2": 2, "T3": 3, "T4": 3, "T5": 3, "T6": 1, "T7": 0}
FORBIDDEN_CONFIGS = (
    "ruff.toml",
    ".ruff.toml",
    "pyrightconfig.json",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    ".coveragerc",
)
GATE_TASKS = ("fmt-check", "lint-check", "types", "lock-check", "deps", "ci-lint", "guardrails", "test-fast", "gate")
GATE_FORBIDDEN = ("--fix", "--exit-zero", "|| true", "--skip")


def run(cmd, cwd=ROOT, env=None, timeout=None):
    return oracle.run(cmd, cwd=cwd, env=env, timeout=timeout)


def git(*args, cwd=ROOT, check=True):
    return oracle.git(*args, cwd=cwd, check=check)


def goal_num(goal: str) -> int:
    return int(goal[1:])


# ----------------------------------------------------------------------------- checks files


def load_checks(goal: str, ref: str | None = None) -> dict:
    rel = "tooling-upgrade/checks/%s.toml" % goal
    text = git("show", "%s:%s" % (ref, rel)) if ref else (ROOT / rel).read_text(encoding="utf-8")
    return tomllib.loads(text)


def expand(cmd):
    parts = cmd if isinstance(cmd, list) else cmd.split()
    return [p.replace("{python}", sys.executable).replace("{root}", str(ROOT)) for p in parts]


def run_check(c: dict):
    try:
        r = run(expand(c["cmd"]), timeout=c.get("timeout_s", 7200))
    except subprocess.TimeoutExpired:
        return False, "timeout", ""
    out = r.stdout + r.stderr
    ok = r.returncode == c.get("expect", 0)
    if ok and c.get("expect_stdout"):
        ok = re.search(c["expect_stdout"], r.stdout, flags=re.M) is not None
        if not ok:
            return False, "stdout lacks /%s/" % c["expect_stdout"], out
    return ok, "exit %d (expect %d)" % (r.returncode, c.get("expect", 0)), out


def checks_history_problems() -> list:
    """Append-only rule for checks/*.toml: every [[check]] keeps its id, cmd, expect, phase and
    expect_stdout from the commit that registered it; required_drills only grows."""
    problems = []
    for goal in GOALS:
        rel = "tooling-upgrade/checks/%s.toml" % goal
        shas = git("log", "--format=%H", "--reverse", "--", rel, check=False).split()
        prev = None
        for sha in shas + ["WORKTREE"]:
            try:
                cur = load_checks(goal, None if sha == "WORKTREE" else sha)
            except (subprocess.SubprocessError, RuntimeError, OSError, tomllib.TOMLDecodeError) as e:
                problems.append("%s at %s unreadable: %s" % (rel, sha[:9], str(e).splitlines()[0][:80]))
                break
            if prev is not None:
                new = {c["id"]: c for c in cur.get("check", [])}
                for c in prev.get("check", []):
                    n = new.get(c["id"])
                    keys = ("cmd", "expect", "phase", "expect_stdout")
                    if n is None:
                        problems.append("%s: check %s removed at %s" % (goal, c["id"], sha[:9]))
                    elif any(c.get(k) != n.get(k) for k in keys):
                        problems.append("%s: check %s changed at %s" % (goal, c["id"], sha[:9]))
                if not set(prev.get("required_drills", [])) <= set(cur.get("required_drills", [])):
                    problems.append("%s: required_drills shrank at %s" % (goal, sha[:9]))
            prev = cur
    return problems


def cmd_assert_checks_files(args) -> int:
    tracked = set(git("ls-files", "tooling-upgrade/checks").split())
    problems = ["%s not committed" % g for g in GOALS if "tooling-upgrade/checks/%s.toml" % g not in tracked]
    for g in GOALS:
        try:
            data = load_checks(g)
            if not data.get("check"):
                problems.append("%s has no checks" % g)
        except (OSError, tomllib.TOMLDecodeError) as e:
            problems.append("%s unparseable: %s" % (g, e))
    problems += checks_history_problems()
    for p in problems:
        print("  ", p)
    print("CHECKS FILES: %s" % ("G0-G7 committed, append-only" if not problems else "FAIL"))
    return 1 if problems else 0


# ----------------------------------------------------------------------------- repo state


def worktree_clean() -> bool:
    return git("status", "--porcelain", "--untracked-files=all") == ""


def on_branch() -> bool:
    return git("rev-parse", "--abbrev-ref", "HEAD").strip() == BRANCH


def is_linked_worktree() -> bool:
    common = Path(git("rev-parse", "--git-common-dir").strip())
    gitdir = Path(git("rev-parse", "--git-dir").strip())
    return common.resolve() != gitdir.resolve()


def pushed() -> bool:
    head = git("rev-parse", "HEAD").strip()
    return bool(git("branch", "-r", "--contains", head, check=False).strip())


def cmd_assert_branch(args) -> int:
    ok = on_branch() and is_linked_worktree()
    print(
        "BRANCH: %s (on %s: %s, linked worktree: %s, path %s)"
        % ("PASS" if ok else "FAIL", BRANCH, on_branch(), is_linked_worktree(), ROOT)
    )
    return 0 if ok else 1


def current_snapshot(require_o1=True):
    """The snapshot whose recorded digest equals HEAD's relevant digest (g0 first)."""
    head = oracle.relevant_digest(git("rev-parse", "HEAD").strip())
    cands = (
        sorted(
            (p for p in oracle.SNAPSHOTS.iterdir() if (p / "meta.json").exists()),
            key=lambda p: (p.name != "g0", p.name),
        )
        if oracle.SNAPSHOTS.exists()
        else []
    )
    for d in cands:
        meta = oracle.load_json(d / "meta.json")
        if meta.get("digest") == head and not meta.get("dirty") and (not require_o1 or (d / "O1.json").exists()):
            if not oracle.verify_snapshot(d.name, 1):
                return d
    return None


# ----------------------------------------------------------------------------- T1-T7


def pyproject() -> dict:
    try:
        return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def poe_tasks() -> dict:
    return pyproject().get("tool", {}).get("poe", {}).get("tasks", {})


def task_text(task) -> str:
    return json.dumps(task, sort_keys=True)


def t1():
    files = git("ls-files").split("\n")
    bad = sorted(f for f in files if f.rsplit("/", 1)[-1] in FORBIDDEN_CONFIGS)
    for name, task in poe_tasks().items():
        t = task_text(task)
        if re.search(r"\bruff (check|format)\b", t) and "--config pyproject.toml" not in t:
            bad.append("poe task %s runs ruff without --config pyproject.toml" % name)
        if "basedpyright" in t and "-p pyproject.toml" not in t:
            bad.append("poe task %s runs basedpyright without -p pyproject.toml" % name)
    return not bad, "; ".join(bad[:6]) or "one config home"


def in_scope_py() -> set:
    inv = oracle.load_json(oracle.INVENTORY)
    archival = set(inv["archival"])
    return {f for f in git("ls-files", "*.py").split() if f not in archival}


def t2():
    inv = oracle.load_json(oracle.INVENTORY)
    must = {f for f in inv["in_scope"] if (ROOT / f).exists()}
    allowed = in_scope_py()
    r = run(["uv", "run", "--frozen", "ruff", "check", "--config", "pyproject.toml", "--show-files"])
    if r.returncode != 0 and "Failed to spawn" in r.stderr:
        return False, "ruff not installed"
    shown = {
        Path(line.strip()).resolve().relative_to(ROOT.resolve()).as_posix()
        for line in r.stdout.splitlines()
        if line.strip().endswith(".py")
    }
    missing, extra = must - shown, shown - allowed
    msg = []
    if missing:
        msg.append("ruff skips %d in-scope files (e.g. %s)" % (len(missing), sorted(missing)[0]))
    if extra:
        msg.append("ruff analyses %d non-scope files" % len(extra))
    if pyproject().get("tool", {}).get("basedpyright") is not None:
        r = run(["uv", "run", "--frozen", "basedpyright", "-p", "pyproject.toml", "--outputjson"])
        try:
            n = json.loads(r.stdout)["summary"]["filesAnalyzed"]
            if n < len(must):
                msg.append("basedpyright analysed %d < %d in-scope files" % (n, len(must)))
        except (ValueError, KeyError):
            msg.append("basedpyright --outputjson unreadable")
    return not msg, "; ".join(msg) or "scope equals inventory"


_SUPP = re.compile(
    r"#\s*(noqa(?::\s*[A-Z0-9, ]+)?|type:\s*ignore(?:\[[^\]]*\])?|"
    r"pyright:\s*ignore(?:\[[^\]]*\])?|ruff:\s*noqa[^\n]*|pyright:\s*[a-zA-Z]+[^\n]*|"
    r"fmt:\s*(?:off|skip))",
    re.I,
)


def suppressions() -> list:
    """(file, line, form, reason) for every suppression comment in in-scope code."""
    out = []
    for f in sorted(in_scope_py()):
        try:
            lines = (ROOT / f).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines, 1):
            if "#" not in line:
                continue
            for m in _SUPP.finditer(line):
                rest = line[m.end() :]
                reason = rest.split("#", 1)[1].strip() if "#" in rest else ""
                out.append((f, i, m.group(1).strip(), reason))
    return out


def blanket(form: str) -> bool:
    f = form.lower().replace(" ", "")
    return (
        f == "noqa"
        or f.startswith("ruff:noqa")
        or f == "type:ignore"
        or (f.startswith("pyright:") and not f.startswith(("pyright:ignore[", "pyright:strict")))
    )


def t3(goal: int):
    bad = []
    for f, i, form, reason in suppressions():
        low = form.lower().replace(" ", "")
        is_type = low.startswith(("type:", "pyright:"))
        if is_type and goal < 4:
            continue
        if blanket(form):
            bad.append("%s:%d blanket %r" % (f, i, form))
        elif not reason and not low.startswith("pyright:strict"):
            bad.append("%s:%d %r without a reason" % (f, i, form))
    return not bad, (
        "%d violations, e.g. %s" % (len(bad), bad[0])
    ) if bad else "every suppression has a rule and a reason"


def t4():
    sup = [s for s in suppressions() if not s[2].lower().startswith(("fmt:", "pyright:strict"))]
    loc = sum(len((ROOT / f).read_bytes().splitlines()) for f in in_scope_py() if (ROOT / f).exists())
    budget = loc // 400
    report_ok = (HERE / "SUPPRESSIONS.md").exists() and (HERE / "SUPPRESSIONS.md").read_text(
        encoding="utf-8"
    ) == render_suppressions()
    ok = len(sup) <= budget and report_ok
    return ok, "%d suppressions / budget %d (%d LOC); SUPPRESSIONS.md %s" % (
        len(sup),
        budget,
        loc,
        "current" if report_ok else "STALE or missing",
    )


ALLOWED_PER_FILE = {"tests/**": {"S101", "PLR2004"}, "scripts/**": {"T20", "T201"}}


def t5():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8") if (ROOT / "pyproject.toml").exists() else ""
    pfi = pyproject().get("tool", {}).get("ruff", {}).get("lint", {}).get("per-file-ignores", {})
    bad = []
    for pat, codes in pfi.items():
        allowed = ALLOWED_PER_FILE.get(pat)
        if allowed is None or not set(codes) <= allowed:
            bad.append("%s = %s not a section-16 structural pattern" % (pat, codes))
        line = next((ln for ln in text.splitlines() if ln.strip().startswith('"%s"' % pat)), "")
        if "#" not in line:
            bad.append("%s has no comment" % pat)
    return not bad, "; ".join(bad) or "%d structural per-file ignores, all commented" % len(pfi)


def t6():
    tasks = poe_tasks()
    bad = []
    for name in GATE_TASKS:
        if name not in tasks:
            bad.append("task %s missing" % name)
            continue
        t = task_text(tasks[name])
        bad += ["task %s contains %r" % (name, f) for f in GATE_FORBIDDEN if f in t]
        r = run(["uv", "run", "--frozen", "poe", "-d", name])
        if r.returncode != 0:
            bad.append("poe -d %s failed" % name)
    return not bad, "; ".join(bad[:6]) or "gate tasks run the tools"


def t7():
    g0 = oracle.SNAPSHOTS / "g0" / "O1.json"
    cur = current_snapshot()
    if not g0.exists() or cur is None:
        return False, "no g0 O1 or no suite record current for HEAD"
    a, b = oracle.load_json(g0), oracle.load_json(cur / "O1.json")
    ran = lambda s: min(oracle.o1_ran(r) for r in s["runs"])  # noqa: E731
    skp = lambda s: max(r["counts"].get("skipped", 0) for r in s["runs"])  # noqa: E731
    ok = ran(b) >= ran(a) and skp(b) <= skp(a)
    return ok, "ran %d (g0 %d), skipped %d (g0 %d) [%s]" % (ran(b), ran(a), skp(b), skp(a), cur.name)


def tamper(goal: str):
    n = goal_num(goal)
    results = {}
    for t, fn in (("T1", t1), ("T2", t2), ("T3", lambda: t3(n)), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7)):
        try:
            ok, msg = fn()
        except Exception as e:  # a crashing rule is a failing rule, never a passing one
            ok, msg = False, "crashed: %s: %s" % (type(e).__name__, e)
        active = n >= T_ACTIVE_FROM[t]
        results[t] = (active, ok, msg)
    return results


def render_suppressions() -> str:
    rows = [
        "# Suppressions in in-scope code (generated by certify.py suppressions --write)",
        "",
        "| File | Line | Suppression | Reason |",
        "|---|---|---|---|",
    ]
    rows += [
        "| %s | %d | `%s` | %s |" % (f, i, form, reason.replace("|", "\\|")) for f, i, form, reason in suppressions()
    ]
    return "\n".join(rows) + "\n"


def cmd_suppressions(args) -> int:
    text = render_suppressions()
    p = HERE / "SUPPRESSIONS.md"
    if args.write:
        p.write_text(text, encoding="utf-8", newline="\n")
        print("wrote %s (%d rows)" % (p.relative_to(ROOT), text.count("\n") - 4))
        return 0
    ok = p.exists() and p.read_text(encoding="utf-8") == text
    print("SUPPRESSIONS.md: %s" % ("current" if ok else "STALE"))
    return 0 if ok else 1


# ----------------------------------------------------------------------------- drills (section 13)

MISFORMATTED = "x=1;y = [1,\n  2]\ndef f( a ):\n  return a\n"


def _write(tree: Path, rel: str, text: str, append=False):
    p = tree / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if append:
        with p.open("a", encoding="utf-8") as fh:
            fh.write(text)
    else:
        p.write_text(text, encoding="utf-8")


def _first_core_module(tree: Path) -> str:
    inv = oracle.load_json(oracle.INVENTORY)
    return next(f for f in inv["in_scope"] if f.startswith("core/") and not f.endswith("__init__.py"))


def _poe(task):
    return ["uv", "run", "--frozen", "poe", task]


def _poe_present(task):
    return ["uv", "run", "--frozen", "poe", "-d", task]


def _fault_d05(t):
    _write(t, "ruff.toml", 'extend-exclude = ["core"]\n')
    _write(t, "core/_drill_fmt.py", MISFORMATTED)


def _fault_d07(t):
    rel = _first_core_module(t)
    p = t / rel
    p.write_text("# pyright: basic\n" + p.read_text(encoding="utf-8"), encoding="utf-8")


def _fault_d08(t):
    p = t / "pyproject.toml"
    s = p.read_text(encoding="utf-8")
    p.write_text(s.replace("dependencies = [", 'dependencies = [\n    "six>=1.16",', 1), encoding="utf-8")


def _fault_d09(t):
    _write(t, "requirements.txt", "six==1.16.0  # hand edit\n", append=True)


def _fault_d14(t):
    base = oracle.load_json(oracle.SNAPSHOTS / "g0" / "O5.json")
    oracle._drop_function(t, oracle.load_json(oracle.INVENTORY), base)


def _gate_d14(t):
    """O5 on the mutated module, compared to g0 (non-zero = DIFF = the gate bit)."""
    base = oracle.load_json(oracle.SNAPSHOTS / "g0" / "O5.json")
    inv = oracle.load_json(oracle.INVENTORY)
    graph = oracle.RepoGraph(t, [f for f in oracle.tracked_files(t) if f.endswith(".py")])
    raw = Path(tempfile.mkdtemp(prefix="drill-d14-"))
    mods = {m for m in base["modules"] if m.startswith("core.")}
    _o3, o5 = oracle.probe_modules(t, inv, graph, raw, mods, python=oracle.venv_python(ROOT))
    oracle._rmtree(raw)
    return 1 if oracle.compare_o5(base, o5, partial=True) else 0


def _fault_d15(t):
    """Rewrite the `gate` Poe task (key form or table form) into one that swallows failure."""
    p = t / "pyproject.toml"
    lines = p.read_text(encoding="utf-8").splitlines()
    out, i, section = [], 0, ""
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("["):
            section = ln.strip()
        if section == "[tool.poe.tasks.gate]" and ln.startswith("["):
            out += [ln, 'shell = "true || true"']
            i += 1
            while i < len(lines) and not lines[i].startswith("["):
                i += 1
            continue
        if section == "[tool.poe.tasks]" and re.match(r"\s*gate\s*=", ln):
            out.append('gate = { shell = "true || true" }')
            i += 1
            while i < len(lines) and not re.match(r'\s*[\w"-]+\s*=|\[', lines[i]):
                i += 1
            continue
        out.append(ln)
        i += 1
    p.write_text("\n".join(out) + "\n", encoding="utf-8")


def _hooks_present(t):
    hp = git("config", "--get", "core.hooksPath", cwd=t, check=False).strip()
    return ["git", "rev-parse", "--verify", "HEAD"] if hp and (t / hp / "pre-commit").exists() else ["false"]


def _gate_d13(t):
    _write(t, "core/_drill_fmt.py", MISFORMATTED)
    run(["git", "add", "core/_drill_fmt.py"], cwd=t)
    return run(["git", "commit", "-q", "-m", "chore: drill"], cwd=t).returncode


DRILLS = {
    # id: (description, fault(tree), gate argv | callable(tree)->rc, presence argv | callable)
    "D01": (
        "mis-formatted in-scope file",
        lambda t: _write(t, "core/_drill_fmt.py", MISFORMATTED),
        _poe("fmt-check"),
        _poe_present("fmt-check"),
    ),
    "D02": (
        "unused import F401",
        lambda t: _write(t, "core/_drill_f401.py", "import os\n"),
        _poe("lint-check"),
        _poe_present("lint-check"),
    ),
    "D03": (
        "bare except",
        lambda t: _write(t, "core/_drill_bare.py", "try:\n    pass\nexcept:\n    pass\n"),
        _poe("lint-check"),
        _poe_present("lint-check"),
    ),
    "D04": (
        "type error under core/",
        lambda t: _write(t, "core/_drill_types.py", 'x: int = "s"\n'),
        _poe("types"),
        _poe_present("types"),
    ),
    "D05": ("ruff.toml excluding core/ + mis-formatted core file", _fault_d05, _poe("gate"), _poe_present("gate")),
    "D06": (
        "file-level ruff: noqa",
        lambda t: _write(t, "core/_drill_noqa.py", "# ruff: noqa\nimport os\n"),
        _poe("gate"),
        _poe_present("gate"),
    ),
    "D07": ("pyright: basic header on a core file", _fault_d07, _poe("gate"), _poe_present("gate")),
    "D08": ("dependency added without relock", _fault_d08, _poe("lock-check"), _poe_present("lock-check")),
    "D09": ("hand edit to a generated requirements file", _fault_d09, _poe("lock-check"), _poe_present("lock-check")),
    "D10": (
        "tag-pinned action",
        lambda t: _write(
            t,
            ".github/workflows/_drill.yml",
            "on: push\npermissions: {}\njobs:\n  d:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n",
        ),
        _poe("ci-lint"),
        _poe_present("ci-lint"),
    ),
    "D11": (
        "permissions: write-all",
        lambda t: _write(
            t,
            ".github/workflows/_drill.yml",
            "on: push\npermissions: write-all\njobs:\n  d:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hi\n",
        ),
        _poe("ci-lint"),
        _poe_present("ci-lint"),
    ),
    "D12": (
        "failing test in a new test file",
        lambda t: _write(t, "tests/test__drill_fail.py", "def test_drill():\n    assert False\n"),
        _poe("test-fast"),
        _poe_present("test-fast"),
    ),
    "D13": ("mis-formatted staged file + git commit", lambda t: None, _gate_d13, _hooks_present),
    "D14": ("public function removed from a core module", _fault_d14, _gate_d14, _poe_present("oracle")),
    "D15": (
        "poe gate task edited to add || true",
        _fault_d15,
        ["{python}", "tooling-upgrade/certify.py", "{goal}", "--tamper-only"],
        _poe_present("gate"),
    ),
}


@contextlib.contextmanager
def drill_tree():
    base = Path(tempfile.mkdtemp(prefix="aurora-drill-"))
    t = base / "aurora-drill"
    git("worktree", "add", "--detach", str(t), "HEAD")
    try:
        yield t
    finally:
        oracle._rmtree(base)
        git("worktree", "prune", check=False)


def _exec(spec, t, goal):
    if isinstance(spec, int):  # a presence probe that already answered with an exit code
        return spec
    if callable(spec):
        return spec(t)
    argv = [a.replace("{python}", sys.executable).replace("{goal}", goal) for a in spec]
    env = oracle.oracle_env({"UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"), "UV_NO_SYNC": "1"})
    try:
        return run(argv, cwd=t, env=env, timeout=3600).returncode
    except FileNotFoundError:
        return 127


def run_drill(did: str, goal: str) -> str:
    desc, fault, gate, presence = DRILLS[did]
    with drill_tree() as t:
        pres = presence(t) if callable(presence) else presence
        if _exec(pres, t, goal) != 0:
            return "MISSED (gate absent)"
        clean_rc = _exec(gate, t, goal)
        if clean_rc != 0:
            return "MISSED (gate red before the fault: rc=%s)" % clean_rc
        fault(t)
        rc = _exec(gate, t, goal)
        return "BIT" if rc != 0 else "MISSED"


def run_drills(goal: str, ids=None):
    out = {}
    for did in ids or sorted(DRILLS):
        try:
            out[did] = run_drill(did, goal)
        except Exception as e:  # a drill that cannot run proves nothing about the gate
            out[did] = "MISSED (drill error: %s: %s)" % (type(e).__name__, str(e)[:120])
        print("%s %s  -- %s" % (did, out[did], DRILLS[did][0]), flush=True)
    return out


def cmd_drills(args) -> int:
    res = run_drills(args.goal)
    missed = sum(1 for v in res.values() if v.startswith("MISSED"))
    bit = sum(1 for v in res.values() if v == "BIT")
    print("DRILLS: %d/%d BIT" % (bit, len(res)))
    print("DRILLS-MISSED %d/%d" % (missed, len(res)))
    if args.expect_missed:
        return 0 if missed == len(res) else 1
    return 0 if bit == len(res) else 1


# ----------------------------------------------------------------------------- fresh clone


def cmd_fresh_clone(args) -> int:
    base = Path(tempfile.mkdtemp(prefix="aurora-clone-"))
    clone = base / "aurora-clone"
    try:
        steps = [
            ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(clone)],
            ["git", "-C", str(clone), "checkout", "--quiet", git("rev-parse", "HEAD").strip()],
            ["uv", "sync", "--locked"],
        ]
        if args.gate:
            steps.append(["uv", "run", "poe", "gate"])
        for cmd in steps:
            r = run(cmd, cwd=clone if cmd[0] == "uv" else base, env=oracle.oracle_env(), timeout=7200)
            tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:])
            print("$ %s\n%s\n[exit %d]" % (" ".join(cmd), tail, r.returncode))
            if r.returncode != 0:
                print("FRESH-CLONE: FAIL")
                return 1
        print("FRESH-CLONE: PASS")
        return 0
    finally:
        oracle._rmtree(base)


# ----------------------------------------------------------------------------- goal-specific asserts


def _report(name, problems) -> int:
    for p in problems[:30]:
        print("  ", p)
    print("%s: %s" % (name, "PASS" if not problems else "FAIL (%d)" % len(problems)))
    return 1 if problems else 0


def commits_since_base():
    out = git("log", "--reverse", "--format=%H%x1f%s%x1f%b%x1e", "%s..HEAD" % oracle.g0_base())
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if rec:
            sha, subject, body = rec.split("\x1f", 2)
            yield sha, subject, body


def cmd_assert_mechanical_commits(args) -> int:
    """Every commit with a `Replay:` line reproduces exactly from its parent (class B/C), and
    every class-B (`style:`) commit is AST-equal to its parent (O2)."""
    import shlex

    problems, n = [], 0
    for sha, subject, body in commits_since_base():
        m = re.search(r"(?m)^Replay:\s*(.+)$", body)
        if subject.startswith("style:"):
            bad = [p for p, ok, _ in oracle.ast_equal(sha + "^", sha) if not ok]
            if bad:
                problems.append("%s %s: AST differs in %s" % (sha[:9], subject, ", ".join(bad[:3])))
            if not m:
                problems.append("%s %s: class-B commit without Replay:" % (sha[:9], subject))
        if not m:
            continue
        n += 1
        base = Path(tempfile.mkdtemp(prefix="aurora-replay-"))
        t = base / "aurora-replay"
        try:
            git("worktree", "add", "--detach", str(t), sha + "^")
            env = oracle.oracle_env({"UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"), "UV_NO_SYNC": "1"})
            run(shlex.split(m.group(1)), cwd=t, env=env, timeout=3600)
            run(["git", "add", "-A"], cwd=t)
            if run(["git", "diff", "--cached", "--quiet", sha], cwd=t).returncode != 0:
                problems.append("%s %s: replay differs from the commit" % (sha[:9], subject))
        finally:
            oracle._rmtree(base)
            git("worktree", "prune", check=False)
    print("replayed %d mechanical commit(s)" % n)
    return _report("MECHANICAL COMMITS", problems)


def cmd_assert_blame_ignore_revs(args) -> int:
    p = ROOT / ".git-blame-ignore-revs"
    if not p.exists():
        return _report("BLAME-IGNORE-REVS", [".git-blame-ignore-revs missing"])
    problems = []
    shas = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    for sha in shas:
        subj = git("log", "-1", "--format=%s", sha, check=False).strip()
        if not subj.startswith("style:"):
            problems.append("%s is not a style: commit (%r)" % (sha[:9], subj))
    if not shas:
        problems.append("no revisions listed")
    return _report("BLAME-IGNORE-REVS", problems)


_VERSION_SURFACES = (".github/workflows", "scripts/githooks", ".claude/settings.json", ".mcp.json")


def cmd_assert_python_agrees(args) -> int:
    pv = ROOT / ".python-version"
    if not pv.exists():
        return _report("PYTHON AGREES", [".python-version missing"])
    pin = pv.read_text(encoding="utf-8").strip()
    pin_mm = ".".join(pin.split(".")[:2])
    problems = []
    pat = re.compile(r"(?:python-version:\s*[\"']?|(?:uv run|uvx|py)\s+(?:-p|--python)\s+|py -)(3\.\d+)")
    for surf in _VERSION_SURFACES:
        root = ROOT / surf
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for m in pat.finditer(text):
                if m.group(1) != pin_mm:
                    problems.append(
                        "%s says %s, .python-version says %s" % (f.relative_to(ROOT).as_posix(), m.group(1), pin_mm)
                    )
    rp = pyproject().get("project", {}).get("requires-python", "")
    floor = re.search(r">=\s*(3\.\d+)", rp)
    if not floor or tuple(map(int, floor.group(1).split("."))) > tuple(map(int, pin_mm.split("."))):
        problems.append("requires-python %r is not a floor at or below the pin %s" % (rp, pin_mm))
    return _report("PYTHON AGREES (pin %s)" % pin_mm, problems)


def cmd_assert_no_bare_py(args) -> int:
    """No executable surface launches Python with a bare `py ` (G1.P5); the documented Windows
    fallback inside the pyrun shim's chain is the one allowed mention."""
    problems = []
    for f in sorted((ROOT / "scripts" / "githooks").glob("*")):
        if f.suffix or not f.is_file():
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"\s*py\s", ln):
                problems.append("%s:%d %s" % (f.relative_to(ROOT).as_posix(), i, ln.strip()[:80]))
    for rel in (".mcp.json", ".claude/settings.json"):
        p = ROOT / rel
        if not p.exists():
            continue
        for m in re.finditer(r'"command"\s*:\s*"([^"]*)"', p.read_text(encoding="utf-8")):
            if re.search(r"(^|&&\s*|;\s*)py\s", m.group(1)) or m.group(1) == "py":
                problems.append("%s command %r" % (rel, m.group(1)[:80]))
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for i, ln in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(run:\s*|^\s*)py\s", ln):
                problems.append("%s:%d %s" % (wf.relative_to(ROOT).as_posix(), i, ln.strip()[:80]))
    return _report("NO BARE PY", problems)


DEV_GROUP = (
    "ruff",
    "basedpyright",
    "ty",
    "pytest",
    "pytest-cov",
    "pytest-xdist",
    "pytest-randomly",
    "poethepoet",
    "prek",
    "deptry",
)  # plan G1.P1, exactly


def _req_name(spec: str) -> str:
    return re.split(r"[\s<>=!~;\[@]", spec.strip(), maxsplit=1)[0].lower().replace("_", "-")


def dev_group_problems(pp: dict) -> list:
    groups = pp.get("dependency-groups", {})
    dev = {_req_name(s) for s in groups.get("dev", []) if isinstance(s, str)}
    problems = ["dev lacks %s" % n for n in DEV_GROUP if n not in dev]
    problems += ["dev has %s (not in the plan's list)" % n for n in sorted(dev - set(DEV_GROUP))]
    runtime = {_req_name(s) for s in pp.get("project", {}).get("dependencies", [])}
    problems += ["[project].dependencies still has tool %s" % n for n in sorted(runtime & set(DEV_GROUP))]
    problems += [
        "pre-commit is still declared (replaced by prek)"
        for g in [runtime] + [{_req_name(s) for s in v if isinstance(s, str)} for v in groups.values()]
        if "pre-commit" in g
    ]
    for g in ("ml", "browser"):
        if g not in groups:
            problems.append("optional group %s missing" % g)
    return problems


def cmd_assert_dev_group(args) -> int:
    return _report("DEV GROUP", dev_group_problems(pyproject()))


def uv_settings_problems(pp: dict) -> list:
    uv = pp.get("tool", {}).get("uv", {})
    problems = []
    if uv.get("package") is not False:
        problems.append("tool.uv.package is not false")
    m = re.fullmatch(r">=\s*0\.(\d+)(\.\d+)?", str(uv.get("required-version", "")))
    if not m or int(m.group(1)) < 12:
        problems.append("tool.uv.required-version %r is not >=0.12 (the G0 uv minor)" % uv.get("required-version"))
    if uv.get("exclude-newer") != "7 days":
        problems.append("tool.uv.exclude-newer %r != '7 days'" % uv.get("exclude-newer"))
    if uv.get("default-groups") != ["dev"]:
        problems.append("tool.uv.default-groups %r != ['dev']" % uv.get("default-groups"))
    return problems


def cmd_assert_uv_settings(args) -> int:
    return _report("UV SETTINGS", uv_settings_problems(pyproject()))


def gate_problems(tasks: dict, members: list) -> list:
    """`gate` is a sequence over gate tasks in plan order (G1.P6) that includes at least
    `members`; tasks only ever join it."""
    gate = tasks.get("gate")
    seq = gate.get("sequence") if isinstance(gate, dict) else gate if isinstance(gate, list) else None
    if not isinstance(seq, list):
        return ["gate is not a sequence task"]
    names = [s if isinstance(s, str) else s.get("ref", "") if isinstance(s, dict) else "" for s in seq]
    problems = ["gate step %r is not a plan gate task" % n for n in names if n not in GATE_TASKS]
    order = [n for n in GATE_TASKS if n in names]
    if names != order:
        problems.append("gate order %s differs from plan order %s" % (names, order))
    problems += ["gate lacks %s" % m for m in members if m not in names]
    if isinstance(gate, dict) and gate.get("ignore_fail"):
        problems.append("gate sets ignore_fail")
    return problems


def cmd_assert_gate(args) -> int:
    return _report("GATE MEMBERS", gate_problems(poe_tasks(), args.members))


_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s'\"#]+)")


def sha_pin_problems(root: Path) -> list:
    """Every workflow `uses:` names a 40-hex commit (local ./ actions and docker:// excepted)."""
    problems = []
    wf_dir = root / ".github" / "workflows"
    for wf in sorted(wf_dir.glob("*.y*ml")) if wf_dir.exists() else []:
        for i, ln in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            m = _USES.match(ln)
            if not m or m.group(1).startswith(("./", "docker://")):
                continue
            ref = m.group(1).rpartition("@")[2] if "@" in m.group(1) else ""
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                problems.append(
                    "%s:%d %s is not pinned to a commit SHA" % (wf.relative_to(root).as_posix(), i, m.group(1))
                )
    return problems


def cmd_assert_sha_pins(args) -> int:
    return _report("SHA PINS", sha_pin_problems(ROOT))


def cmd_assert_ratchet(args) -> int:
    """Stretch rule families (plan G3: D, ANN, ARG, FBT, TRY, PL) may never rise above the
    counts committed in tooling-upgrade/ratchet.json."""
    p = HERE / "ratchet.json"
    if not p.exists():
        return _report("RATCHET", ["tooling-upgrade/ratchet.json missing"])
    limits = oracle.load_json(p)
    r = run(
        [
            "uv",
            "run",
            "--frozen",
            "ruff",
            "check",
            "--config",
            "pyproject.toml",
            "--exit-zero",
            "--select",
            ",".join(sorted(limits)),
            "--output-format",
            "json",
        ]
    )
    try:
        found = json.loads(r.stdout or "[]")
    except ValueError:
        return _report("RATCHET", ["ruff --output-format json unreadable"])
    counts = dict.fromkeys(limits, 0)
    for d in found:
        code = d.get("code") or ""
        fam = max((f for f in limits if code.startswith(f)), key=len, default=None)
        if fam:
            counts[fam] += 1
    problems = ["%s: %d > ratchet %d" % (f, counts[f], limits[f]) for f in sorted(limits) if counts[f] > limits[f]]
    print("counts: %s" % counts)
    return _report("RATCHET", problems)


def cmd_assert_latent_regressions(args) -> int:
    """Every INTENDED_CHANGES entry with `fix_commit` + `regression_test` (G4.P2): the test fails
    on the fix's parent and passes on HEAD."""
    problems, n = [], 0
    for e in oracle.load_intended():
        if not (e.get("fix_commit") and e.get("regression_test")):
            continue
        n += 1
        for ref, want_fail in ((e["fix_commit"] + "^", True), ("HEAD", False)):
            base = Path(tempfile.mkdtemp(prefix="aurora-latent-"))
            t = base / "aurora-latent"
            try:
                git("worktree", "add", "--detach", str(t), ref)
                if want_fail:  # the regression test lands with/after the fix: bring HEAD's copy
                    src = ROOT / e["regression_test"].split("::")[0]
                    dst = t / e["regression_test"].split("::")[0]
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(src.read_bytes())
                env = oracle.oracle_env({"UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"), "UV_NO_SYNC": "1"})
                r = run(
                    ["uv", "run", "--frozen", "pytest", "-q", "-p", "no:cacheprovider", e["regression_test"]],
                    cwd=t,
                    env=env,
                    timeout=1800,
                )
                if (r.returncode != 0) != want_fail:
                    problems.append(
                        "%s: %s %s on %s" % (e["id"], e["regression_test"], "passed" if want_fail else "failed", ref)
                    )
            finally:
                oracle._rmtree(base)
                git("worktree", "prune", check=False)
    print("latent-bug entries checked: %d" % n)
    return _report("LATENT REGRESSIONS", problems)


def cmd_assert_ledger_entry(args) -> int:
    text = (HERE / "LEDGER.md").read_text(encoding="utf-8")
    rows = [ln for ln in text.splitlines() if ln.startswith("| %s" % args.phase)]
    ok = any(re.search(r"\|\s*(DONE|CERTIFIED|NO-GO|SKIPPED)\s*\|", r) for r in rows)
    return _report("LEDGER %s" % args.phase, [] if ok else ["no DONE/CERTIFIED/NO-GO/SKIPPED row"])


def cmd_assert_docs_uv(args) -> int:
    problems = []
    for doc in ("README.md", "CONTRIBUTING.md", "AGENTS.md", "docs/DEPLOY.md"):
        p = ROOT / doc
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        for needle in ("uv sync", "uv run"):
            if needle not in t:
                problems.append("%s never mentions `%s`" % (doc, needle))
    t = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8") if (ROOT / "CONTRIBUTING.md").exists() else ""
    for needle in ("uv run poe gate", "uv run poe test", "--no-verify"):
        if needle not in t:
            problems.append("CONTRIBUTING.md lacks `%s`" % needle)
    return _report("DOCS UV-PRIMARY", problems)


def cmd_assert_ci_replay(args) -> int:
    print(
        "NOT IMPLEMENTED: the local replay of every CI job's run steps is built in G5.P3 "
        "(it needs a workflow parser); until then this check cannot pass."
    )
    return 3


# ----------------------------------------------------------------------------- certificate


def prior_goal_certified(n: int) -> bool:
    text = (HERE / "LEDGER.md").read_text(encoding="utf-8") if (HERE / "LEDGER.md").exists() else ""
    return re.search(r"(?m)^\|\s*G%d\s*\|\s*(CERTIFIED|NO-GO|SKIPPED)\s*\|" % (n - 1), text) is not None


def certify(goal: str, phase=None, drills=False, tamper_only=False) -> int:
    n = goal_num(goal)
    if tamper_only:
        res = tamper(goal)
        failed = [t for t, (active, ok, _m) in res.items() if active and not ok]
        for t, (active, ok, msg) in res.items():
            print("%s %s%s -- %s" % (t, "PASS" if ok else "FAIL", "" if active else " (not yet active)", msg))
        return 1 if failed else 0

    data = load_checks(goal)
    checks = [c for c in data.get("check", []) if phase is None or c["phase"] == phase]
    passed, first_fail = 0, None
    if n > 0 and not prior_goal_certified(n):
        # Goals run in order: a later goal's checks, tamper rules and oracle comparison are not
        # executed before its predecessor is certified (they would only measure work that does
        # not exist yet). Drills still run -- that is the G0.P5 self-test `certify.py G7 --drills`.
        print(
            "CHECKS skipped: G%d is not CERTIFIED in tooling-upgrade/LEDGER.md, so %s has not "
            "started; only the drills run." % (n - 1, goal)
        )
        if drills:
            res = run_drills(goal)
            missed = sum(1 for v in res.values() if v.startswith("MISSED"))
            print("DRILLS: %d/%d BIT" % (len(res) - missed, len(res)))
            print("DRILLS-MISSED %d/%d" % (missed, len(res)))
        print("RESULT: %s NOT CERTIFIED: G%d not certified; %s not started" % (goal, n - 1, goal))
        return 1
    for c in checks:
        ok, why, out = run_check(c)
        passed += ok
        print("%s %s -- %s" % ("PASS" if ok else "FAIL", c["id"], why), flush=True)
        if not ok:
            print("    " + "\n    ".join(out.strip().splitlines()[-6:]))
            first_fail = first_fail or "check %s (%s)" % (c["id"], why)

    if phase:
        # Phase self-check (plan 9: "certify.py G<n> --phase <id>"): that phase's pre-registered
        # checks only. T1-T7, the drills and the oracle belong to the goal-end certificate.
        print(
            "PHASE %s: %d/%d PASS (worktree clean: %s, branch ok: %s)"
            % (phase, passed, len(checks), "yes" if worktree_clean() else "no", "yes" if on_branch() else "no")
        )
        return 0 if checks and passed == len(checks) and worktree_clean() and on_branch() else 1
    res = tamper(goal)
    t_fail = [t for t, (active, ok, _m) in res.items() if active and not ok]
    for t, (active, ok, msg) in res.items():
        print(
            "%s %s%s -- %s"
            % (
                t,
                "PASS" if ok else "FAIL",
                "" if active else " (not yet active: binds from G%d)" % T_ACTIVE_FROM[t],
                msg,
            )
        )
    pending = [t for t, (active, _ok, _m) in res.items() if not active]

    required = data.get("required_drills", [])
    bit_count, drill_res = 0, {}
    if drills:
        drill_res = run_drills(goal)
        missed = sum(1 for v in drill_res.values() if v.startswith("MISSED"))
        print("DRILLS-MISSED %d/%d" % (missed, len(drill_res)))
    elif required:
        drill_res = run_drills(goal, required)
    bit_count = sum(1 for d in required if drill_res.get(d) == "BIT")

    cur = current_snapshot()
    if cur is not None and (oracle.SNAPSHOTS / "g0" / "meta.json").exists():
        lines, oracle_ok = oracle.compare_dirs(oracle.SNAPSHOTS / "g0", cur)
        for ln in lines:
            print(ln)
        k = int(lines[-1].split()[1].split("/")[0])
    else:
        oracle_ok, k = False, 0
        print("ORACLE: no snapshot is current for HEAD (run `oracle.py snapshot head --runs 1`)")

    refusals = []
    if not worktree_clean():
        refusals.append("worktree dirty")
    if not on_branch():
        refusals.append("HEAD not on %s" % BRANCH)
    hist = checks_history_problems()
    if hist:
        refusals.append("checks files changed after registration: " + hist[0])
    if cur is None:
        refusals.append("no full-suite record current for HEAD")
    if pushed():
        refusals.append("HEAD is on a remote branch (pushed)")

    head = git("rev-parse", "HEAD").strip()
    print("=== CERTIFICATE %s%s ===" % (goal, (" " + phase) if phase else ""))
    print(
        "HEAD %s | branch %s | worktree clean: %s | pushed: %s"
        % (
            head[:12],
            git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "yes" if worktree_clean() else "no",
            "yes" if pushed() else "no",
        )
    )
    print("CHECKS %d/%d PASS" % (passed, len(checks)))
    print(
        "TAMPER T1-T7 %s%s"
        % (
            "PASS" if not t_fail else "FAIL (%s)" % ", ".join(t_fail),
            " (binding: %s; not yet active: %s)" % (", ".join(t for t in res if t not in pending), ", ".join(pending))
            if pending
            else "",
        )
    )
    print("DRILLS %d/%d BIT" % (bit_count, len(required)))
    print("ORACLE %d/10 EQUAL" % k)
    failure = (
        first_fail
        or (("tamper " + t_fail[0]) if t_fail else None)
        or ("drills %d/%d BIT" % (bit_count, len(required)) if bit_count < len(required) else None)
        or (None if oracle_ok else "oracle %d/10 EQUAL" % k)
        or (refusals[0] if refusals else None)
    )
    print("RESULT: %s %s" % (goal, "CERTIFIED" if failure is None else "NOT CERTIFIED: " + failure))
    print("=== END CERTIFICATE ===")
    return 0 if failure is None else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and re.fullmatch(r"G[0-7]", argv[0]):
        p = argparse.ArgumentParser(prog="certify.py G<n>")
        p.add_argument("goal")
        p.add_argument("--phase")
        p.add_argument("--drills", action="store_true", help="also run all 15 bite drills")
        p.add_argument("--tamper-only", action="store_true", help="T1-T7 only (the D15 gate)")
        a = p.parse_args(argv)
        return certify(a.goal, a.phase, a.drills, a.tamper_only)
    p = argparse.ArgumentParser(prog="certify.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("assert-branch")
    sub.add_parser("assert-checks-files")
    s = sub.add_parser("suppressions")
    s.add_argument("--write", action="store_true")
    s = sub.add_parser("fresh-clone")
    s.add_argument("--gate", action="store_true")
    s = sub.add_parser("drills")
    s.add_argument("--goal", default="G7")
    s.add_argument("--expect-missed", action="store_true")
    sub.add_parser("assert-mechanical-commits", help="Replay: commits reproduce; style: commits AST-equal")
    sub.add_parser("assert-blame-ignore-revs", help="every listed SHA is a style: commit")
    sub.add_parser("assert-python-agrees", help=".python-version agrees with CI, hooks, settings")
    sub.add_parser("assert-no-bare-py", help="no executable surface launches a bare `py`")
    sub.add_parser("assert-dev-group", help="dev group is exactly the plan's tool list (G1.P1)")
    sub.add_parser("assert-sha-pins", help="every workflow uses: is pinned to a 40-hex SHA")
    sub.add_parser("assert-uv-settings", help="[tool.uv] carries the G1.P3 settings")
    s = sub.add_parser("assert-gate", help="poe gate: plan order, includes the given tasks")
    s.add_argument("members", nargs="*")
    s = sub.add_parser("assert-ratchet", help="stretch rule families never rise")
    s.add_argument("goal")
    sub.add_parser("assert-latent-regressions", help="latent-bug tests fail on parent, pass on HEAD")
    s = sub.add_parser("assert-ledger-entry", help="LEDGER.md has a closed row for a phase")
    s.add_argument("phase")
    sub.add_parser("assert-docs-uv", help="docs present uv as the primary path")
    sub.add_parser("assert-ci-replay", help="local replay of CI run steps (built in G5)")
    a = p.parse_args(argv)
    return {
        "assert-branch": cmd_assert_branch,
        "assert-checks-files": cmd_assert_checks_files,
        "suppressions": cmd_suppressions,
        "fresh-clone": cmd_fresh_clone,
        "drills": cmd_drills,
        "assert-mechanical-commits": cmd_assert_mechanical_commits,
        "assert-blame-ignore-revs": cmd_assert_blame_ignore_revs,
        "assert-python-agrees": cmd_assert_python_agrees,
        "assert-no-bare-py": cmd_assert_no_bare_py,
        "assert-ratchet": cmd_assert_ratchet,
        "assert-dev-group": cmd_assert_dev_group,
        "assert-uv-settings": cmd_assert_uv_settings,
        "assert-gate": cmd_assert_gate,
        "assert-sha-pins": cmd_assert_sha_pins,
        "assert-latent-regressions": cmd_assert_latent_regressions,
        "assert-ledger-entry": cmd_assert_ledger_entry,
        "assert-docs-uv": cmd_assert_docs_uv,
        "assert-ci-replay": cmd_assert_ci_replay,
    }[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
