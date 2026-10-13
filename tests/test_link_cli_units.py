"""Fleet links (RFC #70): `aurora link <action>` (core/link/cli.py), pinned without aurora-linkd.

Every verb runs through `cli.main` on the in-process FakeDaemon of tests/test_link_python_units.py,
so the real Client checks each call against the contract. What is pinned is the CLI's own part:
argument handling, wording, files, exit codes, and the confirmation before a promotion.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.link import cli, export, promote, quarantine  # noqa: E402  # sys.path bootstrap
from core.link import client as lc  # noqa: E402  # sys.path bootstrap
from tests.test_link_python_units import (  # noqa: E402  # sys.path bootstrap
    LINK,
    OUR_ROOT,
    REC,
    THEIR_ROOT,
    FakeDaemon,
    Refuse,
    StubBus,
    event,
    member,
    status,
)


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("AI_SETUP", str(tmp_path))
    return tmp_path


class Harness:
    """Runs `aurora link` actions against one FakeDaemon and remembers how it connected."""

    def __init__(self, monkeypatch, capsys):
        self.d = FakeDaemon()
        self.networks: list[bool] = []
        self._capsys = capsys

        def fake_connect(*, network: bool = False, **_kw: Any) -> lc.Client:
            self.networks.append(network)
            return self.d.client()

        monkeypatch.setattr(cli, "connect", fake_connect)

    def run(self, action: str, *args: str, **opts: Any) -> tuple[int, str]:
        code = cli.main(SimpleNamespace(action=action, args=list(args), **opts))
        return code, self._capsys.readouterr().out

    def params(self, method: str) -> dict[str, Any]:
        return next(p for m, p in self.d.calls if m == method)


@pytest.fixture(autouse=True)
def agent_output(monkeypatch):
    """The read paths and errors print through core/axi; pin the agent rendering (TOON)."""
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


@pytest.fixture
def h(monkeypatch, capsys, home) -> Harness:
    return Harness(monkeypatch, capsys)


# --------------------------------------------------------------------------- dispatch and errors


def test_every_action_has_a_handler_or_is_serve():
    """ACTIONS and HANDLERS agree: no verb the parser offers falls through."""
    assert set(cli.ACTIONS) == set(cli.HANDLERS) | {"serve", "mailbox"}


def test_missing_daemon_is_exit_2_with_the_install_line(monkeypatch, capsys):
    """LinkdMissing prints the remedy and exits 2."""

    def missing(**_kw: Any) -> lc.Client:
        raise lc.LinkdMissing(lc.MISSING)

    monkeypatch.setattr(cli, "connect", missing)
    assert cli.main(SimpleNamespace(action="list", args=[])) == 2
    out = capsys.readouterr().out
    assert "akashic-aurora-linkd" in out
    assert "code: LINKD_MISSING" in out


def test_daemon_refusal_is_exit_1_with_its_message(h):
    """A LinkRpcError from the daemon prints its message and exits 1."""
    h.d.handlers["link.status"] = lambda _p: (_ for _ in ()).throw(Refuse(-32001, "refused: unknown link"))
    code, out = h.run("status", "nope")
    assert code == 1
    assert 'error: "refused: unknown link"\ncode: REFUSED' in out


def test_usage_errors_are_exit_2_with_the_usage(h):
    """Too few arguments print `usage: aurora link ...` and exit 2, before any daemon call."""
    for action, usage in [
        ("create", "create <name>"),
        ("invite", "invite <link>"),
        ("join", "join <code"),
        ("accept", "accept <link> <join id>"),
        ("decline", "decline <link> <join id>"),
        ("verify", "verify <link>"),
        ("remove-member", "remove-member <link> <member>"),
        ("set-role", "set-role <link> <member> <role>"),
        ("add-device", "add-device <link> <cert.json>"),
        ("inbox", "inbox <link>"),
        ("show", "show <link> <record>"),
        ("blob", "blob <link> <record>"),
        ("send", "send <from-seat>"),
        ("certify", "certify <cert.json>"),
        ("peer", "peer <device>"),
        ("policy", "policy <link>"),
        ("rebuild", "rebuild <link>"),
        ("export", "export <link>"),
        ("import", "import <bundle.json>"),
    ]:
        code, out = h.run(action)
        assert code == 2, (action, out)
        assert out.startswith(f'error: "usage: aurora link {usage}'), (action, out)
        assert "code: USAGE" in out, (action, out)
    assert h.d.calls == []


def test_networked_actions_ask_for_the_network(h):
    """join and sync connect with network=True; everything else stays offline."""
    h.d.handlers.update({"sync.now": {}, "link.list": []})
    assert h.run("sync") == (0, "dialing: every member\nstarted: true\nhelp[1]:\n  uv run agent_cli.py link status\n")
    assert h.params("sync.now") == {}
    h.run("sync", "ops")
    assert h.d.calls[-1] == ("sync.now", {"link": "ops"})
    h.run("list")
    assert h.networks == [True, True, False]


def test_json_flag_prints_the_raw_answer(h):
    """--json prints the daemon's answer as JSON instead of the text."""
    rows = [{"name": "ops", "link": LINK, "role": "owner", "members": 2, "epoch": 1, "alarms": 0}]
    h.d.handlers["link.list"] = rows
    code, out = h.run("list", json=True)
    assert code == 0
    assert json.loads(out) == rows


