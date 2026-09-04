"""Which model a seat runs on -- the pin, and the self-report.

Daniil 2026-09-04, verbatim: "I want to have options to change the model. Something should
display which model is running in discord so I can detect model changes while operating
through discord."

TWO PLANES, DELIBERATELY SEPARATE, because collapsing them would manufacture exactly the
confabulated receipt this house keeps paying for:

  THE PIN (`pin`/`unpin`/`model_flag`) is a REQUEST. It is what we pass as `--model` when we
  launch a seat. We know it because we typed it. Unpinned means we pass nothing and the CLI
  picks -- and in that state we must say "CLI default", never guess a name.

  THE SELF-REPORT (`report`/`running`) is a RECEIPT. A live session stamps the model IT
  believes it is running, from inside itself. Only the session knows; nobody can infer it
  from the outside. A stale or absent report is reported AS stale or absent.

A render that mixes them without labels is the failure mode: the operator asked for this
precisely so a model change cannot happen quietly, and a display that shows a request while
implying a receipt would hide the change it exists to reveal.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
#: The pin. Instance-scoped operator preference; small, and the durable record of his choice.
STORE = ROOT / "state" / "coord" / "seat_model.json"

#: Redis key for a live session's self-report. TTL'd, so a dead session stops claiming.
_REPORT_KEY = "seat:model:{agent}:{session}"
REPORT_TTL_SEC = 900

#: The roster the operator picks from. Full ids are accepted too (see `pin`) -- the vendor
#: ships models faster than we alias them, and our lag must never block his choice.
MODELS: Dict[str, Dict[str, str]] = {
    "fable":  {"id": "claude-fable-5",             "label": "Fable 5"},
    "opus":   {"id": "claude-opus-5",              "label": "Opus 5"},
    "sonnet": {"id": "claude-sonnet-5",            "label": "Sonnet 5"},
    "haiku":  {"id": "claude-haiku-4-5-20251001",  "label": "Haiku 4.5"},
}

DEFAULT_LABEL = "CLI default (unpinned)"


def _label_for(model_id: str) -> str:
    for spec in MODELS.values():
        if spec["id"] == model_id:
            return spec["label"]
    return model_id          # a raw id the roster has not aliased: show it verbatim


def resolve() -> Dict[str, Any]:
    """The pin, or the honest absence of one. NEVER raises -- a broken config file must not
    wedge every spawn (that would turn a preference into an outage)."""
    try:
        raw = json.loads(STORE.read_text(encoding="utf-8"))
        model = str(raw.get("model") or "").strip()
        if not model:
            raise ValueError("no model pinned")
        return {"pinned": True, "model": model, "label": _label_for(model),
                "by": str(raw.get("by") or ""), "at": str(raw.get("at") or "")}
    except Exception:                                                     # noqa: BLE001
        return {"pinned": False, "model": None, "label": DEFAULT_LABEL, "by": "", "at": ""}


def model_flag() -> List[str]:
    """The argv fragment for a launch. Empty when unpinned -- inherit, never guess."""
    st = resolve()
    return ["--model", st["model"]] if st["pinned"] else []


def pin(alias_or_id: str, *, by: str) -> Dict[str, Any]:
    """Pin the model future spawns request. Accepts a roster alias or a full model id."""
    want = str(alias_or_id or "").strip().lower()
    if want in MODELS:
        model = MODELS[want]["id"]
    elif want.startswith("claude-"):
        model = want                      # unaliased vendor id: the operator outranks our roster
    else:
        raise ValueError(
            f"unknown model {alias_or_id!r} -- pick one of: {', '.join(sorted(MODELS))} "
            f"(or pass a full model id like claude-opus-5)")
    STORE.parent.mkdir(parents=True, exist_ok=True)
    rec = {"model": model, "by": str(by or "unknown"),
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    STORE.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return resolve()


def unpin(*, by: str) -> Dict[str, Any]:
    """Return to the CLI default. Recorded as an act, not a deletion."""
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(
        {"model": None, "by": str(by or "unknown"),
         "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1) + "\n",
        encoding="utf-8")
    return resolve()


# --- the self-report plane: what a LIVE session says it is running -------------------------

def _client(c=None):
    """The house's control-bus Redis client -- the SAME accessor incarnation.py uses.
    (First draft of this reached for liveness._ns(), which returns a namespace STRING,
    so every report silently no-opped and the render honestly said nobody had stamped.
    A fail-open writer needs a pin that exercises it with a real fake -- see
    test_report_and_running_round_trip.)"""
    if c is not None:
        return c
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:                                                     # noqa: BLE001
        return None


def report(agent: str, session: str, model: str, *, harness: str = "", c=None) -> bool:
    """A live session stamps the model it believes it runs on. Fail-open (False), because a
    seat that cannot reach Redis must still work -- it just cannot be displayed."""
    cli = _client(c)
    if cli is None or not (agent and session and model):
        return False
    try:
        cli.set(_REPORT_KEY.format(agent=agent, session=str(session)[:8]),
                json.dumps({"model": str(model), "label": _label_for(str(model)),
                            "harness": str(harness or ""), "at": int(time.time())}),
                ex=REPORT_TTL_SEC)
        return True
    except Exception:                                                     # noqa: BLE001
        return False


def running(agent: str = "claude", c=None) -> List[Dict[str, Any]]:
    """Every live session's self-reported model for `agent`. Empty means NOBODY REPORTED --
    which is a different fact from 'nobody is running', and the render must say so."""
    cli = _client(c)
    if cli is None:
        return []
    out: List[Dict[str, Any]] = []
    try:
        pattern = _REPORT_KEY.format(agent=agent, session="*")
        for key in cli.scan_iter(match=pattern) if hasattr(cli, "scan_iter") else []:
            try:
                k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
                raw = cli.get(k)
                if not raw:
                    continue
                rec = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                rec["session"] = k.rsplit(":", 1)[-1]
                rec["age_s"] = max(0, int(time.time()) - int(rec.get("at") or 0))
                out.append(rec)
            except Exception:                                             # noqa: BLE001
                continue
    except Exception:                                                     # noqa: BLE001
        return out
    return sorted(out, key=lambda r: r.get("age_s", 0))


def render(*, with_choices: bool = False, agent: str = "claude") -> str:
    """One Discord-shaped answer. Keeps request and receipt visibly separate."""
    st = resolve()
    if st["pinned"]:
        head = f"**Model pin:** {st['label']} (`{st['model']}`) — pinned"
        if st["by"]:
            head += f" by {st['by']} {st['at']}"
    else:
        head = f"**Model pin:** {DEFAULT_LABEL} — new seats inherit whatever the CLI picks"
    lines = [head]

    live = running(agent)
    if live:
        lines.append("**Running now (each session's own report):**")
        for r in live:
            stale = "  ⚠️ stale" if r.get("age_s", 0) > REPORT_TTL_SEC // 2 else ""
            harness = f" · {r['harness']}" if r.get("harness") else ""
            lines.append(f"  `{r.get('session')}` — {r.get('label')}{harness} "
                         f"(reported {r.get('age_s')}s ago){stale}")
    else:
        lines.append("**Running now:** no session has reported a model. That means nobody "
                     "stamped one — not that nobody is running.")

    if with_choices:
        lines.append("")
        lines.append("`!model` — show this · `!model <name>` — pin · `!model default` — unpin")
        lines.append("Choices: " + " · ".join(
            f"`{a}` ({MODELS[a]['label']})" for a in sorted(MODELS)))
        lines.append("A pin applies to seats launched AFTER it; a running session keeps its "
                     "own model until it is replaced.")
    return "\n".join(lines)
