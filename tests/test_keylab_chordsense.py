"""Pins for arsenal/keylab/chordsense.py: live chords, key, roman numerals, tension and pedal, from audio or notes.

Everything here is synthetic and offline (numpy additive "piano" chords, the beatbench's own drum sounds on top),
except the Joy to the World tests, which read Daniel's own playing (an FL Studio score log, ppq 96) from a
private JSON that is never committed: $KEYLAB_JOY_NOTES, else state/arsenal/keylab/joy_notes.json, else the
scratch copy the 2026-10-23 session wrote. Without it those tests skip.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import pytest

from arsenal.keylab import beatbench as BB
from arsenal.keylab import chordsense as CS

RATE = 48000
HOP = 512

# close piano voicings with an explicit bass (MIDI note numbers)
VOICINGS = {
    "C": [36, 48, 52, 55, 60, 64], "Am": [45, 57, 60, 64, 69], "G7": [43, 55, 59, 62, 65],
    "Fmaj7": [41, 53, 57, 60, 64], "Dm7": [38, 50, 53, 57, 60], "Bdim": [47, 59, 62, 65],
    "Csus4": [36, 48, 53, 55, 60], "C/E": [40, 48, 52, 55, 60],
}
EIGHT = ["C", "Am", "G7", "Fmaj7", "Dm7", "Bdim", "Csus4", "C/E"]


# --- synthesis ---------------------------------------------------------------------------------------------

def piano(midi: float, dur: float, rate: int, vel: float, rng) -> np.ndarray:
    """A piano-like note: ten slightly stretched harmonics (1/h^1.1), the higher ones dying faster, a 4 ms attack,
    held for `dur` then a 0.3 s release."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    n = int((dur + 0.3) * rate)
    t = np.arange(n) / rate
    out = np.zeros(n)
    for h in range(1, 11):
        fh = h * f0 * np.sqrt(1 + 2e-4 * h * h)
        if fh > 0.45 * rate:
            break
        out += np.sin(2 * np.pi * fh * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t * h ** 0.6 / 1.6) / h ** 1.1
    env = np.minimum(1.0, t / 0.004) * np.where(t < dur, 1.0, np.clip((dur + 0.3 - t) / 0.3, 0.0, 1.0))
    return vel * out * env


def render(seq, rate=RATE, strike_every=None, drums=True, detune_cents=0.0, seed=1):
    """seq: [(midi notes, seconds, label)]. Chords held (or re-struck every `strike_every` s), normalised, with
    the beatbench's kick / snare / hats at 120 BPM mixed in at the same peak level."""
    rng = np.random.default_rng(seed)
    total = sum(d for _, d, _ in seq)
    buf = np.zeros(int((total + 1) * rate))
    t, truth = 0.0, []
    for notes, dur, label in seq:
        starts = [t] if strike_every is None else list(np.arange(t, t + dur - 1e-6, strike_every))
        for s in starts:
            seg = min(strike_every or dur, t + dur - s)
            for m in notes:
                x = piano(m + detune_cents / 100.0, seg, rate, 0.25, rng)
                i = int(s * rate)
                buf[i:i + len(x)] += x[:len(buf) - i]
        truth.append((t, t + dur, label))
        t += dur
    buf = buf[:int(total * rate)]
    buf /= np.max(np.abs(buf))
    if drums:
        d = BB.synth_case("bed", 120, total, rate, style="drums", rng_seed=seed).audio[:len(buf)]
        buf = 0.6 * buf + 0.6 * d / np.max(np.abs(d))
    return buf.astype(np.float32), truth


def listen(audio, rate=RATE, hop=HOP, **kw):
    cs = CS.ChordSense(rate, hop, **kw)
    events = []
    for i in range(0, len(audio), hop):
        events.extend(cs.feed(audio[i:i + hop]))
    return cs, events


def chords_of(events):
    return [e for e in events if e["type"] == "chord"]


def label_at(chords, t):
    cur = None
    for e in chords:
        if e["t"] <= t:
            cur = e
    return cur


