# Loot Feel: rarity tiers, combos, unlocks and a chord-dex for the piano

Status: design only, one of three independent designs. 2026-09-13, night. No code in `arsenal/` was edited.
Lens: the game and TikTok feel.
Mockups: `mockups/loot-a-epic-drop.png`, `loot-b-legendary-unlock.png`, `loot-c-phrase-cashout.png`, `loot-d-session-haul.png`, `loot-e-layout-map.png`. They are HTML overlays drawn over the real receipt frames in `state/arsenal/receipts/piano-wash/final-4/`, rendered at 1080x1920 in isolated headless Chrome. They are not a build of piano.js.

Daniel, verbatim, tonight:
> "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual spectacle? Perhaps even having a rarity and fanciness scale xD"
> "Lets make the resolution be adaptive to the render window"

Earlier rules that still bind every visual: "notes dont stay lit if I have sustain pressed, when I hold sustain and other notes it should be brighest when I am pressing sustain and note at same time, velocity should be a factor as well", and "the bloom doesn't seem to decay or go down, it just stacks" (fixed in a886a0af: the LIGHT envelope and the light budget; see PIANO-V2-SPEC.md section 2).

---

## 0. The design in one paragraph

Every chord Daniel settles on gets a **tier**: COMMON gray, UNCOMMON green, RARE blue, EPIC purple, LEGENDARY orange, and beyond them **MYTHIC**, a prismatic tier in the twelve pitch hues. The tier comes from a deterministic, explainable **fanciness score**: chord quality, what's in the bass, borrowed harmony (only when the key tracker is confident) and voicing size. A thin **rarity bar** under the chord name climbs through the tier colours and stops at the tier earned. Higher tiers take longer to climb, which gives anticipation and escalation in under a second. Only the top tiers get more: a beam and a banner. A **combo** and a **fanciness gauge** build across a phrase, and the phrase **cashes out in the rest** after it, so the big reveal lands in the silence and never on top of the music. **NEW CHORD UNLOCKED** fires when a chord species appears for the first time in the practice log. Everything is collected in a **chord-dex** (a browsable page) and a recordable **SESSION HAUL** end card. Restraint is the core rule. Common chords show nothing extra. The chord name is never moved, covered or delayed. There are no sounds, no fail states and no randomness, so the same voicing always gets the same tier.

---

## 1. The one-second read

A viewer scrolling TikTok gives the clip about one second. In that second, three things must land without explanation:

1. **"That chord was special."** Gamers already read the gray, green, blue, purple, orange ladder: WoW item quality, Fortnite, Destiny, Borderlands. A purple word above a chord name means epic to anyone who has played a game since 2004. The word sits next to the chord name, where the eye already is (the chord name is the focal point of the frame, 170 px Archivo 800). Nothing important goes in the corners.
2. **"Something is building."** A combo number (`×5`) in a ring, with a vertical gauge filling through the tier colours. It borrows the grammar of fighting-game super meters and Beat Saber's multiplier ring.
3. **"He just found something new."** Achievement-toast language: `NEW CHORD UNLOCKED` in expanded caps, with the chord species in words underneath (`m11 · MINOR ELEVENTH`). It doubles as a lesson for the viewer.

Legibility check in the mockups: `loot-a` and `loot-b` put the tier word 20 px above the chord name in 34 px expanded caps with wide tracking. It reads at phone size as a word, not as texture.

---

## 2. Why loot reveals feel good, and what this design takes and refuses

Principles, with how each maps onto a piano played live:

| Principle | In games | Here |
|---|---|---|
| **Anticipation** | Diablo's loot beam colour shows before you read the item. Hearthstone packs glow by rarity before the card flips. Genshin's wish meteor turns gold before a 5-star. A PC Gamer piece on loot-box art quotes designer Jeremy Craig: "It's all about building the anticipation." | The **rarity climb**: the bar passes through the lower colours before it stops. The phrase gauge fills during the playing, and the reveal waits for the rest. |
| **Escalation** | The size and length of a reveal scale with rarity. A tier 1 beam is small; a top-tier beam is grandiose. | The climb takes 80 ms at COMMON and 530 ms at MYTHIC. Only LEGENDARY and up get a beam and a banner. Only MYTHIC goes prismatic. |
| **Restraint** | Gray and white items make purple mean something. Most drops are junk. | COMMON shows nothing but an 80 ms gray tick. The tier cutoffs are calibrated so about half of all chords are COMMON (section 5.5). Banners are capped and queued. |
| **Consistency** | One colour means one tier everywhere: ground beam, tooltip, inventory frame. | The tier colours appear only in UI chrome: tag, bar, banner rules, gauge, dex card frames. They never touch keys or trails, which keep the pitch colours. |
| **Stinger sound** | Every loot reveal has an audio sting. | **Refused.** The music is the audio, and a chime would ruin both the recording and the practice. The visuals carry everything. |
| **Near miss, variable reward** | Case roulettes slow down past the jackpot. Drop odds are random. | **Refused.** The climb lands exactly on the earned tier and never teases the next one. Scoring is deterministic: the same voicing in the same key always gets the same tier. It is skill feedback wearing loot clothes, not a slot machine. |
| **Collection** | Pokédex silhouettes, "shiny" variants, gear with a best "god roll". | The chord-dex with silhouettes, **shiny** first finds, and a per-species **best roll** (section 8). |

Sources: the PC Gamer article, Game Developer's loot-tips piece, and TV Tropes' "Color-Coded Item Tiers" (links at the end). The specifics about Diablo, Hearthstone, Genshin, CS:GO, Pokémon and Xbox are from memory and were not re-verified tonight.

---

## 3. Two axes, deliberately separated

Daniel's phrase names two things: **rarity** and **fanciness**. Loot games merge them. This design keeps them apart, because merging them would be dishonest on a public video:

