# Archero-style game — a design seed (for a future project)

> **This is a seed, not a plan.** Daniel said the Archero-style game is "for a future time." Nothing
> here is decided; these are options drawn from public sources and the house's own tooling, kept so the
> arsenal is ready when he chooses to start. The design choices are his. Two columns are kept apart
> throughout, per the Iron Law: **observed in the reference game** (from public analysis and
> legitimate play) versus **a design choice for our game.** Never present a choice as a finding.
> **Not legal advice**; the legal note is below, the full map in `method-legal-cleanroom.md`. In the
> US, legality rests on one line: mechanics and methods of play are free to learn (*17 U.S.C. 102(b)*;
> the Copyright Office's games page, copyright.gov/register/tx-games.html), but a specific game's rule
> text, art, audio, UI, names and distinctive look-and-feel are not ours to copy (*Tetris v. Xio*,
> *Spry Fox v. LOLApps*).

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

Daniel's own words (2026-10-13): *"I would love to make an archero style game but actually give a
viable upgrade path and make releases of new weapons and effects for free."* That sentence is the whole
brief: a **viable upgrade path** (investment that keeps its value) and **free weapon/effect releases**
(content, not power, on a cadence a small team can sustain).

## What we know about Archero (from public sources only)

Observed/reported, community-reported and inference are tagged; measurement of the current game waits
until Daniel records his own play (`games-design-teardown.md` has the full ledger and sources). We
never open the client — Habby's terms forbid it; public signals and our own recorded play only.

**The loop (reported, consistent across sources — Scott Fine 2019, Deconstructor of Fun):** a
room-by-room roguelite where you **only shoot while standing still** (auto-fire at the nearest enemy;
moving stops the attack — a positioning puzzle, not an aim test); each level-up drafts **one of three
random abilities**, reset every run; rooms run in a fixed rhythm (a ten-room block: intro, four fights,
an angel room, four fights, a boss); five enemy archetypes each attack the move-or-shoot decision
differently; an **angel** (heal or ability) and a **devil** (an ability for a cut to max HP, offered
after a no-damage room). *Inference worth keeping:* the devil is offered precisely to players who just
proved they can avoid damage, so the HP it takes is worth least to those offered the trade — a
skill-gated risk that feels generous.

**The meta (reported + community-reported):** permanent **talents** (random which you get, rising
cost), **equipment** fused three identical copies at a time up the rarity tiers, an **energy** meter
(a run costs energy; it regenerates slowly or refills with ads/gems), **revive** for gems with a
countdown, chapter-priced **value packs**. The game is still growing (new S-grade heroes and weapons
through 2026).

**Where it stalls (four independent teardowns agree, 2019–2026):**
1. **Copies grow threefold per tier while drops arrive at a roughly flat rate** — fusion becomes a
   grind, and new drops feel worthless once you have invested in high tiers.
2. **Random talents remove ownership** — you grind "out of necessity rather than desire."
3. **Same content, more times** — the diagnosis was repetition, not the grind itself.
4. **New top grades obsolete old investment** — each new S-grade weapon/hero resets the race.
5. **Archero 2 moves the wall earlier** (reported four-to-six weeks in) and puts top items behind gacha.

The structural root (Grillova, Naavik 2022): **run-based power and permanent power fight each other,**
and a player needs only one hero and one gear set, so later spending buys little visible progress. That
is the exact tension Daniel's "viable upgrade path" is meant to resolve.

## Design principles for our game (choices, Daniel's to make)

Each row keeps the reference's observed problem beside an option for our game and the reason.

| Archero (observed/reported) | Design choice for our game | Why |
|---|---|---|
| Investment lives on the **item**; a new top weapon resets the race | Investment lives on the **player** — weapon mastery, or a shared upgrade currency that applies to whatever you equip, or a full respec | A free new weapon is then usable at your current power on day one: a release is a celebration, not a reset (the AM4-socket idea) |
| New weapons arrive as higher **grades** (vertical) | New weapons are **sidegrades** on one published power budget (Schreiber's cost curve) — different verbs (pierce, orbit, melee arc, chain, ground zones) | No power creep, so releases can be free without breaking the economy |
| Talents bought blind | Player-chosen upgrades with **visible costs and a visible time to the next goal**; soft caps the player can *see* | Ownership; and a soft cap is easy to measure but hard to explain from outside (Drill B) — so tell the player rather than hide it |
| Randomness in both run and meta | Randomness **inside the run** (three-choice drafts; a risk-for-reward offer room — a genre pattern older than Archero, e.g. *The Binding of Isaac*'s devil deals — presented with our own characters, not an angel and a devil; room order); **determinism across runs** | Supergiant's "every run counts" principle for Hades |
| Duplicates were dead weight (2019); patched later | Every surplus **converts** to a universal currency at a fixed rate from day one | Removes the dead-inventory feeling the incumbent had to patch |
| Energy meter, ads and gems to refill | No energy, or only a "rested bonus" that multiplies rewards without gating play | Energy bites the most engaged players hardest |
| Revive for gems with a countdown | Revive as a run modifier or an earned token, never a timed purchase | Shokrizade's "fun pain" pattern, avoided |
| Chapter-priced packs at walls | Walls tuned by design, not monetised; price lives elsewhere | Keeps difficulty honest |
| Revenue from power, gacha, passes | Revenue from the game's price + cheap optional expansions with free content updates (Vampire Survivors), or cosmetics, convenience items and supporter packs with no power for sale (Path of Exile, whose shop also sells stash tabs) | **Free weapons only work if weapons are not the product** |
| New effects arrive with paid content | **Effects as data** — status effects and visual effects defined in data files + shaders, so a release is content, not code | Lets a small team ship free releases on a cadence |
| Balance tuned by analysts and revenue | Per-release balance sheet + telemetry (pick rate and win rate per weapon/ability, as Mega Crit did for Slay the Spire) | Evidence instead of guesswork, and a public changelog players can trust |

Two public precedents for free releases that work: **Vampire Survivors** (poncle — a cheap premium
game, a stream of free updates alongside optional paid expansions, a "free-for-real" mobile model; and
note its own lineage from Magic Survival — borrowing a mechanic grows a genre, copying code and assets
is theft) and **Path of Exile** (Grinding Gear Games — free game, a shop of cosmetics and convenience
such as stash tabs with no power for sale, all expansions free).

## Each weapon and effect as a house shader recipe plus presets

This is where the arsenal is already built for the brief. The house GLSL module library
(`arsenal/web/glsl/`, door `py -m arsenal shader lib`) composes every visual surface from shared
**modules**: a `recipe` is a composite with UI-facing **params** (`[{name, unit, range, default,
uniform}]`), each of which becomes a control on every surface. "Tweak one module and have everything
update" was Daniel's own 2026-10-13 ask for that library.

So a weapon or effect release maps to the house's own grammar:

- **A weapon = a shader recipe + a preset.** The recipe is the visual verb (a chain-lightning arc, an
  orbiting blade, a ground-zone, a pierce trail); the preset is one parameter set. A **free new weapon**
  is then "a new parameter set plus, at most, a new module" (`graphics-vfx.md` §11), shipped as data.
  An **upgrade tier** is a change in a few measured quantities — core brightness, trail length, spark
  count, a colour shift *within the weapon's family* — so each tier reads at a glance; that maps
  directly onto parameterised modules, and it keeps the readability tiers Riot's VFX style guide teaches
  (value/saturation/size by gameplay importance), which matter most in a game where dodging projectiles
  *is* the game.
- **An effect = a status + a visual, both as data.** Status effects (burn, freeze, poison, chain) and
  their visuals live in data files plus shaders (`audio-music.md` §9, `graphics-vfx.md` §11).
- **Sounds as data too.** Each weapon's sound is a preset of a parametric generator (sfxr-style) plus a
  few short samples, so a free weapon ships a new sound as a few bytes of parameters and stays
  stylistically consistent (`audio-music.md` §9). A per-weapon sound kit (fire, travel loop, impact,
  crit, kill, plus shared pickup/level-up/hurt/low-health), each with a priority, an instance limit, a
  variation rule and a loudness target — the Overwatch importance-bucket model so crits and hurt sounds
  cut through arrow spam.
- **Release QC is already a house verb.** Every new weapon's sounds pass a loudness check per category
  (`arsenal.media qc` reads LUFS and true peak), so a free release is never jarringly loud; and the
  shader `card` system renders a test pattern with pass/fail verdicts for each recipe.

The engine and middleware choice (an engine's built-in mixer, FMOD, Wwise, or Web Audio for a browser
build; three.js or any renderer for the visuals) is Daniel's call — the house media-suite ruling stands:
best / most stable / most reliable wins, no forbidden-tool rules.

## What we measure from footage of the genre (our own recordings or public video; never extracted)

Public video is an untrusted sample under the never-on-host rule above (VM work until Daniel rules
otherwise); our own recordings are made record-only (`scrcpy --no-control`, OBS) and measured offline,
never with a live overlay or input on the running game. **Every number measured here is a reference
range, not a target: our tuning is our own design choice, written in the design column.**

Projectile speed in screen-heights per second; projectile size against the player; telegraph time before
an enemy attack; the length of each impact stage in frames; hit-stop length; shake amplitude and decay;
the value/saturation contrast between player projectiles, enemy projectiles and the floor (readability
tiers); and how effects grow with upgrade level. All with the `graphics-vfx.md` rulers (calibrated on a
look we built first) and `games-design-teardown.md`'s arithmetic (DPS×EHP, the stop-to-shoot uptime
factor, Wilson intervals on any counted rate). A legitimate first step is a **play log**: record our
own sessions, frame-step with `arsenal.media`, and log the numbers the UI shows as observations with
frame references.

## What we must never take

The name, characters, art, icons, flipbooks, models, UI layout, ability names and descriptions, sound,
music, and any table of numbers copied from a specific game's files — and the distinctive arrangement
and look of a particular game's screens (*Tetris v. Xio* found infringement in a clone that copied
look-and-feel even though the rules were free). Draw, compose, name and code everything ourselves;
borrow the *idea* of a dash-and-shoot roguelite with an upgrade tree, not the expression. **Distance
check before shipping:** list every mechanic and presentation choice we share with Archero and judge
the whole set together, not one at a time — a game assembled from many individually free pieces of one
original can still read as a copy of its expression (the *Tetris v. Xio* and *Spry Fox v. LOLApps*
courts both weighed what was copied taken together). Patent-search any distinctive, recent mechanic
before shipping. App stores also police copycats.

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
the EU, where a database right can apply). **For this domain:** Habby's terms (last updated
2020-08-20) forbid obtaining "any information" from a Habby game "using any method not expressly
permitted by Habby", so we never open the client. In the US the method of play is free (17 U.S.C.
102(b); the Copyright Office's games page), while a game's rule text, art, audio, UI and distinctive
look are not, and names are trademarks; a distinctive, recent mechanic can be patented. Check
distance against the whole combination of borrowed mechanics and presentation, not one element at a
time (the *Tetris v. Xio* and *Spry Fox v. LOLApps* courts both looked at what was copied taken
together), and app stores police copycats on their own terms. The full map with its caveats is
`method-legal-cleanroom.md`; anything we ship that leans on someone else's product goes past a
lawyer first.

## How this seed connects to the rest of the arsenal

- Design method and the full Archero teardown: `games-design-teardown.md`.
- Effect measurement and rebuilding, the shader-school bench: `graphics-vfx.md`.
- Weapon/effect sounds as data, the game-audio observation kit: `audio-music.md`.
- The clean-room wall for anything built from a reference: `method-legal-cleanroom.md`.
- The house GLSL module library (recipes + presets): `arsenal/web/glsl/README.md`, door
  `py -m arsenal shader lib`. (Another workflow is actively building those modules — do not edit them;
  this seed only points at them.)

## Sources

`research/reviewed/reverse-engineering-2026-10-13/games-design-teardown.md` (§5 the Archero
public-record teardown, §7 the viable-upgrade-path options, the sources), `graphics-vfx.md` (§11 toward
the Archero-style game), `audio-music.md` (§9 ideas for the future game), and the house GLSL library
README. Design precedents credited there: Supergiant (Hades), Mega Crit (Slay the Spire telemetry),
poncle (Vampire Survivors), Grinding Gear Games (Path of Exile), Riot's VFX style guide, the
Deconstructor of Fun and Naavik Archero teardowns. Discipline credited to **morluto/rea**.
