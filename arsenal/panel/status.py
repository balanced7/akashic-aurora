"""arsenal.panel.status -- the ONE document the phone renders.

`GET /api/status` returns this, and the PWA renders nothing that is not in it. That constraint is
deliberate: a page that composes its own state from several endpoints will one day show green from one
answer and red from another, and the person reading it is holding a phone in another room and cannot
check. One document, one timestamp, one verdict.

THE SCHEMA (pinned by tests/test_phone_panel.py -- changed only with the pin):

    generated        ISO local time this document was built
    epoch            seconds since the epoch, for the page's "as of" line
    version          the API version string ("1")
    panel            {port, pid, host, agent, session, confirm_ttl_s, audit}
    link             the four things Daniel needs to know before anything else:
                       tunnel   -- the PhoneLink `ssh -R` forward is up (UNKNOWN if not measurable)
                       tailnet  -- the phone answers on its tailnet address
                       gateway  -- the Discord gateway process row
                       listener -- this seat's wake listener
                     plus `verdict` (the reachability verb's own one-line answer)
    reachability     the phase-3 verb's JSON, VERBATIM -- the panel reads it, it does not restate it
    services         one row per actionable service
    status_only      the ones the house rule says may be watched and never touched
    video            Apollo's state and the Artemis deep link (declared, not guessed)
    groups           render order, so the page never invents an order
    audit_tail       the last few decisions, newest last

EVERY STATE IS TRI-STATE: UP / DOWN / UNKNOWN, and the page's colour map is green / red / amber. There
is no fourth state and no coercion: UNKNOWN never renders as DOWN, because on this screen UNKNOWN means
"the panel could not look", which is a different sentence from "it is dead".
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

from . import probe as probe_mod
from .probe import DOWN, UNKNOWN, UP

#: UNKNOWN is amber on purpose: it asks a question ("why could the panel not look?") rather than
#: declaring an outage.
COLOURS = {UP: "green", DOWN: "red", UNKNOWN: "amber"}

#: Where a service's row sits on the page, in order. Declared once here so the page never invents one.
GROUP_ORDER = ("link", "engine", "stage", "bus", "log", "lights", "watch", "video", "services")

#: How long a reachability report is reused. The verb reads Redis streams and probes the phone, so the
#: page polling every few seconds must not multiply that work; five seconds is invisible to a thumb.
REACHABILITY_TTL_S = 5.0


class ReachabilityCache:
    """Call the phase-3 verb at most once per TTL, and never raise."""

    def __init__(self, agent: str, session: str = "",
                 fetch: Optional[Callable[[str, str], Dict[str, Any]]] = None,
                 ttl_s: float = REACHABILITY_TTL_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.agent = agent
        self.session = session
        self._fetch = fetch or _real_fetch
        self._ttl = ttl_s
        self._clock = clock
        self._at = -1e9
        self._doc: Dict[str, Any] = {}
        self._why = ""

    def get(self) -> Dict[str, Any]:
        now = self._clock()
        if now - self._at < self._ttl and self._doc:
            return self._doc
        try:
            self._doc = self._fetch(self.agent, self.session) or {}
            self._why = ""
        except Exception as exc:
            # Keep the LAST good document but say so: a stale screen that does not admit it is stale
            # is the failure this house keeps paying for.
            self._why = f"{type(exc).__name__}: {exc}"
            self._doc = dict(self._doc)
            self._doc.setdefault("rungs", {})
            self._doc["_stale"] = True
            self._doc["_why"] = self._why
        self._at = now
        return self._doc


def _real_fetch(agent: str, session: str) -> Dict[str, Any]:
    from core.comm import reachability
    return reachability.report(agent, session)


def link_block(rep: Dict[str, Any]) -> Dict[str, Any]:
    """The four rungs, flattened for the link card. Unknowns keep their reason."""
    rungs = rep.get("rungs") or {}
    gw = rungs.get("gateway") or {}
    wake = rungs.get("wake_listener") or {}
    phone = rungs.get("phone_tunnel") or {}
    host = phone.get("tailnet_host")
    port = phone.get("tailnet_port")
    answers = phone.get("phone_answers")
    out = {
        "tunnel": {"state": phone.get("state", UNKNOWN), "why": phone.get("why", ""),
                   "forwards": len(phone.get("forwards") or [])},
        "tailnet": {"state": (UP if answers else DOWN) if answers is not None else UNKNOWN,
                    "address": f"{host}:{port}" if host and port else "",
                    "phone_answers": answers},
        "gateway": {"state": gw.get("state", UNKNOWN), "why": gw.get("why", ""),
                    "pid": gw.get("pid"), "age_s": gw.get("age_s"),
                    "worktree": gw.get("worktree", "")},
        "listener": {"state": wake.get("state", UNKNOWN), "why": wake.get("why", ""),
                     "seats": len(wake.get("seats") or [])},
        "verdict": (rep.get("verdict") or {}).get("line", ""),
    }
    if rep.get("_stale"):
        out["stale"] = True
        out["why"] = rep.get("_why", "")
    colours = {k: COLOURS.get(v.get("state"), "amber")
               for k, v in out.items() if isinstance(v, dict)}
    out["colours"] = colours
    return out


def service_row(spec, prober: probe_mod.Prober) -> Dict[str, Any]:
    """One actionable service, probed now."""
    pr = prober.probe(spec)
    state = pr.get("state", UNKNOWN)
    row: Dict[str, Any] = {
        "id": spec.id, "label": spec.label, "group": spec.group,
        "state": state, "colour": COLOURS.get(state, "amber"),
        "why": pr.get("why", ""),
        "actions": list(spec.allowed_verbs()),
        "confirm": [v for v in spec.allowed_verbs() if spec.needs_confirm(v)],
        "detail": pr.get("detail") or {},
    }
    if spec.log:
        row["log_tail"] = probe_mod.tail(spec.log)
        row["log_path"] = spec.log
    return row


def status_only_row(spec, prober: probe_mod.Prober) -> Dict[str, Any]:
    pr = prober.probe(spec)
    state = pr.get("state", UNKNOWN)
    return {"id": spec.id, "label": spec.label, "group": spec.group,
            "state": state, "colour": COLOURS.get(state, "amber"),
            "why": pr.get("why", ""),
            "why_no_actions": spec.why_no_actions,
            "detail": pr.get("detail") or {}}


def video_block(specs: Dict[str, Any], rows: Dict[str, Dict[str, Any]],
                video_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Apollo's live state and the Artemis deep link.

    APOLLO IS REPORTED FROM ITS SPEC'S PROBE, so a PC without it says so instead of showing an
    optimistic green. THE DEEP LINK IS DECLARED (`local/phone-panel.json` -> video.artemis), not
    invented here: an app's URL scheme is a fact about that app on that phone, and a guess would ship a
    button that silently does nothing -- which is worse than a button that says "not configured"."""
    meta = video_meta or {}
    apollo = next((r for r in rows.values() if r.get("group") == "video"), None)
    artemis = meta.get("artemis") or {}
    return {
        "apollo": apollo or {"id": "apollo", "label": "Apollo", "state": UNKNOWN,
                             "colour": "amber", "why": "no Apollo service is declared in the "
                                                       "allowlist for this PC"},
        "link": meta.get("apollo_web") or {},
        "artemis": {"label": artemis.get("label", "Artemis"),
                    "deep_link": artemis.get("deep_link", ""),
                    "why": artemis.get("why",
                                       "no Artemis deep link is declared in local/phone-panel.json"),
                    "configured": bool(artemis.get("deep_link"))},
    }


