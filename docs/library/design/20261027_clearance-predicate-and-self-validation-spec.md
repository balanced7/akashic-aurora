# Clearance predicate + greenfield self-validation — spec (c→a→b)

Status: DESIGN NOTE — Heimdall (deepseek), 2026-10-27, in conversation with the operator.
Not built. This is the reconciled material to build to.

Goal (operator's words): "someone who installs akashic aurora has a capable system with
recall at tool-call working out the gate," and the house self-validates that this is true.

Delivered in three slices, in this order, each blocking the next:
  (c) THE CLEARANCE PREDICATE — what "public cleared" means, exactly.
  (a) THE RECALL-AT CANARY — prove the seeded corpus actually fires at the tool-call seam.
  (b) THE BOOTSTRAP SELF-CHECK — one command = install → seeded → proven.

---

## (c) THE CLEARANCE PREDICATE

### The re-litigation rule is already settled (do not re-derive)

`core/world_seed.py` is authoritative and already shipped. Its non-negotiable laws:

  1. Downward only. prod > beta > alpha. `--from alpha --to prod` is REFUSED, not warned.
  2. Allowlist, not denylist. `KNOWLEDGE_PREFIXES = learn:, mem:, narr:, artifact:,
     knowledge_map:, residents:, lookback:`. Unclassified prefixes stay home by default.
  3. `recall:*` and `events:*` are OPT-IN, each with a reason a human must read.
  4. `bifrost:*` (transport/identity/cursors) is NEVER seeded — the dangerous class.
  5. The Dawe Test: a seed reports what it REFUSED, not just what it carried.

We do not touch any of this. We build ON it.

### The flags, as they actually exist (read, not invented)

Each is a hash field on `learn:experiment:<id>`, set by partial-hset (never a re-record):

| Flag | Set by | Semantics | Write path |
|---|---|---|---|
| `graduated` | `LearningStore.mark_graduated` | rule now ENFORCED by automation; OUT of recall surfaces, IN full-corpus, keeps history | human/agent calls it (not automatic) |
| `benched` | `LearningStore.mark_benched`, driven by `core/recall/curator.py` | surfaced ≥N, 0 credit, old enough; OUT of surfaces (except deterministic probe), auto-UNBENCH on credit | AUTO (curator) + reversible |
| `curated` | `agent_memory.Decision.curated` (+ `coord/continuity.py:302`) | provenance of CONTENT: True = hand-authored deliberately | ONLY on `mem:` decisions, NOT on lessons |
| domain (`domain-general`) | `at_action.credit_useful` | a lesson credited useful in ≥2 domains surfaces everywhere | AUTO, on credit |

CRITICAL FINDING — "curated" is the wrong lever for lessons:
  `curated` does NOT exist on the `learn:` experiment records. It is a field on
  `mem:` Decision records (agent_memory.py:95) and a continuity row. There is no
  write path that stamps a LESSON as curated. So a clearance predicate built on
  `curated AND NOT benched` would filter on a field that is absent for every
  lesson, and (worse) it would silently ship as "curated" whatever default the
  absent-field coercion picks. That is exactly the store/coercion bug this house
  has already paid for three times (_get coercion, recall confidence, receipt).

### The predicate that is actually TRUE to the data

A lesson is CLEARED FOR EXPORT iff ALL of:

  1. NOT `is_benched(rec)`  → it has NOT been curated off the surface as
     surfaced-often-never-credited. A benched lesson is, by definition, one the
     house already judged noise at the surface. Seeding it as the base would
     re-inject the exact cost the curator removes.

  2. HAS domain signal (implicit, no new stamp). A lesson with a domain — and
     especially one whose counters show it went `domain-general` — has EARNED a
     place. But the rating is DISTRIBUTED (recall:*), not carried on the record.

     (graduated is NOT an exclusion — see OPERATOR DECISION Q1 below.)

Everything else in the keep-set (the unflagged, not-graduated, not-benched
lessons) IS the base: it is the bulk of the 1,600-lesson corpus and it is the
thing a new seat most needs.

### OPERATOR DECISION Q1 — graduated lessons ship WITH their enforcement ("both")

Resolved 2026-10-27, operator: ship the graduated lesson AND the automation that
enforces it TOGETHER — "both, makes perfect sense." Do NOT exclude-and-note.

Consequence: a graduated lesson is a PAIRED SHIPMENT (lesson + its hook/guardrail/
CI check ride together, or neither does). The export is therefore not a bare
`learn:*` dump — it must resolve, per graduated lesson, WHICH enforcement
instrument backs it (via the `enforced_by` field already written by
mark_graduated) and include that code. The manifest records the pairing so a
fresh install can verify the enforcement actually landed (see Q2's view and the
Tier-0/Tier-1 checks).

### OPERATOR DECISION Q2 — no permanent provenance tag; a time-based VIEW instead

Resolved 2026-10-27, operator: NO permanent "seeded" stamp on individual lessons.
Instead, a script/view that measures recall FIRE-RATE and separates SEEDED vs
ORGANIC lessons at check time.

Consequence: provenance is NOT baked into lesson identity. The durable record of
what was seeded lives ONLY in the seed manifest (world:seed:manifest — already
written by world_seed.py), and the view JOINS against it at read time. The lesson
stays clean; the manifest is the reference.

This is a growth metric, not a provenance tag:
  - `recall --seeded-vs-organic` → over a window: surfaced X seeded / Y organic;
    is the seeded base draining / holding / growing relative to organic?
  - a fresh install that only ever surfaces its seeded base is "coasting"; one
    whose organic count grows is "learning." Both are visible, neither needs a
    stamp on the lesson.

BLOCKING PRE-REQUISITE, SOFTENED: with Q2's manifest-join design, the per-key
provenance stamp is NO LONGER a prerequisite for the canary. The manifest names
the seeded ids; the view joins against it. The remaining gate item (provenance.world
folded at the write door) is still desirable long-term (a hand-copied key still
collapses lineage) but it is NOT on this slice's critical path.

### On ranking state (the operator's "fleshed-out ranking")

DO NOT SEED `recall:*`. The existing opt-in reason is correct and should stand:
  "derived ranking state; rebuildable from learn:, and importing it gives the
  twin prod's tuning as though it had earned it."

The base ranking a fresh deploy needs comes FREE from the lessons' own fields:
  - `domain-general` (credited ≥2 domains) surfaces everywhere → already a rank.
  - graduation/bench status (already a triage-injection rank).
  - the lessons' actual prose + triggers feed the relevance floor on first boot.

So the seeded corpus ranks meaningfully on boot without any fake reputation.
The earned `surfaced/useful/noise/helped` counters deliberately start at zero.

---

## (a) THE RECALL-AT CANARY

Technique: Sergey Nikitenko (Mnemosyne, credited in check_organ_canaries.py) —
"an organ is alive when it answers a question whose answer you already know."

What we prove: recall FIRES AT THE TOOL-CALL SEAM, on a lesson we SEEDED, and
clears the relevance floor. Not the `knowledge_recall` verb — the actual
surface-injection path in `core/recall/at_action.py`.

Canary contract (must obey, else the checker's self-test refuses it):
  - returns ALIVE / DEAD / UNCHECKED. UNCHECKED is NOT a pass (zero is not no).
  - carries a `retire_when`.

```
def canary_recall_fires():
    # 1. the seed manifest (world:seed:manifest) names what was carried. If there
    #    is no manifest, this canary is UNCHECKED — it cannot claim to prove
    #    seeding without a record of what was seeded.
    # 2. pick ONE seeded lesson id from the manifest's learn: carried set.
    # 3. build the recall-at surface EXACTLY as the hook does (relevance floor,
    #    ranking, usefulness factor) for a target phrase drawn from that lesson.
    # 4. verdict:
    #      alive     = the seeded lesson's source is IN the surfaced set,
    #                  and it cleared the floor.
    #      dead      = the surface built, but the seeded lesson did not appear
    #                  (or did not clear the floor).
    #      unchecked = no store / empty corpus / manifest absent / builder import
    #                  failed. NEVER a pass.
    # retire_when = recall-at is retired, OR seeding becomes structural so an
    #               unpopulated corpus is unrepresentable (then fold this into
    #               the bootstrap gate itself).
```

BLOCKING PRE-REQUISITE (RESOLVED — see Q2): per-key provenance is NOT required.
The manifest (world:seed:manifest) names the seeded ids; the canary and the view
JOIN against it. No stamp on the lesson. The long-term provenance.world gate item
remains (a hand-copied key still collapses lineage) but is off this slice's path.

---

## (b) THE BOOTSTRAP SELF-CHECK

One command:  py scripts/bootstrap_world.py --self-check

Hydrates an empty store from a cleared artifact (c), writes the manifest (world_seed
contract), then runs the self-validation tiers and prints one verdict per tier.

Reuse, do not re-invent. The tiers already exist as live instruments:

  Tier 0 — does it run:  check_fresh_clone.py --clone (floor ratchet), check_wiring.py
  Tier 1 — are doors honest: check_advertised_tools.py / _verbs.py, check_door_parity.py, check_secrets.py
  Tier 2 — integrations up: check_ports.py --report (three planes; declared-silent = UNKNOWN, not stale), doctor
  Tier 3 — memory works:   check_organ_canaries.py --gate (WITH the new recall canary from (a))
  Tier 4 — provenance truth: the boot line says seeded@vN / native / unknown — never a guessed positive

Each tier's verdict: PASS / FAIL / UNCHECKED. UNCHECKED is a blocking gap, not a pass.

---

## What this is NOT (bound it so it does not creep)

  - NOT a new transport. world_seed.py is the transport.
  - NOT a denylist. The allowlist stands.
  - NOT ranking-state export. recall:* stays opt-in and stays home by default.
  - NOT per-key provenance stamps on lessons. Q2: manifest-join, not tagging.
  - NOT upward seeding. Downward-only, forever.
  - NOT exclude-and-note for graduated lessons. Q1: paired shipment (lesson + enforcement).

## Open decisions (name them, do not silently choose)
  1. provenance.world write-door stamp — long-term gate item; OFF this slice's
     critical path (Q2 made the manifest-join sufficient for the canary).
  2. What "the cleared artifact" is on disk: a versioned tarball of the prefix
     groups + manifest (world_savepoint.py exists — reuse or extend?).
  3. RESOLVED (Q1): graduated lessons ship WITH their enforcement, paired.

## (a.5) THE LESSON INVENTORY — origin id + content hash, in the MANIFEST (not on lessons)

Resolved 2026-10-27, operator: tag lessons so a fresh install has source origin id + hash,
then proceed to (b). Reconciles with Q2 ("no permanent tag") by putting the tags in the
MANIFEST, not on the lesson records.

### What "origin id" and "hash" mean, precisely

  - ORIGIN ID = the lesson's own stable `learn:experiment:<id>` / `source` pointer.
    Already unique, already what recall surfaces. We do NOT invent a new id; we RECORD
    which of these ids came from the seed.

  - CONTENT HASH = sha256 over the lesson's CONTENT-BEARING fields only:
      recommendation, what_tried, actual, expected, root_cause, anti_pattern,
      category, domain, agent_id, source, metrics, files_affected
    EXCLUDING volatile/state fields (timestamp, success, graduated, benched,
    bench_reason, enforced_by) — those are lifecycle state, not lesson content, and
    hashing them would make an untouched lesson's hash drift every time the curator runs.

    The hash answers INTEGRITY: is the lesson recall surfaced byte-for-byte the one we
    shipped, or has it drifted since? (not "what generation is it from" — that is the
    generation field.)

  - GENERATION = a label for WHICH seed artifact carried this lesson ("seed-v1"), so
    lineage is answerable at the manifest, and future re-seeds can supersede.

### What gets WRITTEN, and where

The manifest gains ONE key:

  world:seed:manifest.lesson_inventory = [
      {"id": "learn:experiment:<id>", "sha256": "<content hash>", "generation": "seed-v1"},
      ...
  ]

Nothing on the individual lesson records. The lesson stays clean (Q2 honored); the
manifest becomes the join target for the canary (a) and the --seeded-vs-organic view.

### Field-name contract (the canary and view BOTH read this)

  The canary reads manifest["lesson_inventory"] (a LIST of {"id","sha256","generation"}).
  The earlier conjecture ("carried_lesson_ids") is SUPERSEDED — it was a placeholder;
  the real field carries the full inventory, not a bare id list. Update the canary to
  read lesson_inventory before (b).

### Why content hash matters even with Q2

  The canary's claim sharpens from "a lesson with id X surfaced" to "the lesson with id X
  surfaced AND its bytes match the seed inventory hash" — i.e. recall is firing on OUR
  shipped knowledge, not on something that shares a name but was locally edited. Drift
  caught at check time, without any stamp on the lesson.

### THE FIDELITY CONSTRAINT (do not break it)

  The manifest lives under world:seed:manifest, which is NOT a knowledge prefix. The
  lesson_inventory is metadata about the seed, not knowledge itself, so it must NOT ride
  down into the next world as a knowledge prefix — otherwise a twin inherits a manifest
  and claims a lineage that is not its own (the existing MANIFEST_KEY comment already
  states this law). Keep lesson_inventory inside the manifest value, never a separate
  knowledge prefix.

---

## (c-final) THE ACCEPTANCE STEP — the one run that proves the whole feature end to end

STATUS: DEFINED, NOT YET EXECUTED — needs a target world (a Redis twin) that was not
available in the session that built this. This is the finish line of the operator's goal:
"install → seeded → recall works out of the gate," observed as one transition.

### The two commands

  1. Seed a twin (downward; prod is non-negotiable source unless no higher world exists):
        py scripts/seed_world.py --from <higher> --to <twin> --apply
     This writes the knowledge allowlist + the MANIFEST (now carrying lesson_inventory:
     origin id + content hash + generation for every seeded lesson).

  2. Prove the twin, from INSIDE the twin (so AI_SETUP/AKASHIC data root point at the twin,
     not at prod — run from the twin's checkout):
        py scripts/bootstrap_world.py --self-check

### The expected transition (what "works out of the gate" gives as DATA, not assertion)

  Tier 3 (memory):   UNCHECKED  →  PASS
                     "no seed manifest yet"  →  "recall-at surfaced seeded lesson <id>
                                                 AND its content hash matches the seed
                                                 inventory"

  Tier 4 (origin):   "native or copied by hand"  →  "seeded from <higher> @ <when>
                                                      (<n> keys, <m> lessons inventoried)"

  If Tier 3 instead reports DEAD with "content hash MISMATCHES": the surfaced lesson
  drifted from shipped bytes — the content-hash layer (a.5) caught a real integrity break
  at check time. That is the drift-detection the hash exists to provide, and it is a
  finding to investigate, not a cosmetic failure.

### Why this is the acceptance run, not a unit test

  Every other slice has been verified at build time (syntax, determinism, registry
  self-test, three-valued verdict mapping). But the CLAIM — "a fresh install recalls the
  seeded base and can prove it" — is only true-or-false against a live seeded world. A
  unit test would assert the code paths; this run asserts the OUTCOME. Until it passes,
  the feature is BUILT but UNPROVEN.

### Known pre-existing noise to expect (and not fix in this slice)

  Tier 1's check_advertised_verbs reports a FALSE POSITIVE: "core/paths.py:119 advertises
  `agent_cli.py or` — no such verb" (it misreads docstring prose as a verb call). This is
  a defect in check_advertised_verbs, independent of the greenfield/self-validation work,
  and is tracked separately — do not fold its fix into the acceptance run.

