"""Saved looks for the piano page's Studio drawer: the presets file, and the checks every request to it passes.

The server side (arsenal/serve.py routes these):
  GET /api/piano/looks  -> 200 {"api": "arsenal.piano.looks/v1", "rev": N, "presets": [PRESET]}; rev 0 with no presets
                           until the first save
  PUT /api/piano/looks  {"rev": N, "presets": [PRESET]} -> 200 {"api", "rev": N + 1, "presets"}, the whole list replaced;
                           409 {"error", "rev", "presets"} when N is not the stored rev (another window saved first)
  Both answer 403 unless the Host header names this machine (127.0.0.1, localhost or [::1]) on the server's own port and
  any Origin header is that same http origin. A PUT also answers 415 unless it is application/json, 411 without a
  Content-Length, 413 over 256 KB and 400 for a body these checks refuse.

PRESET = {"id": [A-Za-z0-9_-]{1,64}, "name": 1-60 characters (not blank, no control characters),
          "settings": {name: string (<= 200 characters) | finite number | boolean} (<= 64 entries),
          "favourite": bool (optional), "created": epoch ms (optional), "updated": epoch ms (optional)}
At most 100 presets, ids unique. The page decides which settings a look holds (arsenal/web/piano/looks/registry.js);
the server only keeps the values simple. The starter looks are built into the page and never stored here.

The file is state/arsenal/looks/presets.json (git-ignored). It is written whole to a temp file in the same folder and
moved over the old one with os.replace, so a failed write leaves the previous file as it was.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
from pathlib import Path
from typing import Mapping, Optional, Tuple
from urllib.parse import urlsplit

API = "arsenal.piano.looks/v1"
PATH = "/api/piano/looks"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "looks"
FILE_NAME = "presets.json"
MAX_BODY = 256 * 1024
MAX_PRESETS = 100
MAX_NAME = 60
MAX_SETTINGS = 64
MAX_STRING = 200
LOOPBACK = ("127.0.0.1", "localhost", "::1")
PRESET_KEYS = ("id", "name", "settings", "favourite", "created", "updated")
BODY_KEYS = ("api", "rev", "presets")
_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_SETTING = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LooksError(Exception):
    """A refusal with its HTTP status; extra goes into the JSON reply beside "error"."""

    def __init__(self, status: int, message: str, **extra):
        super().__init__(message)
        self.status = status
        self.extra = extra


# ------------------------------------------------------------------ requests
def request_problem(method: str, headers: Mapping[str, str], port: int) -> Optional[Tuple[int, str]]:
    """(status, message) when a looks request must be refused before its body is looked at, else None."""
    host = (headers.get("Host") or "").strip()
    try:
        parts = urlsplit("//" + host)
        host_name, host_port = parts.hostname, parts.port
        plain = not parts.path and not parts.query and parts.username is None
    except ValueError:
        host_name, host_port, plain = None, None, False
    if not host or not plain or host_name not in LOOPBACK or host_port != port:
        return 403, f"saved looks answer only to this machine's pages on port {port}, not host {host or '(none)'}"
    origin = headers.get("Origin")
    if origin is not None:
        try:
            o = urlsplit(origin.strip())
            same = (o.scheme == "http" and o.hostname == host_name and o.port == port and o.path in ("", "/")
                    and not o.query and o.username is None)
        except ValueError:
            same = False
        if not same:
            return 403, f"saved looks answer only to this page's own origin, not {origin}"
    if method == "PUT":
        kind = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if kind != "application/json":
            return 415, f"saved looks must be sent as application/json, not {kind or 'untyped'}"
    return None


def _refuse_constant(name: str):
    raise ValueError(f"{name} is not a number JSON allows")


def parse_body(raw: bytes) -> Tuple[int, list]:
    """The PUT body as (rev, presets), checked; LooksError(400) for anything else."""
    try:
        body = json.loads(raw.decode("utf-8"), parse_constant=_refuse_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise LooksError(400, f"the body is not JSON: {type(exc).__name__}: {exc}"[:300]) from None
    if not isinstance(body, dict):
        raise LooksError(400, 'the body must be {"rev": N, "presets": [...]}')
    unknown = sorted(set(body) - set(BODY_KEYS))
    if unknown:
        raise LooksError(400, f"the body has fields saved looks do not use: {', '.join(unknown)}")
    if "api" in body and body["api"] != API:
        raise LooksError(400, f"api must be {API}")
    rev = body.get("rev")
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
        raise LooksError(400, "rev must be the whole number the last GET answered")
    return rev, validate_presets(body.get("presets"))


def validate_presets(presets) -> list:
    """A checked copy of a presets list, each preset's keys in PRESET_KEYS order; LooksError(400) naming the problem."""
    if not isinstance(presets, list):
        raise LooksError(400, "presets must be a list")
    if len(presets) > MAX_PRESETS:
        raise LooksError(400, f"at most {MAX_PRESETS} saved looks, not {len(presets)}")
    out, seen = [], set()
    for i, preset in enumerate(presets):
        where = f"look {i + 1}"
        if not isinstance(preset, dict):
            raise LooksError(400, f"{where} must be an object")
        unknown = sorted(set(preset) - set(PRESET_KEYS))
        if unknown:
            raise LooksError(400, f"{where} has fields saved looks do not use: {', '.join(unknown)}")
        pid = preset.get("id")
        if not isinstance(pid, str) or not _ID.fullmatch(pid):
            raise LooksError(400, f"{where} needs an id of 1-64 letters, digits, - or _")
        if pid in seen:
            raise LooksError(400, f"{where} repeats the id {pid}")
        seen.add(pid)
        name = preset.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME or not name.strip() or _CONTROL.search(name):
            raise LooksError(400, f"{where} needs a name of 1-{MAX_NAME} characters")
        settings = preset.get("settings")
        if not isinstance(settings, dict):
            raise LooksError(400, f"{where} needs settings, an object")
        if len(settings) > MAX_SETTINGS:
            raise LooksError(400, f"{where} has more than {MAX_SETTINGS} settings")
        for key, value in settings.items():
            if not _SETTING.fullmatch(key):
                raise LooksError(400, f"{where} has a setting named {key[:60]!r}; names are letters, digits and _")
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                if isinstance(value, float) and not math.isfinite(value):
                    raise LooksError(400, f"{where}: {key} must be a finite number")
                continue
            if isinstance(value, str):
                if len(value) > MAX_STRING:
                    raise LooksError(400, f"{where}: {key} is longer than {MAX_STRING} characters")
                continue
            raise LooksError(400, f"{where}: {key} must be a string, a number or true/false")
        clean = {"id": pid, "name": name, "settings": dict(settings)}
        if "favourite" in preset:
            if not isinstance(preset["favourite"], bool):
                raise LooksError(400, f"{where}: favourite must be true or false")
            clean["favourite"] = preset["favourite"]
        for stamp in ("created", "updated"):
            if stamp in preset:
                value = preset[stamp]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise LooksError(400, f"{where}: {stamp} must be a time in epoch milliseconds")
                clean[stamp] = value
        out.append(clean)
    return out


