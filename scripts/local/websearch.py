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
    """(results, unresponsive_engines). SearXNG reports which engines refused it; returning only
    the results discards the single fact that separates "the web has nothing" from "we are
    blocked", and the caller cannot recover it."""
    url = f"{host}/search?q={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as f:
        data = json.loads(f.read().decode("utf-8", errors="replace"))
    unresponsive = [" ".join(str(x) for x in e) if isinstance(e, (list, tuple)) else str(e)
                    for e in (data.get("unresponsive_engines") or [])]
    out = []
    for r in (data.get("results") or [])[:n]:
        out.append({"title": (r.get("title") or "").strip(),
                    "url": r.get("url") or "",
                    "snippet": " ".join(((r.get("content") or "").strip()).split())[:240],
                    "engine": r.get("engine") or ""})
    return out, unresponsive


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        results, unresponsive = search(args.query, args.host.rstrip("/"), args.n)
    except Exception as e:
        print(f"search unavailable: {type(e).__name__}: {e}\n"
              f"(is the akashic-searxng container up? docker start akashic-searxng)", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"results": results, "unresponsive_engines": unresponsive}, indent=1))
        return 0 if (results or not unresponsive) else 2
    if not results:
        # ZERO IS NOT NO. An empty result set has two causes that look identical from here and
        # need opposite responses: the web genuinely has nothing, or every engine refused us.
        # Printing "(no results)" for both taught seats that a walled search meant an empty web
        # -- found live 2026-09-23 when a seat searched a rare name, got "(no results)", and
        # reported the subject did not exist. The control query "python programming language"
        # returned zero at the same moment, with brave/duckduckgo/startpage all CAPTCHA-blocked.
        if unresponsive:
            print("SEARCH IS WALLED -- this is NOT an empty web.", file=sys.stderr)
            for u in unresponsive:
                print(f"  refused: {u}", file=sys.stderr)
            print("  every configured engine refused; treat this as NO ANSWER, not as absence.",
                  file=sys.stderr)
            print("  drill: docker restart akashic-searxng  |  add engines in searxng settings.yml",
                  file=sys.stderr)
            return 2
        print("(no results) -- all engines answered; the web genuinely returned nothing")
        return 0
    if unresponsive:
        print(f"[partial: {len(unresponsive)} engine(s) refused -- "
              f"{', '.join(unresponsive)}]", file=sys.stderr)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
