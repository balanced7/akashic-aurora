# Presentation primitives — `present.scene.v1` (a deck is one projection of a scene)

Status: current
Type: contract (design) · Arc: watcher-reliability deck / media arsenal · Seats: claude (Vandor) · Date: 2026-09-28

**Why.** Daniel, 2026-09-28, verbatim, on the Mail-and-Wake deck: "I want complex things to be macroable,
adaptive, expressive and easy to use" and "make these primitives be a part of a family. design them such that we
can keep layouts while swapping the presentation format (pdf, video, ui element, 3d render, 3d visualization etc).
I want our toolkit to be deep and versatile." The v1 deck was 16 hand-written HTML sections; the substrate pass
measured what that costs (scratchpad gen_deck.py: h2 at five sizes, kickers at eight widths, 17 cards and 11
panels repeating the same paint). Everything in that list is template or token knowledge a slide should never
carry. So a deck is a SCENE: atoms with structured payloads, placed into named regions of a template, measured in
logical canvas units, coloured and sized by role. The slides page is one projection; a PDF, a video, a panel, a
three.js space and a 3D visualisation are others, and each names what it preserves and what it drops per atom kind
before it runs. Code: `arsenal/present/` (scene.py = the primitive, stdlib only, no renderer knowledge; `targets/` =
the four built renderers; `__main__.py` = the interim door). Manifests: `arsenal/modules/present.*.json`. Pins:
`tests/test_arsenal_present.py` (the primitive), `tests/test_present_family.py` (the renderers).

## 1. What this extends (a fourth use, not a fourth idiom)

| precedent | what is reused | receipt |
|---|---|---|
| `core/coord/orient.py` | one scene model, many renderers, "without deriving a second version of state"; a `SCHEMA` string; a CLI projection is one function over the scene | orient.py:6-7, :24 (`orient.scene.v1`), :328 `render_orientation()` |
| arsenal contract | typed ports (`PORT_TYPES` gained `scene.deck`, `scene.slide`), `arsenal.module/v0` manifests with inputs/outputs, caps, isolation, latency, degradation, receipts; "a mismatch refuses at connect time"; "every run is a take"; "a module without a receipt is presumed broken" | mediatypes.py:18-19; registry.py:21 `validate_manifest`, :40-41; reconciliation.md:169, :176, :199, :211 |
| `arsenal/web/lib/flow` | renderer-independent primitives: "No Three.js imports, DOM, global timers"; a renderer may animate what the primitive computes | flow/README.md:3, :6 |

Nothing in arsenal changed except two lines in `PORT_TYPES`. The validator, the plan, the take ledger and the
registry are the arsenal's own; the family only adds `status` and an `atoms` table to the manifest, and the scene
schema is validated by `arsenal/present/scene.py` the way `arsenal/graph.py` validates a graph.

## 2. The scene

```
deck  {schema: "present.scene.v1", title, tokens?, templates?, order?: [slide_id], sections?: {sid: {description, start}},
       slides: [Slide], provenance?}                      # order/sections have deck.json v4's shape
Slide {id [a-z0-9][a-z0-9_-]*, template, background?: light|dark|accent, transition?: fade|push|magic,
       duration_s?, title?, atoms: [Atom], provenance?}   # provenance = purpose/evidence/builder notes: carried, never rendered
Atom  {kind, region, id?, ...payload}                     # a payload is structured; a JSON string is refused (E03)
Runs  [{text, mark?: plain|strong|em|accent|muted|code}]  # a bare string is one plain run
```
`duration_s` defaults to `max(8, words(note) / 2.5)`; the video and sequence targets read it, the page ignores it.
`templates` may override a family template's region GEOMETRY only; `accepts` belongs to the family. Constants:
`scene.py:37 ATOM_KINDS`, `:43 TOKEN_ROLES`, `:71 TEMPLATES`, `:31-34 CANVAS / DIAGRAM_HOST / MAX_PINNED`.

