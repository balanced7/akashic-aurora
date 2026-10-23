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


def test_borrowed_and_chromatic_chords_are_spelled_by_their_degree():
    """Round 2: inside C major or A minor, chromatic chords came out sharp (Bb as A#, Eb as D#, Ab as G#: a sharp
    key's spelling for every pitch). A root is now spelled by the degree it sits on: borrowed and chromatic roots
    are lowered degrees (bII, bIII, bV, bVI, bVII), leading-tone diminished chords and minor's raised 3rd / 6th /
    7th are sharps, a slash bass by its interval above the root, in every key."""
    C, Am = (0, "major"), (9, "minor")
    assert [CS.chord_name(r, q, None, C) for r, q in ((10, "maj"), (3, "maj"), (8, "maj"), (1, "maj"), (5, "min"),
                                                       (10, "7"), (6, "7"))] == ["Bb", "Eb", "Ab", "Db", "Fm",
                                                                                 "Bb7", "Gb7"]
    assert [CS.chord_name(r, q, None, C) for r, q in ((1, "dim"), (3, "dim"), (6, "dim"), (8, "dim"), (2, "7"),
                                                       (4, "7"), (9, "7"))] == ["C#dim", "D#dim", "F#dim", "G#dim",
                                                                                "D7", "E7", "A7"]
    assert [CS.chord_name(r, q, None, Am) for r, q in ((10, "maj"), (5, "maj"), (0, "maj"), (7, "maj"), (8, "dim"),
                                                        (4, "7"), (6, "min"), (1, "min"))] == \
        ["Bb", "F", "C", "G", "G#dim", "E7", "F#m", "C#m"]
    assert CS.chord_name(2, "maj", 6, C) == "D/F#" and CS.chord_name(8, "maj", 0, C) == "Ab/C"
    assert CS.chord_name(7, "maj", 0, C) == "G/C" and CS.chord_name(10, "maj", 2, (7, "major")) == "Bb/D"
    # every key: one accidental at most (bVII of Db major is B, not Cb), and the pedal notes follow the same rules
    for tonic in range(12):
        for mode in ("major", "minor"):
            assert all(len(CS.chord_name(r, "maj", None, (tonic, mode))) <= 2 for r in range(12))
    assert CS.spell_note(1, (1, "major")) == "Db" and CS.spell_note(10, C) == "Bb" and CS.spell_note(6, C) == "F#"
    # heard: C - Bb - F - C in audio names the Bb as Bb
    audio, _ = render([([36, 48, 52, 55, 60], 2.0, ""), ([46, 50, 53, 58, 62], 2.0, ""),
                       ([41, 53, 57, 60, 65], 2.0, ""), ([36, 48, 52, 55, 60], 2.0, "")] * 3, strike_every=0.5)
    cs, events = listen(audio)
    assert cs.key == (0, "major")
    names = {e["name"] for e in chords_of(events) if e["key"] == "C major"}
    assert "Bb" in names and "A#" not in names, names


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
    assert pedals[0]["clash"] >= 0.15, pedals            # it is NOT a tone of the Ab under it: a real clash
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


# --- verifier round 1 (2026-10-23): each pin failed on the merged engine (baa47b0a) and passes now ----------------

def test_a_non_finite_sample_does_not_silence_the_analysis():
    """One NaN or Inf block used to poison the anti-alias filter's state for good: every frame after it was NaN
    and no event ever came again. A non-finite sample is now heard as silence (and an absurd one is clipped)."""
    cs = CS.ChordSense(RATE, HOP)
    for bad in (np.nan, np.inf, -np.inf, 1e300):
        cs.feed(np.full(HOP, bad, dtype=np.float64))
    audio, truth = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=0.5)
    events = []
    for i in range(0, len(audio), HOP):
        events.extend(cs.feed(audio[i:i + HOP]))
    names = [e["name"] for e in chords_of(events)]
    assert [n for n in names if n != "N"] == EIGHT, names
    snap = cs.snapshot()
    assert all(np.isfinite(snap["chroma"])) and np.isfinite(snap["tension"])


def loop_events(names, reps=6, beat=0.5, beats=4):
    """A plain loop of block chords on the keys, every voicing sharing the C4 (the common tone)."""
    v = {"Am": [45, 57, 60, 64], "F": [41, 57, 60, 65], "C": [36, 55, 60, 64]}
    evs, end = play([(v[n], beats) for n in names] * reps, beat=beat)
    return evs, end, v


@pytest.mark.parametrize("names", [["Am", "F", "C"], ["C", "Am", "F", "C"]])
def test_a_common_tone_of_a_plain_loop_is_not_a_pedal(names):
    """The C of Am-F-C sounds through every chord, but it is a tone of every chord: it never clashes, so it is not
    a pedal, and the loop's tension stays flat however often it repeats (it used to climb 0.17 -> 0.55)."""
    evs, end, v = loop_events(names)
    cs = CS.ChordSense()
    out, tension = [], []
    pos = 0
    for k in range(int((end + 0.5) / 0.1) + 1):
        now = k * 0.1
        chunk = []
        while pos < len(evs) and evs[pos]["t"] <= now:
            chunk.append(evs[pos])
            pos += 1
        out += cs.feed_notes(chunk, now=now)
        tension.append((now, cs.snapshot()["tension"]))
    assert not [e for e in out if e["type"] == "pedal"], [e for e in out if e["type"] == "pedal"]
    loop_s = len(names) * 2.0
    per_rep = [np.mean([x for t, x in tension if r * loop_s <= t < (r + 1) * loop_s]) for r in range(1, 6)]
    assert max(per_rep) - min(per_rep) < 0.03, per_rep
    # the same loop heard as audio, re-struck on every beat over the drums
    audio, _ = render([(v[n], 2.0, n) for n in names] * 6, strike_every=0.5)
    _, events = listen(audio)
    assert not [e for e in events if e["type"] == "pedal"]


def _pedal_timeline(evs, end, step=0.1):
    """Feed note events in `step` chunks; return (events, [(t, snapshot)])."""
    cs = CS.ChordSense()
    out, snaps, pos = [], [], 0
    for k in range(int((end + 0.5) / step) + 1):
        now = k * step
        chunk = []
        while pos < len(evs) and evs[pos]["t"] <= now:
            chunk.append(evs[pos])
            pos += 1
        out += cs.feed_notes(chunk, now=now)
        snaps.append((now, cs.snapshot()))
    return out, snaps


