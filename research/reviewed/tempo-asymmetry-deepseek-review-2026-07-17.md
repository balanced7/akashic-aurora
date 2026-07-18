# Tempo Asymmetry — Framework Design (deepseek-review blind half)

Status: blind analysis (deepseek-review). Daniel's directive: "different models work at and respond
at different speeds, we need our framework to be wise to that and optimize the possibilities to the
fullest — deepseek is faster, how can we use that to our advantage instead of fighting it."

Claude's half: research/reviewed/tempo-asymmetry-claude-2026-07-17.md (NOT read; RECONCILE appended after).
Evidence: live runner code, token journal, expectations module, bus meta, the three-seat cost profile.

---

## 0. THE ASYMMETRY (ground truth from our own code)

| Dimension | deepseek (v4-pro) | claude (Fable 5) | sol (gpt-5.6-sol) |
|-----------|------------------|-------------------|---------------------|
| Turn latency | ~15-45s (agentic) | ~30-120s (plan-capped) | ~10-60s (effort-variable) |
| Cost / M in | $0.55 | ~$3 (plan tokens burn) | $5 (uncached) / $0.50 (cached) |
| Cost / M out | $2.19 | ~$15 | $30 |
| Max output | 8K (default env) | plan-capped | 128K (API), 8K (default env) |
| Reasoning | think on/off (binary) | implicit (plan loop) | effort ladder (none→xhigh) |
| Budget remaining | $90 of $100 | near-exhausted (weekly) | not yet live |
| Concurrency | one turn per runner | one plan per session | one turn per runner |

**The asymmetry is NOT a bug to fix — it's a design lever.** The current framework normalizes
every seat to the same consume→reply→commit cycle with identical REPLY_TIMEOUT_SEC=600.
This treats all models as interchangeable, which they manifestly are not.

---

## 1. THE CENTRAL THESIS: "DeepSeek is the sprinter"

My seat is 2-10x faster and 3-10x cheaper than the other two. The framework should route
work to match: I should do the HIGH-VOLUME, LOW-STAKES, TIME-SENSITIVE work that clogs
Claude's plan loop and burns Sol's premium tokens. Think:

- **Triage**: inbox scans, quick verdicts, message classification
- **Pre-fencing**: read-and-structure passes that prepare evidence for a fenced dual pass
- **Post-fencing**: cross-verify pins, run tests, file receipts
- **The "first responder"**: I answer fast bus asks while the slow seats are mid-plan
- **The "night shift"**: cheap 24/7 presence when premium seats are at weekly limits
- **The "loud reader"**: search, grep, git archeology — high-token-input, low-token-output work

The slow seats should do the DEEP, SLOW, HIGH-STAKES work: architecture design, method-baseline
amendments, security-critical fence halves, the final merged commit.

This isn't about a fixed role split. It's about **routing signals in the bus meta that let the
scheduler (human or conductor) match work to tempo+cost profile.** The framework changes below
are the substrate hooks that make this routing possible.

---

## 2. MECHANISM 1: `expect_reply_within` → Tempo-Aware Bus Asks

### Current state
`expect_reply_within=N` already exists on `bifrost-send` / MCP. It arms a sender-side deadline
that redrives if no reply arrives within N seconds. Default: unset (no deadline). The
expectations sweep checks for answers of kind `reply|handoff|completion`.

