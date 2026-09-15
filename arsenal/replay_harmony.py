"""Harmonic windows over a frozen replay, using its pedal-aware sounding durations.

Reuses the practice segmenter without starting a second piano page or a Node process.
The browser names each voicing with the live piano's pure THEORY block.
"""
from . import practice


def harmony(cue, speed=1):
    # Cue time may be scaled by the link verb. UI windows always use source time.
    events = []
    for step in cue["steps"]:
        start = round(step["at_ms"] * speed)
        end = round((step["at_ms"] + step["hold_ms"]) * speed)
        for note in step["notes"]:
            events.extend([
                {"kind": "on", "t_ms": start, "note": note, "vel": step["velocity"]},
                {"kind": "off", "t_ms": end, "note": note},
                {"kind": "sound_end", "t_ms": end, "note": note, "by": "replay"},
            ])
    # Ends precede re-strikes at the same instant. Key release is deliberately not
    # used: a replay's hold_ms already includes the original sustain pedal.
    events.sort(key=lambda e: (e["t_ms"], e["kind"] == "on"))
    snd = practice.sounding(events)
    ctx = practice._context(snd, events)
    windows = practice.harmonic_windows(snd)["windows"]
    for window in windows:
        practice._facts(window, ctx)
    windows = practice.merge_growth(windows, ctx)
    result = []
    for window in windows:
        a, b = window["start_ms"], window["end_ms"]
        sounding = [n for n in snd["notes"] if n["on_ms"] < b and n["end_ms"] > a]
        if not sounding:
            continue
        # The analysis can include a brief rest in a phrase. The replay highlight
        # must stop when its last note stops, even before the next phrase begins.
        a = max(a, min(n["on_ms"] for n in sounding))
        b = min(b, max(n["end_ms"] for n in sounding))
        # The namer may choose a representative octave. Only retain pitches that
        # really occur in this window; never audition an invented octave or third.
        present = {n["note"] for n in sounding}
        notes = [n for n in window["detect_notes"] if n in present]
        if not notes:
            continue
        velocities = {n: round(sum(s["vel"] for s in sounding if s["note"] == n) /
                               sum(1 for s in sounding if s["note"] == n)) for n in notes}
        result.append({"start_ms": a, "end_ms": b, "notes": notes, "velocities": velocities,
                       "texture": window["texture"], "grouped": window["merged"] > 1})
    return result


def theory_module(source):
    """Same marker contract as practice_theory.mjs; no DOM/Three.js imports."""
    text = source.read_text(encoding="utf-8")
    start, end = text.find("// ===== THEORY BEGIN"), text.find("// ===== THEORY END")
    if start < 0 or end <= start:
        raise ValueError("Piano THEORY markers are missing")
    return (text[start:end] + "\nexport default Theory;\n").encode("utf-8")
