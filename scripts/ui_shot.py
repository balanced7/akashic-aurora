#!/usr/bin/env python3
"""Headless screenshots of the live console -- the EYES half of the design loop.

WHY THIS EXISTS. design/CONTRACT.md organ 1 says no UI change ships without before/after
evidence from a sighted seat. But the harness browser pane only composites frames when it is
DISPLAYED on the operator's screen, so from a headless seat `computer{action:screenshot}` times
out, requestAnimationFrame never ticks, and CSS animations are held rather than run. That is the
literal open-loop finding of docs/library/report/20260723_the-ui-gap-... in miniature: the builder
cannot see its own output.

Patchright/Playwright is already a dependency of this repo (the gemini_web lane). Driving it
locally gives a real compositing browser, so a blind seat can SEE the console -- and can also
measure the things a held page cannot report: true frame timing, running animations, paint cost.

USAGE
  py scripts/ui_shot.py                          # both viewports -> artifacts/ui/
  py scripts/ui_shot.py --label before           # tag the set
  py scripts/ui_shot.py --url http://localhost:8787 --viewport 1280x860
  py scripts/ui_shot.py --fps                    # also sample real frame timing

The two default viewports are the contract's "two standard viewports": 1280x860 (desktop, where
the header row was measured overflowing by 399px) and 900x820 (the mid-size window where the
2026-07-23 audit found the layout shattering and the brand cropping to "ifrost").
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "artifacts", "ui")
DEFAULT_VIEWPORTS = ["1280x860", "900x820"]


def _launcher():
    """Patchright first (repo default, stealth-patched), plain Playwright as fallback."""
    try:
        from patchright.sync_api import sync_playwright  # type: ignore
        return sync_playwright, "patchright"
    except Exception:
        from playwright.sync_api import sync_playwright  # type: ignore
        return sync_playwright, "playwright"


FPS_PROBE = """
() => new Promise(resolve => {
  const frames = []; let last = performance.now(); const start = last;
  function tick(now){ frames.push(now - last); last = now;
    if (now - start < 2500) requestAnimationFrame(tick); else {
      const s = frames.slice(1).sort((a,b)=>a-b);
      if (!s.length) return resolve({error:'no frames'});
      const pct = p => s[Math.min(s.length-1, Math.floor(s.length*p))];
      const mean = s.reduce((a,b)=>a+b,0)/s.length;
      let running = 0;
      try { running = document.getAnimations().filter(a=>a.playState==='running').length; } catch(e){}
      resolve({ frames:s.length, meanMs:+mean.toFixed(2), fps:+(1000/mean).toFixed(1),
                p50:+pct(.5).toFixed(1), p95:+pct(.95).toFixed(1), worstMs:+s[s.length-1].toFixed(1),
                over16:s.filter(d=>d>16.7).length, over33:s.filter(d=>d>33).length,
                smoothPct:+((s.filter(d=>d<=17).length/s.length)*100).toFixed(1),
                runningAnimations: running });
    }}
  requestAnimationFrame(tick);
})
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("AKASHIC_UI_URL", "http://localhost:8787"))
    ap.add_argument("--viewport", action="append", default=None,
                    help="WxH; repeatable. Default: %s" % " ".join(DEFAULT_VIEWPORTS))
    ap.add_argument("--label", default="", help="tag for the filename set (e.g. before/after)")
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--settle", type=float, default=2.5,
                    help="seconds to let the feed/shader settle before shooting")
    ap.add_argument("--fps", action="store_true", help="also sample real frame timing")
    ap.add_argument("--full", action="store_true", help="full-page rather than viewport")
    a = ap.parse_args()

    viewports = a.viewport or DEFAULT_VIEWPORTS
    os.makedirs(a.out, exist_ok=True)
    sync_playwright, flavor = _launcher()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    tag = (a.label + "_") if a.label else ""
    report = {"url": a.url, "driver": flavor, "stamp": stamp, "shots": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
        try:
            for vp in viewports:
                try:
                    w, h = (int(x) for x in vp.lower().split("x"))
                except ValueError:
                    print(f"[ui_shot] bad viewport {vp!r}, skipping", file=sys.stderr)
                    continue
                page = browser.new_page(viewport={"width": w, "height": h},
                                        color_scheme="dark", device_scale_factor=1)
                entry = {"viewport": vp}
                try:
                    page.goto(a.url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    # networkidle can never settle on a console with live pollers -- that is
                    # NORMAL here, not a failure. Fall back to load and shoot anyway.
                    entry["nav_note"] = f"{type(e).__name__} (live pollers never idle) -- continued"
                    try:
                        page.goto(a.url, wait_until="load", timeout=30000)
                    except Exception as e2:
                        entry["error"] = f"navigation failed: {e2}"
                        report["shots"].append(entry)
                        page.close()
                        continue
                page.wait_for_timeout(int(a.settle * 1000))

                if a.fps:
                    try:
                        entry["perf"] = page.evaluate(FPS_PROBE)
                    except Exception as e:
                        entry["perf"] = {"error": str(e)}

                # console errors are free evidence while we are here
                errs = []
                page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                path = os.path.join(a.out, f"{tag}{vp}_{stamp}.png")
                page.screenshot(path=path, full_page=a.full)
                entry["path"] = path
                entry["bytes"] = os.path.getsize(path)
                if errs:
                    entry["consoleErrors"] = errs[:5]
                report["shots"].append(entry)
                print(f"[ui_shot] {vp} -> {path}")
                page.close()
        finally:
            browser.close()

    rp = os.path.join(a.out, f"{tag}report_{stamp}.json")
    with open(rp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
