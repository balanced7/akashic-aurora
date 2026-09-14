# Arsenal band: a VFX Script that plays Claude's patterns inside FL Studio

- **Status:** built 2026-09-14 overnight and tested against a mock of FL's `flvfx` module (`tests/test_arsenal_fl_vfx.py`). **Not yet run inside FL.** The drills below are the first session with Daniel.
- **What it is:** one VFX Script, living in Patcher, that loops Claude's bass, drums, comp and pad patterns on FL's own tick clock into Daniel's instruments (Kontakt, Addictive Drums 2, Serum 2, FPC...). A pattern change always lands on a bar line, so Daniel improvises straight through it.
- **Why VFX Script:** FL 2026 ships it, so there is nothing to download, no compiler and no loopback port ([fact-check C1](../../../research/in-flight/fl-jam-bridge-2026-09-14/fact-check.md)). It is the FL-native version of the plan's Option D.
- **Nothing here writes into FL or Documents.** The morning install below is Daniel's to do (or to approve), from the files in this folder.

## Files

| File | What it is | Goes where |
|---|---|---|
| `arsenal_band.py` | The VFX Script: a scheduler, bar-line switching, drum maps, swing, humanize, live file. ASCII only. | Pasted into a VFX Script instance in Patcher |
| `arsenal_patterns.py` | **Example** patterns module (the plan's "Grandeur lift" and "Lazy pocket" grooves). The jam engine generates the real one in the same format. | `[User Data Folder]\VFX Script\Python\arsenal_patterns.py` |
| `flvfx_mock.py` | A mock of FL's `flvfx` module, plus a CLI to check and rehearse patterns offline (`simulate` takes `--gaps`, `--dropout`, `--clock` and `--loop-ticks`). It can call onTick with irregular gaps, hand back wrapper voices, and store knobs as float32 or 16-bit. Never installed. | Stays in the repo |
| `../../../tests/test_arsenal_fl_vfx.py` | Tests: 32 bars at 72 and 120 BPM, bar-line switches, stop, pause (also just past a loop wrap), a playhead nudged while paused, loop wraps with sparse, irregular and spiking onTick gaps (a late onTick across a known wrap at 72 and 120 BPM, PPQ 96 and 960), a seek back to the loop top from the loop's last beat, loops that are not whole bars, seeks and pauses with irregular gaps, the loop's last notes before a wrap, no note of zero length, the Pattern knob round trip, wrapper voices, dropout and the chord struck again after it, drum maps, live file. | Stays in the repo |

## Morning install (Daniel at the keyboard)

1. **Find the user data folder:** FL > Options > File settings > "User data folder". The default is `Documents\Image-Line`; this machine already has per-plugin folders there, such as `VFX Keyboard Splitter`.
2. **Create `[User Data Folder]\VFX Script\Python\`** if it isn't there, and copy in `arsenal_patterns.py` (the example, or the jam engine's generated one). FL 26.1 Beta 2 added imports from this folder (WhatsNew #21719). The exact folder spelling is unverified, so see drill VX1.
3. **Build the rack:**
   - Add a **Patcher** channel.
   - Inside Patcher, add **VFX Script**. FL files it under Patcher in both Generators and Effects.
   - Add the instruments inside the same Patcher, e.g. a Kontakt bass, Addictive Drums 2, a keys patch and a pad.
4. **Load the band:**
   - Open VFX Script's script tab.
   - Replace its text with the whole of `arsenal_band.py`, then compile.
   - The description should read "2 patterns from arsenal_patterns" and list the titles. If it says "fallback", the import folder is wrong; the band still plays a one-bar groove.
5. **Wire the outputs:**
   - Right-click the VFX Script icon in Patcher to activate its voice outputs. The manual says to "Right-click the plugin icon in Patcher to activate and link", and the Voice Cycler preset says "Extra voice outputs must be activated for use".
   - Connect output 1 to the bass, 2 to the drums, 3 to the comp and 4 to the pad.
   - Alternative: one VFX Script per instrument, with **Lane** set to that lane, each on output 1.
6. **Drum map:**
   - **AD2 default** if Addictive Drums 2 uses its factory map.
   - **GM** if AD2 has its GM map preset loaded, or for FPC's "Empty" preset.
   - **FPC** for other FPC kits.
7. **Press Play.** The **Clock** "Keep counting" (the default) works in pattern mode, even though an empty FL pattern may loop after one bar.
8. **Optional:** right-click **Pattern** and link it to a KeyLab knob (drill VX4), or automate it in the playlist.

## Controls

| Group | Control | Values | What it does |
|---|---|---|---|
| Band | Pattern | 0-63 | Index into `PATTERNS` (or the live playlist). Changes land on the next bar line. Turning back before the bar line cancels the change. Automatable. When the live file moves the knob, the band sets it a quarter step above the index, so FL reads back that exact pattern whether it rounds or truncates (tested for all 64). |
| Band | Switch at | Next bar / Next loop | Next loop waits for the top of the running pattern, which suits a song form. |
| Band | Lane | All lanes on outputs 1-4 / Bass / Drums / Comp / Pad | All: bass on output 1, drums on 2, comp on 3, pad on 4. A single lane plays on output 1. |
| Band | Clock | Keep counting / Follow song position | **Keep counting** starts bar 1 at Play from stop, on FL's bar grid (Play from mid-bar joins bar 1 at that beat), counts on through FL's whole-bar loop wraps, and resumes after pause. After a seek or jump, or a wrap of a loop that isn't whole bars, it releases what rings and re-anchors to FL's bar lines, counting on from there. **Follow song position** locks pattern bars to FL's song bars and releases everything when FL loops or jumps. In both, a Pattern change, Reload or live-file change made while paused lands on the first bar line after Play. |
| Feel | Swing | 0-1 | Delays off-beats of the grid by `swing x grid / 3`. 1 = triplet (66.7%); 0.36 is about 56% swing. |
| Feel | Swing grid | 16th / 8th | Which off-beats move. Notes off the grid (triplets, laid-back snares) never move. |
| Feel | Humanize | 0-1 | Velocity varies by up to +/-20 at 1. Fixed per note per loop, so a take replays identically. |
| Feel | Drum map | GM / FPC / AD2 default (+ module maps) | See the drum maps section. |
| Feel | Dropout | Off / Rare / Often | Now and then a bar where every lane but bass rests, so the piano and bass have the room to themselves. Rare is about 1 bar in 11, Often about 1 in 5. Never two bars in a row, and most often the last bar of a 4-bar phrase. See the dropout section. |
| Feel | Dropout seed | 0-99 | Which bars drop out. The same seed drops the same bars on every take, and on every band instance. |
| Mute | Bass, Drums, Comp, Pad | on/off | Silences the lane immediately (releases its ringing notes). Automatable. |
| Patterns | Live file | on/off | Follow the JSON playlist at `LIVE_PATH`. |
| Patterns | Reload | momentary | Re-import `arsenal_patterns`; the new content lands on the next bar line. |
| Patterns | Panic | momentary | Release every note this band is playing. |
| Output | Bar pulse | 0/1 | An output controller: 1 for a 32nd note on every bar line. It can drive another plugin, or a MIDI Out CC for page sync later. |

## Timing rules the band guarantees (and the tests check)

- **Only ticks and PPQ are used, never tempo.** Notes land on `round(beat x PPQ)` ticks from the pattern anchor. FL tempo changes cannot shift a bar line.
- **Every tick of FL's clock is processed exactly once.** The manual says onTick runs every tick, but the band processes the whole window since the last onTick in every case: while playing, across a pause and resume (a gap of up to a beat), and across a loop wrap. The tests run with onTick every 1, 2 and 5 ticks, with irregular gaps up to 9 ticks, with sparse gaps up to 23, and once per 512-sample audio buffer at 72 and 120 BPM (1 or 2 ticks, and 2 or 3, at PPQ 96).
- **A loop wrap is measured, never guessed.** A gap can jump right over the tick where FL's loop wraps, so the ticks that really passed are the loop span minus how far the ticks fell. A fall counts as a wrap only when a span an exact earlier wrap showed explains it with a gap of at most a beat. With no span known (or when the known one doesn't fit), it counts only when a whole number of bars gives a gap no bigger than the largest FL has left lately; that span is then the known one. "Lately" means the last 32 gaps, and once there are 8 the second largest, so one stray jump can't widen it. No span is ever guessed on a beat or 16th grid, and any other fall is a seek.
- **Keep counting stays on FL's bars.** Across a whole-bar loop wrap it counts on by exactly the ticks that passed. On a seek, a jump, or a wrap of a loop that isn't whole bars, it releases what rings and re-anchors to FL's own bar lines (ticks modulo the bar, as at Play), then counts on from there. An off-bar wrap or a late onTick can't leave it off the click for good.
- **A late onTick at a wrap and a seek back to the loop top sound the same.** Say the known span gives a gap longer than FL has been leaving (but at most a beat). That could be one late onTick across the wrap, or a seek back to the loop top from inside the loop's last beat, and no tick count tells them apart. So the band counts the loop's last ticks without sounding them and plays from the loop top: the loop-top downbeat sounds, and a seek fires no stacked burst.
  - Tested with late onTicks of 15 to 50 ticks at PPQ 96, and 250 and 260 at PPQ 960, against steady gaps and 512-sample buffers at 72 and 120 BPM, in both Clock modes.
  - Also tested: seeks back to the loop top from 10 to 90 ticks before the end of 1-bar and 8-bar loops.
- **Follow song position plays both sides of a loop wrap.** FL may pass the last few ticks of its loop after the band's last onTick and then wrap. When that gap is no longer than FL has been leaving, the band plays those last ticks first, releases everything, then plays from the loop top up to where FL is, so the loop-top downbeat still sounds, one gap late at most, as every note does between onTicks. After a seek it plays from the beat line (or 16th line) FL has just passed. The loop end can only be placed when FL's loop starts on a beat line; a loop starting on an off-beat 16th loses its last few ticks, as before.
- **Bar lines stay on FL's bars.** Keep counting starts in step with FL's bar grid. Resuming after a pause continues exactly where the band paused. The first played onTick may report the playhead tick or the one after it (the presets disagree: Tutorial 3 uses `% n == 1`, Arpeggiator `== 0`), so the tick before is played too.
- **Pause is not Stop.** Paused with the playhead where it stopped, a Pattern change, Reload or live-file change waits for the first bar line after Play. After a Stop (playhead back to the start) or a move of the playhead, it applies at once and Play starts on it from bar 1.
  - **A pause just past a loop wrap still resumes in step.** If FL wrapped after the band's last onTick and then paused a few ticks past the loop top, Play continues the count, using the loop span an earlier wrap showed.
  - **Tick 0 always starts fresh.** A pause exactly on the loop top can't be told from a Stop, so Play from there starts at bar 1. Once FL has reported tick 0 while stopped, the band never treats Play as a resume across a wrap either, so a Stop in the last beat of a loop still starts at bar 1.
  - **A nudged playhead is skipped, not played at once.** If the playhead moves forward less than a beat while paused, Play continues from there in step, but the notes FL skipped over are not fired all at once. Only the last few ticks, as many as a normal onTick gap, sound.
- **Switches happen only on bar lines** of the running pattern. A different pattern starts from its top. A new version of the *same* pattern (same `id` and length) keeps its place in the loop, so a live edit continues from bar 3 into the new bar 4.
  - **No blip before a switch:** a comp or pad push into a bar line where a switch or Reload is already waiting is skipped, because the switch would cut it a moment later. A knob turned after the push has started still cuts it on the bar line.
- **Every note-on gets exactly one note-off.** The band sets `voice.length`, so FL's own countdown is the safety net if the script errors. It also releases each voice itself:
  - at its end
  - on Stop or pause
  - on an FL seek or jump (both Clock modes), and on a loop wrap (Follow song position)
  - on a pattern switch
  - on a lane, mute or drum-map change
  - on a dropout bar line (every lane but bass)
  - on Panic
  - when the same pitch retriggers on the same output

  It releases a voice only while FL still lists it in `vfx.context.voices`, and only once. FL may hand back wrapper objects rather than the voices the band triggered. If so, the band finds its voice from its own records, by note and output: it never has two voices of one pitch sounding on one output.
- **No note of zero length.** When one onTick covers more ticks than a note lasts, or a switch, wrap or rest bar would cut a note started in that same onTick, its release waits for the next onTick. Tested with sparse gaps and gaps of 23 ticks, in both Clock modes, with wrapper voices.
  - **Two notes of one pitch in one onTick** would start at the same moment. If the later one is no louder, one voice plays through to its end. If it is louder, such as a backbeat snare after its ghost, the quieter one is cut at once so the louder hit sounds. That is the one case where a note still gets no length.
- **Controls are read about 24 times per beat,** not every tick. At PPQ 960 that avoids thousands of calls a second in FL's audio path.

## Pattern delivery

### Baked module (always works)

```python
# [User Data Folder]\VFX Script\Python\arsenal_patterns.py   (ASCII)
VERSION = 1
PATTERNS = [ {pattern set}, ... ]      # index = the Pattern knob, at most 64
LIVE_PATH = None                        # or r"C:\Users\L5\...\arsenal_live.json"
DRUM_MAPS = {}                          # optional: {"My kit": {36: 36, 38: 40}}; notes not listed are dropped
```

Each pattern set is the shared version 1 contract: `version`, `id`, `title`, `key`, `bpm_hint`, `meter`, `length_beats` (whole bars), `chords`, and `lanes.{bass,drums,comp,pad}.notes[{beat, len, note, vel}]`.

- The band is strict: a set that breaks the contract becomes a silent "INVALID" bar at its index, so the other indexes don't shift.
- The rules: note 0-127, vel 1-127, len > 0, and a finite beat. A beat outside the loop wraps, so -0.25 is a push into bar 1. Lanes other than the four are refused.

### Live playlist (only if FL allows file I/O from VFX Script; drill VX2)

```json
{"version": 1, "rev": 7, "current": 0, "patterns": [ {pattern set}, ... ]}
```

- **When it's read:** once per bar, one beat before the bar line, and only if the file's mtime or size changed. A change therefore lands on the very next bar line.
- **Failure handling:** a missing, unreadable or half-written file keeps the last good playlist, and the band logs the problem once.
- **What a change does:** a new `rev` or `current` switches to `current`, and the Pattern knob moves to show it. Use either Pattern automation or the file's `current`, not both.
- **For the engine:** write the file atomically (write a temp file, then `os.replace`). A bare pattern set, or a bare list of them, is also accepted.

## Dropout

A dropout bar is a bar where drums, comp and pad rest and only the bass plays. It is a small taste of tension and contrast: space for the piano, then the band comes back in.

- **Which bars:** set by the Dropout seed and the bar's number. Bars count from where the pattern started: Play from stop in Keep counting, song bar 1 in Follow song position, or a switch to a different pattern. An edit of the same pattern keeps the count. A take replays exactly, and several band instances (one per lane) on the same seed rest on the same bars.
- **Never:** on the bar the count starts from (the first bar after Play in Keep counting), on a pattern switch bar, or two bars in a row.
- **Phrase ends first:** a rest in the middle of a phrase can sound like a glitch, so the roll leans on the last bar of each 4-bar phrase (bars 4, 8, 12... counted from where the pattern started), then on its 2nd bar. Over 100 seeds and 64 bars, Often rests bars 1/2/3/4 of a phrase 103/312/199/736 times, and Rare 56/113/60/339.
- **On the bar line:** the choice is made on the bar line and holds for the whole bar, so turning Dropout or the seed mid-bar changes the next bar. Anything outside the bass still ringing, such as a pad held over the line, is released right there.
- **Pushes:** a note starting in the last 8th of a bar and ringing over the bar line belongs to the next bar. A push into a rest bar rests. A push out of a rest bar plays, so the band comes back in on its anticipation.
- **Held chords come back:** on the bar line after a rest bar, any comp or pad note that would still be ringing is struck again for what is left of it. That covers a pad cut on the rest bar's line and a chord that started inside the rest bar. A push over that bar line has already played, so it is not struck twice.
- **The engine matches:** `py -m arsenal.band make --dropout P` bakes rest bars into a pattern by the same push and restrike rules.
- **Follow song position:** the same song bars rest on every pass of an FL loop.
- **Safe with transport moves:** a pause inside a rest bar resumes resting, and bass is never touched.

## Drum maps

Patterns carry General MIDI drum notes (36 kick, 38 snare, 42 closed hat, 46 open hat, 49 crash, 51 ride, 37 side stick).

- **GM:** unchanged. Use it for FPC's *Empty* preset (its pads "are already assigned to the appropriate General MIDI keys", per IL's FPC manual) and for AD2 with its GM map preset.
- **FPC:** GM passes through. Rarer pieces fold onto the core kit: 35→36, 40→38, 44→42, 52/55/57→49, 53/59→51.
- **AD2 default:** the factory Addictive Drums 2 keymap, which is **not GM**. It was decoded from XLN's `Addictive Drums 2 Keymap.pdf` (dated June 2, 2021) in `Documents\Addictive Drums 2\App\ADBV0002\Manuals`. GM notes with no sensible piece are dropped.

| GM | AD2 key | AD2 piece |
|---|---|---|
| 35, 36 | 36 | Kick |
| 37 | 42 | Snare SideStick |
| 38, 40 | 38 | Snare Open Hit |
| 39 (clap) | 37 | Snare Rimshot |
| 42 | 49 | HiHat Closed 1 Tip |
| 44 | 48 | HiHat Pedal Closed |
| 46 | 55 | HiHat Open B |
| 41 / 43, 45 / 47, 48 / 50 | 65 / 67 / 69 / 71 | Tom 4 / 3 / 2 / 1 Open Hit |
| 49 / 57 | 77 / 79 | Cymbal 1 / 2 Hit |
| 52 / 55 | 81 / 89 | Cymbal 3 / 4 Hit (china and splash are kit-dependent) |
| 51 / 53 / 59 | 60 / 61 / 84 | Ride 1 Tip / Ride 1 Bell / Ride 2 Tip |

## Drills (each needs FL; write a dated receipt)

| # | Question | How | Pass |
|---|---|---|---|
| VX0 | First light | Install steps 1-7, example module, Play | Both example grooves sound; description lists 2 patterns |
| VX1 | Import folder and reload | Edit `arsenal_patterns.py`, tick Reload; then try recompiling | New notes on the next bar line without restarting FL |
| VX2 | File I/O from VFX Script | Set `LIVE_PATH`, tick Live file, edit the JSON while playing; set `current` to 0, 1, 62 and 63 in turn (a playlist that long, or as many as you have) | Switch on the next bar; no audio dropout on reads; the Pattern knob shows the file's exact index and the band stays on it (not one lower) |
| VX3 | Timing | Kick on output 2 vs FL metronome, PPQ 96 and 960, 32 bars; then pause mid-bar with the KeyLab Play button and resume. Note the largest onTick gap (the morning-drills probe) | Kick on the click, steady, and still on the click after resuming; note whether `ticks` starts at 0 or 1 and whether gaps are ever above 1 |
| VX4 | KeyLab knob to Pattern | Link to controller while the Arturia script owns the port | Knob selects patterns; landing on bar lines |
| VX5 | Transport edges | Pattern mode with an empty pattern (does FL loop 1 bar?), pause/resume, pause mid-bar then turn Pattern or tick Reload then resume, pause right after the loop top then resume, Stop in the last beat of the loop then Play, pause and nudge the playhead a little ahead then Play, Play with the playhead parked mid-bar, Stop mid-note, seek (including back to just past a bar line while playing, and back to the loop top from its last beat), both Clock modes; a 1-bar FL loop for 64 bars in each Clock mode with the audio buffer at its largest; a 1.5-bar song loop in Keep counting | No stuck notes; Keep counting plays all 4 bars and is still on the click after 64 wraps, after the pause at the loop top and after every seek; Stop then Play starts at bar 1; neither the nudge nor the seek to the loop top plays a burst of notes; Follow song position hits the kick on every loop top and after each seek, and the hat just before each loop top still sounds; every switch and downbeat on FL's bar line. Note what `ticks` reads while stopped and paused. **The largest gap and any slip decide the clock defaults** (see Still unverified) |
| VX6 | Drum maps | AD2 factory map and GM map preset; FPC Empty and default kit | Each GM piece hits the right drum |
| VX7 | Four outputs | Activate outputs 1-4, Lane = All | Each lane reaches its own instrument |
| VX8 | Safety net | Force an error mid-note (e.g. a syntax slip, recompile) | FL's `length` countdown still ends the notes |
| VX9 | Dropout | Lane = All, Dropout Often, seed 0, 16 bars while Daniel plays; then seed 1; then two instances (Lane Bass and Lane Drums) on the same seed; turn Pattern so the switch lands on a bar that rested before; then Rare; also a pad patch with a long release and a Mute toggled during a rest bar | Now and then a bar of bass alone, never two in a row; the pad stops cleanly on the bar line, no stuck notes; the band comes back in on its push, and a chord held over the rest bar is struck again on the bar after; seed 1 rests on different bars and seed 0 again repeats the first take; both instances rest together; the switch bar plays in full. Daniel's call: do Rare and Often feel right for his playing? |

## Where the API comes from

Read-only on 2026-09-14. Every name the band uses appears in FL's own factory presets. `test_mock_names_are_attested_by_fl_factory_presets` re-checks this whenever the presets are on disk.

- **Factory presets:** `C:\Program Files\Image-Line\FL Studio 2026\Data\Patches\Plugin presets\Effects\VFX Script\`
  - `Tutorial Scripts\Tutorial 3 - Voice Generation.fst`: builds `vfx.Voice()` in `onTick` and triggers it at `ticks % step == 1`. Sets `length` in ticks, so FL releases the voice automatically.
  - `Tutorial Scripts\Tutorial 1 - Simple Voice Passthrough.fst`, `Default.fst`: `onTriggerVoice`, `onReleaseVoice`, `vfx.context.voices`, `copyFrom`, `release`.
  - `Tutorial Scripts\Tutorial 4 - Control Signal Generation.fst`: `addGroup` and `'Group: Name'` addressing, `addInputCombo(name, list, index)`, `vfx.addOutputController` and `setOutputController`.
  - `Random Sequencer.fst`: generates while `isPlaying`, resets when stopped at `ticks == 0`, and uses a momentary checkbox via `setNormalizedValue(name, 0)`.
  - `X BinaryBorn\Generators\Random Notes.fst`: releases every `vfx.context.voices` entry when not playing.
  - `X BinaryBorn\Voice Utils\Voice Output Switch.fst` and `Voice Cycler.fst`: `voice.output` (0-15); "Extra voice outputs must be activated for use".
  - `X BinaryBorn\Timer\Timer (BPM).fst`: `vfx.context.tempo`, and treats falling ticks as a transport jump.
  - `X BinaryBorn\Voice Utils\Voice Construct.fst`: a fresh `vfx.Voice()` released by hand.
- **Changelog:** `C:\Program Files\Image-Line\FL Studio 2026\WhatsNew.rtf`, entries #21719, #21567, #19518, #20438, #19754, #19592, #19511 and #21906.
- **Embedded Python:** `C:\Program Files\Image-Line\FL Studio 2026\Shared\Python\python312.zip` contains `json`, `os` and `importlib`, so the live file can work if the sandbox allows `open()`.
- **Manual:** [IL manual: VFX Script](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/VFX%20Script.htm) documents the callbacks, `vfx.context` (ticks, PPQ, isPlaying, voices, form), the Voice fields (note, finePitch, velocity, pan, length, output, fcut, fres), and the ScriptDialog methods. It does not mention `tempo`, the Python folder, or file I/O.
- **FPC:** [IL manual: FPC](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FPC.htm) is the source for the Empty preset being GM.

## Offline rehearsal

```
py arsenal/fl/vfx/flvfx_mock.py check arsenal/fl/vfx/arsenal_patterns.py
py arsenal/fl/vfx/flvfx_mock.py check state/arsenal/jam/live.json
py arsenal/fl/vfx/flvfx_mock.py simulate arsenal/fl/vfx/arsenal_patterns.py --pattern 1 --bars 2 --bpm 84 --drum-map "AD2 default"
py arsenal/fl/vfx/flvfx_mock.py simulate arsenal/fl/vfx/generated/arsenal_patterns.py --pattern 1 --bars 16 --bpm 84 --gaps 1,4,2,7 --dropout Often --dropout-seed 0
py arsenal/fl/vfx/flvfx_mock.py simulate arsenal/fl/vfx/generated/arsenal_patterns.py --pattern 3 --bars 8 --gaps buffer:1024 --clock "Follow song position" --loop-ticks 768
py -m pytest tests/test_arsenal_fl_vfx.py -q
```

## Still unverified

- Whether the band is the only Python in the script tab, or whether FL can also load it by file through the external-editor support (#19518).
- Whether a VFX Script can `import` a module that itself does `import flvfx`. The band avoids depending on this.
- FL's behaviour on releasing an already-released voice. The band never does it, and the mock flags it.
- Whether `vfx.context.voices` returns the voice objects the script triggered or wrappers around them. The band works either way (tested with both), but if FL kept released voices listed during their release tail, the band's stop-and-panic sweep would release them again.
- How FL stores an int knob's normalized value and reads it back. The band's quarter-step value round-trips under rounding or truncation, from a float, a float32 or a 16-bit step. It would not survive 7-bit (MIDI CC) storage read back by truncation; drill VX2 checks.
- How irregular FL's onTick gaps are, and so the clock defaults. **Drill VX5 decides them:** which Clock mode is the default, how many recent gaps set the bounds, and whether a late onTick at a wrap should sound the loop's last ticks. Until then the band takes the conservative reading:
  - Keep counting counts through a loop only when it is whole bars (pattern loops, bar-snapped song loops). A loop region that isn't whole bars sends FL back to its bar 1 mid-bar, and the band follows FL's bars there, releasing what rings at each wrap.
  - A gap longer than FL has been leaving at a wrap drops the loop's last ticks, even when it really was one late onTick.
  - A gap over a beat at a wrap is read as a seek, so the loop-top downbeat sounds only if FL's next onTick comes within the loose bound of it.
  - A forward seek of under a beat while playing looks exactly like one late onTick, so it plays the skipped ticks at once.
- Whether onTick really fires on every tick, what `ticks` reads while paused (the band accepts the pause tick up to a beat later), and whether Stop always sends `ticks` back to 0 (a Stop that leaves the playhead within a beat of the pause point would count as a pause). A resume across a loop wrap also relies on FL reporting tick 0 on stopped onTicks after a Stop; if FL reports something else there, a Stop in a loop's last beat followed by Play from tick 1 could continue the count instead of starting at bar 1. Drills VX3 and VX5 settle these.
- Changing a voice's `length` after `trigger()` is never needed: when one onTick holds two notes of one pitch, the voice keeps the first note's length for FL's countdown, so FL may end it before the later note's end.
- FPC's *default* kit pad notes. Only the Empty preset is documented as GM.
- Whether `[User Data Folder]\VFX Script\Python` is the exact on-disk spelling, and whether edits need a recompile or an FL restart.
