"""arsenal.media.probe: a file's facts read once and remembered as a sidecar under the state folder (never beside the
original); titled audio tracks and the house track map; keyframe interval and index; OBS file-name time; the real
33-minute OBS recording against the facts the research track measured."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import threading
import time
from pathlib import Path

import pytest

from arsenal.media import ff, probe

ORACLES = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles"
RECORDING = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("probe_media")
    three = d / "2026-10-11 09-30-00.mkv"          # an OBS-style name: the recorded time comes from it
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=4",
            "-f", "lavfi", "-i", "sine=f=440:d=4", "-f", "lavfi", "-i", "sine=f=660:d=4",
            "-f", "lavfi", "-i", "sine=f=880:d=4",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:a",
            "-c:v", "libx264", "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-bf", "0",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2",
            "-metadata:s:a:0", "title=Voice", "-metadata:s:a:1", "title=Game", "-metadata:s:a:2", "title=Comms",
            "-y", str(three)])
    plain = d / "plain clip.mp4"                   # no stamp, an untitled track, a creation_time tag
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=160x120:r=25:d=2", "-f", "lavfi", "-i", "sine=f=300:d=2",
            "-c:v", "libx264", "-g", "50", "-bf", "2", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-metadata", "creation_time=2026-10-10T12:00:00Z", "-y", str(plain)])
    return {"three": three, "plain": plain}


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    return tmp_path / "state"


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_titled_tracks_keyframes_and_the_sidecar(media, state):
    p = media["three"]
    before = (p.stat().st_mtime_ns, _digest(p))
    sc = probe.probe(p)
    assert sc["schema"] == "arsenal.media.sidecar/v0" and sc["api"] == "arsenal.media.probe/v0"
    v = sc["video"]
    assert (v["codec"], v["w"], v["h"], v["fps"], v["has_b_frames"], v["vfr"]) == ("h264", 320, 240, 30.0, 0, False)
    assert v["keyint_s"] == pytest.approx(1.0) and v["keyint_frames"] == 30 and v["keyint_from"] == "head:20s"
    assert [(a["index"], a["title"], a["house_name"]) for a in sc["audio"]] == [
        (0, "Voice", "Voice"), (1, "Game", "Game"), (2, "Comms", "Comms")]
    assert sc["duration_s"] == pytest.approx(4.0, abs=0.05)
    assert (sc["recorded_at"], sc["recorded_from"]) == ("2026-10-11T09:30:00", "filename")
    assert sc["kind"] == "unknown"                 # lavfi, not OBS; no HUD can see a test pattern
    side = state / "sidecars" / f"{sc['id']}.json"
    assert Path(sc["sidecar_path"]) == side and side.is_file()
    assert not any(x.suffix == ".json" for x in p.parent.iterdir())     # nothing beside the original
    stored = json.loads(side.read_text(encoding="utf-8"))
    assert "api" not in stored and "receipt" not in stored and stored["id"] == sc["id"]
    assert b"\r\n" not in side.read_bytes()
    assert (p.stat().st_mtime_ns, _digest(p)) == before                # read-only
    assert sc["receipt"] and Path(sc["receipt"]).is_file()


def test_untitled_track_takes_the_house_name_and_tags_give_the_time(media, state):
    sc = probe.probe(media["plain"])
    assert sc["audio"][0]["title"] is None and sc["audio"][0]["house_name"] == "Mix"
    assert sc["video"]["has_b_frames"] == 2
    assert sc["recorded_from"] == "tags"
    assert sc["recorded_epoch"] == pytest.approx(1791633600.0)         # 2026-10-10T12:00:00Z


def test_keyframe_index_matches_the_packet_scan(media, state):
    sc = probe.probe(media["three"], keyframes=True)
    assert sc["keyframes"] == probe.keyframes(media["three"]) == pytest.approx([0.0, 1.0, 2.0, 3.0])
    assert sc["video"]["keyframes_n"] == 4 and sc["video"]["keyint_from"] == "full"


def test_second_probe_answers_from_the_sidecar_and_refresh_keeps_catalog_news(media, state):
    first = probe.probe(media["three"])
    t = time.perf_counter()
    again = probe.probe(media["three"])
    assert again["cached"] is True and again["receipt"] is None and time.perf_counter() - t < 0.2
    assert {k: v for k, v in again.items() if k not in probe.RESULT_KEYS} == \
           {k: v for k, v in first.items() if k not in probe.RESULT_KEYS}
    side = probe.read_sidecar(first["id"])
    side["spans"] = [{"kind": "note", "t0": 1.0, "t1": 2.0, "label": "keep me", "data": None, "source": "test"}]
    with probe.sidecar_lock(first["id"]):
        probe.write_sidecar(side)
    fresh = probe.probe(media["three"], refresh=True)
    assert fresh["cached"] is False and fresh["spans"][0]["label"] == "keep me"


def test_a_copy_is_the_same_media_at_a_new_path(media, state, tmp_path):
    a = probe.probe(media["plain"])
    copy = tmp_path / "moved" / "renamed.mp4"
    copy.parent.mkdir()
    copy.write_bytes(media["plain"].read_bytes())
    b = probe.probe(copy)
    assert b["id"] == a["id"] and b["path"] == str(copy.resolve()) and b["name"] == "renamed.mp4"


def test_a_sharing_violation_is_retried_and_a_lasting_one_refuses(media, state, monkeypatch):
    """Windows answers PermissionError while another process replaces the sidecar: that is a moment, not 'no
    sidecar'. A lock that lasts past SHARE_RETRY_S refuses instead of reading as missing."""
    sc = probe.probe(media["three"])
    real = Path.read_text
    refusals = {"n": 3}

    def flaky(self, *a, **k):
        if self.suffix == ".json" and refusals["n"] > 0:
            refusals["n"] -= 1
            raise PermissionError(13, "The process cannot access the file")
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "read_text", flaky)
    assert probe.read_sidecar(sc["id"])["id"] == sc["id"] and refusals["n"] == 0
    refusals["n"] = 10 ** 9
    monkeypatch.setattr(probe, "SHARE_RETRY_S", 0.1)
    with pytest.raises(ff.MediaError, match="stayed locked"):
        probe.read_sidecar(sc["id"])


