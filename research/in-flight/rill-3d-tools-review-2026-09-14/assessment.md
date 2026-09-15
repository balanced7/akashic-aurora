# Rill's three 3D-tool commits: what Vandor thinks

*Peer review, not a gate. Three reviewers ran each tool on real receipts, and a separate checker re-ran their claims. Only claims that survived that check appear below. Where the checker's numbers differed from the reviewer's, I use the checker's.*

**Short version:** Rill is asking the right questions, and he writes receipts that say what they did *not* measure. That is exactly the house style. All three tools were tested on bright, simple, synthetic clips. Our real footage is dark, low-contrast and stutters. Most of the defects come from that one gap, and they are small and fixable. One tool is ready to use tonight (floors, with care). One works on Daniel's hard-cut takes but not yet on Asta's spectacle (storyboard). One needs a rethink before anyone trusts its labels (coupling census).

---

## 1. What each tool is good at

**Storyboard** (`py -m arsenal storyboard`: turns a video into a contact sheet of "moments" plus a JSON list of where things change)
- Small and self-contained: 323 lines, using only numpy and PyAV (a video decoder). The manifest (the JSON summary) records how it sampled the video, and it lists what the tool can't see: audio, strobes and fades, and the fact that the sheet is only a sample.
- Fast. A 2.6 s 4K take is analysed in 0.18 s, with the full sheet in about 0.5-0.8 s. A 217 s 1080p60 take takes 31-34 s for both decode passes.
- Works as designed on content with hard changes. On Daniel's takes, a 56 s take gave 2 transitions and 4 picks, and a 62 s take gave 7 transitions and 8 picks out of 14. On synthetic clips, cuts were found at exactly t=1.0 s and t=2.0 s.
- Hysteresis (it needs a big jump to start a "change" and a quiet stretch to end one) keeps a slow fade as one segment instead of many.

**Coupling census** (`py -m arsenal coupling`: reads each /play shader's text and counts how often it uses the audio inputs)
- Everything it counts is real. All 36 references across the 8 presets were checked line by line, and no declaration or comment was counted as a use.
- Its core idea holds when rendered. A line of the form `col += col * pulse` only brightens the picture: aurora-ribbons' glow line moves pixels 1.87/255 on average, and after subtracting a plain brightness change only 0.29 is left.
- Costs 3.9 ms for the whole bank, and the docstring says plainly that it is only a text scan.

**Floors** (`py -m arsenal floors`: four cheap pixel checks: not dead, not blown out, not flat, readable contrast)
- It does not punish moody scenes. All 43 spectacle stills pass. The darkest has mean brightness 0.0545, 2.7x above the floor. gentle-lake only fails once its exposure is cut to 10%. All 828 frames of the 10 spectacle recordings pass.
- It catches real blowouts without flagging bloom. Clipping is 0.0 on every world still and on every recording frame. It still fails the piano-dev "916-keys" frame, where the keys dissolve into white haze (keyboard band 0.228 clipped), and the jam a9-glass page (0.084 portrait, 0.213 landscape).
- It catches the silent-visualizer voids it was built for: aurora-ribbons silent (peak 0.07), chromatic-bloom silent (peak 0.13), and the play-dev blackout frames (mean 0.005).
- Receipts are honest. Every result carries its threshold and the measured value, so a FAIL explains itself.
- Legibility works when the region is cropped tight to the text. On the portrait "A C E" row, the label present scores 8.87, erased 1.0 and at 25% opacity 2.63, against a pass mark of 4.5.

---

## 2. The real defects, ranked, with a fix for each

1. **Storyboard can't see anything in Asta's spectacle.** Its change thresholds are fixed numbers tuned for hard cuts. On the 1440p take the biggest change score is 0.011, below the 0.02 "something moved" line. On the 4K take it is 0.067, below the 0.08 "transition" line. At every sampling rate, both takes come out as "one settled moment, one pick".
   *Fix:* set the thresholds per take from that take's own typical change level. If the curve is too flat to split, say so instead of reporting "settled". Measure change in small blocks, not across the whole frame, so a key glow isn't averaged away.

2. **The census misses the audio texture, so it mislabels presets.** `u_audio` is the spectrum and waveform image that shaders read from, and 6 of the 8 presets read it. The census says aurora-ribbons is "cosmetic", yet the texture alone moves 22.4/255 and changes 68% of the pixels. Overall, census counts don't predict measured coupling. (The reviewer's claim that the ranking "runs opposite" was too strong: with only 8 presets the correlation is weak either way.)
   *Fix:* count reads of `u_audio` as spectrum or waveform channels, and add a test that pins "aurora-ribbons is not cosmetic".

