# Refactoring Roadmap: Semantic Naming Implementation

## Overview

Transform the codebase incrementally so every function, class, and module uses relationship vocabulary.

This document shows exactly HOW to do it, with before/after examples from your actual code.

---

## Phase 1: Establish Foundation (Days 1-2)

### 1.1 Create Semantic Core Module

**Create:** `E:\AI-Setup\semantic_core\relationship_vocabulary.py`

```python
"""
Vocabulary module: Provides standardized terms for naming conventions.

This module ensures all code uses consistent relationship language from
the ontology. Import these constants to maintain consistency.
"""

from typing import Dict, List
from enum import Enum

# STRUCTURAL OPERATIONS
CONTAINS = "contains"
PART_OF = "part_of"
HAS_COMPONENT = "has_component"
MEMBER_OF = "member_of"

# DERIVATION OPERATIONS
DERIVES_FROM = "derives_from"
DERIVES_INTO = "derives_into"
GENERATES = "generates"
CREATES = "creates"
TRANSFORMS = "transforms_into"

# CAUSAL OPERATIONS
CAUSES = "causes"
CAUSED_BY = "caused_by"
TRIGGERS = "triggers"
PREVENTS = "prevents"
INFLUENCES = "influences"

# DEPENDENCY OPERATIONS
DEPENDS_ON = "depends_on"
REQUIRED_BY = "required_by"
SUPPORTS = "supports"

# TEMPORAL OPERATIONS
PRECEDES = "precedes"
FOLLOWED_BY = "followed_by"
OCCURS_DURING = "occurs_during"

# SEMANTIC OPERATIONS
EQUIVALENT_TO = "equivalent_to"
REFERENCES = "references"
DOCUMENTS = "documents"
RELATES_TO = "relates_to"

# VERSIONING OPERATIONS
REPLACES = "replaces"
VERSION_OF = "version_of"

# AGENT OPERATIONS
CREATED_BY = "created_by"
AUTHORED_BY = "authored_by"
PERFORMED_BY = "performed_by"

# LOCATION OPERATIONS
LOCATED_IN = "located_in"
HAS_LOCATION = "has_location"

class RelationshipOperation(Enum):
    """Standardized operations named after relationship types"""
    
    # Structural
    ADD_TO = "add_X_to_Y"           # add_component_to_system
    REMOVE_FROM = "remove_X_from_Y" # remove_from_cache
    LOCATE_IN = "locate_in"          # locate_in_redis
    
    # Derivation
    DERIVE = "derive_X_from_Y"       # derive_context_from_sources
    EXTRACT = "extract_X_from_Y"     # extract_learning_from_outcome
    GENERATE = "generate_X_from_Y"   # generate_signal_from_event
    
    # Causal
    CAUSE = "cause_X"                # cause_recomputation
    TRIGGER = "trigger_X"            # trigger_update
    PREVENT = "prevent_X"            # prevent_state_loss
    
    # Dependency
    REQUIRE = "require_X"             # require_redis_connection
    DEPEND = "depend_on_X"           # depend_on_context
    SUPPORT = "support_X"            # support_operation
    
    # Temporal
    PRECEDE = "precede_with_X"       # precede_with_initialization
    FOLLOW = "follow_X"              # follow_completion
    
    # Versioning
    CREATE_VERSION = "create_version_of_X"
    MARK_REPLACES = "mark_X_replaces_Y"
    
    # Semantic
    ESTABLISH_EQUIVALENCE = "establish_equivalence_with_X"
    REFERENCE = "reference_X"
    DOCUMENT = "document_with_X"

# Usage example:
# Instead of: def load_data()
# Use: def derive_context_from_redis()  [following DERIVE pattern]
```

### 1.2 Document Current State

Map existing code to ontology:

```python
# existing_mappings.py - Document what currently exists

CURRENT_TO_SEMANTIC_MAPPING = {
    # File: coordinator_api.py
    "coordinator_api.CoordinatorAPI.emit_signal": {
        "current_name": "emit_signal",
        "semantic_name": "emit_signal_causing_state_change",
        "relationship": "causes",
        "priority": "HIGH"
    },
    
    "coordinator_api.CoordinatorAPI.decision": {
        "current_name": "decision",
        "semantic_name": "record_decision_referenced_by_agents",
        "relationship": "references",
        "priority": "HIGH"
    },
    
    # File: agent_init.py
    "agent_init.initialize_and_load_context": {
        "current_name": "initialize_and_load_context",
        "semantic_name": "derive_agent_context_from_startup_sources",
        "relationship": "derives_from",
        "priority": "MEDIUM"
    },
    
    # File: session_state.py
    "session_state.SessionState.save_checkpoint": {
        "current_name": "save_checkpoint",
        "semantic_name": "create_version_replacing_previous_state",
        "relationship": "version_of/replaces",
        "priority": "MEDIUM"
    }
}
```

---

## Phase 2: Refactor Core API (Days 3-5)

### 2.1 Refactor coordinator_api.py

**BEFORE:**
```python
# E:\AI-Setup\coordinator_api.py (current)
class CoordinatorAPI:
    def emit_signal(self, signal_type, data):
        pass
    
    def decision(self, decision_name, outcome, reason):
        pass
    
    def learning(self, experiment_name, what_tried, ...):
        pass
    
    def get_startup_decisions(self):
        pass
    
    def get_startup_learnings(self):
        pass
```

**AFTER:**
```python
# E:\AI-Setup\semantic_core\signal_emitter.py (new)
from semantic_core.relationship_vocabulary import CAUSES, CREATES

class SignalEmitter:
    """
    Emits signals that cause effects in the system.
    
    Relationship: SignalEmitter causes Effects
    Operates in: Redis and File storage (dual-write)
    """
    
    def emit_signal_causing_state_change(
        self,
        signal_type: str,
        data: Dict,
        caused_by_agent: str = None
    ) -> Signal:
        """
        Emit signal that causes state change.
        
        Relationships:
        - Signal causes: Agent reactions, Context updates, Dependent operations
        - Signal created_by: Agent or System event
        - Signal located_in: Redis (primary), Files (redundancy)
        
        Args:
            signal_type: Type of signal (DECISION, BLOCKER, etc.)
            data: Signal data
            caused_by_agent: Which agent caused this signal
        
        Returns:
            Signal object with metadata
        """
        signal = Signal(
            type=signal_type,
            data=data,
            created_by=caused_by_agent,
            timestamp=datetime.now()
        )
        
        # Dual-write: locate_in both systems
        self.redis_backend.store_signal(signal)
        self.file_backend.store_signal(signal)
        
        return signal


class DecisionRecorder:
    """Records decisions that are referenced by future agents"""
    
    def record_decision_referenced_by_future_agents(
        self,
        decision_name: str,
        outcome: str,
        reason: str,
        confidence: str = "medium",
        reversible: bool = True
    ) -> Decision:
        """
        Record a decision for future agents to reference.
        
        Relationships:
        - Decision references: Domain, approach, architecture
        - Decision created_by: Current agent
        - Decision referenced_by: Future agents (cache)
        - Decision based_on: Reasoning provided
        
        This decision eliminates rework: future agents don't re-decide.
        """
        decision = Decision(
            name=decision_name,
            outcome=outcome,
            reason=reason,
            confidence=confidence,
            reversible=reversible,
            created_by=self.agent_id,
            created_at=datetime.now()
        )
        
        self.decision_cache.store(decision)
        return decision


class LearningDeriver:
    """Derives learnings from experiments and outcomes"""
    
    def derive_learning_from_experiment(
        self,
        experiment_name: str,
        what_tried: str,
        expected_outcome: str,
        actual_outcome: str,
        category: str,
        success: bool,
        recommendation: str = None
    ) -> Learning:
        """
        Derive a learning from an experiment.
        
        Relationships:
        - Learning derives_from: Experiment outcome
        - Learning created_by: Current agent
        - Learning documented_with: Rationale and evidence
        - Learning supports: Future agent decisions
        
        This learning prevents rework: "we tried X and got Y"
        """
        learning = Learning(
            experiment=experiment_name,
            tried=what_tried,
            expected=expected_outcome,
            actual=actual_outcome,
            category=category,
            success=success,
            recommendation=recommendation,
            derived_from_experiment=experiment_name,
            created_by=self.agent_id,
            created_at=datetime.now()
        )
        
        self.learning_store.save(learning)
        return learning


class StartupContextBuilder:
    """Builds agent startup context from cached sources"""
    
    def load_decisions_referenced_by_agent(
        self,
        agent_id: str,
        task_keyword: str = None
    ) -> List[Decision]:
        """
        Load decisions that this agent can reference.
        
        Relationships:
        - Decisions referenced_by: Current agent
        - Decisions created_by: Previous agents
        - Decisions relate_to: Task domain
        """
        decisions = self.decision_cache.load_by_agent(
            agent_id=agent_id,
            keyword=task_keyword
        )
        
        return decisions
    
    def load_learnings_applicable_to_agent(
        self,
        agent_id: str,
        task_keyword: str = None
    ) -> List[Learning]:
        """
        Load learnings that apply to this agent's task.
        
        Relationships:
        - Learnings referenced_by: Current agent
        - Learnings created_by: Previous agents
        - Learnings relate_to: Task domain
        """
        learnings = self.learning_store.load_by_domain(
            agent_id=agent_id,
            keyword=task_keyword
        )
        
        return learnings
```