def frame_accuracy(chords, truth, settle=0.7):
    """Share of 50 ms samples, from `settle` s after each change to the next, whose decided label is right."""
    ok = tot = 0
    for t0, t1, label in truth:
        for t in np.arange(t0 + settle, t1, 0.05):
            e = label_at(chords, t)
            tot += 1
            ok += e is not None and e["name"] == label
    return ok / tot


# --- the eight chords, with drums on top ---------------------------------------------------------------------

@pytest.mark.parametrize("strike_every", [None, 0.5])
def test_eight_chords_named_correctly_with_drums_on_top(strike_every):
    audio, truth = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=strike_every)
    _, events = listen(audio)
    chords = chords_of(events)
    assert frame_accuracy(chords, truth) >= 0.95, [(e["name"], e["t"]) for e in chords]
    for t0, t1, label in truth:                       # every chord is named, in its own span
        assert any(e["name"] == label and t0 < e["t"] <= t1 for e in chords), (label, [e["name"] for e in chords])
    # what was named is a chord: root, quality and bass fields agree with the name
    c_e = next(e for e in chords if e["name"] == "C/E")
    assert (c_e["root"], c_e["quality"], c_e["bass"]) == (0, "maj", 4)
    b_dim = next(e for e in chords if e["name"] == "Bdim")
    assert (b_dim["root"], b_dim["quality"]) == (11, "dim")


def test_change_is_back_dated_to_the_attack():
    """t_change is the onset a beat-matcher wants: within ~60 ms of the real change, though the decision itself
    comes ~0.4 s later (the harmonic split waits out the drums on purpose)."""
    audio, truth = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=0.5)
    _, events = listen(audio)
    errs, lags = [], []
    for t0, t1, label in truth[1:]:
        e = next(e for e in chords_of(events) if e["name"] == label and t0 < e["t"] <= t1)
        errs.append(abs(e["t_change"] - t0))
        lags.append(e["t"] - t0)
    assert np.median(errs) < 0.06, errs
    assert max(lags) < 0.8, lags


@pytest.mark.parametrize("chord", ["G7", "Am"])
def test_a_held_chord_does_not_flicker(chord):
    """Eight seconds of one chord, re-struck on every beat under the drums: one chord event, no more."""
    audio, _ = render([(VOICINGS[chord], 8.0, chord)], strike_every=0.5)
    _, events = listen(audio)
    assert [e["name"] for e in chords_of(events)] == [chord]


def arpeggio(notes, secs, step=0.125, rate=RATE, ring=1.2, seed=5):
    """A broken chord over the drums: notes[0] is a bass struck every bar, the rest cycle in 8ths, each ringing
    `ring` seconds, with uneven velocities. The 7th comes and goes, the classic way to make a chord flicker."""
    rng = np.random.default_rng(seed)
    buf = np.zeros(int((secs + 3) * rate))
    t, k = 0.0, 0
    while t < secs:
        hits = [(notes[1 + k % (len(notes) - 1)], ring, 0.25 * (1 - 0.3 * rng.random()))]
        if k % 8 == 0:
            hits.append((notes[0], 16 * step, 0.3))
        for m, dur, vel in hits:
            x = piano(m, dur, rate, vel, rng)
            i = int(t * rate)
            buf[i:i + len(x)] += x[:len(buf) - i]
        t += step
        k += 1
    buf = buf[:int(secs * rate)]
    buf /= np.max(np.abs(buf))
    d = BB.synth_case("bed", 120, secs, rate, style="drums", rng_seed=seed).audio[:len(buf)]
    return (0.6 * buf + 0.6 * d / np.max(np.abs(d))).astype(np.float32)


