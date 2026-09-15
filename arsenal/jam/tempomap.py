"""The jam tempo map: bar <-> epoch <-> pass <-> slot, the landing rule and the hand-off time (jam-spec 9.1, 9.3, 9.4).

The Python twin of arsenal/web/piano/tempomap.js. Every function here has a camelCase twin there that does the same
arithmetic in the same order, and both run tests/fixtures/jam/tempomap_cases.json (tests/test_arsenal_jam_schemas.py,
tests/jam_tempomap.test.mjs), agreeing with it to 0.001 ms.

A run's segments are [{from_bar, bpm, epoch_ms, def_version, def_from_bar}] in the meter m = beats_per_bar, ordered by
from_bar. The first segment starts the count-in at bar -count_in (bar -1 for a one-bar count-in); bar 0 is the loop's
first downbeat.

  bar_ms(bpm, m)      = m * 60000 / bpm
  t_epoch(bar, x)     = s.epoch_ms + (bar - s.from_bar) * bar_ms(s.bpm, m) + x * 60000 / s.bpm   s = segment_at(bar)
  new segment at B    = {from_bar: B, bpm: new, epoch_ms: t_epoch(B) under the old segment}     (float, never re-rounded)
  pass(bar)           = floor((bar - s.def_from_bar) * m / cycle_beats)
  cycle_beat(bar, x)  = ((bar - s.def_from_bar) * m + x) mod cycle_beats      (floor mod: never negative)
  slot                = the last slot with at_beat <= cycle_beat; None while counting in (bar < def_from_bar)

Epoch -> position (DATA 6.3): s = the last segment with epoch_ms <= E; beats = (E - s.epoch_ms) * s.bpm / 60000;
bar = s.from_bar + floor((beats + EPS_BEATS) / m). Bars and epochs before the first segment extrapolate it.

Tolerances: an epoch in ms near 1.9e12 is a double with a resolution of about 0.24 microseconds, so two instants closer
than EPS_MS (1 microsecond) are the same instant, and a position within EPS_BEATS (1e-5 beat: 20 microseconds at 30
bpm, 2.5 at 240) before a bar, beat or slot line is on that line. Both twins and the fixture's oracle use these values.

A def here is anything with {cycle_beats, slots: [{at_beat, beats}, ...]} (the arsenal.jam.def/v0 fields these
functions read). `defs` is one def, used for every def_version, or a mapping def_version -> def (int or str keys).

Pure: nothing here reads a clock. Page time is perf = epoch - offset; session time is t_ms = perf - log.t0_perf_ms.
"""
from __future__ import annotations

import math
from typing import Dict, List, Mapping, Optional, Sequence

EPS_BEATS = 1e-5
EPS_MS = 1e-3
CHANGE_LEAD_MS = 250.0     # a change lands on the first line at least 1 beat + 250 ms after the server has it (9.4, C3)
HANDOFF_MARGIN_MS = 150.0  # the page hands bar n to the player 1 beat + 150 ms before it (9.3)
AT_LINES = ("now", "beat", "bar", "pass")
_MAX_STEPS = 100000


class TempoMapError(ValueError):
    """The map cannot answer: no segments, a bad meter or def, or a change placed before the last segment."""


def beat_ms(bpm: float) -> float:
    return 60000 / bpm


def bar_ms(bpm: float, beats_per_bar: int) -> float:
    return beats_per_bar * 60000 / bpm


def _check(segments, beats_per_bar) -> None:
    if isinstance(segments, (str, bytes)) or not isinstance(segments, Sequence) or not segments:
        raise TempoMapError("a tempo map needs at least one segment")
    if isinstance(beats_per_bar, bool) or not isinstance(beats_per_bar, int) or beats_per_bar < 1:
        raise TempoMapError(f"beats_per_bar must be a positive integer (got {beats_per_bar!r})")


def segment_at(segments: Sequence[dict], bar: int) -> dict:
    """The last segment with from_bar <= bar (the first segment for a bar before it)."""
    chosen = segments[0]
    for s in segments:
        if s["from_bar"] <= bar:
            chosen = s
        else:
            break
    return chosen


def segment_at_epoch(segments: Sequence[dict], epoch_ms: float) -> dict:
    """The last segment with epoch_ms <= E (within EPS_MS; the first segment for a time before it)."""
    chosen = segments[0]
    for s in segments:
        if s["epoch_ms"] <= epoch_ms + EPS_MS:
            chosen = s
        else:
            break
    return chosen


def t_epoch(segments: Sequence[dict], beats_per_bar: int, bar: int, beat: float = 0) -> float:
    """The epoch ms of beat position `beat` inside bar `bar`."""
    _check(segments, beats_per_bar)
    s = segment_at(segments, bar)
    return s["epoch_ms"] + (bar - s["from_bar"]) * bar_ms(s["bpm"], beats_per_bar) + beat * 60000 / s["bpm"]


