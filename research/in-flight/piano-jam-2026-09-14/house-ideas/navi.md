# House ideas — the video arc, TikTok formats, and shader/scene ideas for the jam

Filed by: Navi (deepseek). For: Vandor + the whole house. Status: ideas only — nothing in
`arsenal/` was read-for-edit, nothing edited, no server or browser touched. This document is a
gift-basket for the two lanes already in flight (`piano-spectacle-2026-09-13` — rarity tiers;
`piano-jam-2026-09-14` — cards, loops, ghost keys, jam view) and nothing here blocks either of them.

The night's two governing briefs, in Daniel's own words:

> "feel free to open this up to the whole house, I would love to hear their ideas"
>
> "continue on the video arc, somehow between all of this there is content to be made xD"

So this is pitched at **content between the builds** — the arc that turns what already exists (the
visualizer, the rarity tiers, Claude's band, the practice log, the Nashville row) into *things
Daniel can post*, and the few scene ideas that would make those posts sing.

I write this from the photographer's seat, not the composer's. Every idea below already obeys the
rules the two lanes have hard-won, and I'll name the rule each time so the integrator can trust it:

- **Stage vs glass.** The stage is recorded; the glass is never recorded. `auto` moves Claude to
  the glass the instant REC starts, so a take stays 100% Daniel unless he chooses `stage`.
  (jam-spec C14, UX 7)
- **His palette vs her palette.** Pitch colours are Daniel's alone. Tier colours (green/blue/
  violet/gold/prismatic) appear only in chrome, always with a word + pips. **Gold means Legendary
  and nothing else.** Claude is moonlight `#C8DCFF`, no trails, capped at 0.75 of Daniel's lift.
- **Light is a budget, not a pile.** `LIGHT_BUDGET`, bloom threshold 0.9, house lights *dim* old
  columns so spectacle adds contrast, not luma. The frame may never wash out; chord name stays
  readable. (spectacle 0, vfx director)
- **Every claim is checkable.** A banner says *why* in music words, and a tier is relative to
  Daniel. Never fake a rarity. (theory-rarity 8.1)
- **TikTok is 9:16, 1080x1920, 60 fps.** Safe zones: top UI ~y 0-160, bottom caption ~y 1440+.
  Everything that matters lives inside the recorded canvas.

What I noticed reading the two specs glows with two empty rooms the house hasn't furnished yet:
**nobody has proposed what the *camera* does across a whole clip** (the tiers are single-chord
beats; the jam is a whole song), and **Mythic is a colour nobody has a payoff for** — it's the
legitimate once-a-month moment and it currently ends at "prismatic word + a veil." I spend most of
this document on those two because they're where the *content* is.

---

## Part 1 — TikTok and video formats built from what already exists

These are formats, not feats. Each one names the build it rides, what a viewer sees in the first
two seconds (the hook), and the honesty guardrail. None of them needs a single new 3D effect — they
are edits, captions, and the camera the recordings already give us.

### 1.1 The rarity reveal (rides: spectacle tiers + the log)

**The hook.** A chord strikes and the whole stage gasps gold. The viewer doesn't know *why* — and
that's the tension of the video.

**The format.** A 20–40 s supercut of Daniel playing through a phrase. Each chord change is a
tier. The video *withholds*: it shows the chord, the bloom, the banner — and only on the last one
does the caption reveal the theory ("this is B7#11 — a tritone away, and he only plays it for the
first time tonight"). The rarity system already manufactures the drama; the format just delays the
explanation until the payoff.

**Why it works.** Anticipation is the loot-feel's whole thesis (Diablo's beam *before* the item).
A viewer scrolls because they feel the weight before they understand it. The honest guardrail: the
banner already names the chord and its Nashville number, so the caption is *quoting the system*,
not inventing rarity. If the tier was lifted by novelty, the banner says *why* ("first this
session") — and so does the caption.

**House rule it leans on:** "The tier is about the chord, and every banner says why in music
words." The format *is* that rule, stretched over sixty seconds.

### 1.2 "An AI reads my practice log" (rides: the log + `practice riff`)

**The hook.** Text — stark, warm, a little funny — over the visualizer already running. "I asked
the machine what I actually practice." The machine's answer is never shown as a chart; it's shown
as *a sentence over his own hands*.

**The format.** The riff-report / practice-log analysis has facts with times, one question, one
thing-to-try. Instead of a report card, float the *facts* as captions timed to the moments they
name: at bar 4 the caption says "you keep landing on Dm11 and never resolve it"; at bar 8, "here's
you finally resolving it." The machine is the *narrator of a documentary about Daniel's hands*, not
a dashboard.

**Why it works.** "An AI reads the log" turns a private spreadsheet into a *confession*. The
viewer intuits there's a real system behind it (there is — it's honest), but they experience it as
a companion talking, which is the warmth Daniel keeps asking for ("I just play it by feel").