@pytest.mark.parametrize("chord,notes", [("Am7", [45, 57, 60, 64, 67, 69]), ("G7", [43, 55, 59, 62, 65, 67])])
def test_an_arpeggio_does_not_flicker_between_its_colours(chord, notes):
    """Eight seconds of a broken seventh chord: it may be read as the triad until the 7th has sounded, then it
    stays the seventh chord (a thinner reading of the chord being held must hold for a second, not a moment)."""
    _, events = listen(arpeggio(notes, 8.0))
    names = [e["name"] for e in chords_of(events)]
    assert len(names) <= 2 and names[-1] == chord, names


def test_drums_alone_and_silence_read_no_chord():
    for style in ("drums", "sparse"):
        drums = BB.synth_case("d", 120, 10, RATE, style=style).audio
        _, events = listen(drums)
        assert all(e["name"] == "N" for e in chords_of(events)), (style, chords_of(events))
    _, events = listen(np.zeros(RATE * 4, dtype=np.float32))
    assert chords_of(events) == []
    # a chord, then the band drops out and the drums carry on: back to N
    chord, _ = render([(VOICINGS["Am"], 3.0, "Am")], drums=False)
    drums = BB.synth_case("d", 120, 7, RATE, style="drums").audio
    mix = np.concatenate([0.6 * chord + 0.5 * drums[:len(chord)], 0.5 * drums[len(chord):]]).astype(np.float32)
    _, events = listen(mix)
    assert [e["name"] for e in chords_of(events)] == ["Am", "N"]


def test_tuning_offset_is_estimated_and_removed():
    audio, truth = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=0.5, detune_cents=30.0)
    cs, events = listen(audio)
    assert abs(cs.tuning * 100 - 30.0) < 5.0
    assert frame_accuracy(chords_of(events), truth) >= 0.85


# --- key, numerals, resolution --------------------------------------------------------------------------------

DB = {"Db": [37, 49, 53, 56, 61], "Gb": [42, 49, 54, 58, 61], "Ab7": [44, 48, 51, 54, 60]}


def test_db_I_IV_V_I_reads_db_major_with_the_right_numerals():
    seq = [(DB[k], 2.0, k) for k in ("Db", "Gb", "Ab7", "Db")] * 2
    audio, _ = render(seq, strike_every=0.5)
    cs, events = listen(audio)
    keys = [e for e in events if e["type"] == "key"]
    assert keys and keys[0]["key"] == "Db major" and len(keys) == 1, keys
    assert cs.key == (1, "major")
    after = [e for e in chords_of(events) if e["t"] > keys[0]["t"]]
    assert [(e["name"], e["numeral"]) for e in after][-4:] == [("Db", "I"), ("Gb", "IV"), ("Ab7", "V7"),
                                                               ("Db", "I")]
    assert {e["numeral"] for e in after} == {"I", "IV", "V7"}
    assert keys[0]["numeral"] in ("I", "IV", "V7")   # the chord already sounding when the key landed
    funcs = {e["numeral"]: e["function"] for e in after}
    assert funcs == {"I": "tonic", "IV": "subdominant", "V7": "dominant"}
    tension = {e["numeral"]: e["tension"] for e in after}
    assert tension["V7"] > tension["IV"] > tension["I"]
    res = [e for e in events if e["type"] == "resolution"]
    assert len(res) == 2 and all(r["numeral"] == "I" and r["from"] > r["to"] + 0.15 for r in res), res


