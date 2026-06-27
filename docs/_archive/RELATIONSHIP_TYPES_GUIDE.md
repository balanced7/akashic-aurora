# Relationship Types Framework - Quick Reference

**Total Types:** 60+ standardized relationships  
**Based on:** Dublin Core, OBO Relation Ontology, RDF/OWL, Schema.org  
**Coverage:** Structural, hierarchical, causal, temporal, spatial, agent, documentation, versioning

## Quick Start

```python
from relationship_types import RelationshipType, get_relationship_by_name

# Get a relationship type
rel = get_relationship_by_name("part_of")
print(rel.formal_name, rel.inverse, rel.description)

# Use in your graph
edge = {
    "from": "Engine",
    "to": "Car",
    "type": RelationshipType.PART_OF.value.short_name,
    "description": "Engine is a part of Car"
}

# List all domains
from relationship_types import list_all_domains
print(list_all_domains())

# Get all relationships in a domain
from relationship_types import get_relationships_by_domain
structural_rels = get_relationships_by_domain("structural")
```

## Relationship Domains

### 1. **Structural** (Part-Whole, Composition)
These describe how entities are composed or structured together.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `part_of` | BFO:0000050 | has_part | Engine part_of Car |
| `has_part` | BFO:0000051 | part_of | Car has_part Engine |
| `component_of` | Custom | has_component | CPU component_of Computer |
| `has_component` | Custom | component_of | Computer has_component CPU |
| `member_of` | RDF | has_member | Student member_of Class |
| `has_member` | RDF | member_of | Class has_member Student |
| `contained_in` | RDF | contains | File contained_in Directory |
| `contains` | RDF | contained_in | Directory contains File |

**Use when:** Describing physical or logical composition, hierarchy of objects

---

### 2. **Hierarchical/Taxonomic** (Classification)
These describe inheritance and classification relationships.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `is_a` | RDFS:subClassOf | has_subclass | Dog is_a Animal |
| `has_subclass` | RDFS | is_a | Animal has_subclass Dog |
| `instance_of` | RDF:type | has_instance | Fido instance_of Dog |
| `has_instance` | OWL | instance_of | Dog has_instance Fido |

**Use when:** Defining class hierarchies, type relationships, inheritance

---

### 3. **Causal** (Cause-Effect, Transformation)
These describe causation, transformation, and development relationships.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `causes` | RO:0002410 | caused_by | Heat causes Melting |
| `caused_by` | OBO | causes | Melting caused_by Heat |
| `derives_from` | RO:0001000 | derives_into | Butter derives_from Milk |
| `derives_into` | OBO | derives_from | Milk derives_into Butter |
| `develops_from` | RO:0002202 | develops_into | Adult develops_from Embryo |
| `develops_into` | OBO | develops_from | Embryo develops_into Adult |
| `influences` | Custom | influenced_by | Culture influences Art |
| `influenced_by` | Custom | influences | Art influenced_by Culture |
| `prevents` | Custom | prevented_by | Medicine prevents Disease |
| `prevented_by` | Custom | prevents | Disease prevented_by Medicine |

**Use when:** Showing cause-effect, transformations, evolutionary relationships

---

### 4. **Semantic/Equivalence** (Meaning Relationships)
These describe semantic similarities and equivalences.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `equivalent_to` | OWL:sameAs | equivalent_to | Automobile equivalent_to Car |
| `similar_to` | SKOS:closeMatch | similar_to | Python similar_to Ruby |
| `synonym_of` | SKOS:exactMatch | synonym_of | Physician synonym_of Doctor |
| `opposite_of` | Custom | opposite_of | Hot opposite_of Cold |
| `related_to` | SKOS:related | related_to | Apple related_to Orange |

**Use when:** Showing semantic relationships, synonymy, similarity

---

### 5. **Temporal** (Time-based Relationships)
These describe temporal ordering and relationships in time.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `precedes` | OWL-Time | preceded_by | Birth precedes Death |
| `preceded_by` | OWL-Time | precedes | Death preceded_by Birth |
| `follows` | OWL-Time | followed_by | Death follows Birth |
| `followed_by` | OWL-Time | follows | Birth followed_by Death |
| `occurs_during` | OWL-Time | has_event | Meeting occurs_during Tuesday |
| `has_event` | OWL-Time | occurs_during | Tuesday has_event Meeting |
| `contemporary_with` | Custom | contemporary_with | WW2 contemporary_with Holocaust |

**Use when:** Showing temporal sequences, scheduling, historical relationships

---

### 6. **Agent/Attribution** (Who/What Created/Did Something)
These describe agency, authorship, and creation.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `authored_by` | DC:creator | authored | Book authored_by Author |
| `authored` | Dublin Core | authored_by | Author authored Book |
| `created_by` | PROV:wasGeneratedBy | created | Product created_by Process |
| `created` | PROV | created_by | Process created Product |
| `attributed_to` | PROV:wasAttributedTo | attributed | Success attributed_to Effort |
| `attributed` | PROV | attributed_to | Scientist attributed Theory |
| `performed_by` | PROV | performed | Surgery performed_by Doctor |
| `performed` | PROV | performed_by | Doctor performed Surgery |

**Use when:** Showing who created, wrote, discovered, or performed something

---

