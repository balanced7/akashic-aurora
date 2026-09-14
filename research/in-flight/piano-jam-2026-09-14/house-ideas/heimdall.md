# Heimdall — band feel, honest timing, and concept cards

Sibling idea file, filed overnight 2026-09-14 at Vandor's invitation. Daniel is asleep; this is a relaxed
ideas pass, not a sprint. I read the jam-spec, design-music, design-data and the FL bridge lane first, so
these are extensions of what is already specced, not repeats — and where I disagree with a spec default I
say whose call it is. Nothing installed, nothing opened, no running file touched.

My lens, stated once: a band feels alive not when it plays more notes, but when it is *provably paying
attention and provably fallible*. Daniel is a gifted ear player with a soft, fast touch (median velocity
46-56, onset gaps 216-316 ms) who already hears the thing he "doesn't understand." So the band's job is
half to give him a groove worth leaning on, and half to occasionally *not* play — to leave a hole and be
seen leaving it. A metronome never leaves a hole. A bandmate does.

---

## 1. The band: what makes it feel alive rather than mechanical

### 1.1 The single biggest lie in any generated band is that it is always right

The spec already humanizes (timing, roll, velocity, length) and ducks under his rest. That is the *surface*
of liveness — it makes notes wobble like a person. The deeper liveness is **state**: a real rhythm section
remembers what just happened and lets you hear the memory. I'd pin three small memory knobs that cost almost
nothing and pay out every bar:

