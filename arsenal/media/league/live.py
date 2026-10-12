"""arsenal.media.league.live -- the game's own clock beside an OBS recording: an exact clockmap for live games, no OCR.

Why it exists: OCR can only read what the HUD shows, once a second. While a game is running, Riot's Live Client Data
API (https://127.0.0.1:2999/liveclientdata, official, loopback only, up only during a game) answers gameTime to the
millisecond plus every ChampionKill / DragonKill / ... with its EventTime. poll() logs (wall clock, gameTime) every
half second and each new event as JSON lines; clockmap() turns a log into studio.clockmap.v1 for the recording made
at the same time. Promoted from the studio's live_event_sidecar.py.

The one weak joint is where the recording starts on the wall clock. OBS names files by start time to the second
("%CCYY-%MM-%DD %hh-%mm-%ss"), so the file name alone leaves up to 1 s; the file's creation time (when OBS opened it,
sub-second on NTFS) is used when it sits inside that second, and calibrate=True pins the offset with one HUD clock
tick (league.clock) when a clock reader is available. Nothing in OBS or the game is changed.
"""
from __future__ import annotations

import json
import os
import ssl
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .. import ff, receipt

BASE = "https://127.0.0.1:2999/liveclientdata"
GAME_DIR_ENV = "LEAGUE_GAME_DIR"
DEFAULT_GAME_DIR = Path("C:/Riot Games/League of Legends/Game")   # Riot's default install location
OBS_NAME_FORMAT = "%Y-%m-%d %H-%M-%S"


def _ssl_context() -> ssl.SSLContext:
    """Riot's self-signed certificate on 127.0.0.1: verified against riotgames.pem when it is installed, else not
    verified (the URL is pinned to loopback and nothing secret is sent)."""
    pem = Path(os.environ.get(GAME_DIR_ENV) or DEFAULT_GAME_DIR) / "riotgames.pem"
    if pem.is_file():
        ctx = ssl.create_default_context(cafile=str(pem))
        ctx.check_hostname = False
        return ctx
    return ssl._create_unverified_context()  # noqa: S323 (loopback only)


def _http_get(path: str, ctx: ssl.SSLContext) -> dict:
    with urllib.request.urlopen(f"{BASE}/{path}", context=ctx, timeout=2) as r:
        return json.loads(r.read().decode("utf-8"))


def label(ev: dict) -> str:
    """A one-line marker for a Live Client Data event."""
    n = ev.get("EventName", "?")
    if n == "ChampionKill":
        a = ", ".join(ev.get("Assisters", []))
        return f"Kill {ev.get('KillerName')} > {ev.get('VictimName')}" + (f" (+{a})" if a else "")
    if n == "Multikill":
        return f"Multikill x{ev.get('KillStreak')} {ev.get('KillerName')}"
    if n in ("DragonKill", "BaronKill", "HeraldKill", "HordeKill", "AtakhanKill"):
        return " ".join(x for x in (n, ev.get("DragonType", ""), "by", str(ev.get("KillerName"))) if x)
    if n in ("TurretKilled", "InhibKilled"):
        return f"{n} {ev.get('TurretKilled') or ev.get('InhibKilled')}"
    return n


