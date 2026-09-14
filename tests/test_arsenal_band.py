"""Claude's band (arsenal/band.py): the pattern contract, chord loops and Nashville input, every bass and drum style's
documented rhythm, registers, voice leading, the hand-written .mid files (read back by a tiny reader below), the baked
VFX module, the playlist and the CLI.

Everything writes under pytest's tmp_path: nothing here touches state/, arsenal/fl/ or an Image-Line folder.
"""
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import band  # noqa: E402
from arsenal.band import BandError  # noqa: E402

LOOP_C = "Cmaj7 | Am7 | Dm7 | G7"


# ================================================================================================ a tiny SMF reader
def read_vlq(data, i):
    n = 0
    for _ in range(4):
        b = data[i]
        i += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return n, i
    raise AssertionError("a variable-length quantity longer than 4 bytes")


def read_midi(data):
    """{format, division, tracks: [[("meta", tick, kind, payload) | ("midi", tick, status, data)]]}; asserts the
    chunk lengths add up exactly and every track ends with End of Track."""
    assert data[:4] == b"MThd"
    hlen, fmt, ntrks, division = struct.unpack(">IHHH", data[4:14])
    assert hlen == 6
    i, tracks = 8 + hlen, []
    for _ in range(ntrks):
        assert data[i:i + 4] == b"MTrk"
        (length,) = struct.unpack(">I", data[i + 4:i + 8])
        body = data[i + 8:i + 8 + length]
        assert len(body) == length
        i += 8 + length
        events, j, tick, status = [], 0, 0, None
        while j < len(body):
            delta, j = read_vlq(body, j)
            tick += delta
            b = body[j]
            if b == 0xFF:
                kind = body[j + 1]
                ln, j = read_vlq(body, j + 2)
                events.append(("meta", tick, kind, bytes(body[j:j + ln])))
                j += ln
            elif b in (0xF0, 0xF7):
                ln, j = read_vlq(body, j + 1)
                j += ln
            else:
                if b & 0x80:
                    status = b
                    j += 1
                assert status is not None, "running status with no status byte"
                size = 1 if status & 0xF0 in (0xC0, 0xD0) else 2
                events.append(("midi", tick, status, bytes(body[j:j + size])))
                j += size
        assert events and events[-1][:3] == ("meta", events[-1][1], 0x2F)
        tracks.append(events)
    assert i == len(data), "bytes after the last track"
    return {"format": fmt, "division": division, "tracks": tracks}


def notes_of(track):
    """(on tick, off tick, channel, note, velocity) for each note-on/off pair."""
    open_notes, out = {}, []
    for ev in track:
        if ev[0] != "midi":
            continue
        _, tick, status, d = ev
        kind, ch = status & 0xF0, status & 0x0F
        if kind == 0x90 and d[1] > 0:
            assert (ch, d[0]) not in open_notes, f"note {d[0]} struck again before its release"
            open_notes[(ch, d[0])] = (tick, d[1])
        elif kind == 0x80 or kind == 0x90:
            on, vel = open_notes.pop((ch, d[0]))
            out.append((on, tick, ch, d[0], vel))
    assert not open_notes, "notes left hanging"
    return sorted(out)


def metas(track, kind):
    return [(ev[1], ev[3]) for ev in track if ev[0] == "meta" and ev[2] == kind]


def expected_notes(notes, channel):
    return sorted((round(n["beat"] * 480), max(round(n["beat"] * 480) + 1, round((n["beat"] + n["len"]) * 480)),
                   channel, n["note"], n["vel"]) for n in notes)


# ================================================================================================ helpers
def lane(ps, name):
    return ps["lanes"][name]["notes"]


def at(notes, beat, pitch=None):
    return [n for n in notes if abs(n["beat"] - beat) < 1e-6 and (pitch is None or n["note"] == pitch)]


def tick(beat):
    return round(band.q(beat) * 480)


def at_tick(notes, beat, pitch=None):
    """Notes starting on the 480 PPQ tick of beat (for swung positions, which are snapped to the grid)."""
    return [n for n in notes if tick(n["beat"]) == tick(beat) and (pitch is None or n["note"] == pitch)]


def sw(beat, amount=band.NEO_SOUL_SWING):
    """Where the neo-soul swing puts a beat on an odd 16th (every other beat stays)."""
    return band.q(band._swung_onset(beat, amount, 4))


def assert_no_overlap(notes):
    ends = {}
    for n in sorted(notes, key=lambda n: (n["beat"], n["note"])):
        assert ends.get(n["note"], -1) <= n["beat"] + 1e-9, f"pitch {n['note']} overlaps itself at {n['beat']}"
        ends[n["note"]] = n["beat"] + n["len"]


def make(loop=LOOP_C, **kw):
    kw.setdefault("key", "C major")
    kw.setdefault("bpm", 80)
    kw.setdefault("pid", "t")
    return band.make_pattern_set(loop, **kw)


