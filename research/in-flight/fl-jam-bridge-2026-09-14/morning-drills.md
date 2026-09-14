# Morning drills: first jam with the arsenal band in FL

- **Status:** in-flight checklist, rewritten 2026-09-14 by the round 2 verifier. It replaces the round 1 page: the pause trap it warned about is fixed, and the band now keeps FL's bars through pause, resume and Play from mid-bar. Updated the same night after the engine and VFX polish: new grooves for seeds 1, 3 and 5, comp rhythms that follow the drum style, and the new **Feel: Dropout** controls (drill VX9). Re-checked after the repair round: the neo-soul pushes now land with the swung hat, F to D's comp is two-note shells, its gospel bass runs only into bars 5 and 1, and a held chord comes back after a rest bar. The controls are unchanged. **Round 3 clock repair (same day):**
  - **Clock:** Keep counting now re-anchors to FL's own bar lines after any seek, jump or late onTick, so it can't stay a 16th off the click. A seek back to the loop top from beat 4 no longer fires a stacked burst of notes.
  - **Dropout:** rests lean on the last bar of each 4-bar phrase.
  - **Switches:** a comp push into a bar line where a switch waits is skipped.
  - **Files:** the seed files and .mid files were regenerated.
  - **Still open:** drill VX5 decides the clock defaults.
- **What we're doing:** load Claude's band (one VFX Script) into a Patcher, give it your instruments, check each lane for five minutes, then jam over the six seed grooves. About 45 minutes, coffee included.
- **Nothing has been copied into FL or Documents yet.** Every step below is done together at the keyboard.
- **Deeper reference:** [arsenal/fl/vfx/README.md](../../../arsenal/fl/vfx/README.md) (controls, drum maps, drills VX0-VX9).

## 0. Before we start (2 minutes)

- [ ] FL Studio 2026 open, a fresh empty project, **pattern mode**, metronome on.
- [ ] Note the project PPQ (Options > Project > General). Leave it as it is for the first run.
- [ ] Good to know: the KeyLab **Play** button toggles play and **pause**; **Stop** returns to the start. Both are safe with the band.

## 1. Tick probe (3 minutes, before the band)

This answers the one timing question no document settles: does FL call `onTick` on every tick? Everything below works either way, but the answer tells us which Clock mode to trust.

- [ ] Add a **Patcher** channel, put a **VFX Script** in it, open its Script tab, replace the text with this, and compile:

```python
import flvfx as vfx
last = None
biggest = 0

def onTick():
    global last, biggest
    t = vfx.context.ticks
    if vfx.context.isPlaying:
        if last is None:
            vfx.context.form.setNormalizedValue('First tick', min(t, 16) / 16.0)
        elif t > last and t - last > biggest:
            biggest = t - last
            vfx.context.form.setNormalizedValue('Largest gap', min(biggest, 16) / 16.0)
        last = t
    else:
        last = None

def createDialog():
    form = vfx.ScriptDialog('', 'Tick probe. Play 8 bars from the start, then read the two knobs.')
    form.addInputKnob('First tick', 0, 0, 16, hint='ticks on the first onTick after Play')
    form.addInputKnob('Largest gap', 0, 0, 16, hint='largest jump in ticks between two onTick calls')
    return form
```

- [ ] Press Play from the start, let 8 bars go by, then Stop. Write down both knob values.
  - **Largest gap = 1:** perfect. FL calls onTick every tick, and every Clock mode is fully covered by the simulations.
  - **Largest gap above 1:** still fine, and both Clock modes keep the loop's first beat and FL's bar lines. Tell Claude the number anyway. Drill VX5 uses it to settle the clock defaults: an onTick much later than usual, landing right on an FL loop wrap, drops the loop's last few ticks, and a gap longer than a hi-hat note can make short hits go missing.
- [ ] Delete the probe (or keep the channel muted). Its values go on the receipt.

## 2. Copy one file (3 minutes)

| What | From (repo) | To |
|---|---|---|
| The six seed grooves | `E:\AI-Setup\arsenal\fl\vfx\generated\arsenal_patterns.py` | `C:\Users\L5\Documents\Image-Line\VFX Script\Python\arsenal_patterns.py` |
| The band script | `E:\AI-Setup\arsenal\fl\vfx\arsenal_band.py` | not copied: open it in Notepad, select all, copy (pasted in step 4) |

- [ ] **Confirm the folder first.** FL's registry lists the shared data folder as `C:\Users\L5\Documents\Image-Line\`. VFX Script itself carries the sentence *"If you have external Python files that you want to import in your script then put them in this folder:"* followed by the real path (look in its help or script info). If that path differs from the one above, use FL's.
- [ ] Create the `VFX Script\Python` folders if they aren't there yet.
- [ ] Copy the **generated** module, not `E:\AI-Setup\arsenal\fl\vfx\arsenal_patterns.py`. That one is the two-groove example with the same file name.

