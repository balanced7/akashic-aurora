"""
Auto-Capture - Automatic Context Recording
=========================================

Usage:
    from auto_capture import capture, before_task, after_task
    
    before_task("Install dependencies")
    # ... do work ...
    after_task(success=True, score=0.9, learnings=["Downloaded successfully"])
"""

import sys
import json
import redis
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, r"E:\AI-Setup")

from learning.store import learn
from session_logger import SESSION_ID


def _get_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return r
    except:
        return None


class TaskCapture:
    _current = None
    
    def __init__(self):
        self.redis = _get_redis()
        self.task = ""
        self.approach = ""
        self.start_time = None
        self.learnings = []
    
    def start(self, task: str, approach: str = ""):
        self.task = task
        self.approach = approach
        self.start_time = datetime.now()
        TaskCapture._current = self
        return self
    
    def learn(self, msg: str):
        self.learnings.append(msg)
    
    def done(self, success: bool, score: float = 0.5, learnings: List[str] = None):
        if learnings:
            self.learnings.extend(learnings)
        
        ls = learn()
        exp_id = ls.record(
            task=self.task,
            success=success,
            approach=self.approach,
            score=score,
            learnings=self.learnings,
            session_id=SESSION_ID
        )
        
        if not success and self.learnings:
            ls.reflect(
                task=self.task,
                what_went_wrong="Task failed",
                what_would_help=self.learnings[0],
                confidence=min(0.5 + len(self.learnings) * 0.1, 0.9)
            )
        
        TaskCapture._current = None
        return exp_id
    
    @classmethod
    def get_current(cls):
        return cls._current


def before_task(task: str, approach: str = ""):
    tc = TaskCapture()
    tc.start(task, approach)
    return tc


def after_task(success: bool, score: float = 0.5, learnings: List[str] = None):
    if TaskCapture._current:
        return TaskCapture._current.done(success, score, learnings)
    return ""


def when_decided(title: str, decision: str, rationale: List[str], alternatives: List[Dict] = None):
    """Record a decision"""
    ls = learn()
    return ls.decide(
        title=title,
        decision=decision,
        rationale=rationale,
        alternatives=alternatives or [],
        session_id=SESSION_ID
    )


def when_approach_works(component: str, name: str, learnings: List[str] = None):
    """Record a working approach"""
    ls = learn()
    return ls.register_approach(component, name, "working", learnings)


def when_approach_fails(component: str, name: str, error: str, learnings: List[str] = None):
    """Record a failed approach"""
    ls = learn()
    ls.register_approach(component, name, "failed", learnings, {"error": error[:200]})
    if learnings:
        ls.reflect(
            task=f"{component}: {name}",
            what_went_wrong=error[:100],
            what_would_help=learnings[0] if learnings else "Try different approach",
            confidence=0.6
        )


def get_context(task: str, component: str = None) -> str:
    """Get all relevant context for a task"""
    ls = learn()
    parts = []
    
    if component:
        status = ls.get_component_status(component)
        if status.get("working"):
            parts.append("## Working Approaches\n")
            for a in status["working"]:
                parts.append(f"- {a.get('name', 'N/A')}")
            parts.append("")
        if status.get("failed"):
            parts.append("## Failed Approaches\n")
            for a in status["failed"][:3]:
                parts.append(f"- {a.get('name', 'N/A')}")
                l = a.get('learnings', [])
                if l:
                    parts.append(f"  -> {l[0][:50]}")
            parts.append("")
    
    similar = ls.get_similar(task)
    if similar:
        parts.append("## Similar Experiences\n")
        for e in similar[:3]:
            status = "[OK]" if e.success else "[XX]"
            parts.append(f"- {status} {e.task[:50]}")
            if e.learnings:
                parts.append(f"  -> {e.learnings[0][:50]}")
        parts.append("")
    
    decisions = ls.get_decisions(days=90)
    matching = [d for d in decisions if any(w in d.title.lower() for w in task.lower().split() if len(w) > 3)]
    if matching:
        parts.append("## Relevant Decisions\n")
        for d in matching[:3]:
            parts.append(f"- [{d.status}] {d.title}")
        parts.append("")
    
    return "\n".join(parts) if parts else ""


if __name__ == "__main__":
    print("=" * 50)
    print("  AUTO-CAPTURE TEST")
    print("=" * 50)
    print()
    
    print("[1] Context for 'install comfyui':")
    print(get_context("install comfyui", "vision") or "(No context)")
    print()
    
    print("[2] Recording test task:")
    before_task("Test task", "Test approach")
    after_task(success=True, score=0.85, learnings=["Works!"])