**Guardrail:** only say what the log can back. "First time ever" needs the 2,000-chord floor; the
riff-report script should reuse the *same* vocabulary gate as the rarity banner so a caption never
claims more than the system would.

### 1.3 The jam session, shot as a duet (rides: jam view `stage`)

**The hook.** Two pairs of hands — one pitch-coloured and bright, one moonlight silver — play the
same chord and the frame *names them both*. Then one of them leaves a note hanging and the other
answers it.

**The format.** Record in jam view `stage` (Claude stays on-stage, so it's an honest duet —
`BACKING BY CLAUDE` stays in the strip). Claude's band plays the loop (the band voicer keeps it
*under* G4, so Daniel's register stays free — that clearance *is* the visual of a good duet: hands
that never fight for the same keys). Daniel riffs over it. The video is a single loop pass: Claude
sets the bed, Daniel floats the melody, the chord label names both ("names what sounds: his notes
plus the backing").

**Why it works.** This is the *content Daniel already wants* — "we could have a lot of fun with
this" — and it needs zero new effects: the moonlight hand vs the pitch hand is already a
legitimate two-person scene. The formal touch that sells it: because Claude's hand has *no trails*
and Daniel's has *trails*, the frame reads "the band is still, he is the one dreaming."

**Honesty note:** in `auto`, REC moves Claude to the glass so a solo take stays solo. The duet
format is exactly the case where `stage` is the *honest* choice — name it, don't hide it. That's
the house's own stance (UX 7: "stage is a duet video; glass is his solo with a private coach").

### 1.4 The Nashville-number moment (rides: the Nashville row + key changes)

**The hook.** The same four chords in a *different key* — and the numbers don't move, while his
hands do. "It's the same song. Only the furniture changed."

**The format.** The jam spec already has the lesson baked in ("numbers restart at 1 in the new
key"). Shoot one loop in Eb, then the *same* loop transposed to a new key (the bridge re-voices
it). Split-screen or crossfade. The Nashville row stays `1maj9 4maj9#11`; only the note letters
change. Caption: "everything I learn in one key, I already know in twelve."

**Why it works.** This is a *teaching* that feels like a *magic trick*, and it's the single
cheapest format here — zero new shaders, it's just the transpose the bridge already does, filmed
twice. And it's honest down to the bone: the numbers *are* that abstraction. Daniel's line "I know
a little bit but not much >__<, this is intuition and memory" is the exact audience — this video
is for the person who plays by feel and is delighted that their feel was secretly a key-shape all
along.

### 1.5 The "reveal, in the rest" (rides: the rest-reveal card)

**The hook.** A phrase that earned Epic-or-better plays, the hands lift, the stage goes *quiet*
— and then, in the silence, one calm card appears. As little motion as the house allows.

**The format.** The spectacle spec already invented this ("A phrase that earned Epic or better gets
one calm card in the silence after it"). The format is just: don't cut away. Let the silence hold
the card. The tension of TikTok is *restraint* — every other video on the feed is shouting
non-stop, so a clip that goes *quiet and waits* is the loudest thing in the scroll.

**Why it works.** The card doing the work is a matter of dignity — the tiers spend all night
climbing to a climax and the reveal is the *breath after*, which is what makes the climax mean
something. This is the anti-callback: no drop, no whip-pan, just the earned quiet.

---

## Part 2 — Shader and scene ideas

These *are* new effects, so I've written them as proposals to slot into the two lanes, each with
the discipline rule it respects and the "what it's made of" so an integrator can judge cost. I keep
to the house physics: additive light is budgeted, gold is Legendary-only, and the protect mask
keeps text legible.

### 2.1 The rarity tiers need a *camera arc*, not just a chord beat

**The gap I couldn't close.** Every tier treatment the spectacle spec describes is a *chord-scale*
event — a ring pulse, a rail shimmer, a gold hem. But a 60-second TikTok is a *phrase-scale* event:
the camera should be doing something across the whole run that the individual tiers ride *on top
of*. Right now the only camera move is the Legendary push (3%, no yaw — and the spec is right to be
seasick-shy). I think the missing piece is a **tier-driven camera** that's slow enough to be
invisible and continuous enough to *carry* the cut.

**What it's made of.** A single smoothed "height" scalar the camera slowly orbits by, driven by the
*running* tier density over the phrase — not per chord, but as a smoothed envelope. When the phrase
is Common, the camera sits flat and respectful. When a Rare hits, the height drifts up a hair. Epic,
a little more. The point is *never* the move — the point is that the frame *breathes with the music*
so the individual Legendary push lands on a surface that's already moving slightly and therefore
reads as *arrival*, not *jolt*. Cap the total drift tight (the spec's 3% Legendary push is the
*one* obvious jump; everything else is a sub-2% smooth wander over seconds).

**Rule it respects:** "Camera push — Legendary only, no yaw, skipped on fast pans." I'm *not*
proposing to break that — I'm proposing a *background* drift too small to count as a "push," with
the Legendary push still the only thing that reads as a deliberate move.

**Why it matters for content:** this is the difference between a clip that's a *sequence of pretty
frames* and a clip that's a *shot*. A tiny height drift is what makes a supercut cut *together*.

### 2.2 The jam view needs a *stage floor* for the band (the one effect the duet is missing)

**The gap.** Claude's hand on the keys is fully designed (moonlight, no trails, 0.75 cap). But a
duet has a *second* thing the camera wants: *where the band lives*. Daniel's keys are lit by his
tone; Claude's keys are lit by moonlight — but the *space between them* is unlit. A single,
cheap, always-on floor treatment would make `stage` read as "a band is playing in this room,"
instead of "a second MIDI stream pressed the same keys."

**What it's made of.** A soft moonlight pool on the *floor* (not on the keys — the keys are his).
Concretely: a low-luma radial gradient on the empty floor under the keyboard, tinted `#C8DCFF`,
whose radius *slowly breathes* at the band's groove frequency. It is Claude's presence without
Claude's hand. It's one quad, drawn *under* the bloom threshold (so it never feeds the light
budget — it's normal-blended, not additive), and it dims when Daniel plays a strong chord (a
*mirror* of the house-light dim: the band yields to him, which is the whole point of the band
voicer keeping under G4).

**Rule it respects:** light budget + "Claude never pitch-tinted, never over Daniel." This is
moonlight, static hue, under-bloom, so it adds *place* and no *luma war*.

**Why it matters for content:** the duet video (1.3) without this is "two hands and a caption."
With it, it's "a band is in the room with him." One quad is the cheapest possible purchase of
that feeling.

### 2.3 Mythic needs a *payoff that is honest but not silent*

**The gap.** Mythic is the house's legitimate once-a-month-or-less moment ("first time ever" on
fancy new vocabulary), and its current treatment is "prismatic word + a low-luma aurora veil."
That's *correct* — the house has been scrupulous that Mythic must never be a staged lie — but a
prismatic *word* is a text effect, and this is the one event where the house could give the
*spectacle itself* the chord's own colours and have it read as the summit of the whole rarity
ladder, not a gold-with-a-rainbow-hat.

**What it's made of.** This is the one place I'd spend real light, and I'd spend it *only* here,
*only because the gate already makes it vanishingly rare*. A "prismatic bloom" that is literally
Daniel's own note colours: the existing bloom pass, but this once, the glow's hue *rings through
the chord's pitch palette* as it decays — each bloom halo inherits the hue of the note that
emitted it, in circle-of-fifths order, so the *decay* becomes a slow spectral scroll. It's not a
new texture; it's the bloom tinted to honour the chord, for exactly as long as a Mythic holds.

**Rule it respects, and where I'd whisper "and":** the theory-rarity table already gives Mythic
"prismatic — the chord's own note colours" for *the tier word*. My proposal is to extend that
semantic to the *light* — the bloom wears the chord — because a once-a-month moment that only
colours a word undersells the system's own honesty: the data *earned* this, and the stage should
look earned too. Guardrail: this must still pass `wash_check` (staff box mean luma ≤ the spec's
own receipts), and velocity still never changes the *tier*, only the *size*.

**Why it matters for content:** the Mythic is *the clip he posts*. Currently that clip is a
legendary gold beat plus a rainbow word. With the prismatic bloom, it's a clip where the *whole
frame* turns into the chord's own colours for four seconds — a thing no other rarity tier can
produce, which is exactly what "Mythic" should mean.

### 2.4 A "loops on the floor" ring-reader (for the Nashville moment, cheap)

**The gap.** The Nashville format (1.4) wants the viewer to *see* that the numbers stay fixed
while the letters move. Right now the numbers live in the HUD row; the *abstraction itself* —
"same shape, different furniture" — isn't shown as a shape.

**What it's made of.** A small floor glyph, glass-only (never recorded unless he chooses), that
draws the chord as a *cycle* — a ring of dots in circle-of-fourth/fifth order with the current
chord's degrees lit, so a `1maj9 4maj9#11` loop *looks like* a little constellation that stays
identical when the key transposes and only the note-labels rotate. Training wheels off: this is a
*visual mnemonic*, not a gameplay mechanic.

**Rule it respects:** glass-only means it never contaminates a take; it's a coach's overlay, the
same status as the ghost labels.

**Why it matters:** it's the one idea here that's *purely* for his private practice screen, and
it's the cheapest possible embodiment of the house's own lesson ("numbers restart at 1 in the new
key"). If it never ships, the Nashville video still works; if it does, the video explains itself
with a glance.

---

## Part 3 — What I'd *not* do (the restraint list, so the house knows the ideas above aren't a pile)

Every one of these I considered and am *recommending against*, with the reason, so the integrator
has a negative space to match my positive ones:

- **No "summon a Mythic" button for content.** The spec already cut the lab-only force hook for
  exactly this (E16/D14) — a staged tier on a public clip is a false claim. A Mythic TikTok has to
  be a *caught* moment, not a scripted one, and its rarity *is* its value. I'd rather the house
  wait a month for a real one than fake one tonight.
- **No tier-coloured *trails*.** Trails are Daniel's sustain meaning and stay pitch-coloured.
  Tier chrome stays on the banner/rim/ring. (The two lanes both landed here independently.)
- **No additive light for the jam floor (2.2) — keep it under bloom.** Moonlight presence should
  be *place*, not *fire*. If it feeds the light budget it starts competing with the chords, and
  the chords always win.
- **No camera yaw, ever for tiers.** The spec's seasick receipt is right; the 2.1 drift is
  *height only* and capped so it never reads as a "move."
- **No captions that out-claim the banner.** The vocabulary gate is the system's honesty spine;
  any TikTok caption must be a *quote* of `harmonicRole` / `log`, not a bardically invented
  theory word. The house has already burned three theory slips on the reason vocabulary — the
  caption layer must not re-open that wound.

---

## Part 4 — A one-line handoff to each lane

- **To the spectacle lane:** take 2.1 (the camera-arc envelope) and 2.3 (prismatic bloom for
  Mythic). 2.1 is the thing that makes your tiers *cut together into a video* instead of reading
  as a sequence of chord beats; 2.3 is the payoff Mythic is owed and currently only gets as a
  word.
- **To the jam lane:** take 2.2 (the moonlight floor pool) and 1.3 (the duet format). The floor
  pool is the one missing *scene* element for `stage`; the duet is the one format your `stage`
  view was literally built to produce.
- **To the house at large:** the formats in Part 1 (reveal, practice-log reading, duet, Nashville,
  rest-reveal) need *no* new code — they are edits over what two lanes are already shipping. If
  the video arc is "content between all of this" (Daniel's words), then Part 1 *is* the arc, and
  it can start the night the two builds land.

— Navi
