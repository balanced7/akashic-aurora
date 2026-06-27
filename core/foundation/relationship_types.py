"""
Comprehensive Relationship Type Framework for Knowledge Graphs
==============================================================

Based on:
- Dublin Core Metadata Terms (DCMI)
- OBO Relation Ontology (RO) - biomedical ontology standard
- RDF/OWL properties
- Schema.org predicates
- General knowledge representation standards

This framework provides a robust, standardized set of relationship types
that can map any body of knowledge and ensure consistency across the system.

Usage:
    from core.foundation.relationship_types import RelationshipType, get_relationship_by_name

    rel = RelationshipType.PART_OF
    print(rel.formal_name, rel.inverse)

    rel = get_relationship_by_name("derives_from")
"""

from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class RelationshipTypeDefinition:
    """Formal definition of a relationship type"""
    formal_name: str  # OBO/Dublin Core formal name
    short_name: str  # Short identifier
    inverse: str  # Inverse relationship
    description: str  # What this relationship means
    domain: str  # Subject domain (e.g., "structural", "causal", "temporal")
    examples: List[str]  # Example usage


class RelationshipType(Enum):
    """Comprehensive relationship type framework for knowledge graphs"""

    # ============================================================================
    # STRUCTURAL RELATIONSHIPS (part-whole, composition)
    # Based on: OBO Relation Ontology (RO:0000050, etc.)
    # ============================================================================

    PART_OF = RelationshipTypeDefinition(
        formal_name="BFO:0000050 (OBO)",
        short_name="part_of",
        inverse="has_part",
        description="Subject is a part or component of the object",
        domain="structural",
        examples=["Engine part_of Car", "Chapter part_of Book", "Class part_of Module"]
    )

    HAS_PART = RelationshipTypeDefinition(
        formal_name="BFO:0000051 (OBO)",
        short_name="has_part",
        inverse="part_of",
        description="Subject has the object as a part or component",
        domain="structural",
        examples=["Car has_part Engine", "Book has_part Chapter", "Module has_part Class"]
    )

    COMPONENT_OF = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="component_of",
        inverse="has_component",
        description="Subject is a functional component of object (stricter than part_of)",
        domain="structural",
        examples=["CPU component_of Computer", "Wheel component_of Bicycle"]
    )

    HAS_COMPONENT = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="has_component",
        inverse="component_of",
        description="Subject has object as a functional component",
        domain="structural",
        examples=["Computer has_component CPU", "Bicycle has_component Wheel"]
    )

    MEMBER_OF = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="member_of",
        inverse="has_member",
        description="Subject is a member of a collection or group",
        domain="structural",
        examples=["Student member_of Class", "City member_of Country"]
    )

    HAS_MEMBER = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="has_member",
        inverse="member_of",
        description="Subject is a collection containing the object as a member",
        domain="structural",
        examples=["Class has_member Student", "Country has_member City"]
    )

    CONTAINED_IN = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="contained_in",
        inverse="contains",
        description="Subject is physically or logically contained in object",
        domain="structural",
        examples=["Water contained_in Cup", "File contained_in Directory"]
    )

    CONTAINS = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="contains",
        inverse="contained_in",
        description="Subject physically or logically contains object",
        domain="structural",
        examples=["Cup contains Water", "Directory contains File"]
    )

    # ============================================================================
    # HIERARCHICAL/TAXONOMIC RELATIONSHIPS
    # Based on: RDFS, OWL, Dublin Core
    # ============================================================================

    IS_A = RelationshipTypeDefinition(
        formal_name="RDFS:subClassOf",
        short_name="is_a",
        inverse="has_subclass",
        description="Subject is a class or type of the object (specialization)",
        domain="hierarchical",
        examples=["Dog is_a Animal", "Circle is_a Shape", "Python is_a Programming_Language"]
    )

    HAS_SUBCLASS = RelationshipTypeDefinition(
        formal_name="RDFS",
        short_name="has_subclass",
        inverse="is_a",
        description="Subject is a superclass of object",
        domain="hierarchical",
        examples=["Animal has_subclass Dog", "Shape has_subclass Circle"]
    )

    INSTANCE_OF = RelationshipTypeDefinition(
        formal_name="RDF:type",
        short_name="instance_of",
        inverse="has_instance",
        description="Subject is an instance of the class object",
        domain="hierarchical",
        examples=["Fido instance_of Dog", "Socrates instance_of Philosopher"]
    )

    HAS_INSTANCE = RelationshipTypeDefinition(
        formal_name="OWL",
        short_name="has_instance",
        inverse="instance_of",
        description="Subject is a class that has object as an instance",
        domain="hierarchical",
        examples=["Dog has_instance Fido", "Philosopher has_instance Socrates"]
    )

    # ============================================================================
    # CAUSALITY & TRANSFORMATION RELATIONSHIPS
    # Based on: OBO Relation Ontology (RO:0002410, etc.)
    # ============================================================================

    CAUSES = RelationshipTypeDefinition(
        formal_name="RO:0002410 (OBO)",
        short_name="causes",
        inverse="caused_by",
        description="Subject is the cause of the object (direct causation)",
        domain="causal",
        examples=["Heat causes Melting", "Rain causes Flooding", "Exercise causes Fitness"]
    )

    CAUSED_BY = RelationshipTypeDefinition(
        formal_name="OBO",
        short_name="caused_by",
        inverse="causes",
        description="Subject is caused by the object",
        domain="causal",
        examples=["Melting caused_by Heat", "Flooding caused_by Rain"]
    )

    DERIVES_FROM = RelationshipTypeDefinition(
        formal_name="RO:0001000 (OBO)",
        short_name="derives_from",
        inverse="derives_to",
        description="Subject is derived from or originates from object (transformation/evolution)",
        domain="causal",
        examples=["Butter derives_from Milk", "Adult derives_from Child", "Code derives_from Specification"]
    )

    DERIVES_INTO = RelationshipTypeDefinition(
        formal_name="OBO",
        short_name="derives_into",
        inverse="derives_from",
        description="Subject transforms into or gives rise to object",
        domain="causal",
        examples=["Milk derives_into Butter", "Child derives_into Adult"]
    )

    DEVELOPS_FROM = RelationshipTypeDefinition(
        formal_name="RO:0002202 (OBO)",
        short_name="develops_from",
        inverse="develops_into",
        description="Subject develops or emerges from object (biological/developmental)",
        domain="causal",
        examples=["Adult develops_from Embryo", "Organ develops_from Tissue"]
    )

    DEVELOPS_INTO = RelationshipTypeDefinition(
        formal_name="OBO",
        short_name="develops_into",
        inverse="develops_from",
        description="Subject develops into object",
        domain="causal",
        examples=["Embryo develops_into Adult", "Tissue develops_into Organ"]
    )

    INFLUENCES = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="influences",
        inverse="influenced_by",
        description="Subject has a modifying or determining effect on object (weaker than causes)",
        domain="causal",
        examples=["Culture influences Art", "Weather influences Mood", "History influences Politics"]
    )

    INFLUENCED_BY = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="influenced_by",
        inverse="influences",
        description="Subject is influenced by object",
        domain="causal",
        examples=["Art influenced_by Culture", "Politics influenced_by History"]
    )

    PREVENTS = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="prevents",
        inverse="prevented_by",
        description="Subject prevents or stops the occurrence of object",
        domain="causal",
        examples=["Medicine prevents Disease", "Barrier prevents Entry"]
    )

    PREVENTED_BY = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="prevented_by",
        inverse="prevents",
        description="Subject is prevented by object",
        domain="causal",
        examples=["Disease prevented_by Medicine"]
    )

    # ============================================================================
    # SEMANTIC/EQUIVALENCE RELATIONSHIPS
    # Based on: SKOS, Dublin Core, RDF Schema
    # ============================================================================

    EQUIVALENT_TO = RelationshipTypeDefinition(
        formal_name="OWL:sameAs",
        short_name="equivalent_to",
        inverse="equivalent_to",
        description="Subject is equivalent to or the same as object",
        domain="semantic",
        examples=["Automobile equivalent_to Car", "Heartbeat equivalent_to Pulse"]
    )

    SIMILAR_TO = RelationshipTypeDefinition(
        formal_name="SKOS:closeMatch",
        short_name="similar_to",
        inverse="similar_to",
        description="Subject is similar to object (weaker equivalence)",
        domain="semantic",
        examples=["Python similar_to Ruby", "House similar_to Mansion"]
    )

    SYNONYM_OF = RelationshipTypeDefinition(
        formal_name="SKOS:exactMatch",
        short_name="synonym_of",
        inverse="synonym_of",
        description="Subject is a synonym of object (terms have same meaning)",
        domain="semantic",
        examples=["Automobile synonym_of Car", "Physician synonym_of Doctor"]
    )

    OPPOSITE_OF = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="opposite_of",
        inverse="opposite_of",
        description="Subject is opposite or antonym of object",
        domain="semantic",
        examples=["Hot opposite_of Cold", "Begin opposite_of End"]
    )

    RELATED_TO = RelationshipTypeDefinition(
        formal_name="SKOS:related",
        short_name="related_to",
        inverse="related_to",
        description="Subject is related to object (general semantic relationship)",
        domain="semantic",
        examples=["Apple related_to Orange", "Python related_to Programming"]
    )

    # ============================================================================
    # TEMPORAL RELATIONSHIPS
    # Based on: Dublin Core, OWL-Time
    # ============================================================================

    PRECEDES = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="precedes",
        inverse="preceded_by",
        description="Subject occurs before object in time",
        domain="temporal",
        examples=["Birth precedes Death", "Spring precedes Summer"]
    )

    PRECEDED_BY = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="preceded_by",
        inverse="precedes",
        description="Subject is preceded by object in time",
        domain="temporal",
        examples=["Death preceded_by Birth", "Summer preceded_by Spring"]
    )

    FOLLOWS = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="follows",
        inverse="followed_by",
        description="Subject occurs after object in time",
        domain="temporal",
        examples=["Death follows Birth", "Summer follows Spring"]
    )

    FOLLOWED_BY = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="followed_by",
        inverse="follows",
        description="Subject is followed by object in time",
        domain="temporal",
        examples=["Birth followed_by Death", "Spring followed_by Summer"]
    )

    OCCURS_DURING = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="occurs_during",
        inverse="has_event",
        description="Subject occurs during the time period object",
        domain="temporal",
        examples=["Meeting occurs_during Tuesday", "Event occurs_during Renaissance"]
    )

    HAS_EVENT = RelationshipTypeDefinition(
        formal_name="OWL-Time",
        short_name="has_event",
        inverse="occurs_during",
        description="Subject is a time period that contains event object",
        domain="temporal",
        examples=["Tuesday has_event Meeting", "Renaissance has_event Discovery"]
    )

    CONTEMPORARY_WITH = RelationshipTypeDefinition(
        formal_name="Custom",
        short_name="contemporary_with",
        inverse="contemporary_with",
        description="Subject and object occur at the same time",
        domain="temporal",
        examples=["WW2 contemporary_with Holocaust"]
    )

    # ============================================================================
    # AGENT/ATTRIBUTION RELATIONSHIPS
    # Based on: Dublin Core, PROV
    # ============================================================================

    AUTHORED_BY = RelationshipTypeDefinition(
        formal_name="DC:creator",
        short_name="authored_by",
        inverse="authored",
        description="Subject was created/written by object (person or organization)",
        domain="agent",
        examples=["Book authored_by Author", "Code authored_by Developer"]
    )

    AUTHORED = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="authored",
        inverse="authored_by",
        description="Subject authored the object",
        domain="agent",
        examples=["Author authored Book", "Developer authored Code"]
    )

    CREATED_BY = RelationshipTypeDefinition(
        formal_name="PROV:wasGeneratedBy",
        short_name="created_by",
        inverse="created",
        description="Subject was created by object (agent, process, or action)",
        domain="agent",
        examples=["Product created_by Process", "Discovery created_by Research"]
    )

    CREATED = RelationshipTypeDefinition(
        formal_name="PROV",
        short_name="created",
        inverse="created_by",
        description="Subject created the object",
        domain="agent",
        examples=["Process created Product", "Research created Discovery"]
    )

    ATTRIBUTED_TO = RelationshipTypeDefinition(
        formal_name="PROV:wasAttributedTo",
        short_name="attributed_to",
        inverse="attributed",
        description="Subject's existence or properties are attributed to object",
        domain="agent",
        examples=["Success attributed_to Effort", "Theory attributed_to Scientist"]
    )

    ATTRIBUTED = RelationshipTypeDefinition(
        formal_name="PROV",
        short_name="attributed",
        inverse="attributed_to",
        description="Subject attributes object to someone/something",
        domain="agent",
        examples=["Scientist attributed Theory"]
    )

    PERFORMED_BY = RelationshipTypeDefinition(
        formal_name="PROV",
        short_name="performed_by",
        inverse="performed",
        description="Subject (action/task) is performed by object (agent)",
        domain="agent",
        examples=["Task performed_by Person", "Surgery performed_by Doctor"]
    )

    PERFORMED = RelationshipTypeDefinition(
        formal_name="PROV",
        short_name="performed",
        inverse="performed_by",
        description="Subject performs the object (action/task)",
        domain="agent",
        examples=["Person performed Task", "Doctor performed Surgery"]
    )

    # ============================================================================
    # SPATIAL RELATIONSHIPS
    # Based on: RDF, Custom
    # ============================================================================

    LOCATED_IN = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="located_in",
        inverse="has_location",
        description="Subject is located or situated in object",
        domain="spatial",
        examples=["City located_in Country", "Building located_in City"]
    )

    HAS_LOCATION = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="has_location",
        inverse="located_in",
        description="Subject is a location containing object",
        domain="spatial",
        examples=["Country has_location City", "City has_location Building"]
    )

    ADJACENT_TO = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="adjacent_to",
        inverse="adjacent_to",
        description="Subject is next to or bordered by object",
        domain="spatial",
        examples=["France adjacent_to Germany", "Room adjacent_to Corridor"]
    )

    OVERLAPS_WITH = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="overlaps_with",
        inverse="overlaps_with",
        description="Subject partially overlaps or intersects with object",
        domain="spatial",
        examples=["Territory overlaps_with Boundary"]
    )

    # ============================================================================
    # REFERENCE/DOCUMENTATION RELATIONSHIPS
    # Based on: Dublin Core, Schema.org
    # ============================================================================

    REFERENCES = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="references",
        inverse="referenced_by",
        description="Subject cites or mentions object",
        domain="documentation",
        examples=["Paper references Study", "Code references Documentation"]
    )

    REFERENCED_BY = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="referenced_by",
        inverse="references",
        description="Subject is cited or mentioned by object",
        domain="documentation",
        examples=["Study referenced_by Paper", "Documentation referenced_by Code"]
    )

    DOCUMENTS = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="documents",
        inverse="documented_by",
        description="Subject provides documentation or description of object",
        domain="documentation",
        examples=["Manual documents Device", "Guide documents Process"]
    )

    DOCUMENTED_BY = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="documented_by",
        inverse="documents",
        description="Subject is documented by object",
        domain="documentation",
        examples=["Device documented_by Manual", "Process documented_by Guide"]
    )

    BASED_ON = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="based_on",
        inverse="basis_for",
        description="Subject is based on or derived from object",
        domain="documentation",
        examples=["Implementation based_on Specification", "Variation based_on Original"]
    )

    BASIS_FOR = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="basis_for",
        inverse="based_on",
        description="Subject is the basis for object",
        domain="documentation",
        examples=["Specification basis_for Implementation", "Theory basis_for Application"]
    )

    # ============================================================================
    # VERSIONING RELATIONSHIPS
    # Based on: Dublin Core
    # ============================================================================

    IS_VERSION_OF = RelationshipTypeDefinition(
        formal_name="DC:isVersionOf",
        short_name="is_version_of",
        inverse="has_version",
        description="Subject is a version of object",
        domain="versioning",
        examples=["Version2 is_version_of Software", "Draft is_version_of Document"]
    )

    HAS_VERSION = RelationshipTypeDefinition(
        formal_name="DC:hasVersion",
        short_name="has_version",
        inverse="is_version_of",
        description="Subject has object as a version",
        domain="versioning",
        examples=["Software has_version Version2", "Document has_version Draft"]
    )

    REPLACES = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="replaces",
        inverse="replaced_by",
        description="Subject replaces or supersedes object",
        domain="versioning",
        examples=["NewVersion replaces OldVersion", "UpdatedPolicy replaces OldPolicy"]
    )

    REPLACED_BY = RelationshipTypeDefinition(
        formal_name="Dublin Core",
        short_name="replaced_by",
        inverse="replaces",
        description="Subject is replaced or superseded by object",
        domain="versioning",
        examples=["OldVersion replaced_by NewVersion", "OldPolicy replaced_by UpdatedPolicy"]
    )

    # ============================================================================
    # ASSOCIATIVE RELATIONSHIPS (general associations)
    # ============================================================================

    ASSOCIATED_WITH = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="associated_with",
        inverse="associated_with",
        description="Subject is associated with object (general connection)",
        domain="associative",
        examples=["Concept associated_with Domain", "Person associated_with Organization"]
    )

    DEPENDS_ON = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="depends_on",
        inverse="dependency_of",
        description="Subject depends on or requires object to function",
        domain="associative",
        examples=["Software depends_on Library", "Project depends_on Resource"]
    )

    DEPENDENCY_OF = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="dependency_of",
        inverse="depends_on",
        description="Subject is a dependency required by object",
        domain="associative",
        examples=["Library dependency_of Software", "Resource dependency_of Project"]
    )

    REQUIRES = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="requires",
        inverse="required_by",
        description="Subject requires object (same as depends_on, more active)",
        domain="associative",
        examples=["Course requires Prerequisite", "Job requires Skill"]
    )

    REQUIRED_BY = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="required_by",
        inverse="requires",
        description="Subject is required by object",
        domain="associative",
        examples=["Prerequisite required_by Course", "Skill required_by Job"]
    )

    SUPPORTS = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="supports",
        inverse="supported_by",
        description="Subject supports or helps object",
        domain="associative",
        examples=["Argument supports Claim", "Infrastructure supports Service"]
    )

    SUPPORTED_BY = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="supported_by",
        inverse="supports",
        description="Subject is supported by object",
        domain="associative",
        examples=["Claim supported_by Argument", "Service supported_by Infrastructure"]
    )

    COMPLEMENTS = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="complements",
        inverse="complemented_by",
        description="Subject complements or goes well with object",
        domain="associative",
        examples=["Wine complements Cheese", "Feature complements Functionality"]
    )

    COMPLEMENTED_BY = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="complemented_by",
        inverse="complements",
        description="Subject is complemented by object",
        domain="associative",
        examples=["Cheese complemented_by Wine", "Functionality complemented_by Feature"]
    )

    CONFLICTS_WITH = RelationshipTypeDefinition(
        formal_name="RDF",
        short_name="conflicts_with",
        inverse="conflicts_with",
        description="Subject conflicts with or contradicts object",
        domain="associative",
        examples=["Policy conflicts_with Law", "Theory conflicts_with Evidence"]
    )


