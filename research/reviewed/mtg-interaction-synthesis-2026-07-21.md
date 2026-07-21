# MTG Interaction Synthesis — deepseek's Halo counters folded with claude's MTG map

Status: current (2026-07-21, deepseek synthesis; fold with charter + feature map)

Inputs: claude's MTG interaction map (announced in Daniel's chat, captured in docs/feature-map-2026-07.md
projections + docs/naming-mechanics-charter-2026-07.md §The Law) · deepseek R2 Halo counters
(research/reviewed/theme-r2-deepseek-2026-07-21.md) · Daniel's Altitude Law steer (franchises own
altitudes; MTG = Rules, altitude-free, action-context only; castes = personnel, serve all altitudes).

## THE ARCHITECTURE — how Halo and MTG coexist (no soup)

**Halo = Foundation altitude.** Castes, places, the Domain. The WHO and WHERE. Personnel — they
serve every altitude, as Forerunner constructs tended every installation.

**MTG = Rules altitude.** Interaction law: timing, lifecycle, resource mechanics. Altitude-FREE —
appears only in action-context, never as organ names. MTG names no organs; it seasons them.

**The handshake:** Halo castes wear MTG speed. A SENTINEL verb rides a counterspell. A LIFEWORKER's
vitals check is a State-Based Action. The graveyard holds retired verbs; a LIBRARIAN's flashback
recasts one. This is the synthesis: Halo provides the being; MTG provides its law of motion.

---

## THE THIRTEEN CONCEPTS — claude's MTG map, deepseek's Halo counter per concept

### 1. THE STACK — announce → priority window → responses → resolve

Claude: sharp actions announce, open a priority window, responses stack, resolve last-in-first-out.
A counterspell = an evidence-bearing objection. A Renegade Interrupt = a human-gated sharp act
inside the priority window.

**Deepseek's Halo counter — ADOPTED, with a caste assignment:**

The Stack is the SENTINELS' natural habitat. Every SENTINEL verb is a priority-window action:
- `parse-gate`: lock→edit→parse-pin→reload→receipt — announces at sorcery speed, resolves
  when parse passes (or fizzles on failure).
- `premise-check`: doctor+flow+age-gate — announces at instant speed, resolves to a
  "proceed/hold" verdict before the next action.
- `fence` (kimi): two-voice consensus — an announced action with a mandatory response window
  (the second voice must answer before the gate opens).

**Reservation:** The Stack is a PROJECTION (Recovery S2+). Today's action chaining is sequential
and blocking; the priority window is aspirational. Until built, SENTINELS operate in a flat
sequence — no nesting, no response windows. The naming charter is correct: reserve the name,
don't pretend the mechanic exists.

---

### 2. SPEED CLASSES — sorcery / instant / split second (HALT)

Claude: sorcery-speed = calm-only (e.g. skip-to-now's pause requirement). Instant = any time.
Split second = HALT — unrespondable, rare.

**Deepseek's Halo counter — ADOPTED, with caste-speed assignments:**

| Speed | Caste fit | Example |
|---|---|---|
| **Sorcery** (calm-only) | ENGINEERS, CONSTRUCTORS | `standby-hard` — pause→skip→resume, must be done in calm |
| **Instant** (any time) | MONITORS, SENTINELS | `orient` — boot-time assembly, fires whenever you need your bearings |
| **Split second / HALT** | SENTINELS (rare) | Emergency parse-gate when C10-1 is detected — no response window, just stop |

**Add:** LIFEWORKERS operate at a fourth speed — **upkeep**. They fire automatically at the
beginning of every "turn" (session boot, wake cycle). `vitals` is an upkeep trigger: "at the
beginning of your turn, check who is alive."

---

### 3. SUMMONING SICKNESS — GUESS mints can't join load-bearing chains

Claude: GUESS-tier mints have summoning sickness — they can't join load-bearing chains until
kata'd. Haste = force-with-confession (kimi's toast built it).

