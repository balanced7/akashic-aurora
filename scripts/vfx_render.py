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

Every verb takes --say, and there is a bare `say` verb for narration with no render. Both post to
the bench's live feed, which the open page renders into the thread NEXT TO THE IMAGE. That closes
the last asymmetry here: Daniil's chat box has always attached a snapshot so claude could look at
what he meant, while claude could only send words back about pictures Daniil could not see.

    py scripts/vfx_render.py state --state thinking --identity claude
    py scripts/vfx_render.py thumb --chunk swirl --say "the reference, before I touch gap"
    py scripts/vfx_render.py sheet --frames 12 --to 8
    py scripts/vfx_render.py grid --a thick --a-from 0 --a-to 1 --b gap --b-from 0.004 --b-to 0.18
    py scripts/vfx_render.py say "that read as glow because round turns tile area into gap"
    py scripts/vfx_render.py ingest --name tunnel --file shadertoy.txt
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


def say(text, kind="say", label=""):
    """Narrate into the open bench. The counterpart to Daniil's chat box: his messages carry a
    snapshot so claude can look, and until now claude's carried nothing back but words on a bus
    that arrive a turn later. This lands on the page NOW, next to the render it is about."""
    try:
        r = _post("/vfx/feed", {"text": text, "kind": kind, "label": label, "from": "claude"})
    except urllib.error.URLError as exc:
        print("the console is not running on %s (%s)" % (BASE, exc), file=sys.stderr)
        return 2
    return 0 if r.get("ok") else 1


def ingest(ns):
    """Paste a Shadertoy shader in, get a preview out.

    ONE MOTION, on purpose. Ingesting and then looking are the same act -- a stored shader nobody
    has rendered is an unverified claim that it compiles, and the compile error is the single most
    likely outcome of importing a stranger's code. So the preview is the default and the shader's
    own translation notes ride along as the reason, which puts "needs a texture you do not have"
    directly above the picture that failed to render.

    A CONTACT SHEET rather than a still, also on purpose: almost every Shadertoy shader is a
    function of time, and a still cannot tell a shader that is moving from one that is broken and
    happens to be dark. --frames 1 gives the still when the still is what you want.
    """
    if ns.text:
        src = ns.text
    elif ns.file == "-":
        src = sys.stdin.read()
    elif ns.file:
        with open(ns.file, "r", encoding="utf-8") as fh:
            src = fh.read()
    else:
        print("ingest needs --file PATH (or - for stdin) or --text", file=sys.stderr)
        return 2

    try:
        r = _post("/vfx/ingest", {"name": ns.name, "src": src})
    except urllib.error.URLError as exc:
        print("the console is not running on %s (%s)" % (BASE, exc), file=sys.stderr)
        return 2
    if not r.get("ok"):
        print("ingest failed: %s" % r.get("error", "unknown"), file=sys.stderr)
        return 1

    # The notes go to stderr so the PATH stays the only thing on stdout -- the whole tool is built
    # around that path being pipeable into a Read.
    for n in r.get("notes", []):
        print("  . %s" % n, file=sys.stderr)
    for w in r.get("warnings", []):
        print("  ! %s" % w, file=sys.stderr)
    print("stored design/vfx-sketches/%s.frag (%d bytes)" % (r["name"], r["bytes"]), file=sys.stderr)

    if ns.no_preview:
        return say("ingested `%s` -- %s" % (r["name"], r.get("summary", "")))

    # --say overrides the generated reason: the translation summary is a good default and a poor
    # substitute for knowing WHY this shader was worth importing.
    why = getattr(ns, "say", None) or ("ingested `%s` -- %s" % (r["name"], r.get("summary", "")))
    if r.get("warnings"):
        why += ". " + " ".join(r["warnings"])
    args = {"name": r["name"], "cell": ns.cell, "out": "ingest-" + r["name"], "say": why}
    if ns.frames and ns.frames > 1:
        args.update({"frames": ns.frames, "cols": ns.cols, "from": ns.from_, "to": ns.to})
    else:
        args["t"] = ns.t
    return submit("sketch", args)


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
        return 3
    # And distinguish "no tab" from "a tab, but it is hidden". Both look identical from here -- a
    # job that never moves -- and the fixes are different sentences, so guessing wastes the very
    # minutes the tool exists to save.
    try:
        r = _get("/vfx/renderer")
    except Exception:
        r = {}
    if r.get("attached") and not r.get("visible"):
        print("the /vfx tab is HIDDEN, so it cannot render: bring it to the front", file=sys.stderr)
    elif r.get("attached"):
        print("a renderer is attached (%s) but took no job in %ss -- reload %s/vfx"
              % (r.get("worker", "?"), wait, BASE), file=sys.stderr)
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

    p = sub.add_parser("script", help="build in the OPEN bench, step by step, so it can be watched")
    p.add_argument("--file", help="path to a JSON list of steps")
    p.add_argument("--json", help="inline JSON list of steps")
    p.add_argument("--name", help="name for the final snapshot")

    p = sub.add_parser("graph", help="render a saved graph JSON (or whatever is on the bench)")
    p.add_argument("--file", help="path to a graph JSON; omit to render the bench's current graph")
    p.add_argument("--cell", type=int, default=320)
    p.add_argument("--name")

    p = sub.add_parser("ingest", help="paste a Shadertoy shader in; get a compiled preview back")
    p.add_argument("--name", required=True, help="scratch slot name, without .frag")
    p.add_argument("--file", help="path to the shader source, or - for stdin")
    p.add_argument("--text", help="the shader source inline")
    p.add_argument("--cell", type=int, default=200)
    p.add_argument("--frames", type=int, default=6, help="contact sheet frames; 1 = a single still")
    p.add_argument("--cols", type=int, default=3)
    p.add_argument("--from", dest="from_", type=float, default=0.0)
    p.add_argument("--to", type=float, default=6.0)
    p.add_argument("--t", type=float, default=1.0, help="time for a single still")
    p.add_argument("--no-preview", dest="no_preview", action="store_true",
                   help="store it without rendering")

    p = sub.add_parser("say", help="narrate into the open bench, with no render")
    p.add_argument("text", nargs="+")

    # Every render can carry its reason, and they travel together because separating them is what
    # made the old feed useless: a picture with no intent is decoration, and an intent whose
    # picture is somewhere else is a claim you have to go check. Attached to the SUBPARSERS rather
    # than typed six times, so a verb added later inherits it instead of quietly lacking it.
    for _vn, _vp in sub.choices.items():
        if _vn != "say":
            _vp.add_argument("--say", help="narrate this render into the open bench")

    ns = ap.parse_args()
    if ns.op == "say":
        return say(" ".join(ns.text))
    if ns.op == "ingest":
        return ingest(ns)
    args = {k: v for k, v in vars(ns).items() if k != "op" and v is not None}
    if "from_" in args:
        args["from"] = args.pop("from_")
    if ns.op == "script":
        raw = args.pop("json", None)
        f = args.pop("file", None)
        if f:
            with open(f, "r", encoding="utf-8") as fh:
                raw = fh.read()
        if not raw:
            print("script needs --file or --json", file=sys.stderr)
            return 2
        args["steps"] = json.loads(raw)
    if ns.op == "graph" and args.get("file"):
        with open(args.pop("file"), "r", encoding="utf-8") as fh:
            args["graph"] = json.load(fh)
    return submit(ns.op, args)


if __name__ == "__main__":
    sys.exit(main())
