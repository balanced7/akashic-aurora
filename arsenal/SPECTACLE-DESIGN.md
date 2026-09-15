# A visual language for playing

The piano is the source of a living environment. A strike adds momentum; it never
rewinds a motion already in flight. The first draft made repeated notes erase their
predecessors and made dynamics mostly a change of brightness. This pass changes the
shape, scale, spatial reach and timing of the response as well.

## Moonwater implementation direction

The first built realm pairs a moonlit valley with a reflective lake and a mineral
piano edged in optical glass. A small moon and the distant shoreline establish scale;
the player and the inner voices remain the foreground subject. The landscape is
procedural and intentionally restrained. Common tones keep their colour and phase;
moving voices bend between pitches. Golden-ratio starting phases separate simultaneous
parts without turning them into synchronized copies of one animation.

The surface-wave gradient is shared by water distortion, note motion, firefly
displacement and fog drift. Note positions drive local illumination across those
materials. This is a coherent artistic approximation, with planar reflections and
layered fog rather than a claim of physically complete fluid transport. Strong playing
changes the dimensions and movement of a gesture as well as its radiance. Quiet
playing retains a complete, legible shape. The fifths circle is an illuminated inlay
under the water; it is musical information embedded in the environment.

Letterforms have their own hierarchy: a large light root, raised smaller extensions,
a quiet Nashville/key line, and separate note/octave figures on the parts. A chromatic
cluster keeps its individual spellings while the heading reports the note count.
Full staff mode retains the established theory view; pure performance hides text.
The implementation and measured limits are documented in `SPECTACLE.md`.

## Research translated into choices

