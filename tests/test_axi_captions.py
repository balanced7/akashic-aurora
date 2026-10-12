"""Pins for `captions` after the AXI conversion. yt-dlp is never run: `fetch` is replaced.

Run: uv run pytest tests/test_axi_captions.py -q
"""

import argparse

import pytest

import agent_cli
from scripts import yt_captions


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(tmp_path):
    ns = argparse.Namespace(
        url="https://youtu.be/x", out=str(tmp_path), langs="en.*", keep_vtt=False, punctuate="hybrid"
    )
    return agent_cli.cmd_captions(ns)


def test_written_files_are_rows_with_their_size(monkeypatch, tmp_path, capsys):
    txt = tmp_path / "talk.en.txt"
    txt.write_text("Hello there. " * 10, encoding="utf-8")
    monkeypatch.setattr(yt_captions, "fetch", lambda *a, **k: [txt])
    assert _run(tmp_path) == 0
    out = capsys.readouterr().out
    assert "total: 1" in out
    assert "files[1]{file,chars}:" in out
    assert ",130" in out
    assert f"cat {txt}" in out


def test_missing_ytdlp_is_a_setup_error_with_the_install_command(monkeypatch, tmp_path, capsys):
    def missing(*a, **k):
        raise RuntimeError(yt_captions.MISSING_YTDLP_HINT)

    monkeypatch.setattr(yt_captions, "fetch", missing)
    assert _run(tmp_path) == 2
    out = capsys.readouterr().out
    assert "code: YTDLP_MISSING" in out
    assert "install" in out
    assert "yt-dlp" in out


def test_no_tracks_is_said_with_a_wider_langs_hint(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(yt_captions, "fetch", lambda *a, **k: [])
    assert _run(tmp_path) == 1
    out = capsys.readouterr().out
    assert "code: NO_CAPTIONS" in out
    assert "--langs all" in out