# voice-led loops whose common tones run through most (not all) of the chords
LOOP_V = {"Dm": [38, 57, 62, 65], "Bb": [46, 58, 62, 65], "F": [41, 57, 60, 65], "C": [36, 55, 60, 64],
          "Em": [40, 55, 59, 64], "Am": [45, 57, 60, 64], "G": [43, 55, 59, 62], "Dm7": [38, 57, 60, 65],
          "G7": [43, 55, 59, 65]}


@pytest.mark.parametrize("names,beats", [(["C", "G", "Am", "Em", "F", "C", "F", "G"], 2), (["Am", "F", "C", "G"], 2),
                                         (["C", "Am", "F", "Dm7", "G7"], 2), (["C", "Am", "F", "Dm7", "G7"], 1),
                                         (["Dm", "Bb", "F"], 4), (["C", "Em", "Am"], 4)])
def test_no_pedal_on_plain_progressions(names, beats):
    """Round 2: Pachelbel, Am-F-C-G and C-Am-F-Dm7-G7 (one or two beats a chord) read a false pedal in audio
    (G, E, C: a previous chord's tail ringing over the next counted as a held, clashing note) and C-Am-F-Dm7-G7 at
    one beat a chord on the keys too. A pedal must now be really HELD (struck, or sounding fresh: not a tail) and
    sound in nearly every chord span it runs through; the note of the next chord arriving while the label still
    names the last one does not clash."""
    evs, end = play([(LOOP_V[n], beats) for n in names] * 6, beat=0.5)
    out, _ = _pedal_timeline(evs, end)
    assert not [e for e in out if e["type"] == "pedal"], [e for e in out if e["type"] == "pedal"]
    audio, _ = render([(LOOP_V[n], beats * 0.5, n) for n in names] * 6, strike_every=0.5, seed=21)
    _, events = listen(audio)
    assert not [e for e in events if e["type"] == "pedal"], [(e["note"], e["t"]) for e in events if e["type"] == "pedal"]


@pytest.mark.parametrize("which", ["Db over Db-Gb-Bbm-Ab", "A over Am-G-F-E"])
def test_a_pedal_the_chord_name_absorbs_is_still_found(which):
    """Round 2: a held note the chord name absorbs (Ab + a held Db reads Absus4, G + A Gadd9, E + A Esus4) never
    clashed, so the re-struck Db over Db-Gb-Bbm-Ab (Db also voiced inside Gb and Bbm) was lost in audio and flapped
    on and off on the keys. A held note that is only the chord's colour (the 4th of sus4, the 7th of a seventh) now
    clashes: the pedal is found on both ears, once, and stays."""
    if which.startswith("Db"):
        prog, pc = [[37, 49, 53, 56, 73], [42, 54, 58, 61, 73], [46, 53, 58, 61, 73], [44, 56, 60, 63, 73]], 1
    else:
        prog, pc = [[45, 57, 60, 64, 81], [43, 55, 59, 62, 81], [41, 53, 57, 60, 81], [40, 52, 56, 59, 81]], 9
    evs, end = play([(c, 4) for c in prog] * 4, beat=0.5)
    out, snaps = _pedal_timeline(evs, end)
    on = [e for e in out if e["type"] == "pedal" and e["on"]]
    assert len(on) == 1 and on[0]["pc"] == pc, [(e["note"], e["t"], e["on"]) for e in out if e["type"] == "pedal"]
    later = [s["pedal"] is not None and s["pedal"]["pc"] == pc for t, s in snaps if t >= on[0]["t"] and t < end]
    assert np.mean(later) >= 0.95, np.mean(later)
    audio, _ = render([(c, 2.0, "") for c in prog] * 4, strike_every=0.5, seed=6)
    _, events = listen(audio)
    on = [e for e in events if e["type"] == "pedal" and e["on"]]
    assert len(on) == 1 and on[0]["pc"] == pc, [(e["note"], e["t"], e["on"]) for e in events if e["type"] == "pedal"]