### 2.2 Update function signatures

**Coordinator API refactored:**
```python
# Updated coordinator_api.py
class CoordinatorAPI:
    """Main coordination API"""
    
    def __init__(self):
        self.signal_emitter = SignalEmitter()
        self.decision_recorder = DecisionRecorder()
        self.learning_deriver = LearningDeriver()
        self.context_builder = StartupContextBuilder()
    
    # Delegate to semantic components
    def emit_signal_causing_change(self, signal_type, data):
        return self.signal_emitter.emit_signal_causing_state_change(
            signal_type, data
        )
    
    def record_decision_for_future_reference(self, name, outcome, reason):
        return self.decision_recorder.record_decision_referenced_by_future_agents(
            name, outcome, reason
        )
    
    def derive_learning_from_outcome(self, experiment, tried, expected, actual):
        return self.learning_deriver.derive_learning_from_experiment(
            experiment, tried, expected, actual
        )
```

---

## Phase 3: Refactor Storage & Derivation (Days 6-10)

### 3.1 Create Context Deriver

```python
# E:\AI-Setup\semantic_core\context_deriver.py

class ContextDeriver:
    """Derives context from authoritative sources"""
    
    def derive_context_from_redis_primary_source(
        self,
        agent_id: str
    ) -> Context:
        """
        Derive context from Redis (primary authoritative source).
        
        Reads what:
        - Redis_source derives_from: Real-time system state
        - Redis_contains: Sessions, signals, decisions, learnings
        
        Returns context that is_derived_from Redis
        """
        context = Context()
        context.decisions = self.redis.load_cached_decisions()
        context.learnings = self.redis.load_cached_learnings()
        context.briefing = self.redis.load_agent_briefing(agent_id)
        return context
    
    def derive_context_from_file_fallback_source(
        self,
        agent_id: str
    ) -> Context:
        """
        Derive context from files (fallback source).
        
        Reads what:
        - Files_source derives_from: Canonical session logs
        - Files_contain: Complete audit trail
        
        Returns context that is_derived_from Files
        """
        context = Context()
        context.decisions = self.files.load_decisions()
        context.learnings = self.files.load_learnings()
        context.briefing = self.files.load_briefing(agent_id)
        return context
    
    def derive_context_with_automatic_source_selection(
        self,
        agent_id: str
    ) -> Context:
        """
        Derive context, automatically selecting best source.
        
        Logic:
        - Try: Redis (derives_from Redis) - fast
        - Fallback: Files (derives_from Files) - reliable
        
        Returns context from whichever source is available
        """
        try:
            return self.derive_context_from_redis_primary_source(agent_id)
        except Exception as redis_error:
            logger.warning(f"Redis source failed: {redis_error}")
            return self.derive_context_from_file_fallback_source(agent_id)
```

