# Daniel's answers to the KeyLab questions (2026-10-22, Discord, verbatim)

Source: Bifrost bus message 1792691801852-0 (from daniil, kind chat), replying to Vandor's two-part
question list (bus 1792691091307-0 and 1792691091930-0). His words are kept byte-for-byte below;
the question each number answers is given in brackets for the reader and is not part of his text.

> Commit public,
> 2 lets fold it in
> 3. Keylab Control Center
> 4.lights first
> 5.lets make a custom modified script that has various handoff modes so we can have a one stop shop for all solution that doesnt require tip toing around fl
> 6. Lets do its own service but have it be reachable from the UI of the piano server (unless you have a better idea)
> 7.yes to downloads lets have it all be in the same folder to keep things simple
> 8. Both so we can have more themes and visual presets. Lets make a ui for making presets so I can try making some too, perhaps we can make colors pickable via fades and save or move to next element via pads?
> 9.dont understand
> 10. Yes mcp door
> 11. As fast as we can go, we can play with timings later
> 12. Lets elaborate more on this
> 13. Explain more
> 14. Lets not just make them wishes but design docs with requirements for deliverables
>
> Any other questions?  ^__^!

## The questions those numbers answer

1. Push the commit to the public GitHub too, or keep it local for now?
2. The new arc: count it toward A12 "THE FACE" (your #4), or let it stand on its own?
3. Name: "KeyLab Lit" + "The Engine Room" + "The Commons", or one umbrella "The Lit Console", or your own name?
4. Order: light-first, or sound-first?
5. When FL is open: FL drives, Aurora drives, or later our own FL script replaces Arturia's?
6. The hub that owns the keyboard: inside the piano server (:8793), or its own small service?
7. Installs outside the repo: Carla, pip pedalboard + sounddevice, the Windows MIDI Services SDK, an "Aurora" folder in FL's Mixer presets?
8. Colour root: the piano's note colours, the patch-bay look, or the Aurora Void theme?
9. The beat engine's aubio-ledfx is GPLv3+ inside our Apache-2.0 public repo: optional dependency, out of process, or a permissive detector?
10. Let other agents drive the KeyLab through an MCP door, or CLI-only for now?
11. From key press to pad light, what delay feels instant?
12. "the manual bund method": writing pad notes into the KeyLab's own stored programs, or something else?
13. The Commons (FLP template site + DAW conversion kit): not now, or a private alpha with Simon first?
14. (not a question in the list) His new ideas, filed as W293-W297: OBS, modes that follow the last
    claimant plus a key combo, pads for VFX, fader or dial-wheel scrolling, shader parameters on faders
    and knobs.

## Readings Vandor took, and which still need his confirmation

- 1 "Commit public": a push sends every commit ahead of origin/master, which on 2026-10-22 is 104
  commits back to 2026-10-07, not only the KeyLab pair. Scope confirmation asked before any push.
- 2 "lets fold it in": read as "count A16 toward A12 in the appetite order". Confirmation asked.
- 5: built as the house's own FL controller script rather than a modified copy of Arturia's file,
  so it can live in the public repo (Arturia's script is their code; the protocol facts are not).
- 9, 12, 13: explained again in plain words on Discord.