def _noise(kind, secs, rng):
    from scipy.signal import butter, istft, sosfilt, stft
    n = int(secs * RATE)
    if kind == "white":
        return 0.3 * rng.standard_normal(n)
    if kind == "pink":
        spec = np.fft.rfft(rng.standard_normal(n))
        spec[1:] /= np.sqrt(np.fft.rfftfreq(n, 1.0 / RATE)[1:])
        spec[0] = 0.0
        x = np.fft.irfft(spec, n)
        return 0.3 * x / np.std(x)
    if kind == "riser":                                  # a noise band sweeping 200 Hz -> 8 kHz, swelling
        f, tt, z = stft(rng.standard_normal(n), RATE, nperseg=1024)
        fc = 200.0 * 40.0 ** (tt / tt[-1])
        gain = np.exp(-0.5 * ((np.log2(np.maximum(f, 1.0))[:, None] - np.log2(fc)[None, :]) / 0.6) ** 2)
        x = istft(z * gain, RATE, nperseg=1024)[1][:n]
        return 0.5 * x * np.linspace(0.2, 1.0, len(x)) / np.max(np.abs(x))
    x = np.zeros(n)
    if kind == "crackle":                                # vinyl: sparse clicks over a faint hiss
        x += 0.01 * rng.standard_normal(n)
        for p in rng.integers(0, n - 200, rng.poisson(40 * secs)):
            m = int(rng.integers(20, 200))
            x[p:p + m] += rng.uniform(-1, 1) * np.exp(-np.arange(m) / (m / 4)) * rng.standard_normal(m) * 0.8
        return sosfilt(butter(2, [300, 9000], "bandpass", fs=RATE, output="sos"), x)
    if kind == "applause":                               # many overlapping band-limited claps
        for p in rng.integers(0, n - 2000, rng.poisson(60 * secs)):
            m = int(rng.integers(300, 1500))
            fc = rng.uniform(800, 3000)
            burst = sosfilt(butter(2, [fc / 1.6, fc * 1.6], "bandpass", fs=RATE, output="sos"),
                            rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 5)))
            x[p:p + m] += rng.uniform(0.2, 1.0) * burst
        return 0.5 * x / np.max(np.abs(x))
    # loops in 16ths at 120 BPM: noise hats (a gentle 2 kHz high-pass reaches well into the chroma band), a shaker
    # (band-passed, soft attack) and 808-style metallic hats (six square oscillators: SINUSOIDAL partials)
    t, k = 0.0, 0
    tt = np.arange(int(0.08 * RATE)) / RATE
    metal = sum(np.sign(np.sin(2 * np.pi * 2 * f0 * tt)) for f0 in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
    metal = sosfilt(butter(2, 800, "highpass", fs=RATE, output="sos"), metal)
    hp = butter(2, 2000, "highpass", fs=RATE, output="sos")
    bp = butter(2, [1000, 9000], "bandpass", fs=RATE, output="sos")
    while t < secs:
        if kind == "hats":
            hit = sosfilt(hp, rng.standard_normal(len(tt))) * np.exp(-tt / (0.02 if k % 4 else 0.05))
        elif kind == "shaker":
            hit = sosfilt(bp, rng.standard_normal(len(tt))) * np.minimum(1, tt / 0.02) * np.exp(-tt / 0.03)
        else:
            hit = metal * np.exp(-tt / (0.02 if k % 4 else 0.05))
        i = int(t * RATE)
        x[i:i + len(hit)] += hit[:n - i] * (1.0 if k % 2 == 0 else 0.6)
        t += 0.125
        k += 1
    return 0.6 * x / np.max(np.abs(x))


def chord_time(chords, secs):
    """Share of 20 ms steps over `secs` at which a chord (not N) is the decided label."""
    on = [label_at(chords, t) for t in np.arange(0.0, secs, 0.02)]
    return float(np.mean([e is not None and e["root"] is not None for e in on]))


@pytest.mark.parametrize("kind", ["white", "pink", "riser", "crackle", "applause", "hats", "shaker", "hats808"])
def test_noise_is_not_named_as_chords(kind):
    """Noise used to read as chords (its tonality sat at ~0.67, over the 0.55 bar, and N had no hold): pink noise
    was a chord 65 % of the time, a riser 47 %, white noise 16 %. Now a peak must stand clear of the spectrum
    around it to count as tonal, and N <-> chord has hysteresis."""
    x = _noise(kind, 12.0, np.random.default_rng(3)).astype(np.float32)
    _, events = listen(x)
    assert chord_time(chords_of(events), 12.0) <= 0.02, [e["name"] for e in chords_of(events)]


def test_a_chord_under_a_shaker_holds_and_the_shaker_alone_is_n():
    """The hysteresis both ways: a chord keeps its name under a dense shaker loop; when the chord stops and the
    shaker plays on, the label falls to N and stays there."""
    chord, _ = render([(VOICINGS["Am"], 4.0, "Am")], strike_every=1.0, drums=False)
    shaker = _noise("shaker", 10.0, np.random.default_rng(5))
    mix = 0.5 * shaker
    mix[:len(chord)] += 0.6 * chord
    _, events = listen(mix.astype(np.float32))
    names = [(e["name"], e["t"]) for e in chords_of(events)]
    assert [n for n, _ in names] == ["Am", "N"], names
    assert names[1][1] < 5.0, names


def random_set(n=24, seed=11):
    """Random chords: any root, eight qualities, the root in the bass and the chord in a random inversion above."""
    rng = np.random.default_rng(seed)
    quals = ["maj", "min", "7", "maj7", "m7", "sus2", "sus4", "dim"]
    seq = []
    for _ in range(n):
        root, q = int(rng.integers(12)), quals[int(rng.integers(len(quals)))]
        upper = sorted({52 + ((root + i - 52) % 12) for i in CS.QUALITIES[q][0]})
        inv = int(rng.integers(len(upper)))
        seq.append(([36 + root] + sorted(upper[inv:] + [u + 12 for u in upper[:inv]]), 2.0, (root, q)))
    return seq


def saw(midi, secs, rate=RATE):
    """A band-limited sawtooth: every harmonic at 1/h, the brightest bass there is."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(secs * rate)) / rate
    x = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, int(0.45 * rate / f0) + 1))
    return x * np.minimum(1.0, t / 0.005) * np.clip((secs - t) / 0.05, 0.0, 1.0)


def rq_accuracy(chords, truth, settle=0.7):
    """(full, root): the share of 50 ms samples after `settle` whose decided (root, quality) / root is right."""
    full = root = tot = 0
    for t0, t1, (r, q) in truth:
        for t in np.arange(t0 + settle, t1, 0.05):
            e = label_at(chords, t)
            tot += 1
            full += e is not None and (e["root"], e["quality"]) == (r, q)
            root += e is not None and e["root"] == r
    return full / tot, root / tot


@pytest.mark.parametrize("bass_db", [None, 6, 12])
def test_random_chords_and_a_loud_bright_bass(bass_db):
    """24 random chords over the drums: >= 95 % (root, quality) / >= 98 % root on their own. Under a sawtooth bass
    playing the root 6 or 12 dB above them, the bass used to leak into the harmony (maj7, m7 and sus2 collapsed to
    power chords: 66 % at +6 dB, 12 % at +12); the bass note now leaves the harmony with its harmonic series."""
    seq = random_set()
    audio, truth = render([(notes, d, "") for notes, d, _ in seq], drums=False)
    truth = [(t0, t1, rq) for (t0, t1, _), (_, _, rq) in zip(truth, seq)]
    mix = audio.astype(np.float64)
    if bass_db is not None:
        bass = np.concatenate([saw(36 + r, d) for _, d, (r, _) in seq])[:len(mix)]
        mix = mix + bass * np.sqrt(np.mean(mix ** 2) / np.mean(bass ** 2)) * 10 ** (bass_db / 20)
        mix /= np.max(np.abs(mix))
    drums = BB.synth_case("bed", 120, len(mix) / RATE, RATE, style="drums", rng_seed=1).audio[:len(mix)]
    mix = (0.6 * mix + 0.6 * drums / np.max(np.abs(drums))).astype(np.float32)
    _, events = listen(mix)
    full, root = rq_accuracy(chords_of(events), truth)
    if bass_db is None:
        assert full >= 0.95 and root >= 0.98, (full, root)
    else:
        assert full >= 0.85 and root >= 0.95, (full, root)


def square(midi, secs, rate=RATE):
    """A band-limited square wave: the odd harmonics at 1/h, no even ones at all."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(secs * rate)) / rate
    x = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, int(0.45 * rate / f0) + 1, 2))
    return x * np.minimum(1.0, t / 0.005) * np.clip((secs - t) / 0.05, 0.0, 1.0)