### 3.2 Create State Reconciler

```python
# E:\AI-Setup\semantic_core\state_reconciler.py

class StateReconciler:
    """Reconciles versions of state to establish consistency"""
    
    def reconcile_state_versions_from_redis_and_file(
        self,
        redis_state: Dict,
        file_state: Dict
    ) -> Dict:
        """
        Reconcile two versions of state.
        
        Relationships:
        - redis_state version_of: Logical state
        - file_state version_of: Logical state
        - Result replaces: Both previous versions
        - Result establishes_equivalence: Consistent state
        
        Logic: Merge both to create canonical version
        """
        canonical = self._merge_versions(redis_state, file_state)
        
        # Mark which version replaces which
        canonical["replaces"] = {
            "redis_version": redis_state.get("version_id"),
            "file_version": file_state.get("version_id")
        }
        
        return canonical
    
    def verify_redis_and_file_state_equivalent(
        self,
        redis_state: Dict,
        file_state: Dict
    ) -> bool:
        """
        Verify two versions establish equivalence.
        
        Checks: Do redis_state and file_state represent the same state?
        Returns: bool - True if equivalent_to
        """
        return self._hash_state(redis_state) == self._hash_state(file_state)
```

---

## Phase 4: Refactor Session Management (Days 11-15)

### 4.1 Version and Checkpoint Management

**BEFORE:**
```python
# Current: session_state.py
def save_checkpoint(self, task, progress):
    pass

def load_checkpoint(self):
    pass
```

**AFTER:**
```python
# E:\AI-Setup\semantic_core\version_tracker.py

class VersionTracker:
    """Tracks versions and replacements"""
    
    def create_checkpoint_version_of_current_state(
        self,
        task: str,
        progress: int,
        blockers: List[str] = None
    ) -> Checkpoint:
        """
        Create a new version of current state as checkpoint.
        
        Relationships:
        - Checkpoint version_of: Current state
        - Checkpoint created_by: Agent
        - Checkpoint replaces: Previous checkpoint
        - Checkpoint enables: Crash recovery
        """
        previous = self.load_latest_checkpoint()
        
        checkpoint = Checkpoint(
            version_number=len(self.history) + 1,
            task=task,
            progress=progress,
            blockers=blockers,
            created_at=datetime.now(),
            replaces=previous.id if previous else None
        )
        
        self.store_checkpoint(checkpoint)
        return checkpoint
    
    def load_checkpoint_created_after_crash(
        self
    ) -> Optional[Checkpoint]:
        """
        Load the latest checkpoint (for recovery after crash).
        
        Relationships:
        - Checkpoint creates_recovery_point
        - Checkpoint enables_state_restoration
        """
        return self.load_latest_checkpoint()
    
    def mark_old_checkpoint_replaced_by_new(
        self,
        old_checkpoint: Checkpoint,
        new_checkpoint: Checkpoint
    ):
        """
        Mark: old_checkpoint replaced_by new_checkpoint
        
        Enables version tracking and history.
        """
        old_checkpoint.replaced_by = new_checkpoint.id
        self.store_checkpoint(old_checkpoint)
```

---

## Phase 5: Refactor Entire Codebase Systematically

### 5.1 Create Refactoring Template

For each file, follow this pattern:

```python
# TEMPLATE: How to refactor any file

# STEP 1: Identify current functions/classes
# List what currently exists

# STEP 2: Map to semantic names
# Use the mapping document

# STEP 3: Create semantic module
# Create new file in semantic_core/ or appropriate subdir

# STEP 4: Implement with explicit relationships
# Docstrings describe relationships explicitly

# STEP 5: Update original file
# Either:
# - Delete and replace with new semantic module
# - Make original delegate to new semantic classes

# STEP 6: Update all call sites
# Change calls to use new names

# STEP 7: Test & verify
# Ensure behavior unchanged, only names changed
```

### 5.2 Priority-Ordered Refactoring List

