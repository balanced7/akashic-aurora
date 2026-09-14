# Judge report: Daniel's delight and the viewer

Round: piano spectacle, 2026-09-13 night. My lens: which ideas would make Daniel grin while he plays, and make a TikTok viewer stop scrolling, without turning noisy or cheesy over a long session.

Daniel, verbatim: "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual spectacle? Perhaps even having a rarity and fanciness scale xD" / "Lets make the resolution be adaptive to the render window"

## What I looked at

Documents, read in full:
- design-vfx-director.md
- design-theory-rarity.md
- design-loot-feel.md
- the resolution/AA prototype summary (adaptive-resolution-aa.md, as the brief summarised it)

Frames I viewed, with what each one showed:
- **Baseline:** `state/arsenal/receipts/piano-wash/final-4/04-hold-2bars.jpg`
- **VFX v2, `hook-v2/rare-1-+0.25s`:** the floor ring's front arc under the keys, ivory RARE with blue hairlines. It is clean.
- **VFX v2, `rare-2-+0.6s`:** the ring's back arc rises behind the rail and glitter sits at the column feet. It is clean.
- **VFX v2, `leg-1-+0.3s`:** the best 9:16 frame of the round. The name is gold foil, the LEGENDARY banner is small and elegant, and gold rings run under the keys along with the shaft fan and the gold rail.
- **VFX v2, `leg-2-+0.8s`:** the top of the frame is still filled with soft purple and orange aurora haze. It is the weakest element.
- **VFX v2, `wash-1-leg+0.8s`:** a 40-note cluster plus a Legendary. It is busy, not washed out. However, the staff's flat signs climb to y≈560 and **collide with the LEGENDARY banner's gems**, and the top haze is at its worst here.
- **VFX v2, `wide-1-leg+0.8s`:** in 16:9 the gold aurora hem is lovely, and it is the cleanest frame of the study.
- **VFX `auto-v3/auto-coda-4+1.0`:** the scorer's own Legendary lands on the climax Fmaj9. It reads like a finale.
- **Loot `mockups/loot-a`:** the purple EPIC tag and pips crowd the space above the name. The rarity bar squeezes between the name and the chips, and the ×5 combo ring and rainbow gauge sit in the left margin across trails.
- **Loot `loot-b`:** the same, plus NEW CHORD UNLOCKED. It is the most crowded frame of the round and reads as a mobile-game HUD laid over a piano.
- **Loot `loot-c`:** PHRASE COMPLETE · EPIC appears in an empty, silent frame. It is calm and works as a natural loop or cut point.
- **Loot `loot-d`:** the SESSION HAUL card. It is a good shareable end card, though "drops by tier" is game language.
- **AA crop, `aa-crops/B-2560x1440-display-keys.png`:** HEAD as displayed is visibly soft and stair-stepped on key edges. SS2x is close to the 16-sample reference.

## Scores

| Design | Score | One line |
|---|---|---|
| vfx-director | **8.5** | The only design where the spectacle is actually on screen, prototyped and measured. It is restrained in colour and pays for itself from the light budget. |
| theory-rarity | **7.5** | The best brain. The scoring is honest and calibrated on the real `Theory.detect`, and it counts pedal blooms as one event. Its visuals are thin: mostly a text banner. |
| loot-feel | **6.0** | The best long-game ideas: the dex, a cash-out in the rests, the haul card and credit for voice leading. The in-canvas HUD and the scoring economy are wrong for Daniel's style and for a sincere piano video. |

### vfx-director: 8.5

