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
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.outcome import BoundaryOutcome

#: Discord's hard cap on a message body. Exceeding it is a rejected post, not a clipped one.
DISCORD_MAX = 2000

#: 2026-09-03 (reachability incident): four independent daemons (claude, deepseek, kimi,
#: sol) each pump the SAME global webhook every ~10s with no cross-process coordination --
#: under fleet chatter that blows straight through Discord's per-webhook rate bucket. Every
#: `_default_post` in this house called `raise_for_status()` on the first 429 and the caller
#: (discord_feed.pump) treats a failed post as SKIP, NEVER RETRY -- cursor still advances, so
#: a rate-limited reply was gone forever, confessed only to a log line nobody reads live. This
#: is why "I messaged multiple agents and none responded" reproduces with a healthy gateway,
#: a healthy daemon, and a bus reply that really was sent. Bounded retry against Discord's own
#: reported wait absorbs exactly the transient multi-writer collision without turning a
#: sustained outage into a blocked daemon loop.
_RATE_LIMIT_MAX_RETRIES = 3


def _retry_after_seconds(resp: Any) -> float:
    """Discord's 429 body carries `retry_after` as fractional seconds -- more precise
    than the `Retry-After` header, which is rounded to whole seconds. Small pad against
    clock skew; a missing/unparseable signal falls back to a conservative 1s."""
    try:
        body = resp.json()
        ra = body.get("retry_after")
        if ra is not None:
            return max(0.0, float(ra)) + 0.05
    except ValueError:
        pass
    hdr = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
    try:
        return max(0.0, float(hdr)) + 0.05 if hdr else 1.0
    except (TypeError, ValueError):
        return 1.0


def post_with_rate_limit_retry(post_fn: Callable[[], Any], *,
                               sleep: Callable[[float], None] = time.sleep) -> Any:
    """Call `post_fn()` (a `requests.post(...)` invocation), retrying ONLY on HTTP 429,
    up to `_RATE_LIMIT_MAX_RETRIES` times, waiting exactly what Discord reports it wants.
    Any other status (or exhausted retries) raises via the caller's own `raise_for_status`,
    unchanged -- this only reclaims the specific failure class that is a coordination
    collision, not a real outage."""
    resp = post_fn()
    attempt = 0
    while resp.status_code == 429 and attempt < _RATE_LIMIT_MAX_RETRIES:
        sleep(_retry_after_seconds(resp))
        attempt += 1
        resp = post_fn()
    return resp

#: Same env-first-then-gitignored-file order every other credential here uses.
#: T365: route through secret_intake.secrets_dir() so AKASHIC_SECRETS_DIR redirects the vault
#: (a module-path constant can't be redirected; that class already leaked a credential once).
def url_file() -> Path:
    """Return the active vault path without exposing or reading its credential.

    Status/setup surfaces need to name the same redirected path that ``webhook_url``
    reads.  A function keeps that authority live; a module constant freezes the path
    before ``AKASHIC_SECRETS_DIR`` can redirect it.
    """
    from core.comm.secret_intake import secrets_dir
    return secrets_dir() / "discord_webhook.url"

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
    #
    # THE HYPHEN, 2026-08-24. This pattern was written when an OpenAI key was `sk-` + one
    # alphanumeric blob, and `[A-Za-z0-9]{8,}` was exactly right for that shape. Both vendors
    # then moved to PREFIXED keys -- `sk-ant-api03-...` (Anthropic, the format this house's own
    # credentials use) and `sk-proj-...` (OpenAI) -- and the character class stops dead at the
    # first hyphen: `sk-ant` is three characters, fails {8,}, no match, key forwarded intact.
    # Verified by hand before the fix: sk-ant-api03-* and sk-proj-* both passed through
    # `redact()` unchanged, while the legacy sk-* form redacted correctly. A guard that was
    # right on the day it was written and was never re-read against the thing it guards.
    #
    # The body now admits internal hyphens but must still START and END alphanumeric, so a
    # trailing "-" or a bare "sk--" is not swallowed and prose is left alone.
    (re.compile(r"\b(sk-[A-Za-z0-9][A-Za-z0-9\-]{6,}[A-Za-z0-9]|ghp_[A-Za-z0-9]{8,}"
                r"|xox[baprs]-[A-Za-z0-9-]{8,}|AIza[A-Za-z0-9_\-]{10,})"), "[REDACTED-KEY]"),
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
        return url_file().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


