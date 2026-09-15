"""Runs and the jam routes: every Play, Loop and Try is a run the server records (jam-spec 4.3, 5, 6, 9).

The page keeps time; the server is the record. A run holds its def versions, tempo segments and settings; every
change lands on a line (bar, beat or pass) at least 1 beat + 250 ms after the server received it (C3, 9.4), and is one
line in runs/<run>/events.jsonl plus one `jam` frame on the cue stream.

  RunStore(root, now_ms)       runs/<run>/run.json and events.jsonl; start, launch, control, ack, owner, mark, tick,
                               close_unclosed (server restart), status, list, get
  JamApi(root, performance, hub, resolver, now_ms)
                               handle(method, path, query, body) -> (status, body) for /api/piano/deck*,
                               /api/piano/jam* and /api/piano/replay (arsenal/serve.py delegates; the CLI calls it
                               directly when no server answers)

Behaviour worth knowing (5.2):
- A start by claude without now is pending: no epochs until the owner page calls launch (the courtesy gate).
- Starting a Loop or Try while one is running swaps on the old run's next bar line: the old run stops there with
  `replaced` and the new run numbers its own bars from 0 at that epoch, with no count-in (9.4, J0's contract). A play
  overlays a running loop; a new play replaces an older play (on the bar sounding now).
- A pending start (a knock) never stops what sounds: the running loop plays on until the owner launches the knock,
  and launch() swaps it on a bar line then. A newer start replaces an older pending one at once. GET /api/piano/jam
  lists runs still waiting beside the sounding one under `pending`.
- A tempo, next or set change may land before one already scheduled later (a key change waiting for the pass top):
  insert_segment / insert_settings rebuild what follows on the new map, and the reply names the bar actually used.
- A tempo or next asked for during the count-in lands on bar 0 (the reply's note says so). Every change and stop is
  built on a copy of the run and swapped in only once it validates, so a refused one leaves the run as it was.
- The owner lease lasts 30 s from each claim; a claim always wins (Daniel's input is where he is); with no owner the
  first page to ack or launch becomes it.
- tick() stops runs whose passes are done (reason count) and pending runs nobody launched in 90 s (expired).
- close_unclosed() runs at server start only, never in tests' App(): it closes unclosed runs with server-restart.
"""
from __future__ import annotations

import copy
import json
import math
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from arsenal.jam import RUN_API, align as jam_align, cards as jam_cards
from arsenal.jam import schemas as S
from arsenal.jam import tempomap as T
from arsenal.jam.cards import DeckError, DeckStore, now_iso
from arsenal.jam.resolve import BridgeUnavailable, ResolveError, Resolver, key_of, parse_line

ENGINE = "groove/1"
LEASE_MS = 30000
PENDING_EXPIRE_MS = 90000         # 20 s waiting for his rest + a 60 s knock + margin (8.9)
LAUNCH_MIN_LEAD_MS = 150
LEAD_MS = {"claude": 800, "daniel": 250}
LEVEL = 44
HUMANIZE = 0.6
TRY_PASSES_CLI = 2
PAGE_STOP_REASONS = ("page", "cli", "declined", "expired", "device", "stream-lost")
START_KEYS = ("mode", "card_id", "chords", "key", "variant", "slot", "bpm", "backing", "groove", "count_in", "passes",
              "try_backing", "velocity", "humanize", "seed", "walk", "level", "now", "lead_ms", "page_id", "voicing",
              "arp_ms", "by")
CONTROL_KEYS = ("op", "bpm", "card_id", "chords", "variant", "key", "settings", "at", "if_version", "by", "reason")
CONTROL_OPS = ("tempo", "next", "stop", "mute", "unmute", "set")
DEFAULT_AT = {"tempo": "bar", "next": "bar", "set": "bar", "stop": "bar", "mute": "now", "unmute": "now"}
CAP_JAM, CAP_DECK = "jam1", "deck1"


class RunError(Exception):
    def __init__(self, message: str, status: int = 400, field: Optional[str] = None, **extra):
        super().__init__(message)
        self.status = status
        self.field = field
        self.extra = extra


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def new_run_id(now_ms: float) -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(now_ms / 1000)) + "-" + secrets.token_hex(4)