What the viewer gets:
- **The floor shockwave** is the strongest "this is a 3D stage" cue in the set. Its front arc sweeps the empty floor and its back arc rises behind the rail.
- **The Legendary gold-foil chord name** turns the one element every viewer already reads (the name) into the payoff, with no new clutter. It is drawn after bloom, so the glyphs never change shape.
- **Gold is reserved for Legendary only.** Every other effect wears the chord's own pitch colours, so one colour means one thing and the frame never turns into a loot rainbow.
- **The house lights** dim old columns during Epic and Legendary. Contrast rises instead of luma, and the near-white share actually fell (0.0084 → 0.0013).
- **The arc bonus and the Legendary token** make Legendary land on the top of a crescendo, not on the fanciest chord name. For a viewer that is what "legendary" means: the musical climax lights up. v3 put exactly one on the climax.
- **Anti-aliasing by construction:** fwidth-clamped ring widths, a 2.5 px minimum for points and twinkle under 2 Hz. It lines up with Daniel's "perfectly un-aliased" ask.
- **Cost:** under 1.9 ms per synced frame, with no page or shader errors.

Weaknesses:
- **Calibration:** the scorer was tuned on the designer's own authored music, so the rates are unproven for Daniel.
- **The aurora's upper haze** is soft colour mush at the top of the 9:16 frame (leg-2, wash-1).
- **Banner collisions:** the banner hit the staff accidentals in the dense wash frame. The banner position is a static box, not one resolved against the staff's real glyph bounds.
- **Honesty:** the summon pad fires a chosen tier for staged TikTok moments, which undermines the tier on a public clip.
- **Shared palette uniform:** rings already in flight recolour when a second trigger fires.
- **Shader compile:** the first trigger hitches, and no precompile has been built yet.
- **Common rail pulse:** it fires on every chord change (10-30 a minute). Nobody has checked whether that is noise over an hour of play.

### theory-rarity: 7.5

Strengths:
- **Scoring:** the fanciness score treats Daniel's harmony with respect. It scores bass function by template letter steps and key distance by counted outside notes. A tracker that is unsure gives K=0, a strained reading is capped at Rare, and a pedal smear is capped.
- **Familiarity:** h dims chords he plays constantly. This is what keeps a long session from being noisy, because his lush F/A, C/G, Dm and Bbmaj7 loop goes quiet on its own.
- **The bloom merge:** 1,112 name changes became 278 events and one Rare banner in 10 minutes of pedalled arpeggios. That is the single most important anti-spam mechanism for how Daniel actually plays.
- **A novelty ladder he can check** ("first this session", "rare for you", "first time ever" with 2,000 logged chords or more), with plain music words on the banner's second line. The banner teaches the viewer while it shows off, and never claims more than the data backs.
- **Refusals:** it refuses a recording or showcase multiplier on purpose.
- **Plumbing:** a correct note that `performance.py` KINDS must accept `rarity` before any such events are sent.

Weaknesses:
- **Visuals:** the presentation is mostly a text banner, a sheen and a thin ring pulse. On its own it would not stop a thumb.
- **Tier colour on keys:** Rare puts a tier-colour rim on the keys, which breaks the pitch palette's job.
- **Bloom lift:** the Legendary bloom lift (+0.1) is the kind of light the budget exists to prevent, even with the density offset.
- **Calibration:** the style mix is a guess.
- **Tiers move between nights:** personal-relative tiers mean the same chord can be Epic one night and Uncommon the next. That is fine only if the reason line is always in the recording.
- **Complexity:** there are many interacting constants, and Mythic stays dormant for weeks.

### loot-feel: 6.0

Strengths:
- **The cash-out in the rest:** the big reveal lands in silence after the phrase, never on the music, and it doubles as a TikTok loop or cut point. It is the cleverest timing idea of the round.
- **Voice-leading credit:** smooth voice leading builds the phrase score even on plain chords, which guards against rewarding jazz clichés over good playing.
- **The chord-dex page:** silhouettes of undiscovered qualities form an ear-training map, and each chord keeps a best roll. It is a long-game goal Daniel can grin at between sessions, and it teaches theory he said he wants.
- **The recordable SESSION HAUL card** includes "home chords", which keeps it warm rather than competitive.
- **Firm refusals:** no sounds, no fail states, no randomness, and no near-miss teasing.
- **Layout:** a TikTok safe-zone map (header y 0-150, buttons x≥916, caption y≥1596) that everyone should reuse.
- **Honest separation** of intrinsic fanciness from personal discovery.

