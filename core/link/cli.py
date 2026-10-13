"""cli -- `aurora link <action>`: the operator's door to fleet links.

Each action is one call (or a few) to aurora-linkd. Nothing here decides anything about keys,
membership or records: the daemon does, and refuses what it must. What stays here is the part
that touches people and agents: wording, files, the confirm before a promotion.

Every action and every error prints through core/axi: TOON for an agent, a layout for a person.
`--json` prints the daemon's answer as it came. The exceptions are on purpose: a recovery phrase
is shown once to whoever ran init, and `promote` asks its question on a terminal in plain words.

Promotion is a person's decision by default (ADR 0008, RFC #70 §7.6), so `promote` asks for a
confirmation on a terminal unless `--yes` is given, and the MCP door has no promote at all.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

from core.axi import out as axi
from core.link import export, promote, quarantine
from core.link.client import MISSING, Client, LinkdMissing, LinkRpcError, connect
from core.link.health import takeover_hint

ACTIONS = (
    "init",
    "whoami",
    "renew",
    "cert",
    "certify",
    "create",
    "list",
    "status",
    "invite",
    "join",
    "accept",
    "decline",
    "verify",
    "remove-member",
    "remove-device",
    "add-device",
    "rotate-key",
    "revoke-invite",
    "set-role",
    "leave",
    "handoff",
    "takeover",
    "serve",
    "mailbox",
    "sync",
    "peer",
    "inbox",
    "show",
    "promote",
    "blob",
    "send",
    "export",
    "import",
    "policy",
    "rebuild",
    "import-legacy",
    "relay-config",
)

#: Actions that need the daemon's network (`aurora link serve`, or a one-shot networked child).
NETWORKED = frozenset({"join", "sync"})


class UsageError(RuntimeError):
    pass


def _need(args: Any, n: int, usage: str) -> list[str]:
    rest = list(getattr(args, "args", None) or [])
    if len(rest) < n:
        raise UsageError(f"usage: aurora link {usage}")
    return rest


def _ttl(text: str | None) -> int | None:
    if not text:
        return None
    m = re.fullmatch(r"(\d+)([smhd]?)", text.strip())
    if not m:
        raise UsageError(f"--ttl takes a number with s, m, h or d (got {text!r})")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def _when(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ts)))
    except (TypeError, ValueError, OverflowError):
        return "-"


def _cli() -> str:
    """The CLI as a printed command names it: `aurora` installed, else `<launcher> agent_cli.py`."""
    from core.paths import cli_command

    return cli_command()


def _json(args: Any, data: Any) -> bool:
    """`--json` prints the daemon's answer as it came, for scripts; True when it did."""
    if getattr(args, "json", False):
        print(json.dumps(data, indent=1, default=str))
        return True
    return False


def _read_phrase(args: Any) -> str | None:
    if getattr(args, "phrase_stdin", False):
        return sys.stdin.readline().strip()
    return None


def _passphrase(args: Any) -> str | None:
    var = getattr(args, "passphrase_env", None)
    return os.environ.get(var) if var else None


# --------------------------------------------------------------------------------------- identity


def do_init(c: Client, args: Any) -> int:
    out = c.call(
        "identity.init",
        phrase=_read_phrase(args),
        label=getattr(args, "label", None),
        passphrase=_passphrase(args),
        xwing=not getattr(args, "no_xwing", False),
    )
    if _json(args, out):
        return 0
    doc: dict[str, Any] = {
        "device": out["device"][:16],
        "fleet_root": out["root"][:16],
        "fingerprint": out["fingerprint"],
        "root_kept": "yes, sealed under your passphrase"
        if out["root_stored"]
        else "no: the phrase re-derives it when needed",
    }
    # The phrase is printed once, to whoever ran init, on purpose: it is the only copy of the
    # fleet root that leaves the daemon. It is not repeated anywhere else.
    if out.get("phrase"):
        doc["recovery_phrase"] = out["phrase"]
        doc["warning"] = "RECOVERY PHRASE -- shown once. Write it down and keep it offline. It is the fleet root"

    def human(console, d):
        axi.render_human(console, {k: v for k, v in d.items() if k not in ("recovery_phrase", "warning")})
        if d.get("recovery_phrase"):
            from rich.panel import Panel

            console.print()
            console.print(
                Panel(
                    f"[bold]{axi._esc(d['recovery_phrase'])}[/]",
                    title="[bold red]RECOVERY PHRASE -- shown once[/]",
                    subtitle="write it down and keep it offline: it is the fleet root",
                    border_style="red",
                    padding=(1, 2),
                )
            )

    cli = _cli()
    return axi.emit(
        doc, hints=[f"{cli} link create <name>", f"{cli} link join <code>"], human=human, title="Fleet identity created"
    )


def do_whoami(c: Client, args: Any) -> int:
    out = c.call("identity.status")
    if getattr(args, "json", False):
        print(json.dumps(out, indent=1, default=str))
        return 0 if out.get("initialized") else 1
    if not out.get("initialized"):
        return axi.fail(
            "no fleet identity on this install yet", code="NO_IDENTITY", hints=[f"{_cli()} link init --label <name>"]
        )
    doc = {
        "device": out["device"][:16],
        "label": out["label"],
        "fingerprint": out["fingerprint"],
        "cert_expires": _when(out["cert_expires"]),
        "renew_soon": bool(out["needs_renewal"]),
    }
    hints = [f"{_cli()} link renew"] if out["needs_renewal"] else []  # a detail view answers itself
    return axi.emit(doc, hints=hints, title="Fleet identity")


