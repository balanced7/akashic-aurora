# Learning System: Real-Time Experiment & Outcome Capture
**Enabling all models to learn from what's been tried, what worked, and what didn't**

---

## The Problem We're Solving

**Current state:** You build, you test, you learn things, but that learning disappears.
- Week 1: "Llama 8B doesn't fit in VRAM, use Phi instead"
- Week 3: Someone tries Llama again. Wasted time re-learning.

**What we want:** Every model can see:
- What has been tried
- Why it was tried
- What happened (success/failure)
- What worked vs. what didn't
- Patterns (things that consistently succeed)
- Anti-patterns (things to avoid)

**Like enterprise dev teams have:** Postmortems, ADRs, lessons learned docs
**But:** Automatic, real-time, searchable, actionable

---

## The Solution: Learning Signal Type

Add a **fifth signal type** to our framework:

```
LEARNING: experiment_or_discovery
├─ What we tried: Specific thing tested
├─ Expected outcome: What we thought would happen
├─ Actual outcome: What actually happened
├─ Metrics: Success rate, speed, cost, quality
├─ Success: yes | partial | no
├─ Root cause (if failed): Why it didn't work
├─ Recommendation: What to do next time
├─ Category: performance | cost | quality | architecture
└─ Anti-pattern (if applicable): What NOT to do
```

### Examples:

#### Learning 1: Llama VRAM Test
```
LEARNING: llama_8b_vram_usage_test
├─ What we tried: Load Llama 3.1 8B Q4 on 16GB VRAM
├─ Expected outcome: 4.2GB used, 11.8GB available
├─ Actual outcome: FAILED - GPU out of memory at 14GB
├─ Metrics:
│  ├─ VRAM available: 16GB
│  ├─ Llama required: 14GB (not 4.2GB as estimated)
│  ├─ Actual available after: 2GB (too tight)
│  └─ Success rate: 0%
├─ Success: no
├─ Root cause: VRAM estimates were wrong. Q4 quantization + KV cache uses more than calculated.
├─ Recommendation: Don't use Llama 8B. Use Phi 2 (3.3GB) or wait for optimizations.
├─ Category: performance
└─ Anti-pattern: Don't trust VRAM estimates - always test before committing to architecture.
```

#### Learning 2: Phi 2 Quality Test
```
LEARNING: phi_2_coordinator_reasoning_test
├─ What we tried: Use Phi 2 for briefing synthesis (instead of Llama/Claude)
├─ Expected outcome: Fast, lightweight, ~90% quality
├─ Actual outcome: PARTIAL - Works for simple cases, struggles with complexity
├─ Metrics:
│  ├─ Speed: 10 tokens/sec (fast!)
│  ├─ VRAM: 3.3GB (lightweight)
│  ├─ Quality: 70% on simple tasks, 40% on complex reasoning
│  ├─ Accuracy: 7/10 correct decisions
│  └─ Time to complete: 2.5 minutes (good)
├─ Success: partial
├─ Root cause: Phi 2 is good at simple pattern matching but weak at complex reasoning. Works for decision synthesis but not for architecture questions.
├─ Recommendation: Use Phi 2 for coordinator (briefing synthesis), use Llama/Claude for complex reasoning.
├─ Category: quality
└─ Anti-pattern: Don't use Phi for architecture decisions. It hallucinates on complex topics.
```

#### Learning 3: Framework Learnability
```
LEARNING: framework_learnability_with_opencode_test
├─ What we tried: Have OpenCode learn framework from docs without any code changes
├─ Expected outcome: Understand 80%, need clarifications on 20%
├─ Actual outcome: SUCCESS - 100% understanding, emitted clear signals naturally
├─ Metrics:
│  ├─ Docs read: 3 files (AGENT_ONBOARDING, CONTEXT_SCHEMA, SIGNAL_REFERENCE)
│  ├─ Understanding: 100% (no clarifications needed)
│  ├─ Signal clarity: 95% (perfectly formatted)
│  ├─ Natural usage: Yes (signals felt intuitive)
│  └─ Time to understand: 5 minutes
├─ Success: yes
├─ Root cause: Framework design is model-agnostic, uses natural language, examples are clear
├─ Recommendation: Framework is ready for all models. No changes needed. Can deploy to Llama, Claude, any LLM.
├─ Category: architecture
└─ Anti-pattern: None identified. Framework is solid.
```

