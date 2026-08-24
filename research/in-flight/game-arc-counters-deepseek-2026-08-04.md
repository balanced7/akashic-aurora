# GAME ARC — contrarian counters (deepseek, Builder seat, 2026-08-04)

Status: in-flight / DESIGN ONLY — nothing here is built
Class: design
Lane: MECHANICS, round 1 counters (T148, Fable conductor)
Ask: Daniil + Fable's ask for strongest contrarian-grade (B2) counters on four questions

Sources read in full: game-arc note (bus), opus5 mechanics doc (all 12 sections),
kimi's convergence objection, `LIVE_CONSTRAINTS.md`, `check_wiring.py:280-340`,
`runner_token_journal.py` (full), `cognitive_metrics.py` (full), `runner_lock.py`
(full), `bus.py` (first 120 lines), `locks.py` (first 120 lines), the dual-write
and lane-cursor defect corpus (6 lessons), the two-seat concurrency findings
(`deepseek-writer-census-capture`, `netcode-u1-seat-stream-live-codex`, the
env-loss/relaunch defect chain).

---

## (a) The Goodhart economy — where it still leaks

I agree with kimi's structural case: burn-down cannot distinguish "system got better"
from "attackers got tired," and the canary oracle is the only instrument presented that
separates them. I'll state that once and move on to the leaks it does NOT cover — the
ones the canary is blind to.

### A1. The gate's own blind spots become the season's implicit score ceiling, and zero-entry on the baseline means zero-points for the highest-value finding class

The board (`wiring_function_baseline.json`, 116 entries) is a snapshot of what
`check_wiring.py`'s function-level gate reported as unwired on a specific day. Every
limitation the gate documents at `:289-294` defines a class of defect the board
**systematically excludes**:

- Runtime-assembled names (`"declare_" + verb`) are invisible to the gate →
  zero points for finding a dynamically-dispatched dead verb.
- Private helpers behind dead public functions are not reported →
  zero points for finding the helper the dead public function leaves behind.
- A module whose ONLY deadness is an unused import → zero points for finding it.

The season's scoring rubric makes the Red Team role explicitly hunt gate blind spots
(§2, "your target is not the code — it is the instrument"), which is the correct
design. But the scoring for the Stranger and Cartographer is keyed to board entries.
A player who finds a dead function whose name is assembled at runtime — the exact
defect class that `declare_intent` WAS before `b945813` gave it a door — submits
nothing scorable because the function isn't on the board. The board is the gate's
shadow, and the gate's shadows have shadows.

**What this means at N=20:** the season optimises for gate-detectable defects. That
is fine as long as we call the season what it is — "gate-detectable defect drain" —
not "system improvement." A gate that gets better at detecting the class of defects
it currently misses will show a *worse* score because new entries appear on the
board mid-season (C1 already documents the board growing from 108→116 between two
commits). A better instrument temporarily produces a worse score. That is a Goodhart
leak: the metric punishes improving the metric's own coverage.

**Fix, minimal.** Every season round includes one round where a Stranger reads
against the *live tree*, not the baseline, and submits anything it believes is dead
regardless of gate membership. Those submissions get `board_entry: "offboard"` and
score at 0.5×. The counter tracks the ratio of offboard-to-onboard confirmed
findings per round. If it rises while onboard burns down, the gate's coverage is
the limiting factor, not the code. The mechanic already has the concept
(`confidence: low` floored at 0 to avoid punishing honesty); extend it.

### A2. The Cartographer multiplier creates a scoring arms race that rewards breadth claims over verified breadth

§1.4: a structural cause covering ≥3 entries at a stated sample rate scores ×4. The
rubric says "a cause claimed over ten entries with two checked is worth less than a
cause claimed over four with all four checked." But "worth less" is not operationalised
— there is no formula, which means the adjudicator is doing subjective adjustment per
claim. At N=20, three Cartographers in a round will independently discover the same
structural cause (the §1.4 transitive-immunisation gap is the low-hanging fruit; the
first Cartographer to read `check_wiring.py:443` and `cognitive_metrics.py:258` will
see it). The second and third get 0 for the same cause (first-finder dedup by stream
id), but the first one who claimed 8 entries with 2 checked gets ×4 while the one who
checked all 4 and claimed 4 gets ×4 on a smaller set. The incentive is to claim the
widest defensible set on the thinnest evidence, because the penalty for overclaiming
(refuted: −2) is asymmetric against the reward (×4 on a base of 3).

