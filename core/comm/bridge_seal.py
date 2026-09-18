"""bridge_seal — the sealed envelope and the chain, for a bridge that may pass through a midpoint.

Design: research/in-flight/bridge-midpoint-cache-2026-09-17/design.md (Daniil's rulings, §7).
Transport authority stays docs/library/design/remote-bifrost-bridge-design.md; this adds a layer
UNDER that design's guarantees and relaxes none of them.

WHY THIS EXISTS. The direct link's HMAC gives AUTHENTICITY and not CONFIDENTIALITY — the right trade
between two endpoints that already trust each other, and the wrong one the moment a third party holds
the message. A midpoint that can be read is a midpoint that must be trusted, and a midpoint that must
be trusted is a second place to compromise. So: it holds ciphertext it cannot read, signatures it
cannot forge, and a routing header it cannot edit.

THE HEADER IS THE SUBTLE HALF. A Box authenticates the BODY to its recipient and says nothing about
`to`, `seq` or `prev` — and those must stay outside the ciphertext, because the midpoint has to route
on them. A midpoint able to rewrite `seq` could erase a gap it caused, hiding exactly the loss the
chain exists to detect. Hence a detached Ed25519 signature over canonical(header) || ciphertext: the
field the midpoint most wants to touch is the one it provably cannot.

ONE KEY OUT-OF-BAND, NOT TWO. The sender's X25519 public key rides INSIDE the signed header, so a
peer only has to learn our Ed25519 VERIFY key by hand; everything else is self-describing and
tamper-evident. Substituting a seal key would break the signature, so trusting the header here costs
nothing we had not already staked on the verify key.

PURE BY CONSTRUCTION. seal/unseal take keys as arguments and read no config, no clock authority and
no network, so every pin runs offline (tests/test_bridge_seal_red.py). Chain is the only half that
touches disk, and it takes its path as an argument for the same reason.

WHAT THIS IS NOT. Not a replacement for the direct link: direct stays preferred, and a message that
goes direct is one no midpoint ever sees, metadata included.
"""
from __future__ import annotations

import base64
import json
import os
import struct
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from nacl import public, signing
from nacl.exceptions import BadSignatureError, CryptoError

from core.comm.remote_relay import BRIDGE_KINDS          # ONE allowlist; a copy is a future drift

ALG = "x25519-xsalsa20poly1305/ed25519-v1"
SKEW_WINDOW_S = 300                                       # the window the direct link already uses
RETIRE_AFTER_S = 30 * 24 * 3600                           # Daniil, 2026-09-17: "retire at 30 days"

# Padded PLAINTEXT sizes. The midpoint learns which bucket, never a length. Box adds a 16-byte
# Poly1305 tag and the nonce travels in the header, so the wire sizes are these + 16.
PAD_BUCKETS = (4096, 16384, 65536, 262144, 1048576)
PAD_BUCKETS_CT = tuple(b + 16 for b in PAD_BUCKETS)

_HEADER_FIELDS = ("v", "id", "to", "from", "seq", "prev",
                  "created_at", "expires_at", "alg", "nonce", "seal_pub")


class SealRefused(Exception):
    """A sealed envelope was refused. The message never says WHICH check failed to a remote caller:
    a door that explains itself precisely is an oracle. The log separates them; the wire does not."""


# ------------------------------------------------------------------------------------- identity
def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(str(text or "").encode("ascii"))


def generate_identity() -> Dict[str, str]:
    """A fleet's two keypairs: X25519 to seal to, Ed25519 to sign with. Base64, so an identity is
    JSON — and only the two PUBLIC halves ever cross to the peer."""
    sealer = public.PrivateKey.generate()
    signer = signing.SigningKey.generate()
    return {
        "alg": ALG,
        "seal_secret": _b64(bytes(sealer)),
        "seal_public": _b64(bytes(sealer.public_key)),
        "sign_secret": _b64(bytes(signer)),
        "verify_public": _b64(bytes(signer.verify_key)),
    }


def public_half(identity: Dict[str, str]) -> Dict[str, str]:
    """What you hand the peer: no secret, safe to paste into a message. Only `verify_public` must
    arrive intact — `seal_public` also rides signed in every envelope."""
    return {"alg": identity.get("alg", ALG),
            "seal_public": identity["seal_public"],
            "verify_public": identity["verify_public"]}