[Animation principles](https://learn.microsoft.com/en-us/windows/win32/lwef/animation-principles)
describe timing, arcs, overlapping action and follow-through as ways to communicate
weight. Here the key contact responds immediately, the gesture opens over a fraction
of a second, and the environment follows more slowly. A release removes the source
of force while the accumulated movement continues. Live music cannot be anticipated
without prediction, so decorative anticipation must not delay the note's response.

[Palmer, Schloss, Xu and Prado-Leon](https://palmerlab.berkeley.edu/pdf/PalmerSchlossXuPrado-Leon(2013).pdf)
found music-colour associations mediated by emotion in their US/Mexican samples of
classical orchestral music. This supports exploring coordinated lightness, saturation
and movement, not assigning a universal emotion to every chord. Our colours are an
artistic interpretation: harmony shifts accent relationships gradually; performance
energy governs spatial reach and contrast. The player can choose a world explicitly.

[GPU Gems' fluid chapter](https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu)
describes maintaining simulation state in textures and adding forces to it. That is
the useful distinction from replaying an animation clip on every note. The water here
uses a damped height/velocity wave field with additive impulses; the airborne particles
retain position and velocity in a flowing field. This is not a full incompressible
three-dimensional fluid solver.

[Effective Water Simulation](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
separates broad geometric waves from finer surface detail. Our feedback field supplies
the shared ripples; gradients supply moving highlights. Ripples must affect the water
surface, rather than only appearing as isolated glowing circle decals.

## Grammar

| Musical gesture | Shape and motion | Attention |
| --- | --- | --- |
| Soft attack | Narrow pearl/silk gesture; a small travelling ripple | Crisp local detail and a visible luminous path, even at low velocity |
| Forceful attack | Faster, taller spray; wider swept ribbons; strong surface impulse | More area and contrast, with a restrained bright core |
| Gentle sustained chord | Slowly opening, intertwined veils and orbiting motes | A clear middle-distance focal form; scenery recedes |
| Forceful chord | Broad crown of moving light, expanding waves and displaced particles | Brief architectural scale, followed by a long, legible settling motion |
| High dry staccato | Short crystalline fragments with ballistic fall | Small, precise accents |
| Pedalled staccato | Suspended flecks with a longer drift | Continuity between gestures; lifting the pedal releases the suspended field |
| Repetition | Continuous per-key flow, additive momentum and accumulating waves | Rhythm becomes a pattern in space; old particles continue |
| Silence | Motion settles and the focal form fades | Rest has room; no automatic visual climax |

## World vocabulary

| World | Palette roles | Material and gesture vocabulary |
| --- | --- | --- |
| Moonlit lake | Ink blue ground, jade body, pearl/champagne accent | Silk, pearls, liquid rings, refracted highlights |
| Ember sanctuary | Aubergine shadow, copper body, pale-gold core | Rising smoke curls, sparks and broad flame-like veils |
| Velvet nebula | Violet-black ground, indigo/lilac body, rose-silver stars | Orbital motion, comet glints and spiral filaments |
| Winter mountains | Slate shadow, glacial blue body, ivory accent | Faceted snow crystals, slow suspended movement and sharp frost edges |
| Rainforest at midnight | Blue-black ground, verdigris body, celadon accent | Fine falling streaks, restrained firefly glints and spreading water |
| City of light | Obsidian ground, cyan/violet structure, warm rose accents | Persistent sprung towers, rectilinear flecks and travelling light bands |

The quiet case is a complete composition, not the loud case made almost invisible.
The keyboard remains readable. The foreground strike, middle-distance gesture and
background atmosphere have different speeds. Palette transitions take seconds;
individual strikes can have immediate warm/cool accents within that palette.

## Games as art-direction references

These are design readings and proposed translations, not claims about the games'
internal rendering algorithms. Their original artwork is not included in the app.

| Reference | What to study | Translation to the piano |
| --- | --- | --- |
| [Journey](https://thatgamecompany.com/journey/) | Simple silhouettes, distant destination, warm light and vast quiet space | One clear focal gesture; use atmosphere to separate foreground keys, moving voices and distant scenery |
| [ABZÛ](https://giantsquidstudios.com/ABZU-Concept-Art) | Choreographed movement through depth and a coherent underwater palette | Particles travel through a shared environment; adjacent voices move as an ensemble |
| [Ori and the Will of the Wisps](https://www.orithegame.com/wallpaper_category/ori-and-the-will-of-the-wisps/) | Luminous subjects against layered, painterly darkness | A quiet note still has a crisp core; local light reveals mist and nearby forms |
| [GRIS](https://www.devolverdigital.com/games/gris) | Restrained shapes and colour changes across an emotional journey | Palette changes develop over phrases; preserve silhouette and space during quiet passages |
| [Control](https://www.adobe.com/products/substance3d/magazine/control-how-one-senior-environment-artist-created-entire-brutalist-material-library.html) | Repeated geometry, material variation and deliberate lighting | City notes become clear structural columns; angular light connections show the voicing |
| [Sword of the Sea](https://giantsquidstudios.com/Sword-of-the-Sea-Announcement) | Undulating landscapes and fluid travel | Let broader terrain movement express a phrase's accumulated energy; reserve scene-scale motion for sustained development |

[ABZÛ's gameplay engineer](https://giantsquidstudios.com/Fluid-Motion-in-ABZU)
describes using damped springs and corrective forces to preserve fluid movement and
make drift understandable. The transferable principle is an immediate response with
continuous follow-through, which is now used for note height, light and emission phase.
Control's environment artist describes designing surface shapes, materials and lighting
together. For us, the same note positions therefore drive the strands, glass markers,
connections and mist illumination, instead of adding unrelated decoration.

The current note paths are continuous, straightened in the city and directed back into
depth in rain. Adjacent audible pitches are connected in register order. Moving lights
on these paths use a golden-ratio phase offset as visual spacing; they do not encode a
claimed numerical law of harmony. The detector's own spelling appears on the glass.
The default display retains chord and Nashville information while making staff optional.
The mist is stylized scattering around note sources, not ray-traced particle lighting.
Glass labels have a separate readability constraint: screen packing prevents dense
voicings from covering one another, and leaders connect them to their moving physical
anchors. The Nashville plaque uses the piano's existing reading, including uncertainty.

## Build and acceptance

1. Preserve each pitch's continuous phase and the GPU particle state. A repeated key
   must leave prior particle positions and ages intact. Keep a bounded strike history
   without making that history responsible for GPU particle lifetime.
2. Keep architectural height and momentum across strikes. Distribute particle births
   and natural renewals in time. Add fixed-step water impulses to the existing field.
3. Express velocity through nonlinear launch speed, ribbon reach, particle shape and
   a slowly settling central form. Give each world a distinct motion/material accent.
4. Compare matched soft and hard phrases in actual GPU renders in portrait and
   landscape. Check repeated-key readback before/after a strike, overlapping water
   energy, all-off decay, bounded resources, MIDI event counts and shader errors.

The design fails if softer playing loses its focal form, a new strike erases an old
one, the hard case merely gets whiter, or the scenery overwhelms the played gesture.
Review both stills and motion; passing numeric checks alone does not establish beauty.