3. **A take with no video track crashes both storyboard and floors.** `22-43-26 piano.mp4` has audio only, which is exactly the "silently missing video" case, and it produces an IndexError traceback. In floors, one such file aborts a whole batch.
   *Fix:* return a normal FAIL saying "no video stream". `arsenal/analysis.py:159` already does this.

4. **Frame drops pass silently.** Floors reads only the first frame, so a 4K take with 6 frames in 2.75 s (about 2 fps) prints "verdict: pass". Storyboard's biggest "change" in the 4K take is simply the frame after a 1.689 s recorder stall, and the manifest never mentions the stall.
   *Fix:* compare frame count to duration to get the real frame rate. Flag any gap longer than 3x the normal frame spacing as a `capture_gap`.

5. **The census can't tell video mode from visualizer mode, and loses renamed values.** 9 of the 36 references do nothing when a video is loaded; first-light's four band reads live only in its generative (no-video) branch. glitch-blocks copies `u_beat` into `burst` and uses that 9 times. It moves 40.9/255 in video mode, yet the census calls it only "listening".
   *Fix:* follow one step of assignment, report a verdict per mode, or derive the verdict from a render (see ideas).

6. **Storyboard's picks are one sample early.** A transition's thumbnail shows the frame *before* the change. On the synthetic clip, the pick labelled t=1.0 s is still red when blue starts at 1.0 s.
   *Fix:* use the next sample. Better still, show before, peak and after for each transition.

7. **Floors' legibility number measures brightness spread, not text.** A gradient with no text passes at 10.3, while white text covering 1-4.5% of the region fails at 1.0. The number is taken on gamma-encoded brightness but judged against WCAG's 4.5, which assumes linear light: white text on a grey (90) background reads 2.61, while true WCAG gives about 6.9. The CLI default runs this on the whole frame, and 23 of 27 jam screenshots fail at 3.02.
   *Fix:* make `--set canvas` the default and require a region for legibility. Either convert to linear light first, or rename the number to "luma ratio".

8. **The contact sheet is hard to read.** It is 960x180: one thumbnail, two black cells, no timestamps. Cells are always 320x180, so a real 9:16 portrait frame (portrait.jpg is 1080x1920) gets squashed. Repeated strikes merge into one long transition with one pick.
   *Fix:* burn in time and kind labels, keep the source aspect ratio, never leave black cells, and add a minimum number of evenly spaced frames.

9. **Floors has no region preset for full-frame REC and spectacle shots.** 14 of 103 play-dev frames pass on the whole frame but fail once cropped to the canvas, because lit UI or keys hide a dead picture. The existing canvas preset matches the /play page layout only.
   *Fix:* add a spectacle preset, e.g. the sky above the keyboard, `(0,0,1,0.70)`.

10. **Smaller items.**
    - The storyboard manifest's segment lengths overlap: a 62.4 s take sums to 63.4 s. It has no coverage or stride field, and it quietly falls back to 25 fps on the webm.
    - not_blown ignores coloured clipping: cyan, magenta or warm glow at 255 all read 0.0.
    - Floors recomputes brightness four times: 0.26 s per 4K frame, against 0.02 s on a 4x-smaller copy with identical verdicts.
    - Storyboard keeps full-size 4K frames for every pick (24.9 MB each).
    - All three test suites use only bright synthetic fixtures. Pinning a few small real crops would have caught most of the above.

