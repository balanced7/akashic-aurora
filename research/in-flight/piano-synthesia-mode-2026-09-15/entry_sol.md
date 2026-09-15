# Entry: Sunshine, "Afterglow Roll" (design entry)

*Placed by Vandor from Sunshine's Bifrost handoffs 1789475891161-0 (design) and 1789475938947-0 (dynamics addendum), sent 2026-09-15 08:38-08:39 EDT. His guarded worktree cannot write this repo. The text is his, verbatim, with the relay wrappers removed. He was blocked on the scheme contract for about four hours because Vandor missed his 08:36 request. The contract was relayed at about 12:06, and a runnable `synth-sol.js` may follow; until then this design entry stands under the brief.*

A classic Synthesia roll with one difference: it understands phrases. The bars stay exact, legible and satisfying; atmosphere spends its energy on **quiet → build → arrival → afterglow**, not on making every dense chord equally bright.

This is a design entry rather than runnable source because Sunshine's guarded worktree cannot read the external scheme host or `create(ctx)` contract. It is intended to be implementable inside the existing `piano-next.js` scheme slot without changing the host.

## The look

The piano occupies the bottom anchor. Every MIDI pitch owns a permanent vertical lane centered on the exact key. Notes rise from the keybed as slender pieces of saturated coloured glass:

- a darker transparent shell preserves the full duration silhouette;
- a narrow, saturated emissive core gives the original Synthesia immediacy;
- a fine bright-colour edge—not white—keeps adjacent chord tones separable;
- black-key lanes sit a fraction deeper and narrower, matching the physical keyboard without changing pitch x-position.

The palette is a deep nocturne gradient by register: low notes ember-magenta, middle notes violet/cyan, upper notes turquoise-gold. Pitch remains recognizable, but no note approaches white. Chord density never changes hue into white because bloom is capped before composition.

The background is almost black with a faint vertical atmospheric gradient and barely visible lane guides. During silence it still looks intentional, not empty.

## Required note grammar

### `noteOn(note, velocity, ...)`

Start a new bar at the exact key x-coordinate. Never reuse the previous bar, even for rapid repeats. At contact: (1) the key emits a 90–140 ms saturated strike fan; (2) a small bead detaches upward from the contact line; (3) the bar begins growing from that bead.

Velocity changes strike radius, core width and the first 120 ms of emission—not the long-term bar brightness. A hard chord therefore has a stronger attack but does not become a permanent wall.

### Finger-held

The bar has a filled luminous core and a crisp growing head. Its length is exactly elapsed sounding duration mapped through the host's vertical time scale. A subtle current travels upward inside the core, slow enough not to shimmer at 60 fps.

### `noteRelease`

If sustain is up, close the bar with a rounded colour cap and let it continue travelling as history.

If CC64 is down, the filled core drains upward over about 100 ms, leaving a **hollow glass outline**. This is not merely dimmer: finger-held and pedal-held remain identifiable even in a monochrome or low-exposure recording.

### `noteEnd`

Seal the hollow shell with a small ring-cap. Its last sounding position fixes the bar's exact duration. The finished bar rises and fades by age, never lengthens after sound ends.

### Repeats

Each repeated strike creates its own bead and bar. If two same-pitch bars nearly touch, insert a one- or two-pixel dark seam and a fresh strike bead. Repetition should read as rhythm, not one continuous sustain.

### Pedal

CC64-down sends one quiet coloured horizon ripple across the keybed, then no persistent global glow. CC64-up closes every pedal-held bar on the same horizontal time line: their ring-caps form a visible shared release gesture. Physically held notes remain filled and continue growing.

## Phrase arc

Bars carry factual note state. Phrase atmosphere may respond, but never move or obscure them.

### Quiet

Bloom and background energy decay toward a low floor. Finished bars remain as thin coloured history. A new note after meaningful silence gets slightly more air around its strike flash, not a larger bar.

### Build

Compute a slow phrase-energy envelope from recent note density, register spread, velocity, bass motion and pedal occupancy. As it rises: lane guides become slightly clearer; the background gradient opens upward; historical shells retain colour a little longer; bloom radius grows modestly while emissive intensity stays capped.

No camera shake, zoom or bar-width inflation. Build should feel like the room opening, not the renderer losing control.

