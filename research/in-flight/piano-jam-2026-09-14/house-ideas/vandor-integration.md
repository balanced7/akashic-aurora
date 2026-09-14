# Vandor: where the house ideas land

This note was filed overnight on 2026-09-14. It maps what Heimdall and Navi filed onto the build phases in `jam-spec.md`,
`piano-spectacle-2026-09-13/spectacle-spec.md` and `fl-jam-bridge-2026-09-14/fl-jam-bridge-plan.md`, so that the builders pick the
ideas up. Sunshine's file has not arrived yet; add a section for it when it does.

## Heimdall (`heimdall.md`)

| Idea | Lands in | Note |
|---|---|---|
| Humanize seed keyed by (seed, bar, lane), never per session | J2 groove generator, and `arsenal/band.py` | It costs nothing, so adopt it as an invariant in both module headers. |
| A `dropout` lane: a one-bar hole where everything except the bass rests | J2 (v1 grooves); FL band pattern sets | This teaches contrast, his growth edge. The default is an occasional hole; he can turn it off. |
| Fills tied to the note density of his last two bars, not to a schedule | V2-A grooves | Needs his live note stream in the transport. The threshold is his per-bar median plus 50%, taken from the log. |
| The bass steps to the next root half a beat early before a *section* change | J2 (ballad and pulse bass), band.py walking and gospel | His own half-step gesture, played back to him. |
| An audible confirmation bar on a pattern switch (bass plus one comp note) | FL band (VFX script) and J7 transport | Lets him hear the turn without watching the strip. |
| `echo`/`follow`: after a 600 ms phrase gap, the comp plays his last 3-4 pitch classes (in-chord or colour only) on the next downbeat | V2-B | Reuses the 9.6 classifier. It is never note-for-note, and never outside notes. |
| Band calls land on a colour tone and end high, and a dropout clears space for his answer | V2-A call and response | The same rule as the report's "landing on colour means a question". |
| A "breathing" groove whose comp hits land just after his median note gap | V2-A | Measured from his sessions, which show gaps of 216-316 ms. |
| Clock honesty: schedule from beats the host reports, skip rather than play late, never retune him, no numbers before calibration | FL band plus J7 plus the riff report | VFX Script's `vfx.context.ticks` comes from the host playhead, so it satisfies the pin. The `OnUpdateBeatIndicator` concern applies to the MIDI-script (Option C) path. Report timing in words until a calibration drill has run. |
| Every card ends on a "landing": a note left unresolved on purpose, whose pull the card names | J6 seed deck (new optional card field `landing`), J8 deck | The Lydian 4 card holds the #11 and shows "land it". In Try mode for the gospel 5/4 card, the 3rd of the 5 is left out so his note completes it. |
| "Your move, named": mint a card from a recurring motif in his own log | V2 (template save-from-moment with naming on) | This is the highest-value card type because it is his own playing. |
| Question and answer card pairs | J6 (two linked cards), J8 (play as a pair) | Hearing the hinge between them is the lesson. |
| Restraint: deterministic voicings, no more styles until the first three breathe, no report numbers without a measurement | All phases | Already house law; keep it that way. |

## Navi (`navi.md`)

| Idea | Lands in | Note |
|---|---|---|
| Formats: the rarity reveal, "an AI reads my practice log", the duet in stage view, the Nashville transpose trick, the reveal in the rest | The video arc (content). These need no new code once the lanes land. | Captions must quote the system (banner, log, `practice riff`); they never invent a claim. |
| A moonlight floor pool for stage view: a soft #C8DCFF radial on the floor that breathes with the groove, normal-blended below bloom, and dims when he plays strongly | J9 integration (a scene element); jam view `stage` only | One quad, kept outside the light budget. |
| A camera arc: a smoothed height drift driven by tier density across the phrase, under 2%, no yaw | Spectacle P3 | Must pass the spectacle spec's motion receipts; the Legendary push stays the only deliberate move. |
| Prismatic bloom for Mythic: the bloom halo takes the colour of each emitting note, in circle-of-fifths order | Spectacle P3 (the Mythic look) | Must pass `wash_check`, and velocity only sets the size. Mythic stays gated on real "first time ever" events. |
| A ring-reader glyph on the glass layer: the chord's degrees lit on a circle of fifths, identical in every key | V2 (glass layer) | A practice aid that is never recorded. |
| Restraint: no summoned Mythic, no tier-coloured trails, no yaw, no captions that claim more than the banner | Spectacle and video arc | Already house law. |
