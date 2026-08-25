"""Pins: file transport across the bridge — announce a REF, fetch the BYTES separately.

Daniil, 2026-08-25 (home, after the night the keys kept getting mangled): "can we build a file
transport system that would enable us to send files to each other quickly without having to
rely on discord".

WIRED, NOT INVENTED. The lossless-pointer primitive already exists and has never had a caller:
core/comm/blobs.py BlobStore + bus.py file_part/media_part/Part.resolve. Lesson
`lossless_pointer_part_built_not_wired` says it in as many words — "wire it instead of
building a second one" — so this adds a transport for refs, not a second staging mechanism.

THE SHAPE: put the file in the blob store, send a NORMAL bridge message carrying only the ref,
and let the peer fetch the bytes when it wants them. Three properties fall out, and each one
answers something that actually hurt tonight:

  CONTENT ADDRESSING IS THE INTEGRITY CHECK. A ref is `blob:<sha256>`. If the bytes you
  received hash to the ref you were given, they are the bytes that were sent — full stop. No
  fingerprint ceremony, no "compare these twelve characters", no silent truncation. Two key
  pastes were mangled tonight and both were caught only because someone thought to compare a
  hash by hand; here the comparison is the addressing scheme.

  PATH TRAVERSAL IS STRUCTURALLY IMPOSSIBLE. The request names a HASH, never a path, so there
  is no `../` to reject and no allowlist to get wrong. You can only fetch a blob whose digest
  you already hold, which also means the endpoint cannot be enumerated.

  THE MESSAGE STAYS SMALL. A 1.5MB corpus does not need a 1.5MB message, so the 256KB body cap
  stops being a constraint on what we can send and becomes a constraint only on what we can
  say about it.

WHAT THIS DELIBERATELY DOES NOT DO: it does not push bytes at a peer. The peer is TOLD a ref
exists and pulls it if it wants it — the same parked-not-bussed stance the inbound gate takes
with messages, applied to files. A transport that writes to your disk because someone else
decided to send something is a different and much worse thing than one that offers.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR          # noqa: E402
from core.comm.blobs import BlobStore             # noqa: E402
from scripts import remote_bridge_listener as L   # noqa: E402

KEY = b"blob-transport-test-key-aaaaaaaa"


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.setenv("AKASHIC_BLOB_DIR", str(tmp_path / "blobs"))
    RR._reset_cache()
    yield
    RR._reset_cache()


def signed(payload: dict, secret=KEY) -> bytes:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return json.dumps({"body": base64.b64encode(body).decode(),
                       "sig": RR.sign(body, secret)}).encode()


def blob_request(ref: str, secret=KEY, sent_at=None) -> bytes:
    return signed({"v": 1, "ref": ref,
                   "sent_at": int(sent_at if sent_at is not None else time.time())}, secret)


# ------------------------------------------------------------------ the door
def test_a_valid_signed_request_returns_the_exact_bytes(tmp_path):
    store = BlobStore(str(tmp_path / "blobs"))
    data = b"corpus bytes, 1083 lessons pretend" * 40
    ref = store.put(data)
    status, body, _log = L.handle_blob("POST", "/blob", blob_request(ref), secret=KEY, blobs=store)
    assert status == 200, f"a legitimate fetch failed: {body}"
    assert body == data, "returned bytes are not the stored bytes"


def test_the_ref_is_the_integrity_check(tmp_path):
    """The property that retires fingerprint ceremony: verifying a transfer is recomputing the
    hash, and a truncated or mangled body simply is not that ref any more."""
    store = BlobStore(str(tmp_path / "blobs"))
    data = b"x" * 5000
    ref = store.put(data)
    _s, got, _l = L.handle_blob("POST", "/blob", blob_request(ref), secret=KEY, blobs=store)
    assert RR.blob_matches_ref(got, ref), "the returned bytes did not hash to their own ref"
    assert not RR.blob_matches_ref(got[:-1], ref), "a truncated body passed verification"


def test_an_unsigned_or_forged_request_is_refused(tmp_path):
    store = BlobStore(str(tmp_path / "blobs"))
    ref = store.put(b"secret-ish")
    s1, b1, _ = L.handle_blob("POST", "/blob", blob_request(ref, secret=b"wrong"), secret=KEY, blobs=store)
    assert s1 == 400 and b1 == L.FLAT_REFUSAL
    s2, b2, _ = L.handle_blob("POST", "/blob", b"{}", secret=KEY)
    assert s2 == 400 and b2 == L.FLAT_REFUSAL


def test_a_stale_request_is_refused(tmp_path):
    """Same replay window as the message gate. A captured fetch request must not be valid
    forever, or a leaked one is a permanent read handle."""
    store = BlobStore(str(tmp_path / "blobs"))
    ref = store.put(b"data")
    old = blob_request(ref, sent_at=int(time.time()) - 99_999)
    status, body, _ = L.handle_blob("POST", "/blob", old, secret=KEY, blobs=store)
    assert status == 400 and body == L.FLAT_REFUSAL


def test_an_unknown_ref_reveals_nothing(tmp_path):
    """The refusal must not distinguish 'no such blob' from 'not allowed' — otherwise the
    endpoint becomes an oracle for what this fleet holds, which is exactly the property the
    message gate's flat refusal exists to deny."""
    missing = "blob:" + "0" * 32
    status, body, _ = L.handle_blob("POST", "/blob", blob_request(missing), secret=KEY)
    assert body == L.FLAT_REFUSAL, "an unknown ref returned something distinguishable"


