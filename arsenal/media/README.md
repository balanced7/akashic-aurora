# arsenal.media: the house video toolbox

One toolbox for every agent, the editor and the coaching runs. Mining five days of agent runs (2026-10-12) found 2,437
throwaway scripts. Agents hand-built a contact-sheet grid 333 times, typed the ffmpeg path by hand 203 times and rewrote the
League clock reader 15 times, while the house versions sat unused. This package is the fix. It lives where agents
actually reach: `py -m arsenal.media <verb>`, `py agent_cli.py media <verb>` (recall-at-action shows it when an agent is
about to type `ffmpeg`), and the module manifests in `arsenal/modules/media.*.json`.

`py -m arsenal.media` lists the verbs; each takes `-h`. `py -m arsenal.media doctor --save` finds the best ffmpeg on
the machine and remembers it.

## The rules every primitive keeps

- **Originals are never touched.** Inputs are opened read-only. Outputs go to `--out` or `<state>/<verb>/`; the
  editor's renders go to a new folder, `E:\Video Output E\aurora-edits\<project>\`.
- **Every ffmpeg/ffprobe call goes through `ff.run()` / `ff.popen()`.**
- **Every result is the house shape**: `api`, `source`, `params` (with every default declared), `computed_with`, the
  payload, and `blind`, which says what the primitive cannot see. Each result is also written as a receipt under
  `<state>/receipts/<verb>/`.
- **Fail closed with a one-line reason.** Bad range, missing track, a time past the end of the file
  (`frames.at_times(past_end="error")`), a missing optional package: each names the fallback that ran, or refuses.
- `<state>` is `ARSENAL_MEDIA_STATE`, else `state/arsenal/media/` (gitignored). Test oracles live in
  `state/arsenal/media-oracles/` (local only: Daniel's recordings and other players' names never enter the repo).

## The house clock (Vandor's ruling, 2026-10-12)

**A file time is seconds from the file's start.** That is the time a player shows, and the time ffmpeg's `-ss` means.
Container timestamps (ffprobe `pts_time` and stream `start_time`) are converted at the edges by subtracting the format
`start_time`. League game times are named `game_t`, file times `file_t`.

OBS MP4 starts every stream at 0, so both readings agree on every recording we have. They differ on MPEG-TS-style
files: the container clock starts at 1.4 s, and with the sound muxed ahead of the picture the first frame sits 0.021 s
into the file, not at 0. Every primitive speaks file times: `probe.keyframes` and the sidecar, `frames`, `cut`,
`sheet`, `shots`, `audio.tracks` (`start_s`), and the editor's media record, keyframes, peaks and render. The sidecar
keeps one container time on purpose, its top-level `start_s`: where file time 0 sits on the container's clock. A
sidecar written before the ruling (no `"clock": "file"`) is moved onto the file clock when it is read.
`tests/test_arsenal_media_house_clock.py` pins all of it on two MPEG-TS fixtures and an MKV remux of one.

Two tools count on their own clock, so their edges convert (measured 2026-10-12):

- ffmpeg, reading only some of a file's streams, starts its output clock at the first of them when they all start
  after the seek point ("Correcting start time"): a decode of `v:0` alone puts a first frame that sits 0.021 s into
  the file at t=0. `frames` adds that back (`_origin`), and `shots` adds the first frame's file time to the times its
  scan counts. `-copyts -start_at_zero` has the same blind spot (it subtracted 1.421 s, not 1.4), so `cut.verify`'s
  `-copyts` decode adds the format start back to its trim bounds instead.
- Chrome's `<video>.currentTime` counts on the container's clock: a source whose clock starts at 1.4 s opens at
  1.4, and told 2.0 shows file time 0.6. The editor page converts every read and seek with the media's
  `container_start_s` (`timeline.js` `elementTime` / `sourceTime`).

## Decisions and their reasons

| Decision | Why |
|---|---|
| ffmpeg search: `ARSENAL_FFMPEG`, then the saved `doctor --save` choice, then PATH, then imageio-ffmpeg | The saved choice is ranked (`ff._score`); PATH holds whatever an installer dropped |
| `has_filter`/`has_encoder` answer for any name the build has | The build is the truth. `WATCH_*` lists what `doctor` reports; it is not a whitelist |
| `at_times` follows ffmpeg's `-ss t -frames:v 1` convention (first frame with pts >= t - 1 ms) | Grabs stay bit-identical to every earlier script (measured) |
| MPEG-TS and other non-indexed containers seek to the keyframe before, with `-noaccurate_seek` | Their seek lands on the next keyframe AT OR AFTER the target (measured: -ss 3.0 landed at 4.0) |
| Packet lists are read whole and cached, never with an open-ended `-read_intervals` | That read is nondeterministic near the end of a file (1 in 30 empty, measured) |
| Scene detection: PySceneDetect when installed, else ffmpeg's scene score + the spike rule on a 360p proxy | F1 0.851 / 0.844 on the synthetic montage; scdet's score scale gave 0.523 |
| The editor is First Light's Edit mode (`arsenal/web/edit/`), with its own state | First Light already had library roots, drop resolve and Range serving (Heimdall's fence: separate state) |
| One timeline document per project, `arsenal.media.timeline/v0`, `"master": "timeline-v0"`, a rev counter (stale PUT = 409) | The web UI and the CLI/MCP edit one file, one writer at a time; `master` makes the later board migration detectable |
| `arsenal.tiktok` keeps its own ffmpeg finder for now | Its tests pin a different order; converging changes pinned behaviour, so it waits for Daniel |
| `stt.transcribe(vad=...)` defaults to False; `media words` passes True | Flipping the default is a behaviour change. Its pre-registered gate is met (WER 10.8% on vs 11.7% off on the scratch voice); Daniel's call |

## Named seams (so nobody rediscovers them)

- Two ffmpeg finders (tiktok's and `media.ff`), with different orders.
- `stt` and `media words` transcribe game audio differently until the VAD default flips.
- The clock alignment of `probe.keyframes`/`cut`/`sheet` above.
- `at_times`' "inside the last frame's display interval" uses 1/average-fps: exact for CFR, approximate on VFR.
- `avsync` on the piano practice log finds two equal correlation lobes about 93 ms apart (key noise on the mic and the
  synth on desktop audio). Which one is "the" offset is a ruling still to make; the strict test is an xfail.
- The editor renders each clip as its own ffmpeg input (about 19 MiB per 1080p60 HEVC clip), so a 100-clip edit is heavy.
- Render jobs live in server memory; a server restart loses their state, not their files.

## What needs Daniel (none of it blocks the toolbox)

- **OBS:** Advanced output, 6 named audio tracks, keyframe interval 1 s (studio Part 3.3). Until then every recording
  has one mixed track, and a lossless trim can start up to 4.17 s early.
- **Optional packages** for the house Python: `scenedetect`, `rapidocr` (with `--no-deps`, to protect cv2 4.13),
  `pymediainfo`. Each has a working fallback.
- **The League replay** before patch 26.21 (2026-10-21): `py -m arsenal.media replay sheet` writes the run-sheet.
