# bootstrap.md - System Entry Point

> **START HERE** - This file orients you to the entire system  
> Read this first (5 min), then jump to the specific doc you need

**Current Phase:** 1.5 (Startup & Context Recovery) ✅ Complete  
**System Status:** All modules integrated, metrics validated, tests passing  
**Last Updated:** 2026-06-16  
**Metrics:** Decision reuse 60%, Token efficiency 42.9%, Context loading working  
**Next Step:** Test with real agents, implement context compression, persist decision cache  

See **`SYSTEM_STATUS.md`** for detailed current state and timeline

---

## 🎯 Where Are You?

### "I'm lost, where do I start?"
→ Read **`SYSTEM_STATUS.md`** (2 min) → You'll know what phase we're in and what to do next

### "I'm a new agent joining the system"
→ Read **`AGENT_ONBOARDING.md`** (10 min) → You'll know how to operate  
→ Then read **`PHASE_1_CHECKPOINT.md`** → You'll know what's been built

### "I'm continuing from before"
→ Read **`PHASE_1_CHECKPOINT.md`** (5 min) → Jump to "Next Steps"

### "I want to understand the architecture"
→ Read **`FRAMEWORK_PROTOCOL.md`** (15 min) → Full system design

### "I want to emit signals / work with the framework"
→ Read **`SIGNAL_REFERENCE.md`** (10 min) → Then **`FRAMEWORK_PROTOCOL.md`**

### "I want to learn about the learning system"
→ Read **`LEARNING_SYSTEM_INDEX.md`** → Then **`LEARNING_SYSTEM_QUICKSTART.md`**

### "I'm an agent ready to initialize myself" (NEW - EXECUTABLE)
→ **READ THIS FIRST:** `OPENCODE_START_HERE.md` (optimized for quick reading, first 50 lines have everything)
→ **THEN:** Use the code there to initialize
→ **GET:** API instance + context + diagnostics ready to work
→ **MORE OPTIONS:** Read `INITIALIZATION_GUIDE.md` and `AGENT_INIT_QUICK_START.md`

### "I want to understand startup & context recovery"
→ Read **`INITIALIZATION_GUIDE.md`** (usage) → **`METRICS_FRAMEWORK.md`** (how to measure)

### "I need to set up infrastructure"
→ Read **`INFRASTRUCTURE_STATUS.md`** → Then **`SYSTEM_STATUS.md`**

### "Something's broken or I'm stuck"
→ Read **`TROUBLESHOOTING.md`** → Find your symptom

---

## 📖 Quick Navigation

### Framework Documentation (How the system works)
- **`AGENT_ONBOARDING.md`** - Join the system and operate as an agent
- **`CONTEXT_SCHEMA.md`** - What context is available
- **`SIGNAL_REFERENCE.md`** - Signal types and formats
- **`FRAMEWORK_PROTOCOL.md`** - Complete system architecture

### Phase Documentation (What we're building)
- **`PHASE_1_CHECKPOINT.md`** - Learning system implementation (DONE ✅)
- **`PHASE_2_PLAN.md`** - Automated summaries (Planned ⏳)
- **`PHASE_3_PLAN.md`** - Intelligent patterns (Roadmap 🎯)

### Learning System (Prevent rework, share knowledge)
- **`LEARNING_SYSTEM_INDEX.md`** - Complete learning guide
- **`LEARNING_SYSTEM_QUICKSTART.md`** - 5-min developer guide
- **`learning_store.py`** - Implementation

### System Documentation
- **`SYSTEM_STATUS.md`** ⭐ **START HERE** - Current state
- **`BOOTSTRAP_MANIFEST.md`** - Documentation architecture
- **`INFRASTRUCTURE_STATUS.md`** - Systems and ports
- **`TROUBLESHOOTING.md`** - Problem solving

---

## ⚡ TL;DR Quick Start (3 paths)

### If you're an AGENT initializing yourself:
```python
from agent_init import initialize_and_load_context

result = initialize_and_load_context("your_agent_id", task_keyword="your_task")
api = result["api"]
context = result["context"]
# You now have full context loaded and ready to work
```

### If you're running TESTS:
```bash
cd E:\AI-Setup
python test_onboarding_v2.py    # Compare old vs new (shows 60% decision reuse)
python test_fixes_quick.py      # Verify all components
```

### If you just RESTARTED the system:
1. **Verify WSL**
   ```powershell
   wsl --list --verbose
   # Should show: Ubuntu-... Running ... 2
   ```

2. **Start Redis** (optional, system works without it)
   ```powershell
   cd E:\AI-Setup\dockerized-ai\redis
   docker compose -f docker-compose-edge-mirror.yml up -d
   ```

3. **Verify Tests Pass**
   ```bash
   cd E:\AI-Setup
   python test_onboarding_v2.py
   # Should show: Decision Reuse 60%, Token Efficiency 42.9%
   ```

---

## 📚 Document Architecture

See **`BOOTSTRAP_MANIFEST.md`** for:
- Complete documentation hierarchy
- Which doc to read for which scenario
- Maintenance rules (when to update what)
- Evolution path (how system grows)

---

## 🚀 Three Paths Forward

**Path A: I need to understand everything fast**
1. Read SYSTEM_STATUS.md (2 min)
2. Read FRAMEWORK_PROTOCOL.md (15 min)
3. Read PHASE_1_CHECKPOINT.md (5 min)
4. Done - you understand the system

**Path B: I need to start working**
1. Read AGENT_ONBOARDING.md (10 min)
2. Read your briefing or PHASE_1_CHECKPOINT.md (5 min)
3. Start working
4. Emit signals using SIGNAL_REFERENCE.md

**Path C: I need to set up systems**
1. Read INFRASTRUCTURE_STATUS.md
2. Read SYSTEM_STATUS.md
3. Follow setup steps
4. Run tests to verify

---

## 📋 Key Files for Reference

| Need | File |
|------|------|
| Current state? | SYSTEM_STATUS.md |
| Framework? | AGENT_ONBOARDING.md |
| Signals? | SIGNAL_REFERENCE.md |
| Architecture? | FRAMEWORK_PROTOCOL.md |
| What we built? | PHASE_1_CHECKPOINT.md |
| Learning system? | LEARNING_SYSTEM_INDEX.md |
| Infrastructure? | INFRASTRUCTURE_STATUS.md |
| Problem? | TROUBLESHOOTING.md |
| Documentation map? | BOOTSTRAP_MANIFEST.md |

---

## ✅ You Are Ready

Everything is documented. Everything is linked. Everything makes sense.

**Pick one of the three paths above and go.**

---

*Last verified: 2026-06-16*  
*For detailed state: See SYSTEM_STATUS.md*  
*For doc architecture: See BOOTSTRAP_MANIFEST.md*
