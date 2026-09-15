# half_navi.md — Information design & pedagogy (blind)

Navi's lane. Written blind; I have not read the other halves. Grounded in the brief,
the evidence frames, `arsenal/SPECTACLE-DESIGN.md`, and the jam design docs.

---

## The one sentence

Daniel already told us what this is for, twice: **"I get to actually see the
progressions I am making and can start putting theory and name to intuition,"** and
**"I also love how our system shows you the chord for notes arpeggiated with
sustain!"** The visualizer's whole worth to him is that it *names what his hands
already feel*. If we get the naming hierarchy right, the beauty is meaning; if we
get the spectacle right and the naming wrong, it reads as pretty machinery and
nothing more — which is *exactly* the complaint ("the presentation is lacking").

So my lane is not decoration. It is the answer to: **what does he need to see at
each moment, and what must hide so the rest can breathe.**

---

## The hierarchy (what to show, in what order, at the keys)

There are exactly five facts a player needs, and they are a strict ladder. Lower
rungs must never shout over higher ones.

1. **The chord name** (e.g. `Am9`). This is the headline. It is what Daniel quotes
   back to us. It gets the largest, most legible, most contrast-protected treatment
   on the frame. Vandor's first read of `01-moonwater` and `04-first-spectacle` —
   the headline says **"12 notes"** instead of the chord, and the glass labels are
   white-on-pastel — is the single most load-bearing critique of my lane, because
   it means the *top rung is currently missing or illegible*. The detector's own
   spelling must be **the** headline, always, per `SPECTACLE-DESIGN.md` ("The
   detector's own spelling appears on the glass"). "12 notes" is a count, not a
   chord; show the count only as a quiet sub-line, and only when there is no named
   chord to report (a true chromatic cluster).

2. **The Nashville number** (e.g. `6m9`), beside the chord, in Daniel's key. He
   loves this. It is the *whole point* of "numbers restart at 1 in the new key."
   It is second, smaller than the name but always present when the key is known,
   carrying its uncertainty honestly (the plaque already "uses the piano's existing
   reading, including uncertainty").

3. **The key** (e.g. `key: C`), quietest, smallest, bottom of the plaque. It must
   never compete with the chord; it is context, not content. When he transposes,
   the *letters* move and the *numbers* stay — that visual is itself a lesson
   (my format 1.4), and it only lands if key is visibly subordinate to number.

4. **The note that moved** — the voice-leading. This is the pedagogical gold and
   the thing the other seats will under-specify because it is *mine*. When a chord
   changes, one or two notes usually step a semitone or two (a 7th falling to the
   next chord's 3rd, etc.). Between the keys, on the glass, show **only the notes
   that moved** as a thin bright thread from the old position to the new, for the
   half-second of the change, then let it fade. This is "motion as suggestion":
   the moving note is *drawn as a suggestion of where the harmony is going*, not a
   full re-render. It teaches voice-leading without a word of theory, and it costs
   almost nothing (one drawn leader per moved pitch-class). See below for its
   TikTok form.

5. **Suggestions and the next chord** — the jam's jam. The chord reader
   (`chordread.js`, committed, not yet wired) already computes "anticipates" and
   "suspension resolved". These two flags are the heart of the teaching:
   - **Anticipating** (he arrives early on the next chord, the gospel push) →
     show the *next* chord's name + number ghosting in, one beat early, at 40%
     opacity, then solidifying on the downbeat. The future is a whisper, not a
     billboard. (design-music 9.4: `anticipates`.)
   - **Resolved** (a held note that steps down onto the new chord tone) → show the
     held note as a lit key that *stays lit while other keys change*, then a brief
     connector to the note it lands on. "Suspension, resolved" is one of the few
     theory sentences worth teaching *in the frame* (design-music T15), and here it
     is shown, not said. (design-music 9.4: `suspension resolved`; my `resolve`
     seed.)
   - Claude's **jam next chord** (the ghost rim "incoming, hold, found" states in
     design-ux 533–537) already teaches the next chord at the keys. My lane's job
     is to keep that teaching **in the same visual grammar** as the rest — rims,
     whispers, fades — never a new, louder widget.

### What hides when

The whole discipline of "teaches without clutter" is a *progressive reveal with a
verb attached to each state*:

- **While he plays** (pure performance): chord name + number + key only. No
  suggestions, no moved-note threads, no next-chord whisper. The music is the
  subject. (SPECTACLE-DESIGN: "pure performance hides text.")
- **At the moment of a change**: add the moved-note thread (rung 4) for half a
  second, then fade it. It is a *verb*, a one-beat event, not a persistent overlay.
- **When he holds/arpeggiates with sustain** (the thing he loves): keep the chord
  name and number *aggregated* — the whole arpeggio reads as one named chord, and
  the name is stable until the harmony genuinely changes. This is his quoted joy
  made literal: the sustain *is* the reason the chord is one thing, not four notes.
- **In the jam (`Try`, ghost mode)**: add the next-chord whisper and ghost rims.
  Teaching goes **on** only when he has asked for it (Try/Hover), **off** the
  instant he lets go. Esc/Backspace dismisses everything (design-ux 232).
- **Never at the same time**: name, number, key, moved-note, and suggestion all
  visible at once is clutter. The ladder is a *maximum of three visible at a time*
  — name + number + (key OR moved-note OR next-chord). Pick by state, not by
  accumulation.

---

## The 9:16 TikTok (sound-off) — what teaches when he isn't playing for you

A sound-off TikTok is the hard case: the viewer can't hear the harmony, so the
**view must carry the theory entirely by eye, in the first two seconds.** My
lane's specific answers:

- **The chord name must be readable in the safe caption zone, not the stage.**
  Daniel's brief already carries the 9:16 safe zones (top UI ~y 0–160, bottom
  caption ~y 1440+). The chord name and Nashville number go **top** (chromeless,
  high-contrast, largest), the moved-note story lives in the **played gesture
  itself** (middle third), and the bottom third — which Vandor flags as "black
  water" in `01-moonwater` — must **not** be dead. Rill owns the measured floor
  for that; my lane owns *what goes there*: a quiet, honest, one-line label is
  better than dead water, but better still is *nothing* and a properly-composed
  gesture filling the frame.
- **The moved-note thread is the TikTok's theory teacher.** Sound-off, a lit key
  is just a lit key; the *meaning* is the half-step that resolves. So in the
  recorded canvas, the one deliberate one-second moment to choreograph is the
  **resolve**: a held note, everything else changes, the held note *stays*, then
  steps down and *arrives*. That's a story anyone reads even with sound off —
  "something hung on, then it landed." My `resolve` idea is the single most
  portable theory-into-image we have; make it the default hero of a TikTok.
- **The headline never says a count.** In portrait, "12 notes" (frame 01) is
  noise; "Am9 · 6m9 · C" is the whole lesson. The count is for the chromatic-cluster
  edge case only.
- **Nashville is the TikTok's gift.** A viewer who knows nothing sees the *numbers
  not moving* across a transposition and learns something real in four seconds
  (my format 1.4). This is the one teaching that is *more* legible sound-off than
  sound-on.

---

## How we know it's right

By eye (the ones I can judge without instruments):
- At a chord change, can he say the name out loud without squinting? If the
  headline is white-on-pastel (frames 02, 03), no — fail.
- Does a 5-second sound-off clip communicate "something hung on, then landed" to
  someone who doesn't play? The resolve is legible or the clip has no story.
- Is any single frame showing more than three of the five rungs at once? If yes,
  we over-showed.

By measurement (what I'd hand Rill as the acceptance for *my* layer, so he can
instrument it): headline **contrast ratio** against its local background in the
worst-lit frame (not the best); **chord-name dwell** — how long the correct name
stays stable during a sustained arpeggio (should be the whole hold, not flickering
per-note); **moved-note thread lifetime** — present at change, gone by +0.5s, never
persistent; **ghost/whisper absence outside Try/Hover** — zero teaching pixels in a
pure-performance take.

---

## The one question for Daniel

**When you play, do you want the display to *name what you just played* (look back
and confirm), or *show where it's going* (lean forward and suggest) — or both, and
if both, which one gets the bigger, brighter treatment?** Everything above splits
on this: the chord name + number is the backward look, the moved-note thread and
next-chord whisper are the forward lean. I can build either as the hero, but I
can't make *both* the headline, and your answer says which one gets to be.
