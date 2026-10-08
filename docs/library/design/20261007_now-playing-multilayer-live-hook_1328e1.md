---
akashic_id: art_20261007_now-playing-multilayer-live-hook_1328e1
akashic_sha: bfb920af45af
schema_version: 1
status: current
type: design
arc: media-suite
date: 2026-10-07
title: now-playing-multilayer-live-hook
gist: "Spotify now-playing on /piano: palette bleed, lore reveal, cited facts, Claude co-performer, multilayer hook; 16 slices; content-system frame"
visibility: fleet
body_type: markdown
seats: [claude]
category: [agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20261007_second-press-gentle-hints_db25d1
    rel: discusses
created: "2026-10-07T23:20:10"
updated: "2026-10-07T23:20:10"
---
<!-- GENERATED PROJECTION of art_20261007_now-playing-multilayer-live-hook_1328e1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# now-playing-multilayer-live-hook

# Now Playing on the piano stage — the multilayer live hook

Status: design + slice plan, co-designed live on the night of 2026-10-07 (Daniel + Vandor). Nothing is built yet. Arc: media-suite (the /piano visualizer). This is format one of a broader content system (see "The frame").

## Daniel's words (verbatim)

1. "I have a really fun idea, how do we integrate a toggleable option to display the track playing on spotify and its album art in the piano visualizer in a stunning way, we could even cycle facts about the artist while i improvise over the track, this has great content potential"
2. "We could even have a deciding theme animation! as the album art is selected and it modifies the piano into an art style that resembles memorable parts of the artists lore and perhaps their favorite melodies or their famous riffs, or funny insider knowledge gags or facts. memorable things like birthdays or other famous or odd facts. this can become an engaging passive hook"
3. "we could even go wild and experimental with it where you try to make the visuals and pull in facts live, being an active participant, showing off the music as well as the systems integration and presentation. a DEEP hook xD"
4. "I love this save it durably and lets break it down into slices. we could even have a box that shows the shaders running, or it could be an element that fades in and out. I want to have a multilayer hook that appeals to specialists in different things. the engineers would notice system inegration, music buffs would spot the chord progressions more modes, the vfx artists would notice the cool bpm synced visuals, we could poll from spotify or build our own database or source public ones, then we could make some cool transitions with colors"
5. "the whole progression of the system we are building is itself another form of subtle narrative, we could have ideas and themes between each video. we can start thinking of our own content strategy and cadance. I am trying to build a system that makes it for me to produce viral videos that show facts about various musicians or do a deep dive on the legendary guitar being used, or other cool facts, what movie it was used in and perhaps a video snippet of that, we could pull and cut specific clips for things as well as showcase our own visualization tools as we build them"

## The vision

Daniel improvises on the KeyLab over whatever Spotify is playing, and the piano visualizer knows what's playing. It wears the album: the cover is a lit object on stage, and its palette bleeds through the keys, light and atmosphere. A theme-reveal animation transforms the piano into the artist's world, and grounded facts cycle at musical moments.

At its wildest, Claude performs alongside him live:
- steering the visuals;
- writing shaders that hot-swap mid-song;
- answering his phrases through its MIDI out.

Every layer rewards a different specialist:
- engineers see the systems integration;
- music buffs see the harmony and mode analysis;
- VFX artists see the beat-synced visuals and the live shader code;
- fans see the artist lore;
- casual viewers just see something beautiful.

## The frame: the build is the narrative, and the piano is format one

Daniel's goal is bigger than one feature. He wants a system that makes it easy for him to produce music videos:
- facts about musicians;
- deep dives on legendary instruments, such as the guitar on a famous record;
- where a song or instrument appeared in film, with a clip;
- showcases of the visualization tools themselves as they are built.

**The build is itself the narrative.** Each video can show the system one capability further along, so the series has an arc and themes can thread between videos. Viewers come back to see what the tool does next. The house already writes its own story (chronicle atoms, the `story` verb). What of that becomes public is Daniel's call, in his own voice.

**Format pillars (first sketch, for the strategy round):**
1. **Performance.** Daniel improvises over a track on the now-playing stage (this design).
2. **Deep dive.** An artist, a legendary instrument, a song's history or its film appearances, built from cited facts with sources on screen.
3. **Build log.** A new visualization tool shown as it comes online. This is the engineers' format and the narrative spine.

Each pillar seeds the next: a deep dive on an artist, then a performance over their track, then the build log of the tool that made the reveal.

**Pipeline pieces that already exist:**
- yt-dlp + ffmpeg (the media suite);
- `py -m arsenal tiktok`: vertical 1080x1920, --from/--to cutting, silence trim, loudnorm;
- the `captions` verb (transcripts);
- arsenal/present (scene → slides / ui / three.js);
- web fetch and the research verbs.

**What's new:**
- a clip library that records each clip's source and license;
- a fact store with citations, shared with the S6/S7 dossiers;
- an episode planner for themes, series arcs and cadence.

**Two flags that grow with volume:**
1. **Rights.** Film clips and commercial recordings are copyrighted.
   - Commentary and education using short, transformed excerpts is where fair use is strongest. But fair use is decided case by case, platforms auto-claim and mute, and downloading from YouTube breaks its terms.
   - So the system is rights-aware by design: short clips with real commentary over them, every clip's source and license recorded, and licensed, official, Creative Commons or public-domain sources preferred.
   - Get a proper rights check before monetizing at scale. [This is not legal advice; VERIFY before monetizing.]
2. **Accuracy.** Instrument provenance ("which guitar was on which record") is where confident errors live, and guitar communities catch them fast. Every fact is cited and checked against a primary source before posting. Putting sources on screen can be a brand feature that specialists respect.

## Design principles

1. **Two tiers.**
   - The LIVE PLANE is automatic and works for any track: now-playing, art, palette and beat.
   - The LORE PLANE is curated and deepens over time. It holds per-artist dossiers: themed world, signature riff, curated gags and a reveal script.
   - Every track gets something stunning, and favorite artists get the bespoke magic. This is the same paved-road-then-deepen shape as the one-world UI.
2. **Director vs orchestra.** A model thinks in seconds; music happens in milliseconds.
   - Claude directs at each track change: it retrieves, chooses the world, queues facts and may write a shader.
   - The page performs locally, revealing on musical cues: a key match, a riff quote, an energy peak.
   - Fetch ahead, reveal on the beat. The model never gates a beat.
3. **The multilayer specialist hook is the one-world UI applied to content.**
   - Specialist layers are the stance regions.
   - Per-audience presets are the modes.
   - Fading in and out is the tier ladder.
   - No layer shouts over another, and the performance is never covered. Each specialist community shares the video for its own reason.
4. **Color on three timescales**, following the visual-quality baseline's layered timescales:
   - the album palette over minutes, morphing on each track change;
   - harmony over seconds: tension and mode from harmony-feel shift the hue within the palette;
   - beat pulses at sub-second scale.
5. **Graceful failure.** If Spotify, the network or the model is slow or wrong, the automatic layer carries the show. It is never blank and never shows a broken frame. Live shaders hot-swap through safe compile, so a failed compile keeps the previous shader running.
6. **Facts are grounded.**
   - Every fact comes from a retrieved source with a citation. The model drafts only from retrieved text, never from free recall.
   - Live facts are high-confidence only, such as birthdays from Wikidata or verified trivia.
   - Funny insider gags are curated by Daniel into dossiers.
   - A wrong fact about a real person costs more in front of an audience than in chat.

## Data sources, each used for what it does best

- **Spotify Web API: what's playing.**
  - `GET /me/player/currently-playing` returns the track, artists, album, art URLs and progress_ms; artist genres come from the artist endpoint.
  - Daniel authorizes once with OAuth. The token and refresh token live in the house secret vault, never in plaintext. Scopes are read-only: user-read-currently-playing and user-read-playback-state.
  - [VERIFY in S0] Spotify's Nov 2024 Web API change closed Audio Features and Audio Analysis (tempo, key, mode, beat grids) to new apps, along with Related Artists and Recommendations. So a new app cannot get BPM or key from Spotify.
  - [VERIFY in S0] that currently-playing works for Daniel's account in development mode.
- **Our own ears: beat and key.**
  - The Focusrite exposes a "Loopback L + R" capture endpoint (seen in the device list on 2026-10-07).
  - /piano already selects audio inputs (audio-select, listAudioInputs) and feeds audio data to the atmosphere.
  - So the page can hear the track. Onset and beat detection give BPM and a beat clock, and chroma gives a key and mode estimate. This is more accurate to the moment than any metadata.
- **Public sources: grounded facts and metadata.**
  - Wikidata: structured birthdates, birthplace, instruments and labels.
  - Wikipedia: bios and notable trivia.
  - MusicBrainz: IDs, relationships and discography.
  - Last.fm: tags and bios (free key).
  - GetSongBPM: per-track BPM and key, free with attribution, used to cross-check the ears.
  - [VERIFY each source's current terms and rate limits in S6.]
- **Our own dossier store: the curated lore.**
  - state/arsenal/dossiers/<artist-id>.json, with GET/PUT like the looks store (the arsenal/pianolooks.py precedent).
  - It holds the theme, palette overrides, curated gags with citations, the signature riff (MIDI) and the reveal script.
  - It grows over time, and Daniel gates what goes in.

## What already exists (verified 2026-10-07)

- **Claude's hand on the piano:** `arsenal/pianocue.py` + `arsenal/web/piano/cues.js` — ghost keys, moonlight keys, the cue chip and the glass view during REC.
- **Claude's MIDI out** in `piano.js` (cueMidiOutName). Claude can play notes, and an echo guard makes sure Claude's notes never count as Daniel's.
- **Claude's jam band:** `arsenal/band.py`, with bar/pass position shown in the HUD.
- **The page reads Daniel's playing live:**
  - `moment.js`: energy, pace, pulse, flow, density, intensity, arc, mood;
  - `harmony-feel.js`: lushness, tension, brightness, openness and the bass-solo dance;
  - `harmony-model.js` and `harmony-renderer.js`.
- **Theory organs:** chord reader, speller, Nashville numbers, key signature, and the minor/mode/boundary selects (workbench ids nns-select, minor-select, key-select, boundary-select).
- **Beat organs:** the metronome and its external beat reference (metro-* controls).
- **Claude's voice on the page:** `conversation-dock.js` / `conversation.js`.
- **The /play preset system:** GLSL `.frag` presets with safe compile. A failed compile rejects with err.kind compile or link and the running preset stays. Rescan hot-reloads.
- **Recording:** REC at 30fps → `POST /api/recordings`, and `py -m arsenal tiktok` exports vertical video.
- **Server patterns:** serve.py routes and the store pattern (`/api/piano/looks` GET/PUT).

## Slice plan

Each slice ships independently and adds a new video hook, so the build log writes itself. Visual slices meet the visual-quality baseline acceptance: native-resolution render, frame-time p95, switching and dispose, REC-safe.

### Phase A — Live plane (the first show)

- **S0 Spotify spike.** Gated on Daniel's one OAuth click.
  - Register a Spotify app, authorize it, and confirm currently-playing returns the live track and art.
  - Verify dev-mode access and the audio-features closure.
  - Exit: a terminal print of Daniel's live track.
- **S1 /api/nowplaying.**
  - serve.py polls Spotify every 3–5 s, rate-limit-safe with backoff on 429, and refreshes the token from the vault.
  - The page client shows smooth local progress between polls.
  - Exit: the page shows title, artist and progress in sync.
- **S2 Now Playing look.**
  - A toggle in the Studio.
  - A title/artist card in the house serif that fades in on each track change.
  - The album art as a lit object in the 3D stage (a glass slab or a slow-spinning vinyl) over a soft blurred backdrop.
  - Off means zero overhead. Builds on the looks host and loadFonts.
- **S3 Palette bleed.**
  - Extract dominant and vibrant colors from the cover client-side (downsample + quantize).
  - Feed them to the keys, light and atmosphere, and morph over a beat or two on each track change.
  - Builds on the atmosphere and key paint (applyClassicLook / paintBlackKeys).

**First-show cut:** S0–S3, plus S9, which is mostly built already.

### Phase B — Beat and harmony

- **S4 Ears.**
  - Select the Focusrite loopback as the audio input.
  - Onset and beat detection give BPM and a beat clock; a chroma estimate gives key and mode.
  - Cross-check against GetSongBPM when available.
  - Builds on audioIn and the metronome's beat reference.
- **S5 Color on three timescales.** Compose album (macro), harmony (meso) and beat (micro) without them fighting each other. Measure it, and no strobing.

### Phase C — Lore plane

- **S6 Facts pipeline.**
  - At each track change, resolve the artist (MusicBrainz ID) and retrieve from Wikidata, Wikipedia and Last.fm.
  - The model drafts candidate facts from the retrieved text, each with a citation and a confidence.
  - Live shows high-confidence facts only. Results are cached per artist.
- **S7 Dossier store.**
  - state/arsenal/dossiers, with GET/PUT.
  - Schema: theme, palette overrides, curated gags with citations, riff MIDI, reveal script, birthdays and anniversaries (for a "today is X's birthday" hook).
- **S8 First dossier + the theme reveal.**
  - Artist #1, Daniel's pick, built end to end.
  - The reveal animation: the palette locks, the world morphs into the artist's style, the signature riff ghosts across the keys, and the first card appears.
  - This is the experiment that proves the magic on camera before anything scales.

### Phase D — The specialist layers (the multilayer hook)

- **S9 Theory layer.** Chord names, Roman and Nashville numerals, the mode name and mode color, and a progression strip. Mostly exists already; surface it as a layer.
- **S10 Shader box.**
  - A panel that fades in and out, showing the running shader's code and its live uniforms (time, bpm, palette).
  - Legible, beautiful, and out of the performance's way.
  - When Claude writes a shader live (S14), the code types in here, compiles and becomes the visuals.
- **S11 Systems layer.**
  - A "what Vandor noticed" caption: the reasoning already streamed to Bifrost, shown on stage tastefully.
  - Light telemetry: latency, fps, model calls.
- **S12 Layer conductor.**
  - Per-audience presets as modes: Theory, Systems, VFX, Fans, Clean.
  - Layers rotate, or one is chosen per video.
  - One-world UI rules apply: space is proportional to the decision it enables, and nothing goes over the keys.

### Phase E — The co-performer (wild)

- **S13 Director loop.**
  - At each track change Claude retrieves, chooses the world and queues facts.
  - The page reveals on musical cues: key match, riff quote, an energy peak via moment.js.
  - Smallest proof: one real musical event answered live within a beat or two.
- **S14 Live shader.** Claude authors a GLSL preset inspired by the album. It types into the shader box and hot-swaps mid-song through safe compile.
- **S15 The duet.** Claude answers Daniel's phrases through its MIDI out (band.py), and the ghost keys show its reply.

## Cross-cutting

- **Reboot** before the first live or recorded show. On 2026-10-07 the kernel pool was past the 2026-09-11 outage line.
- **Secrets:** the Spotify client secret and refresh token go in the vault (AKASHIC_SECRETS_DIR), never in the repo.
- **Rights** [VERIFY before public or monetized posting]:
  - Spotify's developer policy restricts some uses around syncing Spotify content with visual media. Check the current terms.
  - The original track's audio in a posted video is a platform-licensing question. Options: TikTok's licensed sound library, or posting Daniel's piano and the visuals only.
  - Clips: see the rights flag in "The frame".
- **Facts:** grounded-only live, gags curated, and a citation kept with every fact.

## Open decisions (Daniel's)

1. Artist #1 for the first dossier.
2. How far the album takes over. Vandor recommends the full palette-bleed version.
3. How wild the first co-performer rung starts: VJ + commentary, or straight to the duet.
4. Per-video layer presets: which specialist layer leads each video.
5. The content-strategy round: cadence, series themes, how the pillars rotate, and how the build arc is told. This is its own design round, possibly opened to the house like the one-world UI.

Related: art_20261007_second-press-gentle-hints_db25d1 (the one-world UI). Its stance regions, modes and tier ladder are the same machinery as the specialist layers.
