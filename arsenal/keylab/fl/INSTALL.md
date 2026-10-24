# Aurora KeyLab: our FL Studio script (v0, "Aurora drives")

Daniel, 2026-10-22: "Lets let the play pause controls work with FL but the fades for mixer is dumb, i want them
unassociated so I can link them to whatever by default." And 2026-10-24: "the only thing i need from the FL
integration is the transport playback".

This script takes the place of Arturia's script on the KeyLab's **DAW** port only. With it:

- **The transport buttons work in FL**: Play/pause, Stop, Record, Loop (loop recording), Metronome, Tap tempo,
  Rewind and Fast forward (while held), Save, Undo, Redo.
- **FL ignores everything else on that port**: the faders, knobs, dial, Back, Quantize, the screen buttons and the
  DAW-bank pads do nothing in FL. Aurora's programs still see them and can bind them to anything.
- **The bank A-D pads still play in FL**: they pass through untouched, so FPC, Addictive Drums or the selected
  channel keeps playing them (Arturia's FPC/Drumaxx note remap is not copied, so pads play their plain notes).
- **FL never writes the screen or the pads.** No more "The Grandeur Pattern 7" repainting over our screen.
- The Play, Record, Loop and Metronome lights follow FL, changing only when the state changes.

Arturia's files are not touched. Going back is one dropdown.

## 1. Put the script where FL looks (one command)

In the terminal, from `E:\AI-Setup`:

```
py -m arsenal.keylab fl-install --dry-run     # shows what it would write, writes nothing
py -m arsenal.keylab fl-install               # copies one file
```

It writes exactly one file:
`C:\Users\L5\Documents\Image-Line\FL Studio\Settings\Hardware\Aurora KeyLab\device_AuroraKeyLab.py`
(the folder `C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Aurora KeyLab/`). It refuses if that folder
holds anything it did not put there, and it never opens any other folder, Arturia's included.

`py -m arsenal.keylab fl-status` tells you whether it is installed, whether it matches the repo, whether FL is running,
and which script FL has saved for the KeyLab's DAW input.

## 2. Pick it in FL (about 30 seconds)

1. **Options > MIDI settings.** Click **Update MIDI scripts** at the bottom (or restart FL) so FL sees the new folder.
2. In the **Input** list, click **KeyLab 88 mk3 DAW**. Set **Controller type** to **Aurora KeyLab (user)**.
   Leave its **port number** as it is (236), and leave the output **KeyLab 88 mk3 DAW** on the same number. The script
   sends its lights through the output with the matching number.
3. Leave **KeyLab 88 mk3 MIDI** alone: it stays on **KeyLab mk3 Arturia dev** (or generic), so your keys play notes and
   Analog Lab / V Collection still get their controls.
4. Optional check: **View > Script output**, tab **KeyLab 88 mk3 DAW**. It should say
   `Aurora KeyLab v0: FL keeps the transport; ...`.
5. **After an FL restart or a KeyLab power cycle, check the Controller type again.** Arturia's script claims this
   keyboard's hardware ID, so FL may link it back by itself. If FL's screen-repainting comes back, that is why.

## 3. Going back to Arturia's script

**Options > MIDI settings > KeyLab 88 mk3 DAW > Controller type > KeyLab mk3** (it may be listed as
**KeyLab mk3 (user)**, because Arturia's script lives in your user folder). That is all. FL unloads ours (which
drops DAW mode) and loads Arturia's (which connects again and repaints everything the way it used to).

To remove our file afterwards: `py -m arsenal.keylab fl-uninstall`. Switch back first: it refuses while FL has our
script picked or FL is running (so FL never starts looking for a script that is gone), unless you add `--force`. It
removes only our folder, and only if it holds nothing but our file.

## 4. First-run drill (the freeze check, P23)

FL 26.1.3 shipped fixes for "freezes when MIDI scripts call functions in FL Studio" (#22368) and "crash when using
GlobalTransport commands" (#22359). Your build (26.1.3.5570) has those fixes, but the drill doctrine says we check on
your machine before trusting it. Image-Line fixed two more related freezes in **26.1.7** (#22604, a freeze when a script
sends SysEx, and #22725 / #22689 in GlobalTransport); updating FL first is the safest order, and your call. Arturia's
own script makes the same kinds of calls every day. Every FL function the script can call is listed at the top of the script.

Save your project first. Then, **one button at a time**, wait two seconds after each, and **stop at the first freeze**
(FL stops responding, or the KeyLab stops answering). Tell Vandor which button it was.

| # | Do this | You should see | FL function it calls |
|---|---|---|---|
| 0 | Pick the script (section 2) and wait 10 s | FL keeps running; the Play/Record/Loop/Metronome lights go dim | `device.midiOutSysex`, then the four light readers |
| 1 | Press **Metronome** | metronome toggles, its light follows (on release) | `transport.globalTransport` (metronome) |
| 2 | Press **Play** | FL plays (on release), the Play light turns green | `transport.start` |
| 3 | Press **Play** again | FL pauses | `transport.start` |
| 4 | Press **Stop** | FL stops | `transport.stop` |
| 5 | Hold **Rewind** for 1 s, let go | the song position runs back while held, stops on release | `transport.continuousMove` |
| 6 | Hold **Fast forward** for 1 s, let go | runs forward while held | `transport.continuousMove` |
| 7 | Press **Tap** four times in tempo | FL's tempo follows | `transport.globalTransport` (tap) |
| 8 | Press **Loop** | loop recording toggles, the Loop light follows | `transport.globalTransport` (loop record) |
| 9 | Press **Record** | recording arms (on release), the Record light turns red; press again to disarm | `transport.record` |
| 10 | Move a note in the piano roll, then press **Undo**, then **Redo** | the move is undone, then redone | `general.undoUp`, `general.undoDown` |
| 11 | Press **Save** | FL saves (or asks where, for a new project) | `transport.globalTransport` (save) |
| 12 | Move every fader, turn every knob and the dial, press Back, Quantize, the screen buttons, tap the pads (DAW position) | **nothing happens in FL** | none |
| 13 | Pad selector to a normal bank, select an FPC channel, tap a pad | it plays (the script passes bank pads to FL untouched); if it does not, tell Vandor | none |

If all fourteen pass, the drill is done: tell Vandor "drill passed" and the date, and it gets a dated receipt.

## What you give up compared with Arturia's script (so nothing surprises you)

- Faders no longer move FL's mixer or plugin parameters; knobs no longer pan or move plugin knobs; knob 9 / fader 9 no
  longer set the selected track's pan and volume. (That is the point: they are free for Aurora to bind.)
- FL's own **Link to controller** cannot learn the faders or knobs either, because the script tells FL to ignore them.
  If you ever want that, it is a one-line change; ask.
- The **dial** no longer browses FL, its click no longer opens plugins or Analog Lab mode, and **Back** no longer
  closes plugin windows. **Quantize** no longer quick-quantizes.
- The **screen buttons** no longer switch Device/Mixer, change patterns, or mute/solo/arm.
- The **DAW-bank pads** no longer run FL's 32-step sequencer. Any pad note that arrives on the DAW port is ignored by
  FL, and Arturia's re-mapping of pad notes for FPC and Drumaxx (which lives in its DAW-port script) is gone. Pads in
  banks A-D that arrive on the **MIDI** port (what Aurora's VJ engine sees today) are not affected: FL plays them on
  the selected channel as before.
- The **screen** no longer shows FL's track names, values or the "Connected" card; Aurora's screen writer owns it.
- The **Play light** no longer blinks with the beat; it is simply green while FL plays.

## One thing we do not know yet

Arturia's script also sends one setting at start-up that moves the DAW pads onto the DAW port. Ours does not send it
(v0 sends nothing but the handshake and the four lights). Today the keyboard still remembers it from Arturia's script.
**After a power cycle with our script picked**, tap a pad in the DAW position: if FL plays a sound, the pads moved to
the other port. Tell Vandor; the fix is one more message at start-up, held for your OK.
