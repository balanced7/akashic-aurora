"""rpc_types -- GENERATED from aurora-rs/linkd/openrpc.json by scripts/generators/gen_link_rpc.py.

Do not edit by hand: change the method table in aurora-rs/linkd/src/rpc.rs, regenerate
openrpc.json (`cargo run -p aurora-linkd -- openrpc`), then rerun the generator.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

CONTRACT_VERSION = "0.1.0"


class RpcDiscoverParams(TypedDict):
    """This contract as an OpenRPC document."""


class DaemonStatusParams(TypedDict):
    """Version, mode, uptime and network state."""


class DaemonShutdownParams(TypedDict):
    """Stop the daemon cleanly (exit code 0, not restarted)."""


class IdentityInitParams(TypedDict):
    """Create this install's device under a fleet root. Without a phrase, a new 24-word phrase is made and returned once."""

    phrase: NotRequired[str]
    label: NotRequired[str]
    passphrase: NotRequired[str]
    xwing: NotRequired[bool]
    force: NotRequired[bool]


class IdentityStatusParams(TypedDict):
    """This install's device, root fingerprint and certificate."""


class IdentityRenewParams(TypedDict):
    """Renew the device certificate (needs the phrase, or the passphrase for root.age) and announce it in every link."""

    phrase: NotRequired[str]
    passphrase: NotRequired[str]


class IdentityCertifyParams(TypedDict):
    """Record a certificate of another device of this fleet as ours (self-monitoring)."""

    cert: dict[str, Any]


class LinkCreateParams(TypedDict):
    """Create a link owned by this fleet."""

    name: str
    label: NotRequired[str]
    kinds: NotRequired[list[Any]]
    retention_days: NotRequired[int]


class LinkListParams(TypedDict):
    """Links this install holds."""


class LinkStatusParams(TypedDict):
    """Members, devices, heads, receipts, invites and alarms of one link."""

    link: str


class LinkInviteParams(TypedDict):
    """Publish an invite and return its code. The code also carries the bundle-free dial hints."""

    link: str
    role: NotRequired[str]
    ttl_s: NotRequired[int]
    single_use: NotRequired[bool]
    approval: NotRequired[bool]


class LinkJoinParams(TypedDict):
    """Join with an invite code. With `acl` (the inviter's log from a bundle) it works offline and returns our join entry as a bundle; without, it dials the inviter."""

    code: str
    label: NotRequired[str]
    acl: NotRequired[list[Any]]


class LinkAcceptParams(TypedDict):
    """Admit a pending join (wraps the read key to it)."""

    link: str
    join: str


class LinkDeclineParams(TypedDict):
    """Refuse a pending join."""

    link: str
    join: str


class LinkVerifyParams(TypedDict):
    """Safety numbers for each member; with mark=true, record that they were compared."""

    link: str
    member: NotRequired[str]
    mark: NotRequired[bool]


class LinkRemoveMemberParams(TypedDict):
    """Remove a fleet and rotate the read key."""

    link: str
    member: str


class LinkLeaveParams(TypedDict):
    """Leave a link (an admin's daemon then rotates the key)."""

    link: str


class LinkRemoveDeviceParams(TypedDict):
    """Remove one device and rotate the read key."""

    link: str
    device: str


class LinkAddDeviceParams(TypedDict):
    """Add another device of a member, from its certificate."""

    link: str
    cert: dict[str, Any]


class LinkRotateKeyParams(TypedDict):
    """Start a new read-key epoch."""

    link: str


class LinkRevokeInviteParams(TypedDict):
    """Kill an unused invite."""

    link: str
    invite: str


class LinkSetRoleParams(TypedDict):
    """Change a member's role (owner > admin > writer > reader > mailbox)."""

    link: str
    member: str
    role: str