1. **Breath in the fills, not the grid.** A drummer doesn't fill on a schedule; he fills because the last
   bar built toward it. Tie `--fill` to *density of the last two bars* rather than "every N bars." If Daniel
   just played a dense run, the band should lay way back for a bar (drop the comp to roots, thin the hats)
   and *then* answer with a fill — the fill reads as a response, not a calendar event. The seed ("fill if
   the previous 2 bars' note-count crossed a threshold") is deterministic given his log, so it stays
   spec-compliant and rebuildable. Which threshold: his per-bar median + 50%, measured from his own sessions
   (the 1.1 table), not hard-coded.

2. **The band should occasionally lead him *into* a change, not always trail it.** Right now every switch
   lands on the bar line (correct, never mid-bar). But the *walking* bass and *gospel* triplet run already
   point at the next bass note. Make that pointing *audible as intention*: on the bar before a section change
   (not just a chord change), let the bass overtly step to the next root a half-beat early on the "and of 4."
   That single early note is the difference between "a sequencer that changes chords" and "a bassist who
   can see the chart." It is also the exact gesture Daniel already owns — the gospel half-step slide — so
   the band teaching him is using his own vocabulary.

3. **Silence as a schedulable lane.** Every groove should have a `dropout` setting (0 to 1 bar, default an
   occasional 1-bar hole). When it fires, the whole band except the bass rests for one bar. The effect on a
   musician is immediate and physical: the floor falls away and his next note is *exposed*, and he gets to
   feel what the room hears when he stops. That is contrast — his stated growth edge — delivered by the band
   refusing to fill, not by him being asked to practice contrast.

### 1.2 How the band should listen: duck is step one; *echo* is the melody

The duck (-3 dB, held 1.2 s) is the right size for his note gaps. But ducking is only "getting out of the
way." The thing that makes a sideman feel alive is **echo** — the band quietly repeats a shape Daniel just
played, a beat or two later, an octave (or a fifth) below his register.

Concretely, and cheaply: a `follow` knob. The transport already receives his note stream for ducking; it is a
small step to keep a short window of his top-line onsets and, on the *next* downbeat after a phrase gap of
600 ms (his measured phrase split), have the comp play the last 3-4 pitch classes of his last phrase as a
soft, low, harmonically-correct voicing — only when those pitch classes are in-chord or colour (reuse the
9.6 classifier, which exists). If they're outside, stay silent this time.

Why this matters more than it sounds: it closes the call-and-response loop in the direction Daniel most needs,
*without* putting his own notes back in his face verbatim (which would read as mocking). It says "I heard the
thing you found" in a lower, slower voice. That is what a real band does, and it is the single most
alive-feeling move available below one page of code.

### 1.3 Call and response: give the *call* a shape worth answering

The spec's call-and-response (9.10) scores *his* echoes of the band. It says less about the band's own calls.
For a call to invite an answer it needs **question-ness**: an unresolved ending. So the band's call should:

- land its last note on a **colour** (9/11/13), never the root — the same "land on colour = question" rule the
  report already uses for him, mirrored onto the band so the game is symmetric;
- end a touch *high* (open) rather than low (closed);
- be the only thing sounding — trigger the `dropout` above for the call itself, so his answer is the next
  note in an otherwise silent room.

If both sides use "question = land on colour, answer = land on root," the jam becomes a duet with rules he
can feel long before he can name them. And his growth edge (tension → resolution) is the whole mechanic.

### 1.4 Grooves from *his* numbers, not from a style sheet

`band.py` styles (ballad, neo-soul, halftime, brushes…) are good, but they were written from genre, not from
him. His sessions say: median onset gap 216-316 ms means eighths at 72-90 bpm *never rush him* (a pulse is
slower than his own note rate). I'd add one groove tuned to that fact — a **"breathing"** groove whose comp
strikes land intentionally *just after* his median gap (so there is always air before the band's next hit),
and whose hats are 16ths only when they'd fall in the *silence between* his phrases. The design-music engine
already notes this once (1.1) and then the groove list drops the idea; I'd carry it through. A band that
breathes around his actual tempo is worth more than any one more style.

---

## 2. The timing pins — honest clock, honest band

Vandor asked specifically: *what pins would you write to keep the timing honest?* Here are the ones I would
fight for, in order of leverage.

### 2.1 Pin the clock to the beat, not to the tick

The FL bridge lane's most important finding, which the band build must not paper over, is that **`onTick` is
not a clock you can trust to make a band feel human** — and `OnUpdateBeatIndicator(value)` is. I'd write the
band so that **every scheduled note keys off beat/bar edges it *receives*, never off wall-clock estimates it
*projects*.** Two reasons:

1. It is the difference between "the band is *on* the beat" and "the band is *near* the beat most of the
   time." A projected clock accumulates float error; a beat callback is the truth as FL experiences it.
2. It is what makes the band *able to be laid back on purpose*. You cannot play 10 ticks late reliably if
   your 10ticks is drifting against a projection. The `band.py` "laid back = 10 ticks late at 480 PPQ" only
   *means* something if the zero it leans against is FL's own beat signal.

So: the pin is **a beat-number register** that only `OnUpdateBeatIndicator` can advance (1 = bar, 2 = beat),
plus a hard rule that no note may be emitted at `beat + offset` unless that `beat` was actually seen. If a
callback is missed (FL under load, a plugin spike), the band *skips* that note rather than playing it late —
a skipped ghost note is inaudible and honest; a lateness of one whole missed bar is neither.

### 2.2 Pin switches to the *next* bar, and make the pin visible

Already correct in `band.py` (`next_bar_line`, never mid-bar). What I'd add is not mechanism but a
**confirmation echo**: when a pattern/clip switch is requested, the band should not silently cut over — it
should land the switch *and* mark it with a one-bar reduced voicing (bass + one comp note) so Daniel *hears
the section turn even with his eyes on the KeyLab.* He improvises by hand; the band owes him an audible
map of where it is. A change he can only see in the strip is a change he will play through by accident.

### 2.3 Pin the humanize seed to the *bar*, never the session

The spec humanizes with a `seed`, good. The subtle bug to pre-empt: if the seed is session-global, the same
"late snare" repeats identically every pass and after two passes the wobble *reads* as pattern (the ear finds
repeats fast). Pin the humanize seed to **(seed, bar, lane)** — so each bar's wobble is unique but the whole
jam is still reproducible from one seed. That yields "lively" that never becomes "predictable," at zero cost, and it
is the single cheapest liveness boost in the whole build.

### 2.4 Pin his playing to a baseline that includes FL's own delay — then never "correct" him

The tap-along calibration (8.2) already captures FL's buffer + plugin delay + his tapping habit into one
offset, and measures him against it. That is the right move and I'd protect it as a *prin*, not a knob:
**once calibrated, his notes are judged against his own baseline, and the band never re-tunes him.** The
failure mode to guard against is a well-meaning "follow" that nudges tempo toward his latest bar — that is a
band leaning on the soloist's breathing, which reads as *chasing*, the single most mechanical thing a band
can do. The band's tempo is FL's; Daniel's placement is measured; the two may differ by his offset and that
difference is *data, not error.* Write it down as an invariant in the band module header so a future edit
doesn't "fix" it.

### 2.5 The pin that matters most: don't let the band pretend precision it can't have

FL's `channels.midiNoteOn` plays a note live but the bridge can't confirm its actual sample position. So the
band must **never claim a timing it did not verify.** I'd gate any "we were on the grid" claim behind a
once-per-session click drill (the FL lane's click drill) that measures loopback latency, and until it is run,
the band reports timing *qualitatively* ("band played laid-back") not *quantitatively* ("-12 ms"). This is
the same honesty rule I'd give the report about Daniel — never state a number the instrument never produced.
A band that exaggerates its own tightness is lying to the musician it exists to serve.

---

## 3. Concept cards — teaching theory through *his* moves

The cards already exist as a specced object (chord chips, Play/Show/Loop/Try/Hear me). Vandor asked for ideas
specifically aimed at a gifted ear player whose edge is **tension and contrast**. My contribution is a
curation principle and a few card *types* I think are missing, all of them "his move → the name for it," in
the order of the ear, not the textbook.

### 3.1 The principle: every card should end in a *fight*, not a fact

He said "I just play it by feel" and "I don't understand a lot of what I do — this is intuition and memory."
The trap is cards that *name* what he does (satisfying, but it trades his intuition for a vocabulary and he
already owns the intuition). The better card **takes a thing he already reaches for and then withholds its
resolution**, so the lesson is lived, not read. A card that tells him "this is the Lydian #4" is a fact. A
card that loops `1maj9 → 4maj9#11` and then *stops on the #11 and waits* is a lesson in what the #11 wants to
do next — which he will now discover by hand. That is teaching a player, not a student.

Concretely: every card gets a **"landing"** — the note the loop deliberately leaves unresolved at its end —
and the card's single line of theory is about *the pull that note creates*, never about the symbol. Tension is
his edge precisely because he feels the pull already; the card's only job is to put a name on the pull and
let him resolve it himself.

### 3.2 Four cards I'd build on his own moves

**The Lydian 4.** `1maj9 | 4maj9#11`, landing on the #11 (D in Eb). The one line: "the #4 is the note that
makes the 4 chord float — it wants to fall back to the 3 of the 1." Card action: the loop holds the #11,
silent, under a held 4 chord, and one word in the strip: *"land it."* He resolves it or he doesn't; either is
a conversation. (This card also quietly fixes the spec's C19 gap — his signature `maj9#11` has no name on his
screen; this card is where that name earns its keep.)

**Gospel 5/4 slash chords.** `4maj7 | 5/4 → 1`, the classic gospel lift, landing on the 5 with the 4 in the
bass and the *major 3rd of the 5* left for him (the spec's "real 5" stretch — his 3rd is the one he omits).
The one line: "the slash bass (the 4 under the 5) is the *rubber band* — it's what makes the 5 pull upward
instead of sit." Try-mode should drop the 5 chord's 3rd so the *only* way to complete the lift is his note.
He learns the slash chord by being the missing piece of it.

**Chromatic half-step slides.** Two cards, to teach both directions of a move he already plays. Slide-in
(approach from a half-step below into a chord tone — the spec notes he almost never plays real outside notes,
so this is a genuine first stretch, not a correction) and the *parallel* slide the spec's gospel bass uses.
The one line: "a half step is the smallest honest move — it's how you arrive somewhere *announcing* it."
Landing: the target chord tone, held.

**Dropping a minor third to change key.** The card shows a two-chord loop whose second chord's root is a
minor third *below* the first (the relative-median drop), and its landing is the two notes themselves —
played as a dyad so he can hear the interval *as* a key-change lever before hearing it as a scale relation.
The one line: "drop the root a minor third and the whole light changes colour — same shape, new room." This
teaches relative keys by ear before it ever names them.

### 3.3 Two card *types* I think are missing

**"Your move, named" — a card that *is* a moment of his.** The spec stores moments (from state, git-ignored).
The missing card is the automation that turns one of *his own* logged moves into a card: detect a recurring
motif or a signature landing (the 9.9 motif finder already exists), snapshot its exact voicings, and mint a
card titled in his words-plus-the-name ("the G he keeps leaning on — that's the 9 over the 6 chord"). Nothing
teaches theory like hearing your own hand explained back to you. This is `template save-from-moment` with the
naming turned *on* — the single highest-leverage card because it is autobiographical.

**"Tension → resolution" as a two-card pair, not one card.** Contrast is his edge, so teach it symmetrically:
a "question" card that lands on colour (tension, unresolved) and a matched "answer" card that begins where
the question left off and resolves to the root. Played back-to-back they *are* the lesson in phrasing; played
separately they're two moods. The ear learns the contrast by hearing the hinge, which is exactly what a
textbook call-and-response diagram cannot do.

---

## 4. What I would *not* do (the "don't sprint it" part)

Three restraint calls, offered because Daniel said don't sprint it, and because the most alive thing we can
ship is a small set of things that all listen:

1. **Don't make the band improvise harmony.** Keep voicings deterministic and spec-checked. The liveness must
   come from *timing, memory, silence and echo* — the places where a tiny bit of state reads as a whole lot of
   humanity — not from the band choosing notes it cannot defend the choice of. A band that surprises him with
   a wrong re-voicing learns nothing and teaches nothing; a band that surprises him by *not playing* lands
   every time.

2. **Don't add more styles before the first three breathe.** `ballad`, `pulse`, `gospel` (already specced)
   plus the `dropout`/`echo`/`follow` ideas above are a complete first instrument. Every additional genre
   style is surface liveness you have to then make *not* wobble. Ship the band that listens; the style sheet
   can grow later against what he actually gravitates to.

3. **Don't let the report outrun the instrument's honesty.** The most valuable thing we can hand a gifted ear
   player is *his own playing, named and located*, not a score. Every number must trace to a real measurement
   (beat callbacks, calibration, the log) or it doesn't ship. Daniel will forgive a missing feature long
   before he forgives being told he played "-12 ms" on an instrument that never measured it.

— Heimdall (Deepseek · Onyx · Blue · 2)
