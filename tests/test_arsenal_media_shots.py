"""arsenal.media.shots: the cached 360p proxy, the spike rule (scenedetect absent), frame accuracy on a lavfi montage
with known cut frames, clock-map jumps as cuts, catalog spans; then F1 on the research montage synthetic2 against
its truth file, with arsenal.storyboard's F1 recorded beside it."""
from __future__ import annotations

import importlib.util
import json
import os
import threading
from pathlib import Path

import pytest

from arsenal.media import catalog, ff, probe, shots

ORACLES = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles"
SYN2 = ORACLES / "clips" / "synthetic2.mp4"
SYN2_TRUTH = ORACLES / "clips" / "synthetic2_truth.json"
HAS_SCENEDETECT = importlib.util.find_spec("scenedetect") is not None

#: (lavfi source, frames at 60 fps): distinct pictures, so each join is a hard cut at a known frame. 165 is odd:
#: that cut falls between two 30 fps proxy frames.
SEGMENTS = [("testsrc2", 90), ("smptehdbars", 75), ("mandelbrot", 104), ("testsrc", 82), ("rgbtestsrc", 120),
            ("color=c=0x336699", 66)]


@pytest.fixture(scope="module")
def montage(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    out = tmp_path_factory.mktemp("shots") / "montage.mp4"
    args, fc = [], ""
    for i, (src, n) in enumerate(SEGMENTS):
        args += ["-f", "lavfi", "-i", f"{src}:s=640x360:r=60" if "=" in src else f"{src}=s=640x360:r=60"]
        fc += f"[{i}:v]trim=end_frame={n},setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p,setsar=1[v{i}];"
    fc += "".join(f"[v{i}]" for i in range(len(SEGMENTS))) + f"concat=n={len(SEGMENTS)}:v=1:a=0[out]"
    ff.run(args + ["-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                   "-g", "120", "-bf", "0", "-r", "60", "-y", str(out)])
    truth, acc = [], 0
    for _, n in SEGMENTS[:-1]:
        acc += n
        truth.append(acc / 60)
    return out, truth


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    return tmp_path / "state"


def test_every_cut_found_within_one_proxy_frame_and_none_invented(montage, state):
    src, truth = montage
    res = shots.shots(src, detector="spike")
    got = [c["t"] for c in res["cuts"]]
    assert len(got) == len(truth)
    for g, t in zip(got, truth):
        assert abs(g - t) <= 1 / 30 + 1e-3, (g, t)
    assert all(c["source"] == "spike" for c in res["cuts"])
    assert res["shots"][0][0] == 0.0 and res["shots"][-1][1] == pytest.approx(res["duration_s"])
    assert len(res["shots"]) == len(truth) + 1
    assert res["api"] == "arsenal.media.shots/v0" and res["blind"] and Path(res["receipt"]).is_file()
    assert res["params"]["spike"] == {"threshold": 0.3, "floor": 0.12, "ratio": 8.0, "half_window_s": 1.0,
                                      "score_width": 320}


def test_proxy_is_made_once_small_and_one_keyframe_a_second(montage, state):
    src, _ = montage
    p = Path(shots.proxy(src))
    assert p.parent == state / "proxy"
    stamp = p.stat().st_mtime_ns
    assert shots.proxy(src) == str(p) and p.stat().st_mtime_ns == stamp          # cached: not re-encoded
    sc = probe.probe(p, keyframes=True)
    assert (sc["video"]["h"], sc["video"]["fps"]) == (360, 30.0) and not sc["audio"]
    assert sc["video"]["keyint_s"] == pytest.approx(1.0)


def test_auto_falls_back_and_says_why(montage, state):
    res = shots.shots(montage[0])
    if HAS_SCENEDETECT:
        assert res["detector_ran"] == "content" and res["fallback_reason"] is None
    else:
        assert res["detector_ran"] == "spike" and "scenedetect is not installed" in res["fallback_reason"]
        with pytest.raises(ff.MediaError, match="scenedetect"):
            shots.shots(montage[0], detector="content")
    with pytest.raises(ff.MediaError, match="v1"):
        shots.shots(montage[0], detector="transnet")


def test_spike_rule_ignores_a_pan_and_keeps_the_stronger_of_two_close_spikes():
    times = [i / 30 for i in range(300)]
    scores = [0.01] * 300
    for i in range(100, 160):                     # a pan: the whole neighbourhood rises
        scores[i] = 0.2
    scores[50] = 0.13                             # a lone spike above the floor: a cut
    scores[200], scores[203] = 0.35, 0.5          # two candidates 0.1 s apart: keep the stronger
    cuts = shots.spike_cuts(times, scores, min_shot_s=0.25)
    assert [round(c["t"] * 30) for c in cuts] == [50, 203]


def test_clock_jumps_become_cuts_unless_a_pixel_cut_is_there(montage, state):
    cmap = {"schema": "studio.clockmap.v1", "passes": [
        {"id": "a_1x", "file": [0.0, 3.0], "speed": 1.0, "offset": 100.0},
        {"id": "b_025x", "file": [3.0, 6.8], "speed": 0.25, "offset": 103.0 - 0.25 * 3.0},   # speed change only
        {"id": "c_1x", "file": [6.8, 8.95], "speed": 1.0, "offset": 400.0}]}                 # a skip ahead
    assert [(c["t"], c["pass"]) for c in shots.clock_cuts(cmap)] == [(6.8, "c_1x")]
    res = shots.shots(montage[0], detector="spike", clockmap=cmap)
    (clock,) = [c for c in res["cuts"] if c["source"] == "clock"]               # no pixel cut within 0.5 s of 6.8
    assert (clock["t"], clock["score"], clock["pass"], clock["gap_s"]) == (6.8, None, "c_1x", 0.0)
    assert clock["jump_game_s"] == pytest.approx(406.8 - 103.95)
    assert [c["t"] for c in res["cuts"]] == sorted(c["t"] for c in res["cuts"])
    cmap["passes"][2]["file"][0] = 5.85                                          # on the testsrc -> rgbtestsrc cut
    res = shots.shots(montage[0], detector="spike", clockmap=cmap)
    assert not [c for c in res["cuts"] if c["source"] == "clock"]
    assert [c.get("clock") for c in res["cuts"] if c.get("clock")] == ["c_1x"]


def test_a_clock_pass_outside_the_file_makes_no_cut(montage, state):
    """A clock map whose pass starts past the end (a map of another file) must not leave an impossible cut in
    "cuts" while "shots" filters it: it is dropped and listed."""
    cmap = {"schema": "studio.clockmap.v1", "passes": [
        {"id": "a", "file": [0.0, 3.0], "speed": 1.0, "offset": 100.0},
        {"id": "far", "file": [50.0, 60.0], "speed": 1.0, "offset": 900.0}]}
    res = shots.shots(montage[0], detector="spike", clockmap=cmap)
    assert all(0.0 < c["t"] < res["duration_s"] for c in res["cuts"])
    assert [(c["t"], c["pass"]) for c in res["clock_cuts_dropped"]] == [(50.0, "far")]
    assert [s for s in res["shots"] if s[1] > res["duration_s"]] == []


def test_two_threads_asking_for_one_uncached_proxy_get_one_encode(montage, state, monkeypatch):
    calls, got, errors = [], [], []
    real = shots._encode_proxy

    def counted(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(shots, "_encode_proxy", counted)

    def ask() -> None:
        try:
            got.append(shots.proxy(montage[0], hw=None))
        except Exception as exc:
            errors.append(repr(exc))
    threads = [threading.Thread(target=ask) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert errors == [] and len(got) == 2 and got[0] == got[1] and Path(got[0]).is_file()
    assert len(calls) == 1
    assert not list((state / "proxy").glob("*.tmp*"))


def test_a_state_folder_with_an_apostrophe_still_scans(montage, tmp_path, monkeypatch):
    """The scene scores stream through ffmpeg's stdout, so no path enters the filtergraph (ff.filter_path refuses
    apostrophes, and the score log used to live under the state folder)."""
    odd = tmp_path / "st ate's [ü] 50%"
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(odd))
    res = shots.shots(montage[0], detector="spike")
    assert len(res["cuts"]) == len(montage[1]) and Path(res["proxy"]).is_relative_to(odd)


def test_times_are_file_times_and_say_where_the_container_clock_starts(tmp_path, state):
    """MPEG-TS starts its own clock late (1.4 s here): shots, like the sidecar's keyframe index, speak file times
    (seconds from the file's start, ffmpeg's -ss clock); start_s says where that clock's 0 sits on the container's.
    Until the house clock ruling the keyframe index was on the container clock and a cut needed + video_start_s."""
    ts = tmp_path / "two shots.ts"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=3", "-f", "lavfi", "-i", "smptehdbars=s=320x180:r=30:d=3",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264",
            "-preset", "ultrafast", "-g", "30", "-bf", "0", "-pix_fmt", "yuv420p", "-y", str(ts)])
    res = shots.shots(ts, detector="spike")
    (cut,) = res["cuts"]
    assert cut["t"] == pytest.approx(3.0, abs=1 / 30 + 1e-3) and res["shots"][0][0] == 0.0
    assert res["start_s"] == pytest.approx(1.4, abs=0.05)                 # the container clock starts late ...
    assert res["video_start_s"] == pytest.approx(0.0, abs=1e-3)           # ... and the picture with the file
    kf = probe.probe(ts, keyframes=True)["keyframes"]
    assert kf[0] == pytest.approx(0.0, abs=1e-3)
    assert min(abs(k - cut["t"]) for k in kf) < 1 / 30 + 1e-3              # x264's keyframe at the cut, same clock
    assert any("video_start_s" in b for b in res["blind"])


def test_a_cataloged_file_keeps_its_shots_as_spans(montage, state):
    src, truth = montage
    res = shots.shots(src, detector="spike")
    assert catalog.find() == []                                                  # not imported: nothing stored
    (r,) = catalog.ingest(src, proxy=False, shots=False, peaks=False, clock="off")
    shots.shots(src, detector="spike")
    rows = catalog.spans(r["id"], "shot")
    assert [[s["t0"], s["t1"]] for s in rows] == res["shots"]
    assert rows[1]["data"]["cut"] == "spike" and rows[1]["source"] == "spike"
    assert catalog.artifact(r["id"], "proxy") is not None
    shots.shots(src, detector="spike")
    assert len(catalog.spans(r["id"], "shot")) == len(rows)                      # a re-run replaces


def test_sheet_of_one_frame_per_shot(montage, state):
    res = shots.shots(montage[0], detector="spike")
    png = shots.sheet(res)
    if importlib.util.find_spec("arsenal.media.sheet") is None:
        assert png is None
    else:
        assert png and Path(png).is_file()


# ------------------------------------------------------------------------------------------------- research oracle
def _score(cuts, truth, tol_hard=0.25, tol_dis=0.8):
    """The research bench's matching (bench_shots2.py): greedy nearest unused cut per truth event."""
    gt = [("hard", t) for t in truth["hard_cuts_s"]] + [("dissolve", t) for t in truth["dissolves_center_s"]]
    used, hits = set(), []
    for kind, t in gt:
        tol = tol_hard if kind == "hard" else tol_dis
        near = [(abs(x - t), i) for i, x in enumerate(cuts) if i not in used and abs(x - t) <= tol]
        if near:
            used.add(min(near)[1])
            hits.append((kind, t))
    tp, fp = len(hits), len(cuts) - len(used)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / len(gt)
    same = set(truth["same_game_cuts_s"])
    return {"tp": tp, "fp": fp, "fn": len(gt) - tp, "precision": round(p, 3), "recall": round(r, 3),
            "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "dissolves": sum(k == "dissolve" for k, _ in hits), "same_game": sum(t in same for _, t in hits)}


needs_syn2 = pytest.mark.skipif(not (SYN2.is_file() and SYN2_TRUTH.is_file()), reason="synthetic2 oracle missing")


@pytest.fixture(scope="module")
def syn2(tmp_path_factory):
    """shots() on synthetic2 once (auto detector, proxy), shared by the oracle tests."""
    if not (SYN2.is_file() and SYN2_TRUTH.is_file()):
        pytest.skip("synthetic2 oracle missing")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp_path_factory.mktemp("syn2_state")))
        yield shots.shots(SYN2), json.loads(SYN2_TRUTH.read_text(encoding="utf-8"))


@needs_syn2
def test_synthetic2_f1_meets_the_spec(syn2):
    res, truth = syn2
    got = _score([c["t"] for c in res["cuts"]], truth)
    one_frame = _score([c["t"] for c in res["cuts"]], truth, tol_hard=1.01 / 30, tol_dis=1.01 / 30)
    print(f"\nsynthetic2, {res['detector_ran']} on the proxy: {got}; proxy {res['timings']['proxy_s']} s, "
          f"detect {res['timings']['detect_s']} s ({res['timings']['realtime_x']}x realtime); "
          f"+-1 frame against the truth file: F1 {one_frame['f1']}")
    assert got["f1"] >= (0.85 if res["detector_ran"] == "content" else 0.84)


@needs_syn2
def test_synthetic2_truth_drifts_from_the_frames(state):
    """Why +-1 frame cannot be scored against synthetic2_truth.json: its hard-cut times are sums of the requested
    segment lengths, and the montage kept whole frames, so the real cut frame (an unmistakable one-frame spike)
    sits up to ~6 frames after the stated time."""
    truth = json.loads(SYN2_TRUTH.read_text(encoding="utf-8"))
    times, scores = shots.scene_scores(SYN2)
    late = []
    for t in truth["hard_cuts_s"]:
        window = [(s, x) for x, s in zip(times, scores) if abs(x - t) <= 0.25]
        s, x = max(window)
        if s >= 0.3:                                  # unmistakable cuts only
            late.append((x - t) * 30)
    assert len(late) >= 15 and max(late) > 3 and min(late) >= -1.5
    print(f"\nsynthetic2 truth vs the cut frames: {len(late)} strong cuts, real cut up to {max(late):.1f} frames late")


@needs_syn2
def test_storyboard_f1_on_the_same_montage_states_its_role(syn2):
    from arsenal import storyboard
    res, truth = syn2
    m = storyboard.analyse(str(SYN2))
    starts = [s["start_s"] for s in m["segments"] if s["kind"] == "transition"]
    sb = _score(starts, truth)
    ours = _score([c["t"] for c in res["cuts"]], truth)
    print(f"\nsynthetic2: arsenal storyboard as a cut detector (transition starts) {sb}; shots spike F1 {ours['f1']}")
    assert sb["f1"] < ours["f1"]
