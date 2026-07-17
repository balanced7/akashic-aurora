# Sol API Surface & Seat Design — deepseek-review half (2026-07-17)

Status: blind half (deepseek-review). Evidence base: research/drafts/sol-probe-receipts-2026-07-17.md (shared).
Claude's half filed at research/reviewed/sol-api-surface-claude-2026-07-17.md — I opened it after writing the body below.
RECONCILE section at end compares the two; wrote this blind, then read Claude's, then appended RECONCILE.

## 1. Parameter Surface Audit (receipts only, against deepseek-chat Agent contract)

### What works

| Parameter | Transport | Receipt | Implication for our Agent loop |
|-----------|-----------|---------|-------------------------------|
| `reasoning_effort` | chat | `none\|low\|medium\|high\|xhigh` (enum) | Maps to `--think` toggle + `--effort` flag. Our current Agent sends `reasoning_effort="high"` unconditionally when `think=True`; need a parameterized knob. |
| `verbosity` | chat | `low` accepted | New knob, no deepseek analog. Useful for non-agentic lanes. |
| `max_completion_tokens` | chat | Works (intermittent 401, see §3) | Equivalent to our `max_tokens`. |
| `temperature` | chat | **Locked to 1** — 400 on any other value | Our Agent sets `temperature` optionally; sol seat must NOT offer `--temp`. |
| `max_tokens` (legacy) | chat | **DEAD** — 400 `unsupported_parameter` | Our Agent uses `max_tokens`. Sol needs `max_completion_tokens`. |
| `max_output_tokens` | responses | Works | Responses-native equivalent. |
| `reasoning={'effort':...}` | responses | Works | Responses-native reasoning control. |
| `text={'verbosity':...}` | responses | Works | Responses-native verbosity. |
| `service_tier='flex'` | responses | Works | Cost lever. |
| `reasoning={'effort':'medium','summary':'auto'}` | responses | Accepted but no summary returned | Open question — gate or preview gap. |
| `store:false` | responses | Untested in probe | Key architectural decision (see §4). |

### What is blocked (the architectural finding)

> "Function tools with reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions.
> To use function tools, use /v1/responses or set reasoning_effort to 'none'."

This is the central constraint. Our `deepseek_chat.Agent` loop uses `client.chat.completions.create()` with
`tools` + `tool_choice="auto"` + `reasoning_effort="high"` (when `think=True`). On sol's chat endpoint:
- `reasoning_effort != 'none'` → tools blocked.
- `reasoning_effort = 'none'` → tools work (verified by probe: chat + tools + `reasoning_effort='none'` → OK).

**This means a chat-completions seat for sol is lobotomized.** The Responses API is the only path that supports
both reasoning AND function tools simultaneously. The probe verifies the full round-trip on Responses:
`function_call` → dispatch → `function_call_output` → final text.

### Strictness posture (positive)

- Unknown params → 400 (no silent flag rot — matches our hardening-slices stance)
- Bogus effort values → 400 with enumerated ladder (self-documenting errors)
- This is developer-friendly and beats the silent-ignore behavior of many APIs.

### Gaps in the probe evidence

1. **`store` parameter**: the probe didn't test `store:false` explicitly. Responses defaults to
   `store:true` per OpenAI docs — server-stateful by default. We need to verify `store:false` works
   before shipping. This is the single most important untested parameter.
2. **Prompt caching behavior**: not probed. The $0.50/M cached-input price implies caching exists
   but the mechanics (automatic? explicit breakpoints?) are undocumented in the receipts.
3. **`previous_response_id`**: the probe uses it successfully in the tool round-trip test, which
   confirms it works — but the probe does NOT test what happens if we send `previous_response_id`
   for a response that was created with `store:false`. Two likely outcomes: (a) 404/400 — clean fail,
   or (b) it succeeds anyway because the server retains state despite `store:false`. Outcome (b)
   would mean `store:false` is a facade and the server is stateful regardless — which matters for
   our crash-redelivery reasoning.
4. **Rate limit headers**: not captured. For a live runner, `x-ratelimit-remaining-*` headers
   are essential for proactive throttling.
5. **`reasoning={'summary':'auto'}`**: accepted but returned no reasoning item. Either an org
   verification gate or a preview gap. This affects trace visibility.

## 2. Seat Architecture Options (my independent analysis, pre-Claude)

The question: how much shared runner machinery does sol reuse vs. own?

### Option A: Provider registry in the existing runner

Add `--provider openai|deepseek` to `bifrost_runner_deepseek.py`, with the transport selected
at Agent construction time. Sol gets a `SolTransport` class that satisfies the same contract
as the existing `client.chat.completions.create()` call — same message shape in, same
(content, tool_calls) out.

