# Consolidation with Semantic Alignment

**Insight**: The relationship types, semantic naming, and learning system should all speak the same language. When we consolidate, we align them so patterns are instantly recognizable.

---

## The Alignment

### What We Have
1. **66 Relationship Types** (relationship_types.py)
   - Structural: part_of, has_part, component_of, etc.
   - Hierarchical: is_a, derives_from, depends_on
   - Causal: causes, prevents, enables
   - Temporal: precedes, follows, during
   - Semantic: related_to, equivalent_to
   - etc.

2. **5 Semantic Naming Patterns** (from learnings)
   - `load_X_from_Y()` → Uses `derives_from` relationship
   - `cache_X_for_Y()` → Uses `purpose_for` relationship
   - `record_X_preventing_Y()` → Uses `prevents` relationship
   - `emit_X_causing_Y()` → Uses `causes` relationship
   - `derive_X_from_Y()` → Uses `derives_from` relationship

3. **Learning System** (learning_store.py)
   - Records experiments with patterns discovered
   - Includes recommendations for code changes
   - BUT: Not yet aware that these patterns ARE relationship types

### The Gap
When we record a learning like:
```
experiment: "semantic_naming_pattern_discovery"
recommendation: "Use these 5 patterns for all future method naming"
patterns_discovered: {
  "load_pattern": "load_X_from_Y()",
  "derive_pattern": "derive_X_from_Y()",
  ...
}
```

The learning system doesn't know that these patterns correspond to relationship types in the code. So when we try to apply the learning later, we have to rediscover the connection.

---

## The Solution: Semantic-Aware Organization

When we consolidate, we organize systems using relationship types as the organizing principle:

### Package Structure (Relationship-Aligned)

```
core/
├── foundation/                          # Base primitives (no deps)
│   ├── relationship_types.py            # The vocabulary
│   └── types.py                         # Canonical types
│
├── signals/                             # What agents EMIT
│   ├── __init__.py
│   ├── coordinator_api.py
│   │   └── emit_signal_to_storage()     # Uses: causes → storage
│   │   └── derive_context_from_sources()# Uses: derives_from
│   │
│   └── coordinator_service.py
│       └── process_signal_causing_state_change()  # Uses: causes
│
├── state/                               # What persists
│   ├── __init__.py
│   ├── session_state.py
│   │   └── load_checkpoint_from_storage()    # Uses: derives_from
│   │   └── cache_state_for_recovery()        # Uses: purpose_for
│   │
│   ├── session_recovery.py
│   │   └── resume_from_checkpoint_preventing_loss()  # Uses: prevents
│   │
│   └── redis_sync_coordinator.py
│       └── sync_state_reconciling_divergence() # Uses: reconciles
│
└── learning/                            # What we know
    ├── __init__.py
    └── learning_store.py
        ├── record_learning_derived_from_experiment()    # Uses: derives_from
        ├── discover_pattern_from_learnings()            # Uses: derives_from
        └── get_recommendations_for_task()               # Uses: applicable_to
```

**Key**: Every function uses semantic naming that references relationship types!

---

## Function Naming Guide (Relationship-Aware)

When writing functions, use this pattern:

```python
# STRUCTURAL relationships
def load_X_from_Y():           # X derives_from Y
def cache_X_for_Y():           # X stored for purpose Y
def record_X_preventing_Y():   # X prevents Y

# CAUSAL relationships
def emit_X_causing_Y():        # X causes Y
def process_X_triggering_Y():  # X triggers Y
def signal_X_enabling_Y():     # X enables Y

# HIERARCHICAL relationships
def get_X_from_Y():            # Get X that part_of Y
def discover_pattern_in_X():   # Find pattern in X
def summarize_X_from_Y():      # Summarize X derived from Y

# TEMPORAL relationships
def X_preceding_Y():           # X happens before Y
def X_following_Y():           # X happens after Y

# SEMANTIC relationships
def X_related_to_Y():          # X semantically related to Y
def X_equivalent_to_Y():       # X same meaning as Y
```

---

## Learning System Enhancement

Update `learning_store.py` to track relationship types:

```python
class EnhancedLearning(Learning):
    """Learning that knows about relationship types"""
    
    relationship_types_used: List[str]  # e.g., ["derives_from", "causes"]
    code_patterns: Dict[str, str]       # Pattern name → relationship type
    semantic_domain: str                # structural, causal, hierarchical, etc.
    
    def to_pattern_recommendation(self):
        """Convert learning into pattern that uses relationship types"""
        return {
            "pattern_name": self.pattern_name,
            "relationship_type": self.get_primary_relationship(),
            "function_template": f"{action}_{subject}_{relationship}_{object}()",
            "examples": self.generate_examples_using_relationships(),
        }
```

**Then when querying:**
```python
store.get_learnings_for_relationship_type("derives_from")
store.get_patterns_using_relationships(["causes", "prevents"])
store.recommend_function_names_for_task("load contexts")
```

---

## Revised Consolidation Steps

### Step 0: Foundation (NEW)
```
[ ] Keep relationship_types.py at root (fundamental vocabulary)
[ ] Create core/foundation/ package
[ ] Move relationship_types.py → core/foundation/
[ ] Create types.py in core/foundation/ (canonical types)
    └── This is the shared vocabulary all systems reference
```

