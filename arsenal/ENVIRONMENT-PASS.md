# Moonwater: performance and environment refinement

Daniel's brief: keep iterating until it is striking; the background feels plain.
His timing references are Synthesia and Guitar Hero. This pass makes the played
notes a clear luminous path, and gives that path an atmospheric destination.

Pre-build acceptance (Asta, 2026-09-15):

- New Lightfall performance view: actual played history flows away from each
  physical key, each attack remains a separate mark, pedal extends the ribbon,
  and strong chords launch coherent travelling light. No invented future notes.
- The existing eight harmonic diagrams stay available, with chord/Nashville
  typography and octave-aware voicing preserved.
- Replace cone trees, uniformly lit banks and the nearly empty sky with detailed
  branching silhouettes, textured stone, layered distance, moving illuminated
  clouds, a composed moon/stellar field, and water with coherent light reflection.
- React to musical energy through the same light/wind/water field. Quiet playing
  remains a finished composition. No random scene changes or repeated flash reset.
- Review actual private canvas captures in portrait and landscape at silence,
  soft/hard chords, repeated notes, a moving inner voice, and pedal release.
  Inspect motion and GPU logs; compare against the previous environment.
- Keep user services and MIDI session roots untouched; verify served modules and
  the relevant existing model tests. Do not publish a partial shared checkout.

Risk: adding scenery can bury the notes, and expensive clouds can steal frame
time. Bound geometry and ray samples, reserve the centre for the performance,
and compare the same notes across render passes before declaring improvement.

Research principles, translated into original code rather than copied assets:

- [Guerrilla: Nubis](https://www.guerrilla-games.com/read/nubis-realtime-volumetric-cloudscapes-in-a-nutshell):
  author cloud shape, depth and lighting together.
- [NVIDIA: volumetric light scattering](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process):
  light is visible through a participating atmosphere and its occlusion.
- [NVIDIA: tree wind](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-6-gpu-generated-procedural-wind-animations-trees):
  separate trunk sway from finer branch motion within a common wind field.

These references do not imply that this browser renderer implements the cited
engines or their full physical models.
