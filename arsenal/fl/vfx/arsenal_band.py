# Arsenal band: Claude's bass, drums, comp and pad patterns, played on FL Studio's own clock.
#
# This whole file is one VFX Script. Paste it into a VFX Script instance inside Patcher (FL Studio 2026,
# 26.1.3 or later) and compile. It imports its patterns from arsenal_patterns.py in
# [User Data Folder]/VFX Script/Python (the import folder added in 26.1 Beta 2, WhatsNew #21719); with no
# such module it plays a one-bar fallback groove so first light still makes a sound.
# Install steps, controls and the drills that still need FL: arsenal/fl/vfx/README.md (Akashic Aurora repo).
#
# Every flvfx name below is one that FL's factory presets or Image-Line's VFX Script manual page use.
# Presets read, read-only, on 2026-09-14, under
# C:/Program Files/Image-Line/FL Studio 2026/Data/Patches/Plugin presets/Effects/VFX Script/ :
#   Tutorial Scripts/Tutorial 3 - Voice Generation.fst          vfx.Voice() built in onTick, length in ticks, trigger()
#   Random Sequencer.fst                                        generation gated on vfx.context.isPlaying
#   X BinaryBorn/Generators/Random Notes.fst                    release every vfx.context.voices entry when stopped
#   X BinaryBorn/Voice Utils/Voice Output Switch.fst            voice.output, 0 to 15
#   Voice Cycler.fst                                            "Extra voice outputs must be activated for use"
#   X BinaryBorn/Timer/Timer (BPM).fst                          vfx.context.tempo; ticks run backwards on a jump
#   Tutorial Scripts/Tutorial 4 - Control Signal Generation.fst 'Group: Name' inputs, vfx.addOutputController
#   X BinaryBorn/Voice Utils/Voice Construct.fst                a fresh vfx.Voice() released by hand
#
# Timing model: the band schedules on vfx.context.ticks and vfx.context.PPQ only, never on tempo, so FL
# tempo changes and automation cannot shift a bar line. FL may call onTick less often than every tick and
# unevenly, so the band plays every tick since the last call. When FL's ticks fall, that is a loop wrap only
# if a loop span an exact earlier wrap showed explains it (or, with none known, a whole number of bars within
# FL's usual gap); anything else is a seek. Keep counting counts on through a wrap by the ticks that really
# passed, and on a seek or jump releases what rings and re-anchors to FL's bar lines (ticks modulo the bar).
# Follow song position plays the end of the loop FL passed before a wrap as well as the loop top. Ticks FL
# did not play (the playhead nudged while paused, the loop's end when a late onTick could have been a seek
# back to the loop top) are counted but not sounded. Every note is triggered with its
# length set (FL's own countdown is the safety net if this script ever stops running) and is also released
# by the band at its end, on stop, on a jump, on a pattern switch, on a mute, on a dropout bar and on panic,
# but only while FL still lists it in vfx.context.voices (matched by identity, or by the band's own note and
# output bookkeeping when FL hands back wrapper objects), so a voice is never released twice. A voice is
# never released in the onTick that triggered it (that would be a note of no length): its release waits for
# the next onTick.
#
# Keep this file ASCII: FL 26 fixed "invalid characters when loading a file from an external editor" (#20438).

try:
    import flvfx as vfx
except ImportError:  # outside FL the pattern parsers below still work; the tests inject a mock flvfx
    vfx = None
import sys

try:
    import os
except Exception:
    os = None
try:
    import json
except Exception:
    json = None

BAND_VERSION = 1
PATTERN_FORMAT_VERSION = 1
PATTERN_MODULE = "arsenal_patterns"
LANES = ("bass", "drums", "comp", "pad")
BASS_LANE = 0
DRUM_LANE = 1
MAX_PATTERNS = 64
MAX_NOTES_PER_LANE = 4096
HUMANIZE_SPAN = 20  # velocity steps either way at Humanize = 1
GAP_MEMORY = 32     # onTick gaps remembered, to judge how far FL can move between two calls

SWITCH_CHOICES = ["Next bar", "Next loop"]
LANE_CHOICES = ["All lanes on outputs 1-4", "Bass", "Drums", "Comp", "Pad"]
CLOCK_CHOICES = ["Keep counting", "Follow song position"]
GRID_CHOICES = ["16th", "8th"]
GRID_BEATS = (0.25, 0.5)
DROPOUT_CHOICES = ["Off", "Rare", "Often"]
DROPOUT_CHANCE = (0.0, 0.1, 0.3)  # a bar's base roll, shaped by PHRASE_WEIGHT; a bar after a rolled one never rests
PHRASE_WEIGHT = (0.5, 0.75, 0.5, 2.25)  # by place in a 4-bar phrase: bar 4 (before a phrase top) rolls most, then bar 2
DROPOUT_SEEDS = 100
SWITCH_NEXT_BAR, SWITCH_NEXT_LOOP = 0, 1
CLOCK_COUNT, CLOCK_SONG = 0, 1
WRAP = None         # in a tick window: FL's loop wraps here (Follow song position ends everything ringing)
HELD_LANES = (2, 3)  # comp and pad: struck again on the bar after a dropout bar if they would still ring

C_PATTERN = "Band: Pattern"
C_SWITCH = "Band: Switch at"
C_LANE = "Band: Lane"
C_CLOCK = "Band: Clock"
C_SWING = "Feel: Swing"
C_GRID = "Feel: Swing grid"
C_HUMANIZE = "Feel: Humanize"
C_DRUM_MAP = "Feel: Drum map"
C_DROPOUT = "Feel: Dropout"
C_DROPOUT_SEED = "Feel: Dropout seed"
C_MUTES = ("Mute: Bass", "Mute: Drums", "Mute: Comp", "Mute: Pad")
C_LIVE = "Patterns: Live file"
C_RELOAD = "Patterns: Reload"
C_PANIC = "Patterns: Panic"
BAR_PULSE = "Bar pulse"

