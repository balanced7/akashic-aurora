"""cli -- `aurora link <action>`: the operator's door to fleet links.

Each action is one call (or a few) to aurora-linkd. Nothing here decides anything about keys,
membership or records: the daemon does, and refuses what it must. What stays here is the part
that touches people and agents: wording, files, the confirm before a promotion.

The read paths (list, status, whoami, inbox) and every error print through core/axi: TOON for an
agent, a layout for a person. The other actions answer in one line of text in both modes.

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


def _print(args: Any, data: Any, text: str) -> None:
    print(json.dumps(data, indent=1, default=str) if getattr(args, "json", False) else text)


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
    lines = [
        f"device      {out['device']}",
        f"fleet root  {out['root']}",
        f"fingerprint {out['fingerprint']}",
        f"root kept   {'yes, sealed under your passphrase' if out['root_stored'] else 'no: the phrase re-derives it when needed'}",
    ]
    if out.get("phrase"):
        lines += [
            "",
            "RECOVERY PHRASE -- shown once. Write it down and keep it offline. It is the fleet root:",
            "",
            f"    {out['phrase']}",
            "",
        ]
    _print(args, out, "\n".join(lines))
    return 0


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
    _print(
        args, out, f"certificate renewed until {_when(out['cert_expires'])}; announced in {len(out['links'])} link(s)"
    )
    return 0


def do_cert(c: Client, args: Any) -> int:
    cert = c.call("identity.status")["cert"]
    text = json.dumps(cert, indent=1)
    if getattr(args, "out", None):
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote this device's certificate to {args.out}: hand it to a device already in the link")
    else:
        print(text)
    return 0


def do_certify(c: Client, args: Any) -> int:
    (path,) = _need(args, 1, "certify <cert.json>")[:1]
    cert = json.loads(Path(path).read_text(encoding="utf-8"))
    out = c.call("identity.certify", cert=cert)
    _print(args, out, f"recorded {out['device'][:16]} as a device of this fleet")
    return 0


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
    _print(args, out, f"link {out['name']} created: {out['link']}\nour fingerprint {out['fingerprint']}")
    return 0


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
    text = [
        f"invite for {out['role']} in {link}, single-use, expires {_when(out['expires'])}"
        + (" (needs your approval after they join)" if out["approval"] else ""),
    ]
    if out.get("queued"):
        text.append(
            "this device does not sequence the link: the invite is a proposal, and the code works once the sequencer includes it"
        )
    text += [
        "",
        out["code"],
        "",
        f"our fingerprint {out['fingerprint']}  -- the joiner should see exactly this",
    ]
    if getattr(args, "out", None):
        text.append(f"offline: the code and our log are in {args.out} (`aurora link join {args.out} --out join.json`)")
    _print(args, out, "\n".join(text))
    return 0


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
    if out.get("queued"):
        head = (
            f"join for {out['name']} ({out['link'][:16]}) handed over; it waits for the link's sequencer: "
            "run the same join again later"
        )
    else:
        head = f"joined {out['name']} ({out['link'][:16]})" + (
            " -- waiting for the inviter to accept" if out["pending"] else ""
        )
    lines = [
        head,
        f"their fingerprint {out['their_fingerprint']}"
        + ("" if out["fingerprint_matches_code"] else "  MISMATCH: the log's owner is not who the code named"),
        f"our fingerprint   {out['our_fingerprint']}",
        f"safety number     {out['safety_number']}",
        f"compare the safety number with them over a channel you already trust, then: aurora link verify {out['name']} --mark",
    ]
    if bundle:
        lines.append(
            f"offline join: hand {getattr(args, 'out', None) or '(pass --out FILE)'} back to the inviter (`aurora link import`), "
            "then import the bundle it exports (`aurora link export`): the link is ours once its sequencer includes the join"
        )
    _print(args, out, "\n".join(lines))
    return 0 if out["fingerprint_matches_code"] else 3


def _two(args: Any, usage: str) -> tuple[str, str]:
    rest = _need(args, 2, usage)
    return rest[0], rest[1]


def _done(out: dict[str, Any], what: str) -> str:
    """How a membership change landed: on the chain, or as a proposal for the sequencer."""
    if out.get("proposal"):
        return (
            f"{what} proposed ({out['proposal'][:16]}); the sequencer {str(out.get('sequencer', ''))[:16]} "
            "includes it when a sync reaches it (`aurora link status` shows it until then)"
        )
    return f"{what} ({out['entry'][:16]})"


def do_accept(c: Client, args: Any) -> int:
    link, join = _two(args, "accept <link> <join id>")
    out = c.call("link.accept", link=link, join=join)
    _print(args, out, _done(out, "accepted; the read key is wrapped to them"))
    return 0


def do_decline(c: Client, args: Any) -> int:
    link, join = _two(args, "decline <link> <join id>")
    out = c.call("link.decline", link=link, join=join)
    _print(args, out, _done(out, "declined"))
    return 0


def do_verify(c: Client, args: Any) -> int:
    rest = _need(args, 1, "verify <link> [member] [--mark]")
    rows = c.call(
        "link.verify", link=rest[0], member=rest[1] if len(rest) > 1 else None, mark=bool(getattr(args, "mark", False))
    )
    text = "\n".join(
        f"{r['label']:<16} {r['safety_number']}  {'verified' if r['verified'] else 'not verified'}" for r in rows
    )
    if not getattr(args, "mark", False):
        text += "\n\nread it to them over a call or Signal; when both of you see the same, add --mark"
    _print(args, rows, text)
    return 0


def _membership(c: Client, args: Any, method: str, usage: str, names: tuple[str, ...]) -> int:
    rest = _need(args, 1 + len(names), usage)
    params = {"link": rest[0], **{n: rest[i + 1] for i, n in enumerate(names)}}
    if method == "link.add_device":
        params["cert"] = json.loads(Path(rest[1]).read_text(encoding="utf-8"))
    out = c.call(method, **params)
    msg = f"{_done(out, 'done')}; epoch {out['epoch']}"
    if out.get("rotation_due"):
        msg += "; a key rotation is due: the sequencer appends it (after 1 h it takes one from any key holder)"
    _print(args, out, msg)
    return 0


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
    _print(
        args,
        out,
        f"this device now sequences {link}: term {out['term']} starts at seq {out['seq']} ({out['entry'][:16]}); "
        "every replica drops what the old sequencer appended after it",
    )
    return 0


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
    body = out.get("body") or {}
    _print(
        args,
        out,
        f"{out['record_id']}\n  from {out.get('fleet')}/{body.get('seat')} (device {out['device'][:16]}, seq {out['seq']})\n"
        f"  status {out['status']}{'  promoted to ' + out['promoted']['seat'] if out.get('promoted') else ''}\n"
        f"  {body.get('kind')} -> {body.get('to')}\n\n{body.get('content', '')}",
    )
    return 0


def do_promote(c: Client, args: Any) -> int:
    link, rid = _two(args, "promote <link> <record> [--to seat] [--yes]")
    if link == "legacy":  # mail the retired HMAC bridge parked (import-legacy)
        from core.link import legacy

        if not getattr(args, "to", None):
            raise UsageError("legacy mail names no seat it can be trusted with: say --to <seat>")
        if not getattr(args, "yes", False) and not sys.stdin.isatty():
            raise UsageError("promotion puts another fleet's words on our bus: confirm on a terminal, or pass --yes")
        out = legacy.promote_legacy(rid, by=getattr(args, "by", None) or f"person:{getpass.getuser()}", to=args.to)
        _print(args, out, f"promoted {out['record_id']} -> {out['seat']} (unverified legacy mail, authority none)")
        return 0
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
    if not out["promoted"]:
        _print(args, out, "already promoted; nothing sent (pass --again to resend)")
        return 0
    _print(args, out, f"promoted {rid[:12]} -> {out['seat']} (bus id {out['bus_id']}), authority none")
    return 0


def do_blob(c: Client, args: Any) -> int:
    rest = _need(args, 3, "blob <link> <record> <name|id> --out PATH")
    rid = _full_id(c, rest[0], rest[1])
    target = getattr(args, "out", None) or rest[2]
    out = c.call("blob.get", link=rest[0], record_id=rid, blob=rest[2], out=str(Path(target).resolve()))
    _print(args, out, f"wrote {out['bytes']} bytes to {out['out']}")
    return 0


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
    _print(args, {"record_id": rid}, f"written to our feed as {rid[:12]}; it syncs as soon as a path is open")
    return 0


def do_export(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "export <link> --out bundle.json")[:1]
    if not getattr(args, "out", None):
        raise UsageError("export needs --out FILE")
    bundle = c.call("bundle.export", link=link)
    Path(args.out).write_text(json.dumps(bundle) + "\n", encoding="utf-8")
    print(f"wrote {len(bundle['acl'])} ACL entries and {len(bundle['records'])} records to {args.out}")
    return 0


def do_import(c: Client, args: Any) -> int:
    (path,) = _need(args, 1, "import <bundle.json>")[:1]
    bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    if bundle.get("kind") == "aurora-link-invite":
        raise UsageError("that is an invite: use `aurora link join` on it")
    out = c.call("bundle.import", bundle=bundle)
    _print(
        args,
        out,
        f"imported into {out['link'][:16]}: {out['acl_entries']} ACL entries, {out['records_stored']} new records, {out['records_refused']} refused",
    )
    return 0


def do_policy(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "policy <link>")[:1]
    link_id = c.call("link.status", link=link)["link"]
    paths = {"promote": str(promote.write_default_policy(link_id)), "export": str(export.write_default_policy(link_id))}
    _print(
        args,
        paths,
        f"promote policy {paths['promote']}\nexport policy  {paths['export']}\nboth are local and never synced",
    )
    return 0


def do_rebuild(c: Client, args: Any) -> int:
    (link,) = _need(args, 1, "rebuild <link>")[:1]
    n = quarantine.rebuild(c, link)
    print(f"rebuilt the quarantine stream from the store: {n} record(s)")
    return 0


def do_peer(c: Client, args: Any) -> int:
    (device,) = _need(args, 1, "peer <device> --addr ip:port [--relay URL]")[:1]
    out = c.call(
        "peers.add",
        device=device,
        addrs=list(getattr(args, "addr", None) or []),
        relay=getattr(args, "relay_url", None),
    )
    _print(args, out, f"remembered dial hints for {device[:16]}")
    return 0


def do_sync(c: Client, args: Any) -> int:
    rest = list(getattr(args, "args", None) or [])
    out = c.call("sync.now", link=rest[0] if rest else None)
    _print(args, out, "dialing every member now")
    return 0


def do_relay_config(c: Client, args: Any) -> int:
    """An iroh-relay config admitting only our links' devices: a self-hosted, members-only relay."""
    out = c.call("relay.config", http_bind=getattr(args, "bind", None))
    if getattr(args, "out", None):
        Path(args.out).write_text(out["toml"], encoding="utf-8")
        print(f"wrote {args.out}: {out['devices']} device(s) may relay. Run: iroh-relay --config-path {args.out}")
    else:
        print(out["toml"], end="")
    return 0


def do_import_legacy(c: Client, args: Any) -> int:
    from core.link import legacy

    out = legacy.import_parked(dry=bool(getattr(args, "dry_run", False)))
    _print(
        args,
        out,
        f"legacy bridge inbox: {out['imported']} imported into the quarantine, {out['skipped']} already there",
    )
    return 0


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
    "add-device": lambda c, a: _membership(c, a, "link.add_device", "add-device <link> <cert.json>", ("cert_file",)),
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
            if action == "add-device":
                rest = _need(args, 2, "add-device <link> <cert.json>")
                out = c.call(
                    "link.add_device", link=rest[0], cert=json.loads(Path(rest[1]).read_text(encoding="utf-8"))
                )
                text = (
                    f"device added ({out['entry'][:16]}); it now holds the read key"
                    if out.get("entry")
                    else _done(out, "device added")
                )
                _print(args, out, text)
                return 0
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
