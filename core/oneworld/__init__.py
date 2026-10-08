"""The one-world UI core (H9). Spec: atom art_20261008_one-world-ui-core-reconciled-spec_d622ac.

The spine every surface renders through: one authored world-state, N rebuildable projections, no
drift. This package holds the core; the visible surfaces render on top of it.

Named `oneworld`, NOT `world`, on purpose: `core/world.py` already exists and is load-bearing (it
resolves which WORLD -- prod/sandbox -- the process runs in, imported by redis_connection,
agent_cli, snapshot_knowledge and more). A `core/world/` package would shadow that module and break
`from core.world import current` across the repo. The two are unrelated: `core/world.py` is runtime
environment resolution; this is the UI's world-STATE model.

W0 (this slice): the authored journal -- core.oneworld.journal. Later slices add the projection
reader, the bounds-legend primitive, the mode schema, and the floor.
"""
