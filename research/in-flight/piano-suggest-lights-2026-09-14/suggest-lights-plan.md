# Chord suggestions and key lights: the build plan

| | |
|---|---|
| Status | Plan, 2026-09-14. Research and design only: no code edited under `arsenal/`, no server or browser started, nothing downloaded, installed or bought. |
| Asked for | Daniel, verbatim (Discord): "Could we add some cool features like suggesting chords to play when you are holding a chord down? I am wondering if there are any light systems out there that we could link up to have individual keys light up!" |
| Built from | `chord-suggestions.md` and `key-lights.md` (this folder); `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (8.7, 8.8, 8.11, 13.0-13.4); house ideas (`heimdall.md`, `navi.md`, `sunshine.md`, `vandor-integration.md`) |
| Checked locally in this pass | `arsenal/web/piano.js` (KEYMAP, keydown, imports, `Theory`, `sounding`, `keyView`, `window.__piano`), `piano.html` (top bar groups), `arsenal/web/piano/deck.js` (SHORTCUTS, constants), `glass.js` (`draw` signature), `transport.js` (rest detector), `cues.js` (exports), `arsenal/jam/schemas.py` (groups, kinds, source kinds), `arsenal/serve.py` (routes), `arsenal/practice.py` (reading functions, riff delegation), `arsenal/practice_theory.mjs` and `pianocue_voicing.mjs` (how node loads THEORY), `git status` |
| Naming | Suggestion build steps are **SG0-SG9**, suggestion receipts **SR1-SR12**, light steps **L0-L5**, light receipts **LR1-LR7**. These replace the S0-S6 and S1-S8 labels in `chord-suggestions.md`, which used the same letter for both. |

---

## 0. The answer in one screen

**Suggestions: yes, and we build them first.**
1. When Daniel holds a chord still, three chips appear beside the chord name, in the margin and never in the video.
2. Each chip is one next chord: its name, its number, and one plain reason word (home, your move, borrowed colour, stretch).
3. The chips come from three sources: theory in his key, his own habits from the practice log, and one sound at his growth edge.
4. Each chip is voiced close to his hands: fingers already on a chord note stay put, the rest move to the nearest note, so he knows exactly which keys to press.
5. Point at a chip and its new keys light as ghosts on the glass. Click it and Claude plays the move: his chord, then the suggestion.

**Lights: yes, individual keys can light up.**
- **Recommended: a DIY LED strip** along the back of the keys, run by a small WLED controller on Ethernet. Our server sends it frames, so the physical keys show the same things the screen shows: his pitch colours, Claude's moonlight, and the suggestion's keys.
- **Commercial light bars only follow their own apps.** They cannot show Claude or the suggestions.
- **Nothing gets bought or built until Daniel picks.** A free on-screen strip can come first, so he can judge the look before spending anything.

**Order.** The pure suggestion engine starts now, in new files only. The page work waits until the jam build lands. Lights come after Daniel picks hardware.

---

## 1. Corrections found in this pass (to the two research files)

| # | What the research said | What the repo says (2026-09-14) | Change in this plan |
|---|---|---|---|
| 1 | Toggle key "N for next" (unchecked) | **`KeyN` is taken:** it is A3 in the computer-keyboard piano (`piano.js:2400`). All 26 letters are taken: 22 by `KEYMAP`, H and F by the page (`piano.js:3025-3026`), A and K by the deck (`deck.js:55-57`). The only free character keys left are `Backquote`, `Digit1`, `Digit4` and `Digit8`. | Toggle on **`Backquote`** (the key left of 1, away from the playing rows). `Digit4` and `Digit8` sit in the gaps of the upper row's black keys, where a slip while playing is likely. |
| 2 | A `near` style inside `pianocue_voicing.mjs`, "the same voicer in node" | `pianocue_voicing.mjs` is a node program (`readFileSync`, stdin) that slices THEORY out of `piano.js` (`:64-70`). The page cannot import it. | The near voicer is a **pure browser module, `arsenal/web/piano/near.js`**, imported by the page, by the node bridge, and later by a one-line `near` style in `pianocue_voicing.mjs`. J1's file is not edited in v1. |
| 3 | `suggest.js` receives `detect` (Theory.detect) | `Theory` (`piano.js:23`) and `spellForKey` (`piano.js:1720`) are private to `piano.js`. Node reaches them by slicing between the THEORY markers (`practice_theory.mjs:4, 19-23`). | `suggest.js`, `readings.js` and `near.js` import nothing from `piano.js`. `detect`, `templates` and `spell` are injected. `suggest_bridge.mjs` uses the same slice loader as `practice_theory.mjs`. |
| 4 | Build "after J10" | The jam build is **in flight, not landed**. `arsenal/jam/`, `deck.js`, `deck.css`, `glass.js`, `deck-test.html`, `practice_riff.py`, `groove_bridge.mjs` and `lanes/jam_timing.mjs` are untracked, and `piano.js` still imports only `log.js`, `nashville.js` and `cues.js` (`:18-20`). | Phase 1 (new files only) can start now in a worktree. Every edit to an existing file waits for the jam files to be committed (13.0, 13.1). |
| 5 | "Keep as card" uses `source.kind: "suggest"` | `SOURCE_KINDS = ("seed", "claude", "saved-live", "saved-from-moment", "kept", "edit")` (`schemas.py:55`). `GROUPS` already has `try` and `KINDS` has `progression` (`:46-47`). | "Keep as card" moves to Phase 3. It needs one contract change through the conductor (13.1 rule 3). |
| 6 | `GET /api/practice/habits` | `serve.py` has no `/api/practice` route. It has `/api/performance*` and the jam dispatcher (`_is_jam_path` `:56`, `_jam_route` `:582`). | The route is new, added in SG5. |
| 7 | Settings in the deck's `[...]` menu; a dock-mode row in the deck's Now header | Both are edits to `deck.js`, which is J8's file and is edited again by V2-B and V2-G. | v1 edits no `deck.js`. The chip column gets its own small `...` menu (owned by `suggest-view.js`). In dock mode the column stays left when the margin allows, and falls back to the glass otherwise. |
| 8 | Chips hidden during REC (0.1, 4.2) versus "the column is outside the recording" (3.6) | Both are true: hidden by default, and clean even when shown. | Setting `while recording: hide (default) / show beside`. The clean-take receipt runs with it set to `show beside`. |
| 9 | Chips disappear when the reading changes | A mouse click needs a free hand. If lifting that hand changes the reading, the chips could vanish before the click lands. | New **linger rule**: after fingers lift with no new note-on, the chips stay (at 0.7 alpha) for 4 s. |

---

## 2. Suggestions v1: the buildable spec

### 2.1 Scope

| In v1 | Deferred |
|---|---|
| Held-chord detection and settle gates; reading with the practice rules (`readings.js`); habits from the log plus tonight's moves live in memory; theory table; the stretch source; the slots HOME, YOUR MOVE and COLOUR/STRETCH (taking turns); near voicing with the read-back gate; stability rules; the DOM column with a glass fallback; the `suggest` ghost state; hover to see, click to hear; a toggle; settings; accept and ignore stats in localStorage; the `practice habits` and `practice next` CLI; the receipts | **v1.1 (Phase 3):** doors (new key, slide); Keep as card; stats in `state/arsenal/jam/suggest/`; `pianocue card add --from-suggest`. **v2 (with the jam waves):** "other nexts" over a Loop; the riff talking point; KeyLab pads that play chips; show in recording; lift rims. |

### 2.2 Files

**New files.** Each belongs to the step that creates it.

| File | Step | What it is |
|---|---|---|
| `tests/fixtures/suggest/readings_cases.json` | SG0 | Synthetic voicings with the practice verbs' reading for each: core, number, suffix, bass degree. At least 60 cases, covering his colour families (maj9, m11, 13, maj13#11, 5-over-4, sus, add9, borrowed 4m, b6, b7) and the worked example `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` in Db major. |
| `tests/fixtures/suggest/held_cases.json`, `chips_expected.json`, `habits_synthetic/` | SG0 | Held chord plus key plus synthetic habits, and the chips expected. Includes the worked example (`chord-suggestions.md` section 6) and the 5sus case. |
| `arsenal/web/piano/readings.js` | SG1 | Pure JS twin of `practice.extended_readings` (`practice.py:1424`), `choose_reading` (`:1475`) and `core_number` (`:3070`) |
| `tests/test_arsenal_suggest_readings.py`, `tests/suggest_readings.test.mjs` | SG1 | Python: the fixture still matches `practice name`. Node: `readings.js` matches the fixture. |
| `arsenal/web/piano/near.js` | SG2 | Pure near voicer, movement measure and variants |
| `tests/suggest_near.test.mjs` | SG2 | Movement, span limits, and the read-back gate (with THEORY sliced from `piano.js`) |
| `arsenal/practice_habits.py` | SG3 | Habits builder; runs as `py -m arsenal.practice_habits` until SG5 registers it |
| `tests/test_arsenal_practice_habits.py` | SG3 | Synthetic sessions only |
| `arsenal/web/piano/suggest.js` | SG4 | Pure engine: rules as data, scoring, slots, stability, stats |
| `arsenal/suggest_bridge.mjs` | SG4 | Node entry: stdin JSON in, chips out. Slices THEORY and `spellForKey`; imports `nashville.js`, `readings.js`, `near.js` and `suggest.js`. |
| `tests/suggest_engine.test.mjs` | SG4 | Chips for the held cases, transposition, and the offline flicker replay |
| `arsenal/web/piano/suggest-view.js`, `suggest.css`, `suggest-test.html` | SG6 | DOM column, chip, hover line, `...` menu, glass fallback; a test page driven by fixture results |
| `arsenal/lanes/suggest_verify.mjs` | SG7 | Live receipts in isolated headless Chrome, on the step's own port (not 8793, not 8795-8798) |
| `tests/test_arsenal_suggest_routes.py` | SG5 | The habits route and the rebuild-if-stale rule |

**Existing files.** Each is edited only after its owner's build lands. See section 2.12.

### 2.3 Module interfaces

```js
// arsenal/web/piano/readings.js (pure)
export const EXTRA_TEMPLATES;   // the practice verbs' reading templates that THEORY lacks (copied, fixture-checked)
export function readHeld({ midis, bassMidi, key /* parseKey result */, templates /* Theory.TEMPLATES */ })
  -> { core: "4", number: "4maj13#11", suffix, rootPc, bassPc, bassDegree, cost, pcs } | null

