"""bridge_seal — the sealed envelope and the chain, for a bridge that may pass through a midpoint.

Design: research/in-flight/bridge-midpoint-cache-2026-09-17/design.md (Daniil's rulings, §7).
Transport authority stays docs/library/design/remote-bifrost-bridge-design.md; this adds a layer
UNDER that design's guarantees and relaxes none of them.

WHY THIS EXISTS. The direct link's HMAC gives AUTHENTICITY and not CONFIDENTIALITY — the right trade
between two endpoints that already trust each other, and the wrong one the moment a third party holds
the message. A midpoint that can be read must be trusted, and a midpoint that must be trusted is a
second place to compromise. So it holds ciphertext it cannot read, signatures it cannot forge, and a
routing header it cannot edit.

THE HEADER IS THE SUBTLE HALF. A Box authenticates the BODY to its recipient and says nothing about
`to`, `seq` or `prev` — and those must stay outside the ciphertext, because the midpoint routes on
them. A midpoint able to rewrite `seq` could erase a gap it caused. Hence a detached Ed25519
signature over canonical(header) || ciphertext.

AND THE TOMBSTONE IS THE HALF THAT NEARLY UNDID IT. Retirement keeps a tombstone so the chain still
sees a retired message; the first implementation stripped the signature when it did so, which handed
the midpoint the exact power the header signature exists to deny — withhold three messages, deposit
three invented tombstones, and the gap disappears. Found by adversarial review 2026-09-17, before
anything was wired. So every envelope now carries a SECOND detached signature over the tombstone
fields alone (`tsig`), which survives the body and lets a tombstone prove itself. Nothing unverified
may reach the chain: `Chain.observe_in` refuses a record not marked verified, so the mistake is hard
to make rather than merely documented.

FORWARD SECRECY, adopted from Chronos on Serge's fleet (2026-09-17): the sender's X25519 key is
EPHEMERAL, generated per message, and rides in the signed header. Identity is carried by the Ed25519
signature, so the seal key never needed to be long-lived; making it per-message means a later
compromise of a long-term key cannot open yesterday's traffic. Never cache `seal_pub` as an identity.

PURE BY CONSTRUCTION. seal/unseal take keys as arguments and read no config, no clock authority and
no network, so every pin runs offline. Chain is the only half that touches disk, and it takes its
path as an argument for the same reason.
"""
from __future__ import annotations

import base64
import binascii
import errno
import json
import math
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
WIRE_V = 1
SKEW_WINDOW_S = 300                                       # the window the direct link already uses
RETIRE_AFTER_S = 30 * 24 * 3600                           # Daniil, 2026-09-17: "retire at 30 days"
MAX_SEQ_JUMP = 10_000                                     # a further jump is refused, never materialised

PAD_BUCKETS = (4096, 16384, 65536, 262144, 1048576)
PAD_BUCKETS_CT = tuple(b + 16 for b in PAD_BUCKETS)       # Box adds a 16-byte Poly1305 tag

_HEADER_FIELDS = ("v", "id", "to", "from", "seq", "prev", "epoch",
                  "created_at", "expires_at", "alg", "nonce", "seal_pub")
_TOMB_FIELDS = ("v", "id", "to", "from", "seq", "prev", "epoch", "created_at", "expires_at")
_ENVELOPE_KEYS = frozenset(_HEADER_FIELDS) | {"ct", "sig", "tsig"}
_TOMB_KEYS = frozenset(_TOMB_FIELDS) | {"tsig", "retired"}
_STR_FIELDS = ("id", "to", "from", "prev", "epoch", "alg", "nonce", "seal_pub")


class SealRefused(Exception):
    """A sealed envelope was refused. The message never says WHICH check failed to a remote caller:
    a door that explains itself precisely is an oracle. The log separates them; the wire does not."""


class ChainCorrupt(Exception):
    """The chain file exists and cannot be trusted. Distinct from absent, ON PURPOSE: absent is a
    fresh start, damaged is a refusal. The first implementation swallowed both into an empty state,
    which made the file whose job is making loss VISIBLE fail closed to 'no loss known'."""


# ------------------------------------------------------------------------------------- primitives
def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    """STRICT. Without validate=True, b64decode silently drops non-alphabet bytes, so a midpoint can
    respell `ct` (whitespace, stray punctuation) and still have it verify — breaking byte-identity
    and dedupe at every hop that trusts the string."""
    if not isinstance(text, str):
        raise SealRefused("expected a base64 string")
    try:
        return base64.b64decode(text.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError) as e:
        raise SealRefused("field is not canonical base64") from e


