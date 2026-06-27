# Integration Guide: Relationship Types Framework

This guide shows how to integrate the new 66-relationship framework into your existing system.

## Step 1: Update project_context.py

### Before (Old String-Based)
```python
"relationships": [
    "redis_ha -> session_logger (stores session data)",
    "redis_ha -> mcp_server (exposes data)",
    "redis_ha -> sync_service (syncs logs)"
]
```

### After (Formal Relationship Types)
```python
from relationship_types import RelationshipType

"relationships": [
    {
        "from": "redis_ha",
        "to": "session_logger",
        "type": RelationshipType.SUPPORTS.value.short_name,  # "supports"
        "formal_type": RelationshipType.SUPPORTS.value.formal_name,  # "RDF"
        "inverse": "supported_by",
        "description": "Redis HA stores session data"
    },
    {
        "from": "redis_ha",
        "to": "mcp_server",
        "type": RelationshipType.SUPPORTS.value.short_name,
        "formal_type": RelationshipType.SUPPORTS.value.formal_name,
        "inverse": "supported_by",
        "description": "Redis HA provides data to MCP server"
    },
    {
        "from": "sync_service",
        "to": "redis_ha",
        "type": RelationshipType.SUPPORTS.value.short_name,
        "formal_type": RelationshipType.SUPPORTS.value.formal_name,
        "inverse": "supported_by",
        "description": "Sync service maintains Redis data consistency"
    }
]
```

---

## Step 2: Update coordinator_api.py or Similar

If you have methods that emit signals with relationships, update them:

### Before
```python
def emit_signal(self, signal_type, data):
    # No relationship type awareness
    self.redis.lpush(f"signal:{signal_type}", json.dumps(data))
```

### After
```python
from relationship_types import get_relationship_by_name, RelationshipType

def emit_signal_with_relationship(self, signal_type, data, relationship_name=None):
    if relationship_name:
        rel = get_relationship_by_name(relationship_name)
        if rel:
            data["relationship_type"] = rel.short_name
            data["relationship_formal"] = rel.formal_name
            data["relationship_domain"] = rel.domain
    
    self.redis.lpush(f"signal:{signal_type}", json.dumps(data))
```

---

## Step 3: Update Learning Storage

When recording learnings, include relationship context:

### Before
```python
learning = {
    "experiment_name": "sync_integration",
    "what_tried": "dual_write",
    "actual_outcome": "hashes_matched"
}
```

### After
```python
from relationship_types import RelationshipType

learning = {
    "experiment_name": "sync_integration",
    "what_tried": "dual_write",
    "actual_outcome": "hashes_matched",
    
    # NEW: relationship context
    "outcome_derived_from": {
        "source": "hash_mismatch_investigation",
        "relationship": RelationshipType.DERIVED_FROM.value.short_name,
        "description": "This learning is derived from investigation of hash mismatches"
    },
    
    "related_learnings": [
        {
            "learning_id": "redis_connection_port",
            "relationship": RelationshipType.RELATED_TO.value.short_name,
            "reason": "Both are about Redis integration"
        }
    ]
}
```

---

## Step 4: Update Session Context

When agents hand off context, use formal relationships:

### Before
```python
# In AGENT_ONBOARDING.md or HANDOFF signal
HANDOFF: implementation_agent
├─ Task: Build coordinator_api.py
├─ Context: Architecture approved
├─ Blockers: redis_connection_failing
└─ Learned: Signal-based logging reduces tokens
```

### After
```python
from relationship_types import RelationshipType

# In structured HANDOFF signal
signal = {
    "signal_type": "HANDOFF",
    "to_agent": "implementation_agent",
    "task": "Build coordinator_api.py",
    
    "context": {
        "approved": {
            "concept": "signal_based_logging",
            "relationship": RelationshipType.EQUIVALENT_TO.value.short_name,
            "equivalent_to": "async_coordination"
        }
    },
    
    "blockers": [
        {
            "blocker": "redis_connection_failing",
            "relationship": RelationshipType.PREVENTS.value.short_name,
            "prevents": "performance_optimization"
        }
    ],
    
    "learnings": [
        {
            "learning": "Signal_based_logging_reduces_tokens",
            "causes": {
                "relationship": RelationshipType.CAUSES.value.short_name,
                "effect": "Reduced_overhead_from_30_to_5_percent"
            }
        }
    ]
}
```

---

## Step 5: Create a Relationship Validator

Add to your codebase to ensure relationships are used correctly:

