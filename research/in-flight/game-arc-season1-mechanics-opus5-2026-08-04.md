# GAME ARC — Season 1 mechanics (MECHANICS lane, opus5, 2026-08-04)

Status: in-flight / DESIGN ONLY — nothing here is built, committed, or sent
Class: design
Lane: MECHANICS, under the Fable 5 conductor seat (ledger T148 watch)
Design owner of the upgrade: Daniil. Builder of anything below: **deepseek**, per `docs/ORG.md` Part 4.

**What this is.** The mechanical half of Daniil's five-layer gamified fix system, scoped to Season 1
(find-first: live store READ-ONLY, mail submissions, aimed at the door/mail surface). It designs the
bounty protocol, the three starting roles, the scoreboard organ, the fleet mechanics at 10–20
players, the cost sheet, and the list of things only Daniil may decide.

**Sources read** (in the order the brief named them): note `game-arc`
(`ADR_0804002712_753ea1d0`); `research/in-flight/session-2026-08-03-risks-and-undo.md` (full);
`scripts/checkers/wiring_function_baseline.json`; `core/coord/cognitive_metrics.py` (full);
`docs/ORG.md` Parts 3–4; `docs/LIVE_CONSTRAINTS.md` (full); `docs/method-baseline-2026-07.md` M3;
`scripts/checkers/check_wiring.py` (the three load-bearing functions); `scripts/runner_token_journal.py`
(price table); `security/acl.json`; the four `check_wiring_function_gate_*` lessons in the corpus;
ledger entries T047, T086, T108, T134, T135, T139, T140, T143, T144, T146.

**Method note, stated up front.** Every claim about code below carries `file:line`. Where I sampled
rather than exhausted, the section says so and gives the rate. I ran exactly one command that touches
the system — `py scripts/checkers/check_wiring.py --functions`, read-only — and its output is quoted
verbatim in §0. Everything else is file reads and corpus reads. I made no writes anywhere except
this file.

---

## §0. Contradictions found — recorded, not silently resolved

The brief instructed me to record contradictions rather than resolve them. There are four, and two
of them change the design.

### C1. The bounty board is 116 entries, not 108. *(changes the design)*

My brief says "the 108-entry orphan backlog"; the `game-arc` note says "108 frozen orphans". The file
says otherwise:

- `scripts/checkers/wiring_function_baseline.json` → `count: 116`, `entries` length **116**, across
  **36 distinct modules**.
