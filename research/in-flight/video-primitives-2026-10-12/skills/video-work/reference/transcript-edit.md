# Edit by transcript (Descript-style, local)

`FF` below = `C:/Users/L5/AppData/Local/StemRollerTrio/ffmpeg/bin/ffmpeg.exe`.

## Pipeline

```
transcribe (word level, cached) -> pack (one line per breath group) -> propose strategy
  -> EDL (edl.md) -> validate -> render 720p preview -> self-eval (<= 3 passes) -> master
```

1. **Transcribe** - pick one:
   - `py -m arsenal.stt <audio> <stem>`: faster-whisper small, int8, CPU. Word probabilities,
     `(?)` on unsure words, an ear-check note on letters that rhyme with "ee". The default.
   - ffmpeg `whisper` filter, already in the house ffmpeg (needs a ggml model file):
     `-af "aresample=16000,whisper=model=ggml-base.bin:language=en:queue=20:max_len=1:destination=words.json:format=json"`.
     66 s in 4.2 s on CPU with base. `max_len=1` gives per-word lines, but word times are
     interpolated and the 20 s queue snaps segment edges: use it for search and rough cuts, not
     for caption timing. Add `vad_model=` to segment on silence.
   - whisper.cpp with Vulkan (not installed; the GPU route on AMD): `-dtw large.v3.turbo -ml 1 -ojf`
     gives DTW word timing. An RX 580 transcribed 15 min with large-v3-turbo in 308 s.
     https://github.com/ggml-org/whisper.cpp
   - Transcribe the **mic track** (or the vocals stem), never a mix with game audio or music.
2. **Pack** - arsenal.stt's `.cadence.txt` already is the packed form: a new line at every pause
   >= 0.6 s, each line starting with its time. That file, not the JSON, is the editing surface.
3. **Find cut candidates**
   - silences >= 400 ms between words;
   - fillers: um, uh, er, "you know", "like" (only when not a verb), "so" at a sentence start;
   - retakes: the same phrase restarted within ~10 s - keep the LAST complete take;
   - no speech at all: `silencedetect=noise=-30dB:d=0.5`, keep 0.1-0.2 s either side.
4. **Snap and pad** - edges on word boundaries, 30-200 ms padding (auto-editor keeps 0.2 s;
   plosives and breaths start before the waveform crosses the threshold).
5. **Render** - per range:
   ```
   FF -ss S -to E -i src -map 0:v:0 -map 0:a:N -af "afade=t=in:d=0.03,afade=t=out:st=<E-S-0.03>:d=0.03" \
      -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 192k -ar 48000 seg_007.mp4
   ```
   then the concat demuxer with `-c copy` (safe: every segment was encoded with the same settings).
6. **Subtitles** - write the master SRT on the OUTPUT timeline:
   `out_t = word.start - range.start + range.output_offset`, and burn it last.

## Off-the-shelf alternatives worth knowing

- **auto-editor** (pip): silence / motion cutting that EXPORTS an NLE timeline (Resolve, Premiere,
  Final Cut, Kdenlive, Shotcut). `auto-editor in.mp4 --edit audio:threshold=0.04 --margin 0.2s --export resolve`.
  Use it when Daniel wants to finish in a real editor. https://github.com/WyattBlue/auto-editor
- **Smart cut** (LosslessCut's method): re-encode only the GOP at each edge, stream-copy the middle.
  Worth it for long ranges of high-bitrate masters. https://github.com/mifi/lossless-cut
- Open text-based editors to borrow UI ideas from (the studio track owns the editor):
  Open Script Editor (tokens tile the whole file, so a text range is always a media range; every
  edit is a JSON op over local HTTP) https://github.com/rbrown101010/Open-Script-Editor ;
  Rescript https://github.com/birhantprkc/rescript

## Approval

Daniel approves the STRATEGY in one paragraph ("keep the three stories, drop the setup, 70 s").
He does not approve individual cuts. While he is away, stop at the 720p preview plus the receipt.
