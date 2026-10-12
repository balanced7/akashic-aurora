# Shorts: 16:9 to 9:16

## First: is it a screen recording of the piano canvas?

Use `py -m arsenal tiktok` - it finds the lit box, trims silence, normalises loudness, encodes
1080x1920. Do not rebuild it.

## Pick the layout (decision tree)

1. **Facecam exists** -> **stack**: facecam on top (~40%), action below (~60%). The viewer sees
   the reaction and its cause at once. https://streamclipping.ai/blog/clip-vertical-9-16-guide
2. **Gameplay, no facecam:**
   - League with the camera locked: the champion stays at (or very near) screen centre, so a
     fixed centre crop follows the action for free (check one frame first: a slight vertical
     offset is normal). Re-composite the HUD a centre crop throws away (kill feed,
     minimap, the clock) as small insets from the same frame (xstack / overlay of a second crop).
   - Free camera: track the subject (below) or use the fit layout.
3. **Talking head / people:** one fixed crop per shot around the faces (FrameShift's method:
   scene-detect, detect faces/objects on up to 150 frames, weighted centroid, one crop per shot).
   Cheap, CPU-only, never wobbles. https://github.com/fralapo/FrameShift
4. **Moving subject:** detect + track + smoothed camera path (YOLO11-seg + ByteTrack + MediaPipe
   face/pose, presets for talking head / sports / movie-locked-per-shot).
   https://github.com/KazKozDev/auto-vertical-reframe
5. **Nothing can be cut:** fit + blurred fill (`split[a][b];[a]scale=1080:1920,boxblur=20[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`).

## Daniel's League recordings (measured 2026-10-12 on `2026-10-11 17-51-11.mp4`, 1920x1080)

- The facecam is already composited in: `crop=495:277:1320:738`. So the stack layout comes from
  ONE file (tested, renders 1080x1920):
  ```
  -filter_complex "[0:v]split=2[a][b];[a]crop=495:277:1320:738,scale=1080:604[cam];[b]crop=886:1080:X:0,scale=1080:1316[game];[cam][game]vstack"
  ```
  Choose X so the game crop holds the action AND does not reach the facecam box
  (x + 886 <= 1320 when the crop's rows include y >= 738), and keep the replay control bar
  (bottom ~70 px) out of frame.
- These files are recordings of the REPLAY viewer with "Manual Camera": the champion is NOT
  centred, so a fixed centre crop will miss the action. Two fixes: (a) track the champion's
  health bar / name plate (template match) and smooth the crop; (b) better, re-record the moment
  from the replay with the camera attached to his champion via the Replay API (`/replay/render`,
  enabled by `EnableReplayApi=1` under `[General]` in the game's `game.cfg` - Daniel's setting to
  change). GET `/replay/render` first and use the field names it returns.
- Hide the replay interface (timeline, controls) before recording footage meant for posting.

## Rules

- Smooth any moving crop (median over ~0.5 s, then a dead zone: do not move for < 3% of width).
  A jittering crop reads worse than a static one.
- Re-check captions and insets against the safe zones in captions.md AFTER reframing.
- Gaming clips: 20-40 s is the usual target (setup + payoff); no single length wins outright.
- Export with the `shorts_1080x1920` preset in export-deliver.md.