def bass_mix(seq, wave, lowest, db, rate=RATE):
    """The random set's voices WITHOUT their bass note, and a bass instrument playing the root from MIDI `lowest`
    up (28 = E1, 41 Hz .. D#2; 36 = C2 .. B2), `db` above the voices, over the drums."""
    audio, truth = render([(notes[1:], d, "") for notes, d, _ in seq], drums=False)
    truth = [(t0, t1, rq) for (t0, t1, _), (_, _, rq) in zip(truth, seq)]
    mix = audio.astype(np.float64)
    bass = np.concatenate([wave(lowest + (r - lowest) % 12, d, rate) for _, d, (r, _) in seq])[:len(mix)]
    mix = mix + bass * np.sqrt(np.mean(mix ** 2) / np.mean(bass ** 2)) * 10 ** (db / 20)
    mix /= np.max(np.abs(mix))
    drums = BB.synth_case("bed", 120, len(mix) / rate, rate, style="drums", rng_seed=1).audio[:len(mix)]
    return (0.6 * mix + 0.6 * drums / np.max(np.abs(drums))).astype(np.float32), truth


@pytest.mark.parametrize("wave", ["saw", "square"])
@pytest.mark.parametrize("lowest", [28, 36])
@pytest.mark.parametrize("db", [6, 12])
def test_a_low_or_hollow_bass_keeps_the_root(wave, lowest, db):
    """Round 2: a sub bass under C2 (E1-D#2, 41-78 Hz: where a hardstyle or house bass lives) used to be found only
    by its 2nd harmonic, its 3rd, 5th and 7th stayed in the harmony, and the root read N (43-53 % at +12 dB); a
    square bass (no even partials) fooled the one power law that took the bass's series out. The bass is now found
    from 39 Hz, its odd and even partials have a law each, and the voices are no longer explained away by the bass's
    own overtones. Root >= 95 % at +6 and +12 dB; (root, quality) >= 85 % at +6 dB."""
    audio, truth = bass_mix(random_set(), saw if wave == "saw" else square, lowest, db)
    _, events = listen(audio)
    full, root = rq_accuracy(chords_of(events), truth)
    assert root >= 0.95 and (db > 6 or full >= 0.85), (full, root)