def test_serve_and_mailbox_hand_their_flags_to_serve_run(monkeypatch):
    """`serve`/`mailbox` never connect: their options become daemon flags for serve.run."""
    from core.link import serve

    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(serve, "run", lambda **kw: seen.append(kw) or 0)
    args = SimpleNamespace(action="serve", relay_url="https://relay", no_mdns=True, bind="0.0.0.0:7", once=True)
    assert cli.main(args) == 0
    assert seen[0] == {
        "flags": ["--relay", "https://relay", "--no-mdns", "--bind", "0.0.0.0:7"],
        "mailbox": False,
        "once": True,
    }
    assert cli.main(SimpleNamespace(action="mailbox")) == 0
    assert seen[1] == {"flags": ["--mailbox"], "mailbox": True, "once": False}


def test_ttl_and_when_helpers():
    """--ttl takes s/m/h/d; a bad timestamp prints as '-'."""
    assert cli._ttl(None) is None
    assert [cli._ttl(x) for x in ("90", "90s", "2m", "3h", "1d")] == [90, 90, 120, 10800, 86400]
    with pytest.raises(cli.UsageError, match="--ttl"):
        cli._ttl("1w")
    assert cli._when("x") == "-"
    assert cli._when(None) == "-"
    assert cli._when(0)[:2] in ("19", "20")


# --------------------------------------------------------------------------------------- identity


def test_init_shows_the_recovery_phrase_once_and_reads_secrets_from_stdin_and_env(h, monkeypatch):
    """init passes --phrase-stdin and the passphrase env var; a new phrase is printed once, with a
    warning, to an agent and (in a red panel) to a person."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("word " * 24 + "\n"))
    monkeypatch.setenv("LINK_PASS", "s3cret")
    h.d.handlers["identity.init"] = {
        "device": "dev1",
        "root": OUR_ROOT,
        "fingerprint": "fp",
        "root_stored": True,
        "phrase": "alpha beta",
    }
    code, out = h.run("init", label="home", phrase_stdin=True, passphrase_env="LINK_PASS", no_xwing=True)
    assert code == 0
    p = h.params("identity.init")
    assert p == {"phrase": ("word " * 24).strip(), "label": "home", "passphrase": "s3cret", "xwing": False}
    assert "recovery_phrase: alpha beta\nwarning: RECOVERY PHRASE -- shown once" in out
    assert 'root_kept: "yes, sealed under your passphrase"' in out
    assert "link create <name>" in out
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _code, out = h.run("init", label="home")
    assert "RECOVERY PHRASE -- shown once" in out
    assert "alpha beta" in out
    assert "keep it offline" in out


def test_init_without_a_new_phrase_prints_no_phrase_block(h):
    """Re-deriving from an existing phrase shows no recovery block; xwing defaults on."""
    h.d.handlers["identity.init"] = {"device": "d", "root": "r", "fingerprint": "f", "root_stored": False}
    code, out = h.run("init")
    assert code == 0
    assert "RECOVERY PHRASE" not in out
    assert "recovery_phrase" not in out
    assert "the phrase re-derives it" in out
    assert h.params("identity.init") == {"xwing": True}


def test_whoami_before_and_after_init(h):
    """No identity: exit 1 with the next step; with one: device, fingerprint, cert expiry."""
    h.d.handlers["identity.status"] = {"initialized": False}
    code, out = h.run("whoami")
    assert code == 1
    assert "error: no fleet identity on this install yet\ncode: NO_IDENTITY" in out
    assert "link init --label <name>" in out
    h.d.handlers["identity.status"] = {
        "initialized": True,
        "device": "f" * 64,
        "label": "home",
        "fingerprint": "fp",
        "cert_expires": 1_900_000_000,
        "needs_renewal": True,
    }
    code, out = h.run("whoami")
    assert code == 0
    assert f"device: {'f' * 16}\nlabel: home" in out
    assert "renew_soon: true" in out
    assert "link renew" in out


def test_renew_reports_the_new_expiry_and_links(h):
    """renew prints the new expiry and how many links heard it."""
    h.d.handlers["identity.renew"] = {"cert_expires": 1_900_000_000, "links": [LINK, LINK]}
    code, out = h.run("renew")
    assert code == 0
    assert "announced_in_links: 2" in out


def test_cert_prints_or_writes_the_certificate_and_certify_reads_it_back(h, tmp_path):
    """cert goes to stdout or --out; certify sends that file's JSON to the daemon."""
    cert = {"device": "d" * 64, "sig": "x"}
    h.d.handlers.update({"identity.status": {"cert": cert}, "identity.certify": {"device": "d" * 64}})
    code, out = h.run("cert")
    assert code == 0
    assert json.loads(out) == cert  # piped (agent mode): the certificate itself, so `> cert.json` works
    assert json.loads(h.run("cert", json=True)[1]) == cert  # --json: the certificate, as before
    target = tmp_path / "cert.json"
    code, out = h.run("cert", out=str(target))
    assert json.loads(target.read_text(encoding="utf-8")) == cert
    assert "hand the file to a device" in out
    assert f"link add-device <link> {target}" in out
    code, out = h.run("certify", str(target))
    assert code == 0
    assert h.params("identity.certify") == {"cert": cert}
    assert out == f"device: {'d' * 16}\nrecorded: a device of this fleet\n"


