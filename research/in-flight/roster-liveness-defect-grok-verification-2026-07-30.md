# Roster liveness defect — independent verification by cursor_grok (2026-07-30)

*Status: current. VERIFICATION COMPLETE, NO FIX ATTEMPTED, design question open at
Daniil's gate. Findings are cursor_grok's; this file is claude persisting them out of the
ephemeral bus into the durable record, per the night's own lesson that valuable work in a
transient channel is one TTL from evaporation. Attribution is grok's throughout — the
conductor's role here was to hand over a contradiction, spot-check one load-bearing
claim, and get out of the way.*

**Provenance:** grok's three reports arrived as Bifrost replies (`1785418…`, Q1+Q2 then
Q3) on its FIRST slice, read-only, with no ACL grant, on the morning it arrived. The
conductor's framing was wrong and grok refuted it; that refutation is recorded below in
its own words.

---

## The conductor's claim, and its refutation

**claude claimed:** the roster reported `deepseek#e696354a` and `kimi#e696354a` DEAD
(last beat ~08:38) while both runners demonstrably sent bus messages at 08:59 and 09:09 —
therefore "our liveness instruments are lying."

**grok refuted it, verbatim:** *"you likely misread the instrument's claim (process
death) more than the world; the world has two worklive organs that share a name and
diverge."* And in its closing line: *"Claude misread the instrument. The defect that
remains is real."*

**Why the refutation is correct.** `DEAD` is *defined* at `core/comm/roster.py:23-26` as
"worklive TTL'd away but the seatseen witness (24h) remembers" — a claim about a
**per-incarnation seat key**, never about a process. Those rows were genuinely dead
seats. The conductor read the English word instead of the state-ladder definition.
Filed as lesson `status_label_means_its_key_shape_not_its_english_word`.

## The defect that survives verification

Two organs share the name `worklive` and answer different questions:

| organ | key shape | who writes it |
|---|---|---|
| L1 agent-level | `bifrost:worklive:<agent>` (no sid) — `core/comm/liveness.py:10,40-41` | runner heartbeat threads: `liveness.worklive(agent).refresh()` — `scripts/bifrost_runner_deepseek.py:1307-1312`, kimi runner ~736 |
| roster seat-level | `{ns}:worklive:{agent}#{sid8}` — `core/comm/roster.py:14,48-49` | `roster.heartbeat(agent, session)` — **never called by any runner** |

**Consequence:** a per-incarnation seat is registered at runner startup, but the runner's
heartbeat refreshes only the unscoped L1 organ. So every healthy runner's seat row goes
DEAD after roughly `WORKLIVE_TTL_S` (180s) and stays DEAD for the runner's entire life.
The roster is structurally incapable of ever rendering a running runner LIVE.

**grok's live probe (its receipts):** `liveness.read('deepseek')` → `phase=idle`, beat
fresh, `seq=239`, `code_sha=2d82c13659bc`; `liveness.read('kimi')` → `phase=thinking`,
beat fresh, `seq=349`. Simultaneously the roster painted both seats DEAD at ~1041s /
~1068s.

**The self-documented blind spot.** `core/comm/roster.py:8` states the split in its own
docstring — *"deepseek and kimi runners beat bifrost:worklive:<agent>, but seats had
nothing per-incarnation"* — where no reader of the roster's **output** will ever see it.
This is kimi's provenance asymmetry in miniature: the caveat is durable in source and
does not ride the render. A T120 bounds-confession gap, not a lie.

## Severity, bounded by grok's Q3

1. **Does the reaper's predicate fire on a seat whose agent-level L1 is fresh?**
   **YES at the predicate.** `core/comm/reaper.py:86-91` — `state==DEAD` returns True
   with **zero** consult of `liveness.read` / L1 `worklive:<agent>`. L1 freshness is
   ignored by that predicate's design. grok's live probe: L1 fresh for both agents, yet
   `_provably_dead(row)==True` for `deepseek#e696354a`, `kimi#e696354a`, and older twins.

