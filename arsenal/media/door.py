"""arsenal.media.door -- the video toolbox as MCP tools: `py -m arsenal.media.door` (stdio), or --http PORT.

Its own door, not grafted onto the knowledge door (ai_setup_mcp.py), so the knowledge door does not grow by twenty tools.
Each tool is a thin call into the same functions the CLI and the editor use, run in a worker thread so a long ffmpeg
call never blocks the server. Results are the house result dicts, made transcript-lean: long lists are cut to their
first rows with a count (the full result is always in its receipt file, named in the answer).

Editor tools edit the SAME project files as the web page, through edit.load -> an op -> edit.save, so a stale revision
is refused exactly as the page's PUT is: an agent and Daniel never overwrite each other.

Register (Daniel's call; nothing registers it automatically):
    claude mcp add arsenal-media -- py -m arsenal.media.door
"""
from __future__ import annotations

import asyncio
import importlib
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

#: Lists longer than this are cut in tool answers; the receipt keeps everything.
MAX_ROWS = 40
#: Keys whose values are bulky raw data; an answer names how many there were instead.
BULKY = {"data", "samples", "wavesurfer", "image", "pixels"}

mcp = FastMCP(
    "arsenal-media",
    instructions=(
        "The house video toolbox (arsenal.media). Use these tools instead of hand-rolled ffmpeg/ffprobe: probe a file "
        "(streams, audio track names, keyframe interval), import it into the media catalog, grab frames, build a "
        "labelled contact sheet or a filmstrip with waveform (one image instead of many), find scene cuts, trim to "
        "the exact frame keeping every audio track, measure loudness, demux or mix tracks, transcribe with word times, "
        "map League video time to game time from the HUD clock, pin Riot timeline events to frames, measure A/V sync, "
        "export with platform presets. Times are float seconds from the file's start. Originals are never modified. "
        "Every answer carries `blind` (what the tool cannot see) and a `receipt` path with the full result."),
)


def _lean(obj: Any, depth: int = 0) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in BULKY and isinstance(v, (list, str, bytes)) and len(v) > MAX_ROWS:
                out[k] = f"<{len(v)} items; see the receipt or the written file>"
            else:
                out[k] = _lean(v, depth + 1)
        return out
    if isinstance(obj, list):
        rows = [_lean(v, depth + 1) for v in obj[:MAX_ROWS]]
        if len(obj) > MAX_ROWS:
            rows.append(f"... {len(obj) - MAX_ROWS} more (of {len(obj)}); the receipt has them all")
        return rows
    if isinstance(obj, (bytes, bytearray)):
        return f"<{len(obj)} bytes>"
    if hasattr(obj, "tolist"):
        return f"<array {getattr(obj, 'shape', '')}>"
    return obj


