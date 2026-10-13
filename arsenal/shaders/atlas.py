"""py -m arsenal shader atlas -- the primitive atlas as data: what the house library plans, and how much of it is built.

    py -m arsenal shader atlas                          # families with their counts, planned against built
    py -m arsenal shader atlas --status P0              # the parts to build tonight (199 rows after the rulings)
    py -m arsenal shader atlas --family B [--category B3] [--built] [--json]
    py -m arsenal shader atlas --groups | --ledger | --tags | --rulings

A filter that names no family, category or status in the atlas (--status P3, --family Z, a category outside the
family given) exits 2 with the valid values, so a typo never reads as an empty bin.

WHY. The atlas draft (research/in-flight/shader-school-2026-10-13/primitive-atlas-draft.md) is a parts catalogue:
13 families of categories, each a bin of primitives with a contract, a cost class and a build priority, plus the
groups (reference designs) that wire parts together. Read as a document it tells a person what to build; read as data
it lets every tool agree on the same bins: the lab groups modules by category id, the dissector's technique tags land
on categories, the Shelf links a loved shader to the parts it teaches, and this verb answers "how much of the plan is
real" by comparing the plan with the module library itself (arsenal.shaders.modules.load_library), not with a list
someone keeps by hand.

THE DATA is atlas.json, generated from the draft by atlas_build.py (never edited by hand; a pin fails when they
disagree). Where it departs from the draft (a renamed function, a part promoted to P0, a struct the draft's signatures
use but never planned, a signature as the library built it, a group recipe's own functions), its `rulings` list says
which ruling and why; `--rulings` prints them. A module "is built" when a library module under arsenal/web/glsl/ provides its functions; the bench chunks
in design/vfx-chunks are legacy and never count. A library module whose `cat` is not an atlas category is a problem
this file names, because a part filed in a bin nobody has is a part nobody can find.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

API = "arsenal.shader-atlas/v1"
HERE = Path(__file__).resolve().parent
ATLAS_PATH = HERE / "atlas.json"
DISSECT = HERE / "dissect.py"


# ---------- loading and querying ----------

@lru_cache(maxsize=4)
def _load_cached(path: str, mtime: float) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("api") != API:
        raise ValueError(f"{path}: not an {API} file (api {data.get('api')!r})")
    return data


def load(path: Optional[Path] = None) -> dict:
    """The atlas. Cached per file and modification time, so a regenerated atlas.json is picked up."""
    p = Path(path or ATLAS_PATH)
    return _load_cached(str(p), p.stat().st_mtime)


def query(atlas: dict, family: Optional[str] = None, category: Optional[str] = None,
          status: Optional[str] = None) -> List[dict]:
    """Parts matching every filter given; family, category and status ignore case."""
    fam = family.upper() if family else None
    cat = category.upper() if category else None
    st = status.upper() if status else None
    return [p for p in atlas["parts"]
            if (fam is None or p["family"] == fam) and (cat is None or p["category"] == cat)
            and (st is None or p["status"] == st)]


def planned_functions(atlas: dict) -> Dict[str, str]:
    """Every planned function (and struct or const) name, mapped to the id of the part that owns it."""
    return {fn: p["id"] for p in atlas["parts"] for fn in p["functions"]}


def filter_problems(atlas: dict, family: Optional[str] = None, category: Optional[str] = None,
                    status: Optional[str] = None) -> List[str]:
    """What is wrong with a filter, in words (empty when every value given names something in the atlas)."""
    problems = []
    letters = [f["letter"] for f in atlas["families"]]
    cats = {c["id"]: c for c in atlas["categories"]}
    statuses = sorted(atlas["counts"]["by_status"])
    if family is not None and family.upper() not in letters:
        problems.append(f"--family {family!r} is not a family (one of {', '.join(letters)})")
    if category is not None and category.upper() not in cats:
        problems.append(f"--category {category!r} is not a category (for example "
                        f"{', '.join(list(cats)[:4])}; `py -m arsenal shader atlas --json` lists all)")
    elif category is not None and family is not None and family.upper() in letters \
            and cats[category.upper()]["family"] != family.upper():
        problems.append(f"--category {category.upper()} belongs to family {cats[category.upper()]['family']}, "
                        f"not {family.upper()}")
    if status is not None and status.upper() not in statuses:
        problems.append(f"--status {status!r} is not a status (one of {', '.join(statuses)})")
    return problems


def categories_for_tag(tag: str, atlas: Optional[dict] = None) -> List[str]:
    """The atlas categories a dissector tag lands on: its exact mapping, else its group's (the part before the dot)."""
    tags = (atlas or load())["tags"]
    return list(tags["exact"].get(tag) or tags["groups"].get(tag.split(".")[0]) or [])


