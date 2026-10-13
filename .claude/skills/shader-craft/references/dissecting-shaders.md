# Dissecting a shader: reverse engineering in the shader school

Taking someone's shader apart to learn how it works is reverse engineering, and the house method for
that lives in `.claude/skills/reverse-engineering/SKILL.md` (scope, the legal map, host safety, the
eleven-step method), with the frames-and-looks playbook in
`.claude/skills/reverse-engineering/references/graphics-vfx.md`. This page is the shader-school
specialisation: which tool reads which kind of shader artifact first, the one rule that keeps each
reading honest, and how a finding is written down. The discipline (observations, inferences and
unknowns kept apart, each tied to an evidence id, in a ledger with confidence and search boundary,
cached on content, revisited against a checklist) is credited to **morluto/rea**
(https://github.com/morluto/rea). We adopt its discipline, not its server machinery.

## The finding ledger: one verb per shader

```
py -m arsenal shader explain <id>                  # summary first: route, counts, checklist, the unknowns by name
py -m arsenal shader explain <id> --detail full    # every claim with its evidence ids, boundary and paths
py -m arsenal shader explain <id> --json           # the ledger itself
```

`arsenal/shaders/explain.py` joins what the house already knows about one corpus shader (its
configuration, the dissector's reading of every pass, the render receipts, our private study note)
into a ledger at `state/arsenal/shaders/ledger/<id>.json` (gitignored: it names other people's work).
It renders nothing; `render` and `filmstrip` make receipts and this verb reads them. A name that
matches more than one shader is refused with the candidates listed: it never picks for you.

Every claim carries exactly one label:

| Label | Means | Evidence id |
|---|---|---|
| observed-in-code | a raw fact only: a pass or input the shader's own configuration (shader.json) declares, a uniform or declared channel read on a line of live code (`iTime`, `iFrame`, `iMouse`, `iChannel<n>`; not a comment, a dropped `#if` branch, a function nothing reaches or a `#define` that only renames it; a macro or function Common defines is live code of every pass that reaches it, and a `#define` alias counts only in its own pass and, from Common, in every pass), a function present at a line (`mainSound`), the functions no entry point reaches, but only where the reader followed every pass that could reach them | `<id>@<sha8 of the pass>:<pass>:<first>-<last line>` (a `#define` continued over several lines is cited whole), or `config:<id>@<sha8 of shader.json>:<pass>:pass` and `config:<id>@<sha8 of shader.json>:<pass>:iChannel<n>` |
| observed-in-render | a receipt says the page compiled, drew, walked from a reset or jumped | `render:<sha8 of the receipt>`, with the receipt's path |
| measured | a number a receipt measured: mean luma, milliseconds per frame on SwiftShader | `render:<sha8>` |
| inferred | a reading, not a sighting: every technique the dissector recognises from the shape of the math (a sphere trace, a box distance, a gamma curve; its own number travels as `score`), a function name alone (low confidence, "function name only; shape not matched", never counted as a technique), a read the dissector reports that no live line holds, or that sits in a pass the reader could not follow (kind `read_unchecked`, low confidence, never answers "made of"), the dead-function list when the reader could not follow a whole pass (an `#if` it could not evaluate, code it could not follow, no entry point found), the static cost estimate, what the media folder predicts a render will draw, every heading of the study note and its corroboration section | code ids, config ids, or `study:<id>@<sha8 of the note>#<section>` |
| unknown | what no evidence reaches, said in so many words: among them a pass in which the reader found no entry point (kind `no_entry`: a pass written as one macro Common defines, so none of its code was followed) | whatever bounds the search |

A sha8 is the first eight hex digits of SHA-256 over the file as it sits on disk, so an evidence id
goes stale the moment its source changes. The ledger is cached on everything it was made from (the
pass hashes, shader.json, meta.json (name, author, the licence reading), every media file an input
names (all six faces of a cubemap), each receipt, the study note and its corroboration section, the
dissector's version and code, the code that reads the rest (the verb, shelf.py, corpus.py) and the
confidence floor): run it again with nothing changed and it returns the stored ledger and says
"cached"; change any input and it is analysed afresh. It ends with a checklist (made of, wiring,
look, motion, cost, intent, and where they apply sound and interaction), each marked answered,
partial or unresolved from the claims. "Made of" is answered only by a technique recognised from the
shape of the math; reads, declarations and function names alone leave it partial.

## Route first: the routing table for shader artifacts

Name the artifact before reading it. The first cell is what you are holding; the rule is the one
that keeps the reading honest. The routes the ledger writes come from `ROUTES` in
`arsenal/shaders/explain.py`, and a pin keeps this table and that list together.

| Artifact | First tool | The rule | What it cannot tell you |
|---|---|---|---|
| single-pass shader (Image, maybe Common) | `py -m arsenal shader render <id> --t 1,4`, then `py -m arsenal shader filmstrip <id>` | render jump: no pass keeps a frame, so the still at t is drawn straight from t | how a GPU rounds it |
| buffer chain (buffers, none keeps a frame) | `render`; read the receipt's `history` flag | a buffer that keeps no frame recomputes from t, so a jump is safe only while the receipt says no history | anything the flag and dissect v1 both missed |
| buffer feedback (a buffer reads its own last frame, or buffers read each other in a cycle) | `render`; the page walks 1/fps steps | walk from a reset, never jump: the picture at t folds in every frame before it, and the same t after a seek is a different picture | how it looks after minutes, or after input |
| sound pass (`mainSound`) | `py -m arsenal shader check <id>` (compile) | compile only: the runtime builds the Sound pass and never plays it | the sound itself |
| cubemap pass (Cube A, `mainCubemap`) | `render`; the compile report names Cube A | Cube A draws six faces before Image every frame: judge it through the Image that samples it; if it reads itself, the feedback rule | each face on its own |
| texture inputs (texture, cubemap, volume, video, webcam) | `py -m arsenal shader missing`, then `render`; read the receipt's `substituted` | check the stand-ins before judging: a medium the corpus lacks is drawn by a procedural stand-in, not the author's picture | the author's picture wherever a stand-in drew |
| audio-reactive (music, mic, stream input; `audio.input`) | `render`, knowing it feeds silence | feed an audio texture or you are judging silence: the harness feeds none, so a render is the shader at rest | how it moves to music (no render verb feeds audio yet; the runtime's audio texture is 512x2, row 0 spectrum, row 1 waveform, `arsenal/web/shaderlab/toy-runtime.js`) |
| interactive (iMouse, keyboard) | `render` | the renders press no key and move no mouse: the picture is the shader untouched | its response to input |
| house module (`arsenal/web/glsl/**`) | `py -m arsenal shader card <name> --render` | a card is the module's own test pattern: compile ok, not flat, NaN-free, on SwiftShader | how it reads composed into a scene |
| group recipe (`arsenal/web/glsl/groups/*.glsl`) | its group sheet: every tier of the recipe side by side, from its card (`arsenal/web/glsl/cards/*.card`) and its CPU twin under `arsenal/shaders/twins/` | a recipe is judged on its sheet, never on one still; read a sheet already under state/arsenal/shaders/groups/ before rendering a new one | the scene it will sit in. Bounded negative, 2026-10-13: no tracked verb writes the sheet yet (searched arsenal/ and scripts/); ask the group lane rather than inventing one |
| three.js house surface (the piano, `arsenal/web/piano.js`; a present scene, `arsenal/present/targets/three_js.py`) | the open tab (`scripts/vfx_render.py` renders through the tab already open), or the GPU lane (`arsenal/GPU-LOCK.md`, Daniel's call) | never a second GPU context to look at your own work, and never the harness Browser preview of a shader page | GPU timing unless the GPU lane ran it |
| video or screenshot of a look | `py -m arsenal.media filmstrip <video> <t0> <t1>`, then `py -m arsenal boost <frame>` and `py -m arsenal floors <frame>` before any judgement | boost and floors first: stretch a dark frame until its structure shows, and check dead, blown, flat and illegible before an eye is spent; then the graphics playbook's rulers | the shader behind it, its parameters, any pass it hides. Our own recordings only on this host (see Host safety) |

For a corpus shader, `py -m arsenal shader dissect <id> --atlas` is the code reading the ledger is
built on: techniques with file:line evidence and a confidence, cost, dead code, and the atlas parts
that would rebuild it.

## Observation, inference, unknown: the rule

- **Label every sentence about a shader.** "iTime is read on line 12" is observed-in-code with that
  line; that the loop on line 30 marches a ray 64 steps is inferred, the dissector's reading of the
  math, cited by its line; "it reads as underwater" is inferred; "what it does past t = 8" is unknown
  until a render reaches it.
- **A detector's miss is bounded.** Write "not detected by dissect v1" with the shapes it searched
  and where (live functions of every pass), never "absent" or "doesn't use". A technique written in a
  shape the detector does not know, or living in dead code, is not seen.
- **A name is a lead, not a finding.** A function called `fbm` is an fbm when its loop shape says so.
  The dissector matches shapes; where it has only a name (`sdBox` whose body is no box), the ledger
  writes it as inferred at low confidence, bounded "function name only; shape not matched", never
  counts it as a technique, and never lets it answer what the shader is made of. The same goes for
  inputs: read their type from the shader's own configuration (shader.json), never from a channel
  name or a texture's file name.
- **Our study notes are inferred.** They are our earlier reading of the code, valuable and unchecked;
  the ledger cites their headings as `study:<id>@<sha8>#4.2` (the note's own hash, so the id goes
  stale when the note changes) and labels every one inferred.
- **A stand-in changes what a render observed.** A frame drawn with a stand-in texture, or with
  silence fed to an audio input, is a picture of the shader plus our substitute. Name the stand-in
  beside any judgement of the look.
- **Summary first, and never the same analysis twice.** Read the summary, drill with
  `--detail full` only where a question is still open, and re-run only after an input changed.
- **Revisit the checklist** before saying a dissection is done; "partial" is an honest answer.

## Timing: SwiftShader timing never stands for GPU timing

Every house render runs on SwiftShader (the CPU), headless, under the GPU lock. Its milliseconds rank
shaders against each other on this machine's CPU and nothing more: the first draw is mostly compile
time (the 2026-10-13 check found code lines tracked ms/frame at Spearman +0.82, ahead of every
execution estimate; see `arsenal/shaders/dissect.py`), and a GPU's occupancy, precision and caches
are not modelled at all. A GPU number needs a GPU run, and that is Daniel's call (`arsenal/GPU-LOCK.md`).

## The rebuild rule

When a study turns into something we build, keep two columns and never let them blur:

| What we observed in the original's renders (and code) | Our own design choice |
|---|---|
| labelled, with the receipt or line that shows it (t, size, fps, stand-ins named) | written as a decision with its reason, owned by us |

The original's frames are evidence; our palette, timing, structure and parameters are design choices,
even where they land close. Techniques transfer, code does not: the house library is Apache-2.0 and
written fresh, card bodies included, and `py -m arsenal shader licence-line` refuses a committable
file that shares a 12-token run with a corpus shader (`arsenal/shaders/licence_line.py`). A shader
whose own header withholds permission is study only: its note and tags, never its pictures
(`arsenal/shaders/shelf.py`). Judge a rebuild against the original's receipts at the same t, size
and fps, with the stand-ins of both named.

## Legal note (not legal advice)

Reading published shader source to understand a technique is study, and techniques, algorithms and
ideas are not protected by copyright; the code, its comments and the specific look are. Most of the
corpus is CC BY-NC-SA 3.0 (Shadertoy's default), which forbids commercial use and requires share-alike
for adaptations; some headers reserve all rights. Across jurisdictions the shape is: US DMCA §1201
bans circumventing access controls, with narrow interoperability and security-research exemptions
(§1201(f), (j), 37 C.F.R. §201.40); *Sega v. Accolade* and *Sony v. Connectix* held intermediate
copying for interoperability can be fair use; the EU Software Directive arts. 5–6 let a lawful user
study a program and decompile for interoperability, and art. 8 voids contract terms that forbid it;
EULAs and terms of service can still bind (in the US especially); trade-secret law permits reverse
engineering of a lawfully obtained product absent a contract; game mechanics are free while assets
and expression are not; and copying a distinctive look can infringe even when the rules are free
(*Tetris Holding v. Xio*, including trade dress). Anything we ship that was informed by someone
else's work goes past a lawyer first. The full map, dated: `.claude/skills/reverse-engineering/references/method-legal-cleanroom.md`.

## Host safety

This machine runs with Defender off and updates blocked by the owner's choice, so: corpus GLSL runs
only inside the house harness (a private headless Chrome forced onto SwiftShader, under the GPU lock,
never on port 8793; `arsenal/shaders/render.py`), never compiled by a native tool or fed to a GPU
debugger. A video, screenshot or capture from outside the house is untrusted media: decoding it is
attack surface, so it belongs in a disposable VM or sandbox (none is enabled today; that is Daniel's
call), and on this host `arsenal.media`, `boost` and `floors` read our own recordings and renders
only. Samples stay out of the repo: the corpus, renders, study notes and ledgers live under `state/`
(gitignored), and no untrusted code executes on the host.

## Sources and credits

- Evidence discipline: morluto/rea, https://github.com/morluto/rea (the reverse-engineer-anything skill).
- Shadertoy, by Inigo Quilez and Pol Jeremias: https://www.shadertoy.com/terms ; the default licence,
  https://creativecommons.org/licenses/by-nc-sa/3.0/
- SwiftShader (Google's CPU implementation of Vulkan, under ANGLE in Chrome): https://github.com/google/swiftshader
- Law: https://www.law.cornell.edu/uscode/text/17/1201 ; https://www.law.cornell.edu/cfr/text/37/201.40 ;
  https://en.wikipedia.org/wiki/Sega_v._Accolade ;
  https://en.wikipedia.org/wiki/Sony_Computer_Entertainment,_Inc._v._Connectix_Corp. ;
  https://eur-lex.europa.eu/eli/dir/2009/24/oj ;
  https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc.
- House research behind the routes: `research/reviewed/reverse-engineering-2026-10-13/graphics-vfx.md`.
