# Smart Log System - Summary

## Philosophy

**Log everything. Summarize intelligently. Chronicle only what matters.**

---

## Three-Tier System

### 1. RAW LOGS (Automatic)
**Where**: `session_logs/session_all.jsonl` + backup  
**What**: EVERYTHING - all actions, errors, decisions  
**Who**: Automatic (session_logger + smart_log)  
**Purpose**: Play-by-play for debugging/troubleshooting

```
✅ ALWAYS logged:
- Every action
- Every error
- Every decision
- Session start/end
```

### 2. SESSION DIGESTS (Auto-Generated)
**Where**: `sessions/YYYY-MM-DD/*_digest.md`  
**When**: Only if session has 3+ meaningful items  
**Purpose**: Quick historical context

```bash
python smart_log.py summary    # Recent sessions
python smart_log.py search X   # Find relevant sessions
```

### 3. CHRONICLES (Manual)
**Where**: `chronicles/*.json`  
**When**: Only significant milestones/decisions/failures  
**Purpose**: Architecture history, decision rationale

```python
from smart_log import milestone, decision, failure

milestone("Learning Store v2", "Unified 5 modules into 1")
decision("Why Redis?", rationale=["Fast", "Persistent", "Already running"])
failure("Race condition", root_cause="Parallel writes", fix="Sequential")
```

---

## When to Use What

| Situation | Action | Goes To |
|-----------|--------|---------|
| "I did X" | `log("Did X")` | Raw logs |
| "I'm doing significant work" | Keep logging | Raw logs |
| "I made a decision" | `decision("X over Y", rationale=[...])` | Chronicle |
| "Something failed" | `failure("Symptom", fix="Solution")` | Chronicle |
| "Major achievement" | `milestone("Feature X done")` | Chronicle |
| Session ended | Auto | Digest if meaningful |

---

## The Logic Tree

```
Start session
    ↓
Do work → Log everything (automatic)
    ↓
End session → Auto-summarize if 3+ meaningful items
    ↓
Significant event? → Yes → Create chronicle entry
    ↓
That's it. Log everything, let the system decide what matters.
```

---

## Commands

```bash
# What's happened recently?
python smart_log.py summary

# Find sessions about X
python smart_log.py search "florence"

# Show all decisions/milestones/failures
python smart_log.py chronicle
```

---

## What Makes a Session "Meaningful"?

**Significant patterns:**
- created, completed, implemented, fixed, designed, decided
- discovered, learned, migrated, consolidated, deployed

**NOT significant (noise filtered):**
- session_continu, logger_startup, ping, heartbeat

**Threshold:** 3+ meaningful entries = digest created
