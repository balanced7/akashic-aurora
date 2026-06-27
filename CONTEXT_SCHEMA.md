# Context Schema: What You Can See
**The standardized structure of all available information**

---

## Overview

When you start working, the system provides five types of context. This document defines the exact structure of each.

All context is provided as readable, structured text. No opaque JSON dumps. You should be able to read and understand any context without special parsing.

---

## 1. DECISION_CACHE

**What it is:** All important decisions made so far, with their reasoning

**Structure:**

```
DECISION_CACHE:
├─ {decision_name}
│  ├─ Proposed by: {agent_id}
│  ├─ Proposed on: {timestamp}
│  ├─ Reasoning: {explanation_of_why}
│  ├─ Outcome: {what_was_chosen}
│  ├─ Confidence: {high | medium | low}
│  ├─ Reversible: {yes | no}
│  ├─ Times reused: {number}
│  └─ Status: {active | deprecated | revisit_in_phase_X}
├─ {decision_name}
│  [same structure]
└─ ...
```

**Example:**

```
DECISION_CACHE:

├─ signal_based_logging
│  ├─ Proposed by: architect
│  ├─ Proposed on: 2026-06-16 Week 1 Day 1
│  ├─ Reasoning: 
│  │   Agents emit structured signals (DECISION, BLOCKER, HANDOFF, COMPLETION)
│  │   instead of narrative prose. This reduces token overhead:
│  │   ├─ Baseline: 30% overhead (agents explaining themselves)
│  │   ├─ Signal-based: 5% overhead (structured facts only)
│  │   └─ Savings: 25% token improvement
│  │   
│  │   Additional benefit: Coordinator can cache decisions, preventing
│  │   future agents from re-reasoning the same problems.
│  ├─ Outcome: Yes, implement signal-based logging
│  ├─ Confidence: high
│  ├─ Reversible: no (core architecture)
│  ├─ Times reused: 3 (implementation, optimization planning, testing)
│  └─ Status: active
│
├─ coordinator_async
│  ├─ Proposed by: architect
│  ├─ Proposed on: 2026-06-16 Week 1 Day 1
│  ├─ Reasoning:
│  │   Coordinator could run synchronously (agents wait for briefings)
│  │   or asynchronously (coordinator works in background, agents proceed).
│  │   
│  │   Chose async because:
│  │   ├─ Agents shouldn't wait for coordination overhead
│  │   ├─ Coordinator overhead must be invisible (<5% CPU)
│  │   ├─ Background monitoring is more efficient
│  │   └─ Graceful degradation (coordinator failure doesn't block agents)
│  ├─ Outcome: Async. Coordinator runs in background thread/process.
│  ├─ Confidence: high
│  ├─ Reversible: yes (could switch to sync if needed)
│  ├─ Times reused: 2
│  └─ Status: active
│
├─ file_fallback_for_redis
│  ├─ Proposed by: architect
│  ├─ Proposed on: 2026-06-16 Week 1 Day 2
│  ├─ Reasoning:
│  │   Redis might not be available (Docker service down, WSL unavailable).
│  │   Could hard-require Redis or implement fallback.
│  │   
│  │   Chose fallback because:
│  │   ├─ File-based JSONL logging is equally reliable
│  │   ├─ Dual-write (Redis + files) is simple to implement
│  │   ├─ Files are always available on local machine
│  │   ├─ Easy to analyze with Python for testing
│  │   └─ Graceful degradation: use Redis if available, files if not
│  ├─ Outcome: Dual-write. Redis for speed, JSONL files for reliability.
│  ├─ Confidence: high
│  ├─ Reversible: yes
│  ├─ Times reused: 1 (implementation fallback)
│  └─ Status: active
│
├─ context_window_7092_tokens
│  ├─ Proposed by: architect
│  ├─ Proposed on: 2026-06-16 Week 1 Day 3
│  ├─ Reasoning:
│  │   Claude's context window is 8192 tokens. Need to leave safety margin.
│  │   
│  │   Allocated:
│  │   ├─ System prompt: 500 tokens
│  │   ├─ Session history: 3000 tokens
│  │   ├─ Task context: 1500 tokens
│  │   ├─ Working buffer: 500 tokens
│  │   ├─ Safety margin: 1092 tokens (13%)
│  │   └─ Total: 7092 tokens (87% utilization)
│  │   
│  │   This allows for aggressive context compression while maintaining
│  │   safety buffer to prevent overflow.
│  ├─ Outcome: 7092 token budget per agent session
│  ├─ Confidence: medium (needs real testing)
│  ├─ Reversible: yes
│  ├─ Times reused: 0 (still planning)
│  └─ Status: active
│
└─ [47 more decisions in full cache...]

KEY INSIGHT FOR YOU:
These decisions are already made. Don't re-think them.
If you need to make a decision and it's in this cache, read the reasoning
and reuse the decision. This saves tokens and prevents re-analysis.
```

