#!/usr/bin/env python3
"""capture_apple_hig.py — harvest Apple HIG component sub-sections into refs/design-inspiration.

Daniel's charter (2026-07-23): "Lets capture both and all the visual data from every
sub section on apples guidelines page" — the components page and every component
sub-page under it: guidance text + EVERY image asset (light/dark, 1x/2x variants).

Mechanism: developer.apple.com serves each HIG page as structured JSON at
  /tutorials/data/documentation/humaninterfaceguidelines/<slug>.json
with image assets in `references` (type=image) pointing at docs-assets CDN. We walk
the components index's topicSections, fetch each sub-page's JSON, write the guidance
text as markdown, and download every image variant.

Output layout (refs/design-inspiration/apple-hig/ — GITIGNORED: copyrighted material stays local;
this script + INDEX.md are the committed, reproducible part):
  raw/<slug>.json          the page JSON verbatim
  text/<slug>.md           extracted guidance text
  images/<slug>/<file>     every image variant on that page
  INDEX.md                 committed: slug -> title/abstract/source URL/image count

Rerunnable: skips files that already exist (pass --force to refetch).
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://developer.apple.com"
DATA = BASE + "/tutorials/data/design/human-interface-guidelines/{slug}.json"
ROOT = Path(__file__).resolve().parent.parent / "design" / "refs" / "apple-hig"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DELAY = 0.25  # politeness between requests


def fetch(url: str, binary: bool = False, retries: int = 3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:  # noqa: BLE001 — log and retry; the summary reports misses
            if attempt == retries - 1:
                print(f"  MISS {url} ({type(e).__name__}: {e})", file=sys.stderr)
                return None
            time.sleep(1.0 + attempt)
    return None


def slug_of(identifier: str, refs: dict) -> str | None:
    """doc:// identifier -> HIG slug via its reference's url field."""
    ref = refs.get(identifier) or {}
    url = ref.get("url") or ""
    m = re.search(r"/human-interface-guidelines/([a-z0-9-]+)$", url)
    return m.group(1) if m else None


def extract_text(page: dict) -> str:
    """Flatten the page JSON's content sections to readable markdown."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("type")
            if t == "heading":
                out.append("\n" + "#" * min(node.get("level", 2) + 1, 6) + " " + node.get("text", ""))
            elif t == "text":
                out.append(node.get("text", ""))
            elif t == "codeVoice":
                out.append(f"`{node.get('code', '')}`")
            elif t == "reference":
                # keep the human-readable title if the identifier resolves
                out.append(node.get("title") or "")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for section in page.get("primaryContentSections") or []:
        walk(section)
    return re.sub(r"\n{3,}", "\n\n", " ".join(x for x in out if x).replace(" \n", "\n")).strip()


def harvest_page(slug: str, force: bool) -> dict | None:
    raw_p = ROOT / "raw" / f"{slug}.json"
    if raw_p.exists() and not force:
        page = json.loads(raw_p.read_text(encoding="utf-8"))
    else:
        page = fetch(DATA.format(slug=slug))
        if page is None:
            return None
        raw_p.parent.mkdir(parents=True, exist_ok=True)
        raw_p.write_text(json.dumps(page, indent=1), encoding="utf-8")
        time.sleep(DELAY)

    meta = page.get("metadata") or {}
    title = meta.get("title") or slug
    abstract = " ".join(a.get("text", "") for a in page.get("abstract") or [])

    text_p = ROOT / "text" / f"{slug}.md"
    if not text_p.exists() or force:
        text_p.parent.mkdir(parents=True, exist_ok=True)
        text_p.write_text(
            f"# {title}\n\n_{abstract}_\n\nSource: {BASE}/design/human-interface-guidelines/{slug}\n\n"
            + extract_text(page) + "\n",
            encoding="utf-8",
        )

    img_dir = ROOT / "images" / slug
    n_imgs = 0
    for ref in (page.get("references") or {}).values():
        if ref.get("type") != "image":
            continue
        for variant in ref.get("variants") or []:
            url = variant.get("url") or ""
            if url.startswith("/"):
                url = BASE + url
            if not url:
                continue
            name = url.rsplit("/", 1)[-1].split("?")[0]
            dest = img_dir / name
            if dest.exists() and not force:
                n_imgs += 1
                continue
            data = fetch(url, binary=True)
            if data:
                img_dir.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                n_imgs += 1
                time.sleep(DELAY)
    return {"slug": slug, "title": title, "abstract": abstract, "images": n_imgs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="refetch even if files exist")
    ap.add_argument("--root-slug", default="components")
    args = ap.parse_args()

    ROOT.mkdir(parents=True, exist_ok=True)
    index = fetch(DATA.format(slug=args.root_slug))
    if index is None:
        print("FATAL: components index unreachable", file=sys.stderr)
        return 1
    refs = index.get("references") or {}

    groups: list[tuple[str, list[str]]] = []
    for section in index.get("topicSections") or []:
        slugs = [s for s in (slug_of(i, refs) for i in section.get("identifiers") or []) if s]
        if slugs:
            groups.append((section.get("title") or "?", slugs))

    total = sum(len(s) for _, s in groups)
    print(f"[hig] level-1: {total} group page(s) across {len(groups)} section(s)")

    rows, misses = [], []
    seen: set[str] = set()
    done = 0
    for group, slugs in groups:
        for slug in slugs:
            if slug in seen:
                continue
            seen.add(slug)
            done += 1
            print(f"[L1 {done}/{total}] {slug}")
            r = harvest_page(slug, args.force)
            if r:
                r["group"] = group if group != "?" else r["title"]
                rows.append(r)
            else:
                misses.append(slug)

    # level 2: every group page's own topicSections are the REAL component
    # sub-sections (buttons, charts, toolbars, ...) — Daniel's "every sub section".
    group_rows = list(rows)
    for parent in group_rows:
        raw_p = ROOT / "raw" / f"{parent['slug']}.json"
        if not raw_p.exists():
            continue
        page = json.loads(raw_p.read_text(encoding="utf-8"))
        prefs = page.get("references") or {}
        children = []
        for section in page.get("topicSections") or []:
            children += [s for s in (slug_of(i, prefs) for i in section.get("identifiers") or []) if s]
        for slug in children:
            if slug in seen:
                continue
            seen.add(slug)
            print(f"[L2] {parent['title']} :: {slug}")
            r = harvest_page(slug, args.force)
            if r:
                r["group"] = parent["title"]
                rows.append(r)
            else:
                misses.append(slug)

    # the components landing page itself rides along
    root_row = harvest_page(args.root_slug, args.force)
    if root_row:
        root_row["group"] = "(root)"
        rows.append(root_row)

    lines = [
        "# Apple HIG components capture — INDEX",
        "",
        f"Captured {len(rows)} page(s), {sum(r['images'] for r in rows)} image file(s) "
        f"(variants counted); misses: {misses or 'none'}.",
        "Assets live beside this index (raw/, text/, images/) and are GITIGNORED —",
        "copyrighted material stays local; rerun scripts/capture_apple_hig.py to refetch.",
        "",
        "| Group | Component | Images | Source |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['group']} | [{r['title']}](text/{r['slug']}.md) | {r['images']} | "
            f"{BASE}/design/human-interface-guidelines/{r['slug']} |"
        )
    (ROOT / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[hig] DONE: {len(rows)} pages, {sum(r['images'] for r in rows)} images, "
          f"{len(misses)} miss(es) -> {ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
