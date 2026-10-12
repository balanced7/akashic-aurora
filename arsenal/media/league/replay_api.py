"""arsenal.media.league.replay_api -- drive League's Replay API for clean re-shoots, and the capture run-sheet.

Why: a replay only plays on the patch that recorded it. The Draven/Yuumi game (NA1_5658447097, 16.20) goes dark when
patch 26.21 ships on 2026-10-21, and the board needs ten clean 4K takes from it. This module plans and drives each
take; OBS records it in real time; a human (Daniel) presses record. It never launches League.

What the API is (developer.riotgames.com /replay-apis; League Director's api.py; wooto/lol-replay-recorder, validated on
16.20.824.8524 on 2026-10-09):
- game.cfg [General] EnableReplayApi=1 turns it on (done 2026-10-11). It answers on https://127.0.0.1:2999 only while
  a replay is open in the client, with Riot's self-signed certificate. This client talks to loopback only and refuses
  any other host, which is the one place it accepts an unverified certificate.
- /replay/playback {time (game seconds), speed, paused, seeking, length}; /replay/render {cameraMode, selectionName,
  cameraAttached, fieldOfView, interfaceAll, interface*, fogOfWar, ...}; /replay/sequence (keyframed tracks; POST {}
  clears); /replay/recording (the API's own recorder: it desyncs A/V, Riot issue #881, so OBS records instead);
  /swagger/v3/openapi.json and /swagger/v2/swagger.json describe the installed build.
- There is no camera-lock field (ahriuwu issue #9): "follow" is cameraMode "fps" + selectionName. If the camera drifts,
  double-tap the champion's key in the replay.
- Speed changes are baked into a real-time recording: 3 s of game at 0.25x is 12 s of video, every frame rendered.

UNPROVEN until Daniel opens the replay: the follow fields (selectionName / cameraAttached), and the push-in by a
fieldOfView sequence. `take --dry-run` prints every request without sending one; `status` and `swagger` are the first
live checks, and their output decides what the next build trusts.
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..ff import MediaError, state_dir

DEFAULT_BASE = "https://127.0.0.1:2999"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
NOT_ANSWERING = ("the Replay API is not answering on {base}: open the replay in the League client (the API exists only "
                 "while a replay plays) and check game.cfg [General] EnableReplayApi=1")

HUD = {"off": {"interfaceAll": False}, "on": {"interfaceAll": True}}
#: How each board camera word maps onto the API. "how" says what is proven and what is a guess.
CAMERAS = {
    "follow": {"render": {"cameraMode": "fps", "cameraAttached": True}, "target": True,
               "how": "fps mode + selectionName (wooto recorder); unproven on this client until the first live take"},
    "locked": {"render": {"cameraMode": "fps", "cameraAttached": True}, "target": True,
               "how": "follow with no camera move; double-tap the champion key if it drifts"},
    "push_in": {"render": {"cameraMode": "fps", "cameraAttached": True}, "target": True,
                "fov": (40.0, 26.0),
                "how": "follow + a fieldOfView sequence 40 -> 26 deg (smoothStep): a zoom, no world coordinates needed"},
    "top": {"render": {"cameraMode": "top"}, "target": False,
            "how": "top mode; cameraPosition is ignored in top (Riot issue #877), so framing is the default"},
    "orbit": {"render": {"cameraMode": "fps", "cameraAttached": True}, "target": True,
              "how": "NOT automated: follow, and orbit by hand (or do the move in post)"},
    "stills": {"render": {"cameraMode": "fps", "cameraAttached": True}, "target": True,
               "how": "paused frames; take each still with OBS's screenshot hotkey"},
}


class ReplayApiError(MediaError):
    """The Replay API refused, was not there, or was asked something this client will not send."""


def parse_game_time(s) -> float:
    """'26:27.20' / '1:02:03' / 95.5 -> game seconds."""
    if isinstance(s, (int, float)):
        return float(s)
    total = 0.0
    for part in str(s).strip().split(":"):
        total = total * 60 + float(part)
    return total


def mmss(t: float) -> str:
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:05.2f}"


# =================================================================================================
# client
# =================================================================================================

class ReplayApi:
    """A loopback-only client. Every request is appended to .log (method, path, body) whether or not it is sent; with
    dry_run=True nothing is sent and reads return None."""

    def __init__(self, base: str = DEFAULT_BASE, *, dry_run: bool = False, timeout: float = 5.0,
                 opener: Optional[Callable] = None):
        parts = urllib.parse.urlsplit(base)
        if parts.hostname not in LOOPBACK:
            raise ReplayApiError(f"refusing {base}: the Replay API lives on this machine only (127.0.0.1)")
        self.base = base.rstrip("/")
        self.dry_run = dry_run
        self.timeout = timeout
        self.log: List[dict] = []
        self._opener = opener
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False          # Riot's self-signed certificate, on loopback only (checked above)
        self._ctx.verify_mode = ssl.CERT_NONE

    def call(self, method: str, path: str, body: Optional[dict] = None):
        self.log.append({"method": method, "path": path, "body": body})
        if self.dry_run:
            return None
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            if self._opener:
                raw = self._opener(req, self.timeout)
            else:
                with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                    raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode("utf-8", errors="replace")
            raise ReplayApiError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            raise ReplayApiError(NOT_ANSWERING.format(base=self.base) + f" ({exc})") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            return {"raw": raw[:2000].decode("utf-8", errors="replace")}

    def game(self):
        return self.call("GET", "/replay/game")

    def playback(self):
        return self.call("GET", "/replay/playback")

    def render(self):
        return self.call("GET", "/replay/render")

    def set_playback(self, **fields):
        return self.call("POST", "/replay/playback", fields)

    def set_render(self, **fields):
        return self.call("POST", "/replay/render", fields)

    def sequence(self, seq: Optional[dict] = None):
        """POST a keyframed sequence; None clears it (the API takes {} as "remove")."""
        return self.call("POST", "/replay/sequence", seq or {})

    def status(self) -> dict:
        """What a first live check needs: is a replay open, where is the playhead, which camera and HUD are on."""
        game, pb, rd = self.game(), self.playback(), self.render()
        keep = ("cameraMode", "selectionName", "cameraAttached", "fieldOfView", "interfaceAll", "fogOfWar")
        return {"game": game, "playback": pb,
                "render": {k: (rd or {}).get(k) for k in keep} if rd is not None else None}

    def swagger(self, out_dir) -> Dict[str, str]:
        """Save the installed build's own API description (v3 and v2), the ground truth for the next build."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        saved = {}
        for name, path in (("openapi-v3.json", "/swagger/v3/openapi.json"), ("swagger-v2.json", "/swagger/v2/swagger.json")):
            doc = self.call("GET", path)
            if doc is None:
                continue
            target = out / name
            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1)
            saved[name] = str(target)
        return saved


