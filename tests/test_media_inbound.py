"""
Inbound media (2026-08-23, Serge's shader ask): the ear learns to receive —
through the bus's OWN media organ (B1 parts: filesystem blob store, the bus
carries content-addressed refs; file_part/Part.resolve were built for exactly
this and were waiting).

  P1  a message WITH attachments rides as PARTS: bus.send receives parts
      whose content_types match the files and whose refs are blob refs.
  P2  an attachment-only message (no text) is NO LONGER 'empty' -- it acts,
      placeholder content names the file(s).
  P3  a text-only message sends no parts (no empty lists riding).

Run: py -m pytest tests/test_media_inbound.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import discord_inbound

ROOT_ID = "111222333444555666"


def _cfg():
    return {"operator_id": ROOT_ID,
            "people": {ROOT_ID: {"agent": "daniil", "tier": "operator"}}}


class _Bus:
    def __init__(self):
        self.sent = []

    def send(self, to, kind, content, meta=None, parts=None):
        self.sent.append({"to": to, "kind": kind, "content": content,
                          "meta": dict(meta or {}), "parts": parts})
        return "m1-0"

    def broadcast(self, kind, content, meta=None, parts=None):
        self.sent.append({"to": "*", "kind": kind, "content": content,
                          "meta": dict(meta or {}), "parts": parts})
        return "m1-0"


def _tmp_png():
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.write(b"\x89PNG\r\n\x1a\nfakepixels")
    f.close()
    return f.name


def _call(content, attachments=None):
    bus = _Bus()
    out = discord_inbound.handle_message(
        _cfg(), author_id=ROOT_ID, author_name="d", channel_id="c1",
        content=content, bus=bus, react=lambda e: None,
        attachments=attachments)
    return out, bus


def test_p1_attachments_ride_as_blob_parts():
    p = _tmp_png()
    try:
        out, bus = _call("design from this", attachments=[p])
        assert out.get("acted")
        parts = bus.sent[-1]["parts"]
        assert parts and len(parts) == 1
        assert parts[0].content_type == "image/png"
        assert parts[0].is_ref, "media rides by REFERENCE (B1), never inline"
    finally:
        os.remove(p)


def test_p2_attachment_only_message_acts():
    p = _tmp_png()
    try:
        out, bus = _call("", attachments=[p])
        assert out.get("acted"), "an image IS a message now"
        assert os.path.basename(p) in str(bus.sent[-1]["content"])
        assert bus.sent[-1]["parts"]
    finally:
        os.remove(p)


def test_p3_text_only_sends_no_parts():
    out, bus = _call("plain words")
    assert out.get("acted")
    assert not bus.sent[-1]["parts"]