- **Fanciness is the tier.** It is intrinsic and computed from the music, so it is the same for every viewer and every player. A Dm11/G voiced across three octaves is LEGENDARY whoever plays it. This is what the TikTok viewer reads.
- **Rarity-for-Daniel is discovery.** It is personal and comes from the practice log: NEW CHORD UNLOCKED, NEW BEST, SHINY. It says "new to him", never "new to music".

The one crossover is the **shiny** modifier. When a species is first found in an EPIC-or-better roll, the unlock banner gets a foil finish and the dex card stays shiny forever.

---

## 4. The tier ladder

Colours are defined in OKLCH for the dark stage. Hex values are the sRGB approximations used in the mockups. Each tier is also coded by **pips** (filled diamonds) and a **word**, so the ladder never depends on hue alone (green and orange are a classic colour-blind confusion).

| # | Tier | Colour | Pips | Points (DROP_TABLE v1) | Presentation | Target share of chords |
|---|---|---|---|---|---|---|
| 0 | COMMON | oklch(0.80 0.01 260), #b8bcc4 | 1 | 0–1 | 80 ms gray tick under the name, then gone. No tag. | ~50% |
| 1 | UNCOMMON | oklch(0.82 0.21 145), #4fe36b | 2 | 2–3 | Bar climbs to green (170 ms) and stays under the name. No tag. | ~25% |
| 2 | RARE | oklch(0.70 0.16 252), #3d9bff | 3 | 4–5 | Bar climbs to blue (260 ms). Tag `RARE` fades in above the name. | ~15% |
| 3 | EPIC | oklch(0.66 0.23 305), #b05cff | 4 | 6–7 | Blue climb, then purple (350 ms). Tag `EPIC`. One 380 ms foil glint across the name glyphs. | ~7% |
| 4 | LEGENDARY | oklch(0.78 0.17 60), #ff9a2e | 5 | 8–9 | Orange (440 ms). Tag `LEGENDARY`. A beam rises behind the name. The banner shows the why-line. The 3D rail line pulses orange for 0.8 s. | ~2.5% |
| 5 | MYTHIC | prismatic: the twelve pitch hues in circle-of-fifths order, white-gold core | 6 | 10+ | Climb pauses on orange for 90 ms, then goes prismatic (530 ms total). Tag `MYTHIC` in foil. Prismatic beam and banner. The rail runs a prismatic sweep left to right over 600 ms. The gauge flashes. | ≤0.5% |

MYTHIC being prismatic in the **pitch palette** is on purpose. The piano's own identity (the circle of fifths walked through hue) is the colour beyond orange. It only shows on thin elements (the bar, the tag glyphs, the banner rules), so it never becomes a rainbow wash.

---

## 5. The fanciness score (DROP_TABLE v1)

Pure, deterministic and explainable. Every point it awards becomes a **why** entry, and the banner shows those entries. The score runs once when the chord label settles (`overlay.shown` changes, which already includes the 120 ms settle for rolled chords), over **`harmonySet`** notes (spec 6.1). That keeps a pedal ride from scoring a smear.

### 5.1 Points

**Quality** (from `info.suffix`, the `Theory.TEMPLATES` suffix):

| Points | Suffixes | Why-text |
|---|---|---|
| 0 | `""` (major), `m`, `5` | none |
| 1 | `sus2`, `sus4`, `6`, `m6`, `dim`, `aug`, `add9`, `m(add9)` | "sus", "6th", "add9"… |
| 2 | `7`, `maj7`, `m7`, `m7b5`, `dim7`, `6/9`, `m6/9`, `add11`, `7sus4` | "7th", "half-diminished", "six-nine"… |
| 3 | `9`, `maj9`, `m9`, `9sus4`, `m(maj7)`, `7#5`, `maj7#5`, `7b5` | "9th", "minor-major 7th", "altered 5th" |
| 4 | `11`, `m11`, `13`, `maj13`, `m13`, `maj7#11`, `7#11`, `7b9`, `7#9` | "11th", "13th", "#11", "b9", "#9" |

**Bass** (when `info.bass` is set):
- +1 for an **inversion**, meaning the bass is the chord's 3rd, 5th or 7th: `F/A`, `C/G`, `Abmaj7/C`. Why: "A in the bass".
- +2 for an **extension or foreign bass**, meaning the bass is the 9th, 11th or 13th, or the chord came from detect's slash path (a foreign bass under a simple upper chord): `Dm11/G`, `C/D`. Why: "G in the bass".

**Borrowed or chromatic:** +2 when `nashville(info, key).diatonic === false`, **and** the tracker's confidence is `sure` or `fair`, **and** it is not a candidate switch in progress. Why: "borrowed ♭VII", using the same text the Nashville row shows, so the two never disagree. With low confidence the bonus is **0**. A wrong key guess must not pay out, because it would teach Daniel the wrong theory.

**Voicing** (harmony notes, doublings included):
- +1 for 5 or more notes. Why: "5 notes"
- +1 for a spread (lowest to highest) of 24 semitones or more. Why: "2-octave spread"
- +1 for a spread of 36 semitones or more. Why: "3-octave spread"

**No drop at all** for `kind` note, interval or cluster. Mashing is not rewarded.

Velocity does **not** change the tier (it is loudness, not fanciness). It does change reveal energy: the bar's landing flash is 1.0 to 1.3x brightness by velocity, and it respects the LIGHT rule "velocity should be a factor".

### 5.2 Tier cutoffs

Points 0–1 COMMON, 2–3 UNCOMMON, 4–5 RARE, 6–7 EPIC, 8–9 LEGENDARY, 10+ MYTHIC. **These cutoffs are the only tuning knob** (see 5.5).

### 5.3 Worked examples from Daniel's own vocabulary

