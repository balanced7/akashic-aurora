# Piano jam: cards, loops, verbs and the seed deck (data lane)

Status: design only, 2026-09-14 night. No code was edited and no server or browser was started. Sibling lanes own
the deck panel and the in-page loop engine. This file owns the card format, storage, the HTTP routes, the events on the
existing stream, the jam timeline and its alignment with the practice log, the CLI verbs, the `practice riff` analysis
and the seed deck.

Daniel, verbatim, tonight:

> "I want us to be able to play in this space, can you make verbs so you can play chord progressions or show loops of
> chords for me to try, I can then riff on that and play with it and we can discuss it"
>
> "so I can click and hear concepts you are describing and have a visual for them, we can make chord templates"
>
> Earlier: "ooooh, can we make a verb for you to be able to play a chord you are curious about or hovering it in the
> viewer?" / "We could have a lot of fun with this!" / "I just play it by feel" / "I know a little bit but not much
> >__< this is intuition and memory"

---

## 0. The shape in one paragraph

A **card** is a small JSON file with these parts:
- chords written as Nashville numbers against a default key, so it plays in any key
- optional exact notes and a tempo
- three short plain-words lines: what it is, why it matters, what to try
- links to the moments in Daniel's practice log where he played it

The **deck** is the folder of cards.

Two ways to play a card:
- **try**: Claude (from the CLI) or Daniel (from the page) plays it once, as a sequence cue on the existing channel.
- **loop**: the card becomes a **run**. The page keeps time for it, and changes (tempo, next card, stop) land on bar lines.

Every run the server starts, including one-shot tries, is written to a **jam timeline** with wall-clock and
page-clock anchors. `practice riff` can then line the loop up with what Daniel played and talk about it. Changes to the
deck and to the running loop travel as two new named events, `deck` and `jam`, on the `/api/piano/cues` stream the page
already holds open.

---

## 1. What the code says (findings that shape this design)

| # | Finding | Evidence | Consequence |
| --- | --- | --- | --- |
| F1 | The server only answers GET, HEAD and POST. | `arsenal/serve.py` `do_HEAD`, `do_GET`, `do_POST` (lines 200-207); the house style is `POST .../events`, `POST .../close` | Card update and delete are `POST .../update` and `POST .../delete`, not PUT/DELETE. |
| F2 | The cue hub writes `event: cue` into every frame, and the page client listens only for `cue`. | `pianocue.py` `CueHub.frame` (200-202); `cues.js` `addEventListener("cue")` (154) | New named events (`deck`, `jam`) are invisible to today's page: adding them is backward compatible. One id sequence across all kinds keeps Last-Event-ID working. |
| F3 | Cues reject unknown fields, and `source` must be `claude` or `replay`, in both mirrors. | `pianocue.py` `SOURCES`, `CUE_KEYS` (43, 50); `cues.js` `SOURCES` (24) | A new `jam` source must land in both mirrors in one release. Anything sent to a page that may predate it keeps `source: "claude"`. |
| F4 | A fresh EventSource gets no backlog. A reconnect gets at most the last 50 frames younger than 10 s. | `CueHub.subscribe` (214-233) | Events are hints, state endpoints are truth. The page re-reads `GET /api/piano/deck` and `GET /api/piano/jam` on every (re)open. |
| F5 | THEORY has no `maj9#11`, `maj13#11` or `sus2(#11)` template. | `piano.js` `TEMPLATES` (76-113); spectacle spec section 4 already notes "TEMPLATES has no maj9#11" | Daniel's most-played colour is shown under another name. Bridge, checked tonight: `4maj9#11` in Eb, spread voicing, reads **Bb13/Ab (5^13/4)**. His full Abmaj13#11 (Ab Eb G C D F Bb) reads **Cm11/Ab**. Cards cache what the page will call each chord (`page_reads`). |
| F6 | Practice-log `t_ms` counts from the page clock at his first note. The client wall time is stored only for buffered sessions. For those, the server `opened_at` can be an hour late. | `log.js` `begin` (293-308), `opened_at_client` sent only when `rec.buffered` (440); session S1 has `opened_at_client` 04:01:14.454Z and `opened_at` 05:01:20.608Z | Alignment needs a ladder (section 7.3) and two additive meta fields on the session open. No new event kinds. |
| F7 | "all inputs except DAW ports" binds every MIDI input ranked above 0. A loopMIDI port ranks 1. | `piano.js` `midiRank` (1629-1635), `bindMidi` (1680) | If Claude's MIDI out goes to a loopMIDI port the page also listens to, the loop re-enters as Daniel's playing and lands in the practice log. That needs a hard rule (6.8) and a guard in `practice riff` (9.4). |
| F8 | `practice.py` is read-only by design. Today its verbs are `list`, `windows`, `keys`, `harmony` and `analyze`. | `practice.py` `main` (1428) | `practice riff` goes there and writes nothing to the log. It can save a report under `state/arsenal/jam/riffs/`. |
| F9 | The voicing bridge is node and reads `piano.js` from disk. The page cannot run it. | `pianocue_voicing.mjs` (30-38) | The server resolves a card into notes (one node call, cached) and sends the page finished notes. |
| F10 | Every listening page plays every cue. | `CueHub.publish` fans out to all | A loop open in two tabs would sound twice. Loops use a sound-owner lease (6.7). |

---

## 2. Cards

### 2.1 A whole card, as stored (the seed card `lydian-four`)

```json
{
  "api": "arsenal.jam.card/v0",
  "id": "lydian-four",
  "rev": 1,
  "title": "The Lydian 4",
  "kind": "loop",
  "key": "Eb major",
  "also_in": ["Db major", "F major"],
  "chords": [
    {"n": "1maj9", "beats": 4},
    {"n": "4maj9#11", "beats": 4}
  ],
  "variants": [],
  "voicing": {"style": "spread", "voice_lead": false, "octave": null},
  "tempo": {"bpm": 66, "beats_per_bar": 4, "feel": "straight"},
  "bars": 2,
  "playback": {"velocity": 48, "arpeggio_ms": 0, "hold": "legato", "count": null},
  "style": "slow pad, pedal-down feel",
  "explanation": "The 4 chord (Ab) with a D on top. D is the #11, a raised 4th above Ab, and it is already a note of Eb major, so it shines without sounding wrong.",
  "why": "It is your signature colour: the analyzer named a Lydian 4 in 80 windows across tonight's four sessions.",
  "try": "Keep the loop going. On the Ab bar, move your top finger between C and D: C is the plain chord, D is the shimmer. Then try D over the Eb bar too (there it is the major 7th).",
  "listen_for": "the moment D arrives on top of the Ab chord",
  "checks": [
    {"id": "sharp-eleven", "slot": 1, "role": "#11", "want": "present", "say": "you touched D, the #11 of Ab"}
  ],
  "tags": ["signature", "lydian", "colour"],
  "moments": [
    {"session": "S4", "at": "0:00", "until": "0:22", "label": "the same move in Db: Gbmaj9, Gbmaj13, Gbmaj13#11"},
    {"session": "S3", "at": "20:22", "until": "20:30", "label": "Abmaj9#11 to Abmaj13#11 in Eb"},
    {"session": "S2", "at": "3:49", "until": "3:58", "label": "Bb11/Ab, Abmaj9#11, Abmaj7, Abmaj9"}
  ],
  "related": ["one-note-apart", "blooming-chord", "gospel-five-over-four"],
  "page_reads": [
    {"variant": null, "slot": 0, "key": "Eb major", "voicing": "spread", "notes": [39, 50, 55, 65, 70],
     "name": "Ebmaj9", "number": "1maj9", "match": "exact"},
    {"variant": null, "slot": 1, "key": "Eb major", "voicing": "spread", "notes": [44, 55, 60, 70, 74],
     "name": "Bb13/Ab", "number": "5^13/4", "match": "equivalent",
     "note": "the page has no name for maj9#11 yet, so it reads these notes as Bb13/Ab"}
  ],
  "source": {"kind": "seed", "seed_version": 1},
  "created_by": "claude",
  "created_at": "2026-09-14T06:10:00.000+00:00",
  "updated_by": "claude",
  "updated_at": "2026-09-14T06:10:00.000+00:00"
}
```

### 2.2 Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `api` | `"arsenal.jam.card/v0"` | yes | Format version. |
| `id` | `^[a-z0-9][a-z0-9-]{0,47}$` | yes | Seeds use readable slugs. Cards saved from the page get `t-YYYYMMDD-HHMMSS-xxxx`. The CLI accepts a unique prefix. |
| `rev` | int >= 1 | server | Goes up by one on every write. Updates and deletes must send `if_rev` (409 when it moved). |
| `title` | string <= 80 | yes | A name, not a sentence. |
| `kind` | `chord` \| `progression` \| `loop` \| `concept` \| `moment` | yes | See 2.5. |
| `key` | key name, e.g. `"Eb major"`, `"C# minor"` (as `nashville.js parseKey`) | yes | The default key. Every number is relative to it. Spelling is kept, so `"Gb major"` spells flats. |
| `also_in` | [key name] <= 6 | no | Keys Daniel uses where the card is worth trying. A suggestion only. |
| `chords` | [ChordItem] 1..64 | yes (except a `concept` with variants) | The main line. See 2.3. |
| `variants` | [Variant] <= 6 | no | Named alternative lines (a / b / c), for comparisons. See 2.4. |
| `voicing` | `{style, voice_lead, octave}` | no (default `spread`, false, null) | `style` is one of the bridge's `close` \| `open` \| `spread` \| `drop2` \| `shell`. A chord with exact `notes` ignores it. |
| `tempo` | `{bpm 30..240, beats_per_bar 2..12, feel}` | no (66, 4, `"straight"`) | `feel` is a word for the page and the riff (`straight`, `rubato`, `half-time`). Playback is always straight time. |
| `bars` | int | no | The declared length. It must be >= total beats / `beats_per_bar`. The remainder is a rest at the end. |
| `playback` | `{velocity 1..127, arpeggio_ms 0..2000, hold, count}` | no (48, 0, `"legato"`, null) | Velocity 48 sits under Daniel, whose captured moments tonight strike between velocity 18 and 79. `hold` is `legato` (sound to the next chord plus 80 ms), `detached` (length minus 40 ms, as `progression`) or a number of beats. `count` is the loop's cycle count (null means until stopped). |
| `style` | string <= 80 | no | Plain words for the sound ("felt pad", "gospel church"). |
| `explanation` | string <= 400 | yes | What it is, in plain words, 1 to 3 lines. |
| `why` | string <= 300 | yes | Why it matters to Daniel's music. |
| `try` | string <= 300 | yes | One concrete thing to play over it. |
| `listen_for` | string <= 160 | no | One thing to notice. |
| `checks` | [Check] <= 8 | no | What `practice riff` looks for (2.8). |
| `tags` | [`^[a-z0-9-]{1,24}$`] <= 12 | no | For filtering. Seeds use `signature`, `growth-edge`, `borrowed`, `bass`, `key-change`, ... |
| `moments` | [Moment] <= 12 | no | `{session, at "m:ss", until "m:ss" or null, label <= 120}`. `session` matches `SESSION_PATTERN`. `moment` cards need at least one. |
| `replay` | `{session, at, seconds, speed}` | `moment` cards | The arguments `pianocue replay` takes. |
| `related` | [card id] <= 8 | no | Links between cards (not checked for existence: a card may be deleted). |
| `page_reads` | [PageRead] | server | Cached: what the page names each chord in the default key and voicing. Recomputed on every write and by `deck seed`. Advisory. |
| `source` | `{kind, ...}` | server | `seed` \| `claude` \| `saved-live` \| `saved-from-moment` \| `edit`, plus provenance (2.10). |
| `created_by` | `claude` \| `daniel` | yes | Who authored the musical content. A voicing captured from Daniel's playing is `daniel`, even when Claude ran the verb; `source.saved_by` records who saved it. |
| `created_at`, `updated_at` | ISO 8601 UTC with ms | server | Same format as `performance._now_iso`. |
| `updated_by` | `claude` \| `daniel` | server | From the route's `by` (the page sends `daniel`, the CLI `claude`). |
| `favorite`, `archived` | bool | no | For the deck panel. An archived card stays on disk but is hidden. |