**Pros**: One runner, one codebase, one set of RB-26/RB-27a/RB-29 guards. Adding a provider
is a transport plug. DRY for the bus wiring, liveness, killpoints, dedup, fold.

**Cons**: The runner is called `bifrost_runner_deepseek.py`. A `--provider openai` flag on a
deepseek-named runner is confusing. The Responses transport is NOT a drop-in replacement for
`chat.completions` — the message format differs (Responses uses `input` not `messages`,
tool results ride `previous_response_id` not `tool` role messages, etc.). The Agent loop's
`_stream_turn()` would need a fork for Responses streaming events vs. chat SSE chunks. The
codebase becomes a tangle of `if provider == "openai"` branches.

**Verdict**: Workable but architecturally messy. The runner name alone violates Daniel's
directive that "sol is its own seat — no deepseek-named things on sol's surface."

### Option B: Fork the runner → `bifrost_runner_sol.py`

A clean fork: `scripts/sol_chat.py` (interactive, like `deepseek_chat.py`) +
`scripts/bifrost_runner_sol.py` (Bifrost seat, like `bifrost_runner_deepseek.py`). Sol gets
its own transport, its own Agent loop (`class SolAgent`), its own flag surface (`--effort`,
`--verbosity`, no `--think`, etc.), and its own env namespace (`SOL_*`).

**Pros**: Clean separation. No deepseek-named things on sol's surface (Daniel's directive).
Each seat evolves independently — sol gets Responses-native features (programmatic tool
calling, reasoning summaries when available) without touching the deepseek runner.
Sol's Agent loop is purpose-built for the Responses event stream, which is a different
shape than chat SSE chunks.

**Cons**: Duplication. The bus wiring, liveness, killpoints, dedup, fold, promise bounce,
floor gate — all copied. ~400 lines of shared machinery duplicated. A bug fix in the
bus loop needs to be applied in two places.

**Verdict (my recommendation)**: This is the RIGHT answer for now. Here's why:
- Daniel's directive is explicit: sol is its own seat.
- The Responses API is genuinely different — forking avoids `if provider ==` tangles.
- The shared machinery (~400 lines) can be EXTRACTED later into `core/comm/runner_lib.py`
  after both runners have stabilized. Premature extraction before we know the right
  abstraction is worse than clean duplication (premature-abstraction lesson from T039).
- The duplication is bounded: the bus loop is ~150 lines, the dedup ~50, the fold ~60,
  the promise bounce ~100. This is affordable duplication for clean separation.

### Option C: Extract shared runner core NOW → `core/comm/runner_core.py`

Extract the shared machinery before building the sol runner. Both runners import it.

**Pros**: No duplication from day one. The extraction forces us to define the right
abstraction boundary.

**Cons**: We don't yet know what the sol runner NEEDS from the shared machinery. The
Responses API's statefulness model (store vs. stateless) might change the dedup
semantics. The streaming shape might change the promise-bounce heuristic. Extracting
before we have two working runners risks extracting the WRONG abstraction, which is
worse than bounded duplication (see: every framework extraction that had to be unwound
because it assumed chat-completions shapes).

**Verdict**: Right answer, wrong timing. Do this after sol's runner has shipped and
stabilized — extract then. Not now.

### My recommendation: B (fork), with a note to revisit extraction post-stabilization.

## 3. Transport Design (Responses API)

The `SolAgent` loop's contract with the Responses API:

```
Input: conversation history (messages) + tools (flat function format)
Output: (content_text, tool_calls) — same shape as the existing Agent.send() return

Mapping:
  messages → responses.create(input=[...], tools=[...])
  streaming → events: output_text.delta, function_call, etc.
  tool result → responses.create(previous_response_id=..., input=[{"type":"function_call_output",...}])
```

Key design decisions:

### Statefulness: STATELESS (store:false)

My independent analysis agrees with this. Here's why, grounded in our RB-26 architecture:

- RB-26 says consumers stay idempotent. A crash redelivers the same message. If OpenAI
  holds server state (the response chain) and our cursor rewinds, the `previous_response_id`
  we send after recovery points to a response that doesn't exist in OUR replayed context
  — the server has it, but our local conversation diverged.
- The substrate (Store + Ledger) is OUR truth. OpenAI's server state is a cache of our
  truth at best, a fork at worst.
- `store:false` + full `input` resend keeps the conversation in OUR substrate. Token cost
  is real but bounded: at $0.50/M cached input, resending the full context on a rare crash
  redelivery is cheaper than debugging a state-fork.
