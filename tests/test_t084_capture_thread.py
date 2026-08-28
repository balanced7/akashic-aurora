"""T084 S2 pre-registered pins — subject-bound bus thread capture."""
from __future__ import annotations

import argparse
import asyncio
import json


def _fields(frm, to, kind, content, ts, sha, meta=None):
    return {
        "frm": frm,
        "to": to,
        "kind": kind,
        "content": json.dumps(content),
        "ts": ts,
        "sha": sha,
        "meta": json.dumps(meta or {}),
        "parts": "[]",
    }


class FakeRedis:
    def __init__(self, streams, lengths=None, aliases=None):
        self.streams = streams
        self.lengths = lengths or {k: len(v) for k, v in streams.items()}
        self.aliases = aliases or {}
        self.calls = []

    def xrevrange(self, key, count=None, **_kw):
        self.calls.append(("xrevrange", key, count))
        return list(reversed(self.streams.get(key, [])))[:count]

    def xlen(self, key):
        self.calls.append(("xlen", key))
        return self.lengths.get(key, 0)

    def get(self, key):
        self.calls.append(("get", key))
        return self.aliases.get(key)


def _fixture():
    streams = {
        "bifrost:inbox:sol": [
            ("1000-0", _fields("claude", "sol", "question", "First verbatim body",
                               "2026-08-28T01:00:00Z", "sha-a",
                               {"thread_id": "thread-7"})),
            # Content resemblance is not linkage and must stay out.
            ("1002-0", _fields("kimi", "sol", "chat", "I happened to say thread-7",
                               "2026-08-28T01:02:00Z", "sha-c")),
        ],
        "bifrost:work:inbox:sol": [
            # Dual-write copy: different stream id, same packet sha.
            ("1000-1", _fields("claude", "sol", "question", "First verbatim body",
                               "2026-08-28T01:00:00Z", "sha-a",
                               {"thread_id": "thread-7"})),
        ],
        "bifrost:broadcast": [
            ("1001-0", _fields("sol", "*", "reply", "Second **verbatim** body",
                               "2026-08-28T01:01:00Z", "sha-b",
                               {"answers": "1000-0", "reply_id": "reply-7"})),
        ],
        "bifrost:work:broadcast": [],
    }
    return FakeRedis(streams)


def test_thread_capture_is_strict_deduplicated_bounded_and_read_only():
    from core.comm.thread_capture import collect_thread

    client = _fixture()
    result = collect_thread("sol", "thread-7", client=client, namespace="bifrost",
                            per_stream=50)

    assert result["schema"] == "capture.thread.v1"
    assert result["subject"] == "sol"
    assert result["thread_ref"] == "thread-7"
    assert result["found"] is True
    assert result["effects"] == []
    assert [row["content"] for row in result["messages"]] == [
        "First verbatim body", "Second **verbatim** body"]
    assert len(result["messages"][0]["copies"]) == 2
    assert result["bounds"]["duplicates_collapsed"] == 1
    assert result["bounds"]["ordering"] == "timestamp then stream id ascending"
    assert result["bounds"]["truncated"] is False
    assert result["blind"] == []

    operations = {call[0] for call in client.calls}
    assert operations <= {"xrevrange", "xlen", "get"}
    read_keys = {call[1] for call in client.calls if call[0] in {"xrevrange", "xlen"}}
    assert "bifrost:inbox:sol" in read_keys
    assert not any("inbox:rill" in key or "inbox:claude" in key for key in read_keys)


def test_thread_membership_never_uses_body_substrings():
    from core.comm.thread_capture import collect_thread

    result = collect_thread("sol", "thread-7", client=_fixture(), namespace="bifrost")
    assert all("happened to say" not in row["content"] for row in result["messages"])