// arsenal/web/piano/near.js (pure)
export function nearVoicing({ held /* sorted midis */, bassMidi,
  target: { bassPc, pcs, required /* pcs */, colour /* pcs */ }, limits: { bassReach: 7, voiceStep: 2, topLift: 2 } })
  -> { notes: [midi], keys: { arrive: [midi], stay: [midi], lift: [midi] }, movement }
export function movement(fromSorted, toSorted) -> integer   // order-preserving cheapest matching (DP, voices never cross)
export function variants(voicing, target) -> [voicing]       // 5th added, 5th dropped, one moving voice left in place

// arsenal/web/piano/suggest.js (pure, no DOM; runs in the page and in node)
export const SUGGEST_API = "arsenal.piano.suggest/v0";
export const TIMING = { settleMs: 700, quietMs: 450, busyNotes: 6, busyWindowMs: 2000, calmMs: 1200, lingerMs: 4000,
  recomputeMs: 100, replaceMargin: 0.15, replaceHoldMs: 1500, fadeOutMs: 120, fadeInMs: 250, keyFadeMs: 300 };
export const WEIGHTS = { habit: 0.40, theory: 0.35, ease: 0.15, novelty: 0.10 };   // illustrative; tuned in SG8
export const REASONS = ["home", "your move", "lift", "surprise", "pull", "borrowed colour", "slide", "new key", "stretch"];
export const RULES;             // chord-suggestions.md 2.4 table as frozen data (held core -> [{next, T, reasons}])
export function createSuggester({ habits, detect, templates, spell, nashville, near, now, settings }) -> {
  update(frame) -> { state: "hidden" | "waiting" | "shown" | "linger", reading, labelNumber, chips: [Chip], alpha },
  hover(chipId), accept(midis), noteTonight(reading, seconds), setHabits(h), setSettings(s), stats(), last() }

