# Video primitives: the build spec (arsenal.media)

Status: proposal, 2026-10-12, written for Daniel and for the builders of tonight's step B in
`studio/STUDIO-RECONCILED.md`. Nothing in the repo, in OBS or in the recordings was changed to write it.

Inputs: three research tracks (outside tools, skills and workflows, mining our own runs), the studio design
(`studio/STUDIO-DESIGN.md`), its reconciliation (`studio/STUDIO-RECONCILED.md`) and Heimdall's fence on it. I also read the live
arsenal tree: `analysis.py`, `storyboard.py`, `timebase.py`, `stt.py`, `tiktok.py`, `mediatypes.py`, `registry.py`,
`modules/*.json`, `jam/align.py` and `__main__.py`.

Tags: **[measured]** means it was run on this machine tonight. **[source]** means a cited page (the URLs are in the track
reports). **[estimate]** means a guess, with the reason given.

Paths: `SP` = `C:\Users\L5\AppData\Local\Temp\claude\E--\2242a56c-f199-40d0-b388-b514151e329c\scratchpad\content`.
`OT` = `SP\primitives\outside-tools`.

---

## Part 0: The short version (for Daniel)

1. **We keep rebuilding the same small tools, and the house versions aren't reaching the agents.** In five days, agents
   wrote 2,437 throwaway scripts. 68 agents hand-built a contact-sheet grid 333 times. Contact sheets were built by hand
   in 48 transcripts, and `py -m arsenal storyboard`, which already makes one, was used in only 3. The ffmpeg path was typed out by hand 203 times.
   15 agents rewrote the League clock reader. The fix is one toolbox that every agent, the editor and the coaching
   run call, placed where agents will actually find it.
2. **The toolbox is `arsenal/media/`, a new package inside the arsenal you already have.** It is not a second system:
   - Scene detection extends `arsenal.storyboard`.
   - Time maps use `arsenal.timebase`.
   - Speech uses `arsenal.stt`.
   - Finding ffmpeg uses the finder in `arsenal.tiktok`.

   The editor (the studio) sits on top of it and calls it.
3. **Tonight (v0)** I'm proposing twelve pieces:
   - read a file's facts and remember them in a small database;
   - accept a file dropped onto the editor without copying it;
   - grab frames fast;
   - put many frames on one labelled sheet;
   - trim to the exact frame without re-encoding the whole file;
   - list, measure, draw and mix every audio track;
   - find the cuts;
   - read the League clock to map video time to game time;
   - load Riot's match data and pin every kill onto the video;
   - transcribe speech without the "if if if" hallucinations;
   - export with platform presets and a loudness check;
   - measure audio/video sync.

   Most of the code already exists in tonight's scratch folders and is measured. v0 means moving it into the house
   and testing it against answers we already hold.
4. **Things only you can do. Each is about five minutes, and none of them blocks v0:**
   - **OBS:** the six-track setup and the 1-second keyframe in studio Part 3.3. Today every recording has ONE mixed
     audio track, so separating your voice from the game is impossible at the source. A trim without re-encoding can
     also start up to 4.17 s early.
   - **League:** move the facecam off the minimap; it hides about 60% of it. When you record a replay to study, set
     the replay's Fog of War to your team. Otherwise the frames show enemies you couldn't see.
   - **Two Windows user settings:** `ARSENAL_FFMPEG` (where ffmpeg lives) and `PYTHONUTF8=1` (this stops a crash that
     hit 17 agents).
   - **Three small Python packages for the house interpreter:** `scenedetect`, `rapidocr` and `pymediainfo`. Each
     primitive works without them, a little worse, until you say yes.
   - **Leftovers from tonight's research, keep or delete:**
     - about 2.2 GB of speech and vision models in your Hugging Face cache;
     - the native Ollama app left running, idle at 43 MB;
     - a 148 MB whisper model copied out of the Steam folder of *Sky: Children of the Light*, in
       `SP\primitives\skills-workflows\whisper-filter-test`. It shouldn't stay.
5. **What we are not building:**
   - vision-language "AI taggers" for League footage (30 s a frame, invented answers);
   - ffmpeg's built-in whisper filter as our speech engine (no support for your GPU);
   - a 200-tool video MCP;
   - another web page.

---

## Part 1: Where it lives and what it reuses

Decision 1 of the reconciliation applies: no second module, port or receipt idiom. Here is the REUSE/EXTEND sheet for
this layer.

| Primitive | Verdict | House code it builds on | Why not just the existing code |
|---|---|---|---|
| ffmpeg locator / runner | **EXTEND** | `arsenal.tiktok.find_ffmpeg()` (ARSENAL_FFMPEG, then PATH, then imageio-ffmpeg) | It finds no ffprobe. Its fallback, imageio-ffmpeg, has no AMF encoder, whisper or libass. It doesn't report capabilities. tiktok then imports it from `media.ff`. |
| probe | **EXTEND** | `arsenal.analysis.probe()` (PyAV) + its on-disk cache | It lacks audio-track titles, the keyframe interval, the OBS encoder tag, a sidecar and a catalog row. |
| scene detection | **EXTEND** | `arsenal.storyboard` | storyboard divides footage into still stretches and motion at 5 fps and 480 px. That is right for pacing and piano takes, but it's not a cut detector, and nobody has measured it as one. `shots` adds cut detection and leaves storyboard in place. |
| time maps | **REUSE** | `arsenal.timebase.ClockMap` (affine: slope = replay speed, offset, uncertainty) and the studio's `studio.clockmap.v1` file | Each replay pass is one ClockMap. The OCR builder writes the studio's existing schema. |
| speech | **EXTEND** | `arsenal.stt.transcribe()` (faster-whisper small, CPU int8, words.json + cadence.txt) | It runs with `vad_filter=False` (stt.py line 88). Without VAD it hallucinates on game audio [measured]. |
| practice-log alignment | **REUSE** | `arsenal.jam.align` (ladder L1-L4, 2-150 ms) | avsync uses its anchor as the prior and reports its own measured offset next to it. |
| contact sheets | **NEW, absorbing copies** | storyboard's sheet writer + 5 `sheet()` functions already in the repo | There are six copies. One shared `sheet()` replaces them once its tests pass, and storyboard calls it. |
| export presets | **REUSE (promote)** | `SP\studio\production-pipeline\export_presets.json` + `studio_export.py` (measured) | Moved into the package unchanged, apart from the studio's own fix: `alpha_webp_anim` is encoded with Pillow. |
| module manifests, ports | **REUSE** | `arsenal/modules/*.json`, `mediatypes.PORT_TYPES`, `registry.validate_manifest` | One `media.<verb>.json` per primitive. No new port types. |
| receipts | **REUSE** | the storyboard/motion/floors manifest habit: `api`, declared params, denominators, `blind` notes, `analysis._computed_with()` | The same shape, written under `state/arsenal/receipts/media/<verb>/`. |

Package layout (builders):

```
arsenal/media/
  __init__.py      API = "arsenal.media/v0"; lazy imports only
  __main__.py      py -m arsenal.media <verb> ...
  ff.py            find + run ffmpeg/ffprobe, caps, Windows filter-path escaping
  probe.py         probe, quick_id, keyframe index, sidecar
  catalog.py       SQLite catalog, find, drop-resolve, link-by-time
  parse.py         OBS filename time, VTT/SRT/ASS -> words, FFMETADATA chapters read/write
  frames.py        one-pass frame iterator (promoted OT framesource.py)
  sheet.py         sheet, video_sheet, filmstrip
  cut.py           plan, cut (copy | smart | exact), verify, concat (promoted OT smartcut.py)
  audio.py         tracks, loudness, silences, demux, mix, split_channels, loudnorm_2pass, qc (promoted OT tracks.py)
  peaks.py         waveform peaks for peaks.js / wavesurfer (promoted OT peaks.py)
  shots.py         proxy + cut detection with default and fallback (promoted OT shots.py + analyze_video.detect_cuts)
  words.py         track/span -> arsenal.stt with VAD, times put back on the source clock
  avsync.py        offset + drift between two audio signals, or audio vs an event list
  export.py        presets + QC receipt (promoted studio_export.py)
  league/
    hud_boxes.json named HUD boxes as FRACTIONS of the frame, per layout (replay_1080, live_1080)
    hud.py         layout detection, box lookup; v1: HP bars, KDA/CS reads
    clock.py       HUD clock -> studio.clockmap.v1 (promoted OT clock_ocr.py)
    live.py        Live Client Data poller -> exact clockmap for live games (promoted studio live_event_sidecar.py)
    riot.py        match + timeline store, typed events
    events.py      Riot events x clockmap -> file times, fight windows
arsenal/modules/media.*.json
arsenal/tools/media-import.cmd        drop files on it -> imported into the catalog (the tiktok-ready.cmd pattern)
tests/arsenal/media/test_*.py
```

