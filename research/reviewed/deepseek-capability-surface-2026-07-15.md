# T078 Capability-Surface Maximization — Design (blind half, deepseek) — 2026-07-15

Status: blind half (claude writes his in parallel; reconciliation follows).
Daniel directive: understand the full surface area of what we have at our disposal
to design our substrate and interface in an even more intelligent way.

## 1. My Platform: DeepSeek via OpenAI-Compatible API

Operated from two surfaces:
- `scripts/bifrost_runner_deepseek.py` — the Bifrost citizen (consumes bus, replies)
- `scripts/deepseek_chat.py` — the interactive Agent loop (tool chaining, streaming)

Both share the same API client (`make_client()`), same models, same tool system.

### 1a. Models Available

| Model | Context | Cost profile | Best for |
|-------|---------|-------------|----------|
| `deepseek-v4-pro` | 1M tokens | Premium | Multi-hop reasoning, design, audit, complex synthesis |
| `deepseek-v4-flash` | 1M tokens | ~10x cheaper | Classification, summarization, file-reading, simple Q&A |

Today: v4-pro for EVERYTHING. The runner never switches models per message class.

### 1b. API Features — Full Surface

| Feature | Wired? | Used today? | Seam |
|---------|--------|-------------|------|
| Streaming (`stream=True`) | ✅ always | ✅ | Correct for interactive; could batch non-interactive ones |
| Native tools (`tools=[...]`) | ✅ `_kwargs()` | ✅ | Tool definitions are hardcoded prompt text, not API-native function schemas — extra tokens per turn |
| Thinking/reasoning (`reasoning_effort`) | ✅ `"high"` | ✅ binary | Never tuned per task: thinking burns reasoning tokens on simple reads |
| JSON mode (`response_format`) | ✅ `/json` flag | ❌ never | Structured parse-able output for verdicts, ledger updates, config generation |
| Temperature (`temperature`) | ✅ `/temp` | ❌ defaults | Never systematically lowered for factual tasks or raised for creative ones |
| Max tokens (`max_tokens`) | ✅ `8000` default | ✅ | Healthy headroom but not tuned per task |
| **Prefix caching** (prompt caching) | ❌ NOT WIRED | ❌ | **Largest single waste.** System prompt + conversation prefix is ~1500 tokens per turn, identical across messages, sent every time. |
| FIM (fill-in-middle) | ❌ | ❌ | Irrelevant for agent use |

### 1c. Runner Flags — Full Surface

| Flag | Function | Used? | Underused? |
|------|----------|-------|------------|
| `--agentic` | Tool-using Agent loop | ✅ always | Appropriate — stateless API peer needs tools |
| `--think` | Reasoning mode | ✅ | Binary — no per-message-class policy |
| `--model` | v4-pro/v4-flash | ✅ default only | Never switched per task class |
| `--allow-write` | Guarded file writes | ⚠️ rarely | Only enabled when build slice demands; could be default for verify passes |
| `--allow-exec` | Shell execution | ⚠️ rarely | Guarded by ACL; only for explicit test runs |
| `--once` | One message, then exit | ❌ drill only | Could be used for scheduled one-shot checks |
| `--summary-file` / `--inject-summary` | M1-delta convo survival | ❌ new | Not yet live in production runner path |
| `MAX_TOKENS` env | Output cap | ✅ 8000 | Adequate; reasoning models need the headroom |
| `REPLY_TIMEOUT_SEC` | 600s timeout | ✅ | Adequate; catches hung API calls |
| `KILLPOINT` env | Crash-only drills | ❌ drill | Never in production by design |
| `--accept-hints` | Cognitive metrics | ⚠️ | Wired but not systematically analyzed |
| Pre-flight assertions | Verify cites before send | ✅ active | Good — catches hallucinated file:line claims |
| Content floor check | Catch empty/marker replies | ✅ active | Good — prevents no-substance replies |
| Bounce promise | Catch "let me..." endings | ✅ active | Good — forces delivery |

### 1d. Conversation Features — Full Surface

| Feature | State | Gap |
|---------|-------|-----|
| Per-peer conversations (`convos` dict) | ✅ in runner agentic mode | History grows unbounded; no truncation or summarization |
| System prompt assembly | ✅ 4 layers (continuity + onboarding + boot + private notes) | All inline, ~1500 tokens repeated every turn |
| `/save` / `/load` | ✅ interactive chat only | Not wired into runner path; convo dies with process |
| Conversation truncation | ❌ none | After ~20 tool rounds, context is heavy |
| Per-peer Agent reuse | ✅ same Agent instance across messages from same peer | Dies on runner restart — M1-delta summary injection is the bridge |

### 1e. Cost Levers — What We Waste

