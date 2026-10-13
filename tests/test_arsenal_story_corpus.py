"""Story corpus (arsenal/story_corpus.py): the private cadence oracle the live cadence judge is proven against.

The tracked tests here are SYNTHETIC: invented progressions only (Dm G C in C major, a G -> Am deceptive move), never
anything lifted from a real practice session. The corpus test runs the oracle on one real session when the private
state/arsenal/performance folder exists (it is skipped otherwise), writes only under state/arsenal/story/_test/<uuid>/
(gitignored, removed afterwards; never pytest's kept tmp folders), and checks the oracle against practice itself
without hard-coding anything about the session.
"""
import contextlib
import io
import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import practice as pr  # noqa: E402
from arsenal import story_corpus as sc  # noqa: E402
from arsenal.performance import PerformanceStore  # noqa: E402

NODE = shutil.which("node")
PERFORMANCE = ROOT / "state" / "arsenal" / "performance"
PRIVATE_TEST = ROOT / "state" / "arsenal" / "story" / "_test"
ORACLE_MANIFEST = sc.DEFAULT_OUT / "manifest.json"
C_MAJOR = {"key": "C major", "tonic": 0, "mode": "major"}
WINDOW_FIELDS = {"n", "start_ms", "end_ms", "at", "root_pc", "pcs", "mask", "bass_pc", "low_bass", "third",
                 "texture", "area"}


def check_contract(o: dict) -> None:
    assert o["api"] == "arsenal.story.oracle/v1"
    assert o["practice_api"] == pr.API
    assert set(o) >= {"sid", "areas", "windows", "raw_cadences", "cadences", "counts"}
    for i, a in enumerate(o["areas"]):
        assert a["id"] == i and 0 <= a["tonic"] <= 11 and a["mode"] in ("major", "minor") and isinstance(a["key"], str)
    for i, w in enumerate(o["windows"]):
        assert set(w) == WINDOW_FIELDS
        assert w["n"] == i
        assert w["pcs"] == sorted(set(w["pcs"])) and all(0 <= p <= 11 for p in w["pcs"])
        assert w["mask"] == sum(1 << p for p in w["pcs"])
        assert w["root_pc"] is None or 0 <= w["root_pc"] <= 11
        assert w["bass_pc"] is None or 0 <= w["bass_pc"] <= 11
        assert w["third"] in ("major", "minor", None)
        assert isinstance(w["low_bass"], bool) and isinstance(w["texture"], str)
        assert w["area"] is None or 0 <= w["area"] < len(o["areas"])
    for c in o["raw_cadences"]:
        assert set(c) == {"n", "kind", "start_ms", "end_ms", "key"}
        assert 1 <= c["n"] < len(o["windows"])
    counts = o["counts"]
    assert counts["windows"] == len(o["windows"])
    assert sum(counts["raw_cadence_kinds"].values()) == len(o["raw_cadences"])
    assert set(counts) == {"windows", "raw_cadence_kinds", "lydian_4", "suspensions", "suspensions_resolved"}
    # the collapse only folds repeated deceptive moves into their first: every raw cadence is counted once
    assert sum(c.get("times", 1) for c in o["cadences"]) == len(o["raw_cadences"])


# ============================================================================================ synthetic rows
def row(i, start, end, root, pcs, bass, third, area=C_MAJOR, texture="chord"):
    """A window shaped like practice._row's output, with the underscore fields _cadence reads (invented)."""
    return {"i": i, "start_ms": start, "end_ms": end, "at": pr.clock(start), "_root_pc": root, "_pcs": pcs,
            "_bass_pc": bass, "_low_bass": True, "third": third, "texture": texture, "_area": area,
            "key": area["key"] if area else None, "name": None, "label": None, "analysed_as": None, "number": None,
            "bass": {"note": None}}


def synthetic_rows():
    other = {"key": "G major", "tonic": 7, "mode": "major"}
    return [
        row(0, 0, 1900, 2, [2, 5, 9], 2, "minor"),        # Dm
        row(1, 2000, 3900, 7, [7, 11, 2], 7, "major"),    # G
        row(2, 4000, 5900, 0, [0, 4, 7], 0, "major"),     # C   <- 2 -> 5 -> 1
        row(3, 6000, 7900, 7, [7, 11, 2, 5], 7, "major"),  # G7
        row(4, 8000, 9900, 9, [9, 0, 4], 9, "minor"),     # Am  <- deceptive
        row(5, 20000, 21900, 7, [7, 11, 2], 7, "major", area=other),
        row(6, 22000, 23900, None, [1], None, None, area=None),
    ]