### House rules for every primitive (builders)

- **The originals are never touched.** Open read-only. Outputs go to `--out`, to `state/arsenal/media/...` (gitignored), or
  next to the original only when the caller asks with `--beside`. The tiktok verb already works that way.
- **Every ffmpeg or ffprobe call goes through `ff.run()`.** That keeps the binary, `-hide_banner -nostdin`, stderr capture
  and the exact argv for the receipt in one place.
- **Times at the API edge are float seconds on the source's own clock.** Stored artefacts also carry exact
  `pts` + `time_base` (the `timebase.TimeRef` JSON). A League game time is never passed where a file time belongs:
  game times are named `game_t` and file times `file_t`, everywhere.
- **Every result is a dict** with `api` (`arsenal.media.<verb>/v0`), `source` (`path`, `id`, `size`, `mtime_ns`), `params`
  (all defaults declared), `computed_with`, the payload, and `blind` (what this primitive cannot see). It is also written
  as a receipt.
- **Fail closed** with a one-line reason: bad range, missing track, missing optional package (and which fallback ran).
  Kinocut's preflight idea, in house form.
- **Crop boxes are accepted in pixels or as fractions** (all four values ≤ 1.0 means fractions). Your OBS base resolution
  became 3840x2160 on 2026-10-11 at 18:36. Every HUD box we hold is a 1080p pixel box, and 4K is untested.
- **Pixel-exact comparisons decode in software** (`hw=None`). d3d11va output differs from software decode by up to 7 luma
  levels on the same frame [measured].
- **Code style:** LF line endings, UTF-8, and no hard-coded user paths in committed code (`ff.doctor` discovers them and
  caches them in `state/`).
- **Heavy work takes the house GPU lock for its burst.** That means AMF encodes over about 30 s, model inference and
  proxy batches, per the reconciliation's single locking story (`arsenal/GPU-LOCK.md`, `lanes/gpu_lock.mjs`; the
  builder confirms the call shape there). Short d3d11va reads don't.
- **Tests that need Daniel's recordings, the Riot match (other players' names) or montages built from his footage skip
  when the files are missing.** Those files never enter the public repo. Synthetic fixtures (tones, `testsrc2`, lavfi
  montages) are generated at test time.

---

## Part 2: The primitives, in priority order

Priority = how often we rebuilt it × whether Daniel asked for it × how ready the code is. Each entry gives what it is
in plain words, the interface, the engine, the test, the cost and the version.

### P1. `ff`: find and run ffmpeg (v0, build step 1)

**Plain words.** One place that knows where ffmpeg is and what it can do, so no agent ever hunts for it again.

**Evidence.**
- 113 location probes in 53 transcripts.
- The path was typed by hand 203 times by 22 agents.
- "ffmpeg not found" failures: 8.
- 43 of 47 ffmpeg-calling scripts tonight hard-code the StemRollerTrio path [measured].

**Interface.**
```python
ff.ffmpeg() -> str
ff.ffprobe() -> str
ff.caps(refresh: bool = False) -> dict
    # {"version", "path", "encoders": {"h264_amf","hevc_amf","av1_amf","libx264",...: bool},
    #  "filters": {"scdet","whisper","ebur128","libplacebo","ass","subtitles": bool},
    #  "hwaccels": [...], "known_bad": {"vulkan_hevc_decode": "error -1145393733 on this driver"}}
ff.run(args: Sequence[str], *, tool: Literal["ffmpeg","ffprobe"] = "ffmpeg",
       timeout: float | None = None, check: bool = True) -> subprocess.CompletedProcess
ff.filter_path(p: str | Path) -> str      # 'C\:/Users/...' for ass=, subtitles=, movie=
ff.doctor(save: bool = False) -> dict      # binaries, caps, Python, optional packages, PYTHONUTF8, ARSENAL_FFMPEG
```

**Doors.**
- CLI: `py -m arsenal.media doctor [--save]`.
- MCP: `media_doctor()`.

**Order of search** (RECONCILED 2026-10-12; the code in `ff.locate()` is the reference):
1. `ARSENAL_FFMPEG`.
2. The location cached in `state/arsenal/media/config.json`. `doctor --save` ranks every build it finds (env, PATH,
   `%LOCALAPPDATA%\*\ffmpeg\bin\ffmpeg.exe`) and keeps the highest score (weights in `ff._score`).
3. `PATH`. The saved choice sits above PATH because it was picked on purpose; PATH holds whatever an installer dropped.
4. imageio-ffmpeg, with a loud warning: it ships no ffprobe and no whisper (the 7.1 build here does have AMF and libass,
   measured).

**Engine.** The house build N-124319 (2026-05-03): `--enable-amf --enable-whisper --enable-libass --enable-vulkan` [measured].

**Test.**
- `caps()` reports `hevc_amf`, `scdet`, `ebur128` and `ass` as true on this machine.
- `filter_path(r"C:\a b\x.ass")` burns a subtitle; the unescaped form fails with `Unable to parse "original_size"` [measured].
- (DEFERRED 2026-10-12) arsenal.tiktok keeps its own finder for now: its tests pin env -> PATH -> bundled, and
  converging on `media.ff` changes pinned behaviour, so it waits for Daniel's yes. Until then the house has two
  finders with different orders, named here so it is not rediscovered.

**Cost.** About 1 hour of building. No new dependencies.

### P2. `probe` + sidecar + `catalog`: a file's facts, remembered (v0, step 2)

**Plain words.**
- Drop a file in and the house learns what it is: length, picture, every audio track and its name, how often it has a
  keyframe, which program recorded it, and when.
- It remembers all of that in a small database, so the editor's library, the agents and the coaching runs ask the
  database instead of re-reading 2.4 GB files.
- It links each recording to what happened at the same time: a piano practice session, a League match.

**Evidence.**
- ffprobe JSON was parsed by hand 44 times by 20 agents.
- `probe.py` was written by 4 agents.
- No index of recordings exists today.

**Interface.**
```python
probe.quick_id(path) -> str                 # sha256(size || first 1 MiB || last 1 MiB)[:16]; ~5 ms
probe.probe(path, *, keyframes: bool = False, mediainfo: bool = True, refresh: bool = False) -> dict
    # sidecar "arsenal.media.sidecar/v0":
    # {id, path, size, mtime_ns, container, duration_s, recorded_at (parse.obs_time or tags), encoder ("OBS Studio (32.2.2)"),
    #  video: {codec, w, h, fps, vfr, has_b_frames, pix_fmt, color, keyint_s, keyframes_n},
    #  audio: [{index, codec, channels, sample_rate, title, house_name}], chapters: [...], kind, links: {...}}
probe.keyframes(path, *, stream: int = 0) -> list[float]     # packet-flag scan, cached in the sidecar
catalog.connect(db: Path | None = None) -> sqlite3.Connection  # state/arsenal/media/catalog.sqlite, WAL
catalog.upsert(sidecar: dict) -> str
catalog.add_spans(media_id, kind, rows, *, source) -> int     # kind: shot|chapter|clock_pass|event|window|silence|note
catalog.add_artifact(media_id, kind, path, *, params, api) -> None   # proxy|peaks|words|sheet|clockmap|stems
catalog.find(**where) -> list[dict]          # find(kind="league_replay", n_audio=1, recorded_after="2026-10-10")
catalog.resolve_dropped(name: str, size: int, last_modified_ms: int) -> str | None
catalog.link(media_id) -> dict               # time-overlap links: practice sessions, Riot matches (with confidence)
catalog.rebuild() -> dict                    # from sidecars; the sidecars are the truth, the database is an index
ingest(path_or_dir, *, recursive=False, proxy=True, shots=True, peaks=True, clock="auto") -> list[dict]
```

