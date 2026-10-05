"""
core.events -- the cross-agent auto-logger: raw, full-fidelity event capture (Domain).

Slice 1: capture primitive (EventLog on the Ledger). See docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md.

The RAW firehose beneath the narrative spine: every agent's tool calls / file edits /
commands / observations land here as append-only "raw events", which the salient
narrative Beats can point at (event:<stream>:<id>) for timeline drill-down.
"""

from core.events.event_log import (
    CANONICAL_MAXLEN,
    EVENT_KINDS,
    PER_AGENT_MAXLEN,
    RAW_STREAM,
    EventLog,
    capture_event,
    event_ref,
    get_event_log,
    per_agent_stream,
    reset_event_log_singleton,
)
from core.events.event_query import EventQuery, get_event_query

__all__ = [
    "CANONICAL_MAXLEN",
    "EVENT_KINDS",
    "PER_AGENT_MAXLEN",
    "RAW_STREAM",
    "EventLog",
    "EventQuery",
    "capture_event",
    "event_ref",
    "get_event_log",
    "get_event_query",
    "per_agent_stream",
    "reset_event_log_singleton",
]