## 3. Build the rack (5 minutes)

- [ ] In a new **Patcher** channel, add **VFX Script**, then your instruments:
  - **Bass:** Kontakt DjinnBass or Nolly Bass (keep clear of keyswitch zones), Serum 2, or FL Transistor Bass
  - **Drums:** Addictive Drums 2 (or FPC)
  - **Keys (comp):** a Kontakt piano, FL Keys or an Arturia keys instrument
  - **Pad:** a lush Serum 2 or Arturia pad
- [ ] Right-click the VFX Script icon in Patcher and **activate voice outputs 1-4**. Extra outputs start switched off.
- [ ] Wire output 1 to bass, 2 to drums, 3 to comp and 4 to pad. Only one keys instrument? Wire 3 and 4 both into it; each seed uses comp or pad, never both.

## 4. Load the band (3 minutes)

- [ ] VFX Script's Script tab: replace everything with the whole of `arsenal_band.py`, then compile.
- [ ] **Read the description.** It should say `6 patterns from arsenal_patterns` and list titles 0 to 5.
  - **"fallback"** means the import folder is wrong. The band still plays a one-bar test groove, so the wiring can be checked anyway. Fix the folder, then tick **Patterns: Reload** or recompile.
- [ ] **Feel: Drum map:**
  - `AD2 default` if Addictive Drums 2 uses its factory keymap
  - `GM` if AD2 has its GM map preset loaded, or for FPC's Empty preset
  - `FPC` for other FPC kits

## 5. The seeds (Band: Pattern knob)

Set FL's tempo to the BPM shown before playing each one. The knob stops at 5; higher values play seed 5.

| Knob | Seed | Key, BPM | Lanes | Feel |
|---|---|---|---|---|
| 0 | Db ballad lift | Db, 66 | bass, drums, pad | whole-note roots, cross-stick on 3, tom fill in bar 8 |
| 1 | Eb neo-soul pocket | Eb, 84 | bass, drums, comp | swung 16th hats, laid-back snare, a pocket bass with ghost notes and holes (its 7th lands with the kick on the "and" of 3), comp pushed a 16th early, landing with the swung hat |
| 2 | D halftime sunrise | D, 72 | bass, drums, pad | root-fifth half notes, snare on 3, fill in bar 8 |
| 3 | F to D drop | F then D, 76 | bass, drums, comp | brushes ride with a triplet skip, two-note comp shells (D3 to D4) on the Charleston (1 and the "and" of 2), gospel bass stepping a half step into each change, with a triplet run on the ride's skip into bar 5 and back into bar 1; drops a minor third at bar 5 |
| 4 | Bbm lament | Bb minor, 60 | bass, drums, pad | Bb-Ab-Gb-F lament, ride swell into a crash every 4 bars |
| 5 | Gb real V7 | Gb, 118 | bass, drums, comp | four on the floor, bass and open hat together on every "and", comp stabs on 1, the "and" of 2 and 4 |

## 6. First five minutes per lane

Keep **Band: Lane** on All and solo a lane with the **Mute** checkboxes. Stop between drills.

- [ ] **Drums (seed 2, 72 BPM):** mute bass and pad, play 8 bars.
  - **Listen for:** kick on the click, snare on beat 3, the fill in bar 8, one crash at the top of the loop. With `AD2 default`, the closed hat must sound like a hat, not a cymbal.
  - **After Stop:** nothing keeps ringing.
- [ ] **Bass (seed 0, 66 BPM):** unmute bass. Expect one note per bar: Gb, Bb, a low Gb, Db.
  - **Listen for:** each note starting exactly on the downbeat and ending cleanly. If it's an octave off, that's the instrument's range; the band sends plain MIDI numbers.
- [ ] **Comp (seed 1, 84 BPM):** comp plus drums. Each chord arrives a 16th before its bar line (only the very first lands on beat 1), with one short stab later in the bar: on the "a" of 3 in bars 1, 3, 5 and 7, on the "and" of 2 in the others.
  - **Listen for:** the voicings sit from the F below middle C up to the F above it, where your left hand usually lives. If you want to comp yourself, just tick **Mute: Comp**.
  - **Also:** each early push should land exactly with a swung hat. If one sounds just ahead of the hat (a flam), tell Claude.
  - **Try:** **Feel: Humanize** at 0.3, so velocities breathe but repeat each pass. Leave **Feel: Swing** at 0 on this seed: its swing is already built in.