```
PRIORITY 1 (Critical path - Days 3-10):
- [ ] coordinator_api.py → SignalEmitter, DecisionRecorder, LearningDeriver
- [ ] agent_init.py → ContextDeriver
- [ ] session_state.py → VersionTracker
- [ ] redis_sync_coordinator.py → StateReconciler

PRIORITY 2 (Core features - Days 11-20):
- [ ] learning_store.py → LearningDeriver (expanded)
- [ ] session_recovery.py → CrashRecoveryManager
- [ ] startup_diagnostics.py → DiagnosticsEngine
- [ ] coordinator_service.py → CoordinationService

PRIORITY 3 (Support systems - Days 21-30):
- [ ] project_context.py → ProjectContextManager (refactor method names)
- [ ] session_logger.py → SessionRecorder
- [ ] fast_cache.py → CacheManager
- [ ] config.py → ConfigurationManager

PRIORITY 4 (Optional/nice-to-have):
- [ ] All test files
- [ ] Utility functions
- [ ] Helper modules
```

---

## Phase 6: Update All Documentation

### 6.1 Docstring Template

Every function should follow this pattern:

```python
def your_function_name(self, param1: Type1, param2: Type2) -> ReturnType:
    """
    One-line description using relationship language.
    
    Full description explaining what it does using relationship terminology.
    
    Relationships (What this function establishes):
    - Subject creates: [what it creates]
    - Subject derives_from: [what it reads/uses]
    - Subject causes: [what effects it has]
    - Subject located_in: [where data goes]
    - Subject replaces: [what it supersedes]
    - Subject requires: [what it depends on]
    
    Args:
        param1: Description in domain language
        param2: Description in domain language
    
    Returns:
        Description of return value with relationship context
    
    Example:
        # Relationship: function_name creates X that derives_from Y
        result = function_name(input_data)
    """
```

Example usage:

```python
def emit_signal_causing_state_change(
    self,
    signal_type: str,
    data: Dict,
    caused_by_agent: str = None
) -> Signal:
    """
    Emit a signal that causes system state changes.
    
    Creates a signal in the system that causes reactions in dependent 
    components. Signal is created_by the specified agent and located_in
    both Redis (primary) and Files (backup).
    
    Relationships:
    - Signal creates: State change events, agent reactions
    - Signal derives_from: Agent action or system event
    - Signal caused_by: Specified agent (or system if None)
    - Signal located_in: Redis (primary), Files (redundant)
    - Signal triggers: All dependent operations
    
    Args:
        signal_type: Type of signal (DECISION, BLOCKER, HANDOFF, etc.)
        data: Signal payload as dictionary
        caused_by_agent: Agent ID that caused this signal (optional)
    
    Returns:
        Signal object with metadata, version info, and storage locations
    
    Example:
        # Relationship: SignalEmitter creates Signal that causes Change
        signal = emitter.emit_signal_causing_state_change(
            signal_type="DECISION",
            data={"decision": "use_semantic_naming"},
            caused_by_agent="claude-code-agent"
        )
    """
```

---

## Complete Example: Refactoring agent_init.py

### Before (Current Code)

```python
def initialize_and_load_context(
    agent_id: str,
    task_keyword: Optional[str] = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    verbose: bool = True
) -> Dict[str, Any]:
    """Initialize an agent with full startup context loading."""
    # ... implementation
```

### After (Semantic Naming)

