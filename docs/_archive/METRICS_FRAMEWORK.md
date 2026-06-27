# Metrics Framework: How to Measure if the System Works

## Core Question
**Does our startup & context recovery system actually improve agent effectiveness?**

---

## Key Metrics

### 1. Decision Reuse Rate (%)
**What:** How many decisions does an agent reuse from cache?

**Calculation:**
```
Decision Reuse Rate = (Decisions Queried / Decisions Made) × 100
```

**Example:**
- Agent makes 20 decisions
- 6 of them were "found in cache" (used get_startup_decisions)
- Rate = 6/20 × 100 = 30%

**Target:** 30-40%  
**Measurement:** Count calls to `get_startup_decisions()` vs new `decision()` calls

---

### 2. Token Efficiency (%)
**What:** How many tokens are saved by reusing context?

**Calculation:**
```
Token Efficiency = (Tokens Without Context - Tokens With Context) / Tokens Without Context × 100
```

**How to Measure:**
- Run agent WITHOUT initialize() → measure tokens (baseline)
- Run agent WITH initialize() → measure tokens (with context)
- Calculate difference

**Example:**
- Without context: 50,000 tokens for task
- With context: 35,000 tokens (reused decisions, learnings)
- Efficiency = (50,000 - 35,000) / 50,000 × 100 = 30%

**Target:** 25-40%  
**Measurement:** Compare API usage before/after

---

### 3. Context Availability at Startup (%)
**What:** How much relevant context was actually available?

**Calculation:**
```
Context Availability = (Available Items / Expected Items) × 100
```

**Breakdown:**
- Briefing present: yes/no
- Relevant decisions found: X (target 5-10)
- Recent learnings found: X (target 5-10)
- Checkpoint available: yes/no

**Example:**
```
Briefing:           Yes (1/1)
Decisions (wanted 5): Found 4 (4/5)
Learnings (wanted 5): Found 5 (5/5)
Checkpoint:         Yes (1/1)

Availability = (1+4+5+1) / (1+5+5+1) × 100 = 91.7%
```

**Target:** >80%  
**Measurement:** Log in `StartupDiagnostics` report

---

### 4. Startup Time (ms)
**What:** How fast is initialization?

**Breakdown:**
```
Total Time = API Init + Context Load + Briefing Load + Checkpoint Load
```

**Example Timeline:**
```
API initialization:      15ms
Context loading:         25ms
Briefing retrieval:      10ms
Checkpoint loading:      5ms
─────────────────────────
Total:                   55ms
```

**Target:** <100ms  
**Measurement:** `StartupDiagnostics.print_report()`

---

### 5. Crash Recovery Success (%)
**What:** Can agents recover from crashes?

**Calculation:**
```
Recovery Success = (Agents That Recovered / Agents That Crashed) × 100
```

**Metrics:**
- Checkpoint saved: yes/no
- Checkpoint recoverable: yes/no
- State restored accurately: yes/no
- Work resumed from checkpoint: yes/no

**Target:** 100%  
**Measurement:** Test with intentional crashes

---

### 6. Decision Reuse Accuracy (%)
**What:** Are the reused decisions actually relevant?

**Calculation:**
```
Accuracy = (Relevant Decisions / Retrieved Decisions) × 100
```

**Example:**
- Agent retrieves 5 decisions from cache
- 4 of them were useful for current task
- 1 was irrelevant
- Accuracy = 4/5 × 100 = 80%

**Target:** >85%  
**Measurement:** Manual review or semantic similarity score

---

### 7. Learning Application Rate (%)
**What:** How often do agents apply learnings to avoid mistakes?

**Calculation:**
```
Application Rate = (Times Learning Prevented Rework / Total Learnings) × 100
```

**Example:**
- 10 learnings loaded at startup
- Agent avoided 7 mistakes by applying them
- Application Rate = 7/10 × 100 = 70%

**Target:** >60%  
**Measurement:** Track LEARNING signals + compare actual decisions to anti-patterns

---

### 8. Session Continuity Score (0-100)
**What:** Overall measure of context preservation across sessions

**Calculation:**
```
Continuity Score = 
  (Decision Reuse Rate × 0.3) +
  (Context Availability × 0.2) +
  (Token Efficiency × 0.3) +
  (Recovery Success × 0.2)
```

**Example:**
```
Decision Reuse:    35% × 0.3 = 10.5
Context Availability: 90% × 0.2 = 18
Token Efficiency:  30% × 0.3 = 9
Recovery Success:  100% × 0.2 = 20
─────────────────────────────────────
Continuity Score: 57.5 / 100
```

**Target:** >60  
**Measurement:** Calculate after each agent session

---

## Measurement Tools

### 1. Instrumentation in Code
Track metrics automatically:

```python
class MetricsCollector:
    def __init__(self, agent_id):
        self.decisions_made = 0
        self.decisions_reused = 0
        self.tokens_used = 0
        self.startup_time_ms = 0
        
    def record_decision_reuse(self):
        self.decisions_reused += 1
        
    def record_decision_new(self):
        self.decisions_made += 1
        
    def get_decision_reuse_rate(self):
        if self.decisions_made == 0:
            return 0
        return (self.decisions_reused / self.decisions_made) * 100
```

