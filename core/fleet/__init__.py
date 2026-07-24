"""Fleet dispatch -- the structure for calling local models (docs/library/design/20260709_fleet-dispatch-an-intelligent-easy-struc_303d15.md).

roster : the single source of truth (models(), get(tag), select(...), probe_availability()).
caller : the direct one-shot caller (call(tag, prompt, ...) -> text; raises FleetCallError).

The AGENTIC path (a full Claude Code session backed by a model) stays in scripts/local/; the roster
feeds those scripts their model choice. The DIRECT caller here is the new primitive that lets bounded
subtasks run without a whole session.
"""
from core.fleet.caller import FleetCallError, call
from core.fleet.roster import default_host, get, models, probe_availability, select

__all__ = ["models", "get", "select", "probe_availability", "default_host",
           "call", "FleetCallError"]
