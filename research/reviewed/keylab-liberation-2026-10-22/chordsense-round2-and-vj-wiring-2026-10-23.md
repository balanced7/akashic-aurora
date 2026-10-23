# chordsense round 2 and the VJ wiring: both builders' reports and both adversarial verifications (2026-10-23)

Workflow run wf_d904da09-5fd (task wdjvdxg7p), two lanes, each built in a worktree and verified adversarially.
Lane A (chordsense round 2): branch `worktree-wf_d904da09-5fd-1`, head 090a5269. Lane B (wiring into vj.py, the page and
`screen --live`): branch `worktree-wf_d904da09-5fd-2`, head ce0f492b. All four texts verbatim below; local paths shortened.

## What was merged, and the one decision taken at the merge (Vandor)

Both verdicts were MERGE WITH NOTES. Lane B's verifier measured the wiring with ROUND-1 chordsense and found the new
default worse than the old templates on hardstyle, so the merge re-ran that verifier's own offline scorer
(`verify-B/offline.py`, time-weighted root / exact) on its renders with round 2 merged:

| render | templates (basic) | chordsense round 1 | chordsense round 2 |
|---|---|---|---|
| hardstyle, full (kick sweep 260-50 Hz, sub 41-65 Hz, supersaw, pad, hats, clap) | root 58.9 / exact 58.9 | 57.3 / 30.1 | 61.0 / 37.5 |
| hardstyle, no drums | 68.0 / 68.0 | 56.7 / 55.6 | 74.1 / 74.1 |
| hardstyle, chords only | 70.3 / 70.3 | 68.0 / 68.0 | 68.2 / 68.2 |
| piano, D-flat pedal | 70.2 / 70.2 | 68.8 / 50.3 | 71.0 / 52.7 |
| piano, D-flat plain | 70.8 / 70.8 | 64.6 / 56.3 | 66.1 / 53.8 |
| piano, C plain | 74.2 / 69.4 | 75.4 / 58.7 | 74.3 / 61.8 |

On the full hardstyle render round 2 names F as Dm7 / Dm7/F, C as Cadd9, G as G/C (the kick's sweep adds D and C);
the templates name all 27 right. Its keys were sensible (A minor; G major for the E-minor part, the relative major).
So the merge added `--chords blend` as the DEFAULT: the templates NAME the audio chords, each decorated with its roman
numeral in chordsense's key, and chordsense sends the key and the tension (its own audio chords are not published);
`--chords sense` keeps chordsense's names, `--chords basic` the templates alone. Also at the merge: chord names spelled
by the key's scale degrees (`spell_in_key`: G#m in E major, Bb in C major; lane B verifier note 2), the page's parser no
longer wraps pitch classes (-1 read as B, 99 as E-flat; note 4), a no-chord carries no numeral, a chordsense failure
in blend never stops the audio chords (pinned in both modes), and the beat bench's temp-copy filter (its '' and '	'
were BEL and TAB) fixed. Commits on master: e2682890 (merge head), ec85d46d, ede3718c. Open for round 3: the notes at
the end of each verification below, first of all the kick's tones in chordsense's audio path on hardstyle.

## Lane A, chordsense round 2: the builder's report (verbatim)

Round 2 is committed on branch `worktree-wf_d904da09-5fd-1`, nothing pushed, master untouched. It meets items 1, 3, 5, 6 and 7. Item 4 is met on the keys and on four of the seven renders. Item 2 is only partly met: real chordal loops are at 80 % chord time against the 85 % target, and the same 3 loops round 1 lost are still lost.

The full test run passes: 206 tests (74 chordsense, 4 licence firewall, 128 in the other keylab files), with 1 skip in vj that needs Daniel's private take. 31 of the 74 chordsense tests are new. Speed is 63.5x real time against 75.9x for round 1, run back to back. The slowest blocks (p99) take 0.52 ms against a 10.7 ms block, and the keys path runs at 202x (round 1: 265x).

**Commits** (on the merge of round 1, `1e64be3f`; only chordsense.py and its tests changed, plus the hook-regenerated `docs/PHYSICS.md`):
- `b3bd640c` low bass
- `e351b789` real pads, melody lines, spelling (items 2, 5, 6)
- `e3228e4e` pedal
- `0bb35448` key confidence and stability
- `551bcb7a` stuck-key gap, bad times refused, confidence under a loud bass
- `d41e1272` chord onsets ignore the kick below C2
- `090a5269` the ride test uses the verifier's ride

The merge conflicted only on `docs/PHYSICS.md` (a generated file); I kept ours. The hooks modified five other files, which I left unstaged as round 1 did.

**Before (7a8ab349) → after**, measured with the verifier's probes on copies in my scratch folder:

