# Learning System: Synthesis of Original Plan + New Design
**Combining your Redis-based learning vision with structured LEARNING signals**

---

## What You Started With (Original Plan)

From `bootstrap.md` and `AGENT_PROTOCOL.md`, you designed:

### Redis Structure:
```
learn:decisions       → Hash of all decisions made
learn:experiences     → Hash of all experiences/outcomes
learn:decisions:idx   → Sorted index (by success rate or date)
learn:experiences:success → Sorted by success percentage
```

### MCP Tools (Planned):
- `learning_record_decision` - Store a decision with outcomes
- `learning_record_experience` - Store an experience/experiment

### Intent:
"System learnings and documentation" + "ADRs and task outcomes"

**Status:** Planned in bootstrap, referenced in AGENT_PROTOCOL, but implementation (`learning.store` module) was never built.

---

## What We Just Designed (New Plan)

### LEARNING Signal Type (5th Signal):
Structured format for capturing experiments:
```
LEARNING: experiment_name
├─ What we tried: {specific description}
├─ Expected vs Actual: {prediction vs reality}
├─ Metrics: {quantified results}
├─ Category: performance|cost|quality|architecture|reliability
├─ Success: yes|partial|no
├─ Root cause: {why it succeeded or failed}
├─ Recommendation: {what to do next time}
└─ Anti-pattern: {what NOT to do}
```

