# Look at a video cheaply

`FF` below = `C:/Users/L5/AppData/Local/StemRollerTrio/ffmpeg/bin/ffmpeg.exe`.

## The ladder (stop at the first rung that answers the question)

1. **Probe** - `py -m arsenal probe <file>`: duration, fps, streams (how many audio tracks?), codecs.
2. **Shot list** - only for EDITED video (montages, YouTube uploads). A raw gameplay or screen
   recording is one continuous shot: skip to rung 3 or to the event signals in highlights.md.
3. **Storyboard sheet** - `py -m arsenal storyboard <file>`: motion-scored segments, de-duplicated
   picks, a contact sheet, and a manifest that states what fraction of the take it shows.
4. **Filmstrip + waveform for one window** - only at a decision point (a cut, a fight, a death).
5. **Single frames** - `FF -ss T -i src -frames:v 1 -q:v 2 out.jpg` (seek BEFORE `-i`).

## Scene / shot detection

- **House default (game edits):** one 320 px decode pass printing every frame's score:
  `-vf "scale=320:-2,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=scene.txt"`.
  A fixed 0.3 threshold found 29 of ~154 real cuts in a game montage; the spike rule finds them:
  cut = score >= 0.30, OR score >= 0.12 AND >= 8x the median of the surrounding +-1 s
  (analyze_video.py `detect_cuts`, 152/154 of scdet's cuts). One-frame ability flashes also spike:
  expect a few false cuts.
- **scdet** (`-vf "scale=320:-2,scdet=threshold=10"`) is the built-in cross-check.
- **Gradual transitions** (dissolves, fades): PySceneDetect's HSV ContentDetector struggles
  (F1 < 0.6 on the SHOT set); TransNetV2 / AutoShot are the neural options (AutoShot +4.2 F1 over
  TransNetV2). Install only when dissolves matter. https://arxiv.org/abs/2304.06116
- **Shot midpoint** is the representative frame (avoids transition blur).

## Contact sheet (if arsenal storyboard does not fit)

Tested 2026-10-12 (5 min of a 1080p60 HEVC recording -> one 1920x900 sheet):
```
FF -hwaccel d3d11va -ss 0 -t 300 -i src -vf "fps=1/10,scale=320:-2,drawtext=fontfile='C\:/Windows/Fonts/segoeuib.ttf':text='%{pts\:hms}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=6x5" -frames:v 1 sheet.jpg
```
Every tile carries its time, or a reader cannot cite it.

## Filmstrip + waveform for a window (video-use's `timeline_view`)

```
FF -ss T0 -t D -i src -filter_complex "[0:v]fps=8/D,scale=240:-2,tile=8x1[f];[0:a]showwavespic=s=1920x120:split_channels=0[w];[f][w]vstack" -frames:v 1 strip.png
```
(8 frames x 240 px = 1920 wide, so the waveform width matches.) Add word labels from the
transcript when the window holds speech.

## HUD strips for games (one decode, many crops)

Crop every HUD region you need in ONE pass with `split`, at 1-4 fps:
```
FF -hwaccel d3d11va -i src -an -filter_complex "[0:v]fps=1,split=3[a][b][c];[a]crop=W:H:X:Y[top];[b]crop=...[chat];[c]crop=...[ban]" -map "[top]" top/%05d.jpg -map "[chat]" chat/%05d.jpg -map "[ban]" ban/%05d.jpg
```
ROI rectangles depend on resolution and HUD scale: keep them in ONE named-preset JSON (e.g.
`league_1080p.json`: clock, kill feed, chat, minimap, scoreboard) instead of re-measuring per run.
Measured on Daniel's 1080p replay recordings (2026-10-12): top-centre score + clock
`crop=200:110:860:0`; facecam `crop=495:277:1320:738` (it hides most of the minimap, about
x 1660-1920, y 820-1080).

Label tiles with SOURCE time: after `-ss T` the pts restart at 0, so use
`drawtext=fontfile='C\:/Windows/Fonts/segoeuib.ttf':text='%{pts\:hms\:T}'` (offset = T).
Name the font file: without it this ffmpeg prints "Fontconfig error" and falls back to a serif.

## Using a vision model

Hand it the sheet plus the event list and a question, never raw video. A model reads a labelled
6x5 sheet far better than 30 separate frames.
