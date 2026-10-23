"""Pins for the round-2 revision of the beat-tracker ruler (beatbench, the keylab CLI's beatbench / record /
annotate / confirm / tapkey verbs, beatsync's capture timing), after three independent reviews (2026-10-23).

Each pin is one defect the reviewers found, stated as the behaviour that must hold; the module docstring of each
section names the defect. Small cases and temp files only, so the file runs in well under a minute.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import types

import numpy as np
import pytest

from arsenal.keylab import beatbench as BB
from arsenal.keylab import beatsync as BS
from arsenal.keylab import __main__ as CLI

RATE, HOP = 22050, 512


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    """No pin may touch the real hash cache, the real recordings, or the real tracker registry."""
    monkeypatch.setattr(BB, "HASH_CACHE_PATH", None)
    monkeypatch.setattr(BB, "_HASH_MEM", {})
    monkeypatch.setattr(BB, "_HASH_LOADED", True)
    monkeypatch.setattr(BB, "RECORDINGS_DIR", str(tmp_path / "recordings"))
    monkeypatch.setattr(BB, "TRACKERS", dict(BB.TRACKERS))


def _scripted(predict_fn, rate=RATE, bpm=120.0, offset=0.5, events=True):
    """A tracker that announces the exact beats as they pass and predicts with predict_fn(now, beats)."""
    def factory(r, hop, seed_bpm=None):
        class T:
            def __init__(self):
                self.now, self.i = 0.0, 0
                self.beats = np.arange(offset, 60.0, 60.0 / bpm)
                self.calls = 0

            def feed(self, block):
                self.now += len(block) / r
                out = []
                while events and self.i < len(self.beats) and self.beats[self.i] <= self.now:
                    out.append({"t_beat": float(self.beats[self.i]), "bpm": bpm, "phase": 0.0, "confidence": 1.0})
                    self.i += 1
                return out

            def predict(self, now):
                self.calls += 1
                factory.calls += 1
                return predict_fn(now, self.beats)
        return T()
    factory.calls = 0
    return factory


def _next(now, beats):
    return float(beats[beats > now][0])


# --- 1. predictions are what the lights use ------------------------------------------------------------------------

def test_predict_is_asked_after_every_block_like_beatsync():
    case = BB.synth_case("p", 120, secs=4.0, rate=RATE)
    f = _scripted(lambda now, b: [{"t_beat": _next(now, b), "bpm": 120.0, "phase": 0.0, "confidence": 1.0}])
    res = BB.run_tracker(f, case, HOP)
    n_blocks = len(case.audio) // HOP
    assert f.calls == n_blocks and len(res["predictions"]) == n_blocks


def test_the_scored_prediction_is_ahead0_not_the_best_item_in_the_list():
    """The lights paint ahead[0]. A list whose first item is 80 ms late (the exact beat second) must score 80 ms,
    and a list that leads with a beat already past must score as the miss it is."""
    case = BB.synth_case("p", 120, secs=12.0, rate=RATE)

    def late_first(now, b):
        n = _next(now, b)
        return [{"t_beat": n + 0.08, "bpm": 120.0, "phase": 0, "confidence": 1}, {"t_beat": n, "bpm": 120.0,
                                                                                  "phase": 0, "confidence": 1}]
    row = BB.score(case, BB.run_tracker(_scripted(late_first), case, HOP))
    assert row["pred_err_ms"] == pytest.approx(80.0, abs=1.0) and row["pred_hit"] == 0.0

    def stale_first(now, b):
        n = _next(now, b)
        return [{"t_beat": n - 0.5, "bpm": 120.0, "phase": 0, "confidence": 1}, {"t_beat": n, "bpm": 120.0,
                                                                                 "phase": 0, "confidence": 1}]
    row = BB.score(case, BB.run_tracker(_scripted(stale_first), case, HOP))
    assert row["pred_err_ms"] == pytest.approx(500.0, abs=1.0) and row["pred_hit"] == 0.0


def _problems(predict_fn=None, bpm_value=120.0, has_predict=True):
    def factory(r, hop, seed_bpm=None):
        class T:
            def __init__(self):
                self.now, self.i = 0.0, 0
                self.beats = np.arange(0.5, 60.0, 0.5)

            def feed(self, block):
                self.now += len(block) / r
                out = []
                while self.i < len(self.beats) and self.beats[self.i] <= self.now:
                    out.append({"t_beat": float(self.beats[self.i]), "bpm": bpm_value, "phase": 0.0,
                                "confidence": 1.0})
                    self.i += 1
                return out
        if has_predict:
            T.predict = lambda self, now: predict_fn(now, self.beats)
        return T()
    return BB.check_tracker(factory, rate=RATE)


def _good(now, b):
    nxt = b[b > now][:3]
    return [{"t_beat": float(x), "bpm": 120.0, "phase": 0.0, "confidence": 1.0} for x in nxt]


def test_the_contract_accepts_a_tracker_that_predicts_properly():
    assert _problems(_good) == []


def test_the_contract_requires_predict():
    assert any("predict() missing" in p for p in _problems(has_predict=False))


def test_the_contract_rejects_unsorted_past_or_vanishing_predictions():
    unsorted = lambda now, b: list(reversed(_good(now, b)))
    past = lambda now, b: [{"t_beat": now - 0.1, "bpm": 120.0, "phase": 0.0, "confidence": 1.0}] + _good(now, b)
    vanishing = lambda now, b: _good(now, b) if now < 3.0 else []
    assert any("sorted" in p for p in _problems(unsorted))
    assert any("before `now`" in p for p in _problems(past))
    assert any("empty after lock" in p for p in _problems(vanishing))


@pytest.mark.parametrize("bad", [0.0, -120.0, float("nan"), float("inf"), None])
def test_the_contract_rejects_an_observed_beat_without_a_real_bpm(bad):
    assert any("bpm must be a finite number" in p for p in _problems(_good, bpm_value=bad))


# --- 2. grid steadiness from beat times; missing bpm counted -------------------------------------------------------

def test_ibi_metrics_see_the_beat_times_that_display_smoothing_hides():
    """A tracker that DISPLAYS a rock-steady 128 while its beats wobble 0.42 / 0.52 s apart: the display metrics
    say perfect, the beat-time metrics must not."""
    t, beats = 5.0, []
    for i in range(40):
        beats.append({"t_beat": t, "bpm": 128.0})
        t += 0.42 if i % 2 else 0.52
    assert BB.drift(beats) == {"bpm_missing": 0, "bpm_spread": 0.0, "tempo_flips": 0}
    ibi = BB.ibi_drift(beats)
    assert ibi["ibi_spread"] > 0.15 and ibi["ibi_flips"] >= 30


def test_ibi_metrics_are_zero_for_a_steady_grid_and_ignore_the_gap_between_spans():
    a = [{"t_beat": 5.0 + i * 0.5, "bpm": 120.0} for i in range(20)]
    b = [{"t_beat": 30.0 + i * 0.5, "bpm": 120.0} for i in range(20)]
    with_spans = BB.ibi_drift(a + b, spans=[[0.0, 15.0], [29.9, 45.0]])
    assert with_spans == {"ibi_spread": 0.0, "ibi_flips": 0}
    assert BB.ibi_drift(a + b)["ibi_flips"] >= 1, "without spans the breakdown reads as a tempo change"


def test_drift_counts_beats_with_no_usable_bpm_instead_of_dropping_them():
    beats = [{"t_beat": 5.0 + i * 0.5, "bpm": 120.0} for i in range(10)]
    beats += [{"t_beat": 11.0, "bpm": None}, {"t_beat": 11.5, "bpm": 0}, {"t_beat": 12.0, "bpm": float("nan")},
              {"t_beat": 12.5}]
    d = BB.drift(beats)
    assert d["bpm_missing"] == 4 and d["bpm_spread"] == 0.0


def test_octave_error_pairs_each_bpm_with_its_own_beat():
    """One early beat without a bpm used to shift every later bpm onto the wrong beat (zip of a filtered list)."""
    case = BB.synth_case("o", 120, secs=20.0, rate=RATE)
    beats = [{"t_beat": 1.0, "_at": 1.0}]
    beats += [{"t_beat": 1.5 + i * 0.5, "bpm": 240.0, "_at": 1.5 + i * 0.5} for i in range(7)]
    beats += [{"t_beat": 5.0 + i * 0.5, "bpm": 120.0 if i % 2 == 0 else 240.0, "_at": 5.0 + i * 0.5}
              for i in range(30)]
    row = BB.score(case, {"beats": beats, "predictions": [], "realtime_x": 1.0})
    assert row["octave_err"] == 0.5


def test_summary_reports_the_new_metrics_and_the_floors():
    rows = [{"case": "a", "F": 0.9, "CMLt": 0.8, "ibi_spread": 0.01, "ibi_flips": 1, "bpm_missing": 2,
             "realtime_x": 50.0, "cpu_x": 60.0},
            {"case": "b", "F": 0.4, "CMLt": 0.3, "ibi_spread": 0.03, "ibi_flips": 3, "bpm_missing": 1,
             "realtime_x": 40.0, "cpu_x": 30.0}]
    s = BB.summarize(rows)
    assert s["min_F"] == 0.4 and s["min_CMLt"] == 0.3 and s["ibi_spread"] == 0.02 and s["ibi_flips"] == 2.0
    assert s["bpm_missing"] == 3 and s["cpu_x_min"] == 30.0 and s["realtime_x_min"] == 40.0


# --- 3. paired comparison -----------------------------------------------------------------------------------------

def _wav(path, secs=2.0, rate=8000, seed=0, bpm=120):
    import soundfile as sf
    rng = np.random.default_rng(seed)
    y = np.zeros(int(secs * rate), dtype=np.float32)
    for t in np.arange(0, secs, 60.0 / bpm):
        i = int(t * rate)
        y[i:i + 200] += rng.uniform(0.3, 0.9) * np.hanning(200).astype(np.float32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, y, rate, subtype="PCM_16")
    return path


def test_two_loops_with_one_file_name_get_two_case_names(tmp_path):
    a = _wav(str(tmp_path / "packA" / "Drum Loop 120 BPM.wav"), seed=1)
    b = _wav(str(tmp_path / "packB" / "Drum Loop 120 BPM.wav"), seed=2)
    cases = BB.loop_suite(n=2, paths=[a, b], tile_secs=4.0, log=lambda s: None)
    names = [c.name for c in cases]
    assert len(set(names)) == 2 and all(n.startswith("Drum Loop 120 BPM.wav #") for n in names)
    assert {c.meta["sha1"][:8] for c in cases} == {n.split("#")[1] for n in names}


def test_the_same_loop_at_two_paths_is_scored_once(tmp_path):
    a = _wav(str(tmp_path / "packA" / "Drum Loop 120 BPM.wav"), seed=1)
    b = str(tmp_path / "copy" / "Drum Loop 120 BPM.wav")
    os.makedirs(os.path.dirname(b))
    with open(a, "rb") as f, open(b, "wb") as g:
        g.write(f.read())
    assert len(BB.loop_suite(n=2, paths=[a, b], tile_secs=4.0, log=lambda s: None)) == 1


def _old_paired(rows_c, rows_ref, key, n_boot=4000, seed=0):
    """Round 1's paired(), verbatim in substance: the no-cluster path must reproduce it exactly."""
    ref = {r["case"]: r for r in rows_ref}
    d = np.array([r[key] - ref[r["case"]][key] for r in rows_c
                  if isinstance(r.get(key), (int, float)) and r["case"] in ref
                  and isinstance(ref[r["case"]].get(key), (int, float))], dtype=float)
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(d)), "mean": round(float(d.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)]}


