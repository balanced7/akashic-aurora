"""The touch-stream instrument, and the per-location scene behind it.

`context --stats` meters what the touch stream costs; `context <anchor>` asks the scene what is
true about a location. One verb at two altitudes on purpose: splitting them would mint a second
name for one surface.
"""
from __future__ import annotations

import os

from verbs.registry import verb


@verb(local=True, door_notes="CLI only; core.events.touch (+ core.coord.scene for the anchor mode). DECLARED local=True: its stats path defaults the subject to a hardcoded seat name, a Local default living in Core -- which is what the local flag exists to make visible.")
def cmd_context(args) -> int:
    """W0.4: the instrument over the touch stream. `context --stats` is the first mode of the
    context door; the anchor modes are W0.5/W0.6 and are not built yet.

    It exists because W0.2 put a new record on the hot path of every seat and shipping that
    without a meter would ask the house to trust a cost nobody measured. The reconciliation gates
    Wave 1 on 24 h of this number, which is why the verb landed the same night the emit did.
    """
    import json as _json
    import time as _time

    # W0.5/W0.6: an anchor asks the scene; --stats meters the stream. One verb, because they are
    # the same door at two altitudes -- "what is true about this location" and "what is this
    # organ costing" -- and splitting them would mint a second name for one surface.
    anchor = getattr(args, "anchor", None)
    if anchor:
        from core.coord import scene as _scene
        from core.events import touch as _touch
        try:
            sc = _scene.build(anchor, subject=(os.getenv("AKASHIC_AGENT_ID") or "claude"),
                              roots=_touch.default_roots(),
                              level=int(getattr(args, "level", None) or 1))
        except Exception as e:                                            # noqa: BLE001
            print(f"ERROR: {e}")
            return 1
        print(_json.dumps(sc, indent=2, default=str) if getattr(args, "json", False)
              else _scene.render(sc))
        return 0

    from core.events import touch_stats as _ts
    window = float(getattr(args, "hours", None) or 24)
    try:
        from core.comm.bus import Bus
        c = Bus("claude")._client
        rows = c.xrange("events:raw", min="-", max="+", count=int(getattr(args, "limit", None) or 20000))
    except Exception as e:                                                # noqa: BLE001
        print(f"ERROR: could not read events:raw ({type(e).__name__}: {e})")
        return 1
    recs = []
    for _mid, f in rows:
        try:
            raw = next(iter(f.values()))
            recs.append(_json.loads(raw.decode() if isinstance(raw, bytes) else str(raw)))
        except Exception:                                                 # noqa: BLE001
            continue          # one unreadable row is not a reason to report nothing
    drops = 0
    try:
        from core.events import touch as _touch
        drops = _touch.drops()
    except Exception:                                                     # noqa: BLE001
        pass
    rep = _ts.compute(recs, now=_time.time(), window_h=window, drops=drops)
    if getattr(args, "json", False):
        print(_json.dumps(rep, indent=2, default=str))
    else:
        print(_ts.render(rep))
    return 0