def bar_at(segments: Sequence[dict], beats_per_bar: int, epoch_ms: float) -> Dict:
    """{bar, beat}: the bar sounding at epoch_ms and the beat position inside it (0 <= beat < beats_per_bar)."""
    _check(segments, beats_per_bar)
    s = segment_at_epoch(segments, epoch_ms)
    beats = (epoch_ms - s["epoch_ms"]) * s["bpm"] / 60000
    k = math.floor((beats + EPS_BEATS) / beats_per_bar)
    beat = beats - k * beats_per_bar
    if beat < 0:
        beat = 0.0
    return {"bar": s["from_bar"] + k, "beat": beat}


def _def_for(defs, version) -> Mapping:
    if isinstance(defs, Mapping) and "cycle_beats" in defs:
        return defs
    if isinstance(defs, Mapping):
        found = defs.get(version)
        if found is None:
            found = defs.get(str(version))
        if found is not None:
            return found
        raise TempoMapError(f"no def for def_version {version}")
    raise TempoMapError("defs must be a def ({cycle_beats, slots}) or a mapping def_version -> def")


def _cycle(d: Mapping) -> float:
    c = d.get("cycle_beats")
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not c > 0:
        raise TempoMapError(f"cycle_beats must be a positive number (got {c!r})")
    return c


def pass_of(segments: Sequence[dict], beats_per_bar: int, bar: int, defs) -> int:
    """The pass bar `bar` belongs to: 0 for the first pass of its def, negative while counting in."""
    _check(segments, beats_per_bar)
    s = segment_at(segments, bar)
    c = _cycle(_def_for(defs, s["def_version"]))
    return math.floor((bar - s["def_from_bar"]) * beats_per_bar / c)


def cycle_beat(segments: Sequence[dict], beats_per_bar: int, bar: int, beat: float, defs) -> float:
    """The beat position inside the def's cycle, 0 <= cycle_beat < cycle_beats."""
    _check(segments, beats_per_bar)
    s = segment_at(segments, bar)
    c = _cycle(_def_for(defs, s["def_version"]))
    v = (bar - s["def_from_bar"]) * beats_per_bar + beat
    r = v - math.floor(v / c) * c
    if r >= c:
        r = 0.0
    return r


def slot_at(slots: Sequence[dict], cycle_beat_value: float) -> Optional[int]:
    """The index of the last slot with at_beat <= cycle_beat (slots are ordered by at_beat), or None before the first."""
    found = None
    for i, sl in enumerate(slots):
        if sl["at_beat"] <= cycle_beat_value + EPS_BEATS:
            found = i
        else:
            break
    return found


def position(segments: Sequence[dict], beats_per_bar: int, epoch_ms: float, defs) -> Dict:
    """Everything the strip and jam status show for one instant: {bar, beat, pass, cycle_beat, slot, rest,
    counting_in, def_version, bpm}. rest is true in a rest gap, before the first slot, and while counting in."""
    at = bar_at(segments, beats_per_bar, epoch_ms)
    bar, beat = at["bar"], at["beat"]
    s = segment_at(segments, bar)
    d = _def_for(defs, s["def_version"])
    c = _cycle(d)
    p = math.floor((bar - s["def_from_bar"]) * beats_per_bar / c)
    cb = cycle_beat(segments, beats_per_bar, bar, beat, defs)
    counting_in = bar < s["def_from_bar"]
    slots = d.get("slots") or []
    slot = None if counting_in else slot_at(slots, cb)
    rest = True if slot is None else cb + EPS_BEATS >= slots[slot]["at_beat"] + slots[slot]["beats"]
    return {"bar": bar, "beat": beat, "pass": p, "cycle_beat": cb, "slot": slot, "rest": rest,
            "counting_in": counting_in, "def_version": s["def_version"], "bpm": s["bpm"]}


def first_segment(start_epoch_ms: float, bpm: float, count_in: int = 1, def_version: int = 1) -> Dict:
    """A run's first segment: the count-in starts at start_epoch_ms, so bar 0 is count_in bars later (9.2)."""
    return {"from_bar": -count_in, "bpm": bpm, "epoch_ms": start_epoch_ms, "def_version": def_version,
            "def_from_bar": 0}


def add_segment(segments: Sequence[dict], beats_per_bar: int, bar: int, bpm: Optional[float] = None,
                def_version: Optional[int] = None, def_from_bar: Optional[int] = None) -> List[dict]:
    """A new list with a change at bar `bar`: its epoch is t_epoch(bar) under the segment in effect there. Fields left
    None keep the last segment's; a new def_version starts its cycle at `bar` unless def_from_bar says otherwise. A
    change on the last segment's own bar replaces that segment (same epoch). The input list is not modified."""
    _check(segments, beats_per_bar)
    last = segments[-1]
    if bar < last["from_bar"]:
        raise TempoMapError(f"a change at bar {bar} is before the last segment's bar {last['from_bar']}")
    version = last["def_version"] if def_version is None else def_version
    if def_from_bar is None:
        def_from_bar = last["def_from_bar"] if version == last["def_version"] else bar
    new = {"from_bar": bar, "bpm": last["bpm"] if bpm is None else bpm,
           "epoch_ms": t_epoch(segments, beats_per_bar, bar), "def_version": version, "def_from_bar": def_from_bar}
    out = [dict(s) for s in segments]
    if bar == last["from_bar"]:
        out[-1] = new
    else:
        out.append(new)
    return out