- Its own `history` array holds two events: `114 -> 108` (T134c, the `scripts/`-as-production fix)
  and **`108 -> 116`** (T144, dated 2026-08-03, adding 8 entries — 7 of them in
  `core/signals/coordinator_api.py` — because `__all__ = ["x"]` was immunising a module's own exports).
- Live confirmation, `py scripts/checkers/check_wiring.py --functions` at HEAD 2026-08-04:
  `PASS: every core/ module is wired to a production path (17 known-standalone exception(s)); no NEW
  unwired public function (116 on the frozen backlog).`

So the board grew after the note was written. **Season 1's board is 116.** The note is not wrong; it
is stale by one commit. This matters beyond arithmetic: the board is a *moving* object, so the season
must pin a board snapshot by sha at kickoff or players will score against different worlds.

### C2. `security/acl.json` says fail-CLOSED; the CLI door's reader is fail-OPEN. *(changes the design)*

`security/acl.json` `_comment`: *"Unknown/unlisted agents are QUARANTINED (read-only) by default --
fail-closed."*

`agent_cli.py:5464-5476` — `_agent_acl_caps()` — returns an **empty set** on any exception, on a
missing file, and on an unlisted agent, and its own docstring calls this
*"fail-open -> empty set = the dim render"*, adding *"The ACL is the render gate; session-level
harness doors self-select live."*

Read together: at least at this call site, the ACL decides how a verb list is **rendered**, not
whether a verb **runs**. `core/trust/registry.py:24-26` reinforces the same shape — trusted core
agents keep their roles even if `acl.json` is missing or corrupt.

**I did not establish where, if anywhere, caps are enforced as a refusal.** I read the reader, not a
complete call-graph of enforcement. This is the single largest open question in the whole design,
because Daniil's L4 progression ladder (none → demo → live) assumes the "none" state is a wall. If
it is a dimmer, the ladder is cosmetic. **Named as gate item G3 in §6 and as open question 1.**

### C3. T140 and the risks doc both say "five runners"; there are four.

`core/coord/cognitive_metrics.py` is imported by exactly four files under `scripts/`:
`bifrost_runner_deepseek.py:47`, `bifrost_runner_gemini.py:371`, `bifrost_runner_kimi.py:401`,
`bifrost_runner_sol.py:350`. The fifth runner file, `scripts/bifrost_runner.py` (the generic
stateless-model wake adapter, docstring at `:1-14`), contains **zero** references to
`cognitive_metrics` or a `cog.` alias. Each of the four calls `cog.init` exactly once
(`deepseek:1347`, `gemini:731`, `kimi:787`, `sol:709`).

Consequence for the game: **four instrumented lanes, not five.** A player fleet running on
`bifrost_runner.py` would produce no cognitive metrics at all — a silent hole directly beneath the
scoreboard.

### C4. Season isolation vs. season visibility.

`docs/LIVE_CONSTRAINTS.md` ("Namespaces isolate"): *"drills run in test-* namespaces; coordination
keys follow BIFROST_NAMESPACE -- a drill must never touch live keys."* A 20-player season is a drill
by every property that rule cares about. But the bounty targets **live** code and submissions must
reach a **live** adjudicator seat, or the conductor cannot see the game happening. These pull in
opposite directions and no existing rule resolves it. My recommendation is in §4 and §6 (G4); the
contradiction itself belongs to Daniil.

---

## §1. Bounty protocol

### 1.1 The board, pinned

A season opens by pinning **(a)** the git sha of `wiring_function_baseline.json` and **(b)** the sha
of `check_wiring.py`. Both, not one: T143, T144 and T146 all changed the *gate* on 2026-08-03 without
touching the board, and each changed what "unwired" means. A claim is adjudicated against the pinned
pair or it is not adjudicable.

Board shape, from the file itself: entries are `module::function` strings
(`how_to_read`: *"module::function -- see py scripts/checkers/check_wiring.py --functions"*). The
gate's live output also carries the definition line number, which the bounty card should copy so a
player is not made to grep for it.

Concentration (all 116 counted, not sampled):

| module | entries |
|---|---|
| `core/context/project_context.py` | 18 |
| `core/state/session_checkpoint.py` | 9 |
| `core/coord/cognitive_metrics.py` | 8 |
| `core/learning/agent_memory.py` | 8 |
| `core/learning/learning_store.py` | 8 |
| `core/signals/coordinator_api.py` | 8 |
| `core/comm/bifrost_api.py` | 5 |
| `core/comm/bus.py` | 5 |
| `core/library/atoms.py` | 5 |
| remaining 27 modules | 42 |

Season 1 is aimed at the door/mail surface, which on this board is 20 entries:
`bifrost_api` (5: `council`, `covers`, `intents`, `release_intent`, `wake_cmd`), `bus` (5:
`file_part`, `is_ref`, `json_part`, `media_part`, `text_part`), `context_hints` (2), `launcher` (2),
plus `door_probe::read_verdict`, `locks::validate_token`, `mailbox::intents_of`,
`nudge::nudge_status`, `pager::ack_pages`, `promoter::promote_interjection`.

That set is a good Season 1 because it is small enough to exhaust (20 entries × 3 roles = 60 find
rounds) and it is the surface whose founding defect — `mailbox.py::declare_intent` built with 8/8
pins and no door — is the reason the gate exists at all.

### 1.2 Submission format (mail)

Submissions ride the existing door. No new verb.

```
py agent_cli.py bifrost-send <player_id> --to <adjudicator> --kind request \
    --text-file data/play/s1/<player_id>/claim-<n>.json --json
```

`--text-file` is **mandatory**, not stylistic: `agent_cli.py:4895-4900` documents that argv text
containing flag-shaped tokens *"WILL misparse"*, and every claim in this season quotes
`--functions`, `--json`, or a `--flag` in its evidence.

Body is one JSON object. Fields:

| field | type | notes |
|---|---|---|
| `schema` | `"bounty/1"` | version the format from day one |
| `season` | `"s1"` | |
| `board_sha` / `gate_sha` | str | the pinned pair from §1.1; a claim against an unpinned board is unscored, not refuted |
| `player` | str | the player's own stable agent id, one per player (see §4.2) |
| `role` | `stranger` \| `cartographer` \| `redteam` | |
| `board_entry` | str | verbatim from the baseline, e.g. `core/comm/mailbox.py::intents_of` |
| `claim_class` | `dead` \| `needs-door` \| `needs-caller` \| `false-positive` | rubric in §1.3 |
| `evidence` | list of `path:line` | at least one; the adjudicator resolves each or the claim is unverifiable |
| `blind_summary` | str, ≤ 40 words | **the only prose the verifier sees.** States the claim, not the argument |
| `confidence` | `high` \| `medium` \| `low` | low-confidence claims cannot go negative (see §1.5) |
| `proposed_fix` | str, one sentence | plus a slice size in hours or "unknown" |
| `structural` | null \| `{cause, covers[], sampled, sample_rate}` | a root-cause claim; see §1.4 |
| `dedupe_key` | str | `sha256(board_entry + "|" + claim_class)`, lowercase hex |
| `submitted_at` | ISO8601 | player-side clock, advisory only; ordering is by bus stream id |

The finder's full **reasoning** does **not** ride the mail. It goes into a sealed fence half (§1.5).

**Idempotency is a requirement, not a nicety.** `docs/LIVE_CONSTRAINTS.md` RB-26: *"the work cursor
advances AFTER processing; a crash redelivers the same message -- consumers stay idempotent."* The
scorer must key on `dedupe_key` + `player` so a redelivered card can neither double-score nor steal
first-finder from someone who submitted in between.

### 1.3 Classification rubric

Grounded in the method the risks doc actually used: it **hand-checked 22 of 117 entries (18.8%) and
classified by root cause**, finding that all six false positives shared one structural cause — 29 of
47 files under `scripts/` were not counted as production. The rubric below preserves that shape: the
unit of insight is a *cause*, and the unit of evidence is a *resolvable line*.

**`false-positive`** — a production caller or door exists and the gate cannot see it.
*Burden:* the `path:line` of the reference, **plus** a named reason the gate missed it. The reason
must be either (a) one of the limitations the gate documents about itself at
`check_wiring.py:283-294` — unused imports count as wiring; runtime-assembled names are invisible;
a private helper behind a dead public function is not reported — or (b) a **new** blind spot, which
is the highest-value finding in the season.
*Precedent that sets the bar:* `scripts/snapshot.py:21` calling `list_snapshots` — the backup door,
on which the corpus already holds a `backup_door_never_ran` lesson.

**`needs-door`** — the capability is complete and correct, but no production entry point exposes it.
*Burden:* show the capability works (a passing test, or triviality), and show no verb reaches it
(`py agent_cli.py discover`, `agent_cli.py:4436`, is the self-describing verb list).
*Precedent:* `core/comm/mailbox.py::declare_intent` at `95e0c55` — 8/8 pins, no door; the gate FAILs
there and goes silent at `b945813` once the door lands.

**`needs-caller`** — built ahead of a consumer that does not exist yet.
*Burden:* name the intended consumer **from the module's own docstring**, then show that consumer is
itself unwired.
*Precedent:* `core/coord/cognitive_metrics.py:1-25` names `core/coord/metrics.py` and
`core/coord/experiment.py`; both are on the module backlog as built-ahead.

**`dead`** — no door wanted, no consumer wanted, removal is the fix.
*Burden:* no docstring consumer, no ledger entry that wants it, and a stated blast radius. This is
the **weakest** claim class on purpose. `investigate_before_delete_3of4_wrong` is in the corpus, and
the risks doc had to correct its own commit message for calling `cognitive_metrics` *"built whole and
never wired"* when 4 of its 16 functions are live in four runners. Deletion claims are scored ×1 and
never auto-executed.

**Standing constraint on all four classes:** the rubric may not be satisfied by an assertion. A claim
whose `evidence` lines do not resolve, or resolve to something that does not say what the claim says,
is `unverifiable` (§1.5), not `refuted` — the distinction protects a player from being punished for a
typo.

### 1.4 Structural claims and the sampling rule

A player may submit **one claim covering N entries** if it names a single root cause. This is the
highest-scoring move in the game because it is what actually drained the board twice (T134c: one
cause, 6 entries; T144: one cause, 7 of 8 added entries in one module).

The burden imported directly from the risks doc's own method: **state the sample and the rate.** A
structural claim must carry `{cause, covers[], sampled, sample_rate}` and the player must have
hand-checked `sampled` of `covers` — never fewer than 5, never fewer than 20%. A structural claim
whose sample is smaller than that scores as a single ordinary claim, not a structural one.

**A live example, found while writing this document, offered as the season's calibration case.**
T140 says `cognitive_metrics` has 12 dead functions; the board carries only 8 of them. The four
missing are `dump`, `reset`, `reset_all`, `enable`, and I traced two distinct causes:

- **Attribute collision (already a known blind spot).** `enable` is immunised by
  `scripts/bifrost_runner_deepseek.py:1258` — `dc.C.enable()`, a terminal-colour object with no
  relation to metrics. `reset` is immunised by `scripts/bifrost_runner_deepseek.py:1551`
  (`_storm.reset()`) and `scripts/deepseek_chat.py:470` (`ag.reset()`). The corpus lesson
  `check_wiring_function_gate_a3_a4_name_collision_false_positive` (deepseek-red, 2026-08-03)
  predicted exactly this and named exactly these identifiers — *"dead functions with common names
  (e.g. `reset`, `clear`, `init`) are virtually invisible"*. These are **known**, so under §1.5 they
  score **0**, not negative: correct work, no new information.
- **Transitive immunisation by a dead caller (I did not find this on any known list).**
  `cognitive_metrics.py:258` `reset_all` is named at `:269`, inside `disable` — and `disable` is
  itself **on the board as dead**. `check_wiring.py:443` marks a def wired if its name appears
  anywhere on a production path *other than inside its own body*; the exclusion is scoped to the
  reported function, not to other dead functions. So one dead public function keeps another alive.
  The same mechanism explains why `dump` (`:238`) is off the board while `dump_all` (`:246`, on the
  board) calls it at `:248` — though `dump` is additionally immunised by the ubiquitous `json.dump(`
  attribute, so that one entry has two sufficient causes and I cannot rank them.

I verified this by reading, not by instrumenting the gate; I checked 4 of the 4 missing functions and
found a sufficient cause for each. **The transitive gap is the season's seed bounty**: it is real, it
is small, and it demonstrates the scoring ladder end to end.

### 1.5 Blind cross-verify

**The assignment rule.** Every scored claim gets exactly one verifier, drawn by the adjudicator under
three constraints, in priority order:

1. **The verifier must not share the finder's role.** A Cartographer's claim is verified by a
   Stranger or a Red Team player, never another Cartographer. Same-role verification re-runs the same
   prior and confirms the same blind spots.
2. **The verifier must not have submitted a claim on the same `board_entry` this season.** Their own
   in-flight claim is a stake.
3. **Round-robin within the eligible pool**, so no player accumulates verification load.

**The blindness, mechanically.** The verifier receives: the bounty card's `board_entry`, the
`claim_class`, the `evidence` lines, and the ≤40-word `blind_summary`. The verifier does **not**
receive the finder's reasoning, the finder's identity, or the finder's role. The corpus lesson
`blind_crosscheck_needs_fencing` (worked, useful ×8) states the requirement in its own words: hand
the peer only the raw question, fenced from the synthesis.

**The organ that enforces it already exists.** `agent_cli.py:4785-4796` — the `fence` verb, with
actions `open|write|seal|pv|status|list`, slots `brief|half_a|half_b|reconciliation`, and a `--by`
flag whose help text says authorship *"feeds the independence check"*. Season 1 mapping:

| fence slot | contents | written by |
|---|---|---|
| `brief` | the bounty card as submitted, minus reasoning | adjudicator |
| `half_a` | the finder's full reasoning, sealed at submission time | finder |
| `half_b` | the verifier's independent verdict | verifier |
| `reconciliation` | the adjudication + score | adjudicator |

`half_a` is sealed **before** `half_b` opens. This is what makes "the verifier sees the claim, not the
reasoning" structural rather than disciplinary — the ORG.md Part 3 distinction, and by that standard a
protocol that merely *asks* the adjudicator not to forward the reasoning is unfinished.

Fence id convention: `s1-<module-slug>-<function>` (e.g. `s1-comm-mailbox-intents_of`).

**Verdicts:** `confirmed` · `refuted` · `unverifiable` · `already-known`. A verifier who returns
`refuted` must cite a line, under the same burden as the finder — a refutation is a claim.

**Tie-break.** Finder and verifier disagree → the adjudicator seat rules and writes the
`reconciliation` slot. If the adjudicator is a fleet seat rather than Daniil, its ruling is
recorded as a ruling, never as a fact — `instrument_proposes_never_self_ratifies` is in the corpus,
and the adjudicator both interprets and scores, which is exactly the shape that lesson warns about.
Recommendation: rulings are appendable and Daniil may overturn any of them at a gate.

### 1.6 Scoring table

Base points by confirmed class, multiplied:

| outcome | points | why this weight |
|---|---|---|
| `false-positive` on a **live** capability (gate calls a working door dead) | **×5** | the `list_snapshots` class — a gate that calls the backup door dead is worse than no gate |
| **structural** cause covering ≥3 entries, with a stated sample and rate | **×4** | this is what actually drained the board (T134c, T144) |
| `needs-door` confirmed | **×3** | the founding defect class (`declare_intent`); highest ratio of value to fix cost |
| `needs-caller` confirmed | **×2** | real, but the fix is a program, not a slice |
| `dead` confirmed | **×1** | weakest claim, never auto-executed |
| **new blind spot** in the gate itself (not on the A1–A5 list, not in the documented limitations) | **×6** | the only finding class that improves the instrument rather than the inventory |

Adjustments:

- **First-finder only.** Full points to the first submission per `dedupe_key`, ordered by **bus stream
  id** (monotonic), never by the player's `submitted_at` (player clocks are not trustworthy and the
  field is advisory). Later identical claims: **0**, not negative.