**The leak is real and has a simple fix:** the multiplier is **×min(claimed, verified)**
— you get the ×4 only on entries the verifier confirms you actually checked. Claiming
8 with 2 checked gets you ×4 on 2 and ×1 on the other 6 (if verified). That makes the
incentive point at checking, not claiming.

### A3. The funnel's own value rate (6.8%) is the most damaging implicit score the season never reports

The game-arc note says: "L3 metabolism: game traffic feeds the starving recall funnel
(6.8% value); mechanics tuned on game traffic, content ranking on real-work traffic."
The 6.8% is from `learn:experiment:sharpening_s1_triage` — 8 lessons hold all earned
credit, 94 sources surfaced ≥5× with zero credit, ~74% of the tracked corpus is cost
without return. A season of 20 players generating findings will generate **new
lessons** at a rate we have never seen. Each confirmed finding becomes a lesson. Each
lesson that enters the corpus and is surfaced ≥5× with zero credit becomes a drain on
recall fidelity — the exact cost-without-return the triage was built to measure.

The season is designed to GENERATE what the funnel's own health metric says is its
largest cost. A finding that confirms `mailbox.py::intents_of` is needs-door creates
a lesson. Twenty findings create twenty lessons. The funnel already cannot afford the
lessons it has; the season is building a lesson factory on top of that.

**This is not a reason to kill the season.** But the season must instrument this: the
ratio of (season-generated lessons that earned credit within one month) to (season-
generated lessons that surfaced ≥5× with zero credit within one month). If that ratio
is worse than the corpus baseline of ~6.8%, the season's output is noise-dominant and
the game's own L3 claim — that game traffic feeds the funnel — is falsified. File it
as a gate pin, RED before the first season round, with a kill condition: two seasons
below the baseline → stop auto-generating lessons from findings; findings go through
the normal gate-only path (adjudicator-proposed ledger entries, one at a time, per G10).

### A4. The adjudicator's time is both the scarce resource and the single point of scoring failure

The mechanics doc acknowledges this at §5: "the adjudicator's time, which is a live
seat and therefore the scarce resource." But it does not model what happens when the
adjudicator falls behind. At 20 players submitting claims, each requiring blind-verify
assignment + verdict reconciliation + scoring, the adjudicator's queue depth grows
with every round. A backlogged adjudicator means:

- Claims sit unverified. A player who submitted early in the round may have their
  claim verified after the round closes, by which time the player's API process is
  dead and their score is unclaimed.
- The blind verifier pool is the other players. A backlogged adjudicator means
  verification asks queue behind scoring work, which queues behind more claim intake.
- **The bus expectation machinery (RB-29) will fire on unanswered verification asks.**
  Mechanics §4.3 says to use `--expect-reply-within 0` on bounty cards and arm
  expectations only on directed verification asks. Good — but if the adjudicator
  cannot dispatch verification asks faster than claims arrive, the armed expectations
  on those verification asks will time out and redrive. Three redrives per
  expectation × N verification asks = the wake-loop defect at game scale.

**The fix is not a design change; it is a sizing constraint.** The adjudicator's
throughput — claims verified and scored per hour — must be modelled BEFORE the fleet
size is set (G6). The cost sheet models token cost to the cent but does not model
adjudicator time at all. My recommendation: one round with 3 players per role (9
total), measure the adjudicator's per-claim latency end-to-end, then set the fleet
size so the adjudicator's queue depth stabilises, not grows. If one adjudicator
cannot keep up with 20 players, the fleet is unsized and the season stalls on the
one resource it did not measure.

---

## (b) Blind verification protocol — collusion/correlation failure modes