```python
# validate_relationships.py
from relationship_types import get_relationship_by_name, RelationshipType

def validate_relationship(from_entity, to_entity, relationship_name):
    """Validate that a relationship makes sense"""
    
    rel = get_relationship_by_name(relationship_name)
    if not rel:
        return False, f"Unknown relationship: {relationship_name}"
    
    # Check that inverse is valid
    inverse = rel.inverse
    if not get_relationship_by_name(inverse):
        return False, f"Invalid inverse: {inverse}"
    
    # Could add domain-specific validation here
    return True, f"Valid: {rel.short_name} ({rel.domain})"


def validate_relationship_pair(from_ent, rel_fwd, to_ent, rel_inv):
    """Validate a forward and inverse relationship pair"""
    
    rel_fwd_def = get_relationship_by_name(rel_fwd)
    rel_inv_def = get_relationship_by_name(rel_inv)
    
    if not rel_fwd_def or not rel_inv_def:
        return False
    
    # Check they are actually inverses
    if rel_fwd_def.inverse != rel_inv_def.short_name:
        return False, "Forward and inverse don't match"
    
    return True, "Valid pair"
```

---

## Step 6: Add Relationship Documentation to README

Update your README or architecture docs:

```markdown
## Relationship Types

This system uses a comprehensive relationship type framework based on Dublin Core, 
OBO Relation Ontology, and semantic web standards. 

### Available Domains
- **Structural**: Part-whole, composition (e.g., `part_of`, `has_part`)
- **Hierarchical**: Classification (e.g., `is_a`, `instance_of`)
- **Causal**: Cause-effect, transformation (e.g., `causes`, `derives_from`)
- **Semantic**: Meaning relationships (e.g., `equivalent_to`, `synonym_of`)
- **Temporal**: Time ordering (e.g., `precedes`, `follows`)
- **Agent**: Authorship, creation (e.g., `authored_by`, `created_by`)
- **Spatial**: Location (e.g., `located_in`, `adjacent_to`)
- **Documentation**: References (e.g., `references`, `documents`)
- **Versioning**: Version control (e.g., `is_version_of`, `replaces`)
- **Associative**: General associations (e.g., `depends_on`, `supports`)

For the complete framework, see `RELATIONSHIP_TYPES_GUIDE.md`
```

---

## Migration Path

### Phase 1: Add Framework (No Breaking Changes)
1. Add `relationship_types.py` to codebase ✅ (DONE)
2. Add `RELATIONSHIP_TYPES_GUIDE.md` for reference
3. All existing code continues to work

### Phase 2: Gradual Adoption
1. New signals use formal relationship types
2. When updating documentation, include relationship types
3. New learnings tagged with relationships

### Phase 3: Full Integration (Optional)
1. Migrate all architecture relationships
2. Update all signals to use formal types
3. Enable relationship validation in all submissions

---

## Example: Adding a New Architecture Component

```python
from relationship_types import RelationshipType

# Add new component
mgr.update_architecture_component(
    "vector_store",
    {
        "type": "storage",
        "status": "active",
        "description": "Vector embeddings for semantic search"
    }
)

# Add relationships to it
architecture = mgr.get_architecture()

new_relationships = [
    {
        "from": "mcp_server",
        "to": "vector_store",
        "type": RelationshipType.SUPPORTS.value.short_name,
        "formal": RelationshipType.SUPPORTS.value.formal_name,
        "description": "MCP server queries vector store for semantic search"
    },
    {
        "from": "vector_store",
        "to": "redis_ha",
        "type": RelationshipType.DEPENDS_ON.value.short_name,
        "formal": RelationshipType.DEPENDS_ON.value.formal_name,
        "description": "Vector store depends on Redis for persistence"
    }
]

architecture["relationships"].extend(new_relationships)
mgr.set_architecture(architecture)
```

---

## Testing the Integration

```bash
# Test the framework
cd E:\AI-Setup
python relationship_types.py

# Verify relationships in your code
python -c "
from relationship_types import get_relationships_by_domain
rels = get_relationships_by_domain('structural')
print(f'Structural relationships: {len(rels)}')
for name, rel in rels:
    print(f'  - {rel.short_name}: {rel.description}')
"
```

---

## Benefits

✅ **Interoperability**: Your relationships can be understood by external systems  
✅ **Standardization**: All relationships follow established ontology standards  
✅ **Completeness**: 66 relationship types cover virtually any knowledge domain  
✅ **Reversibility**: Every relationship has a clear inverse  
✅ **Documentation**: Formal names and descriptions for every type  
✅ **Validation**: Can validate that relationships make semantic sense  
✅ **Future-Proof**: Based on standards (Dublin Core, OBO, OWL, RDF) that won't change

---

## Next Steps

1. **Review** `RELATIONSHIP_TYPES_GUIDE.md` to understand all available types
2. **Test** the framework: `python relationship_types.py`
3. **Gradually adopt** in new code and signals
4. **Document** your domain-specific uses of relationships
5. **Share** with team: relationships create consistency

For questions or domain-specific relationship needs, refer back to the guide.
