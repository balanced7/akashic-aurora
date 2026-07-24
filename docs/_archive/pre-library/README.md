# Archive - Historical Code & Experiments

**Last Updated**: 2026-06-17  
**Consolidation**: Complete  

This directory contains code that is NOT part of the active system. It's preserved for historical reference.

## What's Here

### python_old/ (59 files)
Experimental, duplicate, or outdated Python modules:

**Categories**:
- **Vision/OCR**: vision_engine.py, etc. (GPU infrastructure incomplete)
- **Docker/Stack**: launch_ai_stack.py, stack_manager.py, etc. (experimental)
- **Session Variants**: session_manager.py, sessions.py, etc. (superseded by core/state/)
- **Logging Variants**: log.py, smart_log.py, etc. (superseded by session_logger.py)
- **One-off Scripts**: Various automation, diagnostics, etc.
- **Old Tests**: test variants from earlier phases

**Why Archived**:
These were built during exploratory phases but aren't part of the consolidated foundation. They may be useful for reference (e.g., vision_engine.py to understand GPU setup) but shouldn't be imported or used.

**If You Need Something From Here**:
1. Check if functionality already exists in `core/` packages
2. If not, copy it to the appropriate package
3. Rename to use semantic naming (subject_relationship_object)
4. Update imports
5. Add tests

## How to Reference This

**Example**: If you need logging utilities:
```python
# Don't use archived log.py
# Instead use: core/foundation/ or current session_logger.py
```

**Example**: If you need vision system insights:
```python
# Don't import archived vision_engine.py
# Instead, review it for approach, but implement in proper package with:
# - Semantic naming
# - Proper integration with core systems
# - Tests
```

---

## Consolidation Summary

**Total Archived**:
- 59 Python files (experimental/old variants)
- 94 Documentation files (historical/superseded)

**Core Kept**:
- 10 Python files (working, tested)
- 17 Documentation files (essential, current)

**Result**: Clean foundation with 5 organized systems + 2 meta-layers.

---

## Recovery Path

If you ever need code from here:

1. **Identify the feature** you need from archived code
2. **Find where it belongs** in the new structure (core/, context/, infrastructure/, agent/)
3. **Copy the logic** but rewrite it with:
   - Semantic naming (use relationship_types.py vocabulary)
   - Proper imports (from core.* packages)
   - Tests
   - Documentation with relationship types
4. **Integrate** with the consolidation structure
5. **Test** with the new test suite

This keeps the active codebase clean while preserving knowledge.

---

**Archive is read-only. Do not import from here.**
