"""arsenal.media.league.replay_api: the take planner, the loopback-only client and the run-sheet, without League.

Live proof needs a replay open in the client (Daniel's step); these pins hold the request shapes and the waits so the
first live take changes only what the swagger says is different."""
from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from pathlib import Path

import pytest

from arsenal.media.league import replay_api as ra

ROWS = [
    {"plan_id": "R4", "shot": "s056", "game_in": "26:27.00", "game_out": "26:33.40", "camera": "follow",
     "target": "Draven", "replay_speed": 0.25, "look": "clean", "what": "two axes", "shots": ["s056", "s062"]},
    {"plan_id": "R9", "shot": "s033", "game_in": "23:58.00", "game_out": "24:04.40", "camera": "push_in",
     "target": "Draven", "replay_speed": 0.25, "look": "clean", "what": "the burst"},
    {"plan_id": "R8", "shot": "thumbnail", "game_in": "26:33.40", "game_out": "26:35.40", "camera": "stills",
     "target": "Draven", "replay_speed": 0.0, "look": "clean, HUD off", "what": "ACE frame"},
    {"plan_id": "R10", "shot": "s024", "game_in": "15:44.00", "game_out": "15:59.00", "camera": "top",
     "target": "Yuumi", "replay_speed": 0.5, "look": "clean", "what": "15:50"},
]
ORACLE_PLAN = Path(r"E:\AI-Setup\state\arsenal\media-oracles\capture\draven-penta.capture.json")


def _dry(row):
    api = ra.ReplayApi(dry_run=True)
    take = ra.plan_take(row)
    res = ra.run_take(api, take, confirm=lambda msg: None)
    return take, res


def test_only_loopback_is_ever_spoken_to():
    with pytest.raises(ra.ReplayApiError, match="this machine only"):
        ra.ReplayApi("https://example.com:2999")
    ra.ReplayApi("https://127.0.0.1:2999")


def test_follow_take_requests_in_order():
    take, res = _dry(ROWS[0])
    calls = [(e["method"], e["path"], e["body"]) for e in res["log"]]
    start = 26 * 60 + 27.0 - 8.0
    assert calls == [
        ("POST", "/replay/playback", {"paused": True, "time": start}),
        ("POST", "/replay/sequence", {}),
        ("POST", "/replay/render", {"cameraMode": "fps", "cameraAttached": True, "selectionName": "Draven",
                                    "interfaceAll": True}),
        ("POST", "/replay/playback", {"speed": 0.25}),
        ("POST", "/replay/playback", {"paused": False}),
        ("POST", "/replay/render", {"interfaceAll": False}),
        ("POST", "/replay/playback", {"paused": True}),
    ]
    assert take["record_s"] == pytest.approx((26 * 60 + 33.4 + 4 - start) / 0.25, abs=0.1)
    assert res["waited_s"] == pytest.approx(take["record_s"], abs=0.2)     # the whole roll, pre-roll included


def test_push_in_is_a_field_of_view_sequence():
    take, res = _dry(ROWS[1])
    seqs = [e["body"] for e in res["log"] if e["path"] == "/replay/sequence"]
    assert seqs[0] == {}
    fov = seqs[1]["fieldOfView"]
    assert [k["value"] for k in fov] == [40.0, 26.0]
    assert fov[0]["time"] == pytest.approx(23 * 60 + 58.0)


def test_stills_pause_on_the_frame_and_never_roll():
    take, res = _dry(ROWS[2])
    assert take["record_s"] == 0.0
    assert not any(e["body"] == {"paused": False} for e in res["log"])
    assert res["log"][-1]["body"] == {"interfaceAll": False}


def test_top_camera_names_no_target():
    take, res = _dry(ROWS[3])
    render = [e["body"] for e in res["log"] if e["path"] == "/replay/render"][0]
    assert render["cameraMode"] == "top" and "selectionName" not in render


def test_bad_rows_refuse():
    with pytest.raises(ra.ReplayApiError, match="unknown camera"):
        ra.plan_take(dict(ROWS[0], camera="dolly"))
    with pytest.raises(ra.ReplayApiError, match="not after"):
        ra.plan_take(dict(ROWS[0], game_out="26:20"))


