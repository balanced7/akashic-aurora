"""Independent reader for the live sheet music exports (slice LS4), Python stdlib only.

research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md section 10.3, amended by plan-amendments.md C5:

LR9a  take.musicxml parses (xml.etree); one <measure> per manifest measure length; every voice stream (notes without
      <chord/>, rests, <forward> with that voice) sums to its measure length; tie starts and stops pair on one staff and
      pitch, the stop at the tick where the start ends; <tied> notations agree with <tie>; the sounding notes after tie merge
      equal the performance notes (count and pitch multiset of the log's note-ons in the span); beam structure (ls1-rulings.md
      LS4: begin / continue / end over consecutive beamable notes of one voice, never across an unbeamed note, rest or
      forward); every measure's length equals the time signature in force, implicit="yes" only on the opening measure.
LR9b  performance.mid read here: format 0, one track, PPQ 500, tempo 500000; every logged on (velocity clamped to 1-127),
      off and CC64 crossing at t_ms - t0 ticks with 0 ms error; CC64 values in {0, 127}; the only extra note-offs are the
      manifest's end offs.
LR9c  quantized.mid: format 1, 3 tracks, PPQ 480; the note-ons on tracks 1-2 equal the MusicXML sounding notes in count and
      as a (tick / 20, pitch) multiset.
Reported: pedal marks (every <pedal> has line="yes" sign="no"; the start/change/stop sequence never changes or stops a
closed pedal and ends closed).

Reads every state/arsenal/score/**/export.json (written by arsenal/score_cli.mjs export|bench and
tests/score_export.test.mjs). Prints aggregates per group (session S-numbers, fixture counts; no ids, times or notes) and
writes them to state/arsenal/score/ls4-py-<date>.json.

  py tests/test_score_export.py              every export
  py -m pytest tests/test_score_export.py    the same as a test, skipped when there are no exports
"""
from __future__ import annotations

import datetime
import json
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCORE = REPO / "state" / "arsenal" / "score"
STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
BEAMABLE = {"eighth", "16th", "32nd", "64th", "128th"}
ORDER = {"off": 0, "pedal": 1, "on": 2}


# ------------------------------------------------------------------------------------------------ MIDI ---
def _vlq(data: bytes, p: int) -> tuple[int, int]:
    v = 0
    while True:
        b = data[p]
        p += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, p


def read_smf(data: bytes) -> dict:
    if data[:4] != b"MThd":
        raise ValueError("not a standard MIDI file")
    head_len = int.from_bytes(data[4:8], "big")
    fmt, ntracks, ppq = struct.unpack(">HHH", data[8:14])
    p = 8 + head_len
    tracks = []
    for _ in range(ntracks):
        if data[p:p + 4] != b"MTrk":
            raise ValueError("missing MTrk")
        length = int.from_bytes(data[p + 4:p + 8], "big")
        p += 8
        end, tick, status, events = p + length, 0, 0, []
        while p < end:
            delta, p = _vlq(data, p)
            tick += delta
            s = data[p]
            if s & 0x80:
                p += 1
            else:
                s = status
            if s == 0xFF:
                kind = data[p]
                n, p = _vlq(data, p + 1)
                events.append(("meta", tick, kind, data[p:p + n]))
                p += n
                if kind == 0x2F:
                    break
                continue
            if s in (0xF0, 0xF7):
                n, p = _vlq(data, p)
                p += n
                continue
            status = s
            hi, a = s & 0xF0, data[p]
            p += 1
            b = None
            if hi not in (0xC0, 0xD0):
                b = data[p]
                p += 1
            events.append(("chan", tick, hi, a, b))
        p = end
        tracks.append(events)
    return {"format": fmt, "ntracks": ntracks, "ppq": ppq, "tracks": tracks}