- [ ] **Pad (seed 4, 60 BPM):** pad plus bass.
  - **Listen for:** middle C holding through every chord, and the F above it on top the whole way except the F7b9, where it lifts to Gb, while the bass walks down.
  - **Then:** tick **Mute: Pad** in the middle of a chord. **It must stop at once.** If it rings to the end of the bar, tell Claude: it means FL doesn't hand the band its own voices back.
- [ ] **Switch while playing:** play seed 3, turn **Pattern** to 1 in the middle of a bar.
  - **Pass:** the change lands on the next bar line, never mid-bar, with no short blip of the old chord just before it (the old groove's push into that bar line is skipped).
  - **Next loop:** set **Switch at** to Next loop; the change waits for the top of the 8-bar loop.
  - **Panic:** releases everything instantly, and the band plays on.
- [ ] **Pause and switch:** press KeyLab Play mid-bar (pause), turn Pattern, press Play again.
  - **Pass:** the new groove starts on FL's next bar line, with its kick on the click.
- [ ] **Dropout (seed 1, 84 BPM, drill VX9):** all lanes on. Set **Feel: Dropout** to Often and **Feel: Dropout seed** to 0, then play 16 bars from the start.
  - **Pass:** bars 4 and 14 are bass alone. Comp and drums stop cleanly on those bar lines and come back in on the next (the comp on its early push). Stop and play again: the same bars rest.
  - **Then:** seed 1 (different bars: 2, 4 and 12 in the first 16), then Rare (seed 0 rests bars 4 and 14 there too). Dropout starts Off, so the other drills are unaffected.
  - **Listen for:** rests now lean on the last bar of a 4-bar phrase (bars 4, 8, 12, 16), less often bar 2, rarely bars 1 and 3. Does each rest feel like a breath, or like a glitch?

## 7. Jam (the point)

- [ ] Pick a favourite seed and improvise over it for 10 minutes. Try switching seeds between phrases.

## 8. The receipt

One dated line per item. Save it as `E:\AI-Setup\research\in-flight\fl-jam-bridge-2026-09-14\morning-drills-receipt.md`.

- [ ] Tick probe: First tick = ?, Largest gap = ?, project PPQ = ?
- [ ] Description after compile (6 patterns, or fallback), and the folder spelling that worked.
- [ ] Does Reload pick up an edited `arsenal_patterns.py` without restarting FL? (VX1)
- [ ] Kick against the metronome over 32 bars: on it, early or late? Try PPQ 96 and 960. (VX3)
- [ ] Empty FL pattern in pattern mode: does FL loop after 1 bar, and did Keep counting still play all 8 bars? (VX5)
- [ ] Did the kick ever sit off the click after a loop wrap or a seek, and did it stay off until Stop? (VX5; it should come back on FL's next bar line at the latest)
- [ ] While playing, jump back to the loop top from beat 4 of its last bar: any stacked burst of notes, and did the loop's first kick sound? (VX5)
- [ ] VX5 decides the clock defaults: note which Clock mode felt right in pattern mode and in song mode.
- [ ] Did outputs 1-4 each reach their instrument? (VX7)
- [ ] Mute mid-chord: stopped at once, or rang on?
- [ ] Any hanging notes after Stop, pause or Panic? Which seed and lane?
- [ ] Pause, switch, resume: new groove on FL's bar line?
- [ ] Dropout with seed 0: did bars 4 and 14 rest, cleanly, and do Rare and Often feel right for your playing? (VX9)
- [ ] **Your ears:** which seeds you'd keep, and what felt wrong. Candidates to judge:
  - the pocket bass under Eb neo-soul: does it lock with the kick? Its 7th now lands with the kick on the "and" of 3, and its note on the "and" of 4 is struck again on the 1, not tied.
  - the comp pushes and bass notes on the swung 16ths in Eb neo-soul now share the hat's tick: in the pocket, or too late?
  - the gospel bass in F to D: a half-step approach into each change, and a triplet run only into bar 5 (the drop) and bar 1. Enough motion, or too plain?
  - F to D's two-note comp shells: enough harmony under you, or too thin?
  - the house comp stabs (1, the "and" of 2, 4) over the offbeat bass in Gb real V7
  - comp and pad sit between Db3 and Gb4, around your left hand (F to D's shells between D3 and D4): mute them when you voice chords yourself?

## Not today

- **Live JSON file** (`E:\AI-Setup\arsenal\fl\vfx\generated\arsenal_live.json`, drill VX2): waits until first light works.
- **Linking a KeyLab knob to Pattern** (VX4): also waits.
- **Fallback with no VFX Script at all:** drag `E:\AI-Setup\state\arsenal\band\mid\<seed>\<seed>-<lane>.mid` onto each channel's piano roll. Shift skips the import dialog; leave Blend off. All six seeds' files there were re-exported on 2026-09-14 from the current band.py, and `show` and `export-mid` now warn if a stored seed set is older than the generator.
