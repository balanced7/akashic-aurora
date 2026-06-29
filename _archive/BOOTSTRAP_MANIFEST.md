# Bootstrap Manifest - Documentation Architecture

**Purpose:** Define the systematic structure for startup/catchup documentation  
**Status:** Active (2026-06-16)  
**Audience:** System architects, new sessions, documentation maintenance

---

## Documentation Hierarchy

```
BOOTSTRAP.MD (minimal entry point)
    ↓
┌───────────────────────────────────────────────────────┐
│ SYSTEM_STATUS.MD (single source of truth)            │
│ ├─ Current phase                                      │
│ ├─ What's working/broken/planned                     │
│ └─ Last validated timestamp                          │
└───────────────────────────────────────────────────────┘
    ↓
    ├─→ AGENT_ONBOARDING.MD (framework entry)
    ├─→ PHASE_<N>_CHECKPOINT.MD (what we built)
    ├─→ LEARNING_SYSTEM_INDEX.MD (learning docs)
    ├─→ INFRASTRUCTURE_STATUS.MD (systems)
    └─→ TROUBLESHOOTING.MD (problems)
```

---

## Document Purposes

### Tier 1: Minimal Entry Points

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **bootstrap.md** | "You are here" + quick decision tree | Everyone | <150 lines |
| **SYSTEM_STATUS.md** | Single source of truth for system state | Everyone | <100 lines |

### Tier 2: Framework Documentation

| Document | Purpose | When to Read | Maintained By |
|----------|---------|-------------|---------------|
| **AGENT_ONBOARDING.md** | How to join and operate as an agent | New agents | Framework architect |
| **CONTEXT_SCHEMA.md** | What context is available | When building context awareness | Framework architect |
| **SIGNAL_REFERENCE.md** | Signal types and formats | When emitting signals | Framework architect |
| **FRAMEWORK_PROTOCOL.md** | How the whole system works | Understanding architecture | Framework architect |

### Tier 3: Phase Documentation

| Document | Purpose | Scope | Status |
|----------|---------|-------|--------|
| **PHASE_1_CHECKPOINT.md** | Complete work summary for Phase 1 | Learning system implementation | ✅ DONE |
| **PHASE_2_PLAN.md** | Goals and deliverables for Phase 2 | Automated summaries + dashboards | ⏳ PLANNED |
| **PHASE_3_PLAN.md** | Goals and deliverables for Phase 3 | Intelligent patterns + guardrails | 🎯 ROADMAP |

Each phase doc follows this structure:
- What we're building (goals)
- What we deliver (code, docs, tests)
- How to validate it works (success criteria)
- What comes next (Phase N+1)
- Timeline and blockers

### Tier 4: System Documentation

| Document | Purpose | Covers |
|----------|---------|--------|
| **INFRASTRUCTURE_STATUS.md** | Current infrastructure state | What's running, broken, planned |
| **LEARNING_SYSTEM_INDEX.md** | Complete learning system guide | All learning docs organized |
| **TROUBLESHOOTING.md** | Problem-symptom-solution index | Common issues and fixes |

---

## Key Principles

### 1. **Single Source of Truth**
- SYSTEM_STATUS.md is **the** place to check current state
- All other docs reference it, not vice versa
- Timestamp shows when it was last verified

### 2. **Minimal Entry Points**
- bootstrap.md stays <150 lines
- Only contains: "you are here" + decision tree
- Everything else is links to specialized docs

### 3. **Phase-Based Organization**
- Each phase (1, 2, 3) has its own checkpoint/plan
- Phases don't bleed into each other
- Clear entry point for "what's in this phase"

### 4. **Separation of Concerns**
- Framework docs: How agents work (timeless)
- Phase docs: What we're building now (time-bound)
- Infrastructure docs: Systems status (constantly updating)
- Learning docs: System knowledge (growing)

### 5. **Validation Rules** (manual, before restart)
Before you restart:
- [ ] SYSTEM_STATUS.md has current phase and status
- [ ] PHASE_<N>_CHECKPOINT.md exists and is linked from bootstrap.md
- [ ] All links in bootstrap.md point to real files
- [ ] Timestamp on SYSTEM_STATUS.md is recent

---

## Documentation Maintenance

### When Starting a New Phase
1. Create PHASE_<N>_CHECKPOINT.md or PHASE_<N>_PLAN.md
2. Update SYSTEM_STATUS.md with new phase number
3. Add link to PHASE_<N> in bootstrap.md decision tree
4. Timestamp SYSTEM_STATUS.md

