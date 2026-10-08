---
akashic_id: art_20261007_presentation-grammar-screens-scenes_236d39
akashic_sha: bc97a0658769
schema_version: 1
status: current
type: design
arc: media-suite
date: 2026-10-07
title: presentation-grammar-screens-scenes
gist: "Precise inside, elegant outside: claim passport, stage translation, screens (sources x treatments x placements), scenes and musical spells"
visibility: fleet
body_type: markdown
seats: [claude]
category: [agent-lifecycle, tooling]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20261007_now-playing-multilayer-live-hook_1328e1
    rel: discusses
  - target: art_20261007_fact-sourcing-provenance-ladder_84c3e2
    rel: discusses
created: "2026-10-07T23:40:35"
updated: "2026-10-07T23:40:35"
---
<!-- GENERATED PROJECTION of art_20261007_presentation-grammar-screens-scenes_236d39 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# presentation-grammar-screens-scenes

# Presentation grammar: screens, scenes and the elegant surface

Status: design, co-designed live on the night of 2026-10-07 (Daniel + Vandor). Nothing is built yet. Arc: media-suite.

This is the presentation layer for the now-playing stage and every content format (art_20261007_now-playing-multilayer-live-hook_1328e1). It is also the backstage-and-stage completion of the sourcing rules (art_20261007_fact-sourcing-provenance-ladder_84c3e2). The claim passport lives here because the doc door cannot yet revise the draft contract (wish filed in docs/WISHLIST.md, 2026-10-07).

## Daniel's words (verbatim)

1. "to refine it a touch further, rules, laws, type of claim, scope of claim, time of claim, source or authority. can you riff on this further" / "as well as timeliness and time scope of claim. is this a short lived thing or a long lived thing"
2. "we can do both and we need to find a natural not too in your face way of doing so for the presentation. our internals are precise and robust, our presentation elegant and wise. people also love seeing visualizations like points on a timeline with facts or drawing your attention to a wonderful facet, kinda like how xkcd does on random subjects."
3. "to riff even further for feature ideas, we could have various video presentation buffers and shaders. play video, is in a buffer, shader can present it as a holograph on steam, as a cool stylized led tv screen, or any other really cool and visual striking shaders or presentation methods people have come up with, perhaps a badge can appear somewhere on the piano. we could keep the same presentation primitives and apply them dynamically as we need instead of rebuilding from scratch."
4. "also we can make scenes and animations to transition between things, we could fly past the piano or perhaps inside into a room. omg the piano could be a whole environment, or there could be a magic spell that summons into existance structures that were previously hidden. we could use it to tease upcoming things."

## The principle

Precise and robust inside, elegant and wise on the surface. The passport stays exhaustive backstage, and the stage translates each of its fields into something felt.

## The claim passport (backstage)

Every fact is a record, not a sentence.

