# Games: design teardown without touching code (and Archero, read from public sources)

- **Reverse-engineering arsenal, 2026-10-13** -- one of eight topic reports written the day Daniel asked the house
  to "add it to our repository of knowledge" and to have "the whole reverse engineering arsenal", with a future
  Archero-style game in mind: "actually give a viable upgrade path and make releases of new weapons and effects
  for free".
- **Topic:** (1) design teardown of a game from play, recordings, store pages, wikis, patch notes and talks, with
  no access to its code: core loop, meta loop, progression and upgrade curves, economy faucets and sinks,
  monetisation pressure points, difficulty and spawn pacing, balance arithmetic (DPS, effective HP, scaling);
  (2) Archero specifically, from public sources only, and what a viable upgrade path with free releases would
  change; (3) engine and technology identification from public signals; (4) what is fair and what is off-limits.
- **Author:** Claude (the Vandor seat), as a research subagent. Sources were read on 2026-10-13. The arithmetic in
  section 6 was run locally (a scratch Python script, outputs pasted as computed). No game was installed,
  opened, recorded, decompiled or datamined for this report. No house code was changed.
- **Discipline borrowed:** the evidence habits of the REA skill (morluto/rea, `.agents/skills/reverse-engineer-anything/SKILL.md`):
  separate observations, inferences and unknowns; route the target first; keep a finding ledger with confidence,
  search boundary and unknowns; revisit the checklist at the end; separate observed behaviour from design choices
  when rebuilding; keep bounded negative searches bounded. Its server machinery is not used here, because a
  design teardown never needs to open a binary.
- **Licence line:** written in our own words. Direct quotes are short and credited. Archero numbers below are
  labelled by where they came from; most are community-reported and should be treated as hypotheses until measured.
- **Not legal advice.** Section 10 is an orientation map so we know where the lines are, written by a research
  agent, not a lawyer.

---

## 0. The short version

1. **A design teardown needs no code.** Everything a designer needs (loops, curves, economy, offers, pacing) shows
   up on screen, in store listings, in patch notes and in what developers say in talks. Reading the client's files
   adds little for design and is exactly what Archero's terms forbid. So the method is: public record, then our own
   play recorded and measured, then a model, then pressure points.
2. **Archero in one line:** a room-by-room roguelite where you only shoot while standing still, pick one of three
   random abilities on level-up, and between runs grind permanent upgrades (random talents, equipment fused three
   copies at a time) behind an energy meter and a gem shop.
3. **Where it stalls, according to four independent teardowns (2019 to 2026):** fusing needs copies that grow
   threefold per tier while drops arrive at a roughly flat rate, unusable items had no conversion, talents are
   bought blind, and each new top-grade weapon or hero devalues what you already levelled. Archero 2 is reported to
   apply spending pressure sooner (four to six weeks in), with gacha-only top items.
4. **What Daniel's "viable upgrade path" changes:** make investment portable (it follows the player, not the item),
   make new weapons sidegrades on one published power budget, keep randomness inside the run and out of the
   permanent path, never let a duplicate be dead, and fund free weapon and effect releases with something that is
   not power (the game's price, cosmetics, optional expansions). Vampire Survivors and Path of Exile are the two
   public precedents.
5. **Engine identification is reading the silkscreen, not decapping the die.** Use store pages, credits and
   licence screens, SteamDB's file-name rules (MIT-licensed, published), PCGamingWiki, talks and job posts. For
   Archero the engine is still unconfirmed after this pass (Unity is plausible, not proven). An ads SDK named
   "Unity Ads" is not evidence of the Unity engine.
6. **Fair:** mechanics, rules, numbers you observe yourself, design patterns, public talks, published odds.
   **Off-limits:** extracting or reusing assets, datamining clients whose terms forbid it, modifying or automating
   online games, cheats, bypassing anti-cheat or protection, and copying a game's look and feel wholesale (Tetris
   v. Xio). Mechanics can still be patented, so distinctive ones get a patent check.

---

## 1. How to read this report

Every factual claim carries a source tag `[Sn]` (section 12) and, where it matters, a class:

| Class | Meaning | Example |
|---|---|---|
| **Observed (primary)** | We read it ourselves on 2026-10-13 from the publisher, the court, or the original author | The App Store page lists "Value Pack for Chapter 2" at $6.99 |
| **Reported (secondary)** | A named analyst or journalist observed it | Scott Fine describes the room rhythm |
| **Community-reported** | Wikis, guides, forums; often datamined; version and date uncertain | Front Arrow costs 25% damage per arrow |
| **Inference** | Our reasoning from the above | Copies-per-tier growth explains the slowdown |
| **Unknown** | Asked, not answered within the stated search boundary | Archero's engine |

Search boundary for this pass: web pages and PDFs reachable by the house fetchers on 2026-10-13. Several
sources refused automated reads (the Archero Fandom wiki answered 402, AppBrain, Justia and PCGamingWiki 403,
and the Exodus Privacy site serves junk to AI crawlers and asks them to stay away). Those sources are marked
"human read" in the routing table; nothing was concluded from their absence.

---

## 2. Concepts in plain words

### 2.1 Loops and arcs (Daniel Cook) [S1]

A **loop** is something the player does again and again, each time learning a bit more: they hold a guess about
how the game works, act, see the result, and update the guess. An **arc** is one-way content (a cutscene, a story
beat, a puzzle with one answer) that is spent once consumed. Cook's test for any game is short: "What repeats and
what does not?"

Hardware picture: the **core loop** is the instruction pipeline, the fetch-decode-execute cycle that runs every
few seconds (dodge, stop, shoot, pick up). The **meta loop** is the upgrade cycle between generations: you finish a
run, spend what you earned, and come back a little stronger. An **arc** is a one-time firmware splash screen: nice
once, worthless the tenth time.

### 2.2 Mechanics, dynamics, aesthetics (MDA) [S2]

Robin Hunicke, Marc LeBlanc and Robert Zubek (2004) split a game into three layers. **Mechanics** are the rules and
numbers the designer writes. **Dynamics** are what those rules do when a player pushes on them. **Aesthetics** are
the feelings that result; they name eight (sensation, fantasy, narrative, challenge, fellowship, discovery,
expression, submission). The designer builds upward from rules; the player meets the game from the top, as
feelings. A teardown runs the player's direction backwards: start from a feeling you observed ("that boss felt
unfair"), find the dynamic ("bullets fill the room faster than I can reposition"), then the mechanic ("projectile
count scales with chapter").

### 2.3 Faucets and sinks [S3]