---

## The Learning Store: Queryable Knowledge Base

Beyond just signals, we create a **Learning Store** - structured database of experiments:

```python
learning_store.py

class LearningStore:
    """Structured knowledge from what we've tried and learned"""
    
    def record_learning(self, learning_signal):
        """Store a learning: what was tried, what happened, what to do next"""
        # Stores in Redis + file backup
        # Automatically indexed by category, date, success/failure
        # Can be queried by any model
    
    def get_learnings(self, query):
        """Query: 'What have we learned about Llama?'"""
        # Returns all LEARNING signals about Llama
        # With outcomes, recommendations, anti-patterns
    
    def get_patterns(self, category):
        """Get patterns: 'What consistently works for performance?'"""
        # Analyzes all learnings in category
        # Returns what works, what doesn't, success rates
    
    def get_anti_patterns(self, topic):
        """Get anti-patterns: 'What should we NOT do with Vision?'"""
        # Returns things that failed and why
        # Helps avoid repeating mistakes
    
    def get_recommendations(self, task):
        """Get recommendations: 'How should I approach code generation?'"""
        # Based on past learnings, what's recommended
        # Sorted by success rate
```

---

## Real-Time Learning: How It Works

### When Trying Something New (Experiment)

**Agent** emits LEARNING signal while doing it:

```
LEARNING: attempt_speculative_decoding_with_opencode_task
├─ What we tried: Llama predicts 5 tokens, Claude validates
├─ Expected outcome: 4x speedup, maintain quality
├─ Actual outcome: [IN PROGRESS - measured as we go]
├─ Metrics: [Updated in real-time]
│  ├─ Speed so far: 1.2s per prediction (monitoring)
│  ├─ Quality feedback: [Collecting]
│  └─ Success: [TBD]
```

**As work happens**, metrics get updated:
- Speed measured in real-time
- Quality checked after
- Success determined at end
- Root cause identified if failure

**Signal emitted at END** with final metrics

### When Discovering Something (Insight)

**Agent** emits LEARNING signal immediately when discovering something:

```
LEARNING: redis_connection_more_reliable_than_files
├─ What we tried: Comparing Redis vs file fallback reliability
├─ Expected outcome: Files more reliable (no network)
├─ Actual outcome: Redis more reliable (atomic writes)
├─ Metrics:
│  ├─ Redis failures: 0/1000
│  ├─ File failures: 3/1000
│  └─ Reliability difference: Statistically significant
├─ Success: yes (files are NOT more reliable)
├─ Root cause: File system caching + OS buffering causes occasional lost writes
├─ Recommendation: Use Redis as primary, files as backup (not vice versa)
├─ Category: architecture
└─ Anti-pattern: Don't assume files are more reliable than Redis.
```

---

## Using Learning for Real-Time Decision Making

### Briefing Includes Relevant Learnings

When Agent B receives briefing from Agent A:

```
BRIEFING: For briefing_generator_agent
├─ From: coordinator_test_agent
├─ Task: Build briefing generator
├─ Key decisions: [from DECISION_CACHE]
├─ Relevant learnings: [NEW - from LEARNING_STORE]
│  ├─ LEARNING: "framework_learnability_with_opencode_test"
│  │  └─ Recommendation: Framework is solid, ready for deployment
│  ├─ LEARNING: "coordinator_async_performance_improvement"
│  │  └─ Recommendation: Async coordinator performs better than sync
│  └─ [Other relevant learnings...]
├─ Anti-patterns to avoid:
│  ├─ Don't assume files are more reliable than Redis
│  ├─ Don't use Phi 2 for complex reasoning
│  └─ [Other anti-patterns...]
```