def _rows(vals):
    return [{"case": f"c{i}", "F": float(v)} for i, v in enumerate(vals)]


def test_paired_without_clusters_is_exactly_the_old_bootstrap():
    rng = np.random.default_rng(3)
    rc, rr = _rows(rng.uniform(0, 1, 60)), _rows(rng.uniform(0, 1, 60))
    assert BB.paired(rc, rr, "F") == _old_paired(rc, rr, "F")


def test_the_cluster_bootstrap_does_not_count_one_pack_as_many_witnesses():
    """10 packs of 10 loops; within a pack the difference is the pack's own (production) effect. A plain
    bootstrap sees 100 independent loops and a narrow interval; the pack bootstrap must see about 10."""
    rng = np.random.default_rng(4)
    effect = np.repeat(rng.normal(0, 0.1, 10), 10) + rng.normal(0, 0.005, 100)
    rc, rr = _rows(effect), _rows(np.zeros(100))
    pack = {f"c{i}": f"pack{i // 10}" for i in range(100)}
    plain, clustered = BB.paired(rc, rr, "F"), BB.paired(rc, rr, "F", cluster=pack)
    w = lambda r: r["ci95"][1] - r["ci95"][0]
    assert clustered["clusters"] == 10 and clustered["mean"] == plain["mean"]
    assert w(clustered) > 2.0 * w(plain)
    assert BB.paired(rc, rr, "F", cluster=lambda name: pack[name]) == clustered


