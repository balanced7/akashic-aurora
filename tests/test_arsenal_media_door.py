"""arsenal.media.door: the MCP tools answer with the house results, stay transcript-lean, and edit projects one writer
at a time exactly as the web page does."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp")

from arsenal.media import door, edit, ff  # noqa: E402


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    monkeypatch.setenv("ARSENAL_MEDIA_RECEIPTS", "0")
    yield tmp_path


@pytest.fixture
def clip(tmp_path):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    out = tmp_path / "two tracks.mkv"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=160x120:r=30:d=4", "-f", "lavfi", "-i", "sine=f=440:d=4",
            "-f", "lavfi", "-i", "sine=f=660:d=4", "-map", "0", "-map", "1", "-map", "2", "-c:v", "libx264", "-g", "30",
            "-c:a", "aac", "-metadata:s:a:0", "title=Voice", "-metadata:s:a:1", "title=Game", "-y", str(out)])
    return out


def run(coro):
    return asyncio.run(coro)


def test_every_tool_is_registered_with_a_description():
    tools = run(door.mcp.list_tools())
    names = {t.name for t in tools}
    for want in ("media_doctor", "media_probe", "media_import", "media_find", "media_grab", "media_sheet",
                 "media_shots", "media_cut_plan", "media_cut", "media_audio", "media_mix", "media_qc", "media_words",
                 "media_clockmap", "media_events", "media_replay_plan", "media_avsync", "media_export",
                 "media_edit_projects", "media_edit_show", "media_edit_apply", "media_edit_render"):
        assert want in names, want
    assert all(t.description and len(t.description) > 40 for t in tools)


def test_probe_answers_with_track_names(state, clip):
    res = run(door.media_probe(str(clip)))
    assert [a["title"] for a in res["audio"]] == ["Voice", "Game"]
    assert res["api"].startswith("arsenal.media.probe")


def test_a_refusal_is_data_not_a_crash(state, tmp_path):
    res = run(door.media_probe(str(tmp_path / "missing.mp4")))
    assert "error" in res


def test_long_lists_are_cut_and_counted():
    lean = door._lean({"rows": list(range(100)), "data": list(range(500)), "n": 3})
    assert len(lean["rows"]) == door.MAX_ROWS + 1 and "60 more" in lean["rows"][-1]
    assert lean["data"].startswith("<500 items")


def test_edit_apply_is_one_writer_at_a_time(state, clip):
    run(door.media_import(str(clip)))
    media = edit.import_media(clip)
    doc = edit.new_project("door test")
    added = run(door.media_edit_apply(doc["id"], "add_clip", {"media_id": media["id"], "src_in": 0.5, "src_out": 3.0},
                                      doc["rev"]))
    assert added["rev"] == doc["rev"] + 1 and len(added["clips"]) == 1
    stale = run(door.media_edit_apply(doc["id"], "set_lane_gain", {"lane": "A1", "gain_db": -6.0}, doc["rev"]))
    assert "stale revision" in stale["error"] and stale["project"]["rev"] == added["rev"]
    muted = run(door.media_edit_apply(doc["id"], "set_lane_gain", {"lane": "A2", "mute": True}, added["rev"]))
    assert next(ln for ln in muted["lanes"]["audio"] if ln["id"] == "A2")["mute"] is True
    assert run(door.media_edit_apply(doc["id"], "teleport", {}, muted["rev"]))["error"].startswith("unknown op")


def test_replay_plan_sends_nothing(tmp_path):
    import json
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"plan": [{"plan_id": "R4", "shot": "s056", "game_in": "26:27.00",
                                          "game_out": "26:33.40", "camera": "follow", "target": "Draven",
                                          "replay_speed": 0.25, "look": "clean"}]}), encoding="utf-8")
    res = run(door.media_replay_plan(str(plan), "R4"))
    assert res["requests"][0]["path"] == "/replay/playback" and res["roll_s"] == pytest.approx(73.6, abs=0.2)