# ------------------------------------------------------------------------------------------ links


def test_create_writes_both_local_policies(h, home):
    """create passes kinds as a list and leaves manual promote.toml and default export.toml."""
    h.d.handlers["link.create"] = {"link": LINK, "name": "ops", "fingerprint": "fp"}
    code, out = h.run("create", "ops", kinds="chat, note", retention_days=30)
    assert code == 0
    assert out.startswith(f"name: ops\nlink: {LINK}\nfingerprint: fp\nrole: owner")
    assert "link invite ops" in out
    assert h.params("link.create") == {"name": "ops", "kinds": ["chat", "note"], "retention_days": 30}
    assert promote.load_policy(LINK) == {"mode": "manual", "rules": []}
    assert (lc.state_dir() / LINK / "export.toml").is_file()


def test_list_with_and_without_links(h):
    """list prints one row per link with alarms flagged, or the way to make one."""
    h.d.handlers["link.list"] = []
    out = h.run("list")[1]
    assert out.startswith("total: 0\nlinks: []")
    assert "link create <name>" in out
    h.d.handlers["link.list"] = [
        {"name": "ops", "link": LINK, "role": None, "members": 2, "epoch": 3, "alarms": 1},
    ]
    out = h.run("list")[1]
    assert "total: 1\nlinks[1]{name,link,role,members,epoch,alarms}:" in out
    assert f"ops,{LINK[:16]},null,2,3,1" in out
    assert "link status ops" in out  # the alarmed link is the one to look at


def test_status_text_shows_members_devices_receipts_and_alarms(h):
    """status renders every part of a link: roles, verification, device states, receipts, alarms."""
    dev = {"label": "pc", "device": "1" * 64, "head": 9, "last_contact": None, "removed": False, "cert_expired": False}
    s = status(
        rotation_due=True,
        members=[
            member("home", OUR_ROOT, us=True),
            member(
                "serge",
                THEIR_ROOT,
                verified=False,
                devices=[dev, {**dev, "frozen": True}, {**dev, "cert_expired": True}],
            ),
            member("gone", "9" * 64, removed=True, devices=[{**dev, "removed": True}]),
            member("wait", "8" * 64, pending=True, devices=[]),
        ],
        pending_joins=[{"join": "j" * 64, "label": "wait", "needs_approval": True}],
        live_sessions=[{}],
        quarantine_unpromoted=3,
        sent=[{"seq": 4, "kind": "chat", "receipts": []}, {"seq": 5, "kind": "note", "receipts": ["serge"]}],
        alarms=[{"kind": "fork", "author": "a" * 64, "detail": "two heads"}],
        sequencer={
            "device": "e" * 64,
            "label": "serge/pc",
            "term": 3,
            "handoff_to": "f" * 64,
            "next": "f" * 64,
            "next_label": "home/laptop",
            "next_term": 4,
            "me": False,
        },
        equivocation={"term": 3, "seq": 12, "sequencer": "e" * 64, "ours": "a" * 64, "theirs": "b" * 64},
        proposals=[
            {"id": "1" * 64, "kind": "invite", "status": "queued", "why": None, "at": 1_700_000_000},
            {"id": "2" * 64, "kind": "set_role", "status": "refused", "why": "no admin", "at": 1_700_000_000},
        ],
    )
    h.d.handlers.update({"link.list": [{"link": LINK}], "link.status": s})
    code, out = h.run("status")
    assert code == 0
    assert h.params("link.status") == {"link": LINK}, "no link named: every link"
    for needle in (
        "ROTATION DUE",
        "home,owner,us",
        "serge,writer,no",
        "gone,removed,yes",
        "wait,pending,yes",
        ",never,ok",
        ",frozen",
        ",cert expired",
        ",removed",
        f"pending_joins[1]{{join,from,needs_accept}}:\n  {'j' * 16},wait,true",
        "live_sessions: 1",
        "quarantine_unpromoted: 3",
        "4,chat,nobody yet",
        "5,note,serge",
        "fork,aaaaaaaaaaaaaaaa,two heads",
        'sequencer: "serge/pc (eeeeeeeeeeeeeeee), term 3"',
        "HANDOFF to home/laptop (ffffffffffffffff)",
        "starts term 4",
        "EQUIVOCATION: the sequencer signed two entries at term 3 seq 12",
        "halted at seq 11",
        "aurora link takeover ops --phrase-stdin",
        "proposal 1111111111111111 invite waits for the sequencer",
        "proposal 2222222222222222 set_role REFUSED by the sequencer: no admin",
        # the open items, as next steps
        "link verify ops --mark",
        f"link accept ops {'j' * 16}",
        "link inbox ops",
    ):
        assert needle in out, needle
    h.d.handlers["link.list"] = []
    code, out = h.run("status")
    assert code == 0
    assert out.startswith("total: 0\nlinks: []")