# ---------------------------------------------------------------------------------- the envelope
def _canon(header: Dict[str, Any]) -> bytes:
    """Canonical header bytes. Sender and verifier must agree byte-for-byte: fixed field set, sorted
    keys, no whitespace. A field outside the set cannot be signed, so a midpoint cannot smuggle one
    in and have it believed."""
    slim = {k: header[k] for k in _HEADER_FIELDS if k in header}
    return json.dumps(slim, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _pad(plain: bytes) -> bytes:
    """Length-prefix, then pad to a bucket. Reversible, and the true length lives INSIDE the seal."""
    body = struct.pack(">I", len(plain)) + plain
    for bucket in PAD_BUCKETS:
        if len(body) <= bucket:
            return body + b"\x00" * (bucket - len(body))
    raise SealRefused(f"body of {len(plain)} bytes exceeds the largest bucket ({PAD_BUCKETS[-1]}) — "
                      f"send it as a blob, not as a body")


def _unpad(padded: bytes) -> bytes:
    if len(padded) < 4:
        raise SealRefused("sealed body too short to carry its own length")
    (n,) = struct.unpack(">I", padded[:4])
    if n > len(padded) - 4:
        raise SealRefused("sealed body declares a length past its own end")
    return padded[4:4 + n]


def seal(inner: Dict[str, Any], *, sender: Dict[str, str], recipient_public: str,
         to: str, frm: str, seq: int, prev: str = "",
         created_at: Optional[int] = None, expires_at: Optional[int] = None) -> Dict[str, Any]:
    """Seal one inner message into a cache envelope. Pure.

    The kind allowlist applies HERE, before anything is sealed: moving `kind` inside the ciphertext
    hides it from the midpoint, it does not exempt it. No control verb crosses in any costume.
    """
    kind = str(inner.get("kind") or "")
    if kind not in BRIDGE_KINDS:
        raise SealRefused(f"kind {kind!r} is not on the bridge allowlist ({sorted(BRIDGE_KINDS)})")

    now = int(created_at if created_at is not None else time.time())
    nonce = os.urandom(public.Box.NONCE_SIZE)
    try:
        box = public.Box(public.PrivateKey(_unb64(sender["seal_secret"])),
                         public.PublicKey(_unb64(recipient_public)))
    except (CryptoError, ValueError, TypeError, KeyError) as e:
        raise SealRefused(f"cannot build a box for this pair ({type(e).__name__})") from e

    plain = json.dumps(inner, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ct = box.encrypt(_pad(plain), nonce).ciphertext        # the nonce rides in the header, not here

    header = {
        "v": 1,
        "id": str(inner.get("id") or ""),
        "to": str(to),
        "from": str(frm),
        "seq": int(seq),
        "prev": str(prev or ""),
        "created_at": now,
        "expires_at": int(expires_at if expires_at is not None else now + RETIRE_AFTER_S),
        "alg": ALG,
        "nonce": _b64(nonce),
        "seal_pub": sender["seal_public"],                 # signed, so it cannot be swapped
    }
    sig = signing.SigningKey(_unb64(sender["sign_secret"])).sign(_canon(header) + ct).signature
    return {**header, "ct": _b64(ct), "sig": _b64(sig)}


def unseal(envelope: Dict[str, Any], *, recipient: Dict[str, str], sender_public: str,
           now: Optional[int] = None, within_s: int = SKEW_WINDOW_S) -> Dict[str, Any]:
    """Verify and open one envelope; return the inner message. Pure. Raises SealRefused uniformly.

    `sender_public` is the peer's Ed25519 VERIFY key — the one thing that must arrive out-of-band.

    Order is cheapest-first and deliberate: the signature is checked before the box is opened, so a
    hostile flood is refused before any decryption work and before a parser of ours sees a byte.
    """
    if not isinstance(envelope, dict):
        raise SealRefused("envelope is not an object")
    if str(envelope.get("alg") or "") != ALG:
        raise SealRefused("unknown algorithm suite")

    try:
        ct = _unb64(envelope.get("ct", ""))
        sig = _unb64(envelope.get("sig", ""))
    except Exception as e:                                       # noqa: BLE001
        raise SealRefused(f"envelope fields are not base64 ({type(e).__name__})") from e

    # 1. THE HEADER AND THE CIPHERTEXT TOGETHER, exactly as the sender signed them. This is what
    #    stops a midpoint editing seq/prev/to/from — the fields it can read and must not change.
    try:
        signing.VerifyKey(_unb64(sender_public)).verify(_canon(envelope) + ct, sig)
    except (BadSignatureError, CryptoError, ValueError, TypeError) as e:
        raise SealRefused("signature does not verify over this header and ciphertext") from e

    # 2. replay window, checked against the now-trusted created_at
    stamp = int(envelope.get("created_at") or 0)
    if abs(int(now if now is not None else time.time()) - stamp) > within_s:
        raise SealRefused("created_at is outside the replay window")

    # 3. only now decrypt. The sender's seal key came from the signed header, so trusting it here
    #    stakes nothing beyond the verify key we already trusted.
    try:
        box = public.Box(public.PrivateKey(_unb64(recipient["seal_secret"])),
                         public.PublicKey(_unb64(envelope.get("seal_pub", ""))))
        plain = _unpad(box.decrypt(ct, _unb64(envelope.get("nonce", ""))))
    except SealRefused:
        raise
    except Exception as e:                                       # noqa: BLE001
        raise SealRefused(f"sealed body did not open ({type(e).__name__})") from e

    try:
        inner = json.loads(plain.decode("utf-8"))
        if not isinstance(inner, dict):
            raise ValueError("inner is not an object")
    except Exception as e:                                       # noqa: BLE001
        raise SealRefused(f"inner message unreadable after a VALID seal ({type(e).__name__})") from e

    kind = str(inner.get("kind") or "")
    if kind not in BRIDGE_KINDS:
        raise SealRefused(f"inner kind {kind!r} is not on the bridge allowlist")
    return inner


def is_retired(envelope: Dict[str, Any], *, now: Optional[int] = None) -> bool:
    """Past its expires_at. Retirement is NOT deletion (Daniil's ruling): the midpoint keeps the
    tombstone — id, routing, seq, prev — so a retired message stays visible to gap detection. Only
    the BODY moves home."""
    return int(envelope.get("expires_at") or 0) <= int(now if now is not None else time.time())


def tombstone(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """What the midpoint keeps once a body has been retired to its owner's local storage. The chain
    survives; the content does not live here any more."""
    keep = ("v", "id", "to", "from", "seq", "prev", "created_at", "expires_at")
    return {**{k: envelope[k] for k in keep if k in envelope}, "retired": True}


# ------------------------------------------------------------------------------------- the chain
class Chain:
    """Per-pair sequence numbers and the id chain: the half that makes a LOSS VISIBLE.

    On 2026-09-04 our door shut and thirteen days of the peer's mail was refused at the wire. Both
    fleets' machinery behaved correctly and neither could tell anything was missing, because absence
    has no shape. A monotonic seq per (peer, direction) gives absence a shape: "I am missing 7".

    State is small and local, so it is a JSON file written atomically rather than anything grander.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._state = self._load()

    # ---- persistence
    def _load(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("out", {})
                data.setdefault("in", {})
                return data
        except (OSError, ValueError):
            pass
        return {"out": {}, "in": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".chain-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh, sort_keys=True, indent=1)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ---- outbound
    def next_out(self, peer: str) -> Dict[str, Any]:
        """Claim the next seq for this peer and name the previous message. Persisted IMMEDIATELY:
        a counter that resets on restart re-uses a seq, and a re-used seq is a gap that cannot be
        distinguished from a duplicate."""
        row = self._state["out"].setdefault(str(peer), {"seq": 0, "last_id": ""})
        row["seq"] = int(row.get("seq") or 0) + 1
        self._save()
        return {"seq": row["seq"], "prev": str(row.get("last_id") or "")}

    def sent(self, peer: str, mid: str) -> None:
        """Record what actually went out, so the NEXT message can chain to it."""
        row = self._state["out"].setdefault(str(peer), {"seq": 0, "last_id": ""})
        row["last_id"] = str(mid)
        self._save()

    # ---- inbound
    def observe_in(self, peer: str, *, seq: int, mid: str, prev: str = "") -> List[int]:
        """Record an arrival; return the sequence numbers this arrival newly reveals as MISSING.

        A duplicate reveals nothing and must not advance anything (redelivery is normal and cheap —
        at-least-once is the delivery contract). A late arrival CLOSES a gap rather than opening one.
        """
        row = self._state["in"].setdefault(str(peer), {"seen": [], "last_id": ""})
        seen = set(int(s) for s in row.get("seen") or [])
        seq = int(seq)
        if seq in seen:
            return []
        highest = max(seen) if seen else 0
        newly_missing = [s for s in range(highest + 1, seq) if s not in seen] if seq > highest else []
        seen.add(seq)
        row["seen"] = sorted(seen)
        row["last_id"] = str(mid)
        self._save()
        return newly_missing

    def missing(self, peer: str) -> List[int]:
        """Everything below the high-water mark that has still never arrived."""
        seen = set(int(s) for s in (self._state["in"].get(str(peer)) or {}).get("seen") or [])
        if not seen:
            return []
        return [s for s in range(1, max(seen)) if s not in seen]

    def high_water(self, peer: str) -> int:
        seen = [int(s) for s in (self._state["in"].get(str(peer)) or {}).get("seen") or []]
        return max(seen) if seen else 0
