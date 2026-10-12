"""Pins for `bifrost-fetch` after the AXI conversion: the body stays verbatim, the receipts and
errors are structured.

The blob store is stubbed, so nothing here reads the disk or Redis.

Run: uv run pytest tests/test_axi_bifrost_fetch.py -q
"""

import argparse

import pytest

import agent_cli


class _Store:
    def __init__(self, blobs):
        self.blobs = blobs

    def get(self, ref):
        return self.blobs.get(ref)


@pytest.fixture
def store(monkeypatch):
    import core.comm.blobs as blobs

    holder = _Store({"blob:abc": b"line one\nline two END"})
    monkeypatch.setattr(blobs, "get_blob_store", lambda: holder)
    monkeypatch.setattr(agent_cli, "_fetch_bus_body", lambda mid, agent="": None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _fetch(capsys, **kw):
    ns = argparse.Namespace(get="", out="", agent="")
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_blob(ns)
    return code, capsys.readouterr().out


def test_the_body_is_printed_verbatim(store, capsys):
    code, text = _fetch(capsys, get="blob:abc")
    assert code == 0
    assert text == "line one\nline two END"


def test_out_is_a_receipt_with_the_byte_count(store, capsys, tmp_path):
    dest = tmp_path / "body.txt"
    code, text = _fetch(capsys, get="blob:abc", out=str(dest))
    assert code == 0
    assert "bytes: 21" in text
    assert dest.read_bytes() == b"line one\nline two END"


def test_a_miss_is_a_loud_not_found(store, capsys):
    code, text = _fetch(capsys, get="1234567890123-0")
    assert code == 1
    assert "code: NOT_FOUND" in text
    assert "--agent <agent_id>" in text  # a stream id may live in another seat's streams


def test_no_ref_is_a_usage_error(store, capsys):
    code, text = _fetch(capsys)
    assert code == 2
    assert "code: USAGE" in text
    assert "--get blob:<sha>" in text


def test_human_error_goes_to_stderr(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    code = agent_cli.cmd_blob(argparse.Namespace(get="blob:nope", out="", agent=""))
    captured = capsys.readouterr()
    assert code == 1
    assert "no blob or bus message for blob:nope" in captured.err