@pytest.mark.parametrize("hostile", [
    "blob:../../../../etc/passwd",
    "blob:..\\..\\windows\\system32\\config\\sam",
    "../../secrets/remote_bridge_inbound.key",
    "blob:" + "a" * 5000,
    "",
])
def test_no_request_can_escape_the_blob_store(hostile, tmp_path):
    """Structurally impossible rather than defended-against: the request names a HASH. There
    is no path to sanitise, so there is no sanitiser to get wrong."""
    status, body, _ = L.handle_blob("POST", "/blob", blob_request(hostile), secret=KEY)
    assert status in (400, 404), f"hostile ref {hostile!r} got status {status}"
    assert body == L.FLAT_REFUSAL


def test_the_blob_door_never_raises(tmp_path):
    for junk in (b"", b"\x00\xff", b"[]", b'{"body":5,"sig":[]}', b"not json"):
        try:
            L.handle_blob("POST", "/blob", junk, secret=KEY)
        except Exception as e:                                    # noqa: BLE001
            pytest.fail(f"blob door raised on {junk[:16]!r}: {type(e).__name__}: {e}")


def test_wrong_method_and_path_are_refused(tmp_path):
    assert L.handle_blob("GET", "/blob", b"", secret=KEY)[0] == 405
    assert L.handle_blob("POST", "/blobs", b"", secret=KEY)[0] == 404


# ------------------------------------------------------------------ the sender side
def test_send_file_announces_a_ref_and_never_the_bytes(tmp_path):
    """A 1.5MB file must not become a 1.5MB message. The announce carries a pointer; the peer
    pulls the payload only if it wants it — parked-not-bussed, applied to files."""
    f = tmp_path / "corpus.json"
    f.write_bytes(b"y" * 300_000)
    ann = RR.file_announcement(f, blobs=BlobStore(str(tmp_path / "blobs")))
    assert ann["ref"].startswith("blob:")
    assert ann["name"] == "corpus.json"
    assert ann["bytes"] == 300_000
    wire = json.dumps(ann).encode()
    assert len(wire) < 2000, f"the announcement itself is {len(wire)}B — it carries payload"


# ------------------------------------------------------------------ the pointer needs a DOOR
def test_the_announcement_advertises_a_REAL_retrieval_verb(tmp_path):
    """Lesson a_pointer_needs_a_door_on_every_surface_that_reads_it: "a pointer nobody can
    follow is WORSE than a clip that admits the loss, because it looks like the data is
    reachable." So the notice must carry a retrieval command, and that command must be a thing
    that actually exists -- parsed out of our own notice, not asserted from memory."""
    f = tmp_path / "corpus.json"
    f.write_bytes(b"z" * 2048)
    ann = RR.file_announcement(f, blobs=BlobStore(str(tmp_path / "blobs")))
    how = ann.get("fetch_with", "")
    assert how, "the announcement carries a ref with no way to follow it"
    assert ann["ref"] in how, "the advertised command does not name the ref it retrieves"
    script = how.split()[1] if how.split()[0] in ("py", "python") else how.split()[0]
    assert (REPO / script).exists(), (
        f"the announcement advertises {script!r}, which does not exist -- a retrieval command "
        f"that is not a real entry point is the pointer-with-no-door defect exactly")


def test_every_surface_that_shows_a_ref_also_shows_its_door(tmp_path):
    """Enumerate the readers and give each one a door. On the receiving side a blob ref is
    read by the parked inbox, the watcher's render, and the relay's bus line. A ref rendered
    bare on any of them is a dead end that looks like data."""
    f = tmp_path / "payload.bin"
    f.write_bytes(b"q" * 900)
    ann = RR.file_announcement(f, blobs=BlobStore(str(tmp_path / "blobs")))
    rendered = RR.render_file_announcement(ann)
    assert ann["ref"] in rendered, "the render drops the ref"
    assert ann["name"] in rendered, "the render drops the filename"
    assert "fetch" in rendered.lower() or ann["fetch_with"] in rendered, (
        "a surface shows the ref without showing how to follow it")
