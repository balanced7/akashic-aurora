"""Reach pins for arsenal.media: the toolbox is only worth something if an agent about to hand-roll ffmpeg is shown it.

Mining five days of runs (2026-10-12) found the house versions unused while agents rebuilt them hundreds of times; the
recall-at-action verb channel (core/recall/at_action.py, T311) reads agent_cli's parser help, so these commands must
surface `media`.
"""
from __future__ import annotations

import pytest

from core.recall import at_action


@pytest.mark.parametrize("command", [
    "ffmpeg -ss 12 -i a.mp4 -frames:v 1 x.png",
    "ffprobe -v error -show_streams clip.mp4",
    "ffmpeg -i rec.mp4 -af ebur128 -f null -",
])
def test_hand_rolled_ffmpeg_surfaces_the_media_verb(command):
    query = at_action._query_from(None, command)
    verbs = [v["verb"] for v in at_action._verbs(query, command=command, limit=3)]
    assert "media" in verbs, (query, verbs)


def test_media_verb_passes_through_to_the_toolbox(capsys):
    import agent_cli
    import argparse
    rc = agent_cli.cmd_media(argparse.Namespace(rest=[]))
    assert rc == 0
    assert "contact sheet" in capsys.readouterr().out
