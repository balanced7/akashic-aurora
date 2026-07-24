"""
Wave 3 -- DictStore differential (Daniel's sprint-briefing item; spec:
docs/library/design/20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b.md "DictStore differential").

The same operation sequence runs against the in-memory DictStore and a live RedisStore;
after EVERY op the RETURN VALUES must match, and the final state dump must match.
Divergence IS the finding. Redis-absent -> skip (the local suite + ship gate have Redis).

Sequences: (1) the exact RB-8 supersession protocol ops; (2) deterministic two-handle CAS
contention schedule; (3) seeded random op soup (fixed seed); (4) same-score zset ordering
(lexicographic by member -- Redis documented behavior, DictStore must match).

Run: py -m pytest tests/test_store_differential.py -q
"""
import json
import os
import random
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import DictStore, RedisStore  # noqa: E402

NS = "w3diff:" + uuid.uuid4().hex[:8] + ":"


def _redis():
    try:
        r = RedisStore.connect()
        if r is not None and r.is_available():
            return r
    except Exception:
        pass
    return None


@pytest.fixture()
def pair():
    r = _redis()
    if r is None:
        pytest.skip("Redis not available -- differential needs the live backend")
    d = DictStore()
    yield d, r
    try:
        stale = r.keys(NS + "*")
        if stale:
            r.delete(*stale)
    except Exception:
        pass


def _run(pair, seq):
    """Apply each (method, args) to both stores; return values must match at every step."""
    d, r = pair
    for i, (method, args) in enumerate(seq):
        rv_d = getattr(d, method)(*args)
        rv_r = getattr(r, method)(*args)
        assert rv_d == rv_r, (
            "DIVERGENCE at op %d: %s%r -> dict=%r redis=%r" % (i, method, args, rv_d, rv_r))


def _dump(store, typed_keys):
    """Observable state for the touched keyspace, dumped BY DECLARED TYPE. (Cross-type
    probes are themselves a divergence -- Redis raises WRONGTYPE where the file lineage
    returns empty -- but agent code never cross-types a key; out of v1 scope, noted in
    the W3 spec's cut list spirit.)"""
    readers = {
        "kv": lambda s, k: s.get(k),
        "hash": lambda s, k: s.hgetall(k),
        "zset": lambda s, k: s.zrange(k, 0, -1, False, True),
    }
    out = {}
    for k, kind in sorted(typed_keys.items()):
        out[k] = {"v": readers[kind](store, k), "exists": store.exists(k)}
    return out


def _assert_final_state(pair, typed_keys):
    d, r = pair
    assert _dump(d, typed_keys) == _dump(r, typed_keys), "final state diverged"


# --- (1) the RB-8 protocol, as raw store ops ---

def test_rb8_protocol_ops_agree(pair):
    H, IDX, HEAD = NS + "decisions", NS + "decisions:idx", NS + "head:where-we-are"
    rec_a = json.dumps({"id": "A", "superseded": False})
    rec_b = json.dumps({"id": "B", "superseded": False})
    seq = [
        ("hset", (H, "A", rec_a)),                 # record A
        ("zadd", (IDX, {"A": 1.0})),
        ("cas", (HEAD, None, "A")),                # first-note claims fresh head (nx)
        ("cas", (HEAD, None, "A-rival")),          # rival first-note MUST fail on both
        ("hset", (H, "B", rec_b)),                 # record B
        ("zadd", (IDX, {"B": 2.0})),
        ("get", (HEAD,)),                          # read expected
        ("cas", (HEAD, "A", "B")),                 # supersede claim wins
        ("cas", (HEAD, "A", "B-stale")),           # stale expected MUST fail on both
        ("hset", (H, "A", json.dumps({"id": "A", "superseded": True}))),   # retire old
        ("hget", (H, "A")),
        ("hgetall", (H,)),
        ("zrangebyscore", (IDX, "-inf", "+inf")),
        ("exists", (HEAD,)),
    ]
    _run(pair, seq)
    _assert_final_state(pair, {H: "hash", IDX: "zset", HEAD: "kv"})


# --- (2) deterministic two-handle contention schedule ---

def test_cas_contention_schedule_agrees(pair):
    K = NS + "contended"
    seq = [
        ("cas", (K, None, "h1")),      # handle 1 wins the fresh key
        ("cas", (K, None, "h2")),      # handle 2 loses
        ("cas", (K, "h1", "h2")),      # handle 2 retries with fresh read -> wins
        ("cas", (K, "h1", "h3")),      # handle 3 raced on a stale read -> loses
        ("get", (K,)),
        ("delete", (K,)),
        ("cas", (K, None, "h4")),      # deleted key is fresh again
        ("get", (K,)),
    ]
    _run(pair, seq)
    _assert_final_state(pair, {K: "kv"})


# --- (3) seeded random op soup: divergence anywhere is the finding ---

def test_seeded_soup_agrees(pair):
    rng = random.Random(4242)
    kv_keys = [NS + "kv%d" % i for i in range(4)]
    h_keys = [NS + "h%d" % i for i in range(3)]
    z_keys = [NS + "z%d" % i for i in range(3)]
    fields = ["f1", "f2", "f3"]
    seq = []
    for _ in range(220):
        roll = rng.random()
        if roll < 0.20:
            seq.append(("set", (rng.choice(kv_keys), "v%d" % rng.randint(0, 9))))
        elif roll < 0.32:
            seq.append(("get", (rng.choice(kv_keys),)))
        elif roll < 0.44:
            seq.append(("cas", (rng.choice(kv_keys),
                                rng.choice([None, "v1", "v2", "v3"]),
                                "c%d" % rng.randint(0, 9))))
        elif roll < 0.58:
            seq.append(("hset", (rng.choice(h_keys), rng.choice(fields),
                                 "hv%d" % rng.randint(0, 9))))
        elif roll < 0.68:
            seq.append(("hget", (rng.choice(h_keys), rng.choice(fields))))
        elif roll < 0.76:
            seq.append(("hgetall", (rng.choice(h_keys),)))
        elif roll < 0.88:
            seq.append(("zadd", (rng.choice(z_keys),
                                 {"m%d" % rng.randint(0, 5): float(rng.randint(0, 4))})))
        elif roll < 0.96:
            seq.append(("zrangebyscore", (rng.choice(z_keys), "-inf", "+inf")))
        else:
            seq.append(("delete", (rng.choice(kv_keys + h_keys + z_keys),)))
    _run(pair, seq)
    typed = {k: "kv" for k in kv_keys}
    typed.update({k: "hash" for k in h_keys})
    typed.update({k: "zset" for k in z_keys})
    _assert_final_state(pair, typed)


# --- (4) same-score zset ordering: lexicographic by member on BOTH backends ---

def test_zset_same_score_ordering_agrees(pair):
    Z = NS + "ties"
    seq = [
        ("zadd", (Z, {"charlie": 5.0})),
        ("zadd", (Z, {"alpha": 5.0})),
        ("zadd", (Z, {"bravo": 5.0})),
        ("zadd", (Z, {"zulu": 1.0})),
        ("zrange", (Z, 0, -1)),
        ("zrange", (Z, 0, -1, True)),              # desc
        ("zrangebyscore", (Z, 5, 5)),
        ("zcard", (Z,)),
    ]
    _run(pair, seq)
    d, r = pair
    assert d.zrange(Z, 0, -1) == ["zulu", "alpha", "bravo", "charlie"], \
        "score then lexicographic-by-member is the documented Redis order"