### Models Query Learning Store Before Starting

```python
# Agent starting a task queries learning store
learnings = learning_store.get_learnings("VRAM management")
recommendations = learning_store.get_recommendations("optimize for speed")
anti_patterns = learning_store.get_anti_patterns("local inference")

# Agent now knows:
# - What's been tried with VRAM
# - What's recommended for speed
# - What NOT to do with local inference
```

---

## Structure: What Gets Stored

### LEARNING Signal Fields

```
LEARNING: experiment_name
├─ What we tried: Specific, actionable description
├─ Expected outcome: What we predicted would happen
├─ Actual outcome: What actually happened
├─ Category: performance | cost | quality | architecture | reliability
├─ Success: yes | partial | no
├─ Metrics: Quantitative data
│  ├─ {metric_name}: {value with units}
│  └─ {metric_name}: {value with units}
├─ Confidence: high | medium | low (how confident in this learning?)
├─ Root cause (if failed): Why it didn't work
├─ Root cause (if succeeded): Why it worked
├─ Recommendation: Specific action for next time
├─ Anti-pattern: What NOT to do (if applicable)
├─ Links: 
│  ├─ Related decisions: [list of DECISION signal IDs]
│  ├─ Related blockers: [list of BLOCKER signal IDs]
│  └─ Related learnings: [other LEARNING signals]
└─ Reviewed by: [which agents have seen this and confirmed it]
```

---

## Examples: Real Learnings You'll Capture

### Week 1 Learning
```
LEARNING: signal_based_logging_efficiency_validated
├─ What we tried: Signal-based logging (structured) vs prose-based
├─ Expected outcome: 65% tokens on work (baseline prose)
├─ Actual outcome: 95% tokens on work (signals)
├─ Category: architecture
├─ Success: yes
├─ Metrics:
│  ├─ Overhead baseline: 30% (prose)
│  ├─ Overhead achieved: 5% (signals)
│  ├─ Token efficiency: 95%
│  └─ Cost reduction: 3x
├─ Recommendation: Signal-based logging is core architecture. Do not change.
```

### Week 2 Learning (Hypothetical)
```
LEARNING: briefing_quality_vs_length_tradeoff
├─ What we tried: Briefing with 500 tokens vs 1500 tokens
├─ Expected outcome: More tokens = more context = better decisions
├─ Actual outcome: PARTIAL - 1500 tokens better but 500 tokens sufficient for most tasks
├─ Category: quality
├─ Success: partial
├─ Metrics:
│  ├─ Agent comprehension (500 tokens): 85%
│  ├─ Agent comprehension (1500 tokens): 95%
│  ├─ Re-work due to poor briefing (500): 10%
│  ├─ Re-work due to poor briefing (1500): 2%
│  └─ Token saved with 500: 30%
├─ Recommendation: Use 500-token briefing as default. Upgrade to 1500 if task is complex.
├─ Anti-pattern: Don't assume more context always helps. Brevity has value.
```

### Week 3 Learning (Hypothetical)
```
LEARNING: llama_8b_speed_vs_claude_quality_analysis
├─ What we tried: Route simple tasks to Llama (fast), complex to Claude (quality)
├─ Expected outcome: 70% tasks go to Llama, 30% to Claude
├─ Actual outcome: 65% tasks routed to Llama, 80% of those were correct
├─ Category: cost + performance
├─ Success: yes
├─ Metrics:
│  ├─ Tasks routed to Llama: 65%
│  ├─ Accuracy from Llama: 80%
│  ├─ Speed improvement: 3x
│  ├─ Cost improvement: 5x
│  ├─ Manual review needed: 20% of Llama tasks
│  └─ Overall efficiency: 85%
├─ Recommendation: Continue MoE routing. Add review step for Llama tasks in production.
├─ Anti-pattern: Don't route complex reasoning to Llama without review.
```