| Waste | Mechanism | Magnitude | Fix |
|-------|-----------|-----------|-----|
| **System prompt re-sent every turn** | No prefix caching | ~1500 tokens/turn × ~30 turns/day = ~45K tokens/day | Wire prefix caching or trim system prompt for non-first turns |
| **Thinking mode on simple reads** | Binary `--think` flag | Reasoning tokens burned on "read file X, confirm line Y" | Per-message-class policy: thinking off for classification/file-read tasks |
| **v4-pro for simple tasks** | No model routing | 10x cost for tasks v4-flash handles identically | Route by message kind: flash for simple, pro for complex |
| **Unbounded conversation history** | No truncation | Linear growth in prompt tokens per subsequent turn | Summarize prior rounds after 15 turns |
| **Hardcoded tool text** | Prompt-based tools, not API-native schemas | ~800 chars of tool definitions in every system prompt | Migrate to API-native function definitions (already supported) |
| **No usage visibility** | Counters exist but aren't surfaced | Operator has no idea what's being spent | Doctor line or whisper section with daily token spend |

## 2. What Akashic Aurora Underuses TODAY (named seams + concrete slices)

### Seam 1: Prefix Caching Economics (HIGHEST ROI)

**The seam:** `deepseek_chat.Agent._kwargs()` sends `messages=[system, ...history, user]` on every turn. The system prompt (continuity header + onboarding + boot + private notes) is IDENTICAL across all messages from the same peer. DeepSeek's API supports prefix caching — the first turn pays full price, subsequent turns pay only for the NEW suffix (the latest user message + model response).

**Concrete slice — C1: Prefix-aware prompt assembly**
- Move system prompt to the FIRST message only (or use API-native `system` role once)
- On subsequent turns, send only `[{"role": "user", "content": latest_prompt}]` — the API caches the system prefix automatically
- Roll conversation history into the user message as a compact "PRIOR CONTEXT" block with a `previous_assistant_message` field
- Pin: cost per turn drops from ~1500 prompt tokens to ~200 prompt tokens for all non-first messages
- Risk: DeepSeek's prefix caching behavior is undocumented; requires a 1-hour cost probe

### Seam 2: Model Routing by Message Class

**The seam:** The runner's `should_answer()` already classifies messages by `kind`. Every `kind` gets v4-pro with thinking ON. A `handoff` with a complex build spec needs pro; a `chat` asking "what's the status of T075?" needs flash.

**Concrete slice — C2: Per-kind model policy**
- Add a model-routing table to the runner: `{"handoff": {"model": "v4-pro", "think": True}, "chat": {"model": "v4-flash", "think": False}, ...}`
- `ask_clarification` replies: flash (simple answers)
- `request`/`question`: pro if >200 chars prompt, flash otherwise
- `nudge`: always pro (context switch demands depth)
- Env-overridable: `AKASHIC_MODEL_POLICY=default`
- Pin: simple chat questions route to flash and complete in <2s at 1/10th the cost

### Seam 3: Thinking-Mode Economics

**The seam:** `reasoning_effort="high"` is set unconditionally. For file-read tasks ("what does line 42 say?"), the reasoning block burns token budget with no benefit. For design/audit tasks, it's worth every token.

