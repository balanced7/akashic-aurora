"""py -m arsenal.keylab <verb> ... -- drive the Arturia KeyLab 88 mk3: pads, colours, notes, screen.

Verbs:
  ports                list MIDI ports Windows sees (+ the Windows MIDI service state); marks the KeyLab
  selftest             prove the SysEx wire format offline (no keyboard needed)
  connect | disconnect arm / drop DAW-integration mode (the gate that makes LED/screen commands land)
  led <target> <col>   light one LED/pad   (target: A1..D12 | a button like 'play' | an id 0..93)
  pad <n> <col>        light bank-A pad n (1..12)
  all <col> | off      light every bank-A pad / turn them all off
  rainbow              sweep a hue across the 12 pads (eye candy + a visual rate check)
  chord <spec>         light the pads of a chord ('Cmaj7', 'F#m', 'C E G', '60 64 67'); --play also triggers it
  note <n>             send a Note On/Off (trigger a sampler voice); --pad n uses that pad's default note
  bench                latency / rate-limit harness for colour updates (host throughput + a visual ceiling ramp)
  display <text>       EXPERIMENTAL: push text to the onboard screen (grammar unconfirmed -- for bench probing)
  screen <text>        write the screen in GUEST mode (never connects; FL keeps the KeyLab), the encoder byte-identical
                       to Arturia's FL script; --live keeps chord, BPM and the VJ scene on it (screen.py)
  monitor              print incoming MIDI (tap a pad to see its note) -- needs the keyboard attached
  vj                   the VJ engine: keys, pads, controls, the beat, energy, hits and chords as live events
                       (SSE on 127.0.0.1:8794) for a visual page; the page can light the pads back
  fl-install | fl-uninstall | fl-status
                       our own FL Studio script for the DAW port (FL keeps the transport, everything else is ours):
                       copy it into FL's Hardware/Aurora KeyLab folder, remove it, or check it (flscript.py)

Global: --port SUBSTR picks the output by name (default: first containing 'keylab'); --dry-run prints bytes, sends nothing.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

from . import protocol as P
from . import winmidi as W

# Spacing between LED packets. The device hard-freezes on ~36 packets in one tight burst (needs a power cycle);
# 12 is the safe ceiling, so pace every multi-pad send and you can never cross it. Confirmed 2026-10-22.
PAD_GAP = 0.008


def _hex(b) -> str:
    return bytes(b).hex(" ").upper()


class _DryOut:
    """Stand-in for MidiOut under --dry-run: prints what would go on the wire."""
    name = "(dry-run)"

    def send_sysex(self, data):
        print(f"  SysEx  {_hex(data)}")

    def send_short(self, s, d1, d2):
        print(f"  Short  {s:02X} {d1:02X} {d2:02X}")

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _open(args, prefer="daw"):
    if getattr(args, "dry_run", False):
        return _DryOut()
    return W.MidiOut(getattr(args, "port", None), prefer=prefer)


def _arm(out, args):
    """Arm DAW mode before LED work unless --no-connect. Cheap and idempotent."""
    if not getattr(args, "no_connect", False):
        out.send_sysex(P.daw_connect(True))


# --- verbs ---------------------------------------------------------------------------------------
def cmd_ports(args) -> int:
    try:
        from arsenal import midiports
        snap = midiports.snapshot()
    except Exception as exc:
        snap = {"ok": False, "reason": str(exc)}
    outs, ins = W.outputs(), W.inputs()

    def show(title, names):
        print(title)
        if not names:
            print("  (none)")
        for i, n in enumerate(names):
            tag = "  <- KeyLab" if "keylab" in n.lower() else ""
            print(f"  [{i}] {n}{tag}")

    show("MIDI OUT (openable for notes/colour/screen):", outs)
    show("MIDI IN (for monitor):", ins)
    if snap.get("ok"):
        print(f"Windows MIDI service (midisrv): {snap['service']['state']}")
    if not any("keylab" in n.lower() for n in outs):
        print("\nNo KeyLab output found. Plug the mk3 in over USB; if it still doesn't show, a browser or DAW may "
              "hold a stale MIDI list -- close MIDI apps and re-run.")
    return 0


def cmd_selftest(args) -> int:
    fails = P.selftest()
    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest OK -- wire format matches the bytes read from Arturia's own FL script.")
    print(f"  example  pad A1 green = {_hex(P.set_led('A1', 'green'))}")
    print(f"  example  DAW connect  = {_hex(P.daw_connect(True))}")
    return 0


def cmd_connect(args) -> int:
    with _open(args) as out:
        out.send_sysex(P.daw_connect(True))
    print("DAW-integration mode armed." if not args.dry_run else "")
    return 0


def cmd_disconnect(args) -> int:
    with _open(args) as out:
        out.send_sysex(P.daw_connect(False))
    print("DAW-integration mode dropped." if not args.dry_run else "")
    return 0


def cmd_led(args) -> int:
    with _open(args) as out:
        _arm(out, args)
        out.send_sysex(P.set_led(args.target, args.color, req=args.req))
    return 0


def cmd_pad(args) -> int:
    with _open(args) as out:
        _arm(out, args)
        out.send_sysex(P.set_led(P.pad_led(args.n, args.bank), args.color, req=args.req))
    return 0


def cmd_all(args) -> int:
    with _open(args) as out:
        _arm(out, args)
        for n in range(1, 13):
            out.send_sysex(P.set_led(P.pad_led(n, args.bank), args.color, req=args.req))
            time.sleep(PAD_GAP)
    return 0


def cmd_off(args) -> int:
    with _open(args) as out:
        _arm(out, args)
        for n in range(1, 13):
            out.send_sysex(P.set_led(P.pad_led(n, args.bank), "off", req=args.req))
            time.sleep(PAD_GAP)
    return 0


def cmd_rainbow(args) -> int:
    frames = max(1, int(args.secs * args.hz))
    with _open(args) as out:
        _arm(out, args)
        if args.dry_run:
            print(f"  (dry-run: 1 of {frames} frames)")
            for n in range(1, 13):
                out.send_sysex(P.set_led(P.pad_led(n, args.bank), P.hue(n, 12), req=args.req))
            return 0
        period = 1.0 / args.hz
        for f in range(frames):
            t0 = time.perf_counter()
            for n in range(1, 13):
                out.send_sysex(P.set_led(P.pad_led(n, args.bank), P.hue(n + f, 12), req=args.req))
                time.sleep(PAD_GAP)
            dt = time.perf_counter() - t0
            if period > dt:
                time.sleep(period - dt)
        for n in range(1, 13):
            out.send_sysex(P.set_led(P.pad_led(n, args.bank), "off", req=args.req))
            time.sleep(PAD_GAP)
    print(f"rainbow: {frames} frames x 12 pads")
    return 0


def cmd_chord(args) -> int:
    pcs, root = P.chord_pitchclasses(args.spec)
    pads = {P.pad_for_pitchclass(pc): pc for pc in pcs}
    with _open(args) as out:
        _arm(out, args)
        for n in range(1, 13):
            if n in pads:
                col = args.root_color if pads[n] == root else args.color
                out.send_sysex(P.set_led(P.pad_led(n, args.bank), col, req=args.req))
            else:
                out.send_sysex(P.set_led(P.pad_led(n, args.bank), "off", req=args.req))
            time.sleep(PAD_GAP)
        if args.play:
            for pc in pcs:
                n = P.pad_for_pitchclass(pc)
                out.send_short(*P.note(P.PAD_NOTE[n], 100, on=True))
    print(f"chord {args.spec}: pitch-classes {pcs}, root {root}, pads {sorted(pads)}")
    return 0


def cmd_note(args) -> int:
    n = P.PAD_NOTE[args.pad] if args.pad else args.n
    if n is None:
        print("note: give a MIDI number (e.g. 'note 60') or --pad N", file=sys.stderr)
        return 2
    with _open(args, prefer="midi") as out:
        out.send_short(*P.note(n, args.vel, channel=args.ch, on=True))
        if not args.dry_run:
            time.sleep(args.secs)
        out.send_short(*P.note(n, 0, channel=args.ch, on=False))
    print(f"note {n} ch{args.ch} vel{args.vel} for {args.secs}s")
    return 0


def cmd_bench(args) -> int:
    targets = [P.pad_led(n, "A") for n in range(1, 13)]
    palette = [P.hue(i, 12) for i in range(12)]
    if args.dry_run:
        print(f"  (dry-run) would send {args.count} eSetLed msgs cycling 12 pads; sample:")
        print(f"  {_hex(P.set_led(targets[0], palette[0], req=args.req))}")
        return 0
    print("  (limit probe: the burst governor is OFF for this run)")
    with W.MidiOut(args.port, governor=False) as out:
        _arm(out, args)
        durs = []
        if args.hz:  # paced -- watch for visible stall (the device's render ceiling)
            period = 1.0 / args.hz
            end = time.perf_counter() + args.secs
            i = 0
            while time.perf_counter() < end:
                t0 = time.perf_counter()
                out.send_sysex(P.set_led(targets[i % 12], palette[i % 12], req=args.req))
                durs.append(time.perf_counter() - t0)
                i += 1
                rest = period - (time.perf_counter() - t0)
                if rest > 0:
                    time.sleep(rest)
            mode = f"paced {args.hz} Hz for {args.secs}s"
        else:        # flood -- max host throughput
            t_start = time.perf_counter()
            for i in range(args.count):
                t0 = time.perf_counter()
                out.send_sysex(P.set_led(targets[i % 12], palette[i % 12], req=args.req))
                durs.append(time.perf_counter() - t0)
            mode = f"flood {args.count} msgs"
            total = time.perf_counter() - t_start
        for n in range(1, 13):
            out.send_sysex(P.set_led(P.pad_led(n, "A"), "off", req=args.req))
    durs_ms = sorted(d * 1000 for d in durs)
    n = len(durs_ms)
    mean = sum(durs_ms) / n if n else 0
    p50 = durs_ms[n // 2] if n else 0
    p99 = durs_ms[min(n - 1, int(n * 0.99))] if n else 0
    rate = (n / sum(d / 1000 for d in durs_ms)) if sum(durs_ms) else 0
    print(f"bench ({mode}) -- {n} colour updates")
    print(f"  per-msg host->driver: mean {mean:.3f} ms | p50 {p50:.3f} | p99 {p99:.3f} | max {durs_ms[-1]:.3f}")
    print(f"  sustained send rate:  {rate:,.0f} msgs/s")
    print("  NOTE: this is HOST->driver accept time. The device's own LED render ceiling (firmware has a bounded")
    print("        'LedStrip' queue) shows as visible lag/stall -- watch the pads during a --hz ramp to find it.")
    return 0


def cmd_display(args) -> int:
    if args.line2 is not None:
        data = P.screen_full2(args.text, args.line2) if args.full else P.screen_popup2(args.text, args.line2)
    else:
        data = P.screen_popup1(args.text)
    with _open(args) as out:
        _arm(out, args)
        out.send_sysex(data)
    print(f"display: {_hex(data)}")
    return 0


def cmd_monitor(args) -> int:
    if args.dry_run:
        print("monitor needs the keyboard attached (nothing to dry-run).")
        return 0
    print(f"listening on input ~{args.port or 'keylab'} for {args.secs}s -- tap pads/keys...")

    def on_msg(s, d1, d2):
        kind = {0x90: "NoteOn", 0x80: "NoteOff", 0xB0: "CC", 0xA0: "PolyAT", 0xD0: "ChanAT", 0xE0: "Pitch"}.get(
            s & 0xF0, f"0x{s & 0xF0:02X}")
        pad = P._NOTE_PAD.get(d1)
        tag = f"  (pad {pad})" if pad and (s & 0xF0) in (0x90, 0x80) else ""
        print(f"  ch{(s & 0x0F) + 1:<2} {kind:<7} d1={d1:<3} d2={d2:<3}{tag}")

    count = W.monitor(args.port, args.secs, on_msg, prefer="midi")
    print(f"{count} messages.")
    return 0


def cmd_show(args) -> int:
    """A burst-safe light show on the DAW-bank pads: proof-of-life flashes, a rainbow wave, a chord bloom."""
    with _open(args, "daw") as out:
        _arm(out, args)
        bank = args.bank
        off = ["off"] * 12
        from .ledframe import PadRenderer
        render = PadRenderer(out, bank=bank, gap=PAD_GAP)

        def paint(colors):
            render.set_frame(colors)

        if args.dry_run:
            paint([P.hue(i, 12) for i in range(12)])
            return 0
        for _ in range(2):  # proof-of-life flashes
            paint(["white"] * 12); time.sleep(0.22)
            paint(off); time.sleep(0.16)
        for f in range(40):  # rainbow wave
            paint([P.hue(i + f, 12) for i in range(12)]); time.sleep(0.025)
        paint(off); time.sleep(0.15)
        pcs, root = P.chord_pitchclasses(args.chord)  # chord bloom finale
        bloom = {P.pad_for_pitchclass(pc): (pc == root) for pc in pcs}
        paint(["white" if bloom.get(p) else ("amber" if p in bloom else "off") for p in range(1, 13)])
        time.sleep(2.0)
        paint(off)
    print(f"show done ({args.chord})")
    return 0


def cmd_beat(args) -> int:
    from . import beatsync
    extra = {} if args.engine == "aubio" else {"lead_ms": args.lead_ms, "seed_bpm": args.seed_bpm, "offline": args.offline,
                                               "connect": not args.no_connect, "referee": args.referee,
                                               "hand": args.hand, "save": args.save}
    return beatsync.run(port=args.port, secs=args.secs, mode=args.mode, bank=args.bank, engine=args.engine,
                        verbose=not args.quiet, **extra)


def cmd_ledbench(args) -> int:
    """Characterize the LED send limits -- run ONE test, watch the pads, report, then we bump the knob.
    rate: one pad toggles fast (watch for lag). spacing: 12 pads at a tight gap (watch for dropped pads).
    burst: N packets with NO spacing -- approaches the ~36 freeze wall, so start small; a power cycle recovers."""
    print("ledbench is a limit probe: the burst governor is OFF for this run")
    with W.MidiOut(args.port, prefer="daw", governor=False) as out:
        out.send_sysex(P.daw_connect(True)); time.sleep(0.2)
        if args.test == "rate":
            def _pad(n, c):
                out.send_sysex(P.set_led(P.pad_led(n, "DAW"), c, req=P.REQ_CTRL)); time.sleep(0.008)
            for n in range(1, 13):  # clear the field so markers + pad-1 flicker are unambiguous
                _pad(n, "off")
            rates = [float(x) for x in args.sweep.split(",")] if args.sweep else [args.hz]

            def flicker(hz):
                period = 1.0 / hz
                t0 = time.perf_counter(); end = t0 + args.secs; k = 0
                while time.perf_counter() < end:
                    out.send_sysex(P.set_led(P.pad_led(1, "DAW"), "red" if k % 2 else "off", req=P.REQ_CTRL))
                    k += 1
                    slp = (t0 + k * period) - time.perf_counter()
                    if slp > 0:
                        time.sleep(slp)
                out.send_sysex(P.set_led(P.pad_led(1, "DAW"), "off", req=P.REQ_CTRL))
                return k

            if len(rates) > 1:
                print("rate sweep -- before each level, that many pads flash white = the level number; then watch pad 1")
            for ri, hz in enumerate(rates):
                if len(rates) > 1:  # level counter
                    for j in range(ri + 1):
                        _pad(j + 1, "white")
                    time.sleep(0.6)
                    for j in range(ri + 1):
                        _pad(j + 1, "off")
                    time.sleep(0.3)
                k = flicker(hz)
                print(f"  L{ri+1}: {hz:.0f}Hz target -> {k} toggles, ~{k/args.secs:.0f}Hz on the wire")
                if ri < len(rates) - 1:
                    time.sleep(0.5)
            print("  -> which level number is the LAST one where pad 1 still looks clean/even?")
        elif args.test == "spacing":
            for i in range(12):
                out.send_sysex(P.set_led(P.pad_led(i + 1, "DAW"), P.hue(i, 12), req=P.REQ_CTRL))
                time.sleep(args.gap)
            print(f"spacing: painted 12 pads at {args.gap*1000:.1f}ms gap.")
            print("  -> all 12 lit, each a different colour? any dark/wrong pad = a DROPPED packet at this spacing.")
        elif args.test == "burst":
            for k in range(args.n):
                out.send_sysex(P.set_led(P.pad_led((k % 12) + 1, "DAW"), P.hue(k, 12), req=P.REQ_CTRL))
            print(f"burst: sent {args.n} packets back-to-back, NO spacing.")
            print(f"  -> responsive + all pads updated = safe at N={args.n}. Frozen (needs power cycle) = the wall.")
    return 0


def cmd_chordview(args) -> int:
    from . import chordview
    return chordview.run(secs=args.secs, keys_port=args.port, scheme=args.scheme, sound=args.sound)


def _screen_frames(args, S) -> list:
    """The one-shot frames for `screen TEXT` / `screen --labels`, built by the script-identical encoder."""
    if args.labels is not None:
        names = [s.strip() for s in args.labels.split(",")]
        if len(names) > 8:
            raise ValueError("at most 8 labels (screen buttons 1-8)")
        frames = []
        for button in range(1, 9):
            name = S.ascii_clean(names[button - 1]) if button <= len(names) else ""
            kind = S.LABEL_TEXT_ACTIVE if button == args.active else (S.LABEL_TEXT if name else S.LABEL_EMPTY)
            frames.append(S.button_label(S.SLOT_FOR_BUTTON[button], kind, 1, 1, None, S.WHITE7, name, ""))
        return frames
    if args.text is None:
        raise ValueError("give the TEXT to show, or --live, or --labels")
    line1 = S.ascii_clean(args.text)
    line2 = S.ascii_clean(args.line2) if args.line2 is not None else ""
    c1, c2 = S.rgb7(args.color), S.rgb7(args.color2)
    layout = args.layout
    if layout in S.LAYOUTS:
        return [S._TWO_LINE[S.LAYOUTS[layout]](line1, 1, c1, line2, 1, c2)]
    if layout == "line":
        return [S.f1l(line1, 1, c1)]
    if layout == "popup":
        return [S.p2l(line1, 1, c1, line2, 1, c2) if args.line2 is not None else S.p1l(line1)]
    if layout == "title":
        return [S.ti2lfix(line1, 1, c1, line2, 1, c2, args.icon)]
    if layout == "icon":
        return [S.li2l(line1, line2, args.icon)]
    raise ValueError(f"unknown layout {layout!r}")


def cmd_screen(args) -> int:
    """Guest-mode screen writes: never the DAW connect unless --connect, and --connect refuses while FL runs."""
    from . import screen as S
    if args.connect and not args.dry_run and S.fl_running():
        print("screen: --connect refused: FL Studio is running and owns the KeyLab connection. Close FL first, "
              "or drop --connect (guest mode).", file=sys.stderr)
        return 2
    if args.live:
        out = _open(args)
        try:
            if args.connect:
                out.send_sysex(P.daw_connect(True))
                time.sleep(0.2)
            src = "the keys" if args.source == "keys" else args.engine
            print(f"screen --live on {out.name}: chord, BPM, scene from {src} (Ctrl-C to stop)")
            stats = S.run_live(out, source=args.source, url=args.engine, scene=args.scene,
                               layout=S.LAYOUTS[args.layout if args.layout in S.LAYOUTS else "full"],
                               secs=args.secs, min_interval=args.min_interval, reassert_s=args.reassert,
                               pulse=args.pulse, keys_port=args.keys_port, bpm=args.bpm)
            print(f"screen --live done: {stats}")
        finally:
            if args.connect:
                try:
                    out.send_sysex(P.daw_connect(False))
                except Exception:
                    pass
            out.close()
        return 0
    frames = _screen_frames(args, S)
    for data in frames:
        S.check(data)                       # refuse before anything opens the port
    record = {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "verb": "screen", "guest": not args.connect,
              "layout": "labels" if args.labels is not None else args.layout,
              "text": args.text, "line2": args.line2, "labels": args.labels,
              "frames_hex": [_hex(d) for d in frames], "sent": False, "error": None,
              "fl_running": None if args.dry_run else S.fl_running(),
              "check": "Daniel's eyes: did the screen show it? (we cannot see the screen)"}
    try:
        with _open(args) as out:
            record["port"] = out.name
            if args.connect:
                out.send_sysex(P.daw_connect(True))
                time.sleep(0.2)
            writer = S.write_frames(out, frames)
            record["sent"] = not args.dry_run
            record["writer"] = writer.stats()
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if not args.dry_run:
            print(f"receipt: {S.write_receipt(args.receipt or S.default_receipt_path(), record)}")
    if not args.dry_run:
        for d in frames:
            print(f"  sent  {_hex(d)}")
    return 0


def cmd_vj(args) -> int:
    from . import vj
    return vj.run(port=args.port, engine=args.engine, leds=not args.no_leds, connect=args.connect,
                  replay_midi=args.replay_midi, replay_bpm=args.replay_bpm, replay_stretch=args.replay_stretch,
                  replay_pattern=args.replay_pattern, replay_audio=args.replay_audio, loop=args.loop,
                  audio=not args.no_audio,
                  midi=not args.no_midi, rate_limit=args.rate_limit, pads=args.pads, ahead_ms=args.ahead_ms,
                  offset_ms=args.offset_ms, seed_bpm=args.seed_bpm, secs=args.secs, quiet=args.quiet,
                  chords=args.chords)


def chord_line(e: dict) -> str:
    """One chordsense event as a readable line."""
    t = f"{e['t']:8.2f}s"
    kind = e["type"]
    if kind == "chord":
        num = e.get("roman") or ""
        return (f"{t}  {e['name']:<10} {num:<10} {e.get('function') or '':<18} tension {e['tension']:.2f}"
                f"   (began {e['t_change']:.2f}s, confidence {e['confidence']:.2f})")
    if kind == "key":
        return f"{t}  KEY {e['key']}  (confidence {e['confidence']:.2f})"
    if kind == "pedal":
        if e["on"]:
            return (f"{t}  PEDAL {e['note']} since {e['since']:.2f}s, over {e['chords']} chord roots, "
                    f"clashing {e.get('clash', 0.0):.0%} of the time")
        return f"{t}  pedal {e['note']} released (strength reached {e['strength']:.2f})"
    if kind == "resolution":
        return f"{t}  RESOLUTION {e['from']:.2f} -> {e['to']:.2f} on {e['chord']} ({e['numeral']})"
    return f"{t}  {e}"


def cmd_chords(args) -> int:
    import json
    from . import chordsense as CS

    def show(events):
        for e in events:
            try:
                if args.vj:                 # the VJ engine's SSE events (chord, key, tension), one per line
                    for v in CS.to_vj_events(e):
                        print(json.dumps(v), flush=True)
                else:
                    print(json.dumps(e) if args.json else chord_line(e), flush=True)
            except OSError:                 # the reader went away (| head): stop quietly
                raise BrokenPipeError

    try:
        return _chords(args, show)
    except BrokenPipeError:
        try:
            sys.stdout = open(os.devnull, "w")       # nothing left to flush into a closed pipe at exit
        except OSError:
            pass
        return 0


def _chords(args, show) -> int:
    import json
    from . import chordsense as CS
    if args.notes:
        doc = json.loads(pathlib.Path(args.notes).read_text(encoding="utf-8"))
        notes, ppq = (doc["notes"], int(doc.get("ppq", 96))) if isinstance(doc, dict) else (doc, 96)
        evs = CS.score_to_events(notes, ppq, args.bpm)
        show(CS.ChordSense().feed_notes(evs, now=(evs[-1]["t"] + 1.0) if evs else 0.0))
        return 0
    if args.live:
        return _chords_live(args, show)
    if not args.path:
        print("chords: give an audio file, --live, or --notes FILE", file=sys.stderr)
        return 2
    import soundfile as sf
    audio, rate = sf.read(args.path, dtype="float32", always_2d=True)
    cs = CS.ChordSense(rate, 512)
    for i in range(0, len(audio), 512):
        show(cs.feed(audio[i:i + 512]))
    return 0


def _chords_live(args, show) -> int:
    """Read the loopback in 512-frame blocks and print every chordsense event as it is decided (read-only)."""
    import numpy as np
    import pyaudiowpatch as pa
    from . import beatsync
    from . import chordsense as CS
    inst, dev = beatsync._open_loopback(pa)
    rate = int(dev["defaultSampleRate"])
    ch = int(dev["maxInputChannels"]) or 2
    stream = inst.open(format=pa.paFloat32, channels=ch, rate=rate, input=True,
                       input_device_index=dev["index"], frames_per_buffer=512)
    print(f"listening: {dev['name']} @ {rate} Hz x{ch} (Ctrl-C to stop; silence reads nothing)", flush=True)
    cs = CS.ChordSense(rate, 512)
    t_end = (time.perf_counter() + args.secs) if args.secs else None
    try:
        while t_end is None or time.perf_counter() < t_end:
            # the loopback hands over nothing while nothing plays: poll, so --secs and Ctrl-C still work
            if stream.get_read_available() < 512:
                time.sleep(0.005)
                continue
            raw = stream.read(512, exception_on_overflow=False)
            show(cs.feed(np.frombuffer(raw, dtype=np.float32).reshape(-1, ch)))
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        try:
            stream.stop_stream()
            stream.close()
            inst.terminate()
        except Exception:
            pass
    return 0


# --- dispatch ------------------------------------------------------------------------------------
def _add_send_flags(p, color_default=None):
    p.add_argument("--port", help="output port name substring (default: first containing 'keylab')")
    p.add_argument("--dry-run", action="store_true", help="print bytes, send nothing")
    p.add_argument("--no-connect", action="store_true", help="do not auto-arm DAW mode first")
    p.add_argument("--req", type=lambda x: int(x, 0), default=P.REQ_CTRL,
                   help="first payload byte (0x00 = live colour, confirmed; 0x02 = white, probe-only)")
    p.add_argument("--bank", default="DAW",
                   help="pad bank (default DAW -- the only bank with live host colour; keyboard must be in DAW mode)")


def _positive_float(x: str) -> float:
    v = float(x)
    if not v > 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return v


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="arsenal.keylab", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    sub.add_parser("ports", help="list MIDI ports").set_defaults(func=cmd_ports, dry_run=False)
    sub.add_parser("selftest", help="prove the wire format offline").set_defaults(func=cmd_selftest, dry_run=False)

    for name, fn in (("connect", cmd_connect), ("disconnect", cmd_disconnect)):
        p = sub.add_parser(name, help="arm/drop DAW mode")
        p.add_argument("--port")
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(func=fn)

    p = sub.add_parser("led", help="light one LED/pad")
    p.add_argument("target", help="A1..D12 | button name | id 0..93")
    p.add_argument("color", help="name | #rrggbb | 'r,g,b'")
    _add_send_flags(p)
    p.set_defaults(func=cmd_led)

    p = sub.add_parser("pad", help="light bank-A pad n")
    p.add_argument("n", type=int)
    p.add_argument("color")
    _add_send_flags(p)
    p.set_defaults(func=cmd_pad)

    p = sub.add_parser("all", help="light all bank-A pads")
    p.add_argument("color")
    _add_send_flags(p)
    p.set_defaults(func=cmd_all)

    p = sub.add_parser("off", help="turn all bank-A pads off")
    _add_send_flags(p)
    p.set_defaults(func=cmd_off)

    p = sub.add_parser("rainbow", help="hue sweep across the 12 pads")
    p.add_argument("--secs", type=float, default=5.0)
    p.add_argument("--hz", type=float, default=20.0, help="frames per second")
    _add_send_flags(p)
    p.set_defaults(func=cmd_rainbow)

    p = sub.add_parser("chord", help="light the pads of a chord")
    p.add_argument("spec", help="'Cmaj7' | 'F#m' | 'C E G' | '60 64 67'")
    p.add_argument("--color", default="teal", help="chord-tone colour")
    p.add_argument("--root-color", default="white", help="root-note colour")
    p.add_argument("--play", action="store_true", help="also send the notes (trigger a sampler)")
    _add_send_flags(p)
    p.set_defaults(func=cmd_chord)

    p = sub.add_parser("note", help="send a Note On/Off")
    p.add_argument("n", type=int, nargs="?", help="MIDI note number")
    p.add_argument("--pad", type=int, help="use pad N's default note instead")
    p.add_argument("--vel", type=int, default=100)
    p.add_argument("--ch", type=int, default=P.PAD_CHANNEL)
    p.add_argument("--secs", type=float, default=0.4, help="hold time before Note Off")
    p.add_argument("--port")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_note)

    p = sub.add_parser("bench", help="latency / rate-limit harness for colour updates")
    p.add_argument("--count", type=int, default=400, help="messages to flood (ignored if --hz)")
    p.add_argument("--hz", type=float, help="paced rate to watch for the device's visual ceiling")
    p.add_argument("--secs", type=float, default=5.0, help="duration for --hz mode")
    _add_send_flags(p)
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("display", help="print text to the LCD (1 line, or --line2 for two)")
    p.add_argument("text")
    p.add_argument("--line2", help="second line of text")
    p.add_argument("--full", action="store_true", help="full-screen 2-line view instead of a popup")
    _add_send_flags(p)
    p.set_defaults(func=cmd_display)

    p = sub.add_parser("screen", help="write the KeyLab screen in guest mode; --live: chord, BPM and VJ scene",
                       description="Guest mode: never sends the DAW connect (FL Studio keeps the KeyLab). Every frame "
                                   "is built byte-for-byte like Arturia's FL script, passes the burst governor, and "
                                   "screens 38 / 43 / 44 are refused. Line 2 shows upper-case (the script's rule).")
    p.add_argument("text", nargs="?", help="line 1 (ASCII; over 32 characters becomes 28 + '...')")
    p.add_argument("--line2", help="line 2 (shown upper-case)")
    p.add_argument("--layout", default="full",
                   choices=["full", "inverted", "big", "line", "popup", "title", "icon"],
                   help="full = two lines that stay up (screen 12, confirmed); inverted 13; big 14; line 10; "
                        "popup 23/24 (gone after ~1 s); title 31 (icon card); icon 16. --live uses full, inverted "
                        "or big (anything else falls back to full)")
    p.add_argument("--color", default="teal", help="line 1 colour (name | #rrggbb | r,g,b), halved to 7-bit")
    p.add_argument("--color2", default="white", help="line 2 colour")
    p.add_argument("--icon", type=int, default=None, help="icon number for --layout title / icon (e.g. 65 chord)")
    p.add_argument("--labels", help="comma list of up to 8 names for screen buttons 1-8 (labels; FL repaints them)")
    p.add_argument("--active", type=int, default=0, help="with --labels: which button (1-8) is drawn as active")
    p.add_argument("--live", action="store_true", help="keep chord, BPM and scene on the screen until Ctrl-C")
    p.add_argument("--source", choices=["vj", "keys"], default="vj",
                   help="vj = the VJ engine's SSE feed (chord + BPM); keys = name chords from the MIDI port directly")
    p.add_argument("--engine", default="http://127.0.0.1:8794/api/events", help="VJ engine SSE URL")
    p.add_argument("--scene", help="scene name for line 2 (a {'t':'scene'} event on the feed replaces it)")
    p.add_argument("--bpm", type=float, help="a BPM to show until the feed says otherwise")
    p.add_argument("--secs", type=float, default=None, help="--live: stop after N seconds")
    p.add_argument("--min-interval", type=float, default=0.1, help="--live: at most one frame per this many seconds")
    p.add_argument("--reassert", type=float, default=0.0,
                   help="--live: re-send the current frame every N s (wins the screen back after FL repaints it)")
    p.add_argument("--pulse", action="store_true", help="--live: a 4-step beat marker on line 2, drawn on the beat")
    p.add_argument("--keys-port", help="--source keys: MIDI input port substring (default: the KeyLab MIDI port)")
    p.add_argument("--connect", action="store_true",
                   help="send the DAW connect first and disconnect after -- ONLY with FL Studio closed (refused while "
                        "FL runs)")
    p.add_argument("--receipt", help="receipt JSON path (default state/arsenal/keylab/receipts/screen-<stamp>.json)")
    p.add_argument("--port", help="output port name substring (default: the KeyLab DAW port)")
    p.add_argument("--dry-run", action="store_true", help="print bytes, send nothing")
    p.set_defaults(func=cmd_screen)

    p = sub.add_parser("monitor", help="print incoming MIDI (tap a pad)")
    p.add_argument("--secs", type=float, default=8.0)
    p.add_argument("--port")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_monitor)

    p = sub.add_parser("show", help="a burst-safe light show (flashes, rainbow wave, chord bloom)")
    p.add_argument("--chord", default="Cmaj7", help="chord for the finale bloom")
    _add_send_flags(p)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("beat", help="march the pads to whatever is playing (system-audio beat detection)")
    p.add_argument("--mode", choices=["cycle", "rainbow", "march"], default="cycle", help="how the pads react each beat")
    p.add_argument("--secs", type=float, default=None, help="auto-stop after N seconds (default: until Ctrl-C)")
    p.add_argument("--port")
    p.add_argument("--bank", default="DAW")
    engines = ["a", "aubio"] + sorted(
        x.stem[len("beat_"):] for x in pathlib.Path(__file__).parent.glob("beat_*.py") if x.stem != "beat_a")
    p.add_argument("--engine", choices=engines, default="a",
                   help="a = the house tracker (shipped); any other beat_<name>.py contestant can be tried live "
                        "(opt-in, e.g. g = the grid tracker); aubio = the old reactive path")
    p.add_argument("--lead-ms", type=float, default=15.0, help="paint this many ms before the predicted beat")
    p.add_argument("--seed-bpm", type=float, default=None, help="skip the database lookup and use this BPM as the seed")
    p.add_argument("--offline", action="store_true", help="no database lookup")
    p.add_argument("--no-connect", action="store_true",
                   help="guest mode: FL Studio keeps the KeyLab connection and screen; we only paint the pads")
    p.add_argument("--referee", action="store_true",
                   help="print every 2 s how ON BEAT the lights are, judged against the kicks (beatref.py)")
    p.add_argument("--quiet", action="store_true", help="do not print every beat (useful with --referee)")
    p.add_argument("--save", action="store_true",
                   help="save the audio the tracker heard, with your taps on the same clock (state/, never committed)")
    p.add_argument("--hand", action="store_true",
                   help="tap any pad on the beat (tempo + phase by ear, re-seeds a tracker at the wrong tempo); "
                        "the first fader you move nudges the lights (centre = none, up = later)")
    p.set_defaults(func=cmd_beat, dry_run=False)

    p = sub.add_parser("ledbench", help="characterize the LED send limits (rate / spacing / burst)")
    p.add_argument("test", choices=["rate", "spacing", "burst"])
    p.add_argument("--hz", type=float, default=30.0, help="rate test: pad-1 toggles per second")
    p.add_argument("--sweep", help="rate test: comma list of Hz to ladder through (e.g. 5,10,20,40,80,120)")
    p.add_argument("--secs", type=float, default=4.0, help="rate test: duration per level")
    p.add_argument("--gap", type=float, default=0.004, help="spacing test: seconds between the 12 packets")
    p.add_argument("--n", type=int, default=14, help="burst test: packets sent back-to-back with no spacing")
    p.add_argument("--port")
    p.set_defaults(func=cmd_ledbench, dry_run=False)

    p = sub.add_parser("chordview", help="live chord viewer: play keys -> chord name on the LCD + lit on the pads")
    p.add_argument("--secs", type=float, default=None, help="auto-stop after N seconds (default: until Ctrl-C)")
    p.add_argument("--scheme", choices=["notes", "roles", "quality", "split", "frame"], default="roles",
                   help="how the chord paints the pads")
    p.add_argument("--sound", action="store_true", help="forward your notes to the Windows synth so you hear them")
    p.add_argument("--port", help="MIDI input port for the keys (default: the KeyLab MIDI port)")
    p.set_defaults(func=cmd_chordview, dry_run=False)

    p = sub.add_parser("chords", help="hear the harmony: chord, key, roman numeral, tension, pedal (chordsense)")
    p.add_argument("path", nargs="?", help="an audio file (wav/flac/ogg/mp3) to stream through, as if live")
    p.add_argument("--live", action="store_true", help="listen to whatever is playing (WASAPI loopback)")
    p.add_argument("--secs", type=float, default=None, help="--live: stop after N seconds (default: Ctrl-C)")
    p.add_argument("--notes", help="a score JSON ({notes: [{pos, len, key, vel}], ppq}) through the keys path")
    p.add_argument("--bpm", type=float, default=100.0, help="--notes: the tempo the score's ticks play at")
    p.add_argument("--json", action="store_true", help="one JSON event per line (for a renderer), not text")
    p.add_argument("--vj", action="store_true",
                   help="one JSON event per line in the VJ engine's SSE contract (chord, key, tension)")
    p.set_defaults(func=cmd_chords, dry_run=False)

    p = sub.add_parser("beatbench", help="score beat trackers on the same ground truth (synthetic + your BPM loops)")
    p.add_argument("--suite", choices=["synthetic", "loops", "all", "drift", "shift", "bright", "bright_variants",
                                       "real"],
                   default="synthetic",
                   help="all = synthetic + loops (the reconciliation set); drift = constant-tempo syncopation traps; "
                        "bright = drift with a sawtooth bass; bright_variants = held-out bright basses drawn from "
                        "--variant-seed; real = your recordings with confirmed ground truth")
    p.add_argument("--trackers", default="aubio,librosa",
                   help="comma list: aubio, librosa, and every arsenal/keylab/beat_<name>.py by its <name> (a, b, ...)")
    p.add_argument("--n", type=int, default=40, help="loops to sample for the loops suite")
    p.add_argument("--per-cat", type=int, default=0, help="stratified loops: this many per category (kick/tops/melodic)")
    p.add_argument("--seeded", action="store_true", help="also run every loop with its true BPM as the seed")
    p.add_argument("--seed", type=int, default=7, help="sampling seed, so a run can be repeated exactly")
    p.add_argument("--hop", type=int, default=512)
    p.add_argument("--exclude-seeds", default="",
                   help="held-out draw (needs --per-cat): leave out every loop, by CONTENT, that the stratified draws "
                        "at these seeds used (e.g. 7,11)")
    p.add_argument("--exclude-receipts", default="",
                   help="comma list of bench receipts whose scored loops (by file name) never enter this draw")
    p.add_argument("--exclude-per-cat", type=int, default=30,
                   help="the --per-cat of the excluded draws (round 1 drew 30 per category)")
    p.add_argument("--vs", default="", help="print each tracker's per-class PAIRED difference against this one "
                                            "(it must be one of --trackers)")
    p.add_argument("--variant-seed", type=int, default=None,
                   help="bright_variants: the seed the held-out cases are drawn from (the gating one stays secret)")
    p.add_argument("--write-manifest", metavar="PATH", help="write the drawn loops / recordings (path, size, sha1, "
                                                            "category) and the draw's parameters to PATH")
    p.add_argument("--manifest", metavar="PATH", help="score exactly the files a manifest lists, verifying each sha1")
    p.add_argument("--since", help="real suite: only recordings stamped at or after YYYYMMDD-HHMMSS")
    p.add_argument("--unconfirmed", action="store_true", help="real suite: include recordings not yet listened to")
    p.set_defaults(func=cmd_beatbench, dry_run=False)

    p = sub.add_parser("record", help="capture what is playing to a local FLAC (state/, never committed)")
    p.add_argument("--secs", type=float, default=90.0)
    p.add_argument("--name", help="file label (default: the now-playing artist and title)")
    p.set_defaults(func=cmd_record, dry_run=False)

    p = sub.add_parser("annotate", help="fit an offline beat grid to a recording and render it with clicks to check")
    p.add_argument("path", nargs="?", help="recording (default: the newest)")
    p.add_argument("--bpm", type=_positive_float, help="force the tempo to exactly this (e.g. after the ear check said half or "
                                             "double); only the phase is fitted")
    p.add_argument("--unverified-timing", action="store_true",
                   help="annotate a recording made before captures recorded their timing (no .rec.json)")
    p.set_defaults(func=cmd_annotate, dry_run=False)

    p = sub.add_parser("confirm", help="mark a recording's ground truth as listened to and correct")
    p.add_argument("path", nargs="?", help="recording (default: the newest)")
    p.add_argument("--tapkey", action="store_true", help="confirm the tapped answer key (tapkey) instead of the grid")
    p.set_defaults(func=cmd_confirm, dry_run=False)

    p = sub.add_parser("tapkey", help="turn the taps of a `beat --save --hand` session into an answer key to confirm")
    p.add_argument("path", nargs="?", help="recording (default: the newest one with taps)")
    p.set_defaults(func=cmd_tapkey, dry_run=False)

    p = sub.add_parser("probe", help="guided W0 hardware session: the LCD asks, the pads answer (1 yes, 2 no, 4 skip)")
    p.add_argument("--only", help="comma list of steps (calibrate always runs first); see --list")
    p.add_argument("--list", action="store_true", help="print the steps and exit")
    p.add_argument("--out", help="receipt JSON path (default state/arsenal/keylab/receipts/probe-<stamp>.json)")
    p.set_defaults(func=cmd_probe, dry_run=False)

    p = sub.add_parser(
        "vj", help="the VJ engine: keys, pads, controls, beat, energy, hits and chords as live events for a page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Serve the KeyLab and the music as Server-Sent Events (GET /api/events, GET /api/state, "
                    "POST /api/pads) on 127.0.0.1 for a visual page. Contract and details: arsenal/keylab/vj.py.",
        epilog="PADS: both pad modes are accepted. DAW mode arrives on the 'KeyLab 88 mk3 DAW' input (channel 10, "
               "notes 0-11);\nthe normal pad bank arrives on the 'KeyLab 88 mk3 MIDI' input (channel 10, notes 36-47). "
               "While FL Studio's\nArturia script runs, DAW-mode pads 1-8 ALSO toggle FL step-sequencer steps on "
               "release -- with FL open,\nswitch the pads to the normal bank. One LED writer at a time: do not run "
               "beat/chordview/show alongside.\nControls are learned on touch (any CC; absolute or relative-around-64).")
    p.add_argument("--port", type=int, default=8794, help="HTTP port on 127.0.0.1 (default 8794)")
    vj_engines = ["a"] + sorted(
        x.stem[len("beat_"):] for x in pathlib.Path(__file__).parent.glob("beat_*.py") if x.stem != "beat_a")
    p.add_argument("--engine", choices=vj_engines, default="a",
                   help="beat tracker: a = the house tracker (shipped); others are opt-in contestants (w, g, ...)")
    p.add_argument("--chords", choices=["blend", "sense", "basic"], default="blend",
                   help="blend = the older templates name the audio chords (best under a hardstyle kick and sub bass), "
                        "chordsense on the audio and the keys gives the key, roman numerals and tension (default); "
                        "sense = chordsense names the audio chords too; basic = the templates only, no key or tension")
    p.add_argument("--no-leds", action="store_true",
                   help="never write the pad LEDs (POST /api/pads answers 409; it answers 503 when no KeyLab DAW "
                        "output is found, and hello tells the page either way so it does not post)")
    p.add_argument("--connect", action="store_true",
                   help="send DAW connect when FL Studio is NOT running (default: guest mode, never connects)")
    p.add_argument("--replay-midi", metavar="FILE",
                   help="play notes as if live: a JSON note list or an FL project (.flp, read-only)")
    p.add_argument("--replay-bpm", type=float, help="tempo for tick-based replays (default: the file's, else 100)")
    p.add_argument("--replay-stretch", type=int,
                   help="which stretch of playing to replay, 1-based (default: the largest; 0 = all)")
    p.add_argument("--replay-pattern", type=int, help=".flp: which pattern (default: the newest with notes)")
    p.add_argument("--replay-audio", metavar="FILE",
                   help="analyse this audio file in real time instead of the loopback ('demo' = a made-up groove)")
    p.add_argument("--loop", action="store_true", help="--replay-audio FILE: start the file again when it ends")
    p.add_argument("--no-audio", action="store_true", help="no audio at all (MIDI only)")
    p.add_argument("--no-midi", action="store_true", help="do not open the KeyLab inputs")
    p.add_argument("--rate-limit", action="store_true",
                   help="flash safety at the source: at most 3 'hit' events in any second")
    p.add_argument("--pads", choices=["both", "daw", "bank"], default="both", help="which pad mode to accept")
    p.add_argument("--ahead-ms", type=float, default=250.0, help="announce each beat this long before it lands")
    p.add_argument("--offset-ms", type=float, default=0.0, help="shift every beat's due time (+ = later)")
    p.add_argument("--seed-bpm", type=float, help="seed the beat tracker with this tempo")
    p.add_argument("--secs", type=float, help="stop after N seconds (default: until Ctrl-C)")
    p.add_argument("--quiet", action="store_true", help="print only warnings")
    p.set_defaults(func=cmd_vj, dry_run=False)

    hw_help = "FL's Hardware folder (default: <Documents>/Image-Line/FL Studio/Settings/Hardware)"
    p = sub.add_parser("fl-install", help="copy our FL script (transport only) into FL's Hardware/Aurora KeyLab folder")
    p.add_argument("--hardware-dir", help=hw_help)
    p.add_argument("--dry-run", action="store_true", help="say what would be written; write nothing")
    p.set_defaults(func=cmd_fl_install)
    p = sub.add_parser("fl-uninstall", help="remove our FL script folder (only if it holds only our files)")
    p.add_argument("--hardware-dir", help=hw_help)
    p.add_argument("--dry-run", action="store_true", help="say what would be removed; remove nothing")
    p.add_argument("--force", action="store_true",
                   help="remove even while FL runs or has our script picked (FL then looks for a script that is gone)")
    p.set_defaults(func=cmd_fl_uninstall)
    p = sub.add_parser("fl-status", help="our FL script: installed? same bytes as the repo? FL running? which "
                                         "script FL has on the DAW input?")
    p.add_argument("--hardware-dir", help=hw_help)
    p.set_defaults(func=cmd_fl_status, dry_run=False)
    return ap


def _fl_verb(work, args, *extra) -> int:
    from . import flscript as F
    code, lines = work(F.hardware_dir(args.hardware_dir), *extra)
    for line in lines:
        print(line)
    return code


def cmd_fl_install(args) -> int:
    from . import flscript as F
    return _fl_verb(F.install, args, args.dry_run)


def cmd_fl_uninstall(args) -> int:
    from . import flscript as F
    return _fl_verb(F.uninstall, args, args.dry_run, args.force)


def cmd_fl_status(args) -> int:
    from . import flscript as F
    return _fl_verb(F.status, args)


def tracker_files() -> dict:
    """{name: path} of every contestant file arsenal/keylab/beat_<name>.py, found WITHOUT importing any of them."""
    return {p.stem[len("beat_"):]: p for p in sorted(pathlib.Path(__file__).parent.glob("beat_*.py"))}


def load_trackers(names, BB) -> list:
    """Import and register ONLY the named contestants: a run of `--trackers a,w` executes no code from beat_b.py,
    so one contestant's file can never touch another's run. Returns the names that are unknown."""
    import importlib
    files = tracker_files()
    unknown = []
    for name in names:
        if name in BB.TRACKERS:
            continue
        if name not in files:
            unknown.append(name)
            continue
        path = files[name]
        try:
            m = importlib.import_module(f"arsenal.keylab.{path.stem}")
        except Exception as exc:                                  # a broken contestant is reported, not fatal
            print(f"[beatbench] could not load {path.name}: {type(exc).__name__}: {exc}")
            unknown.append(name)
            continue
        if hasattr(m, "Tracker"):
            BB.register(name, m.Tracker, note=f"{path.name} (clean, numpy-only)")
        else:
            print(f"[beatbench] {path.name} has no Tracker class")
            unknown.append(name)
    return unknown


def _beatbench_args_problem(args, names) -> str:
    """Argument combinations that would silently score the wrong thing are refused before any work is done."""
    if args.vs and args.vs not in names:
        return f"--vs {args.vs}: the reference must be one of the scored trackers ({','.join(names)})"
    if args.exclude_seeds and not args.per_cat:
        return "--exclude-seeds needs --per-cat: only the stratified draw can leave loops out"
    if args.suite == "bright_variants" and args.variant_seed is None:
        return "--suite bright_variants needs --variant-seed N"
    if args.manifest and args.suite not in ("loops", "real"):
        return "--manifest works with --suite loops or --suite real"
    if args.manifest and (args.per_cat or args.exclude_seeds):
        return "--manifest scores exactly its own list; drop --per-cat / --exclude-seeds"
    if args.since and args.suite != "real":
        return "--since applies to --suite real"
    if args.write_manifest and args.suite not in ("loops", "real"):
        return "--write-manifest works with --suite loops or --suite real"
    return ""


def cmd_beatbench(args) -> int:
    import copy
    from . import beatbench as BB
    names = [t.strip() for t in args.trackers.split(",") if t.strip()]
    problem = _beatbench_args_problem(args, names)
    if problem:
        print(f"beatbench: {problem}", file=sys.stderr)
        return 2
    unknown = load_trackers(names, BB)
    if unknown:
        print(f"unknown tracker(s) {unknown}; available: {sorted(set(BB.TRACKERS) | set(tracker_files()))}",
              file=sys.stderr)
        return 2
    manifest, manifest_sha1 = (BB.read_manifest(args.manifest) if args.manifest else (None, None))
    cases, loops = [], []
    if args.suite in ("synthetic", "all"):
        cases += BB.synthetic_suite()
    if args.suite == "drift":
        cases += BB.drift_suite()
    if args.suite == "shift":
        cases += BB.shift_suite()
    if args.suite == "bright":
        cases += BB.bright_drift_suite()
    if args.suite == "bright_variants":
        cases += BB.bright_variants_suite(args.variant_seed)
    if args.suite == "real":
        cases += BB.recording_suite(confirmed_only=not args.unconfirmed, since=args.since, manifest=manifest)
    excluded = []
    if args.suite in ("loops", "all"):
        if manifest is not None:
            loops = BB.manifest_loops(manifest)
        elif args.per_cat:
            pool = BB.find_bpm_loops()
            seeds = [int(s) for s in args.exclude_seeds.split(",") if s.strip()]
            exclude = BB.held_out_exclusion(seeds, args.exclude_per_cat, pool=pool) if seeds else None
            excluded = sorted(exclude or [])
            tuned_names = BB.receipt_case_names([r for r in args.exclude_receipts.split(",") if r.strip()])                 if args.exclude_receipts else None
            picked = BB.stratified_loops(args.per_cat, rng_seed=args.seed, exclude=exclude, pool=pool,
                                         exclude_names=tuned_names)
            loops = BB.loop_suite(n=len(picked), paths=picked, rng_seed=args.seed)
        else:
            loops = BB.loop_suite(n=args.n, rng_seed=args.seed)
        cases += loops
        if args.seeded:
            for c in loops:
                s = copy.copy(c)
                s.seed_bpm, s.name = c.bpm, c.name + " [seeded]"
                cases.append(s)
    written = None
    if args.write_manifest:
        drawn = loops if args.suite in ("loops", "all") else cases
        sha = BB.write_manifest(args.write_manifest, drawn, "loops" if args.suite != "real" else "real",
                                per_cat=args.per_cat, seed=args.seed, n=args.n,
                                exclude_seeds=args.exclude_seeds, exclude_per_cat=args.exclude_per_cat,
                                since=args.since)
        written = {"path": os.path.abspath(args.write_manifest), "sha1": sha}
        print(f"manifest: {written['path']} (sha1 {sha})")
    print(f"beatbench: {len(cases)} cases, trackers {names}")
    rep = BB.bench(cases, names, hop=args.hop)
    rep["suite"], rep["n"], rep["seed"] = args.suite, args.n, args.seed
    rep["args"] = {k: v for k, v in vars(args).items() if k != "func"}
    rep["argv"] = sys.argv[1:]
    if manifest is not None:
        rep["manifest"] = {"path": os.path.abspath(args.manifest), "sha1": manifest_sha1}
    if written:
        rep["manifest_written"] = written
    if excluded:
        rep["excluded_paths"] = excluded
    rep["case_index"] = BB.case_index(cases)
    rc = 0
    if args.vs:
        if args.vs in rep["trackers"] and "cases" in rep["trackers"][args.vs]:
            rep["paired"] = BB.paired_report(cases, rep, args.vs)
        else:
            print(f"beatbench: --vs {args.vs}: the reference could not be scored (unavailable); no paired result",
                  file=sys.stderr)
            rc = 1
    print(f"receipt: {BB.save_report(rep)}")
    return rc


def _newest_recording(path=None, need=None):
    import glob
    from . import beatbench as BB
    if path:
        return path
    files = sorted(glob.glob(os.path.join(BB.RECORDINGS_DIR, "*.flac")))
    if need:
        files = [f for f in files if os.path.exists(f + need)]
    if not files:
        raise SystemExit("no recordings yet: py -m arsenal.keylab record" if not need else
                         f"no recording has a {need} yet")
    return files[-1]


def cmd_record(args) -> int:
    from . import beatsync
    beatsync.record(args.secs, name=args.name)
    return 0


def cmd_annotate(args) -> int:
    import json
    import soundfile as sf
    from . import beatbench as BB
    from . import beatsync
    path = _newest_recording(args.path)
    if not os.path.exists(path):
        print(f"annotate: no such recording: {path}", file=sys.stderr)
        return 1
    timing = beatsync.read_timing(path)
    if timing is None and not args.unverified_timing:
        print(f"annotate: {os.path.basename(path)} has no capture timing record ({os.path.basename(path)}.rec.json), "
              f"so a gap in the capture cannot be ruled out. Record it again, or pass --unverified-timing to "
              f"annotate it anyway (it will not count as held-out ground truth).", file=sys.stderr)
        return 1
    if timing is not None:
        drift_s = abs(float(timing["wall_secs"]) - float(timing["sample_secs"]))
        if timing.get("gap") or drift_s > beatsync.GAP_TOL_S:
            print(f"annotate: refused -- {os.path.basename(path)} holds {timing['sample_secs']:.3f} s of samples "
                  f"captured over {timing['wall_secs']:.3f} s of wall clock ({drift_s * 1000:.0f} ms apart, the limit "
                  f"is {beatsync.GAP_TOL_S * 1000:.0f} ms). Audio went missing during the capture, so everything after "
                  f"the gap sits earlier than the music did and one grid cannot fit it. Record it again.",
                  file=sys.stderr)
            return 1
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = data.mean(axis=1)
    g = BB.fit_grid(audio, rate, bpm=args.bpm)
    clicks = BB.render_clicks(audio, rate, g["bpm"], g["first_beat"], os.path.splitext(path)[0] + " CLICKS.wav")
    side = {**g, "confirmed": False, "audio_sha1": BB.file_sha1_uncached(path),
            "timing_verified": timing is not None,
            "method": f"{g['method']}; whole track; awaiting the ear check"}
    side["clicks"] = BB.clicks_record(clicks, side)
    with open(path + ".beats.json", "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1)
    forced = " (forced)" if args.bpm is not None else ""
    print(f"{g['bpm']} BPM{forced}, first beat {g['first_beat']} s -> listen: {clicks}")
    others = [c for c in g["candidates"] if abs(c["bpm"] / g["bpm"] - 1) > 0.004]
    if others:
        print("other tempi it could be (score): " + ", ".join(f"{c['bpm']} {'/'.join(c['rel'])} ({c['score']})"
                                                         for c in others[:6]))
    print("if the clicks sit on the beat all the way:")
    print(f'  py -m arsenal.keylab confirm "{path}"')
    print("if they are at half or double speed (or 2/3, 3/2):")
    print(f'  py -m arsenal.keylab annotate "{path}" --bpm <the right one from the list above>')
    return 0


def _describe_grid(meta) -> str:
    if meta.get("sections"):
        return "; ".join(f"{s['start']:.1f}-{s['end']:.1f} s at {s['bpm']} BPM from {s['first_beat']} s"
                         for s in meta["sections"])
    return f"{meta.get('bpm')} BPM, first beat {meta.get('first_beat')} s"


def cmd_confirm(args) -> int:
    import json
    import time as _t
    from . import beatbench as BB
    path = _newest_recording(args.path)
    kind, verb = (".tapkey.json", "tapkey") if args.tapkey else (".beats.json", "annotate")
    side = path + kind
    if not os.path.exists(side):
        print(f"confirm: {os.path.basename(path)} has no {'tapped answer key' if args.tapkey else 'grid'} to confirm "
              f"yet. First run:\n  py -m arsenal.keylab {verb} \"{path}\"", file=sys.stderr)
        return 1
    with open(side, encoding="utf-8") as f:
        meta = json.load(f)
    why = BB.clicks_mismatch(meta)
    if why:
        print(f"confirm: refused -- {os.path.basename(side)} cannot be confirmed: {why}. Re-render and listen again:\n"
              f"  py -m arsenal.keylab {verb} \"{path}\"", file=sys.stderr)
        return 1
    print(f"confirming the grid you listened to in {meta['clicks']['path']}:")
    print(f"  {_describe_grid(meta)}")
    meta["confirmed"], meta["confirmed_at"] = True, _t.strftime("%Y-%m-%d %H:%M:%S")
    with open(side, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(f"confirmed: {side}")
    return 0


def cmd_tapkey(args) -> int:
    from . import beatbench as BB
    path = _newest_recording(args.path, need=".hand.json")
    try:
        doc = BB.tap_key(path)
    except ValueError as exc:
        print(f"tapkey: {exc}", file=sys.stderr)
        return 1
    print(f"tapped answer key for {os.path.basename(path)}: {len(doc['sections'])} steady stretch(es), "
          f"{doc['taps']} taps ({doc['dropped_taps']} outside any stretch)")
    for s in doc["sections"]:
        kick = (f"taps {s['kick_offset_ms']:+.0f} ms vs the kicks ({s['kick_matched']:.0%} matched)"
                if s["kick_offset_ms"] is not None else "no kicks near the taps")
        print(f"  {s['start']:7.2f}-{s['end']:7.2f} s  {s['bpm']:8.3f} BPM  {s['taps']:3d} taps  "
              f"jitter {s['jitter_ms']:.0f} ms  {kick}")
    print(f"written: {path}.tapkey.json\nlisten: {doc['clicks']['path']}\nif the clicks sit on the beat:\n"
          f'  py -m arsenal.keylab confirm "{path}" --tapkey')
    return 0


def cmd_probe(args) -> int:
    from . import probe as PR
    if args.list:
        print((PR.__doc__ or "").split("Steps", 1)[-1].strip())
        return 0
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    unknown = [s for s in (only or []) if s not in PR.STEPS]
    if unknown:
        print(f"unknown step(s) {unknown}; choose from {PR.STEPS}")
        return 2
    session = PR.Session(PR.Rig(PR.open_real_ports), args.out or PR.default_receipt_path())
    print(f"probe: receipts -> {session.path}")
    path = session.run(only)
    print(f"probe done: {path}")
    return 0


def _utf8_safe_stdio() -> None:
    """A song title in any script must never crash a verb: a piped or redirected Windows stdout defaults to cp1252,
    and printing a title it cannot encode raised UnicodeEncodeError before a recording had even started. Speak
    UTF-8, and replace (never raise on) anything that still cannot be written."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconf = getattr(stream, "reconfigure", None)
        if callable(reconf):
            try:
                reconf(encoding="utf-8", errors="replace")
            except (ValueError, OSError, TypeError):
                try:
                    reconf(errors="replace")
                except (ValueError, OSError, TypeError):
                    pass


def main(argv=None) -> int:
    _utf8_safe_stdio()
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (RuntimeError, ValueError) as exc:
        print(f"{args.verb}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
