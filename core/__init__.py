"""
Core Multi-Agent Systems

Organized by semantic domain:
- foundation: Base primitives and vocabulary (relationship types, caching)
- signals: Agent communication (emit, receive, process signals)
- state: Agent state persistence (checkpoints, recovery)
- learning: Knowledge capture and retrieval

All systems use semantic naming: subject_relationship_object()
"""

__version__ = "1.0.0"
__all__ = ["foundation", "signals", "state", "learning"]
