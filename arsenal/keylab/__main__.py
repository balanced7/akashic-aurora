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

Global: --port SUBSTR picks the output by name (default: first containing 'keylab'); --dry-run prints bytes, sends nothing.
"""
from __future__ import annotations

import argparse
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


# --- dispatch ------------------------------------------------------------------------------------
def _add_send_flags(p, color_default=None):
    p.add_argument("--port", help="output port name substring (default: first containing 'keylab')")
    p.add_argument("--dry-run", action="store_true", help="print bytes, send nothing")
    p.add_argument("--no-connect", action="store_true", help="do not auto-arm DAW mode first")
    p.add_argument("--req", type=lambda x: int(x, 0), default=P.REQ_CTRL,
                   help="first payload byte (0x00 = live colour, confirmed; 0x02 = white, probe-only)")
    p.add_argument("--bank", default="DAW",
                   help="pad bank (default DAW -- the only bank with live host colour; keyboard must be in DAW mode)")


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

    p = sub.add_parser("beatbench", help="score beat trackers on the same ground truth (synthetic + your BPM loops)")
    p.add_argument("--suite", choices=["synthetic", "loops", "all", "drift", "shift", "bright", "real"],
                   default="synthetic",
                   help="all = synthetic + loops (the reconciliation set); drift = constant-tempo syncopation traps; "
                        "bright = drift with a sawtooth bass; real = your recordings with confirmed ground truth")
    p.add_argument("--trackers", default="aubio,librosa",
                   help="comma list: aubio, librosa, and every arsenal/keylab/beat_<name>.py by its <name> (a, b, ...)")
    p.add_argument("--n", type=int, default=40, help="loops to sample for the loops suite")
    p.add_argument("--per-cat", type=int, default=0, help="stratified loops: this many per category (kick/tops/melodic)")
    p.add_argument("--seeded", action="store_true", help="also run every loop with its true BPM as the seed")
    p.add_argument("--seed", type=int, default=7, help="sampling seed, so a run can be repeated exactly")
    p.add_argument("--hop", type=int, default=512)
    p.add_argument("--exclude-seeds", default="",
                   help="held-out draw: leave out every loop the stratified draws at these seeds used (e.g. 7,11)")
    p.add_argument("--vs", default="", help="print each tracker's per-class PAIRED difference against this one")
    p.add_argument("--unconfirmed", action="store_true", help="real suite: include recordings not yet listened to")
    p.set_defaults(func=cmd_beatbench, dry_run=False)

    p = sub.add_parser("record", help="capture what is playing to a local FLAC (state/, never committed)")
    p.add_argument("--secs", type=float, default=90.0)
    p.add_argument("--name", help="file label (default: the now-playing artist and title)")
    p.set_defaults(func=cmd_record, dry_run=False)

    p = sub.add_parser("annotate", help="fit an offline beat grid to a recording and render it with clicks to check")
    p.add_argument("path", nargs="?", help="recording (default: the newest)")
    p.add_argument("--bpm", type=float, help="force the tempo (e.g. after the ear check said half or double)")
    p.set_defaults(func=cmd_annotate, dry_run=False)

    p = sub.add_parser("confirm", help="mark a recording's ground truth as listened to and correct")
    p.add_argument("path", nargs="?", help="recording (default: the newest)")
    p.set_defaults(func=cmd_confirm, dry_run=False)

    p = sub.add_parser("probe", help="guided W0 hardware session: the LCD asks, the pads answer (1 yes, 2 no, 4 skip)")
    p.add_argument("--only", help="comma list of steps (calibrate always runs first); see --list")
    p.add_argument("--list", action="store_true", help="print the steps and exit")
    p.add_argument("--out", help="receipt JSON path (default state/arsenal/keylab/receipts/probe-<stamp>.json)")
    p.set_defaults(func=cmd_probe, dry_run=False)
    return ap


def cmd_beatbench(args) -> int:
    import importlib
    import pathlib
    from . import beatbench as BB
    # Every contestant registers itself: arsenal/keylab/beat_<name>.py with a Tracker class becomes tracker <name>.
    for path in sorted(pathlib.Path(__file__).parent.glob("beat_*.py")):
        name = path.stem[len("beat_"):]
        try:
            m = importlib.import_module(f"arsenal.keylab.{path.stem}")
            if hasattr(m, "Tracker"):
                BB.register(name, m.Tracker, note=f"{path.name} (clean, numpy-only)")
        except Exception as exc:                                  # a broken contestant is reported, not fatal
            print(f"[beatbench] could not load {path.name}: {type(exc).__name__}: {exc}")
    names = [t.strip() for t in args.trackers.split(",") if t.strip()]
    unknown = [t for t in names if t not in BB.TRACKERS]
    if unknown:
        print(f"unknown tracker(s) {unknown}; registered: {sorted(BB.TRACKERS)}")
        return 2
    cases = []
    if args.suite in ("synthetic", "all"):
        cases += BB.synthetic_suite()
    if args.suite == "drift":
        cases += BB.drift_suite()
    if args.suite == "shift":
        cases += BB.shift_suite()
    if args.suite == "bright":
        cases += BB.bright_drift_suite()
    if args.suite == "real":
        cases += BB.recording_suite(confirmed_only=not args.unconfirmed)
    if args.suite in ("loops", "all"):
        if args.per_cat:
            exclude = set()
            for s in filter(None, args.exclude_seeds.split(",")):
                exclude |= set(BB.stratified_loops(30, rng_seed=int(s)))
            picked = BB.stratified_loops(args.per_cat, rng_seed=args.seed, exclude=exclude or None)
            loops = BB.loop_suite(n=len(picked), paths=picked, rng_seed=args.seed)
        else:
            loops = BB.loop_suite(n=args.n, rng_seed=args.seed)
        cases += loops
        if args.seeded:
            import copy
            for c in loops:
                s = copy.copy(c)
                s.seed_bpm, s.name = c.bpm, c.name + " [seeded]"
                cases.append(s)
    print(f"beatbench: {len(cases)} cases, trackers {names}")
    rep = BB.bench(cases, names, hop=args.hop)
    rep["suite"], rep["n"], rep["seed"] = args.suite, args.n, args.seed
    if args.vs and args.vs in rep["trackers"] and "cases" in rep["trackers"][args.vs]:
        group = {}
        for c in cases:
            cat = (c.meta or {}).get("category", c.source)
            group[c.name] = f"{cat}{' seeded' if c.seed_bpm and c.source == 'loop' else ''}"
        ref = rep["trackers"][args.vs]["cases"]
        rep["paired"] = {}
        for name, t in rep["trackers"].items():
            if name == args.vs or "cases" not in t:
                continue
            out = {}
            for g in sorted(set(group.values())):
                rc = [r for r in t["cases"] if group.get(r["case"]) == g]
                rr = [r for r in ref if group.get(r["case"]) == g]
                out[g] = {k: BB.paired(rc, rr, k) for k in ("F", "CMLt", "bpm_spread")}
                f, c, sp = out[g]["F"], out[g]["CMLt"], out[g]["bpm_spread"]
                if f.get("n"):
                    print(f"[paired] {name} - {args.vs} | {g:18} n {f['n']:3}  F {f['mean']:+.3f} {f['ci95']}  "
                          f"CMLt {c['mean']:+.3f} {c['ci95']}  spread {sp.get('mean', 0):+.3f} {sp.get('ci95')}")
            rep["paired"][name] = out
    print(f"receipt: {BB.save_report(rep)}")
    return 0


def _newest_recording(path=None):
    import glob
    import os
    from . import beatbench as BB
    if path:
        return path
    files = sorted(glob.glob(os.path.join(BB.RECORDINGS_DIR, "*.flac")))
    if not files:
        raise SystemExit("no recordings yet: py -m arsenal.keylab record")
    return files[-1]


def cmd_record(args) -> int:
    from . import beatsync
    beatsync.record(args.secs, name=args.name)
    return 0


def cmd_annotate(args) -> int:
    import json
    import soundfile as sf
    from . import beatbench as BB
    path = _newest_recording(args.path)
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = data.mean(axis=1)
    g = BB.fit_grid(audio, rate, *((args.bpm - 0.3, args.bpm + 0.3) if args.bpm else ()))
    clicks = BB.render_clicks(audio, rate, g["bpm"], g["first_beat"], path[:-5] + " CLICKS.wav")
    json.dump({**g, "confirmed": False, "method": "fit_grid, whole track; awaiting the ear check"},
              open(path + ".beats.json", "w", encoding="utf-8"), indent=1)
    print(f"{g['bpm']} BPM, first beat {g['first_beat']} s -> listen: {clicks}")
    print("if the clicks sit on the beat all the way: py -m arsenal.keylab confirm")
    return 0


def cmd_confirm(args) -> int:
    import json
    import time as _t
    path = _newest_recording(args.path)
    side = path + ".beats.json"
    meta = json.load(open(side, encoding="utf-8"))
    meta["confirmed"], meta["confirmed_at"] = True, _t.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(meta, open(side, "w", encoding="utf-8"), indent=1)
    print(f"confirmed: {side}")
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


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (RuntimeError, ValueError) as exc:
        print(f"{args.verb}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
