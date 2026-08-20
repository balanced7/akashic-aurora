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


# Lines that mean the seat never drew breath. The CLI prints its auth failure to
# STDOUT and exits 1 -- so neither stream alone nor the code alone is the witness;
# we read both and let either convict (T365, from the day his !spawn sprouted a
# corpse). Markers are lowercase substrings, matched against a stripped line.
SPAWN_FATAL_MARKERS = (
    "failed to authenticate",
    "oauth session expired",
    "invalid api key",
    "credit balance is too low",
    "please run /login",
    "is not recognized as",          # Windows: the exe went missing under us
    "command not found",
)


def spawn_stillborn_reason(exit_code: Optional[int], log_text: str,
                           max_len: int = 300) -> Optional[str]:
    """Did the spawned seat LIVE? None means yes; a string is the reason it did not.

    `exit_code` is None while the child is still breathing after its grace window --
    the honest 🌱 case, and the only case that earns a sprout. A corpse gets its
    cause of death named in ONE line, because the reader is Daniil on a phone and a
    receipt that says only "spawn failed" is the same silence with punctuation.

    The false-alarm floor is deliberate: a clean fast exit with an ordinary log is a
    finished run, not a death. A gate with a false-positive rate is a gate nobody
    reads (sample_a_new_gate_for_its_false_positive_rate_before_trusting_it)."""
    if exit_code is None:
        return None                    # still running: the sprout is true, so far
    lines = [ln.strip() for ln in str(log_text or "").splitlines() if ln.strip()]
    fatal = next((ln for ln in lines
                  if any(m in ln.lower() for m in SPAWN_FATAL_MARKERS)), None)
    if exit_code == 0 and fatal is None:
        return None                    # it ran, it finished, it said nothing alarming
    detail = fatal or (lines[-1] if lines else "(no output)")
    reason = " ".join(f"exit {exit_code}: {detail}".split())
    return reason[:max_len]


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


def _mention_map() -> Dict[str, str]:
    """role-name (lowercased) -> agent id, fed by the residents registry — never a
    second hand-kept roster. Agent ids map to themselves so @claude works alongside
    @Vandor; a role the registry doesn't know is simply not an address."""
    agents = ("claude", "deepseek", "kimi", "codex")
    out: Dict[str, str] = {a: a for a in agents}
    try:
        from core.fleet import residents as _R
        for a in agents:
            rec = _R.get(a)
            cs = str((rec or {}).get("callsign") or "").strip().lower()
            if cs:
                out[cs] = a
    except Exception:                                                   # noqa: BLE001
        pass                       # registry down -> agent ids still resolve
    return out


#: seat-channel registry: {"mode": forum|text, "channels": {channel_id: agent},
#: "rooms_channel_id": ...} — written by scripts/discord_setup.py under his admin grant.
SEATS_FILE = _ROOT / "state" / "coord" / "discord_seat_channels.json"


def _seat_channels() -> Dict[str, Any]:
    path = Path(os.getenv("AKASHIC_DISCORD_SEATS_REGISTRY") or SEATS_FILE)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mode": "forum", "channels": {}}


def handle_message(cfg: Dict[str, str], *, author_id: str, author_name: str,
                   channel_id: str, content: str,
                   bus: Any, react: Callable[[str], Any],
                   role_mentions: Any = None,
                   spawner: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
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

    # !spawn — the operator's fresh-hands word (his ask, on the way to work
    # 2026-08-19: "a syntax that I can use to invoke a new instance, in case you
    # get wedged or need to start a fresh handoff"). R1 has already gated this
    # path (only his id reaches here); R3 holds because his keyboard could always
    # launch a session. A control word rides NO bus lane — it is not a message,
    # it is a hand on a lever. Receipt 🌱 fires on process START, and that is the
    # whole promise: the sprout is not the harvest.
    if text.lower().startswith("!spawn"):
        if spawner is None:
            raise RuntimeError("!spawn received but no spawner is wired — the "
                               "runner must provide one; refusing beats pretending")
        task = text[len("!spawn"):].strip() or \
            "fresh seat: operator-invoked spawn from Discord (no task given -- " \
            "boot, read the latest handoff, take the watch)"
        pid = spawner(task)
        react("🌱")
        return {"acted": True, "spawned": str(pid), "id": None}

    meta: Dict[str, Any] = {"source": "discord", "operator": True}

    # the seat lane: typing in #vandor IS addressing claude — the channel is the
    # address, no mention required. His words ride directed, which wakes the seat.
    lane_agent = (_seat_channels().get("channels") or {}).get(str(channel_id))
    if lane_agent:
        meta["lane"] = "seat-channel"
        mid = bus.send(lane_agent, "chat", text, meta=meta)
        if mid is None:
            raise RuntimeError(
                f"the bus accepted nothing for the {lane_agent} lane (send "
                f"returned None); no receipt for an undelivered word")
        react("✅")
        return {"acted": True, "id": str(mid), "to": [lane_agent]}
    ask = _rooms_reverse().get(str(channel_id))
    if ask:
        meta["ask_id"] = ask

    # @-mentions are the wake mechanism (Daniil 2026-08-19, after his first heard
    # message summoned nobody): a known role mention becomes a DIRECTED send, and
    # directed mail is already wake-worthy on every existing semantic — runners
    # spring for their inbox, the wake watcher fires for the seat. No broadcast
    # ride-along: one summons, one copy. Unknown roles are not addresses; a
    # message mentioning only those stays ambient like any other.
    mmap = _mention_map()
    targets = []
    for r in (role_mentions or []):
        agent = mmap.get(str(r).strip().lower())
        if agent and agent not in targets:
            targets.append(agent)
    if targets:
        meta["mentioned"] = True
        sent_ids = []
        for agent in targets:
            mid = bus.send(agent, "chat", text, meta=meta)
            if mid is None:
                raise RuntimeError(
                    f"the bus accepted nothing for @{agent} (send returned None — "
                    f"offline or refused); no receipt may be given for an "
                    f"undelivered summons"
                    + (f" ({len(sent_ids)} earlier summons in this message DID "
                       f"deliver — duplicates beat losses on retype)" if sent_ids else ""))
            sent_ids.append(str(mid))
        react("✅")
        return {"acted": True, "id": sent_ids[-1], "ask_id": ask, "to": targets}

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