## 3. Atom kinds (15) and their fields

| kind | payload | notes |
|---|---|---|
| headline | text, role?: display/h1/h2/h3 | role defaults from the region |
| label | text | the eyebrow: mono, capitals, letter-spaced; W02 over 40 chars |
| statement | runs, role?: body/lede/kicker | |
| quote | text, attribution, ref? | ref = file:line or a measured number |
| number | value, caption, scale?: hero/inline, tone? | value is a string ("53+") |
| list | items: [Runs], ordered | one level only (format.md forbids nesting) |
| table | columns [{title, share}] (sum 100), rows [[Runs]], role?: body/caption | E08 on shape; W08 over 4 columns |
| code | lines [str], marks? [{line, tone}] | lines are exempt from the unit scan: quoted source is content |
| bars | series [{label, value, caption?, tone?}], unit, max? | one scale per slide; max must hold every bar |
| diagram | host {1664x700}, lanes [{id,y,h,title?,tone?}], nodes [{id,x,y,w,h,text,tone?,lane?}], edges [{from,to,route?,head?,dashed?,tone?}], buses [{from[],to[],head?,stubs?[{to,head?,dashed?,tone?}]}], paths [{id?,points[[x,y]],head?,dashed?,tone?}], labels [{id?,x,y,w,text,for?}], aria_label? | geometry only; edges/buses by node id, never coordinates; `for` keeps a label attached on reflow; `stubs` (rill) and `aria_label` (irq) are I7 extensions |
| timeline | orientation: row/column, beats [{at, text: Runs, tone?}] | ghost beats = not yet run |
| comparison | left/right {title, eyebrow?, tone?, body: [nested]}, verdict?: left/right/none | one atom in region `left` spans both columns |
| group | arrangement: row/column/grid, columns?, framed?, items: [nested] | nested = number/statement/list/quote/code; group in group refused (E09) |
| receipt | text | the footer band; W02 over 110 chars |
| note | script, cues? [{atom_id, text}] | one per slide, last (E05); narration / footnote / tooltip per target |

Tones: `accent`, `secondary`, `muted`, `ghost`. **Ghost has one meaning deck-wide: does not exist today**
(dashed accent on tint on the page, wireframe in 3D). Muted never means absent (I9).

## 4. Templates as regions (logical units on a 1920x1080 canvas, 128 margin; `scene.py:71`)

| template | bg | regions (left, top, width, height → accepts) |
|---|---|---|
| cover | dark | stack 128,128,1664,824 → label, headline, statement · footer · note |
| section | dark | stack 128,128,1664,824 → label, headline, statement · note |
| statement | dark (accent once per deck) | stack 128,128,1664,792 → label, headline, quote, statement · footer · note |
| content | light | heading 128,128,1664,148 → headline · lede 128,308,1000,90 → statement · body 128,308,1664,612 → group, table, list, timeline, quote, number, code, bars, statement, comparison · kicker 128,781,1000,139 → statement, quote · footer · note |
| diagram | light | heading 128,128,1664,70 → headline (one line, W01 over 38 chars) · host 128,214,1664,700 → diagram · footer · note |
| comparison | light | heading as content · left 128,308,816,473 · right 976,308,816,473 → comparison · kicker 128,813,1000,107 · footer · note |
| closing | dark | stack 128,128,1664,792 → label, headline, list, quote, statement · footer · note |

footer = 128,982,1664,34 → receipt (layout.md:65: one 24px row at bottom 64; flow stops at y 920, a 792 budget).
note = 0,0,0,0 (takes no space on any target). A diagram host holds at most 24 pinned children (diagrams.md:13); W04
estimates the count (lanes twice, nodes, labels, edges, a bus as drop + bar + stubs, all paths as one svg).

## 5. Tokens by role (`TOKEN_ROLES`, `scene.py:43`)

