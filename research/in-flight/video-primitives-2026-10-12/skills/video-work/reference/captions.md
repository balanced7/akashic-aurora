# Captions

## Method (the one everyone converged on)

word timestamps -> group into chunks -> one ASS file -> burn with libass (`ass=` or `subtitles=`)
as the LAST filter. One ASS event per spoken word, the whole chunk shown, the current word
recoloured or scaled: that is the karaoke / "Hormozi" look.
Examples: https://github.com/philippprimisser-max/whisper-word-captions ,
https://github.com/hqman/karaoke-caption

- Timing must come from the audio (word timestamps), never from estimated beats.
- Always also write a plain `.srt` beside the video (platform upload, accessibility, search).
- Run arsenal.stt's ear check on any line it flags before burning it: a burned typo is permanent.

## Styles (presets, 1080x1920 unless stated)

| preset | words per chunk | size | look |
|---|---|---|---|
| `karaoke` (shorts default) | 1-3 | 65-75 px, bold 700-900 | uppercase, white with black outline 4-6 px, current word in accent colour |
| `phrase` | 3-8 | 60-65 px | sentence case, semi-transparent box |
| `standard` (16:9) | up to 2 lines of ~42 chars | 48-56 px at 1080p | bottom-centred, box |
| `minimal` | full phrase | 40 px | lower third, no box |

Font sizes and weights from https://blitzcutai.com/blog/best-caption-size-youtube-shorts-2026
(start 65 px, minimum 55, hard maximum 100; bold reads better on phones).

## Placement (safe zones on a 1080x1920 canvas)

- YouTube Shorts: keep text >= 300 px above the bottom and >= 120 px from the top; usable centre
  about 984x1500. TikTok: keep ~140 px top, ~400 px bottom, ~180 px right clear. Reels covers the
  most at the bottom (~500 px). One placement that works on all three: centred, baseline about
  1150-1300 px from the top.
  https://imagevideofit.com/guides/youtube-shorts-safe-zone , https://brandeal.ai/en/blog/tiktok-safe-zone-guide
- Never put captions and a lower-third or facecam in the same band.

## ASS essentials

`PlayResX: 1080`, `PlayResY: 1920` so sizes are in output pixels; `Alignment: 2` (bottom-centre)
plus `MarginV` to lift into the safe zone; colours are `&HAABBGGRR` (BGR order). Karaoke word
highlight = one Dialogue per word, the current word wrapped in `{\c&H0000D7FF&\fscx115\fscy115}...{\r}`.
Burn: `-vf "ass='C\:/work/edit/cap.ass'"`. Tested 2026-10-12: WITHOUT the `\:` escape this ffmpeg
fails with `Unable to parse "original_size" option value "/Users/..."` (the colon splits the
option); with it, the highlighted word renders.