### Step 1-8: Same as Before
(Archive, consolidate docs, move files)

### Step 9: Semantic-Aware Naming (NEW)
```
[ ] Review all function names in core/ systems
[ ] Rename functions to use relationship types
[ ] Examples:
    - initialize() → derive_agent_from_startup_sources()
    - load_context() → load_context_from_session_history()
    - save_checkpoint() → cache_state_for_recovery()
    - process_signal() → emit_state_change_caused_by_signal()
[ ] Update docstrings to reference relationship types
```

### Step 10: Enhance Learning System (NEW)
```
[ ] Update learning_store.py to track relationship types used
[ ] Add method: get_patterns_using_relationship_type()
[ ] Add method: recommend_function_name_using_relationships()
[ ] When recording learnings, extract relationship types from patterns
[ ] When querying learnings, can filter by relationship type
```

### Step 11: Documentation Alignment (NEW)
```
[ ] Update SEMANTIC_NAMING_CONVENTION.md to show relationship type mapping
[ ] Create RELATIONSHIP_TYPES_IN_CODE.md
    ├── Shows which relationship types appear in which systems
    ├── Shows naming pattern for each type
    ├── Links to actual code examples
[ ] Create LEARNING_TO_CODE_MAPPING.md
    ├── Shows how learnings translate to code patterns
    ├── Shows which relationship types are most valuable
    └── Shows how to apply a learning using semantic naming
```

---

## Why This Matters

**Before Alignment:**
- Learn: "Use load_X_from_Y pattern"
- Apply: Search codebase for where to use it
- Problem: Don't know which files need it, unclear pattern

**After Alignment:**
- Learn: "Use load_X_from_Y pattern (derives_from relationship)"
- Apply: Get all functions using `derives_from`, apply pattern
- Result: Clear, searchable, instantly recognizable

**In Code:**
```python
# ALIGNED - Knows what it does
def load_context_from_session_history():
    """Semantic Relationship: context derives_from session_history"""
    # Instantly recognizable to anyone who knows relationship types

# GENERIC - Unclear
def get_context():
    """Get the context"""
    # What context? From where? Why this way?
```

---

## Enhanced Consolidation Checklist

### Basic Consolidation (Steps 1-8)
```
[ ] Archive old code (50+ files)
[ ] Archive old docs (83 files)
[ ] Create package structure
[ ] Move core files to packages
[ ] Update imports
[ ] Test everything works
```

### Semantic Alignment (Steps 9-11)
```
[ ] Foundation layer: Keep relationship_types.py as vocabulary
[ ] Rename functions to use relationship types
    [ ] core/signals/ functions
    [ ] core/state/ functions
    [ ] core/learning/ functions
    [ ] New systems when built: context/, infrastructure/, agent/
    
[ ] Update learning_store.py to track relationship types
    [ ] Track which relationships each pattern uses
    [ ] Enable querying by relationship type
    
[ ] Create mapping documentation
    [ ] RELATIONSHIP_TYPES_IN_CODE.md
    [ ] LEARNING_TO_CODE_MAPPING.md
    [ ] Update SEMANTIC_NAMING_CONVENTION.md
```

---

## Time Estimate (Revised)

| Phase | Task | Time |
|-------|------|------|
| **Consolidation** | Steps 1-8 (basic) | 2h |
| **Semantics** | Step 0 (foundation) | 15 min |
| **Semantics** | Step 9 (rename functions) | 45 min |
| **Semantics** | Step 10 (enhance learning) | 30 min |
| **Documentation** | Step 11 (create mappings) | 30 min |
| **Testing** | Full integration test | 30 min |
| **TOTAL** | | **5 hours** |

**Result**: Foundation that speaks ONE unified language (relationship types) across:
- Code structure
- Function naming
- Learning system
- Documentation

---

## Success Criteria (Enhanced)

✅ **Code Organization**
- Systems in packages
- ALL function names use semantic pattern
- Every function references a relationship type

✅ **Learning System Integration**
- Learnings track which relationship types they use
- Can query learnings by relationship type
- Can recommend patterns by relationship type

✅ **Documentation Clarity**
- Know exactly which relationship types are used where
- Can apply a learning by following relationship type
- Patterns are instantly recognizable

✅ **Pattern Recognition**
- New developer learns relationship types
- Can navigate code intuitively
- Can apply past learnings to new problems
- Code patterns are obvious

---

## Implementation Strategy

### Option A: Consolidate First, Then Add Semantics
1. Do basic consolidation (2h)
2. Then rename functions & enhance learning (2h)
3. Test everything (1h)
Total: 5h

### Option B: Consolidate With Semantics (Integrated)
1. During consolidation, rename to semantic names
2. During moving files, apply relationship type principles
3. During testing, verify semantic alignment
Total: 3h (faster because it's all at once)

**Recommendation**: **Option B (Integrated)**
- Less rework
- Better quality from start
- Alignment is automatic, not added later

---

## Ready?

Should I execute consolidated with semantic alignment (Option B)?

The flow:
1. Archive old code/docs
2. Create clean package structure
3. Move files AND rename to semantic names simultaneously
4. Enhance learning_store.py to track relationships
5. Test with aligned semantics
6. Result: Foundation where code, learnings, and documentation speak the same language

This prevents the pattern-discovery problem and makes future systems much easier to build.

