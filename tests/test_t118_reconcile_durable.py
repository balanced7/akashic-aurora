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


class _WrongTypeRedis(FileStore):
    """Faithful to real Redis where FileStore is not: reading a key with the wrong
    verb RAISES (WRONGTYPE). The sweep crashed live on exactly this after green
    FileStore-double pins -- the probe here must carry the same tolerance."""

    def _bucket_of(self, key):
        for b in self.DATA_BUCKETS:
            if key in self._data[b]:
                return b
        return None

    def _demand(self, key, bucket):
        b = self._bucket_of(key)
        if b is not None and b != bucket:
            raise RuntimeError("WRONGTYPE Operation against a key holding the wrong kind of value")

    def get(self, key):
        self._demand(key, "kv")
        return super().get(key)

    def hgetall(self, key):
        self._demand(key, "hash")
        return super().hgetall(key)

    def lrange(self, key, start, end):
        self._demand(key, "list")
        return super().lrange(key, start, end)

    def smembers(self, key):
        self._demand(key, "set")
        return super().smembers(key)

    def zrange(self, key, start, end, desc=False, withscores=False):
        self._demand(key, "zset")
        return super().zrange(key, start, end, desc=desc, withscores=withscores)


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


def test_p8_artifact_divergence_halts_before_any_write(tmp_path):
    """RATIFIED stop-rule (Daniel 2026-07-28): artifacts are write-once; a divergent
    twin is impossible-by-contract, so ONE escrow hit means halt-and-investigate.
    The halt must land BEFORE any write: no escrow file, durable side untouched."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.hset("artifact:art_2026_x", mapping={"body": "redis-variant"})
    file.hset("artifact:art_2026_x", mapping={"body": "file-variant"})
    redis.hset("artifact:art_2026_new", mapping={"body": "would-copy"})
    escrow = tmp_path / "escrow.json"

    with pytest.raises(ReconcileHalt) as exc:
        reconcile_apply(redis, file, escrow_path=escrow)

    assert "write-once" in str(exc.value), (
        "the halt must come from the STOP-RULE (write-once divergence), not from "
        "the unknown-family path"
    )
    assert not escrow.exists(), "stop-rule must fire before the escrow write"
    assert file.hgetall("artifact:art_2026_x") == {"body": "file-variant"}
    assert file.hgetall("artifact:art_2026_new") == {}, (
        "halt means NOTHING was written, not even the safe copies"
    )


def test_p9_auto_type_family_copies_kv_hash_and_list(tmp_path):
    """mem/learn/narr hold mixed structures under one family; the roster's 'auto'
    type probes per key and copies each with its own verb."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.set("mem:decisions:head:alpha", "kv-head")
    redis.hset("mem:decisions:rec:beta", mapping={"body": "hash-rec"})
    redis.rpush("mem:decisions:log", "one", "two")

    reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.get("mem:decisions:head:alpha") == "kv-head"
    assert file.hgetall("mem:decisions:rec:beta") == {"body": "hash-rec"}
    assert file.lrange("mem:decisions:log", 0, -1) == ["one", "two"]


def test_p10_deferred_family_neither_halts_nor_copies(tmp_path):
    """embed is RULED (durable compressed cache, follow-up slice owns the move) --
    so it must not halt as unknown, and must not be raw-copied here."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.set("embed:all-MiniLM-L6-v2:abc123", "raw-vector-bytes")
    redis.hset("learn:experiment:keep", mapping={"result": "x"})

    reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.get("embed:all-MiniLM-L6-v2:abc123") is None
    assert file.hgetall("learn:experiment:keep") == {"result": "x"}


def test_p12_mutable_artifact_indexes_do_not_trip_the_write_once_stop_rule(tmp_path):
    """Live finding 2026-07-28: all 28 divergent artifact keys were artifact:index:*
    (mutable projections that grow as new atoms cite old ones) -- ZERO true atoms
    diverged. The stop-rule guards artifact:art_* (the write-once atoms), not the
    family's mutable indexes, which reconcile normally (escrow + take authority)."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    redis.sadd("artifact:index:category:audit", "art_a", "art_b", "art_c")
    file.sadd("artifact:index:category:audit", "art_a")

    report = reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.smembers("artifact:index:category:audit") == {"art_a", "art_b", "art_c"}
    assert report["displaced"]["artifact"] == 1, "index divergence reconciles, never halts"


def test_p11_probe_survives_wrongtype_raising_authority(tmp_path):
    """Same WRONGTYPE class as the sweep crash, on the reconcile's probe path: a
    mixed-type auto family on a Redis-faithful store must copy cleanly."""
    redis, file = _WrongTypeRedis(str(tmp_path / "r.json")), _mk(tmp_path, "f")
    redis.set("mem:decisions:head:alpha", "kv-head")
    redis.hset("mem:decisions:rec:beta", mapping={"body": "hash-rec"})

    reconcile_apply(redis, file, escrow_path=tmp_path / "escrow.json")

    assert file.get("mem:decisions:head:alpha") == "kv-head"
    assert file.hgetall("mem:decisions:rec:beta") == {"body": "hash-rec"}


def test_p7_unknown_families_report_grouped_with_counts_not_as_a_wall(tmp_path):
    """The live plan's first run listed 1067 'families' that were one namespace of
    artifact atoms. Unknowns group by first segment with a count, so the halt is a
    ruling agenda, not a wall."""
    redis, file = _mk(tmp_path, "r"), _mk(tmp_path, "f")
    for i in range(3):
        redis.hset(f"unruled:rec_2026_{i}", mapping={"body": "x"})

    with pytest.raises(ReconcileHalt) as exc:
        reconcile_plan(redis, file)

    msg = str(exc.value)
    assert "unruled (3 key(s))" in msg
    assert "rec_2026_0" not in msg, "individual keys must not flood the halt message"


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
