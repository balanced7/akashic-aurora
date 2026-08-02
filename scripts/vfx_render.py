#!/usr/bin/env python3
"""Render something in the VFX bench from the command line, and get a file path back.

WHY THIS EXISTS. Every render this session cost claude four or five tool calls -- restart the
server, navigate the browser pane, inject JS, wait, read the result back -- and kept breaking on
pane quirks (frozen rAF, hidden tab, stale routes). Daniil's suggestion was the right one: give
claude a tool that "just pings the same script that we have in the vfx engine".

THE DESIGN DECISION IS WHERE THE GL RUNS, and there were three options:
  * port the shaders to Python + moderngl -- duplicates every shader into a second renderer that
    drifts silently until the two disagree and nobody knows which is right. No.
  * headless Chrome over CDP -- removes the tab dependency, but adds a browser driver and spawns a
    second GPU context on a host with a documented display-driver TDR history.
  * USE THE BENCH THAT IS ALREADY OPEN. The page has thumbShaderFor, renderSheet, renderGrid and
    snap; a job queue lets this CLI call THOSE EXACT FUNCTIONS. One implementation, two callers, so
    a CLI-requested render cannot disagree with a clicked one.

THE HONEST CONSTRAINT: a /vfx tab must be open. That is reported as "no renderer attached" rather
than left as a hang -- a diagnosis beats a mystery, and the fix (open the page) is one sentence.

    py scripts/vfx_render.py state --state thinking --identity claude
    py scripts/vfx_render.py thumb --chunk swirl
    py scripts/vfx_render.py sheet --frames 12 --to 8
    py scripts/vfx_render.py grid --a thick --a-from 0 --a-to 1 --b gap --b-from 0.004 --b-to 0.18
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8787"


def _post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=10))


def _get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=10))


def submit(op, args, wait=90):
    try:
        job = _post("/vfx/job", {"op": op, "args": args})
    except urllib.error.URLError as exc:
        print("the console is not running on %s (%s)" % (BASE, exc), file=sys.stderr)
        print("start it:  py scripts/bifrost_ui.py --port 8787", file=sys.stderr)
        return 2

    jid = job.get("id")
    print("queued %s (%s)" % (jid, op), file=sys.stderr)
    deadline = time.time() + wait
    picked_up = False
    while time.time() < deadline:
        time.sleep(0.6)
        try:
            cur = _get("/vfx/job/" + jid)
        except Exception:
            continue
        if cur.get("state") == "running":
            picked_up = True
        if cur.get("state") == "done":
            res = cur.get("result") or {}
            if res.get("ok"):
                # The PATH is the payload: claude reads the PNG with the Read tool and can then
                # actually LOOK at what it asked for, which is the whole point of the exercise.
                print(res.get("path") or json.dumps(res))
                return 0
            print("render failed: %s" % res.get("error", "unknown"), file=sys.stderr)
            return 1
    # Distinguish "nobody is listening" from "the render is slow" -- they need opposite responses.
    if picked_up:
        print("job %s was picked up but did not finish in %ss" % (jid, wait), file=sys.stderr)
    else:
        print("no renderer attached: open %s/vfx in a browser and leave the tab open" % BASE,
              file=sys.stderr)
    return 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="op", required=True)

    p = sub.add_parser("state", help="render one avatar state")
    p.add_argument("--state", default="thinking")
    p.add_argument("--style", default="geodesic")
    p.add_argument("--identity", default="claude")
    p.add_argument("--wire", type=float)
    p.add_argument("--see", type=float)
    p.add_argument("--cell", type=int, default=320)
    p.add_argument("--name")

    p = sub.add_parser("thumb", help="render one chunk against the calibration reference")
    p.add_argument("--chunk", required=True)
    p.add_argument("--cell", type=int, default=200)
    p.add_argument("--t", type=float, default=1.0)
    p.add_argument("--name")

    p = sub.add_parser("sheet", help="contact sheet: N frames over a time range, tiled")
    p.add_argument("--frames", type=int, default=12)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--cell", type=int, default=170)
    p.add_argument("--from", dest="from_", type=float, default=0.0)
    p.add_argument("--to", type=float, default=8.0)
    p.add_argument("--name")
    p.add_argument("--style", default="geodesic")
    p.add_argument("--chunk", help="render a chunk instead of a style")
    p.add_argument("--state")
    p.add_argument("--identity")

    p = sub.add_parser("grid", help="permutation grid: one param across, another down")
    p.add_argument("--a", required=True)
    p.add_argument("--a-from", dest="aFrom", type=float, required=True)
    p.add_argument("--a-to", dest="aTo", type=float, required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--b-from", dest="bFrom", type=float, required=True)
    p.add_argument("--b-to", dest="bTo", type=float, required=True)
    p.add_argument("--cols", type=int, default=5)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cell", type=int, default=150)
    p.add_argument("--t", type=float, default=2.0)
    p.add_argument("--name")
    p.add_argument("--style", default="geodesic")
    p.add_argument("--chunk", help="render a chunk instead of a style")
    p.add_argument("--state")
    p.add_argument("--identity")

    p = sub.add_parser("sketch", help="render a saved .frag; --frames turns it into a contact sheet")
    p.add_argument("--name", required=True, help="sketch name, without .frag")
    p.add_argument("--out", help="output file name")
    p.add_argument("--cell", type=int, default=320)
    p.add_argument("--t", type=float, default=0.0)
    p.add_argument("--frames", type=int)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--from", dest="from_", type=float, default=0.0)
    p.add_argument("--to", type=float, default=8.0)

    p = sub.add_parser("graph", help="render a saved graph JSON (or whatever is on the bench)")
    p.add_argument("--file", help="path to a graph JSON; omit to render the bench's current graph")
    p.add_argument("--cell", type=int, default=320)
    p.add_argument("--name")

    ns = ap.parse_args()
    args = {k: v for k, v in vars(ns).items() if k != "op" and v is not None}
    if "from_" in args:
        args["from"] = args.pop("from_")
    if ns.op == "graph" and args.get("file"):
        with open(args.pop("file"), "r", encoding="utf-8") as fh:
            args["graph"] = json.load(fh)
    return submit(ns.op, args)


if __name__ == "__main__":
    sys.exit(main())
