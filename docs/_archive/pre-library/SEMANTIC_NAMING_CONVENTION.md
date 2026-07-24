# Semantic Naming Convention: Unified Ontological Architecture

## Vision

Every function, class, method, and variable in the codebase uses the relationship type vocabulary. 
Understanding the 66 relationship types becomes understanding the entire system's organization.

**Benefit:** Someone who knows the relationship types can navigate and understand ANY part of the 
codebase intuitively, because the naming conventions are consistent across all layers.

---

## Naming Pattern: `{Subject}_{RelationType}_{Object}`

All functions follow a consistent structure:

```
{Subject}_{RelationType}_{Object}([parameters])
          └─ from relationship_types.py
```

### Examples

```python
# STRUCTURAL RELATIONSHIPS
redis_contains_sessions()           # redis has_part sessions
session_derives_from_handoff()      # what a session derives from
coordinator_emits_signal_to_redis() # coordinator causes signal in redis
agent_depends_on_context()          # agent requires context

# HIERARCHICAL RELATIONSHIPS
task_is_a_work_unit()              # task classified as
component_instance_of_module()     # component is instance of module

# TEMPORAL RELATIONSHIPS
signal_precedes_completion()        # signal happens before completion
phase_follows_initialization()      # phase occurs after initialization

# SEMANTIC RELATIONSHIPS
decision_equivalent_to_policy()     # decisions are equivalent to policies
error_related_to_sync()             # error connection to sync issue

# AGENT RELATIONSHIPS
system_authored_by_agent()          # system created by agent
algorithm_created_by_research()     # algorithm is output of research
```

---

## Layer-by-Layer Application

### 1. MODULE NAMING (Ontology-Aligned)

**Current:**
```
├── coordinator_api.py
├── coordinator_service.py
├── session_logger.py
├── learning_store.py
├── sync_integration.py
```

**Ontology-Aligned:**
```
├── coordinator_api.py              # Main API that creates/emits signals
├── signal_emitter.py               # What causes signals to be emitted
├── context_derives_from_sources.py # Context derivation logic
├── component_registry.py           # What components participate in system
├── learning_derives_from_outcomes.py # Learning generation
├── sync_reconciles_state.py        # Sync that makes state consistent
├── dependency_resolver.py          # What depends on what
├── transformation_engine.py        # What causes transformations
```

**Better naming communicates:**
- What the module does (using relationship verbs)
- How it relates to other modules
- What its inputs/outputs are

---

### 2. CLASS NAMING (Semantic Role)

```python
# CURRENT APPROACH
class CoordinatorAPI:
    def emit_signal(self):
        pass

class SessionState:
    def load_checkpoint(self):
        pass


# ONTOLOGY-ALIGNED APPROACH
class SignalEmitter:
    """Creates signals that cause effects in the system"""
    def emit_signal_to_redis(self) -> Signal:
        """SignalEmitter emits_signal_to Redis"""
        pass

class ContextDeriver:
    """Derives context from multiple sources"""
    def derive_context_from_redis(self) -> Context:
        """Context derives_from Redis"""
        pass
    
    def derive_context_from_files(self) -> Context:
        """Context derives_from Files"""
        pass

class DependencyResolver:
    """Tracks what depends_on what"""
    def add_dependency(self, dependent, dependency):
        """Add: dependent depends_on dependency"""
        pass
    
    def resolve_dependencies(self, component):
        """Find all components this component depends_on"""
        pass

class ComponentRegistry:
    """Registry of system components and their relationships"""
    def register_component_as_part_of(self, component, parent):
        """component is part_of parent"""
        pass
    
    def get_components_part_of(self, parent):
        """Get all components that are part_of parent"""
        pass

class CausalEngine:
    """Tracks cause-effect relationships"""
    def add_causality(self, cause, effect):
        """cause causes effect"""
        pass
    
    def find_causes_of(self, effect):
        """What causes this effect?"""
        pass

class StateReconciler:
    """Ensures file and Redis states are synchronized"""
    def reconcile_state_from_redis(self, file_state, redis_state):
        """Make states equivalent"""
        pass

class LearningDeriver:
    """Derives learnings from outcomes and experiments"""
    def derive_learning_from_experiment(self, experiment):
        """Learning derives_from Experiment"""
        pass

class VersionTracker:
    """Tracks versions and replacements"""
    def track_version_of(self, original):
        """Track: version is_version_of original"""
        pass
    
    def mark_replaced_by(self, old, new):
        """Mark: old replaced_by new"""
        pass
```

