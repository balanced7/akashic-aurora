"""Pins for the Core-purity RATCHET (modular-core detangle, phase 1; Rill's attack B).

WHY THESE PINS EXIST
--------------------
A ratchet that has never been shown to bite is a comment with a JSON file next to it. The three
ways this one can fail silently:

  1. It reports PASS when the baseline is gone. FIXED BY DESIGN (exit 2, refusal), and pinned
     here by running the real script with a baseline path that does not exist.
  2. It forbids the extraction it exists to enable. A per-file rule applied to a NEW file would
     make moving a verb body out of `agent_cli.py` into `verbs/` a failure, since the literals
     arrive in a file the baseline has never seen. Pinned: extraction that keeps the TOTAL flat
     must PASS.
  3. It lets debt in through the door it left open. Same rule, other side: a new file whose
     literals push the TOTAL up must FAIL. Pinned.

Run: py tests/test_core_purity_ratchet.py   (or via pytest)
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(ROOT, "scripts", "checkers", "check_core_purity.py")
BASELINE = os.path.join(ROOT, "scripts", "checkers", "core_purity_baseline.json")

sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))
import check_core_purity as purity                                        # noqa: E402


# ------------------------------------------------------------------ the shipped freeze & the gate
def test_the_baseline_ships_and_the_live_tree_passes():
    assert os.path.isfile(BASELINE), f"the committed baseline is missing: {BASELINE}"
    doc = json.load(open(BASELINE, encoding="utf-8"))
    assert isinstance(doc.get("files"), dict) and doc["files"], doc.keys()
    assert isinstance(doc.get("total"), int), doc.keys()
    rc = purity.main([])
    assert rc == 0, "the live tree is over its frozen Local-in-Core baseline"
    print(f"\n--- gate ---\n  {doc['total']} frozen literal(s) over {len(doc['files'])} "
          f"file(s); live tree at or below it OK")


def test_a_missing_baseline_REFUSES_rather_than_passing(tmp_path):
    """The whole point: unknown is not zero. Runs the REAL script, so the exit code is real."""
    gone = tmp_path / "no_such_baseline.json"
    r = subprocess.run([sys.executable, CHECKER, "--baseline", str(gone)],
                       capture_output=True, text=True)
    assert r.returncode == 2, (
        f"a missing baseline must REFUSE with rc 2, got {r.returncode}. stdout={r.stdout[:300]!r}")
    assert "MISSING" in r.stderr and "UNKNOWN" in r.stderr, r.stderr[:400]
    assert "PASS" not in r.stdout, "a refusal must not also print a pass"
    print("--- refusal ---\n  missing baseline -> rc 2, says UNKNOWN, no PASS OK")


def test_a_corrupt_baseline_also_refuses(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    r = subprocess.run([sys.executable, CHECKER, "--baseline", str(bad)],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "UNREADABLE" in r.stderr, (r.returncode, r.stderr[:300])
    print("--- refusal (corrupt) ---\n  unreadable baseline -> rc 2 OK")


# ------------------------------------------------------------------------------- the three rules
def _base(files):
    return {"total": sum(sum(v.values()) for v in files.values()), "files": files}


def test_a_rise_in_one_file_FAILS_and_names_the_file_and_class():
    base = _base({"agent_cli.py": {"seat": 168, "path": 8, "port": 7, "fork": 46}})
    cur = {"agent_cli.py": {"seat": 169, "path": 8, "port": 7, "fork": 46}}
    failures, _drops, _new = purity.compare(cur, base)
    assert failures and failures[0][0] == "file", failures
    assert "agent_cli.py" in failures[0][1] and "seat" in failures[0][1], failures
    print("--- rise (per file) ---\n  a seat literal added to a frozen file FAILS, named OK")


def test_extraction_that_keeps_the_total_flat_PASSES():
    """THE MIGRATION FREEDOM. Literals moving out of a frozen file into a new one are not new debt,
    and a gate that said otherwise would forbid the very detangle it guards."""
    base = _base({"agent_cli.py": {"seat": 168, "path": 0, "port": 0, "fork": 0}})
    cur = {"agent_cli.py": {"seat": 160, "path": 0, "port": 0, "fork": 0},
           "verbs/groups/coord/scene.py": {"seat": 8, "path": 0, "port": 0, "fork": 0}}
    failures, drops, new = purity.compare(cur, base)
    assert not failures, f"extraction keeping the total flat must pass, got {failures}"
    assert new == ["verbs/groups/coord/scene.py"], new
    assert drops and "agent_cli.py" in drops[0], drops
    print("--- extraction ---\n  moving literals into a new verbs/ file with a flat total PASSES OK")


def test_a_new_file_that_raises_the_total_FAILS():
    """The other door: the same freedom is not a licence to ADD Local-in-Core."""
    base = _base({"agent_cli.py": {"seat": 168, "path": 0, "port": 0, "fork": 0}})
    cur = {"agent_cli.py": {"seat": 168, "path": 0, "port": 0, "fork": 0},
           "verbs/groups/new/thing.py": {"seat": 2, "path": 0, "port": 0, "fork": 0}}
    failures, _drops, _new = purity.compare(cur, base)
    assert failures and failures[0][0] == "total", failures
    print("--- new debt ---\n  a new file that pushes the total up FAILS at the total rule OK")


def test_a_drop_is_reported_not_required():
    base = _base({"agent_cli.py": {"seat": 10, "path": 0, "port": 0, "fork": 0}})
    cur = {"agent_cli.py": {"seat": 7, "path": 0, "port": 0, "fork": 0}}
    failures, drops, _new = purity.compare(cur, base)
    assert not failures and drops, (failures, drops)
    print("--- paydown ---\n  falling counts pass and are reported for re-freezing OK")


# ------------------------------------------------------------------------------------- counting
def test_the_four_classes_are_counted_and_prose_counts_too():
    """Prose counts, on purpose: the census counted raw text, so a docstring mention is a hit.

    Stated as a pin rather than left implicit, because the known cost is real -- someone reading
    '229' should know it includes prose -- and because a silent change to that (weighting code
    above comments) would change what every frozen number means.

    The four classes are LENSES, not a partition: `serge` appears in both the seat list and the
    fork pattern, so one mention is counted twice. That is deliberate -- each class answers a
    different question ("does Core name a seat" / "does Core name a fork") and a value can answer
    both -- but it means the total is a weighted sum, not a count of distinct literals.
    """
    counts = purity.count_text(
        'x = "claude"      # a seat id\n'
        'y = r"E:\\AI-Setup"\n'
        'z = 8796\n'
        'w = "serge"\n'
    )
    assert counts == {"seat": 2, "path": 1, "port": 1, "fork": 1}, counts
    assert purity.total_of(purity.count_text("# claude rosters the fleet")) == 2
    print("--- counting ---\n  seat/path/port/fork each counted; prose counts too (documented); "
          "serge counts in two classes OK")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            if "tmp_path" in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
                import tempfile
                from pathlib import Path
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
        except Exception as exc:                                          # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print("\nALL CORE-PURITY PINS PASSED" if not failures else f"\n{failures} FAILURE(S)")
    sys.exit(1 if failures else 0)
