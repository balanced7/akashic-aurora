"""The private shader corpus: shaders we study, saved whole, with the facts a reader needs before opening the code.

    py -m arsenal shader ingest <bundle.json>   # a harvest bundle from the browser helper (arsenal/shaders/harvest.js)
    py -m arsenal shader list [--set loved]     # what is in the corpus
    py -m arsenal shader show <id|name>         # one shader's facts: author, licence, passes, inputs, sets

WHERE IT LIVES AND WHY. state/arsenal/shaders/corpus/ (gitignored). Everything in it is someone else's work under
their licence (Shadertoy's default is CC BY-NC-SA 3.0), so nothing here is ever copied into a tracked file:

    corpus/
      sets.json                       named, ordered id lists: "loved" (Daniel's Loved playlist), "love_top" (site rank)
      shaders/<id>/shader.json        the shader exactly as Shadertoy serves it (provenance; never edited)
      shaders/<id>/meta.json          the facts below, derived from shader.json by meta_for()
      shaders/<id>/<pass>.glsl        each render pass's source, one file per pass (image, buffer_a, common, sound...)
      media/<sha>.<ext>               textures, cubemap faces and volumes the shaders sample, as served
      harvests/<sha256>.json          every bundle ingested, byte for byte, named by its hash

A shader is keyed by its Shadertoy id. Ingesting the same shader twice rewrites its files from the newer copy and
keeps its set memberships; sets merge in order (an id keeps its first position). Nothing is ever deleted here.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "state" / "arsenal" / "shaders" / "corpus"
HARVEST_API = "arsenal.shadertoy-harvest/v1"
META_API = "arsenal.shader-meta/v1"
SITE = "https://www.shadertoy.com"

# Shadertoy's terms: a shader with no licence statement is CC BY-NC-SA 3.0 Unported. Order matters: the first pattern
# that matches the shader's comments names its licence (an MIT header that mentions "Creative Commons" in passing is
# still MIT, so the permissive and specific names are tried first).
DEFAULT_LICENSE = "CC-BY-NC-SA-3.0 (Shadertoy default)"
LICENSE_PATTERNS = (
    ("MIT", re.compile(r"\bMIT\b(\s+License)?|Permission is hereby granted, free of charge", re.I)),
    ("CC0", re.compile(r"\bCC0\b|public\s+domain|unlicen[sc]e", re.I)),
    ("WTFPL", re.compile(r"\bWTFPL\b", re.I)),
    ("Apache-2.0", re.compile(r"Apache\s+License", re.I)),
    ("GPL", re.compile(r"\bGPL\b|GNU General Public", re.I)),
    ("CC-BY-NC-SA", re.compile(r"NonCommercial[- ]ShareAlike|BY[- ]NC[- ]SA", re.I)),
    ("CC-BY-NC", re.compile(r"NonCommercial|BY[- ]NC\b", re.I)),
    ("CC-BY-SA", re.compile(r"Attribution[- ]ShareAlike|BY[- ]SA\b", re.I)),
    ("CC-BY", re.compile(r"Creative\s+Commons\s+Attribution|CC[- ]BY\b", re.I)),
    ("all-rights-reserved", re.compile(r"all\s+rights\s+reserved|do\s+not\s+(copy|use|reproduce)", re.I)),
)
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)

# Shadertoy pass names -> file stems. "Buffer A" -> buffer_a; unknown names are slugged the same way.
def pass_stem(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "pass").strip().lower()).strip("_") or "pass"


def detect_license(sources: Iterable[str]) -> Dict[str, object]:
    """{license, explicit, line}: the first licence named in the shader's comments, or the Shadertoy default."""
    for src in sources:
        for comment in _COMMENT.findall(src or ""):
            for name, pat in LICENSE_PATTERNS:
                m = pat.search(comment)
                if m:
                    line = next((ln.strip(" /*\t") for ln in comment.splitlines() if pat.search(ln)), m.group(0))
                    return {"license": name, "explicit": True, "line": line[:200]}
    return {"license": DEFAULT_LICENSE, "explicit": False, "line": ""}


def _input_row(inp: dict) -> dict:
    return {
        "channel": inp.get("channel"),
        "type": inp.get("type") or inp.get("ctype"),
        "id": inp.get("id"),
        "src": inp.get("filepath") or inp.get("src"),
        "sampler": inp.get("sampler") or {},
        "published": inp.get("published"),
    }