// frame (built by piano.js each renderFrame)
{ t, notes: [{ midi, vel, t0, held /* finger-held */ }], pedal, noteOnTimes /* ring buffer, last 2 s */,
  key: { name, confidence, locked }, minor /* theoryUi.minor */, labelName /* overlay.shown */,
  run: null | "play" | "loop" | "try", rec: "idle" | "recording", bannerHold, cueChipUp }

// Chip: as chord-suggestions.md 5.1 (id, core, number, name, reasons, source, score, T, H, E, N, voicing,
// movement, keys {arrive, stay, lift}, reads {page, match}, hover, evidence {after, went})

// arsenal/web/piano/suggest-view.js (DOM)
export function createSuggestView({ root, stage, glass, voice, framing, isRecording, store /* safeGet/safeSet */ }) -> {
  render(result), layout({ canvasRect, marginLeft, framing }), clear(), dispose() }
```

### 2.4 Algorithm 1: when to show (per frame, recompute at most every 100 ms)

```
if setting == off or frame.run or bannerHold or (rec == recording and whileRec == hide): state = hidden
held group  = notes struck since the last bass onset; pedal-held notes from before that bass are dropped
              (bass onset = a note-on that becomes the lowest sounding note)
busy        = at least 6 note-ons in the last 2 s; after busy, wait 1.2 s of calm
settled     = the reading (core + bass degree) unchanged for 700 ms, and 450 ms since the last note-on
blur        = more than 7 pitch classes held, or reading cost over 3.5  -> hidden (silence beats a guess)
linger      = all fingers up, no new note-on: keep the last chips at 0.7 alpha for 4 s
key         = keyView (sure/fair: numbers on, theory at full weight; unsure: letters only, theory x0.5; none: habits + neighbours)
```

### 2.5 Algorithm 2: reading the held chord

`readHeld` uses the practice rules (bass-aware, cheapest reading), never the page label.
- **When the label agrees:** the column header reads `after 4maj13#11`.
- **When the label disagrees:** the header adds, in small type, `the label calls it 6m11/4`. Both readings stay visible, so the screen never quietly contradicts itself.
- **After V2-F:** once V2-F adds `maj9#11`, `maj13#11` and `13sus4` to THEORY, the disagreement line disappears on its own, and `EXTRA_TEMPLATES` shrinks under the same fixture.

### 2.6 Algorithm 3: candidates and score

1. **Theory:** `RULES[core]`, minor rows for minor keys, plus chromatic slides (T 0.4). Doors are off in v1.
2. **Habits:** every next core in `habits.after[core]`, with 3-chord context `habits.after2[prev>core]` when present. Backs off to 2-chord moves, smoothed with k = 1. Tonight's in-page moves (a reading held at least 0.5 s) count with weight 2.
3. **Stretch:** theory candidates with familiarity `1 - h >= 0.7`, at most one step from something played tonight. Ranked by the measured edge: a real 5 with its 3rd resolving home; a diminished passing chord; a secondary dominant that lands; a sus that resolves.
4. **Voicing:** each candidate is voiced by `nearVoicing` from his held keys (algorithm 4). Its colour is his usual colour for that core (`habits.colour`) and its bass is his usual bass for the move (`habits.bass`).
5. **Score:** `0.40·H + 0.35·T + 0.15·exp(-movement/8) + 0.10·N - R`. The penalty R is 1.0 for the same reading as held, 0.3 for a chip shown 3 times for this reading and never played, and 0.2 for a chord outside the key while the key is unsure. A chip ignored 3 times for the same reading is demoted for 10 minutes.

### 2.7 Algorithm 4: near voicing and the read-back gate

