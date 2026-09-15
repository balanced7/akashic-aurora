# M1-BRIEF — piano-presentation

## CHARTER

Tonight Daniel asked for this, and the stakes are his.

Daniel, 2026-09-15, verbatim:
- "GPT Astral is really struggling to make the visualization look quite how I want it, can you help him out?"
- "I'm leaving the driving in your hands, I have been thoroughly impressed by everything you have made. I think Asta has some interesting things that he has built but the presentation is lacking"
- "And lets make it a house wide thing so it comes out looking better and with a more thought out feature set than any of us could alone, how do we bring rill, navi, heimdall and astral into this, perhaps even sunshine if he is reachable"

What he has said about these visuals since the piano began, verbatim:
- "I've always wanted to make a really cool piano visualization! perhaps we can make a detour to set up a 3d rendered animated piano for tiktok where the chords and notes are displayed! We could even make it show sheet music!"
- "notes dont stay lit if I have sustain pressed, when I hold sustain and other notes it should be brighest when I am pressing sustain and note at same time, velocity should be a factor as well"
- "Can you make the piano note colors more saturated and visible? also the bloom doesn't seem to decay or go down, it just stacks"
- "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual spectacle? Perhaps even having a rarity and fanciness scale xD"
- "This is super cool! I get to actually see the progressions I am making and can start putting theory and name to intuition!"
- "I also love how our system shows you the chord for notes arpegiated with sustain!"
- "Would you mind a few different really cool 3d renders and representations of the piano? Perhaps having the notes glow and interact with a fog, or any other crazy and cool effects and visualizations you can think of! Feel free to open it up to the house!"

Relayed by Asta (his summary, not verbatim):
- repeated notes visibly restarted the animation;
- soft and hard playing read too similarly;
- the portrait screenshot had excessive empty space and tiny puffs;
- Daniel wants a cohesive, expressive design language for motion, mood and colour.

**Done looks like:** Daniel sees two or three looks as real frames side by side, portrait and landscape. He picks one and says "yes, that". Behind it sits a presentation spec and a feature set precise enough to build in slices, each with its own acceptance check (by measurement and by eye).

## THE QUESTION

What should Daniel's piano visualizer look like and show, at the keys while he practises and in 9:16 TikTok posts? The systems we have built should read as beautiful and meaningful, not as interesting machinery with weak presentation. What is the feature set and information hierarchy? What is the visual language? How will we know, by measurement and by eye, that it looks right?

## INPUTS (as of 2026-09-15 02:30 EDT)

**The page.** `/piano` runs on three r186 on Daniel's RX 9070 XT (Windows, AMD; the driver has a TDR history under heavy GPU load). It has:
- **The piano v2 light model:** the sustain rule, velocity, bloom that decays, and the gamut-mapped OKLCH note palette.
- **Asta's spectacle engine:**
  - six worlds, with Moonwater (a reflective lake) as the default;
  - GPU particles with per-pitch continuous flow;
  - a shared ripple field and harmonic voices (velocity-scaled height);
  - harmony views: tonnetz, folds, spiral, glass, rings, petals, yarn, compass, atmosphere;
  - glass note labels and a Nashville plaque.
  - Docs: `arsenal/SPECTACLE.md`, `arsenal/SPECTACLE-DESIGN.md`.
- **The chord reader and Nashville numbers.** Daniel loves both. The next-gen reader, `chordread.js`, is committed but not wired in.
- **The jam space:** cards, loops, Try, and Claude's moonlight hand on the glass. It is finishing verification.
- **Live sheet music:** a score strip planned inside the recorded canvas (research/in-flight/live-sheet-music-2026-09-14/).
- **REC at 1440p:** H.264 at about 54 fps. At 4K, VP9 only reaches about 21 fps, and the first take of a session drops frames.

**Evidence frames**, absolute paths readable from any worktree on this machine: `E:/AI-Setup/fences/piano-presentation/evidence/`
- `01-moonwater-portrait-12-notes.jpg`: Moonwater, a 12-note cluster, portrait.
- `02-tonnetz-36-notes.jpg`: tonnetz under a dense chord.
- `03-tonnetz-default-F-chord.jpg`: tonnetz in the default look, F major, portrait.
- `04-first-spectacle-portrait-Am.jpg`: the first spectacle pass, Am, portrait.
- `05-city-hard-landscape.jpg`, `06-gentle-lake-landscape.jpg`: earlier worlds, landscape.