# ------------------------------------------------------------------------------------------- MusicXML ---
def check_musicxml(path: Path, measure_ticks: list[int], log_pitches: Counter) -> tuple[dict, list[dict]]:
    res = {"parsed": False, "error": None, "divisions": None, "measures": 0, "measures_match": False, "voices": 0,
           "voice_sum_bad": 0, "negative_cursor": 0, "tie_unmatched_start": 0, "tie_unmatched_stop": 0,
           "tie_notation_mismatch": 0, "sounding": 0, "pitch_diff": 0, "beams": 0, "beam_bad": 0, "time_bad": 0, "implicit_mid": 0,
           "pedal": {"start": 0, "change": 0, "stop": 0, "bad_attrs": 0, "sequence_bad": 0}}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        res["error"] = str(e)
        return res, []
    res["parsed"] = True
    part = root.find("part")
    measures = part.findall("measure") if part is not None else []
    res["measures"] = len(measures)
    res["measures_match"] = len(measures) == len(measure_ticks)
    offset, open_chains, sounding, pedal_open, cur_time = 0, {}, [], False, None
    for i, m in enumerate(measures):
        cursor, last_start, sums, beam_open = 0, 0, Counter(), {}
        implicit = m.get("implicit") == "yes"
        for el in m:
            if el.tag == "attributes":
                d = el.findtext("divisions")
                if d is not None:
                    res["divisions"] = int(d)
                t = el.find("time")
                if t is not None:
                    cur_time = (int(t.findtext("beats")), int(t.findtext("beat-type")))
            elif el.tag == "backup":
                cursor -= int(el.findtext("duration"))
                if cursor < 0:
                    res["negative_cursor"] += 1
            elif el.tag == "forward":
                dur = int(el.findtext("duration"))
                v = el.findtext("voice")
                if v is not None:
                    sums[v] += dur
                    if beam_open.get(v):
                        res["beam_bad"] += 1
                        beam_open[v] = False
                cursor += dur
            elif el.tag == "direction":
                for ped in el.iter("pedal"):
                    kind = ped.get("type")
                    if ped.get("line") != "yes" or ped.get("sign") != "no":
                        res["pedal"]["bad_attrs"] += 1
                    if kind in res["pedal"]:
                        res["pedal"][kind] += 1
                    if kind == "start":
                        if pedal_open:
                            res["pedal"]["sequence_bad"] += 1
                        pedal_open = True
                    elif kind in ("change", "stop"):
                        if not pedal_open:
                            res["pedal"]["sequence_bad"] += 1
                        pedal_open = kind == "change"
            elif el.tag == "note":
                if el.find("grace") is not None:
                    continue
                dur = int(el.findtext("duration"))
                voice = el.findtext("voice") or "1"
                if el.find("chord") is None:
                    # beam structure (ls1-rulings.md LS4): begin / continue / end over consecutive notes of the voice
                    bm = next((b.text for b in el.findall("beam") if b.get("number", "1") == "1"), None)
                    is_open = beam_open.get(voice, False)
                    if bm is not None and el.findtext("type") not in BEAMABLE:
                        res["beam_bad"] += 1
                    if bm == "begin":
                        res["beams"] += 1
                        res["beam_bad"] += 1 if is_open else 0
                        beam_open[voice] = True
                    elif bm == "continue":
                        res["beam_bad"] += 0 if is_open else 1
                        beam_open[voice] = True
                    elif bm == "end":
                        res["beam_bad"] += 0 if is_open else 1
                        beam_open[voice] = False
                    elif is_open:
                        res["beam_bad"] += 1
                        beam_open[voice] = False
                if el.find("chord") is not None:
                    start = last_start
                else:
                    start, last_start = cursor, cursor
                    cursor += dur
                    sums[voice] += dur
                if el.find("rest") is not None:
                    continue
                pitch = el.find("pitch")
                midi = (int(pitch.findtext("octave")) + 1) * 12 + STEP_PC[pitch.findtext("step")] + int(pitch.findtext("alter") or 0)
                staff = el.findtext("staff") or "1"
                ties = {t.get("type") for t in el.findall("tie")}
                tied = {t.get("type") for t in el.iter("tied")}
                if ties != tied:
                    res["tie_notation_mismatch"] += 1
                at, key = offset + start, (staff, midi)
                if "stop" in ties:
                    chains = open_chains.get(key, [])
                    hit = next((c for c in chains if c["end"] == at), None)
                    if hit is not None:
                        hit["end"] = at + dur
                        if "start" not in ties:
                            chains.remove(hit)
                        continue
                    res["tie_unmatched_stop"] += 1
                chain = {"tick": at, "midi": midi, "end": at + dur}
                sounding.append(chain)
                if "start" in ties:
                    open_chains.setdefault(key, []).append(chain)
        res["beam_bad"] += sum(1 for o in beam_open.values() if o)
        expect = measure_ticks[i] if i < len(measure_ticks) else None
        # short measures (ls1-rulings.md LS4): implicit only on the opening measure; every other measure's length equals
        # the time signature in force
        if implicit and i > 0:
            res["implicit_mid"] += 1
        want = cur_time[0] * 4 * res["divisions"] // cur_time[1] if cur_time and res["divisions"] else None
        if not (implicit and i == 0) and want != expect:
            res["time_bad"] += 1
        for s in sums.values():
            res["voices"] += 1
            if s != expect:
                res["voice_sum_bad"] += 1
        offset += expect if expect is not None else max(sums.values(), default=0)
    if pedal_open:
        res["pedal"]["sequence_bad"] += 1
    res["tie_unmatched_start"] = sum(len(c) for c in open_chains.values())
    res["sounding"] = len(sounding)
    got = Counter(c["midi"] for c in sounding)
    res["pitch_diff"] = sum(((got - log_pitches) + (log_pitches - got)).values())
    return res, sounding


