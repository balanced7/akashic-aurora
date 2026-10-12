"""arsenal.media.league.hud + league.clock: HUD boxes, the clock reader, runs/passes, and the clockmap end to end.

The synthetic tests always run: a 40 s replay-style video is encoded at test time with a clock drawn in OpenCV's
Hershey font (a rewind, a 0.25x stretch, a speed change back), and its templates are cut from the same font, so the
whole pipeline is checked against a known script. The oracle tests need Daniel's recordings, the hand-calibrated
clockmaps in state/arsenal/media-oracles and digit templates built on this machine (`py -m arsenal.media clockmap
--train-templates ...`) or rapidocr; each skips when its inputs are missing.
"""
from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from arsenal import timebase
from arsenal.media import __main__ as media_main
from arsenal.media import ff, frames
from arsenal.media.league import clock, hud

ORACLES = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles"
VIDEOS = Path("E:/Video Output E")
REC_1751 = VIDEOS / "2026-10-11 17-51-11.mp4"
REC_1650 = VIDEOS / "2026-10-11 16-50-20.mp4"
REC_LIVE = VIDEOS / "2026-10-10 21-35-21.mp4"
#: The TTK work's 24:02 death frame in the 0.25x pass: ttk/video/work/d2402q_steps.json, a window read from file
#: 1612.0 s at 60 fps whose frame 542 is the first without Draven's bar (ttk_video_summary.json: death_t 1442.054).
TTK_DEATH_FILE_T = 1612.0 + 542 / 60
#: The live recording's offset, read independently tonight in software decode: the clock ticks at file 300.633,
#: 600.633, 1200.633 and 1500.617 s (game 2:29, 7:29, 17:29, 22:29). The spec's -152 was the keyframe-quantised
#: bench value (first readable keyframe 154.167 s showing 0:02).
LIVE_OFFSET = -151.633

W, H, FPS = 1280, 720, 30
#: (file_t where the segment starts, replay speed, game_t there; None = continuous with the previous segment)
SCRIPT = [(0.0, 1.0, 100.4), (12.0, 1.0, 95.7), (20.0, 0.25, None), (32.0, 1.0, None)]
DURATION = 40.0


def _segments():
    segs = []
    for t0, s, g0 in SCRIPT:
        if g0 is None:
            pt0, ps, pg0 = segs[-1]
            g0 = pg0 + ps * (t0 - pt0)
        segs.append((t0, s, g0))
    return segs


SEGS = _segments()
TRUTH = [(s, g0 - s * t0) for t0, s, g0 in SEGS]          # (speed, offset) per pass


def _game_at(t: float) -> float:
    t0, s, g0 = [seg for seg in SEGS if seg[0] <= t + 1e-9][-1]
    return g0 + s * (t - t0)


def _draw_clock(img, n: int, layout: str = "replay") -> None:
    import cv2
    x, y, w, h = hud.box("clock", layout, img.shape)
    txt = f"{n // 60:02d}:{n % 60:02d}"
    (tw1, _th1), _base = cv2.getTextSize("00:00", cv2.FONT_HERSHEY_SIMPLEX, 1.0, 1)
    scale = min(0.55 * h / 18, 0.85 * w / tw1)              # fits the box at any frame size
    (tw, th), _base = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    cv2.putText(img, txt, (x + (w - tw) // 2, y + (h + th) // 2), cv2.FONT_HERSHEY_SIMPLEX, scale,
                (230, 230, 230) if img.ndim == 3 else 230, 1, cv2.LINE_AA)


def _frame(n: int, shape=(H, W), layout: str = "replay"):
    img = np.full(shape, 40, np.uint8)
    _draw_clock(img, n, layout)
    return img


def _synthetic_templates(state: Path) -> Path:
    labelled = []
    for n in range(0, 3600, 7):
        crop = hud.crop(_frame(n), "clock", "replay")
        labelled.append((np.stack([crop] * 3, axis=2), f"{n // 60:02d}:{n % 60:02d}"))
    glyphs, count = clock._templates_from(labelled)
    assert count.min() > 0
    out = state / clock.TEMPLATE_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / clock.TEMPLATE_FILE, glyphs=glyphs, count=count)
    return out / clock.TEMPLATE_FILE


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    clock._readers.clear()
    yield tmp_path / "state"
    clock._readers.clear()