### Learning Store Interface:
- `record_learning(signal)` - Store a learning
- `get_learnings(query)` - Find learnings about a topic
- `get_patterns(category)` - Find patterns (what works)
- `get_anti_patterns(topic)` - Find anti-patterns (what doesn't work)
- `get_recommendations(task)` - Get recommendations for a task

**Advantage:** More structured, queryable, actionable

---

## The Best Approach: Synthesis

### Layer 1: Redis Storage (Your Original Design)
Keep your original Redis structure. It's solid:

```
# Redis Hashes
learn:decisions         → Hash[decision_name] = {outcome, reasoning, uses}
learn:experiences       → Hash[experiment_name] = {what_tried, actual, metrics}

# Sorted Indexes  
learn:decisions:success      → Sorted Set[decision] = success_score
learn:experiments:success    → Sorted Set[experiment] = success_score
learn:anti_patterns         → Sorted Set[pattern] = criticality_score

# By Category
learn:category:performance  → Set[experiment_id]
learn:category:cost        → Set[experiment_id]
learn:category:quality     → Set[experiment_id]
learn:category:architecture → Set[experiment_id]
learn:category:reliability  → Set[experiment_id]

# For Retrieval
learn:experiments:all       → List of all experiment IDs (newest first)
learn:experiment:{id}       → Hash with full details
```

### Layer 2: LEARNING Signal (Unified Capture)
Add LEARNING signal type to automatically capture learnings:

```python
def learning(self, experiment_name, what_tried, expected, actual,
             category, success, metrics, root_cause, recommendation, anti_pattern=None):
    """Emit a LEARNING signal documenting experiment outcome"""
    signal = {
        "timestamp": now(),
        "agent_id": self.agent_id,
        "signal_type": "learning",
        "experiment_name": experiment_name,
        "what_tried": what_tried,
        "expected_outcome": expected,
        "actual_outcome": actual,
        "category": category,  # performance|cost|quality|architecture|reliability
        "success": success,    # yes|partial|no
        "metrics": metrics,    # dict of measurements
        "root_cause": root_cause,
        "recommendation": recommendation,
        "anti_pattern": anti_pattern,
        "confidence": "high|medium|low"
    }
    
    # Store to Redis + JSONL
    self._store_signal(signal)
    
    # Also store to learning store for immediate indexing
    learning_store.record_learning(signal)
```

### Layer 3: Learning Store Python Module
Build `learning_store.py` with your original intent + new structure:

```python
class LearningStore:
    """Unified interface to Redis learning data"""
    
    def __init__(self, redis_client, learning_logger):
        self.redis = redis_client
        self.logger = learning_logger
    
    def record_learning(self, learning_signal: dict) -> bool:
        """
        Store a learning signal in Redis with all indexes
        
        Updates:
        - learn:experiments:{id}
        - learn:experiments:all (list)
        - learn:experiments:success (sorted by score)
        - learn:category:{category}
        - learn:anti_patterns (if applicable)
        """
        experiment_id = learning_signal['experiment_name']
        
        # Main hash
        self.redis.hset(
            f'learn:experiment:{experiment_id}',
            mapping={
                'what_tried': learning_signal['what_tried'],
                'expected': learning_signal['expected_outcome'],
                'actual': learning_signal['actual_outcome'],
                'metrics': json.dumps(learning_signal['metrics']),
                'success': learning_signal['success'],
                'timestamp': learning_signal['timestamp'],
                'recommendation': learning_signal['recommendation'],
                'anti_pattern': learning_signal.get('anti_pattern', ''),
            }
        )
        
        # Add to all experiments list (newest first)
        self.redis.lpush('learn:experiments:all', experiment_id)
        
        # Score by success (0-100 scale)
        success_scores = {'yes': 100, 'partial': 50, 'no': 0}
        score = success_scores.get(learning_signal['success'], 0)
        self.redis.zadd('learn:experiments:success', {experiment_id: score})
        
        # Index by category
        category = learning_signal['category']
        self.redis.sadd(f'learn:category:{category}', experiment_id)
        
        # Index anti-patterns
        if learning_signal.get('anti_pattern'):
            self.redis.sadd('learn:anti_patterns', learning_signal['anti_pattern'])
            self.redis.hset(
                f'learn:anti_pattern:{learning_signal["anti_pattern"]}',
                mapping={
                    'experiments': experiment_id,
                    'reason': learning_signal['root_cause'],
                    'severity': 'high',  # Could be configurable
                }
            )
        
        return True
    
    def get_learnings(self, query: str) -> List[dict]:
        """
        Find learnings matching a query (experiment name or topic)
        
        Examples:
        - "Llama" → All learnings about Llama
        - "VRAM" → All learnings about VRAM
        - "performance" → All performance learnings
        """
        # Search by experiment ID (substring match)
        all_experiments = self.redis.lrange('learn:experiments:all', 0, -1)
        matching = [e.decode() if isinstance(e, bytes) else e 
                   for e in all_experiments 
                   if query.lower() in e.lower()]
        
        results = []
        for exp_id in matching:
            data = self.redis.hgetall(f'learn:experiment:{exp_id}')
            results.append({
                'id': exp_id,
                **data
            })
        
        return results
    
    def get_patterns(self, category: str) -> dict:
        """
        Analyze patterns in a category
        
        Returns what consistently works vs doesn't work
        """
        # Get all experiments in category
        experiments = self.redis.smembers(f'learn:category:{category}')
        
        success_count = {'yes': 0, 'partial': 0, 'no': 0}
        results = []
        
        for exp_id in experiments:
            data = self.redis.hgetall(f'learn:experiment:{exp_id}')
            success = data.get(b'success', b'unknown').decode()
            success_count[success] += 1
            results.append(data)
        
        return {
            'category': category,
            'total_experiments': len(experiments),
            'success_breakdown': success_count,
            'success_rate': success_count['yes'] / len(experiments) if experiments else 0,
            'experiments': results
        }
    
    def get_anti_patterns(self, topic: str = None) -> List[dict]:
        """
        Get documented anti-patterns (things that don't work)
        
        Sorted by criticality
        """
        if topic:
            # Get anti-patterns related to topic
            all_patterns = self.redis.smembers('learn:anti_patterns')
            matching = [p.decode() if isinstance(p, bytes) else p 
                       for p in all_patterns
                       if topic.lower() in p.lower()]
        else:
            matching = self.redis.smembers('learn:anti_patterns')
        
        results = []
        for pattern in matching:
            data = self.redis.hgetall(f'learn:anti_pattern:{pattern}')
            results.append({
                'pattern': pattern,
                'severity': data.get(b'severity', b'medium').decode(),
                'reason': data.get(b'reason', b'').decode(),
                'experiments': data.get(b'experiments', b'').decode(),
            })
        
        return sorted(results, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x['severity'], 0), reverse=True)
    
    def get_recommendations(self, task: str) -> List[dict]:
        """
        Get recommendations for a specific task based on past learnings
        
        Prioritized by success rate of related experiments
        """
        # Find experiments related to task
        all_experiments = self.redis.lrange('learn:experiments:all', 0, -1)
        matching = [e.decode() if isinstance(e, bytes) else e 
                   for e in all_experiments
                   if task.lower() in e.lower()]
        
        recommendations = []
        for exp_id in matching:
            data = self.redis.hgetall(f'learn:experiment:{exp_id}')
            if data.get(b'recommendation'):
                recommendations.append({
                    'experiment': exp_id,
                    'recommendation': data.get(b'recommendation', b'').decode(),
                    'success': data.get(b'success', b'').decode(),
                    'metrics': json.loads(data.get(b'metrics', '{}')),
                })
        
        # Sort by success rate
        success_scores = {'yes': 3, 'partial': 2, 'no': 1}
        return sorted(recommendations, 
                     key=lambda x: success_scores.get(x['success'], 0),
                     reverse=True)
    
    def search_learnings(self, keywords: str) -> List[dict]:
        """Full-text-ish search across all learnings"""
        all_experiments = self.redis.lrange('learn:experiments:all', 0, -1)
        keywords_lower = keywords.lower()
        
        results = []
        for exp_id in all_experiments:
            exp_id_str = exp_id.decode() if isinstance(exp_id, bytes) else exp_id
            if keywords_lower in exp_id_str.lower():
                data = self.redis.hgetall(f'learn:experiment:{exp_id_str}')
                
                # Also check content
                if any(keywords_lower in str(v).lower() for v in data.values()):
                    results.append({
                        'id': exp_id_str,
                        **data
                    })
        
        return results
```

### Layer 4: Integration Points

**In `coordinator_api.py`:**
```python
def learning(self, experiment_name, what_tried, expected, actual,
             category, success, metrics, root_cause, recommendation):
    """New method for emitting LEARNING signals"""
    data = {
        "experiment_name": experiment_name,
        "what_tried": what_tried,
        "expected_outcome": expected,
        "actual_outcome": actual,
        "category": category,
        "success": success,
        "metrics": metrics,
        "root_cause": root_cause,
        "recommendation": recommendation
    }
    self._emit_signal(SignalType.LEARNING, data)
```

**In `coordinator_service.py`:**
```python
def _handle_signal(self, signal: Dict[str, Any]) -> None:
    """Enhanced to handle LEARNING signals"""
    signal_type = signal.get("signal_type")
    
    # ... existing code ...
    
    elif signal_type == "learning":
        # Auto-index learning in learning store
        learning_store.record_learning(signal)
        self.logger.info(f"Learning recorded: {signal.get('experiment_name')}")
```

**In briefing generation:**
```python
def _generate_briefing(self, target_agent, handoff_signal):
    """Include relevant learnings in briefing"""
    task = handoff_signal.get("task")
    
    briefing = {
        # ... existing fields ...
        "relevant_learnings": learning_store.get_learnings(task),
        "recommendations": learning_store.get_recommendations(task),
        "anti_patterns": learning_store.get_anti_patterns(task),
    }
```

---

## Migration: Historical Learnings

If you have historical learnings in Redis under `learn:decisions` and `learn:experiences`:

```python
def migrate_historical_learnings():
    """Migrate old Redis structure to new LEARNING signal format"""
    
    # Read old decisions
    old_decisions = redis.hgetall('learn:decisions')
    for decision_name, decision_data in old_decisions.items():
        # Convert to LEARNING signal format
        learning_signal = {
            'signal_type': 'learning',
            'experiment_name': decision_name,
            'what_tried': 'Decision: ' + decision_name,
            'expected_outcome': 'Not recorded (migrated)',
            'actual_outcome': 'Success (recorded historically)',
            'category': 'architecture',
            'success': 'yes',
            'metrics': {'historical': True},
            'root_cause': 'Historical decision',
            'recommendation': f'Previously approved: {decision_name}',
            'timestamp': datetime.now().isoformat(),
        }
        
        learning_store.record_learning(learning_signal)
    
    # Do same for experiences
    old_experiences = redis.hgetall('learn:experiences')
    for exp_name, exp_data in old_experiences.items():
        # Similar migration
        pass
```

---

## Implementation Order

### Phase 1: This Week (Day 1-2)
1. ✅ Design done (synthesis document created)
2. Build `learning_store.py` with Redis structure from original plan
3. Add LEARNING signal type to `coordinator_api.py`
4. Integrate into `coordinator_service.py`
5. Test with real learnings from OpenCode test

### Phase 2: Week 2
1. Integrate learnings into briefing generation
2. Auto-generate DEV_NOTES.md from learnings
3. Query learnings before starting tasks
4. Start capturing learnings from all work

### Phase 3: Week 3+
1. Analyze patterns across learnings
2. Build recommendations engine
3. Anti-patterns become guardrails
4. Migrate any historical learnings

---

## Summary: What You Get

**Your Original Plan:** Redis structure + MCP tools (vision: organized learning storage)
**New Design:** LEARNING signals + queryable interface (vision: automatic learning capture)
**Synthesis:** Both layers working together

Result:
- ✅ Learnings stored in organized Redis structure (your original intent)
- ✅ Automatic capture via signals (new)
- ✅ Queryable interface (new)
- ✅ Integration with briefings (new)
- ✅ Anti-patterns prevent rework (new)
- ✅ Can preserve historical learnings (migration path)

---

## Code Files to Create

1. **`learning_store.py`** (300 lines)
   - Redis-backed learning storage
   - Queryable interface
   - Auto-indexing and categorization

2. **Updates to existing files:**
   - `coordinator_api.py` → Add `.learning()` method
   - `coordinator_service.py` → Handle LEARNING signals
   - `test_coordinator_foundation.py` → Test LEARNING signals

3. **Optional:**
   - `learning_migration.py` → Migrate historical learnings
   - `generate_dev_notes.py` → Auto-generate documentation

---

**Ready to build this?** Should I start with learning_store.py?
