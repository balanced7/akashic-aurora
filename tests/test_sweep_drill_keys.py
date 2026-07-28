"""T118 pins: the audited drill-key sweep (ratified roster row: ~180 t-*/t056_*
census singletons are test crumbs, ruled 'one audited TTL-sweep', not data).

The sweep's contract: dry-run by default and writes NOTHING; --apply deletes ONLY
pattern-matched keys AND first writes every doomed key's full value to an audit
file -- so even the deletion is reversible from its own receipt.
"""
import json

from core.foundation.store import FileStore
from scripts.ops.sweep_drill_keys import sweep


class _FakeRedis(FileStore):
    pass


class _WrongTypeRedis(FileStore):
    """Faithful to real Redis where FileStore is not: reading a key with the wrong
    verb RAISES (WRONGTYPE) instead of returning empty. This exact gap let the first
    live sweep --apply crash after 12 green pins (test-double-width lesson)."""

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


def _seed(store):
    store.set("t-s0b-deadbeef:probe", "drill crumb")
    store.hset("t056_cafe:task_cost:T900", mapping={"cost": "1"})
    store.set("census_test", "x")
    store.hset("learn:experiment:keep", mapping={"result": "live data"})


def test_dry_run_deletes_nothing_and_names_the_doomed(tmp_path):
    r = _FakeRedis(str(tmp_path / "r.json"))
    _seed(r)

    doomed = sweep(r, audit_path=tmp_path / "audit.json", apply=False)

    assert sorted(doomed) == ["census_test", "t-s0b-deadbeef:probe",
                              "t056_cafe:task_cost:T900"]
    assert r.get("t-s0b-deadbeef:probe") == "drill crumb"
    assert not (tmp_path / "audit.json").exists(), "dry-run writes nothing"


def test_apply_deletes_only_matches_and_audits_full_values(tmp_path):
    r = _FakeRedis(str(tmp_path / "r.json"))
    _seed(r)
    audit = tmp_path / "audit.json"

    doomed = sweep(r, audit_path=audit, apply=True)

    assert len(doomed) == 3
    assert r.get("t-s0b-deadbeef:probe") is None
    assert r.get("census_test") is None
    assert r.hgetall("learn:experiment:keep") == {"result": "live data"}, (
        "the sweep must never touch a non-matching key"
    )
    rec = json.loads(audit.read_text(encoding="utf-8"))
    assert rec["t-s0b-deadbeef:probe"]["value"] == "drill crumb", (
        "the audit holds full values BEFORE deletion -- the sweep is reversible "
        "from its own receipt"
    )
    assert rec["t056_cafe:task_cost:T900"]["value"] == {"cost": "1"}


def test_apply_survives_a_wrongtype_raising_store(tmp_path):
    """The live crash, pinned: real Redis raises WRONGTYPE on a type-mismatched
    read; the value probe must tolerate that per verb, not die on the first hash."""
    r = _WrongTypeRedis(str(tmp_path / "r.json"))
    _seed(r)
    audit = tmp_path / "audit.json"

    doomed = sweep(r, audit_path=audit, apply=True)

    assert len(doomed) == 3
    assert r.get("census_test") is None
    rec = json.loads(audit.read_text(encoding="utf-8"))
    assert rec["t056_cafe:task_cost:T900"]["value"] == {"cost": "1"}