@pytest.fixture
def hershey(state, monkeypatch):
    """Synthetic Hershey-font templates in the isolated state; 'auto' picks them even if rapidocr arrives."""
    _synthetic_templates(state)
    monkeypatch.setattr(clock, "rapidocr_available", lambda: False)
    clock._readers.clear()
    return state


def _encode_synthetic(out: Path) -> Path:
    try:
        if not ff.has_encoder("libx264"):
            pytest.skip("the house ffmpeg has no libx264")
    except ff.MediaError as exc:
        pytest.skip(str(exc))
    args = ["-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "ultrafast", "-g", str(2 * FPS), "-pix_fmt", "yuv420p", str(out)]
    proc = ff.popen(args, stdin=subprocess.PIPE)
    cache = {}
    for k in range(int(DURATION * FPS)):
        n = math.floor(_game_at(k / FPS) + 1e-9)
        if n not in cache:
            cache[n] = _frame(n).tobytes()
        proc.stdin.write(cache[n])
    proc.stdin.close()
    ff.finish(proc, timeout=60)
    return out


# =================================================================================================
# HUD boxes and layout detection
# =================================================================================================

def test_hud_boxes_are_fractions_and_even_pixels():
    for layout, spec in hud.boxes().items():
        for name, (fx, fy, fw, fh) in spec["boxes"].items():
            assert 0 <= fx < 1 and 0 <= fy < 1 and 0 < fw <= 1 and 0 < fh <= 1, (layout, name)
            assert fx + fw <= 1.0 + 1e-6 and fy + fh <= 1.0 + 1e-6, (layout, name)
            for shape in ((1080, 1920), (2160, 3840), (720, 1280), (1440, 2560)):
                x, y, w, h = hud.box(name, layout, shape)
                assert all(v % 2 == 0 for v in (x, y, w, h)), (layout, name, shape)
                assert x + w <= shape[1] and y + h <= shape[0]
    # the 1080p boxes every earlier script used, and 4K is exactly twice them
    assert hud.box("clock", "replay", (1080, 1920)) == (930, 84, 90, 26)
    assert hud.box("clock", "live", (1080, 1920)) == (1858, 12, 62, 26)
    assert hud.box("speed", "replay", (1080, 1920, 3)) == (678, 1054, 40, 24)
    assert hud.box("clock", "replay", (2160, 3840)) == (1860, 168, 180, 52)
    with pytest.raises(KeyError, match="known"):
        hud.box("minimap", "replay", (1080, 1920))


def test_detect_layout_on_synthetic_frames(hershey):
    replay = _frame(1442, (1080, 1920, 3), "replay")
    live = _frame(448, (1080, 1920, 3), "live")
    blank = np.full((1080, 1920, 3), 40, np.uint8)
    assert hud.detect_layout(replay) == "replay"
    assert hud.detect_layout(live) == "live"
    assert hud.detect_layout(blank) == "none"


# =================================================================================================
# the reader
# =================================================================================================

def test_template_reader_reads_synthetic_clocks_at_any_size(hershey):
    rd = clock.get_reader("templates")
    for n in (0, 59, 61, 600, 1442, 2999, 3599):
        crop = hud.crop(_frame(n, (H, W, 3)), "clock", "replay")
        assert rd.read(crop)[0] == n, n
    big = np.repeat(np.repeat(hud.crop(_frame(1442, (H, W, 3)), "clock", "replay"), 3, axis=0), 3, axis=1)
    assert rd.read(big)[0] == 1442                                 # a 3x larger crop (4K-like) normalises the same
    assert rd.read(np.full((18, 60, 3), 40, np.uint8)) == (None, 0.0)
    noisy = hud.crop(_frame(1442, (1080, 1920, 3)), "clock", "replay").copy()
    cols = np.where(noisy.min(axis=2).max(axis=0) > 135)[0]
    x0 = cols.max() + 2                                             # just right of the text, off the box edge
    assert x0 + 3 < noisy.shape[1] - 1
    noisy[3:-3, x0:x0 + 3] = (230, 80, 120)                         # a pink effect drifting into the box
    assert rd.read(noisy)[0] == 1442


def test_parse_rejects_impossible_seconds():
    assert clock._parse("24:02") == 1442
    assert clock._parse("09:09 anisit") == 549
    assert clock._parse("10:71") is None
    assert clock._parse("") is None


def test_no_reader_names_the_fix(state, monkeypatch):
    monkeypatch.setattr(clock, "template_paths", lambda: [state / "nowhere" / "digits.npz"])
    monkeypatch.setattr(clock, "rapidocr_available", lambda: False)
    with pytest.raises(ff.MediaError, match="train-templates"):
        clock.get_reader("auto")
    with pytest.raises(ff.MediaError, match="rapidocr is not installed"):
        clock.get_reader("rapidocr")


# =================================================================================================
# runs and passes, on reads with a known answer (no video)
# =================================================================================================

def _reads(script, t_end: float, fps: float, every: float):
    """Keyframe-like samples every `every` s, plus dense reads (every frame) over [t, t+2) at each sample."""
    def g(t):
        t0, s, o = [x for x in script if x[0] <= t + 1e-9][-1]
        return s * t + o
    out = []
    k = 0
    while k / fps < t_end:
        t = k / fps
        if (t % every) < 2.0:
            out.append((round(t, 6), math.floor(g(t) + 1e-9)))
        k += 1
    return out


def test_chain_recovers_passes_and_drops_a_misread():
    fps = 60.0
    script = [(0.0, 1.0, 6.84), (29.0, 1.0, -19.66), (50.0, 0.25, 17.84)]     # (start, speed, offset)
    # the speed change at 50 is continuous (both lines show game 30.34 there) and the 0.25x ticks fall at
    # t = 52.64 + 4k, inside the dense halves the helper reads
    assert abs((1.0 * 50 - 19.66) - (0.25 * 50 + 17.84)) < 1e-9
    reads = _reads(script, 70.0, fps, 4.0)
    i = next(k for k, (t, _n) in enumerate(reads) if t >= 12.0)
    t, n = reads[i]
    reads[i] = (t, n + 5)                                            # a 3 read as 8: one bad frame
    runs, dropped = clock._chain(reads, fps)
    assert dropped == [(t, n + 5)]
    passes, events = clock._passes(runs, fps)
    assert [p["speed"] for p in passes] == [1.0, 1.0, 0.25]
    for p, (_t0, s, off) in zip(passes, script):
        assert abs(p["offset"] - off) <= s / fps + 1e-6, (p, off)
    assert [e["kind"] for e in events] == ["rewind", "speed_change"]
    assert abs(events[0]["file_t"] - 29.0) <= 1 / fps + 1e-6
    assert abs(events[1]["file_t"] - 50.0) <= 0.05


def test_run_fit_without_ticks_states_its_width():
    fps = 60.0
    run = clock._Run(1.0, fps)
    for t, n in ((10.0, 16), (14.1667, 21)):          # only 1x fits both; offset in [6.833, 7.0)
        assert run.add(t, n)
    f = clock._fit(run, fps)
    assert f["fit"] == "reads" and f["speed"] == 1.0 and f["speeds_possible"] == [1.0]
    assert 6.83 <= f["offset"] <= 7.0 and f["tol_s"] < 0.1


def _dense(script, t_end: float, fps: float):
    """Every frame read, for a script of (start, speed, offset) segments."""
    def g(t):
        return [s * t + o for t0, s, o in script if t0 <= t + 1e-9][-1]
    return [(round(k / fps, 6), math.floor(g(k / fps) + 1e-9)) for k in range(int(t_end * fps))]


def test_a_slow_tap_without_its_own_tick_states_its_width():
    """A 2 s 0.25x tap shows no tick of its own; its loose line used to take the next 1x pass's first tick and
    report offset 109.475 +-0.008 (truth 109.4). That tick goes to the pass whose line explains it."""
    fps = 30.0
    script = [(0.0, 1.0, 100.4), (12.0, 0.25, 109.4), (14.0, 1.0, 98.9)]
    runs, _dropped = clock._chain(_dense(script, 24.0, fps), fps)
    passes, events = clock._passes(runs, fps)
    assert [p["speed"] for p in passes] == [1.0, 0.25, 1.0]
    tap = passes[1]
    assert tap["fit"] == "reads" and tap["n_ticks"] == 0
    assert abs(tap["offset"] - 109.4) <= tap["tol_s"], tap                  # the truth is inside what it claims
    assert abs(passes[0]["offset"] - 100.4) <= 1 / fps and abs(passes[2]["offset"] - 98.9) <= 1 / fps
    assert passes[2]["fit"] == "ticks" and passes[2]["n_ticks"] >= 8          # its ticks from 15.1 s on
    assert [e["kind"] for e in events] == ["speed_change", "speed_change"]
    for e, t in zip(events, (12.0, 14.0)):
        assert abs(e["file_t"] - t) <= e["tol_s"], e
    g = clock.to_game({"passes": passes}, 13.0)[0]
    assert abs(g - (0.25 * 13.0 + 109.4)) <= tap["tol_s"]


def test_settle_leaves_a_tick_the_next_line_cannot_explain():
    """A 1x pass whose only tick is 0.5 s before a rewind keeps it: the rewound line never shows that transition."""
    fps = 60.0
    script = [(0.0, 1.0, 50.5), (1.0, 1.0, 20.0)]                        # tick at 0.5 s, rewind at 1.0 s
    runs, _dropped = clock._chain(_dense(script, 3.0, fps), fps)
    assert len(runs) == 2 and runs[0].ticks() == [(0.5, 51)]
    f = clock._fit(runs[0], fps)
    assert f["fit"] == "ticks" and abs(f["offset"] - 50.5) <= 1 / fps


def test_settle_never_feeds_a_seek_transient():
    """17-51-11 at file 452-453: a 1x pass, its clock frozen for a few frames, then a rewind. The frozen frames are a
    loose run that explains anything continuous; they must not take the 1x pass's last tick (that made a fake 0.25x
    pass before only tick-less runs could give and only pinned runs could take)."""
    fps = 60.0
    script = [(0.0, 1.0, 6.85), (10.15, 0.0, 16.99), (10.25, 1.0, -5.0)]
    runs, _dropped = clock._chain(_dense(script, 14.0, fps), fps)
    assert len(runs) == 3
    first, frozen, _rewound = runs
    assert first.t1 >= 10.15 and clock._fit(first, fps)["fit"] == "ticks"
    assert frozen.ticks() == [] and frozen.t1 - frozen.t0 < 0.25         # a transient clockmap() sets aside


# =================================================================================================
# queries
# =================================================================================================

def _toy_map():
    return {"schema": clock.SCHEMA, "file": "x.mp4", "passes": [
        {"id": "a", "file": [0.0, 100.0], "speed": 1.0, "offset": 50.0, "tol_s": 0.02},
        {"id": "b", "file": [100.0, 140.0], "speed": 0.25, "offset": 105.0, "tol_s": 0.004},
        {"id": "c", "file": [140.0, 150.0], "speed": 0.0, "offset": 140.3, "tol_s": 0.5},
        {"id": "d", "file": [150.0, 200.0], "speed": 1.0, "offset": -10.0, "tol_s": 0.02}]}


def test_to_game_to_file_and_as_clockmaps():
    cm = _toy_map()
    assert clock.to_game(cm, 10.0) == (60.0, "a")
    assert clock.to_game(cm, 120.0) == (135.0, "b")
    assert clock.to_game(cm, 250.0) is None
    hits = clock.to_file(cm, 140.0)
    assert [(round(f, 6), pid) for f, pid, _s in hits] == [(90.0, "a"), (140.0, "b"), (140.0, "c"), (150.0, "d")]
    assert clock.to_file(cm, 130.0) == [(80.0, "a", 1.0), (100.0, "b", 0.25)]
    maps = clock.as_clockmaps(cm)
    assert [m.slope for m in maps] == [Fraction(1), Fraction(1, 4), Fraction(0), Fraction(1)]
    ref = timebase.TimeRef(maps[1].source, 0, 120, Fraction(1))
    assert maps[1].map_seconds(ref) == Fraction(135)
    assert maps[1].uncertainty_ns == 4_000_000 and maps[1].target == "league.game_t"


# =================================================================================================
# end to end on a synthetic replay recording
# =================================================================================================

@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory):
    """One encode for the module (about 0.6 s), state kept out of the repo while ffmpeg's caps are probed."""
    folder = tmp_path_factory.mktemp("synthetic")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(ff.STATE_ENV, str(folder / "state"))
        return _encode_synthetic(folder / "synthetic_replay.mp4")