def do_renew(c: Client, args: Any) -> int:
    out = c.call("identity.renew", phrase=_read_phrase(args), passphrase=_passphrase(args))
    if _json(args, out):
        return 0
    doc = {"cert_expires": _when(out["cert_expires"]), "announced_in_links": len(out["links"])}
    return axi.emit(doc, title="Certificate renewed")  # a confirmation answers itself


def do_cert(c: Client, args: Any) -> int:
    cert = c.call("identity.status")["cert"]
    text = json.dumps(cert, indent=1)
    target = getattr(args, "out", None)
    if target:
        Path(target).write_text(text + "\n", encoding="utf-8")
    if getattr(args, "json", False):  # --json has always printed the certificate itself, or the line
        print(
            f"wrote this device's certificate to {target}: hand it to a device already in the link" if target else text
        )
        return 0
    doc: dict[str, Any] = {
        "device": str(cert.get("device", ""))[:16],
        "label": cert.get("label"),
        "valid_until": _when(cert.get("not_after")),
        "post_quantum": bool(cert.get("xwing")),
    }
    if target:
        doc["wrote"] = target
        doc["next"] = "hand the file to a device already in the link; it runs add-device with it"
        return axi.emit(doc, hints=[f"{_cli()} link add-device <link> {target}"], title="Device certificate")
    # Without --out the certificate itself is the output, in either mode: `link cert > cert.json`
    # must keep writing a valid certificate, and a pipe is agent mode. A person at a terminal also
    # gets a summary above it.
    if not axi.is_agent():

        def human(console, d):
            for k in ("device", "label", "valid_until", "post_quantum"):
                console.print(f"[dim]{k:<13}[/]{axi._esc(str(d[k]))}")
            console.print(axi._esc(text), soft_wrap=True)

        return axi.emit(doc, hints=[f"{_cli()} link cert --out cert.json"], human=human, title="Device certificate")
    print(text)
    return 0


def do_certify(c: Client, args: Any) -> int:
    (path,) = _need(args, 1, "certify <cert.json>")[:1]
    cert = json.loads(Path(path).read_text(encoding="utf-8"))
    out = c.call("identity.certify", cert=cert)
    if _json(args, out):
        return 0
    return axi.emit({"device": out["device"][:16], "recorded": "a device of this fleet"}, title="Device certified")


# ------------------------------------------------------------------------------------------ links


def do_create(c: Client, args: Any) -> int:
    (name,) = _need(args, 1, "create <name>")[:1]
    kinds = [k.strip() for k in args.kinds.split(",")] if getattr(args, "kinds", None) else None
    out = c.call(
        "link.create",
        name=name,
        label=getattr(args, "label", None),
        kinds=kinds,
        retention_days=getattr(args, "retention_days", None),
    )
    promote.write_default_policy(out["link"])
    export.write_default_policy(out["link"])
    if _json(args, out):
        return 0
    doc = {"name": out["name"], "link": out["link"], "fingerprint": out["fingerprint"], "role": "owner"}
    cli = _cli()
    hints = [f"{cli} link invite {out['name']}", f"{cli} link status {out['name']}"]
    return axi.emit(doc, hints=hints, title="Link created")


def do_list(c: Client, args: Any) -> int:
    rows = c.call("link.list") or []
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=1, default=str))
        return 0
    cli = _cli()
    if not rows:  # AXI section 5: the zero is the answer
        return axi.emit(
            {"total": 0, "links": []},
            hints=[f"{cli} link create <name>", f"{cli} link join <code>"],
            title="Links",
        )
    table = []
    for r in rows:
        row = {"name": r["name"], "link": r["link"][:16], "role": r["role"] or None, "members": r["members"]}
        row["epoch"] = r["epoch"]
        if any(x["alarms"] for x in rows):  # a column only when some link has alarms
            row["alarms"] = r["alarms"]
        table.append(row)
    alarmed = next((r["name"] for r in rows if r["alarms"]), None)
    hints = [f"{cli} link status {alarmed or (rows[0]['name'] if len(rows) == 1 else '<name>')}"]
    hints.append(f"{cli} link invite {rows[0]['name'] if len(rows) == 1 else '<name>'}")
    return axi.emit({"total": len(rows), "links": table}, hints=hints, title=f"Links · {len(rows)}")


def _sequencer_text(s: dict[str, Any]) -> list[str]:
    """Who orders the link's ACL chain, a handoff waiting for its target, and an equivocation."""
    lines = []
    seq = s.get("sequencer") or {}
    if seq:
        who = "this device" if seq.get("me") else f"{seq.get('label') or '?'} ({str(seq.get('device', ''))[:16]})"
        lines.append(f"  sequencer {who}, term {seq.get('term')}")
        if seq.get("handoff_to"):
            lines.append(
                f"  HANDOFF to {seq.get('next_label') or '?'} ({str(seq['handoff_to'])[:16]}): "
                "membership changes wait until it starts term "
                f"{seq.get('next_term')}"
            )
    eq = s.get("equivocation")
    if eq:
        lines.append(
            f"  EQUIVOCATION: the sequencer signed two entries at term {eq['term']} seq {eq['seq']}; "
            f"the link is halted at seq {eq['seq'] - 1} (no new mail is sealed; this device grants only what "
            f"both its chain tip and seq {eq['seq'] - 1} grant) until the owner runs {takeover_hint(s)}"
        )
    for p in s.get("proposals", []):
        if p.get("status") == "refused":
            lines.append(f"  proposal {p['id'][:16]} {p['kind']} REFUSED by the sequencer: {p.get('why')}")
        else:
            lines.append(f"  proposal {p['id'][:16]} {p['kind']} waits for the sequencer since {_when(p.get('at'))}")
    return lines


