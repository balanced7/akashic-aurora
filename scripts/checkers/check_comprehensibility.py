"""check_comprehensibility -- the guard that keeps the comprehension layer honest (the immune system).

PRINCIPLES.md #4 (Guards over discipline) applied to the DOCS themselves. The ARCHITECTURE map, the
LEXICON, and the auto-index rotted once because nothing enforced their freshness -- which is exactly
how a system stops being understandable, after which every downstream decision drifts. This is the
enforcement. Four properties (design: docs/library/design/20260701_the-comprehensibility-immune-system-desi_339b01.md):
  COMPLETE (catches the drift that happens) · UNBYPASSABLE (CI + pre-commit hook + ship all run it) ·
  TRUSTWORTHY (tests/test_comprehensibility.py injects each drift class + proves the guard FAILs) ·
  NON-EVADABLE (exemptions are time-bound: an expired `rot-ok` is itself a failure).

Run before shipping (wired into ship.py, CI, and the pre-commit hook). Exit 1 on FAIL, 0 otherwise.

  A. Every core/ subpackage is named in docs/ARCHITECTURE.md          FAIL
  B. docs/MODULE_INDEX.md is current (run gen_arch_index.py)          FAIL
  B2. PHYSICS.md + MAP.md + DOORS.md current (their generators)       FAIL  (a derived map that rots is worse than none)
  F. No living doc / core docstring cites a repo path that's GONE     FAIL  (stale reference -- rename/delete rot)
  G. Every tracked file's on-disk case matches git (cross-OS safe)    FAIL  (the lexicon.md vs LEXICON.md class)
  C. Every module has a line-1 docstring                              WARN
  D. ARCHITECTURE.md / LEXICON.md far older than core/                WARN
  E. Every UPPERCASE living doc is in the docs map (INDEX.md)         WARN
  X. A CHECK ITSELF CRASHED                                           FAIL  (a broken guard is false-green -- fail LOUD)

`--fast` runs only F+G (the cheap stat-based drift checks) for the pre-commit hook; ship/CI run all.
"""
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth
sys.path.insert(0, os.path.join(ROOT, "scripts", "generators"))  # T104-M1
import gen_arch_index as gen  # reuse the same module survey (single source of truth)

STALE_DAYS = 14

# Repo roots a doc/docstring reference is checked against. A path token is only treated as a
# repo-relative reference when one of these is at the START of the token (root-anchored) -- so a
# deployment/example path like `aurora/agent/harness/hooks/x.py` is NOT mis-read as `agent/harness/hooks/x.py`.
_REF_ROOTS = ("core", "scripts", "tests", "agent", "context", "infrastructure", "security", "docs")
# start-anchored: preceded by a non-path char; ends in a known code/doc/asset extension.
_REF_RE = re.compile(
    r"(?<![\w./-])(" + "|".join(_REF_ROOTS) + r")(/[\w./-]+?\.(?:py|md|json|jsonl|yml|yaml|txt|toml|cfg|ini|sh))",
    re.IGNORECASE,
)

# NON-EVADABLE exemptions: a stale ref is excused ONLY by a dated entry here. `expires` is a hard date;
# past it the entry itself becomes a FAIL ("re-verify or remove") so the allowlist can't rot into a
# silent dumping ground. Keep this SMALL -- root-anchoring already excludes most false positives.
REF_ALLOWLIST = {
    # "some/path.py": {"expires": "2026-12-31", "reason": "why this ref is legitimately not on disk"},
    "docs/security-amendment-deepseek-scoped-admin-2026-07-22.md": {
        "expires": "2026-08-23",
        "reason": "P3 migration 2026-07-23: the path survives as PROSE inside atom titles "
                  "rendered into generated maps; resolves via store/docs/migration_map.json. "
                  "Expires with the A2 library-lint reference pass.",
    },
}


def _read(rel):
    try:
        return open(os.path.join(ROOT, rel), encoding="utf-8").read()
    except Exception:
        return ""


def _living_docs():
    """UPPERCASE docs/*.md (the living-doc convention) + the hand-maintained root docs."""
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, "docs"))):
        if f.endswith(".md") and f == f.upper().replace(".MD", ".md") and f[0].isupper():
            out.append(f"docs/{f}")
    for f in ("AGENTS.md", "CLAUDE.md", "README.md", "bootstrap.md"):
        if os.path.exists(os.path.join(ROOT, f)):
            out.append(f)
    return out


def _newest_core_mtime():
    newest = 0.0
    for dp, _dn, fn in os.walk(os.path.join(ROOT, "core")):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f.endswith(".py"):
                newest = max(newest, os.path.getmtime(os.path.join(dp, f)))
    return newest