def dissector_tags(path: Path = DISSECT) -> List[str]:
    """Every tag dissect.py can emit, read from its TAGS table as text (the dissector need not import cleanly)."""
    from .atlas_build import dissector_tags as read
    return read(Path(path)) if Path(path).exists() else []


# ---------- planned against built ----------

def _library_dir(library_dir) -> Path:
    if library_dir is not None:
        return Path(library_dir).resolve()
    from .modules import LIBRARY_DIR
    return LIBRARY_DIR.resolve()


def _in_dir(path: str, root: Path) -> bool:
    return root in Path(path).resolve().parents


def library_providers(lib, library_dir=None) -> Dict[str, str]:
    """Function name -> module name, for library modules only (the legacy bench chunks never count as built)."""
    root = _library_dir(library_dir)
    return {fn: name for fn, name in lib.providers.items() if _in_dir(lib.modules[name].path, root)}


def part_states(atlas: dict, lib, library_dir=None) -> Dict[str, str]:
    """Part id -> "built" (every function provided by a library module), "partial", "planned", or "idiom"."""
    have = library_providers(lib, library_dir)
    out = {}
    for p in atlas["parts"]:
        fns = p["functions"]
        n = sum(1 for fn in fns if fn in have)
        out[p["id"]] = "idiom" if not fns else ("built" if n == len(fns) else "partial" if n else "planned")
    return out


def check_library(atlas: dict, lib, library_dir=None) -> List[str]:
    """Problems with the BUILT library against the atlas: a module whose `cat` is not an atlas category, or whose
    `family` disagrees with its category's family. An empty list means every built module sits in a known bin."""
    root = _library_dir(library_dir)
    cats = {c["id"]: c for c in atlas["categories"]}
    problems = []
    for name in sorted(lib.modules):
        m = lib.modules[name]
        if not _in_dir(m.path, root):
            continue
        cat = m.header.get("cat")
        if cat not in cats:
            problems.append(f"{name} ({m.path}): cat {cat!r} is not an atlas category")
            continue
        fam = m.header.get("family")
        if fam is not None and fam != cats[cat]["family"]:
            problems.append(f"{name} ({m.path}): family {fam!r} but cat {cat} belongs to family "
                            f"{cats[cat]['family']}")
    return problems


def _library_or_none():
    """The house library, or (None, reason) when it will not load (a name clash refuses the whole library today)."""
    try:
        from .modules import load_library
        return load_library(), None
    except Exception as exc:  # the atlas still answers "what is planned" when the library is broken
        return None, f"{type(exc).__name__}: {exc}"


# ---------- the door: py -m arsenal shader atlas ----------

def _register(sub) -> None:
    p = sub.add_parser("atlas", help="the primitive atlas: families, categories, planned versus built parts")
    p.add_argument("--family", help="one family letter, A to M")
    p.add_argument("--category", help="one category id, for example B3")
    p.add_argument("--status", help="P0, P1 or P2")
    p.add_argument("--built", action="store_true", help="only parts the library already provides (built or partial)")
    p.add_argument("--groups", action="store_true", help="the groups (reference designs) instead of parts")
    p.add_argument("--ledger", action="store_true", help="the collision ledger: who owns each contested name")
    p.add_argument("--tags", action="store_true", help="the dissector's technique tags and their categories")
    p.add_argument("--rulings", action="store_true", help="where the data departs from the draft, and why")
    p.set_defaults(fn=_cmd)


def _part_row(p: dict, state: Optional[str]) -> str:
    fns = ", ".join(p["functions"]) or "(" + p["kind"] + ")"
    return (f"  {p['id']:<7} {p['status']} {p['cost'] or '--':<3} {fns[:58]:<58} {p['module']:<28}"
            + (f" {state}" if state else ""))


def _tiers(g: dict) -> str:
    named = [t for t in g["tiers"] if t["name"]]
    return ("  tiers: " + ", ".join(f"{t['name']} {t['cost'] or '--'} {t['status']}" for t in named)) if named else ""


