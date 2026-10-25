"""PIN: the pre-tool hook refuses Write/Edit of a GPU-shaped .html page (2026-10-25).

The Claude desktop app opens any .html file that Write or Edit touches in its EMBEDDED browser pane;
a WebGL/WebGPU page there is this machine's AMD-driver crash trigger (scripts/hooks/claude_browser_guard.py,
receipt 2026-08-12). The VJ lanes of 2026-10-24/25 hit it 18 times across 10 lanes. Both hook copies
(scripts/ is the live one, agent/harness/ its twin) must refuse such a page, even outside the repo (harness
pages live in the scratchpad), allow ordinary pages and other file types, and fail open on bad input.
Each case is run as the app runs it: a subprocess with the payload on stdin.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = {"scripts": os.path.join(ROOT, "scripts", "hooks", "claude_pretooluse.py"),
          "agent_harness": os.path.join(ROOT, "agent", "harness", "hooks", "claude_pretooluse.py")}


def _run(copy: str, payload) -> dict | None:
    env = dict(os.environ, AKASHIC_RECALL_AT_ACTION="0")
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run([sys.executable, COPIES[copy]], input=raw, capture_output=True, text=True,
                       timeout=60, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            out = json.loads(line).get("hookSpecificOutput") or {}
            if out.get("permissionDecision") == "deny":
                return out
    return None


def _write(path, content):
    # a fresh synthetic session id per case: the hook's 3 s same-payload dedup must not swallow a case
    return {"session_id": f"test-{uuid.uuid4()}", "tool_name": "Write",
            "tool_input": {"file_path": str(path), "content": content}, "cwd": ROOT}


@pytest.mark.parametrize("copy", sorted(COPIES))
@pytest.mark.parametrize("name,content", [
    ("bench.html", "<canvas id=c></canvas><script>c.getContext('webgl2')</script>"),
    ("shell.html", '<div id=app></div><script type="module" src="bench.js"></script>'),
    ("stage.HTML", '<script type="importmap">{"imports":{"three":"./three.module.js"}}</script>'),
    ("gpu.htm", "<script>const a = await navigator.gpu.requestAdapter()</script>"),
])
def test_gpu_pages_are_refused(copy, name, content, tmp_path):
    out = _run(copy, _write(tmp_path / name, content))
    assert out, f"{copy} let a GPU page through: {name}"
    assert "browser pane" in out["permissionDecisionReason"] and ".txt" in out["permissionDecisionReason"]


@pytest.mark.parametrize("copy", sorted(COPIES))
@pytest.mark.parametrize("name,content", [
    ("notes.html", "<h1>Night shift</h1><p>plain page</p><script>console.log(1)</script>"),
    ("cdn.html", '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>'),
    ("bench.js", "canvas.getContext('webgl2')"),
    ("bench.html.txt", "<canvas></canvas><script>c.getContext('webgl2')</script>"),
])
def test_other_writes_are_allowed(copy, name, content, tmp_path):
    assert _run(copy, _write(tmp_path / name, content)) is None, f"{copy} refused {name}"


@pytest.mark.parametrize("copy", sorted(COPIES))
def test_edit_of_an_existing_gpu_page_is_refused(copy, tmp_path):
    page = tmp_path / "harness.html"
    page.write_text("<canvas></canvas><script src='harness.js'></script><title>old</title>", encoding="utf-8")
    payload = {"session_id": f"test-{uuid.uuid4()}", "tool_name": "Edit", "cwd": ROOT,
               "tool_input": {"file_path": str(page), "old_string": "old", "new_string": "new"}}
    assert _run(copy, payload), f"{copy} let an Edit of a GPU page through"


@pytest.mark.parametrize("copy", sorted(COPIES))
@pytest.mark.parametrize("raw", ["not json", '{"tool_name": "Write", "tool_input": "a bare string"}'])
def test_bad_input_fails_open(copy, raw):
    assert _run(copy, raw) is None