def test_roman_numerals_and_functions():
    C, A = 0, 9
    table = [
        ((C, "maj", None, C, "major"), ("I", "", "tonic")),
        ((5, "maj", None, C, "major"), ("IV", "", "subdominant")),
        ((7, "7", None, C, "major"), ("V7", "", "dominant")),
        ((9, "min", None, C, "major"), ("vi", "", "tonic")),
        ((2, "m7", None, C, "major"), ("ii7", "", "subdominant")),
        ((11, "dim", None, C, "major"), ("vii\u00b0", "", "dominant")),
        ((10, "maj", None, C, "major"), ("bVII", "", "borrowed")),
        ((8, "maj", None, C, "major"), ("bVI", "", "borrowed")),
        ((5, "min", None, C, "major"), ("iv", "", "borrowed")),
        ((2, "maj", None, C, "major"), ("V/V", "", "secondary dominant")),
        ((2, "7", None, C, "major"), ("V7/V", "", "secondary dominant")),
        ((9, "7", None, C, "major"), ("V7/ii", "", "secondary dominant")),
        ((4, "maj", None, C, "major"), ("V/vi", "", "secondary dominant")),
        ((C, "7", None, C, "major"), ("V7/IV", "", "secondary dominant")),
        ((1, "maj", None, C, "major"), ("bII", "", "neapolitan")),
        ((C, "maj", 4, C, "major"), ("I", "6", "tonic")),
        ((C, "maj", 7, C, "major"), ("I", "64", "tonic")),
        ((7, "7", 11, C, "major"), ("V7", "65", "dominant")),
        ((7, "7", 5, C, "major"), ("V7", "42", "dominant")),
        ((A, "min", None, A, "minor"), ("i", "", "tonic")),
        ((4, "maj", None, A, "minor"), ("V", "", "dominant")),
        ((4, "7", None, A, "minor"), ("V7", "", "dominant")),
        ((C, "maj", None, A, "minor"), ("III", "", "tonic")),
        ((7, "maj", None, A, "minor"), ("VII", "", "dominant")),
        ((2, "min", None, A, "minor"), ("iv", "", "subdominant")),
        ((2, "sus4", None, A, "minor"), ("IVsus4", "", "subdominant")),
        ((11, "maj", None, A, "minor"), ("V/V", "", "secondary dominant")),
        ((2, "maj", None, A, "minor"), ("IV", "", "borrowed")),          # the Dorian IV
        ((A, "maj", None, A, "minor"), ("I", "", "borrowed")),          # a Picardy third
        ((10, "7", None, C, "major"), ("bVII7", "", "borrowed")),       # the backdoor dominant
        ((11, "5", None, C, "major"), ("VII5", "", "chromatic")),
    ]
    for args, want in table:
        assert CS.roman(*args) == want, (args, CS.roman(*args), want)


def test_names_follow_the_key_spelling():
    assert CS.chord_name(1, "maj", None, (1, "major")) == "Db"
    assert CS.chord_name(1, "maj", None, (9, "major")) == "C#"
    assert CS.chord_name(6, "7", 10, (1, "major")) == "Gb7/Bb"
    assert CS.key_name(1, "major") == "Db major" and CS.key_name(1, "minor") == "C# minor"


# --- the notes path: the same theory, played -------------------------------------------------------------------

def play(chords, beat=0.5, vel=90):
    """Block chords, each held for its beats: [(midi notes, beats)] -> note events."""
    evs, t = [], 0.0
    for notes, beats in chords:
        for m in notes:
            evs.append({"t": t, "note": m, "vel": vel})
        t += beats * beat
        for m in notes:
            evs.append({"t": t - 0.01, "note": m, "vel": 0})
    return evs, t


def test_notes_name_the_same_chords_as_audio():
    evs, end = play([(VOICINGS[k], 4) for k in EIGHT])
    cs = CS.ChordSense()
    names = [e["name"] for e in chords_of(cs.feed_notes(evs, now=end + 0.5))]
    assert [n for n in names if n != "N"] == EIGHT, names


def test_notes_db_progression_key_numerals_and_sustain_pedal():
    prog = [(DB[k], 4) for k in ("Db", "Gb", "Ab7", "Db")] * 2
    evs, end = play(prog)
    cs = CS.ChordSense()
    out = cs.feed_notes(evs, now=end + 0.5)
    assert cs.key == (1, "major")
    tail = [(e["name"], e["numeral"]) for e in chords_of(out) if e["numeral"]][-4:]
    assert tail == [("Db", "I"), ("Gb", "IV"), ("Ab7", "V7"), ("Db", "I")]
    # the sustain pedal keeps released keys sounding; pedal up lets them ring out
    cs2 = CS.ChordSense()
    seq = [{"t": 0.0, "sustain": 127}] + [{"t": 0.0, "note": m, "vel": 90} for m in VOICINGS["Am"]]
    seq += [{"t": 0.1, "note": m, "vel": 0} for m in VOICINGS["Am"]]
    first = cs2.feed_notes(seq, now=1.5)
    assert [e["name"] for e in chords_of(first)] == ["Am"]
    assert cs2.snapshot()["chord"]["name"] == "Am"
    later = cs2.feed_notes([{"t": 1.6, "sustain": 0}], now=4.0)
    assert [e["name"] for e in chords_of(later)] == ["N"]


