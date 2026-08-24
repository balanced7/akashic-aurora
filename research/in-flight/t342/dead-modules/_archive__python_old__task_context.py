#!/usr/bin/env python3
"""
Task Context - Get Context Before Starting Work
===============================================

Usage:
    python task_context.py "Install dependencies"
    
    # In Python:
    from task_context import get_context
    print(get_context("Install dependencies", "vision"))
"""

import sys
sys.path.insert(0, r"E:\AI-Setup")

from auto_capture import get_context


def before_you_start(task: str, component: str = None):
    """Print helpful context before starting work"""
    print()
    print("=" * 70)
    print(f"  TASK CONTEXT: {task}")
    print("=" * 70)
    print()
    
    ctx = get_context(task, component)
    if ctx:
        print(ctx)
    else:
        print("(No prior context - new work)")
    print()
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        component = None
        if any(w in task.lower() for w in ["vision", "florence", "comfyui"]):
            component = "vision"
        elif "redis" in task.lower():
            component = "infrastructure"
        before_you_start(task, component)
    else:
        print("Usage: python task_context.py <task description>")
