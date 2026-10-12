"""arsenal.media.catalog: import without copying, idempotent ingest, find, spans/artifacts/tags kept in the sidecars
and rebuilt row for row, browser-drop resolution, wall-time links to practice sessions and Riot matches; then the
same against Daniel's 11 recordings of 2026-10-10/11 and the practice log."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

import pytest

from arsenal.media import catalog, ff, probe

REPO = Path(__file__).resolve().parents[1]
LIBRARY = Path(r"E:\Video Output E")
SESSIONS = REPO / "state" / "arsenal" / "performance"
SESSION = "20261011-165503-f62d348c"
RECENT = ["2026-10-10 20-06-47.mp4", "2026-10-10 20-55-54.mp4", "2026-10-10 20-58-23.mp4", "2026-10-10 21-35-21.mp4",
          "2026-10-11 16-48-25.mp4", "2026-10-11 16-50-20.mp4", "2026-10-11 16-51-54.mp4", "2026-10-11 16-56-57.mp4",
          "2026-10-11 17-02-30.mp4", "2026-10-11 17-06-22.mp4", "2026-10-11 17-51-11.mp4"]


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("catalog_media")
    made = {}
    for name, dur, tracks, base in (("2026-10-11 09-30-00.mkv", 3, 3, 300), ("2026-10-11 09-40-00.mp4", 2, 1, 300),
                                    ("plain clip.mp4", 2, 1, 1000)):
        args = ["-f", "lavfi", "-i", f"testsrc2=s=160x120:r=30:d={dur}"]
        for k in range(tracks):
            args += ["-f", "lavfi", "-i", f"sine=f={base + 200 * k}:d={dur}"]
        args += ["-map", "0:v"] + [x for k in range(tracks) for x in ("-map", f"{k + 1}:a")]
        args += ["-c:v", "libx264", "-g", "30", "-bf", "0", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(d / name)]
        ff.run(args)
        made[name] = d / name
    (d / "notes.txt").write_text("not media", encoding="utf-8")
    return made


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    return tmp_path / "state"


def _quick(target, **kw):
    return catalog.ingest(target, proxy=False, shots=False, peaks=False, clock="off", **kw)


def _lastmod_ms(p: Path) -> int:
    return p.stat().st_mtime_ns // 1_000_000


# ------------------------------------------------------------------------------------------------- import + find
def test_quick_ingest_of_a_folder_is_idempotent(clips, state):
    folder = next(iter(clips.values())).parent
    before = {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in folder.iterdir()}
    res = _quick(folder)
    assert sorted(Path(r["path"]).name for r in res) == sorted(clips)          # notes.txt is not media
    assert all(r["api"] == "arsenal.media.import/v0" and not r.get("error") for r in res)
    assert all(r["done"][:1] == ["probe"] for r in res)
    first = catalog.dump()
    assert len(first["media"]) == 3 and len(first["streams"]) == 3 + 5          # 3 video + 3 + 1 + 1 audio
    _quick(folder)
    assert catalog.dump() == first                                              # the second time adds 0 rows
    assert {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in folder.iterdir()} == before
    assert sorted(x.name for x in folder.iterdir()) == sorted(before)          # nothing written beside them


def test_find_by_columns_dates_text_and_refuses_unknown_keys(clips, state):
    _quick(next(iter(clips.values())).parent)
    assert [r["name"] for r in catalog.find(n_audio=3)] == ["2026-10-11 09-30-00.mkv"]
    stamped = catalog.find(recorded_after="2026-10-11T09:35", recorded_before="2026-10-11T23:59")
    assert [r["name"] for r in stamped] == ["2026-10-11 09-40-00.mp4"]
    plain = catalog.find(text="plain")[0]                  # no stamp, no tag: made today, so its mtime decides
    assert plain["recorded_at"] > "2026-10-11T09:40" and plain["n_audio"] == 1
    assert [r["name"] for r in catalog.find(text="plain")] == ["plain clip.mp4"]
    assert len(catalog.find(vcodec="h264", limit=2)) == 2
    with pytest.raises(ff.MediaError, match="unknown condition"):
        catalog.find(colour="blue")


def test_find_date_bounds_take_a_space_a_t_a_datetime_or_a_date(clips, state):
    """As text, '2026-10-11 17:00' sorts before every '2026-10-11T..' of that day: the bounds are normalised to the
    stored form first (the review caught a space matching the whole day)."""
    _quick(next(iter(clips.values())).parent)
    for after, before in (("2026-10-11 09:35", "2026-10-11 23:59"), ("2026-10-11T09:35", "2026-10-11T23:59"),
                          (datetime(2026, 10, 11, 9, 35), datetime(2026, 10, 11, 23, 59)),
                          (datetime(2026, 10, 11, 9, 35).astimezone(), " 2026-10-11 23:59:00 ")):
        got = catalog.find(recorded_after=after, recorded_before=before)
        assert [r["name"] for r in got] == ["2026-10-11 09-40-00.mp4"], (after, before)
    early = catalog.find(recorded_after=date(2026, 10, 11), recorded_before="2026-10-11 09:35")
    assert [r["name"] for r in early] == ["2026-10-11 09-30-00.mkv"]
    with pytest.raises(ff.MediaError, match="not an ISO date"):
        catalog.find(recorded_after="yesterday")


def test_a_byte_identical_copy_is_the_same_media_row(clips, state, tmp_path):
    a = clips["plain clip.mp4"]
    b = tmp_path / "copy of plain.mp4"
    shutil.copy2(a, b)
    (ra,) = _quick(a)
    (rb,) = _quick(b)
    assert ra["id"] == rb["id"]
    assert [(r["name"], r["path"]) for r in catalog.find()] == [(b.name, str(b.resolve()))]   # the last path seen


def test_probe_alone_does_not_catalog_a_file(clips, state):
    probe.probe(clips["plain clip.mp4"])
    assert catalog.find() == []
    catalog.upsert(probe.probe(clips["plain clip.mp4"]))
    assert [r["name"] for r in catalog.find()] == ["plain clip.mp4"]


# ------------------------------------------------------------------------------------------------- knowledge + rebuild
def test_upsert_of_a_held_probe_keeps_what_was_learned_since(clips, state):
    """upsert brings facts, never knowledge: a probe result held while another writer added spans (or a keyframe
    index) must not erase them from the sidecar, which rebuild() could then never recover."""
    clip = clips["plain clip.mp4"]
    held = probe.probe(clip)
    mid = catalog.upsert(held)
    catalog.add_spans(mid, "window", [(1.0, 2.0, "added after the probe")], source="other")
    probe.probe(clip, keyframes=True)
    catalog.upsert(held)
    assert [s["label"] for s in catalog.spans(mid, "window")] == ["added after the probe"]
    assert probe.read_sidecar(mid)["keyframes"]
    catalog._mutate(mid, lambda s: s.update(probed_at="2000-01-01T00:00:00"))   # now the held facts are newer
    catalog.upsert(dict(held, duration_s=99.0))
    side = probe.read_sidecar(mid)
    assert side["duration_s"] == 99.0 and [s["label"] for s in side["spans"]] == ["added after the probe"]
    assert catalog.find(text="plain")[0]["duration_s"] == 99.0
    before = catalog.dump()
    catalog.rebuild()
    assert catalog.dump() == before


def test_threads_writing_one_sidecar_lose_nothing_and_never_fail(clips, state):
    clip = clips["plain clip.mp4"]
    held = probe.probe(clip)
    mid = catalog.upsert(held)
    errors = []

    def spans(k: int) -> None:
        for i in range(12):
            try:
                catalog.add_spans(mid, "note", [(i, i + 0.5, f"{k}-{i}")], source=f"w{k}")
                catalog.is_cataloged(mid)
            except Exception as exc:
                errors.append(f"spans {k}: {exc!r}")

    def imports() -> None:
        for _ in range(12):
            try:
                catalog.upsert(held)
                probe.probe(clip, refresh=True, mediainfo=False)
            except Exception as exc:
                errors.append(f"import: {exc!r}")
    threads = [threading.Thread(target=spans, args=(k,)) for k in range(3)] + [threading.Thread(target=imports)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert errors == []
    notes = catalog.spans(mid, "note")
    assert sorted((s["source"], s["label"]) for s in notes) == [("w0", "0-11"), ("w1", "1-11"), ("w2", "2-11")]
    assert sorted(s["label"] for s in probe.read_sidecar(mid)["spans"]) == ["0-11", "1-11", "2-11"]
    assert not list(probe.sidecar_dir().glob("*.tmp")) and not list(probe.sidecar_dir().glob("*.lock"))


def test_spans_artifacts_and_tags_live_in_the_sidecar_and_rebuild_row_for_row(clips, state, tmp_path):
    (r,) = _quick(clips["2026-10-11 09-30-00.mkv"])
    mid = r["id"]
    assert catalog.add_spans(mid, "note", [(0.5, 1.0, "first"), {"t0": 2.0, "t1": 2.5, "label": "second",
                                                                  "data": {"why": "x"}}], source="test") == 2
    assert catalog.add_spans(mid, "note", [1.5], source="test") == 1             # a re-run replaces, never adds
    art = tmp_path / "thing.png"
    art.write_bytes(b"png")
    catalog.add_artifact(mid, "sheet", art, params={"n": 3}, api="arsenal.media.sheet/v0")
    catalog.add_artifact(mid, "sheet", art, params={"n": 3}, api="arsenal.media.sheet/v0")
    catalog.tag(mid, "champion", ["Draven", "Yuumi"])
    notes = catalog.spans(mid, "note")
    assert [(s["t0"], s["t1"], s["source"]) for s in notes] == [(1.5, 1.5, "test")]
    assert catalog.artifact(mid, "sheet")["params"] == {"n": 3}
    assert [r["name"] for r in catalog.find(tag="champion=Yuumi")] == ["2026-10-11 09-30-00.mkv"]
    assert [r["name"] for r in catalog.find(has_artifact="sheet")] == ["2026-10-11 09-30-00.mkv"]
    side = probe.read_sidecar(mid)
    assert side["cataloged"] and side["spans"][0]["label"] is None and len(side["artifacts"]) == 1
    _quick(next(iter(clips.values())).parent)
    before = catalog.dump()
    res = catalog.rebuild()
    assert res["errors"] == [] and res["cataloged"] == 3
    assert catalog.dump() == before
    catalog.db_path().unlink()                                                  # lose the database entirely
    for extra in catalog.db_path().parent.glob("catalog.sqlite-*"):
        extra.unlink()
    catalog.rebuild()
    assert catalog.dump() == before
    with pytest.raises(ff.MediaError, match="span kind"):
        catalog.add_spans(mid, "vibes", [1.0], source="test")
    with pytest.raises(ff.MediaError, match="ends before"):
        catalog.add_spans(mid, "note", [(2.0, 1.0)], source="test")


# ------------------------------------------------------------------------------------------------- drag and drop
def test_resolve_dropped_from_the_catalog_and_from_a_root(clips, state, tmp_path):
    mkv = clips["2026-10-11 09-30-00.mkv"]
    _quick(mkv)
    t = time.perf_counter()
    assert catalog.resolve_dropped(mkv.name, mkv.stat().st_size, _lastmod_ms(mkv)) == str(mkv.resolve())
    assert time.perf_counter() - t < 0.05
    assert catalog.resolve_dropped(mkv.name.upper(), mkv.stat().st_size, _lastmod_ms(mkv)) == str(mkv.resolve())
    assert catalog.resolve_dropped(mkv.name, mkv.stat().st_size, 0) == str(mkv.resolve())   # 0 = unknown
    assert catalog.resolve_dropped(mkv.name, mkv.stat().st_size + 1, _lastmod_ms(mkv)) is None
    assert catalog.resolve_dropped(mkv.name, mkv.stat().st_size, _lastmod_ms(mkv) - 60_000) is None
    root = tmp_path / "library"
    hidden = root / "season" / "week 2" / "dropped clip.mp4"                   # two folders down, never imported
    hidden.parent.mkdir(parents=True)
    shutil.copy2(clips["plain clip.mp4"], hidden)
    assert catalog.resolve_dropped(hidden.name, hidden.stat().st_size, _lastmod_ms(hidden)) is None
    got = catalog.resolve_dropped(hidden.name, hidden.stat().st_size, _lastmod_ms(hidden), roots=[root])
    assert got == str(hidden)
    sibling = mkv.parent / "sibling.mp4"                                      # a folder the catalog knows is a root
    shutil.copy2(clips["plain clip.mp4"], sibling)
    try:
        assert catalog.resolve_dropped("sibling.mp4", sibling.stat().st_size, _lastmod_ms(sibling)) == str(sibling)
    finally:
        sibling.unlink()


# ------------------------------------------------------------------------------------------------- links by wall time
def _session(root: Path, start_epoch: float, dur_s: float, name="20261011-093000-0000abcd") -> str:
    d = root / name
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({"session": name, "opened_ns": int(start_epoch * 1e9),
                                                "duration_s": dur_s, "closed": True, "event_count": 12}),
                                    encoding="utf-8")
    return name


def _match(root: Path, match_id: str, start_epoch: float, dur_s: int) -> None:
    d = root / match_id
    d.mkdir(parents=True)
    (d / "match.json").write_text(json.dumps({"metadata": {"matchId": match_id},
                                              "info": {"gameCreation": int(start_epoch * 1000) - 15000,
                                                       "gameStartTimestamp": int(start_epoch * 1000),
                                                       "gameEndTimestamp": int((start_epoch + dur_s) * 1000),
                                                       "gameDuration": dur_s}}), encoding="utf-8")


def test_link_ties_sessions_and_matches_by_wall_time(clips, state, tmp_path):
    (r,) = _quick(clips["2026-10-11 09-30-00.mkv"])
    sc = probe.read_sidecar(r["id"])
    t0 = sc["recorded_epoch"]
    sessions, matches = tmp_path / "sessions", tmp_path / "riot"
    name = _session(sessions, t0 - 60, 600)
    _session(sessions, t0 + 3600, 600, name="20261011-103000-0000beef")       # an hour later: no overlap
    _match(matches, "NA1_1", t0 - 1, 1800)
    _match(matches, "NA1_2", t0 - 7200, 1800)                                  # ended long before
    res = catalog.link(r["id"], sessions_root=sessions, match_roots=[matches])
    links = res["links"]
    assert [(p["session"], p["confidence"]) for p in links["practice_sessions"]] == [(name, 1.0)]
    assert [(m["match_id"], m["relation"]) for m in links["riot_matches"]] == [("NA1_1", "played_during")]
    assert res["kind"] == "piano"                                              # practice overlap, not League
    assert [r_["name"] for r_ in catalog.find(tag=f"practice_session={name}")] == ["2026-10-11 09-30-00.mkv"]
    assert [r_["name"] for r_ in catalog.find(kind="piano")] == ["2026-10-11 09-30-00.mkv"]


def test_link_reads_the_riot_lanes_match_cache_by_default(clips, state):
    """Matches are looked for where arsenal.media.league.riot caches them (under the state folder), never in the
    test-oracle folder; both of the cache's layouts are read."""
    from arsenal.media.league import riot
    (r,) = _quick(clips["2026-10-11 09-30-00.mkv"])
    t0 = probe.read_sidecar(r["id"])["recorded_epoch"]
    root = riot.default_root()
    assert catalog.default_match_roots() == [root] and root.is_relative_to(state)
    _match(root, "NA1_FOLDER", t0 - 1, 1800)                                   # <root>/<id>/match.json
    flat = root / "flat"
    _match(flat, "NA1_FLAT", t0 - 1, 1800)
    (flat / "NA1_FLAT" / "match.json").rename(root / "NA1_FLAT.match.json")    # <root>/<id>.match.json
    res = catalog.link(r["id"], sessions_root=state / "no sessions")
    assert sorted(m["match_id"] for m in res["links"]["riot_matches"]) == ["NA1_FLAT", "NA1_FOLDER"]
    assert res["params"]["match_roots"] == [str(root)]