Weaknesses:
- **The in-canvas HUD** (combo medallion, vertical rainbow gauge, pips, a tag above the name, a rarity bar squeezed between name and chips) turns a sincere piano performance into a mobile-game screen. loot-b is the busiest frame of the whole round. A viewer's eye splits across five UI widgets instead of the music.
- **Scoring economy:**
  - The intrinsic-only DROP_TABLE gives up to +3 points for voicing size. Daniel plays wide and dense all the time, so his receipt Dm11/G scores 9 (LEGENDARY) every time he plays it.
  - The target share of 2.5% Legendary is about 7 a 10-minute session. The only repeat guard is "matches the last two chords".
  - Legendary would stop meaning anything within one session.
- **Colour clash:**
  - The gray, green, blue, purple and orange game ladder clashes with the pitch palette.
  - Orange Legendary competes with the gold rail and with the vfx design's gold.
- **No measurements:** mockups only, no fps or luma figures.

## The merged system (one coherent design)

**0. Foundation first.**
- Land the adaptive resolution/AA pipeline (verdict below).
- Warm the recording encoder when REC is armed. The first take currently loses about 2.3-2.6 s.
- Precompile every effect shader at boot. The first Legendary of a TikTok take must not stutter.

**1. The event: what gets scored** (theory-rarity + vfx-director)
- A committed chord name over `harmonySet`.
- A pedalled arpeggio bloom is merged into one event and scored 400 ms after it stops growing; later growth can only upgrade it.
- Strike size is measured within 80 ms.
- Notes, intervals, clusters and power chords never score.
- The Demo and computer keys never write history.

