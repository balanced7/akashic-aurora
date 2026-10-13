# Games: design teardown without touching code — the operator's guide

Reading a game's loops, progression, economy, monetisation, pacing and balance from play, recordings,
store pages, wikis, patch notes and talks, with no access to its code. Distilled from
`research/reviewed/reverse-engineering-2026-10-13/games-design-teardown.md` (the full report, with the
Archero worked example, the arithmetic, and every source). **Not legal advice**; the legal note is
below, the full map in `method-legal-cleanroom.md`. For Daniel's future game specifically, see
`archero-design-seed.md`.

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

## The short version

A design teardown needs **no code**. Everything a designer needs — loops, curves, economy, offers,
pacing — shows up on screen, in store listings, in patch notes and in what developers say in talks.
Reading the client's files adds little for design and is exactly what live games' terms forbid
(Habby's terms, last updated 2020-08-20, forbid obtaining "any information" from a Habby game
"using any method not expressly permitted by Habby"). So the method
is: public record, then our own recorded and measured play, then a model, then the pressure points.
Engine identification is reading the silkscreen, not decapping the die.

## Concepts, plainly

- **Loops and arcs** (Daniel Cook). A loop is something the player does again and again, learning each
  time (dodge, stop, shoot, pick up); an arc is one-way content spent once (a cutscene). The **core
  loop** is the fetch-decode-execute cycle of a few seconds; the **meta loop** is the upgrade cycle
  between runs. Cook's test: "what repeats and what does not?"
