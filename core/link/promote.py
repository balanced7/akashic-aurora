"""promote -- the local decision whether a quarantined record reaches our bus, and which seat.

Three questions get three answers (RFC #70 §7.6). The daemon answers "is it authentic, and may its
author write?". This module answers "does it reach our live bus?" -- by local policy, never synced
and never settable by a peer. The receiving agent, under its own Trust role, answers "does it make
me do anything?": promoted mail is data with `authority: none`.

The policy lives in `state/link/<link_id>/promote.toml`. The default is `mode = "manual"`: a person
promotes with `aurora link promote` or the console. Narrow automatic rules can be opted into
locally; a rule can never promote `handoff` (manual-only in v1), and no control kind exists on a
link to promote.

Promotion is idempotent by record id: the daemon's store remembers each promotion.
"""

from __future__ import annotations

import contextlib
import re
import tomllib
from typing import TYPE_CHECKING, Any

from core.link.client import Client, state_dir

if TYPE_CHECKING:
    from pathlib import Path

#: Kinds a rule may promote automatically. handoff stays manual-only in v1.
RULE_KINDS = frozenset({"chat", "question", "reply", "note", "completion", "blocker"})

DEFAULT_POLICY = """# promote.toml -- which quarantined records reach this fleet's bus. LOCAL: never synced.
#
# mode = "manual": a person promotes each record (`aurora link promote <record>`, or the console).
# mode = "rules":  the rules below may promote matching records automatically; the rest wait.
mode = "manual"

# A rule matches on kind, and optionally only replies to a record our fleet wrote. `to` names the
# local seat, or "original_sender" for the seat that wrote the record being answered.
# handoff is never promoted by a rule.
#
# [[rules]]
# kind = "reply"
# replies_to_ours = true
# to = "original_sender"
"""


class PromotionRefused(RuntimeError):
    """A promotion that local policy or the record's state does not allow."""


def policy_dir(link_id: str, home: Path | None = None) -> Path:
    return state_dir(home) / link_id


def load_policy(link_id: str, home: Path | None = None) -> dict[str, Any]:
    """The link's promote.toml, or the manual default. A malformed file is manual, loudly."""
    path = policy_dir(link_id, home) / "promote.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"mode": "manual", "rules": []}
    except (OSError, tomllib.TOMLDecodeError) as e:
        return {"mode": "manual", "rules": [], "error": f"{path}: {e}"}
    mode = data.get("mode", "manual")
    rules = [r for r in data.get("rules", []) if isinstance(r, dict) and r.get("kind") in RULE_KINDS]
    return {"mode": mode if mode in ("manual", "rules") else "manual", "rules": rules}


def write_default_policy(link_id: str, home: Path | None = None) -> Path:
    path = policy_dir(link_id, home) / "promote.toml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_POLICY, encoding="utf-8")
    return path


def _our_seat(to: str, our_label: str) -> str | None:
    """`@<our fleet>/<seat>` -> seat. Mail to the whole fleet or link names no seat."""
    m = re.fullmatch(r"@([^/\s]+)/([^/\s]+)", to or "")
    return m.group(2) if m and m.group(1) == our_label else None


def provenance(rec: dict[str, Any], by: str) -> dict[str, Any]:
    """The meta every promoted message carries. `fleet` and `device` come from the daemon's ACL,
    not from anything the sender wrote; `seat_claim` is only a claim."""
    body = rec.get("body") or {}
    return {
        "source": "link",
        "link": rec.get("link"),
        "fleet": rec.get("fleet"),
        "fleet_root": rec.get("fleet_root"),
        "device": rec.get("device"),
        "record_id": rec.get("record_id"),
        "seat_claim": body.get("seat"),
        "verified": True,
        "authority": "none",
        "promoted_by": by,
        "idempotency_key": f"link:{rec.get('record_id')}",
    }