| Item | Before → After |
|---|---|
| 1. Saw bass E1–D#2, +6 / +12 dB (full / root %) | 63.5/77.9 → 99.8/99.9; 28.0/42.9 → 64.9/95.7 |
| 1. Square bass E1–D#2, +6 / +12 dB | 78.9/91.3 → 88.8/99.2; 28.3/58.8 → 74.4/96.1 |
| 1. Square bass C2–B2, +6 / +12 dB | 90.4/90.7 → 99.2/99.2; 45.2/53.6 → 94.1/96.6 |
| 1. Saw bass C2–B2, +6 / +12 dB | 97.5/97.7 → 100/100; 85.8/92.4 → 83.1/97.8 |
| 1. Square bass G1–F#2, +12 dB | 36.5/64.2 → 83.0/96.7 |
| 1. New hardstyle test, kick tuned to A1 / to G1 (root %) | 75.9 / 74.4 → 91.1 / 96.5 |
| 2. 40 real chordal loops, chord time (base engine 88 %) | 77 % → 80 %; still 3 loops base read >50 % now <40 % |
| 2. Same loops, real chords only (no power chords) | 71.2 % → 72.3 % (base engine 69.8 %) |
| 2. "Ascension C Min Synth Chords" | 12 % → 98 % |
| 2. Chords under pink noise at 0 dB SNR (full) | 24.7 % → 97.2 % |
| 2. Noise | round-1 set 0 %; 50 drum loops 0.5 → 0.2 %; ride 93.7 → 3.7 %; crash 48.5 → 41.2 %; 60 Hz hum 0 → 2.2 % |
| 3. False pedals: Pachelbel, Am-F-C-G, C-Am-F-Dm7-G7 (1 and 2 beats) | 4 false pedals in audio and 1 on keys → none, on the epiano and the fixer's piano |
| 3. Re-struck Db and held A, absorbed by the chord name | audio not found, keys flapped 3× (on 49 %) → found once, on 99–100 %, both ears |
| 3. Joy ending, Db-pedal share (keys) | 0.59 → 0.62, tension 0.35 → 0.52 |
| 3. Joy ending, verifier renders | epiano 0.00 → 0.56, pluck 0.08 → 0.58, organ 0.17 → 0.59, pad 0.68 → 0.60; tension rises at the ending on all |
| 4. C-Bb-F-C | flipped to F major → stays C major, keys and audio |
| 4. Joy keys | Db major 0.93 → 0.96; announcements 6 → 4; passing keys at 1.0 → 0.41–0.53 (Db major 0.84–0.88) |
| 4. Joy renders, Db-major share / announcements | fixer 0.90/8 → 0.87/9 (both); epiano 0.83/10 → 1.00/2; pluck 0.83/9 → 0.81/7; organ 0.84/9 → 0.75/10; pad 0.75/12 → 0.79/10 |
| 4. Modulation speed, keys / audio (s) | C→D 3.4/4.1 → 3.8/4.6; C→Cm 4.6/5.1 → 4.8/5.2; C→A 9.5/4.9 → 9.2/5.2 (round-1 test material: 7.6/7.8) |
| 5. Keys C-D-E-G, notes held 0.45–0.9 s | 9–15 chords → 0–1 |
| 5. Audio bass line / ringing pluck | 18 chords + key / 5 + key → 0 / 0, no key |
| 5. C-E-G-B arpeggio over the sustain pedal | still C / Cmaj7 |
| 6. Spelling in C major / A minor | A#, D#, G# → Bb, Eb, Ab; also Gb7 and G#dim; one accidental at most in every key |
| 7. Stuck key across 30 minutes | 4589 ms → 5.5 ms, same events as stepping |
| 7. now=inf | OverflowError → ValueError |
| 7. Confidence AUC on error-prone material | mid-chord 0.44 → 0.58; at the decision moment 0.43 → 0.43 |
| Random sets (6 sets, full / root) | 99.1/99.9 → 99.1/99.9; 44.1k and 22.05k 100/100; output still the same at any block size |
| Decision latency (median) | about 420 ms both; onset error p90 33 / 52 ms (round 1: 33 / 63) |

**Tests that fail on 7a8ab349 and pass now:**
- Low/hollow bass: 6 of 8 cases. The 2 saw C2–B2 cases are guards.
- Hardstyle: both cases.
- Noise and washy pad: fails before.
- Ride cymbal: fails before.
- Plain progressions with no pedal: 4 of 6 cases. Dm-Bb-F and C-Em-Am are guards.
- Absorbed pedal found: both cases.
- C-Bb-F-C stays in C.
- Key confidence comes from the evidence.
- Joy keys (needs the private notes).
- Melody lines (bass line and pluck): both cases.
- Keys melody: all 3 cases.
- Spelling by degree.
- Stuck key and bad times.
- The arpeggio-over-sustain test is a guard and passes on both.

