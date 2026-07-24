# Consolidation Plan - Build Clean Foundation

**Goal**: Transform scattered 71 Python files + 98 docs into clean, organized systems with clear dependencies.

**Outcome**: Ready to build Systems 1-5 in order without technical debt.

---

## Phase 1: Archive Old Code (30 min)

### Create Archive Structure
```
E:\AI-Setup\
├── _archive/                    # Old, experimental, not needed
│   ├── python_old/
│   ├── docs_old/
│   └── README.md (what's here and why)
```

### Python Files to Archive (50+ files)
These are experimental, old, or duplicates. Move to `_archive/python_old/`:

**Vision/OCR (GPU not ready):**
- vision_engine.py
- vision_engine_comfy.py
- fast_ocr.py
- vision_scan_windows.py
- florence_vision_setup.py

**Docker/Stack (experimental):**
- launch_ai_stack.py
- stack_manager.py
- stack_analysis.py
- stack_gui.py
- monitor_turbo_launch.py
- ui_scout.py

**Alternative Session/Redis (duplicates):**
- session_manager.py
- session_supervisor.py
- sessions.py
- session_canonical.py
- session_compare.py
- redis_helper.py
- redis_sync_admin.py
- redis_failover_sync.py
- migrate_logs.py
- migrate_sessions.py

**Logging variants (keep only session_logger.py):**
- log.py
- smart_log.py
- auto_logger.py
- log_analysis.py
- patch_log.py

**Experimental/one-off scripts:**
- agentic_automation.py
- auto_capture.py
- ai_helper.py
- gemma_voice_service.py
- chronicle.py
- populate_chronicle.py
- origin_story.py
- journey_dump.py
- catchup.py
- check_active.py
- check_new.py
- task_context.py
- work_context.py
- project_context.py (see if used, else archive)
- add_milestone.py
- escalation.py
- operational_alerts.py
- health_check_session_pipeline.py
- bulk_compress.py
- patch_log.py
- persist_semantic_learnings.py
- port_registry.py
- update_port_registry.py
- signal_counter.py
- system_summary.py
- diagnosis.py
- ai_setup_mcp.py

**Keep these (Core, working, tested):**
- ✅ coordinator_api.py
- ✅ coordinator_service.py
- ✅ learning_store.py
- ✅ session_state.py
- ✅ redis_sync_coordinator.py
- ✅ session_recovery.py
- ✅ startup_diagnostics.py
- ✅ agent_init.py
- ✅ session_logger.py
- ✅ fast_cache.py (performance optimization, keep)
- ✅ config.py (configuration, keep)
- ✅ bootstrap.py (entry point, keep)
- ✅ relationship_types.py (semantic framework, keep)

**Keep test files (but clean up):**
- ✅ test_coordinator_foundation.py
- ✅ test_phase1_validation.py
- ✅ test_sync_integration.py
- Archive old test variants

---

## Phase 2: Consolidate Documentation (1 hour)

### Create Documentation Structure
```
E:\AI-Setup\
├── docs/                        # Core documentation
│   ├── _archive/               # Old docs (move here)
│   └── current/                # Active docs
```

### Core Documentation to Keep (15 files)
```
E:\AI-Setup/docs/current/
├── bootstrap.md                         # ENTRY POINT (keep updated)
├── SYSTEMS_ARCHITECTURE.md              # System design
├── IMPLEMENTATION_INVENTORY.md          # Build plan
├── ACTUAL_INVENTORY.md                  # Reality check
├── FRAMEWORK_PROTOCOL.md                # System protocols
├── SIGNAL_REFERENCE.md                  # Signal types
├── CONTEXT_SCHEMA.md                    # Context structure
├── LEARNING_SYSTEM_QUICKSTART.md        # Learning guide
├── LEARNING_SYSTEM_INDEX.md             # Learning navigation
├── PHASE_1_CHECKPOINT.md                # What we built
├── SYSTEM_STATUS.md                     # Current status
├── ERROR_HANDLING_GUIDE.md              # Error patterns
├── BOOTSTRAP_MANIFEST.md                # Doc maintenance rules
├── SEMANTIC_NAMING_CONVENTION.md        # Code style
├── AGENT_ONBOARDING.md                  # Agent guide
└── _archive_list.md                     # What was archived and why
```

### Archive All Others (98 - 15 = 83 files)
Move to `docs/_archive/`:
- All AGENT_*.md variants
- All BOOTSTRAP_*.md variants
- All SESSION_*.md variants
- All INITIALIZATION_*.md variants
- All INTEGRATION_*.md variants
- All CONTEXT_*.md variants (keep main one)
- All LEARNING_SYSTEM_*.md variants (keep essentials)
- All REFACTORING_*.md
- All PHASE_1_*.md variants (keep main one)
- All experimental/theoretical docs

