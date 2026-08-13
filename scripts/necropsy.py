"""necropsy -- unclean deaths detected, then distilled (W151b, disaster-proofing Slice 1b).

Charter lineage (atom art_20260813 w153-janitor... sibling, the charter reconciliation):
P2 every death detected, P3 every death auto-distills WITH the death-delta -- the dying
session's operative false assumption, recorded so the next loop knows what NOT to
re-believe. Fence assignments: claude builds, Navi reviews (her property), Heimdall
cross-weights the cause analysis.

THE DETECTION LAW (validated live 2026-08-13 before this module existed: the ad-hoc
census found the shader crash AND the reboot-massacre trio on its first run): a session
died UNCLEAN when its transcript exists and is recent, no tombstone was ever written
(clean deaths tombstone at SessionEnd), and nothing about the session is live.

Two halves:
  classify_session() / census()   PURE + pinned; read-only over transcript mtimes,
                                  tombstones, seats, markers. Never writes.
  digest_transcript_text()        the 08-13 hand-salvage digester, now with a contract.
  distill()                       assembles the digest tail and (optionally) runs ONE
                                  grounded ask to draft the recovered save point WITH a
                                  DEATH-DELTA section. Draft-flagged; a human or the
                                  dying seat's successor ratifies by superseding.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional, Tuple

WINDOW_H_DEFAULT = 72.0


def classify_session(*, transcript_mtime: float, tombstoned: bool, seat_exists: bool,
                     marker_age_min: Optional[float], window_h: float = WINDOW_H_DEFAULT,
                     now: Optional[float] = None) -> str:
    """'unclean' | 'clean' | 'live' | 'out-of-window'. Pure.

    Order matters and is honesty-ordered: liveness first (a necropsy on a live
    patient is the wrongness class, not a feature), then the window (beyond it the
    tombstone signal is unreliable -- Redis TTL, tempdir wipes -- so REFUSE rather
    than guess), then the tombstone verdict."""
    now_f = float(now if now is not None else time.time())
    if seat_exists or (marker_age_min is not None and marker_age_min < 30.0):
        return "live"
    if (now_f - transcript_mtime) / 3600.0 > window_h:
        return "out-of-window"
    return "clean" if tombstoned else "unclean"


def census(agent: str = "claude", window_h: float = WINDOW_H_DEFAULT,
           now: Optional[float] = None) -> List[dict]:
    """All unclean deaths in the window, newest first. Read-only; never writes.

    Transcript universe: the eye's corpus (live harness dirs + rescued archive --
    the definition that survived the 08-11 rebuild lesson), minus the archive
    copies themselves (they are preservation, not sessions to autopsy)."""
    from core.comm import wake_seat as ws
    from core.eye.index import default_corpus
    import os
    now_f = float(now if now is not None else time.time())
    out: List[dict] = []
    for p in default_corpus():
        if "recovered" in str(p):
            continue
        sid = p.stem
        if len(sid) < 30:                    # uuid-shaped session ids only
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        verdict = classify_session(
            transcript_mtime=mtime,
            tombstoned=ws.is_tombstoned(sid),
            seat_exists=os.path.exists(ws.seat_path(agent, sid)),
            marker_age_min=ws.activity_age_min(agent, sid),
            window_h=window_h, now=now_f)
        if verdict == "unclean":
            out.append({"sid": sid, "path": str(p), "age_h": round((now_f - mtime) / 3600, 1),
                        "mb": round(p.stat().st_size / 1e6, 2), "root": p.parent.name})
    out.sort(key=lambda d: d["age_h"])
    return out


def digest_transcript_text(text: str, asst_clip: int = 400, user_clip: int = 1500
                           ) -> List[Tuple[str, str, str]]:
    """Transcript JSONL text -> [(timestamp, KIND, content)]. KIND in USER/ASST/TOOL.
    The 08-13 salvage digester, promoted. Never raises; garbage lines skip."""
    def clip(s, n):
        s = " ".join(str(s).split())
        return s if len(s) <= n else s[:n] + "..."
    rows: List[Tuple[str, str, str]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t, ts = e.get("type"), str(e.get("timestamp") or "")[:19]
        content = (e.get("message") or {}).get("content")
        if t == "user":
            if isinstance(content, str):
                rows.append((ts, "USER", clip(content, user_clip)))
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        rows.append((ts, "USER", clip(b.get("text", ""), user_clip)))
        elif t == "assistant":
            for b in (content or []):
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and str(b.get("text", "")).strip():
                    rows.append((ts, "ASST", clip(b["text"], asst_clip)))
                elif b.get("type") == "tool_use":
                    ti = b.get("input") or {}
                    key = (ti.get("command") or ti.get("file_path") or ti.get("url")
                           or ti.get("pattern") or ti.get("prompt") or ti.get("description") or "")
                    rows.append((ts, "TOOL", f"{b.get('name', '?')}: {clip(key, 160)}"))
    return rows


def _write_note(agent: str, title: str, body: str) -> bool:
    """The note-door write, seam-shaped for tests (n8 monkeypatches it). Subprocess
    argv list, never shell -- the prime session's backtick lesson, standing."""
    try:
        import subprocess, sys
        r = subprocess.run([sys.executable, "agent_cli.py", "note", agent,
                            "--title", title, "--category", "save", "--note", body],
                           cwd=str(Path(__file__).resolve().parent.parent),
                           capture_output=True, text=True, timeout=120)
        return r.returncode == 0
    except Exception:
        return False