### 2.3 Chord items

A `chords` (or variant) list holds three kinds of item:

| Item | Shape | Meaning |
| --- | --- | --- |
| Chord | `{"n": "4maj9#11", "beats": 4, ...}` | `n` is a Nashville number in `nashville.js` text form (`5^7sus4/1`, `2-^7` and `2m7` are both accepted, `b6maj9`, `#4m7/6`). It is relative to the current key (the card key until a key item). |
| Key change | `{"key": "6 major"}` | From here on, numbers are in a new key whose tonic is the given degree **of the card key**, not of the previous section, so the meaning never depends on order. `"b3 major"` in Eb minor is Gb major; `"1 major"` in Eb minor is Eb major. |
| Rest | `{"rest": 2}` | Silence for 2 beats. |

Optional fields on a chord item:

| Field | Type | Meaning |
| --- | --- | --- |
| `beats` | number > 0, multiple of 0.5, <= 64 | Default 4. |
| `notes` | [MIDI 21..108] <= 24 | An exact voicing, in the card's default-key rendition. When present, the sound is these notes and `voicing` is ignored. `n` stays as the label, and may be null when the notes have no number (a cluster the page names by its letters). |
| `voicing` | style | Overrides the card voicing for this chord. |
| `vel` | 1..127 | Overrides `playback.velocity`. |
| `arp_ms` | 0..2000 | A bottom-up roll. |
| `hold` | as `playback.hold` | |
| `say` | string <= 120 | A caption line while this chord sounds (the cue `detail`). |

The CLI writes the same list as one string, extending `pianocue progression`'s `item:beats` form:

```
"1maj9:4 | 4maj9#11:4"
"1add9:4 | 4maj13:4 | 5^6:4 | [6 major] | 1add9:4 | 4maj13:4 | 1maj9:8"
"4sus2:4 | rest:2 | 4add9:4"
```

Exact notes are given per slot: `--notes-for 1="Ab2 Eb3 G3 C4 D4 F4 Bb4"` (1-based slot numbers, notes as the bridge
reads them).

### 2.4 Variants

```json
{"id": "b", "label": "pull", "key": "b7 major", "chords": [...], "tempo": {"bpm": 60}, "say": "the 3rd is back"}
```

`id` is `a`..`f`. `key` is optional and written as a degree of the card key, like a key-change item, so a variant
transposes with its card. `tempo` overrides only the fields it gives. `try` plays one variant or all of them, in order,
with a bar of rest between. `loop next` on a concept card steps through its variants.

### 2.5 Kinds

| Kind | Holds | `try` does | `loop start` does |
| --- | --- | --- | --- |
| `chord` | one chord item (a template) | plays it for `beats` (hovers with `--hover`) | holds it, re-striking every `beats` |
| `progression` | a line that has an end | plays it once | loops it anyway (asked for) |
| `loop` | a line meant to cycle, usually 2 to 4 bars | plays one cycle | loops it (the intended use) |
| `concept` | `variants` (optionally also `chords`) | plays a, b, c in order with captions | loops variant a; `loop next` moves to b, c |
| `moment` | `replay` plus a transcribed `chords` line | `pianocue replay` of the moment (his own notes) | loops the transcribed line |

### 2.6 Transposing

Resolving a card in key K with voicing V (server-side, cached by `(id, rev, K, V, variant)`):

1. Split the line at key items. Each section's key is the card key moved to K, then moved by the section's degree.
   Spelling follows the degree: `6 major` of Gb major is Eb major, not D# major.
2. Numbers: one bridge call per section, `{items, key, voicing, voice_lead}`. That gives names, notes and `roundtrip`.
   Voice leading restarts after a key change.
3. Exact notes: shift every note by `s = mod(pc(K tonic) - pc(card tonic) + 6, 12) - 6` (-6..+5, the nearest move, so
   the register is kept). If the lowest note is below E1 (28), add 12. If the highest is above G7 (103), subtract 12.
   Notes still off the keyboard are dropped, with a warning. Then one bridge call in notes mode records what the page
   reads.
4. Minor keys use `nashville.js`'s default tonic numbering (Eb minor: Abm = 4m, Gb = b3, Cb = b6, Db = b7).

### 2.7 `page_reads`

`page_reads` exists because of F5. The caption chip shows the card's own name (`Abmaj9#11`). The page's chord chip and
Nashville row show what `Theory.detect` reads (`Bb13/Ab`, `5^13/4`). The deck panel shows "the page calls this Bb13/Ab:
same notes, another name" whenever `match` is not `exact` or `enharmonic`. A card is never refused for a mismatch; the
CLI prints the reading as a note.

### 2.8 Checks (read by `practice riff`)

```json
{"id": "third-of-five", "variant": "c", "slot": 2, "role": "3", "relative_to": "root", "want": "present", "say": "you played D, the 3rd of Bb7"}
```

- `role` is an interval, written as in `practice.py`'s tension names: `1`, `b3`, `3`, `4`, `#4`, `5`, `b6`, `6`, `b7`,
  `7`, `b9`, `9`, `#9`, `11`, `#11`, `b13`, `13`.
