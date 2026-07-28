"""Per-family authority reconcile: make the durable source COMPLETE before migrating.

WHY THIS EXISTS (codex census, note codex-b-defect-map-2026-07-28): whole-store
freshness is not authority. At the live snapshot Redis held 540 learn:experiment
hashes, SQLite 455, the JSON File 23 -- so a shadow-build from JSON alone would
faithfully produce a durable store missing 517 lessons. Authority is PER-FAMILY:
Redis is the recovery source for lessons; the JSON carries newer events/telemetry;
transport/control namespaces have no durable afterlife at all.

RELATION TO heal_must_backfill_never_overwrite (the reconcile() list-clobber scar):
that law binds GENERIC heals, which have no way to adjudicate a divergent twin -- so
they must only backfill. This path is different on purpose: the ROSTER is the
adjudication (a human-gated, receipt-carrying ruling of which side owns a family),
the overwrite direction is stale <- authority (never richer <- stale, which is what
burned us), and every displaced variant is ESCROWED to a sidecar before the write,
so the operation destroys nothing. An unrostered family cannot be adjudicated,
therefore it HALTS the whole run loudly -- the checker-shaped refusal, not a guess.

    py -m core.foundation.durable_reconcile --plan    # read-only report
    py -m core.foundation.durable_reconcile --apply   # escrow + reconcile

Both modes classify EVERY authority-side key first; any unknown non-ephemeral
family halts before a single write (see ReconcileHalt).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# family -> (authority, structure). RATIFIED by Daniel 2026-07-28 ("I like it, I
# assume since its a table we can add other categories as they emerge. Iapprove") --
# the full table with receipts: research/in-flight/t118-roster-proposal-2026-07-28.md.
# The roster is EMPIRICAL and EXTENSIBLE: new families halt the run until they get a
# row, so growth is a ruling with a census receipt, never a guess.
#   authority "redis": pull into the durable file side (additive union; divergent
#                      twins escrow-then-take-authority).
#   authority "file":  the durable side already owns it; nothing to pull.
#   authority "defer": ruled, but a dedicated follow-up slice owns the move -- no
#                      action here, no halt.
#   structure "hash"/"kv": the family's declared shape (anomalies reported).
#   structure "auto":  mixed shapes under one family; probe per key.
ROSTER: Dict[str, Tuple[str, Optional[str]]] = {
    # census 2026-07-28: Redis 540 / SQLite 455 / File 23 -- Redis is recovery source
    "learn:experiment": ("redis", "hash"),
    # category indexes + experiments:all list -- projections but load-bearing (the
    # 485-list clobber scar); mixed shapes
    "learn": ("redis", "auto"),
    # AgentMemory decisions/heads (362 vs 24) -- same durable-critical genus as lessons
    "mem": ("redis", "auto"),
    # Daniel's union reframe: additive union rescues clobbered chapters; file's beat
    # extras survive by additivity; ties break to the live side with escrow
    "narr": ("redis", "auto"),
    # T101 write-once atoms + indexes; divergence is impossible-by-contract -> see
    # STOP_ON_DIVERGENCE
    "artifact": ("redis", "auto"),
    "codex:resource": ("redis", "auto"),
    # census 2026-07-28: file-ahead 5:1 / file-ahead -- durable side already owns them
    "events": ("file", None),
    "events:raw": ("file", None),
    "recall": ("file", None),
    "recall:use": ("file", None),
    "narr:beat": ("file", None),  # superseded by the narr union row; kept harmless
    # RULED durable-as-compressed-content-addressed-cache (Daniel steer); the pack+
    # migrate slice owns the move -- raw vectors are not copied into the JSON twin
    "embed": ("defer", None),
}

# Write-once KEY PREFIXES: a divergent twin here is a CONTRACT VIOLATION, not a tie
# to break -- one hit halts the whole apply before any write (ratified stop-rule).
# Prefix-precise on purpose (live finding 2026-07-28): the artifact FAMILY also holds
# artifact:index:* -- mutable projections that grow as new atoms cite old ones and
# diverge legitimately (all 28 live divergences were indexes; zero true atoms).
STOP_ON_DIVERGENCE_PREFIXES = ("artifact:art_",)


class ReconcileHalt(SystemExit):
    """Raised (before any write) when a family no one has ruled on shows up."""


def _roster_family(key: str) -> Optional[str]:
    """Longest ROSTER prefix that matches on a ':' boundary, else None. Family depth
    is namespace-specific (learn:experiment:NAME is a two-segment family; an
    artifact:art_... atom is a one-segment family), so matching is against the
    roster's own entries, never a fixed segment count."""
    k = str(key)
    best = None
    for fam in ROSTER:
        if (k == fam or k.startswith(fam + ":")) and (best is None or len(fam) > len(best)):
            best = fam
    return best