- **MDA** (Hunicke, LeBlanc, Zubek). Mechanics (rules the designer writes) → dynamics (what they do
  under a player) → aesthetics (the feelings). A teardown runs it backwards: start from a feeling you
  observed ("that boss felt unfair"), find the dynamic ("bullets fill the room faster than I can
  move"), then the mechanic ("projectile count scales with chapter").
- **Faucets and sinks** (Zachary Booth Simpson's Ultima Online study). Every resource has faucets
  (kills, chests, daily rewards, purchases) and sinks (upgrade costs, consumables, rerolls). More in
  than out → inflation; more out than in → players feel starved and quit or pay.
- **Power curve vs difficulty curve** (Ian Schreiber). Progression is two curves racing; perceived
  difficulty is the gap. Skill rises on its own, so the challenge curve must climb faster than stats
  alone. **Cost curves:** plot every item as "what it gives" against "what it costs"; anything above
  the line is overpowered.
- **Balance arithmetic.** DPS = damage × hits/attack × attacks/s × hit-rate; crit is an expected
  multiplier 1 + chance×(mult−1). EHP = HP / ((1−reduction)×(1−dodge)). Time-to-kill = enemy EHP / your
  DPS. The single figure of merit is DPS×EHP (like perf-per-watt, it hides context: single vs crowd,
  burst vs sustained). **A stop-to-shoot game adds an uptime factor** — you deal sheet DPS × the
  fraction of time you stand still (a duty cycle, like a boost clock holding only within thermal
  headroom).
- **Pacing** (Michael Booth's Left 4 Dead AI Director). Estimate "intensity", cycle build-up → sustain
  peak → fade → relax. "Amplitude (difficulty) is not changed, frequency (pacing) is." A fixed room
  rhythm is a hand-authored version of the same cycle.
- **Monetisation pressure points** (Ramin Shokrizade's "coercive monetisation" vocabulary) — a
  **detector, not a recipe**: premium currency between player and money, "fun pain" (discomfort then
  sell relief), progress gates, threatening to remove what's earned. The opposite stance is on record
  (Chris Wilson, Path of Exile: "purposefully divorced any game mechanics from the monetization").
- **Vertical vs horizontal progression, and power creep.** Vertical makes numbers bigger (causes power
  creep: each release outclasses the last); horizontal adds options of similar strength. Daniel's
  "viable upgrade path" is the long-lived socket (AM4), not the yearly GPU that obsoletes last year's.
- **Game feel / "juice"** (Nijman's *The Art of Screenshake*; Jonasson & Purho's *Juice It or Lose
  It*). Hit-pause, shake, particles, sound, tweening — measurable in recordings (frames of hit-pause,
  shake amplitude, effect duration).

## The method

0. **Write the checklist and name the target.** Questions + the evidence each needs. If Daniel says
   "the game" without naming it, ask which — never pick an example on his behalf.
1. **Route the question** (table below): recordings for timing/feel, store pages for offers/prices,
   version history for what changed, talks for intent, wikis for community numbers, reviews/forums for
   where players hurt.
2. **Collect the public record, dated.** URL, date read, game version, class (observed / reported /
   community-reported / inference / unknown). Wikis drift; a 2019 number may be wrong for 2026.
3. **Play and record, on our own device and account — record only, measure afterwards.** On a
   live-service game the recording is passive (`scrcpy --no-control`, OBS) and every measurement runs
   offline on the saved file: no live overlay, HUD reader, OCR or `adb` input while the game runs.
   Fixed 60 fps; raw file outside the repo; probe
   first (`py -m arsenal.media probe`) to confirm constant frame rate. Then `grab --sheet` /
   `filmstrip` (the loop at a glance), `shots` (room/boss transitions as cuts → durations),
   frame-stepping (mpv, Kinovea) to count frames between shots (42 frames at 60 fps = 1.43 attacks/s ±
   one frame), and a tally of drops per run → an interval, never a bare rate.
4. **Model it.** Draw the loops (MDA, Machinations or a plain diagram), list every faucet and sink, put
   the curves (cost per level, copies per tier, stats per chapter) in a spreadsheet or short script.
   The test of a model is whether it predicts something you can then check in play.
5. **Find the pressure points.** Where time-to-next-goal jumps; where an offer appears right after a
   failure or before a wall; where the game says no (energy empty, a gate); where a new release makes an
   old investment worthless.
6. **Cross-check.** Two sources disagree → keep both with provider and date, resolve by our own
   measurement, or leave as unknown. **Never average.**
7. **Ledger and revisit.** Every conclusion with evidence, class, confidence, boundary, open questions.
   When designing our own game, keep two columns: **observed in the reference** and **our design
   choice.** Never present a choice as a finding.

## Tools

The game on our own device/account (never a cheat-detected account, never modified); `py -m
arsenal.media` (probe, grab/sheet, filmstrip, shots, cut, words, qc — use before any hand-typed
ffmpeg); **scrcpy** (Apache-2.0, mirrors and records an Android phone; **Daniel's decision:**
installing it and enabling USB debugging on his own phone; run it record-only with `--no-control`,
e.g. `scrcpy --no-control --record=<file outside the repo>`); OBS; mpv (`.`/`,` frame step); **Kinovea** (free, movement/projectile speed from
recordings); Python/Sheets for curves; **Machinations.io** (economy simulation — cloud, so no
unannounced designs in a public diagram); **SteamDB tech pages + FileDetectionRuleSets** (MIT; engine/
SDK/anti-cheat by depot **file names only**, "educated guesses"); App/Play store pages (offers,
prices, version history, data-safety); teardown publications (Deconstructor of Fun, Naavik, Game
Developer); GDC Vault/YouTube (stated intent); books (Schreiber & Romero *Game Balance*; Adams &
Dormans *Game Mechanics*).

## The arithmetic that matters (method, not the specific numbers)

- **Additive vs multiplicative penalties change rankings.** Two "+1 arrow, −25% each" effects are +50%
  if penalties add, +69% if they multiply. A wiki rarely says; a recording with on-screen damage
  numbers settles it. (REA's "never infer behaviour from names" in game form: the name says "+1
  arrow", the numbers say otherwise.)
- **Figure-of-merit the risk/reward trade** with DPS×EHP (e.g. +53% DPS for −20% max HP = ×1.22, take
  it; +50% DPS for −40% HP = ×0.90, refuse).
- **Fusion N:1 per tier compounds.** 3:1 to each next tier → 243 commons for one Legendary; if inflow
  is flat, each tier takes ~3× longer — the mechanical root of "the grind becomes real" (binning: burn
  a pile of dies per top-bin part).
- **A drop rate you counted yourself needs a Wilson interval.** 3 of 20 → 15% but [5%, 36%]; twenty
  chests tell you almost nothing. Below ~100 trials the interval is wider than most differences worth
  acting on. Where a game sells random items, check the published odds first (Apple requires loot-box
  odds disclosure).
- **Attack speed from frames** at the game's true frame rate; count ten intervals and divide to shrink
  the one-frame error.

## Engine and technology identification by public signals

Strongest first: the developer saying so (GDC talk, credits, showcase) → in-app licences/credits
screen → splash screen (Unity's became optional, so absence proves nothing) → SteamDB tech tag
(regexes over depot **file names**, not contents) → PCGamingWiki/Wikipedia → job postings → SDK/tracker
reports (an ads SDK with a vendor's name is **not** the engine) → clone projects (**no** evidence about
the original). SteamDB's MIT rules, useful for our own builds and games we own: Unity by
`UnityPlayer`/`globalgamemanagers.assets`; Unreal by `Engine/Shaders/Binaries/`/`.uasset`/`.upk`; Godot
by `project.godot`/`.pck`; GameMaker by `data.win`; Electron by `LICENSE.electron.txt`. The same file
lists anti-cheat: **if a game ships anti-cheat, the house only watches it play.** Engine evidence must
carry a version and date.

## Fair and off-limits

**Fair:** playing on our own account and recording our own screen; measuring what is shown; reading
store pages, patch notes, published odds, talks, postmortems, interviews, analyst teardowns, community
wikis; building models from those numbers; borrowing rules and patterns into an original game with
original expression; inspecting our own builds and openly licensed games.

**Off-limits:** datamining or extracting assets from games whose terms forbid it, and reusing any
game's assets; modifying/automating/cheating in online games (memory editing, packet tampering, bots,
private servers — *MDY v. Blizzard*, *Bungie v. AimJunkies*); bypassing anti-cheat/anti-tamper/DRM;
downloading "source code" or asset packs of commercial games (untrusted code on an unprotected host,
likely infringing); look-and-feel cloning (*Tetris v. Xio*, *Spry Fox v. LOLApps*). Mechanics are free
in the US (17 U.S.C. 102(b); the Copyright Office's games page, copyright.gov/register/tx-games.html:
the method of play is free, the text of the rules is not) but can be **patented** (Warner's Nemesis
system) — patent-search a distinctive mechanic before shipping.

## Routing table (games design)

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| What does the player do every few seconds? | Our recording + `arsenal.media grab --sheet`/`filmstrip` | Observed actions, rhythm, feedback, feel | Why the designer chose it; hidden numbers |
| How long is a room/run/boss? | Recording + `arsenal.media shots`/`probe` | Timestamped durations | Spread across players |
| Attack/projectile/movement speed | Frame stepping (mpv); Kinovea | Measured intervals and speeds with error bars | Internal formulas; server-side modifiers |
| What do abilities/talents/items do in numbers? | Community wiki/guide (human read), then measure | Reported values (often datamined) | Whether current; stacking rules |
| Drop rates, gacha odds | In-game odds disclosure; our own tally + Wilson interval | Published odds or an honest interval | Undisclosed pity; silent server changes |
| What is sold, for how much? | App/Play store listing | Offer names and prices, dated | Conversion; revenue mix |
| What changed and when? | Store version history, patch notes | Dated release notes | Undocumented tuning |
| Revenue/downloads/retention | Sensor Tower / AppMagic; analyst teardowns | Modelled estimates with provider + date | True figures; gross vs net |
| Why did the developer do X? | GDC Vault, postmortems, interviews | Stated intent | Whether it survived to the live game |
| Where do players feel stuck/pushed to pay? | Reviews, forums, teardowns + our time-to-goal model | Reported walls and sentiment | How representative the loud voices are |
| How does the economy behave over months? | Faucet/sink inventory → a model | Steady state, inflation, time to each tier | Hidden tuning |
| Which engine/SDKs? | Licences/credits screen; SteamDB tech; PCGamingWiki | Named signals with strength + date | Certainty; per-version; whether an SDK is active |
| Is this mechanic safe to borrow? | `method-legal-cleanroom.md`; Google Patents; a lawyer | Copyright/trademark/patent/look-and-feel map | Legal advice |
| Our own game build | Our code, our telemetry | Everything | Nothing hidden |

## Lessons (trigger-phrased)

- Use when tearing down a live commercial game's design, before opening any of its files: stay on
  public signals and our own recorded play — Habby's terms forbid obtaining "any information" from a
  Habby game "using any method not expressly permitted by Habby". Don't when the target is our own
  build or an openly licensed game.
- Use when citing a wiki/guide number, before building on it: label it community-reported with date
  and game version and plan the measurement that confirms it. Don't when the publisher's own
  disclosure states it.
- Use when two sources disagree on a game fact, before picking one: keep both with provider and date,
  resolve by our own measurement or mark unknown. Don't average.
- Use when estimating a drop rate from our play, before concluding: compute a Wilson interval; below
  ~100 trials it is wider than most differences worth acting on.
- Use when comparing abilities/weapons, before ranking: compute single-target DPS, crowd DPS and EHP
  separately, and test whether penalties add or multiply. Don't trust a tier list that does not say.
- Use when planning a new weapon/effect release, before tuning: place it on the shared power budget and
  make sure existing investment carries over. Don't ship a release that obsoletes what players levelled.
- Use when identifying an engine, before stating it: name the signal, its strength and date. Don't
  count an ads SDK, a tracker listing or a clone project as engine evidence.
- Use when a source answers 402/403 or asks AI crawlers to stay away, before retrying: stop and put it
  on a human-read list.
- Use when any "source code"/asset pack/mod of a commercial game turns up, before downloading: don't —
  untrusted code without AV, and likely infringing.
- Use when borrowing a mechanic into an original game, before shipping: redraw, rename and re-voice
  everything, avoid copying the overall look and feel, and patent-search any distinctive mechanic.
- Use when recording gameplay for measurement, before counting frames: record only (`scrcpy
  --no-control`, OBS) at a fixed 60 fps, probe with `arsenal.media probe`, keep the recording outside
  the repo, and measure offline. Don't run any live overlay, HUD reader or `adb` input on a
  live-service game.

## Gaps (build proposals)

A `teardown` ledger verb (finding ledger with class/confidence/boundary/version/date); gameplay
measurement primitives in `arsenal.media` that run offline on saved recordings (periodic-event
counter, on-screen damage-number OCR generalising the League clock OCR, room-transition timer on
`shots`, a "standing fraction" estimator); a record-only phone capture route wrapping scrcpy
`--no-control`; a local economy simulator (faucets/sinks/curves → time-to-tier,
Monte Carlo over drop luck); a per-release balance-sheet tool; an engine-signal classifier for folders
we own (SteamDB rules, file names only, never online games with anti-cheat); a human-read queue; a
mechanic-borrowing checklist (expression / look-and-feel / name / patent search).

## Legal note (not legal advice; US, EU and UK orientation, dated 2026-10-13)

In the **US**, studying a program to reach its unprotected ideas can be fair use (*Sega v.
Accolade*, 9th Cir. 1992; *Sony v. Connectix*, 9th Cir. 2000), but a EULA or terms of service can
forbid reverse engineering and be enforced (*Bowers v. Baystate*, Fed. Cir. 2003; *Davidson v.
Jung*, 8th Cir. 2005), and DMCA §1201 separately bans circumventing access controls; its exemptions
(§1201(f), (g), (j); 37 C.F.R. §201.40) excuse only the act, under their stated conditions, never
tools. In the **EU and UK**, a lawful user may observe, study and test a program (Directive
2009/24/EC art. 5(3); CDPA s.50BA) and decompile for interoperability within art. 6's limits (CDPA
s.50B), and contract terms against those rights are void (art. 8; CDPA s.296A). In **both**,
trade-secret law allows reverse engineering a lawfully obtained product unless a valid contract
forbids it (18 U.S.C. 1839(6)(B); Directive 2016/943 art. 3(1)(b)), and ideas, methods and observed
facts are free, while code, art, audio and text are protected and a distinctive look may be protected
(*Tetris Holding v. Xio*, D.N.J. 2012, including as trade dress; republishing a whole extracted table
is a separate question in
the EU, where a database right can apply). **For this domain:** live games' terms forbid opening the
client (Habby's terms, last updated 2020-08-20, forbid obtaining "any information" from a Habby game
"using any method not expressly permitted by Habby"). *MDY v. Blizzard* (9th Cir. 2010) applied
§1201 to a bot evading Warden, and *Van Buren* (2021, footnote 8) left open whether terms of service
can define unauthorised access under the CFAA, so the house never automates, overlays, or reads the
memory or traffic of a live game. 37 C.F.R. §201.40(b)(19)(i)(A) lets an individual restore
personal, local play of a game whose servers have closed; its preservation parts are for eligible
libraries, archives and museums only. Mechanics are free to reimplement in the US (17 U.S.C. 102(b))
but can be patented (US 10,926,179 B2), and names are trademarks. The full map with its caveats is
`method-legal-cleanroom.md`; anything we ship that leans on someone else's product goes past a
lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/games-design-teardown.md` (the Archero
worked example, the arithmetic run 2026-10-13, all 56 numbered sources). Method authors credited:
Daniel Cook; Hunicke, LeBlanc & Zubek; Simpson and the UO team; Schreiber & Romero; Dormans & Adams;
Michael Booth; Shokrizade; Chris Wilson; Nijman; Jonasson & Purho; the SteamDB maintainers; Genymobile
(scrcpy); the Kinovea project; and **morluto/rea** for the evidence discipline.