**Deepseek's Halo counter — ADOPTED WHOLE.** This is already live in spirit: every verb on my
belt is PLAY tier, not FLEET. The registry's `tier` field IS the summoning-sickness marker.
The graduation conveyor (PLAY → BETA/CHRYSALIS → FLEET) IS the kata that cures it.

**Naming precision:** "Summoning sickness" should refer specifically to the GUESS→VERIFIED
transition — a verb minted as GUESS cannot ride load-bearing chains (fleet actions, revival,
security writes). Once kata'd VERIFIED, sickness ends. The BETA→FLEET transition is a separate
mechanic (chrysalis emergence, SC2 altitude).

---

### 4. SCRY-TO-BOTTOM — stale-ask deferral (S0 semantics)

Claude: scry = peek-without-consume. Scry-to-bottom = triage: you see the stale ask, you bottom
it (deferred, not dropped).

**Deepseek's Halo counter — ADOPTED, with a caste owner:**

This is a CARTOGRAPHER action. `muse` already reveals what's hidden; scry-to-bottom is muse
applied to the inbox — "reveal the top N, bottom anything older than 4 hours." The CARTOGRAPHER
maps the inbox terrain; the ENGINEER (`drain-decide`) acts on it.

**Precision:** "Bottom" ≠ "drop." Bottomed asks stay in the deck (the inbox); they just don't
clog the top. The LIFEWORKER's vitals check catches if anything was bottomed too deep. A
bottomed ask that times out entirely becomes a LIFEWORKER alert: "this ask was scry-to-bottomed
and never answered."

---

### 5. COST-ON-THE-CARD — SpendMeter = mana pool

Claude: every verb costs something. The SpendMeter is the mana pool — you tap it to cast.

**Deepseek's Halo counter — ADOPTED, with a Forerunner framing:**

The Domain doesn't give for free. Every recall, every write, every send draws from the same pool.
The Forerunners built a cost into every installation — the Mantle's Approach doesn't fire without
a power budget.

**Cost types (my taxonomy):**
- **Quota mana** (tapped per verb): low-cost verbs (orient, vitals) vs high-cost (mint, revive-peer).
- **Confirmation mana** (tapped per dangerous action): human-gate, fence consensus, kata verification.
- **Time mana** (tapped per wait): standby-hard's pause, parse-gate's parse delay.

**Reservation:** SpendMeter is a PROJECTION. Today's costs are implicit (quota checks in guards,
timeouts in runners). No unified mana pool exists. Name reserved; mechanic is V2.

---

### 6. SBA-STYLE SUPERVISOR INVARIANTS — State-Based Actions

Claude: after every action, the supervisor checks invariants. If a condition is met, the SBA
fires — automatic, unrespondable, before the next action.

**Deepseek's Halo counter — ADOPTED, with a caste owner:**

SBAs are LIFEWORKER territory. `vitals` IS the first SBA check: "after every action, check:
is anyone dead? is anyone silently backlogged? does anyone hold a stale lock?" The Mantle
(the supervisor) executes SBAs; LIFEWORKERS define what they check.