def test_invite_passes_ttl_and_writes_an_offline_bundle(h, tmp_path):
    """invite converts --ttl, honours --multi/--approval, and --out writes code + log, not to stdout."""
    h.d.handlers["link.invite"] = {
        "code": "aurora-invite1:abc",
        "acl": [{"e": 1}],
        "role": "writer",
        "expires": 1_900_000_000,
        "approval": True,
        "fingerprint": "fp",
    }
    target = tmp_path / "invite.json"
    code, out = h.run("invite", "ops", ttl="2h", multi=True, approval=True, role="writer", out=str(target))
    assert code == 0
    assert h.params("link.invite") == {
        "link": "ops",
        "role": "writer",
        "ttl_s": 7200,
        "single_use": False,
        "approval": True,
    }
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "v": 1,
        "kind": "aurora-link-invite",
        "code": "aurora-invite1:abc",
        "acl": [{"e": 1}],
    }
    assert 'code: "aurora-invite1:abc"' in out
    assert "needs_approval: true" in out
    assert 'uses: "many, until it expires"' in out
    assert f"bundle: {target}" in out
    assert "link accept ops <join id>" in out
    assert "'e': 1" not in out
    assert '"e"' not in out


def test_invite_with_a_bad_ttl_is_a_usage_error(h):
    """A malformed --ttl stops before the daemon is asked."""
    code, out = h.run("invite", "ops", ttl="soon")
    assert code == 2
    assert "--ttl takes" in out
    assert h.d.calls == []


JOINED = {
    "name": "ops",
    "link": LINK,
    "pending": True,
    "their_fingerprint": "theirs",
    "fingerprint_matches_code": True,
    "our_fingerprint": "ours",
    "safety_number": "12345",
}


def test_join_by_code_shows_the_safety_number(h):
    """A code joins online; the safety number and the verify step are printed."""
    h.d.handlers["link.join"] = dict(JOINED)
    code, out = h.run("join", "aurora-invite1:abc", label="home")
    assert code == 0
    assert h.params("link.join") == {"code": "aurora-invite1:abc", "label": "home"}
    assert "state: pending" in out
    assert "waiting for the inviter to accept" in out
    assert 'safety_number: "12345"' in out
    assert "link verify ops --mark" in out
    assert h.networks == [True]


def test_join_from_an_invite_file_works_offline_and_writes_the_return_bundle(h, tmp_path):
    """An invite.json supplies code and acl; the join bundle goes to --out for the inviter."""
    inv = tmp_path / "invite.json"
    inv.write_text(json.dumps({"code": "aurora-invite1:abc", "acl": [{"e": 1}]}), encoding="utf-8")
    back = tmp_path / "join.json"
    h.d.handlers["link.join"] = {**JOINED, "pending": False, "bundle": {"entries": [2]}}
    code, out = h.run("join", str(inv), out=str(back))
    assert code == 0
    assert h.params("link.join") == {"code": "aurora-invite1:abc", "acl": [{"e": 1}]}
    assert json.loads(back.read_text(encoding="utf-8")) == {"entries": [2]}
    assert f"hand {back} back to the inviter" in out


def test_join_with_a_fingerprint_mismatch_exits_3(h):
    """When the log's owner is not who the code named, join says MISMATCH and exits 3."""
    h.d.handlers["link.join"] = {**JOINED, "fingerprint_matches_code": False, "bundle": {"x": 1}}
    code, out = h.run("join", "aurora-invite1:abc")
    assert code == 3
    assert "fingerprint_matches_code: false" in out
    assert "MISMATCH" in out
    assert "(pass --out FILE)" in out
    assert "--mark" not in out  # nothing to mark verified when the owner is not who the code named


