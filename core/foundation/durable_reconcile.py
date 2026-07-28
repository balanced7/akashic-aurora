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

# family -> (authority, structure). The roster is EMPIRICAL: entries cite the census
# that ruled them. Growing it is a ceremony act with receipts, not a default.
#   authority "redis": copy into the durable file side (additive; divergent twins
#                      escrow-then-take-authority).
#   authority "file":  the durable side already owns it; nothing to pull.
ROSTER: Dict[str, Tuple[str, Optional[str]]] = {
    # census 2026-07-28: Redis 540 / SQLite 455 / File 23 -- Redis is recovery source
    "learn:experiment": ("redis", "hash"),
    # census 2026-07-28: JSON-only deltas -- the file side is the fresh one
    "events:raw": ("file", None),
    "recall:use": ("file", None),
    "narr:beat": ("file", None),
}


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


def plan(authority_store, durable_store) -> Dict[str, Any]:
    """Read-only: what --apply would do. Halts on unknown families exactly as apply
    does -- a plan that silently skips what apply would refuse is a lying plan."""
    per_family, unknown = _classify(authority_store)
    if unknown:
        raise _halt(unknown)
    report: Dict[str, Any] = {"copy": {}, "divergent": {}, "type_anomalies": []}
    for fam, keys in per_family.items():
        structure = ROSTER[fam][1]
        for key in keys:
            got = durable_store.hgetall(key) if structure == "hash" else durable_store.get(key)
            src = authority_store.hgetall(key) if structure == "hash" else authority_store.get(key)
            if structure == "hash" and not src:
                report["type_anomalies"].append(key)
                continue
            if not got:
                report["copy"][fam] = report["copy"].get(fam, 0) + 1
            elif got != src:
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
    to_copy: List[Tuple[str, str, Any]] = []          # (family, key, value)
    displaced: Dict[str, Any] = {}

    for fam, keys in per_family.items():
        structure = ROSTER[fam][1]
        for key in keys:
            if structure == "hash":
                src = authority_store.hgetall(key)
                if not src:
                    report["type_anomalies"].append(key)
                    continue
                cur = durable_store.hgetall(key)
            else:
                src = authority_store.get(key)
                cur = durable_store.get(key)
            if cur and cur == src:
                report["untouched_equal"] += 1
                continue
            if cur and cur != src:
                displaced[key] = cur
                report["displaced"][fam] = report["displaced"].get(fam, 0) + 1
            else:
                report["copied"][fam] = report["copied"].get(fam, 0) + 1
            to_copy.append((fam, key, src))

    if displaced:
        escrow_path = Path(escrow_path)
        escrow_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(f"{escrow_path}.tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(displaced, f, indent=1)
        os.replace(tmp, escrow_path)

    for fam, key, src in to_copy:
        if ROSTER[fam][1] == "hash":
            durable_store.hset(key, mapping=src)
        else:
            durable_store.set(key, src)
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
