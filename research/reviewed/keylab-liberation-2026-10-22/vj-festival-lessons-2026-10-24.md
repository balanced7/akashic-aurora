# What the best VJ setups and festival VFX teach the KeyLab VJ rig (2026-10-24)

Workflow run wf_a869e576-fa4 (task w4km7l10p): three research angles and a synthesis, all verbatim below; local scratch paths shortened. Sources are cited in each report; copyright: summaries, at most one short quote per source.

Daniel (verbatim, 2026-10-24): "The VJ thing is so cool!!!!! How do we make the effects feel more impactful and make the vj sets even more reponsive!" ... "I think all the effects should be non static like the lasers where repeated triggers don't do the exact same thing in the exact same space. what can we learn from the best vj setups and from festival vfx?" and his north star: "The overall design vision is to trigger a vast array of visual effects through a simple interface and combos, for the variety and fidelity to be high"


---

## The synthesis (verbatim)

# VJ research synthesis: making every hit land differently, and land harder

For Daniel, 2026-10-24. Three researchers reported. I re-checked every claim a recommendation below depends on against its own source: manuals, the artists' and designers' own interviews, papers, and our code. Anything I could not confirm is listed at the end and was not used. This does not look at the recording of your set; that is a separate step.

How sure I am:
- **[H]**: I read the primary source myself.
- **[M]**: a secondary source, or only a summary.
- **[L]**: my own idea or a starting number to tune by ear.

---

## Why the lasers already feel alive (checked in our code)

Three things happen on every laser hit (`arsenal/web/vj.js` lines 1258-1265):
1. **It starts from a new place.** Each hit takes the next of 4 starting points in turn: bottom, left, right, top.
2. **The sweep starts at a different point.** A per-hit "seed" sets where the sweep begins. A seed is a number that picks the dice roll; the same number always gives the same roll.
3. **Harder hits are bigger.** More beams (3 to 12), a wider fan, faster movement.

The other pads lack most of this:
- **Shockwave** only moves within about 15% of the centre. **Particles** move within about 25%.
- **Strobe** bars restart at the same point every time (line 1304).
- **Kaleidoscope** always starts at angle 0, from the centre (line 1327).
- **Glitch** varies with the clock, not with the hit (line 1330).
- **Freeze** always zooms from the centre (line 1334).
- **Flash** and **invert** are the same full screen every time.
- The laser's 4-step cycle is fixed, so after four hits it becomes predictable.

One mismatch to know about: in the code today, pad 11 is "kill" (fade to black on the next beat) and pad 12 is "next set" (`vj-core.js` line 384). Invert exists as an effect but is not on a pad by default. Zoom punch does not exist yet, so it is a new build. Keep "kill" somewhere, maybe a transport button. A fade to black on the beat is exactly the "dark before the drop" move in Lesson 2.

---

## 1. THE TEN LESSONS