def test_clockmap_end_to_end_on_a_synthetic_replay(synthetic_video, hershey):
    res = clock.clockmap(synthetic_video, reader="templates")
    assert res["api"] == "arsenal.media.clockmap/v0" and res["schema"] == clock.SCHEMA
    assert res["hud"] == "replay" and res["reader"] == "templates"
    assert res["params"]["every"] == "keyframes" and res["params"]["edge_fit"] is True
    passes = res["passes"]
    assert [p["speed"] for p in passes] == [s for s, _o in TRUTH]
    frame = 1 / FPS
    for p, (s, off) in zip(passes, TRUTH):
        assert abs(p["offset"] - off) <= max(s, 0.25) * frame + 1e-6, (p, off)
        assert p["fit"] == "ticks"
    assert [e["kind"] for e in res["events"]] == ["rewind", "speed_change", "speed_change"]
    for e, t in zip(res["events"], (12.0, 20.0, 32.0)):
        assert abs(e["file_t"] - t) <= frame + 1e-6, e
    assert passes[0]["file"][0] == 0.0 and passes[-1]["file"][1] >= DURATION - 2 * frame
    hits = clock.to_file(res, 105.0)
    assert [pid for _f, pid, _s in hits] == [passes[0]["id"], passes[2]["id"]]
    assert abs(hits[1][0] - 25.2) <= frame
    assert abs(clock.to_game(res, 25.2)[0] - 105.0) <= 0.25 * frame
    assert Path(res["receipt"]).is_file() and Path(res["receipt"]).is_relative_to(hershey)
    assert any("speed box is not read" in b for b in res["blind"])