| Played | Points | Tier |
|---|---|---|
| F, close triad | 0 | COMMON |
| F/A | 0 + 1 (inversion) = 1 | COMMON |
| C/G | 1 | COMMON |
| Dm, pedalled, 5 notes over 26 semitones | 0 + 1 + 1 = 2 | UNCOMMON |
| Bbmaj7, close, 4 notes | 2 | UNCOMMON |
| Bbmaj7, two hands, 6 notes over 27 semitones | 2 + 1 + 1 = 4 | RARE |
| Fmaj9, 5 notes over 24 semitones | 3 + 1 + 1 = 5 | RARE |
| C/D, 4 notes | 0 + 2 = 2 | UNCOMMON |
| Dm11/G, close, 6 notes within 2 octaves | 4 + 2 + 1 = 7 | EPIC |
| **Dm11/G as voiced in receipt `04-hold-2bars.jpg`** (about 11 notes, G2 to A5, 38 semitones) | 4 + 2 + 1 + 1 + 1 = 9 | **LEGENDARY** |
| Abmaj7/C in a confident C major (♭VI) | 2 + 1 + 2 = 5 | RARE |
| the same, 5 notes wide | 5 + 2 = 7 | EPIC |
| E7#9/G# in a confident C major (III7), 6 notes over 36 semitones | 4 + 1 + 2 + 3 = 10 | MYTHIC |
| C D E F G mashed (cluster) | none | no drop |

The same Dm11/G gets two tiers depending on voicing. That is the **best roll** idea (section 8.4): a species has many rolls, and voicing is the affix. Mockup A shows the EPIC presentation over the wide-voiced frame, but under v1 that frame actually scores LEGENDARY (mockup B). A is there to show the EPIC state.

### 5.4 Gates against false drops

- **harmonySet only**, so pedal-held stale notes do not add points.
- **Settled label only.** It reuses the overlay's existing 120 ms settle after a note-on and 300 ms after a release.
- **Unlock dwell:** a discovery needs the label to hold the chord for at least 450 ms. A passing chord still gets its tier, but not a dex entry.
- **Repeats:** if the chord name matches the current or previous two shown chords, the tier bar re-shows but nothing new drops: no re-banner, no combo growth, and gauge gain ×0.2.
- **Key confidence** gates the borrowed bonus and MOVE discoveries.

### 5.5 Calibration: the drop table is tuned to Daniel, then frozen

1. Replay the ~55 s pedalled F-major passage from `wash_check.mjs`, and every session under `state/arsenal/performance/`, through the scorer. Then report the tier histogram.
2. Adjust only the cutoffs until the histogram falls in the target bands of section 4 (about 50/25/15/7/2.5/≤0.5 %).
3. Freeze the result as `DROP_TABLE v1` with a dated receipt. Tiers must not drift silently, because a LEGENDARY in March has to mean what it meant in September. A later retune is a new version, and history keeps the version each drop was scored under.

---

## 6. Presentation grammar, frame by frame

Everything is clock-driven (spec 6.2: never frame counts). Times are measured from the moment the chord label settles, t = 0. The chord name itself behaves exactly as today.

**Every drop (UNCOMMON and up):**
- **0 ms:** if a previous bar is up, it collapses to the centre over 120 ms before the new one climbs. Two bars never overlap.
- **0 → (80 + 90·tier) ms: the climb.** The bar grows outward from the centre to the width of the chord name (clamped 240–760 px). Its colour steps through gray, green, blue, purple and orange up to the earned tier. Each step boundary gets a 40 ms brightness tick, which is felt more than seen.
- **Landing:** a 60 ms flash at 1.0–1.3x brightness, scaled by velocity, then it settles.
- **The bar holds** as long as the label shows, and fades with `overlay.labelAlpha`.
- **RARE and up:** the tag (pips plus word) fades in over 120 ms, starting 40 ms after landing.

**EPIC:** adds one foil glint. A narrow diagonal highlight crosses the name glyphs in 380 ms, **clipped to the glyph alpha**. Mockup finding M3: an unclipped blend rectangle turned the name muddy.

**LEGENDARY:** adds three things.
- **Beam:** rises behind the label from the chips line up to y = 0 over 220 ms, holds 700 ms, then fades over 900 ms. Peak alpha is 0.30, normal blending, under the label's plate.
- **Banner:** unfurls from the centre over 180 ms (scaleX 0 → 1) and holds 1.8 s. It carries the tier word and the why-line, e.g. `LEGENDARY · 11th · G in the bass · 3-octave spread`.
- **3D rail line** (the thin amber `railLine` at the key backs): tints toward orange **at equal luminance** for 0.8 s, so bloom does not change.

**MYTHIC:** the climb pauses on orange for 90 ms, then goes prismatic. Tag and banner get a prismatic foil. The rail sweeps the twelve pitch hues left to right in 600 ms. The gauge flashes once. The banner holds for 2.4 s.

**Level-up tick, mid-phrase:** when the gauge crosses a tier cutoff, the combo medallion pulses once for 200 ms. Nothing else happens until the phrase ends.

---

## 7. The combo, the fanciness gauge and the phrase cash-out

### 7.1 Combo (the `×N` medallion)
- **+1** on each settled, *distinct* chord change whose tier is UNCOMMON or higher, **or** whose move from the previous chord is **smooth**. Smooth means at least 2 pitch classes in common and a top voice that moves 2 semitones or less.
  - The smooth rule rewards musicianship, not just jazz vocabulary. A beautifully voice-led F → C/E → Dm → Bbmaj7 builds a combo even though three of those chords are COMMON.
- **Holds** (no change) on a COMMON change that isn't smooth, and on repeats.
- **Resets only in a rest** (7.3). It is never "broken" mid-phrase, and there is no red, no X and no fail sound.
- The medallion is hidden below ×2. Its ring shows the colour of the current gauge tier.

