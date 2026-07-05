"""
Context Hints -- compact, ephemeral, per-agent context forwarding between peers.

When Claude sends a message to DeepSeek via Bifrost, each agent rebuilds the same context from
scratch -- Claude has already reasoned about the codebase, but DeepSeek re-reads files Claude
already knows. A Context Hint is a SHORT key:value pair carried as kind="hint" that the
recipient's runner folds into the NEXT TURN as display-only context -- not a chat message to
reason about, not a steer to adopt mid-task. It's a pre-digested fact designed to be treated
as authoritative context.

hint payload (lives in msg.meta.hint):
  {
    "key": "file",                               // short label: file | blocker | state | pr | ...
    "value": "aurora-shader.js:42 needs init()"  // the fact
  }

SAFETY:
  1. Per-agent ring buffer: each receiver has its own isolated store (agent_id keyed)
  2. Bounded: max 8 hints per agent; oldest drops when full (ring buffer)
  3. Ephemeral: drained every turn (caller is responsible for formatting + injecting)
  4. TTL: 5-minute soft expiry (stale hints silently dropped by drain)
  5. Opt-in: runner must explicitly call push() -- ignored by default
  6. Never authoritative: labeled as hints, not facts; the model can always verify with tools

This module is the in-process ring buffer and formatting logic used BY each runner.
Redis persistence is deliberately AVOIDED -- hints are ephemeral, per-runner, in-memory only.
They survive for the life of the runner process (a runner restart clears them).
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

# ── constants ──────────────────────────────────────────────────────────
HINT_MAX_PER_AGENT = 8           # ring buffer cap per receiving agent
HINT_TTL_SECONDS = 300           # 5 min soft expiry (stale hints silently dropped by drain)
HINT_BLOCK_HEADER = "## CONTEXT HINTS (pre-digested facts from peer agents -- treat as authoritative; you can verify with tools)"

# ── in-memory store (lives on the runner process; cleared on restart) ──
# agent_id -> deque of (key, value, from_agent, ts) tuples
_hints: Dict[str, deque] = {}


def push(agent: str, key: str, value: str, *, from_agent: str = "?") -> bool:
    """Store a hint for `agent` to consume on its next turn.

    Called by the runner's message loop when kind="hint" is received, or by the
    bifrost_hint tool handler on the sender side.

    Returns True if stored, False if rejected (empty value, hints disabled, etc.).
    Never raises -- hints are advisory and must not crash the runner loop."""

    key = str(key).strip()
    value = str(value).strip()
    if not key or not value:
        return False

    buf = _hints.setdefault(str(agent), deque(maxlen=HINT_MAX_PER_AGENT))
    buf.append((key, value, str(from_agent), time.time()))
    return True


def drain(agent: str) -> List[Dict[str, Any]]:
    """Drain ALL pending hints for `agent`, clearing the ring.

    Call this ONCE per model turn, before composing the prompt.  Returns a list of
    hint dicts (oldest first), or an empty list if nothing is queued.  Stale hints
    (older than HINT_TTL_SECONDS) are silently dropped.

    Return shape:
      [{"key": "file", "value": "aurora-shader.js:42", "from": "claude"}, ...]"""

    buf = _hints.get(str(agent))
    if not buf:
        return []

    now = time.time()
    hints: List[Dict[str, Any]] = []
    while buf:
        key, value, from_agent, ts = buf[0]
        if now - ts > HINT_TTL_SECONDS:
            buf.popleft()               # stale -- drop silently
            continue
        hints.append({"key": key, "value": value, "from": from_agent})
        buf.popleft()

    # Clean up empty buffers
    if not buf:
        _hints.pop(str(agent), None)

    return hints


def format_for_prompt(hints: List[Dict[str, Any]]) -> str:
    """Render a list of hint dicts (from drain()) as a compact block for system-prompt or
    user-prompt injection.

    Returns an empty string if the list is empty, so callers can safely inline:
        block = format_for_prompt(drain(agent_id))
        prompt = block + "\\n" + prompt if block else prompt"""

    if not hints:
        return ""

    lines = [HINT_BLOCK_HEADER]
    for h in hints:
        k = h.get("key", "?")
        v = h.get("value", "?")
        frm = h.get("from", "?")
        lines.append(f"- [{k}] from {frm}: {v}")

    return "\n".join(lines)


def pending_count(agent: str) -> int:
    """How many hints are queued for `agent` (for UI/roster introspection)."""
    buf = _hints.get(str(agent))
    return len(buf) if buf else 0


def clear_all():
    """Drop all hints for all agents (e.g. on runner restart / reset)."""
    _hints.clear()