def _call(module: str, fn: str, *args, **kwargs) -> Any:
    from .ff import MediaError
    try:
        res = getattr(importlib.import_module(f"arsenal.media.{module}"), fn)(*args, **kwargs)
    except MediaError as exc:
        return {"error": str(exc), "argv": getattr(exc, "argv", None)}
    except (ValueError, FileNotFoundError, KeyError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return json.loads(json.dumps(_lean(res), default=str))


async def _run(module: str, fn: str, *args, **kwargs) -> Any:
    return await asyncio.to_thread(_call, module, fn, *args, **kwargs)


# =================================================================================================
# facts and catalog
# =================================================================================================

@mcp.tool()
async def media_doctor() -> Any:
    """Where ffmpeg/ffprobe live, what the build can do (AMF encoders, whisper, libass, scdet), optional packages."""
    return await _run("ff", "doctor")


@mcp.tool()
async def media_probe(path: str, keyframes: bool = False) -> Any:
    """A file's facts: duration, codec, fps, every audio track with its name, keyframe interval, OBS encoder, recorded
    time, kind (league_replay / league_live / piano / screen). keyframes=True adds the full keyframe index."""
    return await _run("probe", "probe", path, keyframes=keyframes)


@mcp.tool()
async def media_import(path_or_dir: str, recursive: bool = False, quick: bool = True) -> Any:
    """Import files into the media catalog (never copied). quick=True: facts + catalog row + links only; quick=False
    also builds the analysis proxy, scene cuts, waveform peaks and the League clock map."""
    heavy = not quick
    return await _run("catalog", "ingest", path_or_dir, recursive=recursive, proxy=heavy, shots=heavy, peaks=heavy,
                      clock="auto" if heavy else "off")


@mcp.tool()
async def media_find(kind: Optional[str] = None, recorded_after: Optional[str] = None,
                     recorded_before: Optional[str] = None, n_audio: Optional[int] = None,
                     text: Optional[str] = None, limit: int = 20) -> Any:
    """Query the media catalog, newest recording first, e.g. kind="league_replay", recorded_after="2026-10-10".
    text matches a substring of the file name or path."""
    where = {k: v for k, v in {"kind": kind, "recorded_after": recorded_after, "recorded_before": recorded_before,
                               "n_audio": n_audio, "text": text, "limit": limit}.items() if v is not None}
    return await _run("catalog", "find", **where)


@mcp.tool()
async def media_resolve_drop(name: str, size: int, last_modified_ms: int = 0) -> Any:
    """The real path of a file dropped in the browser (name + size + lastModified), or null outside the library."""
    return await _run("catalog", "resolve_dropped", name, size, last_modified_ms)


# =================================================================================================
# pictures
# =================================================================================================

@mcp.tool()
async def media_grab(src: str, at: List[float], out_dir: Optional[str] = None, crop: Optional[List[float]] = None,
                     sheet: bool = True) -> Any:
    """Frames at exact times (one decode pass). crop = [x, y, w, h] in pixels or fractions <= 1. With sheet=True the
    frames also land on one labelled contact sheet: read that ONE image instead of many."""
    from .ff import state_dir
    from pathlib import Path
    out = out_dir or str(state_dir() / "grab" / Path(src).stem)
    res = await _run("frames", "save", src, at, out, crop=tuple(crop) if crop else None)
    if sheet and isinstance(res, dict) and res.get("frames"):
        files = [r["file"] for r in res["frames"] if isinstance(r, dict)]
        sh = await _run("sheet", "sheet", files, out=str(Path(out) / "sheet.png"))
        res["sheet"] = sh.get("png") if isinstance(sh, dict) else sh
    return res


@mcp.tool()
async def media_sheet(items: List[Any], cols: Optional[int] = None, title: Optional[str] = None,
                      out: Optional[str] = None) -> Any:
    """Many images or video moments on one labelled grid. items: image paths, [video, t] pairs, or
    {src, t, crop, label} objects. Kept under 1600 px so it costs one image read."""
    norm = [tuple(i) if isinstance(i, list) else i for i in items]
    return await _run("sheet", "sheet", norm, cols=cols, title=title, out=out)


@mcp.tool()
async def media_video_sheet(src: str, n: int = 30, start: float = 0.0, end: Optional[float] = None,
                            out: Optional[str] = None) -> Any:
    """A whole video (or a span) as n labelled frames on one sheet: the cheapest way to 'watch' it."""
    return await _run("sheet", "video_sheet", src, n=n, start=start, end=end, out=out)


@mcp.tool()
async def media_filmstrip(src: str, t0: float, t1: float, n: int = 8, track: int = 0,
                          out: Optional[str] = None) -> Any:
    """A row of frames over the waveform of the same seconds: ten seconds of video in one image."""
    return await _run("sheet", "filmstrip", src, t0, t1, n=n, track=track, out=out)


@mcp.tool()
async def media_shots(src: str, detector: str = "auto") -> Any:
    """Scene detection: the cuts in a video (PySceneDetect or ffmpeg's scene score on a 360p proxy; League clock jumps
    when a clock map exists)."""
    return await _run("shots", "shots", src, detector=detector)


# =================================================================================================
# cutting and audio
# =================================================================================================

@mcp.tool()
async def media_cut_plan(src: str, start: float, end: float) -> Any:
    """What a trim of [start, end) costs: lossless copy (start on a keyframe) or how many seconds a smart cut
    re-encodes."""
    return await _run("cut", "plan", src, start, end)


@mcp.tool()
async def media_cut(src: str, start: float, end: float, out: Optional[str] = None, mode: str = "smart") -> Any:
    """Trim to the exact frame. mode: copy (lossless, snaps to the keyframe before), smart (re-encodes only up to the
    next keyframe, copies the rest), exact (re-encodes all). Every audio track and its name come along; verified."""
    return await _run("cut", "cut", src, start, end, out, mode=mode)


@mcp.tool()
async def media_audio(src: str, loudness: bool = True) -> Any:
    """Audio tracks with their names; with loudness=True each track's integrated LUFS, LRA and true peak (one pass)."""
    tracks = await _run("audio", "tracks", src)
    if not loudness:
        return {"tracks": tracks}
    return {"tracks": tracks, "loudness": await _run("audio", "loudness", src)}


@mcp.tool()
async def media_mix(src: str, out: str, gains_db: Optional[Dict[str, float]] = None,
                    mute: Optional[List[int]] = None, loudnorm: Optional[float] = None) -> Any:
    """Mix a file's audio tracks with per-track gain (dB, keyed by track index) and mutes; optional loudnorm target."""
    gains = {int(k): float(v) for k, v in (gains_db or {}).items()}
    return await _run("audio", "mix", src, out, gains_db=gains, mute=tuple(mute or ()), loudnorm=loudnorm)


@mcp.tool()
async def media_qc(path: str) -> Any:
    """Check a finished file: loudness, true peak, black/freeze/silence runs, stream inventory, duration."""
    return await _run("audio", "qc", path)


@mcp.tool()
async def media_words(src: str, track: Optional[int] = None, start: Optional[float] = None,
                      end: Optional[float] = None, model: str = "small") -> Any:
    """Speech to text with word times (faster-whisper, VAD on: no hallucinated repeats over game audio). Writes
    words.json and a cadence transcript; answers with their paths and counts."""
    span = (start, end) if start is not None and end is not None else None
    return await _run("words", "words", src, track=track, span=span, model=model)


# =================================================================================================
# League
# =================================================================================================

@mcp.tool()
async def media_clockmap(src: str, hud: str = "auto") -> Any:
    """League HUD clock read on the keyframes: a map from video time to game time, with replay rewinds and 0.25x/0.5x
    passes as separate passes."""
    return await _run("league.clock", "clockmap", src, hud=hud)


@mcp.tool()
async def media_events(src: str, match_id: str, player: Optional[str] = None) -> Any:
    """Riot match-v5 timeline events (kills, items, objectives) pinned to every video time that shows them, grouped
    into fight windows. Uses the cached match only; no Riot API call."""
    return await _run("league.events", "pin", src, match_id, player=player)


@mcp.tool()
async def media_replay_plan(plan_path: str, plan_id: str) -> Any:
    """Dry-run of one League Replay API take: every request the driver would send, and how long OBS would record. It
    sends nothing (Daniel drives live takes with `py -m arsenal.media replay take`)."""
    def plan() -> Any:
        from .league import replay_api as ra
        rows = {str(r.get("plan_id")): r for r in ra.load_plan(plan_path)}
        if plan_id not in rows:
            return {"error": f"no take {plan_id!r} (have: {', '.join(rows)})"}
        api = ra.ReplayApi(dry_run=True)
        take = ra.plan_take(rows[plan_id])
        res = ra.run_take(api, take, confirm=lambda msg: None)
        return {"take": {k: v for k, v in take.items() if k != "steps"}, "requests": res["log"],
                "roll_s": res["waited_s"]}
    return await asyncio.to_thread(plan)


@mcp.tool()
async def media_avsync(a: str, b: Optional[str] = None, a_track: int = 0, b_track: Optional[int] = None) -> Any:
    """Offset (ms) and drift (ms/min) between two recordings of the same moment, or between two tracks of one file."""
    return await _run("avsync", "offset", a, b, a_track=a_track, b_track=b_track)


@mcp.tool()
async def media_export(src: str, preset: str, out: str, start: Optional[float] = None,
                       end: Optional[float] = None, dry_run: bool = False) -> Any:
    """Export with a platform preset (youtube_4k60, youtube_4k60_fast, shorts_1080x1920, proxy_edit, alpha_webm,
    alpha_webp_anim, ...) plus a loudness/duration QC receipt. dry_run=True returns the ffmpeg argv only."""
    return await _run("export", "export", src, preset, out, start=start, end=end, dry_run=dry_run)


# =================================================================================================
# the editor's projects (the same files the web page edits)
# =================================================================================================

@mcp.tool()
async def media_edit_projects() -> Any:
    """The video editor's projects (the ones Daniel edits in First Light's Edit mode), newest first: id, name, rev,
    clip count."""
    return await _run("edit", "list_projects")


@mcp.tool()
async def media_edit_show(pid: str) -> Any:
    """One project document: lanes, clips (media, src_in/src_out, timeline position, per-track gains), markers, rev."""
    return await _run("edit", "load", pid)


@mcp.tool()
async def media_edit_apply(pid: str, op: str, args: Dict[str, Any], rev: int) -> Any:
    """Change a project as the web page does, one writer at a time. rev must be the revision you read: if Daniel saved
    in between, this is refused with the current document. ops: add_clip {media_id, src_in?, src_out?, at?},
    move {clip_id, at}, trim {clip_id, src_in?, src_out?}, split {clip_id, t}, remove {clip_id},
    set_lane_gain {lane, gain_db?, mute?, solo?}, set_clip_track_gain {clip_id, src_track, gain_db?, mute?}."""
    def apply() -> Any:
        from . import edit
        doc = edit.load(pid)
        if doc.get("rev") != rev:
            return {"error": f"stale revision {rev}: the project is at rev {doc.get('rev')}; read it again",
                    "project": doc}
        a = dict(args)
        if op == "add_clip":
            media = edit.get_media(a.pop("media_id"))
            doc, _clip = edit.add_clip(doc, media, **a)
        elif op == "split":
            doc, _right = edit.split(doc, a.pop("clip_id"), a.pop("t"))
        elif op in ("move", "trim", "remove", "set_clip_track_gain"):
            cid = a.pop("clip_id")
            if op == "move":
                doc = edit.move(doc, cid, a.pop("at"))
            elif op == "set_clip_track_gain":
                doc = edit.set_clip_track_gain(doc, cid, int(a.pop("src_track")), **a)
            else:
                doc = getattr(edit, op)(doc, cid, **a)
        elif op == "set_lane_gain":
            doc = edit.set_lane_gain(doc, a.pop("lane"), **a)
        else:
            return {"error": f"unknown op {op!r}"}
        return edit.save(doc)
    try:
        return json.loads(json.dumps(_lean(await asyncio.to_thread(apply)), default=str))
    except Exception as exc:          # EditError / Conflict carry their own words; the page shows the same ones
        current = getattr(exc, "current", None)
        return {"error": f"{type(exc).__name__}: {exc}", **({"project": current} if current else {})}


@mcp.tool()
async def media_edit_render(pid: str, preset: str = "youtube_4k60_fast") -> Any:
    """Render a project to a new file under E:\\Video Output E\\aurora-edits\\<project>\\ with a QC line. Blocking: a
    long timeline takes a while (about 6x realtime at the proxy preset)."""
    def render() -> Any:
        from . import edit
        return edit.render(edit.load(pid), preset)
    return json.loads(json.dumps(_lean(await asyncio.to_thread(render)), default=str))


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media.door", description="the video toolbox as MCP tools")
    ap.add_argument("--http", type=int, default=None, metavar="PORT", help="serve streamable HTTP instead of stdio")
    a = ap.parse_args(argv)
    if a.http:
        mcp.settings.port = a.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