### 7.2 Gauge (level L, 0–100)
- **Gain per drop:** `TIER_GAIN[tier] × (1 + 0.12·min(combo, 10))`, with `TIER_GAIN = [1, 3, 6, 10, 16, 24]`. A smooth move adds a flat +2. Repeats get ×0.2.
- **Decay:** exponential, τ = 10 s, while a phrase is live. A phrase has to keep being fancy.
- **Display:** the fill eases up over 0.12 s and down over 0.5 s. The fill is a vertical gradient through the tier colours, and tick marks at the phrase cutoffs are drawn in those colours.
- **Phrase cutoffs on peak L:** 25 RARE, 45 EPIC, 70 LEGENDARY, 92 MYTHIC. Below 25 there is no cash-out.
- **Sanity check:** eight distinct RARE chords at 1.5 s each gain about 68 before decay. With decay the peak is about 45, which grades EPIC. A LEGENDARY phrase needs EPIC and LEGENDARY drops strung together.

### 7.3 Phrase end and the cash-out (the reveal lands in the rest)
- **The phrase ends** when nothing has sounded for 1.2 s (pedal up, no keys), **or** when 3.0 s pass with no new note-on while only pedal-held notes ring. A long pedalled ring-out counts as a rest.
- **Cash-out, peak at RARE or higher:**
  - **0–500 ms:** the gauge drains upward into the medallion (anticipation), then the medallion bursts in an expanding ring (400 ms, normal blend).
  - **The banner:** `PHRASE COMPLETE` / pips + tier word / stats line, e.g. `7 chords · ×6 combo · 2 borrowed · smooth voice leading`.
  - **Timing:** holds 2.2 s. The phrase socket under the gauge fills with the tier colour, a small record of the last phrase.
- **Below RARE:** the gauge drains silently over 0.8 s. Restraint.
- **If Daniel starts playing during a cash-out,** the banner fast-fades over 0.6 s and a new phrase begins. The reveal never blocks the music.

Why the rest: after the lift, the frame empties (the trails fade on their 3.2 s afterglow and the staff dims to 0.4). The reveal gets space instead of fighting the columns for attention. On TikTok it is also a natural loop or cut point: the clip ends on `LEGENDARY PHRASE`.

---

## 8. Discoveries and the chord-dex

### 8.1 What can be discovered (the dex pages)

| Page | Identity | Size | In-canvas show |
|---|---|---|---|
| **QUALITIES** | the template suffix, root-independent (`m11`), plus the power chord | 37 | full `NEW CHORD UNLOCKED` banner |
| **FORMS** | quality × bass type (root / inversion / extension bass / foreign bass) | ≤148 | banner only if the roll is RARE or higher, otherwise a `+1 DEX` chip |
| **CHORDS** | the exact spelled name (`Fmaj9/A`) | open-ended | a `+1 DEX` chip beside the tag, no banner |
| **MOVES** | a numbered move inside a confident key (`F major: 4 → 5/7`), from the Nashville numbers | open-ended | none live; SESSION HAUL card only |

The QUALITY banner reads, in two lines:
- `NEW CHORD UNLOCKED`, 38 px, Archivo 800 at width 125, tracking 0.1 em, white with a glow in the tier colour
- `m11 · MINOR ELEVENTH · DEX 24 / 37`, 22 px caps in the tier colour

If the drop is also LEGENDARY or higher, **the two merge into one banner**: the unlock text plus a `LEGENDARY` tag, as in mockup B. Two banners never show at once.

### 8.2 Honesty and the first-week flood
- **"NEW" means new since logging began.** The dex page says `since 13 Sep 2026 (practice log start)`. The in-canvas banner uses the game register, not a biography claim ("false autobiography is worse than amnesia").
- **Backfill:** before the loot layer ships, the dex builder runs over every logged session.
- **Starter deck** (a loot-game convention, and **the question for Daniel** in section 14): pre-unlock the COMMON and UNCOMMON qualities (major, minor, power, sus, 6, add9, 7, maj7, m7…). The first week then won't be a stream of `NEW CHORD UNLOCKED: minor`, and banners only fire for species that feel like a find.
- **Queue:** at most one unlock banner per 6 s, with extras queued. At most 3 unlock banners per session in the first session; the rest fold into the haul card ("+14 more").
- **Log gaps:** `log.js` drops a batch after one failed retry. The dex treats the server dex plus the in-session memory as its source, so a dropped batch can only cause a missed unlock, never a false one.

### 8.3 Shiny
A species first discovered in an EPIC-or-better roll is **shiny**. Its banner gets a moving foil gradient, and its dex card keeps a foil frame. It can't be earned retroactively.

### 8.4 Best roll ("god roll")
Each species keeps its **best-scoring roll**: the chord, notes, key, tier, points, why-line, session and timestamp. Beating it later adds `· NEW BEST` to the tag line. There is no banner; it is a quiet personal record.

### 8.5 Data (derived, git-ignored: `state/arsenal/performance/dex.json`)

```json
{ "api": "dex/1", "table": "DROP_TABLE v1", "since": "2026-09-13T21:04:00",
  "starter_deck": true,
  "qualities": { "m11": { "first": {"session": "20260913-...", "t_ms": 761200, "chord": "Dm11/G", "tier": 4},
                          "count": 17, "seconds": 41.2, "shiny": true,
                          "best": {"session": "...", "t_ms": 761200, "chord": "Dm11/G", "notes": ["G2","D3","..."],
                                   "key": "F major", "tier": 4, "points": 9, "why": ["11th","G in the bass","3-octave spread"]} } },
  "forms":  { "m11|extension-bass": { "...": "same shape" } },
  "chords": { "Dm11/G": { "...": "same shape" } },
  "moves":  { "F major": { "4>5/7": { "first": {}, "count": 6 } } } }
```

