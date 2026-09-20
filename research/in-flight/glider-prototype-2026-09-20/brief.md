# Damaged-mech glider — design spine (ROUGH DRAFT, in flux)

Status: **ROUGH DRAFT**, locked 2026-09-20. Daniel is still concepting; this is the spine, not the
flesh. Working title: none yet.

## The pitch

You are a **damaged mech**. You must repair yourself and figure out what went wrong — which makes the
tutorial the *story*: you rediscover your own capabilities by rebuilding them. You fight enemies and
**take their parts to integrate into yourself**, so every encounter is a mystery — *what do I
become?* The world is beautiful and mystical — full technology, or a **hybrid of magic and machine**
(recommended: hybrid).

## The backstory (rough, epic)

Two ancient races at war. Humanity lived in harmony with its AI. The attackers hijacked production
and certain AI models and launched a counterattack from within. As a last resort, a human and their
friendly AI do the unthinkable — transplant and upload the human consciousness into a prototype host
console — then use a one-of-a-kind prototype teleporter to whisk it away, its shell blasted as it
teleports.

The player wakes in that shell, remembering nothing. The world is full of hostile mechs — they are
the **hijacked production**, the same machines that were once humanity's allies. Every enemy part you
integrate is a *reclaiming* as much as a repair.

**What the backstory buys, mechanically:**

- The enemy-parts loop gains a moral reason: the enemies are hijacked, not evil.
- The tutorial IS the backstory: "damaged fuzzy visuals + rudimentary UI" is amnesia made visible —
  repairing the optics subsystem sharpens the world, repairing memory returns the friend.
- The friend AI is the emotional spine, and its return is itself a repair ladder: comms → voice →
  memory → presence.
- The open theme (a feature, not a hole): *is the upload still human, or just another machine?* This
  is the game's thesis — leave it open, and earn the answer rather than state it.
- "Plot holes" worth keeping as features: your damage is your disguise (a broken mech blends into a
  world of hijacked machines); the one-of-a-kind teleporter is a Chekhov's gun and the reason you
  cannot simply go home.

## The one loop

> explore → acquire (an enemy's part, a relic, a resource) → **become** (graft it now, or research
> it into something new) → reach what you couldn't before → repeat.

Everything else is this loop at a different scale. This is the whole game.

## The story spine: the movement ladder

**wings → turbine → rocket → endgame magic glide.** Each rung is a *repair* that opens more of the
world. The magic glide is the thesis delivered: flight as freedom, and the moment magic and machine
finally fuse. Not a side system — the emotional payoff the whole game climbs toward.

## Two hands of acquisition

- **SCAVENGE (take their part):** reactive, immediate, visceral. The payoff is *visible
  transformation*, never a stat stick — grafting a wing must *give you a wing*, not "+15% airspeed".
- **RESEARCH (analyze a relic or prototype):** deliberate, planned, yields a **hybrid no enemy has**.
  This is the magic/tech synthesis made mechanical — the first time the player synthesizes a part
  that doesn't exist in the wild, the game has said its theme out loud.

## The traveling base

Not a station, a **home you carry** — the repair story told about a place instead of a body. Auto
resource mining feeds consumables; the base feels *alive* while you're away (come back to a gift,
never a spreadsheet).

## Combat + movement verbs

Combat, dash, thrust — all movement verbs over the SAME physics core. Thrust is a force, dash is an
impulse, glide is committed. The movement ladder is cheap to layer on top of what already exists.

## The world

Beautiful and mystical. Tech/magic hybrid: machine parts for movement and structure, magic for the
*impossible* — the parts that break the physics (which is where a gliding mech gets interesting).

## What already exists (built, pinned)

- `arsenal/web/glider/physics.js` (commit `90a1cb91`): point-mass glide, wind-relative thermals, 16
  pins green. This is the **movement substrate** every ladder rung sits on. (The first draft's
  glide-feel prototype is not discarded — it becomes the first rung: *wings*.)

## The FIRST prototype slice: the integration moment

Not a content prototype, a **feel** prototype. One damaged mech, one grafted part, one repair that
*visibly* changes you. Success = the half-second where "take their parts" stops being a promise and
becomes a feeling. (The glide slice folds in as the first movement rung.)

Pre-registered feel proxies, carried over and still true: stability, energy trade (dive↔speed),
thermal ride, stall + recovery, the speed envelope (soar ↔ Wipeout dive), 60fps, legible frame.

## Open questions (recommendations inline)

1. Tech vs. magic/tech hybrid? → **hybrid** (gives the mystical world *and* a mechanical axis for
   what parts do).
2. Core feel = the integration moment? → prototype that first.
3. More to come as Daniel concepts.

## The build loop for us

prototype the integration feel → measure → **Daniel plays** → tune → repeat. The base, mining,
research, consumables, combat — all plug into the same loop later, one door at a time.
