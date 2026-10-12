---
name: video-work
description: Use when any task touches video or recorded audio in this house - trimming, cutting, jump cuts, removing silence or filler words, scene or shot detection, contact sheets, "look at / watch this video", grabbing frames, captions or subtitles, shorts / TikTok / Reels / 9:16 reframing, multi-track OBS audio (game, mic, Discord), loudness, highlights or kill clips from gameplay, rendering or exporting, footage search, b-roll, or video metadata. Use BEFORE the first ffmpeg or ffprobe call, before writing any script that shells out to ffmpeg, and before hand-building a contact sheet, frame grab, HUD crop or game-clock OCR.
---

# Video work

**Iron Law: text first, pictures on demand, receipts always.** Read a video as data (probe, word
transcript, shot list, event list) and look at frames only at decision points. Never hand-roll a
primitive the house already has. Every render leaves a receipt, or it is presumed broken.

DRAFT 2026-10-12, route table rewritten the same night onto `arsenal.media` (the toolbox built from this track's
findings). Evidence for every rule is in "Why these rules" below. Daniel reads this before it is installed.

## 0. House facts (stop rediscovering them)

- **Never locate ffmpeg yourself.** `py -m arsenal.media doctor` says which build the house uses and what it can do
  (`--save` remembers the best one); from Python, `arsenal.media.ff.run([...])` runs it with the house flags. The
  house build (N-124319) has libass, scdet, loudnorm, ebur128, libplacebo, h264/hevc/av1_amf and the `whisper` filter.
- **Times are seconds from the file's start** (what a player shows). League game times are `game_t`, file times `file_t`.
- **The toolbox: run these before writing code** (`py -m arsenal.media <verb> -h`, or `py agent_cli.py media <verb>`,
  or the MCP door `py -m arsenal.media.door` with the same verbs as `media_*` tools):

  | need | run |
  |---|---|
  | a file's facts: streams, audio track names, keyframe interval, OBS version, recorded time, kind | `media probe <file>` |
  | remember recordings and query them later | `media import <file or dir> [--quick]`, `media find --kind league_replay` |
  | see a video in ONE image | `media sheet --video <file> --n 30`, `media filmstrip <file> 12:00 12:10` |
  | frames at exact times | `media grab <file> --at 12.5,30 [--crop x,y,w,h] --sheet` |
  | find the cuts (scene detection) | `media shots <file> [--sheet]` |
  | trim to the exact frame, every audio track kept | `media cut <file> 10:00 10:20 out.mkv [--plan]` |
  | audio tracks: loudness, silences, demux, mix | `media audio <file> --loudness`, `media mix ...`, `media peaks ...` |
  | check a finished file | `media qc <file>` |
  | words with timing (VAD on: no hallucinated repeats) | `media words <file> [--track 1] [--span 10:00-12:00]` |
  | League: video time -> game time; Riot events on frames; fights | `media clockmap <file>`, `media events <file> --match <id>` |
  | A/V sync | `media avsync <a> [<b>]` |
  | export: YouTube, Shorts, proxy, alpha | `media export <preset> <src> <out>` |
  | edit: projects shared with Daniel's editor (First Light, Edit mode) | `media edit list|show|add|trim|split|render` |
  | League replay re-shoots | `media replay status|swagger|take|sheet` |
  | still useful, older verbs | `py -m arsenal storyboard` (pacing), `motion`, `floors`, `tiktok` (phone-ready copy) |

- **GPU.** Decode with `-hwaccel d3d11va` (software fallback). Encode previews with `h264_amf`,
  masters with `libx264 -crf 17-18`. DirectML defaults to the integrated GPU: pin the adapter by
  DXGI VRAM (analyze_video.py `dxgi_adapters`). The ffmpeg `whisper` filter says
  `Unsupported GPU: gfx1201` and runs on the CPU (base model: 66 s of audio in 4.2 s).
- **Windows.** Inside filter arguments use `arsenal.media.ff.filter_path(p)` (it escapes the drive colon and
  quotes: `subtitles=filename='C\:/work/cap.ass'`). Never build a path with `"\.."` inside a Python f-string
  (OSError 22, seen 2026-10-12). Run Python with `PYTHONUTF8=1`.
- **MPEG-TS and other index-less files** seek to the next keyframe AT OR AFTER `-ss`; `media` handles it, a hand-rolled
  `-ss` does not. `ffprobe -read_intervals` read open-ended near the end of a file is nondeterministic: read packet
  lists whole.

