"""py -m arsenal shader shelf build | list | show <id> -- Daniel's Loved shaders in the house tooling, licence-safe.

    py -m arsenal shader shelf build        # join corpus, dissector, atlas, study notes and renders into the index
    py -m arsenal shader shelf list         # the Loved shaders in Daniel's order: licence, renders, groups, note
    py -m arsenal shader shelf show 4s23zz  # one shader's card in full (an id, or a piece of its title)

WHY. Daniel asked to "import them all into our vfx tooling". That cannot mean copying their code into the bench: the
corpus is other people's work (most of it CC BY-NC-SA; 33 of its 335 shaders withhold permission altogether, one of
them Loved) and this repository is public under Apache-2.0. The Shelf is the import in the only form the licence line allows (architecture draft,
section 9). Think of a parts drawer of datasheets: each loved board gets a card saying what it is, who made it and what
we may do with it, the list of standard parts it is built from, and a photograph -- never a copy of its schematic.
Per loved shader the index joins:

    title, author, link       the corpus meta (corpus.py)
    licence                   the meta's reading, corrected where the shader's own header withholds permission
    tags -> categories        what the dissector found, placed on atlas categories (dissect.atlas_map)
    groups, parts             the atlas groups it exemplifies and the parts it teaches best (atlas.json exemplars)
    study note                its private study note: path, headings and technique headings
    renders                   SwiftShader stills at t=1 and t=4 and an 8-frame filmstrip, from the receipts

WHERE. state/arsenal/shaders/shelf/index.json, gitignored: it names other people's work and quotes the line of each
licence header, so it is private, and write() refuses any path outside state/. The lab server serves it at
/shelf/index.json with /study/<id>.md and /renders/<id>/<file>.png beside it, loopback only (serve.py).

THE RESTRICTIVE-HEADER CORRECTION. corpus.detect_license names the first licence its patterns know. A header that
withholds permission in its own words can slip past it: Warping (4s23zz) did, and its meta reads Shadertoy's default.
So the Shelf reads every comment again, a comment block at a time (a phrase broken across two // lines is still one
phrase), for a short list of phrasings that withhold permission: "all rights reserved", "sole copyright owner", "you
cannot/may not use, copy, host, sell...", "do not copy", "without my permission", "for educational purposes only". A hit
makes the licence all-rights-reserved (marked corrected, with the meta's reading kept beside it) and the shader study
only. Three near misses are deliberately not hits: a clause that forbids commercial use alone (that is CC BY-NC, already
a licence); "All rights reserved" followed in the same comment by a grant ("Distributed under the MIT License", old
copyright boilerplate: two corpus shaders carry it in a credited noise library); and a code comment warning a reader off
a slow helper ("DO NOT USE"), because only phrases about copying, hosting, selling or permission count. Calibrated over
the whole corpus on 2026-10-13: 33 of 335 shaders withhold permission this way, the meta caught 1 of them. The atlas's
own study-only ruling counts too, and so does a meta that already reads all-rights-reserved (its patterns also fire on a
code comment such as "do not use abs() here", so when the Shelf cannot confirm that reading it keeps the stricter one
and says it may be false). Any one reason is enough, and the entry names every reason that holds.

STUDY ONLY means the entry lists the study note, the tags and the atlas links, and no image paths at all, whatever sits
in the renders folder (the server refuses those pictures as well).

RENDERS are read, never made, here. A picture is listed only when a receipt written by `py -m arsenal shader render` or
`filmstrip` names it and the file sits in renders/<id>/. A receipt at a frame rate other than 60 is `stale`; no receipt
is `not rendered`. Making them is a separate, locked SwiftShader burst: `render <id> --t 1,4` and `filmstrip <id>`.
Each receipt's `substituted` list (an input the corpus could not supply: a texture drawn by a procedural stand-in, audio
fed as silence) is kept beside the pictures, so the lab can badge a card whose pictures are not quite the shader.

Apache-2.0, our own code and words. No corpus code passes through this file; the index quotes licence lines and the
study notes' own headings, nothing else.
"""
from __future__ import annotations

import json
import re
import sys
import time
from bisect import bisect_right
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import corpus as C
from . import dissect as D