---

### 3. METHOD NAMING (Relationship Actions)

```python
class AgentContext:
    # STRUCTURAL: part-whole relationships
    def add_component_to_context(self, component):
        pass
    
    def remove_component_from_context(self, component):
        pass
    
    # HIERARCHICAL: classification
    def classify_as_task(self, item):
        pass
    
    def instance_of_phase(self, item) -> bool:
        pass
    
    # CAUSAL: cause-effect
    def cause_recomputation(self, reason):
        pass
    
    def prevent_state_loss(self):
        pass
    
    # TEMPORAL: time-based
    def precede_with_initialization(self):
        pass
    
    def follow_completion(self):
        pass
    
    # SEMANTIC: meaning
    def establish_equivalence_with(self, other_context):
        pass
    
    def reference_external_knowledge(self, source):
        pass
    
    # AGENT: creation/attribution
    def document_authored_by(self, agent_id):
        pass
    
    def attribute_to_agent(self, agent_id):
        pass
    
    # VERSIONING
    def create_version_of(self, original):
        pass
    
    def mark_replaced_by(self, new_version):
        pass
    
    # DEPENDENCY
    def depends_on(self, requirement):
        pass
    
    def required_by(self, dependent):
        pass
    
    def support_component(self, component):
        pass
```

---

### 4. VARIABLE NAMING (Semantic Types)

```python
# CURRENT: Generic names
context = get_context()
data = load_data()
state = get_state()
result = process()

# ONTOLOGY-ALIGNED: Semantic meaning explicit
context_derived_from_redis = load_context_from_redis()
context_derived_from_files = load_context_from_files()

state_components_part_of_system = system.get_components()
state_replacing_old_version = new_state

signal_causing_recomputation = emit_priority_signal()
signals_preceding_completion = get_prerequisite_signals()

learning_derived_from_experiment = extract_learning(experiment)
learnings_referenced_by_current_agent = load_cached_learnings()

version_replacing_previous = create_new_version()
dependencies_required_by_task = resolve_task_requirements()
```

---

### 5. PARAMETER NAMING (Explicit Relationships)

```python
# CURRENT: Vague parameters
def add_relationship(entity_a, entity_b, type):
    pass

def process(data, config, context):
    pass

# ONTOLOGY-ALIGNED: Explicit relationships
def establish_causality(causing_event, caused_event):
    """Establish: causing_event causes caused_event"""
    pass

def derive_context_from_sources(redis_source, file_source, agent_id):
    """Context derives_from multiple sources"""
    pass

def reconcile_versions(version_in_redis, version_in_file, resolution_strategy):
    """Which version replaces the other?"""
    pass

def resolve_dependencies(dependent_component, required_component):
    """dependent_component depends_on required_component"""
    pass

def document_decision_with_reference(decision, supporting_evidence_source):
    """Decision documents with reference_to evidence"""
    pass
```

---

### 6. FUNCTION SIGNATURES (Self-Documenting)

```python
# ANTI-PATTERN: Generic
def process_data(data):
    return transform(data)

# PATTERN: Semantically explicit
def derive_context_from_startup_sources(
    redis_source: Redis,
    file_source: Path,
    agent_id: str
) -> Context:
    """
    Context derives_from multiple sources.
    
    Reads from:
    - Redis (primary source) - part_of distributed state
    - Files (fallback source) - contains canonical log
    
    Returns context that is_derived_from both sources.
    """
    pass

def emit_signal_causing_recomputation(
    component: str,
    reason: str
) -> Signal:
    """
    Emit signal that causes recomputation.
    
    The emitted signal causes:
    - Cache invalidation
    - State refresh
    - Dependent component update
    """
    pass

def reconcile_state_versions(
    redis_version: Dict,
    file_version: Dict
) -> Dict:
    """
    Reconcile two versions of state.
    
    Establishes equivalence between versions.
    Returns canonical version that replaces both.
    """
    pass
```