def _pass_top(segments: Sequence[dict], beats_per_bar: int, bar: int, defs) -> bool:
    s = segment_at(segments, bar)
    if bar < s["def_from_bar"]:
        return False
    c = _cycle(_def_for(defs, s["def_version"]))
    return ((bar - s["def_from_bar"]) * beats_per_bar) % c == 0


def next_line(segments: Sequence[dict], beats_per_bar: int, received_epoch_ms: float, at: str = "bar", defs=None,
              lead_ms: float = CHANGE_LEAD_MS) -> Dict:
    """The landing rule (C3, 9.4): {bar, beat, epoch_ms} where a change the server received at received_epoch_ms
    takes effect. `now`: at once. `beat`, `bar`, `pass`: the first beat line, bar line or pass top (needs defs) at least
    one beat, at the tempo sounding on receipt, plus lead_ms after it."""
    if at not in AT_LINES:
        raise TempoMapError(f"at must be one of {', '.join(AT_LINES)} (got {at!r})")
    pos = bar_at(segments, beats_per_bar, received_epoch_ms)
    if at == "now":
        return {"bar": pos["bar"], "beat": pos["beat"], "epoch_ms": received_epoch_ms}
    if at == "pass" and defs is None:
        raise TempoMapError("at pass needs the def (its cycle_beats)")
    need = 60000 / segment_at_epoch(segments, received_epoch_ms)["bpm"] + lead_ms
    bar = pos["bar"]
    if at == "beat":
        k = math.floor(pos["beat"])
        for _ in range(_MAX_STEPS):
            e = t_epoch(segments, beats_per_bar, bar, k)
            if e - received_epoch_ms >= need - EPS_MS:
                return {"bar": bar, "beat": k, "epoch_ms": e}
            k += 1
            if k >= beats_per_bar:
                k = 0
                bar += 1
    else:
        for _ in range(_MAX_STEPS):
            e = t_epoch(segments, beats_per_bar, bar)
            if e - received_epoch_ms >= need - EPS_MS and (at == "bar" or _pass_top(segments, beats_per_bar, bar, defs)):
                return {"bar": bar, "beat": 0, "epoch_ms": e}
            bar += 1
    raise TempoMapError(f"no {at} line within {_MAX_STEPS} steps")


def handoff_epoch(segments: Sequence[dict], beats_per_bar: int, bar: int,
                  margin_ms: float = HANDOFF_MARGIN_MS) -> float:
    """H(n) (9.3): when bar n, with its pickups on bar n-1's last beat, goes to the player. One beat is measured at bar
    n-1's tempo, where the pickups sit, so a tempo change at bar n still leaves margin_ms before the first pickup."""
    return t_epoch(segments, beats_per_bar, bar) - (60000 / segment_at(segments, bar - 1)["bpm"] + margin_ms)


def session_t_ms(segments: Sequence[dict], beats_per_bar: int, bar: int, beat: float, anchor: Mapping) -> float:
    """Session t_ms of a bar position from one clock pair, extended by the map (11.2). At L1 the anchor is the ack:
    {bar_epoch_ms, perf_ms, t0_perf_ms: ack.log.t0_perf_ms}; at L2 t0_perf_ms comes from the session meta; at L3/L4
    pass {bar_epoch_ms: 0, perf_ms: 0, t0_perf_ms: the session's open time in epoch ms}."""
    return anchor["perf_ms"] - anchor["t0_perf_ms"] + (t_epoch(segments, beats_per_bar, bar, beat) - anchor["bar_epoch_ms"])


def perf_of(epoch_ms: float, offset_ms: float) -> float:
    """Page time of an epoch, with offset = Date.now() - performance.now() (9.1)."""
    return epoch_ms - offset_ms


def median_offset(pairs: Sequence[Sequence[float]]) -> float:
    """The page's clock offset from paired reads [[wall_ms, perf_ms], ...]: the median of wall - perf (9.1 takes 5)."""
    if not pairs:
        raise TempoMapError("median_offset needs at least one [wall_ms, perf_ms] pair")
    diffs = sorted(w - p for w, p in pairs)
    mid = len(diffs) // 2
    return diffs[mid] if len(diffs) % 2 else (diffs[mid - 1] + diffs[mid]) / 2