def test_clockmap_every_seconds_reads_each_frame_at_its_own_time(synthetic_video, hershey):
    """every=<s> used the fps filter, which labels a frame with its output tick: two fake pauses, a fake skip and a
    fake rewind came out of the synthetic replay. Every sample now reads what the clock showed at its time."""
    res = clock.clockmap(synthetic_video, hud="replay", reader="templates", every=1.0)
    assert res["params"]["every"] == 1.0 and res["reads"]["samples"] == 40
    bad = [(t, n) for t, n in res["samples"] if n is not None and n != math.floor(_game_at(t) + 1e-9)]
    assert bad == []
    assert all(abs(t * FPS - round(t * FPS)) < 1e-3 for t, _n in res["samples"])   # frame times, not ticks
    frame = 1 / FPS
    assert [p["speed"] for p in res["passes"]] == [s for s, _o in TRUTH]
    for p, (s, off) in zip(res["passes"], TRUTH):
        assert abs(p["offset"] - off) <= max(s, 0.25) * frame + 1e-6, (p, off)
    assert [e["kind"] for e in res["events"]] == ["rewind", "speed_change", "speed_change"]


def test_a_span_that_cuts_a_slow_pass_states_its_width(synthetic_video, hershey):
    """start=30 leaves 2 s of the 0.25x pass with no tick; it used to claim offset 98.925 +-0.008 (truth 98.7)."""
    res = clock.clockmap(synthetic_video, hud="replay", reader="templates", start=30.0, dur=100.0)
    slow, fast = res["passes"]
    assert (slow["speed"], fast["speed"]) == (0.25, 1.0) and slow["fit"] == "reads"
    assert slow["file"][0] >= 30.0 and abs(slow["offset"] - TRUTH[2][1]) <= slow["tol_s"], slow
    assert abs(fast["offset"] - TRUTH[3][1]) <= 1 / FPS
    (e,) = res["events"]
    assert e["kind"] == "speed_change" and abs(e["file_t"] - 32.0) <= e["tol_s"]