---

### 7. FILE STRUCTURE (Ontologically Organized)

```
E:\AI-Setup\
├── semantic_core/
│   ├── relationship_types.py        # The ontology itself
│   ├── entity_registry.py           # What entities exist
│   └── relationship_graph.py        # Graph of relationships
│
├── structural/                       # part_of, has_part, contains
│   ├── component_registry.py
│   ├── system_composition.py
│   └── hierarchy_manager.py
│
├── derivation/                       # derives_from, derives_into
│   ├── context_deriver.py
│   ├── learning_deriver.py
│   ├── transformation_engine.py
│   └── signal_generator.py
│
├── causality/                        # causes, caused_by, influences
│   ├── causal_engine.py
│   ├── event_reactor.py
│   └── side_effect_tracker.py
│
├── dependency/                       # depends_on, requires
│   ├── dependency_resolver.py
│   ├── requirement_checker.py
│   └── circular_dependency_detector.py
│
├── versioning/                       # is_version_of, replaces
│   ├── version_tracker.py
│   ├── state_reconciler.py
│   └── migration_engine.py
│
├── temporal/                         # precedes, follows, occurs_during
│   ├── event_sequencer.py
│   ├── timeline_manager.py
│   └── phase_coordinator.py
│
├── agent_layer/                      # authored_by, created_by, performed_by
│   ├── agent_context_builder.py
│   ├── operation_tracker.py
│   └── attribution_system.py
│
├── storage/                          # located_in, contained_in
│   ├── redis_backend.py
│   ├── file_storage.py
│   └── storage_router.py
│
└── coordination/
    ├── coordinator_api.py            # Main coordination hub
    └── signal_router.py
```

---

## Implementation Strategy

### Phase 1: Establish Core Semantics (Week 1)
1. Create `semantic_core/` with relationship_types and entity_registry
2. Define what the main entities are (Agent, Context, Signal, etc.)
3. Map existing code to semantic equivalents
4. Document naming convention

### Phase 2: Refactor Critical Path (Week 2-3)
1. Start with `coordinator_api.py` (most central)
2. Rename classes, methods using ontology
3. Update docstrings with relationship language
4. Refactor signatures to be self-documenting

### Phase 3: Expand to All Layers (Week 4+)
1. Apply to storage layer, session management, learning
2. Create new modules with semantic organization
3. Gradually sunset old naming

### Phase 4: Documentation & Training (Ongoing)
1. Update all docstrings to use relationship language
2. Create examples of common patterns
3. Build developer quick-start guide

---

## Examples: Before & After

### Example 1: Signal Emission

**BEFORE:**
```python
class Coordinator:
    def emit(self, signal_type, data):
        self.redis.lpush(f"signal:{signal_type}", json.dumps(data))
        self.file.write(json.dumps(data))
```

**AFTER:**
```python
class SignalEmitter:
    """Emits signals that cause effects in the system"""
    
    def emit_signal_causing_action(
        self,
        signal_type: str,
        data: Dict
    ) -> Signal:
        """
        Emit signal that causes action in system.
        
        This signal:
        - causes: system state change
        - located_in: Redis (primary) and Files (redundancy)
        - created_by: requesting agent
        - triggers: dependent operations
        """
        signal = Signal(type=signal_type, data=data)
        self.redis_backend.store_signal(signal)
        self.file_backend.store_signal(signal)
        return signal
    
    def emit_signal_replacing_previous(
        self,
        new_signal: Signal,
        previous_signal: Signal
    ) -> Signal:
        """Mark: new_signal replaces previous_signal"""
        pass
```

### Example 2: Context Loading

**BEFORE:**
```python
def get_context():
    try:
        return redis.get("context")
    except:
        return load_from_file()
```

