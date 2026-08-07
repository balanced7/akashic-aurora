"""failure_class -- name the cause of a dead ask, and say what to do about it (T202).

Prior art: data4sci's agentic-harness write-up classifies errors by CAUSE and gives each
class its own recovery -- transient retries, tool misuse feeds the error back, missing
information RE-PLANS rather than blind-retrying, policy violations halt. Our redrive was
blind: three attempts on a fixed schedule, whatever the reason the first failed.

MEASURED 2026-08-06 over 336h: 26 dead asks across 12 peers, and they are four different
situations wearing one label --
    deepseek x9    launchable and ATTENDED right now (consumer-side, not transport)
    codex_019f9924 x2, codex_019faa7a x1, codex_root_019fab2d x1  session-suffixed ids
    kimi x3, sol x2, deepseek-review x2, codex_root x1, opus-engineer x1, cursor_grok x1
    claude x2      self-addressed, died while attended
Four right moves, one undifferentiated "DEAD". The caller had to work out which by hand,
thirty minutes later.

THIS MODULE DIAGNOSES. IT CHANGES NO TRANSPORT POLICY, and that boundary was bought
expensively in a fence with deepseek (2026-08-06), which killed the two more ambitious
halves of the original design:

  (1) I proposed a DEAD_INCARNATION class on the claim that a session id is never
      reissued, making a redrive to one PROVABLY futile. That was overclaiming. Orphan
      mail can still be caught: reaper.py's own first line is "a dead seat's unread
      directed mail re-homes, loudly. Never stranded." So the class survives only as
      STALE_INCARNATION -- a ROUTING HINT (the base seat is cheaper and likelier to be
      read) and never a verdict of futility. No recovery string in this module asserts
      that anything can never be answered, and a pin enforces it.

  (2) I wanted to shorten those futile redrives while keeping T197's "preflight never
      gates the send". deepseek: "redrive is still a send" -- skipping one because of a
      classification is gating one decision point later. It is also the same window,
      since the expectation dies when redrives are exhausted, so fewer redrives means a
      shorter late-binding window -- exactly what the law protects, and that law was
      empirically vindicated when an ask to a provably-absent peer settled ANSWERED at
      540.9s. So: pure reader, no sends, no arms, no sweeps, no redrive counts.

What remains is the value: the caller learns in one second which of four situations it is
in and what to do about it. Same shape as T197 -- observe, report, never gate.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

#: Only a trailing session-shaped suffix is an incarnation marker. Same rule and same
#: regex shape as liveness._INCARNATION_SUFFIX (T155), for the same reason: `codex_root`
#: contains an underscore, so "strip the last _segment" would resolve it to `codex`.
_INCARNATION_SUFFIX = re.compile(r"_([0-9a-f]{6,})$", re.I)

CLASSES = ("SEAT_SILENT", "SEAT_DOWN", "STALE_INCARNATION", "UNKNOWN_PEER",
           "UNCLASSIFIED")

RECOVERY: Dict[str, str] = {
    # Attending the whole time and still nothing came back. More transport will not help;
    # the fault is downstream of delivery.
    "SEAT_SILENT": ("the peer was attending and still did not answer -- this is "
                    "consumer-side, not transport: check it is reading the lane the ask "
                    "rode, check for a wedge, or nudge it. Re-asking the same way "
                    "reproduces the same silence"),
    # Down now, and that is a state that ENDS. The 540.9s answer came from exactly here.
    "SEAT_DOWN": ("the seat is real but not attending: launch it (ask --peer <seat> "
                  "--launch) if it is launchable, or leave the ask armed -- a seat that "
                  "comes up later can still answer, and one measurably did at 540.9s"),
    # A routing HINT. Deliberately not a claim about the old address.
    "STALE_INCARNATION": ("this is an incarnation id and its base seat {base} IS "
                          "attending: re-address to {base}, which is cheaper and far "
                          "likelier to be read. The original stays armed"),
    "STALE_INCARNATION_BASE_DOWN": ("this is an incarnation id; its base seat {base} is "
                                    "also down. Address {base} rather than the "
                                    "incarnation -- a session id belongs to one process "
                                    "and the next one will have a different id -- then "
                                    "launch or wait for {base}"),
    "UNKNOWN_PEER": ("no attending seat, no launchable tag, and no base form -- nothing "
                     "here identifies a reader. Check the id, or ask a peer that exists; "
                     "the stateless `ask` needs no seat at all"),
    "UNCLASSIFIED": ("not enough was observed to name a cause -- absence of evidence is "
                     "not evidence of absence. Re-read attendance for this peer"),
}


def base_form(peer: Any) -> Optional[str]:
    """The bare seat behind an incarnation id, or None when there is no suffix.
    `codex_root_019fab2d` -> `codex_root`; `codex_root` -> None."""
    p = str(peer or "")
    bare = _INCARNATION_SUFFIX.sub("", p)
    return bare if bare and bare != p else None


def classify(peer: Any, *, attending: Optional[bool], base_attending: Optional[bool],
             launchable: Optional[bool], known_seat: Optional[bool]) -> Dict[str, Any]:
    """Which of the four situations is this, and what should the caller do?

    PURE -- every observation is supplied by the caller, so the taxonomy is testable
    without a bus and can never silently start probing on a hot path. Returns
    UNCLASSIFIED rather than guessing when the observations are missing.
    """
    name = str(peer or "")
    base = base_form(name)

    if attending is None and base_attending is None and known_seat is None:
        return {"klass": "UNCLASSIFIED", "peer": name, "base": base,
                "recovery": RECOVERY["UNCLASSIFIED"]}

    if attending:
        return {"klass": "SEAT_SILENT", "peer": name, "base": base,
                "recovery": RECOVERY["SEAT_SILENT"]}

    # Not attending under THIS id. Carrying an incarnation suffix is a FACT ABOUT THE ID,
    # true whether or not the base happens to be up -- the first cut required
    # base_attending here, and live testing immediately rendered codex_root_019fab2d as
    # UNKNOWN_PEER, which is both wrong and the most misleading answer available. Whether
    # the base is attending changes the STRENGTH of the advice, never the class.
    if base:
        tail = (RECOVERY["STALE_INCARNATION"] if base_attending
                else RECOVERY["STALE_INCARNATION_BASE_DOWN"])
        return {"klass": "STALE_INCARNATION", "peer": name, "base": base,
                "recovery": tail.format(base=base)}

    # UNKNOWN_PEER asserts NOTHING IDENTIFIES A READER, which is a claim about the world
    # and needs positive evidence. Absence of a launcher tag is not that evidence: kimi,
    # sol and deepseek-review are all real seats with no registry entry, and the first
    # cut called all three UNKNOWN_PEER. So the default for "not attending, cannot prove
    # it never existed" is the weaker, safer SEAT_DOWN.
    if known_seat is False and not launchable:
        return {"klass": "UNKNOWN_PEER", "peer": name, "base": base,
                "recovery": RECOVERY["UNKNOWN_PEER"]}

    return {"klass": "SEAT_DOWN", "peer": name, "base": base,
            "recovery": RECOVERY["SEAT_DOWN"]}