- **Scoring twins.** `arsenal/web/piano/loot.js` (pure scorer) and `arsenal/loot.py` (the same scorer plus `dex_update(dex, events)`) share `tests/fixtures/loot_cases.json`, the way `nashville.js` and `nashville.py` already do. Chord log events may carry a `loot: {tier, points, why, table}` cache, but the analyzer re-derives when it is missing or when `table` differs. The gates are trusted, not the author.
- **Route (for the log lane to add):** `GET /api/performance/dex`. The dex is rebuilt at session close. The page fetches it at boot and applies discoveries in memory.
- **Summary additions:** `summary.loot = { histogram, best_drop, unlocks, longest_combo, phrases: [{t_ms, tier, chords, combo}] }`. `summary.md` gains one card line, e.g. "Your one LEGENDARY tonight was Dm11/G at 12:41 (11th, G in the bass, 3-octave spread)." That gives the banter agents a timestamped fact to ask about.

### 8.6 The dex page: `/web/piano-dex.html` (browsed after playing, not recorded)
- **Tabs:** Qualities · Forms · Chords · Moves · Keys. Each has a completion counter (`QUALITIES 24/37`).
- **Discovered cards** are framed in the tier colour of their best roll (shiny cards in foil). A card shows:
  - the name and its words (`m11 · minor eleventh`) and a one-line lore note (appendix A)
  - first found (date and session time) and times played
  - the best roll: a mini grand staff of its notes plus its why-line
  - the Nashville numbers it has appeared as (`as 6m in F`, `as 2m in C`)
- **Undiscovered cards** are **silhouettes**: a one-octave mini keyboard with dots on the template intervals, the name as `???` and a hint ("a minor 7th with an added 11th"). A `Show names` toggle is there for study. The silhouettes double as an ear-training map, pointing Daniel at theory he said he doesn't fully understand yet.
- **Replay the moment** (later): the log has timestamps, so the page could feed a drop's events back through `__piano.midiMessage` and re-render it at 60 fps for a clip after the fact. That is MIDI only; the audio would have to come from his instrument.

### 8.7 SESSION HAUL: the recordable end card (mockup D)
- **Summon and dismiss:** `H` in the HUD, or the KeyLab mark pad from spec 6.5. Any note dismisses it over 300 ms. It never appears on its own.
- **Contents,** from the in-memory session ledger (instant, no server round trip):
  - drops by tier, as a histogram in the tier colours
  - the best drop with its why-line and time
  - new in the dex, as chips framed in the tier colours
  - longest combo, qualities found (n/37), moves found
  - **home chords:** the chords he returned to most, unranked. It keeps the card warm rather than competitive.
- **Placement:** the title sits in the chord-label slot (nothing is sounding). The card sits in the staff area. **The staff and pedal mark hide while it shows** (mockup finding M4: the staff barline showed through the translucent card).

---

## 9. Where everything lives on the 9:16 frame (1080x1920)

Reference pixels at 1080x1920 (see 10.3 for the adaptive-resolution rule). Existing geometry was measured from `LAYOUT` in piano.js HEAD (unchanged in piano-next.js), `drawLabel`, `drawStaff`, `pedalMarkSpec` in piano-next.js, and the receipt frames. The map is drawn in `mockups/loot-e-layout-map.png`.

### 9.1 Reserved: TikTok's own UI
Published guidance varies by source. This design uses the union:
- **Header:** y 0–150
- **Action-button column:** x ≥ 916, for y 800–1596
- **Caption, sound and progress:** y ≥ 1596 (sources give 270–484 px; the ~324 px figure is used here)

### 9.2 Existing elements (not moved by this design)

| Element | Box |
|---|---|
| Chord name glyphs (label layer 10–1070 × 148–488; baseline y 338; tallest raised accidental top ≈ y 208) | x ≈ 190–890 (centred, width varies), y 205–365 |
| Note chips (baseline y 426) | y 392–436 |
| Nashville row (other build; **placement to be confirmed with that build**) | reserved y 440–486 |
| Staff layer, including the scrim | x 110–970, y 500–1100 |
| Staff lines, brace to right barline | x 140–932, y 620–980 (the G clef rises to y ≈ 586) |
| Pedal mark (piano-next `pedalMarkSpec`) | x 177–345, y 990–1086 |
| Trails | rise from the rail at y ≈ 1370 to the top of the frame |
| Keys | y 1370–1590 |

### 9.3 New elements

| Element | Box / anchor | Shown | Notes |
|---|---|---|---|
| **Tier tag** (pips + word) | centred at x 540, y 158–204, max width 560 | RARE and up | Pips 18 px (M5), 34 px Archivo 800, `fontStretch = "expanded"`, tracking 0.3 em, soft dark plate. Clear of the header (150) and the accidental tops (208). |
| **Rarity bar** | centred, y 370–378, width = clamp(name width + 60, 240, 760) | UNCOMMON and up (COMMON: an 80 ms tick) | 9 px below the slash descender (≈361), 14 px above the chip caps (392). |
| **Beam** | x 540 ± min(nameW/2 + 60, 290), y 0–540 | LEGENDARY and up | Renders under the label mesh (renderOrder). It passes through the TikTok header, which is fine because it isn't text. |
| **Drop / unlock banner** | x 164–916, **y 488–578** (M1: was 492–588, touched the G clef) | LEGENDARY+, QUALITY unlocks, RARE+ FORM unlocks | Dark ribbon at 0.84 alpha with tier-colour rules above and below. Clears the Nashville row (486) and the clef top (586). |
| **Cash-out banner** | x 164–916, **y 452–580** (M2) | in rests, peak RARE+ | The label and Nashville row are faded in rests. The staff is at 0.4 alpha. |
| **Combo medallion** | centre (62, 590), r 44 → x 18–106, y 546–634 | combo ≥ ×2 | Left edge is not covered by TikTok. 34 px clear of the brace (x 140). |
| **Fanciness gauge** | x 50–74, y 650–970 | a phrase is live, or L > 0 | Fades to 0 after 6 s idle. Clear of Upright Roll's 12 px left pedal lane (x 0–12). |
| **Phrase socket** | centre (62, 1016), r 20 | after the first cash-out | Clear of the pedal mark (x ≥ 177). |
| **`+1 DEX` chip** | right of the tag, same baseline, x ≤ 900 | CHORD unlocks | 22 px caps. |
| **Rail pulse** | the existing 3D `railLine`, y ≈ 1370 | LEGENDARY and up | Recolour only, at equal luminance. |
| **Session haul title** | label slot, y 200–350 | on summon | |
| **Session haul card** | x 96–916, y 470–1330 | on summon (in rests) | The staff and pedal mark hide while it shows. |