def _core_docstring_sources():
    """(rel, text) for every core/ module's docstring -- so a docstring that name-lies about a
    renamed/deleted sibling (`see core/old.py`) is caught by the same stale-ref check (DeepSeek Q4)."""
    out = []
    for sub in sorted(d for d in os.listdir(os.path.join(ROOT, "core"))
                      if os.path.isdir(os.path.join(ROOT, "core", d)) and not d.startswith("__")):
        for m in gen.modules(f"core/{sub}"):
            p = os.path.join(ROOT, "core", sub, m)
            try:
                import ast
                doc = ast.get_docstring(ast.parse(open(p, encoding="utf-8").read())) or ""
            except Exception:
                doc = ""
            if doc:
                out.append((f"core/{sub}/{m}", doc))
    return out


# ---- F: stale repo-path references (rename/delete rot) ---------------------------------------------

def scan_refs(text):
    """Root-anchored repo-path references found in `text` (deduped, order-stable, normalized). Pure +
    side-effect-free so the guard's own logic is unit-testable. Root-anchoring is what keeps deployment/
    example paths (`aurora/scripts/x.py`) from being mis-read as repo refs (`scripts/x.py`)."""
    out, seen = [], set()
    for m in _REF_RE.finditer(text or ""):
        ref = (m.group(1) + m.group(2)).replace("\\", "/").rstrip(").,:;\"'`]")
        if ref.lower() not in seen:
            seen.add(ref.lower())
            out.append(ref)
    return out


def exemption_active(ref, today):
    """True iff `ref` has an UNEXPIRED REF_ALLOWLIST exemption (non-evadable: expired => not active)."""
    al = REF_ALLOWLIST.get(ref)
    return bool(al and str(al.get("expires", "")) >= today)


def _stale_refs():
    """FAIL list: every repo-anchored path reference (in living docs + core docstrings) that no longer
    exists on disk and is not covered by an unexpired REF_ALLOWLIST entry. Also FAILs an EXPIRED
    allowlist entry (non-evadable). Root-anchored so deployment/example paths don't false-positive."""
    fails = []
    today = datetime.now().strftime("%Y-%m-%d")

    # expired exemptions are themselves failures (the allowlist must not rot)
    for ref, meta in REF_ALLOWLIST.items():
        if str(meta.get("expires", "")) < today:
            fails.append(f"stale-ref exemption EXPIRED for '{ref}' (expired {meta.get('expires')}) "
                         f"-> re-verify the reference and remove or renew the allowlist entry")

    sources = [(d, _read(d)) for d in _living_docs()] + _core_docstring_sources()
    for rel, text in sources:
        for ref in scan_refs(text):
            if os.path.exists(os.path.join(ROOT, ref)) or exemption_active(ref, today):
                continue
            fails.append(f"{rel} references a repo path that does not exist: '{ref}' "
                         f"-> fix the reference (renamed/deleted?) or add a dated REF_ALLOWLIST entry")
    return fails


# ---- G: filename case-canonicalization (cross-OS; the lexicon.md vs LEXICON.md class) --------------

def case_mismatches(paths, list_dir):
    """Pure: given tracked rel-paths + a `list_dir(reldir)->set(entries)` fn, return (rel, actual_or_None)
    for every path whose exact-case basename is absent from its directory listing (i.e. case drift).
    Side-effect-free so G is unit-testable without touching git."""
    out, cache = [], {}
    for rel in paths:
        d, base = os.path.split(rel)
        if d not in cache:
            cache[d] = list_dir(d)
        if base not in cache[d]:
            actual = [f for f in cache[d] if f.lower() == base.lower()]
            out.append((rel, (d + "/" + actual[0]) if actual else None))
    return out


def _filename_case():
    """FAIL list: every git-TRACKED file under a code/doc root whose exact case differs from its
    on-disk directory entry. Case-insensitive filesystems (Windows/macOS) hide this locally; it ships
    and breaks case-sensitive CI (Linux) or half-commits (git pathspecs are case-sensitive)."""
    try:
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", *_REF_ROOTS],
                                 capture_output=True, text=True)
        paths = [p for p in tracked.stdout.split("\0") if p]
    except Exception as e:
        return [f"could not list git-tracked files for the case check: {type(e).__name__}: {e}"]

    def _list(reldir):
        try:
            return set(os.listdir(os.path.join(ROOT, reldir)))
        except Exception:
            return set()

    return [f"filename case mismatch: git tracks '{rel}' but on disk it is '{actual or '(missing)'}' "
            f"-> canonicalize the case (git mv via a temp name) so it survives case-sensitive CI"
            for rel, actual in case_mismatches(paths, _list)]


# ---- the existing structural checks (A/B/C/D/E), unchanged in intent ------------------------------

def _subpackages_in_arch(arch, subs):
    return [f"ARCHITECTURE.md is missing core/ subpackage(s): {', '.join(m)} -> add one line each "
            f"(a new subsystem the map doesn't know about)"
            for m in [[s for s in subs if f"core/{s}" not in arch]] if m]


def _index_current():
    return ([] if _read("docs/MODULE_INDEX.md").strip() == gen.render().strip()
            else ["docs/MODULE_INDEX.md is stale -> run `py scripts/generators/gen_arch_index.py`"])