def meta_for(shader: dict) -> dict:
    """The facts a reader needs before opening the code, derived only from Shadertoy's own JSON."""
    info = shader.get("info") or {}
    passes = []
    for rp in shader.get("renderpass") or []:
        passes.append({
            "name": rp.get("name"),
            "type": rp.get("type"),
            "file": pass_stem(rp.get("name")) + ".glsl",
            "lines": (rp.get("code") or "").count("\n") + 1,
            "chars": len(rp.get("code") or ""),
            "inputs": [_input_row(i) for i in rp.get("inputs") or []],
            "outputs": [{"id": o.get("id"), "channel": o.get("channel")} for o in rp.get("outputs") or []],
        })
    lic = detect_license(rp.get("code") or "" for rp in shader.get("renderpass") or [])
    return {
        "api": META_API,
        "id": info.get("id"),
        "name": info.get("name"),
        "author": info.get("username"),
        "url": f"{SITE}/view/{info.get('id')}",
        "date": int(info.get("date") or 0),
        "likes": info.get("likes"),
        "views": info.get("viewed"),
        "tags": info.get("tags") or [],
        "description": info.get("description") or "",
        "license": lic,
        "passes": passes,
        "pass_types": sorted({p["type"] for p in passes}),
        "multipass": sum(1 for p in passes if p["type"] in ("buffer", "cubemap")) > 0,
        "media": sorted({i["src"] for p in passes for i in p["inputs"]
                         if i["src"] and i["type"] in ("texture", "cubemap", "volume", "video", "music")}),
    }


def _root(corpus: Optional[Path]) -> Path:
    """The corpus directory: the argument, else CORPUS read at CALL time (so a test can point the module elsewhere)."""
    return Path(corpus) if corpus is not None else CORPUS


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_sets(corpus: Optional[Path] = None) -> Dict[str, List[str]]:
    corpus = _root(corpus)
    p = corpus / "sets.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def merge_set(sets: Dict[str, List[str]], name: str, ids: Iterable[str]) -> int:
    """Append ids to a named set in order, skipping ones already in it. Returns how many were new."""
    cur = sets.setdefault(name, [])
    have, new = set(cur), 0
    for i in ids:
        if i and i not in have:
            cur.append(i)
            have.add(i)
            new += 1
    return new


def save_shader(shader: dict, corpus: Optional[Path] = None) -> dict:
    """Write one shader's directory (shader.json, meta.json, one .glsl per pass). Returns its meta."""
    sid = (shader.get("info") or {}).get("id")
    if not sid or not re.fullmatch(r"[A-Za-z0-9]{6}", sid):
        raise ValueError(f"not a Shadertoy id: {sid!r}")
    corpus = _root(corpus)
    d = corpus / "shaders" / sid
    d.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in shader.items() if not k.startswith("__")}
    _write_json(d / "shader.json", clean)
    for rp in shader.get("renderpass") or []:
        (d / (pass_stem(rp.get("name")) + ".glsl")).write_text(rp.get("code") or "", encoding="utf-8", newline="\n")
    meta = meta_for(clean)
    _write_json(d / "meta.json", meta)
    return meta


def save_media(path_on_site: str, data: bytes, corpus: Optional[Path] = None) -> Path:
    """Media are keyed by their site path's basename (Shadertoy names them by content hash already)."""
    corpus = _root(corpus)
    name = Path(path_on_site).name
    out = corpus / "media" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def ingest_bundle(bundle_path: Path, corpus: Optional[Path] = None) -> dict:
    """Ingest a harvest bundle (arsenal.shadertoy-harvest/v1). Keys understood:
    love_top / loved_full / shaders: lists of full shader JSON; loved_ids: Daniel's playlist order;
    sets: {name: [ids]}; media: {site_path: base64}. Returns a report of what was written."""
    corpus = _root(corpus)
    raw = Path(bundle_path).read_bytes()
    bundle = json.loads(raw.decode("utf-8"))
    if bundle.get("schema") != HARVEST_API:
        raise ValueError(f"not a harvest bundle ({bundle.get('schema')!r}, want {HARVEST_API})")
    sha = hashlib.sha256(raw).hexdigest()
    (corpus / "harvests").mkdir(parents=True, exist_ok=True)
    keep = corpus / "harvests" / f"{sha}.json"
    if not keep.exists():
        shutil.copyfile(bundle_path, keep)
    sets = load_sets(corpus)
    written, sets_new = [], {}
    by_rank = []
    for key in ("love_top", "loved_full", "shaders"):
        for s in bundle.get(key) or []:
            meta = save_shader(s, corpus)
            written.append(meta["id"])
            if key == "love_top":
                by_rank.append((s.get("__rank") or 10 ** 9, meta["id"]))
    if by_rank:
        sets_new["love_top"] = merge_set(sets, "love_top", [i for _, i in sorted(by_rank)])
    if bundle.get("loved_ids"):
        sets_new["loved"] = merge_set(sets, "loved", bundle["loved_ids"])
    for name, ids in (bundle.get("sets") or {}).items():
        sets_new[name] = merge_set(sets, name, ids)
    media = 0
    for site_path, b64 in (bundle.get("media") or {}).items():
        save_media(site_path, base64.b64decode(b64), corpus)
        media += 1
    sets.setdefault("_updated", [])
    sets["_updated"] = [time.strftime("%Y-%m-%dT%H:%M:%S")]
    _write_json(corpus / "sets.json", sets)
    return {"bundle": str(bundle_path), "sha256": sha, "shaders_written": len(set(written)),
            "sets_new": sets_new, "media_written": media, "corpus": str(corpus)}


