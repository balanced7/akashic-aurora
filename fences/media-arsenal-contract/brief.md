# M1-BRIEF — media-arsenal-contract

## CHARTER

Daniel, 2026-09-12: "I have a new project I want to tie in together to our vfx system!"

Daniel, 2026-09-13, verbatim: "the project that I thought of is a suite of software and
integrations. I love winamp and think milkdrop is really cool, I was wondering if we could make a
media player based on mpv, that also has ffmpeg, yt download and other things so we can bot play
back media, drag and drop gifs into the video, cut slice and re-order, make our own shader based
effects, be able to have audio responsive visuals, be able to put midi to drive vizualization
effects. What do you think?"

His ruling, same message, verbatim: "I want to drop all rules that say any certain thing is
forbidden for this, 3js or any 3d renderer we could use should be used if its the best, most
stable and most reliable option. Webgl is just one type of render"

Then, verbatim: "What is the path for all of this that gives us the most freedom. I am not against
building from the ground up if that is what it takes. I want to build up a whole arsenal of backend
infrastructure and media plugins and modules that we can connect and deploy at will. Need video
decode that is hardware accellerated and has known unified API access use this, need presentation
and rendering? use these, and for all of them to have (wherever it makes sense) a unified time,
type and syntax / piping commands and pipelines, what do you think?"

And the go, verbatim: "Lets build it I am curious about the others thoughts on this!"

The stakes are his. Freedom to connect and deploy media capabilities at will. One way to speak
about time, types and pipelines across all of them. And a suite he loves using.

**Done looks like:** a contract Daniel can read and say yes to, precise enough that the first
working pipeline can be built against it. Ledger: T399.

## INPUTS (measured 2026-09-13)

- **His machine:** Windows 11 25H2 (build 26200.9168). The AMD GPU has a documented history of
  display-driver crashes (TDR) under GPU load. The Windows MIDI Service (the new MIDI 2.0 stack) is
  installed and running.
- **His tools, already installed:** FL Studio (he makes music), Ultimate Vocal Remover and
  StemRoller (stem separation), ComfyUI (AI image and video generation), OBS (recordings in
  `E:\Video Output E`).
- **The house:** `E:\AI-Setup`, Python-first, public on GitHub under Apache-2.0. The Bifrost bus is
  how seats and Discord drive things.
- **The VFX system he wants this tied to:** a WebGL2 shader bench inside the Bifrost console. It
  has typed-port shader graphs, shader chunks with JSON headers, a Shadertoy ingest, a render feed,
  and a CLI that renders through the open browser tab. Dormant since 2026-09-03.
  - Code map: `research/in-flight/vfx-system-code-map-2026-09-12.md`.
  - Its 2026-08-02 design plan (render ledger, take strip, split compare, agent takes):
    `research/in-flight/vfx-studio-synthesis-and-plan-2026-08-02.md`.
- **The old shader rules:** raw WebGL2 only, no Three.js, no build step, a single GPU context.
  They were written for the console on this AMD machine. Per Daniel's ruling they do NOT bind this
  project. Stability here gets measured, not assumed.

## RULES OF ENGAGEMENT

- **Blind.** Design from your own thinking and your own reading of current docs. Please don't
  open other files in `fences/media-arsenal-contract/`, and don't look for other seats' answers on
  this, until yours is filed. Everyone reads everyone once all designs are in, and then there is a
  round to respond to each other.
- **Formal halves:** half_a is Heimdall (deepseek), half_b is Navi (kimi). Extra voice, filed the
  same way: Sunshine (sol). Neo and Rill join if Daniel invites them.
- **Reconciliation.** Vandor (claude) reconciles and Daniel gates. Vandor holds no half. His own
  prior design was written and hashed before this brief went out (sha256
  `a5897d1e3636f4bbc9d00547b1b804a3ac1a2d0cd7ab8e1a1475c4d144f34faa`, revealed at reconciliation),
  so it cannot drift toward yours. Wherever a design differs from it, the difference is carried
  verbatim.
- **Tags.** The first line of your design carries a confidence tag
  `[CERTAIN|DESIGN|INFERRED|UNCERTAIN]`. Tag individual claims too where that helps.
- **Sources.** When you name a library, API or capability, check it against current docs and cite
  the version or a link.

## THE QUESTION

How would you design it? What contract lets media modules connect and deploy at will — decode,
rendering and presentation, audio, analysis, MIDI and control, editing, output — with one time
model, one type system and one pipeline syntax wherever that makes sense? Which existing engines
would you plug in, what would you build from scratch, and what should the first working pipeline
be?

Follow what you find interesting; there is no required shape. For orientation, designs like this
usually end up settling:
- how time is represented and how clocks relate (media, audio device, display, musical time, the
  editing timeline)
- what flows between modules, and how formats and GPU memory are described
- what the pipeline language looks like, for Daniel and for agents
- how modules describe themselves and get found
- how modules are isolated and deployed
- how control (MIDI, automation, the bus) reaches them
- licences
- which language(s) you would build in

## HOW TO REPLY

- **If your tools can write files:** write your design to a file, then run
  `py agent_cli.py fence write media-arsenal-contract --slot <half_a|half_b> --file <path> --by <your id>`
  and `py agent_cli.py fence seal media-arsenal-contract --slot <half_a|half_b> --by <your id>`.
  Reply to claude with a one-line pointer.
- **Otherwise:** reply to claude on the bus with your full design in the body. Vandor files it
  verbatim under your name.
- **Extra voices** reply on the bus. They are filed verbatim as `voice_<id>.md` in the fence
  directory.

## SEAT NOTE (independence)

Brief authored by claude (Vandor). Every design sees this brief only. The reconciler's prior is
committed by hash above and declared in full at reconciliation.
