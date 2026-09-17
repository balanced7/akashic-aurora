// The moment: arsenal/web/piano/moment.js (pure ES module: no three.js, no DOM). Tests: tests/piano_moment.test.mjs.
//
// Daniel's ask for the /piano instruments round "Instruments of light", in his words: "When a chord feels really intense it
// can start building some kind of artifact, then when the chord changes it can change. some way of visually changing the
// overall energy level and feel depending on pace and flow. where the visuals creatively display the density and
// relationship of notes and can measure the emotional feel of the moment. just throwing ideas out there ^__^", and "lush
// chords could emit a wind or fog or something and the colors can possibly change with the chord tensions and feels."
// This module is the second half of that pair. harmony-feel.js reads what a chord IS (its colour, its tension, the dance of
// bass and solo); this one reads how the playing MOVES: how much energy is in the room, how fast, how steady, how connected,
// how dense, and what the held chord is building. It draws nothing and decides no look: an instrument maps the numbers to
// its own light, wind, fog or crystal.
//
//   import { createMoment } from "../moment.js";
//   const moment = createMoment(options?);      // one per instrument, next to a harmony-feel instance; options override any
//                                               // MOMENT constant by name
//   const m = moment.update(state, dt, t, f);   // every frame, f = feel.update(state, dt, t); m is ONE object refreshed in
//                                               // place (nothing allocated per frame)
//   moment.reset();                             // back to rest (a new song, a seek)
//   moment.frame                                // the same object update returns
//   moment.constants                            // the constants this moment runs on (MOMENT with the options folded in)
//
// Input (read only, never written):
//   state.sounding  Map midi -> { vel, t0, held, pedal, tRelease, strike }: every note that sounds. Used here: the key
//                   (midi), vel (0..127; a missing one reads as 90), t0 (the strike time, on the same clock as t), held and
//                   pedal (a voice with held false, or pedal true, is a pedal wash), and strike (the host's strike counter).
//                   An older host without it: state.pressed (Map midi -> entry) is read instead. A strike is seen when a
//                   midi appears that was not sounding the frame before, or when a sounding midi's strike counter changes
//                   (a host with no counter: when its t0 changes, because the host replaces the entry on a re-strike).
//                   The strike's time is its t0 when the entry has one, else the frame's t.
//   f               the harmony-feel reading for the same frame: f.colour (tension, lushness, brightness, openness),
//                   f.voices.spread, f.dance (consonance, motion) and f.events.chordChanged are read. Nothing f already
//                   holds is computed again here. A missing f reads as harmony-feel's rest.
//   dt, t           seconds since the last frame, and the clock time now. A missing dt is taken from t; a t that goes
//                   backwards (a seek, a replay) forgets the strike history.
//
// Output m (the same object every frame; m.artifact, m.mood, m.events and m.raw keep their identity too):
//   m.energy     0..1, smoothed with energyAttack up and energyRelease down (so about 2 s to settle). The raw reading is
//                loud * (energyFloor + (1 - energyFloor) * busy) * energyGain, clamped to 1, where loud is the larger of
//                the strike level and the sound level, and busy is the note rate (1 - exp(-pace / energyPaceScale)),
//                the register spread (f.voices.spread over energySpreadFull) and the pedal wash (pedal-held voices over
//                energyWashFull), weighted by energyRateWeight, energySpreadWeight and energyWashWeight. The strike level
//                is how LOUD the recent strikes were, not how many: the mean of every strike's loudness (vel/127)^velCurve
//                over the last paceWindow seconds, each weighted by its freshness exp(-age / strikeTau), times the newest
//                strike's own freshness (so the level fades with strikeTau from the last strike). A pianissimo run at ten
//                notes a second is still pianissimo; velocity is what separates a pp presto from an ff presto, and the
//                rate lives only in busy. The sound level is the mean loudness of what still sounds, each note fading with
//                sustainTau (a piano's tone). Soft playing is low energy however busy it is; a wide loud wash and a fast
//                loud run both read high, and energy starts falling the moment the playing stops.
//   m.pace       notes a second (a raw count, not 0..1): strikes in the last paceWindow seconds divided by the window, or by
//                the time since the sound (re)started when that is shorter (paceSpanMin at least), so a run reads its
//                rate within a second of starting rather than a window later. Eased with paceTau. A four-note chord is
//                four notes.
//   m.pulse      0..1: steady timing (1) against free rubato (0). Strikes within groupGap of each other are one beat (a
//                chord). The intervals between the last pulseCount beats (a rest longer than pulseMaxGap breaks the chain,
//                and fewer than two intervals read 0) are fitted to a grid: every interval, and its half and third, is
//                tried as the unit (units under pulseUnitMin are not tried: a roll is not a beat), each interval is snapped
//                to its nearest whole number of units, and the best unit is the one with the smallest root-mean-square
//                residual, in units. pulse = (1 - that residual / pulseJitterFull) * min(1, intervals / pulseConfident):
//                two beats are no evidence of a grid, five are. Rhythm does not matter, only whether it keeps a grid: a
//                metronomic run, a swung stride (long-short pairs), a march (quarter, eighth, eighth) and a steady
//                accompaniment with the bass on one and the chords on two and three all read about 1; random timing
//                reads 0 and a rubato ballad about 0.2..0.4. Eased with pulseTau, and it falls to 0 once nothing has
//                been struck for pulseHold.
//   m.flow       0..1: connected, legato (1) against detached, staccato (0). Every beat measures its own connectedness: 1
//                when sound was still on when it landed (a finger held, or the pedal holding the sound before it), else
//                1 - (the silence before it) / (the gap since the last beat), so a note held for a fifth of its gap reads
//                0.2. A phrase's first beat (nothing struck for flowHold before it) has nothing to connect to and reads
//                0.5; the second takes its own value outright; every later beat moves the reading flowMix of the way to
//                its own value. The frame eases with flowTau, and the reading falls to 0 once nothing has been struck for
//                flowHold. Silence is read at frame resolution (a gap shorter than a frame is legato).
//   m.density    0..1: distinct pitches sounding now or struck in the last densityWindow seconds, over densityFull (one
//                note 0.1, four 0.4, ten and more 1). Eased with densityAttack up and densityRelease down.
//   m.intensity  0..1: builds while a tense or lush chord is held with the energy up, decays after the chord changes or the
//                sound stops. The target is max(f.colour.tension, f.colour.lushness) * min(1, energy / intensityEnergyFull);
//                it rises toward the target with the intensityBuild time constant and falls with intensityDecay. After a
//                chord change it follows the new chord: it falls if the new chord is plainer, and builds on if it is not.
//   m.artifact = { growth, seed, age, released, releaseStrength }: the thing an intense chord builds
//     growth          0..1: rises at intensity / growFull a second while the chord holds (full after growFull seconds at
//                     full intensity), never falls and never resets mid-chord. It restarts at 0 when the chord changes
//                     or ends (the sound has been off for endGap). Under a chord name (state.chord.name) the change is
//                     harmony-feel's chordChanged, and a chord holds from that, or from the sound returning under a name
//                     after a rest (the same name coming back is no change to harmony-feel, but it is a new artifact
//                     here). Without a name (state.chord null, which is what the host hands over for a cluster, or no
//                     state.chord at all) the sounding pitch-class set is the chord: it holds from the frame three or
//                     more pitch classes sound (age counts from there), and a different set of three or more is the
//                     change, so a cluster builds and releases like a named chord, and a name arriving over a different
//                     set is a change too. A name going null while sound continues (a lone note after the chord) does
//                     not end it, the next chord or the next rest does.
//     seed            an integer (under 2^30) that changes on every chord change and end, so a renderer can vary the shape
//                     of each artifact. Stable for the life of one chord.
//     age             seconds since this chord began (0 while no chord holds).
//     released        true only on the frame a chord whose growth was over releaseMin changes or ends.
//     releaseStrength the growth at release, on that frame only, else 0.
//   m.arc        'resting' | 'building' | 'peak' | 'sustaining' | 'releasing', from the drive (the larger of energy and
//                intensity, so a crescendo and a chord building its artifact both read as a build), its slope (eased
//                with slopeTau) and its level (the drive when the state was entered; it follows the drive up to the
//                crest while building or at the peak, down to the trough while releasing or resting, and trails the
//                drive with arcLevelTau while sustaining). resting: drive under arcRest (and it stays resting until the drive clears
//                arcRest + arcBand). building: the slope over arcRise a second AND the drive arcStep or more above the
//                level (one chord struck in a level passage lifts energy a little and lets it fall again: that is a
//                ripple, not a build, and a crescendo is one build, not one per step). releasing: the slope under
//                -arcFall and the drive arcStep or more under the level. Once entered, building and releasing go on
//                while the slope keeps their sign past the threshold. peak: the crest, entered from building when the
//                rise stops; it lasts until the drive falls (releasing) or rises arcStep past the crest again
//                (building), or for arcPeakMax at most, then sustaining. sustaining: a level held with a flat slope,
//                reached from peak, from releasing when the fall stops (slope within arcFlat of 0) above rest, or from
//                resting on a swell too slow to be a build. Hysteresis: a state holds arcHold seconds at least before it
//                can change, so it never flickers.
//   m.mood = { valence, arousal, label }: an ESTIMATE OF THE MUSIC'S CHARACTER from its features. It is not a claim about
//                the player's emotions, or anyone's: a sad song played by a happy pianist reads sad.
//     valence   -1..1, bright and consonant (1) to dark and tense (-1): valenceBright * 2 * (f.colour.brightness - 0.5)
//               + valenceConsonance * 2 * (f.dance.consonance - valenceConsonanceMid) - valenceTension * f.colour.tension,
//               clamped, then eased with moodTau (about a bar: an accompaniment whose chord tones come and go within the
//               bar, an oom-pah, a broken chord, a ripple, must not swing the mood at beat rate). The tension, lushness,
//               brightness and openness the label rules read are eased the same way.
//     arousal   0..1: arousalEnergy * energy + arousalPace * min(1, beats / arousalPaceFull) + arousalDensity * density,
//               where beats is the BEAT rate (strikes within groupGap of each other are one beat, as for pulse and flow;
//               counted over paceWindow and eased with paceTau): a four-note chord is one beat here, so a soft
//               oom-pah-pah is no busier than a single line at the same tempo. m.pace still counts every note.
//     label     one of 'calm' | 'tender' | 'yearning' | 'searching' | 'playful' | 'tense' | 'dark' | 'triumphant', the
//               first rule that fits, in this order (low arousal: under moodLowArousal; mid: between; high: moodHighArousal
//               and over; positive valence: moodPositive and over; negative: moodNegative and under; near 0: within
//               moodNeutral):
//                 tense       mid or high arousal, tension moodTense or over
//                 playful     mid or high arousal, positive valence, detached flow (under moodDetached)
//                 triumphant  high arousal, positive valence, openness moodOpen or over or density moodDense or over
//                 playful     mid or high arousal, positive valence, high pulse (moodSteady or over)
//                 yearning    low or mid arousal, mildly negative valence (moodYearnFloor .. -moodPositive), lushness
//                             moodLush or over (maj7 or 9 colour in a minor setting)
//                 dark        negative valence (moodNegative or under) with brightness under moodDim or arousal not low;
//                             or, at mid or high arousal, any valence under 0 with brightness under moodDim (a
//                             fortissimo minor riff is dark, never calm and never playful)
//                 searching   low or mid arousal, valence near 0, low pulse (under moodRubato: rubato), and voices that
//                             move (f.dance.motion not "static")
//                 tender      low or mid arousal, positive valence, legato flow (moodLegato or over): a singing line at
//                             mezzo-piano is tender, not calm
//                 calm        low arousal and nothing above fits: valence near 0 or positive, low tension
//               Calm is a LOW-arousal word only. A mid or high arousal reading that fits none of the rules above takes
//               the nearest word instead, the first of these that fits:
//                 tense       tension moodTenseSoft or over (a rough edge on an unsettled passage)
//                 playful     positive valence, or high pulse (moodSteady or over), or detached flow (under moodDetached)
//                 searching   mid arousal (an unsettled middle reading with nothing else to name it)
//                 tense       high arousal (loud and unsettled)
//               Hysteresis, in time and in level: a new label must win for moodHold seconds without a break before it
//               shows (calm, the fallback, for twice that: a word is not dropped for a gap in which nothing else quite
//               fits), and the label showing keeps against a candidate from a rule BELOW its own in the ladder while
//               its own rule still fits with moodMargin to spare on every threshold but the arousal bands (playful
//               keeps on any of its three conditions; calm never keeps, it is the low-arousal fallback). A candidate
//               from a rule above always takes over: tense by tension moodTense or over displaces anything, and
//               searching, which comes before tender, takes a wandering line back from tender. So a reading drifting
//               along a threshold (a nocturne whose valence hovers at the edge of positive, a lament whose lushness
//               hovers at moodLush) holds its word instead of walking through calm and back. The mood's memory is no
//               longer than the phrase is old: after a restart the inputs ease with the time since the sound resumed
//               (moodTauMin at least) until that reaches moodTau.
//   m.events = { build, peak, release, restart }: true only on the frame it happens. build: the arc enters building. peak:
//                the arc enters peak. release: the artifact released. restart: sound resumes after restartGap or more of
//                silence (the first sound after creation or reset counts).
//   m.raw = { energy, pace, pulse, flow, density, intensity, drive, slope }: the unsmoothed readings the smoothed ones are
//                heading for, plus the arc's drive and slope.
//
// Smoothing: exponential and frame-rate independent (it uses dt), in the manner of harmony-feel.js: each frame eases toward
// the reading that was in force over the frame that just passed, then takes its new reading, so the same playing gives the
// same curve at 30 and at 144 frames a second. Pace, the beat rate, pulse, flow and density change in steps (a strike
// lands, a window slides), which that composes exactly. Energy's strike level fades between strikes, so energy eases toward
// the level's exact average over the frame (a strike landing mid-frame counts for the part of the frame it sounded), and
// intensity's target and the mood's inputs are smooth curves, so they ease toward the midpoint of the last two readings;
// growth integrates intensity by the trapezoid rule. All agree within a fraction of a percent between 30 and 144 frames a second. In
// silence everything returns to rest: energy, pace, pulse, flow, density and intensity 0, growth 0, arc resting, mood calm
// with valence at harmony-feel's rest and arousal 0.
//
// Constants (MOMENT; any of them may be overridden by name in createMoment's options):
//   maxDt 0.5 s               the longest frame step used (a stalled tab does not jump the readings)
//   energyAttack 0.6 s        time constant of energy rising
//   energyRelease 2.0 s       time constant of energy falling
//   paceWindow 2.5 s          strikes this recent count toward pace and loudness (128 are remembered: over 51 a second, the
//                             oldest are forgotten early)
//   paceSpanMin 0.5 s         the shortest span pace and the beat rate divide by while the window fills after a restart
//   paceTau 0.3 s             how quickly the shown pace follows the count
//   groupGap 0.05 s           strikes this close together are one beat (a chord struck at once), for pulse and flow
//   velCurve 1.4              loudness of a strike = (vel/127)^velCurve (a mezzo-forte 64 reads about 0.38)
//   strikeTau 1.0 s           a strike's contribution to the strike level fades with this time constant
//   sustainTau 4 s            a sounding note's loudness fades with this time constant after its strike
//   energyPaceScale 6         notes a second at which the rate term reads 0.63 (1 - exp(-pace / energyPaceScale))
//   energySpreadFull 48       register spread (semitones) that reads as full width
//   energyWashFull 6          pedal-held voices that read as a full wash
//   energyRateWeight 0.6      busy = energyRateWeight * rate + energySpreadWeight * spread + energyWashWeight * wash, at most 1
//   energySpreadWeight 0.2
//   energyWashWeight 0.2
//   energyFloor 0.35          energy = loud * (energyFloor + (1 - energyFloor) * busy) * energyGain: a loud lone note still
//                             carries energyFloor of its loudness
//   energyGain 1.8            so a mezzo-forte line reads about 0.4 and a loud busy passage reaches 1
//   pulseCount 8              beats whose intervals decide pulse
//   pulseMaxGap 2.5 s         a rest longer than this breaks the chain of intervals
//   pulseUnitMin 0.08 s       the smallest grid unit tried (a rolled chord or a flam is not a beat unit)
//   pulseJitterFull 0.29      root-mean-square grid residual (in units) that reads as no pulse at all: what random timing
//                             gives (a residual is uniform over 0..0.5, whose rms is 0.29); 0.05 reads about 0.83
//   pulseConfident 4          intervals that make the fit count in full (fewer scale it down in proportion: two beats
//                             are no evidence of a grid, whatever unit they happen to fit)
//   pulseHold 2.5 s           pulse falls to 0 once nothing has been struck for this long
//   pulseTau 0.4 s            how quickly the shown pulse follows its reading
//   flowMix 0.5               how far each beat moves the flow reading toward its own connectedness
//   flowHold 2.5 s            flow falls to 0 once nothing has been struck for this long
//   flowTau 0.4 s             how quickly the shown flow follows its reading
//   densityWindow 1.5 s       a pitch struck this recently still counts toward density
//   densityFull 10            distinct pitches that read as full density
//   densityAttack 0.1 s       time constant of density rising
//   densityRelease 0.5 s      time constant of density falling
//   intensityBuild 1.5 s      time constant of intensity building toward its target
//   intensityDecay 0.8 s      time constant of intensity falling
//   intensityEnergyFull 0.7   energy at which the chord's colour counts in full (below it, in proportion: a pianissimo
//                             seventh chord builds little)
//   growFull 2.5 s            growth reaches 1 after this long at full intensity
//   releaseMin 0.15           growth a chord needs for its change or end to count as a release
//   endGap 0.4 s              silence this long ends the chord (the artifact releases and the age restarts)
//   arcRest 0.1               drive under this is resting ...
//   arcBand 0.05              ... and it takes drive over arcRest + arcBand to leave resting (no flicker on a soft swell)
//   arcRise 0.08 /s           slope over this is building
//   arcFall 0.08 /s           slope under minus this is releasing ...
//   arcFlat 0.02 /s           ... and releasing ends in sustaining only once the slope is within this of flat (the tail
//                             of a fade is still a fade, until it rests)
//   arcStep 0.12              the drive must be this far above the level to start building, or below it to start
//                             releasing (the ripple of one chord struck in a level passage is smaller)
//   arcLevelTau 2.0 s         how quickly the level trails the drive while sustaining
//   arcHold 0.25 s            the least time an arc state holds before it can change
//   arcPeakMax 1.5 s          the longest a peak lasts before it reads as sustaining
//   slopeTau 0.3 s            smoothing of the drive's slope
//   valenceBright 0.8         weight of brightness in valence
//   valenceConsonance 0.2     weight of the bass-to-solo consonance in valence ...
//   valenceConsonanceMid 0.75 ... around this consonance (a minor 3rd: neither sweet nor sour)
//   valenceTension 0.5        weight of tension in valence
//   arousalEnergy 0.5         weight of energy in arousal
//   arousalPace 0.3           weight of the beat rate in arousal ...
//   arousalPaceFull 10        ... which counts in full at this many beats a second (a presto single line)
//   arousalDensity 0.2        weight of density in arousal
//   moodTau 1.5 s             smoothing of the mood's inputs (valence, tension, lushness, brightness, openness) before
//                             the label rules: about a bar, the scale harmony moves on
//   moodTauMin 0.15 s         the shortest that smoothing gets: after a restart the inputs ease with the time since the
//                             sound resumed, from moodTauMin up to moodTau (a phrase's memory is no longer than the
//                             phrase is old, so the first chord colours the mood at once)
//   moodHold 0.4 s            a new label must win this long before it shows
//   moodMargin 0.05           the label showing keeps while its rule still fits with this much to spare on every
//                             threshold (valence, tension, lushness, brightness, openness, pulse, flow, density; the
//                             arousal bands are strict), so a reading drifting along a threshold does not flicker
//   moodTenseSoft 0.3         tension that names an otherwise unnamed mid or high arousal reading 'tense'
//   moodLowArousal 0.4        arousal under this is low
//   moodHighArousal 0.65      arousal at or over this is high
//   moodTense 0.5             tension for 'tense'
//   moodPositive 0.05         valence at or over this is positive
//   moodNegative -0.2         valence at or under this is negative
//   moodNeutral 0.2           valence within this of 0 is near 0
//   moodYearnFloor -0.7       the most negative valence that is still mildly negative ('yearning')
//   moodLush 0.3              lushness for 'yearning'
//   moodDim 0.42              brightness under this is dim ('dark')
//   moodOpen 0.45             openness for 'triumphant'
//   moodDense 0.6             density for 'triumphant'
//   moodLegato 0.55           flow at or over this is legato ('tender')
//   moodDetached 0.45         flow under this is detached ('playful')
//   moodSteady 0.7            pulse at or over this is steady ('playful')
//   moodRubato 0.35           pulse under this is rubato ('searching')
//   restartGap 2.0 s          silence this long before a sound makes the sound a restart
export const MOMENT_API = "arsenal.piano.moment/v1";

