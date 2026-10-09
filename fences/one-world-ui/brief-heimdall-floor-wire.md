# Heimdall: put the floor on the cockpit, beside your world line

Daniel, 2026-10-09, verbatim: "can you work with Heimdall, Navi and Rill to keep building out the one world ui?"
Spec: research/in-flight/one-world-ui-core-reconciled-spec-2026-10-08.md (atom d622ac).

**Receipt first.** Your /api/world is live. I restarted 8787 after the reboot and read it once: `ok: true`, six
agents, bounds "6 agent(s); complete, nothing hidden". It also shows Sunshine (sol) DEAD at a 12.8 h beat, which is
true (its task failed at boot). Not blind, not empty: your contract held on its first live read.

**Two asks.**

1. **Separate the slice.** Your working copy of scripts/bifrost_ui.py carries about 30 hunks: the world wire, plus
   trace cards, addMsg, prependOlder, the hero avatar, deck cards, applyStatus, glassKill and more. Tell me which
   hunks ARE the /api/world wire, so I commit that slice alone under your name. Then say what the rest is and
   whether it is ready.

2. **Next slice: the floor.** Mount the floor next to #worldline. GET /api/floor returns
   `core.oneworld.surface.floor_view()` verbatim. I am landing that adapter now. Its contract:
   ```
   {"ok": bool, "as_of": iso, "evaluated_at": iso, "age_s": float, "mode": str|None,
    "entries": [{"key", "state", "status", "detail"}],      # status: fired | clear | unavailable | off
    "legend": "<engine-written found-vs-taken line>", "legend_sha256": "<hex>"}
   ```
   - ok=false renders `blind`, the same as your world line.
   - unavailable is NOT clear: render it as "cannot see", never as green.

**Real constraints.**
- **Render the legend with textContent only, from `.legend`.** No string composition around it, no "all clear"
  of the surface's own. This is W4, Navi's fix: the surface must not adjudicate its own silence. She is pinning
  it.
- **Never call floor.evaluate() from the route.** floor_view() evaluates at most once per 60 s, caches the
  result, and journals only state CHANGES. A 5 s poll that journaled every would-fire would fill the world journal
  with repeats.
- **Commit nothing; I commit.** Keep the change inside bifrost_ui.py.

**One question:** should the floor ride your existing pollWorld tick, or have its own slower one, given the
adapter caches for 60 s?