- **Type**, each with its own burden of proof:
  - event;
  - attribution (true by construction once traced);
  - usage (played on, appeared in);
  - technical (key, mode, BPM, gear; often self-verifiable by the page's own ears and chord reader);
  - superlative (the riskiest);
  - assessment (framed as opinion);
  - legend (labeled as legend, always).
- **Scope.** Narrow "always / never / first / only". For instruments, a claim about a model and a claim about one serial-numbered object need very different evidence. Also scope the context: album version, live, one tour.
- **Three times:**
  - event time (when it happened);
  - assertion time (when the source said it);
  - valid time (the span over which it is true).
  
  The gap between event time and assertion time is **contemporaneity**: a 1971 session log beats a 2004 memory of 1971. Heimdall reported a bitemporal engine in core/codex/lifecycle.py (valid_from, valid_to, recorded_at) as a candidate store; not yet verified by Vandor.
- **Authority is domain-specific.** The tech outranks the artist on the rig. The artist outranks everyone on intent. The chart archive outranks memory on charts. A film's own credits outrank fan lists. Also record **interest** (does the source gain from the claim?) and **independence** (sources that copy each other count once).
- **Laws vs rules.**
  - Laws never bend: nothing unsourced is shown as fact; every on-screen fact traces to a stored root; the model never supplies a fact from memory.
  - Rules are strong defaults with recorded exceptions. Exceptions are dated with a reason and an owner, and the exception list starts empty.
- **Decay class** — how long the claim stays TRUE:
  - stable (verify once);
  - long-lived and revisable (recheck yearly or before use);
  - medium-lived (recheck before every use);
  - ephemeral (always shown "as of <date>", expires automatically).
  
  Snapshot every root source at verification time, so link rot never orphans a fact.
- **News window** — how long it stays TIMELY. A birthday is always true and timely one day a year. The news window drives the content calendar (anniversaries, "50 years ago today"): ephemeral claims feed reactive videos, stable ones feed evergreen deep dives.

## The stage translation

1. **Three depths of disclosure.**
   - Glance: the fact, beautifully set.
   - Linger: a whisper-line beneath it ("— in his own words, 1987") in the house serif italic, low contrast. It borrows the language of epigraphs and museum placards, not of warnings.
   - Dig: the full passport, in the pinned comment, the description or a source page.
2. **Confidence lives in the grammar, not in badges.**
   - Documented facts are plain statements in solid type.
   - Recalled facts carry their doubt in the verb ("he remembered…").
   - Legends get italics and "As the legend goes…".
3. **Time becomes geography.**
   - Facts are points on a timeline; the date is a position, not a stamp.
   - Line style is confidence: solid means documented, dashed means recalled, dotted means legend. Show the key once.
   - Disputes fork the line ("he says '71, the session log says '72").
   - An instrument's provenance becomes a journey map: owner → stage → auction → museum, with a "you are here" marker for the present.
4. **Decay as material.** Stable facts are etched in glass, the Crystal grand's language; ephemeral facts are written in light that slowly dims.
5. **One arrow, one wonderful facet.** xkcd-spirited, in our own voice: luminous annotation, like a light-pen sketch, pointing at the actual 3D object ("this crack: 1972, per his guitar tech"). It also borrows scale-and-perspective comparisons, every number sourced.
6. **Wise silence.** One callout at a time. Facts arrive in musical rests, never over a run; moment.js knows when the playing is dense.

| Passport field | How the stage shows it |
|---|---|
| Confidence | grammar and line style |
| Time | position on the timeline |
| Decay | material: etched glass or fading light |
| Source | the whisper-line |
| Disputes | a fork in the timeline |

## Screens: sources × treatments × placements

Content, presentation and placement are separate primitives, composed dynamically and never rebuilt per use. N sources × M treatments × K placements give N·M·K looks from N+M+K parts, and every new treatment instantly works with every source and placement.

- **Sources (into a buffer):**
  - a video;
  - the album art;
  - the live camera on Daniel's hands;
  - the shader box's code;
  - the timeline rendered to a texture;
  - the piano's own render (feedback).
- **Treatments (presentation shaders):**
  - hologram on steam: scanlines, flicker, chromatic split, alpha displaced by drifting noise so the image lives in mist, fresnel edge glow;
  - LED wall: a grid of glowing dots, picture from afar, dots up close;
  - CRT: curvature, scanlines, RGB phosphor mask, bloom, rolling interference;
  - neon edges: edge-detected and redrawn as glowing tubes;
  - archival film: grain, gate weave, dust, warm fade;
  - crystal refraction: seen through the glass grand;
  - halftone print;
  - particle dissolve;
  - ASCII terminal.
- **Placements:**
  - a floating screen;
  - projection-mapped onto the piano lid, like a projector beam;
  - the backdrop;
  - the shader-box panel;
  - a badge.
- **Transitions** are shaders too: one treatment dissolves into another.
- **The passport picks the treatment.**
  - Archival footage gets film.
  - A legend gets the hologram, which literally looks less solid.
  - A documented live fact gets crisp LED.
  
  Provenance is expressed without a single label.
- **The badge as nameplate.** Real pianos already carry text on the fallboard nameplate. Ours can carry the whisper-line as an object ("in his own words · 1987"), or the series and episode mark. Generic marks of our own only, never someone else's logo.
- **Grounding (verified 2026-10-07).**
  - /play already samples a buffer in a shader: the feedback tunnel preset reads its previous frame.
  - The preset contract ("Uniforms v1" in arsenal/PLAY-NIGHT-SPEC.md) is strict, so a video source is a v2 addition: a texture uniform such as u_source.
  - arsenal/present (scene → slides / ui / three.js) is the existing presentation-primitive family that screens join.
- **Cost discipline.**
  - Every treatment ships with its measured frame cost (visual-quality baseline).
  - One live video buffer at a time.
  - The director picks cheaper treatments during dense passages.

## Scenes: the piano as a world

- **Transitions are camera flights:** past the piano, under the lid, through the keys into a room. The gallery and follow cameras already exist in /piano.
- **Inside the grand is a world.** At hammer scale, the strings-of-light interior (the grand and crystal grand string upgrade) becomes a forest of light strings to fly through.
- **Rooms.** Each artist dossier can BE a room entered through the piano. The theme-reveal animation becomes a doorway: the lid opens, the camera dives, and you emerge in the artist's world.
- **Summoning spells.** Structures hidden in the scene materialize: assembling from particles, drawn on as wireframe and then filled, grown like crystal.
- **Musical spells.** A chord progression, a riff or a key change casts the spell (the chord reader already listens). Play the progression to open the door: Zelda's ocarina, on a KeyLab. This is the music specialists' easter egg and a performance mechanic in one.
- **The roadmap as hidden architecture.** Upcoming features live in the world, hidden: a locked door, a shape under a sheet, a structure that half-materializes and fades ("next time"). Each episode reveals one, and the build-as-narrative becomes spatial, like a map with fogged regions. Viewers hunt for the hidden things, and the theories write the comments.
- **Discipline.**
  - Flights land in rests or between songs, never mid-phrase.
  - Eased, phone-legible camera moves (vertical video, small screens, no motion sickness).
  - No phase jumps; REC-safe; within the frame budget.

## Where these conversations live (to access later)

- **Transcripts of this night:** three Claude Code session files under C:\Users\L5\.claude\projects\E--\ — 498eac5b-5c09-4494-bb52-1498fd6cc29a.jsonl, e684a2d4-7734-4428-901c-3cbb8b887799.jsonl, 2242a56c-f199-40d0-b388-b514151e329c.jsonl.
- **Archived privately** to E:\Akashic Aurora\transcripts\rolling and the F:\ mirror by the daily TranscriptArchive task. It was also run by hand on 2026-10-07 at Daniel's request. The Eye ingests the archive daily, so `eye find` reaches these conversations.
- **Tonight's design atoms:**
  - art_20261007_second-press-gentle-hints_db25d1 (the one-world UI);
  - art_20261007_now-playing-multilayer-live-hook_1328e1 (the stage + 16 slices);
  - art_20261007_fact-sourcing-provenance-ladder_84c3e2 (draft sourcing rules);
  - this atom (passport + presentation + screens + scenes).