API = "arsenal.shader-shelf/v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE_ROOT = ROOT / "state"                       # gitignored; nothing the Shelf writes leaves it
STATE = STATE_ROOT / "arsenal" / "shaders"
OUT = STATE / "shelf" / "index.json"
STUDY = STATE / "study"
RENDERS = STATE / "renders"
SET = "loved"

SHELF_T = (1.0, 4.0)          # the stills the Shelf wants, at 480x270
SHELF_SIZE = (480, 270)
SHELF_FPS = 60                # render.py DEFAULT_FPS: Shadertoy's rate
FILMSTRIP = {"frames": 8, "to": 8.0}
RESTRICTED = "all-rights-reserved"
PRIVATE = ("private: this index names other people's work and quotes their licence lines; it stays under state/ "
           "(gitignored) and the lab server serves it on loopback only")

# ---------------------------------------------------------------------------------------- the licence correction
_VERBS = r"(?:use|copy|sell|share|host|reproduce|redistribute|distribute|modify|publish|re-?post|re-?upload|mint|train)"
RESTRICTIVE = (
    ("all rights reserved", re.compile(r"\ball\s+rights\s+reserved\b", re.I)),
    ("sole owner", re.compile(r"\bsole\s+(?:copyright\s+)?(?:owner|holder)\b", re.I)),
    ("you may not", re.compile(r"\byou\s+(?:cannot|can\s*not|can'?t|may\s+not|must\s+not|are\s+not\s+(?:allowed|"
                               r"permitted)\s+to)\s+" + _VERBS + r"\b", re.I)),
    ("do not copy", re.compile(r"\b(?:do\s+not|don'?t)\s+(?:copy|reproduce|redistribute|distribute|re-?post|"
                               r"re-?upload|sell|steal)\b", re.I)),
    ("do not use this work", re.compile(r"\b(?:do\s+not|don'?t)\s+use\s+(?:this|my)\s+(?:code|shader|work|piece|art)\b",
                                        re.I)),
    ("without permission", re.compile(r"\bwithout\s+(?:my|the\s+author'?s?|prior|express|explicit|written)\b"
                                      r"[^.;\n]{0,30}?\bpermission\b", re.I)),
    ("educational purposes only", re.compile(r"\b(?:only\s+for\s+educational\s+purposes|for\s+educational\s+purposes"
                                             r"\s+only)\b", re.I)),
)
# A "you may not" clause that forbids commercial use and nothing wider is a NonCommercial term: a licence, not a refusal.
_COMMERCIAL = re.compile(r"\bcommercial\b", re.I)
_WIDER = re.compile(r"non-?\s?commercial|\bany\s+(?:product|project|website|form|way)\b|\banywhere\b", re.I)
# "All rights reserved" is also old copyright boilerplate that precedes a grant ("Copyright (C) Some Lab. All rights
# reserved. Distributed under the MIT License."). With a grant in the same comment block it is a licence, not a refusal.
_GRANT = re.compile(r"\b(?:distributed|licen[cs]ed|released|available)\s+under\b|\bMIT\b|permission\s+is\s+hereby"
                    r"\s+granted|\bBSD\b|\bApache\b|creative\s+commons|\bCC[- ]?(?:0|BY)\b|public\s+domain", re.I)
# "License: X, author: Y" lines that credit a fragment borrowed from elsewhere (a CC0 shader can carry some).
_EMBEDDED = re.compile(r"\blicen[cs]e\s*:\s*([A-Za-z0-9][\w .+-]{0,40}?)\s*(?:,|;|\(|$)", re.I)
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _segments(src: str) -> List[tuple]:
    """(line number, comment text) for every comment line in a source, in order: a /* */ comment gives one per line."""
    out = []
    for m in _COMMENT.finditer(src or ""):
        first = src.count("\n", 0, m.start()) + 1
        body = m.group(0)
        lines = [body[2:]] if body.startswith("//") else body[2:-2].split("\n")
        for i, text in enumerate(lines):
            text = text.strip().lstrip("/*").strip()
            if text:
                out.append((first + i, text))
    return out


def _blocks(segments: List[tuple]) -> List[tuple]:
    """Comment lines on consecutive source lines joined into one text: (joined, offsets, lines, texts)."""
    blocks, cur = [], []
    for line, text in segments:
        if cur and line > cur[-1][0] + 1:
            blocks.append(cur)
            cur = []
        cur.append((line, text))
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks:
        offsets, pos = [], 0
        for _, text in b:
            offsets.append(pos)
            pos += len(text) + 1
        out.append((" ".join(t for _, t in b), offsets, [ln for ln, _ in b], [t for _, t in b]))
    return out


