# Signals Quick Reference

Use `api.signal()` to emit signals. Here are the types:

## DECISION - You made a choice
```python
api.decision(
    name="your_decision",
    outcome="yes",  # or "no" or specific value
    reason="Why you chose it",
    confidence=0.85  # optional, 0-1
)
```

## LEARNING - You discovered something
```python
api.learning(
    experiment_name="what_you_tested",
    what_tried="The approach you used",
    expected_outcome="What you thought would happen",
    actual_outcome="What actually happened",
    category="performance",  # or "quality", "efficiency", "safety"
    success="yes",  # or "no" or "partial"
    recommendation="What next agent should do"
)
```

## ACTION - You're doing something
```python
api.signal(signal_type="ACTION", action="what_you_did", details={...})
```

## BLOCKER - You're stuck
```python
api.signal(
    signal_type="BLOCKER",
    blocker_type="timeout",  # or "missing_data", "permission", etc
    description="What's stuck",
    details={"attempted": "...", "error": "..."}
)
```

## HANDOFF - Next agent takes over
```python
api.signal(
    signal_type="HANDOFF",
    briefing="What next agent should know",
    details={
        "work_completed": "...",
        "next_steps": "...",
        "context": {...}
    }
)
```

## COMPLETION - You finished
```python
api.signal(
    signal_type="COMPLETION",
    status="success",  # or "partial" or "failed"
    summary="What you accomplished",
    details={"metrics": {...}}
)
```

---

**All signals auto-save to learning store for future agents to see.**

For more: See `SIGNAL_REFERENCE.md`