def _derived_docs_current():
    """B2: the OTHER auto-generated maps (PHYSICS.md bounds/flags, MAP.md census) share
    MODULE_INDEX's immune property -- a projection that silently rots is worse than none.
    Reuse each generator's OWN render (single source of truth); strip PHYSICS's derived-at
    sha line (a moved HEAD is not staleness -- the generator's --check strips it identically)."""
    out = []
    try:
        import gen_physics_sheet as phys
        strip = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("> Derived at "))
        if strip(_read("docs/PHYSICS.md")) != strip(phys.render(*phys.scan(), sha="_")):
            out.append("docs/PHYSICS.md is stale -> run `py scripts/generators/gen_physics_sheet.py`")
    except Exception as e:
        out.append(f"docs/PHYSICS.md check could not run ({type(e).__name__}: {e})")
    try:
        import gen_master_map as mapgen
        if _read("docs/MAP.md") != mapgen.render(mapgen.build()):
            out.append("docs/MAP.md is stale -> run `py scripts/generators/gen_master_map.py`")
    except Exception as e:
        out.append(f"docs/MAP.md check could not run ({type(e).__name__}: {e})")
    try:
        import gen_doors
        if _read("docs/DOORS.md") != gen_doors.render(gen_doors.cli_verbs()):
            out.append("docs/DOORS.md is stale -> run `py scripts/generators/gen_doors.py`")
    except Exception as e:
        out.append(f"docs/DOORS.md check could not run ({type(e).__name__}: {e})")
    return out


def _docstring_coverage(subs):
    nodoc = [f"core/{s}/{m}" for s in subs for m in gen.modules(f"core/{s}")
             if gen.first_doc(os.path.join(ROOT, "core", s, m)) == "(no docstring)"]
    return ([f"{len(nodoc)} module(s) have no line-1 docstring: " + ", ".join(nodoc[:8])
             + ("…" if len(nodoc) > 8 else "")] if nodoc else [])


def _doc_age():
    warns, nc = [], _newest_core_mtime()
    for doc in ("docs/ARCHITECTURE.md", "docs/LEXICON.md", "docs/INDEX.md"):
        p = os.path.join(ROOT, doc)
        if os.path.exists(p) and os.path.getmtime(p) < nc - STALE_DAYS * 86400:
            warns.append(f"{doc} is >{STALE_DAYS}d older than the newest core/ change -> review for drift")
    return warns


def _living_docs_indexed():
    index = _read("docs/INDEX.md")
    unlisted = [f for f in _living_docs() if f.startswith("docs/") and os.path.basename(f) not in index
                and os.path.basename(f) != "INDEX.md"]
    return ([f"living doc(s) not in the docs map (INDEX.md): {', '.join(unlisted)} "
             f"-> add them, or rename to lowercase if they're just history"] if unlisted else [])


def _run(label, fn, *a):
    """Run a check crash-safely: an EXCEPTION in the check is a FAIL (loud), never a silent pass -- a
    broken guard that returns green is the false-confidence cascade this whole system exists to prevent."""
    try:
        return fn(*a), None
    except Exception as e:
        import traceback
        return [], f"CHECK '{label}' CRASHED ({type(e).__name__}: {e}) -> the guard itself is broken, " \
                   f"fix it (a crashing check must never pass silently).\n" + traceback.format_exc()


def main():
    fast = "--fast" in sys.argv
    arch = _read("docs/ARCHITECTURE.md")
    subs = sorted(d for d in os.listdir(os.path.join(ROOT, "core"))
                  if os.path.isdir(os.path.join(ROOT, "core", d)) and not d.startswith("__"))

    fails, warns, broken = [], [], []
    # FAIL checks. --fast (pre-commit hook) runs only the cheap stat-based drift checks (F, G).
    fail_checks = [("F stale-refs", _stale_refs), ("G filename-case", _filename_case)]
    if not fast:
        fail_checks = [("A subpackages", _subpackages_in_arch, arch, subs),
                       ("B index-current", _index_current),
                       ("B2 derived-docs-current", _derived_docs_current)] + fail_checks
    for label, fn, *a in fail_checks:
        got, crash = _run(label, fn, *a)
        (broken.append(crash) if crash else fails.extend(got))
    if not fast:
        for label, fn, *a in [("C docstrings", _docstring_coverage, subs),
                              ("D doc-age", _doc_age), ("E living-indexed", _living_docs_indexed)]:
            got, crash = _run(label, fn, *a)
            (broken.append(crash) if crash else warns.extend(got))

    for w in warns:
        print("WARN:", w)
    for f in fails:
        print("FAIL:", f)
    for b in broken:
        print("FAIL:", b)
    if fails or broken:
        print(f"\n{len(fails)} drift FAIL(s), {len(broken)} broken-check FAIL(s), {len(warns)} WARN "
              f"-- the comprehension layer has drifted (or a guard broke). Fix before shipping.")
        return 1
    print(f"PASS: the comprehension layer matches the code ({len(warns)} warning(s)"
          + (", fast mode" if fast else "") + ").")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