def test_archive_truncation_and_not_found_are_loud():
    from core.comm.thread_capture import collect_thread

    client = _fixture()
    client.lengths["bifrost:inbox:sol"] = 500
    result = collect_thread("sol", "missing-thread", client=client,
                            namespace="bifrost", per_stream=2)
    assert result["found"] is False
    assert result["messages"] == []
    assert result["bounds"]["truncated"] is True
    assert any("not found" in item.lower() for item in result["blind"])
    assert any("truncated" in item.lower() for item in result["blind"])


def test_atom_payload_preserves_attribution_bounds_and_citation_edges():
    from core.comm.thread_capture import atom_payload, collect_thread

    snap = collect_thread("sol", "thread-7", client=_fixture(), namespace="bifrost")
    payload = atom_payload(snap, title="verb discussion", cites=["art_design_1"])

    assert payload["type_"] == "chronicle"
    assert payload["status"] == "draft"
    assert payload["origin"] == "conversation"
    assert payload["source_thread"] == "thread-7"
    assert payload["body_type"] == "transcript"
    assert payload["citations"] == [{"target": "art_design_1", "rel": "discusses"}]
    assert payload["speakers"] == ["claude", "sol"]
    assert "First verbatim body" in payload["body"]
    assert "Second **verbatim** body" in payload["body"]
    assert "subject-bound archive view" in payload["body"]
    assert "duplicates collapsed: 1" in payload["body"]


def test_mint_uses_atom_authority_and_returns_projection_receipt(tmp_path):
    from core.comm.thread_capture import collect_thread, mint_thread_atom

    snap = collect_thread("sol", "thread-7", client=_fixture(), namespace="bifrost")
    calls = {}

    class Family:
        def mint(self, type_, title, body, **kwargs):
            calls.update(type_=type_, title=title, body=body, kwargs=kwargs)
            return {"id": "art_thread_7", "header": {"type": type_}}

    def render(atom, repo_root=""):
        calls["render"] = (atom["id"], repo_root)
        return str(tmp_path / "thread.md")

    receipt = mint_thread_atom(snap, title="verb discussion", cites=["art_design_1"],
                               family=Family(), render_fn=render,
                               repo_root=str(tmp_path))
    assert receipt["atom_id"] == "art_thread_7"
    assert receipt["projection"].endswith("thread.md")
    assert calls["kwargs"]["status"] == "draft"
    assert calls["kwargs"]["origin"] == "conversation"


def test_cli_parser_keeps_thread_as_a_capture_mode_not_a_second_verb():
    import agent_cli

    parser = agent_cli.build_parser()
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "capture" in subs.choices
    assert "capture-thread" not in subs.choices
    args = parser.parse_args(["capture", "--thread", "thread-7", "--agent", "sol", "--json"])
    assert args.thread == "thread-7"
    assert args.agent == "sol"


def test_native_mcp_and_toolbox_capture_share_the_core_seam(monkeypatch, tmp_path):
    import ai_setup_mcp
    from core.comm import thread_capture
    from core.comm.toolbox import TOOLS, ToolBox

    snap = thread_capture.collect_thread("sol", "thread-7", client=_fixture(),
                                         namespace="bifrost")
    monkeypatch.setattr(thread_capture, "collect_thread", lambda *a, **k: snap)
    advertised = {row["function"]["name"] for row in TOOLS}
    assert "capture" in advertised

    raw = asyncio.run(ai_setup_mcp.capture(agent="sol", thread="thread-7",
                                            as_doc=False, title="", cites=[]))
    assert json.loads(raw)["schema"] == "capture.thread.v1"

    tb = ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *_: False, agent_id="sol")
    monkeypatch.setattr(tb, "_agent_cli", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("capture must not shell through agent_cli")))
    assert json.loads(tb.capture(thread="thread-7"))["subject"] == "sol"


def test_native_capture_requires_a_bound_subject(tmp_path):
    from core.comm.toolbox import ToolBox

    tb = ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *_: False)
    try:
        tb.capture(thread="thread-7")
    except ValueError as exc:
        assert "subject is required" in str(exc)
    else:
        raise AssertionError("unbound ToolBox borrowed another seat")
