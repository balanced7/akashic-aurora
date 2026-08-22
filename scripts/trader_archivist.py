"""P0b — the archivist: forward-accruing, self-stamped capture of niche semi sources.

Born 2026-08-22 from the semi-signal-paper-trader arc (design r2 + case bench, Daniil's
gate via "order and direction are up to you"). The point-in-time law this serves: a
Tier-C narrative source (paywalled/deletable/retro-editable) becomes Tier-B evidence
ONLY through a snapshot WE stamped. The archive accrues forward; history stays honest
by never being backfilled — a fetch records when WE knew, which is the only timestamp
we can ever prove. (Heimdall's Q1 tiers; the cap on the past becomes the moat on the
future.)

Shape: append-only. items/<sha16>.html + <sha16>.meta.json per item; manifest.jsonl is
the ledger (one line per NEW capture; re-runs are idempotent by URL). No edits, no
deletes — supersession only, matching the substrate law. PAPER-ONLY project charter:
this file fetches public pages and records timestamps; it knows nothing of markets.

Run:  py scripts/trader_archivist.py            (fetch all sources once)
      py scripts/trader_archivist.py --dry      (list what would be fetched)
Cadence: manual / external scheduler for now; daemon fold-in is a gated follow-up.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import requests

_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = _ROOT / "state" / "trader" / "archive"
ITEMS = ARCHIVE / "items"
MANIFEST = ARCHIVE / "manifest.jsonl"

#: The college core, RSS-able tier. YouTube-first sources (MLID, TechTechPotato) need
#: channel-id feeds — a follow-up, not a blocker; absence here is a TODO, not a verdict.
SOURCES = [
    {"id": "semiaccurate", "feed": "https://www.semiaccurate.com/feed/"},
    {"id": "semianalysis", "feed": "https://semianalysis.com/feed/"},
    {"id": "semianalysis-substack", "feed": "https://semianalysis.substack.com/feed"},
    # Round 2 (Daniil's source-atlas ask, 2026-08-22): the RSS-able kin tier.
    {"id": "chipsandcheese", "feed": "https://chipsandcheese.com/feed"},
    {"id": "morethanmoore", "feed": "https://morethanmoore.substack.com/feed"},
    {"id": "phoronix", "feed": "https://www.phoronix.com/rss.php"},
    {"id": "semiengineering", "feed": "https://semiengineering.com/feed/"},
    {"id": "nextplatform", "feed": "https://www.nextplatform.com/feed/"},
    {"id": "servethehome", "feed": "https://www.servethehome.com/feed/"},
    {"id": "fabricatedknowledge", "feed": "https://www.fabricatedknowledge.com/feed"},
]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) akashic-archivist/0.1 "
                    "(point-in-time corpus; contact: local research)"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seen_urls() -> set:
    seen = set()
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["url"])
            except Exception:
                continue                      # a corrupt line never blocks capture
    return seen


def _parse_feed(xml_text: str):
    """RSS 2.0 and Atom, stdlib-only. Yields {url, title, published_claim}."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return
    # RSS 2.0
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        if link:
            yield {"url": link,
                   "title": (item.findtext("title") or "").strip(),
                   "published_claim": (item.findtext("pubDate") or "").strip()}
    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.iter(f"{ns}entry"):
        link_el = entry.find(f"{ns}link")
        link = (link_el.get("href") if link_el is not None else "") or ""
        if link.strip():
            yield {"url": link.strip(),
                   "title": (entry.findtext(f"{ns}title") or "").strip(),
                   "published_claim": (entry.findtext(f"{ns}published")
                                       or entry.findtext(f"{ns}updated") or "").strip()}


def capture(dry: bool = False) -> dict:
    ITEMS.mkdir(parents=True, exist_ok=True)
    seen = _seen_urls()
    stats = {"sources_ok": 0, "sources_failed": 0, "new": 0, "skipped_seen": 0,
             "fetch_failed": 0}
    for src in SOURCES:
        try:
            r = requests.get(src["feed"], headers=UA, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"[archivist] source FAILED {src['id']}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            stats["sources_failed"] += 1
            continue
        stats["sources_ok"] += 1
        for entry in _parse_feed(r.text):
            url = entry["url"]
            if url in seen:
                stats["skipped_seen"] += 1
                continue
            if dry:
                print(f"[dry] would fetch: {url}")
                stats["new"] += 1
                continue
            try:
                page = requests.get(url, headers=UA, timeout=25)
                body = page.text
                status = page.status_code
            except Exception as e:
                # The failure is itself a point-in-time fact worth a manifest line —
                # "we tried at T and could not read it" beats silent absence.
                body, status = "", f"fetch-error:{type(e).__name__}"
                stats["fetch_failed"] += 1
            sha = hashlib.sha256(url.encode() + body.encode(errors="ignore")).hexdigest()
            short = sha[:16]
            if body:
                (ITEMS / f"{short}.html").write_text(body, encoding="utf-8",
                                                     errors="ignore")
            meta = {"url": url, "title": entry["title"], "source": src["id"],
                    "published_claim": entry["published_claim"],   # the FEED'S claim
                    "fetched_at": _now_utc(),                      # OUR stamp: Tier-B
                    "http_status": status, "sha256": sha,
                    "bytes": len(body.encode("utf-8", errors="ignore"))}
            (ITEMS / f"{short}.meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            with open(MANIFEST, "a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            seen.add(url)
            stats["new"] += 1
            time.sleep(1.0)                    # politeness; we are guests on their sites
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    s = capture(dry=args.dry)
    print(f"[archivist] {_now_utc()}  ok_sources={s['sources_ok']} "
          f"failed_sources={s['sources_failed']} new={s['new']} "
          f"seen_skipped={s['skipped_seen']} fetch_failed={s['fetch_failed']}")
