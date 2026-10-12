"""arsenal.media.league.events -- Riot's events pinned to every video frame that shows them, kills grouped into fights.

Why it exists: the question is never "what happened at 24:02" alone but "show me 24:02", and in a replay study the
same second is on screen several times (a 1x pass, a rewind, a 0.25x pass). join() takes every timeline event through
a clockmap (league.clock) and lists each file time that shows it, with the pass and its speed; windows() groups kills
and objectives into fights with a lead-in and an aftermath (15 s / 5 s around a kill and 40 s / 5 s around a death,
the lol-kill-clipper windows; 30 s / 10 s around an objective), ready to clip or review.

Measured on NA1_5658447097 against 2026-10-11 17-51-11: the 24:02 MF-kills-Draven event lands 0.75 frame from the
death frame the TTK work measured in the 0.25x pass, and the four final-fight kills land 0.033 s from the hand-
calibrated 0.25x pass. join over all 1009 events takes about 10 ms once the clockmap exists.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .. import ff, receipt
from . import clock, riot

#: (lead-in s, aftermath s) in game time around each kind of anchor event.
DEFAULT_RULES: Dict[str, Tuple[float, float]] = {"kill": (15.0, 5.0), "death": (40.0, 5.0), "objective": (30.0, 10.0)}
#: Objectives big enough to anchor a fight window (plates and soul notices ride along inside one).
ANCHOR_OBJECTIVES = ("ELITE_MONSTER_KILL", "BUILDING_KILL")


def _row(m: riot.Match, e: riot.Event) -> dict:
    who = m.champion(e.pid) or ("minion/turret" if e.pid == 0 and e.kind in ("kill", "objective") else "")
    row = {"game_t": e.game_t, "mmss": riot.mmss(e.game_t), "kind": e.kind, "type": e.type, "pid": e.pid, "who": who}
    if isinstance(e, riot.Kill):
        row.update(victim=e.victim, victim_champion=m.champion(e.victim), victim_team=m.player(e.victim).team,
                   assists=list(e.assists), assist_champions=[m.champion(a) for a in e.assists],
                   pos=list(e.pos) if e.pos else None, bounty=e.bounty, shutdown_bounty=e.shutdown_bounty)
    elif isinstance(e, riot.ItemEvent):
        row.update(item_id=e.item_id, action=e.action, item_name=m.item_name(e.item_id))
    elif isinstance(e, riot.WardEvent):
        row.update(ward_type=e.ward_type, action=e.action)
    elif isinstance(e, riot.Objective):
        row.update(what=e.what, team=e.team, lane=e.lane, assists=list(e.assists),
                   assist_champions=[m.champion(a) for a in e.assists], pos=list(e.pos) if e.pos else None)
    elif isinstance(e, riot.LevelUp):
        row.update(level=e.level)
    elif isinstance(e, riot.SkillUp):
        row.update(slot=e.slot, level_up_type=e.level_up_type)
    return row


def join(match: riot.Match, cmap: dict, *, kinds: Optional[Iterable[str]] = None) -> List[dict]:
    """Every event (or only `kinds`) as a row with `shows`: each (file_t, pass, speed) where the recording shows
    its game_t. An event no pass covers has shows == []."""
    rows = []
    for e in match.events(kinds):
        row = _row(match, e)
        row["shows"] = [{"file_t": round(ft, 4), "pass": pid, "speed": s}
                        for ft, pid, s in clock.to_file(cmap, e.game_t)]
        rows.append(row)
    return rows


def _pass_game_span(p: dict) -> Tuple[float, float]:
    if p.get("game"):
        return float(p["game"][0]), float(p["game"][1])
    f0, f1 = p["file"]
    return p["speed"] * f0 + p["offset"], p["speed"] * f1 + p["offset"]


def file_spans(cmap: dict, g0: float, g1: float) -> List[dict]:
    """Where game span [g0, g1] is on screen: one entry per pass that shows any of it, clipped to the pass."""
    out = []
    for p in cmap["passes"]:
        s = p["speed"]
        if s <= 0:
            continue
        pg0, pg1 = _pass_game_span(p)
        a, b = max(g0, pg0), min(g1, pg1)
        if a >= b:
            continue
        out.append({"pass": p["id"], "speed": s,
                    "file": [round((a - p["offset"]) / s, 4), round((b - p["offset"]) / s, 4)],
                    "game": [round(a, 3), round(b, 3)], "covers": round((b - a) / (g1 - g0), 3) if g1 > g0 else 1.0})
    return sorted(out, key=lambda r: r["file"][0])


def _anchor_rule(row: dict, player: Optional[int],
                 rules: Dict[str, Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if row["kind"] == "kill":
        involved = {row.get("pid"), row.get("victim"), *row.get("assists", [])}
        if player is not None and player not in involved:
            return None
        return rules["death"] if player is not None and row.get("victim") == player else rules["kill"]
    if row["kind"] == "objective" and row["type"] in ANCHOR_OBJECTIVES:
        if player is not None and player not in {row.get("pid"), *row.get("assists", [])}:
            return None
        return rules["objective"]
    return None


def windows(evts: Sequence[dict], *, rules: Optional[Dict[str, Tuple[float, float]]] = None, merge_gap_s: float = 10.0,
            player: Union[int, str, None] = None, cmap: Optional[dict] = None,
            match: Optional[riot.Match] = None) -> List[dict]:
    """Fights: kill/objective windows (game time), taken in order of their start, merged when they overlap or sit
    within merge_gap_s (a fight starts at its earliest lead-in, whichever event owns it). With a
    player (pid, or a name when `match` is given), only events they took part in anchor a window and their own
    deaths get the longer death lead-in. With a clockmap, each fight carries the file spans that show it."""
    rules = {**DEFAULT_RULES, **(rules or {})}
    if isinstance(player, str) and not player.isdigit():
        if match is None:
            raise ff.MediaError("a player name needs the match (windows(..., match=m)); or pass the participant id")
        player = _player(match, player).pid
    pid = int(player) if player is not None else None
    spans = []
    for row in evts:
        rule = _anchor_rule(row, pid, rules)
        if rule:
            spans.append((row["game_t"] - rule[0], row["game_t"] + rule[1], row))
    # merge in order of window START: a death after a kill has the longer lead-in, so its window can start before
    # the fight it joins (Draven's 4:20 death needs 3:40, the kill before it opened the fight at 4:04)
    spans.sort(key=lambda s: (s[0], s[1], s[2]["game_t"]))
    fights: List[dict] = []
    for g0, g1, row in spans:
        if fights and g0 - fights[-1]["game"][1] <= merge_gap_s:
            f = fights[-1]
            f["game"][1] = max(f["game"][1], g1)
            f["events"].append(row)
        else:
            fights.append({"game": [g0, g1], "events": [row]})
    out = []
    for i, f in enumerate(fights, 1):
        g0, g1 = max(0.0, f["game"][0]), f["game"][1]
        f["events"].sort(key=lambda r: r["game_t"])
        kills = [r for r in f["events"] if r["kind"] == "kill"]
        objs = [r for r in f["events"] if r["kind"] == "objective"]
        names = [n for r in f["events"]
                 for n in (r.get("who"), r.get("victim_champion"), *r.get("assist_champions", []))]
        members = sorted({n for n in names if n and n != "minion/turret"})
        deaths: Dict[str, int] = {}
        for r in kills:
            deaths[str(r.get("victim_team"))] = deaths.get(str(r.get("victim_team")), 0) + 1
        fight = {"id": f"f{i:02d}", "game": [round(g0, 3), round(g1, 3)], "mmss": [riot.mmss(g0), riot.mmss(g1)],
                 "n_kills": len(kills), "deaths_by_team": deaths, "members": members,
                 "kills": [{"game_t": r["game_t"], "mmss": r["mmss"], "killer": r["who"],
                            "victim": r["victim_champion"], "assists": r.get("assist_champions", []),
                            "shows": r.get("shows", [])} for r in kills],
                 "objectives": [{"game_t": r["game_t"], "mmss": r["mmss"], "what": r.get("what"), "team": r.get("team"),
                                 "by": r["who"]} for r in objs]}
        if cmap is not None:
            fight["file_spans"] = file_spans(cmap, g0, g1)
        out.append(fight)
    return out


def write_csv(rows: Sequence[dict], out) -> str:
    """Event rows (from join) or fights (from windows) as CSV; returns the path."""
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    if rows and "n_kills" in rows[0]:
        head = ["id", "game_t0", "game_t1", "mmss0", "mmss1", "n_kills", "members", "file_spans"]
        body = [[r["id"], r["game"][0], r["game"][1], r["mmss"][0], r["mmss"][1], r["n_kills"], "; ".join(r["members"]),
                 "; ".join(f"{s['pass']}@{s['file'][0]:.3f}-{s['file'][1]:.3f}" for s in r.get("file_spans", []))]
                for r in rows]
    else:
        head = ["game_t", "mmss", "kind", "type", "who", "target", "detail", "n_shows", "file_t", "pass", "speed",
                "all_shows"]
        body = []
        for r in rows:
            target = r.get("victim_champion") or r.get("what") or ""
            detail = (r.get("item_name") or r.get("item_id") or r.get("ward_type") or r.get("level")
                      or r.get("slot") or "")
            shows = r.get("shows", [])
            first = shows[0] if shows else {}
            body.append([r["game_t"], r["mmss"], r["kind"], r["type"], r.get("who", ""), target, detail, len(shows),
                         first.get("file_t", ""), first.get("pass", ""), first.get("speed", ""),
                         "; ".join(f"{s['file_t']:.3f}@{s['pass']}" for s in shows)])
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(head)
        w.writerows(body)
    return str(p)


def _player(m: riot.Match, who: Union[int, str]) -> riot.Player:
    """Match.player, failing closed with the names it would have taken."""
    try:
        return m.player(who)
    except KeyError:
        known = ", ".join(f"{p.pid} {p.champion}" for p in m.participants)
        raise ff.MediaError(f"no participant {who!r} in {m.match_id}; give a participant id, champion or riot id "
                            f"({known})") from None


def _clockmap_for(src, cmap=None, clockmap_path=None) -> Tuple[dict, str]:
    """The clockmap to use: given, loaded, the cached OCR one for this exact file, or a fresh one (saved). The
    cache is clock.cache_path(src), the catalog's key, so a map `import` built is found here."""
    if cmap is not None:
        return cmap, "given"
    if clockmap_path:
        return clock.load(clockmap_path), str(clockmap_path)
    cached = clock.cache_path(src)
    if cached.is_file():
        try:
            c = clock.load(cached)
            if (c.get("source") or {}).get("id") == receipt.quick_id(src):
                return c, str(cached)
        except (ff.MediaError, ValueError, OSError):
            pass
    return clock.clockmap(src, out=cached), f"{cached} (built now)"