# =================================================================================================
# takes
# =================================================================================================

def plan_take(row: dict, *, preroll_s: float = 8.0, postroll_s: float = 4.0, slate_s: float = 1.0) -> dict:
    """One capture-plan row (draven-penta.capture.json "plan" shape) -> the ordered steps of a take.

    The take opens with a HUD-on slate: the game clock is on screen for the first slate_s of the pre-roll, so the
    clock reader (league.clock) can map the take's file time to game time with no human note. Then the HUD goes off
    for the clean look, the replay rolls from game_in - preroll to game_out + postroll at the plan's speed."""
    cam_word = str(row.get("camera") or "follow")
    if cam_word not in CAMERAS:
        raise ReplayApiError(f"{row.get('plan_id')}: unknown camera {cam_word!r} (known: {', '.join(CAMERAS)})")
    cam = CAMERAS[cam_word]
    g_in, g_out = parse_game_time(row["game_in"]), parse_game_time(row["game_out"])
    if g_out <= g_in and cam_word != "stills":
        raise ReplayApiError(f"{row.get('plan_id')}: game_out {row['game_out']} is not after game_in {row['game_in']}")
    speed = float(row.get("replay_speed") or 1.0)
    start = max(0.0, g_in - preroll_s)
    render = dict(cam["render"])
    if cam["target"] and row.get("target"):
        render["selectionName"] = row["target"]
    hud_clean = "off" if "clean" in str(row.get("look", "clean")) else "on"
    steps: List[dict] = [
        {"api": "set_playback", "args": {"paused": True, "time": round(start, 3)}},
        {"api": "sequence", "args": None},
        {"api": "set_render", "args": dict(render, **HUD["on"])},
    ]
    if cam_word == "stills":
        steps += [{"api": "set_playback", "args": {"paused": True, "time": round(g_in, 3)}},
                  {"api": "set_render", "args": HUD[hud_clean]},
                  {"human": "take the stills with OBS's screenshot hotkey: low wide, over-the-shoulder, top"}]
        return {"plan_id": row.get("plan_id"), "camera": cam_word, "how": cam["how"], "steps": steps,
                "record_s": 0.0, "game_in": g_in, "game_out": g_out, "start": g_in, "speed": 0.0}
    if "fov" in cam:
        f0, f1 = cam["fov"]
        steps.append({"api": "sequence", "args": {"fieldOfView": [
            {"time": round(g_in, 3), "value": f0, "blend": "smoothStep"},
            {"time": round(g_out, 3), "value": f1, "blend": "smoothStep"}]}})
    steps += [
        {"api": "set_playback", "args": {"speed": speed}},
        {"human": f"start the OBS recording (scene 'Replay clean'); rename the file afterwards to {take_name(row)}"},
        {"api": "set_playback", "args": {"paused": False}},
        {"wait_game": slate_s, "note": "slate: the HUD clock is on screen"},
        {"api": "set_render", "args": HUD[hud_clean]},
        {"wait_until_game": round(g_out + postroll_s, 3)},
        {"api": "set_playback", "args": {"paused": True}},
        {"human": "stop the OBS recording"},
    ]
    record_s = (g_out + postroll_s - start) / speed
    return {"plan_id": row.get("plan_id"), "camera": cam_word, "how": cam["how"], "steps": steps,
            "record_s": round(record_s, 1), "game_in": g_in, "game_out": g_out, "start": start, "speed": speed}