def test_a_league_replay_links_to_the_match_it_followed(clips, state, tmp_path):
    (r,) = _quick(clips["2026-10-11 09-40-00.mp4"])
    t0 = probe.read_sidecar(r["id"])["recorded_epoch"]
    matches = tmp_path / "riot"
    _match(matches, "NA1_OLD", t0 - 40 * 3600, 1500)
    _match(matches, "NA1_NEW", t0 - 3 * 3600, 1500)
    catalog._mutate(r["id"], lambda s: s.update(kind="league_replay", kind_from="hud"))
    links = catalog.link(r["id"], sessions_root=tmp_path / "none", match_roots=[matches])["links"]
    assert [(m["match_id"], m["relation"], m["confidence"]) for m in links["riot_matches"]] == [
        ("NA1_NEW", "replay_candidate", 0.5)]


# ------------------------------------------------------------------------------------------------- heavy phase
def test_full_ingest_adds_proxy_and_shots_and_reports_what_it_skipped(clips, state):
    (r,) = catalog.ingest(clips["2026-10-11 09-40-00.mp4"])                     # the spec's defaults: everything
    assert r["done"][:2] == ["probe", "link"] and "keyframes" in r["done"] and "proxy" in r["done"]
    assert "shots" in r["done"]
    assert r.get("error") is None
    assert catalog.artifact(r["id"], "proxy") is not None
    assert catalog.spans(r["id"], "shot")[0]["t0"] == 0.0
    side = probe.read_sidecar(r["id"])
    assert side["video"]["keyframes_n"] and side["keyframes"]
    if "peaks" in r["done"]:
        assert catalog.artifact(r["id"], "peaks") is not None
    else:
        assert "peaks" in r["skipped"]