palette: dark, light, accent, accent_deep, secondary, muted, muted_on_dark, card, card_on_dark, line, line_on_dark,
tint — every value `#RRGGBB`. type: display, h1, h2, h3, body, lede, kicker, quote, number, number_inline, caption,
eyebrow, code, receipt, node, label — every size ≥ 24 (format.md floor). faces: sans, mono. A slide names a ROLE,
never a hex or a size; the deck's `tokens` block is the only place values live, and missing keys fall back to the
family. The slides-html projection idioms (the CSS per role, the card, node, lane, bus and bars paint) are renderer
knowledge and live with that renderer (scratchpad deck/v2/projection.slides-html.json tonight), not in the scene.

## 6. Render targets (`arsenal/modules/present.*.json`, each `arsenal.module/v0`, registry-valid tonight)

| target | engine | in → out | status | receipts |
|---|---|---|---|---|
| present.slides-html | arsenal | scene.deck → asset.reference (project dir: deck.json v4 + slides/*.html) | exists | 2 (pin: tests/test_present_family.py; audit 2026-09-29: 22 slides against format.md, 0 problems) |
| present.pdf | browser | scene.deck → asset.reference (print.html, paged; the PDF is the browser's print of it) | exists | 2 (pin: the paged HTML; audit: the footnote floor — no PDF printed yet) |
| present.ui-element | browser | scene.slide → asset.reference (one embeddable panel: the 1920x1080 layout in a scale wrapper, width 200–1920, the deck's font link inside) | exists | 2 (pin: 400 and 1200; audit: fonts, inherited degrades) |
| present.three-js | browser | scene.deck → asset.reference (one page, one textured plane per slide, cdnjs r128) | exists | 2 (pin: page; audit: HEAD 200, indentation drawn — a headless-Chrome frame only, see §10) |
| present.sequence | arsenal | scene.deck → timeline.sequence + media.subtitle_cue | designed | none |
| present.video | ffmpeg | timeline.sequence + media.video_frame + cues → stream.video | designed | none |
| present.3d-viz | browser | scene.deck → asset.reference (lanes as planes in z, nodes as blocks) | designed | none |

Status vocabulary: `designed` (a manifest and nothing else), `building` (a builder is assigned this stage; no
receipt yet), `exists` (a receipt in `receipts[]`). By reconciliation.md:199 anything without a receipt is presumed
broken, so `building` is `designed` to every selection rule; the word only records intent. The four `exists` rows are
`arsenal/present/targets/{slides_html,ui_element,print_html,three_js}.py` (shared plumbing in `_core.py`, the
pixel-layout estimate in `_paint.py`), reached through `py -m arsenal.present render`. The honest gap: no module
produces `media.video_frame` from a `scene.slide`; present.video names it as an input instead of owning it, and
present.three-js paints from the scene with the family's own line-fit estimate rather than rasterising the page.
three.js is permitted by the media-suite ruling (best / most stable / most reliable wins).

**Preserves / drops per atom kind** (F = full, D:how = degrades, X = dropped; the manifests carry the long form):

| kind | slides-html | pdf | ui-element | three-js | sequence | video | 3d-viz |
|---|---|---|---|---|---|---|---|
| headline | F | F | F scaled (D: type scales with the panel) | F pixels, X select | X | F raster | D:billboard |
| label | F | F | F scaled | F pixels | X | F | D:billboard |
| statement | F (code mark→strong) | F (D: as page) | F scaled (D: as page) | F pixels, X select | X | F | D:billboard |
| quote | F (D: body role, italic, outside a statement stack) | F (D: as page) | F scaled (D: as page) | F pixels, X select | X | F | D:billboard |
| number | F (D: ghost draws as accent) | F (D: as page) | F scaled (D: as page) | F pixels, X select | X | F | D:billboard |
| list | F | F | F scaled | F pixels, X select | X | F, X per-item build | D:billboards |
| table | F ≤4 cols (D: cells plain text) | F (D: as page) | F scaled, every column (D: as page) | F pixels (D: cells plain text), X select | X | F, X per-row build | D:flat card |
| code | F (spaces collapse; ghost line muted italic) | F (D: as page) | F scaled (D: as page) | F pixels, indentation kept, X select | X | F | X |
| bars | F | F vector | F scaled | F pixels, X select | X | F, X grow-in | F columns |
| diagram | F (nodes, x-connectors, one svg for paths; aria_label only when there are paths; `for` not rendered) | F vector, lines in the page's own svg, alt = aria_label (an svg only when lines exist) | F scaled, lines in the svg (D: as page) | F pixels: boxes, lines with heads; X aria_label, `for` | X | F, X per-edge build | F planes, blocks, tubes, billboards; ghost wireframe |
| timeline | F | F | F scaled | F pixels, X select | X | F | F track |
| comparison | F | F | F scaled | F pixels, X select | X | F | F two shelves |
| group | F | F | F scaled | F pixels (D: flow is the 0.6×size estimate), X select | X | F | F shelf / wall |
| receipt | F footer band | F | F scaled | F pixels, X select | X | F on-frame | X |
| note | F aside, X cues | D:footnote, slide scaled 0.5–0.85 (refuses past the floor); X cues | D:title attribute, a title per cue | D:HUD caption; X cues | F subtitle cue | F narration track | D:HUD caption |

The ui-element column changed when it was built: the panel is the slide in a CSS scale wrapper, so nothing reflows
and nothing is dropped; the cost is that type scales with the panel (24 at 1920 is 5 CSS px at 400). "D: as page"
in the pdf and ui-element columns means the degrade the slides-html column names reaches that target unchanged,
because all three share one section builder (`slides_html.section_html`) — the verify pass of 2026-09-29 found
those inherited degrades undeclared in both manifests and declared them. "X select" on three-js: every text kind
is pixels of a texture, so no target text is selectable there.

Deck-level: transition — page F (magic only where ids match; the renderer emits no element ids, so magic plays as
fade), pdf X, ui X, three-js D:camera move, sequence F,
video F (magic→fade), 3d X. duration_s — page X, pdf X, ui X, three-js only with autoplay, sequence F (default
from the note), video F, 3d X. A slide's `title` — page X, pdf X, ui X (no HUD on any of the three), three-js F (the
HUD names the slide); the three designed manifests do not say yet. `coverage(scene, manifest)` (`scene.py:260`)
refuses a target whose `atoms` row for
a kind the deck uses names none of preserves / degrades / drops: unknown is not a yes (mediatypes.py:37).

## 7. Invariants

- I1 geometry only in logical units: the canvas is 1920x1080, a diagram host 1664x700, nothing else carries coordinates.
- I2 a diagram is geometry (lanes, nodes, edges, buses, paths, labels), never a picture.
- I3 text carries a role, never a size. I4 the note is a first-class atom: one per slide, last.
- I5 a slide names its template and its atoms and nothing else: no hex, no px, no HTML, no renderer key.
- I6 every target names, per atom kind, what it preserves, how it degrades, or what it drops; naming none is refused at plan time; every render writes a take.
- I7 a slide needing an element the family lacks is a FAMILY defect: extend the family (bars, lanes, buses, eyebrow, cues, stubs and aria_label were added this way), never the slide.
- I8 edges and buses reference node ids only; coordinates belong to the renderer; labels carry `for` so a reflow keeps them attached.
- I9 one absent token: ghost = does not exist today; muted never means absent; reroute, owe, settle, present and every target without a receipt are ghost wherever drawn.
- I10 status is exists|building|designed; a module without a receipt is presumed broken (reconciliation.md:199).
- I11 the family extends orient.scene.v1, arsenal.module/v0 and arsenal/web/lib/flow: a fourth use, not a fourth idiom.
- I12 a diagram headline ≤ 38 chars; node text ≤ 3 lines with no file:line inside; receipts live in the footer band.

## 8. Refusals and warnings (`validate()` `scene.py:123`, `lint()` `:192`; messages say what to change)

Refusals, exit 1 through the door: E01 unknown template / atom kind / role / tone / mark / background, a bad token
value; E02 the template has no such region, or the region does not accept the kind; E03 a target unit in any string
(`px|pt|em|rem|vw|vh|vmin|vmax`, `scene.py:101`), a renderer key anywhere (`size, font, color, style, html, css, class,
padding, margin, hex, background`, `:103`), a payload given as a JSON string, a coordinate outside the host, an edge
carrying coordinates; E04 a diagram with `src/image/svg/base64/url` or nothing drawn; E05 a note missing, doubled,
misplaced or not last; E06 duplicate ids (slides; atoms, nodes, lanes, labels, paths per slide), `order` naming an
unknown slide, a slide absent from `order`, a section starting on an unknown slide; E07 an edge, bus, stub, `lane`
or `for` naming an unknown id, a malformed path; E08 table shares not summing to 100, ragged rows; E09 nesting a
kind a group or comparison cannot hold. Shape: `slide <id>: E03 target unit '24px' inside .runs[0].text; geometry
is logical units and text carries a role, never a size`. Warnings, exit 0: W01 diagram headline over 38; W02 label
over 40 / receipt over 110; W03 node text over 3 forced lines; W04 over 24 pinned children; W05 `duration_s` shorter
than the note; W06 a cue naming nothing on its slide; W07 file:line inside a node; W08 over 4 columns; W09 a footer
template with no receipt. Percent is not scanned: the only share the family has is a number field.

## 9. The verb surface, and the alias that composes it

`present` is NOT an agent_cli verb today (measured 2026-09-28: not among the 107 parser verbs; a macro naming it is
refused at core/toolbelt/registry.py:83-84, "registry cannot mint capabilities"). Proposed, in the door's own
shape: `present check <scene.json> [--json]` (E → exit 1, W → exit 0), `present targets [--scene X]` (id, engine,
status, receipts, and I6 coverage against a scene), `present render <scene.json> --to slides|pdf|ui|three|sequence|
video|viz --out <dir> [--allow-drops] [--dry]` (`--dry` prints, per slide and target, what is preserved, degraded and
dropped, and executes nothing; a run writes `<out>/takes/<ts>-<target>.json`: scene sha256, module id and version,
per-slide preserved/degraded/dropped, warnings). Interim door (`arsenal/present/__main__.py`), in that shape:
`py -m arsenal.present check <scene>`, `targets [--scene <scene>]` (status, receipts, renderer built or not, I6
coverage) and `render <scene> --to slides|ui|pdf|3d [--out DIR] [--width N] [--slide ID] [--no-footnotes]
[--autoplay] [--verify-cdn] [--allow-drops] [--dry]`; a run writes `<out>/takes/<ts>-<target>.json`, `--dry` prints
the per-slide table, and a target that only drops a kind the deck uses is refused without `--allow-drops`. It is
not an agent_cli door because arsenal's own entry points (roll, performance, score_cli) are not either: they are
reached as `py -m arsenal ...`, and no `check_door_parity` guard exists at the repo root. The day `present`
is a verb, the alias mints with no registry change, on the ladder the deck itself describes (verb → alias with an
evidence grade → kit → flow; agent_cli.py:9660 `cmd_alias`, :9688 `cmd_run`, :10239 `cmd_kit`, :5805 `cmd_flow`;
`--evidence` defaults to GUESS, :9333-9334 "untested sugar confesses"):

```
py agent_cli.py alias claude mint deck-ship --step 'present check $1' \
   --step 'present render $1 --to slides --out $2' --step 'present render $1 --to pdf --out $2' \
   --family CONSTRUCTORS --evidence GUESS --why 'one word takes a scene to the page and the print'
py agent_cli.py run claude deck-ship deck/scene.json deck/out --dry
```

## 10. Built tonight, measured tonight, not built tonight

Built: `PORT_TYPES` += scene.deck, scene.slide; `arsenal/present/{__init__,scene,__main__}.py`; seven manifests;
`tests/test_arsenal_present.py`; the Mail-and-Wake scene (22 slides, scratchpad deck/v2/scene.json) validates with
zero refusals and zero warnings, and every present.* manifest covers every kind it uses. Measured: `load_registry()`
loads 15 modules (8 prior + 7 present.*).

Built the same night, second stage: the four renderers under `arsenal/present/targets/` (slides-html: deck.json v4 +
22 section files in the subset; ui-element: one scale-wrapped panel per slide; pdf: one paged print.html, the PDF
being the browser's print of it; three-js: one 91 KB page, cdnjs r128, every slide a CanvasTexture plane), the
`render` door with the take writer (`<out>/takes/<ts>-<target>.json`), and `tests/test_present_family.py` (13 pins,
the scene copied to `tests/fixtures/present/` so the pins hold on any checkout). Measured: all four targets render
the 22-slide scene in under 15 ms each; the four manifests say `exists` with one receipt each. Verified by eye: the
print page and a 1200-wide panel in the app's pane; the three.js page in headless Chrome (software GL) shows the
cover plane, HUD and caption -- that run also caught a hoisted `var` that had shadowed the render loop. Not built:
the `present` verb in agent_cli; the rasteriser that video needs; glyph-metric line fitting (every line count is
craft.md's 0.6 × size estimate, and three-js places blocks by it). Not verified: no output has been built through
the artifact type's own validator; no PDF has been printed and measured; the three.js page has not been opened in a
GPU-backed Chrome (the Chrome extension was not connected); the arsenal suite was run only for the four present and
kernel files.

Verified 2026-09-29 (an adversarial pass over the outputs, not the code's own pins). Measured: every one of the 22
written slides audited mechanically against format.md — tags, every style property against the subset table per
element class, the 24 floor on every text element (explicit or inherited), one `<aside>` last, a background on every
section, the 200-element cap (6–40 measured), the 24-pinned cap per host (14–24; `ladder` and `scene` sit exactly at
24), no `<text>` in an svg, x-connector endpoints clear of the host's 6-unit head margin — one violation found and
fixed: `line-height` on `<table>`, which the subset lists for text elements only. HEAD on the three.js script: 200
(cdnjs r128; jsdelivr 0.128.0 also 200). `scene.py` and `__init__.py` import only the stdlib and name no renderer
in code; the residue is wording — `_pinned_estimate`'s docstring and W04's message say "pinned children" and "svg"
(the count is the family's diagram limit, the vocabulary is the page's). The house commit gate's check functions
(scripts/githooks/pre_commit.py: lock backstop, seat attribution, private-plane scan, the guardrail ratchet, the
fast comprehensibility check) pass over the new files. Fixed the same pass: the print scale floor of 0.6 clipped
this deck's longest note by the renderer's own arithmetic (0.594 needed) — floor 0.5, and a note the floor cannot
hold refuses the render; the three.js text routine dropped a code line's indentation (four lines on `refusal`) —
a fresh line keeps its leading spaces, pinned in node; the ui fragment carried no font link — it does now. Declared
the same pass: the shared section builder's degrades in the pdf and ui-element manifests, pdf's dropped cues,
three-js's flat table cells, dropped aria_label and `for`, unselectable text, and the slide `title` at deck level.
Still not verified: the artifact type's own build over these files (the audit is a reading of format.md, and it
accepts `justify-content:flex-end` because layout.md uses it although format.md's grammar lists `end`); a printed
PDF; a GPU-backed frame of the three.js page; the footnote fit itself, which is the 0.6×size estimate, not glyph
metrics.
