# The Rarity Scale, musically honest

Designer lens: theory and rarity. One of three independent designs for the piano spectacle round, 2026-09-13.
Status: design only. Nothing in `arsenal/web/` was edited. A calibration lab (pure node scripts, no page) was run to
set the thresholds; its files and raw outputs are kept beside this document in `design-theory-rarity-lab/`.

Daniel, verbatim (tonight): "Can you reload the piano page and make it be perfectly un-aliased, can we make it even
more a visual spectacle? Perhaps even having a rarity and fanciness scale xD"

Standing rules this design keeps: pedalled notes stay lit and velocity counts (PIANO-V2-SPEC section 2); no wash-out,
the light budget holds (section 2, 6.2); the chord name and staff stay readable; 60 fps at 1080x1920; everything that
matters is inside the recorded canvas.

What I read, at HEAD (a886a0af) unless noted:
- `arsenal/web/piano.js`: `Theory.detect`, `TEMPLATES` (lines 74-112), `matchSet` slash logic, `estimateKey`, the overlay commit logic (`overlay.update`, lines 1164-1211: 120 ms settle after a note-on, 300 ms after a release), `noteOn/noteOff/setSustain`, `renderFrame`, `LAYOUT`.
- `arsenal/PIANO-V2-SPEC.md` sections 2, 4, 6.1 (harmonySet), 6.2, 6.5.
- Working tree, read only (the other build owns them): `arsenal/web/piano/nashville.js` (Nashville numbers and `createKeyTracker`), `arsenal/web/piano/log.js`, `arsenal/performance.py` (`summarize`, `chord_number`, `KINDS`, `validate_event`).

---

## 1. The idea in one paragraph