## 1. Route the task, then read ONE reference file

| the ask sounds like | read |
|---|---|
| look at, watch, what happens, find the cuts, scene detection, thumbnails, contact sheet, HUD crops | [reference/look.md](reference/look.md) |
| cut, trim, jump cut, remove silence / ums / filler / retakes, tighten, rough cut, edit by transcript | [reference/transcript-edit.md](reference/transcript-edit.md) and [reference/edl.md](reference/edl.md) |
| captions, subtitles, SRT, karaoke, word by word, Hormozi style | [reference/captions.md](reference/captions.md) |
| short, TikTok, Reels, Shorts, vertical, 9:16, reframe, crop for phone | [reference/reframe-shorts.md](reference/reframe-shorts.md) |
| audio tracks, mic, Discord, game audio, mixdown, too quiet, loudness, OBS tracks, stems | [reference/multitrack-audio.md](reference/multitrack-audio.md) |
| highlights, best moments, kills, fights, montage, clip it, when did I die | [reference/highlights.md](reference/highlights.md) |
| export, render, upload-ready, YouTube-ready, final, proxy | [reference/export-deliver.md](reference/export-deliver.md) |
| find the clip where, search my footage, b-roll, tag, metadata, index the recordings | [reference/search-metadata.md](reference/search-metadata.md) |
| analyze my gameplay, VOD review, what could I have done better | the `vod-review` skill |

## 2. Hard rules

1. **Sources are read-only.** Outputs go to a work dir (`<source dir>/edit/` or the declared one);
   a finished file is written as `.partial` and renamed when complete (arsenal tiktok's rule).
2. **Multi-track files: always map.** `-map 0` (or `-map 0:v:0 -map 0:a:N`). Without `-map`,
   ffmpeg keeps ONE audio stream (the one with the most channels) and silently drops the rest.
3. **Seek before input.** `-ss T -i src` is fast and frame-accurate when re-encoding.
   `-c copy` cuts on keyframes only: fine for archive splits, never for an edit.
4. **Never cut inside a word.** Snap edges to word boundaries; pad 30-200 ms.
5. **30 ms audio fades at every cut** (`afade=t=in:d=0.03` and `afade=t=out:st=<len-0.03>:d=0.03`);
   50-100 ms `acrossfade` where music is joined.
6. **Render = per-segment extract, then concat.** Subtitles go last, after every overlay.
7. **Cache transcripts per source hash.** Never re-transcribe an unchanged file.
8. **Plan, validate, render.** Write the EDL ([reference/edl.md](reference/edl.md)), run its
   validation, render a 720p preview, and only then the master.
9. **Self-evaluate before anyone sees it:** frames at +-1.5 s around every cut, ffprobe duration
   against the EDL total, `ebur128=peak=true`, `blackdetect` and `freezedetect`. At most 3 fix
   passes, then report what remains.
10. **Receipt per render** (JSON beside the output): inputs (path, size, sha256), the exact
    command, ffmpeg version, the output probe, every check with its number.
11. **Creative calls are proposals; mechanical work is just done.** Which take, which highlight
    leads, pacing: propose to Daniel. Probe, proxy, transcribe, sync, export, QC: do it.

## 3. Budget ladder (cheapest signal first)

game or app event data -> ffmpeg analysis filters (scdet, silencedetect, ebur128, blackdetect)
-> classic CV on cropped HUD strips (template match, OCR) -> CPU speech-to-text on candidate
windows only -> embeddings (SigLIP for frames, CLAP for audio) -> a vision model on a contact
sheet. Never send a whole video to a model: send the sheet plus the event list.

## Why these rules (evidence)

- 1,738 transcripts mined 2026-10-12 (`primitives/skills-workflows/mine_runs.json`): 456 ffmpeg
  calls in 75 sessions. **113 ffmpeg-location probes in 53 transcripts**; the StemRollerTrio path
  hard-coded 140 times in 20. Contact sheets hand-built in **48 transcripts; `arsenal storyboard`
  used in 3.** Game-clock OCR / time sync rebuilt in 19 transcripts; Riot match/timeline handling
  in 40; loudness measured by hand in 17.
- Rules 3-9 follow browser-use/video-use (the most-starred agent video-editing skill, 11.6k stars):
  https://github.com/browser-use/video-use . Receipts and preflight validation follow Kinocut:
  https://github.com/KyaniteLabs/kinocut . Rule 2: ffmpeg's documented default stream selection.