---

## Implementation: Three Components

### 1. LEARNING Signal (New Fifth Signal Type)

Add to your framework:
```python
# coordinator_api.py - add method
def learning(self, experiment_name, what_tried, expected, actual, 
             category, success, metrics, root_cause, recommendation):
    """Emit a LEARNING signal documenting experiment outcome"""
    # Uses same signal infrastructure as DECISION/BLOCKER
    # But structured specifically for learning capture
```

### 2. Learning Store (Queryable Database)

```python
# learning_store.py
class LearningStore:
    def record_learning(self, learning_signal) → bool
    def get_learnings(self, query: str) → List[LearningRecord]
    def get_patterns(self, category: str) → Dict[str, Pattern]
    def get_anti_patterns(self, topic: str) → List[AntiPattern]
    def get_recommendations(self, task: str) → List[Recommendation]
    def search_learnings(self, keywords: str) → List[LearningRecord]
```

### 3. Learning Integration in Briefings

```python
# coordinator_service.py - enhance briefing generation
def _generate_briefing(self, target_agent, handoff_signal):
    """Enhanced briefing including relevant learnings"""
    briefing = {
        # ... existing fields ...
        "relevant_learnings": self._find_relevant_learnings(task),
        "recommendations": self._get_recommendations(task),
        "anti_patterns": self._get_anti_patterns(task),
    }
```

---

## Real-Time Learning Flow

```
Agent starts task
    ↓
Queries learning_store: "What have we learned about this?"
    ↓
Gets recommendations + anti-patterns from past learnings
    ↓
Agent works with knowledge of past attempts
    ↓
Agent emits LEARNING signal: "Here's what I tried, here's what happened"
    ↓
learning_store records the experiment
    ↓
Next agent reads briefing including this new learning
    ↓
Cycle repeats with more knowledge accumulated
```

---

## Benefits: Why This Matters

### 1. Eliminate Rework
- Previous agent learned "Phi 2 is weak at reasoning"
- Next agent doesn't re-discover this
- Time saved: 4 hours of testing

### 2. Accelerate Learning
- Each agent adds to knowledge base
- Collective learning becomes team knowledge
- By Week 6: You have 50+ learnings documented

### 3. Pattern Recognition
- See what consistently works
- See what consistently fails
- Make data-driven decisions (not guesses)

### 4. Cross-Model Knowledge
- Claude learns what Llama discovered
- Llama learns what OpenCode tried
- All models benefit from all experiments

### 5. Risk Reduction
- Anti-patterns documented
- "Don't do this" is explicit
- Prevents repeating expensive mistakes

### 6. Evidence-Based Architecture
- Every architectural decision backed by experiment
- "We chose X because" is documented
- Auditable, defensible, changeable

---

## Example: Real-Time Learning in Action

### Day 1 (Week 3): Testing Llama
```
Agent emits LEARNING: attempt_llama_inference
├─ Actual outcome: VRAM usage 14GB (we estimated 4.2GB)
├─ Success: no
├─ Recommendation: Don't use Llama. Use Phi instead.
```

### Day 2 (Week 3): Next Task
```
Agent starts task, queries learning_store
→ Gets: "Llama doesn't fit. Recommendation: Use Phi."

Instead of re-discovering, agent immediately:
1. Loads Phi 2 (3.3GB)
2. Tests it
3. Finds it works for this task
4. Emits LEARNING: "Phi 2 works well for coordinator synthesis"

Result: 4 hours saved (would have been wasted re-testing Llama)
```