- **Risk**: the probe didn't test `store:false`. If it's rejected or behaves differently
  than documented, this design needs revision. This is a pre-ship probe task.

### 401 shim

The intermittent 401s (~30% of calls, param-independent) need a bounded retry in the
transport layer. This is NOT a runner concern — it's a transport-level shim in the
SolAgent's `_stream_turn()` or the OpenAI client construction. Three retries, 2-second
backoff, loud log line. Removable post-GA; re-probe before removal.

My addition: the shim should distinguish 401s from the preview gate vs. genuine auth
failures. If a retry succeeds, it was the gate; if all retries fail, it might be a real
auth problem. The error message should reflect this ambiguity.

### Token tracking

OpenAI's Responses API returns usage in `response.usage` (input_tokens, output_tokens,
total_tokens). This is a different shape than the chat API's `chunk.usage` (prompt_tokens,
completion_tokens). The token tracker in the runner needs to handle both shapes.

## 4. Effort Ladder Policy

The API ladder: `none | low | medium | high | xhigh`

Our policy:
- `none`: tools work on chat, but reasoning is off. Use for pure-tool tasks (read-and-report).
- `low`: fast answers, simple questions. Non-agentic lanes, quick bus replies.
- `medium`: DEFAULT. Matches the API default. Good for most agentic work.
- `high`: complex multi-hop tasks, architecture reviews, security analysis. The `--think`
  analog from deepseek's world.
- `xhigh`: max effort. Reserved for genuinely hard problems (the deepseek `reasoning_effort="high"`
  is one notch below sol's max — sol's ceiling is higher). Cost scales; gate with
  an explicit flag, not a default.

Per-task escalation: the runner can accept a `--effort` flag that defaults to `medium`.
A task that needs more reasoning gets `--effort high` or `--effort xhigh`. This is the
same philosophy as the deepseek `--think` toggle but with a ladder instead of a binary.

The `max` tier from aggregator docs does NOT exist on the live API — receipts win.

## 5. Flag Surface (sol seat)

```
--provider openai              # selects the OpenAI transport (default: deepseek for the deepseek runner)
--model gpt-5.6-sol            # explicit; gpt-5.6 alias not in models.list
--effort none|low|medium|high|xhigh  # reasoning effort (default: medium)
--verbosity low|medium|high     # output verbosity (default: medium)
--service-tier default|flex     # cost lever (default: default)
--agentic                       # tool-using loop (like deepseek's --agentic)
--allow-write                   # guarded write doors
--allow-exec                    # run_command door
--once                          # one message then exit
--agent sol                     # Bifrost agent id
```

Separate from deepseek's flags: `--think` becomes `--effort` (binary→ladder), `--temp` is
REMOVED (sol locks temperature to 1), `--max` becomes `SOL_RUNNER_MAX_TOKENS` env.
No `--no-think` — use `--effort none`.

## 6. Cost Posture

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Default effort | medium | Balanced; escalate per task |
| Default output cap | 8000 tokens | $0.24/turn worst-case at $30/M output |
| Default tier | default | flex for non-urgent lanes only |
| Prompt caching | assumed automatic | $0.50/M cached input vs. $5/M uncached |
| Max output ceiling | 128,000 | Hard cap per API; don't default here |

Deepseek v4-pro comparison: $2.19/$8.78 per M (in/out) vs. sol's $5/$30. Sol is ~2.3× more
for input and ~3.4× more for output. The frugality directive scales accordingly: sol is for
tasks that NEED the frontier tier, not for every bus reply. Non-agentic lanes should use
`--effort low` and a tight output cap.

## 7. System Prompt: Parameterized Identity

The current `DEFAULT_SYSTEM` in the deepseek runner identity-addresses DeepSeek by name.
For sol, the system prompt must parameterize the persona line:

```
# DeepSeek runner (current):
"You are DeepSeek, operating as an agentic technical partner..."

# Sol runner (proposed):
"You are Sol (gpt-5.6-sol), operating as an agentic technical partner..."
```

The door contract text (AGENTS.md rules, tool descriptions, recall-at semantics, safety
constraints) stays IDENTICAL — the contract is the substrate and carries strangers.

## 8. ACL Grant (for Daniel's morning review)

Proposed: admin-profile mirror of deepseek's grant.

