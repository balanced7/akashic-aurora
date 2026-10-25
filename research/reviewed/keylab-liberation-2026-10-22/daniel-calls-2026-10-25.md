# Daniel's calls and the first real-GPU stage timing (2026-10-25)

Daniel's answers to the open questions from the Lasers v2 spec (vj-lasers-v2-and-colour-themes-2026-10-24.md section 6)
and the Virtual Stage review, given in chat on the morning of 2026-10-25. His words are verbatim; the design that
follows from each is Vandor's, and the integration lanes apply it.

## The first real-GPU timing (Virtual Stage v0, his own Chrome)

Daniel, verbatim: "definitely felt smooth! look at that frametime, 5ms sheesh"

His screenshot of the stage's HUD (demo show, the drop, camera FOH_WIDE, laser look "ceiling", 40 beams, 8 hazers,
haze 49% to 55%): render 3825x2030 at 6.3 ms CPU+GPU a frame, and the flash limiter showed "no limiter interventions"
over 11,125 judged frames. The v0 builder's estimate was about 3.4 ms at 1080p on an RX 6600-class card; the real run
is near 4K. This is the first measurement on real hardware (the stage was served from the local-only preview branch
preview/vj-night-2026-10-25 on port 8796).

## The Lasers v2 calls

1. **Tap and FL.** Asked whether a Tap press should keep changing FL's tempo. Daniel: "for q1, only tempo for vfx."
   Done: the house FL script swallows Tap (TAP_TO_FL = False, commit 17613a6c); the VJ engine's tap tempo is the only
   reader. Note: on 2026-10-25 FL still had Arturia's "KeyLab mk3" script selected for the DAW input, so this takes
   effect once "Aurora KeyLab (user)" is selected there.
2. **The ONE.** Asked whether he starts tapping on beat 1 of a bar. Daniel: "not sure, perhaps we can trigger the tempo
   tap with a drumpad instead, idk lets just design an initial version then we can fine tune after."
   Initial version: the Tap button (CC 23) and pad 12 (the pad he wanted to reclaim) both tap tempo for the visuals
   only; the first tap of a run marks the ONE (the engine clock's --tap-one); a single later tap re-phases the beat
   (round 3 of the engine-clock lane). To be tuned with him after he plays it.
3. **Controls.** Fader 1 becomes Theme (Hue A and B move into Custom), the dial becomes the laser gate picker.
   Daniel: "3. yes i like that"
4. **Velocity tiers on the laser pad.** Soft = single, medium = one-two, hard = triple, or the reverse.
   Daniel: "4. option 1!" -- soft = single, medium = one-two, hard = triple.

## The stage

His build order for the stage (verbatim): "if I was building this I would start with getting the overall set and scene
and make camera movements. then I would add mounting points for lasers in the scene, then I would code different laser
parameters and give myself the ability to tie groups of lasers together and allow them to play various "animations"
and triggers"

His pointers after seeing v0 (verbatim): "The parts that are super impressive to me from the light shows are when they
have 3 levels of light all shooting over the crowd, you have the vertical elements, you can have top, midle then bottom
pan up and down sequentially. or horizontal flash and pan, then vertical 1, 2, 3 then back to lasers, then a cool
pattern of lights from the circular halo. The effects they had on the rings also looked sick!"

And where the levels are (verbatim): "the three levels seems to be altitudes on the circular array where they group the
lasers into thirds. i think it was once per beat. we could also do top and bottom, middle, top and bottom again"

These drive the Virtual Stage v1 workflow (stage-v1-phrases).

## Still open

Rewind and fast-forward in VJ mode only or always; Laser Sky's blue air as an exception to the black-room rule; the haze
module's cyan-white (pale and bright, or saturated); when to restart the machine; clearing the finished worktrees.
