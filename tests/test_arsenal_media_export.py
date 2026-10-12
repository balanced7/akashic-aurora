"""arsenal.media.export: every preset on a 10 s synthetic excerpt lands within 0.5 LU of its loudness target with true
peak at or under it, lasts exactly its frame count, and carries the expected streams; alpha_webp_anim (Pillow)
round-trips a soft-edged moving alpha with error <= 1 on every frame.

The two 4K presets (x264 slow and AMF at 3840x2160, ~10-15 s each here) run when ARSENAL_MEDIA_SLOW=1."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from arsenal.media import audio, export, ff

SLOW = os.environ.get("ARSENAL_MEDIA_SLOW") == "1"
FAST_PRESETS = ["shorts_1080x1920", "proxy_edit", "mezzanine_dnxhr", "alpha_webm", "alpha_prores4444"]
SLOW_PRESETS = ["youtube_4k60", "youtube_4k60_fast"]
EXT = {"mp4": ".mp4", "mov": ".mov", "webm": ".webm", "webp": ".webp"}


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("export_fx")
    av = d / "av.mp4"            # OBS-like: 720p60 H.264 + three Opus tracks (quiet pink-noise mix, voice, mono comms)
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=60:d=12",
            "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.01:seed=3:d=12:r=48000",
            "-f", "lavfi", "-i", "aevalsrc=0.05*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*0.5*t))"
                                 "|0.04*sin(2*PI*330*t):s=48000:c=stereo:d=12",
            "-f", "lavfi", "-i", "aevalsrc=0.03*sin(2*PI*997*t):s=48000:c=mono:d=12",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:a", "-c:v", "libx264", "-preset", "ultrafast",
            "-g", "60", "-pix_fmt", "yuv420p", "-c:a", "libopus", "-b:a", "128k", "-ac:a:0", "2",
            "-metadata:s:a:1", "title=Voice", "-metadata:s:a:2", "title=Comms", str(av)])
    alpha = d / "alpha.mkv"      # soft-edged, moving alpha: a drifting radial gradient merged onto testsrc2
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=12", "-f", "lavfi",
            "-i", "gradients=s=640x360:r=30:d=12:c0=0x000000:c1=0xffffff:type=radial:speed=0.03:seed=5",
            "-filter_complex", "[1:v]format=gray[a];[0:v][a]alphamerge,format=bgra[v]", "-map", "[v]",
            "-c:v", "ffv1", "-level", "3", str(alpha)])
    long_ = d / "long.mp4"       # 31 s: past the GPU-lock threshold for AMF presets
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=31", "-f", "lavfi", "-i",
            "sine=frequency=440:sample_rate=48000:duration=31", "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", str(long_)])
    return {"av": av, "alpha": alpha, "long": long_}


def _run(media, tmp_path, preset: str, **kw) -> dict:
    p = export.presets()["presets"][preset]
    src = media["alpha"] if preset.startswith("alpha_") else media["av"]
    out = tmp_path / f"{preset}{EXT[p['container']]}"
    return export.export(src, preset, out, start=1.0, end=11.0, **kw)


def _alpha_values(path: Path, codec: str) -> np.ndarray:
    dec = ["-c:v", "libvpx-vp9"] if codec == "vp9" else []
    info = audio.streams(path)["streams"][0]
    raw = ff.run(["-v", "error", *dec, "-i", str(path), "-frames:v", "1", "-pix_fmt", "rgba", "-f", "rawvideo", "-"],
                 binary=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(info["h"], info["w"], 4)[..., 3]


@pytest.mark.parametrize("preset", FAST_PRESETS + [pytest.param(
    p, marks=pytest.mark.skipif(not SLOW, reason="4K preset: set ARSENAL_MEDIA_SLOW=1")) for p in SLOW_PRESETS])
def test_preset_hits_loudness_duration_and_inventory(media, tmp_path, preset):
    cfg = export.presets()
    p = cfg["presets"][preset]
    res = _run(media, tmp_path, preset, audio={1: 0.0, 2: -6.0} if preset.startswith("shorts") else "0")
    assert res["ok"], res["problems"]
    out = Path(res["out"])
    inv = audio.streams(out)
    vids = [s for s in inv["streams"] if s["type"] == "video"]
    auds = [s for s in inv["streams"] if s["type"] == "audio"]
    geo = res["geometry"]
    assert len(vids) == 1 and vids[0]["packets"] == round(10.0 * geo["fps"])          # exact frame count
    assert abs(inv["duration_s"] - 10.0) <= 1.0 / geo["fps"] + 1e-6
    if isinstance(p["width"], int):
        assert (vids[0]["w"], vids[0]["h"]) == (p["width"], p["height"])
    target = cfg["loudness_targets"].get(p["loudness"])
    if preset.startswith("alpha_"):
        assert auds == []
        alpha = _alpha_values(out, vids[0]["codec"])
        assert alpha.min() < 64 and alpha.max() > 192                                   # graded alpha survived
    elif p.get("keep_all_audio"):
        assert [a["house_name"] for a in auds] == ["Mix", "Voice", "Comms"]           # names kept through MP4/MOV
    else:
        assert len(auds) == 1
    if target:
        check = audio.loudness(out)["tracks"][0]                                       # read back independently
        assert abs(check["I"] - target["I"]) <= 0.5 and check["TP"] <= target["TP"], (check, target)
    assert Path(res["receipt"]).is_file() and res["source"]["id"]


@pytest.mark.parametrize("dur", [3.0] + ([10.0] if SLOW else []))
def test_alpha_webp_anim_round_trips_alpha_on_every_frame(media, tmp_path, dur):
    from PIL import Image
    out = tmp_path / "sticker.webp"
    res = export.export(media["alpha"], "alpha_webp_anim", out, start=1.0, end=1.0 + dur)
    assert res["ok"], res["problems"]
    p = dict(export.presets()["presets"]["alpha_webp_anim"], name="alpha_webp_anim")
    info = export._source(media["alpha"])
    geo = export.out_geometry(p, info)
    assert res["webp"]["frames"] == round(dur * 30) and res["qc"]["duration_s"] == dur
    worst, levels = 0, set()
    with Image.open(out) as im:
        for k, ref in enumerate(export.webp_frames(media["alpha"], info, geo, 1.0, dur)):
            im.seek(k)
            got = np.asarray(im.convert("RGBA"))[..., 3].astype(np.int16)
            want = np.asarray(ref)[..., 3].astype(np.int16)
            worst = max(worst, int(np.abs(got - want).max()))
            levels.update(np.unique(want[::16, ::16]).tolist())
        assert im.n_frames == k + 1 == round(dur * 30)
    assert worst <= 1, worst
    assert len(levels) > 32                    # the clip really is soft-edged, not 1-bit


def test_dry_run_plans_without_writing(media, tmp_path):
    out = tmp_path / "plan.mp4"
    res = export.export(media["av"], "shorts_1080x1920", out, start=2.0, end=4.0, dry_run=True)
    steps = [s["step"] for s in res["plan"]]
    assert steps == ["audio", "video"] and not out.exists()
    video = res["plan"][1]["argv"]
    assert "-ss" in video and "libx264" in video and res["plan"][1]["gpu_lock"] is None


def test_amf_exports_over_30_s_take_the_gpu_lock(media, tmp_path):
    plan = export.export(media["long"], "proxy_edit", tmp_path / "p.mp4", dry_run=True)["plan"]
    assert plan[-1]["gpu_lock"] == "export proxy_edit"
    short = export.export(media["long"], "proxy_edit", tmp_path / "q.mp4", end=10.0, dry_run=True)["plan"]
    assert short[-1]["gpu_lock"] is None


def test_refusals(media, tmp_path):
    with pytest.raises(ff.MediaError, match="unknown preset 'tiktok'"):
        export.export(media["av"], "tiktok", tmp_path / "x.mp4")
    with pytest.raises(ff.MediaError, match="bad range"):
        export.export(media["av"], "proxy_edit", tmp_path / "x.mp4", start=5.0, end=40.0)
    with pytest.raises(ff.MediaError, match="audio track 7 is not in"):
        export.export(media["av"], "shorts_1080x1920", tmp_path / "x.mp4", end=2.0, audio="7")
    # a typo used to switch normalization off silently; an empty gain map crashed on an empty audio bus
    with pytest.raises(ff.MediaError, match="unknown loudness target 'youtub'; have: youtube, shorts, vo_stem, none"):
        export.export(media["av"], "shorts_1080x1920", tmp_path / "x.mp4", end=2.0, loudness="youtub")
    with pytest.raises(ff.MediaError, match="picks no track"):
        export.export(media["av"], "shorts_1080x1920", tmp_path / "x.mp4", end=2.0, audio={})
    assert not (tmp_path / "x.mp4").exists()


def test_without_pillow_the_webp_preset_refuses_and_names_the_fallback(media, tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "PIL", None)
    with pytest.raises(ff.MediaError, match="needs Pillow.*alpha_webm"):
        export.export(media["alpha"], "alpha_webp_anim", tmp_path / "x.webp", end=1.0)


def test_digital_silence_exports_unnormalized_with_a_note(media, tmp_path):
    silent = tmp_path / "silent.mp4"
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=3", "-f", "lavfi", "-i",
            "anullsrc=r=48000:cl=stereo:d=3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(silent)])
    res = export.export(silent, "shorts_1080x1920", tmp_path / "s.mp4", end=2.0)   # pass 2 used to fail (-inf)
    assert res["ok"], res["problems"]
    assert res["normalized"] is False and "digital silence" in res["notes"][0]
    assert res["qc"]["I"] == -70.0 and res["qc"]["TP"] is None


def test_shorts_from_a_source_narrower_than_9_16_pads(media, tmp_path):
    tall = tmp_path / "tall.mp4"                   # a phone screen recording: 9:19.5
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=540x1170:r=30:d=2", "-f", "lavfi", "-i",
            "sine=frequency=440:sample_rate=48000:duration=2", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(tall)])
    res = export.export(tall, "shorts_1080x1920", tmp_path / "t.mp4")         # the crop used to fail the encode
    assert res["ok"], res["problems"]
    assert res["geometry"]["fit"] == "pad" and "padded, not cropped" in res["notes"][0]
    v = [s for s in audio.streams(res["out"])["streams"] if s["type"] == "video"][0]
    assert (v["w"], v["h"]) == (1080, 1920)
    wide = export.out_geometry(export.presets()["presets"]["shorts_1080x1920"], {"w": 1920, "h": 1080, "fps": 60.0})
    assert wide["fit"] == "crop"


def test_presets_file_is_the_promoted_set_with_the_pillow_fix():
    cfg = export.presets()
    assert list(cfg["presets"]) == ["youtube_4k60", "youtube_4k60_fast", "shorts_1080x1920", "proxy_edit",
                                    "mezzanine_dnxhr", "alpha_webm", "alpha_prores4444", "alpha_webp_anim"]
    webp = cfg["presets"]["alpha_webp_anim"]
    assert webp["encoder"] == "pillow" and "vcodec" not in webp and webp["pillow"]["alpha_quality"] == 100
    for name, p in cfg["presets"].items():
        assert p["loudness"] in cfg["loudness_targets"], name
    assert cfg["loudness_targets"]["youtube"] == {"I": -14.0, "TP": -1.5, "LRA": 11.0}


def test_cli_lists_and_dry_runs(media, tmp_path, capsys):
    assert export.cli("export", ["--list"]) == 0
    assert "alpha_webp_anim" in capsys.readouterr().out
    assert export.cli("export", ["proxy_edit", str(media["av"]), str(tmp_path / "x.mp4"), "--end", "2",
                                 "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["plan"][0]["step"] == "video"
