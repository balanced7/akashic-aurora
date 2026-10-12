# Metadata, footage search, b-roll

## One metadata record per media file

Sources are read-only, so metadata lives in an index, keyed by a quick hash (size + first and last
8 MB), not beside the file. Every analysis verb writes its part; none owns the whole record.

```json
{"key": "quick:...", "path": "E:/Video Output E/2026-10-11 17-51-11.mp4",
 "probe": {"duration": 2412.5, "video": "hevc 1920x1080 60", "audio": [{"index": 0, "codec": "opus", "ch": 2, "name": "mix"}]},
 "recorded_at": "2026-10-11T17:51:11", "kind": "league-replay | league-live | piano | talk | other",
 "game": {"match_id": "NA1_...", "champion": "Draven", "role": "bottom", "result": "win", "rank": "Silver I"},
 "clock_map": "derived/clock_map.json", "events": "derived/events.csv",
 "transcript": {"words": "derived/mic.words.json", "cadence": "derived/mic.cadence.txt", "engine": "faster-whisper small"},
 "shots": "derived/shots.csv", "storyboard": "state/arsenal/storyboards/<stem>/storyboard.json",
 "chapters": [{"t": 0, "title": "Laning"}, {"t": 845, "title": "First dragon fight"}],
 "highlights": [{"start": 160.1, "end": 180.0, "score": 0.91, "reason": "double kill, loudest moment"}],
 "tags": ["draven", "double kill"], "notes": "free text from Daniel"}
```

## Chapters

- YouTube description chapters: first line `00:00`, at least 3 chapters, each >= 10 s.
- Embedded MP4 chapters: an FFMETADATA file
  (`;FFMETADATA1` then `[CHAPTER]` `TIMEBASE=1/1000` `START=` `END=` `title=`) muxed with
  `FF -i video.mp4 -i chapters.txt -map 0 -map_metadata 1 -map_chapters 1 -c copy out.mp4`.

## Search by meaning ("the clip where I flash over the wall", "b-roll of a sunset")

- Visual index: one frame per shot (the midpoint), or one every 2-5 s for continuous gameplay;
  embed with an image-text model (SigLIP-2 or OpenCLIP ViT-B/32; CPU is fine at these rates).
- Text index: transcript chunks of ~400 characters with one segment of overlap.
- Audio index (optional): CLAP embeddings per 5 s for "crowd cheering", "explosion", "laughter".
- Query both indexes with the same text, bucket hits into 5 s slots, score
  `w_visual * visual + w_text * text`, and return the per-signal "why". Weight visual high for
  b-roll, text high for talks.
  https://dev.to/masonwritescode/build-semantic-search-inside-video-shot-embeddings-transcript-chunks-fused-on-the-timeline-2nbb
- Scale: tens of thousands of vectors fit in a `.npy` plus a JSON row list; reach for a vector
  database only past that. Choose the embedding model once: changing it means re-embedding all.

## B-roll matching

For each script line or transcript chunk, query the visual index and propose the top 3 shots
with their scores; Daniel picks. Avoid generic filler (a person at a laptop, glowing brains,
slow scrolls with nothing new); prefer real screenshots, UI state changes and receipts.
https://github.com/Bomx/super-video-maker-skill