def _status_text(s: dict[str, Any]) -> str:
    lines = [
        f"{s['name']}  {s['link']}",
        f"  epoch {s['epoch']}  our role {s['my_role']}  acl entries {s['acl_entries']}",
    ]
    lines.extend(_sequencer_text(s))
    if s.get("rotation_due"):
        lines.append("  ROTATION DUE: the sequencer appends it; after 1 h it takes one from any device holding the key")
    for m in s["members"]:
        flag = " (us)" if m["us"] else ""
        state = "removed" if m["removed"] else "pending" if m["pending"] else m["role"]
        verified = "" if m["us"] else ("  verified" if m["verified"] else "  NOT VERIFIED: aurora link verify")
        lines.append(f"  {m['label']}{flag}: {state}{verified}")
        for d in m["devices"]:
            seen = _when(d["last_contact"]) if d.get("last_contact") else "never"
            extra = (
                " REMOVED"
                if d["removed"]
                else " FROZEN"
                if d.get("frozen")
                else " CERT EXPIRED"
                if d["cert_expired"]
                else ""
            )
            lines.append(f"    {d['label']:<14} {d['device'][:16]} head {d['head']:<5} last contact {seen}{extra}")
    lines.extend(
        f"  pending join {p['join'][:16]} from {p['label']}{' (needs: aurora link accept)' if p['needs_approval'] else ''}"
        for p in s.get("pending_joins", [])
    )
    if s.get("live_sessions"):
        lines.append(f"  live sessions: {len(s['live_sessions'])}")
    lines.append(f"  quarantine: {s['quarantine_unpromoted']} unpromoted")
    lines.extend(
        f"  sent #{r['seq']} {r['kind']}: {r['receipts'] or 'not yet delivered'}" for r in s.get("sent", [])[:5]
    )
    lines.extend(f"  ALARM {a['kind']}: {a['author'][:16]} {a['detail']}" for a in s.get("alarms", []))
    return "\n".join(lines)


def _status_doc(s: dict[str, Any]) -> dict[str, Any]:
    """One link's status as data: scalars first, then members and devices as rows, and every
    condition that needs a person (handoff, equivocation, proposals, rotation) as a notice."""
    doc: dict[str, Any] = {
        "name": s["name"],
        "link": s["link"],
        "epoch": s["epoch"],
        "role": s["my_role"],
        "acl_entries": s["acl_entries"],
    }
    seq = s.get("sequencer") or {}
    if seq:
        who = "this device" if seq.get("me") else f"{seq.get('label') or '?'} ({str(seq.get('device', ''))[:16]})"
        doc["sequencer"] = f"{who}, term {seq.get('term')}"
    doc["quarantine_unpromoted"] = s["quarantine_unpromoted"]
    if s.get("live_sessions"):
        doc["live_sessions"] = len(s["live_sessions"])
    doc["members"] = [
        {
            "fleet": m["label"],
            "state": "removed" if m["removed"] else "pending" if m["pending"] else m["role"],
            "verified": "us" if m["us"] else ("yes" if m["verified"] else "no"),
        }
        for m in s["members"]
    ]
    doc["devices"] = [
        {
            "fleet": m["label"],
            "device": d["label"],
            "id": d["device"][:16],
            "head": d["head"],
            "last_contact": _when(d["last_contact"]) if d.get("last_contact") else "never",
            "state": "removed"
            if d["removed"]
            else "frozen"
            if d.get("frozen")
            else "cert expired"
            if d["cert_expired"]
            else "ok",
        }
        for m in s["members"]
        for d in m["devices"]
    ]
    if s.get("pending_joins"):
        doc["pending_joins"] = [
            {"join": p["join"][:16], "from": p["label"], "needs_accept": bool(p["needs_approval"])}
            for p in s["pending_joins"]
        ]
    if s.get("sent"):
        doc["sent"] = [
            {"seq": r["seq"], "kind": r["kind"], "delivered_to": ", ".join(map(str, r["receipts"])) or "nobody yet"}
            for r in s["sent"][:5]
        ]
    if s.get("alarms"):
        doc["alarms"] = [{"kind": a["kind"], "author": a["author"][:16], "detail": a["detail"]} for a in s["alarms"]]
    notices = [line.strip() for line in _sequencer_text(s) if not line.strip().startswith("sequencer ")]
    if s.get("rotation_due"):
        notices.insert(
            0, "ROTATION DUE: the sequencer appends it; after 1 h it takes one from any device holding the key"
        )
    if notices:
        doc["notices"] = notices
    return doc