def all_ids(corpus: Optional[Path] = None) -> List[str]:
    corpus = _root(corpus)
    d = corpus / "shaders"
    return sorted(p.name for p in d.iterdir() if (p / "meta.json").exists()) if d.exists() else []


def load_meta(sid: str, corpus: Optional[Path] = None) -> dict:
    corpus = _root(corpus)
    return json.loads((corpus / "shaders" / sid / "meta.json").read_text(encoding="utf-8"))


def load_shader(sid: str, corpus: Optional[Path] = None) -> dict:
    corpus = _root(corpus)
    return json.loads((corpus / "shaders" / sid / "shader.json").read_text(encoding="utf-8"))


def resolve(query: str, corpus: Optional[Path] = None) -> List[str]:
    """An exact id, else every shader whose name contains the query (case-insensitive)."""
    corpus = _root(corpus)
    if (corpus / "shaders" / query / "meta.json").exists():
        return [query]
    q = query.lower()
    return [i for i in all_ids(corpus) if q in (load_meta(i, corpus).get("name") or "").lower()]


def missing_media(corpus: Optional[Path] = None) -> List[str]:
    """Site paths of media some shader samples that the corpus does not hold yet."""
    corpus = _root(corpus)
    have = {p.name for p in (corpus / "media").iterdir()} if (corpus / "media").exists() else set()
    need = set()
    for sid in all_ids(corpus):
        for m in load_meta(sid, corpus).get("media") or []:
            if m.startswith("/media/") and Path(m).name not in have:
                need.add(m)
    return sorted(need)


_SITE_MEDIA = re.compile(r"^/media/a/[0-9a-f]{16,}\.[A-Za-z0-9]+$")


def media_to_fetch(corpus: Optional[Path] = None) -> List[str]:
    """The site paths a harvest should fetch: every missing /media/a/<hash>.<ext> a shader samples, plus the five extra
    faces (<hash>_1.<ext> .. _5) of every cubemap input, because a cubemap is six files and the shader JSON names only
    the first. Placeholder paths (/media/previz/...) are Shadertoy's own UI stand-ins and are never fetched."""
    corpus = _root(corpus)
    have = {p.name for p in (corpus / "media").iterdir()} if (corpus / "media").exists() else set()
    want = set()
    for sid in all_ids(corpus):
        for p in load_meta(sid, corpus).get("passes") or []:
            for i in p.get("inputs") or []:
                src = i.get("src") or ""
                if not _SITE_MEDIA.match(src) or i.get("type") not in ("texture", "cubemap", "volume", "video", "music"):
                    continue
                want.add(src)
                if i.get("type") == "cubemap":
                    stem, ext = src.rsplit(".", 1)
                    want.update(f"{stem}_{k}.{ext}" for k in range(1, 6))
    return sorted(w for w in want if Path(w).name not in have)


def missing_ids(corpus: Optional[Path] = None) -> Dict[str, List[str]]:
    """Ids named by a set whose shader is not saved yet (e.g. a playlist page harvested before its shaders were)."""
    have = set(all_ids(corpus))
    return {name: [i for i in ids if i not in have]
            for name, ids in load_sets(corpus).items() if not name.startswith("_")
            and any(i not in have for i in ids)}