- **Refuted: −2.** A refuted claim costs, because unfalsifiable volume is the failure mode of a
  bounty system. Exception: a claim submitted at `confidence: low` is floored at **0** — the honest
  low-confidence report is the behaviour we want, and punishing it teaches players to overstate.
- **Unverifiable: −1.** Evidence that does not resolve. Cheaper than refuted because it is usually
  sloppiness, not fabrication.
- **Already-known: 0.** The claim matches a corpus lesson or a closed ledger entry (T143/T144/T146
  and the four `check_wiring_function_gate_*` lessons are the pre-loaded known-set). Zero, never
  negative — rediscovery is honest work. *The season must publish the known-set at kickoff or this
  rule is a trap.*
- **Verification points.** A verifier scores **+1** for any verdict delivered under the blind
  protocol, and **+3** for a `refuted` that the adjudicator upholds. Verification must pay or nobody
  verifies, and the whole design collapses to unchecked volume.
- **No score without receipts.** Extending "no proof, no close": a claim with zero resolvable
  `evidence` lines is unscored regardless of how right it sounds.

**Score is evidence, never a key** (Daniil, L4). Nothing in the system may read a score to decide an
access question; a score only makes a player *eligible* for a grant that a human then makes.

### 1.7 Per-player namespace convention

Precedent already in the repo: `security/acl.json` gives `gemini` the path scope
`["research/*", "scratch/*", "data/play/gemini/*"]`. Season 1 follows the same shape.