export const MOMENT = Object.freeze({
  maxDt: 0.5,
  energyAttack: 0.6, energyRelease: 2.0,
  paceWindow: 2.5, paceSpanMin: 0.5, paceTau: 0.3, groupGap: 0.05, velCurve: 1.4, strikeTau: 1.0, sustainTau: 4,
  energyPaceScale: 6, energySpreadFull: 48, energyWashFull: 6,
  energyRateWeight: 0.6, energySpreadWeight: 0.2, energyWashWeight: 0.2, energyFloor: 0.35, energyGain: 1.8,
  pulseCount: 8, pulseMaxGap: 2.5, pulseUnitMin: 0.08, pulseJitterFull: 0.29, pulseConfident: 4, pulseHold: 2.5, pulseTau: 0.4,
  flowMix: 0.5, flowHold: 2.5, flowTau: 0.4,
  densityWindow: 1.5, densityFull: 10, densityAttack: 0.1, densityRelease: 0.5,
  intensityBuild: 1.5, intensityDecay: 0.8, intensityEnergyFull: 0.7,
  growFull: 2.5, releaseMin: 0.15, endGap: 0.4,
  arcRest: 0.1, arcBand: 0.05, arcRise: 0.08, arcFall: 0.08, arcFlat: 0.02, arcStep: 0.12, arcLevelTau: 2.0, arcHold: 0.25,
  arcPeakMax: 1.5, slopeTau: 0.3,
  valenceBright: 0.8, valenceConsonance: 0.2, valenceConsonanceMid: 0.75, valenceTension: 0.5,
  arousalEnergy: 0.5, arousalPace: 0.3, arousalPaceFull: 10, arousalDensity: 0.2,
  moodTau: 1.5, moodTauMin: 0.15, moodHold: 0.4, moodMargin: 0.05, moodLowArousal: 0.4, moodHighArousal: 0.65, moodTense: 0.5,
  moodTenseSoft: 0.3, moodPositive: 0.05, moodNegative: -0.2,
  moodNeutral: 0.2, moodYearnFloor: -0.7, moodLush: 0.3, moodDim: 0.42, moodOpen: 0.45, moodDense: 0.6,
  moodLegato: 0.55, moodDetached: 0.45, moodSteady: 0.7, moodRubato: 0.35,
  restartGap: 2.0,
});
export const ARCS = Object.freeze(["resting", "building", "peak", "sustaining", "releasing"]);
export const LABELS = Object.freeze(["calm", "tender", "yearning", "searching", "playful", "tense", "dark", "triumphant"]);

