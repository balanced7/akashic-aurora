I have everything I need. I can see the full architecture: CC64 sustain is already wired (noteOff + setSustain), the trails are an instanced shader keyed off `aT0/aT1/aT2` timestamps, the chord name + grand staff is a Canvas2D overlay, and there's already a `pcHistory` + `estimateKey` (Krumhansl-Kessler) running. Now I'll write up my two schemes and the banter idea.

---

# Vandor — two schemes + one banter idea

## Scheme 1 — "Well Temperament": a circle-of-fifths constellation for the sky

**What's on screen (9:16).** The piano stays exactly as-is at the bottom — it's already gorgeous and he loves it. What I'd change is *everything above the keys*: instead of vertical bars rising straight up from each key, every sounding note becomes a point of light on a giant **circle-of-fifths wheel** drawn flat in the sky behind the keyboard. The 12 pitch classes sit on a ring (C at top, G at 1 o'clock, D at 2, and so on around — same mapping your `fifthsIndex` already computes for colour). Each held note lights its point on the ring and draws a **thin line from the key it came from, up to its point on the wheel** — so the eye traces the physical key to the tonal grammar it belongs to. Same-note octaves stack their brightness rather than making new points.

**What the events do.**

- **Note-on:** an arc of light runs *around the ring* from where the previous note sat to the new note's point — the shortest path, so a fifth is a short hop but a tritone tears across half the circle and visibly *spits*. The point itself blooms and a fine filament stretches down to the active key.
- **Note-off:** the point dims but lingers ~1.5s as a ghost, holding its place in the recent-harmony shape.
- **Sustain pedal (CC64):** the *wheel itself* brightens and thickens — the whole ring glows warmer, and the lines from still-sounding notes stay lit while their keys have physically risen. This is the sustain signal made legible as *the ring holding onto the chord* rather than as a wall of cyan.
- **Chord change:** the set of lit points forms a polygon inscribed in the ring — a triad is a triangle, a 7th is a quadrilateral. On a chord change you see the old triangle *morph* into the new one, and I'd drop a slow-rotating **key-centre ghost** (from your existing `estimateKey`) that breathes toward whichever tonic the Krumhansl-Kessler detector believes — so you can literally watch him modulate.

**What it reveals about the music.** This is the one scheme that makes *harmony and tonality* visible instead of just pitch height and loudness. It solves his exact complaint — the dense pedalled wall — by construction, because notes clump by *grammar* (a chord is a tidy triangle), not by physical key position. A pedal wash of ten notes becomes a compact, legible polygon. It also makes voice-leading visible as the arcs hopping around the ring, and modulation visible as the whole lit shape rotating along the wheel. Exactly the stuff he says he "doesn't fully understand" — it shows him the grammar he's already using.

**Build difficulty: medium.** The heavy lifting (pitch→fifths-index mapping, chord detection, key estimation) already exists in your `Theory` block and `estimateKey`. What's new: a ring of 12 point-sprites (trivial), a per-note line from `keyX(m)` to a ring point (a `Line` per active note, or one instanced line like your trails already are), an arc-tween on note-on (small), and a polygon overlay (a `LineLoop` rebuilt on chord change). Half a day to a day, mostly tuning. No new depth/raster machinery; it reuses your bloom and additive blending.

---

## Scheme 2 — "Velocity Rain": height is time, and the loud parts fall hard

**What's on screen (9:16).** This inverts your current trails' meaning. Right now a bar's *height* = how long it's lived, and everything rises at the same speed. In this scheme, **every note is a falling drop** and its fall speed, size and brightness are held by *velocity*. Soft notes are slow, small, dim teal motes drifting down; loud notes are heavy, fast, bright white-gold comets. The column of each key becomes a *lane*, and the note's colour still follows the fifths-index so pitch hue survives — but the *dynamic* of the note now controls its motion, not its height. The staff and chord label stay, and I'd move them to the *top* of the frame so the falling rain pours down *behind and past* them.

**What the events do.**