def supersaw(midi, secs, rng, rate=RATE, voices=7, spread=0.25):
    """Seven saws detuned across +-spread semitones, each with its own phase: a trance / hardstyle lead chord."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(secs * rate)) / rate
    x = np.zeros(len(t))
    for v in range(voices):
        fd = f0 * 2 ** (spread * (2 * v / (voices - 1) - 1) / 12)
        ph = rng.uniform(0, 2 * np.pi)
        for h in range(1, int(6000 / fd) + 1):
            x += np.sin(2 * np.pi * h * fd * t + h * ph) / h
    return x * np.minimum(1.0, t / 0.01) * np.clip((secs - t) / 0.03, 0.0, 1.0)


def hardstyle(seq, bpm=150.0, rate=RATE, sub_db=6.0, kick_db=6.0, tail_hz=49.0, drive=4.0, seed=4):
    """seq [(root, quality, secs)]: supersaw chords from G3 up, a sub bass on the root at E1-D#2 (a sine and a
    little octave), a distorted four-on-the-floor kick whose tail sits at `tail_hz`, and the sidechain duck that
    pumps the chords and the sub under every kick. Levels are RMS against the chords."""
    rng = np.random.default_rng(seed)
    n = int(sum(d for _, _, d in seq) * rate)
    chords, sub, truth, t = np.zeros(n), np.zeros(n), [], 0.0
    for root, q, d in seq:
        i0 = int(t * rate)
        tones = sorted(55 + ((root + iv - 55) % 12) for iv in CS.QUALITIES[q][0])
        for m in tones + [tones[0] + 12]:
            x = supersaw(m, d, rng)
            chords[i0:i0 + len(x)] += x[:n - i0]
        f0 = 440.0 * 2 ** ((28 + (root - 4) % 12 - 69) / 12)
        tt = np.arange(min(int(d * rate), n - i0)) / rate
        sub[i0:i0 + len(tt)] = ((np.sin(2 * np.pi * f0 * tt) + 0.15 * np.sin(4 * np.pi * f0 * tt))
                                * np.minimum(1, tt / 0.01) * np.clip((d - tt) / 0.02, 0, 1))
        truth.append((t, t + d, (root, q)))
        t += d
    tk = np.arange(int(0.32 * rate)) / rate
    kick = np.tanh(drive * np.sin(2 * np.pi * np.cumsum(tail_hz + 260.0 * np.exp(-tk * 38.0)) / rate)) \
        * np.exp(-tk / 0.16) + 0.5 * np.random.default_rng(1).standard_normal(len(tk)) * np.exp(-tk / 0.004)
    beat = 60.0 / bpm
    tb = np.arange(int(beat * rate)) / rate
    duck, kicks = np.ones(n), np.zeros(n)
    for k in np.arange(0.0, n / rate, beat):
        i = int(k * rate)
        kicks[i:i + len(kick)] += kick[:n - i]
        duck[i:i + len(tb)] = (1.0 - 0.85 * np.exp(-tb / 0.09))[:n - i]
    rms = lambda x: np.sqrt(np.mean(x ** 2)) + 1e-12
    mix = duck * (chords / rms(chords) + sub / rms(sub) * 10 ** (sub_db / 20)) + kicks / rms(kicks) * 10 ** (kick_db / 20)
    return (0.9 * mix / np.max(np.abs(mix))).astype(np.float32), truth


# a minor-key hardstyle progression's pool: i, VI, III, VII, iv, v and V7, with the colours producers reach for
HARDSTYLE_POOL = [(9, "min"), (5, "maj"), (0, "maj"), (7, "maj"), (2, "min"), (4, "min"), (4, "7"), (9, "sus2"),
                  (7, "sus4"), (5, "maj7"), (2, "m7"), (9, "m7")]


@pytest.mark.parametrize("tail_hz", [55.0, 49.0])
def test_hardstyle_kick_sub_bass_and_supersaw_chords(tail_hz):
    """Daniel's hardstyle: a distorted kick on every beat at 150 BPM, a sub bass on the root under 65 Hz ducking
    under it, supersaw chords on top, in A minor. The kick's tail sits in the same band as the sub (tuned to the
    tonic, A1, or off it, G1); it swells and fades with every beat while the sub holds, so the sub is the bass.
    The right root >= 90 % of the time and (root, quality) >= 85 % (round 1: 74-76 % root)."""
    rng = np.random.default_rng(8)
    seq = [HARDSTYLE_POOL[int(rng.integers(len(HARDSTYLE_POOL)))] + (1.6,) for _ in range(24)]
    audio, truth = hardstyle(seq, tail_hz=tail_hz, kick_db=3.0, drive=2.0)
    _, events = listen(audio)
    full, root = rq_accuracy(chords_of(events), truth, settle=0.6)
    assert root >= 0.90 and full >= 0.85, (full, root)


def test_a_melody_alone_is_not_a_chord():
    """A single-note melody (C D E G, four times, each note ringing into the next) used to read as one power chord
    per note (one note and its 3rd harmonic match '5') and found a key. A chord now needs two of its own tones
    sounding as notes, and a two-note reading must hold longer."""
    rng = np.random.default_rng(2)
    seq = [60, 62, 64, 67] * 4
    buf = np.zeros(int((len(seq) * 0.5 + 1) * RATE))
    for i, m in enumerate(seq):
        x = piano(m, 0.45, RATE, 0.3, rng)
        buf[int(i * 0.5 * RATE):int(i * 0.5 * RATE) + len(x)] += x
    _, events = listen((0.8 * buf / np.max(np.abs(buf))).astype(np.float32))
    named = [e["name"] for e in chords_of(events) if e["root"] is not None]
    assert len(named) <= 1, named
    assert not [e for e in events if e["type"] == "key"]


def ringing_line(notes, step, rel, kind="epiano", rate=RATE, seed=31):
    """A one-note line where every note rings into the next: held for `step`, then a `rel` s release. epiano: a
    bell-ish decaying tone; pluck: a string whose upper partials die fast."""
    rng = np.random.default_rng(seed)
    buf = np.zeros(int((len(notes) * step + rel + 1) * rate))
    for i, m in enumerate(notes):
        f0 = 440.0 * 2 ** ((m - 69) / 12)
        t = np.arange(int((step + rel) * rate)) / rate
        x = np.zeros(len(t))
        for h in range(1, 12):
            if h * f0 > 0.45 * rate:
                break
            decay = (0.6 + 0.9 * h) if kind == "epiano" else (0.8 + 0.5 * h)
            x += np.sin(2 * np.pi * h * f0 * t + rng.uniform(0, 6.28)) * np.exp(-t * decay) / h ** (1.5 if kind == "epiano" else 1.0)
        x *= np.minimum(1.0, t / 0.002) * np.where(t < step, 1.0, np.clip(1 - (t - step) / rel, 0, 1))
        j = int(i * step * rate)
        buf[j:j + len(x)] += x
    return (0.8 * buf / np.max(np.abs(buf))).astype(np.float32)


@pytest.mark.parametrize("line", ["bass", "pluck"])
def test_a_line_ringing_into_its_next_note_is_not_a_chord(line):
    """Round 2: a one-note bass line (E2 G2 A2 B2 A2 G2) whose notes ring into each other read 16-18 chords and a
    key; a ringing pluck melody five sus2 chords and A major. A line's previous note, struck before the newest one
    and fading, no longer builds a chord with it (notes struck together and fading together still do)."""
    if line == "bass":
        audio = ringing_line([40, 43, 45, 47, 45, 43] * 4, 0.5, 0.5)
    else:
        audio = ringing_line([64, 67, 69, 71, 69, 67, 64, 62] * 3, 0.35, 0.4, kind="pluck")
    _, events = listen(audio)
    named = [e["name"] for e in chords_of(events) if e["root"] is not None]
    assert len(named) <= 2, named
    assert not [e for e in events if e["type"] == "key"]


@pytest.mark.parametrize("hold,step", [(0.45, 0.5), (0.9, 1.0), (0.25, 0.5)])
def test_a_melody_on_the_keys_is_not_a_chord(hold, step):
    """Round 2: C-D-E-G on the keys, no pedal, each note released just before the next, read 9-15 chords: the
    released note rings out and the two made a dyad. A released note now builds a new chord only while it is
    still loud (above RING_NOTE_ON of the loudest), and a dyad still has to hold longer."""
    evs, t = [], 0.0
    for m in [60, 62, 64, 67] * 4:
        evs += [{"t": t, "note": m, "vel": 90}, {"t": t + hold, "note": m, "vel": 0}]
        t += step
    evs.sort(key=lambda e: (e["t"], e["vel"] > 0))
    out = CS.ChordSense().feed_notes(evs, now=t + 1.0)
    named = [e["name"] for e in chords_of(out) if e["root"] is not None]
    assert len(named) <= 1, named


def test_an_arpeggio_with_sustain_still_reads_its_chord():
    """What the line rule must not cost: C-E-G-B broken over the sustain pedal (audio: each note ringing on; keys:
    the pedal down, each key released) is still C or Cmaj7, on both ears."""
    rng = np.random.default_rng(4)
    buf = np.zeros(int(9 * RATE))
    for k in range(4):                                     # four bars of the broken chord, every note ringing 3 s
        for i, m in enumerate([60, 64, 67, 71]):
            x = piano(m, 3.0, RATE, 0.3, rng)
            j = int((2 * k + 0.25 * i) * RATE)
            buf[j:j + len(x)] += x[:len(buf) - j]
    _, events = listen((0.8 * buf / np.max(np.abs(buf))).astype(np.float32))
    named = [e["name"] for e in chords_of(events) if e["root"] is not None]
    assert named and set(named) <= {"C", "Cmaj7"}, named
    evs = [{"t": 0.0, "sustain": 127}]
    for k in range(4):
        for i, m in enumerate([60, 64, 67, 71]):
            t0 = 2 * k + 0.25 * i
            evs += [{"t": t0, "note": m, "vel": 80}, {"t": t0 + 0.2, "note": m, "vel": 0}]
        evs.append({"t": 2 * k + 1.9, "sustain": 0})
        evs.append({"t": 2 * k + 1.95, "sustain": 127})
    evs.sort(key=lambda e: e["t"])
    out = CS.ChordSense().feed_notes(evs, now=8.5)
    named = [e["name"] for e in chords_of(out) if e["root"] is not None]
    assert named and set(named) <= {"C", "Cmaj7"}, named


def test_chords_under_loud_noise_and_a_washy_pad_are_still_heard():
    """Round 2: round 1's tonality bar (0.25) silenced real pads and synth chords (40 real chordal loops: chord time
    88 -> 77 %, a NodeX pad and a Cymatics pad to 0 %) and chords under pink noise at 0 dB SNR (93 -> 25 %). The
    bar is now 0.08 (noise sits at ~0.00-0.04), with N's benefit of the doubt below 0.25, and sounds whose harmonic
    energy lives above C6 (808 hats, a ride) must be that much more tonal. Pink noise at 0 dB: chords >= 70 % of the
    time and the right root on >= 80 % of them; a 9-voice detuned pad drowned in a long reverb: >= 70 %."""
    from scipy.signal import fftconvolve
    seq = random_set(16, seed=7)
    audio, truth = render([(notes, d, "") for notes, d, _ in seq], drums=False)
    truth = [(t0, t1, rq) for (t0, t1, _), (_, _, rq) in zip(truth, seq)]
    rng = np.random.default_rng(99)
    spec = np.fft.rfft(rng.standard_normal(len(audio)))
    spec[1:] /= np.sqrt(np.fft.rfftfreq(len(audio), 1.0 / RATE)[1:])
    spec[0] = 0.0
    pink = np.fft.irfft(spec, len(audio))
    mix = audio + pink / np.std(pink) * np.std(audio)
    _, events = listen((0.9 * mix / np.max(np.abs(mix))).astype(np.float32))
    chords = chords_of(events)
    on = chord_time(chords, len(audio) / RATE)
    full, root = rq_accuracy(chords, truth)
    assert on >= 0.70 and root >= 0.8 * on, (on, full, root)
    # the pad: three detuned saws per note, a 2.5 s noise-tail reverb, mostly wet
    pad = np.zeros(int(16 * RATE))
    for k, (r, q) in enumerate([(9, "min"), (5, "maj"), (0, "maj"), (7, "maj")]):
        for iv in CS.QUALITIES[q][0]:
            m = 57 + (r + iv - 57) % 12
            t = np.arange(int(4 * RATE)) / RATE
            for det in (-0.12, 0.0, 0.11):
                f0 = 440.0 * 2 ** ((m + det - 69) / 12)
                x = sum(np.sin(2 * np.pi * h * f0 * t + rng.uniform(0, 6.28)) / h * np.exp(-h / 5.0) for h in range(1, 12))
                pad[int(4 * k * RATE):int(4 * k * RATE) + len(t)] += x * np.minimum(1.0, t / 0.3) * np.minimum(1.0, (4 - t) / 0.3)
    ir = rng.standard_normal(int(2.5 * RATE)) * np.exp(-np.arange(int(2.5 * RATE)) / RATE * 6.9 / 2.5)
    wet = fftconvolve(pad, ir)[:len(pad)]
    pad = 0.3 * pad / np.max(np.abs(pad)) + 0.7 * wet / np.max(np.abs(wet))
    _, events = listen((0.8 * pad / np.max(np.abs(pad))).astype(np.float32))
    assert chord_time(chords_of(events), 16.0) >= 0.70, [e["name"] for e in chords_of(events)]


def test_a_ride_cymbal_is_not_named_as_chords():
    """Round 2: a ride (sixty sustained inharmonic partials over 300 Hz-9 kHz, struck on the 8ths) read as chords
    94 % of the time: its partials stand clear and steady, but its energy sits above the voices' register."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(109)
    n, L = int(12 * RATE), int(1.6 * RATE)
    tl = np.arange(L) / RATE
    ride = sum(rng.uniform(0.2, 1) * np.sin(2 * np.pi * f * tl + rng.uniform(0, 6)) * np.exp(-tl / rng.uniform(0.3, 1.5))
               for f in rng.uniform(300, 9000, 60))
    ride = ride + 0.5 * sosfilt(butter(2, 4000, "highpass", fs=RATE, output="sos"),
                                rng.standard_normal(L)) * np.exp(-tl / 0.08)
    x = np.zeros(n)
    for t0 in np.arange(0.0, 12.0, 60 / 96 / 2):
        i = int(t0 * RATE)
        x[i:i + L] += ride[:n - i]
    _, events = listen((0.6 * x / np.max(np.abs(x))).astype(np.float32))
    assert chord_time(chords_of(events), 12.0) <= 0.10, [e["name"] for e in chords_of(events)]