**Collision proof to automate (receipt R8):** `__piano.loot.layout()` returns every loot rectangle in reference pixels, plus the live label glyph bounding box (from `measureRuns`). The receipt fails if any in-play loot rectangle intersects the glyph box, the chips row, the staff-lines box, the pedal mark, or a TikTok reserved zone.

### 9.4 Findings about existing elements (for the layout owner, not for loot)
- **TikTok button column:** the column (x ≥ 916, y 800–1596) covers the staff's right barline (x 932, y 800–980) and the right-hand keys. The chord name and chips are fully safe. If TikTok framing matters, narrowing the staff from w 860 to w 800 (x 140–900) clears the barline.
- **TikTok caption zone:** starts at y 1596, right under the key fronts (y 1590). Nothing important should ever go lower.
- **Why the meter isn't in the empty floor band** (y 1590–1920): that band looks like free space but is exactly TikTok's caption zone.

### 9.5 16:9 (1920x1080)
`LAYOUT` puts the label at left (cx 500, cy 196, left-aligned) and the staff at right (x 1240–1880, y 12–532). Loot follows the name:
- **Tag:** left-aligned at x 74, y 60–100
- **Rarity bar:** under the name, y 228–236, left-aligned to the name width
- **Banner:** x 74–834, y 330–420
- **Gauge:** vertical, x 1108–1132, y 150–470
- **Medallion:** centre (1120, 92)
- **Session haul card:** x 1180–1880, y 40–560; the staff hides while it shows

There are no TikTok zones in this framing. A 5% title-safe margin is kept.

---

## 10. Staying inside the light budget, the frame rate and the canvas

### 10.1 Light
- **Where loot renders:** all of it goes into `overlayScene`, which draws after `composer.render` (after bloom, tone mapping and OutputPass) with normal alpha blending. None of it feeds the bloom threshold, the HDR trails or the `LIGHT_BUDGET`. It can't make the columns stack.
- **No new additive 3D light.** Tier-coloured sparks were considered and **rejected**: they would add light into the scene. The only 3D change is the rail line's *hue* at equal luminance.
- **Loot luma budget (its own acceptance, R4):**
  - **Label band** (y 150–490): at the peak of a LEGENDARY beam, mean luma is at most +0.035 over the same frame with loot off.
  - **Staff box:** in-play loot only adds dark banner plate, so its mean luma can only drop.
- **Spec 6.6 pedal storm:** runs with loot **Off**, because it measures the scheme. The loot receipt runs separately.
- **Readability plates** stay as spec section 2 defines them. The banner brings its own dark ribbon, and the tag brings its own soft plate.

### 10.2 60 fps at 1080x1920 on the RX 9070 XT
- **Per frame:** at most 8 extra quads (tag, bar, beam, banner, medallion, gauge, socket, card). The bar, gauge and beam are shader quads driven only by uniforms (progress, colour stops, alpha). They use analytic anti-aliasing (`smoothstep` over `fwidth`) with no strokes under 2 reference pixels, so they stay clean at any scale and don't reintroduce aliasing.
- **Canvas2D redraws happen on events only:** a drop, an unlock, a combo change or a cash-out, about 2 per second worst case. Each is at most a 760×110 upload. The tag and banner are pre-rasterised when they change, not every frame.
- **Scoring** runs once per settled chord, O(notes). Dex lookups are `Map` gets.
- **Expected cost** is well under 0.2 ms per frame. Receipt R6 measures the p95 frame-time delta, loot on vs off, over the pedal storm at 1080x1920. It must be at most 0.3 ms, with fps at 60 or above during REC.

### 10.3 Resolution adaptive to the render window (Daniel's second ask)
All coordinates in this document are in the **reference framing** (1080x1920 or 1920x1080). When the renderer follows the window, loot layers allocate canvases at `ref × k`, where `k = drawingBufferHeight / 1920` (or `/1080` in 16:9), and multiply positions by `k`. That is the same rule the chord and staff overlay needs, so text stays crisp at native pixels. Recording stays at exactly 1080x1920 (k = 1 for the recorded target).

### 10.4 Inside the recorded canvas
Every in-play loot element and the haul card are WebGL overlay meshes in the canvas, so the recorder captures them. The mode selector and hotkeys live in the HUD and topbar, which are not recorded.

---

## 11. Fun for the player, not noise: the rules

