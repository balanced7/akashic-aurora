"""Name a chord from a set of held MIDI notes. Small, not a jazz oracle -- common triads/7ths/sus/add9 + slashes."""
from __future__ import annotations

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# intervals-from-root (pitch classes) -> quality symbol
QUALITIES = {
    frozenset({0, 7}): "5",            # power chord
    frozenset({0, 4, 7}): "",          # major
    frozenset({0, 3, 7}): "m",
    frozenset({0, 3, 6}): "dim",
    frozenset({0, 4, 8}): "aug",
    frozenset({0, 2, 7}): "sus2",
    frozenset({0, 5, 7}): "sus4",
    frozenset({0, 4, 7, 11}): "maj7",
    frozenset({0, 4, 7, 10}): "7",
    frozenset({0, 3, 7, 10}): "m7",
    frozenset({0, 3, 6, 9}): "dim7",
    frozenset({0, 3, 6, 10}): "m7b5",
    frozenset({0, 4, 7, 9}): "6",
    frozenset({0, 3, 7, 9}): "m6",
    frozenset({0, 4, 7, 2}): "add9",
    frozenset({0, 3, 7, 2}): "madd9",
    frozenset({0, 5, 7, 10}): "7sus4",
    frozenset({0, 4, 7, 10, 2}): "9",
    frozenset({0, 4, 7, 11, 2}): "maj9",
    frozenset({0, 3, 7, 10, 2}): "m9",
}


def analyze(notes):
    """(name, root_pc, quality_symbol). root/quality are None for an un-named note set; 'note' for a lone note."""
    notes = sorted(notes)
    if not notes:
        return (None, None, None)
    pcs = sorted(set(n % 12 for n in notes))
    if len(pcs) == 1:
        return (NOTE_NAMES[pcs[0]], pcs[0], "note")
    bass = notes[0] % 12
    fallback = None
    for root in pcs:
        sym = QUALITIES.get(frozenset((pc - root) % 12 for pc in pcs))
        if sym is None:
            continue
        name = NOTE_NAMES[root] + sym
        if root == bass:
            return (name, root, sym)                       # root-position: the clean read
        if fallback is None:
            fallback = (name + "/" + NOTE_NAMES[bass], root, sym)   # inversion: name/bass
    if fallback:
        return fallback
    return (" ".join(NOTE_NAMES[p] for p in pcs), None, None)       # unknown set: just list the notes


def name_chord(notes) -> str | None:
    """Just the chord name (or a single note, or a note list)."""
    return analyze(notes)[0]
