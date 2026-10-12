# Multi-track audio and trimming

## What the recordings hold today (probed 2026-10-12)

`E:/Video Output E/2026-10-11 *.mp4`: HEVC 1920x1080 60 fps + ONE Opus stereo 48 kHz track.
Game, mic and Discord are already mixed together. Two consequences:

- To separate voices from game sound now, use stem separation (analyze_video.py: htdemucs or
  UVR-MDX on DirectML, vocals vs the rest). It is good, not perfect: announcer lines and champion
  voice lines land in "vocals".
- For truly separate tracks, OBS must record them (Daniel's setting, propose, do not change):
  Settings > Output > Recording > Audio Track 1-4 on; Track 1 = full mix (plays everywhere),
  Track 2 = game (Application Audio Capture of the game), Track 3 = mic, Track 4 = Discord
  (Application Audio Capture of Discord, with Desktop Audio off). OBS cannot unmix Desktop Audio
  after the fact. https://clip.dor.gg/en/blog/separate-game-audio-mic-tracks

## Rules for every multi-track operation

1. **Map explicitly.** `-map 0` keeps everything; `-map 0:v:0 -map 0:a:2` picks. Without `-map`,
   ffmpeg keeps ONE audio stream and drops the others without a warning.
2. **Trim every track with the same in/out** in the same command, so they stay in sync:
   `FF -ss S -to E -i src -map 0 -c:v libx264 -crf 18 -c:a aac -b:a 192k out.mkv`
   (audio is re-encoded, so the cut is sample-accurate; `-c copy` would cut audio on packet edges).
3. **Keep tracks separate through the edit; mix down last.** Per-track gain in dB from the EDL's
   `audio_mix`, then `amix=inputs=N:normalize=0` (normalize=1, the default, divides levels by N
   and makes everything quieter), then loudness on the mix.
4. **Fades on every track at every cut** (30 ms), or the quiet track pops.
5. **Inspect a track before trusting it:** `FF -i src -map 0:a:N -af ebur128 -f null -` (is it
   silent? clipped?) and `showwavespic` for a picture of all tracks stacked.
6. **For speech-to-text, use the mic track (or the vocals stem), mono 16 kHz:**
   `-map 0:a:N -ac 1 -ar 16000 mic16k.wav`.
7. **Container:** keep MKV while editing (holds any codec, survives crashes); remux to MP4 at the
   end. Opus inside MP4 is fine for browsers but some NLEs reject it: give NLE-bound copies AAC
   or PCM WAV per track.

## Loudness

- Measure: `FF -i mix.wav -af ebur128=peak=true -f null -` (integrated LUFS, LRA, true peak).
- Normalise in two passes: pass 1 `loudnorm=I=-14:TP=-1:LRA=11:print_format=json`, pass 2 feed
  `measured_I / measured_TP / measured_LRA / measured_thresh / offset` back with `linear=true`.
  One pass routinely lands ~1 LU off. https://32blog.com/en/ffmpeg/ffmpeg-audio-normalization-loudnorm
- Targets: YouTube normalises down to -14 LUFS (never up), so -14 integrated / -1 dBTP is the
  ceiling for uploads; arsenal tiktok uses -16 for phones. Both are fine; never exceed -1 dBTP.