def _status_hints(docs: list[dict[str, Any]]) -> list[str]:
    """What a person or agent does next about these links: the first open item of each kind."""
    cli, hints = _cli(), []
    for d in docs:
        name = d["name"]
        if any(m["verified"] == "no" for m in d["members"]):
            hints.append(f"{cli} link verify {name} --mark")
        hints += [f"{cli} link accept {name} {p['join']}" for p in d.get("pending_joins", []) if p["needs_accept"]]
        if d["quarantine_unpromoted"]:
            hints.append(f"{cli} link inbox {name}")
    if not hints:  # nothing open: the usual next move is to bring someone in
        hints.append(f"{cli} link invite {docs[0]['name'] if len(docs) == 1 else '<name>'}")
    return list(dict.fromkeys(hints))[:3]


def do_status(c: Client, args: Any) -> int:
    rest = list(getattr(args, "args", None) or [])
    links = rest[:1] or [r["link"] for r in c.call("link.list") or []]
    out = [c.call("link.status", link=link) for link in links]
    if getattr(args, "json", False):
        print(json.dumps(out, indent=1, default=str))
        return 0
    if not out:
        return axi.emit({"total": 0, "links": []}, hints=[f"{_cli()} link create <name>"], title="Links")
    docs = [_status_doc(s) for s in out]
    # One link is the common case: its fields at the top level, not nested one deep.
    doc = docs[0] if len(docs) == 1 else {"total": len(docs), "links": docs}

    def human(console, _doc):  # the person's view keeps the prose layout, which reads well
        console.print(axi._esc("\n\n".join(_status_text(s) for s in out)))

    return axi.emit(doc, hints=_status_hints(docs), human=human, title="Link status")


def do_invite(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "invite <link> [--role writer] [--ttl 24h] [--approval] [--out invite.json]")[:1]
    out = c.call(
        "link.invite",
        link=link,
        role=getattr(args, "role", None),
        ttl_s=_ttl(getattr(args, "ttl", None)),
        single_use=not getattr(args, "multi", False),
        approval=bool(getattr(args, "approval", False)),
    )
    if getattr(args, "out", None):
        bundle = {"v": 1, "kind": "aurora-link-invite", "code": out["code"], "acl": out["acl"]}
        Path(args.out).write_text(json.dumps(bundle) + "\n", encoding="utf-8")
    out.pop("acl", None)
    if _json(args, out):
        return 0
    doc: dict[str, Any] = {
        "link": link,
        "role": out["role"],
        "uses": "many, until it expires" if getattr(args, "multi", False) else "one",
        "expires": _when(out["expires"]),
        "needs_approval": bool(out["approval"]),
        "fingerprint": out["fingerprint"],
        "code": out["code"],
    }
    doc["note"] = "the joiner should see exactly this fingerprint"
    if out.get("queued"):
        doc["queued"] = (
            "this device does not sequence the link: the invite is a proposal, and the code works once the "
            "sequencer includes it"
        )
    if getattr(args, "out", None):  # offline: the code and our log travel in a file
        doc["bundle"] = args.out
        doc["joiner_runs"] = f"link join {args.out} --out join.json"
    cli = _cli()
    # What the inviter does next: watch for the join (and accept it, when it waits for approval).
    hints = [f"{cli} link status {link}"]
    if out["approval"]:
        hints.append(f"{cli} link accept {link} <join id>")

    def human(console, d):
        axi.render_human(console, {k: v for k, v in d.items() if k != "code"})
        console.print()
        console.print("[bold]Invite code[/] [dim](hand it over whole)[/]")
        console.print(f"[bold green]{axi._esc(d['code'])}[/]", soft_wrap=True)  # never broken across lines

    return axi.emit(doc, hints=hints, human=human, title=f"Invite · {link}")


def do_join(c: Client, args: Any) -> int:
    (arg,) = _need(args, 1, "join <code | invite.json> [--label our-fleet] [--out join.json]")[:1]
    acl = None
    code = arg
    if not arg.startswith("aurora-invite1:") and Path(arg).is_file():
        bundle = json.loads(Path(arg).read_text(encoding="utf-8"))
        code, acl = bundle["code"], bundle["acl"]
    out = c.call("link.join", code=code, label=getattr(args, "label", None), acl=acl)
    bundle = out.pop("bundle", None)
    if bundle and getattr(args, "out", None):
        Path(args.out).write_text(json.dumps(bundle) + "\n", encoding="utf-8")
    rc = 0 if out["fingerprint_matches_code"] else 3
    if _json(args, out):
        return rc
    name, cli = out["name"], _cli()
    state = "queued" if out.get("queued") else "pending" if out["pending"] else "joined"
    doc: dict[str, Any] = {
        "link": name,
        "id": out["link"][:16],
        "state": state,
        "fingerprint_matches_code": bool(out["fingerprint_matches_code"]),
        "their_fingerprint": out["their_fingerprint"],
        "our_fingerprint": out["our_fingerprint"],
        "safety_number": out["safety_number"],
    }
    notes = []
    if not out["fingerprint_matches_code"]:
        notes.append("MISMATCH: the log's owner is not who the code named")
    if state == "queued":
        notes.append("the join is handed over and waits for the link's sequencer: run the same join again later")
    elif state == "pending":
        notes.append("waiting for the inviter to accept")
    notes.append("compare the safety number with them over a channel you already trust, then mark it verified")
    if bundle:
        where = getattr(args, "out", None)
        if where:
            doc["bundle"] = where
        notes.append(
            f"offline join: hand {where or '(pass --out FILE)'} back to the inviter (link import), then import "
            "the bundle it exports (link export): the link is ours once its sequencer includes the join"
        )
    doc["notes"] = notes
    hints = [] if rc else [f"{cli} link verify {name} --mark"]
    if state == "queued":
        hints.append(f"{cli} link join {arg}")
    hints.append(f"{cli} link status {name}")
    axi.emit(doc, hints=hints, title=f"Join · {name}")
    return rc


