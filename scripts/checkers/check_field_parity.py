"""check_field_parity -- guard the FIELD surface inside a door, the way check_door_parity
guards the VERB surface across doors.

WHY THIS IS A DIFFERENT CHECKER AND NOT A FLAG ON THE OTHER ONE
---------------------------------------------------------------
check_door_parity asks: is this capability REACHABLE from every door?
This asks:               is a reachable capability actually FILLABLE?

A verb can be present on the CLI, the MCP server and the ToolBox -- passing door-parity
cleanly -- while offering no way to write a field its own ranker reads. That is not a
theoretical gap. Measured 2026-08-25/26, twice, on two unrelated planes:

  learn:experiment  root_cause      0 of 1120   read by the dedup dims, infer_domain,
                                                the index, and draft_anti_pattern_slug
                                                (whose docstring says it PREFERS it)
  learn:experiment  files_affected  0 of 1120   read by base_score tier 0.7
  mem:decisions     rationale       0 of 1355   read by decision_loader._text_of, which
                                                builds the text the Ranker scores

None of these errored. Nothing logged. The output was just quietly worse than designed,
for months, and both discoveries happened by hand at 1am because an outside fleet asked us
to justify a field list.

THE THREE VARIANTS THIS DETECTS (the class is broader than the first one found)
------------------------------------------------------------------------------
  ZERO   exactly 0.0% fill. A reader-without-a-writer candidate. Exactly-zero is a DOOR
         signature -- culture and laziness produce low-but-nonzero.
  SHELL  high fill, ~0% NON-DEFAULT. A default written onto every record. This variant
         actively defeats any fill-rate audit, which is why it survives the longest:
         `consequences` read 100% healthy while being {"negative": [], "positive": []}
         on all 1355 records.
  MONO   100% filled with a SINGLE distinct value. Carries no information even though
         every presence check passes it (`status` = "accepted" on all 1355).

WHAT THIS CHECKER DOES NOT DO, STATED PLAINLY
---------------------------------------------
It does NOT prove a flagged field is read. Deciding whether ZERO on field X matters
requires knowing if a scorer consumes it, and that is a human read of the call sites.
The expensive part is FINDING the candidates across thousands of records; that is what is
mechanised here. A flagged field is a question, not a verdict -- so this reports, and only
FAILS on drift past the manifest, per the ratchet idiom check_door_parity established.

Run:  py scripts/checkers/check_field_parity.py            # gate (exit 1 on NEW anomaly)
      py scripts/checkers/check_field_parity.py --report   # full per-field table
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: KNOWN DEBT, ratcheted. Every entry is a measured anomaly that exists TODAY and is
#: accepted for now. A new anomaly outside this manifest fails the gate; removing an entry
#: after fixing it is how the debt is paid down. Format: plane -> {field: (variant, note)}.
MANIFEST = {
    "learn:experiment": {
        "root_cause":      ("ZERO",  "FIXED 2026-08-26 (--root-cause added); stays listed until "
                                     "backfill or until fresh records move it off zero"),
        "files_affected":  ("ZERO",  "FIXED 2026-08-26 (--files-affected added); same note"),
        "expected":        ("ZERO",  "4% fill, near-dead; door offers --expected. low priority"),
        "anti_pattern":    ("ZERO",  "3.3%, filled via tag-anti-pattern not the learn door"),
        "metrics":         ("SHELL", "97.5% filled / 2.9% real -- '{}' on most records"),
        "confidence":      ("MONO",  "81% 'medium'; also holds TWO TYPE SYSTEMS (25 floats)"),
        "category":        ("MONO",  "60% 'uncategorized'; forfeits 2 of base_score's 4 tiers"),
        "success":         ("MONO",  "92% 'yes'"),
        # DORMANT -- the fourth variant, and the checker found it on its first run.
        # Writer EXISTS (learning_store.stamp_forge_proposal), reader EXISTS
        # (core/recall/curator.py:79), and 0 of 1130 records carry one. So the forge is
        # wired end to end and has NEVER ONCE FIRED. This is not a missing half; it is a
        # complete capability that has never executed, and nothing announces that.
        # Same class as backup_door_never_ran and a_capabilitys_death_is_invisible_from_
        # inside_the_live_tree: present, reachable, and silently inert.
        "forge_proposal":  ("ZERO",  "DORMANT: writer + reader both exist, 0 instances ever. "
                                     "The forge has never stamped a proposal. Decide whether "
                                     "to run it or retire it -- not a field defect"),
    },
    "mem:decisions": {
        # The checker corrected my hand analysis here and it was right: these are not
        # ABSENT, they are WRITTEN EMPTY on every record ([] / {}). That is SHELL, and the
        # distinction matters -- the writer does touch the field, it just always writes
        # nothing, so adding a door flag is only half the fix.
        "rationale":       ("SHELL", "1355 written, 0 real -- always []. READ by "
                                     "decision_loader._text_of, which builds the text the "
                                     "Ranker scores. OPEN DEFECT: no --rationale on the door"),
        "alternatives":    ("SHELL", "always [] -- no readers found; dead schema, harmless"),
        "consequences":    ("SHELL", "always {'negative': [], 'positive': []}; no readers"),
        "session_id":      ("ZERO",  "0/1355 DESPITE the door offering --session. Writer with "
                                     "no users -- a false affordance, not an output defect"),
        "status":          ("MONO",  "'accepted' on all 1355"),
    },
}

EMPTYISH = {"", "null", "none", "[]", "{}"}


def _filled(v):
    """Present at all. Deliberately generous -- SHELL is what catches the empty structures."""
    if v is None:
        return False
    if isinstance(v, bool):
        return True
    if isinstance(v, (list, dict)):
        return True
    return str(v).strip().lower() not in EMPTYISH


def _real(v):
    """Present AND carrying content. The difference between this and _filled IS the finding."""
    if v is None or v is False:
        return False
    if isinstance(v, (list, dict)):
        return any(_real(x) for x in (v.values() if isinstance(v, dict) else v))
    return str(v).strip().lower() not in EMPTYISH


def _records():
    """Every plane we can reach, as {plane: [record dicts]}. Missing plane = skipped, never
    a failure: a checker that dies when Redis is down teaches people to ignore checkers."""
    out = {}
    try:
        import redis
        r = redis.Redis(host=os.environ.get("AKASHIC_REDIS_HOST", "localhost"),
                        port=int(os.environ.get("AKASHIC_REDIS_PORT", 16379)),
                        decode_responses=True, socket_connect_timeout=3)
        r.ping()
    except Exception as e:
        print(f"[field-parity] SKIPPED -- no store reachable ({type(e).__name__}). "
              f"Not a failure; this checker measures live data or says nothing.")
        return out

    lessons = []
    try:
        for k in r.scan_iter("learn:experiment:*", count=4000):
            if r.type(k) == "hash":
                lessons.append(r.hgetall(k))
    except Exception:
        pass
    if lessons:
        out["learn:experiment"] = lessons

    notes = []
    try:
        for v in (r.hgetall("mem:decisions") or {}).values():
            try:
                notes.append(json.loads(v))
            except Exception:
                continue
    except Exception:
        pass
    if notes:
        out["mem:decisions"] = notes
    return out


def analyse(records):
    """Per-field stats and a variant verdict. Pure, so it is testable without a store."""
    n = len(records)
    fields = sorted({k for rec in records for k in rec.keys()})
    rows = []
    for f in fields:
        vals = [rec.get(f) for rec in records]
        filled = sum(1 for v in vals if _filled(v))
        real = sum(1 for v in vals if _real(v))
        distinct = len({json.dumps(v, sort_keys=True, default=str) for v in vals})
        variant = None
        if real == 0:
            # SHELL and ZERO differ by whether something is written at all -- and that
            # distinction is the whole reason SHELL survives audits.
            variant = "SHELL" if filled > n * 0.5 else "ZERO"
        elif distinct == 1 and filled == n:
            variant = "MONO"
        rows.append({"field": f, "n": n, "filled": filled, "real": real,
                     "distinct": distinct, "variant": variant})
    return rows


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    report = "--report" in argv
    planes = _records()
    if not planes:
        return 0

    new_anomalies = []
    for plane, records in sorted(planes.items()):
        rows = analyse(records)
        known = MANIFEST.get(plane, {})
        if report:
            print(f"\n=== {plane} -- {len(records)} records ===")
            print(f"{'FIELD':<20}{'FILLED':>9}{'REAL':>9}{'DISTINCT':>10}  VARIANT")
            print("-" * 62)
        for row in rows:
            if report:
                pct = 100 * row["real"] / max(row["n"], 1)
                print(f"{row['field']:<20}{row['filled']:>9}{row['real']:>9}"
                      f"{row['distinct']:>10}  {row['variant'] or ''}"
                      f"{'' if row['variant'] is None else f'  ({pct:.1f}% real)'}")
            if row["variant"] and row["field"] not in known:
                new_anomalies.append((plane, row["field"], row["variant"], row))

    if new_anomalies:
        print("\n[field-parity] FAIL -- new field anomalies outside the manifest:\n")
        for plane, field, variant, row in new_anomalies:
            print(f"  {plane}.{field}  [{variant}]  "
                  f"filled={row['filled']}/{row['n']} real={row['real']} distinct={row['distinct']}")
        print("\n  ZERO  = nothing writes it. Check whether a scorer READS it -- if so this is a")
        print("          live defect degrading output silently, not a cosmetic gap.")
        print("  SHELL = a default written on every record. It will pass any fill-rate check.")
        print("  MONO  = one value everywhere. Presence checks pass; it carries no information.")
        print("\n  Fix it, or add it to MANIFEST in this file WITH a rationale. An entry with no")
        print("  rationale is how known debt becomes forgotten debt.")
        return 1

    print(f"[field-parity] OK -- {sum(len(v) for v in planes.values())} records across "
          f"{len(planes)} plane(s); no anomalies outside the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