### Day 7 (End of Week 3): Patterns Emerge
```
learning_store.get_patterns("performance")
→ Returns analysis of all performance learnings
→ Shows: "Phi 2 is 2x faster than Llama, good enough for 70% of tasks"
→ Shows: "Claude API is better for complex reasoning but costs money"
→ Shows: "Best mix: 70% Phi, 25% Llama, 5% Claude"

This recommendation becomes architecture for Week 4-6
```

---

## What Gets Stored (Storage)

### Primary: Redis (Fast Access)
```
learn:experiments (sorted set by success rate)
learn:patterns:performance (patterns by category)
learn:anti_patterns (what NOT to do)
learn:recommendations (by task type)
```

### Backup: JSONL Files
```
E:\AI-Setup\learnings\experiments.jsonl
E:\AI-Setup\learnings\patterns.jsonl
E:\AI-Setup\learnings\anti_patterns.jsonl
```

### Human-Readable: DEV_NOTES.md (Auto-Generated)
```
# Development Notes & Learnings

## Performance Learnings
- Phi 2 is 2x faster than Llama for simple tasks
- Redis is 10x faster than file access for coordinator

## Quality Learnings  
- Briefings with 500 tokens work 85% of the time
- Llama needs human review for complex tasks

## Anti-Patterns
- Don't assume files are more reliable than Redis
- Don't use Phi 2 for architectural decisions
- Don't rely on VRAM estimates without testing

## Recommendations
- Use Phi 2 for coordinator (proven reliable)
- Use Llama for medium reasoning (proven fast enough)
- Use Claude for architecture (proven high quality)
```

---

## By Week 6: Your Dev Notes Look Like This

```
# Multi-Agent System: Learnings Document
**Last Updated:** Week 6, Day 3

## Proven Approach
✅ Signal-based logging: 95% token efficiency (confirmed in Week 1)
✅ Async coordinator with Phi 2: 2x faster than alternatives (tested Week 2)
✅ MoE routing: 65% tasks local, 35% cloud (optimized Week 4)
✅ Speculative decoding: 4x speedup validated (tested Week 5)

## What Works
- Phi 2 for coordinator tasks (3.3GB, fast, good enough)
- Llama 8B for medium complexity reasoning (proven in Week 3)
- Claude for architecture decisions (proven high quality)
- OpenCode for implementation (proven reliable)

## What Doesn't Work
- Llama 8B with full KV cache (VRAM explodes, don't do it)
- Phi 2 for architectural decisions (hallucinates, avoid)
- File-based logging as primary (unreliable, use Redis)
- Context windows >7500 tokens (runs out of buffer, causes overflow)

## Patterns Discovered
- Every 100% local inference approach saves ~$400/month
- Every 10% reduction in re-work saves ~4 hours/week
- Every 50 learnings captured prevents ~3 hours of rework
- Pattern: Problems not documented cost 3x to re-solve

## Recommendations for Scaling
- Keep learning store. Invaluable.
- Review anti-patterns weekly.
- Share learnings across teams.
- Document every experiment.
```

---

## Next: Implementation Plan

**Phase 1 (This Week):**
- Add LEARNING signal type to coordinator_api.py
- Create learning_store.py with basic record/query
- Start capturing learnings from work you're already doing

**Phase 2 (Week 2):**
- Integrate learnings into briefing generation
- Start auto-generating DEV_NOTES.md
- Query learnings before starting tasks

**Phase 3 (Week 3+):**
- Analyze patterns across learnings
- Build recommendations engine
- Anti-patterns become guardrails

---

## Summary: Why This Matters

You asked: **"How do we eliminate waste and rework?"**

Answer: **Capture what was tried, what happened, and what to do next.**

That's what enterprise teams do with postmortems and ADRs. You're automating it, making it real-time, and making it available to all models.

Result: By Week 6, you have 50+ documented learnings. No re-discovering. No re-work. Every model learns from every other model's discoveries.

**This is how teams scale from chaos to clarity.**

---

**Ready to implement this?** Or refine the design first?