def test_a_reader_holding_the_sidecar_open_delays_the_write_instead_of_failing_it(media, state):
    sc = probe.probe(media["three"])
    fh = open(probe.sidecar_path(sc["id"]), encoding="utf-8")       # Windows: the replace is refused while open
    threading.Timer(0.3, fh.close).start()
    t = time.perf_counter()
    with probe.sidecar_lock(sc["id"]):
        probe.write_sidecar(dict(probe.pure(sc), tags=[{"key": "k", "value": "v", "source": "test"}]))
    waited = time.perf_counter() - t
    assert probe.read_sidecar(sc["id"])["tags"] == [{"key": "k", "value": "v", "source": "test"}]
    assert not list(probe.sidecar_dir().glob("*.tmp"))
    if os.name == "nt":
        assert 0.2 < waited < probe.SHARE_RETRY_S


def test_missing_file_refuses_in_one_line(state, tmp_path):
    with pytest.raises(ff.MediaError, match="no such file"):
        probe.probe(tmp_path / "nope.mp4")


def test_cli_prints_the_facts(media, state, capsys):
    assert probe.cli("probe", [str(media["three"])]) == 0
    out = capsys.readouterr().out
    assert '"Voice"' in out and "keyframe every 1.0 s (30 frames" in out


# ------------------------------------------------------------------------------------------------- the real recording
needs_recording = pytest.mark.skipif(not RECORDING.is_file(), reason="Daniel's recording is not on this machine")


@needs_recording
def test_the_33_minute_obs_recording(state):
    t = time.perf_counter()
    sc = probe.probe(RECORDING, keyframes=True)
    cold = time.perf_counter() - t
    v = sc["video"]
    assert (v["codec"], v["w"], v["h"], v["fps"], v["has_b_frames"]) == ("hevc", 1920, 1080, 60.0, 0)
    assert [(a["codec"], a["channels"], a["sample_rate"]) for a in sc["audio"]] == [("opus", 2, 48000)]
    assert v["keyint_s"] == pytest.approx(4.1667, abs=0.001) and v["keyint_frames"] == 250
    assert v["keyframes_n"] == 487
    assert sc["duration_s"] == pytest.approx(2028.25, abs=0.01)
    assert sc["encoder"] == "OBS Studio (32.2.2)" and v["encoder"] == "h265_texture_amf"
    assert sc["recorded_at"] == "2026-10-11T17:51:11"
    t = time.perf_counter()
    assert probe.probe(RECORDING)["cached"] is True
    warm = time.perf_counter() - t
    print(f"\n17-51-11: cold probe + keyframe index {cold:.2f} s, from the sidecar {warm * 1000:.1f} ms")
    assert warm < 0.05


@needs_recording
@pytest.mark.skipif(not (ORACLES / "clips" / "kf_full.csv").is_file(), reason="research oracle missing")
def test_keyframes_and_facts_match_the_research_oracles(state):
    sc = probe.probe(RECORDING, keyframes=True)
    with open(ORACLES / "clips" / "kf_full.csv", newline="") as fh:
        kf = [float(r[0]) for r in csv.reader(fh) if r]
    assert sc["keyframes"] == pytest.approx(kf, abs=1e-6)
    raw = json.loads((ORACLES / "clips" / "probe_full.json").read_text(encoding="utf-8"))
    assert sc["duration_s"] == float(raw["format"]["duration"])
    assert sc["size"] == int(raw["format"]["size"])


@needs_recording
@pytest.mark.skipif(importlib.util.find_spec("arsenal.media.league.clock") is None,
                    reason="the league lane's HUD clock reader is not built yet")
def test_kind_is_league_replay(state):
    sc = probe.probe(RECORDING)
    assert sc["kind"] == "league_replay", sc.get("kind_votes")
