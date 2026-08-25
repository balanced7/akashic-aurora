"""Remote peer relay — the OUTBOUND half of the Akashic↔Akashic bridge (v0.1).

Daniil, 2026-08-24: "design an akashic aurora to akashic aurora bridge ... so Serge's DSH
agent can communicate with us ... I don't want everyone having access."
Design: docs/library/design/remote-bifrost-bridge-design.md (fence: remote-bridge).

STATUS: v1. Outbound (push/enqueue/tick) AND the inbound gate (accept) are both live; the
HTTP door is scripts/remote_bridge_listener.py. v0.1 was outbound-only ON PURPOSE — a peer
relay is a prompt-injection door into a fleet holding a shell, a repo and an API budget, so
inbound shipped only once it had an identity pin, HMAC + replay window, the kind allowlist,
redaction, and parked-not-bussed delivery. That sequencing was the point, not a delay.

(This paragraph read "V0 IS OUTBOUND-ONLY" for half a day after inbound shipped. A module
docstring is a claim about the code, and it rots the moment the code moves — Zadkiel found
three such rotted claims in this file at once.)

WHAT V0 GUARANTEES (the three load-bearing properties, each inherited not invented):

1. NO CREDENTIAL ON GITHUB. The committed config (state/coord/remote_bridge.json) names the
   peer URL + which secret FILE, never the secret. The secret is HMAC material in
   .secrets/ (already gitignored), captured through the vault door
   `py agent_cli.py secret remote_bridge_outbound.key`, handed to the peer out-of-band.

2. NOT EVERYONE HAS ACCESS. Outbound direction is one peer (the configured route). Holding
   our outbound secret lets an attacker push INTO Serge's relay only — not read us, not
   steer us, not enumerate. Inbound (the actually dangerous direction) does not exist in v0.

3. ROBUST — AT-LEAST-ONCE, NOT FIRE-AND-FORGET. Messages carry a stable id; a durable
   outbox cursor records the last-acked id; on any post failure the message is NOT dropped
   (it stays un-acked and is replayed on the next tick). A redelivered copy is harmless
   because the receiver dedupes by id (RB-26 house law, carried from the bus).

NEIGHBOUR LAW: this module copies discord_bridge's GUARDS, not just its shape — allowlist
never denylist, visible redaction, absent-is-not-broken, never raise into a bus caller,
injectable transport so every pin runs offline. It still imports discord_bridge's REDACTION,
so credential-scrubbing cannot fork. It deliberately does NOT share the allowlist: see
BRIDGE_KINDS for why FORWARD_KINDS answers a different question, and why the anti-drift
guarantee moved to a pin instead.
"""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from core.outcome import BoundaryOutcome
from core.comm import discord_bridge

_ROOT = Path(__file__).resolve().parents[2]

#: The committed route config: names the peer URL + which secret file, NEVER the secret.
#: A route is inert without the key; the key travels out-of-band (the "Serge one-pager").
CONFIG_FILE = _ROOT / "state" / "coord" / "remote_bridge.json"

#: Direction secrets live FLAT in .secrets/ under these exact names, gitignored house-wide,
#: captured via `py agent_cli.py secret <name>` and handed to the peer out-of-band.
#:
#: An earlier design named them serge_*.key under a .secrets/remote_bridge/ subdir. Nothing
#: ever read those names — THE FLAT NAMES BELOW ARE THE AUTHORITY, because they are what the
#: code opens. Zadkiel (Serge's seat) caught the docstring and a refusal message still
#: teaching the dead ones, which is the worst kind of stale doc: an error that hands a
#: stuck reader a filename that will not work.
OUTBOUND_KEY_FILE = "remote_bridge_outbound.key"
INBOUND_KEY_FILE = "remote_bridge_inbound.key"

#: Clock-skew window for inbound verification (v1) — replay protection margin, seconds.
SKEW_WINDOW_S = 300

