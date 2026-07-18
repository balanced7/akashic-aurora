#!/usr/bin/env python3
"""kimi_walk_narrator -- stream kimi's FULL REASONING from its Claude-Code session transcript
onto the Bifrost bus, live (Daniel directive 2026-07-18: "full reasoning on the bifrost ui so
I can see it at work too").

HOW: Claude Code appends every event -- including THINKING blocks (verified on the 2026-07-18
smoke transcript) -- to the session JSONL under CLAUDE_CONFIG_DIR/projects/**. This tailer
polls that file READ-ONLY from OUTSIDE kimi's session (zero contamination of the blind walk;
kimi never sees the narrator), extracts new assistant entries, and emits think/say lines in
the trace dialect the UI already renders (agent/harness/trace.py -> broadcast kind=trace,
display_only). Tool calls are deliberately NOT emitted here -- claude_trace.py (PreToolUse,
in-session) already streams them; both would double every line.

Invariants: read-only on the transcript; fail-open per entry (bad JSON skipped) and per poll
(errors tolerated, loop continues); bus offline -> lines drop silently (display telemetry is
never load-bearing). Kill: Ctrl-C, or AKASHIC_KIMI_NARRATOR=0. Fence: built at Daniel's tempo;
deepseek's counter invited with the walk-report review bundle.

Run (arm BEFORE the walk; attaches to the first transcript that appears after start):
  py scripts/kimi_walk_narrator.py
Replay a finished transcript (verification / post-hoc rendering):
  py scripts/kimi_walk_narrator.py --replay <path.jsonl>
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from agent.harness.trace import emit   # broadcast kind=trace, display_only -- UI already renders

HOME = Path(os.getenv("KIMI_CLAUDE_HOME", r"E:\AI-Setup\.kimi-claude-home")) / "projects"
CHUNK = 700          # thinking arrives in paragraphs; bus lines stay skimmable
POLL_S = 1.0


def chunks(text, n=CHUNK):
    text = (text or "").strip()
    for i in range(0, len(text), n):
        yield text[i:i + n]


def narrate_entry(entry, agent="kimi") -> int:
    """Emit one transcript entry's thinking/text. Returns lines emitted."""
    if entry.get("type") != "assistant":
        return 0
    sent = 0
    for block in (entry.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "thinking":
            for c in chunks(block.get("thinking")):
                sent += bool(emit("think", c, agent_id=agent))
        elif block.get("type") == "text":
            for c in chunks(block.get("text")):
                sent += bool(emit("say", c, agent_id=agent))
        # tool_use skipped on purpose: claude_trace.py streams those pre-execution
    return sent


def tail(path: Path, agent: str, seen: set, offset: int):
    """Read new COMPLETE lines from byte offset; emit unseen assistant entries.
    Binary mode so offsets are true byte positions (no CRLF translation drift)."""
    sent = 0
    with path.open("rb") as f:
        f.seek(offset)
        data = f.read()
    end = data.rfind(b"\n")
    if end < 0:
        return offset, 0
    for raw in data[:end].split(b"\n"):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            continue
        uid = entry.get("uuid")
        if uid and uid in seen:
            continue
        if uid:
            seen.add(uid)
        sent += narrate_entry(entry, agent)
    return offset + end + 1, sent


def newest_transcript(after_ts: float):
    try:
        cands = [p for p in HOME.rglob("*.jsonl") if p.stat().st_mtime > after_ts]
        return max(cands, key=lambda p: p.stat().st_mtime) if cands else None
    except Exception:
        return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Stream kimi's transcript reasoning to the bus.")
    ap.add_argument("--agent", default="kimi")
    ap.add_argument("--replay", help="narrate one existing transcript fully, then exit")
    args = ap.parse_args()
    if os.getenv("AKASHIC_KIMI_NARRATOR", "1") == "0":
        print("[narrator] disabled by AKASHIC_KIMI_NARRATOR=0")
        return 0

    if args.replay:
        _, sent = tail(Path(args.replay), args.agent, set(), 0)
        print(f"[narrator] replay {args.replay}: {sent} line(s) emitted")
        return 0

    start = time.time()
    print(f"[narrator] armed -- watching {HOME} for a transcript newer than now; Ctrl-C stops")
    path, offset, seen = None, 0, set()
    while True:
        try:
            if path is None:
                path = newest_transcript(start)
                if path is not None:
                    offset = 0
                    print(f"[narrator] attached: {path}")
                    emit("say", "(narrator attached -- kimi's reasoning streams here from this point)",
                         agent_id=args.agent)
            if path is not None:
                offset, sent = tail(path, args.agent, seen, offset)
                if sent:
                    print(f"[narrator] +{sent} line(s)")
        except KeyboardInterrupt:
            print("[narrator] stopped")
            return 0
        except Exception as e:
            print(f"[narrator] tolerated: {type(e).__name__}: {e}")   # telemetry never dies loudly
        time.sleep(POLL_S)


if __name__ == "__main__":
    sys.exit(main())