def test_accept_decline_and_verify(h):
    """accept/decline name the entry; verify lists safety numbers and asks for --mark."""
    h.d.handlers.update(
        {
            "link.accept": {"entry": "1" * 64},
            "link.decline": {"entry": "2" * 64},
            "link.verify": [{"label": "serge", "safety_number": "777", "verified": False}],
        }
    )
    code, out = h.run("accept", "ops", "j1")
    assert code == 0
    assert out == (
        f'link: ops\nchange: join accepted\nstate: applied\nentry: "{"1" * 16}"\n'
        "effect: the read key is wrapped to them\n"
    )
    assert h.params("link.accept") == {"link": "ops", "join": "j1"}
    assert h.run("decline", "ops", "j2") == (
        0,
        f'link: ops\nchange: join declined\nstate: applied\nentry: "{"2" * 16}"\n',
    )
    code, out = h.run("verify", "ops")
    assert code == 0
    assert 'members[1]{fleet,safety_number,verified}:\n  serge,"777",no' in out
    assert "unverified: 1" in out
    assert "link verify ops serge --mark" in out
    assert h.params("link.verify") == {"link": "ops", "mark": False}
    _code, out = h.run("verify", "ops", "serge", mark=True)
    assert "--mark" not in out
    assert h.d.calls[-1] == (
        "link.verify",
        {"link": "ops", "member": "serge", "mark": True},
    )
    h.d.handlers["link.verify"] = []  # nobody else in the link: an explicit zero, and the way in
    _code, out = h.run("verify", "ops")
    assert out.startswith("link: ops\ntotal: 0\nmembers: []")
    assert "link invite ops" in out


def test_membership_changes_report_entry_epoch_and_due_rotation(h):
    """remove-member, set-role, rotate-key, revoke-invite, remove-device and leave share one shape."""
    h.d.handlers.update(
        {
            "link.remove_member": {"entry": "3" * 64, "epoch": 4, "rotation_due": True},
            "link.set_role": {"entry": "4" * 64, "epoch": 4},
            "link.rotate_key": {"entry": "5" * 64, "epoch": 5},
            "link.revoke_invite": {"entry": "6" * 64, "epoch": 5},
            "link.remove_device": {"entry": "7" * 64, "epoch": 6},
            "link.leave": {"entry": "8" * 64, "epoch": 6},
        }
    )
    code, out = h.run("remove-member", "ops", "serge")
    assert code == 0
    assert "change: member removed" in out
    assert "epoch: 4" in out
    assert "rotation_due: the sequencer appends it" in out
    assert "link status ops" in out
    assert h.params("link.remove_member") == {"link": "ops", "member": "serge"}
    assert h.run("set-role", "ops", "serge", "admin")[0] == 0
    assert h.params("link.set_role") == {"link": "ops", "member": "serge", "role": "admin"}
    for action, args, method in [
        ("rotate-key", ("ops",), "link.rotate_key"),
        ("revoke-invite", ("ops", "inv"), "link.revoke_invite"),
        ("remove-device", ("ops", "dev"), "link.remove_device"),
        ("leave", ("ops",), "link.leave"),
    ]:
        code, out = h.run(action, *args)
        assert code == 0, action
        assert out.startswith("link: ops\nchange: "), action
        assert "state: applied" in out, action
        assert "rotation" not in out, action
        assert "help" not in out, action  # applied and nothing due: the confirmation is the answer
        assert h.d.calls[-1][0] == method


def test_a_change_made_off_the_sequencer_is_reported_as_a_proposal(h):
    """On a device that does not sequence the link a change is a proposal: the CLI says so and
    names the sequencer; a due rotation is the sequencer's."""
    h.d.handlers["link.remove_member"] = {
        "proposal": "9" * 64,
        "queued": True,
        "sequencer": "a" * 64,
        "epoch": 4,
        "rotation_due": False,
    }
    code, out = h.run("remove-member", "ops", "serge")
    assert code == 0
    assert f'state: proposed\nproposal: "{"9" * 16}"\nsequencer: {"a" * 16}' in out
    assert "the sequencer includes it when a sync reaches it" in out
    assert "link status ops" in out
    h.d.handlers["link.accept"] = {"proposal": "8" * 64, "queued": True, "sequencer": "a" * 64}
    _code, out = h.run("accept", "ops", "j")
    assert 'change: join accepted\nstate: proposed\nproposal: "8888888888888888"' in out


