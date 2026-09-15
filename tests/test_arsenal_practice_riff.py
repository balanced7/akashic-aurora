"""Riff analysis (arsenal/practice_riff.py, jam-spec section 11 and acceptance check A11) on synthetic jams built here.

Nothing here reads Daniel's practice data: every run and session is generated in this file and dated 2030. The fixtures
under tests/fixtures/jam/riff_*/ are written by build_fixture(), and a test checks that the files on disk still match
it. To regenerate them (node is needed for the loopback fixture, which mirrors the groove bridge's own notes):

    py tests/test_arsenal_practice_riff.py --write-fixtures

The A11 jam (riff_lydian_l1): lydian-four in Eb at 66 bpm, 8 passes of 2 bars, stopped at bar 16, with an L1 ack. His
top line plants 9 D5s over the Ab chord (its #11), one held rub, one passing note, three slide-ins, two outside notes,
five anticipations, eight two-bar phrases (six with pickups), per-pass velocity medians 40 44 48 52 56 52 48 44, and
the pedal down for 80% of every bar. Its twins: riff_lydian_d4 (D at about 4% of the weight over the Ab chord),
riff_lydian_loopback (Claude's notes mirrored into the log 2-9 ms late) and riff_lydian_buffered (a buffered session
with no opened_at_client and no L1 ack).
"""
import copy
import functools
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import nashville  # noqa: E402
from arsenal import practice as pr  # noqa: E402
from arsenal import practice_riff as riff  # noqa: E402
from arsenal.jam import RIFF_API  # noqa: E402
from arsenal.jam import schemas  # noqa: E402
from arsenal.jam import tempomap as tm  # noqa: E402
from arsenal.performance import PerformanceStore  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "jam"
J0_RUN = FIX / "run_loop_l1"
BRIDGE = ROOT / "arsenal" / "groove_bridge.mjs"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run arsenal/groove_bridge.mjs")

BPM, M = 66, 4
BEAT = 60000 / BPM
RUN_ID = "20300101-010019-7a11c0df"
SESSION_ID = "20300101-010012-5e55a0f2"
START_EPOCH = 1893459620000.0                      # the count-in starts here (2030-01-01T01:00:20Z)
OPEN_CLIENT_EPOCH = 1893459612000.0                # the page opened the practice log 8 s earlier
PERF_OFFSET = 1893456000000.25                     # Date.now() - performance.now() on the page
T0_PERF = OPEN_CLIENT_EPOCH - PERF_OFFSET          # the log's t0 on the page clock
PAGE = "p-0a1c"
BAR0_EPOCH = START_EPOCH + M * BEAT
BAR0_T = BAR0_EPOCH - OPEN_CLIENT_EPOCH            # 11636.36 ms into the session
MEDIANS = [40, 44, 48, 52, 56, 52, 48, 44]
PC = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
      "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}
PRIORITY = {"off": 0, "up": 1, "down": 2, "on": 3}


def n(name: str) -> int:
    """'Eb5' -> 75 (C4 = 60)."""
    letters = name.rstrip("-0123456789")
    return (int(name[len(letters):]) + 1) * 12 + PC[letters]


def t_map(segments):
    """Session t_ms of a beat position counted from the loop's bar 0, through the run's tempo map. Under L1 the session
    clock is the page clock from the log's open: t = epoch - OPEN_CLIENT_EPOCH. The log keeps whole ms."""
    def t_of(beat: float) -> int:
        bar = math.floor(beat / M + 1e-9)
        return int(round(tm.t_epoch(segments, M, bar, beat - bar * M) - OPEN_CLIENT_EPOCH))
    return t_of


# ================================================================================================ his notes
def planted_notes(d_plan: str = "l1"):
    """[(beat from bar 0, midi, length in beats, tag)]: the A11 riff. d_plan 'd4' is the twin whose D (the #11 over the
    Ab chord) carries about 4% of the weight; 'd0' has no D at all."""
    ant = 200 / BEAT
    out = []
    for k in range(1, 9):
        s = 8 * (k - 1)
        if k in (2, 3, 4, 6, 7, 8):
            out.append((s - 0.5, n("Bb4"), 0.5, "pickup"))
        if k == 3:
            out += [(s, n("Ab4"), 2.0, "rub"), (s + 2, n("G4"), 1.0, ""), (s + 3, n("Bb4"), 1.0, "")]
        elif k == 5:
            out += [(s, n("Eb5"), 1.0, ""), (s + 1, n("Bb4"), 0.5, ""), (s + 1.5, n("Ab4"), 0.5, "passing"),
                    (s + 2, n("G4"), 1.0, ""), (s + 3, n("Bb4"), 1.0, "")]
        else:
            out += [(s, n("Eb5"), 1.0, ""), (s + 1, n("F5"), 0.5, ""), (s + 1.5, n("G5"), 0.5, "")]
            if k == 8:
                out.append((s + 2, n("A4"), 1.0, "outside"))
            elif k in (2, 4, 6):
                out += [(s + 2, n("C5"), 0.75, ""), (s + 2.75, n("F#4"), 0.25, "slide-in")]
            else:
                out.append((s + 2, n("C5"), 1.0, ""))
            if k in (1, 2, 4, 6, 8):
                out += [(s + 3, n("G4"), 1 - ant, ""), (s + 4 - ant, n("C5"), ant, "anticipation")]
            else:
                out.append((s + 3, n("G4"), 1.0, ""))
        b2 = s + 4
        if k == 7:
            out.append((b2, n("E5"), 1.0, "outside"))
        else:
            out.append((b2, n("Eb5"), 0.5, ""))
            if (k == 1 and d_plan == "l1") or (k == 5 and d_plan == "d4"):
                out.append((b2 + 0.5, n("D5"), 0.5, "sharp-eleven"))
            else:
                out.append((b2 + 0.5, n("F5"), 0.5, ""))
        keep_d = d_plan == "l1" or (k == 1 and d_plan == "d4")
        out += [(b2 + 1.0, n("D5") if keep_d else n("Bb4"), 0.5, "sharp-eleven" if keep_d else ""),
                (b2 + 1.5, n("C5"), 0.25, ""), (b2 + 1.75, n("Ab4"), 0.25, ""), (b2 + 2.0, n("G4"), 0.25, "end")]
    return sorted(out)