1. **The chord name is sacred.** Loot never moves, delays, covers or recolours it. The one exception is the 380 ms EPIC foil glint, clipped to the glyphs.
2. **Music first.** Big reveals wait for rests (the cash-out). The only exceptions are LEGENDARY-and-up drops, which are rare by construction.
3. **No sounds,** ever.
4. **No negative feedback.** No "combo broken", no red, no fail states. The gauge drains quietly.
5. **Honest and deterministic.** Every tier can explain itself (the why-line). Nothing is random. The climb never teases.
6. **Repeats don't farm.** Replaying a chord doesn't re-drop. Only a better roll counts (`NEW BEST`).
7. **Caps and a queue.** One banner at a time, at least 6 s apart. LEGENDARY suppresses other banners for 6 s. Extras fold into the haul card.
8. **A long-game goal without pressure.** The dex's 37 qualities and silhouettes give him things to find, and each find teaches a name.
9. **Goodhart guard.** Fancier isn't better music. Smooth voice leading builds combos on plain chords, and the haul card shows *home chords* beside the best drop.
10. **Modes** (HUD select plus `G` to cycle, stored in localStorage `arsenal.piano.loot`):
    - **Show** (default): everything above, with caps.
    - **Practice:** only the rarity bar under the name. No tags, banners or gauge. Discoveries stay silent until the haul card.
    - **Off:** nothing.

    REC never changes the mode on its own.

---

## 12. Architecture and integration (after the current build lands; nothing edited tonight)

- **`arsenal/web/piano/loot.js`,** an ES module in two halves:
  - **Pure half:** `DROP_TABLE`, `score(info, harmonyNotes, nns, keyState) → {points, tier, why[]}`, `species(info) → {quality, form, chord}`, `smooth(prevNotes, notes) → bool`, `phraseGrade(peakL)`. Node-tested against the shared fixtures.
  - **Presenter:** `createLootLayer({ THREE, overlayScene, framing, fontState, noteCss, pitchHues })` → `{ chord(shownInfo, extras, t), update(dt, t, {soundingCount, heldCount, lastOnT, labelAlpha}), setMode(m), haul(on), resize(framing), layout(), stats(), dispose() }`.
- **Twin:** `arsenal/loot.py` (scorer plus dex), with `tests/fixtures/loot_cases.json`, `tests/loot_js.test.mjs` and `tests/test_arsenal_loot.py`.
- **Hooks in piano-next.js** (a few lines, wired by Vandor):
  - in `overlay.update`, where `this.shown` changes: call `loot.chord(this.shown, {nns, keyState, harmonyNotes}, t)`
  - once per frame: `loot.update(...)`
  - at boot: fetch the dex
  - `window.__piano.loot = { stats, layout, dex, mode }`
- **Log lane additions** (owned by that build): an optional `loot` field on chord events, `GET /api/performance/dex`, `summary.loot`, and the dex rebuild at close.
- **Fonts:** piano.html already loads Archivo at widths 62–125 (HEAD piano.html line 10). `loadFonts` should also load `800 34px "Archivo"` with the expanded stretch descriptor. The canvas sets `ctx.fontStretch = "expanded"`.

---

## 13. Receipts (acceptance)

| # | Receipt | Pass |
|---|---|---|
| R1 | Scorer twin fixtures, node and pytest | at least 25 cases including every row of 5.3; a low-confidence key gives no borrowed points; clusters give no drop; JS and Python agree on every case |
| R2 | Economy | tier histogram over the wash_check passage and all logged sessions falls in the section 4 bands; cutoffs frozen as v1 with a dated receipt |
| R3 | Noise, headless, 60 s dense pedalled passage, Show mode | at most 6 banners per minute; at most 2 beams per minute; tag visible at most 40% of the time; zero overlapping banners |
| R4 | Luma | label band at most +0.035 at a LEGENDARY beam's peak vs loot off; staff box at most +0 |
| R5 | Legibility | snapshot 1.0 s after a drop of each tier: tag-band pixels match the tier colour (ΔE under 10); the chord-name label layer is byte-identical with loot on and off, outside the foil window |
| R6 | Performance | p95 frame-time delta at most 0.3 ms at 1080x1920; at least 60 fps while recording |
| R7 | Dex round trip | backfill, then an unseen species banners, then the same species again doesn't, then close merges into dex.json; the haul card matches the ledger |
| R8 | Collisions | `layout()` rectangles clear the glyph box, chips, staff lines, pedal mark and TikTok zones, in both framings and at k = 0.5, 1 and 2 |

---

## 14. Question for Daniel (one)

**Should the dex start with a "starter deck"** (major, minor, sus, 6ths, add9s and plain 7ths already unlocked), so `NEW CHORD UNLOCKED` only pops for chords that feel like a find? Or should it start empty and be honest from zero, which means a flood of unlocks in the first sessions?

This design recommends the starter deck.

---

## 15. Risks

1. **Goodhart.** The loot layer could pull his playing toward cliché extensions. Mitigations: smooth voice leading earns combo, home chords appear on the haul card, Practice mode exists, and fanciness is never called "better".
2. **Key-tracker errors** would create false "borrowed" points and false MOVE unlocks. Mitigation: gated on `sure`/`fair` confidence and a held key, which the tracker already provides.
3. **Detection churn in rolled or pedalled passages** could give false drops. Mitigations: harmonySet, the settle, a 450 ms unlock dwell, and no drop for clusters.
4. **First-week unlock flood.** Mitigations: starter deck, backfill, banner priority, queue caps.
5. **Recording noise and cheesiness.** Loot language can cheapen a sincere piano video. Mitigations: restraint by default (COMMON shows nothing), caps, Practice and Off modes. MYTHIC's prismatic stays on thin elements. Daniel's taste is the final gate.
6. **Tier colours vs pitch colours.** Blue and purple exist in both. Mitigation: tier colour appears only in UI chrome, always with a word and pips, and never on keys or trails.
7. **Parallel builds.** The overlay code, the Nashville row position and harmonySet are all in flight. Mitigation: loot is a separate module with narrow hooks. **The reserved Nashville row (y 440–486) must be confirmed with that build**, or the banner coordinates move.
8. **Resolution-adaptive rework** changes overlay scaling. Mitigation: everything is specified in reference pixels with one scale factor `k`, and R8 runs at several k values.
9. **Log gaps** (dropped batches) can cause a missed or late unlock. Never a false one, because the server dex plus the session memory is the source.
10. **Calibration drift** as Daniel improves. Mitigation: a versioned DROP_TABLE, with every drop recorded under its table version.
11. **Luma creep** if later tweaks raise beam alpha or add sparks. R4 guards it.

