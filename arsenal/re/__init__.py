"""arsenal.re — the reverse-engineering arsenal's read-only front door (gap G3).

Reverse engineering in this house follows one rule before anything else: keep
OBSERVATIONS apart from INFERENCES apart from UNKNOWNS (the REA discipline that
Vandor restated in `research/reviewed/reverse-engineering-2026-10-13/`). Every
receipt produced here carries an evidence tag on every claim, and a `blind` field
naming what was NOT searched — a bounded negative stays bounded, never silently
becomes "nothing".

This package ships the first slice: `triage`, the read-only "what is this file"
router. It reads a bounded prefix, identifies the kind, and names which per-format
door to open next. It never executes, unpacks, or trusts a target.

Nothing here registers an MCP door or runs untrusted input. The domain-first fence
(Vandor's house-inventory legal §2) is the standing boundary; this code stays on the
reading side of it.
"""

API = "arsenal.re/v0"

# Evidence tags — the house's words for the REA observation/inference/unknown split.
OBSERVED = "observed"    # a tool/person directly saw it; reproducible from the same bytes
INFERRED = "inferred"    # a detector's guess, with confidence and the observations it rests on
UNKNOWN = "unknown"      # a question we know we have not answered yet

TAGS = (OBSERVED, INFERRED, UNKNOWN)
