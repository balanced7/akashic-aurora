"""core.comm.runner_lib -- shared hardening for OpenAI-compatible seat transports (K0, 2026-07-18).

The rule-of-three extraction's second seam (fence: deepseek counter sec 1, accepted): the
G4/L0 anti-wedge client factory as GENUS -- explicit parameters only, no env reads here.
Each seat module (deepseek_chat, kimi_chat, ...) wraps this with its OWN env-var conventions
and defaults; that keeps every seat's tuning surface local and greppable, per the fence.

The Agent/loop layer deliberately does NOT live here ("premature generalization" ruling):
chat-completions loops stay species-specific until two of them stabilize side by side.
"""
from __future__ import annotations


def set_seat_agent(agent: str) -> str:
    """Declare which seat this runner process is, so its wire records are attributable.

    T160: BIFROST_AGENT was read in exactly one place and written in none, so 102 of 102 records
    in the live journal said 'unknown' and doctor's per-seat wire forensics matched nothing for
    as long as it had existed. Every runner already knows its own id from argv; nothing carried
    it the last few inches.

    Wrapped here rather than imported directly by four runners so the SAFETY NET has one
    definition: a runner must never fail to start because its instrumentation could not load.
    That is the same rule recording_http_client() follows, and for the same reason -- the
    blindness this cures is far cheaper than a seat that will not boot.
    """
    try:
        from scripts.wire_journal import set_seat_agent as _set
        return _set(agent)
    except Exception:
        return ""


def make_openai_compat_client(api_key: str, base_url: str, *,
                              connect_timeout: float = 15.0,
                              read_timeout: float = 120.0,
                              max_retries: int = 1):
    """OpenAI-compatible client hardened against hung-stream wedges (G4/L0): a per-read
    streaming timeout turns a stalled model call into a caught httpx.ReadTimeout the caller's
    try/except revives from, and an explicit max_retries stops the SDK default (2) from
    tripling wall-clock before the wedge surfaces. Lazy imports keep this module import-cheap
    for callers that never build a client (e.g. spend-ledger-only tooling)."""
    from openai import OpenAI
    import httpx
    return OpenAI(api_key=api_key, base_url=base_url,
                  timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
                  max_retries=max_retries)
