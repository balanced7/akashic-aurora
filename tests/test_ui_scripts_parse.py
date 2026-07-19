"""C10-1 pin: every script the Bifrost console serves must PARSE.

The 2026-07-19 incident: a T002 trace-collapse block was spliced INTO the argument list of
a `registerVariant(...)` call in the PAGE template (scripts/bifrost_ui.py:2269-2272). The
entire 85KB inline script became a SyntaxError at page load: chrome rendered, but no
EventSource, no feed, no agent cards -- and the console surfaced ZERO errors (page-load
parse failures fire before any console attach). Because the console serves the WORKING TREE
live, the broken intermediate state was production, invisible until the next relaunch
(failure-ledger C10 "serve-from-working-tree exposure").

This pin extracts exactly what the server ships -- the PAGE constant (served verbatim by
`_html()`) and every `_static("scripts/*.js", ...)` module route in do_GET -- and parse-checks
each with `node --check` (real parser, real line numbers). No node = LOUD SKIP, never a
homemade lexer: the first draft's delimiter-balance fallback false-positived on regex
literals containing backticks (PAGE line 15, /`([^`\n]+)`/g) -- regex-vs-division needs a
real parser, and a gate that cries wolf on valid code teaches people to ignore it.
"""
import ast
import os
import re
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_PATH = os.path.join(REPO, "scripts", "bifrost_ui.py")
NODE = shutil.which("node")


def _page_constant():
    """The PAGE template exactly as served: AST-extract, zero import side effects."""
    with open(UI_PATH, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "PAGE":
                    assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str), (
                        "PAGE is no longer a plain string constant -- update this pin to "
                        "extract whatever _html() now serves; do NOT let it skip."
                    )
                    return node.value.value
    pytest.fail("PAGE constant not found in bifrost_ui.py -- the serve path moved; re-anchor this pin.")


def _static_js_routes():
    """Every scripts/*.js file do_GET serves via _static -- new modules auto-join the pin."""
    with open(UI_PATH, "r", encoding="utf-8") as fh:
        src = fh.read()
    paths = re.findall(r'_static\("(scripts/[^"]+\.js)"', src)
    assert paths, "no _static scripts/*.js routes found -- the static serve path moved; re-anchor this pin."
    return paths


def _inline_scripts(html):
    """Bare <script> blocks only; <script src=...> tags have no inline body to check."""
    blocks = re.findall(r"<script>([\s\S]*?)</script>", html)
    assert blocks, "no inline <script> blocks found in PAGE -- template shape changed; re-anchor this pin."
    return blocks


def _parse_check(src, label, tmp_path):
    if not NODE:
        pytest.skip("node not on PATH -- the C10-1 parse gate CANNOT verify the console "
                    "without it; install node (the CI runners ship it)")
    js = tmp_path / (re.sub(r"[^\w.-]", "_", label) + ".js")
    js.write_text(src, encoding="utf-8")
    r = subprocess.run([NODE, "--check", str(js)], capture_output=True, text=True)
    if r.returncode != 0 and "Cannot use import statement" in (r.stderr or ""):
        mjs = js.with_suffix(".mjs")
        mjs.write_text(src, encoding="utf-8")
        r = subprocess.run([NODE, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, f"{label} does not parse:\n{r.stderr.strip()}"


def test_inline_page_scripts_parse(tmp_path):
    for n, block in enumerate(_inline_scripts(_page_constant())):
        _parse_check(block, f"PAGE inline script #{n}", tmp_path)


def test_static_module_scripts_parse(tmp_path):
    for rel in _static_js_routes():
        fpath = os.path.join(REPO, rel.replace("/", os.sep))
        assert os.path.exists(fpath), f"{rel} is routed in do_GET but missing on disk"
        with open(fpath, "r", encoding="utf-8") as fh:
            _parse_check(fh.read(), rel, tmp_path)