#: additional pool slots for the SAME global channel -- Discord meters a webhook by its
#: URL, not by the channel it posts into, so N webhooks on one channel are N independent
#: rate-limit buckets. Named like `url_file()`'s single slot so the paste-window UX
#: (secret_intake) that already exists for one credential just... works for four.
_POOL_SLOT_NAMES = ("discord_webhook.url", "discord_webhook_2.url",
                    "discord_webhook_3.url", "discord_webhook_4.url")


def webhook_urls() -> list:
    """Every configured pipe for the global channel, most-preferred first.

    2026-09-03 (the coordination-gap note this closes): the fleet's daemons were never
    individually over budget -- FOUR of them pumping the SAME single webhook is what blew
    through its bucket. Multiple webhooks pointed at the same channel are how Discord's own
    rate limit is shaped to be scaled: pool N of them and the sustained ceiling is N times
    one, while every caller (`forward()`, the automatic feed) still makes exactly one
    logical post -- the pool is invisible from outside this module.

    AKASHIC_DISCORD_WEBHOOKS overrides the vault entirely with a comma/newline separated
    list (an ops deploy that would rather not paste through the window); AKASHIC_DISCORD_
    WEBHOOK (singular, pre-existing) still works as a one-pipe override. Absent either,
    falls back to whichever vault slots hold a value -- one pipe is the common case and
    stays exactly as before.
    """
    env = os.getenv("AKASHIC_DISCORD_WEBHOOKS") or os.getenv("AKASHIC_DISCORD_WEBHOOK")
    if env and env.strip():
        urls = [u.strip() for u in re.split(r"[,\n]", env) if u.strip()]
        if urls:
            return urls
    out = []
    for name in _POOL_SLOT_NAMES:
        try:
            v = (url_file().parent / name).read_text(encoding="utf-8").strip()
        except OSError:
            v = ""
        if v:
            out.append(v)
    return out


def post_via_pool(urls: list, content: str, post_fn: Callable[[str, str], Any]) -> Any:
    """Post `content` through the first pipe in `urls` with capacity.

    `post_fn(url, content)` already retries against ITS OWN bucket (every `_default_post`
    in this house wraps `post_with_rate_limit_retry`); a pipe that is STILL 429 after that
    budget hands off to the NEXT pipe instead of sleeping through the same bucket's
    cooldown -- this is the difference between N webhooks being worth N times the WAIT of
    one versus N times the THROUGHPUT. Any other failure (non-429, or the pool exhausted)
    propagates exactly as a single-pipe call would, so callers built for one pipe need no
    changes.
    """
    import requests
    last_exc: Optional[Exception] = None
    for u in urls:
        if not u:
            continue
        try:
            return post_fn(u, content)
        except requests.HTTPError as e:
            resp = getattr(e, "response", None)
            if resp is not None and getattr(resp, "status_code", None) == 429:
                last_exc = e
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("discord post_via_pool: no pipe configured")


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
    r = post_with_rate_limit_retry(
        lambda: requests.post(url, json={"content": content}, timeout=10))
    r.raise_for_status()
    return True


_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)


def chunk(text: str, max_len: int = DISCORD_MAX) -> list:
    """Split `text` into whole-line parts, none over `max_len`, never splitting a word.

    THE LAW 2026-08-19 (T364). An oversize body used to become ONE truncated post whose
    tail carried `bifrost-fetch --get <id>` — a SHELL command. The reader is Daniil on a
    phone: a recovery handle he cannot run is the T220/T222 defect wearing gloves. The fix
    is to POST N parts instead of one clip, so a long message is simply read, top to
    bottom, no shell required.

    Three guarantees, in priority order:
    1. No part exceeds `max_len` (Discord rejects an overlarge body outright, so this one
       is absolute — if a single line overflows the cap, it hard-splits at a word boundary).
    2. No part splits a WORD — boundaries fall on whitespace, or on a newline.
    3. No part splits a markdown fence — a ``` ... ``` block stays in one part until the
       block alone exceeds the cap, at which point it hard-splits (atomic-until-impossible).
    """
    if not text:
        return [""]

    lines = text.split("\n")
    parts: list = []
    current: list = []

    def _flush() -> None:
        if current:
            parts.append("\n".join(current))
            current.clear()

    def _fits(line: str) -> bool:
        joined = "\n".join(current + [line])
        return len(joined) <= max_len

    i = 0
    while i < len(lines):
        line = lines[i]
        # A fence-opener line pulls its WHOLE block along atomically.
        if _FENCE_RE.match(line):
            block = [line]
            j = i + 1
            while j < len(lines):
                block.append(lines[j])
                # a closing fence is a fence line that is not the opener
                if _FENCE_RE.match(lines[j]) and j != i:
                    break
                j += 1
            block_text = "\n".join(block)
            if block_text and len(block_text) > max_len:
                # atomic-until-impossible: the block alone overflows, hard-split it.
                _flush()
                parts.extend(_hard_split(block_text, max_len))
                i = j + 1
                continue
            # fits appended to the current part? else start a fresh part for it.
            if current and _len_joined(current, block_text) > max_len:
                _flush()
            current.extend(block)
            i = j + 1
            continue
        if not current:
            if len(line) <= max_len:
                current.append(line)
            else:
                parts.extend(_hard_split(line, max_len))
        elif len(line) <= max_len and _fits(line):
            current.append(line)
        else:
            _flush()
            if len(line) > max_len:
                parts.extend(_hard_split(line, max_len))
            else:
                current.append(line)
        i += 1
    _flush()
    return [p for p in parts if p]