def _report_family(key: str) -> str:
    """Grouping unit for UNKNOWN keys in the halt message: the first segment. 1067
    artifact atoms are one ruling ('artifact'), not 1067 walls of text."""
    return str(key).split(":", 1)[0]


def _is_ephemeral(key: str) -> bool:
    try:
        from core.comm.packet_spec import is_ephemeral_key
        return bool(is_ephemeral_key(key))
    except Exception:
        return False


def _classify(authority_store) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """(rostered redis-authoritative family -> keys, unknown family -> key count).
    Ephemeral and file-authoritative keys drop out here; unknowns are counted per
    first-segment group, never guessed at."""
    per_family: Dict[str, List[str]] = {}
    unknown: Dict[str, int] = {}
    for key in authority_store.keys("*"):
        if _is_ephemeral(key):
            continue
        fam = _roster_family(key)
        if fam is None:
            grp = _report_family(key)
            unknown[grp] = unknown.get(grp, 0) + 1
            continue
        if ROSTER[fam][0] == "redis":
            per_family.setdefault(fam, []).append(key)
    return per_family, unknown


def _halt(unknown: Dict[str, int]) -> "ReconcileHalt":
    shown = sorted(unknown.items(), key=lambda kv: -kv[1])
    head = ", ".join(f"{fam} ({n} key(s))" for fam, n in shown[:20])
    more = f" +{len(shown) - 20} more group(s)" if len(shown) > 20 else ""
    return ReconcileHalt(
        f"[reconcile] HALT: {len(shown)} unrostered family group(s) on the authority "
        f"side: {head}{more}. Rule on each in ROSTER (with a census receipt) or add "
        f"it to the ephemeral roster; nothing was written.")


def _quiet(fn, default):
    """Real Redis RAISES (WRONGTYPE) on a type-mismatched read where FileStore
    returns empty -- crashed the first live sweep after green FileStore-double pins.
    Each probe verb tolerates the mismatch and moves to the next shape."""
    try:
        return fn()
    except Exception:
        return default


def _probe(store, key) -> Tuple[Optional[str], Any]:
    """(structure, value) for whatever this key holds on this store; (None, None)
    when empty everywhere. Store-agnostic: probes the five structure verbs rather
    than trusting any backend's private type table."""
    h = _quiet(lambda: store.hgetall(key), {})
    if h:
        return "hash", h
    v = _quiet(lambda: store.get(key), None)
    if v is not None:
        return "kv", v
    lst = _quiet(lambda: store.lrange(key, 0, -1), [])
    if lst:
        return "list", list(lst)
    s = _quiet(lambda: store.smembers(key), set())
    if s:
        return "set", sorted(s)
    z = _quiet(lambda: store.zrange(key, 0, -1, withscores=True), [])
    if z:
        return "zset", {m: sc for m, sc in z}
    return None, None


def _read_source(authority_store, fam: str, key: str) -> Tuple[Optional[str], Any, bool]:
    """(structure, value, is_anomaly) honoring the family's DECLARED shape: a
    declared-hash family with a non-hash key is a shape anomaly (reported, skipped);
    'auto' families accept whatever the probe finds."""
    declared = ROSTER[fam][1]
    src_t, src = _probe(authority_store, key)
    if src_t is None:
        return None, None, False
    if declared in ("hash", "kv") and src_t != declared:
        return None, None, True
    return src_t, src, False


def plan(authority_store, durable_store) -> Dict[str, Any]:
    """Read-only: what --apply would do. Halts on unknown families exactly as apply
    does -- a plan that silently skips what apply would refuse is a lying plan."""
    per_family, unknown = _classify(authority_store)
    if unknown:
        raise _halt(unknown)
    report: Dict[str, Any] = {"copy": {}, "divergent": {}, "type_anomalies": []}
    for fam, keys in per_family.items():
        for key in keys:
            src_t, src, anomaly = _read_source(authority_store, fam, key)
            if anomaly:
                report["type_anomalies"].append(key)
                continue
            if src_t is None:
                continue
            cur_t, cur = _probe(durable_store, key)
            if cur_t is None:
                report["copy"][fam] = report["copy"].get(fam, 0) + 1
            elif (cur_t, cur) != (src_t, src):
                report["divergent"][fam] = report["divergent"].get(fam, 0) + 1
    return report