def take_name(row: dict) -> str:
    """The file name a take is renamed to: <plan_id>_<first shot>."""
    shot = row.get("shot") or next(iter(row.get("shots") or []), None) or "take"
    return f"{row.get('plan_id')}_{shot}"


def run_take(api: ReplayApi, take: dict, *, confirm: Callable[[str], None] = print,
             sleep: Callable[[float], None] = time.sleep, poll_s: float = 0.1) -> dict:
    """Execute a planned take. Human steps go through confirm() (the CLI waits for Enter). In dry-run the waits are
    computed from the game position, not slept. Returns {log, waited_s}."""
    waited = 0.0
    pos = take["start"]                         # game seconds where the playhead sits
    speed = max(take["speed"], 1e-6)
    for step in take["steps"]:
        if "api" in step:
            fn = getattr(api, step["api"])
            fn(**step["args"]) if isinstance(step["args"], dict) and step["api"] != "sequence" else fn(step["args"])
        elif "human" in step:
            confirm(step["human"])
        elif "wait_game" in step:
            secs = step["wait_game"] / speed
            waited += secs
            pos += step["wait_game"]
            if not api.dry_run:
                sleep(secs)
        elif "wait_until_game" in step:
            target = step["wait_until_game"]
            if api.dry_run:
                waited += max(0.0, target - pos) / speed
                pos = target
                continue
            deadline = time.monotonic() + 3600
            while time.monotonic() < deadline:
                pb = api.playback() or {}
                if float(pb.get("time", 0.0)) >= target or pb.get("paused"):
                    break
                sleep(poll_s)
                waited += poll_s
    return {"log": list(api.log), "waited_s": round(waited, 1)}


# =================================================================================================
# the run-sheet
# =================================================================================================

def load_plan(path) -> List[dict]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = doc.get("plan") if isinstance(doc, dict) else doc
    if not isinstance(rows, list) or not rows:
        raise ReplayApiError(f"{path}: no capture plan rows (expected a 'plan' list)")
    return rows