Every resource has **faucets** (where it enters: kills, chests, daily rewards, purchases) and **sinks** (where it
leaves: upgrade costs, consumables, repairs, rerolls). Zachary Booth Simpson's 1999 analysis of the Ultima Online
economy (written with thanks to the UO team, Raph Koster among them) is the classic case study; he called the
sinks "drains". UO's lessons still hold: players hoard, so anything that only enters and never leaves inflates;
"artificial" drains such as decay are resented while natural consumption is accepted; and a duplication exploit
can wreck a whole economy (UO's counterfeit gold caused hyperinflation and pushed players to barter).

Hardware picture: a power supply and its loads. If the rails deliver more than the loads draw, the voltage creeps
up (inflation: prices stop meaning anything). If the loads exceed the supply, the system browns out (players feel
starved and quit, or pay).

### 2.4 Power curve versus difficulty curve [S4][S5]

Ian Schreiber's free 2010 course *Game Balance Concepts* (later a book with Brenda Romero [S6]) frames progression
as two curves racing each other: the player's **power** (stats, gear) plus their **skill**, against the challenge's
**power** plus the **skill** it demands. Perceived difficulty is the gap between them. Because skill rises on its
own with practice, a game with flat numbers feels easier over time, so the challenge curve must climb faster than
the stat curve alone. Level 3 of the course adds **cost curves**: put every item on one curve of "what it gives"
against "what it costs", and anything above the curve is overpowered.

Hardware picture: a cost curve is a price/performance chart. A new card that sits far above the line makes every
other card on the chart look bad; that is power creep (2.8).

### 2.5 Balance arithmetic: DPS, effective HP, figure of merit

- **DPS** (damage per second) = damage per hit x hits per attack x attacks per second x hit rate.
  Critical hits enter as an expected multiplier: 1 + crit chance x (crit multiplier - 1).
  A 25% chance of double damage is worth x1.25 on average.
- **Effective HP** (EHP) = HP / ((1 - damage reduction) x (1 - dodge chance)). 1000 HP with 20% reduction is
  1250 EHP; add 10% dodge and it is about 1389.
- **Time to kill** = enemy EHP / your DPS; **time to die** = your EHP / incoming DPS. You win a straight trade when
  time to kill is shorter. Their ratio scales with **DPS x EHP**, a single figure of merit for "can I win this
  fight", much like performance-per-watt is a single figure for a chip. Like perf-per-watt it hides context: single
  target versus crowds, burst versus sustained, and (in Archero) how much damage the player dodges by skill.
- **Archero's stop-to-shoot rule adds an uptime factor.** You only fire while standing still, so the damage you
  actually deal is sheet DPS x the fraction of time you stand still. A player who must move 40% of the time deals
  60% of their sheet DPS. This is a duty cycle, exactly like a boost clock that only holds while there is thermal
  headroom.

### 2.6 Pacing and spawn direction (Michael Booth, Valve) [S7]

Booth's slides on Left 4 Dead's AI Director are the clearest public description of pacing as an algorithm. The
game estimates each survivor's "intensity" (it rises when they are hurt, incapacitated or near a dying enemy, and
decays when nothing is engaging them) and cycles through four states: **build up** (full threat population until
intensity peaks), **sustain peak** for 3 to 5 seconds, **peak fade** (stop spawning and let the fight play out),
and **relax** for 30 to 45 seconds or until the team has moved on. Mobs arrive at random 90 to 180 second intervals
on Normal, mostly from behind. Bosses are dealt from a shuffled deck so the same one never comes twice in a row. His
own summary: "Amplitude (difficulty) is not changed, frequency (pacing) is."

Hardware picture: a fan curve with hysteresis. The controller watches temperature (intensity), lets the load run
until it gets hot, holds a moment, then backs off and lets it cool before the next burst.

Archero's fixed room rhythm (section 5.2) is a hand-authored version of the same cycle: fights build, the angel
room is the relax beat, the boss is the peak.

### 2.7 Monetisation pressure points (a detector, not a recipe) [S8]

Ramin Shokrizade's 2013 article catalogued techniques he called **coercive monetisation**: a premium currency
between the player and real money (each extra layer makes value harder to judge), **"fun pain"** (put the player in
discomfort, then sell relief), progress gates that block or slow advancement, threatening to remove what the player
already earned, and quietly ramping difficulty once a player is marked as a spender. We use this vocabulary to
**spot** pressure in a teardown and to **avoid** it in our own game. Nothing in this report recommends using it.

The opposite stance is on record too. Chris Wilson of Grinding Gear Games described Path of Exile as having
"purposefully divorced any game mechanics from the monetization": cosmetics, stash space and supporter packs only,
with all content updates free [S9].

### 2.8 Vertical versus horizontal progression, and power creep [S10]

**Vertical** progression makes numbers bigger (more damage, more HP). **Horizontal** progression adds options of
similar strength (a new weapon that plays differently but is not stronger). Vertical progression causes **power
creep**: each new release outclasses the last, so old content and old investments lose value.

Hardware picture: a new GPU generation that makes last year's card worthless, versus a long-lived socket (AM4 kept
one motherboard useful across several CPU generations). Daniel's "viable upgrade path" is the socket.

### 2.9 Game feel ("juice") [S11][S12]

Two talks every teardown should watch: Jan Willem Nijman's *The Art of Screenshake* (Vlambeer, INDIGO Classes 2013)
and Martin Jonasson and Petri Purho's *Juice It or Lose It* (GDC Europe 2012). They show how hit-pause, shake,
particles, sound and tweening turn the same rules from limp to delightful. Archero-like games live or die on this
layer, and it is measurable in recordings (frames of hit-pause, shake amplitude, effect duration).

---

## 3. The method, step by step

The steps follow the REA staging (checklist, smallest overview first, corroborate with the right evidence type,
ledger, revisit), translated from binaries to games.

**Step 0: write the checklist and name the target.** Turn the request into questions and the evidence each needs.
Example: "Why does Archero's progression feel slow after the first week?" needs (a) the upgrade rules, (b) the
inflow of upgrade materials per run, (c) costs per tier, (d) player reports of where it stalls. If Daniel says "the
game" without naming it, ask which one; never pick an example on his behalf (REA's rule, and ours).

**Step 1: route the question.** Use the routing table (section 13a) to pick the first source by question type:
recordings for timing and feel, store pages for offers and prices, version history for what changed when, talks
for intent, wikis for community-measured numbers, reviews and forums for where players hurt.

**Step 2: collect the public record, dated.** For each item record the URL, the date read, the version of the game
it describes, and its class (section 1). Wikis drift; a 2019 number may be wrong for 2026.

**Step 3: play and record, on our own device and account.** Record at a fixed frame rate (60 fps), keep the raw
file outside the repo, and probe it first (`py -m arsenal.media probe`) to confirm a constant frame rate. Then:
- `grab --sheet` and `filmstrip` to see the loop at a glance (a contact sheet of one room is the loop diagram);
- `shots` to find room transitions and boss intros as scene cuts, which gives room and run durations;
- frame-stepping (mpv, or Kinovea for motion and speed measurement) to count frames between shots: 42 frames
  between arrows at 60 fps is 1.43 attacks per second, give or take 0.03 for a one-frame error;
- count drops per chest or per run in a tally sheet, and compute an interval (section 6.6), never a bare rate.

**Step 4: model it.** Draw the loops (MDA layers; Machinations or a plain diagram), list every faucet and sink, and
put the curves (costs per level, copies per tier, stats per chapter) in a spreadsheet or a short Python script.
The test of a model is whether it predicts something you can then check in play.

**Step 5: find the pressure points.** Look for (a) where time to the next goal jumps (a curve steepens or an
input becomes random), (b) where an offer appears right after a failure or right before a wall (a revive prompt
with a countdown, a "Chapter 2 pack"), (c) where the game says no (energy empty, a gate floor not cleared), and (d)
where a new release makes an old investment worthless.

**Step 6: cross-check.** When two sources disagree, keep both with provider and date and resolve with our own
measurement, or leave it as an unknown. Do not average.

**Step 7: ledger and revisit.** Every conclusion goes into a finding ledger with its evidence, class, confidence,
search boundary and open questions. At the end, revisit the checklist and mark each question answered, partially
answered or unresolved. When designing our own game, keep two columns: **observed in the reference game** and
**our design choice**. Never present a choice as a finding.

---

## 4. Tools