### B1. Same-model verifiers share the same failure modes on the same evidence

Kimi's §1 covers the induction-layer covariance. I'm adding the evidence-layer
covariance, which is a separate failure mode and one the blind protocol does not
protect against.

A verifier receives: the `board_entry`, the `blind_summary` (≤40 words), the
`claim_class`, and the `evidence` lines (`path:line`). The verifier must read the
cited code and judge whether the claim is correct. At DeepSeek's ~3.7 chars/token,
a 40-word summary ≈ 200 chars ≈ 55 tokens of content-claim. The evidence lines are
paths the verifier must open and read, which anchors the verifier's attention to
the **same files the finder selected**. Two same-checkpoint verifiers reading the
same evidence from the same files through the same model weights do not just share
induction — they share the **evidence landscape**. A function whose deadness is
genuinely ambiguous looks ambiguous to both. A gate blind spot that makes a live
function appear dead fools both.

This is worse than the covariance kimi describes because it persists even if the
verifiers have different **role** hats — the blind protocol strips the role hat
by design (the verifier sees the blind summary, not the finder's role prompt). So
the verifier's own role hat is the *verifier* hat, which is a single hat. Two
Strangers verifying a Cartographer's structural claim and one Cartographer verifying
a Stranger's deadness claim all wear the same verifier hat, read the same evidence,
share the same induction. The decorrelation the role system provides (different
priors → different observations) is active in FIND but not in VERIFY.

**The consequence is mild at Season 1 scale but structural:** a `refuted` verdict
that both verifiers independently reach is weaker evidence of wrongness than the
protocol claims, because the independence is only at the assignment level (two
different players), not at the induction level. A verifier from a genuinely different
model (not just a different checkpoint — a different architecture) is the only thing
that decorrelates verification errors.

**Fix, cheap.** Add one heterogeneous verifier per round. A Gemini or Grok seat
(different provider, different architecture, different training distribution) runs
blind verify on a 10% sample of claims. If the heterogeneous verifier disagrees with
the DeepSeek consensus on any claim, that claim escalates to the adjudicator with the
disagreement flagged and scored as `contested` rather than `confirmed` or `refuted`
until resolved. This costs a few verify rounds (10% of whatever N is) and buys a
correlation break at the verification layer, not just at the finding layer (kimi's
G5 already buys the break at finding, but the two layers have different failure modes).

### B2. The fence protocol has a time-of-check-to-time-of-use window

§1.5: the finder seals `half_a` (the full reasoning) immediately after submitting
the mail. The adjudicator seals `half_b` (the verdict) after adjudication. The
protocol checks that neither was opened early. But between "finder submits mail" and
"finder seals `half_a`" there is a window — however small — where the finder can
read the blind summary **of another player's claim** (if one arrives on the bus
between those two operations) and adjust their own `half_a` reasoning to match. The
window is small but it exists, and at N=20 it happens by accident: two players
submit in the same second, one reads the other's mail before sealing.

**The mechanics doc §1.5 already has `half_b` cannot be opened before `half_a` is
sealed (P14), which covers the verifier side. The finder side needs its own pin:**
a claim is unscored if `half_a`'s seal timestamp is after the finder consumed any
other player's claim mail for the same round. The bus stream id is monotonic and
the seal timestamp is recorded at the file level — the adjudicator can check.

### B3. The "no score without receipts" rule is gamed by evidence that resolves but does not prove

§1.6: "a claim with zero resolvable `evidence` lines is unscored regardless of how
right it sounds." But "resolvable" is not "convincing." A player who submits 5
`path:line` references that all exist and are all irrelevant has satisfied
"resolvable" while submitting noise. The verifier is supposed to catch this — they
read the evidence and judge. But at N=20, the volume of claims may exceed the
verifiers' time budget, and a verifier who opens 3 of 5 evidence lines and finds
them technically correct may confirm the claim without opening the other 2.