def test_clockmap_fails_closed(synthetic_video, hershey):
    with pytest.raises(ff.MediaError, match="no League clock pass"):
        clock.clockmap(synthetic_video, hud="live", reader="templates")    # this recording has no live clock
    with pytest.raises(ff.MediaError, match="past the end"):
        clock.clockmap(synthetic_video, hud="replay", reader="templates", start=100.0)
    for bad in ({"dur": 0.0}, {"start": -1.0}, {"every": 0}):
        with pytest.raises(ff.MediaError, match="every=|bad range"):
            clock.clockmap(synthetic_video, hud="replay", reader="templates", **bad)


def test_cli_writes_the_clockmap(synthetic_video, hershey, capsys):
    out = hershey / "cm.json"
    assert media_main.main(["clockmap", str(synthetic_video), "--hud", "replay", "--reader", "templates",
                            "--no-edge-fit", "--out", str(out)]) == 0
    assert "passes, hud replay, reader templates, 20/20 keyframes read" in capsys.readouterr().out
    cm = clock.load(out)
    assert cm["params"]["edge_fit"] is False and cm["params"]["hud"] == "replay" and "receipt" not in cm
    assert [p["speed"] for p in cm["passes"]][:2] == [1.0, 1.0]       # keyframes alone: offsets to +-0.5 s
    assert b"\r\n" not in out.read_bytes()
    # no --out: the catalog's key (<state>/clockmap/<media id>.clockmap.json), shared with `import` and `events`
    assert media_main.main(["clockmap", str(synthetic_video), "--hud", "replay", "--reader", "templates",
                            "--no-edge-fit", "--every", "4"]) == 0
    assert "10/10 samples (every 4 s) read" in capsys.readouterr().out
    assert clock.cache_path(synthetic_video).is_file()
    assert clock.cache_path(synthetic_video).parent == hershey / "clockmap"
    assert media_main.main(["clockmap", str(synthetic_video.parent / "nope.mp4")]) == 1
    assert "no such video" in capsys.readouterr().err


