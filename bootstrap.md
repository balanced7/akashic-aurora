# bootstrap.md - DEPRECATED
> **⚠️ DEPRECATED**: Read `STARTUP.md` instead. This file is kept for reference only.

**Superseded by**: `E:\AI-Setup\STARTUP.md`

---

## Quick Redirect

If you're starting a new session, read these files **in order**:

1. **`STARTUP.md`** (this directory) - Session initialization, re-prime detection
2. **`ARCHITECTURE.md`** - System architecture and design
3. **`AGENT_PRIMER.md`** - Best practices, ports, Docker, GPU setup
4. **`COORDINATION_PRIMER.md`** - Enterprise coordination patterns

---

## What Changed

### Old Bootstrap System (DEPRECATED)
- Multiple bootstrap files: `bootstrap.md`, `bootstrap_generator.md`, `bootstrap_analyst.md`, `bootstrap_master.md`, `bootstrap_common.md`
- No automatic session change detection
- Confusing startup sequence across files

### New Startup System (CURRENT)
- **Single entry point**: `STARTUP.md`
- **Automatic session detection**: `session_manager.py`
- **Re-prime triggers**: When SESSION_ID changes
- **Unified initialization**: `session_logger.py` integrates with `session_manager.py`

---

## Migration

### Old Way (DEPRECATED)
```python
# scattered across files
from session_logger import log
from blackboard import init_blackboard
# confusing order of operations
```

### New Way (CURRENT)
```python
# Single import auto-detects session changes
from session_logger import log, SESSION_ID, SESSION_UNIQUE
from session_manager import check_and_reprime

state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
if state.is_new:
    print("RE-PRIME REQUIRED")
```

---

## Key Files

| File | Status | Purpose |
|------|--------|---------|
| `STARTUP.md` | **CURRENT** | Primary startup documentation |
| `ARCHITECTURE.md` | Current | System architecture |
| `AGENT_PRIMER.md` | Current | Best practices |
| `COORDINATION_PRIMER.md` | Current | Enterprise patterns |
| `bootstrap.md` | DEPRECATED | This file - redirect only |
| `bootstrap_*.md` | DEPRECATED | Superseded by STARTUP.md |

---

## Commands

### Check Session State
```bash
python E:\AI-Setup\reprime.py --check
```

### Force Re-prime
```bash
python E:\AI-Setup\reprime.py --force
```

### Run Full Initialization
```bash
python E:\AI-Setup\init_session.py
```

---

**Last Updated**: 2026-04-14  
**Supersedes**: All `bootstrap_*.md` files