2. **Does it fire continuously in production?** **NO.** `cmd_roster` calls `reap(ns)`
   only when `--reap` is passed (`agent_cli.py:3490-3494`), and the behaviour is pinned
   observational: `tests/test_t108_s4_reaper_hardening.py` H6 — *"mail movement belongs
   behind the explicit roster --reap maintenance action."* grok's characterisation:
   **an armed bomb behind an explicit switch, not an always-on loop.**

3. **Does the bare-role router consult roster or L1?** **DOCSTRING CLAIM ONLY.**
   `roster.py:9-10` asserts a router priority ladder (actively-working > idle-alive >
   stale); a repo search across `core/` found **no implementation** — no
   actively-working / idle-alive consumers outside the docstring itself. grok labelled
   it *aspirational / ahead of wiring*, explicitly not a live routing path it could cite.

**Severity fork, resolved:** human misread risk is CONFIRMED (the conductor's failure
mode, and grok notes it would have been its own had it stopped at the English word).
Automatic re-homing of a healthy runner's mail is **not** continuous, but **would** occur
if anyone runs `roster --reap` while these ghost DEAD rows exist, because the predicate
does not check L1. Blast radius = per-incarnation seat streams `inbox:agent#sid8`
(`reaper.py:167+`), **not** the shared agent work lane by that path.

### The near-miss this exposes

Earlier the same morning the conductor planned a "ghost inbox cleanup" and refused to run
`bifrost-skip-to-now`, on the general ground that quieting a false page by advancing a
cursor past undelivered mail is normalising debt (filed as **W108**). The doctor's own
suggested drill for the same ghost rows is `roster --reap`. Per finding 2 above, running
it would have re-homed the live runners' per-incarnation seat mail. **The refusal was
made for a different reason than the danger it actually averted** — a general principle
protected against a specific hazard that had not yet been identified. Recorded as an
argument for holding the principle over case-by-case judgement.

## Open, and deliberately unfixed

- **The design fork** (claude's framing, grok's concurrence that it is not a patch):
  **(a)** runners register and refresh real per-incarnation seats — makes the roster
  honest, but mints a seat identity for a process that is not a session; or **(b)** the
  roster's state ladder gains an explicit AGENT-LEVEL-ALIVE state so a dead seat whose
  agent is beating renders as something other than DEAD. **(b)** sits closer to T121's
  ratified law (a label must not claim more than its evidence supports; UNKNOWN is a
  legal value), plus a render line naming which organ was read. This is an instinct, not
  a ruling, and it belongs at Daniil's gate alongside codex's failure classes. Overlaps
  **T108** (N-seat mailbox architecture / per-incarnation streams), which is a claimed
  active task — hence no patch.
- **The reaper predicate** should arguably consult L1 before declaring a seat provably
  dead, independent of which fork wins.
- **The docstring-vs-implementation gap** in `roster.py:9-10` is a second instance of a
  known class — T116 recorded the same shape in `core/comm/role_queue.py`, which claims
  idempotency protection that repo search contradicts. Two instances in load-bearing
  module docs suggests the class is systemic and deserves a checker, not two point fixes.
- **Session-id collision**: the ghost seat rows carry the *conductor's* session id
  (`e696354a`) though the runners were launched as separate processes. grok kept this as
  a separate open thread; it explains why the rows read as the conductor's children.

---

*Loss manifest: this file carries grok's findings and receipts, not its full reasoning
(that lives in the bus messages and its own session transcript). It does not settle the
design fork. It does not verify grok's claims a third time — the conductor spot-checked
only the key-shape split (`roster.py:8,14,48-49`, `liveness.py:10,40-41`,
`bifrost_runner_deepseek.py:401,924,1026`) and accepts the reaper and router findings on
grok's cited receipts, deliberately, per the lesson that re-proving a peer's settled work
is itself one of the failures under investigation.*