### When Adding a Feature
1. Document it in relevant PHASE_<N> doc
2. If it's learning-related, add to LEARNING_SYSTEM_INDEX.md
3. If it's infrastructure, add to INFRASTRUCTURE_STATUS.md
4. Update SYSTEM_STATUS.md timestamp

### When Something Breaks
1. Document symptom and fix in TROUBLESHOOTING.md
2. If infrastructure, update INFRASTRUCTURE_STATUS.md
3. If it blocks a phase, update PHASE_<N> "blockers" section

---

## Quick Reference: What to Read When

| Scenario | Read This | Then This |
|----------|-----------|-----------|
| "I'm lost, where do I start?" | bootstrap.md | SYSTEM_STATUS.md |
| "What phase are we in?" | SYSTEM_STATUS.md | PHASE_<N>_CHECKPOINT.md |
| "How do I work as an agent?" | AGENT_ONBOARDING.md | CONTEXT_SCHEMA.md |
| "How do I emit signals?" | SIGNAL_REFERENCE.md | FRAMEWORK_PROTOCOL.md |
| "Tell me about learning system" | LEARNING_SYSTEM_INDEX.md | LEARNING_QUICKSTART.md |
| "Something's broken" | TROUBLESHOOTING.md | INFRASTRUCTURE_STATUS.md |
| "What should I work on next?" | PHASE_<N>_CHECKPOINT.md | Next section in that doc |

---

## File Locations

All documentation lives in: `E:\AI-Setup/`

Core files that stay minimal:
```
E:\AI-Setup\
├── bootstrap.md                    (entry point, <150 lines)
├── BOOTSTRAP_MANIFEST.md           (this file, architecture definition)
├── SYSTEM_STATUS.md                (single source of truth)
├── TROUBLESHOOTING.md              (problem index)
└── INFRASTRUCTURE_STATUS.md        (systems status)
```

Framework docs (timeless):
```
E:\AI-Setup\
├── AGENT_ONBOARDING.md
├── CONTEXT_SCHEMA.md
├── SIGNAL_REFERENCE.md
└── FRAMEWORK_PROTOCOL.md
```

Phase docs (time-bound):
```
E:\AI-Setup\
├── PHASE_1_CHECKPOINT.md           (complete)
├── PHASE_2_PLAN.md                 (planned)
└── PHASE_3_PLAN.md                 (roadmap)
```

Learning system docs (specialized):
```
E:\AI-Setup\
├── LEARNING_SYSTEM_INDEX.md
├── LEARNING_SYSTEM_QUICKSTART.md
├── LEARNING_SYSTEM_PHASE_1.md
├── LEARNING_SYSTEM_ROADMAP.md
└── learning_store.py               (implementation)
```

---

## Evolution Path

**Right Now (Session 1):**
- ✅ Bootstrap.md exists
- ✅ PHASE_1_CHECKPOINT.md created
- ✅ Learning system implemented
- 📋 BOOTSTRAP_MANIFEST.md created
- 📋 SYSTEM_STATUS.md created
- 📋 Refactor bootstrap.md to be minimal

**After Restart (Session 2+):**
- Read bootstrap.md (<2 min)
- Check SYSTEM_STATUS.md (what phase are we in?)
- Jump to relevant phase doc
- Fully oriented in <5 min

**Phase 2 Planning:**
- Create PHASE_2_PLAN.md
- Update SYSTEM_STATUS.md (phase = 2)
- Continue pattern

**Phase 3 Planning:**
- Create PHASE_3_PLAN.md
- Update SYSTEM_STATUS.md (phase = 3)
- Continue pattern

---

## Why This Architecture Works

| Problem | Solution |
|---------|----------|
| Bootstrap gets stale | Minimal + timestamps on SYSTEM_STATUS.md |
| Too much info at start | Decision tree narrows to what you need |
| Phases unclear | PHASE_<N> docs explicitly scope each phase |
| Infrastructure confusion | INFRASTRUCTURE_STATUS.md single place |
| Documentation scattered | BOOTSTRAP_MANIFEST defines structure |
| Hard to maintain | Clear rules: when to update what |

---

## For Future Implementation (Automation)

When time permits, these could be automated:
- Generate SYSTEM_STATUS.md from phase docs
- Validate all bootstrap.md links exist
- Check timestamps are recent
- Generate TROUBLESHOOTING.md from issues
- Auto-update LEARNING_SYSTEM_INDEX from learning_store.py

For now: **manual, systematic, elegant**

---

**This manifest ensures that as the system grows, documentation stays coherent and navigation stays simple.**