**Schema** (SQLite, WAL, one writer per process; rebuildable from the sidecars):
- `media(id PK, path, size, mtime_ns, duration_s, container, vcodec, w, h, fps, vfr, keyint_s, n_audio, encoder,
  recorded_at, kind, probed_at, sidecar)`
- `streams(media_id, idx, kind, codec, channels, sample_rate, title, house_name)`
- `tags(media_id, key, value, source)`. Examples: `match_id`, `champion`, `practice_session`, `replay=true`.
- `spans(media_id, kind, t0, t1, label, data_json, source)`. All time-ranged metadata goes in one table.
- `artifacts(media_id, kind, path, params_json, api, created_at)`

**Drag and drop, on a budget.**
- A browser drop gives the page a `File` (name, size, lastModified), never a path. Copying a 2.4 GB file to the server
  is what we avoid.
- `resolve_dropped()` matches name + size + mtime against the catalog and the library roots that `arsenal serve`
  already knows (`E:\Video Output E` by default), and returns the real path.
- If nothing matches, the page says which folder to add as a library root (Daniel's action). It can still preview the
  file in-browser with mediabunny.
- Second drop path: `arsenal\tools\media-import.cmd`. Dropping files onto it in Explorer runs `ingest`, the same pattern
  as `tiktok-ready.cmd`.

**Kind.**
- `league_live` or `league_replay`, from HUD layout detection on 3 keyframes (P8). The replay shows the speed box and
  "Manual Camera".
- `piano`, when it overlaps a practice session in wall time.
- Otherwise `screen` or `unknown`.

Recording time comes from the OBS filename `YYYY-MM-DD HH-MM-SS`, which is local time.

**Engine.** PyAV (house), ffprobe, and pymediainfo when installed (adds "OBS Studio (32.2.2)", CFR/VBR; 31 ms).

**Test.**
- `2026-10-11 17-51-11.mp4` gives:
  - HEVC 1920x1080, 60 fps, `has_b_frames` 0;
  - one Opus stereo track;
  - keyframe interval 4.17 s (250 frames) and 487 keyframes;
  - duration 2028.25 s (it matches the studio clockmap);
  - encoder OBS 32.2.2;
  - `kind` = `league_replay`.
- Ingesting the 11 recordings dated 2026-10-10/11 twice adds 0 rows the second time.
- `link()` ties `2026-10-11 16-56-57.mp4` and `17-06-22.mp4` to practice session `20261011-165503-f62d348c` (opened
  16:55:03 local, 51.5 min).
- `resolve_dropped()` finds a file from `E:\Video Output E` in under 50 ms, and returns None for a file outside the roots.
- `rebuild()` from sidecars reproduces the database row for row.

**Cost.**
- 85 ms for ffprobe and 31 ms for pymediainfo per file [measured].
- Keyframe index: 0.8 s for a 33-min file [measured]. The 11.8 s `-skip_frame nokey` path is banned.
- About 2.5 hours of building.

### P3. `frames`: frames out of a video, fast (v0, step 3)

**Plain words.** One fast way to pull pictures out of a video: every Nth frame, only the keyframes, or a list of exact
moments. Cropping and resizing happen inside ffmpeg.

**Evidence.**
- 21 scripts spawned one ffmpeg per timestamp (0.6 s a frame, against 0.03 s a frame in one pass).
- 21 scripts piped raw video by hand.
- A frame-grab helper was rewritten by 13 agents.
- Only 1 script used hardware decode.

**Interface** (promoted from `OT\primitives\framesource.py`; tested):
```python
frames.frames(path, start=0.0, dur=None, fps=None, crop=None, size=None, pix_fmt="rgb24",
              hw: str | None = "d3d11va") -> Iterator[tuple[float, np.ndarray]]      # (exact pts seconds, frame)
frames.keyframes(path, crop=None, size=None, pix_fmt="rgb24", hw="d3d11va") -> Iterator[...]
frames.at_times(path, times, crop=None, size=None, pix_fmt="rgb24", hw=None, max_gap=8.0,
                past_end="error") -> Iterator[(t_requested, t_pts, frame)]   # always accurate; past the end fails
                                                                             # closed unless past_end="last"|"skip"
frames.save(path, times, out_dir, *, fmt="png", **kw) -> dict    # files + manifest {t_requested, t_pts, crop, file}
```

**Doors.**
- CLI: `py -m arsenal.media grab <video> --at 12.5,30 | --span 10:20 --fps 2 [--crop x,y,w,h] [--size 640x] [--sheet]`.
- MCP: `media_grab` (the studio's tool name). It accepts `game_t` when a clockmap exists.

**Engine.**
- d3d11va decode: 1345 fps on 1080p60 HEVC, 22x realtime [measured].
- CPU decode: 620 fps.
- Keyframe-only decode: 325x realtime.

**Test.**
- The CPU path is bit-identical to single-frame `-ss` grabs [measured].
- `keyframes()` on 17-51-11 yields 487 frames whose pts equal `probe.keyframes()`.
- Clock crops for the whole 33-min file take under 10 s (4.7 s measured).
- Fractional and pixel crops give the same pixels at 1080p.

**Cost.** About 1 hour (promotion + tests). No new dependencies (numpy, house ffmpeg).

### P4. `sheet` + `filmstrip`: many frames, one picture (v0, step 4)

**Plain words.**
- Many frames on one labelled picture, each label saying where and when the frame came from.
- The filmstrip version puts a row of frames over the sound wave of the same seconds, so an agent can "watch" ten
  seconds in one image.

**Evidence.** This is the biggest hidden cost we found.
- The grid builder was written 333 times by 68 agents (about 588k output tokens).
- There were 134 streaks of 3 or more single-image reads (560 images).
- Each image costs about 2.2k context tokens and is carried a median 28 turns. That comes to about 174M cache-read
  tokens, roughly 8% of all of them.
- One labelled sheet costs about the same as one image.

**Interface.**
```python
Item = str | Path | tuple[str, float] | dict      # image path | (video, t) | {src, t, crop, label, zoom}
sheet.sheet(items: Sequence[Item], *, cols=None, cell_w=384, labels="auto", zoom=(), max_long_edge=1600,
            title=None, out=None) -> dict
    # {"png", "index": path, "cells": [{"i","src","t","pts","crop","label","row","col"}]}
sheet.video_sheet(src, *, n=30, cols=6, start=0.0, end=None, keyframes_only=True, crop=None, out=None) -> dict
sheet.filmstrip(src, t0, t1, *, n=8, width=1920, waveform=True, track=0, words=None, clock=None, out=None) -> dict
```

The default labels give file time, plus game time when a clockmap is given. Fonts are resolved once, from a
DejaVu/Segoe fallback list. `max_long_edge` keeps every sheet at the cost of a single image read.

**Doors.**
- CLI: `py -m arsenal.media sheet <items...>`, `... sheet --video <v> --n 30`, `... filmstrip <v> 12:00 12:10`.
- MCP: `media_sheet`.

**Test.**
- Index round-trip: re-grab cell k with `frames.at_times` and compare its md5 to the cell's crop.
- The 6x5 labelled sheet recipe and the 1920x256 filmstrip+waveform recipe reproduce the tested outputs in
  `SP\primitives\skills-workflows\cmd-tests` [measured].
- storyboard's own tests still pass after it calls `sheet()`.

**Cost.** About 2 hours. Pillow is already in the house interpreter (11.3.0).

### P5. `cut`: trim to the exact frame (v0, step 5)

**Plain words.**
- A trim that starts on exactly the frame you chose.
- Only the first second or so is re-encoded, on the GPU. Everything after is copied bit for bit, so it is near-instant
  and loses nothing.
- Every audio track and its name come along.
- Before cutting, it tells the editor what a trim will cost, so trim handles can show it.

**Why it matters.** OBS puts a keyframe every 4.17 s, and a plain copy-cut can only start on one. Without this, a "lossless
trim" starts up to 4.17 s early. ffmpeg hides 1.5 s of pre-roll that some players show anyway [measured].

**Interface** (promoted from `OT\primitives\smartcut.py`; verified):
```python
cut.plan(src, start, end) -> dict
    # {"mode_suggested": "copy"|"smart"|"exact", "start_keyframe", "head_reencode_s", "est_s", "reasons": [...]}
cut.cut(src, start, end, out, *, mode: Literal["copy","smart","exact"] = "smart",
        tracks: str | Sequence[int] = "all", verify: bool = True, preset: str | None = None) -> dict
cut.verify(src, start, end, out) -> dict
    # {frames_expected, frames_out, decode_errors, head_psnr_db, tail_psnr_db, copied_identical_sample,
    #  audio_streams_in, audio_streams_out, titles_kept}
cut.concat(parts: Sequence[str], out) -> dict        # concat demuxer; refuses mismatched codec parameters
```

**Modes.**
- `copy` snaps to the keyframe at or before `start` and reports the real start time.
- `smart` re-encodes [start, next keyframe) with `hevc_amf`/`h264_amf` at CQP 18, joins Annex-B, and copies audio
  packets. Audio is accurate to one packet: 20 ms for Opus, 21 ms for AAC.
- `exact` re-encodes the whole range with an export preset.
- If `has_b_frames` ≠ 0, `smart` falls back to `exact` and says so.
- Intermediates are written as MKV, which keeps track names. An MP4 output gets explicit `-metadata:s:a:N title=`,
  because copy-remuxing to MP4 drops track names [measured].
- The 30 ms audio fades at every join belong to the EDL renderer (studio), not to a single cut.

**Doors.**
- CLI: `py -m arsenal.media cut <src> <start> <end> <out> [--mode smart] [--plan]`.
- MCP: `media_cut`.

**Test.**
- The 4 verified cuts on 17-51-11 reproduce [measured]:
  - exact frame counts (601.5-612.0 s gives 630 frames);
  - 0 decode errors;
  - head PSNR 47.9-50.9 dB;
  - every copied frame bit-identical.
- A synthetic 3-track MKV (lavfi tones titled Voice, Game, Comms) keeps 3 titled tracks through `smart` into both MKV and MP4.
- `plan()` says `copy` exactly when start lies on a keyframe (0.28 s, against 1.3-1.5 s for a smart cut).

**Cost.** 1.3-1.5 s per cut [measured]. About 1.5 hours to promote.

### P6. `audio` + `peaks`: every track, measured, drawn and mixed (v0, step 6)

**Plain words.** Everything the editor's audio lanes need:
- list the tracks with their names;
- measure each one's loudness in a single pass;
- split each track into its own file so the browser can play them side by side;
- draw each one's waveform;
- mix them with your gains and mutes;
- run a final check that loudness, peaks and track count are right.

**Why it is needed.**
- Chromium here has no `HTMLMediaElement.audioTracks` [measured]. The editor must get one file per track and mix in
  WebAudio.
- ffmpeg's default stream selection silently keeps ONE audio track unless `-map 0` is given [source].
- Loudness was measured by hand in 17 transcripts, and two-pass loudnorm was built by hand 6 times.

**Interface** (promoted from `OT\primitives\tracks.py`, `peaks.py`):
```python
HOUSE_TRACKS = {0: "Mix", 1: "Voice", 2: "Game", 3: "Comms", 4: "Music", 5: "Piano"}   # ffmpeg a:N = OBS track N+1
audio.tracks(src) -> list[dict]          # index, codec, channels, sample_rate, title, house_name, duration_s
audio.loudness(src, *, tracks="all", span=None) -> list[dict]     # I (LUFS), LRA, TP (dBTP) per track, one decode pass
audio.silences(src, *, track=0, noise_db=-40.0, min_s=0.5, span=None) -> list[tuple[float, float]]
audio.demux(src, out_dir, *, tracks="all", codec="copy"|"flac"|"wav") -> list[str]   # copy: Opus -> .ogg, AAC -> .m4a
audio.mix(src, out, *, gains_db: dict[int, float] | None = None, mute=(), tracks="all", span=None,
          codec="aac", loudnorm: float | None = None) -> dict
audio.split_channels(src, track, out_dir) -> list[str]
audio.loudnorm_2pass(src, out, *, target_i=-14.0, tp=-1.0, lra=11.0, track=None) -> dict
audio.qc(path, *, expect: dict | None = None) -> dict
    # {I, TP, LRA, black: [...], freeze: [...], silence: [...], duration_s, streams: [...], problems: [...]}
peaks.peaks(src, *, track=0, spp=512, bits=8, channels="mono", out_prefix=None,
            formats=("dat","json","wavesurfer")) -> dict
```

**Doors.**
- CLI: `py -m arsenal.media audio <src> [--loudness] [--silences] [--demux DIR]`, `... mix`, `... peaks`, `... qc`.
- MCP: `media_audio`, `media_mix`, `media_peaks`, `media_qc`.

The track map follows studio Part 3.3 (6 tracks). The outside-tools track proposed 4 tracks; one map wins, and it's the
studio's. A stream's own title beats the map.

**Test.**
- A synthetic 3-track file with sines at -20, -26 and -30 dBFS measures within 0.1 LU per track.
- A mixdown with gains {0: 0, 1: -6} measures as predicted within 0.2 LU.
- Peaks length = ceil(samples / spp), and min/max match numpy per block exactly.
- The 33-min track gives a peaks `.dat` of about 371 KB in under 5 s [measured 3.4 s].
- `qc` flags a deliberately dropped track (expect 3 streams, get 1).
- `loudnorm_2pass` lands within ±0.5 LU of target; one pass lands about 1 LU off [source].

**Cost.**
- Loudness for 3 tracks: 0.74 s per 2 min. Demux: 0.2 s per 2 min. Peaks: 3.4 s per 33 min [measured].
- About 2 hours to promote. No new dependencies (soundfile and numpy are in the house).

### P7. `shots`: easy scene detection (v0, step 7)

**Plain words.** Finds the cuts in a video. It first makes a small 360p copy once, which takes about 6 s per 2 minutes,
and scans that copy about 100 times faster than real time.

One thing pixel methods can't do: a jump within the same League game looks like camera movement. For League footage,
the clock reader (P8) catches those jumps, and both answers are merged.

**Measured** on synthetic montages built from 8 of your recordings (40 hard cuts, 7 dissolves, 7 same-game cuts):

| Detector | F1 | Notes |
|---|---|---|
| PySceneDetect ContentDetector (threshold 27) on the proxy | 0.851 | Precision 0.925; 103x realtime on the proxy |
| ContentDetector threshold 22 / AdaptiveDetector | 0.857 | AdaptiveDetector adds 7 false cuts during fights |
| ffmpeg scdet + the house spike rule (analyze_video) | 0.844 | No new package |
| TransNetV2 (CPU torch) | 0.863 | Catches 6 of 7 dissolves |
| ffmpeg scene > 0.30 (a fixed threshold) | 0.50 | Recall 0.34. Never use it |

Every pixel method found 0-3 of the 7 same-game cuts.

**Choice.**
- **Default:** ContentDetector, threshold 27, on the proxy (best precision on gameplay).
- **Fallback when `scenedetect` is not installed:** scdet scores + the spike rule (`score ≥ 0.30`, or `≥ 0.12` and
  `≥ 8×` the median of the surrounding 2 s; minimum shot 0.25 s). The receipt names which one ran.
- **League footage:** clockmap discontinuities are added as cuts with `source="clock"`.
- **v1:** TransNetV2 as a second vote for montages with dissolves.

**Interface.**
```python
shots.proxy(src, *, height=360, fps=30, gop_s=1.0, hw="d3d11va", out=None) -> str     # cached as an artifact
shots.shots(src, *, detector: Literal["auto","content","spike","transnet"] = "auto", threshold=None,
            min_shot_s=0.25, use_proxy=True, clockmap: dict | None = None) -> dict
    # {"cuts": [{"t", "score", "source": "content"|"spike"|"clock"}], "shots": [[t0, t1], ...], "detector_ran", "blind"}
```

**Doors.**
- CLI: `py -m arsenal.media shots <src> [--detector spike] [--sheet]`. `--sheet` writes one representative frame per shot via P4.
- MCP: `media_shots`.

The editor's scrub proxy is the studio's `proxy_edit` preset. This 360p proxy is for analysis.

**Test.**
- On `OT\clips\synthetic2.mp4` with `synthetic2_truth.json`: default F1 ≥ 0.85, fallback ≥ 0.84 (±1 frame tolerance).
- **Pre-registered, not yet measured:** with the clockmap fused in, at least 6 of the 7 same-game cuts are found.
- `arsenal storyboard` is run on the same montage and its F1 recorded, so its role is stated by a number, not an
  opinion.

**Cost.**
- Proxy: 6 s per 2 min of 1080p60 with x264 ultrafast [measured].
- Detection on the proxy: about 20 s per 33 min [estimate from 103x realtime].
- About 1.5 hours to build.
- `scenedetect` 0.7.1 is BSD-3 and needs Daniel's install yes. The fallback needs nothing.

### P8. `league.clock`: video time to game time (v0, step 8)

**Plain words.**
- Reads the in-game clock on screen once per keyframe and builds a map from "second N of this video" to "game time
  M:SS".
- It handles your replay studying: rewinds, slow motion (0.25x, 0.5x) and skips.
- This map is what lets Riot's exact kill times land on the right frame. It also lets "show me the 24:02 fight" find
  every pass you watched of it.

**Evidence.**
- Clock and time-mapping code was rebuilt by 15 agents in 19 transcripts (63 calls), including `clocksheet.py` twice.
- `ttk_lib.py` hard-codes 1080p pixel boxes.

**Disagreement with the studio design, named on purpose.** Studio §1.8 leaves "OCR clockmaps" out of v0, because the old
recordings are hand-mapped and new takes get slates. I put it in v0 for three reasons:
- Your gameplay question tonight covers every fight in 17-51-11, and the hand map covers 11 passes.
- The code exists and is measured: 6 s per 33-min file.
- The hand map is the perfect test oracle, so v0 work is promotion plus a test.

**Interface** (promoted from `OT\primitives\clock_ocr.py`):
```python
league.hud.detect_layout(frame) -> Literal["replay","live","none"]
league.hud.box(name, layout, frame_shape) -> tuple[int, int, int, int]   # from hud_boxes.json fractions
league.clock.read(img) -> tuple[int | None, float]       # (game seconds, confidence)
league.clock.clockmap(src, *, hud="auto", every: Literal["keyframes"] | float = "keyframes",
                      start=0.0, dur=None, edge_fit=True, out=None) -> dict    # studio.clockmap.v1
league.clock.to_game(cmap, file_t) -> tuple[float, str] | None             # (game_t, pass_id)
league.clock.to_file(cmap, game_t) -> list[tuple[float, str, float]]       # every pass showing that moment: (file_t, pass_id, speed)
league.clock.as_clockmaps(cmap) -> list[timebase.ClockMap]
league.live.poll(out, interval=0.5)                       # Live Client Data API gameTime beside an OBS recording
league.live.clockmap(poll_log, recording) -> dict         # exact map for live games, no OCR
```

**How it works.**
- Passes are segments where `game_t - speed × file_t` is constant. The speed comes from the replay speed box, or is
  fitted.
- `edge_fit` finds the frame where the seconds digit changes. That pins the offset to 1 frame × speed (17 ms at 1x,
  4 ms at 0.25x), not ±0.5 s.
- The 3/8, 5/6, 0/8, 1/7 and 4/1 confusions are fixed by neighbour consistency.

**Engine.**
- RapidOCR recognition-only on the clock crop: 29/29 correct, 5.8 ms per crop [measured]. Tesseract got 19/29, so it's
  rejected.
- If rapidocr is not installed (Daniel's yes): a digit-template reader on house `cv2` 4.13. Its 10 templates are cut
  once from frames that RapidOCR labelled in the scratch `tv` venv, and normalised to crop height so 4K works.
- For future live games: `league.live`. It is the studio's `live_event_sidecar.py`, which polls
  `https://127.0.0.1:2999/liveclientdata`. That gives an exact map with no OCR at all.

**Test** (ground truth we hold):
- Against `SP\studio\storyboarding\draven\clockmaps\rec_17-51-11.clockmap.json`, 11 hand-calibrated passes. For every
  pass, the OCR map gives the same speed and an offset within `max(tol_s, 1 frame × speed)`:
  - `early_1x` offset 6.84 ± 0.03;
  - `A_0.25x` speed 0.25, offset 1097.4375 ± 0.05;
  - `C_1x` offset -405.375 ± 0.05.
- The two passes in `rec_16-50-20.clockmap.json`.
- The live recording `2026-10-10 21-35-21.mp4` gives exactly one 1x pass with offset -152 s ± 1 frame, covering
  0:02-22:53.
- `to_file(cmap, 1442.051)` (the 24:02 kill) returns both passes that show it: file ≈ 1596.2 s in `p2402_1x` and one
  inside the 0.25x pass at 26:52-27:01.

**Cost.**
- About 6 s per 33-min file [measured].
- About 3 hours to build (promotion, edge-fit, template fallback, tests).
- `rapidocr` 3.10.0 is Apache-2.0. Install it **with `--no-deps` plus its non-OpenCV dependencies**, because in the
  scratch venv it pulled opencv 5.0.0.93, which would replace the house cv2 4.13 [measured in the venv].

### P9. `league.riot` + `league.events`: Riot's truth, pinned to frames (v0, step 9)

**Plain words.**
- Loads a match's full Riot record once: every kill with its exact millisecond, assists and position, items, wards,
  objectives, levels.
- Puts every event on every video frame that shows it.
- Groups nearby kills into fights, with a lead-in and an aftermath, ready to clip or review.

**Evidence.**
- Match and timeline JSON was re-parsed in 165 calls by 23 agents (148 scripts, about 384k output tokens).
- `CHAMPION_KILL` was parsed by 20 agents, and an mm:ss formatter written by 32.
- We once told you "bootless Draven", which was wrong: the boots had moved to `participant.roleBoundItem` when the role
  quest completed.

**Interface.**
```python
riot.load(match_id, *, root=None) -> Match       # cached match.json + timeline.json + the patch's ddragon/cdragon
Match.participants -> list[Player]               # champion, team, role, riot id, items incl. roleBoundItem
Match.frames() -> list[dict]                     # per-minute state: gold, xp, cs, position per participant
Match.events(kinds=None) -> list[Event]          # typed: Kill(killer, victim, assists, pos, bounty, game_t), ItemEvent,
                                                 # WardEvent, Objective, LevelUp, SkillUp
riot.mmss(t) -> str
riot.parse_mmss(s) -> float
events.join(match, cmap) -> list[dict]           # each event + every file_t that shows it (+ pass id, speed)
events.windows(evts, *, rules={"kill": (15, 5), "death": (40, 5), "objective": (30, 10)}, merge_gap_s=10.0,
               player=None) -> list[dict]        # fights: [t0, t1], members, kills, deaths, file spans
events.write_csv(rows, out) -> str
```

**Doors.**
- CLI: `py -m arsenal.media events <video> --match NA1_5658447097 [--player <name>] [--csv out]`.
- MCP: `media_events`.
- The studio's `beats_mine(match)` calls `events.windows`.

**v0 scope.** Load from cached JSON only. Fetching from Riot's API needs an API key, and the key is Daniel's to enter;
agents never type it.

**Engine.** Python stdlib + json. Windows follow lol-kill-clipper (15/5 s around a kill, 40/5 s around a death) [source].

**Test.**
- `SP\riot\match.json` + `timeline.json` (NA1_5658447097, 16.20, 1629 s): every participant's kills and deaths in the
  match summary equal the count of `CHAMPION_KILL` events (Draven 31/8).
- The Draven roleBoundItem boots are reported.
- `join` places the 24:02 MF-kills-Draven event at the frame where `ttk_video_summary.json` measured the death, within
  1 frame (death_err there is 3 ms).
- The final-fight score changes in `yuumi/video-final-fight/fight_timeline.json` (Mord 26:14.88, Galio 26:17.14, Swain
  26:17.31, Amumu 26:18.36) land inside the 0.25x pass, within 0.05 s.

**Cost.** Milliseconds per call. About 3 hours to build. No dependencies.

### P10. `words`: speech to text with word times, without hallucinations (v0, step 10)

**Plain words.** Turns speech into text with the time of every word, so we can edit by text, caption and search. The
fix: always skip the parts with no speech. Without that step, the model invents words over game sound ("if if if",
"Oh. Oh. Thank you.") [measured].

**Interface.**
```python
arsenal.stt.transcribe(audio, stem, model_size="small", *, vad: bool = <see below>, language="en") -> dict   # extended
words.words(src, *, track: int | None = None, span: tuple[float, float] | None = None, model="small",
            vad: bool = True, out_stem=None) -> dict
    # cuts the track/span to 16 kHz mono via ff, calls stt.transcribe, shifts word times back to the source clock;
    # {"words_json", "cadence_txt", "words": n, "unsure": n, "vad": true, "model"}
parse.subtitles(path) -> list[dict]          # VTT/SRT/ASS -> words or segments (vttwords.py was written twice)
```

**Doors.**
- CLI: `py -m arsenal.media words <src> [--track 1] [--span 10:00-12:00] [--model large-v3-turbo]`.
- MCP: `media_words`.

**Rules.**
- `small` with VAD for indexing (32x realtime). `large-v3-turbo` with VAD for final captions (16x realtime, best text)
  [measured].
- Never the ffmpeg `whisper` filter. Its GPU path rejects gfx1201. It ran at 15x realtime with the base model, and
  0.62x with large-v3-turbo q5 [measured].
- With one mixed track, transcribe only the chosen windows, or the Voice stem once stems exist.

**Changing stt's default.** stt's default `vad=False` flips to True **only if** a clean-voice test shows no loss: word
error rate on the studio animatic's scratch voice against its locked script, VAD on vs off. Otherwise stt keeps False and
`words` passes True. This changes no behaviour silently ("ask before deleting functionality").

**Test.**
- On the game-audio excerpt 600-720 s of 17-51-11, VAD on gives no repeated-token runs of 3 or more. VAD off reproduces
  the hallucination; that is the regression oracle.
- The scratch-voice WER is reported for both settings.
- Word times shifted for `span` agree with a full-file run within 50 ms.

**Cost.** CPU only, $0. About 1 hour to build. faster-whisper 1.2.1 is already in the house interpreter. The models sit in
the HF cache (see Part 0, item 4).

### P11. `export` + QC: platform presets with a receipt (v0, step 11)

**Plain words.** One command makes the YouTube, Shorts, edit-proxy, archive or transparent version. Every export checks
its own loudness, peaks, track count and length, and writes down what it did.

**Interface** (promoted from `SP\studio\production-pipeline\studio_export.py` + `export_presets.json`):
```python
export.presets() -> dict
export.export(src, preset, out, *, start=None, end=None, audio: str | Sequence[int] | dict = "0",
              crop_x=0.5, loudness=None, dry_run=False) -> dict   # receipt: argv, ffmpeg version, input id, qc
```

**Presets.** These are the measured set; any new preset ships with its own measured row:

| Preset | For | Measured |
|---|---|---|
| `youtube_4k60` | YouTube, final | x264 CRF 16 |
| `youtube_4k60_fast` | Drafts | 10 s in 9.5 s, -14.1 LUFS / -1.4 dBTP |
| `shorts_1080x1920` | Shorts, TikTok, Reels | 20 s in 8.8 s; a quiet clip went from -41.3 to -14.2 LUFS |
| `proxy_edit` | Editor scrubbing | 1080p, a keyframe every 0.25 s |
| `mezzanine_dnxhr` | Archive and handoff to other editors | |
| `alpha_webm` | Web and OBS overlays | Decode with libvpx-vp9 |
| `alpha_prores4444` | Resolve, Kdenlive, Blender | |
| `alpha_webp_anim` | Discord "transparent gif" | **Encode with Pillow.** ffmpeg piles up opacity (alpha error 111 by frame 30) |

The house TikTok target stays -16 LUFS (`arsenal tiktok`); the YouTube target is -14 LUFS / -1 dBTP.

**Doors.**
- CLI: `py -m arsenal.media export <preset> <src> <out> [--start --end --audio 0,1]`.
- MCP: `media_export`.

**Test.**
- Each preset on a 10 s excerpt lands within ±0.5 LU of its target, with true peak ≤ target, exact duration to 1 frame,
  and the expected stream inventory.
- `alpha_webp_anim` round-trips a soft-edged test clip with alpha error ≤ 1 on every frame.

**Cost.** AMF encode at about 7.3x realtime for 1080p at 12 Mb/s [measured]. About 1.5 hours to promote.

### P12. `avsync`: is the sound lined up with the picture? (v0, step 12)

**Plain words.** Measures how far two recordings of the same moment are apart, in milliseconds, and whether the gap
grows over time (drift). It answers:
- Are the OBS audio and video in sync?
- Does this recording line up with the piano practice log?
- Is the Discord track late?

**Evidence.**
- A/V sync was measured in 22 calls by 8 agents; `sync.py` was written by 3 agents.
- `analyze_video.alignment()` exists but only scores cuts against beats.

**Interface.**
```python
avsync.offset(a, b, *, a_track=0, b_track=0, span=None, max_offset_s=2.0, window_s=30.0) -> dict
    # onset-envelope cross-correlation; {offset_ms, confidence (peak/second-peak), drift_ms_per_min, windows: [...]}
avsync.against_events(src, event_times_s: Sequence[float], *, track=0, max_offset_s=2.0) -> dict
    # e.g. MIDI note-ons from a practice session; {offset_ms, drift_ms_per_min, matched, unmatched}
```

v1: `avsync.visual(src, roi, track)`, which compares visual onsets (key lights, muzzle flashes) with audio onsets. That
is the true A/V check.

**Doors.**
- CLI: `py -m arsenal.media avsync <a> [<b>] [--events session:<id>]`.
- MCP: `media_avsync`.

**Test.**
- A synthetic test: a copy shifted with `-itsoffset 0.083` is recovered as 83 ± 2 ms.
- Practice session `20261011-165503-f62d348c` (56,353 events, note-ons with `t_ms`) against `2026-10-11 17-06-22.mp4`.
  First check with `peaks` that the piano is audible in it. The offset should hold steady to within 1 frame (16.7 ms)
  across the recording and agree with `jam.align`'s anchor within that anchor's stated error (L3: 50 ms).

**Cost.** Seconds per call. About 1.5 hours to build. librosa and scipy are in the house interpreter.

### Doors, reach and manifests (v0, built WITH each primitive, not after)

The mining's clearest lesson: **agents use what is in reach and ignore what is not.**
- `gpu_lock.mjs` was run 71 times by 12 agents.
- `scripts/ui_shot.py` was used 0 times while 41 agents wrote 170 browser rigs.
- `arsenal/timebase.py` was never touched.

So every primitive ships these, in the same commit:
1. **CLI verb** under `py -m arsenal.media`. `py -m arsenal probe` and `storyboard` keep working.
2. **agent_cli verb** `py agent_cli.py media <verb> ...`, a passthrough. Recall-at-action's verb channel (T311,
   `core/recall/at_action.py`) parses agent_cli's `add_parser(help=...)` strings and pushes matching verbs when an agent
   is about to act. The help text must therefore use the words agents type: ffmpeg, ffprobe, frame, contact sheet,
   trim, cut, scene, loudness, waveform, clock, OCR, Riot, timeline.
   - **Test:** `py agent_cli.py recall-at --command "ffmpeg -ss 12 -i a.mp4 -frames:v 1 x.png"` surfaces the media verb.
     If `_verb_exclusions` filters the token `ffmpeg`, that is fixed or the help wording changed until the test passes.
3. **MCP tool** with the names above. They are mounted by the studio server when it exists. Until then a thin
   `py -m arsenal.media.door` (the house FastMCP pattern from `ai_setup_mcp.py`) serves them on its own, so the
   knowledge door doesn't grow by 16 tools.
4. **Module manifest** `arsenal/modules/media.<verb>.json` (`protocol: arsenal.module/v0`, port types from
   `mediatypes.PORT_TYPES`). `py -m arsenal inspect` lists it and `registry.validate_manifest` passes.
5. **Skill routing.** The drafted `video-work` and `vod-review` skills (`SP\primitives\skills-workflows\skills\`) get
   their route tables pointed at these verbs before they are installed in `.claude/skills/`. Daniel reads them first,
   and each gets 3 evals.

**Pre-registered reach measure.** One week after v0 lands, re-run `SP\primitives\self-mining\extract_calls.py` and
`classify.py` over the new transcripts. Success means, per agent-hour of media work:
- hand-built grids halved;
- hand-typed ffmpeg paths halved;
- single-image read streaks halved.

### MCP tool list (v0, 16 tools)

| Tool | Function |
|---|---|
| `media_doctor()` | `ff.doctor` |
| `media_probe(path, keyframes=False)` | `probe.probe` |
| `media_import(path_or_dir, recursive=False)` | `ingest` (the studio's tool name, the same function) |
| `media_find(**where)` / `media_resolve_drop(name, size, last_modified_ms)` | `catalog.find` / `catalog.resolve_dropped` |
| `media_grab(src, at=None, span=None, fps=None, crop=None, game_t=None, sheet=True)` | `frames` + `sheet` |
| `media_sheet(items, cols=None)` / `media_filmstrip(src, t0, t1)` | `sheet` |
| `media_shots(src, detector="auto")` | `shots.shots` |
| `media_cut(src, start, end, out, mode="smart")` / `media_cut_plan(src, start, end)` | `cut` |
| `media_audio(src)` / `media_mix(...)` / `media_peaks(...)` / `media_qc(path)` | `audio`, `peaks` |
| `media_words(src, track=None, span=None)` | `words.words` |
| `media_clockmap(src, hud="auto")` | `league.clock.clockmap` |
| `media_events(src, match_id, player=None)` | `league.events` |
| `media_avsync(a, b=None, events=None)` | `avsync` |
| `media_export(src, preset, out, ...)` | `export.export` |

---

## Part 3: Later (v1 and v2)

| # | Primitive | Ver. | Plain words | Engine / evidence | Test against | Cost |
|---|---|---|---|---|---|---|
| L1 | `stems.split(src, track, models)` + `gpu.dml_device()` | v1 | Pull voice, game and music apart in old one-track recordings | UVR MDX-Net / Demucs on DirectML **pinned to the RX 9070 XT by DXGI name**. The default adapter is the integrated GPU: 1,444 ms against 47 ms per chunk, and 35-38 s against 4.4-7.5 s per 90 s of audio [measured]. Promotes analyze_video's `pick_gpu` and `split_stems` | Receipt names the device. Separation of a synthetic sum of known voice + game recovers each with SDR reported. 39.5x realtime holds | Needs a durable venv location (today it's in %TEMP%), Daniel's call. 3-4 h |
| L2 | `league.hud.hp_bars(frames, champs)` → per-100 ms HP table | v1 | Read health bars over a fight: who took what damage, when | Promotes `SP\ttk\video\ttk_lib.py` (template match + bar profile). 86 calls by 11 agents rebuilt pieces of it | `ttk_video_summary.json`: reproduce each kill's TTK within one HP update (≤125 ms), and death time within 1 frame (the 24:02 kill: TTK 929 ms, death_err 3 ms) | 1-2 days |
| L3 | `league.hud.read_scoreboard(frame)` | v1 | KDA, CS, team kills from the HUD | RapidOCR on fixed boxes ("4/2/0", "47", "3 vs 10" read correctly [measured]) | Riot `participantFrames` minionsKilled per minute; kill counts from `CHAMPION_KILL` | 3 h |
| L4 | `shots(detector="transnet")` | v1 | A second opinion for montages with dissolves | TransNetV2 PyTorch CPU (MIT), F1 0.863, 6/7 dissolves [measured] | synthetic2 dissolves ≥ 6/7 | torch CPU venv; 2 h |
| L5 | `captions.ass(words, preset, size)` | v1 | Burned-in word-by-word captions for Shorts | One ASS event per word, libass burn via `ff.filter_path`. Karaoke highlight tested [measured]. Coordinate with the studio's `shorts_cut` (one generator, not two) | Renders; MarginV keeps out of each platform's safe zone | 2 h |
| L6 | `reframe.stack(src)` / tracked crop | v1 | 9:16 with facecam on top and the game below | Stack recipe tested at 1080x1920 [measured]. Florence-2-base finds the facecam box at 0.9 s/frame on CPU [measured] | Facecam box matches `crop=495:277:1320:738` at 1080p | 2 h (stack), 1 day (tracking) |
| L7 | `otio.export(edl|board)` | v1 | Hand the edit to Resolve, Kdenlive or Premiere | opentimelineio (Apache-2.0); install is Daniel's yes. The studio already compiles .otio | Premiere import drill (studio item 16) | 2 h |
| L8 | `catalog.search(text)` | v1-v2 | "Find the clip where I flash over the wall" | Transcript chunks in SQLite FTS5 first (free); SigLIP shot embeddings later | A hand-written query set of 20 with known answers | FTS: 2 h; embeddings: 1-2 days |
| L9 | `avsync.visual` | v1 | True picture-vs-sound check | Visual onsets in an ROI vs audio onsets | A piano take with the visualizer on screen | 3 h |
| L10 | auto-editor on the Voice track | v1 (after OBS change) | Jump cuts for talking parts | auto-editor 29.3.1 (Unlicense): whole 33-min file in 7 s; on the game mix it only finds loud moments [measured] | A take with deliberate pauses | 1 h |
| L11 | `league.cam` camera model | v2 | Where on the map the screen is looking | Minimap camera box or Riot positions. Manual replay camera makes this hard | Riot positions per minute | days |
| L12 | `league.fx` effect and ability detectors | v2 | Flash, ult and ability use from frames and the chat log | cdragon icon templates; RapidOCR full frame reads "Swain used Flash" in 510 ms, so only inside windows [measured] | Riot timeline where it has the event; else hand labels | days |
| L13 | GPU speech (whisper.cpp Vulkan) | v2 | Faster transcripts on the GPU | Needs a Vulkan SDK build or a vetted binary (official Windows builds lack Vulkan [source]) | Same WER as CPU | 1 day |

**Not recommended, with the measurement that killed each:**
- **Vision-language taggers for League:**
  - gemma3:4b in the Docker Ollama ran CPU-only at 30 s/frame and invented tags;
  - llava:7b on the native ROCm Ollama ran at 6.5 s/frame and echoed the JSON schema.
  - If tagging is ever wanted, the one to try is qwen3-vl:2b on the native Ollama (port 11435). Pulling it is Daniel's call.
- **ffmpeg's whisper filter as the speech engine.**
- **Tesseract** (19/29 on the clock).
- **Vulkan HEVC decode** (fails on this driver).
- **`-skip_frame nokey` for keyframe lists** (11.8 s, against 0.8 s for the packet-flag scan).
- **AdaptiveDetector on fights.**
- **A 200-tool video MCP:** borrow Kinocut's preflight and receipts, not its surface.
- **CoTracker3, MatAnyone, RMBG-2.0** (non-commercial licences; from the studio track).

---

## Part 4: Build order for tonight

Four lanes run in parallel once P1 lands. Every step: tests pass, LF line endings, advisory lock on touched paths,
recall-at before edits, local commit (no push). These are the reconciliation's rules.

| Step | Lane | Primitive | Depends on | Hours [estimate] |
|---|---|---|---|---|
| 1 | all | P1 `ff` + `doctor` (+ tiktok imports it) | none | 1 |
| 2 | A | P2 `probe`, sidecar, `catalog`, `parse.obs_time`, `resolve_dropped`, `link`, `ingest`, `media-import.cmd` | 1 | 2.5 |
| 3 | B | P3 `frames` | 1 | 1 |
| 4 | B | P4 `sheet`, `video_sheet`, `filmstrip` | 3 | 2 |
| 5 | B | P5 `cut` (plan, smart, copy, exact, verify, concat) | 1, 2 (keyframes) | 1.5 |
| 6 | C | P6 `audio` + `peaks` + `qc` | 1 | 2 |
| 7 | A | P7 `shots` (proxy, content, spike fallback) | 1, 4 (for `--sheet`) | 1.5 |
| 8 | D | P8 `league.hud` boxes + `league.clock` (+ `league.live` promoted as-is) | 3 | 3 |
| 9 | D | P9 `league.riot` + `league.events` | 8 | 3 |
| 10 | C | P10 `words` (+ the stt VAD parameter and its WER test) | 1, 6 | 1 |
| 11 | C | P11 `export` (+ the Pillow WebP fix) | 6 | 1.5 |
| 12 | C | P12 `avsync` | 6 | 1.5 |
| 13 | A | MCP door + module manifests + agent_cli verb + reach test | each primitive's CLI | 2 |

That is about 24 builder-hours across four lanes, roughly 6-7 hours of wall time.

**If the night runs short, the cut line falls after step 9.** P1-P9 are what the editor (drag-drop, trim, multi-track
audio, metadata) and the gameplay review need. P10-P12 come first thing tomorrow.

**Compute per 33-minute recording once v0 exists, all local, $0:**
- probe and keyframes: about 1 s;
- proxy: about 100 s;
- cuts: about 20 s;
- clockmap: about 6 s;
- loudness and peaks: about 8 s;
- transcript of chosen windows only: seconds.

That is about 2-3 minutes in total [measured parts, summed]. Disk: the analysis proxy is about 250-500 MB per
33 minutes [estimate: 360p30 x264 ultrafast at 1-2 Mb/s, not yet measured]. Sidecars, peaks and the database come to a
few MB.

---

## Part 5: Ground truth we already hold (the test oracles)

| Truth | Where | Tests |
|---|---|---|
| Hand-calibrated clockmap, 11 passes, tol 0.03-0.5 s | `SP\studio\storyboarding\draven\clockmaps\rec_17-51-11.clockmap.json` (+ `rec_16-50-20`) | P8 |
| Live recording maps as one pass, offset -152 s | `OT\bench\clock_full_21-35-21.json` | P8 |
| Replay passes found by OCR: 17 rewinds, 7 slow-motion runs (consistency, not truth) | `OT\bench\clock_full_17-51-11.json` | P8 |
| Riot match + timeline NA1_5658447097 (patch 16.20, 1629 s) | `SP\riot\match.json`, `timeline.json` | P9 |
| Measured TTK per kill, death time error 3 ms | `SP\ttk\video\ttk_video_summary.json` | P9 join, L2 |
| Final-fight score changes at 0.25x | `SP\yuumi\video-final-fight\fight_timeline.json` | P9, L3 |
| Shot montages with truth: 40 cuts, 7 dissolves, 7 same-game cuts | `OT\clips\synthetic2.mp4` + `synthetic2_truth.json` | P7 |
| 4 verified smart cuts (frame counts, PSNR) | OT track report, `OT\bench` | P5 |
| Practice-log note-ons, 56,353 events | `E:\AI-Setup\state\arsenal\performance\20261011-165503-f62d348c\events.jsonl` + recordings 16-56-57, 17-06-22 | P2 link, P12 |
| Probe facts of 17-51-11 | OT track report | P2 |
| Export preset measurements | `SP\studio\production-pipeline\export_presets.json` | P11 |
| Hallucination oracle (VAD off) and the scratch voice + locked script | 17-51-11 at 600-720 s; studio animatic | P10 |

All of these stay local: they hold Daniel's recordings and other players' names. Tests that need them skip when they
are missing.

---

## Part 6: What mining our runs found beyond video (other homes, not this package)

These are just as repetitive and just as cheap to fix. They belong in `scripts/` or `core/`, not `arsenal.media`. Listed
so they don't get lost:

| Tool | Evidence | Suggested home |
|---|---|---|
| `patch`: exact-once anchored edits that keep line endings, then syntax-check | Written 178 times by 32 agents; 160 lines silently turned CRLF; 20 anchor failures | `scripts/patch.py` + agent_cli verb |
| Environment doctor (PYTHONUTF8, PATH, path normalising, argv-based process match) | PYTHONIOENCODING set by hand 225 times by 26 agents; cp1252 crashes in 17 agents | `py agent_cli.py doctor` |
| Job runner instead of sleep loops | 83 polling loops took 6.7 h; 149 calls asked for more than the 10-minute cap | Harness Monitor + a brief rule |
| `shoot`: one headless render rig (absorbs `ui_shot.py`) | 170 rig scripts by 41 agents; 211 runs took 12.9 h | `arsenal/lanes/` |
| `imgdiff` with the SwiftShader noise floor | Written 135 times by 42 agents | `arsenal/lanes/` |
| `fetch`: a yt-dlp wrapper (newest binary, JS runtime check, 429 back-off, stops at bot checks) | 48 of 50 downloads got 403 on an old yt-dlp | `scripts/`; installing yt-dlp-ejs is Daniel's call |

---

## Part 7: Daniel's decisions (none of them block v0)

1. **OBS:** studio Part 3.3, about 30 minutes: Advanced output, 6 named tracks, 1 s keyframes, 48 kHz, fix the broken
   Desktop Audio device. Then run the drill and send me the file name.
   - Until then, every recording has one mixed track. Stems (L1) are the only way to separate voice from game.
2. **Facecam:** off the minimap, or record study sessions in the facecam-free "League clean" scene.
3. **Replays for study:** Fog of War set to your team, so the review only judges what you could see.
4. **Two user environment variables:**
   - `ARSENAL_FFMPEG` = the StemRollerTrio `ffmpeg.exe`;
   - `PYTHONUTF8=1`.
5. **Packages for the house Python 3.11:**
   - `scenedetect==0.7.1` (BSD-3);
   - `rapidocr==3.10.0` with `--no-deps` plus its non-OpenCV dependencies (Apache-2.0). This protects cv2 4.13;
   - `pymediainfo==7.0.1` (MIT);
   - later, `opentimelineio`.

   Each has a working fallback, so saying no costs a little accuracy, not a feature.
6. **Tonight's leftovers, keep or delete:**
   - about 2.2 GB in `C:\Users\L5\.cache\huggingface\hub` (faster-whisper base and large-v3-turbo, Florence-2-base). The
     turbo model is the one P10 uses for final captions;
   - the native Ollama app (idle, 43 MB);
   - the whisper model copied from Sky's Steam folder (delete);
   - the research venvs under `SP\primitives\venvs` (`ot`, `tv`).
7. **The two drafted skills** (`video-work`, `vod-review`): read them before they go into `.claude/skills/`.
