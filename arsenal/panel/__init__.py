"""arsenal.panel -- the phone control panel: the PC-side API the S24 drives, and the PWA it serves.

WHY THIS EXISTS (Daniel, 2026-10-31, verbatim): "can we build a management app for our connections and
services on my phone? This way we can spin daemons up and down, restore connection, set up video feed
etc." His ruling on the shape: a webapp first, and video is Apollo + Artemis.

THE REASON IT LIVES ON THE PHONE, from the day the ask was made: the phone's Tailscale had been offline
for 18 h, so the PC could not reach it. Anything whose job is to RESTORE THE LINK has to run on the side
that is still up. That is `scripts/phone/` (the Termux:Widget buttons), not this package. This package is
the other half: what the phone calls once the link is back.

THE THREE PARTS, and where each one lives:

  1. THE LINK RESTORER, phone side -- `scripts/phone/link-up.sh`, `link-down.sh`, `link-status.sh`,
     installed as Termux:Widget buttons. It starts the phone's own sshd and opens Tailscale, so the PC
     can find it again.
  2. THE CONTROL API (this package) -- stdlib `http.server` on 127.0.0.1 only, reached from the phone
     through one extra `-R` on the PhoneLink watcher's existing tunnel. NEVER published to the tailnet.
  3. THE WEB APP -- `page.html` + `manifest.webmanifest` + `sw.js`, served by (2), installable to the
     phone's home screen, dark, thumb-sized.

THE ONE RULE THAT SHAPES EVERY OTHER DECISION HERE: the API can start and stop processes on Daniel's
desktop, so it is not a shell with a web form in front of it. Actions are chosen from an ALLOWLIST of
frozen argv vectors declared in `local/phone-panel.json`; the request carries an id and a verb and
nothing else; `subprocess` is called with a list and `shell=False`, so no request byte can ever reach a
command interpreter. `tests/test_phone_panel.py` pins that refusal.

Deliberately NOT here: instance facts. Which services exist, their argv, their ports and the phone's
address are `local/phone-panel.json`, because a fork must be able to take this package without being
told who we are (the Local-in-Core rule from the modular-core detangle).
"""
from __future__ import annotations

from .spec import CONFIRM_VERBS, VERBS, ServiceSpec, SpecError, load_specs

__all__ = ["VERBS", "CONFIRM_VERBS", "ServiceSpec", "SpecError", "load_specs"]