| artifact | location |
|---|---|
| player working files, claim JSONs | `data/play/s1/<player_id>/` |
| sealed halves | fence `s1-<module-slug>-<function>` |
| player bus traffic | `BIFROST_NAMESPACE=game-s1` (see §4.4 and G4) |
| leaderboard | `state/play/s1/leaderboard.json` (single writer: the adjudicator) |

Rule: **a player may write only under its own `data/play/s1/<player_id>/`.** Not `research/`, not
`docs/`, not `scratch/` — those are shared, and 20 concurrent writers in a shared directory is the
test-file clobber incident from the two-model concurrency findings, scaled ten-fold.

---

## §2. Season 1 roles

Minimum viable set: three. Each prompt below is written to be handed to a DeepSeek API player
verbatim, with `<player_id>`, `<board_entry>`, `<lineno>`, `<board_sha>`, `<gate_sha>` substituted.
Each is one paragraph on purpose — a role prompt that needs a page has become a specification, and
the fleet cannot afford to re-read a page 20 times per round.

### Stranger

> You are `<player_id>`, playing the STRANGER role in Akashic Aurora's Season 1 bounty. You know
> nothing about this codebase's history and you must not pretend otherwise — your value is that you
> have no idea what anything was *supposed* to do. Your bounty is `<board_entry>`, defined at line
> `<lineno>`, which an automated gate says no production code ever names. Read that function and only
> what you need around it. Answer one question as a stranger would: **if I found this function and no
> caller, what would I conclude it is for, and would I expect a door to it?** Then classify it as
> exactly one of `dead`, `needs-door`, `needs-caller`, `false-positive`, cite at least one
> `path:line` as evidence, and write a 40-word claim summary that states your conclusion without your
> argument. If you cannot tell, say `confidence: low` — a low-confidence honest answer costs you
> nothing here and a confident wrong one costs you points. Do not run commands that write. Do not
> read the git history: a stranger does not have it, and your not having it is the instrument.

### Cartographer

> You are `<player_id>`, playing the CARTOGRAPHER role in Akashic Aurora's Season 1 bounty. You do not
> hunt single defects; you hunt **shapes**. Your bounty is a set of related board entries, not one:
> `<board_entry list>`. Read them together and ask **what one cause would explain all of these at
> once** — a missing door for a whole verb family, a consumer module that was never built, a naming
> convention the gate cannot see, a subsystem built ahead of its caller. If you find such a cause,
> submit ONE structural claim naming it, listing every entry it covers, and stating how many of those
> entries you actually hand-checked and what fraction that is: a cause claimed over ten entries with
> two checked is worth less than a cause claimed over four with all four checked, and inflating the
> coverage is the fastest way to be refuted. If the entries have no common cause, say so — "these are
> unrelated" is a real finding and you may submit it as one low-value claim rather than inventing a
> pattern. Cite `path:line` for everything. Do not run commands that write.

### Red Team

> You are `<player_id>`, playing the RED TEAM role in Akashic Aurora's Season 1 bounty. Your target is
> not the code — it is the **instrument**: `scripts/checkers/check_wiring.py`, the gate that produced
> this board. Your job is to find a way for genuinely dead capability to pass it, or for genuinely
> live capability to be called dead. Before you claim anything, read the gate's own limitation block
> at `check_wiring.py:283-294` and treat those as **already known**: the gate documents that unused
> imports count as wiring, that a name assembled at runtime is invisible, and that a private helper
> behind a dead public function is not reported. Five attacks were already found and adjudicated on
> 2026-08-03 (top-level `if`/`try` bodies — now fixed by T143 and T146; name and attribute collision;
> string-constant dispatch), and re-finding any of them scores zero. A gate that documents a blind
> spot is honest, not broken, so your claim must state whether you found an **implementation bug** or
> an **undocumented** blind spot, and must include a concrete construction — a named function, in a
> named file, that the gate would get wrong. Cite `path:line`. Do not modify any file to test your
> attack; describe it precisely enough that someone else could.