def apply(authority_store, durable_store, escrow_path) -> Dict[str, Any]:
    """Escrow-then-reconcile. Additive for keys the durable side lacks; divergent
    twins take the authority value AFTER the displaced variant lands in the escrow
    file. Escrow is written before the first overwrite (crash order matters)."""
    per_family, unknown = _classify(authority_store)
    if unknown:
        raise _halt(unknown)

    report: Dict[str, Any] = {"copied": {}, "displaced": {}, "type_anomalies": [],
                              "untouched_equal": 0}
    to_copy: List[Tuple[str, str, str, Any]] = []      # (family, key, structure, value)
    displaced: Dict[str, Any] = {}

    for fam, keys in per_family.items():
        for key in keys:
            src_t, src, anomaly = _read_source(authority_store, fam, key)
            if anomaly:
                report["type_anomalies"].append(key)
                continue
            if src_t is None:
                continue
            cur_t, cur = _probe(durable_store, key)
            if cur_t is not None and (cur_t, cur) == (src_t, src):
                report["untouched_equal"] += 1
                continue
            if cur_t is not None:
                displaced[key] = cur
                report["displaced"][fam] = report["displaced"].get(fam, 0) + 1
            else:
                report["copied"][fam] = report["copied"].get(fam, 0) + 1
            to_copy.append((fam, key, src_t, src))

    # RATIFIED stop-rule: a divergent WRITE-ONCE twin is a contract violation, not a
    # tie to break. Halt before any write -- no escrow, no copies, durable untouched.
    stop = sorted(k for k in displaced
                  if any(str(k).startswith(p) for p in STOP_ON_DIVERGENCE_PREFIXES))
    if stop:
        shown = ", ".join(stop[:5]) + (" ..." if len(stop) > 5 else "")
        raise ReconcileHalt(
            f"[reconcile] HALT: {len(stop)} write-once twin(s) diverged -- "
            f"impossible-by-contract under {STOP_ON_DIVERGENCE_PREFIXES}, so "
            f"something upstream is broken. Investigate before ANY reconcile: {shown}. "
            f"Nothing was written, no escrow was created.")

    if displaced:
        escrow_path = Path(escrow_path)
        escrow_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(f"{escrow_path}.tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(displaced, f, indent=1)
        os.replace(tmp, escrow_path)

    for fam, key, src_t, src in to_copy:
        if src_t == "hash":
            durable_store.hset(key, mapping=src)
        elif src_t == "kv":
            durable_store.set(key, src)
        elif src_t == "list":
            durable_store.delete(key)   # divergent replace; no-op on fresh copies
            durable_store.rpush(key, *src)
        elif src_t == "set":
            durable_store.sadd(key, *src)
        elif src_t == "zset":
            durable_store.zadd(key, src)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true", help="read-only report")
    ap.add_argument("--apply", action="store_true", help="escrow + reconcile")
    a = ap.parse_args(argv)
    if not (a.plan or a.apply):
        ap.error("pick --plan or --apply")

    from core.foundation.store import FileStore, RedisStore
    redis = RedisStore.connect()
    if not redis.is_available():
        print("[reconcile] REFUSING: Redis (the authority side for rostered families) "
              "is down; a reconcile without the authority present would be fiction.")
        return 1
    file_store = FileStore(None)

    try:
        if a.plan:
            rep = plan(redis, file_store)
            print(f"[reconcile] PLAN (read-only): copy={rep['copy']} "
                  f"divergent(escrow-then-take)={rep['divergent']} "
                  f"type_anomalies={len(rep['type_anomalies'])}")
            return 0
        stamp = int(time.time())
        escrow = Path(os.getenv("AI_SETUP", r"E:\AI-Setup")) / "session_logs" / \
            f"reconcile-displaced-{stamp}.json"
        rep = apply(redis, file_store, escrow_path=escrow)
        print(f"[reconcile] APPLIED: copied={rep['copied']} displaced={rep['displaced']} "
              f"(escrow: {escrow if rep['displaced'] else 'none needed'}) "
              f"equal-untouched={rep['untouched_equal']} "
              f"type_anomalies={rep['type_anomalies'] or 'none'}")
        return 0
    except ReconcileHalt as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
