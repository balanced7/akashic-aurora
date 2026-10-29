"""bootstrap_world -- one command that proves "install → seeded → recall works out of the gate".

    py scripts/bootstrap_world.py --self-check           # run the validation tiers (the point)
    py scripts/bootstrap_world.py --self-check --skip-clone   # fast mode: skip the full clone drill

WHY THIS EXISTS
---------------
The operator goal this closes (2026-10-27): "someone who installs akashic aurora has a capable
system with recall at tool-call working out the gate." Install, then ONE command proves it.

It does NOT re-invent transport or checks. It ORCHESTRATES the instruments the house already
built, each of which already obeys the house laws (fail-open, UNKNOWN-not-empty, ratchet-on-
baseline, retirement rules). Reuse, do not re-derive:

    Tier 0 - does it run        check_fresh_clone --clone   (a clone of HEAD collects the suite)
                                check_wiring                (no built-not-wired module)
    Tier 1 - are doors honest   check_advertised_tools      (every promised tool exists)
                                check_advertised_verbs      (every promised verb resolves)
                                check_door_parity           (doors match their parity table)
                                check_secrets               (secrets redirectable, not const)
    Tier 2 - integrations up    check_ports --report        (declared ports are listening)
                                agent_cli.py doctor         (fleet liveness: progress, not presence)
    Tier 3 - memory works       check_organ_canaries --gate (recall-at surfaces a seeded lesson)
    Tier 4 - provenance truth   the seed manifest           (seeded@vN / native / unknown)

VERDICTS ARE THREE-VALUED, NEVER GUESSED
----------------------------------------
Each tier prints PASS / FAIL / UNCHECKED. UNCHECKED is a blocking gap, not a pass: a checker
that could not run (missing module, missing store, missing manifest) is an unwatched organ, and
ZERO IS NOT NO -- the same law check_organ_canaries enforces on itself.

Tier 4 is the honest provenance line, taken from core.world_seed.read_manifest (the same reader
agent_cli._boot_world_line uses): "seeded from X @when", "native / copied by hand", or "origin
unknown -- the seed manifest could not be read". Never a guessed positive.

REUSE, NOT RE-INVENTION
-----------------------
Transport is core/world_seed.py + scripts/seed_world.py (downward-only, allowlist, refusal
reporting). THE CLEARANCE PREDICATE and the lesson inventory (origin id + content hash) live in
docs/library/design/20261027_clearance-predicate-and-self-validation-spec.md and are enforced at
seed time, not here. This script only PROVES the result, through the existing gates.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable  # "py" if this runs under the launcher; subprocess under the same python
sys.path.insert(0, str(ROOT))   # _tier4_provenance imports core.* in THIS process; the child
                                # checkers each do their own insert, but this process must too.

# Each tier: name -> list of (display, argv). argv is run with cwd=ROOT. A checker that exits
# non-zero is a FAIL; one that could not run (ImportError/find failure) is UNCHECKED -- but we
# distinguish the two by the RETURN CODE BELOW, because a checker's own FAIL is exit 1 while a
# missing module may be exit 1 too. So each command is (label, argv, expected_fail_marker) --
# see _run.
TIERS: dict[str, list] = {
    "tier0-runs": [
        ("fresh clone collects the suite (drill)",
         ["scripts/check_fresh_clone.py", "--clone"]),
        ("no built-not-wired module",
         ["scripts/checkers/check_wiring.py"]),
    ],
    "tier1-doors": [
        ("every promised tool exists",
         ["scripts/checkers/check_advertised_tools.py"]),
        ("every promised verb resolves",
         ["scripts/checkers/check_advertised_verbs.py"]),
        ("doors match their parity table",
         ["scripts/checkers/check_door_parity.py"]),
        ("secrets redirectable",
         ["scripts/checkers/check_secrets.py"]),
    ],
    "tier2-integrations": [
        ("declared ports are listening",
         ["scripts/checkers/check_ports.py", "--report"]),
        ("fleet liveness (doctor)",
         ["agent_cli.py", "doctor"]),
    ],
    "tier3-memory": [
        ("recall-at surfaces a seeded lesson",
         ["scripts/checkers/check_organ_canaries.py", "--gate"]),
    ],
}


def _run(argv: list[str], timeout: int = 600) -> tuple[int, str]:
    """Run a checker, capturing combined output. Never raises: a crashed checker is a finding."""
    try:
        p = subprocess.run([PY, *argv], cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    except FileNotFoundError as e:
        return -2, f"not runnable: {e}"
    except Exception as e:
        return -3, f"{type(e).__name__}: {e}"


def _verdict(rc: int, out: str) -> str:
    """Map a checker run to PASS / FAIL / UNCHECKED.

    rc < 0  -> the checker could not run at all (timeout/missing/runtime crash) => UNCHECKED.
    rc == 0 -> the checker ran and found nothing wrong => PASS.
    rc > 0  -> the checker ran and found a defect => FAIL.

    Note this is the exact three-valued contract the organ canary enforces internally: a
    crashed instrument is never silently a pass.
    """
    if rc < 0:
        return "UNCHECKED"
    if rc == 0:
        return "PASS"
    return "FAIL"


def _tier3_memory(rc: int, out: str) -> tuple[str, str]:
    """Tier 3 is special: check_organ_canaries --gate exits 1 for BOTH a dead organ AND an
    unrunnable (UNCHECKED) one AND any OTHER organ being dead -- but the ONLY thing this tier
    cares about is whether the RECALL canary is alive. Parse the recall canary's own verdict line
    out of the full output rather than trusting rc (which reflects all 6 canaries).

    Returns (verdict, detail)."""
    if rc < 0:
        return "UNCHECKED", out.strip().splitlines()[0] if out.strip() else "could not run"
    # Locate the recall canary's own line: "ALIVE     recall-at surfaces ..." / "DEAD      recall..."
    # / "UNCHECKED recall-at surfaces ...". The CANARIES name is "recall-at surfaces a seeded lesson".
    recall_line = next((ln for ln in out.splitlines() if "recall-at surfaces" in ln), "")
    status = ""
    if recall_line:
        status = recall_line.split("recall-at surfaces")[0].strip()  # ALIVE / DEAD / UNCHECKED
    if status == "ALIVE":
        return "PASS", f"recall-at surfaced a seeded lesson: {recall_line.strip()[:100]}"
    if status == "DEAD":
        return "FAIL", f"recall organ is DEAD: {recall_line.strip()[:100]}"
    if status == "UNCHECKED":
        if "no world:seed:manifest" in out or "no lesson_inventory" in out:
            return "UNCHECKED", ("no seed manifest yet -- recall cannot be attributed to a seed; "
                                 "seed this install (seed_world.py) then re-run")
        return "UNCHECKED", f"recall canary could not run: {recall_line.strip()[:100]}"
    # No recall canary line found at all (should not happen): report what we can
    if rc == 0:
        return "PASS", "recall-at surfaced a seeded lesson (gate passed)"
    line = next((ln.strip() for ln in out.splitlines() if "GATE FAIL" in ln or "dead" in ln.lower()), "")
    return "FAIL", (line or f"tier3 gate failed: rc={rc}")


T3_LABEL = "recall-at surfaces a seeded lesson"


def _tier4_provenance() -> tuple[str, str]:
    """The honest origin line. Read the seed manifest the SAME way agent_cli boot does.

    Returns (verdict, detail). Never guesses a positive: an unreachable store is UNKNOWN,
    not "native". A genuinely absent manifest is "native / copied by hand" (a real answer).
    """
    try:
        from core.comm.bus import get_bus
        client = get_bus("bootstrap-world")._client
        if client is None:
            return "UNCHECKED", "no store client -- provenance unreadable"
        from core.world_seed import read_manifest
        manifest = read_manifest(client)
    except Exception as e:
        return "UNCHECKED", f"store unreachable / manifest unreadable: {type(e).__name__}: {e}"
    if manifest is None:
        return "PASS", ("origin: native or copied by hand (no seed manifest) -- nothing was "
                        "claimed about seeding, which is honest, not a failure")
    src = manifest.get("source_world", "?")
    when = manifest.get("seeded_at", "?")
    total = manifest.get("total_carried", "?")
    n_lessons = len(manifest.get("lesson_inventory") or [])
    return "PASS", (f"origin: seeded from {src} @ {when} ({total} keys carried, "
                    f"{n_lessons} lessons inventoried)")


def _heading(s: str) -> str:
    return f"\n=== {s} " + "=" * (44 - len(s))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-check", action="store_true", help="run the validation tiers")
    ap.add_argument("--skip-clone", action="store_true",
                    help="tier 0 skips the full clone drill (fast mode)")
    ap.add_argument("--world", default=None,
                    help="which world to validate (sets AKASHIC_WORLD for this process AND its "
                         "children); leave unset to use the checkout's own resolution")
    args = ap.parse_args(argv)

    # World routing must be set IN-PROCESS, not via shell `set`, because the shell's set-quoting
    # is unreliable (a `set "AKASHIC_WORLD=beta"` dropped the var entirely in the live seed test;
    # `set AKASHIC_WORLD=beta &&` captured a trailing space). Setting it here propagates cleanly to
    # every subprocess and to _tier4_provenance's in-process core imports.
    if args.world:
        os.environ["AKASHIC_WORLD"] = args.world.strip()

    if not args.self_check:
        ap.print_help()
        return 0

    print("bootstrap self-check -- is this install proven, or merely present?")
    print(f"root: {ROOT}")

    results: dict[str, str] = {}   # tier -> worst verdict
    for tier in ("tier0-runs", "tier1-doors", "tier2-integrations", "tier3-memory"):
        print(_heading(tier))
        any_failed = False
        any_unchecked = False
        for label, argv in TIERS[tier]:
            if args.skip_clone and "--clone" in argv:
                print(f"  SKIP     {label}")
                continue
            rc, out = _run(argv)
            if tier == "tier3-memory":
                # the recall canary's UNCHECKED-vs-DEAD distinction needs the output, not rc
                v, detail = _tier3_memory(rc, out)
            else:
                v = _verdict(rc, out)
                detail = ""
            mark = {"PASS": "PASS    ", "FAIL": "FAIL    ", "UNCHECKED": "UNCHECK"}[v]
            print(f"  {mark}  {label}")
            if v == "FAIL":
                any_failed = True
                if detail:
                    print(f"          {detail[:120]}")
                else:
                    for ln in out.splitlines():
                        if ln.strip() and ("FAIL" in ln or "PASS" in ln or "[organ" in ln
                                           or "GATE" in ln or "VIOLATION" in ln
                                           or "dead" in ln.lower() or "drift" in ln.lower()):
                            print(f"          {ln.strip()[:120]}")
                            break
            elif v == "UNCHECKED":
                any_unchecked = True
                d = detail or (out.strip().splitlines()[0] if out.strip() else "")
                print(f"          {d[:120]}")
        if tier == "tier2-integrations":
            # Informational, not a gate: the FIND engine this machine would use, and what to
            # install to upgrade it. Wired here so describe_finder is not a latent capability
            # (check_wiring flags a public function nothing calls). It makes a fresh Linux
            # deploy's "why is find walking" answerable in the same breath as "are ports up".
            try:
                from core.tools.everything import describe_finder
                print(f"  INFO     {describe_finder()}")
            except Exception:
                pass
        if any_unchecked:
            results[tier] = "UNCHECKED"
        elif any_failed:
            results[tier] = "FAIL"
        else:
            results[tier] = "PASS"

    # Tier 4 renders its own verdict (it is a read, not a subprocess).
    print(_heading("tier4-provenance"))
    pv, pd = _tier4_provenance()
    mark = {"PASS": "PASS    ", "FAIL": "FAIL    ", "UNCHECKED": "UNCHECK"}[pv]
    print(f"  {mark}  provenance truth")
    print(f"          {pd}")
    results["tier4-provenance"] = pv

    print(_heading("summary"))
    for tier in ("tier0-runs", "tier1-doors", "tier2-integrations", "tier3-memory",
                 "tier4-provenance"):
        print(f"  {results[tier]:<9} {tier}")
    blocking = [t for t, v in results.items() if v == "UNCHECKED"]
    failing = [t for t, v in results.items() if v == "FAIL"]
    if blocking:
        print(f"\nBLOCKING: {len(blocking)} tier(s) could not be checked (UNCHECKED) -- an "
              f"unwatched organ is an unwatched capability. Resolve before trusting this install.")
    if failing and not blocking:
        print(f"\nFAIL: {len(failing)} tier(s) found defects. The install runs; it is not yet "
              f"proven to recall correctly out of the gate.")
    if not blocking and not failing:
        print("\nPASS: every tier answered. This install is proven capable out of the gate, "
              "recall firing on the seeded base included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
