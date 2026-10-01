"""Harmonic windows over a frozen replay, using its pedal-aware sounding durations.

Reuses the practice segmenter without starting a second piano page or a Node process.
The browser names each voicing with the live piano's pure THEORY block.
"""

import math

from . import practice

# Audition loudness (Daniel, 2026-09-29: "when I hit the chord it sounds with the notes that I was actually
# sustaining in that time. past notes that have decayed and are barely silent should either register and play
# as such or be silent"). A struck string decays; the pedal only stops the damper. So a note is auditioned at the
# AMPLITUDE it had left at the instant the chord was whole, and that amplitude is turned back into a velocity by
# inverting the voice's own loudness curve -- because the keys voice maps velocity to loudness as
# peak = VOICE_LEVEL * (0.06 + 0.94 * (vel/127) ** 1.6) (arsenal/web/piano/cues.js:1455), so half the velocity is
# -7.8 dB, not half as loud (Heimdall, measured, 2026-09-29). The decay rate is a T60: the time to fall 60 dB,
# 20 s at C2 and 3 s at C7 (log-linear between, clamped outside), which is the calibration the first model
# stated and then missed by 3-4x. The voice has no gate: its quietest strike still peaks at VOICE_LEVEL * 0.06,
# so a note that has decayed below that plays at velocity 1 -- as quiet as the voice can say it -- and only a
# note more than SILENT_DB below its strike is silent, and listed as faded.
VOICE_LEVEL, VOICE_FLOOR, VOICE_GAIN, VOICE_EXP = 0.2, 0.06, 0.94, 1.6  # mirror of cues.js:1049 and :1455
DECAY_T60_S = (20.0, 3.0)  # seconds to fall 60 dB, at MIDI 36 (C2) and MIDI 96 (C7)
SILENT_DB = -40.0  # below this, relative to the strike, the note is silent and faded


def t60_s(midi):
    lo, hi = DECAY_T60_S
    x = min(1.0, max(0.0, (midi - 36) / 60.0))
    return lo * (hi / lo) ** x


def amplitude_at(age_ms, midi):
    """The share of its strike AMPLITUDE a note has left age_ms after the strike (1.0 at the strike):
    -60 dB at t60_s(midi), exponentially."""
    return 10.0 ** (-3.0 * max(0.0, float(age_ms)) / 1000.0 / t60_s(midi))


def peak_of(velocity):
    """The voice's peak level for a velocity 1..127 (cues.js:1455)."""
    v = min(127, max(0, float(velocity))) / 127.0
    return VOICE_LEVEL * (VOICE_FLOOR + VOICE_GAIN * v**VOICE_EXP)


def velocity_for_peak(peak):
    """The velocity whose voice peak is `peak`, inverting peak_of; 1 for anything the voice cannot play
    quieter than, 127 for anything above a full strike."""
    x = (float(peak) / VOICE_LEVEL - VOICE_FLOOR) / VOICE_GAIN
    if x <= 0.0:
        return 1
    return int(min(127, max(1, round(127.0 * x ** (1.0 / VOICE_EXP)))))


def densest_instant(sounding, a, b):
    """The first instant in [a, b) at which the most of these notes sound together: the moment the chord was
    whole. Candidates are the window start and every onset inside it."""
    best_t, best_n = a, -1
    for t in sorted({a} | {s["on_ms"] for s in sounding if a <= s["on_ms"] < b}):
        n = sum(1 for s in sounding if s["on_ms"] <= t < s["end_ms"])
        if n > best_n:
            best_t, best_n = t, n
    return best_t


def level_at(age_ms, midi):
    """Kept for callers of the first model: the amplitude share (see amplitude_at)."""
    return amplitude_at(age_ms, midi)


def harmony(cue, speed=1, lifts_ms=None, boundary="notes", carried=None, theory_source=None, node=None):
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
            events.extend(
                [
                    {"kind": "on", "t_ms": start, "note": note, "vel": step["velocity"]},
                    {"kind": "off", "t_ms": end, "note": note},
                    {"kind": "sound_end", "t_ms": end, "note": note, "by": "replay"},
                ]
            )
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
    # The SAME pipeline as practice.analyze(): early merges, naming, late merges -- one segmentation.
    windows = practice.merge_early(practice.harmonic_windows(snd, boundary)["windows"], ctx)
    practice.name_windows(windows, theory_source, node)
    windows = practice.merge_late(windows, ctx)
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
        # Each note as it sounded at the instant the chord was WHOLE (the densest instant of the window): the
        # loudest strike sounding then wins; a strike carried in from before the excerpt adds the age the cue
        # could not carry. Loudness is amplitude through the voice's curve, turned back into a velocity.
        at = densest_instant(sounding, a, b)
        db, vels, present_at = {}, {}, {}
        for note in notes:
            best_amp, best_ratio, vel = -1.0, 0.0, 0
            for s in sounding:
                if s["note"] != note or not (s["on_ms"] <= at < s["end_ms"]):
                    continue
                age, v = max(0.0, at - s["on_ms"]), s["vel"]
                if carried and s["on_ms"] <= 0 and note in carried:
                    age += float(carried[note].get("age_ms") or 0)
                    v = carried[note].get("vel") or v
                ratio = amplitude_at(age, note)
                amp = peak_of(v) * ratio
                if amp > best_amp:
                    best_amp, best_ratio, vel = amp, ratio, v
            if best_amp < 0:
                continue  # not sounding at the instant the chord was whole: not part of the audition
            present_at[note] = best_amp
            db[note] = round(20.0 * math.log10(max(best_ratio, 1e-9)), 1)
            vels[note] = vel
        audible = [n for n in notes if n in present_at and db[n] >= SILENT_DB]
        faded = [n for n in notes if n in present_at and db[n] < SILENT_DB]
        if not audible:
            continue  # everything the analysis heard here had faded: silent, as asked
        velocities = {n: velocity_for_peak(present_at[n]) for n in audible}
        result.append(
            {
                "start_ms": a,
                "end_ms": b,
                "at_ms": at,
                "notes": audible,
                "velocities": velocities,
                "db": db,
                "faded": faded,
                "texture": window["texture"],
                "grouped": window["merged"] > 1,
            }
        )
    return result


def theory_module(source):
    """Same marker contract as practice_theory.mjs; no DOM/Three.js imports."""
    text = source.read_text(encoding="utf-8")
    start, end = text.find("// ===== THEORY BEGIN"), text.find("// ===== THEORY END")
    if start < 0 or end <= start:
        raise ValueError("Piano THEORY markers are missing")
    return (text[start:end] + "\nexport default Theory;\n").encode("utf-8")
