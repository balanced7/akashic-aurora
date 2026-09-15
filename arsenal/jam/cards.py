"""The deck: cards as files under state/arsenal/jam/deck (jam-spec 4.1, 5.1; DATA 2.10 and 3).

  deck/deck.json                  {"api": "arsenal.jam.deck/v0", "rev": N, "order": [id, ...]}
  deck/cards/<id>.json            one stored card (schemas.validate_card(stored=True))
  deck/trash/<id>.rev<N>.<utc>.json   deleted cards: delete moves them here, restore moves the newest back
  seed/moments-v1.json            git-ignored moment links, merged into the seed by id (section 12)

DeckStore(root, reader) is the one writer while the server runs. Every JSON file is written to <name>.tmp and then
replaced, as PerformanceStore does; deck.json's rev goes up with every card write and every order write. Nothing is
hard-deleted. `reader(card) -> page_reads` voices the card through the bridge (resolve.Resolver.page_reads); it raises
resolve.ResolveError (400, naming the field) or resolve.BridgeUnavailable (503), which the routes pass on.

Card ids: seeds and Claude's cards are slugs; page saves are t-YYYYMMDD-HHMMSS-xxxx; kept copies k-<source id>-xxxx
(truncated to 48). Every error is a DeckError carrying its HTTP status and extra body fields (409 carries the rev).
"""
from __future__ import annotations

import copy
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from arsenal import nashville
from arsenal.jam import CARD_API, DECK_API
from arsenal.jam import schemas as S

PACKAGE = Path(__file__).resolve().parent
DEFAULT_ROOT = PACKAGE.parents[1] / "state" / "arsenal" / "jam"
SEED_FILE = PACKAGE / "seed" / "deck-v1.json"
MOMENTS_FILE = Path("seed") / "moments-v1.json"
TEMPLATE_MAX_NOTES = 16
PC_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

# Plain default lines for cards Daniel keeps (DATA 2.10 gives none; tests/fixtures/jam/card_kept_template.json).
CAPTURE_TEXT = {"meaning": "The chord you were holding when you pressed Keep.",
                "explanation": "These are the notes you held, kept as you played them.",
                "why": "It is your own voicing, so you can hear it again and build on it.",
                "try": "Play it, then change one note at a time and listen to what moves."}
MOMENT_TEXT = {"meaning": "A chord from your practice log, kept as it sounded.",
               "explanation": "These are the notes that sounded through that moment of your playing.",
               "why": "It is your own voicing, so you can hear it again and build on it.",
               "try": "Play it, then change one note at a time and listen to what moves."}


class DeckError(Exception):
    """A refused deck request: status is the HTTP status, field the offending field (400), extra more body fields."""

    def __init__(self, message: str, status: int = 400, field: Optional[str] = None, **extra):
        super().__init__(message)
        self.status = status
        self.field = field
        self.extra = extra


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def clock_text(ms: float) -> str:
    s = max(0, int(ms)) // 1000
    return f"{s // 60}:{s % 60:02d}"


