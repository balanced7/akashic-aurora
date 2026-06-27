# Framework Protocol: How Everything Works Together
**The standardized protocol that makes the multi-agent system work**

---

## The Big Picture

This is a protocol. Not code. Not theory. A **protocol**.

A protocol is a standard way things communicate. Like HTTP for web browsers, or TCP/IP for networks.

Our protocol defines:
- How agents join the system
- How they communicate (signals)
- What context they can access
- How they hand off to each other

If agents follow this protocol, the system works. If they don't, it breaks.

This protocol is:
✅ **Model-agnostic** - Works with Claude, Llama, GPT, anything
✅ **Language-neutral** - Just text, no special syntax
✅ **Learnable** - Any agent can understand it from scratch
✅ **Extensible** - Can grow without breaking compatibility
✅ **Observable** - Can see everything happening

---

## The Protocol: Step by Step

### Step 1: Agent Initialization

**When:** Agent starts working
**What happens:**

1. Agent reads AGENT_ONBOARDING.md (this is required)
   - Understands what signals are
   - Understands what context is available
   - Understands how to use the system

2. Agent initializes the coordinator
   ```
   [Coordinator available]
   [Ready to emit signals and receive context]
   ```

3. Agent checks for BRIEFING
   - If first agent: No briefing (start fresh)
   - If handoff: Read briefing from previous agent
   - If mid-session: Continue from saved state

4. Agent reviews DECISION_CACHE
   - Understands what's been decided
   - Won't re-decide settled questions
   - Can reuse decisions if applicable

**Duration:** <2 minutes
**Overhead:** None (reading, thinking)

---

### Step 2: Agent Works

**When:** Agent is actually doing their task
**What happens:**

1. Agent works normally (whatever their task is)

2. When they make a decision, they emit a DECISION signal
   ```
   DECISION: {decision_name}
   ├─ Reasoning: ...
   ├─ Outcome: ...
   ├─ Confidence: ...
   └─ Reversible: ...
   ```
   - Signal is stored in coordinator
   - Signal is logged to Redis/files
   - Other agents can potentially reuse this decision

3. If they hit a blocker, they emit a BLOCKER signal
   ```
   BLOCKER: {blocker_name}
   ├─ Severity: ...
   ├─ Description: ...
   ├─ Impact: ...
   └─ Workaround: ...
   ```
   - Signal is stored in coordinator
   - Coordinator monitors blocker escalation
   - Other agents can learn about the blocker

4. Agent completes their work (or hands off)

**Duration:** Varies (hours/days)
**Overhead:** ~0.2-0.5ms per signal (<1% of work time)

---

### Step 3: Agent Completion

**When:** Agent finishes their task
**What happens:**

1. If agent is done completely: Emit COMPLETION signal
   ```
   COMPLETION: {task_name}
   ├─ Success: ...
   ├─ Output: ...
   ├─ Metrics: ...
   └─ Learned: ...
   ```

2. If handing off to another agent: Emit HANDOFF signal
   ```
   HANDOFF: {next_agent}
   ├─ Task: ...
   ├─ Context: ...
   ├─ Blockers: ...
   └─ Learned: ...
   ```

3. Coordinator processes signals
   - Creates briefing for next agent
   - Caches new decisions
   - Updates project state
   - Logs completion metrics

4. Next agent initializes, receives briefing
   - Cycle repeats with fresh agent
   - Zero context loss
   - No re-reasoning needed

**Duration:** <1 minute
**Overhead:** Briefing generation (background)

---

## The Context Lifecycle

### What Context Is Available

At any point, an agent can access:

```
AVAILABLE_CONTEXT:
├─ DECISION_CACHE
│  └─ All decisions made so far (cached, queryable)
├─ PROJECT_STATE
│  └─ Current phase, blockers, timeline
├─ AGENT_MANIFEST
│  └─ Who's done what, who's available
├─ BLOCKERS
│  └─ All known obstacles
└─ BRIEFING (if handed off)
   └─ Specific context for this agent's task
```

### How Context Flows

```
Previous Agent Work
        ↓
    [Emit signals]
        ↓
    [Complete task]
        ↓
    [Coordinator processes]
        ↓
    [Context synthesized into briefing]
        ↓
    [Next agent reads briefing + context]
        ↓
    [Starts fresh with full history]
```

### Context Guarantees

- ✅ **No data loss** - Everything is recorded
- ✅ **Queryable** - Can ask "what was decided about X?"
- ✅ **Understandable** - Format is readable, not opaque
- ✅ **Actionable** - Contains what agent needs to work
- ✅ **Compressed** - No unnecessary details

---

## Signal Flow

### How Signals Move Through System

```
Agent emits signal
        ↓
    [Signal recorded]
        ├─ Redis (if available)
        └─ JSONL files (always)
        ↓
    [Coordinator reads signal]
        ├─ If DECISION: Cache it, update project state
        ├─ If BLOCKER: Monitor it, escalate if critical
        ├─ If HANDOFF: Create briefing
        └─ If COMPLETION: Log metrics, mark phase done
        ↓
    [Signal accessible to other agents]
        ├─ In DECISION_CACHE (for reuse)
        ├─ In BLOCKERS (for awareness)
        └─ In briefing (for next agent)
```

### Signal Storage

Each signal is stored in two places:

**Location 1: Canonical Stream** (for ordering)
```
Redis Stream: agent:events
├─ Every signal from every agent
├─ Ordered by timestamp
├─ Kept for ~1 week
└─ Source of truth
```

**Location 2: Local Files** (for persistence)
```
JSONL files: E:\AI-Setup\session_logs\
├─ Backup of every signal
├─ Always available (even if Redis down)
├─ Indefinite retention
└─ Analyzable by scripts
```