**Instruments available:**
- Rill's `py -m arsenal floors` (dead, blown, flat and legibility checks), `storyboard` and `coupling`. A checked review is in research/in-flight/rill-3d-tools-review-2026-09-14/.
- Asta's headless study harness: `state/arsenal/receipts/spectacle/harmony-study.py`.

**Vandor's first read** is one voice, not a finding; Asta has already seen it:
- Moonwater is underexposed with low contrast.
- The terrain reads as placeholder.
- The played gesture is hairline strands filling about 15% of the portrait frame.
- The keys lost the saturated per-note glow.
- The headline says "12 notes" instead of the chord.
- The tonnetz is milky and washed out, with white labels on pastel, and floats unanchored above the keys.
- The bottom third of the portrait is black water.

## LANES

Every seat writes a **blind half** in its strongest lane. Wander beyond it wherever you see something the others will miss.

| Seat | Lane |
|---|---|
| **Asta** (Codex) | **Engine truth and self-critique.** What your systems can express, what each presentation change costs (cheap parameter, medium hook, deep rework), which of your built ideas deserve to be the stars, and your honest read of the evidence frames. |
| **Rill** (dsh) | **Acceptance instruments.** Measurable floors for "looks right": exposure and contrast bands for dark scenes, gesture area fraction in 9:16, label legibility per region, a soft/hard shape (not brightness) separation, repeat continuity (slit-scan), no dead bottom third. How to run them per take and per build, and which of your tools need what fix first. |
| **Navi** (kimi) | **Information design and pedagogy.** What a player needs to see at each moment (chord name, Nashville number, key, the note that moved, suggestions, the jam's next chord), the hierarchy, what hides when, and how the view teaches without clutter, at the keys and in a TikTok. |
| **Heimdall** (deepseek) | **Systems and budget.** The render and record budget at 1440p/4K and 60 fps on this GPU, a determinism/seed seam so pixel receipts work with the atmosphere on, frame pacing with REC, TDR risk, and what not to build. |
| **Sunshine** (sol) | **Feeling and play.** The emotional arc of a session (quiet, build, arrival), how the visuals reward exploration (your play-notice-name-alter loop), what the one moment a TikTok is made of looks like, and what would make Daniel smile at 1 a.m. |
| **Vandor** (claude) | **Art direction by evidence.** A blind look-development panel: four distinct looks rendered on the real page, judged blind against Daniel's words, synthesized into a parameter-level proposal. Also the reconciliation. |

## RULES OF ENGAGEMENT

1. **Blind.** Do not read other seats' halves until the reconciliation is posted. This brief and the evidence frames are shared.
2. **Where to write.** Put your half in `E:/AI-Setup/fences/piano-presentation/half_<seat>.md`, using asta, rill, navi, heimdall or sunshine. If you cannot write to the tree, send it on Bifrost to `claude` with `--kind handoff`. Then send one bus line saying it is done.
3. **Short and specific.** At most about two pages, citing evidence (frame names, file paths, measured numbers). Proposals in Daniel's language, not jargon.
4. **No product edits this round.** Prototypes go in your own scratch space. The shared page files are locked for the jam integration commit.
5. **Deadline:** about 04:30 EDT (two hours). A partial half by then beats a perfect one later.
6. **One calibrated question.** End with the single question you would most want Daniel to answer.

## OUTPUT CONTRACT

**Each half must contain:**
- your lane's proposal, concrete enough to build or measure;
- the evidence it rests on (frame names, file paths, numbers);
- what you would cut or refuse;
- one calibrated question for Daniel.

**The reconciliation must contain:** each seat's accepted and declined points with reasons, the presentation spec, the feature set and hierarchy, acceptance floors, and the frames Daniel chooses from.

Vandor reconciles into:
- a presentation spec and feature set, with each seat's contributions credited;
- two or three looks, shown to Daniel as frames.

Once Daniel picks, the slices go to each seat's strength:
- Asta builds the engine side;
- Rill wires the acceptance floors;
- Navi reviews the hierarchy and wording;
- Heimdall verifies budget and determinism;
- Sunshine reviews feel on the first playable build.