#: The BRIDGE allowlist (design §3.2) — deliberately NOT discord_bridge.FORWARD_KINDS.
#:
#: v0.1 imported FORWARD_KINDS to stop the two bridges drifting apart, which is a real virtue
#: and the wrong list, because THE TWO LISTS ANSWER DIFFERENT QUESTIONS. FORWARD_KINDS answers
#: "is this worth buzzing the operator's phone?" — so it contains `halt` and `nudge`, and
#: rightly: a human wants to know the fleet was halted. This list answers "is this safe to
#: accept from ANOTHER FLEET?", and design §3.2 is explicit that a remote peer cannot halt or
#: steer us. Inheriting the phone list silently handed a remote peer two control verbs.
#:
#: The anti-drift guarantee is kept, but moved to where it belongs: a PIN
#: (test_bridge_allowlist_contains_no_control_kind) fails red the moment a control verb
#: appears here. A shared constant would have made the two questions un-askable separately;
#: a pin lets them differ and still catches the mistake.
BRIDGE_KINDS = frozenset({
    "chat", "question", "handoff", "reply", "completion", "blocker", "note",
})

#: Where un-acked outbound mail waits. Durable ON DISK because the whole point is surviving a
#: crash between enqueue and delivery — an in-memory queue is a comment, not a guarantee.
OUTBOX_FILE_DEFAULT = _ROOT / "state" / "coord" / "remote_bridge_outbox.jsonl"

#: Where admitted inbound mail is PARKED. v1 quarantines: an admitted message is DATA an agent
#: drains deliberately, never a live bus message that acts on arrival. This file is also the
#: idempotency ledger — it must be durable, or a restart re-opens the replay window.
INBOX_FILE_DEFAULT = _ROOT / "state" / "coord" / "remote_bridge_inbox.jsonl"

#: Parsed-file cache keyed by path, invalidated on stat change. Real (tick may run on a timer
#: and would otherwise re-parse every pass) and honest (_reset_cache simulates a fresh process).
_FILE_CACHE: Dict[str, Tuple[Tuple[int, int], list]] = {}


def _reset_cache() -> None:
    """Drop every parsed-file cache — what a fresh process would see. Used by pins to prove
    durability is on disk and not in a module global."""
    _FILE_CACHE.clear()


def _jsonl_path(env_name: str, default: Path) -> Path:
    v = os.getenv(env_name)
    return Path(v) if v and v.strip() else default


def outbox_path() -> Path:
    return _jsonl_path("AKASHIC_REMOTE_BRIDGE_OUTBOX", OUTBOX_FILE_DEFAULT)


def inbox_path() -> Path:
    return _jsonl_path("AKASHIC_REMOTE_BRIDGE_INBOX", INBOX_FILE_DEFAULT)


def _read_jsonl(path: Path) -> list:
    """Read a durable line-log. A corrupt line is SKIPPED, never fatal: a half-written record
    from a crash must not wedge the queue it was meant to protect."""
    try:
        st = path.stat()
        sig = (int(st.st_mtime_ns), int(st.st_size))
    except OSError:
        _FILE_CACHE.pop(str(path), None)
        return []
    hit = _FILE_CACHE.get(str(path))
    if hit and hit[0] == sig:
        return list(hit[1])
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    _FILE_CACHE[str(path)] = (sig, list(rows))
    return rows