def perform(actions):
    """[(t_ms, 'on'|'off'|'down'|'up', note, vel)] -> page-style events with sound_end, as log.js writes them."""
    events, held, ringing, pedal = [], set(), set(), False
    for t, kind, note, vel in sorted(actions, key=lambda a: (a[0], PRIORITY[a[1]], a[2] or 0)):
        if kind == "on":
            if note in ringing:
                events.append({"t_ms": t, "kind": "sound_end", "note": note, "by": "repeat"})
            events.append({"t_ms": t, "kind": "on", "note": note, "vel": vel})
            held.add(note)
            ringing.add(note)
        elif kind == "off" and note in held:
            held.discard(note)
            events.append({"t_ms": t, "kind": "off", "note": note})
            if not pedal:
                ringing.discard(note)
                events.append({"t_ms": t, "kind": "sound_end", "note": note, "by": "release"})
        elif kind == "down" and not pedal:
            pedal = True
            events.append({"t_ms": t, "kind": "pedal", "down": True, "value": 100})
        elif kind == "up" and pedal:
            pedal = False
            events.append({"t_ms": t, "kind": "pedal", "down": False, "value": 0})
            for m in sorted(ringing - held):
                ringing.discard(m)
                events.append({"t_ms": t, "kind": "sound_end", "note": m, "by": "pedal"})
    return events


def note_actions(notes, t_of, medians=MEDIANS, passes=8, shift=0):
    """Note-on/off actions for planted notes, velocity by the pass the onset falls in (offsets 0, +3, -3 keep the
    median on the planted value)."""
    acts, index = [], {}
    for beat, midi, beats, _ in notes:
        p = min(passes - 1, max(0, math.floor(beat / 8)))
        i = index.get(p, 0)
        index[p] = i + 1
        vel = medians[p % len(medians)] + (0, 3, -3)[i % 3]
        acts += [(t_of(beat), "on", midi + shift, vel), (t_of(beat + beats), "off", midi + shift, None)]
    return acts


def pedal_actions(bars, t_of):
    """The pedal down from 0.1 to 0.9 of every bar: 80% of the run."""
    acts = []
    for b in range(bars):
        acts += [(t_of(4 * b + 0.4), "down", None, None), (t_of(4 * b + 3.6), "up", None, None)]
    return acts


def bridge_notes(run, lines):
    """Every note Claude strikes in the run, from arsenal/groove_bridge.mjs (its run form, flat)."""
    defs = {str(x["version"]): x["def"] for x in lines if isinstance(x.get("def"), dict)}
    request = {"run": run, "defs": defs, "from_bar": 0, "to_bar": run["stop_bar"], "flat": True}
    proc = subprocess.run([NODE, str(BRIDGE)], input=json.dumps(request), capture_output=True, text=True,
                          encoding="utf-8", timeout=120)
    answer = json.loads(proc.stdout)
    assert answer["ok"], answer
    return answer["notes"]


def claude_mirror_actions(run, lines):
    """Claude's strikes as a MIDI loopback would log them: the bridge's notes, each 2-9 ms late."""
    acts = []
    for i, e in enumerate(bridge_notes(run, lines)):
        lag = 2 + (i * 5) % 8
        acts += [(int(round(e["epoch_ms"] - OPEN_CLIENT_EPOCH)) + lag, "on", e["midi"], e["vel"]),
                 (int(round(e["end_epoch_ms"] - OPEN_CLIENT_EPOCH)) + lag, "off", e["midi"], None)]
    return acts


# ================================================================================================ defs and runs
def j0_start_line():
    return json.loads((J0_RUN / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])


def base_def():
    d = copy.deepcopy(j0_start_line()["def"])
    d["backing"] = "comp"
    return d