### 2. Logging & Collection
Save metrics to JSON for analysis:

```python
{
  "session_id": "agent1_20260616_021500",
  "agent_id": "agent1",
  "timestamp": "2026-06-16T02:15:00Z",
  "metrics": {
    "decision_reuse_rate": 35,
    "context_availability": 90,
    "startup_time_ms": 55,
    "tokens_used": 35000,
    "decisions_made": 20,
    "decisions_reused": 7,
    "learnings_applied": 5,
    "crash_recovery_success": true
  }
}
```

### 3. Aggregation & Reporting
Compare across multiple sessions:

```
Agent Performance Report (Last 10 Sessions)
═════════════════════════════════════════════
Decision Reuse Rate:      32% ± 4%  (Target: 30-40%)
Token Efficiency:         28% ± 5%  (Target: 25-40%)
Context Availability:     87% ± 8%  (Target: >80%)
Startup Time:             62ms ± 12ms (Target: <100ms)
Crash Recovery Success:   100%       (Target: 100%)
─────────────────────────────────────────────
Overall Continuity Score: 58.2 / 100 (Target: >60)
```

---

## Test Scenarios

### Scenario 1: Fresh Agent (No Context)
**Setup:** New agent, no prior sessions  
**Measure:**
- Decision reuse rate should be 0%
- Startup time should be minimal
- Context availability should be 0%

**Expected:** Baseline metrics

---

### Scenario 2: Returning Agent (With Context)
**Setup:** Agent initialized for 2nd time  
**Measure:**
- Decision reuse rate should be 20-40%
- Context availability should be >80%
- Startup time should be consistent

**Expected:** Significant improvement vs. Scenario 1

---

### Scenario 3: Crash & Recovery
**Setup:** Agent crashes mid-task, recovers from checkpoint  
**Measure:**
- Recovery success: 100%
- Task resumed from correct progress %
- No work duplicated
- Blockers restored

**Expected:** Perfect recovery

---

### Scenario 4: Similar Task (Different Agent)
**Setup:** Agent A completes "implementation", Agent B does "testing"  
**Measure:**
- Can Agent B reuse decisions from Agent A?
- Decision relevance accuracy

**Expected:** 70%+ accuracy if decisions are related

---

## Red Flags (System Not Working)

| Metric | Problem | Indicates |
|--------|---------|-----------|
| Decision reuse = 0% | No decisions retrieved | Briefing loader broken |
| Startup time > 1000ms | Slow initialization | Context too large or Redis slow |
| Context availability < 50% | Missing context | File fallbacks not working |
| Recovery success < 100% | Crashes aren't recoverable | Checkpoint corruption |
| Token efficiency = 0% | No tokens saved | Decisions not helping |
| Decision relevance < 60% | Wrong decisions suggested | Query algorithm broken |

---

## Success Criteria (System Working)

✅ **All of these must be true:**

1. Decision Reuse Rate: 25-40%
2. Token Efficiency: 20-35%
3. Context Availability: >80%
4. Startup Time: <100ms
5. Crash Recovery: 100%
6. Decision Accuracy: >80%
7. Learning Application: >50%
8. Continuity Score: >60

**If any metric is red, investigate that component**

---

## Measurement Dashboard (Future)

```
Real-Time Metrics Dashboard
════════════════════════════════════════════════════════════

CURRENT SESSION (agent_id: impl_agent_001)
├─ Decision Reuse:       28% ↑ (5/18 reused)
├─ Context Loaded:       92% ✓ (12/13 items)
├─ Startup Time:         48ms ✓ (<100ms)
├─ Tokens Used:          42,350 (vs 58,000 baseline)
├─ Token Efficiency:     27% ✓ (save 15,650)
└─ Status:               RUNNING

LAST 10 SESSIONS AVERAGE
├─ Decision Reuse:       31% (target: 30-40%)
├─ Context Available:    86% (target: >80%)
├─ Startup Time:         61ms (target: <100ms)
├─ Crash Recovery:       100% (target: 100%)
└─ Overall Score:        58.2 / 100 (target: >60)

RED FLAGS: None
RECOMMENDATIONS: None
```

---

## How to Use This Framework

### As a Developer
1. **Before/After:** Compare metrics before and after changes
2. **Regression detection:** Did this change break anything?
3. **Optimization:** Which component is slowest?

### As a User
1. **Trust verification:** Is the system actually helping?
2. **Troubleshooting:** Which metric is failing?
3. **ROI calculation:** How much are we saving?

### In Reports
1. **Executive summary:** "30% token savings achieved"
2. **Technical deep-dive:** "Decision reuse 35%, Context availability 88%"
3. **Recommendations:** "Compress context to improve startup speed"

---

**Next: Implement metrics collection in coordinator_api.py**
