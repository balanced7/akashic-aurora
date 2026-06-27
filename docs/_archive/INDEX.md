# BreakThrough Stack - Index

## Logging Strategy: Smart Log System

**Philosophy**: Log everything, summarize intelligently, chronicle skeptically.

---

## Three-Tier System

### 1. RAW LOGS (Automatic)
- **Location**: `session_logs/session_all.jsonl`
- **What**: EVERYTHING - all actions
- **Purpose**: Play-by-play, debugging

### 2. SESSION DIGESTS (Auto)
- **Location**: `sessions/YYYY-MM-DD/*_digest.md`
- **When**: Only if 3+ meaningful entries
- **Purpose**: Historical context

### 3. CHRONICLES (Auto + Skeptical)
- **Location**: `chronicles/*.json`
- **Purpose**: Significant events with verification

---

## Smart Auto-Chronicle

**Status Levels** (for skeptical tracking):
- `[P]` prototype - Initial implementation
- `[A]` alpha - Basic functionality
- `[?]` claimed - Agent says done (NEEDS VERIFICATION!)
- `[B]` beta - Tested/verified
- `[S]` stable - Production-ready

**Auto-Detection**:
```
"completed X" / "finished X" → chronicle (status=claimed, CONFIDENCE=40%)
"tested X" / "verified X" → chronicle (status=beta, CONFIDENCE=80%)
"failed X" → auto-failure entry
"decided X" → auto-decision entry
```

---

## Dynamic Tag Vocabulary

Tags are **learned dynamically** from content:
- Domain terms extracted automatically (e.g., "florence-2", "directml")
- Frequency-based: more mentions = more confident
- Stored in: `chronicles/tag_vocabulary.json`

---

## Commands

```bash
# Session summary
python smart_log.py summary
python smart_log.py search "query"

# Chronicle status
python smart_log.py chronicles
python smart_log.py tags

# Full chronicle (skeptical view)
python chronicle.py
python chronicle.py --verify  # Show unverified entries
```

---

## Code Usage

```python
from smart_log import log, decision, failure

log("Implemented feature X")           # Auto-chronicles if significant
decision("Chose Redis", rationale=[])  # Auto-chronicles as ADR
failure("Bug in X", fix="Changed Y")   # Auto-chronicles

summarize()  # Auto-summarize if meaningful
```

---

## Key Principles

1. **Be skeptical of completion claims** - "completed" gets status=claimed (40% confidence)
2. **Verify before trusting** - Check `[?]` entries before trusting milestones
3. **Learn tags dynamically** - System discovers relevant terms from context
4. **Auto-summarize only meaningful sessions** - 3+ significant entries threshold