class LinkSendParams(TypedDict):
    """Write one record. `source` makes it idempotent (the exporter passes the bus message id). Attachments become encrypted blobs."""

    link: str
    body: dict[str, Any]
    source: NotRequired[str]
    attachments: NotRequired[list[Any]]


class LinkReadParams(TypedDict):
    """Send read receipts for records a seat has read."""

    link: str
    record_ids: list[Any]


class RecordGetParams(TypedDict):
    """One stored record with its body and provenance."""

    link: str
    record_id: str


class EventsWaitParams(TypedDict):
    """Admitted records after the given per-link cursors; waits up to timeout_ms for the first one."""

    cursors: NotRequired[dict[str, Any]]
    timeout_ms: NotRequired[int]
    limit: NotRequired[int]


class PromotionRecordParams(TypedDict):
    """Record that a person or rule promoted a record onto the bus. Returns first=false when it already was."""

    link: str
    record_id: str
    seat: str
    by: str
    bus_id: NotRequired[str]


class BundleExportParams(TypedDict):
    """The whole log and records of a link, for sneakernet."""

    link: str
    records: NotRequired[bool]


class BundleImportParams(TypedDict):
    """Merge a bundle: every entry and record is verified as if it came over the wire."""

    bundle: dict[str, Any]


class BlobGetParams(TypedDict):
    """Fetch (if needed), verify and decrypt one attachment of a record into a file."""

    link: str
    record_id: str
    blob: str
    out: str


class PeersAddParams(TypedDict):
    """Remember dial hints (direct addresses, a relay URL) for a device."""

    device: str
    addrs: NotRequired[list[Any]]
    relay: NotRequired[str]


class NetStatusParams(TypedDict):
    """Our endpoint id, addresses, relay and live sessions."""


class SyncNowParams(TypedDict):
    """Dial every member of a link (or all links) now."""

    link: NotRequired[str]


class HousekeepingParams(TypedDict):
    """Run retention and certificate renewal now."""


#: method -> (required parameters, optional parameters)
METHODS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "rpc.discover": ((), ()),
    "daemon.status": ((), ()),
    "daemon.shutdown": ((), ()),
    "identity.init": ((), ("phrase", "label", "passphrase", "xwing", "force")),
    "identity.status": ((), ()),
    "identity.renew": ((), ("phrase", "passphrase")),
    "identity.certify": (("cert",), ()),
    "link.create": (("name",), ("label", "kinds", "retention_days")),
    "link.list": ((), ()),
    "link.status": (("link",), ()),
    "link.invite": (("link",), ("role", "ttl_s", "single_use", "approval")),
    "link.join": (("code",), ("label", "acl")),
    "link.accept": (("link", "join"), ()),
    "link.decline": (("link", "join"), ()),
    "link.verify": (("link",), ("member", "mark")),
    "link.remove_member": (("link", "member"), ()),
    "link.leave": (("link",), ()),
    "link.remove_device": (("link", "device"), ()),
    "link.add_device": (("link", "cert"), ()),
    "link.rotate_key": (("link",), ()),
    "link.revoke_invite": (("link", "invite"), ()),
    "link.set_role": (("link", "member", "role"), ()),
    "link.send": (("link", "body"), ("source", "attachments")),
    "link.read": (("link", "record_ids"), ()),
    "record.get": (("link", "record_id"), ()),
    "events.wait": ((), ("cursors", "timeout_ms", "limit")),
    "promotion.record": (("link", "record_id", "seat", "by"), ("bus_id",)),
    "bundle.export": (("link",), ("records",)),
    "bundle.import": (("bundle",), ()),
    "blob.get": (("link", "record_id", "blob", "out"), ()),
    "peers.add": (("device",), ("addrs", "relay")),
    "net.status": ((), ()),
    "sync.now": ((), ("link",)),
    "housekeeping": ((), ()),
}

#: Methods an offline daemon refuses: they need `aurora link serve`.
NETWORK: frozenset[str] = frozenset(["net.status", "sync.now"])
