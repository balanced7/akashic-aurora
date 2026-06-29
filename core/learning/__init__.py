"""
Learning System

Semantic Relationship: Learning enables agents to build on past discoveries

Includes:
- learning_store.py: experiment-outcome learnings (signals), indexed on a Store
  - Functions: record_learning_derived_from_experiment()
  - Functions: load_learnings_applicable_to_task()
  - Functions: discover_patterns_from_learnings()
- agent_memory.py: richer multi-type memory (decisions, experiences, reflections,
  approaches) — the CoALA-style model, persisted through a Store
  - Class: AgentMemory ; Function: get_agent_memory()

Purpose: Capture experiments, extract patterns, and apply them to future problems.

Two complementary stores, kept distinct (different names + Redis namespaces):
- LearningStore -> experiment outcomes (the `learn:` namespace)
- AgentMemory   -> decisions/experiences/reflections/approaches (the `mem:` namespace)
"""

from .learning_store import LearningStore, get_learning_store
from .agent_memory import AgentMemory, get_agent_memory
from .consolidation import (consolidate_into_chronicle, consolidate_memory_into_chronicle,
                            consolidate_learnings_into_chronicle)

__all__ = ["LearningStore", "get_learning_store", "AgentMemory", "get_agent_memory",
           "consolidate_into_chronicle", "consolidate_memory_into_chronicle",
           "consolidate_learnings_into_chronicle"]