```python
# E:\AI-Setup\semantic_core\agent_initialization.py

class AgentInitializer:
    """
    Initializes agents by deriving context from startup sources.
    
    Relationship: Initializer derives_from Redis/Files to create Context
    """
    
    def initialize_agent_with_context_derived_from_startup_sources(
        self,
        agent_id: str,
        task_keyword: Optional[str] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Initialize agent by deriving context from startup sources.
        
        Complete initialization for an agent, including:
        - Deriving context from Redis and file sources
        - Loading decisions that this agent can reference
        - Loading learnings from previous agents
        - Checking for crash checkpoints to recover from
        
        Relationships:
        - Context derives_from: Redis (primary), Files (fallback)
        - Agent references: Cached decisions (previous agents)
        - Agent learns_from: Cached learnings (previous experiments)
        - Agent recovers_from: Latest checkpoint (if exists)
        - Agent located_in: Specified Redis/file backends
        
        Args:
            agent_id: Unique identifier for this agent
            task_keyword: Filter decisions/learnings by task domain
            redis_host: Redis host
            redis_port: Redis port (default: 16379 for Docker)
            verbose: Print diagnostic report
        
        Returns:
            Dictionary containing:
            - api: CoordinatorAPI instance (for creating signals)
            - context: Full startup context (decisions, learnings, briefing)
            - state: SessionState instance (for checkpointing)
            - diagnostics: Startup diagnostics report
            - status: "success", "partial", or "failed"
        
        Example:
            result = initializer.initialize_agent_with_context_derived_from_startup_sources(
                agent_id="my_agent",
                task_keyword="implementation"
            )
            api = result["api"]
            context = result["context"]  # Contains referenced decisions, learnings
        """
        # Implementation follows semantic naming
        context_deriver = ContextDeriver(redis_host, redis_port)
        context = context_deriver.derive_context_with_automatic_source_selection(agent_id)
        
        api = SignalEmitter()  # Can emit signals
        state = SessionState()  # Can save checkpoints
        
        if verbose:
            diagnostics = self._create_startup_diagnostics(agent_id)
        
        return {
            "api": api,
            "context": context,
            "state": state,
            "diagnostics": diagnostics,
            "status": "success"
        }
```

---

## Testing the Refactoring

### Test Template

```python
# test_semantic_naming.py

def test_signal_emitter_causes_state_change():
    """Verify: SignalEmitter causes State changes"""
    emitter = SignalEmitter()
    signal = emitter.emit_signal_causing_state_change(
        "DECISION",
        {"choice": "test"}
    )
    
    # Verify: Signal was created
    assert signal is not None
    
    # Verify: Signal located_in Redis and Files
    assert redis_backend.has_signal(signal.id)
    assert file_backend.has_signal(signal.id)
    
    # Verify: Signal causes state change (can be referenced)
    retrieved = redis_backend.retrieve_signal(signal.id)
    assert retrieved == signal

def test_context_derives_from_redis():
    """Verify: Context derives_from Redis"""
    deriver = ContextDeriver()
    context = deriver.derive_context_from_redis_primary_source("agent_1")
    
    # Verify: Context contains decisions (derived from Redis)
    assert context.decisions is not None
    
    # Verify: Context contains learnings (derived from Redis)
    assert context.learnings is not None

def test_context_derives_from_files_when_redis_unavailable():
    """Verify: Context derives_from Files when Redis unavailable"""
    deriver = ContextDeriver()
    # Mock Redis failure
    redis_backend.make_unavailable()
    
    context = deriver.derive_context_with_automatic_source_selection("agent_1")
    
    # Verify: Context still loaded (from Files)
    assert context is not None
    assert context.source == "file"
```

---

## Success Criteria

✅ All function names use relationship verbs  
✅ Class names describe their semantic role  
✅ Method signatures are self-documenting  
✅ Docstrings explicitly state relationships  
✅ New developers can guess function names  
✅ Code organization mirrors ontology structure  
✅ All tests pass with new names  
✅ No behavioral changes, only naming  

---

## Timeline

```
Week 1 (Days 1-5):
  - Create semantic_core modules
  - Refactor coordinator API
  - Update all call sites
  - Test thoroughly

Week 2 (Days 6-10):
  - Refactor storage/derivation
  - Update session management
  - Create version tracker
  - Integration test

Week 3 (Days 11-15):
  - Refactor remaining core
  - Update all docstrings
  - Performance testing
  - Documentation

Week 4 (Days 16-20):
  - Test files and utilities
  - Create developer guide
  - Knowledge transfer
  - Final validation

After (Ongoing):
  - Maintain consistency
  - Update as needed
  - Document new patterns
```

---

## Result

**After this refactoring:**

A new developer can:
1. Learn the 66 relationship types (2-3 hours)
2. Understand your entire codebase structure (1-2 hours)
3. Navigate and modify code intuitively (from day 1)

The codebase becomes self-documenting, self-organizing, and infinitely more maintainable.
