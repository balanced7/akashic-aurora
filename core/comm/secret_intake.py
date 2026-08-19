"""Secret intake — credentials travel window -> file, never through a transcript.

Daniil, 1:40am 2026-08-19, verbatim: "can we make some kind of pop up window for
credential capture that I can paste into and you can invoke with a verb?" Both of this
house's standing credential wounds (the PAT, the sk-proj key) entered the world as chat
pastes that a transcript then kept forever. This organ removes the temptation: the easy
path and the safe path become the same path (his own T339 doctrine).

Laws (pins in tests/test_secret_intake_pins.py):
  the target is an ALLOWLIST KEY, never a path — traversal cannot be expressed;
  the value lands byte-exact in its file and NOWHERE else;
  every receipt is transcript-safe — it counts bytes it never shows;
  an empty paste refuses (a blank credential authenticates as garbage; absence at
  least refuses loudly downstream).

The tkinter window lives in agent_cli's verb; this module is the pure, pinned half.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parents[2]


class IntakeError(RuntimeError):
    """Refusal at the vault door — named, loud, value-free."""


#: The vault's vocabulary. A name not in this table is refused BEFORE any path math —
#: path traversal is not blocked here, it is UNREPRESENTABLE here.
TARGETS: Dict[str, str] = {
    "discord_bot.token":         "Discord bot token (Developer Portal -> Bot -> Reset Token)",
    "discord_operator_id":       "Daniil's numeric Discord user id — the R1 allowlist",
    "discord_webhook.url":       "the #aurora global-feed webhook",
    "discord_forum_webhook.url": "the #aurora-rooms forum webhook",
    "discord_channel_vandor.url":   "the #vandor seat-channel webhook (his lane with claude)",
    "discord_channel_heimdall.url": "the #heimdall seat-channel webhook (his lane with deepseek)",
    "discord_channel_navi.url":     "the #navi seat-channel webhook (his lane with kimi)",
    "openai.key":                "OpenAI API key",
    "deepseek.key":              "DeepSeek API key",
    "kimi.key":                  "Kimi/Moonshot API key",
    "gemini.key":                "Gemini API key",
    "cursor.key":                "Cursor API key",
}


def secrets_dir() -> Path:
    return Path(os.getenv("AKASHIC_SECRETS_DIR") or (_ROOT / ".secrets"))


def save_secret(target: str, value: str) -> Dict[str, Any]:
    """Write one credential to its allowlisted file. Returns a transcript-safe receipt."""
    if target not in TARGETS:
        raise IntakeError(
            f"unknown target {target!r} — the vault takes an allowlisted NAME, never a "
            f"path. Known: {', '.join(sorted(TARGETS))}")
    cleaned = str(value or "").strip()
    if not cleaned:
        raise IntakeError(
            f"empty paste for {target!r} — refusing; a blank credential file "
            f"authenticates as garbage, absence at least refuses loudly")
    if "\n" in cleaned or "\r" in cleaned:
        raise IntakeError(
            f"{target!r} expects a single line and the paste holds several — "
            f"probably a copy that grabbed extra; try again")
    d = secrets_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / target
    path.write_text(cleaned, encoding="utf-8")
    return {"target": target, "bytes": len(cleaned.encode("utf-8")), "path": str(path)}


def inventory() -> Dict[str, Any]:
    """What the vault holds — sizes only, never a byte of content."""
    d = secrets_dir()
    out: Dict[str, Any] = {}
    for name, desc in sorted(TARGETS.items()):
        p = d / name
        out[name] = {"desc": desc,
                     "present": p.exists() and p.stat().st_size > 0,
                     "bytes": (p.stat().st_size if p.exists() else 0)}
    return out