def test_run_sheet_is_in_game_order_and_counts_down():
    text = ra.run_sheet(ROWS, deadline="2026-10-21", today=date(2026, 10, 12), match="NA1_x")
    assert "**9 day(s) left**" in text
    order = [line.split("|")[2].strip() for line in text.splitlines() if line.startswith("| ") and "| ID |" not in line]
    assert order == ["R10", "R9", "R4", "R8"]
    assert "`R4_s056`" in text and "`R8_thumbnail`" in text and "fieldOfView" in text
    ins = ra.run_sheet(ROWS, today=date(2026, 10, 12),
                       insurance=[{"id": "FULL-A", "range": ["0:00", "27:09"], "camera": "director", "hud": "on"}])
    assert "FULL-A" in ins and "About 27 min" in ins


class FakeLeague:
    """A stand-in transport: answers like the Replay API, with a playhead that advances 1 s per poll."""

    def __init__(self, fail=None):
        self.time, self.paused, self.fail, self.seen = 0.0, True, fail, []

    def __call__(self, req, timeout):
        body = json.loads(req.data) if req.data else None
        self.seen.append((req.get_method(), req.full_url, body))
        if self.fail == "refused":
            raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
        if self.fail == "500":
            raise urllib.error.HTTPError(req.full_url, 500, "x", {}, io.BytesIO(b'{"error":"boom"}'))
        path = req.full_url.split("2999", 1)[1]
        if path == "/replay/playback" and req.get_method() == "POST":
            self.time = body.get("time", self.time)
            self.paused = body.get("paused", self.paused)
        if path == "/replay/playback" and req.get_method() == "GET":
            if not self.paused:
                self.time += 1.0
            return json.dumps({"time": self.time, "paused": self.paused, "speed": 0.25}).encode()
        if path == "/replay/game":
            return b'{"processID": 1234}'
        if path == "/replay/render":
            return b'{"cameraMode": "fps", "selectionName": "Draven", "interfaceAll": true, "extra": 1}'
        return b""


def test_live_take_polls_the_playhead_until_the_end():
    fake = FakeLeague()
    api = ra.ReplayApi(opener=fake)
    take = ra.plan_take(ROWS[0])
    prompts = []
    ra.run_take(api, take, confirm=prompts.append, sleep=lambda s: None)
    assert prompts[0].startswith("start the OBS recording") and prompts[-1] == "stop the OBS recording"
    assert fake.time >= 26 * 60 + 33.4 + 4.0
    assert fake.paused is True


def test_status_keeps_the_fields_a_first_check_needs():
    st = ra.ReplayApi(opener=FakeLeague()).status()
    assert st["game"] == {"processID": 1234}
    assert st["render"]["selectionName"] == "Draven" and "extra" not in st["render"]


def test_no_replay_open_says_what_to_do():
    with pytest.raises(ra.ReplayApiError, match="open the replay in the League client"):
        ra.ReplayApi(opener=FakeLeague("refused")).status()
    with pytest.raises(ra.ReplayApiError, match="HTTP 500"):
        ra.ReplayApi(opener=FakeLeague("500")).playback()


def test_swagger_saves_both_descriptions(tmp_path):
    saved = ra.ReplayApi(opener=lambda req, t: b'{"openapi": "3.0.0"}').swagger(tmp_path)
    assert sorted(saved) == ["openapi-v3.json", "swagger-v2.json"]
    assert json.loads(Path(saved["openapi-v3.json"]).read_text(encoding="utf-8")) == {"openapi": "3.0.0"}


@pytest.mark.skipif(not ORACLE_PLAN.exists(), reason="the Draven capture plan is not on this machine")
def test_the_draven_plan_plans_every_take(tmp_path):
    rows = ra.load_plan(ORACLE_PLAN)
    takes = [ra.plan_take(r) for r in rows]
    assert len(takes) == 10
    assert sum(t["record_s"] for t in takes) > 0