Both are synchronized (dual-write). If Redis is down, files work. If Redis is up, files are backup.

---

## The Coordinator's Job

The Coordinator runs in the background and:

1. **Monitors signals** (passively reads from stream)
2. **Caches decisions** (stores in memory for reuse)
3. **Watches blockers** (escalates critical ones)
4. **Synthesizes briefings** (creates handoff context)
5. **Maintains state** (current project status)

The Coordinator is:
- ✅ **Invisible** (<5% CPU, <200MB RAM)
- ✅ **Asynchronous** (doesn't block agents)
- ✅ **Always available** (runs continuously)
- ✅ **Gracefully degradable** (works with file fallback)

```
Agent 1 working → Coordinator monitoring
    ↓                     ↓
Emits signals ←→ Processes signals
    ↓                     ↓
Completes → Coordinator generates briefing
                     ↓
                  Agent 2 reads briefing
                     ↓
                  Agent 2 works (informed)
```

---

## Cross-Model Compatibility

This protocol works with **any model** because:

### 1. It's Text-Based
- Signals are text, not binary
- Any model can read and emit text
- No special training needed

### 2. It's Learnable
- Agents understand it from documentation
- No model-specific hacks
- Same protocol for Claude, Llama, GPT, etc

### 3. It's Structured
- Consistent format
- Parseable by code
- But human-readable too

### 4. It's Language-Neutral
- Examples here are in English
- Could be in any language
- Model can understand and operate

### Example: Same Protocol, Different Model

**With Claude:**
```
I've finished the design phase. Handing off to you.

HANDOFF: implementation_agent
├─ Task: Build the API
├─ Context: Signal-based logging approved
├─ Blockers: Redis might not be available
└─ Learned: File fallback is reliable
```

**With Llama:**
```
[Same signal format]
[Same context structure]
[Same protocol]
[Different reasoning, same output]
```

**With GPT:**
```
[Same signal format]
[Same context structure]
[Same protocol]
[Different approach, same interface]
```

The protocol is **model-agnostic**. The reasoning varies. The interface doesn't.

---

## Extensibility: How Protocol Grows

The protocol is designed to grow without breaking:

### Adding New Signal Types

If we need a new signal type (e.g., QUESTION):
```
QUESTION: {question}
├─ Context: {what_you_need_to_know}
├─ Impact: {why_it_matters}
└─ Urgency: {how_soon_you_need_answer}
```

Existing code still works. New agents can use QUESTION. Old agents ignore it.

### Adding New Context Types

If we need to expose new context (e.g., METRICS_HISTORICAL):
```
METRICS_HISTORICAL:
├─ Phase: {phase_name}
├─ Token_efficiency: {percentage}
├─ Cost: {USD}
└─ Duration: {hours}
```

Old agents don't get it. New agents do. No breaking change.

### Changing Signal Format

If we need to change DECISION signal:
```
Old format: DECISION: {name} / Reasoning: ... / Outcome: ...
New format: DECISION {name} with extended fields

Both work. Coordinator handles both versions.
```

The protocol is **forward-compatible**.

---

## What Makes This Protocol Work

### 1. Clarity
Every agent knows exactly what to do and what to expect. No surprises.

### 2. Consistency
Same format everywhere. Same protocol for all models, all tasks, all phases.

### 3. Learnability
New agents read documentation and understand. No training required.

### 4. Measurability
Every action is recorded. Can see what works and what doesn't.

### 5. Robustness
Handles failures gracefully. Redis down? Use files. Agent crashes? Next agent continues.

### 6. Extensibility
Can add features without breaking existing features. Protocol grows as needed.

### 7. Transparency
All communication is visible and analyzable. No black boxes.

---

## Testing the Protocol

To validate the protocol works:

1. **Learnability test** (this week)
   - Can an agent (Claude) learn it from documentation?
   - Can they use it naturally without training?
   - What's confusing? What's clear?

2. **Real usage test**
   - Does it work with actual tasks?
   - Are signals clear enough?
   - Is context sufficient?

3. **Cross-model test** (planned)
   - Can Llama understand the protocol?
   - Can other models follow it?
   - Does it really work across models?

4. **Scalability test** (later)
   - Does it work with 10 agents?
   - Does it work with 100 signals?
   - Does context bloat become a problem?

---

## Success Criteria

The protocol is successful if:

✅ **Learnable:** Any agent can understand it from documentation
✅ **Usable:** Agents use it naturally without special effort
✅ **Reliable:** Works consistently, no data loss
✅ **Efficient:** Overhead is minimal (<1% of work time)
✅ **Transparent:** All actions are observable and measurable
✅ **Extensible:** Can grow features without breaking changes
✅ **Cross-compatible:** Works with different models

---

## Summary: The Protocol in One Paragraph

Agents join a system where they read onboarding documents, understand how to emit four signal types (decision, blocker, handoff, completion), access five context types (decision cache, project state, agent manifest, blockers, briefing), and coordinate through a background coordinator that caches decisions, monitors blockers, and generates briefings for handoffs. Every signal is stored in Redis and files, readable by any agent, and analyzable by code. New agents receive full briefings when handed off to, preventing context loss. The protocol is text-based, learnable, model-agnostic, and designed to scale.

---

## Next Steps

1. **Test the protocol with me (Claude)**
   - I'll read the onboarding documents
   - I'll use the protocol to do a real task
   - I'll emit signals and report what works

2. **Measure the protocol**
   - Is it learnable? (yes/no)
   - Is it usable? (easy/hard/natural)
   - What needs improving?

3. **Iterate the protocol**
   - Fix confusing parts
   - Add missing examples
   - Clarify ambiguities

4. **Finalize and scale**
   - Once proven with Claude
   - Test with other models
   - Deploy as standard

This protocol is the backbone. If it works, everything built on top of it will work.