def test_paired_refuses_duplicate_case_names():
    with pytest.raises(ValueError, match="duplicate"):
        BB.paired(_rows([0.1, 0.2]) + _rows([0.3]), _rows([0.1, 0.2]), "F")
    with pytest.raises(ValueError, match="duplicate"):
        BB.bench([BB.synth_case("x", 120, 1.0, RATE), BB.synth_case("x", 120, 1.0, RATE)], [], log=lambda s: None)


def test_paired_report_has_every_group_and_a_pooled_row_clustered_by_pack():
    cases = []
    for i in range(12):
        c = BB.Case(f"loop{i}", np.zeros(10, np.float32), RATE, np.array([]), 120.0, source="loop",
                    meta={"category": "kick" if i < 6 else "tops", "pack": f"p{i % 3}"})
        cases.append(c)
    rows = lambda off: [{"case": c.name, "F": 0.5 + off, "CMLt": 0.5, "bpm_spread": 0.0, "ibi_spread": 0.0}
                        for c in cases]
    rep = {"trackers": {"a": {"cases": rows(0.0)}, "w": {"cases": rows(0.1)}}}
    out = BB.paired_report(cases, rep, "a", log=lambda s: None)["w"]
    assert set(out) == {"kick", "tops", "pooled"}
    assert out["pooled"]["F"]["n"] == 12 and out["pooled"]["F"]["clusters"] == 3
    assert out["pooled"]["F"]["mean"] == pytest.approx(0.1)


def test_vs_must_be_a_scored_tracker(monkeypatch, capsys):
    monkeypatch.setattr(BB, "bench", lambda *a, **k: pytest.fail("no work may start"))
    assert CLI.main(["beatbench", "--trackers", "a", "--vs", "w"]) == 2
    assert "--vs w" in capsys.readouterr().err


def test_exclude_seeds_needs_per_cat(monkeypatch, capsys):
    monkeypatch.setattr(BB, "bench", lambda *a, **k: pytest.fail("no work may start"))
    assert CLI.main(["beatbench", "--suite", "loops", "--trackers", "a", "--exclude-seeds", "7,11"]) == 2
    assert "--per-cat" in capsys.readouterr().err


@pytest.mark.parametrize("argv,expect", [([], 30), (["--exclude-per-cat", "12"], 12)])
def test_exclude_per_cat_sets_the_size_of_the_excluded_draws(monkeypatch, tmp_path, argv, expect):
    seen = {}
    monkeypatch.setattr(BB, "find_bpm_loops", lambda *a, **k: [])
    monkeypatch.setattr(BB, "held_out_exclusion", lambda seeds, per_cat, pool=None: seen.update(
        seeds=list(seeds), per_cat=per_cat) or set())
    monkeypatch.setattr(BB, "save_report", lambda rep, path=None: str(tmp_path / "r.json"))
    BB.register("stub", _stub_factory)
    assert CLI.main(["beatbench", "--suite", "loops", "--trackers", "stub", "--per-cat", "5", "--seed", "31",
                     "--exclude-seeds", "7,11"] + argv) == 0
    assert seen == {"seeds": [7, 11], "per_cat": expect}


def _stub_factory(rate, hop, seed_bpm=None):
    class T:
        def feed(self, block):
            return []

        def predict(self, now):
            return []
    return T()


# --- 4. content-based held-out sets ------------------------------------------------------------------------------