def test_oracle_body_on_synthetic_rows_captures_raw_cadences_and_area_ids():
    rows = synthetic_rows()
    body = sc.oracle_body(rows)
    assert [(c["n"], c["kind"]) for c in body["raw_cadences"]] == [
        (2, "2 -> 5 -> 1 (authentic)"), (4, "5 -> 6m (deceptive)")]
    first = body["raw_cadences"][0]
    assert (first["start_ms"], first["end_ms"], first["key"]) == (0, 5900, "C major")
    assert [a["key"] for a in body["areas"]] == ["C major", "G major"]
    assert [w["area"] for w in body["windows"]] == [0, 0, 0, 0, 0, 1, None]
    g7 = body["windows"][3]
    assert g7["pcs"] == [2, 5, 7, 11] and g7["mask"] == (1 << 2) | (1 << 5) | (1 << 7) | (1 << 11)
    assert body["windows"][6]["root_pc"] is None and body["windows"][6]["bass_pc"] is None
    # the raw list is exactly what practice._cadence answers, n by n
    assert [c["n"] for c in body["raw_cadences"]] == [n for n in range(1, len(rows)) if pr._cadence(rows, n)]


def test_capturing_restores_findings_even_on_error():
    original = pr._findings
    with pytest.raises(RuntimeError):
        with sc.capturing():
            assert pr._findings is not original
            raise RuntimeError("boom")
    assert pr._findings is original


# ========================================================================================= synthetic events
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name: str) -> int:
    return (int(name[1:]) + 1) * 12 + PC[name[0]]


def progression(chords, seconds=2.0, repeats=3):
    """Block chords, each held `seconds` less 100 ms, no pedal: page-style on/off/sound_end events (invented)."""
    events, t, step = [], 0, int(seconds * 1000)
    for _ in range(repeats):
        for chord in chords:
            for name in chord:
                events.append({"t_ms": t, "kind": "on", "note": midi(name), "vel": 70})
            for name in chord:
                events.append({"t_ms": t + step - 100, "kind": "off", "note": midi(name)})
                events.append({"t_ms": t + step - 100, "kind": "sound_end", "note": midi(name), "by": "release"})
            t += step
    return events


@pytest.mark.skipif(NODE is None, reason="node is needed to run piano.js Theory.detect inside practice.analyze")
def test_oracle_from_synthetic_events_through_analyze():
    events = progression([["D3", "F4", "A4", "D5"], ["G2", "B3", "D4", "G4"], ["C3", "E4", "G4", "C5"]])
    original = pr._findings
    oracle, doc = sc.oracle_from_events(events, sid="synthetic")
    assert pr._findings is original
    check_contract(oracle)
    assert oracle["sid"] == "synthetic"
    assert len(oracle["windows"]) == len(doc["windows"])
    assert any("authentic" in c["kind"] for c in oracle["raw_cadences"]), oracle["raw_cadences"]
    assert oracle["cadences"] == doc["findings"]["cadences"]
    assert all(not k.startswith("_") for w in doc["windows"] for k in w)  # analyze still strips its fields


# ========================================================================================= guards and stamps
def test_rules_sha_fingerprints_the_five_practice_rules():
    import hashlib
    import inspect
    src = "".join(inspect.getsource(f) for f in
                  (pr._cadence, pr._passing_moment, pr._bass_dominant, pr._chordal, pr._rel))
    src += "".join("\n" + f"{name}={getattr(pr, name)!r}" for name in
                   ("CADENCE_GAP_MS", "CADENCE_ARRIVAL_MS", "DECEPTIVE_LEARNED"))
    assert sc.rules_sha() == hashlib.sha256(src.encode("utf-8")).hexdigest()


def test_rules_sha_moves_when_a_rule_constant_moves(monkeypatch):
    before = sc.rules_sha()
    monkeypatch.setattr(pr, "CADENCE_GAP_MS", pr.CADENCE_GAP_MS + 50)
    assert sc.rules_sha() != before


@pytest.mark.parametrize("where", ["tests/fixtures", "docs", "."])
def test_out_dir_inside_the_repo_but_outside_state_is_refused(where, capsys):
    target = (ROOT / where).resolve()
    before = sorted(p.name for p in target.iterdir())
    # refused before the store is opened or a session is read: a made-up sid is never looked up
    assert sc.main(["oracle", "--session", "no-such-session", "--out-dir", str(target)]) == 2
    assert "refusing --out-dir" in capsys.readouterr().err
    assert sorted(p.name for p in target.iterdir()) == before  # nothing written there


