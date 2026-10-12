# The house EDL (edit decision list)

One JSON file is the whole edit. The agent writes it, a validator checks it, the renderer obeys it,
the editor UI can load it, and the receipt points at it. Fields marked (vu) come from
browser-use/video-use; the rest are house additions.

```json
{
  "version": 1,
  "sources": {"rec1": {"path": "E:/Video Output E/2026-10-11 17-51-11.mkv", "sha256": "...", "duration": 2412.5}},
  "output": {"preset": "shorts_1080x1920", "fps": 60},
  "ranges": [
    {"source": "rec1", "start": 1731.60, "end": 1752.10,
     "audio": {"game": 0, "mic": 1, "discord": null},
     "beat": "hook", "quote": "first words said", "reason": "why this range (vu)",
     "reframe": {"mode": "stack", "crop": [656, 0, 608, 1080]}}
  ],
  "audio_mix": {"game": -6.0, "mic": 0.0, "discord": -9.0, "target_lufs": -14, "true_peak": -1.0},
  "grade": "none",
  "overlays": [{"file": "overlays/title.mov", "start_in_output": 0.0, "duration": 2.5}],
  "subtitles": "edit/master.srt",
  "total_duration_s": 20.5
}
```

- `audio` maps each named track to the source's audio stream index (`0:a:N`); `null` mutes it.
- `audio_mix` gains are in dB, applied per track BEFORE the mixdown; loudness is normalised on
  the mix.
- `beat`, `quote` and `reason` make the EDL readable as a script: Daniel reviews the reasons, not
  the timecodes.

## Validation (run before every render; fail closed, say exactly what is wrong)

- every `source` exists and its sha256 matches (else: re-probe, never guess);
- `0 <= start < end <= duration` for every range; ranges of one source do not overlap unless
  marked `"repeat": true`;
- no range edge falls inside a word (from the cached transcript), unless `"split_word_ok": true`;
- every audio index exists in that source (`ffprobe -select_streams a`);
- `total_duration_s` equals the sum of the ranges (to 1 frame);
- the preset's platform limit holds (Shorts <= 180 s, TikTok copy <= 10 min as arsenal tiktok uses);
- overlays end before the output ends; subtitle file exists.

Write errors like Kinocut does: name the field, the bad value, and the allowed values.

## Handing the cut to a real editor

OpenTimelineIO is the interchange: a Python script can build the same timeline as `.otio`,
which DaVinci Resolve imports natively (since 18.5) and Kdenlive natively (since 25.04); the OTIO
adapters convert to FCPXML, AAF and CMX 3600 EDL. Export OTIO when Daniel wants to finish in an
NLE; render with ffmpeg when he wants a file.
https://opentimelineio.readthedocs.io/en/latest/tutorials/adapters.html