- `relative_to` is `root` (the slot chord's root, the default) or `bass` (the slot's bass note, for slash chords such as
  Bbm11/Gb, where C is the 9th of Bb and also the #11 over Gb).
- `slot` is a chord item's position, counted from 0 as in `def.slots`, with key-change and rest items not counted. The
  CLI's `--notes-for` and the seed-deck text count chords from 1.
- `want` is `present` (heard in at least one cycle), `landing` (his first note after the change has that role) or
  `absent`.
- `say` is the sentence the riff report uses when the check passes.

### 2.9 Validation

- Enforced in Python at the route:
  - the shape and limits above
  - a whole card <= 64 KB
  - numbers against the syntax `^(#{1,2}|b{1,2})?[1-7](.*?)(/(#{1,2}|b{1,2})?[1-7])?$`
  - key items against `^(#{1,2}|b{1,2})?[1-7] (major|minor)$`
  - keys through `arsenal.nashville.parse_key`
- The meaning of each number (can its suffix be read) is checked by one bridge call on create and update. The bridge's
  own message comes back as the 400 (`cannot read the chord suffix "maj9##11"`).
- Unknown top-level fields are refused, as `validate_cue` does, so typos surface.

### 2.10 Templates Daniel saves

**From the page ("save this voicing").** The UI lane owns the button; this is its payload and its rule.

The page captures, at the click:
- `notes`: Daniel's own sounding notes, from the page's sounding map with cue and jam notes excluded.
  - If at least 3 keys are held down, take the held keys.
  - Otherwise take the sounding notes struck in the last 4 s. That keeps the pedal cloud but drops older tails.
  - Keep at most 16: the lowest note plus the 15 most recent.
- `name`, `number`, `key`, `key_conf`, `locked`: from the chord chip and key tracker at that moment.
- The page clock and log timebase (7.5), so the saved chord can be found in the log later.

```
POST /api/piano/deck/templates
{"by": "daniel",
 "capture": {"notes": [42, 49, 54, 56, 58, 61, 65, 70, 75, 77, 80, 84], "name": "Gb Db Ab Bb F Eb C", "number": null,
             "key": "Db major", "key_conf": "sure", "locked": false, "title": null,
             "page_id": "p-7f3a", "perf_ms": 8123456.2,
             "log": {"local": "mu1x...", "session": "S4", "t0_perf_ms": 8118000.0}}}
-> 200 {"id": "t-20260914-012546-9c1e", "rev": 1, "card": {...}}
```

The server builds a `chord` card:
- `key`: the page key. With no key, the key of the chord root in major, with `source.number_from: "root"`.
- `chords: [{"n": <number or null>, "beats": 4, "notes": <notes>}]`
- `title`: the name plus the time ("Gbmaj13#11, 01:25"). A cluster uses its letters.
- `source`: `{"kind": "saved-live", "saved_by": "daniel", "page_name", "page_number", "key_conf", "log_session",
  "log_t_ms"}`
- `moments`: `[{session, at}]` when the log timebase is known.
- `created_by`: `daniel`

It then publishes a `deck` event.

**From a moment in the log.** `pianocue template save-from-moment` (8.6) runs the same build from `practice.analyze`:

1. Take the harmonic window containing `at`. With `--until`, take the longest window overlapping the range.
2. The notes are the distinct MIDI notes heard for at least `CHORD_SHARE` (0.5) of the window. That is the chord-set rule
   applied per MIDI note instead of per pitch class. Drop notes below the window's main bass note. Keep at most 16.
3. `n` is the window's number in its key area (the "reading" name when there is one). `page_reads` comes from the live
   chord events in that window.

Example, from tonight's log: `template save-from-moment S1 2:40` should yield
`5^7sus4/1` in Eb major with notes **Eb2 Eb3 Eb4 F4 Ab4 Bb4**. Those are the notes sounding at 2:40 by `_note_spans`,
checked tonight. The bridge reads them as Bb7sus4/Eb. The 0.5 share rule could differ by a passing note; the builder's
test pins it.

---

## 3. Storage: `state/arsenal/jam/` (git-ignored by `state/*`)

```
state/arsenal/jam/
  deck/
    deck.json                      {"api": "arsenal.jam.deck/v0", "rev": 17, "order": ["lydian-four", ...]}
    cards/<id>.json                one card per file (2.1)
    trash/<id>.rev<N>.<utc>.json   deleted cards: rm moves them here, restore moves them back
  seed/
    seed-deck-v1.json              {"api": "arsenal.jam.seed/v0", "seed_version": 1, "cards": [...]} (section 10)
  runs/
    <run>/run.json                 one run header (7.1)
    <run>/events.jsonl             its append-only timeline (7.2)
  riffs/
    <run>.json                     saved `practice riff --save` reports
```

The resolve cache (2.6) is in memory only, keyed `(id, rev, key, voicing, variant)`, and dies with the server.

Rules:
- **One writer.** While the server runs, only the server writes the deck, so events always fan out. The CLI writes
  through the routes. It writes the files directly only when no server answers on the port, and then says so
  (`--offline` is implied and printed).
- **Atomic.** Every JSON file is written to `<name>.tmp` and then `replace`d, as `PerformanceStore._write_text` does.
  `deck.json`'s `rev` goes up with every card write and every `order` write. The deck is small (tens of cards), so
  `list` scans the folder.
- **Nothing is hard-deleted.** `card rm` moves to `trash/` (the "ask before deleting functionality" doctrine applied to
  data), `card restore` brings back the newest trashed revision, and emptying the trash is a manual act. Runs and riffs
  are kept. A later `pianocue jam prune --older-than DAYS --yes` can mirror `performance prune`, but it is not part of
  this design.
- **Run ids** use the practice-log pattern, `YYYYMMDD-HHMMSS-xxxxxxxx` (`SESSION_PATTERN`), so the same validators and
  sorting apply.
- **Privacy.** Cards carry session ids, times and transcriptions of Daniel's playing. That is practice data, so the seed
  deck lives under `state/` like the log (PIANO-V2-SPEC "Privacy"). See open question Q5 about this design file itself.

---

## 4. HTTP routes (added to `arsenal/serve.py`)

### 4.1 Conventions

- Everything is JSON, with the existing `_json`/`_read_json` helpers. The body cap is `MAX_CUE_BODY` (2 MB).
- The origin check is the one `_cue_post` uses on every write: 403 unless `Origin` is absent, `127.0.0.1` or `localhost`.
- Every write carries `"by": "claude" | "daniel"` (default `claude`).
- Status codes: 400 malformed (the message names the field); 404 `no card <id>` / `no run <id>`; 409 `rev changed` or
  `version changed`, with the current value in the body; 503 `the voicing bridge is unavailable (node not on PATH)`,
  but only on routes that must voice.
- These routes need the practice-log store only for alignment. `--no-performance-log` keeps the deck and jam routes on.

### 4.2 Deck

| Method and path | Body | Answer |
| --- | --- | --- |
| `GET /api/piano/deck?kind=&tag=&by=&archived=0` | | `{api, rev, order, cards: [Summary]}`. `Summary = {id, rev, title, kind, key, numbers: "1maj9 4maj9#11", variants: ["a","b"], tags, created_by, updated_at, favorite, runs}` (`runs` counted from the timeline index). |
| `GET /api/piano/deck/cards/<id>` | | `{card}` |
| `GET /api/piano/deck/cards/<id>/resolve?key=Db%20major&voicing=spread&variant=b` | | `{resolved: Def}` (6.2): the notes the page plays, with names, numbers and page reads. |
| `POST /api/piano/deck/cards` | `{card, by}` | `{id, rev, card, warnings}`; 409 if the id exists |
| `POST /api/piano/deck/cards/<id>/update` | `{patch, if_rev, by}` | `{id, rev, card, warnings}`. `patch` is a JSON merge patch (RFC 7386) on the card; `api`, `id`, `rev`, `created_*` and `page_reads` cannot be patched. |
| `POST /api/piano/deck/cards/<id>/delete` | `{if_rev, by}` | `{id, trashed: "trash/<file>"}` |
| `POST /api/piano/deck/cards/<id>/restore` | `{by}` | `{id, rev, card}`: the newest trashed revision, rev + 1 |
| `POST /api/piano/deck/templates` | `{capture, by}` | `{id, rev, card}` (2.10) |
| `POST /api/piano/deck/order` | `{order, if_rev, by}` | `{rev}`. Ids not listed keep their relative order after the listed ones. |
| `POST /api/piano/deck/seed` | `{update: false, dry_run: false, by}` | `{installed: [...], updated: [...], kept: [...]}` (8.2) |

### 4.3 Jam

| Method and path | Body | Answer |
| --- | --- | --- |
| `GET /api/piano/jam` | | `{run: RunHeader or null, now_epoch_ms, position: {bar, beat, cycle, slot, version} or null, owner: {page_id, lease_until_epoch_ms} or null, pages: [{page_id, caps, since}]}` |
| `POST /api/piano/jam/try` | `{card_id or chords, key?, variant?, bpm?, voicing?, hover?, arp_ms?, velocity?, by}` | `{run, cue_id, listeners, def}`. Resolves, publishes one `sequence` cue (source `claude`, label = title, detail = `"b: pull, Eb major"`), and records a run with `mode: "once"`. |
| `POST /api/piano/jam/start` | `{card_id or chords, key?, variant?, bpm?, voicing?, voice_lead?, count?, velocity?, arp_ms?, hover?, sound?, display?, lead_ms? (default 800), by}` | `{run, version: 1, start_epoch_ms, def, jam_pages, listeners, fallback: null or "cue-loop"}`. Starting while a run is active stops the old one at once (`reason: "replaced"`). |
| `POST /api/piano/jam/runs/<run>/control` | `{op: "tempo" or "next" or "stop" or "mute" or "unmute", bpm?, card_id?, chords?, variant?, key?, at: "beat" or "bar" or "loop" or "now", if_version?, by}` | `{version, effective_bar, epoch_ms}`. 409 if `if_version` is stale. 400 for `tempo`/`next` on a `cue-loop` fallback run. |
| `POST /api/piano/jam/runs/<run>/ack` | `Ack` (7.2) | `{ok: true}`. Idempotent per `(page_id, version)`. |
| `POST /api/piano/jam/owner` | `{page_id, claim: true or false}` | `{owner}` (6.7) |
| `POST /api/piano/jam/mark` | `{text <= 200, run?, epoch_ms?, by}` | `{run, seq}`: a note in the timeline ("he found D on the Bb7 bar") |
| `GET /api/piano/jam/runs?limit=20` | | `{runs: [RunHeader]}`, newest first |
| `GET /api/piano/jam/runs/<run>` | | `{run: RunHeader, events: [...]}` |

---

## 5. Events on the existing stream

### 5.1 Frames

One id sequence and one ring buffer, shared by all three kinds. The `cue` frame keeps its exact bytes
(`test_frame_bytes_are_exactly_the_protocol` pins them).

```
id: 41
event: cue
data: {"id":41,"cue":{...},"sent_at":1789365129012}

id: 42
event: deck
data: {"id":42,"deck":{"op":"upsert","card_id":"lydian-four","rev":2,"deck_rev":18,"by":"daniel","summary":{...}},"sent_at":1789365130100}

id: 43
event: jam
data: {"id":43,"jam":{"op":"start","run":"20260914-015210-3fa9c1d2","version":1,"effective_bar":0,"epoch_ms":1789365129812,"segments":[...],"def":{...},"owner":null},"sent_at":1789365129012}
```

- `deck` ops: `upsert`, `delete`, `restore`, `order`, `seed`. Pages apply `upsert` only when `rev` is newer than their copy.
- `jam` ops:
  - `start`, `change`, `stop`: carry `version`, `effective_bar`, `epoch_ms`, the full `segments`, and `def` whenever the
    definition changed
  - `owner`: carries `owner`
  - `mark`: carries `text`
  - Pages ignore any `version` at or below the one they applied.

### 5.2 Hub change (`pianocue.py`)

- `publish(cue)` stays and becomes `publish_event("cue", cue)`.
- `publish_event(kind, payload)` writes `{"id", kind: payload, "sent_at"}` under the same lock and ring. `frame()` keeps
  its current bytes for `cue`.
- `subscribe(last_event_id, caps=(), page_id=None)` records the listener's capabilities, and `status()` adds
  `{"caps": {"jam1": n, "deck1": n}}`.
- The page announces its capabilities in the stream URL: `/api/piano/cues?caps=jam1,deck1&page=p-7f3a`. `_cue_stream`
  already owns the query string.

### 5.3 Page rules (for the integration lane)

- **State is truth.** On every EventSource `open` (first connect and every reconnect), read `GET /api/piano/deck` when the
  local `deck_rev` is older, and `GET /api/piano/jam`. Events only say "something changed".
- **No stale drop for `deck` and `jam`.** `cues.js` drops cues older than 10 s. Deck events are idempotent by `rev`. Jam
  events carry absolute epochs, so a late one is placed by computing the current bar.
- **One connection.** `createCueClient` gains an additive option `events: { deck: fn, jam: fn }` that registers extra
  named listeners on the same EventSource, with the same dedupe by `id:sent_at`.

### 5.4 Compatibility

- A page from before this change never sees `deck` or `jam` (F2).
- `loop start` checks `status().caps.jam1`. When no page announces it but a page is listening, the loop falls back
  (6.10). When no page listens at all, exit 3 with the page URL, as the play verbs do.

---

## 6. Loops

### 6.1 Decision: the page keeps time for a run; the server keeps the definition

A long `sequence` cue (N cycles in one cue) would work on today's page, but it fails at what a jam needs:
- a tempo change or a new card means `clear` plus a resend. That cuts held notes and drops hovers mid-bar.
- "stop at the end of this loop" cannot be said.
- a 30-minute cue is unstoppable except by a `clear` that also wipes everything else.

So a loop is a **run**:
- The server holds the definition and a list of tempo **segments** anchored in epoch milliseconds.
- The page schedules each slot on its own `performance.now()` clock through the existing `createCuePlayer` (local cues
  with `source: "jam"`).
- Every change takes effect on a named bar at a known epoch.

The long cue survives only as the fallback for old pages (6.10).

### 6.2 The definition (`def`) the page receives

```json
{
  "card": {"id": "lydian-four", "rev": 1, "title": "The Lydian 4", "variant": null},
  "key": "Eb major",
  "beats_per_bar": 4,
  "cycle_beats": 8,
  "slots": [
    {"i": 0, "at_beat": 0, "beats": 4, "n": "1maj9", "name": "Ebmaj9", "key": "Eb major",
     "notes": [39, 50, 55, 65, 70], "vel": 48, "hold_beats": 4.0, "legato_ms": 80, "arp_ms": 0, "say": null,
     "page_reads": {"name": "Ebmaj9", "number": "1maj9", "match": "exact"}},
    {"i": 1, "at_beat": 4, "beats": 4, "n": "4maj9#11", "name": "Abmaj9#11", "key": "Eb major",
     "notes": [44, 55, 60, 70, 74], "vel": 48, "hold_beats": 4.0, "legato_ms": 80, "arp_ms": 0, "say": null,
     "page_reads": {"name": "Bb13/Ab", "number": "5^13/4", "match": "equivalent"}}
  ],
  "count": null,
  "hover": false,
  "sound": "owner",
  "display": {"caption": true, "ghost_keys": true, "in_recording": false}
}
```

A `rest` becomes a gap in `at_beat`. A key change becomes the `key` on each later slot. `def` is complete: the page never
needs the bridge.

### 6.3 Bar arithmetic

`segments` is an ordered list: `[{from_bar, bpm, epoch_ms, def_version, def_from_bar}]`.

For a wall time E:

```
s          = the last segment with s.epoch_ms <= E
beats      = (E - s.epoch_ms) * s.bpm / 60000
bar        = s.from_bar + floor(beats / beats_per_bar)
cycle_beat = ((bar - s.def_from_bar) * beats_per_bar + (beats mod beats_per_bar)) mod def.cycle_beats
slot       = the last slot with at_beat <= cycle_beat
```

A change at bar B under segment s starts a new segment with `epoch_ms = s.epoch_ms + (B - s.from_bar) * beats_per_bar * 60000 / s.bpm`,
kept as a float with 0.1 ms resolution. Each segment is computed from the stored previous one, so error never exceeds a
rounding step per change. The server computes positions for `jam status` the same way.

### 6.4 Start and acknowledgement

- **Server.** `start_epoch_ms = now + lead_ms` (800 ms by default), so every page has time to schedule bar 0 with
  lookahead.
- **Page.** Converts epoch to page time with `perf = epoch - (Date.now() - performance.now())`, re-measured each bar, so
  drift between the two clocks cannot accumulate.
- **Ack.** The page POSTs one `ack` per version it applied. That ack is the record that makes exact alignment possible
  (7.3 L1).
- **Voice commit.** The page may plan ahead freely, but must not hand a note to the voice more than 250 ms before it
  sounds (the player's `lookaheadMs` is 60 today). A change with 300 ms notice can then always cancel what has not
  sounded.

### 6.5 Changes

| Op | Default `at` | Effect |
| --- | --- | --- |
| `tempo` | `bar` | A new segment at the next bar line at least 300 ms away. `+4` / `-4` are relative. `at: "beat"` takes the next beat. |
| `next` | `loop` | A new `def` (another card, variant or key) from the first cycle boundary at least 300 ms away. With no card on a concept card: the next variant. With no card otherwise: the next card in `deck.json` order. `at: "bar"` switches at the next bar, starting the new line at its beat 0. |
| `stop` | `loop` | Ends at the next cycle boundary. `at: "now"` releases every loop note with an 80 ms fade. |
| `mute` / `unmute` | `now` | Silences the loop's sound, keeping time and visuals, so Daniel can check he is still with it. |

Every change bumps `version`, appends a timeline line, and publishes one `jam` frame carrying the whole `segments` list.

### 6.6 Stop, orphans and restarts

- **Stream lost.** A page that loses the stream keeps a running loop for at most **2 bars**, then stops it. On reconnect
  it posts an `ack` with `stopped: "stream-lost"` and the bar it stopped on.
- **Server restart.** The server keeps the active run in memory. At startup, any run whose timeline has no `stop` gets
  one with `reason: "server-restart"`, `approx: true`, and `epoch_ms` set to the time of its last timeline line.
- **Count.** A run with `count` N stops itself after N cycles: the server writes the `stop` line with `reason: "count"`.

### 6.7 Sound owner

Only one page sounds a loop:
- A page claims ownership on Daniel's input (pointer, key or MIDI), with a 30 s lease renewed while the page stays
  visible and in use.
- Other jam pages draw the loop (captions, ghost keys) but stay silent.
- With no claim, the first page to `ack` a start becomes the owner.
- `jam {op: "owner"}` tells every page.

`try` cues keep today's behaviour (every page plays them) until the cue channel gets the same lease; see Q6.

### 6.8 Kept out of the log, and MIDI loopback

**Out of the log.** Loop notes carry `meta.source: "jam"`. The page keeps them out of:
- the practice log
- `pcHistory`
- the key tracker
- any count of Daniel's playing

This is the rule `cues.js` already states for `claude` and `replay`. One recommendation for the page lane: while a run is
active and Daniel has no lock of his own, number his chords against `run.key` (`keyTracker.lock(run.key)`), so the
Nashville row agrees with the loop he is riffing on.

**MIDI loopback (F7).** When loop or cue sound goes out over MIDI:
- The chosen output port's name must never be bound as an input.
  - `midiRank` returns -1 for an input whose name equals the MIDI-out port's name.
  - `bindMidi` refuses to bind it, even when chosen by hand, with a status message.
- Otherwise a loopMIDI port feeding FL Studio could echo Claude's loop back into the page as Daniel's playing.
- `practice riff` also checks for this (9.4).

### 6.9 Recording stays clean

`display.in_recording` defaults to **false**. While REC runs, loop captions, ghost keys and deck UI stay in the HUD and
top bar, outside the canvas. Loop notes are not drawn as key presses inside the canvas: they are not Daniel's.

Loop captions never borrow the canvas Nashville row or the banner slot: spectacle spec D8 gives that slot to rarity
banners for 2 to 3 s. A card or run may opt in with `display.in_recording: true` (for example a teaching video).

### 6.10 Fallback for pages without `jam1`

`loop start` sends one `sequence` cue with these properties:
- `count` cycles (default 8), capped so that steps <= 4000 and length <= 30 min
- `source: "claude"`, label = the card title
- detail = `"loop, 8 cycles; stop: py -m arsenal.pianocue clear"`

It records a run with `mode: "cue-loop"` and warns. `loop stop` sends `clear`. `loop tempo` and `loop next` exit 2 with
"this page predates loops; reload the piano page".

---

## 7. The jam timeline and alignment with the practice log

### 7.1 `runs/<run>/run.json`

```json
{
  "api": "arsenal.jam.run/v0",
  "run": "20260914-015210-3fa9c1d2",
  "mode": "loop",
  "created_at": "2026-09-14T05:52:09.012+00:00",
  "created_by": "claude",
  "card": {"id": "lydian-four", "rev": 1, "title": "The Lydian 4", "variant": null},
  "card_snapshot": {"...": "the card as it was at start, so later edits never rewrite history"},
  "key": "Eb major",
  "voicing": "spread",
  "beats_per_bar": 4,
  "start_epoch_ms": 1789365129812,
  "closed": false,
  "stopped_epoch_ms": null,
  "stop_reason": null,
  "last_version": 1,
  "owner_page_id": "p-7f3a"
}
```

`mode` is `loop`, `once` (a `try`) or `cue-loop` (the fallback).

### 7.2 `runs/<run>/events.jsonl` (append-only; one line per change)

```
{"seq":0,"kind":"start","recorded_epoch_ms":1789365129012,"by":"claude","version":1,"effective_bar":0,"epoch_ms":1789365129812,"bpm":66,"def":{...}}
{"seq":1,"kind":"ack","recorded_epoch_ms":1789365129140,"page_id":"p-7f3a","role":"owner","version":1,"bar":0,"bar_epoch_ms":1789365129812.4,"perf_ms":8123456.2,"perf_offset_ms":1789357006356.2,"output_latency_ms":21.3,"log":{"local":"mu1x-81c2","session":"20260914-015140-5d0e44a1","t0_perf_ms":8101234.0}}
{"seq":2,"kind":"change","op":"tempo","recorded_epoch_ms":1789365151900,"by":"claude","version":2,"effective_bar":8,"epoch_ms":1789365158903.3,"bpm":72}
{"seq":3,"kind":"change","op":"next","recorded_epoch_ms":1789365170200,"by":"daniel","version":3,"effective_bar":16,"epoch_ms":1789365185570.0,"card":{"id":"float-or-pull","rev":1,"variant":"c"},"key":"Eb major","def":{...}}
{"seq":4,"kind":"mark","recorded_epoch_ms":1789365190000,"by":"claude","text":"he leaned on D in the Bb7 bar"}
{"seq":5,"kind":"stop","recorded_epoch_ms":1789365210000,"by":"claude","version":4,"effective_bar":28,"epoch_ms":1789365225570.0,"reason":"cli"}
```

- `mode: "once"` runs have one `start` line with `cue_id` and `sent_at` and no acks. The cue channel has none; its
  alignment is L3 or L4 plus the player's 50 ms start delay.
- `Ack` fields: `page_id`, `role`, `version`, `bar`, `bar_epoch_ms`, `perf_ms` (the page time of that bar),
  `perf_offset_ms` (`Date.now() - performance.now()` when scheduled), `output_latency_ms` (`AudioContext.outputLatency`,
  or null), `log` (null when the page records no session), and `stopped` (for orphans).

### 7.3 Alignment ladder

`jam.align(run, performance_store)` returns, for each practice session that overlaps the run in wall time, the session
`t_ms` of the run's bar 0 plus the method and its error:

| Level | When | Session `t_ms` of a bar | Error |
| --- | --- | --- | --- |
| **L1** page clock | an `ack.log.session` equals the session | `ack.perf_ms(bar) - ack.log.t0_perf_ms` | Scheduling resolution (under 2 ms). Output latency is recorded separately and can be subtracted. |
| **L2** session meta | the session's `meta.page_id` equals an ack's `page_id` (7.5), for a session that opened after the loop started | `perf_ms(bar) - meta.t0_perf_ms` | As L1 |
| **L3** client wall clock | `meta.opened_at_client` exists (buffered sessions today; every session after 7.5) | `bar_epoch_ms - epoch(opened_at_client)` | The page's `Date.now()` against its performance clock: tens of ms, more after a system sleep. Reported as +/-50 ms. |
| **L4** server open time | nothing better, and the session was not buffered | `bar_epoch_ms - epoch(opened_at)` | Time from the first note to the server receiving `open`: normally under 100 ms, reported as +/-150 ms. **Refused** for `meta.buffered: true` without `opened_at_client`. Session S1 shows why: its server `opened_at` is 1 h 0 min 6 s after its client time. |

`practice riff` reports beat-level timing (early/late against the grid) only at L1 or L2. Which chord was sounding when
he played a note is reliable at every level, because slots last seconds.

Worked L1 example with the lines above: bar 0 is at `8123456.2 - 8101234.0 = 22222.2` ms, 0:22 into session
`20260914-015140-5d0e44a1`. Bar 8, after the tempo change, is at `22222.2 + 8 * 4 * 60000 / 66 = 51313.1` ms.

### 7.4 Formula for any bar

```
t_ms(bar) = t_ms(bar 0 of its segment) + (bar - seg.from_bar) * beats_per_bar * 60000 / seg.bpm
t_ms(bar 0 of segment k) = t_ms(bar 0) + (seg_k.epoch_ms - seg_0.epoch_ms)       # epochs share one clock
```

### 7.5 Two additive meta fields on the practice-log open (`log.js` only; no event kinds change)

`log.js` already builds `meta` for `POST /api/performance/open`, and `performance.py` stores `meta` as given. Add:
- `meta.page_id`: the log's existing `pageId`
- `meta.t0_perf_ms`: `cur.t0 * 1000`
- `meta.opened_at_client` on every open, not only buffered ones

Plus a read-only accessor, `log.timebase() -> {local, session, t0_perf_ms} | null`, for the page's jam ack and template
capture. `performance.py`, its validators, `summary.json` and every event kind are untouched.

---

## 8. CLI verbs (`py -m arsenal.pianocue ...`, extending `arsenal/pianocue.py`)

### 8.0 Conventions

- Every verb takes `--port` (default 8793). Verbs that write take `--dry-run` (print the card or request, send nothing)
  and `--json`.
- A card argument is an id or a unique id prefix. Where marked, it can also be a chord string in 2.3 form (an unsaved
  line; it needs `--key`).
- Exit codes: 0 done; 2 bad input (the message names the flag); 3 sent, but no page is listening (prints the page URL);
  4 no server, or an old server; **5 conflict** (the card or run changed underneath: rerun).

### 8.1 `card`

```
card add --title TITLE --kind chord|progression|loop|concept|moment --key KEY
         (--chords "1maj9:4 | 4maj9#11:4" | --names "Ebmaj9:4 | Abmaj9#11:4" | --notes "Ab2 Eb3 G3 C4 D4 F4 Bb4" | --from-json FILE)
         [--id SLUG] [--also-in KEY]... [--notes-for SLOT="NOTES"]...
         [--variant "b=pull: 1maj9:4 | 5^7:8 | 1maj9:4"]... [--variant-key b="b7 major"]...
         [--bpm 66] [--beats-per-bar 4] [--bars N] [--voicing spread|close|open|drop2|shell] [--voice-lead]
         [--vel 48] [--arp 0] [--hold legato|detached|BEATS] [--style TEXT]
         [--explain TEXT] [--why TEXT] [--try TEXT] [--listen-for TEXT]
         [--check "slot=1 role=#11 want=present say=you touched D"]...
         [--tag T]... [--moment SESSION@m:ss[-m:ss][=label]]... [--replay SESSION@m:ss+SECONDS]
         [--related ID]... [--by claude|daniel] [--dry-run] [--json]
```

- `--names` turns chord names into numbers in `--key` through the bridge's `nashvilleFromName`. A name that has no
  number is refused.
- `--notes` makes a one-chord card from exact notes.
- The command prints the card resolved in its key: names, notes, what the page reads, and warnings.

```
$ py -m arsenal.pianocue card add --id lydian-four --title "The Lydian 4" --kind loop --key "Eb major" \
    --chords "1maj9:4 | 4maj9#11:4" --bpm 66 --tag signature --tag lydian \
    --explain "The 4 chord (Ab) with a D on top..." --why "..." --try "..." \
    --moment S4@0:00-0:22="the same move in Db"
card lydian-four rev 1 (loop, Eb major, 66 bpm, 2 bars)
  1  Ebmaj9      1maj9      Eb2 D3 G3 F4 Bb4     page reads Ebmaj9
  2  Abmaj9#11   4maj9#11   Ab2 G3 C4 Bb4 D5     page reads Bb13/Ab (5^13/4): no maj9#11 name on the page yet
```

```
card list [--kind K] [--tag T] [--by claude|daniel] [--archived] [--json]
card show CARD [--key KEY] [--variant a|b|all] [--voicing STYLE] [--json]
card edit CARD [--title] [--kind] [--key] [--chords] [--notes-for] [--variant] [--bpm] [--voicing] [--vel] [--arp]
               [--explain] [--why] [--try] [--add-tag T] [--rm-tag T] [--add-moment M] [--rm-moment N]
               [--set FIELD=JSON]... [--favorite|--unfavorite] [--archive|--unarchive] [--if-rev N] [--dry-run]
card rm CARD [--if-rev N]        # moves it to state/arsenal/jam/deck/trash/
card restore CARD                # the newest trashed revision comes back as rev + 1
card trash                       # list what is in the trash
```

Example: `card show gospel-five-over-four --key "Db major"` prints Gbmaj9, Ab11/Gb, Db/F, Dbmaj9 with notes, plus the
explanation, why and try lines.

### 8.2 `deck`

```
deck [--kind K] [--tag T] [--json]          # the deck in order, grouped by kind
deck order CARD CARD ...                    # listed cards first, the rest after in their current order
deck seed [--update] [--dry-run]            # install state/arsenal/jam/seed/seed-deck-v1.json
```

`deck seed` installs cards whose id is absent. With `--update` it also replaces seed cards nobody has edited
(`source.kind == "seed"` and `rev == 1`) when the seed file's `seed_version` is newer. Anything edited or created by
Daniel is left alone and listed as kept.

```
$ py -m arsenal.pianocue deck
deck rev 17: 15 cards (15 by claude, 0 by daniel)
  loop         lydian-four               Eb major  1maj9 4maj9#11                     The Lydian 4
  loop         gospel-five-over-four     Eb major  4maj9 5^11/4 1/3 1maj9             Gospel 5 over 4
  concept      one-note-apart            Eb major  a b c                              One note apart
  ...
```

### 8.3 `try` (play once)

```
try CARD|CHORDS [--key KEY] [--variant a|b|all] [--slot N] [--bpm N] [--voicing STYLE] [--hover] [--arp MS] [--vel N] [--silent]
```

- A single chord or `--slot N` is a `play` (or `hover`) cue. Anything else is one `sequence` cue.
- `--variant all` (the default for concept cards) plays the variants in order, one bar of rest between them, each step
  labelled `"a: float (your habit)"`.
- Every try goes through `POST /api/piano/jam/try`, so it is in the timeline (`mode: "once"`).

```
$ py -m arsenal.pianocue try float-or-pull
sent cue #57 to 1 listener: float-or-pull, variants a b c, Eb major, 60 bpm, 24.0 s (run 20260914-015930-0b7e2a19)
  a  float (your habit)  Ebmaj9 | Bb7sus4/Eb | Ebmaj9
  b  pull                Ebmaj9 | Bb7 | Ebmaj9
  c  float, then pull    Ebmaj9 | Bb7sus4 | Bb7 | Ebmaj9
```

### 8.4 `loop`

```
loop start CARD|CHORDS [--key KEY] [--variant V] [--bpm N] [--voicing STYLE] [--voice-lead] [--count N]
                       [--vel N] [--arp MS] [--hover] [--mute] [--show-in-recording] [--lead-ms 800]
loop stop  [--now | --at bar|loop]
loop tempo BPM|+N|-N [--at beat|bar]
loop next  [CARD|CHORDS] [--variant V] [--key KEY] [--at loop|bar]
loop mute | loop unmute
```

```
$ py -m arsenal.pianocue loop start lament-bass --bpm 60
loop 20260914-020114-77a0c3e5: lament-bass "Lament bass" in Db major, 60 bpm, 4 bars, until stopped
  bar 1  Bbm11     6m11    Bb2 Bb3 Ab4 C5 Db5 Eb5 F5
  bar 2  Bbm11/Ab  6m11/5  Ab2 Bb3 Ab4 C5 Db5 Eb5 F5
  bar 3  Bbm11/Gb  6m11/4  Gb2 Bb3 Ab4 C5 Db5 Eb5 F5
  bar 4  Bbm11/F   6m11/3  F2 Bb3 Ab4 C5 Db5 Eb5 F5
starts in 0.8 s on 1 jam page (owner p-7f3a)
$ py -m arsenal.pianocue loop tempo -4
version 2: 56 bpm from bar 9 (in 5.1 s)
$ py -m arsenal.pianocue loop next --key "Eb major"
version 3: lament-bass in Eb major from bar 13 (the next loop boundary, in 9.2 s)
```

### 8.5 `jam`

```
jam status [--json] [--runs 5]
jam runs [--limit 20] [--json]
jam mark TEXT
```

```
$ py -m arsenal.pianocue jam status
pages  2 listening (1 with jam1), sound owner p-7f3a (lease 21 s)
loop   20260914-020114-77a0c3e5  lament-bass "Lament bass", Db major, 56 bpm, version 2
       bar 11 beat 3 (cycle 3, slot 3: Bbm11/Gb), started 01:01:14 (0:41 ago), no change queued
deck   15 cards, rev 17
runs   lament-bass (loop, running) | float-or-pull (once, 0:24) | lydian-four (loop, 3:28)
```

### 8.6 `template`

```
template save-from-moment SESSION|latest AT [--until m:ss] [--title TEXT] [--key auto|KEY] [--beats 4] [--id SLUG] [--dry-run] [--json]
template save-last [--title TEXT] [--dry-run]       # latest session, its last harmonic window
```

Rules are in 2.10. The verb reads the practice log only (`PerformanceStore.events` plus `practice.analyze`). The card is
`created_by: "daniel"` with `source.saved_by: "claude"`.

```
$ py -m arsenal.pianocue template save-from-moment S2 5:00
card t-20260914-021502-4d1a rev 1 (chord, Eb major): "Dbmaj9, from 5:00"
  1  Dbmaj9  b7maj9  Db3 Ab3 Eb4 F4 Ab4 C5 Db5 F5 Ab5   page reads Dbmaj9
  moment S2 5:00-5:09
```

---

## 9. `practice riff` (in `arsenal/practice.py`, read only)

### 9.1 Invocation

```
py -m arsenal.practice riff [RUN|latest] [--session SESSION] [--root DIR] [--jam-root DIR]
                            [--card CARD --key KEY --bpm N --from m:ss [--to m:ss]]
                            [--bars A-B] [--json] [--out FILE] [--save]
```

- **With a run**, the loop definition and the time window come from the timeline, and the session from alignment
  (7.3). Pass `--session` when several sessions overlap.
- **Without a run** (Daniel played along with a card he read, or with Claude describing one), give `--card`, `--key`,
  `--bpm` and `--from`. The grid is then assumed to start at `--from` (L4-like, flagged `alignment: "assumed"`).
- `--save` writes the JSON to `state/arsenal/jam/riffs/<run>.json`. Nothing ever writes to the practice log.

### 9.2 Pipeline

1. **Loop timeline.** Expand segments and definitions into slot instances `[t_start, t_end)` in session `t_ms`, each with
   the chord, number, key and notes.
2. **His notes.** `practice.sounding(events)["notes"]`. The log holds only his notes when 6.8 holds; see 9.4 when it does
   not.
3. **Per slot instance:**
   - **What he played.** Onsets in `[t_start - 120 ms, t_end - 120 ms)`: a note played just before a change belongs to
     the next chord. Pitch classes are weighted by heard time inside the slot (`_heard`).
   - **Role of each pitch class**, relative to the loop chord's root: chord tone, tension (`9`, `#11`, `13`, ...),
     outside the key, or a rub (a half step against a chord tone that is sounding).
   - **Landing note.** His first onset in `[t_start - 120, t_start + 250]` and its role.
   - **Top-note line** (the highest note per onset group).
   - **His own reading.** `Theory.detect` (through `practice_theory.mjs`) over his notes alone, and over his notes plus
     the loop's. When his root or bass differs from the loop's, it is a **reharmonization** ("over 4maj9 you played
     2m9/4").
4. **Per slot across cycles.** Which roles he used, how often, and new colours per cycle (a role not heard in earlier
   cycles).
5. **Per cycle.** Onsets per bar, mean and peak velocity, share of pedal down, register span. The arcs come from these.
6. **Timing.** Only at L1/L2: each onset's offset from the nearest eighth-note grid point (median, interquartile range),
   so "you sit 30 ms behind the beat" is honest.
7. **Card checks** (2.8), each pass or fail with its `say` line.
8. **Highlights.** The top 3 slot instances, ranked by new colours + reharmonization + velocity peak. Each has a clock
   time and a ready command, `pianocue template save-from-moment <session> <m:ss>`.
9. **Questions.** Two or three in plain words, in the manner of `performance.questions()`, built only from the numbers
   above.

### 9.3 Output (`arsenal.practice.riff/v0`)

```json
{
  "api": "arsenal.practice.riff/v0",
  "run": "20260914-020114-77a0c3e5",
  "card": {"id": "lament-bass", "rev": 1, "variant": null},
  "session": "20260914-020050-a1b2c3d4",
  "alignment": {"method": "L1", "error_ms": 2, "bar0_t_ms": 22222.2, "output_latency_ms": 21.3},
  "loopback": {"suspected": false, "mirrored_share": 0.0},
  "coverage": {"cycles": 9, "bars": 36, "bars_with_his_notes": 31},
  "slots": [
    {"slot": 2, "name": "Bbm11/Gb", "number": "6m11/4", "cycles": 9,
     "roles": {"b3": 9, "9": 7, "11": 5, "5": 4}, "bass_roles": {"#11": 7, "3": 9},
     "landings": {"b3": 5, "9": 2, "5": 2},
     "reharmonized": [{"cycle": 6, "his": "Ab11/Gb", "loop": "Bbm11/Gb", "because": "no F in his notes"}],
     "outside": [], "top_line": ["Db5", "C5", "Bb4"]}
  ],
  "cycles": [{"cycle": 1, "onsets_per_bar": 3.1, "mean_vel": 41, "peak_vel": 58, "pedal_down": 0.82, "span": [42, 80]}],
  "timing": {"grid": "eighths", "median_ms": 28, "iqr_ms": [4, 61], "note": "behind the beat"},
  "checks": [{"id": "lydian-over-gb", "pass": true, "say": "you found C, the Lydian note, over the Gb bass"}],
  "highlights": [{"at": "1:47", "slot": 2, "why": "new colour: C (#11 over the Gb bass) for the first time",
                  "save": "py -m arsenal.pianocue template save-from-moment 20260914-020050-a1b2c3d4 1:47"}],
  "questions": ["In cycle 6 you left F out over the Gb bass, and the chord became your gospel Ab11/Gb. Did you hear it lean?"]
}
```

The numbers above are illustrative placeholders, not a measurement. The builder's receipts use synthetic sessions, as
`test_arsenal_practice.py` does. `roles` are relative to the slot chord's root (Bb here); `bass_roles` are relative to
the bass (Gb), because slash chords are heard both ways. Questions are templated from the facts only, and a receipt
checks each template's wording against the fact it cites.

The text render is a short chat-ready report: coverage, the two strongest slot facts, checks, highlights, questions.

### 9.4 Guards

- **Loopback.** If more than half of the loop's slot onsets have one of Daniel's notes of the same pitch within 15 ms,
  the report sets `loopback.suspected`, says "the loop may be echoing into the log (MIDI loopback)", and still analyses.
- **No overlap.** No session overlaps the run: exit 2 with the run's wall-clock window and the nearest sessions.
- **Refused alignment.** L4 refused for a buffered session (7.3): exit 2, naming the missing `opened_at_client`.

---

## 10. The seed deck (15 cards)

The chords below were run through the voicing bridge on 2026-09-14, and "page reads" gives its `roundtrip` answer. The
moments were checked against `py -m arsenal.practice windows` and `harmony` for the four sessions. Items marked
*expected* were not run through the bridge in that exact voicing; `deck seed` recomputes every `page_reads` anyway.

Every card has `created_by: "claude"`, `source: {"kind": "seed", "seed_version": 1}`, `playback.velocity: 48`, and
`voicing.style: "spread"` unless it says otherwise.

| # | id | kind | key | line (default key) | tags |
| --- | --- | --- | --- | --- | --- |
| 1 | `lydian-four` | loop | Eb major | `1maj9:4 \| 4maj9#11:4` | signature, lydian |
| 2 | `gospel-five-over-four` | loop | Eb major | `4maj9:4 \| 5^11/4:4 \| 1/3:4 \| 1maj9:4` | signature, gospel, slash |
| 3 | `one-note-apart` | concept | Eb major | a `4maj13#11` / b `5^11/4` / c both | signature, lydian, gospel |
| 4 | `blooming-chord` | progression | Eb major | `4sus2:4 \| 4add9:4 \| 4maj9:4 \| 4maj13#11:8` | signature, colour |
| 5 | `chromatic-slide` | concept | Eb major | a `2^9/#4 \| 2m9/4 \| 4maj9#11` / b (Db) `#4m7/6 \| 4maj7/6` | signature, half-step |
| 6 | `lament-bass` | loop | Db major | `6m11:4 \| 6m11/5:4 \| 6m11/4:4 \| 6m11/3:4` | signature, bass |
| 7 | `minor-third-drop` | progression | F major | a F to D / b Gb to Eb | signature, key-change |
| 8 | `borrowed-four-minor` | loop | Eb major | `1maj9:4 \| 4add9:4 \| 4m(add9):4 \| 1maj9:4` | borrowed |
| 9 | `borrowed-b6-b7-home` | loop | Eb major | `b6maj9:4 \| b7maj9:4 \| 1maj9:8` | borrowed, ending |
| 10 | `float-or-pull` | concept | Eb major | a sus / b V7 / c sus then V7 | growth-edge, dominant |
| 11 | `lush-two-five-one` | loop | Eb major | `2m9:4 \| 5^13:4 \| 1maj9:8` | growth-edge, dominant |
| 12 | `lights-on-ending` | progression | Eb minor | Eb minor, then Gb major, then Eb major | signature, key-change, ending |
| 13 | `db-opening` | loop | Db major | `4maj9:2 \| 4maj13#11:6 \| 5^11/4:4 \| 4maj13#11:4 \| 6m9/1:8` | yours, lydian |
| 14 | `held-sus-five` | moment | Eb major | `5^7sus4/1:16` (his notes) | yours, dominant |
| 15 | `open-ending-b7` | moment | Eb major | `b7maj9:16` (his notes) | yours, borrowed, ending |

### 1. The Lydian 4 (`lydian-four`, loop, Eb major, 66 bpm, 2 bars)

- **Line:** `1maj9:4 | 4maj9#11:4`. In Eb: Ebmaj9 to Abmaj9#11. Also in Db major (Dbmaj9 to Gbmaj9#11) and F major.
- **Page reads:** Ebmaj9 (exact). Abmaj9#11, spread Ab2 G3 C4 Bb4 D5, reads **Bb13/Ab (5^13/4)**: the page has no
  maj9#11 name yet.
- **Explanation:** The 4 chord (Ab) with a D on top. D is the #11, a raised 4th above Ab, and it is already a note of Eb
  major, so it shines without sounding wrong.
- **Why it matters:** It is your signature colour: the analyzer named a Lydian 4 in 80 windows across tonight's four
  sessions (38 in the long session, 19 in the Db piece, 17 and 6 in the two Eb sessions).
- **Try this:** Keep the loop going. On the Ab bar, move your top finger between C and D: C is the plain chord, D is the
  shimmer. Then try D over the Eb bar too (there it is the major 7th).
- **Check:** slot 2, role `#11`, present: "you touched D, the #11 of Ab".
- **Moments:**
  - `S4` 0:00-0:22: Gbmaj9, Gbmaj13, Gbmaj13#11 (the same move in Db)
  - `S3` 20:22-20:30: Abmaj9#11 to Abmaj13#11
  - `S2` 3:49-3:58: Bb11/Ab, Abmaj9#11, Abmaj7, Abmaj9

### 2. Gospel 5 over 4 (`gospel-five-over-four`, loop, Eb major, 66 bpm, 4 bars)

- **Line:** `4maj9:4 | 5^11/4:4 | 1/3:4 | 1maj9:4`. In Eb: Abmaj9, Bb11/Ab, Eb/G, Ebmaj9. Also in Db major (Ab11/Gb) and
  D major (A11/G).
- **Page reads:** all exact. Bb11/Ab spread is Ab2 Bb3 D4 C5 Eb5; Eb/G is G2 Eb3 Bb3 Eb4.
- **Explanation:** In Bb11/Ab your right hand plays the 5 chord (Bb) while the bass stays on Ab, the 4. It leans toward
  home without the hard pull of a plain 5.
- **Why it matters:** The bass only has to step down from Ab to G to land (G is the 3rd of Eb), so the arrival is soft
  and churchy. It is one of your most used shapes, in three keys tonight.
- **Try this:** Let the loop run and follow the bass with your ear: Ab, Ab, G, Eb. Then riff a melody on C and Eb, which
  sound good over all four bars.
- **Check:** slot 3 (Eb/G), `landing`, role `3` or `1`: "you landed on home as the bass stepped down".
- **Moments:**
  - `S1` 2:54-3:00: Ab, Abadd#11, Bb11/Ab, then Eb
  - `S2` 3:36-3:49: Bb7sus4/Ab to Bb11/Ab, then Abmaj13#11
  - `S4` 0:15-0:20: Ab11/Gb, 5 s, in Db
  - `S3` 10:42-10:48: A9/G to A11/G, in D

Note: bar 3 is a plain Eb/G triad on purpose, so the bass step from Ab to G is what you hear. Bar 4 brings the colour
back.

### 3. One note apart (`one-note-apart`, concept, Eb major, 60 bpm)

- **Variants (exact notes):**
  - **a** "the Lydian 4, with G": `4maj13#11:8`, notes Ab2 Eb3 G3 C4 D4 F4 Bb4. Page reads **Cm11/Ab (6m11/4)**,
    checked.
  - **b** "the gospel 5 over 4, without G": `5^11/4:8`, notes Ab2 Eb3 C4 D4 F4 Bb4. Page reads **Bb11/Ab**, checked.
  - **c** "back and forth": `4maj13#11:4 | 5^11/4:4 | 1/3:8`, with a's and b's notes and Eb/G spread.
- **Explanation:** Over an Ab bass, Bb11/Ab and Abmaj13#11 share six notes: Ab Bb C D Eb F. The Lydian chord adds one
  more, G.
- **Why it matters:** G is the major 7th of Ab. With it the chord floats and can stay; without it the chord belongs to
  Bb and leans toward Eb. Your two favourite moves are one finger apart. In Db the same pair is Gbmaj13#11 and Ab11/Gb,
  and the note is F.
- **Try this:** Hold the Ab bass. Play a, then lift only the G and listen to the chord start to lean. Put it back. The
  page names the same sound three ways (Abmaj13#11, Cm11/Ab, Bb11/Ab minus one note): the notes are what matter.
- **Moments:** `S2` 3:36-3:49 (Bb11/Ab straight into Abmaj13#11); `S3`
  19:19-19:24 (Absus2(#11), Bb11/Ab, Abmaj13#11).

### 4. The blooming chord (`blooming-chord`, progression, Eb major, 60 bpm, 5 bars)

- **Line (exact notes, each chord keeps the one before it):**
  - `4sus2:4`: Ab2 Eb3 Bb3 Eb4
  - `4add9:4`: Ab2 Eb3 Bb3 C4 Eb4 (adds C)
  - `4maj9:4`: Ab2 Eb3 G3 Bb3 C4 Eb4 (adds G)
  - `4maj13#11:8`: Ab2 Eb3 G3 Bb3 C4 Eb4 D5 F5 (adds D and F)
  - `arpeggio_ms: 45` on each
- **Page reads:** Absus2, Abadd9, Abmaj9 expected exact; the last expected Cm11/Ab, the same seven notes as card 3a.
- **Explanation:** Keep the root and bass still and add colour one note at a time: sus2 (Ab Bb Eb), then the 3rd arrives
  (add9), then the major 7th (maj9), then the Lydian top (D and F).
- **Why it matters:** A chord can grow in front of the listener: the harmony stays and the colour rises. The analyzer
  found 65 of these colour additions in the long session alone.
- **Try this:** Play it with the loop, then un-bloom it yourself: take the notes away in reverse, one per bar, until only
  Ab and Eb are left.
- **Moments:** `S4` 0:00-0:07 (Gbmaj9, Gbmaj13, Gbmaj13#11); `S2` 3:05-3:10
  (Abmaj9#11, Ab6/9, Absus2, Abadd9); `S3` 20:45-20:50 (Abadd#11, Absus2(#11,13), Abmaj13#11).

### 5. The chromatic slide (`chromatic-slide`, concept, Eb major, 60 bpm)

- **Variants:**
  - **a** "the bass slides": `2^9/#4:4 | 2m9/4:4 | 4maj9#11:8`. In Eb: F9/A, Fm9/Ab, Abmaj9#11. Spread voicings, checked:
    F9/A is A2 F3 Eb4 G4 C5 and Fm9/Ab is Ab2 F3 Eb4 G4 C5, so exactly one note moves.
  - **b** "the top slides over a still bass", variant key `b7 major` (Db major when the card is in Eb): `#4m7/6:4 |
    4maj7/6:8`. In Db: Gm7/Bb, Gbmaj7/Bb. Exact notes Bb2 F3 G3 Bb3 D4, then Bb2 F3 Gb3 Bb3 Db4.
- **Page reads:** a all exact (Abmaj9#11 reads Bb13/Ab as in card 1). b: Gbmaj7/Bb expected exact. The first chord may
  read **Bb6**: Gm7/Bb and Bb6 are the same four notes.
- **Explanation:** In a, only one note moves: A slides down to Ab, and F, Eb, G and C stay where they are. In b, over a
  held Bb, two notes slide down a half step: G to Gb and D to Db.
- **Why it matters:** A half step is the smallest move on the keyboard, so the colour changes while everything else
  holds, and the ear follows the note that moved.
- **Try this:** Loop a and play the moving note yourself as a tiny melody (A, then Ab) an octave up. Then look for
  another chord in your pieces where one note can slide.
- **Moments:** `S3` 20:05-20:22 (F9/A 5 s, F11/A, Fm7/Ab, Fm9/Ab, Fm13/Ab, then Abmaj9#11);
  `S4` 2:42-2:46 (Bbsus4, Gm7/Bb, Gbmaj7/Bb, Gbmaj7#11/Bb).

### 6. The lament bass (`lament-bass`, loop, Db major, 60 bpm, 4 bars)

- **Line (exact notes; the hands never move):**
  - hands Bb3 Ab4 C5 Db5 Eb5 F5 on every bar
  - `6m11:4` bass Bb2, `6m11/5:4` bass Ab2, `6m11/4:4` bass Gb2, `6m11/3:4` bass F2
  - In Db: Bbm11, Bbm11/Ab, Bbm11/Gb, Bbm11/F. Also in Eb major (Cm11 over C Bb Ab G).
- **Page reads (checked):** Bbm11, Bbm11/Ab, Bbm11/Gb, Bbm11/F. The bridge's spread voicing of 6m11/4 leaves out F and
  reads Ab11/Gb, which is why this card stores exact notes.
- **Explanation:** Your hands hold one chord, Bbm11, the whole time. Only the bass walks down: Bb, Ab, Gb, F.
- **Why it matters:** Four bass notes stepping down from the minor chord's root is the old lament bass. The hands never
  move, but the harmony does: over Gb the same notes are the whole Lydian 4 (Gbmaj13#11), and over F they hold Dbmaj9
  plus a Bb.
- **Try this:** Keep the loop going and play a slow melody that stays on one note (Db, or F) while the bass walks under
  it. Listen to the same note change its meaning bar by bar.
- **Check:** slot 3, role `#11`, `relative_to: "bass"` (C over Gb), present: "you found C, the Lydian note, over the Gb
  bass".
- **Moments:** `S4` 2:19-2:28 (Bbm11/Ab, then Bbm11); `S4` 3:17-3:32
  (Bbm11/Ab, Ab11/Gb, Bbm11/Gb, then Dbmaj7/F). The card straightens that walk into a loop.

### 7. Drop a minor third (`minor-third-drop`, progression, F major, 66 bpm)

- **Variants:**
  - **a** "F to D": `1add9:4 | 4maj13:4 | 5^6:4 | [6 major] | 1add9:4 | 4maj13:4 | 1maj9:8`. In F: Fadd9, Bbmaj13, C6.
    Then in D: Dadd9, Gmaj13, Dmaj9. Every chord checked exact.
  - **b** "Gb to Eb", variant key `b2 major` (Gb): `4maj9:4 | 1maj9:4 | 5sus4:4 | [b7 major] | b3add9/b7:2 | 1add9:6 |
    4maj9:4 | 1maj9:8`. In Gb: Cbmaj9, Gbmaj9, Dbsus4. Then in Eb: Gbadd9/Db, Ebadd9, Abmaj9, Ebmaj9. Checked; Cbmaj9 is
    enharmonic on the page.
- **Explanation:** To change key, move home down a minor third (three half steps): F to D, Gb to Eb. The door is your
  old 5 chord: C is the 5 of F and also the b7 of D. Play it, then land on the new 1.
- **Why it matters:** The new key arrives through a chord that belongs to both keys, so the change sounds like walking
  through a door instead of jumping. It works from any key: the old 5 is always the b7 of the key three half steps
  below.
- **Try this:** Loop the door chord (C6) for two bars and choose your moment to step through. Then use the same door from
  Eb: Bb, the 5 of Eb, is the b7 of C major.
- **Moments:** `S3` 9:01-9:16 (Am, Bbmaj13, C6 at 9:06, Dadd9 at 9:08; the analyzer's key area
  changes from F major to D major at 9:06). `S3` 18:38-19:00 (Bmaj7, C#sus4 = Dbsus4 at 18:41,
  Gbadd9/Db at 18:42, Ebadd11, Ebmaj9; F# major to Eb major at 18:42).

### 8. The borrowed 4m (`borrowed-four-minor`, loop, Eb major, 66 bpm, 4 bars)

- **Line:** `1maj9:4 | 4add9:4 | 4m(add9):4 | 1maj9:4`. In Eb: Ebmaj9, Abadd9, Abm(add9), Ebmaj9.
- **Page reads (checked):** Abadd9 spread Ab2 Eb3 C4 Bb4, then Abm(add9) spread Ab2 Eb3 Cb4 Bb4. Exactly one note moves.
  Abm(add9) is enharmonic on the page.
- **Explanation:** 4m is your Ab chord with its 3rd lowered: C drops to Cb. Cb comes from Eb minor, so the chord is
  "borrowed".
- **Why it matters:** One lowered note turns the 4 chord from warm to bittersweet right before home. It is the sigh at
  the end of a lot of ballads.
- **Try this:** Move only the finger on C. Then let your melody use Cb during that bar, and C again when home comes back.
- **Check:** slot 3, role `b3`, present: "you played Cb, the borrowed note".
- **Moments:** `S1` 5:15-5:25 (Abm, Abm7/Gb, Eb5, Cbmaj7/Eb, Abm(add9) at 5:22; here inside an Eb
  minor passage); `S3` 3:14-3:18 (Abm(add9), Abm9, then Bmaj9, in Eb major).

### 9. b6, b7, home (`borrowed-b6-b7-home`, loop, Eb major, 66 bpm, 4 bars)

- **Line:** `b6maj9:4 | b7maj9:4 | 1maj9:8`. In Eb: Cbmaj9, Dbmaj9, Ebmaj9.
- **Page reads (checked):** the page spells the first chord **Bmaj9**, the same chord with sharps. Dbmaj9 and Ebmaj9 are
  exact.
- **Explanation:** Two major chords borrowed from Eb minor, a whole step apart, climb into home: Cb, Db, Eb.
- **Why it matters:** The roots rise step by step (b6, b7, 1), so home arrives big and open without any 5 chord.
- **Try this:** You ended one piece tonight on Dbmaj9. Loop this and choose each time: stop on b7 (the door stays open)
  or go on to 1 (home).
- **Moments:** `S2` 4:58-5:09 (Gb5, Dbadd9, Dbmaj9 held 9 s: your ending);
  `S1` 5:03-5:08 (Ab-Cb, Cbmaj9/G, Eb); `S3` 3:16-3:19 (Abm9, then Bmaj9,
  which is b6maj9).

### 10. Float or pull (`float-or-pull`, concept, growth edge, Eb major, 60 bpm)

- **Variants:**
  - **a** "float (your habit)": `1maj9:4 | 5^7sus4/1:8 | 1maj9:4`. Slot 2 exact notes, his own: Eb2 Eb3 Eb4 F4 Ab4 Bb4,
    reads Bb7sus4/Eb (checked).
  - **b** "pull": `1maj9:4 | 5^7:8 | 1maj9:4`. Bb7 spread Bb2 Ab3 D4 F4 (checked).
  - **c** "float, then pull": `1maj9:4 | 5^7sus4:4 | 5^7:4 | 1maj9:8`. Exact notes Bb2 F3 Ab3 Eb4, then Bb2 F3 Ab3 D4:
    only Eb4 moves, to D4.
- **Explanation:** Bb7sus4 swaps Bb7's 3rd (D) for Eb. D sits a half step under home (Eb), so Bb7 pulls toward Eb.
  Bb7sus4 already holds Eb, so it floats.
- **Why it matters:** None of tonight's 5 -> 1 cadences that the analyzer found uses a plain 5^7: your 5 chords arrive
  suspended (Bb7sus4/Eb, held 15 s) or with an added 11th (Bbadd11). The plain pull is a colour you don't use yet, and
  contrast (float, then pull, then home) makes an arrival feel earned.
- **Try this:** Play a, b and c. Then loop c and riff: lean on D during the Bb7 bar and let it rise to Eb when home comes.
- **Checks:** variant c, slot 3 (Bb7), role `3`, present: "you played D, the 3rd of Bb7". Variant c, slot 4, `landing`,
  role `1` or `3`: "you landed on home".
- **Moments:** `S1` 2:36-2:54 (Ebmaj7, then Bb7sus4/Eb for 15 s); `S1`
  3:09-3:12 (Absus2, Bb7sus4/Ab, Eb).

### 11. The lush 2-5-1 (`lush-two-five-one`, loop, growth edge, Eb major, 63 bpm, 4 bars)

- **Line (exact notes):**
  - `2m9:4`: F2 Eb3 Ab3 C4 G4
  - `5^13:4`: Bb2 D3 Ab3 C4 G4
  - `1maj9:8`: Eb2 D3 G3 Bb3 F4
  - In Eb: Fm9, Bb13, Ebmaj9.
- **Page reads:** spread voicings checked exact (Fm9, Bb13, Ebmaj9). These exact voicings are expected exact.
- **Explanation:** At each change one note steps down a half step while its neighbour holds: Eb falls to D (Fm9 to Bb13),
  then Ab falls to G (Bb13 to Ebmaj9).
- **Why it matters:** This is the pull of a real 5 chord, still in your lush colours. The falling half steps (each
  chord's 7th becoming the next chord's 3rd) are what make home sound like arriving.
- **Try this:** Play only the two inner notes as a little two-voice line (Eb and Ab, D and Ab, D and G), then put the full
  chords back. Then swap Bb13 for your Bb7sus4/Eb and compare.
- **Check:** slot 2, role `3`, present: "you played D, the note that pulls home".
- **Moments:** the closest you came, `S3` 21:42-21:49 (Cm7, Cm9, Bb6/9/F, Bb13/F).

### 12. Lights on (`lights-on-ending`, progression, Eb minor, 58 bpm, 16 bars)

- **Line:** `1m9:4 | 4m9:4 | b6maj9:4 | b7maj9:4 | [b3 major] | 4maj9:4 | 6m9:4 | 5sus4:4 | 1maj9:8 | [1 major] |
  b3add9/b7:4 | 1add9:4 | 4maj9:4 | 1maj9:8`
  - Eb minor: Ebm9, Abm9, Cbmaj9, Dbmaj9
  - Gb major: Cbmaj9, Ebm9, Dbsus4, Gbmaj9
  - Eb major: Gbadd9/Db, Ebadd9, Abmaj9, Ebmaj9
  - Every chord checked through the bridge in its key.
- **Explanation:** Three homes that share Eb's notes. First Eb minor. Then Gb major, which uses the same notes with Gb as
  home. Then Eb major, which is Eb minor with three notes raised a half step: Gb to G, Cb to C, Db to D.
- **Why it matters:** Minor, then its relative major, then the parallel major is a way to end a dark piece in full light.
  The Gbadd9/Db bar is the door: Db is the 5 of Gb and the b7 of Eb, card 7's move again.
- **Try this:** Play the Gb bars as the loudest part, then let the Eb major bars arrive soft and slow. Listen for the
  three raised notes.
- **Moments:**
  - `S3` 16:04-22:13. The analyzer's key areas: Gb major (spelled F# major) from 16:13, with its
    Ebm chords (spelled D#m9, D#m11) around 16:51-18:23; the turn to Eb major at 18:42 (Gbadd9/Db); Ebmaj7 held at
    22:07.
  - `S1` 4:00-5:25: the Eb minor passage (Ebm(add9), Gbadd9, Cbmaj7#11/Bb, Ebm, Abm(add9)).

### 13. Your Db opening (`db-opening`, loop, Db major, 56 bpm, 6 bars)

- **Line:** `4maj9:2 | 4maj13#11:6 | 5^11/4:4 | 4maj13#11:4 | 6m9/1:8`. In Db: Gbmaj9, Gbmaj13#11, Ab11/Gb, Gbmaj13#11,
  Bbm9/Db.
- **Exact notes for both Gbmaj13#11 slots:** your pedal cloud at 0:05, Gb2 Db3 Gb3 Ab3 Bb3 Db4 F4 Bb4 Eb5 F5 Ab5 C6.
- **Page reads (checked):** the cloud has no name on the page; it shows the letters "Gb Db Ab Bb F Eb C" with no number.
  Gbmaj9, Ab11/Gb and Bbm9/Db are exact.
- **Explanation:** Your own opening, straightened into a loop: Gbmaj9 blooms into the Lydian 4 of Db, Ab11/Gb takes a
  breath, and Bbm9 over Db brings you home.
- **Why it matters:** You never play a plain Db chord here, and it still sounds like home, because the bass lands on Db.
- **Try this:** Ab is in every chord of this loop: start a melody on Ab, then reach up to C, which is in every chord but
  the first.
- **Moments:** `S4` 0:00-0:23 (Gbmaj9 0:00, Gbmaj13 0:03, Gbmaj13#11 0:05, Ab11/Gb 0:15,
  Gbmaj13#11 0:20, Bbm9/Db 0:22).

### 14. The held sus 5 (`held-sus-five`, moment, Eb major)

- **Line:** `5^7sus4/1:16`, exact notes Eb2 Eb3 Eb4 F4 Ab4 Bb4 (yours, at 2:40), reads Bb7sus4/Eb (checked).
- **Replay:** `{"session": "S1", "at": "2:36", "seconds": 18, "speed": 1}`.
- **Explanation:** You held Bb7sus4 over Eb for 15 seconds: Eb F Ab Bb, with Eb in three octaves. It never resolved, and
  it did not need to: Eb, home, is inside it.
- **Why it matters:** A 5 chord over the home bass is tension and rest at the same time (a pedal point). It is the root of
  your floating sound.
- **Try this:** Replay it. Then play it yourself and, after a few seconds, move Eb4 down to D4: Bb7 over Eb, a new colour
  on the same bass.
- **Related:** `float-or-pull`.
- **Moments:** `S1` 2:36-2:54 (Ebmaj7, then Bb7sus4/Eb from 2:38 for 15.1 s, velocities 18 to 60).

### 15. The open ending (`open-ending-b7`, moment, Eb major)

- **Line:** `b7maj9:16`, exact notes Db3 Ab3 Eb4 F4 Ab4 C5 Db5 F5 Ab5 (yours, at 5:02), reads Dbmaj9, b7maj9 (checked).
- **Replay:** `{"session": "S2", "at": "4:58", "seconds": 12, "speed": 1}`.
- **Explanation:** You ended an Eb major piece on Dbmaj9, the b7 chord, borrowed from Eb minor. The piece stops with the
  door open instead of closing it.
- **Why it matters:** An ending that is not 1 feels like a question. It is a real choice, not a mistake, and this card
  keeps it so you can choose it on purpose.
- **Try this:** Replay your ending. Then play it once more and add one bar of Ebmaj9 after it, and decide which ending the
  piece wants.
- **Related:** `borrowed-b6-b7-home`.
- **Moments:** `S2` 4:58-5:09 (Gb5, Dbadd9, then Dbmaj9 held 8.95 s).

---

## 11. Receipts (read-only runs, 2026-09-14)

- `py -m arsenal.practice harmony <session>` and `py -m arsenal.practice windows <session>` for the four sessions, saved
  under the session scratchpad `jamdata/`. These gave the key areas, Lydian-4 counts, cadences, colour additions and
  every moment time above.
- `node arsenal/pianocue_voicing.mjs <items> --key <key> --voicing spread` for every seed number:
  - Eb major, Db major, Eb minor, Gb major, F major, D major
  - notes-mode reads of the exact voicings: Ab2 Eb3 G3 C4 D4 F4 Bb4 reads Cm11/Ab; Ab2 Eb3 C4 D4 F4 Bb4 reads Bb11/Ab;
    the four lament-bass bars read Bbm11, Bbm11/Ab, Bbm11/Gb, Bbm11/F; the Db cloud reads as letters
- `pianocue._note_spans` over the log for the exact notes sounding at 2:40 (010120), 5:02 (010121), 0:05.5 and 3:29
  (012540), 20:07, 20:13.5 and 20:24.5 (010144).
- Code read:
  - `arsenal/serve.py`, `arsenal/pianocue.py`, `arsenal/pianocue_voicing.mjs`
  - `arsenal/web/piano/cues.js`, `arsenal/web/piano/nashville.js`, `arsenal/web/piano/log.js` (timebase)
  - `arsenal/web/piano.js` (THEORY templates, MIDI input binding)
  - `arsenal/performance.py` (validators, store), `arsenal/practice.py` (sounding, windows, CLI), `arsenal/nashville.py`
  - `arsenal/PIANO-V2-SPEC.md` (hard rules), `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (banner
    slot, TEMPLATES note)
  - `tests/test_arsenal_pianocue.py` (pinned frame bytes)
  - The integration-notes file named in the brief does not exist on disk.

---

## 12. Decisions and open questions

### Decisions

1. **Chords as numbers.** Cards store Nashville numbers against a default key, plus optional exact MIDI notes in the
   default-key rendition. Exact notes transpose by the nearest shift (-6..+5 semitones). Key changes inside a card are
   degrees of the card key, never of the previous section.
2. **Page names are cached, not enforced.** Because THEORY has no maj9#11 or maj13#11, a card caches what the page will
   call each chord (`page_reads`) and never refuses a mismatch.
3. **POST-verb routes.** Update and delete are `POST .../update` and `POST .../delete` (the server has no PUT or DELETE),
   with `rev` / `if_rev` optimistic concurrency. `rm` is a soft delete into `trash/`.
4. **Deck and loop changes ride the existing stream** as named `deck` and `jam` events, sharing the cue id sequence and
   ring. Old pages ignore them. The page re-reads state on every (re)open; events are hints.
5. **A loop is a run.** The server owns the definition and epoch-anchored tempo segments; the page keeps time on its own
   clock. Changes land on bar or loop boundaries at least 300 ms out. A long sequence cue is only the fallback for pages
   without `jam1`.
6. **Every run is recorded.** Loops, one-shot tries and fallback loops each get a `run.json` and an append-only
   `events.jsonl`, with the resolved definition and card snapshot. Alignment with the practice log climbs a ladder:
   page clock (L1/L2), client wall clock (L3), server open time (L4, refused for buffered sessions).
7. **No practice-log format change.** No event kinds change. The only log-side additions are `meta.page_id`,
   `meta.t0_perf_ms` and an always-sent `meta.opened_at_client` on open, plus a read-only `log.timebase()`.
8. **One sound owner.** A single page owns a loop's sound (a 30 s lease on Daniel's input). Loop notes carry
   `source: "jam"` and stay out of the log and key tracker.
9. **The MIDI-out port is never an input.** A MIDI-out port name must never be bound as a MIDI input, and `practice riff`
   flags suspected loopback.
10. **`practice riff` is read-only.** It lives in `practice.py`, reports chord-slot facts at any alignment level, and
    reports beat timing only at L1/L2.
11. **The seed deck is 15 cards** built from Daniel's own moves and growth edges, with bridge-checked chords and
    log-checked moment links. It lives under `state/arsenal/jam/seed/` (git-ignored), like the log.

### Open questions

- **Q1.** Add `maj9#11`, `maj13#11` (and `sus2(#11)`) to THEORY TEMPLATES? Today the page calls Daniel's signature chord
  Bb13/Ab or Cm11/Ab, while the analyzer's reading layer calls it Abmaj9#11. Adding templates changes detection costs,
  the nashville fixtures and the spectacle rarity table.
- **Q2.** Where will loop and cue MIDI out go (a loopMIDI port into FL Studio / Kontakt?), and does the page ever listen
  on that port? The 6.8 rule must be in the page before any MIDI-out loop runs, or Claude's loops will be logged as
  Daniel's playing.
- **Q3.** Does the log lane accept `meta.page_id` and `meta.t0_perf_ms` (plus always sending `opened_at_client`)?
  Without them, exact alignment only works for sessions already open when a loop starts, and the rest falls back to
  +/-150 ms or refuses.
- **Q4.** Should loops ever show inside recordings? Default here: hidden (HUD only, never the canvas Nashville row or
  banner slot), with a per-card or per-run opt-in.
- **Q5.** This design file names Daniel's session ids and transcribes his moves under `research/in-flight/`, and the repo
  is public. Keep that, or keep only the generic seed (no moment links) in tracked files?
- **Q6.** Should one-shot cues (`try`, `play`, `hover`) also respect the sound-owner lease, so two open piano tabs never
  double Claude's voice?
- **Q7.** Loops play at a fixed tempo while Daniel plays rubato. Is a "follow me" tempo (taking the bpm from his first
  bars) wanted later, or does the loop lead?
- **Q8.** Daniel should read a few explanation / why / try lines and say whether the level is right. He reads chord
  names, not theory terms.
