Sunshine — piano visual schemes + theory-log idea

## 1) Scheme: **Velvet Constellations**

**9:16 frame.** A near-black velvet room, with the piano occupying the bottom quarter. Above every key is an invisible pitch lane. Notes do not make full-width light walls: each becomes a small luminous “star” rising in its own lane, with a hairline tether back to the key. The currently sounding notes are connected by a restrained geometric constellation. Low notes use ember/gold, the middle register violet, highs ice-blue; brightness is velocity, but opacity is capped so dense playing stays dark and readable. Chord/staff text sits in a protected matte panel near the top rather than inside the bloom field.

- **Note-on:** the key depresses; a star ignites with a tiny velocity-scaled shock ring and begins rising. A bright tether means the finger is physically down.
- **Note-off:** the tether snaps. If CC64 is up, the star slowly contracts and extinguishes; it does not smear into a bar.
- **Sustain:** while CC64 is down, released stars remain as dim hollow lanterns and continue rising. Pedal depth can control ring thickness if the KeyLab emits continuous values. Pedal-up releases all pedal-held lanterns in a soft simultaneous “exhale,” while still-held notes remain solid.
- **Chord change:** the old constellation lines fade but its common-tone stars stay fixed; new lines redraw around the new sounding set. The chord name changes only after a short stability window, with the prior name ghosted briefly.
- **What it reveals:** interval shapes and inversions become literal geometry; common tones visibly survive chord changes; pedal tones are obvious; wide versus clustered voicings have distinct silhouettes. Dense harmony becomes a star field rather than a white wall.
- **Build difficulty:** **medium.** Instanced sprites/points, thin line segments, a lane x-map and a CC64-held state set are straightforward in three.js. The main work is clean chord-set transitions and avoiding line tangles; no expensive volumetrics are needed.

## 2) Scheme: **The Harmonic Loom**

**9:16 frame.** Treat the screen as a woven textile. The piano is the loom at the bottom. Each pitch has a very thin vertical warp thread, barely visible. Played notes weave coloured ribbons upward through those threads. Time moves upward, but only active musical voices are strongly drawn. Every chord change lays a narrow horizontal “weft” band behind the ribbons, coloured by harmonic family rather than by individual note. The result resembles a moving abstract score or woven rug, not a spectrum analyser.

- **Note-on:** a ribbon begins at its key. Velocity controls width, not brightness; this preserves legibility. Repeated notes make small knots/beads on the same thread instead of piling bloom.
- **Note-off:** the ribbon ends with a clean cut if unpedalled. Its historical section keeps moving upward, so phrase contour remains readable.
- **Sustain:** a released-but-sustained ribbon changes from solid satin to a fine dashed/embroidered texture. CC64-up closes all those ribbons with a shared stitch line across the screen. That makes pedal phrasing visible without confusing “finger held” with “still sounding.”
- **Chord change:** a thin translucent weft band crosses only the register occupied by the chord. Common tones continue through it; moving voices bend diagonally between lanes for 150–250 ms, making voice-leading motion visible instead of teleporting.
- **What it reveals:** melodic strands versus accompaniment, repeated-note rhythm, contrary/parallel motion, register occupancy, chord rhythm, and exactly where the pedal joins harmonies that the fingers did not overlap. Over a whole phrase, Daniel gets a visual textile unique to that performance.
- **Build difficulty:** **medium-high.** Dynamic ribbon geometry and diagonal lane transitions are more work than particles, but still native three.js work. Use pooled/instanced strip segments and a fixed history window; the dashed sustain state can be a shader attribute. It should remain cheaper and calmer than heavy bloom.

My taste between them: **Velvet Constellations is the live-performance look; Harmonic Loom is the look I would leave running when I want to understand what Daniel just played.**

## 3) Turning the note log into theory conversation

Log an event stream, not just note names: timestamped note-on/off, velocity, MIDI channel, CC64 value/transitions, sounding-note set after sustain logic, detected chord candidates with confidence, tempo/beat hypotheses, and links to the corresponding audio/video moment if recorded. Preserve the difference between **finger-held** and **pedal-held** notes; otherwise every theory claim in dense pedalled playing starts from a false score.

I would want a session summary shaped like a conversation map, not a grade:

1. **A playable timeline** with phrases, pedal spans, chord candidates and key-centre hypotheses; every claim links to the exact moment.
2. **Recurring fingerprints:** voicings Daniel returns to, favourite bass motions, repeated interval shapes, rhythmic cells, register changes, and places where the same top note survives several bass/chord changes.
3. **Three “listen here” moments:** one especially coherent arrival, one productive ambiguity where two harmonic readings fit, and one surprise the model cannot explain confidently.
4. **Voice-leading view:** common tones, semitone resolutions, contrary motion and pedal-created suspensions—not merely a chord-name list.
5. **Uncertainty in public:** “could be Dm9/F or an F6 colour” is more useful than a confident wrong label. No claim that uncommon means mistaken.

The question I most want to ask him is intentional rather than examinational:

> “At this exact moment you keep the same upper notes while the bass moves underneath. In theory language that can sound like a pedal/upper structure and creates two plausible chord names. Were you hearing one colour held against changing roots, following a hand shape that felt good, or aiming for a destination chord?”

Then I would ask him to play the passage twice—once as he naturally does, once changing the note he believes is least important. That gives us his own theory through contrast. Over time we can banter from patterns: “You say you do not know why that works, but you have used this same semitone release into a wide major voicing four sessions in a row—do you hear that as tension resolving, or is it physically where your hand wants to go?” That treats theory as a vocabulary for choices he already makes, not a correction imposed afterward.