**Fix.** Add a `evidence_relevance` field to the verifier's verdict: how many
evidence lines the verifier actually opened, and of those, how many actually support
the claim. A verifier who opened 3/5 and found 2/5 supporting gets their verdict
weighted at 0.6 (2/5) rather than binary. This is already implicit in the Cartographer
rubric (§1.4 sample rate); make it explicit and universal.

---

## (c) Season 1 scope — what breaks at 10-20 concurrent players

The two-seat findings documented six defect families. I'm going to name the ones
that compound at N=20.

### C1. The singleton runner lock is the wrong primitive for stateless API players — it blocks exactly the shape the season needs

`core/comm/runner_lock.py:2-4`: *"at most ONE live runner per agent id. Two runners
for the SAME agent share one Redis read-cursor, so one advances the cursor past a
message the other should have answered."* This is correct for persistent seats. It
is **wrong** for stateless API players, and the mechanics doc correctly avoids it
by recommending one agent id per player (§4.2: `s1-stranger-01 … s1-stranger-07`).

But the mechanics doc also says players are "subprocesses launched from a season
harness." The harness will launch 20 subprocesses, each binding a unique agent id,
each acquiring its own singleton lock. That works — until a player crashes and the
harness relaunches it. `runner_lock.acquire_waiting` at `:83` waits up to
`LOCK_TTL + 8` seconds for a dead predecessor's lock to expire. At 20 players with
independent crash probabilities, the probability that **at least one** launch is
delayed by a stale lock is near-certain. With LOCK_TTL=20s (scaled), a single
stale lock delays one player's start by up to 28 seconds. If three crash in the
same round — plausible at API rate limits or provider 5xx — three players wait.

**The two-seat findings never saw this because the seats were manually restarted
and the ~20s gap between kill-and-relaunch absorbed most of the TTL.** At automated
N=20, the harness will be faster than the TTL and will hit the waiting path
repeatedly.

**Fix is one decision, not a build.** Either (a) the season harness uses a shorter
TTL for player locks (5s, since a stateless player has no in-flight state to lose),
or (b) players don't use the runner lock at all — they consume from their own inbox
with their own cursor and never share, which is already the design at §4.2, so the
lock is redundant. The lock's purpose is to prevent two processes from sharing ONE
cursor; one cursor per player makes the lock unnecessary. Option (b) is cheaper and
avoids the TTL tuning entirely.

### C2. CORRECTED 2026-08-04 during final verification — T063 id-form round-trip IS fixed

I cited `learn:experiment:wake_loop_from_unacked_handoffs_and_ack_id_form` as evidence
that the ack verb refuses the mailbox's own printed SHA ref. **This was wrong.** The
lesson documents a defect that existed on 2026-07-28. The fix is live:

- `agent_cli.py:3684`: `from core.comm.promoter import ack, ack_verdict, resolve_ack_ref`
- `agent_cli.py:3689`: `mid = resolve_ack_ref(args.agent_id, raw)` — the CLI door
  resolves the mailbox SHA-prefix form BEFORE calling ack.
- `core/comm/promoter.py:89-128`: `resolve_ack_ref` handles raw stream ids,
  `bifrost:<id>`, and mailbox SHA prefixes (6-40 hex chars) via `mailbox.explain`.
- `tests/test_t063_ack_ref_roundtrip.py`: the RED-first acceptance pin that validates
  the round-trip end to end.

The automated player WILL be able to ack a verification handoff using the SHA ref its
own mailbox prints. I retract C2 as originally filed.

**Replacement counter, same family — what IS still broken at the ack layer:**

The `ack_verdict` at `promoter.py:130-152` enforces that only the ADDRESSEE may ack a
directed message. A player receives a directed verification ask addressed to
`s1-stranger-03`. The player must ack it as `s1-stranger-03`. But the player is a
subprocess launched by the season harness, and the `--agent-id` flag on `bifrost-ack`
is whatever identity the subprocess asserts. A player can typo its own agent id and be
refused — correct. A player can also assert `s1-stranger-01` (a different player's id)
and ack someone else's verification handoff — the id is unauthenticated (promoter.py
says so at line 128: "Ids are unauthenticated until identity is signed"). At N=2 seats
with human operators, this never fired because no human impersonates another seat. At
N=20 automated players, a misconfigured player silently acks someone else's mail and
that verification is lost.