def _schema(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except S.JamSchemaError as exc:
        raise RunError(str(exc), 400, exc.field) from None


# ================================================================================================= store
class RunStore:
    def __init__(self, root=None, now_ms=None):
        self.root = Path(root) if root else jam_cards.DEFAULT_ROOT
        self.now_ms = now_ms or (lambda: time.time() * 1000)
        self._lock = threading.RLock()
        self._recs: Dict[str, dict] = {}
        self._owner: Optional[dict] = None

    # ------------------------------------------------------------------------------------------ files
    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    def _dir(self, run_id) -> Path:
        if not isinstance(run_id, str) or not S.RUN_ID_RE.match(run_id):
            raise RunError(f"no run {run_id}", 404)
        return self.runs_dir / run_id

    def _write(self, rec: dict) -> None:
        run = rec["run"]
        try:
            S.validate_run(run)
        except S.JamSchemaError as exc:
            raise RunError(f"the run came out malformed ({exc}); this is a run store bug", 500) from None
        path = self._dir(run["run"]) / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name("run.json.tmp")
        tmp.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)

    def _commit(self, rec: dict, new_run: dict, refused: Optional[str] = None) -> None:
        """Swap a changed copy of the run in only once it validates, then write it. A copy that does not validate leaves
        the run exactly as it was, in memory and on disk: with `refused` (what was asked) the caller hears 409 naming the
        field, otherwise it is a store bug (500). Changing the run in place first left a broken run in memory that
        answered 500 to every later change and a stop that never reached the page."""
        try:
            S.validate_run(new_run)
        except S.JamSchemaError as exc:
            if refused:
                raise RunError(f"{refused} cannot be applied ({exc}); the run is unchanged", 409, exc.field,
                               version=rec["run"]["last_version"]) from None
            raise RunError(f"the run came out malformed ({exc}); this is a run store bug", 500) from None
        run = rec["run"]
        run.clear()
        run.update(new_run)
        self._write(rec)

    def _append(self, rec: dict, line: dict) -> dict:
        line = dict(seq=rec["seq"], **line)
        try:
            S.validate_run_event(line)
        except S.JamSchemaError as exc:
            raise RunError(f"a run event came out malformed ({exc}); this is a run store bug", 500) from None
        path = self._dir(rec["run"]["run"]) / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(line, separators=(",", ":"), ensure_ascii=False) + "\n")
        rec["seq"] += 1
        if line["kind"] == "ack":
            rec["acks"].add((line["page_id"], line["version"], line["bar"]))
        return line

    def _load(self, run_id: str) -> dict:
        rec = self._recs.get(run_id)
        if rec is not None:
            return rec
        folder = self._dir(run_id)
        try:
            run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise RunError(f"no run {run_id}", 404) from None
        events = self._events(run_id)
        rec = {"run": run, "defs": {}, "acks": set(), "seq": 0, "created_ms": None, "bpm0": None}
        for e in events:
            rec["seq"] = max(rec["seq"], int(e.get("seq", 0)) + 1)
            if e.get("def") is not None:
                rec["defs"][int(e["version"])] = e["def"]
            if e.get("kind") == "start":
                rec["created_ms"], rec["bpm0"] = e.get("recorded_epoch_ms"), e.get("bpm")
            if e.get("kind") == "ack":
                rec["acks"].add((e.get("page_id"), e.get("version"), e.get("bar")))
        self._recs[run_id] = rec
        return rec

    def _events(self, run_id: str) -> List[dict]:
        try:
            text = (self._dir(run_id) / "events.jsonl").read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        out = []
        for line in text.splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    # ------------------------------------------------------------------------------------------ reads
    def _live(self, now: float) -> List[dict]:
        return [rec for rec in self._recs.values()
                if not rec["run"]["closed"] or (rec["run"]["stopped_epoch_ms"] or 0) > now]

    def live_of(self, now: float, mode_class: str) -> List[dict]:
        """The live runs of one class ('play' or 'loop': a loop or try), oldest first."""
        with self._lock:
            live = sorted(self._live(now), key=lambda r: r["run"]["run"])
            return [r for r in live if (r["run"]["mode"] == "play") == (mode_class == "play")]

    def current(self, now: Optional[float] = None, mode_class: Optional[str] = None) -> Optional[dict]:
        """The live run: a loop or try first, else a play. mode_class 'play' or 'loop' asks for one class only. Inside a
        class a run that sounds (or has launched) comes before one still waiting for Daniel's pause, so a knock waiting
        beside a playing loop never hides the loop from `loop stop`, `jam status` or a page's sync."""
        now = self.now_ms() if now is None else now

        def pick(recs):
            launched = [r for r in recs if r["run"]["state"] != "pending"]
            return (launched or recs or [None])[-1]

        with self._lock:
            loops, plays = self.live_of(now, "loop"), self.live_of(now, "play")
            if mode_class == "play":
                return pick(plays)
            if mode_class == "loop":
                return pick(loops)
            return pick(loops) if loops else pick(plays)

    def pending(self, now: Optional[float] = None) -> List[dict]:
        """Runs still waiting for Daniel's pause (the courtesy gate), oldest first."""
        now = self.now_ms() if now is None else now
        with self._lock:
            return [r for r in sorted(self._live(now), key=lambda r: r["run"]["run"]) if r["run"]["state"] == "pending"]

    def owner(self, now: Optional[float] = None) -> Optional[dict]:
        now = self.now_ms() if now is None else now
        o = self._owner
        if o and o["lease_until_epoch_ms"] > now:
            return dict(o)
        return None

    def get(self, run_id: str) -> dict:
        with self._lock:
            rec = self._load(run_id)
            return {"run": copy.deepcopy(rec["run"]), "events": self._events(run_id)}

    def list(self, limit: int = 20, card: Optional[str] = None) -> List[dict]:
        out = []
        if not self.runs_dir.is_dir():
            return out
        for folder in sorted(self.runs_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not (folder.is_dir() and S.RUN_ID_RE.match(folder.name)):
                continue
            with self._lock:
                rec = self._recs.get(folder.name)
                if rec is not None:
                    run = copy.deepcopy(rec["run"])
                else:
                    try:
                        run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        continue
            if card and (run.get("card") or {}).get("id") != card:
                continue
            out.append(run)
            if len(out) >= limit:
                break
        return out

    def counts_by_card(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for run in self.list(limit=10 ** 6):
            cid = (run.get("card") or {}).get("id")
            if cid:
                counts[cid] = counts.get(cid, 0) + 1
        return counts

    def defs_for(self, rec: dict) -> Dict[int, dict]:
        return rec["defs"]

    def position(self, rec: dict, now: float) -> Optional[dict]:
        run = rec["run"]
        if not run["segments"]:
            return None
        try:
            p = T.position(run["segments"], run["beats_per_bar"], now, rec["defs"])
        except T.TempoMapError:
            return None
        return {"bar": p["bar"], "beat": p["beat"], "pass": p["pass"], "slot": p["slot"], "version": run["last_version"],
                "cycle_beat": p["cycle_beat"], "counting_in": p["counting_in"], "rest": p["rest"], "bpm": p["bpm"],
                "def_version": p["def_version"]}

    # ------------------------------------------------------------------------------------------ owner
    def claim(self, page_id: str, claim: bool, now: float) -> Tuple[dict, List[dict]]:
        if not isinstance(page_id, str) or not S.PAGE_ID_RE.match(page_id):
            raise RunError("page_id must be 1 to 80 letters, digits or _ . : -", 400, "page_id")
        frames = []
        with self._lock:
            before = self.owner(now)
            if claim:
                since = before["since"] if before and before["page_id"] == page_id else now
                self._owner = {"page_id": page_id, "lease_until_epoch_ms": now + LEASE_MS, "since": since}
            elif before and before["page_id"] == page_id:
                self._owner = None
            after = self.owner(now)
            if (before or {}).get("page_id") != (after or {}).get("page_id"):
                frames.append(self._owner_changed(after, now))
        return {"owner": after}, frames

    def _owner_changed(self, owner: Optional[dict], now: float) -> dict:
        page = owner["page_id"] if owner else None
        for rec in self._live(now):
            if rec["run"]["owner_page_id"] != page and page is not None:
                rec["run"]["owner_page_id"] = page
                self._write(rec)
        return {"op": "owner", "owner": page, "lease_until_epoch_ms": owner["lease_until_epoch_ms"] if owner else None}

    # ------------------------------------------------------------------------------------------ frames
    @staticmethod
    def _frame(rec: dict, op: str, by: str, **extra) -> dict:
        run = rec["run"]
        frame = {"op": op, "run": run["run"], "mode": run["mode"], "state": run["state"],
                 "version": run["last_version"], "by": by, "segments": run["segments"], "settings": run["settings"],
                 "owner": run["owner_page_id"], "card": run["card"], "key": run["key"],
                 "beats_per_bar": run["beats_per_bar"], "count_in_bars": run["count_in_bars"],
                 "start_epoch_ms": run["start_epoch_ms"], "bar0_epoch_ms": run["bar0_epoch_ms"]}
        frame.update(extra)
        return frame

    # ------------------------------------------------------------------------------------------ start
    def start(self, spec: dict, d: dict, card: Optional[dict], by: str, now: float) -> Tuple[dict, List[dict]]:
        """spec: {mode, bpm, count_in, settings0, now, lead_ms, slot, velocity}; d: the resolved def; card: the stored
        card (its snapshot goes into run.json) or None for bare chords."""
        mode = spec["mode"]
        frames: List[dict] = []
        with self._lock:
            owner = self.owner(now)
            pending = by == "claude" and not spec["now"]
            run_id = new_run_id(now)
            while (self.runs_dir / run_id).exists() or run_id in self._recs:
                run_id = new_run_id(now)
            count_in = spec["count_in"]
            run = {"api": RUN_API, "run": run_id, "mode": mode, "route": "page", "engine": ENGINE,
                   "state": "pending" if pending else "running", "created_at": now_iso(), "created_by": by,
                   "card": d["card"], "card_snapshot": copy.deepcopy(card) if card else None, "key": d["key"],
                   "beats_per_bar": d["beats_per_bar"], "count_in_bars": count_in, "start_epoch_ms": None,
                   "bar0_epoch_ms": None, "segments": [], "settings": [spec["settings0"]], "last_version": 1,
                   "owner_page_id": owner["page_id"] if owner else None,
                   "courtesy": {"held_ms": 0, "via": None if pending else "now"}, "closed": False,
                   "stopped_epoch_ms": None, "stop_bar": None, "stop_reason": None, "late_dropped": 0}
            if spec.get("slot") is not None:
                run["slot"] = spec["slot"]
            if spec.get("velocity") is not None:
                run["velocity"] = spec["velocity"]
            rec = {"run": run, "defs": {1: d}, "acks": set(), "seq": 0, "created_ms": now, "bpm0": spec["bpm"]}
            same_class = self.live_of(now, "play" if mode == "play" else "loop")
            # A run still waiting for Daniel's pause is replaced at once (the newest word wins).
            for waiting in [r for r in same_class if r["run"]["state"] == "pending"]:
                frames += self._stop_now(waiting, "replaced", now, by)
            sounding = [r for r in same_class if r["run"]["state"] == "running"]
            old = sounding[-1] if sounding else None
            swap = None
            if old is not None and not pending:
                if mode != "play":
                    swap = self._swap_line(old, now, now + spec["lead_ms"])
                else:
                    frames += self._stop_now(old, "replaced", now, by)
                    old = None
            elif old is not None:
                # A pending start leaves the sounding run alone: it plays on while the knock waits, and launch() swaps
                # it on a bar line (or replaces a play) when Daniel takes it. Stopping it here, with no bar, left the
                # page handing its bars forever.
                old = None
            if not pending:
                self._place(rec, swap["epoch_ms"] if swap else now + spec["lead_ms"], count_in if not swap else 0)
                if swap:
                    frames += self._stop(old, "replaced", swap["epoch_ms"], swap["bar"], by, "bar", now,
                                         replaced_by=run_id)
            self._recs[run_id] = rec
            self._write(rec)
            line = {"kind": "start", "recorded_epoch_ms": now, "by": by, "version": 1,
                    "effective_bar": None if pending else -run["count_in_bars"], "epoch_ms": run["start_epoch_ms"],
                    "bpm": spec["bpm"], "state": run["state"], "mode": mode, "card": run["card"], "key": run["key"],
                    "settings": run["settings"], "segments": run["segments"], "def": d}
            self._append(rec, line)
            extra = {"swapped_from": old["run"]["run"]} if swap else {}
            frames.append(self._frame(rec, "start", by, effective_bar=line["effective_bar"],
                                      epoch_ms=run["start_epoch_ms"], bpm=spec["bpm"], def_=None, **extra))
            frames[-1]["def"] = frames[-1].pop("def_") or d
            reply = {"run": run_id, "version": 1, "state": run["state"], "start_epoch_ms": run["start_epoch_ms"],
                     "bar0_epoch_ms": run["bar0_epoch_ms"], "count_in_bars": run["count_in_bars"], "def": d,
                     "owner": run["owner_page_id"], **extra}
        return reply, frames

    def _swap_line(self, old: dict, now: float, not_before: float) -> dict:
        """The old run's first bar line both at least 1 beat + 250 ms away (9.4) and not before not_before."""
        run = old["run"]
        land = T.next_line(run["segments"], run["beats_per_bar"], now, "bar", old["defs"])
        bar = max(land["bar"], run["segments"][0]["from_bar"])  # never before the old run's own first bar
        while T.t_epoch(run["segments"], run["beats_per_bar"], bar) < not_before - T.EPS_MS and bar < land["bar"] + 64:
            bar += 1
        return {"bar": bar, "epoch_ms": T.t_epoch(run["segments"], run["beats_per_bar"], bar)}

    def _place(self, rec: dict, start_epoch: float, count_in: int) -> None:
        run = rec["run"]
        run["count_in_bars"] = count_in
        run["segments"] = [T.first_segment(start_epoch, rec["bpm0"], count_in, 1)]
        run["start_epoch_ms"] = start_epoch
        run["bar0_epoch_ms"] = T.t_epoch(run["segments"], run["beats_per_bar"], 0)
        run["state"] = "running"

    # ------------------------------------------------------------------------------------------ launch
    def launch(self, run_id: str, page_id, epoch_ms, via, now: float) -> Tuple[dict, List[dict]]:
        if not isinstance(page_id, str) or not S.PAGE_ID_RE.match(page_id):
            raise RunError("page_id must be 1 to 80 letters, digits or _ . : -", 400, "page_id")
        if not _is_num(epoch_ms):
            raise RunError("epoch_ms must be a number (epoch ms)", 400, "epoch_ms")
        if via is not None and via not in S.COURTESY_VIA:
            raise RunError(f"via must be one of {', '.join(S.COURTESY_VIA)}", 400, "via")
        frames: List[dict] = []
        with self._lock:
            rec = self._load(run_id)
            run = rec["run"]
            if run["state"] != "pending":
                raise RunError(f"run {run_id} is {run['state']}, not waiting for a launch", 409, state=run["state"],
                               version=run["last_version"])
            if epoch_ms < now + LAUNCH_MIN_LEAD_MS - T.EPS_MS:
                raise RunError(f"epoch_ms must be at least {LAUNCH_MIN_LEAD_MS} ms from now", 400, "epoch_ms",
                               now_epoch_ms=now)
            owner = self.owner(now)
            if owner and owner["page_id"] != page_id:
                raise RunError("only the owner page launches a run", 409, owner=owner["page_id"])
            if not owner:
                _, owner_frames = self.claim(page_id, True, now)
                frames += owner_frames
            same_class = [r for r in self.live_of(now, "play" if run["mode"] == "play" else "loop") if r is not rec]
            for waiting in [r for r in same_class if r["run"]["state"] == "pending"]:
                frames += self._stop_now(waiting, "replaced", now, "page")
            sounding = [r for r in same_class if r["run"]["state"] == "running"]
            old = sounding[-1] if sounding else None
            swap = None
            if old is not None and run["mode"] != "play":
                swap = self._swap_line(old, now, epoch_ms)
                frames += self._stop(old, "replaced", swap["epoch_ms"], swap["bar"], "page", "bar", now,
                                     replaced_by=run_id)
            elif old is not None:
                frames += self._stop_now(old, "replaced", now, "page")
            self._place(rec, swap["epoch_ms"] if swap else epoch_ms, 0 if swap else run["count_in_bars"])
            run["owner_page_id"] = page_id
            run["courtesy"] = {"held_ms": max(0.0, now - (rec["created_ms"] or now)), "via": via or "rest"}
            self._write(rec)
            self._append(rec, {"kind": "launch", "recorded_epoch_ms": now, "by": "page",
                               "version": run["last_version"], "start_epoch_ms": run["start_epoch_ms"],
                               "bar0_epoch_ms": run["bar0_epoch_ms"], "page_id": page_id,
                               "held_ms": run["courtesy"]["held_ms"], "via": run["courtesy"]["via"]})
            frames.append(self._frame(rec, "launch", "page", effective_bar=-run["count_in_bars"],
                                      epoch_ms=run["start_epoch_ms"], courtesy=run["courtesy"],
                                      def_version=run["segments"][0]["def_version"]))
            reply = {"version": run["last_version"], "start_epoch_ms": run["start_epoch_ms"],
                     "bar0_epoch_ms": run["bar0_epoch_ms"], "count_in_bars": run["count_in_bars"]}
        return reply, frames

    # ------------------------------------------------------------------------------------------ stop
    def _stop(self, rec: dict, reason: str, epoch: float, bar: Optional[int], by: str, at: Optional[str], now: float,
              approx: bool = False, **extra) -> List[dict]:
        run = rec["run"]
        if run["closed"]:
            return []
        stopped = copy.deepcopy(run)
        stopped.update(state="stopped", closed=True, stopped_epoch_ms=epoch, stop_bar=bar if run["segments"] else None,
                       stop_reason=reason, last_version=run["last_version"] + 1)
        if approx:
            stopped["approx"] = True
        self._commit(rec, stopped)
        line = {"kind": "stop", "recorded_epoch_ms": now, "by": by, "reason": reason, "version": run["last_version"],
                "epoch_ms": epoch, "effective_bar": run["stop_bar"], "stop_bar": run["stop_bar"]}
        if at:
            line["at"] = at
        if approx:
            line["approx"] = True
        self._append(rec, line)
        return [self._frame(rec, "stop", by, reason=reason, effective_bar=run["stop_bar"], epoch_ms=epoch,
                            stop_bar=run["stop_bar"], **extra)]

    def _stop_now(self, rec: dict, reason: str, now: float, by: str, **extra) -> List[dict]:
        """Stop a run at once, on the bar sounding now (never before its first bar): a launched run always stops with a
        real bar, so a page knows which bars to take back. A pending run has no bars and stops with none."""
        run = rec["run"]
        bar = None
        if run["segments"]:
            bar = max(T.bar_at(run["segments"], run["beats_per_bar"], now)["bar"], run["segments"][0]["from_bar"])
        return self._stop(rec, reason, now, bar, by, "now", now, **extra)

    # ------------------------------------------------------------------------------------------ control
    def control(self, run_id: str, op: str, args: dict, by: str, now: float,
                new_def: Optional[dict] = None) -> Tuple[dict, List[dict]]:
        if op not in CONTROL_OPS:
            raise RunError(f"op must be one of {', '.join(CONTROL_OPS)} (got {op!r})", 400, "op")
        at = args.get("at")
        if at is None:
            at = "pass" if op == "next" and args.get("key_only") else DEFAULT_AT[op]
        if at not in T.AT_LINES:
            raise RunError(f"at must be one of {', '.join(T.AT_LINES)} (got {at!r})", 400, "at")
        with self._lock:
            rec = self._load(run_id)
            run = rec["run"]
            if_version = args.get("if_version")
            if if_version is not None:
                if not _is_int(if_version):
                    raise RunError("if_version must be an integer", 400, "if_version")
                if if_version != run["last_version"]:
                    raise RunError(f"version changed: run {run_id} is at version {run['last_version']}", 409,
                                   version=run["last_version"])
            if run["closed"]:
                raise RunError(f"run {run_id} has stopped ({run['stop_reason']})", 409, version=run["last_version"],
                               state=run["state"])
            if op == "stop":
                reason = args.get("reason") or ("page" if by == "daniel" else "cli")
                if reason not in PAGE_STOP_REASONS:
                    raise RunError(f"reason must be one of {', '.join(PAGE_STOP_REASONS)}", 400, "reason")
                if run["state"] == "pending" or at == "now":
                    frames = self._stop_now(rec, reason, now, by)  # never before the run's first bar (a long lead)
                    return {"version": run["last_version"], "effective_bar": run["stop_bar"], "epoch_ms": now}, frames
                land = T.next_line(run["segments"], run["beats_per_bar"], now, at, rec["defs"])
                frames = self._stop(rec, reason, land["epoch_ms"], land["bar"], by, at, now)
                return {"version": run["last_version"], "effective_bar": land["bar"], "epoch_ms": land["epoch_ms"],
                        "at": at}, frames
            if run["state"] == "pending":
                raise RunError(f"run {run_id} is waiting for Daniel's pause; stop it, or change it once it plays", 409,
                               version=run["last_version"], state="pending")
            if run["mode"] == "play":
                raise RunError("a play run only stops", 400, "op")
            m, segs = run["beats_per_bar"], run["segments"]
            used_at = at
            if op in ("tempo", "next", "set") and at in ("now", "beat"):
                used_at = "bar"  # tempo segments, def versions and settings start on bar lines (9.1, 4.3)
            if used_at == "now":
                land = {"bar": T.bar_at(segs, m, now)["bar"], "beat": 0, "epoch_ms": now}
            else:
                land = T.next_line(segs, m, now, used_at, rec["defs"])
            # never before the run's first bar (a long lead), and settings never before their first entry
            bar = max(land["bar"], segs[0]["from_bar"])
            counted_in = False
            if op in ("tempo", "next") and bar < 0:
                # A tempo or next asked for during the count-in lands on bar 0: the count-in keeps the start's tempo
                # and bar 0 stays where the start put it (bar0_epoch_ms), and a count-in bar never becomes a backing bar.
                bar, counted_in = 0, True
            if op in ("mute", "unmute", "set"):
                bar = max(bar, run["settings"][0]["from_bar"])
            epoch = land["epoch_ms"] if bar == land["bar"] else T.t_epoch(segs, m, bar)
            version = run["last_version"] + 1
            line = {"kind": "change", "op": op, "recorded_epoch_ms": now, "by": by, "version": version,
                    "effective_bar": bar, "epoch_ms": epoch, "at": used_at}
            extra = {}
            changed = copy.deepcopy(run)  # built on a copy and swapped in only once it validates (_commit)
            if op == "tempo":
                bpm = self._bpm(args.get("bpm"), T.segment_at(segs, bar)["bpm"])
                changed["segments"] = insert_segment(segs, m, bar, bpm=bpm)
                line.update(bpm=bpm, segments=changed["segments"])
                extra["bpm"] = bpm
            elif op == "next":
                if new_def is None:
                    raise RunError("next needs a card, chords, a variant or a key", 400, "card_id")
                if new_def["beats_per_bar"] != m:
                    raise RunError(f"the next line is in {new_def['beats_per_bar']} beats a bar; this run keeps "
                                   f"{m}", 400, "card_id")
                changed["segments"] = insert_segment(segs, m, bar, def_version=version)
                line.update(def_=None, card=new_def["card"], key=new_def["key"], segments=changed["segments"])
                line.pop("def_")
                line["def"] = new_def
                if new_def["card"] is not None:
                    line["variant"] = new_def["card"]["variant"]
                extra["def"] = new_def
            else:
                if op in ("mute", "unmute"):
                    partial = {"muted": op == "mute"}
                else:
                    partial = args.get("settings")
                    if not isinstance(partial, dict) or not partial:
                        raise RunError("settings must be an object with the fields to change", 400, "settings")
                    _schema(S._unknown, partial, S.SETTINGS_KEYS[1:] + S.SETTINGS_OPTIONAL_KEYS, "settings")
                new_settings = insert_settings(run["settings"], bar, partial)
                _schema(S._settings, new_settings, run["mode"])
                changed["settings"] = new_settings
                line["settings"] = partial
                extra["change_settings"] = partial
            changed["last_version"] = version
            self._commit(rec, changed, refused=f"{op} on bar {bar}")
            if op == "next":
                rec["defs"][version] = new_def
            self._append(rec, line)
            frames = [self._frame(rec, "change", by, change=op, effective_bar=bar, epoch_ms=epoch, at=used_at,
                                  **extra)]
            reply = {"version": version, "effective_bar": bar, "epoch_ms": epoch, "at": used_at}
            if "bpm" in extra:
                reply["bpm"] = extra["bpm"]
            notes = []
            if used_at != at:
                notes.append(f"{op} changes land on bar lines, so this one lands on bar {bar}")
            if counted_in:
                notes.append(f"asked for during the count-in, this {op} lands on bar 0, where the loop begins")
            if notes:
                reply["note"] = "; ".join(notes)
            return reply, frames

    @staticmethod
    def _bpm(value, current: float) -> float:
        if isinstance(value, str) and re.fullmatch(r"[+-]\d+(\.\d+)?", value.strip()):
            bpm = current + float(value)
        elif isinstance(value, str) and re.fullmatch(r"\d+(\.\d+)?", value.strip()):
            bpm = float(value)
        elif _is_num(value):
            bpm = float(value)
        else:
            raise RunError(f'bpm must be a number or a relative "+N" / "-N" (got {value!r})', 400, "bpm")
        bpm = int(bpm) if float(bpm).is_integer() else round(bpm, 3)
        if not S.BPM_MIN <= bpm <= S.BPM_MAX:
            raise RunError(f"bpm must be {S.BPM_MIN}..{S.BPM_MAX} (got {bpm:g})", 400, "bpm")
        return bpm

    # ------------------------------------------------------------------------------------------ ack, mark
    def ack(self, run_id: str, body, now: float) -> Tuple[dict, List[dict]]:
        a = _schema(S.validate_ack, body)
        frames: List[dict] = []
        with self._lock:
            rec = self._load(run_id)
            run = rec["run"]
            if a["version"] > run["last_version"]:
                raise RunError(f"version {a['version']} is newer than the run's {run['last_version']}", 400, "version")
            key = (a["page_id"], a["version"], a["bar"])
            if key in rec["acks"]:
                return {"ok": True, "duplicate": True}, frames
            if not self.owner(now) and a["role"] == "owner" or not self.owner(now) and run["owner_page_id"] is None:
                _, owner_frames = self.claim(a["page_id"], True, now)
                frames += owner_frames
            self._append(rec, {"kind": "ack", "recorded_epoch_ms": now, "by": "page", **a})
            if a["page_id"] == run["owner_page_id"] and a["late_dropped"] > run["late_dropped"]:
                run["late_dropped"] = a["late_dropped"]
                self._write(rec)
            if a["stopped"] and not run["closed"] and a["page_id"] == run["owner_page_id"]:
                bar = a.get("stop_bar") if a.get("stop_bar") is not None else a["bar"]
                epoch = T.t_epoch(run["segments"], run["beats_per_bar"], bar) if run["segments"] else now
                frames += self._stop(rec, a["stopped"], epoch, bar, "page", "now", now)
        return {"ok": True, "duplicate": False}, frames

    def mark(self, text, run_id: Optional[str], epoch_ms, by: str, now: float) -> Tuple[dict, List[dict]]:
        if not isinstance(text, str) or not text.strip() or len(text) > S.MARK_TEXT_MAX:
            raise RunError(f"text must be 1 to {S.MARK_TEXT_MAX} characters", 400, "text")
        if epoch_ms is not None and not _is_num(epoch_ms):
            raise RunError("epoch_ms must be a number or null", 400, "epoch_ms")
        with self._lock:
            if run_id is None:
                rec = self.current(now)
                if rec is None:
                    latest = self.list(limit=1)
                    if not latest:
                        raise RunError("no run to mark", 404)
                    rec = self._load(latest[0]["run"])
            else:
                rec = self._load(run_id)
            run = rec["run"]
            at = epoch_ms if epoch_ms is not None else now
            line = {"kind": "mark", "recorded_epoch_ms": now, "by": by, "text": text, "run": run["run"],
                    "epoch_ms": at, "version": run["last_version"]}
            if run["segments"]:
                line["bar"] = T.bar_at(run["segments"], run["beats_per_bar"], at)["bar"]
            line = self._append(rec, line)
            frame = {"op": "mark", "run": run["run"], "text": text, "by": by, "seq": line["seq"], "epoch_ms": at,
                     "bar": line.get("bar"), "version": run["last_version"]}
        return {"run": run["run"], "seq": line["seq"]}, [frame]

    # ------------------------------------------------------------------------------------------ time passing
    def tick(self, now: Optional[float] = None) -> List[dict]:
        now = self.now_ms() if now is None else now
        frames: List[dict] = []
        with self._lock:
            for rec in list(self._live(now)):
                run = rec["run"]
                if run["closed"]:
                    continue
                try:
                    if run["state"] == "pending":
                        if rec["created_ms"] is not None and now - rec["created_ms"] >= PENDING_EXPIRE_MS:
                            frames += self._stop(rec, "expired", now, None, "server", "now", now)
                        continue
                    end = self._passes_end(rec)
                    if end is not None and now >= end[1]:
                        frames += self._stop(rec, "count", end[1], end[0], "server", "pass", now)
                except (RunError, T.TempoMapError):
                    continue  # one run that cannot close here must never fail an unrelated jam route
        return frames

    def _passes_end(self, rec: dict) -> Optional[Tuple[int, float]]:
        run = rec["run"]
        settings = run["settings"][-1]
        passes = settings["passes"]
        if not passes or not run["segments"]:
            return None
        seg = run["segments"][-1]
        d = rec["defs"].get(seg["def_version"])
        if not d:
            return None
        m = run["beats_per_bar"]
        cycle_bars = d["cycle_beats"] // m
        end_bar = seg["def_from_bar"] + passes * cycle_bars
        while end_bar < settings["from_bar"]:
            end_bar += cycle_bars
        return end_bar, T.t_epoch(run["segments"], m, end_bar)

    def close_unclosed(self, now: Optional[float] = None) -> List[str]:
        """At server start: every run left open gets a stop line with server-restart and approx, at the time of its
        last timeline line (DATA 6.6)."""
        now = self.now_ms() if now is None else now
        closed = []
        if not self.runs_dir.is_dir():
            return closed
        with self._lock:
            for folder in sorted(self.runs_dir.iterdir()):
                if not (folder.is_dir() and S.RUN_ID_RE.match(folder.name)):
                    continue
                try:
                    rec = self._load(folder.name)
                except (RunError, OSError, ValueError):
                    continue
                run = rec["run"]
                if run.get("closed"):
                    continue
                events = self._events(folder.name)
                last = max([e.get("recorded_epoch_ms") or 0 for e in events] or [0])
                epoch = last or now  # the time of its last timeline line (DATA 6.6), hence approx
                bar = T.bar_at(run["segments"], run["beats_per_bar"], epoch)["bar"] if run["segments"] else None
                self._stop(rec, "server-restart", epoch, bar, "server", None, now, approx=True)
                closed.append(folder.name)
        return closed

    def status(self, now: float) -> dict:
        with self._lock:
            rec = self.current(now)
            play = self.current(now, "play")
            out = {"run": None, "now_epoch_ms": now, "position": None, "owner": self.owner(now), "def": None,
                   "defs": {}, "play": None}
            if rec is not None:
                out["run"] = copy.deepcopy(rec["run"])
                out["position"] = self.position(rec, now)
                versions = {s["def_version"] for s in rec["run"]["segments"]} or {1}
                out["defs"] = {str(v): rec["defs"][v] for v in sorted(versions) if v in rec["defs"]}
                last = max(versions)
                out["def"] = rec["defs"].get(last)
            if play is not None and play is not rec:
                out["play"] = copy.deepcopy(play["run"])
            # runs waiting for Daniel's pause beside the ones above (a knock while a loop plays), so a page that
            # re-reads state still gates them
            shown = {r["run"] for r in (out["run"], out["play"]) if r}
            out["pending"] = [copy.deepcopy(r["run"]) for r in self.pending(now) if r["run"]["run"] not in shown]
        return out


# ================================================================================================= the routes
class JamApi:
    """The deck, jam and replay routes, independent of HTTP: handle(method, path, query, body) -> (status, body)."""

    def __init__(self, root=None, performance=None, hub=None, resolver: Optional[Resolver] = None, now_ms=None,
                 seed_path=None):
        self.root = Path(root) if root else jam_cards.DEFAULT_ROOT
        self.resolver = resolver or Resolver()
        self.deck = DeckStore(self.root, reader=self.resolver.page_reads)
        self.runs = RunStore(self.root, now_ms)
        self.performance = performance
        self.hub = hub
        self.seed_path = seed_path

    # ------------------------------------------------------------------------------------------ plumbing
    def now(self) -> float:
        return self.runs.now_ms()

    def _hub(self):
        """The cue hub, or None. hub may be a callable returning it (serve.App passes lambda: self.cues, so a hub
        swapped in later is the one used)."""
        return self.hub() if callable(self.hub) else self.hub

    def publish(self, kind: str, payload: dict) -> None:
        hub = self._hub()
        if hub is not None:
            hub.publish_event(kind, payload)

    def pages(self) -> dict:
        hub = self._hub()
        if hub is None:
            return {"listeners": 0, "caps": {CAP_JAM: 0, CAP_DECK: 0}, "pages": []}
        st = hub.status()
        return {"listeners": st.get("listeners", 0), "caps": st.get("caps") or {CAP_JAM: 0, CAP_DECK: 0},
                "pages": st.get("pages") or []}

    def tick(self) -> None:
        for frame in self.runs.tick(self.now()):
            self.publish("jam", frame)

    def handle(self, method: str, path: str, query: Optional[dict] = None, body=None) -> Tuple[int, dict]:
        query = query or {}
        try:
            if method == "POST":
                if not isinstance(body, dict):
                    return 400, {"error": "the body must be a JSON object"}
                by = body.get("by", "claude")
                if by not in S.AUTHORS:
                    return 400, {"error": f"by must be claude or daniel (got {by!r})", "field": "by"}
            else:
                by = None
            for pattern, verb, handler in self._routes():
                if verb != method:
                    continue
                m = re.fullmatch(pattern, path)
                if m:
                    if path.startswith("/api/piano/jam"):
                        self.tick()
                    return handler(*m.groups(), query=query, body=body, by=by)
            return 404, {"error": f"no route for {method} {path}"}
        except (DeckError, RunError) as exc:
            out = {"error": str(exc), **exc.extra}
            if exc.field:
                out["field"] = exc.field
            return exc.status, out
        except ResolveError as exc:
            return 400, {"error": str(exc), "field": exc.field}
        except S.JamSchemaError as exc:
            return 400, {"error": str(exc), "field": exc.field}
        except BridgeUnavailable as exc:
            return 503, {"error": str(exc)}
        except T.TempoMapError as exc:  # a change the run's map cannot take: a conflict, never a server error
            return 409, {"error": str(exc)}

    def _routes(self):
        card = r"([a-z0-9][a-z0-9-]{0,47})"
        run = r"(\d{8}-\d{6}-[0-9a-f]{8})"
        return [
            (r"/api/piano/deck", "GET", self._deck_get),
            (rf"/api/piano/deck/cards/{card}", "GET", self._card_get),
            (rf"/api/piano/deck/cards/{card}/resolve", "GET", self._card_resolve),
            (r"/api/piano/deck/cards", "POST", self._card_create),
            (rf"/api/piano/deck/cards/{card}/(update|delete|restore|keep)", "POST", self._card_post),
            (r"/api/piano/deck/templates", "POST", self._templates),
            (r"/api/piano/deck/order", "POST", self._order),
            (r"/api/piano/deck/seed", "POST", self._seed),
            (r"/api/piano/deck/open", "POST", self._open),
            (r"/api/piano/deck/trash", "GET", self._trash),
            (r"/api/piano/replay", "GET", self._replay),
            (r"/api/piano/jam", "GET", self._jam_get),
            (r"/api/piano/jam/start", "POST", self._start),
            (rf"/api/piano/jam/runs/{run}/(launch|control|ack)", "POST", self._run_post),
            (r"/api/piano/jam/owner", "POST", self._owner),
            (r"/api/piano/jam/mark", "POST", self._mark),
            (r"/api/piano/jam/runs", "GET", self._runs_get),
            (rf"/api/piano/jam/runs/{run}", "GET", self._run_get),
        ]

    @staticmethod
    def _q(query: dict, name: str, default=None):
        values = query.get(name)
        if not values:
            return default
        return values[0] if isinstance(values, list) else values

    # ------------------------------------------------------------------------------------------ deck
    def _deck_frame(self, op: str, card: Optional[dict], by: str, deck_rev: int, **extra) -> None:
        payload = {"op": op, "card_id": card["id"] if card else None, "rev": card["rev"] if card else None,
                   "deck_rev": deck_rev, "by": by}
        if card is not None and op in ("upsert", "restore"):
            payload["summary"] = DeckStore.summary(card, self.runs.counts_by_card().get(card["id"], 0))
        payload.update(extra)
        self.publish("deck", payload)

    def _deck_get(self, query, body, by):
        archived = self._q(query, "archived", "0") in ("1", "true")
        return 200, self.deck.doc(self.runs.counts_by_card(), group=self._q(query, "group"),
                                  kind=self._q(query, "kind"), tag=self._q(query, "tag"), by=self._q(query, "by"),
                                  archived=archived)

    def _card_get(self, card_id, query, body, by):
        return 200, {"card": self.deck.get(card_id)}

    def _card_resolve(self, card_id, query, body, by):
        card = self.deck.get(card_id)
        slot = self._q(query, "slot")
        if slot is not None:
            if not re.fullmatch(r"\d{1,3}", slot):
                return 400, {"error": "slot must be a chord slot number from 0", "field": "slot"}
            slot = int(slot)
        d = self.resolver.resolve(card, key=self._q(query, "key"), variant=self._q(query, "variant"),
                                  backing=self._q(query, "backing"), voicing=self._q(query, "voicing"), slot=slot)
        return 200, {"def": d}

    def _card_create(self, query, body, by):
        _only(body, ("card", "by"))
        out = self.deck.create(body.get("card"), by)
        self._deck_frame("upsert", out["card"], by, out["deck_rev"])
        return 200, {k: out[k] for k in ("id", "rev", "card", "warnings")}

    def _card_post(self, card_id, action, query, body, by):
        if action == "update":
            _only(body, ("patch", "if_rev", "by"))
            out = self.deck.update(card_id, body.get("patch"), body.get("if_rev"), by)
            self._deck_frame("upsert", out["card"], by, out["deck_rev"])
            return 200, {k: out[k] for k in ("id", "rev", "card", "warnings")}
        if action == "delete":
            _only(body, ("if_rev", "by"))
            out = self.deck.delete(card_id, body.get("if_rev"), by)
            self.publish("deck", {"op": "delete", "card_id": card_id, "rev": out["rev"], "deck_rev": out["deck_rev"],
                                  "by": by})
            return 200, {"id": card_id, "trashed": out["trashed"]}
        if action == "restore":
            _only(body, ("by",))
            out = self.deck.restore(card_id, by)
            self._deck_frame("restore", out["card"], by, out["deck_rev"])
            return 200, {k: out[k] for k in ("id", "rev", "card", "warnings")}
        _only(body, ("by", "key"))
        out = self.deck.keep(card_id, by, body.get("key"))
        self._deck_frame("upsert", out["card"], by, out["deck_rev"])
        return 200, {k: out[k] for k in ("id", "rev", "card", "warnings")}

    def _templates(self, query, body, by):
        _only(body, ("capture", "moment", "by"))
        if ("capture" in body) == ("moment" in body):
            return 400, {"error": "send capture (the page) or moment (the log), one of them", "field": "capture"}
        out = self.deck.template_from_capture(body["capture"], by) if "capture" in body else \
            self.deck.template_from_moment(body["moment"], by)
        self._deck_frame("upsert", out["card"], by, out["deck_rev"])
        return 200, {k: out[k] for k in ("id", "rev", "card", "warnings")}

    def _order(self, query, body, by):
        _only(body, ("order", "if_rev", "by"))
        out = self.deck.order(body.get("order"), body.get("if_rev"), by)
        self.publish("deck", {"op": "order", "card_id": None, "rev": None, "deck_rev": out["rev"], "by": by,
                              "order": out["order"]})
        return 200, {"rev": out["rev"]}

    def _seed(self, query, body, by):
        _only(body, ("update", "dry_run", "by", "moments"))
        doc = jam_cards.load_seed(self.seed_path)
        out = self.deck.seed(doc, body.get("moments"), bool(body.get("update")), bool(body.get("dry_run")), by)
        if not out["dry_run"] and (out["installed"] or out["updated"]):
            self.publish("deck", {"op": "seed", "card_id": None, "rev": None, "deck_rev": out["deck_rev"], "by": by,
                                  "installed": out["installed"], "updated": out["updated"]})
        return 200, out

    def _open(self, query, body, by):
        _only(body, ("card_id", "by"))
        card = self.deck.get(self.deck.find(body.get("card_id")))
        self.publish("deck", {"op": "open", "card_id": card["id"], "rev": card["rev"],
                              "deck_rev": self.deck.deck()["rev"], "by": by})
        return 200, {"id": card["id"], "listeners": self.pages()["caps"].get(CAP_DECK, 0)}

    def _trash(self, query, body, by):
        return 200, {"trash": self.deck.trash()}

    def _replay(self, query, body, by):
        from arsenal.performance import PerformanceError
        from arsenal.pianocue import CueError, build_replay_cue, parse_clock, validate_cue
        if self.performance is None:
            return 404, {"error": "no practice log on this server (--no-performance-log)"}
        session = self._q(query, "session")
        if session == "latest":
            session = self.performance.latest()
        try:
            at = self._q(query, "at")
            if at is None:
                return 400, {"error": "replay needs at (m:ss into the session)", "field": "at"}
            seconds = float(self._q(query, "seconds", "8"))
            speed = float(self._q(query, "speed", "1"))
            events = self.performance.events(session)
            cue = validate_cue(build_replay_cue(events, parse_clock(at), seconds, speed, at_text=at, session=session))
        except PerformanceError as exc:
            return getattr(exc, "status", 404), {"error": str(exc), "field": "session"}
        except (CueError, ValueError) as exc:
            return 400, {"error": str(exc)}
        return 200, {"cue": cue}

    # ------------------------------------------------------------------------------------------ jam
    def _jam_get(self, query, body, by):
        out = self.runs.status(self.now())
        out["pages"] = self.pages()["pages"]
        return 200, out

    def _runs_get(self, query, body, by):
        limit = self._q(query, "limit", "20")
        if not re.fullmatch(r"\d{1,4}", str(limit)):
            return 400, {"error": "limit must be a number", "field": "limit"}
        card = self._q(query, "card")
        return 200, {"runs": self.runs.list(max(1, int(limit)), card)}

    def _run_get(self, run_id, query, body, by):
        out = self.runs.get(run_id)
        try:
            out["alignment"] = jam_align.align(out["run"], out["events"], self.performance)
        except Exception as exc:  # alignment is a convenience here; the run itself always answers
            out["alignment"] = [{"refused": True, "reason": f"{type(exc).__name__}: {exc}"}]
        return 200, out

    def _start(self, query, body, by):
        _only(body, START_KEYS)
        mode = body.get("mode")
        if mode not in S.MODES:
            return 400, {"error": f"mode must be one of {', '.join(S.MODES)} (got {mode!r})", "field": "mode"}
        d, card, variant_tempo = self._def_for(body, mode, None)
        settings = S.card_settings(card) if card else None
        bpm = body.get("bpm")
        if bpm is None:
            bpm = (variant_tempo or {}).get("bpm") or (settings["tempo"]["bpm"] if settings else 66)
        _check_num(bpm, "bpm", S.BPM_MIN, S.BPM_MAX)
        count_in = body.get("count_in", 0 if mode == "play" else 1)
        _check_int(count_in, "count_in", 0, S.COUNT_IN_MAX)
        if mode == "play" and count_in:
            return 400, {"error": "count_in must be 0 for a play run", "field": "count_in"}
        groove = body.get("groove") or (settings["groove_v1"] if settings else ("ballad" if bpm < 80 else "pulse"))
        if groove not in S.GROOVES:
            return 400, {"error": f"groove must be one of {', '.join(S.GROOVES)}", "field": "groove"}
        backing = body.get("backing") or d["backing"]
        if backing not in S.BACKINGS:
            return 400, {"error": f"backing must be one of {', '.join(S.BACKINGS)}", "field": "backing"}
        try_backing = body.get("try_backing", "bass" if mode == "try" else None)
        if mode == "try" and try_backing not in S.TRY_BACKINGS:
            return 400, {"error": f"try_backing must be one of {', '.join(S.TRY_BACKINGS)}", "field": "try_backing"}
        if mode != "try" and try_backing is not None:
            return 400, {"error": "try_backing is only for a try run", "field": "try_backing"}
        level = body.get("level", LEVEL)
        _check_int(level, "level", S.VELOCITY_MIN, S.VELOCITY_MAX)
        humanize = body.get("humanize", HUMANIZE)
        _check_num(humanize, "humanize", 0, 1)
        seed = body.get("seed")
        if seed is None:
            seed = secrets.randbits(32)
        _check_int(seed, "seed", 0, 2 ** 32 - 1)
        walk = body.get("walk", 1)
        _check_int(walk, "walk", 0, 1)
        # a Play plays once, a Try ends after 2 passes (7.2's default, now for the page's Try too), a Loop runs on
        passes = body.get("passes", {"play": 1, "try": TRY_PASSES_CLI}.get(mode, 0))
        _check_int(passes, "passes", 0, None)
        velocity = body.get("velocity")
        if velocity is not None:
            _check_int(velocity, "velocity", S.VELOCITY_MIN, S.VELOCITY_MAX)
        arp_ms = body.get("arp_ms")
        if arp_ms is not None:
            _check_int(arp_ms, "arp_ms", 0, S.ARP_MAX_MS)
        if mode == "play" and (velocity is not None or arp_ms is not None):
            d = copy.deepcopy(d)  # a Play's --vel and --arp reach the page as the def's own per-slot values
            for sl in d["slots"]:
                if velocity is not None:
                    sl["vel"] = velocity
                if arp_ms is not None:
                    sl["arp_ms"] = arp_ms
        now_flag = body.get("now", False)
        if not isinstance(now_flag, bool):
            return 400, {"error": "now must be true or false", "field": "now"}
        lead_ms = body.get("lead_ms", LEAD_MS[by])
        _check_num(lead_ms, "lead_ms", 0, 10000)
        page_id = body.get("page_id")
        if page_id is not None and (not isinstance(page_id, str) or not S.PAGE_ID_RE.match(page_id)):
            return 400, {"error": "page_id must be 1 to 80 letters, digits or _ . : -", "field": "page_id"}
        now = self.now()
        if page_id is not None and by == "daniel":
            _, frames = self.runs.claim(page_id, True, now)
            for f in frames:
                self.publish("jam", f)
        settings0 = {"from_bar": 0, "groove": groove, "backing": backing, "level": level, "humanize": humanize,
                     "seed": seed, "walk": walk, "try_backing": try_backing if mode == "try" else None,
                     "passes": passes, "ending": "cut"}
        spec = {"mode": mode, "bpm": bpm, "count_in": count_in, "settings0": settings0, "now": now_flag,
                "lead_ms": lead_ms, "slot": body.get("slot"), "velocity": velocity}
        reply, frames = self.runs.start(spec, d, card, by, now)
        for f in frames:
            self.publish("jam", f)
        pages = self.pages()
        reply.update(jam_pages=pages["caps"].get(CAP_JAM, 0), listeners=pages["listeners"], bpm=bpm)
        return 200, reply

    def _def_for(self, body: dict, mode: Optional[str], current: Optional[dict]):
        """(def, card or None, variant tempo) for a start or a next: card_id or chords (+ key)."""
        variant, key, slot = body.get("variant"), body.get("key"), body.get("slot")
        if slot is not None and (not _is_int(slot) or slot < 0):
            raise RunError("slot must be a chord slot number from 0", 400, "slot")
        voicing = body.get("voicing")
        if body.get("card_id") is not None and body.get("chords") is not None:
            raise RunError("send card_id or chords, not both", 400, "chords")
        if body.get("card_id") is not None:
            card = self.deck.get(self.deck.find(body["card_id"]))
            if variant is None and mode == "play" and card.get("kind") == "concept" and card.get("variants"):
                variant = "all"
            d = self.resolver.resolve(card, key=key, variant=variant, backing=body.get("backing"), voicing=voicing,
                                      slot=slot)
            vt = next((v.get("tempo") for v in card.get("variants") or [] if v["id"] == d["card"]["variant"]), None)
            return d, card, vt
        chords = body.get("chords")
        if chords is None:
            raise RunError("start needs card_id or chords", 400, "card_id")
        if key is None:
            raise RunError("chords need a key", 400, "key")
        if isinstance(chords, str):
            try:
                chords = parse_line(chords)
            except ValueError as exc:
                raise RunError(str(exc), 400, "chords") from None
        if not isinstance(chords, list):
            raise RunError("chords must be a chord line (a string or a list of items)", 400, "chords")
        meter = current["beats_per_bar"] if current else 4
        d = self.resolver.resolve_chords(chords, key, meter=meter, backing=body.get("backing") or "comp",
                                         voicing=voicing or "spread", slot=slot)
        return d, None, None

    def _run_post(self, run_id, action, query, body, by):
        now = self.now()
        if action == "launch":
            _only(body, ("page_id", "epoch_ms", "via", "by"))
            reply, frames = self.runs.launch(run_id, body.get("page_id"), body.get("epoch_ms"), body.get("via"), now)
        elif action == "ack":
            ack = {k: v for k, v in body.items() if k != "by"}
            reply, frames = self.runs.ack(run_id, ack, now)
        else:
            _only(body, CONTROL_KEYS)
            op = body.get("op")
            args = {k: body.get(k) for k in ("at", "if_version", "bpm", "settings", "reason")}
            new_def = None
            if op == "next":
                new_def, key_only = self._next_def(run_id, body)
                args["key_only"] = key_only
            reply, frames = self.runs.control(run_id, op, args, by, now, new_def)
        for f in frames:
            self.publish("jam", f)
        return 200, reply

    def _next_def(self, run_id: str, body: dict) -> Tuple[dict, bool]:
        rec = self.runs._load(run_id)
        run = rec["run"]
        current = rec["defs"][max(rec["defs"])]
        if body.get("card_id") is not None or body.get("chords") is not None:
            key = body.get("key") or (current["key"] if body.get("chords") is not None else None)
            d, _, _ = self._def_for(dict(body, key=key, backing=None), None, run)
            return d, False
        cur_card = current["card"]
        if cur_card is None:
            raise RunError("a run on bare chords moves on by sending the next chords", 400, "chords")
        card = self.deck.get(cur_card["id"])
        if body.get("key") is not None or body.get("variant") is not None:
            variant = body.get("variant") if body.get("variant") is not None else cur_card["variant"]
            d = self.resolver.resolve(card, key=body.get("key") or current["key"], variant=variant)
            return d, body.get("variant") is None
        variants = [v["id"] for v in card.get("variants") or []]
        if card.get("kind") == "concept" and variants:
            at = variants.index(cur_card["variant"]) if cur_card["variant"] in variants else -1
            return self.resolver.resolve(card, key=current["key"], variant=variants[(at + 1) % len(variants)]), False
        order = [c["id"] for c in self.deck.list()]
        if not order:
            raise RunError("the deck is empty", 400, "card_id")
        at = order.index(card["id"]) if card["id"] in order else -1
        nxt = self.deck.get(order[(at + 1) % len(order)])
        return self.resolver.resolve(nxt), False

    def _owner(self, query, body, by):
        _only(body, ("page_id", "claim", "by"))
        claim = body.get("claim", True)
        if not isinstance(claim, bool):
            return 400, {"error": "claim must be true or false", "field": "claim"}
        reply, frames = self.runs.claim(body.get("page_id"), claim, self.now())
        for f in frames:
            self.publish("jam", f)
        return 200, reply

    def _mark(self, query, body, by):
        _only(body, ("text", "run", "epoch_ms", "by"))
        run_id = body.get("run")
        if run_id is not None and (not isinstance(run_id, str) or not S.RUN_ID_RE.match(run_id)):
            return 400, {"error": "run must be a run id", "field": "run"}
        reply, frames = self.runs.mark(body.get("text"), run_id, body.get("epoch_ms"), by, self.now())
        for f in frames:
            self.publish("jam", f)
        return 200, reply


def insert_segment(segs: List[dict], m: int, bar: int, bpm=None, def_version: Optional[int] = None) -> List[dict]:
    """The run's segments with a tempo (bpm) or next (def_version, its cycle starting at `bar`) change at `bar`, which
    may land before a change already scheduled later (a key change waiting for the pass top when Daniel presses `]`).
    Later segments are rebuilt on the new map, so every epoch stays where the tempo map puts it:
    - a tempo change: a later segment that only carried the old bpm takes the new one; a later tempo change keeps its;
    - a next change: the newest line wins, so later def changes fold into it (their tempo changes stay).
    A later segment that is left carrying nothing is dropped."""
    if bar >= segs[-1]["from_bar"]:
        return T.add_segment(segs, m, bar, bpm=bpm, def_version=def_version,
                             def_from_bar=bar if def_version is not None else None)
    in_effect = T.segment_at(segs, bar)
    out = [dict(s) for s in segs if s["from_bar"] < bar]
    out.append({"from_bar": bar, "bpm": in_effect["bpm"] if bpm is None else bpm,
                "epoch_ms": T.t_epoch(segs, m, bar),
                "def_version": in_effect["def_version"] if def_version is None else def_version,
                "def_from_bar": in_effect["def_from_bar"] if def_version is None else bar})
    old_prev = in_effect
    for s in segs:
        if s["from_bar"] <= bar:
            continue
        cur = out[-1]
        seg_bpm = cur["bpm"] if bpm is not None and s["bpm"] == old_prev["bpm"] else s["bpm"]
        if def_version is None:
            seg_def = (s["def_version"], s["def_from_bar"])
        else:
            seg_def = (cur["def_version"], cur["def_from_bar"])
        old_prev = s
        if seg_bpm == cur["bpm"] and seg_def == (cur["def_version"], cur["def_from_bar"]):
            continue
        out.append({"from_bar": s["from_bar"], "bpm": seg_bpm, "epoch_ms": T.t_epoch(out, m, s["from_bar"]),
                    "def_version": seg_def[0], "def_from_bar": seg_def[1]})
    return out


def insert_settings(settings: List[dict], bar: int, partial: dict) -> List[dict]:
    """The run's settings with `partial` taking effect at `bar`, which may come before an entry already scheduled later
    (a `set --at pass` waiting): the change gets a real entry at its own bar, and a later entry keeps the fields it set
    itself while taking the new values of the fields it only carried. An entry left identical to the one before it is
    dropped."""
    bar = max(bar, settings[0]["from_bar"])
    in_effect = [s for s in settings if s["from_bar"] <= bar][-1]
    out = [dict(s) for s in settings if s["from_bar"] < bar]
    out.append({**in_effect, **partial, "from_bar": bar})
    old_prev = in_effect
    same = lambda a, b: {k: v for k, v in a.items() if k != "from_bar"} == {k: v for k, v in b.items() if k != "from_bar"}  # noqa: E731
    for s in settings:
        if s["from_bar"] <= bar:
            continue
        entry = dict(s)
        for k, v in partial.items():
            if s.get(k) == old_prev.get(k):
                entry[k] = v
        old_prev = s
        if same(entry, out[-1]):
            continue
        out.append(entry)
    return out


def _only(body: dict, allowed) -> None:
    extra = sorted(set(body) - set(allowed))
    if extra:
        raise RunError(f"{extra[0]} is not a known field; expected some of {', '.join(sorted(allowed))}", 400, extra[0])


def _check_int(value, field: str, lo, hi) -> None:
    if not _is_int(value) or (lo is not None and value < lo) or (hi is not None and value > hi):
        span = f" {lo}..{hi}" if hi is not None else f" >= {lo}"
        raise RunError(f"{field} must be an integer{span} (got {value!r})", 400, field)


def _check_num(value, field: str, lo, hi) -> None:
    if not _is_num(value) or value < lo or value > hi:
        raise RunError(f"{field} must be a number {lo}..{hi} (got {value!r})", 400, field)
