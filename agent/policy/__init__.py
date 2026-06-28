"""Policy-as-code: one rulebook, many enforcers.

Shared safety rules that the Claude and Cursor hooks both consult, so the rule can
never drift between the two agents (the same no-drift discipline as the MCP/CLI door).
"""