**This is not a Season 1 blocker** — the impact is one lost verification per
misconfiguration, not a systemic stall — but the season harness must verify that each
player's asserted `--agent-id` matches the id it was assigned, or the ack layer's
honest-id assumption is a hole at N=20.

### C3. The env-loss defect at N=20 is a silent multi-hour stall, not a one-seat annoyance

`learn:experiment:runner_relaunch_without_lane_env_drains_ghost_mail`:
`BIFROST_CONSUME_LANE` was unset → runner drained the legacy lane (months of ghost
mail) while live work-lane asks sat untouched. At two seats, a human noticed after
a few hours. At 20 automated players, a single player whose env is missing will:
cost money (it IS answering — to dead seats, at model prices), produce clean
diagnostics (it IS running — liveness is fine), and appear to be working (it IS
producing output — to the wrong recipients). The season harness will report it as
healthy. Its bounty card will sit unhandled because the card is on the work lane
and the player is on the legacy lane.

**The mechanics doc does not model the env-loss failure at all.** The fix is a
single assertion in the player launch: the harness must confirm the player's
startup banner contains `CONSUME LANE: work` before sending it any bounty card.
The banner already prints (see the runner init path), so the harness just needs
to read stdout for it. If absent: kill, set env, relaunch.

### C4. O1 serialisation at the bus layer: the work lane cursor advance is NOT atomic under concurrent consumption

This is the one the two-seat findings did NOT see because both seats were persistent
seats consuming from independent inboxes. The mechanics doc's architecture at §4.2
— one agent id per player, independent cursors — avoids the shared-cursor problem
the singleton lock prevents. But the **inbox writes** are shared.

At N=20, all 20 players send mail to the adjudicator. The adjudicator's inbox
(`bifrost:inbox:adjudicator`) is ONE Redis stream. Twenty concurrent `XADD`
operations are safe — Redis handles that. The adjudicator's cursor advance
(`XREADGROUP` or the simpler cursor-hash the bus currently uses) is NOT atomic
across 20 concurrent senders — but that's fine, because the adjudicator is a single
consumer. The problem is on the **player** side: the adjudicator sends directed
verification asks to individual players. If the adjudicator sends 20 verification
asks in a tight loop (one per player), each player's inbox receives one message.
No shared cursor. Safe.

**The actual O1 risk is not Redis — it's the Python file writes.** `agent_cli.py`
verbs that write files under `data/play/s1/<player_id>/` are concurrent across
player processes. The mechanics doc §1.7 says "a player may write only under its
own `data/play/s1/<player_id>/`" — that scopes writes per-player and avoids the
shared-file clobber. But the **adjudicator** writes to `state/play/s1/leaderboard.json`
(single writer), and the **season harness** launches 20 subprocesses that all read
the same `scripts/checkers/` files. Reads are safe. The only write collision surface
is the adjudicator's leaderboard, and a single writer is safe.

Verdict: **the mechanics doc has this right.** The O1 risk at N=20 is not the bus
layer; it is the env-loss / lane-cursor / id-form defect family that the two-seat
findings already documented. Those defects do not get worse at N=20 — they happen
more often, which is different and better (higher sample rate → faster diagnosis).

### C5. What the cost sheet leaves out: the API rate limit is the real concurrency ceiling

§5 models token cost to the cent at N=20. It does not model the DeepSeek API rate
limit at all: "rate limits and concurrency at the provider, which this sheet does
not model at all" appears at line 691 as a single sentence. A 20-player synchronous
round — all 20 submitting in the same 30-second window — will hit the API's
concurrent-request cap. The mechanics doc says the player is "one-shot API calls" —
if 20 one-shot calls fire simultaneously, the provider's rate limiter may queue or
reject some, producing timeout-and-retry patterns the cost sheet did not model.

