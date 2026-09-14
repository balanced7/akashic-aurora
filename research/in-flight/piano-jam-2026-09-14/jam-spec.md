# Piano jam: the build spec (cards, loops, verbs, riff talk)

| | |
|---|---|
| Status | Build spec, 2026-09-14. Design only: no code edited, no server or browser started. Supersedes the three lane designs where they disagree; they stay the reference for detail this file cites by section. |
| Built from | `design-ux.md` (UX), `design-data.md` (DATA), `design-music.md` (MUSIC) in this folder; `research/in-flight/fl-jam-bridge-2026-09-14/fl-jam-bridge-plan.md` (FL); the cue integration notes (scratchpad `piano-cues-integration.md`, INT); the code as it stands tonight (`pianocue.py`, `serve.py`, `cues.js`, `piano.js`, `log.js`, `performance.py`, `practice.py`, `pianocue_voicing.mjs`). |
| Checked tonight | Every seed line in section 12 went through `node arsenal/pianocue_voicing.mjs` (scratchpad `jam/seed_check.py`, output `jam/seed_check.txt`): all chords read back `exact` or `enharmonic`. The same run confirms MUSIC 1.3: `spread` tops reach Eb5, F5 and G5 (Bbmaj13, Bb13, Bb7sus4/Eb), inside Daniel's top line, so loops need the band voicer. |
| Starts after | Three running builds land (section 13.0). |

Daniel, verbatim:

> "I want us to be able to play in this space, can you make verbs so you can play chord progressions or show loops of
> chords for me to try, I can then riff on that and play with it and we can discuss it"
>
> "so I can click and hear concepts you are describing and have a visual for them, we can make chord templates"
>
> "ooooh, can we make a verb for you to be able to play a chord you are curious about or hovering it in the viewer?" /
> "We could have a lot of fun with this!" / "I just play it by feel" / "I know a little bit but not much >__< this is
> intuition and memory"

**Privacy rule (resolves DATA Q5).** The repo is public. Tracked files (this spec, `arsenal/jam/seed/deck-v1.json`)
carry no session ids, clock times or transcriptions of his playing. Moment links live only in
`state/arsenal/jam/seed/moments-v1.json` (git-ignored), which `deck seed` merges when present. `design-data.md` section 10
and `design-music.md` section 10 name session ids: strip them before this folder is ever committed.

---

## 0. The system in one screen

1. **Cards.** A card is a concept Daniel can hear: a plain-words title and one-line meaning, a chord line written in
   Nashville numbers against a key, optional exact notes (his own voicings), a tempo, and three short lines (what it
   is, why it matters to him, what to try). Cards live on the server under `state/arsenal/jam/`; Claude publishes them
   from the CLI, Daniel keeps and saves them from the page.
2. **The deck** is a drawer at the right of the piano stage (outside the recorded canvas). Each card has chord chips
   (hover = silent ghost keys, click = hear that chord) and five buttons: **Play, Show, Loop, Try, Hear me**.
3. **Runs.** Play, Loop and Try each become a **run** the server records. The server owns the run's definition and its
   tempo segments; **the page keeps time**: a bar clock on `performance.now()`, handing the cue player one bar at a
   time, so every change (tempo, next card, stop) lands on a bar line with nothing to cancel.
4. **The backing** is built by a pure, seeded groove generator (`groove.js`) over voicings from a new register-banded
   voicer (`band` style in the bridge) that keeps Claude at or under G4 and leaves Daniel's register (Bb4 up) free.
5. **Two surfaces.** The canvas (stage) is recorded; a transparent glass layer over it is not. Jam view `auto`
   (default) shows Claude's keys and ghosts on the stage while he practises and moves them to the glass the moment REC
   starts, so a take is only Daniel.
6. **Discussion.** Every run is aligned to the practice log. `py -m arsenal.practice riff` reads his notes against the
   loop's bars and chords and writes facts with times, one question and one thing to try. In v1 the talk happens in
   chat; in v2 it comes back as a riff report card in the deck.
7. **Templates.** "Keep" copies a card into Daniel's Kept group; "Keep what I just played" saves his sounding voicing
   as a chord card; `pianocue template save-from-moment` does the same from the log.

---

## 1. Conflicts between the designs, and how this spec resolves them