def test_the_pool_is_deduplicated_by_content(tmp_path):
    a = _wav(str(tmp_path / "x" / "a Drum Loop 120 BPM.wav"), seed=1)
    b = str(tmp_path / "y" / "b Drum Loop 120 BPM.wav")
    os.makedirs(os.path.dirname(b))
    with open(a, "rb") as f, open(b, "wb") as g:
        g.write(f.read())
    c = _wav(str(tmp_path / "z" / "c Drum Loop 120 BPM.wav"), seed=2)          # same size, other content
    d = _wav(str(tmp_path / "z" / "d Drum Loop 120 BPM.wav"), secs=3.0, seed=3)  # a size of its own
    kept, counts = BB.dedupe_by_content([d, c, b, a, str(tmp_path / "missing 120 BPM.wav")])
    assert kept == sorted([a, c, d]) and counts == {"unreadable": 1, "duplicates": 1}


def test_a_held_out_draw_excludes_by_content_wherever_the_copy_lives(tmp_path):
    tuned = [_wav(str(tmp_path / "packs" / f"Drum Loop {i} 120 BPM.wav"), seed=i) for i in range(6)]
    fresh = [_wav(str(tmp_path / "packs" / f"Drum Loop {i} 120 BPM.wav"), seed=i) for i in range(6, 12)]
    copies = []
    for p in tuned:                                       # the same loops copied to another folder (the Desktop)
        q = str(tmp_path / "Desktop" / os.path.basename(p))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        with open(p, "rb") as f, open(q, "wb") as g:
            g.write(f.read())
        copies.append(q)
    pool = tuned + fresh + copies
    for seed in range(5):
        picked = BB.stratified_loops(12, rng_seed=seed, exclude=set(tuned), pool=pool)
        assert sorted(picked) == sorted(fresh), "a copy of a tuned-on loop leaked into the held-out draw"


def test_the_round1_draw_is_reproduced_exactly_for_exclusion():
    pool = [f"C:\\p\\{k} Drum Loop {i} 1{i % 9}0 BPM.wav" if i % 3 else f"C:\\p\\hat loop {i} 120 BPM.wav"
            for i, k in enumerate(range(40))]

    def round1(per_cat, rng_seed, exclude=None):
        pl = [p for p in pool if not exclude or p not in exclude]
        rng = np.random.default_rng(rng_seed)
        rng.shuffle(pl)
        quota = {"kick": per_cat, "tops": per_cat, "melodic": per_cat}
        out = []
        for p in pl:
            c = BB.loop_category(p)
            if quota[c] > 0:
                out.append(p)
                quota[c] -= 1
            if not any(quota.values()):
                break
        return out
    assert BB.stratified_loops(5, rng_seed=7, pool=pool, dedupe=False) == round1(5, 7)


def test_a_manifest_scores_exactly_its_files_and_refuses_a_changed_one(tmp_path):
    paths = [_wav(str(tmp_path / "packs" / f"Drum Loop {i} 120 BPM.wav"), seed=i) for i in range(3)]
    cases = BB.loop_suite(n=3, paths=paths, tile_secs=4.0, log=lambda s: None)
    m = str(tmp_path / "m.json")
    sha = BB.write_manifest(m, cases, "loops", per_cat=1, seed=31, exclude_seeds="7,11")
    doc, sha2 = BB.read_manifest(m)
    assert sha2 == sha and doc["seed"] == 31 and doc["exclude_seeds"] == "7,11" and doc["per_cat"] == 1
    assert {c["path"] for c in doc["cases"]} == set(paths)
    assert all(set(c) == {"path", "size", "sha1", "category"} for c in doc["cases"])
    again = BB.manifest_loops(doc, tile_secs=4.0, log=lambda s: None)
    assert sorted(c.name for c in again) == sorted(c.name for c in cases)
    _wav(paths[1], seed=99)                                   # the file changes under the manifest
    with pytest.raises(BB.ManifestMismatch, match="changed"):
        BB.manifest_loops(doc, tile_secs=4.0, log=lambda s: None)
    os.remove(paths[1])
    with pytest.raises(BB.ManifestMismatch):
        BB.manifest_loops(doc, tile_secs=4.0, log=lambda s: None)


def test_the_receipt_records_args_the_manifest_sha1_and_each_case_file(monkeypatch, tmp_path):
    paths = [_wav(str(tmp_path / "packs" / f"Drum Loop {i} 120 BPM.wav"), seed=i) for i in range(2)]
    m = str(tmp_path / "m.json")
    sha = BB.write_manifest(m, BB.loop_suite(n=2, paths=paths, tile_secs=4.0, log=lambda s: None), "loops")
    got = {}
    monkeypatch.setattr(BB, "save_report", lambda rep, path=None: got.update(rep) or str(tmp_path / "r.json"))
    BB.register("stub", _stub_factory)
    assert CLI.main(["beatbench", "--suite", "loops", "--manifest", m, "--trackers", "stub", "--seeded"]) == 0
    assert got["manifest"] == {"path": os.path.abspath(m), "sha1": sha}
    assert got["args"]["manifest"] == m and got["args"]["seeded"] is True and got["args"]["trackers"] == "stub"
    files = {r["path"]: r["sha1"] for r in got["case_index"] if r["source"] == "loop"}
    assert files == {p: BB.file_sha1(p) for p in paths}
    assert len(got["case_index"]) == 4                         # two loops, each also seeded


# --- 5. speed that matches live use -------------------------------------------------------------------------------

