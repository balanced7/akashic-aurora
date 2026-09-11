"""A console message that came from Discord must say so -- one timeline, visible origin.

DANIEL, verbatim, 2026-09-11 (on Discord, from work): "Also do we have any way of integrating
discord to the Bifrost so that you have one place to check and see instead of two? This way
messages naturally interleve and you dont have to do mental math to reconcile" -- and, to the
offer of a small mark on console messages that came from his phone: "Yes please ^___^!!!!!!!".

WHAT WAS ALREADY TRUE, measured before this pin: the console reads every inbox plus the
broadcast (core/comm/room_feed.streams_for), so Discord-origin messages already interleave in
its one timeline, and _fmt passes meta through to the browser; the gateway stamps
meta.source="discord" on everything it relays (core/comm/discord_inbound.py). What was missing
is only the reader-visible mark: renderMsg drew a Discord line exactly like a console line, so
the one timeline hid which door each line came through.

THE CONTRACT: renderMsg -- the single DOM builder for live messages and scrolled-back history
(addMsg and prependOlder both call it) -- renders a small "via Discord" mark in the message
row when, and only when, meta.source is "discord". A console message carries no mark.

BEHAVIOURAL, not structural: the pin AST-extracts the PAGE constant exactly as served (the
C10-1 method in tests/test_ui_scripts_parse.py), cuts renderMsg out of it, and executes it in
node with minimal stubs. No node = LOUD SKIP, the same rule as C10-1.

Run::

    py -m pytest tests/test_console_marks_discord_origin.py -q
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_PATH = os.path.join(REPO, "scripts", "bifrost_ui.py")
NODE = shutil.which("node")

HARNESS = r"""
const document = { createElement: (tag) => ({ tag, className: '', innerHTML: '', dataset: {}, setAttribute() {} }) };
const esc = (s) => String(s == null ? '' : s);
const cls = (f) => String(f);
const name = (f) => String(f);
const initials = (n) => String(n).slice(0, 2);
const now = (ts) => 'T';
const epiGlyph = (m) => ({ tier: 'unknown', glyph: '?', marker: '', unknown: true });
const _msgRenderer = (m) => String(m.content || '');
%RENDER%
const out = {
  discord: renderMsg({ from: 'daniil', to: 'claude', kind: 'chat', content: 'hello from my phone', ts: '', meta: { source: 'discord', operator: true } }).innerHTML,
  console: renderMsg({ from: 'user', to: 'claude', kind: 'chat', content: 'hello from the console', ts: '', meta: { via: 'console' } }).innerHTML,
  nometa: renderMsg({ from: 'deepseek', to: '*', kind: 'reply', content: 'a seat reply', ts: '' }).innerHTML,
};
process.stdout.write(JSON.stringify(out));
"""


def _page() -> str:
    """The PAGE template exactly as served: AST-extract, zero import side effects."""
    with open(UI_PATH, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "PAGE":
                    return node.value.value
    pytest.fail("PAGE constant not found in bifrost_ui.py -- the serve path moved; re-anchor this pin.")


def _render_msg_source(page: str) -> str:
    m = re.search(r"function renderMsg\(m\)\{.*?\n\}\n", page, re.S)
    assert m, "renderMsg not found in PAGE -- the render path moved; re-anchor this pin, do not delete it."
    return m.group(0)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    if not NODE:
        pytest.skip("node not on PATH -- this pin executes renderMsg and cannot verify the "
                    "Discord mark without it; install node (the CI runners ship it)")
    js = tmp_path_factory.mktemp("via_discord") / "render.js"
    js.write_text(HARNESS.replace("%RENDER%", _render_msg_source(_page())), encoding="utf-8")
    r = subprocess.run([NODE, str(js)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"renderMsg harness failed: {r.stderr[-800:]}"
    return json.loads(r.stdout)


def _row(html: str) -> str:
    """The message row: everything before the content div."""
    return html.split('<div class="content">')[0]


def test_p0_a_discord_message_carries_a_via_discord_mark_in_its_row(rendered):
    row = _row(rendered["discord"])
    assert "via Discord" in row, (
        "a message relayed from Discord renders exactly like a console line: " + row[-300:])


def test_p1_a_console_message_carries_no_discord_mark(rendered):
    assert "via Discord" not in rendered["console"]


def test_p2_a_seat_message_without_meta_renders_and_carries_no_mark(rendered):
    html = rendered["nometa"]
    assert 'class="who' in html and "via Discord" not in html


def test_p3_the_mark_has_a_style_rule_beside_the_other_row_badges():
    assert re.search(r"\n\s*\.via\{[^}]+\}", _page()), "no .via style rule in the PAGE stylesheet"