def pin(src, match_id: str, *, player: Union[int, str, None] = None, root=None, cmap: Optional[dict] = None,
        clockmap_path=None, kinds: Optional[Sequence[str]] = None, rules: Optional[dict] = None,
        merge_gap_s: float = 10.0, csv_out=None) -> dict:
    """The house result for one recording + one match: every event with the file times that show it, and fights.
    Fails closed (MediaError, one line) on a missing video, an uncached match or an unknown player."""
    if not Path(src).is_file():
        raise ff.MediaError(f"no such video: {src}")
    m = riot.load(match_id, root=root)
    pid = _player(m, player).pid if player is not None else None
    cm, cm_from = _clockmap_for(src, cmap, clockmap_path)
    rows = join(m, cm, kinds=kinds)
    fights = windows(rows, rules=rules, merge_gap_s=merge_gap_s, player=pid, cmap=cm, match=m)
    params = {"match_id": match_id, "player": player, "root": str(root) if root else str(riot.default_root()),
              "clockmap": cm_from, "kinds": list(kinds) if kinds else None,
              "rules": {**DEFAULT_RULES, **(rules or {})}, "merge_gap_s": merge_gap_s,
              "csv": str(csv_out) if csv_out else None}
    payload = {"match_id": m.match_id, "patch": m.patch, "duration_s": m.duration_s,
               "n_events": len(rows), "n_shown": sum(1 for r in rows if r["shows"]),
               "kda_check": m.kda_check(), "events": rows, "fights": fights}
    if csv_out:
        payload["csv"] = write_csv(rows, csv_out)
    blind = ["an event no clockmap pass covers (HUD hidden, outside the recording) has no file time",
             "Riot stamps the server's moment; the frame shows it on the next rendered frame (about 1 frame later)",
             "file times inherit the clockmap's offset tolerance (tol_s per pass)",
             "v0 reads cached match/timeline JSON only; nothing is fetched from Riot"]
    return receipt.result("events", src, params, payload, blind)


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media events",
                                 description="Riot match-v5 timeline events (kills, items, objectives) pinned to the "
                                             "video frames that show them, through the League clock map; fights")
    ap.add_argument("video")
    ap.add_argument("--match", required=True, help="match id, e.g. NA1_5658447097 (cached JSON)")
    ap.add_argument("--root", help=f"match cache folder (default {riot.default_root()})")
    ap.add_argument("--player", help="participant id, champion or riot id: only their fights, deaths get 40 s lead-in")
    ap.add_argument("--clockmap", help="a studio.clockmap.v1 file (default: the cached OCR map, else build one)")
    ap.add_argument("--kinds", help="comma list: kill,objective,item,ward,level,skill,special_kill,other")
    ap.add_argument("--csv", help="write the event rows as CSV here")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    kinds = [k.strip() for k in a.kinds.split(",")] if a.kinds else None
    res = pin(a.video, a.match, player=a.player, root=a.root, clockmap_path=a.clockmap, kinds=kinds, csv_out=a.csv)
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != "events"}, indent=1, default=str))
        return 0
    print(f"{a.match} on {Path(a.video).name}: {res['n_events']} events, {res['n_shown']} on screen, "
          f"{len(res['fights'])} fights (clockmap: {res['params']['clockmap']})")
    for f in res["fights"]:
        where = ", ".join(f"{s['pass']} {s['file'][0]:.1f}-{s['file'][1]:.1f}" for s in f.get("file_spans", [])) or "-"
        print(f"  {f['id']} {f['mmss'][0]}-{f['mmss'][1]}  {f['n_kills']} kills  file: {where}")
    if res.get("csv"):
        print(f"csv     -> {res['csv']}")
    print(f"receipt -> {res.get('receipt')}")
    return 0