def test_handoff_names_the_device_and_takeover_needs_the_root(h, monkeypatch):
    """handoff passes the target device; takeover refuses without the root, reads the phrase from
    stdin, and passes --after."""
    h.d.handlers["link.handoff"] = {"entry": "4" * 64, "epoch": 2}
    code, out = h.run("handoff", "ops", "abcd1234")
    assert code == 0
    assert out.startswith('link: ops\nchange: sequencer handed off\nstate: applied\nentry: "4444444444444444"')
    assert h.params("link.handoff") == {"link": "ops", "device": "abcd1234"}
    assert h.run("takeover", "ops")[0] == 2, "no phrase, no passphrase: a usage error before any call"
    assert not any(m == "link.takeover" for m, _ in h.d.calls)
    monkeypatch.setattr(sys, "stdin", io.StringIO("word " * 24 + "\n"))
    h.d.handlers["link.takeover"] = {"entry": "5" * 64, "term": 4, "seq": 12, "sequencer": "e" * 64}
    code, out = h.run("takeover", "ops", phrase_stdin=True, after=11)
    assert code == 0
    assert h.params("link.takeover") == {"link": "ops", "phrase": ("word " * 24).strip(), "after": 11}
    assert "term: 4\nstarts_at_seq: 12" in out


def test_add_device_reads_the_certificate_file(h, tmp_path):
    """add-device sends the cert file's JSON and says the device now holds the read key."""
    cert = tmp_path / "cert.json"
    cert.write_text(json.dumps({"device": "d"}), encoding="utf-8")
    h.d.handlers["link.add_device"] = {"entry": "9" * 64, "epoch": 2}
    code, out = h.run("add-device", "ops", str(cert))
    assert code == 0
    assert h.params("link.add_device") == {"link": "ops", "cert": {"device": "d"}}
    assert out.startswith(f'link: ops\nchange: device added\nstate: applied\nentry: "{"9" * 16}"')
    assert "effect: it now holds the read key" in out


# --------------------------------------------------------------------------------------- the mail


def mail_daemon(h: Harness, monkeypatch, rec_status: str = "admitted") -> None:
    """Quarantine on the store (bus offline), one record REC, promotion recorded once."""
    monkeypatch.setattr(quarantine, "redis_client", lambda: None)
    rec = event(1, rid=REC)
    rec.update(status=rec_status, seq=7, promoted=None)
    h.d.handlers.update(
        {
            "link.status": status(),
            "events.wait": {"events": [event(1, rid=REC)]},
            "record.get": rec,
            "promotion.record": {"first": True},
        }
    )


def test_inbox_lists_quarantine_or_says_it_is_empty(h, monkeypatch):
    """inbox shows id, kind, fleet/seat claim, address and content; empty says so."""
    mail_daemon(h, monkeypatch)
    code, out = h.run("inbox", "ops", limit="5")
    assert code == 0
    assert "records[1]{record,kind,from,to,content}:" in out
    assert f"{REC[:12]},chat,serge/chronos,@home/claude,msg 1" in out
    assert f"link show ops {REC[:12]}" in out
    h.d.handlers["events.wait"] = {"events": []}
    assert h.run("inbox", "ops")[1].startswith("link: ops\nquarantined: 0\nrecords: []")


def test_show_resolves_a_record_prefix_from_the_quarantine(h, monkeypatch):
    """show accepts an id prefix, then prints provenance, status and content."""
    mail_daemon(h, monkeypatch)
    code, out = h.run("show", "ops", REC[:6])
    assert code == 0
    assert h.params("record.get") == {"link": "ops", "record_id": REC}
    assert out.startswith(f"record: {REC}")
    assert "from: serge/chronos" in out
    assert "seq: 7" in out
    assert "status: admitted" in out
    assert "content: msg 1" in out
    assert f"link promote ops {REC[:12]}" in out
    code, out = h.run("show", "ops", "zzz")
    assert code == 2
    assert "no quarantined record starts with 'zzz'" in out


def test_promote_with_yes_puts_the_record_on_the_bus(h, monkeypatch):
    """--yes skips the prompt; the promoter defaults to person:<user>."""
    mail_daemon(h, monkeypatch)
    bus = StubBus()
    import core.comm.bus as bus_mod

    monkeypatch.setattr(bus_mod, "Bus", lambda _n: bus)
    monkeypatch.setattr(cli.getpass, "getuser", lambda: "dan")
    code, out = h.run("promote", "ops", REC, yes=True)
    assert code == 0
    assert out == f"record: {REC[:12]}\npromoted_to: claude\nbus_id: 17-0\nauthority: none\n"
    assert h.params("promotion.record")["by"] == "person:dan"
    assert bus.sent[0][0] == "claude"