```
bass   : octave of target.bassPc nearest the held bass, within 7 semitones (prefer a step)
uppers : for each held upper voice v:
           pc(v) in target  -> stay
           nearest target note within 2 semitones, not already taken -> arrive (v lifts)
           else -> lift
required tones still missing (3rd and 7th of a dominant, #11 of a Lydian 4, b3 of 4m):
         insert at the nearest octave inside [lowest right-hand note, top note + 2]
limits : drop or raise any voice below the low-interval limits (design-music.md 4.4)
movement = movement(held, notes)   // order-preserving DP
gate   : detect(notes) names the target (exact or enharmonic)? done
         else try variants(); first that reads as itself wins
         else keep the best voicing and set chip.reads = { page: <what detect says>, match: "other" }
              -> hover line: "your screen will call this <name>"
```

Worked example to reproduce (SR4), holding `4maj13#11` in Db major:

| Chip | Page reading | Movement |
|---|---|---|
| `Dbmaj9/F` | exact | 3 |
| `Ab9/Gb` | exact | 3 |
| `Gbm6/9` | detected as `F#m6/9`, respelled | 4 |
| `Gdim7` | exact | 6 |

The one-finger `4m` version is rejected by the gate.

### 2.8 Algorithm 5: slots and stability

- **One chip per core number.** Its best voicing and bass win.
- **HOME:** best tonic-function chord. When the held chord already is the 1, the slot shows the best 4 or 6m under the word **lift**.
- **YOUR MOVE:** best habit with at least 3 plays across at least 2 sessions that is not already in HOME. If HOME is also his top habit, HOME shows `home · your move` and this slot takes his next habit.
- **COLOUR/STRETCH:** with 3 chips they alternate for the same reading: colour the first time, stretch the next. With 4 chips both show. Stretch is never labelled "your move".
- **Stable order per reading.** A newcomer replaces a shown chip only by beating it by 0.15 for 1.5 s of holding.
- **Re-voicing** the same reading keeps the chips and updates only their ghosts.
- **Transitions.** A new reading fades the chips out over 120 ms at its first note-on and back in over 250 ms once the gates pass. A key change crossfades over 300 ms.

### 2.9 Algorithm 6: habits (`arsenal/practice_habits.py`)

- **Input:** every session in `state/arsenal/performance`, via `practice.chord_sequences(doc, exact)` (`practice.py:3245`) at both levels, with `min_count = 1`.
- **Weights:** sessions from the last 24 h count double; older ones decay with a 30-day half-life.
- **Output:** `state/arsenal/practice/habits.json` (git-ignored under `state/*`, `.gitignore:122`):

```json
{ "api": "arsenal.practice.habits/v0", "sessions": 6, "half_life_days": 30,
  "after":  { "4": { "1": { "w": 38.1, "n": 45, "sessions": 6 }, "5": { "w": 20.2, "n": 24, "sessions": 5 } } },
  "after2": { "6m>4": { "1": { "w": 9.0, "n": 10, "sessions": 3 } } },
  "colour": { "4": "4maj13#11", "1": "1maj9", "6m": "6m11" },
  "bass":   { "4>1": "1/3" },
  "familiar": { "4maj13#11": 0.98, "5^7": 0.04 } }
```

Numbers and counts only: no session ids, no times, no letters. Staleness is read from file modification times, never stored in the payload.

### 2.10 UI

**Placement** (collision boxes as in `chord-suggestions.md` 3.1):

| Situation | Where the chips go |
|---|---|
| Left margin at least 220 CSS px | `<aside id="suggest">` in the left margin, first chip level with the label centre |
| Narrow margin in 9:16 | on the glass, in the cue-chip band (y 28-144), only while no CLAUDE chip is up |
| 16:9 | on the glass slot x 50-950, y 464-568, pending the trail-foot receipt (SR7) |
| Deck docked | column stays left if the margin allows, else the glass fallback |
| Legendary banner holding | chips wait at alpha 0 |