def render(rec: dict[str, Any]) -> str:
    """The bus text: `[remote <fleet>/<seat>] content`, with attachments named."""
    body = rec.get("body") or {}
    text = f"[remote {rec.get('fleet')}/{body.get('seat')}] {body.get('content', '')}"
    blobs = body.get("blobs") or []
    if blobs:
        names = ", ".join(f"{b.get('name')} ({b.get('bytes')} bytes)" for b in blobs)
        text += f"\n[attachments: {names} -- `aurora link blob {rec.get('record_id', '')[:12]} <name>`]"
    return text


def promote(
    client: Client,
    link: str,
    record_id: str,
    *,
    by: str,
    to: str | None = None,
    again: bool = False,
    bus: Any | None = None,
) -> dict[str, Any]:
    """Put one quarantined record on the bus, once. Returns what happened."""
    status = client.call("link.status", link=link)
    link_id = status["link"]
    our_label = next((m["label"] for m in status["members"] if m.get("us")), "")
    rec = client.call("record.get", link=link_id, record_id=record_id)
    rec["link"] = link_id
    if rec.get("status") != "admitted":
        raise PromotionRefused(f"record is {rec.get('status')}: only admitted mail from another fleet is promoted")
    if rec.get("promoted") and not again:
        return {"promoted": False, "already": rec["promoted"], "record_id": record_id}
    body = rec.get("body") or {}
    seat = to or _our_seat(str(body.get("to", "")), our_label)
    if not seat:
        raise PromotionRefused(
            f"the record is addressed to {body.get('to') or 'the whole link'}: say which seat with --to"
        )
    claimed = client.call("promotion.record", link=link_id, record_id=record_id, seat=seat, by=by)
    if not claimed.get("first") and not again:
        return {"promoted": False, "already": True, "record_id": record_id}
    if bus is None:
        from core.comm.bus import Bus

        bus = Bus(f"link:{rec.get('fleet')}")
    mid = bus.send(seat, str(body.get("kind", "chat")), render(rec), meta=provenance(rec, by))
    if not mid:
        raise PromotionRefused(
            "recorded as promoted, but the bus did not take it (offline?): rerun with --again once it is up"
        )
    return {"promoted": True, "record_id": record_id, "seat": seat, "bus_id": mid}


def _our_root(client: Client, link_id: str) -> str:
    status = client.call("link.status", link=link_id)
    return next((m["root"] for m in status["members"] if m.get("us")), "")


def apply_rules(
    client: Client, events: list[dict[str, Any]], bus: Any | None = None, home: Path | None = None
) -> list[dict[str, Any]]:
    """Promote what a link's local rules allow; leave everything else in quarantine."""
    done: list[dict[str, Any]] = []
    policies: dict[str, dict[str, Any]] = {}
    for e in events:
        link_id = str(e.get("link"))
        policy = policies.setdefault(link_id, load_policy(link_id, home))
        if policy["mode"] != "rules":
            continue
        body = e.get("body") or {}
        kind = str(body.get("kind", ""))
        for rule in policy["rules"]:
            if rule.get("kind") != kind or kind not in RULE_KINDS:
                continue
            seat = rule.get("to")
            if rule.get("replies_to_ours") or seat == "original_sender":
                orig = body.get("reply_to")
                if not orig:
                    continue
                try:
                    o = client.call("record.get", link=link_id, record_id=orig)
                except Exception:  # noqa: BLE001  # an unknown original is simply not ours
                    continue
                # "Ours" means written by our own fleet, and real mail: never another fleet's ack
                # (a receipt), whose seat field that fleet chose itself.
                o_body = o.get("body") or {}
                if (
                    o.get("status") != "own"
                    or o_body.get("kind") == "ack"
                    or o.get("fleet_root") != _our_root(client, link_id)
                ):
                    continue
                if seat == "original_sender":
                    seat = (o.get("body") or {}).get("seat")
            if not seat:
                continue
            with contextlib.suppress(PromotionRefused):
                done.append(promote(client, link_id, str(e["record_id"]), by=f"rule:{kind}", to=str(seat), bus=bus))
            break
    return done