// harmony-feel's rest, for a frame handed no f.
const FEEL_REST = Object.freeze({
  voices: Object.freeze({ count: 0, bass: null, top: null, solo: null, spread: 0 }),
  colour: Object.freeze({ simplicity: 1, lushness: 0, tension: 0, brightness: 0.5, openness: 0 }),
  dance: Object.freeze({ interval: 0, family: "octave", consonance: 1, motion: "static", pull: 0, stretch: 0, phase: 0 }),
  events: Object.freeze({ chordChanged: false, bassMoved: false, soloMoved: false }),
});
const RING = 128, BEATS = 32, IVLS = BEATS - 1;
const NO_TIME = -1e9;
// how many pitch classes a 12-bit mask holds (the chord an unnamed sound holds is its pitch-class set)
const POP12 = new Uint8Array(4096);
for (let i = 1; i < 4096; i++) POP12[i] = POP12[i >> 1] + (i & 1);
// each label's place in the rule ladder (the index of its first rule), in LABELS order: the label showing keeps only
// against a candidate from a rule below its own
const PRIORITY = new Uint8Array([8, 7, 4, 6, 1, 0, 5, 2]);

// Known limits (the pianist's 233-check harness, 2026-09-17: 221 pass). flow reads 0.5-0.75 on detached patterns whose
// notes still overlap (stride, shout stabs), so a renderer should treat flow under ~0.6 as detached; 'calm' can show for
// the first second of a passage while the label hysteresis settles; a rubato nocturne mixes tender, searching and yearning
// rather than settling on one word; a plain final triad after a tense build grows a small artifact (about 0.36) rather
// than none.
const fin = (v, d) => (Number.isFinite(v) ? v : d);  // a number from f, or its rest value