def _as_int(value: Any, *, what: str) -> int:
    """Fail-closed integer. Everything that reaches this comes off the wire or off a midpoint, where
    "abc", Infinity, NaN, [1] and {} all arrive as easily as 7 — and each of those raised a DIFFERENT
    uncaught type before, out of a door whose whole contract is to refuse uniformly."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SealRefused(f"{what} is not a number")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value) or value != int(value):
            raise SealRefused(f"{what} is not a whole finite number")
        value = int(value)
    if not (-(2 ** 62) < int(value) < 2 ** 62):
        raise SealRefused(f"{what} is out of range")
    return int(value)


def _dumps(obj: Any, *, what: str) -> bytes:
    """Canonical JSON with NO default= coercion. `default=str` shipped a set as the string
    "{1, 2, 3}" with no error on either side — corruption wearing the costume of tolerance."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise SealRefused(f"{what} is not JSON-serialisable") from e


# -------------------------------------------------------------------------------------- identity
def generate_identity() -> Dict[str, str]:
    """A fleet's long-term keys: X25519 to RECEIVE seals at, Ed25519 to sign with. Sending uses an
    ephemeral X25519 per message, so this seal key only ever opens, never seals."""
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
    """What you hand the peer. Only `verify_public` must arrive intact out-of-band; `seal_public` is
    where they seal TO you."""
    try:
        return {"alg": identity.get("alg", ALG),
                "seal_public": identity["seal_public"],
                "verify_public": identity["verify_public"]}
    except (KeyError, TypeError) as e:
        raise SealRefused("identity is missing its public half") from e


# --------------------------------------------------------------------------------- the envelope
def _canon(header: Dict[str, Any], fields) -> bytes:
    """Canonical bytes over a FIXED field set: sender and verifier must agree byte-for-byte, and a
    field outside the set cannot be signed — so a midpoint cannot smuggle one in and have it
    believed. (Adding one is separately REFUSED at the door; see _check_keys.)"""
    missing = [f for f in fields if f not in header]
    if missing:
        raise SealRefused(f"header is missing signed field(s): {','.join(missing)}")
    return _dumps({k: header[k] for k in fields}, what="header")


def _check_keys(envelope: Dict[str, Any], allowed: frozenset) -> None:
    extra = set(envelope) - allowed
    if extra:
        raise SealRefused(f"unsigned field(s) present: {','.join(sorted(extra))}")


def _pad(plain: bytes) -> bytes:
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
         to: str, frm: str, seq: int, prev: str = "", epoch: str = "",
         created_at: Optional[int] = None, expires_at: Optional[int] = None) -> Dict[str, Any]:
    """Seal one inner message into a cache envelope. Pure. Raises only SealRefused.

    The kind allowlist applies HERE: moving `kind` inside the ciphertext hides it from the midpoint,
    it does not exempt it. No control verb crosses in any costume.
    """
    if not isinstance(inner, dict):
        raise SealRefused("inner message is not an object")
    if str(inner.get("kind") or "") not in BRIDGE_KINDS:
        raise SealRefused(f"kind is not on the bridge allowlist ({sorted(BRIDGE_KINDS)})")

    now = _as_int(created_at if created_at is not None else int(time.time()), what="created_at")
    expiry = _as_int(expires_at if expires_at is not None else now + RETIRE_AFTER_S,
                     what="expires_at")
    seq_i = _as_int(seq, what="seq")

    try:
        signer = signing.SigningKey(_unb64(sender["sign_secret"]))
        recipient_key = public.PublicKey(_unb64(recipient_public))
    except SealRefused:
        raise
    except (KeyError, TypeError) as e:
        raise SealRefused("sender identity is incomplete") from e
    except (CryptoError, ValueError) as e:
        raise SealRefused(f"a key is unusable ({type(e).__name__})") from e

    ephemeral = public.PrivateKey.generate()               # forward secrecy: per-message, never kept
    nonce = os.urandom(public.Box.NONCE_SIZE)
    plain = _dumps(inner, what="inner message")
    try:
        ct = public.Box(ephemeral, recipient_key).encrypt(_pad(plain), nonce).ciphertext
    except SealRefused:
        raise
    except (CryptoError, ValueError, TypeError) as e:
        raise SealRefused(f"sealing failed ({type(e).__name__})") from e

    header = {
        "v": WIRE_V,
        "id": str(inner.get("id") or ""),
        "to": str(to),
        "from": str(frm),
        "seq": seq_i,
        "prev": str(prev or ""),
        "epoch": str(epoch or ""),
        "created_at": now,
        "expires_at": expiry,
        "alg": ALG,
        "nonce": _b64(nonce),
        "seal_pub": _b64(bytes(ephemeral.public_key)),
    }
    return {**header,
            "ct": _b64(ct),
            "sig": _b64(signer.sign(_canon(header, _HEADER_FIELDS) + ct).signature),
            # THE TOMBSTONE SIGNATURE: over the routing fields ALONE, so it survives retirement.
            "tsig": _b64(signer.sign(_canon(header, _TOMB_FIELDS)).signature)}