DEATH_DELTA_PROMPT = (
    "You are performing a NECROPSY on a dead agent session from its final transcript "
    "minutes (below, chronological). Answer DESCRIPTIVELY in four labeled sections:\n"
    "DOING: what the session was working on when it died (2 sentences).\n"
    "LAST-ACT: its final actions, verbatim tool names.\n"
    "DEATH-DELTA: the operative FALSE ASSUMPTION at time of death -- what it believed "
    "that the next loop must NOT re-believe. If the evidence cannot establish one, say "
    "CANNOT-ESTABLISH and why. Never invent.\n"
    "STRANDED: work in flight that a successor could resume, with the evidence line.\n"
)


def distill(sid: str, agent: str = "claude", tail_rows: int = 120,
            run_ask: bool = True) -> dict:
    """Digest the dead session's tail; optionally run ONE grounded ask for the
    death-delta; write the draft save point note. Returns a report dict either way
    (ask failures degrade to a mechanical-only draft -- the necropsy never blocks
    on a model)."""
    from core.eye.index import default_corpus
    cand = [p for p in default_corpus() if p.stem == sid]
    if not cand:
        return {"ok": False, "why": f"no transcript found for sid {sid}"}
    rows = digest_transcript_text(cand[0].read_text(encoding="utf-8", errors="replace"))
    tail = rows[-tail_rows:]
    digest = "\n".join(f"[{ts}] {k}: {c}" for ts, k, c in tail)
    # n9 (calibration finding, maiden run): the 08-12 death's fatal act lived in a
    # SUBAGENT transcript the parent-only read never saw -- an honest abstention
    # where the answer sat one directory over. Fold in each subagent's tail, labeled.
    subdir = cand[0].parent / cand[0].stem / "subagents"
    if subdir.is_dir():
        for sub in sorted(subdir.glob("*.jsonl")):
            srows = digest_transcript_text(sub.read_text(encoding="utf-8", errors="replace"))
            if srows:
                stail = srows[-30:]
                digest += (f"\n--- SUBAGENT {sub.stem} (final {len(stail)} rows) ---\n"
                           + "\n".join(f"[{ts}] {k}: {c}" for ts, k, c in stail))
    delta = ""
    if run_ask:
        try:
            import core.comm.ask as _ask_mod
            out = _ask_mod.ask(DEATH_DELTA_PROMPT + "\n---\n" + digest)
            # ask() returns a BoundaryOutcome, ALWAYS -- detail["answer"] carries the
            # text (its docstring shouts this; the maiden run proved the subscript
            # error live, pinned as n8). Extract honestly; degrade with a label.
            detail = getattr(out, "detail", None) or {}
            delta = str(detail.get("answer") or "").strip()
            if not delta:
                line = getattr(out, "line", None)
                why = line() if callable(line) else str(out)
                delta = f"(death-delta ask returned no answer [{why}] -- mechanical draft only)"
        except Exception as e:
            delta = f"(death-delta ask unavailable: {type(e).__name__} -- mechanical draft only)"
    body = (f"AUTO-NECROPSY DRAFT (W151b) -- session {sid[:8]}, distilled "
            f"{time.strftime('%Y-%m-%d %H:%M')}. Ratify by superseding this note.\n\n"
            f"{delta}\n\n--- FINAL {len(tail)} TRANSCRIPT ROWS (mechanical) ---\n{digest[-6000:]}")
    title = f"save:{agent}:recovered-{sid[:8]}"
    wrote = _write_note(agent, title, body)
    return {"ok": True, "sid": sid, "rows": len(rows), "note": title if wrote else "",
            "note_written": wrote, "delta_head": delta[:200]}