def test_an_idle_gap_costs_one_step():
    """The keys path used to step every 20 ms frame through a gap: half an hour of silence was ~90,000 frames
    (3.3 s) in one call. Once nothing sounds and the state has settled, the gap is one jump."""
    cs = CS.ChordSense()
    cs.feed_notes([{"t": 0.0, "note": m, "vel": 90} for m in (60, 64, 67)], now=1.0)
    cs.feed_notes([{"t": 1.0, "note": m, "vel": 0} for m in (60, 64, 67)], now=2.0)
    t0 = time.perf_counter()
    cs.feed_notes([], now=1800.0)
    assert time.perf_counter() - t0 < 0.02
    assert abs(cs.snapshot()["t"] - 1800.0) < 0.05 and cs.snapshot()["tension"] < 1e-6
    out = cs.feed_notes([{"t": 1800.5, "note": m, "vel": 90} for m in (57, 60, 64)], now=1802.0)
    assert [e["name"] for e in chords_of(out)] == ["Am"]


def test_a_stuck_key_across_a_long_gap_costs_one_step_and_bad_times_are_refused():
    """Round 2: with a key still held (a stuck note, a held organ chord) half an hour cost 5 s of frames, one by one:
    the idle jump only knew silence. Held keys whose level has reached the floor a held key keeps are a steady
    state too: the gap is jumped (the key memories take the same evidence as a geometric sum, the pedal runs and
    the tension move as they would), and the result matches stepping frame by frame. And now=inf (or NaN) is
    refused with a ValueError, not an OverflowError deep in the clock."""
    cs = CS.ChordSense()
    cs.feed_notes([{"t": 0.0, "note": 60, "vel": 90}], now=1.0)
    t0 = time.perf_counter()
    cs.feed_notes([], now=1800.0)
    assert time.perf_counter() - t0 < 0.05
    assert abs(cs.snapshot()["t"] - 1800.0) < 0.05

    def run(jump):
        cs = CS.ChordSense()
        if not jump:
            cs._steady_held = lambda: False
        out = cs.feed_notes([{"t": 0.0, "note": m, "vel": 90} for m in (48, 52, 55, 60)], now=1.0)
        out += cs.feed_notes([], now=61.0)
        out += cs.feed_notes([{"t": 61.0, "note": m, "vel": 0} for m in (48, 52, 55, 60)]
                             + [{"t": 61.1, "note": m, "vel": 90} for m in (45, 52, 57, 60)], now=64.0)
        s = cs.snapshot()
        return [(e["type"], e.get("name") or e.get("key"), round(e["t"], 2)) for e in out], s
    (a, sa), (b, sb) = run(True), run(False)
    assert a == b, (a, b)
    assert abs(sa["tension"] - sb["tension"]) < 1e-3 and abs(sa["key_confidence"] - sb["key_confidence"]) < 1e-3
    for bad in (float("inf"), float("nan")):
        with pytest.raises(ValueError):
            CS.ChordSense().feed_notes([], now=bad)
        with pytest.raises(ValueError):
            CS.ChordSense().feed_notes([{"t": bad, "note": 60, "vel": 90}])


