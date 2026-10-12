"""arsenal.media.league.riot -- one League match's Riot record (match-v5 + its timeline), loaded once and typed.

Why it exists: match and timeline JSON was re-parsed in 165 calls by 23 agents (148 throwaway scripts), CHAMPION_KILL
by 20 of them and an mm:ss formatter by 32. One reader also fixes a wrong answer we gave: "bootless Draven". Since
the 2026 role quests, finishing the quest moves the boots out of item0..item6 into participant.roleBoundItem, so the
full build is item0..item6 PLUS roleBoundItem (Player.build).

v0 reads cached JSON only: <root>/<match_id>/{match,timeline}.json, <root>/<match_id>.{match,timeline}.json, or a
folder holding match.json + timeline.json whose metadata.matchId agrees. Fetching from Riot's API needs an API key,
which is Daniel's to enter; nothing here calls Riot. Times are game seconds (game_t) from the timeline's milliseconds.
Measured on NA1_5658447097 (patch 16.20, 1629 s, 1 MB of JSON): load 6 ms, 1009 typed events in 1 ms.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .. import ff

#: Riot event type -> our kind. Everything else is kept as kind "other" with its raw dict.
KINDS = {
    "CHAMPION_KILL": "kill", "CHAMPION_SPECIAL_KILL": "special_kill",
    "ITEM_PURCHASED": "item", "ITEM_SOLD": "item", "ITEM_DESTROYED": "item", "ITEM_UNDO": "item",
    "WARD_PLACED": "ward", "WARD_KILL": "ward",
    "ELITE_MONSTER_KILL": "objective", "BUILDING_KILL": "objective", "TURRET_PLATE_DESTROYED": "objective",
    "DRAGON_SOUL_GIVEN": "objective",
    "LEVEL_UP": "level", "SKILL_LEVEL_UP": "skill",
}


# =================================================================================================
# time
# =================================================================================================

def mmss(t: float, *, ms: bool = True) -> str:
    """Game seconds as the HUD writes them: 1442.051 -> '24:02.051' (ms=False -> '24:02'); past an hour 'H:MM:SS'."""
    sign = "-" if t < 0 else ""
    t = abs(float(t))
    whole = int(t)
    frac = t - whole
    if ms and round(frac, 3) >= 1.0:
        whole, frac = whole + 1, 0.0
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    head = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    return sign + head + (f".{int(round(frac * 1000)):03d}" if ms else "")


_MMSS = re.compile(r"^\s*(-)?(?:(\d+):)?(\d+):(\d{1,2}(?:\.\d+)?)\s*$")


def parse_mmss(s: Union[str, float, int]) -> float:
    """'24:02.051', '24:02', '1:02:03.5', '-0:05' or plain seconds -> game seconds."""
    if isinstance(s, (int, float)):
        return float(s)
    text = str(s).strip()
    m = _MMSS.match(text)
    if not m:
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"not a game time: {s!r} (want m:ss, m:ss.mmm, h:mm:ss or seconds)") from None
    sign, h, mi, sec = m.groups()
    if float(sec) >= 60 or (h and int(mi) >= 60):            # '24:75' is a typo, not 25:15
        raise ValueError(f"not a game time: {s!r} (seconds, and minutes after hours, stay under 60)")
    total = int(h or 0) * 3600 + int(mi) * 60 + float(sec)
    return -total if sign else total


# =================================================================================================
# typed records
# =================================================================================================

@dataclass(frozen=True)
class Player:
    pid: int
    team: int                       # 100 blue, 200 red
    champion: str
    role: str                       # teamPosition: TOP JUNGLE MIDDLE BOTTOM UTILITY
    riot_id: str                    # gameName#tagLine
    puuid: str
    kills: int
    deaths: int
    assists: int
    items: Tuple[int, ...]          # item0..item6 as Riot lists them (0 = empty)
    role_bound_item: Optional[int]  # where the boots go once the role quest is done
    win: bool

    @property
    def build(self) -> Tuple[int, ...]:
        """Every item the player ended with: item0..item6 plus roleBoundItem, empties dropped."""
        extra = (self.role_bound_item,) if self.role_bound_item else ()
        return tuple(i for i in self.items if i) + extra


@dataclass(frozen=True, kw_only=True)
class Event:
    kind: str                       # kill, special_kill, item, ward, objective, level, skill, other
    type: str                       # Riot's event type
    game_t: float
    pid: Optional[int] = None       # the participant who did it (killer, buyer, placer, ...), 0 = minion/turret
    raw: dict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, kw_only=True)
class Kill(Event):
    victim: int
    assists: Tuple[int, ...] = ()
    pos: Optional[Tuple[int, int]] = None
    bounty: int = 0
    shutdown_bounty: int = 0


@dataclass(frozen=True, kw_only=True)
class ItemEvent(Event):
    item_id: int
    action: str                     # PURCHASED, SOLD, DESTROYED, UNDO


@dataclass(frozen=True, kw_only=True)
class WardEvent(Event):
    ward_type: str
    action: str                     # PLACED, KILL


@dataclass(frozen=True, kw_only=True)
class Objective(Event):
    what: str                       # DRAGON/CHEMTECH_DRAGON, HORDE, TOWER_BUILDING/OUTER_TURRET, TURRET_PLATE, SOUL
    team: Optional[int] = None      # the team that TOOK it (Riot names the losing team on buildings and plates)
    lane: Optional[str] = None
    assists: Tuple[int, ...] = ()
    pos: Optional[Tuple[int, int]] = None


@dataclass(frozen=True, kw_only=True)
class LevelUp(Event):
    level: int


@dataclass(frozen=True, kw_only=True)
class SkillUp(Event):
    slot: int
    level_up_type: str


def _pos(e: dict) -> Optional[Tuple[int, int]]:
    p = e.get("position")
    return (int(p["x"]), int(p["y"])) if isinstance(p, dict) and "x" in p else None


def _other_team(team: Optional[int]) -> Optional[int]:
    return {100: 200, 200: 100}.get(team) if team else None


def _typed(e: dict) -> Event:
    typ = e.get("type", "")
    kind = KINDS.get(typ, "other")
    base = {"kind": kind, "type": typ, "game_t": int(e.get("timestamp", 0)) / 1000.0, "raw": e}
    if typ == "CHAMPION_KILL":
        return Kill(**base, pid=e.get("killerId"), victim=int(e["victimId"]),
                    assists=tuple(e.get("assistingParticipantIds") or ()), pos=_pos(e),
                    bounty=int(e.get("bounty") or 0), shutdown_bounty=int(e.get("shutdownBounty") or 0))
    if kind == "item":
        item = e.get("itemId") if typ != "ITEM_UNDO" else (e.get("beforeId") or e.get("afterId"))
        return ItemEvent(**base, pid=e.get("participantId"), item_id=int(item or 0), action=typ.split("_", 1)[1])
    if kind == "ward":
        return WardEvent(**base, pid=e.get("creatorId") if typ == "WARD_PLACED" else e.get("killerId"),
                         ward_type=str(e.get("wardType", "")), action=typ.split("_", 1)[1])
    if typ == "ELITE_MONSTER_KILL":
        what = "/".join(x for x in (e.get("monsterType"), e.get("monsterSubType")) if x)
        return Objective(**base, pid=e.get("killerId"), what=what, team=e.get("killerTeamId"),
                         assists=tuple(e.get("assistingParticipantIds") or ()), pos=_pos(e))
    if typ in ("BUILDING_KILL", "TURRET_PLATE_DESTROYED"):
        what = "/".join(x for x in (e.get("buildingType"), e.get("towerType")) if x) or "TURRET_PLATE"
        return Objective(**base, pid=e.get("killerId"), what=what, team=_other_team(e.get("teamId")),
                         lane=e.get("laneType"), assists=tuple(e.get("assistingParticipantIds") or ()), pos=_pos(e))
    if typ == "DRAGON_SOUL_GIVEN":
        return Objective(**base, what=f"SOUL/{e.get('name', '')}", team=e.get("teamId") or None)
    if typ == "LEVEL_UP":
        return LevelUp(**base, pid=e.get("participantId"), level=int(e.get("level", 0)))
    if typ == "SKILL_LEVEL_UP":
        return SkillUp(**base, pid=e.get("participantId"), slot=int(e.get("skillSlot", 0)),
                       level_up_type=str(e.get("levelUpType", "")))
    if typ == "CHAMPION_SPECIAL_KILL":
        return Event(**base, pid=e.get("killerId"))
    return Event(**base, pid=e.get("participantId") or e.get("killerId"))


# =================================================================================================
# the match
# =================================================================================================

class Match:
    """match-v5 + timeline of one game; participants, per-minute frames and typed events."""

    def __init__(self, match: dict, timeline: dict, *, source: Optional[dict] = None,
                 items: Optional[Dict[str, dict]] = None):
        self.match = match
        self.timeline = timeline
        self.info = match["info"]
        self.match_id = match["metadata"]["matchId"]
        self.source = source or {}
        self._items = items or {}
        tl_id = (timeline.get("metadata") or {}).get("matchId")
        if tl_id and tl_id != self.match_id:
            raise ff.MediaError(f"timeline is for {tl_id}, match is {self.match_id}")
        self.participants: List[Player] = [self._player(p) for p in self.info["participants"]]
        self._events: Optional[List[Event]] = None

    @staticmethod
    def _player(p: dict) -> Player:
        rid = f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}".strip("#")
        return Player(pid=int(p["participantId"]), team=int(p["teamId"]), champion=str(p["championName"]),
                      role=str(p.get("teamPosition") or p.get("individualPosition") or ""), riot_id=rid,
                      puuid=str(p.get("puuid", "")), kills=int(p["kills"]), deaths=int(p["deaths"]),
                      assists=int(p["assists"]), items=tuple(int(p.get(f"item{i}", 0) or 0) for i in range(7)),
                      role_bound_item=int(p["roleBoundItem"]) if p.get("roleBoundItem") else None,
                      win=bool(p.get("win")))

    @property
    def duration_s(self) -> float:
        return float(self.info.get("gameDuration", 0))

    @property
    def patch(self) -> str:
        """'16.20' from gameVersion '16.20.824.8524'."""
        return ".".join(str(self.info.get("gameVersion", "")).split(".")[:2])

    def player(self, who: Union[int, str]) -> Player:
        """By participant id, champion name, riot id (name or name#tag) or puuid; case and spaces ignored."""
        if isinstance(who, int) or (isinstance(who, str) and who.isdigit()):
            for p in self.participants:
                if p.pid == int(who):
                    return p
        key = str(who).replace(" ", "").lower()
        for p in self.participants:
            names = {p.champion.lower(), p.riot_id.replace(" ", "").lower(),
                     p.riot_id.split("#")[0].replace(" ", "").lower(), p.puuid.lower()}
            if key in names:
                return p
        raise KeyError(f"no participant {who!r} in {self.match_id}")

    def champion(self, pid: Optional[int]) -> str:
        """The champion a participant id played; '' for no one (Riot uses 0 for minions, turrets and the game)."""
        if not pid:
            return ""
        return next((p.champion for p in self.participants if p.pid == pid), f"p{pid}")

    def item_name(self, item_id: int) -> Optional[str]:
        """The item's name from the patch's Data Dragon item.json when it was cached beside the match, else None."""
        entry = self._items.get(str(item_id))
        return entry.get("name") if entry else None

    def frames(self) -> List[dict]:
        """Per-minute state: [{game_t, by_pid: {pid: {gold, total_gold, xp, level, cs, jungle_cs, pos}}}]."""
        out = []
        for fr in self.timeline["info"]["frames"]:
            by = {}
            for k, pf in (fr.get("participantFrames") or {}).items():
                by[int(k)] = {"gold": pf.get("currentGold"), "total_gold": pf.get("totalGold"), "xp": pf.get("xp"),
                              "level": pf.get("level"), "cs": pf.get("minionsKilled"),
                              "jungle_cs": pf.get("jungleMinionsKilled"),
                              "pos": _pos(pf)}
            out.append({"game_t": int(fr.get("timestamp", 0)) / 1000.0, "by_pid": by})
        return out

    def events(self, kinds: Optional[Iterable[str]] = None, *, pid: Optional[int] = None) -> List[Event]:
        """Typed timeline events in time order; kinds filters (kill, item, ward, objective, level, skill, ...), pid
        keeps the ones a participant did, suffered (victim) or assisted."""
        if self._events is None:
            evs = [_typed(e) for fr in self.timeline["info"]["frames"] for e in fr.get("events", [])]
            self._events = sorted(evs, key=lambda e: e.game_t)
        want = set(kinds) if kinds else None
        out = []
        for e in self._events:
            if want is not None and e.kind not in want:
                continue
            if pid is not None and pid not in involved(e):
                continue
            out.append(e)
        return out

    def kills(self) -> List[Kill]:
        return [e for e in self.events(["kill"]) if isinstance(e, Kill)]

    def kda_check(self) -> List[dict]:
        """Each player's kills/deaths in the match summary against CHAMPION_KILL counts in the timeline."""
        kills = self.kills()
        out = []
        for p in self.participants:
            k = sum(1 for e in kills if e.pid == p.pid)
            d = sum(1 for e in kills if e.victim == p.pid)
            out.append({"pid": p.pid, "champion": p.champion, "summary": [p.kills, p.deaths],
                        "timeline": [k, d], "agree": (k, d) == (p.kills, p.deaths)})
        return out


def involved(e: Event) -> Tuple[int, ...]:
    """Participant ids an event involves: the actor, a kill's victim and assisters, an objective's assisters."""
    ids = [e.pid] if e.pid else []
    if isinstance(e, Kill):
        ids += [e.victim, *e.assists]
    elif isinstance(e, Objective):
        ids += list(e.assists)
    return tuple(ids)


# =================================================================================================
# loading the cache
# =================================================================================================

def default_root() -> Path:
    return ff.state_dir() / "league" / "matches"


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _candidates(match_id: str, root: Path) -> List[Tuple[Path, Path]]:
    return [(root / match_id / "match.json", root / match_id / "timeline.json"),
            (root / f"{match_id}.match.json", root / f"{match_id}.timeline.json"),
            (root / "match.json", root / "timeline.json")]


def _ddragon_items(folder: Path, patch: str) -> Dict[str, dict]:
    for p in (folder / "ddragon" / patch / "item.json", folder / "item.json", folder / "ddragon_item.json"):
        if p.is_file():
            try:
                return _read(p).get("data") or {}
            except (OSError, ValueError):
                return {}
    return {}


def load(match_id: str, *, root=None) -> Match:
    """The cached match + timeline for match_id (v0: cached JSON only, never the API)."""
    base = Path(root) if root else default_root()
    for mp, tp in _candidates(match_id, base):
        if not (mp.is_file() and tp.is_file()):
            continue
        match = _read(mp)
        if (match.get("metadata") or {}).get("matchId") != match_id:
            continue
        timeline = _read(tp)
        m = Match(match, timeline, source={"match": str(mp), "timeline": str(tp)})
        m._items = _ddragon_items(mp.parent, m.patch)
        return m
    raise ff.MediaError(f"match {match_id} is not cached under {base} (want {match_id}/match.json + timeline.json); "
                        f"v0 reads cached JSON only, fetching from Riot needs Daniel's API key")


def load_files(match_json, timeline_json) -> Match:
    """A match from two explicit files."""
    mp, tp = Path(match_json), Path(timeline_json)
    m = Match(_read(mp), _read(tp), source={"match": str(mp), "timeline": str(tp)})
    m._items = _ddragon_items(mp.parent, m.patch)
    return m


def summary(m: Match, players: Optional[Sequence[int]] = None) -> dict:
    """A compact view: match facts and each player's champion, role, K/D/A and build (roleBoundItem included)."""
    rows = []
    for p in m.participants:
        if players and p.pid not in players:
            continue
        rows.append({"pid": p.pid, "team": p.team, "champion": p.champion, "role": p.role,
                     "kda": [p.kills, p.deaths, p.assists], "items": list(p.items),
                     "role_bound_item": p.role_bound_item, "build": list(p.build),
                     "build_names": [m.item_name(i) for i in p.build] if m._items else None, "win": p.win})
    return {"match_id": m.match_id, "patch": m.patch, "duration_s": m.duration_s, "players": rows}
