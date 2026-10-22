# Daniel's asks, 2026-10-22 session (curated by Vandor from the live conversation, in order)

Scope: the KeyLab / sound / VFX / FL vision. Quotes are his words as typed (typos kept); [paraphrase] marks where only the gist is held.

## Why it started
1. "I've been feeling really guilty about having a $1300 keyboard and not using any of its fancy functions. If arturia refuses to build actually useful FL studio integration, we will build it ourselves."
2. "this is really important to me, understanding software is not illegal, can you probe and understand the full arturia software suite and documentation for the keylab. I want us to understand our full surface."

## Sound, samples, collaboration (morning ideas)
3. "a music collaboration site where users can upload flp templates and we could perhaps make a project conversion kit where I upload an flp but the users of the site can download a project file in their preferred daw like ableton or reason"
4. "I am thinking of how to 'Splice-ify' sound chains and buildups / structure."
5. "how can we make it easy to assign whatever I want to the drum pads on my arturia ... no easy way to drag and drop samples on to the drumpads and controll adsr or to map addictive drums notes to specific pads"
6. "on other keyboards there is a shift button you can press to play a piano note then tap a pad and then the pad will trigger that note, is there any way to do that with the arturia? Should we make our own vst to make this easier?"
7. "Can we make it so I can drop samples onto the pads, easily select color, velocity controlls as well as adsr settings? The built in methods for doing so are incredibly cumbersome and annoying to the point that I have only used it once. their app sucks"
8. "I want a sexy ui that I can just drag and drop samples into on top of the pad to set up drumpads with the manual bund method as well. there are ways of switching modes and pad banks / functions with the arturia, I want us to expose them"

## Light, screen, verbs, limits
9. "perhaps we can even render to the pads as an extension of the keyboard VFX with a fun mode that displays the chord you are playing on the pads, that would be so sick!"
10. "Lets build! Lets also make verbs for interfacing with the keylab and triggering midi and colors, I would love to test latency and rate limits on color updates. It would be even cooler if we can see if we can pipe into the onboard display on the keylab too!"
11. "I want us to play with the send limits for LED information, I want us to learn where the actual limits are through testing, perhaps we can be more clever than the hardware"
12. "it looked uneven, but it did flicker, I want us to test higher and lower so we can track stability, even if its not perfect it could be used for illustrative effect" (his estimate: ~15 ms drift, maybe 9 ms)
13. "can we print to the main lcd? perhaps you can say what test pattern its in the main led"
14. "Keylab Unlocked!!!!! Lets goo!!!! Can we animate to it?" -> "beautifully, flawlessly rendered, 0 ficker! can we make it be a renderable window for our VFX? what if we make a chord viewer straight on the keylab!!!"
15. "the pads changed color and shaper per chord too!!! that was incredible! its so visually stunning!" / "We can come up with cool representations of the chords on the pads with colors and shape schemas"
16. "sustain doesn't have any effect though" (fixed same day: CC64 handling)
17. "it would be cool for 7ths to make a chord be one color on the pads, or perhaps the edges change color, for there to be a region resoponsible for quality, one for note, idk think of a few schemas"

## Music-aware light (Spotify, BPM, chord DB)
18. "how can we see what spotify is playing and know the bpm and track position. I want the led lights to march to the beat changing color as it clicks through, or having an animation ... I would be so hype if we can solve spotify with realtime bpm with an eventual goal of tying into ultimatechords and building our own db showing chord changes in time with the music"
19. "If we can poll a db and run our own test with the starting bpm being the one sourced from multiple db's. Can you keep refining the bpm detect and accuracy?"
20. "this research is important and will help our efforts of making engaging content so I am here for all of it"

## House ergonomics he asked for along the way
21. Attention verb: "if you have something that requres my attention at a specific point in time i can acknowledge it and select an option or click to launch."
22. Media ergonomics: "how can we make it easy for you to get the image when i send it to you? lets fix that ergonomics thing so its quick" / "how can the wake message also give you a direct link to the media file so you can just ingest it immediately, perhaps find for latest created media file could be a crutch" (crutch built: scripts/inbound_media.py)

## The sound room and FL
23. "Lets test the synth, we can use it to just host vst's ourselves, actually wait, lets just build that! so you can invoke kontakt and the piano with effects vst's and EQ's, then we can have the piano arsenal thing be capible of hosting a vst!, we may have a product on our hands!!!!!!"
24. "I don't have all the details on productization figured out and thats secondary, I want this thing we're building, low latency audio play space, where we can craft sounds and IMPORT them to FL, can you imagine the workflows and collaboration?"
25. "THEN we can use the keylab as a vfx device with all the faders and buttons, we can showcase the keylab in the best light and also learn how to powerfully utilize it"
26. "I mean effects chain silly, there are preset files in FL for the mixer, we can make it easy to import and export, or just read and interact with natively" / "both instrument hosting and effects chains, so this would work detached and with FL"

## The UI tie-in and the mandate
27. "We need to tie in our UI work to incorperate the keylab, and for the vfx page and arsenal pages to interact with the keylab display with menus and adaptive beautiful coloring. I am super excited to see what you all make!!!"
28. "I want the full vision, no shortcuts or hedges, every feature you could think of and want. actually spin up a fanout about my preferences and our overall goals and lets set the house at this proper, lets structure this into our overall projects. this may require multiple passes"

# Facts confirmed on the hardware today (receipts in arsenal/keylab + memory keylab-mk3-liberation-2026-10-22)
- Pad grid is 3 across x 4 down, printed labels:  9 5 1 / 10 6 2 / 11 7 3 / 12 8 4  (photo of the 12-colour test). protocol.py's MPC note map, chordview's old 3x4 row-major guess and keylab88mk3.js's 2x6 were all wrong about position; chordview.GRID now carries the photo truth.
- Warm low-saturation colours (amber, yellow, orange, lime) photograph close to white on these LEDs; saturated blues/purples/magentas/pinks/reds read clearly. Palette work must pre-snap to colours the LEDs render well.
- Pad mode selector on the device: left = Arturia Program, middle = DAW, right = Default.
- Popups dismiss after ~1 s; full-screen F2L persists; 100-frame colour cycle at 60 ms spacing rendered with zero flicker.
- Live chord naming from the keybed worked on first try (C, Cmaj9, Em/B, Gaug, Fadd9, Cm9, D#maj9, A#maj9 ...).
- The Windows GS Wavetable synth played a chord ("a chime") when forwarded notes; --sound works.
- Single-pad flicker: host hit every target rate up to 120 Hz; device looked even at low rates, uneven but usable at higher rates.
