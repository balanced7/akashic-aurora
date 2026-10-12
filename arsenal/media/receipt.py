"""arsenal.media.receipt -- the one result shape every primitive returns, and where it is written down.

A result is a dict: api, source {path, id, size, mtime_ns}, params (every default declared), computed_with, the
payload keys, and blind (what this primitive cannot see). write() keeps it as a receipt under
<state>/receipts/<verb>/, the storyboard/motion/floors manifest habit in one place.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Iterable, Optional

from . import API, api
from .ff import state_dir, version_short

_CHUNK = 1 << 20


def quick_id(path) -> str:
    """sha256(size || first 1 MiB || middle 1 MiB || last 1 MiB)[:16]: a content id that costs a few ms on a 2.4 GB
    file and survives a rename or a move between drives. The middle read is there because two recordings can share a
    container header and a trailing run (Heimdall's fence, 2026-10-12); the id is the catalog's join key, so a
    collision would be a wrong join, not a cosmetic clash."""
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha256(str(size).encode("ascii") + b"|")
    with open(p, "rb") as fh:
        h.update(fh.read(_CHUNK))
        if size > 3 * _CHUNK:
            fh.seek(size // 2 - _CHUNK // 2)
            h.update(fh.read(_CHUNK))
        if size > _CHUNK:
            fh.seek(max(size - _CHUNK, _CHUNK))
            h.update(fh.read(_CHUNK))
    return h.hexdigest()[:16]


def source(path, *, with_id: bool = True) -> dict:
    p = Path(path).resolve()
    st = p.stat()
    out = {"path": str(p), "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    if with_id:
        out["id"] = quick_id(p)
    return out


def computed_with(extra: Optional[dict] = None) -> dict:
    out = {"arsenal.media": API, "ffmpeg": version_short(), "python": sys.version.split()[0]}
    if extra:
        out.update(extra)
    return out


def result(verb: str, src, params: dict, payload: dict, blind: Iterable[str] = (), *,
           engine: Optional[dict] = None, write_receipt: bool = True) -> dict:
    """Build the house result dict for one call; src is a path, a list of paths, or an already-built source dict."""
    if isinstance(src, dict) or src is None:
        srcs = src
    elif isinstance(src, (list, tuple)):
        srcs = [source(s) for s in src]
    else:
        srcs = source(src)
    res = {"api": api(verb), "source": srcs, "params": dict(params), "computed_with": computed_with(engine)}
    res.update(payload)
    res["blind"] = list(blind)
    if write_receipt:
        try:
            res["receipt"] = write(verb, res)
        except OSError as exc:              # the primitive's answer stands; the missing receipt is said out loud
            res["receipt"] = None
            res["blind"].append(f"receipt not written: {exc}")
            warnings.warn(f"arsenal.media {verb}: receipt not written ({exc})", stacklevel=2)
    return res


def write(verb: str, res: dict) -> str:
    """Write one result as JSON under <state>/receipts/<verb>/; returns the path. ARSENAL_MEDIA_RECEIPTS=0 turns it
    off (a test that only checks numbers)."""
    if os.environ.get("ARSENAL_MEDIA_RECEIPTS") == "0":
        return ""
    d = state_dir() / "receipts" / verb
    d.mkdir(parents=True, exist_ok=True)
    sid = ""
    s = res.get("source")
    if isinstance(s, dict) and s.get("id"):
        sid = "-" + s["id"]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = d / f"{stamp}-{time.perf_counter_ns() % 1_000_000:06d}{sid}.json"
    body = {k: v for k, v in res.items() if k != "receipt"}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(body, fh, indent=2, default=str)
        fh.write("\n")
    return str(path)