# ---------------------------------------------------------------------- file
class LooksStore:
    """state/arsenal/looks/presets.json. Nothing is created until the first save; one lock covers read, rev check, write."""

    def __init__(self, root=None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self.root / FILE_NAME

    def read(self) -> dict:
        if not self.path.is_file():
            return {"api": API, "rev": 0, "presets": []}
        try:
            doc = json.loads(self.path.read_text(encoding="utf-8"), parse_constant=_refuse_constant)
            rev = doc["rev"]
            if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
                raise ValueError("rev is not a whole number")
            presets = validate_presets(doc["presets"])
        except (OSError, ValueError, KeyError, TypeError, LooksError) as exc:
            # never overwritten while unreadable: Daniel's looks stay on disk for a person to look at
            raise LooksError(500, f"{self.path} could not be read ({exc}); it was left as it is") from None
        return {"api": API, "rev": rev, "presets": presets}

    def replace(self, rev: int, presets: list) -> dict:
        with self._lock:
            current = self.read()
            if rev != current["rev"]:
                raise LooksError(409, f"the saved looks changed since rev {rev} (now rev {current['rev']}); "
                                      "load them again and reapply the change", rev=current["rev"],
                                 presets=current["presets"])
            doc = {"api": API, "rev": current["rev"] + 1, "presets": presets}
            self._write(doc)
            return doc

    def _write(self, doc: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / f".{FILE_NAME}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=1)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
