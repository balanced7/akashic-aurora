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
# agent_id -> hints the full ring evicted since last take_dropped() (RB-5/RB-6, T029:
# a bounded read must SAY what it dropped -- the deque evicts silently on its own)
_dropped: Dict[str, int] = {}


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

    # RB-1 (T029): hints render under a "treat as authoritative" header, so the fold door
    # accepts them only from a sender whose trust grant can send kind="hint" (unknown /
    # quarantined / expired ids fail closed via resolve()). `from_agent` mirrors the
    # bus-stamped frm; meta contents are never consulted. A broken trust door also drops:
    # losing an advisory hint is cheap, folding forged authoritative context is not.
    try:
        from core.trust.registry import resolve
        if not resolve(str(from_agent)).can_send_kind("hint"):
            return False
    except Exception:
        return False

    buf = _hints.setdefault(str(agent), deque(maxlen=HINT_MAX_PER_AGENT))
    if len(buf) == HINT_MAX_PER_AGENT:      # this append evicts the oldest -- count the loss
        _dropped[str(agent)] = _dropped.get(str(agent), 0) + 1
    buf.append((key, value, str(from_agent), time.time()))
    return True


def take_dropped(agent: str) -> int:
    """How many hints the full ring evicted since last asked (RB-5/RB-6, T029). Reading
    RESETS the counter -- one confession per drain, alongside drain(agent)."""
    return _dropped.pop(str(agent), 0)


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


def format_for_prompt(hints: List[Dict[str, Any]], dropped: int = 0) -> str:
    """Render a list of hint dicts (from drain()) as a compact block for system-prompt or
    user-prompt injection. `dropped` (from take_dropped()) confesses ring overflow: the
    block reports the loss instead of narrowing silently (RB-5/RB-6, T029).

    Returns an empty string if there is nothing to say, so callers can safely inline:
        block = format_for_prompt(drain(agent_id), dropped=take_dropped(agent_id))
        prompt = block + "\\n" + prompt if block else prompt"""

    if not hints and not dropped:
        return ""

    lines = [HINT_BLOCK_HEADER]
    for h in hints:
        k = h.get("key", "?")
        v = h.get("value", "?")
        frm = h.get("from", "?")
        lines.append(f"- [{k}] from {frm}: {v}")
    if dropped:
        lines.append(f"- (! {dropped} older hint(s) dropped -- ring full at "
                     f"{HINT_MAX_PER_AGENT}; peers should batch or slow down)")

    return "\n".join(lines)


def pending_count(agent: str) -> int:
    """How many hints are queued for `agent` (for UI/roster introspection)."""
    buf = _hints.get(str(agent))
    return len(buf) if buf else 0


def clear_all():
    """Drop all hints for all agents (e.g. on runner restart / reset)."""
    _hints.clear()
    _dropped.clear()