def load_events(manifest_path: Path, manifest: dict) -> list[dict]:
    ref = manifest.get("events") or {}
    base = REPO if ref.get("base") == "repo" else manifest_path.parent
    out = []
    with open(base / ref["path"], encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    span = (manifest.get("options") or {}).get("span")
    if span:
        lo, hi = span["from_ms"], span.get("to_ms")
        out = [e for e in out if "t_ms" in e and e["t_ms"] >= lo and (hi is None or e["t_ms"] <= hi)]
    return out


def check_export(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    d = manifest_path.parent
    events = load_events(manifest_path, manifest)
    t0 = manifest.get("t0_ms") or 0
    ons = [e for e in events if e.get("kind") == "on"]

    # LR9a
    xml, sounding = check_musicxml(d / "take.musicxml", manifest["measureTicks"], Counter(e["note"] for e in ons))
    lr9a = dict(xml, log_ons=len(ons))
    lr9a["pass"] = (xml["parsed"] and xml["divisions"] == 24 and xml["measures_match"] and xml["voice_sum_bad"] == 0
                    and xml["negative_cursor"] == 0 and xml["tie_unmatched_start"] == 0 and xml["tie_unmatched_stop"] == 0
                    and xml["tie_notation_mismatch"] == 0 and xml["sounding"] == len(ons) and xml["pitch_diff"] == 0
                    and xml["beam_bad"] == 0 and xml["time_bad"] == 0 and xml["implicit_mid"] == 0)

    # LR9b
    want_on, want_off, want_cc, rounded, down = Counter(), Counter(), Counter(), 0, False
    logged = sorted(((i, e) for i, e in enumerate(events) if e.get("kind") in ORDER), key=lambda x: (x[1]["t_ms"], ORDER[x[1]["kind"]], x[0]))
    for _, e in logged:
        t = e["t_ms"] - t0
        if t != int(t):
            rounded += 1
        tick = int(round(t))
        if e["kind"] == "on":
            want_on[(tick, e["note"], max(1, min(127, int(round(e.get("vel", 64))))))] += 1
        elif e["kind"] == "off":
            want_off[(tick, e["note"])] += 1
        elif bool(e.get("down")) != down:
            down = bool(e.get("down"))
            want_cc[(tick, 127 if down else 0)] += 1
    perf = read_smf((d / "performance.mid").read_bytes())
    track = perf["tracks"][0] if perf["tracks"] else []
    got_on, got_off, got_cc, tempo = Counter(), Counter(), Counter(), None
    for ev in track:
        if ev[0] == "meta":
            if ev[2] == 0x51 and tempo is None:
                tempo = int.from_bytes(ev[3], "big")
            continue
        _, tick, hi, a, b = ev
        if hi == 0x90 and b > 0:
            got_on[(tick, a, b)] += 1
        elif hi == 0x80 or (hi == 0x90 and b == 0):
            got_off[(tick, a)] += 1
        elif hi == 0xB0 and a == 64:
            got_cc[(tick, b)] += 1
    end_offs = ((manifest.get("stats") or {}).get("performance") or {}).get("endOffs", 0)
    lr9b = {"format": perf["format"], "ntracks": perf["ntracks"], "ppq": perf["ppq"], "tempo": tempo,
            "ons": sum(got_on.values()), "ons_diff": sum(((got_on - want_on) + (want_on - got_on)).values()),
            "offs": sum(got_off.values()), "offs_missing": sum((want_off - got_off).values()), "offs_extra": sum((got_off - want_off).values()),
            "end_offs": end_offs, "cc64": sum(got_cc.values()), "cc_diff": sum(((got_cc - want_cc) + (want_cc - got_cc)).values()),
            "cc_bad_values": sum(n for (_, v), n in got_cc.items() if v not in (0, 127)), "rounded_times": rounded}
    lr9b["pass"] = (perf["format"] == 0 and perf["ntracks"] == 1 and perf["ppq"] == 500 and tempo == 500000 and lr9b["ons_diff"] == 0
                    and lr9b["offs_missing"] == 0 and lr9b["offs_extra"] == end_offs and lr9b["cc_diff"] == 0
                    and lr9b["cc_bad_values"] == 0 and rounded == 0)

    # LR9c
    quant = read_smf((d / "quantized.mid").read_bytes())
    q_notes = [(ev[1], ev[3]) for tr in quant["tracks"][1:3] for ev in tr if ev[0] == "chan" and ev[2] == 0x90 and ev[4] > 0]
    off_grid = sum(1 for t, _ in q_notes if t % 20)
    got_q = Counter((t // 20, a) for t, a in q_notes)
    want_q = Counter((c["tick"], c["midi"]) for c in sounding)
    lr9c = {"format": quant["format"], "ntracks": quant["ntracks"], "ppq": quant["ppq"], "notes": len(q_notes), "sounding": len(sounding),
            "off_grid": off_grid, "tick_pitch_diff": sum(((got_q - want_q) + (want_q - got_q)).values())}
    lr9c["pass"] = (quant["format"] == 1 and quant["ntracks"] == 3 and quant["ppq"] == 480 and len(q_notes) == len(sounding)
                    and off_grid == 0 and lr9c["tick_pitch_diff"] == 0)
    return {"label": manifest.get("label"), "group": manifest.get("group") or "cli", "lr9a": lr9a, "lr9b": lr9b, "lr9c": lr9c}


def run(manifests: list[Path], write: bool = True) -> dict:
    groups: dict[str, dict] = {}
    for mp in manifests:
        try:
            r = check_export(mp)
        except Exception as e:  # a missing or unreadable file fails all three receipts for that export
            r = {"label": None, "group": "unreadable", "error": f"{type(e).__name__}: {e}",
                 "lr9a": {"pass": False}, "lr9b": {"pass": False}, "lr9c": {"pass": False}}
        g = groups.setdefault(r["group"], {"exports": 0, "failed": {"LR9a": [], "LR9b": [], "LR9c": []},
                                           "sounding": 0, "log_ons": 0, "voices": 0, "ties_unmatched": 0,
                                           "midi_ons": 0, "midi_offs": 0, "cc64": 0, "quantized_notes": 0,
                                           "pedal": Counter()})
        g["exports"] += 1
        for key, name in (("lr9a", "LR9a"), ("lr9b", "LR9b"), ("lr9c", "LR9c")):
            if not r[key].get("pass"):
                g["failed"][name].append(r["label"] if r["group"] in ("sessions", "cli") else "fixture")
        a, b, c = r["lr9a"], r["lr9b"], r["lr9c"]
        g["sounding"] += a.get("sounding", 0)
        g["log_ons"] += a.get("log_ons", 0)
        g["voices"] += a.get("voices", 0)
        g["ties_unmatched"] += a.get("tie_unmatched_start", 0) + a.get("tie_unmatched_stop", 0)
        g["midi_ons"] += b.get("ons", 0)
        g["midi_offs"] += b.get("offs", 0)
        g["cc64"] += b.get("cc64", 0)
        g["quantized_notes"] += c.get("notes", 0)
        g["pedal"].update(a.get("pedal", {}))
    for g in groups.values():
        g["pedal"] = dict(g["pedal"])
        for name in ("LR9a", "LR9b", "LR9c"):
            g[name] = {"pass": not g["failed"][name], "failed": len(g["failed"][name]),
                       "failed_labels": sorted(set(x for x in g["failed"][name] if x))}
        del g["failed"]
    summary = {"date": datetime.date.today().isoformat(), "slice": "LS4", "reader": "tests/test_score_export.py (Python stdlib)", "groups": groups}
    if write:
        SCORE.mkdir(parents=True, exist_ok=True)
        (SCORE / f"ls4-py-{summary['date']}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def _manifests() -> list[Path]:
    return sorted(SCORE.rglob("export.json")) if SCORE.exists() else []


def test_lr9_exports():
    manifests = _manifests()
    if not manifests:
        import pytest
        pytest.skip("no exports under state/arsenal/score")
    summary = run(manifests, write=False)
    for name, g in summary["groups"].items():
        assert g["LR9a"]["pass"] and g["LR9b"]["pass"] and g["LR9c"]["pass"], (name, g["LR9a"], g["LR9b"], g["LR9c"])


def main() -> int:
    manifests = _manifests()
    if not manifests:
        print("no exports under state/arsenal/score (run node arsenal/score_cli.mjs bench or node tests/score_export.test.mjs)")
        return 0
    summary = run(manifests)
    ok = True
    for name, g in sorted(summary["groups"].items()):
        ok = ok and g["LR9a"]["pass"] and g["LR9b"]["pass"] and g["LR9c"]["pass"]
        print(f"{name}: {g['exports']} exports; LR9a {'pass' if g['LR9a']['pass'] else 'FAIL'} ({g['LR9a']['failed']} failed {g['LR9a']['failed_labels']}), "
              f"LR9b {'pass' if g['LR9b']['pass'] else 'FAIL'} ({g['LR9b']['failed']} failed {g['LR9b']['failed_labels']}), "
              f"LR9c {'pass' if g['LR9c']['pass'] else 'FAIL'} ({g['LR9c']['failed']} failed {g['LR9c']['failed_labels']})")
        print(f"  sounding {g['sounding']} = log note-ons {g['log_ons']}; voices checked {g['voices']}; unmatched ties {g['ties_unmatched']}; "
              f"performance.mid ons {g['midi_ons']} offs {g['midi_offs']} cc64 {g['cc64']}; quantized notes {g['quantized_notes']}; pedal {g['pedal']}")
    print(f"written to state/arsenal/score/ls4-py-{summary['date']}.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