# Drum maps. Patterns always carry General MIDI drum notes; a map turns them into what the drum plugin expects.
# FPC: Image-Line's FPC manual says the "Empty" preset's pads "are already assigned to the appropriate General
# MIDI keys", so GM passes through and only rarer GM pieces fold onto the core kit.
FPC_FOLD = {
    35: 36,  # acoustic bass drum -> bass drum
    40: 38,  # electric snare -> snare
    44: 42,  # pedal hi-hat -> closed hi-hat
    52: 49,  # chinese cymbal -> crash
    55: 49,  # splash -> crash
    57: 49,  # crash 2 -> crash
    53: 51,  # ride bell -> ride
    59: 51,  # ride 2 -> ride
}
# Addictive Drums 2 factory keymap, decoded from XLN's own "Addictive Drums 2 Keymap.pdf" (dated June 2, 2021)
# in Documents/Addictive Drums 2/App/ADBV0002/Manuals. It is not GM: hats sit on 48-59, ride on 60-63, toms on
# 65-72, cymbals from 77. GM notes without a sensible AD2 piece are dropped rather than sounding a wrong one.
# If AD2 has its GM map preset loaded, choose "GM" instead.
AD2_DEFAULT = {
    35: 36,  # acoustic bass drum -> Kick
    36: 36,  # bass drum -> Kick
    37: 42,  # side stick -> Snare SideStick
    38: 38,  # snare -> Snare Open Hit
    39: 37,  # hand clap -> Snare Rimshot (AD2 has no clap)
    40: 38,  # electric snare -> Snare Open Hit
    41: 65,  # low floor tom -> Tom 4 Open Hit
    42: 49,  # closed hi-hat -> HiHat Closed 1 Tip
    43: 67,  # high floor tom -> Tom 3 Open Hit
    44: 48,  # pedal hi-hat -> HiHat Pedal Closed
    45: 67,  # low tom -> Tom 3 Open Hit
    46: 55,  # open hi-hat -> HiHat Open B
    47: 69,  # low-mid tom -> Tom 2 Open Hit
    48: 69,  # hi-mid tom -> Tom 2 Open Hit
    49: 77,  # crash 1 -> Cymbal 1 Hit
    50: 71,  # high tom -> Tom 1 Open Hit
    51: 60,  # ride 1 -> Ride 1 Tip
    52: 81,  # chinese cymbal -> Cymbal 3 Hit (which cymbal is a china depends on the kit)
    53: 61,  # ride bell -> Ride 1 Bell
    55: 89,  # splash -> Cymbal 4 Hit (kit-dependent)
    57: 79,  # crash 2 -> Cymbal 2 Hit
    59: 84,  # ride 2 -> Ride 2 Tip
}
# (name, table, passthrough): with passthrough a note missing from the table plays unchanged, without it the note is dropped
DRUM_MAPS = [("GM", {}, True), ("FPC", FPC_FOLD, True), ("AD2 default", AD2_DEFAULT, False)]

FALLBACK_PATTERN = {
    "version": 1, "id": "arsenal-band-fallback", "title": "Fallback groove (no arsenal_patterns module)",
    "key": "C major", "bpm_hint": 90, "meter": [4, 4], "length_beats": 4,
    "chords": [{"beat": 0, "name": "C", "nns": "1"}],
    "lanes": {
        "bass": {"notes": [{"beat": 0, "len": 1.5, "note": 36, "vel": 100},
                           {"beat": 2.5, "len": 0.5, "note": 43, "vel": 88}]},
        "drums": {"notes": [{"beat": 0, "len": 0.25, "note": 36, "vel": 110},
                            {"beat": 2.5, "len": 0.25, "note": 36, "vel": 96},
                            {"beat": 1, "len": 0.25, "note": 38, "vel": 104},
                            {"beat": 3, "len": 0.25, "note": 38, "vel": 104}]
                           + [{"beat": b * 0.5, "len": 0.1, "note": 42, "vel": 72 if b % 2 == 0 else 46} for b in range(8)]},
        "comp": {"notes": []},
        "pad": {"notes": [{"beat": 0, "len": 4, "note": n, "vel": 56} for n in (52, 55, 60)]},
    },
}


class PatternError(ValueError):
    """A pattern set, playlist or drum map that breaks the version 1 contract."""


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x not in (float("inf"), float("-inf"))


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def parse_pattern_set(d, where="pattern"):
    """Check one pattern set against the version 1 contract and return the band's normalized form.

    Strict on purpose: a broken set is refused whole, so a half-written or mistyped pattern never plays.
    Beats may lie outside the loop (a push at -0.25 is the last 16th of the loop); they wrap.
    """
    if not isinstance(d, dict):
        raise PatternError(where + ": a pattern set must be an object")
    if d.get("version") != PATTERN_FORMAT_VERSION:
        raise PatternError(where + ": version must be 1, got %r" % (d.get("version"),))
    pid = d.get("id")
    if not isinstance(pid, str) or not pid:
        raise PatternError(where + ": id must be a non-empty string")
    title = d.get("title", pid)
    if not isinstance(title, str):
        raise PatternError(where + ": title must be a string")
    meter = d.get("meter", [4, 4])
    if (not isinstance(meter, (list, tuple)) or len(meter) != 2 or not _is_int(meter[0]) or not _is_int(meter[1])
            or meter[0] < 1 or meter[1] not in (1, 2, 4, 8, 16, 32)):
        raise PatternError(where + ": meter must be [beats, 1|2|4|8|16|32], got %r" % (meter,))
    bar_beats = meter[0] * 4.0 / meter[1]
    length = d.get("length_beats")
    if not _is_number(length) or length <= 0:
        raise PatternError(where + ": length_beats must be a positive number")
    bars = length / bar_beats
    if bars < 1 or abs(bars - round(bars)) > 1e-9:
        raise PatternError(where + ": length_beats %r is not whole bars of %d/%d" % (length, meter[0], meter[1]))
    chords = d.get("chords", [])
    if not isinstance(chords, list):
        raise PatternError(where + ": chords must be a list")
    lanes = d.get("lanes")
    if not isinstance(lanes, dict):
        raise PatternError(where + ": lanes must be an object")
    for name in lanes:
        if name not in LANES:
            raise PatternError(where + ": unknown lane %r (lanes are bass, drums, comp, pad)" % (name,))
    parsed = {}
    for lane in LANES:
        spec = lanes.get(lane)
        if spec is None:
            parsed[lane] = []
            continue
        notes = spec.get("notes") if isinstance(spec, dict) else None
        if not isinstance(notes, list):
            raise PatternError(where + ": lanes.%s must be an object with a notes list" % lane)
        if len(notes) > MAX_NOTES_PER_LANE:
            raise PatternError(where + ": lanes.%s has more than %d notes" % (lane, MAX_NOTES_PER_LANE))
        out = []
        for i, n in enumerate(notes):
            w = "%s: lanes.%s.notes[%d]" % (where, lane, i)
            if not isinstance(n, dict):
                raise PatternError(w + " must be an object")
            beat, ln, note, vel = n.get("beat"), n.get("len"), n.get("note"), n.get("vel")
            if not _is_number(beat):
                raise PatternError(w + ": beat must be a number")
            if not _is_number(ln) or ln <= 0:
                raise PatternError(w + ": len must be a positive number")
            if not _is_int(note) or not 0 <= note <= 127:
                raise PatternError(w + ": note must be an integer 0-127")
            if not _is_int(vel) or not 1 <= vel <= 127:
                raise PatternError(w + ": vel must be an integer 1-127")
            out.append((float(beat), float(ln), note, vel))
        parsed[lane] = out
    return {"id": pid, "title": title, "meter": (meter[0], meter[1]), "bar_beats": bar_beats,
            "length_beats": float(length), "lanes": parsed}


