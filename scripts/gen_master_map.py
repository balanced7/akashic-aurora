"""gen_master_map -- regenerate docs/MAP.md: the master map's census matrix (T096-M0, v0).

The charter's law (docs/library/brief/20260719_the-master-map-documentation-as-projecti_a26fd3.md): the map is a PROJECTION,
not a document. This v0 joins what the code already knows about itself -- each module's line-1
docstring (gen_arch_index's extractor), the env flags it reads (gen_physics_sheet's scanner),
a name-matched pin file, and a name-matched design/reference doc -- into one matrix with an
honest GAP column. Name-matching is a v0 heuristic (labeled as such in the output): it ranks
the paper-backfill queue (charter M3); it does not certify coverage. Universe: the core/ areas
MODULE_INDEX surveys + agent/harness (the seat-side organs).

Run:  py scripts/gen_master_map.py            # writes docs/MAP.md
      py scripts/gen_master_map.py --check    # exit 1 if stale vs code (CI/pre-ship)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "MAP.md")
sys.path.insert(0, ROOT)

from scripts.gen_arch_index import CORE_ORDER, first_doc          # noqa: E402
from scripts.gen_physics_sheet import scan as physics_scan        # noqa: E402

AREAS = [f"core/{a}" for a in CORE_ORDER] + ["agent/harness", "agent"]


def _modules(rel):
    d = os.path.join(ROOT, rel)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if f.endswith(".py") and f != "__init__.py"
                  and os.path.isfile(os.path.join(d, f)))


def _name_index(dirpath, exts):
    """Lowercased filenames (stem-searchable) under dirpath, non-recursive is enough for
    docs/; research/reviewed adds one more flat corpus."""
    out = []
    for base in dirpath:
        d = os.path.join(ROOT, base)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if any(f.endswith(e) for e in exts):
                out.append((base + "/" + f, f.lower()))
    return out


def build():
    flags_by_file = {}
    flags, _bounds = physics_scan()
    for name, sites in flags.items():
        for site, _default in sites:
            flags_by_file.setdefault(site.split(":")[0], set()).add(name)

    tests = _name_index(["tests"], (".py",))
    papers = _name_index(["docs", os.path.join("research", "reviewed")], (".md",))

    def _squash(s):
        # hyphen/underscore-blind matching: packet_spec.py must find packet-spec-v1-2026-07.md
        return s.lower().replace("-", "").replace("_", "")

    rows = {}
    for area in AREAS:
        for fname in _modules(area):
            rel = f"{area}/{fname}"
            stem = fname[:-3].lower().lstrip("_")
            doc = first_doc(os.path.join(ROOT, area, fname))
            pin = next((p for p, low in tests if _squash(stem) in _squash(low)), "")
            paper = next((p for p, low in papers
                          if len(stem) > 3 and _squash(stem) in _squash(low)), "")
            mod_flags = sorted(flags_by_file.get(rel, ()))
            rows.setdefault(area, []).append(
                {"module": fname, "doc": doc, "pin": pin, "paper": paper,
                 "flags": mod_flags,
                 "gap": not (pin or paper)})
    return rows


def render(rows):
    gaps = [f"{area}/{r['module']}" for area in AREAS for r in rows.get(area, ()) if r["gap"]]
    total = sum(len(v) for v in rows.values())
    lines = [
        "# MAP -- the master census matrix (auto-generated, v0)",
        "",
        "Status: current",
        "Class: reference",
        "",
        "> Do NOT edit by hand. Regenerate with `py scripts/gen_master_map.py`.",
        "> Columns: line-1 docstring (the module's own spec) | name-matched pin file |",
        "> name-matched design/reference doc (v0 HEURISTIC -- ranks the M3 backfill queue,",
        "> does not certify coverage) | env flags read (physics scan). GAP = neither a",
        "> name-matched pin nor a paper: the honest backfill queue, worst first by area.",
        "> Companions: ARCHITECTURE.md (skeleton) - MODULE_INDEX.md (docstrings) -",
        "> PHYSICS.md (bounds+flags) - the charter docs/library/brief/20260719_the-master-map-documentation-as-projecti_a26fd3.md.",
        "",
        f"## GAP queue ({len(gaps)} of {total} modules lack both pin and paper by name)",
        "",
    ]
    lines += [f"- {g}" for g in gaps] or ["- (none)"]
    for area in AREAS:
        if not rows.get(area):
            continue
        lines += ["", f"## {area}/  ({len(rows[area])} modules)", "",
                  "| Module | One-line spec | Pin | Paper | Flags |",
                  "|---|---|---|---|---|"]
        for r in rows[area]:
            lines.append("| `{m}` | {d} | {p} | {pp} | {f} |".format(
                m=r["module"], d=r["doc"].replace("|", "/"),
                p=(r["pin"] or "GAP"), pp=(r["paper"] or "GAP"),
                f=", ".join(f"`{x}`" for x in r["flags"]) or ""))
    lines.append("")
    return "\n".join(lines)


def main():
    text = render(build())
    if "--check" in sys.argv:
        try:
            old = open(OUT, encoding="utf-8").read()
        except OSError:
            print("MAP.md missing -- regenerate"); return 1
        if old != text:
            print("MAP.md STALE vs code -- regenerate (py scripts/gen_master_map.py)"); return 1
        print("MAP.md current"); return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    n = sum(len(v) for v in build().values())
    print(f"wrote docs/MAP.md: {n} modules across {len(AREAS)} areas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