def test_a_repeated_note_over_moving_chords_is_a_pedal_and_tension_rises():
    """A high Db struck every beat while the harmony walks I-IV-vi-V under it: a pedal on Db, and the longer it
    holds, the higher the tension on the very same chord."""
    beat = 0.6
    walk = [[37, 53, 56], [42, 54, 58], [46, 53, 58], [44, 51, 60]]       # Db, Gb, Bbm, Ab under the pedal
    evs, t = [], 0.0
    for bar in range(12):
        chord = walk[bar % 4]
        for b in range(4):
            evs.append({"t": t, "note": 73, "vel": 80})
            evs.append({"t": t + 0.2, "note": 73, "vel": 0})
            if b == 0:
                evs += [{"t": t, "note": m, "vel": 85} for m in chord]
            if b == 3:
                evs += [{"t": t + beat - 0.02, "note": m, "vel": 0} for m in chord]
            t += beat
    evs.sort(key=lambda e: (e["t"], e["vel"] > 0))
    cs = CS.ChordSense()
    tension_on_ab = []
    out = []
    i = 0
    for k in range(int(t / 0.1) + 1):
        now = k * 0.1
        chunk = []
        while i < len(evs) and evs[i]["t"] <= now:
            chunk.append(evs[i])
            i += 1
        out += cs.feed_notes(chunk, now=now)
        snap = cs.snapshot()
        if snap["chord"]["root"] == 8:
            tension_on_ab.append((now, snap["tension"]))
    pedals = [e for e in out if e["type"] == "pedal" and e["on"]]
    assert pedals and pedals[0]["note"] == "Db" and pedals[0]["chords"] >= 3, pedals
    early = [v for tt, v in tension_on_ab if tt < 10]
    late = [v for tt, v in tension_on_ab if tt > 22]
    assert early and late and np.mean(late) > np.mean(early) + 0.1, (np.mean(early), np.mean(late))


def test_one_source_per_instance_and_the_snapshot_contract():
    cs = CS.ChordSense()
    cs.feed(np.zeros(HOP, dtype=np.float32))
    with pytest.raises(ValueError):
        cs.feed_notes([{"t": 0.0, "note": 60, "vel": 90}])
    audio, _ = render([(VOICINGS["G7"], 2.0, "G7")])
    cs, _ = listen(audio)
    snap = cs.snapshot()
    assert set(snap) >= {"t", "chord", "key", "tension", "dissonance", "pedal", "pulse", "chroma", "notes", "bass",
                         "energy", "tuning_cents"}
    assert snap["chord"]["name"] == "G7" and snap["chord"]["changed"] is False
    assert len(snap["chroma"]) == len(snap["notes"]) == len(snap["bass"]) == 12
    assert 0.0 <= snap["tension"] <= 1.0 and 0.0 <= snap["pulse"] <= 1.0
    # stereo blocks and odd block sizes are fine
    stereo = np.stack([audio, audio], axis=1)
    cs2 = CS.ChordSense(RATE, HOP)
    names = [e["name"] for i in range(0, len(stereo), 700) for e in cs2.feed(stereo[i:i + 700])
             if e["type"] == "chord"]
    assert names == ["G7"]


# --- speed and the licence firewall ---------------------------------------------------------------------------

