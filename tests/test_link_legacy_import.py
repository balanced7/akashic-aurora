"""RFC #70 Phase 6: mail the old HMAC bridge parked is imported into the quarantine as `legacy`
records, once, unverified, and never onto an inbox until a person promotes it."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fakeredis  # sys.path bootstrap

from core.link import legacy, quarantine  # sys.path bootstrap


def _park(tmp_path, monkeypatch, rows):
    f = tmp_path / "inbox.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(f))
    monkeypatch.setenv("AI_SETUP", str(tmp_path))


def test_parked_mail_becomes_unverified_legacy_records_once(tmp_path, monkeypatch):
    _park(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "m1",
                "frm": "remote:serge",
                "claimed_frm": "chronos",
                "kind": "question",
                "content": "hi",
                "sent_at": 1,
                "admitted_at": 2,
            },
            {
                "id": "m2",
                "frm": "remote:serge",
                "claimed_frm": "chronos",
                "kind": "halt",
                "content": "stop",
                "sent_at": 1,
                "admitted_at": 2,
            },
        ],
    )
    r = fakeredis.FakeRedis(decode_responses=True)
    assert legacy.import_parked(dry=True, r=r)["would_import"] == 1
    out = legacy.import_parked(r=r)
    assert out["imported"] == 1, "a kind outside the allowlist is never imported"
    assert legacy.import_parked(r=r)["imported"] == 0, "idempotent"
    rows = list(r.xrange(quarantine.stream_key(legacy.LEGACY)) or [])
    assert len(rows) == 1
    f: dict = dict(rows[0][1] or {})
    assert f["verified"] == "false"
    assert f["fleet"] == "serge"
    assert f["seat_claim"] == "chronos"
    assert set(r.keys("*")) == {quarantine.stream_key(legacy.LEGACY)}, "quarantine only"

    sent = []

    class StubBus:
        def send(self, to, kind, text, meta=None):
            sent.append((to, kind, text, meta))
            return "9-0"

    p = legacy.promote_legacy("m1", by="person:test", to="claude", r=r, bus=StubBus())
    assert p["promoted"]
    to, kind, text, meta = sent[0]
    assert (to, kind) == ("claude", "question")
    assert text.startswith("[remote serge (legacy bridge)]")
    assert meta["verified"] is False
    assert meta["authority"] == "none"