def poll(out=None, interval: float = 0.5, *, stop_after: Optional[int] = None,
         get: Optional[Callable[[str], dict]] = None, idle_sleep: float = 3.0) -> Optional[str]:
    """Log gameTime every `interval` s and each new event, one JSON line each, until Ctrl+C (or `stop_after` polls).
    Waits quietly while no game runs; a new game opens a new file. Returns the last log path."""
    ctx = None if get else _ssl_context()
    fetch = get or (lambda path: _http_get(path, ctx))
    folder = Path(out) if out else ff.state_dir() / "league" / "live"
    folder.mkdir(parents=True, exist_ok=True)
    fh, path, seen, n = None, None, -1, 0
    try:
        while stop_after is None or n < stop_after:
            n += 1
            try:
                stats = fetch("gamestats")
                evs = fetch("eventdata").get("Events", [])
            except Exception:                              # no game (connection refused) or the game just ended
                if fh:
                    fh.close()
                    fh, seen = None, -1
                time.sleep(idle_sleep if stop_after is None else 0)
                continue
            wall = time.time()
            if fh is None:
                path = folder / f"{datetime.now().strftime(OBS_NAME_FORMAT)} league.jsonl"
                fh = open(path, "a", encoding="utf-8", newline="\n")
            fh.write(json.dumps({"wall": wall, "gameTime": stats.get("gameTime")}) + "\n")
            for ev in evs:
                if ev.get("EventID", -1) > seen:
                    seen = ev["EventID"]
                    fh.write(json.dumps({"wall": wall, "gameTime": stats.get("gameTime"), "event": ev}) + "\n")
            fh.flush()
            if stop_after is None or n < stop_after:
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        if fh:
            fh.close()
    return str(path) if path else None


def read_log(poll_log) -> Tuple[List[Tuple[float, float]], List[dict]]:
    """((wall, gameTime) pairs, events) from a poll log; tolerates a torn last line."""
    pairs, events = [], []
    for line in Path(poll_log).read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("gameTime") is None:
            continue
        if "event" in d:
            events.append(d)
        else:
            pairs.append((float(d["wall"]), float(d["gameTime"])))
    return pairs, events


def recording_start(recording) -> Tuple[float, str, float]:
    """(wall-clock start of the recording, how it was found, its uncertainty in s)."""
    p = Path(recording)
    try:
        named = datetime.strptime(p.stem[:19], OBS_NAME_FORMAT).timestamp()
    except ValueError:
        raise ff.MediaError(f"{p.name} does not start with an OBS time stamp ({OBS_NAME_FORMAT}); pass file_start")
    try:
        created = os.stat(p).st_ctime if os.name == "nt" else None
    except OSError:
        created = None
    if created is not None and named <= created < named + 1.0:
        return created, "file creation time (inside the name's second)", 0.25
    return named + 0.5, "OBS file name (second only)", 0.5


def _segments(pairs: List[Tuple[float, float]], start: float, jump_s: float = 0.25) -> List[List[Tuple[float, float]]]:
    """(file_t, game_t) runs where the game clock advanced with the wall clock (a pause or reconnect breaks one)."""
    pts = sorted((w - start, g) for w, g in pairs)
    runs: List[List[Tuple[float, float]]] = []
    for ft, gt in pts:
        if runs and abs((gt - runs[-1][-1][1]) - (ft - runs[-1][-1][0])) <= jump_s:
            runs[-1].append((ft, gt))
        else:
            runs.append([(ft, gt)])
    return runs


