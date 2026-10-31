"""arsenal.panel.tokens -- the two-step confirm for STOP and RESTART.

THE PROBLEM THIS SOLVES, stated as the situation rather than as a feature. The panel's buttons live on a
phone. A stop button that acts on one tap is a stop button that will eventually act on one accidental
tap, at a moment when nobody is at the PC to undo it. A browser `confirm()` dialog is not a control --
the page can skip it, and the page is the thing that lives on the phone.

So a destructive verb needs a token the CLIENT MUST EARN WITH A SEPARATE ROUND TRIP:

    POST /api/confirm {service, verb}   -> {"token": "...", "expires_in_s": 60}
    POST /api/action  {service, verb, token}

and the token is:

  * SINGLE USE -- consumed on the first matching action, so a replayed request from a browser history
    or a stale tab does nothing;
  * BOUND to one (service, verb) pair -- a token minted for "stop stage-8796" cannot stop the bus
    runners, so a token that leaks is worth one action on one service;
  * SHORT LIVED (60 s default) -- long enough for a thumb, short enough that a token captured from a
    screen recording is already dead;
  * UNPREDICTABLE -- `secrets.token_urlsafe(24)`, never a counter, never derived from the service name;
  * CAPPED -- at most `MAX_OUTSTANDING` live tokens, so a client cannot mint an unbounded set.

WHAT THIS IS NOT: it is not authentication. The panel is bound to loopback and reaches the phone through
an ssh tunnel, and the house has not asked for an identity gate on this surface. The token is a
confirmation gate -- it makes an accidental action deliberate. Saying so plainly matters, because a
control mistaken for a lock is worse than no lock. In the report and in `local/phone-panel.json`'s
schema this is written as "confirm", never as "auth".
"""
from __future__ import annotations

import secrets
import time
from typing import Callable, Dict, Optional, Tuple

#: How long a minted token stays usable.
DEFAULT_TTL_S = 60.0

#: How many live tokens may exist at once. Reached only by a client that mints without acting, which
#: is exactly the behaviour worth bounding.
MAX_OUTSTANDING = 32


class ConfirmTokens:
    """Single-use, bound, expiring confirm tokens. Clock and minter are injectable for the pins."""

    def __init__(self, *, ttl_s: float = DEFAULT_TTL_S, clock: Callable[[], float] = time.time,
                 mint: Optional[Callable[[], str]] = None,
                 max_outstanding: int = MAX_OUTSTANDING) -> None:
        self.ttl_s = float(ttl_s)
        self._clock = clock
        self._mint = mint or (lambda: secrets.token_urlsafe(24))
        self._live: Dict[str, Tuple[str, str, float]] = {}
        self.max_outstanding = int(max_outstanding)

    # ------------------------------------------------------------------------------- public
    def issue(self, service: str, verb: str) -> Tuple[str, float]:
        """Mint a token for one (service, verb). Returns (token, expires_in_s)."""
        self._prune()
        if len(self._live) >= self.max_outstanding:
            raise OverflowError(
                f"{len(self._live)} confirm tokens are already outstanding (cap "
                f"{self.max_outstanding}); use or wait out the ones you have")
        token = str(self._mint())
        self._live[token] = (service, verb, self._clock() + self.ttl_s)
        return token, self.ttl_s

    def consume(self, token: str, service: str, verb: str) -> bool:
        """True only for a live token minted for THIS (service, verb). Always consumes on a match."""
        self._prune()
        entry = self._live.get(str(token))
        if entry is None:
            return False
        token_service, token_verb, expires = entry
        if token_service != service or token_verb != verb:
            return False                      # wrong target: leave it live for its rightful request
        del self._live[token]                 # single use, even if the action then fails
        return self._clock() <= expires

    def live(self) -> int:
        self._prune()
        return len(self._live)

    # ------------------------------------------------------------------------------- private
    def _prune(self) -> None:
        now = self._clock()
        for token, (_, _, expires) in list(self._live.items()):
            if expires < now:
                del self._live[token]