def test_confidence_is_an_agreement_margin():
    """confidence used to be the HMM posterior (~0.99 on everything). It is now how far the reading leads its best
    rival, times the share of its tones sounding, times the clarity of the sound: it ranks readings."""
    def conf(notes, noise=0.0):
        audio, _ = render([(notes, 4.0, "")], strike_every=0.5, drums=False)
        audio = audio + noise * np.random.default_rng(1).standard_normal(len(audio))
        cs, _ = listen(audio.astype(np.float32))
        return cs.snapshot()["chord"]["confidence"]
    triad = conf([45, 57, 60, 64, 69])                                      # Am, clean
    assert triad >= 0.8
    assert conf([45, 57, 60, 64, 69], noise=0.15) < triad - 0.1            # the same chord under noise
    assert conf([60, 64]) < triad - 0.2                                     # a bare dyad: two thirds of a triad
    assert conf([43, 50, 55, 60, 62]) < 0.5                                 # G-D-G-C-D: Gsus4 or Csus2?
    audio, _ = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=0.5)
    confs = [e["confidence"] for e in chords_of(listen(audio)[1])]
    assert min(confs) < 0.7 and max(confs) > 0.9, confs                     # it spreads, it is not a constant


def test_pulse_comes_from_the_harmony_not_the_drums():
    """pulse used to be the raw spectral rise, so drums alone flashed it to 1.0. It is now the rise of the HARMONIC
    part: drums alone never pulse, re-struck chords do."""
    drums = BB.synth_case("d", 120, 10, RATE, style="drums").audio
    cs = CS.ChordSense(RATE, HOP)
    pulses = []
    for i in range(0, len(drums), HOP):
        cs.feed(drums[i:i + HOP])
        pulses.append(cs.snapshot()["pulse"])
    assert max(pulses) == 0.0
    audio, _ = render([(VOICINGS[k], 2.0, k) for k in EIGHT], strike_every=0.5)
    cs = CS.ChordSense(RATE, HOP)
    pulses = []
    for i in range(0, len(audio), HOP):
        cs.feed(audio[i:i + HOP])
        pulses.append(cs.snapshot()["pulse"])
    assert max(pulses) >= 0.9 and np.mean(np.array(pulses) > 0.3) > 0.02


def test_names_before_a_key_follow_common_usage():
    """With no key yet, minor chords are spelled the way charts spell them: C#m, not Dbm (major stays Db)."""
    assert [CS.chord_name(r, q) for r, q in ((1, "min"), (8, "min"), (6, "min"), (3, "min"), (10, "min"))] == \
        ["C#m", "G#m", "F#m", "Ebm", "Bbm"]
    assert [CS.chord_name(r, q) for r, q in ((1, "maj"), (8, "maj"), (3, "dim"))] == ["Db", "Ab", "D#dim"]
    assert CS.chord_name(1, "min", 8) == "C#m/G#"
    assert CS.chord_name(1, "min", None, (1, "major")) == "Dbm"                     # a key still decides
    audio, _ = render([([37, 49, 52, 56, 61], 4.0, "C#m")], strike_every=0.5)
    assert [e["name"] for e in chords_of(listen(audio)[1])] == ["C#m"]


def test_a_triad_over_a_lone_bass_is_a_slash_chord():
    """G-B-D over a lone C in the bass is G/C, not Csus2 (which leaves the B out); E-G-B over a lone C is still
    Cmaj7 (the bass joins the voices into a chord that explains all of them)."""
    for notes, want in (([36, 55, 59, 62, 67], "G/C"), ([36, 52, 55, 59, 64], "Cmaj7")):
        audio, _ = render([(notes, 4.0, want)], strike_every=0.5)
        assert [e["name"] for e in chords_of(listen(audio)[1])] == [want], want
        evs, end = play([(notes, 8)])
        assert [e["name"] for e in chords_of(CS.ChordSense().feed_notes(evs, now=end))] == [want], want


def test_a_modulation_is_heard_within_eight_seconds():
    """C major for 32 s, then A major (I-IV-V7-I): the key used to need 21 s (by way of A minor). A fast 4 s memory
    beside the 18 s one, and a dominant 7th pointing at its tonic, hear it within 8 s on the keys and in audio."""
    c = [[36, 48, 52, 55, 60], [41, 53, 57, 60, 65], [43, 55, 59, 62, 65], [36, 48, 52, 55, 60]]
    a = [[45, 57, 61, 64, 69], [38, 50, 54, 57, 62], [40, 52, 56, 59, 62], [45, 57, 61, 64, 69]]
    evs, end = play([(x, 4) for x in c] * 4 + [(x, 4) for x in a] * 4)
    keys = [(e["t"], e["key"]) for e in CS.ChordSense().feed_notes(evs, now=end) if e["type"] == "key"]
    audio, _ = render([(x, 2.0, "") for x in c] * 4 + [(x, 2.0, "") for x in a] * 4, strike_every=0.5)
    keys_audio = [(e["t"], e["key"]) for e in listen(audio)[1] if e["type"] == "key"]
    for got in (keys, keys_audio):
        assert got[0][1] == "C major" and got[-1][1] == "A major", got
        assert next(t for t, k in got if k == "A major") - 32.0 <= 8.0, got
        assert all(k in ("C major", "A major") for _, k in got), got