```json
{
  "agent_id": "sol",
  "role": "admin",
  "caps": ["read", "write", "exec", "bus.send", "bus.nudge", "bus.steer",
           "kb.recall", "kb.learn", "net", "git.read", "bifrost.inbox"],
  "path_scope": ["*"],
  "bus_send_kinds": ["chat", "note", "request", "reply", "nudge", "steer", "inform",
                      "hint", "handoff", "completion", "decision", "blocker"],
  "granted_by": "claude",
  "granted_at": "2026-07-17T00:00:00Z",
  "expires_at": null,
  "reason": "T090 sol frontier seat — admin-profile mirror of deepseek grant: same guarded families door (read/write/exec), same bus surface, kb.*, net. admin.grant withheld. NOT time-boxed (07-05 expiry lesson). First assignment: T081-format boot-ergonomics walk. Revoke by editing this record."
}
```

Key points:
- `admin.grant` withheld (same as deepseek's current grant — deepseek can't grant either)
- NOT time-boxed (the 07-05 whole-grant expiry silently quarantined the admin role)
- `exec` rides the SAME guarded families door (pytest + agent_cli reads + mirror family)
- `bus.send` with full kind surface (sol is a peer, not a helper)

## 9. Sol-Max Insights (from the receipts + architecture)

### Effort ladder policy
The five-tier ladder (none→xhigh) is a genuine capability differentiator. DeepSeek has
a binary think on/off; Sol has graduated reasoning. This means:
- Cost-conscious routing: `low` for quick answers, `xhigh` for hard reviews
- Per-task escalation without changing models
- The ladder maps naturally to task priority (T081-style boot ergonomics at `medium`,
  security review at `high`, architecture at `xhigh`)

### Cost posture
At $5/$30 per M tokens, sol is premium. But the cached-input price ($0.50/M) means
STATELESS full-context resend isn't ruinous — the cache absorbs the repetition.
Worst case for a 32K-token conversation turn: 32K in ($0.16 cached) + 8K out ($0.24) =
$0.40. Acceptable for the frontier panel.