def clockmap(poll_log, recording, *, file_start: Optional[float] = None, offset_s: float = 0.0,
             calibrate: bool = False, out=None) -> dict:
    """studio.clockmap.v1 for `recording` from a poll log: one 1x pass per stretch where gameTime ran with the wall
    clock, plus the logged events as markers (file_t, game_t, label)."""
    from . import clock
    pairs, evs = read_log(poll_log)
    if not pairs:
        raise ff.MediaError(f"{poll_log} holds no gameTime samples")
    if file_start is None:
        start, how, unc = recording_start(recording)
    else:
        start, how, unc = float(file_start), "given", 0.0
    start -= offset_s
    passes = []
    for run in _segments(pairs, start):
        if len(run) < 2:
            continue
        off = statistics.median(g - f for f, g in run)
        resid = max(abs(g - f - off) for f, g in run)
        passes.append({"id": "", "file": [round(run[0][0], 4), round(run[-1][0], 4)], "speed": 1.0,
                       "offset": round(off, 4), "tol_s": round(unc + resid, 4),
                       "game": [round(run[0][1], 3), round(run[-1][1], 3)], "fit": "poll", "n_reads": len(run)})
    calibrated = None
    if calibrate and passes and Path(recording).is_file():
        p = max(passes, key=lambda q: q["file"][1] - q["file"][0])
        tick = clock.tick_offset(recording, "live", (p["file"][0] + p["file"][1]) / 2)
        if tick is not None:
            shift = tick - p["offset"]
            for q in passes:
                q["file"] = [round(q["file"][0] - shift, 4), round(q["file"][1] - shift, 4)]
                q["offset"] = round(q["offset"] + shift, 4)
                q["tol_s"] = round(1.0 / 60 + max(0.0, q["tol_s"] - unc), 4)
                q["fit"] = "poll + clock tick"
            calibrated = {"shift_s": round(shift, 4), "tick_offset": tick}
    used: set = set()
    for q in passes:
        q["id"] = clock._pass_id(q["game"][0], 1.0, used)
    markers = []
    for d in evs:
        ev = d["event"]
        gt = float(ev.get("EventTime", d["gameTime"]))
        ft = None
        for q in passes:
            cand = gt - q["offset"]
            if q["file"][0] - 1.0 <= cand <= q["file"][1] + 1.0:
                ft = round(cand, 3)
                break
        markers.append({"game_t": round(gt, 3), "file_t": ft, "label": label(ev), "event": ev.get("EventName")})
    rec = Path(recording)
    params = {"poll_log": str(poll_log), "file_start": file_start, "offset_s": offset_s, "calibrate": calibrate,
              "out": str(out) if out else None}
    payload = {"schema": clock.SCHEMA, "file": rec.resolve().as_posix(), "what": "live game: Live Client Data gameTime "
               "logged beside the recording", "how_built": f"poll log {Path(poll_log).name}; file start from {how}",
               "hud": "live", "reader": "live-client-data", "passes": passes, "events": [], "markers": markers,
               "start": {"wall": start, "from": how, "uncertainty_s": unc}, "calibrated": calibrated}
    blind = ["where the recording starts on the wall clock is known to the file's creation time or the name's second "
             "unless calibrate=True pins it with a HUD clock tick",
             "Live Client Data exists only in live games; replays and spectating need the OCR clockmap"]
    src = receipt.source(rec) if rec.is_file() else {"path": str(rec)}
    res = receipt.result("clockmap", src, params, payload, blind, engine={"reader": "live-client-data"})
    if out:
        clock.save(res, out)
    return res


def cli(verb: str, argv: List[str]) -> int:
    """py -m arsenal.media.league.live poll [--out DIR] | clockmap LOG RECORDING [--out F] [--calibrate]"""
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media.league.live",
                                 description="League Live Client Data beside an OBS recording: log gameTime and kill "
                                             "events while you play, then an exact clockmap (no OCR)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("poll", help="log gameTime every --interval s and each new event until Ctrl+C")
    p.add_argument("--out", help="folder for the .jsonl logs (default <state>/league/live)")
    p.add_argument("--interval", type=float, default=0.5)
    c = sub.add_parser("clockmap", help="studio.clockmap.v1 for a recording from a poll log")
    c.add_argument("log")
    c.add_argument("recording")
    c.add_argument("--file-start", type=float, help="wall-clock start of the recording (epoch s)")
    c.add_argument("--offset", type=float, default=0.0, help="seconds to move the recording start earlier")
    c.add_argument("--calibrate", action="store_true", help="pin the offset with one HUD clock tick")
    c.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "poll":
        print(f"waiting for a game; logs go to {a.out or ff.state_dir() / 'league' / 'live'} (Ctrl+C stops)")
        print(f"last log: {poll(a.out, a.interval)}")
        return 0
    res = clockmap(a.log, a.recording, file_start=a.file_start, offset_s=a.offset, calibrate=a.calibrate,
                   out=a.out)
    for q in res["passes"]:
        print(f"  {q['id']:<12} file {q['file'][0]:.3f}-{q['file'][1]:.3f}  offset {q['offset']:+.4f} "
              f"+-{q['tol_s']:.3f} ({q['fit']})")
    print(f"{len(res['markers'])} markers; start from {res['start']['from']}; receipt {res.get('receipt')}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(cli("live", sys.argv[1:]))