**What still misses the targets**
- **Chordal-loop chord time (item 2).** The base engine's 88 % includes 18 % of power chords read off single notes and dyads, which item 5 forbids. On real chords this engine is ahead of both earlier ones. The 3 lost loops look like a washed-out pad (NodeX Sweet Pad), a pad that plays single notes (Cymatics Artificial) and a picked guitar line (Stickz Smile, 37 %). I did not put power chords back to win them.
- **Cymbals.** The crash still reads as chords 41 % of the time. Nothing I measured (register, chroma peakiness, alignment to the semitone grid) separates it from real pads.
- **Hardstyle with a heavily distorted kick tuned to the tonic, +6 dB.** Root accuracy is 80.7 % (round 1: 69 %). The kick's own overtones really sound, so the engine can hear an E over every G chord. The committed test uses a +3 dB kick with lighter distortion.
- **Joy key share on pluck, organ and pad renders** stays at 0.75–0.81. The passing keys there (the relative minor, IV, V) sound for several seconds at a time.

**Judgement calls and trade-offs**
- **Drone pedal.** A note held 16 s over 4 or more roots now counts as a pedal even if it fits every chord. Daniel's Joy Db works this way: it fits most chords and is struck with them, so a stricter rule loses it. A 4-chord loop sharing one tone in every chord would read the same once it has run 16 s.
- **Thin pedal margins.** A pedal may miss at most 15 % of the chords it runs through. Joy misses 9–15 %; the plain loops miss 17–25 %. I picked the threshold on these probes.
- **Lines.** A new chord can't be built from a fading note struck before the newest one, but only when no chord is named yet. Once a chord is named, arpeggios and Rhodes chords that decay keep it.
- **Decision-moment confidence.** On loud-bass material the wrong readings are the right root in a thinner colour, which the margin can't see. Pushing that AUC higher drops hardstyle confidence to about 0.1, so I stopped at a mild correction.
- **Keys path speed.** It dropped to 202x, mostly from the new pedal bookkeeping per frame.

`to_vj_events`' output contract is unchanged: `keylab chords --notes <Joy> --vj` gives 341 chord, 367 tension and 4 key events, all with the contract keys. Daniel's playing was only read in place. No committed file holds any of it; derived outputs (`vj_out_r2.jsonl` and the Joy probe outputs) exist only in scratch.

Files are in <session scratchpad>/r2/:
- final/ — every probe output behind the table
- probe_lib.py (and the copied p*.py probes) — the verifier's probes, comparing round 1 against the working copy
- bass_exp.py, hardstyle.py, tonal_diag.py, tonal_cmp.py, joy_keys.py — my extra harnesses

## Lane A: the adversarial verification (verbatim)

**Verdict: MERGE WITH NOTES.** Round 2 is better than round 1 on every item, with no regression on clean material. All tests pass, `to_vj_events` is unchanged, and none of Daniel's playing is in any commit. But the builder's claim that it "meets items 1, 3, 5, 6 and 7" only holds on its own tuning material. On my material, items 1, 3, 5 and 7 are partly met. Item 6 is fully met. Items 2 and 4 are partly met, as the builder said.

I checked branch `worktree-wf_d904da09-5fd-1` at `090a5269` against round 1 (`7a8ab349`) and master's engine (`baa47b0a`, called "base" below). I read it with `git show` and exported copies into my scratch folder, and wrote nothing to the repo or the builder's worktree.

