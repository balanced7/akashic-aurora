"""Fleet links (RFC #70): the contract between Python and aurora-linkd, pinned without the binary.

- Python's bridge allowlist and the Rust daemon's are the same set, and neither carries a control
  kind (the drift guard the old bridge pinned, now covering both sides).
- core/link/rpc_types.py is generated from the checked-in OpenRPC document and is current.
- The client refuses a call the contract does not allow before anything is sent.
- Remote addresses are recognised exactly, so a local seat name never leaks to a link.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.link import client, export  # noqa: E402  # sys.path bootstrap
from core.link.kinds import BRIDGE_KINDS  # noqa: E402  # sys.path bootstrap
from core.link.rpc_types import METHODS  # noqa: E402  # sys.path bootstrap


def _rust_kinds() -> set[str]:
    src = (ROOT / "aurora-rs" / "link" / "src" / "acl.rs").read_text(encoding="utf-8")
    m = re.search(r"pub const BRIDGE_KINDS: \[&str; \d+\] = \[([^\]]*)\]", src)
    assert m, "BRIDGE_KINDS not found in acl.rs"
    return set(re.findall(r'"([a-z]+)"', m.group(1)))


def test_python_and_rust_share_one_bridge_allowlist():
    assert set(BRIDGE_KINDS) == _rust_kinds()


def test_no_control_kind_crosses_a_fleet_boundary():
    control = {"halt", "nudge", "pause", "interrupt", "steer", "resume", "drain", "kill"}
    assert not control & set(BRIDGE_KINDS)
    assert not control & _rust_kinds()


def test_the_old_bridge_uses_the_same_allowlist_object():
    from core.comm import remote_relay

    assert remote_relay.BRIDGE_KINDS is BRIDGE_KINDS


def test_generated_rpc_types_are_current():
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generators" / "gen_link_rpc.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stdout + out.stderr


def test_every_documented_method_is_in_the_table():
    for m in ("link.send", "events.wait", "promotion.record", "link.join", "bundle.import"):
        assert m in METHODS


def test_the_client_refuses_calls_outside_the_contract():
    with pytest.raises(client.LinkRpcError) as e:
        client.check_params("link.send", {"link": "x"})
    assert e.value.code == -32602
    with pytest.raises(client.LinkRpcError):
        client.check_params("link.send", {"link": "x", "body": {}, "authority": "admin"})
    with pytest.raises(client.LinkRpcError):
        client.check_params("shell.exec", {})
    client.check_params("link.send", {"link": "x", "body": {}})


@pytest.mark.parametrize(
    ("to", "remote"),
    [
        ("@partner/claude", True),
        ("@partner", True),
        ("claude", False),
        ("@partner/claude/extra", False),
        ("@ partner", False),
        ("", False),
        (None, False),
    ],
)
def test_remote_addresses_are_recognised_exactly(to, remote):
    assert export.is_remote_address(to) is remote


def test_parse_address_splits_fleet_and_seat():
    assert export.parse_address("@partner/claude") == ("partner", "claude")
    assert export.parse_address("@partner") == ("partner", None)
    with pytest.raises(export.ExportRefused):
        export.parse_address("claude")


def test_export_policy_defaults_and_narrows(tmp_path):
    link = "ab" * 32
    assert set(export.load_policy(link, home=tmp_path)["kinds"]) == set(BRIDGE_KINDS)
    path = tmp_path / "state" / "link" / link / "export.toml"
    path.parent.mkdir(parents=True)
    path.write_text('kinds = ["note", "halt"]\nseats = ["claude"]\nmax_chars = 100\n', encoding="utf-8")
    p = export.load_policy(link, home=tmp_path)
    assert p["kinds"] == ["note"], "a control kind in export.toml is ignored, never honoured"
    assert p["seats"] == ["claude"]
    assert p["max_chars"] == 100


def test_promote_policy_is_manual_by_default_and_never_auto_promotes_handoff(tmp_path):
    from core.link import promote

    link = "cd" * 32
    assert promote.load_policy(link, home=tmp_path) == {"mode": "manual", "rules": []}
    path = tmp_path / "state" / "link" / link / "promote.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        'mode = "rules"\n[[rules]]\nkind = "handoff"\nto = "claude"\n[[rules]]\nkind = "reply"\nto = "claude"\n',
        encoding="utf-8",
    )
    p = promote.load_policy(link, home=tmp_path)
    assert p["mode"] == "rules"
    assert [r["kind"] for r in p["rules"]] == ["reply"]


def test_a_broken_promote_policy_falls_back_to_manual(tmp_path):
    from core.link import promote

    link = "ef" * 32
    path = tmp_path / "state" / "link" / link / "promote.toml"
    path.parent.mkdir(parents=True)
    path.write_text("mode = [", encoding="utf-8")
    p = promote.load_policy(link, home=tmp_path)
    assert p["mode"] == "manual"
    assert "error" in p


def test_bus_send_routes_remote_addresses_to_the_exporter(monkeypatch):
    from core.comm.bus import Bus

    seen = {}

    def fake_send_remote(frm, to, kind, content, meta=None, **_):
        seen.update(frm=frm, to=to, kind=kind, content=content)
        return "f" * 64

    monkeypatch.setattr(export, "send_remote", fake_send_remote)
    bus = Bus("claude", client="dummy")
    assert bus.send("@partner/codex", "question", "hi") == "f" * 64
    assert seen == {"frm": "claude", "to": "@partner/codex", "kind": "question", "content": "hi"}


def test_a_refused_remote_send_returns_none_and_never_touches_the_bus(monkeypatch):
    from core.comm.bus import Bus

    def refuse(*_a, **_k):
        raise export.ExportRefused("no link")

    monkeypatch.setattr(export, "send_remote", refuse)
    bus = Bus("claude", client="dummy")
    assert bus.send("@nobody/x", "chat", "hi") is None


def test_provenance_comes_from_the_acl_and_carries_no_authority():
    from core.link import promote

    rec = {
        "link": "l",
        "fleet": "partner",
        "fleet_root": "r",
        "device": "d",
        "record_id": "x" * 64,
        "body": {"seat": "codex", "kind": "reply", "content": "done", "to": "@us/claude"},
    }
    meta = promote.provenance(rec, "person:alice")
    assert meta["authority"] == "none"
    assert meta["verified"] is True
    assert meta["fleet"] == "partner"
    assert meta["seat_claim"] == "codex"
    assert promote.render(rec) == "[remote partner/codex] done"
