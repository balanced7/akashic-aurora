# arsenal_patterns: the pattern module the arsenal band VFX Script imports.
#
# EXAMPLE, written by hand from the two worked grooves in
# research/in-flight/fl-jam-bridge-2026-09-14/fl-jam-bridge-plan.md (sections 9.2 and 9.3).
# The jam engine generates the real module in this same format; copy either one to
# [User Data Folder]/VFX Script/Python/arsenal_patterns.py. Keep it ASCII.
#
# Format (version 1):
#   VERSION   = 1
#   PATTERNS  = [pattern set, ...]   index = the band's Pattern knob (0-63)
#   LIVE_PATH = None or r"C:\...\arsenal_live.json"   the playlist the "Live file" checkbox follows
#   DRUM_MAPS = {}   optional extra drum maps: {"name": {gm_note: target_note}}; unmapped notes are dropped
# A pattern set is the shared contract: {"version": 1, "id", "title", "key", "bpm_hint", "meter": [4, 4],
# "length_beats" (whole bars), "chords": [{"beat", "name", "nns"}], "lanes": {"bass"|"drums"|"comp"|"pad":
# {"notes": [{"beat", "len", "note", "vel"}]}}}. Beats are quarter notes from the pattern start; drums are GM notes.

VERSION = 1
LIVE_PATH = None
DRUM_MAPS = {}


def _n(beat, length, note, vel):
    return {"beat": beat, "len": length, "note": note, "vel": vel}


def _grandeur_lift():
    # Eb major, 68 BPM, half-time worship. Chart: Abmaj9 | Bb13sus4 | Cm11 | Ebmaj9/G  (4 - 5sus - 6m - 1/3)
    bass_rows = [
        (0, 2.5, 32), (2.5, .5, 39), (3, .5, 32), (3.5, .5, 33),
        (4, 2.5, 34), (6.5, .5, 41), (7, .5, 34), (7.5, .5, 35),
        (8, 2.5, 36), (10.5, .5, 43), (11, .5, 34), (11.5, .5, 32),
        (12, 2.5, 31), (14.5, .5, 38), (15, .5, 39), (15.5, .5, 31),
    ]
    bass = [_n(b, ln, note, 100 if b % 4 == 0 else 84) for b, ln, note in bass_rows]
    pad = []
    for bar, chord in enumerate(([51, 55, 58, 60], [51, 55, 56, 60], [51, 53, 58, 62], [51, 58, 62, 65])):
        pad.extend(_n(bar * 4, 4, note, 64) for note in chord)
    drums = [_n(0, .25, 49, 100)]  # crash on the loop top, after the bar 4 fill
    for bar in range(4):
        base = bar * 4
        drums.append(_n(base, .25, 36, 112))
        drums.append(_n(base + 2, .25, 38, 104))
        if bar < 3:
            drums.append(_n(base + 2.5, .25, 36, 96))
            drums.extend(_n(base + s * .5, .1, 42, 72 if s % 2 == 0 else 46) for s in range(8))
        else:
            drums.extend([_n(base + 1.5, .25, 36, 92), _n(base + 2.5, .25, 36, 96)])
            drums.extend(_n(base + s * .5, .1, 42, 72 if s % 2 == 0 else 46) for s in range(6))
            drums.extend([_n(base + 3, .25, 50, 96), _n(base + 3.25, .25, 48, 100),
                          _n(base + 3.5, .25, 45, 104), _n(base + 3.75, .25, 41, 110)])
    return {
        "version": 1, "id": "grandeur-lift", "title": "Grandeur lift, Eb, half-time worship",
        "key": "Eb major", "bpm_hint": 68, "meter": [4, 4], "length_beats": 16,
        "chords": [{"beat": 0, "name": "Abmaj9", "nns": "4maj9"}, {"beat": 4, "name": "Bb13sus4", "nns": "5sus"},
                   {"beat": 8, "name": "Cm11", "nns": "6m11"}, {"beat": 12, "name": "Ebmaj9/G", "nns": "1maj9/3"}],
        "lanes": {"bass": {"notes": bass}, "drums": {"notes": drums}, "comp": {"notes": []}, "pad": {"notes": pad}},
    }


def _lazy_pocket():
    # Db major, 84 BPM, neo-soul. Chart: Ebm9 | Ab13 | Dbmaj9 | Bb7(#9,b13)  (2m - 5 - 1 - 6)
    bass = [
        _n(0, .75, 39, 100), _n(.75, .25, 39, 40), _n(1.5, .5, 34, 84), _n(2.5, .5, 37, 84), _n(3, .75, 39, 92), _n(3.75, .25, 31, 76),
        _n(4, 1, 32, 100), _n(5.5, .5, 39, 84), _n(6, .25, 44, 96), _n(6.5, .5, 42, 84), _n(7.5, .5, 36, 76),
        _n(8, 1.5, 37, 100), _n(9.75, .25, 32, 72), _n(10.5, .5, 37, 84), _n(11, .5, 41, 84), _n(11.5, .25, 44, 88), _n(11.75, .25, 33, 76),
        _n(12, 1, 34, 100), _n(13.5, .5, 38, 84), _n(14, .5, 42, 88), _n(14.5, .5, 41, 84), _n(15.5, .5, 40, 80),
    ]
    comp = []
    for bar, chord in enumerate(([54, 58, 61, 65], [54, 58, 60, 65], [53, 56, 60, 63], [50, 56, 61, 66])):
        base = bar * 4
        comp.extend(_n(base - .25, 1.5, note, 72) for note in chord)  # pushed a 16th early; bar 1's push wraps to beat 15.75
        comp.extend(_n(base + 2.75, .75, note, 64) for note in chord)
    drums = []
    hat_vels = (80, 35, 55, 35)
    for bar in range(4):
        base = bar * 4
        drums.extend([_n(base, .25, 36, 112), _n(base + 1.75, .25, 36, 90), _n(base + 2.5, .25, 36, 100)])
        drums.extend([_n(base + 1.015, .25, 38, 108), _n(base + 3.015, .25, 38, 108)])  # backbeat laid back ~10 ms
        drums.extend([_n(base + 2.75, .1, 38, 30), _n(base + 3.75, .1, 38, 30)])  # ghosts
        drums.extend(_n(base + s * .25, .1, 42, hat_vels[s % 4]) for s in range(16))
    return {
        "version": 1, "id": "lazy-pocket", "title": "Lazy pocket, Db, neo-soul",
        "key": "Db major", "bpm_hint": 84, "meter": [4, 4], "length_beats": 16,
        "chords": [{"beat": 0, "name": "Ebm9", "nns": "2m9"}, {"beat": 4, "name": "Ab13", "nns": "5 13"},
                   {"beat": 8, "name": "Dbmaj9", "nns": "1maj9"}, {"beat": 12, "name": "Bb7(#9,b13)", "nns": "6 7alt"}],
        "lanes": {"bass": {"notes": bass}, "drums": {"notes": drums}, "comp": {"notes": comp}, "pad": {"notes": []}},
    }


PATTERNS = [_grandeur_lift(), _lazy_pocket()]
