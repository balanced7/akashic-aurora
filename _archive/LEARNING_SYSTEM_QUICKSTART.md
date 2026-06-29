# Learning System Quick Start Guide

**For:** Developers integrating learnings into their agents  
**Duration:** 5 minutes to read, 2 minutes to implement  
**Status:** Ready to use - Phase 1 complete ✅

---

## TL;DR

Add learning capture to your agent in 3 steps:

```python
# 1. Initialize coordinator (already done for you)
from coordinator_api import initialize
api = initialize("my_agent")

# 2. Do your experiment/work

# 3. Log the learning
from coordinator_api import learning

learning(
    experiment_name="my_experiment",
    what_tried="What I attempted",
    expected_outcome="What I thought would happen",
    actual_outcome="What actually happened",
    category="performance",  # or: cost, quality, architecture, reliability
    success="yes",          # or: "partial", "no"
    metrics={"metric_name": value},
    root_cause="Why it worked/failed",
    recommendation="What to do next time",
    anti_pattern="What NOT to do (optional)"
)

# Done! Coordinator auto-indexes and shares with other agents
```

---

## When to Log a Learning

### Log When:
✅ You complete an experiment  
✅ You try something new and see the result  
✅ You discover what works (or doesn't)  
✅ You find an optimization  
✅ You hit a failure and understand why  
✅ You need to remember this for future agents  

### Don't Log:
❌ Normal task progress
❌ Debug messages
❌ Routine decisions
❌ Things you're still trying to figure out

### Examples of Good Learnings

**Example 1: Successful Optimization**
```python
learning(
    experiment_name="llama_kv_cache_pruning",
    what_tried="Implemented sliding window KV cache pruning",
    expected_outcome="Reduce VRAM from 4.2GB to 3.5GB",
    actual_outcome="Achieved 3.4GB with 5% speedup",
    category="performance",
    success="yes",
    metrics={"vram_gb": 3.4, "speedup_percent": 5},
    root_cause="Tokens beyond 1024 steps have minimal impact",
    recommendation="Use 1024-token sliding window for future optimizations",
    confidence="high"
)
```

**Example 2: Partial Success**
```python
learning(
    experiment_name="speculative_decoding_attempt",
    what_tried="Llama predictions with Claude validation",
    expected_outcome="4x speedup with maintained quality",
    actual_outcome="2.3x speedup, 2% quality loss",
    category="performance",
    success="partial",
    metrics={"speedup": 2.3, "quality_loss": 2.0},
    root_cause="Llama predictions less accurate without fine-tuning",
    recommendation="Fine-tune Llama on validation patterns first",
    anti_pattern="Don't use raw predictions without validation training",
    confidence="medium"
)
```

**Example 3: Failed Experiment**
```python
learning(
    experiment_name="redis_clustering_edge",
    what_tried="Set up Redis cluster on 4GB edge device",
    expected_outcome="Distributed caching with failover",
    actual_outcome="OOM error after 2 hours, device crashed",
    category="architecture",
    success="no",
    metrics={"uptime_minutes": 120, "memory_peak_gb": 5.8},
    root_cause="Cluster overhead exceeds device capacity",
    recommendation="Use single Redis instance with persistence",
    anti_pattern="Never cluster on memory-constrained devices",
    confidence="high"
)
```

---

## Learning Categories Explained

### Performance
**What:** Speed, throughput, latency improvements  
**Examples:** VRAM optimization, inference speedup, cache efficiency  
**When:** After optimizing resource usage or response times

### Cost
**What:** Reducing token usage or resource consumption  
**Examples:** Prompt compression, context window reduction, efficient models  
**When:** After achieving better resource efficiency

### Quality
**What:** Output accuracy, correctness improvements  
**Examples:** Better formatting, more accurate responses, improved reasoning  
**When:** After improving answer quality or reducing errors

### Architecture
**What:** System design, scalability, integration improvements  
**Examples:** Multi-agent coordination, distributed systems, new patterns  
**When:** After implementing system-level improvements

### Reliability
**What:** Stability, error handling, recovery mechanisms  
**Examples:** Graceful degradation, error resilience, backup strategies  
**When:** After improving system robustness

---

## Success Values Explained

### "yes" - Full Success
✅ Use when:
- Goal was clearly stated and met
- Improvement is significant (>10%)
- Result is reproducible
- High confidence in the finding
- No negative trade-offs

```python
success="yes",
confidence="high"
```

### "partial" - Mixed Success
⚠️ Use when:
- Some goals met, some not
- Trade-offs involved (speed vs quality)
- Improvement is moderate (5-10%)
- Medium confidence in findings
- Conditions matter (works in some cases)

```python
success="partial",
confidence="medium"
```

### "no" - Failed
❌ Use when:
- Goal not met
- Result worse than baseline
- Experiment blocked or crashed
- Clear failure mode identified
- Important anti-pattern to document

```python
success="no",
confidence="high"  # High confidence in failure!
```

---

## Metrics Format

### What to Include
Include any quantified measurements:

```python
metrics={
    "duration_seconds": 2.5,
    "tokens_used": 1500,
    "quality_score": 0.92,
    "vram_mb": 3400,
    "speedup_percent": 5,
    "accuracy_improvement": 0.03
}
```

### What NOT to Include
Don't include:
- Descriptions (use `root_cause` instead)
- Timestamps (auto-added)
- Names (use in `experiment_name`)
- Qualitative assessments (use `success` value)

---

## How Future Agents Use Your Learning

### Automatic (in briefing)
```python
# When agent_b takes over a task...
briefing = coordinator.get_briefing("agent_b")

# Your learning appears here:
briefing["relevant_learnings"]  # Your experiment
briefing["recommendations"]     # Your recommendation
briefing["anti_patterns"]       # What NOT to do
```

### Manual (if querying)
```python
from learning_store import get_learning_store

store = get_learning_store()

# Agent B can find your learning:
learnings = store.get_learnings("vram")
recs = store.get_recommendations("optimization")
anti = store.get_anti_patterns()
```

---

## Complete Example: Real-World Scenario

You're Llama, optimizing VRAM usage:

```python
from coordinator_api import initialize, learning
import time

# Initialize
api = initialize("llama_optimizer")

# Do your optimization work
start_vram = 4.2
print(f"Starting VRAM: {start_vram}GB")

# Try KV cache pruning
# ... [optimization code] ...

end_vram = 3.4
speedup = 1.05

print(f"Final VRAM: {end_vram}GB")
print(f"Speedup: {speedup}x")

# Log the learning
learning(
    experiment_name="llama_kv_cache_pruning_v2",
    
    what_tried=(
        "Implemented sliding window KV cache pruning. "
        "Tracks only recent 1024 tokens, discards older context. "
        "Applied at each attention head independently."
    ),
    
    expected_outcome=(
        "Reduce VRAM from 4.2GB to ~3.5GB "
        "while maintaining quality >95%"
    ),
    
    actual_outcome=(
        f"Achieved {end_vram}GB VRAM "
        f"with {(speedup-1)*100:.1f}% speedup "
        "and 0.1% quality loss"
    ),
    
    category="performance",
    
    success="yes",
    
    metrics={
        "initial_vram_gb": start_vram,
        "final_vram_gb": end_vram,
        "vram_reduction_percent": ((start_vram - end_vram) / start_vram * 100),
        "speedup_percent": (speedup - 1) * 100,
        "quality_loss_percent": 0.1,
        "tested_context_sizes": [512, 1024, 2048, 4096],
        "best_performance_at": 1024
    },
    
    root_cause=(
        "Tokens beyond 1024 steps back contribute minimal context "
        "to attention computation. Pruning them saves both VRAM "
        "and computation with negligible quality impact."
    ),
    
    recommendation=(
        "For future VRAM optimization: Use sliding window approach "
        "with 1024-token lookback. This is reliable, reproducible, "
        "and achieves ~20% VRAM reduction with minimal quality loss."
    ),
    
    anti_pattern=(
        "Don't prune more than 50% of context at once. "
        "Over-aggressive pruning (keeping <512 tokens) causes "
        "noticeable quality degradation in complex reasoning."
    ),
    
    confidence="high"
)

print("✓ Learning logged and shared with team")
```

When the next optimization agent starts:
```python
# They automatically get:
briefing = {
    "relevant_learnings": [
        {
            "id": "llama_kv_cache_pruning_v2",
            "what_tried": "Sliding window KV cache pruning...",
            "success": "yes",
            "recommendation": "Use 1024-token lookback..."
        }
    ]
}

# They can also query:
store = get_learning_store()
recs = store.get_recommendations("vram optimization")
# Returns your recommendation with success: yes

anti = store.get_anti_patterns()
# Shows: "Don't prune >50% at once [HIGH severity]"
```

---

## Common Questions

### Q: Should I log every decision?
**A:** No, just the important experiments where you learn something new or confirm something important. Major improvements, failures with lessons, novel approaches.

### Q: What if my learning is very specific to Llama?
**A:** Still log it! Put the specifics in `experiment_name` and `what_tried`. Other agents can see it and adapt for their context.

### Q: Can I update a learning after logging?
**A:** Not directly, but you can log a follow-up learning (e.g., "llama_pruning_v2_validation") with additional results.

### Q: What if I don't have all the metrics?
**A:** Log what you have. The system is flexible:
```python
metrics={
    "primary_metric": 5.0
    # Include what you measured
}
```

### Q: How do I know if my learning was useful?
**A:** Check with:
```python
store = get_learning_store()
stats = store.get_stats()
print(f"Total experiments: {stats['total_experiments']}")

# Check if others queried yours:
recs = store.get_recommendations("your_topic")
if your_learning in recs:
    print("✓ Your learning is being used!")
```

### Q: Can multiple agents log for the same experiment?
**A:** Yes! Give it a slightly different name:
- `v1`, `v2`, `v3` - different iterations
- By agent: `claude_attempt`, `llama_attempt`
- By date: `2026_06_16_attempt`

---

## Integration Checklist

Before logging learnings:
- [ ] Coordinator API is initialized
- [ ] You're in a multi-agent system
- [ ] You've completed an experiment
- [ ] You know the results
- [ ] You can articulate the learning

When ready to log:
- [ ] Import `learning` from coordinator_api
- [ ] Call `learning()` with all 6 required fields
- [ ] Optionally add metrics, root_cause, recommendation, anti_pattern
- [ ] Set confidence appropriately

---

## Testing Your Learning

Verify your learning was captured:

```python
from learning_store import get_learning_store

store = get_learning_store()

# 1. Check total experiments
stats = store.get_stats()
print(f"Total experiments: {stats['total_experiments']}")

# 2. Search for your learning
my_learnings = store.get_learnings("llama_kv_cache")
print(f"Found {len(my_learnings)} related learnings")

# 3. Get recommendations
recs = store.get_recommendations("vram")
print(f"Recommendations for VRAM work: {len(recs)}")

# 4. Check anti-patterns
anti = store.get_anti_patterns()
print(f"Known anti-patterns: {len(anti)}")
```

---

## Summary

Learning system is now ready to use. Four steps to get started:

1. **Import** the learning function
2. **Complete** your experiment
3. **Log** the structured outcome
4. **Done** - automatically shared with all agents

The Coordinator handles indexing, searching, and sharing. You just focus on experimenting and learning.

**Start logging learnings today!** 🚀

