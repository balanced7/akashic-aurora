// Practice exercises for the Studio drawer — arsenal/web/piano/practice/library.js  (ES module: plain data, no imports)
//
// The exercises Practice plays through the page's own cue player (practice/player.js): exact MIDI notes for every chord,
// so nothing is voiced by the server and nothing is recorded. The menu is FAMILIES -> groups -> exercises, and EXERCISES
// are stored in that same menu order, which is also the order auto-advance and next/prev walk.
//
//   FAMILIES   [{ id, title, blurb, groups: [{ id, title, blurb, exercises: [exerciseId, ...] }] }]
//   EXERCISES  [{ id, title, family, group, level, key, minor, bpm, beatsPerBar, chords, concept, listenFor, leftHand,
//                 variation, tags }]
//     level      "foundation" | "build" | "stretch"
//     key        a key name as nashville.js parseKey writes it ("E minor"); minor: "tonic" (a minor key numbers from its
//                own tonic, 1m)
//     chords     [{ name, number, bass: [midi], upper: [midi], beats, pedal }], notes bottom-up
//       name     the chord name the page's reader gives these notes in the exercise key (chordread.js, spelled by spell.js)
//       number   its Nashville number in nashville.js text form ("5^7"); draw it with formatNumber, never the raw "^"
//       bass     left hand, inside E1-E3 (MIDI 28-52); upper: right hand, inside A2-C6 (45-84); each hand within an octave
//       beats    how long the chord lasts; pedal: "change" (fresh pedal on this chord) or "hold" (let the one before ring)
//     concept, listenFor, leftHand, variation: plain words for the player at the piano
//
// tests/piano_practice_library.test.mjs checks every chord's name and number against the page's reader and nashville.js,
// the ranges and spans, the menu references, and every transposition -5..+6. Each chord's trailing comment gives its
// notes as letter names (left hand | right hand).

export const FAMILIES = [
  {
    id: "moving-bass",
    title: "Moving bass, still hands",
    blurb: "Your right hand holds its shape while the left hand walks. One step in the bass renames the whole chord.",
    groups: [
      {
        id: "inversions",
        title: "Walking through inversions",
        blurb: "A bass line that moves by step, using inversions so the harmony flows downhill.",
        exercises: ["stepwise-bass-g"],
      },
      {
        id: "chromatic-lines",
        title: "Falling chromatic lines",
        blurb: "Half steps in the bass under a chord that barely moves.",
        exercises: ["line-cliche-em", "lament-bass-am"],
      },
    ],
  },
  {
    id: "bass-decides-home",
    title: "The bass decides home",
    blurb: "The right hand plays notes from one scale; the bass decides which note feels like home.",
    groups: [
      {
        id: "same-hand",
        title: "Same hand, new bass",
        blurb: "Keep the right hand inside G major and let the bass change the mood.",
        exercises: ["lydian-bass-g", "three-homes"],
      },
      {
        id: "relative-minor",
        title: "Turning to the relative minor",
        blurb: "The same key signature, a new home, and the bass leads the way.",
        exercises: ["relative-minor-pivot"],
      },
    ],
  },
  {
    id: "same-root",
    title: "Same root, new mood",
    blurb: "Keep the root and change one note: the 3rd decides major or minor.",
    groups: [
      {
        id: "flips",
        title: "Major and minor flips",
        blurb: "Move only the 3rd and hear the light change.",
        exercises: ["flip-e", "a-minor-to-major"],
      },
      {
        id: "bright-endings",
        title: "Bright endings",
        blurb: "A minor passage that closes on a major chord.",
        exercises: ["picardy-d"],
      },
    ],
  },
  {
    id: "pedal-points",
    title: "Pedal points",
    blurb: "One bass note stays while the harmony above it moves.",
    groups: [
      {
        id: "held-bass",
        title: "Held bass, moving harmony",
        blurb: "Hold the bass and let the chords come and go above it.",
        exercises: ["tonic-pedal-g", "dominant-pedal-e"],
      },
      {
        id: "colour-pedal",
        title: "Colour over a pedal",
        blurb: "Chromatic colours above a bass that never moves.",
        exercises: ["chromatic-colour-e"],
      },
    ],
  },
  {
    id: "approach-tension",
    title: "Approach and tension",
    blurb: "How a chord leans into the next one: surprises, suspensions and half steps.",
    groups: [
      {
        id: "surprise-landings",
        title: "Surprise landings",
        blurb: "Set up an expectation, then land somewhere else.",
        exercises: ["deceptive-g"],
      },
      {
        id: "leaning-in",
        title: "Leaning into the bass",
        blurb: "Notes that lean on a neighbour before they land.",
        exercises: ["suspensions-g", "chromatic-approach-e"],
      },
    ],
  },
];

