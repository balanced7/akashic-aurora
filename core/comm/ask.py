"""ask -- a synchronous helper call, with no seat behind it (T171).

Daniil, 2026-08-04: "what if you could quickly invoke with a verb a deepseek instance to help you
with something... this might help reduce your cognitive load if you could quickly ask for help
yourself."

THE EVIDENCE THIS IS NEEDED. Across two multi-seat rounds that night, NINE seat-tasks produced TWO
findings that reached the conductor. The rest died to cursor tail-seeding, dedup collapse, budget
exhaustion returning "", and wedges -- and most of the session went on seat plumbing rather than on
getting help. Asking had become more expensive than doing it myself, so I stopped asking.

ASK IS NOT A SEAT, AND THAT IS THE WHOLE DESIGN. A seat carries identity, a singleton lock, cursors,
a mailbox, a heartbeat, a roster row, a wake listener and reaper protection. Every one of those
exists so a peer can be addressed ASYNCHRONOUSLY and survive without the caller. A synchronous ask
needs none of it: it is born, it answers, it dies inside one call. Today every ask has to become a
seat, which is why asking costs what it costs.

DELIBERATELY ABSENT IN v1, each for a reason:
  * TOOLS -- a tool loop is the seat path (budget, hops, wedges). Single turn first; see how it
    actually gets used before adding the machinery that broke the last two rounds.
  * PERSISTENT MEMORY -- persistence is what makes a seat. Memory that must cross invocations
    belongs in the store (learn/note) where the whole fleet can inspect it, not in N private
    shadow histories nobody can audit.
  * WRITE ACCESS -- a helper that can write is a seat with extra steps, and needs all the
    machinery back.

IT RETURNS A BoundaryOutcome, which is the point of having built one. In particular a response cut
off by `finish_reason == "length"` comes back as PARTIALLY -- the T169 lesson generalized: a helper
that ran out of room hands back what it has, marked, instead of looking complete or returning "".
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from core.outcome import BoundaryOutcome

DEFAULT_MODEL = os.getenv("AKASHIC_ASK_MODEL", "deepseek-v4-pro")
DEFAULT_MAX_TOKENS = int(os.getenv("AKASHIC_ASK_MAX_TOKENS", "2000"))
BASE_URL = os.getenv("AKASHIC_ASK_BASE_URL", "https://api.deepseek.com")
KEY_FILE = Path(__file__).resolve().parents[2] / ".secrets" / "deepseek.key"
DEFAULT_SYSTEM = (
    "You are a helper called synchronously by claude, the conductor of the Akashic Aurora fleet. "
    "You have no memory of previous calls and no tools. Answer the question directly and briefly. "
    "If you cannot answer from what you were given, say exactly what is missing -- a stated gap is "
    "worth more than a confident guess."
)


def _load_key() -> Optional[str]:
    """Env first, then the gitignored key file -- the same order and the same two sources
    scripts/deepseek_chat.py uses. Resolved HERE so core does not have to reach into scripts
    for a credential; runner_lib takes explicit parameters precisely so callers own this.
    """
    v = os.getenv("DEEPSEEK_API_KEY")
    if v and v.strip():
        return v.strip()
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def _usd(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Cost in USD, or None when the model has no sourced rate.

    None is a DESIGNED state, not a failure: runner_token_journal's own comment says an absent
    entry stays unpriced rather than borrowing another vendor's number.
    """
    try:
        # DIRECTION SEAM, filed rather than normalized: the canonical price table lives in
        # scripts/, so this is a core -> scripts import, which is backwards. It resolves
        # through every real door (agent_cli.py and the pins both put the repo root on
        # sys.path), and the except below makes an unresolvable import behave exactly like
        # an unpriced model -- None, never a borrowed rate. The table belongs in core; moving
        # it touches agent_cli and runner_token_journal, so it is a follow-up task and NOT a
        # a path hack here -- which was this module's original boundary violation.
        # (This comment cannot NAME that hack: check_boundaries greps raw text, so writing
        #  the literal token would flag the very line explaining its removal -- K6's
        #  reflexivity bug, one function away. Filed as a follow-up against the checker.)
        from scripts.runner_token_journal import price_of
        rate = price_of(model)
        if not rate:
            return None
        return round(prompt_tokens / 1e6 * float(rate["prompt"])
                     + completion_tokens / 1e6 * float(rate["completion"]), 6)
    except Exception:
        return None


def ask(prompt: str, *, system: Optional[str] = None, model: Optional[str] = None,
        max_tokens: Optional[int] = None, client=None) -> BoundaryOutcome:
    """Ask a helper one question, synchronously. Never raises.

    Returns a BoundaryOutcome whose `detail["answer"]` carries the text. done / partially / failed
    are the three real states, and every one of them can say why.
    """
    if not str(prompt or "").strip():
        return BoundaryOutcome.failed("empty prompt -- nothing to ask")
    model = model or DEFAULT_MODEL
    t0 = time.time()
    try:
        if client is None:
            key = _load_key()
            if not key:
                return BoundaryOutcome.failed(
                    "no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the door is closed, "
                    "which is a configuration state and not a model failure")
            # core -> core. runner_lib is the G4/L0 anti-wedge factory, so ask inherits the
            # per-read timeout AND lands in the T156 wire journal for free.
            from core.comm.runner_lib import make_openai_compat_client
            client = make_openai_compat_client(key, BASE_URL)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system or DEFAULT_SYSTEM},
                      {"role": "user", "content": prompt}],
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        )
    except Exception as e:
        return BoundaryOutcome.caught(e, where=f"ask({model})")

    elapsed = round(time.time() - t0, 2)
    try:
        choice = resp.choices[0]
        answer = (choice.message.content or "").strip()
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
    except Exception as e:
        return BoundaryOutcome.caught(e, where="ask(parse response)")

    detail = {"answer": answer, "model": model, "prompt_tokens": pt,
              "completion_tokens": ct, "usd": _usd(model, pt, ct),
              "elapsed_s": elapsed, "finish_reason": finish}

    if not answer:
        return BoundaryOutcome.failed(
            f"model returned an empty answer (finish_reason={finish})", **detail)
    if finish == "length":
        # The T169 lesson, generalized: out of room is a PARTIAL, never a silent complete.
        return BoundaryOutcome.partially(
            f"answer cut at the {max_tokens or DEFAULT_MAX_TOKENS}-token ceiling "
            f"(finish_reason=length) -- ask again narrower, or raise --max-tokens", **detail)
    return BoundaryOutcome.done(**detail)