| # | Topic | UX | DATA | MUSIC / FL / INT | Resolution |
|---|---|---|---|---|---|
| C1 | Who keeps time | page transport | server holds def + epoch segments, page keeps time, acks | MUSIC: page tempo map; FL: FL keeps time | **Page keeps time, server is the record.** Every Loop/Try/Play from the page or CLI goes through `POST /api/piano/jam/start`; the page schedules from the `jam` event. FL as clock is the v2 Route F backend under the same run model. |
| C2 | Hand-off to the player | one pass at a time | slots, commit ≤ 250 ms ahead | one bar + pickups, absolute `at`, `extend` for ties | **One bar + pickups** at `t(bar) - (1 beat + 150 ms)` (MUSIC 6.2). Needs `player.handle(cue, {at, id})` and `player.extend`. |
| C3 | When a change lands | next bar; key and card rev at top of pass | bar or loop boundary ≥ 300 ms away | first bar line ≥ 1 beat + 150 ms away | **1 beat + 250 ms** at the server (MUSIC's 1 beat + 150 ms hand-off, plus 100 ms for the frame to reach the page; section 9.4). Defaults: tempo → bar; swap card → bar (UX, DAW-like); key → top of pass; stop from the page button → now (80 ms fade); `loop stop` from the CLI → bar. |
| C4 | Bus and routes | `card` event, `/api/piano/cards` | `deck` and `jam` events on `/api/piano/cues`; `/api/piano/deck/*`, `/api/piano/jam/*` (POST verbs) | FL: separate `/api/jam/*` SSE | **DATA's routes and named events on the one stream.** No second SSE; FL's v2 backend publishes `jam {op:"clock"}` frames on the same stream. |
| C5 | Card shape | provenance kinds (concept/report/kept), voicings stored in card | musical kinds, numbers + optional notes, computed `page_reads` | per-chord tones/scale/voicings computed | **DATA's stored card** plus `meaning`, `theory_name`, `group`, `groove`, `backing`. Voicings, tones and scales are never stored in the card: the server computes them into the resolved `def` (MUSIC 3.1 fields). Reports are a separate object (v2). |
| C6 | Transposing | shift every note -6..+5 | numbers re-resolved; exact notes shifted nearest | re-voice per key | **Numbers are re-voiced per key by the bridge** (cached); **exact notes (his voicings) shift by the nearest interval** with octave folds (DATA 2.6). Shifting numbers is only a fallback while the bridge answer is pending. |
| C7 | Key changes in a card | one tonic per card | key items as degrees of the card key | loop 6 used one tonic | **DATA's key items.** Chips show numbers in their section's key with a small "in D major" header; the Nashville row follows the section key while a run plays it. The lesson "numbers restart at 1 in the new key" is the point of those cards. |
| C8 | Loop voicing | bridge `spread` / `shell` | card `voicing.style` (default spread) | new `band` voicer | **Loop and Try backing use `band`** (full/comp/bass). **Play** uses exact notes if the chord has them, else the card's style (default `spread`), because Play is a demonstration, not a bed. Added rule `upper: "same"` (4.1, 10.1) so the lament bass's hands do not move (MUSIC 5.8 contradicted its own no-doubled-bass rule). |
| C9 | Duck | gain 0.5, 0.8 s, back over 400 ms | none | -3 dB, held 1.2 s, release τ 0.6 s | **MUSIC's duck**: his median attack gap is 216-316 ms, so UX's setting would pump on every breath. |
| C10 | Loop notes' identity | `source: "claude"` | new source `jam` in both mirrors | INT: cue notes never enter `sounding` | **No new source.** Transport cues are page-local with `source: "claude"` and a transport-owned cue id (`jam:<run>:<bar>`). The server protocol and the parity test stay untouched. |
| C11 | Big chord label during a jam | names his notes plus the backing (stage) | not addressed | INT invariant 1: cue notes never reach `detect()` | **INT invariant wins.** The label, chips, Nashville row, staff, log, key tracker and rarity are Daniel's alone. Claude's chord is named by the cue chip (and the DOM strip). |
| C12 | Claude's hand on the keys | moonlight `#C8DCFF`, 60% depth, no trails | not addressed | INT: pitch colour, trails, bursts like Daniel's | **UX identity**, applied to INT's `cueNoteOn`: no trails, bursts or pitch tint; moonlight emissive capped at 0.75 of his lift. Pitch colour stays his alone. |
| C13 | Jam log kind | add `jam` kind to the log | no kind change; meta fields + run files | `jam` kind by the log lane | **DATA: no new event kind.** Runs live in `state/arsenal/jam/runs/`; alignment uses three additive `meta` fields on session open (`page_id`, `t0_perf_ms`, `opened_at_client` always). This removes the batch-400 hazard for good. |
| C14 | Recording | jam view auto/stage/glass; Claude's sound mixed in for stage | `display.in_recording` false by default | INT chip in canvas with `cueChip: norec` | **Jam view only** (`auto`, `glass` in v1; `stage` in v2). `display.in_recording` is dropped. In `auto`, REC moves Claude's keys, ghosts and chip to the glass and never connects Claude's voice to the recorder's audio track. |
| C15 | Old pages | n/a | long `sequence` cue fallback (`cue-loop`) | n/a | **Dropped.** Page and routes ship in one wave; `loop start` with no `jam1` page exits 3: "reload the piano page". One run mode less. |
| C16 | `try` means two things | Try = count-in + ghosts in time for him | `try` verb = play once | | **Page words are the verb words.** `pianocue card play` = Play once; `pianocue try` = Try in time; `pianocue loop start` = Loop; `pianocue card info` prints a card (DATA's `card show` renamed; `card show` is now the silent ghosts). |
| C17 | Where files live | `state/arsenal/piano/deck/`, `jams.jsonl` | `state/arsenal/jam/` | `state/arsenal/piano/calibration.json` | **Everything under `state/arsenal/jam/`** (deck, seed moments, runs, riffs, reports, calibration). |
| C18 | Riff verb | "the verb name is theirs" | `practice riff [RUN\|latest]`, in practice.py | `practice riff <session>`, in `practice_riff.py` | **Run-centred invocation (DATA), code in `arsenal/practice_riff.py` (MUSIC)** so `practice.py` gets a 3-line registration only. |
| C19 | Signature chord names | reads-as line | `page_reads` cached | loops use maj7#11 | **Loops use `maj7#11`** (checked exact tonight in Eb, Db, F, and enharmonic in Gb); `maj9#11`/`maj13#11` appear only as exact-note chords with a reads-as line. Adding THEORY templates is v2, owned with the spectacle rarity table. |
| C20 | Groove vs backing | backing full/comp/bass/pad | playback hold/legato | backing + groove (6 grooves) | **Both settings.** v1 grooves: `hold`, `ballad`, `pulse`; v1 backings: `full`, `comp`, `bass`. v2: `swell`, `arp`, `gospel`, call and response, `pad` backing and timbre. |
| C21 | Marks "in the chord" | pitch class in the voicing | n/a | chord tones T | MUSIC (T), so a plain 5th left out of a `comp` voicing is not called colour. v2 feature. |
| C22 | FL lane's `arsenal/jam.py` | | | FL: a sibling module `jam.py` | **`arsenal/jam/` package.** The v1 store, runs and CLI live there; FL's v2 pattern contract, SMF export and WinMM backend become `arsenal/jam/fl.py`, `smf.py`, `midi_winmm.py` in the same package. |

---

## 2. Feature set

### 2.1 v1 (tonight-ish: the first build wave, then Daniel plays)

| Area | In v1 |
|---|---|
| Cards | Seed deck of 17 cards (section 12); `card add/edit/rm/restore/trash/info/list/keep`; exact-note chords; variants; key items; checks; moments (from state only). |
| Deck UI | Drawer inside `.stage` (overlay when the side margin ≥ 392 px, else dock; never reflow during REC); tabs Tonight, Your moves, Try this, Kept, All; search; NEW handling that never moves cards under his mouse while he plays; key selector (as written / my key now / his keys / all 12); tempo `[-] [+]` and tap. |
| Card actions | **Play** (once), **Show** (silent ghosts held), **Loop** (count-in 1 bar, then backing), **Try** (in time: count-in, ghosts of the current chord, incoming ghosts on the last beat, "with bass" backing), **Hear me** (replay a cited moment locally, never broadcast); chips: hover 250 ms = ghosts, click = hear, shift-click = Show that chip; "reads as" line. |
| Templates | **Keep** (copy into Kept); **Keep what I just played** (page capture, DATA 2.10); `template save-from-moment`, `template save-last`. |
| Transport | Bar clock with step tempo changes, count-in ticks, quantised launches and swaps, stop now / at bar / at pass, `passes N`, `ending cut`. Grooves `hold`, `ballad`, `pulse`; backings `full`, `comp`, `bass`; humanize with seed; bass approach notes (`walk` 0/1). |
| Sound | Built-in voice only: the darker `keys` preset (sine bass under E2), base velocity 44, polyphony 40 during a run, duck -3 dB held 1.2 s, count-in ticks. |
| Strip | DOM only: the deck's Now header (kind, card, key, bpm, NOW/NEXT chord and number, beat pips, bar, pass, Stop) and the pill when the deck is closed. |
| Keys | Claude's hand in moonlight (no trails); ghost rims with states target, incoming, hold, found; glass layer drawing the same when jam view puts them there; Esc/Backspace stops Claude. |
| Jam view | `auto` (default) and `glass`. |
| Courtesy | Remote sound waits for his rest (≤ 20 s) then becomes a knock (Enter plays, expires into Tonight at 60 s); remote ghosts wait ≤ 8 s; clear always at once; `--now` skips. |
| Runs | Every Play/Loop/Try is a run with `run.json` + `events.jsonl`; page acks; sound-owner lease (one tab sounds a loop); stream-loss stop after 2 bars; server-restart close. |
| Alignment | L1-L4 ladder (DATA 7.3) with the three `log.js` meta additions and `log.timebase()`. |
| Riff analysis | `practice riff`: alignment, per-slot note classes (in the chord / colour / rub / passing / outside, with slide-in), per-chord scale with the mode naming gate, landings, top-line degrees per bar (most played and per pass), per-pass range, velocity, rests, pedal share, phrases (split, contour, landing), anticipations, card checks, highlights with save commands, talking points T1-T7, T10, T13, T14, one question, one thing to try, loopback guard. Chat is the discussion surface. |
| Safety | MIDI echo guard in `midiRank`/`bindMidi` (INT section 8) lands even though MIDI out is v2. |

### 2.2 v2 (after Daniel's first nights with v1)

| Area | In v2 |
|---|---|
| Discussion in the deck | "Ask Claude" on the closing line; `pianocue jam wait` (harness-tracked background verb); riff report cards (lead-sheet lanes with his top-note degrees, three facts, one question with answer chips that write back, one Try-it card); "Hear pass N with the loop". |
| Marks | Glass marks on his notes during a run (quiet/teach), `your top: 9` in the Now header. |
| Grooves and sound | `swell`, `arp`, `gospel` (swing, push, spice), call and response with motif, tempo ramps, `pad` timbre and backing, `bass_mode: pedal`, `ending: home`. |
| Recording duet | Jam view `stage`: in-frame strip (UX 5.3 coordinates and collision map), Claude's voice mixed into the recorded audio, `BACKING BY CLAUDE` credit. |
| Rhythm | Tap-along calibration (`pianocue jam calibrate`), placement, drift, swing, motifs, call-and-response scoring (MUSIC 9.8-9.10), T8, T9, T11, T12, T15; enclosure and blue-note classes. |
| MIDI and FL | After Daniel approves a loopback download: MIDI out (bass ch 1, chords ch 2), `midi_offset_ms`, channel echo filter, FL Route F (FL as clock, `arsenal/jam/fl.py`), `.mid` export card action (FL Option A). |
| Hands and editing | Kept-card inline editing re-voiced by the bridge; Try "wait for me" with hints; KeyLab pad learn (Stop, Loop again, Keep that, Hear). |
| Names | THEORY templates `maj9#11`, `maj13#11`, `13sus4` with the spectacle rarity table and Nashville fixtures updated together. |
| Follow me | Loop tempo taken from his first bars (DATA Q7). |

---

## 3. Architecture and file map

```
 CLI (pianocue card/deck/try/loop/jam/template) ─┐
                                                  ├─> serve.py routes ─> arsenal/jam (cards, runs, align, resolve)
 page deck.js (Daniel's clicks) ──────────────────┘          │                 │
                                                             │                 └─> node pianocue_voicing.mjs (band)
                                         CueHub.publish_event("deck"|"jam") ─> /api/piano/cues SSE
                                                             │
 page: cues client ─> transport.js (tempo map, bar hand-off) ─> groove.js ─> createCuePlayer({at,id}) ─> Claude's voice
                          │                                                         └─> cueNoteOn / ghosts / chip
                          └─> POST ack (perf_ms of bar, log timebase)
 KeyLab ─> piano.js noteOn ─> sounding ─> log.js ─> performance store
 practice riff ─> runs + session events + groove_bridge.mjs (rebuild Claude's notes) ─> facts ─> chat (v1) / report card (v2)
```

| File | New or existing | Role |
|---|---|---|
| `arsenal/jam/__init__.py` | new | package marker, `API` constants |
| `arsenal/jam/schemas.py` | new | card, def, run, ack validators (shape and limits, DATA 2.9) |
| `arsenal/jam/cards.py` | new | `DeckStore`: atomic files, rev, trash, order, templates, seed install |
| `arsenal/jam/resolve.py` | new | card → `def` (sections, bridge calls, exact-note shifts, per-chord facts), in-memory cache |
| `arsenal/jam/tempomap.py` | new | bar ↔ epoch ↔ session `t_ms` (Python twin of `tempomap.js`, shared fixture) |
| `arsenal/jam/runs.py` | new | `RunStore`: start, change, stop, ack, owner lease, restart close, position |
| `arsenal/jam/align.py` | new | L1-L4 ladder |
| `arsenal/jam/cli.py` | new | the new `pianocue` verbs; `pianocue.py` delegates to it |
| `arsenal/jam/seed/deck-v1.json` | new, tracked | seed text and lines, no moments |
| `arsenal/web/piano/tempomap.js` | new | the page's bar math |
| `arsenal/web/piano/groove.js` | new | pure groove generator |
| `arsenal/groove_bridge.mjs` | new | node entry for Python (riff rebuild, v2 FL) |
| `arsenal/web/piano/transport.js` | new | run scheduler: bar hand-off, count-in, duck, lease, acks |
| `arsenal/web/piano/deck.js`, `deck.css` | new | the drawer, cards, chips, settings, Now header, pill, knocks |
| `arsenal/web/piano/glass.js` | new | the unrecorded 2D layer: ghosts, Claude quads |
| `arsenal/practice_riff.py` | new | riff analysis |
| `arsenal/pianocue_voicing.mjs` | existing | + `band` style, `tones_pc`, `upper: "same"` |
| `arsenal/pianocue.py` | existing | + `CueHub.publish_event`, `subscribe(caps, page)`, delegate to `jam.cli` |
| `arsenal/serve.py` | existing | + deck and jam routes, `?caps=&page=` on the stream |
| `arsenal/web/piano/cues.js` | existing | + `handle(cue, {at, id})`, `extend`, named-event listeners, `keys` timbre, duck, polyphony option |
| `arsenal/web/piano/log.js` | existing | + meta fields, `timebase()` |
| `arsenal/practice.py` | existing | + `riff` registration |
| `arsenal/web/piano.js`, `piano.html`, `piano.css` | existing | integration only |

---

## 4. Schemas

All JSON. Times are ISO 8601 UTC with ms (as `performance._now_iso`), or epoch ms where a field is named `*_epoch_ms`.
Unknown top-level fields are refused (400), as `validate_cue` does.

### 4.1 Card (`arsenal.jam.card/v0`, stored as `state/arsenal/jam/deck/cards/<id>.json`)

DATA 2.1-2.10 is the base. This spec adds five fields and one chord-item field, and removes `display`.

| Field | Type | Req | Meaning |
|---|---|---|---|
| `api` | `"arsenal.jam.card/v0"` | yes | |
| `id` | `^[a-z0-9][a-z0-9-]{0,47}$` | yes | seeds: slugs; page saves: `t-YYYYMMDD-HHMMSS-xxxx`; kept copies: `k-<source id>-xxxx` (truncated to 48) |
| `rev` | int ≥ 1 | server | +1 per write; updates and deletes send `if_rev` (409 when it moved) |
| `title` | string ≤ 80 | yes | a name in plain words |
| `meaning` | string ≤ 120 | yes | **new.** One line: what it does to the ear. Shown on the collapsed card |
| `theory_name` | string ≤ 40 | no | **new.** Small caps under the meaning ("Lydian", "pedal point") |
| `group` | `moves` \| `try` \| `kept` | yes | **new.** The deck tab. Tonight is derived (`updated_at` in the last 12 h, or published this page session); All is everything |
| `kind` | `chord` \| `progression` \| `loop` \| `concept` \| `moment` | yes | DATA 2.5 |
| `key` | key name (`nashville.js parseKey`) | yes | the card key; every number and key item is relative to it |
| `also_in` | [key name] ≤ 6 | no | "your keys" shortcuts on the key selector |
| `chords` | [ChordItem] 1..64 | yes (a concept may use only `variants`) | DATA 2.3 |
| `variants` | [Variant] ≤ 6 | no | DATA 2.4; allowed on any kind |
| `voicing` | `{style, voice_lead, octave}` | no | the **Play** voicing: default `spread`, false, null |
| `groove` | `hold` \| `ballad` \| `pulse` (v2 adds `swell` `arp` `gospel`) | no | **new.** The Loop default. Absent: `ballad` under 80 bpm, `pulse` from 80. A v2 value on a v1 page plays `ballad` |
| `backing` | `full` \| `comp` \| `bass` (v2 adds `pad`) | no | **new.** The Loop default. Absent: `comp` |
| `tempo` | `{bpm 30..240, beats_per_bar 2..7, feel}` | no | default 66, 4, `straight` (v1 always plays straight) |
| `bars` | int | no | ≥ total beats / beats_per_bar; the remainder is a rest |
| `playback` | `{velocity, arpeggio_ms, hold, count}` | no | Play only; default 48, 0, `legato`, null |
| `style`; `explanation` (≤ 400, req); `why` (≤ 300, req); `try` (≤ 300, req); `listen_for` (≤ 160) | strings | | DATA 2.2 |
| `checks` | [Check] ≤ 8 | no | DATA 2.8, read by `practice riff` |
| `tags` | [slug] ≤ 12 | no | |
| `moments` | [`{session, at, until, label}`] ≤ 12 | no | never in tracked files (privacy rule) |
| `replay` | `{session, at, seconds, speed}` | `moment` cards | |
| `related` | [id] ≤ 8 | no | |
| `page_reads` | [PageRead] | server | DATA 2.7, recomputed on every write |
| `source` | `{kind: seed\|claude\|saved-live\|saved-from-moment\|kept\|edit, ...}` | server | provenance; `kept` carries `from: {id, rev}` |
| `created_by`, `updated_by` | `claude` \| `daniel` | yes / server | |
| `created_at`, `updated_at` | ISO | server | |
| `favorite`, `archived` | bool | no | |

ChordItem additions to DATA 2.3:

| Field | Type | Meaning |
|---|---|---|
| `upper` | `"same"` | **new.** Loop and Try backing reuse the previous chord's upper voices unchanged, so only the bass moves. For that slot the band voicer skips its no-doubled-bass rule and still runs the round-trip gate; a failed gate is a warning, not a refusal. |
| `name` | string ≤ 24 | Optional author label in the default key ("Abmaj9#11") when the page would read the number differently. Display only. |

Number syntax, key items (`{"key": "6 major"}`, a degree **of the card key**), rests, `beats` (0.5 steps), `notes` (MIDI
21..108, in the default key), `vel`, `arp_ms`, `hold` and `say` are as DATA 2.3. CLI string form:
`"1maj9:4 | [6 major] | 1add9:4 | rest:2"`, with `--notes-for SLOT="Ab2 Eb3 ..."` (slots count from 1).

### 4.2 Resolved definition (`def`: computed, never stored in the card)

`GET .../resolve` returns it, and so does every `jam` frame that starts a run or changes its card. The page never calls the bridge.

```json
{ "api": "arsenal.jam.def/v0",
  "card": {"id": "lament-bass", "rev": 1, "title": "Walking bass under a held chord", "variant": null},
  "key": "Db major", "beats_per_bar": 4, "cycle_beats": 16, "backing": "comp",
  "sections": [{"i": 0, "key": "Db major", "from_beat": 0}],
  "slots": [
    { "i": 0, "section": 0, "at_beat": 0, "beats": 4, "n": "6m11", "name": "Bbm11", "key": "Db major",
      "tones_pc": {"root": 10, "third": 1, "fifth": 5, "seventh": 8, "ninth": 0, "eleventh": 3},
      "bass_pc": 10, "chord_pcs": [10, 1, 5, 8, 0, 3],
      "scale": [10, 0, 1, 3, 5, 6, 8], "scale_name": "Bb Aeolian", "class": "diatonic",
      "voicings": { "play": [46, 58, 68, 72, 73, 75, 77], "full": [46, 56, 60, 61, 63, 65],
                    "comp": [46, 56, 60, 61], "bass": [46] },
      "roles": { "full": ["bass", "seventh", "ninth", "third", "eleventh", "fifth"],
                 "comp": ["bass", "seventh", "ninth", "third"], "bass": ["bass"] },
      "exact": true, "upper_same": false, "vel": 48, "arp_ms": 0, "say": null,
      "page_reads": {"name": "Bbm11", "number": "6m11", "match": "exact"}, "warnings": [] }
  ],
  "warnings": [] }
```

The MIDI numbers are illustrative. Rules:
- `voicings.play` is the chord's exact notes when it has them (shifted per C6), otherwise the card's `voicing.style`.
- `full`, `comp` and `bass` always come from the band voicer, run over the whole line as a ring (MUSIC 4.7). That
  includes chords with exact notes: his exact voicing sits in his own register and is not a bed.
- `chord_pcs` holds the named chord's tones plus the bass pitch class (MUSIC 9.5 T). This is what "in the chord" means
  everywhere: Try `found`, riff classes and v2 marks.
- `scale`, `scale_name` and `class` follow MUSIC 9.5.
- A rest is a gap in `at_beat`. A key item starts a new `sections[]` entry, and the slots after it carry that `key`.
- Cache key: `(id, rev, key, variant, backing, play voicing)`. Resolving a 16-slot card takes ≤ 150 ms cold and ≤ 2 ms warm.

### 4.3 Run (`arsenal.jam.run/v0`, `state/arsenal/jam/runs/<run>/run.json`)

```json
{ "api": "arsenal.jam.run/v0", "run": "20260914-015210-3fa9c1d2", "mode": "loop", "route": "page", "engine": "groove/1",
  "state": "running", "created_at": "2026-09-14T05:52:09.012+00:00", "created_by": "claude",
  "card": {"id": "lydian-four", "rev": 1, "title": "The Lydian 4 chord", "variant": null},
  "card_snapshot": {"...": "the card as it was at start"},
  "key": "Eb major", "beats_per_bar": 4, "count_in_bars": 1,
  "start_epoch_ms": 1789365129812.0, "bar0_epoch_ms": 1789365133448.4,
  "segments": [ {"from_bar": -1, "bpm": 66, "epoch_ms": 1789365129812.0, "def_version": 1, "def_from_bar": 0} ],
  "settings": [ {"from_bar": 0, "groove": "hold", "backing": "comp", "level": 44, "humanize": 0.6, "seed": 90210,
                 "walk": 1, "try_backing": null, "passes": 0, "ending": "cut"} ],
  "last_version": 1, "owner_page_id": "p-7f3a", "courtesy": {"held_ms": 0, "via": "rest"},
  "closed": false, "stopped_epoch_ms": null, "stop_bar": null, "stop_reason": null, "late_dropped": 0 }
```

- `mode` is `play` (once, no count-in), `loop` or `try`. `state` is `pending` (held by the courtesy gate), `running` or
  `stopped`.
- `segments` has DATA 6.3's shape. Bar −1 is the count-in. v2 adds optional `to_bpm` and `to_bar` for ramps (MUSIC 6.1).
- `settings` holds the MUSIC 3.2 fields that exist in v1, keyed by `from_bar`.
- `courtesy.via` is `rest`, `knock` (he took it), `now` (the `--now` flag) or `timeout`.
- `stop_reason` is one of `page`, `cli`, `replaced`, `count`, `stream-lost`, `server-restart`, `device`, `declined`
  (he pressed Not now) or `expired` (a knock nobody took within 60 s).

`events.jsonl` is append-only. It holds DATA 7.2's lines (`start`, `ack`, `change`, `mark`, `stop`), plus `launch`
(a pending run got its epoch) and `change` with `op: "set"` (a settings change). Every line carries `seq`, `kind`,
`recorded_epoch_ms` and `by`.

**Ack** (`POST .../ack`): `{page_id, role: owner|viewer, version, bar, bar_epoch_ms, perf_ms, perf_offset_ms,
output_latency_ms, log: {local, session, t0_perf_ms} | null, stopped: null | "stream-lost" | "device", late_dropped}`.
- Idempotent per `(page_id, version, bar)`.
- The owner acks once per version and again every 16 bars, so a long run keeps a fresh clock pair.

### 4.4 Riff output

Section 11.6.

### 4.5 v2 objects (named now so v1 leaves room for them)

- **Report:** `arsenal.jam.report/v0` at `state/arsenal/jam/reports/<id>.json`:
  `{id, rev, run, card, created_at, lanes, facts[≤3], question, answers[], try_card_id}`.
  Routes: `POST /api/piano/deck/reports` and `.../reports/<id>/answer`.
- **Calibration:** `state/arsenal/jam/calibration.json` (MUSIC 8.2).

---

## 5. HTTP routes (added to `arsenal/serve.py`)

Conventions (DATA 4.1):
- JSON bodies through the existing helpers, with the 2 MB cap.
- The `_cue_post` origin check on every POST.
- `"by": "claude" | "daniel"` on every write.
- Errors: 400 names the field; 404 says `no card <id>` or `no run <id>`; 409 carries the current `rev` or `version`;
  503 only on routes that need node.
- The routes stay on with `--no-performance-log`; alignment then reports `no log`.

### 5.1 Deck

| Method and path | Body | Answer |
|---|---|---|
| `GET /api/piano/deck?group=&kind=&tag=&by=&archived=0` | | `{api, rev, order, cards: [Summary]}`, where Summary is `{id, rev, title, meaning, group, kind, key, numbers, variants, tags, created_by, updated_at, favorite, runs}` |
| `GET /api/piano/deck/cards/<id>` | | `{card}` |
| `GET /api/piano/deck/cards/<id>/resolve?key=&variant=&backing=` | | `{def}` |
| `POST /api/piano/deck/cards` | `{card, by}` | `{id, rev, card, warnings}`; 409 if the id exists |
| `POST /api/piano/deck/cards/<id>/update` | `{patch, if_rev, by}` | a JSON merge patch; `api`, `id`, `rev`, `created_*`, `page_reads` and `source` cannot be patched |
| `POST /api/piano/deck/cards/<id>/delete` | `{if_rev, by}` | `{id, trashed}`: a soft delete into `trash/` |
| `POST /api/piano/deck/cards/<id>/restore` | `{by}` | `{id, rev, card}` |
| `POST /api/piano/deck/cards/<id>/keep` | `{by, key?}` | `{id, rev, card}`: a copy with `group: kept` and `source: {kind: kept, from}` |
| `POST /api/piano/deck/templates` | `{capture, by}` | `{id, rev, card}` (the DATA 2.10 capture) |
| `POST /api/piano/deck/order` | `{order, if_rev, by}` | `{rev}` |
| `POST /api/piano/deck/seed` | `{update, dry_run, by}` | `{installed, updated, kept}` |
| `POST /api/piano/deck/open` | `{card_id, by}` | `{id, listeners}`; publishes `deck {op: "open"}`, and the page opens the drawer on that card (no sound, so no courtesy gate) |
| `GET /api/piano/replay?session=&at=&seconds=&speed=` | | `{cue}` from `pianocue.build_replay_cue` over the log, **never broadcast** (Hear me) |

### 5.2 Jam

| Method and path | Body | Answer |
|---|---|---|
| `GET /api/piano/jam` | | `{run: Run \| null, now_epoch_ms, position: {bar, beat, pass, slot, version} \| null, owner, pages: [{page_id, caps, since}]}` |
| `POST /api/piano/jam/start` | `{mode, card_id \| (chords + key), key?, variant?, slot?, bpm?, backing?, groove?, count_in?, passes?, try_backing?, velocity?, humanize?, seed?, now?, lead_ms?, page_id?, by}` | `{run, version: 1, state, start_epoch_ms \| null, bar0_epoch_ms \| null, def, jam_pages, listeners}` |
| `POST /api/piano/jam/runs/<run>/launch` | `{page_id, epoch_ms}` | `{version, start_epoch_ms, bar0_epoch_ms}` |
| `POST /api/piano/jam/runs/<run>/control` | `{op, bpm?, card_id?, chords?, variant?, key?, settings?, at, if_version?, by}` | `{version, effective_bar, epoch_ms}`; 409 on a stale `if_version` |
| `POST /api/piano/jam/runs/<run>/ack` | Ack (4.3) | `{ok}` |
| `POST /api/piano/jam/owner` | `{page_id, claim}` | `{owner}` |
| `POST /api/piano/jam/mark` | `{text ≤ 200, run?, epoch_ms?, by}` | `{run, seq}` |
| `GET /api/piano/jam/runs?limit=20&card=` | | `{runs: [Run]}`, newest first |
| `GET /api/piano/jam/runs/<run>` | | `{run, events}` |

**`jam/start` fields and behaviour:**
- `count_in`: 0..2 bars; default 1, and 0 for `play`.
- `try_backing`: `ghosts`, `bass` or `loop`; default `bass`.
- `now`: default false, so the courtesy gate applies.
- `lead_ms`: default 250 from the page, 800 from the CLI.
- Starting a run stops the running one at once with reason `replaced`, except a `play`: a play overlays a running loop.
- `by: "claude"` without `now: true` creates the run in state `pending`, with no epochs.

**`launch`:** only the owner page may call it, and only while the run is `pending`. `epoch_ms` must be at least
now + 150 ms.

**`control` ops:** `tempo`, `next`, `stop`, `mute`, `unmute` and `set`. `tempo` also takes a relative `+N` or `-N`.
`at` is `now`, `beat`, `bar` or `pass`.

**Landing rule for `at`** (C3): the change takes effect on the first bar line (or beat, or pass top) at least
`1 beat + 250 ms` after the server receives the request (9.4). `now` releases the run's notes with an 80 ms fade.

Default `at` per op:

| Op | Default `at` |
|---|---|
| `tempo`, `next` (another card), `set` | `bar` |
| `next` with only `key` (a key change) | `pass` |
| `stop` | `bar` (the page's Stop button sends `now`) |
| `mute`, `unmute` | `now` |

**Owner lease** (DATA 6.7):
- A page claims ownership on Daniel's input (pointer, key or MIDI) for 30 s, renewed while the page is visible and in use.
- With no claim, the first page to ack becomes the owner.
- Pages that are not the owner draw the run but stay silent.
- A pending run waits for the owner's `launch`. If there is no owner within 2 s, the first jam page to receive the run
  owns it.

**Stream loss, restart and count** (DATA 6.6, unchanged):
- A page that loses the stream keeps a run for 2 bars, then stops and acks `stream-lost`.
- At startup the server closes unclosed runs with `server-restart` and `approx: true`.
- `passes N` stops the run by itself at the top of a pass.

---

## 6. Events on the existing stream (`/api/piano/cues`)

`cue`, `deck` and `jam` frames share one id sequence and one ring. The `cue` frame keeps its exact bytes, so
`test_frame_bytes_are_exactly_the_protocol` still passes unchanged.

```
id: 42
event: deck
data: {"id":42,"deck":{"op":"upsert","card_id":"lydian-four","rev":2,"deck_rev":18,"by":"daniel","summary":{...}},"sent_at":1789365130100}

id: 43
event: jam
data: {"id":43,"jam":{"op":"start","run":"20260914-015210-3fa9c1d2","mode":"loop","state":"pending","version":1,"by":"claude","effective_bar":-1,"segments":[],"settings":[...],"def":{...},"owner":"p-7f3a"},"sent_at":1789365129012}
```

| Event | Ops | Payload beyond `op` |
|---|---|---|
| `deck` | `upsert`, `delete`, `restore`, `order`, `seed`, `open` | `card_id`, `rev`, `deck_rev`, `by`; `summary` (upsert); `order` (order) |
| `jam` | `start`, `launch`, `change`, `stop`, `owner`, `mark` | `run`, `mode`, `state`, `version`, `by`, `effective_bar`, `epoch_ms`, the full `segments` and `settings`; `def` whenever it changed; `owner`; `text` (mark); `reason` (stop) |

**The hub (`pianocue.py`):**
- `publish(cue)` becomes `publish_event("cue", cue)`.
- `publish_event(kind, payload)` writes `{"id", kind: payload, "sent_at"}` under the same lock and into the same ring.

**Listeners:**
- The page opens `/api/piano/cues?caps=jam1,deck1&page=<page_id>`.
- `subscribe(last_event_id, caps, page_id)` records both.
- `GET /api/piano/cues/status` adds `{"caps": {"jam1": n, "deck1": n}, "pages": [...]}`.

**The page client (`cues.js`):**
- `createCueClient` gains `events: {deck: fn, jam: fn}`, which registers extra listeners on the same EventSource with
  the same `id:sent_at` dedupe.
- `deck` and `jam` frames are **never dropped as stale**: they are idempotent by `rev` or `version`, and their epochs
  place a late frame correctly.

**State is truth:**
- On every EventSource open, the page reads `GET /api/piano/deck` (when its `deck_rev` is older) and `GET /api/piano/jam`.
- A page ignores any `version` at or below the one it already applied.

**Verbs without a jam page:** `pianocue loop start`, `try` and `card play` exit 3.
- Listeners exist but none has `jam1`: "reload the piano page".
- Nobody is listening: the page URL.

---

## 7. CLI verbs (`py -m arsenal.pianocue ...`)

The verbs are implemented in `arsenal/jam/cli.py`. `pianocue.build_parser` gains one call, `jam.cli.add_verbs(sub)`,
and `main` dispatches to `jam.cli.run(args)`. The existing verbs (`play`, `hover`, `progression`, `replay`, `clear`,
`voicing`, `status`) do not change.

**Conventions:**
- Every verb takes `--port` (default 8793). Verbs that write also take `--json` and `--dry-run`.
- `CARD` is an id or a unique id prefix. `CARD|CHORDS` also accepts a chord string in the 4.1 form, which needs `--key`.
- Exit codes: 0 done; 2 bad input (the message names the flag); 3 no jam page (section 6, last rule); 4 no server or an
  old server; 5 conflict (the card or run changed underneath: run it again).
- With no server answering, the `card`, `deck` and `template` verbs write the files directly, and say so.
  `play`, `show`, `loop`, `try` and `jam` need the server.

### 7.1 Cards and the deck

```
card add --title T --meaning M --group moves|try|kept --kind chord|progression|loop|concept|moment --key KEY
         (--chords "1maj9:4 | 4maj7#11:4" | --names "Ebmaj9:4 | Abmaj7#11:4" | --notes "Ab2 Eb3 G3 C4" | --from-json FILE)
         [--id SLUG] [--theory-name T] [--also-in KEY]... [--notes-for SLOT="NOTES"]... [--upper-same SLOT]...
         [--variant "b=pull: 1maj9:4 | 5^7:8"]... [--variant-key b="b7 major"]...
         [--bpm 66] [--beats-per-bar 4] [--bars N] [--voicing spread|close|open|drop2|shell] [--voice-lead]
         [--groove hold|ballad|pulse] [--backing full|comp|bass]
         [--vel 48] [--arp 0] [--hold legato|detached|BEATS] [--style TEXT]
         [--explain T] [--why T] [--try T] [--listen-for T]
         [--check "slot=2 role=#11 want=present say=you touched D"]... [--tag T]...
         [--moment SESSION@m:ss[-m:ss][=label]]... [--replay SESSION@m:ss+SECONDS] [--related ID]...
         [--by claude|daniel]
card list  [--group G] [--kind K] [--tag T] [--by B] [--archived]
card info  CARD [--key KEY] [--variant a|b|all] [--backing full|comp|bass]     # prints the resolved def
card edit  CARD [any add flag] [--add-tag T] [--rm-tag T] [--add-moment M] [--rm-moment N] [--set FIELD=JSON]...
                [--favorite|--unfavorite] [--archive|--unarchive] [--if-rev N]
card rm CARD [--if-rev N] | card restore CARD | card trash
card keep  CARD [--key KEY]                                                    # copy into Kept
card play  CARD|CHORDS [--key] [--variant a|b|all] [--slot N] [--bpm] [--voicing] [--arp MS] [--vel N] [--now]
card show  CARD|CHORDS [--key] [--variant] [--slot N] [--hold SECONDS]          # silent ghosts (a hover cue; not a run)
card open  CARD                                                                # open the deck on it
deck [--group G] [--json] | deck order CARD CARD ... | deck seed [--update] [--dry-run] [--moments FILE]
```

- `card add` and `card edit` print the card resolved in its key: each slot's name, number, the `play` notes, the
  `full` band notes and what the page reads, then any warnings (DATA 8.1 layout).
- `card play` records a run with mode `play`. `--variant all` (the default on concept cards) plays the variants in
  order, one bar of rest between them.
- `deck seed` installs `arsenal/jam/seed/deck-v1.json` and merges `state/arsenal/jam/seed/moments-v1.json` (or
  `--moments FILE`) by card id. `--update` replaces seed cards nobody edited (`source.kind == "seed"` and `rev == 1`).

### 7.2 Loops and Try

```
loop start CARD|CHORDS [--key KEY] [--variant V] [--bpm N] [--groove hold|ballad|pulse] [--backing full|comp|bass]
                       [--count-in 0|1|2] [--passes N] [--humanize 0..1] [--seed N] [--walk 0|1] [--level N] [--now]
loop stop  [--now | --at bar|pass]
loop tempo BPM|+N|-N [--at beat|bar]
loop next  [CARD|CHORDS] [--variant V] [--key KEY] [--at bar|pass]
loop set   [--groove G] [--backing B] [--humanize H] [--walk W] [--level N] [--at bar]
loop mute | loop unmute
try CARD|CHORDS [--key KEY] [--variant V] [--bpm N] [--count-in 0|1|2] [--backing ghosts|bass|loop] [--passes N] [--now]
```

- `try` defaults: `--passes 2`, `--backing bass`, count-in 1.
- `loop next` with no card steps to the next variant on a concept card, and otherwise to the next card in deck order.

```
$ py -m arsenal.pianocue loop start lament-bass --bpm 60
run 20260914-020114-77a0c3e5: loop "Walking bass under a held chord" in Db major, 60 bpm, 4 bars, hold/comp, until stopped
  bar 1  Bbm11     6m11    comp Bb1 Ab3 C4 Db4     page reads Bbm11
  bar 2  Bbm11/Ab  6m11/5  comp Ab1 Ab3 C4 Db4     (upper same)
  ...
waiting for Daniel's pause on 1 jam page (owner p-7f3a); --now skips the wait
```

### 7.3 Runs and templates

```
jam status [--json] [--runs 5]            # pages, owner, the running run, bar/beat/pass/slot, pending changes, deck rev
jam runs   [--limit 20] [--card CARD] [--json]
jam mark   TEXT
template save-from-moment SESSION|latest AT [--until m:ss] [--title T] [--key auto|KEY] [--beats 4] [--id SLUG] [--dry-run] [--json]
template save-last [--title T] [--dry-run]
```

The template rules are DATA 2.10: the notes heard for ≥ 0.5 of the window, lowest-bass trim, at most 16 notes,
`created_by: daniel`, `source.saved_by: claude`, `group: kept`.

**v2 verbs:** `jam wait` (block until Daniel presses Ask Claude; run as a harness-tracked background task),
`jam calibrate`, `loop export --mid DIR`, `report publish RUN`.

**Riff analysis** is a practice verb: section 11.1.

---

## 8. Page components and placement

### 8.1 Where things sit

| Component | Element / module | Placement | Recorded? |
|---|---|---|---|
| Deck drawer | `<aside id="deck">` inside `.stage`, from `deck.js` | UX 2.1: `right: 0`, 380 px wide, z-index 3. It overlays when `(stage width - canvas CSS width) / 2 ≥ 392 px`; otherwise it docks and `fitCanvas()` subtracts 380 px. The layout never reflows while REC runs: it overlays, with a peek button that slides it to a 44 px rail | no |
| Closed tab | inside `#deck` | 28 x 120 px on the stage's right edge, vertically centred; `CARDS` rotated, with an unseen-count badge | no |
| Now header | the top of `#deck` | 96 px, 132 px during a run (UX 5.2 layout: kind, card, key, bpm, Stop; NOW and NEXT chord with number; beat pips, bar, pass; Claude volume and duck) | no |
| Pill | `<div id="jam-pill">` inside `.stage` | 44 px tall. In 9:16: centred on the canvas box, 14 px above its bottom edge. In 16:9: at the canvas box's bottom-right corner. It moves into the letterbox when that is ≥ 56 px. Shown when the deck is closed and a run, Show or knock is active; `H` never hides it | no |
| Glass | `<canvas id="jam-glass">` in `.stage`, directly after the WebGL canvas | the canvas's exact CSS box, DPR-scaled, `pointer-events: none`, z-index 2 (HUD 3, toast 4) | no |
| Cue chip (INT section 5) | the WebGL overlay layer | INT's boxes (9:16 top band y 28-144; 16:9 x 50-950, y 464-568) while jam view puts Claude on the stage; drawn on the glass at the same projected box otherwise | only in `auto` outside REC |
| Claude's keys and ghost rims | the 3D keys (INT section 4 meshes) or the glass | per jam view (8.6) | only in `auto` outside REC |
| Toast | the existing `#toast` | `right: 392px` while the deck is open | no |

### 8.2 Modules and their interfaces

```js
// arsenal/web/piano/transport.js
export function createTransport({ player, voice, api, pageId, now = () => performance.now(), wallNow = () => Date.now(),
  log = null /* {timebase()} */, isResting /* () => bool, 8.9 */, onPosition /* ({run, bar, beat, pass, slot, next}) */,
  onGhosts /* ({target, incoming, hold, found}) */, onState /* ({state, run, pending, knock}) */ }) -> {
  apply(jamFrame), start(opts), control(op, args), stop(at = "now"), takeKnock(), declineKnock(),
  claimOwner(), state(), stats() /* lateness, dropped, bars handed, ack count */, dispose() }

// arsenal/web/piano/deck.js
export function createDeck({ root, stage, api, transport, glass, cueClient, keyView /* tracker key, locked */,
  isRecording, onOpenChange }) -> { open(cardId?), close(), toggle(), select(delta), act(action), applyDeckFrame(f),
  refresh(), layout() /* overlay | dock, width */, stats() }

// arsenal/web/piano/glass.js
export function createGlass({ canvas, projectKeyTop /* midi -> 4 corners in CSS px */ }) -> {
  resize(cssRect, dpr), draw({ ghosts, claude, chip }), clear(), layout() /* rects for receipts */ }
```

`groove.js` (section 10) and `tempomap.js` (section 9.1) are pure and have no DOM.

### 8.3 The card

**Collapsed (88 px):**
- the title and a group tag (NEW / updated / YOUR MOVE / TRY THIS / KEPT);
- the meaning line;
- the chord line in letters and numbers (numbers with superscript suffixes);
- the key and bpm on the right.

**Expanded** (one at a time, accordion; UX 4.1):

| Element | Content and behaviour |
|---|---|
| Title, meaning, theory name | as the card |
| Chord chips | one per slot: the name in the shown key, the number, the length in beats. Hover 250 ms: ghosts of that chord, silent, while the pointer stays. Click: hear it (a one-slot Play). Shift-click: Show it (ghosts held). Key-change items draw a small "in D major" divider |
| Reads-as line | "your screen calls this Bb13/Ab: the same notes" whenever `page_reads.match` is neither `exact` nor `enharmonic` |
| Key selector | as written / my key now (the tracker's key, followed live) / his keys (`also_in`, then Eb F D Gb Db) / all 12. Chips and the Now header format numbers through the page's own
`nashville()` call, with the page's Minor-keys setting (tonic or relative major). Chips, the Nashville row and the pill
therefore always agree. Card JSON and the CLI store tonic numbering. A change asks `resolve?key=`; until the answer comes, chips show names transposed by the nearest shift in grey. A one-time hint: `numbers stay the same in every key` |
| Tempo | `[-] 66 [+]` (steps of 2, hold to repeat), `tap` (four taps, median interval, 40-200 bpm), bars and meter |
| Actions | `[Play] [Show] [Loop] [Try] [Hear me at <label>]`; buttons `blur()` after a click |
| Explanation, why, try, listen for | collapsible "About this" |
| Footer | `[Keep]`, the Loop settings (groove, backing) and `[...]` (edit title, meaning and tags on Kept cards) |

### 8.4 Actions (v1)

| Action | Run | Sound | Keys | Label and number row | Ends |
|---|---|---|---|---|---|
| Play | `mode: play` | the `play` voicings, once, at the card tempo | Claude's hand | the cue chip names Claude's chord (`CLAUDE · Abmaj7#11`, detail `4maj7#11 in Eb major`); the big label stays Daniel's | after the last chord's hold |
| Show | none (a local hover, `hold_ms: 0`) | none | ghosts (target) of the selected chip or the first chord | the Now header reads `SHOWING Abmaj7#11 · 4maj7#11 [Dismiss]` | `K`, Dismiss, Stop, or another Show |
| Loop | `mode: loop` | count-in, then groove + backing | Claude's hand | the chip names the NOW chord; the Nashville row counts from the section key (8.10) | Stop, `\`, or another Loop (a swap on the next bar) |
| Try | `mode: try` | count-in, then `try_backing` | ghosts: target for the current chord, incoming on the last beat, hold rims on shared pitch classes for the last beat and the first beat after the change | the Now header shows `found` for 600 ms when he lands a chord | Stop, `'`, or after `passes` |
| Hear me | none (`GET /api/piano/replay`, then played locally with `source: replay`) | his logged notes at 1x | his pitch colours at 55% saturation, no sparks | the chip reads `YOU · <label>` | the end of the moment |

- Clicks unlock Claude's voice (`unlock()`) before playing.
- Starting a run while the Demo is running stops the Demo first, with a toast.
- **Try `found`:** every pitch class of `chord_pcs` is sounding in Daniel's `sounding` map for 150 ms, in any voicing.
  The natural 5th is optional when the bridge's `omits` lists it. The bass pitch class is required only for slash chords.

### 8.5 How notes look

| Who | Look |
|---|---|
| Daniel, live | unchanged |
| Claude's hand (C12) | Ivory or black key surface, never pitch-tinted. Emissive moonlight `#C8DCFF` following the strike envelope, capped at 0.75 of Daniel's glow for the same velocity. Pressed to 60% of `cueDepth`. No trails, bursts or spill lights. A key held by both: Daniel's colour wins, and a thin moonlight rim shows Claude holds it too |
| Ghost, target | INT's frame mesh with opacity 0.55 (0.7 on black keys) under the bloom threshold, plus a 10% fill breathing 0.92-1.00 at 0.5 Hz |
| Ghost, incoming | opacity 0.35 with no fill; on the glass, a dashed rim (dash 0.12 u, gap 0.08 u) |
| Ghost, hold | a second inner rim |
| Found | every rim pulses once in size (1.0 → 1.15 → 1.0 over 200 ms), never in brightness |
| Daniel, replayed | his pitch colour at 55% saturation, 70% glow, trails at half gain, no sparks |

Rules:
- On the glass, each ghosted key's rest-pose top face is projected every frame (at most 24 keys) and stroked with the
  same rules.
- Claude's pressed keys on the glass are moonlight quads at 38% fill with an 80% rim.
- Ghost labels are v2.
- Claude's and replayed notes never reach `sounding`, the log, the key tracker, rarity, or the light budget's
  fresh-strike protection (INT invariant 1).

### 8.6 Jam view (v1: `auto` and `glass`)

| Thing | `auto`, not recording | `auto`, recording | `glass` |
|---|---|---|---|
| Claude's hand on the keys | 3D keys | glass quads | glass quads |
| Ghost rims | 3D | glass | glass |
| Cue chip | canvas layer | glass | glass |
| Strip | DOM (Now header / pill) | DOM | DOM |
| Claude's sound | speakers | speakers, **never connected to the recorder's audio track** | speakers, never connected |
| Label, numbers, staff, log, rarity | Daniel's only | Daniel's only | Daniel's only |

- REC start in `auto` crossfades Claude's things from the stage to the glass over 250 ms, and shows the toast
  `Recording you only. Claude's keys stay on the glass.` REC stop crossfades them back.
- If Chrome's output device is also captured by the interface Loopback, Claude's sound reaches that input no matter
  what the page does. The deck settings say this next to Claude's volume (INT section 8).

### 8.7 Keyboard shortcuts

These use keys that neither `KEYMAP` nor the page already takes (UX 3.5, checked against `piano.js` tonight: KeyA,
KeyK, Backslash, Quote, Minus, Equal and the brackets are free).

| Key | Action |
|---|---|
| `A` | open or close the deck |
| `↑` `↓` | select the previous or next card |
| `Enter` | Play the selected card, or take a knock when one is showing |
| `K` | Show or hide the selected card's ghosts |
| `\` | Loop on or off |
| `'` | Try |
| `Shift` + `Enter` | Hear me |
| `-` `=` | transpose the selected card a half step |
| `[` `]` | tempo -4 / +4 bpm (lands on the next bar in a run) |
| `Esc` or `Backspace` | **Stop Claude**: stop the run now, dismiss ghosts, `cuePlayer.clear()` |

- `Space` stays the sustain pedal.
- `e.repeat` never re-triggers an action.
- The existing guards stay: Ctrl, Meta or Alt, or an INPUT, SELECT or TEXTAREA target, skip the handler.

### 8.8 Settings (the deck's `[...]` menu; `safeGet`/`safeSet`)

| Setting | Values | Default | localStorage key |
|---|---|---|---|
| Jam view | auto / glass | auto | `arsenal.piano.jam.view` |
| Claude volume | 0-1 | 0.7 | `arsenal.piano.cueVolume` (INT's key, shared) |
| Duck Claude when I play | on / off | on (Loop and Try only) | `arsenal.piano.jam.duck` |
| Loop groove, backing | per card, or override | card | `arsenal.piano.jam.groove`, `.backing` |
| Try backing | ghosts / bass / loop | bass | `arsenal.piano.jam.tryBacking` |
| Count-in | 0 / 1 / 2 bars | 1 | `arsenal.piano.jam.countIn` |
| Let Claude knock while I play | on / off | on | `arsenal.piano.jam.knock` |
| Deck tab, seen ids | | | `arsenal.piano.deck.tab`, `arsenal.piano.deck.seen` (capped at 500) |

Query overrides for receipts, never stored: `?jam=auto|glass`, `?deck=open`, `?card=<id>`.

### 8.9 The courtesy gate

**Rest:** 1.2 s with none of Daniel's notes sounding, or 3.0 s with no note-on while only pedal-held notes ring.

| Remote action (`by: claude`, no `now`) | He is resting | He is playing |
|---|---|---|
| A `jam start` (play, loop, try) that arrives `pending` | the owner calls `launch` at once | waits up to 20 s for a rest, then launches. If no rest comes, a **knock** shows in the Now header and pill: `Claude has a Loop for you: The Lydian 4 chord [Hear ⏎] [Not now]`, with a dot pulsing in size |
| A hover cue (`card show`) | appears with a 400 ms fade | waits up to 8 s, then fades in anyway |
| `deck open` | the drawer opens | the badge ticks; the drawer opens at the next rest |
| `clear`, `loop stop` | at once | at once |

- A knock expires after 60 s: the run stops with `expired`, and the card is marked in Tonight.
- `Not now` stops the run with `declined`.
- When Claude knocks while he is playing, the gate does not block his own clicks: they launch at once.
- Today's direct cues (`pianocue play`, `progression`) keep their current behaviour in v1. They reach the player
  without the gate, because they predate it and carry no `pending` state.

### 8.10 The jam key

While a run is active, and for 2 s after it ends, the page locks the key tracker's display key to the running
section's key. The top bar's Key select shows `jam: E♭`, unless Daniel locked a key by hand, which always wins. The
previous state comes back afterwards.

### 8.11 Integration points in `piano.js`

These are wired by the integration phase only (J9 in 13.2).

1. **Imports:** `createTransport`, `createDeck`, `createGlass`.
2. **Voice:** construct `createClaudeVoice` with the polyphony option. The transport raises it to 40 during a run.
3. **`cueNoteOn` / `cueNoteOff` (C12):** the moonlight look; no `trails.start`, `burst`, or `noteColor` tint.
4. **`updateKeys`:** ghost states (target, incoming, hold, found) driven by `transport.onGhosts` and deck hovers.
5. **The overlay's cue layer and the 3D Claude look:** gated by `jamView.onStage()`, which is
   `view === "auto" && rec.state !== "recording"`.
6. **`renderFrame`:** after `cuePlayer.pump()`, call `transport.tick(t)` and `glass.draw(...)`, the glass only while it
   has content.
7. **`fitCanvas`:** subtract `deck.layout().dockWidth`, frozen while recording.
8. **The recorder:** assert that no Claude audio node is connected to the recording stream.
9. **Keydown:** the 8.7 keys, before the `KEYMAP` lookup.
10. **`noteOn`:** notify `transport` (duck, rest detection) and claim the owner lease.
11. **`midiRank` / `bindMidi`:** the echo guard (INT section 8) if it has not already landed.
12. **`window.__piano.jam`:** `{ deck, transport, glass, view, stats() }` for receipts.
13. **`boot()`:** start the deck after `startCues()`. The cue client carries `caps=jam1,deck1&page=<pageId>` and
    `events: {deck, jam}`.

---

## 9. Transport, timing and sound

### 9.1 The tempo map (`tempomap.js` and `arsenal/jam/tempomap.py`, one shared fixture)

A run's `segments` are `[{from_bar, bpm, epoch_ms, def_version, def_from_bar}]` in the meter `m = beats_per_bar`.

```
barMs(s)         = m * 60000 / s.bpm
t_epoch(bar)     = s.epoch_ms + (bar - s.from_bar) * barMs(s)              s = the last segment with s.from_bar <= bar
beat position x  = t_epoch(bar) + x * 60000 / s.bpm
new segment at B = { from_bar: B, bpm: new, epoch_ms: t_epoch(B) under the old segment }   (float, never re-rounded)
pass(bar)        = floor((bar - s.def_from_bar) * m / def.cycle_beats)
cycle_beat       = ((bar - s.def_from_bar) * m + x) mod def.cycle_beats;  slot = the last slot with at_beat <= cycle_beat
```

Rules:
- Epochs are computed from the stored previous segment, so error never builds up.
- v2 ramps use MUSIC 6.1's logarithmic formula.

**Page time:** `perf(epoch) = epoch - offset`.
- `offset = Date.now() - performance.now()` is taken as the median of 5 paired reads when the run is applied, then
  re-measured every bar.
- A change of more than 2 ms between bars (a system clock step) is **not** applied mid-run. Page time keeps the first
  offset, so bar lines never jump; the ack reports `offset_step_ms`.

**Session time:** `t_ms(bar) = perf_ms(bar) - log.t0_perf_ms` (L1/L2). Section 11.2 gives the ladder.

### 9.2 Start

1. The run arrives (`jam start`). If it is `pending` and this page is the owner, the courtesy gate (8.9) decides the
   `launch` epoch.
2. Otherwise the start is `start_epoch_ms`, which the server set to now + `lead_ms`.
3. Bar −1 (when `count_in` is 1) begins at `start_epoch_ms`, and bar 0 at `start + count_in * barMs`.
4. A `play` run has no count-in: bar 0 is the start.

### 9.3 Handing bars to the player

- At `H(n) = t(n) - (60000/bpm + 150 ms)`, the transport calls `groove.bar(def, settings(n), pass(n), n)`. That returns
  bar n's events, including its pickups on the previous bar's last beat.
- The events become one local `sequence` cue: `source: "claude"`, label = the NOW chord name, detail = number + key, and
  one `play` step per note (`at_ms` relative to the earliest event, `velocity`, `hold_ms`).
- The cue goes to `player.handle(cue, { id: "jam:<run>:<version>:<n>", at: perf(t_event0) })`.

Required `cues.js` changes (the player and voice API):

| Change | Contract |
|---|---|
| `handle(cue, {id, at})` | `at` given: the base is `at` instead of `now() + startDelayMs`. An `at` more than 20 ms in the past drops the steps already late (counted in `late_dropped`), except a downbeat bass up to 40 ms late |
| `extend(id, stepIndex, offAt)` | moves a planned or sounding note's release; returns false if already released |
| `cancel(id)` | removes a cue's actions not yet started; notes already sounding release with an 80 ms fade |
| `voice.tick({at, freq, velocity})` | a 20 ms sine tick; never sent to MIDI |
| `createClaudeVoice({polyphony})` + `setPolyphony(n)` | 24 by default, 40 during a run |
| `voice.setDuck(on)` | 9.5 |
| `voice.timbre("keys")` | 9.6 |
| the fitted clock | 9.7 |

**Ties:** a note marked `tie: "next"` is handed with its release at the next downbeat + 30 ms. When bar n+1 is handed
and continues the note, the transport calls `extend` and skips the strike. When a change or stop lands there instead,
nothing is needed.

### 9.4 Changes on bar lines

- The server accepts a change for bar B only if `t_epoch(B) - now ≥ 1 beat + 250 ms`. Otherwise it moves to the next
  line (bar, beat or pass per `at`).
- The page hands bar B at 1 beat + 150 ms before it. A frame therefore has 100 ms to arrive before its bar is handed.
- **If a frame still arrives after bar B was handed:** the transport calls `cancel("jam:<run>:<old version>:B")`
  (nothing in it has sounded: its earliest pickup is 1 beat before B, 150 ms after the hand-off) and regenerates B
  under the new version. It acks `late_frame_ms`.
- Stop `now`: `cancel` every handed bar of the run, release sounding run notes with an 80 ms fade, ack `stop_bar`.
- Swap (Loop on another card): the old run stops at bar B with `replaced`. The new run's segment starts at B with no
  count-in, because the clock continues.

### 9.5 Duck (C9)

Loop and Try only, never Play, and only when "Duck Claude when I play" is on:
- **Attack:** Claude's master gain goes to 0.7 (−3 dB) over 80 ms on each of Daniel's note-ons.
- **Hold:** it stays there until 1.2 s after his last note-on.
- **Release:** it returns with a 0.6 s time constant.

### 9.6 Sound

**The `keys` timbre** (MUSIC 7.2) is the backing preset of today's voice:
- the sawtooth partial's gain × 0.6;
- lowpass `min(6000, f(2 + 7v²) + 200 + 1200v²)`;
- notes below E2 (40) play sine partials only.

**Base velocity** is L = 44. Groove offsets: hold −2, ballad 0, pulse −4. Count-in ticks: velocity 60, 2 kHz on beat 1,
1.5 kHz on the others. A Play run keeps the card's `playback.velocity` (default 48) and today's voice.

### 9.7 Staying on time (MUSIC 6.4)

- **Fitted clock:** the voice maps `at` to the audio clock through a least-squares line over (performance time,
  `getOutputTimestamp`) pairs from the last 10 s, sampled at each worker wake. It re-seeds when a new pair lands more
  than 5 ms off the line. `outputLatency` is not added on top.
- **Worker timer:** it wakes at each `H(n)`, and every 100 ms for beat pips and position. Every time is computed from
  the tempo map.
- **Device change:** an AudioContext leaving `running` stops the run with `device`.
- **Lateness:** the rule in 9.3 applies. The drop count is shown in the HUD row and recorded in the ack and `run.json`.

---

## 10. Accompaniment

### 10.1 The band voicer (`band` style in `pianocue_voicing.mjs`)

MUSIC 4.1-4.8 is adopted with its numbers:

| Rule | Value |
|---|---|
| Bass register | E1-D3 (28-50), preferring C2-B2 |
| Upper voices, `full` | D3 to G4 (hard A4); 4 voices (pulse uses the 3rd or sus, the 7th or 6th, and the top colour) |
| Upper voices, `comp` | C3-B3; the defining altered colour (b9, #9, #11, b13, b5, #5) may reach E4; 2-3 voices, or 4 over a foreign bass |
| `bass` | the bass note only |
| Required tones | the 3rd or sus; the 7th or 6th; the defining altered colour; named 9/11/13 in `full` only; the root in the upper voices over a slash bass; the natural 5th only when the gate needs it |
| Never | the bass pitch class doubled in the upper voices (except the root of a root-position chord with fewer than 3 upper voices, and slots with `upper: "same"`) |
| Low-interval limits | MUSIC 4.4 table (m2 ≥ E3, M2 ≥ Eb3, m3 ≥ C3, M3/P4 ≥ Bb2, TT ≥ B2, P5 ≥ Bb1, m6-M7 ≥ F2, m9 ≥ E2, M9 ≥ Eb2) |
| Candidates | MUSIC 4.3: up to 120 orderings × octave choices, filtered (hard top, limits, span ≤ 24, no minor 9ths unless named, top two voices not a minor 2nd), best 40 by static cost |
| Costs | static S and move T exactly as MUSIC 4.5 and 4.6 |
| Line | Loop and Try: the ring (MUSIC 4.7) with the wrap move; Play: an open chain |
| Gate | `full` candidates must read back `exact` or `enharmonic`; otherwise add the omitted optional tones one at a time; otherwise keep the best shape and set `reads_as` with a warning (MUSIC 4.8). `comp` and `bass` are not gated |
| Determinism | ties go to the lower total S, then the lower MIDI list; the same request gives byte-identical JSON |

**Amendment** (`upper: "same"`, C8): for such a slot the candidate set is exactly the previous slot's chosen upper
shape. Only the bass is chosen, from the bass register nearest the written bass pitch class under the limits. The ring
treats the run of same-upper slots as one chord for the T cost, so the first slot of the run is optimised against its
neighbours and the rest follow. The round-trip gate for the shared shape runs over **every** slot of the run with its
own bass. A candidate survives only if all of them read `exact` or `enharmonic`. This is what keeps the F in the
lament's upper voices: without it, Bbm11/Gb reads Ab11/Gb (MUSIC 1.3).

**Output additions to each result:** `band: {full: {notes, roles}, comp: {...}, bass: {...}}`,
`tones_pc: {role: pc}` and `bass_pc`.

### 10.2 The groove generator (`groove.js`, pure)

```
bar(def, settings, pass, barIndex) -> [{ beat, midi, vel, len, role, voice: "bass"|"upper"|"tick", tie, ms }]
```

Shared rules, MUSIC 5.1, for v1:
- **Ties.** A note sounding to the end of its chord ties into the next chord when that chord voices the same MIDI note
  in the same voice group. The strike is skipped and `extend` is used.
- **Gate.** "To chord end" means release 0.03 beat before the next chord, unless the note ties.
- **Humanising** (h = `humanize`, default 0.6; 0 for receipts):
  - The random source is mulberry32, seeded with FNV-1a-32 of `"${seed}:${pass}:${bar}:${voiceIndex}"`; normal draws
    use Box-Muller.
  - Timing: upper voices N(0, 5h ms), bass N(0, 2.5h ms), both clamped to ±12h ms. A downbeat bass is never earlier
    than −4 ms.
  - Roll: hold U(4,9)·h ms per voice, ballad U(8,14)·h ms, pulse none.
  - Velocity: `L + table offset + round(N(0, 2.5h)) + breath + arc`, with MUSIC's breath random walk (±4) and loop arc
    `round(3h·sin(π(k+0.5)/B))`. Passes 1-2 get −2. The top voice never exceeds L+2 unless the table says so.
  - Length × (1 + U(−0.03, 0.03)·h).
- **Feel.** v1 is straight only: the offbeat eighth is at 0.5.
- **Bass approach** (`walk`: 0 or 1, default 1), from bass b to the next bass nb, with d = nb − b:
  - |d| ≤ 2: none.
  - |d| 3-4: the key-scale note between them nearest the middle (the lower of two), else the chromatic middle.
  - |d| ≥ 5: a half step below nb (above if that would be below E1).
  - The approach sits on beat 4 of the chord's last bar.
- **Written lines:** `upper: "same"` slots tie their upper voices, so only the bass walks (the lament).

### 10.3 `hold` (held voicings)

| At (beat) | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass | L+2 | to chord end (ties if the next bass is the same note) |
| 0 | upper, rolled | L−4, top voice L | to chord end; tied notes carry |
| 2 | upper voices that are not tied (chord ≥ 4 beats and beat ≥ 0.6 s) | L−12 | to chord end (the soft breath re-strike) |
| 3 | approach bass (walk 1, next bass differs) | L−6 | 0.9 |

A 2-beat chord uses the beat-0 rows only.

### 10.4 `ballad`

| At | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass | L+4 | 1.9 (0.95 before a beat-4 approach) |
| 0 | upper, rolled | L−2, top voice L+2 | 1.95 |
| 2 | second bass: the natural 5th nearest the first bass (the chord has one, is in root position, and the note is in range); else the root again | L−2 | 1.9 (0.95 before an approach) |
| 2 | inner upper voices (all but the top) | L−10 | 1.95 |
| 3 | approach bass | L−6 | 0.9 |

- A 2-beat chord uses the beat-0 rows plus an approach on beat 1.
- Meter 3 (waltz): the bass and upper voices on beat 0, and the inner upper voices at L−10 for 0.8 beat on beats 1 and 2.

### 10.5 `pulse` (3 upper voices: the 3rd or sus, the 7th or 6th, the top colour)

| At | Who | Velocity | Length |
|---|---|---|---|
| every eighth, 0 &0 1 &1 2 &2 3 &3 | upper | L−4 + accent, accents [+6, −6, −2, −6, +3, −6, −2, −4] | 0.28 beat |
| 0 | bass | L+2 | 1.9 |
| 2 | bass (root) | L | 1.9 (0.95 before an approach) |
| 3 | approach bass | L−6 | 0.9 |

Meter 3 has 6 eighths, with accents [+6, −6, −2, −6, +2, −6]. v1 has no push.

### 10.6 Backings, Try backings and Play

| Setting | Notes used |
|---|---|
| `full` | `voicings.full` |
| `comp` | `voicings.comp` (pulse runs over the voices that exist) |
| `bass` | the groove's bass rows only, approaches included |
| Try `ghosts` | no notes; a soft tick (velocity 40, 1.5 kHz) on every beat, so time stays audible |
| Try `bass` | the bass on each chord's beat 0 at L+2, held to chord end, plus approaches |
| Try `loop` | the card's Loop groove and backing |
| Play (`mode: play`) | `voicings.play` per slot at the slot's time, `arp_ms` rolled, `vel`; hold `legato` = to the next chord + 80 ms, `detached` = length − 40 ms, a number = beats |

**Meters in v1:**
- meter 4: all three grooves;
- meter 3: hold, ballad (waltz) and pulse;
- meters 2, 5, 6 and 7: `hold` only (the others fall back to it, with a warning at start).

**v2 grooves** follow MUSIC 5.3 (`swell`), 5.6 (`arp`), 5.7 (`gospel`), 5.10 (call and response) and 5.11 as written,
together with feel and swing, push, spice, `bass_mode: pedal` and `ending: home`.

---

## 11. Riff analysis (`arsenal/practice_riff.py`, verb `py -m arsenal.practice riff`, read only)

### 11.1 Invocation

```
py -m arsenal.practice riff [RUN|latest] [--session SESSION] [--root DIR] [--jam-root DIR]
                            [--card CARD --key KEY --bpm N --from m:ss [--to m:ss]]
                            [--bars A-B] [--pass N] [--json] [--out FILE] [--save]
```

| Form | What it analyses |
|---|---|
| `riff RUN` or `riff latest` | The run's def versions, segments and settings. The latest run means mode `loop` or `try`, stopped, and overlapping a session. `--session` picks one when several sessions overlap |
| `riff --session S` | Every loop or try run overlapping S, one block per run. With none, **free play** (11.7) |
| `riff --card C --key K --bpm N --from m:ss` | He played along with a card that had no run. The grid starts at `--from`; alignment is `assumed` |

- `--save` writes `state/arsenal/jam/riffs/<run>.json`.
- Nothing writes to the practice log.
- Runtime: at most 3 s for a 30-minute session with 4 runs.

### 11.2 Alignment (DATA 7.3)

| Level | When | Bar-line session time | Error |
|---|---|---|---|
| L1 | an ack's `log.session` is the session | `ack.perf_ms(bar) − ack.log.t0_perf_ms`, extended by the tempo map | ≤ 2 ms |
| L2 | the session's `meta.page_id` equals an ack's `page_id` | `perf_ms(bar) − meta.t0_perf_ms` | ≤ 2 ms |
| L3 | `meta.opened_at_client` exists | `bar_epoch_ms − epoch(opened_at_client)` | ±50 ms |
| L4 | nothing better; the session was not buffered | `bar_epoch_ms − epoch(opened_at)` | ±150 ms; **refused** for `meta.buffered: true` |

- Which chord a note is heard against, and every class, is reported at every level.
- Landings and anticipations are reported at L1-L3. At L4 they carry `approx: true`.
- Beat placement is v2 and needs L1/L2 plus a calibration.

### 11.3 Pipeline

1. **Loop timeline.** Expand segments, settings and def versions into slot instances `[t_start, t_end)` in session
   `t_ms`, each with `pass`, `bar`, the slot and its chord facts from `def`.
2. **His notes.** `practice.sounding(events)["notes"]`.
   - **Attacks:** note-ons grouped within `ONSET_GROUP_MS` = 50.
   - **Top line:** the highest note of each attack, at C4 (60) or above. With backing `full`, the threshold is the
     backing's top voice + 1 (at most A4 + 1 = 70).
   - **Length** of a top-line note: until the next top-line onset or its `sound_end`, whichever comes first, capped at
     2 beats. The pedal never stretches it.
3. **Grid and weight.** Beat position b within the bar comes from the tempo map, with phase p = b − floor(b).
   - **Grid class** with TOL = 0.08 beat: `beat` (p near 0 or 1), `offbeat` (near 0.5), `triplet` (1/3, 2/3),
     `sixteenth` (0.25, 0.75), else `free`.
   - **Metric weight w_m:** beat 1 = 1.0; beat 3 in meter 4 = 0.8; other beats 0.6; offbeat 0.4; the rest 0.3.
   - **Note weight:** w = w_m × clamp(length in beats, 0.25, 2).
4. **Which chord** (MUSIC 9.4). Normally the slot sounding at the onset. The note is judged against the next slot,
   flagged `anticipates`, when all three hold:
   - the change is at most min(0.5 beat, 300 ms) away;
   - the pitch class is in the next slot's `chord_pcs`;
   - it is not in the current slot's.
5. **Class**, relative to the slot's `chord_pcs`, `scale` and root (first match wins):

   | # | Class | Rule | Word Daniel sees |
   |---|---|---|---|
   | 1 | chord tone | pc ∈ `chord_pcs` | in the chord |
   | 2 | colour | pc ∈ `scale`, not a rub | colour |
   | 3 | passing | a rub shorter than 1 beat, w_m < 0.6, that steps (≤ 2 semitones) to a chord tone or colour within 0.5 beat | colour |
   | 4 | rub | a scale note, not a chord tone, a half step above a chord tone. Exceptions: b9 and b13 are colours on dominant chords; the major 3rd is a rub on sus chords | rub |
   | 5 | slide-in | not in `scale`, length ≤ min(0.5 beat, 300 ms), and the next top-line note within 1 beat is 1 semitone away and a chord tone or colour; noted `from below` or `from above` | outside |
   | 6 | outside | everything else; noted `in the key, not this chord` when pc is in the section key's scale | outside |

   **Labels.**
   - Chord tones: `R`, `b3`, `3`, `4` (sus), `b5`, `5`, `#5`, `6`, `b7`, `7`.
   - Colours, by interval from the root: 1 `b9`, 2 `9`, 3 `#9`, 5 `11`, 6 `#11`, 8 `b13`, 9 `13`.
   - Every note also carries `bass_label`, the interval from the bass, because slash chords are heard both ways.
6. **Scale and mode per slot** (MUSIC 9.7). Only for a slot with at least 12 top-line notes across the run.
   - Build a weighted interval histogram from the slot root and score the MUSIC 9.7 candidates with
     `coverage − 0.04·(size − 5) − 0.05·(degrees under 0.02 share)`. Report the best, the runner-up and the margin.
   - **Naming gate:** a mode is named only when its own note carries at least 5% of the weight (Lydian #4; Mixolydian
     b7; Dorian 6 with b3; Aeolian b6 with b3; Phrygian b2; Locrian b5 with b3; Lydian dominant #4 and b7; altered b9
     or #9, plus b13).
   - A pentatonic is named only when all 5 degrees are used and the 4th and 7th together carry ≤ 3%.
   - Otherwise the report says "the notes of <section key>".
7. **Landings.** His first top-line onset in `[t_start − min(0.5 beat, 300 ms), t_start + 250 ms]`, with its class and label.
8. **Top-note degrees by bar.**
   - For each (pass, bar): the label of the top-line note with the most weight.
   - `most_played[bar]`: the label that wins that bar in the most passes; ties go to the higher summed weight.
9. **His own reading.** One batched `practice_theory.mjs` call runs `Theory.detect` over his notes per slot instance.
   A root or bass that differs from the loop's is a `reharmonized` entry ("over 4maj7#11 you played 2m9/4").
10. **Per pass:**
    - top-line range;
    - velocity median and p90 over all his note-ons;
    - weight shares in the chord, colour and outside;
    - rests (bars with no onset of his);
    - pedal share (the practice verbs' pedal spans intersected with the pass);
    - onsets per bar;
    - at most one picking fact per pass, the first that applies in this order: the widest range, the highest p90
      velocity, the most colour weight, the first pass with a new colour label.
11. **Phrases** (MUSIC 9.9). A top-line gap of at least max(1 beat, 600 ms) ends a phrase; a phrase over 4 bars splits
    at its longest inner gap of 0.5 beat or more.
    - Per phrase: start (pass, bar, beat, m:ss), bars rounded to 0.5, pickup, range, landing class and label.
    - Contour: `rising` (ends ≥ 3 semitones above its start, peak in the last third), `falling`, `arch` (peak in the
      middle third, both ends ≥ 3 below it), `valley`, or `flat` (range ≤ 4).
12. **Checks** (DATA 2.8): each passes or fails, with its `say` line.
13. **Loopback guard.**
    - Rebuild Claude's notes for the run through `groove_bridge.mjs` from def, settings, seed and passes.
    - If more than half of Claude's onsets have one of his onsets of the same pitch within 15 ms, set
      `loopback.suspected`, say "the loop may be echoing into the log (MIDI loopback)", and still analyse.
14. **Highlights.** The top 3 slot instances by (new colour labels) + 2·(reharmonized) + (velocity peak z-score within
    the run). Each carries its m:ss plus two commands:
    `py -m arsenal.pianocue replay <session> <m:ss> --seconds 6` and
    `py -m arsenal.pianocue template save-from-moment <session> <m:ss>`.

### 11.4 Talking points, the question and the try (v1)

Salience = type weight × min(1, count / 5) × (1.25 when the point concerns the card's concept note: a `checks[].role`,
or the #11 on a `lydian` tag) × (0.5 when the same type was said for this card in its last saved riff). Chat takes up
to 6 points; the v2 report card takes the top 3 of different types. All templates state **counts, not percentages**.

| Type | Template (gate) | Weight |
|---|---|---|
| T1 colour on top | "Over Cm11 (6m11) your top line leaned on the 9, D: 11 of 26 notes, first at 1:12." (the label carries ≥ 20% of that slot's colour weight; ≥ 4 notes) | 1.0 |
| T2 mode | "Over the 4 chord you played Ab Lydian: the D, its #11, came 9 times." (the naming gate) | 1.1 |
| T3 landings | "8 of your 12 phrases landed on a colour, mostly the 9." (≥ 6 phrases) | 0.9 |
| T4 held rub | "At 1:12 you held Ab over Ebmaj9 for 2 beats: it rubs a half step against the G. At 0:50 the same Ab passed quickly." (≥ 1 held rub; pairs with a passing use when one exists) | 1.0 |
| T5 key note over a borrowed chord | "Over Abm6 (4m, borrowed) you played D natural, the key's note, 3 times; the chord's scale has Db." (≥ 2) | 1.0 |
| T6 inside the key | "None of your 412 notes left Eb major." (outside plus slide-in under 1 in 200, and ≥ 100 notes) | 0.8 |
| T7 slide-ins | "You slid into G from a half step below 4 times, first at 0:42." (≥ 3) | 0.8 |
| T10 phrase length | "Your phrases were mostly 2 bars (9 of 12), and 7 started with a pickup." (≥ 6 phrases) | 0.8 |
| T13 growth | "Colour notes went from 3 of 25 in passes 1-2 to 9 of 29 in the last two." (≥ 4 passes; a change of ≥ 10 points of share) | 0.8 |
| T14 anticipations | "You arrived early on the chord change 5 times." (≥ 3) | 0.7 |

**One question.** The highest-salience ambiguous moment: a held rub, an outside note of 1 beat or more, or a landing
on a class he used under 10% of the time. It is asked about intent, with its replay range `[t − 4 s, t + 4 s]`.
Example: "At 1:12 the G natural rubbed against the Gb in the bass. Did you want that rub?"

**One thing to try**, the first of these that applies:
1. The card's concept note came up fewer than 2 times: "land your top note on <note> in bar N".
2. Held rubs recurred 3 or more times: "let the rub pass quickly, or step it down to <chord tone>".
3. T6 applies: "slide into the 3rd of <chord> from a half step below".
4. Every phrase started on a downbeat: "start one phrase a beat early".
5. Otherwise: the card's own `try` line.

**Wording guard** (a receipt checks every rendered string):
- Never "wrong", "mistake", "error", "score", "best", "%", "should" or "correct".
- Theory names only in brackets after the plain words.
- Every number in a sentence equals a field in the JSON.

### 11.5 Guards and exits

| Case | Exit |
|---|---|
| No session overlaps the run | exit 2, printing the run's wall-clock window and the nearest sessions |
| L4 refused for a buffered session | exit 2, naming the missing `opened_at_client` |
| The run has no ack and the session has no `page_id` or `opened_at_client` | L4 with `approx: true` |
| Fewer than 8 of his onsets inside the run | exit 0 with "not enough playing inside the loop to talk about (N notes)" and no talking points |

### 11.6 Output (`arsenal.practice.riff/v0`)

```json
{ "api": "arsenal.practice.riff/v0", "constants": {"ONSET_GROUP_MS": 50, "LINE_MIN_NOTE": 60, "GRID_TOL": 0.08, "...": "..."},
  "session": "<id>",
  "runs": [ {
    "run": "<run>", "card": {"id": "lydian-four", "rev": 1, "variant": null}, "mode": "loop",
    "alignment": {"method": "L1", "error_ms": 2, "bar0_t_ms": 22222.2, "approx": false, "output_latency_ms": 21.3},
    "loopback": {"suspected": false, "mirrored_share": 0.0},
    "coverage": {"passes": 9, "bars": 18, "bars_with_his_notes": 16, "notes": 412, "top_line_notes": 233},
    "slots": [ {"slot": 1, "name": "Abmaj7#11", "number": "4maj7#11", "instances": 9,
                "classes": {"in_chord": 61, "colour": 30, "rub": 2, "passing": 1, "slide_in": 0, "outside": 0},
                "labels": {"#11": 9, "9": 14, "3": 20}, "bass_labels": {"3": 20},
                "landings": {"3": 5, "#11": 2}, "reharmonized": [], "outside": [],
                "scale": {"best": "Ab Lydian", "score": 0.93, "runner_up": "Eb major", "margin": 0.02, "named": true} } ],
    "degrees_by_bar": {"most_played": ["9", "#11"], "passes": [["9", "3"], ["5", "#11"]]},
    "passes": [ {"pass": 1, "range": ["Bb4", "Eb6"], "vel_median": 51, "vel_p90": 66,
                 "shares": {"in_chord": 0.58, "colour": 0.39, "outside": 0.03}, "rests": 0, "pedal": 0.82,
                 "onsets_per_bar": 5.5, "fact": "your widest top line"} ],
    "phrases": [ {"at": "1:04", "pass": 2, "bar": 1, "beat": -0.5, "bars": 2.0, "pickup": true, "contour": "arch",
                  "landing": {"class": "colour", "label": "9"}} ],
    "anticipations": [ {"at": "1:35", "to_slot": 0, "early_ms": 180} ],
    "checks": [ {"id": "sharp-eleven", "pass": true, "say": "you touched D, the #11 of Ab"} ],
    "highlights": [ {"at": "1:47", "slot": 1, "why": "new colour: D (#11) for the first time",
                     "replay": "py -m arsenal.pianocue replay <session> 1:44 --seconds 6",
                     "save": "py -m arsenal.pianocue template save-from-moment <session> 1:47"} ],
    "notes": [ {"t_ms": 64210, "at": "1:04.2", "pass": 2, "bar": 1, "beat": 3.5, "note": 73, "name": "Db5", "top": true,
                "slot": 0, "class": "colour", "label": "9", "bass_label": "9", "w": 0.8, "grid": "offbeat",
                "flags": ["anticipates"]} ] } ],
  "talking_points": [ {"type": "T2", "run": "<run>", "text": "...", "times": ["0:42"], "replay": "...", "evidence": {"count": 9}} ],
  "question": {"text": "...", "at": "1:12", "replay": "py -m arsenal.pianocue replay <session> 1:08 --seconds 8"},
  "try": {"text": "...", "rule": 1, "card": {"id": "lydian-four", "target_notes": [74], "bar": 2}} }
```

The numbers are illustrative. Shares are internal fields only; rendered text uses counts. The text render is a
chat-ready block: coverage, up to 6 talking points with times, checks, highlights, the question and the try.

### 11.7 Free play (no run)

Chords come from `practice.analyze` windows, labelled "chords read from your own playing", each with its window's
scale from its class (MUSIC 9.5 table). There is no grid, so there are no anticipations, landings are measured against
window starts, phrases split on gaps of 600 ms or more, and T14 is left out.

### 11.8 v2 additions

- Rhythm with calibration: placement, drift, swing, syncopation (MUSIC 9.8).
- Motifs, and question/answer phrase pairs (9.9).
- Call-and-response scoring (9.10).
- Enclosure, blue-note and suspension classes.
- Talking points T8, T9, T11, T12, T15, and try rules 4 and 6.
- The report card payload.

---

## 12. The seed deck (final text, 17 cards)

**Files.**
- `arsenal/jam/seed/deck-v1.json` (tracked, `{"api": "arsenal.jam.seed/v0", "seed_version": 1, "cards": [...]}`) holds
  exactly the text below.
- `state/arsenal/jam/seed/moments-v1.json` (git-ignored, `{"api": "arsenal.jam.seed.moments/v0", "cards": {"<id>":
  {"moments": [...], "replay": {...}}}}`) holds the moment links, copied from `design-data.md` section 10 by the seed
  phase. Section 12 names only how many links each card has.

**Common fields.** Every card has `created_by: "claude"`, `source: {kind: "seed", seed_version: 1}`,
`playback.velocity: 48` and `voicing.style: "spread"` unless it says otherwise.

**Checked.** "Page reads" is the voicing bridge's round trip, run on 2026-09-14 (`jam/seed_check.txt`) or by the data
lane (DATA 10). `deck seed` recomputes `page_reads` anyway.

**Wording rule.** Card text never says "wrong", "mistake" or "should"; theory names only follow plain words.

**Slots** in checks count from 1 in this text and are stored 0-based.

| # | id | group | kind | key | bpm | bars | groove / backing | line |
|---|---|---|---|---|---|---|---|---|
| 1 | `lydian-four` | moves | loop | Eb major | 66 | 2 | hold / full | `1maj9:4 \| 4maj7#11:4` |
| 2 | `gospel-five-over-four` | moves | loop | Eb major | 66 | 4 | ballad / full | `4maj9:4 \| 5^11/4:4 \| 1/3:4 \| 1maj9:4` |
| 3 | `one-note-apart` | moves | concept | Eb major | 60 | var. | hold / full | a `4maj13#11:8`, b `5^11/4:8`, c both then home (exact notes) |
| 4 | `blooming-chord` | moves | progression | Eb major | 60 | 5 | hold / full | `4sus2:4 \| 4add9:4 \| 4maj9:4 \| 4maj13#11:8` (exact notes) |
| 5 | `half-step-slide` | moves | concept | Eb major | 60 | var. | ballad / full | a `2^9/#4:4 \| 2m9/4:4 \| 4maj7#11:8`, b in Db `#4m7/6:4 \| 4maj7/6:8` |
| 6 | `lament-bass` | moves | loop | Db major | 60 | 4 | hold / full | `6m11:4 \| 6m11/5:4 \| 6m11/4:4 \| 6m11/3:4`, upper same |
| 7 | `minor-third-drop` | moves | progression | F major | 66 | var. | ballad / comp | a F to D, b Gb to Eb (key items) |
| 8 | `borrowed-four-minor` | moves | loop | Eb major | 66 | 4 | ballad / full | `1maj9:4 \| 4add9:4 \| 4m(add9):4 \| 1maj9:4` |
| 9 | `borrowed-b6-b7-home` | moves | loop | Eb major | 66 | 4 | ballad / full | `b6maj9:4 \| b7maj9:4 \| 1maj9:8` |
| 10 | `float-or-pull` | try | concept | Eb major | 60 | var. | ballad / full | a sus, b V7, c sus then V7 |
| 11 | `lush-two-five-one` | try | loop | Eb major | 63 | 4 | ballad / full | `2m9:4 \| 5^13:4 \| 1maj9:8` (exact notes) |
| 12 | `sunrise-ending` | moves | loop | Eb major | 60 | 8 | hold / full | `1m11:4 \| 1m11:4 \| b6maj7#11:4 \| 5^7sus4:2 \| 5^7:2 \| b3maj9:4 \| b3maj9:4 \| 4m6:4 \| 1maj9:4` |
| 13 | `db-opening` | moves | loop | Db major | 56 | 6 | hold / full | `4maj9:2 \| 4maj7#11:6 \| 5^11/4:4 \| 4maj7#11:4 \| 6m9/1:8` |
| 14 | `held-sus-five` | moves | moment | Eb major | 60 | 4 | hold / full | `5^7sus4/1:16` (his notes) |
| 15 | `open-ending-b7` | moves | moment | Eb major | 60 | 4 | hold / full | `b7maj9:16` (his notes) |
| 16 | `white-keys` | try | loop | C major | 72 | 4 | pulse / full | `1maj9:4 \| 6m11:4 \| 4maj7#11:4 \| 5^7sus4:2 \| 5^13:2` |
| 17 | `dorian-vamp` | try | loop | D minor | 88 | 2 | pulse / comp | `1m11:4 \| 4^13:4` |

Where the three lanes differed:
- **Card 1** takes DATA's two bars with MUSIC's `maj7#11`.
- **Card 12** takes MUSIC's single-tonic 8-bar loop as the main line and keeps DATA's 16-bar three-homes line as variant b.
- **Cards 16 and 17** are MUSIC's stretches.
- **MUSIC's call-and-response bloom** waits for the v2 seed (it needs the `arp` groove and call and response).
- **Two ids are renamed from DATA:** `chromatic-slide` is now `half-step-slide`, and `lights-on-ending` is now
  `sunrise-ending`. The seed phase maps their moments.

### 12.1 The Lydian 4 chord (`lydian-four`)

- **Line:** `1maj9:4 | 4maj7#11:4`. In Eb: Ebmaj9, Abmaj7#11. Also in Db major (Dbmaj9, Gbmaj7#11) and F major (Fmaj9, Bbmaj7#11).
- **Page reads:** Ebmaj9 exact; Abmaj7#11 exact (spread Ab2 G3 C4 D5 Eb5; the band voicer keeps D under A4). Db and F exact; Gb enharmonic (Cbmaj7#11).
- **Meaning:** The 4 chord with a raised 4th inside: it floats instead of landing.
- **Theory name:** Lydian
- **Explanation:** The 4 chord (Ab) with a D in it. D is the #11, a raised 4th above Ab. It already belongs to Eb major, so it shimmers and still sounds like home's family.
- **Why it matters:** It is your signature colour. The practice analyzer found a Lydian 4 in 80 moments across your four sessions on 2026-09-14, in Eb and in Db.
- **Try this:** Keep the loop going. On the Ab bar, move your top finger between C and D: C is the plain chord, D is the shimmer. Then try D over the Eb bar too, where it is the major 7th.
- **Listen for:** the moment D arrives over the Ab bass.
- **Check:** slot 2, role `#11`, present: "you touched D, the #11 of Ab".
- **Tags:** signature, lydian, colour. **Related:** one-note-apart, blooming-chord, db-opening. **Moments:** 3.

### 12.2 The gospel 5 over 4 (`gospel-five-over-four`)

- **Line:** `4maj9:4 | 5^11/4:4 | 1/3:4 | 1maj9:4`. In Eb: Abmaj9, Bb11/Ab, Eb/G, Ebmaj9.
- **Variant b** "keep it rolling": `4maj9:4 | 5^11/4:4 | 3m9:4 | 6m11:4` (Abmaj9, Bb11/Ab, Gm9, Cm11).
- **Also in:** Db major (Gbmaj9, Ab11/Gb, Db/F, Dbmaj9) and D major (Gmaj9, A11/G, D/F#, Dmaj9).
- **Page reads:** every chord exact in Eb, Db and D, including variant b.
- **Meaning:** The 5 chord standing on the 4 in the bass: churchy, and it leans home softly.
- **Theory name:** slash chord, 5 over 4
- **Explanation:** In Bb11/Ab your right hand plays the 5 chord (Bb) while the bass stays on Ab, the 4. It leans toward home without the hard pull of a plain 5.
- **Why it matters:** The bass only has to step down from Ab to G to land (G is the 3rd of Eb), so the arrival is soft and churchy. It is one of your most used shapes, and you played it in three keys on 2026-09-14.
- **Try this:** Let the loop run and follow the bass with your ear: Ab, Ab, G, Eb. Then make a melody from C and Eb, which sit well over all four bars. For a loop that never lands, switch to variant b.
- **Listen for:** the bass stepping from Ab down to G.
- **Checks:** slot 3, `landing`, role `3`: "you landed on G as the bass stepped down"; slot 3, `landing`, role `1`: "you landed on home as the bass stepped down".
- **Note on bar 3:** a plain Eb/G on purpose, so the bass step is what you hear; bar 4 brings the colour back.
- **Tags:** signature, gospel, slash. **Related:** one-note-apart, db-opening. **Moments:** 4.

### 12.3 One note apart (`one-note-apart`)

- **Variants (exact notes):**
  - **a** "the Lydian 4, with G": `4maj13#11:8`, name Abmaj13#11, notes Ab2 Eb3 G3 C4 D4 F4 Bb4.
  - **b** "the gospel 5 over 4, without G": `5^11/4:8`, notes Ab2 Eb3 C4 D4 F4 Bb4.
  - **c** "back and forth": `4maj13#11:4 | 5^11/4:4 | 1/3:8`, with a's and b's notes and Eb/G spread.
- **Page reads:** a reads **Cm11/Ab** (reads-as line shown: "your screen calls this Cm11/Ab: the same notes"); b Bb11/Ab exact. The Loop backing for a uses the band voicer and carries the same reads-as warning.
- **Meaning:** Your two favourite chords over an Ab bass are one finger apart.
- **Theory name:** Lydian and the 5 over 4
- **Explanation:** Over an Ab bass, Bb11/Ab and Abmaj13#11 share six notes: Ab Bb C D Eb F. The Lydian chord adds one more, G.
- **Why it matters:** G is the major 7th of Ab. With it the chord floats and can stay; without it the chord belongs to Bb and leans toward Eb. In Db the same pair is Gbmaj13#11 and Ab11/Gb, and the note is F.
- **Try this:** Hold the Ab bass. Play a, then lift only the G and listen to the chord start to lean. Put it back. The screen may give the same sound three names: the notes are what matter.
- **Listen for:** the lean when G leaves.
- **Tags:** signature, lydian, gospel. **Related:** lydian-four, gospel-five-over-four. **Moments:** 2.

### 12.4 The blooming chord (`blooming-chord`)

- **Line (exact notes, each chord keeps the one before it, `arp_ms: 45` on each):**
  - `4sus2:4`: Ab2 Eb3 Bb3 Eb4
  - `4add9:4`: Ab2 Eb3 Bb3 C4 Eb4 (adds C)
  - `4maj9:4`: Ab2 Eb3 G3 Bb3 C4 Eb4 (adds G)
  - `4maj13#11:8`, name Abmaj13#11: Ab2 Eb3 G3 Bb3 C4 Eb4 D5 F5 (adds D and F)
- **Page reads:** Absus2, Abadd9, Abmaj9 exact (checked as numbers); the last reads Cm11/Ab, as card 3a.
- **Meaning:** One chord opening like a flower: no 3rd, then the 3rd, then the 7th, then the Lydian top.
- **Theory name:** added colour tones
- **Explanation:** Keep the root and bass still and add colour one note at a time: sus2 (Ab Bb Eb), then the 3rd arrives (add9), then the major 7th (maj9), then the Lydian top (D and F).
- **Why it matters:** A chord can grow in front of the listener: the harmony stays and the colour rises. The analyzer found 65 of these colour additions in your longest session alone.
- **Try this:** Play along with it, then un-bloom it yourself: take the notes away in reverse, one per bar, until only Ab and Eb are left.
- **Listen for:** which added note changes the mood most.
- **Tags:** signature, colour. **Related:** lydian-four. **Moments:** 3.

### 12.5 The half-step slide (`half-step-slide`)

- **Variants:**
  - **a** "the bass slides": `2^9/#4:4 | 2m9/4:4 | 4maj7#11:8`. In Eb: F9/A, Fm9/Ab, Abmaj7#11. Exact notes for the first two: A2 F3 Eb4 G4 C5, then Ab2 F3 Eb4 G4 C5 (only A moves).
  - **b** "the top slides over a still bass", variant key `b7 major` (Db major when the card is in Eb): `#4m7/6:4 | 4maj7/6:8`. In Db: Gm7/Bb, Gbmaj7/Bb. Exact notes Bb2 F3 G3 Bb3 D4, then Bb2 F3 Gb3 Bb3 Db4.
- **Page reads:** a all exact (checked). b: Gbmaj7/Bb expected exact; the first chord may read **Bb6** (the same four notes), and the reads-as line says so. Variant b is a Play and Show variant: its Loop uses the band voicer, which may drop a sliding voice, so the card's Loop plays variant a.
- **Meaning:** Slide one note down a half step and the colour turns from bright to shadow.
- **Theory name:** chromatic voice leading
- **Explanation:** In a, only one note moves: A slides down to Ab, and F, Eb, G and C stay where they are. In b, over a held Bb, two notes slide down a half step: G to Gb and D to Db.
- **Why it matters:** A half step is the smallest move on the keyboard, so the colour changes while everything else holds, and the ear follows the note that moved.
- **Try this:** Loop a and play the moving note yourself as a tiny melody an octave up: A, then Ab. Then look for another chord in your pieces where one note can slide.
- **Listen for:** A turning into Ab.
- **Tags:** signature, half-step. **Related:** lament-bass. **Moments:** 2.

### 12.6 Walking bass under a held chord (`lament-bass`)

- **Line:** `6m11:4 | 6m11/5:4 (upper same) | 6m11/4:4 (upper same) | 6m11/3:4 (upper same)`. In Db: Bbm11, Bbm11/Ab, Bbm11/Gb, Bbm11/F. Also in Eb major (Cm11 over C, Bb, Ab, G).
- **Play notes (exact, your hands):** hands Bb3 Ab4 C5 Db5 Eb5 F5 on every bar; bass Bb2, Ab2, Gb2, F2.
- **Page reads:** Bbm11, Bbm11/Ab, Bbm11/Gb, Bbm11/F, all exact (checked in close voicing, and by the data lane in the exact voicing). The Loop backing's shared upper shape must keep F (the gate over every slot, 10.1).
- **Meaning:** Hold one chord and let the bass step down underneath: the sad staircase.
- **Theory name:** lament bass
- **Explanation:** Your hands hold one chord, Bbm11, the whole time. Only the bass walks down: Bb, Ab, Gb, F.
- **Why it matters:** Four bass notes stepping down from the minor chord's root is the old lament bass. The hands never move, yet the harmony does: over Gb the same notes are the whole Lydian 4 (Gbmaj13#11), and over F they hold Dbmaj9 plus a Bb.
- **Try this:** Keep the loop going and play a slow melody that stays on one note, Db or F, while the bass walks under it. Listen to the same note change its meaning bar by bar.
- **Listen for:** bar 3, where the chord turns bright.
- **Check:** slot 3, role `#11`, `relative_to: "bass"`, present: "you found C, the Lydian note, over the Gb bass".
- **Tags:** signature, bass. **Related:** half-step-slide, lydian-four. **Moments:** 2.

### 12.7 Down a minor third to a new home (`minor-third-drop`)

- **Variants:**
  - **a** "F to D": `1add9:4 | 4maj13:4 | 5^6:4 | [6 major] | 1add9:4 | 4maj13:4 | 1maj9:8`. In F: Fadd9, Bbmaj13, C6. Then in D: Dadd9, Gmaj13, Dmaj9.
  - **b** "Gb to Eb", variant key `b2 major` (Gb major): `4maj9:4 | 1maj9:4 | 5sus4:4 | [b7 major] | b3add9/b7:2 | 1add9:6 | 4maj9:4 | 1maj9:8`. In Gb: Cbmaj9, Gbmaj9, Dbsus4. Then in Eb: Gbadd9/Db, Ebadd9, Abmaj9, Ebmaj9. (Key items are degrees of the card key F: b7 of F is Eb.)
- **Page reads:** every chord exact, except Cbmaj9 enharmonic (checked).
- **Meaning:** Move home down three half steps and walk through a door chord into a warmer room.
- **Theory name:** modulation down a minor third
- **Explanation:** To change key, move home down a minor third (three half steps): F to D, Gb to Eb. The door is your old 5 chord: C is the 5 of F and also the b7 of D. Play it, then land on the new 1. The chips restart their numbers at 1 in the new key.
- **Why it matters:** The new key arrives through a chord that belongs to both keys, so the change sounds like walking through a door instead of jumping. It works from any key: the old 5 is always the b7 of the key three half steps below.
- **Try this:** Loop the door chord (C6) for two bars and choose your moment to step through. Then use the same door from Eb: Bb, the 5 of Eb, is the b7 of C major.
- **Listen for:** the bar where D major arrives.
- **Tags:** signature, key-change. **Related:** sunrise-ending. **Moments:** 2.

### 12.8 The borrowed 4 minor (`borrowed-four-minor`)

- **Line:** `1maj9:4 | 4add9:4 | 4m(add9):4 | 1maj9:4`. In Eb: Ebmaj9, Abadd9, Abm(add9), Ebmaj9.
- **Page reads:** Ebmaj9 and Abadd9 exact; Abm(add9) enharmonic (checked). In spread voicing only one note moves: C to Cb.
- **Meaning:** Lower one note in the 4 chord and it turns bittersweet just before home.
- **Theory name:** borrowed from Eb minor
- **Explanation:** 4m is your Ab chord with its 3rd lowered: C drops to Cb. Cb comes from Eb minor, so the chord is "borrowed".
- **Why it matters:** One lowered note turns the 4 chord from warm to bittersweet right before home. It is the sigh at the end of a lot of ballads, and you reached for Abm in two sessions.
- **Try this:** Move only the finger on C. Then let your melody use Cb during that bar, and C again when home comes back.
- **Listen for:** the sigh in bar 3.
- **Check:** slot 3, role `b3`, present: "you played Cb, the borrowed note".
- **Tags:** borrowed. **Related:** borrowed-b6-b7-home, sunrise-ending. **Moments:** 2.

### 12.9 b6, b7, home (`borrowed-b6-b7-home`)

- **Line:** `b6maj9:4 | b7maj9:4 | 1maj9:8`. In Eb: Cbmaj9, Dbmaj9, Ebmaj9.
- **Page reads:** the page spells the first chord **Bmaj9** (enharmonic, the same chord with sharps); Dbmaj9 and Ebmaj9 exact (checked).
- **Meaning:** Two borrowed major chords climb a whole step at a time into home.
- **Theory name:** Aeolian cadence
- **Explanation:** Two major chords borrowed from Eb minor, a whole step apart, climb into home: Cb, Db, Eb.
- **Why it matters:** The roots rise step by step (b6, b7, 1), so home arrives big and open without any 5 chord.
- **Try this:** You once ended a piece on Dbmaj9. Loop this and choose each time: stop on b7 (the door stays open) or go on to 1 (home).
- **Listen for:** how open home sounds without a 5 chord.
- **Tags:** borrowed, ending. **Related:** open-ending-b7, borrowed-four-minor. **Moments:** 3.

### 12.10 Float or pull (`float-or-pull`)

- **Variants:**
  - **a** "float (your habit)": `1maj9:4 | 5^7sus4/1:8 | 1maj9:4`. Slot 2 exact notes, yours: Eb2 Eb3 Eb4 F4 Ab4 Bb4.
  - **b** "pull": `1maj9:4 | 5^7:8 | 1maj9:4`.
  - **c** "float, then pull": `1maj9:4 | 5^7sus4:4 | 5^7:4 | 1maj9:8`. Exact notes Bb2 F3 Ab3 Eb4, then Bb2 F3 Ab3 D4: only Eb4 moves, to D4.
- **Page reads:** Ebmaj9, Bb7sus4/Eb, Bb7, Bb7sus4 all exact (checked).
- **Meaning:** The sus 5 chord floats; give it its 3rd and it pulls you home.
- **Theory name:** suspended dominant and dominant 7
- **Explanation:** Bb7sus4 swaps Bb7's 3rd (D) for Eb. D sits a half step under home (Eb), so Bb7 pulls toward Eb. Bb7sus4 already holds Eb, so it floats.
- **Why it matters:** None of the 5-to-1 moves the analyzer found in your sessions uses a plain 5 chord with its 3rd. Your 5 chords arrive suspended (Bb7sus4 over Eb, held 15 seconds) or with an added 11th. The pull is a colour you have not used yet, and contrast (float, then pull, then home) makes an arrival feel earned.
- **Try this:** Play a, b and c. Then loop c and riff: lean on D during the Bb7 bar and let it rise to Eb when home comes.
- **Listen for:** D, the note that turns float into pull.
- **Checks:** variant c, slot 3 (Bb7), role `3`, present: "you played D, the 3rd of Bb7"; variant c, slot 4, `landing`, role `1`: "you landed on home".
- **Tags:** growth-edge, dominant. **Related:** held-sus-five, lush-two-five-one. **Moments:** 2.

### 12.11 The lush 2-5-1 (`lush-two-five-one`)

- **Line (exact notes):** `2m9:4` F2 Eb3 Ab3 C4 G4; `5^13:4` Bb2 D3 Ab3 C4 G4; `1maj9:8` Eb2 D3 G3 Bb3 F4. In Eb: Fm9, Bb13, Ebmaj9.
- **Page reads:** Fm9, Bb13, Ebmaj9 exact in spread voicing (checked); these exact voicings expected exact.
- **Meaning:** A real 2-5-1 in your lush colours: one note falls a half step at each change.
- **Theory name:** ii-V-I with guide tones
- **Explanation:** At each change one note steps down a half step while its neighbour holds: Eb falls to D (Fm9 to Bb13), then Ab falls to G (Bb13 to Ebmaj9).
- **Why it matters:** This is the pull of a real 5 chord, still in your lush colours. The falling half steps (each chord's 7th becoming the next chord's 3rd) are what make home sound like arriving.
- **Try this:** Play only the two inner notes as a little two-voice line (Eb and Ab, D and Ab, D and G), then put the full chords back. Then swap Bb13 for your Bb7sus4 over Eb and compare.
- **Listen for:** the two falling half steps.
- **Check:** slot 2, role `3`, present: "you played D, the note that pulls home".
- **Tags:** growth-edge, dominant. **Related:** float-or-pull. **Moments:** 1.

### 12.12 The sunrise ending (`sunrise-ending`)

- **Line:** `1m11:4 | 1m11:4 | b6maj7#11:4 | 5^7sus4:2 | 5^7:2 | b3maj9:4 | b3maj9:4 | 4m6:4 | 1maj9:4`. In Eb: Ebm11, Ebm11, Cbmaj7#11, Bb7sus4 into Bb7, Gbmaj9, Gbmaj9, Abm6, Ebmaj9.
- **Variant b** "the long way, three homes" (DATA's line, key items of the card key): `1m9:4 | 4m9:4 | b6maj9:4 | b7maj9:4 | [b3 major] | 4maj9:4 | 6m9:4 | 5sus4:4 | 1maj9:8 | [1 major] | b3add9/b7:4 | 1add9:4 | 4maj9:4 | 1maj9:8` (Eb minor colours, then Gb major, then Eb major).
- **Page reads:** Ebm11, Bb7sus4, Bb7, Gbmaj9, Abm6, Ebmaj9 exact; Cbmaj7#11 enharmonic, shown as Bmaj7#11 (checked). Variant b: every chord checked by the data lane.
- **Meaning:** Minor home, a lift into its bright relative, then home again in full light.
- **Theory name:** relative major, then parallel major
- **Explanation:** Ebm11 is home in minor. Gbmaj9 uses the same notes with Gb as home: that is the climax. Abm6 keeps one borrowed note for a last sigh, then Ebmaj9 arrives with the light on: Gb has become G.
- **Why it matters:** This is how you end a dark piece in full light: Eb minor, a Gb major climax, then Eb major. Bar 4 also gives your 5 chord its 3rd for two beats, the pull from card 10.
- **Try this:** Play the Gb bars as the loudest part of the loop, then let Ebmaj9 arrive soft and slow. Listen for the G natural in the last bar.
- **Listen for:** G natural in the last bar.
- **Check:** slot 9 (Ebmaj9), role `3`, present: "you played G, the note that turns the lights on".
- **Tags:** signature, key-change, ending. **Related:** minor-third-drop, borrowed-four-minor. **Moments:** 2.

### 12.13 Your Db opening (`db-opening`)

- **Line:** `4maj9:2 | 4maj7#11:6 | 5^11/4:4 | 4maj7#11:4 | 6m9/1:8`. In Db: Gbmaj9, Gbmaj13#11, Ab11/Gb, Gbmaj13#11, Bbm9/Db.
- **Exact notes (both `4maj7#11` slots, name Gbmaj13#11):** your pedal cloud, Gb2 Db3 Gb3 Ab3 Bb3 Db4 F4 Bb4 Eb5 F5 Ab5 C6. Play uses the cloud; the Loop backing voices `4maj7#11`, which reads exact.
- **Page reads:** Gbmaj9, Ab11/Gb, Bbm9/Db, Gbmaj7#11 exact (checked); the cloud reads as letters "Gb Db Ab Bb F Eb C" with no number (reads-as line shown).
- **Meaning:** Your own opening, straightened into a loop.
- **Theory name:** Lydian 4, slash chords
- **Explanation:** Gbmaj9 blooms into the Lydian 4 of Db, Ab11/Gb takes a breath, and Bbm9 over Db brings you home.
- **Why it matters:** You never play a plain Db chord here, and it still sounds like home, because the bass lands on Db.
- **Try this:** Ab is in every chord of this loop: start a melody on Ab, then reach up to C, which is in every chord but the first.
- **Listen for:** home arriving through the bass alone.
- **Tags:** yours, lydian. **Related:** lydian-four, gospel-five-over-four. **Moments:** 1.

### 12.14 The held sus 5 (`held-sus-five`)

- **Line:** `5^7sus4/1:16`, exact notes Eb2 Eb3 Eb4 F4 Ab4 Bb4 (yours).
- **Replay:** from the moments file (18 seconds at 1x).
- **Page reads:** Bb7sus4/Eb exact (checked).
- **Meaning:** Tension and rest at the same time: a 5 chord over the home bass.
- **Theory name:** pedal point
- **Explanation:** You held Bb7sus4 over Eb for 15 seconds: Eb F Ab Bb, with Eb in three octaves. It never resolved, and it did not need to: Eb, home, is inside it.
- **Why it matters:** A 5 chord over the home bass is tension and rest at once. It is the root of your floating sound.
- **Try this:** Hear yourself play it. Then play it again and, after a few seconds, move Eb4 down to D4: Bb7 over Eb, a new colour on the same bass.
- **Listen for:** how long it can hang without resolving.
- **Tags:** yours, dominant. **Related:** float-or-pull. **Moments:** 1.

### 12.15 The open ending (`open-ending-b7`)

- **Line:** `b7maj9:16`, exact notes Db3 Ab3 Eb4 F4 Ab4 C5 Db5 F5 Ab5 (yours).
- **Replay:** from the moments file (12 seconds at 1x).
- **Page reads:** Dbmaj9, b7maj9, exact (checked by the data lane).
- **Meaning:** Ending on the b7 chord leaves the door open.
- **Theory name:** borrowed bVII
- **Explanation:** You ended an Eb major piece on Dbmaj9, the b7 chord, borrowed from Eb minor. The piece stops with the door open instead of closing it.
- **Why it matters:** An ending that is not 1 feels like a question. It is a real choice, and this card keeps it so you can choose it on purpose.
- **Try this:** Hear your ending. Then play it once more and add one bar of Ebmaj9 after it, and decide which ending the piece wants.
- **Listen for:** the question the last chord leaves.
- **Tags:** yours, borrowed, ending. **Related:** borrowed-b6-b7-home. **Moments:** 1.

### 12.16 Same shapes, white keys (`white-keys`)

- **Line:** `1maj9:4 | 6m11:4 | 4maj7#11:4 | 5^7sus4:2 | 5^13:2`. In C: Cmaj9, Am11, Fmaj7#11, G7sus4 into G13.
- **Page reads:** all exact (checked).
- **Meaning:** Your favourite numbers in a key with no black keys to lean on.
- **Theory name:** transposition
- **Explanation:** These are the numbers of your Lydian 4 loop and the pull of a real 5 chord, moved to C major, where every note of the key is a white key.
- **Why it matters:** In Eb, Db and Gb the black keys anchor your hands. The same sounds in C ask your ear, not your hand shapes, to find them.
- **Try this:** Loop it and find the #11 (B) over the F bar. Then notice when your hand reaches for Bb, Eb or Ab: those are your home keys talking.
- **Listen for:** B natural over the F bar.
- **Check:** slot 3, role `#11`, present: "you found B, the #11 of F".
- **Tags:** stretch, geography, lydian. **Related:** lydian-four, float-or-pull. **Moments:** 0.

### 12.17 Two-chord Dorian vamp (`dorian-vamp`)

- **Line:** `1m11:4 | 4^13:4`. In D minor: Dm11, G13.
- **Page reads:** Dm11 and G13 exact (checked).
- **Meaning:** Two chords, one scale, and a steady beat to play against.
- **Theory name:** Dorian
- **Explanation:** Dm11 and G13 share one scale: every white key, with D as home. B natural is the telling note: the 13 of G and the 6 of D.
- **Why it matters:** All your sessions so far are in free time, so there is no beat yet to play against. The pulse at 88 bpm is a little slower than your own note rate, so it leaves room to place notes off the beat.
- **Try this:** Play short phrases that start just after the beat. Leave a full bar of space after each phrase and let the vamp answer.
- **Listen for:** B natural against the Bb your hand expects.
- **Check:** slot 2, role `13`, present: "you played B, the 13 of G".
- **Tags:** stretch, rhythm, dorian. **Related:** white-keys. **Moments:** 0.

**A first night, in order:** card 1 (meet the loop on a sound you love), card 6 (the lament), card 10 (the growth
edge), card 12 (the sunrise), then card 17 or 16.

---

## 13. Build plan

### 13.0 Gate: three running builds land first

No jam phase starts until all three below are **landed**:
- committed by Vandor (the sole committer);
- their own receipts green;
- no advisory lock held on their files.

| Build | Files it owns (untouchable by jam phases until it lands) | Landed when |
|---|---|---|
| **B1 Cue channel, CLI, page module** | `arsenal/pianocue.py`, `arsenal/pianocue_voicing.mjs`, `arsenal/serve.py` (cue routes), `arsenal/web/piano/cues.js`, `cues-test.html`, and the INT wiring in `arsenal/web/piano.js`, `piano.html`, `piano.css` (cueSounding, ghost frames, chip, Escape, `midiRank` guard) | `py -m pytest tests/test_arsenal_pianocue.py tests/test_arsenal_serve.py -q` green; the INT section 9 checks pass in the piano receipt |
| **B2 Practice verbs** | `arsenal/practice.py`, `arsenal/practice_theory.mjs`, `tests/test_arsenal_practice.py` | `py -m pytest tests/test_arsenal_practice.py -q` green |
| **B3 Nashville and log fixes** | `arsenal/web/piano/nashville.js`, `arsenal/nashville.py`, `arsenal/web/piano/log.js`, `arsenal/performance.py`, `tests/fixtures/nashville_cases.json`, and the chord-event fix in `piano.js` | `py -m pytest tests/test_arsenal_nashville.py tests/test_arsenal_performance.py -q` and `node tests/nashville_js.test.mjs` green |

A phase's first act is to re-read its owned files at the landed commit, because INT's line numbers drift.

### 13.1 Ownership rules

1. **One owner per existing file per wave.** Only the phase listed in 13.3 edits that file in that wave. Every other
   phase reads it at the landed commit.
2. **New files belong to the phase that creates them.** A later phase edits them only when 13.3 hands them over.
3. **Shared contracts are frozen in J0.** `arsenal/jam/schemas.py`, the tempo maps and `tests/fixtures/jam/*` from J0
   change only through the conductor, with a note to every running phase.
4. **Integration is one phase.** `piano.js`, `piano.html` and `piano.css` belong to J9 alone. Wave-2 page modules
   expose the section 8.2 interfaces and are proven on their own test pages.
5. **Locks.** Each phase takes an advisory `lock` on its owned existing files at start and `unlock`s at hand-off.
   Phases work in their own worktrees and hand patches to Vandor, who commits.
6. **Test files are namespaced per phase** (`test_arsenal_jam_<phase topic>.py`, `tests/jam_<topic>.test.mjs`).
7. **Never on 8793.** Live checks use the phase's own server port (J3 8795, J7 8796, J8 8797, J9 8798) and an isolated
   headless Chrome with `--mute-audio` and the three anti-throttling flags (PIANO-V2-SPEC hard rules).

### 13.2 Phases

| Phase | Wave | Depends on | Scope | Exit (section 14) |
|---|---|---|---|---|
| **J0 Contracts** | 0 (sequential, conductor) | gate | Validators for card, def, run and ack (section 4); both tempo maps (9.1) with one shared fixture; the synthetic run and session fixtures used by J3, J4 and J7 | A2 (tempo map half); `test_arsenal_jam_schemas.py` accepts every fixture and refuses 24 malformed cases with the field named |
| **J1 Band voicer** | 1 | J0 | `band` style (10.1), `upper: "same"` with the gate over the run, `tones_pc`, `bass_pc`, the ring, determinism | A4 (voicing half) |
| **J2 Groove generator** | 1 | J0 | `groove.js` (10.2-10.6: hold, ballad, pulse; ties; humanize; walk; Try backings; Play rendering), `groove_bridge.mjs` | A2 (groove half) |
| **J3 Store, routes, hub, CLI** | 1 | J0 (J1 for the live resolve test) | `arsenal/jam/cards.py`, `resolve.py`, `runs.py`, `align.py`, `cli.py`; routes (section 5); `publish_event`, caps and page on subscribe (section 6); verbs (section 7). Uses a stub bridge until J1 merges | A4 (transposition half); route tests (conflicts, lease, pending/launch, landing rule, restart close) |
| **J4 Riff analysis** | 1 | J0 (J2 for the loopback guard test) | `practice_riff.py` (section 11) and the verb registration | A11 |
| **J5 Log timebase** | 1 | gate | `meta.page_id`, `meta.t0_perf_ms`, `opened_at_client` on every open; `log.timebase()` | `log-test.html` receipt: all three fields on 3 of 3 opens (live, buffered, reopened); `timebase()` equals the values sent; `git diff arsenal/performance.py` empty |
| **J6 Seed deck** | 1 | J0 (J1 + J3 for the resolve check) | `arsenal/jam/seed/deck-v1.json` (section 12 text verbatim), the moments file under `state/` from DATA section 10, `deck seed` against it | A4 (seed half): 17 of 17 cards validate and resolve; wording guard over every text field |
| **J7 Transport and voice** | 2 | J1, J2, J3 merged | `transport.js` (9.2-9.5, 8.9 gate logic); `cues.js` changes (9.3 table, 9.6, 9.7, named-event listeners); `transport-test.html`; `arsenal/lanes/jam_timing.mjs` | A1, A3 |
| **J8 Deck and glass** | 2 | J3, J6 merged | `deck.js`, `deck.css`, `glass.js`; `deck-test.html` mounted against a J3 server with a fake transport | A8 (deck-page half), A9 (projection maths on the test page) |
| **J9 Integration** | 3 | J5, J7, J8 merged | `piano.js`, `piano.html`, `piano.css` per 8.11; `arsenal/lanes/jam_verify.mjs` | A5, A6, A7, A8, A9, A10, A12 |
| **J10 First night with Daniel** | 4 | J4, J9 merged | `deck seed`, the first-night order (section 12), one real riff read-through (MUSIC R-M8), level and wording tuned by ear | Daniel reads 3 cards and one riff and says whether each fact matches what he remembers; the answers go to `state/arsenal/jam/riffs/` |

Rough size, for planning only: J0 half a day; J1, J3, J4 and J7 about a day each; J2, J8 and J9 one to one and a half
days; J5 and J6 a few hours each.

### 13.3 Who owns which file

`N` = creates the file; `E` = edits an existing file; blank = read only. No row has two marks in the same wave.

| File | J0 | J1 | J2 | J3 | J4 | J5 | J6 | J7 | J8 | J9 |
|---|---|---|---|---|---|---|---|---|---|---|
| `arsenal/jam/__init__.py`, `schemas.py` | N | | | | | | | | | |
| `arsenal/jam/tempomap.py`, `arsenal/web/piano/tempomap.js` | N | | | | | | | | | |
| `tests/fixtures/jam/tempomap_cases.json`, `run_loop_l1/`, `def_*.json` | N | | | | | | | | | |
| `tests/test_arsenal_jam_schemas.py`, `tests/jam_tempomap.test.mjs` | N | | | | | | | | | |
| `arsenal/pianocue_voicing.mjs` | | E | | | | | | | | |
| `tests/test_arsenal_voicing_band.py` | | N | | | | | | | | |
| `arsenal/web/piano/groove.js`, `arsenal/groove_bridge.mjs`, `tests/jam_groove.test.mjs` | | | N | | | | | | | |
| `arsenal/jam/cards.py`, `resolve.py`, `runs.py`, `align.py`, `cli.py` | | | | N | | | | | | |
| `arsenal/serve.py`, `arsenal/pianocue.py` | | | | E | | | | | | |
| `tests/test_arsenal_jam_store.py`, `_routes.py`, `_cli.py` | | | | N | | | | | | |
| `arsenal/practice_riff.py`, `tests/test_arsenal_practice_riff.py`, `tests/fixtures/jam/riff_*` | | | | | N | | | | | |
| `arsenal/practice.py` (3-line registration) | | | | | E | | | | | |
| `arsenal/web/piano/log.js`, `arsenal/web/piano/log-test.html` | | | | | | E | | | | |
| `arsenal/jam/seed/deck-v1.json`, `tests/test_arsenal_jam_seed.py` | | | | | | | N | | | |
| `state/arsenal/jam/seed/moments-v1.json` (untracked) | | | | | | | N | | | |
| `arsenal/web/piano/cues.js`, `cues-test.html` | | | | | | | | E | | |
| `arsenal/web/piano/transport.js`, `transport-test.html`, `arsenal/lanes/jam_timing.mjs` | | | | | | | | N | | |
| `arsenal/web/piano/deck.js`, `deck.css`, `glass.js`, `deck-test.html` | | | | | | | | | N | |
| `arsenal/web/piano.js`, `piano.html`, `piano.css`, `arsenal/lanes/jam_verify.mjs` | | | | | | | | | | E / N |
| `tests/test_arsenal_pianocue.py` (only if the hub change needs a new test; frame-bytes test untouched) | | | | E | | | | | | |

Wave 1 (J1-J6) touches six disjoint sets of existing files: `pianocue_voicing.mjs`; nothing; `serve.py` +
`pianocue.py` + `test_arsenal_pianocue.py`; `practice.py`; `log.js`; nothing. Wave 2 (J7, J8): `cues.js`; nothing.
Wave 3: `piano.js`, `piano.html` and `piano.css` only.

### 13.4 v2 waves (after J10; each keeps the same ownership rule)

| Wave | Scope | Owner files |
|---|---|---|
| V2-A Grooves | `swell`, `arp`, `gospel`, call and response, ramps, swing, `pad` timbre and backing, `bass_mode: pedal`, `ending: home` | `groove.js`, `cues.js` (pad timbre), `tempomap.*` |
| V2-B Discussion in the deck | Ask Claude, `jam wait`, report objects and routes, report cards, answer chips, Hear pass N, marks on his notes, `your top` | `arsenal/jam/reports.py`, `serve.py`, `jam/cli.py`, `deck.js`, `glass.js`, then `piano.js` in its own integration step |
| V2-C Rhythm | tap-along calibration, placement, drift, swing, motifs, call-and-response scoring, T8/T9/T11/T12/T15 | `practice_riff.py`, `jam/cli.py` |
| V2-D Duet recording | jam view `stage`, in-frame strip (UX 5.3 boxes and collision map), Claude's voice into the recorded track | `arsenal/web/piano/jamstrip.js`, `piano.js` |
| V2-E MIDI and FL | only after Daniel approves a loopback download: MIDI out (ch 1 bass, ch 2 chords), `midi_offset_ms`, channel echo filter, FL Route F, `.mid` export | `cues.js`, `arsenal/jam/fl.py`, `smf.py`, `midi_winmm.py`, `piano.js` |
| V2-F Names | THEORY templates `maj9#11`, `maj13#11`, `13sus4`, with the spectacle rarity table and both Nashville fixtures | the theory and spectacle owners together |
| V2-G Hands | kept-card inline editing, Try "wait for me", KeyLab pad learn, follow-me tempo | `deck.js`, `transport.js`, `piano.js` |

---

## 14. Acceptance checks

All are headless and scripted:
- isolated Chrome with `--mute-audio` and the three anti-throttling flags, on the phase's own server;
- never against 8793;
- dated receipts under `state/arsenal/receipts/jam/<check>-<date>/`.

A number marked **pass** is the bar to clear.

### A1 Loop timing drift over 5 minutes (J7, `arsenal/lanes/jam_timing.mjs` on `transport-test.html`)

**Setup.** A 4-bar synthetic def with groove `pulse`, backing `full`, humanize 0 and a click-like test timbre. Two
5:00 runs: 72 bpm (90 bars) and 140 bpm (175 bars). The 72 bpm run changes tempo to 80 at bar 40.

| Measure | Pass |
|---|---|
| (a) Plan: each handed event's `at` against the tempo-map formula | \|Δ\| ≤ 0.001 ms for 100% of events |
| (b) Player: note-on callback time minus planned time | p50 ≤ 1 ms, p99 ≤ 4 ms, max ≤ 12 ms; least-squares slope over the run \|slope\| ≤ 0.2 ms/min; mean of the first 30 s minus mean of the last 30 s ≤ 1 ms |
| (c) Sound: an AudioWorklet probe before the destination detects onset sample frames, compared with the planned time through the fitted clock | p99 ≤ 2 ms; slope ≤ 0.1 ms/min. If `--mute-audio` freezes `getOutputTimestamp`, the receipt says so and renders the same schedule in an OfflineAudioContext instead: every onset within 1 sample at 48 kHz |
| (d) Occluded window (CDP focus emulation off, page hidden) | worker wake lateness p99 ≤ 10 ms; `late_dropped` = 0 |
| (e) Tempo change | the bar-40 downbeat at the formula ± 0.5 ms; bars 41+ use the new bar length; the ack shows version 2, `effective_bar` 40 |
| (f) Clock step | a fake 30 ms `Date.now()` step at bar 60 moves no bar line (0.000 ms) and the ack reports `offset_step_ms: 30` |

### A2 Pure maths (J0, J2)

| Measure | Pass |
|---|---|
| `tempomap_cases.json` (40 cases: steps, many segments, bar ↔ epoch ↔ pass ↔ slot) in JS and Python | both agree with the fixture to 0.001 ms |
| `groove.js` determinism over 1000 random (def, settings, seed, pass, bar) inputs | byte-identical output on repeat |
| humanize 0 | every event exactly on its table position (10.3-10.5) and at its table velocity |
| transpose the def to all 12 keys | every event's `beat`, `len` and `vel` identical |
| ties and pickups | 100% belong to the bar that owns them |
| `groove_bridge.mjs` against the browser module | identical events for 200 bars |

### A3 Count-in accuracy and launch quantising (J7)

| Measure | Pass |
|---|---|
| Ticks at 60, 72 and 140 bpm, count-in 1 and 2 | exactly `4 × count_in` ticks; each onset within 2 ms of `start + k·beat`; the first tick of each bar at 2 kHz and the others at 1.5 kHz (OfflineAudioContext FFT peak ± 20 Hz) |
| Count-in length | `count_in × barMs` ± 1 ms |
| Silence before bar 0 | 0 backing notes sound before bar 0 |
| Bar 0 downbeat | the bass onset within 2 ms of `bar0_epoch_ms` mapped to page time |
| Strip countdown | the Now header's 4 3 2 1 changes within 17 ms of each tick |
| 30 swap and tempo requests at random times mid-run | 30 of 30 land on the first bar line ≥ 1 beat + 250 ms after the server received them |
| A frame delayed 180 ms (a proxy) | the bar is regenerated; 0 note-ons of the old version after the cancel; the ack carries `late_frame_ms` |

### A4 Card transposition correctness (J1, J3, J6)

Scope: 17 seed cards × 12 keys × backings `full`, `comp`, `bass` and `play` (816 resolves).

| Measure | Pass |
|---|---|
| Numbers | every slot's `n` identical in all 12 keys (100%) |
| Pitch classes | for every numbered slot, `chord_pcs` in key K equals the card-key set shifted by the interval (100%); section keys move with the card |
| Names (20 hand-written expectations, exact strings) | 20 of 20 |
| Exact-note chords | shift s in [−6, +5]; after folds the lowest ≥ E1 (28) and the highest ≤ G7 (103); interval pattern unchanged unless a fold is reported |
| Band registers | every `full` top ≤ A4 (69), every `comp` top ≤ E4 (64), every bass in 28..50, 0 adjacent pairs under their low-interval limit (100%) |
| Band round trip | every `full` slot reads `exact` or `enharmonic` in all 12 keys, except an exception list that must equal exactly {`one-note-apart` a slot 1, `one-note-apart` c slot 1, `blooming-chord` slot 4}, the chords whose cards show a reads-as line |
| Ring | the wrap move costs no more than the loop's largest other move, for every loop card |
| `lament-bass` | the upper voices identical across its 4 slots, with F present, in all 12 keys |
| Determinism and speed | byte-identical def JSON on repeat; warm resolve ≤ 2 ms; cold ≤ 150 ms (median of 10) for a 16-slot card |
| Page agreement (`deck-test.html`) | the chip name and number equal the def's for 204 of 204 card × key pairs |

The 20 name expectations:
- `lydian-four`: Db major → Dbmaj9, Gbmaj7#11; F major → Fmaj9, Bbmaj7#11.
- `gospel-five-over-four`: D major → Gmaj9, A11/G, D/F#, Dmaj9.
- `lament-bass`: Eb major → Cm11, Cm11/Bb, Cm11/Ab, Cm11/G.
- `borrowed-b6-b7-home`: F major → Dbmaj9, Ebmaj9, Fmaj9.
- `dorian-vamp`: E minor → Em11, A13.
- `sunrise-ending`, first three slots: F major → Fm11, Fm11, Dbmaj7#11.

### A5 Recording stays clean with the jam view off (J9, `jam_verify.mjs`)

"Off" means the jam view is not duet: `auto` during REC, or `glass`.

**Setup.**
- `?jam=auto`, with the receipt harness stepping frames on a frozen clock.
- Scripted Daniel MIDI: 20 s through `__piano.midiMessage`.
- A Loop on `lydian-four`, then a Try with ghosts, a Play overlay and a remote hover.
- REC for 5 s.
- Control: the identical script with no run and no cues.

| Measure | Pass |
|---|---|
| Recorded video: 300 frames decoded from the recorder's file, against the control take | per-channel MAE = 0.0 on 300 of 300 frames |
| Moonlight pixels (within ΔE 6 of `#C8DCFF`) present in the take but not in the control | 0 |
| The recorder's audio graph | 0 connections from Claude's voice (`__piano.jam.stats().recorderSources` has no `claude`) |
| Recorded audio track, with a test oscillator as the input, nulled against the control | residual ≤ −90 dBFS |
| The glass during REC | ghost pixels > 0 (Claude's things moved, not vanished) |
| `?jam=glass` outside REC | canvas frames equal the control (MAE 0.0) |
| After REC stops in `auto` | within 300 ms Claude's keys are back on the stage (the frame differs from the control) |

### A6 Honesty (J9)

**Setup.** A 60 s Loop, a Hear me, a `card play` and a remote `pianocue play`, with 300 scripted notes of Daniel's.

**Pass:**
- After `log.flush()`, the practice log holds exactly Daniel's events: 300 on, 300 off, and his pedal events. There are
  0 extra events.
- The `stats().keyRaw` sequence is identical to the control run's.
- `stats().sounding` never contains a note only Claude or a replay holds (0 samples at 60 Hz).
- Rarity scorer inputs from Claude or replay notes: 0.
- 0 events of any new kind are sent.

### A7 Courtesy gate (J9)

**Setup.** Scripted playing: a note-on every 250 ms for 25 s. `pianocue loop start lydian-four` arrives at t = 2 s.

**Pass:**
- 0 Claude note-ons from 2 s to 22 s.
- The knock is visible at 22 s ± 0.25 s.
- Enter at 24 s calls `launch` with an epoch ≥ now + 150 ms, and the count-in starts on it.
- A hover arriving while he plays appears by 8.4 s.
- A `clear` during a knock acts within 50 ms.
- `--now` starts the count-in without waiting.
- A knock left 60 s stops its run with `expired`, and the card shows in Tonight.

### A8 Deck layout and keys (J8 test page, then J9 on the page)

**Setup.** Viewports 1280×900, 1920×1080 and 2560×1440; framings 9:16 and 16:9; windowed and fullscreen (CDP).

| Measure | Pass |
|---|---|
| 9:16 at 2560 wide | the deck overlays; the canvas rect changes by 0 px |
| 16:9 at 1920 wide | the deck docks; canvas width = stage width − 380 ± 1 px |
| During REC | the canvas rect changes by 0 px on deck open and close |
| Fullscreen | deck, pill and glass are descendants of the fullscreen element |
| Toast | its rect never intersects the deck's |
| A new card arriving while he plays | card order and scroll offset under the pointer unchanged (0 px) until his next rest |
| The 10 shortcut keys in 8.7 | each triggers its action and changes `stats().noteOns` by 0 |
| The 32 `KEYMAP` keys | still play (32 of 32) |
| Space | still sustains |

### A9 Glass alignment (J8 maths, J9 on the page)

**Setup.** Ghosts on 12 keys (6 white, 6 black) in both framings, at DPR 1 and 1.5, on a still frame and during a
camera follow pan.

**Pass:** every glass rim centroid within 1.5 CSS px of the projected 3D key-top centroid, and within 1.5 px of the
stage ghost mesh in a snapshot compare.

### A10 Two tabs, stream loss, restart (J9)

| Measure | Pass |
|---|---|
| Two listening tabs, one run | total strikes across tabs = one tab's planned strikes |
| Owner moves to tab B on input | within 1 bar; 0 doubled strikes; no silent gap longer than 1 bar |
| Stream cut at a proxy | the page stops after 2 bars ± 1 beat; the ack says `stream-lost` |
| Server restart | the run closes with `server-restart`; `jam status` shows no run |

### A11 Riff analysis on a synthetic jam (J4, `tests/test_arsenal_practice_riff.py`)

**Fixture `riff_lydian_l1`.**
- Run: `lydian-four` in Eb at 66 bpm, 8 passes (16 bars, 58.18 s), with an L1 ack.
- Session events with these planted things:
  - 9 D5 top-line notes over slot 2 (the #11);
  - 1 held rub (Ab4 over Ebmaj9 for 2 beats, pass 3, bar 1, beat 1);
  - 1 passing Ab4 (0.5 beat on the &2 of pass 5, stepping to G4);
  - 3 slide-ins (F#4 for 0.25 beat into G4, in passes 2, 4 and 6);
  - 2 outside notes (E5 over Abmaj7#11 for 1 beat in pass 7; A4 over Ebmaj9 for 1 beat in pass 8);
  - 5 anticipations (a next-chord tone 200 ms before a change);
  - 8 two-bar phrases, 6 with pickups;
  - per-pass velocity medians 40, 44, 48, 52, 56, 52, 48, 44;
  - pedal down for 80% of the run.

| Measure | Pass |
|---|---|
| Planted counts | every one reported exactly: 9 `#11` labels on slot 2, 1 rub, 1 passing, 3 slide-ins (`from below`), 2 outside, 5 anticipations, 8 phrases with 6 pickups, the 8 velocity medians |
| Times | every planted time within ± 10 ms |
| Alignment | method L1, `error_ms` ≤ 2 |
| Mode naming gate | `Ab Lydian` named on slot 2 (D weight ≥ 5%); in a twin fixture with D at 4% of the weight, `named: false` and no T2 point |
| Transposition invariance | the fixture shifted to all 12 keys gives identical class counts and talking-point types (12 of 12) |
| Free play (the same notes, no run) | 0 anticipations, no T14, exit 0 |
| Buffered session at L4 | exit 2, naming `opened_at_client` |
| Loopback fixture (Claude's notes mirrored into the log within 10 ms) | `suspected: true`, `mirrored_share` ≥ 0.9; the clean fixture gives `false` and 0.0 |
| Wording guard over 12 fixtures' rendered text | 0 forbidden tokens; 100% of numbers in sentences equal a JSON field |
| Speed | ≤ 3 s for a synthetic 30-minute session with 4 runs |

### A12 End to end (J9, own server 8798)

1. `deck seed` installs 17 cards.
2. `pianocue loop start lydian-four --now`: the headless page plays and acks at L1.
3. `loop tempo +4` lands on the announced bar.
4. `loop stop`.
5. `practice riff latest` over the scripted notes played during the run: exit 0, alignment L1.
6. `template save-last` makes a Kept card that appears in the page's deck within 1 s through the `deck` event.

---

## 15. Questions for Daniel (three, each with a recommended default)

1. **Should Claude's backing be in your recordings?**
   - **Recommended: no, for now.** While you practise you see and hear the duet. The moment you press REC, the take is
     only you: Claude's keys move to a private layer only you can see, and its sound is kept out of the recording.
     Duet videos can come later as a setting.
   - One thing to tell us: if Chrome plays through your Focusrite and you record its Loopback, Claude's sound would
     still reach the recording that way.
2. **Which sound should Claude play with?**
   - **Recommended: its own soft built-in voice for now.** You can always tell whose notes are whose, and nothing needs
     installing.
   - Playing through FL Studio / Kontakt (same sound world, lands in your mix) needs a Microsoft MIDI loopback download
     that you would approve later.
3. **When you press Try, should the loop keep time or wait for you?**
   - **Recommended: keep time.** One bar of count-in, then the chords move on the beat whether or not you have found
     them yet.
   - The alternative is "wait for me": each chord stays until your hands find it. That can be added next if you want it.

---

## 16. For Vandor, not for Daniel

- **Privacy before commit.** `design-data.md` (sections 2.1, 8, 10, 11) and `design-music.md` (sections 1.1, 10)
  contain session ids and transcriptions. Strip them, or keep this folder uncommitted, before any push. This spec
  contains none.
- **The FL lane** proposes `arsenal/jam.py` with its own `/api/jam/*` SSE. This spec takes the `arsenal/jam/` package
  and the single stream instead (C4, C22); the FL plan's Option A and Route B/C slot in as v2 backends. Tell the FL
  lane before it builds.
- **Pre-existing, not introduced here:** PIANO-V2-SPEC gives `S` to the scheme picker in piano-next, while `KeyS` is
  C#3 in `KEYMAP`.
- **Cue direct verbs** (`pianocue play`, `progression`) bypass the courtesy gate in v1 (8.9). If that annoys Daniel,
  give them a `pending` path in v2.
- **Not measured in this design:** whether `--mute-audio` freezes `getOutputTimestamp` (A1c has a fallback); the
  16:9 trail-foot height (a v2 strip question only); how the band voicer's ring runtime scales at 16 slots (MUSIC
  estimates 512,000 move evaluations for 8 slots, well under a second; J1 measures).

