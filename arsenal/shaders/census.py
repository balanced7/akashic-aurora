"""py -m arsenal shader census [--set loved] -- the corpus dissected and tabulated: how often each technique appears,
what travels together, and the families of shaders that share a toolkit.

WHY. The dissector (dissect.py) says what ONE shader is made of. The house primitive library needs the other view:
across everything Daniel loves (the `loved` set) and everything the site loves (`love_top`), which techniques recur,
which pairs travel together (a sphere-traced scene almost always brings central-difference normals and a soft shadow),
and which clusters of shaders share a whole toolkit. Those clusters are the candidate "structures" of Daniel's
2026-10-13 ask -- "break down the primitives and group them by category ... so we can have reusable structures" --
and the frequency table orders the library's build list: write first what most of the loved shaders use.

FAMILIES. Each shader is a set of technique tags (conf >= the floor; animation and input tags left out -- iTime says
nothing about technique). Similarity is a weighted Jaccard where a tag weighs log(N / shaders-with-it), so rare shared
techniques count for more than common ones; families are average-linkage clusters cut at FAMILY_DISTANCE, named by
the tags most over-represented in them (lift against the whole set). Deterministic: same corpus, same families.

PRIVATE OUTPUT. The tables name other people's shaders and describe their internals, so they are written only under
state/arsenal/shaders/census/ (gitignored): <set>.md (the human tables), <set>.json (everything), and a timestamped
copy of the JSON under runs/ (nothing here is overwritten without a dated twin).
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import corpus as C
from . import dissect as D

API = "arsenal.shader-census/v1"
# Merge clusters whose average weighted-Jaccard distance is at most this. Swept on the 2026-10-13 corpus (335):
# 0.6 -> 35 families / 192 loners, 0.75 -> 42 / 62, 0.85 -> 26 / 13 with one 83-shader catch-all; 0.75 keeps the
# lineages apart (SDF characters, volumetric landscapes, inversion fractals, fluid feedback sims).
FAMILY_DISTANCE = 0.75
MIN_FAMILY = 3                 # smaller clusters are reported as loners
NON_TECHNIQUE_GROUPS = frozenset({"animation", "input"})
TOP_PAIRS = 25
TOP_COST = 15


def census_dir(corpus: Optional[Path] = None) -> Path:
    return C._root(corpus).parent / "census"


# ---------- one row per shader ----------

def _row(rep: dict) -> dict:
    tech = {t["tag"]: t for t in rep["techniques"]}
    params: Dict[str, object] = {}
    march = [e["params"].get("steps") for t in rep["techniques"] if t["tag"] == "raymarch.sphere_trace"
             for e in t["evidence"] if e["params"].get("steps")]
    if march:
        params["march_steps"] = max(march)
    fbm = [e["params"] for t in rep["techniques"] if t["tag"] == "noise.fbm" for e in t["evidence"]]
    if fbm:
        params["fbm"] = [{k: p.get(k) for k in ("octaves", "lacunarity", "gain", "form") if p.get(k) is not None} for p in fbm]
    aa = [e["params"].get("samples") for t in rep["techniques"] if t["tag"] == "aa.supersample" for e in t["evidence"]]
    if any(aa):
        params["aa_samples"] = max(a for a in aa if a)
    return {"id": rep["id"], "name": rep["name"], "author": rep["author"], "tags": rep["tags"], "groups": rep["groups"],
            "conf": {t: tech[t]["conf"] for t in rep["tags"]}, "passes": rep["size"]["passes"],
            "lines": rep["size"]["lines"], "functions": rep["size"]["functions"],
            "dead_functions": rep["size"]["dead_functions"], "cost": rep["cost"]["heaviest"],
            "cost_path": rep["cost"]["path"], "calls_per_pixel": rep["cost"]["calls_per_pixel"],
            "work": rep["cost"]["work"],
            "unknown_loops": rep["cost"]["unknown_loops"], "params": params,
            "notes": [n for p in rep["passes"] for n in p["problems"]] +
                     [f"{p['file']}: unevaluated #if at {p['unsure_ifs']}" for p in rep["passes"] if p["unsure_ifs"]]}


# ---------- families ----------

def _features(row: dict) -> List[str]:
    return [t for t in row["tags"] if t.split(".")[0] not in NON_TECHNIQUE_GROUPS]


def _weights(rows: Sequence[dict]) -> Dict[str, float]:
    df = Counter(t for r in rows for t in set(_features(r)))
    n = len(rows)
    return {t: math.log((n + 1) / c) for t, c in df.items()}


def _distance(a: set, b: set, w: Dict[str, float]) -> float:
    union = sum(w[t] for t in a | b)
    if union == 0:
        return 1.0
    return 1.0 - sum(w[t] for t in a & b) / union


def cluster(rows: Sequence[dict], threshold: float = FAMILY_DISTANCE) -> List[List[int]]:
    """Average-linkage agglomerative clusters (row indices), cut at `threshold`, by the nearest-neighbour chain:
    O(n^2) and deterministic (ties go to the lower index)."""
    n = len(rows)
    if n == 0:
        return []
    w = _weights(rows)
    feats = [set(_features(r)) for r in rows]
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist[i][j] = dist[j][i] = _distance(feats[i], feats[j], w)
    size = [1] * n
    active = set(range(n))
    merges: List[Tuple[float, int, int]] = []
    chain: List[int] = []
    while len(active) > 1:
        if not chain:
            chain.append(min(active))
        a = chain[-1]
        prev = chain[-2] if len(chain) > 1 else None
        best, bd = None, math.inf
        for k in sorted(active):
            if k == a:
                continue
            d = dist[a][k]
            if d < bd or (d == bd and k == prev):
                best, bd = k, d
        if best == prev:
            chain.pop()
            chain.pop()
            lo, hi = min(a, best), max(a, best)
            merges.append((bd, lo, hi))
            for k in active:
                if k not in (lo, hi):
                    v = (size[lo] * dist[lo][k] + size[hi] * dist[hi][k]) / (size[lo] + size[hi])
                    dist[lo][k] = dist[k][lo] = v
            size[lo] += size[hi]
            active.discard(hi)
        else:
            chain.append(best)
    # cut: apply every merge at or under the threshold (average linkage is monotone, so order by height is safe)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for d, lo, hi in sorted(merges):
        if d > threshold:
            break
        parent[find(hi)] = find(lo)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def families(rows: Sequence[dict], threshold: float = FAMILY_DISTANCE) -> Tuple[List[dict], List[dict]]:
    """(families, loners): each family with its size, its characteristic tags (frequent in it, ranked by lift over the
    whole set) and its members."""
    n = len(rows)
    base = Counter(t for r in rows for t in set(_features(r)))
    fams, loners = [], []
    for members in cluster(rows, threshold):
        if len(members) < MIN_FAMILY:
            loners.extend(rows[i] for i in members)
            continue
        inside = Counter(t for i in members for t in set(_features(rows[i])))
        chars = []
        for t, c in inside.items():
            share = c / len(members)
            if share >= 0.5:
                lift = share / (base[t] / n)
                chars.append({"tag": t, "share": round(share, 2), "lift": round(lift, 2)})
        chars.sort(key=lambda x: (-x["lift"], -x["share"], x["tag"]))
        label = " + ".join(c["tag"] for c in chars[:3]) or "(no shared technique)"
        fams.append({"label": label, "size": len(members), "characteristic": chars,
                     "members": [{"id": rows[i]["id"], "name": rows[i]["name"], "author": rows[i]["author"]}
                                 for i in sorted(members, key=lambda i: rows[i]["id"])]})
    for k, f in enumerate(fams, 1):
        f["family"] = f"F{k}"
    return fams, [{"id": r["id"], "name": r["name"], "tags": _features(r)} for r in loners]


# ---------- the tables ----------

def _distribution(values: Iterable[float]) -> Optional[dict]:
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    q = lambda p: vals[min(len(vals) - 1, int(round(p * (len(vals) - 1))))]
    return {"n": len(vals), "min": vals[0], "p10": q(0.1), "median": statistics.median(vals), "p90": q(0.9),
            "max": vals[-1]}


def tabulate(rows: Sequence[dict], set_name: str, min_conf: float, errors: Sequence[dict] = (),
             threshold: float = FAMILY_DISTANCE) -> dict:
    n = len(rows)
    tag_freq = Counter(t for r in rows for t in r["tags"])
    group_freq = Counter(g for r in rows for g in r["groups"])
    conf_sum: Dict[str, float] = {}
    for r in rows:
        for t, c in r["conf"].items():
            conf_sum[t] = conf_sum.get(t, 0.0) + c
    tags = [{"tag": t, "shaders": c, "share": round(c / n, 3) if n else 0, "mean_conf": round(conf_sum[t] / c, 2),
             "meaning": D.TAGS.get(t, "")} for t, c in sorted(tag_freq.items(), key=lambda x: (-x[1], x[0]))]
    groups = []
    for g, c in sorted(group_freq.items(), key=lambda x: (-x[1], x[0])):
        top = [t["tag"] for t in tags if t["tag"].split(".")[0] == g][:4]
        groups.append({"group": g, "name": D.GROUPS.get(g, g), "shaders": c, "share": round(c / n, 3) if n else 0,
                       "top_tags": top})
    pairs = []
    tech_groups = [g for g in group_freq if g not in NON_TECHNIQUE_GROUPS]
    for i, a in enumerate(sorted(tech_groups)):
        for b in sorted(tech_groups)[i + 1:]:
            both = sum(1 for r in rows if a in r["groups"] and b in r["groups"])
            if both:
                lift = (both / n) / ((group_freq[a] / n) * (group_freq[b] / n))
                pairs.append({"a": a, "b": b, "both": both, "lift": round(lift, 2)})
    pairs.sort(key=lambda p: (-p["both"], -p["lift"], p["a"], p["b"]))
    tag_pairs = []
    feat_tags = [t for t in tag_freq if t.split(".")[0] not in NON_TECHNIQUE_GROUPS and tag_freq[t] >= 5]
    for i, a in enumerate(sorted(feat_tags)):
        for b in sorted(feat_tags)[i + 1:]:
            if a.split(".")[0] == b.split(".")[0]:
                continue
            both = sum(1 for r in rows if a in r["tags"] and b in r["tags"])
            if both >= 5:
                lift = (both / n) / ((tag_freq[a] / n) * (tag_freq[b] / n))
                tag_pairs.append({"a": a, "b": b, "both": both, "lift": round(lift, 2)})
    tag_pairs.sort(key=lambda p: (-p["lift"], -p["both"], p["a"], p["b"]))
    fams, loners = families(rows, threshold)
    fbm = [f for r in rows for f in r["params"].get("fbm", [])]
    numbers = {"march_steps": _distribution(r["params"].get("march_steps") for r in rows),
               "fbm_octaves": _distribution(f.get("octaves") for f in fbm),
               "fbm_lacunarity": _distribution(f.get("lacunarity") for f in fbm),
               "fbm_gain": _distribution(f.get("gain") for f in fbm),
               "aa_samples": _distribution(r["params"].get("aa_samples") for r in rows),
               "lines": _distribution(r["lines"] for r in rows),
               "heaviest_cost": _distribution(r["cost"] for r in rows if isinstance(r["cost"], (int, float))),
               "work_per_pixel": _distribution(r["work"] for r in rows if isinstance(r["work"], (int, float)))}
    heavy = sorted(rows, key=lambda r: -(r["cost"] if isinstance(r["cost"], (int, float)) else 0))[:TOP_COST]
    return {"api": API, "set": set_name, "shaders": n, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "min_conf": min_conf, "family_distance": threshold, "groups": groups, "tags": tags,
            "group_pairs": pairs[:TOP_PAIRS], "tag_pairs": tag_pairs[:TOP_PAIRS], "families": fams, "loners": loners,
            "numbers": numbers,
            "heaviest": [{"id": r["id"], "name": r["name"], "cost": r["cost"], "work": r["work"], "path": r["cost_path"]}
                         for r in heavy],
            "rows": list(rows), "errors": list(errors)}


def _rows(ids: Sequence[str], min_conf: float, corpus: Optional[Path], cache: Optional[Dict[str, dict]] = None):
    rows, errors = [], []
    for sid in ids:
        if cache is not None and sid in cache:
            rows.append(cache[sid])
            continue
        try:
            rows.append(_row(D.dissect(sid, min_conf, corpus)))
        except FileNotFoundError:
            errors.append({"id": sid, "error": "not in the corpus"})
        except Exception as exc:          # one unreadable shader must not sink a census; it is listed instead
            errors.append({"id": sid, "error": f"{type(exc).__name__}: {exc}"})
    return rows, errors


def run(ids: Sequence[str], set_name: str = "all", min_conf: float = D.MIN_CONF, corpus: Optional[Path] = None,
        threshold: float = FAMILY_DISTANCE) -> dict:
    rows, errors = _rows(ids, min_conf, corpus)
    res = tabulate(rows, set_name, min_conf, errors, threshold)
    if set_name != "all":
        # A set is too small to cluster on its own (42 loved shaders mostly come out as loners); what it needs is
        # its place in the CORPUS families: which lineages Daniel's favourites belong to.
        everyone, _ = _rows(C.all_ids(corpus), min_conf, corpus, {r["id"]: r for r in rows})
        fams, _ = families(everyone, threshold)
        member = {r["id"] for r in rows}
        placed = []
        for f in fams:
            inside = [m for m in f["members"] if m["id"] in member]
            if inside:
                placed.append({"family": f["family"], "label": f["label"], "corpus_size": f["size"],
                               "characteristic": f["characteristic"][:6], "in_set": inside})
        placed.sort(key=lambda f: (-len(f["in_set"]), f["family"]))
        res["corpus_families"] = placed
        res["corpus_loners"] = sorted(member - {m["id"] for f in placed for m in f["in_set"]})
    return res


# ---------- markdown ----------

def _md_cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def markdown(res: dict) -> str:
    n = res["shaders"]
    out = [f"# Shader census: {res['set']} ({n} shaders)", "",
           f"Generated {res['generated']} by `py -m arsenal shader census"
           + (f" --set {res['set']}`" if res["set"] != "all" else "`")
           + f". A tag counts at confidence >= {res['min_conf']}. Families: average-linkage clusters at weighted-Jaccard "
             f"distance <= {res['family_distance']}.", "",
           "PRIVATE: this file names other people's shaders and describes their internals. It lives under "
           "state/arsenal/shaders/census/ (gitignored) and is never copied into a tracked file.", ""]
    if res["errors"]:
        out += [f"Not dissected ({len(res['errors'])}): " + ", ".join(f"{e['id']} ({e['error']})" for e in res["errors"]), ""]
    out += ["## Technique groups", "", "| group | shaders | share | most common tags |", "|---|---:|---:|---|"]
    for g in res["groups"]:
        out.append(f"| {g['name']} (`{g['group']}`) | {g['shaders']} | {g['share']:.0%} | {', '.join(g['top_tags'])} |")
    out += ["", "## Techniques", "", "| tag | shaders | share | mean conf | what it means |", "|---|---:|---:|---:|---|"]
    for t in res["tags"]:
        out.append(f"| `{t['tag']}` | {t['shaders']} | {t['share']:.0%} | {t['mean_conf']:.2f} | {_md_cell(t['meaning'])} |")
    out += ["", "## What travels together", "", "Group pairs, most frequent first (lift > 1: together more often than "
            "chance).", "", "| group | group | both | lift |", "|---|---|---:|---:|"]
    for p in res["group_pairs"]:
        out.append(f"| {p['a']} | {p['b']} | {p['both']} | {p['lift']:.2f} |")
    out += ["", "Technique pairs with the strongest pull (at least 5 shaders, across groups).", "",
            "| tag | tag | both | lift |", "|---|---|---:|---:|"]
    for p in res["tag_pairs"]:
        out.append(f"| `{p['a']}` | `{p['b']}` | {p['both']} | {p['lift']:.2f} |")
    out += ["", "## Families", ""]
    for f in res["families"]:
        chars = ", ".join(f"`{c['tag']}` {c['share']:.0%} (x{c['lift']:.1f})" for c in f["characteristic"][:8])
        out += [f"### {f['family']}: {f['label']} ({f['size']} shaders)", "", f"Characteristic: {chars or 'none'}", "",
                ", ".join(f"{m['id']} *{_md_cell(m['name'])}* ({_md_cell(m['author'])})" for m in f["members"]), ""]
    if res["loners"]:
        out += [f"Loners ({len(res['loners'])}): " + ", ".join(f"{r['id']} *{_md_cell(r['name'])}*" for r in res["loners"]), ""]
    if res.get("corpus_families") is not None:
        out += ["## Where this set sits in the corpus families", "",
                "The same clustering run over the whole corpus; each family below holds at least one shader of this set.", "",
                "| family | corpus size | from this set | characteristic techniques | members from this set |",
                "|---|---:|---:|---|---|"]
        for f in res["corpus_families"]:
            chars = ", ".join(f"`{c['tag']}`" for c in f["characteristic"][:4])
            names = ", ".join(f"{m['id']} *{_md_cell(m['name'])}*" for m in f["in_set"])
            out.append(f"| {f['family']} {_md_cell(f['label'])} | {f['corpus_size']} | {len(f['in_set'])} | {chars} | {names} |")
        if res.get("corpus_loners"):
            out += ["", "In no corpus family (their toolkits are their own): " + ", ".join(res["corpus_loners"])]
        out.append("")
    out += ["## Numbers the detectors read off the code", "", "| quantity | n | min | p10 | median | p90 | max |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for k, d in res["numbers"].items():
        if d:
            out.append(f"| {k} | {d['n']} | {d['min']} | {d['p10']} | {d['median']} | {d['p90']} | {d['max']} |")
    out += ["", "## Heaviest shaders", "", "Product of literal loop bounds along the heaviest call path from the entry "
            "point; work = tokens executed per pixel (both are estimates read off the code, not frame times).", "",
            "| id | name | heaviest path | work/pixel | path |", "|---|---|---:|---:|---|"]
    for h in res["heaviest"]:
        out.append(f"| {h['id']} | {_md_cell(h['name'])} | {h['cost']:,} | {h['work']:,} | {_md_cell(h['path'])} |")
    out += ["", "## Every shader", "", "| id | name | author | passes | lines | heaviest path | work/pixel | technique groups |",
            "|---|---|---|---:|---:|---:|---:|---|"]
    for r in sorted(res["rows"], key=lambda r: r["id"]):
        groups = ", ".join(g for g in r["groups"] if g not in NON_TECHNIQUE_GROUPS)
        cost = f"{r['cost']:,}" if isinstance(r["cost"], (int, float)) else str(r["cost"])
        work = f"{r['work']:,}" if isinstance(r["work"], (int, float)) else str(r["work"])
        out.append(f"| {r['id']} | {_md_cell(r['name'])} | {_md_cell(r['author'])} | {r['passes']} | {r['lines']} | "
                   f"{cost} | {work} | {groups} |")
    notes = [(r["id"], x) for r in res["rows"] for x in r["notes"]]
    if notes:
        out += ["", "## Reader notes", ""] + [f"- {sid}: {_md_cell(x)}" for sid, x in notes]
    return "\n".join(out) + "\n"


def write(res: dict, corpus: Optional[Path] = None) -> Dict[str, str]:
    d = census_dir(corpus)
    (d / "runs").mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    paths = {"markdown": d / f"{res['set']}.md", "json": d / f"{res['set']}.json",
             "run": d / "runs" / f"{stamp}-{res['set']}.json"}
    text = json.dumps(res, indent=1, ensure_ascii=False)
    paths["markdown"].write_text(markdown(res), encoding="utf-8", newline="\n")
    paths["json"].write_text(text, encoding="utf-8", newline="\n")
    paths["run"].write_text(text, encoding="utf-8", newline="\n")
    return {k: str(v) for k, v in paths.items()}


def human(res: dict, written: Optional[Dict[str, str]] = None, top: int = 20) -> str:
    n = res["shaders"]
    out = [f"census of {res['set']}: {n} shaders" + (f", {len(res['errors'])} not dissected" if res["errors"] else "")]
    out.append("TOP TECHNIQUES")
    for t in [t for t in res["tags"] if t["tag"].split(".")[0] not in NON_TECHNIQUE_GROUPS][:top]:
        out.append(f"  {t['shaders']:4d}  {t['share']:4.0%}  {t['tag']}")
    out.append("GROUPS  " + ", ".join(f"{g['group']} {g['shaders']}" for g in res["groups"]))
    if res.get("corpus_families") is not None:
        out.append(f"IN CORPUS FAMILIES ({len(res['corpus_families'])} families hold this set; "
                   f"{len(res.get('corpus_loners') or [])} of its shaders are corpus loners)")
        for f in res["corpus_families"][:12]:
            out.append(f"  {f['family']:<4} {len(f['in_set']):3d} of {f['corpus_size']:<3d} {f['label']}")
    else:
        out.append(f"FAMILIES ({len(res['families'])}, {len(res['loners'])} loners)")
        for f in res["families"][:12]:
            out.append(f"  {f['family']:<4} {f['size']:3d}  {f['label']}")
    m = res["numbers"].get("march_steps")
    o = res["numbers"].get("fbm_octaves")
    if m:
        out.append(f"march steps median {m['median']} (p10 {m['p10']}, p90 {m['p90']})")
    if o:
        out.append(f"fbm octaves median {o['median']} (p10 {o['p10']}, p90 {o['p90']})")
    if written:
        out.append("written: " + written["markdown"])
    return "\n".join(out)


# ---------- the door: py -m arsenal shader census ... ----------

def _register(sub) -> None:
    p = sub.add_parser("census", help="dissect the corpus (or a set) and tabulate techniques, pairs and families")
    p.add_argument("--set", help="a named set (loved, love_top); default: the whole corpus")
    p.add_argument("--min-conf", type=float, default=D.MIN_CONF)
    p.add_argument("--distance", type=float, default=FAMILY_DISTANCE, help="family cut (weighted-Jaccard distance)")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--no-write", action="store_true", help="print only; write nothing under state/")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    if ns.set:
        sets = C.load_sets()
        if ns.set not in sets:
            print(f"no set {ns.set!r}; sets: {', '.join(k for k in sets if not k.startswith('_'))}", file=sys.stderr)
            return 2
        ids = list(sets[ns.set])
    else:
        ids = C.all_ids()
    if ns.limit:
        ids = ids[:ns.limit]
    res = run(ids, ns.set or "all", ns.min_conf, threshold=ns.distance)
    written = None if ns.no_write else write(res)
    if ns.json:
        _print(dict(res, written=written), True, str)
    else:
        _print(res, False, lambda r: human(r, written))
    return 0


def _hook() -> None:
    from . import cli
    cli.VERBS["census"] = _register


_hook()
