"""
DEPRECATED shim — project_context moved to context/project_context.py.

Semantic Relationship: this_module re-exports context.project_context (back-compat)

Project context is now part of the Context pillar (System 4). New code should
import from `context.project_context`. This shim keeps existing imports
(`from project_context import ...`) working during the transition and re-exports
the SAME objects (so the singleton stays single).
"""

from context.project_context import (  # noqa: F401
    ProjectContextManager,
    Milestone,
    Task,
    Blocker,
    get_project_context_manager_instance,
    get_context_manager,
)

__all__ = [
    "ProjectContextManager",
    "Milestone",
    "Task",
    "Blocker",
    "get_project_context_manager_instance",
    "get_context_manager",
]
