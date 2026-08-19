"""Discord inbound — Daniil's Discord messages become his voice on the bus. Nothing else does.

Born 2026-08-19, the night he typed into #aurora and asked what happened to his message
(answer: nothing — the house had a voice there and no inbound path). This module is the R1-R3
security model of discord-bridge-design-2026-08-07 made executable, pins in
tests/test_discord_inbound_pins.py:

  R1  the operator allowlist is ONE numeric Discord id. Display names are costume —
      an author named "Daniil" with the wrong id is weather.
  R2  every non-allowlisted message is DATA, never instruction. v1 does not even
      surface it; it returns unacted and the runner moves on.
  R3  reach, never authority. The ear's ONLY write into the house is a bus send AS
      the operator — a Discord message can do exactly what a bifrost-send from his
      keyboard could, from farther away. No task verbs, no grant, no shell. The route
      (which ask a room-message belongs to) comes from the ROOMS REGISTRY, never from
      message content.

This module is PURE and hermetic: no discord.py, no network, no token. The gateway
shell (scripts/bifrost_runner_discord.py) owns the credential and the socket; everything
decidable is decided here where pins can reach it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_ROOT = Path(__file__).resolve().parents[2]

#: The R1 allowlist file — one line, all digits. env override is for pins only.
OPERATOR_ID_FILE = _ROOT / ".secrets" / "discord_operator_id"


class EarConfigError(RuntimeError):
    """Refusal at the gate: inbound must never start on a guessed allowlist."""


def build_config() -> Dict[str, str]:
    """Read the operator id, refusing LOUDLY on absence or malformation.

    An absent allowlist must not resolve to 'allow' (the obvious sin) and must not
    resolve to a quiet death either (the sneaky one) — the refusal names exactly
    what is missing so the operator can fix it in one motion (T176 at a gate)."""
    path = Path(os.getenv("AKASHIC_DISCORD_OPERATOR_ID_FILE") or OPERATOR_ID_FILE)
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise EarConfigError(
            f"no operator id — the R1 allowlist file is missing ({path}). "
            f"Discord: User Settings -> Advanced -> Developer Mode, right-click "
            f"yourself -> Copy User ID, save the number as that file's one line. "
            f"({type(e).__name__})") from e
    if not raw.isdigit() or not (15 <= len(raw) <= 22):
        raise EarConfigError(
            f"operator id file exists but does not hold a single numeric Discord "
            f"snowflake ({path}) — refusing rather than guessing the allowlist.")
    return {"operator_id": raw}


def _rooms_reverse() -> Dict[str, str]:
    """thread_id -> ask_id, from the rooms registry. The registry maps the route;
    message content never does (R3)."""
    from core.comm.discord_rooms import _reg_path
    try:
        reg = json.loads(_reg_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: Dict[str, str] = {}
    for ask_id, rec in reg.items():
        tid = str((rec or {}).get("thread_id") or "")
        if tid:
            out[tid] = str(ask_id)
    return out


def handle_message(cfg: Dict[str, str], *, author_id: str, author_name: str,
                   channel_id: str, content: str,
                   bus: Any, react: Callable[[str], Any]) -> Dict[str, Any]:
    """One inbound message, fully decided. Returns what happened and why.

    Raises nothing it can help; but a BUS failure raises to the caller — the runner
    must know a send died, because a ✅ on a dead send would be the T149 lie with
    an emoji on it. The reaction fires only AFTER the bus accepted."""
    if str(author_id) != cfg["operator_id"]:
        return {"acted": False,
                "reason": f"non-operator author {author_id!r} "
                          f"(name {author_name!r} is costume; R2: data, never "
                          f"instruction)"}

    text = str(content or "").strip()
    if not text:
        return {"acted": False, "reason": "empty message (attachment-only or sticker)"}

    meta: Dict[str, Any] = {"source": "discord", "operator": True}
    ask = _rooms_reverse().get(str(channel_id))
    if ask:
        meta["ask_id"] = ask

    mid = bus.broadcast("chat", text, meta=meta)
    if mid is None:
        # Heimdall's load-bearing find (review 2026-08-19): bus.broadcast returns
        # None WITHOUT RAISING when Redis is down (bus.py:451) or both writes fail
        # (bus.py:566). Reacting ✅ on that None is the exact T149 lie the module
        # docstring promises to prevent — raise so the runner's ⚠️ path fires.
        raise RuntimeError(
            "the bus accepted nothing (broadcast returned None — Redis down or "
            "both writes failed); no receipt may be given for an undelivered word")
    react("✅")
    return {"acted": True, "id": str(mid), "ask_id": ask}