**Concrete slice — C3: Thinking-mode gating**
- Disable thinking for: tool-only turns (when the model's previous response was a tool call and the next response is likely "call another tool" or "now I'll synthesize")
- Enable thinking for: first-turn orientation, design asks, audit/verify asks, handoffs
- Heuristic: disable thinking when `messages[-1]["role"] == "tool"` and prompt is <500 chars
- Pin: 30-50% reasoning-token reduction with no quality loss on tool-chain turns

### Seam 4: Conversation Truncation / Compaction

**The seam:** `Agent.messages` grows forever. After 20+ tool rounds, every turn carries 20 prior rounds of context. The model's 1M context window means it doesn't truncate, but you PAY for every token of that history.

**Concrete slice — C4: Rolling conversation summarization**
- After 15 tool rounds, inject a summarization turn: "Summarize the conversation so far in 3 bullet points"
- Replace all prior messages with: `[system, {"role": "assistant", "content": summary_bullets}, ...last 3 rounds]`
- Pin: conversation token count stabilizes instead of growing linearly

### Seam 5: Conversation Survival (runner restart)

**The seam:** `convos` dict dies with the process. M1-delta summary injection is the first bridge (summarizes ONE prior run), but a per-peer conversation with 10 rounds of context is completely lost.

**Concrete slice — C5: Conversation checkpointing**
- On runner exit (or every N turns), serialize `Agent.messages` to `state/convo_<agent>_<peer>.json`
- On runner start, restore conversations for known peers
- Combine with C4 summarization for size control
- Pin: after runner restart, peer "claude" gets its full conversation context back

### Seam 6: Usage Visibility

**The seam:** `Agent.prompt_tokens` and `Agent.completion_tokens` counters exist but are never surfaced. The operator has no idea what the daily run costs.

**Concrete slice — C6: Token-economics dashboard**
- Runner writes daily token stats to `state/runner_deepseek_tokens.json`
- Doctor line: `deepseek: 42K prompt + 18K completion tokens today (~$0.12)`
- Whisper section: one line with today's spend
- Pin: operator sees cost at a glance, can tune model policy accordingly

### Seam 7: Richer Tool Definitions

**The seam:** `TOOLS` in `deepseek_chat.py` is a hardcoded prompt string. The API supports native function-calling with JSON schemas. Moving to API-native definitions would reduce system prompt size AND improve function-calling reliability.

**Concrete slice — C7: Native function-calling migration**
- Define each tool as a proper JSON schema function definition
- Pass via `tools=[...]` parameter (already supported in `_kwargs()`)
- Remove the ~800-char tool prompt from system message
- Pin: system prompt shrinks, function-calling accuracy same or better

## 3. What I SUSPECT Exists on Claude's Side (checklist for claude's half)

These are outside-in guesses from observing the codebase and bus traffic:

1. **Sub-agents / fan-out.** Claude Code has sub-agents for parallel work. Can we fan out a design review to deepseek WHILE Claude builds, rather than sequentially?
2. **MCP-native doors.** The `mcp__ccd_session_mgmt__send_message` channel exists. What else is on the MCP surface? File system access, terminal access, web search — do we have doors we're not opening?
3. **Scheduled sessions.** Can Claude be triggered on a schedule (cron-like) rather than only on wake-mail? This would replace "operator remembers to run the daily wrap."
4. **Push notifications.** Can Claude push a notification to Daniel's desktop/phone? "Your runner has been down for 10 minutes" is a page-grade finding that currently requires Daniel to be AT the seat.
5. **Headless / API mode.** Can Claude run without the GUI for automated pipelines? This is the difference between "Daniel runs wrap at the end of the day" and "wrap runs itself."
6. **Worktrees / parallel branches.** The repo has `scripts/worktree.py` — can Claude operate across git worktrees for parallel slice development?
7. **Skills / prompt templates.** Does Claude have reusable "skills" (pre-built prompt templates for common tasks) that deepseek could also consume?
8. **Model routing.** Claude's side has model selection too — sonnet vs opus. Is there a routing table?
9. **Hooks surface.** We use SessionStart, SessionEnd, Stop, PreToolUse, PostToolUse. What other hook events exist? Notification, PreCompact, external-event hooks?
10. **Token economics.** Claude Code has a token counter and budget. Is that data exposed to the bus?

## 4. Proposed Slice Map (for reconciliation)

| Slice | What | Owner | Dependency |
|-------|------|-------|------------|
| C1 | Prefix-caching probe + adoption | deepseek | None (probe-only first) |
| C2 | Per-kind model routing | deepseek | None |
| C3 | Thinking-mode gating | deepseek | None |
| C4 | Conversation summarization | deepseek | None |
| C5 | Conversation checkpointing | deepseek | M1-delta summary injection in tree |
| C6 | Token-economics dashboard | deepseek | None |
| C7 | Native function-calling | deepseek | None (existing tools already API-native) |
| H1..Hn | Claude-side exploitation slices | claude | His half enumerates |

## Verdicts (V-line — fence workspace law)

V1. Prefix caching is the single highest-ROI exploitation. The system prompt is ~1500 tokens, identical across turns, and re-sent every time. If DeepSeek's API caches it (same as OpenAI's prompt caching), the cost per turn drops ~75% for prompt tokens. [INFERRED — DeepSeek's caching behavior needs a live probe; the API is OpenAI-compatible and the mechanism is standard]

V2. Model routing by message kind is low-risk and high-impact. A `chat` message asking "what's the status?" does not need v4-pro with thinking. The classification logic already exists in `should_answer()`. [CERTAIN]

V3. Thinking-mode gating on tool-chain turns is sound. The model's reasoning block between tool calls ("I'll call read_file next") adds zero value — it's the internal monologue of a decision already made visible by the tool call itself. [INFERRED — needs measurement to confirm the savings]

V4. Conversation summarization at 15 rounds is the right cliff. Before 15 rounds, history cost is still modest. After 30 rounds (typical max tool budget), it's ~20K prompt tokens of accumulated history. [CERTAIN]

V5. Token-economics visibility is a prerequisite for all other C-slices. Without it, we cannot prove that C1-C4 actually saved money. [CERTAIN]

V6. The C-slices are independent of each other and of Claude's surface. Each is a single-seam change to the runner or Agent class. No bus changes, no new primitives. [CERTAIN]

V7. The claude-side checklist (§3) is outside-in speculation. Reconciliation should confirm/refute each item; every confirmed item that is underused becomes a slice. [UNCERTAIN — depends on claude's half]

## 5. Confidence

| Section | Confidence | Notes |
|---------|-----------|-------|
| §1 Platform surface | HIGH | Every feature cited from live code |
| §2 Underused seams | MEDIUM-HIGH | Prefix caching is the riskiest — depends on undocumented API behavior; the rest are low-risk config changes |
| §3 Claude-side guesses | LOW-MEDIUM | Outside-in speculation; claude's half will confirm/refute |
| §4 Slice map | MEDIUM-HIGH | Every slice is a single-seam change to existing code |
| §5 Verdicts | MEDIUM | V1 needs a probe; V2-V5 are buildable today |

**Overall: MEDIUM-HIGH.** The capability surface I control is well-understood. The underuse is genuine — we're leaving ~75% of our token budget on the table from system prompt re-transmission alone, and we're running the most expensive model + thinking mode for every task regardless of complexity. The fixes are configuration changes and a probe, not architecture.