export function createMoment(options = {}) {
  const K = { ...MOMENT };
  for (const key of Object.keys(MOMENT)) if (options && typeof options[key] === "number" && Number.isFinite(options[key])) K[key] = options[key];

  // The one frame object. Every number that is not always a whole number starts as a fraction, so the engine gives the
  // field a double slot from birth and every later frame writes it in place (reset() puts the resting values in first).
  const m = {
    energy: 0.5, pace: 0.5, pulse: 0.5, flow: 0.5, density: 0.5, intensity: 0.5,
    artifact: { growth: 0.5, seed: 1, age: 0.5, released: false, releaseStrength: 0.5 },
    arc: ARCS[0],
    mood: { valence: 0.5, arousal: 0.5, label: LABELS[0] },
    events: { build: false, peak: false, release: false, restart: false },
    raw: { energy: 0.5, pace: 0.5, pulse: 0.5, flow: 0.5, density: 0.5, intensity: 0.5, drive: 0.5, slope: 0.5 },
  };

  // Per-midi memory and per-frame scratch (typed arrays: nothing boxed, nothing allocated).
  const lastSig = new Float64Array(128), lastOnsetAt = new Float64Array(128).fill(NO_TIME);
  const wasThere = new Uint8Array(128), isThere = new Uint8Array(128);
  const ringT = new Float64Array(RING), ringV = new Float64Array(RING);  // strikes: time and loudness, newest at ringHead - 1
  const ringB = new Uint8Array(RING);                                     // 1 where the strike began a beat
  const beatT = new Float64Array(BEATS);                                  // beats (grouped strikes), newest at beatHead - 1
  const ivl = new Float64Array(IVLS);                                     // scratch: the intervals pulse fits to a grid
  let ringHead = 0, ringN = 0, beatHead = 0, beatN = 0, pcMask = 0, chordMask = 0;
  let count = 0, wash = 0, lastCount = 0, silent = true, started = false, chordOn = false, hasFrame = false, flowFresh = true;
  let arcState = 0, moodLabel = 0, pendingLabel = 0, beatLanded = false, wasNamed = false;
  // Doubles that live across frames sit in N (a closure variable holding a double would box a new number on every write).
  const N = new Float64Array(32);
  const LAST_T = 0, NOW = 1, HELD_PREV = 2, LOUD_SUSTAIN = 3, FLOW_ACC = 4, BUSY_PREV = 5, SILENT_AT = 6, LAST_BEAT = 7,
    CHORD_AT = 8, LAST_DRIVE = 9, ARC_AT = 10, PEAK_AT = 11, MOOD_AT = 12, GROWTH = 13, LAST_INTENSITY = 14, LAST_STRIKE = 15,
    PULSE_FIT = 16, BEATS_RAW = 17, BEATS_NOW = 18, ARC_LEVEL = 19, MOOD_V = 20, MOOD_TENSION = 21, MOOD_LUSH = 22,
    MOOD_BRIGHT = 23, MOOD_OPEN = 24, LAST_V = 25, LAST_TENSION = 26, LAST_LUSH = 27, LAST_BRIGHT = 28, LAST_OPEN = 29,
    RESTART_AT = 30;

  // Visits one sounding entry. The strike path lives inside it rather than in a helper of its own: a helper called once
  // every few frames from this hot, optimized code would run unoptimized and box every double it touches.
  function visit(e, key) {
    const mi = key | 0;
    if (mi !== key || mi < 0 || mi > 127 || isThere[mi] === 1 || !e) return;
    isThere[mi] = 1;
    pcMask |= 1 << (mi % 12);
    const t0 = typeof e.t0 === "number" && e.t0 === e.t0 ? e.t0 : NO_TIME;
    const sig = typeof e.strike === "number" && e.strike === e.strike ? e.strike : t0;
    const vel = typeof e.vel === "number" && e.vel === e.vel ? (e.vel < 0 ? 0 : e.vel > 127 ? 127 : e.vel) : 90;
    const v = Math.pow(vel / 127, K.velCurve);
    if (wasThere[mi] === 0 || sig !== lastSig[mi]) {
      // a strike lands: it joins the strike ring, and the beat ring unless it is part of the beat before it
      lastSig[mi] = sig;
      const at = t0 === NO_TIME ? N[NOW] : t0;
      lastOnsetAt[mi] = at;
      const newBeat = !(beatN > 0 && at - N[LAST_BEAT] <= K.groupGap);
      ringT[ringHead] = at; ringV[ringHead] = v; ringB[ringHead] = newBeat ? 1 : 0;
      ringHead = (ringHead + 1) % RING; if (ringN < RING) ringN++;
      N[LAST_STRIKE] = at;
      if (newBeat) {
        // connectedness of this beat: sound was on (last frame) when it landed, else how much of the gap since the last
        // beat was silent. A phrase's first beat has nothing to connect to and reads 0.5; its second beat takes its own
        // reading outright, and every later one moves the reading flowMix of the way.
        if (beatN > 0 && at - N[LAST_BEAT] <= K.flowHold) {
          let conn = 1;
          if (lastCount === 0) {
            const gap = at - N[LAST_BEAT], quiet = at - N[SILENT_AT];
            conn = gap > 0 ? 1 - (quiet > gap ? gap : quiet < 0 ? 0 : quiet) / gap : 0;
          }
          N[FLOW_ACC] = flowFresh ? conn : N[FLOW_ACC] + (conn - N[FLOW_ACC]) * K.flowMix;
          flowFresh = false;
        } else { N[FLOW_ACC] = 0.5; flowFresh = true; }
        beatT[beatHead] = at; beatHead = (beatHead + 1) % BEATS; if (beatN < BEATS) beatN++;
        N[LAST_BEAT] = at;
        beatLanded = true;
      }
    }
    const age = N[NOW] - (t0 === NO_TIME ? N[NOW] : t0);
    N[LOUD_SUSTAIN] += v * Math.exp(-(age < 0 ? 0 : age) / K.sustainTau);
    if (e.held === false || e.pedal === true) wash++;
    count++;
  }

  function forgetHistory() {
    ringHead = 0; ringN = 0; beatHead = 0; beatN = 0; lastCount = 0;
    N[LAST_BEAT] = NO_TIME; N[LAST_STRIKE] = NO_TIME; N[SILENT_AT] = NO_TIME; N[FLOW_ACC] = 0; N[HELD_PREV] = 0; N[BUSY_PREV] = 0;
    lastOnsetAt.fill(NO_TIME); wasThere.fill(0); isThere.fill(0);
    silent = true; chordOn = false; flowFresh = true; N[CHORD_AT] = 0; N[GROWTH] = 0;
    pcMask = 0; chordMask = 0; wasNamed = false; beatLanded = false; N[PULSE_FIT] = 0; N[BEATS_RAW] = 0; N[BEATS_NOW] = 0;
  }

  function reset() {
    forgetHistory();
    N[LAST_T] = 0; N[NOW] = 0; N[HELD_PREV] = 0; N[BUSY_PREV] = 0; N[LOUD_SUSTAIN] = 0; N[LAST_DRIVE] = 0; N[ARC_AT] = NO_TIME;
    N[PEAK_AT] = NO_TIME; N[MOOD_AT] = NO_TIME; N[LAST_INTENSITY] = 0; N[ARC_LEVEL] = 0; N[RESTART_AT] = NO_TIME;
    started = false; hasFrame = false; arcState = 0; moodLabel = 0; pendingLabel = 0; count = 0; wash = 0;
    m.energy = 0; m.pace = 0; m.pulse = 0; m.flow = 0; m.density = 0; m.intensity = 0;
    const A = m.artifact, R = m.raw, E = m.events;
    A.growth = 0; A.age = 0; A.released = false; A.releaseStrength = 0;
    m.arc = ARCS[0];
    const restValence = K.valenceConsonance * 2 * (1 - K.valenceConsonanceMid);  // harmony-feel's rest through the formula
    N[MOOD_V] = restValence; N[LAST_V] = restValence; N[MOOD_TENSION] = 0; N[LAST_TENSION] = 0; N[MOOD_LUSH] = 0; N[LAST_LUSH] = 0;
    N[MOOD_BRIGHT] = 0.5; N[LAST_BRIGHT] = 0.5; N[MOOD_OPEN] = 0; N[LAST_OPEN] = 0;
    m.mood.valence = restValence; m.mood.arousal = 0; m.mood.label = LABELS[0];
    E.build = false; E.peak = false; E.release = false; E.restart = false;
    R.energy = 0; R.pace = 0; R.pulse = 0; R.flow = 0; R.density = 0; R.intensity = 0; R.drive = 0; R.slope = 0;
  }

  function update(state, dt, t, f) {
    if (typeof t !== "number" || t !== t) t = N[LAST_T] + (typeof dt === "number" && dt > 0 ? dt : 0);
    if (typeof dt !== "number" || !(dt >= 0)) dt = started ? t - N[LAST_T] : 0;
    if (!(dt > 0)) dt = 0; else if (dt > K.maxDt) dt = K.maxDt;
    if (started && t < N[LAST_T] - 1e-6) forgetHistory();
    started = true;
    N[LAST_T] = t; N[NOW] = t;
    if (!f || !f.colour || !f.dance || !f.voices || !f.events) f = FEEL_REST;
    // A partial f (a caller's stub, or a field left NaN upstream) must never poison the smoothed state: every number read
    // from f is taken finite here, at its rest value otherwise (API audit 2026-09-17: a NaN that got in stayed for good).
    const fSpread = fin(f.voices.spread, 0), fTension = fin(f.colour.tension, 0), fLush = fin(f.colour.lushness, 0);
    const fBright = fin(f.colour.brightness, 0.5), fOpen = fin(f.colour.openness, 0), fCons = fin(f.dance.consonance, K.valenceConsonanceMid);
    const A = m.artifact, R = m.raw, E = m.events, MD = m.mood;
    E.build = false; E.peak = false; E.release = false; E.restart = false;
    A.released = false; A.releaseStrength = 0;

    // ---- smoothing of the step-like readings, toward the values in force over the frame that just passed
    const kEA = Math.exp(-dt / K.energyAttack), kER = Math.exp(-dt / K.energyRelease);
    const kP = Math.exp(-dt / K.paceTau), kPu = Math.exp(-dt / K.pulseTau), kF = Math.exp(-dt / K.flowTau);
    const kDA = Math.exp(-dt / K.densityAttack), kDR = Math.exp(-dt / K.densityRelease);
    const kIB = Math.exp(-dt / K.intensityBuild), kID = Math.exp(-dt / K.intensityDecay), kS = Math.exp(-dt / K.slopeTau);
    const kL = Math.exp(-dt / K.arcLevelTau);
    // (each ease is written out: a helper taking doubles could be called rather than inlined, and box them)
    m.pace = R.pace + (m.pace - R.pace) * kP;
    m.pulse = R.pulse + (m.pulse - R.pulse) * kPu;
    m.flow = R.flow + (m.flow - R.flow) * kF;
    m.density = R.density + (m.density - R.density) * (R.density > m.density ? kDA : kDR);

    // ---- gather: strikes, sounding voices, the wash
    lastCount = count;
    count = 0; wash = 0; pcMask = 0; N[LOUD_SUSTAIN] = 0;
    const src = state ? (state.sounding || state.pressed) : null;
    if (src && typeof src.forEach === "function") src.forEach(visit);
    let distinct = 0;
    const densityFrom = t - K.densityWindow;
    for (let i = 0; i < 128; i++) {
      wasThere[i] = isThere[i]; isThere[i] = 0;
      if (wasThere[i] === 1 || lastOnsetAt[i] > densityFrom) distinct++;
    }

    // ---- silence, restart, the chord's end
    if (count === 0) {
      if (!silent) { silent = true; N[SILENT_AT] = t; }
    } else {
      if (silent && (N[SILENT_AT] === NO_TIME || t - N[SILENT_AT] >= K.restartGap)) { E.restart = true; N[RESTART_AT] = t; }
      silent = false;
    }
    // ---- the strikes in the window: pace (a count), and the strike level (each strike's loudness fading with strikeTau),
    // as it stands now and averaged exactly over the frame that just passed (a strike that landed mid-frame counts for
    // the part of the frame it sounded), which is what energy eases toward
    let inWindow = 0, beats = 0, level = 0, levelAvg = 0, weight = 0, weightAvg = 0, presence = 0, presenceAvg = 0;
    const from = t - K.paceWindow, tPrev = t - dt, invTau = 1 / K.strikeTau;
    for (let i = 1; i <= ringN; i++) {
      const j = (ringHead - i + RING) % RING;
      const tj = ringT[j];
      if (tj <= from) break;
      inWindow++; beats += ringB[j];
      const v = ringV[j], b = t - tj;
      const eb = Math.exp(-(b < 0 ? 0 : b) * invTau);
      const ea = dt > 0 ? (Math.exp(-(tj > tPrev ? 0 : tPrev - tj) * invTau) - eb) * K.strikeTau / dt : eb;
      if (i === 1) { presence = eb; presenceAvg = ea; }
      level += v * eb; weight += eb;
      levelAvg += v * ea; weightAvg += ea;
    }
    // the window is no longer than the phrase is old: while it fills after a restart, the count is over the time since
    // the sound resumed (paceSpanMin at least)
    let span = t - N[RESTART_AT];
    span = span < K.paceSpanMin ? K.paceSpanMin : span > K.paceWindow ? K.paceWindow : span;
    const paceRaw = inWindow / span, beatsRaw = beats / span;
    // the strike level: the freshness-weighted mean loudness of the recent strikes, times the newest strike's own
    // freshness (so it fades with strikeTau from the last strike: energy starts falling the moment the playing stops)
    const struck = weight > 0 ? level / weight * presence : 0;
    const struckAvg = weightAvg > 0 ? levelAvg / weightAvg * presenceAvg : 0;
    // the beat rate (arousal's pace), eased like pace toward the rate in force over the past frame
    N[BEATS_NOW] = N[BEATS_RAW] + (N[BEATS_NOW] - N[BEATS_RAW]) * kP;
    N[BEATS_RAW] = beatsRaw;
    const heldNow = count > 0 ? N[LOUD_SUSTAIN] / count : 0;
    const heldAvg = N[HELD_PREV] * Math.exp(-0.5 * dt / K.sustainTau);  // the notes that sounded over the past frame, mid-frame
    N[HELD_PREV] = heldNow;
    const loud = struck > heldNow ? struck : heldNow, loudAvg = struckAvg > heldAvg ? struckAvg : heldAvg;

    // ---- energy: eased toward the reading in force over the past frame (the averaged level, last frame's busy)
    const rate = 1 - Math.exp(-paceRaw / K.energyPaceScale);
    let spread = fSpread / K.energySpreadFull; spread = spread > 1 ? 1 : spread < 0 ? 0 : spread;
    let washT = wash / K.energyWashFull; washT = washT > 1 ? 1 : washT;
    let busy = K.energyRateWeight * rate + K.energySpreadWeight * spread + K.energyWashWeight * washT;
    if (busy > 1) busy = 1;
    let energy = loud * (K.energyFloor + (1 - K.energyFloor) * busy) * K.energyGain;
    if (energy > 1) energy = 1;
    let energyAvg = loudAvg * (K.energyFloor + (1 - K.energyFloor) * N[BUSY_PREV]) * K.energyGain;
    if (energyAvg > 1) energyAvg = 1;
    N[BUSY_PREV] = busy;
    m.energy = energyAvg + (m.energy - energyAvg) * (energyAvg > m.energy ? kEA : kER);

    // ---- pulse: the regularity of the intervals between recent beats
    // The fit is redone only when a beat lands (the intervals do not change between beats) and held in N[PULSE_FIT].
    if (beatLanded) {
      beatLanded = false;
      let n = 0;
      for (let i = 1; i < beatN && n < K.pulseCount && n < IVLS; i++) {
        const d = beatT[(beatHead - i + BEATS) % BEATS] - beatT[(beatHead - i - 1 + BEATS) % BEATS];
        if (!(d > 0) || d > K.pulseMaxGap) break;
        ivl[n++] = d;
      }
      let fit = 0;
      if (n >= 2) {
        // every interval, its half and its third as the unit; the unit that snaps the intervals best wins
        let best = 1e9;
        for (let j = 0; j < n; j++) {
          for (let div = 1; div <= 3; div++) {
            const u = ivl[j] / div;
            if (u < K.pulseUnitMin) break;
            let sq = 0;
            for (let i = 0; i < n; i++) { const q = ivl[i] / u, e = q - Math.round(q); sq += e * e; }
            if (sq < best) best = sq;
          }
        }
        fit = 1 - Math.sqrt(best / n) / K.pulseJitterFull;
        fit = fit < 0 ? 0 : fit > 1 ? 1 : fit;
        if (n < K.pulseConfident) fit *= n / K.pulseConfident;  // two beats are no evidence of a grid
      }
      N[PULSE_FIT] = fit;
    }
    const pulse = beatN >= 3 && t - N[LAST_BEAT] <= K.pulseHold ? N[PULSE_FIT] : 0;
    const flow = beatN > 0 && t - N[LAST_BEAT] <= K.flowHold ? N[FLOW_ACC] : 0;
    let density = distinct / K.densityFull; if (density > 1) density = 1;

    // ---- intensity: the chord's colour scaled by the energy in the room is a smooth target, so the ease heads for the
    // midpoint of the last two targets; growth integrates the eased intensity by the trapezoid rule
    const colour = fTension > fLush ? fTension : fLush;
    let gain = m.energy / K.intensityEnergyFull; if (gain > 1) gain = 1;
    const intensity = colour * gain;
    const iMid = 0.5 * (R.intensity + intensity);
    m.intensity = iMid + (m.intensity - iMid) * (iMid > m.intensity ? kIB : kID);
    if (hasFrame && chordOn) N[GROWTH] += dt * 0.5 * (N[LAST_INTENSITY] + m.intensity) / K.growFull;
    if (N[GROWTH] > 1) N[GROWTH] = 1;
    N[LAST_INTENSITY] = m.intensity;

    // ---- the artifact. A chord begins on harmony-feel's chordChanged, or when sound returns under a chord name after a
    // rest (the same name coming back is no change to harmony-feel, but it is a new artifact here). It ends after endGap
    // of silence. The growth just integrated belongs to the chord that held over the past frame, so it goes with the
    // release before the new chord's growth starts from 0.
    const chord = state ? state.chord : undefined;
    const named = chord != null && typeof chord.name === "string" && chord.name !== "";
    const pcs = POP12[pcMask];
    const chordEnds = chordOn && silent && t - N[SILENT_AT] >= K.endGap;
    // Without a name (this frame, or the frame before: a name arriving over a different set is a change too) the
    // sounding pitch-class set is the chord: three or more pitch classes hold it, a different three or more change it.
    const begins = f.events.chordChanged === true
      || (!chordOn && count > 0 && (named || pcs >= 3))
      || (chordOn && (!named || !wasNamed) && pcs >= 3 && pcMask !== chordMask);
    wasNamed = named;
    if (begins || chordEnds) {
      if (chordOn && N[GROWTH] > K.releaseMin) { A.released = true; A.releaseStrength = N[GROWTH]; E.release = true; }
      N[GROWTH] = 0;
      let s = A.seed | 0;  // xorshift, kept under 2^30 so the field stays a small integer
      s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
      s &= 0x3FFFFFFF;
      A.seed = s === 0 ? 1 : s;
      chordOn = begins;
      chordMask = pcMask;
      N[CHORD_AT] = t;
    }
    A.growth = N[GROWTH];
    A.age = chordOn ? t - N[CHORD_AT] : 0;

    R.energy = energy; R.pace = paceRaw; R.pulse = pulse; R.flow = flow; R.density = density; R.intensity = intensity;

    // ---- the arc
    const drive = m.energy > m.intensity ? m.energy : m.intensity;
    const slopeNow = dt > 0 && hasFrame ? (drive - N[LAST_DRIVE]) / dt : 0;
    R.slope = hasFrame ? slopeNow + (R.slope - slopeNow) * kS : 0;
    N[LAST_DRIVE] = drive; R.drive = drive;
    if (N[ARC_AT] === NO_TIME) { N[ARC_AT] = t; N[ARC_LEVEL] = drive; }
    if (t - N[ARC_AT] >= K.arcHold) {
      const level = N[ARC_LEVEL];
      let next = arcState;
      if (drive < K.arcRest) next = 0;
      else if (arcState === 0 && drive < K.arcRest + K.arcBand) next = 0;
      else if (R.slope > K.arcRise && (arcState === 1 || drive >= level + K.arcStep)) next = 1;
      else if (R.slope < -K.arcFall && (arcState === 4 || drive <= level - K.arcStep)) next = 4;
      else if (arcState === 1) next = 2;
      else if (arcState === 2) next = t - N[PEAK_AT] >= K.arcPeakMax ? 3 : 2;
      else if (arcState === 4) next = R.slope > -K.arcFlat ? 3 : 4;  // the tail of a fade is still a fade
      else if (arcState === 0) next = 3;
      if (next !== arcState) {
        arcState = next; N[ARC_AT] = t; N[ARC_LEVEL] = drive; m.arc = ARCS[next];
        if (next === 1) E.build = true;
        if (next === 2) { E.peak = true; N[PEAK_AT] = t; }
      }
    }
    // the level: the crest while building or at the peak, the trough while releasing or resting, a slow follower while
    // sustaining
    if (arcState === 1 || arcState === 2) { if (drive > N[ARC_LEVEL]) N[ARC_LEVEL] = drive; }
    else if (arcState === 4 || arcState === 0) { if (drive < N[ARC_LEVEL]) N[ARC_LEVEL] = drive; }
    else N[ARC_LEVEL] = drive + (N[ARC_LEVEL] - drive) * kL;

    // ---- the mood
    // its inputs are smooth curves, eased with moodTau toward the midpoint of the last two readings (as intensity is)
    let vRaw = K.valenceBright * 2 * (fBright - 0.5) + K.valenceConsonance * 2 * (fCons - K.valenceConsonanceMid)
      - K.valenceTension * fTension;
    vRaw = vRaw < -1 ? -1 : vRaw > 1 ? 1 : vRaw;
    // the memory is no longer than the phrase is old: the time since the sound resumed, between moodTauMin and moodTau
    let tauM = t - N[RESTART_AT];
    tauM = tauM < K.moodTauMin ? K.moodTauMin : tauM > K.moodTau ? K.moodTau : tauM;
    const kM = Math.exp(-dt / tauM);
    if (hasFrame) {
      let mid = 0.5 * (N[LAST_V] + vRaw); N[MOOD_V] = mid + (N[MOOD_V] - mid) * kM;
      mid = 0.5 * (N[LAST_TENSION] + fTension); N[MOOD_TENSION] = mid + (N[MOOD_TENSION] - mid) * kM;
      mid = 0.5 * (N[LAST_LUSH] + fLush); N[MOOD_LUSH] = mid + (N[MOOD_LUSH] - mid) * kM;
      mid = 0.5 * (N[LAST_BRIGHT] + fBright); N[MOOD_BRIGHT] = mid + (N[MOOD_BRIGHT] - mid) * kM;
      mid = 0.5 * (N[LAST_OPEN] + fOpen); N[MOOD_OPEN] = mid + (N[MOOD_OPEN] - mid) * kM;
    }
    N[LAST_V] = vRaw; N[LAST_TENSION] = fTension; N[LAST_LUSH] = fLush; N[LAST_BRIGHT] = fBright;
    N[LAST_OPEN] = fOpen;
    const valence = N[MOOD_V];
    let beatsT = N[BEATS_NOW] / K.arousalPaceFull; if (beatsT > 1) beatsT = 1;
    let arousal = K.arousalEnergy * m.energy + K.arousalPace * beatsT + K.arousalDensity * m.density;
    arousal = arousal < 0 ? 0 : arousal > 1 ? 1 : arousal;
    MD.valence = valence; MD.arousal = arousal;
    const low = arousal < K.moodLowArousal, high = arousal >= K.moodHighArousal;
    const positive = valence >= K.moodPositive, negative = valence <= K.moodNegative;
    const neutral = valence < K.moodNeutral && valence > -K.moodNeutral;
    const tension = N[MOOD_TENSION], lushness = N[MOOD_LUSH], brightness = N[MOOD_BRIGHT], openness = N[MOOD_OPEN];
    const open = openness >= K.moodOpen || m.density >= K.moodDense;
    let label = 0, rule = 8;
    if (!low && tension >= K.moodTense) { label = 5; rule = 0; }
    else if (!low && positive && m.flow < K.moodDetached) { label = 4; rule = 1; }
    else if (high && positive && open) { label = 7; rule = 2; }
    else if (!low && positive && m.pulse >= K.moodSteady) { label = 4; rule = 3; }
    else if (!high && valence >= K.moodYearnFloor && valence <= -K.moodPositive && lushness >= K.moodLush) { label = 2; rule = 4; }
    // dark: clearly negative valence (and dim, or not low); or, at mid or high arousal, any negative valence with dim
    // brightness (a fortissimo minor riff sits near -0.17 with brightness 0.33: dark, never playful)
    else if ((negative && (brightness < K.moodDim || !low)) || (!low && valence < 0 && brightness < K.moodDim)) { label = 6; rule = 5; }
    else if (!high && neutral && m.pulse < K.moodRubato && f.dance.motion !== "static") { label = 3; rule = 6; }
    else if (!high && positive && m.flow >= K.moodLegato) { label = 1; rule = 7; }
    else if (low) { label = 0; rule = 8; }
    // mid or high arousal and nothing above fits: the nearest word, never calm
    else if (tension >= K.moodTenseSoft) { label = 5; rule = 9; }
    else if (positive || m.pulse >= K.moodSteady || m.flow < K.moodDetached) { label = 4; rule = 11; }
    else { label = high ? 5 : 3; rule = 12; }
    // level hysteresis: the label showing keeps against a candidate from a rule below its own, while its own rule still
    // fits with moodMargin to spare (the arousal bands strict); calm, the low-arousal fallback, never keeps
    if (label !== moodLabel && moodLabel !== 0 && rule > PRIORITY[moodLabel]) {
      const mg = K.moodMargin;
      let keep = false;
      if (moodLabel === 1) keep = !high && valence >= K.moodPositive - mg && m.flow >= K.moodLegato - mg;
      else if (moodLabel === 2) keep = !high && valence >= K.moodYearnFloor - mg && valence <= mg - K.moodPositive && lushness >= K.moodLush - mg;
      else if (moodLabel === 3) keep = !high && valence < K.moodNeutral + mg && valence > -K.moodNeutral - mg && m.pulse < K.moodRubato + mg && f.dance.motion !== "static";
      else if (moodLabel === 4) keep = !low && (valence >= K.moodPositive - mg || m.pulse >= K.moodSteady - mg || m.flow < K.moodDetached + mg);
      else if (moodLabel === 5) keep = !low && tension >= K.moodTenseSoft - mg;
      else if (moodLabel === 6) keep = (valence <= K.moodNegative + mg && (brightness < K.moodDim + mg || !low)) || (!low && valence < mg && brightness < K.moodDim + mg);
      else keep = high && valence >= K.moodPositive - mg && (openness >= K.moodOpen - mg || m.density >= K.moodDense - mg);
      if (keep) label = moodLabel;
    }
    if (label !== pendingLabel) { pendingLabel = label; N[MOOD_AT] = t; }
    // calm, the fallback, must win for twice moodHold: a word is not dropped for a gap in which nothing else quite fits
    if (pendingLabel !== moodLabel && t - N[MOOD_AT] >= (pendingLabel === 0 ? 2 * K.moodHold : K.moodHold)) { moodLabel = pendingLabel; MD.label = LABELS[moodLabel]; }

    hasFrame = true;
    return m;
  }

  reset();
  return { update, reset, frame: m, constants: Object.freeze(K) };
}