### 7. **Spatial** (Location/Position)
These describe spatial relationships and locations.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `located_in` | RDF | has_location | City located_in Country |
| `has_location` | RDF | located_in | Country has_location City |
| `adjacent_to` | RDF | adjacent_to | France adjacent_to Germany |
| `overlaps_with` | RDF | overlaps_with | Territory overlaps_with Boundary |

**Use when:** Describing geographical or spatial locations, boundaries

---

### 8. **Documentation/Reference** (Knowledge Links)
These describe documentation and cross-references.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `references` | Dublin Core | referenced_by | Paper references Study |
| `referenced_by` | Dublin Core | references | Study referenced_by Paper |
| `documents` | RDF | documented_by | Manual documents Device |
| `documented_by` | RDF | documents | Device documented_by Manual |
| `based_on` | Dublin Core | basis_for | Implementation based_on Specification |
| `basis_for` | Dublin Core | based_on | Specification basis_for Implementation |

**Use when:** Showing citations, documentation, specifications

---

### 9. **Versioning** (Version Control)
These describe version relationships.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `is_version_of` | DC:isVersionOf | has_version | Version2 is_version_of Software |
| `has_version` | DC:hasVersion | is_version_of | Software has_version Version2 |
| `replaces` | Dublin Core | replaced_by | NewVersion replaces OldVersion |
| `replaced_by` | Dublin Core | replaces | OldVersion replaced_by NewVersion |

**Use when:** Tracking versions, updates, superseding documents

---

### 10. **Associative** (General Associations)
These describe general associations and dependencies.

| Type | Formal | Inverse | Example |
|------|--------|---------|---------|
| `associated_with` | RDF | associated_with | Concept associated_with Domain |
| `depends_on` | RDF | dependency_of | Software depends_on Library |
| `dependency_of` | RDF | depends_on | Library dependency_of Software |
| `requires` | RDF | required_by | Course requires Prerequisite |
| `required_by` | RDF | requires | Prerequisite required_by Course |
| `supports` | RDF | supported_by | Argument supports Claim |
| `supported_by` | RDF | supports | Claim supported_by Argument |
| `complements` | RDF | complemented_by | Wine complements Cheese |
| `complemented_by` | RDF | complements | Cheese complemented_by Wine |
| `conflicts_with` | RDF | conflicts_with | Policy conflicts_with Law |

**Use when:** Showing dependencies, support, conflicts, and general relationships

---

## How to Use in Your Project

### Option 1: Use in Architecture Documentation

```python
from relationship_types import RelationshipType

# Define architecture with formal relationships
architecture = {
    "components": {
        "redis_ha": {"type": "database"},
        "mcp_server": {"type": "protocol"},
        "session_logger": {"type": "logging"}
    },
    "relationships": [
        {
            "from": "redis_ha",
            "to": "session_logger",
            "type": RelationshipType.SUPPORTS.value.short_name,
            "description": "Redis HA supports session logging"
        },
        {
            "from": "mcp_server",
            "to": "redis_ha",
            "type": RelationshipType.DEPENDS_ON.value.short_name,
            "description": "MCP server depends on Redis HA"
        }
    ]
}
```

### Option 2: Use in Knowledge Graph

```python
from relationship_types import get_relationship_by_name

def add_knowledge_link(from_entity, to_entity, relationship_name):
    rel = get_relationship_by_name(relationship_name)
    if rel:
        return {
            "source": from_entity,
            "target": to_entity,
            "relation_type": rel.short_name,
            "formal_name": rel.formal_name,
            "inverse": rel.inverse
        }
```

### Option 3: Use in Learning System

```python
# Tag learnings with relationship context
learning = {
    "experiment_name": "Redis performance",
    "what_tried": "Dual-write to file and Redis",
    "actual_outcome": "Hash mismatch resolved after cleanup",
    "outcome_relationship": "derived_from",  # What this learning derives from
    "related_to": ["sync_integration", "data_integrity"]
}
```

---

## Key Principles

1. **Always use the inverse:** Every relationship has an inverse. Be consistent about directionality.
   - ✅ Good: `A part_of B` and `B has_part A` (consistent pair)
   - ❌ Bad: Just use `part_of` in one direction

2. **Match the domain:** Use relationships appropriate to your domain.
   - Structural for composition
   - Causal for transformations
   - Temporal for sequences
   - Semantic for meaning

3. **Formal names for interoperability:** Always store the formal name (like `RO:0000050`) for systems that need to understand your graph.

4. **Examples help:** Include examples when documenting relationships.

---

## Integration with project_context.py

To upgrade your architecture relationships:

```python
# OLD:
"relationships": [
    "redis_ha -> session_logger (stores session data)"
]

# NEW:
"relationships": [
    {
        "from": "redis_ha",
        "to": "session_logger",
        "type": "supports",
        "formal_type": "RDF",
        "description": "Redis HA stores and supports session logger data"
    }
]
```

---

## Print Full Reference

```bash
cd E:\AI-Setup
python relationship_types.py
```

This will print a complete reference of all 60+ relationship types organized by domain.

---

## Sources

- [Dublin Core Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- [OBO Relation Ontology](https://oborel.github.io/)
- [RDF Schema](https://www.w3.org/TR/rdf-schema/)
- [OWL (Web Ontology Language)](https://www.w3.org/TR/owl2-overview/)
- [SKOS (Simple Knowledge Organization System)](https://www.w3.org/2004/02/skos/)