# =================================================================================================
# oracles: Daniel's recordings against the hand-calibrated clockmaps (skip when missing)
# =================================================================================================

def _need(*paths: Path) -> None:
    for p in paths:
        if not p.exists():
            pytest.skip(f"oracle missing: {p}")
    clock._readers.clear()
    try:
        clock.get_reader("auto")
    except ff.MediaError:
        pytest.skip("no clock reader on this machine (rapidocr or `clockmap --train-templates`)")


@pytest.fixture(scope="module")
def cm_1751(tmp_path_factory):
    _need(REC_1751, ORACLES / "clockmaps" / "rec_17-51-11.clockmap.json")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(ff.STATE_ENV, str(tmp_path_factory.mktemp("state1751")))
        return clock.clockmap(REC_1751, hud="replay")


def _match(hand: dict, ocr: dict) -> dict:
    """The OCR pass that overlaps a hand pass's file span the most."""
    a, b = hand["file"]
    best = max(ocr["passes"], key=lambda p: min(b, p["file"][1]) - max(a, p["file"][0]))
    assert min(b, best["file"][1]) - max(a, best["file"][0]) > 0, hand["id"]
    return best


def _check_hand(hand_file: Path, ocr: dict) -> int:
    hand = json.loads(hand_file.read_text(encoding="utf-8"))
    for hp in hand["passes"]:
        p = _match(hp, ocr)
        assert p["speed"] == hp["speed"], (hp["id"], p)
        tol = max(hp["tol_s"], hp["speed"] / ocr["fps"])
        assert abs(p["offset"] - hp["offset"]) <= tol, (hp["id"], p["offset"], hp["offset"], tol)
    return len(hand["passes"])


def test_every_hand_pass_of_17_51_11_reproduced(cm_1751):
    assert _check_hand(ORACLES / "clockmaps" / "rec_17-51-11.clockmap.json", cm_1751) == 11


def test_to_file_finds_both_passes_of_the_24_02_kill(cm_1751):
    hits = clock.to_file(cm_1751, 1442.051)
    assert len(hits) == 2, hits
    (f1, _p1, s1), (f2, _p2, s2) = hits
    assert s1 == 1.0 and abs(f1 - (1442.051 + 154.15)) <= 0.5               # p2402_1x, hand offset -154.15 +- 0.5
    assert s2 == 0.25 and 1612.0 <= f2 <= 1625.0                             # the 0.25x pass at 26:52-27:05
    assert abs(f2 - TTK_DEATH_FILE_T) <= 1 / 60, (f2, TTK_DEATH_FILE_T)


def test_rec_16_50_20_hand_passes_reproduced(state):
    _need(REC_1650, ORACLES / "clockmaps" / "rec_16-50-20.clockmap.json")
    res = clock.clockmap(REC_1650, hud="replay")
    assert _check_hand(ORACLES / "clockmaps" / "rec_16-50-20.clockmap.json", res) == 2


def test_live_recording_maps_as_one_1x_pass(state):
    _need(REC_LIVE)
    res = clock.clockmap(REC_LIVE)                                           # layout found on its own
    assert res["hud"] == "live"
    (p,) = res["passes"]
    assert p["speed"] == 1.0
    assert abs(p["offset"] - LIVE_OFFSET) <= 1 / 60, p
    assert -152.17 <= p["offset"] < -151.17                                  # inside the keyframe-read interval
    assert p["game"][0] <= 2.0 and p["game"][1] >= 22 * 60 + 53              # covers 0:02-22:53 at least
    assert res["events"] == []


def test_detect_layout_on_recordings(state):
    _need(REC_1751, REC_LIVE)
    shot = {}
    for name, path, t in (("replay", REC_1751, 1621.0), ("live", REC_LIVE, 600.0), ("menu", REC_LIVE, 20.0)):
        for _req, _pts, img in frames.at_times(path, [t]):
            shot[name] = hud.detect_layout(img)
    assert shot == {"replay": "replay", "live": "live", "menu": "none"}
