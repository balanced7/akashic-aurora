"""arsenal command line: serve | plan | inspect | probe | analyze | takes | tiktok.

Run from the repo root (or with PYTHONPATH pointing at it):  py -m arsenal serve
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal", description="Daniel's modular media suite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the local First Light server on 127.0.0.1")
    s.add_argument("--port", type=int, default=8793)
    s.add_argument("--root", action="append", help="a library root; repeat for more (default: E:\\Video Output E)")
    s.add_argument("--performance-root", metavar="PATH",
                   help="where practice-log sessions are stored (default: state/arsenal/performance)")
    s.add_argument("--no-performance-log", action="store_true",
                   help="switch the practice-log routes off (they answer 404, like a server from before them)")

    p = sub.add_parser("plan", help="print the loud plan for a graph (.json, or the text form)")
    p.add_argument("graph")

    i = sub.add_parser("inspect", help="print a module manifest, or list the modules")
    i.add_argument("module", nargs="?")

    pr = sub.add_parser("probe", help="probe a media file with FFmpeg (via PyAV)")
    pr.add_argument("path")
    pr.add_argument("--hw", action="store_true", help="also test hardware decode")

    an = sub.add_parser("analyze", help="compute timestamped audio features")
    an.add_argument("path")
    an.add_argument("--out")

    sb = sub.add_parser("storyboard",
                        help="dynamic capture: score a video's motion, segment it into settled "
                             "runs and transitions, and write a contact sheet + manifest")
    sb.add_argument("path")
    sb.add_argument("--fps", type=float, default=None, help="analysis sampling rate (default 5)")
    sb.add_argument("--width", type=int, default=None, help="downscale before scoring (default 480)")
    sb.add_argument("--out", help="output directory (default state/arsenal/storyboards/<stem>)")
    sb.add_argument("--frames", action="store_true", help="also write one PNG per kept pick")
    sb.add_argument("--json", action="store_true", help="print the whole manifest")

    mo = sub.add_parser("motion",
                        help="how a take MOVES: pacing read from a storyboard manifest (or a "
                             "video, analysed first) -- so a seat that cannot watch the video "
                             "can still compare twenty takes")
    mo.add_argument("path", nargs="?", help="a storyboard.json, or a video to analyse first")
    mo.add_argument("--dir", help="profile every storyboard.json under this directory, as a bank")
    mo.add_argument("--json", action="store_true")

    cp = sub.add_parser("coupling",
                        help="audio-coupling census of the preset bank: which channels each "
                             "preset actually reads, and how deeply")
    cp.add_argument("--dir", help="a preset directory (default arsenal/web/presets)")
    cp.add_argument("--json", action="store_true")

    fl = sub.add_parser("floors",
                        help="visual floors: pinned checks on a rendered frame (dead, blown, "
                             "flat, illegible) -- so an eye is never spent on a histogram")
    fl.add_argument("path", nargs="?", help="an image or video frame")
    fl.add_argument("--dir", help="census mode: lint every matching frame under this directory")
    fl.add_argument("--pattern", default="*.jpg", help="census glob (default *.jpg; .png is added)")
    fl.add_argument("--region", help="fractional crop x,y,w,h in 0..1 (e.g. 0,0.06,0.6,0.86)")
    fl.add_argument("--floors", help="comma-separated subset: not_dead,not_blown,variety,legibility")
    fl.add_argument("--set", dest="floor_set", choices=["canvas", "label", "frame"],
                    help="named floor set by target (canvas: not_dead,variety,not_blown; "
                         "label: legibility; frame: all)")
    fl.add_argument("--no-exempt", action="store_true",
                    help="ignore declared expected-absence: report the raw red (an exemption "
                         "hides a red, never the measurement, so the numbers stay either way)")
    fl.add_argument("--json", action="store_true")

    sub.add_parser("takes", help="list recorded takes")

    tk = sub.add_parser(
        "tiktok",
        help="make a ready-to-post TikTok copy of a recording: cut the black borders, trim the "
             "silence, 1080x1920",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Make a ready-to-post TikTok copy of a screen recording.\n\n"
                    "It finds the picture inside the black borders (ignoring the mouse pointer and\n"
                    "thin tabs at the screen edge), cuts the borders off, makes it tall 1080x1920,\n"
                    "starts half a second before the first note and ends two seconds after the last,\n"
                    "evens out the loudness, and saves a phone-friendly MP4 next to the original,\n"
                    "named '<name> tiktok.mp4'. The original is never changed.\n\n"
                    "A long recording (TikTok stops at 10 minutes) is cut to a window with --from and\n"
                    "--to: the borders, the silence and the loudness are all read inside the window,\n"
                    "a copy that starts or ends in the middle of a note fades in or out, and the copy\n"
                    "is named '<name> tiktok 28-52-end.mp4' so it sits beside the other copies.",
        epilog="examples:\n"
               "  py -m arsenal tiktok \"E:\\Video Output E\\my take.mp4\"\n"
               "      makes \"my take tiktok.mp4\" beside it\n"
               "  py -m arsenal tiktok --latest --dry-run --preview\n"
               "      checks the newest recording: prints the box, the trim and the ffmpeg command,\n"
               "      saves a preview picture, and encodes nothing\n"
               "  py -m arsenal tiktok --latest --from 28:52\n"
               "      the newest recording from 28:52 to its end (the keeper at the end of a long take),\n"
               "      saved as \"<name> tiktok 28-52-end.mp4\"; add --to 31:00 to stop there\n\n"
               "Tip: drag videos onto arsenal\\tools\\tiktok-ready.cmd to do the same without typing.")
    tk.add_argument("videos", nargs="*", metavar="video", help="one or more recordings (.mp4, .mkv, .mov)")
    tk.add_argument("--latest", action="store_true",
                    help="use the newest recording in --folder instead of naming one")
    tk.add_argument("--folder", metavar="DIR",
                    help="where --latest looks (default: the library folder 'py -m arsenal serve' uses)")
    tk.add_argument("--from", dest="start", metavar="TIME",
                    help="start the copy here instead of at the start of the recording; TIME is seconds "
                         "(1732 or 1731.6), m:ss (28:52 or 28:52.5) or h:mm:ss (1:05:03.2)")
    tk.add_argument("--to", dest="end", metavar="TIME",
                    help="end the copy here instead of at the end of the recording (same forms as --from)")
    tk.add_argument("--out", metavar="PATH",
                    help="a folder to save into, made if missing (a name with no extension, or ending "
                         "in \\, is a folder), or a file name ending in .mp4 (default: beside the original)")
    tk.add_argument("--force", action="store_true",
                    help="replace the output and the preview if they already exist "
                         "(the original is never replaced)")
    tk.add_argument("--dropped", action="store_true", help=argparse.SUPPRESS)  # set by tiktok-ready.cmd
    tk.add_argument("--dry-run", action="store_true",
                    help="show the box, the trim, the final size and the ffmpeg command; encode nothing")
    tk.add_argument("--preview", action="store_true",
                    help="also save '<name> tiktok-preview.jpg', one frame of the final framing")
    tk_shape = tk.add_mutually_exclusive_group()
    tk_shape.add_argument("--fit", dest="shape", action="store_const", const="fit",
                          help="show the whole picture, black bars where it does not reach (default)")
    tk_shape.add_argument("--fill", dest="shape", action="store_const", const="fill",
                          help="fill the whole phone screen, cutting the picture's edges to fit")
    tk.set_defaults(shape="fit")
    tk.add_argument("--no-trim", action="store_true", help="keep the silence at the start and the end")
    tk.add_argument("--lead", type=float, default=0.5, metavar="SECONDS",
                    help="start this long before the first sound (default 0.5)")
    tk.add_argument("--tail", type=float, default=2.0, metavar="SECONDS",
                    help="keep this long after the last sound, then fade out (default 2.0)")
    tk.add_argument("--lufs", type=float, default=-16.0, metavar="LUFS",
                    help="loudness target (default -16, right for phones)")
    tk.add_argument("--no-loudnorm", action="store_true", help="leave the loudness as recorded")
    tk.add_argument("--crf", type=int, default=17, metavar="N",
                    help="picture quality: lower is sharper and bigger (default 17)")
    tk.add_argument("--fps", choices=["auto", "30", "60"], default="auto",
                    help="frames per second (default auto: the recording's own, at most 60)")

    pf = sub.add_parser("performance", help="the piano practice log: list sessions, print a summary, prune")
    pf_sub = pf.add_subparsers(dest="perf_cmd", required=True)
    pf_list = pf_sub.add_parser("list", help="list practice sessions, newest first")
    pf_summary = pf_sub.add_parser("summary", help="print a session's summary.md (provisional if still open)")
    pf_summary.add_argument("session", help="a session id, or latest for the newest session")
    pf_prune = pf_sub.add_parser("prune", help="list sessions older than N days; delete them only with --yes")
    pf_prune.add_argument("--older-than-days", type=float, required=True, metavar="N")
    pf_prune.add_argument("--yes", action="store_true", help="really delete the listed sessions")
    for parser in (pf_list, pf_summary, pf_prune):
        parser.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")

    args = ap.parse_args(argv)

    if args.cmd == "serve":
        from .serve import serve
        serve(port=args.port, roots=args.root, performance_root=args.performance_root,
              performance_log=not args.no_performance_log)
        return 0

    if args.cmd == "plan":
        from .graph import GraphError, load_graph, parse_text
        from .plan import make_plan, render_plan
        from .registry import load_registry
        registry = load_registry()
        source = Path(args.graph).read_text(encoding="utf-8")
        try:
            obj = json.loads(source) if args.graph.lower().endswith(".json") else parse_text(source, registry)
            print(render_plan(make_plan(load_graph(obj), registry)))
        except GraphError as exc:
            print("the graph does not validate:", file=sys.stderr)
            for problem in exc.problems:
                print(f"  - {problem}", file=sys.stderr)
            return 2
        return 0

    if args.cmd == "inspect":
        from .registry import load_registry
        registry = load_registry()
        if not args.module:
            print("\n".join(registry.ids()))
            return 0
        try:
            print(json.dumps(registry.get(args.module), indent=2))
        except KeyError:
            print(f"no module {args.module!r}; try: py -m arsenal inspect", file=sys.stderr)
            return 2
        return 0

    if args.cmd == "probe":
        from . import analysis
        result = analysis.probe(args.path)
        if args.hw:
            result["hwdecode"] = analysis.hw_decode_evidence(args.path)
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "analyze":
        from . import analysis
        features = analysis.audio_features(args.path)
        rows = len(features.get("frames") or [])
        if args.out:
            Path(args.out).write_text(json.dumps(features), encoding="utf-8")
            print(f"wrote {rows} rows to {args.out}")
        else:
            summary = {k: v for k, v in features.items() if k != "frames"}
            summary["rows"] = rows
            print(json.dumps(summary, indent=2))
        return 0

    if args.cmd == "motion":
        from . import motion as mo_mod
        if args.dir:
            profiles = mo_mod.profile_many(args.dir)
            if not profiles:
                print(f"no storyboard.json under {args.dir}", file=sys.stderr)
                return 2
            if args.json:
                print(json.dumps(profiles, indent=2))
            else:
                for p in profiles:
                    name = str(p["source"] or "(unknown source)").replace("\\", "/").split("/")[-1]
                    print(f"  [{str(p['read']):<7}] {name:<30} {p['transitions']:>3} transition(s) "
                          f"in {p['duration_s']}s -> {p['transitions_per_min']}/min, "
                          f"longest calm {p['longest_calm_s']}s")
            return 0
        if not args.path:
            print("give a storyboard.json (or a video), or --dir for a bank", file=sys.stderr)
            return 2
        manifest = args.path
        if Path(args.path).suffix.lower() != ".json":
            from . import storyboard as sb_mod
            manifest = sb_mod.analyse(args.path)
        p = mo_mod.profile(manifest)
        if args.json:
            print(json.dumps(p, indent=2))
        else:
            print(f"{p['source']}  {p['duration_s']}s  read={p['read']}")
            for key in ("transitions", "settled", "transitions_per_min", "transition_fraction",
                        "median_transition_ms", "p90_transition_ms", "max_transition_ms",
                        "median_settled_ms", "longest_calm_s", "peak_median", "stride_ms"):
                print(f"  {key:<22} {p[key]}")
            for note in p.get("not_measured") or []:
                print(f"  not measured: {note}")
            for note in p["blind"]:
                print(f"  blind: {note}")
        return 0

    if args.cmd == "storyboard":
        from . import storyboard as sb_mod
        kw = {}
        if args.fps is not None:
            kw["fps"] = args.fps
        if args.width is not None:
            kw["width"] = args.width
        manifest = sb_mod.storyboard(args.path, out_dir=args.out, write_frames=args.frames, **kw)
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print(f"examined {manifest['frames_examined']} frame(s) at {manifest['sampling']['fps']} fps")
            print(f"  settled runs: {manifest['settled']}")
            print(f"  transitions : {manifest['transitions']}")
            for seg in manifest["segments"]:
                if seg["kind"] == "transition":
                    print(f"    {seg['start_s']:>8.3f}s -> {seg['end_s']:>8.3f}s  "
                          f"{seg['duration_ms']:>6} ms  peak {seg['peak_score']}")
            print(f"  picks kept  : {len(manifest['picks'])} of {manifest['picks_before_dedupe']}")
            print(f"  sheet       : {'written' if manifest['sheet_written'] else 'NOT written'}")
            print(f"  manifest    : {manifest['manifest_path']}")
        return 0

    if args.cmd == "coupling":
        from .presets import coupling_table
        rows = coupling_table(args.dir)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'preset':<20} {'verdict':<10} {'distinct':>8} {'refs':>5}  channels")
            for r in rows:
                channels = ", ".join(f"{k} x{v}" for k, v in sorted(r["used"].items(),
                                                                     key=lambda kv: -kv[1])) or "-"
                print(f"{r['id']:<20} {r['verdict']:<10} {r['distinct']:>8} {r['references']:>5}  {channels}")
            counts = {}
            for r in rows:
                counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
            print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        return 0

    if args.cmd == "floors":
        from . import floors as fl_mod
        region = None
        if args.region:
            try:
                region = tuple(float(p) for p in args.region.split(","))
                if len(region) != 4:
                    raise ValueError
            except ValueError:
                print("--region wants four fractions: x,y,w,h (e.g. 0,0.06,0.6,0.86)", file=sys.stderr)
                return 2
        names = [n.strip() for n in args.floors.split(",")] if args.floors else None
        if names is None and args.floor_set:
            names = fl_mod.SETS[args.floor_set]
        # Declared exemptions are ON by default, because a lane that cannot honour a declared
        # absence tends to grow an UNDECLARED one instead. --no-exempt asks for the raw red.
        exemptions = [] if args.no_exempt else None
        if args.dir:
            receipts = fl_mod.sweep(args.dir, pattern=args.pattern, region=region, floors=names,
                                    exemptions=exemptions)
            if not receipts:
                print(f"no frames matched {args.pattern} under {args.dir}", file=sys.stderr)
                return 2
            summary = fl_mod.summarise(receipts)
            if args.json:
                print(json.dumps({"summary": summary, "receipts": receipts}, indent=2))
            else:
                for r in receipts:
                    def _shown(res):
                        return (f"{res['floor']}("
                                + ", ".join(f"{k}={v}" for k, v in (res.get("measured") or {}).items())
                                + ")")
                    excused = [_shown(res) for res in r["results"] if "exempt" in res]
                    bad = [_shown(res) for res in r["results"]
                           if not res["pass"] and "exempt" not in res]
                    verdict = r.get("verdict") or ("pass" if r["pass"] else "fail")
                    mark = {"pass": "ok    ", "exempt": "EXEMPT", "fail": "FAIL  "}[verdict]
                    name = str(r["frame"]).split("receipts")[-1].lstrip("\\/")
                    print(f"  [{mark}] {name}")
                    for b in bad:
                        print(f"          {b}")
                    if excused:
                        ids = sorted({res["exempt"]["id"] for res in r["results"] if "exempt" in res})
                        for e in excused:
                            print(f"          {e}  <- measured, declared: {', '.join(ids)}")
                hard = [r for r in receipts
                        if (r.get("verdict") or ("pass" if r["pass"] else "fail")) == "fail"]
                line = (f"census: {summary['frames']} frame(s) -- {summary['passed']} pass, "
                        f"{summary['failed']} fail, {summary['unreadable']} unreadable")
                if summary["exempt"]:
                    line += f", {summary['exempt']} declared-exempt"
                if summary["pass_rate"] is not None:
                    line += f", pass rate {summary['pass_rate']}"
                print(line)
                if summary["failures_by_floor"]:
                    print("  failures by floor: " + ", ".join(f"{k}={v}" for k, v in
                                                              summary["failures_by_floor"].items()))
                if summary["exempted_floors"]:
                    print("  exempted floors: " + ", ".join(f"{k}={v}" for k, v in
                                                            summary["exempted_floors"].items()))
                if summary["declarations_unused"]:
                    print("  declarations that matched NOTHING (stale, or the frames moved): "
                          + ", ".join(summary["declarations_unused"]))
                for note in summary["blind"]:
                    print(f"  blind: {note}")
            return 0 if not hard else 1
        if not args.path:
            print("give a frame path, or --dir for a census", file=sys.stderr)
            return 2
        receipt = fl_mod.check(args.path, region=region, floors=names, exemptions=exemptions)
        if args.json:
            print(json.dumps(receipt, indent=2))
        else:
            print(f"{receipt['frame']}  {receipt['size'][0]}x{receipt['size'][1]}"
                  + (f"  region={region}" if region else ""))
            for r in receipt["results"]:
                mark = "ok    " if r["pass"] else ("EXEMPT" if "exempt" in r else "FAIL  ")
                measured = ", ".join(f"{k}={v}" for k, v in (r.get("measured") or {}).items())
                print(f"  [{mark}] {r['floor']:<11} {measured or r.get('error', '')}")
                if "exempt" in r:
                    ex = r["exempt"]
                    print(f"           declared: {ex['id']} -- {ex['reason']} "
                          f"(owner {ex['owner']}, {ex['date']})")
            verdict = receipt.get("verdict") or ("pass" if receipt["pass"] else "fail")
            print(f"  verdict: {verdict}")
        return 0 if (receipt.get("verdict")
                     or ("pass" if receipt["pass"] else "fail")) != "fail" else 1

    if args.cmd == "takes":
        from .take import TakeLedger
        for take in TakeLedger().list():
            state = "closed" if take["closed"] else "open  "
            print(f"{take['take_id']}  {state}  {take['event_count']:>6} events  {take.get('clip') or ''}")
        return 0

    if args.cmd == "tiktok":
        from .tiktok import run_cli
        return run_cli(args)

    if args.cmd == "performance":
        from .performance import PerformanceError, PerformanceStore
        store = PerformanceStore(args.root)
        if args.perf_cmd == "list":
            sessions = store.list()
            if not sessions:
                print(f"no practice sessions under {store.root}")
            for s in sessions:
                state = "closed" if s["closed"] else "open  "
                print(f"{s['session']}  {state}  {s['event_count']:>6} events  {s['duration_s']:>8.1f} s")
            return 0
        if args.perf_cmd == "prune":
            if args.older_than_days < 0:
                print("--older-than-days must be 0 or more", file=sys.stderr)
                return 2
            rows = store.older_than(args.older_than_days)
            if not rows:
                print(f"nothing older than {args.older_than_days:g} days under {store.root}")
                return 0
            for s in rows:
                state = "closed" if s["closed"] else "open  "
                print(f"{s['session']}  {state}  {s['event_count']:>6} events  opened {s['opened_at']}")
            if not args.yes:
                print(f"{len(rows)} sessions older than {args.older_than_days:g} days; nothing deleted. "
                      f"Add --yes to delete them.")
                return 0
            for s in rows:
                store.delete(s["session"])
            print(f"deleted {len(rows)} sessions from {store.root}")
            return 0
        session = args.session
        if session == "latest":
            session = store.latest()
            if session is None:
                print(f"no practice sessions under {store.root}", file=sys.stderr)
                return 2
        try:
            text = store.markdown(session)
        except PerformanceError as exc:
            print(f"{exc}; try: py -m arsenal performance list", file=sys.stderr)
            return 2
        # summary.md has arrows and note names; write UTF-8 even when stdout is a cp1252 pipe.
        stream = getattr(sys.stdout, "buffer", None)
        if stream is not None:
            sys.stdout.flush()
            stream.write(text.encode("utf-8"))
            stream.flush()
        else:
            sys.stdout.write(text)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