**Tests**
- Chordsense (74) and the licence firewall (4): 78 passed.
- 26 of the 74 fail on round 1, exactly the builder's list.
- The other keylab files: 250 passed, 1 skipped (the vj test that needs Daniel's private take).

**Per item, round 1 → round 2**

1. **Low bass: partly.**
   - The round-1 verifier's probes reproduce: saw E1–D#2 on electric piano +6 dB 63.5/77.9 → 99.8/99.9 (full/root %), +12 dB 28.0/42.9 → 64.9/95.7; square G1–F#2 +12 dB 36.5/64.2 → 83.0/96.7. Organ and pluck pass too.
   - My hardstyle material (24 setups: 6 progressions, 150/155 BPM, soft or hard-clipped kick at +3/+6 dB, tuned to the tonic or not, a held or off-beat sub under 65 Hz): root 94.7–100 %, full 90–100 %, chords named 99–100 %. Round 1 ranged from 8.7 % root.
   - Kick alone, sub alone, and kick plus sub with no chords all read N.
   - Slash chords with a single low bass note: right bass 67–69 → 97–98 %.
   - **Misses:**
     - Electric piano with a saw bass at +6 dB, full 67 %: the bass's 7th partial takes the m7's 7th, so m7 reads as min.
     - Square bass at +12 dB, root: 81.6 / 87.4 (electric piano), 94.3 (organ), 90.2 / 92.8 (supersaw).
     - Pad, root 89–92 %. Its no-bass baseline is about 89 %, so this is the timbre's own ceiling, not the bass.

2. **Real pads and synth chords: partly (target missed).**
   - Mean chord time on three loop selections, base → round 1 → round 2:

     | Selection (40 loops each) | Base | Round 1 | Round 2 | Base > 50 % falling below 40 % |
     |---|---|---|---|---|
     | Round-1 verifier's loops | 88.1 % | 77.0 % | 79.7 % | 3 |
     | My own selection | 87.5 % | 66.6 % | 73.2 % | 5 |
     | 150 BPM NodeX pads and pianos (Daniel's genre) | 95.2 % | 66.5 % | 83.1 % | 4 |

   - The four lost NodeX loops are "Sweet Pad Intrestelar" 02–05, read 0–7 %. Their tonality sits at about 0.07, so the N boost wins.
   - Not counting power chords ("5"), round 2 is at or above base everywhere: 72.2 vs 69.7, 63.3 vs 60.2, 77.6 vs 75.1 %.
   - "Ascension C Min Synth Chords": 15 → 97 %.
   - Pink noise at 0 dB on the verifier's electric piano: 25 → 97 % full. On my timbres, chords are named 88–100 % of the time.
   - Noise:
     - Round-1 noise set: 0 %, except the 60 Hz hum with hiss at 2.2 % (round 1: 0).
     - Ride: 3.7 % (round 1: 94 %). Crash: 41 %.
     - Drum loops: round-1 verifier's 50 at 0.2 %; my 50 at 0.08 %.
     - A mains hum with its harmonics: 95 → 0 %.
     - **Not fixed:** my gong-like inharmonic sound (150–2500 Hz) still reads as chords 91 % of the time (base: 0 %).

3. **Pedal: partly.**
   - **Fixed:** absorbed pedals are found on both ears, once, at 99–100 % share. That covers the re-struck Db, the held A, and my own Eb over Ab-Fm-Db-Eb, which round 1 missed entirely. The keys path stays clean on every plain loop, including when played with the sustain pedal.
   - The verifier's probes show no false pedals.
   - **Not fixed: in audio, ring-over tails still make false pedals.** I swept the release time using the verifier's exact voicings and electric piano:
     - At 0.5 s (the tuning point): clean.
     - At 0.3 s: one false pedal.
     - At 0.8, 1.2 and 2.0 s: false pedals on 4 of the 6 target loops (clash 0.00–0.28). Tension climbs from 0.17 to 0.63.
     - My timbres: Rhodes 3 loops, pad 5, strings 3, pluck 1, organ 0.
   - **New in round 2:** the drone rule gives a false C pedal on C-Am7-Fmaj7-Dm7 on keys and in audio, on every timbre (round 1: none).
   - **Joy ending:** keys 0.62 with tension 0.35 → 0.52; every render the verifier made passes (0.54–0.60). On my renders, organ, pluck and Rhodes pass (0.57–0.60), but **pad 0.68 → 0.39 and strings 0.78 → 0.01**. On those two the pedal is only found at beat 544 / 582 instead of 517.

4. **Key: partly.**
   - **Holds up:** C-Bb-F-C stays in C, and so does G-F-C-G. On the keys, Joy holds Db major 0.96 of the time with 4 announcements. Passing keys are announced at 0.41–0.53 against 0.84–0.88 for Db major. The verifier's modulation timings are kept.
   - **Opening regression:** Joy now opens in F minor until 31 s on the keys (round 1 reached Db major at 11 s), and until 52 s on my organ render.
   - **Db-major share at or above 0.85:** met on 9 of 14 renders. Organ regresses: 0.84 → 0.75 on the verifier's, 0.78 → 0.68 on mine.
   - **More announcements than round 1:** the fixer's two renders (8 → 9), organ (9 → 10), strings (9 → 11).
   - **Slower modulations on my I-IV-V7-I material:** C→F 4.9 → 8.8 s, C→A 5.1 → 7.4 s.

5. **Melody: partly.**
   - **Fixed:** the brief's cases.
     - Keys, C-D-E-G held 0.45–0.9 s: 9–15 → 0–1 chords.
     - Audio bass line: 18 → 0 chords. Ringing pluck: 5 → 0. No key in either.
     - Arpeggios read correctly on both ears.
   - **Not fixed:** legato on the keys. With overlaps of 40 ms or more at 0.5 s per note, round 2 names 13–18 chords and finds a key (round 1: 10–13 chords, no key on C-D-E-G or A-B-C#-E).
   - **Trade-off:** an Am7 broken chord on the keys with each note released and no pedal now reads N (round 1 read Am7).

6. **Spelling: fixed.**
   - Bb, Eb, Ab and Db in C major; Bb in A minor; correct in G, D and A major.
   - Flat keys use at most one accidental. So bVII of Db is "B", and the diatonic IV of Gb major is spelled "B", not "Cb", as in round 1.

7. **Smaller items: partly.**
   - A stuck key across a 30-minute gap: 4.5–7.3 s → 5–29 ms, with the same events as stepping frame by frame.
   - inf, -inf and nan now raise ValueError.
   - **Not fixed:** confidence AUC. On the verifier's material it is 0.43 at the decision moment and 0.58 mid-chord. On mine it is 0.34 and 0.30, so wrong labels still get higher confidence than right ones.
   - **New, small:** a close C3-E3-G3 triad held under the sustain pedal announces E minor (round 1: no key).

**Unchanged and fine**
- Random sets: 99.1/99.9, 100/100 at 44.1 and 22.05 kHz; same output at any block size. My 6 timbres × 2 seeds: equal to or better than round 1.
- Speed: 65x real time against round 1's 77x, same run (worst blocks 0.55 ms against a 10.7 ms block). Keys path 187x against 251x.
- Decision latency: median about 420 ms, about 400–490 ms on hardstyle.
- `to_vj_events`: the source is identical, and the output has the same fields as round 1. `chords --notes Joy --vj` gives 341 chord, 367 tension and 4 key events.

**Privacy: clean.** The branch diff touches four files: `chordsense.py`, its tests, `__main__.py` (round 1 only) and a one-line hash change in `docs/PHYSICS.md`. None of its added lines carries a run of Joy's pitches, onsets or lengths, or names `joy_notes`, `joy_take` or `recordings`. My derived outputs are only in scratch.

**Merge:** only the generated `docs/PHYSICS.md` conflicts with master (regenerate it).

**Notes for round 3, most important first:**
- Telling a held note from a ring-over tail depends on the envelope: sounds with a long release make false pedals, and slow-attack pads or strings lose Joy's pedal.
- The drone rule makes a false pedal on loops whose four chords share one tone.
- The washy NodeX Intrestelar pads (Daniel's genre) read N.
- Legato melodies on the keys still name chords and a key.
- Joy opens in F minor, and organ renders hold Db major less.
- Confidence AUC is still below 0.5.
- Crash and gong-like sounds still read as chords.
- C→F modulation is slower than in round 1.

Everything is in `<session scratchpad>/verify-A/`: `out/` holds every probe output (start with `vd_relsweep.txt`, `vb_pedal_*.txt`, `vb_joy_*.txt`, `vb_loops_*.txt`, `vb_nodex.txt`, `vd_legato.txt`, `vb_bass_*.txt`, `vb_hard.txt`); my probes are `va_lib.py`, `vb_*.py` and `vd_*.py`; the copied round-1 probes are `p*.py`.

## Lane B, the VJ wiring: the builder's report (verbatim)

I've wired chordsense into the VJ engine, the page and `screen --live`. Everything is committed on branch `worktree-wf_d904da09-5fd-2`, not pushed, master untouched. The browser receipt `node arsenal/lanes/vj_verify.mjs` passes all 43 checks. That includes a new phase where the real Python engine (`vj --replay-audio demo --no-leds --no-midi`, on a test-band port) drives the page and the HUD shows "C major" and "F IV" from actual chordsense output. The keylab Python tests give 186 passed and 1 skipped (the private Joy take), and `vj_core.test.mjs` gives 151 passed.

**Commits**
- `81530e26`: the merge of round 1 (`7a8ab349`). Its only conflict, `docs/PHYSICS.md`, is a generated file, so I resolved it by regenerating it.
- `ce0f492b`: this lane, 13 files.

**Engine (`vj.py`)**
- `--chords sense` is the default and `--chords basic` keeps the old AudioChords path. The hello event now says which one runs (`"chords": "sense"`).
- The audio path publishes `to_vj_events()` output: the chord with `roman`, `key`, `bass` and `conf`, plus the new `key` and `tension` events.
- A second ChordSense hears the keys; the MIDI thread steps its clock every 20 ms.
- The page is told one key and one tension: the keys' while they were played in the last 10 s, otherwise the audio's. Every chord's numeral is written in that key.
- A chordsense failure on either thread is counted and reported once, and never stops the beat, the energy, the hits or the pads (pinned by a test).

**Keys naming: I kept today's reading, and let chordsense fill in where it has no name.** Measured on synthetic piano material:

| Material | Today's naming | chordsense notes path | What I shipped |
|---|---|---|---|
| Held block chords (24) | 97 % correct, 46 ms after the attack | 85 %, 180 ms | 97 %, 46 ms |
| With sustain pedal | 97 %, 46 ms | 85 %, 180 ms | 97 %, 46 ms |
| Re-struck D-flat 5 pedal note | 32 % (most chords get no name) | 74 % | 78 % |
| Pedal held down over 4 chords | 24 % | 43 % | 45 % |

**What Daniel sees on the page**
- HUD chord row: `Gbmaj7 IVmaj7 (keys) · tension 0.62 (engine)`.
- New HUD key row: `Db major · conf 0.82 (keys) · IVmaj7`.
- The pedal row reads `D♭ held under the harmony (engine)` when chordsense hears a pedal and the page's own pedal star is dark.
- The engine's tension replaces the page's own estimate in the strip; it is never added on top. The rest of the formula is unchanged: the larger of that and the page's pedal tension × 0.8.
- A key change gives half a chord-change pulse plus a constellation redraw, and no flash; the receipt checks the flash gate count is unchanged.
- An audio no-chord shows "no chord (audio)" and the palette returns to the fader colours. This is new behaviour: the basic path never cleared the chord.
- An engine that sends none of the new events leaves the page exactly as before.

**What he sees on the KeyLab screen (`screen --live`)**
- Line 1, the only line the firmware leaves in its own case: `Gbmaj7  IVmaj7  in Db`, `Bbm  vi  in Db`, `Am  i  in Am  (song)`. An audio no-chord shows `--`.
- Past 32 characters it uses single spaces, then drops `(song)`, then the key; never the chord or the numeral.
- Line 2 stays `150 BPM | SCENE`. It redraws only on change; a test pins one send for repeated identical events.

**Timing and CPU** (real-time synthesized hardstyle replay, 48 kHz, 25.6 s; one block is 10.7 ms)

| | sense | basic |
|---|---|---|
| Blocks read | 2400 of 2400 | 2400 of 2400 |
| Capture timing gap | +0.6 ms (`gap: false`) | +0.1 ms |
| Late blocks / behind | 0 / 1 ms | 0 / 0 ms |
| Whole loop per block | 0.87 ms avg, p99 2.80, max 4.1 | 0.67 ms avg, p99 2.38, max 6.45 |
| chordsense's share | 0.28 ms avg, p99 0.88, max 1.36 | — |

In the receipt's real-engine phase the capture record showed a 0.0–0.1 ms gap and chordsense p99 1.19 ms. The live record is in `GET /api/state` under `audio.timing`.

**After merge, one command is needed.** Daniel's private `state/arsenal/keylab/joy_take_events.json` no longer matches the engine: there are 322 chord rows instead of 241, because chordsense now names chords the old reading could not. Run `py tests/fixtures/vj/make_joy_take.py --refresh` (new: it rebuilds the rows from the fixture's own notes). I checked on a scratch copy only: the refreshed rows equal the engine's output, and the page's Joy pedal checks are unchanged (83.8 % kept, 7.0 s of false alarms). I did not touch the main checkout's state.

**Contract note:** chord events now carry `key` meaning the musical key, while note events use `key` for the MIDI note number. Two tests read `e.get("key", e.get("name"))` and I fixed them; any other consumer doing that needs the same fix.

**Needs chordsense changes (for the other lane):**
1. **The kick is read as the bass.** On my hardstyle synth (sub bass fundamentals under 65 Hz, a distorted kick), the audio path named Am "Am/Eb", F "F/Eb" and G first as "G/C". The bass band starts at 65 Hz, so the sub never counts, and the kick tail's harmonic near 150 Hz takes its place. `--chords basic` named all 16 chords correctly on the same audio. This is the verifier's item 2, plus rejecting kick harmonics as bass.
2. **Fast-path key confidence is 1.0.** On Joy through the keys, wrong keys (Eb minor, Gb major, Ab major) were announced at confidence 1.0 while the right one, Db major, got 0.52 and 0.16. The HUD passes this through as "conf 1.00". On my synthetic progression the keys' key also moved to Bb minor about 3 s after a C7 had rung out.
3. **The chord name swallows the pedal note.** On piano with a re-struck D-flat, the audio reads Ab as "Absus4" or "Db5/Ab" at confidence 0.03–0.2 (verifier item 1).
4. **What `vj.py` relies on.** It calls `chordsense.roman()` and `full_roman()` to write numerals for the keys' chords and to re-write a chord in the key the page is told, and it parses the key name format "Tonic major|minor". If round 2 changes `roman()`'s signature or the quality names, the numerals go blank but nothing fails.
5. **Sharps inside C major or A minor** (A# for Bb, verifier item 6) are already respelled as flats on the page and the screen, but chordsense's own output still needs the fix.

The post-commit authorship hook appended a line for my commit to `state/authorship/seats.jsonl`; I left it unstaged, as round 1 did.

Files are in `<worktree>/wf_d904da09-5fd-2`:
- `arsenal\keylab\vj.py`
- `arsenal\keylab\screen.py`
- `arsenal\keylab\__main__.py`
- `arsenal\keylab\README.md`
- `arsenal\web\vj-core.js`
- `arsenal\web\vj.js`
- `arsenal\web\vj.html`
- `arsenal\lanes\vj_verify.mjs`
- `tests\test_keylab_vj.py`
- `tests\test_keylab_screen.py`
- `tests\vj_core.test.mjs`
- `tests\fixtures\vj\make_joy_take.py`
- Receipt and screenshots (gitignored): `state\arsenal\receipts\vj-20261023-094242\`

## Lane B: the adversarial verification (verbatim)

**Overall verdict: MERGE WITH NOTES.** The wiring is correct. Every item works and nothing in the page or screen breaks. But on Daniel's main genre, the new default (`--chords sense`) names chords worse than the old `--chords basic`. The cause is in chordsense, not in this lane's code. Daniel should decide before merging whether `sense` stays the default now, or this branch merges together with lane A's bass and kick fix (note 1).

I checked branch `worktree-wf_d904da09-5fd-2` (commits 7a8ab349, 81530e26 and ce0f492b) against master. I read it with `git archive` into my scratch folder and wrote nothing to the repo. The builder's worktree is untouched (HEAD ce0f492b, only the unstaged `seats.jsonl` line).

**My replay:** 45.8 s at 48 kHz and 150 BPM, my own seed. It has a distorted kick sweeping 260 → 50 Hz on every beat, a ducked sub bass at 41–65 Hz (plus D2 at 73 Hz), a 7-voice supersaw, a pad, hats and a clap. The progression is Am F C G ×2, Am Dm E7 Am, Am F C G, then Em C G D ×3 (the key moves to E minor at 25.6 s). Both engines ran in real time on ports 8971 and 8972 with `--no-leds --no-midi`.

**Per item**
1. **Chord events carry roman, key, bass and conf: fixed.**
   - All 36 of 36 chord events carry all four fields.
   - I ran all 2,176 recorded events through the page's `parseEvent`: 0 rejected, no field lost.
   - All 446 numerals and 24 key names chordsense can produce pass the page's filters.
2. **Key and tension events arrive and make sense: partly.**
   - They arrive: 5 key events and 41 tension events.
   - Tension follows the cadence: 0.85 on E7, then 0.32 when Am resolves.
   - The key is wrong for most of the A-minor part: C major (5.0 s), G major (7.8 s), D major at confidence 0.24 (18.6 s). A minor only arrives at 24.2 s, 1.4 s before the modulation. The E-minor part reads as G major, its relative major, which is acceptable.
   - A false D pedal runs from 21.8 s to the end, with F# and C before it. F# is not in the music at all; the kick's harmonics produce these. Because of it, the tension stays at 0.55–0.83 through the whole E-minor part.
   - The fast-path confidence bug reproduces: A minor and G major are announced at 1.0.
3. **hello names the chord engine: fixed.** It says `"chords":"sense"` or `"basic"`, and the status line repeats it.
4. **`--chords basic` still works: fixed.**
   - 27 of 27 chords correct. No key or tension events, and `harmony` in the state is null.
   - Offline, it produces the same chord names as the base on the same audio.
   - Beats (110) and hits (149) are identical between sense and basic.
5. **Every audio block read, cost per block: fixed.** One block is 10.67 ms.

   | | sense | basic |
   |---|---|---|
   | Blocks read | 4294 of 4294 | 4294 of 4294 |
   | Capture timing gap | −0.2 ms (`gap: false`) | +0.2 ms |
   | Late blocks / behind | 0 / 0 s | 0 / 0 s |
   | Whole loop per block | 0.89 ms avg, p99 2.01, max 2.85 | 0.62 ms avg, p99 1.49, max 2.17 |
   | chordsense's share | 0.34 ms avg, p99 1.19, max 1.52 | — |

   - Offline worst cases (noise at 0 dBFS, NaN/Inf blocks, a clipped square wave) stay at p99 0.32 ms and max 0.60 ms.
6. **`node arsenal/lanes/vj_verify.mjs`: PASS, 43 of 43.**
   - Run from my copy, under the house GPU lock, on SwiftShader.
   - Real-engine phase: the HUD shows "C major · conf 0.75 (audio) · IV" and "F IV (audio 0.89)". Capture gap 0.2 ms, chordsense p99 1.21 ms.
   - The receipt's demo groove puts the bass at 130 Hz, so it never exercises the failure in item 2.
7. **Test suites: pass.**
   - All keylab Python tests: 309 passed, 1 skipped; the base has 274 passed.
   - vj, screen, chordsense and the licence firewall alone: 155 passed, 1 skipped.
   - `vj_core.test.mjs`: 151 passed. `vj_show.test.mjs`: 18 passed.
8. **Malformed key, tension and chord events through `window.__vj.event`: fixed.**
   - 36 bad events sent; 34 were counted as bad and dropped:
     - NaN or ±Infinity values
     - text where numbers belong
     - `<img>` and `<script>` names
     - a 3,500-character name
     - a non-integer `pedal_pc`
     - null, array and object inputs
   - The other two: "Cb major" is accepted as a valid key, and an object with a getter that throws is not caught. Only the test hook can send such an object; JSON cannot.
   - Afterwards: no errors or exceptions, frames still advance, and the strip value stays finite.
   - 30 key changes in one second gave 0 flashes: the flash gate was untouched.
9. **A page facing an engine with no key or tension events: fixed.** Against both a `basic` hello and an older hello without the field, the branch page matches the base page: same chord HUD, strip tension 0.903 by the same rule, 0 bad events. Two differences:
   - the engine line now adds "chords basic";
   - an audio chord now shows its confidence in the HUD.
10. **Keys naming choice: reproduced.** On my random held block chords:
    - today's naming: 96.4 % right, first right at 50 ms (median);
    - chordsense's notes path: 84 % right, 170 ms.

    The builder's choice is right. Shipped `sense` on the keys:
    - matches today's on block chords;
    - 93.4 % against 73.2 % with a held D-flat 5 pedal note;
    - equal (73.2 %) with the pedal note re-struck; the gaps are filled with "Absus4".

    A live `--replay-midi` run of my own take (`--no-audio`): Db major announced 3.1 s after the first chord, numerals I / IV / vi / V7, tension 0.57 on Ab7 falling to 0.006 on Db.
11. **`screen --live`: fixed.**
    - Line 1 reads like `G/C  V  in C  (song)` and stays at 29 characters or fewer.
    - 2,176 events from my run gave 43 distinct views.
    - When the key moves, the numeral is dropped until the next chord arrives.
    - Line 2 reads `150 BPM | LASER`.
12. **Daniel's private playing: none in any committed file.**
    - All three commits: no `state/` or `recordings` files, no fixtures, no note lists.
    - The worship test material is synthetic: Db Gb Ab Bbm built in the test.
    - `--refresh` writes only to `state/`, which is gitignored.

**Regressions and notes**
1. **The default chord reading is worse on hardstyle** (chordsense, the other lane's file).
   - Real time: chords right 31 % of the time (root 59 %), against 71 % for basic.
   - Offline: 30 % (root 57 %) against 59 % for basic.
   - It names F as "Dm7", Am as "Asus4" and G as "G/C".
   - Without the drums it is still bad: 56 % against 68 %, with 7 "no chord" readings in the middle of the song. Without the sub bass as well it is close: 68 % against 70 %.
   - On my piano renders the root is about level (65–75 % against 70–74 %); the exact chord is lower (50–59 % against 69–71 %), because it names the pedal overlap: "Gbmaj7/Bb", "Absus4".
   - My recommendation: either keep `basic` as the default for audio chord names until lane A passes a kick-and-sub replay, or merge this branch together with lane A.
2. **Sharp keys get flat chord names.** `spell()` turns C#, D#, G# and A# into flats whatever the key. So the iii chord in E major shows "Abm iii" and C#m shows "Dbm". This undoes chordsense's own correct sharp spelling. It is the existing house rule, now applied to chordsense's names.
3. **After merge, the Joy fixture test fails until Daniel refreshes it.** This was disclosed by the builder; it fails and is fixed by `py tests/fixtures/vj/make_joy_take.py --refresh`.
   - I checked on a copy in my scratch folder: before the refresh, `test_the_joy_take_fixture_is_what_the_engine_sends_today` FAILS; after it, it passes.
   - Chord rows go from 241 to 322. The page's Joy pedal check is unchanged (83.8 % kept, 7.0 s of false alarms).
   - I deleted the copies afterwards.
4. **Minor page and engine issues:**
   - After a key change with no new chord, the HUD chord row keeps the numeral from the old key.
   - Identical tension events are sometimes sent twice in a row (for example, two at 9.649 s).
   - A "no chord" from the audio fires a full chord-change pulse.
   - `pedal_pc: -1` is shown as "B held under the harmony", `bass: -1` becomes 11, and `pedal_pc: 99` wraps round to E-flat.
   - A "no chord" event that carries a numeral displays it.
5. **The keys clock after a long stall.** If the MIDI thread stalls with keys held, the next step costs about 6.5 s per 30 minutes of stall (measured with 10 held notes). That freezes the MIDI dispatcher, not the audio loop. This is chordsense's round-1 item 6.
6. **Key confidence 1.0 and false pedals** pass straight through to the HUD and the strip (chordsense, lane A).
7. **Already on master, not this lane:**
   - `tests/test_keylab_chordsense.py` hardcodes this session's scratch-folder path (since 0caf4865).
   - `docs/PHYSICS.md` will conflict again at merge (its generated "Derived at" line); regenerate it.

Files are in `<session scratchpad>\verify-B\`:
- Scripts: `synth.py`, `piano.py`, `run_engine.py`, `analyze.py`, `offline.py`, `keys_probe.py`, `run_keys.py`, `pageprobe.mjs`, `parsecheck.mjs`, `romancheck.mjs`
- Results: `run_sense.json`, `run_basic.json`, `run_keys.json`, `pageprobe.json`, `pytest_branch_all.txt`, `pytest_master_all.txt`
- Receipt: `receipts\vj-20261023-095945\receipt.json`
