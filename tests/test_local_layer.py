"""Pins for the Local layer (modular-core detangle, phase 1).

WHAT THIS DEFENDS
-----------------
`local/` is where instance VALUES live so that a fork edits data instead of core code. Two ways
that can go wrong, and both render as a clean report rather than as a failure:

  1. THE DATA DRIFTS AWAY FROM THE TREE. An entry point listed but no longer present silently
     SHRINKS the wiring gate's field of view -- the module behind it reports built-not-wired
     forever, or worse, stops being looked for at all. `check_wiring` filters production files by
     `os.path.exists`, so a typo in data is invisible to it. Hence the existence pin below.
  2. THE LOADER LIES SOFTLY. A loader that returns `{}` for a missing file turns "this deployment
     has no local layer" into "this deployment has no entry points" -- the invisible-absence shape
     the repo has paid for repeatedly. Hence the refusal pins.

The third pin is the one that makes the move *provable* rather than asserted: check_wiring's live
ENTRY_POINTS/EXCEPTIONS must equal what the data declares (plus the two enumerations, which stay
in code on purpose).

Run: py tests/test_local_layer.py   (or via pytest)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

from core.local import (                                          # noqa: E402
    LocalDataMissing,
    instance_root,
    load,
    local_dir,
    local_path,
    optional,
    status,
    strings,
    why_of,
)


# --------------------------------------------------------------------------- the shipped data
def test_the_local_layer_ships_a_wiring_file():
    d = local_dir()
    assert d.is_dir(), f"the Local layer's directory is missing: {d}"
    assert local_path("wiring").is_file(), f"local/wiring.json is missing under {d}"
    data = load("wiring")
    assert data["entry_points"] and data["exceptions"], data.keys()
    print(f"\n--- local layer ---\n  {d} carries {len(data['entry_points'])} entry point(s), "
          f"{len(data['exceptions'])} exception(s)")


def test_every_declared_entry_point_exists():
    """A listed entry point that is GONE narrows the gate silently -- check_wiring cannot see it."""
    data = load("wiring")
    declared = strings(data["entry_points"], what="entry_point")
    gone = [p for p in declared if not os.path.exists(os.path.join(str(instance_root()), p))]
    assert not gone, (
        f"local/wiring.json declares entry point(s) that do not exist: {gone}. "
        "check_wiring filters production files by os.path.exists, so this SHRINKS the gate's "
        "field of view rather than failing it -- fix the path or delete the entry.")
    print(f"--- entry points ---\n  all {len(declared)} declared path(s) resolve OK")


def test_every_entry_point_carries_its_why():
    """The values moved out of Python comments; an undocumented entry is how a register stays
    accurate while ceasing to be about anything."""
    data = load("wiring")
    whys = why_of(data["entry_points"])
    undocumented = [p for p in strings(data["entry_points"]) if not whys.get(p)]
    assert not undocumented, (
        f"entry point(s) with no 'why': {undocumented}. Every one of these was added because a "
        "real module reported built-not-wired while being precisely wired; the reason is the "
        "value of the entry, not decoration.")
    print(f"--- provenance ---\n  every entry point carries its reason ({len(whys)}) OK")


def test_every_exception_carries_a_reason():
    """An exception with an empty reason is an amnesty wearing a backlog's name."""
    data = load("wiring")
    bad = []
    for path, entry in data["exceptions"].items():
        reason = entry.get("reason", "") if isinstance(entry, dict) else str(entry)
        if not reason.strip():
            bad.append(path)
    assert not bad, f"EXCEPTIONS entries with no reason: {bad}"
    print(f"--- exceptions ---\n  all {len(data['exceptions'])} carry a reason OK")


def test_no_secrets_in_the_committed_local_layer():
    """`local/` is COMMITTED, so a secret here is a secret in git history. Scans the data, not
    the prose: values and keys both, classed by the shapes secrets actually take."""
    secretish = ("secret", "token", "password", "passwd", "api_key", "apikey", "access_key",
                 "private_key", "webhook", "credential", "bearer", "auth")

    def walk(obj, trail):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from walk(v, trail + [str(k)])
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from walk(v, trail + [str(i)])
        else:
            yield trail, obj

    offenders = []
    for fname in status()["files"]:
        for trail, value in walk(load(fname[:-5]), [fname]):
            joined = " ".join(trail).lower()
            if any(s in joined for s in secretish):
                offenders.append("/".join(trail))
    assert not offenders, (
        f"secret-shaped key(s) in local/: {offenders}. Secrets live in the gitignored secret "
        "planes (AKASHIC_SECRETS_DIR); local/ ships in git.")
    print("--- secrets ---\n  no secret-shaped key in local/*.json OK")