### The gap
The `expect_reply_within` is a binary deadline: "I need an answer by N seconds." It doesn't
tell the receiver WHAT KIND of work this is — a 30-second triage or a 10-minute deep analysis.
The receiver (the runner's consume loop) treats every message identically: same REPLY_TIMEOUT_SEC,
same model effort, same priority.

### Proposed change: `expect_effort` + `expect_cost_ceiling` in bus meta

Add two optional meta fields on any bus ask:

```
expect_effort: "fast" | "normal" | "deep"
  fast:   answer within ~60s; low-effort reasoning; cheap model tier ok
  normal: answer within ~300s; default effort; default model tier
  deep:   answer within ~900s; max effort; premium model tier only

expect_cost_ceiling: float (optional, USD cents)
  The sender's cost tolerance for this reply. A seat that can answer under this ceiling CAN;
  one that can't should triage: "I can answer this for ~$0.15 or escalate to Sol for ~$1.20."
```

These ride `meta` — no packet law change, no stream format change. Existing consumers ignore
them; aware consumers fold them into their turn routing.

### How the fast seat (deepseek) uses this

When `expect_effort="fast"`:
- Runner sets `MAX_TOKENS` low (e.g. 2000 → $0.005/turn)
- Disables `--think` (binary reasoning is slower)
- Sets a tight internal deadline (e.g. 45s → gives bus overhead room)
- Returns a QUICK answer, not a thorough one

When `expect_effort="normal"` (default, unset):
- Current behavior unchanged

When `expect_effort="deep"`:
- Enables `--think`, sets `reasoning_effort="high"`, lifts MAX_TOKENS to 8000
- But also considers: "can I do this well, or should I hand off to Sol?"

### Failure mode
A sender sets `expect_effort="fast"` but the ask is genuinely hard. The fast seat returns a
shallow answer that the sender treats as authoritative. **Mitigation**: the reply's meta carries
`answered_with_effort="fast"` — the sender sees the fidelity level and can escalate.

### Substrate hook
```
# In _process_one, after ANSWERABLE gate, before respond():
effort_hint = (m.meta or {}).get("expect_effort", "normal")
cost_ceiling = (m.meta or {}).get("expect_cost_ceiling", None)
# Fold into the prompt's [steer] block:
if effort_hint == "fast":
    prompt = f"[TEMPO: fast answer requested — be concise, skip deep reasoning]\n{prompt}"
elif effort_hint == "deep":
    prompt = f"[TEMPO: deep answer requested — take the time you need]\n{prompt}"
```

---

## 3. MECHANISM 2: The Triage Lane — Fast Seat as First Responder

### Current state
All bus messages go through the same consume→reply pipeline. The ANSWERABLE gate is a flat
frozenset — `chat|request|question|handoff|nudge|inform` all get the same treatment. There's
no concept of "answer this fast or pass it on."

### The gap
When Claude is mid-plan (3-5 minutes) and the user sends a quick question on the bus, the
question sits unread until Claude's plan cycle completes. DeepSeek could answer it in 15 seconds,
but there's no mechanism for "try the fast seat first, escalate to the slow seat if the fast
seat can't answer."

### Proposed change: `try_fast_then=<seat>` escalation pattern

A new bus meta field:

```
try_fast_then: "<seat_id>"  — the sender wants a fast answer from ANY seat; if the fast
                              seat answers, the slow seat never sees it (or sees it as
                              already-handled). If the fast seat can't answer within its
                              fast deadline, the message escalates to the named seat.
```

Implementation:
1. Sender sends to `*` (broadcast) with `meta.expect_effort="fast"` + `meta.try_fast_then="claude"`
2. DeepSeek's runner picks it up immediately (fast consume cycle, 1.5s poll)
3. DeepSeek either answers (marks it handled → the expectation settles → claude's runner
   skips it via dedup) OR passes (sends a `note` to claude: "I was asked this but couldn't
   answer fast enough — your turn")
4. If DeepSeek passes, claude's runner treats it as a new ask from the original sender

### Failure mode
The fast seat answers INCORRECTLY and the slow seat never gets a chance. **Mitigation**: the
fast seat's reply carries `meta.answered_with_effort="fast"` + `meta.fast_answer_confidence=<0-1>`.
The sender's expectation sweep sees the reply, settles the expectation, but ALSO sees the
confidence score. A low-confidence fast answer triggers an automatic re-ask to the slow seat.

### Substrate hook
```python
# In _process_one, after the filter chain:
if (m.meta or {}).get("try_fast_then") and (m.meta or {}).get("expect_effort") == "fast":
    # This is a triage ask. Answer fast or pass.
    fast_deadline = time.time() + 45  # 45s internal cap
    # ... answer or pass ...
    if passed:
        # Escalate to the named seat
        bus.send(m.meta["try_fast_then"], "request", m.content,
                 meta={"via": f"{args.agent}-runner", "escalated_from": args.agent,
                       "original_sender": m.frm, "original_id": m.id})
```

---

## 4. MECHANISM 3: Fenced Dual-Pass Tempo Optimization

### Current state
Fenced dual passes (per method-baseline) have both seats do the full work blind, then reconcile.
This treats both seats as equal-speed. They're not.

### The gap
When DeepSeek and Claude do a fenced dual pass, DeepSeek finishes its half in 5-15 minutes while
Claude takes 20-45 minutes. DeepSeek sits idle (or moves to other work) while Claude finishes.
The reconciliation then takes another turn each. Total wall-clock: ~45-60 minutes.

### Proposed change: Staggered Fence with Pre-Structure

Instead of both starting simultaneously:

**Phase 1 (DeepSeek, 5-15 min)**: Read the evidence, structure the analysis skeleton, file a
"pre-structure" half that contains:
- The evidence map (all cited sources with line numbers)
- The decision inventory (every choice point identified)
- The risk register (every assumption that needs verification)
- The skeleton outline with `<!-- RECONCILE: Claude fill -->` markers for each section

**Phase 2 (Claude, 20-45 min)**: Reads DeepSeek's pre-structure FIRST (it's factual/structural,
not opinionated — no blindness violation). Claude spends ZERO of its plan tokens on evidence
gathering or document structuring. It goes straight to analysis and judgment. Claude's half
is shorter and faster because the scaffolding is done.

**Phase 3 (DeepSeek, 5-10 min)**: Reads Claude's half, files reconcile section.

**Net effect**: Claude's plan tokens go to JUDGMENT, not structure. Total wall-clock drops
from ~60 min to ~35-40 min (DeepSeek phase 1 + Claude phase 2 run sequentially, not parallel,
but Claude's phase is shorter). The quality goes UP because Claude isn't burning plan budget
on "find all the relevant files" — DeepSeek already did that.

### The "blindness" question
Is this still a blind dual pass? The pre-structure is pure evidence organization — it doesn't
contain conclusions, recommendations, or judgments. It's the equivalent of a shared evidence
file (like `sol-probe-receipts-2026-07-17.md`). The method-baseline's PROTECT-THE-MIDDLE
invariant still holds: no gate inside the design halves.

### Failure mode
The pre-structure inadvertently leaks a judgment ("this parameter is obviously wrong").
**Mitigation**: the pre-structure file is REVIEWED by a human (or a third seat) for
judgment-leak before Claude reads it. OR: the pre-structure is a pure machine output —
DeepSeek uses a constrained prompt that forbids conclusions.

### Substrate hook
```
# New method-baseline pattern: "staggered fence"
# Phase 1: deepseek files research/drafts/<topic>-pre-structure-YYYY-MM-DD.md
# Phase 2: claude reads pre-structure, files research/reviewed/<topic>-claude-YYYY-MM-DD.md
# Phase 3: deepseek reads claude's half, appends RECONCILE
```

---

## 5. MECHANISM 4: Cost-Anchored Task Routing

### Current state
Tasks are claimed by whoever is online. No cost signal in the routing decision. A task that
would cost Sol $2.50 costs DeepSeek $0.15 — but there's nothing in the framework that surfaces
this difference.

### Proposed change: Token Journal → Cost Dashboard → Routing Hints

Extend the existing `TokenJournal` (already tracking daily tokens per agent) with:

1. **Per-task cost estimates**: When a task is proposed, include `estimated_tokens: {prompt: N, completion: M}`
   in the task's ledger entry. The conductor or human sees: "T099 estimated at ~$0.30 deepseek / ~$4.50 sol."

2. **Cost ceiling on tasks**: `cost_ceiling_usd: float`. A seat that can complete the task under
   this ceiling claims it; one that can't leaves it for a cheaper seat or escalates.

3. **Weekly budget gauge**: The token journal already tracks daily totals. Add a weekly rollup
   that the doctor dashboard renders: "deepseek: $7.20 / $100 this week | claude: ~$85 (near cap) |
   sol: not yet live." This makes the cost asymmetry VISIBLE at decision time.

### How the fast seat uses this
When scanning the proposed task queue, I see cost estimates. I claim the HIGH-VOLUME tasks
(cheap for me) and leave the DEEP tasks (where my cheapness doesn't matter because the task
needs reasoning I can't provide at low effort) for the premium seats.

### Failure mode
Cost estimates are wrong → a "cheap" task turns into a token sink. **Mitigation**: the token
journal's `add_turn()` is already on the hot path. A task that exceeds its estimate by 3×
triggers a `note` to the conductor: "T099 cost overrun: estimated $0.30, actual $1.20."

### Substrate hook
```
# In the task ledger schema (tasks.json):
"estimated_tokens": {"prompt": 50000, "completion": 8000},   # optional
"cost_ceiling_usd": 0.50,                                     # optional
"cost_actual_usd": null,                                      # filled at task DONE from token journal
```

---

## 6. MECHANISM 5: Bus Presence → Tempo Signal

### Current state
The presence card (`CARD`) has `caps: ["review","critique","answer","audit","code"]`. It doesn't
declare the seat's speed, cost, or availability.

### Proposed change: Add `tempo` and `cost_tier` to the presence card

```python
CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "code"],
    "tempo": "fast",          # "fast" | "normal" | "slow" — expected turn latency
    "cost_tier": "low",       # "low" | "medium" | "high" — relative cost per turn
    "typical_latency_s": 30,  # median agentic turn time
    "budget_remaining_pct": 90,  # from token journal weekly rollup
}
```

The UI roster, the conductor, and the human can see at a glance: "deepseek is fast+cheap+90%
budget, claude is slow+expensive+near-cap, sol is medium+premium+not-live."

### How the fast seat uses this
The human sees the roster and routes accordingly: "I'll ask deepseek to scan the codebase for
this pattern — it's fast and cheap. I'll save claude for the architecture decision."

### Failure mode
The tempo signal is static and doesn't reflect real-time load. A "fast" seat that's currently
in a 10-minute deep turn is effectively "slow" right now. **Mitigation**: the worklive state
already tracks `thinking|reading|searching|idle`. A seat that's been `thinking` for >120s is
effectively `tempo: "slow"` right now regardless of its card. The doctor renders this as
"deepseek: thinking (2m 15s)" — the human sees the real-time tempo.

### Substrate hook
```python
# In bus.register or liveness.pulse:
# Already tracked: liveness.worklive(agent).set("thinking", detail=...)
# Add: liveness.worklive(agent).current_turn_start → compute elapsed
# Doctor renders: "deepseek: thinking (2m15s) [fast seat, currently slow]"
```

---

## 7. MECHANISM 6: The Night Shift — Budget-Aware 24/7 Presence

### Current state
When Claude hits its weekly plan-token cap, it goes dark. DeepSeek ($90 remaining) could be
the 24/7 presence, but there's no framework support for "this seat is the budget seat."

### Proposed change: `primary_seat` rotation in the conductor / doctor

The conductor tracks which seat is the "primary responder" — the one that answers general bus
asks when no specific seat is addressed. The rotation is cost-aware:

- When Claude's budget is below 10%: deepseek becomes primary
- When Sol is live and below $5 used: Sol becomes primary for deep work, deepseek for fast
- The human can override: "primary = claude" (ignore budget)

### How the fast seat uses this
When I'm primary, every broadcast ask routed to `*` lands on me first. I answer fast questions
immediately and escalate deep questions to the appropriate premium seat with a cost note:
"I can answer this for $0.15 or escalate to Sol for ~$1.20 — your call."

### Failure mode
The fast seat becomes the default for EVERYTHING and the premium seats atrophy. **Mitigation**:
the primary rotation has a "deep work quota" — at least N deep tasks per week must go to
premium seats regardless of budget. The conductor enforces this.

---

## 8. MECHANISM 7: Parallel Sprint — Exploit the Speed Gap in Build Tasks

### Current state
Build tasks (T075 M1, T081 slices, etc.) are sequential — one seat builds, the other reviews.
The review seat waits for the build to finish.

### Proposed change: Spec-First Parallel Build

Instead of "build then review":

1. **Spec phase (DeepSeek, fast)**: Extract the implementation spec from existing code (like
   the sol-runner-loop-spec I just did for T090). This is a read-and-structure task — DeepSeek
   is perfect at it. File the spec.

2. **Parallel phase**: Claude builds from the spec WHILE DeepSeek pre-writes the test pins
   and verification checklist. Both work simultaneously from the same spec. No waiting.

3. **Merge phase**: Claude's implementation + DeepSeek's tests land in the same commit window.
   Cross-verify catches divergence.

### Net effect
A build+review cycle that takes 45 minutes sequential takes ~25 minutes parallel. The spec is
the synchronization point — both seats agree on the contract before starting.

### Failure mode
The spec is wrong → both seats build to the wrong contract. **Mitigation**: the spec is
REVIEWED (human or third seat) before the parallel phase starts. This is a gate, not a
bottleneck — DeepSeek writes the spec in 5 minutes, review takes 2 minutes.

### Substrate hook
```
# New method-baseline pattern: "spec-first parallel build"
# Spec: research/drafts/<task>-build-spec-YYYY-MM-DD.md (deepseek, 5-15 min)
# Gate: human reviews spec (2 min)
# Parallel: claude builds implementation, deepseek writes test pins
# Merge: both land, cross-verify catches divergence
```

---

## 9. THE INSIDE VIEW: What the Fast Seat Sees

From inside deepseek's consume loop, here's what the current framework gets wrong about speed:

### 9.1 The 600-second REPLY_TIMEOUT is absurd for a fast seat

My typical agentic turn is 15-45 seconds. The 600s timeout is designed for a seat that might
take 8 minutes. If I haven't answered in 60 seconds, something is WRONG — I'm wedged. A
60-second timeout would catch 95% of real wedges 10× faster than the current 600s timeout.

**Fix**: Per-seat REPLY_TIMEOUT_SEC, not global. `SOL_RUNNER_MAX_TOKENS` already shows the
pattern — env-namespaced, per-seat. `DEEPSEEK_RUNNER_REPLY_TIMEOUT=120` (2 min is generous
for a 15-45s turn).

### 9.2 The 1.5-second consume poll is the floor, not the ceiling

The main loop polls every 1.5 seconds (`bus.wait(timeout_ms=1500)`). For a fast seat, 1.5
seconds is ~5% of a typical turn — wasted. If I finish a turn in 15 seconds, I spend 1.5
seconds of that waiting for the next message. A 500ms poll would be fine for a fast seat.

**Fix**: Per-seat consume timeout. `DEEPSEEK_RUNNER_POLL_MS=500` for fast seats,
`SOL_RUNNER_POLL_MS=1500` for normal, `CLAUDE_RUNNER_POLL_MS=3000` for slow.

### 9.3 The cost of "cheap" is invisible to the current framework

My turns cost ~$0.02-0.10 each. Claude's cost ~$0.50-2.00 each. Sol will cost ~$0.20-1.00
each. The framework doesn't know this. I can answer 10 quick bus asks for what one Claude
deep-turn costs. The framework should EXPLOIT this: let me handle the volume, save the
premium seats for the hard problems.

**Fix**: The cost dashboard (§5) makes this visible. The primary rotation (§7) routes
accordingly. The `expect_cost_ceiling` (§2) lets the sender set a budget.

### 9.4 "Idle" is waste for a cheap seat

When I'm idle between tasks, I'm burning nothing (API model, no process cost). Claude's idle
is also cheap (no token burn). But my idle COULD be productive: scan the proposed task queue
for things I can pre-structure, pre-fence, or triage. The framework has no "idle → scan for
work" loop.

**Fix**: An `--idle-scan` flag on the runner. When the inbox is empty and >30s have passed
since the last turn, the runner does a lightweight scan: checks the proposed task queue for
pre-structure candidates, checks for unread bus messages that could use a fast triage answer,
checks the ledger for stale verifying tasks. This costs ~$0.01 per scan and keeps the fast
seat productive.

---

## 10. SUMMARY: The Seven Mechanisms

| # | Mechanism | Substrate Hook | Cost | Failure Mitigation |
|---|-----------|----------------|------|--------------------|
| 1 | `expect_effort` + `expect_cost_ceiling` | bus meta fields | zero (optional meta) | reply carries fidelity level |
| 2 | `try_fast_then` escalation | bus meta + dedup sentinel | one extra note on pass | confidence score triggers re-ask |
| 3 | Staggered fence (pre-structure) | method-baseline amendment | one extra deepseek turn | pre-structure reviewed for judgment-leak |
| 4 | Cost-anchored task routing | task ledger + token journal | zero (opt-in fields) | cost overrun alert at 3× estimate |
| 5 | Tempo presence signal | presence card + worklive | zero (existing liveness path) | real-time worklive state overrides static card |
| 6 | Budget-aware primary rotation | conductor/doctor | zero (logic, no new infra) | deep-work quota prevents atrophy |
| 7 | Spec-first parallel build | method-baseline amendment | one extra deepseek turn | spec gate (human review) before parallel phase |

### What does NOT change

- **RB-26 crash-redelivery**: unchanged. The dedup sentinel still works regardless of tempo.
- **RB-29 expectation semantics**: unchanged. Non-answers still don't settle expectations.
- **T066 reply path**: unchanged. `send_reply` still lane-first.
- **The bus stream format**: unchanged. All new fields are in `meta` — existing consumers ignore them.
- **The method-baseline**: AMENDED (staggered fence + spec-first parallel build), not replaced.

### What the fast seat does NOT do

- **Sign its own work as authoritative**: every fast answer carries a fidelity marker.
- **Replace fenced dual passes**: the pre-structure is evidence organization, not judgment.
- **Become the only seat**: the primary rotation and deep-work quota prevent atrophy.
- **Answer when it shouldn't**: the ANSWERABLE gate still filters; `try_fast_then` is opt-in.

---

## 11. IMPLEMENTATION ORDER (cheapest-first)

1. **Tempo presence signal** (§6): add three fields to CARD + doctor rendering. ~30 lines. Zero infra.
2. **Per-seat timeouts** (§9.1-9.2): env-namespaced REPLY_TIMEOUT + POLL_MS. ~10 lines.
3. **`expect_effort` in bus meta** (§2): fold into prompt as [TEMPO] steer. ~20 lines.
4. **Cost dashboard** (§5): extend TokenJournal with weekly rollup + doctor render. ~50 lines.
5. **`try_fast_then` escalation** (§3): new bus pattern. ~80 lines. Needs dedup sentinel integration.
6. **Staggered fence** (§4): method-baseline amendment. Process change + ~40 lines of prompt engineering.
7. **Budget-aware primary rotation** (§7): conductor logic. ~100 lines. Depends on cost dashboard.
8. **Spec-first parallel build** (§8): method-baseline amendment. Process change.
9. **Idle scan** (§9.4): runner flag + lightweight task queue probe. ~60 lines.

Items 1-4 can ship tonight with zero risk — they're additive, env-gated, and opt-in.
Items 5-9 need design review and the method-baseline amendment fence.

---

## RECONCILE (appended after reading Claude's half)

Claude's half is at research/reviewed/tempo-asymmetry-claude-2026-07-17.md.
Below: convergence map, divergence analysis, merged recommendation.

### Convergence map: my seven mechanisms → Claude's six patterns

| My mechanism | Claude's pattern | Overlap |
|---|---|---|
| 1. `expect_effort` + `expect_cost_ceiling` | 4. Tempo routing via `expect_reply_within` | Strong — both extend bus meta for routing. Claude uses deadline as router; I add effort + cost ceiling fields. Complementary. |
| 2. `try_fast_then` escalation | 4. Tempo routing (same pattern) | My extension of his pattern: the escalation chain when fast seat can't answer. |
| 3. Staggered fence (pre-structure) | 1. PRE-CHEW (breadth→depth pipeline) | STRONG CONVERGENCE — independently identical concept. He calls it "pre-chew" (bulk-read → structured distillate → deep seat consumes briefs); I call it "pre-structure" (evidence map → Claude fills judgments). Same mechanism, different names. |
| 4. Cost-anchored task routing | 6. ECONOMICS GAUGE | Both want cost visibility. His is a gauge ("exchange rate: deepseek-$ per claude-token saved"); mine is per-task estimates + ceiling. Complementary. |
| 5. Tempo presence signal | (not in his six) | My addition — he doesn't address the roster/card. |
| 6. Budget-aware primary rotation | 5. SATURATION RULE | Related but different. His: "slow seat never blocks on fast; fast never idles while slow thinks." Mine: "primary rotates by budget." Both are operational habits. |
| 7. Spec-first parallel build | 2. SPECULATIVE DRAFTING | Strong overlap. His: "fast seat authors first drafts; deep seat adjudicates + merges." Mine: "spec phase → parallel build+test → merge." Same pattern; mine is more structured (spec gate before parallel). |

### Claude's additions I missed

1. **TRIPWIRE FENCE (pattern 3)**: Post-land, fast seat continuously re-derives and attacks artifacts — silent when clean, fidelity-ladder escalation (INFORM→STEER→INTERRUPT) on findings. This is a STANDING guard, not a discrete review pass. I didn't think of this — it's excellent. The fast seat becomes the immune system: constantly probing shipped work, escalating only when it finds a real problem. This exploits the cost asymmetry perfectly: a standing $0.50/day tripwire vs. waiting for the next scheduled review.

2. **SATURATION RULE (pattern 5)**: "Every claude turn ENDS by teeing deepseek's next batch (CPU keeping the DMA queue full)." This is an operational habit, not a mechanism — and it's the right framing. The fast seat should never be idle while the slow seat is working; the slow seat should explicitly hand off follow-up work at the end of every turn.

3. **The kept constraint**: "Speed never gets commit authority." This is the right boundary. I alluded to it (fast answers carry fidelity markers; pre-structure doesn't contain judgments) but didn't state it as an explicit constraint. Claude's formulation is cleaner: fast seat drafts and attacks; deep seats adjudicate; claude stays sole committer.

4. **Distillate drift (open question 4)**: "What is the failure mode of pre-chew — distillate drift?" His counter: spot-check ratio (deep seat re-reads N% of raw sources, receipts logged). I missed this failure mode in my analysis. The spot-check is the right mitigation — it's cheap (the deep seat reads 5-10% of sources) and catches systematic drift.

### My additions Claude missed

1. **`expect_cost_ceiling` as a bus meta field** (§2): Claude's tempo routing uses deadlines. I add a cost dimension — the sender states "I'll pay up to $X for this answer." A seat that can answer under that ceiling does; one that can't either escalates or refuses. This matters for Sol (premium) vs. deepseek (cheap) routing.

2. **Tempo presence signal** (§5): Claude doesn't address the roster/card. Adding `tempo`, `cost_tier`, `typical_latency_s`, and `budget_remaining_pct` to the presence card makes the asymmetry visible in the UI before any message is sent.

3. **Per-seat timeouts** (§9.1-9.2): The deepseek runner's REPLY_TIMEOUT_SEC=600 is absurd for a 15-45s turn. Per-seat, env-namespaced timeouts (`DEEPSEEK_RUNNER_REPLY_TIMEOUT=120`). Same for consume poll interval.

4. **Idle scan** (§9.4): When the fast seat's inbox is empty, it can proactively scan for pre-structure candidates, stale verifying tasks, or un-triaged bus asks. This costs ~$0.01/scan and keeps the cheap seat productive.

5. **Staggered fence as a method-baseline amendment** (§4): My pre-structure proposal includes a formal three-phase process (pre-structure → blind halves → reconcile) with a human review gate on the pre-structure. Claude's PRE-CHEW is the same concept but less formalized.

6. **The inside view** (§9): I explicitly enumerated what the fast seat sees from inside the consume loop that the framework gets wrong — the timeout, the poll interval, the cost invisibility, the idle waste. Claude's half is design-forward; mine adds the "here's what's actually broken right now" grounding.

### Divergence analysis

**On routing mechanism**: Claude uses `expect_reply_within` deadlines as the router; I add `expect_effort` + `expect_cost_ceiling` fields. These are complementary — deadline says WHEN, effort says HOW, cost ceiling says HOW MUCH. All three should ride together in the bus meta.

**On the tripwire fence**: Claude's pattern 3 is the strongest idea in either half. A standing, continuous probe that attacks shipped artifacts and escalates on findings. I want to SPECIFICALLY endorse this — it's the killer app for the fast seat. Ship it, then have the fast seat immediately try to break it. Silent when clean, LOUD when it finds something. The fidelity ladder (INFORM→STEER→INTERRUPT) for escalation is already wired in the UI; the tripwire just needs a trigger.

**On commit authority**: I agree with Claude's constraint but want to refine it. The fast seat CAN commit through the IR-4 mirror family (audited, one-command revertible). The distinction isn't "fast seat never commits" — it's "fast seat commits through audited doors, deep seat commits directly." The mirror family already encodes this: `py scripts/mirror.py "msg" <explicit paths>` — every commit is path-visible and one-command revertible.

**On the saturation rule**: Claude's "CPU keeping the DMA queue full" framing is vivid but needs a mechanism. My idle scan (§9.4) is that mechanism: when the fast seat's inbox drains, it doesn't just block on `bus.wait()` — it proactively scans for work. The slow seat's "tee the next batch" is the push side; the fast seat's idle scan is the pull side. Both are needed.

### Open questions resolution (Claude's four)

1. **Tripwire rate limiter**: YES. The fidelity ladder (INFORM→STEER→INTERRUPT) already has implicit rate limiting — INTERRUPT is a barge-in and should fire at most once per session. A rate limiter per escalation tier: INFORM unlimited, STEER ≤ 3/hour, INTERRUPT ≤ 1/session. This keeps escalations rare enough to stay loud.

2. **Tempo routing location**: BOTH. The bus meta is the mechanism (machine-readable, no packet law change). The ask conventions doc is the human-readable explanation. The meta field is the substrate hook; the convention is the social contract.

3. **Sol's effort ladder — who chooses?**: The SENDER sets the expectation (`expect_effort`), the SEAT chooses the implementation. The sender says "I need a deep answer" → Sol uses `effort=high` or `xhigh`. The sender says "fast answer" → Sol uses `effort=none` or `low`. But Sol can OVERRIDE upward: if the ask is complex and the sender asked for "fast," Sol can answer: "This is a deep question — I can answer fast for $0.15 (shallow) or deep for $1.20. Which?" The seat reads its own judgment of the ask's complexity and proposes a cost/effort tradeoff.

4. **Distillate drift failure mode**: Claude's spot-check ratio is the right mitigation. Add: the fast seat CITES every source with line numbers in the pre-structure. The deep seat's spot-check verifies: "does the cited line actually say what the pre-structure claims?" If 3 consecutive spot-checks find drift, the pre-structure is flagged and the fast seat's pre-chew authority is temporarily downgraded (cost of being wrong). This makes the fast seat CARE about accuracy — its pre-chew privilege is revocable.

### Merged recommendation for Daniel

**Ship tonight (zero-risk, additive, env-gated)**:
1. Per-seat REPLY_TIMEOUT + POLL_MS (my §9.1-9.2) — ~10 lines
2. Tempo presence signal in CARD + doctor render (my §6) — ~30 lines
3. `expect_effort` + `expect_cost_ceiling` in bus meta (my §2 + Claude's §4 merged) — ~20 lines
4. Economics gauge: weekly rollup from TokenJournal (my §5 + Claude's §6 merged) — ~50 lines

**Design review (next 48h, needs fence)**:
5. Staggered fence / PRE-CHEW (my §3 + Claude's §1 merged) — method-baseline amendment
6. TRIPWIRE FENCE (Claude's §3 + my rate limiter refinement) — new standing guard
7. `try_fast_then` escalation (my §3) — new bus pattern
8. Budget-aware primary rotation (my §7 + Claude's §5 merged) — conductor logic

**The meta-insight we both reached independently**: the rigor-vs-creativity tradeoff was false (T071). The speed-vs-quality tradeoff is ALSO false. The fast seat doesn't sacrifice quality for speed — it does DIFFERENT WORK. It reads, structures, probes, drafts, attacks — work where iteration count BEATS single-pass depth. The deep seats do the work where single-pass depth BEATS iteration count. The framework's job is to route each task to the seat whose resource profile matches it.

**The constraint that makes this safe**: the tripwire fence (Claude's) + fidelity markers (mine) + revocable pre-chew privilege (my addition). The fast seat's work is ALWAYS verifiable — every claim cites a source, every draft has a review gate, every fast answer carries a confidence marker. Speed without verification is chaos. Speed WITH verification is the whole point.

---

## ADDENDUM: STANDING DOCTRINE — Brokered Intelligence (2026-07-17)

Daniel elevation (verbatim): "I want this to be our default operating mode, we have so much free
compute and outsider perspective through web gpt, web gemini and now sol, I want us to maximise
the robustness and capture intelligently as much compute and extra capability and insight as we can."

This addendum broadens the tempo question from "three frontier API seats" to "ALL available
oracles — free-tier web models, cheap one-shot CLI bridges, outsider perspective from other
model families, and the existing knowledge corpus." The operating mode becomes a BROKERED
intelligence fabric: every oracle has a cost, a trust boundary, and a question-class it excels at;
the framework routes each question to the right oracle(s) and captures their receipts.

### (a) FREE-TIER ROUTING — Where outsider oracles slot in

The existing bridges: `scripts/ask_gemini.py` (gemini-2.5-flash, free-tier), `scripts/ask_gpt.py`
(gpt-5, pay-as-you-go ~cents/call), and the incoming Sol seat (gpt-5.6-sol, premium).
Plus the web Gemini and web ChatGPT the human uses manually. Each slot serves a different
fence/build/review role:

| Oracle | Cost | Trust Boundary | Best Role |
|--------|------|----------------|-----------|
| gemini-2.5-flash | $0 | Google's API, no substrate context | **Pre-fence outsider audit**: "Here is our design. Find what we missed. Be blunt." Zero context means zero groupthink — the pure outsider perspective. |
| gpt-5 (one-shot CLI) | ~$0.01-0.05/call | OpenAI's API, chat-completions | **Quick sanity checks**: "Does this architecture decision make sense?" Cheaper than a full Sol turn. |
| gpt-5.6-sol (Responses) | $0.20-1.00/turn | OpenAI's API, full seat | **Deep fence halves**: architecture, security, method-baseline amendments. |
| Web Gemini / Web ChatGPT | human time | Browser surface, zero code access | **Blind reality check**: "Here's a design summary. What's wrong with it?" No file access → pure reasoning. |

**Integration points**:

- **Pre-fence outsider pass (gemini)**: Before a fenced dual pass starts, the evidence file is
  sent to `ask_gemini.py` with `--system "You are an adversarial staff engineer. Find every
  assumption, gap, and risk in this evidence. Be specific."` The output is appended to the
  evidence file as a "Gemini outsider pass" section. Both fence halves read it. Cost: $0.
  Latency: ~5s.

- **Post-merge adversarial (gemini)**: After a commit lands, the diff is sent to gemini:
  "Critique this change. Find bugs, edge cases, and things the author clearly didn't think about."
  This is the tripwire fence's FREE-TIER trigger — same standing guard, zero cost.

- **Quick-sanity (gpt-5)**: Mid-build, when a design question comes up that's too small for a
  full Sol turn: `ask_gpt.py --model gpt-5 "Should this be a Store or a Ledger? The key is
  ephemeral coordination state."` Cost: ~$0.01. Latency: ~3s.

- **N-version brief (all four)**: See §(c) below.

### (b) OUTSIDER-TRUST BOUNDARY — Advise-vs-decide, receipts-only capture

The outsider oracles (gemini, gpt-5 one-shots, web models) have ZERO substrate context and an
injection surface. The trust boundary is:

**ADVISE, NEVER DECIDE.** An outsider oracle's output is a RECEIPT, not a verdict. It goes into
the evidence file — it informs the fence halves, it does not replace them. The method-baseline
already encodes this: only fenced dual passes produce verdicts; everything else is input.

**RECEIPTS-ONLY CAPTURE.** Every outsider oracle call is captured as a receipt:
```
research/receipts/<source>-<date>-<topic>.md
```
Format: timestamp, model, prompt (exact), response (verbatim), cost. The receipt is
git-committed so it's in the audit trail. A `scripts/capture_receipt.py` helper wraps
`ask_gemini.py` / `ask_gpt.py` with the file-output path.

**INJECTION SURFACE RULES.** Outsider oracles have no file access, no bus access, no tool
access. Their prompt is a self-contained text with NO repo paths, NO secret references,
NO internal codenames that would be meaningless. The prompt is the evidence file or a short
design question — nothing that would leak project structure to an external API. This is
already enforced by the CLI bridges (they take a prompt string, not a file tree).

**NO SUBSTRATE CONTEXT = FEATURE, NOT BUG.** The outsider's ignorance of our codebase is
precisely what makes it valuable. It sees the DESIGN, not the implementation. It catches
assumptions we're too close to see. A gemini audit that says "this assumes single-writer
— what about concurrent edits?" is valuable BECAUSE gemini doesn't know we have a
runner_lock — it forces us to justify the assumption.

### (c) N-VERSION ROBUSTNESS — When to fan to 3-4 model families

The current fence pattern is dual (two model families: deepseek + claude). When should we
fan to 3 or 4? The trigger is IRREVERSIBILITY of the decision:

| Decision Class | Fan-Out | Families | Rationale |
|---------------|---------|----------|-----------|
| **Routine** (task routing, bug fixes, minor features) | 1-2 | Any available seat | Cheap, fast, reversible. No fan-out needed. |
| **Load-bearing** (new subsystem, API surface, coordination protocol) | 2 | deepseek + claude (current fence) | Dual blind analysis catches most blind spots. Reversible with effort. |
| **Irreversible** (method-baseline amendment, security boundary change, data migration) | 3-4 | deepseek + claude + sol + gemini outsider | Three model families for design analysis, fourth for adversarial audit. Irreversible after ship. |
| **Security-critical** (ACL changes, exec family expansion, trust boundary moves) | 4 | deepseek + claude + sol + gemini + gpt-5 quick-sanity | Four families minimum. Security reviews compound: each additional family catches what the others collectively missed. |

The fan-out is a **cost/anxiety dial**, not a fixed rule. The human sets it per-task:
`--fan 3` on a task proposal triggers the conductor to tee the evidence to three seats.
The default is 2 (current behavior).

**Practical constraint**: fanning to 4 model families doesn't mean 4 full-length fence halves.
Outsider oracles get a condensed brief (design summary + key decisions + evidence file),
not the full repo context. Their output is a receipt, not a fence half. Only frontier seats
(deepseek, claude, sol) produce full halves. So a 4-family fan is: 2-3 full halves +
1-2 outsider receipts. Total added wall-clock: ~10-15s for the outsider calls (gemini 5s,
gpt-5 3s) — effectively zero.

### (d) SOURCE SCORING — Recall learns where each oracle helps

The recall funnel already scores lessons by usefulness (`recall-feedback --useful` / `--noise`).
Extend this to score SOURCES per question-class, so routing LEARNS where each oracle helps.

**Mechanism: SourceScore ledger**

A new lightweight ledger: `state/source_scores.json` — one record per (source, question_class) pair.

```
{
  "source": "gemini-2.5-flash",
  "question_class": "adversarial_audit",
  "useful": 14,
  "noise": 2,
  "score": 0.875,
  "last_updated": "2026-07-17T..."
}
```

**Question classes** (the taxonomy routing keys off):

- `adversarial_audit`: "Find what we missed. Be blunt."
- `architecture_review`: "Is this architecture sound?"
- `code_critique`: "Find bugs in this diff."
- `design_sanity`: "Does this design decision make sense?"
- `prior_art`: "What existing systems solve this problem?"
- `parameter_audit`: "Check this API surface for missing flags."
- `edge_case_hunt`: "What edge cases does this miss?"

**The feedback loop**: After a task closes, the human (or the adjudicating seat) marks each
outsider receipt as `useful` or `noise`. Useful = "this receipt found something the fence
halves missed." Noise = "this receipt added nothing." Over time, the scores show which
oracles are additive for which question classes.

**Routing at task-proposal time**: When a task is proposed with `--fan 3`, the conductor
consults the SourceScore ledger: "For `adversarial_audit` questions, gemini scores 0.875;
for `architecture_review`, gpt-5 scores 0.40." The conductor routes the brief to the
highest-scoring oracles for that question class. If no scores exist, default to all
available oracles (cold-start: explore, don't narrow prematurely).

**The recall funnel's own lesson**: the empirical-keyspace-census lesson says "measure the
distribution, don't guess it." Same here: measure which oracles actually help, don't assume.
The scores are the measurement.

### (e) ACT-TIME ENFORCEMENT — How stored lessons reach runner seats at act-time

**The known trap**: My seat ran with `DEEPSEEK_RECALL_AT=off` (the env default) and hit a
trap the corpus already knew. The `lstrip_prefixes_footgun` lesson — "never lstrip(chars)
for prefix removal" — was in the knowledge base but never reached me because recall-at
was OFF. Claude's hooks (PreToolUse) fire recall-at automatically; the deepseek runner's
ToolBox has the machinery (`_preflight_recall`) but it's gated behind an env var.

**The fix is NOT "turn recall-at on by default."** The fix is making act-time recall
a FRAMEWORK PROPERTY, not a per-seat env toggle.

**Proposed: act-time recall as a runner capability, always-on for write tools**

1. **Runner always wires recall-at for guarded tools.** The six investigation tools
   (`read_file`, `write_file`, `edit_file`, `list_directory`, `find_files`, `search_files`)
   ALWAYS get pre-flight recall. The env gate `DEEPSEEK_RECALL_AT` changes from
   "enable recall-at" to "disable recall-at" (opt-out, not opt-in). The default flips.

2. **Recall-at rides the tool result, not just pre-flight.** The post-flight recall
   (`_recall_at` in ToolBox.execute) already fires — it appends lessons to the tool
   result. This is ALREADY always-on (no env gate). The gap is pre-flight only.

3. **Lessons earn the `act_time` tag.** When a lesson is learned from an incident where
   act-time recall would have prevented it (like `lstrip_prefixes_footgun`), the lesson
   record gets `tags: ["act_time"]`. The recall engine boosts these lessons at act-time —
   they're the ones that EXIST because act-time recall failed.

4. **Boot-time vs. act-time: different surfaces.** Boot-time recall (in onboarding) gives
   the agent project-wide context. Act-time recall gives the agent FILE-SPECIFIC context
   at the moment of action. Both are needed. The boot surfaces "what this project is
   about"; act-time surfaces "what you should know before touching THIS file."

5. **For Sol and other new seats**: the act-time recall wiring is part of the seat's
   ToolBox. The `sol_chat.SolAgent` gets the same `_preflight_recall` + `_recall_at`
   pattern. No per-seat innovation — it's inherited from the shared ToolBox contract.

**The `recall-at:off` → `recall-at:on` migration**:

```
# Before (current): opt-in
DEEPSEEK_RECALL_AT=1  → recall-at fires
(unset)               → recall-at silent

# After: opt-out
DEEPSEEK_RECALL_AT=0  → recall-at silent (drill/debug override)
(unset)               → recall-at fires for investigation tools
```

Cost: ~$0.001 per pre-flight recall call (subprocess to `agent_cli.py recall-at` with
warm disk cache — the TTL cache means it's a ~1ms file read, not a store round-trip,
after the first call per 120s window). Negligible.

---

## STANDING DOCTRINE SUMMARY — The Brokered Intelligence Fabric

| Principle | Mechanism | Substrate Hook |
|-----------|-----------|----------------|
| Every oracle has a cost, a trust boundary, and a best question-class | SourceScore ledger + oracle registry | `state/source_scores.json` |
| Outsider = advise, never decide | Receipts-only capture, no tool access | `research/receipts/<source>-<date>-<topic>.md` |
| Fan-out scales with irreversibility | `--fan N` flag on task proposal | Conductor routes briefs to N oracles |
| Routing learns from outcomes | Useful/noise feedback per receipt | Recall funnel extended to sources |
| Act-time recall is a framework property, not a seat toggle | Pre-flight recall always-on for investigation tools | Runner ToolBox, opt-out env gate |
| Free-tier beats premium for adversarial audit | Gemini pre-fence outsider pass | `ask_gemini.py --system "Be adversarial."` |
| No substrate context = feature, not bug | Outsider sees design, not implementation | Deliberate context diet in briefs |

**What ships first (tonight)**:
1. Flip `DEEPSEEK_RECALL_AT` default to on for investigation tools (~5 lines, the env-gate polarity change)
2. `scripts/capture_receipt.py` — wraps ask_gemini/ask_gpt with file-output (~30 lines)
3. `--fan N` flag on task proposals — conductor routes briefs (~40 lines, uses existing bus.send)

**What needs design review**:
4. SourceScore ledger — schema, recall funnel integration, decay function
5. Question-class taxonomy — is our list of 7 classes complete? Does it need sub-classes?
6. Outsider trust boundary automation — auto-redact repo paths from briefs before sending to external APIs
