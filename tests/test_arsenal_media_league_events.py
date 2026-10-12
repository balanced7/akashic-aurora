"""arsenal.media.league.riot + league.events + league.live: Riot's record typed, pinned to frames, fights, live poll.

Synthetic tests build a small match and a clockmap in memory (no real names, no Riot data). The oracle tests read
NA1_5658447097 from state/arsenal/media-oracles (other players' names stay there, read at run time) and Daniel's
17-51-11 recording, and skip when they are missing.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from arsenal.media import __main__ as media_main
from arsenal.media import ff
from arsenal.media.league import clock, events, live, riot

ORACLES = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles"
REC_1751 = Path("E:/Video Output E/2026-10-11 17-51-11.mp4")
MATCH_ID = "NA1_5658447097"
#: The TTK work's 24:02 death frame in the 0.25x pass: ttk/video/work/d2402q_steps.json, a window read from file
#: 1612.0 s at 60 fps whose frame 542 is the first without Draven's bar.
TTK_DEATH_FILE_T = 1612.0 + 542 / 60


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    clock._readers.clear()
    yield tmp_path / "state"
    clock._readers.clear()


# =================================================================================================
# a small synthetic match
# =================================================================================================

def _participant(pid: int, team: int, champ: str, k: int, d: int, a: int, items, rbi=None) -> dict:
    p = {"participantId": pid, "teamId": team, "championName": champ, "teamPosition": "BOTTOM",
         "riotIdGameName": f"Player {pid}", "riotIdTagline": "TST", "puuid": f"puuid-{pid}",
         "kills": k, "deaths": d, "assists": a, "win": team == 100}
    for i in range(7):
        p[f"item{i}"] = items[i] if i < len(items) else 0
    if rbi:
        p["roleBoundItem"] = rbi
    return p


def _kill(ms: int, killer: int, victim: int, assists=()) -> dict:
    return {"type": "CHAMPION_KILL", "timestamp": ms, "killerId": killer, "victimId": victim,
            "assistingParticipantIds": list(assists), "position": {"x": 100, "y": 200}, "bounty": 300,
            "shutdownBounty": 0}


def _synthetic(tmp: Path, *, layout: str = "folder") -> Path:
    match = {"metadata": {"matchId": "TST_1", "participants": []},
             "info": {"gameDuration": 600, "gameVersion": "16.20.824.8524", "participants": [
                 _participant(1, 100, "Draven", 2, 1, 0, [6697, 0, 3031], rbi=3006),
                 _participant(2, 100, "Yuumi", 0, 0, 2, [3870]),
                 _participant(3, 200, "MissFortune", 1, 1, 0, [1055]),
                 _participant(4, 200, "Swain", 0, 1, 1, [1056])]}}
    timeline = {"metadata": {"matchId": "TST_1"}, "info": {"frameInterval": 60000, "frames": [
        {"timestamp": 0, "participantFrames": {"1": {"currentGold": 500, "totalGold": 500, "xp": 0, "level": 1,
                                                     "minionsKilled": 0, "jungleMinionsKilled": 0,
                                                     "position": {"x": 1, "y": 2}}},
         "events": [{"type": "ITEM_PURCHASED", "timestamp": 1000, "participantId": 1, "itemId": 1055},
                    {"type": "ITEM_PURCHASED", "timestamp": 0, "participantId": 0, "itemId": 3865}]},
        {"timestamp": 60000, "participantFrames": {}, "events": [
            _kill(100_000, 1, 3, [2]),
            _kill(108_500, 3, 1),
            {"type": "WARD_PLACED", "timestamp": 109_000, "creatorId": 2, "wardType": "YELLOW_TRINKET"},
            _kill(112_250, 1, 4, [2]),
            {"type": "ELITE_MONSTER_KILL", "timestamp": 300_000, "killerId": 1, "killerTeamId": 100,
             "monsterType": "DRAGON", "monsterSubType": "WATER_DRAGON", "assistingParticipantIds": [2],
             "position": {"x": 9866, "y": 4414}},
            {"type": "BUILDING_KILL", "timestamp": 302_000, "killerId": 1, "teamId": 200,
             "buildingType": "TOWER_BUILDING", "towerType": "OUTER_TURRET", "laneType": "BOT_LANE"},
            {"type": "LEVEL_UP", "timestamp": 303_000, "participantId": 1, "level": 9},
            {"type": "SKILL_LEVEL_UP", "timestamp": 303_100, "participantId": 1, "skillSlot": 4,
             "levelUpType": "NORMAL"},
            {"type": "ITEM_UNDO", "timestamp": 304_000, "participantId": 4, "beforeId": 1056, "afterId": 0}]}]}}
    if layout == "folder":
        d = tmp / "TST_1"
        d.mkdir(parents=True)
        mp, tp = d / "match.json", d / "timeline.json"
    elif layout == "prefixed":
        tmp.mkdir(parents=True, exist_ok=True)
        mp, tp = tmp / "TST_1.match.json", tmp / "TST_1.timeline.json"
    else:
        tmp.mkdir(parents=True, exist_ok=True)
        mp, tp = tmp / "match.json", tmp / "timeline.json"
    mp.write_text(json.dumps(match), encoding="utf-8")
    tp.write_text(json.dumps(timeline), encoding="utf-8")
    return tmp


def _toy_map() -> dict:
    """A recording of the synthetic game: 1x from game 90 s, a rewind, the same moments again at 0.25x."""
    return {"schema": clock.SCHEMA, "file": "toy.mp4", "fps": 60, "passes": [
        {"id": "p0130_1x", "file": [10.0, 40.0], "speed": 1.0, "offset": 80.0, "tol_s": 0.017},
        {"id": "p0138_0.25x", "file": [40.0, 100.0], "speed": 0.25, "offset": 88.0, "tol_s": 0.004}]}


# =================================================================================================
# riot: time, typed records, loading
# =================================================================================================

def test_mmss_round_trips():
    assert riot.mmss(1442.051) == "24:02.051"
    assert riot.mmss(1442.051, ms=False) == "24:02"
    assert riot.mmss(59.9996) == "1:00.000"
    assert riot.mmss(3725.5) == "1:02:05.500"
    assert riot.mmss(-5) == "-0:05.000"
    for s in ("24:02.051", "0:00.000", "1:02:05.500", "-0:05.000"):
        assert riot.mmss(riot.parse_mmss(s)) == s
    assert riot.parse_mmss("26:14.88") == pytest.approx(1574.88)
    assert riot.parse_mmss("75") == 75.0 and riot.parse_mmss(12.5) == 12.5
    with pytest.raises(ValueError, match="not a game time"):
        riot.parse_mmss("soon")
    assert riot.parse_mmss("75:00") == 4500.0                        # minutes run on when no hours are written
    for typo in ("24:75", "1:60:00", "0:60.5"):
        with pytest.raises(ValueError, match="under 60"):
            riot.parse_mmss(typo)


def test_match_types_events_and_reports_role_bound_boots(tmp_path):
    m = riot.load("TST_1", root=_synthetic(tmp_path / "cache"))
    assert m.patch == "16.20" and m.duration_s == 600.0
    draven = m.player("draven")
    assert draven.role_bound_item == 3006 and 3006 not in draven.items and draven.build == (6697, 3031, 3006)
    assert m.player("Player 3").champion == "MissFortune" and m.player("player 3#tst").pid == 3
    assert m.player(4).champion == "Swain"
    with pytest.raises(KeyError):
        m.player("nobody")
    assert all(r["agree"] for r in m.kda_check())
    kinds = [e.kind for e in m.events()]
    assert kinds.count("kill") == 3 and kinds.count("objective") == 2 and "level" in kinds and "skill" in kinds
    k = m.kills()[0]
    assert isinstance(k, riot.Kill) and (k.game_t, k.pid, k.victim, k.assists) == (100.0, 1, 3, (2,))
    obj = [e for e in m.events(["objective"])]
    assert obj[0].what == "DRAGON/WATER_DRAGON" and obj[0].team == 100
    assert obj[1].what == "TOWER_BUILDING/OUTER_TURRET" and obj[1].team == 100      # Riot names the LOSING team
    undo = [e for e in m.events(["item"]) if e.action == "UNDO"][0]
    assert undo.item_id == 1056 and undo.pid == 4
    assert [e.game_t for e in m.events(["kill"], pid=2)] == [100.0, 112.25]        # assists count as involvement
    assert m.champion(0) == "" and m.frames()[0]["by_pid"][1]["pos"] == (1, 2)


def test_load_finds_every_cache_layout_and_refuses_politely(tmp_path):
    for layout in ("folder", "prefixed", "plain"):
        root = _synthetic(tmp_path / layout, layout=layout)
        assert riot.load("TST_1", root=root).match_id == "TST_1"
    with pytest.raises(ff.MediaError, match="API key"):
        riot.load("TST_2", root=tmp_path / "plain")          # match.json is there, but for another match
    with pytest.raises(ff.MediaError, match="not cached"):
        riot.load("TST_1", root=tmp_path / "empty")


def test_item_names_come_from_a_cached_ddragon(tmp_path):
    root = _synthetic(tmp_path / "cache")
    m = riot.load("TST_1", root=root)
    assert m.item_name(3006) is None
    (root / "TST_1" / "item.json").write_text(json.dumps({"data": {"3006": {"name": "Berserker's Greaves"}}}),
                                              encoding="utf-8")
    m = riot.load("TST_1", root=root)
    assert m.item_name(3006) == "Berserker's Greaves"
    assert riot.summary(m)["players"][0]["build_names"][-1] == "Berserker's Greaves"


# =================================================================================================
# events: join, windows, csv, the house result and the CLI
# =================================================================================================

def test_join_lists_every_pass_that_shows_an_event(tmp_path):
    m = riot.load("TST_1", root=_synthetic(tmp_path / "cache"))
    rows = events.join(m, _toy_map())
    k = [r for r in rows if r["kind"] == "kill"][0]                 # game 100.0
    assert (k["who"], k["victim_champion"], k["assist_champions"]) == ("Draven", "MissFortune", ["Yuumi"])
    assert k["shows"] == [{"file_t": 20.0, "pass": "p0130_1x", "speed": 1.0},
                          {"file_t": 48.0, "pass": "p0138_0.25x", "speed": 0.25}]
    late = [r for r in rows if r["game_t"] >= 300][0]
    assert late["shows"] == []                                      # no pass shows the dragon
    assert [r["who"] for r in rows if r["game_t"] == 0.0] == [""]   # Riot's participant 0 buying an item: no one
    assert len(events.join(m, _toy_map(), kinds=["kill"])) == 3


def test_windows_follow_the_kill_and_death_rules(tmp_path):
    m = riot.load("TST_1", root=_synthetic(tmp_path / "cache"))
    rows = events.join(m, _toy_map())
    fights = events.windows(rows, cmap=_toy_map())
    assert [f["n_kills"] for f in fights] == [3, 0]                 # three kills within 12 s, then dragon + tower
    f = fights[0]
    assert f["game"] == [85.0, 117.25]                              # 15 s before the first kill, 5 s after the last
    assert f["members"] == ["Draven", "MissFortune", "Swain", "Yuumi"]
    assert f["deaths_by_team"] == {"200": 2, "100": 1}
    spans = {s["pass"]: s for s in f["file_spans"]}
    assert spans["p0130_1x"]["file"] == [10.0, 37.25]               # game 90 (pass start) to 117.25
    assert spans["p0138_0.25x"]["file"] == [40.0, 100.0] and spans["p0138_0.25x"]["covers"] == 0.465
    assert fights[1]["game"] == [270.0, 312.0] and len(fights[1]["objectives"]) == 2
    mine = events.windows(rows, player="MissFortune", match=m)      # her death gets the 40 s lead-in
    assert [fx["game"] for fx in mine] == [[60.0, 113.5]]
    assert mine[0]["n_kills"] == 2
    # Draven kills first (100.0) and dies after (108.5): his death's 40 s lead-in opens the fight at 68.5, not the
    # kill's 85.0 (the merge used to keep the first window's start)
    his = events.windows(rows, player="Draven", match=m)
    assert his[0]["game"] == [68.5, 117.25] and his[0]["n_kills"] == 3
    assert [k["game_t"] for k in his[0]["kills"]] == [100.0, 108.5, 112.25]
    assert [fx["game"] for fx in his[1:]] == [[270.0, 312.0]]
    with pytest.raises(ff.MediaError, match="no participant 'Teemo'"):
        events.windows(rows, player="Teemo", match=m)
    assert events.windows(rows, merge_gap_s=0.0, rules={"kill": (1.0, 1.0)})[0]["game"] == [99.0, 101.0]
    with pytest.raises(ff.MediaError, match="needs the match"):
        events.windows(rows, player="Draven")


def test_write_csv_for_events_and_fights(tmp_path):
    m = riot.load("TST_1", root=_synthetic(tmp_path / "cache"))
    rows = events.join(m, _toy_map())
    p = events.write_csv(rows, tmp_path / "out" / "events.csv")
    body = list(csv.reader(open(p, encoding="utf-8", newline="")))
    assert body[0][:3] == ["game_t", "mmss", "kind"] and len(body) == len(rows) + 1
    kill = [r for r in body if r[2] == "kill"][0]
    assert kill[4:6] == ["Draven", "MissFortune"] and kill[-1] == "20.000@p0130_1x; 48.000@p0138_0.25x"
    q = events.write_csv(events.windows(rows, cmap=_toy_map()), tmp_path / "out" / "fights.csv")
    head, first = list(csv.reader(open(q, encoding="utf-8", newline="")))[:2]
    assert head[0] == "id" and first[0] == "f01" and "p0130_1x@10.000-37.250" in first[-1]
    assert b"\r\n" not in Path(p).read_bytes()


def test_pin_writes_a_receipt_and_the_cli_prints_fights(tmp_path, state, capsys):
    root = _synthetic(tmp_path / "cache")
    video = tmp_path / "toy.mp4"
    video.write_bytes(b"not really a video" * 100)
    res = events.pin(video, "TST_1", root=root, cmap=_toy_map(), csv_out=tmp_path / "e.csv")
    assert res["api"] == "arsenal.media.events/v0" and res["n_events"] == 11 and res["n_shown"] == 4
    assert res["params"]["rules"]["death"] == (40.0, 5.0) and res["params"]["merge_gap_s"] == 10.0
    assert Path(res["receipt"]).is_relative_to(state) and Path(res["csv"]).is_file()
    cm_file = tmp_path / "toy.clockmap.json"
    cm_file.write_text(json.dumps(_toy_map()), encoding="utf-8")
    assert media_main.main(["events", str(video), "--match", "TST_1", "--root", str(root), "--clockmap",
                            str(cm_file), "--player", "Swain"]) == 0
    out = capsys.readouterr().out
    assert "1 fights" in out and "f01 1:12.250-1:57.250" in out      # Swain's death: 40 s before, 5 s after
    # one line on stderr, never a traceback: an unknown player, a missing video
    base = ["--match", "TST_1", "--root", str(root), "--clockmap", str(cm_file)]
    assert media_main.main(["events", str(video), *base, "--player", "Teemo"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("events: no participant 'Teemo' in TST_1") and "Traceback" not in err
    assert media_main.main(["events", str(tmp_path / "nope.mp4"), *base]) == 1
    assert capsys.readouterr().err.startswith("events: no such video")


def test_clockmap_cache_is_the_catalogs_key(tmp_path, state, monkeypatch):
    """`import` (catalog) writes <state>/clockmap/<media id>.clockmap.json; events finds it instead of rebuilding."""
    video = tmp_path / "rec.mp4"
    video.write_bytes(b"not really a video" * 100)
    cached = clock.cache_path(video)
    assert cached == state / "clockmap" / f"{events.receipt.quick_id(video)}.clockmap.json"
    cm = {**_toy_map(), "source": {"id": events.receipt.quick_id(video)}}
    cached.parent.mkdir(parents=True)
    cached.write_text(json.dumps(cm), encoding="utf-8")
    monkeypatch.setattr(clock, "clockmap", lambda *a, **k: pytest.fail("rebuilt a cached clockmap"))
    got, how = events._clockmap_for(video)
    assert how == str(cached) and got["passes"] == cm["passes"]


# =================================================================================================
# live: the Live Client Data poll and its clockmap (no network: the API is a function here)
# =================================================================================================

def test_poll_logs_game_time_and_new_events_only(tmp_path):
    calls = {"n": 0}

    def fake(path: str) -> dict:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise ConnectionRefusedError("no game yet")
        if path == "gamestats":
            return {"gameTime": 100.0 + calls["n"]}
        return {"Events": [{"EventID": 0, "EventName": "GameStart", "EventTime": 0.05},
                           {"EventID": 1, "EventName": "ChampionKill", "EventTime": 101.5, "KillerName": "A",
                            "VictimName": "B", "Assisters": ["C"]}]}

    log = live.poll(tmp_path / "live", interval=0.0, stop_after=5, get=fake)
    pairs, evs = live.read_log(log)
    assert len(pairs) == 3 and [e["event"]["EventID"] for e in evs] == [0, 1]       # each event once
    assert live.label(evs[1]["event"]) == "Kill A > B (+C)"


def test_live_clockmap_from_a_poll_log(tmp_path, state):
    rec = tmp_path / "2026-10-12 10-00-00.mp4"
    rec.write_bytes(b"x" * 4096)
    start = 1_791_900_000.0
    lines = []
    for k in range(200):                                            # 100 s of polls, game = file - 152.0
        ft = 5.0 + 0.5 * k
        gt = ft - 152.0 + (0.004 if k % 3 == 0 else 0.0)
        if ft >= 60.0:
            gt = 60.0 - 152.0 if ft < 70.0 else ft - 162.0          # paused 10 s at file 60, then running again
        lines.append(json.dumps({"wall": start + ft, "gameTime": gt}))
    lines.append(json.dumps({"wall": start + 30.0, "gameTime": -122.0,
                             "event": {"EventID": 3, "EventName": "DragonKill", "EventTime": -125.0,
                                       "DragonType": "Water", "KillerName": "A"}}))
    log = tmp_path / "poll.jsonl"
    log.write_text("\n".join(lines) + "\n{torn", encoding="utf-8")
    res = live.clockmap(log, rec, file_start=start)
    ps = res["passes"]
    assert [p["speed"] for p in ps] == [1.0, 1.0]
    assert ps[0]["offset"] == pytest.approx(-152.0, abs=0.005) and ps[1]["offset"] == pytest.approx(-162.0, abs=0.005)
    assert ps[0]["file"] == [5.0, 60.0] and ps[1]["file"][0] == 70.0
    assert res["markers"] == [{"game_t": -125.0, "file_t": 27.0, "label": "DragonKill Water by A",
                               "event": "DragonKill"}]
    assert clock.to_file(res, -100.0) == [(52.0, ps[0]["id"], 1.0)]
    out = tmp_path / "live.clockmap.json"
    assert live.cli("live", ["clockmap", str(log), str(rec), "--file-start", str(start), "--out", str(out)]) == 0
    assert [p["offset"] for p in clock.load(out)["passes"]] == [p["offset"] for p in ps]
    named, how, unc = live.recording_start(tmp_path / "2026-10-12 10-00-00.mp4")
    assert unc in (0.25, 0.5) and how
    with pytest.raises(ff.MediaError, match="OBS time stamp"):
        live.recording_start(tmp_path / "clip.mp4")


# =================================================================================================
# oracles: NA1_5658447097 and Daniel's 17-51-11 (skip when missing)
# =================================================================================================

def _oracle_match() -> riot.Match:
    root = ORACLES / "riot"
    if not (root / "match.json").is_file():
        pytest.skip(f"oracle missing: {root}")
    return riot.load(MATCH_ID, root=root)


def test_oracle_summary_agrees_with_the_timeline_and_reports_the_boots():
    m = _oracle_match()
    assert m.patch == "16.20" and m.duration_s == 1629.0
    check = m.kda_check()
    assert all(r["agree"] for r in check), [r for r in check if not r["agree"]]
    draven = m.player("Draven")
    assert (draven.kills, draven.deaths) == (31, 8)
    assert draven.role_bound_item == 3006 and 3006 in draven.build and 3006 not in draven.items
    assert len(m.kills()) == sum(p.kills for p in m.participants) == 76


@pytest.fixture(scope="module")
def cm_fights(tmp_path_factory):
    """The OCR clockmap of 17-51-11 over the 24:02 passes and the final fight (file 1550-1940 s)."""
    if not REC_1751.is_file():
        pytest.skip(f"oracle missing: {REC_1751}")
    clock._readers.clear()
    try:
        clock.get_reader("auto")
    except ff.MediaError:
        pytest.skip("no clock reader on this machine (rapidocr or `clockmap --train-templates`)")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(ff.STATE_ENV, str(tmp_path_factory.mktemp("state_events")))
        return clock.clockmap(REC_1751, hud="replay", start=1550.0, dur=390.0)


def test_join_puts_the_24_02_kill_on_the_ttk_death_frame(cm_fights):
    m = _oracle_match()
    ttk_file = ORACLES / "ttk_video_summary.json"
    if not ttk_file.is_file():
        pytest.skip(f"oracle missing: {ttk_file}")
    ttk = next(d for d in json.loads(ttk_file.read_text(encoding="utf-8")) if d["id"] == "24:02")
    row = next(r for r in events.join(m, cm_fights, kinds=["kill"])
               if abs(r["game_t"] - ttk["kill_ts"]) < 0.0005)
    assert (row["who"], row["victim_champion"]) == ("MissFortune", "Draven")
    assert [s["speed"] for s in row["shows"]] == [1.0, 0.25]
    quarter = row["shows"][1]["file_t"]
    assert abs(quarter - TTK_DEATH_FILE_T) <= 1 / 60, (quarter, TTK_DEATH_FILE_T)
    # the summary's own number: where this map puts the measured death (game 1442.054) is one frame from the join
    (death_file, _pid, _s), = [h for h in clock.to_file(cm_fights, ttk["death_t"]) if h[2] == 0.25]
    assert abs(death_file - quarter) <= 1 / 60 and ttk["death_err_ms"] <= 5


def test_final_fight_kills_land_inside_the_quarter_speed_pass(cm_fights):
    m = _oracle_match()
    ft_file = ORACLES / "fight_timeline.json"
    if not ft_file.is_file():
        pytest.skip(f"oracle missing: {ft_file}")
    ft = json.loads(ft_file.read_text(encoding="utf-8"))
    k = float(re.search(r"game = \(file \+ ([\d.]+)\)/4", ft["video_mapping"]["passA_0.25x"]).group(1))
    calibrated = re.search(r"calibrated on (.*?) score changes", ft["video_mapping"]["passA_0.25x"]).group(1)
    times = [riot.parse_mmss(t) for t in re.findall(r"\d+:\d+\.\d+", calibrated)]
    assert len(times) == 4                                          # Mord, Galio, Swain, Amumu score changes
    rows = events.join(m, cm_fights, kinds=["kill"])
    for t in times:
        row = next(r for r in rows if abs(r["game_t"] - t) < 0.006)
        (show,) = [s for s in row["shows"] if s["speed"] == 0.25]
        hand = 4 * row["game_t"] - k                               # the hand-calibrated 0.25x pass
        assert 1876.0 <= show["file_t"] <= 1931.0 and abs(show["file_t"] - hand) <= 0.05, (row["mmss"], show, hand)