- **Note-on:** the drop spawns at its key with a burst scaled to velocity (your `burst()` already does `6 + 20·vel` — I'd make it louder, like 4 + 40·vel), then accelerates downward under a little gravity with its terminal velocity set by `vel/127`. A `fff` accent is a meteor; a ghost note drifts like paper.
- **Note-off:** the drop keeps falling (decoupled from the key, since it's already in motion).
- **Sustain pedal:** this is the payoff. When the pedal is down, *drops pool at the bottom* — instead of dying at the bottom edge, they collect into a luminous **liquid layer** at the floor of the frame that swells as he pedals and *drains away the moment he lifts CC64*. The pedal becomes a visible dam that catches and releases the sound. On his dense pedalled playing, a rising tide of pooled colour is the *intended* effect — a wall, yes, but a wall that meaningfully maps to "the pedal is holding everything."
- **Chord change:** the pooled liquid shimmers, and a brief ripple propagates across it; the chord label at the top does a small pop (your existing `pop`).

**What it reveals about the music.** This one makes *dynamics and pedal choreography* visible rather than harmony. It takes the thing he already loves — the glow — and gives it a physics that's honest about what his hands and feet are doing. Soft-and-hard passage contrast becomes immediately legible (the rain thins, the rain pours). And crucially it *doesn't* wash out the staff and chord name, because the bright activity pools at the bottom while the notation lives at the top — the separation that the current layout loses.

**Build difficulty: medium-easy, but with one real risk.** It's almost entirely a rewrite of your existing trail shader (`bot` becomes gravity-driven instead of constant `uSpeed`, and I'd add a bottom pool as a separate full-width `Plane` with a height uniform driven by pedal state). The real risk is *performance*: with dense pedalled input you can have hundreds of drops plus a bloomed pool, and your current design was deliberately GPU-cheap. At 60fps with 640 concurrent drops that's still fine (it's one instanced draw). The subtler risk is making small soft notes legible against the pool — needs a minimum fall brightness floor. A day-ish of iteration; the frame-perfect part is the pool drain, not the drops.

---

## The banter idea — "What were you *feeling*, not what did you play"

He said *"there is a lot of stuff I do that I don't fully understand."* The trap is to answer with a theory lecture he didn't ask for. So my pitch is to make the log feed **not a score, but a mirror with taste.**

**What I'd want in a session summary** (already mostly computable from your existing engine):

1. **The emotional lie of the pedal** — total sustain-seconds vs. played-seconds; how often he holds CC64 across a chord change (that's the tell of someone hearing a melody *over* a held harmony, whether they know it or not).
2. **Favourite notes.** A ranked list of his top 3–4 notes by dwell time and loudness. The notes he comes back to aren't random — they're his *home pitch*.
3. **The key he actually lives in.** `estimateKey` over a full session, and — the fun part — the *moment* it drifted. "You started in C minor and at 2:14 you slid somewhere darker. What happened there?"
4. **Chord vocabulary ranking** — his most-played chord shapes (from `detect`), laid out as "you play a lot of m7 and sus4, almost never a dim7."
5. **The loudest single note and the quietest passage** — bookends to anchor a memory.

**What I'd ask him** (short, concrete, one at a time — never a quiz):

- "That G you keep landing on and leaning into with the pedal — is that a note you *hear* before you play it, or a place your hand just knows?"
- "You pedal across the chord change here, which is why the whole thing blurs into one colour. Do you *want* it to blur there, or is that a habit you didn't notice?"
- "This run climbs to a B♭ and then you back off and go quiet. Were you building to something and changed your mind — or is B♭ as far as it goes in your head?"

The design point: I'd rather ask him *why the B♭ stops the climb* than tell him *that the B♭ is the minor 7th of C*. He knows the music by hand; the theory is the last thing to give him a name for what he already does. The log's whole job is to produce questions with his fingerprints on them.

---

That's my two schemes and the banter angle. My taste skews toward **Scheme 1** (Well Temperament) as the more genuinely *revelatory* one — it's the only look that converts the thing he says he doesn't understand (harmony) directly into something he can see. Scheme 2 is the more *satisfying* one for runtime feel and it respects what he already loves. Either lands faster/cleaner at 60fps than at monitor-native on a dense session; `renderer.setPixelRatio(1)` and the instanced draws are already tuned for it.