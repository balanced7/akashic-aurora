"""T084 Slice 0 RED pins: truthful, pure, structured awareness.

These tests are deliberately hermetic.  A status test must never borrow a real
fleet identity merely to prove formatting: doing so turns observation into live
presence/expectation mutation and makes the test itself an actor.
"""
from __future__ import annotations

import inspect

import pytest

from core.coord.observations import Observation, Snapshot
from core.comm import awareness


SUBJECT = "synthetic-seat-t084"


def _obs(name: str, summary: str = "ok") -> Observation:
    return Observation(
        name=name,
        subject=SUBJECT,
        status="OK",
        summary=summary,
        source=(f"fixture:{name}",),
    )


def test_observation_schema_carries_the_boundary_and_effects():
    row = Observation(
        name="bus",
        subject=SUBJECT,
        status="OK",
        summary="mail waiting",
        source=("fixture:peek",),
        total=70,
        total_relation="at_least",
        shown=2,
        order="oldest+newest",
        truncated=True,
        effects=(),
        details={"attention_shown": 1},
        drill=f"bifrost-sync {SUBJECT}",
    ).as_dict()

    assert row["subject"] == SUBJECT
    assert row["total"] == 70
    assert row["total_relation"] == "at_least"
    assert row["shown"] == 2
    assert row["order"] == "oldest+newest"
    assert row["truncated"] is True
    assert row["effects"] == []
    assert row["observed_at"]


def test_bus_observation_uses_authoritative_total_and_excludes_gap_row():
    rows = [
        {"id": "1-0", "kind": "note", "to": SUBJECT,
         "pending_at_least": 70, "pending_capped": True},
        {"gap": True, "display_only": True, "kind": "gap",
         "pending_at_least": 70, "pending_capped": True},
        {"id": "70-0", "kind": "question", "to": SUBJECT,
         "pending_at_least": 70, "pending_capped": True},
    ]

    got = awareness.observe_bus(
        SUBJECT,
        limit=10,
        peek_fn=lambda _subject, _limit: rows,
        presence_fn=lambda _subject: {
            "bus_online": True,
            "agents_online": ["peer-a"],
            "agents_registered_unattended": ["peer-b"],
        },
    )

    assert got.total == 70
    assert got.total_relation == "at_least"
    assert got.shown == 2                 # the synthetic gap is not unread mail
    assert got.truncated is True
    assert got.details["attention_shown"] == 1
    assert got.effects == ()


def test_snapshot_fails_one_provider_open_without_losing_the_other_rows():
    def broken(_subject: str) -> Observation:
        raise RuntimeError("bench store unavailable")

    snap = awareness.build_snapshot(
        SUBJECT,
        providers={
            "bus": lambda _subject: _obs("bus"),
            "bench": broken,
            "route": lambda _subject: _obs("route"),
            "moved": lambda _subject: _obs("moved"),
        },
    )

    assert isinstance(snap, Snapshot)
    assert snap.subject == SUBJECT
    assert snap.effects == ()
    assert [row.name for row in snap.observations] == ["bus", "bench", "route", "moved"]
    bench = next(row for row in snap.observations if row.name == "bench")
    assert bench.status == "UNAVAILABLE"
    assert "RuntimeError" in bench.summary


def test_render_is_compact_subject_explicit_and_boundary_honest():
    snap = Snapshot(
        kind="awareness",
        subject=SUBJECT,
        observations=(
            Observation(
                name="bus", subject=SUBJECT, status="OK", summary="mail waiting",
                source=("fixture:peek",), total=70, total_relation="at_least",
                shown=10, order="oldest+newest", truncated=True,
                details={"attention_shown": 1},
            ),
            _obs("bench", "0 parked"),
            _obs("route", "UNATTENDED"),
            _obs("moved", "git=1; ledger=0; notes=0; promoted=0"),
        ),
    )

    text = awareness.render_snapshot(snap)
    assert f"subject={SUBJECT}" in text
    assert ">=70" in text
    assert "10 shown" in text
    assert "truncated=yes" in text
    assert "effects=none" in text
    assert len(text.splitlines()) <= 8


def test_subject_is_required_instead_of_defaulting_to_another_identity():
    with pytest.raises(ValueError, match="subject"):
        awareness.build_snapshot("")


def test_bus_provider_has_no_sync_or_expectation_maintenance_dependency():
    source = inspect.getsource(awareness.observe_bus)
    for forbidden in (
        "collect_boot_bifrost",
        "peek_inbox",            # advance=False still refreshes presence through Bus._touch
        "register_presence",
        "expectations.sweep",
    ):
        assert forbidden not in source


def test_unread_probe_uses_only_read_operations():
    class ReadOnlyStore:
        def __init__(self):
            self.calls = []

        def hgetall(self, key):
            self.calls.append(("hgetall", key))
            return {}

        def xrange(self, key, **kwargs):
            self.calls.append(("xrange", key))
            return []

        def xrevrange(self, key, **kwargs):
            self.calls.append(("xrevrange", key))
            return []

        def __getattr__(self, name):
            raise AssertionError(f"observation attempted non-read Redis operation: {name}")

    store = ReadOnlyStore()
    got = awareness.peek_unread(SUBJECT, limit=10, client=store, namespace="fixture")

    assert got == []
    assert store.calls
    assert {name for name, _key in store.calls} <= {"hgetall", "xrange", "xrevrange"}


def test_pure_probe_confesses_packets_it_cannot_render(monkeypatch):
    class OnePacketStore:
        def hgetall(self, _key):
            return {}

        def xrange(self, key, **_kwargs):
            return [("1-0", {"packet": "fragment"})] if key.endswith(SUBJECT) else []

        def xrevrange(self, _key, **_kwargs):
            return []

    monkeypatch.setattr(
        awareness,
        "_decode_row",
        lambda *_args, **_kwargs: (None, "fragment"),
    )
    got = awareness.peek_unread(
        SUBJECT, limit=10, client=OnePacketStore(), namespace="fixture"
    )

    assert len(got) == 1
    assert got[0]["gap"] is True
    assert got[0]["pending_capped"] is True
    assert got[0]["unrendered_entries"] == 1
    assert "fragments=1" in got[0]["content"]


def test_own_broadcast_is_skipped_without_crashing_the_whole_peek():
    """FOUND 2026-08-31: _decode_row's own-broadcast branch returned a bare `None`
    instead of the `(None, why)` pair every other early-return uses, so
    `row, why = _decode_row(...)` raised TypeError the moment the subject's own
    broadcast sat in the peeked window -- observe_bus then reported the whole bus
    UNAVAILABLE (reproduced live; matches deepseek's 2026-08-29
    bus_redelivery_loop_masquerades_as_reasks report). Real _decode_row, not
    monkeypatched -- this exercises the actual bug, not a stand-in for it."""
    class SelfBroadcastStore:
        def hgetall(self, _key):
            return {}

        def xrange(self, key, **_kwargs):
            if key.endswith(":broadcast"):
                return [("1-0", {"frm": SUBJECT, "to": "*", "kind": "trace",
                                 "content": '"hi"', "ts": "1"})]
            return []

        def xrevrange(self, _key, **_kwargs):
            return []

    got = awareness.peek_unread(
        SUBJECT, limit=10, client=SelfBroadcastStore(), namespace="fixture"
    )  # must not raise

    assert got == [], "the subject's own broadcast must be silently excluded, not crash the peek"


