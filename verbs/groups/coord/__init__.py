"""verbs.groups.coord -- the read-only scene verbs and the pre-flight.

`orient`, `shadow`, `ground`, `glance` compose what a seat can SEE about itself and its peers
without changing anything; `scout` asks whether a lane is already in flight. All five are pure
readers over `core/` and take their subject from `--agent` or `AKASHIC_AGENT_ID`.
"""
