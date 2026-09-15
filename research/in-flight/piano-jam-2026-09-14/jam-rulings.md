# Jam space v1 rulings (conductor, 2026-09-15)

These rulings answer the open decisions from the jam build (workflow run wf_9b2c9f6c-a7d): J0-J9, round-2 verification and the repair round. Where this file and `jam-spec.md` disagree, this file wins.

## A1 timing: re-baselined rows (b) and (d)

**The measurement.** On this machine (Windows, Chrome 152), a worker timer's message reaches the page main thread p50 5-7 ms and p99 about 14 ms late. That holds even when the worker busy-waits to the exact moment and the page has no frame loop (repair probe `fix1/a1probe4.mjs`), and four timer variants left the callback p99 at the same floor. It is the platform's main-thread wake-up, not jam code.

**What Daniel hears is not affected.** `cues.js` hands every note to the voice 60 ms ahead (200 ms for at-cues) with an exact audio-clock time, so sound is placed by the audio clock, not by the callback. Post-repair A3: count-in tick sound onsets within 0.056 ms of plan, bar-0 bass onset within 0.235 ms.

| A1 row | Was | Ruling |
|---|---|---|
| (a) | unchanged | unchanged |
| **(b) Player callback lateness** (note-on callback minus planned) | p50 ≤ 1, p99 ≤ 4, max ≤ 12 ms | **p50 ≤ 8 ms, p99 ≤ 16 ms, max ≤ 33 ms** (two 60 Hz frames). The drift rows are unchanged: \|slope\| ≤ 0.2 ms/min, and first 30 s minus last 30 s ≤ 1 ms. |
| **(c) Sound onsets** (AudioWorklet probe) | p99 ≤ 2 ms, slope ≤ 0.1 ms/min | **Unchanged and binding.** This is the row that protects Daniel's ears. |
| **(d) Occluded window** | worker wake p99 ≤ 10 ms; `late_dropped` = 0 | **worker wake p99 ≤ 20 ms; `late_dropped` = 0 unchanged.** |

**Guard.** The re-baseline holds only while (c) passes and no at-cue is dropped for lateness (`AT_LATE_MS` = 20). If (c) fails, or a callback-driven visual (strip countdown, ghosts, chip) breaks its own budget (strip ≤ 17 ms, A3), the page must move that visual onto the audio-clock schedule. The budgets are not loosened again.

## Behaviour changes from the repair: ratified

- **A pending start (a knock) leaves the playing loop sounding until the launch swaps it on a bar line.** Musically right: Claude never cuts Daniel's groove to announce the next idea. Spec 5.2's "starting a run stops the running one at once" now applies to non-pending starts and to older pending runs. Spec 9.4's swap rule applies at launch.
- **The 9.4 landing rule taken literally.** A tempo, next or set change may land before one already scheduled later. A next card folds in a key change still waiting later. A later settings entry keeps only the fields it set. Relative tempo (`+4`) is taken from the segment in effect at the landing bar.
- **`GET /api/piano/jam` gains `pending`.** Page Try runs default to 2 passes at the server. J9's A7 lane must be re-run against this.

## Smaller rulings

- **`dropout` is a run setting.** Add it (a number 0..1, absent means off) to `SETTINGS_OPTIONAL_KEYS` and to the change-op `set` settings (J2 open issue; groove.js already accepts it).
- **Pad backing plays comp on v1**, following J0's `card_settings`. MUSIC 5.12's "full voicing forced to hold" reading is v2.
- **Comp register (J1):** the top voice and altered colours may reach E4; inner voices stay at or under B3. Leave out a 5th that only filled a voice before adding omitted tones (the Gm7/Bb case).
- **Ring check (A4):** a run of `upper: same` slots counts as one chord, per the 10.1 amendment.
- **Landing-note spelling:** spell the landing and riff note from the chord's own tones (`B♭, the ♭3rd of Gm(add9)`), never from a key-wide sharp or flat table. The theory TN2 ruling (one shared accidental-minimising speller) is the long-term home, and jam must not add a second speller.
- **Port 8888 is held by Docker Desktop.** Jam lanes default to 8889 or higher. Port 8796 stays with the replay companion.
- **Atmosphere in receipts.** A5's pixel-exact checks run with `--spectacle off`, as J9 found: the atmosphere is nondeterministic, and Asta confirmed there is no seed seam yet. Every other lane (A6, A7, A8, A9, A10, A12) must also pass once with `--spectacle on`, because Moonwater is Daniel's default look.