def test_cli_quick_import_and_find(clips, state):
    env = dict(os.environ, PYTHONUTF8="1", ARSENAL_MEDIA_STATE=str(state))
    run = subprocess.run([sys.executable, "-m", "arsenal.media", "import", "--quick", str(clips["plain clip.mp4"])],
                         cwd=REPO, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert "plain clip.mp4: unknown" in run.stdout and "did probe" in run.stdout
    found = subprocess.run([sys.executable, "-m", "arsenal.media", "find", "--json"], cwd=REPO, env=env,
                           capture_output=True, text=True, timeout=60)
    assert [r["name"] for r in json.loads(found.stdout)] == ["plain clip.mp4"]


def test_the_drop_tool_exists_with_crlf_for_cmd():
    cmd = REPO / "arsenal" / "tools" / "media-import.cmd"
    data = cmd.read_bytes()
    assert b"py -m arsenal.media import --dropped" in data
    assert data.count(b"\n") == data.count(b"\r\n")        # .gitattributes: *.cmd eol=crlf (cmd.exe needs it)


# ------------------------------------------------------------------------------------------------- Daniel's recordings
needs_library = pytest.mark.skipif(not all((LIBRARY / n).is_file() for n in RECENT),
                                   reason="Daniel's recordings are not on this machine")


@needs_library
def test_the_11_recordings_import_twice_without_new_rows(state):
    t = time.perf_counter()
    first_res = [catalog.ingest(LIBRARY / n, proxy=False, shots=False, peaks=False)[0] for n in RECENT]
    cold = time.perf_counter() - t
    assert not [r["error"] for r in first_res if r.get("error")]
    first = catalog.dump()
    t = time.perf_counter()
    for n in RECENT:
        _quick(LIBRARY / n)
    warm = time.perf_counter() - t
    assert catalog.dump() == first and len(first["media"]) == 11
    print(f"\n11 recordings: quick ingest {cold:.2f} s cold, {warm:.2f} s again (0 new rows)")
    assert all(r["recorded_at"].startswith(("2026-10-10", "2026-10-11")) for r in first_res)
    assert len(catalog.find(recorded_after="2026-10-11", recorded_before="2026-10-12")) == 7
    catalog.rebuild()
    assert catalog.dump() == first


@needs_library
@pytest.mark.skipif(not (SESSIONS / SESSION / "session.json").is_file(), reason="practice log not on this machine")
def test_practice_session_links_the_two_piano_recordings(state):
    linked = {}
    for n in ("2026-10-11 16-51-54.mp4", "2026-10-11 16-56-57.mp4", "2026-10-11 17-06-22.mp4"):
        (r,) = _quick(LIBRARY / n)
        linked[n] = [p["session"] for p in r["links"]["practice_sessions"]]
    assert linked["2026-10-11 16-56-57.mp4"] == [SESSION]
    assert linked["2026-10-11 17-06-22.mp4"] == [SESSION]
    assert linked["2026-10-11 16-51-54.mp4"] == []          # ends before the session opened at 16:55:03
    session = probe.read_sidecar(_quick(LIBRARY / "2026-10-11 17-06-22.mp4")[0]["id"])["links"]["practice_sessions"][0]
    assert session["session_start"] == "2026-10-11T16:55:03" and session["session_s"] == pytest.approx(3090.853)


@needs_library
def test_resolve_a_library_file_in_under_50_ms_and_refuse_outsiders(state, tmp_path):
    target = LIBRARY / "2026-10-11 17-51-11.mp4"
    catalog.resolve_dropped("warm-up.mp4", 1, 1)               # first call pays the one-time serve import
    t = time.perf_counter()
    got = catalog.resolve_dropped(target.name, target.stat().st_size, _lastmod_ms(target))
    ms = (time.perf_counter() - t) * 1000
    assert got == str(target)
    outsider = tmp_path / "elsewhere.mp4"
    outsider.write_bytes(b"\0" * 1000)
    assert catalog.resolve_dropped(outsider.name, 1000, _lastmod_ms(outsider)) is None
    print(f"\nresolve_dropped from the library root (empty catalog): {ms:.1f} ms")
    assert ms < 50
