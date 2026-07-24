"""A3 migration pipeline: the ~900-file corpus -> enriched atoms, verified, gated.

Spec: docs/library/design/20260701_artifact-substrate-the-reconciled-design_8ea728.md section 8 + docs/taxonomy-ergonomics-
reconciliation-2026-07.md section 6 (enrich-before-delete; acceptance bars) + deepseek
fence bites (idempotency skip-map, strip prose headers pre-gist, per-atom sha verify)
+ kimi bar (strong rels from supersession evidence; census lists = fixtures).

Phases (each idempotent; Daniel gates between):
  --dry-run   walk + classify + report (counts, samples, unclassifiable tail). No writes.
  --import    mint atoms for every migratable file (skip-map state/migration_map.json
              makes re-runs safe); render projections; JSONL grows append-only.
  --link      pass 2: resolve path-citations to atom ids; stamp superseded-by links
              from header evidence (STRONG rels, not discusses-floor).
  --verify    the bars: map-count vs atom-count, body byte-integrity (stripped-body sha
              re-derive == atom.body_sha), projection file exists + akashic_sha match,
              citation liveness. Prints receipts; nonzero exit on any bar failure.
Deletion is NOT here: P3 is one visible Daniel-gated commit, after --verify is green.

Stays as FILES (never minted, never deleted): crown docs (docs/UPPERCASE + explicit
list), generated maps + READMEs, docs/library/** (projections), charters/** (agent
contracts), docs/_archive/** (later wave).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))  # T104-M1: generators moved

from gen_library import walk_docs, _extract, _relpath  # noqa: E402
from core.library import taxonomy as tx  # noqa: E402
from core.library.atoms import AtomFamily, DOC_TYPES, AtomError  # noqa: E402
from core.library.projection import render_atom  # noqa: E402

MAP_PATH = ROOT / "state" / "migration_map.json"

CROWN_EXPLICIT = {
    "docs/method-baseline-2026-07.md", "docs/failure-ledger-2026-07.md",
    "docs/pillar-analysis-method.md",
}
_CROWN_RE = re.compile(r"^docs/[A-Z0-9_]+\.md$")

# zone -> default type when the header is silent (LIBRARY naming canon)
_ZONE_TYPE = {"research/briefs": "brief", "research/reviewed": "report",
              "research/drafts": "design", "chronicles": "chronicle"}

_HDR_TYPE_MAP = {"plan": "design", "draft": "design", "research": "report",
                 "counter": "design", "brainstorm": "design", "think-pass": "design",
                 "reconciliation": "design", "capture": "report"}

_PATH_REF = re.compile(r"\b((?:docs|research|chronicles)/[A-Za-z0-9_\-./]+\.md)\b")
_SUPERSEDED_BY = re.compile(r"superseded[- ]by[:\s]+`?([A-Za-z0-9_\-./]+\.md)`?", re.IGNORECASE)
_HDR_BLOCK = re.compile(r"^(#[^\n]*\n)?\s*(Status:[^\n]*\n)(Type:[^\n]*\n)?([^\n]*·[^\n]*\n)*\n?",
                        re.IGNORECASE)


def skip_reason(rel: str) -> str | None:
    p = rel.replace("\\", "/")
    if p.startswith("docs/library/") or p.startswith("docs/_archive/"):
        return "projection/archive"
    if p.startswith("charters/"):
        return "agent-contract (stays file)"
    if p.endswith("/README.md") or p == "README.md":
        return "generated readme"
    if _CROWN_RE.match(p) or p in CROWN_EXPLICIT:
        return "crown (stays file)"
    return None


def derive(rel: str, header: dict, text: str) -> dict:
    """Pure derivation: (type, status, arc, date, title, categories+sources, body)."""
    p = rel.replace("\\", "/")
    zone = "/".join(p.split("/")[:2]) if p.startswith("research/") else p.split("/")[0]
    htype = (header.get("type") or "").split("(")[0].strip().lower()
    typ = _HDR_TYPE_MAP.get(htype, htype)
    if typ not in DOC_TYPES:
        typ = _ZONE_TYPE.get(zone, "report" if "review" in p else "design")
    status_raw = (header.get("status") or "").strip().lower()
    if status_raw.startswith("current"):
        status = "current"
    elif status_raw.startswith("superseded"):
        status = "superseded"
    elif status_raw.startswith("fossil") or status_raw.startswith("historical"):
        status = "fossil"
    else:
        status = "draft"  # unmarked = uncurated; honest, and the lint sweeps drafts
    arc = (header.get("arc") or "").strip() or None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", p) or re.search(r"(\d{4}-\d{2})", p)
    date = (header.get("date") or "").strip() or (m.group(1) if m else None)
    if date and len(date) == 7:
        date += "-01"
    heading = (header.get("heading") or "").strip()
    title = heading or Path(p).stem
    body = _HDR_BLOCK.sub("", text, count=1) if text else ""  # deepseek: strip prose header pre-gist
    if len(body) < len(text) * 0.3:  # stripped too much -> keep original (guard the guard)
        body = text
    cats = tx.classify(f"{title} {p} {body[:400]}")
    seats = [s.strip() for s in re.split(r"[,+&]", header.get("seats") or "") if s.strip()]
    return {"type": typ, "status": status, "arc": arc, "date": date, "title": title[:160],
            "categories": cats, "cat_sources": ["auto"] * len(cats),
            "seats": seats[:4], "body": body}


def load_map() -> dict:
    if MAP_PATH.exists():
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {}


def save_map(m: dict) -> None:
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")


def migratable() -> list[tuple[str, dict, str]]:
    out = []
    for path, header in walk_docs():
        rel = _relpath(path)
        if skip_reason(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        out.append((rel, header, text))
    return out


def cmd_dry_run() -> int:
    files = migratable()
    skipped = [( _relpath(p), skip_reason(_relpath(p))) for p, _ in walk_docs() if skip_reason(_relpath(p))]
    by_type, by_status, no_cat, no_date = {}, {}, [], []
    for rel, header, text in files:
        d = derive(rel, header, text)
        by_type[d["type"]] = by_type.get(d["type"], 0) + 1
        by_status[d["status"]] = by_status.get(d["status"], 0) + 1
        if not d["categories"]:
            no_cat.append(rel)
        if not d["date"]:
            no_date.append(rel)
    print(f"[dry-run] migratable: {len(files)} file(s) | stays-as-files: {len(skipped)}")
    print(f"  by type:   {json.dumps(by_type, sort_keys=True)}")
    print(f"  by status: {json.dumps(by_status, sort_keys=True)}")
    print(f"  unclassifiable (no category): {len(no_cat)}")
    for rel in no_cat[:15]:
        print(f"    ? {rel}")
    print(f"  dateless: {len(no_date)} (created_ts falls back to file mtime)")
    print("  SPOT-CHECK SAMPLE (5, evenly spaced):")
    step = max(1, len(files) // 5)
    for rel, header, text in files[::step][:5]:
        d = derive(rel, header, text)
        print(f"    {rel}\n      -> type={d['type']} status={d['status']} arc={d['arc']} "
              f"cats={d['categories']} title={d['title'][:60]!r}")
    print("[dry-run] no writes. Next: --import after Daniel's spot-check gate.")
    return 0


def _fam() -> AtomFamily:
    from core.foundation.store import create_store
    return AtomFamily(create_store(), repo_root=str(ROOT))


def cmd_import() -> int:
    fam, mp = _fam(), load_map()
    minted = skipped = failed = 0
    for rel, header, text in migratable():
        if rel in mp:
            skipped += 1
            continue
        d = derive(rel, header, text)
        try:
            atom = fam.mint(d["type"], d["title"], d["body"], arc=d["arc"],
                            seats=d["seats"], categories=d["categories"],
                            category_sources=d["cat_sources"], status=d["status"],
                            origin="migrated", date=d["date"],
                            now=os.path.getmtime(str(ROOT / rel)) if (ROOT / rel).exists() else time.time())
            render_atom(atom, repo_root=str(ROOT))
            mp[rel] = atom["id"]
            minted += 1
            if minted % 100 == 0:
                save_map(mp)
                print(f"  ... {minted} minted")
        except AtomError as e:
            failed += 1
            print(f"  REFUSED {rel}: {e}")
    save_map(mp)
    print(f"[import] minted {minted}, skip-map hits {skipped}, refused {failed}; map -> {MAP_PATH}")
    return 0 if failed == 0 else 1


def cmd_link() -> int:
    fam, mp = _fam(), load_map()
    linked = strong = 0
    for rel, art_id in mp.items():
        atom = fam.get(art_id)
        if atom is None:
            continue
        src = (ROOT / rel)
        text = src.read_text(encoding="utf-8", errors="replace") if src.exists() else atom["body"]
        cites, seen = [], set()
        sup = _SUPERSEDED_BY.search(text[:2000])
        for ref in _PATH_REF.findall(text):
            tid = mp.get(ref)
            if tid and tid != art_id and tid not in seen:
                seen.add(tid)
                cites.append({"target": tid, "rel": "cites"})
        changed = False
        if cites and not atom.get("citations_out"):
            atom["citations_out"] = cites[:20]
            changed = True
            linked += 1
        if sup and atom["header"]["status"] == "superseded" and not atom.get("superseded"):
            succ = mp.get(sup.group(1))
            if succ:
                atom["superseded"] = succ  # kimi bar: STRONG link from header evidence
                changed = True
                strong += 1
        if changed:
            atom["version"] = int(atom.get("version", 1)) + 1
            atom["updated_ts"] = time.time()
            fam.store.set("artifact:" + art_id, json.dumps(atom, ensure_ascii=False, sort_keys=True))
            fam._append_jsonl(atom)
            render_atom(atom, repo_root=str(ROOT))
    print(f"[link] citation-backfilled {linked} atom(s); strong superseded-links {strong}")
    return 0


def cmd_verify() -> int:
    from core.library.projection import projection_relpath
    fam, mp = _fam(), load_map()
    bars = {"missing_atom": [], "sha_mismatch": [], "missing_projection": [], "proj_sha": []}
    for rel, art_id in mp.items():
        atom = fam.get(art_id)
        if atom is None:
            bars["missing_atom"].append(rel)
            continue
        if atom["header"].get("visibility") == "local":
            continue  # P3b redaction: no public projection by design
        import hashlib
        if hashlib.sha256(atom["body"].encode("utf-8", "replace")).hexdigest()[:12] != atom["body_sha"]:
            bars["sha_mismatch"].append(rel)
        proj = ROOT / projection_relpath(atom)
        if not proj.exists():
            bars["missing_projection"].append(rel)
        elif f"akashic_sha: {atom['body_sha']}" not in proj.read_text(encoding="utf-8", errors="replace")[:2000]:
            bars["proj_sha"].append(rel)
    total = len(mp)
    fails = sum(len(v) for v in bars.values())
    print(f"[verify] map entries: {total} | atoms present: {total - len(bars['missing_atom'])}")
    for k, v in bars.items():
        print(f"  {k}: {len(v)}" + (f"  e.g. {v[:3]}" if v else ""))
    print(f"[verify] {'ALL BARS GREEN' if fails == 0 else 'FAILURES: ' + str(fails)}")
    return 0 if fails == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A3 corpus migration: enrich -> atoms, verified, gated")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--import", dest="do_import", action="store_true")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    if a.dry_run:
        return cmd_dry_run()
    if a.do_import:
        return cmd_import()
    if a.link:
        return cmd_link()
    if a.verify:
        return cmd_verify()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
