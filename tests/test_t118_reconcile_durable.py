"""T118 pins: per-family authority reconcile (the step BEFORE any live shadow-build).

Codex's census (note codex-b-defect-map-2026-07-28) proved whole-store freshness is
not authority: Redis holds 540 learn:experiment hashes, SQLite 455, the JSON File 23.
A shadow-build from JSON alone would faithfully produce a durable store missing 517
lessons. So the cutover's first act is an authority-roster reconcile into the durable
source: additive for records only the authority holds, escrow-then-take-authority for
divergent twins, LOUD HALT for families no one has ruled on, and never a byte of
transport/control traffic.

These pins run on DictStore/FileStore stand-ins -- no Redis required.
"""
import json

import pytest

from core.foundation.durable_reconcile import (
    ReconcileHalt,
    apply as reconcile_apply,
    plan as reconcile_plan,
)
from core.foundation.store import FileStore


class _FakeRedis(FileStore):
    """Store stand-in for the live/authority side: FileStore semantics, tmp-backed."""


def _mk(tmp_path, name):
    return _FakeRedis(str(tmp_path / f"{name}.json"))


def test_p1_missing_lesson_is_copied_additively(tmp_path):
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.hset("learn:experiment:alpha", mapping={"result": "fresh"})
    file.hset("learn:experiment:beta", mapping={"result": "file-only"})

    report = reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.hgetall("learn:experiment:alpha") == {"result": "fresh"}
    assert file.hgetall("learn:experiment:beta") == {"result": "file-only"}, (
        "additive means the file's unique records are preserved, never dropped"
    )
    assert report["copied"]["learn:experiment"] == 1


def test_p2_divergent_twin_takes_authority_but_escrows_the_displaced(tmp_path):
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.hset("learn:experiment:gamma", mapping={"result": "authority-fresh"})
    file.hset("learn:experiment:gamma", mapping={"result": "file-stale"})
    escrow = tmp_path / "escrow.json"

    report = reconcile_apply(redis, file, escrow_path=escrow)

    assert file.hgetall("learn:experiment:gamma") == {"result": "authority-fresh"}, (
        "authority means authority: the rostered side wins the divergent twin"
    )
    displaced = json.loads(escrow.read_text(encoding="utf-8"))
    assert displaced["learn:experiment:gamma"] == {"result": "file-stale"}, (
        "nothing is destroyed: the displaced variant is escrowed, append-only ethos"
    )
    assert report["displaced"]["learn:experiment"] == 1


def test_p3_unknown_family_halts_loud_and_writes_nothing(tmp_path):
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.hset("mystery:family:key", mapping={"x": "1"})

    with pytest.raises(ReconcileHalt) as exc:
        reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert "mystery" in str(exc.value)
    assert file.keys("*") == [], "a halt must leave the durable side untouched"


def test_p7_unknown_families_report_grouped_with_counts_not_as_a_wall(tmp_path):
    """The live plan's first run listed 1067 'families' that were one namespace of
    artifact atoms. Unknowns group by first segment with a count, so the halt is a
    ruling agenda, not a wall."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    for i in range(3):
        redis.hset(f"artifact:art_2026_{i}", mapping={"body": "x"})

    with pytest.raises(ReconcileHalt) as exc:
        reconcile_plan(redis, file)

    msg = str(exc.value)
    assert "artifact (3 key(s))" in msg
    assert "art_2026_0" not in msg, "individual keys must not flood the halt message"


def test_p4_ephemeral_families_are_never_copied(tmp_path):
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.set("bifrost:work:123-0", "transport traffic")
    redis.hset("learn:experiment:delta", mapping={"result": "keep"})

    reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.get("bifrost:work:123-0") is None, (
        "transport/control namespaces must not gain a durable afterlife"
    )
    assert file.hgetall("learn:experiment:delta") == {"result": "keep"}


def test_p5_plan_is_read_only(tmp_path):
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.hset("learn:experiment:eps", mapping={"result": "fresh"})

    report = reconcile_plan(redis, file)

    assert report["copy"]["learn:experiment"] == 1
    assert file.keys("*") == [], "--plan must write nothing"


def test_p6_wrong_type_in_rostered_family_is_loud_not_silent(tmp_path):
    """The roster carries the family's TYPE (lessons are hashes). A kv key inside a
    hash-rostered family is a shape anomaly: skipped, counted, named -- not copied
    wrong and not sailed past."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.set("learn:experiment:weird", "a bare kv where a hash should live")

    report = reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.get("learn:experiment:weird") is None
    assert report["type_anomalies"] == ["learn:experiment:weird"]