**Chip face:**
- Line 1: name and number (the deck's `nameText` and `numberHtml` look, read-only imports from `deck.js`).
- Line 2: at most two reason words in small caps at 0.62 alpha.
- A thin moonlight `#C8DCFF` hairline; a dashed hairline for stretch.
- No scores on the face.
- Hover line after 600 ms: one plain sentence, with the evidence count.

**Actions:**

| Input | Result |
|---|---|
| Hover 250 ms (`deck.js` `HOVER_MS`) | The chip's `arrive` keys get the `suggest` ghost on the glass (solid hairline rim at 0.3 on white keys and 0.4 on black keys, no fill, no breathing). `stay` and `lift` keys are not drawn. |
| Click | Claude plays **the move**: the held voicing, then the suggestion, 0.8 s each, `keys` timbre, velocity 44. It goes through the existing `createClaudeVoice` and player (`cues.js:1227`) as Claude's notes, which never reach `sounding`, the log, the tracker or rarity. |
| Shift-click | The suggestion alone |
| He plays it | Every chord pitch class sounding for 150 ms counts as an accept. The chip pulses once in size (1.0 to 1.15 to 1.0 over 200 ms), then the chips follow the new chord. |
| `` ` `` (Backquote) | Cycles off, chips, chips + keys. `e.repeat` is ignored; the Ctrl, Meta, Alt and INPUT guards apply. Handled before the `KEYMAP` lookup. |

**Top bar:** `<select id="suggest-select">` in the theory group beside Numbers, Minor and Key (`piano.html:62-80`), with the options `off | chips | chips + keys`.

### 2.11 Settings (`safeGet` and `safeSet`; the column's `...` menu except the first)

| Setting | Values | Default | localStorage key |
|---|---|---|---|
| Suggest | off / chips / chips + keys | chips | `arsenal.piano.suggest` |
| How many | 2 / 3 / 4 | 3 | `arsenal.piano.suggest.count` |
| Stretch chip | on / off | on | `arsenal.piano.suggest.stretch` |
| Sources | theory, my moves (each on or off) | both on | `arsenal.piano.suggest.sources` |
| One-finger moves only (Sunshine's "Keep Three, Move One") | on / off | off | `arsenal.piano.suggest.oneFinger` |
| Bass-only moves (Sunshine's "Moving Floor") | on / off | off | `arsenal.piano.suggest.bassOnly` |
| While recording | hide / show beside | hide | `arsenal.piano.suggest.whileRec` |
| Stats (not a setting) | `{reading: {chip core: {shown, accepted, ignored}}}`, capped at 300 readings | | `arsenal.piano.suggest.stats` |

Query overrides for receipts, never stored: `?suggest=off|chips|keys`, `?suggestCount=2|3|4`.
Receipt hook: `window.__piano.suggest = { suggester, view, last(), stats() }`.

### 2.12 Jam-build files touched, and when

Nothing below is edited until the owning build is committed by Vandor, its receipts are green, and no lock is held on the file (jam-spec 13.0, 13.1).

| File | Owner in the jam build (13.3) | Suggestion step | Change | Sequence against v2 waves |
|---|---|---|---|---|
| `arsenal/serve.py` | B1 cue routes, then J3 | SG5 (also L2, SG9) | `GET /api/practice/habits`: serves `habits.json`, rebuilding under a lock when any session file is newer (at most once per 30 s); on failure it serves the last good file, or `{sessions: 0}` | V2-B also edits `serve.py`: run SG5 before V2-B or after it, never in the same wave |
| `arsenal/practice.py` | B2, then J4 (registration) | SG5 | `habits` and `next` delegated at the top of `main` (`practice.py:5006`), exactly like `riff` | none |
| `arsenal/web/piano/glass.js` | J8 (creates it) | SG6 | `ghosts.suggest` state; a second image slot `panel` for the glass-fallback chips (the cue `chip` slot stays Claude's) | V2-B edits `glass.js`: sequence after V2-B, or give `glass.js` a single owner for that wave |
| `arsenal/web/piano.js`, `piano.html`, `piano.css` | J9 | SG7 (later L0) | Imports; `suggester.update(frame)` in `renderFrame` after `tickKey` and the transport tick; `noteOn` feeds `noteOnTimes`; `view.layout` from `fitCanvas`; the Backquote key before `KEYMAP`; `suggest-select`; `suggest.css` link; `window.__piano.suggest` | V2-B, V2-D, V2-E and V2-G all have `piano.js` integration steps: one owner per wave |
| `arsenal/web/piano/deck.js` | J8 | none (read-only import of `nameText`, `numberHtml`, `HOVER_MS`) | — | — |
| `arsenal/web/piano/transport.js` | J7 | none in v1 (reads `frame.run` via `piano.js`; may import `createRestDetector`) | — | v2 "other nexts" needs `onPosition`: with V2-A or V2-G |
| `arsenal/web/piano/cues.js` | B1, then J7 | none (uses the voice and player as they are) | — | — |
| `arsenal/jam/schemas.py` | J0 (conductor only) | SG9 | `SOURCE_KINDS` gains `"suggest"`, with a note to running phases | contract change |
| `arsenal/pianocue.py` | J3 | SG9 | `card add --from-suggest` | — |
| `arsenal/pianocue_voicing.mjs` | J1 | SG9 (optional) | a `near` style that delegates to `near.js` | — |
| `arsenal/practice_riff.py` | J4 | v2 | one talking point from accept and ignore counts | with V2-C |

### 2.13 CLI

- `py -m arsenal.practice habits [--root] [--out] [--json]` builds `habits.json`.
- `py -m arsenal.practice next CHORD|NOTES [--key "Db major"] [--after PREV] [--count 3] [--json]` pipes a request to `node arsenal/suggest_bridge.mjs` and prints the chips, with reasons, near voicings, movement and evidence counts.
- Until SG5 registers these, the same commands run as `py -m arsenal.practice_habits` and `node arsenal/suggest_bridge.mjs`.

### 2.14 Receipts (all must pass before "built")

| # | Check | Pass |
|---|---|---|
| SR1 | Reading parity: `readings.js` against `practice name` on the whole reading fixture | 100% match on core, number and bass degree, including `4maj13#11` for the worked example |
| SR2 | Transposition: 40 held cases in all 12 keys | identical cores, numbers and reasons; letters follow `spellForKey` |
| SR3 | Read-back: every chip voicing through the sliced `Theory.detect` | `exact` or `enharmonic`, or a `reads` line; zero silent mismatches |
| SR4 | Near voicing: the worked example and the 5sus case | the section 6 chips with movements 3, 3, 4 (stretch 6); no voice below the held bass minus 7 or above the top note plus 2 |
| SR5 | Bridge parity: 20 seeded held chords through `practice next --json` and through the page's `__piano.suggest.last()` | chips byte-identical once timing fields are removed |
| SR6 | Flicker: offline replay in node of synthetic sessions (note gaps p25/50/75 of 190/250/400 ms, pedal down 60-95%) | 0 chip changes with an unchanged reading; 0 chips during busy spells; stale chip visible for under 120 ms |
| SR7 | Collision: chip rectangles against every canvas element box, in both framings, at margins 180, 220 and 400 px; the 16:9 trail foot measured | zero intersections on the canvas; column outside the canvas at 220 px or more; at least 60 px above the 16:9 trail foot |
| SR8 | Clean take: seeded note stream, `whileRec = show beside`, 5 s REC, against a run with suggestions off | every recorded frame MAE 0 |
| SR9 | Isolation: click every chip for 60 s | `sounding`, log events, tracker histogram and rarity events unchanged by Claude's notes |
| SR10 | Honesty and privacy: `habits.json`, the route payload, `git status` after a build | no session ids or times; "your move" only with 3 plays in 2 sessions; every word in `REASONS`; no tracked file changed; tests use synthetic sessions only |
| SR11 | Cost: 60 s replay on the page | recompute p95 at most 2 ms; frame time p95 within 0.5 ms of suggestions off |
| SR12 | Toggle key | Backquote cycles the modes and produces zero note-ons; all 33 `KEYMAP` keys still play; the deck's 8.7 keys still work |

---

## 3. Lights: the recommendation

### 3.1 Three options

Prices are research estimates, to re-check at purchase time. Confidence as in `key-lights.md`: high means read on a vendor page, low means an estimate.

| | **A. Best DIY (recommended)** | **B. Budget DIY** | **C. Plug-and-play** |
|---|---|---|---|
| **What it is** | A ready-built WLED controller with a fuse, level shifter and **Ethernet** (a GLEDOPTO Ethernet model or similar); a 2 m WS2812B strip at 144 LEDs per metre, black PCB, cut to about 176 LEDs; a UL-listed 5 V 6-10 A power supply feeding both ends; an aluminium diffuser channel with at least 12 mm inside width; removable mounting on the lip behind the keys | The same strip, supply and channel, with a bare ESP32 dev board, a 74AHCT125 level shifter, a 1000 µF capacitor and a 330 Ω data resistor | **Piano LED Plus**: a finished 123 cm strip with its own app |
| **Price** | about $90-150 in total (low); controller about $26-48 (medium) | about $50-80 (low) | EUR 179 on sale, EUR 199 list (high) |
| **Daniel's effort** | about 2-3 hours: screw-terminal wiring, mounting, one Ethernet cable; about 2 minutes of calibration presses (low estimate) | about half a day, including soldering and owning the 5 V wiring safety (low estimate) | about 30 minutes (low estimate) |
| **What Daniel buys or installs** | Buys the parts above and an Ethernet cable. WLED firmware usually comes pre-flashed; an update is a firmware download (his OK). **Nothing installed on the PC.** | Buys the parts. Flashes WLED from its web installer, which is a firmware download (his OK). Nothing installed on the PC. | Buys the device (and maybe a 5-pin MIDI cable). Installs the vendor app on a phone or PC. |
| **How our code drives it** | The page composes a 176-LED frame (`lights.js`) from state it already has: his `noteColor`, Claude's moonlight, ghosts, Try targets, the suggestion's `keys`. It posts changed frames to `serve.py`. `arsenal/lights.py` (stdlib `socket`) forwards each one as **DRGB UDP to port 21324** with a 2 s timeout, so the strip blanks if arsenal dies. | Identical code, sent over Wi-Fi. Jitter must be measured (LR4); if it fails, move to option A's controller. | **It doesn't.** The strip follows its own app. Lighting keys from a computer through its MIDI IN is undocumented, so the vendor must be asked before buying. It can never show Claude, ghosts or suggestions. |
| **Shows** | everything the page shows | everything the page shows | its own lessons only |
| **Latency** | steadiest (wired); target 20 ms or less from key press to light, to be measured | depends on the Wi-Fi at the piano | "less than 20 ms" (vendor claim) |

**Not recommended:**
- **A keyboard with lit keys.** The NI Kontrol S88 MK3 ($1,299) has no Windows light control; the others are beginner or 61-key instruments.
- **The ONE Hi-Lite.** It lights red and blue only.

**A fourth route, if the page must not be needed.** If the lights have to work with the page closed (question 3), the option is a standalone Piano LED Visualizer box: a Raspberry Pi Zero 2 W, the same strip, about $75-100 in parts. It lights only his own notes, from MIDI, and takes guide colours per channel. Getting MIDI to it from the KeyLab is unproven (does the DIN Out carry the keybed?).

### 3.2 Why A

It is the only option where the physical keys speak the page's language.
- **Colours:** his pitch colours are his alone, and Claude is moonlight, never pitch-tinted (C12).
- **Ghosts:** a suggestion lights only its `arrive` keys, the same way the glass does.
- **Wiring:** Ethernet removes the main risk, Wi-Fi jitter, with no PC install.
- **Failsafe:** built into the protocol. DRGB's timeout byte blanks the strip when frames stop.

### 3.3 Design choice for Path A: the page composes and the server forwards

`key-lights.md` proposed composing frames on the server. This plan composes them **on the page**:
- **One colour source.** `noteColor` (`piano.js:338`, OKLCH) and the ghost grammar already live on the page. A Python twin would be a second copy to keep in step with its own fixture.
- **Identical by construction.** The on-screen virtual strip and the UDP payload are the same bytes (LR1).
- **Background tabs.** Claude's cues already reach the page through the cue stream, so nothing is lost. Web MIDI events still arrive while the tab is hidden, and sends are event-driven. Only animations (breathing) pause.
- **Safe failure.** Chrome slows timers in a tab hidden for more than 5 minutes. Heartbeats stop, and the strip blanks after 2 s instead of freezing on stuck notes.
- **When to flip.** If Daniel turns out to play mostly with the page hidden, move composition to the server with a Python twin and a shared frame fixture.

### 3.4 Lights modules (Path A; all new unless noted)

| File | What |
|---|---|
| `arsenal/web/piano/lights.js` (pure) | `composeFrame({ his, claude, ghosts, suggest, tryTargets, map, budget, t }) -> Uint8Array(ledCount * 3)`, using the grammar in `key-lights.md` section 3. Suggestions: `arrive` keys get moonlight on their edge LEDs at 0.3; `stay` keys already show his colour, so nothing is added; `lift` keys are unlit in v1. A current budget scales the frame so the estimated draw (`sum(rgb)/765 × 60 mA` per LED) stays under 80% of the supply rating. |
| `arsenal/web/piano/lights-view.js`, `lights-test.html` | The virtual strip: a thin unrecorded DOM canvas under the stage. The calibration drill UI (sweep one LED, press the key under it, save the map). |
| `arsenal/lights.py` | Stdlib sender: DRGB (DNRGB above 490 LEDs), config and map I/O, frame length check. Re-sends the last frame every 1 s only while the page posted within 1.5 s. CLI `py -m arsenal.lights blank / sweep / test`. |
| `serve.py` (existing, after SG5) | `POST /api/piano/lights/frame` (octet-stream, `ledCount × 3` bytes); `GET`/`PUT /api/piano/lights/config` and `/map` |
| `state/arsenal/lights/config.json`, `map.json` (untracked) | host, port, protocol, LED count, reverse flag, brightness cap; `midi -> [led indices]` |
| `piano.js`, `piano.html`, `piano.css` (existing, J9's; after SG7) | The Lights select (`off / screen / strip`); feeds `composeFrame`; posts frames |
| `tests/lights_compose.test.mjs`, `tests/test_arsenal_lights.py` | Composition and budget; sender bytes checked against a local UDP listener (no hardware) |

**Light settings:**
- `arsenal.piano.lights`: `off | screen | strip`, default off.
- `arsenal.piano.lights.brightness`: default 0.35.
- `arsenal.piano.lights.whileRec`: default `notes only`. While REC runs, the strip shows only what is in the video (his notes and Claude's played notes). Hints go dark: suggestions, ghosts and Try targets.

**Light receipts:**

| # | Check | Pass |
|---|---|---|
| LR1 | Byte parity: virtual strip frame against the UDP payload, via a local listener | identical |
| LR2 | Failsafe drill: kill the server with a chord lit | strip blank within 3 s; dated receipt |
| LR3 | Calibration | 88 of 88 keys mapped; 10 random keys light under the right key |
| LR4 | Latency: 240 fps video, 30 presses, count frames from key-down to light | median at most 20 ms, p95 reported |
| LR5 | Budget: worst case (88 keys at full velocity, pedal down) | estimated draw under 80% of the supply; WLED's current limiter set just below the supply rating |
| LR6 | Isolation: lights on and off | `sounding`, log, tracker and rarity unchanged (INT 1) |
| LR7 | Camera test (only if he wants lights on camera) | a phone clip with no visible banding at the chosen brightness |

---

## 4. Phased plan

### Phase 1: the suggestion engine (new files only; can start now, in a worktree)

| Step | Scope | Depends on | Exit |
|---|---|---|---|
| SG0 Contracts | fixtures under `tests/fixtures/suggest/`; `REASONS`, the Chip shape and the habits schema frozen in module headers | none | the fixtures load; the reading fixture regenerates from `practice name` with no diff |
| SG1 Reading twin | `readings.js` and its two tests | SG0 | SR1 |
| SG2 Near voicer | `near.js` and its test | SG0 | SR3, SR4 (voicing half) |
| SG3 Habits | `practice_habits.py` (its own `main`) and a test | SG0 | synthetic sessions give known counts; SR10 (payload half) |
| SG4 Engine and bridge | `suggest.js`, `suggest_bridge.mjs`, engine test | SG1, SG2, SG3 | SR2, SR4, SR6 |

Vandor commits each step, since Vandor is the sole committer. No existing file changes in this phase.

### Phase 2: on the page (after the jam build lands; recommended after J10, so the first jam night stays uncluttered)

| Step | Scope | Depends on | Exit |
|---|---|---|---|
| SG5 Routes and verbs | `serve.py` habits route; `practice.py` registration of `habits` and `next` | J3 and J4 committed; SG4 | route tests; `practice next` matches the bridge |
| SG6 View and glass | `suggest-view.js`, `suggest.css`, `suggest-test.html`; the `suggest` state and `panel` slot in `glass.js` | J8 committed; SG4; sequenced against V2-B | SR7 (test-page half) |
| SG7 Integration | `piano.js`, `piano.html`, `piano.css`; `lanes/suggest_verify.mjs` | J9 committed; SG5; SG6 | SR5, SR7, SR8, SR9, SR11, SR12 |
| SG8 First suggestion night | Daniel holds chords for 10 minutes; weights and timings tuned by ear; stats read from `__piano.suggest.stats()` | SG7 | Daniel says which chips he took and which felt wrong; tuned values land as a commit |

### Phase 3: fitting the jam space (after SG8)

| Step | Scope | Files |
|---|---|---|
| SG9 Keep as card and doors | "Keep as card" creates a `try` group, `progression` card through `POST /api/piano/deck/cards`, with `source.kind: "suggest"` (conductor contract change); doors in `suggest.js`; stats in `state/arsenal/jam/suggest/stats.json`; `pianocue card add --from-suggest`; optional `near` style | `schemas.py`, `serve.py`, `pianocue.py`, `pianocue_voicing.mjs`, `suggest.js`, `suggest-view.js` |
| v2, with the jam waves | "other nexts" over a Loop (`transport.js` `onPosition`); a riff talking point (with V2-C); KeyLab pads that play chips (with V2-G); show in recording (in V2-D's strip slot); lift rims | each wave's own owner files |

### Phase 4: lights (after Daniel picks)

| Step | Scope | Gate |
|---|---|---|
| L0 On-screen strip | `lights.js`, `lights-view.js`, `lights-test.html`; the Lights select with `screen`; LR1 (compose half), LR5, LR6 | Daniel picks A or B, or asks for the free preview first; after SG7 (one `piano.js` owner at a time) |
| L1 Measure and buy | Daniel measures the lip behind the keys (depth and height) and checks whether Ethernet reaches the piano; prices re-checked; **Daniel buys** | his OK on the shopping list |
| L2 Sender | `lights.py`, the routes, config; WLED flashed or updated (**his OK**, it is a download); LR1 over UDP, LR2 on hardware | parts arrived |
| L3 Calibration | the sweep drill writes `map.json`; LR3 | L2 |
| L4 Latency | 240 fps receipt, LR4; on Wi-Fi (option B) a failure means switching to an Ethernet controller | L3 |
| L5 Camera (optional) | test clip; brightness default; LR7 | he wants lights on camera |

**If Daniel picks C:** no code. One setup note, and the vendor is asked about MIDI IN before he buys.
**If he picks the standalone box:** no code in v1. The page could later send guide notes to it, but only after V2-E's MIDI out, and V2-E waits for his approval of a loopback download.

---

## 5. Questions for Daniel (four, each with a recommended default)

1. **The chips.** When you hold a chord still you get 3 chips: home, your move, and a colour or stretch that take turns. Keys light only while you point at a chip, and clicking plays your chord then the suggestion. Keep that, or would you rather have 2 chips, or have the first chip's keys always lit?
   *Default: 3 chips, point to light, click plays the move.*
2. **Which lights?**
   - (A) Best DIY: about $90-150, an evening of assembly; the keys show your colours, Claude's moonlight and the suggestions.
   - (B) Budget DIY: about $50-80, with soldering.
   - (C) Piano LED Plus: EUR 179-199, 30 minutes, but only its own app's lessons.
   - (D) Not yet: show me a free on-screen strip first.

   If A or B: measure the flat strip behind the keys (how deep and how tall), and tell me whether an Ethernet cable reaches the piano.
   *Default: D, then A.*
3. **Should the lights work with the piano page closed** (playing straight into FL Studio)?
   *Default: no, the page stays open. That is what lets the lights show Claude and the suggestions. A "yes" points to a standalone box that lights only your own notes.*
4. **Lights on camera.** Subtle practice lights, where hints go dark while you record and only your notes and Claude's notes stay lit? Or brighter on-camera lights for TikTok, which needs one test clip for flicker?
   *Default: subtle, hints dark while recording.*

---

## 6. For Vandor (not for Daniel)

- **Ownership.** Phase 1 creates files only and touches nothing J0-J9 owns, so it can run beside the jam build. Everything in section 2.12 waits for 13.0 landing plus the one-owner-per-wave rule. `glass.js` and `piano.js` are the two contested files (V2-B, V2-D, V2-E, V2-G): schedule SG6 and SG7 into their own wave or hand them over explicitly.
- **Stays true from the research:**
  - the page label misreads his `4maj13#11` as `6m11/4`, so the engine must never key on the label;
  - `voice_lead` anchors to the style's register (`REGISTER_WINDOW = 7`, `pianocue_voicing.mjs:602`);
  - the habits builder must use `min_count = 1`;
  - no new performance-log event kinds, because `validate_event` rejects the whole batch.
- **Unverified and carried forward:**
  - the 16:9 rail and trail-foot height (SR7 measures it);
  - the timings and weights, until SR6 and SG8;
  - `readings.js` duplicates Python rules until V2-F, and SR1 is the tripwire;
  - light prices; the KeyLab lip size; whether the KeyLab DIN Out carries the keybed; whether Piano LED Plus accepts notes on MIDI IN; Wi-Fi at the piano; Windows MIDI Services on this update-blocked machine.
- **Privacy.** This plan holds no session ids, no clock times and no transcriptions. The counts quoted come from `chord-suggestions.md`, already aggregated.

## Daniel's decisions (2026-09-14, answered on Discord)

On Discord Daniel answered the questions below, sent with recommended defaults, with: "Yes to all of them! Really good ideas!". Recorded as:
- **Q1 (chips):** 3 suggestion chips. A chip's keys light only while you point at it, and a click plays the move.
- **Q2 (lights):** start with option D, the free on-screen strip, then option A, best DIY. Before anything is bought, Daniel measures the lip behind the KeyLab 88 mk3's keys and checks whether an Ethernet cable reaches the piano. The purchase itself stays his call.
- **Q3 (page closed):** no. The lights do not need to work with the piano page closed.
- **Q4 (brightness):** subtle practice lights, with hints dark while recording.
