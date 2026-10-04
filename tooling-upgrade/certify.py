#!/usr/bin/env python3
# pyright: strict
"""Goal certification for the 2026-10 Python tooling upgrade (plan sections 12-14). Stdlib only.

    certify.py G<n> [--phase G<n>.P<k>] [--drills]   run checks + T1-T7 (+ drills) and print
                                                      the certificate block
    certify.py G<n> --tamper-only                     T1-T7 only (the D15 gate)
    certify.py assert-branch                          HEAD is the migration branch, in a linked worktree
    certify.py assert-checks-files                    checks/G0..G7.toml tracked, parseable, append-only
    certify.py suppressions [--write]                 regenerate / verify SUPPRESSIONS.md (T4)
    certify.py fresh-clone [--gate]                   clone --no-hardlinks, uv sync --locked (, poe gate)
    certify.py drills [--expect-missed]               D01-D15 alone
    certify.py assert-suppressions                    T3 + T4 (the gate step that makes D07 bite)

The evaluator of a goal cannot run anything, so this script runs every pre-registered check
itself and prints one block. It refuses to print CERTIFIED when the worktree is dirty, HEAD is
off the branch, a checks entry was removed or changed after registration, or no oracle record
is current for HEAD (the "suite record postdates the newest *.py/pyproject/uv.lock commit"
rule, implemented as digest equality: oracle.relevant_digest).
"""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle

# oracle's private helpers, shared by these two sibling scripts
_rmtree = oracle._rmtree  # pyright: ignore[reportPrivateUsage]  # sibling tool module, same owner
_drop_function = oracle._drop_function  # pyright: ignore[reportPrivateUsage]  # sibling tool module, same owner

HERE = oracle.HERE
ROOT = oracle.ROOT
CHECKS = HERE / "checks"
BRANCH = oracle.BRANCH
GOALS = tuple(f"G{i:d}" for i in range(8))

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