def _cmd(ns) -> int:
    import sys
    from .cli import _print
    atlas = load()
    problems = filter_problems(atlas, ns.family, ns.category, ns.status)
    if problems:
        for p in problems:
            print(f"atlas: {p}", file=sys.stderr)
        return 2
    lib, why = _library_or_none()
    states = part_states(atlas, lib) if lib is not None else {}

    if ns.groups:
        rows = atlas["groups"]
        _print(rows, ns.json, lambda rs: "\n".join(
            [f"{len(rs)} groups (cost is the costliest tier that ships at the group's status)"] +
            [f"  {g['name']:<18} {g['status']} {g['cost'] or '--':<3} {len(g['parts']):>2} parts  {g['line'][:60]}"
             + _tiers(g) for g in rs]))
        return 0
    if ns.rulings:
        rows = atlas["rulings"]
        _print(rows, ns.json, lambda rs: "\n".join(
            [f"{len(rs)} rulings: where the data departs from the draft"] +
            [f"  {r['id']:<26} {r['kind']:<13} {', '.join(r['names'])[:36]:<36} {r['source'].split(', ')[-1]}"
             for r in rs] + ["--json gives each ruling's reason, its source and the parts it touched"]))
        return 0
    if ns.ledger:
        rows = atlas["collisions"]
        _print(rows, ns.json, lambda rs: "\n".join(
            [f"{len(rs)} contested names, each settled"] +
            [f"  {r['proposed'][:34]:<34} -> {', '.join(r['names'])[:40]:<40} {r['why'][:50]}" for r in rs]))
        return 0
    if ns.tags:
        known = dissector_tags()
        rows = {t: categories_for_tag(t, atlas) for t in (known or sorted(atlas["tags"]["exact"]))}
        _print(rows, ns.json, lambda rs: "\n".join(
            [f"{len(rs)} dissector tags"] + [f"  {t:<24} {', '.join(c)}" for t, c in rs.items()]))
        return 0

    filtered = ns.family or ns.category or ns.status or ns.built
    if filtered:
        parts = query(atlas, ns.family, ns.category, ns.status)
        if ns.built:
            parts = [p for p in parts if states.get(p["id"]) in ("built", "partial")]
        rows = [dict(p, state=states.get(p["id"], "unknown")) for p in parts]

        def human(rs):
            out = [f"{len(rs)} parts" + (f"  (library not loaded: {why})" if why else "")]
            cat = None
            for r in rs:
                if r["category"] != cat:
                    cat = r["category"]
                    c = next(c for c in atlas["categories"] if c["id"] == cat)
                    out.append(f"[{cat}] {c['name']}")
                out.append(_part_row(r, r["state"]))
            return "\n".join(out)
        _print(rows, ns.json, human)
        return 0

    built_fns = library_providers(lib) if lib is not None else {}
    planned = planned_functions(atlas)
    fams = []
    for f in atlas["families"]:
        parts = query(atlas, family=f["letter"])
        fams.append({
            "letter": f["letter"], "name": f["name"],
            "categories": sum(1 for c in atlas["categories"] if c["family"] == f["letter"]),
            "parts": len(parts),
            "by_status": {s: sum(1 for p in parts if p["status"] == s) for s in ("P0", "P1", "P2")},
            "built": sum(1 for p in parts if states.get(p["id"]) == "built"),
        })
    summary = {"counts": atlas["counts"], "families": fams,
               "functions_built": sum(1 for fn in planned if fn in built_fns), "functions_planned": len(planned),
               "library_error": why}

    def human(s):
        c = s["counts"]
        st = c["by_status"]
        out = [f"atlas: {c['families']} families, {c['categories']} categories, {c['parts']} parts "
               f"(P0 {st.get('P0', 0)}, P1 {st.get('P1', 0)}, P2 {st.get('P2', 0)}), {c['groups']} groups",
               f"built: {s['functions_built']} of {s['functions_planned']} planned names"
               + (f"  (library not loaded: {s['library_error']})" if s["library_error"] else "")]
        for f in s["families"]:
            b = f["by_status"]
            out.append(f"  {f['letter']}  {f['name']:<28} {f['categories']:>2} cats {f['parts']:>3} parts  "
                       f"P0 {b['P0']:>3}  P1 {b['P1']:>3}  P2 {b['P2']:>3}  built {f['built']}")
        out.append("filter with --family/--category/--status/--built; --groups, --ledger, --tags for the rest")
        return "\n".join(out)
    _print(summary, ns.json, human)
    return 0


def _hook() -> None:
    from . import cli
    cli.VERBS["atlas"] = _register


_hook()