**2. The score: tier = music × familiarity, lifted by the moment** (theory-rarity + vfx-director)
- Fanciness F uses theory-rarity's parts: colour by TEMPLATES suffix, bass function, a small voicing term, key distance gated by tracker confidence, and the honesty caps.
- Familiarity h dims home chords, tonight and across the log.
- Performance, from vfx-director: strike mass, accent against the 20 s velocity mean, and the crescendo **arc**. These act as **gates** for Epic and Legendary, not as fanciness points. A fancy chord whispered in passing tops out at Rare, and the climax of a build gets the gold.
- Personal novelty (theory's ladder) can lift an event at most one tier, and it **always** prints its reason on the banner. A public clip then never shows an unexplained personal tier.
- Velocity scales effect size (0.6-1.0x) and never decides fanciness.

**3. Rationing** (vfx tokens + theory gate)
- **Tokens:** Rare cap 3, refill every 10 s; Epic cap 2, refill every 45 s; Legendary cap 1, refill every 180 s, and none in the first ~45 s.
- **Banner gate:**
  - at least 6 s between any two banners
  - per identity, 90 s apart and at most 3 per session
  - blocked events fall back to the quiet Uncommon look
  - an inflation guard that can only make tiers stricter
- **Targets for Daniel-style play:** Rare about 1 a minute, Epic 2-3 per 10 min, Legendary 1-2 per 10 min (0 while he loops), Mythic only for genuinely new vocabulary.

**4. The visual ladder** (vfx-director's effects)

| Tier | Adds |
|---|---|
| Common | the rail colour fronts |
| Uncommon | ember lift, plus theory's 350 ms sheen on the name |
| Rare | floor shockwave ring, glitter fountain, column shimmer (scaled by column count), banner |
| Epic | second ring, 7-shaft fan in the chord's colours, 2.5% push, house lights -15% |
| Legendary | **gold**: foil chord name with sheen, gold rail, three rings, gold hem ribbon (**hem only, no upper haze**), house lights -35%, 5.5% push that is skipped while the follow camera pans fast |
| Mythic | theory's gate ("first time ever" with at least 2,000 logged chords, once per session). The tier word is drawn in the chord tones' own trail colours, the third line reads FIRST TIME EVER, and everything from Legendary is included |

Two rules hold at every tier:
- All effect colour comes from the chord's pitch colours, and gold means Legendary only.
- Tier ink appears only on hairline rules and gems.

**5. The banner copy** (theory-rarity's content in vfx-director's typography)
- Letter-spaced ivory tier word with tier-ink hairlines and gems.
- Line 1: `EPIC · A7b9 · 3 7b9`, the chord name as the overlay shows it plus the Nashville number when the key is sure.
- Line 2: at most two plain reasons, e.g. `outside the key · first this session`.
- Placement is resolved against the live Nashville row **and the staff's real glyph bounds**, including accidentals, and tested with loot's R8 collision receipt at k 0.5/1/2.

**6. The reveal in the rest** (loot-feel's cash-out, without the HUD)
- There is no live gauge or combo widget on the canvas. The phrase ledger is kept invisibly.
- When a phrase that earned Epic or better ends (1.2 s of silence, or 3 s of pedal ring-out), one calm card appears: `PHRASE · EPIC · 7 chords · 2 borrowed · smooth voice leading`.
- Smooth voice leading counts toward the phrase grade.
- Playing again fast-fades the card, so it never blocks the music.

**7. The long game, off canvas** (loot-feel)
- **The chord-dex page** (`/web/piano-dex.html`): qualities with silhouettes, a best roll per chord, and first-found dates "since logging began".
- **NEW CHORD UNLOCKED in the canvas** only for a quality, merged into the tier banner, at most 3 per session, with the starter deck (recommend yes).
- **SESSION HAUL**, summoned only with H or the pad, and it shows home chords.
- **History plumbing:** `rarity` events go to the log only after the server accepts the kind (theory's order-of-operations note).

**8. Modes** (merged)
- **Off:** byte-identical to today.
- **Practice:** rail pulse, ring and a quiet reason chip; no banners; finds wait for the haul card.
- **Show:** everything above, rationed.
- REC never changes the mode by itself.
- No summon-a-tier pad. What is recorded is what he played.

**9. Receipts to keep**
- wash_check with a forced Legendary every 3 s: staff luma under 0.6, label band within 5%.
- A noise receipt over 60 s of dense pedalled play: banners per minute, and zero overlaps.
- p95 frame-time delta at most 0.3 ms at 1080x1920, **with REC running**.
- A per-slot palette, so rings in flight don't recolour.
- A per-scheme blend policy for Upright Roll.

## Cut

- **Loot's in-canvas combo medallion and live fanciness gauge.** They read as a mobile game, clutter the left margin across the trails, and pull the eye from the music.
- **Loot's tier tag with pips above the chord name, and the rarity-climb bar between the name and the chips** in Show mode. They crowd the sacred name band; the vfx banner and gems carry the tier. The bar could survive only as an optional Practice indicator.
- **Loot's gray/green/blue/purple/orange ladder as the primary signal, and its orange Legendary.** Use gold for Legendary; tier ink only on hairlines.
- **Loot's intrinsic-only DROP_TABLE with up to +3 voicing points.** Daniel's habitual wide voicings would hit LEGENDARY constantly.
- **The vfx aurora's upper haze.** Keep the gold hem ribbon only.
- **The vfx summon pad that fires a chosen tier, and the "staged" Mythic (E16).** A staged tier on a public clip is a false claim.
- **E14, the "held breath" time dilation.** It touches the LIGHT model's time base; defer indefinitely.
- **Theory's Legendary bloom +0.1 lift and its tier-colour key rim on Rare.** Use the house lights instead, and keep keys in pitch colours.
- **Live `+1 DEX` chips and live MOVES unlocks.** Keep them for the dex page and haul card.
- **Surprisal-based personal rarity.** theory-rarity already rejected it with evidence.

## Concerns

1. **The first Legendary of a take must not stutter.** A three.js program compiles the first time its mesh is visible; precompile with `compileAsync` at boot.
2. **The first recording after page load loses about 2.3-2.6 s of frames.** This is pre-existing and reproduced on HEAD's own pipeline. It ruins TikTok takes more than any missing effect, so fix the encoder warm-up first.
3. **Every tier rate is synthetic.** vfx was tuned on its own authored music, theory used a guessed style mix, and loot has no numbers. The practice log only began tonight. Re-read the thresholds against Daniel's first three real sessions before anyone calls a tier right.
4. **Banner collisions.** In the dense wash frame the staff's flat signs reached the banner's gems (`hook-v2/wash-1-leg+0.8s.jpg`). All three designs claim the y 440-590 gap that the live Nashville row also wants. Resolve against real glyph bounds.
5. **Noise over a long session.** The Common rail pulse fires 10-30 times a minute, and Rare banners about once a minute. Consider dropping the rail pulse on repeats and when the bloom merge holds, and check how it feels after 30+ minutes of real play.
6. **Chasing banners (Goodhart).** Familiarity dimming, voice-leading credit and Practice mode are the guards; watch whether Daniel starts playing for the gold.
7. **Tiers are personal.** The same chord can rank differently on different nights. That is only honest on a public video if the reason line is always rendered into the recording.
8. **Shared palette uniform.** A second trigger within ~2 s recolours rings already in flight. Use per-slot palettes, and blend in OKLab to avoid grey mud.
9. **Camera push.** It must scale by framing, skip fast pans and never crop sounding keys.
10. **Integration.** All prototypes sit on a886a0af, and the concurrent build changed the overlay, LAYOUT and imports, so each needs a hand 3-way merge. The vfx pixel constants (the point minimum, banner canvas size) must follow the adaptive render scale.
11. **Unmeasured:** fps in a real, visible window; recording with effects running; a real KeyLab session.

## Verdict on the resolution/AA approach

**Adopt it, and merge it before any spectacle work.** It is correct, measured and conservative:
- **Display path:**
  - An adaptive drawing buffer sized from `device-pixel-content-box` puts the canvas 1:1 on screen (screenshot equals buffer, MAE 0, at DPR 1.5 too).
  - It removes the browser resample that softened HEAD, whose edge error was 2.9-3.4x higher.
- **Pipeline:** SS 2x with a linear-light box downsample plus MSAA 4 was the best of 14 configs in all four window cases (edge MAE .007-.009), and it roughly halves edge shimmer.
- **Bloom** is pinned to the framing size. This matters for the spectacle: the glow, and every effect tuned against it, looks the same live, in a small window and in the file.
- **Recording:**
  - It renders exactly 1080x1920 from a 2160x3840 scene in 5.3 ms, paced to the 60 frames the file keeps.
  - The wash and sustain receipts match HEAD, and the sustain gaps are explained by snapshot resize timing.
  - That is a real improvement for TikTok, not just for the live view.

Follow-ups, in order:
1. **Encoder warm-up** for the first-take frame loss.
2. **Replace the fixed 5 MP live cap with a frame-time governor.** Daniel's 16:9 window at 2560x1440 currently drops to 1x, although 2x without MSAA fits.
3. **Specular anti-aliasing on the key bevels and clearcoat.** The remaining shimmer is on the glossy keys, the part a viewer's eye sits on. "Perfectly un-aliased" is not literally reached (edge error ~.007), and Daniel should be told that plainly.
4. **Verify a runtime DPR change** (Ctrl+=) in his real browser.
5. **Update the stale piano.css comment** at merge.

HDR is untouched and 8-bit sRGB remains, which is fine for the TikTok deliverable. Any spectacle effect built afterwards must use the render scale for its pixel constants.
