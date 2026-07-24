"""
core.comm -- Bifrost, the agent-to-agent communication layer (the bridge between agent realms:
Claude Code <-> Cursor <-> OpenCode).

B0 lays the transport: ONE Redis-Streams bus (correct canonical port, real per-agent fan-out),
replacing the four fragmented comm layers. See docs/library/design/20260709_bifrost-the-agent-communication-handoff_2bcfd5.md.
"""
