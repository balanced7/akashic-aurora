"""A stand-in for FL Studio's flvfx module (VFX Script), so the arsenal band runs, and is tested, without FL.

Only names that FL's own factory presets or Image-Line's manual use are here, with the value types those
presets rely on. A census of all 89 factory presets (read-only, 2026-09-14, under
C:/Program Files/Image-Line/FL Studio 2026/Data/Patches/Plugin presets/Effects/VFX Script/) found:
  vfx.context.{form, PPQ, isPlaying, voices, ticks, tempo}; vfx.{ScriptDialog, Voice, addOutputController,
  setOutputController}; form.{addGroup, endGroup, addInputKnob, addInputKnobInt, addInputCheckbox,
  addInputCombo, addInputText, addInputSurface, getInputValue, setNormalizedValue} plus capitalised aliases;
  voice.{note, velocity, length, pan, finePitch, output, fcut, fres, color, releaseVelocity, trigger, release, copyFrom}.
Manual: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/VFX%20Script.htm

What neither source pins down is a switch the tests flip, never a guess baked in:
  auto_release  whether FL's own length countdown frees a voice before or after onTick on its last tick;
  first_tick    whether the first onTick after Play sees ticks 0 or 1 (Tutorial 3 and Sequencer POV step on
                ticks % n == 1, Arpeggiator on == 0);
  loop_ticks    FL's pattern-mode loop, which sends ticks back to 0 (Timer (BPM) resets when ticks fall);
  tick_step     how many ticks pass between onTick calls (the manual says "called every tick"; 1 by default);
  gaps          irregular onTick gaps instead: a list of tick counts played in turn, or a function of the call
                number; buffer_samples does the same from an audio buffer size at the current tempo, so the
                gaps change with BPM (at PPQ 96 a 512-sample buffer is 1 or 2 ticks at 72 BPM, 2 or 3 at 120);
                a gap can skip the tick where FL's loop wraps;
  voice_views   whether vfx.context.voices hands back the voices the script triggered, or fresh wrapper
                objects around them on every read (so `is` never matches);
  knob_store, knob_read   how an int knob keeps a setNormalizedValue (a float, a float32 or a 16-bit step)
                and turns it back into an int (round or floor).
Triggering a sounding voice, releasing a silent one, or a value outside the manual's ranges is recorded as an
anomaly: FL's behaviour there is unknown, so the band must never do it.

Also a small CLI for offline rehearsal:
  py arsenal/fl/vfx/flvfx_mock.py check PATH       validate a patterns module (.py) or live playlist (.json)
  py arsenal/fl/vfx/flvfx_mock.py simulate PATH    play it through the band and print the notes
      [--gaps 1,4,2 | --gaps buffer:512] [--dropout Rare|Often --dropout-seed N] [--clock "Follow song position"]
      [--loop-ticks N]
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import struct
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAND_SCRIPT = HERE / "arsenal_band.py"
PATTERN_MODULE = "arsenal_patterns"

VOICE_DEFAULTS = {"note": 60.0, "finePitch": 0.0, "velocity": 100 / 127, "pan": 0.0, "length": 0, "output": 0,
                  "fcut": 0.0, "fres": 0.0, "color": 0, "releaseVelocity": 0.5}
FLVFX_NAMES = ("context", "Voice", "ScriptDialog", "addOutputController", "setOutputController")
CONTEXT_NAMES = ("ticks", "PPQ", "isPlaying", "tempo", "voices", "form")
FORM_NAMES = ("addGroup", "endGroup", "addInputKnob", "addInputKnobInt", "addInputCheckbox", "addInputCombo",
              "addInputText", "addInputSurface", "getInputValue", "setNormalizedValue")

_ids = itertools.count(1)
_ABSENT = object()


class _Input:
    __slots__ = ("kind", "lo", "hi", "options", "value")

    def __init__(self, kind, lo, hi, options, value):
        self.kind, self.lo, self.hi, self.options, self.value = kind, lo, hi, options, value


KNOB_STORES = ("float", "float32", "16bit")
KNOB_READS = ("round", "floor")


def stored_normalized(n, store):
    """A normalized value as FL might keep it: exactly, as a float32, or on a 16-bit step (rounded down)."""
    if store == "float32":
        return struct.unpack("f", struct.pack("f", n))[0]
    if store == "16bit":
        return math.floor(n * 65535) / 65535.0
    return n


class ScriptDialog:
    """vfx.ScriptDialog(title, description). Inputs inside a group are addressed as 'Group: Name'."""

    knob_store = "float"
    knob_read = "round"

    def __init__(self, title, description):
        self.title = title
        self.description = description
        self._inputs = {}
        self._group = None
        self.reads = 0
        self.normalized_writes = []

    def addGroup(self, name):
        self._group = name

    def endGroup(self):
        self._group = None

    def _add(self, name, inp):
        full = "%s: %s" % (self._group, name) if self._group else name
        if full in self._inputs:
            raise ValueError("duplicate input %r" % full)
        self._inputs[full] = inp

    def addInputKnob(self, name, default, lo, hi, hint=""):
        self._add(name, _Input("knob", float(lo), float(hi), None, min(max(float(default), lo), hi)))

    def addInputKnobInt(self, name, default, lo, hi, hint=""):
        self._add(name, _Input("knob_int", int(lo), int(hi), None, int(min(max(default, lo), hi))))

    def addInputCheckbox(self, name, default, hint=""):
        self._add(name, _Input("checkbox", 0, 1, None, 1 if default else 0))

    def addInputCombo(self, name, options, default, hint=""):
        opts = options.split(",") if isinstance(options, str) else list(options)
        if not opts:
            raise ValueError("combo %r has no options" % name)
        self._add(name, _Input("combo", 0, len(opts) - 1, opts, int(min(max(default, 0), len(opts) - 1))))

    def addInputText(self, name, default="", hint=""):
        self._add(name, _Input("text", None, None, None, str(default)))

    def addInputSurface(self, name=""):
        pass

    def getInputValue(self, name):
        self.reads += 1
        try:
            return self._inputs[name].value
        except KeyError:
            raise KeyError("no input named %r (inputs: %s)" % (name, ", ".join(self._inputs))) from None

    def setNormalizedValue(self, name, value):
        inp = self._inputs[name]
        n = min(max(float(value), 0.0), 1.0)
        self.normalized_writes.append((name, n))
        if inp.kind == "knob":
            inp.value = inp.lo + n * (inp.hi - inp.lo)
        elif inp.kind in ("knob_int", "combo"):
            x = inp.lo + stored_normalized(n, self.knob_store) * (inp.hi - inp.lo)
            inp.value = int(math.floor(x)) if self.knob_read == "floor" else int(round(x))
        elif inp.kind == "checkbox":
            inp.value = 1 if n >= 0.5 else 0

    # capitalised spellings the factory presets also use
    AddInputKnob = addInputKnob
    AddInputKnobInt = addInputKnobInt
    AddInputCheckbox = addInputCheckbox
    AddInputCombo = addInputCombo
    AddInputText = addInputText
    AddInputSurface = addInputSurface
    GetInputValue = getInputValue

    # host side (not FL API): a person or FL automation moves a control
    def set(self, name, value):
        inp = self._inputs[name]
        if inp.kind == "knob":
            inp.value = min(max(float(value), inp.lo), inp.hi)
        elif inp.kind in ("knob_int", "combo"):
            if inp.kind == "combo" and isinstance(value, str):
                value = inp.options.index(value)
            inp.value = int(min(max(int(value), inp.lo), inp.hi))
        elif inp.kind == "checkbox":
            inp.value = 1 if value else 0
        else:
            inp.value = str(value)

    def names(self):
        return list(self._inputs)

    def options(self, name):
        return list(self._inputs[name].options or [])


class Context:
    def __init__(self, host):
        self._host = host
        self.ticks = 0
        self.PPQ = 96
        self.isPlaying = False
        self.tempo = 120.0
        self.form = None

    @property
    def voices(self):
        """Active voices triggered by this script (a fresh list each read; fresh wrappers too with voice_views)."""
        if self._host.voice_views:
            return [VoiceView(self._host, v) for v in self._host.active]
        return list(self._host.active)


class VoiceView:
    """A wrapper FL might hand back from vfx.context.voices: the same voice underneath, a new object on every read."""
    __slots__ = ("_host", "_voice")

    def __init__(self, host, voice):
        object.__setattr__(self, "_host", host)
        object.__setattr__(self, "_voice", voice)

    def __getattr__(self, name):
        value = getattr(self._voice, name)
        return float(value) if name == "note" else value  # FL may report the pitch as a float

    def __setattr__(self, name, value):
        setattr(self._voice, name, value)

    def release(self):
        self._host.release(self._voice)

    def trigger(self):
        self._host.trigger(self._voice)


def make_flvfx(host):
    """A fresh flvfx module bound to one Host."""
    mod = types.ModuleType("flvfx")
    mod.__doc__ = "Mock of FL Studio's VFX Script API (arsenal/fl/vfx/flvfx_mock.py)"

    class Voice:
        def __init__(self, other=None):
            for k, v in VOICE_DEFAULTS.items():
                object.__setattr__(self, k, v)
            if other is not None:
                self.copyFrom(other)

        def __setattr__(self, name, value):
            if type(self) is Voice and name not in VOICE_DEFAULTS:
                raise AttributeError("vfx.Voice has no attribute %r (subclass it to add fields)" % name)
            object.__setattr__(self, name, value)

        def copyFrom(self, other):
            for k in VOICE_DEFAULTS:
                object.__setattr__(self, k, getattr(other, k))

        def trigger(self):
            host.trigger(self)

        def release(self):
            host.release(self)

    def addOutputController(name, default):
        host.controllers[name] = [default]

    def setOutputController(name, value):
        if name not in host.controllers:
            raise KeyError("no output controller named %r" % name)
        host.controllers[name].append(value)

    class Dialog(ScriptDialog):
        knob_store = host.knob_store
        knob_read = host.knob_read

    mod.context = Context(host)
    mod.Voice = Voice
    mod.ScriptDialog = Dialog
    mod.addOutputController = addOutputController
    mod.setOutputController = setOutputController
    return mod


class Host:
    """FL's side of a VFX Script: the transport, the tick loop and the voices, recorded as note events."""

    def __init__(self, script=BAND_SCRIPT, *, ppq=96, bpm=120.0, first_tick=0, auto_release="after",
                 patterns=_ABSENT, patterns_dir=None, loop_ticks=None, tick_step=1, gaps=None,
                 buffer_samples=None, sample_rate=44100, voice_views=False, knob_store="float", knob_read="round"):
        if auto_release not in ("before", "after"):
            raise ValueError("auto_release is 'before' or 'after'")
        if not isinstance(tick_step, int) or tick_step < 1:
            raise ValueError("tick_step is a whole number of ticks, at least 1")
        if gaps is not None and buffer_samples is not None:
            raise ValueError("gaps or buffer_samples, not both")
        if gaps is not None and not callable(gaps):
            gaps = list(gaps)
            if not gaps or any(not isinstance(g, int) or g < 0 for g in gaps) or not any(gaps):
                raise ValueError("gaps are whole tick counts, not all 0")
        if knob_store not in KNOB_STORES or knob_read not in KNOB_READS:
            raise ValueError("knob_store is one of %s, knob_read one of %s" % (KNOB_STORES, KNOB_READS))
        self.tick_step = tick_step
        self.gaps = gaps
        self.buffer_samples = buffer_samples
        self.sample_rate = sample_rate
        self.voice_views = voice_views
        self.knob_store = knob_store
        self.knob_read = knob_read
        self.call_log = []        # (host_tick, ticks FL reported, playing) for every onTick
        self.play_host_tick = None
        self._carry = 0.0
        self.script = Path(script)
        self.ppq = ppq
        self.bpm = float(bpm)
        self.first_tick = first_tick
        self.auto_release = auto_release
        self.patterns = patterns
        self.patterns_dir = patterns_dir
        self.loop_ticks = loop_ticks
        self.events = []
        self.anomalies = []
        self.controllers = {}
        self.active = []
        self.triggered = []
        self.position = 0
        self.playing = False
        self.host_tick = 0
        self.seconds = 0.0
        self._auto = {}
        self._saved = {}
        self._path_added = False
        self.vfx = None
        self.module = None
        self.form = None

    # -- lifecycle --------------------------------------------------------------------------------------------

    def __enter__(self):
        return self.load()

    def __exit__(self, *exc):
        self.close()

    def _swap(self, name, value):
        if name not in self._saved:
            self._saved[name] = sys.modules.get(name, _ABSENT)
        if value is _ABSENT:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = value

    def load(self):
        self.vfx = make_flvfx(self)
        self._swap("flvfx", self.vfx)
        self._swap(PATTERN_MODULE, self.patterns)  # _ABSENT: the script must find it on sys.path, or fall back
        if self.patterns_dir is not None:
            sys.path.insert(0, str(self.patterns_dir))
            self._path_added = True
        try:
            spec = importlib.util.spec_from_file_location("arsenal_band_sim_%d" % next(_ids), self.script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.module = module
            self.form = module.createDialog()
            self.vfx.context.form = self.form
        except BaseException:
            self.close()
            raise
        return self

    def close(self):
        for name, value in self._saved.items():
            if value is _ABSENT:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
        self._saved = {}
        if self._path_added:
            try:
                sys.path.remove(str(self.patterns_dir))
            except ValueError:
                pass
            self._path_added = False

    @property
    def band(self):
        return self.module.BAND

    # -- voices -----------------------------------------------------------------------------------------------

    def _is_active(self, v):
        return any(x is v for x in self.active)

    @property
    def regular(self):
        return self.gaps is None and self.buffer_samples is None

    def trigger(self, v):
        if self._is_active(v):
            self.anomalies.append(("trigger of a sounding voice", self.host_tick, v.note))
            return
        if not isinstance(v.note, (int, float)) or not 0 <= v.note <= 131:
            self.anomalies.append(("note out of range", self.host_tick, v.note))
        if not isinstance(v.velocity, (int, float)) or not 0.0 <= v.velocity <= 1.0:
            self.anomalies.append(("velocity outside 0..1", self.host_tick, v.velocity))
        if not isinstance(v.length, int) or v.length < 0:
            self.anomalies.append(("length is not a tick count", self.host_tick, v.length))
        if not isinstance(v.output, int) or not 0 <= v.output <= 15:
            self.anomalies.append(("output outside 0..15", self.host_tick, v.output))
        self.active.append(v)
        self.triggered.append(v)  # held so id(v) stays unique for the whole take
        self.events.append({"kind": "on", "host_tick": self.host_tick, "tick": self.position, "seconds": self.seconds,
                            "note": v.note, "velocity": v.velocity, "output": v.output, "length": v.length,
                            "voice": id(v), "auto": False})
        if isinstance(v.length, int) and v.length > 0:
            self._auto.setdefault(self.host_tick + v.length, []).append(v)

    def release(self, v, auto=False):
        if isinstance(v, VoiceView):
            v = v._voice
        if not self._is_active(v):
            if not auto:
                self.anomalies.append(("release of a silent voice", self.host_tick, v.note))
            return
        self.active = [x for x in self.active if x is not v]
        self.events.append({"kind": "off", "host_tick": self.host_tick, "tick": self.position, "seconds": self.seconds,
                            "note": v.note, "velocity": v.velocity, "output": v.output, "length": v.length,
                            "voice": id(v), "auto": auto})

    def _auto_release(self):
        if self.tick_step == 1 and self.regular:
            due = self._auto.pop(self.host_tick, ())
        else:  # a countdown can end between two onTick calls
            due = [v for k in sorted(k for k in self._auto if k <= self.host_tick) for v in self._auto.pop(k)]
        for v in due:
            self.release(v, auto=True)

    # -- transport ----------------------------------------------------------------------------------------------

    def _next_gap(self):
        """Ticks until the next onTick call."""
        n = len(self.call_log) - 1
        if self.buffer_samples is not None:
            self._carry += self.buffer_samples / float(self.sample_rate) * self.bpm / 60.0 * self.ppq
            step = int(self._carry)
            self._carry -= step
            return step
        if self.gaps is None:
            return self.tick_step
        if callable(self.gaps):
            return int(self.gaps(n))
        return self.gaps[n % len(self.gaps)]

    def tick(self):
        ctx = self.vfx.context
        ctx.ticks = self.position
        ctx.isPlaying = self.playing
        ctx.PPQ = self.ppq
        ctx.tempo = self.bpm
        self.call_log.append((self.host_tick, self.position, self.playing))
        if self.auto_release == "before":
            self._auto_release()
        self.module.onTick()
        if self.auto_release == "after":
            self._auto_release()
        step = self._next_gap()
        self.host_tick += step
        self.seconds += step * 60.0 / (self.bpm * self.ppq)
        if self.playing:
            self.position += step
            if self.loop_ticks:
                while self.position >= self.loop_ticks:
                    self.position -= self.loop_ticks

    def run(self, calls):
        """Run this many onTick calls (each tick_step ticks apart)."""
        for _ in range(int(calls)):
            self.tick()

    def run_to(self, tick):
        """Run onTick calls until the playhead reaches tick (playing, no loop wrap)."""
        while self.position < tick:
            self.tick()

    def run_ticks(self, ticks):
        """Run onTick calls until at least this many ticks of host time have passed (loop wraps and gaps allowed)."""
        end = self.host_tick + int(ticks)
        while self.host_tick < end:
            self.tick()

    def run_beats(self, beats):
        self.run(round(beats * self.ppq / self.tick_step))

    def play(self):
        if not self.playing:
            if self.position == 0:
                self.position = self.first_tick
            self.playing = True
            self.play_host_tick = self.host_tick

    def played_calls(self):
        """(host_tick, ticks) for every onTick FL made while playing, in order."""
        return [(h, t) for h, t, playing in self.call_log if playing]

    def pause(self):
        self.playing = False

    def stop(self):
        """FL's Stop: the transport halts and the playhead returns to the start."""
        self.playing = False
        self.position = 0

    def seek(self, tick):
        self.position = int(tick)

    def set(self, name, value):
        self.form.set(name, value)

    def get(self, name):
        return self.form.getInputValue(name)

    # -- reading the take ---------------------------------------------------------------------------------------

    def ons(self):
        return [e for e in self.events if e["kind"] == "on"]

    def pairs(self):
        """(on, off) per voice in trigger order; off is None for a voice still sounding."""
        offs = {}
        for e in self.events:
            if e["kind"] == "off":
                offs.setdefault(e["voice"], []).append(e)
        out = []
        for on in self.ons():
            lst = offs.get(on["voice"]) or [None]
            out.append((on, lst.pop(0) if lst[0] is not None else None))
        return out


# -- CLI --------------------------------------------------------------------------------------------------------

def load_band_parsers():
    """arsenal_band.py loaded outside FL (no flvfx): its parse functions only."""
    saved = sys.modules.pop("flvfx", _ABSENT)
    try:
        spec = importlib.util.spec_from_file_location("arsenal_band_parsers_%d" % next(_ids), BAND_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if saved is not _ABSENT:
            sys.modules["flvfx"] = saved


def load_patterns_module(path):
    spec = importlib.util.spec_from_file_location("%s_checked_%d" % (PATTERN_MODULE, next(_ids)), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(path, out=print):
    band = load_band_parsers()
    path = Path(path)
    problems = []
    titles = []
    if path.suffix.lower() == ".json":
        try:
            playlist = band.parse_playlist(json.loads(path.read_text(encoding="utf-8")), path.name)
            titles = [p["title"] for p in playlist["patterns"]]
        except Exception as exc:
            problems.append(str(exc))
    else:
        module = load_patterns_module(path)
        if getattr(module, "VERSION", 1) != 1:
            problems.append("VERSION must be 1")
        patterns = getattr(module, "PATTERNS", None)
        if not isinstance(patterns, (list, tuple)) or not patterns:
            problems.append("PATTERNS must be a non-empty list")
            patterns = []
        if len(patterns) > band.MAX_PATTERNS:
            problems.append("at most %d PATTERNS" % band.MAX_PATTERNS)
        for i, p in enumerate(patterns):
            try:
                titles.append(band.parse_pattern_set(p, "PATTERNS[%d]" % i)["title"])
            except band.PatternError as exc:
                problems.append(str(exc))
        if getattr(module, "DRUM_MAPS", None):
            try:
                band.parse_drum_maps(module.DRUM_MAPS)
            except band.PatternError as exc:
                problems.append(str(exc))
        if path.read_bytes().decode("ascii", "replace") != path.read_bytes().decode("utf-8", "replace"):
            problems.append("the module is not ASCII")
    for p in problems:
        out("refused: " + p)
    if not problems:
        out("ok: %d pattern sets" % len(titles))
        for i, t in enumerate(titles):
            out("  %d  %s" % (i, t))
    return 1 if problems else 0


def parse_gaps(text):
    """--gaps: None (onTick every tick), "buffer:SAMPLES" (one onTick per audio buffer), or "1,4,2" (played in turn)."""
    if text is None or text == "":
        return {}
    if text.startswith("buffer:"):
        return {"buffer_samples": int(text.split(":", 1)[1])}
    return {"gaps": [int(g) for g in text.split(",")]}


def simulate(path, *, bars=4, bpm=120.0, ppq=96, pattern=0, lane="All lanes on outputs 1-4", drum_map="GM",
             swing=0.0, humanize=0.0, gaps=None, dropout="Off", dropout_seed=0, clock="Keep counting", loop_ticks=None,
             out=print):
    module = load_patterns_module(path)
    with Host(ppq=ppq, bpm=bpm, patterns=module, loop_ticks=loop_ticks, **parse_gaps(gaps)) as host:
        host.set("Band: Pattern", pattern)
        host.set("Band: Lane", lane)
        host.set("Band: Clock", clock)
        host.set("Feel: Drum map", drum_map)
        host.set("Feel: Swing", swing)
        host.set("Feel: Humanize", humanize)
        host.set("Feel: Dropout", dropout)
        host.set("Feel: Dropout seed", dropout_seed)
        host.run(1)
        host.play()
        host.run_ticks(int(bars * host.band.pattern["bar_beats"] * ppq))
        host.stop()
        host.run(1)
        bar_ticks = int(round(host.band.pattern["bar_beats"] * ppq))
        for e in host.events:
            bar, rest = divmod(e["tick"], bar_ticks)
            beat, tick = divmod(rest, ppq)
            out("%3d.%d.%03d  %-3s  out %d  note %3d  vel %3d%s" % (bar + 1, beat + 1, tick, e["kind"], e["output"], e["note"],
                                                                     round(e["velocity"] * 127), "  (FL length)" if e["auto"] else ""))
        for a in host.anomalies:
            out("ANOMALY: %r" % (a,))
        return 1 if host.anomalies else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flvfx_mock", description="Rehearse the arsenal band VFX Script without FL Studio.")
    sub = ap.add_subparsers(dest="verb", required=True)
    c = sub.add_parser("check", help="validate a patterns module (.py) or a live playlist (.json)")
    c.add_argument("path")
    s = sub.add_parser("simulate", help="play a patterns module through the band and print the note events")
    s.add_argument("path")
    s.add_argument("--bars", type=int, default=4)
    s.add_argument("--bpm", type=float, default=120.0)
    s.add_argument("--ppq", type=int, default=96)
    s.add_argument("--pattern", type=int, default=0)
    s.add_argument("--drum-map", default="GM")
    s.add_argument("--swing", type=float, default=0.0)
    s.add_argument("--humanize", type=float, default=0.0)
    s.add_argument("--gaps", help='onTick gaps: "1,4,2" played in turn, or "buffer:512" (one call per audio buffer)')
    s.add_argument("--dropout", default="Off", choices=["Off", "Rare", "Often"])
    s.add_argument("--dropout-seed", type=int, default=0)
    s.add_argument("--clock", default="Keep counting", choices=["Keep counting", "Follow song position"])
    s.add_argument("--loop-ticks", type=int, help="FL's pattern loop in ticks (the playhead wraps to 0)")
    args = ap.parse_args(argv)
    if args.verb == "check":
        return check(args.path)
    try:
        parse_gaps(args.gaps)
    except ValueError:
        ap.error('--gaps reads like "1,4,2" or "buffer:512"')
    return simulate(args.path, bars=args.bars, bpm=args.bpm, ppq=args.ppq, pattern=args.pattern,
                    drum_map=args.drum_map, swing=args.swing, humanize=args.humanize, gaps=args.gaps,
                    dropout=args.dropout, dropout_seed=args.dropout_seed, clock=args.clock, loop_ticks=args.loop_ticks)


if __name__ == "__main__":
    sys.exit(main())
