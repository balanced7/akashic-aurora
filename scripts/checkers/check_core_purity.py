"""check_core_purity -- the Local-in-Core RATCHET (modular-core detangle, phase 1; attack B).

THE RULE THIS TURNS INTO A GATE
-------------------------------
The Core rule is "never names a seat, a path, a port, or a fork" -- a fork must be able to take
Core without being told who we are. Stated as a rule it is checkable; stated as a preference it
is decoration. This checker counts the four literal classes per file and compares the tree
against a COMMITTED baseline.

WHY IT IS A RATCHET AND NOT A FLAG DAY
--------------------------------------
The door script alone carried 229 hits when this landed, and `core/fleet/seat_launchers.py` 118.
Blocking every commit on the whole debt would have been a rule that gets reverted within a day
(the file's own lesson, from `check_wiring`'s EXCEPTIONS expiry block). So today's tree is FROZEN
and the gate enforces the direction: counts may fall, never rise. Freezing debt is not the same
as accepting it -- the baseline carries the totals and the top offenders, so the trend is a
number someone can be asked about rather than a claim someone can forget.

THREE RULES, and the second is the one that is easy to get wrong:
  1. A MISSING BASELINE IS A REFUSAL (exit 2), never a pass. If the baseline cannot be read, the
     tree's debt is UNKNOWN -- and a gate that reads unknown as zero is the exact failure shape
     this house keeps paying for. Same for an unparseable or wrong-shaped baseline.
  2. THE PER-FILE RULE DOES NOT PUNISH A NEW FILE -- the TOTAL rule does. Extracting a verb body
     out of `agent_cli.py` into `verbs/` moves literals between files without creating any. A
     per-file rule applied to an unseen file would either forbid the extraction outright or push
     the values somewhere the gate cannot see. So: every file in the baseline may not rise, and
     the SUM over the whole Core surface may not rise. Headroom created by removing a literal can
     be spent anywhere -- which is what makes the ratchet usable and still strictly monotone.
  3. A DROP IS REPORTED, NOT REQUIRED. When counts fall the gate says so and asks the author to
     re-freeze (`--write-baseline`), because a baseline that keeps stale headroom slowly hands the
     next author an unearned allowance -- the amnesty-by-attrition the house has recorded twice.

WHAT IT WILL NOT DO
-------------------
It does not judge prose. Counts come from raw source text, so a docstring that says "claude" is
counted, exactly as the phase-0 census counted it. That keeps the numbers comparable across the
two measurements and keeps the gate one cheap regex pass. A future refinement could weight code
above prose; it would change what "229" means, so it is a decision to take deliberately, with a
re-baseline, not a quiet improvement.

Run:  py scripts/checkers/check_core_purity.py                  # BOTH surfaces (the gate)
      py scripts/checkers/check_core_purity.py --report         # per-file table (all files)
      py scripts/checkers/check_core_purity.py --write-baseline  # re-freeze (author's act)
      py scripts/checkers/check_core_purity.py --baseline PATH   # alternate Core baseline (tests)
      py scripts/checkers/check_core_purity.py --local-baseline PATH # alternate local baseline
      PURITY_SURFACE=local py scripts/checkers/check_core_purity.py  # one surface only

TWO SURFACES, TWO QUESTIONS (Rill's A1, 2026-10-31). The Core surface asks "does Core know who we
are"; the LOCAL surface asks the complementary question about the files that are ALLOWED to know:
`local/`, `arsenal/panel/` and `scripts/phone/` are committed to a PUBLIC repo, so they may carry
this deployment's SHAPE and never this machine's ADDRESS or a home path. The local surface has its
own class set (tailnet address, LAN address, home path), its own scope and its own baseline, and an
honest freeze of ZERO -- those values now live in the private profile (`akashic-local/profile/`),
which `core/local.py` lays over the public file at read time. Same three rules, same refusal on a
missing baseline: a gate that runs half of itself on a fresh clone is the failure both baselines
exist to prevent.

Provenance: the four regex classes are the phase-0 census's own patterns
(research/in-flight/modular-core-2026-10-30/census.py, Heimdall 2026-10-30), reused verbatim so
this gate's numbers are the census's numbers. Attack B is Rill's (dsh_agent), 2026-09-17:
"Local-in-Core is a CLASS, so sweep it mechanically instead of naming it."
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "core_purity_baseline.json")

# --- the four Local-in-Core shapes (census.py, verbatim) -----------------------------------
SEAT_IDS = re.compile(
    r"\b(?:deepseek|claude|kimi|grok|sol|vandor|dsh_agent|rill|serge|novac|r2|"
    r"sunshine|zadkiel|navi|heimdall|codex|arturia|chronos|duck|rook|onyx)\b",
    re.IGNORECASE)
ABS_PATH = re.compile(r"\b[CDE]:\\|/(?:home|Users|usr)/|C:\\Users|E:\\AI-Setup", re.IGNORECASE)
PORT = re.compile(r"\b(?<![\w.])(?:87\d\d|89\d\d|1[0-9]{4}|3000|4000|5000|6379|8000|8080)\b")
FORK = re.compile(r"\bserge\b|\bfleet\b|\bDSH\b|\b$DSH_HOME\b", re.IGNORECASE)

CLASSES = (("seat", SEAT_IDS), ("path", ABS_PATH), ("port", PORT), ("fork", FORK))

# The Core surface this gate governs. `verbs/` is here from birth on purpose: the whole point of
# the extraction is that the new home is Core code, so it must be held to the Core rule from its
# first commit rather than exempted as "new".
SCOPE_FILES = ("agent_cli.py",)
SCOPE_DIRS = ("core", "verbs")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".mypy_cache", ".pytest_cache"}


# ==================================================================================================
# THE SECOND SURFACE: MACHINE VALUES IN THE LOCAL / PANEL PLANE (Rill's A1, 2026-10-31)
# ==================================================================================================
# The Core surface above asks "does Core know who we are". This one asks the complementary
# question about the files that ARE allowed to know: `local/` and the phone panel's public code are
# committed to a PUBLIC repo, so they may carry the SHAPE of this deployment and never the address
# of this machine. A tailnet address is routable; a home path names a person's account. Both were
# found headed for the public remote by a pre-push scan on 2026-10-31, which is the fact this gate
# exists to make checkable rather than luck.
#
# It is a DIFFERENT class set on purpose -- the Core surface's "seat" and "port" classes would flag
# local/operator_ids and every loopback port, which are exactly what those files are FOR. Two
# surfaces, two questions, two baselines; one entry point, so a ship step cannot run half of it.
TAILNET_IP = re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
LAN_IP = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
HOME_PATH = re.compile(
    # `[\\/]+` on BOTH sides of Users on purpose: a path inside a JSON file arrives escaped
    # (`C:\\Users\\someone`), which is two backslashes, and a single-separator pattern misses
    # exactly the shape that reaches a public repo through a committed .json.
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'`,;:]+"
    r"|(?<![\w.])/(?:home|Users)/[A-Za-z0-9._-]+")

MACHINE_CLASSES = (("tailnet", TAILNET_IP), ("lan", LAN_IP), ("home", HOME_PATH))

#: What the local surface governs: the committed Local data, the panel's public code and assets, and
#: the phone-side scripts that talk to this PC. Deliberately NOT docs/ -- prose may quote an example
#: address to explain a rule, and a gate that forbids ever naming an IP is a gate someone turns off.
LOCAL_SCOPE_DIRS = ("local", "arsenal/panel", "scripts/phone")
LOCAL_SUFFIXES = (".json", ".py", ".ps1", ".sh", ".js", ".html", ".css", ".webmanifest", ".svg")
LOCAL_BASELINE_NAME = "local_purity_baseline.json"
LOCAL_BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOCAL_BASELINE_NAME)


# ------------------------------------------------------------------------------- measurement
def count_text(text):
    """{class: count} for one blob of source text. All four classes, always all four keys."""
    return {name: len(rx.findall(text)) for name, rx in CLASSES}


def total_of(counts, classes=None):
    return sum(counts.get(name, 0) for name, _rx in (classes or CLASSES))


# ------------------------------------------------------------------- the local surface's halves
def count_machine(text):
    """{class: count} for one blob of the LOCAL surface: tailnet address, LAN address, home path."""
    return {name: len(rx.findall(text)) for name, rx in MACHINE_CLASSES}


def _local_scan_paths(root=ROOT):
    """Every governed file of the local surface, as repo-relative posix paths."""
    out = []
    for d in LOCAL_SCOPE_DIRS:
        base = os.path.join(root, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(x for x in dirnames if x not in SKIP_DIRS)
            for fn in sorted(filenames):
                if fn.endswith(LOCAL_SUFFIXES):
                    full = os.path.join(dirpath, fn)
                    out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(set(out))


def measure_local(root=ROOT):
    """{file: {tailnet, lan, home, total}} over the local/panel surface."""
    files = {}
    for rel in _local_scan_paths(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        counts = count_machine(text)
        if total_of(counts, MACHINE_CLASSES):
            counts["total"] = total_of(counts, MACHINE_CLASSES)
            files[rel] = counts
    return files


def snapshot_local(files):
    """The baseline document for the local surface."""
    return {
        "_what": "The frozen count of MACHINE VALUES (tailnet address, LAN address, home path) in "
                 "the PUBLIC local/panel surface. scripts/checkers/check_core_purity.py enforces "
                 "the direction: counts may FALL, never rise.",
        "_why": "A tailnet address is a routable address for one machine and a home path names a "
                "person's account; `local/`, arsenal/panel and scripts/phone are all committed to "
                "a PUBLIC repo. Both were found headed for the public remote by the 2026-10-31 "
                "pre-push scan, so this is a gate rather than a habit. The honest freeze here is "
                "ZERO -- these values belong in the private profile "
                "(akashic-local/profile/), read through core/local.py's overlay.",
        "_classes": {name: rx.pattern for name, rx in MACHINE_CLASSES},
        "_scope": {"dirs": list(LOCAL_SCOPE_DIRS), "suffixes": list(LOCAL_SUFFIXES)},
        "total": total_of({k: sum(f.get(k, 0) for f in files.values()) for k, _ in MACHINE_CLASSES},
                          MACHINE_CLASSES),
        "by_class": {name: sum(f.get(name, 0) for f in files.values()) for name, _ in MACHINE_CLASSES},
        "files": {rel: {name: f.get(name, 0) for name, _ in MACHINE_CLASSES}
                  for rel, f in sorted(files.items())},
    }


def _scan_paths(root=ROOT):
    """Every Core-surface .py file, as repo-relative posix paths."""
    out = []
    for rel in SCOPE_FILES:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            out.append(rel)
    for d in SCOPE_DIRS:
        base = os.path.join(root, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(x for x in dirnames if x not in SKIP_DIRS)
            for fn in sorted(filenames):
                if fn.endswith(".py"):
                    full = os.path.join(dirpath, fn)
                    out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(set(out))


def measure(root=ROOT):
    """{file: {seat, path, port, fork, total}} over the Core surface."""
    files = {}
    for rel in _scan_paths(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        counts = count_text(text)
        if total_of(counts):
            counts["total"] = total_of(counts)
            files[rel] = counts
    return files


def snapshot(files):
    """The baseline document for a measurement."""
    return {
        "_what": "The frozen Local-in-Core debt for the Core surface, per file. "
                 "scripts/checkers/check_core_purity.py enforces the direction: counts may FALL, "
                 "never rise. Re-freeze with --write-baseline when they fall.",
        "_why": "The door script carried 229 of these on 2026-10-30 and the brief that asked for "
                "this gate also said not to clean them now: freeze them so they can only go "
                "down. A missing baseline is UNKNOWN, not zero, so the checker refuses rather "
                "than passes when this file is gone.",
        "_classes": {name: rx.pattern for name, rx in CLASSES},
        "_scope": {"files": list(SCOPE_FILES), "dirs": list(SCOPE_DIRS), "suffix": ".py"},
        "total": total_of({k: sum(f.get(k, 0) for f in files.values()) for k, _ in CLASSES}),
        "by_class": {name: sum(f.get(name, 0) for f in files.values()) for name, _ in CLASSES},
        "files": {rel: {name: f.get(name, 0) for name, _ in CLASSES}
                  for rel, f in sorted(files.items())},
    }


def compare(current, baseline, classes=None, what="Local-in-Core"):
    """-> (failures, drops, new_files) for a measurement against a baseline document.

    PURE, so the ratchet can be drilled without touching the tree. `failures` are [(kind, detail)]
    and an empty list means the tree is at or below the frozen debt. `classes` defaults to the Core
    set so every existing caller and pin keeps its meaning; the local surface passes its own.
    """
    classes = classes or CLASSES
    base_files = baseline.get("files") or {}
    base_total = baseline.get("total")
    if not isinstance(base_total, int):
        base_total = sum(total_of(v, classes) for v in base_files.values())

    cur_total = total_of({k: sum(f.get(k, 0) for f in current.values()) for k, _ in classes}, classes)
    failures, drops = [], []

    for rel, counts in sorted(current.items()):
        before = base_files.get(rel)
        if before is None:
            continue                                  # new file: governed by the TOTAL rule
        for name, _rx in classes:
            now, was = counts.get(name, 0), before.get(name, 0)
            if now > was:
                failures.append((
                    "file",
                    f"{rel}: {name} literals ROSE {was} -> {now} (+{now - was})"))
    for rel, before in sorted(base_files.items()):
        now = current.get(rel)
        if now is None:
            continue
        for name, _rx in classes:
            was, cur = before.get(name, 0), now.get(name, 0)
            if cur < was:
                drops.append(f"{rel}: {name} {was} -> {cur}")

    if cur_total > base_total:
        failures.append((
            "total",
            f"{what} TOTAL rose {base_total} -> {cur_total} "
            f"(+{cur_total - base_total}) across the surface"))

    new_files = sorted(set(current) - set(base_files))
    return failures, drops, new_files


def load_baseline(path=BASELINE_PATH, label="Core-purity"):
    """The committed freeze, or a legible REFUSAL. Never an empty baseline.

    Exit code 2 (not 1) is deliberate: 1 means "the tree is over the line", 2 means "this checker
    cannot answer". Collapsing them would let a broken install read as a clean tree that happens
    to have failed once.
    """
    if not os.path.isfile(path):
        sys.stderr.write(
            f"REFUSED: the {label} baseline is MISSING ({path}).\n"
            "         A missing baseline is UNKNOWN debt, not zero debt -- this gate will not "
            "grade a tree it has no line for.\n"
            "         Restore the file (it is committed), or re-freeze deliberately with "
            "--write-baseline and say why in the commit message.\n")
        raise SystemExit(2)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"REFUSED: the {label} baseline is UNREADABLE ({path}): {exc}\n"
                         "         Unknown is not zero: fix or re-freeze the baseline.\n")
        raise SystemExit(2)
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        sys.stderr.write(
            f"REFUSED: the {label} baseline at {path} has no 'files' object -- it exists but "
            "does not answer the question this gate asks.\n")
        raise SystemExit(2)
    return data


# -------------------------------------------------------------------------------------- gate
def _run_surface(kind, root, baseline_path, report, write):
    """One surface's gate. Returns (exit_code, summary_line). Raises SystemExit(2) on a refusal.

    `kind` is "core" or "local". The two surfaces share this body so neither can quietly acquire a
    laxer rule than the other -- the ONLY differences are the class set, the scope and the baseline.
    """
    if kind == "local":
        current = measure_local(root)
        classes, label, what = MACHINE_CLASSES, "local-surface (machine values)", "machine-value"
    else:
        current = measure(root)
        classes, label, what = CLASSES, "Core-purity", "Local-in-Core"

    if write:
        doc = snapshot_local(current) if kind == "local" else snapshot(current)
        with open(baseline_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=2, sort_keys=False)
            fh.write("\n")
        print(f"# {label} baseline WRITTEN -> {baseline_path}")
        print(f"  total {doc['total']}  "
              f"({', '.join(f'{k}={v}' for k, v in doc['by_class'].items())})  "
              f"over {len(doc['files'])} file(s)")
        return 0, ""

    baseline = load_baseline(baseline_path, label=label)
    failures, drops, new_files = compare(current, baseline, classes, what)

    cur_total = sum(total_of(v, classes) for v in current.values())
    base_total = baseline.get("total")
    if not isinstance(base_total, int):
        base_total = sum(total_of(v, classes) for v in (baseline.get("files") or {}).values())
    cur_by_class = {name: sum(f.get(name, 0) for f in current.values()) for name, _ in classes}

    if report:
        print(f"# {label} -- {len(current)} file(s) over the line")
        print(f"  total {cur_total} (baseline {base_total})   "
              + "   ".join(f"{k}={v}" for k, v in cur_by_class.items()))
        print("\n## per-file, worst first")
        for rel, counts in sorted(current.items(), key=lambda kv: -total_of(kv[1], classes))[:40]:
            was = (baseline.get("files") or {}).get(rel)
            delta = "" if was is None else (
                f"  (was {total_of(was, classes)}, "
                f"{total_of(counts, classes) - total_of(was, classes):+d})")
            flags = "  ".join(f"{name}{counts.get(name, 0)}" for name, _ in classes)
            print(f"  {rel:<58} {total_of(counts, classes):>4}   {flags}{delta}")

    for rel in new_files:
        print(f"NOTE[{kind}]: '{rel}' is new since the freeze and counts into the total "
              f"({total_of(current[rel], classes)} literal(s))")
    for d in drops:
        print(f"NOTE[{kind}]: debt paid down -- {d}")

    if failures:
        for _kind, detail in failures:
            print(f"FAIL[{kind}]: {detail}")
        if kind == "local":
            print(f"\n{len(failures)} regression(s). This surface is a RATCHET with an honest "
                  "freeze of ZERO: a tailnet/LAN address or a home path may never enter the public "
                  "local/panel tree. Put the value in the private profile "
                  "(akashic-local/profile/<file>.json, read by core/local.py's overlay) and leave a "
                  "null or a ${INSTANCE_ROOT} derivation here.")
        else:
            print(f"\n{len(failures)} regression(s). This gate is a RATCHET: Local-in-Core may "
                  "fall, never rise. Move the value into local/ (one loader: core/local.py) instead "
                  "of adding a literal to Core, or explain in the commit why this one is "
                  "irreducible.")
        return 1, ""
    if drops and not report:
        print(f"\n{len(drops)} count(s) went DOWN -- re-freeze with --write-baseline so the next "
              "author inherits the real debt, not stale headroom.")
    return 0, (f"PASS: {what} at or below the frozen baseline "
               f"({cur_total} <= {base_total} over {len(current)} file(s)).")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    baseline_path = BASELINE_PATH
    local_baseline_path = LOCAL_BASELINE_PATH
    if "--baseline" in argv:
        i = argv.index("--baseline")
        try:
            baseline_path = argv[i + 1]
        except IndexError:
            sys.stderr.write("ERROR: --baseline needs a path\n")
            return 2
        del argv[i:i + 2]
    if "--local-baseline" in argv:
        i = argv.index("--local-baseline")
        try:
            local_baseline_path = argv[i + 1]
        except IndexError:
            sys.stderr.write("ERROR: --local-baseline needs a path\n")
            return 2
        del argv[i:i + 2]

    report = "--report" in argv or "--verbose" in argv
    write = "--write-baseline" in argv
    runner = os.environ.get("PURITY_SURFACE", "").strip().lower()
    if runner not in ("core", "local"):
        runner = "both"                            # the default: a ship step cannot run half of it

    codes = []
    summaries = []
    if runner in ("core", "both"):
        code, line = _run_surface("core", ROOT, baseline_path, report, write)
        codes.append(code)
        summaries.append(line)
    if runner in ("local", "both"):
        code, line = _run_surface("local", ROOT, local_baseline_path, report, write)
        codes.append(code)
        summaries.append(line)

    if write:
        return 0
    for line in summaries:
        if line:
            print(line)
    if 1 in codes:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