def test_runs_well_over_20x_real_time_at_48k_hop_512():
    audio, _ = render([(VOICINGS[k], 2.0, k) for k in EIGHT] * 2, strike_every=0.5)
    cs = CS.ChordSense(RATE, HOP)
    per_block = []
    t0 = time.process_time()
    for i in range(0, len(audio), HOP):
        b0 = time.perf_counter()
        cs.feed(audio[i:i + HOP])
        per_block.append(time.perf_counter() - b0)
    cpu = time.process_time() - t0
    speed = (len(audio) / RATE) / max(cpu, 1e-9)
    assert speed >= 20.0, f"{speed:.1f}x real time"
    # bounded work per call: even the slow blocks (the ones that run an analysis frame) finish far inside the
    # block's own duration, so an audio callback is never held up
    p99 = float(np.percentile(per_block, 99))
    assert p99 < 0.5 * HOP / RATE, f"p99 block {p99 * 1000:.2f} ms against a {HOP / RATE * 1000:.1f} ms block"


def test_chordsense_keeps_the_licence_firewall():
    """Same rule as the beat trackers: stdlib, numpy and scipy only, and no door past the audio it is fed."""
    from test_keylab_beat_licence_firewall import reach_violations, violations
    src = (Path(CS.__file__)).read_text(encoding="utf-8")
    assert not violations(src)
    assert not reach_violations(src)


# --- Daniel's Joy to the World ---------------------------------------------------------------------------------

_SCRATCH = ("C:/Users/L5/AppData/Local/Temp/claude/E--/88c7ecac-d149-46ae-8e9a-612d5ba3736a/scratchpad/"
            "joy_notes.json")
JOY_BPM = 100.0
BEAT = 60.0 / JOY_BPM


def _joy_path():
    root = Path(__file__).resolve().parents[1]
    for p in (os.environ.get("KEYLAB_JOY_NOTES"), root / "state" / "arsenal" / "keylab" / "joy_notes.json",
              _SCRATCH):
        if p and Path(p).is_file():
            return Path(p)
    return None


@pytest.fixture(scope="module")
def joy():
    p = _joy_path()
    if p is None:
        pytest.skip("Daniel's Joy to the World notes are not on this machine (private, never committed)")
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["notes"], int(d["ppq"])


def _timeline(cs, feed, total_s, step=0.1):
    """Run a source in `step` chunks; return (events, [(t, snapshot)])."""
    events, snaps = [], []
    for k in range(1, int(total_s / step) + 2):
        events += feed(k * step)
        snaps.append((k * step, cs.snapshot()))
    return events, snaps


def _key_share(events, key, t_from, t_end):
    keys = [(e["t"], e["key"]) for e in events if e["type"] == "key"]
    share = 0.0
    for i, (t, k) in enumerate(keys):
        a, b = max(t, t_from), min(keys[i + 1][0] if i + 1 < len(keys) else t_end, t_end)
        if k == key and b > a:
            share += b - a
    return share / (t_end - t_from)


def _passage(snaps, b0, b1):
    return [s for t, s in snaps if b0 * BEAT <= t < b1 * BEAT]


def _check_joy_story(events, snaps, end):
    assert _key_share(events, "Db major", 60 * BEAT, end) >= 0.8
    assert [e["key"] for e in events if e["type"] == "key"][-1] == "Db major"
    final, opening = _passage(snaps, 476, 588), _passage(snaps, 0, 112)
    # the pedal: Db, held through the final passage
    on_db = np.mean([s["pedal"] is not None and s["pedal"]["note"] == "Db" for s in final])
    assert on_db >= 0.5, on_db
    assert any(e["type"] == "pedal" and e["on"] and e["note"] == "Db" and 470 * BEAT <= e["t"] <= 588 * BEAT
               for e in events)
    # ... and the tension it builds: the final passage sits higher than the opening
    t_final = np.mean([s["tension"] for s in final])
    t_open = np.mean([s["tension"] for s in opening])
    assert t_final > t_open + 0.05, (t_open, t_final)
    return t_open, t_final