def j0_def(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


NAME_RE = re.compile(r"^([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?$")


def shift_key(key: str, s: int) -> str:
    k = nashville.parse_key(key)
    return nashville.key_name_of((k["tonic"] + s) % 12, k["mode"])


def shift_name(name: str, s: int, key: str) -> str:
    m = NAME_RE.match(name)
    bass = "/" + pr.pc_name((PC[m.group(3)] + s) % 12, key) if m.group(3) else ""
    return pr.pc_name((PC[m.group(1)] + s) % 12, key) + m.group(2) + bass


def transpose_def(d: dict, s: int) -> dict:
    """The def moved by s half steps: keys, names, pitch classes, scales, voicings (a bass under E1 folds up)."""
    d = copy.deepcopy(d)
    if s == 0:
        return d
    sh = lambda pc: (pc + s) % 12  # noqa: E731
    d["key"] = shift_key(d["key"], s)
    for sec in d["sections"]:
        sec["key"] = shift_key(sec["key"], s)
    for sl in d["slots"]:
        sl["key"] = shift_key(sl["key"], s)
        sl["name"] = shift_name(sl["name"], s, sl["key"])
        sl["tones_pc"] = {role: sh(pc) for role, pc in sl["tones_pc"].items()}
        sl["bass_pc"] = sh(sl["bass_pc"])
        sl["chord_pcs"] = [sh(pc) for pc in sl["chord_pcs"]]
        sl["scale"] = [sh(pc) for pc in sl["scale"]]
        root_text, rest = sl["scale_name"].split(" ", 1)
        sl["scale_name"] = f"{pr.pc_name(sh(PC[root_text]), sl['key'])} {rest}"
        sl["voicings"] = {k: [m + s + (12 if m + s < 28 else 0) for m in v] for k, v in sl["voicings"].items()}
        sl["page_reads"]["name"] = sl["name"]
    if isinstance(d.get("landing"), dict):
        d["landing"]["pc"] = sh(d["landing"]["pc"])
    return d


def make_run(d=None, run_id=RUN_ID, session=SESSION_ID, settings=None, ack_log=True, page=PAGE, stop_bar=16,
             start_epoch=START_EPOCH, bpm=BPM, mode="loop", changes=(), card=True):
    """(run.json, events.jsonl lines) for a stopped loop, from J0's run as a template. changes: extra lines
    [('tempo', bar, bpm) | ('next', bar, def)] applied in order. card False: a run of chords with no card."""
    d = copy.deepcopy(d or base_def())
    template = json.loads((J0_RUN / "run.json").read_text(encoding="utf-8"))
    m = d["beats_per_bar"]
    segs = [tm.first_segment(start_epoch, bpm, 1)]
    st = settings or {"from_bar": 0, "groove": "hold", "backing": "comp", "level": 44, "humanize": 0.6, "seed": 90210,
                      "walk": 1, "try_backing": "bass" if mode == "try" else None, "passes": 0, "ending": "cut"}
    lines = []
    version = 1
    start = copy.deepcopy(j0_start_line())
    start.update({"recorded_epoch_ms": start_epoch - 800, "epoch_ms": start_epoch, "bpm": bpm, "mode": mode,
                  "key": d["key"], "settings": [st], "segments": copy.deepcopy(segs), "def": d})
    if not card:
        start.pop("card", None)
    lines.append(start)
    ack_log_obj = {"local": "lg-0a1c", "session": session, "t0_perf_ms": T0_PERF} if ack_log else None

    def ack(bar, ver, **extra):
        e = tm.t_epoch(segs, m, bar)
        line = {"kind": "ack", "recorded_epoch_ms": e + 100, "by": "page", "page_id": page, "role": "owner",
                "version": ver, "bar": bar, "bar_epoch_ms": e, "perf_ms": e - PERF_OFFSET,
                "perf_offset_ms": PERF_OFFSET, "output_latency_ms": 21.3, "log": ack_log_obj, "stopped": None,
                "late_dropped": 0}
        line.update(extra)
        return line

    lines.append(ack(0, 1))
    for op, bar, value in changes:
        version += 1
        if op == "tempo":
            segs = tm.add_segment(segs, m, bar, bpm=value)
            lines.append({"kind": "change", "op": "tempo", "recorded_epoch_ms": tm.t_epoch(segs, m, bar) - 3000,
                          "by": "claude", "version": version, "effective_bar": bar, "epoch_ms": tm.t_epoch(segs, m, bar),
                          "bpm": value, "at": "bar", "segments": copy.deepcopy(segs)})
        else:
            segs = tm.add_segment(segs, m, bar, def_version=version, def_from_bar=bar)
            lines.append({"kind": "change", "op": "next", "recorded_epoch_ms": tm.t_epoch(segs, m, bar) - 3000,
                          "by": "claude", "version": version, "effective_bar": bar, "epoch_ms": tm.t_epoch(segs, m, bar),
                          "def": value, "at": "bar", "segments": copy.deepcopy(segs)})
        lines.append(ack(bar, version, effective_bar=bar))
    version += 1
    stop_epoch = tm.t_epoch(segs, m, stop_bar)
    lines.append({"kind": "stop", "recorded_epoch_ms": stop_epoch - 3000, "by": "claude", "version": version,
                  "effective_bar": stop_bar, "epoch_ms": stop_epoch, "reason": "cli", "at": "bar"})
    lines.append(ack(stop_bar, version, stop_bar=stop_bar))
    for seq, line in enumerate(lines):
        line["seq"] = seq
    run = copy.deepcopy(template)
    run.update({"run": run_id, "mode": mode, "created_at": "2030-01-01T01:00:19.200+00:00", "key": d["key"],
                "beats_per_bar": m, "start_epoch_ms": start_epoch, "bar0_epoch_ms": tm.t_epoch(segs, m, 0),
                "segments": segs, "settings": [st], "last_version": version, "owner_page_id": page,
                "stopped_epoch_ms": stop_epoch, "stop_bar": stop_bar, "stop_reason": "cli"})
    if card:
        run["card_snapshot"]["key"] = d["key"]
    else:
        run["card"], run["card_snapshot"] = None, None
    return run, lines


def _iso(epoch_ms: float) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat(timespec="milliseconds")


def session_meta(kind: str, opened_epoch: float = OPEN_CLIENT_EPOCH) -> dict:
    """The log's open meta: 'full' (page_id, t0_perf_ms, opened_at_client: L2 without an L1 ack), 'l3'
    (opened_at_client only), 'l4' (nothing), 'buffered' (a buffered session with nothing)."""
    iso = _iso(opened_epoch)
    return {"full": {"page_id": PAGE, "t0_perf_ms": opened_epoch - PERF_OFFSET, "opened_at_client": iso,
                     "buffered": False},
            "l3": {"opened_at_client": iso, "buffered": False},
            "l4": {"buffered": False},
            "buffered": {"buffered": True}}[kind]


def session_doc(events, meta, session=SESSION_ID, opened_epoch=OPEN_CLIENT_EPOCH):
    last = max((e["t_ms"] for e in events), default=0)
    opened = opened_epoch + 41                     # the server's open time, 41 ms after the page's
    return {"api": "arsenal.performance/v0", "session": session, "opened_at": _iso(opened),
            "opened_ns": int(round(opened)) * 1000000, "client_id": "lg-0a1c", "meta": meta, "closed": True,
            "event_count": len(events), "last_t_ms": last, "duration_s": round(last / 1000, 3)}


def write_jam(folder: Path, runs, sessions):
    """runs: [(run, lines)]; sessions: [(session doc, events)] -> folder/jam/runs/..., folder/performance/..."""
    for run, lines in runs:
        d = folder / "jam" / "runs" / run["run"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8", newline="\n")
        (d / "events.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines),
                                        encoding="utf-8", newline="\n")
    (folder / "jam").mkdir(parents=True, exist_ok=True)
    for info, events in sessions:
        d = folder / "performance" / info["session"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "session.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                                        newline="\n")
        (d / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events),
                                        encoding="utf-8", newline="\n")
    return folder


def jam_case(folder: Path, d_plan="l1", shift=0, meta="full", ack_log=True, humanize=0.6, walk=1, mirror=False,
             changes=(), mode="loop", d=None, card=True, keep=None, session_shift_ms=0) -> dict:
    """One synthetic jam: a stopped 16-bar run and one session with the planted riff (moved by shift half steps; the
    def moves with it unless d is given), the pedal, and optionally Claude's notes mirrored into the log."""
    d = copy.deepcopy(d) if d is not None else transpose_def(base_def(), shift)
    settings = {"from_bar": 0, "groove": "hold", "backing": "comp", "level": 44, "humanize": humanize, "seed": 90210,
                "walk": walk, "try_backing": "bass" if mode == "try" else None, "passes": 0, "ending": "cut"}
    run, lines = make_run(d=d, settings=settings, ack_log=ack_log, changes=changes, mode=mode, card=card)
    t_of = t_map(run["segments"])
    notes = planted_notes(d_plan)
    if keep is not None:
        notes = notes[:keep]
    acts = note_actions(notes, t_of, shift=shift) + pedal_actions(16, t_of)
    if mirror:
        acts += claude_mirror_actions(run, lines)
    events = perform(acts)
    opened = OPEN_CLIENT_EPOCH + session_shift_ms
    write_jam(folder, [(run, lines)], [(session_doc(events, session_meta(meta, opened), opened_epoch=opened), events)])
    return {"folder": folder, "run": run, "lines": lines, "notes": notes, "t_of": t_of,
            "root": folder / "performance", "jam": folder / "jam"}


FIXTURES = {"riff_lydian_l1": {}, "riff_lydian_d4": {"d_plan": "d4"},
            "riff_lydian_loopback": {"mirror": True, "humanize": 0, "walk": 0},
            "riff_lydian_buffered": {"meta": "buffered", "ack_log": False}}


def build_fixture(name: str, folder: Path) -> Path:
    """One of the riff_* fixtures, written under folder (a temp dir, or tests/fixtures/jam/<name>)."""
    case = jam_case(folder, **FIXTURES[name])
    if name == "riff_lydian_l1":
        notes, t_of = case["notes"], case["t_of"]
        tagged = lambda tag: [t_of(b) for b, _, _, g in notes if g == tag]  # noqa: E731
        expected = {
            "note": "Synthetic A11 jam (jam-spec 14): generated by tests/test_arsenal_practice_riff.py build_fixture.",
            "run": RUN_ID, "session": SESSION_ID, "bar0_t_ms": BAR0_T,
            "planted": {"sharp_eleven": {"slot": 1, "label": "#11", "count": 9, "t_ms": tagged("sharp-eleven")},
                        "rub": tagged("rub"), "passing": tagged("passing"), "slide_ins": tagged("slide-in"),
                        "outside": tagged("outside"), "anticipations": tagged("anticipation"),
                        "phrases": {"count": 8, "pickups": 6,
                                    "t_ms": sorted(tagged("pickup") + [t_of(0), t_of(32)])},
                        "vel_medians": MEDIANS, "pedal": 0.8}}
        (folder / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8", newline="\n")
    return folder


def build_long_session(folder: Path, runs: int = 4, reps: int = 5) -> Path:
    """A 30-minute session with `runs` loops of 16 x reps bars each (the planted riff reps times per run)."""
    jam_runs, acts = [], []
    for k in range(runs):
        start = START_EPOCH + k * 7 * 60000
        run, lines = make_run(run_id=f"20300101-01{7 * k:02d}19-7a11c0d{k}", start_epoch=start, stop_bar=16 * reps)
        t_of = t_map(run["segments"])
        notes = [(b + 64 * r, midi, beats, tag) for r in range(reps) for b, midi, beats, tag in planted_notes()]
        acts += note_actions(notes, t_of, passes=8 * reps) + pedal_actions(16 * reps, t_of)
        jam_runs.append((run, lines))
    acts += [(29 * 60000 + 59000, "on", n("C5"), 50), (29 * 60000 + 59500, "off", n("C5"), None)]
    events = perform(acts)
    return write_jam(folder, jam_runs, [(session_doc(events, session_meta("full")), events)])


# ================================================================================================ helpers
@functools.lru_cache(maxsize=None)
def _fixture_doc_json(name: str, rebuild=None) -> str:
    f = FIX / name
    return json.dumps(riff.riff(RUN_ID, root=f / "performance", jam_root=f / "jam", rebuild=rebuild))


def fixture_doc(name: str, rebuild=None) -> dict:
    return json.loads(_fixture_doc_json(name, rebuild))


def case_doc(case: dict, rebuild="def", **kw) -> dict:
    return riff.riff(kw.pop("run", RUN_ID), root=case["root"], jam_root=case["jam"], rebuild=rebuild, **kw)


def slot(block: dict, i: int) -> dict:
    return next(s for s in block["slots"] if s["slot"] == i)


def planted_counts(doc: dict) -> dict:
    b = doc["runs"][0]
    total = lambda c: sum(s["classes"][c] for s in b["slots"])  # noqa: E731
    return {"sharp_eleven": slot(b, 1)["labels"].get("#11", 0), "rub": total("rub"), "passing": total("passing"),
            "slide_in": total("slide_in"), "slide_dirs": [x["direction"] for x in b["slide_ins"]],
            "outside": total("outside"), "anticipations": len(b["anticipations"]), "phrases": len(b["phrases"]),
            "pickups": sum(1 for p in b["phrases"] if p["pickup"]), "phrase_bars": [p["bars"] for p in b["phrases"]],
            "vel_medians": [p["vel_median"] for p in b["passes"]], "pedal": [p["pedal"] for p in b["passes"]]}


A11_COUNTS = {"sharp_eleven": 9, "rub": 1, "passing": 1, "slide_in": 3, "slide_dirs": ["below"] * 3, "outside": 2,
              "anticipations": 5, "phrases": 8, "pickups": 6, "phrase_bars": [2.0] * 8, "vel_medians": MEDIANS,
              "pedal": [0.8] * 8}


def invariant_view(doc: dict) -> dict:
    """Everything the analysis says that must not depend on the key."""
    b = doc["runs"][0]
    return {"slots": [(s["slot"], s["classes"], s["all_notes"], s["labels"], s["bass_labels"], s["landings"],
                       len(s["rubs"]), len(s["passing"]), len(s["outside"]), (s["scale"] or {}).get("named"))
                      for s in b["slots"]],
            "anticipations": [a["t_ms"] for a in b["anticipations"]],
            "slide_ins": [(x["t_ms"], x["direction"]) for x in b["slide_ins"]],
            "phrases": [(p["t_ms"], p["pass"], p["bar"], p["beat"], p["bars"], p["pickup"], p["contour"],
                         p["landing"]["class"], p["landing"]["label"]) for p in b["phrases"]],
            "degrees": b["degrees_by_bar"],
            "passes": [(p["pass"], p["vel_median"], p["shares"], p["rests"], p["pedal"], p["fact"]) for p in b["passes"]],
            "checks": [(c["pass"], c["count"]) for c in b["checks"]],
            "types": [p["type"] for p in doc["talking_points"]],
            "question": ((doc["question"] or {}).get("kind"), (doc["question"] or {}).get("at")),
            "try": (doc["try"] or {}).get("rule"), "loopback": b["loopback"]["mirrored_share"]}


# ================================================================================================ fixtures
@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixture_files_match_their_builder(tmp_path, name):
    if FIXTURES[name].get("mirror") and NODE is None:
        pytest.skip("the loopback fixture mirrors the groove bridge, which needs node")
    built = build_fixture(name, tmp_path / name)
    on_disk = FIX / name
    files = sorted(p.relative_to(built).as_posix() for p in built.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(on_disk).as_posix() for p in on_disk.rglob("*") if p.is_file())
    for rel in files:
        assert (built / rel).read_bytes() == (on_disk / rel).read_bytes(), f"{name}/{rel} is stale: --write-fixtures"


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixture_runs_and_sessions_are_valid_and_synthetic(name):
    f = FIX / name
    run = json.loads((f / "jam" / "runs" / RUN_ID / "run.json").read_text(encoding="utf-8"))
    schemas.validate_run(run)
    for line in (f / "jam" / "runs" / RUN_ID / "events.jsonl").read_text(encoding="utf-8").splitlines():
        schemas.validate_run_event(json.loads(line))
    store = PerformanceStore(f / "performance")
    info = store.info(SESSION_ID)
    events, problems = pr.read_events(store, SESSION_ID)
    assert problems == [] and events
    assert info["opened_at"].startswith("2030-") and run["created_at"].startswith("2030-")
    assert run["run"].startswith("2030") and SESSION_ID.startswith("2030")


# ================================================================================================ A11
def test_a11_planted_counts_are_reported_exactly():
    doc = fixture_doc("riff_lydian_l1")
    assert doc["api"] == RIFF_API and doc["session"] == SESSION_ID
    assert planted_counts(doc) == A11_COUNTS
    b = doc["runs"][0]
    assert slot(b, 1)["name"] == "Abmaj7#11" and slot(b, 0)["name"] == "Ebmaj9"
    assert b["coverage"] == {"passes": 8, "bars": 16, "bars_with_his_notes": 16, "notes": 99, "top_line_notes": 99}
    notes = b["notes"]
    rub = [x for x in notes if x["class"] == "rub"]
    assert [(x["name"], x["pass"], x["bar"], x["beat"], x["beats"]) for x in rub] == [("Ab4", 3, 1, 0.0, 2.0)]
    passing = [x for x in notes if x["class"] == "passing"]
    assert [(x["name"], x["pass"], x["bar"], x["beat"], x["grid"]) for x in passing] == [("Ab4", 5, 1, 1.5, "offbeat")]
    assert [(x["name"], x["pass"]) for x in notes if x["class"] == "slide_in"] == [("Gb4", 2), ("Gb4", 4), ("Gb4", 6)]
    outside = [(x["name"], x["pass"], x["bar"], x["beat"], x["beats"], x["slot"]) for x in notes if x["class"] == "outside"]
    assert outside == [("E5", 7, 2, 0.0, 1.0, 1), ("A4", 8, 1, 2.0, 1.0, 0)]
    assert all("anticipates" in x["flags"] for x in notes if x["t_ms"] in {a["t_ms"] for a in b["anticipations"]})
    assert all(190 <= a["early_ms"] <= 210 for a in b["anticipations"])
    assert [p["pass"] for p in b["passes"]] == list(range(1, 9))


def test_a11_planted_times_within_10_ms():
    doc = fixture_doc("riff_lydian_l1")
    b = doc["runs"][0]
    planted = json.loads((FIX / "riff_lydian_l1" / "expected.json").read_text(encoding="utf-8"))["planted"]

    def close(got, want):
        assert len(got) == len(want), (got, want)
        assert all(abs(g - w) <= 10 for g, w in zip(sorted(got), sorted(want))), (got, want)

    close([x["t_ms"] for x in b["notes"] if x["slot"] == 1 and x["label"] == "#11"], planted["sharp_eleven"]["t_ms"])
    close([x["t_ms"] for s in b["slots"] for x in s["rubs"]], planted["rub"])
    close([x["t_ms"] for s in b["slots"] for x in s["passing"]], planted["passing"])
    close([x["t_ms"] for x in b["slide_ins"]], planted["slide_ins"])
    close([x["t_ms"] for s in b["slots"] for x in s["outside"]], planted["outside"])
    close([x["t_ms"] for x in b["anticipations"]], planted["anticipations"])
    close([p["t_ms"] for p in b["phrases"]], planted["phrases"]["t_ms"])


def test_a11_alignment_is_l1_within_2_ms():
    a = fixture_doc("riff_lydian_l1")["runs"][0]["alignment"]
    assert a["method"] == "L1" and a["error_ms"] <= 2 and a["approx"] is False
    assert abs(a["bar0_t_ms"] - BAR0_T) <= 0.1 and a["page_id"] == PAGE


def test_a11_mode_naming_gate_and_its_twin():
    doc = fixture_doc("riff_lydian_l1")
    sc = slot(doc["runs"][0], 1)["scale"]
    assert sc["best"] == "Ab Lydian" and sc["named"] is True and sc["own_note"] == "D" and sc["own_share"] >= 0.05
    t2 = [p for p in doc["talking_points"] if p["type"] == "T2"]
    assert len(t2) == 1 and "(Ab Lydian)" in t2[0]["text"] and "the D, its #11, came 9 times" in t2[0]["text"]
    twin = fixture_doc("riff_lydian_d4")
    sc = slot(twin["runs"][0], 1)["scale"]
    assert sc["own_note"] == "D" and 0.03 <= sc["own_share"] < 0.05, sc
    assert sc["named"] is False and sc["say"] == "the notes of Eb major"
    assert "T2" not in [p["type"] for p in twin["talking_points"]]


def test_a11_transposition_invariance_in_all_12_keys(tmp_path):
    views, keys = {}, set()
    for s in range(-6, 6):
        doc = case_doc(jam_case(tmp_path / f"shift{s + 6}", shift=s))
        views[s] = invariant_view(doc)
        keys.add(doc["runs"][0]["key"])
        assert planted_counts(doc) == A11_COUNTS, s
    assert len(keys) == 12
    same = [s for s in views if views[s] == views[0]]
    assert len(same) == 12, {s: v for s, v in views.items() if v != views[0]}


def test_a11_free_play_same_notes_no_run(tmp_path, capsys):
    f = FIX / "riff_lydian_l1"
    empty = tmp_path / "jam"
    empty.mkdir()
    code = riff.main(["--session", SESSION_ID, "--root", str(f / "performance"), "--jam-root", str(empty), "--json"])
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    free = doc["free_play"]
    assert doc["runs"] == [] and free["mode"] == "free play" and free["chords"] == "chords read from your own playing"
    assert free["anticipations"] == []
    assert "T14" not in [p["type"] for p in doc["talking_points"]]
    assert all("beat" not in p and "seconds" in p for p in free["phrases"])
    if NODE:
        assert free["coverage"]["chords_read"] > 0 and free["coverage"]["notes"] > 0
    assert riff.wording_problems(doc) == []


def test_a11_buffered_session_at_l4_exits_2_naming_opened_at_client(capsys):
    f = FIX / "riff_lydian_buffered"
    code = riff.main([RUN_ID, "--root", str(f / "performance"), "--jam-root", str(f / "jam")])
    assert code == 2
    captured = capsys.readouterr()
    assert "opened_at_client" in captured.err and captured.out == ""


@needs_node
def test_a11_loopback_guard_through_the_groove_bridge():
    mirrored = fixture_doc("riff_lydian_loopback")
    lb = mirrored["runs"][0]["loopback"]
    assert lb["source"] == "groove_bridge.mjs" and lb["claude_onsets"] > 0
    assert lb["suspected"] is True and lb["mirrored_share"] >= 0.9
    assert "the loop may be echoing into the log (MIDI loopback)" in riff.render(mirrored)
    assert slot(mirrored["runs"][0], 1)["labels"]["#11"] == 9           # and it still analyses
    clean = fixture_doc("riff_lydian_l1")["runs"][0]["loopback"]
    assert clean["source"] == "groove_bridge.mjs" and clean["claude_onsets"] > 0
    assert clean["suspected"] is False and clean["mirrored_share"] == 0.0


def test_a11_loopback_guard_from_the_def_without_node():
    lb = fixture_doc("riff_lydian_loopback", "def")["runs"][0]["loopback"]
    assert lb["source"].startswith("the def's downbeat strikes")
    assert lb["suspected"] is True and lb["mirrored_share"] >= 0.9
    clean = fixture_doc("riff_lydian_l1", "def")["runs"][0]["loopback"]
    assert clean["suspected"] is False and clean["mirrored_share"] == 0.0


WORDING_CASES = {
    "l1": {}, "d4": {"d_plan": "d4"}, "d0": {"d_plan": "d0"}, "loopback": {"mirror": True, "humanize": 0, "walk": 0},
    "l2": {"ack_log": False}, "l3": {"ack_log": False, "meta": "l3"}, "l4": {"ack_log": False, "meta": "l4"},
    "tempo": {"changes": [("tempo", 8, 80)]}, "next": {"changes": [("next", 8, "Db")]}, "try": {"mode": "try"},
    "lament": {"d": "def_lament_bass", "card": False, "shift": -2},
    "dorian": {"d": "def_dorian_vamp", "card": False, "shift": -1},
}


def wording_case(tmp_path: Path, name: str) -> dict:
    kw = copy.deepcopy(WORDING_CASES[name])
    if isinstance(kw.get("d"), str):
        kw["d"] = j0_def(kw["d"])
    kw["changes"] = [(op, bar, transpose_def(base_def(), -2) if value == "Db" else value)
                     for op, bar, value in kw.get("changes", ())]
    return jam_case(tmp_path / name, **kw)


def test_a11_wording_guard_over_13_fixtures(tmp_path):
    docs = {}
    for name in WORDING_CASES:
        if WORDING_CASES[name].get("mirror") and NODE is None:
            continue
        docs[name] = case_doc(wording_case(tmp_path, name), rebuild=None)
    empty = tmp_path / "empty-jam"
    empty.mkdir()
    docs["free"] = riff.riff(None, session=SESSION_ID, root=FIX / "riff_lydian_l1" / "performance", jam_root=empty)
    assert len(docs) >= 12
    sentences = 0
    for name, doc in docs.items():
        text = riff.render(doc)
        for word in riff.FORBIDDEN_WORDS:
            assert not re.search(rf"\b{word}\b", text, re.I), (name, word, text)
        assert "%" not in text, name
        assert riff.wording_problems(doc, text) == [], name
        sentences += len(riff.sentences(doc))
    assert sentences >= 60


def test_wording_guard_catches_what_it_guards():
    doc = fixture_doc("riff_lydian_l1")
    doc["talking_points"][0]["text"] += " That was a mistake 97% of the time, in Lydian."
    problems = riff.wording_problems(doc)
    assert any("mistake" in p for p in problems)
    assert any("'%'" in p for p in problems)
    assert any("'97'" in p for p in problems)
    assert any("Lydian" in p and "brackets" in p for p in problems)


def test_a11_speed_30_minute_session_with_4_runs(tmp_path):
    folder = build_long_session(tmp_path)
    t = time.perf_counter()
    doc = riff.riff(None, session=SESSION_ID, root=folder / "performance", jam_root=folder / "jam")
    elapsed = time.perf_counter() - t
    assert elapsed <= 3.0, elapsed
    assert len(doc["runs"]) == 4 and all(b["coverage"]["passes"] == 40 for b in doc["runs"])
    assert PerformanceStore(folder / "performance").info(SESSION_ID)["last_t_ms"] >= 29 * 60000 + 59000


# ================================================================================================ the rest of 11
@pytest.mark.parametrize("meta,method,error", [("full", "L2", 2.0), ("l3", "L3", 50.0), ("l4", "L4", 150.0)])
def test_alignment_ladder_without_an_l1_ack(tmp_path, meta, method, error):
    doc = case_doc(jam_case(tmp_path, meta=meta, ack_log=False))
    b = doc["runs"][0]
    a = b["alignment"]
    assert a["method"] == method and a["error_ms"] == error and a["approx"] is (method == "L4")
    assert abs(a["bar0_t_ms"] - BAR0_T) <= error
    assert slot(b, 1)["labels"]["#11"] == 9                            # which chord: at every level
    assert len(b["anticipations"]) == 5
    assert all(x.get("approx") is (True if method == "L4" else None) for x in b["anticipations"] + b["phrases"])


def test_tempo_change_mid_run_follows_the_tempo_map(tmp_path):
    case = jam_case(tmp_path, changes=[("tempo", 8, 80)])
    doc = case_doc(case)
    assert planted_counts(doc) == A11_COUNTS
    assert doc["runs"][0]["bpm"] == [66, 80] and doc["runs"][0]["coverage"]["bars"] == 16
    loaded = riff.load_run(case["jam"], RUN_ID)
    tl = riff.RunTimeline(loaded, riff.align(loaded, SESSION_ID, PerformanceStore(case["root"]).info(SESSION_ID)))
    segs = case["run"]["segments"]
    assert len(tl.instances) == 16
    for inst in tl.instances:
        assert abs(inst["start_t"] - (tm.t_epoch(segs, M, inst["bar_ix"]) - OPEN_CLIENT_EPOCH)) <= 0.01
        assert abs(inst["end_t"] - (tm.t_epoch(segs, M, inst["bar_ix"] + 1) - OPEN_CLIENT_EPOCH)) <= 0.01


def test_next_card_mid_run_keeps_counting_passes(tmp_path):
    doc = case_doc(jam_case(tmp_path, changes=[("next", 8, transpose_def(base_def(), -2))]))
    b = doc["runs"][0]
    assert b["coverage"]["passes"] == 8
    assert {(s["def_version"], s["name"]) for s in b["slots"]} == \
        {(1, "Ebmaj9"), (1, "Abmaj7#11"), (2, "Dbmaj9"), (2, "Gbmaj7#11")}
    assert [x["def_version"] for x in b["degrees_by_bar"]["by_def"]] == [1, 2]
    assert sorted({x["pass"] for x in b["notes"] if x["t_ms"] >= case_t(8)}) == [5, 6, 7, 8]


def case_t(bar: int) -> float:
    return BAR0_T + bar * M * BEAT


def test_not_enough_playing_inside_the_loop_exits_0(tmp_path, capsys):
    case = jam_case(tmp_path, keep=5)
    code = riff.main([RUN_ID, "--root", str(case["root"]), "--jam-root", str(case["jam"]), "--json", "--rebuild", "def"])
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    b = doc["runs"][0]
    assert b["enough"] is False and b["say"] == "not enough playing inside the loop to talk about (5 notes)"
    assert doc["talking_points"] == [] and doc["question"] is None and doc["try"] is None


def test_no_session_overlapping_the_run_exits_2(tmp_path, capsys):
    case = jam_case(tmp_path, session_shift_ms=24 * 3600 * 1000)
    code = riff.main([RUN_ID, "--root", str(case["root"]), "--jam-root", str(case["jam"])])
    assert code == 2
    err = capsys.readouterr().err
    assert f"no practice session overlaps run {RUN_ID}, which played from" in err
    assert f"nearest sessions: {SESSION_ID}" in err


def test_question_try_checks_and_the_held_rub_point():
    doc = fixture_doc("riff_lydian_l1")
    planted = json.loads((FIX / "riff_lydian_l1" / "expected.json").read_text(encoding="utf-8"))["planted"]
    q = doc["question"]
    assert q["kind"] == "rub" and q["at"] == pr.clock(planted["rub"][0])
    assert q["text"] == f"At {pr.clock(planted['rub'][0])} the Ab rubbed against the G in Ebmaj9. Did you want that rub?"
    assert q["replay"] == riff.replay_command(SESSION_ID, planted["rub"][0] - 4000, 8)
    assert doc["try"]["rule"] == 5 and doc["try"]["text"].startswith("Keep the loop going. On the Ab bar")
    check = doc["runs"][0]["checks"][0]
    assert check["id"] == "sharp-eleven" and check["pass"] is True and check["count"] == 9
    t4 = [p for p in fixture_doc("riff_lydian_d4")["talking_points"] if p["type"] == "T4"]
    assert t4 and t4[0]["text"] == (f"At {pr.clock(planted['rub'][0])} you held Ab over Ebmaj9 for 2 beats: it rubs a "
                                    f"half step against the G. At {pr.clock(planted['passing'][0])} the same Ab passed "
                                    f"quickly.")


def test_concept_note_missing_gives_try_rule_1(tmp_path):
    doc = case_doc(jam_case(tmp_path, d_plan="d0"))
    check = doc["runs"][0]["checks"][0]
    assert check["pass"] is False and check["count"] == 0
    assert doc["try"]["rule"] == 1 and doc["try"]["text"] == "Land your top note on D in bar 2."
    assert doc["try"]["card"] == {"id": "lydian-four", "target_notes": [74], "bar": 2}
    assert "- sharp-eleven: D did not come up this time" in riff.render(doc)


def test_card_with_no_run_is_assumed_alignment(tmp_path, capsys):
    f = FIX / "riff_lydian_l1"
    def_path = tmp_path / "lydian.def.json"
    def_path.write_text(json.dumps(base_def()), encoding="utf-8")
    code = riff.main(["--card", str(def_path), "--from", "0:11.636", "--bpm", "66", "--session", SESSION_ID,
                      "--root", str(f / "performance"), "--jam-root", str(tmp_path / "jam"), "--json",
                      "--rebuild", "def"])
    assert code == 0
    b = json.loads(capsys.readouterr().out)["runs"][0]
    assert b["alignment"]["method"] == "assumed" and b["alignment"]["approx"] is True
    assert slot(b, 1)["labels"]["#11"] == 9 and len(b["anticipations"]) == 5
    assert all(x["approx"] is True for x in b["anticipations"])


def test_save_writes_only_the_riff_file(tmp_path, capsys):
    folder = tmp_path / "jam-case"
    shutil.copytree(FIX / "riff_lydian_l1", folder)
    before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    code = riff.main([RUN_ID, "--root", str(folder / "performance"), "--jam-root", str(folder / "jam"), "--save",
                      "--rebuild", "def"])
    assert code == 0
    saved = folder / "jam" / "riffs" / f"{RUN_ID}.json"
    doc = json.loads(saved.read_text(encoding="utf-8"))
    assert doc["api"] == RIFF_API and doc["saved_at"] and [b["run"] for b in doc["runs"]] == [RUN_ID]
    after = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    assert set(after) - set(before) == {saved} and all(after[p] == before[p] for p in before)
    assert "saved" in capsys.readouterr().err


def test_the_practice_verb_registration():
    f = FIX / "riff_lydian_l1"
    proc = subprocess.run([sys.executable, "-m", "arsenal.practice", "riff", RUN_ID, "--root", str(f / "performance"),
                           "--jam-root", str(f / "jam"), "--json", "--rebuild", "def"], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["api"] == RIFF_API and doc["runs"][0]["alignment"]["method"] == "L1"
    assert doc["constants"]["ONSET_GROUP_MS"] == 50 and doc["constants"]["GRID_TOL"] == 0.08


def test_latest_and_session_forms_and_the_filters(capsys):
    f = FIX / "riff_lydian_l1"
    base = ["--root", str(f / "performance"), "--jam-root", str(f / "jam"), "--json", "--rebuild", "def"]
    assert riff.main(["latest"] + base) == 0
    latest = json.loads(capsys.readouterr().out)
    assert [b["run"] for b in latest["runs"]] == [RUN_ID] and latest["session"] == SESSION_ID
    assert riff.main(["--session", SESSION_ID] + base) == 0
    by_session = json.loads(capsys.readouterr().out)
    assert [b["run"] for b in by_session["runs"]] == [RUN_ID] and "free_play" not in by_session
    for flags in (["--pass", "3"], ["--bars", "5-6"]):
        assert riff.main([RUN_ID] + flags + base) == 0
        b = json.loads(capsys.readouterr().out)["runs"][0]
        assert b["coverage"]["passes"] == 1 and b["coverage"]["bars"] == 2, flags
        assert sum(s["classes"]["rub"] for s in b["slots"]) == 1 and sum(s["classes"]["passing"] for s in b["slots"]) == 0
        assert {x["pass"] for x in b["notes"]} == {3}
    assert riff.main([RUN_ID, "--pass", "0"] + base) == 2
    assert "--pass counts from 1" in capsys.readouterr().err


def test_text_render_is_chat_ready():
    text = riff.render(fixture_doc("riff_lydian_l1"))
    assert text.startswith("Riff on The Lydian 4 chord (lydian-four): loop in Eb major at 66 bpm")
    assert "lined up by the page's own clock: L1, within 2 ms." in text
    assert "8 passes, 16 bars, 99 notes of yours (99 in the top line)" in text
    for part in ("Talking points:", "Card checks:", "Highlights:", "A question:", "One thing to try:"):
        assert part in text
    assert text.count("\n- ") >= 6


def test_passes_he_did_not_play_are_not_growth_or_misses(tmp_path):
    """Round-1 verify: he joined at pass 2 and stopped after pass 7, with one stray note in pass 8. The growth point
    compares only passes that hold his playing, and the card's landing counts only the times he played over it."""
    d = base_def()
    d.setdefault("landing", {"slot": 1, "role": "#11", "pc": PC["D"], "pull": "D, the #11, floats over the Ab bass."})
    run, lines = make_run(d=d)
    t_of = t_map(run["segments"])
    notes = [x for x in planted_notes() if 8 <= x[0] < 56]  # passes 2..7 only (a pass is 8 beats)
    notes.append((58.0, n("Eb5"), 1.0, "stray"))             # one note in pass 8, over its first chord
    events = perform(note_actions(notes, t_of) + pedal_actions(16, t_of))
    folder = write_jam(tmp_path / "late", [(run, lines)], [(session_doc(events, session_meta("full")), events)])
    doc = riff.riff(RUN_ID, root=folder / "performance", jam_root=folder / "jam", rebuild="def")
    b = doc["runs"][0]
    held = [p["pass"] for p in b["passes"] if p["top_line_notes"] >= riff.T13_MIN_PASS_NOTES]
    assert held == [2, 3, 4, 5, 6, 7], [(p["pass"], p["top_line_notes"]) for p in b["passes"]]
    for point in doc["talking_points"]:
        if point["type"] == "T13":
            ev = point["evidence"]
            assert set(ev["passes"] + ev["to_passes"]) <= set(held), ev
            assert ev["from_notes"] >= riff.T13_MIN_NOTES and ev["to_notes"] >= riff.T13_MIN_NOTES, ev
    ld = b["card_landing"]
    assert ld is not None and (ld["instances"], ld["instances_all"]) == (6, 8), ld
    text = riff.render(doc)
    assert f"of the {ld['instances']} times you played over it" in text
    assert riff.wording_problems(doc, text) == []


def test_landing_and_check_notes_are_spelled_from_the_chord():
    """Round-2 verify: the riff named borrowed-four-minor's landing and its check with the key's table (pc_name(11,
    'Eb major') is B), where the card and jam-rulings say Cb, the b3 of Abm(add9). Both are spelled from the chord's own
    tones now, also for a def recorded before resolve carried landing.note."""
    from types import SimpleNamespace
    from arsenal.jam.resolve import tone_name
    slot = {"name": "Abm(add9)", "key": "Eb major", "tones_pc": {"root": 8, "third": 11, "fifth": 3, "ninth": 10},
            "bass_pc": 8}
    d = {"slots": [slot], "landing": {"slot": 0, "role": "b3", "relative_to": "root", "pc": 11, "pull": "Cb, the b3."}}
    f = {"root": 8, "bass": 8, "roles": {8: "root", 11: "third", 3: "fifth", 10: "ninth"}, "key": "Eb major",
         "name": "Abm(add9)", "major_third": False, "sus": False}
    tl = SimpleNamespace(defs={1: d}, facts=lambda version, i: f)
    block = {"_insts": [{"i": 0, "slot": 0, "def_version": 1}], "_recs": [], "_landings": {}}
    assert pr.pc_name(11, "Eb major") == "B"  # the key's table, which the riff no longer uses for these
    assert riff.card_landing(tl, block, 1)["note"] == "Cb"
    card = {"checks": [{"id": "borrowed", "slot": 0, "role": "b3", "want": "present", "say": "you played Cb"}]}
    assert riff.card_checks(tl, block, card, None, 1)[0]["note"] == "Cb"
    # Daniel's keys (round-2 landing_check rows): double flats and a slash bass keep the chord's letters
    for name, key, tones, bass, role, rel, want in (
            ("Gm(add9)", "D major", {"root": 7}, 7, "b3", "root", "Bb"),
            ("Cm(add9)", "G major", {"root": 0}, 0, "b3", "root", "Eb"),
            ("Cbm(add9)", "Gb major", {"root": 11}, 11, "b3", "root", "Ebb"),
            ("Dbm(add9)", "Ab major", {"root": 1}, 1, "b3", "root", "Fb"),
            ("Gbm(add9)", "Db major", {"root": 6}, 6, "b3", "root", "Bbb"),
            ("Db11/Cb", "Gb major", {"root": 1}, 11, "1", "bass", "Cb"),
            ("Cmaj7#11", "G major", {"root": 0}, 0, "#11", "root", "F#")):
        assert tone_name({"name": name, "key": key, "tones_pc": tones, "bass_pc": bass}, role, rel) == want, name
    assert tone_name({"name": "a cluster of mine", "key": "Eb major", "tones_pc": {"root": 8}, "bass_pc": 8}, "b3") is None


if __name__ == "__main__" and "--write-fixtures" in sys.argv:
    for fixture in FIXTURES:
        target = FIX / fixture
        if target.exists():
            shutil.rmtree(target)
        build_fixture(fixture, target)
        print(f"wrote {target}")