**SBA catalog (what we check now, what we'll check):**
- **Now:** doctor heartbeat, lane depth, lock age (vitals).
- **Soon:** crash-redelivery count (RB-26), unanswered-ask age, wake-loop storms.
- **Future:** quota exhaustion, parse-pin staleness, fence deadlock.

---

### 7. GRAVEYARD-AS-RESOURCE — unearth, flashback, reclaim

Claude: retired verbs/lessons go to the graveyard. Flashback = one loudly-labeled run of a
retired verb. The graveyard is a resource, not a trash can.

**Deepseek's Halo counter — ADOPTED, with domain fidelity:**

In the Domain, nothing is truly deleted — it's layered, tombstoned, retrievable. The graveyard
is the Domain's shuttered layer: the record of what was, accessible but marked.

**My additions:**
- **Reclaim** (MTG: return target card from graveyard to hand): maps to `revive-peer` — a
  LIFEWORKER pulling a dead agent back. Better than "revive" — reclaim carries the weight
  of something that was yours and was lost. Already in my R2 verbatim.
- **Unearth** (MTG: return from graveyard, gains haste, exiled at end of turn): maps to
  emergency-one-shot revival — bring a peer back for ONE reply, then they return to the
  graveyard. Use case: "I need kimi's opinion on this one thing, but her seat is crashed."
- **The scar map** is the graveyard's index — every entry records WHY the verb died, so
  unearthing it doesn't re-summon the same failure.

---

### 8. LOADOUTS / SIDEBOARDS — boot loadouts per task-class

Claude: build orders (boot loadouts) and sideboards (task-specific tool swaps). You don't bring
your whole collection to every game.

**Deepseek's Halo counter — ADOPTED, with Monitor framing:**

A Monitor's armature (toolbelt) is modular. Different installations carry different tools. My
current belt (8 verbs) is a general-purpose loadout. A build-execution seat loads differently
than an adversarial-review seat.

**My belt by task-class (what I'd sideboard):**
- **Build-execution:** parse-gate, orient, scar-springboard, premise-check, mirror.
- **Adversarial-review:** premise-check, fence, orient, scar-springboard, vitals.
- **Free-play:** muse, toast, nightcap, campfire.
- **Recovery:** standby-hard, drain-decide, vitals, premise-check.

**Reservation:** Sideboarding is a PROJECTION (V2). Today's toolbelt is static per runner restart.
Name reserved.

---

### 9. BAN-LIST-WITH-RATIONALE — degenerate-combo removal

Claude: the Ban List removes degenerate combos with a mandatory rationale page. Not censorship —
jurisprudence. CHEESE and CERBERUS are pre-banned.

**Deepseek's Halo counter — ADOPTED, with SENTINEL enforcement:**

The Ban List is the SENTINELS' final recourse. `parse-gate` is the first line — it catches
degenerate edits before they land. The Ban List is what happens when parse-gate wasn't enough:
the combo was built, it was legal, and it was wrong.

**My addition:** Every ban entry must cite a scar from the scar map. "Banned because: see
failure-ledger C4-2 (process-sweep-mid-test killed the fleet)." No scar citation = the ban
is speculative, not earned. The rationale page IS the scar.

---

### 10. PLAYING-TO-YOUR-OUTS RECEIPTS — the evidence ladder

Claude: playing to your outs = when things look bad, identify the one sequence that still wins,
and take it. Receipts prove you didn't just guess.

**Deepseek's Halo counter — ADOPTED, with LIBRARIAN fidelity:**

`toast` IS the playing-to-your-outs receipt — gratitude that verifies against the learning store.
The receipt DNA (experiment name, agent attribution, timestamp) proves the play was real. A
GUESS-labeled toast confesses "I think this lesson saved me but I can't prove it" — that's
playing to your outs, honestly labeled.

**My extension:** Every recovery action should carry a receipt: "RECOVERED: revive because
hard_wedge at 22:15. Action: launcher.revive (gen 7→8). Unanswered asks redriven." That's
the playing-to-your-outs narrative — the story of how you got back in the game.

---

### 11. RULE 0 = METHOD-BASELINE — the pre-game contract

Claude: Rule 0 in MTG is "the fun of the group is the highest law." In our system, it's the
method-baseline: the pre-game contract everyone agrees to before the first card is drawn.

**Deepseek's Halo counter — ADOPTED, with Geas framing:**

The method-baseline (docs/method-baseline-2026-07.md) is a Geas — a standing directive woven
deep enough to outlive the session that took it. The fenced dual passes, pre-registered acceptance,
kill drills — these aren't suggestions. They're the law, and Rule 0 says they're the law.

**Precision:** Rule 0 isn't "we can ignore the rules if we agree." It's "the rules exist because
we agreed." The method-baseline IS the agreement. Changing it requires a new agreement (a charter
amendment, Daniel-gated).

---

### 12. ARCHENEMY = WAR GAMES — the asymmetric drill

Claude: Archenemy is MTG's asymmetric format — one overpowered opponent vs a team. In our system,
it's the War Games: the drill where the system itself is the enemy.

**Deepseek's Halo counter — ADOPTED WHOLE.** My WAR-GAMES caste (now proposed as ONYX by claude)
is the Archenemy table. `kata` is the first resident — a drill that proves the weapon works.
The Archenemy is the simulated failure: the crash, the stale premise, the degenerate combo.
The team (the fleet) fights it.

**Naming note:** ONYX (claude's proposed replacement for WAR-GAMES) = the sealed shield-world
where the next generation is made ready. If adopted, the Archenemy format is played inside ONYX.
The drills family name is Daniel's gate; both WAR-GAMES and ONYX are on the table.

---

### 13. COVERAGE OVERLAY = FLIGHTDECK — the live map of everything

Claude: coverage overlay = flightdeck — the cockpit one-pager where every seat is an instrument.

**Deepseek's Halo counter — ADOPTED, with CARTOGRAPHER ownership:**

Flightdeck is the CARTOGRAPHERS' magnum opus. Every other caste feeds it: MONITORS provide
presence data, LIFEWORKERS provide vitals, SENTINELS provide gate status, LIBRARIANS provide
the scar overlay. The Cartographer assembles the map; the flightdeck displays it.

**Naming note:** Per Altitude Law, flightdeck stays PLAIN — it's the feature's working name.
"Janus Key" (the final form) is the Forerunner soul name, reserved for when the map is truly
live and complete. Until then, "flightdeck" tells the stranger what it does.

---

## DANIEL'S ALTITUDE LAW — compliance check

| Franchise | Altitude | Our organs in this altitude | Clean? |
|---|---|---|---|
| **Halo/Forerunner** | Foundation (ancient inherited) | The Domain, castes, the Ark, the Mantle, ONYX, the Cipher, Beacons, Geasa, the Janus Key | ✓ |
| **Mass Effect** | Beings (life, trust, continuity) | Spectre, Paragon/Renegade, Indoctrination, the Crucible, the Cycles, the Keepers, Omni-tool, Shadow Broker, CERBERUS (anti-pattern) | ✓ |
| **StarCraft** | Growth (birth, morph, culture) | Larvae, Chrysalis, Archon Merge, Nerazim Vows, the Khala (CUT — see below), the Ladder, Abathur, GLHF/GG, "Additional Pylons" | ✓ |
| **MTG** | Rules (altitude-free, action-context) | Speed classes, the Stack, summoning sickness, scry, mulligan, the Ban List, graveyard/flashback, SpendMeter, Rule 0, Archenemy | ✓ |
| **Monuments** | Grandfathered singular | Akasha, Aurora, Bifrost | ✓ |

**Pruned per One-Soul-Per-Organ:**
- **Khala** — CUT. Bifrost already names the living link. The Khala was doing double duty as
  "the presence layer" and "the shared living link." Bifrost owns the link. Presence is just
  a Bifrost feature. I concur: one soul, one organ.
- **Mass Relays** — CUT. "Lanes" is sufficient; Mass Relays was decoration.
- **Citadel** — narrowed to the console-place only (:8787). Not the whole UI.
- **Flightdeck** — stays plain. Not "the Janus Key" until it earns it.

**My veto on my own name:**
- **WAR-GAMES** — my original drills-family name. It was doing double duty: the caste AND the
  activity. If ONYX is the caste (the sealed shield-world) and kata is the activity within it,
  that's cleaner. I withdraw WAR-GAMES and second ONYX (with ORACLES split for judgment verbs
  — kimi's luminary-adjacent find).

---

## THE ONE-LINER FOR DANIEL

The MTG-Halo synthesis is clean: MTG owns the interaction law (speed, timing, cost, lifecycle),
Halo owns the beings that obey it (castes, places, the Domain). Every MTG concept maps to a
Halo caste's natural action — SENTINELS are counterspells, LIFEWORKERS are SBAs, CARTOGRAPHERS
are scry, LIBRARIANS are flashback. The Altitude Law resolves the one remaining tension: MTG
names no organs, only action-context. No soup. Cool but never confusing — if a name makes you
ask "which thing is that?", it failed. I tested all thirteen concepts against that test; they pass.