---

## Phase 3: Create Clean Package Structure (30 min)

### New Directory Structure
```
E:\AI-Setup/
├── core/                                # Core systems (existing code moved here)
│   ├── __init__.py                      # Package init
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── coordinator_api.py           # Moved from root
│   │   ├── coordinator_service.py       # Moved from root
│   │   └── types.py                     # Signal type definitions
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   ├── session_state.py             # Moved from root
│   │   ├── session_recovery.py          # Moved from root
│   │   ├── redis_sync_coordinator.py    # Moved from root
│   │   └── checkpoint.py                # Extracted/new
│   │
│   └── learning/
│       ├── __init__.py
│       └── learning_store.py            # Moved from root
│
├── context/                             # NEW - System 4 (to be built)
│   ├── __init__.py
│   ├── briefing_loader.py               # Load previous handoff
│   ├── decision_loader.py               # Load decisions
│   ├── learning_loader.py               # Load learnings
│   ├── blocker_loader.py                # Load blockers
│   ├── ranker.py                        # Relevance scoring
│   ├── summarizer.py                    # Compress learnings
│   ├── aggregator.py                    # Combine into dict
│   └── quality_scorer.py                # Calculate quality
│
├── infrastructure/                      # NEW - System 1 (to consolidate)
│   ├── __init__.py
│   ├── orchestrator.py                  # Main: launch all systems
│   ├── wsl.py                           # WSL detection + enable
│   ├── docker.py                        # Docker startup
│   ├── redis.py                         # Redis startup + check
│   └── health_check.py                  # Overall health
│
├── agent/                               # System 5 (to refactor)
│   ├── __init__.py
│   ├── initializer.py                   # Main bootstrap (from agent_init.py)
│   ├── detector.py                      # Detect agent type
│   ├── supervisor.py                    # Manage lifecycle
│   └── briefing_generator.py            # Create briefings
│
├── docs/                                # Documentation
│   ├── current/                         # Active docs (consolidated)
│   │   ├── bootstrap.md
│   │   ├── SYSTEMS_ARCHITECTURE.md
│   │   └── ... (15 core files)
│   └── _archive/                        # Historical (83 files)
│
├── tests/                               # All tests
│   ├── test_system_1_infrastructure.py
│   ├── test_system_2_signals.py
│   ├── test_system_3_state.py
│   ├── test_system_4_context.py
│   ├── test_system_5_agent.py
│   └── test_integration.py
│
├── _archive/                            # Old code
│   ├── python_old/                      # 50+ archived Python files
│   └── README.md                        # What's here and why
│
├── session_logs/                        # Existing (unchanged)
├── session_cache/                       # Existing (unchanged)
│
├── bootstrap.py                         # ENTRY POINT (root, unchanged)
├── config.py                            # Configuration (moved? or keep root)
├── relationship_types.py                # Semantic framework (moved? or keep root)
├── fast_cache.py                        # Performance (moved? or keep root)
├── CONSOLIDATION_PLAN.md                # This file
└── README.md                            # Project root
```

**Files to keep at root (entry points + config):**
- bootstrap.py (users run this)
- config.py (global configuration)
- relationship_types.py (semantic framework, widely used)
- fast_cache.py (performance, widely used)

**Files to move to packages:**
- All core system files (signals, state, learning) → core/
- All infrastructure files → infrastructure/
- All agent files → agent/

---

## Phase 4: Update Imports & Test (1 hour)

### Import Path Changes

**Before:**
```python
from coordinator_api import initialize
from session_state import SessionState
from learning_store import LearningStore
```

**After:**
```python
from core.signals.coordinator_api import initialize
from core.state.session_state import SessionState
from core.learning.learning_store import LearningStore
```

### Files to Update Imports In:
- bootstrap.py
- agent_init.py (or moved to agent/initializer.py)
- All test files
- Any other files that import these modules

### Testing Checklist:
```
[ ] Python path resolution works
[ ] Can import from core/ package
[ ] Can import from agent/ package
[ ] All existing tests still pass
[ ] No circular imports
[ ] bootstrap.py still works
```

---

## Phase 5: Documentation Updates (30 min)

### Update Key Files

**bootstrap.md**: Point to current docs structure
```
Old: See all 98 markdown files scattered
New: See docs/current/*.md for active docs
     See _archive/ or docs/_archive/ for historical
```

