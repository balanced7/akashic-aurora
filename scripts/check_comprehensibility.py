"""check_comprehensibility -- one guard that keeps the comprehension layer honest.

PRINCIPLES.md #4 (Guards over discipline) applied to the DOCS themselves. The ARCHITECTURE map,
the LEXICON, and the auto-index all rotted once because nothing enforced their freshness -- which is
exactly how a system stops being understandable. This is the enforcement.

Run it before shipping (wire into ship.py). Exit 1 on FAIL (objective drift you must fix), 0 otherwise.

  A. Every core/ subpackage is named in docs/ARCHITECTURE.md   FAIL  (the drift that actually happened)
  B. docs/MODULE_INDEX.md is current                           FAIL  (run gen_arch_index.py)
  C. Every module has a line-1 docstring                       WARN  (no docstring => breaks the index
                                                                       and can't state its one job)
  D. ARCHITECTURE.md / LEXICON.md far older than core/         WARN  (probably stale -- review)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gen_arch_index as gen  # reuse the same module survey (single source of truth)

STALE_DAYS = 14


def _read(rel):
    try:
        return open(os.path.join(ROOT, rel), encoding="utf-8").read()
    except Exception:
        return ""


def _newest_core_mtime():
    newest = 0.0
    for dp, _dn, fn in os.walk(os.path.join(ROOT, "core")):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f.endswith(".py"):
                newest = max(newest, os.path.getmtime(os.path.join(dp, f)))
    return newest


def main():
    fails, warns = [], []
    arch = _read("docs/ARCHITECTURE.md")
    subs = sorted(d for d in os.listdir(os.path.join(ROOT, "core"))
                  if os.path.isdir(os.path.join(ROOT, "core", d)) and not d.startswith("__"))

    # A. every subpackage named in the map
    missing = [s for s in subs if f"core/{s}" not in arch]
    if missing:
        fails.append(f"ARCHITECTURE.md is missing core/ subpackage(s): {', '.join(missing)} "
                     f"-> add one line each (a new subsystem the map doesn't know about)")

    # B. the auto-index is current
    if _read("docs/MODULE_INDEX.md").strip() != gen.render().strip():
        fails.append("docs/MODULE_INDEX.md is stale -> run `py scripts/gen_arch_index.py`")

    # C. docstring coverage (line-1 responsibility)
    nodoc = [f"core/{s}/{m}" for s in subs for m in gen.modules(f"core/{s}")
             if gen.first_doc(os.path.join(ROOT, "core", s, m)) == "(no docstring)"]
    if nodoc:
        warns.append(f"{len(nodoc)} module(s) have no line-1 docstring: "
                     + ", ".join(nodoc[:8]) + ("…" if len(nodoc) > 8 else ""))

    # D. comprehension-doc age vs the newest core change
    nc = _newest_core_mtime()
    for doc in ("docs/ARCHITECTURE.md", "docs/LEXICON.md"):
        p = os.path.join(ROOT, doc)
        if os.path.exists(p) and os.path.getmtime(p) < nc - STALE_DAYS * 86400:
            warns.append(f"{doc} is >{STALE_DAYS}d older than the newest core/ change -> review for drift")

    for w in warns:
        print("WARN:", w)
    for f in fails:
        print("FAIL:", f)
    if fails:
        print(f"\n{len(fails)} FAIL, {len(warns)} WARN -- the map has drifted from the code. Fix before shipping.")
        return 1
    print(f"PASS: the comprehension layer matches the code ({len(warns)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