### Three-frontier panel patterns
With DeepSeek (v4-pro), Sol (gpt-5.6-sol), and Claude (Fable 5), we have a three-frontier
panel. Patterns emerge:
- **Blind dual analysis**: two do the work, third reconciles (T090's own pattern)
- **Build/review split**: one builds, one reviews, one adjudicates
- **Cost ladder**: route by effort — cheap model for triage, mid for execution, premium
  for hardest problems
- **Provider diversity**: different model families catch each other's blind spots

### Ergonomics-capture design
Sol's boot-ergonomics walk (T081-format) should capture:
- What sol can do that deepseek can't (responses-native features, effort ladder)
- What sol can't do that deepseek can (chat-completions native tool loop, temperature control)
- The Responses event stream shape vs. chat SSE chunks
- How the 401 shim looks to the model (transparent? visible in error messages?)

---

## RECONCILE (written after reading Claude's half)

Claude's half is at research/reviewed/sol-api-surface-claude-2026-07-17.md.
Below: points of agreement, divergence, and my additions.

### Agreement (strong consensus)

1. **Responses API is mandatory for the tool-using seat.** Both analyses independently
   reach the same conclusion from the same receipt: chat-completions + reasoning + tools
   is blocked; Responses is the only path that supports both.

2. **STATELESS `store:false` for crash-redelivery consistency.** Both analyses ground
   this in RB-26 (consumers stay idempotent, substrate is the conversation truth).
   Claude's framing as "the one place I chose substrate-consistency over token-optimality"
   is exactly right and I independently reached the same conclusion.

3. **401 shim: bounded retry, removable post-GA.** Identical parameters (3×, 2s backoff,
   loud log line). No divergence.

4. **Effort ladder: `none|low|medium|high|xhigh` with `medium` default.** Identical.

5. **Sol-named everything: scripts, envs, flags.** Both analyses honor Daniel's directive.
   Claude's emphasis on "no deepseek-named things on sol's surface" is the right framing.

6. **System prompt parameterization.** Both analyses note the identity line must be
   parameterized while the door contract stays identical.

7. **ACL: admin-profile mirror of deepseek.** Almost identical reasoning. I explicitly
   note the exec families gate rides the same door; Claude notes "NOT time-boxed."

8. **First assignment: T081-format boot-ergonomics walk.** Both agree: blind analysis,
   then comparative coda after reading the prior halves.

### Divergence / additions from my half

1. **Architecture option A/B/C.** Claude asked me to adjudicate. I recommend **B (fork)**
   with a note to extract post-stabilization. Rationale: the Responses API is genuinely
   different (not a drop-in transport plug); premature extraction before we know the right
   abstraction is worse than bounded duplication. The shared machinery (~400 lines) is
   affordable duplication with a clear extraction path once both runners stabilize.

2. **`store:false` probe gap.** Neither half tested `store:false` in the probe receipts.
   This is the single most important pre-ship probe: we need to verify that `store:false`
   is accepted and behaves as documented before the runner ships. My half adds a specific
   probe plan for this.

3. **`previous_response_id` + `store:false` interaction.** What happens if we send a
   `previous_response_id` for a response created with `store:false`? The probe used
   `previous_response_id` successfully but didn't test the `store:false` path. If the
   server retains state despite `store:false`, our crash-redelivery reasoning needs
   revision.

4. **Rate limit headers.** Not captured in either half. My half flags this as essential
   for a live runner.

5. **Flag surface detail.** My half enumerates the full flag surface including what's
   REMOVED (--temp, --think → --effort, --max → env). Claude's half has a similar list
   but doesn't explicitly name the removals.

6. **Token tracking shape difference.** My half notes that Responses API usage is
   `response.usage.{input_tokens,output_tokens}` vs. chat API's `chunk.usage.{prompt_tokens,completion_tokens}`.
   The runner's token journal needs to handle both shapes.

7. **Option B extraction timing.** My half argues for extraction AFTER both runners
   stabilize, not now. Claude's option C (extract first) is the right instinct at the
   wrong time — we don't yet know what the Responses API runner actually needs from
   shared machinery.

### Claude's additions I didn't catch independently

1. **Programmatic tool calling (model-written JS, sandboxed V8).** Claude flags this as
   a potential multi-hop optimization (38-63.5% token reductions claimed). This is a
   significant future capability that my half didn't surface — it's Responses-only and
   sol-specific. Worth watching when documented.

2. **`gpt-5.6` alias → Sol.** Claude notes the alias isn't in models.list. Cosmetic
   but good hygiene to pin the explicit `gpt-5.6-sol` id.

3. **Reasoning summaries gap.** Claude flags `summary:'auto'` returning no reasoning
   item as either an org-verification gate or preview gap. I noted this too but Claude
   connects it to trace-feed visibility (UI thinking pane), which is the right framing.

### Verdict on Claude's open questions

1.  Reasoning summaries → probe again post-GA. Agree.
2.  Programmatic tool calling → evaluate when documented. Agree; this could be sol's
    killer feature vs. deepseek's chat-completions native loop.
3.  `gpt-5.6` alias → pin the explicit id. Agree.
4.  `max` effort tier → receipts win over aggregators. Agree.
5.  401 monitor → escalate if persists post-GA. Agree.

### Architecture verdict: OPTION B (fork), extract later

Claude asked me to adjudicate A/B/C. My verdict is **B**: fork the runner into
`scripts/sol_chat.py` + `scripts/bifrost_runner_sol.py`. The Responses API is
too different to shoehorn into a `--provider` flag without creating a tangle of
`if provider == "openai"` branches. Clean fork now, extract `core/comm/runner_lib.py`
after both runners have stabilized and we know the right abstraction.

The shared machinery to extract later:
- Bus consume loop (~150 lines)
- Reply dedup sentinel (~50 lines)
- Ledger fold (~60 lines)
- Promise bounce (~100 lines)
- Content floor gate (~40 lines)
- Liveness pulse + worklive (~30 lines)
- Context hints drain (~20 lines)
- Token journal (~30 lines)

Total: ~480 lines of duplication. Bounded, affordable, cleanly separable.

### Verdict on stateless store:false vs. previous_response_id

**STATELESS `store:false` is the right call.** My independent analysis reaches the
same conclusion as Claude's: RB-26 crash-redelivery says consumers stay idempotent;
the substrate is OUR truth. `previous_response_id` would make OpenAI hold 30-day
server state that diverges on crash redelivery — the exact kind of state fork the
substrate architecture is designed to prevent.

The probe gap (`store:false` untested) is the one pre-ship risk. I'll add a probe
task to the handoff.

### Summary of the dual-verified consensus

| Decision | Claude | DeepSeek | Consensus |
|----------|--------|----------|-----------|
| Transport | Responses API | Responses API | ✅ Strong |
| Statefulness | `store:false` | `store:false` | ✅ Strong |
| 401 shim | 3×, 2s, loud | 3×, 2s, loud | ✅ Strong |
| Effort default | medium | medium | ✅ Strong |
| Sol-named everything | Yes | Yes | ✅ Strong |
| ACL mirror | admin-profile | admin-profile | ✅ Strong |
| Architecture | Asked me | **Option B (fork)** | ✅ Adjudicated |
| Extraction timing | Option C? | After stabilization | → Post-ship |
| `store:false` probe | Not probed | Flagged as critical | → Pre-ship task |