| Tool | What it is for | Licence / cost | Notes |
|---|---|---|---|
| The game itself, on our own device and account | Primary evidence: play | Archero is free to install | Never on a cheat-detected account; never modified |
| `py -m arsenal.media` (house) | probe, grab/sheet, filmstrip, shots, cut, words, qc on recordings | Ours | Originals are opened read-only; receipts written; use it before any hand-typed ffmpeg |
| scrcpy (Genymobile) [S13] | Mirror and record an Android phone to the PC (`--record=file.mp4`, `--max-fps`) | Apache-2.0, free | No root needed, but USB debugging must be on: Daniel enables it on his own phone |
| OBS Studio | Record PC games or the scrcpy window | GPL-2.0, free | The house already has OBS settings notes in the media README |
| iOS screen recording | Record on iPhone | Built in | Lower control over frame rate |
| mpv | Frame-accurate stepping to count frames | GPL-2.0+ (LGPL builds exist), free | `.` and `,` step one frame |
| Kinovea [S14] | Sports-analysis video tool: timers, distance, speed, trajectory tracking, side-by-side | Free and open source, Windows | Good for movement speed and projectile speed from recordings |
| Python (pandas, matplotlib) or LibreOffice Calc / Google Sheets | Curves, cost tables, time-to-goal, intervals | Free (PSF/BSD; MPL-2.0; free) | The scratch script behind section 6 is about 100 lines |
| Machinations.io [S15] | Visual economy and resource-flow simulation (Joris Dormans's diagram language) | Freemium web service; free public plan | Cloud-hosted: do not put unannounced designs in a public diagram |
| SteamDB tech pages and FileDetectionRuleSets [S16][S17] | Engine, SDK and anti-cheat detection for Steam games from depot file names | Website free; rules MIT | Names only, never file contents; "educated guesses" by its own description |
| PCGamingWiki, Wikipedia, MobyGames | Engine, middleware and credits | Free websites | PCGamingWiki refuses our fetcher: human read |
| App Store and Google Play pages | In-app purchase list, version history, size, data-safety and requirements | Free | Primary source for offers and dated changes |
| AppBrain, Exodus Privacy reports | SDKs and trackers detected in Android apps | Free websites | Human read only (403 to us; Exodus asks AI crawlers to stay away). A tracker listed is not proof it is active |
| Sensor Tower, AppMagic (data.ai is now part of Sensor Tower) | Download and revenue estimates | Commercial; limited free views | Estimates are models; always cite provider and date |
| Teardown publications: Deconstructor of Fun, Game Developer (ex-Gamasutra), Naavik, Mobile Dev Memo | Analyst teardowns of meta, monetisation, market | Mostly free articles; some paid tiers | Analysts have their own lens (often revenue-first) |
| GDC Vault, GDC YouTube channel | Developer talks and postmortems | Many free; vault subscription for the rest | Primary source for stated intent |
| Books: *Game Balance* (Schreiber and Romero), *Game Mechanics: Advanced Game Design* (Adams and Dormans) [S6][S18] | Method references | Paid | The free Schreiber course covers most of the balance chapter |

---

## 5. Worked example A: Archero, from public sources only

Archero is Habby's 2019 mobile roguelite (Habby, Singapore). The house owns no Archero recording yet, so this
section is the public-record half of a teardown. The measurement half (section 3, step 3) waits until Daniel
chooses to record his own play.

### 5.1 Origin and scale (reported)

- Habby's CEO Wang Si'en has described a method of validating gameplay cheaply before scaling. Conference notes by
  a Chinese developer blogger (zrong, August 2020) report that Archero's first playable was made by two people, a
  producer-designer and a programmer, before the team grew to about ten with outsourced art [S19]. (Secondhand
  notes, not a transcript.)
- Revenue figures disagree because they come from different estimators, dates, and gross versus net. Deconstructor
  of Fun: over $35M net in-app revenue in the first three months (2019) [S20]; Game World Observer: about $8.5M
  in the first month [S21]; Udonis (December 2023): over $200M all-time and 90M downloads [S22]; Game Economist
  Consulting (April 2025): over $500M lifetime [S23]; Deconstructor of Fun (2025, with Sensor Tower data): about
  $4 lifetime revenue per download for Archero against $11+ for Archero 2, which was running near $27M a month [S24].
  Lesson: never mix providers in one chart.

### 5.2 Core loop (reported, consistent across sources)

- **Move or shoot, never both.** The hero auto-fires at the nearest enemy only while standing still; moving stops
  the attack. Scott Fine's 2019 three-part teardown calls the result a puzzle of positioning rather than a test of
  aim [S25].
- **Rooms in a fixed rhythm.** Fine gives a ten-room block: an intro room, four fights, an angel room, four more
  fights, a boss [S25]. Chapters run up to 50 stages [S20][S22].
- **Five enemy archetypes** that each attack the move-or-shoot decision differently: chargers, spread shooters,
  aimed shooters with red warning lines, burrowing or leaping ambushers, and slow tanks [S25].
- **Level-up drafting.** Each level-up offers three random abilities; the build resets every run [S25][S22]. A
  2019-era report puts the pool at about 50 abilities (community-reported).
- **Angel and devil.** The angel offers healing or an ability. The devil appears after a room cleared without
  taking damage and offers an ability for a cut to maximum HP [S25].

**Inference worth keeping:** the devil is offered precisely to players who just proved they can avoid damage, so
the HP it takes is worth least to the players who are offered the trade. It is a skill-gated risk that feels
generous. A design worth learning from.

### 5.3 Meta loop (reported and community-reported)

- **Gold** comes from kills and a start-of-run wheel whose payout scales with chapter, which Fine reads as a
  catch-up mechanism [S26].
- **Talents** are permanent stat upgrades bought with gold, but the talent you get is random and each purchase
  costs more [S26][S20]. A community guide lists one talent's costs as 50, 100, 150, 200, 260, 320, 390 gold
  (1470 cumulative to level 7); the increments themselves creep up (50, 50, 50, 60, 60, 70).
- **Equipment** (2019): one weapon, one armour, two rings, two spirits; rarities Common, Great, Rare, Epic,
  Perfect Epic, Legendary; three identical items fuse into the next tier; scrolls plus gold level an item [S26]. The
  Fandom wiki adds that two Legendaries make an Ancient Legendary (community-reported). Later versions added more
  slots and grades.
- **Weapons over time** (community-reported, tier list of November 2023): Brave Bow (starter), Saw Blade,
  Brightspear, Death Scythe, Tornado, Demon Blade, Stalker Staff, Gale Force, Mini Atreus (April Fool's 2022),
  Antiquated Sword, and the S-grade Expedition Fist, which the guide rates far above everything else and warns that
  "leveling the wrong weapon" is a costly mistake [S27].
- **Still growing:** version 8.1.0 (August 2026) added a new S-grade hero, Athena, a "Divinity Crusade" event and
  a "Pantheon Challenge" mode; 8.2.0 shipped on 13 September 2026 (observed on the App Store, 2026-10-13) [S28].

### 5.4 Energy, gems and ads (reported, 2019 values)

- Energy: 20 maximum, a run costs 5, one point returns every 12 minutes; four ads a day give 5 energy each; 100
  gems buy 20 energy (about $1.25 then) [S29][S22].
- Revive: 30 gems on the first death, with a five-second decision window [S29].
- Chests: Golden 60 gems or free with an ad every 24 hours; Obsidian 300 gems or free every seven days [S20][S29].
- Rewarded-ad placements: store gems, a daily spin, energy, daily packs, a lucky wheel (five ads a day), revives
  [S22].
- Offers observed on the US App Store on 2026-10-13: Battle Pass $4.99, Battle Pass 2 $16.99, Monthly Card $2.99,
  Growth Pack $0.99, Value Pack for First Purchase $1.99, Value Pack for C1 $1.99, for Chapter 2 $6.99, for
  Chapter 3 $9.99, plus gem piles [S28]. Fine already noted chapter bundles priced by progress in 2019 [S29].

### 5.5 Archero 2 (reported)

- A soft-launch teardown (SomeSelectedStories, November 2024): same stand-still-to-attack loop, 28-day battle
  passes at $9.99 and $29.99, "privilege cards" that pay daily premium currency, a Sky Tower whose floors gate
  chapter progress, weekly PvP arena, a daily two-minute boss; global launch planned for January 2025 [S30].
- A 2026 review (Priya Kapoor, April 2026): the first four to six weeks are comfortable without paying; Legendary
  gear and hero shards become the first walls; pressure "arrives earlier than it did in the first game" [S31].
- A community guide (October 2026) describes "Quality Down": a free reset that strips an item's sub-tiers and
  refunds generic, slot-specific upgrade tokens instead of the original fodder [S32]. If accurate, it is the
  publisher's own answer to the 2019 complaint that unusable items had no conversion.

### 5.6 Where progression stalls (four sources agree)

1. **Copies grow threefold per tier; drops do not.** Deconstructor of Fun (2019): fusion is painfully slow, new
   drops feel worthless once you have invested in high tiers, there was no conversion for unusable items, and
   collection depends on random drops and chest luck [S20].
2. **Random talents remove ownership.** Fine: frustrating when the only remedy is grinding "out of necessity rather
   than desire" [S26].
3. **Same content, more times.** Deconstructor of Fun's diagnosis was not the grind but repeating the same dungeon;
   their fixes were more item inflow, stat growth on level-up, and rotating modes [S20].
4. **New top grades obsolete old investment** (S-grade weapon in 2023, S-grade hero in 2026) [S27][S28].
5. **Archero 2 moves the wall earlier** and puts top items behind gacha [S31][S33].

### 5.7 Finding ledger (Archero)

| ID | Finding | Class | Evidence | Confidence | Open |
|---|---|---|---|---|---|
| F1 | Stop-to-shoot with auto-aim at nearest enemy | Reported (x3) | S25, S20, S30 | High | None |
| F2 | Ten-room rhythm with angel at the midpoint | Reported (x1) | S25 | Medium | Whether later chapters keep it: measure |
| F3 | Run length per chapter | Conflict | S25 vs S20/S22 | Low | Fine's 10 to 15 minutes vs 50-stage chapters: time a recorded run |
| F4 | Three-choice level-up draft, reset per run | Reported (x2) | S25, S22 | High | Pool size today |
| F5 | Talents random and rising in cost | Reported + community | S26, S20, guide | High (rule), Medium (numbers) | Current cost table |
| F6 | Fusion 3:1 per tier to Legendary | Reported + community | S26, wiki | High (rule), Medium (later tiers) | Whether non-identical fodder is allowed at high tiers |
| F7 | Energy 20 / 5 / 12 min; ads 4 x 5; 100 gems = 20 | Reported (2019) | S29, S22 | Medium | Unchanged in 2026? |
| F8 | Chapter-priced value packs | Observed 2026 | S28 | High | Contents of each pack |
| F9 | New S-grade items devalue prior investment | Inference from S27, S28 | S27, S28 | Medium | Whether old items get catch-up |
| F10 | Archero 2 pressure at 4 to 6 weeks; gacha-only top items | Reported | S31, S33 | Medium | Single-author reviews |
| F11 | Engine | Unknown | S19 (company moved to Unity), S34 | Low | See section 8.3 |

---

## 6. The arithmetic behind the teardown (run 2026-10-13)

All inputs are community-reported or 2019 values; the point is the method, which turns each assumption into a
number that a recording can confirm or refute.

### 6.1 Arrow abilities, single target (base damage 100, 1 attack per second)

Reported modifiers: Front Arrow +1 adds an arrow but cuts each arrow's damage by 25%; Multishot fires a second
volley but costs 10% damage and 15% attack speed (community-reported).

| Build | DPS | Change |
|---|---|---|
| Base | 100.0 | 0% |
| Front Arrow +1 (2 x 75) | 150.0 | +50% |
| Multishot (2 x 0.90 x 0.85) | 153.0 | +53% |
| Two Front Arrows, penalties **add** (3 x 50) | 150.0 | +50% |
| Two Front Arrows, penalties **multiply** (3 x 56.25) | 168.8 | +69% |
| Front Arrow + Multishot, multiply | 229.5 | +130% |
| Front Arrow + Multishot, damage penalties add (-35%) | 221.0 | +121% |

**The unknown that matters:** whether penalties add or multiply decides whether the second Front Arrow is worth
anything at all (+0% versus +19%). A wiki rarely says. A recording with on-screen damage numbers settles it. This is
REA's "never infer behaviour from names" in game form: the ability's name says "+1 arrow", the numbers say
something else.

### 6.2 Crit and EHP

Crit 25% at x2.0 is an expected x1.25; at x2.5 it is x1.375. EHP for 1000 HP: 1000 bare, 1250 with 20% reduction,
about 1389 with 20% reduction and 10% dodge.

### 6.3 The devil's trade

Using DPS x EHP as the figure of merit: +53% DPS for -20% max HP gives x1.224 (take it); +50% DPS for -40% HP gives
x0.90 (refuse); +20% DPS for -25% HP gives x0.90 (refuse). The stop-to-shoot uptime factor shifts this further
toward DPS for players who rarely get hit, which is who the devil visits (section 5.2).

### 6.4 Energy

At one point per 12 minutes the meter regenerates 120 energy a day (24 runs) if it never sits full. One 8-hour sleep
fills the 20-point cap after 4 hours and wastes 20 points; four ads return 20, so a player who checks in a few
times a day still gets about 24 runs. **Inference:** energy rarely binds a casual player; it binds the most engaged
players, who are also the ones most likely to pay. Buying energy at the 2019 price works out near $0.31 per run.

### 6.5 Fusion

| Tier | Commons-equivalent (identical fodder, upper bound) |
|---|---|
| Common | 1 |
| Great | 3 |
| Rare | 9 |
| Epic | 27 |
| Perfect Epic | 81 |
| Legendary | 243 |
| Ancient Legendary (2 Legendary) | 486 |

If item inflow per run is roughly constant, each tier takes about three times longer than the last. That is the
mechanical root of "the grind becomes real". Hardware picture: binning. To ship one top-bin part you burn through a
pile of dies, and the pile grows with every bin you climb.

### 6.6 How sure is a drop rate you counted yourself? (Wilson 95% interval)

| Observed | Rate | 95% interval |
|---|---|---|
| 3 of 20 | 15.0% | 5.2% to 36.0% |
| 12 of 100 | 12.0% | 7.0% to 19.8% |
| 30 of 300 | 10.0% | 7.1% to 13.9% |
| 0 of 50 | 0.0% | 0.0% to 7.1% (rule of three: about 6%) |

Twenty chests tell you almost nothing. This is benchmark run-to-run variance: one run is noise. Where a game sells
random items, check the published odds first; Apple requires apps selling "loot boxes" to disclose the odds of each
item type before purchase [S35].

### 6.7 Attack speed from frames

At 60 fps: 36 frames between shots is 1.67 attacks per second (1.62 to 1.71 with a one-frame error), 42 frames is
1.43 (1.40 to 1.46), 51 frames is 1.18 (1.15 to 1.20). Count ten intervals and divide to shrink the error.

---

## 7. Worked example B: what a viable upgrade path with free releases would change

This section keeps two columns apart on purpose: what Archero does (observed or reported) and what Daniel's game
could do (a design choice, his to make). Daniel said this is "for a future time"; these are options, not a plan.

| Archero (observed or reported) | Design choice for Daniel's game | Why |
|---|---|---|
| Investment lives on the item; a new top weapon resets the race (S27, S28) | Investment lives on the **player**: weapon mastery or a shared upgrade currency that applies to whatever you equip, or a full-refund respec | A free new weapon is then usable at your current power on day one: a release is a celebration, not a reset. The AM4-socket idea |
| New weapons arrive as higher grades (vertical) | New weapons are **sidegrades** on one published power budget (Schreiber's cost curve), different verbs (pierce, orbit, melee arc, chain, ground zones) | No power creep, so releases can be free without breaking the economy |
| Talents bought blind (S26) | Player-chosen upgrades with visible costs and a visible time to the next goal | Ownership; randomness that annoys in the meta is fun inside the run |
| Randomness in both run and meta | Randomness **inside the run** (three-choice drafts, angel and devil, room order); determinism **across runs** | Supergiant's "every run counts" principle for Hades [S36] |
| Duplicates were dead weight in 2019 (S20); Archero 2 later converts them (S32) | Every surplus converts to a universal currency at a fixed rate from day one | Removes the dead-inventory feeling the incumbent had to patch |
| Energy meter, ads and gems to refill (S29) | No energy, or only a "rested bonus" that multiplies rewards without gating play | Energy bites the most engaged players hardest (section 6.4) |
| Revive for gems with a countdown (S29) | Revive as a run modifier or an earned token, never a timed purchase | Shokrizade's "fun pain" pattern, avoided [S8] |
| Chapter-priced packs at walls (S28) | Walls are tuned by design, not monetised; price lives elsewhere | Keeps difficulty honest |
| Revenue from power, gacha, passes | Revenue from: the game's price plus cheap optional expansions with free content updates (Vampire Survivors), or cosmetics and supporter packs only (Path of Exile) | Free weapons only work if weapons are not the product |
| New effects arrive with paid content | **Effects as data**: status effects (burn, freeze, poison, chain lightning) and visual effects defined in data files plus shaders, so a release is content, not code | Lets a small team ship free releases on a cadence |
| Balance tuned by analysts and revenue | Per-release balance sheet plus telemetry: pick rate and win rate per weapon and ability, as Mega Crit did for Slay the Spire [S37] | Evidence instead of guesswork, and a public changelog players can trust |

Two public precedents for "free releases" that work:

- **Vampire Survivors (poncle, Luca Galante).** Cheap premium game on PC and consoles; a stream of free updates
  (Whiteout in 2023, Laborratory in 2024, Emerald Diorama and Ante Chamber in 2025) alongside optional paid
  expansions; on mobile, free with optional ads and no real-money sinks, which poncle called a "free-for-real
  approach". The mobile launch was rushed because 1:1 clones with stolen code and assets appeared on the stores
  [S38][S39]. Note the lineage too: Vampire Survivors was itself inspired by the mobile game Magic Survival. Borrowing
  a mechanic is how genres grow; copying code and assets is theft.
- **Path of Exile (Grinding Gear Games, Chris Wilson).** Free game, cosmetic-only shop, all expansions free; Wilson
  also described steering heavy spenders toward cheaper packs they could afford [S9].

---

## 8. Engine and technology identification by public signals

### 8.1 Why bother

Knowing a game's engine tells us what a small team can realistically build with similar tools, which public docs
explain its quirks, and, for games we own, what modding the publisher supports. For Daniel's future game the engine
is our choice; identifying Archero's is low value and is included as a method example.

### 8.2 Signals, strongest first

| Signal | Where | Strength | Caveat |
|---|---|---|---|
| Developer says so (talk, postmortem, engine showcase, credits) | GDC Vault, engine vendor showcase, credits screen | Strong | Dated; engines change between versions |
| In-app licences or credits screen | Settings > About / Licences in many games | Strong | Lists bundled libraries, not always the engine |
| Splash screen | Game start | Medium | Unity's "Made with Unity" splash became optional for Personal licences from Unity 6, so absence proves nothing |
| SteamDB tech tag (Steam games) | steamdb.info/tech | Medium-strong | Regexes over depot **file names**, not contents; its own docs call results educated guesses [S16][S17] |
| PCGamingWiki engine field, Wikipedia infobox | Wikis | Medium | Volunteer-edited; check the date |
| Job postings, company statements | Careers pages, interviews | Weak-medium | Company-level, not per game |
| SDK and tracker reports (AppBrain, Exodus) | Websites | Weak for engine | An ads or analytics SDK with an engine vendor's name is not the engine |
| Clone projects and "source code" listings | GitHub, marketplaces | **None** | Evidence about the clone only. Do not download (section 10.3) |

Examples of file-name rules from SteamDB's MIT-licensed rule set [S17], useful for our own builds and for games we
own: Unity is detected by `UnityEngine` or `UnityPlayer` libraries or a `globalgamemanagers.assets` file; Unreal by
`Engine/Shaders/Binaries/`, `.uasset` or `.upk` files; Godot by `project.godot`, `GodotSharp.dll` and `.pck` as
supporting evidence; GameMaker by `data.win` and `options.ini`; Electron by `LICENSE.electron.txt`. The same file
lists anti-cheat systems, which is useful to know before touching any game: if it ships anti-cheat, the house only
watches it play.

### 8.3 Worked example C: Archero's engine (bounded negative result)

- Observed: the App Store page lists requirements and size, not the engine [S28].
- Reported: Habby's early music games used Cocos2d-x, and the studio later moved to Unity (zrong's conference notes,
  2020, company-level) [S19].
- Community: Exodus Privacy's report reportedly lists a "Unity3d Ads" tracker among 18 [S34]. Unity Ads is
  offered to non-Unity apps as well, and Exodus itself says a listed tracker is not proof of activity, so this is
  not engine evidence.
- Non-evidence: GitHub "Archero clone" projects in Unity, and marketplaces selling "Archero Unity source code".
- **Conclusion:** Unity is plausible, not confirmed. Confidence low to medium. Search boundary: pages the house
  fetchers could read on 2026-10-13; AppBrain, PCGamingWiki and Exodus pages need a human read. Next step if it ever
  matters: Daniel opens the game's own licences screen, or a human reads the AppBrain or Exodus page.

Second example, dates matter: Vampire Survivors was written with the Phaser JavaScript framework, and in 2022 poncle
announced a port to an "industry-standard" engine for performance [S38]. Engine evidence must carry a version and
date.

---

## 9. Mistakes that waste time

1. **Treating wiki numbers as facts.** They are often datamined from an old client. Label, date, then measure.
2. **Mixing estimate providers.** Sensor Tower, AppMagic and an analyst's blog will disagree; gross and net differ by
   the store cut. Cite one provider per chart.
3. **Counting twenty drops and calling it a rate.** See section 6.6.
4. **Assuming stacking rules.** Additive versus multiplicative penalties change rankings (section 6.1).
5. **Reading intent from outcome.** A pressure point may be an accident of tuning; developer talks give intent, play
   gives outcome. Keep them in different columns.
6. **Judging a free-to-play game on day one.** The meta only shows its shape after weeks (Archero 2's pressure
   arrives at four to six weeks, per S31). A teardown needs a calendar, not a session.
7. **Recording at variable frame rate.** Phone captures often vary; probe first and count with timestamps.
8. **Retrying a site that refuses robots.** A 402, a 403, or an explicit "AI crawlers stay away" means route to a
   human read, not retry harder.
9. **Copying the look while "only borrowing mechanics".** The Tetris court's warning (section 10.1). Mechanics are
   free; the specific way they are drawn, animated and laid out is not.
10. **Downloading "source code" of a commercial game** from a marketplace or a "free download" site. Untrusted
    executables on a machine with no antivirus, and likely infringing. Never.
11. **Designing the economy before the loop is fun.** Habby's own method validated the core with two people before
    building the meta [S19].

---

## 10. Fair and off-limits: legal and safety notes

**Not legal advice.** This is a research map of where the lines are in the US and the EU (with UK notes), for
understanding and for building our own game. Anything that would ship commercially gets a lawyer's read.

### 10.1 What is free to learn and reuse

- **Game mechanics and methods of play are not protected by copyright in the US; the text of the rules is.** US law
  excludes any "idea, procedure, process, system, method of operation" (17 U.S.C. 102(b)). The Copyright Office applies
  this to games on its games registration page (https://www.copyright.gov/register/tx-games.html): the idea for a game,
  its name or title and its method of play are not protected, but the text of the rules and the artwork can be
  registered. The Office's older games factsheet (FL-108) said the same (its URL now returns 404). [Corrected 2026-10-13
  after review: an earlier draft cited Circular 33 [S40] for the games statement; Circular 33 (rev. March 2021)
  restates the 102(b) exclusions in general terms and does not discuss games.]
- **Facts are not protected**, including numbers you observe in play. *Feist v. Rural* (US Supreme Court, 1991):
  facts are never copyrightable, and a compilation is protected only in its original selection and arrangement [S41].
- **What is protected is expression**: art, animation, sound, music, text, characters, code, and the specific
  audiovisual presentation. *Tetris Holding v. Xio Interactive* (D.N.J., Judge Freda L. Wolfson, 30 May 2012) held
  that Xio could copy Tetris's rules but not its expression; the court listed the playing-field dimensions, the
  style and movement of the pieces, the garbage lines, the ghost piece, the next-piece display, the colour change on
  locking and the fill animation at game over as protected expression, and also found trade-dress infringement
  [S42]. In *Spry Fox v. LOLApps* (W.D. Wash., Judge Richard A. Jones, 2012) the court refused to dismiss a claim
  that a reskinned clone copied Triple Town's protectable expression; the case settled in Spry Fox's favour [S43].
- **Names are trademarks, not copyrights.** Circular 33 notes names and titles may be protected as trademarks [S40].
  Daniel's game needs its own name, characters, art direction and UI, not an Archero lookalike.
- **Patents can cover mechanics.** Copyright leaves rules free, but a patent can claim a game method. Warner Bros
  holds US 10,926,179 B2 (granted 23 February 2021) on the Nemesis system [S44], and the Tetris opinion itself cites
  Nintendo's Dr. Mario patent (US 5,265,888). Before shipping, run a patent search on any distinctive mechanic.

### 10.2 Reverse engineering law, in the order a game question hits it

- **Terms of service and licences come first in practice.** Habby's terms (last updated 20 August 2020) prohibit
  reverse engineering, decompiling, disassembling or deciphering, and obtaining "any information" from a Habby game
  "using any method not expressly permitted", as well as cheats, bots, automation and mods; US residents are under
  California law, others under Singapore law [S45]. In the US, such clauses can be enforced: in *Davidson &
  Associates v. Jung* (8th Cir. 2005), the bnetd developers who agreed to Blizzard's terms lost their fair-use
  defence for reverse engineering [S46]. **So for Archero the house stays on public signals and its own play.**
- **US copyright and fair use.** *Sega v. Accolade* (9th Cir. 1992): disassembly is fair use when it is the only way
  to reach unprotected functional elements and there is a legitimate reason, such as making compatible games [S47].
  *Sony v. Connectix* (9th Cir. 2000): intermediate copying of the PlayStation BIOS while building an emulator was
  fair use [S48]. These protect interoperability work; they do not license copying assets or code into a product,
  and the terms can still bite.
- **US anti-circumvention (DMCA section 1201).** Breaking a technical measure that controls access is its own
  violation, even when the underlying use would be fair. Narrow exceptions: 1201(f) for interoperability of an
  independently created program, 1201(g) encryption research, 1201(j) security testing with authorisation [S49].
  The 2024 triennial rule renewed exemptions for good-faith security research and for video games whose outside
  server support has ended (individual play and preservation), and refused a broader remote-access preservation
  exemption [S50]. None of this covers a live online game like Archero.
- **EU Software Directive 2009/24/EC.** Article 5(3): a lawful user may observe, study and test a program to find
  its underlying ideas and principles. Article 6: decompilation only when indispensable for interoperability of an
  independently created program, only by a lawful user, only of the necessary parts, and never to build a
  substantially similar program. Article 8: contract terms contrary to Article 6 or 5(2)-(3) are void [S51]. *SAS
  Institute v. World Programming* (CJEU, C-406/10, 2 May 2012): a program's functionality, programming language and
  data file formats are not protected expression [S52]. UK equivalents sit in the Copyright, Designs and Patents
  Act 1988, ss. 50B, 50BA and 296A (not re-read for this report).
- **Trade secrets.** Reverse engineering a lawfully obtained product is a proper means under US law (18 U.S.C.
  1839(6)(B)) and lawful acquisition under the EU Trade Secrets Directive (2016/943, art. 3(1)(b)), unless a valid
  contract limits it [S53].

### 10.3 Off-limits for the house, whatever the jurisdiction

- **Datamining or extracting assets** (models, textures, sounds, data tables) from games whose terms forbid it, and
  reusing any game's assets in our work. Reading a public wiki page others wrote is fine; republishing whole
  datamined tables in our product is not.
- **Modifying, automating or cheating in online games**, including memory editing, packet tampering, bots and
  private servers. *MDY v. Blizzard* (9th Cir. 2010) held a bot seller liable under the anti-trafficking rule for
  getting around Blizzard's Warden, which protected the online play experience, while treating the anti-bot terms as
  contract promises [S54]. In *Bungie v. AimJunkies* the cheat seller lost: an arbitrator found anti-circumvention
  and licence violations (about $4.3 million), a 2024 jury found copyright infringement, and courts refused a new
  trial [S55][S56].
- **Anti-cheat, anti-tamper, DRM or licence-check bypass** of any kind. This report gives no technique for it.
- **"Source code" or asset packs of commercial games** from marketplaces or "free download" sites: never download.
- **Look-and-feel cloning** (section 10.1).

### 10.4 What is fair, concretely

Playing the game on our own account and recording our own screen; measuring what is shown; reading store pages,
patch notes, published odds, talks, postmortems, interviews, analyst teardowns and community wikis; building
spreadsheets and models from those numbers; borrowing rules and patterns into an original game with original
expression; inspecting our own builds and openly licensed games without limit.

### 10.5 Host safety

This machine runs with Windows Defender off and updates blocked, by the owner's choice. So: any untrusted binary,
installer, mod, "source code" archive, save editor or capture file from the internet is opened only inside a
disposable VM or sandbox, never executed on the host, and never committed to the repo. Recordings of Daniel's own
play stay outside the repo too (the media toolbox already keeps oracles in `state/`, which is gitignored). A design
teardown, done as described here, needs none of those risky inputs.

---

## 11. Credits

Daniel Cook (Lost Garden); Robin Hunicke, Marc LeBlanc and Robert Zubek (MDA); Ian Schreiber and Brenda Romero
(Game Balance); Joris Dormans and Ernest Adams (Machinations, *Game Mechanics*); Zachary Booth Simpson and the Ultima
Online team (Raph Koster, Richard Vogel, Starr Long, Damion Schubert); Michael Booth (Valve); Ramin Shokrizade;
Scott Fine; Eva Grillova and Abhimanyu Kumar (Deconstructor of Fun, 2019); Mishka Katkoff and Sam Aune
(Deconstructor of Fun and Sensor Tower, 2025); Andrea Knezovic (Udonis); Priya Kapoor; the SomeSelectedStories
author; Wang Si'en (Habby) as reported by zrong; Anthony Giovannetti (Mega Crit); Greg Kasavin (Supergiant); Chris
Wilson (Grinding Gear Games); Luca Galante (poncle); Jan Willem Nijman; Martin Jonasson and Petri Purho; the SteamDB
maintainers; Genymobile (scrcpy); the Kinovea project; and morluto/rea for the evidence discipline.

---

## 12. Sources

| ID | URL | One line |
|---|---|---|
| S1 | https://lostgarden.com/2012/04/30/loops-and-arcs/ | Daniel Cook, Loops and Arcs (2012): loops build mastery, arcs are spent once |
| S2 | https://users.cs.northwestern.edu/~hunicke/MDA.pdf | Hunicke, LeBlanc, Zubek, MDA (2004): mechanics, dynamics, aesthetics; eight aesthetics |
| S3 | https://dergigi.com/assets/files/UO-Economics.pdf | Zachary Booth Simpson, The In-game Economics of Ultima Online (1999): faucets, drains, hoarding, counterfeit inflation |
| S4 | https://gamebalanceconcepts.wordpress.com/2010/07/21/level-3-transitive-mechanics-and-cost-curves/ | Schreiber, Level 3: cost curves |
| S5 | https://gamebalanceconcepts.wordpress.com/2010/08/18/level-7-advancement-progression-and-pacing/ | Schreiber, Level 7: power curve against difficulty curve, perceived difficulty, reward schedules |
| S6 | https://www.routledge.com/Game-Balance/Schreiber-Romero/p/book/9781498799577 | Schreiber and Romero, *Game Balance* (book) |
| S7 | https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf | Michael Booth, The AI Systems of Left 4 Dead (Valve, 2009): intensity, build up / peak / fade / relax, spawn rules |
| S8 | https://www.gamedeveloper.com/business/the-top-f2p-monetization-tricks | Ramin Shokrizade (2013): coercive monetisation vocabulary |
| S9 | https://www.gamedeveloper.com/business/the-mechanics-and-ethics-of-free-to-play-in-i-path-of-exile-i- | Chris Wilson on Path of Exile's cosmetic-only model (2014) |
| S10 | https://taugrim.com/2012/04/19/why-games-should-scale-horizontally-instead-of-vertically/ | Horizontal versus vertical scaling and power creep (2012) |
| S11 | https://www.youtube.com/watch?v=AJdEqssNZ-U | Jan Willem Nijman, The Art of Screenshake (2013) |
| S12 | https://www.gdcvault.com/play/1016487/Juice-It-or-Lose | Martin Jonasson and Petri Purho, Juice It or Lose It (GDC Europe 2012); found via the course notes at https://github.com/dr-jam/GameplayProgramming/blob/master/Juice.md |
| S13 | https://github.com/Genymobile/scrcpy | scrcpy: Apache-2.0, records with `--record`, needs USB debugging, no root |
| S14 | https://www.kinovea.org/ | Kinovea: free, open-source video analysis with timing, distance, speed and tracking |
| S15 | https://machinations.io/homepage | Machinations: browser economy simulation, free public plan |
| S16 | https://steamdb.info/tech/ | SteamDB technology pages |
| S17 | https://github.com/SteamDatabase/FileDetectionRuleSets | SteamDB detection rules (MIT): file-name regexes for engines, SDKs, anti-cheat; limits stated |
| S18 | https://www.oreilly.com/library/view/game-mechanics-advanced/9780132946728/ch05.html | Adams and Dormans, *Game Mechanics: Advanced Game Design*, Machinations chapter |
| S19 | https://blog.zengrong.net/post/gamenote20200801/ | zrong's ChinaJoy 2020 notes: Habby's cheap validation, two-person Archero prototype, Cocos2d-x then Unity at company level |
| S20 | https://www.deconstructoroffun.com/blog/2019/8/9/why-archero-banked-25m-but-leaves-25m-hanging-hlx9n | Grillova and Kumar (DoF, 2019): Archero meta critique, fusion, talents, chests, recommendations |
| S21 | https://gameworldobserver.com/2019/06/17/roguelike-archero-grosses-8-5m-first-month | Game World Observer: first-month revenue estimate |
| S22 | https://www.blog.udonis.co/mobile-marketing/mobile-games/archero-advertising | Andrea Knezovic (Udonis, 2023): ad placements, IAP, downloads and revenue estimates |
| S23 | https://www.gameeconomistconsulting.com/in-search-of-the-casual-habby-meta-sdk/ | Game Economist Consulting (2025): the Habby meta and its long-run problems |
| S24 | https://www.deconstructoroffun.com/blog/2025/7/31/habbys-hybridcasual-empire-the-template-that-built-a-powerhouse | Katkoff with Sensor Tower data (DoF, 2025): Habby template, revenue per download |
| S25 | https://www.gamedeveloper.com/design/finding-the-fun-archero-part-1---gameplay | Scott Fine, Archero part 1 (2019): stop-to-shoot, room rhythm, enemy types, angel and devil |
| S26 | https://www.gamedeveloper.com/design/finding-the-fun-archero-part-2---progression | Scott Fine, part 2: gold, talents, equipment, fusion, scrolls |
| S27 | https://www.allclash.com/best-weapon-in-archero-tier-list/ | Community tier list (2023): weapon roster, S-grade Expedition Fist |
| S28 | https://apps.apple.com/us/app/archero/id1453651052 | App Store listing, read 2026-10-13: version 8.2.0, IAP list and prices, 8.1.0 notes |
| S29 | https://www.gamedeveloper.com/design/finding-the-fun-archero-part-3---monetization | Scott Fine, part 3: energy, revive, chests, vendor, chapter bundles |
| S30 | https://someselectedstories.substack.com/p/tiny-teardown-archero-2-habby-games | Archero 2 soft-launch teardown (2024): passes, privilege cards, gates |
| S31 | https://www.mobilegamereport.com/articles/archero-2-pay-to-win-2026 | Priya Kapoor (2026): where Archero 2's free experience runs out |
| S32 | https://mturbogamer.com/2026/10/archero-2-quality-down/ | Community guide (2026): Quality Down refunds generic tokens |
| S33 | https://minireview.io/action/archero-2 | Archero 2 review page: gacha-only top items criticised (via search summary) |
| S34 | https://reports.exodus-privacy.eu.org/en/reports/search/com.habby.archero/ | Exodus Privacy reports for Archero (human read; tracker list via search summary) |
| S35 | https://developer.apple.com/app-store/review/guidelines/ | Apple guideline 3.1.1: loot-box odds must be disclosed before purchase |
| S36 | https://www.gamedeveloper.com/design/roguelikes-and-narrative-design-with-i-hades-i-creative-director-greg-kasavin | Greg Kasavin on Hades and meta-progression |
| S37 | https://gdcvault.com/browse/gdc-19/play/1026309 | Anthony Giovannetti, Slay the Spire: Metrics Driven Design and Balance (GDC 2019) |
| S38 | https://en.wikipedia.org/wiki/Vampire_Survivors | Vampire Survivors: Phaser origin, planned engine port, free updates, paid DLC, mobile model |
| S39 | https://kotaku.com/vampire-survivors-free-iphone-steam-mobile-smartphone-1849955308 | Kotaku on poncle's free-for-real mobile model and the 1:1 clones |
| S40 | https://www.copyright.gov/circs/circ33.pdf | US Copyright Office Circular 33 (rev. 03/2021): ideas, methods, systems, names, layouts not protected |
| S41 | https://www.law.cornell.edu/supremecourt/text/499/340 | Feist v. Rural (1991): facts are not copyrightable |
| S42 | http://business.cch.com/ipld/TetrisHoldingVXio.pdf | Tetris Holding v. Xio Interactive (D.N.J. 2012), opinion text |
| S43 | https://en.wikipedia.org/wiki/Spry_Fox,_LLC_v._Lolapps,_Inc. | Spry Fox v. LOLApps: motion to dismiss denied, settled 2012 |
| S44 | https://patents.google.com/patent/US10926179B2/en | Warner Bros Nemesis patent, granted 2021-02-23 |
| S45 | https://www.habby.com/termsOfService.html | Habby terms of service, last updated 2020-08-20 |
| S46 | https://www.eff.org/issues/coders/reverse-engineering-faq | EFF Coders' Rights reverse-engineering FAQ: fair use, EULAs (bnetd), DMCA, trade secrets |
| S47 | https://law.resource.org/pub/us/case/reporter/F2/977/977.F2d.1510.92-15655.html | Sega v. Accolade, 977 F.2d 1510 (9th Cir. 1992) |
| S48 | https://law.justia.com/cases/federal/appellate-courts/F3/203/596/474793/ | Sony v. Connectix, 203 F.3d 596 (9th Cir. 2000) |
| S49 | https://www.law.cornell.edu/uscode/text/17/1201 | 17 U.S.C. 1201 including (f), (g), (j) |
| S50 | https://www.federalregister.gov/documents/2024/10/28/2024-24563/exemption-to-prohibition-on-circumvention-of-copyright-protection-systems-for-access-control | 2024 section 1201 final rule |
| S51 | https://www.legislation.gov.uk/eudr/2009/24/article/6 | Directive 2009/24/EC art. 6 (and art. 8 alongside) |
| S52 | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:62010CJ0406 | SAS Institute v. World Programming, C-406/10 |
| S53 | https://uscode.house.gov/view.xhtml?req=granuleid%3AUSC-prelim-title18-section1839&num=0&edition=prelim | 18 U.S.C. 1839 (improper means excludes reverse engineering); EU 2016/943 art. 3 at https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32016L0943 |
| S54 | https://www.courtlistener.com/opinion/181055/mdy-industries-llc-v-blizzard-entertainment/ | MDY v. Blizzard, 629 F.3d 928 (9th Cir. 2010) |
| S55 | https://www.gamedeveloper.com/business/jury-backs-bungie-in-lawsuit-against-cheat-maker-aimjunkies | Bungie v. AimJunkies jury verdict (2024) |
| S56 | https://torrentfreak.com/court-denies-cheat-seller-aimjunkies-a-new-trial-affirms-bungies-4-3-million-win-240902/ | New trial denied; arbitration award affirmed (2024) |

---

## 13. Hand-off

### 13a. Routing table (games design domain)

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| What does the player do every few seconds? | Our own recording, then `arsenal.media grab --sheet` / `filmstrip` | Observed actions, rhythm, feedback, feel | Why the designer chose it; hidden numbers |
| How long is a room, a run, a boss? | Recording, then `arsenal.media shots` and `probe` | Timestamped durations | Spread across players unless many samples |
| Attack speed, projectile speed, movement speed | Frame stepping in mpv; Kinovea for motion | Measured intervals and speeds with error bars | Internal formulas, server-side modifiers |
| What do abilities, talents, items do in numbers? | Community wiki or guide (human read), then measure | Reported values, often datamined | Whether they are current; stacking rules |
| Drop rates, gacha odds | In-game odds disclosure; our own tally with a Wilson interval | Published odds or an honest interval | Undisclosed pity rules; silent server changes |
| What is sold and for how much? | App Store and Google Play listing | Offer names and prices on a dated read | Conversion, revenue mix |
| What changed and when? | Store version history, official patch notes | Dated release notes | Undocumented tuning |
| Revenue, downloads, retention | Sensor Tower or AppMagic estimates; analyst teardowns | Modelled estimates with a provider and date | True figures; gross versus net |
| Why did the developer do X? | GDC Vault, postmortems, interviews | Stated intent | Whether intent survived to the live game |
| Where do players feel stuck or pushed to pay? | Reviews, Reddit, analyst teardowns, plus our own time-to-goal model | Reported walls and sentiment | How representative the loud voices are |
| How does the economy behave over months? | Faucet and sink inventory, then a model (Machinations or Python) | Steady state, inflation, time to each tier in the model | The real game's hidden tuning |
| Which engine and SDKs? | Licences or credits screen; SteamDB tech (Steam); PCGamingWiki; AppBrain or Exodus (human read) | Named signals with strength and date | Certainty; per-version changes; whether an SDK is active |
| Is this mechanic safe to borrow? | Section 10 of this report; Google Patents search; a lawyer for anything commercial | Copyright, trademark, patent and look-and-feel map | Legal advice |
| Our own game build | Our code, our telemetry | Everything | Nothing hidden |

### 13b. Lessons the house should keep

1. Use when tearing down a live commercial game's design, before opening any of its files: stay on public signals
   and our own recorded play, because Habby's terms forbid obtaining "any information" from a Habby game "using any
   method not expressly permitted by Habby" [S45]. Don't when the target is our own build or an openly licensed game.
2. Use when citing a number from a wiki or guide, before building on it: label it community-reported with date and
   game version, and plan the measurement that would confirm it. Don't when the publisher's own disclosure (odds
   page, patch note) states it.
3. Use when two sources disagree on a game fact (revenue, run length, a cost), before picking one: keep both with
   provider and date, then resolve by our own measurement or record it as unknown. Don't average them.
4. Use when estimating a drop rate from our own play, before concluding anything: compute a Wilson interval;
   below about 100 trials the interval is wider than most differences worth acting on.
5. Use when comparing abilities or weapons, before ranking them: compute single-target DPS, crowd DPS and EHP
   separately, and test whether penalties add or multiply. Don't trust a tier list that does not say.
6. Use when designing progression for Daniel's game, before adding a random element to the permanent upgrade path:
   move the randomness into the run and keep the meta deterministic and visible.
7. Use when planning a new weapon or effect release, before tuning its numbers: place it on the shared power budget
   and make sure existing investment carries over. Don't ship a release that obsoletes what players levelled.
8. Use when identifying a game's engine, before stating it: name the signal, its strength and its date. Don't count
   an ads SDK, a tracker listing or a clone project as engine evidence.
9. Use when a source answers 402 or 403 or asks AI crawlers to stay away, before retrying: stop and put it on a
   human-read list.
10. Use when any "source code", asset pack or mod of a commercial game turns up, before downloading: don't. On this
    host it is untrusted code without antivirus, and it is likely infringing.
11. Use when borrowing a mechanic into an original game, before shipping: redraw, rename and re-voice everything,
    avoid copying the overall look and feel, and patent-search any distinctive mechanic.
12. Use when recording gameplay for measurement, before counting frames: record at a fixed 60 fps, probe the file
    with `arsenal.media probe`, and keep the recording outside the repo.

### 13c. Gaps: where the house needs a new tool or verb

1. **A teardown ledger verb** (for example `py agent_cli.py teardown`): a structured finding ledger for game and
   product teardowns with evidence IDs, class (observed, reported, community, inference, unknown), confidence,
   search boundary, game version and date, plus a checklist revisit. Today it is a table in a markdown file.
2. **Gameplay measurement primitives in `arsenal.media`**: a periodic-event counter (shots per second from muzzle
   flashes or projectile spawns), on-screen damage-number OCR (generalising the League clock OCR), a room-transition
   timer tuned on top of `shots`, and a "standing fraction" estimator for stop-to-shoot games.
3. **A phone capture route**: a verb wrapping scrcpy recording at a fixed frame rate with a receipt. Needs Daniel
   to turn on USB debugging on his phone himself.
4. **A local economy simulator**: faucets, sinks and curves in, time to each tier out, with Monte Carlo over drop
   luck and receipts. Machinations is a cloud service; we want something local and versioned.
5. **A balance-sheet tool for Daniel's future game**: power budget per weapon, DPS, EHP and stacking rules, versioned
   per release so every free release ships with its numbers.
6. **An engine-signal classifier for folders we own**: apply SteamDB's MIT rules to file names only, read-only, for
   our own builds and games Daniel owns. Never for live online games with anti-cheat.
7. **A human-read queue**: a way to hand Daniel a short list of URLs the fetchers cannot or should not read (Fandom,
   AppBrain, PCGamingWiki, Exodus, Justia), and ingest his notes or screenshots back as evidence.
8. **A mechanic-borrowing checklist** (expression, look and feel, name, patent search) as a reusable page, so the
   legal map travels with the design work.

### 13d. Checklist revisited

| Question from the brief | Status | Note |
|---|---|---|
| Design teardown method without code (loops, progression, economy, monetisation, pacing, balance maths) | Answered | Sections 2, 3, 6 |
| Archero: loop, stop-to-shoot, level-up picks, talents, equipment, energy and gems | Answered, partly | Numbers are 2019 or community-reported; current values need our own measurement |
| Archero: where progression stalls or spend is pressured | Answered | Four sources agree (5.6); Archero 2 sources are single-author |
| What a viable upgrade path with free weapon and effect releases would change | Answered as design options | Section 7; the choices are Daniel's |
| Engine and technology identification by public signals | Answered for method | Archero's engine unresolved (low to medium confidence, bounded search) |
| Off-limits versus fair, with jurisdiction-aware legal note | Answered | Section 10; not legal advice |
| Tools with purpose and licence or cost | Answered | Section 4 |
| Worked examples on public, permitted material | Answered | Sections 5 to 8; no recording made, because the house owns none yet and the game to record is Daniel's call |
| Routing table, lessons, gaps | Answered | Section 13 |
