"""followup — the question-back channel for fire-and-forget charters (W46).

Born from kimi's tools hunt (#2, research/reviewed/kimi-tools-hunt-tonight-2026-07-21.md):
a charter seat closes a verdict with an open ask and the only channel back was relaunching
the whole round. One verb now writes BOTH halves at once:

  1. the verdict file's `## Open Questions` block gains `- Q# (date, by -> to) OPEN: ask`
     (the block is created if absent; q-ids mint collision-free against Q-ids anywhere in
     the file, so a body that cites "the Q7 consensus" pushes the next question to Q8);
  2. the W33 defer queue (core/coord/defer_queue.py) gains an item whose cmd points back
     at file + q-id + ask — the responsible seat's next boot surfaces it, and the
     discharge receipt points at the answered block.

ALTITUDE (why toolbelt, stated honestly): the NATURAL altitude is core/coord/ beside
defer_queue — this verb couples two coordination artifacts (the cross-seat verdict-file
convention + the W33 queue). But the builder allowlist (Daniel's morning ruling
2026-07-21, security/acl.json kimi record _tool_author_activation) scopes kimi's core
writes to core/toolbelt/**; core/coord/ holds the ledger-critical organs and stays
fence territory. So the module lives here and RIDES coord across an import — reads
across the boundary are free, only writes are gated. If a future ruling opens coord,
this module is a one-line move; the verb surface and pins do not change.

Laws carried from the house contracts:
  FILE-HALF-FIRST — the file write precedes the queue add, so a refusal can never leave
    a defer pointer at a question that was never written.
  ATOMIC WRITES (K0) — the verdict file is replaced via tmp+os.replace, same directory,
    same volume; a torn verdict is unrepresentable. The queue's own atomicity is dq's.
  IDEMPOTENT REPLAY (RB-26) — the same (by, to, ask) re-filed reuses the existing q-id
    and pending defer item instead of doubling either; a crash between the halves
    self-heals (line present, queue missing -> only the queue half re-files).
  DOOR HYGIENE — the verdict path must resolve INSIDE the repo root (ROOT is
    monkeypatchable for tests, the dq.QUEUE_PATH pattern); the verb appends to an
    EXISTING verdict, it never mints one.

Honest residual: if the file half is later REVERTED by hand while its defer item stays
pending, a re-file mints a fresh q-id and the stale item discharges against a missing
question — the discharger sees it and re-files. Named, not hidden.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from core.coord import defer_queue as _dq

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Monkeypatchable write-door boundary (tests sandbox it; production is the repo root).
ROOT = _ROOT

BLOCK_HEADER = "## Open Questions"
_QID_RE = re.compile(r"\bQ(\d+)\b")


def _resolve(path: str, root: str) -> str:
    """Repo-relative or absolute in; realpath out. Refuses outside the root and any
    path that is not an existing file — followup appends, it never mints."""
    if not str(path or "").strip():
        raise ValueError("followup needs --on <verdict-file> (the verdict to question)")
    p = path if os.path.isabs(path) else os.path.join(root, path)
    p = os.path.realpath(p)
    root_r = os.path.realpath(root)
    try:
        inside = os.path.commonpath([p, root_r]) == root_r
    except ValueError:  # different drives (Windows) -- outside by definition
        inside = False
    if not inside:
        raise ValueError(f"verdict file must live inside the repo root -- got {p}")
    if not os.path.isfile(p):
        raise FileNotFoundError(
            f"no verdict file at {path!r} -- followup appends to an EXISTING verdict; "
            f"it never mints one")
    return p


def _rel(p: str, root: str) -> str:
    return os.path.relpath(p, os.path.realpath(root)).replace(os.sep, "/")


def _next_qid(text: str) -> str:
    nums = [int(n) for n in _QID_RE.findall(text)]
    return "Q%d" % (max(nums) + 1 if nums else 1)


def _atomic_write(path: str, text: str) -> None:
    """tmp + os.replace in the same directory (K0: a torn write is unrepresentable)."""
    tmp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _find_block(lines) -> Optional[Tuple[int, int]]:
    """(heading index, end index) of the Open Questions section; end = next '## '
    heading or EOF. None when the file has no block."""
    head = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("## open questions"):
            head = i
            break
    if head is None:
        return None
    end = len(lines)
    for j in range(head + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return head, end


def _existing_qid(lines, head: int, end: int, by: str, to: str, ask: str) -> Optional[str]:
    """The q-id of an identical OPEN line already in the block (replay detection)."""
    pat = re.compile(r"^- (Q\d+) \([^)]*" + re.escape(by) + r" -> " + re.escape(to) +
                     r"[^)]*\) OPEN: " + re.escape(ask) + r"\s*$")
    for ln in lines[head + 1:end]:
        m = pat.match(ln)
        if m:
            return m.group(1)
    return None


def _append_question(p: str, line: str) -> bool:
    """Insert the question line at the end of the block (creating the block at EOF
    when absent). Returns True when the block was created."""
    with open(p, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    found = _find_block(lines)
    if found is None:
        sep = "" if (not text or text.endswith("\n")) else "\n"
        gap = "" if text.endswith("\n\n") or not text else "\n"
        _atomic_write(p, text + sep + gap + BLOCK_HEADER + "\n\n" + line + "\n")
        return True
    head, end = found
    ins = end
    while ins > head + 1 and not lines[ins - 1].strip():
        ins -= 1
    insert = ([""] if ins == head + 1 else []) + [line, ""]
    lines = lines[:ins] + insert + lines[ins:]
    _atomic_write(p, "\n".join(lines).rstrip("\n") + "\n")
    return False


def file_followup(path: str, *, by: str, to: str, ask: str,
                  needs: str = "write", root: Optional[str] = None) -> Dict[str, Any]:
    """File one followup: q-id'd question into the verdict file's Open Questions block
    + a defer-queue item the responsible seat's next boot surfaces. FILE-HALF-FIRST so
    a refusal never points at an unwritten question; replay-safe per RB-26."""
    by, to, ask = str(by or "").strip(), str(to or "").strip(), str(ask or "").strip()
    if not ask:
        raise ValueError("followup needs the question itself (--ask \"...\")")
    if not to:
        raise ValueError("followup needs --to <seat> -- a question with no responsible "
                         "seat is a wish; file that instead")
    root = root or ROOT
    p = _resolve(path, root)
    rel = _rel(p, root)

    with open(p, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    found = _find_block(lines)
    reused_qid = (_existing_qid(lines, found[0], found[1], by, to, ask)
                  if found else None)

    if reused_qid:
        qid, created_block, reused_line = reused_qid, False, True
    else:
        qid = _next_qid(text)
        line = f"- {qid} ({time.strftime('%Y-%m-%d')}, {by} -> {to}) OPEN: {ask}"
        created_block = _append_question(p, line)
        reused_line = False

    cmd = f"answer {qid} in {rel} (Open Questions): {ask}"
    why = (f"followup for {to}: flip {qid} OPEN -> ANSWERED in the file; the discharge "
           f"receipt points at the answered block")
    reused_defer = None
    for it in _dq.pending():
        if it["by"] == by and cmd in it["cmd"]:
            reused_defer = it["id"]
            break
    if reused_defer:
        defer_id = reused_defer
    else:
        defer_id = _dq.add(by, cmd, needs=needs, why=why)["id"]

    return {"qid": qid, "defer_id": defer_id, "path": rel,
            "created_block": created_block,
            "reused_line": reused_line, "reused_defer": bool(reused_defer)}