**AFTER:**
```python
class ContextDeriver:
    """Derives context from authoritative sources"""
    
    def derive_context_from_redis(self) -> Context:
        """
        Derive context from Redis.
        Context derives_from Redis (primary source).
        """
        return self.redis.load_context()
    
    def derive_context_from_files(self) -> Context:
        """
        Derive context from files.
        Context derives_from Files (fallback source).
        """
        return self.file_system.load_context()
    
    def derive_context_from_primary_source(self) -> Context:
        """
        Derive context with automatic failover.
        Tries Redis first (derives_from Redis).
        Falls back to Files (derives_from Files).
        """
        try:
            return self.derive_context_from_redis()
        except:
            return self.derive_context_from_files()
```

### Example 3: Dependency Management

**BEFORE:**
```python
class Requirements:
    def get_deps(self, task):
        return self.deps.get(task, [])
```

**AFTER:**
```python
class DependencyResolver:
    """Resolves what depends_on what"""
    
    def get_components_required_by(self, component: str) -> List[str]:
        """
        Get all components that component requires.
        component depends_on [results]
        """
        return self.graph.get_dependencies(component)
    
    def get_components_that_require(self, component: str) -> List[str]:
        """
        Get all components that require this component.
        [results] depend_on component
        """
        return self.graph.get_dependents(component)
    
    def verify_no_circular_dependencies(self) -> bool:
        """
        Verify the dependency graph has no cycles.
        Would create: A depends_on B depends_on A (invalid)
        """
        return self.graph.is_acyclic()
```

---

## Benefits of This Approach

### 1. **Self-Documenting Code**
Once you know the relationship types, function names tell you exactly what they do.

### 2. **Consistent Mental Model**
Everyone on the team uses the same vocabulary → fewer misunderstandings.

### 3. **Intuitive Navigation**
New team members can guess function names correctly because they follow patterns.

### 4. **Automatic Documentation**
Function names are so clear that additional documentation is often redundant.

### 5. **Refactoring Safety**
When renaming, you're following consistent rules, not making arbitrary decisions.

### 6. **Knowledge Transfer**
Teaching new developers: "Learn the 66 relationship types, then you understand the whole system."

### 7. **Cross-Layer Coherence**
Naming is consistent across API layer, storage layer, coordination layer, etc.

---

## Quick Reference: Relationship Words by Category

### Verbs for Methods (What the method does)

**Structural:**
- add_X_to_Y
- remove_X_from_Y
- get_components_part_of_X
- register_X_as_member_of_Y

**Hierarchical:**
- classify_as_X
- instance_of_X
- subclass_of_X

**Causal:**
- cause_X
- prevent_X
- trigger_X
- affect_X
- influence_X

**Derivation:**
- derive_X_from_Y
- extract_X_from_Y
- generate_X_from_Y
- transform_X_into_Y

**Temporal:**
- precede_with_X
- follow_X
- occur_during_X
- sequence_as_X

**Semantic:**
- establish_equivalence_with_X
- relate_to_X
- reference_X
- document_with_X

**Dependency:**
- depends_on_X
- required_by_X
- support_X

**Versioning:**
- create_version_of_X
- mark_replaced_by_X
- track_version_of_X

---

## Adoption Guidelines

1. **Start with function signatures:** Most immediately impactful
2. **Move to class names:** Creates structural coherence
3. **Then variable names:** Adds clarity to implementation
4. **Finally, module organization:** Completes the architecture

---

## Examples That Make It Intuitive

Once adopted, a new developer seeing this code understands it immediately:

```python
# INTUITIVE - relationship names are self-documenting
signal = signal_emitter.emit_signal_causing_recomputation(
    component="context_loader",
    reason="redis_state_changed"
)

learnings = learning_deriver.derive_learnings_from_experiment(
    experiment=test_result,
    agent_id=current_agent
)

dependencies = dependency_resolver.get_components_required_by(
    component="coordinator_api"
)

context = context_deriver.derive_context_from_primary_source()

version = version_tracker.create_version_replacing(
    old_version=previous_state,
    new_version=current_state
)
```

**Without semantic naming**, the developer would need to read 20 lines of comments to understand what's happening.  
**With semantic naming**, the code is self-explanatory.

---

## This Creates: Semantic Coherence

The entire codebase becomes an implementation of the ontology.  
The ontology is the blueprint.  
The code is the building.  
Understanding one = understanding the other.