def parse_playlist(doc, where="playlist"):
    """A live playlist: {"version": 1, "rev": any, "current": int, "patterns": [pattern sets]}.

    A bare pattern set, or a bare list of them, is accepted as a playlist too. All or nothing: one bad set
    refuses the whole file, so indexes never shift under the Pattern knob.
    """
    if isinstance(doc, dict) and "lanes" in doc:
        return {"patterns": [parse_pattern_set(doc, where)], "current": 0, "rev": None}
    rev = None
    current = 0
    if isinstance(doc, list):
        items = doc
    elif isinstance(doc, dict):
        if doc.get("version") != PATTERN_FORMAT_VERSION:
            raise PatternError(where + ": version must be 1, got %r" % (doc.get("version"),))
        items = doc.get("patterns")
        current = doc.get("current", 0)
        rev = doc.get("rev")
        if not _is_int(current) or current < 0:
            raise PatternError(where + ": current must be a non-negative integer")
    else:
        raise PatternError(where + ": must be an object or a list")
    if not isinstance(items, list) or not items:
        raise PatternError(where + ": patterns must be a non-empty list")
    if len(items) > MAX_PATTERNS:
        raise PatternError(where + ": at most %d patterns" % MAX_PATTERNS)
    patterns = [parse_pattern_set(p, "%s: patterns[%d]" % (where, i)) for i, p in enumerate(items)]
    return {"patterns": patterns, "current": min(current, len(patterns) - 1), "rev": rev}


def parse_drum_maps(obj, where="DRUM_MAPS"):
    """Extra maps from the patterns module: {"name": {gm_note: target_note}}; notes missing from a map are dropped."""
    if not isinstance(obj, dict):
        raise PatternError(where + " must be a dict of name -> {gm_note: note}")
    out = []
    for name, table in obj.items():
        if not isinstance(name, str) or not name or "," in name or not isinstance(table, dict):
            raise PatternError(where + ": map names must be strings without commas, each with a dict")
        clean = {}
        for k, v in table.items():
            key = int(k) if isinstance(k, str) and k.isdigit() else k
            if not _is_int(key) or not _is_int(v) or not 0 <= key <= 127 or not 0 <= v <= 127:
                raise PatternError(where + ": map %r must map notes 0-127 to notes 0-127" % (name,))
            clean[key] = v
        out.append((name, clean, False))
    return out


def placeholder_pattern(message, index):
    """A silent 4/4 bar standing in for a refused baked pattern, so the Pattern knob's indexes stay put."""
    return {"id": "invalid-%d" % index, "title": "INVALID: " + message[:120], "meter": (4, 4), "bar_beats": 4.0,
            "length_beats": 4.0, "lanes": dict((lane, []) for lane in LANES)}


def swing_beat(beat, amount, grid):
    """Delay notes on the off positions of the swing grid by amount * grid / 3 (amount 1 = triplet feel)."""
    g = beat / grid
    k = int(round(g))
    if k % 2 == 1 and abs(g - k) < 1e-6:
        return beat + amount * grid / 3.0
    return beat


def _hash32(a, b):
    h = (a * 2654435761 + b * 2246822519 + 374761393) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h


def humanize_velocity(vel, eid, loop_n, amount):
    """Velocity nudged by up to amount * HUMANIZE_SPAN, fixed for a given note and loop so a take can be replayed."""
    r = _hash32(eid, loop_n & 0xFFFF) / 2147483647.5 - 1.0
    v = int(round(vel + r * amount * HUMANIZE_SPAN))
    return 1 if v < 1 else (127 if v > 127 else v)


def _dropout_roll(seed, n, chance):
    weighted = 1.0 - (1.0 - chance) ** PHRASE_WEIGHT[n % len(PHRASE_WEIGHT)]
    return _hash32((n & 0xFFFFFF) * 31 + 17, (seed & 0xFFFF) + 40503) / 4294967296.0 < weighted


def dropout_bar(seed, n, chance):
    """True when bar n (counted from the bar a pattern started on) is a dropout bar, where every lane but bass rests.

    Fixed by seed and bar, so a take replays and every band instance on the same seed rests on the same bars. Bar 0
    never rests, and a bar rests only when the bar before it did not roll, so two never come in a row. A rest reads as
    a breath at a phrase end, so the roll leans on the 4th bar of each 4-bar phrase (bars 4, 8, 12 counted from 1),
    then the 2nd; bars 1 and 3 rest least (PHRASE_WEIGHT).
    """
    if chance <= 0.0 or n == 0:
        return False
    return _dropout_roll(seed, n, chance) and not _dropout_roll(seed, n - 1, chance)


def pattern_knob_value(index):
    """The normalized value that sets the Pattern knob (0 to MAX_PATTERNS - 1) to index.

    A quarter step above the index, not index / 63: FL reads that back as index whether it rounds or truncates, even
    after keeping it as a float32 or on a 16-bit step, where index / 63 can read back one pattern low.
    """
    top = MAX_PATTERNS - 1
    index = max(0, min(int(index), top))
    return 1.0 if index == top else (index + 0.25) / top


def _ascii(text):
    return "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)


def _short(exc):
    return _ascii("%s: %s" % (type(exc).__name__, exc))[:160]


