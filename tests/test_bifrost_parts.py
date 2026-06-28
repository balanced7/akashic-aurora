"""
Slice B1 -- Bifrost Parts + media-by-reference (the BlobStore).

Bar: large/media payloads round-trip by REFERENCE (the bus stays light); the ref is never handed
out before the bytes are durable (blob-before-pointer); identical content dedups; a missing/garbage
ref is non-fatal; and a Message can carry Parts (inline or blob refs) that the receiver resolves.

BlobStore tests are filesystem-only (always run); the message-with-media-part test uses real Redis
(skips if down). Run: py -m pytest tests/test_bifrost_parts.py -q
"""
import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.blobs import BlobStore
from core.comm.bus import Bus, Part, text_part, json_part, media_part


def _blobs():
    return BlobStore(base_dir=os.path.join(tempfile.mkdtemp(), "blobs"))


# ----------------------------------------------------------------- BlobStore (no Redis)
def test_blob_roundtrip_and_ref_shape():
    bs = _blobs()
    ref = bs.put(b"hello bifrost")
    assert ref.startswith("blob:")
    assert bs.get(ref) == b"hello bifrost"
    assert bs.exists(ref)
    assert bs.put("a string") and bs.get(bs.put("a string")) == b"a string"   # str -> utf-8


def test_blob_dedup_same_content_same_ref():
    bs = _blobs()
    assert bs.put(b"same") == bs.put(b"same")            # content-addressed -> identical ref
    assert bs.put(b"same") != bs.put(b"different")


def test_blob_before_pointer():
    bs = _blobs()
    ref = bs.put(b"x" * 100)
    # the ref is only returned after the bytes are durable: exists() is immediately true,
    # and no stray .tmp file is left behind
    assert bs.exists(ref)
    assert not any(p.suffix == ".tmp" for p in bs.base.iterdir())


def test_missing_ref_is_not_fatal():
    bs = _blobs()
    assert bs.get("blob:deadbeefdeadbeef") is None
    assert bs.get("not-a-ref") is None
    assert bs.exists("blob:nope") is False


def test_large_blob_roundtrip():
    bs = _blobs()
    data = bytes((i * 7) % 256 for i in range(1_000_000))   # ~1 MB
    ref = bs.put(data)
    assert bs.get(ref) == data


def test_part_resolve_inline_and_ref():
    bs = _blobs()
    assert text_part("hi").resolve() == "hi"
    assert json_part({"a": 1}).resolve() == {"a": 1}
    p = media_part(b"\x89PNG fake bytes", "image/png", blobs=bs)
    assert p.is_ref and p.resolve(blobs=bs) == b"\x89PNG fake bytes"
    assert Part.from_dict(p.to_dict()).ref == p.ref            # serialization round-trip


# ----------------------------------------------------------------- message carries Parts (real Redis)
def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def test_message_with_media_part_roundtrips():
    c = _client()
    ns = f"bifrost_test_{uuid.uuid4().hex[:8]}"
    bs = _blobs()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        payload = b"the quick brown fox" * 1000
        parts = [text_part("see attached log"), media_part(payload, "text/plain", blobs=bs)]
        alice.send("bob", "handoff", {"note": "context attached"}, parts=parts)
        got = bob.inbox()
        assert len(got) == 1
        m = got[0]
        assert m.content == {"note": "context attached"} and len(m.parts) == 2
        assert m.parts[0].resolve() == "see attached log"          # inline survives
        assert m.parts[1].is_ref and m.parts[1].resolve(blobs=bs) == payload   # media by ref
    finally:
        keys = c.keys(f"{ns}:*")
        if keys:
            c.delete(*keys)


if __name__ == "__main__":
    for fn in [test_blob_roundtrip_and_ref_shape, test_blob_dedup_same_content_same_ref,
               test_blob_before_pointer, test_missing_ref_is_not_fatal, test_large_blob_roundtrip,
               test_part_resolve_inline_and_ref]:
        fn()
    print("BlobStore/Part tests passed; the message-with-media test runs under pytest")
