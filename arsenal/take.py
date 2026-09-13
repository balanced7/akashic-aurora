"""The take ledger: every run leaves an append-only record that loads back (contract §4.3).

A take is a directory holding take.json (the graph, plan and meta, plus closing state) and
events.jsonl, which is append-only. Epochs only move forward: a new epoch arrives as an epoch
event carrying exactly latest + 1. Anything from an older epoch is refused, and nothing from a
refused batch is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .timebase import StaleEpoch, TimeRef

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "takes"
_TAKE_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{8}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class TakeLedger:
    def __init__(self, root=None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ helpers
    def _dir(self, take_id: str) -> Path:
        if not isinstance(take_id, str) or not _TAKE_ID_RE.match(take_id):
            raise ValueError(f"not a take id: {take_id!r}")
        path = self.root / take_id
        if not path.is_dir():
            raise KeyError(take_id)
        return path

    def _read(self, take_id: str) -> dict:
        return json.loads((self._dir(take_id) / "take.json").read_text(encoding="utf-8"))

    def _write(self, take_id: str, take: dict) -> None:
        path = self._dir(take_id) / "take.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(take, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(path)

    # ---------------------------------------------------------------------- API
    def open(self, graph_json: dict, plan: dict, meta: dict) -> str:
        blob = json.dumps({"graph": graph_json, "meta": meta}, sort_keys=True, default=str).encode("utf-8")
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            while True:
                nonce = f"{time.time_ns()}-{os.getpid()}".encode("ascii")
                take_id = time.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha256(blob + nonce).hexdigest()[:8]
                path = self.root / take_id
                try:
                    path.mkdir()
                    break
                except FileExistsError:
                    continue
            (path / "events.jsonl").touch()
            take = {"api": "arsenal.take/v0", "take_id": take_id, "opened_at": _now_iso(),
                    "graph": graph_json, "plan": plan, "meta": meta,
                    "closed": False, "latest_epoch": 0, "event_count": 0}
            self._write(take_id, take)
        return take_id

    def append(self, take_id: str, events: List[dict]) -> int:
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        with self._lock:
            take = self._read(take_id)
            if take.get("closed"):
                raise ValueError(f"take {take_id} is closed")
            latest = int(take.get("latest_epoch", 0))
            lines: List[str] = []
            for i, event in enumerate(events):
                if not isinstance(event, dict) or "kind" not in event or "t" not in event:
                    raise ValueError(f"event {i} needs a kind and a t")
                ref = TimeRef.from_json(event["t"])
                if event["kind"] == "epoch":
                    declared = event.get("epoch", ref.epoch)
                    if declared != latest + 1 or ref.epoch != latest + 1:
                        raise StaleEpoch(f"event {i}: an epoch event must carry epoch {latest + 1}, "
                                         f"got {declared} (t.epoch {ref.epoch})")
                    latest += 1
                elif ref.epoch < latest:
                    raise StaleEpoch(f"event {i} ({event['kind']}) is from epoch {ref.epoch}; the take is at {latest}")
                elif ref.epoch > latest:
                    raise ValueError(f"event {i} ({event['kind']}) is from epoch {ref.epoch} before any "
                                     f"epoch event announced it; the take is at {latest}")
                lines.append(json.dumps(event, sort_keys=True, default=str))
            if lines:
                with open(self._dir(take_id) / "events.jsonl", "a", encoding="utf-8") as fh:
                    fh.write("\n".join(lines) + "\n")
                take["latest_epoch"] = latest
                take["event_count"] = int(take.get("event_count", 0)) + len(lines)
                self._write(take_id, take)
            return len(lines)

    def close(self, take_id: str, summary: dict) -> None:
        with self._lock:
            take = self._read(take_id)
            if take.get("closed"):
                raise ValueError(f"take {take_id} is already closed")
            take.update({"closed": True, "closed_at": _now_iso(), "summary": summary})
            self._write(take_id, take)

    def load(self, take_id: str) -> dict:
        with self._lock:
            take = self._read(take_id)
            raw = (self._dir(take_id) / "events.jsonl").read_text(encoding="utf-8")
        return {"take": take, "events": [json.loads(line) for line in raw.splitlines() if line.strip()]}

    def list(self) -> List[Dict]:
        if not self.root.is_dir():
            return []
        out = []
        for path in sorted(self.root.iterdir(), reverse=True):
            if not (path.is_dir() and _TAKE_ID_RE.match(path.name)):
                continue
            try:
                take = json.loads((path / "take.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            meta = take.get("meta") or {}
            out.append({"take_id": take.get("take_id", path.name), "opened_at": take.get("opened_at"),
                        "closed": bool(take.get("closed")), "event_count": take.get("event_count", 0),
                        "clip": meta.get("clip_name") or meta.get("clip_id")})
        return out