def test_out_dir_rules():
    assert sc.refused_out_dir(ROOT / "tests" / "fixtures")
    assert sc.refused_out_dir(ROOT / "state" / ".." / "tests")  # resolved before it is judged
    assert sc.refused_out_dir(ROOT / "state" / "arsenal" / "story" / "oracle") is None
    assert sc.refused_out_dir(sc.DEFAULT_OUT) is None
    assert sc.refused_out_dir(ROOT.parent / "somewhere-outside-the-repo") is None


def test_private_oracle_is_fresh():
    if not ORACLE_MANIFEST.is_file():
        pytest.skip("no private oracle manifest here (state/arsenal/story/oracle/manifest.json is absent)")
    # plain locals: a failure prints the two hashes only, never the private manifest pytest would otherwise expand
    stamp = str(json.loads(ORACLE_MANIFEST.read_text(encoding="utf-8")).get("rules_sha"))
    current = sc.rules_sha()
    assert stamp == current, (
        "the private cadence oracle was built from other practice rules than these (rules_sha differs): "
        "rebuild it with 'py -m arsenal.story_corpus oracle'")


# =================================================================================================== corpus
def _small_real_session():
    """The smallest stored session the private oracle manifest says has windows and at least one raw cadence, so the
    comparison below can fail (a session with no cadences would compare two empty lists)."""
    if not PERFORMANCE.is_dir() or not ORACLE_MANIFEST.is_file():
        return None
    listed = json.loads(ORACLE_MANIFEST.read_text(encoding="utf-8")).get("sessions") or {}
    sized = sorted((p.stat().st_size, p.parent.name) for p in PERFORMANCE.glob("*/events.jsonl") if p.stat().st_size > 0)
    for _, sid in sized:
        m = listed.get(sid) or {}
        if m.get("windows", 0) >= 2 and m.get("raw_cadences", 0) >= 1:
            return sid
    return None


def test_oracle_on_one_real_session_matches_practice():
    sid = _small_real_session()
    if sid is None:
        pytest.skip("no private session with a cadence here (state/arsenal/performance or the oracle manifest is "
                    "absent, or no session has one)")
    # private output stays under state/ (gitignored), never in pytest's kept tmp folders; removed afterwards
    out = PRIVATE_TEST / uuid.uuid4().hex
    try:
        _check_real_session(sid, out)
    finally:
        shutil.rmtree(out, ignore_errors=True)
        with contextlib.suppress(OSError):
            PRIVATE_TEST.rmdir()  # only when empty


def _check_real_session(sid: str, out: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()):  # its summary counts his playing: keep it out of a failure log
        code = sc.main(["oracle", "--session", sid, "--out-dir", str(out)])
    assert code == 0
    path = out / f"{sid}.json"
    assert b"\r" not in path.read_bytes()
    oracle = json.loads(path.read_text(encoding="utf-8"))
    check_contract(oracle)
    assert oracle["sid"] == sid
    current = sc.rules_sha()
    oracle_stamp = str(oracle.get("rules_sha"))
    assert oracle_stamp == current
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["totals"]["sessions"] == 1 and sid in manifest["sessions"] and not manifest["failed"]
    manifest_stamp = str(manifest.get("rules_sha"))
    assert manifest_stamp == current

    # practice itself, through a wrapper written here: _cadence over the same rows gives the same raw list
    seen = {}
    original = pr._findings

    def wrapper(rows, areas, ctx):
        seen["raw"] = [(n, c["kind"], c["start_ms"], c["end_ms"], c["key"])
                       for n in range(1, len(rows)) for c in [pr._cadence(rows, n)] if c]
        seen["n"] = len(rows)
        return original(rows, areas, ctx)

    pr._findings = wrapper
    try:
        doc = pr.load_session(PerformanceStore(), sid)["doc"]
    finally:
        pr._findings = original
    # booleans, not lists: a failure must not print his private progressions into a test log
    nonvacuous = seen["n"] >= 2 and len(seen["raw"]) >= 1
    assert nonvacuous, "the chosen session has no cadence to compare (details withheld: private)"
    same_raw = [(c["n"], c["kind"], c["start_ms"], c["end_ms"], c["key"]) for c in oracle["raw_cadences"]] == seen["raw"]
    assert same_raw, "the oracle's raw cadences differ from practice._cadence (details withheld: private)"
    same_windows = len(oracle["windows"]) == seen["n"] == len(doc["windows"])
    assert same_windows, "the oracle's window count differs from practice's rows (details withheld: private)"
    same_cadences = oracle["cadences"] == json.loads(json.dumps(doc["findings"]["cadences"], default=str))
    assert same_cadences, "the oracle's collapsed cadences differ from practice's findings (details withheld: private)"
