"""Payload-truth capture shared by every harness adapter (Integration Tiers H1).

Never trust an assumed hook payload shape: the ONLY ground truth for what a runtime
actually sends per version is a live capture (the 2026-07-01 lesson -- Claude's
PostToolUse turned out to fire only on success, sinking the assumed design). Every
adapter therefore captures its payload FIRST, before acting on any field, and the
captures get pinned into tests/fixtures/<harness>_payloads/ as contract tests.

Bounded (newest _CAP_MAX files per dir), string-truncated (the SHAPE is the contract,
not the content), tempdir-only, fail-soft, kill switch AKASHIC_PAYLOAD_CAPTURE=0.
Callers own their directory (one per harness) so per-harness pinning stays trivial.
"""
import json
import os
import time

_CAP_MAX = 200
_CAP_STR = 400


def truncated(o, depth=0):
    """Copy with long strings cut to _CAP_STR chars -- shape survives, content need not."""
    if depth > 6:
        return "..."
    if isinstance(o, str):
        return o if len(o) <= _CAP_STR else o[:_CAP_STR] + f"...[+{len(o) - _CAP_STR} chars]"
    if isinstance(o, dict):
        return {k: truncated(v, depth + 1) for k, v in o.items()}
    if isinstance(o, list):
        return [truncated(v, depth + 1) for v in o[:20]]
    return o


def capture(data, cap_dir: str, label: str = "unknown") -> None:
    """Write one truncated payload snapshot into cap_dir, pruning to the newest _CAP_MAX.
    Diagnostics only: fail-soft, it must never affect the agent."""
    if os.getenv("AKASHIC_PAYLOAD_CAPTURE", "1") == "0":
        return
    try:
        os.makedirs(cap_dir, exist_ok=True)
        name = "%d_%s_%s.json" % (int(time.time() * 1000), label, os.getpid())
        with open(os.path.join(cap_dir, name), "w", encoding="utf-8") as f:
            json.dump(truncated(data), f, indent=1)
        stale = sorted(os.listdir(cap_dir))[:-_CAP_MAX]   # ms-epoch prefix -> lexical sort = oldest first
        for n in stale:
            try:
                os.remove(os.path.join(cap_dir, n))
            except Exception:
                pass
    except Exception:
        pass