def restrictive_lines(sources: Dict[str, str]) -> List[dict]:
    """Where a shader's comments withhold permission: [{kind, file, line, text}], in file order. `sources` maps a pass's
    file name to its code; only comments are read (corpus.detect_license reads the same way)."""
    hits = []
    for file, src in sources.items():
        for joined, offsets, lines, texts in _blocks(_segments(src)):
            granted = bool(_GRANT.search(joined))
            for kind, pat in RESTRICTIVE:
                if kind == "all rights reserved" and granted:
                    continue
                for m in pat.finditer(joined):
                    if kind == "you may not":
                        stop = joined.find(".", m.end())
                        clause = joined[m.start(): stop if stop >= 0 else m.start() + 200]
                        if _COMMERCIAL.search(clause) and not _WIDER.search(clause):
                            continue
                    i = bisect_right(offsets, m.start()) - 1
                    hits.append({"kind": kind, "file": file, "line": lines[i], "text": texts[i][:200]})
    seen, out = set(), []
    for h in sorted(hits, key=lambda h: (list(sources).index(h["file"]), h["line"])):
        key = (h["file"], h["line"], h["kind"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def embedded_licences(sources: Dict[str, str]) -> List[dict]:
    """Fragments a shader credits to elsewhere with a licence of their own ("License: X, author: Y")."""
    out = []
    for file, src in sources.items():
        for line, text in _segments(src):
            m = _EMBEDDED.search(text)
            if m and "author" in text.lower():
                out.append({"file": file, "line": line, "licence": m.group(1).strip()})
    return out


def licence_for(meta: dict, sources: Dict[str, str]) -> dict:
    """The licence a card shows: the corpus meta's reading, corrected when the shader's own header withholds permission."""
    lic = meta.get("license") or {}
    said = lic.get("license") or C.DEFAULT_LICENSE
    hits = restrictive_lines(sources)
    embedded = embedded_licences(sources)
    out = {"name": said, "meta": said, "explicit": bool(lic.get("explicit")), "line": lic.get("line") or "",
           "corrected": False, "restrictive": hits, "embedded": embedded, "caution": None}
    if hits and said != RESTRICTED:
        out.update(name=RESTRICTED, explicit=True, line=hits[0]["text"], corrected=True)
    unknown = [e for e in embedded if e["licence"].lower().startswith("unknow")]
    if unknown:
        where = ", ".join(f"{e['file']}:{e['line']}" for e in unknown)
        out["caution"] = (f"credits {len(unknown)} borrowed fragment(s) whose licence its own comments call unknown "
                          f"({where}): learn the technique, never the text")
    return out


def study_only_reason(sid: str, lic: dict, loved_atlas: Dict[str, dict]) -> Optional[str]:
    reasons = []
    if lic["restrictive"]:
        h = lic["restrictive"][0]
        reasons.append(f"its own header withholds permission ({h['kind']}, {h['file']}:{h['line']})"
                       + (f"; the corpus meta had read it as {lic['meta']}" if lic["corrected"] else ""))
    elif lic["meta"] == RESTRICTED:
        # corpus.detect_license reads "do not use" in any comment, and copyright boilerplate before a grant, as all
        # rights reserved; the stricter reading stands (no pictures costs little) but the doubt is said out loud.
        reasons.append(f"the corpus meta reads its header as all rights reserved (\"{lic['line'][:120]}\"); the Shelf's "
                       "own reading found no phrase that withholds permission, so this may be a false reading: a person "
                       "should look before it is lifted")
    if (loved_atlas.get(sid) or {}).get("study_only"):
        reasons.append("the atlas marks it study only (atlas.json, loved)")
    return "; ".join(reasons) or None


# ------------------------------------------------------------------------------------------ notes and renders
_TECHNIQUES = re.compile(r"^##\s+(?:\d+\.\s*)?techniques\b", re.I)


def _rel(p: Path) -> str:
    """A repo-relative POSIX path when the file is in this repository, else the absolute one."""
    p = Path(p)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def study_facts(sid: str, study_dir: Path) -> dict:
    """The study note's path, title, section headings and the technique headings under its Techniques section."""
    p = Path(study_dir) / f"{sid}.md"
    if not p.is_file():
        return {"path": None, "url": None, "title": None, "headings": [], "techniques": [], "missing": True}
    title, headings, techniques, in_tech, fence = None, [], [], False, False
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        elif line.startswith("## "):
            headings.append(line[3:].strip())
            in_tech = bool(_TECHNIQUES.match(line))
        elif line.startswith("### ") and in_tech:
            techniques.append(line[4:].strip())
    return {"path": _rel(p), "url": f"/study/{sid}.md", "title": title, "headings": headings,
            "techniques": techniques, "missing": False}


def _read_json(path: Path) -> Optional[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _local_png(d: Path, named) -> Optional[Path]:
    """The picture a receipt names, if it is a .png directly inside renders/<id>/ (the one level the server serves)."""
    if not named:
        return None
    for cand in (Path(named), d / Path(str(named).replace("\\", "/")).name):
        try:
            if cand.suffix.lower() == ".png" and cand.is_file() and cand.resolve().parent == d.resolve():
                return cand
        except OSError:
            continue
    return None


_STAND_IN_FIELDS = ("src", "kind", "reason", "style")


def _stand_ins(receipt: Optional[dict]) -> List[dict]:
    """A receipt's `substituted` list: each input the render could not feed and what drew in its place (a procedural
    stand-in texture, silent audio). Only the fields a badge needs are kept."""
    out = []
    for s in (receipt or {}).get("substituted") or []:
        if isinstance(s, dict):
            out.append({k: s[k] for k in _STAND_IN_FIELDS if k in s})
    return out


def render_facts(sid: str, renders_dir: Path, withheld: bool = False) -> dict:
    """What the receipts in renders/<id>/ say: stills, the filmstrip sheet, the frame rate, a one-word status, and
    each receipt's stand-ins (`substituted`: an input the corpus could not supply, drawn by a stand-in), which the lab
    badges on the card: a picture drawn with stand-ins is not quite the shader as its author shows it."""
    facts = {"status": None, "fps": None, "stills": [], "filmstrip": None, "problems": [],
             "substituted": {"stills": [], "filmstrip": []}}
    if withheld:
        facts["status"] = "withheld: study only (no images, whatever is on disk)"
        return facts
    d = Path(renders_dir) / sid
    rec, fil = _read_json(d / "receipt.json"), _read_json(d / "filmstrip.json")
    facts["substituted"] = {"stills": _stand_ins(rec), "filmstrip": _stand_ins(fil)}
    fps_seen, problems, stills = [], [], []
    if rec:
        fps_seen.append((rec.get("request") or {}).get("fps"))
        for f in rec.get("frames") or []:
            png = _local_png(d, f.get("png"))
            if png is None:
                problems.append(f"t={f.get('t')}: the receipt names a picture that is not in renders/{sid}/")
                continue
            stills.append({"t": float(f.get("t") or 0), "path": _rel(png), "url": f"/renders/{sid}/{png.name}",
                           "flat": f.get("flat"), "mean_luma": f.get("mean_luma")})
        if not rec.get("ok"):
            problems.append(f"render {rec.get('status')}: {rec.get('first_error') or 'not ok'}")
        got = sorted(s["t"] for s in stills)
        if stills and got != list(SHELF_T):
            problems.append(f"stills at t={got}; the Shelf wants t={list(SHELF_T)}")
    film = None
    if fil:
        req = fil.get("request") or {}
        fps_seen.append(req.get("fps"))
        sheet = d / "filmstrip.png"
        if sheet.is_file():
            film = {"path": _rel(sheet), "url": f"/renders/{sid}/filmstrip.png",
                    "frames": len(fil.get("frames") or []), "to": req.get("to"), "fps": req.get("fps")}
        if not fil.get("ok"):
            problems.append(f"filmstrip {fil.get('status')}: {fil.get('first_error') or 'not ok'}")
    flat = [s["t"] for s in stills if s.get("flat")]
    if flat:
        problems.append(f"one flat colour at t={flat}")
    rates = sorted({f for f in fps_seen if f is not None})
    if not stills and film is None:
        status = "failed" if (rec or fil) else "not rendered"
    elif any(f != SHELF_FPS for f in rates):
        status = f"stale ({'/'.join(str(f) for f in rates)} fps; the Shelf wants {SHELF_FPS})"
    elif stills and film:
        status = "rendered"
    else:
        status = "partial (" + ("no filmstrip" if stills else "no stills") + ")"
    facts.update(status=status, fps=rates[0] if rates else None,   # the lowest rate seen: a stale one shows
                 stills=stills, filmstrip=film, problems=problems)
    return facts


# ----------------------------------------------------------------------------------------------------- the index
def _sources(sid: str, meta: dict, corpus: Path) -> Dict[str, str]:
    d = corpus / "shaders" / sid
    out = {}
    for p in meta.get("passes") or []:
        try:
            out[p["file"]] = (d / p["file"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return out


def _entry(rank: int, sid: str, corpus: Path, atlas: dict, loved_atlas: Dict[str, dict], study_dir: Path,
           renders_dir: Path, dissect: Callable, have: set) -> dict:
    short = (loved_atlas.get(sid) or {}).get("short")
    if sid not in have:
        lic = {"name": "unknown (not in the corpus)", "meta": None, "explicit": False, "line": "", "corrected": False,
               "restrictive": [], "embedded": [], "caution": None}
        reason = study_only_reason(sid, lic, loved_atlas)
        m = D.atlas_map({"id": sid, "tags": []}, atlas)
        return {"rank": rank, "id": sid, "title": short or sid, "short": short or sid, "author": None,
                "url": f"{C.SITE}/view/{sid}", "missing_from_corpus": True, "licence": lic,
                "study_only": bool(reason), "study_only_reason": reason, "tags": [], "categories": m["categories"],
                "unmapped_tags": [], "groups": m["groups"], "parts": m["parts"],
                "atlas_links": len(m["categories"]) + len(m["groups"]) + len(m["parts"]),
                "study": study_facts(sid, study_dir), "renders": render_facts(sid, renders_dir, withheld=bool(reason))}
    meta = C.load_meta(sid, corpus)
    lic = licence_for(meta, _sources(sid, meta, corpus))
    reason = study_only_reason(sid, lic, loved_atlas)
    error = None
    try:
        tags = list(dissect(sid, D.MIN_CONF, corpus).get("tags") or [])
    except Exception as exc:  # one shader the dissector cannot read must not empty the Shelf
        tags, error = [], f"{type(exc).__name__}: {exc}"[:300]
    m = D.atlas_map({"id": sid, "tags": tags}, atlas)
    entry = {"rank": rank, "id": sid, "title": meta.get("name") or short or sid, "short": short or meta.get("name"),
             "author": meta.get("author"), "url": meta.get("url") or f"{C.SITE}/view/{sid}",
             "missing_from_corpus": False, "licence": lic, "study_only": bool(reason), "study_only_reason": reason,
             "tags": tags, "categories": m["categories"], "unmapped_tags": m["unmapped"], "groups": m["groups"],
             "parts": m["parts"], "atlas_links": len(m["categories"]) + len(m["groups"]) + len(m["parts"]),
             "study": study_facts(sid, study_dir), "renders": render_facts(sid, renders_dir, withheld=bool(reason)),
             "passes": [p.get("type") for p in meta.get("passes") or []]}
    if error:
        entry["dissect_error"] = error
    return entry


def build(corpus: Optional[Path] = None, atlas: Optional[dict] = None, study_dir: Optional[Path] = None,
          renders_dir: Optional[Path] = None, dissect: Optional[Callable] = None, set_name: str = SET) -> dict:
    """The Shelf's index, in memory (write() puts it on disk). Every default is read at call time, so a test can point
    any source elsewhere; nothing here writes."""
    corpus = Path(corpus) if corpus is not None else C.CORPUS
    if atlas is None:
        from . import atlas as A
        atlas = A.load()
    study_dir = Path(study_dir) if study_dir is not None else STUDY
    renders_dir = Path(renders_dir) if renders_dir is not None else RENDERS
    dissect = dissect or D.dissect
    sets = C.load_sets(corpus)
    if set_name not in sets:
        raise LookupError(f"no set {set_name!r} in {corpus / 'sets.json'}")
    loved_atlas = {row["id"]: row for row in atlas.get("loved") or []}
    have = set(C.all_ids(corpus))
    entries = [_entry(rank, sid, corpus, atlas, loved_atlas, study_dir, renders_dir, dissect, have)
               for rank, sid in enumerate(sets[set_name], 1)]
    pick = lambda pred: [e["id"] for e in entries if pred(e)]  # noqa: E731
    status = lambda e: e["renders"]["status"] or ""  # noqa: E731
    summary = {
        "study_only": pick(lambda e: e["study_only"]),
        "licence_corrected": pick(lambda e: e["licence"]["corrected"]),
        "rendered": pick(lambda e: status(e) == "rendered"),
        "not_rendered": pick(lambda e: status(e) == "not rendered"),
        "stale": pick(lambda e: status(e).startswith("stale")),
        "failed": pick(lambda e: status(e) == "failed"),
        "partial": pick(lambda e: status(e).startswith("partial")),
        "stand_ins": pick(lambda e: any(e["renders"]["substituted"].values())),
        "flat_frames": pick(lambda e: any(s.get("flat") for s in e["renders"]["stills"])),
        "no_atlas_link": pick(lambda e: e["atlas_links"] < 1),
        "no_group": pick(lambda e: not e["groups"]),
        "no_study_note": pick(lambda e: e["study"]["missing"]),
        "missing_from_corpus": pick(lambda e: e["missing_from_corpus"]),
        "dissect_errors": pick(lambda e: "dissect_error" in e),
    }
    return {"api": API, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": PRIVATE, "set": set_name,
            "count": len(entries),
            "want": {"t": list(SHELF_T), "size": list(SHELF_SIZE), "fps": SHELF_FPS, "filmstrip": dict(FILMSTRIP)},
            "sources": {"corpus": _rel(corpus), "study": _rel(study_dir), "renders": _rel(renders_dir),
                        "atlas": "arsenal/shaders/atlas.json"},
            "summary": summary, "shaders": entries}


def write(index: dict, out: Optional[Path] = None, state_root: Optional[Path] = None) -> Path:
    """Write the index (atomically). Refused outside state/: it names other people's work."""
    out = Path(out) if out is not None else OUT
    root = Path(state_root) if state_root is not None else STATE_ROOT
    if not out.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"refused: {out} is outside {root}; the Shelf names other people's work and stays under state/")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(out)
    return out


def load(path: Optional[Path] = None) -> Optional[dict]:
    """The written index, or None when there is none yet."""
    data = _read_json(Path(path) if path is not None else OUT)
    return data if data and data.get("api") == API else None


# ------------------------------------------------------------------------------------------------------ the door
def _lic_short(lic: dict) -> str:
    name = lic.get("name") or "?"
    return "CC-BY-NC-SA (default)" if name == C.DEFAULT_LICENSE else name


def _n(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _links(e: dict) -> str:
    return (f"atlas: {_n(len(e['categories']), 'category').replace('categorys', 'categories')}, "
            f"{_n(len(e['groups']), 'group')}, {_n(len(e['parts']), 'part')}")


def human_list(index: dict, path: Path) -> str:
    s = index["summary"]
    out = [f"{index['count']} {index['set']} shaders on the Shelf, Daniel's order  (built {index['built_at']}; {_rel(path)})",
           f"  rendered {len(s['rendered'])}, stale {len(s['stale'])}, not rendered {len(s['not_rendered'])}, "
           f"failed {len(s['failed'])}; study only: {', '.join(s['study_only']) or 'none'}",
           f"  {'#':>3}  {'id':<6}  {'title':<28} {'licence':<22} {'renders':<12} groups"]
    for e in index["shaders"]:
        r = "STUDY ONLY" if e["study_only"] else (e["renders"]["status"] or "?").split(" (")[0]
        groups = ", ".join(g["name"] for g in e["groups"]) or "(no group)"
        out.append(f"  {e['rank']:>3}  {e['id']:<6}  {(e['title'] or '')[:28]:<28} {_lic_short(e['licence'])[:22]:<22} "
                   f"{r[:12]:<12} {groups}")
        note = e["study"]["path"] or "(no study note)"
        out.append(f"  {'':>3}  {'':<6}  note {note}  |  {_links(e)}")
    return "\n".join(out)


def human_show(e: dict) -> str:
    lic = e["licence"]
    out = [f"{e['title']} by {e['author'] or '?'}  ({e['id']}, rank {e['rank']})  {e['url']}",
           f"  licence: {lic['name']}" + (f"  (corrected; the corpus meta said {lic['meta']})" if lic["corrected"] else "")]
    for h in lic["restrictive"][:4]:
        out.append(f"    {h['file']}:{h['line']} ({h['kind']}): \"{h['text'][:110]}\"")
    if lic.get("caution"):
        out.append(f"  caution: {lic['caution']}")
    if e["study_only"]:
        out.append(f"  STUDY ONLY: {e['study_only_reason']}")
    st = e["study"]
    out.append(f"  study note: {st['path'] or '(none)'}" + (f"  ({st['url']})" if st["url"] else ""))
    if st["techniques"]:
        out.append("    techniques: " + "; ".join(t.split(" (")[0].split(" — ")[0] for t in st["techniques"])[:600])
    out.append(f"  tags ({len(e['tags'])}): {', '.join(e['tags']) or '(none)'}")
    for c in e["categories"]:
        out.append(f"    [{c['id']}] {c['name']}  <- {', '.join(c['tags'])}")
    if e["unmapped_tags"]:
        out.append(f"    no category for: {', '.join(e['unmapped_tags'])}")
    out.append("  groups: " + (", ".join(g["name"] + (" (study only)" if g.get("study_only") else "")
                                        for g in e["groups"]) or "(none)"))
    if e["parts"]:
        out.append(f"  parts it teaches ({len(e['parts'])}): "
                   + "; ".join(f"{p['id']} {'/'.join(p['functions'][:2]) or p['module']}" for p in e["parts"][:14])
                   + (f" ... +{len(e['parts']) - 14}" if len(e["parts"]) > 14 else ""))
    r = e["renders"]
    out.append(f"  renders: {r['status']}" + (f", {r['fps']} fps" if r.get("fps") else ""))
    for s in r["stills"]:
        out.append(f"    t={s['t']:g}  {s['path']}" + ("  (one flat colour)" if s.get("flat") else ""))
    if r["filmstrip"]:
        out.append(f"    filmstrip  {r['filmstrip']['path']}  ({r['filmstrip']['frames']} frames to {r['filmstrip']['to']} s)")
    for which, subs in (r.get("substituted") or {}).items():
        for s in subs:
            out.append(f"    stand-in ({which}): {s.get('kind', '?')} {s.get('src', '?')}: {s.get('reason', '?')}")
    for p in r["problems"]:
        out.append(f"    note: {p}")
    return "\n".join(out)


def _register(sub) -> None:
    p = sub.add_parser("shelf", help="the Loved shaders in the house tooling: build the private index, list it, show one")
    p.add_argument("action", choices=("build", "list", "show"))
    p.add_argument("target", nargs="?", help="show: an id, or a piece of a title")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    if ns.action == "build":
        try:
            index = build()
        except (LookupError, FileNotFoundError) as exc:
            print(f"shelf: {exc}", file=sys.stderr)
            return 2
        path = write(index)
        _print(index, ns.json, lambda i: human_list(i, path))
        return 0
    index = load()
    if index is None:
        print(f"shelf: no index at {OUT} yet; run: py -m arsenal shader shelf build", file=sys.stderr)
        return 2
    if ns.action == "list":
        _print(index, ns.json, lambda i: human_list(i, OUT))
        return 0
    if not ns.target:
        print("shelf show needs an id or a piece of a title", file=sys.stderr)
        return 2
    q = ns.target.lower()
    hits = [e for e in index["shaders"] if e["id"] == ns.target] or \
           [e for e in index["shaders"] if q in (e["title"] or "").lower() or q in (e["short"] or "").lower()]
    if not hits:
        print(f"shelf: nothing on the Shelf matches {ns.target!r}; try: py -m arsenal shader shelf list", file=sys.stderr)
        return 2
    _print(hits if len(hits) > 1 else hits[0], ns.json,
           lambda h: "\n\n".join(human_show(e) for e in (h if isinstance(h, list) else [h])))
    return 0


def _hook() -> None:
    from . import cli
    cli.VERBS["shelf"] = _register


_hook()