def test_promote_without_yes_needs_a_terminal(h, monkeypatch):
    """Off a terminal and without --yes, promotion is refused (exit 2) and nothing is recorded."""
    mail_daemon(h, monkeypatch)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    code, out = h.run("promote", "ops", REC)
    assert code == 2
    assert "confirm on a terminal" in out
    assert "promotion.record" not in h.d.methods()


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_promote_on_a_terminal_asks_first(h, monkeypatch):
    """On a terminal the record is shown and only `y` promotes; anything else exits 1."""
    mail_daemon(h, monkeypatch)
    monkeypatch.setattr(sys, "stdin", Tty())
    answers = iter(["n", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    code, out = h.run("promote", "ops", REC)
    assert code == 1
    assert "from serge/chronos [chat]: msg 1" in out
    assert out.endswith("not promoted\n")
    bus = StubBus()
    import core.comm.bus as bus_mod

    monkeypatch.setattr(bus_mod, "Bus", lambda _n: bus)
    code, out = h.run("promote", "ops", REC, by="person:x", to="sol")
    assert code == 0
    assert bus.sent[0][0] == "sol"


def test_promote_already_promoted_sends_nothing(h, monkeypatch):
    """A record already promoted is reported, exit 0, nothing on the bus."""
    mail_daemon(h, monkeypatch)
    h.d.handlers["promotion.record"] = {"first": False}
    code, out = h.run("promote", "ops", REC, yes=True)
    assert code == 0
    assert "promoted: false\nreason: already promoted; nothing sent" in out
    assert "--again" in out


def test_promote_of_a_refused_record_is_exit_1(h, monkeypatch):
    """PromotionRefused surfaces as `refused:` with exit 1."""
    mail_daemon(h, monkeypatch, rec_status="own")
    code, out = h.run("promote", "ops", REC, yes=True)
    assert code == 1
    assert out.startswith('error: "refused: record is own')
    assert "code: REFUSED" in out


def test_promote_legacy_needs_to_and_confirmation(h, monkeypatch):
    """Legacy mail needs --to and a confirmation, then goes through legacy.promote_legacy."""
    from core.link import legacy

    seen: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        legacy,
        "promote_legacy",
        lambda rid, by, to: seen.append((rid, by, to)) or {"record_id": rid, "seat": to},
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert "say --to <seat>" in h.run("promote", "legacy", "m1")[1]
    assert "confirm on a terminal" in h.run("promote", "legacy", "m1", to="claude")[1]
    code, out = h.run("promote", "legacy", "m1", to="claude", yes=True, by="person:t")
    assert code == 0
    assert seen == [("m1", "person:t", "claude")]
    assert "source: unverified legacy mail" in out


def test_blob_writes_the_attachment_to_an_absolute_path(h, monkeypatch, tmp_path):
    """blob resolves the record and hands the daemon an absolute output path."""
    mail_daemon(h, monkeypatch)
    h.d.handlers["blob.get"] = lambda p: {"bytes": 12, "out": p["out"]}
    target = tmp_path / "a.log"
    code, out = h.run("blob", "ops", REC[:8], "a.log", out=str(target))
    p = h.params("blob.get")
    assert code == 0
    assert p == {"link": "ops", "record_id": REC, "blob": "a.log", "out": str(target.resolve())}
    assert out == f"wrote: {target.resolve()}\nbytes: 12\n"


def test_send_writes_to_the_feed_through_the_exporter(h):
    """send joins the words, defaults to chat, and prints the new record id."""
    h.d.handlers.update(
        {"link.list": [{"link": LINK, "name": "ops"}], "link.status": status(), "link.send": {"record_id": REC}}
    )
    code, out = h.run("send", "claude", "@serge/chronos", "hello", "there")
    assert code == 0
    assert out.startswith(f"record: {REC[:12]}\nfrom: claude\nto: @serge/chronos\nkind: chat")
    assert "written to our feed" in out
    body = h.params("link.send")["body"]
    assert body == {"kind": "chat", "seat": "claude", "to": "@serge/chronos", "content": "hello there"}


def test_send_to_an_unknown_fleet_is_refused(h):
    """An address no link knows is `refused:` with exit 1."""
    h.d.handlers.update({"link.list": [{"link": LINK, "name": "ops"}], "link.status": status()})
    code, out = h.run("send", "claude", "@nobody/x", "hi")
    assert code == 1
    assert "refused: no link here has a member fleet called 'nobody'" in out


def test_export_needs_out_and_writes_the_bundle(h, tmp_path):
    """export refuses without --out, then writes the whole bundle."""
    assert h.run("export", "ops")[1].startswith("error: export needs --out FILE\ncode: USAGE")
    h.d.handlers["bundle.export"] = {"acl": [1, 2], "records": [3]}
    target = tmp_path / "bundle.json"
    code, out = h.run("export", "ops", out=str(target))
    assert code == 0
    assert json.loads(target.read_text(encoding="utf-8")) == {"acl": [1, 2], "records": [3]}
    assert out.startswith(f"link: ops\nwrote: {target}\nacl_entries: 2\nrecords: 1")
    assert f"link import {target}" in out


def test_import_merges_a_bundle_but_refuses_an_invite(h, tmp_path):
    """import sends a bundle to the daemon; an invite file is pointed at `join` instead."""
    inv = tmp_path / "invite.json"
    inv.write_text(json.dumps({"kind": "aurora-link-invite"}), encoding="utf-8")
    code, out = h.run("import", str(inv))
    assert code == 2
    assert "use `aurora link join`" in out
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"acl": [], "records": []}), encoding="utf-8")
    h.d.handlers["bundle.import"] = {"link": LINK, "acl_entries": 2, "records_stored": 5, "records_refused": 1}
    code, out = h.run("import", str(bundle))
    assert code == 0
    assert "records_stored: 5\nrecords_refused: 1" in out
    assert f"link inbox {LINK[:16]}" in out
    assert h.params("bundle.import") == {"bundle": {"acl": [], "records": []}}