**BOOTSTRAP_MANIFEST.md**: Update with new structure
```
Maintain clear rules for:
- Where docs go (docs/current/)
- Archive rules
- Maintenance responsibilities
```

**README.md** (create/update at root):
```
AI-Setup Multi-Agent Coordination System

## Quick Start
See docs/current/bootstrap.md

## Architecture
See docs/current/SYSTEMS_ARCHITECTURE.md

## Code Organization
- core/       - Working core systems (signals, state, learning)
- context/    - Context intelligence (System 4 - new)
- infrastructure/ - Infrastructure orchestration (System 1)
- agent/      - Agent orchestration (System 5)
- tests/      - All tests
- docs/       - Documentation
- _archive/   - Old code (reference only)

## Status
Foundation phase: Clean structure created
Building: System 1, 2, 3, 4, 5 in order
```

---

## Consolidation Checklist

### Step 1: Archive Old Code (15 min)
```
[ ] Create _archive/ directory
[ ] Create _archive/python_old/ directory
[ ] Create _archive/README.md (explain what's here)
[ ] Move 50+ old Python files to _archive/python_old/
[ ] Move old test variants to _archive/
```

### Step 2: Archive Old Docs (15 min)
```
[ ] Create docs/ directory
[ ] Create docs/current/ directory
[ ] Create docs/_archive/ directory
[ ] Move 83 old markdown files to docs/_archive/
[ ] Move 15 core docs to docs/current/
```

### Step 3: Create Package Structure (10 min)
```
[ ] Create core/ package
[ ] Create core/signals/ package
[ ] Create core/state/ package
[ ] Create core/learning/ package
[ ] Create context/ package (empty for now)
[ ] Create infrastructure/ package (empty for now)
[ ] Create agent/ package
[ ] Create tests/ package
```

### Step 4: Move Core Files (15 min)
```
[ ] Move coordinator_api.py → core/signals/
[ ] Move coordinator_service.py → core/signals/
[ ] Move session_state.py → core/state/
[ ] Move session_recovery.py → core/state/
[ ] Move redis_sync_coordinator.py → core/state/
[ ] Move learning_store.py → core/learning/
[ ] Move startup_diagnostics.py → ? (where should this go?)
[ ] Move all test_*.py → tests/
```

### Step 5: Update Imports (30 min)
```
[ ] Update bootstrap.py imports
[ ] Update agent_init.py imports
[ ] Update test imports
[ ] Update coordinator_service imports
[ ] Test all imports work
```

### Step 6: Create __init__.py Files (10 min)
```
[ ] core/__init__.py
[ ] core/signals/__init__.py
[ ] core/state/__init__.py
[ ] core/learning/__init__.py
[ ] agent/__init__.py
[ ] context/__init__.py
[ ] infrastructure/__init__.py
[ ] tests/__init__.py
```

### Step 7: Verify & Test (15 min)
```
[ ] Run test_coordinator_foundation.py
[ ] Run any other critical tests
[ ] Verify bootstrap.py works
[ ] Check for import errors
[ ] Python path resolution works
```

### Step 8: Documentation Updates (15 min)
```
[ ] Update bootstrap.md
[ ] Update BOOTSTRAP_MANIFEST.md
[ ] Create/update README.md at root
[ ] Create docs/_archive/README.md (what's archived)
```

---

## Total Time Estimate

| Phase | Task | Time |
|-------|------|------|
| 1 | Archive old Python files | 15 min |
| 2 | Archive old docs | 15 min |
| 3 | Create package structure | 10 min |
| 4 | Move core files | 15 min |
| 5 | Update imports | 30 min |
| 6 | Create __init__.py | 10 min |
| 7 | Test & verify | 15 min |
| 8 | Update docs | 15 min |
| **TOTAL** | | **2 hours** |

**Then ready to build Systems 1-5 with clean foundation!**

---

## Success Criteria

✅ **Code Organization**
- All core systems in organized packages
- Clear 5-system structure
- No loose files at root (except entry points)
- All imports work

✅ **Documentation**
- 15 core docs in docs/current/
- 83 archived docs safe in docs/_archive/
- Clear navigation and purpose
- No duplication

✅ **Testability**
- All tests pass
- No circular imports
- Can run tests from any directory
- Clear test organization

✅ **Readability**
- Package structure obvious
- Each system has clear boundaries
- Dependencies explicit
- Easy to onboard new understanding

---

## Proceed?

This consolidation will take ~2 hours and give us a **clean, professional foundation** for building Systems 1-5.

Ready to start? I can execute these steps while you review, or do them together.