def get_relationship_by_name(name: str) -> Optional[RelationshipTypeDefinition]:
    """Get relationship type by short name or formal name"""
    name_lower = name.lower().replace(" ", "_")

    for rel in RelationshipType:
        if (rel.value.short_name.lower() == name_lower or
            rel.value.formal_name.lower().replace(" ", "_") == name_lower or
            rel.name.lower() == name_lower):
            return rel.value

    return None


def get_relationships_by_domain(domain: str) -> List[tuple]:
    """Get all relationships in a specific domain"""
    domain_lower = domain.lower()
    results = []

    for rel in RelationshipType:
        if rel.value.domain.lower() == domain_lower:
            results.append((rel.name, rel.value))

    return sorted(results, key=lambda x: x[1].short_name)


def list_all_domains() -> List[str]:
    """List all available domains"""
    domains = set()
    for rel in RelationshipType:
        domains.add(rel.value.domain)
    return sorted(list(domains))


def print_relationship_reference():
    """Print a human-readable reference of all relationship types"""
    print("\n" + "=" * 100)
    print("RELATIONSHIP TYPE FRAMEWORK - COMPLETE REFERENCE")
    print("=" * 100)

    domains = list_all_domains()

    for domain in domains:
        print(f"\n[{domain.upper()}]")
        print("-" * 100)

        rels = get_relationships_by_domain(domain)

        for rel_name, rel_def in rels:
            print(f"\n  {rel_name}")
            print(f"    Short: {rel_def.short_name}")
            print(f"    Formal: {rel_def.formal_name}")
            print(f"    Inverse: {rel_def.inverse}")
            print(f"    Definition: {rel_def.description}")
            print(f"    Examples: {', '.join(rel_def.examples)}")

    print("\n" + "=" * 100 + "\n")


# For backwards compatibility with existing code
RELATIONSHIP_TYPES = {rel.value.short_name: rel.value for rel in RelationshipType}


if __name__ == "__main__":
    print_relationship_reference()
