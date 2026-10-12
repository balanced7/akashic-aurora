# Export, QC, receipt

## Presets (name them in the EDL's `output.preset`)

| preset | video | audio | notes |
|---|---|---|---|
| `youtube_16x9` | libx264 High, `-crf 18 -preset slow -pix_fmt yuv420p`, closed GOP = half the frame rate (`-g 30` at 60 fps), source fps | AAC-LC 48 kHz stereo 384k | `-movflags +faststart`; loudness -14 LUFS / -1 dBTP |
| `shorts_1080x1920` | same, 1080x1920, 30 or 60 fps | AAC-LC 48 kHz 256-384k | <= 180 s; safe zones per captions.md |
| `tiktok` | use `py -m arsenal tiktok` (CRF 17, AAC 256k, -16 LUFS, `.partial` then rename) | | piano canvas recordings |
| `preview_720p` | `h264_amf -quality speed`, 1280x720 (or 720x1280) | AAC 128k | for self-eval and Daniel's first look; never published |
| `proxy_scrub` | libx264 `-g 12 -bf 0`, <= 960 px wide, <= 30 fps, yuv420p (all-intra `-g 1` for frame-exact scrubbing) | AAC 128k | for the browser editor; HEVC 60 fps originals scrub badly in a browser |
| `nle_handoff` | keep the source video stream | PCM WAV per track | with the OTIO timeline (edl.md) |

YouTube's own recommendation for these settings: https://support.google.com/youtube/answer/1722171

## QC checklist (all numbers go in the receipt)

```
- [ ] duration: ffprobe output duration == EDL total_duration_s (+- 1 frame)
- [ ] streams: expected count and codecs; audio 48 kHz; no stream dropped (multi-track!)
- [ ] loudness: ebur128=peak=true -> integrated LUFS within 1 LU of target, true peak <= -1 dBTP
- [ ] black: blackdetect=d=0.5:pix_th=0.10 -> no unplanned black runs
- [ ] freeze: freezedetect=n=-60dB:d=2 -> no unplanned frozen runs
- [ ] silence: silencedetect=noise=-50dB:d=2 on the output -> no unplanned dead air
- [ ] cuts: a frame at +-1.5 s of every cut viewed (filmstrip, look.md); no pop at any cut
- [ ] captions: inside the safe zone, never under an overlay, spelling checked
- [ ] first and last 2 s viewed (the hook and the ending are where errors hide)
```
Three passes at most; then ship the preview with the open items listed.

## Receipt (`<output>.receipt.json`)

```json
{"tool": "video-work/render", "created": "2026-10-12T03:10:00", "ffmpeg": "N-124319-gb801f1fe6d-20260503",
 "edl": "edit/edl.json", "cmd": ["...exact argv..."],
 "inputs": [{"path": "...", "size": 0, "mtime": "...", "hash": "sha256:... | quick:size+first8MB+last8MB"}],
 "output": {"path": "...", "size": 0, "sha256": "...", "duration": 20.5, "streams": ["h264 1080x1920 60", "aac 48000 2ch"]},
 "checks": {"lufs": -14.2, "true_peak": -1.3, "black": [], "freeze": [], "duration_delta_s": 0.0, "cuts_viewed": 7}}
```
Full sha256 for outputs; for multi-GB sources a labelled quick hash is acceptable. The receipt is
what lets a second agent (or Daniel) verify the render without re-running it - Kinocut's
"Video Receipt" idea, and the house drill doctrine. https://github.com/KyaniteLabs/kinocut