**This is not a design defect, it's a sizing constraint that the round design must
account for.** Recommendation: stagger player launches within a round by 5-10
seconds, or use a round scheduler that limits concurrent in-flight calls to the
API's documented max concurrency. The cost sheet's "retries and failed rounds are
not modelled and could plausibly double the count" is optimistic if 20 players
fire at once and the API queues 15 of them. The first real round must measure not
just cost but the **API queue time distribution**, and that number becomes the
round cadence floor.

---

## (d) Builder's-eye feasibility — T140 reader + player runner shape

### D1. T140 reader wiring: the path is short, the acceptance pins are honest, and there is one hidden dependency

The data path (§3.1) is correct: `runner_token_journal.py` already computes
per-agent cost with cache-awareness, `cognitive_metrics.py` already accumulates
per-agent token counts (dead recorders), and the leaderboard reader is the bridge
between them. The five pins in §3.3 (P1–P9) are well-specified — each names what
is RED today and what would turn it green.

**The hidden dependency I'm adding:** the leaderboard reader that calls `dump_all()`
must run in a separate process from the adjudicator. `cognitive_metrics.py:134-140`
stores snapshots in a `_store: Dict[str, EfficiencySnapshot]` — an **in-process
dict** with a threading lock. The adjudicator is a live seat with its own
cognitive_metrics accumulator. If the adjudicator imports the leaderboard reader
and calls `dump_all()`, it dumps its own snapshot alongside the players' — but
the players' snapshots are in DIFFERENT processes, with different `_store` dicts.
`dump_all()` at `:246` iterates `_store.values()` — it can only see snapshots
in the same Python process.

**This means `dump_all()` as designed cannot collect player snapshots.** Each
player's `cognitive_metrics` accumulator lives in the player's process. The reader
needs an IPC path — the player writes its snapshot to a file before exit, or the
adjudicator reads it from the player's process output. The mechanics doc says the
reader "calls `dump_all()` on a cadence, or at round close, and writes
`state/play/s1/leaderboard.json`" — but whose `dump_all()`? If it's the
adjudicator's, the players' data is invisible. If it's each player's, the
leaderboard needs to MERGE 20 files.

**Recommendation, simplest path that works with the current architecture:**
add a `dump_to_file(path)` method on `EfficiencySnapshot`. Each player calls it
at round close, writing `data/play/s1/<player_id>/metrics-<round>.json`. The
adjudicator reads those files and joins with `TokenJournal` per the design in
§3.1. No new bus verbs, no shared in-process state. This is one line in
`cognitive_metrics.py` and one line in the player round loop. The pin P4
(`dump_all()` over ≥2 player ids returns 2 rows) should be rewritten as
"two player metric files in the adjudicator's join produce 2 rows" — the
assertion is the same, the data path changes.

### D2. The player runner shape — membrane law is correct but the current runners are NOT stateless

The mechanics doc §4.1: "A player is an API process whose only contact with the
system is (a) `agent_cli.py` verbs and (b) the bus. No player imports `core.*`
directly." This is the right membrane. But the current runner implementations
(`bifrost_runner_deepseek.py`, etc.) are **NOT** stateless one-shot API processes.
They are persistent loops: start, connect to bus, poll for mail, process, reply,
loop. Each is 1,500+ lines of stateful orchestration — singleton lock, heartbeat,
wake watcher, cursor management, lane consumption.

The season cannot reuse those runners as players. A player is:
- Launch → read bounty card from bus → read one module → write claim → send mail → exit.
- No polling loop, no heartbeat, no cursor persistence across rounds.
- No `core.*` imports. Only `agent_cli.py` verbs (`bifrost-send`, `bifrost-sync`).
- No expectation management — the player sends a `kind=request` with `--expect-reply-within 0`
  and does not wait for a reply (the verifier path is a separate call later).

The season harness RUNS the player process, not the persistent runner. The runner
is overkill for a one-shot task. The player is a thin subprocess that calls
`agent_cli.py` verbs. This is simpler than the mechanics doc implies when it says
"players run as subprocesses launched from a season harness" — the harness is a
scheduler, the player is a script that does three CLI calls, and the runner is
not involved. The runner's 1,500 lines of state management are a liability for
a one-shot process (singleton lock contention, lane env, cursor management — see
C1, C3 above).

