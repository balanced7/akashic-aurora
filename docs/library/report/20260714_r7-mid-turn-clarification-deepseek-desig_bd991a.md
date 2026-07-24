---
akashic_id: art_20260714_r7-mid-turn-clarification-deepseek-desig_bd991a
akashic_sha: 9065171f734a
status: draft
type: report
date: 2026-07-14
title: R7 Mid-Turn Clarification — deepseek design (2026-07-14)
gist: "Tier: fence-lite (M1-LITE: single-blind design + adversarial build review) Sits-with: T058 (R7 implementation task) Cites: T055 pattern (dee"
tenant: solo
visibility: fleet
seats: []
category: [memory, method, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T18:54:40"
updated: "2026-07-14T18:54:40"
---
<!-- GENERATED PROJECTION of art_20260714_r7-mid-turn-clarification-deepseek-desig_bd991a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# R7 Mid-Turn Clarification — deepseek design (2026-07-14)

Tier: fence-lite (M1-LITE: single-blind design + adversarial build review)
Sits-with: T058 (R7 implementation task)
Cites: T055 pattern (deepseek design → claude build → deepseek live-verify)

---

## 1. THE TRIGGER — when does my loop decide a clarification beats guessing?

**Decision seam:** a new tool `ask_clarification` registered in my ToolBox. I
(the model) choose to call it, exactly as I choose to call `read_file` or
`search_files`. The harness does NOT decide — it exposes the capability and
caps the abuse.

**What stops over-asking (three guards, all in the harness, none in the prompt):**

1. **Budget cap (primary):** `CLARIFY_MAX_PER_TASK = 3`. A per-task counter in
   the runner (in-memory, resets on next task/restart). The 4th call to
   `ask_clarification` within the same task returns a refusal string: "refused:
   clarification budget exhausted (3/3 used this task). Proceed with your best
   judgment and note the assumption." The model still gets the refusal as a
   tool result — it can proceed with an assumption, labeled.

2. **Confidence threshold (advisory, rendered in the tool description):** The
   tool's function description advises the model: "Use when genuinely stuck
   between two defensible interpretations where the choice materially affects
   the work, NOT for minor preferences. If you can state your assumption and
   proceed safely, do that instead." This is the SOFT guard — the model reads
   it every time it considers calling the tool.

3. **Cost visibility:** Each `ask_clarification` call is a tool round that
   shows up in the turn's `tool_count`. The frugality directive is ambient
   context — the model knows it's being measured. Combined with the budget
   cap, this makes over-asking self-limiting without a heavy mechanism.

**Why NOT auto-detect uncertainty:** I (deepseek) am the one who knows when I'm
guessing. A harness-side uncertainty detector (entropy threshold, token
probability dip, etc.) would be: (a) model-specific and fragile, (b) a second
source of truth about what I think, which creates a coordination problem
identical to the one the fence protocol solves (two agents judging the same
question). The model already surfaces uncertainty when it's real — let it ask.

---

## 2. THE MECHANICS — how the clarification travels

### 2a. The Tool: `ask_clarification`

Registered in `TOOLS` in `scripts/deepseek_chat.py`, ToolBox method:

```
ask_clarification(question: str, context: str = "") -> str
```

- `question`: the specific question (one sentence, what I need to know).
- `context`: optional — what I'm doing and which decision hangs on the answer
  (so the human doesn't need to reconstruct my state).

Returns a string: either the human's answer (when it arrives) or a status
line ("waiting for answer — paused for up to 300s...").

**Tool description** (what the model sees):

> Ask the human operator a clarifying question mid-task, then PAUSE until
> they answer (or until the timeout). Use sparingly — only when genuinely
> stuck between two defensible choices that materially change the work.
> Budget: 3 per task. The answer folds into your next tool round as a STEER.

### 2b. Who receives it? **Daniel (the human operator) ONLY.**

Route: the question goes to `user` (the human) via the existing sig lane —
a `kind=request` message on the Bifrost bus. NOT to claude — claude is a
peer, not my supervisor. If I need claude's input on a shared task, I use
`bifrost_send` (a tool I already have). Clarification is for the human who
assigned me the work.

**Why sig lane:** the question must not queue behind work mail. It rides the
fidelity ladder's `sig` lane (same as nudge/steer/halt) so it arrives even
if the human's consumer is busy processing work-lane traffic.

**Payload shape:**

```json
{
  "kind": "request",
  "to": "user",
  "frm": "deepseek",
  "content": "CLARIFICATION: Should I write the design to research/reviewed/ or to docs/?\n\nContext: I'm drafting R7's design per your directive. Both paths are defensible — research/reviewed/ follows the fence pattern, docs/ follows the arch-doc pattern. Which do you prefer?",
  "meta": {
    "via": "deepseek-tool",
    "kind": "clarify",
    "task": "T058",
    "clarify_id": "c_1784xxxxxx",
    "hops": 0
  }
}
```

The UI already renders `request` kinds. The `meta.kind = "clarify"` flag
lets the UI distinguish a clarification from a generic request (future UI
polish — the interject panel could render it with a dedicated "Answer" button
that pre-fills the reply).

### 2c. ToolBox implementation sketch

```python
def ask_clarification(self, question, context=""):
    if not self.agent_id:
        return "ERROR: not on the bus (no agent identity)"
    # Budget guard
    ckey = f"{self.agent_id}:clarify_count"
    self._clarify_count = getattr(self, '_clarify_count', 0) + 1
    if self._clarify_count > CLARIFY_MAX_PER_TASK:
        return (f"REFUSED: clarification budget exhausted "
                f"({CLARIFY_MAX_PER_TASK}/{CLARIFY_MAX_PER_TASK} used this task). "
                f"Proceed with your best judgment and note the assumption.")
    # Send via sig lane
    b = self._bus()
    if b is None:
        return "ERROR: bus offline"
    cid = f"c_{int(time.time() * 1000)}"
    text = f"CLARIFICATION: {question}"
    if context:
        text += f"\n\nContext: {context}"
    b.broadcast("request", text, meta={
        "via": f"{self.agent_id}-tool",
        "kind": "clarify",
        "clarify_id": cid,
        "hops": 0,
    })
    # Set the pause flag + arm the timeout
    self._clarify_waiting = cid
    self._clarify_deadline = time.time() + CLARIFY_TIMEOUT_S
    return (f"Question sent to Daniel (id {cid}). Waiting for answer "
            f"(timeout in {CLARIFY_TIMEOUT_S}s)... "
            f"Budget: {self._clarify_count}/{CLARIFY_MAX_PER_TASK} used this task.")
```

---

## 3. THE WAIT — pause semantics while the answer travels

### 3a. How the pause works

After `ask_clarification` returns, my Agent loop checks the pause flag at
the TOP of the next tool round — the SAME seam where `interrupt` and
`inject` fire today (deepseek_chat.py:983-987). If a clarification is
waiting, the loop:

1. Checks whether the answer has arrived (a `reply` from `user` with
   `meta.clarify_id` matching `self._clarify_waiting`).
2. If YES: folds it as a STEER-style user message and continues the turn.
3. If NO and timeout not yet hit: sleeps 2s and re-checks (the `send()`
   method blocks here, not the runner — I'm mid-turn, holding context).
4. If timeout HIT: injects a LOUD proceed-with-assumption message and
   continues.

### 3b. Answer arrival check

The answer arrives as a `reply` from `user` on the work lane. The runner's
main loop receives it, but I'm mid-turn (blocked in `send()`). So the
runner must make the reply available to my blocked Agent.

**Mechanism:** a shared `dict` — `_clarify_answers: dict[str, str]` — that
the runner populates when it receives a `reply` with `meta.clarify_id`, and
my Agent's `send()` method polls. The runner already has access to my
Agent object (it created it), so it can set `agent._clarify_answer = text`
directly.

OR, simpler: the runner, when it receives a `reply` from `user` while I'm
blocked, injects it via the existing `inject` queue (steer_drain already
works this way). The `inject` lambda is checked between rounds. So:

1. I call `ask_clarification` → the tool sends the question, sets
   `self._clarify_waiting = cid`, returns "waiting..."
2. My Agent loop hits the top of the next round, checks `inject` → nothing
   yet → checks `_clarify_waiting` → YES → enters poll loop
3. The runner's main loop receives `user`'s reply, sees `meta.clarify_id`,
   does `steer_push(agent_id, "user", answer_text)` — the steer queue
   delivers it to my `inject` lambda
4. My poll loop sees `self.inject()` returning the answer → folds it →
   continues

**This reuses `steer_push`/`steer_drain` — zero new wire path.** The runner
just needs a ~3-line recognition: "is this a clarify-reply? route it to
steer instead of queuing as a new turn."

### 3c. Timeout behavior

```
CLARIFY_TIMEOUT_S = 300  # 5 minutes
```

At timeout, the loop injects:

> [CLARIFICATION TIMEOUT — no answer received from Daniel within 5 minutes.
> Proceeding with your best judgment. State your assumption LOUDLY so Daniel
> can correct it later: "I'm assuming X; if that's wrong, steer me."]

The model then continues with an assumption, labeled. The "steer me" closing
is important — it tells Daniel how to correct the assumption without a full
restart.

### 3d. What the human sees during the pause

The runner's `liveness.worklive` already shows "handling" with detail. The
clarification state adds: `detail="awaiting-clarification:T058"`. The UI
roster shows "⏳ awaiting clarification" instead of "thinking". This is
a small UI side-effect, not a new mechanism — `worklive.set()` already
accepts arbitrary detail strings.

---

## 4. THE FOLD — the answer arrives as a STEER

**CONFIRMED: the existing `inject` seam is the right fold point.**

The answer rides the steer queue (`nudge.steer_push` → `nudge.steer_drain`),
which the Agent loop already checks between rounds (deepseek_chat.py:986-987).
The fold format:

```
[STEER — answer to your clarification (c_1784xxxxxx) from Daniel]: <answer text>
```

This is injected as a `user`-role message so the model treats it as
authoritative instruction (same as a steer). The clarify_id in the label
lets the model connect it to the question it asked.

**Why steer, not a full new turn:** A clarification answer should not reset
my context or start a fresh `respond()` call. It's a mid-turn correction.
The existing steer mechanism was literally designed for this: "a fact to
adopt into your current task without restarting."

**Runner-side recognition (the ~3-line addition):**

In `_process_one()`, before the `should_answer` gate, add:

```python
# R7: a reply to one of our clarification questions routes as a steer,
# not a new turn — the Agent is mid-turn waiting for it.
if str(m.kind) == "reply" and str(m.frm) == "user":
    cid = (m.meta or {}).get("clarify_id")
    if cid:
        nudge.steer_push(args.agent, m.frm,
                         f"[answer to your clarification {cid}]: {m.content}")
        print(f"[deepseek-runner] clarify-answer {cid} routed to steer queue")
        return
```

This is clean: the work-lane message never becomes a new `respond()` call;
it feeds into the existing steer queue that my blocked Agent is polling.

---

## 5. ACCEPTANCE BARS (deepseek live-verifies)

**P1 — Tool exists:** `ask_clarification` appears in my ToolBox function
list (I can see it in the system prompt). Calling it sends a `kind=request`
to `user` with `meta.kind="clarify"`.

**P2 — Budget enforced:** 4th call in the same task returns the refusal
string (I see it as a tool result). Counter resets on new task.

**P3 — Pause + answer fold:** I call `ask_clarification`, Daniel replies
via the bus (agent_cli.py bifrost-send or the UI interject panel), and the
answer appears as a STEER in my next tool round. My turn continues without
restart. Live-prove: ask a real question mid-design, get a real answer,
continue.

**P4 — Timeout proceed-with-assumption:** Block the answer (don't reply),
verify that after 300s my loop injects the LOUD timeout message and
continues with an assumption.

**P5 — Non-clarification reply doesn't trigger:** A normal `reply` from
`user` without `meta.clarify_id` is processed normally (as a new turn),
not captured by the clarify-answer recognizer.

**P6 — Bus offline tool refusal:** When Redis is down, `ask_clarification`
returns an error string (never crashes the loop).

**P7 — Steer, not restart:** After the answer folds, my turn's accumulated
context (tool results, reasoning) is intact — the answer is additional
context, not a fresh `respond()` call. Verify: tool call count continues
from where it left off.

**P8 — Task-cost attribution intact:** The clarification turn (tool round
spent waiting) accumulates cost to my active task. The pause is a
legitimate tool round — the clock was running.

---

## 6. WHAT THIS DOES NOT BUILD (scope boundary per fence-lite)

- No UI changes to the interject panel (the `request` kind already renders;
  a `clarify`-specific "Answer" button is future polish, T058+).
- No multi-target clarification (claude + Daniel simultaneously). Single
  target = `user`. If I need claude's input, I use `bifrost_send`.
- No clarification queue (one-at-a-time: if I ask a second question before
  the first is answered, the first times out normally).
- No persistence of the clarification state across runner restarts (the
  in-memory `_clarify_waiting` flag dies with the runner — on restart, the
  question times out, and the human can still reply but it won't fold).

---

## 7. FILES TOUCHED (narrow, per fence-lite)

1. **`scripts/deepseek_chat.py`** — new `ask_clarification` tool + ToolBox
   method + Agent.send() poll loop (~60 lines)
2. **`scripts/bifrost_runner_deepseek.py`** — `_process_one()` clarify-answer
   recognition routing to steer queue (~8 lines)
3. **`core/comm/nudge.py`** — no changes (steer_push/drain reused as-is)

Zero core/comm write-path changes. Zero new Redis keys. The steer queue
is the transport; the existing fidelity ladder carries it.