Every chord the overlay commits gets two measurements. **Fanciness** is what the chord is, as music: how much colour
it carries beyond a plain triad, what is in the bass, how the hands spread it, and how far it reaches outside the key.
**Rarity** is about Daniel: how often *he* plays it, tonight and across his practice log. The tier comes from both:
`Φ = fanciness × familiarity + novelty`. A chord he plays all the time fades toward Common however fancy it is. A new
chord gets a lift, but only as big as the claim the data can back ("first this session" is cheap to prove; "first
time ever" needs a real history). Every banner says **why** in plain words ("outside the key · first this session"),
so the scale teaches while it shows off. Rarity is judged once per committed harmonic event, the chord name the
overlay actually shows, with a pedalled arpeggio's note-by-note bloom counted as one event. Cooldowns keep Legendary
legendary.

Honesty rules, which override spectacle:
1. Never claim what the data cannot back. "Outside the key" needs a key the tracker is at least fairly sure of. "First time ever" needs at least 2,000 logged chords. Before the log vocabulary exists, Mythic is off.
2. The detector's confidence caps the claim. A strained reading (template cost ≥ 4.2) cannot score above Rare.
3. A smear the pedal made is not a voicing he chose. If more than 40% of the pitch classes come only from old pedal-held notes, fanciness is capped at Common or Uncommon.
4. The thresholds are absolute floors on fanciness. No percentile auto-calibration makes a triad session "Legendary". The only moving part is the inflation guard (section 6), which can only make tiers *stricter*.
5. The banner shows the name the overlay shows. Section 8.3 has the one known naming gap.

---

## 2. Music words, in plain language

Examples are in F major (F G A Bb C D E), Daniel's home key in the test scores.

| Word | Plain meaning | F major example |
|---|---|---|
| Triad | Three notes stacked in thirds: root, 3rd, 5th. The plainest chord. | F = F A C; Dm = D F A |
| Root | The note the chord is named after. | F in Fmaj7 |
| Seventh chord | A triad plus the 7th above the root. Adds warmth or pull. | Bbmaj7 = Bb D F A |
| maj7 vs 7 | "maj7" adds the note a half step below the root's octave (dreamy). A plain "7" (dominant seventh) adds the note a whole step below (bluesy, wants to move). | Fmaj7 has E; F7 has Eb |
| m7b5 (half-diminished, ø) | A minor seventh chord with a lowered 5th. Tense, sad-questioning. | Em7b5 = E G Bb D |
| dim7 (°7) | Stacked minor thirds all the way round. Very tense, symmetric. | C#dim7 = C# E G Bb |
| Extension (9, 11, 13) | Notes past the 7th: the 9th is the 2nd an octave up, the 11th the 4th, the 13th the 6th. Lush colour. | Dm9 adds E to Dm7 |
| add9, 6, 6/9 | Colour notes added without the 7th. Softer than a 9 chord. | Fadd9 = F A C G |
| sus2 / sus4 | The 3rd replaced by the 2nd or 4th. Open, unresolved. | Csus4 = C F G |
| Altered | A dominant chord whose 5th or 9th is bent a half step: b9, #9, #11 (= b5), #5. Maximum tension, jazz and film-score sound. | A7b9 = A C# E G Bb |
| Inversion | Same chord, a different chord note in the bass. | F/A: F major with A lowest |
| Slash chord | Written "chord/bass". Either an inversion (bass is a chord note) or a **foreign bass** (bass is not in the chord), which stacks two harmonies. | C/G is an inversion; Bb/C is a foreign bass |
| Voicing | How the notes are spread on the keyboard: close (bunched), open (spread wide), dense (many notes). | Fmaj9 over two octaves is an open voicing |
| Diatonic | Made only of notes from the key's scale. | Gm7, Am7, Bbmaj7 in F |
| Borrowed chord | A chord taken from the parallel minor key. Common in pop, sounds bittersweet. | Bbm (the "sad four", iv), Db, Eb, Ab |
| Secondary dominant | The "five chord" of some other chord in the key, used to lead into it. It brings one outside note. | A7 leads to Dm (A7 is V of vi); C# is the outside note |
| Chromatic mediant | A major chord whose root is a 3rd away and that shares few notes with the key. A sudden-light-change sound. | A major or Ab major against F |
| Neapolitan (bII) | The major chord a half step above the tonic. Dark, dramatic. | Gb major in F |
| Tritone away | The key a half octave off. The farthest you can get. | B major in F |
| Pedal point | A bass note held (often by the sustain pedal) while chords change above it. | Low C held under F/C, Gm/C, C7 |
| Nashville number | A chord named by its scale step in the key, so a habit reads the same in every key. The parallel build shows these live. | In F: Bbmaj7 = 4maj7, Dm = 6m, F/A = 1/3 |
| Committed chord | The chord name the overlay actually settles on and shows (after its 120 ms / 300 ms settle). | Not the flickers while a chord is rolled |

---

## 3. What the scorer can read (no new detection needed)

- `Theory.detect(notes, keyBias)` gives `kind` ("chord" / "note" / "interval" / "cluster"), `root` and `bass` spellings, `suffix` (a `TEMPLATES` suffix, or "5" for a power chord), `notes` (spelled MIDI notes from the bass up), and `cost` (the reading's strain; see `matchSet`).
- `Theory.TEMPLATES`: the chord vocabulary and each tone's letter step. This is how "3rd in the bass" is told from "foreign bass".
- `Theory.harmonySet(sounding, t)` (spec 6.1, being built): the notes that name the harmony, so the pedal's tail does not muddy the reading.
- `createKeyTracker().update(pcHistory, t)` (nashville.js): `{ key, confidence: "sure" | "fair" | "unsure", candidate }`, a steady key held against flicker, with the challenger it is considering.
- `nashville(info, key)`: `{ text: "4maj7", diatonic: bool, ... }`. `diatonic` is false for borrowed and chromatic chords.
- The notes engine's `sounding` map (`held`, `vel`, `t0`) and `sustain`: strike velocities, and finger-held versus pedal-held.
- The practice log (log.js, performance.py): per-session chord events with `chord`, `notes` and `key`, plus, from 6.5, `bass`, `harmony_notes` and `pedal_across`.

---

## 4. The scoring function

The runnable version is `design-theory-rarity-lab/rarity.mjs`; the pseudo-code below mirrors it exactly.

### 4.1 Intrinsic fanciness F

```js
// F = C + B + V + K + P, then honesty caps. Scale: plain triad 0, a lush 9th ~3, altered-and-outside 6-7.
function intrinsic(ev) {  // ev = { info, key, keyConfidence, candidateKey, peakVel, medianVel, pedalBlendShare, pedalPoint }
  const info = ev.info;
  if (!info || info.kind !== "chord" || info.suffix === "5") return NOT_SCORABLE;  // notes, intervals, clusters, power chords: Common
  const pcs = distinctPitchClasses(info.notes);

  const C = COLOUR[info.suffix];                 // 4.1.1
  const B = bassScore(info);                     // 4.1.2
  const V = voicingScore(info.notes);            // 4.1.3
  let K = 0;                                     // 4.1.4
  if (ev.key && ev.keyConfidence !== "unsure") {
    K = keyScore(info, pcs, ev.key);
    if (ev.candidateKey) K = Math.min(K, keyScore(info, pcs, ev.candidateKey));  // mid-modulation: judge against the kinder key
    if (ev.keyConfidence === "fair") K *= 0.6;
  }
  let P = 0;                                     // 4.1.5
  if (ev.peakVel - ev.medianVel >= 25) P += 0.3; // struck clearly harder than his running median
  if (ev.pedalPoint) P += 0.2;                   // a pedal-held bass under finger-held chords
  P = Math.min(P, 0.5);

  let F = C + B + V + K + P;
  if (ev.pedalBlendShare > 0.4) F = Math.min(F, 2.0);   // rule 3: a pedal smear, not a chosen voicing
  if (info.cost >= 4.2)         F = Math.min(F, 3.0);   // rule 2: a strained reading claims at most Rare
  return { F, core: C + B + K, parts: { C, B, V, K, P }, reasons: plainReasons(...) };
}
```

#### 4.1.1 C, chord colour (by TEMPLATES suffix)

| C | Suffixes | Why |
|---|---|---|
| 0 | `""` (major), `m` | The plain triads |
| 0.75 | `sus2`, `sus4` | One note moved; open but simple |
| 1.25 | `6`, `add9`, `7`, `m7`, `dim` | One added colour, or the everyday seventh |
| 1.5 | `m6`, `m(add9)` | Minor with a colour note |
| 1.75 | `7sus4`, `add11` | |
| 2.0 | `maj7`, `aug` | The dreamy maj7; the augmented triad is rare in pop |
| 2.25 | `m7b5`, `6/9` | |
| 2.5 | `dim7`, `m6/9` | |
| 2.75 | `9`, `m9` | Extensions: the lush range |
| 3.0 | `maj9`, `9sus4` | |
| 3.25 | `m(maj7)`, `11`, `m11` | The "James Bond" minor-major 7th; 11ths |
| 3.5 | `13`, `m13` | |
| 3.75 | `maj13` | |
| 4.0 | `maj7#11`, `7#11`, `7b5`, `7#5` | One altered tone (the Lydian #11, or a bent 5th) |
| 4.25 | `maj7#5` | |
| 4.5 | `7b9`, `7#9` | Altered dominants: the most tension the vocabulary holds |

A node test must check that every `TEMPLATES` suffix has a `COLOUR` entry, so a template added later cannot score
by default without a decision.

#### 4.1.2 B, the bass

```js
function bassScore(info) {
  if (!info.bass) return 0;                                    // root position
  const rel = (pc(info.bass) - pc(info.root)) mod 12;
  const tone = TEMPLATES.filter(t => t.suffix === info.suffix).flatMap(t => t.tones).find(([semis]) => semis === rel);
  if (!tone) return 1.75;                                      // foreign bass: two harmonies stacked (Bb/C)
  switch (tone.steps) {                                        // letter steps above the root
    case 2: return 0.75;                                       // 3rd in the bass (F/A): the sweet inversion
    case 4: return 0.5;                                        // 5th in the bass (C/G): common, cadential
    case 6: return 1.25;                                       // 7th in the bass (Fmaj7/E): a falling-bass colour
    default: return 1.5;                                       // a 9th, 11th or 13th in the bass
  }
}
```

The detector already makes this split. A foreign bass only appears through the slash path in `detect`, where the
upper chord's template does not contain the bass note.

#### 4.1.3 V, voicing (capped at 1.0)

```js
function voicingScore(notes) {                 // notes: distinct MIDI, bass first
  const span = top - bass, count = notes.length;
  let V = 0;
  if (span >= 24) V += 0.25;                   // two octaves
  if (span >= 36) V += 0.25;                   // three octaves
  if (count >= 6) V += 0.25;                   // dense
  if (count >= 8) V += 0.25;                   // very dense
  if (notes[1] - notes[0] >= 7) V += 0.15;     // an open bass (a 5th or more below the next voice)
  return Math.min(V, 1.0);
}
```

Voicing is deliberately small. Daniel plays lush and wide almost all the time, so a big V would inflate every chord.
Voicing never enters his history identity (4.2), so a wide voicing of a home chord is not "new".

#### 4.1.4 K, relation to the steady key (capped at 3.0)

```js
function keyScore(info, pcs, key) {
  const scale = key.mode === "major" ? MAJOR_SCALE : NATURAL_MINOR_PLUS_LEADING_TONE;  // as nashville.js FITS reads minor keys
  const outside = pcs.filter(pc => !scale.includes((pc - key.tonic) mod 12)).length;  // bass included
  const nv = nashville(info, key);
  return Math.min(3, 0.75 * outside + (nv && !nv.diatonic ? 0.75 : 0));
}
```

In words: count the notes that are not in the key (0.75 each), and add 0.75 more when the chord's root and type do
not belong to the key. One rule, no hand table, and it grades borrowed and chromatic chords by how far they reach:

| F major | Outside notes | Not diatonic | K |
|---|---|---|---|
| F7 (I7, leads to Bb) | Eb | no (the triad fits) | 0.75 |
| C7b9 | Db | no | 0.75 |
| Eb (bVII) | Eb | yes | 1.5 |
| Bbm (iv, the "sad four") | Db | yes | 1.5 |
| A7 (V of vi), D7 (V of ii), G7 (V of V) | C#, F#, B | yes | 1.5 |
| Dbmaj7 (bVI), Abmaj7 (bIII), Gbmaj7 (bII, Neapolitan) | 2 flats each | yes | 2.25 |
| E major, B7#11 (tritone away), Emaj7/G# | 3 or more | yes | 3.0 (cap) |

The tracker's confidence scales it: "unsure" gives 0 (and no "outside the key" reason is ever shown), "fair" gives
×0.6. While the tracker is weighing a new key (`candidate` set), K is the smaller of the two readings. A chord that
belongs to the key he is moving *into* is not scored as outside the key he is leaving. The tracker's own lag guards
(`holdSec` 3 s, `YOUNG_SEC` 12 s) would otherwise reward modulation lag.

#### 4.1.5 P, performance (capped at 0.5)

- Velocity: +0.3 when the event's peak strike velocity is at least 25 above his running median. "Played with intent."
- Pedal point: +0.2 when the bass is pedal-held (key up), older than 1.5 s, under finger-held upper notes. That is the pedal used on purpose.
- Velocity never decides a tier on its own. Its main job is the *size* of the effect inside the tier (section 7.3), the way loudness already scales light (spec section 2).

#### 4.1.6 Plain reasons (at most two on the banner)

In priority order: "first time ever" / "rare for you" / "first time tonight" / "first this session" / "back again"
(from 4.2), then "far outside the key" (K ≥ 2.25), "outside the key" (K ≥ 1.5), "borrowed note" (K > 0), "altered
dominant" (C ≥ 4.5), "sharp or flat colour" (C ≥ 4), "rich extension" (C ≥ 2.75), "seventh colour" (C ≥ 2), "foreign
bass" / "7th in the bass" / "colour note in the bass" (B ≥ 1.25), "wide voicing" (V ≥ 0.75), "accented", "pedal
point".

### 4.2 Personal rarity: familiarity h and novelty bonus

**Identity.** A chord's identity is its key-relative Nashville number, so a habit counts the same in every key:
- `id1` includes the bass ("4maj7/3");
- `id2` omits it ("4maj7").

Without a usable key the chord name is used, and those counts are kept separately and never mixed with numbers.
Novelty looks at `id2`, so a new inversion of an old friend is not "new". Familiarity blends both.

```js
// c = { Ns, ns1, ns2, lastSeenAgo, Nh, nh1, nh2, bandShare }
//   Ns: scored events so far this session; ns1/ns2: this identity's count this session
//   lastSeenAgo: scored events since id2 was last seen this session (Infinity if not yet)
//   Nh, nh1, nh2: the same counts over every earlier logged session (the vocabulary, section 9)
//   bandShare: share of his events (tonight + weighted history) whose core fanciness is >= this chord's core - 0.25
function personal(c) {
  const w = Math.min(1, 600 / Math.max(c.Nh, 1));            // history counts as at most ~600 chords of evidence
  const N = c.Ns + w * c.Nh;
  const blended = N >= 20 ? (0.7 * (c.ns1 + w * c.nh1) + 0.3 * (c.ns2 + w * c.nh2)) / N : 0;
  const tonight = c.Ns >= 20 ? (0.7 * c.ns1 + 0.3 * c.ns2) / c.Ns : 0;
  const share = Math.max(blended, tonight);                  // looping it right now makes it home tonight
  const lifeShare = c.Nh > 0 ? c.nh2 / c.Nh : 0;
  const mature = c.Nh >= 2000;                               // about seven 10-minute sessions
  const firstSession = c.ns2 === 0;
  const oftenForYou = mature && lifeShare >= 0.01;

  let bonus = 0, novelty = null;                             // the novelty ladder: the first rule that holds wins
  if (mature && c.nh2 === 0 && firstSession)          { bonus = 2.0;  novelty = "first time ever"; }
  else if (mature && lifeShare < 1/500 && firstSession) { bonus = 1.25; novelty = "rare for you"; }
  else if (!mature && c.Ns >= 150 && firstSession)    { bonus = 1.25; novelty = "first time tonight"; }
  else if (c.Ns >= 40 && firstSession && !oftenForYou) { bonus = 0.75; novelty = "first this session"; }
  else if (!firstSession && c.lastSeenAgo >= 150 && !oftenForYou) { bonus = 0.4; novelty = "back again"; }

  const famId   = smoothstep(0.03, 0.12, share);             // 3% of his chords starts to feel like home; 12% is home
  const famBand = smoothstep(0.10, 0.30, c.bandShare);       // if 10-30% of his chords are this fancy, fancy is his normal
  const h = Math.max(0.5, 1 - 0.45 * famId - 0.25 * famBand);
  return { h, bonus, novelty, lifetimeFirst: novelty === "first time ever" };
}
```

Why this shape and not a probability. The first calibration pass used surprisal (`-log2 p` with smoothing). It failed
in an instructive way. Daniel's lush chords each make up about 1% of his playing, so every one of them looked "rare",
and a 10th session with history fired *more* banners (25) than the first (19). A long tail of individually rare chords
is, as a whole, common. Novelty claims he can check ("first this session"), plus familiarity that dims home chords and
a band term that dims a fancy baseline, measured calmer and read truer (section 7.2).

Warm-up: nothing is "first this session" until 40 events in (about 80 s of playing), so the opening minute does not
treat every chord as new. Before any history exists, a new chord in a long session (150+ events) earns "first time
tonight", the no-history stand-in for "rare for you".

### 4.3 The final score and the tiers

```js
function tierOf(F, pers, raise /* inflation guard, section 6 */) {
  const phi = F * pers.h + pers.bonus;
  // walk up: a tier needs its phi floor (+raise for Rare and up), its F floor, and any special gate
}
```

| Tier | Φ at least | F at least | Extra gate | In words |
|---|---|---|---|---|
| Common | | | | Everyday harmony, or a home chord |
| Uncommon | 2.0 | | | A seventh-or-richer colour, a foreign bass, a touch outside the key |
| Rare | 4.0 (+raise) | 2.0 | | Lush and unusual: a #11, a 13th, a far borrowed maj7, a lush chord new tonight |
| Epic | 5.25 (+raise) | 3.0 | | Real tension or distance: altered dominants, a far chord with colour |
| Legendary | 6.75 (+raise) | 5.0 | novelty bonus ≥ 1.25, or F ≥ 7 | Fancy **and** rare for him: needs both, unless the chord alone is extreme |
| Mythic | 8.0 (+raise) | 5.5 | "first time ever" (≥ 2,000 logged chords, never seen) | A genuinely new fancy sound in his whole history. At most one per session. |

---

## 5. What counts as one event

### 5.1 Committed chords only

Rarity hooks the overlay's commit, the moment `overlay.shown` takes a new name (lines 1182-1192 at HEAD). It does
not hook every `detect`. Only what the viewer actually sees can be rare.

Eligible events:
- `kind === "chord"`, not a power chord ("5"), with at least 3 pitch classes;
- detected over `harmonySet` (spec 6.1), not raw `sounding`, once that lands;
- from MIDI input. The Demo never scores and never writes history. Computer keys score on screen but do not write history.

### 5.2 The bloom merge (pedalled arpeggios)

A pedalled arpeggio builds its chord one note at a time: F5 → F → Fmaj7 → Fmaj9, then D5 → Dm → Dm7 → Dm9. The
settle windows cannot stop this, because each new note really does change the name. So:

```js
// Called on each overlay commit, and every frame via tick().
// A bloom grows while each new committed set contains the previous one, over the same bass, pedal not lifted.
function createBloomTracker({ settle = 0.4, window = 1.6, maxLen = 2.5 } = {}) {
  let bloom = null;  // { t0, lastChange, info, pcs, bassPc, scored: null | { tierRank, id1, id2 } }
  return {
    commit(info, t, pedalLiftedSinceLast) {
      const pcs = pitchClassSet(info), bassPc = mod(info.notes[0].midi, 12);
      const grows = bloom && !pedalLiftedSinceLast && t - bloom.t0 <= window
                    && bassPc === bloom.bassPc && isSuperset(pcs, bloom.pcs);
      if (grows) { Object.assign(bloom, { info, pcs, lastChange: t }); return; }
      bloom = { t0: t, lastChange: t, info, pcs, bassPc, scored: null };
    },
    tick(t, shownName) {  // returns an event to score, at most once per settle
      if (!bloom || bloom.info.name !== shownName) return null;
      const settled = t - bloom.lastChange >= settle || t - bloom.t0 >= maxLen;
      if (!settled || (bloom.scored && bloom.scored.at === bloom.lastChange)) return null;
      const upgrade = bloom.scored;  // the bloom grew after it was scored
      bloom.scored = { at: bloom.lastChange };
      return { info: bloom.info, upgradeOf: upgrade };
    },
  };
}
```

Rules around it:
- **Scoring happens at settle.** The event is scored 400 ms after the bloom stops growing, on the name then shown. The banner arrives while the chord rings.
- **Upgrades replace, they do not add.** If a scored bloom grows again (a slow arpeggio), its session counts move from the old identity to the new one. The gate only lets it show a banner if its tier is strictly higher than the tier the bloom already showed.
- **A pedal lift ends the bloom.** That is the "one visible clearing" of spec 6.2.

Measured on 10 minutes of looping pedalled arpeggio blooms (sim F):
- Without the merge: 1,112 scored events, 117 Uncommon glints, 2 Rare.
- With it: 278 scored events, 78 glints, and 1 Rare banner in the whole 10 minutes.

The loop quickly becomes "home tonight" (h falls), which is the honest reading.

### 5.3 The pedal-blend cap

`pedalBlendShare` is the share of the event's pitch classes that come only from pedal-held notes older than 0.8 s.
Above 0.4, F is capped at 2.0 and the reason "pedal blend" goes to the HUD, not the banner. With `harmonySet` this
should rarely trigger. It stays as a guard for dense pedalled passages before that lands.

---

## 6. Anti-spam: the banner gate

A scored tier is always recorded: in the session counts, the HUD, and the practice log once section 9 lands. Whether
it gets a **banner** is the gate's decision.

```js
function createRarityGate() {
  // COOL: seconds since the last banner of THIS tier OR HIGHER (a higher tier ignores lower tiers' cooldowns)
  const COOL = { Rare: 12, Epic: 30, Legendary: 120 };
  // - any banner: at least 6 s after the previous banner (readability: one banner at a time, never stacked)
  // - Mythic: once per session
  // - per identity (id2): at least 90 s between banners, and at most 3 banners per session
  // - blocked Rare+ events fall back to the Uncommon "glint", never to nothing
  // - inflation guard: count Rare+ *scored* events in the last 300 s; above 15, Rare and higher floors
  //   rise by 0.25 per 5 extra, capped at +0.75; shown in the HUD as "rarity strict +0.5"
}
```

This is the order of defence against an arpeggiated pedalled passage firing Legendary every bar:
1. `harmonySet` stops the pedal tail from inventing fancy chords.
2. The bloom merge makes one bar one event.
3. Familiarity: a loop is home tonight after a few repeats (h falls to 0.55-0.6).
4. The per-identity limit: 90 s apart, 3 per session.
5. Tier cooldowns: Legendary 120 s.
6. The inflation guard.

Each layer works alone. Sims F2 and C show the first three are usually enough.

Not included, on purpose: a "showcase" or "recording" multiplier. What is recorded is what he played.

---

## 7. The tiers, with examples, frequencies and presentation

### 7.1 Examples in F major (real `Theory.detect` names, real Nashville numbers)

Every row below comes from running HEAD's THEORY block and nashville.js on the voicing in
`design-theory-rarity-lab/voicings.mjs` (full table in section 11). Columns are the tier in five personal contexts:
- **start**: the first chords of a session, no log;
- **home**: 15% of everything he plays;
- **occ.**: 0.5% of his history, first time this session;
- **rare**: 0.1% of his history, first this session;
- **first**: never in 5,000 logged chords.

| Detect name | Number | F | start | home | occ. | rare | first |
|---|---|---|---|---|---|---|---|
| F/A | 1/3 | 1.15 | Common | Common | Common | Uncommon | Uncommon |
| C/G | 5/2 | 0.90 | Common | Common | Common | Uncommon | Uncommon |
| Dm | 6m | 0.15 | Common | Common | Common | Common | Uncommon |
| Gm7 / C7 / Am7 | 2m7 / 5^7 / 3m7 | 1.40 | Common | Common | Uncommon | Uncommon | Uncommon |
| Eb (borrowed bVII) | b7 | 1.50 | Common | Common | Uncommon | Uncommon | Uncommon |
| Bb/C (foreign bass) | 4/5 | 1.90 | Common | Common | Uncommon | Uncommon | Uncommon |
| Bbmaj7 / Fmaj7 | 4maj7 / 1maj7 | 2.15 | Uncommon | Common | Uncommon | Uncommon | Rare |
| Dm9 | 6m9 | 2.90 | Uncommon | Common | Uncommon | Rare | Rare |
| A7 (secondary dominant) | 3^7 | 2.90 | Uncommon | Common | Uncommon | Rare | Rare |
| Fmaj7/E (7th in bass) | 1maj7/7 | 3.40 | Uncommon | Common | Rare | Rare | Epic |
| C13 | 5^13 | 3.65 | Uncommon | Uncommon | Rare | Rare | Epic |
| Gm11 (wide) | 2m11 | 3.90 | Uncommon | Uncommon | Rare | Rare | Epic |
| Fmaj9, spread over 3+ octaves | 1maj9 | 4.00 | Rare | Uncommon | Rare | Epic | Epic |
| Bbmaj7#11 | 4maj7#11 | 4.15 | Rare | Uncommon | Rare | Epic | Epic |
| Dbmaj7 / Abmaj7 / Gbmaj7 | b6maj7 / b3maj7 / b2maj7 | 4.40 | Rare | Uncommon | Rare | Epic | Epic |
| Dm9/Bb (his Bb F A C D E voicing) | 6m9/4 | 4.90 | Rare | Uncommon | Epic | Epic | Epic |
| C7b9 | 5^7b9 | 5.40 | Epic | Uncommon | Epic | Epic | Legendary |
| C7#5 | 5^7#5 | 5.50 | Epic | Uncommon | Epic | Legendary | Legendary |
| Emaj7/G# (chromatic mediant) | 7maj7/#2 | 6.15 | Epic | Uncommon | Epic | Legendary | Mythic |
| A7b9 / E7#9 | 3^7b9 / 7^7#9 | 6.40 | Epic | Uncommon | Epic | Legendary | Mythic |
| B7#11 (tritone away) | #4^7#11 | 7.15 | Legendary | Uncommon | Legendary | Legendary | Mythic |

The same examples, by tier, as they would usually land for Daniel:
- **Common**: F, F/A, C/G, Dm, C/E, Gm7, C7, Am7, Eb, Bbm. His loop, and anything he plays constantly.
- **Uncommon**: Bbmaj7, Fmaj7, Dm9, Bbmaj9, A7 / D7 / G7, Bbm6, Bb/C, C6/9.
- **Rare**: Bbmaj7#11, Fmaj13, Fmaj9 spread wide, Dm9/Bb, Dbmaj7, Abmaj7, Gbmaj7, C#dim7, Dm(maj7), and a Dm9 or Gm11 that is new tonight.
- **Epic**: A7b9, E7#9, C7b9, C7#5, Emaj7/G#, and a Bbmaj7#11 or Dbmaj7 that is rare for him.
- **Legendary**: B7#11 at any time, and A7b9 / E7#9 / C7#5 / Emaj7/G# when they are under 0.2% of his history.
- **Mythic**: one of those, or anything with F ≥ 5.5, played for the first time in 2,000+ logged chords.

### 7.2 How often (measured on synthetic sessions; recalibrate on his real logs)

`design-theory-rarity-lab/sim.mjs`, one committed event every ~2 s (about 300 per 10 minutes, after the bloom merge).
Style mixes are my guesses at his playing:
- **Daniel**: 58% the F/A C/G Dm Bbmaj7 loop, 22% everyday colour, 12% lush, 6% borrowed or secondary, 2% altered or far.

| Scenario (10 min) | Common | Uncommon | Rare | Epic | Legendary | Mythic | Banners R / E / L / M |
|---|---|---|---|---|---|---|---|
| A. Daniel style, first session, no log | 84.2% | 7.1% | 7.7% | 1.0% | 0% | 0% | 14 / 2 / 0 / 0 |
| B. Daniel style, 10th session (2,727 chords of history) | 81.0% | 9.8% | 6.9% | 2.0% | 0.3% | 0% | 10 / 4 / 1 / 0 |
| G. B over 20 seeds, banners per 10 min | | | | | | | 10.8 (7-15) / 2.9 (1-4) / 1.6 (0-3) / 0 |
| C. Plain triad loop F C Dm Bb, with history | 100% | 0% | 0% | 0% | 0% | 0% | 0 / 0 / 0 / 0 |
| D. Explorer mix, with Daniel's history | 48.5% | 34.6% | 11.3% | 4.3% | 1.3% | 0% | 17 / 4 / 1 / 0 |
| E. Explorer mix, no history | 47.0% | 40.7% | 7.0% | 5.0% | 0.3% | 0% | 10 / 9 / 1 / 0 |
| F2. Pedalled arpeggio loop, bloom merge | 69.8% | 28.1% | 2.2% | 0% | 0% | 0% | 1 / 0 / 0 / 0 |

Mythic never fires in the sim because its vocabulary is closed: every voicing is in the history after nine sessions.
That is correct behaviour. Mythic belongs to real new vocabulary.

**Targets for a typical 10-minute session of his playing:**

| Tier | Share of committed chords | Banners per 10 min | On a 60 s TikTok |
|---|---|---|---|
| Common | ~80% | none | |
| Uncommon | ~10% | none (glint only) | several glints |
| Rare | ~7% | ~10 (about one a minute) | usually one |
| Epic | ~2% | ~3 | sometimes one |
| Legendary | ~0.5% | 1-2 (0 when he loops) | a lucky clip |
| Mythic | new vocabulary only | ≤ 1 per session, expected a few per month of logging | the clip he posts |

### 7.3 How a tier is shown

**The banner is text, drawn in the overlay pass.** The overlay scene renders after the composer (HEAD
`renderFrame`: composer, then `renderer.render(overlayScene)`), so the banner is never bloomed. It adds nothing to
the light budget, cannot wash out, and is in the recording.

Format, two lines:

```
EPIC · A7b9 · 3⁷ᵇ⁹
outside the key · first this session
```

- Line 1: the tier word in caps, in the tier colour, weight 800, letter-spacing 0.12em; then the chord name and the Nashville number in ink, drawn with the same run renderer as the label (`nameRuns`/`suffixRuns`, raised suffix), not the caret text form. With no usable key (tracker unsure) the number is omitted: `RARE · Bbmaj7#11`.
- Line 2: at most two reasons (4.1.6), 60% ink, small caps.
- A soft dark plate behind both lines (rgba 0,0,0,0.5, radius 18 px), matching the readability plate of spec section 2.
- The tier word for Mythic is drawn letter by letter in the chord tones' own trail colours (`noteCss`), so the banner wears the chord.

Tier colours: chosen at similar luminance so none dominates, and clear of the pitch palette's job.

| Tier | Colour | Hex (approx.) |
|---|---|---|
| Uncommon | green | oklch(0.80 0.19 150), #4FD37F |
| Rare | blue | oklch(0.72 0.15 250), #5AA2FF |
| Epic | violet | oklch(0.66 0.20 305), #B071F5 |
| Legendary | amber gold | oklch(0.82 0.16 75), #FFB43A |
| Mythic | prismatic | the chord's own note colours |

Placement:
- **9:16** (1080x1920): the label occupies y 148-488 (LAYOUT cy 318, h 340) and its second line ends near y 440; the grand staff content starts near y 650. The banner is its own overlay layer centred at x 540, y ≈ 540, 980 x 110. It sits in the gap between chord name and staff, well clear of TikTok's top UI band (about y 0-160) and bottom caption band (about y 1440+). If the parallel build's live Nashville line takes that gap, the banner sits directly under it. The integrator resolves the exact y once both exist. The staff scrim must not be pushed down.
- **16:9**: left-aligned under the label, x 74, y ≈ 380.

Lifetimes: fade in 120 ms, hold, fade out 500 ms.

| Tier | Hold | Text treatment | Scene treatment |
|---|---|---|---|
| Uncommon | no banner | 350 ms sheen across the chord name (overlay canvas only) | none |
| Rare | 1.8 s | banner + sheen | the chord's keys get a 250 ms tier-colour rim (key emissive +0.15, not additive to trails) |
| Epic | 2.6 s | banner + sheen | one thin ring pulse along the rail from the chord's lowest to highest key: one instanced quad, normal blending, only its 120 ms leading edge may cross the bloom threshold; this event's spark *count* ×1.5 (brightness unchanged) |
| Legendary | 3.4 s | tier word revealed letter by letter (60 ms each) | ring pulse; camera push-in 2% over 1.2 s and back; bloom strength +0.1 for 0.6 s **paid for** by lowering the density target to 0.8 of the light budget for the same 0.6 s, so total light is flat |
| Mythic | 4.0 s | prismatic tier word + third line "FIRST TIME EVER" | all of Legendary + a slow, low-luma aurora veil behind the keyboard (never over the label or staff band), mean luma rise ≤ 0.03 in the staff box |

- **Velocity** scales every scene treatment from 0.6× (soft) to 1.0× (≥ his p90), never the tier. A whispered Epic is still Epic, just quieter.
- **Pedal**: if the pedal lifts during a treatment, the scene part ends with the clearing (spec 6.2: one visible clearing) while the banner text finishes.

Acceptance for the presentation, with the existing receipts:
- `wash_check.mjs` passes with a test hook forcing a Legendary every 3 s. Mean luma in the staff box stays under 0.6, and every note head stays visible.
- The chord-name band stays within 5% of silence (spec 6.6), measured with banners suppressed on the frame pairs.
- 60 fps holds at 1080x1920: a banner redraws its 2D layer at most once per reveal step, and the ring is one draw call.

---

## 8. Honesty notes and known gaps

### 8.1 Why this is "musically honest"

- The fanciness scale follows harmony, not a lookup of "cool names". Colour by extension depth, bass function from the template's own letter steps, distance from the key by counted outside notes.
- The tier is relative to Daniel. The same chord fades as it becomes his, and the banner says so ("first this session", "rare for you").
- Every claim is gated by evidence: key confidence, reading cost, history size.

### 8.2 The brief's example banner, corrected

The brief's sketch was "EPIC · Bbmaj9#11 · b7". Two corrections:
- In F major, a chord built on Bb is the **4** chord, not b7. b7 would be Eb.
- The overlay names Daniel's Bb F A C D E voicing **Dm9/Bb**. It is the same six notes as Bbmaj9#11. `TEMPLATES` has `maj7#11` but no `maj9#11`, so `detect` takes the slash path (Dm9 over a foreign Bb bass).

The banner shows what the overlay shows: `RARE · Dm9/Bb · 6m⁹/4` with "rich extension · foreign bass" at session
start, or EPIC with "first this session" when it is not a habit. The fanciness score lands in the same place under
either name (4.9 via m9 + foreign bass).

### 8.3 Gaps

- **The vocabulary caps the scale.** No `maj9#11`, `7b9#11`, `13#11`, `7#9b13`, `7alt`. Adding templates extends the scale automatically, once each gets a COLOUR entry (enforced by the test in 4.1.1).
- **Minor keys.** The scale set is natural minor plus the leading tone (as `nashville.js` FITS reads it). A melodic-minor raised 6th (F# in A minor) counts as outside. Consider adding the raised 6th when the leading tone is heard.
- **Tracker lag** right after a modulation is handled by the candidate-key minimum and the fair ×0.6, but a chord in the first seconds of a new key can still be over-scored as outside. The per-identity gate limits the damage.
- **Synthetic calibration.** The style mixes are guesses. The thresholds are one table, and should be re-read against his first three real logged sessions (the vocabulary endpoint, section 9, makes that a one-command check).
- **Chasing banners.** A game layer can pull attention from the music. Familiarity fading repeated tricks, and reasons written in music words, push the other way. Give him a toggle (key `R`, persisted like the other settings) and a HUD count.

---

## 9. Personal history plumbing (a proposal for the log's owner, after the current build lands)

- **The source of truth is the practice log.** Raw log `chord` events are label changes, not bloom-merged events, so history counted from them would disagree with the scorer's own events.
- **The client logs one `rarity` event per scored event:** `{ kind: "rarity", id1, id2, core, F, phi, tier, novelty, reasons, key, upgrade_of }`.
- **Order matters.** `performance.py` `validate_event` rejects unknown kinds with a 400, and the whole batch is dropped (`KINDS = ("on", "off", "pedal", "chord", "sound_end")` today). The server must add `rarity` to `KINDS` first. The client feature-detects the vocabulary route below and sends `rarity` events only when it exists.
- **Vocabulary route:** `GET /api/performance/vocabulary` returns:

  ```json
  { "api": "arsenal.performance.vocabulary/v0", "chords": 5123, "sessions": 17,
    "by_id2": { "4maj7": 812, "6m9": 51 }, "by_id1": { "4maj7/3": 40 },
    "by_name_nokey": { "Dm9/Bb": 3 }, "core_hist": { "bucket": 0.25, "counts": [ ... ] },
    "first_seen": { "4maj7#11": "20260914-201502-1a2b3c4d" }, "updated_at": "..." }
  ```

  It is recomputed on session close from the `rarity` events and cached at `state/arsenal/performance/vocabulary.json`. Demo and computer-key events never write `rarity` events.
- **Before the route exists,** the page keeps a per-browser fallback in localStorage (`arsenal.piano.rarity.v0`, same shape, try/catch). It feeds familiarity only. "First time ever", "rare for you" and Mythic stay off until the log's vocabulary is the source, because a browser's storage cannot prove "ever".
- **Privacy:** it all stays under `state/arsenal/` on this machine (spec section 1 rules).
- **Later,** the analyzer can add "your rarest moments" to `summary.md`: every Epic+ event with its time, so Daniel can replay it. That fits the 6.5 card format.

---

## 10. Integration sketch (for whoever builds it; nothing here was edited)

- A new pure module `arsenal/web/piano/rarity.js`, no DOM and no three.js, node-tested like THEORY. It exports `intrinsic`, `personal`, `tierOf`, `createBloomTracker`, `createRarityGate`, `COLOUR` and `TIERS`.
- **In the core,** after `overlay.update`:
  - call `bloom.commit(...)` when the shown name changes, and `bloom.tick(t, overlay.shown?.name)` every frame;
  - score what `tick` returns with the tracker key, the harmony set's velocities and pedal ages, and the vocabulary counts;
  - pass the result through the gate;
  - on a banner, draw the rarity layer and trigger the scheme's optional `rarity(tier, event, t)` hook. It is an optional addition to the scheme interface; schemes without it just get the overlay banner.
- **Test hooks:** `__piano.rarity.stats()` (per-tier scored and banner counts, strictness, source "log" or "local") and `__piano.rarity.force(tier)` (for the wash receipt).
- **HUD line:** `rarity 10R 3E 1L · strict +0 · log`.
- **Node tests,** with fixtures in the style of `tests/fixtures/nashville_cases.json`:
  1. every `TEMPLATES` suffix has a COLOUR entry;
  2. the section 7.1 table reproduces exactly (voicing, key, context → tier);
  3. 10 minutes of the F C Dm Bb triad loop gives zero Rare-or-higher;
  4. a pedalled bloom F → Fmaj7 → Fmaj9 gives one scored event, and a slow bloom upgrade replaces its counts;
  5. gate invariants: no two banners within 6 s, at most one Mythic per session, at most 3 banners per identity, Legendary spacing ≥ 120 s;
  6. "first time ever" never appears with fewer than 2,000 logged chords or with the local source;
  7. tracker "unsure" gives K = 0 and no key reason;
  8. a template cost of 4.2 or more caps the tier at Rare.

---

## 11. Calibration lab (receipts)

Folder: `research/in-flight/piano-spectacle-2026-09-13/design-theory-rarity-lab/`

| File | What |
|---|---|
| `theory.mjs` | HEAD's THEORY block (`git show HEAD:arsenal/web/piano.js`, lines between `THEORY BEGIN` and `THEORY END`) plus `export { Theory }` |
| `nashville.mjs` | A snapshot of the in-progress `arsenal/web/piano/nashville.js`, 2026-09-13 night |
| `rarity.mjs` | The scorer, exactly as in section 4 |
| `voicings.mjs` | The F major voicings and the style groups |
| `examples.mjs` → `examples-output.txt` | The full per-voicing table (section 7.1 is a subset) |
| `sim.mjs` → `sim-output.txt` | Scenarios A-G, with every banner that fired and why |

Run: `node examples.mjs` and `node sim.mjs` inside the folder (Node 24).

Calibration history, so the next tuner does not repeat it:
1. **Pass 1** (surprisal-based personal rarity, Rare at Φ 3.0, Legendary 5.75):
   - Legendary took 6-12% of Daniel-style chords, and a 10th session was spammier than a first.
   - A gate bug (Mythic's infinite cooldown checked for every tier) blocked all banners. It was fixed in the gate, not the scale.
2. **Pass 2** (novelty ladder, Rare 3.5):
   - Rare banners ran about 15-19 per 10 minutes, because every lush chord cleared Rare on colour alone.
   - "back again" fired for chords never seen this session.
3. **Pass 3** (this design):
   - Rare raised to 4.0.
   - "back again" limited to chords already seen this session.
   - Tonight's share can dim a looped chord (the history weight no longer swamps it).
   - The band term dims a fancy baseline.
   - Result: section 7.2.
