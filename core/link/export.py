"""export -- the outbound half: bus mail with a remote address becomes a record in our feed.

Nothing leaves the fleet without an explicit remote address: `@<fleet>/<seat>` (one seat of a
member fleet) or `@<fleet>` (that whole fleet). `Bus.send` routes any such address here, so the
CLI (`bifrost-send --to @fleet/seat`), the MCP `bifrost_send` tool and the runner ToolBox all reach
a peer the same way. The record is written by the daemon and syncs whenever a path opens, so
sending works with the peer offline and even with `aurora link serve` stopped.

Outbound is policy-gated by a local `state/link/<link_id>/export.toml`:

- kinds: a subset of BRIDGE_KINDS (the default is all of them);
- seats: which local seats may write to the link (the default is every seat);
- `redact()` always runs before anything is written;
- text past `max_chars` (8,000, as on the bus) travels as an encrypted attachment.
"""

from __future__ import annotations

import re
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from core.link.client import Client, connect, state_dir
from core.link.kinds import BRIDGE_KINDS

ADDRESS = re.compile(r"@([^/\s@]+)(?:/([^/\s@]+))?")
DEFAULT_MAX_CHARS = 8000

DEFAULT_POLICY = """# export.toml -- what this fleet may write to the link. LOCAL: never synced.
#
# Nothing is exported without an explicit remote address (@fleet/seat or @fleet).
# kinds: a subset of chat, question, handoff, reply, completion, blocker, note.
kinds = ["chat", "question", "handoff", "reply", "completion", "blocker", "note"]
# seats: local seats allowed to write here; "*" means every seat.
seats = ["*"]
# Longer messages travel as an encrypted attachment instead of inline text.
max_chars = 8000
"""


class ExportRefused(RuntimeError):
    """Local policy, or the address, does not allow this send."""


def is_remote_address(to: Any) -> bool:
    return isinstance(to, str) and ADDRESS.fullmatch(to.strip()) is not None


def parse_address(to: str) -> tuple[str, str | None]:
    m = ADDRESS.fullmatch(to.strip())
    if not m:
        raise ExportRefused(f"{to!r} is not a remote address (@fleet/seat or @fleet)")
    return m.group(1), m.group(2)


def load_policy(link_id: str, home: Path | None = None) -> dict[str, Any]:
    path = state_dir(home) / link_id / "export.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ExportRefused(f"{path} is unreadable ({e}); nothing is exported until it is fixed") from e
    kinds = [k for k in data.get("kinds", sorted(BRIDGE_KINDS)) if k in BRIDGE_KINDS]
    return {
        "kinds": kinds,
        "seats": list(data.get("seats", ["*"])),
        "max_chars": int(data.get("max_chars", DEFAULT_MAX_CHARS)),
    }


def write_default_policy(link_id: str, home: Path | None = None) -> Path:
    path = state_dir(home) / link_id / "export.toml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_POLICY, encoding="utf-8")
    return path


def resolve_link(client: Client, fleet: str, link: str | None = None) -> tuple[str, str]:
    """(link id, the member fleet's label) for an address's fleet part. A fleet that shares more
    than one link with us needs `link` to say which."""
    hits: list[tuple[str, str]] = []
    for row in client.call("link.list") or []:
        if link and link not in (row["link"], row["name"]) and not row["link"].startswith(link):
            continue
        status = client.call("link.status", link=row["link"])
        for m in status["members"]:
            if m.get("us") or m.get("removed") or m.get("pending"):
                continue
            if fleet in (m["label"], m["root"]) or (len(fleet) >= 8 and m["root"].startswith(fleet)):
                hits.append((row["link"], m["label"]))
    if not hits:
        raise ExportRefused(f"no link here has a member fleet called {fleet!r}")
    if len({h[0] for h in hits}) > 1:
        raise ExportRefused(f"{fleet!r} shares more than one link with us: name the link")
    return hits[0]


def _reply_to(meta: dict[str, Any] | None) -> str | None:
    answers = str((meta or {}).get("answers") or "")
    return answers if re.fullmatch(r"[0-9a-f]{64}", answers) else None


def send_remote(
    frm: str,
    to: str,
    kind: str,
    content: Any,
    meta: dict[str, Any] | None = None,
    *,
    link: str | None = None,
    client: Client | None = None,
) -> str:
    """Write one message to a link. Returns the record id. Raises ExportRefused."""
    from core.comm.discord_bridge import redact

    fleet, seat = parse_address(to)
    own = client is None
    c = client or connect()
    try:
        link_id, label = resolve_link(c, fleet, link)
        policy = load_policy(link_id)
        if kind not in policy["kinds"]:
            raise ExportRefused(f"kind {kind!r} may not leave this fleet on that link (export.toml kinds)")
        if "*" not in policy["seats"] and frm not in policy["seats"]:
            raise ExportRefused(f"seat {frm!r} may not write to that link (export.toml seats)")
        text = redact("" if content is None else str(content))
        attachments = []
        if len(text) > policy["max_chars"]:
            spill = Path(tempfile.mkdtemp(prefix="aurora-link-")) / "message.md"
            spill.write_text(text, encoding="utf-8")
            attachments.append({"path": str(spill), "name": "message.md"})
            text = (
                text[: policy["max_chars"] - 200]
                + f"\n[... {len(text)} chars in all; the full text is attached as message.md]"
            )
        body: dict[str, Any] = {
            "kind": kind,
            "seat": frm,
            "to": f"@{label}/{seat}" if seat else f"@{label}",
            "content": text,
        }
        reply = _reply_to(meta)
        if reply:
            body["reply_to"] = reply
        source = str((meta or {}).get("source_id") or "") or None
        out = c.call("link.send", link=link_id, body=body, source=source, attachments=attachments or None)
        for a in attachments:
            Path(a["path"]).unlink(missing_ok=True)
        return str(out["record_id"])
    finally:
        if own:
            c.close()