class Compiled(object):
    """One pattern laid out in ticks: loop and bar length, the events starting at each tick of the loop, and the
    comp and pad events in start order (held, for striking a chord again after a dropout bar)."""
    __slots__ = ("ppq", "loop", "bar", "read_at", "at", "count", "held")

    def __init__(self, pattern, ppq, swing=0.0, grid=0.25):
        self.ppq = ppq
        length = pattern["length_beats"]
        self.bar = max(1, int(round(pattern["bar_beats"] * ppq)))
        self.loop = self.bar * max(1, int(round(length / pattern["bar_beats"])))
        self.read_at = self.bar - min(ppq, self.bar)  # the live file is read one beat before each bar line
        at = {}
        held = []
        eid = 0
        for lane_i, lane in enumerate(LANES):
            for beat, ln, note, vel in pattern["lanes"][lane]:
                b = beat % length
                if swing > 0.0:
                    b = swing_beat(b, swing, grid)
                tick = int(round(b * ppq)) % self.loop
                ticks = max(1, int(round(ln * ppq)))
                at.setdefault(tick, []).append((eid, lane_i, note, vel, ticks))
                if lane_i in HELD_LANES:
                    held.append((tick, eid, lane_i, note, vel, ticks))
                eid += 1
        self.at = at
        self.count = eid
        held.sort()
        self.held = held


class _Entry(object):
    """The band's own record of one voice it triggered: which note on which output, from which band tick to which,
    and in which onTick call."""
    __slots__ = ("voice", "lane", "output", "note", "start", "end", "alive", "call", "vel")

    def __init__(self, voice, lane, output, note, start, end, call=0, vel=0):
        self.voice, self.lane, self.output, self.note = voice, lane, output, note
        self.start, self.end, self.alive, self.call, self.vel = start, end, True, call, vel