# --------------------------------------------------------------------------- the loader's rules
def test_a_missing_file_refuses_and_names_itself(tmp_path):
    with pytest_raises(LocalDataMissing) as caught:
        load("wiring", root=tmp_path)
    assert "wiring.json" in str(caught), caught
    assert "UNKNOWN" in str(caught), (
        "the refusal must say that missing means UNKNOWN, not zero -- that sentence is the whole "
        "reason this raises instead of returning {}")
    print("--- refusal (absent) ---\n  missing file refuses loudly and names the path OK")


def test_a_corrupt_file_refuses_differently_from_an_absent_one(tmp_path):
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest_raises(LocalDataMissing) as caught:
        load("broken", root=tmp_path)
    assert "JSON" in str(caught), caught

    (tmp_path / "local" / "notanobject.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest_raises(LocalDataMissing) as caught:
        load("notanobject", root=tmp_path)
    assert "OBJECT" in str(caught).upper(), caught
    print("--- refusal (corrupt) ---\n  corrupt / wrong-shaped data refuses and says why OK")


def test_optional_tolerates_absence_but_not_corruption(tmp_path):
    assert optional("nothing-here", root=tmp_path) is None, "absent is a legitimate answer here"
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest_raises(LocalDataMissing):
        optional("broken", root=tmp_path)
    print("--- optional() ---\n  absent -> None, corrupt -> raises OK")


def test_status_separates_not_adopted_from_adopted_and_broken(tmp_path):
    empty = status(root=tmp_path)
    assert empty["exists"] is False and empty["files"] == [] and empty["unreadable"] == []
    assert empty["missing"] == ["wiring.json"], empty

    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "wiring.json").write_text("{not json", encoding="utf-8")
    broken = status(root=tmp_path)
    assert broken["exists"] is True and broken["missing"] == [], broken
    assert [f["file"] for f in broken["unreadable"]] == ["wiring.json"], broken
    print("--- status() ---\n  'not adopted' and 'adopted and broken' are different answers OK")


def test_strings_accepts_both_shapes_and_rejects_junk():
    assert strings(["a.py", {"path": "b.py", "why": "because"}]) == ["a.py", "b.py"]
    assert why_of(["a.py", {"path": "b.py", "why": "because"}]) == {"b.py": "because"}
    for junk in ([""], [{"why": "no path"}], [3]):
        try:
            strings(junk)
        except LocalDataMissing:
            continue
        raise AssertionError(f"strings() accepted junk: {junk!r}")
    print("--- shapes ---\n  string-or-{path,why} accepted, junk refused OK")


# --------------------------------------------------------------- the move is behaviour-identical
def test_check_wiring_reads_the_same_values_it_used_to_hardcode():
    """THE MIGRATION PIN: the gate's live values equal the data it now reads.

    ENTRY_POINTS = the declared ones plus the two rules that stay in code (every seat runner,
    every hook dir). EXCEPTIONS = the declared dict, verbatim. If this ever drifts, the gate and
    its data disagree and one of them is lying.
    """
    import check_wiring

    data = load("wiring")
    declared = strings(data["entry_points"], what="entry_point")
    enumerated = [p for p in check_wiring.ENTRY_POINTS if p not in declared]
    assert check_wiring.ENTRY_POINTS[:len(declared)] == declared, (
        "the declared entry points must come first, in file order -- the enumeration appends")
    for p in enumerated:
        assert (p.startswith("scripts/bifrost_runner_")
                or p.startswith("agent/harness/hooks/")
                or p.startswith("scripts/githooks/")), (
            f"an entry point appeared that is neither declared in local/wiring.json nor produced "
            f"by one of the two in-code enumerations: {p!r}")
    assert check_wiring.EXCEPTIONS == data["exceptions"], (
        "check_wiring.EXCEPTIONS has drifted from local/wiring.json")
    print(f"--- check_wiring parity ---\n  {len(declared)} declared + {len(enumerated)} "
          f"enumerated = {len(check_wiring.ENTRY_POINTS)} entry points; "
          f"{len(check_wiring.EXCEPTIONS)} exceptions, verbatim OK")


# ------------------------------------------------------------------------------ tiny pytest shim
class pytest_raises:
    """`with pytest_raises(Exc) as caught:` -- runs under pytest AND bare python.

    `str(caught)` is the exception's own message, because several pins assert on WHAT the
    refusal says (a refusal that does not name the path is a dead end for the reader).
    """

    def __init__(self, exc):
        self.exc = exc
        self.value = None
        self.message = ""

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            raise AssertionError(f"expected {self.exc.__name__}, nothing was raised")
        if not issubclass(et, self.exc):
            return False
        self.value = ev
        self.message = str(ev)
        return True

    def __str__(self):
        return self.message


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            if "tmp_path" in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
        except Exception as exc:                                       # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(("\nALL LOCAL-LAYER PINS PASSED" if not failures
           else f"\n{failures} FAILURE(S)"), )
    sys.exit(1 if failures else 0)