def run_sheet(rows: List[dict], *, deadline: str = "2026-10-21", match: str = "", today: Optional[date] = None,
              preroll_s: float = 8.0, postroll_s: float = 4.0, insurance: Optional[List[dict]] = None) -> str:
    """The manual capture run-sheet as Markdown: takes in game order (the replay only moves forward between them),
    each with its camera, speed, how long OBS records, the file name, and what is still a guess."""
    takes = sorted((plan_take(r, preroll_s=preroll_s, postroll_s=postroll_s) | {"row": r} for r in rows),
                   key=lambda t: t["game_in"])
    today = today or date.today()
    days = (date.fromisoformat(deadline) - today).days
    total = sum(t["record_s"] for t in takes)
    out = [f"# Capture run-sheet{(' -- ' + match) if match else ''}", "",
           f"**{days} day(s) left**: the replay stops playing on {deadline} (patch day). "
           f"{len(takes)} takes, about {total / 60:.0f} min of recording plus setup.", "",
           "## Before the first take", "",
           "1. OBS: Advanced output, 6 audio tracks, keyframe interval 1 s, scene **Replay clean** "
           "(Game Capture of the League window).",
           "2. Open the replay in the League client and let it load.",
           "3. Run `py -m arsenal.media replay status`. It must print the game and the playhead. "
           "Then `py -m arsenal.media replay swagger` once (it saves this build's API description).",
           "4. Each take: `py -m arsenal.media replay take <ID> --plan <plan.json>`. It seeks, sets the camera and the "
           "HUD, waits for you to press record, rolls, and pauses at the end. Add `--dry-run` to see the requests only.",
           "", "## Takes (in game order)", "",
           "| # | ID | Shots | Game time | Camera | Target | Speed | Records | Rename the file to | What |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for i, t in enumerate(takes, 1):
        r = t["row"]
        span = mmss(t["game_in"]) if t["camera"] == "stills" else f"{mmss(t['game_in'])}-{mmss(t['game_out'])}"
        rec = "stills" if t["camera"] == "stills" else f"{t['record_s']:.0f} s"
        speed = "paused" if t["camera"] == "stills" else f"{t['speed']:g}x"
        shots = " ".join(r.get("shots") or [r.get("shot", "")])
        what = str(r.get("what", "")).replace("|", "/")
        out.append(f"| {i} | {t['plan_id']} | {shots} | {span} | {t['camera']} | {r.get('target', '')} | {speed} | "
                   f"{rec} | `{take_name(r)}` | {what} |")
    if insurance:
        ins_total = sum(parse_game_time(x["range"][1]) - parse_game_time(x["range"][0]) for x in insurance)
        out += ["", "## Insurance: the whole game, recorded by hand (if there is time)", "",
                f"These can never be redone after {deadline}. About {ins_total / 60:.0f} min at 1x; press record, "
                f"play from 0:00, stop at the end.", "",
                "| ID | Range | Camera | HUD | Speed |", "|---|---|---|---|---|"]
        for x in insurance:
            out.append(f"| {x.get('id')} | {x['range'][0]}-{x['range'][1]} | {x.get('camera', '')} | "
                       f"{x.get('hud', '')} | {x.get('speed', 1.0)}x |")
    guesses = sorted({f"- **{t['camera']}**: {t['how']}" for t in takes})
    out += ["", "## Still guesses until the first live take", "", *guesses, "",
            "If a camera word misbehaves, record the take with the camera by hand: the clock slate at the start of every "
            "take still lets the clock reader place it, so nothing is lost but the move.", ""]
    return "\n".join(out)


# =================================================================================================
# CLI: py -m arsenal.media replay status|swagger|take|sheet
# =================================================================================================

def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media replay",
                                 description="League Replay API (127.0.0.1:2999): status, swagger, take, run-sheet")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="is a replay open: game, playhead, camera, HUD")
    sw = sub.add_parser("swagger", help="save the installed build's API description (v3 + v2)")
    sw.add_argument("--out", default=None)
    tk = sub.add_parser("take", help="drive one planned take; OBS records")
    tk.add_argument("plan_id")
    tk.add_argument("--plan", required=True, help="capture plan JSON (a 'plan' list of rows)")
    tk.add_argument("--dry-run", action="store_true", help="print every request; send nothing")
    sh = sub.add_parser("sheet", help="write the capture run-sheet (Markdown) for a plan")
    sh.add_argument("--plan", required=True)
    sh.add_argument("--out", default=None)
    sh.add_argument("--deadline", default="2026-10-21")
    sh.add_argument("--match", default="")
    sh.add_argument("--insurance", default=None, help="shot-list JSON with an insurance_full_game list")
    for p in (sub.choices["status"], sw, tk):
        p.add_argument("--base", default=DEFAULT_BASE)
    a = ap.parse_args(argv)
    if a.cmd == "sheet":
        ins = None
        if a.insurance:
            ins = json.loads(Path(a.insurance).read_text(encoding="utf-8")).get("insurance_full_game")
        text = run_sheet(load_plan(a.plan), deadline=a.deadline, match=a.match, insurance=ins)
        out = Path(a.out) if a.out else state_dir() / "league" / "run-sheet.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"run-sheet -> {out}")
        return 0
    api = ReplayApi(a.base, dry_run=getattr(a, "dry_run", False))
    if a.cmd == "status":
        print(json.dumps(api.status(), indent=2))
        return 0
    if a.cmd == "swagger":
        out = Path(a.out) if a.out else state_dir() / "league" / "swagger"
        print(json.dumps(api.swagger(out), indent=2))
        return 0
    rows = {str(r.get("plan_id")): r for r in load_plan(a.plan)}
    if a.plan_id not in rows:
        raise ReplayApiError(f"no take {a.plan_id!r} in {a.plan} (have: {', '.join(rows)})")
    take = plan_take(rows[a.plan_id])
    print(f"{take['plan_id']}: camera {take['camera']} ({take['how']}); records about {take['record_s']:.0f} s")
    confirm = print if api.dry_run else (lambda msg: input(f"-> {msg}; press Enter when done "))
    res = run_take(api, take, confirm=confirm)
    if api.dry_run:
        for entry in res["log"]:
            print(f"  {entry['method']:4s} {entry['path']}  {json.dumps(entry['body']) if entry['body'] is not None else ''}")
        print(f"  (would roll about {res['waited_s']:.0f} s)")
    return 0