def _len_joined(current: list, block_text: str) -> int:
    return len("\n".join(current + [block_text]))


def _hard_split(text: str, max_len: int) -> list:
    """Split overflow text at word boundaries without exceeding max_len. A word longer
    than max_len is itself hard-split at max_len (there is no other faithful choice)."""
    out: list = []
    buf = ""
    for word in text.split(" "):
        candidate = (buf + " " + word) if buf else word
        if len(candidate) <= max_len:
            buf = candidate
        else:
            if buf:
                out.append(buf)
                buf = ""
            while len(word) > max_len:
                out.append(word[:max_len])
                word = word[max_len:]
            buf = word
    if buf:
        out.append(buf)
    return out


def render_parts(msg: Dict[str, Any]) -> list:
    """One or more Discord posts for a message: the head rides every part, and a body
    over the cap becomes N whole-line parts — none truncated, none carrying a shell
    handle. This is what makes a long message readable top-to-bottom from a phone."""
    frm = str(msg.get("frm") or "?")
    kind = str(msg.get("kind") or "?")
    body = redact(_content_str(msg.get("content")))
    head = f"**{frm}** · `{kind}`\n"
    if not body:
        return [head.rstrip("\n")]
    if len(head) + len(body) <= DISCORD_MAX:
        return [head + body]
    # body must carry the head+body budget, so chunk the BODY against the remaining room.
    room = DISCORD_MAX - len(head)
    parts = chunk(body, max_len=room)
    return [head + p for p in parts]


def render(msg: Dict[str, Any]) -> str:
    """Backward-compatible single-render: the FIRST part of render_parts. Kept because a
    caller asking for one string is asking for one string; the multi-post path (forward)
    iterates render_parts directly."""
    return render_parts(msg)[0]


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
    targets = ([url] if url else []) if url is not None else webhook_urls()
    if not targets:
        return BoundaryOutcome.failed(
            "discord bridge not configured -- set AKASHIC_DISCORD_WEBHOOK or write "
            ".secrets/discord_webhook.url. This is a configuration state, not a delivery "
            "failure: the bridge is opt-in and most seats will never set it.")
    # REFUSE AN EMPTY BODY (2026-08-25). render_parts returns the head alone when there is
    # no body, and forward used to post it -- so a message with nothing in it arrived
    # looking like a delivered reply. Simon, on the receiving end: "getting empty responses
    # here labeled reply". That is a green light produced by absence, on the one path where
    # the reader has no way to tell it from a delivery failure.
    #
    # The refusal NAMES the field, because the way this happens in practice is a bus-shaped
    # dict: the bus carries its body in `text`, render_parts reads `content`, and the
    # mismatch is invisible until a human says the replies are blank. A refusal that only
    # said "failed" would be the original silence with punctuation on it.
    if not _content_str(msg.get("content")).strip():
        return BoundaryOutcome.failed(
            "refusing to post an EMPTY body -- a header with nothing under it reads as a "
            "delivered reply and carries no information, which the reader cannot tell from "
            "a failed send. If your message came off the bus, its body is in 'text' and "
            "this renderer reads 'content'; that mismatch is the usual cause.")
    parts = render_parts(msg)
    poster = post or _default_post
    try:
        for content in parts:
            post_via_pool(targets, content, poster)
    except Exception as e:                                              # noqa: BLE001
        return BoundaryOutcome.failed(
            f"discord post failed ({type(e).__name__}: {e}) -- the bus is unaffected; this "
            f"bridge is a listener and never blocks a send")
    return BoundaryOutcome.done(ref=str(msg.get("id") or ""),
                                chars=sum(len(p) for p in parts))