class Band(object):
    def __init__(self):
        self.log = []
        self.switches = []        # (tick or None when stopped, index, anchor before, bar ticks before)
        self.live_reads = 0
        self.module_status = "patterns module not loaded"
        self.baked = [parse_pattern_set(FALLBACK_PATTERN, "fallback")]
        self.live_path = None
        self.live = None
        self.live_sig = None
        self.live_text = None
        self.live_error = None
        self.drum_maps = list(DRUM_MAPS)
        self.current = 0
        self.pattern = self.baked[0]
        self.pending = None
        self.compiled = None
        self.anchor = 0           # band tick where the running pattern's beat 0 sits
        self.band_t = -1          # last band tick processed
        self.last_ticks = None    # FL ticks at the last played onTick
        self.gaps = []            # recent FL ticks between played onTicks (forward moves of at most a beat)
        self.loop_span = None     # FL's loop span (end - start), once a loop wrap has shown it
        self.parked_at_zero = False  # FL reported tick 0 while stopped since the last played onTick (a Stop)
        self.quiet = 0            # how many leading ticks of this onTick's window are counted but not sounded
        self.deferred = []        # entries whose release waits for the next onTick (they started in this one)
        self.was_playing = False
        self.restart = True       # the next Play starts fresh at bar 1
        self.ppq = None
        self.poll_every = 4
        self.calls = 0
        self.next_poll = 0
        self.sounding = []
        self.due = {}
        self.fired = {}
        self.has_pulse = False
        self.pulse_off = None
        self.knob_seen = None
        self.switch_at = SWITCH_NEXT_BAR
        self.lane_sel = 0
        self.clock = CLOCK_COUNT
        self.swing = 0.0
        self.grid = 0
        self.humanize = 0.0
        self.drum_map = 0
        self.dropout = 0
        self.dropout_seed = 0
        self.drop_t = None        # band tick of the bar the dropout decision below is for
        self.drop_now = False     # whether that bar rests
        self.switch_t = None      # band tick of the last pattern switch
        self.mutes = [False, False, False, False]
        self.live_on = False

    # -- patterns ---------------------------------------------------------------------------------------------

    def _log(self, message):
        self.log.append(message)
        del self.log[:-50]
        try:
            print("[arsenal band] " + message)
        except Exception:
            pass

    def load_module(self):
        """Import (or re-import) arsenal_patterns. A missing or broken module leaves the band playing something."""
        mod = None
        try:
            cached = sys.modules.get(PATTERN_MODULE)
            if cached is not None and getattr(cached, "__file__", None):
                import importlib
                mod = importlib.reload(cached)  # a recompile or Reload picks up a regenerated file
            elif cached is not None:
                mod = cached
            else:
                mod = __import__(PATTERN_MODULE)
        except Exception as exc:
            mod = sys.modules.get(PATTERN_MODULE)
            if mod is None:
                self.module_status = "%s not importable (%s); playing the fallback groove" % (PATTERN_MODULE, _short(exc))
                self._log(self.module_status)
                self.baked = [parse_pattern_set(FALLBACK_PATTERN, "fallback")]
                return False
        patterns = getattr(mod, "PATTERNS", None)
        if getattr(mod, "VERSION", PATTERN_FORMAT_VERSION) != PATTERN_FORMAT_VERSION or not isinstance(patterns, (list, tuple)) or not patterns:
            self.module_status = "%s has no version 1 PATTERNS list; playing the fallback groove" % PATTERN_MODULE
            self._log(self.module_status)
            self.baked = [parse_pattern_set(FALLBACK_PATTERN, "fallback")]
            return False
        baked = []
        refused = 0
        for i, p in enumerate(list(patterns)[:MAX_PATTERNS]):
            try:
                baked.append(parse_pattern_set(p, "PATTERNS[%d]" % i))
            except PatternError as exc:
                refused += 1
                baked.append(placeholder_pattern(str(exc), i))
                self._log("refused " + _ascii(str(exc)))
        self.baked = baked
        live_path = getattr(mod, "LIVE_PATH", None)
        self.live_path = live_path if isinstance(live_path, str) and live_path else None
        maps = list(DRUM_MAPS)
        extra = getattr(mod, "DRUM_MAPS", None)
        if extra:
            try:
                maps.extend(parse_drum_maps(extra))
            except PatternError as exc:
                self._log("refused " + _ascii(str(exc)))
        self.drum_maps = maps
        self.module_status = "%d patterns from %s%s" % (len(baked), PATTERN_MODULE, (" (%d refused)" % refused) if refused else "")
        self._log(self.module_status)
        return True

    def playlist(self):
        if self.live_on and self.live is not None:
            return self.live["patterns"]
        return self.baked

    def describe(self):
        lines = ["Arsenal band v%d. Plays Claude's patterns on FL's clock; pattern switches land on bar lines." % BAND_VERSION,
                 "", _ascii(self.module_status)]
        for i, p in enumerate(self.baked[:16]):
            lines.append("%d  %s" % (i, _ascii(p["title"])))
        if self.live_path:
            lines.append("Live file: " + _ascii(self.live_path))
        return "\r\n".join(lines)

    def drum_map_names(self):
        return [name for name, _table, _passthrough in self.drum_maps]

    def read_live(self, defer):
        """Read the live playlist when it changed; a missing, unreadable or broken file keeps the last good one."""
        path = self.live_path
        if not path or json is None:
            return
        self.live_reads += 1
        sig = None
        try:
            if os is not None:
                st = os.stat(path)
                sig = (st.st_mtime_ns, st.st_size)
                if sig == self.live_sig:
                    return
            f = open(path, "r", encoding="utf-8")
            try:
                text = f.read()
            finally:
                f.close()
        except Exception as exc:
            self._live_problem("cannot read the live file: " + _short(exc))
            return
        self.live_sig = sig
        if text == self.live_text:
            return
        self.live_text = text
        try:
            playlist = parse_playlist(json.loads(text), "live file")
        except Exception as exc:
            self._live_problem("kept the last good patterns; live file refused: " + _short(exc))
            return
        self.live = playlist
        self.live_error = None
        self._log("live file: %d patterns, current %d, rev %r" % (len(playlist["patterns"]), playlist["current"], playlist["rev"]))
        self.request(playlist["current"], defer, force=True, reflect=True)

    def _live_problem(self, message):
        if message != self.live_error:
            self.live_error = message
            self._log(message)

    # -- switching ----------------------------------------------------------------------------------------------

    def request(self, index, defer, force=False, reflect=False):
        """Ask for a pattern. defer (playing, or paused where Play continues) waits for a bar line; else it applies now."""
        plist = self.playlist()
        idx = max(0, min(int(index), len(plist) - 1))
        if not force and idx == self.current and plist[idx] is self.pattern:
            self.pending = None  # asked for what is already playing: cancel a pending switch
            return
        if reflect and idx != self.knob_seen:
            try:
                vfx.context.form.setNormalizedValue(C_PATTERN, pattern_knob_value(idx))
                self.knob_seen = idx
            except Exception:
                pass
        if defer:
            self.pending = idx
        else:
            self.apply(idx, None)

    def apply(self, index, t):
        """Make a pattern current. Playing or paused, this runs only on a bar line (t); stopped, t is None and Play
        starts fresh."""
        plist = self.playlist()
        index = max(0, min(int(index), len(plist) - 1))
        new = plist[index]
        old = self.pattern
        bar_before = self.compiled.bar if self.compiled is not None else None
        self.switches.append((t, index, self.anchor, bar_before))
        keep = (t is not None and old is not None and new["id"] == old["id"]
                and new["length_beats"] == old["length_beats"] and new["bar_beats"] == old["bar_beats"])
        self.release_all()
        self.pending = None
        self.fired = {}
        if t is None:
            self.restart = True
        else:
            self.switch_t = t  # a switch bar is never a dropout bar
            if not keep:
                self.anchor = t  # a different pattern starts from its top; an edit of the same one keeps its place
        self.current = index
        self.pattern = new
        self.compiled = None
        self._log("pattern %d: %s" % (index, _ascii(new["title"])))

    # -- voices -------------------------------------------------------------------------------------------------

    def listed_voice(self, e):
        """The entry's voice as FL lists it now in vfx.context.voices, or None once FL has let it go.

        FL may hand back wrapper objects rather than the voice the band triggered, so after identity the band's own
        bookkeeping decides: it keeps at most one sounding voice per note per output (a pitch ends before it sounds
        again), so the entry's voice is the most recently listed one with its note and output.
        """
        v = e.voice
        match = None
        for x in vfx.context.voices:
            if x is v:
                return x
            if x.note == e.note and x.output == e.output:
                match = x
        return match

    def release_entry(self, e, now=False):
        """Release one of the band's voices. One triggered in this very onTick waits for the next (a release in the
        same call would make a note of no length), unless now: the same pitch is about to sound again."""
        if not e.alive:  # released already, by the band or with everything
            return
        if e.call == self.calls and not now:
            if e not in self.deferred:
                self.deferred.append(e)
            return
        e.alive = False
        try:
            self.sounding.remove(e)
        except ValueError:
            pass
        x = self.listed_voice(e)
        if x is not None:
            x.release()

    def release_lane(self, lane_i):
        for e in list(self.sounding):
            if e.lane == lane_i:
                self.release_entry(e)

    def release_all(self):
        """Release every voice FL lists for this script, except those triggered in this very onTick: they are
        released on the next one (see release_entry)."""
        keep = [e for e in self.sounding if e.alive and e.call == self.calls]
        for e in self.sounding:
            if e.call != self.calls:
                e.alive = False
        self.sounding = keep
        self.deferred = list(keep)
        self.due = {}
        for v in list(vfx.context.voices):  # only voices this script triggered (manual; Random Notes preset)
            if keep and any(v is e.voice or (v.note == e.note and v.output == e.output) for e in keep):
                continue
            v.release()

    def cut(self):
        """FL's playhead jumped or its loop wrapped (Follow song position): everything ringing ends here."""
        self.release_all()
        self.fired = {}
        self.switch_t = None

    def pulse(self, value):
        if self.has_pulse:
            try:
                vfx.setOutputController(BAR_PULSE, value)
            except Exception:
                self.has_pulse = False

    # -- the clock ----------------------------------------------------------------------------------------------

    def poll(self, playing, defer):
        form = vfx.context.form
        if form is None:
            return
        get = form.getInputValue
        if get(C_PANIC):
            form.setNormalizedValue(C_PANIC, 0)
            self.release_all()
            self._log("panic: all notes released")
        if get(C_RELOAD):
            form.setNormalizedValue(C_RELOAD, 0)
            self.load_module()
            self.request(self.current, defer, force=True)
        lane = int(get(C_LANE))
        if lane != self.lane_sel:
            self.lane_sel = lane
            self.release_all()
        clock = int(get(C_CLOCK))
        if clock != self.clock:
            self.clock = clock
            self.release_all()
            self.restart = True
        swing = float(get(C_SWING))
        grid = int(get(C_GRID))
        if swing != self.swing or grid != self.grid:
            self.swing, self.grid = swing, grid
            self.compiled = None
        self.humanize = float(get(C_HUMANIZE))
        drum_map = min(int(get(C_DRUM_MAP)), len(self.drum_maps) - 1)
        if drum_map != self.drum_map:
            self.drum_map = drum_map
            self.release_lane(DRUM_LANE)
        # Dropout and its seed are decided once per bar line (bar_rests), so a change takes effect on the next bar.
        self.dropout = max(0, min(int(get(C_DROPOUT)), len(DROPOUT_CHANCE) - 1))
        self.dropout_seed = int(get(C_DROPOUT_SEED))
        for i, name in enumerate(C_MUTES):
            muted = bool(get(name))
            if muted and not self.mutes[i]:
                self.release_lane(i)
            self.mutes[i] = muted
        self.switch_at = int(get(C_SWITCH))
        live_on = bool(get(C_LIVE))
        if live_on != self.live_on:
            self.live_on = live_on
            if live_on:
                self.live_sig = None
                self.live_text = None
                if not playing:
                    self.read_live(defer)
            elif self.live is not None:
                self.request(self.current, defer, force=True)
        knob = int(get(C_PATTERN))
        if self.knob_seen is None or knob != self.knob_seen:
            self.knob_seen = knob
            self.request(knob, defer)

    def resume_gap(self, ticks):
        """The ticks between the last played onTick and FL's playhead now, if Play would continue from where the band
        paused: up to a beat on, or across a loop wrap FL made just before the pause (the loop span known from an
        earlier wrap, and no Stop seen since). None when Play starts fresh."""
        d = ticks - self.last_ticks
        if 0 <= d <= self.ppq:
            return d
        span = self.loop_span
        if d < 0 and span is not None and not self.parked_at_zero and 1 <= span + d <= self.ppq:
            return span + d
        return None

    def resumable(self, ticks):
        """True when FL's playhead is where the band paused (up to a beat on, across a loop wrap too), so Play
        continues the loop in step.

        A Stop sends ticks back to 0 (or before the pause point), a seek moves them further: both start fresh. Tick
        0 always starts fresh: a pause exactly on the loop top cannot be told from a Stop. FL may call onTick less
        often than every tick, so any gap up to a beat still counts as a continuation.
        """
        if self.restart or self.last_ticks is None or self.band_t < 0 or self.ppq is None or ticks <= 0:
            return False
        return self.resume_gap(ticks) is not None

    def on_tick(self):
        ctx = vfx.context
        playing = bool(ctx.isPlaying)
        ticks = int(ctx.ticks)
        ppq = int(ctx.PPQ)
        self.calls += 1
        if self.deferred:  # voices triggered in the last onTick whose release had to wait for this one
            held, self.deferred = self.deferred, []
            for e in held:
                self.release_entry(e)
        if not playing and ticks == 0:
            self.parked_at_zero = True
        if ppq != self.ppq:
            if self.ppq is not None:
                self.release_all()
                self.restart = True
            self.ppq = ppq
            self.compiled = None
            self.poll_every = max(1, ppq // 24)
        # Paused where Play will continue: a switch or Reload waits for the first bar line after resuming, so the
        # band never restarts off FL's bar grid. Stopped (or moved): it applies now and Play starts fresh.
        defer = playing or self.resumable(ticks)
        if self.calls >= self.next_poll:
            self.next_poll = self.calls + self.poll_every
            self.poll(playing, defer)
        if not playing:
            if self.was_playing:
                self.was_playing = False
                self.release_all()
                self.pulse(0)
                self.pulse_off = None
            if self.pending is not None and not self.resumable(ticks):
                self.apply(self.pending, None)
            if self.live_on and self.calls % (ppq * 4) == 0:
                self.read_live(self.resumable(ticks))
            return
        self.quiet = 0
        window = self.advance(ticks)
        self.was_playing = True
        self.parked_at_zero = False
        self.last_ticks = ticks
        quiet = self.quiet
        last = None
        for t in window:
            if t is WRAP:
                self.cut()
                continue
            self.step(t, quiet <= 0)
            quiet -= 1
            last = t
        if last is not None:
            self.band_t = last

    def gap_bounds(self):
        """(tight, loose): the largest gap FL has left between recent onTicks, and room for a one-off longer one.
        Once there are 8 gaps, tight is the second largest, so one forward seek of under a beat (which looks like a
        gap) cannot widen it. Both stay within a beat, the most the band ever treats as FL playing on."""
        g = self.gaps
        tight = (sorted(g)[-2] if len(g) >= 8 else max(g)) if g else 1
        return min(self.ppq, tight), min(self.ppq, 2 * tight + 1)

    def bar_ticks(self):
        return self.compiled.bar if self.compiled is not None else max(1, int(round(self.pattern["bar_beats"] * self.ppq)))

    def wrap_info(self, d):
        """(gap, exact) when FL's ticks fell by -d between two onTicks and the fall is a loop wrap; None for a seek.

        FL played on to its loop end and again from the loop start, so gap = span + d ticks passed, where span is the
        length of the loop (end - start). Only a span an exact wrap has shown counts, never a guess on a beat or 16th
        grid. The known span is a wrap when it gives a gap of at most a beat: exact when that gap is no longer than
        the largest FL has left lately (the tight bound); longer, it is either one late onTick across the wrap or a
        seek back to the loop top from inside the loop's last beat, which no tick count can tell apart, so the caller
        counts the loop's end without sounding it. A fall the known span does not fit (or any fall before a span is
        known) is an exact wrap only when a whole number of bars gives a gap within the tight bound; that span
        becomes the known one. Anything else is a seek.
        """
        tight = self.gap_bounds()[0]
        span = self.loop_span
        if span is not None and 1 <= span + d <= self.ppq:
            return span + d, span + d <= tight
        bar = self.bar_ticks()
        span = -(-(1 - d) // bar) * bar  # the fewest whole bars giving a gap of at least 1
        if 1 <= span + d <= tight:
            self.loop_span = span
            return span + d, True
        return None

    def realign(self, ticks):
        """Keep counting: how many band ticks to count, from 1 to a bar, so the band's place in its bar is FL's place in
        its own bar (ticks modulo the bar, as at Play). Across a whole-bar loop wrap that is exactly the ticks that
        passed; after a seek, a jump or a wrap of a loop that is not whole bars it re-anchors the band to FL's bars."""
        bar = self.bar_ticks()
        return (ticks % bar - (self.band_t - self.anchor) - 1) % bar + 1

    def song_wrap(self, ticks, gap, span):
        """Follow song position across a loop wrap that passed gap ticks: the end of the loop FL played after the last
        onTick, WRAP, then the loop top up to ticks. The loop start is the beat line jump_window finds; when it is
        not on a beat line the loop end cannot be placed, and only the loop top plays."""
        head = self.jump_window(ticks, gap)
        tail = []
        if span is not None and isinstance(head, range) and head.start % self.ppq == 0:
            end = head.start + span
            if 0 <= end - self.last_ticks - 1 < gap:
                tail = list(range(self.last_ticks + 1, end))
        return tail + [WRAP] + list(head)

    def jump_window(self, ticks, gap):
        """The ticks to play at once after FL moved the playhead to ticks, having passed at most gap ticks since it
        landed. A beat line (or failing that a 16th line) among those is where it landed: the loop top after a wrap,
        the downbeat after a seek just past one. Play from there, so the downbeat is not lost. Else the tick before
        is played too, as at Play."""
        lo = ticks - gap + 1
        for grid in (self.ppq, max(1, self.ppq // 4)):
            line = ticks - ticks % grid
            if line >= lo:
                return range(line, ticks + 1)
        return [ticks - 1, ticks] if ticks >= 1 else [0]

    def advance(self, ticks):
        """The band ticks to process for this onTick, in order; WRAP marks FL's loop wrap in Follow song position.
        Each tick is processed exactly once. self.quiet counts the leading ticks that are processed without sounding
        (FL did not play them: the playhead was nudged while paused)."""
        if self.was_playing and self.restart:  # the Clock mode changed mid-play
            self.was_playing = False
        if not self.was_playing:
            gap = self.resume_gap(ticks) if self.resumable(ticks) else None
            self.restart = False
            self.fired = {}
            if gap is not None:
                # Continue by exactly the ticks FL moved, so the band keeps its offset to FL's bars. FL played at most
                # a gap or so of them before the pause took hold; anything beyond the loose bound was a nudge of the
                # playhead while paused, counted but not sounded.
                if gap == 0:
                    return []
                loose = self.gap_bounds()[1]
                if gap <= loose:
                    self.gaps.append(gap)
                    del self.gaps[:-GAP_MEMORY]
                self.quiet = max(0, gap - loose)
                if self.clock == CLOCK_SONG:
                    if ticks >= self.last_ticks:
                        return range(self.last_ticks + 1, ticks + 1)
                    return self.song_wrap(ticks, gap, self.loop_span)
                return range(self.band_t + 1, self.band_t + gap + 1)
            if self.pending is not None:  # asked for while paused, then FL stopped or moved: start on it
                self.apply(self.pending, None)
                self.restart = False
            self.anchor = 0
            self.switch_t = None
            self.drop_t = None
            self.drop_now = False
            # FL's first played onTick may report the tick after the playhead, so the tick before is played too.
            if self.clock == CLOCK_SONG:
                return [ticks - 1, ticks] if ticks >= 1 else [0]
            # Keep counting starts at bar 1 in step with FL's bar grid: Play from mid-bar joins bar 1 at that beat.
            bar = max(1, int(round(self.pattern["bar_beats"] * self.ppq)))
            b0 = ticks % bar
            self.band_t = -1
            return [b0 - 1, b0] if b0 >= 1 else [0]
        d = ticks - self.last_ticks
        if d == 0:
            return []
        if 0 < d <= self.ppq:
            self.gaps.append(d)
            del self.gaps[:-GAP_MEMORY]
            if self.clock == CLOCK_SONG:
                return range(self.last_ticks + 1, ticks + 1)
            return range(self.band_t + 1, self.band_t + d + 1)
        # FL moved the playhead: a loop wrap (wrap_info), or a seek or jump.
        loose = self.gap_bounds()[1]
        wrap = self.wrap_info(d) if d < 0 else None
        if self.clock == CLOCK_SONG:
            # A wrap plays the end of the loop FL passed after the last onTick, releases everything, then plays from
            # the loop top; when the gap is longer than FL has been leaving (it may have been a seek back to the loop
            # top) the loop's end is counted, not sounded. A seek releases everything and plays from the beat line
            # (or 16th line) FL has just passed.
            if wrap is not None:
                window = self.song_wrap(ticks, wrap[0], self.loop_span)
                if not wrap[1]:
                    self.quiet = window.index(WRAP)
                return window
            self.cut()
            return self.jump_window(ticks, loose)
        # Keep counting counts on through FL's loop wraps and re-anchors to FL's bar lines on anything else (realign).
        # Only the ticks FL played since it landed sound: after an exact wrap the whole gap; after a longer one, from
        # the loop top; after a seek or jump, which also releases everything, from the line FL has just passed.
        step = self.realign(ticks)
        if wrap is not None and wrap[1]:
            heard = wrap[0]
        else:
            if wrap is None:
                self.cut()
            heard = len(self.jump_window(ticks, loose if wrap is None else wrap[0]))
        self.quiet = max(0, step - heard)
        return range(self.band_t + 1, self.band_t + step + 1)

    def step(self, t, sound=True):
        """Process band tick t: bar-line switches, the bar pulse, dropout, releases due, and (when sound) the events
        starting here."""
        c = self.compiled
        if c is None:
            c = self.compiled = Compiled(self.pattern, self.ppq, self.swing, GRID_BEATS[self.grid])
        if self.pulse_off is not None and t >= self.pulse_off:
            self.pulse(0)
            self.pulse_off = None
        rel = t - self.anchor
        phase = rel % c.bar
        if self.live_on and phase == c.read_at:
            self.read_live(True)
        if phase == 0:
            if self.pending is not None and (self.switch_at != SWITCH_NEXT_LOOP or rel % c.loop == 0):
                self.apply(self.pending, t)
                c = self.compiled = Compiled(self.pattern, self.ppq, self.swing, GRID_BEATS[self.grid])
                rel = t - self.anchor
            rested = self.drop_now and self.drop_t == t - c.bar and self.switch_t != t
            self.pulse(1)
            self.pulse_off = t + max(1, self.ppq // 8)
            if self.bar_rests(t, c):  # a dropout bar: whatever still rings outside the bass ends on its bar line
                for e in list(self.sounding):
                    if e.lane != BASS_LANE:
                        self.release_entry(e)
            elif rested and sound:
                self.restrike(t, rel, c)
        due = self.due.pop(t, None)
        if due:
            for e in due:
                if e.alive:
                    self.release_entry(e)
        events = c.at.get(rel % c.loop)
        if events and sound:
            self.start(events, t, rel // c.loop, t - rel % c.bar, c)

    # -- dropout ------------------------------------------------------------------------------------------------

    def dropout_due(self, bar_t, c, switching):
        if switching or not self.dropout:
            return False
        return dropout_bar(self.dropout_seed, (bar_t - self.anchor) // c.bar, DROPOUT_CHANCE[self.dropout])

    def bar_rests(self, bar_t, c):
        """True when the bar starting at band tick bar_t is a dropout bar. Decided once, at the bar's first tick, and
        kept for the bar: never right after a bar that rested, never on a pattern switch bar."""
        if bar_t != self.drop_t:
            rest = not self.drop_now and self.dropout_due(bar_t, c, bar_t == self.switch_t)
            self.drop_t, self.drop_now = bar_t, rest
        return self.drop_now

    def next_bar_rests(self, bar_t, c):
        """Whether the bar after the one at bar_t will rest, as far as can be told now (a switch waiting for that
        bar line means it will not)."""
        nxt = bar_t + c.bar
        return not self.bar_rests(bar_t, c) and self.dropout_due(nxt, c, self.switch_waits(nxt, c))

    def switch_waits(self, line, c):
        """True when a pattern switch (or Reload) is waiting for the bar line at band tick line."""
        return self.pending is not None and (self.switch_at != SWITCH_NEXT_LOOP or (line - self.anchor) % c.loop == 0)

    def restrike(self, t, rel, c):
        """The bar line after a dropout bar: comp and pad notes that would still be ringing here (cut on the rest bar's
        line, or started inside it) are struck again for what is left of them, so a held chord comes back with the
        band. A push over this bar line belongs to this bar and has already played."""
        p = rel % c.loop
        half = self.ppq // 2
        for s, eid, lane_i, note, vel, length in c.held:
            ago = (p - s) % c.loop  # ticks since the note's latest start at or before this bar line
            if ago == 0 or ago >= length or ago <= half:
                continue
            self.sound(eid, lane_i, note, vel, length - ago, t, (rel - ago) // c.loop)

    def route(self, lane_i):
        """The voice output a lane plays on, or None when it is muted or another lane is selected."""
        if self.mutes[lane_i]:
            return None
        if self.lane_sel == 0:
            return lane_i
        return 0 if self.lane_sel - 1 == lane_i else None

    def start(self, events, t, loop_n, bar_t, c):
        for eid, lane_i, note, vel, length in events:
            if self.route(lane_i) is None:
                continue
            if lane_i != BASS_LANE:
                ahead = bar_t + c.bar - t
                if ahead <= self.ppq // 2 and length > ahead:  # a push over the bar line belongs to the next bar
                    if self.switch_waits(bar_t + c.bar, c) or self.next_bar_rests(bar_t, c):
                        continue  # a switch on that bar line would cut it at once; a rest bar silences it
                elif self.bar_rests(bar_t, c):
                    continue
            if self.fired.get(eid) == loop_n:
                continue
            self.fired[eid] = loop_n
            self.sound(eid, lane_i, note, vel, length, t, loop_n)

    def sound(self, eid, lane_i, note, vel, length, t, loop_n):
        """Trigger one note of the pattern on its lane's output, drum-mapped and humanized."""
        out = self.route(lane_i)
        if out is None:
            return
        if lane_i == DRUM_LANE:
            _name, table, passthrough = self.drum_maps[self.drum_map]
            mapped = table.get(note)
            if mapped is None:
                if not passthrough:
                    return
                mapped = note
            note = mapped
        if self.humanize > 0.0:
            vel = humanize_velocity(vel, eid, loop_n, self.humanize)
        for e in list(self.sounding):  # a pitch still sounding on this output ends before it sounds again
            if e.note == note and e.output == out:
                if e.alive and e.call == self.calls and vel <= e.vel:
                    # Triggered in this very onTick, so both would start at the same moment: that voice, at least as
                    # loud, carries on as this note rather than being released at once (a note of no length) and
                    # triggered again. A louder one (a backbeat after its ghost) replaces it below.
                    old = self.due.get(e.end)
                    if old is not None and e in old:
                        old.remove(e)
                    if e in self.deferred:
                        self.deferred.remove(e)
                    e.end = max(e.end, t + length)
                    self.due.setdefault(e.end, []).append(e)
                    return
                self.release_entry(e, now=True)
        v = vfx.Voice()
        v.note = note
        v.velocity = vel / 127.0
        v.length = length
        v.output = out
        v.trigger()
        e = _Entry(v, lane_i, out, note, t, t + length, self.calls, vel)
        self.sounding.append(e)
        self.due.setdefault(t + length, []).append(e)


BAND = Band()
if vfx is not None:
    BAND.load_module()
    BAND.pattern = BAND.baked[0]


def onTick():
    BAND.on_tick()


def createDialog():
    form = vfx.ScriptDialog("", BAND.describe())
    form.addGroup("Band")
    form.addInputKnobInt("Pattern", 0, 0, MAX_PATTERNS - 1, hint="Pattern to play; the switch lands on the next bar line")
    form.addInputCombo("Switch at", SWITCH_CHOICES, 0, hint="Switch on the next bar line, or on the top of the loop")
    form.addInputCombo("Lane", LANE_CHOICES, 0, hint="All lanes on voice outputs 1-4, or one lane on output 1")
    form.addInputCombo("Clock", CLOCK_CHOICES, 0, hint="Keep counting through FL loops, or follow FL's song position")
    form.endGroup()
    form.addGroup("Feel")
    form.addInputKnob("Swing", 0, 0, 1, hint="0 straight, 1 full triplet swing on the grid below")
    form.addInputCombo("Swing grid", GRID_CHOICES, 0, hint="Which off-beats swing")
    form.addInputKnob("Humanize", 0, 0, 1, hint="Velocity variation, up to 20 steps either way")
    form.addInputCombo("Drum map", BAND.drum_map_names(), 0, hint="GM notes as they are, or mapped for FPC or Addictive Drums 2")
    form.addInputCombo("Dropout", DROPOUT_CHOICES, 0, hint="Now and then a bar where every lane but bass rests")
    form.addInputKnobInt("Dropout seed", 0, 0, DROPOUT_SEEDS - 1, hint="Which bars drop out; the same seed drops the same bars")
    form.endGroup()
    form.addGroup("Mute")
    for name in ("Bass", "Drums", "Comp", "Pad"):
        form.addInputCheckbox(name, 0, hint="Silence this lane now")
    form.endGroup()
    form.addGroup("Patterns")
    form.addInputCheckbox("Live file", 0, hint="Follow the JSON playlist named by LIVE_PATH in arsenal_patterns")
    form.addInputCheckbox("Reload", 0, hint="Re-import arsenal_patterns; lands on the next bar line")
    form.addInputCheckbox("Panic", 0, hint="Release every note this band is playing")
    form.endGroup()
    vfx.addOutputController(BAR_PULSE, 0)
    BAND.has_pulse = True
    return form
