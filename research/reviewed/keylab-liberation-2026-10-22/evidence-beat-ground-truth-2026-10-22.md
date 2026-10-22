# Evidence: ground truth for the beat bench from Daniel's own files (2026-10-22)

The final report of a read-only Explore agent (sonnet, the local Everything index), dispatched by Vandor for
the beat bench. Condensed to its findings; counts and paths are as reported.

## 1. FL Studio projects

- 11,941 files ending .flp, mostly autosave/backup noise:
  - C:\Users\L5\... : 6,614
  - F:\Backups\music-and-plugins\... : 4,961
  - FL's factory templates: 363
  - a sample pack: 3
- About **478 distinct projects** Daniel authored:
  - C:\Users\L5\Desktop\Old FL Projects\Projects\ (213);
  - C:\Users\L5\Documents\Image-Line\FL Studio\Projects\ (139);
  - C:\Users\L5\FL Studio Projects\ (122, including 27 date-named Piano Jams).
- Date range from file names, roughly 2018 to Oct 2026 (exact mtimes UNCONFIRMED).

## 2. Project and render pairs

- FL's render folder (Documents\Image-Line\FL Studio\Audio\Rendered) is **empty**. Renders sit beside their
  projects.
- Only **about 4-5 exact same-name .flp + audio pairs**, for example:
  - "FL Studio Metal 2026" (.flp + .mp3);
  - "Dua Lipa_5 w guitar_4.1" (.flp + .mp3);
  - Worship Grandeur Piano takes;
  - Providence Citi Worship Remix stems;
  - Jeremy Riddle Remix stems (stem-split, not a bounce).
- "new bass 120bpm.mp3" and "new chords 120bpm.mp3" carry BPM in the name, with no matching .flp found.

## 3. Reading tempo from an .flp

The house documents the FLP container (FLhd + FLdt, event-size classes by ID) in
research/reviewed/reverse-engineering-2026-10-13/software-binaries.md:417-424. Only event 199 (version) and 213
(plugin data) are named there. **No tempo event ID is documented.** PyFLP is GPL-3.0 (teardown-toolkit-and-practice.md
:748, :898), so the tempo event is derived clean-room: save one project at two tempos and diff the events.

## 4. BPM-labelled loops

About **34,030 audio files** carry a BPM in their file name (`\d{2,3}bpm`), almost all commercial packs:
- F:\Sample Packs\Cymatics\
- D:\Cymatics Samples\
- Documents\Splice\Samples\packs\
- FL's Sliced audio

These are valid ground truth for tempo and, because loops are cut to the grid, for phase too. They are
third-party content: **local private evaluation only, never committed or redistributed**.

## 5. Listening logs

No now-playing history is persisted anywhere. beatsync.now_playing() and tempo.py read SMTC live and discard
it.

## Vandor's plan from this

The bench's real-audio set is a manifest of BPM-labelled loops sampled across the packs (tempo from the file
name, phase from t=0), plus Daniel's handful of renders once the FLP tempo event is derived. The manifest
lists paths only, and the audio never leaves his disk.