export const EXERCISES = [
  // ---------------------------------------------------------------------------------------- Moving bass, still hands
  {
    id: "stepwise-bass-g",
    title: "Step down through G major",
    family: "moving-bass",
    group: "inversions",
    level: "foundation",
    key: "G major",
    minor: "tonic",
    bpm: 72,
    beatsPerBar: 4,
    chords: [
      { name: "G",     number: "1",     bass: [43], upper: [67, 71, 74], beats: 4, pedal: "change" }, // G2 | G4 B4 D5
      { name: "D/F#",  number: "5/7",   bass: [42], upper: [66, 69, 74], beats: 4, pedal: "change" }, // F#2 | F#4 A4 D5
      { name: "Em",    number: "6m",    bass: [40], upper: [67, 71, 76], beats: 4, pedal: "change" }, // E2 | G4 B4 E5
      { name: "Em7/D", number: "6m7/5", bass: [38], upper: [67, 71, 76], beats: 4, pedal: "change" }, // D2 | G4 B4 E5
      { name: "Cmaj7", number: "4maj7", bass: [36], upper: [67, 71, 76], beats: 4, pedal: "change" }, // C2 | G4 B4 E5
      { name: "G/B",   number: "1/3",   bass: [35], upper: [67, 71, 74], beats: 4, pedal: "change" }, // B1 | G4 B4 D5
      { name: "Am7",   number: "2m7",   bass: [33], upper: [67, 72, 76], beats: 4, pedal: "change" }, // A1 | G4 C5 E5
      { name: "D",     number: "5",     bass: [38], upper: [66, 69, 74], beats: 4, pedal: "change" }, // D2 | F#4 A4 D5
    ],
    concept: "The bass walks down the G major scale one step at a time, from G all the way to A, then hops up to D to turn around. The right hand hardly moves: the G on top of your thumb stays in almost every chord. The E minor shape sits over E, then over D, then over C, where it quietly turns into Cmaj7. Inversions are what let the bass move by step while the harmony still makes sense.",
    listenFor: "The E minor shape over D: the D is the 7th of the chord, so it sounds unsettled and wants to keep falling. When C arrives under the very same right hand, the chord opens up into Cmaj7 without the right hand moving at all.",
    leftHand: "Single notes. Play G, F#, E with fingers 1, 2, 3, pass the thumb under for D, then C, B, A with 2, 3, 4, and hop back up to D. Change the pedal on every bass note: the line moves by step, so a held pedal would smear the steps together.",
    variation: "Add the octave below each bass note once the line feels easy. Or let the right hand add A (the 9th) on top of the G chords for a softer colour. Then move it to D major with the key picker: the numbers stay the same.",
    tags: ["inversions", "stepwise bass", "common tones", "major"],
  },
  {
    id: "line-cliche-em",
    title: "Line cliché under E minor",
    family: "moving-bass",
    group: "chromatic-lines",
    level: "build",
    key: "E minor",
    minor: "tonic",
    bpm: 66,
    beatsPerBar: 4,
    chords: [
      { name: "Em",          number: "1m",         bass: [40, 52], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // E2 E3 | G4 B4 E5
      { name: "Em(maj7)/D#", number: "1m(maj7)/7", bass: [39, 51], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // D#2 D#3 | G4 B4 E5
      { name: "Em7/D",       number: "1m7/b7",     bass: [38, 50], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // D2 D3 | G4 B4 E5
      { name: "C#m7b5",      number: "6ø7",        bass: [37, 49], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // C#2 C#3 | G4 B4 E5
      { name: "Cmaj7",       number: "b6maj7",     bass: [36, 48], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // C2 C3 | G4 B4 E5
      { name: "B7",          number: "5^7",        bass: [35, 47], upper: [69, 71, 75, 78], beats: 4, pedal: "change" }, // B1 B2 | A4 B4 D#5 F#5
      { name: "Em",          number: "1m",         bass: [40, 52], upper: [67, 71, 76],     beats: 8, pedal: "change" }, // E2 E3 | G4 B4 E5
    ],
    concept: "A line cliché is a chord that stays still while one voice slides down by half steps. Here the right hand holds an E minor chord and the bass does the sliding: E, D#, D, C#, C. Each step gives the same right hand a new name and a new mood, from dark to bittersweet to warm, before B7 pulls everything back home.",
    listenFor: "The D# is the tensest moment: a major 7th under the E on top. By the time the bass reaches C, the E minor shape has turned into a warm Cmaj7. Over C# the page names the chord C#m7b5 (C# half-diminished): the same four notes as E minor with a 6th, read from the bass.",
    leftHand: "Octaves, 5 on the bottom and 1 on top, sliding down by half steps without changing the hand shape. Change the pedal exactly as each new bass note sounds, or the half steps will blur. On B7 the right hand finally moves: G up to A, E down to D#, and F# added on top.",
    variation: "Reverse it: start on C and climb C, C#, D, D#, back to E. Or move the line into the right hand: keep E in the bass and let your right thumb play E, D#, D, C# under G and B.",
    tags: ["line cliché", "chromatic bass", "minor", "inversions"],
  },
  {
    id: "lament-bass-am",
    title: "Lament bass in A minor",
    family: "moving-bass",
    group: "chromatic-lines",
    level: "build",
    key: "A minor",
    minor: "tonic",
    bpm: 63,
    beatsPerBar: 4,
    chords: [
      { name: "Am",     number: "1m",     bass: [33, 45], upper: [69, 72, 76], beats: 4, pedal: "change" }, // A1 A2 | A4 C5 E5
      { name: "Am7/G",  number: "1m7/b7", bass: [31, 43], upper: [69, 72, 76], beats: 4, pedal: "change" }, // G1 G2 | A4 C5 E5
      { name: "F#m7b5", number: "6ø7",    bass: [30, 42], upper: [69, 72, 76], beats: 4, pedal: "change" }, // F#1 F#2 | A4 C5 E5
      { name: "Fmaj7",  number: "b6maj7", bass: [29, 41], upper: [69, 72, 76], beats: 4, pedal: "change" }, // F1 F2 | A4 C5 E5
      { name: "E7",     number: "5^7",    bass: [28, 40], upper: [68, 71, 74], beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 D5
      { name: "Am",     number: "1m",     bass: [33, 45], upper: [69, 72, 76], beats: 8, pedal: "change" }, // A1 A2 | A4 C5 E5
    ],
    concept: "The lament bass is one of the oldest sounds in music: a line falling from the home note down to the 5th. In A minor it walks A, G, F#, F, E. Hold an A minor chord in the right hand for the first four steps and let the bass tell the story. When the bass lands on E, the right hand finally steps down into E7, and E7 leads home.",
    listenFor: "The F# is bright and a little surprising; the F right after it darkens the colour again. Over F# the page names the chord F#m7b5, because those four notes read that way from the bass. On E7, every right-hand note steps down: A to G#, C to B, E to D.",
    leftHand: "Octaves, 5 and 1, stepping down A, G, F#, F, E. Change the pedal on every bass note. The last move, E up to A for the home chord, is a leap: move the whole hand and catch the pedal as the A sounds.",
    variation: "Slow down and give each bass note two bars. Or end on A major instead of A minor (C# instead of C) for a bright finish, as in Same root, new mood.",
    tags: ["lament bass", "chromatic bass", "minor", "dominant"],
  },
  // ------------------------------------------------------------------------------------------- The bass decides home
  {
    id: "lydian-bass-g",
    title: "The Lydian bass: C, D, E under G major",
    family: "bass-decides-home",
    group: "same-hand",
    level: "build",
    key: "G major",
    minor: "tonic",
    bpm: 69,
    beatsPerBar: 4,
    chords: [
      { name: "Cmaj7#11", number: "4maj7#11", bass: [36, 48], upper: [64, 66, 67, 71], beats: 4, pedal: "change" }, // C2 C3 | E4 F#4 G4 B4
      { name: "Dadd9",    number: "5add9",    bass: [38, 50], upper: [64, 66, 69, 74], beats: 4, pedal: "change" }, // D2 D3 | E4 F#4 A4 D5
      { name: "Em9",      number: "6m9",      bass: [40, 52], upper: [66, 67, 71, 74], beats: 8, pedal: "change" }, // E2 E3 | F#4 G4 B4 D5
    ],
    concept: "Every note in both hands comes from the G major scale, but G itself never sounds in the bass. Put C under those notes and you get the Lydian sound: the F# above C is the raised 4th that makes the chord float. Walk the bass up to D and the music leans forward; reach E and the same scale settles into E minor. Three bass notes, three moods, one scale.",
    listenFor: "The F# rubbing gently against G in the right hand over C: that is the Lydian colour, the #11. Over E the same F# becomes the 9th of Em9 and sounds calm instead of bright.",
    leftHand: "Octaves stepping up C, D, E. Change the pedal on each new bass note. Your right thumb stays on E or F# the whole time; only the upper fingers move, from G and B, to A and D, to G, B and D.",
    variation: "Stay on the C for two bars and improvise with G major scale notes over it: you are playing in C Lydian. Then do the same over D and over E, as in One scale, three homes.",
    tags: ["Lydian", "modes", "rising bass", "colour tones"],
  },
  {
    id: "three-homes",
    title: "One scale, three homes",
    family: "bass-decides-home",
    group: "same-hand",
    level: "stretch",
    key: "G major",
    minor: "tonic",
    bpm: 60,
    beatsPerBar: 4,
    chords: [
      { name: "Cmaj7#11",   number: "4maj7#11",   bass: [36, 48], upper: [66, 71, 72, 76], beats: 4, pedal: "change" }, // C2 C3 | F#4 B4 C5 E5
      { name: "G/C",        number: "1/4",        bass: [36, 48], upper: [67, 71, 74],     beats: 4, pedal: "hold" },   // C2 C3 | G4 B4 D5
      { name: "D13",        number: "5^13",       bass: [38, 50], upper: [66, 71, 72, 76], beats: 4, pedal: "change" }, // D2 D3 | F#4 B4 C5 E5
      { name: "G/D",        number: "1/5",        bass: [38, 50], upper: [67, 71, 74],     beats: 4, pedal: "hold" },   // D2 D3 | G4 B4 D5
      { name: "Cmaj7#11/E", number: "4maj7#11/6", bass: [40, 52], upper: [66, 71, 72, 76], beats: 4, pedal: "change" }, // E2 E3 | F#4 B4 C5 E5
      { name: "Em7",        number: "6m7",        bass: [40, 52], upper: [67, 71, 74],     beats: 4, pedal: "hold" },   // E2 E3 | G4 B4 D5
    ],
    concept: "Two right-hand shapes, both made only of G major notes, played over three different bass notes. Over C the scale sounds like C Lydian, bright and floating. Over D it sounds like D Mixolydian, relaxed and a little bluesy. Over E it sounds like E Aeolian, plain minor. The right hand never learns anything new: the bass alone decides which note feels like home.",
    listenFor: "Over D, the C in the right hand is the lowered 7th that gives D13 its easy, bluesy pull. Over E, the same shape puts C just above the 5th, the darkest note of E minor; the page names that chord Cmaj7#11/E. Let each home ring until you could sing its bass note as the resting place.",
    leftHand: "Octaves: C, then D, then E, two bars each. Change the pedal when the bass moves, and keep it down through the second chord of each pair so the two shapes melt into one sound.",
    variation: "Improvise a melody on G major scale notes over each bass for four bars at a time, ending your phrases on the bass note. Then play the three homes in a different order (E, C, D) and notice which one your ear still calls home.",
    tags: ["modes", "Lydian", "Mixolydian", "Aeolian"],
  },
  {
    id: "relative-minor-pivot",
    title: "Into E minor, led by the bass",
    family: "bass-decides-home",
    group: "relative-minor",
    level: "build",
    key: "G major",
    minor: "tonic",
    bpm: 66,
    beatsPerBar: 4,
    chords: [
      { name: "Gadd9",    number: "1add9",    bass: [31, 43], upper: [67, 69, 71, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 A4 B4 D5
      { name: "Cmaj7",    number: "4maj7",    bass: [36, 48], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // C2 C3 | G4 B4 E5
      { name: "D",        number: "5",        bass: [38, 50], upper: [66, 69, 74],     beats: 4, pedal: "change" }, // D2 D3 | F#4 A4 D5
      { name: "B7/D#",    number: "3^7/#5",   bass: [39, 51], upper: [66, 69, 71],     beats: 4, pedal: "change" }, // D#2 D#3 | F#4 A4 B4
      { name: "Em(add9)", number: "6m(add9)", bass: [40, 52], upper: [66, 67, 71],     beats: 4, pedal: "change" }, // E2 E3 | F#4 G4 B4
      { name: "Cmaj7#11", number: "4maj7#11", bass: [36, 48], upper: [66, 67, 71, 76], beats: 4, pedal: "change" }, // C2 C3 | F#4 G4 B4 E5
      { name: "Dadd9/F#", number: "5add9/7",  bass: [30, 42], upper: [69, 74, 76],     beats: 4, pedal: "change" }, // F#1 F#2 | A4 D5 E5
      { name: "G",        number: "1",        bass: [31, 43], upper: [67, 71, 74],     beats: 4, pedal: "change" }, // G1 G2 | G4 B4 D5
    ],
    concept: "G major and E minor share every note, so the move between them is made by the bass. After G, C and D, the bass does not fall back to G: it rises D, D#, E. That D# is the leading tone of E minor, and B7 over D# makes the new home unmistakable. Then the bass drops to C, falls to F# and steps up to G, and G major is home again. The numbers stay in G major, so E minor shows as 6m: the relative minor.",
    listenFor: "The moment the bass goes from D to D#: nothing in the key signature has changed, but your ear turns towards E. On the way back, the F# under the D chord leads just as strongly up to G.",
    leftHand: "Octaves. The steps that matter are D, D#, E (half steps up) and F# up to G at the end. Change the pedal on every bass note. For B7 over D# the right hand only needs F#, A and B: let the bass carry the D#.",
    variation: "Stay in E minor longer by repeating the D# and E bars before moving on. Or turn the other way: from E minor, let the bass fall E, D, C, B and hear how quickly G major takes over.",
    tags: ["relative minor", "pivot", "leading tone", "secondary dominant"],
  },
  // --------------------------------------------------------------------------------------------- Same root, new mood
  {
    id: "flip-e",
    title: "E minor, E major",
    family: "same-root",
    group: "flips",
    level: "foundation",
    key: "E minor",
    minor: "tonic",
    bpm: 72,
    beatsPerBar: 4,
    chords: [
      { name: "Em", number: "1m",  bass: [40, 52], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // E2 E3 | G4 B4 E5
      { name: "E",  number: "1",   bass: [40, 52], upper: [68, 71, 76],     beats: 4, pedal: "change" }, // E2 E3 | G#4 B4 E5
      { name: "Em", number: "1m",  bass: [40, 52], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // E2 E3 | G4 B4 E5
      { name: "E7", number: "1^7", bass: [40, 52], upper: [68, 71, 74, 76], beats: 4, pedal: "change" }, // E2 E3 | G#4 B4 D5 E5
      { name: "Am", number: "4m",  bass: [33, 45], upper: [69, 72, 76],     beats: 4, pedal: "change" }, // A1 A2 | A4 C5 E5
      { name: "B7", number: "5^7", bass: [35, 47], upper: [69, 71, 75, 78], beats: 4, pedal: "change" }, // B1 B2 | A4 B4 D#5 F#5
      { name: "Em", number: "1m",  bass: [40, 52], upper: [67, 71, 76],     beats: 8, pedal: "change" }, // E2 E3 | G4 B4 E5
    ],
    concept: "The only difference between E minor and E major is one note: G or G#. The root stays, the 5th stays, and the mood flips from shadow to light. The second time, the major chord also grows a 7th (D) and stops being a home: E7 wants to fall to A minor, and B7 brings you back to E minor.",
    listenFor: "Your thumb moving from G to G# and nothing else changing. E major inside an E minor passage sounds like a window suddenly opening; E7 immediately asks to go somewhere.",
    leftHand: "Hold E in octaves for the first four chords, then A, then B, then E. Change the pedal with every chord, even while the bass stays on E, so G and G# never sound together.",
    variation: "Flip on every beat instead of every bar. Then try the same trick on A minor and B minor: move only the 3rd.",
    tags: ["parallel major", "3rd", "minor", "major", "dominant"],
  },
  {
    id: "a-minor-to-major",
    title: "A minor becomes A major",
    family: "same-root",
    group: "flips",
    level: "build",
    key: "A minor",
    minor: "tonic",
    bpm: 76,
    beatsPerBar: 4,
    chords: [
      { name: "Am", number: "1m",  bass: [33, 45], upper: [69, 72, 76],     beats: 4, pedal: "change" }, // A1 A2 | A4 C5 E5
      { name: "Dm", number: "4m",  bass: [38, 50], upper: [69, 74, 77],     beats: 4, pedal: "change" }, // D2 D3 | A4 D5 F5
      { name: "E7", number: "5^7", bass: [40, 52], upper: [68, 71, 74, 76], beats: 4, pedal: "change" }, // E2 E3 | G#4 B4 D5 E5
      { name: "Am", number: "1m",  bass: [33, 45], upper: [69, 72, 76],     beats: 4, pedal: "change" }, // A1 A2 | A4 C5 E5
      { name: "A",  number: "1",   bass: [33, 45], upper: [69, 73, 76],     beats: 4, pedal: "change" }, // A1 A2 | A4 C#5 E5
      { name: "D",  number: "4",   bass: [38, 50], upper: [69, 74, 78],     beats: 4, pedal: "change" }, // D2 D3 | A4 D5 F#5
      { name: "E7", number: "5^7", bass: [40, 52], upper: [68, 71, 74, 76], beats: 4, pedal: "change" }, // E2 E3 | G#4 B4 D5 E5
      { name: "A",  number: "1",   bass: [33, 45], upper: [69, 73, 76],     beats: 8, pedal: "change" }, // A1 A2 | A4 C#5 E5
    ],
    concept: "Play a short phrase in A minor, then play it again with every C raised to C# and every F raised to F#. The bass line and the E7 in the middle stay exactly the same; the phrase that sounded serious now sounds hopeful. Composers use this switch to lift a piece near its end.",
    listenFor: "E7 is identical both times, but it leads to a different world: first to A minor, then to A major. The C# in the middle of the fifth chord is the moment the light comes on.",
    leftHand: "Octaves: A, D, E, A, then the same again. Change the pedal on every chord. The bass never changes between the minor and major halves, so let the right hand carry the story.",
    variation: "Alternate minor and major on the same root, one bar each: A minor then A major, D minor then D major. Or start in A major and fall back into A minor for the opposite effect.",
    tags: ["parallel major", "modal switch", "dominant", "minor"],
  },
  {
    id: "picardy-d",
    title: "A Picardy ending in D",
    family: "same-root",
    group: "bright-endings",
    level: "build",
    key: "D minor",
    minor: "tonic",
    bpm: 66,
    beatsPerBar: 4,
    chords: [
      { name: "Dm",     number: "1m",     bass: [38, 50], upper: [65, 69, 74], beats: 4, pedal: "change" }, // D2 D3 | F4 A4 D5
      { name: "Bbmaj7", number: "b6maj7", bass: [34, 46], upper: [65, 69, 74], beats: 4, pedal: "change" }, // Bb1 Bb2 | F4 A4 D5
      { name: "Gm7",    number: "4m7",    bass: [31, 43], upper: [65, 70, 74], beats: 4, pedal: "change" }, // G1 G2 | F4 Bb4 D5
      { name: "A7",     number: "5^7",    bass: [33, 45], upper: [64, 67, 73], beats: 4, pedal: "change" }, // A1 A2 | E4 G4 C#5
      { name: "Dm",     number: "1m",     bass: [38, 50], upper: [65, 69, 74], beats: 4, pedal: "change" }, // D2 D3 | F4 A4 D5
      { name: "Gm",     number: "4m",     bass: [31, 43], upper: [67, 70, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 Bb4 D5
      { name: "A7",     number: "5^7",    bass: [33, 45], upper: [67, 73, 76], beats: 4, pedal: "change" }, // A1 A2 | G4 C#5 E5
      { name: "D",      number: "1",      bass: [38, 50], upper: [66, 69, 74], beats: 8, pedal: "change" }, // D2 D3 | F#4 A4 D5
    ],
    concept: "A Picardy third is a major chord at the end of a minor passage. Everything here is in D minor until the very last chord, where F becomes F#. The first time, A7 lands on D minor as expected; the second time, the same move lands on D major, like light breaking through at the end.",
    listenFor: "Compare the two arrivals from A7. The first time the right hand steps from E up to F (D minor); the second time from G down to F# (D major). The C# in A7 already hints at the brightness, and the Picardy ending keeps it.",
    leftHand: "Octaves: D, Bb, G, A, D, G, A, D. Move the hand as one piece down to Bb and G, keeping it relaxed. Change the pedal on every chord and let the final D major ring for two bars.",
    variation: "Move the whole passage to A minor or E minor with the key picker. For an even softer ending, add E (the 9th) on top of the final D major chord.",
    tags: ["Picardy third", "cadence", "minor", "ending"],
  },
  // ---------------------------------------------------------------------------------------------------- Pedal points
  {
    id: "tonic-pedal-g",
    title: "Home note in the bass: G",
    family: "pedal-points",
    group: "held-bass",
    level: "foundation",
    key: "G major",
    minor: "tonic",
    bpm: 72,
    beatsPerBar: 4,
    chords: [
      { name: "G",   number: "1",   bass: [31, 43], upper: [67, 71, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 B4 D5
      { name: "C/G", number: "4/1", bass: [31, 43], upper: [67, 72, 76], beats: 4, pedal: "change" }, // G1 G2 | G4 C5 E5
      { name: "D/G", number: "5/1", bass: [31, 43], upper: [66, 69, 74], beats: 4, pedal: "change" }, // G1 G2 | F#4 A4 D5
      { name: "G",   number: "1",   bass: [31, 43], upper: [67, 71, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 B4 D5
    ],
    concept: "A tonic pedal holds the home note in the bass while the chords above it leave home and come back. G stays under C and under D, so the music moves without ever really leaving. It is the sound of a final amen, an organ holding its lowest note, or a guitar strumming over an open string.",
    listenFor: "C over G sounds gentle and settled. D over G rubs a little: F# and A against the G below. That rub is what makes the return to plain G feel like a sigh of relief.",
    leftHand: "Press the G octave once and keep the keys down with your fingers for all four chords. Change the damper pedal on every right-hand chord: the harmonies stay clean while the bass keeps sounding under your fingers.",
    variation: "Add an A minor chord (A, C, E) over the G before D. Or turn the idea upside down: keep a G on top of every right-hand chord while the bass moves G, C, D, G.",
    tags: ["pedal point", "tonic pedal", "major", "finger pedal"],
  },
  {
    id: "dominant-pedal-e",
    title: "Building over a held E",
    family: "pedal-points",
    group: "held-bass",
    level: "build",
    key: "A minor",
    minor: "tonic",
    bpm: 63,
    beatsPerBar: 4,
    chords: [
      { name: "Esus4", number: "5sus4", bass: [28, 40], upper: [69, 71, 76],     beats: 4, pedal: "change" }, // E1 E2 | A4 B4 E5
      { name: "E",     number: "5",     bass: [28, 40], upper: [68, 71, 76],     beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 E5
      { name: "Am/E",  number: "1m/5",  bass: [28, 40], upper: [69, 72, 76],     beats: 4, pedal: "change" }, // E1 E2 | A4 C5 E5
      { name: "E7",    number: "5^7",   bass: [28, 40], upper: [68, 71, 74],     beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 D5
      { name: "E7b9",  number: "5^7b9", bass: [28, 40], upper: [68, 71, 74, 77], beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 D5 F5
      { name: "Am",    number: "1m",    bass: [33, 45], upper: [69, 72, 76],     beats: 8, pedal: "change" }, // A1 A2 | A4 C5 E5
    ],
    concept: "A dominant pedal holds the 5th of the key (E, in A minor) and piles up tension above it. Each chord asks a stronger question: a suspended 4th, plain E major, A minor over E that still refuses to rest, E7, and finally E7 with a flat 9 (F on top). Only when the bass finally moves to A does the music answer.",
    listenFor: "A minor over E does not feel like home, even though it is the home chord: the E underneath keeps it waiting. The F at the top of E7b9 is the most painful note, and it falls a half step to E when A minor arrives.",
    leftHand: "Hold the low E octave down for five chords, then move up to A for the answer. Change the pedal on every chord above the pedal note, and keep the E keys down so the bass never stops.",
    variation: "Give each chord two bars so the tension builds more slowly. Or play the right-hand chords as slow broken chords over the held E.",
    tags: ["pedal point", "dominant pedal", "minor", "tension"],
  },
  {
    id: "chromatic-colour-e",
    title: "Chromatic colour over E",
    family: "pedal-points",
    group: "colour-pedal",
    level: "stretch",
    key: "E major",
    minor: "tonic",
    bpm: 56,
    beatsPerBar: 4,
    chords: [
      { name: "E",         number: "1",          bass: [28, 40], upper: [68, 71, 76],     beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 E5
      { name: "Cmaj7#5/E", number: "b6maj7#5/1", bass: [28, 40], upper: [68, 71, 72, 76], beats: 4, pedal: "hold" },   // E1 E2 | G#4 B4 C5 E5
      { name: "E7b13",     number: "1^7b13",     bass: [28, 40], upper: [68, 71, 72, 74], beats: 4, pedal: "change" }, // E1 E2 | G#4 B4 C5 D5
      { name: "Eadd11",    number: "1add11",     bass: [28, 40], upper: [68, 69, 71, 76], beats: 4, pedal: "change" }, // E1 E2 | G#4 A4 B4 E5
      { name: "E",         number: "1",          bass: [28, 40], upper: [68, 71, 76],     beats: 8, pedal: "change" }, // E1 E2 | G#4 B4 E5
    ],
    concept: "The bass stays on E and the right hand adds one foreign note at a time. C, a flat 6th above E, makes the E major chord dreamy and slightly eerie; the page reads those notes as Cmaj7#5 over E. Add D and the chord becomes E7b13, a dominant with a dark edge. Then A, the 11th, replaces the tension with an open, hymn-like colour before plain E major returns.",
    listenFor: "The top voice goes E, E, D, E; the voice under it goes B, C, C, B. Each colour arrives by a half step or a whole step, and the E in the bass makes every one of them sound like a shade of E rather than a new chord.",
    leftHand: "Keep the E octave down under your fingers the whole time. Change the pedal on every chord except the second, where you keep it down and simply add the C. Play the right hand slowly and listen to each new note arrive.",
    variation: "Play the right hand as a slow broken chord, lowest note first, so each colour note is heard on its own. Then move the whole exercise to A with the key picker and hear the same colours over an A pedal.",
    tags: ["pedal point", "chromatic", "colour tones", "b13"],
  },
  // -------------------------------------------------------------------------------------------- Approach and tension
  {
    id: "deceptive-g",
    title: "The deceptive landing in G",
    family: "approach-tension",
    group: "surprise-landings",
    level: "foundation",
    key: "G major",
    minor: "tonic",
    bpm: 80,
    beatsPerBar: 4,
    chords: [
      { name: "G",  number: "1",  bass: [31, 43], upper: [67, 71, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 B4 D5
      { name: "C",  number: "4",  bass: [36, 48], upper: [67, 72, 76], beats: 4, pedal: "change" }, // C2 C3 | G4 C5 E5
      { name: "D",  number: "5",  bass: [38, 50], upper: [66, 69, 74], beats: 4, pedal: "change" }, // D2 D3 | F#4 A4 D5
      { name: "G",  number: "1",  bass: [31, 43], upper: [67, 71, 74], beats: 4, pedal: "change" }, // G1 G2 | G4 B4 D5
      { name: "C",  number: "4",  bass: [36, 48], upper: [67, 72, 76], beats: 4, pedal: "change" }, // C2 C3 | G4 C5 E5
      { name: "D",  number: "5",  bass: [38, 50], upper: [66, 69, 74], beats: 4, pedal: "change" }, // D2 D3 | F#4 A4 D5
      { name: "Em", number: "6m", bass: [40, 52], upper: [67, 71, 76], beats: 8, pedal: "change" }, // E2 E3 | G4 B4 E5
    ],
    concept: "D major wants to go to G: it is the strongest pull in the key. The first time through, it does. The second time, the bass steps up from D to E instead, and E minor answers where G was expected. The ear accepts it because E minor shares two notes with G major (G and B), but the phrase is left open, asking to go on.",
    listenFor: "The bass: G, C, D, then G the first time and E the second. One note in the left hand makes the whole surprise.",
    leftHand: "Octaves: G, C, D, G, then C, D, E. The step from D up to E is the surprise, so play it as smoothly as the rest. Change the pedal on every chord.",
    variation: "Add C to the D chord (D7) before E minor to make the pull, and the surprise, stronger. Then carry on from E minor with C, D and G to give the phrase the ending it was denied.",
    tags: ["deceptive cadence", "cadence", "major"],
  },
  {
    id: "suspensions-g",
    title: "Suspensions over a stepping bass",
    family: "approach-tension",
    group: "leaning-in",
    level: "build",
    key: "G major",
    minor: "tonic",
    bpm: 72,
    beatsPerBar: 4,
    chords: [
      { name: "Am7",   number: "2m7",   bass: [33, 45], upper: [64, 67, 72], beats: 4, pedal: "change" }, // A1 A2 | E4 G4 C5
      { name: "G/B",   number: "1/3",   bass: [35, 47], upper: [62, 67, 71], beats: 4, pedal: "change" }, // B1 B2 | D4 G4 B4
      { name: "C",     number: "4",     bass: [36, 48], upper: [64, 67, 72], beats: 4, pedal: "change" }, // C2 C3 | E4 G4 C5
      { name: "Dsus4", number: "5sus4", bass: [38, 50], upper: [62, 67, 69], beats: 2, pedal: "change" }, // D2 D3 | D4 G4 A4
      { name: "D",     number: "5",     bass: [38, 50], upper: [62, 66, 69], beats: 2, pedal: "change" }, // D2 D3 | D4 F#4 A4
      { name: "Esus4", number: "6sus4", bass: [40, 52], upper: [64, 69, 71], beats: 2, pedal: "change" }, // E2 E3 | E4 A4 B4
      { name: "Em",    number: "6m",    bass: [40, 52], upper: [64, 67, 71], beats: 6, pedal: "change" }, // E2 E3 | E4 G4 B4
    ],
    concept: "A suspension holds a note over from one chord into the next, where it clashes, and then lets it fall one step onto a chord tone. The bass climbs A, B, C, D, E. On D, the G from the C chord hangs on (Dsus4) before falling to F#. On E, the A from the D chord hangs on (Esus4) before falling to G. Both the tension and its release happen inside your right hand.",
    listenFor: "The 4th falling to the 3rd: G to F# over D, then A to G over E. Try singing the falling note as you play it.",
    leftHand: "Octaves stepping up A, B, C, D, E. Change the pedal on every chord, including each resolution, so the suspended note and the note it falls to never sound together.",
    variation: "Delay each resolution: hold the sus chord for a full bar before letting the note fall. Or add a suspension over C as well: C with F instead of E, then F falling to E.",
    tags: ["suspension", "rising bass", "major"],
  },
  {
    id: "chromatic-approach-e",
    title: "Half steps into E",
    family: "approach-tension",
    group: "leaning-in",
    level: "stretch",
    key: "E minor",
    minor: "tonic",
    bpm: 63,
    beatsPerBar: 4,
    chords: [
      { name: "Cmaj7",    number: "b6maj7",    bass: [36, 48], upper: [67, 71, 76],     beats: 4, pedal: "change" }, // C2 C3 | G4 B4 E5
      { name: "B7/D#",    number: "5^7/7",     bass: [39, 51], upper: [66, 69, 71],     beats: 4, pedal: "change" }, // D#2 D#3 | F#4 A4 B4
      { name: "Em9",      number: "1m9",       bass: [40, 52], upper: [67, 71, 74, 78], beats: 4, pedal: "change" }, // E2 E3 | G4 B4 D5 F#5
      { name: "Ebmaj7",   number: "7maj7",     bass: [39, 51], upper: [67, 70, 74],     beats: 4, pedal: "change" }, // Eb2 Eb3 | G4 Bb4 D5
      { name: "Em7",      number: "1m7",       bass: [40, 52], upper: [67, 71, 74],     beats: 4, pedal: "change" }, // E2 E3 | G4 B4 D5
      { name: "Fmaj7#11", number: "b2maj7#11", bass: [29, 41], upper: [69, 71, 72, 76], beats: 4, pedal: "change" }, // F1 F2 | A4 B4 C5 E5
      { name: "Em",       number: "1m",        bass: [28, 40], upper: [67, 71, 76],     beats: 8, pedal: "change" }, // E1 E2 | G4 B4 E5
    ],
    concept: "Three ways into the same E. From below as a leading tone: D# is the 3rd of B7, and it rises to E. From below as a slide: Ebmaj7 glides into E minor by moving the bass and one right-hand note up a half step (Bb to B). From above: F sinks to E, the dark Phrygian approach. One destination, three kinds of arrival.",
    listenFor: "B7 over D# is a question with an obvious answer. Ebmaj7 to Em7 is a smooth gear change where only Eb and Bb move. Fmaj7#11 falling into E minor sounds Spanish or cinematic. The page numbers Ebmaj7 as 7maj7: in E minor the note a half step below E is counted as the leading tone, D#.",
    leftHand: "Octaves: C, D#, E, Eb, E, then drop down an octave for F and the final E. Every approach note is a half step from E, so the hand barely moves. Change the pedal on every bass note; half steps blur faster than anything else.",
    variation: "Shorten the approach chords to two beats and lengthen the E chords to six, so the approaches sound like quick leans. Then move the exercise to A minor with the key picker.",
    tags: ["chromatic approach", "leading tone", "Phrygian", "minor"],
  },
];