def test_policy_writes_both_defaults_for_the_resolved_link(h, home):
    """policy resolves the link id and writes promote.toml and export.toml there."""
    h.d.handlers["link.status"] = status()
    code, out = h.run("policy", "ops")
    assert code == 0
    assert "scope: both are local and never synced" in out
    assert "promote.toml" in out
    assert (promote.policy_dir(LINK) / "promote.toml").is_file()
    assert (lc.state_dir() / LINK / "export.toml").is_file()


def test_rebuild_reports_the_count(h, monkeypatch):
    """rebuild replays the store into the stream and prints how many records."""
    monkeypatch.setattr(quarantine, "rebuild", lambda _c, link: 4 if link == "ops" else 0)
    assert h.run("rebuild", "ops") == (0, "link: ops\nrecords: 4\nhelp[1]:\n  uv run agent_cli.py link inbox ops\n")
    assert h.run("rebuild", "ops", json=True)[1] == "rebuilt the quarantine stream from the store: 4 record(s)\n"


def test_peer_remembers_dial_hints(h):
    """peer passes addresses and relay to peers.add."""
    h.d.handlers["peers.add"] = {}
    code, out = h.run("peer", "d" * 64, addr=["1.2.3.4:5"], relay_url="https://relay")
    assert code == 0
    assert h.params("peers.add") == {"device": "d" * 64, "addrs": ["1.2.3.4:5"], "relay": "https://relay"}
    assert out.startswith(f'device: {"d" * 16}\naddrs[1]: "1.2.3.4:5"\nrelay: "https://relay"')


def test_relay_config_prints_or_writes_the_toml(h, tmp_path):
    """relay-config prints the iroh-relay TOML, or writes it with the command to run."""
    toml = 'http_bind_addr = "[::]:3340"\naccess.allowlist = [\n  "' + "d" * 64 + '",\n]\n'
    h.d.handlers["relay.config"] = {"toml": toml, "devices": 3}
    code, out = h.run("relay-config")
    assert code == 0
    assert out == toml  # piped (agent mode): the file itself, so `> relay.toml` works
    assert h.run("relay-config", json=True) == (0, toml)  # --json: the file itself, as before
    target = tmp_path / "relay.toml"
    code, out = h.run("relay-config", out=str(target), bind="0.0.0.0:3340")
    assert code == 0
    assert target.read_text(encoding="utf-8") == toml
    assert f"wrote: {target}\ndevices: 3\nrun: iroh-relay --config-path {target}" in out
    assert h.d.calls[-1] == ("relay.config", {"http_bind": "0.0.0.0:3340"})


def test_import_legacy_reports_counts(h, monkeypatch):
    """import-legacy passes --dry-run through and prints imported/skipped."""
    from core.link import legacy

    seen: list[bool] = []
    monkeypatch.setattr(legacy, "import_parked", lambda dry: seen.append(dry) or {"imported": 2, "skipped": 1})
    code, out = h.run("import-legacy", dry_run=True)
    assert code == 0
    assert seen == [True]
    assert out.startswith("imported: 2\nskipped: 1\n")


def test_export_refused_on_policy_is_exit_1(h, home):
    """A kind export.toml forbids is refused with exit 1 and nothing is written."""
    export.write_default_policy(LINK).write_text('kinds = ["note"]\n', encoding="utf-8")
    h.d.handlers.update({"link.list": [{"link": LINK, "name": "ops"}], "link.status": status()})
    code, out = h.run("send", "claude", "@serge", "hi", kind="chat")
    assert code == 1
    assert "kind 'chat' may not leave" in out
    assert "link.send" not in h.d.methods()