def run(
    cmd: Sequence[object], cwd: Path | str = ROOT, env: dict[str, str] | None = None, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    return oracle.run(cmd, cwd=cwd, env=env, timeout=timeout)


def git(*args: object, cwd: Path | str = ROOT, check: bool = True) -> str:
    return oracle.git(*args, cwd=cwd, check=check)


def goal_num(goal: str) -> int:
    return int(goal[1:])


# ----------------------------------------------------------------------------- checks files


def load_checks(goal: str, ref: str | None = None) -> dict[str, Any]:
    rel = f"tooling-upgrade/checks/{goal}.toml"
    text = git("show", f"{ref}:{rel}") if ref else (ROOT / rel).read_text(encoding="utf-8")
    return tomllib.loads(text)


def expand(cmd: str | list[str]) -> list[str]:
    parts = cmd if isinstance(cmd, list) else cmd.split()
    return [p.replace("{python}", sys.executable).replace("{root}", str(ROOT)) for p in parts]


def run_check(c: dict[str, Any]) -> tuple[bool, str, str]:
    try:
        r = run(expand(c["cmd"]), timeout=c.get("timeout_s", 7200))
    except subprocess.TimeoutExpired:
        return False, "timeout", ""
    out = r.stdout + r.stderr
    ok = r.returncode == c.get("expect", 0)
    if ok and c.get("expect_stdout"):
        ok = re.search(c["expect_stdout"], r.stdout, flags=re.M) is not None
        if not ok:
            return False, "stdout lacks /{}/".format(c["expect_stdout"]), out
    return ok, "exit {:d} (expect {:d})".format(r.returncode, c.get("expect", 0)), out


def checks_history_problems() -> list[str]:
    """Append-only rule for checks/*.toml: every [[check]] keeps its id, cmd, expect, phase and
    expect_stdout from the commit that registered it; required_drills only grows."""
    problems: list[str] = []
    for goal in GOALS:
        rel = f"tooling-upgrade/checks/{goal}.toml"
        shas = git("log", "--format=%H", "--reverse", "--", rel, check=False).split()
        prev: dict[str, Any] | None = None
        for sha in [*shas, "WORKTREE"]:
            try:
                cur = load_checks(goal, None if sha == "WORKTREE" else sha)
            except (subprocess.SubprocessError, RuntimeError, OSError, tomllib.TOMLDecodeError) as e:
                problems.append(f"{rel} at {sha[:9]} unreadable: {str(e).splitlines()[0][:80]}")
                break
            if prev is not None:
                new = {c["id"]: c for c in cur.get("check", [])}
                for c in prev.get("check", []):
                    n = new.get(c["id"])
                    keys = ("cmd", "expect", "phase", "expect_stdout")
                    if n is None:
                        problems.append("{}: check {} removed at {}".format(goal, c["id"], sha[:9]))
                    elif any(c.get(k) != n.get(k) for k in keys):
                        problems.append("{}: check {} changed at {}".format(goal, c["id"], sha[:9]))
                if not set(prev.get("required_drills", [])) <= set(cur.get("required_drills", [])):
                    problems.append(f"{goal}: required_drills shrank at {sha[:9]}")
            prev = cur
    return problems


# pytest's output-verbosity flags: deleting one changes what pytest prints, never which tests
# run or the exit code. They are the only tokens a superseding check may drop, and only from a
# pytest command (in other programs the same spelling can change semantics: `git diff --quiet`
# sets the exit code, `grep -v` inverts the match).
VERBOSITY_FLAGS = frozenset({"-q", "--quiet", "-v", "--verbose"})


def _pytest_start(argv: Sequence[str]) -> int:
    """Index of the first token pytest itself parses (-1 if `argv` does not run pytest): after
    `-m pytest`, after a `pytest` executable at argv[0], or after `uv run [--opt ...] pytest`."""
    for i in range(len(argv) - 1):
        if argv[i] == "-m" and argv[i + 1] == "pytest":
            return i + 2
    if argv and Path(argv[0]).stem in ("pytest", "py.test"):
        return 1
    if argv[:2] == ["uv", "run"]:
        j = 2
        while j < len(argv) and argv[j].startswith("--") and "=" not in argv[j]:
            j += 1  # uv's own value-less switches (--frozen, --locked, ...)
        if j < len(argv) and argv[j] == "pytest":
            return j + 1
    return -1


def _drops_only_verbosity(old: Sequence[str], new: Sequence[str]) -> bool:
    """True iff `old` runs pytest and `new` is `old` with at least one token deleted, where every
    deleted token is a pytest verbosity flag, sits after the pytest marker, and does not follow an
    option (so it cannot be that option's value, as in `-k -q`)."""
    start = _pytest_start(old)
    if start < 0:
        return False
    i = 0
    for pos, tok in enumerate(old):
        if i < len(new) and new[i] == tok:
            i += 1
            continue
        prev = old[pos - 1] if pos else ""
        if tok not in VERBOSITY_FLAGS or pos < start or (prev.startswith("-") and prev not in VERBOSITY_FLAGS):
            return False
    return i == len(new) and len(new) < len(old)


def supersede_verdict(old: dict[str, Any], new: dict[str, Any], ledger: str, old_at: int, new_at: int) -> list[str]:
    """Problems with `new` superseding `old` (empty = valid). A check registered with a defect no
    tree can satisfy is never edited (append-only); a check appended later may supersede it if
    every key but id and cmd is unchanged (phase, expect, expect_stdout, timeout_s, ...), its cmd
    is the old pytest cmd minus verbosity flags only, it was registered in a later commit, and a
    LEDGER.md decision line names both ids."""
    tag = "{} supersedes {}".format(new["id"], old["id"])
    keys = sorted((set(old) | set(new)) - {"id", "cmd", "supersedes"})
    problems = [f"{tag}: {k} differs" for k in keys if old.get(k) != new.get(k)]
    old_cmd: object = old["cmd"]
    new_cmd: object = new["cmd"]
    if not (isinstance(old_cmd, list) and isinstance(new_cmd, list)):
        problems.append(f"{tag}: both commands must be argv lists")
    elif not _drops_only_verbosity(
        [str(t) for t in cast("list[object]", old_cmd)], [str(t) for t in cast("list[object]", new_cmd)]
    ):
        problems.append(f"{tag}: cmd may only drop pytest verbosity flags {sorted(VERBOSITY_FLAGS)}")
    if not 0 <= old_at < new_at:
        problems.append(f"{tag}: not registered in a later commit than the check it supersedes")

    def names(check_id: str, line: str) -> bool:  # a whole id, not a prefix of a longer one
        return re.search(r"(?<![\w.-])" + re.escape(check_id) + r"(?![\w.-])", line) is not None

    if not any(names(old["id"], ln) and names(new["id"], ln) for ln in ledger.splitlines()):
        problems.append(f"{tag}: no LEDGER.md decision line names both ids")
    return problems


def _first_registered(goal: str, check_id: str) -> int:
    """Index (in commit order) of the first commit of checks/<goal>.toml that holds `check_id`;
    -1 if no commit does (an uncommitted check is never registered)."""
    rel = f"tooling-upgrade/checks/{goal}.toml"
    for i, sha in enumerate(git("log", "--format=%H", "--reverse", "--", rel, check=False).split()):
        if any(c["id"] == check_id for c in load_checks(goal, sha).get("check", [])):
            return i
    return -1


def supersessions(goal: str, data: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """{superseded id: superseding id} for the valid supersessions in `data`, and the problems."""
    by_id = {c["id"]: c for c in data.get("check", [])}
    ledger = (HERE / "LEDGER.md").read_text(encoding="utf-8")
    valid: dict[str, str] = {}
    problems: list[str] = []
    for c in data.get("check", []):
        target = c.get("supersedes")
        if target is None:
            continue
        old = by_id.get(target)
        if old is None:
            problems.append("{} supersedes unknown check {}".format(c["id"], target))
            continue
        if target in valid:
            problems.append(f"{target} is superseded twice")
            continue
        found = supersede_verdict(old, c, ledger, _first_registered(goal, target), _first_registered(goal, c["id"]))
        problems += found
        if not found:
            valid[target] = c["id"]
    return valid, problems


def cmd_assert_checks_files(args: argparse.Namespace) -> int:
    tracked = set(git("ls-files", "tooling-upgrade/checks").split())
    problems = [f"{g} not committed" for g in GOALS if f"tooling-upgrade/checks/{g}.toml" not in tracked]
    for g in GOALS:
        try:
            data = load_checks(g)
            if not data.get("check"):
                problems.append(f"{g} has no checks")
        except (OSError, tomllib.TOMLDecodeError) as e:
            problems.append(f"{g} unparseable: {e}")
    problems += checks_history_problems()
    for g in GOALS:
        try:
            problems += supersessions(g, load_checks(g))[1]
        except (OSError, tomllib.TOMLDecodeError):
            continue  # already reported as unparseable above
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


def cmd_assert_branch(args: argparse.Namespace) -> int:
    ok = on_branch() and is_linked_worktree()
    print(
        "BRANCH: {} (on {}: {}, linked worktree: {}, path {})".format(
            "PASS" if ok else "FAIL", BRANCH, on_branch(), is_linked_worktree(), ROOT
        )
    )
    return 0 if ok else 1


def current_snapshot(require_o1: bool = True) -> Path | None:  # noqa: FBT001, RUF100  # positional flag kept: signature probed by the oracle (O5); FBT is ratchet-only
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
        if (
            meta.get("digest") == head
            and not meta.get("dirty")
            and (not require_o1 or (d / "O1.json").exists())
            and not oracle.verify_snapshot(d.name, 1)
        ):
            return d
    return None


# ----------------------------------------------------------------------------- T1-T7


def pyproject() -> dict[str, Any]:
    try:
        return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def poe_tasks() -> dict[str, Any]:
    return pyproject().get("tool", {}).get("poe", {}).get("tasks", {})


def task_text(task: Any) -> str:
    return json.dumps(task, sort_keys=True)


def t1() -> tuple[bool, str]:
    files = git("ls-files").split("\n")
    bad = sorted(f for f in files if f.rsplit("/", 1)[-1] in FORBIDDEN_CONFIGS)
    for name, task in poe_tasks().items():
        t = task_text(task)
        if re.search(r"\bruff (check|format)\b", t) and "--config pyproject.toml" not in t:
            bad.append(f"poe task {name} runs ruff without --config pyproject.toml")
        if "basedpyright" in t and "-p pyproject.toml" not in t:
            bad.append(f"poe task {name} runs basedpyright without -p pyproject.toml")
    return not bad, "; ".join(bad[:6]) or "one config home"


def in_scope_py() -> set[str]:
    inv = oracle.load_json(oracle.INVENTORY)
    archival = set(inv["archival"])
    return {f for f in git("ls-files", "*.py").split() if f not in archival}


def t2() -> tuple[bool, str]:
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
    msg: list[str] = []
    if missing:
        msg.append(f"ruff skips {len(missing):d} in-scope files (e.g. {sorted(missing)[0]})")
    if extra:
        msg.append(f"ruff analyses {len(extra):d} non-scope files")
    if pyproject().get("tool", {}).get("basedpyright") is not None:
        r = run(["uv", "run", "--frozen", "basedpyright", "-p", "pyproject.toml", "--outputjson"])
        try:
            n = json.loads(r.stdout)["summary"]["filesAnalyzed"]
            if n < len(must):
                msg.append(f"basedpyright analysed {n:d} < {len(must):d} in-scope files")
        except (ValueError, KeyError):
            msg.append("basedpyright --outputjson unreadable")
    return not msg, "; ".join(msg) or "scope equals inventory"


_SUPP = re.compile(
    r"#\s*(noqa(?::\s*[A-Z0-9, ]+)?|type:\s*ignore(?:\[[^\]]*\])?|"
    r"pyright:\s*ignore(?:\[[^\]]*\])?|ruff:\s*noqa[^\n]*|pyright:\s*[a-zA-Z]+[^\n]*|"
    r"fmt:\s*(?:off|skip))",
    re.I,
)


def suppressions() -> list[tuple[str, int, str, str]]:
    """(file, line, form, reason) for every suppression comment in in-scope code."""
    out: list[tuple[str, int, str, str]] = []
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


def t3(goal: int) -> tuple[bool, str]:
    bad: list[str] = []
    for f, i, form, reason in suppressions():
        low = form.lower().replace(" ", "")
        is_type = low.startswith(("type:", "pyright:"))
        if is_type and goal < 4:
            continue
        if blanket(form):
            bad.append(f"{f}:{i:d} blanket {form!r}")
        elif not reason and not low.startswith("pyright:strict"):
            bad.append(f"{f}:{i:d} {form!r} without a reason")
    return not bad, (f"{len(bad):d} violations, e.g. {bad[0]}") if bad else "every suppression has a rule and a reason"


def t4() -> tuple[bool, str]:
    sup = [s for s in suppressions() if not s[2].lower().startswith(("fmt:", "pyright:strict"))]
    loc = sum(len((ROOT / f).read_bytes().splitlines()) for f in in_scope_py() if (ROOT / f).exists())
    budget = loc // 400
    report_ok = (HERE / "SUPPRESSIONS.md").exists() and (HERE / "SUPPRESSIONS.md").read_text(
        encoding="utf-8"
    ) == render_suppressions()
    ok = len(sup) <= budget and report_ok
    return ok, "{:d} suppressions / budget {:d} ({:d} LOC); SUPPRESSIONS.md {}".format(
        len(sup), budget, loc, "current" if report_ok else "STALE or missing"
    )


ALLOWED_PER_FILE = {"tests/**": {"S101", "PLR2004"}, "scripts/**": {"T20", "T201"}}


def t5() -> tuple[bool, str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8") if (ROOT / "pyproject.toml").exists() else ""
    pfi = pyproject().get("tool", {}).get("ruff", {}).get("lint", {}).get("per-file-ignores", {})
    bad: list[str] = []
    for pat, codes in pfi.items():
        allowed = ALLOWED_PER_FILE.get(pat)
        if allowed is None or not set(codes) <= allowed:
            bad.append(f"{pat} = {codes} not a section-16 structural pattern")
        line = next((ln for ln in text.splitlines() if ln.strip().startswith(f'"{pat}"')), "")
        if "#" not in line:
            bad.append(f"{pat} has no comment")
    return not bad, "; ".join(bad) or f"{len(pfi):d} structural per-file ignores, all commented"


def t6() -> tuple[bool, str]:
    tasks = poe_tasks()
    bad: list[str] = []
    for name in GATE_TASKS:
        if name not in tasks:
            bad.append(f"task {name} missing")
            continue
        t = task_text(tasks[name])
        bad += [f"task {name} contains {f!r}" for f in GATE_FORBIDDEN if f in t]
        r = run(["uv", "run", "--frozen", "poe", "-d", name])
        if r.returncode != 0:
            bad.append(f"poe -d {name} failed")
    return not bad, "; ".join(bad[:6]) or "gate tasks run the tools"


def t7() -> tuple[bool, str]:
    g0 = oracle.SNAPSHOTS / "g0" / "O1.json"
    cur = current_snapshot()
    if not g0.exists() or cur is None:
        return False, "no g0 O1 or no suite record current for HEAD"
    a, b = oracle.load_json(g0), oracle.load_json(cur / "O1.json")

    def ran(s: dict[str, Any]) -> int:
        return min(oracle.o1_ran(r) for r in s["runs"])

    def skp(s: dict[str, Any]) -> int:
        return max(r["counts"].get("skipped", 0) for r in s["runs"])

    ok = ran(b) >= ran(a) and skp(b) <= skp(a)
    return ok, f"ran {ran(b):d} (g0 {ran(a):d}), skipped {skp(b):d} (g0 {skp(a):d}) [{cur.name}]"


def tamper(goal: str) -> dict[str, tuple[bool, bool, str]]:
    n = goal_num(goal)
    results: dict[str, tuple[bool, bool, str]] = {}
    for t, fn in (("T1", t1), ("T2", t2), ("T3", lambda: t3(n)), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7)):
        try:
            ok, msg = fn()
        except Exception as e:  # a crashing rule is a failing rule, never a passing one
            ok, msg = False, f"crashed: {type(e).__name__}: {e}"
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
        "| {} | {:d} | `{}` | {} |".format(f, i, form, reason.replace("|", "\\|"))
        for f, i, form, reason in suppressions()
    ]
    return "\n".join(rows) + "\n"


def cmd_suppressions(args: argparse.Namespace) -> int:
    text = render_suppressions()
    p = HERE / "SUPPRESSIONS.md"
    if args.write:
        p.write_text(text, encoding="utf-8", newline="\n")
        print("wrote {} ({:d} rows)".format(p.relative_to(ROOT), text.count("\n") - 4))
        return 0
    ok = p.exists() and p.read_text(encoding="utf-8") == text
    print("SUPPRESSIONS.md: %s" % ("current" if ok else "STALE"))
    return 0 if ok else 1


# ----------------------------------------------------------------------------- drills (section 13)

MISFORMATTED = "x=1;y = [1,\n  2]\ndef f( a ):\n  return a\n"


def _write(tree: Path, rel: str, text: str, append: bool = False) -> None:  # noqa: FBT001, RUF100  # positional flag kept: signature probed by the oracle (O5); FBT is ratchet-only
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


def _poe(task: str) -> list[str]:
    return ["uv", "run", "--frozen", "poe", task]


def _poe_present(task: str) -> list[str]:
    return ["uv", "run", "--frozen", "poe", "-d", task]


def _fault_d05(t: Path) -> None:
    _write(t, "ruff.toml", 'extend-exclude = ["core"]\n')
    _write(t, "core/_drill_fmt.py", MISFORMATTED)


def _fault_d07(t: Path) -> None:
    rel = _first_core_module(t)
    p = t / rel
    p.write_text("# pyright" + ": basic\n" + p.read_text(encoding="utf-8"), encoding="utf-8")


def _fault_d08(t: Path) -> None:
    p = t / "pyproject.toml"
    s = p.read_text(encoding="utf-8")
    p.write_text(s.replace("dependencies = [", 'dependencies = [\n    "six>=1.16",', 1), encoding="utf-8")


def _fault_d09(t: Path) -> None:
    _write(t, "requirements.txt", "six==1.16.0  # hand edit\n", append=True)


def _fault_d14(t: Path) -> None:
    base = oracle.load_json(oracle.SNAPSHOTS / "g0" / "O5.json")
    _drop_function(t, oracle.load_json(oracle.INVENTORY), base)


def _gate_d14(t: Path) -> int:
    """O5 on the mutated module, compared to g0 (non-zero = DIFF = the gate bit)."""
    base = oracle.load_json(oracle.SNAPSHOTS / "g0" / "O5.json")
    inv = oracle.load_json(oracle.INVENTORY)
    graph = oracle.RepoGraph(t, [f for f in oracle.tracked_files(t) if f.endswith(".py")])
    raw = Path(tempfile.mkdtemp(prefix="drill-d14-"))
    mods = {m for m in base["modules"] if m.startswith("core.")}
    _o3, o5 = oracle.probe_modules(t, inv, graph, raw, mods, python=oracle.venv_python(ROOT))
    _rmtree(raw)
    # Same rule as `oracle.py compare`: a diff item covered by a registered intended change
    # (INTENDED_CHANGES.md, e.g. IC-0002 annotation spelling) is not a DIFF.
    intended = [e for e in oracle.load_intended() if e["component"] == "O5"]
    open_ = [
        d
        for d in oracle.compare_o5(base, o5, partial=True)
        if not any(fnmatch.fnmatchcase(d[0], e["key"]) for e in intended)
    ]
    return 1 if open_ else 0


def _fault_d15(t: Path) -> None:
    """Rewrite the `gate` Poe task (key form or table form) into one that swallows failure."""
    p = t / "pyproject.toml"
    lines = p.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i, section = 0, ""
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


def _hooks_present(t: Path) -> list[str]:
    hp = git("config", "--get", "core.hooksPath", cwd=t, check=False).strip()
    return ["git", "rev-parse", "--verify", "HEAD"] if hp and (t / hp / "pre-commit").exists() else ["false"]


def _gate_d13(t: Path) -> int:
    _write(t, "core/_drill_fmt.py", MISFORMATTED)
    run(["git", "add", "core/_drill_fmt.py"], cwd=t)
    return run(["git", "commit", "-q", "-m", "chore: drill"], cwd=t).returncode


DRILLS: dict[
    str,
    tuple[
        str,
        Callable[[Path], object],
        list[str] | Callable[[Path], int],
        list[str] | Callable[[Path], list[str] | int],
    ],
] = {
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
        lambda t: _write(t, "core/_drill_noqa.py", "# ruff" + ": noqa\nimport os\n"),
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
def drill_tree() -> Generator[Path, None, None]:
    base = Path(tempfile.mkdtemp(prefix="aurora-drill-"))
    t = base / "aurora-drill"
    git("worktree", "add", "--detach", str(t), "HEAD")
    # basedpyright reads `venv = ".venv"` relative to the tree (G4.P1); UV_PROJECT_ENVIRONMENT
    # only reaches uv, so give the drill tree the project venv (.venv is git-ignored).
    with contextlib.suppress(OSError):
        (t / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
    # Suite records are git-ignored working records, so a fresh tree has none and T7 (inside the
    # D15 gate) would be red before the fault. Copy HEAD's current record (its JSON, not raw logs).
    cur = current_snapshot()
    if cur is not None:
        dst = t / "tooling-upgrade" / "snapshots" / cur.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in cur.glob("*.json"):
            shutil.copy2(f, dst / f.name)
    try:
        yield t
    finally:
        if (t / ".venv").is_symlink():  # unlink the link itself first: never walk into the real venv
            (t / ".venv").unlink()
        _rmtree(base)
        git("worktree", "prune", check=False)


def _exec(spec: int | list[str] | Callable[[Path], int], t: Path, goal: str) -> int:
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
    _desc, fault, gate, presence = DRILLS[did]
    with drill_tree() as t:
        pres = presence(t) if callable(presence) else presence
        if _exec(pres, t, goal) != 0:
            return "MISSED (gate absent)"
        clean_rc = _exec(gate, t, goal)
        if clean_rc != 0:
            return f"MISSED (gate red before the fault: rc={clean_rc})"
        fault(t)
        rc = _exec(gate, t, goal)
        return "BIT" if rc != 0 else "MISSED"


def run_drills(goal: str, ids: list[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for did in ids or sorted(DRILLS):
        try:
            out[did] = run_drill(did, goal)
        except Exception as e:  # a drill that cannot run proves nothing about the gate
            out[did] = f"MISSED (drill error: {type(e).__name__}: {str(e)[:120]})"
        print(f"{did} {out[did]}  -- {DRILLS[did][0]}", flush=True)
    return out


def cmd_drills(args: argparse.Namespace) -> int:
    res = run_drills(args.goal)
    missed = sum(1 for v in res.values() if v.startswith("MISSED"))
    bit = sum(1 for v in res.values() if v == "BIT")
    print(f"DRILLS: {bit:d}/{len(res):d} BIT")
    print(f"DRILLS-MISSED {missed:d}/{len(res):d}")
    if args.expect_missed:
        return 0 if missed == len(res) else 1
    return 0 if bit == len(res) else 1


# ----------------------------------------------------------------------------- fresh clone


def cmd_fresh_clone(args: argparse.Namespace) -> int:
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
            print("$ {}\n{}\n[exit {:d}]".format(" ".join(cmd), tail, r.returncode))
            if r.returncode != 0:
                print("FRESH-CLONE: FAIL")
                return 1
        print("FRESH-CLONE: PASS")
        return 0
    finally:
        _rmtree(base)


# ----------------------------------------------------------------------------- goal-specific asserts


def _report(name: str, problems: list[str]) -> int:
    for p in problems[:30]:
        print("  ", p)
    print("{}: {}".format(name, "PASS" if not problems else f"FAIL ({len(problems):d})"))
    return 1 if problems else 0


def commits_since_base() -> Iterator[tuple[str, str, str]]:
    out = git("log", "--reverse", "--format=%H%x1f%s%x1f%b%x1e", f"{oracle.g0_base()}..HEAD")
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if rec:
            sha, subject, body = rec.split("\x1f", 2)
            yield sha, subject, body


def cmd_assert_mechanical_commits(args: argparse.Namespace) -> int:
    """Every commit with a `Replay:` line reproduces exactly from its parent (class B/C), and
    every class-B (`style:`) commit is AST-equal to its parent (O2)."""
    import shlex

    problems: list[str] = []
    n = 0
    for sha, subject, body in commits_since_base():
        m = re.search(r"(?m)^Replay:\s*(.+)$", body)
        if subject.startswith("style:"):
            bad = [p for p, ok, _ in oracle.ast_equal(sha + "^", sha) if not ok]
            if bad:
                problems.append("{} {}: AST differs in {}".format(sha[:9], subject, ", ".join(bad[:3])))
            if not m:
                problems.append(f"{sha[:9]} {subject}: class-B commit without Replay:")
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
                problems.append(f"{sha[:9]} {subject}: replay differs from the commit")
        finally:
            _rmtree(base)
            git("worktree", "prune", check=False)
    print(f"replayed {n:d} mechanical commit(s)")
    return _report("MECHANICAL COMMITS", problems)


def cmd_assert_blame_ignore_revs(args: argparse.Namespace) -> int:
    p = ROOT / ".git-blame-ignore-revs"
    if not p.exists():
        return _report("BLAME-IGNORE-REVS", [".git-blame-ignore-revs missing"])
    problems: list[str] = []
    shas = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    for sha in shas:
        subj = git("log", "-1", "--format=%s", sha, check=False).strip()
        if not subj.startswith("style:"):
            problems.append(f"{sha[:9]} is not a style: commit ({subj!r})")
    if not shas:
        problems.append("no revisions listed")
    return _report("BLAME-IGNORE-REVS", problems)


_VERSION_SURFACES = (".github/workflows", "scripts/githooks", ".claude/settings.json", ".mcp.json")


def cmd_assert_python_agrees(args: argparse.Namespace) -> int:
    pv = ROOT / ".python-version"
    if not pv.exists():
        return _report("PYTHON AGREES", [".python-version missing"])
    pin = pv.read_text(encoding="utf-8").strip()
    pin_mm = ".".join(pin.split(".")[:2])
    problems: list[str] = []
    pat = re.compile(r"(?:python-version:\s*[\"']?|(?:uv run|uvx|py)\s+(?:-p|--python)\s+|py -)(3\.\d+)")
    for surf in _VERSION_SURFACES:
        root = ROOT / surf
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            problems.extend(
                f"{f.relative_to(ROOT).as_posix()} says {m.group(1)}, .python-version says {pin_mm}"
                for m in pat.finditer(text)
                if m.group(1) != pin_mm
            )
    rp = pyproject().get("project", {}).get("requires-python", "")
    floor = re.search(r">=\s*(3\.\d+)", rp)
    if not floor or tuple(map(int, floor.group(1).split("."))) > tuple(map(int, pin_mm.split("."))):
        problems.append(f"requires-python {rp!r} is not a floor at or below the pin {pin_mm}")
    return _report(f"PYTHON AGREES (pin {pin_mm})", problems)


def cmd_assert_no_bare_py(args: argparse.Namespace) -> int:
    """No executable surface launches Python with a bare `py ` (G1.P5); the documented Windows
    fallback inside the pyrun shim's chain is the one allowed mention."""
    problems: list[str] = []
    for f in sorted((ROOT / "scripts" / "githooks").glob("*")):
        if f.suffix or not f.is_file():
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"\s*py\s", ln):
                problems.append(f"{f.relative_to(ROOT).as_posix()}:{i:d} {ln.strip()[:80]}")
    for rel in (".mcp.json", ".claude/settings.json"):
        p = ROOT / rel
        if not p.exists():
            continue
        problems.extend(
            f"{rel} command {m.group(1)[:80]!r}"
            for m in re.finditer(r'"command"\s*:\s*"([^"]*)"', p.read_text(encoding="utf-8"))
            if re.search(r"(^|&&\s*|;\s*)py\s", m.group(1)) or m.group(1) == "py"
        )
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for i, ln in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(run:\s*|^\s*)py\s", ln):
                problems.append(f"{wf.relative_to(ROOT).as_posix()}:{i:d} {ln.strip()[:80]}")
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


def dev_group_problems(pp: dict[str, Any]) -> list[str]:
    groups = pp.get("dependency-groups", {})
    dev = {_req_name(s) for s in groups.get("dev", []) if isinstance(s, str)}
    problems = [f"dev lacks {n}" for n in DEV_GROUP if n not in dev]
    problems += [f"dev has {n} (not in the plan's list)" for n in sorted(dev - set(DEV_GROUP))]
    runtime = {_req_name(s) for s in pp.get("project", {}).get("dependencies", [])}
    problems += [f"[project].dependencies still has tool {n}" for n in sorted(runtime & set(DEV_GROUP))]
    problems += [
        "pre-commit is still declared (replaced by prek)"
        for g in [runtime] + [{_req_name(s) for s in v if isinstance(s, str)} for v in groups.values()]
        if "pre-commit" in g
    ]
    for g in ("ml", "browser"):
        if g not in groups:
            problems.append(f"optional group {g} missing")
    return problems


def cmd_assert_dev_group(args: argparse.Namespace) -> int:
    return _report("DEV GROUP", dev_group_problems(pyproject()))


def uv_settings_problems(pp: dict[str, Any]) -> list[str]:
    uv = pp.get("tool", {}).get("uv", {})
    problems: list[str] = []
    if uv.get("package") is not False:
        problems.append("tool.uv.package is not false")
    m = re.fullmatch(r">=\s*0\.(\d+)(\.\d+)?", str(uv.get("required-version", "")))
    if not m or int(m.group(1)) < 12:
        problems.append(
            "tool.uv.required-version {!r} is not >=0.12 (the G0 uv minor)".format(uv.get("required-version"))
        )
    if uv.get("exclude-newer") != "7 days":
        problems.append("tool.uv.exclude-newer {!r} != '7 days'".format(uv.get("exclude-newer")))
    if uv.get("default-groups") != ["dev"]:
        problems.append("tool.uv.default-groups {!r} != ['dev']".format(uv.get("default-groups")))
    return problems


def cmd_assert_uv_settings(args: argparse.Namespace) -> int:
    return _report("UV SETTINGS", uv_settings_problems(pyproject()))


def gate_problems(tasks: dict[str, Any], members: list[str]) -> list[str]:
    """`gate` is a sequence over gate tasks in plan order (G1.P6) that includes at least
    `members`; tasks only ever join it."""
    gate = tasks.get("gate")
    seq = (
        cast("dict[str, Any]", gate).get("sequence")
        if isinstance(gate, dict)
        else cast("list[Any]", gate)
        if isinstance(gate, list)
        else None
    )
    if not isinstance(seq, list):
        return ["gate is not a sequence task"]
    names = [
        s if isinstance(s, str) else cast("dict[str, Any]", s).get("ref", "") if isinstance(s, dict) else ""
        for s in cast("list[Any]", seq)
    ]
    problems = [f"gate step {n!r} is not a plan gate task" for n in names if n not in GATE_TASKS]
    order = [n for n in GATE_TASKS if n in names]
    if names != order:
        problems.append(f"gate order {names} differs from plan order {order}")
    problems += [f"gate lacks {m}" for m in members if m not in names]
    if isinstance(gate, dict) and cast("dict[str, Any]", gate).get("ignore_fail"):
        problems.append("gate sets ignore_fail")
    return problems


def cmd_assert_gate(args: argparse.Namespace) -> int:
    return _report("GATE MEMBERS", gate_problems(poe_tasks(), args.members))


_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s'\"#]+)")


def sha_pin_problems(root: Path) -> list[str]:
    """Every workflow `uses:` names a 40-hex commit (local ./ actions and docker:// excepted)."""
    problems: list[str] = []
    wf_dir = root / ".github" / "workflows"
    for wf in sorted(wf_dir.glob("*.y*ml")) if wf_dir.exists() else []:
        for i, ln in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            m = _USES.match(ln)
            if not m or m.group(1).startswith(("./", "docker://")):
                continue
            ref = m.group(1).rpartition("@")[2] if "@" in m.group(1) else ""
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                problems.append(f"{wf.relative_to(root).as_posix()}:{i:d} {m.group(1)} is not pinned to a commit SHA")
    return problems


def cmd_assert_sha_pins(args: argparse.Namespace) -> int:
    return _report("SHA PINS", sha_pin_problems(ROOT))


def workflow_permission_problems(root: Path) -> list[str]:
    """Least privilege (G5.P3): every workflow declares top-level `permissions:`, and none grants
    `write-all` anywhere. (zizmor's default persona reports excessive-permissions only at higher
    confidence, so a single-job `permissions: write-all` passed it: drill D11.)"""
    problems: list[str] = []
    wf_dir = root / ".github" / "workflows"
    for wf in sorted(wf_dir.glob("*.y*ml")) if wf_dir.exists() else []:
        rel = wf.relative_to(root).as_posix()
        text = wf.read_text(encoding="utf-8")
        if not re.search(r"(?m)^permissions:", text):
            problems.append(f"{rel}: no top-level permissions:")
        problems.extend(
            f"{rel}:{i:d} grants write-all"
            for i, ln in enumerate(text.splitlines(), 1)
            if re.match(r"\s*permissions:\s*write-all\b", ln)
        )
    return problems


def cmd_assert_workflow_permissions(_args: argparse.Namespace) -> int:
    """`poe ci-lint`: every workflow declares top-level permissions; none is write-all."""
    return _report("WORKFLOW PERMISSIONS", workflow_permission_problems(ROOT))


def cmd_assert_ratchet(args: argparse.Namespace) -> int:
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
    problems = [f"{f}: {counts[f]:d} > ratchet {limits[f]:d}" for f in sorted(limits) if counts[f] > limits[f]]
    print(f"counts: {counts}")
    return _report("RATCHET", problems)


def cmd_assert_latent_regressions(args: argparse.Namespace) -> int:
    """Every INTENDED_CHANGES entry with `fix_commit` + `regression_test` (G4.P2): the test fails
    on the fix's parent and passes on HEAD."""
    problems: list[str] = []
    n = 0
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
                        "{}: {} {} on {}".format(
                            e["id"], e["regression_test"], "passed" if want_fail else "failed", ref
                        )
                    )
            finally:
                _rmtree(base)
                git("worktree", "prune", check=False)
    print(f"latent-bug entries checked: {n:d}")
    return _report("LATENT REGRESSIONS", problems)


STRICT_ISLANDS = (
    # G4.P3: the Python files this effort wrote (oracle and certify tooling included)
    "scripts/generators/gen_requirements.py",
    "tests/test_tooling_upgrade_oracle.py",
    "tooling-upgrade/certify.py",
    "tooling-upgrade/oracle.py",
    "tooling-upgrade/pytest_plugin/aurora_oracle_plugin.py",
)
BASELINE_FILES = (".basedpyright/baseline.json", "basedpyright-baseline.json")


def types_config_problems() -> list[str]:
    """G4.P1: [tool.basedpyright] carries the plan's settings, [tool.ty] exists, no baseline."""
    tool = pyproject().get("tool", {})
    bp, ty = tool.get("basedpyright"), tool.get("ty")
    if not isinstance(bp, dict):
        return ["no [tool.basedpyright] table"]
    bp = cast("dict[str, Any]", bp)
    floor = re.search(r"(\d+\.\d+)", pyproject().get("project", {}).get("requires-python", ""))
    want = {
        "typeCheckingMode": "standard",
        "pythonVersion": floor.group(1) if floor else "?",
        "venvPath": ".",
        "venv": ".venv",
        "enableTypeIgnoreComments": True,
        "reportUnnecessaryTypeIgnoreComment": "error",
    }
    problems = [f"basedpyright {k} = {bp.get(k)!r}, want {v!r}" for k, v in want.items() if bp.get(k) != v]
    problems += [f"basedpyright sets {k}" for k in ("baselineFile", "strict", "ignore") if k in bp]
    for env in bp.get("executionEnvironments", []):
        mode = env.get("typeCheckingMode", "standard")
        if mode not in ("standard", "basic", "strict") or any(k.startswith("report") for k in env):
            problems.append(f"executionEnvironment {env.get('root')!r} loosens rules beyond `basic`")
    if not isinstance(ty, dict):
        problems.append("no [tool.ty] table")
    problems += [f"baseline file {b} exists" for b in BASELINE_FILES if (ROOT / b).exists()]
    return problems


def cmd_assert_types_config(_args: argparse.Namespace) -> int:
    """Check [tool.basedpyright] and [tool.ty] against plan G4.P1."""
    return _report("TYPES CONFIG", types_config_problems())


def cmd_assert_strict_islands(_args: argparse.Namespace) -> int:
    """Check that every G4.P3 island opts into strict mode."""
    problems: list[str] = []
    for f in STRICT_ISLANDS:
        p = ROOT / f
        head = p.read_text(encoding="utf-8").splitlines()[:5] if p.exists() else []
        if not any(re.fullmatch(r"#\s*pyright:\s*strict\s*", ln) for ln in head):
            problems.append(f"{f} has no strict pyright header")
    return _report("STRICT ISLANDS", problems)


def cmd_assert_suppressions(_args: argparse.Namespace) -> int:
    """Run the gate's suppression step: T3 at G4 strength and T4 (this makes D07 bite)."""
    problems: list[str] = []
    for name, (ok, msg) in (("T3", t3(4)), ("T4", t4())):
        if not ok:
            problems.append(f"{name}: {msg}")
    return _report("SUPPRESSIONS", problems)


def cmd_assert_ledger_entry(args: argparse.Namespace) -> int:
    text = (HERE / "LEDGER.md").read_text(encoding="utf-8")
    rows = [ln for ln in text.splitlines() if ln.startswith(f"| {args.phase}")]
    ok = any(re.search(r"\|\s*(DONE|CERTIFIED|NO-GO|SKIPPED)\s*\|", r) for r in rows)
    return _report(f"LEDGER {args.phase}", [] if ok else ["no DONE/CERTIFIED/NO-GO/SKIPPED row"])


def cmd_assert_docs_uv(args: argparse.Namespace) -> int:
    problems: list[str] = []
    for doc in ("README.md", "CONTRIBUTING.md", "AGENTS.md", "docs/DEPLOY.md"):
        p = ROOT / doc
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        problems.extend(f"{doc} never mentions `{needle}`" for needle in ("uv sync", "uv run") if needle not in t)
    t = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8") if (ROOT / "CONTRIBUTING.md").exists() else ""
    problems.extend(
        f"CONTRIBUTING.md lacks `{needle}`"
        for needle in ("uv run poe gate", "uv run poe test", "--no-verify")
        if needle not in t
    )
    return _report("DOCS UV-PRIMARY", problems)


# ----------------------------------------------------------------------------- G5 assertions

WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CI_JOBS = ("gate", "test", "ty", "windows-smoke", "ci-lint")
# The guardrail steps the pre-G5 workflow ran (G0's ci.yml), kept as named steps (G5.P3).
CI_GUARDRAILS = {
    "Architecture boundary guardrail": "check_boundaries",
    "Doc-freshness guardrail": "check_doc_freshness",
    "Comprehensibility guardrail (docs match code; no stale refs / case drift)": "check_comprehensibility",
    "Wiring guardrail (no built-but-unwired core module)": "check_wiring",
    "Door-parity guardrail (CLI<->MCP verb surface)": "check_door_parity",
}
CI_GUARDRAIL_COMMENTS = (
    "# The comprehensibility immune system -- the unbypassable REMOTE gate: every push/PR is checked,",
    "# so drift can't reach the shared repo via any local path (mirror/git commit that skipped hooks).",
    "# See docs/library/design/20260701_the-comprehensibility-immune-system-desi_339b01.md.",
)


def _yaml_scalar(v: str) -> str:
    """A plain or quoted YAML scalar, its trailing comment dropped (the subset ci.yml uses)."""
    v = v.strip()
    if v[:1] in "\"'":
        q = v[0]
        end = v.find(q, 1)
        return v[1:end] if end > 0 else v[1:]
    return re.sub(r"\s+#.*$", "", v).strip()


def parse_workflow(text: str) -> dict[str, dict[str, Any]]:
    """jobs -> {keys: {...}, env: {...}, services: [...], steps: [{name, uses, run, with}]}.

    Stdlib-only reader for the YAML subset .github/workflows/ci.yml is written in: block
    mappings, step lists, plain/quoted scalars and `|`/`>-` block scalars. Anything it cannot
    place is ignored, and assert-ci-structure checks the parts it relies on."""
    lines = text.splitlines()
    jobs: dict[str, dict[str, Any]] = {}
    i = lines.index("jobs:") + 1 if "jobs:" in lines else len(lines)
    job: dict[str, Any] | None = None
    section = ""
    step: dict[str, str] | None = None

    def indent(ln: str) -> int:
        return len(ln) - len(ln.lstrip(" "))

    while i < len(lines):
        ln = lines[i]
        i += 1
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        ind = indent(ln)
        if ind == 0:
            break
        body = ln.strip()
        if ind == 2 and body.endswith(":"):
            job = {"keys": {}, "env": {}, "services": [], "steps": []}
            jobs[body[:-1]] = job
            section, step = "", None
            continue
        if job is None:
            continue
        if ind == 4:
            key, _, val = body.partition(":")
            section, step = key, None
            if val.strip():
                job["keys"][key] = _yaml_scalar(val)
            continue
        if section == "env" and ind == 6:
            key, _, val = body.partition(":")
            job["env"][key] = _yaml_scalar(val)
        elif section == "services" and ind == 6:
            job["services"].append(body.rstrip(":"))
        elif section == "steps" and ind >= 6:
            if ind == 6 and body.startswith("- "):
                step = {}
                job["steps"].append(step)
                body = body[2:]
                ind = 8
            if step is None or ind != 8:
                if step is not None and ind == 10 and step.get("_with") == "1":
                    k, _, v = body.partition(":")
                    step["with." + k] = _yaml_scalar(v)
                continue
            key, _, val = body.partition(":")
            val = val.strip()
            if key == "with":
                step["_with"] = "1"
                continue
            if val in ("|", "|-", ">", ">-"):
                block: list[str] = []
                while i < len(lines) and (not lines[i].strip() or indent(lines[i]) > 8):
                    block.append(lines[i].strip())
                    i += 1
                step[key] = ("\n" if val.startswith("|") else " ").join(b for b in block if b)
            else:
                step[key] = _yaml_scalar(val)
    return jobs


def cmd_assert_ci_structure(_args: argparse.Namespace) -> int:
    """G5.P3: the workflow's shape (permissions, concurrency, timeouts, pins, jobs, guardrails)."""
    problems: list[str] = []
    text = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.exists() else ""
    if not re.search(r"(?m)^permissions:\n  contents: read\s*$", text):
        problems.append("top-level `permissions: contents: read` missing")
    if not re.search(r"(?m)^concurrency:\n(  .*\n)*  cancel-in-progress: true\s*$", text):
        problems.append("top-level concurrency with cancel-in-progress: true missing")
    for m in re.finditer(r"(?m)^\s*(?:-\s+)?uses:\s*(\S+)(.*)$", text):
        if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", m.group(1)):
            problems.append(f"uses: {m.group(1)} is not pinned to a 40-hex SHA")
        if not re.match(r"\s+#\s*v?\d+\.\d+\.\d+\s*$", m.group(2)):
            problems.append(f"uses: {m.group(1)} lacks its `# vX.Y.Z` comment")
    jobs = parse_workflow(text)
    problems.extend(f"job {name} missing" for name in CI_JOBS if name not in jobs)
    for name, job in jobs.items():
        keys: dict[str, str] = job["keys"]
        steps: list[dict[str, str]] = job["steps"]
        if not keys.get("timeout-minutes", "").isdigit():
            problems.append(f"job {name}: no timeout-minutes")
        for st in steps:
            uses = st.get("uses", "")
            if uses.startswith("actions/checkout@") and st.get("with.persist-credentials") != "false":
                problems.append(f"job {name}: checkout without persist-credentials: false")
            if uses.startswith("astral-sh/setup-uv@") and st.get("with.enable-cache") != "true":
                problems.append(f"job {name}: setup-uv without enable-cache: true")
        runs = [st.get("run", "") for st in steps]
        if not any(r.strip() == "uv sync --locked" for r in runs):
            problems.append(f"job {name}: no `uv sync --locked` step")
        if not any(st.get("uses", "").startswith("astral-sh/setup-uv@") for st in steps):
            problems.append(f"job {name}: no astral-sh/setup-uv step")
    want_run = {
        "gate": "uv run poe gate",
        "test": "uv run poe test",
        "ty": "uv run poe types-ty",
        "ci-lint": "uv run poe ci-lint",
    }
    for name, cmd in want_run.items():
        if name in jobs and cmd not in [st.get("run", "").strip() for st in jobs[name]["steps"]]:
            problems.append(f"job {name}: does not run `{cmd}`")
    problems.extend(
        f"job {name}: continue-on-error: true missing"
        for name in ("ty", "windows-smoke")
        if name in jobs and jobs[name]["keys"].get("continue-on-error") != "true"
    )
    problems.extend(
        f"job {name}: blocking job marked continue-on-error"
        for name in ("gate", "test", "ci-lint")
        if name in jobs and jobs[name]["keys"].get("continue-on-error") == "true"
    )
    if "windows-smoke" in jobs:
        ws = jobs["windows-smoke"]
        if ws["keys"].get("runs-on") != "windows-latest":
            problems.append("job windows-smoke: not runs-on windows-latest")
        wr = " ".join(st.get("run", "") for st in ws["steps"])
        if " status" not in wr or "test_portability" not in wr:
            problems.append("job windows-smoke: needs a status command and the portability tests")
    if "test" in jobs:
        t = jobs["test"]
        if "redis" not in t["services"] or t["env"].get("REDIS_PORT") != "16379":
            problems.append("job test: the Redis service and its env (REDIS_PORT 16379) must stay")
    gate_steps = {st.get("name", ""): st.get("run", "") for st in jobs.get("gate", {}).get("steps", [])}
    for step_name, checker in CI_GUARDRAILS.items():
        if gate_steps.get(step_name, "").strip() != f"uv run poe guardrails --only {checker}":
            problems.append(f"guardrail step {step_name!r} must run `uv run poe guardrails --only {checker}`")
    problems.extend(f"guardrail comment missing: {c}" for c in CI_GUARDRAIL_COMMENTS if c not in text)
    return _report("CI STRUCTURE", problems)


def cmd_assert_dependabot(_args: argparse.Namespace) -> int:
    """G5.P3: uv + github-actions, weekly, 7-day cooldown, minor and patch grouped."""
    path = ROOT / ".github" / "dependabot.yml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    problems: list[str] = [] if re.search(r"(?m)^version:\s*2\s*$", text) else ["version: 2 missing"]
    blocks = re.split(r"(?m)^  - package-ecosystem:", text)[1:]
    seen: set[str] = set()
    for b in blocks:
        eco = _yaml_scalar(b.splitlines()[0])
        seen.add(eco)
        if not re.search(r"interval:\s*\"?weekly\"?", b):
            problems.append(f"{eco}: schedule is not weekly")
        if not re.search(r"cooldown:\s*\n\s+default-days:\s*7\b", b):
            problems.append(f"{eco}: cooldown default-days 7 missing")
        if not (re.search(r"groups:", b) and '"minor"' in b and '"patch"' in b):
            problems.append(f"{eco}: minor and patch updates are not grouped")
    problems.extend(f"ecosystem {e} missing" for e in ("uv", "github-actions") if e not in seen)
    return _report("DEPENDABOT", problems)


PRECOMMIT = ROOT / ".pre-commit-config.yaml"
PRECOMMIT_HOOKS = (
    "ruff-check", "ruff-format", "uv-lock", "uv-export", "check-toml", "check-yaml",
    "check-merge-conflict", "check-added-large-files", "zizmor", "actionlint",
)  # fmt: skip  # data table: one hook id per plan G5.P2 bullet
PRECOMMIT_FORBIDDEN = (
    "trailing-whitespace", "end-of-file-fixer", "mixed-line-ending", "fix-byte-order-marker",
    "pretty-format-json", "requirements-txt-fixer", "file-contents-sorter",
)  # fmt: skip  # data table: fixers that would rewrite non-Python trees (I8)


def cmd_assert_precommit_config(_args: argparse.Namespace) -> int:
    """G5.P2: SHA revs with version comments, the plan's hooks, exclude = ARCHIVAL, no prek install."""
    problems: list[str] = []
    text = PRECOMMIT.read_text(encoding="utf-8") if PRECOMMIT.exists() else ""
    revs = re.findall(r"(?m)^\s+rev:\s*(\S+)(.*)$", text)
    if not revs:
        problems.append("no rev: lines")
    for rev, rest in revs:
        if not re.fullmatch(r"[0-9a-f]{40}", rev):
            problems.append(f"rev {rev} is not a full commit SHA")
        if not re.match(r"\s+#\s*v?\d+\.\d+\.\d+", rest):
            problems.append(f"rev {rev[:12]} lacks its version comment")
    ids = re.findall(r"(?m)^\s+- id:\s*(\S+)", text)
    problems.extend(f"hook {h} missing" for h in PRECOMMIT_HOOKS if h not in ids)
    problems.extend(f"forbidden fixer hook {h}" for h in PRECOMMIT_FORBIDDEN if h in ids)
    gen = (ROOT / "scripts" / "generators" / "gen_requirements.py").read_text(encoding="utf-8")
    outputs = re.findall(r'^    "(requirements[^"]*\.txt)":', gen, flags=re.MULTILINE)
    exports = re.findall(r"(?m)^\s+- id: uv-export\n(?:\s+(?!- id).*\n)*?\s+args: \[(.*)\]", text)
    problems.extend(
        f"no uv-export hook writes {out}"
        for out in outputs
        if not any(a.rstrip().endswith("--output-file, " + out) for a in exports)
    )
    if not re.search(r"(?m)^\s+- id: ruff-check\n\s+args: \[--fix", text):
        problems.append("ruff-check hook does not pass --fix")
    m = re.search(r"(?ms)^exclude: \|\n(.*?)\n\S", text)
    if not m:
        problems.append("top-level exclude block missing")
    else:
        rx = re.compile("\n".join(ln[2:] for ln in m.group(1).splitlines()))
        inv = oracle.load_json(HERE / "inventory.json")
        problems.extend(f"exclude misses ARCHIVAL {f}" for f in inv["archival"] if not rx.match(f))
        problems.extend(f"exclude hides in-scope {f}" for f in inv["in_scope"] if rx.match(f))
    hook = Path(git("rev-parse", "--git-path", "hooks/pre-commit").strip())
    hook = hook if hook.is_absolute() else ROOT / hook
    if hook.exists() and "prek" in hook.read_text(encoding="utf-8", errors="replace"):
        problems.append(f"{hook} was written by `prek install` (it would fight core.hooksPath)")
    return _report("PRE-COMMIT CONFIG", problems)


EXPERIMENTS = HERE / "EXPERIMENTS-G5.md"
EXPERIMENT_NAMES = ("xdist", "randomly", "doctest", "coverage")


def cmd_assert_experiments(_args: argparse.Namespace) -> int:
    """G5.P1: each experiment has a verdict with evidence, and the config matches the verdict."""
    problems: list[str] = []
    text = EXPERIMENTS.read_text(encoding="utf-8") if EXPERIMENTS.exists() else ""
    entries: dict[str, dict[str, Any]] = {}
    for block in re.findall(r"```toml\n(.*?)```", text, flags=re.DOTALL):
        e = tomllib.loads(block)
        entries[str(e.get("experiment"))] = e
    for name in EXPERIMENT_NAMES:
        e = entries.get(name)
        if e is None:
            problems.append(f"experiment {name}: no record")
            continue
        if e.get("verdict") not in ("ADOPT", "ADOPT-FAST-ONLY", "REJECT"):
            problems.append(f"experiment {name}: verdict must be ADOPT, ADOPT-FAST-ONLY or REJECT")
        if not e.get("evidence"):
            problems.append(f"experiment {name}: no evidence")
    pp = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = " ".join(pp["tool"]["pytest"]["ini_options"].get("addopts", []))
    tasks = pp["tool"]["poe"]["tasks"]
    test_text = task_text(tasks.get("test", ""))
    fast_text = task_text(tasks.get("test-fast", ""))
    rnd = entries.get("randomly", {}).get("verdict")
    if rnd == "REJECT":
        if "no:randomly" not in addopts:
            problems.append("randomly REJECTed but addopts lacks -p no:randomly")
        if "order-dependent" not in (HERE / "BACKLOG.md").read_text(encoding="utf-8"):
            problems.append("randomly REJECTed but BACKLOG.md lists no order-dependent tests")
    if rnd == "ADOPT" and "no:randomly" in addopts:
        problems.append("randomly ADOPTed but addopts still disables it")
    xd = entries.get("xdist", {}).get("verdict")
    if xd == "ADOPT" and "xdist" not in test_text:
        problems.append("xdist ADOPTed but poe test does not use it")
    if xd == "ADOPT-FAST-ONLY" and "xdist" not in fast_text:
        problems.append("xdist ADOPT-FAST-ONLY but poe test-fast does not use it")
    if xd != "ADOPT" and ("-n " in addopts or "--numprocesses" in addopts):
        problems.append("xdist not ADOPTed for the suite but addopts enables it")
    dt = entries.get("doctest", {}).get("verdict")
    if (dt == "ADOPT") != ("--doctest-modules" in addopts + test_text):
        problems.append("doctest verdict and the configuration disagree")
    if entries.get("coverage", {}).get("verdict") != "ADOPT":
        problems.append("coverage reporting is always on (plan G5.P1): its verdict must be ADOPT")
    cov = pp["tool"].get("coverage", {}).get("run", {})
    if cov.get("branch") is not True or sorted(cov.get("source", [])) != sorted(oracle.COVERAGE_SOURCES):
        problems.append("[tool.coverage.run] must set branch = true and source = the O10 packages")
    if "O10" not in test_text or "compare" not in test_text:
        problems.append("poe test must capture O10 and compare it with g0 (the 0.5 pp ratchet)")
    return _report("EXPERIMENTS G5.P1", problems)


def _generators() -> list[str]:
    sys.path.insert(0, str(ROOT))
    try:
        from scripts.githooks import pre_commit

        names = [str(g) for g in cast("tuple[str, ...]", pre_commit.GENERATORS)]
    finally:
        sys.path.remove(str(ROOT))
    return [*names, "gen_requirements"]


def cmd_assert_generated_docs(_args: argparse.Namespace) -> int:
    """G5.P4: at HEAD each generator's --check passes (where it has one), and every generator
    re-run in a throwaway tree changes nothing -- except the one line gen_physics_sheet stamps
    with the current HEAD SHA ("> Derived at <sha>."), which no commit can keep current."""
    problems: list[str] = []
    gens = _generators()
    with drill_tree() as t:
        env = oracle.oracle_env({"UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"), "UV_NO_SYNC": "1"})
        for g in gens:
            src = t / "scripts" / "generators" / f"{g}.py"
            if "--check" in src.read_text(encoding="utf-8"):
                r = run([sys.executable, str(src), "--check"], cwd=t, env=env, timeout=600)
                print(f"{g} --check: rc={r.returncode:d}")
                if r.returncode != 0:
                    problems.append(f"{g} --check exits {r.returncode:d}")
            r = run([sys.executable, str(src)], cwd=t, env=env, timeout=600)
            print(f"{g} (write): rc={r.returncode:d}")
            if r.returncode != 0:
                problems.append(f"{g} exits {r.returncode:d}")
        diff = run(["git", "diff", "-U0", "--no-color"], cwd=t).stdout.splitlines()
        stamp = re.compile(r"^[-+]> Derived at [0-9a-f]{7,40}\.")
        changed = [ln for ln in diff if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        problems.extend(f"stale generated text: {ln[:120]}" for ln in changed if not stamp.match(ln))
    return _report("GENERATED DOCS", problems)


def cmd_assert_ci_replay(_args: argparse.Namespace) -> int:
    """G5.P3 local proof (nothing is pushed, I2): replay every `run:` step of every Linux job, in
    order, with the job's env, in a fresh clone of HEAD, as GitHub would (`bash -e`). `uses:`
    steps are emulated: checkout = the clone; setup-uv = the uv on PATH. A job's Redis service is
    the local server on the same port. A continue-on-error job may fail without failing the
    replay. Windows jobs are recorded as defined, not executed."""
    jobs = parse_workflow(WORKFLOW.read_text(encoding="utf-8"))
    logs = oracle.SNAPSHOTS / "ci-replay"  # git-ignored working record: every step's full output
    if logs.exists():
        _rmtree(logs)
    logs.mkdir(parents=True)
    base = Path(tempfile.mkdtemp(prefix="aurora-ci-replay-"))
    clone = base / "aurora-ci"
    failed: list[str] = []
    try:
        for argv in (
            ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(clone)],
            ["git", "-C", str(clone), "checkout", "--quiet", git("rev-parse", "HEAD").strip()],
        ):
            if run(argv).returncode != 0:
                return _report("CI REPLAY", ["could not clone HEAD: " + " ".join(argv)])
        uv_v = run(["uv", "--version"]).stdout.strip()
        for name, job in jobs.items():
            keys: dict[str, str] = job["keys"]
            soft = keys.get("continue-on-error") == "true"
            if "windows" in keys.get("runs-on", ""):
                print(f"JOB {name}: defined, not executed (runs-on {keys.get('runs-on')}; no Windows host)")
                continue
            print(f"JOB {name} (runs-on {keys.get('runs-on')}{', continue-on-error' if soft else ''})")
            env = oracle.oracle_env()
            env.pop("VIRTUAL_ENV", None)
            for k, v in cast("dict[str, str]", job["env"]).items():
                env[k] = v.replace("${{ github.workspace }}", str(clone))
            if job["services"]:
                print(
                    "  services {}: the local server on the job's REDIS_PORT {}".format(
                        ",".join(job["services"]), env.get("REDIS_PORT", "?")
                    )
                )
            job_ok = True
            for st in cast("list[dict[str, str]]", job["steps"]):
                label = st.get("name") or st.get("uses") or st.get("run", "")[:60]
                if "uses" in st:
                    how = "the fresh clone" if "checkout" in st["uses"] else uv_v
                    print(f"  step {label}: emulated ({how})")
                    continue
                if not job_ok:
                    print(f"  step {label}: skipped (an earlier step failed)")
                    continue
                t0 = time.time()
                r = subprocess.run(
                    ["bash", "-e", "-c", st["run"]],
                    cwd=clone,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=7200,
                    check=False,
                )
                n_step = len(list(logs.iterdir())) + 1
                (logs / f"{n_step:02d}-{name}.log").write_text(
                    f"$ {st['run']}\n# exit {r.returncode:d}\n{r.stdout}{r.stderr}", encoding="utf-8"
                )
                tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
                print(
                    f"  step {label}: `{st['run']}` -> exit {r.returncode:d} ({time.time() - t0:.0f}s)  {tail[0][:110]}"
                )
                job_ok = r.returncode == 0
            print(f"  JOB {name}: {'PASS' if job_ok else 'FAIL' + (' (allowed: continue-on-error)' if soft else '')}")
            if not job_ok and not soft:
                failed.append(name)
    finally:
        _rmtree(base)
    print(f"step logs: {logs.relative_to(ROOT).as_posix()}/")
    return _report("CI REPLAY", [f"job {j} failed" for j in failed])


# ----------------------------------------------------------------------------- certificate


def prior_goal_certified(n: int) -> bool:
    text = (HERE / "LEDGER.md").read_text(encoding="utf-8") if (HERE / "LEDGER.md").exists() else ""
    return re.search(rf"(?m)^\|\s*G{n - 1:d}\s*\|\s*(CERTIFIED|NO-GO|SKIPPED)\s*\|", text) is not None


def certify(goal: str, phase: str | None = None, drills: bool = False, tamper_only: bool = False) -> int:  # noqa: FBT001, RUF100  # positional flag kept: signature probed by the oracle (O5); FBT is ratchet-only
    n = goal_num(goal)
    if tamper_only:
        res = tamper(goal)
        failed = [t for t, (active, ok, _m) in res.items() if active and not ok]
        for t, (active, ok, msg) in res.items():
            print("{} {}{} -- {}".format(t, "PASS" if ok else "FAIL", "" if active else " (not yet active)", msg))
        return 1 if failed else 0

    data = load_checks(goal)
    checks = [c for c in data.get("check", []) if phase is None or c["phase"] == phase]
    passed = 0
    first_fail: str | None = None
    if n > 0 and not prior_goal_certified(n):
        # Goals run in order: a later goal's checks, tamper rules and oracle comparison are not
        # executed before its predecessor is certified (they would only measure work that does
        # not exist yet). Drills still run -- that is the G0.P5 self-test `certify.py G7 --drills`.
        print(
            f"CHECKS skipped: G{n - 1:d} is not CERTIFIED in tooling-upgrade/LEDGER.md, so {goal} has not "
            "started; only the drills run."
        )
        if drills:
            res = run_drills(goal)
            missed = sum(1 for v in res.values() if v.startswith("MISSED"))
            print(f"DRILLS: {len(res) - missed:d}/{len(res):d} BIT")
            print(f"DRILLS-MISSED {missed:d}/{len(res):d}")
        print(f"RESULT: {goal} NOT CERTIFIED: G{n - 1:d} not certified; {goal} not started")
        return 1
    superseded, sup_problems = supersessions(goal, data)
    for p in sup_problems:
        print("FAIL supersede --", p)
        first_fail = first_fail or "supersede: " + p
    for c in checks:
        ok, why, out = run_check(c)
        if c["id"] in superseded:
            # still run and shown, never counted: its successor carries the criterion
            print("SUPERSEDED {} by {} -- {} {}".format(c["id"], superseded[c["id"]], "pass" if ok else "fail", why))
            continue
        passed += ok
        print("{} {} -- {}".format("PASS" if ok else "FAIL", c["id"], why), flush=True)
        if not ok:
            print("    " + "\n    ".join(out.strip().splitlines()[-6:]))
            first_fail = first_fail or "check {} ({})".format(c["id"], why)
    counted = [c for c in checks if c["id"] not in superseded]
    sup_note = (
        " ({:d} superseded: {})".format(
            len(checks) - len(counted),
            ", ".join(f"{o} -> {n}" for o, n in superseded.items() if any(c["id"] == o for c in checks)),
        )
        if len(counted) < len(checks)
        else ""
    )

    if phase:
        # Phase self-check (plan 9: "certify.py G<n> --phase <id>"): that phase's pre-registered
        # checks only. T1-T7, the drills and the oracle belong to the goal-end certificate.
        print(
            "PHASE {}: {:d}/{:d} PASS{} (worktree clean: {}, branch ok: {})".format(
                phase,
                passed,
                len(counted),
                sup_note,
                "yes" if worktree_clean() else "no",
                "yes" if on_branch() else "no",
            )
        )
        ok_all = counted and passed == len(counted) and first_fail is None
        return 0 if ok_all and worktree_clean() and on_branch() else 1
    res = tamper(goal)
    t_fail = [t for t, (active, ok, _m) in res.items() if active and not ok]
    for t, (active, ok, msg) in res.items():
        print(
            "{} {}{} -- {}".format(
                t,
                "PASS" if ok else "FAIL",
                "" if active else f" (not yet active: binds from G{T_ACTIVE_FROM[t]:d})",
                msg,
            )
        )
    pending = [t for t, (active, _ok, _m) in res.items() if not active]

    required = data.get("required_drills", [])
    bit_count = 0
    drill_res: dict[str, str] = {}
    if drills:
        drill_res = run_drills(goal)
        missed = sum(1 for v in drill_res.values() if v.startswith("MISSED"))
        print(f"DRILLS-MISSED {missed:d}/{len(drill_res):d}")
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

    refusals: list[str] = []
    if not worktree_clean():
        refusals.append("worktree dirty")
    if not on_branch():
        refusals.append(f"HEAD not on {BRANCH}")
    hist = checks_history_problems()
    if hist:
        refusals.append("checks files changed after registration: " + hist[0])
    if cur is None:
        refusals.append("no full-suite record current for HEAD")
    if pushed():
        refusals.append("HEAD is on a remote branch (pushed)")

    head = git("rev-parse", "HEAD").strip()
    print("=== CERTIFICATE {}{} ===".format(goal, (" " + phase) if phase else ""))
    print(
        "HEAD {} | branch {} | worktree clean: {} | pushed: {}".format(
            head[:12],
            git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "yes" if worktree_clean() else "no",
            "yes" if pushed() else "no",
        )
    )
    print(f"CHECKS {passed:d}/{len(counted):d} PASS{sup_note}")
    print(
        "TAMPER T1-T7 {}{}".format(
            "PASS" if not t_fail else "FAIL ({})".format(", ".join(t_fail)),
            " (binding: {}; not yet active: {})".format(
                ", ".join(t for t in res if t not in pending), ", ".join(pending)
            )
            if pending
            else "",
        )
    )
    print(f"DRILLS {bit_count:d}/{len(required):d} BIT")
    print(f"ORACLE {k:d}/10 EQUAL")
    failure = (
        first_fail
        or (("tamper " + t_fail[0]) if t_fail else None)
        or (f"drills {bit_count:d}/{len(required):d} BIT" if bit_count < len(required) else None)
        or (None if oracle_ok else f"oracle {k:d}/10 EQUAL")
        or (refusals[0] if refusals else None)
    )
    print("RESULT: {} {}".format(goal, "CERTIFIED" if failure is None else "NOT CERTIFIED: " + failure))
    print("=== END CERTIFICATE ===")
    return 0 if failure is None else 1


def main(argv: Sequence[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and re.fullmatch(r"G[0-7]", argv[0]):
        p = argparse.ArgumentParser(prog="certify.py G<n>")
        p.add_argument("goal")
        p.add_argument("--phase")
        p.add_argument("--drills", action="store_true", help="also run all 15 bite drills")
        p.add_argument("--tamper-only", action="store_true", help="T1-T7 only (the D15 gate)")
        a = p.parse_args(argv)
        return certify(a.goal, a.phase, a.drills, a.tamper_only)
    p = argparse.ArgumentParser(prog="certify.py", description=cast("str", __doc__).split("\n\n")[0])
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
    sub.add_parser("assert-workflow-permissions", help="top-level permissions:, never write-all")
    sub.add_parser("assert-uv-settings", help="[tool.uv] carries the G1.P3 settings")
    s = sub.add_parser("assert-gate", help="poe gate: plan order, includes the given tasks")
    s.add_argument("members", nargs="*")
    s = sub.add_parser("assert-ratchet", help="stretch rule families never rise")
    s.add_argument("goal")
    sub.add_parser("assert-latent-regressions", help="latent-bug tests fail on parent, pass on HEAD")
    sub.add_parser("assert-types-config", help="[tool.basedpyright] per G4.P1, [tool.ty], no baseline")
    sub.add_parser("assert-strict-islands", help="G4.P3 files carry the strict pyright header")
    sub.add_parser("assert-suppressions", help="T3 (G4 strength) and T4: the gate's suppression step")
    s = sub.add_parser("assert-ledger-entry", help="LEDGER.md has a closed row for a phase")
    s.add_argument("phase")
    sub.add_parser("assert-docs-uv", help="docs present uv as the primary path")
    sub.add_parser("assert-ci-replay", help="replay every Linux CI job's run: steps in a fresh clone")
    sub.add_parser("assert-ci-structure", help="ci.yml: permissions, concurrency, pins, jobs (G5.P3)")
    sub.add_parser("assert-dependabot", help="dependabot.yml: uv + actions, weekly, cooldown, grouped")
    sub.add_parser("assert-precommit-config", help=".pre-commit-config.yaml per G5.P2; no prek install")
    sub.add_parser("assert-experiments", help="G5.P1 verdicts recorded and matched by the config")
    sub.add_parser("assert-generated-docs", help="generators change nothing at HEAD; --check passes")
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
        "assert-workflow-permissions": cmd_assert_workflow_permissions,
        "assert-latent-regressions": cmd_assert_latent_regressions,
        "assert-types-config": cmd_assert_types_config,
        "assert-strict-islands": cmd_assert_strict_islands,
        "assert-suppressions": cmd_assert_suppressions,
        "assert-ledger-entry": cmd_assert_ledger_entry,
        "assert-docs-uv": cmd_assert_docs_uv,
        "assert-ci-replay": cmd_assert_ci_replay,
        "assert-ci-structure": cmd_assert_ci_structure,
        "assert-dependabot": cmd_assert_dependabot,
        "assert-precommit-config": cmd_assert_precommit_config,
        "assert-experiments": cmd_assert_experiments,
        "assert-generated-docs": cmd_assert_generated_docs,
    }[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