def _two(args: Any, usage: str) -> tuple[str, str]:
    rest = _need(args, 2, usage)
    return rest[0], rest[1]


def _changed(args: Any, out: dict[str, Any], link: str, change: str, effect: str | None = None) -> int:
    """How a membership change landed, for an agent and a person: applied on the chain (its entry),
    or a proposal the link's sequencer has yet to include. `--json` prints the daemon's answer."""
    if _json(args, out):
        return 0
    doc: dict[str, Any] = {"link": link, "change": change}
    if out.get("proposal"):
        doc["state"] = "proposed"
        doc["proposal"] = out["proposal"][:16]
        doc["sequencer"] = str(out.get("sequencer", ""))[:16]
        doc["note"] = "the sequencer includes it when a sync reaches it; link status shows it until then"
    else:
        doc["state"] = "applied"
        doc["entry"] = out["entry"][:16]
        if effect:
            doc["effect"] = effect
    if "epoch" in out:
        doc["epoch"] = out["epoch"]
    if out.get("rotation_due"):
        doc["rotation_due"] = "the sequencer appends it (after 1 h it takes one from any key holder)"
    # A proposal or a due rotation is still open: status is where it shows; otherwise it is done.
    hints = [f"{_cli()} link status {link}"] if doc["state"] == "proposed" or out.get("rotation_due") else []
    return axi.emit(doc, hints=hints, title=f"{change.capitalize()} · {link}")


def do_accept(c: Client, args: Any) -> int:
    link, join = _two(args, "accept <link> <join id>")
    out = c.call("link.accept", link=link, join=join)
    return _changed(args, out, link, "join accepted", "the read key is wrapped to them")


def do_decline(c: Client, args: Any) -> int:
    link, join = _two(args, "decline <link> <join id>")
    out = c.call("link.decline", link=link, join=join)
    return _changed(args, out, link, "join declined")


def do_verify(c: Client, args: Any) -> int:
    rest = _need(args, 1, "verify <link> [member] [--mark]")
    link, mark = rest[0], bool(getattr(args, "mark", False))
    rows = c.call("link.verify", link=link, member=rest[1] if len(rest) > 1 else None, mark=mark)
    if _json(args, rows):
        return 0
    cli = _cli()
    if not rows:  # AXI section 5: no other fleet means nothing to compare, said as a zero
        doc = {"link": link, "total": 0, "members": [], "note": "no other fleet in this link yet: nothing to compare"}
        return axi.emit(doc, hints=[f"{cli} link invite {link}"], title=f"Safety numbers · {link}")
    members = [
        {"fleet": r["label"], "safety_number": r["safety_number"], "verified": "yes" if r["verified"] else "no"}
        for r in rows
    ]
    doc: dict[str, Any] = {"link": link, "total": len(rows)}
    unverified = [m["fleet"] for m in members if m["verified"] == "no"]
    if unverified:
        doc["unverified"] = len(unverified)
    doc["members"] = members
    hints = []
    if unverified and not mark:
        doc["note"] = "read the safety number to them over a call or Signal; when both of you see the same, mark it"
        hints.append(f"{cli} link verify {link} {unverified[0] if len(unverified) == 1 else '<member>'} --mark")
    return axi.emit(doc, hints=hints, title=f"Safety numbers · {link}")


#: What each membership action did, as its confirmation names it.
_CHANGES = {
    "link.remove_member": "member removed",
    "link.remove_device": "device removed",
    "link.rotate_key": "key rotated",
    "link.revoke_invite": "invite revoked",
    "link.set_role": "role set",
    "link.leave": "left the link",
    "link.handoff": "sequencer handed off",
}


def _membership(c: Client, args: Any, method: str, usage: str, names: tuple[str, ...]) -> int:
    rest = _need(args, 1 + len(names), usage)
    params = {"link": rest[0], **{n: rest[i + 1] for i, n in enumerate(names)}}
    out = c.call(method, **params)
    return _changed(args, out, rest[0], _CHANGES[method])


def do_add_device(c: Client, args: Any) -> int:
    link, path = _two(args, "add-device <link> <cert.json>")
    out = c.call("link.add_device", link=link, cert=json.loads(Path(path).read_text(encoding="utf-8")))
    return _changed(args, out, link, "device added", "it now holds the read key")