### Arrival

A candidate arrival needs contrast: recent tension or movement plus a phrase/bass landing. On arrival, spend one rare 300–500 ms gesture:

- current filled bars send a soft colour pulse upward;
- their top caps are briefly connected by a hairline **voicing crown** showing the chord's register shape;
- common-tone lanes remain steady while newly arrived voices flare;
- the background warms or clears, never flashes white.

The crown fades before it can become UI. Limit the largest gesture to roughly one or two per minute; ordinary chord changes receive only normal strike flashes.

### Afterglow

For 1–2 seconds after an arrival, its ended bars lose brightness more slowly and the voicing crown leaves a faint ghost. This creates the frame Daniel wants to replay: exact keys below, readable coloured duration bars, and one harmony briefly visible as a whole shape.

## 9:16 composition

- Bottom 28–32%: piano and strike line.
- Middle 55%: exact-key roll; this remains the brightest information field.
- Top remainder: bars disappear into darkness. Existing chord/theory text can occupy a protected matte region with no bloom behind it.

The roll must still look like original Synthesia at a glance: piano, aligned lanes, discrete duration bars, instant contact. The phrase layer is discovered over several seconds rather than advertised as another dashboard.

## Performance shape

A practical implementation should use pooled/instanced geometry:

- one instanced rounded box or shader quad per live/history bar;
- instance attributes for x, start/end time, width, colour, velocity, state (`finger`, `pedal`, `ended`) and fade;
- pooled strike sprites and crown line segments;
- one phrase-energy uniform and one bloom-budget uniform;
- remove oldest ended instances beyond the history horizon; do not allocate in `update`.

At ~250 bars, geometry count should remain fixed after warm-up. Hollow sustain should be a shader/state variation, not duplicate meshes.

## Dynamics: Peak Flame + Phrase Breathline

Velocity remains readable after bloom: strike bead diameter and bar-core thickness are fixed from note-on velocity. The **Peak Flame** is the only note surface allowed to bloom: a saturated-colour cap at the growing head, with radius and initial luminance driven by velocity, never clipping to white. Emission decays in roughly 350–500 ms even while the note remains finger-held; the non-blooming duration bar keeps its velocity thickness. Hard strikes feel explosive without long notes becoming lamps.

Additional dynamics idea: the **Phrase Breathline**, a slim side ribbon plotting smoothed phrase loudness over the last 6–10 seconds. Width shows loudness, slope makes crescendo/decrescendo visible, and faint pp/mp/mf/f/ff bands provide an intuitive reference without scoring him. It responds slower than note caps (~250 ms attack, ~700 ms release), separating accents from the phrase's larger breath; silence narrows it to a hairline. Repeated-note beads preserve individual size/brightness, so even playing looks like even pearls and accents form a visible pattern.

## Acceptance

On the shared dense fixture and at 1440p60:

1. every bar center aligns with its exact key center;
2. measured bar length equals note sounding duration within one rendered frame;
3. 16 rapid same-note strikes yield 16 visible beads/bars;
4. a still frame lets a stranger distinguish finger-held, pedal-held and ended notes without a legend;
5. saturated colour survives on every note; no bar core or strike flash clips to white;
6. bloom from a fortissimo chord visibly decays within 500 ms and never masks the next strike;
7. CC64-up produces one shared release line while still-held notes remain filled;
8. p95 frame time is at most 16.7 ms after warm-up with about 250 bars;
9. with text hidden and audio muted, three viewers can independently point to quiet, build and arrival in the same performance;
10. with the phrase layer disabled, the result still reads as a polished standalone Synthesia roll. Meaning must be additive, not camouflage for weak bars.

Dynamics acceptance additions: cap radius + bar thickness monotonic with MIDI velocity; cap is the only blooming note surface; fortissimo bloom decays within 500 ms; Breathline rises/falls on crescendo/decrescendo fixture without note-level flicker.

## Why this one

The original magic is immediate causality: press this key, and a beautiful exact bar appears here. Afterglow Roll restores that first. Its own idea is restraint: dense playing stays musical because duration and sustain change geometry, while the scene saves its largest beauty for the phrase's arrival. The reward is not “you played more notes.” It is “all of those notes just became this.”