def _verify_schema(env: Dict[str, Any]) -> None:
    """After the signature passes, the FIELDS still have to mean something. A peer can sign a header
    whose `seq` is "7", whose `to` is [], or whose `id` is absent entirely — all of which verified
    cleanly before, and one of which reached the chain as observe_in(seq=None)."""
    if _as_int(env.get("v"), what="v") != WIRE_V:
        raise SealRefused("unknown wire version")
    if str(env.get("alg") or "") != ALG:
        raise SealRefused("unknown algorithm suite")
    for f in _STR_FIELDS:
        if not isinstance(env.get(f), str):
            raise SealRefused(f"{f} is not a string")
    if not env.get("id"):
        raise SealRefused("id is empty")
    _as_int(env.get("seq"), what="seq")
    _as_int(env.get("created_at"), what="created_at")
    _as_int(env.get("expires_at"), what="expires_at")


def unseal(envelope: Dict[str, Any], *, recipient: Dict[str, str], sender_public: str,
           me: str = "", now: Optional[int] = None, within_s: int = SKEW_WINDOW_S) -> Dict[str, Any]:
    """Verify and open one envelope; return the inner message. Pure. Raises only SealRefused.

    `sender_public` is the peer's Ed25519 VERIFY key — the one thing that must arrive out-of-band.
    `me` is this fleet's routing name; an envelope addressed elsewhere is refused rather than opened.

    Cheapest-first and deliberate: the signature is checked before the box is opened, so a hostile
    flood is refused before any decryption work and before a parser of ours sees a byte.
    """
    if not isinstance(envelope, dict):
        raise SealRefused("envelope is not an object")
    _check_keys(envelope, _ENVELOPE_KEYS)
    if str(envelope.get("alg") or "") != ALG:
        raise SealRefused("unknown algorithm suite")

    ct = _unb64(envelope.get("ct", ""))
    sig = _unb64(envelope.get("sig", ""))

    try:
        signing.VerifyKey(_unb64(sender_public)).verify(_canon(envelope, _HEADER_FIELDS) + ct, sig)
    except SealRefused:
        raise
    except (BadSignatureError, CryptoError, ValueError, TypeError) as e:
        raise SealRefused("signature does not verify over this header and ciphertext") from e

    _verify_schema(envelope)
    if me and str(envelope.get("to")) != str(me):
        raise SealRefused("envelope is addressed to another fleet")

    clock = _as_int(now if now is not None else int(time.time()), what="now")
    if abs(clock - _as_int(envelope.get("created_at"), what="created_at")) > within_s:
        raise SealRefused("created_at is outside the replay window")
    if clock >= _as_int(envelope.get("expires_at"), what="expires_at"):
        raise SealRefused("envelope has expired — its body should have been retired")

    try:
        box = public.Box(public.PrivateKey(_unb64(recipient["seal_secret"])),
                         public.PublicKey(_unb64(envelope["seal_pub"])))
        plain = _unpad(box.decrypt(ct, _unb64(envelope["nonce"])))
    except SealRefused:
        raise
    except (KeyError, TypeError) as e:
        raise SealRefused("recipient identity is incomplete") from e
    except Exception as e:                                       # noqa: BLE001
        raise SealRefused(f"sealed body did not open ({type(e).__name__})") from e

    try:
        inner = json.loads(plain.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise SealRefused("inner message unreadable after a VALID seal") from e
    if not isinstance(inner, dict):
        raise SealRefused("inner message is not an object")
    if str(inner.get("kind") or "") not in BRIDGE_KINDS:
        raise SealRefused("inner kind is not on the bridge allowlist")
    return inner


# ------------------------------------------------------------------------------------ retirement
def is_retired(envelope: Dict[str, Any], *, now: Optional[int] = None) -> bool:
    """Past its expires_at. Never raises: it is CALLED ON TOMBSTONES, i.e. on data a midpoint
    controls, so a malformed field must be an answer and not an exception."""
    if not isinstance(envelope, dict):
        return False
    try:
        return _as_int(envelope.get("expires_at"), what="expires_at") <= _as_int(
            now if now is not None else int(time.time()), what="now")
    except SealRefused:
        return False


def tombstone(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """What the midpoint keeps once a body has been retired to its owner's local storage: the chain
    survives, the content does not live here any more — and `tsig` comes with it, so the record can
    still prove it was ours."""
    if not isinstance(envelope, dict) or "tsig" not in envelope:
        raise SealRefused("cannot retire an envelope that carries no tombstone signature")
    return {**{k: envelope[k] for k in _TOMB_FIELDS if k in envelope},
            "tsig": envelope["tsig"], "retired": True}


def verify_tombstone(tomb: Dict[str, Any], *, sender_public: str) -> Dict[str, Any]:
    """Prove a tombstone was minted by the sender, after its body is gone. THE fix for the review's
    critical: without this, a midpoint invents tombstones to paper over messages it withheld, and
    gap detection reports clean."""
    if not isinstance(tomb, dict):
        raise SealRefused("tombstone is not an object")
    _check_keys(tomb, _TOMB_KEYS)
    tsig = _unb64(tomb.get("tsig", ""))
    try:
        signing.VerifyKey(_unb64(sender_public)).verify(_canon(tomb, _TOMB_FIELDS), tsig)
    except SealRefused:
        raise
    except (BadSignatureError, CryptoError, ValueError, TypeError) as e:
        raise SealRefused("tombstone signature does not verify") from e
    _as_int(tomb.get("seq"), what="seq")
    return tomb


# ------------------------------------------------------------------------------------- the chain
class _FileLock:
    """One advisory lock around the whole read-modify-write. Without it two seats claimed the same
    seq (measured: 561 duplicates in 800 claims) and os.replace raced itself into WinError 5 — in a
    house whose entire model is concurrent agents."""

    def __init__(self, path: Path, timeout: float = 10.0):
        self.path = Path(str(path) + ".lock")
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() > deadline:
                    try:                                  # a stale lock must not wedge the fleet
                        if time.time() - self.path.stat().st_mtime > self.timeout:
                            os.unlink(str(self.path))
                            continue
                    except OSError:
                        pass
                    raise ChainCorrupt(f"could not take the chain lock at {self.path}")
                time.sleep(0.01)
            except OSError as e:
                if e.errno == errno.EACCES:
                    time.sleep(0.01)
                    continue
                raise

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
        try:
            os.unlink(str(self.path))
        except OSError:
            pass
        return False


class Chain:
    """Per-pair sequence numbers and the id chain: the half that makes a LOSS VISIBLE.

    On 2026-09-04 our door shut and thirteen days of the peer's mail was refused at the wire. Both
    fleets' machinery behaved correctly and neither could tell anything was missing, because absence
    has no shape. A monotonic seq per (peer, direction) gives absence a shape.

    State is bounded BY CONSTRUCTION: a high-water mark plus the holes below it, never the set of
    everything seen. The first version kept every seq forever, so 20k messages cost 82 s and 229 KB,
    and one message with an absurd seq left a hundred thousand phantom gaps that `missing()` rebuilt
    on every call, for ever.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._read()                                      # fail fast on a damaged file

    # ---- persistence
    def _read(self) -> Dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"out": {}, "in": {}}
        except OSError as e:
            raise ChainCorrupt(f"chain file unreadable: {e}") from e
        try:
            data = json.loads(raw)
        except ValueError as e:
            raise ChainCorrupt("chain file is not valid JSON — refusing to start from a blank "
                               "state, which would silently re-use sequence numbers") from e
        if not isinstance(data, dict) or not isinstance(data.get("out", {}), dict) \
                or not isinstance(data.get("in", {}), dict):
            raise ChainCorrupt("chain file has the wrong shape")
        data.setdefault("out", {})
        data.setdefault("in", {})
        return data

    def _write(self, state: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".chain-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(state, fh, sort_keys=True, indent=1)
            for attempt in range(50):                     # Windows: the target may be briefly open
                try:
                    os.replace(tmp, self.path)
                    return
                except PermissionError:
                    if attempt == 49:
                        raise
                    time.sleep(0.01)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ---- outbound
    def next_out(self, peer: str) -> Dict[str, Any]:
        """Claim the next seq for this peer. Persisted under the lock and re-read inside it, so two
        processes cannot claim the same number: a re-used seq is a gap indistinguishable from a
        duplicate, which is the one confusion this whole class exists to prevent."""
        with _FileLock(self.path):
            state = self._read()
            row = state["out"].setdefault(str(peer), {"seq": 0, "last_id": "", "epoch": ""})
            row["seq"] = _as_int(row.get("seq") or 0, what="stored seq") + 1
            self._write(state)
            return {"seq": row["seq"], "prev": str(row.get("last_id") or ""),
                    "epoch": str(row.get("epoch") or "")}

    def sent(self, peer: str, mid: str) -> None:
        with _FileLock(self.path):
            state = self._read()
            row = state["out"].setdefault(str(peer), {"seq": 0, "last_id": "", "epoch": ""})
            row["last_id"] = str(mid)
            self._write(state)

    def set_epoch(self, peer: str, epoch: str) -> None:
        """A sender that loses its chain file must announce a NEW epoch. Without one it reissues
        1..N and the receiver swallows every message as a duplicate — the original silence,
        reproduced by the machinery built to prevent it."""
        with _FileLock(self.path):
            state = self._read()
            state["out"].setdefault(str(peer), {"seq": 0, "last_id": "", "epoch": ""})
            state["out"][str(peer)]["epoch"] = str(epoch)
            self._write(state)

    # ---- inbound
    def observe_in(self, peer: str, *, seq: Any, mid: str, prev: str = "", epoch: str = "",
                   verified: bool = False) -> Dict[str, Any]:
        """Record an arrival; report what it reveals.

        `verified` is REQUIRED to be true and defaults to False on purpose: the caller must have
        checked a signature (unseal, or verify_tombstone for a retired record) before the chain will
        believe routing data. An unverified tombstone is exactly how the review broke this.

        Returns {missing, chain_broken, epoch_changed}. A duplicate reveals nothing and advances
        nothing — at-least-once redelivery is the contract and must stay cheap. A late arrival CLOSES
        a gap rather than opening one.
        """
        if not verified:
            raise SealRefused("refusing an unverified record: routing data must carry a signature "
                              "that has already been checked before it reaches the chain")
        seq_i = _as_int(seq, what="seq")
        if seq_i < 1:
            raise SealRefused("seq must be positive")

        with _FileLock(self.path):
            state = self._read()
            row = state["in"].setdefault(str(peer),
                                         {"high_water": 0, "holes": [], "last_id": "", "epoch": ""})
            known_epoch = str(row.get("epoch") or "")
            epoch_changed = bool(epoch) and bool(known_epoch) and str(epoch) != known_epoch
            if epoch_changed:                              # a new chain: start clean, loudly
                row.update({"high_water": 0, "holes": [], "last_id": ""})
            row["epoch"] = str(epoch or known_epoch)

            high = _as_int(row.get("high_water") or 0, what="stored high_water")
            holes = set(_as_int(h, what="stored hole") for h in (row.get("holes") or []))
            newly_missing: List[int] = []
            chain_broken = False

            if seq_i > high:
                if seq_i - high > MAX_SEQ_JUMP:
                    raise SealRefused(
                        f"seq jumps {seq_i - high} past the high-water mark (cap {MAX_SEQ_JUMP}) — "
                        f"refused rather than materialised as that many phantom gaps")
                newly_missing = list(range(high + 1, seq_i))
                holes.update(newly_missing)
                last = str(row.get("last_id") or "")
                if last and not newly_missing and not epoch_changed and str(prev or "") != last:
                    chain_broken = True                    # prev is CHECKED, not decoration
                row["high_water"] = seq_i
                row["last_id"] = str(mid)
            else:
                holes.discard(seq_i)                       # a late arrival closes its own gap

            row["holes"] = sorted(holes)
            self._write(state)
            return {"missing": newly_missing, "chain_broken": chain_broken,
                    "epoch_changed": epoch_changed}

    def missing(self, peer: str) -> List[int]:
        """Everything below the high-water mark that has still never arrived. O(holes), not O(seq)."""
        row = self._read()["in"].get(str(peer)) or {}
        return sorted(_as_int(h, what="stored hole") for h in (row.get("holes") or []))

    def high_water(self, peer: str) -> int:
        row = self._read()["in"].get(str(peer)) or {}
        return _as_int(row.get("high_water") or 0, what="stored high_water")
