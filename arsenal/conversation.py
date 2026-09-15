"""Private question cards and explicitly saved piano answers; performance logs stay read-only."""
from __future__ import annotations

import copy
import json
import math
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from .performance import PerformanceStore
from .pianocue import build_replay_cue, validate_cue

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "state" / "arsenal" / "replay"
API = "arsenal.conversation/v1"


class ConversationStore:
    def __init__(self, root=None, performance=None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self.performance = performance if performance is not None else PerformanceStore()
        self.lock = threading.RLock()

    def _write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def cards(self):
        path = self.root / "conversation.json"
        with self.lock:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"api": API, "cards": []}

    def publish(self, doc):
        from .replay import excerpt
        if not isinstance(doc, dict) or not isinstance(doc.get("cards"), list) or len(doc["cards"]) > 40:
            raise ValueError("provide an object with at most 40 cards")
        clean = copy.deepcopy(doc)
        seen = set()
        for card in clean["cards"]:
            if not isinstance(card, dict) or not re.fullmatch(r"[a-z0-9-]{1,60}", str(card.get("id", ""))):
                raise ValueError("each card needs a short lowercase id")
            if card["id"] in seen:
                raise ValueError("card ids must be unique")
            seen.add(card["id"])
            for field, limit in (("title", 120), ("observation", 1200), ("question", 600), ("prompt", 600), ("group", 80)):
                value = card.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > limit:
                    raise ValueError(f"{card['id']}: {field} needs 1-{limit} characters")
            clips = card.get("clips")
            if not isinstance(clips, list) or not 1 <= len(clips) <= 4:
                raise ValueError("a card needs 1-4 replay clips")
            for clip in clips:
                if not isinstance(clip, dict):
                    raise ValueError("each replay clip must be an object")
                data = excerpt(self.performance, clip.get("session"), str(clip.get("at", "")),
                               float(clip.get("seconds", 8)))
                clip.update(session=data["session"], seconds=data["seconds"])
                if not isinstance(clip.get("label"), str) or not 1 <= len(clip["label"]) <= 160:
                    raise ValueError("each clip needs a short label")
        clean.update(api=API, updated_at=datetime.now(timezone.utc).isoformat())
        with self.lock:
            self._write(self.root / "conversation.json", clean)
        return clean

    def response(self, response_id):
        if not re.fullmatch(r"[0-9a-f]{32}", str(response_id)):
            raise ValueError("invalid response id")
        path = self.root / "responses" / f"{response_id}.json"
        if not path.exists():
            raise ValueError("response not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def responses(self):
        with self.lock:
            paths = sorted((self.root / "responses").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]
            return [{k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k != "replay"} for p in paths]

    def save_response(self, body):
        if not isinstance(body, dict):
            raise ValueError("response must be an object")
        rid = body.get("id")
        if not re.fullmatch(r"[0-9a-f]{32}", str(rid)):
            raise ValueError("response needs a unique id")
        start, end = body.get("start_ms"), body.get("end_ms")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)):
            raise ValueError("response times must be finite milliseconds")
        start, end = round(start), round(end)
        if start < 0 or not 100 <= end - start <= 60000:
            raise ValueError("an answer can span 0.1 to 60 seconds")
        note = body.get("note", "")
        if not isinstance(note, str) or len(note) > 1500:
            raise ValueError("the answer note must be at most 1500 characters")
        identity = {"card_id": body.get("card_id"), "session": body.get("session"), "start_ms": start, "end_ms": end}
        with self.lock:
            path = self.root / "responses" / f"{rid}.json"
            if path.exists():
                existing = self.response(rid)
                if any(existing[k] != v for k, v in identity.items()) or existing["note"] != note:
                    raise ValueError("this response id was already used for a different answer")
                return existing
            card = next((c for c in self.cards()["cards"] if c["id"] == identity["card_id"]), None)
            if card is None:
                raise ValueError("question card not found")
            events = self.performance.events(identity["session"])
            ons = [e for e in events if e["kind"] == "on" and start <= e["t_ms"] < end]
            if not ons:
                raise ValueError("No played notes have reached this answer yet. Play a phrase, then save again.")
            # An in-memory cut boundary lets a note still held at Save ring to the cut. It is never logged as input.
            bounded = [e for e in events if e["t_ms"] <= end] + [{"kind": "replay-cut", "t_ms": end}]
            cue = validate_cue(build_replay_cue(bounded, start, (end - start) / 1000, session=identity["session"]))
            data = {"api": API, "id": rid, **identity, "card_title": card["title"], "question": card["question"],
                    "note": note, "note_count": len(ons), "saved_at": datetime.now(timezone.utc).isoformat(),
                    "replay": {**identity, "seconds": (end - start) / 1000, "speed": 1, "cue": cue}}
            self._write(path, data)
            return data
