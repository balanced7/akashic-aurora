"""Harmonic windows over a frozen replay, using its pedal-aware sounding durations.

Reuses the practice segmenter without starting a second piano page or a Node process.
The browser names each voicing with the live piano's pure THEORY block.
"""
from . import practice

# Audition loudness (Daniel, 2026-09-29: "when I hit the chord it sounds with the notes that I was actually
# sustaining in that time. past notes that have decayed and are barely silent should either register and play
# as such or be silent"). A struck string decays; the pedal only stops the damper. So a note is auditioned at the
# share of its strike velocity it had left when the chord began: a velocity half-life that is long in the bass
# and short in the treble (log-linear between the two anchors, clamped outside them), and a note under FADE_FLOOR
# of its strike is "barely silent": not played, listed as faded. Notes struck inside the window are fresh.
DECAY_HALF_MS = (6000.0, 1500.0)  # velocity half-life at MIDI 36 (C2) and at MIDI 96 (C7)
FADE_FLOOR = 0.12                 # below this share of the strike velocity the note is silent (and faded)


def half_life_ms(midi):
    lo, hi = DECAY_HALF_MS
    x = min(1.0, max(0.0, (midi - 36) / 60.0))
    return lo * (hi / lo) ** x


def level_at(age_ms, midi):
    """The share of its strike velocity a note has left age_ms after the strike (1.0 at the strike)."""
    return 0.5 ** (max(0.0, float(age_ms)) / half_life_ms(midi))


def harmony(cue, speed=1, lifts_ms=None, boundary="notes", carried=None):
    """lifts_ms: the session's pedal lifts inside the excerpt, in ms from its start (unscaled). With
    boundary="pedal" the segmenter cuts every window at them (practice.harmonic_windows). The cue itself
    carries no pedal (its hold_ms already includes the sustain), so lifts arrive as pedal events that only
    mark time: with explicit sound_end events, practice.sounding never ends a note at a pedal event.
    carried: {note: {"age_ms", "vel"}} for notes struck BEFORE the excerpt and still sounding at its start (the
    cue opens them at 0 ms with one mean velocity); their true age and velocity decide how loud they still are."""
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
    down_at = 0
    for lift in sorted(set(int(round(t * speed)) for t in (lifts_ms or []) if t >= 0)):
        if lift <= down_at:
            continue
        events.append({"kind": "pedal", "t_ms": down_at, "down": True, "value": 100})
        events.append({"kind": "pedal", "t_ms": lift, "down": False, "value": 0})
        down_at = lift + 1
    events.sort(key=lambda e: (e["t_ms"], e["kind"] == "on"))
    snd = practice.sounding(events)
    ctx = practice._context(snd, events, boundary)
    windows = practice.harmonic_windows(snd, boundary)["windows"]
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
        # Each note at the loudness it had left when this chord began (a): its freshest sounding strike wins; a
        # strike carried in from before the excerpt adds the age the cue could not carry.
        levels, vels = {}, {}
        for note in notes:
            best, vel = -1.0, 0
            for s in sounding:
                if s["note"] != note:
                    continue
                age, v = max(0.0, a - s["on_ms"]), s["vel"]
                if carried and s["on_ms"] <= 0 and note in carried:
                    age += float(carried[note].get("age_ms") or 0)
                    v = carried[note].get("vel") or v
                lv = level_at(age, note)
                if lv > best:
                    best, vel = lv, v
            levels[note], vels[note] = best, vel
        audible = [n for n in notes if levels[n] >= FADE_FLOOR]
        faded = [n for n in notes if levels[n] < FADE_FLOOR]
        if not audible:
            continue  # everything the analysis heard here had faded: silent, as asked
        velocities = {n: max(1, min(127, round(vels[n] * levels[n]))) for n in audible}
        result.append({"start_ms": a, "end_ms": b, "notes": audible, "velocities": velocities,
                       "levels": {n: round(levels[n], 3) for n in notes}, "faded": faded,
                       "texture": window["texture"], "grouped": window["merged"] > 1})
    return result


def theory_module(source):
    """Same marker contract as practice_theory.mjs; no DOM/Three.js imports."""
    text = source.read_text(encoding="utf-8")
    start, end = text.find("// ===== THEORY BEGIN"), text.find("// ===== THEORY END")
    if start < 0 or end <= start:
        raise ValueError("Piano THEORY markers are missing")
    return (text[start:end] + "\nexport default Theory;\n").encode("utf-8")