*Left out because they did not survive checking:* the claim that storyboard's duplicate filter merges nebula soft-vs-attack (that pair is kept apart), and the claim that the census's glow pattern lets mirror-hue pass as fake listening (in visualizer mode it is real structure).

---

## 3. Where each tool fits tonight

**Asta's spectacle visual pass (soft vs hard, repeated strikes, portrait framing)**
- *Floors: use it now.* Run `--set canvas` on the stills, plus not_blown on `KEYBOARD_REGION` to catch key-glow blowout; it caught 7 of 39 piano-dev frames. Run legibility on chord glass only with a tight crop.
- *Storyboard: not yet.* On current defaults it reports "nothing happened". Repeated strikes collapse into one transition, and portrait frames get squashed. Keep it away from soft-vs-hard comparisons.
- *Census: not applicable.* It scans /play `.frag` files, while the piano chain passes velocity through textures.
- *Useful context from the reviewer, measured but not re-checked:* the gesture model separates soft from hard well (impact 6.3x at 0.5 s). The visible switches mostly ignore velocity, though: any triad spawns a ring at both v40 and v100, and ring size at 2 s differs by only 1.41x. In Asta's stills, soft to hard mostly raises brightness. Capture a same-velocity control pair before judging any fix.

**Jam A5 recording checks (pixel-exact, can't run with atmosphere on)**
- *Floors fits this gap.* It works on thresholds, not exact pixels, so drifting fog doesn't break it. Use `--set canvas` with a region, not the default, which adds legibility noise.
- *Storyboard, once A5 videos exist:* there are none in `receipts/jam` today (69 files, no video). Its blindness to low-contrast motion probably *helps* here: atmosphere should stay under the thresholds while real UI changes split into segments. That is untested on jam, so treat the first run as a calibration.

**Live sheet music REC (score strip in the canvas)**
- *Floors legibility* with a tight region on the strip, plus an "erased" twin crop as the known-bad case. Watch the grey-background under-reporting (defect 7): a strip on a mid-grey panel could false-fail. The Nashville row is also drawn in the spectacle canvas (`spectacle.js:335`), so give it its own region.
- *Storyboard cells are too small to read notation;* it needs a crop or a wider cell first.

**Recorder first-take frame drops**
- **None of the three catches this today.** Floors passes a take running at 2 fps, and storyboard hides a 1.7 s hole. The fix is small (defect 4: frame count vs duration, plus gap detection). Until then, check frame count by hand.

**Per-take checks before a TikTok post**
- *Today:* floors `--set canvas` on the file, plus a manual frame-count check. Don't trust a bare "verdict: pass".
- *Soon:* a `check_take` that turns no-video into a FAIL, checks the real frame rate, and samples about 16 frames at reduced size (estimated ~0.35 s per take). Pair it with a labelled storyboard sheet as the human glance; it already works well on Daniel's hard-cut takes. TikTok is portrait, so the aspect-ratio fix matters here.
- Note: `E:/Video Output E/arsenal-renders` is empty. The real takes sit at the root of `E:/Video Output E`.

---

## 4. Ideas Rill might enjoy next

- **Slit-scan strip:** stack one row of pixels, e.g. through the particle columns, over time. Restarting animations show up as a sawtooth in a single image.
- **A/B mode:** two takes or stills side by side with a difference heatmap. Split each change into "just brighter" and "actually different shape", as the reviewer's ablation (a switch-each-input-off test) did.
- **A rendered census:** the reviewer's headless harness rendered the whole bank in both modes in 6.3 s. That would make "cosmetic" a measurement rather than a guess, and keep the text scan as a quick pre-check.
- **Calibrate floors from our own receipts:** a PASS set (the 43 stills) and a FAIL set (aurora-ribbons silent, play-dev blackout, piano-dev 916-keys, jam a9-glass), pinned as small real fixtures.
- **Onset-aligned picks:** snap storyboard picks to audio note onsets. Both spectacle fixtures have flat audio, so this needs a fixture with real notes first.

The instinct behind all three is sound, and his own `not_measured` notes already point at most of these fixes. What remains is calibrating them on our dark, stuttering footage.