def _schema(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except S.JamSchemaError as exc:
        raise DeckError(str(exc), 400, exc.field) from None


def merge_patch(target, patch):
    """RFC 7386: objects merge, null removes, anything else replaces."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = dict(target) if isinstance(target, dict) else {}
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = merge_patch(out.get(k), v)
    return out


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40].strip("-")
    return slug or "card"


def kept_id(source_id: str) -> str:
    return f"k-{source_id[:41].rstrip('-')}-{secrets.token_hex(2)}"


def template_id(now: Optional[float] = None) -> str:
    return f"t-{time.strftime('%Y%m%d-%H%M%S', time.localtime(now))}-{secrets.token_hex(2)}"


def numbers_text(items) -> str:
    out = []
    for it in items or []:
        if "key" in it:
            out.append(f"[{it['key']}]")
        elif "rest" in it:
            continue
        else:
            out.append(it.get("n") or "notes")
    return " ".join(out)


class DeckStore:
    def __init__(self, root=None, reader: Optional[Callable[[dict], List[dict]]] = None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self.reader = reader
        self._lock = threading.RLock()

    # ------------------------------------------------------------------------------------------ files
    @property
    def cards_dir(self) -> Path:
        return self.root / "deck" / "cards"

    @property
    def trash_dir(self) -> Path:
        return self.root / "deck" / "trash"

    @staticmethod
    def _write_json(path: Path, obj) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)

    def _path(self, card_id) -> Path:
        if not isinstance(card_id, str) or not S.ID_RE.match(card_id):
            raise DeckError(f"no card {card_id}", 404)
        return self.cards_dir / f"{card_id}.json"

    def deck(self) -> dict:
        path = self.root / "deck" / "deck.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            return {"api": DECK_API, "rev": int(doc.get("rev", 0)), "order": list(doc.get("order") or [])}
        except (OSError, ValueError):
            return {"api": DECK_API, "rev": 0, "order": []}

    def _bump(self, order: Optional[List[str]] = None) -> int:
        doc = self.deck()
        doc["rev"] += 1
        if order is not None:
            doc["order"] = order
        self._write_json(self.root / "deck" / "deck.json", doc)
        return doc["rev"]

    # ------------------------------------------------------------------------------------------ reads
    def get(self, card_id: str) -> dict:
        path = self._path(card_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise DeckError(f"no card {card_id}", 404) from None

    def exists(self, card_id: str) -> bool:
        try:
            return self._path(card_id).is_file()
        except DeckError:
            return False

    def all(self) -> List[dict]:
        if not self.cards_dir.is_dir():
            return []
        cards = []
        for path in self.cards_dir.glob("*.json"):
            try:
                cards.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        order = {cid: i for i, cid in enumerate(self.deck()["order"])}
        cards.sort(key=lambda c: (order.get(c.get("id"), len(order)), c.get("created_at") or "", c.get("id") or ""))
        return cards

    def find(self, ref: str) -> str:
        """A card id or a unique id prefix -> the id (404 none, 400 ambiguous)."""
        if isinstance(ref, str) and self.exists(ref):
            return ref
        ids = [c["id"] for c in self.all() if isinstance(ref, str) and ref and c.get("id", "").startswith(ref)]
        if len(ids) == 1:
            return ids[0]
        if ids:
            raise DeckError(f"{ref!r} matches {len(ids)} cards: {', '.join(ids[:8])}", 400, "card")
        raise DeckError(f"no card {ref}", 404)

    def list(self, group=None, kind=None, tag=None, by=None, archived: bool = False) -> List[dict]:
        out = []
        for c in self.all():
            if group and c.get("group") != group or kind and c.get("kind") != kind:
                continue
            if tag and tag not in (c.get("tags") or []) or by and c.get("created_by") != by:
                continue
            if c.get("archived") and not archived:
                continue
            out.append(c)
        return out

    @staticmethod
    def summary(card: dict, runs: int = 0) -> dict:
        return {"id": card["id"], "rev": card["rev"], "title": card["title"], "meaning": card.get("meaning"),
                "group": card.get("group"), "kind": card.get("kind"), "key": card.get("key"),
                "numbers": numbers_text(card.get("chords")), "variants": [v["id"] for v in card.get("variants") or []],
                "tags": card.get("tags") or [], "created_by": card.get("created_by"),
                "updated_at": card.get("updated_at"), "favorite": bool(card.get("favorite")),
                "archived": bool(card.get("archived")), "runs": runs}

    def doc(self, runs_by_card: Optional[Dict[str, int]] = None, **filters) -> dict:
        deck = self.deck()
        runs_by_card = runs_by_card or {}
        return {"api": DECK_API, "rev": deck["rev"], "order": deck["order"],
                "cards": [self.summary(c, runs_by_card.get(c["id"], 0)) for c in self.list(**filters)]}

    def trash(self) -> List[dict]:
        out = []
        if self.trash_dir.is_dir():
            for path in sorted(self.trash_dir.glob("*.json")):
                m = re.fullmatch(r"(.+)\.rev(\d+)\.(\d{8}T\d{9}Z)\.json", path.name)
                if not m:
                    continue
                try:
                    title = json.loads(path.read_text(encoding="utf-8")).get("title")
                except (OSError, ValueError):
                    title = None
                out.append({"id": m.group(1), "rev": int(m.group(2)), "trashed_at": m.group(3),
                            "file": f"trash/{path.name}", "title": title})
        out.sort(key=lambda t: (t["trashed_at"], t["id"]), reverse=True)
        return out

    # ------------------------------------------------------------------------------------------ writes
    def _finish(self, card: dict) -> List[str]:
        """Validate a card about to be stored, read its chords through the bridge, and return warnings."""
        _schema(S.validate_card, card)
        if self.reader is not None:
            card["page_reads"] = self.reader(card)
        _schema(S.validate_card, card, stored=True)
        warnings = [f"{path} uses the word {word!r}" for path, word in S.wording_problems(card)]
        for pr in card.get("page_reads") or []:
            if pr["match"] not in ("exact", "enharmonic", "notes"):
                line = f"variant {pr['variant']} " if pr.get("variant") else ""
                warnings.append(f"{line}slot {pr['slot'] + 1}: the page reads these notes as "
                                f"{pr.get('name') or 'a cluster'} ({pr['match']})")
        return warnings

    def create(self, card: dict, by: str = "claude", source: Optional[dict] = None) -> dict:
        if not isinstance(card, dict):
            raise DeckError("card must be a JSON object", 400, "card")
        if by not in S.AUTHORS:
            raise DeckError(f"by must be claude or daniel (got {by!r})", 400, "by")
        c = copy.deepcopy(card)
        for key in ("rev", "page_reads", "source", "created_at", "updated_at", "updated_by"):
            c.pop(key, None)  # server fields: whatever a client sent, the server writes them
        c.setdefault("api", CARD_API)
        c.setdefault("created_by", by)
        with self._lock:
            if not c.get("id"):
                base = slugify(c.get("title", ""))
                cid, n = base, 1
                while self.exists(cid):
                    n += 1
                    cid = f"{base}-{n}"
                c["id"] = cid
            now = now_iso()
            c.update(rev=1, created_at=now, updated_at=now, updated_by=by,
                     source=source or ({"kind": "claude"} if by == "claude" else {"kind": "edit"}))
            if self.exists(c.get("id")):
                raise DeckError(f"card {c['id']} exists", 409, rev=self.get(c["id"])["rev"])
            warnings = self._finish(c)
            self._write_json(self._path(c["id"]), c)
            order = [x for x in self.deck()["order"] if x != c["id"]] + [c["id"]]
            deck_rev = self._bump(order)
        return {"id": c["id"], "rev": 1, "card": c, "warnings": warnings, "deck_rev": deck_rev}

    def update(self, card_id: str, patch, if_rev, by: str = "claude") -> dict:
        if not isinstance(patch, dict):
            raise DeckError("patch must be a JSON object (a merge patch)", 400, "patch")
        for key in S.CARD_UNPATCHABLE:
            if key in patch:
                raise DeckError(f"patch.{key} cannot be patched", 400, f"patch.{key}")
        if isinstance(if_rev, bool) or not isinstance(if_rev, int):
            raise DeckError("if_rev is required: the rev the change was made against", 400, "if_rev")
        with self._lock:
            old = self.get(card_id)
            if old["rev"] != if_rev:
                raise DeckError(f"rev changed: card {card_id} is at rev {old['rev']}", 409, rev=old["rev"])
            c = merge_patch(old, patch)
            c.update(rev=old["rev"] + 1, updated_at=now_iso(), updated_by=by)
            if (old.get("source") or {}).get("kind") == "seed":
                c["source"] = {"kind": "edit", "from_seed_version": old["source"].get("seed_version", 1)}
            warnings = self._finish(c)
            self._write_json(self._path(card_id), c)
            deck_rev = self._bump()
        return {"id": card_id, "rev": c["rev"], "card": c, "warnings": warnings, "deck_rev": deck_rev}

    def delete(self, card_id: str, if_rev, by: str = "claude") -> dict:
        if isinstance(if_rev, bool) or not isinstance(if_rev, int):
            raise DeckError("if_rev is required: the rev the delete was made against", 400, "if_rev")
        with self._lock:
            old = self.get(card_id)
            if old["rev"] != if_rev:
                raise DeckError(f"rev changed: card {card_id} is at rev {old['rev']}", 409, rev=old["rev"])
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")[:-3] + "Z"
            target = self.trash_dir / f"{card_id}.rev{old['rev']}.{stamp}.json"
            self.trash_dir.mkdir(parents=True, exist_ok=True)
            self._path(card_id).replace(target)
            deck_rev = self._bump([x for x in self.deck()["order"] if x != card_id])
        return {"id": card_id, "trashed": f"trash/{target.name}", "rev": old["rev"], "deck_rev": deck_rev, "by": by}

    def restore(self, card_id: str, by: str = "claude") -> dict:
        with self._lock:
            entries = [t for t in self.trash() if t["id"] == card_id]
            if not entries:
                raise DeckError(f"no card {card_id} in the trash", 404)
            if self.exists(card_id):
                raise DeckError(f"card {card_id} exists; delete it before restoring an older one", 409,
                                rev=self.get(card_id)["rev"])
            path = self.root / "deck" / entries[0]["file"]
            c = json.loads(path.read_text(encoding="utf-8"))
            c.update(rev=c["rev"] + 1, updated_at=now_iso(), updated_by=by)
            warnings = self._finish(c)
            self._write_json(self._path(card_id), c)
            path.unlink()
            deck_rev = self._bump([x for x in self.deck()["order"] if x != card_id] + [card_id])
        return {"id": card_id, "rev": c["rev"], "card": c, "warnings": warnings, "deck_rev": deck_rev}

    def keep(self, card_id: str, by: str = "daniel", key: Optional[str] = None) -> dict:
        """A copy in Daniel's Kept group, with source {kind: kept, from: {id, rev}}; key moves it (numbers move with
        the key, exact notes shift by the nearest interval)."""
        from arsenal.jam.resolve import key_of, shift_notes, shift_of, ResolveError
        src = self.get(card_id)
        c = copy.deepcopy(src)
        for k in ("pair", "favorite", "archived"):
            c.pop(k, None)
        c["id"] = kept_id(src["id"])
        c["group"] = "kept"
        if key:
            try:
                target = key_of(key)["name"]
                s = shift_of(src["key"], target)
            except ResolveError as exc:
                raise DeckError(str(exc), 400, "key") from None
            c["key"] = target
            lines = [c.get("chords") or []] + [v["chords"] for v in c.get("variants") or []]
            for line in lines:
                for it in line:
                    if isinstance(it, dict) and it.get("notes"):
                        it["notes"] = shift_notes(it["notes"], s)[0]
                        it.pop("name", None)  # the author label names the chord in the old key
            c["also_in"] = [k for k in c.get("also_in") or [] if k != target][:S.MAX_ALSO_IN]
        return self.create(c, by, source={"kind": "kept", "from": {"id": src["id"], "rev": src["rev"]}})

    def order(self, order, if_rev, by: str = "claude") -> dict:
        if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
            raise DeckError("order must be a list of card ids", 400, "order")
        if isinstance(if_rev, bool) or not isinstance(if_rev, int):
            raise DeckError("if_rev is required: the deck rev the order was made against", 400, "if_rev")
        with self._lock:
            deck = self.deck()
            if deck["rev"] != if_rev:
                raise DeckError(f"rev changed: the deck is at rev {deck['rev']}", 409, rev=deck["rev"])
            ids = [c["id"] for c in self.all()]
            for i, cid in enumerate(order):
                if cid not in ids:
                    raise DeckError(f"order[{i}] is {cid!r}, which is not a card in the deck", 400, f"order[{i}]")
            listed = list(dict.fromkeys(order))
            rest = [cid for cid in ids if cid not in listed]
            rev = self._bump(listed + rest)
        return {"rev": rev, "order": listed + rest, "by": by}

    # ------------------------------------------------------------------------------------------ templates
    def template_from_capture(self, capture, by: str = "daniel") -> dict:
        """"Keep what I just played" (DATA 2.10): a chord card from the page's capture."""
        cap = _schema(S._obj, capture, "capture")
        notes = cap.get("notes")
        _schema(S._midi_list, notes, "capture.notes", 1, TEMPLATE_MAX_NOTES)
        for field in ("name", "number", "key", "key_conf", "title", "page_id"):
            if cap.get(field) is not None and not isinstance(cap[field], str):
                raise DeckError(f"capture.{field} must be a string or null", 400, f"capture.{field}")
        notes = sorted(notes)
        name = cap.get("name")
        key, number_from = self._template_key(cap.get("key"), name, notes)
        number = self._template_number(cap.get("number"), name, key, number_from)
        stamp = time.strftime("%H:%M")
        letters = " ".join(dict.fromkeys(PC_FLAT[n % 12] for n in notes))
        title = cap.get("title") or f"{name or letters}, {stamp}"
        card = {"api": CARD_API, "id": template_id(), "title": title[:80], **CAPTURE_TEXT, "group": "kept",
                "kind": "chord", "key": key, "chords": [{"n": number, "beats": 4, "notes": notes}],
                "created_by": "daniel"}
        log = cap.get("log") if isinstance(cap.get("log"), dict) else None
        source = {"kind": "saved-live", "saved_by": by, "page_name": name, "page_number": cap.get("number"),
                  "key_conf": cap.get("key_conf"), "log_session": None, "log_t_ms": None}
        if number_from:
            source["number_from"] = number_from
        session = log.get("session") if log else None
        perf, t0 = cap.get("perf_ms"), (log or {}).get("t0_perf_ms")
        if session and S.SESSION_RE.match(str(session)) and isinstance(perf, (int, float)) and \
                isinstance(t0, (int, float)) and perf >= t0:
            t_ms = int(round(perf - t0))
            source.update(log_session=session, log_t_ms=t_ms)
            card["moments"] = [{"session": session, "at": clock_text(t_ms), "until": None,
                                "label": "saved from the page"}]
        return self.create(card, by, source=source)

    def template_from_moment(self, moment, by: str = "claude") -> dict:
        """template save-from-moment (DATA 2.10): the CLI reads the log and sends {session, at_ms, until_ms, notes,
        name, number, key, title?, id?, beats?}; the voicing is Daniel's, saved by Claude."""
        m = _schema(S._obj, moment, "moment")
        session = m.get("session")
        if not isinstance(session, str) or not S.SESSION_RE.match(session):
            raise DeckError("moment.session must be a practice session id", 400, "moment.session")
        notes = m.get("notes")
        _schema(S._midi_list, notes, "moment.notes", 1, TEMPLATE_MAX_NOTES)
        at_ms, until_ms = m.get("at_ms"), m.get("until_ms")
        if not isinstance(at_ms, (int, float)) or isinstance(at_ms, bool) or at_ms < 0:
            raise DeckError("moment.at_ms must be a time in ms", 400, "moment.at_ms")
        beats = m.get("beats", 4)
        _schema(S._beats, beats, "moment.beats")
        name = m.get("name")
        key, number_from = self._template_key(m.get("key"), name, sorted(notes))
        number = self._template_number(m.get("number"), name, key, number_from)
        at_text = clock_text(at_ms)
        card = {"api": CARD_API, "title": (m.get("title") or f"{name or 'Your chord'}, from {at_text}")[:80],
                **MOMENT_TEXT, "group": "kept", "kind": "chord", "key": key,
                "chords": [{"n": number, "beats": beats, "notes": sorted(notes)}], "created_by": "daniel",
                "moments": [{"session": session, "at": at_text,
                             "until": clock_text(until_ms) if isinstance(until_ms, (int, float)) else None,
                             "label": "saved from your practice log"}]}
        card["id"] = m.get("id") or template_id()
        source = {"kind": "saved-from-moment", "saved_by": by, "page_name": name, "page_number": m.get("number"),
                  "log_session": session, "log_t_ms": int(at_ms)}
        if number_from:
            source["number_from"] = number_from
        return self.create(card, by, source=source)

    @staticmethod
    def _template_key(key, name, notes):
        if key and nashville.parse_key(key):
            return nashville.parse_key(key)["name"], None
        parsed = nashville.parse_chord(name) if name else None
        pc = nashville._pc(parsed["root"]) if parsed and parsed["kind"] == "chord" else notes[0] % 12
        return f"{nashville.MAJOR_KEY_NAMES[pc]} major", "root"

    @staticmethod
    def _template_number(number, name, key, number_from):
        if isinstance(number, str) and S.NUMBER_RE.match(number) and len(number) <= S.NUMBER_MAX and not number_from:
            return number
        if name:
            got = nashville.nashville_from_name(name, key)
            text = got and got.get("kind") == "chord" and got.get("text")
            if text and S.NUMBER_RE.match(text) and len(text) <= S.NUMBER_MAX:
                return text
        return None

    # ------------------------------------------------------------------------------------------ seed
    def moments_file(self) -> Path:
        return self.root / MOMENTS_FILE

    def seed(self, doc: dict, moments: Optional[dict] = None, update: bool = False, dry_run: bool = False,
             by: str = "claude") -> dict:
        """Install the seed deck (7.1): ids not in the deck are installed; with update, seed cards nobody edited
        (source.kind seed and rev 1) are replaced; everything else is kept. Moment links merge in by card id."""
        _schema(S.validate_seed, doc)
        if moments is None and self.moments_file().is_file():
            try:
                moments = json.loads(self.moments_file().read_text(encoding="utf-8"))
            except ValueError as exc:
                raise DeckError(f"{self.moments_file()} is not JSON: {exc}", 400, "moments") from None
        if moments is not None:
            _schema(S.validate_seed_moments, moments)
        links = (moments or {}).get("cards") or {}
        result = {"installed": [], "updated": [], "kept": [], "moments": 0, "dry_run": bool(dry_run)}
        with self._lock:
            for card in doc["cards"]:
                c = copy.deepcopy(card)
                for k in ("rev", "page_reads", "created_at", "updated_at", "updated_by"):
                    c.pop(k, None)
                entry = links.get(c["id"]) or {}
                for k in ("moments", "replay"):
                    if entry.get(k) is not None:
                        c[k] = copy.deepcopy(entry[k])
                if entry:
                    result["moments"] += len(entry.get("moments") or [])
                source = {"kind": "seed", "seed_version": doc["seed_version"]}
                if not self.exists(c["id"]):
                    result["installed"].append(c["id"])
                    if not dry_run:
                        self.create(c, by, source=source)
                    continue
                old = self.get(c["id"])
                if update and (old.get("source") or {}).get("kind") == "seed" and old.get("rev") == 1:
                    result["updated"].append(c["id"])
                    if not dry_run:
                        c.setdefault("api", CARD_API)
                        c.setdefault("created_by", by)
                        c.update(rev=1, created_at=old.get("created_at") or now_iso(), updated_at=now_iso(),
                                 updated_by=by, source=source)
                        self._finish(c)
                        self._write_json(self._path(c["id"]), c)
                        self._bump()
                else:
                    result["kept"].append(c["id"])
        result["deck_rev"] = self.deck()["rev"]
        return result


def load_seed(path: Optional[Path] = None) -> dict:
    path = Path(path) if path else SEED_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DeckError(f"no seed deck at {path} yet (the seed phase writes it)", 404) from None
    except ValueError as exc:
        raise DeckError(f"the seed deck {path} is not JSON: {exc}", 400, "seed") from None