def _write_jsonl(path: Path, rows: list) -> None:
    """Rewrite the log atomically-ish (tmp + replace) so a crash mid-write cannot truncate the
    queue to nothing — losing the outbox is the exact failure the outbox exists to prevent."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("".join(json.dumps(r, sort_keys=True, default=str) + "\n"
                               for r in rows), encoding="utf-8")
        os.replace(tmp, path)
        _FILE_CACHE.pop(str(path), None)
    except OSError:
        _FILE_CACHE.pop(str(path), None)


def _config() -> Dict[str, Any]:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _secret(filename: str) -> bytes:
    """Direction secret through the vault's OWN resolution rule (env-first, then the
    gitignored file), so AKASHIC_SECRETS_DIR redirects it like every other credential.
    T365: a module-path constant cannot be redirected; this class already leaked once."""
    env_key = {"remote_bridge_outbound.key": "AKASHIC_REMOTE_BRIDGE_OUTBOUND_KEY",
               "remote_bridge_inbound.key": "AKASHIC_REMOTE_BRIDGE_INBOUND_KEY"}.get(filename)
    if env_key:
        v = os.getenv(env_key)
        if v and v.strip():
            return v.strip().encode("utf-8")
    from core.comm.secret_intake import secrets_dir
    try:
        return (secrets_dir() / filename).read_bytes().strip()
    except OSError:
        return b""


def peers() -> list:
    """Every configured peer, newest schema first, falling back to the single-peer shape.

    A fleet that upgrades and silently stops admitting its only peer has been BROKEN by a
    fix, so the legacy `peer` block stays first-class rather than deprecated.
    """
    cfg = _config()
    rows = cfg.get("peers")
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    one = cfg.get("peer")
    return [one] if isinstance(one, dict) and one else []


def resolve_peer(body_b64: str, sig: str, *, within_s: int = SKEW_WINDOW_S):
    """Which configured peer signed this? Returns (name, secret) or (None, None).

    THE KEY IS THE IDENTITY. A flag is our launcher's assertion; `frm` is the sender's
    assertion; only the HMAC is cryptography's assertion — whoever signed this held that
    secret, and secrets are per-peer by construction. So identity is whatever the maths says
    and nothing else, which is the payload-frm rule applied one level up: having stopped
    trusting the sender's claim, we also stop trusting our own configuration's guess.

    Order-independent by construction: every candidate is tried and the answer is the one
    that verifies, so a config reshuffle can never change who a message came from.
    """
    for row in peers():
        name = str(row.get("name") or "").strip()
        fname = str(row.get("inbound_secret_file") or INBOUND_KEY_FILE)
        key = _secret(fname)
        if not key or not name:
            continue
        if verify(body_b64, sig, key, within_s=within_s):
            return name, key
    return None, None


def peer_row(selector: str = ""):
    """The config row for an outbound selector, or the default. None when unknown.

    A PEER IS A PAIR OF DIRECTIONS, NOT AN INBOX (Chronos, 2026-08-25). Inbound identity comes
    from the key that verified; outbound identity comes from here — the row carries the url we
    speak to and the key we sign with.

    TWO FIELDS, BECAUSE ONE FIELD WAS ANSWERING TWO QUESTIONS (Chronos again, hours later):

        `name`  WHO SENT IT      — the label stamped on arriving mail
        `as`    WHO WE SIGN AS   — our local identity on this route

    On OUR topology they coincide (one local identity, N remote peers), which is exactly why
    a single field survived review. Chronos's topology inverts it — ONE remote peer, TWO local
    identities — and there the two jobs disagree: inbound wants both rows labelled `daniil`,
    outbound needs them distinguishable. It measured the consequence before writing any config:
    push(peer="chronos") refused with "configured peers are ['daniil','daniil']", and
    push(peer="daniil") always took the first row, so chronos could never speak as itself.

    The selector matches EITHER field, so rows with no `as` behave exactly as before. An
    AMBIGUOUS selector is refused rather than resolved to the first match: picking one of two
    valid answers is a silent misdelivery, and this is the one moment it is still cheap to say
    so out loud.
    """
    rows = peers()
    if not selector:
        return rows[0] if rows else None
    sel = selector.strip()
    hits = [r for r in rows
            if str(r.get("as") or "").strip() == sel or str(r.get("name") or "").strip() == sel]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return "AMBIGUOUS"
    return None


def peer_url(name: str = "") -> str:
    """The endpoint for a named peer (or the default). "" when unrouted or unknown."""
    v = os.getenv("AKASHIC_REMOTE_BRIDGE_PEER_URL")
    if v and v.strip() and not name:
        return v.strip()
    row = peer_row(name)
    if not isinstance(row, dict):
        return ""                      # unknown OR ambiguous -> unrouted, never a guess
    return str(row.get("url") or "")


def _outbound_key_for(name: str = "") -> bytes:
    row = peer_row(name)
    if not isinstance(row, dict):
        return b""                     # unknown OR ambiguous -> inert, never the wrong key
    return _secret(str(row.get("outbound_secret_file") or OUTBOUND_KEY_FILE))


#: The entry point a peer runs to follow a blob ref. Named ONCE, here, because the pin parses
#: this very string out of the announcement and asserts the file exists — a retrieval command
#: that is not a real entry point is the pointer-with-no-door defect, and the only way to keep
#: an advertised verb honest is to derive the advertisement from something checkable.
FETCH_ENTRY = "scripts/remote_bridge_fetch.py"


def blob_matches_ref(data, ref: str) -> bool:
    """Do these bytes hash to that ref? THE INTEGRITY CHECK IS THE ADDRESS.

    Nothing else needs to be compared. A truncated, mangled or substituted body simply is not
    that ref any more — which is what retires the fingerprint ceremony two mangled key pastes
    needed tonight. Never raises; a malformed ref is a mismatch, not an error.
    """
    if not isinstance(data, (bytes, bytearray)) or not str(ref or "").startswith("blob:"):
        return False
    want = str(ref)[len("blob:"):]
    if not want:
        return False
    return hashlib.sha256(bytes(data)).hexdigest()[:len(want)] == want


def file_announcement(path, *, blobs=None) -> Dict[str, Any]:
    """Stage a file and describe it. Returns the NOTICE, never the payload.

    A 1.5MB corpus does not become a 1.5MB message: the bytes go to the content-addressed blob
    store and the peer is told a ref exists. It pulls if it wants it — parked-not-bussed,
    applied to files. A transport that writes to your disk because someone else decided to
    send something is a different and much worse thing than one that offers.

    `fetch_with` is not decoration. A pointer nobody can follow is WORSE than a clip that
    admits the loss, because it looks like the data is reachable.
    """
    from pathlib import Path as _P
    from core.comm.blobs import get_blob_store
    p = _P(path)
    store = blobs or get_blob_store()
    ref = store.put_path(p)
    return {
        "kind": "file",
        "ref": ref,
        "name": p.name,
        "bytes": p.stat().st_size,
        "fetch_with": f"py {FETCH_ENTRY} {ref} --out {p.name}",
    }


def render_file_announcement(ann: Dict[str, Any]) -> str:
    """One line for every surface that shows a ref — inbox, watcher, relay, doctor.

    Each of those readers must see the DOOR beside the pointer. Enumerating the surfaces and
    giving each one a door is the whole lesson; a ref rendered bare is a dead end wearing the
    appearance of data.
    """
    return (f"[file] {ann.get('name')} ({int(ann.get('bytes') or 0):,} bytes) "
            f"{ann.get('ref')} — fetch: {ann.get('fetch_with')}")


def sign(payload_bytes: bytes, secret: bytes) -> str:
    """HMAC-SHA256 over the raw payload, hex-encoded. Pure, so pins verify offline."""
    return _hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()


def _stable_id(msg: Dict[str, Any]) -> str:
    """The id used for dedupe + outbox cursor. Prefers the message's own id; falls back
    to a content hash so a message without an id still gets a stable address (never an
    ever-fresh uuid — that would make redelivery un-dedupeable)."""
    mid = str(msg.get("id") or "").strip()
    if mid:
        return mid
    raw = json.dumps(msg, sort_keys=True, default=str).encode("utf-8")
    return "h:" + hashlib.sha256(raw).hexdigest()[:16]


def _allowed(msg: Dict[str, Any]) -> bool:
    """The BRIDGE allowlist, by KIND ONLY — see BRIDGE_KINDS for why this is not
    discord_bridge.should_forward().

    Two changes from v0.1, both security properties:

    1. No operator short-circuit. should_forward() returns True for ANY sender on its
       operator list regardless of kind. Outbound that is merely generous; inbound it is an
       impersonation bypass, because the payload's `frm` is written by the peer. A rule that
       reads a sender's self-declared name is a rule an attacker fills in. One function,
       one answer, both directions — so the gate cannot be softer than the door.

    2. Kind-only, from the narrow list. `halt` and `nudge` no longer cross in EITHER
       direction; design §3.2 says a remote peer cannot steer our fleet, and we should not
       expect to steer theirs.
    """
    return str(msg.get("kind") or "") in BRIDGE_KINDS


def _payload(msg: Dict[str, Any]) -> Dict[str, Any]:
    """The projected surface a remote peer is allowed to see. Narrow on purpose: a peer
    never touches our inbox, lanes, Redis, or any control verb — it gets the same
    FORWARD_KINDS slice Discord gets, redacted, with reasoning stripped."""
    return {
        "v": 1,
        "id": _stable_id(msg),
        "frm": str(msg.get("frm") or "?"),
        "kind": str(msg.get("kind") or "?"),
        "content": discord_bridge.redact(discord_bridge._content_str(msg.get("content"))),
        "sent_at": int(time.time()),
    }


def render(msg: Dict[str, Any]) -> bytes:
    """One canonically-signed payload (JSON + HMAC). Canonical ordering (sort_keys) so the
    sender and verifier compute the same signature. Never raises on a malformed message."""
    try:
        return json.dumps(_payload(msg), sort_keys=True, separators=(",", ":"),
                          default=str).encode("utf-8")
    except Exception:                                            # noqa: BLE001
        return json.dumps({"v": 1, "frm": "?", "kind": "?", "content": ""},
                          sort_keys=True).encode("utf-8")


def build_envelope(msg: Dict[str, Any], secret: bytes) -> Dict[str, str]:
    """The wire envelope: base64 body + its HMAC, so the verifier does not need to re-serialize
    byte-for-byte. Pure; the transport (push) and verify (v1) both consume this shape."""
    body = render(msg)
    return {"body": base64.b64encode(body).decode("ascii"),
            "sig": sign(body, secret)}


def push(msg: Dict[str, Any], *, url: Optional[str] = None,
         post: Optional[Callable[[str, Dict[str, str]], Any]] = None,
         secret: Optional[bytes] = None, peer: str = "") -> BoundaryOutcome:
    """Push one message to the remote peer's relay. NEVER RAISES.

    OUTBOUND-ONLY, v0.1: a single best-effort POST. The durable outbox (def tick below)
    wraps this and provides at-least-once redelivery; this function is the pure half a pin
    can exercise offline with an injected `post`."""
    if not _allowed(msg):
        return BoundaryOutcome.failed(
            f"kind {str(msg.get('kind') or '?')!r} is not on the forward allowlist — the "
            f"remote bridge inherits the Discord list; unknown kinds don't cross the bridge")
    # AN UNKNOWN PEER IS A REFUSAL, NEVER A FALLBACK. Silently defaulting to "the first
    # peer" would send one fleet's message to another fleet -- a misdelivery that returns 202
    # and looks like success, which is the worst shape a bug can take.
    _row = peer_row(peer) if peer else None
    if peer and _row == "AMBIGUOUS":
        return BoundaryOutcome.failed(
            f"AMBIGUOUS outbound selector {peer!r} — more than one configured row answers to "
            f"it. Give the rows distinct `as` values (your local identity on each route); "
            f"`name` stays the REMOTE sender's label. Refusing rather than taking the first "
            f"match: choosing between two valid rows is a misdelivery that returns 202.")
    if peer and _row is None:
        return BoundaryOutcome.failed(
            f"unknown peer {peer!r} — configured peers are "
            f"{[str(r.get('name')) for r in peers()] or '(none)'}. Refusing rather than "
            f"falling back: delivering to the wrong fleet would look exactly like success.")
    target = url if url is not None else peer_url(peer)
    if not target:
        return BoundaryOutcome.failed(
            "remote bridge not routed — set AKASHIC_REMOTE_BRIDGE_PEER_URL or write the "
            "peer url into state/coord/remote_bridge.json. A configuration state, not a "
            "delivery failure: the bridge is opt-in.")
    key = secret if secret is not None else _outbound_key_for(peer)
    if not key:
        return BoundaryOutcome.failed(
            "remote bridge has no outbound secret. Capture one with "
            "`py agent_cli.py secret remote_bridge_outbound.key` (the vault door keeps it "
            "out of every transcript), then hand the peer the SAME value out-of-band. "
            "Inert-until-keyed is the 'not everyone has access' gate.")
    envelope = build_envelope(msg, key)
    try:
        (post or _default_post)(target, envelope)
    except Exception as e:                                        # noqa: BLE001
        return BoundaryOutcome.failed(
            f"remote push failed ({type(e).__name__}: {e}) — the bus is unaffected; this "
            f"relay is a listener and never blocks a send")
    return BoundaryOutcome.done(ref=_stable_id(msg), chars=len(envelope["body"]))


def _default_post(url: str, envelope: Dict[str, str]) -> Any:
    """The only network call in this module, isolated so every pin runs offline."""
    import requests
    r = requests.post(url, json=envelope, timeout=12)
    r.raise_for_status()
    return r.json()


def verify(body_b64: str, sig: str, secret: bytes, *, within_s: int = SKEW_WINDOW_S) -> bool:
    """v1 inbound verification: HMAC must match, and the payload's sent_at must be within
    the skew window (replay protection). Pure; shipped now so the inbound gate is a thin
    caller over a proven verifier, not a green-field build later."""
    if not secret:
        return False
    try:
        body = base64.b64decode(body_b64)
    except Exception:                                             # noqa: BLE001
        return False
    if not _hmac.compare_digest(sign(body, secret), sig):
        return False
    try:
        sent_at = int(json.loads(body.decode("utf-8")).get("sent_at") or 0)
    except (ValueError, UnicodeDecodeError):
        return False
    return abs(int(time.time()) - sent_at) <= within_s


# =============================================================================================
# THE DURABLE OUTBOX (design §3.4) — "a message that is sent is delivered eventually"
#
# push() above is the pure, single-shot half: one POST, never raises, reports honestly. That
# honesty shipped alone. Reporting a loss and PREVENTING one are different virtues, and a relay
# with only the first is fire-and-forget with good manners.
#
# enqueue -> tick is the pair: the message is on disk before the first attempt and stays there
# until the peer takes it. At-least-once, never at-most-once, because the receiver dedupes by
# stable id (RB-26) and a duplicate is therefore cheap while a loss is not.
# =============================================================================================


def enqueue(msg: Dict[str, Any], *, secret: Optional[bytes] = None,
            peer: str = "") -> BoundaryOutcome:
    """Park one message for delivery. NEVER RAISES.

    REFUSES AT THE DOOR, not at the tick. A message that can never be delivered (wrong kind)
    must not enter the queue: it would be retried forever, growing the file without bound and
    filling the log with a failure nobody can fix. A refusal here is immediate and legible; a
    refusal at the tick is a slow leak that teaches operators to ignore the log.
    """
    if not _allowed(msg):
        return BoundaryOutcome.failed(
            f"kind {str(msg.get('kind') or '?')!r} is not on the bridge allowlist "
            f"({sorted(BRIDGE_KINDS)}) — control verbs never cross a fleet boundary in "
            f"either direction (design §3.2)")
    path = outbox_path()
    rows = _read_jsonl(path)
    mid = _stable_id(msg)
    if any(str(r.get("id")) == mid for r in rows):
        return BoundaryOutcome.done(ref=mid, chars=0)           # RB-26: idempotent enqueue
    if peer and peer_row(peer) is None:
        return BoundaryOutcome.failed(
            f"unknown peer {peer!r} — refusing to queue mail for a fleet that is not "
            f"configured. A queue entry with no valid address is a message that will be "
            f"delivered to whoever happens to be first when it drains.")
    # THE OUTBOX CARRIES THE ADDRESS, NOT JUST THE LETTER. A queue that forgets who a message
    # was for delivers it to whoever is configured first at drain time -- which is a
    # misdelivery that reports success.
    rows.append({"id": mid, "msg": msg, "peer": peer,
                 "queued_at": int(time.time()), "attempts": 0})
    _write_jsonl(path, rows)
    return BoundaryOutcome.done(ref=mid, chars=len(rows))


def pending() -> list:
    """The un-acked backlog, oldest first. Read from DISK so a fresh process sees the truth."""
    return _read_jsonl(outbox_path())


def tick(*, post: Optional[Callable[[str, Dict[str, str]], Any]] = None,
         url: Optional[str] = None, secret: Optional[bytes] = None,
         limit: int = 50) -> BoundaryOutcome:
    """Attempt delivery of the backlog. NEVER RAISES. Reports what actually happened.

    NO HEAD-OF-LINE BLOCKING. One permanently-failing message must not stop every message
    behind it — that turns a single bad envelope into a total outage, the failure that makes
    people delete the queue and go back to fire-and-forget. Each entry is tried independently;
    failures stay queued for the next tick, successes are dropped.
    """
    path = outbox_path()
    rows = _read_jsonl(path)
    if not rows:
        return BoundaryOutcome.done(ref="idle", chars=0)

    kept, sent, failed, last_why = [], 0, 0, ""
    for row in rows[:limit]:
        # Each entry goes to ITS peer. One unreachable fleet must not strand another's
        # mail -- the head-of-line rule, applied ACROSS peers rather than only within a queue.
        out = push(row.get("msg") or {}, url=url, post=post, secret=secret,
                   peer=str(row.get("peer") or ""))
        if out.ok:
            sent += 1
            continue
        failed += 1
        last_why = out.why or ""
        row["attempts"] = int(row.get("attempts") or 0) + 1
        row["last_error"] = last_why[:300]
        kept.append(row)
    kept.extend(rows[limit:])
    _write_jsonl(path, kept)

    if failed and not sent:
        return BoundaryOutcome.failed(
            f"{failed} message(s) still queued, none delivered — RETAINED, not lost; they "
            f"replay on the next tick. Last error: {last_why[:200]}")
    if failed:
        return BoundaryOutcome.partially(
            f"delivered {sent}, retained {failed} for replay (last: {last_why[:120]})",
            ref="tick", chars=sent)
    return BoundaryOutcome.done(ref="tick", chars=sent)


# =============================================================================================
# THE INBOUND GATE (design §3.3) — the dangerous half, and the one that ships slowly
#
# verify() proves ONE thing: the sender holds the key. It does not prove who the message says
# it is from, and it does not prove the message is safe to act on. Three separate questions;
# v0.1 answered the first, correctly and no further.
#
# WHAT THIS GATE REFUSES TO DO, on purpose:
#   - it does not read `frm` from the payload (costume; provenance comes from the verified route)
#   - it does not put anything on the live bus (admitted mail is PARKED and drained deliberately,
#     so a remote sentence is never a thing that HAPPENED TO an agent)
#   - it does not accept a control verb in any costume
#   - it does not raise, ever: a listener that raises is a one-byte denial of service
# =============================================================================================

#: Last message admitted, for pins and for the drain verb's "what just arrived" line.
_LAST_ADMITTED: Dict[str, Any] = {}


def last_admitted() -> Dict[str, Any]:
    """The most recently admitted message, AS PARKED (provenance rewritten, content redacted)."""
    return dict(_LAST_ADMITTED)


def admitted_count(mid: str) -> int:
    """How many times a given id was actually parked. Idempotency is only real if it is
    countable — "we dedupe" is a claim; this is the measurement."""
    return sum(1 for r in _read_jsonl(inbox_path()) if str(r.get("id")) == str(mid))


def accept(envelope: Dict[str, str], *, secret: Optional[bytes] = None,
           peer: str = "", within_s: int = SKEW_WINDOW_S) -> BoundaryOutcome:
    """Admit (or refuse) one inbound envelope from the remote peer. NEVER RAISES.

    Checks run in order of cost: cheap cryptographic facts first, semantic judgement last, so
    a hostile flood is rejected before it reaches any parser we wrote.
    """
    if not isinstance(envelope, dict):
        return BoundaryOutcome.failed("inbound envelope is not an object — refused unread")

    body_b64 = str(envelope.get("body") or "")
    sig = str(envelope.get("sig") or "")

    # IDENTITY BY KEY, decided before anything else is believed. When no secret is injected,
    # every configured peer's key is tried and the one that VERIFIES names the sender. An
    # explicit `secret=` (drills, single-key callers) keeps the old path.
    resolved = ""
    if secret is None:
        resolved, key = resolve_peer(body_b64, sig, within_s=within_s)
        if not key:
            # Could be no keys at all, or a stranger's signature. Both are refusals, and the
            # wire cannot be told which -- that distinction is exactly the oracle we refuse
            # to be. The LOG separates them.
            if not any(_secret(str(r.get("inbound_secret_file") or INBOUND_KEY_FILE))
                       for r in peers()):
                return BoundaryOutcome.failed(
                    "no inbound secret for any configured peer — the bridge is "
                    "INERT-UNTIL-KEYED. An absent allowlist must not resolve to 'allow' (the "
                    "obvious sin) and must not resolve to a guess (discord_inbound's "
                    "refusal). Capture one: py agent_cli.py secret remote_bridge_inbound.key")
            return BoundaryOutcome.failed(
                "no configured peer's key verifies this envelope — refused. Identity here is "
                "decided by WHICH KEY SIGNED IT, so an unrecognised signature is an "
                "unrecognised sender, and an unrecognised sender is not admitted under a "
                "placeholder name. (Also fires on a stale replay outside the skew window.)")
    else:
        key = secret

    if not key:
        return BoundaryOutcome.failed(
            "no inbound secret — the bridge is INERT-UNTIL-KEYED. An absent allowlist must "
            "not resolve to 'allow' and must not resolve to a guess.")

    if not verify(body_b64, sig, key, within_s=within_s):
        return BoundaryOutcome.failed(
            "inbound envelope failed HMAC or replay-window verification — refused. This is "
            "the whole 'not everyone has access' gate: it fires on a forged signature, a "
            "wrong key, AND a captured envelope replayed later.")

    try:
        payload = json.loads(base64.b64decode(body_b64).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as e:                                        # noqa: BLE001
        return BoundaryOutcome.failed(
            f"inbound payload unreadable after a VALID signature ({type(e).__name__}) — "
            f"refused. A signed-but-malformed body means the peer's sender is broken, not "
            f"that we should improvise a reading of it.")

    kind = str(payload.get("kind") or "")
    if kind not in BRIDGE_KINDS:
        return BoundaryOutcome.failed(
            f"inbound kind {kind!r} is not on the bridge allowlist ({sorted(BRIDGE_KINDS)}) "
            f"— refused. Allowlist never denylist: a kind invented after this line was "
            f"written does not cross, and no control verb crosses in any costume.")

    # ---- provenance is ASSIGNED, never read: the payload's `frm` is the peer's costume ----
    # THE KEY WINS. `resolved` came from cryptography; `peer` is our launcher's opinion and
    # may only fill in when the key proved nothing (the injected-secret path). A flag that
    # could rename a peer the maths already identified would reintroduce, on our own side,
    # exactly the trust-the-label hole we refuse the sender.
    route = (resolved
             or peer
             or str((_config().get("peer") or {}).get("name") or "")
             or "unknown-peer").strip()
    parked = {
        "id": str(payload.get("id") or _stable_id(payload)),
        "frm": f"remote:{route}",
        "claimed_frm": str(payload.get("frm") or "?"),   # VISIBLE as data, never used to decide
        "kind": kind,
        "content": discord_bridge.redact(discord_bridge._content_str(payload.get("content"))),
        "sent_at": int(payload.get("sent_at") or 0),
        "admitted_at": int(time.time()),
    }

    path = inbox_path()
    rows = _read_jsonl(path)
    if any(str(r.get("id")) == parked["id"] for r in rows):
        _LAST_ADMITTED.clear()
        _LAST_ADMITTED.update(parked)
        return BoundaryOutcome.done(ref=parked["id"], chars=0)   # T116: point at the cached
    rows.append(parked)                                          # outcome, never vanish silently
    _write_jsonl(path, rows)
    _LAST_ADMITTED.clear()
    _LAST_ADMITTED.update(parked)
    return BoundaryOutcome.done(ref=parked["id"], chars=len(parked["content"]))