def do_takeover(c: Client, args: Any) -> int:
    """The owner's takeover when the sequencer is lost, compromised or equivocated: the fleet root
    (the recovery phrase on stdin, or the sealed root's passphrase) makes this device sequence a
    new term after `--after` (default: this device's last held entry, so nothing it holds is
    dropped). Entries of older terms after that point are dropped everywhere. While halted below
    its last held entry, `--after` is required: the halt's seq - 1 drops both branches and every
    replica can take it; the last held entry keeps this branch, and replicas on the other one stay
    halted until a takeover at or below the halt's seq - 1 reaches them."""
    (link,) = _need(args, 1, "takeover <link> --phrase-stdin [--after SEQ]")[:1]
    phrase, passphrase = _read_phrase(args), _passphrase(args)
    if not phrase and not passphrase:
        raise UsageError("a takeover needs the fleet root: --phrase-stdin, or --passphrase-env VAR for root.json")
    out = c.call("link.takeover", link=link, phrase=phrase, passphrase=passphrase, after=getattr(args, "after", None))
    if _json(args, out):
        return 0
    doc = {
        "link": link,
        "sequencer": "this device",
        "term": out["term"],
        "starts_at_seq": out["seq"],
        "entry": out["entry"][:16],
        "note": "every replica drops what the old sequencer appended after it",
    }
    return axi.emit(doc, hints=[f"{_cli()} link status {link}"], title=f"Takeover · {link}")


# --------------------------------------------------------------------------------------- the mail


def do_inbox(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "inbox <link> [--limit 20]")[:1]
    limit = int(getattr(args, "limit", None) or 20)
    rows = quarantine.inbox(c, link, limit=limit)
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=1, default=str))
        return 0
    cli = _cli()
    if not rows:
        return axi.emit(
            {"link": link, "quarantined": 0, "records": []}, hints=[f"{cli} link status {link}"], title="Quarantine"
        )
    records = [
        {
            "record": r["record_id"][:12],
            "kind": r["kind"],
            "from": f"{r['fleet']}/{r['seat_claim']}",
            "to": r["to"] or "(link)",
            "content": axi.truncate(r["content"], 200)[0],
        }
        for r in rows
    ]
    doc: dict[str, Any] = {"link": link, "shown": len(rows)}
    if len(rows) >= limit:  # the inbox reads newest-first up to --limit; there may be more
        doc["limit"] = limit
    doc["records"] = records
    first = records[0]["record"] if len(records) == 1 else "<record>"
    hints = [f"{cli} link show {link} {first}", f"{cli} link promote {link} {first}"]
    if len(rows) >= limit:
        hints.append(f"{cli} link inbox {link} --limit {limit * 2}")
    return axi.emit(doc, hints=hints, title=f"Quarantine · {link}")


