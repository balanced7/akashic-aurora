"""arsenal.keylab.webmount -- the hook that puts the KeyLab on the VFX Bench without editing the bench's code.

The VFX Bench (scripts/vfx.html, served at /vfx by scripts/bifrost_ui.py on :8787) drives AgentAvatar's PARAMS and
DIALS from its own sliders. arsenal/web/lib/keylab-hosts.js knows how to drive the same things from the KeyLab
(faders with pickup, fine knobs, learn on touch, presets on pads, a chord root on the tint's hue), and
arsenal/web/lib/keylab-mount.js mounts it on whatever page imports it. The Bifrost console does not serve
arsenal/web/lib/ today, so the bench cannot import it. This module is the whole server-side half: a pure function that
maps a /keylab/<file>.js request to the one allowed file, so the console's change is three lines and stays reviewable.

scripts/bifrost_ui.py belongs to DeepSeek; this file does not edit it. THE INTEGRATION SNIPPET (to apply there):

    # --- KeyLab on the VFX Bench (claude/Vandor 2026-10-23; arsenal/keylab/webmount.py) ---
    # in do_GET, beside the other /vfx routes, before the 404:
        from arsenal.keylab.webmount import keylab_route
        hit = keylab_route(path)
        if hit:
            return self._static(hit, "application/javascript")

and one line at the very end of scripts/vfx.html (the file has no </body>; the line goes after the bench's last
</script>, so `av` and the bench's functions exist when the module runs; the mount also waits for them itself):

    <script type="module" src="/keylab/keylab-mount.js"></script>

What it then does on /vfx: a folded "KeyLab - vfx-bench" panel bottom right. Faders 1-8 drive subdivision, tile gap,
shell thickness, sphere->cube, torus, spin, breathe and saturation (each catching its value when it passes it), knobs
1-8 trim them, fader 9 is brightness, knob 9 and the chord root turn the tint's hue; the bench's saved presets are the
scenes on pads 1-8 and the dial; pads 9-12 hold snapshots. Every slider stays live for the mouse, and the bench's
hand-off row (emit) and presets keep working, because the mount sets the same av.target / av.cur fields its sliders set.
"""
from __future__ import annotations

import re
from typing import Optional

#: The files the console may serve under /keylab/, and nothing else: the mount, what it imports, and the param schema
#: the client formats values with. Each maps to its repo-relative path.
ALLOWED = {
    "keylab-mount.js": "arsenal/web/lib/keylab-mount.js",
    "keylab-hosts.js": "arsenal/web/lib/keylab-hosts.js",
    "keylab-client.js": "arsenal/web/lib/keylab-client.js",
    "keylab-desk.js": "arsenal/web/lib/keylab-desk.js",
    "params.js": "arsenal/web/lib/params.js",
}
_ROUTE = re.compile(r"^/keylab/([a-z0-9-]+\.js)$")


def keylab_route(path: str) -> Optional[str]:
    """The repo-relative file for a /keylab/<name>.js request path (query already stripped), or None.

    Only the names in ALLOWED: no directories, no traversal, no other extension, no case games."""
    if not isinstance(path, str):
        return None
    m = _ROUTE.match(path)
    if not m:
        return None
    return ALLOWED.get(m.group(1))
