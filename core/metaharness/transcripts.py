"""Keep raw harness transcripts before they rotate away (meta-harness task 03, step 1).

The raw transcripts hold everything a replay corpus needs -- the request, every tool input and
output -- and they are the one record the harness deletes on its own schedule. The Eye indexes
their text but not the tool calls. So: copy them, redacted, gzipped, into gitignored state.

  source   ~/.claude/projects/*/<session>.jsonl, ~/.codex/sessions/**/*.jsonl
  dest     <state>/metaharness/transcripts/<harness>/<session>.jsonl.gz
  index    <state>/metaharness/transcripts/index.json  (session -> source, sizes, prov pointer)

Every write is redacted line by line, then CHECKED with the stricter pattern set in
redact.find_secrets; a hit deletes the file and records a refusal instead. The archive stops
at a size cap rather than evicting anything -- dropping history is the operator's call.
"""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.metaharness import home
from core.metaharness.redact import find_secrets, redact

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_CAP_MB = 2048


def _root() -> Path:
    p = home() / "transcripts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_sources() -> list[tuple[str, Path]]:
    """(harness, file) for every transcript the known harnesses keep on this machine."""
    home_dir = Path.home()
    out: list[tuple[str, Path]] = []
    out += [("claude-code", p) for p in sorted((home_dir / ".claude" / "projects").glob("*/*.jsonl"))]
    out += [("codex-cli", p) for p in sorted((home_dir / ".codex" / "sessions").glob("**/*.jsonl"))]
    return out


def _load_index() -> dict[str, Any]:
    try:
        return json.loads((_root() / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_index(idx: dict[str, Any]) -> None:
    tmp = _root() / "index.json.tmp"
    tmp.write_text(json.dumps(idx, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, _root() / "index.json")


def archived_bytes(idx: dict[str, Any] | None = None) -> int:
    idx = _load_index() if idx is None else idx
    return sum(int(v.get("bytes") or 0) for v in idx.values() if isinstance(v, dict))


def archive(sources: Iterable[tuple[str, Path]] | None = None, *, cap_mb: int | None = None) -> dict[str, Any]:
    """Archive new or grown transcripts. Idempotent: an unchanged source (same size and mtime)
    is skipped. Returns counts plus the sessions refused by the secret check."""
    cap = int(cap_mb if cap_mb is not None else os.getenv("AKASHIC_TRANSCRIPT_CAP_MB", DEFAULT_CAP_MB)) * 1024 * 1024
    idx = _load_index()
    total = archived_bytes(idx)
    done = skipped = 0
    refused: list[str] = []
    capped = False
    from core.fleet.provenance import pointer

    for harness, src in sources if sources is not None else default_sources():
        try:
            st = src.stat()
        except OSError:
            continue
        sid = src.stem
        prev = idx.get(sid) or {}
        if prev.get("src_size") == st.st_size and prev.get("src_mtime") == int(st.st_mtime):
            skipped += 1
            continue
        if total - int(prev.get("bytes") or 0) + st.st_size > cap:
            capped = True
            break
        dest_dir = _root() / harness
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{sid}.jsonl.gz"
        text = redact(src.read_text(encoding="utf-8", errors="replace"))
        hits = find_secrets(text)
        if hits:
            refused.append(f"{sid} ({', '.join(hits)})")
            dest.unlink(missing_ok=True)
            continue
        with gzip.open(dest, "wt", encoding="utf-8") as f:
            f.write(text)
        size = dest.stat().st_size
        total += size - int(prev.get("bytes") or 0)
        idx[sid] = {
            "harness": harness,
            "src": str(src),
            "src_size": st.st_size,
            "src_mtime": int(st.st_mtime),
            "path": str(dest.relative_to(_root())),
            "bytes": size,
            "prov": pointer(sid),
        }
        done += 1
    _save_index(idx)
    return {"archived": done, "unchanged": skipped, "refused": refused, "capped": capped, "bytes": total, "cap": cap}


def read(session_id: str) -> list[dict[str, Any]]:
    """The archived transcript as a list of JSON entries ([] if not archived)."""
    meta = _load_index().get(session_id)
    if not meta:
        return []
    out: list[dict[str, Any]] = []
    with gzip.open(_root() / meta["path"], "rt", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def sessions() -> dict[str, Any]:
    return _load_index()
