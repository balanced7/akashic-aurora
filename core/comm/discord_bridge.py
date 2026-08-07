"""Outbound Discord bridge -- the fleet becomes watchable from a phone.

Daniil, leaving for work 2026-08-07: "research and build out what it will take for me to be
able to interact with akashic aurora via discord".

THE FINDING THAT SHRANK THIS. It is not an integration; it is `scripts/bifrost_console.py`
with a different I/O surface. That module already implements a human joining the bus as a
participant -- broadcast, `@claude` DM, live transcript -- and its only defect from a phone is
that it needs a terminal on this machine. The bus half is finished; this replaces stdout.

PHASE 1 IS OUTBOUND ONLY, AND THAT IS A SECURITY PROPERTY RATHER THAN A ROADMAP NOTE. A
Discord webhook URL is WRITE-ONLY: holding it lets you post to one channel and nothing else --
it cannot read, enumerate, or act. Inbound is where the whole risk lives, because a channel
that feeds messages to agents is a prompt-injection door into a fleet holding a shell, a repo
and an API budget. That path does not ship until its identity gate (design doc R1-R3) is built
and pinned, and `test_the_outbound_bridge_exposes_no_inbound_door` enforces that this module
does not grow one by accident.

Outbound alone is ~80% of the value -- visibility while away, which is the thing actually
missing today -- at ~0% of the added attack surface.

PRIVACY, stated because it is easy to skip: posting to Discord PUBLISHES to a third party,
retained and indexed regardless of later deletion. Hence `redact()` below, and hence the
recommendation of a private server with one private channel.

Setup is five minutes and is documented in
research/in-flight/discord-bridge-design-2026-08-07.md.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.outcome import BoundaryOutcome

#: Discord's hard cap on a message body. Exceeding it is a rejected post, not a clipped one.
DISCORD_MAX = 2000

#: Same env-first-then-gitignored-file order every other credential here uses.
URL_FILE = Path(__file__).resolve().parents[2] / ".secrets" / "discord_webhook.url"

#: AN ALLOWLIST, NEVER A DENYLIST. A denylist silently leaks every kind added after it was
#: written, and this repo adds kinds regularly -- 31 at the T177 census, with 14 hand-kept
#: policy sets already disagreeing about them. An unknown kind therefore does NOT forward.
#: `trace` is deliberately absent: it is the firehose and would make the channel unreadable
#: within an hour, which is how a notification surface gets muted and stops being read at all.
FORWARD_KINDS = frozenset({
    "handoff", "blocker", "resolved", "ledger_update", "question", "reply",
    "completion", "nudge", "halt", "chat",
})

#: Senders whose mail always forwards regardless of kind -- a message from a person is the one
#: thing worth a phone buzz. Mirrors bifrost_wake's operator override rather than inventing a
#: second list, because two lists of "who counts as the operator" is the fork this repo keeps
#: paying for.
_OPERATORS = frozenset({"user", "daniel", "daniil", "human", "operator"})

_SECRET_PATTERNS = (
    # provider keys: sk-..., ghp_..., xoxb-..., AIza..., and generic KEY=<blob>
    (re.compile(r"\b(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}"
                r"|AIza[A-Za-z0-9_\-]{10,})"), "[REDACTED-KEY]"),
    (re.compile(r"((?:API_?KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*)(\S{6,})", re.IGNORECASE),
     r"\1[REDACTED]"),
    # a webhook URL leaking through the channel it posts to
    (re.compile(r"(https://discord(?:app)?\.com/api/webhooks/\d+/)(\S+)"), r"\1[REDACTED]"),
)


def webhook_url() -> str:
    """The configured webhook, or "" when the bridge is simply off.

    ABSENT IS NOT BROKEN. Most seats will never configure this, and an unconfigured bridge
    must be distinguishable from a delivery failure -- T170's one vocabulary, and the reason
    `forward()` says "not configured" rather than returning a bare falsy.
    """
    v = os.getenv("AKASHIC_DISCORD_WEBHOOK")
    if v and v.strip():
        return v.strip()
    try:
        return URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def should_forward(msg: Dict[str, Any]) -> bool:
    """Is this worth a phone buzz? Allowlist by kind, plus any human sender."""
    frm = str(msg.get("frm") or "").lower()
    if frm in _OPERATORS:
        return True
    return str(msg.get("kind") or "") in FORWARD_KINDS


def redact(text: str) -> str:
    """Strip credential-shaped substrings before anything leaves the machine.

    VISIBLE redaction, never silent deletion: a reader who cannot tell a redaction from an
    empty field will eventually trust the empty field. And deliberately conservative on the
    surrounding text -- over-redaction makes the channel useless, which is how a safety
    feature gets switched off entirely.
    """
    out = str(text or "")
    for pat, repl in _SECRET_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _default_post(url: str, content: str) -> bool:
    """The only network call in this module, isolated so every pin runs offline."""
    import requests
    r = requests.post(url, json={"content": content}, timeout=10)
    r.raise_for_status()
    return True


def render(msg: Dict[str, Any]) -> str:
    """One Discord line: who, what kind, the body, and -- when clipped -- its ADDRESS.

    The clip carries a handle for the same reason T220/T222 did, but the stakes are higher
    here: the reader is on a phone with no shell, so an unaddressed clip is unrecoverable by
    the person actually reading it rather than merely expensive.
    """
    frm = str(msg.get("frm") or "?")
    kind = str(msg.get("kind") or "?")
    body = redact(_content_str(msg.get("content")))
    head = f"**{frm}** · `{kind}`\n"
    mid = str(msg.get("id") or "")
    tail = f"\n… clipped · full body: `bifrost-fetch --get {mid}`" if mid else \
           "\n… clipped · NO ADDRESS (this render had no message id)"
    room = DISCORD_MAX - len(head) - len(tail)
    if len(body) <= DISCORD_MAX - len(head):
        return head + body
    return head + body[:max(0, room)] + tail


def _content_str(c: Any) -> str:
    if isinstance(c, str):
        return c
    if c is None:
        return ""
    return str(c)


def forward(msg: Dict[str, Any], *, url: Optional[str] = None, force: bool = False,
            post: Optional[Callable[[str, str], bool]] = None) -> BoundaryOutcome:
    """Post one message to the channel. NEVER RAISES.

    This is a LISTENER on a substrate that must not care about it: a Discord outage, a revoked
    webhook or a rate limit must not raise into a bus caller. It must also not pretend success
    -- silence on a delivery path is the T149 defect, where stdout claimed a send that did not
    happen.
    """
    # The allowlist is load-bearing HERE, so an automatic feed cannot bypass it by calling the
    # wrong function. `force` is for an EXPLICIT operator action (`discord test`/`send`),
    # where the person typing the command is the selection.
    if not force and not should_forward(msg):
        return BoundaryOutcome.failed(
            f"kind {str(msg.get('kind') or '?')!r} is not on the forward allowlist -- not an "
            f"error, a filter. Unknown kinds default to NOT forwarded so a kind added next "
            f"week cannot silently start paging a phone.")
    target = webhook_url() if url is None else url
    if not target:
        return BoundaryOutcome.failed(
            "discord bridge not configured -- set AKASHIC_DISCORD_WEBHOOK or write "
            ".secrets/discord_webhook.url. This is a configuration state, not a delivery "
            "failure: the bridge is opt-in and most seats will never set it.")
    content = render(msg)
    try:
        (post or _default_post)(target, content)
    except Exception as e:                                              # noqa: BLE001
        return BoundaryOutcome.failed(
            f"discord post failed ({type(e).__name__}: {e}) -- the bus is unaffected; this "
            f"bridge is a listener and never blocks a send")
    return BoundaryOutcome.done(ref=str(msg.get("id") or ""), chars=len(content))