def test_cpu_x_counts_feed_and_predict_on_the_cpu_clock(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(BB, "_cpu_clock", lambda: clock["t"])

    def factory(rate, hop, seed_bpm=None):
        class T:
            def feed(self, block):
                clock["t"] += 0.0005
                return []

            def predict(self, now):
                clock["t"] += 0.002                     # the live loop pays for predict() on every block
                return []
        return T()
    case = BB.synth_case("s", 120, secs=4.0, rate=RATE)
    res = BB.run_tracker(factory, case, HOP)
    n = len(case.audio) // HOP
    assert res["proc_s"] == pytest.approx(n * 0.0025)
    assert res["cpu_x"] == pytest.approx(4.0 / (n * 0.0025))
    assert BB.score(case, res)["cpu_x"] == pytest.approx(round(4.0 / (n * 0.0025), 1))


# --- 6. held-out bright-bass variants -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def variants():
    return BB.bright_variants_suite(123, n=10, rate=RATE, secs=12.0)


def test_variants_are_a_pure_function_of_the_seed(variants):
    again = BB.bright_variants_suite(123, n=10, rate=RATE, secs=12.0)
    assert all(np.array_equal(a.audio, b.audio) and np.array_equal(a.beats, b.beats) for a, b in zip(variants, again))
    other = BB.bright_variants_suite(124, n=10, rate=RATE, secs=12.0)
    assert [c.meta["bpm"] for c in other] != [c.meta["bpm"] for c in variants]


def test_variants_cover_every_timbre_pattern_and_the_registered_ranges(variants):
    assert {c.meta["timbre"] for c in variants} == set(BB.BASS_TIMBRES)
    assert {c.meta["pattern"] for c in variants} == set(BB.BASS_PATTERNS)
    for c in variants:
        assert 125 <= c.bpm <= 175 and 35 <= c.meta["root_hz"] <= 90 and 1 <= c.meta["start16"] <= 15
        assert c.audio.dtype == np.float32 and len(c.audio) == 12 * RATE and np.max(np.abs(c.audio)) <= 0.8 + 1e-6
    assert {c.meta["glide"] for c in BB.bright_variants_suite(5, n=10, rate=RATE, secs=2.0)} == {True, False}


def test_variant_ground_truth_is_exact_and_never_starts_on_beat_one(variants):
    for c in variants:
        period = 60.0 / c.bpm
        assert np.allclose(np.diff(c.beats), period)
        first = ((4 - c.meta["start16"] % 4) % 4) * period / 4
        assert c.beats[0] == pytest.approx(first, abs=1.0 / RATE)
        # the audio's first sample sits at 16th `start16` of a bar, so beat one is never at t = 0
        assert c.meta["start16"] % 16 != 0


def test_bass_patterns_land_where_they_claim():
    rng = np.random.default_rng(0)
    for _ in range(50):
        assert not set(BB.bass_positions("offbeat", rng)) & {0, 4, 8, 12}
        assert 0 in BB.bass_positions("onbeat", rng)
        assert BB.bass_positions("sidechain", rng)[0] == 0


@pytest.mark.parametrize("timbre", BB.BASS_TIMBRES)
def test_every_bass_note_releases_to_silence_without_a_click(timbre):
    y = BB.bass_note(timbre, 55.0, 0.11, RATE, glide_from=82.0, decay_s=None)
    nr = int(round(BB.BASS_RELEASE_S * RATE))
    peak = float(np.max(np.abs(y)))
    assert y[-1] == 0.0 and y[0] == 0.0
    assert abs(float(y[-2])) <= 0.02 * peak, "the step into silence at the note's end must be tiny (no cut)"
    env = np.abs(y[-nr:]) / (peak + 1e-9)
    assert np.all(env <= np.linspace(1.0, 0.0, nr) + 1e-6), "the last 5 ms must fade under a linear ramp"


def test_variant_truth_agrees_with_its_own_drums():
    """End to end: the same parameters with the bass and noise off leave only the drums; an independent grid fit
    must find the case's tempo and put its phase within 20 ms of the case's ground truth."""
    c = BB.bright_variants_suite(77, n=1, rate=RATE, secs=20.0)[0]
    p = {**{k: c.meta[k] for k in ("bpm", "timbre", "pattern", "root_hz", "glide", "glide_s", "start16", "drums",
                                   "duck_depth", "duck_tau_beats")}, "bass_gain": 0.0, "noise": 0.0}
    dry = BB.bright_variant_case("dry", p, RATE, 20.0, rng_seed=(77, 0))
    assert np.array_equal(dry.beats, c.beats)
    g = BB.fit_grid(dry.audio, RATE)
    period = 60.0 / c.bpm
    hit = [k for k in g["candidates"] if abs(k["bpm"] / c.bpm - 1) < 0.005]
    assert hit, f"{c.bpm} not among {[k['bpm'] for k in g['candidates']]}"
    d = ((hit[0]["first_beat"] - c.beats[0] % period) / period + 0.5) % 1 - 0.5
    assert abs(d * period) < 0.020


def test_cli_bright_variants_needs_a_seed(monkeypatch, capsys):
    monkeypatch.setattr(BB, "bench", lambda *a, **k: pytest.fail("no work may start"))
    assert CLI.main(["beatbench", "--suite", "bright_variants", "--trackers", "a"]) == 2
    assert "--variant-seed" in capsys.readouterr().err


# --- 7. offline reference grids that admit doubt --------------------------------------------------------------------

def test_the_frame_time_convention_is_calibrated_on_clicks():
    """Clicks at known times must come out of the onset envelope at those times (within half a 5.8 ms frame)."""
    rate = 44100
    buf = np.zeros(6 * rate, dtype=np.float32)
    truth = np.round((0.6 + np.arange(10) * 0.45 + 0.0013 * np.arange(10)) * rate) / rate
    for t in truth:
        BB._place(buf, BB._click(rate), float(t), rate)
    t, env = BB.onset_envelope(buf, rate)
    for x in truth:
        sel = np.where(np.abs(t - x) < 0.05)[0]
        assert abs(t[sel[np.argmax(env[sel])]] - x) <= 0.0035
    assert BB.frame_time_offset(rate) != pytest.approx(BB.FIT_N_FFT / 2 / rate, abs=0.003), \
        "the window centre is not where the flux peaks"


@pytest.mark.parametrize("bpm", [120, 128, 140, 174])
def test_fit_grid_lists_the_true_tempo_and_puts_the_phase_within_20_ms(bpm):
    c = BB.synth_case(f"drums_{bpm}", bpm, 30.0, 44100)
    g = BB.fit_grid(c.audio, c.rate)
    rels = {r for k in g["candidates"] for r in k["rel"]}
    assert {"best", "x1/2", "x2", "x2/3", "x3/2", "x4/5"} <= rels
    hit = [k for k in g["candidates"] if abs(k["bpm"] / bpm - 1) < 0.002]
    assert hit, f"{bpm} not among {[k['bpm'] for k in g['candidates']]}"
    period = 60.0 / bpm
    d = ((hit[0]["first_beat"] - c.beats[0] % period) / period + 0.5) % 1 - 0.5
    assert abs(d * period) < 0.020
    if abs(g["bpm"] / bpm - 1) < 0.002:
        d = ((g["first_beat"] - c.beats[0] % period) / period + 0.5) % 1 - 0.5
        assert abs(d * period) < 0.020


def _recording(tmp_path, name="20261023-120000 Test Song.flac", bpm=128, secs=20.0, gap=False, timing=True,
               style="drums"):
    import soundfile as sf
    c = BB.synth_case("rec", bpm, secs, RATE, style=style)
    d = tmp_path / "recordings"
    d.mkdir(exist_ok=True)
    p = str(d / name)
    sf.write(p, c.audio, RATE, format="FLAC", subtype="PCM_16")
    if timing:
        n = len(c.audio)
        BS.write_timing(p, BS.capture_timing(100.0 + HOP / RATE, HOP, 100.0 + n / RATE + (0.3 if gap else 0.0),
                                             n, RATE))
    return p, c


def test_annotate_bpm_forces_exactly_that_tempo_and_records_the_doubt(tmp_path, capsys):
    p, _ = _recording(tmp_path)
    assert CLI.main(["annotate", p, "--bpm", "128.013"]) == 0
    side = json.load(open(p + ".beats.json", encoding="utf-8"))
    assert side["bpm"] == 128.013 and side["bpm_forced"] == 128.013 and side["confirmed"] is False
    assert side["candidates"] and side["clicks"]["grid"] == {"bpm": 128.013, "first_beat": side["first_beat"]}
    out = capsys.readouterr().out
    assert f'py -m arsenal.keylab confirm "{p}"' in out


def test_confirm_shows_the_grid_and_refuses_one_that_changed_after_the_listen(tmp_path, capsys):
    p, _ = _recording(tmp_path)
    assert CLI.main(["annotate", p]) == 0
    side_path = p + ".beats.json"
    good = json.load(open(side_path, encoding="utf-8"))
    edited = {**good, "bpm": good["bpm"] * 2}
    json.dump(edited, open(side_path, "w", encoding="utf-8"))
    capsys.readouterr()
    assert CLI.main(["confirm", p]) == 1
    assert "changed after the CLICKS file was rendered" in capsys.readouterr().err
    json.dump(good, open(side_path, "w", encoding="utf-8"))
    with open(good["clicks"]["path"], "ab") as f:            # a different render now sits under that name
        f.write(b"\0")
    assert CLI.main(["confirm", p]) == 1
    assert "not the one rendered" in capsys.readouterr().err
    assert CLI.main(["annotate", p]) == 0
    capsys.readouterr()
    assert CLI.main(["confirm", p]) == 0
    out = capsys.readouterr().out
    assert "BPM, first beat" in out and json.load(open(side_path, encoding="utf-8"))["confirmed"] is True


def test_confirm_without_a_grid_says_what_to_run(tmp_path, capsys):
    p, _ = _recording(tmp_path)
    assert CLI.main(["confirm", p]) == 1
    assert "py -m arsenal.keylab annotate" in capsys.readouterr().err


# --- 8. recordings that admit gaps; UTF-8 safe output ----------------------------------------------------------------

def test_capture_timing_flags_a_gap_but_not_a_clean_capture():
    ok = BS.capture_timing(10.0 + 512 / 44100, 512, 10.0 + 90.0, int(90.0 * 44100), 44100)
    assert ok["gap"] is False and abs(ok["wall_secs"] - ok["sample_secs"]) < 0.001
    lost = BS.capture_timing(10.0 + 512 / 44100, 512, 10.0 + 90.5, int(90.0 * 44100), 44100)
    assert lost["gap"] is True and lost["gap_ms"] == pytest.approx(500.0, abs=1.0)
    assert set(ok) >= {"wall_start", "wall_end", "wall_secs", "samples", "sample_secs", "gap"}


class _FakeClock:
    def __init__(self):
        self.t = 50.0

    def __call__(self):
        return self.t


def _fake_pa(clock, rate=8000, ch=2, stall_at=None):
    class Stream:
        def __init__(self):
            self.n = 0

        def read(self, n, exception_on_overflow=False):
            self.n += 1
            clock.t += n / rate
            if stall_at is not None and self.n == stall_at:
                clock.t += 0.3                              # the loopback handed over nothing for 300 ms
            return np.zeros(n * ch, dtype=np.float32).tobytes()

        def stop_stream(self):
            pass

        def close(self):
            pass

    class Inst:
        def get_default_wasapi_loopback(self):
            return {"defaultSampleRate": rate, "maxInputChannels": ch, "index": 0, "name": "fake loopback"}

        def open(self, **kw):
            return Stream()

        def terminate(self):
            pass
    return types.SimpleNamespace(PyAudio=Inst, paFloat32=1)


@pytest.mark.parametrize("stall_at,gap", [(None, False), (20, True)])
def test_record_writes_wall_and_sample_time_next_to_the_audio(monkeypatch, tmp_path, stall_at, gap):
    clock = _FakeClock()
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", _fake_pa(clock, stall_at=stall_at))
    monkeypatch.setattr(BS, "_clock", clock)
    monkeypatch.setattr(BS, "now_playing", lambda: None)
    p = BS.record(2.0, out_dir=str(tmp_path), name="t")
    timing = BS.read_timing(p)
    assert timing["gap"] is gap and timing["samples"] >= 2 * 8000 and timing["rate"] == 8000
    assert timing["sample_secs"] == pytest.approx(timing["samples"] / 8000, abs=1e-4)
    assert (timing["wall_secs"] - timing["sample_secs"]) == pytest.approx(0.3 if gap else 0.0, abs=0.002)


def test_a_saved_session_writes_its_timing_too(tmp_path):
    blocks = [np.zeros(HOP, np.float32) for _ in range(40)]
    timing = BS.capture_timing(1.0, HOP, 1.0 + 39 * HOP / RATE + 0.25, 40 * HOP, RATE)
    p = BS._save_session(blocks, RATE, [], None, {"artist": "A", "title": "B"}, timing=timing, root=str(tmp_path))
    assert BS.read_timing(p)["gap"] is True
    assert json.load(open(p + ".hand.json", encoding="utf-8"))["timing"]["gap"] is True


def test_annotate_refuses_a_recording_with_a_capture_gap(tmp_path, capsys):
    p, _ = _recording(tmp_path, gap=True)
    assert CLI.main(["annotate", p]) == 1
    assert "refused" in capsys.readouterr().err and not os.path.exists(p + ".beats.json")


def test_annotate_needs_a_timing_record_or_an_explicit_override(tmp_path, capsys):
    p, _ = _recording(tmp_path, timing=False)
    assert CLI.main(["annotate", p]) == 1
    assert "--unverified-timing" in capsys.readouterr().err
    assert CLI.main(["annotate", p, "--unverified-timing"]) == 0
    assert json.load(open(p + ".beats.json", encoding="utf-8"))["timing_verified"] is False


def test_a_title_cp1252_cannot_encode_does_not_crash_the_cli(monkeypatch):
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", out)
    title = "Ry\u014dji Ikeda \u2013 \u6771\u4eac \u266b"
    monkeypatch.setattr(BS, "record", lambda secs, name=None: print(f"recording 1 s of '{title}'"))
    assert CLI.main(["record", "--secs", "1"]) == 0
    out.flush()
    assert title.encode("utf-8") in raw.getvalue()


# --- 9. a real-song set that cannot leak; tapped answer keys -------------------------------------------------------

def _confirmed_grid(p, bpm=128.0):
    json.dump({"bpm": bpm, "first_beat": 0.5, "confirmed": True}, open(p + ".beats.json", "w", encoding="utf-8"))


def test_recording_suite_since_keeps_only_later_stamps_and_names_what_it_scores(tmp_path):
    early, _ = _recording(tmp_path, "20261022-234925 Early.flac", secs=6.0)
    late, _ = _recording(tmp_path, "20261023-130000 Late.flac", secs=6.0)
    nostamp, _ = _recording(tmp_path, "Some Song.flac", secs=6.0)
    for p in (early, late, nostamp):
        _confirmed_grid(p)
    log = []
    cases = BB.recording_suite(since="20261023-000000", log=log.append)
    assert [c.name for c in cases] == [os.path.basename(late)]
    text = "\n".join(log)
    assert "scoring 20261023-130000 Late.flac" in text and "Early.flac" in text and "Some Song.flac" in text
    with pytest.raises(ValueError):
        BB.recording_suite(since="2026-10-23", log=log.append)


def test_recording_suite_never_scores_a_capture_with_a_gap(tmp_path):
    p, _ = _recording(tmp_path, gap=True, secs=6.0)
    _confirmed_grid(p)
    log = []
    assert BB.recording_suite(log=log.append) == [] and "gap" in "\n".join(log)


def test_recording_suite_manifest_scores_exactly_its_files(tmp_path):
    a, _ = _recording(tmp_path, "20261023-130000 A.flac", secs=6.0)
    b, _ = _recording(tmp_path, "20261023-140000 B.flac", secs=6.0)
    for p in (a, b):
        _confirmed_grid(p)
    cases = BB.recording_suite(log=lambda s: None)
    m = str(tmp_path / "real.json")
    BB.write_manifest(m, cases[:1], "real")
    doc, _ = BB.read_manifest(m)
    assert [c.name for c in BB.recording_suite(manifest=doc, log=lambda s: None)] == [os.path.basename(a)]
    import soundfile as sf
    sf.write(a, np.zeros(RATE, np.float32), RATE, format="FLAC")
    with pytest.raises(BB.ManifestMismatch):
        BB.recording_suite(manifest=doc, log=lambda s: None)


def test_tap_stretches_split_on_long_pauses_and_drop_short_runs():
    a = list(5.0 + np.arange(12) * 0.5)
    b = list(a[-1] + 3.0 + np.arange(9) * 0.47)               # a pause of 6 beats, then a new stretch
    c = list(b[-1] + 4.0 + np.arange(5) * 0.5)                # only 5 taps: dropped
    stretches, dropped = BB.tap_stretches(a + b + c)
    assert [len(s) for s in stretches] == [12, 9] and dropped == 5


def _tapped(tmp_path, bpm=128.0, late_ms=15.0, jitter_ms=5.0, seed=1):
    p, c = _recording(tmp_path, bpm=bpm, secs=20.0)
    rng = np.random.default_rng(seed)
    beats = c.beats[(c.beats > 2.0) & (c.beats < 18.0)]
    taps = beats + late_ms / 1000 + rng.uniform(-jitter_ms, jitter_ms, len(beats)) / 1000
    json.dump({"taps": [round(float(x), 4) for x in taps]}, open(p + ".hand.json", "w", encoding="utf-8"))
    return p, c


def test_tap_key_fits_the_line_and_reports_jitter_and_the_offset_to_the_kicks(tmp_path):
    p, c = _tapped(tmp_path)
    doc = BB.tap_key(p)
    assert len(doc["sections"]) == 1 and doc["confirmed"] is False
    s = doc["sections"][0]
    assert s["bpm"] == pytest.approx(128.0, rel=0.002)
    assert 1.0 < s["jitter_ms"] < 5.0                           # uniform +-5 ms scatter: about 2.9 ms RMS
    assert s["kick_offset_ms"] == pytest.approx(15.0, abs=8.0) and s["kick_matched"] > 0.8
    assert doc["spans"] == [[s["start"], s["end"]]]
    on_disk = json.load(open(p + ".tapkey.json", encoding="utf-8"))
    assert on_disk["sections"] == doc["sections"] and os.path.exists(on_disk["clicks"]["path"])


def test_a_confirmed_tap_key_is_the_ground_truth_recording_suite_uses(tmp_path, capsys):
    p, c = _tapped(tmp_path)
    _confirmed_grid(p, bpm=64.0)                               # a (wrong) confirmed grid is also present
    assert CLI.main(["tapkey", p]) == 0
    assert BB.recording_suite(log=lambda s: None)[0].meta["truth"] == "grid", "an unconfirmed key is not truth"
    assert CLI.main(["confirm", p, "--tapkey"]) == 0
    case = BB.recording_suite(log=lambda s: None)[0]
    assert case.meta["truth"] == "tapkey" and case.meta["spans"] and case.bpm == pytest.approx(128.0, rel=0.002)
    inside = case.beats[(case.beats > 3.0) & (case.beats < 17.0)]
    assert np.max(np.abs(inside[:, None] - c.beats[None, :]).min(axis=1)) < 0.03


def test_tap_key_refuses_a_session_with_a_gap(tmp_path):
    p, _ = _tapped(tmp_path)
    BS.write_timing(p, BS.capture_timing(1.0, HOP, 30.0, 20 * RATE, RATE))
    with pytest.raises(ValueError, match="gap"):
        BB.tap_key(p)


# --- 10. isolation ------------------------------------------------------------------------------------------------

def test_beatbench_imports_only_the_named_trackers(monkeypatch):
    for mod in [m for m in sys.modules if m.startswith("arsenal.keylab.beat_")]:
        monkeypatch.delitem(sys.modules, mod)
    assert CLI.load_trackers(["a"], BB) == []
    loaded = {m for m in sys.modules if m.startswith("arsenal.keylab.beat_")}
    assert loaded == {"arsenal.keylab.beat_a"}, f"a run of tracker a executed {sorted(loaded)}"
    assert "a" in BB.TRACKERS and set(CLI.tracker_files()) >= {"a", "b", "g", "h", "w"}
    assert CLI.load_trackers(["nope"], BB) == ["nope"]



def test_a_tuned_on_file_name_never_enters_a_held_out_draw_and_temp_copies_are_not_packs(tmp_path, monkeypatch):
    """The live index drifts (the bench's own tests leave 'Drum Loop N 120 BPM.wav' files behind), so round 1's
    tuning set is excluded by the file names its receipts actually scored, and temp/pytest copies are not packs."""
    import json as _json
    import ntpath
    rec = tmp_path / "r.json"
    _json.dump({"trackers": {"a": {"cases": [{"case": "Kick Loop 1 120 BPM.wav"},
                                             {"case": "Kick Loop 1 120 BPM.wav [seeded]"},
                                             {"case": "Hat Loop 2 128 BPM.wav #0123abcd"}]}}}, open(rec, "w"))
    names = BB.receipt_case_names([str(rec)])
    assert names == {"kick loop 1 120 bpm.wav", "hat loop 2 128 bpm.wav"}
    pool = [ntpath.join("D:", "packs", "A", f"Kick Loop {i} 120 BPM.wav") for i in range(1, 6)]
    pool.append(ntpath.join("F:", "copy", "Hat Loop 2 128 BPM.wav"))
    picked = BB.stratified_loops(10, rng_seed=31, pool=pool, dedupe=False, exclude_names=names)
    assert picked and not any(ntpath.basename(p).lower() in names for p in picked)

    keep = ntpath.join("D:", "packs", "Kick Loop 9 120 BPM.wav")
    temp = ntpath.join("C:", "Users", "x", "AppData", "Local", "Temp", "pytest-of-x", "packs", "Drum Loop 1 120 BPM.wav")

    # a temp copy outside pytest's folder (a scratch render) and a recycle-bin copy are not packs either
    scratch = ntpath.join("C:", "Users", "x", "AppData", "Local", "Temp", "claude", "scratch", "Kick Loop 3 120 BPM.wav")
    binned = ntpath.join("D:\\", "$Recycle.Bin", "S-1-5-21", "Kick Loop 4 120 BPM.wav")

    class R:
        paths = [keep, temp, scratch, binned]
    import core.tools.everything as E
    monkeypatch.setattr(E, "search", lambda *a, **k: R())
    assert BB.find_bpm_loops() == [keep]
    assert not any(c in x for x in BB._NOT_A_PACK for c in ("\a", "\t"))