---

## 16. Mockup findings (what the renders showed that paper did not)

- **M1:** the unlock banner at y 492–588 touched the top of the treble clef (≈ y 586). It moves to y 488–578.
- **M2:** the cash-out banner at 458–604 overlapped the clef. It moves to y 452–580, with the stats line at 20 px.
- **M3:** the EPIC foil drawn as a blended rectangle turned the name into a dull box. It must be clipped to glyph alpha (`source-atop` on the label canvas, or a mask on the label texture's alpha).
- **M4:** the translucent haul card let the staff's right barline show through. The staff and pedal mark hide while the card shows.
- **M5:** 13 px pips read as a glyph string at phone scale. They grow to 18 px with 9 px gaps.
- **M6:** the tag word in expanded caps (`LEGENDARY`, pips included, about 490 px wide) reads instantly and fits the 560 px budget.
- **Beam over the name:** in mockup B the beam is blended *over* a baked chord name because the base is a JPEG. In the build it sits *under* the label mesh. The mockup overstates its effect on the glyphs.
- **Illustrative content:** the haul-card numbers in mockup D are invented and marked `mockup · illustrative numbers` on the card itself. The tier shown in mockup A (EPIC) is illustrative; under DROP_TABLE v1 the voicing in that frame is LEGENDARY (5.3).

**Method note:** the mockups are static HTML over the receipt JPEGs, rendered one by one with `chrome.exe --headless=new` plus the three anti-throttling flags, a temporary `--user-data-dir`, `--mute-audio`, `--virtual-time-budget=6000` and `--window-size=1080,1920`. The server on 8793 was not touched. After the scratch HTML was written, a harness hook auto-displayed it in the app's browser pane. That pane was not driven or used for any render.

---

## Appendix A: species words and lore lines (flavour text, for Daniel to ratify)

Only well-established names and nicknames. Nothing invented is presented as fact.

| Suffix | Words | Lore line |
|---|---|---|
| `""` | major | "Home." |
| `m` | minor | |
| `5` | power chord | "No third, all attitude." |
| `sus2` / `sus4` | suspended 2nd / 4th | "Unresolved on purpose." |
| `6` / `m6` | sixth / minor sixth | |
| `add9` / `m(add9)` | add nine / minor add nine | |
| `7` | dominant seventh | "Wants to go somewhere." |
| `maj7` | major seventh | |
| `m7` | minor seventh | |
| `m7b5` | half-diminished | |
| `dim7` | diminished seventh | "Symmetrical: every note is a minor third apart." |
| `m(maj7)` | minor-major seventh | "Cousin of the James Bond chord" (the Bond theme's final chord is a minor with major 7th and 9th). |
| `6/9` | six-nine | "A classic jazz ending." |
| `9` / `maj9` / `m9` | ninths | |
| `7sus4` / `9sus4` | suspended dominants | |
| `11` / `m11` | eleventh / minor eleventh | |
| `13` / `maj13` / `m13` | thirteenths | "All seven notes of the scale, stacked." (a full 13th chord) |
| `maj7#11` | major seventh sharp eleven | "The Lydian chord." |
| `7#11` | dominant sharp eleven | "Lydian dominant." |
| `7#9` | dominant sharp nine | "The Hendrix chord." |
| `7b9` | dominant flat nine | |
| `aug`, `7#5`, `maj7#5` | augmented family | |
| `7b5`, `dim` | flattened-fifth family | |
| `add11` | add eleven | |

---

## Sources

- TikTok safe zones for 1080x1920:
  - [Zeely: TikTok safe zones 2026](https://zeely.ai/blog/tiktok-safe-zones/)
  - [House of Marketers: safe zones guide](https://houseofmarketers.com/guide-to-safe-zones-tiktok-facebook-instagram-stories-reels/)
  - [Quso: TikTok dimensions and safe zones](https://quso.ai/blog/tiktok-dimensions)
  - [Creamate: TikTok safe zone guide](https://creamate.ai/en/blog/tiktok-safe-zone-guide)
- Loot reveal feel:
  - [PC Gamer: the psychology and art of loot boxes](https://www.pcgamer.com/behind-the-addictive-psychology-and-seductive-art-of-loot-boxes/)
  - [Game Developer: five tips for better loot experiences](https://www.gamedeveloper.com/design/five-tips-for-making-better-loot-experiences-in-games)
  - [TV Tropes: Color-Coded Item Tiers](https://tvtropes.org/pmwiki/pmwiki.php/Main/ColorCodedItemTiers)
  - [Tales of the Aggronaut: origins of colour-coded loot](https://aggronaut.com/2020/09/03/origins-of-color-coded-loot/)
- Code read at HEAD: `arsenal/web/piano.js` (THEORY templates, LIGHT and `LIGHT_BUDGET`, `LAYOUT`, `drawLabel`, `drawStaff`, overlay settle logic, `renderFrame`), `arsenal/web/piano.html` (font loading).
- Read-only, in flight: `arsenal/web/piano-next.js` (`pedalMarkSpec`, LAYOUT), `arsenal/web/piano/nashville.js` (the `diatonic` flag, key-tracker confidence), `arsenal/web/piano/log.js`, `arsenal/performance.py` (`summarize` fields), `arsenal/PIANO-V2-SPEC.md`, `research/in-flight/piano-ideas-2026-09-13/panel-synthesis.md`.