**How to use it:**
- Before making an architecture decision, check if it's here
- If it is, read the reasoning
- If the reasoning applies to your situation, reuse the decision
- If the reasoning doesn't apply, you can override (emit new DECISION signal)
- If something in the cache is wrong, emit a new DECISION signal to update it

**Format rules:**
- One decision per entry
- Reasoning is paragraph form, readable by any agent
- Outcome is the actual choice
- Status indicates if it's still active or deprecated

---

## 2. PROJECT_STATE

**What it is:** Current status of the entire project

**Structure:**

```
PROJECT_STATE:
├─ Project: {project_name}
├─ Started: {timestamp}
├─ Current phase: {phase_name}
├─ Target completion: {timeline}
│
├─ COMPLETED PHASES:
│  ├─ {phase_name}
│  │  ├─ Deliverables:
│  │  │  ├─ {deliverable_1}
│  │  │  ├─ {deliverable_2}
│  │  │  └─ ...
│  │  ├─ Completed on: {timestamp}
│  │  ├─ Blockers encountered: {number}
│  │  └─ Blockers resolved: {number}
│  └─ ...
│
├─ IN PROGRESS:
│  ├─ {phase_name}
│  │  ├─ Expected completion: {timestamp}
│  │  ├─ Progress: {percentage}
│  │  ├─ Current blockers:
│  │  │  ├─ {blocker_name} (severity)
│  │  │  └─ ...
│  │  └─ Current agent: {agent_id}
│
├─ UPCOMING PHASES:
│  ├─ {phase_name}
│  │  ├─ Scheduled start: {timestamp}
│  │  ├─ Prerequisites: {list}
│  │  └─ Estimated duration: {hours}
│  └─ ...
│
└─ CRITICAL PATH:
   ├─ Items blocking next phase: {list}
   └─ Priority: {high | medium | low}
```

**Example:**

```
PROJECT_STATE:
├─ Project: Multi-Agent Coordinator System
├─ Started: 2026-06-16 Week 1
├─ Current phase: Week 1 - Foundation
├─ Target completion: 2026-07-03 (6 weeks)
│
├─ COMPLETED PHASES:
│  └─ Week 1 - Foundation
│     ├─ Deliverables:
│     │  ├─ coordinator_api.py (157 lines)
│     │  ├─ coordinator_service.py (480 lines)
│     │  ├─ test_coordinator_foundation.py (350 lines)
│     │  └─ WEEK_1_FOUNDATION_DELIVERED.md
│     ├─ Completed on: 2026-06-16
│     ├─ Blockers encountered: 2
│     └─ Blockers resolved: 1 (Redis connection)
│
├─ IN PROGRESS:
│  └─ Week 1 - Framework Testing
│     ├─ Expected completion: 2026-06-17
│     ├─ Progress: 30%
│     ├─ Current blockers:
│     │  ├─ Framework not yet tested with real agent (MEDIUM)
│     │  └─ Cross-model compatibility unverified (MEDIUM)
│     └─ Current agent: claude (testing framework)
│
├─ UPCOMING PHASES:
│  ├─ Week 2 - Intelligence Layer
│  │  ├─ Scheduled start: 2026-06-18
│  │  ├─ Prerequisites: Framework finalized and tested
│  │  ├─ Tasks: briefing_generator.py, agent_profiles.py
│  │  └─ Estimated duration: 20 hours
│  ├─ Week 3 - Local Reasoning
│  │  ├─ Scheduled start: 2026-06-24
│  │  ├─ Prerequisites: Week 2 complete
│  │  ├─ Tasks: local_reasoner.py, Llama 8B integration
│  │  └─ Estimated duration: 18 hours
│  └─ [Weeks 4-6 planned...]
│
└─ CRITICAL PATH:
   ├─ Items blocking next phase:
   │  ├─ Framework must be learnable by any model
   │  ├─ Must test with real agent work (not just theory)
   │  └─ Must verify cross-model compatibility
   └─ Priority: high (delays everything after Week 2)
```