**1. Black space is what makes a hit land.**
- Rick Jacobs (Nicky Romero's VJ) says don't stack six visuals and mix them every beat: "black is your friend." [H] https://resolume.com/blog/14343
- Ed Warren (lights for Four Tet, Fred again.. and Skrillex at Madison Square Garden) keeps to two colours at once at most, follows the off beat, and keeps the look sparse and uncluttered. [H] https://edm.com/interviews/skrillex-fred-again-four-tet-msg-rave-how-ed-warren-designed-lighting-lasers/

**2. Hold the big thing back, then reveal it at the last moment.**
- At Madison Square Garden, Warren kept a warm "house lights" look for 90 minutes. Then he cut it on the drop when Four Tet signalled, and hit the rainbow lasers.
- He hid the mirrorballs in shrouds and lowered them in the dark, so they stayed a secret until used.
- His strobe rule is to wait for the last possible moment, then "save something for the next drop, and the next." [H] same interview
- Qlimax 2023 was designed around "the contrast between light and darkness." [H] https://www.syncronorm.com/newsitem/qlimax-2023-interview

**3. Big effects wear out, so ration them.**
- A special-effects company puts it plainly: fire cryo on every chorus and "by song four the crowd stops reacting." [H] https://pyrotecnico.com/news/how-special-fx-shape-live-concerts/
- Corbin Sharpe (lasers for Levity) says that with a full crew, a bass hit might go to the strobes while the lasers wait for their own moment, so every part of the show gets a turn. [H] https://edmidentity.com/2026/01/22/levity-lasers-corbin-sharpe-interview/

**4. Breaks and drops should look like different worlds.**
- In Romero's show, break visuals are often desaturated, black-and-white and realistic. Drop visuals are flashing neon and abstract shapes. [H] (Jacobs, above)
- Research on dance music (Solberg 2014) explains why this works. Tension builds when the bass and kick are taken away and the drums speed up in a "drum roll". The peak comes when the bass and kick return. [H] https://dj.dancecult.net/index.php/dancecult/article/download/451/457

**5. The music decides *when*; you decide *what*.**
- VJ 0xf8 says the audio sets the timing and speed of her effect changes, but she picks which effects are affected.
- Her partner Synnack sends the kick, snare and drum-loop levels as numbers to her visuals. [H] https://www.ableton.com/en/blog/audio-reactive-visuals-interview-synnack-0xf8/

**6. Know where you are in the song, not just where the beat is.**
- deadmau5's lighting desk receives the song, the BPM and the current bar position, so "Joel can change the set overnight" and the show still works the next day. [H] https://plsn.com/articles/designer-insights/deadmau5-cube-v3-tour/
- Excision's system reads his song position, his faders and which deck is live. [H] https://resolume.com/blog/14554
- rekordbox already labels every part of a track (Intro, Up, Down, Chorus, Bridge, Verse, Outro) and rates its mood HIGH, MID or LOW. [H] https://cdn.rekordbox.com/files/20241216130922/rekordbox7.0.7_lighting_operation_guide_EN.pdf

**7. Vary where it lands, not what it is. And bring the look back when the section comes back.**
- Pro tools change the landing spot, the starting point and how hard it plays:
  - Resolume's Random button, when synced to BPM, jumps to a random *beat* and keeps playing from there. [H] https://resolume.com/support/en/6/video
  - Pangolin's laser software lets you change position, rotation, size, colour and speed while a cue runs, and lets you move a cue between projection zones. [H] https://wiki.pangolin.com/doku.php?id=beyond%3Alivecontrol , https://wiki.pangolin.com/doku.php?id=beyond%3Aeffects
- The counterweight comes from lighting designer Brad Schiller. Keep separate stacks for position, colour and effect, and mix them for new looks all night. But if a look went with the first chorus, repeat it when the chorus returns, because audiences feel connected through that. [H] http://www.lightingandsoundamerica.com/reprint/Busking.pdf

**8. Designed randomness, not dice.**
- On the grandMA3 lighting desk, the same shuffle number (0 to 32,767) always gives the same order. [H] https://help.malighting.com/grandMA3/2.0/HTML/matricks.html
- Its random generator works as a centre value plus a set amount of spread. A "Random Start" switch makes a run repeatable or different every time. [H] https://help.malighting.com/grandMA3/2.0/HTML/generator.html
- Kate Compton, a procedural-generation designer, warns that things can be mathematically unique and still look the same: "Perceptual uniqueness is the real metric." She recommends shuffling a deck of options so nothing repeats too soon. [H] http://www.galaxykate.com/buildagenerator-kcompton.pdf

**9. Make the hit feel physical: freeze, shake, bounce. This adds impact without adding brightness.**
- Sakurai (the Smash Bros. director): on impact, both fighters freeze for a moment ("hit-stop"). Harder hits freeze longer, up to a cap. They shake during the freeze, and the shake fades out. [H] https://sourcegaming.info/2015/11/11/thoughts-on-hitstop-sakurais-famitsu-column-vol-490-1/
- A study of player reviews (Lin et al. 2022) found that hit-stop, sound matching the picture, and camera work separate well-liked action games from disliked ones. Without hit-stop, attacks feel "soft and powerless". [H] https://arxiv.org/pdf/2208.06155
- Game designer Squirrel Eiserloh's screen-shake recipe:
  - each hit adds to a "trauma" level, which fades over time;
  - the shake grows with trauma squared;
  - shake both position and angle;
  - use smooth noise, not random jumps. [H] http://www.mathforgameprogrammers.com/gdc2016/GDC2016_Eiserloh_Squirrel_JuicingYourCameras.pdf

**10. Leave things to play by hand, with a few big controls.**
- Ghostdad, Porter Robinson's VJ: "I leave myself a few things to do by hand." [H] https://resolume.com/blog/11941
- Eric Prydz's HOLO show is triggered live. Production director Mark Calvert says industry people "thought the whole show was timecoded rather than triggered live." "Timecoded" means pre-programmed to a clock. [H] https://plsn.com/newsroom/projection-connection/avolites-ai-s4-servers-drive-eric-prydz-epic-4-0-usa-tour/
- Scott Pagano prefers "one big slider per effect" that does ten things under the hood. [H] https://derivative.ca/community-post/touchdesigner-performance-interfaces/60765

---

## 2. NON-STATIC BY DESIGN

### The rules (apply to every pad)

1. **The hit lands when you hit.** Never randomise *when* an effect starts. Vary only where, which way, how big, what colour and which version. Viewers are more sensitive to timing when they can predict the beat, so a late visual hurts more than no visual. [H] Vroomen & Keetels 2010, https://repository.tilburguniversity.edu/bitstreams/2ba07297-41a3-4ad8-ba1d-6d06732912bf/download
2. **Two seeds, two speeds** [L]:
   - A *section seed* changes every 8 or 16 bars, or at each new section. It picks the look and the palette, so a section feels like one thing.
   - A *hit seed* changes every press. It picks the position, the angle and the version, so no two hits match.
   - This follows Lessons 7 and 8.
3. **Deal positions like cards.** Each pad has a small deck of 6 to 8 landing spots. No spot repeats until the deck is used up (Compton's deck; Unity's audio "Shuffle" works the same way [H] https://docs.unity3d.com/2023.2/Documentation/Manual/AudioRandomContainer-UI.html). Alternatively, pick from 8 random tries the spot farthest from the last 4 hits [H] https://bost.ocks.org/mike/algorithms/. Keep everything inside the middle 80% of the screen.
4. **Match position to sound** [M/L]: people link high pitch with small, bright and high up. So kick-driven hits lean low and big; hat and screech hits go small and high. [M] Spence 2011, https://link.springer.com/article/10.3758/s13414-010-0073-7
5. **Size**: velocity sets the centre and the seed adds about ±15%, with mid values most likely. [L]
6. **Colour**: stay inside the section's palette, with no more than two colours on screen (Warren). Allow up to ±15° of hue drift. Never use a full-screen saturated red (see section 4). [L]
7. **Versions**: 3 to 5 hand-designed versions per pad, drawn from a deck that never repeats the last 2. A rare "hero" version comes up about 1 hit in 6 to 8. [L]
8. **The second press is a question**: hitting the same pad again within a bar steps up to a bigger version. It falls back over a bar or two. This is Eiserloh's trauma idea and your own escalating-hints principle. [L]
9. **Same pad, different section**: a pad looks calmer in a break and heavier in a drop (Lesson 4).
10. **Keep the identity**: the effect type and its section colour stay the same when that section comes back (Schiller).
11. **Pin a seed**: if you love a hit, the dial pins its seed so you can call it again. A **Variety** fader runs from 0 (identical every time, good for rehearsing) to 1 (full designed range). [L]

### Per pad (starting ranges to tune by ear [L])

| Pad | What changes every hit | Designed range | What never changes |
|---|---|---|---|
| **1 Shockwave** | Where the ring starts; its size; its shape; single or double ring | Deck of 8 spots in the middle 80% (today it stays within ±15% of the centre); kick hits lean low; size ±15%; width-to-height 0.9-1.1; double ring about 1 in 6; bright ring gone within about 1 beat (400 ms at 150 BPM) | A ring from a point, on the hit |
| **2 Laser burst** | Starting point; sweep direction; beam count; mirrored pairs | 6-8 starting points (4 edges, 2 corners, 1 "from behind" at the centre), dealt from a deck reshuffled every bar instead of today's fixed 1-2-3-4; clockwise or anticlockwise from the seed; velocity's 3-12 beams ±1; mirrored pair from both sides about 1 in 4 (stage shows run two side projectors as mirror images [H] https://www.ilda.com/resources/Safety/audience-scanning_overview_latest.pdf) | Beams aim inward; a beam never sweeps the whole frame like a flash |
| **3 White flash** | Version; where it starts | Deck: radial burst from a spot, wipe from one of 4 sides, an iris ring opening or closing, edge glow, full screen (rare); length 80-220 ms by velocity (as now); white or a pale palette tint | Always through the 3-per-second gate; never saturated red |
| **4 Glitch** | Block layout; tear direction; colour-split angle; version | Layout from the hit seed (today it comes from the clock); block size ±20%; tears vertical on kick, sideways on snare; split angle 0°, 45° or 90°; deck: slice tear, block shuffle, RGB split, line jump | About half a second long, scaled by velocity |
| **5 Strobe** | Bar direction; bar order; start point | Direction from a deck (across, up, two diagonals); bar order shuffled each press; start point snapped to the beat; speed locked to beat divisions instead of a free knob | Bars stay thin, a few percent of the screen; full-screen pulses at most 3 per second |
| **6 Particles → the Swarm** | Where it comes from; which way; how the flow swirls; version | Start spot from the deck or the current chord's star; one of 8 directions; a new swirl seed every hit (smooth "curl noise" flow [H] https://dl.acm.org/doi/10.1145/1275808.1276435); count and speed ±15%; deck: burst, fountain, ring, stream | Same flow physics; chord colour |
| **7 Kaleidoscope** | Start angle; number of segments; spin direction; centre | Random start angle; velocity's 4-12 segments ±2 (kept even); spin direction from the seed; centre within ±20% of the middle; spin speed ±15% | A mirrored, symmetric look |
| **8 Freeze** | Zoom point; drift direction; tap or hold | Zooms toward a dealt spot (today always the centre); drift direction from the seed; **a tap gives a 50-100 ms hit-stop**, a hold gives the classic freeze | The frozen picture is always the current frame |
| **9 Dampen** | Only *how* things leave | Deck: fade, sink down, collapse to the centre | Fast release of everything, every time. It is a control, so it must be trustworthy |
| **10 Choke** | Nothing | — | Instant cut, every time. This is your escape hatch (Schiller calls it a "get-out-of-jail-free card") |
| **11 Invert** | Version; where it starts | Deck: full invert (rare), hue flip, colour-channel swap, half-screen split (left, right, top or bottom), a circle growing from a spot; ease-in time by velocity | Its start uses a gate slot; if refused, it fades in slowly (as now) |
| **12 Zoom punch** (new) | Zoom point; in or out; small tilt | Zoom 3-8% by velocity, toward a dealt spot; mostly in, out about 1 in 4; tilt ±1-3°; overshoots by about 10% and settles within 1 beat | Lands exactly on the hit; no brightness change, so it never uses a flash slot |

---

## 3. FROM LESSONS TO OUR RIG (ranked)

**1. The variety engine. Size M.**
- *What:* one shared piece of code for all pads: the two seeds, the card decks, the "farthest spot" pick, the range per pad, pinned seeds and the Variety fader.
- *Lessons:* 7 and 8.
- *Controls:* the Variety fader; the dial pins or unpins a seed.
- *Fit:* a combo mixes both pads' seeds, so a fusion also lands differently each time. The Swarm takes its start spot and swirl from it. The flash gate is unchanged.

**2. Impact without light. Size S-M.**
- *What:* three pieces:
  - Zoom punch on pad 12.
  - A 50-100 ms hit-stop on accented hits, up to about 200 ms on drops and fusion payoffs.
  - A shake that points somewhere: up-down on kicks, sideways on snares. Guilty Gear does exactly this, vertical on a knockdown and sideways on a sideways slash. [H] (Lin et al.)
- *Lesson:* 9.
- *Controls:* pad 12, velocity, and one "impact" knob.
- *Fit:* none of these is a flash, so the 3-per-second budget stays free for real flashes. This is the natural payoff for combos. A long streak can add a little shake.

**3. A grown-up safety gate. Size M. Ship it with 1 and 2.**
- *What:* the gate checks the final picture, not just the requests. It should:
  - measure how much of the screen flashes;
  - add a saturated-red rule;
  - count fast cuts and transitions as flashes;
  - watch for striped patterns;
  - force a rest after about 5 seconds of flashing.
- *Why now:* variety adds coloured and partial flashes, which today's gate does not see.
- *Source:* the broadcast safety standard [H] https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf and the web rule [H] https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html. Details are in section 4.

**4. Beat landing. Size M.**
- *What:* every press answers instantly with a small spark and the pad light. If you press slightly early (up to about 1/16 of a beat, 100 ms at 150 BPM), the body of the effect lands on the next beat point. Otherwise it fires at once. Launching on the beat is standard in Ableton [H] https://www.ableton.com/en/manual/launching-clips/.
- *Plus:* a "visual offset" setting per screen. Guitar-game maker Harmonix gives starting video offsets of about 0 ms for old CRT TVs, 50 ms for LCDs and 60 ms for DLP projectors, and calibrates sound and picture separately [H] https://www.harmonixmusic.com/blog/how-to-calibrate.
- *Lesson:* 5.
- *Sync target* [L]: land between 30 ms early and 15 ms late. TV standards notice a late picture at about 45 ms but an early one only at about 125 ms. [H] https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- *Fit, streak meter:*
  - It scores how close each press is to the beat. osu!'s windows at medium difficulty are 50, 100 and 150 ms [H] https://osu.ppy.sh/wiki/en/Beatmap/Overall_difficulty.
  - Centre the windows on *your* average timing, not on zero, because people naturally tap a little early [H] https://pubmed.ncbi.nlm.nih.gov/16615303/.

**5. Song-structure sense: phrase counter plus break, build and drop detector. Size L.**
- *What:* a bar counter that knows blocks of 8, 16 and 32 bars, plus a section guess:
  - **Break:** bass and kick gone for 2 or more bars.
  - **Build:** high-band energy rising, snare or hat hits speeding up (Solberg's "drum roll"), tension climbing.
  - **Drop:** kick and bass return after a build, on a phrase line.
- *Lessons:* 4 and 6. rekordbox and Beat Link Trigger show the industry already does this. Beat Link Trigger picks a look for each phrase by weighted raffle, where "the weight is the number of raffle tickets each phrase trigger buys" [H] https://blt-guide.deepsymmetry.org/beat-link-trigger/8.0.0/Shows_PhraseTriggers.html.
- *Honest gap:* our live beat tracker (beat_a) does not claim where bar 1 falls (`is_downbeat: None`). The beat_g tracker estimates a bar position from accents, but it is not the live one. Until that is solved, a transport button lets you tap the "one", and another lets you mark "drop next".
- *Controls:* transport buttons for manual marks; the LCD shows the section and the bar count.
- *Fit:* it drives items 6, 7 and 8. Builds refill charges; drops pay out streak bonuses.

**6. Break and drop looks. Size M (S if switched by hand).**
- *What:* a break look (desaturated, slow, thin, few layers) and a drop look (full palette, wide, heavy). Switched by item 5, with a fader to override.
- *Lesson:* 4.
- *Fit:* the same pad changes register (rule 9). The Swarm drifts slowly in breaks and gets dense and fast in drops.

**7. Charges and an escalation ladder. Size M.**
- *What:* big effects (flash, strobe, invert, full laser fan, kaleidoscope) carry charges, shown on the pad lights: bright means ready, dim means recharging. Charges refill during builds and with streaks. A second press inside a bar steps up a version.
- *Lessons:* 2 and 3.
- *Fit:* a combo spends two charges for a bigger payoff. The streak meter refills charges. The gate still sits underneath everything.

**8. The set's secret. Size S.**
- *What:* one layer is held back until the first big drop: for example, the Swarm's full form, or a new set of laser starting points. Use "kill" (fade to black on the next beat) one beat before the drop.
- *Lesson:* 2 (Warren's hidden mirrorballs).
- *Fit:* the Swarm's debut, or a streak unlock.

**9. A colour script. Size S-M.**
- *What:* each section gets a palette from the engine's key and tension. No more than two colours at once. The drop palette comes back when the drop comes back.
- *Lessons:* 1 and 7.
- *Controls:* one palette fader.

**10. Macro faders. Size S.**
- *What:* three or four big faders, each doing many things: Intensity (size, brightness, count), Speed, Variety, and Darkness (how much black space).
- *Lesson:* 10 (Pagano).
- *Controls:* free faders.

**11. Keys as position. Size S. My idea.**
- *What:* when you play the 88 keys, the key's place on the keyboard sets where the next pad hit lands, left to right. Pangolin lets a keyboard play its cue grid [H] https://wiki.pangolin.com/doku.php?id=beyond%3Amidi_settings-new; using it for screen position is my extension.

### Hardstyle ideas [L unless noted]

- **Kick = weight, not light.** Use zoom punch and an up-down shake. Save a full flash for the first kick of a phrase.
- **Safety arithmetic at 150 BPM:**
  - a flash on every kick is 2.5 per second, which passes;
  - kick plus off-beat is 5 per second, which fails if the flash covers more than a quarter of the screen.
- **Off-beat (reverse bass).** The bass sits on the off beat ([M] https://en.wikipedia.org/wiki/Hardstyle), and Warren follows the off beat. Give it small, coloured swells that cut off before the next kick, never full-screen flashes.
- **Screech:** thin, high, small-area lasers or spikes, matching high pitch with small and high up.
- **Anti-climax and climax** (your genre knowledge; I found no primary source): anti-climax monochrome and angular, the "dark ritual" Qlimax aims for [M]; climax in the full palette, wide and rising.
- **Pitched kicks:** the hit's colour follows the engine's chord.
- **Long drops:** 32 bars at 150 BPM is about 51 seconds. The standard warns that even compliant flashing for more than about 5 seconds may be a risk, so build in rests.
- **Worship piano:** the same engine with gentle ranges and slower tails. The sustain-pedal tension already in the code can drive the colour.

---

## 4. WHAT TO AVOID

1. **Layer soup.** Six visuals mixed every beat (Jacobs). One layer should lead at a time.
2. **Too many colours.** Warren keeps to two at once.
3. **The same big effect every time.** By song four nobody reacts (Pyrotecnico).
4. **Pure randomness.** It looks like "oatmeal" (Compton): unique on paper, the same to the eye. Vary what the eye reads first: position, direction, shape, colour.
5. **Variety that breaks identity.** The chorus look should come back with the chorus (Schiller).
6. **Randomising the start time.** It makes hits feel late. Late is noticed at about 45 ms; early is tolerated more (BT.1359).
7. **Long tails at 150 BPM.** Today the shockwave rings for about 0.7-1.5 s and the laser for about 0.5-1.3 s, which is up to 3 or 4 beats. The bright part should clear within about one beat so the next kick reads as new. [L]
8. **Too many small controls.** A few big ones work better (Pagano). And leave some things for your hands (Ghostdad).
9. **Flash-safety blind spots.** The standards count more than our gate does:
   - any change to or from **saturated red** counts as a flash at any brightness;
   - the danger line is flashes over **25% of the screen**, more than 3 per second;
   - **fast cuts** count as flashes;
   - **stripes**: more than 5 light-dark pairs over 25% of the screen, if moving or flashing, are risky;
   - **runs over 5 seconds** may be a risk even when they comply;
   - a **dark room, a bigger screen and sitting closer** all raise the risk. The standard suggests a lit room and at least 2 m distance.
   - Sources: [H] ITU-R BT.1702-3; WCAG 2.3.1.
10. **Strobe speed.** Seizure triggers are most common at 3-30 flashes per second, and most likely at 16-25. The UK safety regulator recommends club strobes flash 4 times a second or less [H] https://epilepsysociety.org.uk/about-epilepsy/epileptic-seizures/seizure-triggers/photosensitive-epilepsy. Our strobe bars run at 2-12 per second, so they must stay thin.
11. **Letting combos or streaks get around the gate.** Every flash, whatever triggered it, goes through the same gate.
12. **A virtual laser turning into a flash.** Never let a beam sweep across the whole frame. Real stage lasers are dimmed below the audience line; copy that idea. [H] ILDA paper above

---

## What I checked, and what I dropped

**Confirmed in the primary source:**
- Jacobs's interview; Warren's interview (the researcher's saved copy); Schiller's article.
- The grandMA3 shuffle and random generator pages; Resolume's random-beat jump and velocity mapping; Pangolin's live controls, zones and "First key".
- Chaser's random features; Beat Link Trigger's raffle; rekordbox's phrase labels; Unity's shuffle.
- deadmau5 (PLSN); Excision; Plastikman; Ghostdad; 0xf8 and Synnack; Calvert's timecode quote; Qlimax; Sharpe; Pyrotecnico's cryo line.
- Solberg; Sakurai; Lin et al.; Eiserloh; Compton; BT.1359; Vroomen; BT.1702; WCAG; the Epilepsy Society; osu!; Harmonix; Synesthesia; Pagano.
- Our code lines.

**Corrected:**
- Harmonix's video offsets are about 50 ms for LCD and 60 ms for DLP, not "30-50 ms".
- Confetti in the Pyrotecnico piece is a release at the finale, not a "one-shot" rule.

**Dropped as unverified:**
- The claim that Prydz's VJ uses a grid of speed, colour and intensity (Medium page blocked). I used Pagano and Pangolin for the macro-fader idea instead.
- The claim that Prydz's VJ knows the tracks but not the order: it was not on the page I checked.
- A line attributed to Schiller, "don't use everything on every song": it is not in his article.
- Romero's drops being "loosely based on" the break visual.
- Spotify's shuffle (the researcher could not load the page).
- The Tetris "bag": I replaced it with Compton's deck and Unity's shuffle.
- Anyma at Sphere (secondary source only).
- The depth-perception paper cited from memory.
- Hardstyle anti-climax structure: Wikipedia does not cover it, and only a forum does.

**Not found by anyone:** a primary source from a hardstyle VJ on visualising kicks, screeches or anti-climaxes.

All ranges marked [L] are starting points to tune live.

**Files:** the researchers' saved sources are in `<session scratchpad>/vjresearch/`. The code lines cited are in `E:\AI-Setup\arsenal\web\vj.js` and `E:\AI-Setup\arsenal\web\vj-core.js`.

---

## Research angle: performers (verbatim)

Performers and tools research (VJ angle), 2026-10-24

Read-only. Nothing in the repo, the KeyLab or the 8793/8794 servers was touched, and no files were written. Confidence tags: [H] means an official manual or the artist or team speaking first-hand. [M] means trade press quoting the team, or a source I saw only through a search snippet. [L] means a secondary write-up or one I could not verify.

## FIVE LESSONS
1. Pros get variety by changing where a clip lands, when it starts and how hard it plays, not by swapping in new content. The same clip goes to a different surface or zone, enters at a different beat, or runs at a different speed, colour or intensity. Prydz's VJ works a grid of speed, colour and intensity. Laser software can re-route a cue to other projection zones. Max Cooper chooses which surface each visual goes on. Resolume's random button jumps to a random beat in BPM-sync mode.
2. They use seeded randomness rather than raw randomness. On a grandMA3 desk the Shuffle value runs from 0 to 32,767, each value is a different order, and the same value always gives the same order. The desk's Random generator works as a centre value plus a variance, and its "Random Start" can be set to repeatable or unpredictable. Chaser's Tiler effect and Notch's particle emitters also expose a seed. The variety is reproducible, so you can name a seed and come back to it.
3. The music decides when something happens and the performer decides what happens. Everything in the rig is told where it is in the song, not just where the beat is (deadmau5's bar positions over OSC, Excision's song position, Plastikman's show sequencing).
4. Impact comes from restraint and contrast: black space, few layers, a completely different look for the break than for the drop, and few controls.
5. Leave some things to play by hand. When the operator knows the music, hand-triggering is tight enough that industry people mistook Prydz's show for a timecoded one.

## 1. HOW THE BIG SHOWS ARE ACTUALLY RUN (from cue list to fully improvised)
- **Eric Prydz, EPIC/HOLO (fully live).** "There are never any pre-sequenced elements" (Dave Green, video software director). Creative director and VJ Liam Tomaszewski fires Avolites Ai servers from a Livid MIDI controller. He knows every track but not the order, and lighting director Ross Chapple works the same way. Production director Mark Calvert says industry people "thought the whole show was timecoded rather than triggered live". Tomaszewski also says the team responds in real time to how the crowd reacts. His screen is a grid of blocks controlling the speed, colour and intensity of the visuals.
  - Green and Calvert quotes [M]: https://plsn.com/featured/eric-prydz-holo-stuns-with-holographic-3d-fx-powered-by-avolites-ai/ , https://plsn.com/newsroom/projection-connection/avolites-ai-s4-servers-drive-eric-prydz-epic-4-0-usa-tour/ , https://www.tpimagazine.com/eric-prydz-goes-holographic-with-avolites-ai/
  - Crowd-response point, Vice 2014 [M]: https://www.vice.com/en/article/eric-prydzs-holo-brings-largest-hologram-ever-to-this-years-ultra-music-festival/
  - Grid detail [M, search snippet only; the page returned 403]: https://medium.com/re-form/go-for-the-music-stay-for-the-holograms-bb369594c842
- **Excision, Paradox (hybrid).** Jeff runs visuals, lasers, lights and cryo from his CDJ/DJM plus a custom panel. When he picks a song on the CDJ, its video loads automatically. A TouchDesigner program reads his fader states, song position and active deck, and drives the timecode for lights and lasers. They dropped SMPTE timecode for video because he scrubs and jumps between cue points. Every track has its own video and there are no loop-based visuals. The animation look also changes with the state of the motorised DJ booth. Animator Ben Leonard builds each scene around a camera move, such as an elevator dropping. [H] https://resolume.com/blog/14554
- **deadmau5, Cube v3 (hybrid).** Six TouchDesigner instances, most of the show in Joel's own GLSL shaders, and more than 800 OSC tags. [H] https://derivative.ca/community-post/made-love-touchdesigner-v99-cusersdeadmau5/60967
  - Lighting runs on SMPTE plus an OSC decoder for the grandMA2 that receives song, BPM, bar position and set-list changes, so "Joel can change the set overnight" and the show still works the next day. [M] https://plsn.com/articles/designer-insights/deadmau5-cube-v3-tour/
- **Plastikman, Richie Hawtin (generative).** Ableton sends TouchDesigner the controllers, which loops are playing, clocks, show sequencing and track transitions, raw audio and effect outputs. Each track "has its own cocoon": the team chooses, per track, which part of the visual hooks up to which part of the music. Ali Demirel steers from front of house on a Lemur touchscreen. [H] https://derivative.ca/community-post/plastikman-derivative-team-2010-tour/60824
- **Amon Tobin, ISAM (rehearsed, with manual control).** Peter Sistrom says TouchDesigner let him escape a "cue stack mentality". Kinect captured Tobin live; the narrative content was pre-rendered. [M] https://plsn.com/articles/production-profile/amon-tobins-isam-tour-is-visual-innovation-squared/
- **Max Cooper (improvised, spatial).** Ableton plus Max for Live sends OSC to one or two Resolume machines, feeding up to 16 visuals across many projectors. He has 100 to 200 projects available and chooses live which visual goes on which surface. "Every show is designed for the space." [M] https://www.yahoo.com/entertainment/every-show-designed-space-max-152647561.html , https://www.clashmusic.com/features/max-cooper-talks-3d-av/
- **Illenium, VJ Sandy Meidinger (two modes).** For DJ sets she triggers by ear. For the live show, Ableton sends MIDI to Resolume. Each song is a column, with Chaser effects stacked above the clips. She uses Chaser for random panel flashing, logo grids and mirror splits. [H] https://resolume.com/blog/tag/chaser
- **Nicky Romero, VJ Rick Jacobs (freestyle).** "The whole show is freestyle, we never use SMPTE." He plays from an APC40 mk2 and coordinates with lighting designer Koen by hand signals and shouting. He sets cue points on vocal tracks so he is ready when one is mixed in. A song's visuals change from day to day depending on which colours the two of them call. [H] https://resolume.com/blog/14343
- **Porter Robinson, Worlds Live (hybrid).** Laura Escudé built the rig so Porter could manipulate "sounds and images on the fly". Each song brings its own controller mapping, which switches automatically through the set. Ghostdad, the VJ, says "I leave myself a few things to do by hand" even on Worlds.
  - [M] https://www.vice.com/en/article/an-inside-look-at-porter-robinsons-electrifying-worlds-tour-visuals/
  - [H] https://resolume.com/blog/11941
- **Aphex Twin, Weirdcore (live-generated).** Crowd-camera footage is processed in real time, with face detection swapping faces onto local celebrities. One section is customised for each city. Lighting designer Dave Ross picks which of the 12 screens show. "It's a psychological overload."
  - [M] https://www.itsnicethat.com/features/weirdcore-aphex-twin-field-day-050617-miscellaneous
  - [M] https://www.vice.com/en/article/aphex-twins-twisted-new-live-show-interview/
- **Anyma at Sphere (timecoded spectacle).** Reportedly Unreal Engine content synced by timecode through disguise. [L, secondary source; its claims about Stable Diffusion, Notch and TouchDesigner are unverified] https://ymcinema.com/2025/01/30/the-making-of-anymas-the-end-of-genesys-at-the-las-vegas-sphere-a-groundbreaking-fusion-of-music-and-technology/

## 2. WHAT IS UNDER THEIR HANDS
- **Grid plus faders plus encoders, mirroring the software:**
  - An APC40 mk2 for Rick Jacobs, a Livid controller for Tomaszewski, a Lemur and an APC40 for Max Cooper.
  - Resolume can send velocity values back to light the pads in colour, with lookup tables for the APC40 mk2 [H] https://resolume.com/support/en/midi-shortcuts
- **Split the job by speed of action.** Kazoe Nobuaki's DEVISION system (Tokyo club VJ) puts colour pickers and switches on a touch display, and everything that must be instant on MIDI faders, modelled on lighting consoles. He also maps each of its 16 layers to different stage layouts. [H] https://derivative.ca/community-post/kazoe-nobuakis-sensational-and-highly-adaptive-devision-vj-system/60681
- **Keep it small.** Scott Pagano argues that "a small number of effective controls" makes for a more impactful result. Jim Ellis notes that large sliders capture gesture far better than small ones. [H] https://derivative.ca/community-post/touchdesigner-performance-interfaces/60765 (2013)
- **A keyboard can play the cue grid.** In Pangolin BEYOND laser software, a "First key" note fires the top-left cue and higher notes fire later cues. [H] https://wiki.pangolin.com/doku.php?id=beyond%3Amidi_settings-new
  - BEYOND's own Performer Console offers grids, fader and encoder banks, four layers deep. [M, search snippet] https://pangolin.com/en-us/blogs/news/beyond-performer-console
- **Resolume's MIDI mapping:**
  - Velocity can map to any parameter; the manual's example makes a clip grow up to 200% the harder you hit.
  - Piano mode makes a trigger momentary.
  - [H] https://resolume.com/support/en/midi-shortcuts , https://resolume.com/index.php/support/en/7/clips
- Caution: Resolume's "MIDI controller with video on the buttons" post (2011) was an April Fools joke. Do not cite it as a real product. [H] https://www.resolume.com/blog/10256

## 3. VARIETY WITHOUT CHAOS (concrete techniques)
- **a. Random entry point, still on the grid.** Resolume's Random (R) button jumps to random frames. In BPM-sync mode it jumps to a random beat and keeps playing from there. Loop modes include ping-pong, and BeatLoopr loops a chosen number of beats. [H] https://resolume.com/support/en/6/video
  - Parameter animation can loop, ping-pong, play random frames or play once, can be audio-driven with Gain and Fall controls, and takes an envelope. [H] https://resolume.com/support/en/parameter-animation
- **b. Random clip from a pool, quantised.**
  - Resolume's Autopilot can play the next, previous, a random or a specific clip after N loops, and Beat Snap holds a launch until the next beat, bar, 2 or 4 bars. [H] https://resolume.com/index.php/support/en/7/clips
  - MadMapper's cue banks have an Auto Play mode with loop or random. [M, search snippet] https://madmapper.com/files/06-Scenes%20and%20Cues.pdf
- **c. Seeded shuffle, so variety can be repeated.**
  - grandMA3 MAtricks Shuffle: values 0 to 32,767, and "the same shuffle value will result in the same shuffled selection order". [H] https://help.malighting.com/grandMA3/2.0/HTML/matricks.html
  - Lighting programmers combine Shuffle with phasers' phase to make effects look random. [M] https://forum.malighting.com/forum/thread/4445-random-based-effects/
- **d. Variance around a designed centre.** The grandMA3 Random generator has Speed, Phase and Low/High settings, each with its own variance, plus attack/decay, ratio and a Random Start that can be repeatable or unpredictable. [H] https://help.malighting.com/grandMA3/2.0/HTML/generator.html
- **e. Spatial routing is the main lever.**
  - Pangolin effects can set, add, delete or replace a cue's projection zones, and multi-zone time-shift plays the same frame phase-offset across zones. Its oscillating effects run by time, beats or MIDI, and can be randomised through custom waveforms. [H] https://wiki.pangolin.com/doku.php?id=beyond%3Aeffects
  - Chaser for Resolume:
    - It sequences an input map's slices over 16 steps.
    - Its "Random" effect lights a random set of slices up to a Max Slices count.
    - Tiler's Seed switches between whole looks.
    - Outliner's Randomise gives each animation a random offset.
    - [H] https://hybridconstructs.com/support/chaser/plugins/ , https://hybridconstructs.com/support/chaser/making-a-chase/
  - The same idea also appears in Max Cooper's surface choices, Weirdcore's lighting designer picking screens, and DEVISION's per-layer maps.
- **f. Live macros on top of fixed content.** Prydz's grid of speed, colour and intensity; Pangolin's encoders for size, rotation and oscillation.
- **g. Same trigger, different context.**
  - Plastikman's per-track hookups.
  - Porter's per-song controller remaps.
  - Excision's look that changes with the booth state.
  - Rick Jacobs's colours that follow the lighting designer.
- **h. Modulation sources in other tools.**
  - VDMX's LFO includes a random waveform, and its step sequencer handles numbers, colours and booleans. [H] https://vdmx.vidvox.net/tutorials/generating-control-data-with-the-lfo-and-step-sequencer
  - Notch emitters have a Seed, and Notch Blocks expose parameters to Resolume, with a reported limit of 32 per type. [M, search snippets] https://manual.notch.one/1.0/en/docs/whats-new/release-notes/1-0-0/ , https://manual.notch.one/2026.1/en/docs/workflows/working-with-media-servers/blocks/using-notch-in-resolume/

## 4. IMPACT AND SYNC
- **Black and restraint.** Rick Jacobs: don't stack six visuals and mix them every beat; "black is your friend". [H] https://resolume.com/blog/14343
- **Change register between break and drop.** In Romero's show, breaks are desaturated and realistic, and drops are neon, abstract and flashing, loosely based on the break visual. The contrast is the crowd booster. Same source [H].
- **Music decides when, the performer decides what.** 0xf8 (Jennifer) says the audio data sets the timing and speed of effect changes, but she chooses which effects are affected and which clips play. Synnack sends kick, snare and loop amplitudes over OSC, and only the highs from ambient clips. [H] https://www.ableton.com/en/blog/audio-reactive-visuals-interview-synnack-0xf8/
- **Feed structure, not just beats.** deadmau5 sends bar positions and set changes; Excision tracks song position and fader states; Plastikman sends sequencing and transitions (sources in section 1).
- **Motion metaphor per moment.** Ben Leonard builds scenes around camera moves (Excision source). Tomaszewski says he imagines the music as a film (Rolling Stone, search snippet only [L]).
- **Hand-played accents keep the performer expressive.** Ghostdad: controlling in real time keeps him engaged and expressive [H, above]. An academic gesture study finds fader sweeps, knob turns and button presses form the expressive layer over audio-reactive visuals. [L/M, 2026] https://idealogyjournal.com/ojs/index.php/idealogy/article/view/1016
- **Personal relevance can be a deliberate overload.** Weirdcore's local faces and city-specific section (sources in section 1).

## 5. TRANSLATION TO OUR RIG
From a quick read of the repo, not a test:
- **What already varies.** Each trigger gets a golden-ratio seed (`arsenal/web/vj-core.js:591-592`).
  - Shockwave and particles take their origin from that seed (`arsenal/web/vj.js:1251-1272`).
  - Lasers rotate through four origins by serial number, with a seeded aim wobble (`vj.js:1259`). That is why the lasers already feel alive.
- **What does not vary.**
  - The strobe-bar phase restarts at 0 on every trigger (`vj.js:1304`).
  - Kaleido is always centred and its rotation starts from 0 (`vj.js:1327`).
  - Glitch varies over time but uses no per-trigger seed (`vj.js:1330`).
  - Flash, invert and freeze are full-frame and come out the same every time.
- **Proposals:**
  1. Give every pad the laser treatment: a set of zones or origins that rotates or shuffles (section 3e), and a seeded variance around a designed centre (3c, 3d), keeping seeds reproducible so a good one can be pinned and named.
  2. Use our ahead-of-time beat for on-grid random entry, like Resolume's random-beat jump: random phase, rotation or bar offset, quantised to the beat.
  3. Put Prydz-style macros (speed, colour, intensity) on three faders that apply across all pads.
  4. Let context recolour the same pad, the way Plastikman's hookups do: key or chord sets the colour, tension sets the energy, break or drop sets the register.
  5. Treat full-frame events (flash, invert) as scarce punctuation with black around them. That fits the 3-flashes-per-second gate.
  6. Possibly let each press within a bar advance a step of a short sequence, as Chaser steps and lighting cue stacks do. This is my inference, not something a source describes. It matches Daniel's "the second press is a question" rule.
  7. The 88 keys could act as a cue or zone grid, the way Pangolin lets a keyboard play cues. My idea: map key position to screen x.

## GAPS
- Boiler Room VJs: no first-hand source on their practice.
- Beeple: his loops are free Creative Commons source material, but I found nothing on how they are performed. [M] https://vimeo.com/channels/beeple
- Rezz: the interview with her VJ Cam MacNeil has little on technique. [M] https://stagehoppers.com/inside-rezzs-visual-world-with-vj-cam-macneil/
- Anyma: low confidence, secondary source only.
- Pages that blocked me (403): Medium re-form and DJ Mag. Rolling Stone and Variety redirected to a paywall.

---

## Research angle: festival (verbatim)

# Festival stage VFX and show design: research for the VJ rig (vj.html)

## Summary

1. **Vary the instance, keep the identity.** The pro tools vary repeated triggers in four ways: phase spread, seeded shuffles, live controls for position, rotation and size, and a weighted random pick among alternative versions [S1][S2][S3][S4]. Pro busking advice also says the look for a section should come back when the section comes back [S5]. So the rule for our rig: the effect family stays tied to the musical moment, and its position, phase and size change on every hit. The music works the same way: "with variation, but not too much" [S6].
2. **Darkness is a tool.** The biggest reactions in these sources come from taking things away, then hitting late: cut to dark just before the drop and save something for the next one [S7][S8][S9][S6].
3. **Effects wear out when overused.** Each big effect needs a budget and a ladder that escalates, not a button that does the same thing every time [S10][S7][S5].
4. **A hybrid is the norm at the top.** Timecoded shows run alongside a live operator. At Qlimax one VJ ran the timecode content and another played live [S11][S12][S13]. In our rig the engine's look-ahead beat could be the timecode operator, and Daniel on the pads the live one.
5. **Our flash gate covers the headline rule only.** The broadcast standard (ITU-R BT.1702) also counts saturated red, the share of screen that flashes, fast cuts, stripe patterns, and sequences longer than five seconds [S14][S15].

## 1. What the repo shows (read-only)

- **Why the lasers feel alive** (`E:\AI-Setup\arsenal\web\vj.js`, roughly lines 1249–1272):
  - they rotate through four starting points in turn (`f.serial % 4`: bottom, left, right, top);
  - the sweep has a random starting phase (`sin(age*2.4 + seed*6.28)`);
  - harder hits give more beams (3 to 12), wider spread and faster speed.
  - This is the same grammar real laser rigs use: several projector positions, aim adjusted live, and beam count tied to intensity.
- **Why the other pads feel the same each time.**
  - Shockwave and particles only shift within a small box near the centre (about ±0.15 of width, ±0.125 of height for shockwave).
  - Flash, strobe, kaleido, freeze and glitch cover the whole frame, so where they happen never changes.
- **What the flash gate covers today** (`vj-core.js` FlashGate and `envFlashSafe` in vj.js):
  - It counts white full-frame flash and invert requests, at most 3 per second.
  - Strobe bars run at 2–12 Hz but are kept "thin, a few percent of the frame".
  - Nothing counts saturated red changes, scene cuts or stripe patterns.
  - There is already a luminance probe on the output (vj.js around line 1374) that could become a full output check.

## 2. How the pros make repeated triggers differ

- **Phase spread (grandMA3 lighting console).** Every light runs the same steps, but each starts at a different point in the loop ("0 thru 360"). One effect becomes a wave or chase across the rig. [S1, high]
  - For us: spread each hit across several copies, each at a different phase.
- **Seeded shuffle (grandMA3).** The shuffle value is a seed from 0 to 32,767. The same seed gives the same "random" order. [S2, high]
  - For us: a new seed on every hit. Let Daniel pin a seed he likes.
- **Live controls (Pangolin BEYOND, the standard laser software).** Position, rotation, size, zoom, colour, visible points, scan rate and animation speed can all be changed while a cue runs. A "mass-spring filter" smooths knob moves. Effects can run in time or in beats, use random waveforms, have a percentage phase delay, and hop between projection zones. [S3, high]
  - For us: the knobs and dial set where and how the next hit lands. Use spring smoothing. Screen regions act as zones that a repeated pad hops between.
- **Mirrored and surrounding sources.** In the typical audience-scanning show ILDA describes, two side projectors make mirror-image shapes that change on the beat while a centre projector sweeps [S16, high]. Laserface surrounded the room with 122 projectors: house left and right, a truss facing the stage, floor and flown arrays [S17, high].
  - For us: beams can enter from the screen edges, including "from behind the viewer", aimed toward the vanishing point.
- **Weighted random pick by section (Beat Link Trigger).** Each phrase trigger has start, loop, end and fill parts, stretched to fit the phrase. Competing triggers are drawn by lottery: "the weight is the number of raffle tickets each phrase trigger buys". Triggers can be filtered by tempo, phrase length and track bank. [S4, high]
  - Ableton Follow Actions do the same with chance percentages [S18, high].
- **Combining stacks (Brad Schiller, busking).** Keep separate stacks for position, colour and gobo/effect; combining them yields new looks all night. Faders switch fixture groups on and off. Keep a reset cue as a "get-out-of-jail-free card". [S5, high]
  - For us: a velocity × zone × colour × shape matrix per pad.
- **Shuffle bag.** The Tetris "7-bag" deals every option once before any repeats, which caps long runs without a given piece. [S19, medium]
  - For us: deal each pad's start positions from a bag, so a position never repeats until all have been used.
- **The counterweight.** Schiller says to repeat the chorus look when the chorus comes back, because audiences feel connected through it [S5]. EDM layers enter and leave on 2/4/8/16/32-bar boundaries [S6, high].
  - For us: vary position, seed, phase and size every hit. Keep the family, colour and section mapping stable.

## 3. Song structure, darkness and contrast

- **The research (Solberg 2014, peer-reviewed).** Tension comes from risers, the "drum roll effect" (note values keep halving, giving a sense of speeding up without a tempo change), large frequency changes, removing bass and kick, and a contrasting breakdown. The peak comes when the bass returns after a build focused on high frequencies. [S6, high]
  - For us (my inference): during a build, keep visuals thin, high-pitched in feel and small-area, with subdivisions speeding up. On the drop, go full-frame, low and heavy.
- **Ed Warren** (Skrillex, Fred again.., Four Tet at Madison Square Garden; Four Tet's lighting designer since 2008):
  - kept a 90-minute "house lights" look, then cut it on the drop on Kieran's signal;
  - hid mirrorballs and lowered them in darkness, so they stayed a secret until used;
  - built slowly and wound it back down so he could build again;
  - on strobing: hit the beat and the off beat, wait for the last possible moment, and "save something for the next drop, and the next" [S7, high].
- **Qlimax 2023** design played on the "contrast between light and darkness", led by a story figure called the illusionist [S8, high].
- **Q-dance end shows.** Jonas Schmidt builds intensity, then cuts everything to silence; his team re-edited the intro themselves [S9, medium; Dutch interview, read through a summary].
- **Hand-offs between layers.** Alexander Wessely (Anyma at Sphere) on "having the digital world step into the shadows and letting the physical lead", then flipping it [S20, high].
  - For us: one layer leads at a time. For example, the overlay effects take over while the background scene drops away.

## 4. Restraint and an effect budget

- **Pyrotecnico:** "Fire off cryo on every chorus, and by song four the crowd stops reacting." Confetti is a one-shot; once fired, the moment is spent. [S10, medium-high; vendor blog]
- **Schiller:** don't use everything on every song [S5].
- **Corbin Sharpe** (laser designer for Levity):
  - minimal cues, driven by how the music moves;
  - "I want the lasers to look like they're being controlled by the music";
  - with a full crew, each department gets its moment: a bass hit might go to strobes or a dimmer chase while the lasers wait for their own moments [S21, high].
- **Translation (my inference):**
  - big effects carry charges that refill during builds, or through the streak meter;
  - a second use in the same set gets a different, bigger version (an escalation ladder). This fits Daniel's second-press preference from memory;
  - each type of hit owns one effect family at a time.

## 5. Colour dramaturgy

- Ed Warren: never more than two colours at once; the MSG palette (blue, red, green, white) was agreed in advance [S7].
- Artists can lock palettes: Knife Party wanted only red, except for one song; Carnage allows at most four colours [S22, medium].
- Defqon.1 colour-codes its stages by genre (RED main, BLUE rawstyle, BLACK hardcore, MAGENTA euphoric) [S23, medium].
- Qlimax must "feel like a dark ritual"; the audio is the foundation, and the goal is a trip rather than a story [S24, medium; Dutch, read through a summary].
- Tomorrowland 2026 was themed as six "provinces", each a human emotion [S25, medium].
- Pixar's colour script maps a film's emotional arc as a sequence of colours [S26, medium].
- For us: a colour script for the whole set, plus a palette per section driven by the engine's key and tension.

## 6. Scale and depth on a flat screen

- Qlimax used two layers of LED wall plus a translucent header video wall [S27, high].
- Eric Prydz's HOLOSPHERE used 72 handmade panels with LEDs on both sides. Mark Calvert's point was that earlier shows were "two-dimensional projections". The show runs live, with crowd cameras guiding song choice. [S28, medium-high]
- Flat-wall 3D illusions rely on forced perspective with a sweet spot, shading and shadows, and motion parallax [S29, medium]. Motion parallax is an independent depth cue [S30, high; Rogers & Graham 1979, Perception 8:125–134, cited from memory].
- Ed Warren designed for the full range from a "fine pinpoint beam" scanning slowly to washing the whole room [S7].
- Kinetic stages:
  - Schmidt is obsessed with moving stage parts and pyro mounted on cranes [S31, medium];
  - TWOFIFTYK used TouchDesigner to aim lights and lasers at moving stage parts [S12, high];
  - Tomorrowland's Freedom Stage has a moving LED roof [S32, medium].
- For us: near, mid and far layers with slow camera drift; one hidden layer kept back for the peak.

## 7. Laser choreography

- **Basic shapes.** Cones, flat and wavy planes, pyramids, and stripes moving "like a giant keyboard". One shape morphs into the next (cone → striped → thin plane). [S16]
- **Roles by laser type:**
  - high-power lasers stop above the crowd, as a thin wall on the roof or balcony;
  - crowd scanners fill whole zones (they run at about 3 W effective, with wide lenses and scan-safety cut-off);
  - laser bars sit on the ground, each aperture controlled separately [S21].
- Design for how it looks in the haze, not how the drawn shape looks [S21].
- **Counts:**
  - Alison Wonderland's tour: 10 BB3 + 18 Kinekt + 8 Lynx lasers, with lasers and lights firing every four beats on the drop [S33, high];
  - Laserface: 122 projectors [S17];
  - Tomorrowland 2026 mainstage: 56 lasers [S25].

## 8. Timecode versus live busking

- **Timecoded examples:**
  - Defqon.1: every stage show is timecoded, pre-programmed in Depence, with about 3 hours of on-site programming for lasers, effects and pyro [S11, high];
  - Qlimax finale: about an hour of timecode visuals across 17 shows (usually 6–9), with no content reused [S12];
  - Laserface: timecode taken from the DJ's CDJs over Ethernet (TC Supply) into BEYOND [S17].
- **Live examples:**
  - Steve Lieberman (EDC, Ultra): never knows what will play, so the console is set up for instant changes and he anticipates 4/4 phrasing; the music and video lead, the lights follow [S13, high];
  - Ed Warren: no timecode, every look within one button press [S7];
  - Tomorrowland 2026: visuals and pyro respond live to each DJ [S25].
- **Automatic tools:** rekordbox's lighting mode labels each phrase (Intro/Up/Down/Chorus/Bridge/Verse/Outro), sorts tracks into HIGH/MID/LOW moods from tempo, rhythm, kick and density, and offers banks of scene variations (COOL, HOT, VIVID…) [S34, high].

## 9. Hardstyle specifics

Primary sources here are thin; confidence is medium to low.

- **The music:**
  - modern hardstyle runs about 150–160 BPM, with an off-beat "reverse bass" and dissonant screeches [S35, medium];
  - the kick sits on the beat, the bass on the off beat, with no overlap (a push-pull) [S36, low-medium];
  - the anti-climax has no melody: kicks plus a screech pattern [S37, low].
- **Mapping for the rig (my inference):**
  - **Kick:** mass (scale punch, camera shove). Use a full flash only on the first kick of a phrase.
  - **Reverse bass:** a swell that snaps off before the next kick. Warren says to follow the off beat [S7].
  - **Screech:** thin, small-area lasers or spikes.
  - **Anti-climax:** monochrome, angular, the "dark ritual".
  - **Climax:** full palette, wide, rising.
  - **Pitched kicks:** let the hit's hue follow the engine's chord.
- **Safety arithmetic:**
  - a flash on every kick at 150 BPM is 2.5 per second, which passes;
  - adding the off beat makes 5 per second, which fails if the flash covers more than a quarter of the screen. Off-beat hits must stay small;
  - a 32-bar drop runs about 51 seconds, past the five-second note in section 10.

## 10. Safety for a home rig

- **ITU-R BT.1702-3 (the broadcast standard):**
  - A flash means a luminance change of 20 cd/m² or more while the darker image is under 160 cd/m².
  - Any change to or from saturated red counts, whatever the brightness.
  - A flash sequence fails only if both hold: flashes cover more than 25% of the screen, and there are more than 3 flashes in any second. Flashes whose leading edges are at least 334 ms apart (on 60 Hz) are fine.
  - Fast cuts count as flashes.
  - Even compliant flashing for more than about 5 seconds may be a risk.
  - Patterns: more than 5 light-and-dark stripe pairs is risky if still and over 40% of the screen, or if moving, flashing or reversing and over 25%. Patterns flowing smoothly in one direction are exempt.
  - A darker room, a bigger or brighter screen, and a closer viewer all raise the risk. Viewers under 20 are most affected. The standard suggests a lit room and at least 2 m distance.
  - [S14, high]
- **WCAG 2.3.1 (web rules):** the limit is 0.006 steradians within any 10° of view. A red flash is defined by R/(R+G+B) ≥ 0.8. Test at the largest size anyone will view. [S15, high]
- **Epilepsy Society:**
  - flashes at 3–30 Hz are the common triggers, up to 60 Hz for some; 16–25 Hz is most likely;
  - the UK Health and Safety Executive recommends club strobes at 4 Hz or less [S38, high; the HSE figure is second-hand].
- **Gate upgrades (my inference):**
  - measure the final composited frame by area;
  - add a rule for saturated red;
  - count cuts and transitions as flashes;
  - detect stripes and radial patterns;
  - force a rest after about 5 seconds of flashing;
  - add a venue mode for projectors that caps brightness and area.
- **Lasers:**
  - ILDA's audience-scanning paper: shows have historically run 5–10× to 100× above the safe exposure limit; ILDA proposes measuring exposure, with a 10× cap; software dims beams below the audience "horizon" [S16];
  - ILDA's basic-safe draft: no exposure to Class 3B/4 lasers [S39, medium; draft];
  - US: any show laser over 5 mW needs an FDA variance; consumer projectors can't legally be sold without one; beams must stay 3.0 m above and 2.5 m to the side of the audience [S40, high].
  - For the rig: keep the lasers virtual. Copy the horizon dimming so a beam sweeping across the camera can't turn into a full-screen flash.

## Gaps

- No primary source found from a hardstyle VJ on visualising kicks, screeches or anti-climaxes.
- Ofcom's own PDF and the EDM.com Lieberman and KCRW pages blocked fetching; ITU and WCAG were used instead of Ofcom.
- The Dutch Q-dance interviews were read through summaries.
- Scratch files are in `<session scratchpad>/vjresearch/`.

## Sources

- **S1** https://help.malighting.com/grandMA3/2.0/HTML/qsg_phasers.html
- **S2** https://help.malighting.com/grandMA3/2.2/HTML/matricks.html
- **S3** https://wiki.pangolin.com/doku.php?id=beyond%3Alivecontrol ; https://wiki.pangolin.com/doku.php?id=beyond%3Aeffects
- **S4** https://blt-guide.deepsymmetry.org/beat-link-trigger/8.0.0/Shows_PhraseTriggers.html
- **S5** http://www.lightingandsoundamerica.com/reprint/Busking.pdf (Brad Schiller, Lighting&Sound America, Dec 2024)
- **S6** https://dj.dancecult.net/index.php/dancecult/article/download/451/457 (Solberg 2014, DOI 10.12801/1947-5403.2014.06.01.04)
- **S7** https://edm.com/interviews/skrillex-fred-again-four-tet-msg-rave-how-ed-warren-designed-lighting-lasers/
- **S8** https://www.syncronorm.com/newsitem/qlimax-2023-interview
- **S9** https://hardnews.nl/en/the-bosses-of-q-dance-and-sensation-about-end-shows/
- **S10** https://pyrotecnico.com/news/how-special-fx-shape-live-concerts/
- **S11** https://www.syncronorm.com/newsitem/defqon1-depence
- **S12** https://twofiftyk.com/en/project/qlimax
- **S13** https://pro.harman.com/insights/entertainment/touring/electrifying-the-edm-environment-with-lighting-and-stage-designer-steve-lieberman/
- **S14** https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf
- **S15** https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
- **S16** https://www.ilda.com/resources/Safety/audience-scanning_overview_latest.pdf (Murphy & Makhov, v2.8, 2012)
- **S17** https://plsn.com/articles/features/gareth-emery-brings-laserface-to-san-francisco/
- **S18** https://www.ableton.com/en/manual/launching-clips/
- **S19** https://tetris.wiki/Random_Generator
- **S20** https://coolhunting.com/culture/interview-alexander-wessely-on-the-end-of-genesys/
- **S21** https://edmidentity.com/2026/01/22/levity-lasers-corbin-sharpe-interview/
- **S22** https://www.vice.com/en/article/steve-lieberman-ultra-music-festival-lighting-interview/
- **S23** https://en.wikipedia.org/wiki/Defqon.1_Festival
- **S24** https://www.eventinspiration.nl/klaar-is-case-s-werelds-grootste-indoor-hardstylefeest-qlimax-werd-unieke-online-audiovisuele-trip/
- **S25** https://www.creativeboom.com/news/tomorrowland-2026s-stunning-designs-highlight-what-creativity-can-add-in-a-sea-of-samey-festivals/
- **S26** https://www.moma.org/audio/playlist/192/2581 ; https://www.awn.com/animationworld/ralph-eggleston-talks-inside-out
- **S27** https://www.backbone-international.com/talks/tpi-qlimax/
- **S28** https://dancingastronaut.com/2019/07/see-how-eric-prydzs-most-ambitious-live-rig-was-made-epic-6-0-holosphere/
- **S29** https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals
- **S30** Rogers & Graham 1979, *Perception* 8:125–134 (no URL)
- **S31** https://festileaks.com/2022/01/jonas-schmidt-is-show-creator-bij-q-dance-in-essentie-speel-ik-met-de-emotie-van-80-000-man/
- **S32** https://www.prismax.com/work/tomorrowland-2025/
- **S33** https://plsn.com/articles/wide-focus/alison-wonderland-awake-tour/
- **S34** https://cdn.rekordbox.com/files/20241216130922/rekordbox7.0.7_lighting_operation_guide_EN.pdf
- **S35** https://en.wikipedia.org/wiki/Hardstyle
- **S36** https://www.hardcultr.com/producer-talk/reverse-bass-hardstyle-explained-2026/
- **S37** https://harderstate.com/viewtopic.php?t=2584
- **S38** https://epilepsysociety.org.uk/about-epilepsy/epileptic-seizures/seizure-triggers/photosensitive-epilepsy
- **S39** https://ilda.com/basicsafe.htm
- **S40** https://www.lasershowsafety.info/us-laws.html

---

## Research angle: craft (verbatim)

# Making VJ hits land harder and never repeat: what game feel, real-time VFX, music research and lighting desks teach

Confidence tags: [H] means I read the primary source myself. [M] means the source is secondary, or I only saw a summary or snippet. [L] means it is my own inference or a suggested starting value, not a sourced fact.

## 0. What the rig does today (read-only look at E:\AI-Setup\arsenal\web\vj.js and vj-core.js)

- **Lasers.** The reason the lasers feel "non-static" is in the code. Each new laser burst takes the next of 4 fixed origins (`f.serial % 4`). Its aim sweeps on a phase set by a per-trigger seed. That seed is a golden-ratio sequence: `seedCounter*0.618034 % 1` in EffectBank.trigger.
  - So the lasers already combine two of the techniques below: cycling through spatial variants, and seeded motion.
  - Weakness: the slot order is a fixed cycle, so after 4 hits it becomes predictable.
- **Shockwave and particles.** They take their origin from the same seed, but only within about ±15% of screen width of the centre.
- **The full-screen effects have no per-trigger variation apart from velocity:**
  - **Flash** is always the same full frame.
  - **Kaleido** always starts at 0° (`u_kalRot = (now - t0) * speed`), and its segment count comes from velocity alone.
  - **Freeze** always zooms from the centre.
  - **Invert** is always the same.
  - **Strobe** runs at a free rate set by a knob (2–12 Hz), with its phase starting at t0. It is not locked to the beat.
  - **Glitch** varies only because it is time-seeded at 14 Hz.
- **Timing.**
  - Pads fire immediately; there is no quantising to the beat.
  - Effect decays are long for 150 BPM: shockwave 1.1 s and laser 0.9 s, each multiplied by 0.6–1.4 for velocity.
  - The pitch-class (chord) smoothing already uses a fast-attack, slow-release envelope: 30 ms up, 250 ms down.

## 1. Impact: the craft

**1.1 Three-phase timing.**
- Game VFX splits every effect into anticipation (wind-up), climax (impact) and dissipation. The flash must land on the exact frame of impact. Instant effects skip the wind-up but still need a graceful fade. [M] https://www.vfxapprentice.com/blog/the-soul-of-effects-what-is-timing-in-vfx
- Riot's 2017 League of Legends VFX style guide adds:
  - a short anticipation, then the peak within the first quarter of the effect, then a smooth dissipation;
  - keep effects short;
  - save the brightest values for the impact point, with the leading edge brightest against dark;
  - make effect size and brightness match the move's importance.
  - [M] https://www.vfxapprentice.com/blog/10-league-of-legends-vfx-design-tips ; official guide at https://nexus.leagueoflegends.com/en-us/2017/10/dev-leagues-vfx-style-guide/
- For us [L]: at 150 BPM a beat is 400 ms. The bright part of a pad hit should mostly clear within one beat. Anything longer should drop to low contrast and opacity (feedback trails), so the next kick reads as a new event.

**1.2 Layer a fast transient over a slow tail.**
- Inigo Quilez's `expImpulse(x,k) = k·x·e^(1−k·x)` is meant exactly for envelopes that "grow fast and decay slowly". It peaks at x = 1/k. His `sustainedImpulse` controls attack and release separately. [H] https://iquilezles.org/articles/functions/
- Broadcast meters show the two speeds people read: PPM peak meters integrate in 5–10 ms, the VU "loudness" meter in about 300 ms. [M] https://en.wikipedia.org/wiki/Peak_programme_meter
- Suggested starting values [L]:

| Layer | Attack | Decay |
|---|---|---|
| Transient | 1 frame or less (≤17 ms), hold 1–2 frames | exponential, 60–150 ms |
| Body | 10–40 ms | 200–400 ms (about 1 beat) |
| Afterglow | — | seconds (feedback trails) |

**1.3 Anticipation, made possible by the beat arriving ahead of time.**
- Disney's principles: anticipation, squash and stretch with volume kept constant, follow-through and overlapping action, slow-in/slow-out. Source book: Thomas & Johnston, *The Illusion of Life* (1981). [H] https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation
- osu! shows each target's "approach" over a fixed lead time before the hit: 1200 ms at approach rate 5, 600 ms at AR 9, 450 ms at AR 10. It fades in over the first two-thirds of that. [H] https://osu.ppy.sh/wiki/en/Beatmap/Approach_rate
- Caveat [H]: Vroomen & Keetels (2010) report that predictive cues and rhythmic sequences make viewers *more* sensitive to timing errors between sight and sound. So an anticipation that lands late hurts more than having no anticipation. https://repository.tilburguniversity.edu/bitstreams/2ba07297-41a3-4ad8-ba1d-6d06732912bf/download
- For us [L]:
  - On kicks: a 5–10% contraction or darken over about 1/16 of a beat (100 ms), released at the hit with overshoot.
  - On drops: a build of 1–4 bars, keyed to phrase boundaries.
  - EDC lighting designer Steve Lieberman describes counting 4/4 phrases to hit changes on the beat, and setting up his console for instant changes. [M] https://pro.harman.com/insights/entertainment/touring/electrifying-the-edm-environment-with-lighting-and-stage-designer-steve-lieberman/

**1.4 Hit-stop (a freeze frame on impact).**
- Sakurai: on impact both fighters freeze; more damage means a longer freeze, with a cap. During the freeze they vibrate, horizontally on the ground and vertically in the air, and the vibration fades through the freeze. [H] https://sourcegaming.info/2015/11/11/thoughts-on-hitstop-sakurais-famitsu-column-vol-490-1/
- Smash Ultimate's formula is about (damage × 0.65 + 6) frames: roughly 5 frames minimum, 30 frames cap, ×1.5 for electric attacks. [H] https://www.ssbwiki.com/Hitlag
- A study of impact feel in action games (Lin et al. 2022):
  - Guilty Gear Xrd freezes 7 frames for light attacks and about 10 for heavy ones.
  - Hit stop, sight-sound coherence and camera control were the three features separating well-liked games from disliked ones.
  - Games lacking hit stop read as "soft and powerless".
  - [H] https://arxiv.org/pdf/2208.06155
- For us [L]: freeze the feedback buffer and motion for 1/32–1/16 of a beat (50–100 ms, 3–6 frames) on accented hits, and up to 1/8 (200 ms) for drops and fusion payoffs. Scale with velocity and cap it. A freeze is not a flash, so it does not spend the flash budget.

**1.5 Screen shake.**
- Eiserloh, GDC 2016 (slides read):
  - Keep a "trauma" value in [0,1]. Each hit adds +0.2 or +0.5, and trauma decays linearly.
  - Shake = trauma² or trauma³, so trauma of 0.3, 0.6 and 0.9 gives 3%, 22% and 73% shake.
  - In 2D, use translation plus rotation together.
  - Drive the shake with seeded Perlin noise, not per-frame random values. Noise feels better, has adjustable frequency, works with pause and slow motion, and replays identically.
  - [H] http://www.mathforgameprogrammers.com/gdc2016/GDC2016_Eiserloh_Squirrel_JuicingYourCameras.pdf
- Shake in a meaningful direction communicates more than random shake. Guilty Gear shakes vertically on a knockdown and horizontally on a sideways slash. [H] the arXiv paper above; also Pichlmair & Johansen, "Designing Game Feel" https://arxiv.org/pdf/2011.09201
- For us [L]: kick shakes vertically, snare shakes horizontally. The slides give no maximum offsets, so mine are guesses: about 1–2% of screen height and 1–3° of rotation at full shake.

**1.6 Overshoot and springs.**
- Penner's easeOutBack with s = 1.70158 overshoots by 10%. [M] https://robertpenner.com/easing/penner_chapter7_tweening.pdf
- Allen Chou's springs are set with a frequency in Hz and a damping ratio ζ, where ζ = ln(fraction left)/(−ω·t). His example is 4 Hz with ζ = 0.23. Below ζ = 1 the spring oscillates; at 1 it settles without oscillating. [H] https://allenchou.net/2015/04/game-math-precise-control-over-numeric-springing/
- For us [L]: kick pulses at about 6–8 Hz with ζ around 0.3–0.5.

**1.7 Contrast, negative space and the flash budget.**
- WCAG counts *either order* of opposing brightness changes (dark-to-bright or bright-to-dark) as a flash, and saturated red has its own limit of 3 per second. [H] https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
- So a dip to black before a hit, followed by a flash, spends a gate slot. Ways to get impact that do not spend the budget [L]:
  - motion, scale and overshoot;
  - hit-stop and shake;
  - displacement;
  - saturation and hue shifts at roughly constant brightness.
- Lighting advice that darkness before the drop makes the drop is common. I found only marketing blogs for it, not a primary interview [L]. Lieberman's quote is about hitting the drop at the exact moment. [M] https://liveforlivemusic.com/features/interview-edc-orlando-light-designer-steve-lieberman/

## 2. Sync and latency budget

| Fact | Numbers | Source |
|---|---|---|
| TV standard, picture **late** (sound first) | detectable at 45 ms, acceptable to 90 ms | ITU-R BT.1359-1 [H] https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf |
| TV standard, picture **early** | detectable at 125 ms, acceptable to 185 ms | same |
| Hammer-hits-peg (impact event) | noticed at 75 ms when video is late vs 188 ms when video is early; feels most simultaneous with video 103 ms early | Dixon & Spitz 1980, via Vroomen & Keetels 2010 [H] |
| Simple flash and beep | detection threshold about 25–50 ms; best-sync point usually slightly vision-first | Vroomen & Keetels [H] |
| Sharp rise times | make timing errors easier to spot; soft rises hide them | same [H] |
| Fast pulses | matching sight to sound breaks down above about 4 Hz | Fujisaki & Nishida, via the same review [H] |
| Display delay | Harmonix's starting video offsets by TV type: CRT 0 ms, LCD 30–50 ms, DLP 60 ms. They calibrate audio and video separately | [H] https://www.harmonixmusic.com/blog/how-to-calibrate |
| Musical control | 10 ms or less, with jitter of 1 ms or less. Timestamps trade jitter for latency | Wessel & Wright 2002 [H] https://arxiv.org/pdf/2010.01570 |
| Browser canvas | the `desynchronized: true` context hint skips the compositor queue, works for WebGL2, may tear; over 50 ms hurts hand-eye coordination | [H] https://developer.chrome.com/blog/desynchronized |
| Touch to visual | about 6 ms perceivable (range 2–11) when dragging; 64 ms detection threshold for the "land-on" moment | Ng et al. 2014, citing Ng 2012 and Jota 2013 [H] https://sites.ualberta.ca/~wfb/publications/C-2014-SIGCHI-Latency.pdf |

What this means for us [L]:
- Aim for the visual to land between 30 ms early and 15 ms late of the audible beat. Early is the safe side.
- Schedule from the beat that arrives ahead of time, minus a display-latency offset. Expose it as a per-venue "visual offset" knob, calibrated the way Harmonix does it.
- At 150 BPM, kicks run at 2.5 Hz, below the 4 Hz limit, so their sync is judged: spend the precision there.
- 16th-note hats run at 10 Hz, above it, so hat sparkle can be texture rather than tightly synced.
- Effects driven by detected onsets (rather than the beat grid) arrive late: capture, a 23 ms analysis frame, peak picking, render and display. Give them softer rises of 30–60 ms to hide that lateness.

## 3. Variation without chaos

**Why exact repeats feel weak.**
- The brain's response drops when the same stimulus repeats (repetition suppression). [M] Grill-Spector, Henson & Martin 2006, TICS 10(1):14–23
- Kate Compton's "10,000 bowls of oatmeal" problem: things that are mathematically unique still look like more oatmeal. "Perceptual uniqueness is the real metric." What matters is being perceptibly different from the last one. She also notes that people like seeing evidence of process and forces, and that shuffling a deck of options stops the same pick coming up twice. [H] http://www.galaxykate.com/buildagenerator-kcompton.pdf
- For us [L]: vary what the eye reads first (position, direction, silhouette, colour), not micro-detail. Never jitter the onset time.

**Techniques:**
1. **Seeds you can replay.** Hash a per-trigger counter on the GPU; PCG3D is the best quality/speed balance per Jarzynski & Olano 2020. [H] https://jcgt.org/published/0009/03/02/paper.pdf
   - Log the seed with every trigger, so recorded sets can be replayed exactly; Eiserloh makes the same replay point for noise. [L]
2. **Placement with low-discrepancy sequences.** The golden-ratio step (×0.618034) already in use spreads 1D values. For 2D, the R2 sequence uses steps of 0.7548777 and 0.5698403. [M] https://blog.demofox.org/2022/02/01/two-low-discrepancy-grids-plus-shaped-sampling-ldg-and-r2-ldg/ and https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/
3. **Mitchell's best-candidate.** Pick k random candidates and keep the one farthest from earlier points. This avoids both clumps and gaps. [H] https://bost.ocks.org/mike/algorithms/
   - For us [L]: k = 8, measured against the last 4 anchors.
4. **Anchor placement to the music.** People consistently match high pitch with small, bright and high up. [M] Spence 2011, https://link.springer.com/article/10.3758/s13414-010-0073-7
   - For us [L]: hats go small and high, kick goes big and low, chord-tied effects emit from the chord-constellation position.
5. **Random but never repeating.**
   - Unity's random audio container has Shuffle (pool empties as clips play) and "Avoid Repeating Last N". [H] https://docs.unity3d.com/2023.2/Documentation/Manual/AudioRandomContainer-UI.html
   - Games keep several sound clips for frequent attacks to avoid fatigue (arXiv paper above).
   - Spotify replaced pure random shuffle with evenly spaced slots plus a random offset and jitter, inspired by dithering. [M] https://engineering.atspotify.com/2014/02/28/how-to-shuffle-songs/ (I could not render the page, so this is from secondary summaries.)
   - For us [L]: give each effect 3–5 hand-designed variants, drawn from a shuffle bag that avoids the last 2.
6. **Distributions.** Tyler Hobbs uses a clamped Gaussian for "consistent but varied" values and a power law for many small values with rare big ones. [H] https://www.tylerxhobbs.com/words/probability-distributions-for-algorithmic-artists
   - Starting values [L]: scale ×(0.85–1.15) with σ about 0.07; hue within ±15° of the palette; a rare "hero" variant about 1 hit in 6–8, timed by the shuffle bag.
7. **Phase spread across elements.** grandMA3 phasers spread fixtures around a 0–360° loop so they do not move in unison. "Shuffle" randomises the order but repeats it until reshuffled. [H] https://help.malighting.com/grandMA3/2.0/HTML/qsg_phasers.html ; [M] https://forum.malighting.com/forum/thread/4445-random-based-effects/
   - For us [L]: reshuffle on every trigger, for laser beams, particles and strobe bars.
8. **Noise fields over random.** Use Perlin noise for motion (Eiserloh). For the Swarm, curl noise gives a divergence-free, fluid-like flow from Perlin noise. [H] https://dl.acm.org/doi/10.1145/1275808.1276435
9. **Two levels of seed** [L]. Compton says pure random distribution fails on structured material like music.
   - A phrase-level seed (per 8 or 16 bars) picks the look family and palette. That keeps a phrase coherent and avoids chaos.
   - A hit-level seed picks position, angle and variant. That keeps every hit different and avoids sameness.
10. **Escalate instead of repeating** [L]. Repeated pad hits accumulate "trauma" (Eiserloh's model), stepping to bigger variants and then decaying back. This fits Daniel's "the second press is a question" principle.

## 4. Audio-reactive specifics

- **Four signal types per frequency band.** Synesthesia's are a clean blueprint. [H] https://app.synesthesia.live/docs/ssf/audio_uniforms.html and https://app.synesthesia.live/docs/ssf/best_practices.html
  - **Level:** smoothed loudness, drives the body layer.
  - **Hits:** isolated transients, drive the transient layer.
  - **Presence:** sustained activity that ignores individual hits, drives scene intensity and palette.
  - **Time:** a clock that runs faster when the music is loud. Use it to drive motion, so energy sets speed rather than position; that avoids jitter.
  - **Beat signals:** OnBeat, ToggleOnBeat, RandomOnBeat (a new value each beat with an S-curve glide), BeatTime, and BPM confidence.
- **Fast up, slow down.**
  - Eiserloh's "asymmetric asymptotic averaging": different weights for rising and falling. 0.01 per frame at 60 fps is slow, 0.1 fast, 0.5 very fast. Scale the weight by time-scale. [H] (slides above)
  - TouchDesigner's Lag CHOP has separate up and down lags (time to follow 90% of a change) plus overshoot. [H] https://docs.derivative.ca/Lag_CHOP
  - Its Trigger CHOP adds hysteresis (separate trigger and release thresholds), an ADSR envelope and a re-trigger delay. [H] https://docs.derivative.ca/Trigger_CHOP
  - Resolume's FFT control exposes band, gain and fall. [H] https://resolume.com/support/en/parameter-animation
- **Live onset detection (Böck et al. 2012).** [H] https://www.cp.jku.at/research/papers/Boeck_etal_ISMIR_2012.pdf
  - Spectral flux on a log-filtered spectrogram, 23 ms frames, 10 ms hop (100 frames/s).
  - With no look-ahead, a frame counts as an onset if it is the maximum of the last 3 frames (30 ms), exceeds the mean of the last 4–12 frames (40–120 ms) plus a threshold, and comes at least 3 frames (30 ms) after the previous onset.
  - Evaluation tolerance was ±25 ms. The detector catches an onset about one frame before people perceive it.
- **Beat-quantised vs free pad hits.**
  - Ableton's launch quantisation snaps a trigger to a bar, 1/4, 1/8 or 1/16 grid. [H] https://www.ableton.com/en/manual/launching-clips/
  - Taps usually come a few tens of ms before the beat. The lead shrinks for musicians, with sound feedback on each tap, and at faster tempi. [H] Repp 2005, http://users.df.uba.ar/anita/f1_labo/clase1/repp%20psycho%20bull%20rev%202006%20synchro%20tapping%20review.pdf
  - Proposed hybrid [L]: answer instantly with a small spark and the pad LED. If the press is up to about 1/16 early, land the effect's body on the next grid point; otherwise fire immediately.
- **Streak-meter timing windows.**
  - In The Groove: ±21.5 / 43 / 102 / 135 / 180 ms. [M] https://rwong.wordpress.com/2010/07/18/itg-dedicab-and-ddr-arcade-timings/
  - osu!: 80−6·OD, 140−8·OD and 200−10·OD ms (at OD 5: 50, 100, 150 ms). [H] https://osu.ppy.sh/wiki/en/Beatmap/Overall_difficulty
  - [L] Centre the windows on each player's own measured average offset, not on zero.

## 5. Translating to our 12 pads [L]

| Effect | Changes |
|---|---|
| Shockwave | Anchor to the music using best-candidate placement; aspect jitter ±10%; rare double-ring variant; bright ring fades within about 1 beat. |
| Laser | Shuffle the slot order per bar instead of `serial % 4`; fan count ±1; sweep direction from the seed. |
| Flash | Variants: radial burst from the anchor, wipe in 4 directions, iris ring, vignette-out. Each is a 1-frame transient with 80–120 ms decay, still through the gate. |
| Glitch | Seed the block layout from `f.seed` (not just the 14 Hz clock); alternate displacement direction. |
| Strobe | Lock the rate to beat subdivisions and the phase to the grid; reshuffle bar order and orientation each trigger. |
| Particles / Swarm | Seeded emission cone; curl-noise field with a per-trigger seed offset. |
| Kaleido | Start angle seed·2π/N; segment count from velocity ±2 (kept even); spin direction from the seed. |
| Freeze | Zoom from the anchor, not the centre; seeded drift. Doubles as the 50–100 ms hit-stop on accents. |
| Invert | Variants: full invert, hue rotation, channel swap, radial mask expanding from the anchor. |
| Combos | Escalate through the trauma-style accumulator. Hit-stop plus directional shake as the payoff, which needs no flash. |

## 6. Gaps

- **Not found:** a primary festival-VJ interview on variation, a primary source for "blackout before the drop", and numbers from Nijman's "Art of Screenshake". The talk is at https://www.youtube.com/watch?v=AJdEqssNZ-U ; it lists "sleep" (hit pause), "less accuracy" (random bullet spread) and directional camera kick, but I saw only secondary summaries. [M]
- **Unchecked:** "Juice it or lose it" (Jonasson & Purho, GDC Europe 2012) at https://www.gdcvault.com/play/1016487/juice-it-or-lose is cited from search summaries only. [M]
- **My own starting values:** the shake magnitudes, jitter ranges and spring settings tagged [L] in sections 1 and 3 are proposals to tune live, not sourced numbers.

Scratch copies of the source PDFs and text are in <session scratchpad>/vjresearch/ (eiserloh, vroomen, bt1359, compton, boeck, repp, impact, wessel2, blink, pichlmair).