def _full_id(c: Client, link: str, prefix: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", prefix):
        return prefix
    for r in quarantine.inbox(c, link, limit=1000):
        if r["record_id"].startswith(prefix):
            return r["record_id"]
    raise UsageError(f"no quarantined record starts with {prefix!r}")


def do_show(c: Client, args: Any) -> int:
    link, rid = _two(args, "show <link> <record>")
    out = c.call("record.get", link=link, record_id=_full_id(c, link, rid))
    if _json(args, out):
        return 0
    body = out.get("body") or {}
    content = str(body.get("content", ""))
    shown, cut = axi.truncate(content, 800)
    doc: dict[str, Any] = {
        "record": out["record_id"],
        "from": f"{out.get('fleet')}/{body.get('seat')}",
        "device": out["device"][:16],
        "seq": out["seq"],
        "status": out["status"],
        "promoted_to": (out.get("promoted") or {}).get("seat"),
        "kind": body.get("kind"),
        "to": body.get("to"),
    }
    if cut:  # AXI section 3: the size, and where the rest is
        doc["content_chars"] = len(content)
    doc["content"] = shown
    cli, short = _cli(), out["record_id"][:12]
    hints = []
    if cut:
        hints.append(f"{cli} link show {link} {short} --json")
    if out["status"] == "admitted" and not out.get("promoted"):
        hints.append(f"{cli} link promote {link} {short}")

    def human(console, d):
        axi.render_human(console, {k: v for k, v in d.items() if k != "content"})
        console.print()
        console.print(axi._esc(d["content"]) or "[dim](no content)[/]")

    return axi.emit(doc, hints=hints, human=human, title=f"Record · {link}")


def do_promote(c: Client, args: Any) -> int:
    link, rid = _two(args, "promote <link> <record> [--to seat] [--yes]")
    if link == "legacy":  # mail the retired HMAC bridge parked (import-legacy)
        from core.link import legacy

        if not getattr(args, "to", None):
            raise UsageError("legacy mail names no seat it can be trusted with: say --to <seat>")
        if not getattr(args, "yes", False) and not sys.stdin.isatty():
            raise UsageError("promotion puts another fleet's words on our bus: confirm on a terminal, or pass --yes")
        out = legacy.promote_legacy(rid, by=getattr(args, "by", None) or f"person:{getpass.getuser()}", to=args.to)
        if _json(args, out):
            return 0
        doc = {
            "record": out["record_id"],
            "promoted_to": out["seat"],
            "source": "unverified legacy mail",
            "authority": "none",
        }
        return axi.emit(doc, title="Promoted")
    rid = _full_id(c, link, rid)
    rec = c.call("record.get", link=link, record_id=rid)
    body = rec.get("body") or {}
    by = getattr(args, "by", None) or f"person:{getpass.getuser()}"
    if not getattr(args, "yes", False):
        if not sys.stdin.isatty():
            raise UsageError("promotion puts another fleet's words on our bus: confirm on a terminal, or pass --yes")
        print(f"from {rec.get('fleet')}/{body.get('seat')} [{body.get('kind')}]: {str(body.get('content', ''))[:300]}")
        if input("promote this onto the bus? [y/N] ").strip().lower() not in ("y", "yes"):
            print("not promoted")
            return 1
    out = promote.promote(c, link, rid, by=by, to=getattr(args, "to", None), again=bool(getattr(args, "again", False)))
    if _json(args, out):
        return 0
    if not out["promoted"]:  # nothing to do is a success, said plainly (AXI section 6)
        doc = {"record": rid[:12], "promoted": False, "reason": "already promoted; nothing sent"}
        return axi.emit(doc, hints=[f"{_cli()} link promote {link} {rid[:12]} --yes --again"], title="Promote")
    doc = {"record": rid[:12], "promoted_to": out["seat"], "bus_id": out["bus_id"], "authority": "none"}
    return axi.emit(doc, title="Promoted")


def do_blob(c: Client, args: Any) -> int:
    rest = _need(args, 3, "blob <link> <record> <name|id> --out PATH")
    rid = _full_id(c, rest[0], rest[1])
    target = getattr(args, "out", None) or rest[2]
    out = c.call("blob.get", link=rest[0], record_id=rid, blob=rest[2], out=str(Path(target).resolve()))
    if _json(args, out):
        return 0
    return axi.emit({"wrote": out["out"], "bytes": out["bytes"]}, title="Attachment saved")


def do_send(c: Client, args: Any) -> int:
    rest = _need(args, 3, 'send <from-seat> <@fleet/seat> "text" [--kind chat]')
    rid = export.send_remote(
        rest[0],
        rest[1],
        getattr(args, "kind", None) or "chat",
        " ".join(rest[2:]),
        client=c,
        link=getattr(args, "link", None),
    )
    if _json(args, {"record_id": rid}):
        return 0
    doc = {
        "record": rid[:12],
        "from": rest[0],
        "to": rest[1],
        "kind": getattr(args, "kind", None) or "chat",
        "state": "written to our feed; it syncs as soon as a path is open",
    }
    return axi.emit(doc, hints=[f"{_cli()} link sync"], title="Sent")


def do_export(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "export <link> --out bundle.json")[:1]
    if not getattr(args, "out", None):
        raise UsageError("export needs --out FILE")
    bundle = c.call("bundle.export", link=link)
    Path(args.out).write_text(json.dumps(bundle) + "\n", encoding="utf-8")
    if getattr(args, "json", False):  # --json has always printed this line (the bundle is the file)
        print(f"wrote {len(bundle['acl'])} ACL entries and {len(bundle['records'])} records to {args.out}")
        return 0
    doc = {"link": link, "wrote": args.out, "acl_entries": len(bundle["acl"]), "records": len(bundle["records"])}
    # The bundle travels by hand: the next command is the other device's.
    return axi.emit(doc, hints=[f"{_cli()} link import {args.out}"], title=f"Bundle exported · {link}")


def do_import(c: Client, args: Any) -> int:
    (path,) = _need(args, 1, "import <bundle.json>")[:1]
    bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    if bundle.get("kind") == "aurora-link-invite":
        raise UsageError("that is an invite: use `aurora link join` on it")
    out = c.call("bundle.import", bundle=bundle)
    if _json(args, out):
        return 0
    short = out["link"][:16]
    doc = {
        "link": short,
        "acl_entries": out["acl_entries"],
        "records_stored": out["records_stored"],
        "records_refused": out["records_refused"],
    }
    cli = _cli()
    hint = f"{cli} link inbox {short}" if out["records_stored"] else f"{cli} link status {short}"
    return axi.emit(doc, hints=[hint], title="Bundle imported")


def do_policy(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "policy <link>")[:1]
    link_id = c.call("link.status", link=link)["link"]
    paths = {"promote": str(promote.write_default_policy(link_id)), "export": str(export.write_default_policy(link_id))}
    if _json(args, paths):
        return 0
    doc = {"link": link, "promote_policy": paths["promote"], "export_policy": paths["export"]}
    doc["scope"] = "both are local and never synced"
    return axi.emit(doc, title=f"Policies · {link}")  # the paths are the answer


def do_rebuild(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "rebuild <link>")[:1]
    n = quarantine.rebuild(c, link)
    if getattr(args, "json", False):  # --json has always printed this line
        print(f"rebuilt the quarantine stream from the store: {n} record(s)")
        return 0
    hints = [f"{_cli()} link inbox {link}"] if n else []
    return axi.emit({"link": link, "records": n}, hints=hints, title="Quarantine stream rebuilt")


def do_peer(c: Client, args: Any) -> int:
    (device,) = _need(args, 1, "peer <device> --addr ip:port [--relay URL]")[:1]
    addrs, relay = list(getattr(args, "addr", None) or []), getattr(args, "relay_url", None)
    out = c.call("peers.add", device=device, addrs=addrs, relay=relay)
    if _json(args, out):
        return 0
    doc = {"device": device[:16], "addrs": addrs, "relay": relay, "remembered": "dial hints for this device"}
    return axi.emit(doc, hints=[f"{_cli()} link sync"], title="Peer")


def do_sync(c: Client, args: Any) -> int:
    rest = list(getattr(args, "args", None) or [])
    out = c.call("sync.now", link=rest[0] if rest else None)
    if _json(args, out):
        return 0
    doc = {"dialing": "every member" + (f" of {rest[0]}" if rest else ""), "started": bool(out.get("dialing", True))}
    return axi.emit(doc, hints=[f"{_cli()} link status{' ' + rest[0] if rest else ''}"], title="Sync")


def do_relay_config(c: Client, args: Any) -> int:
    """An iroh-relay config admitting only our links' devices: a self-hosted, members-only relay."""
    out = c.call("relay.config", http_bind=getattr(args, "bind", None))
    target = getattr(args, "out", None)
    if target:
        Path(target).write_text(out["toml"], encoding="utf-8")
    if getattr(args, "json", False):  # --json has always printed the TOML itself, or the line
        if target:
            print(f"wrote {target}: {out['devices']} device(s) may relay. Run: iroh-relay --config-path {target}")
        else:
            print(out["toml"], end="")
        return 0
    if target:
        doc = {"wrote": target, "devices": out["devices"], "run": f"iroh-relay --config-path {target}"}
        return axi.emit(doc, title="Relay config")
    # Without --out the file itself is the output: `link relay-config > relay.toml` must keep
    # writing a valid config, and a pipe is agent mode. A person also gets the device count.
    if axi.is_agent():
        print(out["toml"], end="")
        return 0
    conf = tomllib.loads(out["toml"])
    allow = (conf.get("access") or {}).get("allowlist") or []
    doc = {
        "devices": out["devices"],
        "http_bind_addr": conf.get("http_bind_addr"),
        "allowlist": [d[:16] for d in allow],
    }

    def human(console, _d):
        console.print(f"[dim]{out['devices']} device(s) may relay[/]")
        console.print(axi._esc(out["toml"]), end="", soft_wrap=True)

    return axi.emit(doc, hints=[f"{_cli()} link relay-config --out relay.toml"], human=human, title="Relay config")


def do_import_legacy(c: Client, args: Any) -> int:
    from core.link import legacy

    out = legacy.import_parked(dry=bool(getattr(args, "dry_run", False)))
    if _json(args, out):
        return 0
    doc = {"imported": out["imported"], "skipped": out["skipped"]}
    if "would_import" in out:  # --dry-run: what a real run would bring in
        doc["would_import"] = out["would_import"]
    doc["into"] = "the quarantine (skipped: already there)"
    return axi.emit(doc, title="Legacy bridge inbox")


HANDLERS = {
    "init": do_init,
    "whoami": do_whoami,
    "renew": do_renew,
    "cert": do_cert,
    "certify": do_certify,
    "create": do_create,
    "list": do_list,
    "status": do_status,
    "invite": do_invite,
    "join": do_join,
    "accept": do_accept,
    "decline": do_decline,
    "verify": do_verify,
    "remove-member": lambda c, a: _membership(c, a, "link.remove_member", "remove-member <link> <member>", ("member",)),
    "remove-device": lambda c, a: _membership(c, a, "link.remove_device", "remove-device <link> <device>", ("device",)),
    "add-device": do_add_device,
    "rotate-key": lambda c, a: _membership(c, a, "link.rotate_key", "rotate-key <link>", ()),
    "revoke-invite": lambda c, a: _membership(c, a, "link.revoke_invite", "revoke-invite <link> <invite>", ("invite",)),
    "set-role": lambda c, a: _membership(c, a, "link.set_role", "set-role <link> <member> <role>", ("member", "role")),
    "leave": lambda c, a: _membership(c, a, "link.leave", "leave <link>", ()),
    "handoff": lambda c, a: _membership(c, a, "link.handoff", "handoff <link> <device>", ("device",)),
    "takeover": do_takeover,
    "inbox": do_inbox,
    "show": do_show,
    "promote": do_promote,
    "blob": do_blob,
    "send": do_send,
    "export": do_export,
    "import": do_import,
    "policy": do_policy,
    "rebuild": do_rebuild,
    "peer": do_peer,
    "sync": do_sync,
    "import-legacy": do_import_legacy,
    "relay-config": do_relay_config,
}


def main(args: Any) -> int:
    """Run one `aurora link` action. Returns the exit code."""
    action = args.action
    if action in ("serve", "mailbox"):
        from core.link import serve

        flags = serve.daemon_flags(
            mailbox=action == "mailbox",
            relays=getattr(args, "relay_url", None) and [args.relay_url],
            no_relay=bool(getattr(args, "no_relay", False)),
            no_n0=bool(getattr(args, "no_n0", False)),
            no_mdns=bool(getattr(args, "no_mdns", False)),
            bind=getattr(args, "bind", None),
            trace_rpc=bool(getattr(args, "trace_rpc", False)),
            relay_only=bool(getattr(args, "relay_only", False)),
        )
        return serve.run(flags=flags, mailbox=action == "mailbox", once=bool(getattr(args, "once", False)))
    try:
        with connect(network=action in NETWORKED) as c:
            return HANDLERS[action](c, args)
    except LinkdMissing:
        return axi.fail(
            MISSING, code="LINKD_MISSING", hints=["uv pip install akashic-aurora-linkd"], exit_code=axi.EXIT_USAGE
        )
    except UsageError as e:
        return axi.fail(str(e), code="USAGE", hints=[f"{_cli()} link --help"], exit_code=axi.EXIT_USAGE)
    except LinkRpcError as e:
        code = "REFUSED" if e.code == -32001 else "DAEMON_ERROR"
        return axi.fail(e.message, code=code, hints=[f"{_cli()} link list"])
    except (export.ExportRefused, promote.PromotionRefused) as e:
        return axi.fail(f"refused: {e}", code="REFUSED")
