"""
core.comm -- Bifrost, the agent-to-agent communication layer (the bridge between agent realms:
Claude Code <-> Cursor <-> OpenCode).

B0 lays the transport: ONE Redis-Streams bus (correct canonical port, real per-agent fan-out),
replacing the four fragmented comm layers. See docs/bifrost-plan.md.
"""