def test_joy_notes_db_major_and_the_pedal_at_the_end(joy):
    notes, ppq = joy
    evs = CS.score_to_events(notes, ppq, JOY_BPM)
    end = evs[-1]["t"]
    cs = CS.ChordSense()
    pos = [0]

    def feed(now):
        chunk = []
        while pos[0] < len(evs) and evs[pos[0]]["t"] <= now:
            chunk.append(evs[pos[0]])
            pos[0] += 1
        return cs.feed_notes(chunk, now=now)

    events, snaps = _timeline(cs, feed, end)
    _check_joy_story(events, snaps, end)
    # the harmony is mostly IN the key: time-weighted, most named chords have diatonic roots
    chords = [e for e in chords_of(events) if e["root"] is not None]
    diatonic = {1, 3, 5, 6, 8, 10, 0}
    share = np.mean([e["root"] in diatonic for e in chords if e["t"] > 60 * BEAT])
    assert share >= 0.85, share


def render_score(notes, ppq, bpm, rate, ring_s=0.6, seed=3):
    """Additive piano render of a score (the same partials as `piano`), each note ringing out after release."""
    rng = np.random.default_rng(seed)
    t0 = min(n["pos"] for n in notes)
    sec = 60.0 / (bpm * ppq)
    end = max((n["pos"] - t0 + n["len"]) * sec for n in notes) + 3.0
    buf = np.zeros(int(end * rate))
    for n in notes:
        dur = max(0.05, n["len"] * sec)
        f0 = 440.0 * 2 ** ((n["key"] - 69) / 12)
        t = np.arange(int((dur + 4 * ring_s) * rate)) / rate
        x = np.zeros(len(t))
        for h in range(1, 11):
            fh = h * f0 * np.sqrt(1 + 2e-4 * h * h)
            if fh > 0.45 * rate:
                break
            x += np.sin(2 * np.pi * fh * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t * h ** 0.6 / 2.0) / h ** 1.1
        env = np.where(t < dur, 1.0, np.exp(-(t - dur) / ring_s)) * np.minimum(1.0, t / 0.003)
        i = int((n["pos"] - t0) * sec * rate)
        seg = n.get("vel", 100) / 127.0 * x * env
        buf[i:i + len(seg)] += seg[:len(buf) - i]
    return (0.8 * buf / np.max(np.abs(buf))).astype(np.float32)


def test_joy_audio_render_finds_db_major_and_a_sensible_chord_sequence(joy):
    notes, ppq = joy
    rate = 22050
    audio = render_score(notes, ppq, JOY_BPM, rate)
    cs = CS.ChordSense(rate, HOP)
    pos = [0]
    step = int(0.1 * rate) // HOP * HOP

    def feed(_now):
        block = audio[pos[0]:pos[0] + step]
        pos[0] += step
        return cs.feed(block) if len(block) else []

    end = len(audio) / rate
    events, snaps = _timeline(cs, feed, end, step=step / rate)
    _check_joy_story(events, snaps, end - 3.0)
    chords = [e for e in chords_of(events) if e["root"] is not None and e["t"] > 60 * BEAT]
    # sensible: the tonic, subdominant and dominant families dominate, and the I / IV / V roots are all there
    roots = [e["root"] for e in chords]
    assert np.mean([r in {1, 3, 5, 6, 8, 10, 0} for r in roots]) >= 0.85
    assert {1, 6, 8} <= set(roots)
    named = {e["numeral"] for e in chords}
    assert {"I", "IV", "V"} & named or {"I5", "IV5", "V5"} & named
    # audio and keys agree: the same chord root on most beats
    keys = CS.ChordSense()
    by_notes = chords_of(keys.feed_notes(CS.score_to_events(notes, ppq, JOY_BPM), now=end))
    agree = tot = 0
    for b in np.arange(4, 588, 1.0):
        n = label_at(by_notes, b * BEAT)
        if n is None or n["root"] is None:
            continue
        a = label_at(chords_of(events), b * BEAT + 0.45)          # the audio decision lands ~0.45 s later
        tot += 1
        agree += a is not None and a["root"] == n["root"]
    assert agree / tot >= 0.65, agree / tot