**Special note: TOKEN_BUDGET (if present)**
- **What it is:** The maximum tokens you can use per session/task
- **When to care:** Only if managing context window, creating briefings, or concerned about overflow
- **Most agents:** Don't need to think about this (handled automatically)
- **If you see it:** System is optimizing for efficiency. Work normally; coordinator handles compression.

**How to use it:**
- Check where you fit in the timeline
- Know what's blocking the critical path
- Understand what was already done (don't duplicate)
- See what's coming next (plan accordingly)

---

## 3. AGENT_MANIFEST

**What it is:** Who's doing what right now

**Structure:**

```
AGENT_MANIFEST:
├─ {agent_id}
│  ├─ Role: {role_description}
│  ├─ Status: {COMPLETED | IN_PROGRESS | WAITING | QUEUED | PLANNING}
│  ├─ Task: {what_they're_working_on}
│  ├─ Start time: {timestamp}
│  ├─ Expected completion: {timestamp}
│  ├─ Signals emitted: {count}
│  ├─ Last signal: {timestamp}
│  ├─ Decisions made: {count}
│  ├─ Blockers reported: {count}
│  └─ Available for questions: {yes | no}
└─ ...
```

**Example:**

```
AGENT_MANIFEST:

├─ architect (claude)
│  ├─ Role: System design and planning
│  ├─ Status: COMPLETED
│  ├─ Task: Design 6-week roadmap and hardware optimization
│  ├─ Start time: 2026-06-16 Session 1
│  ├─ Completed: 2026-06-16 16:30
│  ├─ Signals emitted: 27
│  ├─ Last signal: "COMPLETION: architecture_and_planning"
│  ├─ Decisions made: 15
│  ├─ Blockers reported: 3 (all resolved)
│  └─ Available for questions: yes (context maintained)
│
├─ implementation (claude)
│  ├─ Role: Build foundation layer
│  ├─ Status: IN_PROGRESS
│  ├─ Task: Implement coordinator_api.py and coordinator_service.py
│  ├─ Start time: 2026-06-16 16:45
│  ├─ Expected completion: 2026-06-17 08:00
│  ├─ Signals emitted: 8
│  ├─ Last signal: "DECISION: dual_write_redis_and_files"
│  ├─ Decisions made: 4
│  ├─ Blockers reported: 1 (redis_unavailable, workaround active)
│  └─ Available for questions: yes (currently working)
│
├─ framework_tester (claude) [YOU ARE HERE]
│  ├─ Role: Test framework learnability and cross-compatibility
│  ├─ Status: IN_PROGRESS
│  ├─ Task: Use framework naturally, report what works/doesn't
│  ├─ Start time: 2026-06-17 00:00
│  ├─ Expected completion: 2026-06-17 06:00
│  ├─ Signals emitted: 0 (just started)
│  ├─ Decisions made: 0
│  ├─ Blockers reported: 0
│  └─ Available for questions: yes (just getting started)
│
├─ briefing_agent (claude)
│  ├─ Role: Build intelligent briefing generation
│  ├─ Status: QUEUED
│  ├─ Task: Implement briefing_generator.py and agent_profiles.py
│  ├─ Scheduled start: 2026-06-18 09:00
│  ├─ Expected duration: 20 hours
│  └─ Available for questions: no (waiting to start)
│
└─ local_reasoning_agent (claude)
   ├─ Role: Integrate local Llama 8B
   ├─ Status: PLANNING
   ├─ Task: Implement local_reasoner.py, test VRAM management
   ├─ Scheduled start: 2026-06-24
   ├─ Expected duration: 18 hours
   └─ Available for questions: no (not started yet)
```

**How to use it:**
- See who's done what before
- Know who to ask for clarification (they're available if status is COMPLETED or IN_PROGRESS)
- Understand the team composition
- Track progress of parallel work

---

## 4. BLOCKERS (Global)

**What it is:** All known issues, problems, and uncertainties

**Structure:**

```
BLOCKERS:
├─ {blocker_name}
│  ├─ Severity: {LOW | MEDIUM | HIGH | CRITICAL}
│  ├─ Reported by: {agent_id}
│  ├─ Reported on: {timestamp}
│  ├─ Age: {how_long_its_been_active}
│  ├─ Description: {what's_the_problem}
│  ├─ Impact: {how_it_affects_progress}
│  ├─ Workaround: {how_its_being_handled}
│  ├─ Status: {ACTIVE | MONITORED | IN_PROGRESS | RESOLVED}
│  └─ Resolution planned: {yes | no}
└─ ...
```

**Example:**

```
BLOCKERS:

├─ redis_unavailable
│  ├─ Severity: HIGH
│  ├─ Reported by: implementation
│  ├─ Reported on: 2026-06-16 16:50
│  ├─ Age: 2 hours
│  ├─ Description:
│  │   Redis server is not responding on port 6379.
│  │   Docker service may not be running, or WSL unavailable.
│  ├─ Impact: HIGH
│  │   ├─ Can't test coordinator monitoring with real streams
│  │   ├─ Decisions won't be cached in-memory
│  │   ├─ If not mitigated: system can't function
│  ├─ Workaround: ACTIVE
│  │   ├─ Dual-write to JSONL files instead
│  │   ├─ Files provide equal reliability
│  │   ├─ Fallback tested and working
│  │   └─ Graceful: Redis used if available, files if not
│  ├─ Status: MONITORED
│  └─ Resolution planned: yes
│     └─ In Week 2, will set up Docker properly
│
├─ context_window_might_overflow
│  ├─ Severity: MEDIUM
│  ├─ Reported by: architect
│  ├─ Reported on: 2026-06-16 12:00
│  ├─ Age: 8 hours
│  ├─ Description:
│  │   Agent briefing + session history might exceed 8K token limit.
│  │   Could lose context if not handled carefully.
│  ├─ Impact: MEDIUM
│  │   ├─ Agents could be cut off mid-context
│  │   ├─ Loss of important information
│  │   ├─ Degraded performance
│  ├─ Workaround: IN_PROGRESS
│  │   ├─ Implementing aggressive context compression
│  │   ├─ 7092-token budget per session (87% of 8192)
│  │   ├─ Prioritizing recent and high-signal tokens
│  │   └─ 13% safety margin for unexpected expansion
│  ├─ Status: IN_PROGRESS (awaiting real testing)
│  └─ Resolution planned: yes
│     └─ Will test in Week 2 with real agent work
│
├─ no_real_agent_integration_yet
│  ├─ Severity: HIGH
│  ├─ Reported by: architect
│  ├─ Reported on: 2026-06-16 11:00
│  ├─ Age: 9 hours
│  ├─ Description:
│  │   System is designed theoretically but not tested with real agent work.
│  │   Don't know what actually works, what doesn't, what's missing.
│  ├─ Impact: HIGH
│  │   ├─ Can't measure real token savings
│  │   ├─ Don't know if decisions are actually reused
│  │   ├─ Can't verify context is actually useful
│  │   ├─ Everything after Week 1 is built on assumptions
│  ├─ Workaround: PLANNED
│  │   ├─ Test framework with real agent use (you, right now)
│  │   ├─ Report what works and what doesn't
│  │   ├─ Measure actual impact
│  │   └─ Iterate based on real feedback
│  ├─ Status: IN_PROGRESS (this is your task)
│  └─ Resolution planned: yes
│     └─ Finishing today (expected by 2026-06-17 06:00)
│
└─ vram_management_unproven
   ├─ Severity: MEDIUM
   ├─ Reported by: architect
   ├─ Reported on: 2026-06-16 10:00
   ├─ Age: 10 hours
   ├─ Description:
   │   Theory says VRAM management is possible. Haven't tested actual
   │   model loading, unloading, KV cache management under load.
   ├─ Impact: MEDIUM
   │   ├─ Week 3 depends on this
   │   ├─ If proven impossible: changes architecture
   │   └─ If proven possible: unlocks 70% cost reduction
   ├─ Workaround: PLANNED
   │   ├─ Will test in Week 3 with actual Llama loading
   │   ├─ Will measure real VRAM usage
   │   └─ Will iterate on allocation strategy
   ├─ Status: PLANNED
   └─ Resolution planned: yes
      └─ Testing in Week 3
```

**How to use it:**
- Before starting work, check if there are blockers that affect you
- Understand how blockers are being handled
- Don't waste time on problems that are already known and being managed
- Report new blockers as you encounter them
- Check back regularly—blocker status changes as work progresses

---

## 5. BRIEFING (Only if you're receiving a handoff)

**What it is:** Summary of what happened before you + what you need to know

**Structure:**

```
BRIEFING: For {your_agent_id}
├─ From: {previous_agent_id}
├─ Task: {what_you_should_do}
├─ Completed: {what_previous_agent_did}
│
├─ KEY DECISIONS (Relevant to your task):
│  ├─ {decision_name}
│  │  ├─ Reasoning: {summary}
│  │  ├─ Outcome: {choice}
│  │  └─ Why it matters for you: {relevance}
│  └─ ...
│
├─ BLOCKERS TO KNOW:
│  ├─ {blocker_name}
│  │  ├─ Severity: {level}
│  │  ├─ How it affects you: {impact}
│  │  └─ How to work around it: {workaround}
│  └─ ...
│
├─ PROJECT STATUS:
│  ├─ Where we are: {phase}
│  ├─ What's done: {list}
│  └─ What's next: {list}
│
├─ WHAT PREVIOUS AGENT LEARNED:
│  ├─ Insight 1: {learning}
│  ├─ Insight 2: {learning}
│  └─ ...
│
├─ FILES & ARTIFACTS:
│  ├─ {file_path}
│  │  └─ {description}
│  └─ ...
│
└─ NEXT STEPS:
   ├─ Immediate (first hour):
   │  ├─ {step}
   │  └─ ...
   └─ Full task:
      ├─ {step}
      └─ ...
```

**Example:**

```
BRIEFING: For briefing_generator_agent
├─ From: implementation
├─ Task: Build intelligent briefing generation system
├─ Completed: 
│  ├─ coordinator_api.py (signal-based logging)
│  ├─ coordinator_service.py (background monitoring)
│  └─ Full test coverage (all tests pass)
│
├─ KEY DECISIONS (Relevant to your task):
│  ├─ signal_based_logging
│  │  ├─ Reasoning: Reduces overhead from 30% to 5%
│  │  ├─ Outcome: Agents emit signals, not prose
│  │  └─ Why it matters for you: 
│  │      Briefings must use this signal format. Don't change it.
│  │      Your job is to synthesize signals into useful briefings.
│  │
│  ├─ decision_cache_structure
│  │  ├─ Reasoning: Cache must be fast and queryable
│  │  ├─ Outcome: Dict of {decision_name: {outcome, reasoning, uses}}
│  │  └─ Why it matters for you:
│  │      Briefings should include relevant cached decisions.
│  │      You'll query this structure and summarize for next agent.
│  │
│  ├─ briefing_purpose
│  │  ├─ Reasoning: Next agent shouldn't lose context or re-decide
│  │  ├─ Outcome: Briefing includes decisions, blockers, state, learnings
│  │  └─ Why it matters for you:
│  │      Design briefing to be maximally useful with minimal tokens.
│  │      Target: 500-800 tokens per briefing.
│  │
│  └─ file_fallback_for_redis
│     ├─ Reasoning: Redis might not be available
│     ├─ Outcome: Dual-write. Use files if Redis fails.
│     └─ Why it matters for you:
│         Briefings can be stored in either Redis or files.
│         Use dual-write pattern like the API does.
│
├─ BLOCKERS TO KNOW:
│  ├─ redis_unavailable
│  │  ├─ Severity: HIGH
│  │  ├─ How it affects you: 
│  │      You'll store briefings in Redis if available, files if not.
│  │  └─ How to work around it:
│  │      Implement dual-write (Redis + files).
│  │      Test both paths. Files-only is acceptable.
│  │
│  └─ no_real_agent_integration_yet
│     ├─ Severity: HIGH
│     ├─ How it affects you:
│     │  Can't test briefings with real agent handoffs yet.
│     │  Will test manually with mock agents.
│     └─ How to work around it:
│        Build comprehensive test suite with synthetic handoffs.
│
├─ PROJECT STATUS:
│  ├─ Where we are: Week 1 → Week 2 transition
│  ├─ What's done: 
│  │  ├─ Foundation layer (API + Coordinator service)
│  │  ├─ Framework documentation (learnable protocol)
│  │  └─ Initial framework testing (in progress)
│  └─ What's next:
│     ├─ Briefing generation (you)
│     ├─ Agent profiles and specialization
│     └─ Real agent integration testing
│
├─ WHAT PREVIOUS AGENT LEARNED:
│  ├─ Signal-based logging is very effective
│  │  └─ 0.2-0.5ms overhead per signal (well under 1ms target)
│  ├─ File fallback is as reliable as Redis
│  │  └─ Dual-write adds minimal complexity
│  ├─ Coordinator service is lightweight
│  │  └─ <200MB RAM, <5% CPU (invisible to agents)
│  ├─ Test-first approach prevents bugs
│  │  └─ Test file caught 3 edge cases before real use
│  └─ Decision caching has high reuse potential
│     └─ Estimated 25-30% of decisions are reusable
│
├─ FILES & ARTIFACTS:
│  ├─ E:\AI-Setup\coordinator_api.py
│  │  └─ Complete signal-based logging API
│  ├─ E:\AI-Setup\coordinator_service.py
│  │  └─ Background monitoring + decision cache
│  ├─ E:\AI-Setup\test_coordinator_foundation.py
│  │  └─ Integration tests (all passing)
│  ├─ E:\AI-Setup\WEEK_1_FOUNDATION_DELIVERED.md
│  │  └─ Summary of what was built
│  └─ E:\AI-Setup\session_logs/
│     └─ Signal files (for analysis)
│
└─ NEXT STEPS:
   ├─ Immediate (first hour):
   │  ├─ Read this briefing carefully
   │  ├─ Review the decision cache for briefing-related decisions
   │  ├─ Understand the decision_cache structure in coordinator_service.py
   │  └─ Look at test examples (how briefings will be used)
   │
   ├─ First task (hours 1-4):
   │  ├─ Design briefing_generator.py structure
   │  ├─ Implement find_relevant_decisions() (smarter than keyword matching)
   │  ├─ Create briefing template (what information + order)
   │  └─ Write basic unit tests
   │
   ├─ Second task (hours 4-8):
   │  ├─ Integrate with coordinator_service
   │  ├─ Test briefing generation with mock handoffs
   │  ├─ Design agent_profiles.py (agent specializations)
   │  └─ Document briefing format
   │
   └─ Completion:
      ├─ Full test coverage (all paths working)
      ├─ Briefings tested with real agent handoff signals
      ├─ Documentation for next agent
      └─ Ready for Week 2 integration testing
```

**How to use it:**
- Read this first thing (usually the briefing is your whole context)
- Understand what was done before (don't duplicate)
- Know the decisions that affect your task
- Be aware of blockers and how to work around them
- Follow the suggested next steps (they're based on what worked before)

**After reading your briefing (important):**
1. **Acknowledge understanding** - Emit a DECISION signal confirming you understand the task
   - Example: `DECISION: understand_briefing_and_ready_to_proceed`
   - Include any critical blockers you'll need to work around
2. **Ask questions** - If briefing is unclear, ask the previous agent (they're available if status=COMPLETED)
3. **Start work** - You now have full context and can proceed confidently
4. **Update blockers** - If you resolve any blockers mentioned in the briefing, report it

This ensures the system knows the briefing was understood and tracked.

---

## Summary: The Five Context Types

| Context Type | What | When to Check | Why It Matters |
|---|---|---|---|
| DECISION_CACHE | All past decisions + reasoning | Before making any decision | Reuse decisions, save tokens |
| PROJECT_STATE | Current phase, blockers, timeline | At the start of your task | Know where you fit, what's blocking |
| AGENT_MANIFEST | Who's working on what | When you need clarification | Know who to ask, track progress |
| BLOCKERS | All known issues | Before starting work | Work around known problems |
| BRIEFING | Previous agent's summary | First thing (if handed off) | Understand what's been done |

---

## Important: Context Should Be Readable by Any Model

All context in this schema is designed to be:
✅ **Human-readable** - Plain English, not JSON dumps
✅ **Agent-readable** - Any LLM can parse and understand
✅ **Structured** - Clear format, consistent format
✅ **Actionable** - Contains what you need to do your job
✅ **Concise** - No unnecessary details

If context doesn't meet these criteria, it should be improved.

---

## Next Steps

1. **In your task**: Use this context schema
2. **Report back**: What was clear? What was confusing?
3. **Iterate**: Fix based on real feedback
4. **Finalize**: Once proven, this becomes the standard

This schema is how agents in this system communicate across time and capability.