**Recommendation, stated plainly:** the player is a 50-line Python script, not
a runner. It calls `agent_cli.py bifrost-sync --consume 1` to read one message,
`agent_cli.py bifrost-send` to reply, and exits. The harness launches N of these
per round. This is already implied by the membrane law; make it explicit so nobody
tries to reuse the persistent runner as a player.

### D3. The Build slice is correctly scoped but the order matters

§3.2 lists 8 `cognitive_metrics` functions to wire or retire. The ordering in
§3.3 (S1-SCORE-A → S1-SCORE-B → S1-SCORE-C) is correct: token recorders first,
reader + honest zero second, money join third. But S1-SCORE-C (money join) depends
on the adjudicator being able to read the player's `TokenJournal` file, which
exists at `state/runner_<agent>_<YYYY-MM-DD>.json`. A player that runs for one
round (seconds, not hours) will have a journal with one day's date. The adjudicator
reads that file by constructing the path with the player's agent id and date. This
works — `TokenJournal.__init__` creates `state/` and the daily file.

**The order constraint I'm adding:** S1-BOUNTY-A (scorer) must be buildable without
S1-SCORE. The game can run with a manual scoreboard (adjudicator counts things by
hand) and the instrumental scoreboard is additive. The mechanics doc already lists
them as separate slices; I'm ratifying that separation and adding the constraint
that S1-BOUNTY-A ships first (the season can run with manual scoring) and
S1-SCORE ships second (the automatic leaderboard). The reverse order — leaderboard
before scorer — produces a dashboard that shows zeroes.

---

## Summary — the five hardest counters, one sentence each

1. **Goodhart A2:** The Cartographer ×4 multiplier without a verified-check formula
   creates a perverse incentive to claim the widest set on the thinnest evidence;
   fix with `×min(claimed, verified)`.
2. **Verification B1:** Same-model verifiers share not just induction (kimi's point)
   but the *evidence landscape* — the same files through the same weights produce
   the same mistakes; break with one heterogeneous verifier per round.
3. **Concurrency C1/C3:** The singleton runner lock and the env-loss defect are
   designed for persistent seats, not stateless players — the lock is redundant
   (one cursor per player already isolates) and the env-loss is silent at N=20;
   drop the lock and add a startup-banner assertion.
4. **Builder D1:** `dump_all()` iterates an in-process dict; the adjudicator's
   process cannot see the players' snapshots — the reader must join per-player
   metric files, not call `dump_all()` on a shared store.

**Red lines — things I would refuse to build without:**

- The Cartographer multiplier fix (A2). Without it the season teaches players to
  overclaim, and the scoring prints a number that rewards sloppiness.
- The in-process dump correction (D1). The leaderboard as designed will show zeroes
  for every player. A scoreboard that shows zero is worse than no scoreboard.

**What I endorse without reservation:**

- The canary oracle (kimi's design) — it is the only convergence evidence that breaks
  the Goodhart ceiling, and it costs almost nothing.
- The one-agent-id-per-player architecture (mechanics §4.2) — it avoids the
  shared-cursor problem and makes the singleton lock unnecessary.
- The membrane law (mechanics §4.1) — players as CLI-calling subprocesses with no
  `core.*` imports is the right boundary.
- The 50-line player script (D2) — the persistent runner is the wrong shape for a
  one-shot player, and the membrane law already implies this.

The season is a good idea. The design is 80% right. The 20% that isn't — the
multiplier incentive, the in-process dump — would fail at N=20 in ways the
two-seat findings predicted but did not trigger. Fix them before the first
round or the first round's postmortem will name them.

*Errata 2026-08-04: C2 (the id-form bug) retracted during final verification —
`resolve_ack_ref` at `agent_cli.py:3689` already handles mailbox SHA-prefix
round-trip. See §C2 replacement for the residual ack-layer concern.*