def test_a_borrowed_bVII_loop_stays_in_its_key():
    """Round 2: C-Bb-F-C (C with a borrowed bVII) flipped to F major for 3 s on the 4 s key memory. The fast way to a
    new key now waits until the first key has stood a few seconds, and needs the rival's own tonic chord to have
    been heard more than the current key's lately: C keeps coming home."""
    prog = [[36, 48, 52, 55, 60], [46, 50, 53, 58, 62], [41, 53, 57, 60, 65], [36, 48, 52, 55, 60]]
    evs, end = play([(x, 4) for x in prog] * 8)
    keys = [e["key"] for e in CS.ChordSense().feed_notes(evs, now=end) if e["type"] == "key"]
    audio, _ = render([(x, 2.0, "") for x in prog] * 6, strike_every=0.5)
    keys_audio = [e["key"] for e in listen(audio)[1] if e["type"] == "key"]
    assert keys == ["C major"] and keys_audio == ["C major"], (keys, keys_audio)


def test_key_confidence_is_the_evidence_not_the_switching_margin():
    """Round 2: a key reached by the fast memory was announced at confidence 1.0 (its switching margin / 0.15,
    clipped), so a passing key read as surely as a settled one. Confidence is now the key's share of a softmax over
    all 24 keys' fits, the fast memory blended with a long one a key change does not reset: a key just reached is
    believed less than one that has stood, and the belief grows as the new key holds."""
    c = [[36, 48, 52, 55, 60], [41, 53, 57, 60, 65], [43, 55, 59, 62, 65], [36, 48, 52, 55, 60]]
    d = [[38, 50, 54, 57, 62], [43, 55, 59, 62, 67], [45, 57, 61, 64, 67], [38, 50, 54, 57, 62]]
    evs, end = play([(x, 4) for x in c] * 4 + [(x, 4) for x in d] * 4)
    out, snaps = _pedal_timeline(evs, end)
    keys = [(e["t"], e["key"], e["confidence"]) for e in out if e["type"] == "key"]
    assert keys[0][1] == "C major" and keys[-1][1] == "D major", keys
    steady_c = [s["key_confidence"] for t, s in snaps if 20.0 <= t < 30.0]
    assert min(steady_c) >= 0.8, min(steady_c)
    moved = [k for k in keys if k[0] > 32.0]
    assert moved and all(cf <= 0.8 for _, _, cf in moved), moved
    t_d, _, c_d = keys[-1]
    later = [s["key_confidence"] for t, s in snaps if t_d + 9.0 <= t < t_d + 11.0]
    assert later and min(later) >= c_d + 0.1, (c_d, later)


def test_vj_events_follow_the_engine_contract():
    """to_vj_events maps every chordsense event onto the VJ engine's SSE contract (arsenal/keylab/vj.py): chord in
    its own shape, plus the new key and tension events -- so wiring chordsense into vj.py is a few lines."""
    import json
    audio, _ = render([(DB[k], 2.0, k) for k in ("Db", "Gb", "Ab7", "Db")] * 2, strike_every=0.5)
    _, events = listen(audio)
    vj = [v for e in events for v in CS.to_vj_events(e)]
    json.dumps(vj)                                                          # plain JSON, ready for 'data:'
    chord_keys = {"t", "src", "name", "root", "quality", "pcs", "bass", "roman", "key", "conf", "changed"}
    chords = [v for v in vj if v["t"] == "chord"]
    assert chords and all(set(v) == chord_keys and v["src"] == "audio" and v["changed"] is True for v in chords)
    db7 = next(v for v in chords if v["name"] == "Ab7")
    assert db7["root"] == 8 and db7["quality"] == "7" and db7["pcs"] == [0, 3, 6, 8] and 0.0 <= db7["conf"] <= 1.0
    assert [(v["name"], v["conf"] >= 0) for v in vj if v["t"] == "key"] == [("Db major", True)]
    assert all(set(v) == {"t", "name", "conf"} for v in vj if v["t"] == "key")
    tension = [v for v in vj if v["t"] == "tension"]
    assert len(tension) >= len(chords) and all(set(v) == {"t", "value", "pedal_pc"} and 0.0 <= v["value"] <= 1.0
                                               for v in tension)
    # the minor spelling is the engine's ('m'), the keys are 'keys', and a pedal becomes a tension event
    minor = CS.to_vj_events({"type": "chord", "src": "keys", "name": "C#m", "root": 1, "quality": "min", "bass": 1,
                             "roman": None, "key": None, "confidence": 0.7, "changed": True, "tension": 0.2,
                             "pedal_pc": None})
    assert minor[0]["quality"] == "m" and minor[0]["src"] == "keys" and minor[0]["pcs"] == [1, 4, 8]
    ped = CS.to_vj_events({"type": "pedal", "pc": 1, "on": True, "tension": 0.6})
    assert ped == [{"t": "tension", "value": 0.6, "pedal_pc": 1}]
    assert CS.to_vj_events({"type": "pedal", "pc": 1, "on": False, "tension": 0.2})[0]["pedal_pc"] is None
    assert CS.to_vj_events({"type": "nothing"}) == []


# --- Daniel's Joy to the World ---------------------------------------------------------------------------------

JOY_BPM = 100.0
BEAT = 60.0 / JOY_BPM


def _joy_path():
    root = Path(__file__).resolve().parents[1]
    for p in (os.environ.get("KEYLAB_JOY_NOTES"), root / "state" / "arsenal" / "keylab" / "joy_notes.json"):
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


def test_joy_keys_hold_db_major_and_believe_it_most(joy):
    """Round 2: on the keys Joy held Db major 0.93 of the time with 6 announcements, and the passing keys (Eb minor,
    Gb major, Ab major) were announced at confidence 1.0 while Db major got 0.36-0.52. Now Db major holds >= 0.9
    with at most 5 announcements, and every passing key is believed less than Db major ever is."""
    notes, ppq = joy
    evs = CS.score_to_events(notes, ppq, JOY_BPM)
    end = evs[-1]["t"]
    events = CS.ChordSense().feed_notes(evs, now=end)
    keys = [(e["key"], e["confidence"]) for e in events if e["type"] == "key"]
    assert _key_share(events, "Db major", 60 * BEAT, end) >= 0.9
    assert len(keys) <= 5, keys
    db = [cf for k, cf in keys if k == "Db major"]
    others = [cf for k, cf in keys[1:] if k != "Db major"]
    assert db and all(cf < min(db) for cf in others), keys


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