def build(specs: Dict[str, Any],
          prober: probe_mod.Prober,
          *,
          port: int,
          host: str = "127.0.0.1",
          agent: str = "",
          session: str = "",
          version: str = "1",
          confirm_ttl_s: float = 60.0,
          audit_tail: Optional[List[Dict[str, Any]]] = None,
          audit_path: str = "",
          audit_error: str = "",
          reach: Optional[ReachabilityCache] = None,
          video_meta: Optional[Dict[str, Any]] = None,
          extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the whole document. Never raises: a broken rung becomes an UNKNOWN row with its reason."""
    now = time.time()
    services: List[Dict[str, Any]] = []
    status_only: List[Dict[str, Any]] = []
    rows: Dict[str, Dict[str, Any]] = {}
    for spec in specs.values():
        try:
            row = status_only_row(spec, prober) if spec.status_only else service_row(spec, prober)
        except Exception as exc:                                  # one bad row must not blank the page
            row = {"id": spec.id, "label": spec.label, "group": spec.group, "state": UNKNOWN,
                   "colour": "amber", "actions": [], "confirm": [],
                   "why": f"the row could not be built: {type(exc).__name__}: {exc}"}
        rows[spec.id] = row
        (status_only if spec.status_only else services).append(row)

    rep: Dict[str, Any] = {}
    if reach is not None:
        try:
            rep = reach.get()
        except Exception as exc:
            rep = {"_why": f"{type(exc).__name__}: {exc}", "rungs": {}}
    groups = [g for g in GROUP_ORDER
              if any(r.get("group") == g for r in services + status_only)]
    groups += sorted({r.get("group") for r in services + status_only} - set(groups))

    doc: Dict[str, Any] = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "epoch": round(now, 3),
        "version": version,
        "panel": {"port": port, "host": host, "pid": os.getpid(), "agent": agent,
                  "session": session, "confirm_ttl_s": confirm_ttl_s,
                  "audit": audit_path, "audit_error": audit_error},
        "link": link_block(rep),
        "reachability": rep or {"state": UNKNOWN,
                                "why": "the reachability verb was not called for this document"},
        "services": services,
        "status_only": status_only,
        "video": video_block(specs, rows, video_meta),
        "groups": groups,
    }
    if audit_tail is not None:
        doc["audit_tail"] = audit_tail
    if extra:
        doc.update(extra)
    return doc