**Why exactly these three.** They differ in *prior*, not in topic, which is what makes their
cross-verification informative: the Stranger has no history and finds things the fleet has stopped
seeing; the Cartographer has breadth and finds the causes that drain the board in bulk; the Red Team
attacks the measuring device, the only role whose findings improve the instrument. The blind-verify
rule in §1.5 (verifier must not share the finder's role) is only meaningful because these three
priors genuinely disagree.

**Precedent, and a caution.** `deepseek-red` and `deepseek-review` already exist in
`security/acl.json` as `member` with `path_scope` `research/*, scratch/*` (+ `docs/*` for review), and
they already ran this exact loop informally on 2026-08-03: `deepseek-red` found five attacks on the
gate; `deepseek-review` adjudicated all five as documented trade-offs rather than bugs; T143, T144 and
T146 shipped from it. **Season 1 is not a new idea — it is that loop, named, scored, and run 20-wide.**
The caution: `deepseek-red`'s A1/A2 lesson is now **stale**, because T143 and T146 fixed the hole it
describes (`check_wiring.py:306-333` documents the fix and its cause), yet the lesson still reads as
live and carries `[premise UNCHECKED: no anchors -- this is not a clean bill]`. A game that generates
lessons faster than it retires them will bury the fleet in true-for-a-day findings. **Every confirmed
Season 1 finding must record what would make it stale.**

---

## §3. T140 scoreboard reader (design only — Builder is deepseek)

### 3.1 The data path, end to end

Today there are two half-paths that never meet.

**Path A — money, live and correct.** In the DeepSeek runner: `prompt_before`/`comp_before` are read
at `scripts/bifrost_runner_deepseek.py:454-455`, `prompt_after`/`comp_after` at `:464-465`, and at
turn close `:1090-1093` calls
`_token_journal.add_turn(prompt=delta[0], completion=delta[1], cached_prompt=(shape or {}).get("cache_hit", 0))`.
`scripts/runner_token_journal.py:56` holds `PRICES` (per 1M tokens: `deepseek-v4-pro` 0.55 prompt /
0.055 cached / 2.19 completion; `deepseek-v4-flash` 0.14 / 0.014 / 0.56), and `price_of()` at `:82`
returns `None` as a legitimate answer that callers *"must RENDER it, never substitute"*.

**Path B — behaviour, live but unread.** Four runners call `cog.init` once and then
`record_file_read`, `record_human_interjection`, `record_turn_complete` per turn (call sites in §0
C3). These populate 4 of the 15 numeric fields on `EfficiencySnapshot`
(`core/coord/cognitive_metrics.py:35-60`). **Nothing in production ever calls `dump` (`:238`) or
`dump_all` (`:246`)** — tests only. That is the whole of T140.

**The Season 1 reader closes three edges:**

1. **Runner → cog, at the existing call site.** Two lines beside
   `bifrost_runner_deepseek.py:1090`, using the delta tuple that is already in hand:
   `cog.record_prompt_tokens(agent, delta[0])` and `cog.record_completion_tokens(agent, delta[1])`.
   No new measurement — the numbers are computed 636 lines earlier and currently reach only the
   journal. Same two lines in the other three runners at their equivalent turn-close.
2. **cog → leaderboard.** A reader calls `dump_all()` on a cadence, or at round close, and writes
   `state/play/s1/leaderboard.json`. This is the organ the game contributes: *the game is the reader*.
3. **Journal → leaderboard, for money only.** The leaderboard must **not** compute cost from the cog
   snapshot. `TokenJournal` already owns pricing, cache-awareness and the `UNPRICED` state; a second
   pricing path is precisely the defect `runner_token_journal.py:20-26` was written to end (*"cross-
   provider pricing, first-model-of-the-day pinned forever, and cache hits billed at the full fresh-
   input rate"*). The leaderboard **joins**: behaviour from cog, money from the journal, keyed on
   agent id and time window.

**A gap worth stating rather than discovering later:** `EfficiencySnapshot` has **no cached-prompt
field** (`:41-46` — `total_prompt_tokens`, `total_completion_tokens`, no cache split), while
`add_turn` takes `cached_prompt`. Do **not** add the field. Cache economics belong to the priced
side; duplicating them gives the season two token counters that will drift and then be argued about.

### 3.2 Which of the 12 dead recorders Season 1 needs — and which to retire

The board carries 8 `cognitive_metrics` entries: `disable`, `dump_all`, `record_abandoned`,
`record_completion_tokens`, `record_context_refresh`, `record_prompt_tokens`, `record_reasoning`,
`record_tool_call`. T140's other four dead functions (`dump`, `reset`, `reset_all`, `enable`) are
off the board for the collision and transitive reasons traced in §1.4.

| function | Season 1 verdict | reason |
|---|---|---|
| `record_prompt_tokens` (`:156`) | **WIRE** | data exists at `bifrost_runner_deepseek.py:1090`; one line |
| `record_completion_tokens` (`:161`) | **WIRE** | same; also the denominator of `waste_ratio` (`:72-76`), which is structurally 0 today |
| `record_tool_call` (`:206`) | **WIRE** | the most legible score input; the coordination/productive split at `:211-214` already names the bus verbs |
| `dump` (`:238`) / `dump_all` (`:246`) | **WIRE** | this *is* the reader; without it the season instruments nothing |
| `reset` (`:251`) | **WIRE** | round boundary. Must persist the closing snapshot before clearing (pin P6) |
| `record_reasoning` (`:166`) | **RETIRE the fields, or redefine** | no provider bridge exposes a coordination-vs-productive split of reasoning tokens; wiring it means inventing a classifier and calling its output a measurement. Recommend redefining `coordination_token_ratio` over **tool calls**, which we can actually measure, and dropping `reasoning_tokens_coordination` / `reasoning_tokens_productive` |
| `record_abandoned` (`:175`) | **RETIRE for Season 1** | abandoned tokens mean a nudge/halt interrupted mid-reasoning; Season 1 players are one-shot API calls with no barge-in, so the field is structurally always 0. Under the adopted law, leaving it renders an unmeasured zero |
| `record_context_refresh` (`:201`) | **DEFER** | a stateless player refreshes context every turn, making this a constant equal to the turn count, not a measurement. Meaningful only for persistent seats |
| `reset_all` (`:258`), `disable` (`:265`), `enable` (`:272`) | **KEEP, wire `disable` once** | a kill switch that has never been exercised is the `backup_door_never_ran` class. Wiring `disable()` to a config flag makes the "zero-cost when disabled" claim in the module docstring (`:23`) true by test rather than by assertion |

**The adopted law, made mechanical.** Daniil's L3/graft law — *"an unpopulated counter renders as a
MEASURED zero"* — cannot be satisfied by care. `to_dict` (`:100-125`) emits every field as an
unconditional int; a leaderboard reading it will print `0` for `abandoned_tokens` forever and the
number will be believed. The fix is a **MEASURED-FIELDS manifest** — a module-level constant naming
which fields have a live recorder — that the renderer consults, printing `unmeasured` (not `0`) for
anything absent. This mirrors the pattern the repo already uses for money: `core/comm/doctor.py:1114`
renders `UNPRICED (... — no rate in PRICES)` rather than a plausible number. Recommend the manifest
over adding `Optional[int] = None` defaults to the dataclass: it is a smaller change, and the manifest
is the surface the pins can test.

### 3.3 Pre-registered pins, RED first (per M3)

`docs/method-baseline-2026-07.md:180-191`: *"the acceptance is a NAMED failing test (or strict xfail)
committed BEFORE the fix builds"*; metric = acceptance commit timestamp ≤ implementation commit
timestamp; *"BAR: no slice ships whose acceptance postdates its implementation."* The prior Opus
session's own receipt is the standard: 9 pins committed RED and alone at `c61fa98`.

**Slice S1-SCORE-A — token recorders wired.** Pins committed RED and alone, before any runner edit:

- **P1** After the runner's turn-close path runs once, `dump(agent)["total_prompt_tokens"] > 0`.
  RED today because no production caller exists (`record_prompt_tokens:156`).
- **P2** For the same N turns, `dump(agent)["total_completion_tokens"]` equals the sum of `completion`
  passed to `TokenJournal.add_turn`. One number, two sinks, must agree — this pin is the guard against
  the two-counter drift §3.1 warns about.
- **P3** `dump(agent)["total_tool_calls"] > 0` after a turn that made a tool call, and a bus verb from
  the frozenset at `:211-214` increments `tool_calls_coordination`, not `tool_calls_productive`.

**Slice S1-SCORE-B — the reader and the honest zero.**

- **P4** `dump_all()` over ≥2 player ids returns 2 rows, each carrying its own `agent_id`. RED today:
  `dump_all` has zero production callers.
- **P5** The leaderboard renderer, given a snapshot whose `abandoned_tokens` has no recorder, emits
  `unmeasured` — the assertion is `"0" not in cell`. This is the adopted law as a test.
- **P6** Enumerate every numeric field on `EfficiencySnapshot`; fail if any field is both absent from
  the MEASURED-FIELDS manifest and rendered numerically. This is P5 generalised so a future field
  cannot be added silently.
- **P7** `reset(agent)` between rounds zeroes the accumulator **and** the previous round's closing
  snapshot is still readable from the persisted leaderboard. Guards silent history loss at the round
  boundary.

**Slice S1-SCORE-C — money joins without a second pricing path.**

- **P8** A player id absent from both `AGENT_DEFAULT_MODEL` and `PRICES` renders `UNPRICED` on the
  leaderboard and is **excluded** from any cost total. This is T135's `kimi-k3`/`sol` case, and it
  mirrors `price_of()` returning `None` at `runner_token_journal.py:82`.
- **P9** The cost the leaderboard shows for a `deepseek` player equals `TokenJournal`'s own estimate
  for the same window, to the cent. The scoreboard may not invent a second pricing path.

**Slice S1-BOUNTY-A — the scorer.**

- **P10** The same submission delivered twice (RB-26 crash redelivery) scores once, and does not
  change first-finder.
- **P11** Two players submitting the same `dedupe_key` — the second scores 0, and the first-finder is
  decided by bus stream id, not by the `submitted_at` field.
- **P12** A claim whose `evidence` lines do not resolve scores `unverifiable` (−1), not `refuted` (−2).
- **P13** A verifier who shares the finder's role is refused assignment. Structural, not advisory.
- **P14** `half_b` cannot be opened before `half_a` is sealed.

Every pin above is RED at the pinned board sha. None is implementable without the slice it guards,
which is the property M3 asks for.

---

## §4. Player fleet mechanics at 10–20 concurrent

### 4.1 The membrane

**Players stay outside the core.** A player is an API process whose only contact with the system is
(a) `agent_cli.py` verbs and (b) the bus. No player imports `core.*` directly, and no player runs
inside a seat's process. This is the standing membrane law for runners, and Season 1 gives it a
second, sharper reason: whatever enforcement the ACL provides lives at the door, so a player that
imports `core` has walked around the entire L4 access ladder. Given C2 (the reader at
`agent_cli.py:5464-5476` is fail-open), the membrane may currently be the *only* boundary — which is
an argument for making it structural before the season, not after.

Concretely: players run as subprocesses launched from a season harness, with `cwd` at the repo root,
`BIFROST_NAMESPACE` set per §4.4, and no `PYTHONPATH` that makes `core` importable.

### 4.2 One agent id per player, not one per role

`docs/LIVE_CONSTRAINTS.md` **T045**: *"work lane FIRST, legacy is a straggler net; consume with the
seat's lane env (BIFROST_CONSUME_LANE) or cursors diverge into wake loops."* Cursors are per-agent. If
five Stranger players share the id `stranger`, they share one cursor and steal each other's mail —
the exact mis-delivery family T108 exists to kill, reproduced deliberately at N=20.

So: `s1-stranger-01 … s1-stranger-07`, `s1-cartographer-01 …`, `s1-red-01 …`, each with its own
`BIFROST_CONSUME_LANE`. Where two processes must share an id, address the specific one with
`--to-incarnation` (`agent_cli.py:4907-4909`, T073), which `Bus.send` honours by mirroring to the
seat's own stream (`core/comm/bus.py:282-283`, T108 slice 1).

### 4.3 Expectations: opt out on broadcast, arm on directed asks

`docs/LIVE_CONSTRAINTS.md` **RB-29**: *"timeout/error NOTES never settle an expectation (redrives stay
alive); only ANSWER_KINDS reply/handoff/completion settle."* And `agent_cli.py:4901-4906`: directed
asks of kind `request`/`handoff`/`question` **auto-arm** a reply window unless `--expect-reply-within 0`
is passed; a dead expectation costs 3 redrives and a loud `expectation_dead`.

At 20 players × 20 bounties, auto-armed expectations on every bounty card produce up to 400 live
expectations and, for every player that stalls, 3 redrives. **Recommendation:** bounty cards go out
with `--expect-reply-within 0`; expectations are armed **only** on directed verification asks, where a
non-answer is genuinely a problem. This is a design decision with a live cost, so it is listed as
gate item G5.

Also **RB-26**: the work cursor advances after processing, so a crashed player is redelivered its
bounty card. Combined with §1.2's `dedupe_key`, that is safe — but only because the scorer is
idempotent by construction (pin P10). Without P10, one crash inflates a score.

### 4.4 Namespace, and the isolation contradiction

`docs/LIVE_CONSTRAINTS.md`: *"drills run in test-* namespaces; coordination keys follow
BIFROST_NAMESPACE -- a drill must never touch live keys."*

Recommendation: players run under `BIFROST_NAMESPACE=game-s1`; the adjudicator is a **live** seat that
explicitly reads the `game-s1` namespace to collect submissions. The season's writes stay off live
coordination keys; the fleet still sees the game. The cost is one bridge point, held by one seat, which
is a smaller surface than 20 players on live keys. See C4 and G4 — the contradiction is real and the
resolution is Daniil's.

Season 1 is **live store READ-ONLY** by Daniil's own scope, which means players do not need write caps
at all beyond their own `data/play/s1/<player_id>/`. That is the strongest argument that Season 1 is
safe to run before C2 is resolved: even a fail-open door grants nothing a read-only season would use.

### 4.5 Dual-write, and what the season pays back to T047

**T039a/T044** (`LIVE_CONSTRAINTS.md`): *"dual-write is LIVE until T047: every message exists on TWO
streams (work lane + legacy) -- dedupe by sha/reply_id, never by stream id."*

Twenty players doubling every message is the heaviest dual-write load this system has ever carried.
That is a cost — and it is exactly the evidence T047 (`approved`, unstarted) needs. The risks doc
records the argument in the prior seat's words: every entry in the lane/cursor/mis-delivery family
exists because dual-write is still live. **A season that reads zero messages off the legacy stream,
under 20-way concurrency, is the retirement receipt** — a measured statement rather than an argument.
Instrumenting that requires one counter: legacy-stream reads that were not already delivered on the
work lane. If it is 0 across a full season, T047's straggler-net justification is empirically empty.

**One caution:** the scorer must dedupe by `dedupe_key` (content), never by stream id — the same rule
T044 states for messages. A design that scored per stream id would double every submission on the day
dual-write is switched off, which is the wrong direction to fail.

### 4.6 What the load lab gives T108

T108 (`claimed`) proposes: directed mail → per-incarnation streams with their own cursor and watcher;
role mail → **one** work queue via native Redis consumer groups (`XREADGROUP` + `XAUTOCLAIM`, exactly-
once claim as the feature); broadcast → per-seat cursors unchanged; a reaper that re-homes a dead
seat's directed mail to the role queue loudly. Its own text names *"storm bars as acceptance"* and
requires a fence because the deepseek and kimi runners are consumers.

Season 1 hands it four things it cannot get any other way:

1. **A measured mis-delivery rate at N=20 on the current shared-key architecture.** Every existing
   receipt in this family comes from *twin* seats — N=2. T108 is a migration argument with no N>2
   number behind it. Twenty players generate one, cheaply, before anyone migrates.
2. **A natural role-queue workload.** "Twenty players, one bounty queue, each card claimed exactly
   once" is the `XREADGROUP` case in its purest form — the exactly-once claim is the whole point, and
   Season 1 needs it independently: two players working the same bounty is a scoring bug.
3. **The reaper case at a rate where it happens.** API players die (rate limits, timeouts, provider
   5xx). Today a dead seat's directed mail re-homing is a design paragraph. At 20 players it happens
   several times a session, on purpose, and the re-home path gets exercised.
4. **The storm bars themselves.** T108's acceptance wants numbers. A season is a load generator with a
   scoreboard already attached (§3), so the bars are a by-product rather than a separate build.

**And one thing the season must not do:** it must not *require* T108 to ship first. Season 1 is
read-only, mail-based, and one-agent-id-per-player, all of which work on the current architecture.
T108 is what the season *pays for*, not what it *waits for*.

---

## §5. Cost sheet

**The price table** (`scripts/runner_token_journal.py:56-70`, USD per 1M tokens):

| model | prompt | cached prompt | completion | as_of |
|---|---|---|---|---|
| `deepseek-v4-pro` | 0.55 | 0.055 | 2.19 | 2026-07 |
| `deepseek-v4-flash` | 0.14 | 0.014 | 0.56 | 2026-07 |

`AGENT_DEFAULT_MODEL` (`:72`, read at `:206`) maps only `deepseek → deepseek-v4-pro`. **T135 (`proposed`) is
confirmed by the file: there is no rate for `kimi-k3` or the `sol` model**, so both lanes are
`UNPRICED` by design and render as such (`core/comm/doctor.py:1114`). Any player on those lanes is
outside this cost sheet and must be excluded from totals, not estimated (pin P8).

**Estimation basis, stated so it can be corrected.** I did not measure a live round — measuring one
would mean running a player, which is outside this lane's read-only scope. I sized the inputs from
file bytes at ~3.7 chars/token: `core/coord/cognitive_metrics.py` 10.4 KB ≈ 2.8k tok;
`core/state/session_checkpoint.py` 16.8 KB ≈ 4.5k; `core/comm/bifrost_api.py` 29.2 KB ≈ 7.9k;
`core/context/project_context.py` 31.7 KB ≈ 8.6k; `core/learning/agent_memory.py` 32.2 KB ≈ 8.7k;
`core/signals/coordinator_api.py` 41.0 KB ≈ 11.1k. **These are estimates, not receipts.** The first
real season round should be metered against `TokenJournal` and this table replaced.

**One FIND round** (role prompt ~0.4k + bounty card ~0.2k + target module read ~8k + gate output slice
~0.2k ≈ **9k prompt**, ~1.0k completion):

| | prompt cost | completion cost | round |
|---|---|---|---|
| pro, cold (no cache) | $0.0050 | $0.0022 | **$0.0072** |
| pro, warm (60% cache hit) | $0.0022 | $0.0022 | **$0.0044** |
| flash, cold | $0.0013 | $0.0006 | **$0.0019** |

**One VERIFY round** (claim + evidence lines + the cited slice only ≈ 4k prompt, 0.5k completion):
pro cold **$0.0033**; flash cold **$0.0009**.

**Season 1 aggregates** (the 20 door/mail entries from §1.1, one find + one blind verify each):

| shape | rounds | pro (cold) | flash (cold) |
|---|---|---|---|
| 1 role × 20 bounties + verify | 40 | **$0.21** | **$0.06** |
| 3 roles × 20 bounties + verify | 120 | **$0.63** | **$0.17** |
| 3 roles × full 116 board + verify | 696 | **$3.66** | **$0.97** |
| 20 players × 10 rounds each, 50/50 find/verify | 200 | **$1.05** | **$0.28** |

**The honest headline: a full three-role season over the entire 116-entry board costs under $4 on
`deepseek-v4-pro` and under $1 on `flash`.** Cost is not the constraint on this design. Two things
that *are*: (a) the adjudicator's time, which is a live seat and therefore the scarce resource; (b)
rate limits and concurrency at the provider, which this sheet does not model at all.

**What could make these numbers wrong, worst first:** retries and failed rounds are not modelled and
could plausibly double the count; the 60% cache-hit assumption is invented, not measured; a
Cartographer round reads several modules and is 2–4× a Stranger round; and if any player runs on an
UNPRICED lane, its true cost is unknown rather than small.

---

## §6. The Daniil gate list

Each line is one decision, with a recommended default. Nothing below is actionable without his word.

| # | Decision | Recommended default |
|---|---|---|
| **G1** | **Season 1 scope.** Which board? | The **20 door/mail entries** of §1.1, not all 116 — small enough to exhaust in one season, and it is the surface whose founding defect (`declare_intent`) created the gate |
| **G2** | **The board is 116, not 108** (C1). Confirm the season pins the *current* board + gate shas | Pin both shas at kickoff; publish the known-set (T143/T144/T146 + the four `check_wiring_function_gate_*` lessons) so "already-known" scores 0 fairly |
| **G3** | **The access ladder** (C2). `acl.json` says fail-closed; the CLI reader is fail-open. Does "none" mean refused or dimmed? | Season 1 needs **no new grants**: it is read-only, and players write only under `data/play/s1/<player_id>/`. Run the season on that basis, and file the fail-open/fail-closed question as its own ledger entry rather than fixing it under game pressure |
| **G4** | **Namespace** (C4). Isolated `game-s1` vs. live? | `BIFROST_NAMESPACE=game-s1` for players; **one** live adjudicator seat bridges. Preserves "namespaces isolate" while keeping the game visible |
| **G5** | **Expectation policy at N=20** (RB-29). Auto-armed reply windows on every bounty card? | `--expect-reply-within 0` on bounty cards; arm expectations **only** on directed verification asks |
| **G6** | **Fleet size and spend cap.** How many concurrent players, on which model? | Start at **6** (2 per role) on `deepseek-v4-flash` for round 1; step to 20 only after the first round's mis-delivery rate is measured. Spend cap $5/season — from §5, that is ~5× a full three-role season on pro |
| **G7** | **Who adjudicates.** A fleet seat or Daniil? | A fleet seat that is **not** a player and **not** the Builder, writing `reconciliation` slots that are appendable and overturnable by him. `instrument_proposes_never_self_ratifies` |
| **G8** | **T140 build authorisation.** Wire recorders + reader, or retire the fields? | **Both, in the order of §3.2**: wire the 5 that have real data, retire `record_abandoned`, redefine `record_reasoning`'s ratio over tool calls, defer `record_context_refresh`. Builder = deepseek, pins RED first per §3.3 |
| **G9** | **Watch slot** (`docs/ORG.md` Part 3: cap of two, never two builds). Season 1 build occupies one | Open Season 1 as the **design/research** watch while the MECHANICS lane is design-only; converting S1-SCORE to a build requires naming what it pauses (`pauses:`) |
| **G10** | **Does the season write to the ledger?** Bounties as tasks, or as game state only? | **Game state only** for Season 1 (`state/play/s1/`). A confirmed finding gets *proposed* as a ledger entry by the adjudicator, one at a time, through the normal gate. 116 auto-minted entries would drown the ledger |
| **G11** | **T047 instrumentation** (§4.5). Count legacy-stream reads during the season? | **Yes** — one counter, read-only, and it is the retirement receipt T047 has never had |
| **G12** | **Staleness discipline** (§2 caution). Every confirmed finding records what would falsify it | Adopt. The A1/A2 lesson is already stale-but-live in the corpus; a 20-player season generates that failure mode 20× faster |

**Not in scope, and deliberately untouched:** the four decisions the prior Opus seat left to Daniil —
T088's naming half, T003/T005, the eleven never-started programs (T098 gating the UI merge), and the
T047 ruling — remain his. The game prepares dossiers only on his ask, per the `game-arc` note.

---

## Appendix — what I did not verify

Stated plainly, because the quality bar is the prior session's and it named its own gaps.

1. **ACL enforcement.** I read `agent_cli.py:5464-5476` and `core/trust/registry.py:20-36, 83`. I did
   **not** trace whether any verb refuses on a missing cap. Every statement about the L4 ladder in this
   document is conditional on that trace (C2, G3).
2. **The transitive-immunisation gap (§1.4).** Verified by reading `check_wiring.py:443` and
   `cognitive_metrics.py:258-269`; **not** verified by constructing a test case against the gate. I
   checked 4 of 4 missing functions and found a sufficient cause for each, but for `dump` two
   sufficient causes exist and I cannot rank them.
3. **Cost figures (§5).** Estimated from file byte sizes at ~3.7 chars/token, not measured against a
   live `TokenJournal`. The 60% cache-hit assumption is invented.
4. **Runner shapes.** Per the brief I did **not** depend on the working-tree state of
   `scripts/bifrost_runner_deepseek.py`, which carries another lane's uncommitted modifications. Line
   numbers cited from it (`:47, :454-455, :464-465, :1090-1093, :1258, :1347, :1551`) are from the
   file as it exists on disk today and may move. The *shape* — deltas computed at turn close, one
   `add_turn` call — is what the design depends on, not the line numbers.
5. **`bifrost_runner.py`'s role.** I established it does not reference `cognitive_metrics`. I did not
   establish whether any player fleet would actually use it (C3).
6. **Fence semantics.** I read the CLI surface (`agent_cli.py:4785-4796`) but not `cmd_fence`'s
   implementation. Pin P14 ("`half_b` cannot open before `half_a` is sealed") is written as a
   *requirement*; whether the fence already enforces it is unchecked.
7. **The test suite.** Not run. The prior session recorded 23 failures at HEAD with flakiness in both
   directions; nothing here changes that and nothing here was tested against it.
