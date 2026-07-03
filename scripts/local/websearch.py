#!/usr/bin/env python3
"""Web search for the local research fleet (R2) -- a CLI over the self-hosted SearXNG.

The local backend has no server-side WebSearch tool (that's an Anthropic-API feature),
so discovery goes through this door instead: SearXNG aggregates real engines locally,
free, key-less, private (container `akashic-searxng`, loopback-only port 8888).

Usage (what a research worker runs via Bash):
    py scripts/local/websearch.py "deepseek v4 technical report"
    py scripts/local/websearch.py "rocm rdna4 windows lora" --n 10 --json

Output is deliberately COMPACT (one result = two lines) -- worker context is the scarce
resource. Search finds candidates; the worker must still FETCH what it cites
(article-contract.md rule: fetch-before-cite).
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:8888"


def search(query: str, host: str, n: int):
    url = f"{host}/search?q={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as f:
        data = json.loads(f.read().decode("utf-8", errors="replace"))
    out = []
    for r in (data.get("results") or [])[:n]:
        out.append({"title": (r.get("title") or "").strip(),
                    "url": r.get("url") or "",
                    "snippet": " ".join(((r.get("content") or "").strip()).split())[:240],
                    "engine": r.get("engine") or ""})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        results = search(args.query, args.host.rstrip("/"), args.n)
    except Exception as e:
        print(f"search unavailable: {type(e).__name__}: {e}\n"
              f"(is the akashic-searxng container up? docker start akashic-searxng)", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(results, indent=1))
        return 0
    if not results:
        print("(no results)")
        return 0
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
