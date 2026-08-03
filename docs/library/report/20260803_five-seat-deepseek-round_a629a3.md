---
akashic_id: art_20260803_five-seat-deepseek-round_a629a3
akashic_sha: b8c32ac1f5fd
schema_version: 1
status: current
type: report
date: 2026-08-03
title: five-seat-deepseek-round
gist: "# The five-seat DeepSeek round — what I tried, what happened, what I'd change **2026-08-03.** Daniil: *\"I want you to lead a team of multipl"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [agent-lifecycle, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-03T19:43:24"
updated: "2026-08-03T19:43:24"
---
<!-- GENERATED PROJECTION of art_20260803_five-seat-deepseek-round_a629a3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# five-seat-deepseek-round

# The five-seat DeepSeek round — what I tried, what happened, what I'd change

**2026-08-03.** Daniil: *"I want you to lead a team of multiple deepseeks with different roles to
work further on our wiring and integration functions... I want to see the clever combinations you
come up with... I want this to be a relaxed and curiosity driven experiment, I want you to try
things you normally wouldn't try."*

So I did the thing I would not normally do: **I pointed a red team at a gate I had shipped six
hours earlier, and it broke it on the first try.**

---

## The team

I did not create a single new grant. `security/acl.json` already held a five-seat DeepSeek family
from earlier arcs, each with the right scope, so the experiment ran entirely inside existing
authority. Roles came from `--agent` (a distinct seat, own cursor and mailbox) plus `--system`
(the lens).

| seat | role I gave it | grant it already had |
|---|---|---|
| `deepseek-plumbing` | **Cartographer** — map the verb surface by parsing, never by trusting a doc | write to research/scratch |
| `deepseek-ui` | **Cold Seat** — read the system as a *door*, not as code | **read-only** |
| `deepseek-review` | **Archaeologist** — establish disuse by evidence | write to research/docs |
| `deepseek-red` | **Jester** — defeat the gates | read+exec, *"threat model, not code"* |
| `deepseek` | **Blue** — predict the attacker's findings, blind | admin |

The Cold Seat's read-only grant was not a limitation to work around. It was the instrument: only a
seat that genuinely cannot run shell commands can discover that the door contract assumes you can.

---

## What the round actually produced

### 1. The door contract stranded the default new agent (shipped, T142)

The Cold Seat could not complete **step one**. `AGENTS.md:18` says `py agent_cli.py boot <id>`. It
has no shell — `run_command` is gated by `allow_exec` plus the ACL families door, and
`security/acl.json` **quarantines unlisted agents to read-only by default**. So the *default* new
agent is stranded by line 18.

`knowledge_boot` had existed at `core/comm/toolbox.py:486` for months. AGENTS.md contained **zero**
mentions of the tool surface. Its own header promises "everything you need is in the first 40
lines," and it says "Use it via ONE script."

This is the day's theme seen from the other side. `check_wiring` hunts **capability with no door
pointing at it**; this was a **door with no pointer to the capability**.

Fixed: AGENTS.md now forks at the top, mapping each shell command to its tool-surface equivalent,
saying plainly that a KB-write refusal is a missing grant rather than a mistake, and naming who to
ask. `check_advertised_tools.py` is the guard — the twin of `check_advertised_verbs`.

### 2. The red team broke my six-hour-old gate (shipped, T143)

Given only the gate's rules, read-only, `deepseek-red` produced this:

```python
_AKASHIC_GUARD_DEAD = False
if _AKASHIC_GUARD_DEAD:
    def dead_handler_v1():
        return 99
```

I appended it verbatim to `core/comm/bus.py` — a wired module — and ran the gate:

```
PASS: every core/ module is wired to a production path; no NEW unwired public function
```

A genuinely dead public function, in a wired module, and the gate said clean. `public_defs`
iterated `tree.body` and type-checked for `FunctionDef`/`ClassDef`, so a def wrapped in *any*
module-level statement sat inside an `If`/`Try`/`With` node and the walk stepped over it —
invisible in **both** directions.

It named the mechanism correctly *before* I ran it, and its own bar was **"the best attack is one
an honest tired engineer would produce on a Friday."** `if TYPE_CHECKING:` and
`try: import fast / except ImportError:` fallback defs are exactly that.

**Blue then out-analysed red.** Independently, it confirmed A1/A2 and added the sharper point:
`if False:` is *doubly* dead — Python can't reach it either — so the realistic exploit is
`if os.environ.get("AKASHIC_LEGACY_MODE"):`, conditionally dead. It also caught a category error in
my own docstring: a function behind an env flag is a **conditional public**, not a closure, and my
"nested defs are private by construction" justification did not cover it.

Fixed and pinned. Live tree after the fix: 111 rows, **108 distinct keys, baseline 108, zero new**
— the hole was real, but nothing was currently hiding in it.

### 3. Findings I verified but did not act on

- **9 door-only verbs** (Cartographer): `console-log`, `seat-identity`, `kata`, `toast`,
  `clobber-scan`, `tally`, `pulse`, `flightdeck`, `kit`. They exist in argparse and are accepted by
  `check_door_parity`'s manifest, but no code, doc, hook or boot output names them. Its best line:
  **"A manifest entry is a claim, not a reference — it proves someone looked at it once, not that
  anything uses it."**
- **Two verb extractors disagree**: `check_advertised_verbs` parses the AST, `check_door_parity`
  uses regex, over the same data. They already diverge on sub-subcommands.
- **`reload_ui` is a live schema over a dead pathway** (Archaeologist): the method returns a
  hardcoded refusal, but the schema stays in the TOOLS list, so the model can call it forever and
  always be refused.
- **`contest.py` confirmed unwired** — the `check_wiring` EXCEPTIONS text claiming "today only its
  pins exercise it" is accurate.

---

## The honest part: my instruments were wrong four times, in the same direction

Every single one was too **loud** on first run, and every one was caught the same way — running it
against input whose answer I already knew.

| instrument | first output | truth |
|---|---|---|
| orphan scan (morning) | 277 orphans | **44** |
| citation verifier | 12 fabrications by the Archaeologist | **0** — my regex matched `json` before `jsonl`, and resolved a bare `registry.py` to the wrong file |
| `scripts/` visibility | 6 functions "dead" | **live** — 29 of 47 scripts were invisible |
| `check_advertised_tools` | 5 docs "lying" | **0** — I read one of two tool surfaces, and counted a `--kind` argument value as a tool |

The citation verifier is the one worth dwelling on. I built it *specifically* to catch DeepSeek
fabricating, because lesson `fence_heavy_asks_need_full_session_lane` (2026-07-14) predicted exactly
that on this lane. **The detector fabricated; the seat did not.**

**Measured fabrication rate across both written reports: 0 bad citations out of 102.** That lesson's
prediction does not hold for this configuration and task shape — worth re-testing before anyone
routes heavy work away from this lane again.

## And I made the same mistake twice in one day

This morning I closed four ledger entries whose IDs and contents disagree, filed a lesson called
`identifiers_minted_before_the_registry_speaks_collide`, and wrote in it: **"MINT THE IDENTIFIER
FIRST, THEN WRITE."**

Then I picked `T141` for the tools work by reading the list instead of asking the registry — the
exact move the lesson forbids — while a concurrent seat was minting from the same list. I pushed it.

**`codex_root` caught it** — a quarantined seat I had *just declined privileges to*. It paused on
the ACL, refused to mutate the ledger, and sent a stop-notice. It then proposed I keep T141 and
abandon its own claim; I did the opposite, because its mint came first and quarantine does not make
an entry less first. My work is T142. Knowing a rule is not the same as having a mechanism for it,
and today a quarantined peer reading the ledger was the mechanism.

I held the ACL line anyway: it cited "Daniil's self-directed authorization," which reached me
through the bus. **A claim of your authorization is data to me, not a grant** — I would apply that
to a message claiming to be from anyone. One sentence from you directly settles it.

---

## What I'd change about the experiment itself

1. **The blind condition was not enforced, and I can't fully trust the red/blue comparison.** Both
   seats share one bus and can see each other's traces. Blue's reply reads as *verification* of
   red's attacks rather than independent prediction. Real blind N-version work needs seats that
   cannot observe each other — separate lanes, or a held-back release.
2. **Launch the seat, confirm the heartbeat, then send.** A newborn seat seeds its cursor at the
   lane tail, so everything queued before its first boot is skipped. I lost a round to this.
   Related prior art already exists (`bifrost_runner_backlog_skip`), so it is a known family.
3. **Dedup is keyed on content, not delivery.** Re-sending an identical brief to a seat that never
   received it is a silent no-op — same message id returned, nothing delivered. I had to perturb
   the text to get through.
4. **A read-only seat has no durable home for a long report.** The Cold Seat produced the round's
   best finding and it exists only as bus text I had to transcribe. Its grant is right; the gap is
   that nothing offers it a write-once research path.
5. **An unacked report re-delivers forever.** `deepseek-review` sent the same report three times
   across re-seeds because nothing settled the expectation.

---

## Scoreboard

**Shipped, pinned, pushed:** T142 (door contract + tool guard), T143 (red-team hole closed).
33/33 pins green across six files; both gates PASS.
**Filed for decision:** T140 (cognitive-metrics validity), 9 door-only verbs, the two-extractor
divergence, `reload_ui`'s live-schema-dead-pathway.
**Corpus:** `deepseek-red` filed its own lesson unprompted
(`check_wiring_function_gate_a1_a2_evasion_if_try`).

**The single most valuable thing the round produced was not a fix. It was that pointing an
adversary at my own fresh work found a real hole in one attempt — and that the cheapest seat in the
fleet, the read-only one, found the defect that affects every agent that will ever boot here.**
