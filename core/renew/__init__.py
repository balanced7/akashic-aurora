"""Renew -- the membrane's temporal (5th) job: keep working context healthy ACROSS sessions.

Semantic Relationship: Renew closes the loop Capture -> Surface over the session boundary
(docs/agent-membrane-design-2026-07.md #Renew). This package holds Renew's deterministic
organs; the health *estimator* itself is data-gated on the Strand-A correlation and does
not exist yet -- session_signals.py is the sensor that accrues that correlation dataset.
"""