def per_bar(notes, pitch=None, bpb=4):
    bars = {}
    for n in notes:
        if pitch is None or n["note"] == pitch:
            b = int(n["beat"] // bpb)
            bars.setdefault(b, []).append(round(n["beat"] - b * bpb, 6))
    return {b: sorted(v) for b, v in bars.items()}


# ================================================================================================ MIDI
def test_vlq_matches_the_smf_spec_table():
    table = {0x00: "00", 0x40: "40", 0x7F: "7F", 0x80: "81 00", 0x2000: "C0 00", 0x3FFF: "FF 7F",
             0x4000: "81 80 00", 0x100000: "C0 80 00", 0x1FFFFF: "FF FF 7F", 0x200000: "81 80 80 00",
             0x08000000: "C0 80 80 00", 0x0FFFFFFF: "FF FF FF 7F"}
    for n, hexes in table.items():
        encoded = band.vlq(n)
        assert encoded == bytes.fromhex(hexes)
        assert read_vlq(encoded, 0) == (n, len(encoded))
    for bad in (-1, 0x10000000):
        with pytest.raises(ValueError):
            band.vlq(bad)


def test_combined_mid_is_type_1_with_a_conductor_and_one_track_per_lane():
    ps = band.seed("eb-neosoul-pocket")
    m = read_midi(band.midi_bytes(ps))
    assert m["format"] == 1 and m["division"] == 480 and len(m["tracks"]) == 1 + len(band.LANES)
    conductor = m["tracks"][0]
    assert metas(conductor, 0x51) == [(0, round(60_000_000 / 84).to_bytes(3, "big"))]
    assert metas(conductor, 0x58) == [(0, bytes((4, 2, 24, 8)))]
    assert metas(conductor, 0x59) == [(0, struct.pack(">bB", -3, 0))]          # Eb major: three flats
    assert [(t, p.decode()) for t, p in metas(conductor, 0x06)] == [(round(c["beat"] * 480), c["name"])
                                                                   for c in ps["chords"]]
    end = round(ps["length_beats"] * 480)
    for track, name in zip(m["tracks"][1:], band.LANES):
        assert metas(track, 0x03) == [(0, name.encode())]
        assert notes_of(track) == expected_notes(lane(ps, name), band.CHANNELS[name])
        assert track[-1][1] == end                                              # End of Track on the loop's end
    assert band.CHANNELS["drums"] == 9 and notes_of(m["tracks"][2])[0][2] == 9  # drums on MIDI channel 10


def test_per_lane_files_hold_the_tempo_and_just_that_lane(tmp_path):
    ps = band.seed("db-ballad-lift")
    written = band.export_mid(ps, tmp_path)
    names = sorted(p.name for p in written)
    assert names == sorted(["db-ballad-lift.mid", "db-ballad-lift-bass.mid", "db-ballad-lift-drums.mid",
                            "db-ballad-lift-pad.mid"])                             # comp is off in this seed
    for name in ("bass", "drums", "pad"):
        m = read_midi((tmp_path / f"db-ballad-lift-{name}.mid").read_bytes())
        assert m["format"] == 1 and len(m["tracks"]) == 1
        track = m["tracks"][0]
        assert metas(track, 0x51)[0][1] == round(60_000_000 / 66).to_bytes(3, "big")
        assert metas(track, 0x59) == [(0, struct.pack(">bB", -5, 0))]          # Db major: five flats
        assert notes_of(track) == expected_notes(lane(ps, name), band.CHANNELS[name])


def test_a_repeated_pitch_releases_before_it_strikes_again():
    ps = make("C", bass="synth-pulse", drums="none", bars=1)
    track = read_midi(band.midi_bytes(ps, "bass"))["tracks"][0]
    at_240 = [ev for ev in track if ev[0] == "midi" and ev[1] == 240]
    kinds = [ev[2] & 0xF0 for ev in at_240]
    assert kinds.count(0x90) == 1 and (0x80 not in kinds or kinds.index(0x80) < kinds.index(0x90))
    assert len(notes_of(track)) == 8


@pytest.mark.parametrize("key, sf, mi", [("C major", 0, 0), ("D major", 2, 0), ("F major", -1, 0),
                                         ("Db major", -5, 0), ("Gb major", -6, 0), ("F# major", 6, 0),
                                         ("Bb minor", -5, 1), ("A minor", 0, 1), ("E minor", 1, 1)])
def test_key_signatures(key, sf, mi):
    assert band.key_signature(key) == (sf, mi)


# ================================================================================================ bars and beats
@pytest.mark.parametrize("meter, beats", [((4, 4), 4), ((3, 4), 3), ((6, 8), 3), ((12, 8), 6), ((7, 8), 3.5),
                                          ((2, 2), 4)])
def test_beats_per_bar(meter, beats):
    assert band.beats_per_bar(meter) == beats
    assert band.is_whole_bars(beats * 3, meter) and not band.is_whole_bars(beats * 3 + 1, meter)


def test_next_bar_line_is_strictly_after_the_position():
    assert band.next_bar_line(0, (4, 4)) == 4
    assert band.next_bar_line(3.99, (4, 4)) == 4
    assert band.next_bar_line(4.0, (4, 4)) == 8
    assert band.next_bar_line(5.3, (4, 4)) == 8
    assert band.next_bar_line(17, (4, 4)) == 20          # positions may run past the loop's length
    assert band.next_bar_line(2.5, (3, 4)) == 3
    assert band.next_bar_line(3.2, (6, 8)) == 6


def test_bar_lines_split_a_bar_and_durations_override():
    cycle = band.parse_loop("Gmaj9 A/G | F#m9 Bm9", "D major")
    assert [(c["name"], c["beat"], c["dur"]) for c in cycle] == [("Gmaj9", 0, 2), ("A/G", 2, 2), ("F#m9", 4, 2),
                                                                ("Bm9", 6, 2)]
    cycle = band.parse_loop("Db13sus4:2 Db7b9:2 Gbmaj9", "Gb major")
    assert [(c["beat"], c["dur"]) for c in cycle] == [(0, 2), (2, 2), (4, 4)]
    cycle = band.parse_loop("Fmaj9 % Dm9 %")
    assert [c["name"] for c in cycle] == ["Fmaj9", "Fmaj9", "Dm9", "Dm9"] and cycle[3]["beat"] == 12
    cycle = band.parse_loop("| Cmaj7:8 | Am7 |")
    assert [(c["beat"], c["dur"]) for c in cycle] == [(0, 8), (8, 4)]
    with pytest.raises(BandError, match="whole bars"):
        band.parse_loop("C:3 G")
    with pytest.raises(BandError, match="no room"):
        band.parse_loop("C:4 G | F")
    with pytest.raises(BandError, match='"%"'):
        band.parse_loop("% C")


def test_bars_repeat_or_cut_the_loop_and_every_note_fits():
    ps = make(bars=8, bass="walking", drums="neo-soul", comp=True, pad=True, fill=True)
    assert ps["length_beats"] == 32
    assert [c["beat"] for c in ps["chords"]] == [0, 4, 8, 12, 16, 20, 24, 28]
    assert [c["name"] for c in ps["chords"]][4:] == ["Cmaj7", "Am7", "Dm7", "G7"]
    for name in band.LANES:
        assert all(0 <= n["beat"] < 32 and n["beat"] + n["len"] <= 32 + 1e-9 for n in lane(ps, name))
    short = make(bars=2)
    assert short["length_beats"] == 8 and [c["name"] for c in short["chords"]] == ["Cmaj7", "Am7"]


def test_three_four_meter():
    ps = make("C | G | Am | F", meter="3/4", bass="walking", drums="ballad", pad=True)
    assert ps["meter"] == [3, 4] and ps["length_beats"] == 12
    assert [c["beat"] for c in ps["chords"]] == [0, 3, 6, 9]
    band.validate_pattern_set(ps)
    assert band.lint(ps) == []
    assert per_bar(lane(ps, "drums"), band.KICK, 3) == {b: [0] for b in range(4)}


def test_an_eight_beat_chord_is_restruck_each_bar():
    ps = make("Cmaj7:8 Fmaj7:8", bass="roots-on-1", drums="none", comp=True)
    assert [(n["beat"], n["note"] % 12) for n in lane(ps, "bass")] == [(0, 0), (4, 0), (8, 5), (12, 5)]
    assert sorted({n["beat"] for n in lane(ps, "comp")}) == [0, 2.5, 4, 6.5, 8, 10.5, 12, 14.5]


# ================================================================================================ contract
def test_normalize_notes_cuts_overlaps_and_keeps_the_louder_duplicate():
    raw = [{"beat": 0, "len": 3, "note": 40, "vel": 80}, {"beat": 2, "len": 1, "note": 40, "vel": 90},
           {"beat": 2, "len": 1, "note": 40, "vel": 70}, {"beat": 1, "len": 9, "note": 50, "vel": 200},
           {"beat": 8, "len": 1, "note": 41, "vel": 60}, {"beat": 0.1, "len": 1, "note": 128, "vel": 60}]
    out = band.normalize_notes(raw, 8)
    assert out == [{"beat": 0, "len": 2, "note": 40, "vel": 80}, {"beat": 1, "len": 7, "note": 50, "vel": 127},
                   {"beat": 2, "len": 1, "note": 40, "vel": 90}]


def test_the_contract_shape():
    ps = band.seed("gb-real-v7")
    assert list(ps) == ["version", "id", "title", "key", "bpm_hint", "meter", "length_beats", "chords", "lanes"]
    assert ps["version"] == 1 and list(ps["lanes"]) == list(band.LANES)
    assert all(set(c) == {"beat", "name", "nns"} for c in ps["chords"])
    for name in band.LANES:
        assert set(ps["lanes"][name]) == {"notes"}
        assert all(list(n) == ["beat", "len", "note", "vel"] for n in lane(ps, name))
        assert lane(ps, name) == sorted(lane(ps, name), key=lambda n: (n["beat"], n["note"]))
    assert lane(ps, "pad") == []                                   # an off lane is present and empty
    assert json.loads(band.dump_json(ps)) == ps


@pytest.mark.parametrize("patch, message", [
    (lambda ps: ps.update(version=2), "version"),
    (lambda ps: ps.update(length_beats=30), "whole bars"),
    (lambda ps: ps.update(id="Not An Id"), "id"),
    (lambda ps: lane(ps, "bass")[0].update(vel=0), "vel"),
    (lambda ps: lane(ps, "bass")[0].update(note=128), "note"),
    (lambda ps: lane(ps, "bass")[0].update(beat=32), "inside"),
    (lambda ps: lane(ps, "bass")[-1].update(len=99), "inside"),
    (lambda ps: ps["lanes"].update(lead={"notes": []}), "unknown lane"),
    (lambda ps: ps["lanes"].pop("pad"), "lanes.pad"),
    (lambda ps: ps["chords"][0].pop("nns"), "chords"),
])
def test_validation_rejects_broken_sets(patch, message):
    ps = band.seed("eb-neosoul-pocket")
    patch(ps)
    with pytest.raises(BandError, match=message):
        band.validate_pattern_set(ps)


# ================================================================================================ registers + overlap
REGISTER_LOOPS = [
    ("Emaj9 | C#m11 | Aadd9/E | B13sus4", "E major"),
    ("Gmaj7 | G/B | C6/9 | D7b9", "G major"),
    ("1m11 | 1m9/b7 | b6maj9#11 | 5^7sus4 5^7b9", "Bb minor"),
    ("F#m7b5 B7alt | Em9 | Am11 A7#9 | Dmaj13", "D major"),
]


@pytest.mark.parametrize("loop, key", REGISTER_LOOPS)
@pytest.mark.parametrize("style", band.BASS_STYLES)
def test_bass_styles_stay_in_register_and_never_overlap(loop, key, style):
    ps = band.make_pattern_set(loop, key=key, bass=style, drums="none", comp=True, pad=True, bars=8, pid="reg")
    band.validate_pattern_set(ps)
    assert band.lint(ps) == []
    lo, hi = band.BASS_RANGE
    assert all(lo <= n["note"] <= hi for n in lane(ps, "bass"))
    assert (lane(ps, "bass") == []) == (style == "none")
    for name in ("comp", "pad"):
        assert lane(ps, name) and all(48 <= n["note"] <= 71 for n in lane(ps, name))
    for name in band.LANES:
        assert_no_overlap(lane(ps, name))


@pytest.mark.parametrize("meter", ["4/4", "3/4", "6/8"])
@pytest.mark.parametrize("style", band.DRUM_STYLES)
@pytest.mark.parametrize("fill", [False, True])
def test_drum_styles_are_valid_in_every_meter(meter, style, fill):
    bpb = band.beats_per_bar(band.parse_meter(meter))
    loop = " | ".join(["C"] * 8) if bpb == 4 else " | ".join(["C"] * 4)
    ps = make(loop, meter=meter, drums=style, bass="none", fill=fill)
    band.validate_pattern_set(ps)
    assert band.lint(ps) == []
    assert (lane(ps, "drums") == []) == (style == "none")
    assert_no_overlap(lane(ps, "drums"))
    assert {n["note"] for n in lane(ps, "drums")} <= set(band.GM_NAMES)


# ================================================================================================ bass rhythms
def test_roots_on_1_follows_the_slash_bass():
    ps = make("C/E | F | G/B | C", bass="roots-on-1", drums="none")
    assert [(n["beat"], n["note"] % 12) for n in lane(ps, "bass")] == [(0, 4), (4, 5), (8, 11), (12, 0)]
    assert all(abs(n["len"] - (4 - band.GAP)) < 1e-6 for n in lane(ps, "bass"))


def test_root_fifth_is_bass_on_1_and_fifth_on_3():
    ps = make("C | Bdim | Am | Gaug", key="C major", bass="root-fifth", drums="none")
    notes = lane(ps, "bass")
    assert [n["beat"] for n in notes] == [0, 2, 4, 6, 8, 10, 12, 14]
    roots = [0, 11, 9, 7]
    fifths = [7, 5, 4, 3]                 # G, F (the dim chord's b5), E, D# (the augmented #5)
    assert [n["note"] % 12 for n in notes[0::2]] == roots
    assert [n["note"] % 12 for n in notes[1::2]] == fifths


def sounding(notes, beat):
    return [n for n in notes if n["beat"] - 1e-9 <= beat < n["beat"] + n["len"] - 1e-9]


def test_walking_is_quarters_that_step_into_each_change_half_a_beat_early():
    ps = make(bass="walking", drums="none")
    notes = lane(ps, "bass")
    roots = [0, 9, 2, 7]
    assert at(notes, 0)[0]["note"] % 12 == 0
    for b in range(4):
        nxt = (b + 1) % 4
        onsets = [round(n["beat"] - b * 4, 6) for n in notes if b * 4 <= n["beat"] < b * 4 + 4]
        assert onsets == ([0] if b == 0 else []) + [1, 2, 3, 3.5], f"bar {b + 1}: {onsets}"
        approach, early = at(notes, b * 4 + 3)[0], at(notes, b * 4 + 3.5)[0]
        assert early["note"] % 12 == roots[nxt], f"bar {b + 1} does not step to the next root on the and of 4"
        assert abs(approach["note"] - early["note"]) == 1 and approach["len"] <= 0.5     # a half-step 8th
        if nxt:
            assert sounding(notes, nxt * 4) == [early] and early["beat"] + early["len"] > nxt * 4 + 0.5  # tied over
        else:
            assert early["beat"] + early["len"] <= 16 and at(notes, 0)                  # the loop top strikes its 1
    for a, b2 in zip(notes, notes[1:]):
        assert a["note"] != b2["note"], "a walking line repeats a note"


def test_walking_does_not_step_early_where_the_bass_note_stays():
    notes = lane(make("Cmaj7:8 Fmaj7:8", bass="walking", drums="none"), "bass")
    assert [n["beat"] for n in notes if n["beat"] < 4] == [0, 1, 2, 3] and at(notes, 4)       # same chord: on the 1
    assert at(notes, 7.5)[0]["note"] % 12 == 5 and not at(notes, 8)                           # the change to F


def test_gospel_runs_early_into_phrase_tops_and_steps_plainly_into_the_other_changes():
    ps = make("Cmaj7 | Am7 | Fmaj7 | G7", bass="gospel", drums="none")
    notes = sorted(lane(ps, "bass"), key=lambda n: n["beat"])
    roots = [0, 9, 5, 7]
    for b in range(4):
        nxt = (b + 1) % 4
        bar = [n for n in notes if b * 4 <= n["beat"] < b * 4 + 4]
        onsets = [round(n["beat"] - b * 4, 4) for n in bar]
        root = sounding(notes, b * 4)[0]["note"]
        assert root % 12 == roots[b]
        struck_1 = [0] if b == 0 or b % 2 == 1 else []                                # bar 3 is tied in from bar 2
        if nxt % 2 == 0:                     # into bar 3 or the loop top, the phrase tops of a 4-bar loop: the run
            assert onsets == struck_1 + [1.5, 2, 2.75, 3, 3.25, 3.5], f"bar {b + 1}: {onsets}"
            partner, third, run, early = bar[-6], bar[-5], [n["note"] for n in bar[-4:-1]], bar[-1]
            assert run[1] - run[0] == run[2] - run[1] and abs(run[1] - run[0]) == 1  # a chromatic 16th run
            assert abs(run[2] - early["note"]) == 1 and early["note"] % 12 == roots[nxt]
            assert partner["note"] % 12 in (root % 12, (root + 7) % 12)               # octave, or the fifth
            assert run[0] != third["note"], "the run restates beat 3's note"
            assert partner["note"] != third["note"], "the and of 2 and beat 3 repeat one note"
            if nxt:
                assert sounding(notes, nxt * 4) == [early]                            # tied over the bar line
        else:                                # any other change: no run, no anticipation, room for the piano
            assert onsets == struck_1 + [1.5, 2, 3], f"bar {b + 1}: {onsets}"
            approach, landing = bar[-1], at(notes, nxt * 4)[0]
            assert abs(approach["note"] - landing["note"]) == 1 and landing["note"] % 12 == roots[nxt]
            assert approach["beat"] + approach["len"] <= nxt * 4                      # lands on the 1, not before


def test_f_to_d_drop_runs_in_triplets_only_into_the_key_drop_and_the_turnaround():
    ps = band.seed("f-to-d-drop")
    notes, drums = lane(ps, "bass"), lane(ps, "drums")
    rides = {tick(n["beat"]) for n in drums if n["note"] == band.RIDE}
    tail = {b: [round(n["beat"] - b * 4, 3) for n in notes if b * 4 + 2.5 <= n["beat"] < b * 4 + 4] for b in range(8)}
    assert tail[3] == [2.667, 3, 3.333, 3.667] and tail[7] == [3.333, 3.667]            # into bar 5 and bar 1
    assert all(tail[b] == [3] for b in (0, 1, 2, 4, 5, 6)), tail                         # a plain step elsewhere
    for b, pc in ((3, 2), (7, 5)):                                                       # D at the drop, F at the top
        early = [n for n in notes if tick(n["beat"]) == tick(b * 4 + 3 + 2 / 3)][0]
        assert tick(early["beat"]) in rides and early["note"] % 12 == pc                 # on the ride's triplet skip
    assert sounding(notes, 16)[0]["note"] % 12 == 2 and not at(notes, 16)                # tied into the drop
    assert at(notes, 0)[0]["note"] % 12 == 5                                              # the loop top strikes its 1


def test_gospel_keeps_the_triplet_run_on_4_where_the_bass_note_stays():
    notes = lane(make("Cmaj7:8 Fmaj7:8", bass="gospel", drums="none"), "bass")
    assert [round(n["beat"], 4) for n in notes if n["beat"] < 4] == [0, 1.5, 2, 3, 3.3333, 3.6667]
    assert at(notes, 4) and at(notes, 7.5) and not at(notes, 8)


def test_gospel_minor_third_walk_down_keeps_moving():
    ps = make("Fmaj9 | Dmaj9 | Bm11 | C13sus4", key="F major", bass="gospel", drums="none")
    notes = sorted(lane(ps, "bass"), key=lambda n: n["beat"])
    assert [len([n for n in notes if b * 4 <= n["beat"] < b * 4 + 4]) for b in range(4)] == [4, 7, 3, 7]
    line = [n["note"] for n in notes]
    assert all(x != y for x, y in zip(line, line[1:])), f"the line repeats a note back to back: {line}"


def test_pocket_bass_is_root_on_1_ghosts_anticipations_and_space():
    ps = band.seed("eb-neosoul-pocket")
    assert next(s for s in band.SEEDS if s["id"] == "eb-neosoul-pocket")["bass"] == "pocket"
    notes, chords = lane(ps, "bass"), ps["chords"]
    kicks = [n["beat"] for n in lane(ps, "drums") if n["note"] == band.KICK]
    root_pc = [band.parse_chord_token(c["name"], None)["bass"] for c in chords]
    for b in range(8):
        bar = [n for n in notes if b * 4 <= n["beat"] < b * 4 + 4]
        offs = [round(n["beat"] - b * 4, 6) for n in bar]
        first = at(notes, b * 4)
        assert first and first[0]["note"] % 12 == root_pc[b], f"bar {b + 1} has no root on 1"
        assert 1.5 in offs and offs != [0, 1, 2, 3]                                  # the and of 2, not a walk
        assert at(notes, b * 4 + 2.5) and b * 4 + 2.5 in kicks                         # with the kick on the and of 3
        if b % 2 == 0:
            ghost = at_tick(notes, sw(b * 4 + 0.75))[0]                               # swung with the hats
            assert ghost["vel"] < 50 and ghost["len"] <= 0.25 and ghost["note"] == first[0]["note"]
            assert abs(at_tick(notes, sw(b * 4 + 3.75))[0]["note"] - at(notes, (b + 1) % 8 * 4)[0]["note"]) == 1
        else:
            assert at(notes, b * 4 + 3.5)[0]["note"] % 12 == root_pc[(b + 1) % 8]    # anticipated on the and of 4
        covered = sum(1 for k in range(16) if sounding(bar, b * 4 + k * 0.25 + 0.125))
        assert covered <= 10, f"bar {b + 1} leaves too little space ({covered} of 16 sixteenths sound)"
    for k in kicks:                                                                   # the kick never lands in a note
        assert not [n for n in notes if n["beat"] + 1e-9 < k < n["beat"] + n["len"] - 1e-9], k
    assert len([n for n in notes if any(abs(n["beat"] - k) < 1e-9 for k in kicks)]) >= 16


def test_offbeat_bass_plays_the_ands_and_leaves_the_beats_to_the_kick():
    ps = band.seed("gb-real-v7")
    bass, drums = lane(ps, "bass"), lane(ps, "drums")
    assert per_bar(bass) == {b: [0.5, 1.5, 2.5, 3.5] for b in range(8)}
    assert not {n["beat"] for n in bass} & {n["beat"] for n in drums if n["note"] == band.KICK}
    assert all(n["beat"] + n["len"] <= n["beat"] + 0.5 for n in bass)
    assert per_bar(drums, band.OPEN_HAT) == {b: [0.5, 1.5, 2.5, 3.5] for b in range(8)}
    for b, pc in enumerate((6, 3, 8, 1)):                                            # Gb Eb Ab Db
        assert {n["note"] % 12 for n in bass if b * 4 <= n["beat"] < b * 4 + 4} == {pc}


def test_pedal_holds_the_tonic_under_every_chord():
    ps = make("Dbmaj9 | Gbmaj9/Db | Ebm11/Db | Ab13sus4/Db", key="Db major", bass="pedal", drums="none", bars=4)
    notes = lane(ps, "bass")
    assert [n["beat"] for n in notes] == [0, 4, 8, 12]
    assert {n["note"] for n in notes} == {37}                     # Db2
    other = make("Fmaj7 | Bb | C | F", key="Db major", bass="pedal", drums="none")
    assert {n["note"] % 12 for n in lane(other, "bass")} == {1}   # the key's tonic, not the chord's root


def test_synth_pulse_is_straight_eighths_on_the_bass_note():
    ps = make(bass="synth-pulse", drums="none")
    notes = lane(ps, "bass")
    assert per_bar(notes) == {b: [i * 0.5 for i in range(8)] for b in range(4)}
    for b, pc in enumerate((0, 9, 2, 7)):
        assert {n["note"] % 12 for n in notes if b * 4 <= n["beat"] < b * 4 + 4} == {pc}


def test_repeats_of_the_loop_play_the_same_bass_line():
    for sid in ("db-ballad-lift", "eb-neosoul-pocket", "d-halftime-sunrise"):
        notes = lane(band.seed(sid), "bass")
        first = [(tick(n["beat"]), n["note"]) for n in notes if n["beat"] < 16]
        second = [(tick(n["beat"]) - 16 * 480, n["note"]) for n in notes if n["beat"] >= 16]
        assert first == second, sid


@pytest.mark.parametrize("kw", [dict(bass="pocket", comp=True), dict(bass="gospel", comp=True, pad=True, swing=0.66),
                                dict(bass="walking", comp=True, swing=0.5)])
def test_bass_comp_and_pad_sit_in_the_neo_soul_swing_with_the_hats(kw):
    ps = band.seed("eb-neosoul-pocket") if kw.get("bass") == "pocket" else make(drums="neo-soul", bars=4, **kw)
    amount = kw.get("swing", band.NEO_SOUL_SWING)
    hats = {tick(n["beat"]) for n in lane(ps, "drums") if n["note"] in (band.HAT, band.SNARE)}
    swung = 0
    for name in ("bass", "comp", "pad"):
        for n in lane(ps, name):
            t = tick(n["beat"])
            assert t % 240 != 120 or amount == 0.5, f"{name} note at {n['beat']} is a straight 16th under swung hats"
            if t % 120 and t % 160:
                assert t in hats, f"{name} note at {n['beat']} flams against the hats"
                swung += 1
    assert (swung > 0) == (amount != 0.5)
    other = make(bass="pocket", drums="halftime", swing=0.66)                            # only neo-soul swings
    assert at(lane(other, "bass"), 0.75)


# ================================================================================================ drum rhythms
def test_ballad_is_kick_on_1_and_side_stick_on_3():
    d = lane(make(drums="ballad"), "drums")
    assert per_bar(d, band.KICK) == {b: [0] for b in range(4)}
    assert per_bar(d, band.STICK) == {b: [2] for b in range(4)}
    assert per_bar(d, band.HAT) == {b: [i * 0.5 for i in range(8)] for b in range(4)}
    assert not [n for n in d if n["note"] == band.SNARE]


def test_neo_soul_lays_back_the_snare_ghosts_and_swings_the_hats():
    d = lane(make(drums="neo-soul"), "drums")
    for b in range(4):
        loud = [n for n in d if n["note"] == band.SNARE and n["vel"] >= 90 and b * 4 <= n["beat"] < b * 4 + 4]
        assert [round(n["beat"] - b * 4, 6) for n in loud] == [round(1 + 10 / 480, 6), round(3 + 10 / 480, 6)]
        ghosts = [n for n in d if n["note"] == band.SNARE and n["vel"] < 45 and b * 4 <= n["beat"] < b * 4 + 4]
        assert len(ghosts) == 2
    hats = per_bar(d, band.HAT)[0]
    assert len(hats) == 15 and band.q(0.29) in hats and 0.25 not in hats and 0.5 in hats  # offbeat 16ths late
    assert per_bar(d, band.OPEN_HAT) == {b: [3.5] for b in range(4)}
    assert per_bar(d, band.KICK) == {b: [0, 1.75, 2.5] for b in range(4)}
    straight = lane(make(drums="neo-soul", swing=0.5), "drums")
    assert 0.25 in per_bar(straight, band.HAT)[0]


def test_halftime_puts_the_snare_on_3():
    d = lane(make(drums="halftime"), "drums")
    assert per_bar(d, band.SNARE) == {b: [2] for b in range(4)}
    assert per_bar(d, band.KICK) == {0: [0, 2.5], 1: [0, 2.5, 3.75], 2: [0, 2.5], 3: [0, 2.5, 3.75]}


def test_four_on_the_floor_opens_the_hat_on_every_and():
    d = lane(make(drums="four-on-floor"), "drums")
    assert per_bar(d, band.KICK) == {b: [0, 1, 2, 3] for b in range(4)}
    assert per_bar(d, band.SNARE) == {b: [1, 3] for b in range(4)}
    assert per_bar(d, band.OPEN_HAT) == {b: [0.5, 1.5, 2.5, 3.5] for b in range(4)}
    assert per_bar(d, band.HAT) == {b: [0, 1, 2, 3] for b in range(4)}               # soft, closing the open hat
    assert all(n["vel"] < 50 for n in d if n["note"] == band.HAT)
    assert all(n["beat"] + n["len"] <= n["beat"] // 1 + 1 + 1e-9 for n in d if n["note"] == band.OPEN_HAT)


def test_brushes_ride_the_triplet_skip():
    d = lane(make(drums="brushes"), "drums")
    assert per_bar(d, band.RIDE) == {b: [0, 1, 1.666667, 2, 3, 3.666667] for b in range(4)}
    assert per_bar(d, band.PEDAL) == {b: [1, 3] for b in range(4)}
    assert all(n["vel"] < 60 for n in d if n["note"] in (band.SNARE, band.KICK))


def test_ambient_is_sparse_with_crashes_and_a_rising_swell():
    ps = make(" | ".join(["Dbmaj9"] * 8), key="Db major", drums="ambient")
    d = lane(ps, "drums")
    assert per_bar(d, band.CRASH) == {0: [0], 4: [0]}
    assert per_bar(d, band.KICK) == {b: [0] for b in (0, 2, 4, 6)}
    for bar in (3, 7):
        swell = sorted((n for n in d if n["note"] == band.RIDE and bar * 4 + 2 <= n["beat"] < bar * 4 + 4),
                       key=lambda n: n["beat"])
        assert len(swell) == 8 and swell[-1]["vel"] > swell[0]["vel"] + 50
        assert all(b2["vel"] >= a["vel"] - 4 for a, b2 in zip(swell, swell[1:]))
    for bar in (0, 1, 2, 4, 5, 6):
        assert len([n for n in d if bar * 4 <= n["beat"] < bar * 4 + 4]) <= 3


def test_fill_rewrites_the_back_half_of_the_last_bar():
    plain, filled = lane(make(drums="halftime"), "drums"), lane(make(drums="halftime", fill=True), "drums")
    assert [n for n in plain if n["beat"] < 12] != []
    toms = [(n["beat"], n["note"]) for n in filled if n["note"] in (50, 48, 45, 41)]
    assert toms == [(15, 50), (15.25, 48), (15.5, 45), (15.75, 41)]
    assert [n["beat"] for n in filled if n["note"] == band.CRASH] == [0]
    assert not [n for n in filled if n["note"] == band.HAT and n["beat"] >= 14]
    assert not [n for n in plain if n["note"] in (50, 48, 45, 41, band.CRASH)]
    assert [n for n in filled if 4 <= n["beat"] < 12] == [n for n in plain if 4 <= n["beat"] < 12]


def test_humanize_is_seeded_per_seed_bar_and_lane():
    assert "HUMANIZE INVARIANT" in band.__doc__ and '"<id>/<bar>/<lane>"' in band.__doc__

    def bar5(h):
        return [h.vel(20 + k * 0.5, 80, 10) for k in range(8)]

    busy = band.Humanizer("s", "drums", 4)
    for i in range(37):
        busy.vel(i % 16 * 0.25, 80, 10)                        # bar 1 draws a lot first
    assert bar5(busy) == bar5(band.Humanizer("s", "drums", 4))
    assert bar5(band.Humanizer("s", "comp", 4)) != bar5(band.Humanizer("s", "drums", 4))
    assert bar5(band.Humanizer("t", "drums", 4)) != bar5(band.Humanizer("s", "drums", 4))


def test_a_bars_velocities_ignore_what_other_bars_hold():
    one, two = make("C | C | C | C", pad=True, drums="none"), make("C:2 G:2 | C | C | C", pad=True, drums="none")
    assert len([n for n in lane(two, "pad") if n["beat"] < 4]) > len([n for n in lane(one, "pad") if n["beat"] < 4])
    later = [[n["vel"] for n in lane(ps, "pad") if n["beat"] >= 4] for ps in (one, two)]
    assert later[0] == later[1] and len(set(later[0])) > 1


def test_dropout_rests_every_lane_but_the_bass():
    loop = "Cmaj7:12 Fmaj7:4"
    kw = dict(bass="walking", drums="neo-soul", comp=True, pad=True, bars=4)
    holes, plain = make(loop, dropout=1.0, **kw), make(loop, **kw)
    assert band.dropout_bars("t", 4, 1.0) == [1, 3]
    band.validate_pattern_set(holes)
    assert band.lint(holes) == []
    assert lane(holes, "bass") == lane(plain, "bass")
    for b in (1, 3):
        for name in ("drums", "comp", "pad"):
            inside = [n for n in lane(holes, name) if n["beat"] < (b + 1) * 4 - 1e-9 and n["beat"] + n["len"] > b * 4 + 1e-9]
            pushes_out = [n for n in inside if n["beat"] >= (b + 1) * 4 - 0.5 and n["beat"] + n["len"] > (b + 1) * 4]
            assert inside == pushes_out, (b, name)                                     # only a push out of the rest
        assert not [n for n in lane(holes, "comp") if b * 4 - 0.5 <= n["beat"] < b * 4]  # the push into it rests too
    assert [n for n in lane(holes, "drums") if 8 <= n["beat"] < 12] == [n for n in lane(plain, "drums") if 8 <= n["beat"] < 12]
    assert {n["note"] for n in at(lane(holes, "pad"), 8)} == {n["note"] for n in at(lane(plain, "pad"), 0)}  # struck again
    assert at_tick(lane(holes, "comp"), sw(7.75)) == at_tick(lane(plain, "comp"), sw(7.75))   # comes back on its push
    assert at(lane(holes, "pad"), 0)


def test_dropout_treats_pushes_as_the_vfx_band_does():
    spec = next(s for s in band.SEEDS if s["id"] == "eb-neosoul-pocket")
    kw = dict(key=spec["key"], bpm=spec["bpm"], bars=8, bass="pocket", drums="neo-soul", comp=True, pid=spec["id"])
    holes, plain = band.make_pattern_set(spec["loop"], dropout=0.3, **kw), band.make_pattern_set(spec["loop"], **kw)
    assert band.dropout_bars(spec["id"], 8, 0.3) == [1, 3]
    assert at_tick(lane(plain, "comp"), sw(3.75)) and not [n for n in lane(holes, "comp") if 3 <= n["beat"] < 7.5]
    out = at_tick(lane(holes, "comp"), sw(7.75))
    assert out and out == at_tick(lane(plain, "comp"), sw(7.75)) and not at(lane(holes, "comp"), 8)
    long_pad = band.make_pattern_set("Cmaj9:8 Fmaj9:8", key="C major", bars=4, drums="none", pad=True, pid="set-3",
                                     dropout=1.0)
    assert band.dropout_bars("set-3", 4, 1.0) == [1, 3]
    assert [(n["beat"], n["len"]) for n in lane(long_pad, "pad")][:1] == [(0, 4)]              # cut at the rest bar
    assert {n["beat"] for n in lane(long_pad, "pad")} == {0, 8}                                # nothing restruck into 3


def test_dropout_bars_are_seeded_never_the_first_and_never_two_in_a_row():
    seen = set()
    for pid in [f"set-{i}" for i in range(40)]:
        for amount in (0.25, 0.6, 0.95):
            rests = band.dropout_bars(pid, 16, amount)
            assert rests == band.dropout_bars(pid, 16, amount)
            assert 0 not in rests and all(y - x >= 2 for x, y in zip(rests, rests[1:]))
            assert band.dropout_bars(pid, 8, amount) == [b for b in rests if b < 8]
            seen.update(rests)
    assert seen and band.dropout_bars("set-1", 16, 0) == []
    assert len(set(tuple(band.dropout_bars(f"set-{i}", 16, 0.25)) for i in range(40))) > 5  # not one fixed pattern
    with pytest.raises(BandError, match="--dropout"):
        make(dropout=1.5)
    assert make(dropout=0.0) == make()


def test_dropout_rests_lean_on_the_last_bar_of_a_phrase():
    by_place = [0, 0, 0, 0]
    for i in range(400):
        for b in band.dropout_bars(f"set-{i}", 16, 0.3):
            by_place[b % 4] += 1
    assert by_place[3] > 2 * max(by_place[:3])  # bars 4, 8, 12, 16: a breath before the phrase top
    assert band.dropout_bars("t", 16, 1.0) == [1, 3, 5, 7, 9, 11, 13, 15]  # 1 still rests every other bar


def test_velocities_are_humanised_but_deterministic():
    a, b = make(drums="neo-soul", bass="walking", comp=True), make(drums="neo-soul", bass="walking", comp=True)
    assert a == b
    kicks = [n["vel"] for n in lane(a, "drums") if n["note"] == band.KICK and n["beat"] % 4 == 0]
    assert len(set(kicks)) > 1
    assert make(pid="other", drums="neo-soul") != make(drums="neo-soul")


# ================================================================================================ keys
def test_suffix_tones():
    t = band.suffix_tones
    assert t("") == {"1": 0, "3": 4, "5": 7}
    assert t("maj9#11") == {"1": 0, "3": 4, "5": 7, "7": 11, "9": 2, "#11": 6}
    assert t("m11") == {"1": 0, "3": 3, "5": 7, "7": 10, "9": 2, "11": 5}
    assert t("13sus4") == {"1": 0, "5": 7, "7": 10, "9": 2, "13": 9, "4": 5}
    assert "3" not in t("11") and t("11")["11"] == 5
    assert t("7(#9,b13)") == {"1": 0, "3": 4, "5": 7, "7": 10, "#9": 3, "b13": 8}
    assert t("m7b5")["5"] == 6 and t("ø7") == t("m7b5")
    assert t("dim7") == {"1": 0, "3": 3, "5": 6, "7": 9}
    assert t("6/9") == t("69") == {"1": 0, "3": 4, "5": 7, "6": 9, "9": 2}
    assert t("add9") == {"1": 0, "3": 4, "5": 7, "9": 2}
    assert t("m(maj7)")["7"] == 11 and t("m(maj7)")["3"] == 3
    assert t("5") == {"1": 0, "5": 7}
    assert t("sus") == t("sus4") == {"1": 0, "5": 7, "4": 5}
    assert t("7alt") == {"1": 0, "3": 4, "7": 10, "b9": 1, "#9": 3, "b13": 8}
    with pytest.raises(BandError):
        t("xyz")


def test_voicings_use_chord_tones_guide_tones_first_in_c3_to_b4():
    ps = make(comp=True, pad=True)
    for name in ("comp", "pad"):
        for c in ps["chords"]:
            parsed = band.parse_chord_token(c["name"], None)
            pcs = {(parsed["root"] + s) % 12 for s in parsed["tones"].values()}
            struck = [n["note"] for n in lane(ps, name) if n["beat"] == c["beat"]]
            assert struck and {p % 12 for p in struck} <= pcs
            assert all(48 <= p <= 71 for p in struck)
            third, seventh = (parsed["root"] + parsed["tones"]["3"]) % 12, (parsed["root"] + parsed["tones"]["7"]) % 12
            assert {third, seventh} <= {p % 12 for p in struck}, f"{name} {c['name']} lacks its guide tones"


def test_pad_holds_each_chord_and_comp_restrikes_on_the_and_of_3():
    ps = make(comp=True, pad=True, drums="none")
    assert sorted({n["beat"] for n in lane(ps, "pad")}) == [0, 4, 8, 12]
    assert all(abs(n["len"] - (4 - band.GAP)) < 1e-6 for n in lane(ps, "pad"))
    assert sorted({n["beat"] for n in lane(ps, "comp")}) == [0, 2.5, 4, 6.5, 8, 10.5, 12, 14.5]
    assert len({n["note"] for n in lane(ps, "comp") if n["beat"] == 0}) <= 4
    assert len({n["note"] for n in lane(ps, "pad") if n["beat"] == 0}) <= 5


def test_voice_leading_moves_little():
    cycle = band.parse_loop("Dm9 | G13 | Cmaj9 | A7b13 | Dm9 | G7 | Em7 | A7", "C major")
    for name in ("comp", "pad"):
        voicings = band.voice_lead(cycle, name)
        moves = []
        for a, b in zip(voicings, voicings[1:]):
            moves.append(band._movement(a, b) / max(len(a), len(b)))
        assert sum(moves) / len(moves) <= 3.0, (name, voicings)
        assert all(v[-1] <= 71 and v[0] >= 48 for v in voicings)


MUD_LOOPS = REGISTER_LOOPS + [(s["loop"], s["key"]) for s in band.SEEDS] + [
    ("A13sus4 | Gb13sus4 | Ab7b9 | Dbmaj9", "Db major"), ("Ebm11 | Ab13 | Dbmaj9 | Bb7(#9,b13)", "Db major")]


@pytest.mark.parametrize("loop, key", MUD_LOOPS)
def test_no_minor_second_is_stacked_below_g3(loop, key):
    cycle = band.parse_loop(loop, key)
    for name in ("comp", "pad"):
        for chord, v in zip(cycle, band.voice_lead(cycle, name)):
            lows = [(a, b) for a, b in zip(v, v[1:]) if b - a == 1 and a < 55]
            assert not lows, f"{name} {chord['name']} {[band.midi_name(p) for p in v]}"


def test_a13sus4_is_voiced_clear_of_the_low_cluster():
    spec = next(s for s in band.SEEDS if s["id"] == "f-to-d-drop")
    ps = band.make_pattern_set(spec["loop"], key=spec["key"], bars=8, bass="gospel", drums="brushes", comp=True, pid="full")
    a13 = next(c for c in ps["chords"] if c["name"] == "A13sus4")
    struck = sorted(n["note"] for n in lane(ps, "comp") if n["beat"] == a13["beat"])
    assert struck == [55, 59, 62, 66]                                # G3 B3 D4 F#4, not Gb3 G3 B3 D4
    for sid in [s["id"] for s in band.SEEDS]:
        for name in ("comp", "pad"):
            groups = {}
            for n in lane(band.seed(sid), name):
                groups.setdefault(n["beat"], []).append(n["note"])
            assert not [g for g in groups.values() if band.is_muddy(sorted(g))], (sid, name)


@pytest.mark.parametrize("sid", [s["id"] for s in band.SEEDS])
def test_keys_voice_lead_across_the_loop_seam(sid):
    spec = next(s for s in band.SEEDS if s["id"] == sid)
    cycle = band.parse_loop(spec["loop"], spec["key"])
    for name in ("comp", "pad"):
        if not spec.get(name):
            continue
        vs = band.voice_lead(cycle, name)
        tops = [abs(a[-1] - b[-1]) for a, b in zip(vs, vs[1:])]
        seam = abs(vs[-1][-1] - vs[0][-1])
        assert seam <= max([2] + tops), f"{name}: the top voice jumps {seam} at the seam ({vs})"
        assert band._movement(vs[-1], vs[0]) / max(len(vs[-1]), len(vs[0])) <= 3.0


def test_the_sunrise_pad_top_voice_returns_home_at_the_seam():
    pad = lane(band.seed("d-halftime-sunrise"), "pad")
    first, last = sorted(n["note"] for n in at(pad, 0)), sorted(n["note"] for n in at(pad, 28))
    assert abs(first[-1] - last[-1]) <= 2                            # it was B3 -> F#4
    ring, chain = band.voice_lead(band.parse_loop("Dadd9 | A/C# | Bm9 | Gmaj9"), "pad"), None
    chain = band.voice_lead(band.parse_loop("Dadd9 | A/C# | Bm9 | Gmaj9"), "pad", ring=False)
    assert len(ring) == len(chain) == 4


def test_comp_rhythm_follows_the_drum_style():
    rhythms = {}
    for style in ("ballad", "neo-soul", "halftime", "four-on-floor", "brushes", "ambient", "none"):
        comp = lane(make(drums=style, comp=True), "comp")
        rhythms[style] = {b: sorted(set(v)) for b, v in per_bar(comp).items()}
        onsets = sorted({n["beat"] for n in comp})
        for a, b2 in zip(onsets, onsets[1:]):
            assert all(n["beat"] + n["len"] < b2 for n in at(comp, a)), f"{style}: a strike rings into the next"
        if style == "ballad":
            assert all(len(at(comp, b * 4 + 3)) == 2 and len(at(comp, b * 4)) == 4 for b in range(4))  # top two on 4
    assert rhythms["none"] == {b: [0, 2.5] for b in range(4)}
    assert rhythms["ballad"] == {b: [0, 3] for b in range(4)}
    s1, s2 = sw(2.75), sw(3.75)                                      # swung with the hats
    assert rhythms["neo-soul"] == {0: [0, s1, s2], 1: [1.5, s2], 2: [s1, s2], 3: [1.5]}  # pushed; the top on 1
    assert rhythms["halftime"] == {0: [0, 2], 1: [0, 2, 3.5], 2: [0, 2], 3: [0, 2, 3.5]}
    assert rhythms["four-on-floor"] == {b: [0, 1.5, 3] for b in range(4)}
    assert rhythms["brushes"] == {b: [0, 1.5] for b in range(4)}
    assert rhythms["ambient"] == {b: [0] for b in range(4)}
    assert len({json.dumps(r) for r in rhythms.values()}) == 7


def test_a_change_off_the_rhythm_is_still_struck():
    comp = lane(make("Cmaj7:2 A7:2 | Dm7 | G7:3 C:1 | Cmaj7", drums="neo-soul", comp=True), "comp")
    chords = [0, 2, 4, 8, 11, 12]
    for beat in chords:
        assert at(comp, beat) or at_tick(comp, sw(beat - 0.25)), f"the chord at {beat} is never struck"


def test_a_shell_comp_is_two_guide_tones_below_e4():
    ps = band.seed("f-to-d-drop")
    assert next(s for s in band.SEEDS if s["id"] == "f-to-d-drop")["shell"]
    groups = {}
    for n in lane(ps, "comp"):
        groups.setdefault(n["beat"], []).append(n["note"])
    for beat, notes in groups.items():
        chord = band.parse_chord_token(band._chord_at(ps["chords"], beat)["name"], None)
        guide = {(chord["root"] + chord["tones"][r]) % 12 for r in ("3", "4", "7") if r in chord["tones"]}
        assert len(notes) == 2 and all(48 <= p <= 64 for p in notes) and {p % 12 for p in notes} == guide, beat
    loop = "1maj9 - 4maj9#11 - 6m11 - 5sus"
    full = band.make_pattern_set(loop, key="Eb major", comp=True, pad=True, bass="walking", pid="x")
    shell = band.make_pattern_set(loop, key="Eb major", comp=True, pad=True, bass="walking", shell=True, pid="x")
    assert max(n["note"] for n in lane(shell, "comp")) <= 64 < max(n["note"] for n in lane(full, "comp"))
    assert lane(shell, "pad") == lane(full, "pad") and lane(shell, "bass") == lane(full, "bass")


def test_the_real_v7_sounds_its_third_and_seventh():
    ps = band.seed("gb-real-v7")
    v7 = next(c for c in ps["chords"] if c["nns"] == "5^7")
    assert v7["name"] == "Db7"
    struck = {n["note"] % 12 for n in lane(ps, "comp") if n["beat"] == v7["beat"]}
    assert {5, 11} <= struck                                         # F (the 3rd) and Cb (the 7th): a tritone


def test_a_slash_bass_is_not_doubled_when_other_tones_remain():
    chord = band.parse_chord_token("Bbm9/Ab", None)
    assert 8 not in band.voicing_pcs(chord, 4)
    triad = band.parse_chord_token("A/C#", None)
    assert set(band.voicing_pcs(triad, 4)) == {9, 1, 4}              # too few tones to leave C# out


# ================================================================================================ Nashville input
def test_nashville_numbers_read_in_the_key_and_round_trip():
    ps = band.make_pattern_set("4maj9 - 6m11 - 5^11/4 - 1add9", key="Db major", pid="n", pad=True, comp=True)
    assert [c["name"] for c in ps["chords"]] == ["Gbmaj9", "Bbm11", "Ab11/Gb", "Dbadd9"]
    assert [c["nns"] for c in ps["chords"]] == ["4maj9", "6m11", "5^11/4", "1add9"]
    assert lane(ps, "bass")[2]["note"] % 12 == 6                    # the /4: Gb under Ab11


def test_the_same_numbers_in_another_key_transpose_every_lane():
    kw = dict(pid="same", bass="walking", drums="neo-soul", comp=True, pad=True, bars=4)
    db = band.make_pattern_set("4maj9 - 6m11 - 5^11/4 - 1add9", key="Db major", **kw)
    d = band.make_pattern_set("4maj9 - 6m11 - 5^11/4 - 1add9", key="D major", **kw)
    assert [c["name"] for c in d["chords"]] == ["Gmaj9", "Bm11", "A11/G", "Dadd9"]
    assert [c["nns"] for c in d["chords"]] == [c["nns"] for c in db["chords"]]
    assert lane(d, "drums") == lane(db, "drums")
    for name in ("comp", "pad"):
        for c in db["chords"]:
            lo = {n["note"] % 12 for n in lane(db, name) if n["beat"] == c["beat"]}
            hi = {n["note"] % 12 for n in lane(d, name) if n["beat"] == c["beat"]}
            assert hi == {(p + 1) % 12 for p in lo}
    for name in ("bass",):
        for c in db["chords"]:
            lo = [n["note"] % 12 for n in lane(db, name) if n["beat"] == c["beat"]]
            hi = [n["note"] % 12 for n in lane(d, name) if n["beat"] == c["beat"]]
            assert hi == [(p + 1) % 12 for p in lo]


def test_minor_key_numbers_use_major_scale_accidentals():
    cycle = band.parse_loop("1m11 | 1m9/b7 | b6maj9#11 | 5^7sus4 5^7b9", "Bb minor")
    assert [c["name"] for c in cycle] == ["Bbm11", "Bbm9/Ab", "Gbmaj9#11", "F7sus4", "F7b9"]
    ps = band.seed("bbm-lament")
    assert [c["nns"] for c in ps["chords"][:5]] == ["1m11", "1m9/b7", "b6maj9#11", "5^7sus4", "5^7b9"]
    assert [n["note"] for n in lane(ps, "bass")[:5]] == [34, 32, 30, 29, 29]    # Bb1 Ab1 Gb1 F1 F1: the lament


def test_numbers_need_a_key_and_letters_get_an_estimated_one():
    with pytest.raises(BandError, match="--key"):
        band.parse_loop("1 - 4 - 5")
    ps = band.make_pattern_set("Gbmaj9 | Bbm11 | Ab11/Gb | Dbadd9", pid="est")
    assert ps["key"] == "Db major" and [c["nns"] for c in ps["chords"]] == ["4maj9", "6m11", "5^11/4", "1add9"]
    with pytest.raises(BandError, match="key"):
        band.make_pattern_set("C | G", key="H major")
    with pytest.raises(BandError, match="chord"):
        band.parse_loop("C | Q7")


# ================================================================================================ seeds
def test_six_seeds_fit_daniel_and_cover_every_drum_style():
    assert len(band.SEEDS) == 6 and len({s["id"] for s in band.SEEDS}) == 6
    assert {s["drums"] for s in band.SEEDS} == set(band.DRUM_STYLES) - {"none"}
    for s in band.SEEDS:
        ps = band.seed(s["id"])
        band.validate_pattern_set(ps)
        assert band.lint(ps) == [], s["id"]
        assert ps["key"] == s["key"] and s["why"]
        assert all(c["nns"] for c in ps["chords"])
        assert lane(ps, "bass") and lane(ps, "drums") and (lane(ps, "comp") or lane(ps, "pad"))
    with pytest.raises(KeyError):
        band.seed("nope")


SEED_DIGESTS = {2: "fdb37006e684d39a2a77c20923502fce62e789f1"}  # GENERATOR_VERSION -> sha1 of the six seeds


def test_seed_output_is_pinned_to_the_generator_version():
    """What the generator writes for the seeds is pinned to GENERATOR_VERSION: change the notes and this fails until the
    version is bumped (and the new digest recorded), so stored sets from before the change warn in show and exports."""
    digest = hashlib.sha1(json.dumps([band.seed(s["id"]) for s in band.SEEDS], sort_keys=True).encode()).hexdigest()
    assert SEED_DIGESTS.get(band.GENERATOR_VERSION) == digest, (
        f"the seeds changed: bump band.GENERATOR_VERSION and record {digest} for it in SEED_DIGESTS")


def test_the_minor_third_drop_seed_changes_key_centre():
    ps = band.seed("f-to-d-drop")
    names = [c["name"] for c in ps["chords"]]
    assert names[:4] == ["Fmaj9", "Dm9", "Bbmaj9", "C13sus4"] and names[4] == "Dmaj9"
    assert names[-1] == "C13sus4" and ps["chords"][-1]["beat"] == 30


# ================================================================================================ store, playlist
def test_store_round_trip_and_seed_fallback(tmp_path):
    store = band.PatternStore(str(tmp_path))
    ps = make(pid="mine", comp=True)
    path = store.save(ps)
    assert path == tmp_path / "patterns" / "mine.json"
    assert store.load("mine") == ps and store.stored() == ["mine"]
    assert store.load("db-ballad-lift") == band.seed("db-ballad-lift")
    with pytest.raises(BandError, match="no pattern set"):
        store.load("missing")
    with pytest.raises(BandError):
        store.path("../escape")


def test_playlist_add_rm_and_current(tmp_path):
    store = band.PatternStore(str(tmp_path))
    assert store.playlist() == {"version": 1, "current": 0, "items": []}
    store.playlist_add("db-ballad-lift")
    store.playlist_add("eb-neosoul-pocket")
    store.playlist_add("bbm-lament")
    store.playlist_current(3)
    assert store.playlist()["current"] == 2
    store.playlist_add("gb-real-v7", at=1)                      # inserted before the current set: it stays current
    pl = store.playlist()
    assert pl["items"] == ["gb-real-v7", "db-ballad-lift", "eb-neosoul-pocket", "bbm-lament"] and pl["current"] == 3
    pl, removed = store.playlist_rm("2")
    assert removed == "db-ballad-lift" and pl["current"] == 2 and pl["items"][2] == "bbm-lament"
    pl, removed = store.playlist_rm("bbm-lament")               # removing the last, current set
    assert pl["current"] == 1 and pl["items"] == ["gb-real-v7", "eb-neosoul-pocket"]
    with pytest.raises(BandError):
        store.playlist_add("missing")
    with pytest.raises(BandError):
        store.playlist_rm("9")
    with pytest.raises(BandError):
        store.playlist_current(0)
    assert json.loads((tmp_path / "playlist.json").read_text()) == store.playlist()


# ================================================================================================ VFX module
def test_vfx_module_is_ascii_python_holding_the_playlist(tmp_path):
    store = band.PatternStore(str(tmp_path))
    out = tmp_path / "vfx" / "arsenal_patterns.py"
    path, live, ids, current = band.export_vfx(store, out)          # empty playlist: the six seeds
    assert ids == [s["id"] for s in band.SEEDS] and current == 0 and live == tmp_path / "vfx" / "arsenal_live.json"
    assert store.stored() == sorted(ids)                              # ... saved into the store as well
    raw = path.read_bytes()
    assert raw.isascii() and live.read_bytes().isascii()
    scope = {}
    exec(compile(raw.decode("ascii"), str(path), "exec"), scope)
    assert scope["VERSION"] == 1 and scope["LIVE_PATH"] is None and scope["DRUM_MAPS"] == {}
    assert scope["PATTERNS"] == [band.seed(i) for i in ids]
    doc = json.loads(live.read_text(encoding="utf-8"))
    assert doc["version"] == 1 and doc["current"] == 0 and doc["patterns"] == scope["PATTERNS"] and doc["rev"]

    store.save(make(pid="mine", pad=True, title="Café ☕ loop"))    # non-ASCII titles are escaped, not written raw
    store.playlist_add("mine")
    store.playlist_add("bbm-lament")
    store.playlist_current(2)
    path, live, ids, current = band.export_vfx(store, out, live_path="C:\\Users\\L5\\jam\\arsenal_live.json")
    assert path.read_bytes().isascii()
    scope = {}
    exec(path.read_text(encoding="ascii"), scope)
    assert [p["id"] for p in scope["PATTERNS"]] == ["mine", "bbm-lament"]
    assert scope["PATTERNS"][0]["title"] == "Café ☕ loop"
    assert scope["LIVE_PATH"] == "C:\\Users\\L5\\jam\\arsenal_live.json"
    doc2 = json.loads(live.read_text(encoding="utf-8"))
    assert doc2["current"] == 1 and doc2["rev"] != doc["rev"]


def test_vfx_export_refuses_what_the_band_would_refuse():
    too_many = [band.seed("db-ballad-lift")] * (band.VFX_MAX_PATTERNS + 1)
    with pytest.raises(BandError, match="at most 64"):
        band.vfx_module_text(too_many)
    big = band.seed("db-ballad-lift")
    big["lanes"]["drums"]["notes"] = [{"beat": i / 1000, "len": 0.0005, "note": 42, "vel": 60} for i in range(4097)]
    with pytest.raises(BandError, match="4096"):
        band.vfx_live_text([big])


def test_the_vfx_band_script_accepts_the_generated_module(tmp_path):
    """Cross-build contract: arsenal/fl/vfx/arsenal_band.py's own strict parser takes every generated set."""
    script = ROOT / "arsenal" / "fl" / "vfx" / "arsenal_band.py"
    if not script.is_file():
        pytest.skip("the VFX Script band is not in this checkout")
    import importlib.util
    spec = importlib.util.spec_from_file_location("arsenal_band_vfx_under_test", script)
    vfx_band = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vfx_band)                                # flvfx is absent outside FL: no load_module
    store = band.PatternStore(str(tmp_path))
    path, live, ids, _ = band.export_vfx(store, tmp_path / "arsenal_patterns.py")
    scope = {}
    exec(path.read_text(encoding="ascii"), scope)
    for i, ps in enumerate(scope["PATTERNS"]):
        parsed = vfx_band.parse_pattern_set(ps, f"PATTERNS[{i}]")
        assert parsed["id"] == ids[i] and parsed["length_beats"] == ps["length_beats"]
    playlist = vfx_band.parse_playlist(json.loads(live.read_text(encoding="utf-8")))
    assert [p["id"] for p in playlist["patterns"]] == ids and playlist["current"] == 0


def test_default_vfx_path_is_the_generated_area_inside_the_repo():
    assert band.VFX_OUT.name == "arsenal_patterns.py"
    assert band.VFX_OUT.parent.resolve() == (ROOT / "arsenal" / "fl" / "vfx" / "generated").resolve()


# ================================================================================================ text grid + CLI
def test_grid_shows_chords_bass_degrees_drums_and_keys():
    text = band.render_grid(band.seed("eb-neosoul-pocket"))
    lines = text.splitlines()
    chord = next(line for line in lines if line.startswith("chord"))
    assert "Ebmaj9" in chord and "Abmaj9#11" in chord
    bass = next(line for line in lines if line.startswith("bass "))
    assert bass.split("|")[1].startswith("R--R")                                  # the pocket: 1, then its ghost
    kick = next(line for line in lines if line.startswith("kick"))
    assert kick.split("|")[1] == "X......x..x....." or kick.split("|")[1].replace("X", "x") == "x......x..x....."
    voicings = next(line for line in lines if line.startswith("  comp voicings: Ebmaj9"))
    assert all(len(part.split()) >= 4 for part in voicings.split(": ", 1)[1].split(" | "))  # pushed chords found
    assert all(len(line.split("|")[1]) == 16 for line in lines if line.startswith(("hat", "snare", "comp")))


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stderr
    sys.stderr = err
    try:
        code = band.main(list(argv), out=out)
    finally:
        sys.stderr = old
    return code, out.getvalue(), err.getvalue()


def test_cli_make_show_export_and_playlist(tmp_path):
    state = str(tmp_path / "state")
    code, out, err = run_cli("make", "4maj9 - 6m11 - 5^11/4 - 1add9", "--key", "Db major", "--bpm", "66",
                             "--bars", "8", "--bass", "gospel", "--drums", "neo-soul", "--comp", "--pad",
                             "--title", "Test lift", "--add", "--state", state)
    assert code == 0, err
    path = tmp_path / "state" / "patterns" / "test-lift.json"
    ps = band.validate_pattern_set(json.loads(path.read_text(encoding="utf-8")))
    assert ps["length_beats"] == 32 and ps["bpm_hint"] == 66
    assert "Gbmaj9 (4maj9)" in out and "added test-lift" in out

    code, out, _ = run_cli("show", "test-lift", "--state", state)
    assert code == 0 and "|Gbmaj9" in out and "comp voicings" in out

    code, out, _ = run_cli("export-mid", "test-lift", "--state", state)
    folder = tmp_path / "state" / "mid" / "test-lift"
    assert code == 0 and sorted(p.name for p in folder.iterdir()) == sorted(
        ["test-lift.mid"] + [f"test-lift-{name}.mid" for name in band.LANES])
    assert read_midi((folder / "test-lift.mid").read_bytes())["format"] == 1

    code, out, _ = run_cli("playlist", "add", "bbm-lament", "--state", state)
    assert code == 0 and "> " in out and "bbm-lament" in out
    vfx = tmp_path / "gen" / "arsenal_patterns.py"
    code, out, _ = run_cli("export-vfx", "--out", str(vfx), "--state", state)
    assert code == 0 and "2 pattern sets" in out and "Pattern knob  1: bbm-lament" in out
    assert (tmp_path / "gen" / "arsenal_live.json").is_file()
    scope = {}
    exec(vfx.read_text(encoding="utf-8"), scope)
    assert [p["id"] for p in scope["PATTERNS"]] == ["test-lift", "bbm-lament"]

    code, out, _ = run_cli("playlist", "rm", "1", "--state", state)
    assert code == 0 and "removed test-lift" in out
    code, out, _ = run_cli("list", "--state", state)
    assert "stored  test-lift" in out and "seed    db-ballad-lift" in out


def test_cli_errors_exit_2_with_a_message(tmp_path):
    code, _, err = run_cli("make", "1 - 4 - 5", "--state", str(tmp_path))
    assert code == 2 and "--key" in err
    code, _, err = run_cli("show", "missing", "--state", str(tmp_path))
    assert code == 2 and "no pattern set" in err
    code, _, err = run_cli("make", "C | G", "--bars", "0", "--state", str(tmp_path))
    assert code == 2 and "--bars" in err


def test_cli_export_vfx_saves_the_seeds_when_the_playlist_is_empty(tmp_path):
    state, module = tmp_path / "state", tmp_path / "gen" / "arsenal_patterns.py"
    code, out, _ = run_cli("export-vfx", "--out", str(module), "--no-write-seeds", "--state", str(state))
    assert code == 0 and not (state / "patterns").exists() and "saved the" not in out
    stale = band.seed("gb-real-v7")
    stale["title"] = "an older build of this seed"
    band.PatternStore(str(state)).save(stale)
    code, out, _ = run_cli("export-vfx", "--out", str(module), "--state", str(state))
    store = band.PatternStore(str(state))
    assert code == 0 and "saved the 6 seeds" in out
    assert store.stored() == sorted(s["id"] for s in band.SEEDS)
    assert store.load("gb-real-v7") == band.seed("gb-real-v7")            # overwritten, as seeds --write does
    store.playlist_add("bbm-lament")
    (state / "patterns" / "db-ballad-lift.json").unlink()
    code, out, _ = run_cli("export-vfx", "--out", str(module), "--state", str(state))
    assert code == 0 and "saved the" not in out and "db-ballad-lift" not in store.stored()


def test_show_and_exports_warn_about_a_stored_set_from_an_older_generator(tmp_path):
    state = tmp_path / "state"
    store = band.PatternStore(str(state))
    path = store.save(band.seed("gb-real-v7"))
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["generator"] == band.GENERATOR_VERSION                     # stamped on save ...
    assert store.load("gb-real-v7") == band.seed("gb-real-v7")            # ... and never part of the loaded set
    for verb in ("show", "export-mid"):
        code, _, err = run_cli(verb, "gb-real-v7", "--state", str(state))
        assert code == 0 and "older" not in err
    del raw["generator"]                                                  # a file from before the stamp
    path.write_text(json.dumps(raw), encoding="utf-8")
    for verb in ("show", "export-mid"):
        code, _, err = run_cli(verb, "gb-real-v7", "--state", str(state))
        assert code == 0 and "generator version 1, older than this band.py" in err and "seeds --write" in err
    store.playlist_add("gb-real-v7")
    code, _, err = run_cli("export-vfx", "--out", str(tmp_path / "gen" / "arsenal_patterns.py"), "--state", str(state))
    assert code == 0 and "gb-real-v7.json was written by generator version 1" in err
    mine = make(pid="mine")
    band.PatternStore(str(state)).save({**mine, "title": "old"})
    raw = json.loads((state / "patterns" / "mine.json").read_text(encoding="utf-8"))
    raw["generator"] = band.GENERATOR_VERSION - 1
    (state / "patterns" / "mine.json").write_text(json.dumps(raw), encoding="utf-8")
    code, _, err = run_cli("show", "mine", "--state", str(state))
    assert code == 0 and "make it again" in err
    assert run_cli("seeds", "--write", "--state", str(state))[0] == 0
    code, _, err = run_cli("show", "gb-real-v7", "--state", str(state))
    assert code == 0 and "older" not in err
    code, _, err = run_cli("show", "bbm-lament", "--state", str(tmp_path / "empty"))  # no stored file: the seed
    assert code == 0 and "older" not in err


def test_cli_make_with_dropout_names_the_rest_bars(tmp_path):
    state = str(tmp_path / "state")
    code, out, err = run_cli("make", "C | G | Am | F", "--key", "C major", "--bars", "8", "--drums", "halftime",
                             "--pad", "--dropout", "1", "--id", "holes", "--state", state)
    assert code == 0, err
    assert "dropout bars 2, 4, 6, 8 rest" in out
    ps = band.PatternStore(state).load("holes")
    assert not [n for n in lane(ps, "drums") if 4 <= n["beat"] < 8] and [n for n in lane(ps, "bass") if 4 <= n["beat"] < 8]
    code, _, err = run_cli("make", "C | G", "--dropout", "2", "--state", state)
    assert code == 2 and "--dropout" in err
    code, out, err = run_cli("make", "Dm9 | G13 | Cmaj9 | A7b13", "--key", "C major", "--comp", "--shell", "--id", "shells",
                             "--state", state)
    assert code == 0, err
    comp = lane(band.PatternStore(state).load("shells"), "comp")
    assert comp and max(n["note"] for n in comp) <= 64 and len(at(comp, 0)) == 2


def test_cli_seeds_explain_themselves(tmp_path):
    code, out, _ = run_cli("seeds", "--state", str(tmp_path))
    assert code == 0 and all(s["id"] in out and s["why"] in out for s in band.SEEDS)
    assert not (tmp_path / "patterns").exists()
    code, out, _ = run_cli("seeds", "--add", "--state", str(tmp_path))
    assert code == 0 and len(list((tmp_path / "patterns").glob("*.json"))) == 6
    assert band.PatternStore(str(tmp_path)).playlist()["items"] == [s["id"] for s in band.SEEDS]
